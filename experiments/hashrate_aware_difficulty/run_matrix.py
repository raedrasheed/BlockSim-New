"""Experiment matrices -> results/hashrate_aware_difficulty/.

- difficulty_by_population.csv: ANALYTIC difficulty/target/expected-interval
  table, N in {1..500} x {H1,H2} x {D1,D2} (big-int targets as strings).
- raw_runs.csv (stochastic, FRESH SUBPROCESS each, paired seeds):
    primary: D2 x {H1,H2} x 3 protocols x N in {100..500} x n_seeds
    D1 demo: H2 x 3 protocols x N in {1,2,5,10} x n_seeds
    D3 demo: H2 x PoCol x N in {10,100} (window 10, start 10x too easy) x n_seeds
- summary_statistics.csv, paired_comparisons.csv (PoCol vs DUP / vs IND + TOST),
  per_block_work.csv, configuration.json, reproducibility_manifest.json.

Usage:  python experiments/hashrate_aware_difficulty/run_matrix.py [n_seeds] [workers]
"""
import os
import sys
import csv
import json
import platform
import subprocess
import concurrent.futures as cf

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import numpy as np

from experiments.hashrate_aware_difficulty.configuration import (
    PROTO_DUP, PROTO_IND, PROTO_POCOL, HW_H1, HW_H2,
    D1_CONSTANT, D2_SCALED, D3_RETARGET,
)
from experiments.hashrate_aware_difficulty.difficulty import difficulty_by_population
from experiments.hashrate_aware_difficulty.run_scenario import run as run_one
from experiments.hashrate_aware_difficulty import statistics as st

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUTDIR = os.path.join(ROOT, "results", "hashrate_aware_difficulty")
RUNNER = os.path.join(ROOT, "experiments", "hashrate_aware_difficulty", "run_scenario.py")

ALL_N = [1, 2, 5, 10, 20, 50, 100, 200, 300, 400, 500]
PROTOCOLS = [PROTO_DUP, PROTO_IND, PROTO_POCOL]
PRIMARY_N = [100, 200, 300, 400, 500]
D1_N = [1, 2, 5, 10]
D3_N = [10, 100]

SUMMARY_METRICS = ["mean_block_interval_s", "accepted_blocks", "mean_difficulty",
                   "total_hashes", "total_energy_kwh",
                   "energy_per_accepted_block_kwh", "energy_per_tx_kwh",
                   "template_exhaustion_rate", "active_fraction", "idle_fraction",
                   "duplicate_header_attempts", "unique_header_attempts",
                   "actual_hashes_per_accepted_block", "accumulated_work_per_block"]


def _cmd(proto, N, hw, mode, seed, extra=()):
    return ([sys.executable, RUNNER, proto, str(N), "--hardware", hw,
             "--mode", mode, "--seed", str(seed)] + list(extra))


def _sub(args):
    out = subprocess.run(args, capture_output=True, text=True, cwd=ROOT)
    if out.returncode != 0:
        raise RuntimeError(f"{' '.join(args[-8:])}:\n{out.stderr[-1200:]}")
    return json.loads(out.stdout.strip().splitlines()[-1])


def run_stochastic(n_seeds, workers):
    jobs = []
    for N in PRIMARY_N:                                    # primary D2
        for hw in ("H1", "H2"):
            for proto in PROTOCOLS:
                for s in range(n_seeds):
                    jobs.append(_cmd(proto, N, hw, "D2", s))
    for N in D1_N:                                         # D1 dilution demo (H2)
        for proto in PROTOCOLS:
            for s in range(n_seeds):
                jobs.append(_cmd(proto, N, "H2", "D1", s))
    for N in D3_N:                                         # D3 retarget demo
        for s in range(n_seeds):
            jobs.append(_cmd(PROTO_POCOL, N, "H2", "D3", s,
                             ("--window", "10", "--initial-factor", "0.1")))
    print(f"stochastic: {len(jobs)} fresh-subprocess runs, {workers} workers")
    rows = []
    done = 0
    with cf.ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(_sub, j): j for j in jobs}
        for f in cf.as_completed(futs):
            rows.append(f.result())
            done += 1
            if done % 500 == 0 or done == len(jobs):
                print(f"  {done}/{len(jobs)}")
    return rows


