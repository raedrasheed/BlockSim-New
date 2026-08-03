"""Generate the Stage-5A executable-correction evidence metrics from REAL executions.

Every number in STAGE_05A_METRICS.json and stage5a_metrics.json is produced
by running the executable Stage-5 model here — none is hand-written.  The scenarios are small,
deterministic micro-scenarios for evidence only; they are NOT the confirmatory experiment
matrix and no statistical claim is derived from them.

Run:  python docs/thesis_revision_v45/stage_05a/generate_stage5a_metrics.py
"""
from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from Models.PoCol.stage2 import (Stage2Config, run_simulation, AdversarialPolicy,
                                 RangeLeasePolicy,
                                 IncentivePolicy, results_schema, RangeLeasePolicy,
                                 run_matched_adversarial_pair, RESULT_SCHEMA_VERSION,
                                 ADVERSARIAL_COVERAGE_GAP_NO_BLOCK)
from Models.PoCol.stage2 import adversarial_runtime as adv

_HARD = 1 << 300     # unreachable target: the whole domain is searched and no block is found
_TRIVIAL = 1         # target == 2^256 - 1: every nonce is a valid solution
MINERS = ("M000", "M001", "M002", "M003")

_BASE = dict(num_miners=4, reserve_fraction=0.0, nonce_domain_size=400, batch_size=25,
             horizon_T=60.0)


def cfg(adversarial=None, incentive=None, difficulty=_HARD, **kw):
    return Stage2Config(difficulty=difficulty,
                        adversarial=adversarial or AdversarialPolicy(),
                        incentive=incentive or IncentivePolicy(), **{**_BASE, **kw})


def attacker(flags, miners=("M000",), klass="BYZANTINE", **pol):
    return AdversarialPolicy(enabled=True,
                             entities=(("E1", klass, tuple(miners), None),),
                             miner_behaviours=tuple((0, m, tuple(flags)) for m in miners),
                             **pol)


