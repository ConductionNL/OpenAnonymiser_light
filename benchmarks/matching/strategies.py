"""Span matching strategies for PII evaluation.

Provides configurable matching strategies that go beyond standard IoU,
enabling more tolerant evaluation for NER models like GLiNER that
produce slightly offset or asymmetric entity spans.

Usage:
    from benchmarks.matching import MatchingConfig, MatchingStrategy, SpanMatcher

    config = MatchingConfig(strategy=MatchingStrategy.COVERAGE, coverage_threshold=0.3)
    matcher = SpanMatcher(config)
    match = matcher.match(pred_start=10, pred_end=20, gt_start=8, gt_end=25)
    print(match.is_match, match.score, match.gt_coverage)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import ClassVar


class MatchingStrategy(Enum):
    IOU = "iou"
    PARTIAL_OVERLAP = "partial"
    COVERAGE = "coverage"
    CONTAINMENT = "containment"
    FUZZY_LENGTH = "fuzzy_length"
    SEMI_STRICT = "semi_strict"


@dataclass(frozen=True)
class SpanMatch:
    is_match: bool
    score: float
    match_type: str
    gt_coverage: float
    pred_coverage: float
    iou: float
    length_ratio: float


@dataclass
class MatchingConfig:
    strategy: MatchingStrategy = MatchingStrategy.IOU
    iou_threshold: float = 0.5
    coverage_threshold: float = 0.3
    length_ratio_threshold: float = 0.5
    score_threshold: float = 0.4

    _PROFILE_DEFAULTS: ClassVar[dict[str, dict]] = {
        "gliner": {
            "strategy": MatchingStrategy.COVERAGE,
            "coverage_threshold": 0.3,
            "iou_threshold": 0.3,
            "score_threshold": 0.45,
        },
        "spacy": {
            "strategy": MatchingStrategy.IOU,
            "iou_threshold": 0.5,
            "score_threshold": 0.4,
        },
        "strict": {
            "strategy": MatchingStrategy.IOU,
            "iou_threshold": 0.75,
            "score_threshold": 0.4,
        },
    }

    @classmethod
    def from_profile(cls, profile: str) -> MatchingConfig:
        cfg = cls._PROFILE_DEFAULTS.get(profile)
        if cfg is None:
            raise ValueError(
                f"Unknown profile '{profile}'. Choose from: {sorted(cls._PROFILE_DEFAULTS)}"
            )
        return cls(**cfg)

    @classmethod
    def available_profiles(cls) -> list[str]:
        return sorted(cls._PROFILE_DEFAULTS.keys())


class SpanMatcher:
    def __init__(self, config: MatchingConfig) -> None:
        self.config = config

    def match(
        self,
        pred_start: int,
        pred_end: int,
        gt_start: int,
        gt_end: int,
    ) -> SpanMatch:
        iou = _iou(pred_start, pred_end, gt_start, gt_end)
        gt_coverage = _coverage(pred_start, pred_end, gt_start, gt_end)
        pred_coverage = _coverage(gt_start, gt_end, pred_start, pred_end)
        pred_len = pred_end - pred_start
        gt_len = gt_end - gt_start
        length_ratio = min(pred_len, gt_len) / max(pred_len, gt_len) if max(pred_len, gt_len) else 0.0

        strategy = self.config.strategy

        if strategy == MatchingStrategy.IOU:
            is_match = iou >= self.config.iou_threshold
            return SpanMatch(is_match, iou, "iou", gt_coverage, pred_coverage, iou, length_ratio)

        if strategy == MatchingStrategy.PARTIAL_OVERLAP:
            is_match = iou > 0.0
            return SpanMatch(is_match, iou, "partial", gt_coverage, pred_coverage, iou, length_ratio)

        if strategy == MatchingStrategy.COVERAGE:
            is_match = gt_coverage >= self.config.coverage_threshold
            return SpanMatch(is_match, gt_coverage, "coverage", gt_coverage, pred_coverage, iou, length_ratio)

        if strategy == MatchingStrategy.CONTAINMENT:
            contained = (gt_start <= pred_start and pred_end <= gt_end) or \
                        (pred_start <= gt_start and gt_end <= pred_end)
            score = 1.0 if contained else iou
            return SpanMatch(contained, score, "containment", gt_coverage, pred_coverage, iou, length_ratio)

        if strategy == MatchingStrategy.FUZZY_LENGTH:
            if length_ratio >= self.config.length_ratio_threshold:
                is_match = iou >= self.config.iou_threshold
                return SpanMatch(is_match, iou, "fuzzy_similar", gt_coverage, pred_coverage, iou, length_ratio)
            intersection = max(0, min(pred_end, gt_end) - max(pred_start, gt_start))
            min_len = min(pred_len, gt_len)
            effective = intersection / min_len if min_len else 0.0
            is_match = effective >= self.config.iou_threshold
            return SpanMatch(is_match, effective, "fuzzy_asymmetric", gt_coverage, pred_coverage, iou, length_ratio)

        if strategy == MatchingStrategy.SEMI_STRICT:
            is_match = pred_start < gt_end and gt_start < pred_end
            return SpanMatch(is_match, iou, "semi_strict", gt_coverage, pred_coverage, iou, length_ratio)

        return SpanMatch(False, 0.0, "none", gt_coverage, pred_coverage, iou, length_ratio)


def _iou(pred_start: int, pred_end: int, gt_start: int, gt_end: int) -> float:
    inter_start = max(pred_start, gt_start)
    inter_end = min(pred_end, gt_end)
    if inter_start >= inter_end:
        return 0.0
    intersection = inter_end - inter_start
    union = (pred_end - pred_start) + (gt_end - gt_start) - intersection
    return intersection / union if union else 0.0


def _coverage(outer_start: int, outer_end: int, inner_start: int, inner_end: int) -> float:
    inter_start = max(outer_start, inner_start)
    inter_end = min(outer_end, inner_end)
    if inter_start >= inter_end:
        return 0.0
    intersection = inter_end - inter_start
    length = inner_end - inner_start
    return intersection / length if length else 0.0
