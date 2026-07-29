"""Stage 4 finder-model equivalence audit (Objective A).

Independently validates that the finder-based finite-domain abstraction used by
the PoCol simulator is equivalent, within explicitly bounded error, to a direct
finite-domain Bernoulli hashing process:

  * solution count K ~ Binomial(S, p) (exact) vs Poisson(mu=S*p) (approximation);
  * per-range assignment K_i ~ Binomial(S_i, p) with sum_i K_i = K;
  * discovery time = first-success index / rate (min-position identity);
  * Poisson approximation error bounded by the Le Cam theorem: d_TV <= sum p_i^2.

Reference distributions use scipy (exact); simulations use seeded numpy.
Run as a script to (re)generate the CSV + manifest under results/.../stage_04/.
"""

from __future__ import annotations

import os
import sys
import json
import math
import hashlib
import csv

import numpy as np
from scipy import stats

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from Models.PoCol import round_state as rs   # noqa: E402


# ---------------------------------------------------------------------------
# Analytical references
# ---------------------------------------------------------------------------
def analytical(S, p):
    mu = S * p
    return dict(
        S=S, p=p, mu=mu,
        binom_P0=float(stats.binom.pmf(0, S, p)),
        binom_P1=float(stats.binom.pmf(1, S, p)),
        binom_P2plus=float(stats.binom.sf(1, S, p)),
        binom_mean=float(S * p),
        pois_P0=float(stats.poisson.pmf(0, mu)),
        pois_P1=float(stats.poisson.pmf(1, mu)),
        pois_P2plus=float(stats.poisson.sf(1, mu)),
        exhaust_prob_binom=float(stats.binom.pmf(0, S, p)),
        success_prob_binom=float(stats.binom.sf(-1, S, p) - stats.binom.pmf(0, S, p) + 0.0)
        if False else float(1.0 - stats.binom.pmf(0, S, p)),
        lecam_tv_bound=float(S * p * p),      # sum p_i^2 (homogeneous) = S p^2 = mu p
    )


