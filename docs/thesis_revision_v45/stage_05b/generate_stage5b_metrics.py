"""Generate the Stage-5B executable-correction evidence metrics from REAL executions.

Every number in STAGE_05B_METRICS.json and stage5b_metrics.json is produced by running the
executable Stage-5 model here — none is hand-written.  The scenarios are small, deterministic
micro-scenarios for evidence only; they are NOT the confirmatory experiment matrix and no
statistical claim is derived from them.

Run:  python docs/thesis_revision_v45/stage_05b/generate_stage5b_metrics.py
"""
from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from Models.PoCol.stage2 import (Stage2Config, run_simulation, AdversarialPolicy,
                                 RangeLeasePolicy, SecurityFloorPolicy, IncentivePolicy,
                                 results_schema, RESULT_SCHEMA_VERSION,
                                 ADVERSARIAL_COVERAGE_GAP_NO_BLOCK)
from Models.PoCol.stage2 import adversarial_runtime as adv

_HARD = 1 << 300     # unreachable target: the whole domain is searched and no block is found
_TRIVIAL = 1         # target == 2^256 - 1: every nonce is a valid solution
MINERS = ("M000", "M001", "M002", "M003")
M0, M1 = "M000", "M001"

_BASE = dict(num_miners=4, reserve_fraction=0.0, nonce_domain_size=400, batch_size=25,
             horizon_T=60.0)


def cfg(adversarial=None, incentive=None, difficulty=_HARD, **kw):
    return Stage2Config(difficulty=difficulty,
                        adversarial=adversarial or AdversarialPolicy(),
                        incentive=incentive or IncentivePolicy(), **{**_BASE, **kw})


def attacker(flags, miners=(M0,), klass="BYZANTINE", **pol):
    return AdversarialPolicy(enabled=True,
                             entities=(("E1", klass, tuple(miners), None),),
                             miner_behaviours=tuple((0, m, tuple(flags)) for m in miners),
                             **pol)


