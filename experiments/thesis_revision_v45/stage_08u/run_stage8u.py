#!/usr/bin/env python3
"""Stage 8U — structural pilot + frozen execution harness (final refinement cycle).

    python run_stage8u.py pilot        # 5 scenarios x 2 FRESH pilot seeds, STRUCTURE ONLY
    python run_stage8u.py execute      # 5 x 12 = 60 runs, <= 2 workers, atomic checkpoints
    python run_stage8u.py verify       # re-verify every checkpoint checksum + timelines
    python run_stage8u.py dataset      # 60-row STAGE_08U_RUN_DATASET.csv

The pilot verifies ONLY: every scenario executes (engine AND matched-PoW); the handoff
occurs and honours its structural gates; at most one epoch and one reserve wake per
round; PoW overlap is measurable; PoW post-round evaluations are zero; integrity fields
are computable; runtime and memory are feasible.  Nothing seen in the pilot may tune any
seed, margin, target, difficulty or scenario definition.
"""
from __future__ import annotations

import dataclasses
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
          str(REPO_ROOT / "experiments" / "thesis_revision_v45" / "stage_06m"),
          str(REPO_ROOT / "experiments" / "thesis_revision_v45" / "stage_08r"),
          str(REPO_ROOT / "experiments" / "thesis_revision_v45" / "stage_08s")):
    if p not in sys.path:
        sys.path.insert(0, p)

import scenarios_8u as S8U                                                 # noqa: E402
from scenarios_6m import energy_pair_kwh                                   # noqa: E402
from scenarios_8r import energy_time_decomposition, COMPONENTS             # noqa: E402
from run_pilot import (post_round_audit, residency_and_energy_identity,    # noqa: E402
                       round_durations, nonterminal_activation_request_count)
from run_stage8r import floor_deficit_area, q, to_jsonable                 # noqa: E402
from run_stage8s import S8S_FIELDS, CONTROLLER_FIELDS                      # noqa: E402
from Models.PoCol.stage2.simulator import run_simulation                   # noqa: E402
from Models.PoCol.stage2.adapter import results_schema                     # noqa: E402
from Models.PoCol.stage2.config import a1_continuous_control_kwh           # noqa: E402
from Models.PoCol.stage2.refinement import (TERMINAL_EPISODE_STATUSES,     # noqa: E402
                                            TERMINAL_HANDOFF_STATUSES)
from Models.PoCol.stage2.matched_pow import run_matched_pow                # noqa: E402

DOCS = REPO_ROOT / "docs" / "thesis_revision_v45" / "stage_08u"
RUNS = HERE / "runs"
TIMELINES = HERE / "timelines"
PILOT_OUT = HERE / "pilot"

MAX_WORKERS = 2
WALL_LIMIT_S = 600.0
RSS_LIMIT_MB = 4096.0
HORIZON = 300.0
N_RUNS = len(S8U.SCENARIOS) * S8U.N_CONFIRMATORY_SEEDS

ADVERSARIAL_COUNTERS = ("adversarial_entity_count", "adversarial_miner_count",
                        "adversarial_duplicate_evaluation_count",
                        "adversarial_coverage_gap_round_count",
                        "adversarial_reevaluation_count", "solution_withholding_count")

#: Stage-8U engine-side fields (added on top of the retained Stage-8S families).
S8U_FIELDS = [
    "handoff_epoch_count", "handoff_committed_count", "handoff_completed_count",
    "handoff_failed_count", "handoff_cancelled_count",
    "duplicate_handoff_prevented_count", "nonterminal_handoff_epoch_count",
    "single_reserve_requests_seated", "single_reserve_requests_completed",
    "single_reserve_requests_incomplete", "reserve_wake_rejected_short_useful_window",
    "reserve_wake_rejected_awake_receiver_available",
    "reserve_wake_rejected_no_bound_work",
]

