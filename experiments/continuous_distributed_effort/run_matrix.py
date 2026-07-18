"""Deterministic + stochastic experiment matrices for the continuous
distributed-effort study. Writes results/continuous_distributed_effort/*.

Deterministic grid (analytical, pure-functional -> run in-process): modes x miner
counts x schedules x hardware x idle ratios, plus a sleep-ratio sub-sweep.

Stochastic: modes x miner counts x >=100 paired seeds, each in a FRESH SUBPROCESS
(run_scenario.py) so no global state leaks. Reports bootstrap CIs and a
pre-registered TOST equivalence test for B vs C1.

Usage:  python experiments/continuous_distributed_effort/run_matrix.py [n_seeds] [workers]
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

from experiments.continuous_distributed_effort.configuration import (
    ExperimentConfig, PowerConfig, MODE_A, MODE_B, MODE_C1, MODE_C2,
    SCHED_IMMEDIATE, SCHED_FIXED_SLOT, HW_H1, HW_H2, AGG_HASHRATE_HPS, AGG_ACTIVE_POWER_W,
)
from experiments.continuous_distributed_effort.round_model import (
    simulate_continuous, deterministic_outcome,
)
from experiments.continuous_distributed_effort import statistics as st

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUTDIR = os.path.join(ROOT, "results", "continuous_distributed_effort")
RUNNER = os.path.join(ROOT, "experiments", "continuous_distributed_effort", "run_scenario.py")

MINER_COUNTS = [1, 2, 5, 10, 20, 50, 100, 200, 300, 400, 500]
MODES = [MODE_A, MODE_B, MODE_C1, MODE_C2]
SCHEDULES = [SCHED_IMMEDIATE, SCHED_FIXED_SLOT]
HARDWARES = [HW_H1, HW_H2]
IDLE_RATIOS = [0.00, 0.05, 0.10, 0.20, 0.50, 1.00]
SLEEP_RATIOS = [0.00, 0.01, 0.05]

# Stochastic conditions (H2, calibrated so a full-domain scan fills one slot).
STO_MINERS = [100, 200, 300, 400, 500]
STO_M = 1_000_000
STO_P = 2.0 / STO_M          # E[successes]=2 per template -> exhaustion ~ e^-2
STO_IDLE = 0.10
STO_SLOT = 600.0
STO_SIM = 10000.0

# Pre-registered equivalence margin for B vs C1 (set BEFORE inspecting results):
# 1% of the C1 mean energy per N (relative TOST margin).
BC1_MARGIN_REL = 0.01


def _M_for(hardware, N, slot=STO_SLOT):
    """Domain size so a full-domain scan fills exactly one slot, divisible by N."""
    if hardware == HW_H2:
        return 1000 * N                    # r=M/slot; active_full=slot; M/N=1000
    # H1: r_i = AGG/N; M = r_i*slot; round to a multiple of N
    m = int(round((AGG_HASHRATE_HPS / N) * slot))
    return m - (m % N)


# ---------------------------------------------------------------------------
def run_deterministic():
    rows = []
    # main idle-ratio grid
    for hw in HARDWARES:
        for N in MINER_COUNTS:
            M = _M_for(hw, N)
            for sched in SCHEDULES:
                for q in IDLE_RATIOS:
                    cfg = ExperimentConfig(
                        N=N, M=M, mode=MODE_A, schedule=sched, hardware=hw,
                        power=PowerConfig(idle_ratio=q), slot_seconds=STO_SLOT,
                        sim_seconds=STO_SIM)
                    per_mode = {}
                    for mode in MODES:
                        c = ExperimentConfig(
                            N=N, M=M, mode=mode, schedule=sched, hardware=hw,
                            power=PowerConfig(idle_ratio=q), slot_seconds=STO_SLOT,
                            sim_seconds=STO_SIM)
                        m, _ = simulate_continuous(c, deterministic_outcome)
                        per_mode[mode] = m
                    eA = per_mode[MODE_A]["total_energy_j"]
                    for mode in MODES:
                        m = per_mode[mode]
                        rows.append({
                            "hardware": hw, "N": N, "M": M, "schedule": sched,
                            "idle_ratio": q, "sleep_ratio": 0.0, "finished_state": "IDLE",
                            "mode": mode,
                            "total_energy_j": m["total_energy_j"],
                            "total_energy_kwh": m["total_energy_kwh"],
                            "active_miner_seconds": m["active_miner_seconds"],
                            "idle_miner_seconds": m["idle_miner_seconds"],
                            "sleep_miner_seconds": m["sleep_miner_seconds"],
                            "pct_time_active": m["pct_time_active"],
                            "unique_candidate_evaluations": m["unique_candidate_evaluations"],
                            "duplicate_header_evaluations": m["duplicate_header_evaluations"],
                            "successful_rounds": m["successful_rounds"],
                            "energy_ratio_vs_A": m["total_energy_j"] / eA if eA else float("nan"),
                            "energy_reduction_pct_vs_A": 100.0 * (1 - m["total_energy_j"] / eA) if eA else float("nan"),
                            "expected_reduction_pct": (100.0 * (1 - q) * (1 - 1.0 / N)
                                                       if sched == SCHED_FIXED_SLOT else 0.0),
                        })
    # sleep-ratio sub-sweep (FIXED_SLOT, H2, finished miners SLEEP, idle=0)
    for N in [10, 100]:
        M = _M_for(HW_H2, N)
        for sr in SLEEP_RATIOS:
            per_mode = {}
            for mode in (MODE_A, MODE_B):
                c = ExperimentConfig(
                    N=N, M=M, mode=mode, schedule=SCHED_FIXED_SLOT, hardware=HW_H2,
                    power=PowerConfig(idle_ratio=0.0, sleep_ratio=sr, use_sleep=True),
                    slot_seconds=STO_SLOT, sim_seconds=STO_SIM)
                m, _ = simulate_continuous(c, deterministic_outcome)
                per_mode[mode] = m
            eA = per_mode[MODE_A]["total_energy_j"]
            for mode in (MODE_A, MODE_B):
                m = per_mode[mode]
                rows.append({
                    "hardware": HW_H2, "N": N, "M": M, "schedule": SCHED_FIXED_SLOT,
                    "idle_ratio": 0.0, "sleep_ratio": sr, "finished_state": "SLEEP",
                    "mode": mode,
                    "total_energy_j": m["total_energy_j"],
                    "total_energy_kwh": m["total_energy_kwh"],
                    "active_miner_seconds": m["active_miner_seconds"],
                    "idle_miner_seconds": m["idle_miner_seconds"],
                    "sleep_miner_seconds": m["sleep_miner_seconds"],
                    "pct_time_active": m["pct_time_active"],
                    "unique_candidate_evaluations": m["unique_candidate_evaluations"],
                    "duplicate_header_evaluations": m["duplicate_header_evaluations"],
                    "successful_rounds": m["successful_rounds"],
                    "energy_ratio_vs_A": m["total_energy_j"] / eA if eA else float("nan"),
                    "energy_reduction_pct_vs_A": 100.0 * (1 - m["total_energy_j"] / eA) if eA else float("nan"),
                    "expected_reduction_pct": 100.0 * (1 - sr) * (1 - 1.0 / N),
                })
    return rows


def _sto_cmd(mode, N, seed):
    return [sys.executable, RUNNER, "--mode", mode, "--N", str(N), "--M", str(STO_M),
            "--schedule", SCHED_FIXED_SLOT, "--hardware", HW_H2,
            "--idle", str(STO_IDLE), "--seed", str(seed), "--p", repr(STO_P),
            "--sim", str(STO_SIM), "--slot", str(STO_SLOT)]


def _run_sto(mode, N, seed):
    out = subprocess.run(_sto_cmd(mode, N, seed), capture_output=True, text=True, cwd=ROOT)
    if out.returncode != 0:
        raise RuntimeError(f"sto run failed {mode} N={N} seed={seed}:\n{out.stderr[-1500:]}")
    rec = json.loads(out.stdout.strip().splitlines()[-1])
    rec["seed"] = seed
    return rec


def run_stochastic(n_seeds, workers):
    jobs = [(mode, N, s) for N in STO_MINERS for mode in MODES for s in range(n_seeds)]
    print(f"stochastic: {len(jobs)} fresh-subprocess runs, {workers} workers...")
    rows = []
    done = 0
    with cf.ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(_run_sto, m, N, s): (m, N, s) for (m, N, s) in jobs}
        for f in cf.as_completed(futs):
            rows.append(f.result())
            done += 1
            if done % 200 == 0 or done == len(jobs):
                print(f"  {done}/{len(jobs)}")
    return rows


def _write_csv(path, rows, fieldnames=None):
    fieldnames = fieldnames or list(rows[0].keys())
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)


def _git(*a):
    try:
        return subprocess.run(["git", *a], capture_output=True, text=True, cwd=ROOT).stdout.strip()
    except Exception:
        return None


def main(n_seeds=100, workers=12):
    os.makedirs(OUTDIR, exist_ok=True)

    det = run_deterministic()
    _write_csv(os.path.join(OUTDIR, "deterministic_raw.csv"), det)
    print(f"wrote deterministic_raw.csv ({len(det)} rows)")

    sto = run_stochastic(n_seeds, workers)
    _write_csv(os.path.join(OUTDIR, "stochastic_raw.csv"), sto)
    print(f"wrote stochastic_raw.csv ({len(sto)} rows)")

    # ---- summary per (N, mode) ----
    METRICS = ["total_energy_kwh", "active_miner_seconds", "idle_miner_seconds",
               "pct_time_active", "avg_discovery_time_s", "duplicate_header_evaluations",
               "unique_candidate_evaluations", "successful_rounds"]
    summ = []
    for N in STO_MINERS:
        for mode in MODES:
            sub = [r for r in sto if r["N"] == N and r["mode"] == mode]
            row = {"N": N, "mode": mode, "n_seeds": len(sub)}
            for met in METRICS:
                s = st.summarize([r[met] for r in sub])
                for k, v in s.items():
                    row[f"{met}__{k}"] = v
            row["exhaustion_probability"] = np.mean([not r["successful_rounds"] for r in sub]) \
                if sub else float("nan")
            summ.append(row)
    _write_csv(os.path.join(OUTDIR, "summary_statistics.csv"), summ)
    print(f"wrote summary_statistics.csv ({len(summ)} rows)")

    # ---- paired comparisons: B vs A, B vs C1, B vs C2 (paired by seed) ----
    def _by_seed(mode, N):
        d = {r["seed"]: r for r in sto if r["N"] == N and r["mode"] == mode}
        return d
    paired = []
    for N in STO_MINERS:
        bB = _by_seed(MODE_B, N)
        for other in (MODE_A, MODE_C1, MODE_C2):
            bO = _by_seed(other, N)
            seeds = sorted(set(bB) & set(bO))
            eB = [bB[s]["total_energy_kwh"] for s in seeds]
            eO = [bO[s]["total_energy_kwh"] for s in seeds]
            pd = st.paired_diff(eO, eB)          # d = B - other
            rec = {"N": N, "comparison": f"B_minus_{other}", "metric": "total_energy_kwh",
                   "other_mean": float(np.mean(eO)) if eO else float("nan"),
                   "B_mean": float(np.mean(eB)) if eB else float("nan"), **pd}
            if other == MODE_C1:
                margin = BC1_MARGIN_REL * (float(np.mean(eO)) if eO else 0.0)
                rec.update({f"tost_{k}": v for k, v in st.tost_equivalence(eO, eB, margin).items()})
            paired.append(rec)
    _write_csv(os.path.join(OUTDIR, "paired_comparisons.csv"), paired,
               fieldnames=sorted({k for r in paired for k in r}))
    print(f"wrote paired_comparisons.csv ({len(paired)} rows)")

    # ---- per-miner energy (representative deterministic run) ----
    cfg = ExperimentConfig(N=10, M=_M_for(HW_H2, 10), mode=MODE_B,
                           schedule=SCHED_FIXED_SLOT, hardware=HW_H2,
                           power=PowerConfig(idle_ratio=0.10), slot_seconds=STO_SLOT,
                           sim_seconds=STO_SIM)
    _, miners = simulate_continuous(cfg, deterministic_outcome)
    pm = [dict(mode=MODE_B, N=10, **m.to_dict()) for m in miners]
    _write_csv(os.path.join(OUTDIR, "per_miner_energy.csv"), pm,
               fieldnames=sorted(pm[0].keys()))
    print(f"wrote per_miner_energy.csv ({len(pm)} rows)")

    # ---- configuration + manifest ----
    config = {
        "experiment": "continuous_distributed_effort",
        "modes": {"A": MODE_A, "B": MODE_B, "C1": MODE_C1, "C2": MODE_C2},
        "deterministic": {"miner_counts": MINER_COUNTS, "schedules": SCHEDULES,
                          "hardware": HARDWARES, "idle_ratios": IDLE_RATIOS,
                          "sleep_ratios": SLEEP_RATIOS, "solution": "final nonce M-1"},
        "stochastic": {"miner_counts": STO_MINERS, "M": STO_M, "p_success": STO_P,
                       "idle_ratio": STO_IDLE, "hardware": HW_H2, "schedule": SCHED_FIXED_SLOT,
                       "slot_seconds": STO_SLOT, "sim_seconds": STO_SIM, "n_seeds": n_seeds,
                       "fresh_subprocess_per_run": True,
                       "note": ("energy RATIOS are hardware-independent, so H2 stochastic "
                                "ratios transfer to H1; H1 IMMEDIATE_RESTART = 8.4208 kWh.")},
        "formula": "reduction = (1-q)(1-1/N); E_B/E_A = 1/N + q(1-1/N)",
        "bc1_equivalence_margin_rel_preregistered": BC1_MARGIN_REL,
        "energy_model": "state power integrated over wall-clock time; never energy/N",
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
        "reproduce": f"python experiments/continuous_distributed_effort/run_matrix.py {n_seeds} {workers}",
        "protected_unchanged": ["results/corrected/", "results/nonce_partition_worst_case/"],
    }
    with open(os.path.join(OUTDIR, "reproducibility_manifest.json"), "w") as fh:
        json.dump(manifest, fh, indent=2)
    print("wrote configuration.json + reproducibility_manifest.json")

    # ---- console headline ----
    print("\n=== deterministic FIXED_SLOT H2 energy reduction % vs A (idle q) ===")
    print("  N " + "".join(f"{('q='+str(q)):>10}" for q in IDLE_RATIOS))
    for N in [2, 10, 100, 500]:
        cells = []
        for q in IDLE_RATIOS:
            r = next(x for x in det if x["hardware"] == HW_H2 and x["N"] == N
                     and x["schedule"] == SCHED_FIXED_SLOT and x["idle_ratio"] == q
                     and x["mode"] == MODE_B)
            cells.append(f"{r['energy_reduction_pct_vs_A']:>10.2f}")
        print(f"{N:>4}" + "".join(cells))
    return det, sto, summ, paired


if __name__ == "__main__":
    ns = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    wk = int(sys.argv[2]) if len(sys.argv) > 2 else 12
    main(ns, wk)
