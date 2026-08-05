#!/usr/bin/env python3
"""Stage 8S — structural pilot + frozen execution harness (FINAL refinement cycle).

    python run_stage8s.py pilot        # 4 scenarios x 2 FRESH pilot seeds, STRUCTURE ONLY
    python run_stage8s.py execute      # 4 x 12 = 48 runs, <= 2 workers, atomic checkpoints
    python run_stage8s.py verify       # re-verify every checkpoint checksum + timelines
    python run_stage8s.py dataset      # 48-row STAGE_08S_RUN_DATASET.csv

The pilot verifies ONLY: every mode executes; useful-floor metrics exist; coarse
reassignment occurs; chunk union/disjointness gates pass; reserve admission is enforced;
integrity fields are computable; runtime and memory are feasible.  Nothing seen in the
pilot may tune the 0.80 static target, the useful-floor formula, batch_size, the partition
rule, reassignment caps or the acceptance margins.
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
          str(REPO_ROOT / "experiments" / "thesis_revision_v45" / "stage_06m"),
          str(REPO_ROOT / "experiments" / "thesis_revision_v45" / "stage_08r")):
    if p not in sys.path:
        sys.path.insert(0, p)

import scenarios_8s as S8S                                                 # noqa: E402
from scenarios_6m import energy_pair_kwh                                   # noqa: E402
from scenarios_8r import energy_time_decomposition, COMPONENTS             # noqa: E402
from run_pilot import (post_round_audit, residency_and_energy_identity,    # noqa: E402
                       round_durations, nonterminal_activation_request_count)
from run_stage8r import floor_deficit_area, q, to_jsonable                 # noqa: E402
from Models.PoCol.stage2.simulator import run_simulation                   # noqa: E402
from Models.PoCol.stage2.adapter import results_schema                     # noqa: E402
from Models.PoCol.stage2.config import a1_continuous_control_kwh           # noqa: E402
from Models.PoCol.stage2.refinement import TERMINAL_EPISODE_STATUSES       # noqa: E402

DOCS = REPO_ROOT / "docs" / "thesis_revision_v45" / "stage_08s"
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

S8S_FIELDS = [
    "duration_below_static_floor", "static_floor_unattainable_count",
    "duration_below_useful_floor", "useful_floor_deficit_area",
    "useful_floor_unattainable_count", "H_useful_available_time_weighted",
    "H_useful_target_time_weighted", "coarse_repartition_count",
    "coarse_reassignment_count", "mean_coarse_chunk_size", "minimum_coarse_chunk_size",
    "maximum_coarse_chunk_size", "donor_lineage_repartition_replay_count",
    "duplicate_reassignment_prevented_count", "nonterminal_coarse_request_count",
    "coarse_requests_completed", "reserve_wakes_rejected_no_useful_work",
    "reserve_wakes_with_bound_work", "reserve_wakes_completed_with_useful_work",
    "reserve_wake_useful_completion_ratio",
]
CONTROLLER_FIELDS = [
    "controller_mode", "breach_episode_count", "breach_episode_recovered_count",
    "episode_unattainable_count", "activation_batches_seated",
    "predictive_batches_seated", "reactive_batches_seated",
    "duplicate_activation_batch_prevented_count", "prediction_decision_count",
    "false_positive_wake_count", "late_wake_count", "maximum_H_pipeline",
    "time_weighted_H_pipeline",
]


def run_plan() -> list:
    return [{"run_id": f"8s-{row['scenario_id']}-s{i:02d}", "scenario": row,
             "seed_class": "CONFIRMATORY_8S", "seed_index": i, "master_seed": seed}
            for row in S8S.SCENARIOS
            for i, seed in enumerate(S8S.confirmatory_seeds_8s())]


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


def coarse_structural_gates(run) -> dict:
    """Executable chunk union/disjointness verification for THIS run's coarse requests."""
    by = {}
    for q_ in run.coarse_requests.values():
        by.setdefault((q_.BreachEpisodeID, q_.DonorAssignmentID), []).append(q_)
    donor_led = {}
    for rec in run.evaluation_ledger:
        donor_led.setdefault((rec.RoundID, rec.AssignmentID), []).append(rec)
    disjoint = contiguous = donor_exclusion = True
    for (ep_id, donor_aid), reqs in by.items():
        ivs = sorted((q_.chunk_start, q_.chunk_end) for q_ in reqs)
        for (a0, a1), (b0, b1) in zip(ivs, ivs[1:]):
            disjoint &= a1 <= b0
            contiguous &= a1 == b0
        rid = reqs[0].RoundID
        for rec in donor_led.get((rid, donor_aid), []):
            for q0, q1 in ivs:
                donor_exclusion &= (rec.interval_end <= q0 or rec.interval_start >= q1)
    return {"coarse_chunks_pairwise_disjoint": disjoint,
            "coarse_chunks_contiguous": contiguous,
            "coarse_donor_never_in_ceded_chunk": donor_exclusion,
            "coarse_lineage_count": len(by)}


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
              "nonterminal_episode_count", "live_batch_after_close_count",
              "nonterminal_coarse_request_count"):
        check(f"{f} == 0", rec[f] == 0)
    for f in ("coarse_chunks_pairwise_disjoint", "coarse_chunks_contiguous",
              "coarse_donor_never_in_ceded_chunk", "residency_reconciles",
              "round_terminal_times_strictly_increasing"):
        check(f, rec[f] is True)
    return g