def scenario(name, description, config, run_id):
    run = run_simulation(config, run_id=run_id)
    res = results_schema(run, config)
    reasons = sorted({o.data.get("reason") for o in run.log if o.kind == "round_aborted"})
    return name, {
        "description": description,
        "rounds_executed": res["rounds_executed"],
        "rounds_accepted": res["rounds_accepted"],
        "rounds_no_block": res["rounds_no_block"],
        "no_block_dispositions": reasons,
        "energy_kwh": res["energy_kwh"],
        "residency_reconciles": res["residency_reconciles"],
        "evaluation_ledger_entries": res["evaluation_ledger_entries"],
        "adversarial_model_enabled": res["adversarial_model_enabled"],
        "incentive_model_enabled": res["incentive_model_enabled"],
        "behaviour_profile_count": res["behaviour_profile_count"],
        "free_rider_count": res["free_rider_count"],
        "hash_rate_misreport_count": res["hash_rate_misreport_count"],
        "allocation_distortion_max_ratio": res["allocation_distortion_max_ratio"],
        "false_exhaustion_attempted": res["false_exhaustion_attempted"],
        "false_exhaustion_detected": res["false_exhaustion_detected"],
        "false_exhaustion_accepted": res["false_exhaustion_accepted"],
        "coverage_gap_nonce_count": res["coverage_gap_nonce_count"],
        "adversarial_coverage_gap_round_count": res["adversarial_coverage_gap_round_count"],
        "solution_withholding_count": res["solution_withholding_count"],
        "withheld_released_count": res["withheld_released_count"],
        "withheld_never_released_count": res["withheld_never_released_count"],
        "withheld_release_too_late_count": res["withheld_release_too_late_count"],
        "withheld_total_hidden_duration": res["withheld_total_hidden_duration"],
        "delayed_wake_count": res["delayed_wake_count"],
        "out_of_range_attempt_count": res["out_of_range_attempt_count"],
        "invalid_action_rejection_count": res["invalid_action_rejection_count"],
        "progress_claim_count": res["progress_claim_count"],
        "actual_reported_divergence_count": res["actual_reported_divergence_count"],
        "reported_accepted_divergence_count": res["reported_accepted_divergence_count"],
        "maximum_q_adv": res["maximum_q_adv"],
        "time_weighted_q_adv": res["time_weighted_q_adv"],
        "q_adv_active_duration": res["q_adv_active_duration"],
        "q_adv_na_duration": res["q_adv_na_duration"],
        "duration_above_q_adv_threshold": res["duration_above_q_adv_threshold"],
        "incentive_ledger_entries": res["incentive_ledger_entries"],
        "incentive_reward_total": res["incentive_reward_total"],
        "incentive_penalty_total": res["incentive_penalty_total"],
        "incentive_net_total": res["incentive_net_total"],
        "incentive_reconciliation_residual": res["incentive_reconciliation_residual"],
        "naive_identity_reward_total": res["naive_identity_reward_total"],
        "deduplicated_entity_reward_total": res["deduplicated_entity_reward_total"],
        "work_reward_total": res["work_reward_total"],
        "winner_reward_total": res["winner_reward_total"],
        "invalid_message_penalty_total": res["invalid_message_penalty_total"],
        "false_claim_penalty_total": res["false_claim_penalty_total"],
        "abandonment_penalty_total": res["abandonment_penalty_total"],
        # ---------------- Stage-5A executable corrections ----------------
        "accepted_frontier_record_count": res["accepted_frontier_record_count"],
        "accepted_below_actual_count": res["accepted_below_actual_count"],
        "physical_frontier_rewind_count": res["physical_frontier_rewind_count"],
        "unique_rewarded_nonce_count": res["unique_rewarded_nonce_count"],
        "physical_evaluation_count": res["physical_evaluation_count"],
        "adversarial_reevaluation_count": res["adversarial_reevaluation_count"],
        "duplicate_work_reward_prevented_count": res["duplicate_work_reward_prevented_count"],
        "work_reward_union_residual": res["work_reward_union_residual"],
        "reported_rate_allocation_rounds": res["reported_rate_allocation_rounds"],
        "allocation_range_size_distortion_max_ratio":
            res["allocation_range_size_distortion_max_ratio"],
        "subassignment_count": res["subassignment_count"],
        "virtual_identity_count": res["virtual_identity_count"],
        "subassignment_capacity_residual": res["subassignment_capacity_residual"],
        "abandonment_action_count": res["abandonment_action_count"],
        "abandoned_nonce_count": res["abandoned_nonce_count"],
        "abandonment_penalty_without_action_count":
            res["abandonment_penalty_without_action_count"],
        "delayed_wake_below_floor_overlap_total":
            res["delayed_wake_below_floor_overlap_total"],
        "attack_induced_floor_breach_duration": res["attack_induced_floor_breach_duration"],
        "actions_rejected_over_limit": res["actions_rejected_over_limit"],
        "withheld_alternative_solution_won_count":
            res["withheld_alternative_solution_won_count"],
        "frontier_reconciliation": res["frontier_reconciliation"],
    }