#: Cross-paradigm comparison fields, present for EVERY run (PoW and PoCol).
COMPARISON_FIELDS = [
    "total_physical_evaluations", "unique_physical_evaluations",
    "duplicate_physical_evaluations", "post_round_evaluation_count",
    "blocks_per_million_physical_evaluations", "energy_per_accepted_block_kwh",
]


def run_plan() -> list:
    return [{"run_id": f"8u-{row['scenario_id']}-s{i:02d}", "scenario": row,
             "seed_class": "CONFIRMATORY_8U", "seed_index": i, "master_seed": seed}
            for row in S8U.SCENARIOS
            for i, seed in enumerate(S8U.confirmatory_seeds_8u())]


def engine_hash() -> str:
    files = sorted((REPO_ROOT / "Models" / "PoCol" / "stage2").glob("*.py"))
    lines = [f"{f.name}:{hashlib.sha256(f.read_bytes()).hexdigest()}" for f in files]
    return hashlib.sha256("\n".join(lines).encode()).hexdigest()


def config_hash_engine(cfg) -> str:
    return hashlib.sha256(json.dumps(dataclasses.asdict(cfg), sort_keys=True,
                                     default=str).encode()).hexdigest()


def record_checksum(rec: dict) -> str:
    body = {k: v for k, v in rec.items() if k != "record_sha256"}
    return hashlib.sha256(json.dumps(body, sort_keys=True,
                                     default=str).encode()).hexdigest()


def handoff_structural_gates(run) -> dict:
    """Executable U1/U3/U4 verification for THIS run's handoff epochs and fallbacks."""
    by_round: dict = {}
    for e in run.handoff_epochs.values():
        by_round.setdefault(e.RoundID, []).append(e)
    one_per_round = all(len(v) == 1 for v in by_round.values())
    contiguous = union_exact = benefit = terminal = True
    ledger_by_round: dict = {}
    for rec in run.evaluation_ledger:
        ledger_by_round.setdefault(rec.RoundID, []).append(rec)
    donor_exclusion = True
    for e in run.handoff_epochs.values():
        terminal &= e.status in TERMINAL_HANDOFF_STATUSES
        if e.receiver_chunk is None or e.donor_chunk is None:
            continue
        d0, d1 = e.donor_chunk
        r0, r1 = e.receiver_chunk
        o0, o1 = e.original_suffix
        contiguous &= d1 == r0
        union_exact &= (d0 == o0 and r1 == o1)
        benefit &= e.predicted_makespan_after < e.predicted_makespan_before
        for rec in ledger_by_round.get(e.RoundID, []):
            if rec.AssignmentID == e.source_assignment_id:
                donor_exclusion &= (rec.interval_end <= r0 or rec.interval_start >= r1)
    wakes_by_round: dict = {}
    for q_ in run.activation_requests.values():
        wakes_by_round.setdefault(q_.RoundID, []).append(q_)
    one_wake_per_round = all(len(v) <= 1 for v in wakes_by_round.values())
    return {"handoff_one_epoch_per_round": one_per_round,
            "handoff_chunks_contiguous": contiguous,
            "handoff_union_equals_original_suffix": union_exact,
            "handoff_benefit_gate_strict": benefit,
            "handoff_epochs_all_terminal": terminal,
            "handoff_donor_never_in_ceded_chunk": donor_exclusion,
            "one_reserve_wake_per_round": one_wake_per_round}


def integrity_gates_pocol(rec: dict) -> list:
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
              "nonterminal_episode_count", "live_batch_after_close_count",
              "nonterminal_coarse_request_count", "nonterminal_handoff_epoch_count",
              "handoff_failed_count", "duplicate_physical_evaluations"):
        check(f"{f} == 0", rec[f] == 0)
    for f in ("handoff_one_epoch_per_round", "handoff_chunks_contiguous",
              "handoff_union_equals_original_suffix", "handoff_benefit_gate_strict",
              "handoff_epochs_all_terminal", "handoff_donor_never_in_ceded_chunk",
              "residency_reconciles", "round_terminal_times_strictly_increasing"):
        check(f, rec[f] is True)
    if rec["controller_mode_configured"] == "USEFUL_FLOOR_SINGLE_HANDOFF":
        # U4 is a property of the single-handoff policy only: the Stage-8S coarse
        # baseline may legitimately seat several reserve wakes in one round.
        check("one_reserve_wake_per_round", rec["one_reserve_wake_per_round"] is True)
    return g


