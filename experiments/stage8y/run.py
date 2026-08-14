"""Stage 8Y — execution driver.

    python -m experiments.stage8y.run --phase pilot
    python -m experiments.stage8y.run --phase primary
    python -m experiments.stage8y.run --phase secondary
    python -m experiments.stage8y.run --phase longhorizon

Every phase writes to its own CSV under ``experiments/stage8y/outputs/``. Runs are
resumable by ``run_id``: completed runs are skipped and never duplicated. Failures
are logged and do not abort the matrix. Raw values are written unrounded.
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

from experiments.stage8y.config import seeds as seedmod
from experiments.stage8y.config import stage8y_config as C
from experiments.stage8y.src import energy as em
from experiments.stage8y.src import metrics as mx
from experiments.stage8y.src.engine import RunResult, simulate

PHASE_FILES = {
    "pilot": "stage8y_pilot_runs.csv",
    "primary": "stage8y_physical_runs.csv",
    "secondary": "stage8y_secondary_runs.csv",
    "longhorizon": "stage8y_longhorizon_runs.csv",
}
TRACE_FILES = {p: f.replace("_runs.csv", "_traces.csv") for p, f in PHASE_FILES.items()}
INTERVAL_FILES = {p: f.replace("_runs.csv", "_intervals.csv")
                  for p, f in PHASE_FILES.items()}
ENERGY_FILES = {p: f.replace("_runs.csv", "_energy.csv") for p, f in PHASE_FILES.items()}

BASE_FIELDS = [
    "run_id", "phase", "protocol", "protocol_label", "composition", "N", "seed",
    "seed_index", "tag", "horizon_s",
    "H_N_Hps", "H_N_THs", "P_N_W", "eta_network_J_per_TH",
    "difficulty", "target", "q_per_candidate", "nonce_domain", "domain_semantics",
    "allocation", "selection_rule", "target_hash_fraction", "target_count_fraction",
    "reserve_schedule", "trigger_s", "wake_s",
    "n_active_initial", "r_count_initial", "r_hash_initial", "r_power_initial",
    "accepted_blocks", "closed_rounds", "blocks_created", "stale_blocks", "stale_rate",
    "blocks_per_hour", "mean_block_interval", "median_block_interval",
    "sd_block_interval", "p95_block_interval",
    "total_evaluations", "unique_evaluations", "duplicate_evaluations",
    "duplicate_ratio", "distinct_nonce_values", "nonce_value_reuse_ratio",
    "n_templates", "stale_evaluations", "useful_chain_evaluations",
    "reserve_activations", "stage_max_reached", "epoch_exhaustions",
    "range_completions", "work_accounting_error", "execution_time_seconds",
    "commit_hash", "config_hash",
]
PS_FIELDS = [
    "t_active_miner_s", "t_low_miner_s", "t_standby_miner_s", "t_waking_miner_s",
    "F_active", "F_low", "F_standby", "F_waking", "F_parked_minertime",
    "F_parked_power_weighted", "pw_active_Ws", "pw_low_Ws", "pw_standby_Ws",
    "pw_waking_Ws", "integral_H_active_hashes", "integral_P_active_Ws",
    "integral_P_waking_Ws", "integral_P_parked_nominal_Ws",
    "mean_h_active_fraction", "mean_p_drawn_fraction", "min_h_active_fraction",
    "wake_events", "low_episodes", "mean_low_episode_s", "max_low_episode_s",
    "standby_episodes", "mean_standby_episode_s", "miners_entering_low",
    "miners_entering_standby", "state_time_conservation_error_s",
    "min_state_residence_s",
]
METRIC_FIELDS = [
    "HashCapacityResidence_hashes", "PowerResidence_Ws", "CapacityRemovedFraction",
    "PowerRemovedFraction", "SelectivityGain", "SelectivityGain_defined",
    "mean_SecurityHashFraction", "min_SecurityHashFraction", "mean_PowerDrawnFraction",
    "gini_blocks_by_miner", "gini_active_time_by_miner",
    "miners_with_zero_active_time", "miners_with_zero_blocks",
]
DEVICE_KEYS = ("S21PRO", "S19XP", "S19JPRO")
DEVICE_FIELDS = []
for _k in DEVICE_KEYS:
    DEVICE_FIELDS += [f"participation_share_{_k}", f"reward_share_{_k}",
                      f"active_time_share_{_k}", f"installed_hash_share_{_k}",
                      f"selection_frequency_{_k}", f"n_{_k}", f"blocks_won_{_k}"]

RAW_FIELDS = BASE_FIELDS + PS_FIELDS + METRIC_FIELDS + DEVICE_FIELDS

ENERGY_FIELDS = [
    "run_id", "pow_run_id", "phase", "protocol", "composition", "N", "seed_index",
    "tag", "alpha_case", "alpha", "is_idealized_alpha", "P_low_note",
    "PoW_energy_J", "PoW_energy_kWh", "PoCol_energy_J", "PoCol_energy_kWh",
    "PoCol_active_J", "PoCol_waking_J", "PoCol_low_J", "PoCol_standby_J",
    "paired_energy_difference_kWh", "EnergySaving",
    "PoW_energy_per_block_kWh", "PoCol_energy_per_block_kWh",
    "PoW_energy_per_round_kWh", "PoCol_energy_per_round_kWh",
    "PoW_accepted_blocks", "PoCol_accepted_blocks", "BlockRetention",
    "LatencyRatio_median", "LatencyRatio_mean", "HashRetention",
    "mean_SecurityHashFraction", "min_SecurityHashFraction",
    "CapacityRemovedFraction", "PowerRemovedFraction", "SelectivityGain",
    "F_low", "F_standby", "F_parked_power_weighted",
    "dE_total_J", "dE_participation_J", "dE_selection_J",
    "share_participation", "share_selection",
    "dE_participation_shapley_J", "dE_selection_shapley_J",
    "share_participation_shapley", "share_selection_shapley",
    "dE_postrange_J", "dE_reserve_J", "share_postrange", "share_reserve",
    "dE_stale_J", "decomposition_residual_J", "power_identity_error_Ws",
]


def git_commit_hash() -> str:
    try:
        out = subprocess.run(["git", "rev-parse", "HEAD"], cwd=C.REPO_ROOT,
                             capture_output=True, text=True, timeout=30)
        return out.stdout.strip() or "UNKNOWN"
    except Exception:
        return "UNKNOWN"


def _na(v):
    return "" if v is None else v


def result_row(r: RunResult, cfg: C.RunConfig, commit: str, cfghash: str) -> Dict:
    ps = r.power_state
    m = mx.participation_metrics(ps, r.H_N_Hps, r.P_N_W, r.horizon_s)
    f = mx.fairness_metrics(r.device_stats, r.blocks_by_miner,
                            r.active_seconds_by_miner, r.n_miners, r.horizon_s)
    row = {
        "run_id": r.run_id, "phase": cfg.phase, "protocol": r.protocol,
        "protocol_label": C.PROTOCOL_LABELS[r.protocol],
        "composition": r.composition, "N": r.n_miners, "seed": r.seed,
        "seed_index": r.seed_index, "tag": r.tag, "horizon_s": r.horizon_s,
        "H_N_Hps": repr(r.H_N_Hps), "H_N_THs": repr(r.H_N_Hps / 1e12),
        "P_N_W": repr(r.P_N_W),
        "eta_network_J_per_TH": repr(r.eta_network_J_per_TH),
        "difficulty": repr(r.difficulty), "target": r.target_hex,
        "q_per_candidate": repr(r.q_per_candidate), "nonce_domain": r.nonce_domain,
        "domain_semantics": r.domain_semantics, "allocation": r.allocation,
        "selection_rule": r.selection_rule,
        "target_hash_fraction": _na(r.target_hash_fraction),
        "target_count_fraction": _na(r.target_count_fraction),
        "reserve_schedule": r.reserve_schedule, "trigger_s": r.trigger_s,
        "wake_s": r.wake_s,
        "n_active_initial": r.n_active_initial,
        "r_count_initial": repr(r.r_count_initial),
        "r_hash_initial": repr(r.r_hash_initial),
        "r_power_initial": repr(r.r_power_initial),
        "accepted_blocks": r.accepted_blocks, "closed_rounds": r.closed_rounds,
        "blocks_created": r.blocks_created, "stale_blocks": r.stale_blocks,
        "stale_rate": _na(r.stale_rate), "blocks_per_hour": repr(r.blocks_per_hour),
        "mean_block_interval": _na(r.mean_block_interval),
        "median_block_interval": _na(r.median_block_interval),
        "sd_block_interval": _na(r.sd_block_interval),
        "p95_block_interval": _na(r.p95_block_interval),
        "total_evaluations": r.total_evaluations,
        "unique_evaluations": r.unique_evaluations,
        "duplicate_evaluations": r.duplicate_evaluations,
        "duplicate_ratio": _na(r.duplicate_ratio),
        "distinct_nonce_values": r.distinct_nonce_values,
        "nonce_value_reuse_ratio": _na(r.nonce_value_reuse_ratio),
        "n_templates": r.n_templates,
        "stale_evaluations": repr(r.stale_evaluations),
        "useful_chain_evaluations": repr(r.useful_chain_evaluations),
        "reserve_activations": r.reserve_activations,
        "stage_max_reached": r.stage_max_reached,
        "epoch_exhaustions": r.epoch_exhaustions,
        "range_completions": r.range_completions,
        "work_accounting_error": repr(r.work_accounting_error),
        "execution_time_seconds": repr(r.execution_time_seconds),
        "commit_hash": commit, "config_hash": cfghash,
    }
    for k in PS_FIELDS:
        row[k] = repr(ps[k]) if isinstance(ps.get(k), float) else ps.get(k, "")
    for k in METRIC_FIELDS:
        v = m.get(k, f.get(k))
        row[k] = repr(v) if isinstance(v, float) else _na(v)
    for k in DEVICE_KEYS:
        st = r.device_stats.get(k)
        row[f"n_{k}"] = st["count"] if st else 0
        row[f"blocks_won_{k}"] = st["blocks_won"] if st else 0
        for fld in ("participation_share", "reward_share", "active_time_share",
                    "installed_hash_share", "selection_frequency"):
            v = f.get(f"{fld}_{k}")
            row[f"{fld}_{k}"] = repr(v) if isinstance(v, float) else _na(v)
    return row


def _read_done(path: str) -> set:
    if not os.path.exists(path):
        return set()
    with open(path, newline="", encoding="utf-8") as fh:
        return {row["run_id"] for row in csv.DictReader(fh)}


def _append(path: str, fields: List[str], rows: Iterable[Dict]) -> None:
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
              "secondary": C.secondary_matrix,
              "longhorizon": C.longhorizon_matrix}[phase]()

    out_path = os.path.join(C.OUT_DIR, PHASE_FILES[phase])
    iv_path = os.path.join(C.OUT_DIR, INTERVAL_FILES[phase])
    tr_path = os.path.join(C.OUT_DIR, TRACE_FILES[phase])
    log_path = os.path.join(C.OUT_DIR, f"{phase}_progress.log")
    fail_path = os.path.join(C.OUT_DIR, f"{phase}_failures.log")
    if force:
        for p in (out_path, iv_path, tr_path):
            if os.path.exists(p):
                os.remove(p)

    done = _read_done(out_path)
    commit, cfghash = git_commit_hash(), C.config_hash()
    todo = [c for c in matrix if c.run_id not in done]
    print(f"[stage8y:{phase}] matrix={len(matrix)} done={len(done)} todo={len(todo)}")

    t0 = time.time()
    completed = failed = 0
    with open(log_path, "a", encoding="utf-8") as log:
        log.write(f"=== {phase} start {time.strftime('%Y-%m-%dT%H:%M:%S')} "
                  f"commit={commit} config={cfghash} todo={len(todo)}\n")
        for i, cfg in enumerate(todo, start=1):
            try:
                r = simulate(cfg)
                _append(out_path, RAW_FIELDS, [result_row(r, cfg, commit, cfghash)])
                _append(iv_path, ["run_id", "protocol", "composition", "N",
                                  "seed_index", "block_index", "interval_s"],
                        [{"run_id": r.run_id, "protocol": r.protocol,
                          "composition": r.composition, "N": r.n_miners,
                          "seed_index": r.seed_index, "block_index": j,
                          "interval_s": repr(v)}
                         for j, v in enumerate(r.block_intervals, start=1)])
                # traces are large: keep only seed 1 of each configuration
                if r.seed_index == 1:
                    _append(tr_path, ["run_id", "protocol", "composition", "N",
                                      "t", "h_active_fraction", "p_drawn_fraction"],
                            [{"run_id": r.run_id, "protocol": r.protocol,
                              "composition": r.composition, "N": r.n_miners,
                              "t": repr(t), "h_active_fraction": repr(hf),
                              "p_drawn_fraction": repr(pf)}
                             for t, hf, pf in r.trace_h_active])
                completed += 1
                log.write(f"OK {r.run_id} blk={r.accepted_blocks} "
                          f"meanH={r.power_state['mean_h_active_fraction']:.4f} "
                          f"meanP={r.power_state['mean_p_drawn_fraction']:.4f}\n")
            except Exception:
                failed += 1
                with open(fail_path, "a", encoding="utf-8") as fl:
                    fl.write(f"FAIL {cfg.run_id}\n{traceback.format_exc()}\n")
                log.write(f"FAIL {cfg.run_id}\n")
            if i % 100 == 0 or i == len(todo):
                print(f"  {i}/{len(todo)} ok={completed} fail={failed} "
                      f"elapsed={time.time() - t0:.1f}s")
                log.flush()
        log.write(f"=== {phase} end completed={completed} failed={failed} "
                  f"elapsed={time.time() - t0:.1f}s\n")

    summary = {"phase": phase, "matrix": len(matrix), "completed": completed,
               "failed": failed, "already_done": len(done),
               "elapsed_s": time.time() - t0, "output": out_path,
               "commit": commit, "config_hash": cfghash}
    print(f"[stage8y:{phase}] {json.dumps(summary)}")
    return summary


# --------------------------------------------------------------------------
def build_energy_table(phase: str) -> str:
    """Re-price every PoCol trajectory under each alpha against its paired PoW run.

    This is accounting, not simulation: no additional physical run is performed.
    """
    raw = os.path.join(C.OUT_DIR, PHASE_FILES[phase])
    with open(raw, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))

    pow_by = {(r["composition"], r["N"], r["seed_index"]): r
              for r in rows if r["protocol"] == C.POW}
    out: List[Dict] = []
    for r in rows:
        if r["protocol"] not in C.POCOL_PROTOCOLS:
            continue
        key = (r["composition"], r["N"], r["seed_index"])
        pw = pow_by.get(key)
        if pw is None:
            continue
        T = float(r["horizon_s"])
        h_total, p_total = float(r["H_N_Hps"]), float(r["P_N_W"])
        pw_energy = em.account(float(pw["pw_active_Ws"]), float(pw["pw_waking_Ws"]),
                               float(pw["pw_low_Ws"]), float(pw["pw_standby_Ws"]), 0.0)
        ps_pc = {k: float(r[k]) for k in ("pw_active_Ws", "pw_waking_Ws", "pw_low_Ws",
                                          "pw_standby_Ws", "integral_H_active_hashes",
                                          "integral_P_active_Ws",
                                          "integral_P_waking_Ws")}
        svc = mx.paired_service_metrics(
            {"accepted_blocks": int(r["accepted_blocks"]),
             "median_block_interval": float(r["median_block_interval"])
             if r["median_block_interval"] else None,
             "mean_block_interval": float(r["mean_block_interval"])
             if r["mean_block_interval"] else None,
             "power_state": {"integral_H_active_hashes":
                             float(r["integral_H_active_hashes"])}},
            {"accepted_blocks": int(pw["accepted_blocks"]),
             "median_block_interval": float(pw["median_block_interval"])
             if pw["median_block_interval"] else None,
             "mean_block_interval": float(pw["mean_block_interval"])
             if pw["mean_block_interval"] else None,
             "power_state": {"integral_H_active_hashes":
                             float(pw["integral_H_active_hashes"])}})
        for label, alpha in C.ALPHA_CASES.items():
            pc = em.account(ps_pc["pw_active_Ws"], ps_pc["pw_waking_Ws"],
                            ps_pc["pw_low_Ws"], ps_pc["pw_standby_Ws"], alpha,
                            C.WAKE_POWER_RATIO)
            dec = mx.decompose_saving(ps_pc, h_total, p_total, T, alpha)
            out.append({
                "run_id": r["run_id"], "pow_run_id": pw["run_id"], "phase": phase,
                "protocol": r["protocol"], "composition": r["composition"],
                "N": int(r["N"]), "seed_index": int(r["seed_index"]), "tag": r["tag"],
                "alpha_case": label, "alpha": alpha,
                "is_idealized_alpha": label in C.IDEALIZED_ALPHA_LABELS,
                "P_low_note": "model assumption, not a manufacturer-certified mode",
                "PoW_energy_J": repr(pw_energy.total_J),
                "PoW_energy_kWh": repr(pw_energy.total_kWh),
                "PoCol_energy_J": repr(pc.total_J),
                "PoCol_energy_kWh": repr(pc.total_kWh),
                "PoCol_active_J": repr(pc.active_J), "PoCol_waking_J": repr(pc.waking_J),
                "PoCol_low_J": repr(pc.low_J), "PoCol_standby_J": repr(pc.standby_J),
                "paired_energy_difference_kWh": repr(pc.total_kWh - pw_energy.total_kWh),
                "EnergySaving": _na(em.saving_fraction(pc.total_kWh,
                                                       pw_energy.total_kWh)),
                "PoW_energy_per_block_kWh": _na(
                    pw_energy.per_block_kWh(int(pw["accepted_blocks"]))),
                "PoCol_energy_per_block_kWh": _na(
                    pc.per_block_kWh(int(r["accepted_blocks"]))),
                "PoW_energy_per_round_kWh": _na(
                    pw_energy.per_round_kWh(int(pw["closed_rounds"]))),
                "PoCol_energy_per_round_kWh": _na(
                    pc.per_round_kWh(int(r["closed_rounds"]))),
                "PoW_accepted_blocks": int(pw["accepted_blocks"]),
                "PoCol_accepted_blocks": int(r["accepted_blocks"]),
                "BlockRetention": _na(svc["BlockRetention"]),
                "LatencyRatio_median": _na(svc["LatencyRatio_median"]),
                "LatencyRatio_mean": _na(svc["LatencyRatio_mean"]),
                "HashRetention": _na(svc["HashRetention"]),
                "mean_SecurityHashFraction": r["mean_SecurityHashFraction"],
                "min_SecurityHashFraction": r["min_SecurityHashFraction"],
                "CapacityRemovedFraction": r["CapacityRemovedFraction"],
                "PowerRemovedFraction": r["PowerRemovedFraction"],
                "SelectivityGain": r["SelectivityGain"],
                "F_low": r["F_low"], "F_standby": r["F_standby"],
                "F_parked_power_weighted": r["F_parked_power_weighted"],
                **{k: repr(v) if isinstance(v, float) else _na(v)
                   for k, v in dec.items()
                   if k in ("dE_total_J", "dE_participation_J", "dE_selection_J",
                            "share_participation", "share_selection",
                            "dE_participation_shapley_J", "dE_selection_shapley_J",
                            "share_participation_shapley", "share_selection_shapley",
                            "dE_postrange_J", "dE_reserve_J", "share_postrange",
                            "share_reserve", "dE_stale_J",
                            "decomposition_residual_J", "power_identity_error_Ws")},
            })

    path = os.path.join(C.OUT_DIR, ENERGY_FILES[phase])
    if os.path.exists(path):
        os.remove(path)
    _append(path, ENERGY_FIELDS, out)
    print(f"[stage8y] {phase} energy observations={len(out)} -> {path}")
    return path


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Stage 8Y execution driver")
    ap.add_argument("--phase", required=True,
                    choices=["pilot", "primary", "secondary", "longhorizon"])
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args(argv)
    summary = execute_phase(args.phase, force=args.force)
    build_energy_table(args.phase)
    return 0 if summary["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