def main() -> None:
    here = pathlib.Path(__file__).parent
    inc_full = IncentivePolicy(enabled=True, r_work=1.0, r_avail=0.1, r_win=100.0,
                               q_false=7.0, q_invalid=5.0, q_abandon=11.0)
    scenarios = dict([
        scenario("A_honest_baseline_disabled",
                 "All Stage-5 features DISABLED: the frozen Stage-4C behaviour, unchanged.",
                 cfg(), "m-a"),
        scenario("B_honest_with_incentives",
                 "Honest miners, incentive layer ON: the reward baseline for every comparison.",
                 cfg(incentive=inc_full, difficulty=_TRIVIAL, horizon_T=30.0), "m-b"),
        scenario("C_free_rider",
                 "One RATIONAL FREE_RIDER at work_fraction 0.5: the physical rate really drops.",
                 cfg(adversarial=attacker(("FREE_RIDER",), klass="RATIONAL",
                                          free_rider_work_fraction=0.5),
                     incentive=inc_full), "m-c"),
        scenario("D_hash_rate_misreporter",
                 "One RATIONAL HASH_RATE_MISREPORTER at 3x: reported diverges, physical does not.",
                 cfg(adversarial=attacker(("HASH_RATE_MISREPORTER",), klass="RATIONAL",
                                          reported_hash_rate_multiplier=3.0),
                     incentive=inc_full), "m-d"),
        scenario("E_false_exhaustion_detected",
                 "FALSE_EXHAUSTION_CLAIMER, modeled audit p=1.0: every claim caught and rejected.",
                 cfg(adversarial=attacker(("FALSE_EXHAUSTION_CLAIMER",),
                                          audit_detection_probability=1.0),
                     incentive=inc_full), "m-e"),
        scenario("F_false_exhaustion_undetected",
                 "FALSE_EXHAUSTION_CLAIMER, modeled audit p=0.0: an accepted coverage gap.",
                 cfg(adversarial=attacker(("FALSE_EXHAUSTION_CLAIMER",),
                                          audit_detection_probability=0.0),
                     incentive=inc_full), "m-f"),
        scenario("G_solution_withholding_never",
                 "All four miners SOLUTION_WITHHOLDER / NEVER_RELEASE: no block is ever accepted.",
                 cfg(difficulty=_TRIVIAL, horizon_T=30.0, incentive=inc_full,
                     adversarial=attacker(("SOLUTION_WITHHOLDER",), miners=MINERS,
                                          solution_release_policy="NEVER_RELEASE")), "m-g"),
        scenario("H_solution_withholding_delayed",
                 "All four SOLUTION_WITHHOLDER / DELAYED_RELEASE 2.0s: released and re-accepted.",
                 cfg(difficulty=_TRIVIAL, horizon_T=30.0, incentive=inc_full,
                     adversarial=attacker(("SOLUTION_WITHHOLDER",), miners=MINERS,
                                          solution_release_policy="DELAYED_RELEASE",
                                          solution_withholding_delay=2.0)), "m-h"),
        scenario("I_delayed_wake",
                 "DELAYED_WAKE +5.0s: extra WAKING residency, charged at P_wake (a COST).",
                 cfg(adversarial=attacker(("DELAYED_WAKE",), delayed_wake_extra_latency=5.0),
                     incentive=inc_full), "m-i"),
        scenario("J_out_of_range_actor",
                 "OUT_OF_RANGE_ACTOR: every attempt rejected, penalty-eligible, never credited.",
                 cfg(adversarial=attacker(("OUT_OF_RANGE_ACTOR",), out_of_range_nonce_offset=5),
                     incentive=inc_full), "m-j"),
        scenario("K_assignment_split_and_identities",
                 "ASSIGNMENT_SPLITTER x4 with 3 declared identities: dedup vs naive accounting.",
                 cfg(adversarial=attacker(("ASSIGNMENT_SPLITTER",), klass="RATIONAL",
                                          assignment_split_count=4, sybil_identity_count=3),
                     incentive=inc_full), "m-k"),
        scenario("L_all_adversarial_q_adv_one",
                 "Every miner BYZANTINE: q_adv == 1.0 over every ACTIVE interval, NA elsewhere.",
                 cfg(adversarial=attacker(("FREE_RIDER",), miners=MINERS,
                                          free_rider_work_fraction=1.0),
                     incentive=inc_full), "m-l"),
        scenario("M_progress_withholding_reassignment",
                 "S5A-1/2 END-TO-END: an undetected under-report lowers only the ACCEPTED "
                 "frontier; the physical frontier never rewinds and the re-evaluation earns no "
                 "second work reward.",
                 cfg(adversarial=attacker(("PROGRESS_WITHHOLDER",),
                                          audit_detection_probability=0.0,
                                          progress_withholding_fraction=0.5),
                     incentive=inc_full, reserve_fraction=0.25, horizon_T=90.0,
                     range_lease=RangeLeasePolicy(enabled=True, reassignment_wake_latency=1.0,
                                                  lease_duration=1e18, progress_timeout=1e18),
                     injected_lease_faults=((1, "M000", 2.0, "fault"),)), "m-m"),
        scenario("N_reported_rate_allocation",
                 "S5A-3: reported-rate SIZING changes ranges deterministically; physical hash "
                 "capacity still uses the actual rate.",
                 cfg(adversarial=attacker(("HASH_RATE_MISREPORTER",), klass="RATIONAL",
                                          reported_hash_rate_multiplier=5.0,
                                          coordinator_uses_reported_hash_rate=True),
                     incentive=inc_full), "m-n"),
        scenario("O_executable_split_and_identities",
                 "S5A-4: real subassignments under ONE entity capacity budget plus declared "
                 "virtual identities that grant no physical capacity.",
                 cfg(adversarial=attacker(("ASSIGNMENT_SPLITTER",), klass="RATIONAL",
                                          assignment_split_count=4, sybil_identity_count=3),
                     incentive=inc_full), "m-o"),
        scenario("P_executed_abandonment",
                 "S5A-5: an ABANDONMENT_PENALTY is charged strictly against an EXECUTED "
                 "abandonment action.",
                 cfg(adversarial=attacker(("IDLE_POLICY_DEFECTOR",)),
                     incentive=inc_full), "m-p"),
    ])

    base_map = dict(num_miners=4, nonce_domain_size=400, difficulty=_TRIVIAL, horizon_T=30.0,
                    batch_size=25, reserve_fraction=0.0)
    pair = run_matched_adversarial_pair(base_map, {
        "adversarial_enabled": True, "solution_release_policy": "NEVER_RELEASE",
        "adversarial_entities": [("E1", "BYZANTINE", MINERS, None)],
        "miner_behaviours": [(0, m, ("SOLUTION_WITHHOLDER",)) for m in MINERS]},
        run_id="metrics-pair")

    doc = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "stage": "05A",
        "algorithm": "PoCol",
        "energy_saving_mechanism": "the idle policy within PoCol",
        "adversarial_coverage_gap_label": ADVERSARIAL_COVERAGE_GAP_NO_BLOCK,
        "generator": "docs/thesis_revision_v45/stage_05a/generate_stage5a_metrics.py",
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
        "matched_pair_S5_13": {
            "baseline_rounds_accepted": pair["baseline"]["rounds_accepted"],
            "attacked_rounds_accepted": pair["attacked"]["rounds_accepted"],
            "identical_target_and_difficulty": pair["identical_target_and_difficulty"],
            "difficulty": pair["difficulty"],
            "nonce_domain_size": pair["nonce_domain_size"],
            "delta": pair["delta"],
            "interpretation_scope": pair["interpretation_scope"],
        },
    }

    # cross-scenario invariants that must hold in EVERY measured scenario.
    doc["invariants"] = {
        # ---- Stage-5A acceptance invariants ----
        "physical_frontier_never_rewinds": all(
            v["physical_frontier_rewind_count"] == 0 for v in scenarios.values()),
        "work_reward_union_residual_max": max(
            v["work_reward_union_residual"] for v in scenarios.values()),
        "subassignment_capacity_residual_max": max(
            v["subassignment_capacity_residual"] for v in scenarios.values()),
        "no_abandonment_penalty_without_action": all(
            v["abandonment_penalty_without_action_count"] == 0 for v in scenarios.values()),
        "duplicate_work_rewards_prevented_total": sum(
            v["duplicate_work_reward_prevented_count"] for v in scenarios.values()),
        "incentive_reconciliation_residual_max": max(
            s["incentive_reconciliation_residual"] for s in scenarios.values()),
        "residency_reconciles_in_every_scenario": all(
            s["residency_reconciles"] for s in scenarios.values()),
        "no_full_domain_exhaustion_label_in_any_gapped_scenario": all(
            "FULL_DOMAIN_EXHAUSTED_NO_BLOCK" not in s["no_block_dispositions"]
            for s in scenarios.values()
            if s["coverage_gap_nonce_count"] > 0 or s["solution_withholding_count"] > 0),
        "q_adv_never_fabricated_when_inactive": all(
            (s["maximum_q_adv"] is None) or (s["q_adv_active_duration"] > 0)
            for s in scenarios.values()),
        "disabled_baseline_has_zero_stage5_effect": (
            scenarios["A_honest_baseline_disabled"]["behaviour_profile_count"] == 0
            and scenarios["A_honest_baseline_disabled"]["incentive_ledger_entries"] == 0
            and scenarios["A_honest_baseline_disabled"]["maximum_q_adv"] is None),
    }

    for out in (here / "STAGE_05A_METRICS.json",
                here / "evidence" / "stage5a_metrics.json"):
        out.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n")
        print("wrote", out.relative_to(ROOT))


if __name__ == "__main__":
    main()
