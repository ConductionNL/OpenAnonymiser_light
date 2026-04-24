"""Custom PII Evaluation Pipeline - No presidio-evaluator dependency.

Provides:
  - Character-span IoU matching (0.5+ threshold)
  - Per-entity TP/FP/FN metrics
  - Confusion matrix (entity class predictions)
  - Error collection (false positives, false negatives, partial matches)
  - JSON-serializable result artifact

Usage:
    from benchmarks.evaluator import CustomEvaluator, _Sample, _Span
    
    dataset = [_Sample(text="...", spans=[_Span(entity_type="EMAIL", start=0, end=5)])]
    evaluator = CustomEvaluator(iou_threshold=0.5, score_threshold=0.3)
    result = evaluator.evaluate(dataset)
    
    print(result.global_f1)
    print(result.confusion_matrix)
    result_dict = result.to_dict()  # Export to JSON
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import NamedTuple

import numpy as np



class _Span(NamedTuple):
    """Character-level span: entity type + start/end positions."""

    entity_type: str
    start: int
    end: int


@dataclass
class _Sample:
    """Text sample with labeled entity spans."""

    text: str
    spans: list[_Span] = field(default_factory=list)


@dataclass
class _EntityMetrics:
    """Per-entity evaluation counts: TP/FP/FN → Precision/Recall/F1."""

    tp: int = 0
    fp: int = 0
    fn: int = 0

    @property
    def precision(self) -> float:
        """True positives / (true positives + false positives)."""
        return self.tp / (self.tp + self.fp) if (self.tp + self.fp) else 0.0

    @property
    def recall(self) -> float:
        """True positives / (true positives + false negatives)."""
        return self.tp / (self.tp + self.fn) if (self.tp + self.fn) else 0.0

    @property
    def f1(self) -> float:
        """Harmonic mean of precision and recall."""
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if (p + r) else 0.0


@dataclass
class PiiCoverageMetrics:
    """Binary PII coverage: was any PII detected per sample?"""

    total_samples: int = 0
    samples_with_pii: int = 0
    samples_pii_any_pred: int = 0
    samples_missed_entirely: int = 0

    @property
    def pii_recall_binary(self) -> float:
        """Fraction of PII-containing samples where model predicted at least one span."""
        return (
            self.samples_pii_any_pred / self.samples_with_pii
            if self.samples_with_pii
            else 0.0
        )

    @property
    def samples_without_pii(self) -> int:
        """Samples where GT contained no PII."""
        return self.total_samples - self.samples_with_pii


@dataclass
class EvaluationResult:
    """Aggregate evaluation results: metrics, confusion matrix, errors."""

    metrics: dict[str, _EntityMetrics]
    confusion_matrix: np.ndarray
    entity_types: list[str]
    errors: dict[str, list[dict]]
    pii_coverage: PiiCoverageMetrics = field(default_factory=PiiCoverageMetrics)

    @property
    def global_tp(self) -> int:
        """Total true positives across all entities."""
        return sum(m.tp for m in self.metrics.values())

    @property
    def global_fp(self) -> int:
        """Total false positives across all entities."""
        return sum(m.fp for m in self.metrics.values())

    @property
    def global_fn(self) -> int:
        """Total false negatives across all entities."""
        return sum(m.fn for m in self.metrics.values())

    @property
    def global_precision(self) -> float:
        """Global precision: TP / (TP + FP)."""
        total_pos = self.global_tp + self.global_fp
        return self.global_tp / total_pos if total_pos else 0.0

    @property
    def global_recall(self) -> float:
        """Global recall: TP / (TP + FN)."""
        total_actual = self.global_tp + self.global_fn
        return self.global_tp / total_actual if total_actual else 0.0

    @property
    def global_f1(self) -> float:
        """Global F1 score."""
        p, r = self.global_precision, self.global_recall
        return 2 * p * r / (p + r) if (p + r) else 0.0

    def to_dict(self) -> dict:
        """Serialize to JSON-compatible dict.

        Includes:
          - global: precision, recall, F1, TP/FP/FN totals
          - per_entity: per-entity metrics
          - confusion_matrix: raw matrix (for export)
        """
        return {
            "global": {
                "precision": float(self.global_precision),
                "recall": float(self.global_recall),
                "f1": float(self.global_f1),
                "tp": int(self.global_tp),
                "fp": int(self.global_fp),
                "fn": int(self.global_fn),
            },
            "per_entity": {
                entity: {
                    "precision": float(self.metrics[entity].precision),
                    "recall": float(self.metrics[entity].recall),
                    "f1": float(self.metrics[entity].f1),
                    "tp": int(self.metrics[entity].tp),
                    "fp": int(self.metrics[entity].fp),
                    "fn": int(self.metrics[entity].fn),
                }
                for entity in self.entity_types
                if entity != "O"
            },
            "confusion_matrix": self.confusion_matrix.tolist(),
            "pii_coverage": {
                "total_samples": self.pii_coverage.total_samples,
                "samples_with_pii": self.pii_coverage.samples_with_pii,
                "samples_pii_any_pred": self.pii_coverage.samples_pii_any_pred,
                "samples_missed_entirely": self.pii_coverage.samples_missed_entirely,
                "pii_recall_binary": float(self.pii_coverage.pii_recall_binary),
            },
        }


class CustomEvaluator:
    """PII detection evaluator with IoU-based span matching.

    Evaluates predictions against ground truth by:
      1. Computing Intersection-over-Union (IoU) for each predicted vs ground-truth span pair
      2. Matching spans with IoU >= threshold and same entity type
      3. Classifying unmatched spans as FP/FN
      4. Computing per-entity precision/recall/F1 + confusion matrix
    """

    def __init__(self, iou_threshold: float = 0.5, score_threshold: float = 0.3) -> None:
        """Initialize evaluator.

        Args:
            iou_threshold: Minimum IoU (0.0-1.0) to consider a match. Default 0.5.
            score_threshold: Minimum Presidio confidence score (0.0-1.0). Default 0.3.
        """
        self.iou_threshold = iou_threshold
        self.score_threshold = score_threshold

    @staticmethod
    def align_labels(
        dataset: list[_Sample],
        label_map: dict[str, str | None],
    ) -> list[_Sample]:
        """Remap ground-truth entity labels before evaluation.

        Maps dataset labels to the entity types a specific model configuration
        can detect. Labels mapped to None are dropped (model cannot detect them).
        Labels not present in label_map are kept as-is.

        Args:
            dataset: List of samples with ground-truth spans
            label_map: Dict of {dataset_label: model_label | None}
                       None means drop the span from evaluation.

        Returns:
            New dataset list with remapped/dropped spans.
        """
        aligned = []
        for sample in dataset:
            mapped_spans = []
            for span in sample.spans:
                if span.entity_type in label_map:
                    new_type = label_map[span.entity_type]
                    if new_type is not None:
                        mapped_spans.append(_Span(new_type, span.start, span.end))
                    # else: drop (None mapping means model cannot detect this type)
                else:
                    mapped_spans.append(span)
            aligned.append(_Sample(sample.text, mapped_spans))
        return aligned

    def evaluate(
        self,
        dataset: list[_Sample],
        entities: frozenset[str] | None = None,
        label_map: dict[str, str | None] | None = None,
    ) -> EvaluationResult:
        """Run full evaluation pipeline on dataset.

        Args:
            dataset: List of samples with text and ground-truth spans
            entities: Optional filter to evaluate only specific entity types
            label_map: Optional entity label remapping applied to ground truth
                       before evaluation (e.g. to align dataset labels to a
                       specific model's supported entity types).

        Returns:
            EvaluationResult with metrics, confusion matrix, errors
        """
        # Import here to avoid circular dependency with text_analyzer
        from src.api.services.text_analyzer import analyze

        # Apply label mapping to ground-truth spans
        if label_map:
            dataset = self.align_labels(dataset, label_map)

        # Per-entity metrics and confusion matrix data
        metrics: dict[str, _EntityMetrics] = defaultdict(lambda: _EntityMetrics())
        coverage = PiiCoverageMetrics()
        errors: dict[str, list[dict]] = {
            "false_positives": [],
            "false_negatives": [],
            "partial_matches": [],
        }
        # Confusion matrix entries: (gt_type, pred_type) → count
        # Convention: row = ground truth, col = prediction
        #   TP diagonal:       (A, A)
        #   FN (missed):       (A, "O")  — GT was A, nothing predicted
        #   FP (spurious):    ("O", B)  — no GT, model predicted B
        #   Misclassification: (A, B)   — GT was A, model predicted B
        misclassifications: dict[tuple[str, str], int] = defaultdict(int)

        for sample in dataset:
            # Get predictions from analyzer
            results = analyze(sample.text, language="nl")
            predictions = [
                _Span(r.entity_type, r.start, r.end)
                for r in results
                if r.score >= self.score_threshold
            ]

            # Scope GT and predictions to entity filter
            gt_spans = sample.spans
            if entities:
                gt_spans = [s for s in gt_spans if s.entity_type in entities]
                predictions = [p for p in predictions if p.entity_type in entities]

            # Track binary PII coverage per sample
            coverage.total_samples += 1
            if gt_spans:
                coverage.samples_with_pii += 1
                if predictions:
                    coverage.samples_pii_any_pred += 1
                else:
                    coverage.samples_missed_entirely += 1

            # --- Bipartite greedy TP matching (same entity type, IoU >= threshold) ---
            # Compute all qualifying (iou, gt_idx, pred_idx) pairs, then assign
            # greedily from highest IoU down so each span is matched at most once.
            candidates: list[tuple[float, int, int]] = []
            for gi, gt in enumerate(gt_spans):
                for pi, pred in enumerate(predictions):
                    if pred.entity_type != gt.entity_type:
                        continue
                    iou = self._iou(pred.start, pred.end, gt.start, gt.end)
                    if iou >= self.iou_threshold:
                        candidates.append((iou, gi, pi))

            matched_gts: set[int] = set()
            matched_preds: set[int] = set()
            for _iou, gi, pi in sorted(candidates, reverse=True):
                if gi in matched_gts or pi in matched_preds:
                    continue
                metrics[gt_spans[gi].entity_type].tp += 1
                matched_gts.add(gi)
                matched_preds.add(pi)

            # --- Unmatched GT spans → FN (or misclassification) ---
            for gi, gt in enumerate(gt_spans):
                if gi in matched_gts:
                    continue

                # Check for spatial overlap with a different entity type
                best_iou = 0.0
                best_pi = -1
                best_wrong_type: str | None = None
                for pi, pred in enumerate(predictions):
                    if pi in matched_preds or pred.entity_type == gt.entity_type:
                        continue
                    iou = self._iou(pred.start, pred.end, gt.start, gt.end)
                    if iou >= self.iou_threshold and iou > best_iou:
                        best_iou = iou
                        best_pi = pi
                        best_wrong_type = pred.entity_type

                gt_text = sample.text[gt.start : gt.end]
                context_start = max(0, gt.start - 20)
                context_end = min(len(sample.text), gt.end + 20)
                context = sample.text[context_start:context_end]

                metrics[gt.entity_type].fn += 1

                if best_wrong_type is not None:
                    # Misclassification: same span, wrong type
                    # FN for GT type (already counted), FP for predicted type
                    metrics[best_wrong_type].fp += 1
                    misclassifications[(gt.entity_type, best_wrong_type)] += 1
                    matched_preds.add(best_pi)
                    pred_text = sample.text[
                        predictions[best_pi].start : predictions[best_pi].end
                    ]
                    errors["partial_matches"].append(
                        {
                            "entity_type": gt.entity_type,
                            "predicted_type": best_wrong_type,
                            "predicted": pred_text,
                            "ground_truth": gt_text,
                            "iou": float(best_iou),
                        }
                    )
                else:
                    # Pure miss: GT present, nothing predicted
                    misclassifications[(gt.entity_type, "O")] += 1
                    errors["false_negatives"].append(
                        {
                            "entity_type": gt.entity_type,
                            "text": gt_text,
                            "context": context,
                        }
                    )

            # --- Unmatched predictions → FP (spurious) ---
            for pi, pred in enumerate(predictions):
                if pi in matched_preds:
                    continue
                metrics[pred.entity_type].fp += 1
                misclassifications[("O", pred.entity_type)] += 1
                pred_text = sample.text[pred.start : pred.end]
                context_start = max(0, pred.start - 20)
                context_end = min(len(sample.text), pred.end + 20)
                context = sample.text[context_start:context_end]
                errors["false_positives"].append(
                    {
                        "entity_type": pred.entity_type,
                        "text": pred_text,
                        "context": context,
                    }
                )

        # Filter metrics to entity set (redundant when per-sample filter is active,
        # kept as safety net for entities that slip through label_map)
        if entities:
            metrics = {k: v for k, v in metrics.items() if k in entities}

        # Build confusion matrix — always (n+1)×(n+1) including the "O" row/col
        confusion_matrix = self._build_confusion_matrix(metrics, misclassifications)

        # entity_types always includes "O" to match the (n+1)×(n+1) matrix shape
        entity_types = sorted(metrics.keys()) + ["O"]

        return EvaluationResult(
            metrics=metrics,
            confusion_matrix=confusion_matrix,
            entity_types=entity_types,
            errors=errors,
            pii_coverage=coverage,
        )

    def _iou(self, pred_start: int, pred_end: int, gt_start: int, gt_end: int) -> float:
        """Compute Intersection-over-Union (IoU) for character spans.

        Args:
            pred_start: Predicted span start position
            pred_end: Predicted span end position
            gt_start: Ground-truth span start position
            gt_end: Ground-truth span end position

        Returns:
            IoU score between 0.0 and 1.0
        """
        inter_start = max(pred_start, gt_start)
        inter_end = min(pred_end, gt_end)

        if inter_start >= inter_end:
            return 0.0

        intersection = inter_end - inter_start
        union = (pred_end - pred_start) + (gt_end - gt_start) - intersection

        return intersection / union if union else 0.0

    def _build_confusion_matrix(
        self,
        metrics: dict[str, _EntityMetrics],
        misclassifications: dict[tuple[str, str], int],
    ) -> np.ndarray:
        """Build confusion matrix from per-entity metrics.

        Standard row=GT, col=prediction layout:
          Diagonal (A, A)  = TP — correct detection
          Col O   (A, "O") = FN — GT was A, model predicted nothing
          Row O  ("O",  B) = FP — no GT, model spuriously predicted B
          Off-diagonal (A, B) = misclassification — GT was A, predicted B

        Args:
            metrics: Per-entity TP/FP/FN counts
            misclassifications: Dict of (gt_type, pred_type) → count

        Returns:
            (n+1) × (n+1) confusion matrix (n = number of entity types, +1 for O)
        """
        # Add "O" as pseudo-entity for missed/spurious predictions
        entity_types = sorted(metrics.keys()) + ["O"]
        entity_to_idx = {e: i for i, e in enumerate(entity_types)}
        n = len(entity_types)

        matrix = np.zeros((n, n), dtype=int)

        # Fill in TP on diagonal (only for real entities, not O)
        for entity in metrics.keys():
            i = entity_to_idx[entity]
            matrix[i, i] = metrics[entity].tp

        # Fill in misclassifications and FN/FP
        for (gt_type, pred_type), count in misclassifications.items():
            if gt_type in entity_to_idx and pred_type in entity_to_idx:
                i = entity_to_idx[gt_type]  # Row = ground truth
                j = entity_to_idx[pred_type]  # Col = prediction
                matrix[i, j] += count

        return matrix


_TOKEN_RE = re.compile(r"[a-zA-Z\u00C0-\u024F]{2,}")


def token_error_analysis(
    errors: dict[str, list[dict]],
    n: int = 10,
) -> dict:
    """Aggregate token-level analysis of false positives and false negatives.

    For false positives: most common tokens in the wrongly-predicted text.
    For false negatives: most common context tokens around missed entities
    (useful for identifying recognizer context words to boost confidence scores).

    Args:
        errors: errors dict from EvaluationResult.errors
        n: Number of top tokens to return per category

    Returns:
        {
            "fp_tokens": [(token, count), ...],
            "fn_context_tokens": [(token, count), ...],
            "fp_by_entity": {entity_type: [(token, count), ...]},
            "fn_by_entity": {entity_type: [(token, count), ...]},
        }
    """
    def _tokens(text: str) -> list[str]:
        return [t.lower() for t in _TOKEN_RE.findall(text)]

    fp_counts: Counter = Counter()
    fp_by_entity: dict[str, Counter] = defaultdict(Counter)
    for err in errors.get("false_positives", []):
        toks = _tokens(err.get("text", ""))
        fp_counts.update(toks)
        fp_by_entity[err["entity_type"]].update(toks)

    fn_ctx_counts: Counter = Counter()
    fn_by_entity: dict[str, Counter] = defaultdict(Counter)
    for err in errors.get("false_negatives", []):
        # Context tokens, excluding the missed entity text itself
        entity_toks = set(_tokens(err.get("text", "")))
        ctx_toks = [t for t in _tokens(err.get("context", "")) if t not in entity_toks]
        fn_ctx_counts.update(ctx_toks)
        fn_by_entity[err["entity_type"]].update(ctx_toks)

    return {
        "fp_tokens": fp_counts.most_common(n),
        "fn_context_tokens": fn_ctx_counts.most_common(n),
        "fp_by_entity": {et: c.most_common(n) for et, c in fp_by_entity.items()},
        "fn_by_entity": {et: c.most_common(n) for et, c in fn_by_entity.items()},
    }
