"""Span matching strategies and statistical utilities for PII evaluation."""

from benchmarks.matching.strategies import (
    MatchingConfig,
    MatchingStrategy,
    SpanMatch,
    SpanMatcher,
)
from benchmarks.matching.statistics import (
    ConfidenceInterval,
    bootstrap_ci_entity_level,
    bootstrap_ci_sample_level,
)

__all__ = [
    "MatchingConfig",
    "MatchingStrategy",
    "SpanMatch",
    "SpanMatcher",
    "ConfidenceInterval",
    "bootstrap_ci_entity_level",
    "bootstrap_ci_sample_level",
]
