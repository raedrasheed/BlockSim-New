"""Generate the Stage-5D post-round evidence-integrity metrics from REAL executions.

The Stage-5C generator defined

    post_round_evaluation_count = len(run.evaluation_ledger)

which counts EVERY evaluation record, not evaluations occurring after their round closed.  That
field is invalid and is superseded here by a CAUSAL computation over the immutable evaluation
ledger and ``run_ctx.round_terminal_times``:

  post_round_evaluation_record_count
      records whose completion_time is strictly later than their round's terminal time plus a
      declared floating-point tolerance;
  post_round_evaluation_nonce_count
      sum(interval_end - interval_start) over exactly those records;
  evaluation_missing_terminal_time_count
      finalised records whose RoundID has NO terminal time — never silently treated as valid.

Every value below is produced by executing the accepted Stage-5C model.  No executable model
code is modified by Stage 5D.  The scenarios are small deterministic micro-scenarios for
evidence only; they are NOT the confirmatory experiment matrix and no statistical claim is
derived from them.

Run:  python docs/thesis_revision_v45/stage_05d/generate_stage5d_metrics.py
"""
from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from Models.PoCol.stage2 import (Stage2Config, run_simulation, AdversarialPolicy,
                                 IncentivePolicy, RangeLeasePolicy, results_schema,
                                 RESULT_SCHEMA_VERSION)

_HARD = 1 << 300     # unreachable target: the whole domain is searched and no block is found
_TRIVIAL = 1         # target == 2^256 - 1: every nonce is a valid solution
M0 = "M000"
MINERS = ("M000", "M001", "M002", "M003")

#: S5D-1 declared floating-point tolerance.  Simulation times are IEEE doubles produced by
#: repeated addition, so a record completing exactly AT its round's terminal time may differ in
#: the last ulp.  Only work strictly later than terminal_time + TOLERANCE is post-round.
POST_ROUND_TOLERANCE = 1e-9


def post_round_audit(run, tolerance: float = POST_ROUND_TOLERANCE):
    """S5D-1: the CAUSAL post-round evidence audit over immutable run state."""
    post_records = 0
    post_nonces = 0
    missing_terminal_time = 0
    offenders = []
    for rec in run.evaluation_ledger:
        terminal_time = run.round_terminal_times.get(rec.RoundID)
        if terminal_time is None:
            missing_terminal_time += 1
            offenders.append({"RoundID": str(rec.RoundID), "reason": "missing_terminal_time",
                              "completion_time": rec.completion_time})
            continue
        if rec.completion_time > terminal_time + tolerance:
            post_records += 1
            post_nonces += max(0, rec.interval_end - rec.interval_start)
            offenders.append({"RoundID": str(rec.RoundID), "reason": "completed_after_close",
                              "completion_time": rec.completion_time,
                              "round_terminal_time": terminal_time,
                              "nonces": rec.interval_end - rec.interval_start})
    return {
        "post_round_evaluation_record_count": post_records,
        "post_round_evaluation_nonce_count": post_nonces,
        "evaluation_missing_terminal_time_count": missing_terminal_time,
        "offending_records": offenders,
    }


def cfg(**kw):
    base = dict(num_miners=4, reserve_fraction=0.0, nonce_domain_size=400,
                difficulty=_HARD, batch_size=25, horizon_T=30.0)
    base.update(kw)
    return Stage2Config(**base)


def adv(flags, miners=(M0,), klass="RATIONAL", **pol):
    return AdversarialPolicy(enabled=True,
                             entities=(("E1", klass, tuple(miners), None),),
                             miner_behaviours=tuple((0, m, tuple(flags)) for m in miners), **pol)