def scenario(name, description, config, run_id):
    run = run_simulation(config, run_id=run_id)
    res = results_schema(run, config)
    reasons = sorted({o.data.get("reason") for o in run.log if o.kind == "round_aborted"})
    rc = run.current_round_context
    sub_acct = res["subassignment_accounting"]
    ident_acct = res["virtual_identity_accounting"]
    return name, {
        "description": description,
        "rounds_executed": res["rounds_executed"],
        "rounds_accepted": res["rounds_accepted"],
        "rounds_no_block": res["rounds_no_block"],
        "no_block_dispositions": reasons,
        "energy_kwh": res["energy_kwh"],
        "residency_reconciles": res["residency_reconciles"],
        "evaluation_ledger_entries": res["evaluation_ledger_entries"],
        "behaviour_profile_count": res["behaviour_profile_count"],
        # ---------------- retained Stage-5 / 5A measurements ----------------
        "coverage_gap_nonce_count": res["coverage_gap_nonce_count"],
        "adversarial_coverage_gap_round_count": res["adversarial_coverage_gap_round_count"],
        "abandonment_action_count": res["abandonment_action_count"],
        "abandoned_nonce_count": res["abandoned_nonce_count"],
        "abandonment_penalty_without_action_count":
            res["abandonment_penalty_without_action_count"],
        "physical_frontier_rewind_count": res["physical_frontier_rewind_count"],
        "accepted_frontier_record_count": res["accepted_frontier_record_count"],
        "accepted_below_actual_count": res["accepted_below_actual_count"],
        "unique_rewarded_nonce_count": res["unique_rewarded_nonce_count"],
        "adversarial_reevaluation_count": res["adversarial_reevaluation_count"],
        "duplicate_work_reward_prevented_count": res["duplicate_work_reward_prevented_count"],
        "work_reward_union_residual": res["work_reward_union_residual"],
        "incentive_ledger_entries": res["incentive_ledger_entries"],
        "incentive_reconciliation_residual": res["incentive_reconciliation_residual"],
        "naive_identity_reward_total": res["naive_identity_reward_total"],
        "deduplicated_entity_reward_total": res["deduplicated_entity_reward_total"],
        "subassignment_count": res["subassignment_count"],
        "virtual_identity_count": res["virtual_identity_count"],
        "subassignment_capacity_residual": res["subassignment_capacity_residual"],
        "reported_rate_allocation_rounds": res["reported_rate_allocation_rounds"],
        "allocation_range_size_distortion_max_ratio":
            res["allocation_range_size_distortion_max_ratio"],
        "actions_rejected_over_limit": res["actions_rejected_over_limit"],
        # ---------------- Stage-5B executable corrections ----------------
        "ownership_reconciliation_rows": len(res["ownership_reconciliation"]),
        "ownership_rewarded_total": sum(r["rewarded_count"]
                                        for r in res["ownership_reconciliation"]),
        "ownership_duplicate_prevented_total": sum(
            r["duplicate_reward_prevented_count"] for r in res["ownership_reconciliation"]),
        "distinct_reward_owners": len({r["reward_owner"]
                                       for r in res["ownership_reconciliation"]
                                       if r["reward_owner"] is not None}),
        "delayed_wake_primary_count": res["delayed_wake_primary_count"],
        "delayed_wake_reserve_activation_count": res["delayed_wake_reserve_activation_count"],
        "delayed_wake_path_a_reassignment_count":
            res["delayed_wake_path_a_reassignment_count"],
        "delayed_wake_path_b_reserve_count": res["delayed_wake_path_b_reserve_count"],
        "delayed_wake_unspecified_lifecycle_count":
            res["delayed_wake_unspecified_lifecycle_count"],
        "delayed_wake_unattributed_refused": res["delayed_wake_unattributed_refused"],
        "delayed_wake_replay_no_effect_count": res["delayed_wake_replay_no_effect_count"],
        "delayed_wake_another_reserve_activated_count":
            res["delayed_wake_another_reserve_activated_count"],
        "delayed_wake_realised_extra_delay_total":
            res["delayed_wake_realised_extra_delay_total"],
        "delayed_wake_incremental_energy_j": res["delayed_wake_incremental_energy_j"],
        "subassignment_mapped_evaluation_count": res["subassignment_mapped_evaluation_count"],
        "subassignment_unmapped_evaluation_count":
            res["subassignment_unmapped_evaluation_count"],
        "entity_physical_capacity_residual": res["entity_physical_capacity_residual"],
        "virtual_identity_physical_capacity_granted":
            res["virtual_identity_physical_capacity_granted"],
        "max_physical_capacity_residual": sub_acct["max_physical_capacity_residual"],
        "identity_granted_physical_capacity": ident_acct[
            "physical_capacity_granted_by_identities"],
        "claim_overstatement_total": res["claim_overstatement_total"],
        "abandonment_coverage_gap_rounds": res["abandonment_coverage_gap_rounds"],
        "physical_evaluation_count": res["physical_evaluation_count"],
        "evaluation_ledger_nonce_total": res["evaluation_ledger_nonce_total"],
        "physical_evaluation_ledger_residual": res["physical_evaluation_ledger_residual"],
        "false_exhaustion_claims_range_end": res["false_exhaustion_claims_range_end"],
        "false_exhaustion_claim_offset": res["false_exhaustion_claim_offset"],
        "wake_handles_created": run.lease_stats["wake_handles_created"],
        "path_b_reassignment_count": sum(
            1 for r in run.reassignment_requests.values() if r.needs_stage3_wake),
        "subassignment_accounting_rows": sub_acct["rows"],
        "virtual_identity_accounting_rows": ident_acct["rows"],
        "current_round_id": str(getattr(rc, "RoundID", None)),
    }