def execute_one(spec: dict) -> dict:
    row, seed = spec["scenario"], spec["master_seed"]
    cfg = S8S.build_config_8s(row, seed)
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
            rounds_executed=n_rounds,
            rounds_accepted=res["rounds_accepted"],
            accepted_blocks_per_closed_round=(res["rounds_accepted"] / n_rounds
                                              if n_rounds else 0.0),
            zero_block_indicator=int(res["rounds_accepted"] == 0),
            median_round_duration=(statistics.median(durs) if durs else None),
            mean_round_duration=(statistics.fmean(durs) if durs else None),
            p95_round_duration=(q(sd, 0.95) if sd else None),
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
            reassignments_per_closed_round=(res["coarse_reassignment_count"] / n_rounds
                                            if n_rounds else 0.0),
            nonterminal_activation_request_count=nonterminal_activation_request_count(run),
            **{k: res[k] for k in S8S_FIELDS},
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
            **coarse_structural_gates(run),
            **decomp,
        )
        rec["integrity_gates"] = integrity_gates(rec)
        rec["all_integrity_gates_pass"] = all(g["pass"] for g in rec["integrity_gates"])
        if (spec["seed_class"] == "CONFIRMATORY_8S"
                and (row["scenario_id"], spec["seed_index"]) in set(S8S.TIMELINE_RUNS)):
            rec.update(write_timeline(spec["run_id"], run, cfg, res))
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
    S8S.assert_seed_disjointness()
    PILOT_OUT.mkdir(exist_ok=True)
    specs = [{"run_id": f"8s-pilot-{row['scenario_id']}-p{i}", "scenario": row,
              "seed_class": "PILOT_8S", "seed_index": i, "master_seed": seed}
             for row in S8S.SCENARIOS
             for i, seed in enumerate(S8S.pilot_seeds_8s())]
    with mp.Pool(processes=MAX_WORKERS, maxtasksperchild=1) as pool:
        recs = pool.map(execute_one, specs)
    gates, all_pass = [], True

    def check(name, ok):
        nonlocal all_pass
        gates.append({"gate": name, "pass": bool(ok)})
        all_pass &= bool(ok)

    check("every mode executes (8/8 COMPLETED)",
          all(r["run_status"] == "COMPLETED" for r in recs))
    for r in recs:
        check(f"{r['run_id']}: integrity fields computable and pass",
              r.get("all_integrity_gates_pass") is True)
        check(f"{r['run_id']}: wall/RSS feasible",
              r.get("wall_clock_seconds", 1e9) <= WALL_LIMIT_S
              and r.get("peak_rss_mb", 1e9) <= RSS_LIMIT_MB)
        check(f"{r['run_id']}: useful-floor metrics exist",
              all(k in r for k in S8S_FIELDS))
    s03 = [r for r in recs if r["scenario_id"] == "S03_USEFUL_FLOOR_COARSE_REASSIGNMENT"]
    check("coarse reassignment occurs (every S03 pilot run)",
          all(r.get("coarse_reassignment_count", 0) >= 1 for r in s03))
    check("chunk union/disjointness gates pass (every S03 pilot run)",
          all(r.get("coarse_chunks_pairwise_disjoint") and r.get("coarse_chunks_contiguous")
              and r.get("coarse_donor_never_in_ceded_chunk") for r in s03))
    useful = [r for r in recs if r["scenario_id"] in
              ("S02_USEFUL_FLOOR", "S03_USEFUL_FLOOR_COARSE_REASSIGNMENT")]
    check("reserve admission enforced (every wake bound to useful work)",
          all(r.get("reserve_wakes_with_bound_work") == r.get("activation_requests_seated")
              for r in useful))
    payload = {"harness": "run_stage8s.py pilot",
               "purpose": ("STRUCTURE AND FEASIBILITY ONLY.  Nothing here may tune the "
                           "0.80 static target, the useful-floor formula, batch_size, the "
                           "partition rule, reassignment caps or acceptance margins."),
               "gates": gates, "all_structural_gates_pass": all_pass,
               "runs": [{k: r.get(k) for k in
                         ("run_id", "scenario_id", "run_status", "rounds_executed",
                          "wall_clock_seconds", "all_integrity_gates_pass",
                          "coarse_reassignment_count", "coarse_repartition_count",
                          "reserve_wakes_rejected_no_useful_work")}
                        for r in recs]}
    (PILOT_OUT / "structural_pilot_8s.json").write_text(
        json.dumps(payload, indent=1, sort_keys=True, default=str) + "\n")
    for r in recs:
        print(f"  {r['run_id']:52s} {r['run_status']:9s} "
              f"rounds={r.get('rounds_executed', '-'):>4} "
              f"wall {r.get('wall_clock_seconds', 0):5.2f}s "
              f"gates {'PASS' if r.get('all_integrity_gates_pass') else 'FAIL'}")
    print("structural pilot:", "ALL GATES PASS" if all_pass else "BLOCKED")
    return 0 if all_pass else 2


