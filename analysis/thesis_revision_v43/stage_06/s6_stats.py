#!/usr/bin/env python3
"""Stage 6 — statistics library (paired inference, effect sizes, intervals, multiplicity).

All randomness uses an explicit numpy Generator seeded from a recorded constant; there is
no reliance on a global default RNG. Deterministic given the same inputs and seeds.

Design notes tied to the Stage-6 approval:
- Paired analyses operate on seed-matched difference vectors (§6, §9).
- For a degenerate difference vector (all differences identical), the paired
  permutation/bootstrap are structurally uninformative; we flag `deterministic=True`
  and report the exact constant difference rather than dressing a design identity as an
  empirical test (§9, §18).
"""
import numpy as np
from scipy import stats as sps


def describe(x):
    """Distribution-free + moment descriptives for a 1-D array (finite values only)."""
    a = np.asarray([v for v in x if v is not None and np.isfinite(v)], dtype=float)
    n = int(a.size)
    d = {"n": n}
    if n == 0:
        d.update(mean=None, sd=None, median=None, q1=None, q3=None, iqr=None,
                 min=None, max=None, ci_lo=None, ci_hi=None)
        return d
    d["mean"] = float(np.mean(a))
    d["sd"] = float(np.std(a, ddof=1)) if n > 1 else 0.0
    d["median"] = float(np.median(a))
    q1, q3 = (float(np.percentile(a, 25)), float(np.percentile(a, 75)))
    d["q1"], d["q3"], d["iqr"] = q1, q3, q3 - q1
    d["min"], d["max"] = float(np.min(a)), float(np.max(a))
    lo, hi = bootstrap_ci_mean(a, seed=6060600)
    d["ci_lo"], d["ci_hi"] = lo, hi
    return d


def bootstrap_ci_mean(x, seed, n_boot=10000, level=0.95):
    a = np.asarray(x, dtype=float)
    n = a.size
    if n == 0:
        return (None, None)
    if n == 1 or np.ptp(a) == 0:
        return (float(a[0]) if n >= 1 else None, float(a[0]) if n >= 1 else None)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, n, size=(n_boot, n))
    boots = a[idx].mean(axis=1)
    alpha = 1 - level
    return (float(np.quantile(boots, alpha / 2)), float(np.quantile(boots, 1 - alpha / 2)))


def paired_diff(a, b):
    """b - a element-wise on seed-matched arrays."""
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    assert a.shape == b.shape
    return b - a


def bootstrap_ci_paired(diff, seed, n_boot=10000, level=0.95):
    d = np.asarray(diff, dtype=float)
    n = d.size
    if n == 0:
        return (None, None)
    if np.ptp(d) == 0:
        return (float(d[0]), float(d[0]))
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, n, size=(n_boot, n))
    boots = d[idx].mean(axis=1)
    alpha = 1 - level
    return (float(np.quantile(boots, alpha / 2)), float(np.quantile(boots, 1 - alpha / 2)))


def paired_permutation_p(diff, seed, n_perm=10000):
    """Two-sided sign-flip permutation test on paired differences (H0: symmetric about 0).
    Returns (p_value, deterministic_flag). For an all-equal difference vector the test is
    structurally uninformative (returns p=None, deterministic=True)."""
    d = np.asarray(diff, dtype=float)
    n = d.size
    if n == 0:
        return (None, False)
    if np.ptp(d) == 0:
        # all differences identical: design-deterministic, not an empirical test
        return (None, True)
    obs = abs(np.mean(d))
    rng = np.random.default_rng(seed)
    signs = rng.choice(np.array([-1.0, 1.0]), size=(n_perm, n))
    stat = np.abs((signs * d).mean(axis=1))
    # +1 correction (include observed)
    p = (np.sum(stat >= obs - 1e-15) + 1) / (n_perm + 1)
    return (float(min(1.0, p)), False)


def wilcoxon_signed_rank(diff):
    d = np.asarray(diff, dtype=float)
    nz = d[d != 0]
    if nz.size == 0:
        return {"stat": None, "p": None, "note": "all-zero differences"}
    try:
        w = sps.wilcoxon(nz, alternative="two-sided", zero_method="wilcox", method="auto")
        return {"stat": float(w.statistic), "p": float(w.pvalue), "n_nonzero": int(nz.size)}
    except Exception as e:  # pragma: no cover
        return {"stat": None, "p": None, "note": str(e)}


def hodges_lehmann_paired(diff):
    """Hodges-Lehmann paired location shift = median of Walsh averages of the differences."""
    d = np.asarray(diff, dtype=float)
    n = d.size
    if n == 0:
        return None
    i, j = np.triu_indices(n, k=0)
    walsh = (d[i] + d[j]) / 2.0
    return float(np.median(walsh))


def paired_effect(a, b, seed_boot):
    """Full paired effect-size bundle for b vs a (seed-matched)."""
    d = paired_diff(a, b)
    n = d.size
    md = float(np.mean(d))
    sd = float(np.std(d, ddof=1)) if n > 1 else 0.0
    dz = float(md / sd) if sd > 0 else None
    hl = hodges_lehmann_paired(d)
    lo, hi = bootstrap_ci_paired(d, seed=seed_boot)
    mean_a = float(np.mean(a))
    rel = float(md / mean_a) if mean_a != 0 else None
    return {
        "n_pairs": int(n),
        "mean_diff": md,          # b - a, scientific units
        "median_diff_hl": hl,     # Hodges-Lehmann
        "sd_diff": sd,
        "dz": dz,                 # standardized paired effect
        "rel_change_vs_a": rel,   # None when reference mean is 0 (avoid /0)
        "boot_ci_lo": lo,
        "boot_ci_hi": hi,
        "deterministic": bool(np.ptp(d) == 0),
    }


def wilson_ci(k, n, level=0.95):
    if n == 0:
        return (None, None)
    z = sps.norm.ppf(1 - (1 - level) / 2)
    p = k / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = (z / denom) * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (float(center - half), float(center + half))


def rule_of_three(n):
    return 3.0 / n if n > 0 else None


def clopper_pearson(k, n, level=0.95):
    if n == 0:
        return (None, None)
    alpha = 1 - level
    lo = 0.0 if k == 0 else float(sps.beta.ppf(alpha / 2, k, n - k + 1))
    hi = 1.0 if k == n else float(sps.beta.ppf(1 - alpha / 2, k + 1, n - k))
    return (lo, hi)


def holm(pvalues):
    """Holm step-down adjusted p-values. Input: list of (label, p). p=None passes through.
    Returns list of dicts with raw and adjusted p, preserving input order."""
    idx = [(i, lbl, p) for i, (lbl, p) in enumerate(pvalues) if p is not None]
    m = len(idx)
    order = sorted(idx, key=lambda t: t[2])
    adj = {}
    running = 0.0
    for rank, (i, lbl, p) in enumerate(order):
        a = (m - rank) * p
        running = max(running, a)
        adj[i] = min(1.0, running)
    out = []
    for i, (lbl, p) in enumerate(pvalues):
        out.append({"label": lbl, "p_raw": p,
                    "p_holm": (adj[i] if i in adj else None),
                    "family_size": m})
    return out