def _replay_purity_probe():
    """S5B-2 measured directly: finalise the SAME round twice and compare EVERY metric."""
    from Models.PoCol.stage2 import RunInitialise
    from Models.PoCol.stage2.context import EvaluationRecord
    run = RunInitialise(cfg(adversarial=attacker(("PROGRESS_WITHHOLDER",)),
                            incentive=IncentivePolicy(enabled=True, r_work=1.0)))
    rc = type("RC", (), {"RoundID": "r", "TemplateID_committed": "t", "block_accepted": False,
                         "winner_miner_id": None, "round_terminal_time": None})()
    for mid, lo, hi, t in ((M0, 0, 80, 1.0), (M1, 40, 100, 2.0)):
        run.evaluation_ledger.append(EvaluationRecord(
            RoundID="r", TemplateID="t", MinerID=mid, AssignmentID="A", assignment_version=1,
            interval_start=lo, interval_end=hi, completion_time=t, contained_solution=False,
            winning_nonce=None, event_ref=None, assignment_kind="PRIMARY_ASSIGNMENT",
            RangeSliceID="S1", LeaseID="L1", lease_generation=1, progress_generation=1,
            predecessor_lease_id=None))
    adv.finalise_incentives(run, rc, 10.0)
    first_stats = json.loads(json.dumps(run.adversarial_stats, sort_keys=True, default=str))
    first_ledger = len(run.incentive_ledger)
    per_miner_first = {}
    for e in run.incentive_ledger:
        if e.component == "WORK_REWARD":
            per_miner_first[e.MinerID] = per_miner_first.get(e.MinerID, 0.0) + e.amount
    adv.finalise_incentives(run, rc, 10.0)
    second_stats = json.loads(json.dumps(run.adversarial_stats, sort_keys=True, default=str))
    per_miner_second = {}
    for e in run.incentive_ledger:
        if e.component == "WORK_REWARD":
            per_miner_second[e.MinerID] = per_miner_second.get(e.MinerID, 0.0) + e.amount
    return {
        "scenario": "predecessor [0,80) then successor [40,100) on one lineage",
        "work_reward_by_miner_first_call": per_miner_first,
        "work_reward_by_miner_second_call": per_miner_second,
        "ledger_entries_first_call": first_ledger,
        "ledger_entries_second_call": len(run.incentive_ledger),
        "ledger_unchanged": first_ledger == len(run.incentive_ledger),
        "every_metric_unchanged": first_stats == second_stats,
        "duplicate_work_reward_prevented_count":
            run.adversarial_stats["duplicate_work_reward_prevented_count"],
        "unique_rewarded_nonce_count": run.adversarial_stats["unique_rewarded_nonce_count"],
        "work_reward_union_residual": run.adversarial_stats["work_reward_union_residual"],
        "ownership_reconciliation": adv.ownership_reconciliation(run),
    }


