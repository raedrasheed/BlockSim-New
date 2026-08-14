"""Stage 8X — paired statistical analysis.

All primary protocol comparisons are **seed-paired**: for every network size N and
paired seed k we form the within-pair difference

        Delta_{N,k} = metric_PoCol(N,k) - metric_PoW(N,k)

and analyse the distribution of those differences. Grand means are never used to
manufacture a paired statistic.

Reported for every comparison: n, mean, median, SD, IQR, a 95 % confidence interval
for the mean difference (t-based) and for the median difference (bootstrap
percentile), a normality assessment (Shapiro-Wilk), a paired t-test, a Wilcoxon
signed-rank test, and both a parametric (Cohen's d_z) and a non-parametric
(matched-pairs rank-biserial correlation) effect size. The test whose assumptions
hold is named in ``recommended_test``; p-values are never reported alone.

Multiplicity: Holm-Bonferroni within each primary metric family across the five
network sizes. Sensitivity analyses (alpha cases, secondary comparators) are
labelled as such and are not folded into the primary family.
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional, Sequence

import numpy as np
from scipy import stats as sps


def _clean_pairs(x: Sequence, y: Sequence):
    """Drop pairs where either side is NA. NA is never replaced by zero."""
    xs, ys = [], []
    for a, b in zip(x, y):
        if a is None or b is None:
            continue
        fa, fb = float(a), float(b)
        if math.isnan(fa) or math.isnan(fb):
            continue
        xs.append(fa)
        ys.append(fb)
    return np.asarray(xs, dtype=float), np.asarray(ys, dtype=float)


def bootstrap_ci(values: np.ndarray, statistic=np.median, n_boot: int = 10000,
                 seed: int = 20260814, alpha: float = 0.05):
    """Percentile bootstrap CI for an arbitrary statistic of the differences."""
    if values.size == 0:
        return (None, None)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, values.size, size=(n_boot, values.size))
    boot = statistic(values[idx], axis=1)
    lo, hi = np.percentile(boot, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return float(lo), float(hi)


def paired_comparison(treatment: Sequence, control: Sequence, label: str = "",
                      n_boot: int = 10000) -> Dict:
    """Full paired analysis of ``treatment - control``."""
    t, c = _clean_pairs(treatment, control)
    n = t.size
    out: Dict[str, object] = {
        "label": label, "n_pairs": n,
        "n_dropped_na": len(list(treatment)) - n,
        "mean_treatment": float(np.mean(t)) if n else None,
        "mean_control": float(np.mean(c)) if n else None,
    }
    if n == 0:
        out["note"] = "no usable pairs"
        return out

    d = t - c
    q1, q3 = np.percentile(d, [25, 75])
    sd = float(np.std(d, ddof=1)) if n > 1 else 0.0
    mean_d = float(np.mean(d))

    out.update({
        "mean_difference": mean_d,
        "median_difference": float(np.median(d)),
        "sd_difference": sd,
        "iqr_difference": float(q3 - q1),
        "q1_difference": float(q1),
        "q3_difference": float(q3),
        "min_difference": float(np.min(d)),
        "max_difference": float(np.max(d)),
        "n_negative": int(np.sum(d < 0)),
        "n_zero": int(np.sum(d == 0)),
        "n_positive": int(np.sum(d > 0)),
    })

    # 95% CI for the mean difference (t-based)
    if n > 1 and sd > 0:
        se = sd / math.sqrt(n)
        tcrit = float(sps.t.ppf(0.975, df=n - 1))
        out["ci95_mean_low"] = mean_d - tcrit * se
        out["ci95_mean_high"] = mean_d + tcrit * se
        out["se_difference"] = se
    else:
        out["ci95_mean_low"] = out["ci95_mean_high"] = mean_d
        out["se_difference"] = 0.0

    lo, hi = bootstrap_ci(d, np.median, n_boot=n_boot)
    out["ci95_median_low"], out["ci95_median_high"] = lo, hi

    # relative effect against the control mean
    mc = float(np.mean(c))
    out["relative_difference"] = (mean_d / mc) if mc else None

    # ---- distributional assumption check ----
    if n >= 3 and np.ptp(d) > 0:
        w, p = sps.shapiro(d)
        out["shapiro_W"], out["shapiro_p"] = float(w), float(p)
        out["normality_ok"] = bool(p > 0.05)
    else:
        out["shapiro_W"] = out["shapiro_p"] = None
        out["normality_ok"] = False

    # ---- tests ----
    if n > 1 and sd > 0:
        tt = sps.ttest_rel(t, c)
        out["ttest_t"], out["ttest_p"] = float(tt.statistic), float(tt.pvalue)
    else:
        out["ttest_t"] = out["ttest_p"] = None

    if np.any(d != 0) and n > 1:
        try:
            wr = sps.wilcoxon(d, zero_method="wilcox", alternative="two-sided")
            out["wilcoxon_W"], out["wilcoxon_p"] = float(wr.statistic), float(wr.pvalue)
        except ValueError:
            out["wilcoxon_W"] = out["wilcoxon_p"] = None
    else:
        out["wilcoxon_W"] = out["wilcoxon_p"] = None
        out["note_all_zero"] = bool(np.all(d == 0))

    # ---- effect sizes ----
    out["cohen_dz"] = (mean_d / sd) if sd > 0 else None
    nz = d[d != 0]
    if nz.size:
        ranks = sps.rankdata(np.abs(nz))
        rplus = float(np.sum(ranks[nz > 0]))
        rminus = float(np.sum(ranks[nz < 0]))
        out["rank_biserial"] = (rplus - rminus) / (rplus + rminus)
    else:
        out["rank_biserial"] = 0.0

    out["recommended_test"] = ("paired t-test" if out["normality_ok"]
                               else "Wilcoxon signed-rank")
    out["recommended_p"] = (out["ttest_p"] if out["normality_ok"]
                            else out["wilcoxon_p"])
    return out


def holm_correction(pvalues: Sequence[Optional[float]]) -> List[Optional[float]]:
    """Holm-Bonferroni adjusted p-values; ``None`` entries pass through."""
    idx = [i for i, p in enumerate(pvalues) if p is not None]
    if not idx:
        return list(pvalues)
    m = len(idx)
    order = sorted(idx, key=lambda i: pvalues[i])
    adj: Dict[int, float] = {}
    running = 0.0
    for rank, i in enumerate(order):
        val = (m - rank) * float(pvalues[i])
        running = max(running, val)
        adj[i] = min(1.0, running)
    return [adj.get(i) if i in adj else None for i in range(len(pvalues))]


def describe(values: Sequence) -> Dict:
    """Univariate summary with a 95 % CI of the mean (NA-safe)."""
    v = np.asarray([float(x) for x in values
                    if x is not None and not (isinstance(x, float) and math.isnan(x))],
                   dtype=float)
    if v.size == 0:
        return {"n": 0, "mean": None, "median": None, "sd": None,
                "ci95_low": None, "ci95_high": None, "min": None, "max": None,
                "p95": None, "iqr": None}
    sd = float(np.std(v, ddof=1)) if v.size > 1 else 0.0
    mean = float(np.mean(v))
    if v.size > 1 and sd > 0:
        half = float(sps.t.ppf(0.975, df=v.size - 1)) * sd / math.sqrt(v.size)
    else:
        half = 0.0
    q1, q3 = np.percentile(v, [25, 75])
    return {
        "n": int(v.size), "mean": mean, "median": float(np.median(v)), "sd": sd,
        "ci95_low": mean - half, "ci95_high": mean + half,
        "min": float(np.min(v)), "max": float(np.max(v)),
        "p95": float(np.percentile(v, 95)), "iqr": float(q3 - q1),
    }