def integrity_gates_pow(rec: dict) -> list:
    g = []

    def check(name, ok):
        g.append({"gate": name, "pass": bool(ok)})

    check("energy_identity_residual_j <= 1e-8",
          rec["maximum_energy_identity_residual_j"] <= 1e-8)
    check("residency_partition_residual_s <= 1e-9",
          rec["maximum_residency_partition_residual_s"] <= 1e-9)
    check("post_round_evaluation_count == 0", rec["post_round_evaluation_count"] == 0)
    check("total == unique + duplicate",
          rec["total_physical_evaluations"] == rec["unique_physical_evaluations"]
          + rec["duplicate_physical_evaluations"])
    check("blocks == first_valid_solution_count",
          rec["rounds_accepted"] == rec["first_valid_solution_count"])
    check("round close times strictly increasing",
          rec["round_terminal_times_strictly_increasing"] is True)
    check("fixed target and difficulty",
          rec["difficulty_configured"] == 1000)
    return g


def _common_service_fields(rec: dict, durs: list, n_rounds: int, blocks: int) -> None:
    sd = sorted(durs)
    rec.update(
        rounds_executed=n_rounds,
        rounds_accepted=blocks,
        accepted_blocks_per_closed_round=(blocks / n_rounds if n_rounds else 0.0),
        zero_block_indicator=int(blocks == 0),
        median_round_duration=(statistics.median(durs) if durs else None),
        mean_round_duration=(statistics.fmean(durs) if durs else None),
        p95_round_duration=(q(sd, 0.95) if sd else None))
    total = rec["total_physical_evaluations"]
    rec["blocks_per_million_physical_evaluations"] = (
        blocks / (total / 1e6) if total else None)
    rec["energy_per_accepted_block_kwh"] = (
        rec["E_idle_kwh"] / blocks if blocks else None)   # NA (None) when zero blocks


