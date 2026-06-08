"""Custom PII Evaluation Pipeline - No presidio-evaluator dependency.

Provides:
  - Configurable span matching strategies (IoU, coverage, containment, fuzzy, semi-strict)
  - Per-entity TP/FP/FN metrics
  - Confusion matrix (entity class predictions)
  - Error collection (false positives, false negatives, partial matches)
  - Per-sample TP/FP/FN tracking for bootstrap confidence intervals
  - JSON-serializable result artifact

Usage:
    from benchmarks.evaluator import CustomEvaluator, _Sample, _Span
    from benchmarks.matching import MatchingConfig, MatchingStrategy

    dataset = [_Sample(text="...", spans=[_Span(entity_type="EMAIL", start=0, end=5)])]
    config = MatchingConfig(strategy=MatchingStrategy.COVERAGE, coverage_threshold=0.3)
    evaluator = CustomEvaluator(matching_config=config)
    result = evaluator.evaluate(dataset)

    print(result.global_f1)
    print(result.confusion_matrix)
    result_dict = result.to_dict()
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import NamedTuple

import numpy as np

from benchmarks.matching.strategies import (
    MatchingConfig,
    MatchingStrategy,
    SpanMatcher,
    _iou,
)


class _Span(NamedTuple):
    entity_type: str
    start: int
    end: int


@dataclass
class _Sample:
    text: str
    spans: list[_Span] = field(default_factory=list)


@dataclass
class _EntityMetrics:
    tp: int = 0
    fp: int = 0
    fn: int = 0

    @property
    def precision(self) -> float:
        return self.tp / (self.tp + self.fp) if (self.tp + self.fp) else 0.0

    @property
    def recall(self) -> float:
        return self.tp / (self.tp + self.fn) if (self.tp + self.fn) else 0.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if (p + r) else 0.0


@dataclass
class PiiCoverageMetrics:
    total_samples: int = 0
    samples_with_pii: int = 0
    samples_pii_any_pred: int = 0
    samples_missed_entirely: int = 0

    @property
    def pii_recall_binary(self) -> float:
        return (
            self.samples_pii_any_pred / self.samples_with_pii
            if self.samples_with_pii
            else 0.0
        )

    @property
    def samples_without_pii(self) -> int:
        return self.total_samples - self.samples_with_pii


@dataclass
class EvaluationResult:
    metrics: dict[str, _EntityMetrics]
    confusion_matrix: np.ndarray
    entity_types: list[str]
    errors: dict[str, list[dict]]
    pii_coverage: PiiCoverageMetrics = field(default_factory=PiiCoverageMetrics)
    per_sample_counts: list[tuple[int, int, int]] = field(default_factory=list)
    match_details: list[dict] = field(default_factory=list)
    matching_config: MatchingConfig | None = None

    @property
    def global_tp(self) -> int:
        return sum(m.tp for m in self.metrics.values())

    @property
    def global_fp(self) -> int:
        return sum(m.fp for m in self.metrics.values())

    @property
    def global_fn(self) -> int:
        return sum(m.fn for m in self.metrics.values())

    @property
    def global_precision(self) -> float:
        total_pos = self.global_tp + self.global_fp
        return self.global_tp / total_pos if total_pos else 0.0

    @property
    def global_recall(self) -> float:
        total_actual = self.global_tp + self.global_fn
        return self.global_tp / total_actual if total_actual else 0.0

    @property
    def global_f1(self) -> float:
        p, r = self.global_precision, self.global_recall
        return 2 * p * r / (p + r) if (p + r) else 0.0

    def to_dict(self) -> dict:
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
            "matching_config": {
                "strategy": self.matching_config.strategy.value if self.matching_config else None,
                "iou_threshold": self.matching_config.iou_threshold if self.matching_config else None,
                "coverage_threshold": self.matching_config.coverage_threshold if self.matching_config else None,
                "score_threshold": self.matching_config.score_threshold if self.matching_config else None,
            } if self.matching_config else None,
        }


class CustomEvaluator:
    """PII detection evaluator with configurable span matching strategies.

    Evaluates predictions against ground truth by:
      1. Computing span matches using a configurable strategy (IoU, coverage, etc.)
      2. Matching spans with same entity type and sufficient match score
      3. Classifying unmatched spans as FP/FN
      4. Computing per-entity precision/recall/F1 + confusion matrix
    """

    def __init__(
        self,
        matching_config: MatchingConfig | None = None,
        iou_threshold: float | None = None,
        score_threshold: float | None = None,
    ) -> None:
        if matching_config is not None:
            self.matching_config = matching_config
            if score_threshold is not None:
                self.matching_config.score_threshold = score_threshold
        else:
            self.matching_config = MatchingConfig(
                iou_threshold=iou_threshold or 0.5,
                score_threshold=score_threshold or 0.4,
            )
        self._matcher = SpanMatcher(self.matching_config)
        self.iou_threshold = self.matching_config.iou_threshold
        self.score_threshold = self.matching_config.score_threshold

    @staticmethod
    def align_labels(
        dataset: list[_Sample],
        label_map: dict[str, str | None],
    ) -> list[_Sample]:
        aligned = []
        for sample in dataset:
            mapped_spans = []
            for span in sample.spans:
                if span.entity_type in label_map:
                    new_type = label_map[span.entity_type]
                    if new_type is not None:
                        mapped_spans.append(_Span(new_type, span.start, span.end))
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
        from src.api.services.text_analyzer import analyze

        if label_map:
            dataset = self.align_labels(dataset, label_map)

        metrics: dict[str, _EntityMetrics] = defaultdict(lambda: _EntityMetrics())
        coverage = PiiCoverageMetrics()
        errors: dict[str, list[dict]] = {
            "false_positives": [],
            "false_negatives": [],
            "partial_matches": [],
        }
        misclassifications: dict[tuple[str, str], int] = defaultdict(int)
        per_sample_counts: list[tuple[int, int, int]] = []
        match_details: list[dict] = []

        for sample in dataset:
            results = analyze(sample.text, language="nl")
            predictions = [
                _Span(r.entity_type, r.start, r.end)
                for r in results
                if r.score >= self.score_threshold
            ]

            gt_spans = sample.spans
            if entities:
                gt_spans = [s for s in gt_spans if s.entity_type in entities]
                predictions = [p for p in predictions if p.entity_type in entities]

            coverage.total_samples += 1
            if gt_spans:
                coverage.samples_with_pii += 1
                if predictions:
                    coverage.samples_pii_any_pred += 1
                else:
                    coverage.samples_missed_entirely += 1

            sample_tp, sample_fp, sample_fn = 0, 0, 0

            candidates: list[tuple[float, int, int]] = []
            for gi, gt in enumerate(gt_spans):
                for pi, pred in enumerate(predictions):
                    if pred.entity_type != gt.entity_type:
                        continue
                    m = self._matcher.match(pred.start, pred.end, gt.start, gt.end)
                    if m.is_match:
                        candidates.append((m.score, gi, pi))
                    match_details.append({
                        "sample_idx": len(per_sample_counts),
                        "gt_idx": gi,
                        "pred_idx": pi,
                        "entity_type": gt.entity_type,
                        "match_type": m.match_type,
                        "score": m.score,
                        "iou": m.iou,
                        "gt_coverage": m.gt_coverage,
                        "pred_coverage": m.pred_coverage,
                    })

            matched_gts: set[int] = set()
            matched_preds: set[int] = set()
            for _score, gi, pi in sorted(candidates, reverse=True):
                if gi in matched_gts or pi in matched_preds:
                    continue
                metrics[gt_spans[gi].entity_type].tp += 1
                sample_tp += 1
                matched_gts.add(gi)
                matched_preds.add(pi)

            for gi, gt in enumerate(gt_spans):
                if gi in matched_gts:
                    continue

                best_score = 0.0
                best_pi = -1
                best_wrong_type: str | None = None
                best_match = None
                for pi, pred in enumerate(predictions):
                    if pi in matched_preds or pred.entity_type == gt.entity_type:
                        continue
                    m = self._matcher.match(pred.start, pred.end, gt.start, gt.end)
                    if m.is_match and m.score > best_score:
                        best_score = m.score
                        best_pi = pi
                        best_wrong_type = pred.entity_type
                        best_match = m

                gt_text = sample.text[gt.start : gt.end]
                context_start = max(0, gt.start - 20)
                context_end = min(len(sample.text), gt.end + 20)
                context = sample.text[context_start:context_end]

                metrics[gt.entity_type].fn += 1
                sample_fn += 1

                if best_wrong_type is not None:
                    metrics[best_wrong_type].fp += 1
                    sample_fp += 1
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
                            "iou": float(best_match.iou) if best_match else 0.0,
                            "gt_coverage": float(best_match.gt_coverage) if best_match else 0.0,
                            "match_type": best_match.match_type if best_match else "unknown",
                        }
                    )
                else:
                    misclassifications[(gt.entity_type, "O")] += 1
                    errors["false_negatives"].append(
                        {
                            "entity_type": gt.entity_type,
                            "text": gt_text,
                            "context": context,
                        }
                    )

            for pi, pred in enumerate(predictions):
                if pi in matched_preds:
                    continue
                metrics[pred.entity_type].fp += 1
                sample_fp += 1
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

            per_sample_counts.append((sample_tp, sample_fp, sample_fn))

        if entities:
            metrics = {k: v for k, v in metrics.items() if k in entities}

        confusion_matrix = self._build_confusion_matrix(metrics, misclassifications)
        entity_types = sorted(metrics.keys()) + ["O"]

        return EvaluationResult(
            metrics=metrics,
            confusion_matrix=confusion_matrix,
            entity_types=entity_types,
            errors=errors,
            pii_coverage=coverage,
            per_sample_counts=per_sample_counts,
            match_details=match_details,
            matching_config=self.matching_config,
        )

    def evaluate_from_cache(
        self,
        dataset: list[_Sample],
        predictions_cache: dict[int, list[_Span]],
        entities: frozenset[str] | None = None,
        label_map: dict[str, str | None] | None = None,
    ) -> EvaluationResult:
        if label_map:
            dataset = self.align_labels(dataset, label_map)

        metrics: dict[str, _EntityMetrics] = defaultdict(lambda: _EntityMetrics())
        coverage = PiiCoverageMetrics()
        errors: dict[str, list[dict]] = {
            "false_positives": [],
            "false_negatives": [],
            "partial_matches": [],
        }
        misclassifications: dict[tuple[str, str], int] = defaultdict(int)
        per_sample_counts: list[tuple[int, int, int]] = []
        match_details: list[dict] = []

        for i, sample in enumerate(dataset):
            predictions = [
                p for p in predictions_cache.get(i, [])
                if True
            ]

            gt_spans = sample.spans
            if entities:
                gt_spans = [s for s in gt_spans if s.entity_type in entities]
                predictions = [p for p in predictions if p.entity_type in entities]

            coverage.total_samples += 1
            if gt_spans:
                coverage.samples_with_pii += 1
                if predictions:
                    coverage.samples_pii_any_pred += 1
                else:
                    coverage.samples_missed_entirely += 1

            sample_tp, sample_fp, sample_fn = 0, 0, 0

            candidates: list[tuple[float, int, int]] = []
            for gi, gt in enumerate(gt_spans):
                for pi, pred in enumerate(predictions):
                    if pred.entity_type != gt.entity_type:
                        continue
                    m = self._matcher.match(pred.start, pred.end, gt.start, gt.end)
                    if m.is_match:
                        candidates.append((m.score, gi, pi))
                        match_details.append({
                            "sample_idx": i,
                            "gt_idx": gi,
                            "pred_idx": pi,
                            "entity_type": gt.entity_type,
                            "match_type": m.match_type,
                            "score": m.score,
                            "iou": m.iou,
                            "gt_coverage": m.gt_coverage,
                            "pred_coverage": m.pred_coverage,
                        })

            matched_gts: set[int] = set()
            matched_preds: set[int] = set()
            for _score, gi, pi in sorted(candidates, reverse=True):
                if gi in matched_gts or pi in matched_preds:
                    continue
                metrics[gt_spans[gi].entity_type].tp += 1
                sample_tp += 1
                matched_gts.add(gi)
                matched_preds.add(pi)

            for gi, gt in enumerate(gt_spans):
                if gi in matched_gts:
                    continue

                best_score = 0.0
                best_pi = -1
                best_wrong_type: str | None = None
                best_match = None
                for pi, pred in enumerate(predictions):
                    if pi in matched_preds or pred.entity_type == gt.entity_type:
                        continue
                    m = self._matcher.match(pred.start, pred.end, gt.start, gt.end)
                    if m.is_match and m.score > best_score:
                        best_score = m.score
                        best_pi = pi
                        best_wrong_type = pred.entity_type
                        best_match = m

                gt_text = sample.text[gt.start : gt.end]
                context_start = max(0, gt.start - 20)
                context_end = min(len(sample.text), gt.end + 20)
                context = sample.text[context_start:context_end]

                metrics[gt.entity_type].fn += 1
                sample_fn += 1

                if best_wrong_type is not None:
                    metrics[best_wrong_type].fp += 1
                    sample_fp += 1
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
                            "iou": float(best_match.iou) if best_match else 0.0,
                            "gt_coverage": float(best_match.gt_coverage) if best_match else 0.0,
                            "match_type": best_match.match_type if best_match else "unknown",
                        }
                    )
                else:
                    misclassifications[(gt.entity_type, "O")] += 1
                    errors["false_negatives"].append(
                        {
                            "entity_type": gt.entity_type,
                            "text": gt_text,
                            "context": context,
                        }
                    )

            for pi, pred in enumerate(predictions):
                if pi in matched_preds:
                    continue
                metrics[pred.entity_type].fp += 1
                sample_fp += 1
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

            per_sample_counts.append((sample_tp, sample_fp, sample_fn))

        if entities:
            metrics = {k: v for k, v in metrics.items() if k in entities}

        confusion_matrix = self._build_confusion_matrix(metrics, misclassifications)
        entity_types = sorted(metrics.keys()) + ["O"]

        return EvaluationResult(
            metrics=metrics,
            confusion_matrix=confusion_matrix,
            entity_types=entity_types,
            errors=errors,
            pii_coverage=coverage,
            per_sample_counts=per_sample_counts,
            match_details=match_details,
            matching_config=self.matching_config,
        )

    def _iou(self, pred_start: int, pred_end: int, gt_start: int, gt_end: int) -> float:
        return _iou(pred_start, pred_end, gt_start, gt_end)

    def _build_confusion_matrix(
        self,
        metrics: dict[str, _EntityMetrics],
        misclassifications: dict[tuple[str, str], int],
    ) -> np.ndarray:
        entity_types = sorted(metrics.keys()) + ["O"]
        entity_to_idx = {e: i for i, e in enumerate(entity_types)}
        n = len(entity_types)

        matrix = np.zeros((n, n), dtype=int)

        for entity in metrics.keys():
            i = entity_to_idx[entity]
            matrix[i, i] = metrics[entity].tp

        for (gt_type, pred_type), count in misclassifications.items():
            if gt_type in entity_to_idx and pred_type in entity_to_idx:
                i = entity_to_idx[gt_type]
                j = entity_to_idx[pred_type]
                matrix[i, j] += count

        return matrix


_TOKEN_RE = re.compile(r"[a-zA-Z\u00C0-\u024F]{2,}")


def token_error_analysis(
    errors: dict[str, list[dict]],
    n: int = 10,
) -> dict:
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
