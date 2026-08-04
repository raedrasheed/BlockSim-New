#!/usr/bin/env python3
"""Stage 7M — minimal frozen execution of the Stage-6M preregistration.

Commands (run in this order):

    python run_stage7m.py preflight     # ONE dry-run preflight; PILOT seeds only
    python run_stage7m.py execute       # 30 confirmatory + 2 exploratory runs, <= 2 workers
    python run_stage7m.py dataset       # 30-row confirmatory dataset + 2-row scale table
    python run_stage7m.py verify        # re-verify every checkpoint checksum + audit digests

Discipline
----------
* The design is FROZEN (Stage-6M commit).  Nothing here re-tunes any parameter.
* The preflight executes ONLY pilot seeds that are assigned to no Stage-7M run, and it gates
  on: projected total wall <= 4 h, projected peak RSS <= 8 GB at the selected concurrency,
  free disk >= 2 GB, zero pre-existing output, 32 unique run identifiers.  On any failure it
  prints STAGE_7M_BLOCKED and exits non-zero.
* Every run checkpoints ATOMICALLY (tmp file + os.replace) after completion; re-running
  `execute` skips completed checkpoints, so interruption is recoverable without re-execution.
* Compact run-level output only: the preregistered outcomes, integrity counts, round-duration
  summary, residuals, identity, seed, config hash, engine hash, wall time, peak RSS, checksum
  and status.  Full detailed ledgers are preserved ONLY for the two preregistered audit runs
  (M01 seed-index 0, M03 seed-index 0), compressed.
* NO aggregation, interval, p-value or cross-run effect summary is computed here.  That is
  Stage 8M, on the frozen dataset.
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
import shutil
import statistics
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
STAGE6 = REPO_ROOT / "experiments" / "thesis_revision_v45" / "stage_06"
STAGE6M = REPO_ROOT / "experiments" / "thesis_revision_v45" / "stage_06m"
for p in (str(REPO_ROOT), str(STAGE6), str(STAGE6M)):
    if p not in sys.path:
        sys.path.insert(0, p)

import scenarios_6m as M                                                        # noqa: E402
from run_pilot import (post_round_audit, residency_and_energy_identity,         # noqa: E402
                       round_durations, nonterminal_activation_request_count)
from generate_completion_report import ACCEPTED_DIGESTS                         # noqa: E402
from Models.PoCol.stage2.simulator import run_simulation                        # noqa: E402
from Models.PoCol.stage2.adapter import results_schema                          # noqa: E402
from Models.PoCol.stage2.config import a1_continuous_control_kwh                # noqa: E402

DOCS = REPO_ROOT / "docs" / "thesis_revision_v45" / "stage_07m"
RUNS = HERE / "runs"
AUDIT = HERE / "audit"
PREFLIGHT_RECORD = DOCS / "STAGE_07M_PREFLIGHT_RECORD.json"

MAX_WORKERS = 2
WALL_LIMIT_H = 4.0
RSS_LIMIT_GB = 8.0
DISK_MIN_GB = 2.0
WALL_SAFETY = 1.5           # projection safety factor on measured per-class wall
RSS_SAFETY = 1.25           # projection safety factor on measured per-class RSS
#: Unassigned PILOT seed indexes used ONLY to time the two cost classes in the preflight.
#: (0,1 are the structural pilot; 2,3 are assigned to X01/X02; 4,5 are free.)
PREFLIGHT_PILOT_INDEX = {"CORE": 0, "SCALE_X01": 4, "SCALE_X02": 5}

#: Adversarial counters in the accepted schema whose sum defines adversarial_action_total.
ADVERSARIAL_COUNTERS = ("adversarial_entity_count", "adversarial_miner_count",
                        "adversarial_duplicate_evaluation_count",
                        "adversarial_coverage_gap_round_count",
                        "adversarial_reevaluation_count", "solution_withholding_count")

ENERGY_IDENTITY_TOLERANCE_J = 1e-8
RESIDENCY_PARTITION_TOLERANCE_S = 1e-9
POWER_NULL_A1_TOLERANCE_KWH = 1e-9


# ------------------------------------------------------------------ run plan
def run_plan() -> list:
    """The 32 frozen runs: (run_id, scenario_row, seed_class, seed_index, master_seed)."""
    plan = []
    seeds = M.confirmatory_seeds()
    for row in M.CONFIRMATORY:
        for i, seed in enumerate(seeds):
            plan.append({"run_id": f"7m-{row['scenario_id']}-s{i:02d}", "scenario": row,
                         "seed_class": "CONFIRMATORY", "seed_index": i, "master_seed": seed})
    pilots = M.pilot_seeds()
    for row in M.EXPLORATORY:
        i = M.SCALE_CHECK_PILOT_SEED_INDEX[row["scenario_id"]]
        plan.append({"run_id": f"7m-{row['scenario_id']}-p{i:02d}", "scenario": row,
                     "seed_class": "PILOT", "seed_index": i, "master_seed": pilots[i]})
    return plan


def is_audit_run(scenario_id: str, seed_class: str, seed_index: int) -> bool:
    return seed_class == "CONFIRMATORY" and (scenario_id, seed_index) in set(M.AUDIT_RUNS)


# ------------------------------------------------------------------ hashes
def engine_hash() -> str:
    """One digest binding the run record to the ACCEPTED engine baseline (Stage 5D)."""
    lines = [f"{rel}:{digest}" for rel, digest in sorted(ACCEPTED_DIGESTS.items())]
    return hashlib.sha256("\n".join(lines).encode()).hexdigest()


def verify_engine() -> None:
    for rel, digest in sorted(ACCEPTED_DIGESTS.items()):
        actual = hashlib.sha256((REPO_ROOT / rel).read_bytes()).hexdigest()
        if actual != digest:
            raise SystemExit(f"STAGE_7M_BLOCKED — engine drift in {rel}")


def config_hash(cfg) -> str:
    payload = json.dumps(dataclasses.asdict(cfg), sort_keys=True, default=str)
    return hashlib.sha256(payload.encode()).hexdigest()


def record_checksum(rec: dict) -> str:
    body = {k: v for k, v in rec.items() if k != "record_sha256"}
    return hashlib.sha256(
        json.dumps(body, sort_keys=True, default=str).encode()).hexdigest()


def to_jsonable(x, _stack=None):
    """Cycle-safe JSON projection.  Run-state objects (e.g. activation requests) can hold
    back-references to shared registries; a revisit on the CURRENT descent path is emitted as
    a marker string instead of recursing forever."""
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


# ------------------------------------------------------------------ per-run worker
def execute_one(spec: dict) -> dict:
    """One physical run -> compact preregistered record.  Runs in its own process
    (maxtasksperchild=1) so peak RSS is attributed to exactly this run."""
    row, seed = spec["scenario"], spec["master_seed"]
    cfg = M.build_config_6m(row, seed)
    rec = {"run_id": spec["run_id"], "scenario_id": row["scenario_id"], "role": row["role"],
           "seed_class": spec["seed_class"], "seed_index": spec["seed_index"],
           "master_seed": seed, "hypotheses": row["hypotheses"],
           "config_sha256": config_hash(cfg), "engine_sha256": engine_hash(),
           "python_version": sys.version.split()[0]}
    t0 = time.time()
    try:
        run = run_simulation(cfg, run_id=spec["run_id"])
        res = results_schema(run, cfg)
        durs, monotonic = round_durations(run, cfg)
        ident = residency_and_energy_identity(run, cfg)
        audit = post_round_audit(run)
        pair = M.energy_pair_kwh(run, cfg)
        a1 = a1_continuous_control_kwh(cfg)
        adversarial_action_total = sum(int(res[k]) for k in ADVERSARIAL_COUNTERS)
        rec.update(
            run_status="COMPLETED",
            wall_clock_seconds=time.time() - t0,
            peak_rss_mb=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0,
            # --- primary preregistered outcomes -------------------------------------
            E_idle_kwh=pair["E_idle_kwh"],
            E_power_null_kwh=pair["E_power_null_kwh"],
            absolute_reduction_kwh=pair["absolute_reduction_kwh"],
            relative_reduction=pair["relative_reduction"],
            # --- service outcomes ---------------------------------------------------
            rounds_accepted=res["rounds_accepted"],
            median_round_duration=(statistics.median(durs) if durs else None),
            rounds_executed=len(run.round_terminal_times),
            zero_block_indicator=int(res["rounds_accepted"] == 0),
            round_terminal_times_strictly_increasing=bool(monotonic),
            round_duration_min=(min(durs) if durs else None),
            round_duration_max=(max(durs) if durs else None),
            # --- operational (floor) outcomes ---------------------------------------
            total_duration_below_floor=res["total_duration_below_floor"],
            floor_unattainable_count=res["floor_unattainable_count"],
            security_floor_observation_count=res["security_floor_observation_count"],
            reserve_activations_seated=res["reserve_activations_seated"],
            reserve_activations_completed=res["reserve_activations_completed"],
            nonterminal_activation_request_count=nonterminal_activation_request_count(run),
            # --- integrity outcomes -------------------------------------------------
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
            adversarial_action_total=adversarial_action_total,
            offline_residency_s=pair["offline_residency_s"],
            power_null_equals_A1_residual_kwh=abs(pair["E_power_null_kwh"] - a1),
            a1_continuous_control_kwh=a1,
            residency_reconciles=bool(res["residency_reconciles"]),
            evaluation_ledger_entries=res["evaluation_ledger_entries"],
            energy_kwh_reported=res["energy_kwh"],
        )
        rec["integrity_gates"] = integrity_gates(rec)
        rec["all_integrity_gates_pass"] = all(g["pass"] for g in rec["integrity_gates"])
        if is_audit_run(row["scenario_id"], spec["seed_class"], spec["seed_index"]):
            rec.update(write_audit_ledger(spec["run_id"], run, cfg, res))
    except Exception as exc:                                          # noqa: BLE001
        rec.update(run_status="EXCEPTION", exception=repr(exc),
                   wall_clock_seconds=time.time() - t0,
                   all_integrity_gates_pass=False)
    rec["record_sha256"] = record_checksum(rec)
    return rec


def integrity_gates(rec: dict) -> list:
    """The preregistered deterministic gates, evaluated per run."""
    g = []
    def check(name, ok):
        g.append({"gate": name, "pass": bool(ok)})
    check("maximum_energy_identity_residual_j <= 1e-8",
          rec["maximum_energy_identity_residual_j"] <= ENERGY_IDENTITY_TOLERANCE_J)
    check("maximum_residency_partition_residual_s <= 1e-9",
          rec["maximum_residency_partition_residual_s"] <= RESIDENCY_PARTITION_TOLERANCE_S)
    check("duplicate_nonce_count == 0", rec["duplicate_nonce_count"] == 0)
    check("post_round_evaluation_record_count == 0",
          rec["post_round_evaluation_record_count"] == 0)
    check("post_round_evaluation_nonce_count == 0",
          rec["post_round_evaluation_nonce_count"] == 0)
    check("evaluation_missing_terminal_time_count == 0",
          rec["evaluation_missing_terminal_time_count"] == 0)
    check("physical_frontier_rewind_count == 0", rec["physical_frontier_rewind_count"] == 0)
    check("work_reward_union_residual == 0", rec["work_reward_union_residual"] == 0)
    check("nonterminal_lease_count == 0", rec["nonterminal_lease_count"] == 0)
    check("nonterminal_reassignment_request_count == 0",
          rec["nonterminal_reassignment_request_count"] == 0)
    check("adversarial_action_total == 0 (maps nonterminal_adversarial_action_count)",
          rec["adversarial_action_total"] == 0)
    check("nonterminal_activation_request_count == 0",
          rec["nonterminal_activation_request_count"] == 0)
    check("residency_reconciles", rec["residency_reconciles"] is True)
    check("round_terminal_times_strictly_increasing",
          rec["round_terminal_times_strictly_increasing"] is True)
    if rec["offline_residency_s"] == 0.0:
        check("power_null_equals_A1_residual_kwh <= 1e-9 (zero offline residency)",
              rec["power_null_equals_A1_residual_kwh"] <= POWER_NULL_A1_TOLERANCE_KWH)
    return g


def write_audit_ledger(run_id: str, run, cfg, res: dict) -> dict:
    """Full detailed ledgers for ONE preregistered audit run, gzip-compressed."""
    AUDIT.mkdir(exist_ok=True)
    payload = {
        "run_id": run_id,
        "results_schema": to_jsonable(res),
        "evaluation_ledger": [to_jsonable(r) for r in run.evaluation_ledger],
        "round_terminal_times": to_jsonable(run.round_terminal_times),
        "per_miner_residency_s": {str(mid): to_jsonable(run.miners[mid].duration)
                                  for mid in run.miners},
        "activation_requests": to_jsonable(getattr(run, "activation_requests", {})),
        "event_log": [to_jsonable(e) for e in run.log],
    }
    raw = json.dumps(payload, sort_keys=True, default=str).encode()
    dest = AUDIT / f"{run_id}_full_ledger.json.gz"
    tmp = dest.with_suffix(".gz.tmp")
    with gzip.open(tmp, "wb", compresslevel=9) as fh:
        fh.write(raw)
    os.replace(tmp, dest)
    return {"audit_ledger_file": str(dest.relative_to(REPO_ROOT)),
            "audit_ledger_sha256": hashlib.sha256(dest.read_bytes()).hexdigest(),
            "audit_ledger_raw_bytes": len(raw),
            "audit_ledger_compressed_bytes": dest.stat().st_size}


# ------------------------------------------------------------------ preflight
def preflight_one(spec: dict) -> dict:
    """Time ONE unassigned-pilot-seed run of a cost class (child process)."""
    row, seed = spec["scenario"], spec["master_seed"]
    cfg = M.build_config_6m(row, seed)
    t0 = time.time()
    run = run_simulation(cfg, run_id=spec["run_id"])
    wall = time.time() - t0
    return {"cost_class": spec["cost_class"], "scenario_id": row["scenario_id"],
            "pilot_seed_index": spec["seed_index"], "wall_seconds": wall,
            "peak_rss_mb": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0,
            "rounds_executed": len(run.round_terminal_times)}


def cmd_preflight() -> int:
    M.assert_core_matches_directive()
    verify_engine()
    plan = run_plan()
    pilots = M.pilot_seeds()
    assigned = {p["master_seed"] for p in plan}
    gates, samples = [], []

    def check(name, ok, value=None):
        gates.append({"gate": name, "pass": bool(ok), "value": value})

    # ---- static gates -----------------------------------------------------------
    ids = [p["run_id"] for p in plan]
    check("exactly 32 planned runs", len(plan) == 32, len(plan))
    check("all 32 run identifiers unique", len(set(ids)) == 32, len(set(ids)))
    pre = [str(q.relative_to(REPO_ROOT)) for d in (RUNS, AUDIT) if d.exists()
           for q in d.iterdir()]
    check("zero pre-existing output", not pre, pre or "none")
    free_gb = shutil.disk_usage(REPO_ROOT).free / 1e9
    check(f"free disk >= {DISK_MIN_GB} GB", free_gb >= DISK_MIN_GB, round(free_gb, 2))

    # ---- dry-run timing: PILOT seeds only, none assigned to any Stage-7M run ----
    specs = [
        {"cost_class": "CORE", "run_id": "7m-preflight-core",
         "scenario": M.CONFIRMATORY[2],          # M03: the most expensive core class
         "seed_index": PREFLIGHT_PILOT_INDEX["CORE"],
         "master_seed": pilots[PREFLIGHT_PILOT_INDEX["CORE"]]},
        {"cost_class": "SCALE_X01", "run_id": "7m-preflight-x01",
         "scenario": M.EXPLORATORY[0],
         "seed_index": PREFLIGHT_PILOT_INDEX["SCALE_X01"],
         "master_seed": pilots[PREFLIGHT_PILOT_INDEX["SCALE_X01"]]},
        {"cost_class": "SCALE_X02", "run_id": "7m-preflight-x02",
         "scenario": M.EXPLORATORY[1],
         "seed_index": PREFLIGHT_PILOT_INDEX["SCALE_X02"],
         "master_seed": pilots[PREFLIGHT_PILOT_INDEX["SCALE_X02"]]},
    ]
    for s in specs:
        assert s["master_seed"] not in assigned, \
            "preflight may not execute a seed assigned to a Stage-7M run"
    with mp.Pool(processes=1, maxtasksperchild=1) as pool:
        samples = pool.map(preflight_one, specs)

    core = next(s for s in samples if s["cost_class"] == "CORE")
    x01 = next(s for s in samples if s["cost_class"] == "SCALE_X01")
    x02 = next(s for s in samples if s["cost_class"] == "SCALE_X02")
    projected_wall_s = WALL_SAFETY * (30 * core["wall_seconds"]
                                      + x01["wall_seconds"] + x02["wall_seconds"])
    peak_class_rss = max(s["peak_rss_mb"] for s in samples)
    projected_rss_gb = RSS_SAFETY * MAX_WORKERS * peak_class_rss / 1024.0
    check("projected total wall <= 4 h (sequential-equivalent x safety 1.5)",
          projected_wall_s <= WALL_LIMIT_H * 3600.0, round(projected_wall_s, 1))
    check(f"projected peak RSS <= {RSS_LIMIT_GB} GB at {MAX_WORKERS} workers (x1.25)",
          projected_rss_gb <= RSS_LIMIT_GB, round(projected_rss_gb, 3))

    all_pass = all(g["pass"] for g in gates)
    DOCS.mkdir(parents=True, exist_ok=True)
    record = {"harness": "run_stage7m.py preflight",
              "note": ("dry-run preflight; every executed seed is an UNASSIGNED pilot seed; "
                       "no confirmatory seed and no assigned exploratory seed was executed; "
                       "no energy quantity was computed or recorded"),
              "max_workers": MAX_WORKERS, "wall_safety_factor": WALL_SAFETY,
              "rss_safety_factor": RSS_SAFETY, "engine_sha256": engine_hash(),
              "timing_samples": samples, "gates": gates, "all_gates_pass": all_pass,
              "verdict": "STAGE_7M_PREFLIGHT_PASSED" if all_pass else "STAGE_7M_BLOCKED"}
    PREFLIGHT_RECORD.write_text(json.dumps(record, indent=1, sort_keys=True) + "\n")
    for g in gates:
        print(f"  [{'PASS' if g['pass'] else 'FAIL'}] {g['gate']}: {g['value']}")
    print(record["verdict"])
    return 0 if all_pass else 2


# ------------------------------------------------------------------ execute
def checkpoint_path(run_id: str) -> pathlib.Path:
    return RUNS / f"{run_id}.json"


def cmd_execute() -> int:
    M.assert_core_matches_directive()
    verify_engine()
    if not PREFLIGHT_RECORD.exists():
        raise SystemExit("STAGE_7M_BLOCKED — no preflight record; run `preflight` first")
    pf = json.loads(PREFLIGHT_RECORD.read_text())
    if not pf.get("all_gates_pass"):
        raise SystemExit("STAGE_7M_BLOCKED — preflight did not pass")
    RUNS.mkdir(exist_ok=True)
    plan = run_plan()
    pending = [p for p in plan if not checkpoint_path(p["run_id"]).exists()]
    done = len(plan) - len(pending)
    if done:
        print(f"resume: {done} checkpoint(s) already present; {len(pending)} to run")
    t0 = time.time()
    failures = 0
    with mp.Pool(processes=MAX_WORKERS, maxtasksperchild=1) as pool:
        for rec in pool.imap_unordered(execute_one, pending):
            dest = checkpoint_path(rec["run_id"])
            tmp = dest.with_suffix(".json.tmp")
            tmp.write_text(json.dumps(rec, indent=1, sort_keys=True, default=str) + "\n")
            os.replace(tmp, dest)                       # atomic checkpoint
            ok = rec["run_status"] == "COMPLETED" and rec["all_integrity_gates_pass"]
            failures += (not ok)
            print(f"  {rec['run_id']:34s} {rec['run_status']:9s} "
                  f"wall {rec.get('wall_clock_seconds', 0):6.2f}s "
                  f"rss {rec.get('peak_rss_mb', 0):7.1f} MB "
                  f"gates {'PASS' if rec.get('all_integrity_gates_pass') else 'FAIL'}")
    total = sum(1 for p in plan if checkpoint_path(p["run_id"]).exists())
    print(f"\nexecution wall: {time.time() - t0:.1f}s; checkpoints: {total}/32; "
          f"failures this pass: {failures}")
    if failures or total != 32:
        print("STAGE_7M_EXECUTION_INCOMPLETE_OR_GATED")
        return 2
    print("STAGE_7M_EXECUTION_COMPLETE")
    return 0


# ------------------------------------------------------------------ dataset + verify
CSV_FIELDS = [
    "run_id", "scenario_id", "role", "seed_class", "seed_index", "master_seed", "hypotheses",
    "run_status", "all_integrity_gates_pass",
    "E_idle_kwh", "E_power_null_kwh", "absolute_reduction_kwh", "relative_reduction",
    "rounds_accepted", "median_round_duration", "rounds_executed", "zero_block_indicator",
    "total_duration_below_floor", "floor_unattainable_count",
    "security_floor_observation_count", "reserve_activations_seated",
    "reserve_activations_completed", "nonterminal_activation_request_count",
    "maximum_energy_identity_residual_j", "maximum_residency_partition_residual_s",
    "duplicate_nonce_count", "post_round_evaluation_record_count",
    "post_round_evaluation_nonce_count", "evaluation_missing_terminal_time_count",
    "physical_frontier_rewind_count", "work_reward_union_residual",
    "nonterminal_lease_count", "nonterminal_reassignment_request_count",
    "adversarial_action_total", "offline_residency_s", "power_null_equals_A1_residual_kwh",
    "a1_continuous_control_kwh", "evaluation_ledger_entries",
    "wall_clock_seconds", "peak_rss_mb", "config_sha256", "engine_sha256", "record_sha256",
]


def load_all_records() -> list:
    plan = run_plan()
    recs = []
    for p in plan:
        path = checkpoint_path(p["run_id"])
        if not path.exists():
            raise SystemExit(f"STAGE_7M_BLOCKED — missing checkpoint {path.name}")
        recs.append(json.loads(path.read_text()))
    return recs


def verify_records(recs: list) -> list:
    problems = []
    for rec in recs:
        if record_checksum(rec) != rec.get("record_sha256"):
            problems.append(f"{rec['run_id']}: record checksum mismatch")
        if rec.get("run_status") != "COMPLETED":
            problems.append(f"{rec['run_id']}: status {rec.get('run_status')}")
        if not rec.get("all_integrity_gates_pass"):
            problems.append(f"{rec['run_id']}: integrity gate failure")
        if "audit_ledger_file" in rec:
            f = REPO_ROOT / rec["audit_ledger_file"]
            if not f.exists():
                problems.append(f"{rec['run_id']}: audit ledger missing")
            elif hashlib.sha256(f.read_bytes()).hexdigest() != rec["audit_ledger_sha256"]:
                problems.append(f"{rec['run_id']}: audit ledger digest mismatch")
    audits = [r for r in recs if "audit_ledger_file" in r]
    if len(audits) != 2:
        problems.append(f"expected exactly 2 audit-ledger runs, found {len(audits)}")
    return problems


def cmd_verify() -> int:
    problems = verify_records(load_all_records())
    for x in problems:
        print(f"  FAIL {x}")
    print("OK: all 32 checkpoints verified" if not problems
          else f"STAGE_7M_BLOCKED — {len(problems)} problem(s)")
    return 0 if not problems else 2


def cmd_dataset() -> int:
    import csv                                                       # noqa: PLC0415
    recs = load_all_records()
    problems = verify_records(recs)
    if problems:
        for x in problems:
            print(f"  FAIL {x}")
        raise SystemExit("STAGE_7M_BLOCKED — checksum/gate verification failed")
    conf = sorted((r for r in recs if r["role"] == "CONFIRMATORY"),
                  key=lambda r: (r["scenario_id"], r["seed_index"]))
    expl = sorted((r for r in recs if r["role"] == "EXPLORATORY_SCALE_CHECK"),
                  key=lambda r: r["scenario_id"])
    assert len(conf) == 30 and len(expl) == 2
    DOCS.mkdir(parents=True, exist_ok=True)
    for name, rows in (("STAGE_07M_CONFIRMATORY_DATASET.csv", conf),
                       ("STAGE_07M_EXPLORATORY_SCALE_TABLE.csv", expl)):
        dest = DOCS / name
        with open(dest, "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=CSV_FIELDS, lineterminator="\n",
                               extrasaction="ignore")
            w.writeheader()
            for r in rows:
                w.writerow(r)
        print(f"wrote {dest.relative_to(REPO_ROOT)} ({len(rows)} rows)")
    return 0


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    cmds = {"preflight": cmd_preflight, "execute": cmd_execute,
            "dataset": cmd_dataset, "verify": cmd_verify}
    if len(argv) != 1 or argv[0] not in cmds:
        print(f"usage: run_stage7m.py {{{'|'.join(cmds)}}}", file=sys.stderr)
        return 64
    return cmds[argv[0]]()


if __name__ == "__main__":
    raise SystemExit(main())
