#!/usr/bin/env python3
"""Stage 6 — outcome dictionary and machine-readable IP-hypothesis specification.

Emits:
    docs/thesis_revision_v45/stage_06/STAGE_06_OUTCOME_DICTIONARY.csv
    docs/thesis_revision_v45/stage_06/STAGE_06_IP_HYPOTHESES.json

EVERY outcome is resolved against the ACCEPTED adapter schema by EXECUTING
``Models.PoCol.stage2.adapter.results_schema`` and checking the name is really there.  A name
that is not a literal schema key must declare an explicit derivation from names that ARE schema
keys, or from named ACCEPTED RunContext state.  No alias is invented; a name that resolves to
nothing fails this generator rather than silently reaching the preregistration.

Usage:
    python experiments/thesis_revision_v45/stage_06/generate_outcome_dictionary.py [--check]
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
for p in (str(REPO_ROOT), str(HERE)):
    if p not in sys.path:
        sys.path.insert(0, p)

import scenarios as S                                     # noqa: E402

DOCS = REPO_ROOT / "docs" / "thesis_revision_v45" / "stage_06"

DICT_FIELDS = ["field_name", "source_file_or_adapter_key", "unit", "type", "valid_range",
               "primary_or_secondary", "hypothesis_ids", "zero_block_behavior", "NA_rule",
               "aggregation_rule", "paired_control_requirement", "interpretation_limit"]

ADAPTER = "Models/PoCol/stage2/adapter.py::results_schema"
LEDGER = "Models/PoCol/stage2/context.py::RunContext.evaluation_ledger + round_terminal_times"
S5D = ("tests/thesis_revision_v45/stage2/test_stage5d_post_round_evidence_integrity.py"
       "::post_round_audit (accepted Stage-5D definition, tolerance 1e-9)")

_RUNLEVEL = "one value per physical run; never averaged over rounds, miners or blocks"
_NO_SEC = ("operational measurement only; establishes no consensus-security, incentive-"
           "compatibility, fairness or Sybil-resistance property")

#: (field, adapter key or derivation, unit, type, range, P/S, hyps, zero-block, NA, agg,
#:  pairing, limit)
OUTCOMES = [
    ("total_energy_kwh", f"{ADAPTER}['energy_kwh']", "kWh", "float", ">= 0", "PRIMARY",
     "IP-H1;IP-H2;IP-H3;IP-H4;IP-H5;IP-H6", "defined (energy is not per-block)", "never NA",
     _RUNLEVEL, "required: matched control under the same master seed",
     "energy of THIS configuration; not an unconditional PoCol energy-reduction claim"),
    ("continuous_all_active_control_kwh",
     f"{ADAPTER}['continuous_all_active_control_kwh']", "kWh", "float", "> 0", "PRIMARY",
     "IP-H1;IP-H5", "defined", "never NA", _RUNLEVEL, "not applicable (accounting reference)",
     "an ACCOUNTING REFERENCE (N x P_hash x T), not a matched CONTROL simulation"),
    ("relative_energy_reduction_percent",
     "DERIVED: 100 * (E_control - E_treatment) / E_control, both from ['energy_kwh'] under the "
     "SAME master seed", "percent", "float", "unbounded", "SECONDARY",
     "IP-H3;IP-H4;IP-H6", "defined", "NA if E_control == 0", _RUNLEVEL,
     "required", "relative to the matched control only, never to an absolute PoW baseline"),
    ("accepted_blocks", f"{ADAPTER}['rounds_accepted']", "count", "int", ">= 0", "SECONDARY",
     "IP-H8", "0 is a real value, retained", "never NA", _RUNLEVEL, "required",
     "service throughput of this configuration only"),
    ("accepted_blocks_per_horizon",
     "DERIVED: ['rounds_accepted'] / horizon_T", "blocks/second", "float", ">= 0", "PRIMARY",
     "IP-H8", "0 is a real value, retained", "never NA (horizon_T > 0 always)", _RUNLEVEL,
     "required", "service throughput only"),
    ("round_duration",
     "DERIVED: consecutive differences of run_ctx.round_terminal_times (strictly increasing), "
     "first round measured from run_start_time", "second", "float", "> 0", "SECONDARY",
     "IP-H8", "defined (rounds exist even with no accepted block)", "NA if no round closed",
     "per-round; summarised to the run by the median", "required",
     "round latency, not block-interval"),
    ("median_round_duration", "DERIVED: median of round_duration within the run", "second",
     "float", "> 0", "PRIMARY", "IP-H8", "defined", "NA if no round closed", _RUNLEVEL,
     "required", "round latency only"),
    ("zero_block_indicator", "DERIVED: 1 if ['rounds_accepted'] == 0 else 0", "indicator",
     "int", "0 or 1", "SECONDARY", "IP-H8", "this IS the zero-block flag", "never NA",
     _RUNLEVEL, "required", "feasibility indicator"),
    ("zero_block_rate", "DERIVED: mean of zero_block_indicator over master seeds within a "
     "condition", "proportion", "float", "0..1", "PRIMARY", "IP-H8", "definitional",
     "never NA", "across master seeds within one condition", "required",
     "condition-level zero-block frequency"),
    ("security_floor_observation_count", f"{ADAPTER}['security_floor_observation_count']",
     "count", "int", ">= 0", "SECONDARY", "IP-H7", "defined", "never NA", _RUNLEVEL,
     "required", _NO_SEC),
    ("breach_count", f"{ADAPTER}['breach_count']", "count", "int", ">= 0", "SECONDARY",
     "IP-H7", "defined", "never NA", _RUNLEVEL, "required", _NO_SEC),
    ("total_duration_below_floor", f"{ADAPTER}['total_duration_below_floor']", "second",
     "float", ">= 0", "PRIMARY", "IP-H7", "defined", "never NA", _RUNLEVEL, "required",
     "operational ACTIVE-CAPACITY availability only; not a consensus-security guarantee"),
    ("maximum_hash_rate_deficit", f"{ADAPTER}['maximum_hash_rate_deficit']", "nonces/second",
     "float", ">= 0", "SECONDARY", "IP-H7", "defined", "NA when the floor is disabled",
     _RUNLEVEL, "required", _NO_SEC),
    ("floor_unattainable_count", f"{ADAPTER}['floor_unattainable_count']", "count", "int",
     ">= 0", "PRIMARY", "IP-H7", "defined", "never NA", _RUNLEVEL, "required",
     "counts observations where no reserve activation could restore the floor"),
    ("reserve_activations_completed", f"{ADAPTER}['reserve_activations_completed']", "count",
     "int", ">= 0", "SECONDARY", "IP-H7", "defined", "never NA", _RUNLEVEL, "required",
     "reserve activation may INCREASE energy; it never saves energy"),
    ("duplicate_nonce_count", f"{ADAPTER}['duplicate_nonce_count']", "count", "int", ">= 0",
     "PRIMARY", "IP-H9", "defined", "never NA", _RUNLEVEL,
     "gate: must be 0 in every honest condition", "deterministic integrity gate, no p-value"),
    ("post_round_evaluation_record_count",
     f"{ADAPTER}['post_round_evaluation_count'] (identical causal computation) cross-checked "
     f"against {S5D}", "count", "int", ">= 0", "PRIMARY", "IP-H9", "defined", "never NA",
     _RUNLEVEL, "gate: must be 0", "deterministic integrity gate, no p-value"),
    ("post_round_evaluation_nonce_count", f"DERIVED via {S5D} over {LEDGER}", "count", "int",
     ">= 0", "PRIMARY", "IP-H9", "defined", "never NA", _RUNLEVEL, "gate: must be 0",
     "deterministic integrity gate, no p-value"),
    ("evaluation_missing_terminal_time_count", f"DERIVED via {S5D} over {LEDGER}", "count",
     "int", ">= 0", "PRIMARY", "IP-H9", "defined", "never NA", _RUNLEVEL, "gate: must be 0",
     "a missing terminal time is NEVER silently treated as valid"),
    ("physical_evaluation_count", f"{ADAPTER}['physical_evaluation_count']", "count", "int",
     ">= 0", "SECONDARY", "IP-H9", "defined", "never NA", _RUNLEVEL, "required",
     "physical truth derived from the immutable evaluation ledger"),
    ("evaluation_ledger_nonce_total", f"{ADAPTER}['evaluation_ledger_nonce_total']", "count",
     "int", ">= 0", "SECONDARY", "IP-H9", "defined", "never NA", _RUNLEVEL, "required",
     "liveness denominator: a zero gate over an empty ledger would be vacuous"),
    ("coverage_gap_nonce_count", f"{ADAPTER}['coverage_gap_nonce_count']", "count", "int",
     ">= 0", "PRIMARY", "IP-H9;IP-H10c", "defined", "never NA", _RUNLEVEL, "required",
     "measures a MODELED coverage gap; establishes no security property"),
    ("physical_frontier_rewind_count", f"{ADAPTER}['physical_frontier_rewind_count']",
     "count", "int", ">= 0", "PRIMARY", "IP-H9;IP-H10d", "defined", "never NA", _RUNLEVEL,
     "gate: must be 0", "the physical committed frontier is monotonic ground truth"),
    ("work_reward_union_residual", f"{ADAPTER}['work_reward_union_residual']", "nonces",
     "float", ">= 0", "PRIMARY", "IP-H9", "defined", "never NA", _RUNLEVEL, "gate: must be 0",
     "unique physical work is rewarded exactly once"),
    ("nonterminal_lease_count", f"{ADAPTER}['nonterminal_lease_count']", "count", "int",
     ">= 0", "PRIMARY", "IP-H9", "defined", "never NA", _RUNLEVEL, "gate: must be 0",
     "lease lifecycle closure"),
    ("nonterminal_reassignment_request_count",
     f"{ADAPTER}['nonterminal_reassignment_request_count']", "count", "int", ">= 0",
     "PRIMARY", "IP-H9", "defined", "never NA", _RUNLEVEL, "gate: must be 0",
     "reassignment lifecycle closure"),
    ("nonterminal_activation_request_count",
     "DERIVED: count of run_ctx.activation_requests whose status is not in "
     "Models/PoCol/stage2/security.py::TERMINAL_REQUEST_STATUSES", "count", "int", ">= 0",
     "PRIMARY", "IP-H7;IP-H9", "defined", "never NA", _RUNLEVEL, "gate: must be 0",
     "reserve-activation lifecycle closure"),
    ("maximum_energy_identity_residual_j",
     "DERIVED: max over miners of |sum_states P(state)*t(state) - miner_energy_joules|",
     "joule", "float", ">= 0", "PRIMARY", "IP-H2", "defined", "never NA", _RUNLEVEL,
     "gate: <= 1e-8 J", "accounting identity, no p-value"),
    ("maximum_residency_partition_residual_s",
     "DERIVED: max over miners of |sum_states t(state) - (run_end_time - run_start_time)|",
     "second", "float", ">= 0", "PRIMARY", "IP-H2", "defined", "never NA", _RUNLEVEL,
     "gate: <= 1e-9 s", "accounting identity, no p-value"),
    ("maximum_q_adv", f"{ADAPTER}['maximum_q_adv']", "proportion", "float or NA", "0..1",
     "SECONDARY", "IP-H10a;IP-H10b;IP-H10c;IP-H10d",
     "defined", "NA when H_active == 0; NEVER imputed and NEVER numerically compared",
     _RUNLEVEL, "required",
     "adversarial capacity share of a MODELED population; not an attack-resistance claim"),
    ("time_weighted_q_adv", f"{ADAPTER}['time_weighted_q_adv']", "proportion", "float or NA",
     "0..1", "SECONDARY", "IP-H10a;IP-H10b;IP-H10c;IP-H10d", "defined",
     "NA when the q_adv-active duration is 0", _RUNLEVEL, "required",
     "not an attack-resistance claim"),
    ("adversarial_reevaluation_count", f"{ADAPTER}['adversarial_reevaluation_count']",
     "count", "int", ">= 0", "PRIMARY", "IP-H10d", "defined", "never NA", _RUNLEVEL,
     "required: matched honest control D00",
     "a BOUNDED experimental effect of a modeled behaviour; NOT evidence of attack resistance"),
    ("duplicate_work_reward_prevented_count",
     f"{ADAPTER}['duplicate_work_reward_prevented_count']", "count", "int", ">= 0",
     "SECONDARY", "IP-H10d", "defined", "never NA", _RUNLEVEL, "required",
     "must be >= adversarial_reevaluation_count"),
    ("delayed_wake_count", f"{ADAPTER}['delayed_wake_count']", "count", "int", ">= 0",
     "PRIMARY", "IP-H10a", "defined", "never NA", _RUNLEVEL, "required",
     "bounded modeled behaviour; not an attack-resistance claim"),
    ("solution_withholding_count", f"{ADAPTER}['solution_withholding_count']", "count", "int",
     ">= 0", "PRIMARY", "IP-H10b", "defined", "never NA", _RUNLEVEL, "required",
     "bounded modeled behaviour; not a selfish-mining-resistance claim"),
    ("false_exhaustion_accepted", f"{ADAPTER}['false_exhaustion_accepted']", "count", "int",
     ">= 0", "PRIMARY", "IP-H10c", "defined", "never NA", _RUNLEVEL, "required",
     "bounded modeled behaviour; the audit is a MODELED abstraction, not a cryptographic proof"),
    ("incentive_reconciliation_residual", f"{ADAPTER}['incentive_reconciliation_residual']",
     "reward units", "float", ">= 0", "SECONDARY", "IP-H9", "defined", "never NA", _RUNLEVEL,
     "gate: must be 0",
     "EXPLORATORY in Stage 7; incentive quantities are never a primary confirmatory endpoint"),
]

#: Every hypothesis field the directive fixes, in order.
HYP_FIELDS = ["hypothesis_id", "scientific_question", "condition_A", "condition_B",
              "primary_outcome", "secondary_outcomes", "estimand", "direction",
              "inferential_unit", "analysis_method", "decision_rule", "multiplicity_family",
              "failure_condition", "interpretation_limit"]

UNIT = "one physical run under one master seed"
PERM = ("one-sided paired sign-permutation over master seeds (10 000 permutations when exact "
        "enumeration is unavailable) plus a 95 % paired cluster bootstrap over master seeds "
        "(10 000 resamples), both driven by the frozen analysis seed")
GATE = "deterministic validation gate — no p-value, no confidence interval"

HYPOTHESES = [
    {
        "hypothesis_id": "IP-H1",
        "scientific_question": "Does the A1 continuous full-participation accounting reference "
                               "reproduce exactly under the frozen reference configuration?",
        "condition_A": "every confirmatory scenario at the reference population and horizon",
        "condition_B": "the declared analytical constant 8.420833333 kWh",
        "primary_outcome": "continuous_all_active_control_kwh",
        "secondary_outcomes": [],
        "estimand": "absolute error |computed - 8.420833333| kWh",
        "direction": "equality",
        "inferential_unit": UNIT,
        "analysis_method": GATE,
        "decision_rule": "PASS iff absolute error <= 1e-9 kWh in every run",
        "multiplicity_family": "NONE (validation gate)",
        "failure_condition": "any run exceeds 1e-9 kWh",
        "interpretation_limit": "an ACCOUNTING validation of the reference, not an energy claim "
                                "and not a matched control simulation",
    },
    {
        "hypothesis_id": "IP-H2",
        "scientific_question": "Is per-miner energy exactly the state-complete sum of residency "
                               "times per-state power, over a complete residency partition?",
        "condition_A": "every confirmatory run",
        "condition_B": "the analytic identity E_i = P_hash*t_hash + P_listen*t_listen + "
                       "P_reserve*t_reserve + P_wake*t_wake + P_offline*t_offline",
        "primary_outcome": "maximum_energy_identity_residual_j",
        "secondary_outcomes": ["maximum_residency_partition_residual_s"],
        "estimand": "maximum absolute residual over miners within a run",
        "direction": "equality",
        "inferential_unit": UNIT,
        "analysis_method": GATE,
        "decision_rule": "PASS iff energy residual <= 1e-8 J AND residency-partition residual "
                         "<= 1e-9 s in every run",
        "multiplicity_family": "NONE (validation gate)",
        "failure_condition": "any run exceeds either tolerance",
        "interpretation_limit": "an accounting identity; it says nothing about whether the idle "
                                "policy saves energy",
    },
    {
        "hypothesis_id": "IP-H3",
        "scientific_question": "Under HOMOGENEOUS hash rates, does lowering the idle-power "
                               "ratio change total energy by more than a negligible margin?",
        "condition_A": "A02 — homogeneous rates, idle-power ratio 0.10",
        "condition_B": "A01 — homogeneous rates, idle-power ratio 1.00 (idle policy off)",
        "primary_outcome": "total_energy_kwh",
        "secondary_outcomes": ["relative_energy_reduction_percent", "accepted_blocks"],
        "estimand": "mean paired difference in total_energy_kwh (A02 - A01) over master seeds",
        "direction": "equivalence (two-sided) within +/- 0.10 % of A1",
        "inferential_unit": UNIT,
        "analysis_method": PERM,
        "decision_rule": "EQUIVALENT iff the COMPLETE 95 % paired bootstrap CI lies inside "
                         "+/- 0.0084208333 kWh (0.10 % of 8.420833333 kWh)",
        "multiplicity_family": "Family 1 (IP-H3, IP-H4, IP-H6 adjacent contrasts), Holm",
        "failure_condition": "any part of the CI falls outside the margin",
        "interpretation_limit": "a homogeneous-population NULL; failing to reject is NEVER "
                                "evidence of equivalence outside the stated margin",
    },
    {
        "hypothesis_id": "IP-H4",
        "scientific_question": "Under HETEROGENEOUS hash rates, does the PoCol idle policy "
                               "reduce total energy relative to the matched idle-policy-off "
                               "control?",
        "condition_A": "A05 — heterogeneous 1x-4x rates, idle-power ratio 0.10",
        "condition_B": "A03 — heterogeneous 1x-4x rates, idle-power ratio 1.00",
        "primary_outcome": "total_energy_kwh",
        "secondary_outcomes": ["relative_energy_reduction_percent", "accepted_blocks",
                               "median_round_duration"],
        "estimand": "mean paired difference (A03 - A05) and mean paired RELATIVE reduction",
        "direction": "one-sided: A05 strictly lower than A03",
        "inferential_unit": UNIT,
        "analysis_method": PERM,
        "decision_rule": "SUCCESS iff Holm-adjusted p < 0.05 AND the lower 95 % CI bound of the "
                         "paired difference > 0 AND the mean relative reduction >= 5 % "
                         "(a PREREGISTERED minimum, not pilot-estimated)",
        "multiplicity_family": "Family 1, Holm",
        "failure_condition": "any of the three conditions fails",
        "interpretation_limit": "a CONDITIONAL reduction under heterogeneous rates in THIS "
                                "configuration; never an unconditional PoCol energy-reduction "
                                "claim. An energy success may be claimed ONLY if IP-H7 and "
                                "IP-H8 both pass.",
    },
    {
        "hypothesis_id": "IP-H5",
        "scientific_question": "With the idle policy switched off, is the saving exactly zero?",
        "condition_A": "A01 and A03 — every non-hashing non-offline state draws P_hash",
        "condition_B": "the A1 continuous full-participation reference",
        "primary_outcome": "total_energy_kwh",
        "secondary_outcomes": ["continuous_all_active_control_kwh"],
        "estimand": "|total_energy_kwh - continuous_all_active_control_kwh| per run",
        "direction": "equality (zero saving)",
        "inferential_unit": UNIT,
        "analysis_method": GATE,
        "decision_rule": "PASS iff the residual is <= 1e-9 kWh for EVERY master seed",
        "multiplicity_family": "NONE (negative control)",
        "failure_condition": "any master seed exceeds 1e-9 kWh",
        "interpretation_limit": "a NEGATIVE CONTROL. Its precondition — zero OFFLINE and zero "
                                "DISQUALIFIED residency — is verified per run and never assumed.",
    },
    {
        "hypothesis_id": "IP-H6",
        "scientific_question": "Is total energy monotone in the idle-power ratio?",
        "condition_A": "A06 (0.00), A05 (0.10), A04 (0.25)",
        "condition_B": "the adjacent higher-ratio row: A05, A04, A03 (1.00) respectively",
        "primary_outcome": "total_energy_kwh",
        "secondary_outcomes": ["relative_energy_reduction_percent"],
        "estimand": "mean paired difference for each ADJACENT contrast",
        "direction": "one-sided, ordering E(0.00) <= E(0.10) <= E(0.25) <= E(1.00)",
        "inferential_unit": UNIT,
        "analysis_method": PERM,
        "decision_rule": "each adjacent contrast SUCCEEDS iff its Holm-adjusted p < 0.05 within "
                         "IP-H6 and its 95 % CI excludes 0 in the predicted direction",
        "multiplicity_family": "Family 1; Holm applied WITHIN IP-H6 across its three adjacent "
                               "contrasts",
        "failure_condition": "any adjacent contrast reverses the predicted ordering",
        "interpretation_limit": "monotonicity only. NO linearity is claimed unless the data "
                                "support it, and the 0.25 -> 1.00 contrast additionally raises "
                                "the transient wake power, because that is what switching the "
                                "idle policy off means.",
    },
    {
        "hypothesis_id": "IP-H7",
        "scientific_question": "Does the operational active-capacity floor hold in honest "
                               "conditions?",
        "condition_A": "B02 / B03 — floor enabled, minimum_active_hash_rate = 0.80 x initial "
                       "active-primary ACTUAL hash rate, MINIMUM_CARDINALITY reserve "
                       "selection, ON_CAPACITY_CHANGE, activation_wake_latency 1.0, "
                       "floor_tolerance 0.0, CONTINUE_DEGRADED",
        "condition_B": "B01 — floor disabled, otherwise identical",
        "primary_outcome": "total_duration_below_floor",
        "secondary_outcomes": ["floor_unattainable_count", "breach_count",
                               "maximum_hash_rate_deficit", "reserve_activations_completed",
                               "nonterminal_activation_request_count"],
        "estimand": "per-run total_duration_below_floor and the two exact counts",
        "direction": "bounded",
        "inferential_unit": UNIT,
        "analysis_method": "exact per-run criteria plus " + PERM + " for the paired contrast",
        "decision_rule": "SUCCESS in honest conditions iff floor_unattainable_count == 0 AND "
                         "nonterminal_activation_request_count == 0 AND "
                         "total_duration_below_floor <= 0.01 * horizon_T",
        "multiplicity_family": "Family 2 (IP-H7, IP-H8), Holm",
        "failure_condition": "any of the three criteria fails",
        "interpretation_limit": "an OPERATIONAL ACTIVE-CAPACITY criterion only. It is not "
                                "consensus security, not common-prefix security, not chain "
                                "quality, and not Bitcoin/PoW-equivalent security. B04 is a "
                                "DIAGNOSTIC row and is excluded from this criterion.",
    },
    {
        "hypothesis_id": "IP-H8",
        "scientific_question": "Is service non-inferior under the conditions where an energy "
                               "claim would be made?",
        "condition_A": "each treatment row",
        "condition_B": "its matched control under the same master seed",
        "primary_outcome": "accepted_blocks_per_horizon",
        "secondary_outcomes": ["median_round_duration", "zero_block_rate", "accepted_blocks"],
        "estimand": "paired ratio of accepted_blocks_per_horizon; paired ratio of "
                    "median_round_duration; absolute difference in zero_block_rate",
        "direction": "non-inferiority",
        "inferential_unit": UNIT,
        "analysis_method": PERM,
        "decision_rule": "NON-INFERIOR iff the accepted_blocks_per_horizon ratio >= 0.95 AND "
                         "the median_round_duration ratio <= 1.05 AND the absolute increase in "
                         "zero_block_rate <= 0.05",
        "multiplicity_family": "Family 2, Holm",
        "failure_condition": "any of the three margins is violated",
        "interpretation_limit": "Zero-block runs are RETAINED; per-block quantities are NA, "
                                "never imputed as zero and never dropped. An ENERGY success may "
                                "be claimed ONLY when IP-H7 and IP-H8 both pass.",
    },
    {
        "hypothesis_id": "IP-H9",
        "scientific_question": "Do the lease, reassignment and evaluation integrity invariants "
                               "hold exactly under every matched robustness condition?",
        "condition_A": "C01 (no fault), C02 (leases disabled), C03 (Path A), C04 (genuine "
                       "Path-B reserve wake), C05 (no eligible miner), C06 (full-domain "
                       "exhaustion), D00 (honest control)",
        "condition_B": "the exact invariant values below",
        "primary_outcome": "duplicate_nonce_count",
        "secondary_outcomes": ["post_round_evaluation_record_count",
                               "post_round_evaluation_nonce_count",
                               "evaluation_missing_terminal_time_count",
                               "nonterminal_lease_count",
                               "nonterminal_reassignment_request_count",
                               "nonterminal_activation_request_count",
                               "physical_frontier_rewind_count",
                               "work_reward_union_residual",
                               "evaluation_ledger_nonce_total"],
        "estimand": "the exact per-run counts",
        "direction": "equality with zero",
        "inferential_unit": UNIT,
        "analysis_method": GATE,
        "decision_rule": "PASS iff duplicate_nonce_count == 0 in every honest condition AND "
                         "post_round_evaluation_record_count == 0 AND "
                         "post_round_evaluation_nonce_count == 0 AND "
                         "evaluation_missing_terminal_time_count == 0 AND "
                         "nonterminal_lease_count == 0 AND "
                         "nonterminal_reassignment_request_count == 0 AND "
                         "nonterminal_activation_request_count == 0 AND "
                         "physical_frontier_rewind_count == 0 AND "
                         "work_reward_union_residual == 0 AND full-domain exhaustion is "
                         "reported only when every suffix is covered; each gate is evaluated "
                         "only over runs with a NON-EMPTY evaluation ledger, so a zero is "
                         "evidence rather than absence of activity",
        "multiplicity_family": "NONE (deterministic gates)",
        "failure_condition": "any invariant is non-zero, or any gate is evaluated over an "
                             "empty ledger",
        "interpretation_limit": "internal consistency of the accepted model; establishes no "
                                "security property",
    },
    {
        "hypothesis_id": "IP-H10a",
        "scientific_question": "What bounded effect does modeled DELAYED WAKE have relative to "
                               "the matched honest control?",
        "condition_A": "D01 — DELAYED_WAKE on the fixed adversarial entity set",
        "condition_B": "D00 — identical configuration, entity set declared with NO behaviour",
        "primary_outcome": "delayed_wake_count",
        "secondary_outcomes": ["total_energy_kwh", "accepted_blocks",
                               "total_duration_below_floor", "maximum_q_adv"],
        "estimand": "mean paired difference vs D00 over master seeds",
        "direction": "two-sided",
        "inferential_unit": UNIT,
        "analysis_method": PERM,
        "decision_rule": "report the effect and its 95 % CI; Holm-adjusted within IP-H10",
        "multiplicity_family": "Family 3 (IP-H10a/b/c/d), Holm",
        "failure_condition": "the behaviour does not occur (count == 0), making the contrast "
                             "vacuous",
        "interpretation_limit": "a BOUNDED EXPERIMENTAL EFFECT of a modeled behaviour. It is "
                                "NOT evidence of attack resistance, incentive compatibility, "
                                "coalition resistance or Sybil resistance.",
    },
    {
        "hypothesis_id": "IP-H10b",
        "scientific_question": "What bounded effect does modeled SOLUTION WITHHOLDING have?",
        "condition_A": "D02 — SOLUTION_WITHHOLDER, NEVER_RELEASE",
        "condition_B": "D00",
        "primary_outcome": "solution_withholding_count",
        "secondary_outcomes": ["accepted_blocks", "accepted_blocks_per_horizon",
                               "total_energy_kwh", "maximum_q_adv"],
        "estimand": "mean paired difference vs D00 over master seeds",
        "direction": "two-sided",
        "inferential_unit": UNIT,
        "analysis_method": PERM,
        "decision_rule": "report the effect and its 95 % CI; Holm-adjusted within IP-H10",
        "multiplicity_family": "Family 3, Holm",
        "failure_condition": "no solution is ever withheld",
        "interpretation_limit": "a bounded modeled effect; NOT a selfish-mining-resistance or "
                                "chain-quality claim",
    },
    {
        "hypothesis_id": "IP-H10c",
        "scientific_question": "What bounded effect does an ACCEPTED FALSE EXHAUSTION claim "
                               "have?",
        "condition_A": "D03 — FALSE_EXHAUSTION_CLAIMER with audit_detection_probability 0.0",
        "condition_B": "D00",
        "primary_outcome": "false_exhaustion_accepted",
        "secondary_outcomes": ["coverage_gap_nonce_count", "accepted_blocks",
                               "total_energy_kwh"],
        "estimand": "mean paired difference vs D00 over master seeds",
        "direction": "two-sided",
        "inferential_unit": UNIT,
        "analysis_method": PERM,
        "decision_rule": "report the effect and its 95 % CI; Holm-adjusted within IP-H10",
        "multiplicity_family": "Family 3, Holm",
        "failure_condition": "no false-exhaustion claim is accepted",
        "interpretation_limit": "the progress-verification layer is a MODELED ABSTRACTION, not "
                                "a complete cryptographic proof; this is not a security claim",
    },
    {
        "hypothesis_id": "IP-H10d",
        "scientific_question": "Under modeled PROGRESS WITHHOLDING, does re-evaluation occur "
                               "while the physical frontier never rewinds and duplicate reward "
                               "is prevented?",
        "condition_A": "D04 (D04_PROGRESS_WITHHOLDING) — PROGRESS_WITHHOLDER, withholding "
                       "fraction 0.5, audit_detection_probability 0.0, batch_size 25",
        "condition_B": "D04C (D04C_PROGRESS_CONTROL) — the SAME adversarial entity set declared "
                       "with NO behaviour, batch_size 25; a dedicated control, NOT the batch-50 "
                       "D00 control",
        "primary_outcome": "adversarial_reevaluation_count",
        "secondary_outcomes": ["physical_frontier_rewind_count",
                               "duplicate_work_reward_prevented_count",
                               "work_reward_union_residual", "total_energy_kwh"],
        "estimand": "mean paired difference vs D00 over master seeds",
        "direction": "one-sided: strictly positive re-evaluation count",
        "inferential_unit": UNIT,
        "analysis_method": PERM,
        "decision_rule": "SUCCESS iff adversarial_reevaluation_count > 0 AND "
                         "physical_frontier_rewind_count == 0 AND "
                         "duplicate_work_reward_prevented_count >= "
                         "adversarial_reevaluation_count",
        "multiplicity_family": "Family 3, Holm",
        "failure_condition": "adversarial_reevaluation_count == 0 (vacuous), or the physical "
                             "frontier rewinds, or duplicate reward is not prevented",
        "interpretation_limit": "a BOUNDED EXPERIMENTAL EFFECT of a modeled behaviour; NOT "
                                "evidence of attack resistance, incentive compatibility, "
                                "coalition resistance or Sybil resistance. The pair carries "
                                "batch_size 25 on BOTH arms because progress withholding "
                                "under-reports the COMMITTED frontier, which requires a batch "
                                "boundary strictly inside a primary range (4000/113 = 35.4 > 25; "
                                "at the reference batch size 50 no intermediate committed "
                                "frontier can exist). Chosen from that structural inequality, "
                                "never from an observed effect.",
    },
]


def accepted_schema_keys() -> set:
    from Models.PoCol.stage2.config import Stage2Config
    from Models.PoCol.stage2.simulator import run_simulation
    from Models.PoCol.stage2.adapter import results_schema
    cfg = Stage2Config(num_miners=4, horizon_T=12.0, nonce_domain_size=80, batch_size=10)
    return set(results_schema(run_simulation(cfg, run_id="dict"), cfg))


def resolve_or_die(keys: set) -> None:
    """Fail loudly if any declared source names a field the accepted schema does not expose."""
    bad = []
    for row in OUTCOMES:
        src = row[1]
        if src.startswith(ADAPTER):
            key = src.split("['")[1].split("']")[0]
            if key not in keys:
                bad.append(f"{row[0]}: adapter key {key!r} is not in results_schema")
        elif not (src.startswith("DERIVED") or src.startswith("Models/")):
            bad.append(f"{row[0]}: unrecognised source {src!r}")
    declared = {r[0] for r in OUTCOMES}
    for h in HYPOTHESES:
        for f in [h["primary_outcome"]] + list(h["secondary_outcomes"]):
            if f not in declared:
                bad.append(f"{h['hypothesis_id']}: outcome {f!r} is not in the dictionary")
    if bad:
        raise SystemExit("STAGE_6_PREREGISTRATION_BLOCKED — unresolved outcome field(s):\n  "
                         + "\n  ".join(bad))


def render() -> tuple:
    buf = io.StringIO(newline="")
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(DICT_FIELDS)
    for row in OUTCOMES:
        w.writerow(row)
    payload = {
        "stage": "STAGE_06",
        "engine_commit_sha": "fb8a34d63d9369336d5c1e7aeecdfcf8263920b2",
        "result_schema_version": "stage5c.1",
        "inferential_unit": UNIT,
        "hypothesis_fields": HYP_FIELDS,
        "hypotheses": HYPOTHESES,
    }
    return (buf.getvalue(), json.dumps(payload, indent=1, sort_keys=True) + "\n",
            render_markdown(payload))


_LABELS = {"scientific_question": "Scientific question", "condition_A": "Condition A",
           "condition_B": "Condition B", "primary_outcome": "Primary outcome",
           "secondary_outcomes": "Secondary outcomes", "estimand": "Estimand",
           "direction": "Direction", "inferential_unit": "Inferential unit",
           "analysis_method": "Analysis method", "decision_rule": "Decision rule",
           "multiplicity_family": "Multiplicity family",
           "failure_condition": "Failure condition",
           "interpretation_limit": "Interpretation limit"}


def render_markdown(payload: dict) -> str:
    """Render the SAME frozen specification as the JSON, so the two can never disagree."""
    out = [
        "# Stage 6 — IP-H1 … IP-H10 Hypothesis Specification (human-readable)",
        "",
        "The machine-readable form is `STAGE_06_IP_HYPOTHESES.json`. Both are generated by",
        "`experiments/thesis_revision_v45/stage_06/generate_outcome_dictionary.py`, which aborts",
        "rather than emit an outcome name that does not resolve against the accepted adapter",
        "schema. Every outcome referenced below is defined in `STAGE_06_OUTCOME_DICTIONARY.csv`.",
        "",
        f"**Engine commit:** `{payload['engine_commit_sha']}`  ",
        f"**Result schema:** `{payload['result_schema_version']}`  ",
        f"**Inferential unit:** {payload['inferential_unit']}",
        "",
        "> **Claim scope.** The algorithm is PoCol; the energy-saving mechanism is the idle",
        "> policy within PoCol; nonce-domain partitioning alone is never an energy-saving",
        "> mechanism; the security floor is an operational active-capacity floor only; the",
        "> progress-verification layer is a modeled abstraction, not a complete cryptographic",
        "> proof. Nothing here claims unconditional energy reduction, incentive compatibility,",
        "> fairness, Sybil resistance, selfish-mining resistance, coalition resistance,",
        "> common-prefix security, chain-quality security, or Bitcoin/PoW-equivalent security.",
        "",
        "**Energy success may be claimed only when IP-H7 and IP-H8 both pass.**",
        "",
        "---",
        "",
    ]
    for h in payload["hypotheses"]:
        out += [f"## {h['hypothesis_id']}", "", "| field | value |", "|---|---|"]
        for k in payload["hypothesis_fields"]:
            if k == "hypothesis_id":
                continue
            v = h[k]
            if isinstance(v, list):
                v = "; ".join(v) if v else "(none)"
            v = str(v).replace("|", "\\|").replace("\n", " ")
            out.append(f"| **{_LABELS[k]}** | {v} |")
        out.append("")
    return "\n".join(out)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args(argv)
    S.assert_reference_matches_baseline()
    keys = accepted_schema_keys()
    resolve_or_die(keys)
    csv_text, json_text, md_text = render()
    targets = {DOCS / "STAGE_06_OUTCOME_DICTIONARY.csv": csv_text,
               DOCS / "STAGE_06_IP_HYPOTHESES.json": json_text,
               DOCS / "STAGE_06_IP_HYPOTHESES.md": md_text}
    if args.check:
        bad = [str(p.relative_to(REPO_ROOT)) for p, t in targets.items()
               if not p.exists() or p.read_bytes() != t.encode("utf-8")]
        if bad:
            print("FAIL: differs from regeneration: " + ", ".join(bad), file=sys.stderr)
            return 1
        print("OK: outcome dictionary and hypothesis spec are byte-identical to regeneration")
    else:
        for p, t in targets.items():
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(t.encode("utf-8"))
        print(f"wrote {len(targets)} artefacts")
    print(f"  outcomes defined      : {len(OUTCOMES)}")
    print(f"  hypotheses defined    : {len(HYPOTHESES)}")
    print(f"  accepted schema keys  : {len(keys)}")
    print(f"  dictionary sha256     : {hashlib.sha256(csv_text.encode()).hexdigest()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