def execute_pocol(spec: dict, rec: dict) -> dict:
    row, seed = spec["scenario"], spec["master_seed"]
    cfg = S8U.build_config_8u(row, seed)
    rec.update(controller_mode_configured=row["controller_mode"],
               difficulty_configured=cfg.difficulty,
               config_sha256=config_hash_engine(cfg))
    t0 = time.time()
    run = run_simulation(cfg, run_id=spec["run_id"])
    res = results_schema(run, cfg)
    durs, monotonic = round_durations(run, cfg)
    ident = residency_and_energy_identity(run, cfg)
    audit = post_round_audit(run)
    pair = energy_pair_kwh(run, cfg)
    deficit = floor_deficit_area(run, cfg)
    decomp = energy_time_decomposition(run, cfg)
    n_rounds = len(run.round_terminal_times)
    rec.update(
        run_status="COMPLETED",
        wall_clock_seconds=time.time() - t0,
        peak_rss_mb=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0,
        E_idle_kwh=pair["E_idle_kwh"], E_power_null_kwh=pair["E_power_null_kwh"],
        absolute_reduction_kwh=pair["absolute_reduction_kwh"],
        relative_reduction=pair["relative_reduction"],
        offline_residency_s=pair["offline_residency_s"],
        a1_continuous_control_kwh=a1_continuous_control_kwh(cfg),
        unclosed_final_tail_s=HORIZON - (max(run.round_terminal_times.values())
                                         if run.round_terminal_times else 0.0),
        round_terminal_times_strictly_increasing=bool(monotonic),
        static_floor_deficit_area_hash_s=deficit["floor_deficit_area_hash_s"],
        activation_requests_seated=res["reserve_activations_seated"],
        activation_requests_completed=res["reserve_activations_completed"],
        activation_requests_cancelled=res["reserve_activations_cancelled"],
        incomplete_activation_request_count=(
            res["reserve_activations_seated"] - res["reserve_activations_completed"]),
        activations_per_closed_round=(res["reserve_activations_seated"] / n_rounds
                                      if n_rounds else 0.0),
        reassignments_per_closed_round=(
            (res["coarse_reassignment_count"] + res["handoff_committed_count"]) / n_rounds
            if n_rounds else 0.0),
        handoffs_per_closed_round=(res["handoff_committed_count"] / n_rounds
                                   if n_rounds else 0.0),
        nonterminal_activation_request_count=nonterminal_activation_request_count(run),
        total_physical_evaluations=res["physical_evaluation_count"],
        unique_physical_evaluations=(res["physical_evaluation_count"]
                                     - res["duplicate_nonce_count"]),
        duplicate_physical_evaluations=res["duplicate_nonce_count"],
        post_round_evaluation_count=audit["post_round_evaluation_nonce_count"],
        first_valid_solution_count=res["rounds_accepted"],
        **{k: res[k] for k in S8S_FIELDS},
        **{k: res[k] for k in S8U_FIELDS},
        **{k: res[k] for k in CONTROLLER_FIELDS},
        nonterminal_episode_count=sum(
            1 for ep in run.breach_episodes.values()
            if ep.status not in TERMINAL_EPISODE_STATUSES),
        live_batch_after_close_count=sum(
            1 for b in run.activation_batches.values() if b.status != "TERMINAL"),
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
        **handoff_structural_gates(run),
        **decomp,
    )
    _common_service_fields(rec, durs, n_rounds, res["rounds_accepted"])
    rec["integrity_gates"] = integrity_gates_pocol(rec)
    rec["all_integrity_gates_pass"] = all(g["pass"] for g in rec["integrity_gates"])
    if (spec["seed_class"] == "CONFIRMATORY_8U"
            and (row["scenario_id"], spec["seed_index"]) in set(S8U.TIMELINE_RUNS)):
        rec.update(write_timeline(spec["run_id"], run, cfg, res))
    return rec


def execute_pow(spec: dict, rec: dict) -> dict:
    row, seed = spec["scenario"], spec["master_seed"]
    pcfg = S8U.build_pow_config_8u(row, seed)
    rec.update(controller_mode_configured="MATCHED_POW",
               difficulty_configured=pcfg.difficulty,
               config_sha256=hashlib.sha256(json.dumps(
                   dataclasses.asdict(pcfg), sort_keys=True,
                   default=str).encode()).hexdigest())
    t0 = time.time()
    res = run_matched_pow(pcfg)
    durs = list(res["round_durations_closed"])
    closes = [r.close_time for r in res["rounds"]]
    rec.update(
        run_status="COMPLETED",
        wall_clock_seconds=time.time() - t0,
        peak_rss_mb=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0,
        E_idle_kwh=res["energy_kwh"],                # actual executed energy of the run
        E_power_null_kwh=None, absolute_reduction_kwh=None, relative_reduction=None,
        offline_residency_s=0.0, a1_continuous_control_kwh=None,
        unclosed_final_tail_s=(HORIZON - max(closes)) if closes else HORIZON,
        round_terminal_times_strictly_increasing=all(
            a < b for a, b in zip(closes, closes[1:])),
        rounds_exhausted=res["rounds_exhausted"],
        rounds_horizon_truncated=res["rounds_horizon_truncated"],
        total_physical_evaluations=res["total_physical_evaluations"],
        unique_physical_evaluations=res["unique_physical_evaluations"],
        duplicate_physical_evaluations=res["duplicate_physical_evaluations"],
        post_round_evaluation_count=res["post_round_evaluation_count"],
        first_valid_solution_count=len(res["first_valid_solutions"]),
        maximum_energy_identity_residual_j=res["energy_identity_residual_j"],
        maximum_residency_partition_residual_s=res["residency_partition_residual_s"],
        energy_kwh_active_hashing=res["energy_kwh_by_state"]["ACTIVE_HASHING"],
        energy_kwh_reserve_standby=res["energy_kwh_by_state"]["RESERVE_STANDBY"],
        mining_node_count=res["mining_node_count"],
        standby_node_count=res["standby_node_count"],
    )
    n_closed = res["rounds_accepted"] + res["rounds_exhausted"]
    _common_service_fields(rec, durs, n_closed, res["rounds_accepted"])
    rec["integrity_gates"] = integrity_gates_pow(rec)
    rec["all_integrity_gates_pass"] = all(g["pass"] for g in rec["integrity_gates"])
    return rec


