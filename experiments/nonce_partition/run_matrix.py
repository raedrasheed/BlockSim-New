"""Deterministic and stochastic experiment matrices for the disjoint-nonce
worst-case study. Writes results/nonce_partition_worst_case/*.

Deterministic (final-nonce worst case): miner counts x domain sizes, comparing
the Common-Template Duplicate-Search Baseline (Mode A) with PoCol Disjoint-Nonce
Allocation (Mode B). Asserts the reduction equals 1-1/N when M is divisible by N.

Stochastic: >=30 paired seeds per miner population, large analytical domain,
comparing A, B, and the Independent-Candidate-Headers reference (Mode C).

The model is analytical and stateless (no BlockSim global state), so runs occur
in-process; results are exactly reproducible from the seeds recorded in the
manifest.

Usage:  python experiments/nonce_partition/run_matrix.py [n_seeds]
"""
import os
import sys
import json
import platform
import subprocess

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import numpy as np

from experiments.nonce_partition.model import (
    duplicate_full_domain, disjoint_partition,
    duplicate_full_domain_stochastic, disjoint_partition_stochastic,
    independent_candidate_headers_stochastic,
    compare_modes, assert_energy_methods_agree,
)
from experiments.nonce_partition.statistics import (
    summarize, paired_cohens_d, exhaustion_probability,
)

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUTDIR = os.path.join(ROOT, "results", "nonce_partition_worst_case")

# Deterministic matrix axes (section 9)
MINER_COUNTS = [1, 2, 5, 10, 20, 50, 100, 200, 500]
DOMAIN_SIZES = [100, 1_000, 1_000_000, 2**32]

# Stochastic axes (section 10)
STO_MINERS = [100, 200, 300, 400, 500]
STO_DOMAIN = 2**32
STO_P = 2.0 ** -31          # E[successes] = M*p = 2 -> exhaustion prob ~ e^-2 ~ 13.5%


def _dup_header_evals(res):
    """Number of DUPLICATE complete-header evaluations in a result.

    Distinct complete headers evaluated = discovery_step (Mode A: all miners
    repeat the same t* headers) or the full total (Modes B/C: each header once).
    """
    if res.mode == "duplicate_full_domain":
        distinct = res.discovery_step if res.discovery_step is not None else res.M
        return res.total_attempts - distinct
    return 0


# ---------------------------------------------------------------------------
# Deterministic worst-case matrix
# ---------------------------------------------------------------------------
def run_deterministic():
    rows = []
    for M in DOMAIN_SIZES:
        for N in MINER_COUNTS:
            A = duplicate_full_domain(M, N, solution="last")
            B = disjoint_partition(M, N, solution="last")
            assert_energy_methods_agree(A)
            assert_energy_methods_agree(B)
            cmp = compare_modes(A, B)

            divisible = (M % N == 0)
            if divisible:
                # section 9 / invariants: exact 1-1/N reduction
                assert B.total_attempts == M, (M, N, B.total_attempts)
                assert A.total_attempts == N * M
                assert abs(cmp["energy_reduction_pct"] - 100.0 * (1 - 1.0 / N)) < 1e-9

            rows.append({
                "M": M, "N": N, "divisible": divisible,
                "baseline_total_attempts": A.total_attempts,
                "pocol_total_attempts": B.total_attempts,
                "baseline_attempts_per_miner": A.total_attempts // N,
                "pocol_attempts_per_miner_max": max(m.attempts for m in B.miners),
                "baseline_completion_time": A.completion_time,
                "pocol_completion_time": B.completion_time,
                "baseline_aggregate_active_s": A.aggregate_active_seconds,
                "pocol_aggregate_active_s": B.aggregate_active_seconds,
                "baseline_energy": A.total_energy,
                "pocol_energy": B.total_energy,
                "attempts_ratio": cmp["attempts_ratio"],
                "energy_ratio": cmp["energy_ratio"],
                "energy_reduction_pct": cmp["energy_reduction_pct"],
                "time_ratio": cmp["time_ratio"],
                "expected_reduction_pct": 100.0 * (1 - 1.0 / N),
                "winner_id": B.winner_id,
                "baseline_exhausted_ranges": A.exhausted_ranges,
                "pocol_exhausted_ranges": B.exhausted_ranges,
                "duplicate_evaluations_avoided": cmp["duplicate_evaluations_avoided"],
            })
    return rows


