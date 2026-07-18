"""Statistics helpers for the stochastic nonce-partition experiment.

numpy only (no scipy). 95% CI uses the normal approximation and is labelled as
such. Paired effect size is Cohen's d for paired samples = mean(diff)/std(diff).
"""
from __future__ import annotations

import math
import numpy as np


def summarize(values):
    """mean/median/std/95% CI (normal approx)/min/max/n for a 1-D sample."""
    x = np.asarray(list(values), dtype=float)
    x = x[~np.isnan(x)]
    n = int(len(x))
    if n == 0:
        return dict(n=0, mean=float("nan"), median=float("nan"), std=float("nan"),
                    ci95_low=float("nan"), ci95_high=float("nan"),
                    min=float("nan"), max=float("nan"))
    mean = float(np.mean(x))
    std = float(np.std(x, ddof=1)) if n > 1 else 0.0
    se = std / math.sqrt(n) if n > 1 else 0.0
    return dict(
        n=n, mean=mean, median=float(np.median(x)), std=std,
        ci95_low=mean - 1.96 * se, ci95_high=mean + 1.96 * se,
        min=float(np.min(x)), max=float(np.max(x)),
    )


def paired_cohens_d(a, b):
    """Cohen's d for paired samples on (b - a): mean(diff)/std(diff).

    Negative d means b (e.g. PoCol) is smaller than a (baseline).
    """
    a = np.asarray(list(a), dtype=float)
    b = np.asarray(list(b), dtype=float)
    diff = b - a
    diff = diff[~np.isnan(diff)]
    if len(diff) < 2 or np.std(diff, ddof=1) == 0:
        return float("nan")
    return float(np.mean(diff) / np.std(diff, ddof=1))


def exhaustion_probability(solution_found_flags):
    """Fraction of runs that exhausted the domain (no solution found)."""
    flags = list(solution_found_flags)
    if not flags:
        return float("nan")
    return sum(1 for f in flags if not f) / len(flags)
