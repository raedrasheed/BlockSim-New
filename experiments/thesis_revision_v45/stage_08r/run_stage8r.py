#!/usr/bin/env python3
"""Stage 8R — structural pilot + frozen execution harness.

Commands (in order):

    python run_stage8r.py pilot        # 4 scenarios x 2 FRESH pilot seeds, STRUCTURE ONLY
    python run_stage8r.py execute      # 4 x 12 = 48 runs, <= 2 workers, atomic checkpoints
    python run_stage8r.py verify       # re-verify every checkpoint checksum + timelines
    python run_stage8r.py dataset      # 48-row STAGE_08R_RUN_DATASET.csv + decomposition CSVs

The pilot validates ONLY: all modes execute; predictive activation fires; hysteresis
prevents duplicate batches; required fields exist; integrity gates are calculable; runtime
and memory are feasible.  No pilot effect magnitude is used to change any policy parameter
(0.78 / 0.80 / 0.82, lookahead, cooldown and the 25-nonce chunk are frozen).
Confirmatory execution is legal only AFTER the preregistration freeze commit.
"""
from __future__ import annotations

import dataclasses
import enum
import gzip
import hashlib
import json
import multiprocessing as mp
import os
import pathlib
import resource
import statistics
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
for p in (str(REPO_ROOT), str(HERE),
          str(REPO_ROOT / "experiments" / "thesis_revision_v45" / "stage_06"),
          str(REPO_ROOT / "experiments" / "thesis_revision_v45" / "stage_06m")):
    if p not in sys.path:
        sys.path.insert(0, p)

import scenarios_8r as S8                                                  # noqa: E402
from scenarios_6m import energy_pair_kwh                                   # noqa: E402
from run_pilot import (post_round_audit, residency_and_energy_identity,    # noqa: E402
                       round_durations, nonterminal_activation_request_count)
from Models.PoCol.stage2.simulator import run_simulation                   # noqa: E402
from Models.PoCol.stage2.adapter import results_schema, _controller_results  # noqa: E402
from Models.PoCol.stage2.config import a1_continuous_control_kwh           # noqa: E402
from Models.PoCol.stage2.refinement import TERMINAL_EPISODE_STATUSES       # noqa: E402

DOCS = REPO_ROOT / "docs" / "thesis_revision_v45" / "stage_08r"
RUNS = HERE / "runs"
TIMELINES = HERE / "timelines"
PILOT_OUT = HERE / "pilot"

MAX_WORKERS = 2
WALL_LIMIT_S = 600.0
RSS_LIMIT_MB = 4096.0
HORIZON = 300.0

ADVERSARIAL_COUNTERS = ("adversarial_entity_count", "adversarial_miner_count",
                        "adversarial_duplicate_evaluation_count",
                        "adversarial_coverage_gap_round_count",
                        "adversarial_reevaluation_count", "solution_withholding_count")

CONTROLLER_FIELDS = [
    "controller_mode", "breach_episode_count", "breach_episode_recovered_count",
    "episode_unattainable_count", "episode_round_closed_count",
    "episode_closed_with_live_activation_count", "total_episode_recovery_time_s",
    "mean_episode_recovery_time_s", "activation_batches_seated",
    "predictive_batches_seated", "reactive_batches_seated",
    "duplicate_activation_batch_prevented_count", "max_activation_batches_per_episode",
    "mean_activation_batches_per_episode", "activation_batch_terminal_count",
    "prediction_decision_count", "resolved_prediction_count",
    "unresolved_prediction_count", "mean_absolute_prediction_error",
    "false_positive_wake_count", "late_wake_count", "requested_reserve_hash_rate_total",
    "completed_reserve_hash_rate_total", "cancelled_reserve_hash_rate_total",
    "excess_activation_hash_rate_total", "under_activation_hash_rate_total",
    "maximum_H_pipeline", "time_weighted_H_pipeline",
    "duration_pipeline_above_target_while_H_effective_below_target",
    "controller_suffix_reassignment_count",
    "controller_suffix_reassignment_skipped_in_flight",
]


# ------------------------------------------------------------------ plan / ids / hashes
def run_plan() -> list:
    plan = []
    for row in S8.SCENARIOS:
        for i, seed in enumerate(S8.confirmatory_seeds_8r()):
            plan.append({"run_id": f"8r-{row['scenario_id']}-s{i:02d}", "scenario": row,
                         "seed_class": "CONFIRMATORY_8R", "seed_index": i,
                         "master_seed": seed})
    return plan