# ------------------------------------------------------------------ execute/verify/dataset
def checkpoint_path(run_id: str) -> pathlib.Path:
    return RUNS / f"{run_id}.json"


def cmd_execute() -> int:
    S8S.assert_seed_disjointness()
    pilot = PILOT_OUT / "structural_pilot_8s.json"
    if not pilot.exists() or not json.loads(pilot.read_text())["all_structural_gates_pass"]:
        raise SystemExit("STAGE_8S_BLOCKED — structural pilot has not passed")
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
    print(f"\nwall {time.time() - t0:.1f}s; checkpoints {total}/48; failures {failures}")
    print("STAGE_8S_EXECUTION_COMPLETE" if not failures and total == 48
          else "STAGE_8S_EXECUTION_INCOMPLETE_OR_GATED")
    return 0 if not failures and total == 48 else 2


def load_all() -> list:
    recs = []
    for p in run_plan():
        path = checkpoint_path(p["run_id"])
        if not path.exists():
            raise SystemExit(f"STAGE_8S_BLOCKED — missing checkpoint {path.name}")
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
    if sum(1 for r in recs if "timeline_file" in r) != 3:
        problems.append("expected exactly 3 timeline runs")
    return problems


def cmd_verify() -> int:
    problems = verify_records(load_all())
    for x in problems:
        print(f"  FAIL {x}")
    print("OK: all 48 checkpoints verified" if not problems
          else f"STAGE_8S_BLOCKED — {len(problems)} problem(s)")
    return 0 if not problems else 2


def csv_fields() -> list:
    base = ["run_id", "scenario_id", "role", "seed_class", "seed_index", "master_seed",
            "controller_mode_configured", "run_status", "all_integrity_gates_pass",
            "E_idle_kwh", "E_power_null_kwh", "absolute_reduction_kwh",
            "relative_reduction", "offline_residency_s", "a1_continuous_control_kwh",
            "rounds_executed", "rounds_accepted", "accepted_blocks_per_closed_round",
            "zero_block_indicator", "median_round_duration", "mean_round_duration",
            "p95_round_duration", "unclosed_final_tail_s",
            "static_floor_deficit_area_hash_s", "activation_requests_seated",
            "activation_requests_completed", "activation_requests_cancelled",
            "incomplete_activation_request_count", "activations_per_closed_round",
            "reassignments_per_closed_round", "nonterminal_activation_request_count"]
    integ = ["maximum_energy_identity_residual_j", "maximum_residency_partition_residual_s",
             "duplicate_nonce_count", "post_round_evaluation_record_count",
             "post_round_evaluation_nonce_count", "evaluation_missing_terminal_time_count",
             "physical_frontier_rewind_count", "work_reward_union_residual",
             "nonterminal_lease_count", "nonterminal_reassignment_request_count",
             "adversarial_action_total", "nonterminal_episode_count",
             "live_batch_after_close_count", "evaluation_ledger_entries",
             "coarse_chunks_pairwise_disjoint", "coarse_chunks_contiguous",
             "coarse_donor_never_in_ceded_chunk", "coarse_lineage_count"]
    decomp = [f"{prefix}_{c}_{unit}" for c in COMPONENTS
              for prefix, unit in (("residency", "s"), ("energy", "kwh"),
                                   ("power_null_difference", "kwh"))]
    named = ["range_idle_energy_difference_kwh", "reserve_standby_energy_difference_kwh",
             "wake_energy_difference_kwh", "activated_reserve_energy_kwh",
             "total_low_power_state_difference_kwh"]
    tail = ["wall_clock_seconds", "peak_rss_mb", "config_sha256", "engine_sha256",
            "record_sha256"]
    return base + S8S_FIELDS + CONTROLLER_FIELDS + integ + decomp + named + tail


def cmd_dataset() -> int:
    import csv                                                        # noqa: PLC0415
    recs = load_all()
    problems = verify_records(recs)
    if problems:
        for x in problems:
            print(f"  FAIL {x}")
        raise SystemExit("STAGE_8S_BLOCKED — verification failed")
    recs.sort(key=lambda r: (r["scenario_id"], r["seed_index"]))
    DOCS.mkdir(parents=True, exist_ok=True)
    with open(DOCS / "STAGE_08S_RUN_DATASET.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=csv_fields(), lineterminator="\n",
                           extrasaction="ignore")
        w.writeheader()
        for r in recs:
            w.writerow(r)
    print(f"wrote STAGE_08S_RUN_DATASET.csv ({len(recs)} rows)")
    return 0


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    cmds = {"pilot": cmd_pilot, "execute": cmd_execute, "verify": cmd_verify,
            "dataset": cmd_dataset}
    if len(argv) != 1 or argv[0] not in cmds:
        print(f"usage: run_stage8s.py {{{'|'.join(cmds)}}}", file=sys.stderr)
        return 64
    return cmds[argv[0]]()


if __name__ == "__main__":
    raise SystemExit(main())