def execute_one(spec: dict) -> dict:
    row = spec["scenario"]
    rec = {"run_id": spec["run_id"], "scenario_id": row["scenario_id"],
           "role": row["role"], "engine": row["engine"],
           "seed_class": spec["seed_class"], "seed_index": spec["seed_index"],
           "master_seed": spec["master_seed"], "engine_sha256": engine_hash(),
           "python_version": sys.version.split()[0]}
    t0 = time.time()
    try:
        if row["engine"] == "POCOL":
            rec = execute_pocol(spec, rec)
        else:
            rec = execute_pow(spec, rec)
    except Exception as exc:                                          # noqa: BLE001
        rec.update(run_status="EXCEPTION", exception=repr(exc),
                   wall_clock_seconds=time.time() - t0,
                   all_integrity_gates_pass=False)
    rec["record_sha256"] = record_checksum(rec)
    return rec


def write_timeline(run_id: str, run, cfg, res: dict) -> dict:
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
        "coarse_requests": to_jsonable(run.coarse_requests),
        "handoff_epochs": to_jsonable(run.handoff_epochs),
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
            "timeline_sha256": hashlib.sha256(dest.read_bytes()).hexdigest()}


# ------------------------------------------------------------------ pilot
def cmd_pilot() -> int:
    S8U.assert_seed_disjointness()
    PILOT_OUT.mkdir(exist_ok=True)
    specs = [{"run_id": f"8u-pilot-{row['scenario_id']}-p{i}", "scenario": row,
              "seed_class": "PILOT_8U", "seed_index": i, "master_seed": seed}
             for row in S8U.SCENARIOS
             for i, seed in enumerate(S8U.pilot_seeds_8u())]
    with mp.Pool(processes=MAX_WORKERS, maxtasksperchild=1) as pool:
        recs = pool.map(execute_one, specs)
    gates, all_pass = [], True

    def check(name, ok):
        nonlocal all_pass
        gates.append({"gate": name, "pass": bool(ok)})
        all_pass &= bool(ok)

    check("every scenario executes (10/10 COMPLETED)",
          all(r["run_status"] == "COMPLETED" for r in recs))
    for r in recs:
        check(f"{r['run_id']}: integrity fields computable and pass",
              r.get("all_integrity_gates_pass") is True)
        check(f"{r['run_id']}: wall/RSS feasible",
              r.get("wall_clock_seconds", 1e9) <= WALL_LIMIT_S
              and r.get("peak_rss_mb", 1e9) <= RSS_LIMIT_MB)
        check(f"{r['run_id']}: comparison fields present",
              all(k in r for k in COMPARISON_FIELDS))
    p02 = [r for r in recs if r["scenario_id"] == "P02_POCOL_SINGLE_HANDOFF"]
    check("the single handoff occurs (every P02 pilot run)",
          all(r.get("handoff_committed_count", 0) >= 1 for r in p02))
    check("handoff structural gates pass (every P02 pilot run)",
          all(r.get("handoff_one_epoch_per_round") and r.get("handoff_chunks_contiguous")
              and r.get("handoff_union_equals_original_suffix")
              and r.get("handoff_benefit_gate_strict")
              and r.get("handoff_donor_never_in_ceded_chunk")
              and r.get("one_reserve_wake_per_round") for r in p02))
    pow_runs = [r for r in recs if r["engine"] == "MATCHED_POW"]
    check("PoW overlap measurable (every W pilot run)",
          all(r.get("duplicate_physical_evaluations", 0) > 0 for r in pow_runs))
    check("PoW post-round evaluations zero (every W pilot run)",
          all(r.get("post_round_evaluation_count") == 0 for r in pow_runs))
    check("W00 and W01 remain separate scenarios",
          {r["scenario_id"] for r in pow_runs} ==
          {"W00_POW_POPULATION_MATCHED", "W01_POW_ACTIVE_CAPACITY_MATCHED"})
    payload = {"harness": "run_stage8u.py pilot",
               "purpose": ("STRUCTURE AND FEASIBILITY ONLY.  Nothing here may tune any "
                           "seed, margin, acceptance threshold, target, difficulty or "
                           "scenario definition."),
               "gates": gates, "all_structural_gates_pass": all_pass,
               "runs": [{k: r.get(k) for k in
                         ("run_id", "scenario_id", "engine", "run_status",
                          "rounds_executed", "rounds_accepted", "wall_clock_seconds",
                          "all_integrity_gates_pass", "handoff_committed_count",
                          "single_reserve_requests_seated",
                          "duplicate_physical_evaluations")}
                        for r in recs]}
    (PILOT_OUT / "structural_pilot_8u.json").write_text(
        json.dumps(payload, indent=1, sort_keys=True, default=str) + "\n")
    for r in recs:
        print(f"  {r['run_id']:52s} {r['run_status']:9s} "
              f"rounds={r.get('rounds_executed', '-'):>4} "
              f"blocks={r.get('rounds_accepted', '-'):>4} "
              f"wall {r.get('wall_clock_seconds', 0):5.2f}s "
              f"gates {'PASS' if r.get('all_integrity_gates_pass') else 'FAIL'}")
    print("structural pilot:", "ALL GATES PASS" if all_pass else "BLOCKED")
    return 0 if all_pass else 2