# ---------------------------------------------------------------------------
# Stochastic matrix
# ---------------------------------------------------------------------------
def run_stochastic(n_seeds):
    raw = []
    summary = []
    for N in STO_MINERS:
        per_mode = {"duplicate_full_domain": [], "disjoint_partition": [],
                    "independent_candidate_headers": []}
        for seed in range(n_seeds):
            A = duplicate_full_domain_stochastic(STO_DOMAIN, N, STO_P, seed)
            B = disjoint_partition_stochastic(STO_DOMAIN, N, STO_P, seed)
            C = independent_candidate_headers_stochastic(STO_DOMAIN, N, STO_P, seed)
            for res in (A, B, C):
                assert_energy_methods_agree(res)
                rec = {
                    "mode": res.mode, "N": N, "seed": seed,
                    "M": STO_DOMAIN, "p_success": STO_P,
                    "total_attempts": res.total_attempts,
                    "total_energy": res.total_energy,
                    "completion_time": res.completion_time,
                    "solution_found": res.solution_found,
                    "winner_id": res.winner_id,
                    "duplicate_header_evaluations": _dup_header_evals(res),
                }
                raw.append(rec)
                per_mode[res.mode].append(res)

        # per-mode summaries + paired effect size vs baseline
        base = per_mode["duplicate_full_domain"]
        base_att = [r.total_attempts for r in base]
        base_en = [r.total_energy for r in base]
        for mode, results in per_mode.items():
            att = [r.total_attempts for r in results]
            en = [r.total_energy for r in results]
            ct = [r.completion_time for r in results]
            s_att = summarize(att)
            s_en = summarize(en)
            s_ct = summarize(ct)
            summary.append({
                "N": N, "mode": mode, "n_seeds": n_seeds,
                "attempts_mean": s_att["mean"], "attempts_median": s_att["median"],
                "attempts_std": s_att["std"],
                "attempts_ci95_low": s_att["ci95_low"], "attempts_ci95_high": s_att["ci95_high"],
                "attempts_min": s_att["min"], "attempts_max": s_att["max"],
                "energy_mean": s_en["mean"], "energy_ci95_low": s_en["ci95_low"],
                "energy_ci95_high": s_en["ci95_high"],
                "completion_time_mean": s_ct["mean"],
                "exhaustion_probability": exhaustion_probability(r.solution_found for r in results),
                "duplicate_header_evals_mean": float(np.mean([_dup_header_evals(r) for r in results])),
                "paired_cohens_d_attempts_vs_baseline": paired_cohens_d(base_att, att),
                "paired_cohens_d_energy_vs_baseline": paired_cohens_d(base_en, en),
            })
    return raw, summary


# ---------------------------------------------------------------------------
def _write_csv(path, rows, fieldnames):
    import csv
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def _git(*args):
    try:
        return subprocess.run(["git", *args], capture_output=True, text=True,
                              cwd=ROOT).stdout.strip()
    except Exception:
        return None