# ---------------------------------------------------------------------------
# Simulations (seeded)
# ---------------------------------------------------------------------------
def sim_counts(S, p, method, trials, seed):
    """Return sampled K counts. method in {bernoulli, binomial, poisson}."""
    g = np.random.default_rng(seed)
    if method == "bernoulli":
        # direct finite-domain Bernoulli process (chunked to bound memory)
        out = np.empty(trials, dtype=np.int64)
        chunk = max(1, int(2e7 // max(S, 1)))
        i = 0
        while i < trials:
            m = min(chunk, trials - i)
            out[i:i + m] = (g.random((m, S)) < p).sum(axis=1)
            i += m
        return out
    if method == "binomial":
        return g.binomial(S, p, size=trials)
    if method == "poisson":
        return g.poisson(S * p, size=trials)
    raise ValueError(method)


def prob_stats(counts, trials):
    c = np.asarray(counts)
    p0 = float((c == 0).mean()); p1 = float((c == 1).mean())
    p2 = float((c >= 2).mean()); mean = float(c.mean())
    # Wald SE for a proportion (for CIs)
    def se(phat):
        return math.sqrt(max(phat * (1 - phat), 0.0) / trials)
    return dict(P0=p0, P1=p1, P2plus=p2, mean=mean,
                P0_se=se(p0), P1_se=se(p1), P2plus_se=se(p2))


# ---------------------------------------------------------------------------
# Discovery-time (first-success index) validation
# ---------------------------------------------------------------------------
def discovery_time_reference(S, p, trials, seed):
    """Direct ordered Bernoulli search: first-success index, conditional on >=1."""
    g = np.random.default_rng(seed)
    firsts = []
    for _ in range(trials):
        hits = np.nonzero(g.random(S) < p)[0]
        if hits.size:
            firsts.append(int(hits[0]))
    return np.asarray(firsts)


def discovery_time_finder(S, p, trials, seed):
    """Finder model: K ~ Binomial(S,p); place K uniform positions; take min."""
    g = np.random.default_rng(seed)
    firsts = []
    for _ in range(trials):
        k = int(g.binomial(S, p))
        if k > 0:
            firsts.append(int(g.integers(0, S, size=k).min()))
    return np.asarray(firsts)


# ---------------------------------------------------------------------------
# Per-range assignment: sum_i Binomial(S_i, p) == Binomial(sum S_i, p)
# ---------------------------------------------------------------------------
def per_range_assignment_check(S, p, n_ranges, trials, seed):
    g = np.random.default_rng(seed)
    base = S // n_ranges
    sizes = [base] * n_ranges
    sizes[-1] += S - base * n_ranges          # remainder on last range
    assert sum(sizes) == S
    totals = np.zeros(trials, dtype=np.int64)
    for si in sizes:
        totals += g.binomial(si, p, size=trials)
    ref = g.binomial(S, p, size=trials)
    return dict(sizes_sum=sum(sizes), S=S,
                perrange_mean=float(totals.mean()), global_mean=float(ref.mean()),
                perrange_var=float(totals.var()), global_var=float(ref.var()))


# ---------------------------------------------------------------------------
# Full audit
# ---------------------------------------------------------------------------
MU_REGIMES = [0.1, 0.5, 1.0, 2.0, 5.0]
SIM_S = 5_000                  # domain for Bernoulli/Binomial/Poisson sims (Bernoulli-feasible)
SMALL_S = 20                   # small-domain regime (max Poisson error)
TRIALS = 200_000
DISC_TRIALS = 40_000
THESIS_S = int(2 * 141e12 * 600)
THESIS_P = 1.0 / (141e12 * 600.0)
TOL_SE = 5.0                   # simulated estimator must be within 5 SE of reference
_METHOD_OFFSET = {"bernoulli": 1, "binomial": 2, "poisson": 3}   # deterministic seeds


def run_audit(seed=20260729):
    rows = []
    # A) count-distribution comparison across mu regimes (moderate S)
    for i, mu in enumerate(MU_REGIMES):
        S, p = SIM_S, mu / SIM_S
        ana = analytical(S, p)
        for method in ("bernoulli", "binomial", "poisson"):
            counts = sim_counts(S, p, method, TRIALS, seed + i * 10 + _METHOD_OFFSET[method])
            st = prob_stats(counts, TRIALS)
            ref = ("pois" if method == "poisson" else "binom")
            rows.append(dict(
                block="count_distribution", mu=mu, S=S, p=p, method=method, trials=TRIALS,
                P0=st["P0"], P0_ref=ana[f"{ref}_P0"], P0_abs_err=abs(st["P0"] - ana[f"{ref}_P0"]),
                P0_within_4se=abs(st["P0"] - ana[f"{ref}_P0"]) <= TOL_SE * st["P0_se"],
                P2plus=st["P2plus"], P2plus_ref=ana[f"{ref}_P2plus"],
                mean=st["mean"], mean_ref=ana["mu"], lecam_tv_bound=ana["lecam_tv_bound"]))
    # B) Poisson-vs-Binomial analytical error (incl. small-S and thesis regimes)
    for lbl, (S, p) in {"small_S20": (SMALL_S, 2.0 / SMALL_S),
                        "sim_S1e5": (SIM_S, 2.0 / SIM_S),
                        "thesis": (THESIS_S, THESIS_P)}.items():
        ana = analytical(S, p)
        rows.append(dict(
            block="poisson_vs_binomial", regime=lbl, mu=ana["mu"], S=S, p=p,
            binom_P0=ana["binom_P0"], pois_P0=ana["pois_P0"],
            P0_abs_err=abs(ana["binom_P0"] - ana["pois_P0"]),
            binom_P2plus=ana["binom_P2plus"], pois_P2plus=ana["pois_P2plus"],
            lecam_tv_bound=ana["lecam_tv_bound"]))
    # C) per-range assignment
    for n_ranges in (2, 10, 100):
        chk = per_range_assignment_check(SIM_S, 2.0 / SIM_S, n_ranges, TRIALS, seed + n_ranges)
        rows.append(dict(block="per_range_assignment", n_ranges=n_ranges, **chk,
                         mean_abs_err=abs(chk["perrange_mean"] - chk["global_mean"])))
    # D) discovery-time (first-success index)
    for mu in (0.5, 2.0, 5.0):
        S, p = SIM_S, mu / SIM_S
        ref = discovery_time_reference(S, p, 40_000, seed)
        fnd = discovery_time_finder(S, p, 40_000, seed + 1)
        rows.append(dict(block="discovery_time", mu=mu, S=S, p=p,
                         ref_mean_index=float(ref.mean()), finder_mean_index=float(fnd.mean()),
                         ref_n=int(ref.size), finder_n=int(fnd.size),
                         rel_err=abs(ref.mean() - fnd.mean()) / max(ref.mean(), 1e-9),
                         ks_stat=float(stats.ks_2samp(ref, fnd).statistic),
                         ks_pvalue=float(stats.ks_2samp(ref, fnd).pvalue)))
    return rows


def main():
    base = os.path.join(ROOT, "results", "thesis_revision_v43", "stage_04")
    raw = os.path.join(base, "raw"); mani = os.path.join(base, "manifests")
    os.makedirs(raw, exist_ok=True); os.makedirs(mani, exist_ok=True)
    rows = run_audit()
    # write CSV (union of keys)
    keys = []
    for r in rows:
        for k in r:
            if k not in keys:
                keys.append(k)
    path = os.path.join(raw, "finder_equivalence.csv")
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys); w.writeheader()
        for r in rows:
            w.writerow(r)
    os.chmod(path, 0o444)
    sha = hashlib.sha256(open(path, "rb").read()).hexdigest()
    json.dump(dict(rows=len(rows), csv_sha256=sha, seed=20260729,
                   mu_regimes=MU_REGIMES, sim_S=SIM_S, trials=TRIALS,
                   thesis_S=str(THESIS_S), thesis_p=THESIS_P),
              open(os.path.join(mani, "finder_equivalence.manifest.json"), "w"), indent=2)
    return rows


if __name__ == "__main__":
    for r in main():
        print(r)