# ------------------------------------------------------------------ execute/verify/dataset
def checkpoint_path(run_id: str) -> pathlib.Path:
    return RUNS / f"{run_id}.json"


def cmd_execute() -> int:
    S8U.assert_seed_disjointness()
    pilot = PILOT_OUT / "structural_pilot_8u.json"
    if not pilot.exists() or not json.loads(pilot.read_text())["all_structural_gates_pass"]:
        raise SystemExit("STAGE_8U_BLOCKED — structural pilot has not passed")
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
            os.replace(tmp, dest)
            ok = rec["run_status"] == "COMPLETED" and rec["all_integrity_gates_pass"]
            failures += (not ok)
            print(f"  {rec['run_id']:48s} {rec['run_status']:9s} "
                  f"wall {rec.get('wall_clock_seconds', 0):6.2f}s "
                  f"gates {'PASS' if rec.get('all_integrity_gates_pass') else 'FAIL'}")
    total = sum(1 for p in plan if checkpoint_path(p["run_id"]).exists())
    print(f"\nwall {time.time() - t0:.1f}s; checkpoints {total}/{N_RUNS}; "
          f"failures {failures}")
    print("STAGE_8U_EXECUTION_COMPLETE" if not failures and total == N_RUNS
          else "STAGE_8U_EXECUTION_INCOMPLETE_OR_GATED")
    return 0 if not failures and total == N_RUNS else 2


def load_all() -> list:
    recs = []
    for p in run_plan():
        path = checkpoint_path(p["run_id"])
        if not path.exists():
            raise SystemExit(f"STAGE_8U_BLOCKED — missing checkpoint {path.name}")
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
    if sum(1 for r in recs if "timeline_file" in r) != len(S8U.TIMELINE_RUNS):
        problems.append(f"expected exactly {len(S8U.TIMELINE_RUNS)} timeline runs")
    return problems


def cmd_verify() -> int:
    problems = verify_records(load_all())
    for x in problems:
        print(f"  FAIL {x}")
    print(f"OK: all {N_RUNS} checkpoints verified" if not problems
          else f"STAGE_8U_BLOCKED — {len(problems)} problem(s)")
    return 0 if not problems else 2