def engine_hash() -> str:
    files = sorted((REPO_ROOT / "Models" / "PoCol" / "stage2").glob("*.py"))
    lines = [f"{f.name}:{hashlib.sha256(f.read_bytes()).hexdigest()}" for f in files]
    return hashlib.sha256("\n".join(lines).encode()).hexdigest()


def config_hash(cfg) -> str:
    return hashlib.sha256(json.dumps(dataclasses.asdict(cfg), sort_keys=True,
                                     default=str).encode()).hexdigest()


def record_checksum(rec: dict) -> str:
    body = {k: v for k, v in rec.items() if k != "record_sha256"}
    return hashlib.sha256(json.dumps(body, sort_keys=True, default=str).encode()).hexdigest()


def to_jsonable(x, _stack=None):
    if isinstance(x, (str, int, float, bool)) or x is None:
        return x
    if isinstance(x, enum.Enum):
        return str(x)
    if _stack is None:
        _stack = set()
    oid = id(x)
    if oid in _stack:
        return f"<cycle:{type(x).__name__}>"
    _stack.add(oid)
    try:
        if isinstance(x, dict):
            return {str(k): to_jsonable(v, _stack) for k, v in x.items()}
        if isinstance(x, (list, tuple, set, frozenset)):
            return [to_jsonable(v, _stack) for v in x]
        if dataclasses.is_dataclass(x) and not isinstance(x, type):
            return {f.name: to_jsonable(getattr(x, f.name), _stack)
                    for f in dataclasses.fields(x)}
        if hasattr(x, "__dict__"):
            return {k: to_jsonable(v, _stack) for k, v in vars(x).items()}
        return str(x)
    finally:
        _stack.discard(oid)


# ------------------------------------------------------------------ derived measures
def floor_deficit_area(run, cfg) -> dict:
    """EXACT deficit integral: H_effective changes only at capacity-change events, and every
    capacity change produces a floor observation, so the piecewise-constant integral over
    consecutive observations of a round (last segment closed by the closure observation at
    the round terminal) is exact, not an approximation."""
    if not cfg.security_floor.enabled:
        return {"floor_deficit_area_hash_s": 0.0, "maximum_floor_deficit_hash": 0.0}
    floor = cfg.security_floor.minimum_active_hash_rate
    by_round = {}
    for o in run.security_observations:
        by_round.setdefault(o.RoundID, []).append(o)
    area = 0.0
    max_def = 0.0
    for rid, obs in by_round.items():
        obs.sort(key=lambda o: o.observation_time)
        for a, b in zip(obs, obs[1:]):
            d = max(0.0, floor - a.effective_active_hash_rate)
            area += d * max(0.0, b.observation_time - a.observation_time)
            max_def = max(max_def, d)
        if obs:
            max_def = max(max_def, max(0.0, floor - obs[-1].effective_active_hash_rate))
    return {"floor_deficit_area_hash_s": area, "maximum_floor_deficit_hash": max_def}


def q(sorted_vals: list, frac: float) -> float:
    i = min(len(sorted_vals) - 1, max(0, int(frac * len(sorted_vals) + 0.999999) - 1))
    return sorted_vals[i]


def integrity_gates(rec: dict) -> list:
    g = []
    def check(name, ok):
        g.append({"gate": name, "pass": bool(ok)})
    check("maximum_energy_identity_residual_j <= 1e-8",
          rec["maximum_energy_identity_residual_j"] <= 1e-8)
    check("maximum_residency_partition_residual_s <= 1e-9",
          rec["maximum_residency_partition_residual_s"] <= 1e-9)
    for f in ("duplicate_nonce_count", "post_round_evaluation_record_count",
              "post_round_evaluation_nonce_count", "evaluation_missing_terminal_time_count",
              "physical_frontier_rewind_count", "work_reward_union_residual",
              "nonterminal_lease_count", "nonterminal_reassignment_request_count",
              "adversarial_action_total", "nonterminal_activation_request_count",
              "nonterminal_episode_count", "live_batch_after_close_count"):
        check(f"{f} == 0", rec[f] == 0)
    check("residency_reconciles", rec["residency_reconciles"] is True)
    check("round_terminal_times_strictly_increasing",
          rec["round_terminal_times_strictly_increasing"] is True)
    return g


