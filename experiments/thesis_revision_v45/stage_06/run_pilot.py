#!/usr/bin/env python3
"""Stage 6 — pilot harness (FEASIBILITY ONLY).

Executes the frozen scenario types under **pilot master seeds only**, at two tiers:

  Tier 1  reduced-scale SEMANTIC pilot   12 miners / 200 s / 400-nonce domain / batch 25
          every frozen scenario type, >= 2 pilot seeds each
  Tier 2  full-scale RUNTIME pilot       141 miners / 10 000 s / 4000-nonce domain
          four representative configurations, one pilot seed each

WHAT THE PILOT MAY BE USED FOR
    runtime, memory, output size, event count, round count, zero-block count, NA counts,
    exception counts, integrity-gate computability, configuration feasibility, completion.

WHAT THE PILOT MUST NEVER BE USED FOR
    selecting a hypothesis direction; selecting factor levels because they produced larger
    savings; removing scenarios with small effects; estimating or reporting confirmatory
    p-values; making thesis claims; choosing an attack because it looked most damaging;
    replacing confirmatory runs; changing the target or the difficulty.

Accordingly this harness records **no condition-specific energy saving, no effect estimate,
no p-value, no confidence interval and no ranking of conditions by effect**.  The one energy
quantity it retains per run is the deterministic IP-H1/IP-H2/IP-H5 accounting residual, which
is an integrity gate with a fixed numeric tolerance, not an effect.

If a pilot scenario cannot execute because the ACCEPTED engine lacks a required configuration
path, this harness records the failure and the caller must stop and return
``STAGE_6_PREREGISTRATION_BLOCKED``.  It never edits the engine.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import os
import pathlib
import resource
import sys
import time
import traceback

HERE = pathlib.Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
for p in (str(REPO_ROOT), str(HERE)):
    if p not in sys.path:
        sys.path.insert(0, p)

import scenarios as S                                                   # noqa: E402
from generate_seed_registry import build_rows                           # noqa: E402
from Models.PoCol.stage2.simulator import run_simulation                # noqa: E402
from Models.PoCol.stage2.adapter import results_schema                  # noqa: E402
from Models.PoCol.stage2.config import a1_continuous_control_kwh        # noqa: E402
from Models.PoCol.stage2.leases import TERMINAL_REASSIGN_REQUEST_STATUSES  # noqa: E402
from Models.PoCol.stage2.security import TERMINAL_REQUEST_STATUSES      # noqa: E402

PILOT_DIR = HERE / "pilot"
JOULES_PER_KWH = 3_600_000.0

#: Stage-5D declared tolerance for the causal post-round comparison (accepted, unchanged).
POST_ROUND_TOLERANCE = 1e-9
#: IP-H2 gates.
ENERGY_IDENTITY_TOLERANCE_J = 1e-8
RESIDENCY_PARTITION_TOLERANCE_S = 1e-9
#: IP-H5 gate.
EQUAL_POWER_RESIDUAL_TOLERANCE_KWH = 1e-9


# ------------------------------------------------------------------ derived measurements
def post_round_audit(run, tolerance: float = POST_ROUND_TOLERANCE) -> dict:
    """The ACCEPTED Stage-5D causal audit, re-derived from immutable run state.

    Identical in definition to
    ``tests/thesis_revision_v45/stage2/test_stage5d_post_round_evidence_integrity.py``.
    A missing terminal time is never silently treated as valid.
    """
    post_records = post_nonces = missing = 0
    for rec in run.evaluation_ledger:
        terminal_time = run.round_terminal_times.get(rec.RoundID)
        if terminal_time is None:
            missing += 1
            continue
        if rec.completion_time > terminal_time + tolerance:
            post_records += 1
            post_nonces += max(0, rec.interval_end - rec.interval_start)
    return {"post_round_evaluation_record_count": post_records,
            "post_round_evaluation_nonce_count": post_nonces,
            "evaluation_missing_terminal_time_count": missing}


def residency_and_energy_identity(run, cfg) -> dict:
    """IP-H2: the state-complete per-miner energy identity and residency partition.

        E_i == sum over states of  P(state) * t_i(state)
        sum over states of t_i(state) == run_end_time - run_start_time

    Both are re-derived from ``MinerRecord.duration`` and the canonical power map, never read
    back from a reported field.
    """
    span = float(run.run_end_time) - float(cfg.run_start_time)
    max_energy_residual = 0.0
    max_partition_residual = 0.0
    waking_s = offline_s = 0.0
    by_state = {}
    for mid in run.miners:
        m = run.miners[mid]
        joules = 0.0
        total = 0.0
        for state, dur in m.duration.items():
            joules += cfg.per_miner_power(state) * dur
            total += dur
            by_state[state] = by_state.get(state, 0.0) + dur
        max_energy_residual = max(max_energy_residual,
                                  abs(joules - run.miner_energy_joules(mid)))
        max_partition_residual = max(max_partition_residual, abs(total - span))
    waking_s = by_state.get("WAKING", 0.0)
    offline_s = by_state.get("OFFLINE", 0.0) + by_state.get("DISQUALIFIED", 0.0)
    return {"maximum_energy_identity_residual_j": max_energy_residual,
            "maximum_residency_partition_residual_s": max_partition_residual,
            "waking_residency_s": waking_s,
            "offline_or_disqualified_residency_s": offline_s,
            "residency_by_state_s": {k: v for k, v in sorted(by_state.items())}}


def round_durations(run, cfg) -> list:
    """Per-round durations derived from the ACCEPTED ``round_terminal_times`` registry.

    Rounds execute strictly sequentially, so round k spans (terminal[k-1], terminal[k]] with
    round 1 starting at ``run_start_time``.  Verified by the strict-monotonicity gate below.
    """
    items = sorted(run.round_terminal_times.items(), key=lambda kv: kv[1])
    times = [v for _, v in items]
    monotonic = all(b > a for a, b in zip(times, times[1:]))
    durs, prev = [], float(cfg.run_start_time)
    for t in times:
        durs.append(t - prev)
        prev = t
    return durs, monotonic


def nonterminal_activation_request_count(run) -> int:
    """Reserve-activation requests left non-terminal — computed exactly as the accepted adapter
    computes the lease and reassignment residues, but for the Stage-3 activation lifecycle."""
    return sum(1 for r in run.activation_requests.values()
               if r.status not in TERMINAL_REQUEST_STATUSES)


def measure(run, cfg, res) -> dict:
    """Collect ONLY feasibility, availability and integrity measurements."""
    durs, monotonic = round_durations(run, cfg)
    ident = residency_and_energy_identity(run, cfg)
    audit = post_round_audit(run)
    a1 = a1_continuous_control_kwh(cfg)
    energy = res["energy_kwh"]
    out = {
        # --- feasibility / availability ---
        "rounds_executed": res["rounds_executed"],
        "rounds_accepted": res["rounds_accepted"],
        "rounds_no_block": res["rounds_no_block"],
        "zero_block_indicator": int(res["rounds_accepted"] == 0),
        "evaluation_ledger_entries": res["evaluation_ledger_entries"],
        "evaluation_ledger_nonce_total": res["evaluation_ledger_nonce_total"],
        "physical_evaluation_count": res["physical_evaluation_count"],
        "log_event_count": len(run.log),
        "round_terminal_times_recorded": len(run.round_terminal_times),
        "round_terminal_times_strictly_increasing": bool(monotonic),
        "median_round_duration": (sorted(durs)[len(durs) // 2] if durs else None),
        "run_disposition": res["run_disposition"],
        "loop_result": res["loop_result"],
        "residency_reconciles": bool(res["residency_reconciles"]),
        # --- deterministic accounting gates (NOT effects) ---
        "continuous_all_active_control_kwh": a1,
        "a1_reference_absolute_error_kwh": (
            abs(a1 - S.A1_REFERENCE_KWH)
            if (cfg.num_miners == S.REFERENCE["num_miners"]
                and cfg.horizon_T == S.REFERENCE["horizon_T"]) else "NA"),
        "equal_power_paired_residual_kwh": (
            abs(energy - a1) if cfg.P_listen == cfg.P_hash else "NA"),
        **{k: ident[k] for k in ("maximum_energy_identity_residual_j",
                                 "maximum_residency_partition_residual_s",
                                 "waking_residency_s",
                                 "offline_or_disqualified_residency_s")},
        "residency_by_state_s": ident["residency_by_state_s"],
        # --- integrity gates (IP-H9) ---
        "duplicate_nonce_count": res["duplicate_nonce_count"],
        "post_round_evaluation_record_count": audit["post_round_evaluation_record_count"],
        "post_round_evaluation_nonce_count": audit["post_round_evaluation_nonce_count"],
        "evaluation_missing_terminal_time_count":
            audit["evaluation_missing_terminal_time_count"],
        "adapter_post_round_evaluation_count": res["post_round_evaluation_count"],
        "nonterminal_lease_count": res["nonterminal_lease_count"],
        "nonterminal_reassignment_request_count": res["nonterminal_reassignment_request_count"],
        "nonterminal_activation_request_count": nonterminal_activation_request_count(run),
        "physical_frontier_rewind_count": res["physical_frontier_rewind_count"],
        "work_reward_union_residual": res["work_reward_union_residual"],
        # IP-H10d feasibility: an ACCEPTED frontier recorded BELOW the actual committed
        # frontier is exactly what progress withholding produces, and it must never rewind the
        # physical frontier (S5A-1).
        "accepted_frontier_record_count": res["accepted_frontier_record_count"],
        "accepted_below_actual_count": res["accepted_below_actual_count"],
        "coverage_gap_nonce_count": res["coverage_gap_nonce_count"],
        "uncovered_nonce_count": res["uncovered_nonce_count"],
        "incentive_reconciliation_residual": res["incentive_reconciliation_residual"],
        # --- security floor (IP-H7 availability) ---
        "security_floor_enabled": bool(res["security_floor_enabled"]),
        "security_floor_observation_count": res["security_floor_observation_count"],
        "breach_count": res["breach_count"],
        "floor_unattainable_count": res["floor_unattainable_count"],
        "total_duration_below_floor": res["total_duration_below_floor"],
        "maximum_hash_rate_deficit": res["maximum_hash_rate_deficit"],
        "reserve_activations_seated": res["reserve_activations_seated"],
        "reserve_activations_completed": res["reserve_activations_completed"],
        # --- lease / reassignment liveness (Block C) ---
        "leases_created": res["leases_created"],
        "leases_revoked": res["leases_revoked"],
        "leases_reassigned": res["leases_reassigned"],
        "reassignment_requests_seated": res["reassignment_requests_seated"],
        "reassignment_requests_completed": res["reassignment_requests_completed"],
        "reassignment_requests_failed": res["reassignment_requests_failed"],
        "wake_handles_created": res["wake_handles_created"],
        # --- adversarial liveness (Block D) ---
        "adversarial_model_enabled": bool(res["adversarial_model_enabled"]),
        "adversarial_miner_count": res["adversarial_miner_count"],
        "delayed_wake_count": res["delayed_wake_count"],
        "solution_withholding_count": res["solution_withholding_count"],
        "withheld_never_released_count": res["withheld_never_released_count"],
        "false_exhaustion_attempted": res["false_exhaustion_attempted"],
        "false_exhaustion_accepted": res["false_exhaustion_accepted"],
        "progress_withholding_count": res["progress_withholding_count"],
        "adversarial_reevaluation_count": res["adversarial_reevaluation_count"],
        "duplicate_work_reward_prevented_count": res["duplicate_work_reward_prevented_count"],
        # --- q_adv NA feasibility ---
        "maximum_q_adv": ("NA" if res["maximum_q_adv"] is None else res["maximum_q_adv"]),
        "time_weighted_q_adv": ("NA" if res["time_weighted_q_adv"] is None
                                else res["time_weighted_q_adv"]),
        "q_adv_na_duration": res["q_adv_na_duration"],
        "schema_version": res["schema_version"],
        "schema_key_count": len(res),
    }
    # --- IP-H10d reachability (a CONFIGURATION FEASIBILITY fact, not an effect) ---
    # apply_progress_withholding under-reports COMMITTED progress, so it can only act when the
    # committed frontier has advanced strictly inside the miner's own range.  The frontier
    # advances at batch completion, so a batch boundary must fall strictly inside a primary's
    # range:   nonce_domain_size / primary_count > batch_size.
    primaries = max(1, cfg.num_miners - int(cfg.reserve_fraction * cfg.num_miners))
    per_primary = cfg.nonce_domain_size / primaries
    out["nonces_per_primary_range"] = per_primary
    out["batch_size"] = cfg.batch_size
    out["progress_withholding_reachable"] = bool(per_primary > cfg.batch_size)
    return out


# ------------------------------------------------------------------ execution
def execute(row: dict, master_seed: int, tier_name: str, tier: dict) -> dict:
    record = {"scenario_id": row["scenario_id"], "block_id": row["block_id"],
              "tier": tier_name, "master_seed": master_seed,
              "confirmatory_or_exploratory": row["confirmatory_or_exploratory"]}
    t0 = time.time()
    try:
        cfg = S.build_config(row, master_seed, tier)
    except Exception:
        record.update(run_status="CONFIG_ERROR", wall_clock_seconds=time.time() - t0,
                      traceback=traceback.format_exc())
        return record
    record["config_num_miners"] = cfg.num_miners
    record["config_difficulty"] = cfg.difficulty
    record["config_P_listen"] = cfg.P_listen
    record["config_template_seed"] = cfg.template_seed
    record["config_adversarial_seed"] = cfg.adversarial.deterministic_seed
    try:
        run = run_simulation(cfg, run_id=f"pilot-{tier_name}-{row['scenario_id']}-{master_seed}")
        res = results_schema(run, cfg)
    except Exception:
        record.update(run_status="EXECUTION_ERROR", wall_clock_seconds=time.time() - t0,
                      traceback=traceback.format_exc())
        return record
    elapsed = time.time() - t0
    # The measurement step is guarded too: a full-scale run costs tens of minutes, so an
    # unexpected missing field must degrade this ONE record rather than discard the whole
    # pilot.  A MEASUREMENT_ERROR is a failed run under the retention policy, never a silent
    # drop.
    try:
        record.update(measure(run, cfg, res))
        record["run_status"] = "COMPLETED"
    except Exception:
        record["run_status"] = "MEASUREMENT_ERROR"
        record["traceback"] = traceback.format_exc()
    record["wall_clock_seconds"] = elapsed
    record["peak_rss_mb"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0
    record["results_json_bytes"] = len(json.dumps(res, default=str).encode("utf-8"))
    return record


def pilot_seeds(count: int) -> list:
    return [r["master_seed_decimal"] for r in build_rows()
            if r["seed_class"] == "PILOT"][:count]


def write_pilot_matrix(path: pathlib.Path, plan: list) -> None:
    fields = ["tier", "scenario_id", "block_id", "confirmatory_or_exploratory",
              "master_seed", "seed_index", "num_miners", "horizon_T", "nonce_domain_size",
              "batch_size", "difficulty", "purpose"]
    buf = io.StringIO(newline="")
    w = csv.DictWriter(buf, fieldnames=fields, lineterminator="\n")
    w.writeheader()
    for r in plan:
        w.writerow(r)
    path.write_bytes(buf.getvalue().encode("utf-8"))


def run_d04_sweep(out_file: pathlib.Path) -> int:
    """Execute the frozen IP-H10d matched pair (D04C, D04) on ALL EIGHT pilot seeds.

    The fault schedule is frozen and seed-independent, so this sweep can only reveal how
    often the withholding action is *reachable* across seeds — it can never be used to
    re-tune the schedule.  Seeds that produce no withholding action are RETAINED and their
    zero-action result recorded; no seed is replaced and no seed is redrawn.
    """
    S.assert_reference_matches_baseline()
    seeds = pilot_seeds(8)
    rows = {r["scenario_id"]: r for r in S.confirmatory_rows()}
    results = []
    for sid in ("D04C", "D04"):
        for idx, master in enumerate(seeds):
            rec = execute(rows[sid], master, "TIER1", S.TIER1)
            rec["seed_index"] = idx
            results.append(rec)
            print(f"  {sid:4s} seed[{idx}] {rec['run_status']:16s} "
                  f"{rec.get('wall_clock_seconds', 0):6.2f}s "
                  f"below={rec.get('accepted_below_actual_count', '-')} "
                  f"rewind={rec.get('physical_frontier_rewind_count', '-')} "
                  f"reeval={rec.get('adversarial_reevaluation_count', '-')} "
                  f"dup={rec.get('duplicate_work_reward_prevented_count', '-')}", flush=True)
            out_file.parent.mkdir(parents=True, exist_ok=True)
            out_file.write_text(json.dumps(
                {"harness": "run_pilot.py --d04-sweep",
                 "purpose": "IP-H10d structural reachability across every pilot seed "
                            "(FEASIBILITY ONLY — never an effect estimate)",
                 "tier": S.TIER1, "pilot_seed_count": len(seeds),
                 "results": results}, indent=1, sort_keys=True, default=str) + "\n")
    bad = [r for r in results if r["run_status"] != "COMPLETED"]
    return 2 if bad else 0


def run_single_tier2(scenario_id: str, seed_index: int, out_file: pathlib.Path) -> int:
    """Execute ONE full-scale Tier-2 pilot run as an independent process.

    Each run gets its own log, its own fixed pilot seed and its own checkpointed output file,
    so the four required Tier-2 runs may execute in parallel without sharing state and without
    one failure discarding another's result.
    """
    S.assert_reference_matches_baseline()
    seeds = pilot_seeds(8)
    if not 0 <= seed_index < len(seeds):
        print(f"seed index {seed_index} out of range", file=sys.stderr)
        return 1
    master = seeds[seed_index]
    rows = {r["scenario_id"]: r for r in S.confirmatory_rows()}
    if scenario_id not in rows:
        print(f"unknown scenario {scenario_id!r}", file=sys.stderr)
        return 1
    print(f"TIER2 {scenario_id} seed[{seed_index}]={master} starting", flush=True)
    limits = {"soft_address_space": resource.getrlimit(resource.RLIMIT_AS)[0],
              "cpu_count": os.cpu_count()}
    rec = execute(rows[scenario_id], master, "TIER2", S.TIER2)
    rec["seed_index"] = seed_index
    rec["resource_limits"] = limits
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(json.dumps(rec, indent=1, sort_keys=True, default=str) + "\n")
    print(f"TIER2 {scenario_id} seed[{seed_index}] {rec['run_status']} "
          f"{rec.get('wall_clock_seconds', 0):.1f}s "
          f"rss={rec.get('peak_rss_mb', 0):.0f}MB "
          f"rounds={rec.get('rounds_executed', '-')} -> {out_file}", flush=True)
    return 0 if rec["run_status"] == "COMPLETED" else 2


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tier", choices=("1", "2", "both"), default="both")
    ap.add_argument("--seeds-per-scenario", type=int, default=2,
                    help="Tier-1 pilot seeds per scenario (>= 2)")
    ap.add_argument("--out", default=str(PILOT_DIR))
    ap.add_argument("--tier2-scenario", default=None,
                    help="execute ONE full-scale Tier-2 run and exit (parallel mode)")
    ap.add_argument("--seed-index", type=int, default=None,
                    help="pilot seed index for --tier2-scenario")
    ap.add_argument("--out-file", default=None,
                    help="output path for --tier2-scenario")
    ap.add_argument("--d04-sweep", action="store_true",
                    help="run the frozen IP-H10d pair on all eight pilot seeds and exit")
    args = ap.parse_args(argv)

    if args.d04_sweep:
        return run_d04_sweep(pathlib.Path(args.out_file) if args.out_file
                             else PILOT_DIR / "d04_all_seeds.json")

    if args.tier2_scenario:
        if args.seed_index is None or not args.out_file:
            print("--tier2-scenario requires --seed-index and --out-file", file=sys.stderr)
            return 1
        return run_single_tier2(args.tier2_scenario, args.seed_index,
                                pathlib.Path(args.out_file))

    S.assert_reference_matches_baseline()
    out_dir = pathlib.Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    seeds = pilot_seeds(8)
    seed_index = {s: i for i, s in enumerate(seeds)}
    rows = S.confirmatory_rows()
    plan, results, log_lines = [], [], []

    def note(msg):
        log_lines.append(msg)
        print(msg, flush=True)

    def checkpoint():
        """Persist after every run.  A full-scale Tier-2 run costs tens of minutes, so an
        interrupted pilot must not lose the runs that already completed."""
        (out_dir / "pilot_results.json").write_text(
            json.dumps({"harness": "run_pilot.py", "status": "IN_PROGRESS",
                        "results": results}, indent=1, sort_keys=True, default=str) + "\n")

    note(f"Stage-6 pilot harness — PILOT SEEDS ONLY.  No confirmatory seed is executed.")
    note(f"pilot seeds available: {len(seeds)}")

    if args.tier in ("1", "both"):
        note(f"\n=== Tier 1 — reduced-scale semantic pilot {S.TIER1} ===")
        for row in rows:
            for k in range(args.seeds_per_scenario):
                s = seeds[k]
                plan.append({"tier": "TIER1", "scenario_id": row["scenario_id"],
                             "block_id": row["block_id"],
                             "confirmatory_or_exploratory": row["confirmatory_or_exploratory"],
                             "master_seed": s, "seed_index": seed_index[s],
                             **{kk: S.TIER1[kk] for kk in
                                ("num_miners", "horizon_T", "nonce_domain_size", "batch_size")},
                             "difficulty": row["difficulty"],
                             "purpose": "semantic/config validation"})
                rec = execute(row, s, "TIER1", S.TIER1)
                results.append(rec)
                checkpoint()
                note(f"  {row['scenario_id']:4s} seed[{seed_index[s]}] "
                     f"{rec['run_status']:16s} {rec.get('wall_clock_seconds', 0):7.2f}s "
                     f"rounds={rec.get('rounds_executed', '-')} "
                     f"accepted={rec.get('rounds_accepted', '-')}")
                if rec["run_status"] != "COMPLETED":
                    note(f"    !! {rec['run_status']} in {row['scenario_id']}")
                    note(rec.get("traceback", ""))

    if args.tier in ("2", "both"):
        note(f"\n=== Tier 2 — full-scale runtime pilot {S.TIER2} ===")
        by_id = {r["scenario_id"]: r for r in rows}
        for j, sid in enumerate(S.TIER2_SCENARIOS):
            s = seeds[4 + j]           # Tier-2 uses pilot seeds 4..7, disjoint from Tier-1 use
            row = by_id[sid]
            plan.append({"tier": "TIER2", "scenario_id": sid, "block_id": row["block_id"],
                         "confirmatory_or_exploratory": row["confirmatory_or_exploratory"],
                         "master_seed": s, "seed_index": seed_index[s],
                         **{kk: S.TIER2[kk] for kk in
                            ("num_miners", "horizon_T", "nonce_domain_size", "batch_size")},
                         "difficulty": row["difficulty"],
                         "purpose": "runtime/memory/output-size estimation"})
            rec = execute(row, s, "TIER2", S.TIER2)
            results.append(rec)
            checkpoint()
            note(f"  {sid:4s} seed[{seed_index[s]}] {rec['run_status']:16s} "
                 f"{rec.get('wall_clock_seconds', 0):8.1f}s "
                 f"rss={rec.get('peak_rss_mb', 0):.0f}MB "
                 f"rounds={rec.get('rounds_executed', '-')}")
            if rec["run_status"] != "COMPLETED":
                note(f"    !! {rec['run_status']} in {sid}")
                note(rec.get("traceback", ""))

    write_pilot_matrix(out_dir / "pilot_matrix.csv", plan)
    payload = {
        "harness": "experiments/thesis_revision_v45/stage_06/run_pilot.py",
        "purpose": "FEASIBILITY ONLY — no effect estimate, no p-value, no confidence interval",
        "pilot_seed_count": len(seeds),
        "planned_runs": len(plan),
        "executed_runs": len(results),
        "tier1": S.TIER1, "tier2": S.TIER2,
        "results": results,
    }
    (out_dir / "pilot_results.json").write_text(
        json.dumps(payload, indent=1, sort_keys=True, default=str) + "\n")
    (out_dir / "pilot_run_log.txt").write_text("\n".join(log_lines) + "\n")

    failed = [r for r in results if r["run_status"] != "COMPLETED"]
    note(f"\nplanned={len(plan)} executed={len(results)} failed={len(failed)}")
    if failed:
        note("STAGE_6_PREREGISTRATION_BLOCKED candidates:")
        for r in failed:
            note(f"  {r['tier']} {r['scenario_id']} seed={r['master_seed']}: {r['run_status']}")
        return 2
    note("all pilot scenarios executed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
