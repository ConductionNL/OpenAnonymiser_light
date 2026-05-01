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

import json
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
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


class ConfusionMatrixBuilder:
    """Build confusion matrix: entity type × entity type.

    Rows = ground truth classes
    Cols = predicted classes
    Diagonal = correct predictions (TP)
    Off-diagonal = misclassifications (FP/FN)
    """

    def __init__(self, entity_types: list[str]) -> None:
        """Initialize confusion matrix.

        Args:
            entity_types: Sorted list of entity types (determines row/col order)
        """
        self.entity_types = sorted(entity_types)
        self.entity_to_idx = {e: i for i, e in enumerate(self.entity_types)}
        n = len(self.entity_types)
        # Matrix: n × n (no extra "missing" or "background" class for now)
        self.matrix: np.ndarray = np.zeros((n, n), dtype=int)

    def add_tp(self, entity_type: str) -> None:
        """Record true positive (correct entity detected).

        Args:
            entity_type: Entity type that was correctly detected
        """
        idx = self.entity_to_idx[entity_type]
        self.matrix[idx, idx] += 1

    def add_fp(self, pred_entity_type: str, gt_entity_type: str) -> None:
        """Record false positive / misclassification.

        Args:
            pred_entity_type: What the model predicted
            gt_entity_type: What the ground truth actual is
        """
        gt_idx = self.entity_to_idx.get(gt_entity_type)
        pred_idx = self.entity_to_idx.get(pred_entity_type)
        if gt_idx is not None and pred_idx is not None:
            self.matrix[gt_idx, pred_idx] += 1

    def add_fn(self, gt_entity_type: str) -> None:
        """Record false negative (entity missed by model).

        Args:
            gt_entity_type: Entity type that was missed
        """
        # No predicted entity, so mark as "missed" via diagonal 0
        # In confusion matrix: ground-truth present but prediction absent
        # We'll track this separately if needed, for now just count in FN
        pass

    def get_matrix(self) -> np.ndarray:
        """Return the confusion matrix (not normalized)."""
        return self.matrix

    def get_matrix_normalized_by_row(self) -> np.ndarray:
        """Normalize confusion matrix by row (per ground-truth entity).

        Returns:
            Normalized matrix where each row sums to 1.0
            Interpretation: For each ground-truth entity X, what % was predicted as Y?
        """
        row_sums = self.matrix.sum(axis=1, keepdims=True)
        # Avoid division by zero
        row_sums[row_sums == 0] = 1
        return self.matrix / row_sums


@dataclass
class EvaluationResult:
    """Aggregate evaluation results: metrics, confusion matrix, errors."""

    metrics: dict[str, _EntityMetrics]
    confusion_matrix: np.ndarray
    entity_types: list[str]
    errors: dict[str, list[dict]]

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
            },
            "confusion_matrix": self.confusion_matrix.tolist(),
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

    def evaluate(
        self,
        dataset: list[_Sample],
        entities: frozenset[str] | None = None,
    ) -> EvaluationResult:
        """Run full evaluation pipeline on dataset.

        Args:
            dataset: List of samples with text and ground-truth spans
            entities: Optional filter to evaluate only specific entity types

        Returns:
            EvaluationResult with metrics, confusion matrix, errors
        """
        # Import here to avoid circular dependency with text_analyzer
        from src.api.services.text_analyzer import analyze

        # 1. Compute per-entity metrics
        metrics: dict[str, _EntityMetrics] = defaultdict(lambda: _EntityMetrics())
        errors: dict[str, list[dict]] = {
            "false_positives": [],
            "false_negatives": [],
            "partial_matches": [],
        }
        # Track misclassifications: (gt_entity_type, pred_entity_type) → count
        misclassifications: dict[tuple[str, str], int] = defaultdict(int)

        for sample in dataset:
            # Get predictions from analyzer
            results = analyze(sample.text, language="nl")
            predictions = [
                _Span(r.entity_type, r.start, r.end)
                for r in results
                if r.score >= self.score_threshold
            ]

            # Match predictions to ground truth
            matched_preds: set[int] = set()

            for gt in sample.spans:
                found = False
                best_iou = 0.0
                best_i = -1
                best_wrong_type = None

                # Try to find matching prediction
                for i, pred in enumerate(predictions):
                    iou = self._iou(
                        pred.start,
                        pred.end,
                        gt.start,
                        gt.end,
                    )

                    if pred.entity_type == gt.entity_type:
                        if iou >= self.iou_threshold:
                            # Match found
                            found = True
                            metrics[gt.entity_type].tp += 1
                            matched_preds.add(i)
                            break
                        elif iou > best_iou:
                            # Track best partial match (same type)
                            best_iou = iou
                            best_i = i
                    else:
                        # Different entity type - track for misclassification
                        if iou > best_iou:
                            best_iou = iou
                            best_i = i
                            best_wrong_type = pred.entity_type

                if not found:
                    # False negative
                    metrics[gt.entity_type].fn += 1
                    # Track in confusion matrix as (O, entity_type)
                    misclassifications[("O", gt.entity_type)] += 1

                    gt_text = sample.text[gt.start : gt.end]
                    context_start = max(0, gt.start - 20)
                    context_end = min(len(sample.text), gt.end + 20)
                    context = sample.text[context_start:context_end]

                    errors["false_negatives"].append(
                        {
                            "entity_type": gt.entity_type,
                            "text": gt_text,
                            "context": context,
                        }
                    )

                    # Record partial match or misclassification if applicable
                    if best_iou >= self.iou_threshold:
                        pred = predictions[best_i]
                        pred_text = sample.text[pred.start : pred.end]
                        
                        if best_wrong_type:
                            # Misclassification: spatial match but wrong entity type
                            misclassifications[(gt.entity_type, best_wrong_type)] += 1
                            matched_preds.add(best_i)  # Mark as matched for FP purposes
                        
                        errors["partial_matches"].append(
                            {
                                "entity_type": gt.entity_type,
                                "predicted": pred_text,
                                "ground_truth": gt_text,
                                "iou": float(best_iou),
                            }
                        )

            # False positives (unmatched predictions)
            for i, pred in enumerate(predictions):
                if i not in matched_preds:
                    metrics[pred.entity_type].fp += 1
                    # Track in confusion matrix as (entity_type, O) for spurious predictions
                    misclassifications[(pred.entity_type, "O")] += 1

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

        # 2. Filter entities if requested
        if entities:
            metrics = {k: v for k, v in metrics.items() if k in entities}

        # 3. Build confusion matrix
        confusion_matrix = self._build_confusion_matrix(metrics, misclassifications)

        # 4. Build entity_types list (including "O" pseudo-entity only if not filtered)
        entity_types = sorted(metrics.keys())
        if entities is None:
            # Only add "O" if we're using all entities (not filtered)
            entity_types.append("O")

        # 5. Return result
        return EvaluationResult(
            metrics=metrics,
            confusion_matrix=confusion_matrix,
            entity_types=entity_types,
            errors=errors,
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

        Rows = ground-truth entity types + O (Other/missed)
        Cols = predicted entity types + O (Other/spurious)
        Diagonal = correct predictions (TP)
        Row O = false negatives (missed entities per type)
        Col O = false positives without overlap (spurious predictions per type)
        Off-diagonal (Entity→Entity) = misclassifications (spatial match, wrong type)

        Args:
            metrics: Per-entity TP/FP/FN counts
            misclassifications: Dict of (gt_type, pred_type) → count, including ("O", type) and (type, "O")

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