def execute_one(spec: dict) -> dict:
    row, seed = spec["scenario"], spec["master_seed"]
    cfg = S8.build_config_8r(row, seed)
    rec = {"run_id": spec["run_id"], "scenario_id": row["scenario_id"], "role": row["role"],
           "seed_class": spec["seed_class"], "seed_index": spec["seed_index"],
           "master_seed": seed, "controller_mode_configured": row["controller_mode"],
           "config_sha256": config_hash(cfg), "engine_sha256": engine_hash(),
           "python_version": sys.version.split()[0]}
    t0 = time.time()
    try:
        run = run_simulation(cfg, run_id=spec["run_id"])
        res = results_schema(run, cfg)
        durs, monotonic = round_durations(run, cfg)
        sd = sorted(durs)
        ident = residency_and_energy_identity(run, cfg)
        audit = post_round_audit(run)
        pair = energy_pair_kwh(run, cfg)
        deficit = floor_deficit_area(run, cfg)
        decomp = S8.energy_time_decomposition(run, cfg)
        ctrl = _controller_results(run, cfg)
        last_terminal = max(run.round_terminal_times.values()) \
            if run.round_terminal_times else 0.0
        rec.update(
            run_status="COMPLETED",
            wall_clock_seconds=time.time() - t0,
            peak_rss_mb=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0,
            # --- energy (within-run power null, identical accounting to Stage 8M) ---
            E_idle_kwh=pair["E_idle_kwh"], E_power_null_kwh=pair["E_power_null_kwh"],
            absolute_reduction_kwh=pair["absolute_reduction_kwh"],
            relative_reduction=pair["relative_reduction"],
            offline_residency_s=pair["offline_residency_s"],
            a1_continuous_control_kwh=a1_continuous_control_kwh(cfg),
            # --- service ---
            rounds_executed=len(run.round_terminal_times),
            rounds_accepted=res["rounds_accepted"],
            accepted_blocks_per_closed_round=(
                res["rounds_accepted"] / len(run.round_terminal_times)
                if run.round_terminal_times else 0.0),
            zero_block_indicator=int(res["rounds_accepted"] == 0),
            median_round_duration=(statistics.median(durs) if durs else None),
            mean_round_duration=(statistics.fmean(durs) if durs else None),
            p90_round_duration=(q(sd, 0.90) if sd else None),
            p95_round_duration=(q(sd, 0.95) if sd else None),
            max_round_duration=(sd[-1] if sd else None),
            unclosed_final_tail_s=HORIZON - last_terminal,
            round_terminal_times_strictly_increasing=bool(monotonic),
            # --- floor / operational ---
            total_duration_below_floor=res["total_duration_below_floor"],
            floor_unattainable_count=res["floor_unattainable_count"],
            security_floor_observation_count=res["security_floor_observation_count"],
            breach_count=res["breach_count"],
            maximum_hash_rate_deficit=res["maximum_hash_rate_deficit"],
            **deficit,
            # --- activation lifecycle ---
            activation_requests_seated=res["reserve_activations_seated"],
            activation_requests_completed=res["reserve_activations_completed"],
            activation_requests_cancelled=res["reserve_activations_cancelled"],
            incomplete_activation_request_count=(
                res["reserve_activations_seated"] - res["reserve_activations_completed"]),
            activations_per_closed_round=(
                res["reserve_activations_seated"] / len(run.round_terminal_times)
                if run.round_terminal_times else 0.0),
            nonterminal_activation_request_count=nonterminal_activation_request_count(run),
            reserve_standby_energy_kwh=res["reserve_standby_energy_kwh"],
            reserve_wake_energy_kwh=res["reserve_wake_energy_kwh"],
            reserve_active_energy_kwh=res["reserve_active_energy_kwh"],
            # --- controller (R1-R6) ---
            **ctrl,
            nonterminal_episode_count=sum(
                1 for ep in run.breach_episodes.values()
                if ep.status not in TERMINAL_EPISODE_STATUSES),
            live_batch_after_close_count=sum(
                1 for b in run.activation_batches.values() if b.status != "TERMINAL"),
            # --- integrity ---
            maximum_energy_identity_residual_j=ident["maximum_energy_identity_residual_j"],
            maximum_residency_partition_residual_s=(
                ident["maximum_residency_partition_residual_s"]),
            duplicate_nonce_count=res["duplicate_nonce_count"],
            post_round_evaluation_record_count=audit["post_round_evaluation_record_count"],
            post_round_evaluation_nonce_count=audit["post_round_evaluation_nonce_count"],
            evaluation_missing_terminal_time_count=(
                audit["evaluation_missing_terminal_time_count"]),
            physical_frontier_rewind_count=res["physical_frontier_rewind_count"],
            work_reward_union_residual=res["work_reward_union_residual"],
            nonterminal_lease_count=res["nonterminal_lease_count"],
            nonterminal_reassignment_request_count=(
                res["nonterminal_reassignment_request_count"]),
            adversarial_action_total=sum(int(res[k]) for k in ADVERSARIAL_COUNTERS),
            residency_reconciles=bool(res["residency_reconciles"]),
            evaluation_ledger_entries=res["evaluation_ledger_entries"],
            # --- role-state decomposition ---
            **decomp,
        )
        rec["integrity_gates"] = integrity_gates(rec)
        rec["all_integrity_gates_pass"] = all(g["pass"] for g in rec["integrity_gates"])
        if (spec["seed_class"] == "CONFIRMATORY_8R"
                and (row["scenario_id"], spec["seed_index"]) in set(S8.TIMELINE_RUNS)):
            rec.update(write_timeline(spec["run_id"], run, cfg, res))
    except Exception as exc:                                          # noqa: BLE001
        rec.update(run_status="EXCEPTION", exception=repr(exc),
                   wall_clock_seconds=time.time() - t0,
                   all_integrity_gates_pass=False)
    rec["record_sha256"] = record_checksum(rec)
    return rec


