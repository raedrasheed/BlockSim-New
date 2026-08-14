"""Stage 8X — execution driver.

    python -m experiments.stage8x.run --phase pilot
    python -m experiments.stage8x.run --phase primary
    python -m experiments.stage8x.run --phase secondary

Execution integrity
-------------------
* Every phase writes to its own CSV under ``experiments/stage8x/outputs/``.
  Nothing outside ``experiments/stage8x/`` is ever written.
* Runs are resumable: an existing output CSV is read first and completed
  ``run_id`` values are skipped, so a resumed execution never duplicates a valid
  completed run and never silently re-runs one.
* Failures are recorded in ``<phase>_failures.log`` and do not abort the matrix;
  the completeness audit then reports the missing runs.
* Raw values are written unrounded.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
import time
import traceback
from typing import Dict, Iterable, List

from experiments.stage8x.config import seeds as seedmod
from experiments.stage8x.config import stage8x_config as C
from experiments.stage8x.config.asic import ALPHA_CASES, S21_PRO
from experiments.stage8x.simulator import energy as energymod
from experiments.stage8x.simulator.engine import RunResult, simulate

PHASE_FILES = {
    "pilot": "stage8x_pilot_runs.csv",
    "primary": "stage8x_physical_runs.csv",
    "secondary": "stage8x_secondary_runs.csv",
}
INTERVAL_FILES = {
    "pilot": "stage8x_pilot_block_intervals.csv",
    "primary": "stage8x_block_intervals.csv",
    "secondary": "stage8x_secondary_block_intervals.csv",
}
ENERGY_SENSITIVITY_FILE = "stage8x_energy_sensitivity.csv"

RAW_FIELDS = [
    "run_id", "phase", "protocol", "protocol_label", "N", "seed", "seed_index", "tag",
    "miner_hashrate_THs", "aggregate_hashrate_THs",
    "active_power_W_per_miner", "aggregate_full_power_W",
    "difficulty", "target", "q_per_candidate",
    "simulation_seconds", "epoch_sweep_s", "nonce_domain", "range_per_miner",
    "accepted_blocks", "closed_rounds", "blocks_created", "blocks_per_hour",
    "total_evaluations", "unique_evaluations", "duplicate_evaluations",
    "duplicate_ratio", "distinct_nonce_values", "nonce_value_reuse_ratio", "n_templates",
    "active_miner_seconds", "low_power_miner_seconds", "low_power_fraction",
    "mean_block_interval", "median_block_interval", "sd_block_interval",
    "p95_block_interval", "stale_blocks", "stale_rate",
    "range_completions", "epoch_exhaustions", "exhaustion_count",
    "domain_artifact_exhaustions",
    "active_to_low_transitions", "low_to_active_transitions", "low_episodes",
    "mean_low_duration_s", "median_low_duration_s", "max_low_duration_s",
    "miners_entering_low", "fraction_miners_entering_low",
    "mean_simultaneous_low_miners", "max_simultaneous_low_miners",
    "state_time_conservation_error_s", "work_accounting_error",
    "energy_active_J", "energy_total_J_LP0", "energy_total_kWh_LP0",
    "execution_time_seconds", "commit_hash", "config_hash",
]

ENERGY_FIELDS = [
    "run_id", "pow_run_id", "N", "seed", "seed_index", "alpha", "alpha_label",
    "P_active_W_per_miner", "P_low_W_per_miner",
    "PoW_energy_J", "PoW_energy_kWh", "PoCol_energy_J", "PoCol_energy_kWh",
    "PoCol_active_energy_kWh", "PoCol_low_power_energy_kWh",
    "paired_energy_difference_kWh", "paired_energy_saving_fraction",
    "PoW_energy_per_accepted_block_kWh", "PoCol_energy_per_accepted_block_kWh",
    "PoW_energy_per_closed_round_kWh", "PoCol_energy_per_closed_round_kWh",
    "PoW_accepted_blocks", "PoCol_accepted_blocks", "block_retention",
    "PoW_median_block_interval", "PoCol_median_block_interval", "latency_ratio",
    "low_power_fraction", "active_miner_seconds", "low_power_miner_seconds",
    "alpha_case",
]


# --------------------------------------------------------------------------
def git_commit_hash() -> str:
    try:
        out = subprocess.run(["git", "rev-parse", "HEAD"], cwd=C.REPO_ROOT,
                             capture_output=True, text=True, timeout=30)
        return out.stdout.strip() or "UNKNOWN"
    except Exception:
        return "UNKNOWN"


def _na(v):
    """NA stays NA: never substitute zero for an undefined quantity."""
    return "" if v is None else v


def result_row(r: RunResult, cfg: C.RunConfig, commit: str, cfghash: str) -> Dict:
    ps = r.power_state_summary
    e0 = energymod.account(r.active_miner_seconds, r.low_power_miner_seconds,
                           S21_PRO.active_power_w, 0.0)
    return {
        "run_id": r.run_id, "phase": cfg.phase, "protocol": r.protocol,
        "protocol_label": C.PROTOCOL_LABELS[r.protocol],
        "N": r.n_miners, "seed": r.seed, "seed_index": r.seed_index, "tag": cfg.tag,
        "miner_hashrate_THs": r.miner_hashrate_THs,
        "aggregate_hashrate_THs": r.aggregate_hashrate_THs,
        "active_power_W_per_miner": r.active_power_W_per_miner,
        "aggregate_full_power_W": r.aggregate_full_power_W,
        "difficulty": repr(r.difficulty), "target": r.target_hex,
        "q_per_candidate": repr(r.q_per_candidate),
        "simulation_seconds": r.simulation_seconds, "epoch_sweep_s": r.epoch_sweep_s,
        "nonce_domain": r.nonce_domain, "range_per_miner": r.range_per_miner,
        "accepted_blocks": r.accepted_blocks, "closed_rounds": r.closed_rounds,
        "blocks_created": r.blocks_created, "blocks_per_hour": repr(r.blocks_per_hour),
        "total_evaluations": r.total_evaluations,
        "unique_evaluations": r.unique_evaluations,
        "duplicate_evaluations": r.duplicate_evaluations,
        "duplicate_ratio": _na(r.duplicate_ratio),
        "distinct_nonce_values": r.distinct_nonce_values,
        "nonce_value_reuse_ratio": _na(r.nonce_value_reuse_ratio),
        "n_templates": r.n_templates,
        "active_miner_seconds": repr(r.active_miner_seconds),
        "low_power_miner_seconds": repr(r.low_power_miner_seconds),
        "low_power_fraction": repr(r.low_power_fraction),
        "mean_block_interval": _na(r.mean_block_interval),
        "median_block_interval": _na(r.median_block_interval),
        "sd_block_interval": _na(r.sd_block_interval),
        "p95_block_interval": _na(r.p95_block_interval),
        "stale_blocks": r.stale_blocks, "stale_rate": _na(r.stale_rate),
        "range_completions": r.range_completions,
        "epoch_exhaustions": r.epoch_exhaustions,
        "exhaustion_count": r.epoch_exhaustions,
        "domain_artifact_exhaustions": r.domain_artifact_exhaustions,
        "active_to_low_transitions": ps["active_to_low_transitions"],
        "low_to_active_transitions": ps["low_to_active_transitions"],
        "low_episodes": ps["low_episodes"],
        "mean_low_duration_s": repr(ps["mean_low_duration_s"]),
        "median_low_duration_s": repr(ps["median_low_duration_s"]),
        "max_low_duration_s": repr(ps["max_low_duration_s"]),
        "miners_entering_low": ps["miners_entering_low"],
        "fraction_miners_entering_low": repr(ps["fraction_miners_entering_low"]),
        "mean_simultaneous_low_miners": repr(ps["mean_simultaneous_low_miners"]),
        "max_simultaneous_low_miners": ps["max_simultaneous_low_miners"],
        "state_time_conservation_error_s": repr(ps["state_time_conservation_error_s"]),
        "work_accounting_error": repr(r.work_accounting_error),
        "energy_active_J": repr(e0.active_energy_j),
        "energy_total_J_LP0": repr(e0.total_energy_j),
        "energy_total_kWh_LP0": repr(e0.total_energy_kwh),
        "execution_time_seconds": repr(r.execution_time_seconds),
        "commit_hash": commit, "config_hash": cfghash,
    }


def _read_done(path: str) -> set:
    if not os.path.exists(path):
        return set()
    with open(path, newline="", encoding="utf-8") as fh:
        return {row["run_id"] for row in csv.DictReader(fh)}


def _append_rows(path: str, fields: List[str], rows: Iterable[Dict]) -> None:
    new = not os.path.exists(path)
    with open(path, "a", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        if new:
            w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fields})


# --------------------------------------------------------------------------
def execute_phase(phase: str, force: bool = False) -> Dict:
    C.ensure_dirs()
    seedmod.write_registry(C.SEEDS_JSON)

    matrix = {"pilot": C.pilot_matrix, "primary": C.primary_matrix,
              "secondary": C.secondary_matrix}[phase]()
    out_path = os.path.join(C.OUT_DIR, PHASE_FILES[phase])
    iv_path = os.path.join(C.OUT_DIR, INTERVAL_FILES[phase])
    log_path = os.path.join(C.OUT_DIR, f"{phase}_progress.log")
    fail_path = os.path.join(C.OUT_DIR, f"{phase}_failures.log")

    if force:
        for p in (out_path, iv_path):
            if os.path.exists(p):
                os.remove(p)

    done = _read_done(out_path)
    commit, cfghash = git_commit_hash(), C.config_hash()
    todo = [c for c in matrix if c.run_id not in done]

    print(f"[stage8x:{phase}] matrix={len(matrix)} done={len(done)} todo={len(todo)}")
    t0 = time.time()
    completed, failed = 0, 0
    with open(log_path, "a", encoding="utf-8") as log:
        log.write(f"=== {phase} start {time.strftime('%Y-%m-%dT%H:%M:%S')} "
                  f"commit={commit} config={cfghash} todo={len(todo)}\n")
        for i, cfg in enumerate(todo, start=1):
            try:
                r = simulate(cfg)
                _append_rows(out_path, RAW_FIELDS,
                             [result_row(r, cfg, commit, cfghash)])
                _append_rows(iv_path, ["run_id", "protocol", "N", "seed_index",
                                       "block_index", "interval_s"],
                             [{"run_id": r.run_id, "protocol": r.protocol,
                               "N": r.n_miners, "seed_index": r.seed_index,
                               "block_index": j, "interval_s": repr(v)}
                              for j, v in enumerate(r.block_intervals, start=1)])
                completed += 1
                log.write(f"OK {r.run_id} blocks={r.accepted_blocks} "
                          f"Flow={r.low_power_fraction:.6e} "
                          f"wall={r.execution_time_seconds:.3f}\n")
            except Exception:
                failed += 1
                with open(fail_path, "a", encoding="utf-8") as fl:
                    fl.write(f"FAIL {cfg.run_id}\n{traceback.format_exc()}\n")
                log.write(f"FAIL {cfg.run_id}\n")
            if i % 25 == 0 or i == len(todo):
                el = time.time() - t0
                print(f"  {i}/{len(todo)} ok={completed} fail={failed} "
                      f"elapsed={el:.1f}s")
                log.flush()
        log.write(f"=== {phase} end completed={completed} failed={failed} "
                  f"elapsed={time.time() - t0:.1f}s\n")

    summary = {"phase": phase, "matrix": len(matrix), "completed": completed,
               "failed": failed, "already_done": len(done),
               "elapsed_s": time.time() - t0, "output": out_path,
               "commit": commit, "config_hash": cfghash}
    print(f"[stage8x:{phase}] {json.dumps(summary)}")
    return summary


# --------------------------------------------------------------------------
def build_energy_sensitivity() -> str:
    """Re-price every PoCol physical trajectory under the four alpha cases.

    One row per (PoCol physical run x alpha) = 150 x 4 = 600 rows, each carrying
    its paired PoW reference. This is *accounting*, not simulation: no additional
    physical runs are performed.
    """
    raw = os.path.join(C.OUT_DIR, PHASE_FILES["primary"])
    with open(raw, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))

    pow_by = {(int(r["N"]), int(r["seed_index"])): r
              for r in rows if r["protocol"] == C.PROTO_POW}
    out_rows = []
    for r in rows:
        if r["protocol"] != C.PROTO_POCOL:
            continue
        key = (int(r["N"]), int(r["seed_index"]))
        pw = pow_by.get(key)
        if pw is None:
            continue
        pw_e = energymod.account(float(pw["active_miner_seconds"]),
                                 float(pw["low_power_miner_seconds"]),
                                 S21_PRO.active_power_w, 0.0)
        pw_blocks = int(pw["accepted_blocks"])
        pc_blocks = int(r["accepted_blocks"])
        pw_med = float(pw["median_block_interval"]) if pw["median_block_interval"] else None
        pc_med = float(r["median_block_interval"]) if r["median_block_interval"] else None
        for label, alpha in ALPHA_CASES.items():
            pc_e = energymod.account(float(r["active_miner_seconds"]),
                                     float(r["low_power_miner_seconds"]),
                                     S21_PRO.active_power_w, alpha)
            out_rows.append({
                "run_id": r["run_id"], "pow_run_id": pw["run_id"],
                "N": key[0], "seed": r["seed"], "seed_index": key[1],
                "alpha": alpha, "alpha_label": label, "alpha_case": label,
                "P_active_W_per_miner": S21_PRO.active_power_w,
                "P_low_W_per_miner": S21_PRO.low_power_w(alpha),
                "PoW_energy_J": repr(pw_e.total_energy_j),
                "PoW_energy_kWh": repr(pw_e.total_energy_kwh),
                "PoCol_energy_J": repr(pc_e.total_energy_j),
                "PoCol_energy_kWh": repr(pc_e.total_energy_kwh),
                "PoCol_active_energy_kWh": repr(pc_e.active_energy_kwh),
                "PoCol_low_power_energy_kWh": repr(pc_e.low_power_energy_kwh),
                "paired_energy_difference_kWh": repr(
                    pc_e.total_energy_kwh - pw_e.total_energy_kwh),
                "paired_energy_saving_fraction": _na(
                    energymod.energy_saving_fraction(pc_e.total_energy_kwh,
                                                     pw_e.total_energy_kwh)),
                "PoW_energy_per_accepted_block_kWh": _na(
                    pw_e.energy_per_block_kwh(pw_blocks)),
                "PoCol_energy_per_accepted_block_kWh": _na(
                    pc_e.energy_per_block_kwh(pc_blocks)),
                "PoW_energy_per_closed_round_kWh": _na(
                    pw_e.energy_per_round_kwh(int(pw["closed_rounds"]))),
                "PoCol_energy_per_closed_round_kWh": _na(
                    pc_e.energy_per_round_kwh(int(r["closed_rounds"]))),
                "PoW_accepted_blocks": pw_blocks,
                "PoCol_accepted_blocks": pc_blocks,
                "block_retention": _na(pc_blocks / pw_blocks if pw_blocks else None),
                "PoW_median_block_interval": _na(pw_med),
                "PoCol_median_block_interval": _na(pc_med),
                "latency_ratio": _na(pc_med / pw_med if (pw_med and pc_med) else None),
                "low_power_fraction": r["low_power_fraction"],
                "active_miner_seconds": r["active_miner_seconds"],
                "low_power_miner_seconds": r["low_power_miner_seconds"],
            })

    path = os.path.join(C.OUT_DIR, ENERGY_SENSITIVITY_FILE)
    if os.path.exists(path):
        os.remove(path)
    _append_rows(path, ENERGY_FIELDS, out_rows)
    print(f"[stage8x] energy sensitivity rows={len(out_rows)} -> {path}")
    return path


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Stage 8X execution driver")
    ap.add_argument("--phase", required=True, choices=["pilot", "primary", "secondary"])
    ap.add_argument("--force", action="store_true",
                    help="discard existing phase output and re-run the whole matrix")
    args = ap.parse_args(argv)

    summary = execute_phase(args.phase, force=args.force)
    if args.phase == "primary":
        build_energy_sensitivity()
    return 0 if summary["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
