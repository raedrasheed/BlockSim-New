"""Experiment matrices for the fixed-600s study -> results/fixed_600s_pocol/.

Deterministic grid (in-process; the model is pure-functional and invariant-19
tested): N x protocol x hardware x placement x idle ratio, + sleep sub-sweep.
Stochastic: 3 protocols x N in {100..500} x >=100 paired seeds, EACH IN A FRESH
SUBPROCESS (invariant 26).

Usage:  python experiments/fixed_600s_pocol/run_matrix.py [n_seeds] [workers]
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

from experiments.fixed_600s_pocol.configuration import (
    FixedRoundConfig, PowerConfig, PROTO_DUP, PROTO_IND, PROTO_POCOL,
    HW_H1, HW_H2, PLACEMENTS, ROUND_DURATION_SECONDS,
)
from experiments.fixed_600s_pocol.run_scenario import run as run_one
from experiments.fixed_600s_pocol import statistics as st

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUTDIR = os.path.join(ROOT, "results", "fixed_600s_pocol")
RUNNER = os.path.join(ROOT, "experiments", "fixed_600s_pocol", "run_scenario.py")

MINER_COUNTS = [1, 2, 5, 10, 20, 50, 100, 200, 300, 400, 500]
PROTOCOLS = [PROTO_DUP, PROTO_IND, PROTO_POCOL]
IDLE_RATIOS = [0.00, 0.05, 0.10, 0.20, 0.50, 1.00]
SLEEP_RATIOS = [0.00, 0.01, 0.05]
STO_MINERS = [100, 200, 300, 400, 500]

_DROP = ("_rounds", "_miners")


def _clean(rec):
    return {k: v for k, v in rec.items() if k not in _DROP}


def run_deterministic():
    rows = []
    for hw_name, hw in (("H1", HW_H1), ("H2", HW_H2)):
        for N in MINER_COUNTS:
            for placement in PLACEMENTS:
                for q in IDLE_RATIOS:
                    base = {}
                    for proto in PROTOCOLS:
                        rec = run_one(proto, N, hardware=hw, placement=placement,
                                      idle=q, sim=10200.0)
                        rec["hardware_label"] = hw_name
                        base[proto] = rec
                    eA = base[PROTO_DUP]["total_energy_j"]
                    for proto in PROTOCOLS:
                        r = dict(_clean(base[proto]))
                        r["hardware_label"] = hw_name
                        r["energy_ratio_vs_duplicate"] = (
                            r["total_energy_j"] / eA if eA else float("nan"))
                        r["energy_reduction_pct_vs_duplicate"] = (
                            100.0 * (1 - r["total_energy_j"] / eA) if eA else float("nan"))
                        rows.append(r)
    # sleep sub-sweep (H2, N in {10,100}, last placement, finished -> SLEEP)
    for N in (10, 100):
        for sr in SLEEP_RATIOS:
            base = {}
            for proto in (PROTO_DUP, PROTO_POCOL):
                rec = run_one(proto, N, hardware=HW_H2, placement="last",
                              idle=0.0, sleep=sr, use_sleep=True, sim=10200.0)
                base[proto] = rec
            eA = base[PROTO_DUP]["total_energy_j"]
            for proto in (PROTO_DUP, PROTO_POCOL):
                r = dict(_clean(base[proto]))
                r["hardware_label"] = "H2"
                r["energy_ratio_vs_duplicate"] = r["total_energy_j"] / eA
                r["energy_reduction_pct_vs_duplicate"] = 100.0 * (1 - r["total_energy_j"] / eA)
                rows.append(r)
    return rows


def _sto_cmd(proto, N, seed):
    return [sys.executable, RUNNER, proto, str(N), "--hardware", "H1",
            "--p", "auto", "--seed", str(seed), "--sim", "10200"]


def _sto_run(proto, N, seed):
    out = subprocess.run(_sto_cmd(proto, N, seed), capture_output=True,
                         text=True, cwd=ROOT)
    if out.returncode != 0:
        raise RuntimeError(f"{proto} N={N} seed={seed}:\n{out.stderr[-1200:]}")
    rec = json.loads(out.stdout.strip().splitlines()[-1])
    return _clean(rec)


def run_stochastic(n_seeds, workers):
    jobs = [(p, N, s) for N in STO_MINERS for p in PROTOCOLS for s in range(n_seeds)]
    print(f"stochastic: {len(jobs)} fresh-subprocess runs, {workers} workers")
    rows = []
    done = 0
    with cf.ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(_sto_run, *j): j for j in jobs}
        for f in cf.as_completed(futs):
            rows.append(f.result())
            done += 1
            if done % 250 == 0 or done == len(jobs):
                print(f"  {done}/{len(jobs)}")
    return rows


SUMMARY_METRICS = ["total_energy_kwh", "accepted_blocks", "empty_rounds",
                   "mean_discovery_time_s", "mean_post_discovery_idle_s",
                   "total_attempts", "duplicate_header_evaluations",
                   "active_miner_seconds", "pct_time_active",
                   "throughput_tx_per_s", "energy_per_accepted_block_kwh",
                   "energy_per_tx_kwh", "exhausted_templates"]


def summarize_stochastic(sto):
    rows = []
    for N in STO_MINERS:
        for proto in PROTOCOLS:
            sub = [r for r in sto if r["N"] == N and r["protocol"] == proto]
            row = {"N": N, "protocol": proto, "n_seeds": len(sub)}
            for met in SUMMARY_METRICS:
                s = st.summarize([r[met] for r in sub])
                for k, v in s.items():
                    row[f"{met}__{k}"] = v
            rows.append(row)
    return rows


def paired_comparisons(sto):
    rows = []
    for N in STO_MINERS:
        by = {p: {r["seed"]: r for r in sto if r["N"] == N and r["protocol"] == p}
              for p in PROTOCOLS}
        for other in (PROTO_DUP, PROTO_IND):
            seeds = sorted(set(by[PROTO_POCOL]) & set(by[other]))
            for metric in ("total_energy_kwh", "total_attempts",
                           "mean_discovery_time_s", "accepted_blocks"):
                a = [by[other][s][metric] for s in seeds]
                b = [by[PROTO_POCOL][s][metric] for s in seeds]
                pd = st.paired_diff(a, b)
                rec = {"N": N, "comparison": f"pocol_minus_{other}", "metric": metric,
                       "other_mean": float(np.nanmean(a)) if a else float("nan"),
                       "pocol_mean": float(np.nanmean(b)) if b else float("nan"), **pd}
                if other == PROTO_IND and metric == "total_energy_kwh":
                    margin = st.POCOL_VS_IND_MARGIN_REL * float(np.nanmean(a))
                    rec.update({f"tost_{k}": v
                                for k, v in st.tost_equivalence(a, b, margin).items()})
                rows.append(rec)
    return rows


def per_round_and_miner_reports():
    per_round, per_miner = [], []
    # representative stochastic rounds: N=100, seed 0, all protocols (H1)
    for proto in PROTOCOLS:
        rec = run_one(proto, 100, hardware=HW_H1, p=2.0 / FixedRoundConfig(
            N=100, hardware=HW_H1).effective_M(), seed=0, sim=10200.0,
            want_rounds=True)
        for r in rec["_rounds"]:
            per_round.append({"protocol": proto, "N": 100, "seed": 0,
                              "scenario": "stochastic_H1", **r})
    # spec-12 deterministic per-miner detail (H2, M=100, N=10)
    for proto in PROTOCOLS:
        rec = run_one(proto, 10, hardware=HW_H2, M=100, h2_rate=1.0,
                      placement="last", sim=600.0, want_miners=True)
        for m in rec["_miners"]:
            per_miner.append({"protocol": proto, "scenario": "spec12_H2_M100", **m})
    return per_round, per_miner


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
    det = run_deterministic()
    _write_csv(os.path.join(OUTDIR, "deterministic_raw.csv"), det)
    sto = run_stochastic(n_seeds, workers)
    _write_csv(os.path.join(OUTDIR, "stochastic_raw.csv"), sto)
    _write_csv(os.path.join(OUTDIR, "summary_statistics.csv"), summarize_stochastic(sto))
    _write_csv(os.path.join(OUTDIR, "paired_comparisons.csv"), paired_comparisons(sto))
    pr, pm = per_round_and_miner_reports()
    _write_csv(os.path.join(OUTDIR, "per_round_results.csv"), pr)
    _write_csv(os.path.join(OUTDIR, "per_miner_results.csv"), pm)

    config = {
        "experiment": "fixed_600s_pocol",
        "round_seconds": ROUND_DURATION_SECONDS,
        "protocols": PROTOCOLS,
        "deterministic": {"miner_counts": MINER_COUNTS, "hardware": ["H1", "H2"],
                          "placements": list(PLACEMENTS), "idle_ratios": IDLE_RATIOS,
                          "sleep_ratios": SLEEP_RATIOS, "sim_seconds": 10200.0},
        "stochastic": {"miner_counts": STO_MINERS, "hardware": "H1",
                       "p_success": "2/M (E[successes]=2 per template)",
                       "idle_ratio": 0.0, "n_seeds": n_seeds,
                       "sim_seconds": 10200.0, "fresh_subprocess_per_run": True},
        "pocol_vs_independent_tost_margin_rel_preregistered": st.POCOL_VS_IND_MARGIN_REL,
        "energy_rule": "E_i = P_a*t_a + P_i*t_i + P_s*t_s; never divided by N",
        "commit_rule": "block buffered; commit_time = round_start + 600 exactly",
    }
    with open(os.path.join(OUTDIR, "configuration.json"), "w") as fh:
        json.dump(config, fh, indent=2)
    manifest = {
        "git_commit": _git("rev-parse", "HEAD"),
        "git_branch": _git("rev-parse", "--abbrev-ref", "HEAD"),
        "git_dirty": bool(_git("status", "--porcelain")),
        "python_version": sys.version, "platform": platform.platform(),
        "packages": {"numpy": np.__version__},
        "n_deterministic_rows": len(det), "n_stochastic_runs": len(sto),
        "n_seeds": n_seeds,
        "reproduce": f"python experiments/fixed_600s_pocol/run_matrix.py {n_seeds} {workers}",
        "protected_unchanged": ["results/corrected/", "results/nonce_partition_worst_case/",
                                "results/continuous_distributed_effort/",
                                "results/mainsim_idle_after_range/"],
    }
    with open(os.path.join(OUTDIR, "reproducibility_manifest.json"), "w") as fh:
        json.dump(manifest, fh, indent=2)
    print("wrote configuration.json + reproducibility_manifest.json")

    # headline: deterministic H1 last-placement q=0 energy reduction vs duplicate
    print("\n=== deterministic H1, placement=last, q=0: energy reduction vs duplicate ===")
    for N in (10, 100, 500):
        row_b = next(r for r in det if r["hardware_label"] == "H1" and r["N"] == N
                     and r["placement"] == "last" and r["idle_ratio"] == 0.0
                     and r["protocol"] == PROTO_POCOL and not r.get("use_sleep"))
        row_c = next(r for r in det if r["hardware_label"] == "H1" and r["N"] == N
                     and r["placement"] == "last" and r["idle_ratio"] == 0.0
                     and r["protocol"] == PROTO_IND and not r.get("use_sleep"))
        print(f"  N={N}: PoCol {row_b['energy_reduction_pct_vs_duplicate']:.2f}%  "
              f"IND {row_c['energy_reduction_pct_vs_duplicate']:.2f}%")
    return det, sto


if __name__ == "__main__":
    ns = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    wk = int(sys.argv[2]) if len(sys.argv) > 2 else 12
    main(ns, wk)