def write_timeline(run_id: str, run, cfg, res: dict) -> dict:
    """Full diagnostic timeline payload for ONE preregistered timeline run."""
    TIMELINES.mkdir(exist_ok=True)
    payload = {
        "run_id": run_id,
        "results_schema": to_jsonable(res),
        "round_terminal_times": to_jsonable(run.round_terminal_times),
        "per_miner_residency_s": {str(m): to_jsonable(run.miners[m].duration)
                                  for m in run.miners},
        "security_observations": [to_jsonable(o) for o in run.security_observations],
        "activation_requests": to_jsonable(run.activation_requests),
        "breach_episodes": to_jsonable(run.breach_episodes),
        "activation_batches": to_jsonable(run.activation_batches),
        "prediction_records": [to_jsonable(p) for p in run.prediction_records],
        "evaluation_ledger": [to_jsonable(r) for r in run.evaluation_ledger],
        "event_log": [to_jsonable(e) for e in run.log],
    }
    raw = json.dumps(payload, sort_keys=True, default=str).encode()
    dest = TIMELINES / f"{run_id}_timeline.json.gz"
    tmp = dest.with_suffix(".gz.tmp")
    with gzip.open(tmp, "wb", compresslevel=9) as fh:
        fh.write(raw)
    os.replace(tmp, dest)
    return {"timeline_file": str(dest.relative_to(REPO_ROOT)),
            "timeline_sha256": hashlib.sha256(dest.read_bytes()).hexdigest(),
            "timeline_raw_bytes": len(raw)}


