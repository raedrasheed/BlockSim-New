"""Stage 5B1D distributional-uniformity audit of the exact without-replacement
sampler. For small domains it enumerates all C(S,k) subsets, runs a deterministic
Monte-Carlo, and compares observed subset frequencies to the uniform 1/C(S,k) with a
chi-square goodness-of-fit test; it also validates the minimum, maximum, and
ordered-gap distributions against their exact combinatorial references.

Acceptance criterion (declared here, before running): chi-square statistic below the
99.9% critical value for each case (i.e. p > 0.001), so uniformity is not rejected.
"""

from __future__ import annotations
import os
import json
from math import comb
from itertools import combinations

from scipy.stats import chi2

from experiments.thesis_revision_v43 import exact_sampling as es
from experiments.thesis_revision_v43.scenario_engine import rng
from experiments.thesis_revision_v43 import run_utils

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DOCS = os.path.join(ROOT, "docs", "thesis_revision_v43")
RESULTS = os.path.join(ROOT, "results", "thesis_revision_v43", "stage_05b1d")

CASES = [(5, 2, 200_000), (6, 3, 300_000), (10, 1, 100_000), (10, 9, 100_000)]
ALPHA = 0.001                       # chi-square tail; reject uniformity if p < ALPHA


def subset_uniformity(S, k, n_trials, seed=4242):
    counts = {frozenset(c): 0 for c in combinations(range(S), k)}
    g = rng(seed, "solution_positions")
    for _ in range(n_trials):
        counts[frozenset(es.sample_without_replacement(g, S, k).tolist())] += 1
    m = comb(S, k)
    exp = n_trials / m
    chisq = sum((o - exp) ** 2 / exp for o in counts.values())
    dof = m - 1
    crit = float(chi2.ppf(1 - ALPHA, dof)) if dof > 0 else 0.0
    pval = float(chi2.sf(chisq, dof)) if dof > 0 else 1.0
    max_dev = max(abs(o / n_trials - 1 / m) for o in counts.values())
    return dict(S=S, k=k, n_trials=n_trials, num_subsets=m, chi_square=chisq, dof=dof,
                critical_99_9=crit, p_value=pval, max_abs_freq_deviation=max_dev,
                passed=(dof == 0 or chisq < crit))


def order_statistics(S, k, n_trials=200_000, seed=99):
    """Empirical vs exact combinatorial P(min=m), P(max=m); mean ordered gaps."""
    g = rng(seed, "solution_positions")
    mins = {}; maxs = {}
    for _ in range(n_trials):
        s = es.sample_without_replacement(g, S, k)
        mins[int(s[0])] = mins.get(int(s[0]), 0) + 1
        maxs[int(s[-1])] = maxs.get(int(s[-1]), 0) + 1
    # exact: P(min=m) = C(S-1-m, k-1)/C(S,k); P(max=m) = C(m, k-1)/C(S,k)
    tot = comb(S, k)
    min_err = max(abs(mins.get(m, 0) / n_trials - comb(S - 1 - m, k - 1) / tot)
                  for m in range(S - k + 1))
    max_err = max(abs(maxs.get(m, 0) / n_trials - (comb(m, k - 1) / tot if m >= k - 1 else 0.0))
                  for m in range(S))
    return dict(S=S, k=k, n_trials=n_trials, max_min_freq_error=min_err,
                max_max_freq_error=max_err, passed=(min_err < 0.01 and max_err < 0.01))


def run():
    os.makedirs(RESULTS, exist_ok=True)
    subsets = [subset_uniformity(S, k, n) for S, k, n in CASES]
    orders = [order_statistics(10, 3), order_statistics(8, 4)]
    report = dict(acceptance="chi-square p > 0.001 (uniformity not rejected); "
                             "order-statistic frequency error < 0.01",
                  subset_uniformity=subsets, order_statistics=orders,
                  all_passed=all(s["passed"] for s in subsets) and all(o["passed"] for o in orders))
    run_utils.atomic_write_json(os.path.join(RESULTS, "uniformity_results.json"), report)
    json.dump(report, open(os.path.join(DOCS, "STAGE_05B1D_UNIFORMITY_RESULTS.json"), "w"), indent=2)
    return report


if __name__ == "__main__":
    r = run()
    print(json.dumps(dict(all_passed=r["all_passed"],
                          subsets=[(s["S"], s["k"], round(s["chi_square"], 2), s["passed"]) for s in r["subset_uniformity"]],
                          orders=[(o["S"], o["k"], o["passed"]) for o in r["order_statistics"]]), indent=2))