def main(n_seeds=30):
    os.makedirs(OUTDIR, exist_ok=True)

    det = run_deterministic()
    det_path = os.path.join(OUTDIR, "deterministic_results.csv")
    _write_csv(det_path, det, list(det[0].keys()))
    print(f"wrote {det_path}  ({len(det)} rows)")

    raw, summ = run_stochastic(n_seeds)
    raw_path = os.path.join(OUTDIR, "stochastic_raw_runs.csv")
    _write_csv(raw_path, raw, list(raw[0].keys()))
    summ_path = os.path.join(OUTDIR, "stochastic_summary.csv")
    _write_csv(summ_path, summ, list(summ[0].keys()))
    print(f"wrote {raw_path}  ({len(raw)} rows)")
    print(f"wrote {summ_path}  ({len(summ)} rows)")

    config = {
        "experiment": "nonce_partition_worst_case",
        "modes": {
            "A": "duplicate_full_domain (Common-Template Duplicate-Search Baseline)",
            "B": "disjoint_partition (PoCol Disjoint-Nonce Allocation)",
            "C": "independent_candidate_headers (reference control)",
        },
        "interval_convention": "half-open [domain_start, domain_end); M = end - start",
        "deterministic": {
            "miner_counts": MINER_COUNTS, "domain_sizes": DOMAIN_SIZES,
            "solution_placement": "final position (domain_end - 1)",
        },
        "stochastic": {
            "miner_counts": STO_MINERS, "domain_size": STO_DOMAIN,
            "p_success": STO_P, "p_success_repr": "2**-31",
            "expected_successes_M_times_p": STO_DOMAIN * STO_P,
            "expected_exhaustion_probability_approx": "e^-2 ~= 0.135",
            "n_seeds": n_seeds, "seed_pairing": "A and B share the same seed draw",
        },
        "energy_model": {
            "hashrate_per_miner": 1.0, "energy_per_attempt": 1.0, "power_per_miner": 1.0,
            "rule": "energy = attempts * (P/r) = P * active_time; never block_time/N",
        },
    }
    cfg_path = os.path.join(OUTDIR, "configuration.json")
    with open(cfg_path, "w") as fh:
        json.dump(config, fh, indent=2)
    print(f"wrote {cfg_path}")

    manifest = {
        "git_commit": _git("rev-parse", "HEAD"),
        "git_branch": _git("rev-parse", "--abbrev-ref", "HEAD"),
        "git_dirty": bool(_git("status", "--porcelain")),
        "python_version": sys.version,
        "platform": platform.platform(),
        "packages": {"numpy": np.__version__},
        "n_deterministic_rows": len(det),
        "n_stochastic_runs": len(raw),
        "n_seeds": n_seeds,
        "reproduce": f"python experiments/nonce_partition/run_matrix.py {n_seeds}",
        "note": ("Analytical model; results reproduce exactly from the fixed seeds. "
                 "This experiment does NOT modify results/corrected/ or the "
                 "wall-clock energy model."),
    }
    man_path = os.path.join(OUTDIR, "reproducibility_manifest.json")
    with open(man_path, "w") as fh:
        json.dump(manifest, fh, indent=2)
    print(f"wrote {man_path}")

    # ---- console headline ----
    print("\n=== deterministic worst case: energy reduction % (M vs N) ===")
    import collections
    by = collections.defaultdict(dict)
    for r in det:
        by[r["N"]][r["M"]] = r["energy_reduction_pct"]
    hdr = "  N   " + "".join(f"{('M='+str(M)):>16}" for M in DOMAIN_SIZES)
    print(hdr)
    for N in MINER_COUNTS:
        print(f"{N:>4}  " + "".join(f"{by[N][M]:>16.4f}" for M in DOMAIN_SIZES))

    print("\n=== stochastic mean total attempts (M=2^32, p=2^-31) ===")
    print(f"{'N':>4} {'duplicate(A)':>16} {'disjoint(B)':>16} {'independent(C)':>16}")
    for N in STO_MINERS:
        row = {s["mode"]: s["attempts_mean"] for s in summ if s["N"] == N}
        print(f"{N:>4} {row['duplicate_full_domain']:>16.0f} "
              f"{row['disjoint_partition']:>16.0f} "
              f"{row['independent_candidate_headers']:>16.0f}")

    return det, raw, summ


if __name__ == "__main__":
    ns = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    main(ns)