def csv_fields() -> list:
    base = ["run_id", "scenario_id", "role", "engine", "seed_class", "seed_index",
            "master_seed", "controller_mode_configured", "difficulty_configured",
            "run_status", "all_integrity_gates_pass",
            "E_idle_kwh", "E_power_null_kwh", "absolute_reduction_kwh",
            "relative_reduction", "offline_residency_s", "a1_continuous_control_kwh",
            "rounds_executed", "rounds_accepted", "accepted_blocks_per_closed_round",
            "zero_block_indicator", "median_round_duration", "mean_round_duration",
            "p95_round_duration", "unclosed_final_tail_s",
            "static_floor_deficit_area_hash_s", "activation_requests_seated",
            "activation_requests_completed", "activation_requests_cancelled",
            "incomplete_activation_request_count", "activations_per_closed_round",
            "reassignments_per_closed_round", "handoffs_per_closed_round",
            "nonterminal_activation_request_count", "first_valid_solution_count",
            "rounds_exhausted", "rounds_horizon_truncated",
            "mining_node_count", "standby_node_count",
            "energy_kwh_active_hashing", "energy_kwh_reserve_standby"]
    integ = ["maximum_energy_identity_residual_j",
             "maximum_residency_partition_residual_s",
             "duplicate_nonce_count", "post_round_evaluation_record_count",
             "post_round_evaluation_nonce_count", "evaluation_missing_terminal_time_count",
             "physical_frontier_rewind_count", "work_reward_union_residual",
             "nonterminal_lease_count", "nonterminal_reassignment_request_count",
             "adversarial_action_total", "nonterminal_episode_count",
             "live_batch_after_close_count", "evaluation_ledger_entries",
             "handoff_one_epoch_per_round", "handoff_chunks_contiguous",
             "handoff_union_equals_original_suffix", "handoff_benefit_gate_strict",
             "handoff_epochs_all_terminal", "handoff_donor_never_in_ceded_chunk",
             "one_reserve_wake_per_round"]
    decomp = [f"{prefix}_{c}_{unit}" for c in COMPONENTS
              for prefix, unit in (("residency", "s"), ("energy", "kwh"),
                                   ("power_null_difference", "kwh"))]
    named = ["range_idle_energy_difference_kwh", "reserve_standby_energy_difference_kwh",
             "wake_energy_difference_kwh", "activated_reserve_energy_kwh",
             "total_low_power_state_difference_kwh"]
    tail = ["wall_clock_seconds", "peak_rss_mb", "config_sha256", "engine_sha256",
            "record_sha256"]
    return (base + COMPARISON_FIELDS + S8S_FIELDS + S8U_FIELDS + CONTROLLER_FIELDS
            + integ + decomp + named + tail)


def cmd_dataset() -> int:
    import csv                                                        # noqa: PLC0415
    recs = load_all()
    problems = verify_records(recs)
    if problems:
        for x in problems:
            print(f"  FAIL {x}")
        raise SystemExit("STAGE_8U_BLOCKED — verification failed")
    recs.sort(key=lambda r: (r["scenario_id"], r["seed_index"]))
    DOCS.mkdir(parents=True, exist_ok=True)
    with open(DOCS / "STAGE_08U_RUN_DATASET.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=csv_fields(), lineterminator="\n",
                           extrasaction="ignore")
        w.writeheader()
        for r in recs:
            w.writerow(r)
    print(f"wrote STAGE_08U_RUN_DATASET.csv ({len(recs)} rows)")
    return 0


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    cmds = {"pilot": cmd_pilot, "execute": cmd_execute, "verify": cmd_verify,
            "dataset": cmd_dataset}
    if len(argv) != 1 or argv[0] not in cmds:
        print(f"usage: run_stage8u.py {{{'|'.join(cmds)}}}", file=sys.stderr)
        return 64
    return cmds[argv[0]]()


if __name__ == "__main__":
    raise SystemExit(main())
