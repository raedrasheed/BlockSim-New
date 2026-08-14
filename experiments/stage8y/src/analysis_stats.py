"""Stage 8Y — paired statistical analysis.

Seeds are matched, so every primary comparison is paired: for each
(composition, N, seed k) we form Delta = metric_PoCol - metric_PoW and analyse the
distribution of differences. Grand means are never used to build a paired statistic.

Reported per comparison: n, mean, median, SD, IQR, a t-based 95 % CI for the mean
difference, a **paired bootstrap** percentile CI (the robust alternative the brief
prefers), a Shapiro-Wilk normality check, a paired t-test, a Wilcoxon signed-rank
test, Cohen's d_z, and the matched-pairs rank-biserial correlation. Holm correction
is applied across the predefined primary comparisons. Magnitude is reported first;
p-values are never reported alone.

For the central questions the analysis estimates a CI around the quantity itself
(EnergySaving, BlockRetention) and asks whether the relevant bound clears the
preregistered threshold — a one-sided assessment against 0.50 / 0.90 / 0.95.
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional, Sequence

import numpy as np
from scipy import stats as sps

BOOT_SEED = 20260814
N_BOOT = 10000


def _clean(x: Sequence) -> np.ndarray:
    out = []
    for v in x:
        if v is None:
            continue
        f = float(v)
        if math.isnan(f):
            continue
        out.append(f)
    return np.asarray(out, dtype=float)


def _clean_pairs(a: Sequence, b: Sequence):
    xs, ys = [], []
    for u, v in zip(a, b):
        if u is None or v is None:
            continue
        fu, fv = float(u), float(v)
        if math.isnan(fu) or math.isnan(fv):
            continue
        xs.append(fu)
        ys.append(fv)
    return np.asarray(xs, dtype=float), np.asarray(ys, dtype=float)


def bootstrap_ci(values: np.ndarray, statistic=np.mean, n_boot: int = N_BOOT,
                 seed: int = BOOT_SEED, alpha: float = 0.05):
    if values.size == 0:
        return (None, None)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, values.size, size=(n_boot, values.size))
    boot = statistic(values[idx], axis=1)
    lo, hi = np.percentile(boot, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return float(lo), float(hi)


def describe(values: Sequence, threshold: float = None) -> Dict:
    """Univariate summary with t-based and bootstrap CIs, plus a threshold verdict."""
    v = _clean(values)
    if v.size == 0:
        return {"n": 0, "mean": None, "median": None, "sd": None, "ci95_low": None,
                "ci95_high": None, "boot_ci95_low": None, "boot_ci95_high": None,
                "min": None, "max": None, "iqr": None, "p95": None}
    sd = float(np.std(v, ddof=1)) if v.size > 1 else 0.0
    mean = float(np.mean(v))
    half = (float(sps.t.ppf(0.975, df=v.size - 1)) * sd / math.sqrt(v.size)
            if v.size > 1 and sd > 0 else 0.0)
    q1, q3 = np.percentile(v, [25, 75])
    blo, bhi = bootstrap_ci(v, np.mean)
    out = {
        "n": int(v.size), "mean": mean, "median": float(np.median(v)), "sd": sd,
        "ci95_low": mean - half, "ci95_high": mean + half,
        "boot_ci95_low": blo, "boot_ci95_high": bhi,
        "min": float(np.min(v)), "max": float(np.max(v)),
        "iqr": float(q3 - q1), "p95": float(np.percentile(v, 95)),
    }
    if threshold is not None:
        out["threshold"] = threshold
        out["mean_exceeds_threshold"] = bool(mean > threshold)
        out["ci_lower_exceeds_threshold"] = bool((mean - half) > threshold)
        out["boot_ci_lower_exceeds_threshold"] = bool(blo is not None and blo > threshold)
        out["fraction_of_seeds_exceeding"] = float(np.mean(v > threshold))
        if v.size > 1 and sd > 0:
            t = (mean - threshold) / (sd / math.sqrt(v.size))
            out["one_sided_t"] = float(t)
            out["one_sided_p_greater"] = float(sps.t.sf(t, df=v.size - 1))
        else:
            out["one_sided_t"] = out["one_sided_p_greater"] = None
    return out


def paired_comparison(treatment: Sequence, control: Sequence, label: str = "") -> Dict:
    """Full paired analysis of ``treatment - control``."""
    t, c = _clean_pairs(treatment, control)
    n = t.size
    out: Dict = {"label": label, "n_pairs": n,
                 "n_dropped_na": len(list(treatment)) - n}
    if n == 0:
        out["note"] = "no usable pairs"
        return out
    d = t - c
    sd = float(np.std(d, ddof=1)) if n > 1 else 0.0
    mean_d = float(np.mean(d))
    q1, q3 = np.percentile(d, [25, 75])
    out.update({
        "mean_control": float(np.mean(c)), "mean_treatment": float(np.mean(t)),
        "mean_difference": mean_d, "median_difference": float(np.median(d)),
        "sd_difference": sd, "iqr_difference": float(q3 - q1),
        "q1_difference": float(q1), "q3_difference": float(q3),
        "min_difference": float(np.min(d)), "max_difference": float(np.max(d)),
        "n_negative": int(np.sum(d < 0)), "n_zero": int(np.sum(d == 0)),
        "n_positive": int(np.sum(d > 0)),
        "relative_difference": (mean_d / float(np.mean(c))) if np.mean(c) else None,
    })
    if n > 1 and sd > 0:
        se = sd / math.sqrt(n)
        tc = float(sps.t.ppf(0.975, df=n - 1))
        out["ci95_mean_low"], out["ci95_mean_high"] = mean_d - tc * se, mean_d + tc * se
        out["se_difference"] = se
    else:
        out["ci95_mean_low"] = out["ci95_mean_high"] = mean_d
        out["se_difference"] = 0.0
    blo, bhi = bootstrap_ci(d, np.mean)
    out["boot_ci95_low"], out["boot_ci95_high"] = blo, bhi
    mlo, mhi = bootstrap_ci(d, np.median)
    out["boot_ci95_median_low"], out["boot_ci95_median_high"] = mlo, mhi

    if n >= 3 and np.ptp(d) > 0:
        w, p = sps.shapiro(d)
        out["shapiro_W"], out["shapiro_p"] = float(w), float(p)
        out["normality_ok"] = bool(p > 0.05)
    else:
        out["shapiro_W"] = out["shapiro_p"] = None
        out["normality_ok"] = False

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

    out["cohen_dz"] = (mean_d / sd) if sd > 0 else None
    nz = d[d != 0]
    if nz.size:
        ranks = sps.rankdata(np.abs(nz))
        rp = float(np.sum(ranks[nz > 0]))
        rm = float(np.sum(ranks[nz < 0]))
        out["rank_biserial"] = (rp - rm) / (rp + rm)
    else:
        out["rank_biserial"] = 0.0
    out["recommended_test"] = ("paired t-test" if out["normality_ok"]
                               else "Wilcoxon signed-rank")
    out["recommended_p"] = (out["ttest_p"] if out["normality_ok"]
                            else out["wilcoxon_p"])
    return out


def holm(pvalues: Sequence[Optional[float]]) -> List[Optional[float]]:
    """Holm-Bonferroni adjusted p-values; None entries pass through untouched."""
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
    return [adj.get(i) for i in range(len(pvalues))]


def pareto_front(points: List[Dict], x_key: str, y_key: str) -> List[Dict]:
    """Maximal points under (higher x, higher y) dominance.

    A point is Pareto-optimal when no other point is at least as good on both axes
    and strictly better on one.
    """
    usable = [p for p in points if p.get(x_key) is not None and p.get(y_key) is not None]
    front = []
    for p in usable:
        dominated = any(
            (o[x_key] >= p[x_key] and o[y_key] >= p[y_key]
             and (o[x_key] > p[x_key] or o[y_key] > p[y_key]))
            for o in usable if o is not p)
        if not dominated:
            front.append(p)
    return sorted(front, key=lambda p: (-p[x_key], -p[y_key]))
