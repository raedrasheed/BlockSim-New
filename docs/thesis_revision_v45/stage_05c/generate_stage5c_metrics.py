"""Generate the Stage-5C executable-correction evidence metrics from REAL executions.

Every number in STAGE_05C_METRICS.json and stage5c_metrics.json is produced by running the
executable Stage-5 model here — none is hand-written.  The scenarios are small, deterministic
micro-scenarios for evidence only; they are NOT the confirmatory experiment matrix and no
statistical claim is derived from them.

Run:  python docs/thesis_revision_v45/stage_05c/generate_stage5c_metrics.py
"""
from __future__ import annotations

import copy
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from Models.PoCol.stage2 import (Stage2Config, RunInitialise, run_simulation, AdversarialPolicy,
                                 RangeLeasePolicy, SecurityFloorPolicy, IncentivePolicy,
                                 MinerSearchState, MinerBehaviourProfile, results_schema,
                                 RESULT_SCHEMA_VERSION, ADVERSARIAL_COVERAGE_GAP_NO_BLOCK)
from Models.PoCol.stage2 import adversarial_runtime as adv
from Models.PoCol.stage2.context import EvaluationRecord

_HARD = 1 << 300     # unreachable target: the whole domain is searched and no block is found
M0, M1 = "M000", "M001"
MINERS = ("M000", "M001", "M002", "M003")

_BASE = dict(num_miners=4, reserve_fraction=0.0, nonce_domain_size=400, batch_size=25,
             horizon_T=30.0)


def cfg(adversarial=None, incentive=None, difficulty=_HARD, **kw):
    return Stage2Config(difficulty=difficulty,
                        adversarial=adversarial or AdversarialPolicy(),
                        incentive=incentive or IncentivePolicy(), **{**_BASE, **kw})


def attacker(flags, miners=(M0,), klass="RATIONAL", **pol):
    return AdversarialPolicy(enabled=True,
                             entities=(("E1", klass, tuple(miners), None),),
                             miner_behaviours=tuple((0, m, tuple(flags)) for m in miners), **pol)


def scenario(name, description, config, run_id):
    run = run_simulation(config, run_id=run_id)
    res = results_schema(run, config)
    reasons = sorted({o.data.get("reason") for o in run.log if o.kind == "round_aborted"})
    rc = run.current_round_context
    ledger_total = sum(r.interval_end - r.interval_start for r in run.evaluation_ledger)
    ent_rows = [r for r in res["entity_reconciliation"]
                if str(r["RoundID"]) == str(getattr(rc, "RoundID", None))]
    return name, {
        "description": description,
        "adversarial_model_enabled": res["adversarial_model_enabled"],
        "incentive_model_enabled": res["incentive_model_enabled"],
        "range_leases_enabled": bool(config.range_lease.enabled),
        "rounds_executed": res["rounds_executed"],
        "rounds_accepted": res["rounds_accepted"],
        "rounds_no_block": res["rounds_no_block"],
        "no_block_dispositions": reasons,
        "residency_reconciles": res["residency_reconciles"],
        "evaluation_ledger_entries": res["evaluation_ledger_entries"],
        # ---------------- S5C-2 global ledger-derived physical count ----------------
        "physical_evaluation_count": res["physical_evaluation_count"],
        "evaluation_ledger_nonce_total": res["evaluation_ledger_nonce_total"],
        "recomputed_ledger_nonce_total": ledger_total,
        "physical_evaluation_ledger_residual": res["physical_evaluation_ledger_residual"],
        "post_round_evaluation_count": len(run.evaluation_ledger),
        # ---------------- S5C-1 record-derived identity / split accounting ----------------
        "entity_reconciliation_rows": ent_rows,
        "subassignment_record_count": res["subassignment_count"],
        "virtual_identity_record_count": res["virtual_identity_count"],
        "requested_assignment_split_count": int(config.adversarial.assignment_split_count),
        "requested_sybil_identity_count": int(config.adversarial.sybil_identity_count),
        "assignment_split_amplification_ratio": res["assignment_split_amplification_ratio"],
        "identity_multiplication_amplification_ratio":
            res["identity_multiplication_amplification_ratio"],
        "naive_identity_reward_total": res["naive_identity_reward_total"],
        "deduplicated_entity_reward_total": res["deduplicated_entity_reward_total"],
        # ---------------- retained Stage-5A/5B measurements ----------------
        "unique_rewarded_nonce_count": res["unique_rewarded_nonce_count"],
        "duplicate_work_reward_prevented_count": res["duplicate_work_reward_prevented_count"],
        "work_reward_union_residual": res["work_reward_union_residual"],
        "incentive_reconciliation_residual": res["incentive_reconciliation_residual"],
        "physical_frontier_rewind_count": res["physical_frontier_rewind_count"],
        "subassignment_capacity_residual": res["subassignment_capacity_residual"],
        "entity_physical_capacity_residual": res["entity_physical_capacity_residual"],
        "virtual_identity_physical_capacity_granted":
            res["virtual_identity_physical_capacity_granted"],
        "abandonment_penalty_without_action_count":
            res["abandonment_penalty_without_action_count"],
        "coverage_gap_nonce_count": res["coverage_gap_nonce_count"],
        "claim_overstatement_total": res["claim_overstatement_total"],
        "false_exhaustion_attempted": res["false_exhaustion_attempted"],
        "false_exhaustion_detected": res["false_exhaustion_detected"],
        "false_exhaustion_accepted": res["false_exhaustion_accepted"],
        "actions_rejected_over_limit": res["actions_rejected_over_limit"],
    }


