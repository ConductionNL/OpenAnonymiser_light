"""Statistical utilities for benchmark evaluation.

Provides bootstrap confidence intervals for precision, recall, and F1,
computed at the sample level to preserve within-sentence correlations.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class ConfidenceInterval:
    point_estimate: float
    ci_lower: float
    ci_upper: float
    n_bootstrap: int
    alpha: float

    @property
    def width(self) -> float:
        return self.ci_upper - self.ci_lower

    def __str__(self) -> str:
        return f"{self.point_estimate:.3f} [{self.ci_lower:.3f}, {self.ci_upper:.3f}]"


def bootstrap_ci_sample_level(
    per_sample_counts: list[tuple[int, int, int]],
    n_bootstrap: int = 10_000,
    alpha: float = 0.05,
    seed: int = 42,
) -> dict[str, ConfidenceInterval]:
    rng = np.random.default_rng(seed)
    n = len(per_sample_counts)
    if n == 0:
        zero_ci = ConfidenceInterval(0.0, 0.0, 0.0, n_bootstrap, alpha)
        return {"precision": zero_ci, "recall": zero_ci, "f1": zero_ci}

    prec_estimates = np.empty(n_bootstrap)
    rec_estimates = np.empty(n_bootstrap)
    f1_estimates = np.empty(n_bootstrap)

    counts = np.array(per_sample_counts, dtype=np.int64)
    indices = rng.integers(0, n, size=(n_bootstrap, n))

    for b in range(n_bootstrap):
        idx = indices[b]
        total_tp = int(counts[idx, 0].sum())
        total_fp = int(counts[idx, 1].sum())
        total_fn = int(counts[idx, 2].sum())

        p = total_tp / (total_tp + total_fp) if (total_tp + total_fp) else 0.0
        r = total_tp / (total_tp + total_fn) if (total_tp + total_fn) else 0.0
        f1 = 2 * p * r / (p + r) if (p + r) else 0.0

        prec_estimates[b] = p
        rec_estimates[b] = r
        f1_estimates[b] = f1

    def _ci(estimates: np.ndarray, point_estimate: float) -> ConfidenceInterval:
        lower = float(np.percentile(estimates, 100 * alpha / 2))
        upper = float(np.percentile(estimates, 100 * (1 - alpha / 2)))
        return ConfidenceInterval(
            point_estimate=point_estimate,
            ci_lower=lower,
            ci_upper=upper,
            n_bootstrap=n_bootstrap,
            alpha=alpha,
        )

    total_tp = int(counts[:, 0].sum())
    total_fp = int(counts[:, 1].sum())
    total_fn = int(counts[:, 2].sum())
    p_obs = total_tp / (total_tp + total_fp) if (total_tp + total_fp) else 0.0
    r_obs = total_tp / (total_tp + total_fn) if (total_tp + total_fn) else 0.0
    f1_obs = 2 * p_obs * r_obs / (p_obs + r_obs) if (p_obs + r_obs) else 0.0

    return {
        "precision": _ci(prec_estimates, p_obs),
        "recall": _ci(rec_estimates, r_obs),
        "f1": _ci(f1_estimates, f1_obs),
    }


def bootstrap_ci_entity_level(
    tp: int,
    fp: int,
    fn: int,
    n_bootstrap: int = 10_000,
    alpha: float = 0.05,
    seed: int = 42,
) -> dict[str, ConfidenceInterval]:
    rng = np.random.default_rng(seed)

    prec_outcomes = np.array([1] * tp + [0] * fp) if (tp + fp) else np.array([])
    rec_outcomes = np.array([1] * tp + [0] * fn) if (tp + fn) else np.array([])

    if len(prec_outcomes) == 0 and len(rec_outcomes) == 0:
        zero_ci = ConfidenceInterval(0.0, 0.0, 0.0, n_bootstrap, alpha)
        return {"precision": zero_ci, "recall": zero_ci, "f1": zero_ci}

    prec_estimates = np.empty(n_bootstrap)
    rec_estimates = np.empty(n_bootstrap)
    f1_estimates = np.empty(n_bootstrap)

    for b in range(n_bootstrap):
        p = float(rng.choice(prec_outcomes, size=len(prec_outcomes), replace=True).mean()) if len(prec_outcomes) else 0.0
        r = float(rng.choice(rec_outcomes, size=len(rec_outcomes), replace=True).mean()) if len(rec_outcomes) else 0.0
        f1 = 2 * p * r / (p + r) if (p + r) else 0.0
        prec_estimates[b] = p
        rec_estimates[b] = r
        f1_estimates[b] = f1

    p_obs = tp / (tp + fp) if (tp + fp) else 0.0
    r_obs = tp / (tp + fn) if (tp + fn) else 0.0
    f1_obs = 2 * p_obs * r_obs / (p_obs + r_obs) if (p_obs + r_obs) else 0.0

    def _ci(estimates: np.ndarray, point_estimate: float) -> ConfidenceInterval:
        lower = float(np.percentile(estimates, 100 * alpha / 2))
        upper = float(np.percentile(estimates, 100 * (1 - alpha / 2)))
        return ConfidenceInterval(
            point_estimate=point_estimate,
            ci_lower=lower,
            ci_upper=upper,
            n_bootstrap=n_bootstrap,
            alpha=alpha,
        )

    return {
        "precision": _ci(prec_estimates, p_obs),
        "recall": _ci(rec_estimates, r_obs),
        "f1": _ci(f1_estimates, f1_obs),
    }