# ------------------------------------------------------------------ structural pilot
def cmd_pilot() -> int:
    S8.assert_seed_disjointness()
    PILOT_OUT.mkdir(exist_ok=True)
    specs = [{"run_id": f"8r-pilot-{row['scenario_id']}-p{i}", "scenario": row,
              "seed_class": "PILOT_8R", "seed_index": i, "master_seed": seed}
             for row in S8.SCENARIOS
             for i, seed in enumerate(S8.pilot_seeds_8r())]
    with mp.Pool(processes=MAX_WORKERS, maxtasksperchild=1) as pool:
        recs = pool.map(execute_one, specs)
    gates, all_pass = [], True

    def check(name, ok):
        nonlocal all_pass
        gates.append({"gate": name, "pass": bool(ok)})
        all_pass &= bool(ok)

    check("all 8 pilot runs complete (all modes execute)",
          all(r["run_status"] == "COMPLETED" for r in recs))
    for r in recs:
        check(f"{r['run_id']}: integrity gates calculable and pass",
              r.get("all_integrity_gates_pass") is True)
        check(f"{r['run_id']}: wall <= {WALL_LIMIT_S:.0f}s",
              r.get("wall_clock_seconds", 1e9) <= WALL_LIMIT_S)
        check(f"{r['run_id']}: peak RSS <= {RSS_LIMIT_MB:.0f} MB",
              r.get("peak_rss_mb", 1e9) <= RSS_LIMIT_MB)
    predictive = [r for r in recs
                  if r["scenario_id"] in ("R02_REVISED_CONTROLLER",
                                          "R03_REVISED_PLUS_REASSIGNMENT")]
    check("predictive activation fires in every predictive-mode pilot run",
          all(r.get("prediction_decision_count", 0) >= 1
              and r.get("predictive_batches_seated", 0) >= 1 for r in predictive))
    check("hysteresis prevents duplicate batches (counter > 0, no live state leaks)",
          all(r.get("duplicate_activation_batch_prevented_count", 0) >= 1
              and r.get("nonterminal_episode_count", 1) == 0
              and r.get("live_batch_after_close_count", 1) == 0 for r in predictive))
    required = set(csv_fields())
    for r in recs:
        missing = required - set(r.keys())
        check(f"{r['run_id']}: required fields exist", not missing)
    payload = {"harness": "run_stage8r.py pilot",
               "purpose": ("STRUCTURE AND FEASIBILITY ONLY.  No effect magnitude here may "
                           "change 0.78/0.80/0.82, the lookahead, the cooldown or the "
                           "25-nonce chunk (frozen before this pilot ran)."),
               "gates": gates, "all_structural_gates_pass": all_pass,
               "runs": [{k: r.get(k) for k in
                         ("run_id", "scenario_id", "run_status", "rounds_executed",
                          "wall_clock_seconds", "peak_rss_mb",
                          "all_integrity_gates_pass", "prediction_decision_count",
                          "duplicate_activation_batch_prevented_count")}
                        for r in recs]}
    (PILOT_OUT / "structural_pilot_8r.json").write_text(
        json.dumps(payload, indent=1, sort_keys=True, default=str) + "\n")
    for r in recs:
        print(f"  {r['run_id']:44s} {r['run_status']:9s} "
              f"rounds={r.get('rounds_executed', '-'):>4} "
              f"wall {r.get('wall_clock_seconds', 0):5.2f}s "
              f"gates {'PASS' if r.get('all_integrity_gates_pass') else 'FAIL'}")
    print("structural pilot:", "ALL GATES PASS" if all_pass else "BLOCKED")
    return 0 if all_pass else 2


# ------------------------------------------------------------------ execute / verify / dataset
def checkpoint_path(run_id: str) -> pathlib.Path:
    return RUNS / f"{run_id}.json"


def cmd_execute() -> int:
    S8.assert_seed_disjointness()
    pilot = PILOT_OUT / "structural_pilot_8r.json"
    if not pilot.exists() or not json.loads(pilot.read_text())["all_structural_gates_pass"]:
        raise SystemExit("STAGE_8R_BLOCKED — structural pilot has not passed")
    RUNS.mkdir(exist_ok=True)
    plan = run_plan()
    pending = [p for p in plan if not checkpoint_path(p["run_id"]).exists()]
    if len(plan) - len(pending):
        print(f"resume: {len(plan) - len(pending)} checkpoint(s) present")
    t0 = time.time()
    failures = 0
    with mp.Pool(processes=MAX_WORKERS, maxtasksperchild=1) as pool:
        for rec in pool.imap_unordered(execute_one, pending):
            dest = checkpoint_path(rec["run_id"])
            tmp = dest.with_suffix(".json.tmp")
            tmp.write_text(json.dumps(rec, indent=1, sort_keys=True, default=str) + "\n")
            os.replace(tmp, dest)                      # atomic checkpoint after every run
            ok = rec["run_status"] == "COMPLETED" and rec["all_integrity_gates_pass"]
            failures += (not ok)
            print(f"  {rec['run_id']:40s} {rec['run_status']:9s} "
                  f"wall {rec.get('wall_clock_seconds', 0):6.2f}s "
                  f"gates {'PASS' if rec.get('all_integrity_gates_pass') else 'FAIL'}")
    total = sum(1 for p in plan if checkpoint_path(p["run_id"]).exists())
    print(f"\nwall {time.time() - t0:.1f}s; checkpoints {total}/48; failures {failures}")
    if failures or total != 48:
        print("STAGE_8R_EXECUTION_INCOMPLETE_OR_GATED")
        return 2
    print("STAGE_8R_EXECUTION_COMPLETE")
    return 0


def load_all() -> list:
    recs = []
    for p in run_plan():
        path = checkpoint_path(p["run_id"])
        if not path.exists():
            raise SystemExit(f"STAGE_8R_BLOCKED — missing checkpoint {path.name}")
        recs.append(json.loads(path.read_text()))
    return recs