def _ownership_probe():
    """S5C-4 measured directly: the interval-exact reconciliation for the canonical example."""
    run = RunInitialise(cfg(adversarial=attacker(("PROGRESS_WITHHOLDER",), klass="BYZANTINE"),
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
    rows = adv.ownership_reconciliation(run)
    by_owner, by_ledger = {}, {}
    for r in rows:
        by_owner[str(r["reward_owner"])] = by_owner.get(str(r["reward_owner"]), 0) + \
            r["rewarded_count"]
    for e in run.incentive_ledger:
        if e.component == "WORK_REWARD":
            by_ledger[str(e.MinerID)] = by_ledger.get(str(e.MinerID), 0.0) + e.amount
    stats_before = copy.deepcopy(run.adversarial_stats)
    ledger_before = len(run.incentive_ledger)
    adv.finalise_incentives(run, rc, 10.0)               # S5B-2 purity is preserved
    return {
        "scenario": "M000 evaluates [0,80); M001 evaluates [40,100) on one lineage",
        "rows": rows,
        "intervals": [r["nonce_interval"] for r in rows],
        "reward_owner_totals": by_owner,
        "work_reward_ledger_totals": by_ledger,
        "unique_rewarded_nonce_count": run.adversarial_stats["unique_rewarded_nonce_count"],
        "duplicate_nonce_count": run.adversarial_stats["duplicate_work_reward_prevented_count"],
        "work_reward_union_residual": run.adversarial_stats["work_reward_union_residual"],
        "rows_sum_rewarded": sum(r["rewarded_count"] for r in rows),
        "rows_sum_duplicate": sum(r["duplicate_reward_prevented_count"] for r in rows),
        "reconciles_to_ledger": {k: by_ledger.get(k) for k in by_owner} == \
            {k: float(v) for k, v in by_owner.items()},
        "second_finalisation_changed_nothing": (
            run.adversarial_stats == stats_before
            and len(run.incentive_ledger) == ledger_before),
    }


def _false_exhaustion_replay_probe(detect, label):
    """S5C-3 measured directly: the full state delta across an exact claim replay."""
    pol = AdversarialPolicy(enabled=True, entities=(("E1", "BYZANTINE", (M0,), None),),
                            miner_behaviours=((0, M0, ("FALSE_EXHAUSTION_CLAIMER",)),),
                            audit_detection_probability=detect,
                            false_exhaustion_claims_range_end=False,
                            false_exhaustion_claim_offset=10, maximum_actions_per_round=10)
    run = RunInitialise(cfg(adversarial=pol))
    rc = type("RC", (), {"RoundID": "round-1", "TemplateID_committed": "tpl"})()
    run.behaviour_profiles[("round-1", M0)] = MinerBehaviourProfile(
        MinerID=M0, EntityID="E1", RoundID="round-1",
        behaviour_set=("FALSE_EXHAUSTION_CLAIMER",), actual_hash_rate=100.0,
        reported_hash_rate=100.0, work_fraction=1.0, wake_delay_multiplier=1.0,
        solution_release_policy="PROMPT_RELEASE", progress_reporting_policy="HONEST",
        exhaustion_claim_policy="FALSE", assignment_split_count=1,
        identity_group_id="E1", behaviour_generation=0)
    st = MinerSearchState(M0, "A0", 1, 100.0, 0, 100, 21.5, 2.15)
    st.cursor = 25

    def snap():
        return {
            "stats": json.loads(json.dumps(run.adversarial_stats, sort_keys=True, default=str)),
            "adv_actions_this_round": {str(k): v for k, v in run.adv_actions_this_round.items()},
            "progress_claims": [[str(c.ClaimID), c.detected, c.accepted, c.claim_overstatement,
                                 c.actual_unsearched_suffix] for c in run.progress_claims],
            "adversarial_actions": sorted(map(str, run.adversarial_actions)),
            "coverage_gap": {str(k): v for k, v in run.adv_round_coverage_gap.items()},
            "event_queue": len(run.event_queue.queued_event_registry),
            "search_state": [st.cursor, st.completed, str(st.completion_kind)],
        }

    first = adv.maybe_false_exhaustion(run, rc, st, 5.0)
    before = snap()
    second = adv.maybe_false_exhaustion(run, rc, st, 5.0)
    third = adv.maybe_false_exhaustion(run, rc, st, 5.0)
    after = snap()
    delta = {k: [before[k], after[k]] for k in before if before[k] != after[k]}
    return {
        "disposition": label,
        "audit_detection_probability": detect,
        "first_result": first.kind if first is not None else None,
        "replay_result": second.kind if second is not None else None,
        "third_result": third.kind if third is not None else None,
        "replay_returns_the_same_stored_result": (second is first and third is first),
        "state_delta_across_replays": delta,
        "state_pure": delta == {},
        "progress_claim_count": len(run.progress_claims),
        "budget_charged": run.adv_actions_this_round.get("round-1", 0),
    }


def _over_limit_replay_probe():
    """S5C-3: a refused action re-offered under the SAME identity counts one refusal."""
    pol = AdversarialPolicy(enabled=True, entities=(("E1", "BYZANTINE", (M0,), None),),
                            miner_behaviours=((0, M0, ("FALSE_EXHAUSTION_CLAIMER",)),),
                            audit_detection_probability=0.0,
                            false_exhaustion_claims_range_end=False,
                            false_exhaustion_claim_offset=10, maximum_actions_per_round=0)
    run = RunInitialise(cfg(adversarial=pol))
    rc = type("RC", (), {"RoundID": "round-1", "TemplateID_committed": "tpl"})()
    run.behaviour_profiles[("round-1", M0)] = MinerBehaviourProfile(
        MinerID=M0, EntityID="E1", RoundID="round-1",
        behaviour_set=("FALSE_EXHAUSTION_CLAIMER",), actual_hash_rate=100.0,
        reported_hash_rate=100.0, work_fraction=1.0, wake_delay_multiplier=1.0,
        solution_release_policy="PROMPT_RELEASE", progress_reporting_policy="HONEST",
        exhaustion_claim_policy="FALSE", assignment_split_count=1,
        identity_group_id="E1", behaviour_generation=0)
    st = MinerSearchState(M0, "A0", 1, 100.0, 0, 100, 21.5, 2.15)
    st.cursor = 25
    for _ in range(5):
        adv.maybe_false_exhaustion(run, rc, st, 5.0)
    return {
        "offers": 5,
        "actions_rejected_over_limit": run.adversarial_stats["actions_rejected_over_limit"],
        "progress_claims": len(run.progress_claims),
        "budget_consumed": run.adv_actions_this_round.get("round-1", 0),
    }


def main() -> None:
    here = pathlib.Path(__file__).resolve().parent
    (here / "evidence").mkdir(parents=True, exist_ok=True)
    inc = IncentivePolicy(enabled=True, r_work=1.0, r_avail=0.1, r_win=100.0,
                          q_false=7.0, q_invalid=5.0, q_abandon=11.0)
    lease = RangeLeasePolicy(enabled=True, reassignment_wake_latency=1.0,
                             lease_duration=1e18, progress_timeout=1e18)

    scenarios = dict([
        scenario("A_disabled_honest_control",
                 "S5C-2: the honest Stage-5-DISABLED control reports its REAL physical "
                 "evaluation count, reconciling exactly with the immutable evaluation ledger.",
                 cfg(), "o-a"),
        scenario("B_disabled_honest_control_with_leases",
                 "S5C-2: the same equality with range leases ENABLED and Stage 5 disabled.",
                 cfg(range_lease=lease), "o-b"),
        scenario("C_enabled_without_leases",
                 "S5C-2: the same equality with Stage 5 ENABLED and range leases disabled.",
                 cfg(adversarial=attacker(("FREE_RIDER",), free_rider_work_fraction=0.5),
                     incentive=inc), "o-c"),
        scenario("D_enabled_with_leases",
                 "S5C-2: the same equality with Stage 5 ENABLED and range leases enabled.",
                 cfg(adversarial=attacker(("FREE_RIDER",), free_rider_work_fraction=0.5),
                     incentive=inc, range_lease=lease), "o-d"),
        scenario("E_one_miner_three_virtual_identities",
                 "S5C-1: one real miner plus three VirtualIdentityRecords is FOUR represented "
                 "identities — the real miner is itself an identity.",
                 cfg(adversarial=attacker(("ASSIGNMENT_SPLITTER",), sybil_identity_count=3),
                     incentive=inc), "o-e"),
        scenario("F_two_miners_five_virtual_identities",
                 "S5C-1: two real miners plus five VirtualIdentityRecords is SEVEN represented "
                 "identities.",
                 cfg(adversarial=attacker(("ASSIGNMENT_SPLITTER",), miners=(M0, M1),
                                          sybil_identity_count=5),
                     incentive=inc), "o-f"),
        scenario("G_split_request_exceeds_span",
                 "S5C-1: a requested split of 8 over a 3-nonce range creates 3 "
                 "SubAssignmentRecords, and the amplification uses 3 — never the request.",
                 cfg(adversarial=attacker(("ASSIGNMENT_SPLITTER",), assignment_split_count=8),
                     incentive=inc, nonce_domain_size=12, horizon_T=10.0), "o-g"),
        scenario("H_split_and_identities_together",
                 "S5C-1: splitting x4 with three declared identities — both factors come from "
                 "the executed records.",
                 cfg(adversarial=attacker(("ASSIGNMENT_SPLITTER",), assignment_split_count=4,
                                          sybil_identity_count=3),
                     incentive=inc), "o-h"),
        scenario("I_false_exhaustion_offset_claim",
                 "S5C-3 context: an accepted false-exhaustion claim with a configured offset, "
                 "separating claim overstatement from the real unsearched suffix.",
                 cfg(adversarial=attacker(("FALSE_EXHAUSTION_CLAIMER",), miners=MINERS,
                                          klass="BYZANTINE", audit_detection_probability=0.0,
                                          false_exhaustion_claims_range_end=False,
                                          false_exhaustion_claim_offset=10,
                                          maximum_actions_per_round=50),
                     incentive=inc, horizon_T=60.0), "o-i"),
        scenario("J_progress_withholding_reassignment",
                 "S5C-4 context: an undetected under-report creates a real re-evaluated segment "
                 "whose reconciliation must be interval-exact.",
                 cfg(adversarial=attacker(("PROGRESS_WITHHOLDER",), klass="BYZANTINE",
                                          audit_detection_probability=0.0,
                                          progress_withholding_fraction=0.5),
                     incentive=inc, reserve_fraction=0.25, horizon_T=90.0, range_lease=lease,
                     injected_lease_faults=((1, M0, 2.0, "fault"),)), "o-j"),
    ])

    doc = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "stage": "05C",
        "algorithm": "PoCol",
        "energy_saving_mechanism": "the idle policy within PoCol",
        "adversarial_coverage_gap_label": ADVERSARIAL_COVERAGE_GAP_NO_BLOCK,
        "generator": "docs/thesis_revision_v45/stage_05c/generate_stage5c_metrics.py",
        "provenance": "every value below is produced by executing the Stage-5 model",
        "scope": {
            "what_this_is": (
                "Deterministic micro-scenario MEASUREMENTS of bounded modeled adversarial "
                "behaviours running on the accepted Stage-4C PoCol core."),
            "what_this_is_not": (
                "NOT the confirmatory experiment matrix, NOT a statistical result, and NOT "
                "evidence of incentive compatibility, fairness, Sybil resistance, "
                "selfish-mining resistance, coalition resistance, common-prefix security, "
                "chain-quality security or Bitcoin/PoW-equivalent security.  The record-derived "
                "identity accounting is an EXPLORATORY SENSITIVITY model of how a naive scheme "
                "could be inflated; it is never presented as Sybil resistance."),
            "fixed_target": (
                "No Stage-5 parameter changes the fixed SHA-256 target or difficulty; dynamic "
                "difficulty remains excluded."),
            "security_floor": "operational active-capacity floor only",
            "nonce_partitioning": (
                "Nonce-domain partitioning alone is NOT an energy-saving mechanism and is never "
                "described as one."),
        },
        "scenarios": scenarios,
        "ownership_reconciliation_S5C_4": _ownership_probe(),
        "false_exhaustion_replay_S5C_3": [
            _false_exhaustion_replay_probe(1.0, "detected_and_rejected"),
            _false_exhaustion_replay_probe(0.0, "undetected_and_accepted"),
        ],
        "over_limit_replay_S5C_3": _over_limit_replay_probe(),
    }

    own = doc["ownership_reconciliation_S5C_4"]
    replays = doc["false_exhaustion_replay_S5C_3"]
    doc["invariants"] = {
        # ---- retained Stage-5A / 5B acceptance invariants ----
        "physical_frontier_never_rewinds": all(
            v["physical_frontier_rewind_count"] == 0 for v in scenarios.values()),
        "work_reward_union_residual_max": max(
            v["work_reward_union_residual"] for v in scenarios.values()),
        "incentive_reconciliation_residual_max": max(
            v["incentive_reconciliation_residual"] for v in scenarios.values()),
        "subassignment_capacity_residual_max": max(
            v["subassignment_capacity_residual"] for v in scenarios.values()),
        "entity_physical_capacity_residual_max": max(
            v["entity_physical_capacity_residual"] for v in scenarios.values()),
        "identities_grant_no_physical_capacity": all(
            v["virtual_identity_physical_capacity_granted"] == 0.0 for v in scenarios.values()),
        "no_abandonment_penalty_without_action": all(
            v["abandonment_penalty_without_action_count"] == 0 for v in scenarios.values()),
        "residency_reconciles_in_every_scenario": all(
            v["residency_reconciles"] for v in scenarios.values()),
        # ---- S5C-1 record-derived accounting ----
        "S5C_1_identity_ratio_equals_real_plus_virtual_records": all(
            all(r["identity_amplification_ratio"]
                == float(max(1, r["real_miner_count"] + r["virtual_identity_record_count"]))
                for r in v["entity_reconciliation_rows"]) for v in scenarios.values()),
        "S5C_1_split_ratio_never_exceeds_created_records": all(
            all(r["actual_split_units"] <= max(1, r["subassignment_record_count"])
                for r in v["entity_reconciliation_rows"]) for v in scenarios.values()),
        "S5C_1_request_never_overrides_records": (
            scenarios["G_split_request_exceeds_span"]["requested_assignment_split_count"] == 8
            and scenarios["G_split_request_exceeds_span"][
                "assignment_split_amplification_ratio"] == 3.0),
        "S5C_1_one_real_plus_three_virtual_is_four": (
            scenarios["E_one_miner_three_virtual_identities"][
                "identity_multiplication_amplification_ratio"] == 4.0),
        "S5C_1_two_real_plus_five_virtual_is_seven": (
            scenarios["F_two_miners_five_virtual_identities"][
                "identity_multiplication_amplification_ratio"] == 7.0),
        "S5C_1_naive_reconstructed_from_record_derived_counts": all(
            all(abs(r["naive_identity_reward"]
                    - r["unique_physical_work_reward"] * r["split_amplification_ratio"]
                    * r["identity_amplification_ratio"]) < 1e-9
                for r in v["entity_reconciliation_rows"]) for v in scenarios.values()),
        # ---- S5C-2 global ledger-derived physical count ----
        "S5C_2_physical_count_equals_ledger_in_every_scenario": all(
            v["physical_evaluation_count"] == v["evaluation_ledger_nonce_total"]
            == v["recomputed_ledger_nonce_total"] for v in scenarios.values()),
        "S5C_2_residual_zero_in_every_scenario": all(
            v["physical_evaluation_ledger_residual"] == 0 for v in scenarios.values()),
        # NOTE: no behaviour_profile_count exemption — the DISABLED control must satisfy this too.
        "S5C_2_no_zero_physical_count_beside_a_non_empty_ledger": all(
            v["physical_evaluation_count"] > 0 for v in scenarios.values()
            if v["evaluation_ledger_entries"] > 0),
        "S5C_2_disabled_control_reports_real_physical_count": (
            scenarios["A_disabled_honest_control"]["adversarial_model_enabled"] is False
            and scenarios["A_disabled_honest_control"]["physical_evaluation_count"] > 0
            and scenarios["A_disabled_honest_control"]["physical_evaluation_ledger_residual"] == 0),
        "S5C_2_disabled_control_has_no_adversarial_effect": (
            scenarios["A_disabled_honest_control"]["false_exhaustion_attempted"] == 0
            and scenarios["A_disabled_honest_control"]["coverage_gap_nonce_count"] == 0
            and scenarios["A_disabled_honest_control"]["subassignment_record_count"] == 0
            and scenarios["A_disabled_honest_control"]["virtual_identity_record_count"] == 0),
        # ---- S5C-3 state-pure false-exhaustion replay ----
        "S5C_3_replay_state_pure_for_both_dispositions": all(
            r["state_pure"] for r in replays),
        "S5C_3_replay_returns_the_same_stored_result": all(
            r["replay_returns_the_same_stored_result"] for r in replays),
        "S5C_3_one_progress_claim_per_action_identity": all(
            r["progress_claim_count"] == 1 for r in replays),
        "S5C_3_over_limit_rejection_counted_once": (
            doc["over_limit_replay_S5C_3"]["actions_rejected_over_limit"] == 1
            and doc["over_limit_replay_S5C_3"]["progress_claims"] == 0),
        # ---- S5C-4 interval-exact ownership reconciliation ----
        "S5C_4_intervals_are_exact": own["intervals"] == [[0, 40], [40, 80], [80, 100]],
        "S5C_4_no_raw_duplicate_interval": [40, 100] not in own["intervals"],
        "S5C_4_rows_reconcile_to_metrics": (
            own["rows_sum_rewarded"] == own["unique_rewarded_nonce_count"] == 100
            and own["rows_sum_duplicate"] == own["duplicate_nonce_count"] == 40),
        "S5C_4_owner_totals_match_the_reward_ledger": (
            own["reward_owner_totals"] == {"M000": 80, "M001": 20}
            and own["work_reward_ledger_totals"] == {"M000": 80.0, "M001": 20.0}),
        "S5C_4_second_finalisation_changed_nothing":
            own["second_finalisation_changed_nothing"],
    }

    for out in (here / "STAGE_05C_METRICS.json",
                here / "evidence" / "stage5c_metrics.json"):
        out.write_text(json.dumps(doc, indent=2, sort_keys=True, default=str) + "\n")
        print("wrote", out.relative_to(ROOT))


if __name__ == "__main__":
    main()