def summarize(sto):
    keys = sorted({(r["hardware"], r["difficulty_mode"], r["protocol"], r["N"])
                   for r in sto})
    out = []
    for hw, mode, proto, N in keys:
        sub = [r for r in sto if (r["hardware"], r["difficulty_mode"],
                                  r["protocol"], r["N"]) == (hw, mode, proto, N)]
        row = {"hardware": hw, "difficulty_mode": mode, "protocol": proto,
               "N": N, "n_seeds": len(sub),
               "aggregate_hashrate_hps": sub[0]["aggregate_hashrate_hps"],
               "difficulty_ratio_vs_N1": float("nan")}
        for met in SUMMARY_METRICS:
            s = st.summarize([r[met] for r in sub])
            for k, v in s.items():
                row[f"{met}__{k}"] = v
        out.append(row)
    # difficulty ratio vs the N=1 (or smallest-N) row of the same condition class
    for row in out:
        base = [r for r in out if r["hardware"] == row["hardware"]
                and r["difficulty_mode"] == row["difficulty_mode"]
                and r["protocol"] == row["protocol"]]
        base_row = min(base, key=lambda r: r["N"])
        b = base_row["mean_difficulty__mean"]
        if b:
            row["difficulty_ratio_vs_N1"] = row["mean_difficulty__mean"] / b
    return out


def paired(sto):
    rows = []
    for hw in ("H1", "H2"):
        for N in PRIMARY_N:
            by = {p: {r["seed"]: r for r in sto
                      if r["hardware"] == hw and r["difficulty_mode"] == D2_SCALED
                      and r["protocol"] == p and r["N"] == N}
                  for p in PROTOCOLS}
            for other in (PROTO_DUP, PROTO_IND):
                seeds = sorted(set(by[PROTO_POCOL]) & set(by[other]))
                for metric in ("total_energy_kwh", "energy_per_accepted_block_kwh",
                               "mean_block_interval_s", "accepted_blocks",
                               "total_attempts"):
                    a = [by[other][s][metric] for s in seeds]
                    b = [by[PROTO_POCOL][s][metric] for s in seeds]
                    pd = st.paired_diff(a, b)
                    rec = {"hardware": hw, "N": N,
                           "comparison": f"pocol_minus_{other}", "metric": metric,
                           "other_mean": float(np.nanmean(a)) if a else float("nan"),
                           "pocol_mean": float(np.nanmean(b)) if b else float("nan"),
                           **pd}
                    if other == PROTO_IND and metric == "total_energy_kwh":
                        margin = st.POCOL_VS_IND_MARGIN_REL * float(np.nanmean(a))
                        rec.update({f"tost_{k}": v for k, v in
                                    st.tost_equivalence(a, b, margin).items()})
                    rows.append(rec)
    return rows


def per_block_work():
    rows = []
    for proto in PROTOCOLS:
        rec = run_one(proto, 100, hardware="H1", mode="D2", seed=0,
                      want_blocks=True)
        commits = [b["commit_time"] for b in rec["_blocks"]]
        for i, b in enumerate(rec["_blocks"]):
            rows.append({
                "protocol": proto, "N": 100, "hardware": "H1", "mode": "D2",
                "seed": 0, **{k: b[k] for k in ("height", "commit_time",
                                                "winner_id", "template_index",
                                                "target_bits", "difficulty",
                                                "attempts_this_template")},
                "interval_s": commits[i] - commits[i - 1] if i else commits[0],
            })
    return rows


def _write_csv(path, rows):
    keys = sorted({k for r in rows for k in r})
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=keys, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print(f"wrote {os.path.relpath(path, ROOT)} ({len(rows)} rows)")


def _git(*a):
    try:
        return subprocess.run(["git", *a], capture_output=True, text=True,
                              cwd=ROOT).stdout.strip()
    except Exception:
        return None