def verify_records(recs: list) -> list:
    problems = []
    for rec in recs:
        if record_checksum(rec) != rec.get("record_sha256"):
            problems.append(f"{rec['run_id']}: record checksum mismatch")
        if rec.get("run_status") != "COMPLETED" or not rec.get("all_integrity_gates_pass"):
            problems.append(f"{rec['run_id']}: status/integrity failure")
        if "timeline_file" in rec:
            f = REPO_ROOT / rec["timeline_file"]
            if not f.exists() or hashlib.sha256(
                    f.read_bytes()).hexdigest() != rec["timeline_sha256"]:
                problems.append(f"{rec['run_id']}: timeline missing or digest mismatch")
    timelines = [r for r in recs if "timeline_file" in r]
    if len(timelines) != 3:
        problems.append(f"expected exactly 3 timeline runs, found {len(timelines)}")
    return problems


def cmd_verify() -> int:
    problems = verify_records(load_all())
    for x in problems:
        print(f"  FAIL {x}")
    print("OK: all 48 checkpoints verified" if not problems
          else f"STAGE_8R_BLOCKED — {len(problems)} problem(s)")
    return 0 if not problems else 2


def csv_fields() -> list:
    base = ["run_id", "scenario_id", "role", "seed_class", "seed_index", "master_seed",
            "controller_mode_configured", "run_status", "all_integrity_gates_pass",
            "E_idle_kwh", "E_power_null_kwh", "absolute_reduction_kwh",
            "relative_reduction", "offline_residency_s", "a1_continuous_control_kwh",
            "rounds_executed", "rounds_accepted", "accepted_blocks_per_closed_round",
            "zero_block_indicator", "median_round_duration", "mean_round_duration",
            "p90_round_duration", "p95_round_duration", "max_round_duration",
            "unclosed_final_tail_s", "total_duration_below_floor",
            "floor_unattainable_count", "security_floor_observation_count", "breach_count",
            "maximum_hash_rate_deficit", "floor_deficit_area_hash_s",
            "maximum_floor_deficit_hash", "activation_requests_seated",
            "activation_requests_completed", "activation_requests_cancelled",
            "incomplete_activation_request_count", "activations_per_closed_round",
            "nonterminal_activation_request_count", "reserve_standby_energy_kwh",
            "reserve_wake_energy_kwh", "reserve_active_energy_kwh"]
    integ = ["maximum_energy_identity_residual_j", "maximum_residency_partition_residual_s",
             "duplicate_nonce_count", "post_round_evaluation_record_count",
             "post_round_evaluation_nonce_count", "evaluation_missing_terminal_time_count",
             "physical_frontier_rewind_count", "work_reward_union_residual",
             "nonterminal_lease_count", "nonterminal_reassignment_request_count",
             "adversarial_action_total", "nonterminal_episode_count",
             "live_batch_after_close_count", "evaluation_ledger_entries"]
    decomp = [f"{prefix}_{c}_{unit}" for c in S8.COMPONENTS
              for prefix, unit in (("residency", "s"), ("energy", "kwh"),
                                   ("power_null_difference", "kwh"))]
    named = ["range_idle_energy_difference_kwh", "reserve_standby_energy_difference_kwh",
             "wake_energy_difference_kwh", "activated_reserve_energy_kwh",
             "total_low_power_state_difference_kwh"]
    tail = ["wall_clock_seconds", "peak_rss_mb", "config_sha256", "engine_sha256",
            "record_sha256"]
    return base + CONTROLLER_FIELDS + integ + decomp + named + tail


def cmd_dataset() -> int:
    import csv                                                        # noqa: PLC0415
    recs = load_all()
    problems = verify_records(recs)
    if problems:
        for x in problems:
            print(f"  FAIL {x}")
        raise SystemExit("STAGE_8R_BLOCKED — verification failed")
    recs.sort(key=lambda r: (r["scenario_id"], r["seed_index"]))
    DOCS.mkdir(parents=True, exist_ok=True)
    fields = csv_fields()
    with open(DOCS / "STAGE_08R_RUN_DATASET.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, lineterminator="\n",
                           extrasaction="ignore")
        w.writeheader()
        for r in recs:
            w.writerow(r)
    print(f"wrote STAGE_08R_RUN_DATASET.csv ({len(recs)} rows)")
    return 0


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    cmds = {"pilot": cmd_pilot, "execute": cmd_execute, "verify": cmd_verify,
            "dataset": cmd_dataset}
    if len(argv) != 1 or argv[0] not in cmds:
        print(f"usage: run_stage8r.py {{{'|'.join(cmds)}}}", file=sys.stderr)
        return 64
    return cmds[argv[0]]()


if __name__ == "__main__":
    raise SystemExit(main())