def scenario(name, description, config, run_id):
    run = run_simulation(config, run_id=run_id)
    res = results_schema(run, config)
    audit = post_round_audit(run)
    ledger_rounds = {str(r.RoundID) for r in run.evaluation_ledger}
    return name, {
        "description": description,
        "adversarial_model_enabled": res["adversarial_model_enabled"],
        "range_leases_enabled": bool(config.range_lease.enabled),
        "rounds_executed": res["rounds_executed"],
        "evaluation_ledger_entries": res["evaluation_ledger_entries"],
        "evaluation_ledger_nonce_total": res["evaluation_ledger_nonce_total"],
        "physical_evaluation_count": res["physical_evaluation_count"],
        "rounds_present_in_ledger": len(ledger_rounds),
        "round_terminal_time_entries": len(run.round_terminal_times),
        # ---- S5D-1 corrected post-round integrity metrics ----
        "post_round_evaluation_record_count": audit["post_round_evaluation_record_count"],
        "post_round_evaluation_nonce_count": audit["post_round_evaluation_nonce_count"],
        "evaluation_missing_terminal_time_count":
            audit["evaluation_missing_terminal_time_count"],
        "offending_records": audit["offending_records"],
        "post_round_tolerance": POST_ROUND_TOLERANCE,
        # ---- the SUPERSEDED Stage-5C field, recorded for comparison only ----
        "superseded_post_round_evaluation_count_len_ledger": len(run.evaluation_ledger),
        # ---- scenario-liveness evidence (a zero result must not be an absent behaviour) ----
        "reassignment_requests_seated": run.lease_stats["reassignment_requests_seated"],
        "wake_handles_created": run.lease_stats["wake_handles_created"],
        "needs_stage3_wake_requests": sum(
            1 for r in run.reassignment_requests.values() if r.needs_stage3_wake),
        "abandonment_action_count": res["abandonment_action_count"],
        "false_exhaustion_accepted": res["false_exhaustion_accepted"],
        "coverage_gap_nonce_count": res["coverage_gap_nonce_count"],
        "solution_withholding_count": res["solution_withholding_count"],
    }


