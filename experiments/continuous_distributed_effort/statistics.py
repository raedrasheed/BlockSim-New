"""Statistics for the continuous distributed-effort experiment.

numpy only. Bootstrap CIs use a fixed RNG seed so results are reproducible.
Equivalence is tested with a TOST-style bootstrap: the 90% bootstrap CI of the
paired mean difference must lie entirely within a PRE-REGISTERED margin
(equivalent to two one-sided tests at alpha=0.05).
"""
from __future__ import annotations

import numpy as np

_BOOT_SEED = 20240718
_N_BOOT = 2000


def _clean(x):
    x = np.asarray(list(x), dtype=float)
    return x[~np.isnan(x)]


def _bootstrap_ci(x, stat=np.mean, n_boot=_N_BOOT, alpha=0.05, seed=_BOOT_SEED):
    x = _clean(x)
    if len(x) < 2:
        return (float("nan"), float("nan"))
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(x), size=(n_boot, len(x)))
    boots = stat(x[idx], axis=1)
    lo = float(np.percentile(boots, 100 * alpha / 2))
    hi = float(np.percentile(boots, 100 * (1 - alpha / 2)))
    return (lo, hi)


def summarize(values):
    x = _clean(values)
    n = int(len(x))
    if n == 0:
        keys = ["n", "mean", "median", "std", "p2_5", "p97_5",
                "boot_ci_low", "boot_ci_high", "min", "max"]
        return {k: (0 if k == "n" else float("nan")) for k in keys}
    lo, hi = _bootstrap_ci(x)
    return dict(
        n=n, mean=float(np.mean(x)), median=float(np.median(x)),
        std=float(np.std(x, ddof=1)) if n > 1 else 0.0,
        p2_5=float(np.percentile(x, 2.5)), p97_5=float(np.percentile(x, 97.5)),
        boot_ci_low=lo, boot_ci_high=hi,
        min=float(np.min(x)), max=float(np.max(x)),
    )


def paired_diff(a, b):
    """Paired stats on d = b - a (same seed order). Negative mean => b < a."""
    a = np.asarray(list(a), dtype=float)
    b = np.asarray(list(b), dtype=float)
    d = b - a
    d = d[~np.isnan(d)]
    if len(d) == 0:
        return dict(n=0, mean_diff=float("nan"), median_diff=float("nan"),
                    cohens_d=float("nan"), boot_ci_low=float("nan"), boot_ci_high=float("nan"))
    sd = np.std(d, ddof=1) if len(d) > 1 else 0.0
    lo, hi = _bootstrap_ci(d)
    return dict(
        n=int(len(d)), mean_diff=float(np.mean(d)), median_diff=float(np.median(d)),
        cohens_d=float(np.mean(d) / sd) if sd else float("nan"),
        boot_ci_low=lo, boot_ci_high=hi,
    )


def tost_equivalence(a, b, margin, alpha=0.05):
    """TOST-style equivalence on d = b - a via bootstrap. `margin` is PRE-REGISTERED
    (set before inspecting the data). Equivalent iff the (1-2*alpha) bootstrap CI of
    mean(d) lies entirely within [-margin, +margin]."""
    a = np.asarray(list(a), dtype=float)
    b = np.asarray(list(b), dtype=float)
    d = b - a
    d = d[~np.isnan(d)]
    if len(d) < 2:
        return dict(equivalent=False, margin=margin, ci_low=float("nan"),
                    ci_high=float("nan"), mean_diff=float("nan"))
    # (1 - 2*alpha) CI is the TOST-equivalent interval
    lo, hi = _bootstrap_ci(d, alpha=2 * alpha)
    return dict(
        equivalent=bool(lo > -margin and hi < margin),
        margin=float(margin), ci_low=lo, ci_high=hi, mean_diff=float(np.mean(d)),
    )