def main() -> None:
    here = pathlib.Path(__file__).resolve().parent
    (here / "evidence").mkdir(parents=True, exist_ok=True)
    inc_full = IncentivePolicy(enabled=True, r_work=1.0, r_avail=0.1, r_win=100.0,
                               q_false=7.0, q_invalid=5.0, q_abandon=11.0)
    lease = RangeLeasePolicy(enabled=True, reassignment_wake_latency=1.0,
                             lease_duration=1e18, progress_timeout=1e18)

    scenarios = dict([
        scenario("A_honest_baseline_disabled",
                 "All Stage-5 features DISABLED: the frozen Stage-4C behaviour, unchanged.",
                 cfg(), "n-a"),
        scenario("B_ownership_predecessor_and_successor",
                 "S5B-1 END TO END: an undetected progress-withholding claim creates a "
                 "successor that re-evaluates below the accepted frontier; the predecessor keeps "
                 "its own work and the successor is paid only for the unique suffix it adds.",
                 cfg(adversarial=attacker(("PROGRESS_WITHHOLDER",),
                                          audit_detection_probability=0.0,
                                          progress_withholding_fraction=0.5),
                     incentive=inc_full, reserve_fraction=0.25, horizon_T=90.0,
                     range_lease=lease,
                     injected_lease_faults=((1, M0, 2.0, "fault"),)), "n-b"),
        scenario("C_true_path_b_reserve_reassignment",
                 "S5B-3: a GENUINE Path-B reserve reassignment (needs_stage3_wake, an AVAILABLE "
                 "reserve, a ReserveActivationRequest) that applies accepted-frontier "
                 "separation; the physical frontier still never rewinds.",
                 cfg(adversarial=attacker(("PROGRESS_WITHHOLDER",),
                                          audit_detection_probability=0.0,
                                          progress_withholding_fraction=0.5),
                     incentive=inc_full, reserve_fraction=0.5, horizon_T=120.0,
                     range_lease=lease,
                     injected_lease_faults=((1, M0, 1.3, "MINER_FAILED"),)), "n-c"),
        scenario("D_reserve_and_path_b_delayed_wakes",
                 "S5B-4: DELAYED_WAKE on every miner with the floor engaged and a fault — the "
                 "initial primary wake, the ordinary reserve-activation wake and the Path-B "
                 "reassignment reserve wake all consult the delayed-wake policy.",
                 cfg(adversarial=attacker(("DELAYED_WAKE",), miners=MINERS,
                                          delayed_wake_extra_latency=2.0,
                                          maximum_actions_per_round=100),
                     incentive=inc_full, reserve_fraction=0.5, horizon_T=90.0,
                     security_floor=SecurityFloorPolicy(enabled=True,
                                                        minimum_active_hash_rate=150.0),
                     range_lease=lease,
                     injected_lease_faults=((1, M0, 1.3, "MINER_FAILED"),)), "n-d"),
        scenario("E_path_a_delayed_wake",
                 "S5B-4: a LATE fault whose reassignee is an already-alive miner that exhausted "
                 "its own range — the Path-A reassignment wake consults the same policy.",
                 cfg(adversarial=attacker(("DELAYED_WAKE",), miners=MINERS,
                                          delayed_wake_extra_latency=2.0,
                                          maximum_actions_per_round=100),
                     incentive=inc_full, horizon_T=90.0, range_lease=lease,
                     injected_lease_faults=((1, M0, 3.5, "MINER_FAILED"),)), "n-e"),
        scenario("F_delayed_wake_another_reserve_activated",
                 "S5B-4: a delayed wake that keeps active capacity below the operational floor "
                 "really causes ANOTHER reserve activation inside the added interval.",
                 cfg(adversarial=attacker(("DELAYED_WAKE",), delayed_wake_extra_latency=5.0,
                                          maximum_actions_per_round=50),
                     incentive=inc_full, reserve_fraction=0.25, horizon_T=60.0,
                     security_floor=SecurityFloorPolicy(enabled=True,
                                                        minimum_active_hash_rate=150.0)),
                 "n-f"),
        scenario("G_delayed_wake_cancelled_at_close",
                 "S5B-4: a wake still pending at round closure is charged over the REALISED "
                 "added interval, never over the configured extra latency.",
                 cfg(adversarial=attacker(("DELAYED_WAKE",), miners=MINERS,
                                          delayed_wake_extra_latency=50.0,
                                          maximum_actions_per_round=100),
                     incentive=inc_full, horizon_T=20.0), "n-g"),
        scenario("H_zero_action_budget",
                 "S5B-5: maximum_actions_per_round = 0 prevents EVERY action type; each refusal "
                 "is counted and creates no protocol effect.",
                 cfg(adversarial=attacker(("SOLUTION_WITHHOLDER", "OUT_OF_RANGE_ACTOR",
                                           "FALSE_EXHAUSTION_CLAIMER", "IDLE_POLICY_DEFECTOR"),
                                          miners=MINERS, maximum_actions_per_round=0,
                                          solution_release_policy="NEVER_RELEASE",
                                          out_of_range_nonce_offset=5),
                     incentive=inc_full, difficulty=_TRIVIAL, horizon_T=30.0), "n-h"),
        scenario("I_free_rider_and_assignment_splitter",
                 "S5B-6: FREE_RIDER 0.5 combined with ASSIGNMENT_SPLITTER x4 budgets the "
                 "EFFECTIVE 50 nonces/s across four subassignments, never the nominal 100.",
                 cfg(adversarial=attacker(("FREE_RIDER", "ASSIGNMENT_SPLITTER"),
                                          klass="RATIONAL", free_rider_work_fraction=0.5,
                                          assignment_split_count=4),
                     incentive=inc_full, horizon_T=30.0), "n-i"),
        scenario("J_misreporter_and_assignment_splitter",
                 "S5B-6: HASH_RATE_MISREPORTER x5 combined with ASSIGNMENT_SPLITTER x4 — "
                 "over-reporting buys no physical capacity at all.",
                 cfg(adversarial=attacker(("HASH_RATE_MISREPORTER", "ASSIGNMENT_SPLITTER"),
                                          klass="RATIONAL", reported_hash_rate_multiplier=5.0,
                                          assignment_split_count=4),
                     incentive=inc_full, horizon_T=30.0), "n-j"),
        scenario("K_multiple_controlled_miners_and_identities",
                 "S5B-6: two controlled miners, each split, plus four declared virtual "
                 "identities — the entity's physical capacity is unchanged.",
                 cfg(adversarial=attacker(("ASSIGNMENT_SPLITTER",), miners=(M0, M1),
                                          klass="RATIONAL", assignment_split_count=2,
                                          sybil_identity_count=4),
                     incentive=inc_full, horizon_T=30.0), "n-k"),
        scenario("L_executed_abandonment_coverage_gap",
                 "S5B-7: an executed abandonment records its REAL unsearched suffix; the round "
                 "closes with the explicit adversarial coverage-gap disposition and can never "
                 "be labelled ordinary or full-domain exhaustion.",
                 cfg(adversarial=attacker(("IDLE_POLICY_DEFECTOR",), miners=MINERS,
                                          maximum_actions_per_round=50),
                     incentive=inc_full, horizon_T=60.0), "n-l"),
        scenario("M_false_claim_offset_overstatement",
                 "S5B-7/8: a configured false-exhaustion offset separates the claim "
                 "overstatement from the REAL unsearched suffix, and the offset is honoured "
                 "rather than silently overridden by range-end claiming.",
                 cfg(adversarial=attacker(("FALSE_EXHAUSTION_CLAIMER",), miners=MINERS,
                                          audit_detection_probability=0.0,
                                          false_exhaustion_claims_range_end=False,
                                          false_exhaustion_claim_offset=10,
                                          maximum_actions_per_round=50),
                     incentive=inc_full, horizon_T=60.0), "n-m"),
        scenario("N_physical_count_without_range_leases",
                 "S5B-8: the physical evaluation count reconciles with the evaluation ledger "
                 "when range leases are DISABLED.",
                 cfg(adversarial=attacker(("FREE_RIDER",), klass="RATIONAL",
                                          free_rider_work_fraction=0.5),
                     incentive=inc_full, horizon_T=30.0), "n-n"),
        scenario("O_physical_count_with_range_leases",
                 "S5B-8: ... and when range leases are ENABLED.",
                 cfg(adversarial=attacker(("FREE_RIDER",), klass="RATIONAL",
                                          free_rider_work_fraction=0.5),
                     incentive=inc_full, horizon_T=30.0, range_lease=lease), "n-o"),
        scenario("P_floor_and_reported_rate_allocation",
                 "S5B-8: the operational security floor and reported-rate allocation EXECUTE "
                 "TOGETHER — the reserve domain keeps its slices and only the primary span is "
                 "re-sized from reported rates.",
                 cfg(adversarial=attacker(("HASH_RATE_MISREPORTER",), klass="RATIONAL",
                                          reported_hash_rate_multiplier=5.0,
                                          coordinator_uses_reported_hash_rate=True),
                     incentive=inc_full, reserve_fraction=0.25, horizon_T=30.0,
                     security_floor=SecurityFloorPolicy(enabled=True,
                                                        minimum_active_hash_rate=1.0)), "n-p"),
    ])

    doc = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "stage": "05B",
        "algorithm": "PoCol",
        "energy_saving_mechanism": "the idle policy within PoCol",
        "adversarial_coverage_gap_label": ADVERSARIAL_COVERAGE_GAP_NO_BLOCK,
        "generator": "docs/thesis_revision_v45/stage_05b/generate_stage5b_metrics.py",
        "provenance": "every value below is produced by executing the Stage-5 model",
        "scope": {
            "what_this_is": (
                "Deterministic micro-scenario MEASUREMENTS of bounded modeled adversarial "
                "behaviours running on the accepted Stage-4C PoCol core."),
            "what_this_is_not": (
                "NOT the confirmatory experiment matrix, NOT a statistical result, and NOT "
                "evidence of incentive compatibility, fairness, Sybil resistance, "
                "selfish-mining resistance, coalition resistance, common-prefix security, "
                "chain-quality security or Bitcoin/PoW-equivalent security.  Stage 5 models "
                "bounded behaviours and measures outcomes; it does not prove PoCol defeats "
                "them."),
            "fixed_target": (
                "No Stage-5 parameter changes the fixed SHA-256 target or difficulty; dynamic "
                "difficulty remains excluded."),
            "security_floor": "operational active-capacity floor only",
            "nonce_partitioning": (
                "Nonce-domain partitioning alone is NOT an energy-saving mechanism and is never "
                "described as one."),
        },
        "scenarios": scenarios,
        "replay_purity_S5B_2": _replay_purity_probe(),
    }

    gapped = [s for s in scenarios.values() if s["coverage_gap_nonce_count"] > 0]
    doc["invariants"] = {
        # ---- retained Stage-5A acceptance invariants ----
        "physical_frontier_never_rewinds": all(
            v["physical_frontier_rewind_count"] == 0 for v in scenarios.values()),
        "work_reward_union_residual_max": max(
            v["work_reward_union_residual"] for v in scenarios.values()),
        "subassignment_capacity_residual_max": max(
            v["subassignment_capacity_residual"] for v in scenarios.values()),
        "no_abandonment_penalty_without_action": all(
            v["abandonment_penalty_without_action_count"] == 0 for v in scenarios.values()),
        "incentive_reconciliation_residual_max": max(
            v["incentive_reconciliation_residual"] for v in scenarios.values()),
        "residency_reconciles_in_every_scenario": all(
            v["residency_reconciles"] for v in scenarios.values()),
        # ---- Stage-5B acceptance invariants ----
        "S5B_1_every_rewarded_position_has_an_owner": all(
            v["ownership_rewarded_total"] == v["unique_rewarded_nonce_count"]
            for v in scenarios.values()),
        "S5B_1_duplicate_prevented_matches_reconciliation": all(
            v["ownership_duplicate_prevented_total"]
            == v["duplicate_work_reward_prevented_count"] for v in scenarios.values()),
        "S5B_2_second_finalisation_changes_nothing":
            doc["replay_purity_S5B_2"]["every_metric_unchanged"]
            and doc["replay_purity_S5B_2"]["ledger_unchanged"],
        "S5B_3_true_path_b_scenario_count": sum(
            1 for v in scenarios.values() if v["path_b_reassignment_count"] > 0),
        "S5B_4_wake_lifecycles_covered": sorted({
            lc for lc, key in (("PRIMARY_WAKE", "delayed_wake_primary_count"),
                               ("RESERVE_ACTIVATION_WAKE",
                                "delayed_wake_reserve_activation_count"),
                               ("PATH_A_REASSIGNMENT_WAKE",
                                "delayed_wake_path_a_reassignment_count"),
                               ("PATH_B_REASSIGNMENT_RESERVE_WAKE",
                                "delayed_wake_path_b_reserve_count"))
            if any(v[key] > 0 for v in scenarios.values())}),
        "S5B_4_no_unattributed_or_unspecified_wake": all(
            v["delayed_wake_unattributed_refused"] == 0
            and v["delayed_wake_unspecified_lifecycle_count"] == 0
            for v in scenarios.values()),
        "S5B_4_another_reserve_activated_total": sum(
            v["delayed_wake_another_reserve_activated_count"] for v in scenarios.values()),
        "S5B_5_actions_rejected_over_limit_total": sum(
            v["actions_rejected_over_limit"] for v in scenarios.values()),
        "S5B_5_zero_budget_scenario_has_no_action_effect": (
            scenarios["H_zero_action_budget"]["abandonment_action_count"] == 0
            and scenarios["H_zero_action_budget"]["coverage_gap_nonce_count"] == 0
            and scenarios["H_zero_action_budget"]["actions_rejected_over_limit"] > 0),
        "S5B_6_entity_physical_capacity_residual_max": max(
            v["entity_physical_capacity_residual"] for v in scenarios.values()),
        "S5B_6_unmapped_evaluation_total": sum(
            v["subassignment_unmapped_evaluation_count"] for v in scenarios.values()),
        "S5B_6_identities_grant_no_physical_capacity": all(
            v["virtual_identity_physical_capacity_granted"] == 0.0
            for v in scenarios.values()),
        "S5B_7_no_gapped_round_closes_as_exhaustion": all(
            "round_exhausted_no_block" not in v["no_block_dispositions"]
            and "full_domain_exhausted_no_block" not in v["no_block_dispositions"]
            for v in gapped),
        "S5B_7_abandonment_never_reports_a_zero_gap": all(
            v["coverage_gap_nonce_count"] >= v["abandoned_nonce_count"]
            for v in scenarios.values()),
        "S5B_8_physical_count_matches_ledger_in_every_scenario": all(
            v["physical_evaluation_ledger_residual"] == 0 for v in scenarios.values()),
        "S5B_8_no_zero_physical_count_beside_a_non_empty_ledger": all(
            v["physical_evaluation_count"] > 0 or v["evaluation_ledger_entries"] == 0
            or v["behaviour_profile_count"] == 0 for v in scenarios.values()),
        "disabled_baseline_has_zero_stage5_effect": (
            scenarios["A_honest_baseline_disabled"]["behaviour_profile_count"] == 0
            and scenarios["A_honest_baseline_disabled"]["incentive_ledger_entries"] == 0
            and scenarios["A_honest_baseline_disabled"]["physical_evaluation_count"] == 0),
    }

    for out in (here / "STAGE_05B_METRICS.json",
                here / "evidence" / "stage5b_metrics.json"):
        out.write_text(json.dumps(doc, indent=2, sort_keys=True, default=str) + "\n")
        print("wrote", out.relative_to(ROOT))


if __name__ == "__main__":
    main()