def main() -> None:
    here = pathlib.Path(__file__).resolve().parent
    (here / "evidence").mkdir(parents=True, exist_ok=True)
    lease = RangeLeasePolicy(enabled=True, reassignment_wake_latency=1.0,
                             lease_duration=1e18, progress_timeout=1e18)
    inc = IncentivePolicy(enabled=True, r_work=1.0)
    free_rider = adv(("FREE_RIDER",), free_rider_work_fraction=0.5)
    withholder = adv(("PROGRESS_WITHHOLDER",), klass="BYZANTINE",
                     audit_detection_probability=0.0, progress_withholding_fraction=0.5)

    scenarios = dict([
        scenario("A_disabled_honest_control",
                 "Stage-5 DISABLED honest control.",
                 cfg(), "p-a"),
        scenario("B_enabled_without_leases",
                 "Stage 5 ENABLED, range leases disabled.",
                 cfg(adversarial=free_rider, incentive=inc), "p-b"),
        scenario("C_enabled_with_leases",
                 "Stage 5 ENABLED, range leases enabled.",
                 cfg(adversarial=free_rider, incentive=inc, range_lease=lease), "p-c"),
        scenario("D_path_a_reassignment",
                 "Path-A reassignment: the reassignee is an already-alive miner that exhausted "
                 "its own range, so no Stage-3 wake is needed.",
                 cfg(adversarial=withholder, incentive=inc, range_lease=lease, horizon_T=90.0,
                     injected_lease_faults=((1, M0, 1.3, "MINER_FAILED"),)), "p-d"),
        scenario("E_path_b_reassignment",
                 "GENUINE Path-B reassignment: needs_stage3_wake, an AVAILABLE reserve and a "
                 "non-domain ReassignmentWakeHandle.",
                 cfg(adversarial=withholder, incentive=inc, range_lease=lease, horizon_T=120.0,
                     reserve_fraction=0.5,
                     injected_lease_faults=((1, M0, 1.3, "MINER_FAILED"),)), "p-e"),
        scenario("F_abandonment_coverage_gap",
                 "Executed abandonment leaving a real unsearched suffix.",
                 cfg(adversarial=adv(("IDLE_POLICY_DEFECTOR",), miners=MINERS, klass="BYZANTINE",
                                     maximum_actions_per_round=50),
                     incentive=inc, horizon_T=60.0), "p-f"),
        scenario("G_false_exhaustion_coverage_gap",
                 "Accepted false-exhaustion claim leaving a real coverage gap.",
                 cfg(adversarial=adv(("FALSE_EXHAUSTION_CLAIMER",), miners=MINERS,
                                     klass="BYZANTINE", audit_detection_probability=0.0,
                                     maximum_actions_per_round=50),
                     incentive=inc, horizon_T=60.0), "p-g"),
        scenario("H_solution_withholding",
                 "Every miner withholds its valid solution (NEVER_RELEASE).",
                 cfg(adversarial=adv(("SOLUTION_WITHHOLDER",), miners=MINERS, klass="BYZANTINE",
                                     solution_release_policy="NEVER_RELEASE",
                                     maximum_actions_per_round=50),
                     incentive=inc, difficulty=_TRIVIAL, horizon_T=30.0), "p-h"),
    ])

    doc = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "stage": "05D",
        "algorithm": "PoCol",
        "energy_saving_mechanism": "the idle policy within PoCol",
        "generator": "docs/thesis_revision_v45/stage_05d/generate_stage5d_metrics.py",
        "provenance": "every value below is produced by executing the accepted Stage-5C model",
        "post_round_tolerance": POST_ROUND_TOLERANCE,
        "superseded_field": {
            "name": "post_round_evaluation_count",
            "old_definition": "len(run.evaluation_ledger)",
            "why_invalid": (
                "It counted EVERY evaluation record rather than evaluations occurring after "
                "round closure, so it was non-zero in every healthy run and could never have "
                "detected the post-round work it was named for."),
            "superseded_by": [
                "post_round_evaluation_record_count",
                "post_round_evaluation_nonce_count",
                "evaluation_missing_terminal_time_count",
            ],
            "historical_evidence": (
                "docs/thesis_revision_v45/stage_05c/ is retained unchanged; a supersession "
                "notice was ADDED there.  No historical Stage-5C evidence was rewritten or "
                "deleted."),
        },
        "scope": {
            "what_this_is": (
                "Deterministic micro-scenario MEASUREMENTS of post-round evidence integrity in "
                "the accepted Stage-5C model."),
            "what_this_is_not": (
                "NOT the confirmatory experiment matrix, NOT a statistical result, and NOT "
                "evidence of incentive compatibility, fairness, Sybil resistance, "
                "selfish-mining resistance, coalition resistance, common-prefix security, "
                "chain-quality security or Bitcoin/PoW-equivalent security."),
        },
        "scenarios": scenarios,
    }

    doc["invariants"] = {
        "S5D_post_round_record_count_zero_in_every_scenario": all(
            v["post_round_evaluation_record_count"] == 0 for v in scenarios.values()),
        "S5D_post_round_nonce_count_zero_in_every_scenario": all(
            v["post_round_evaluation_nonce_count"] == 0 for v in scenarios.values()),
        "S5D_no_missing_terminal_time_in_every_scenario": all(
            v["evaluation_missing_terminal_time_count"] == 0 for v in scenarios.values()),
        "S5D_no_offending_records": all(
            v["offending_records"] == [] for v in scenarios.values()),
        "S5D_every_ledger_round_has_a_terminal_time": all(
            v["rounds_present_in_ledger"] <= v["round_terminal_time_entries"]
            for v in scenarios.values()),
        # the corrected metric is genuinely different from the superseded one.
        "S5D_corrected_metric_differs_from_superseded_definition": all(
            v["superseded_post_round_evaluation_count_len_ledger"]
            != v["post_round_evaluation_record_count"] for v in scenarios.values()),
        # every scenario really evaluated nonces, so a zero result is evidence not absence.
        "S5D_every_scenario_really_searched": all(
            v["evaluation_ledger_entries"] > 0 for v in scenarios.values()),
        # the named behaviours really executed.
        "S5D_path_a_seated_without_stage3_wake": (
            scenarios["D_path_a_reassignment"]["reassignment_requests_seated"] >= 1
            and scenarios["D_path_a_reassignment"]["wake_handles_created"] == 0),
        "S5D_path_b_is_a_genuine_stage3_wake": (
            scenarios["E_path_b_reassignment"]["wake_handles_created"] >= 1
            and scenarios["E_path_b_reassignment"]["needs_stage3_wake_requests"] >= 1),
        "S5D_abandonment_scenario_really_abandoned": (
            scenarios["F_abandonment_coverage_gap"]["abandonment_action_count"] > 0
            and scenarios["F_abandonment_coverage_gap"]["coverage_gap_nonce_count"] > 0),
        "S5D_false_exhaustion_scenario_really_claimed": (
            scenarios["G_false_exhaustion_coverage_gap"]["false_exhaustion_accepted"] > 0
            and scenarios["G_false_exhaustion_coverage_gap"]["coverage_gap_nonce_count"] > 0),
        "S5D_withholding_scenario_really_withheld": (
            scenarios["H_solution_withholding"]["solution_withholding_count"] > 0),
    }

    for out in (here / "STAGE_05D_METRICS.json",
                here / "evidence" / "stage5d_metrics.json"):
        out.write_text(json.dumps(doc, indent=2, sort_keys=True, default=str) + "\n")
        print("wrote", out.relative_to(ROOT))


if __name__ == "__main__":
    main()