def main(n_seeds=100, workers=12):
    os.makedirs(OUTDIR, exist_ok=True)

    pop = []
    for hw in (HW_H1, HW_H2):
        for mode in (D1_CONSTANT, D2_SCALED):
            pop += difficulty_by_population(ALL_N, hw, mode)
    _write_csv(os.path.join(OUTDIR, "difficulty_by_population.csv"), pop)

    sto = run_stochastic(n_seeds, workers)
    for r in sto:
        r.pop("_blocks", None)
    _write_csv(os.path.join(OUTDIR, "raw_runs.csv"), sto)
    _write_csv(os.path.join(OUTDIR, "summary_statistics.csv"), summarize(sto))
    _write_csv(os.path.join(OUTDIR, "paired_comparisons.csv"), paired(sto))
    _write_csv(os.path.join(OUTDIR, "per_block_work.csv"), per_block_work())

    config = {
        "experiment": "hashrate_aware_difficulty",
        "t_target_s": 600.0,
        "formulas": {
            "W_expected": "H_network * T_target",
            "p_success": "1/W = (target+1)/2^256",
            "target": "floor(2^256/W) - 1 (256-bit clamped)",
        },
        "hardware": {"H1": "fixed aggregate 141e12 H/s (difficulty constant in N)",
                     "H2": "fixed per-miner 1.41e12 H/s (D2: D_N = N*D_1)"},
        "difficulty_modes": {"D1": "constant (reference-frozen)",
                             "D2": "hashrate-scaled (primary)",
                             "D3": "dynamic retarget (window 10, clamp [0.25,4], start 0.1x)"},
        "domain": "M_total = H_network * 1200s (aggregate-based; double-scaling removed)",
        "stochastic": {"primary": {"mode": "D2", "hardware": ["H1", "H2"],
                                   "N": PRIMARY_N, "n_seeds": n_seeds},
                       "d1_demo": {"hardware": "H2", "N": D1_N, "n_seeds": n_seeds},
                       "d3_demo": {"hardware": "H2", "N": D3_N, "n_seeds": n_seeds},
                       "fresh_subprocess_per_run": True},
        "tost_margin_rel_preregistered": st.POCOL_VS_IND_MARGIN_REL,
    }
    with open(os.path.join(OUTDIR, "configuration.json"), "w") as fh:
        json.dump(config, fh, indent=2)
    manifest = {
        "git_commit": _git("rev-parse", "HEAD"),
        "git_branch": _git("rev-parse", "--abbrev-ref", "HEAD"),
        "git_dirty": bool(_git("status", "--porcelain")),
        "python_version": sys.version, "platform": platform.platform(),
        "packages": {"numpy": np.__version__},
        "n_stochastic_runs": len(sto), "n_seeds": n_seeds,
        "reproduce": f"python experiments/hashrate_aware_difficulty/run_matrix.py {n_seeds} {workers}",
        "protected_unchanged": ["results/corrected/", "results/nonce_partition_worst_case/",
                                "results/continuous_distributed_effort/",
                                "results/mainsim_idle_after_range/",
                                "results/fixed_600s_pocol/"],
    }
    with open(os.path.join(OUTDIR, "reproducibility_manifest.json"), "w") as fh:
        json.dump(manifest, fh, indent=2)
    print("wrote configuration.json + reproducibility_manifest.json")

    print("\n=== D2 primary, H1: mean interval (s) by protocol x N ===")
    for N in PRIMARY_N:
        row = {}
        for proto in PROTOCOLS:
            sub = [r for r in sto if r["hardware"] == HW_H1 and
                   r["difficulty_mode"] == D2_SCALED and r["protocol"] == proto
                   and r["N"] == N and r["accepted_blocks"] >= 2]
            row[proto] = (float(np.mean([r["mean_block_interval_s"] for r in sub]))
                          if sub else float("nan"))
        print(f"  N={N}: dup={row[PROTO_DUP]:.0f}  ind={row[PROTO_IND]:.0f}  "
              f"pocol={row[PROTO_POCOL]:.0f}")
    return sto


if __name__ == "__main__":
    ns = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    wk = int(sys.argv[2]) if len(sys.argv) > 2 else 12
    main(ns, wk)
