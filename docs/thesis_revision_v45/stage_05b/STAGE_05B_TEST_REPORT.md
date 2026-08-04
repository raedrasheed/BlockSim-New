# Stage 5B — Test Report

**Command:** `python -m pytest tests/thesis_revision_v45 -v`
**Result:** `176 passed`
**Environment:** Python 3.11, pytest 9.1.1
**Raw evidence:** `evidence/pytest_stage5b.log`, `evidence/pytest_stage5b.junit.xml`

## Totals

| File | Tests | Result |
|---|---:|---|
| `test_stage2_adapter.py` | 4 | pass |
| `test_stage2_e2e.py` | 5 | pass |
| `test_stage2_scientific.py` | 14 | pass |
| `test_stage2_semantic_vectors.py` | 14 | pass |
| `test_stage3_security_floor.py` | 31 | pass |
| `test_stage4_range_leases.py` | 21 | pass |
| `test_stage4a_lease_lifecycle.py` | 14 | pass |
| `test_stage4b_terminal_pathb_replay_energy.py` | 12 | pass |
| `test_stage4c_exact_energy_links_deadline.py` | 9 | pass |
| `test_stage5_adversarial_incentive.py` | 26 | pass |
| `test_stage5a_frontier_reward_behaviour.py` | 12 | pass |
| **`test_stage5b_ownership_pathb_wake_coverage.py`** | **14** | **pass** |
| **Total** | **176** | **0 failed, 0 skipped, 0 xfailed** |

162 tests were retained from Stage 5A and 14 added. No test is skipped, marked xfail or
conditionally collected.

## New Stage-5B tests

| Test | Requirement | Key measured figures |
|---|---|---|
| `test_s5b_01_unique_suffix_work_belongs_to_the_reassignee_predecessor_keeps_its_own` | S5B-1 | M000 = 80, M001 = 20, total = 100, duplicate prevented = 40 |
| `test_s5b_01b_both_accounting_views_use_the_same_ownership_map` | S5B-1 | dedup entity total = 100.0 |
| `test_s5b_02_second_finalisation_changes_neither_the_ledger_nor_any_derived_metric` | S5B-2 | ledger and full stats dict identical across 2nd and 3rd calls |
| `test_s5b_03_a_true_path_b_reserve_reassignment_applies_accepted_frontier_separation` | S5B-3 | accepted 13 < actual 25, re-eval [13,25), rewind count 0 |
| `test_s5b_04_initial_reserve_path_a_and_path_b_wakes_all_consult_delayed_wake_policy` | S5B-4 | all four lifecycle counters > 0; unspecified = 0; unattributed = 0 |
| `test_s5b_04b_exact_wake_replay_returns_the_same_action_and_consumes_no_budget` | S5B-4 | replay returns 5.0, generation unchanged, budget unchanged |
| `test_s5b_05_a_real_delayed_wake_triggers_another_reserve_activation` | S5B-4 | `another_reserve_activated` true, backed by a real seating of a different miner |
| `test_s5b_06_a_wake_cancelled_before_its_delay_ends_charges_only_the_realised_delay` | S5B-4 | configured 50.0 s → realised 19.0 s; energy = `P_wake × 19.0` |
| `test_s5b_07_a_zero_action_budget_blocks_every_action_type_and_replay_costs_nothing` | S5B-5 | 0-budget blocks withholding, out-of-range and delayed wake; replay costs 0 |
| `test_s5b_08_free_riding_at_one_half_and_splitting_four_ways_conserves_effective_capacity` | S5B-6 | 4 × 12.5 = 50.0 (not 100); misreporter case = 100.0 |
| `test_s5b_09_subassignment_and_identity_accounting_derive_from_records_without_extra_work` | S5B-6 | mapped == ledger total; identical throughput to the unsplit control; multi-miner entity 300.0 |
| `test_s5b_10_abandoning_seventy_five_nonces_records_a_gap_and_forbids_ordinary_exhaustion` | S5B-7 | gap = 75; closure `ROUND_CLOSED_WITH_ADVERSARIAL_COVERAGE_GAP`; floor re-evaluated |
| `test_s5b_11_a_false_claim_separates_overstatement_from_the_real_unsearched_suffix` | S5B-7 | overstatement 10, suffix 75, gap 75 |
| `test_s5b_12_adapter_exposes_the_range_end_flag_and_reconciles_the_physical_count` | S5B-8 | offset 10 → reported 35 through all three entry points; residual 0 with leases on and off; floor + allocation compose |

## Executed-evidence invariants

Produced by `generate_stage5b_metrics.py` across 16 executed micro-scenarios:

| Invariant | Value |
|---|---|
| `physical_frontier_never_rewinds` | true |
| `work_reward_union_residual_max` | 0.0 |
| `incentive_reconciliation_residual_max` | 0.0 |
| `residency_reconciles_in_every_scenario` | true |
| `S5B_1_every_rewarded_position_has_an_owner` | true |
| `S5B_1_duplicate_prevented_matches_reconciliation` | true |
| `S5B_2_second_finalisation_changes_nothing` | true |
| `S5B_3_true_path_b_scenario_count` | 2 |
| `S5B_4_wake_lifecycles_covered` | all four |
| `S5B_4_no_unattributed_or_unspecified_wake` | true |
| `S5B_4_another_reserve_activated_total` | 20 |
| `S5B_5_zero_budget_scenario_has_no_action_effect` | true |
| `S5B_6_entity_physical_capacity_residual_max` | 0.0 |
| `S5B_6_unmapped_evaluation_total` | 0 |
| `S5B_6_identities_grant_no_physical_capacity` | true |
| `S5B_7_no_gapped_round_closes_as_exhaustion` | true |
| `S5B_7_abandonment_never_reports_a_zero_gap` | true |
| `S5B_8_physical_count_matches_ledger_in_every_scenario` | true |
| `disabled_baseline_has_zero_stage5_effect` | true |

## Scope

These are deterministic micro-scenarios for evidence only. They are **not** the confirmatory
experiment matrix and no statistical claim is derived from them. They establish no security,
fairness, incentive-compatibility or Sybil-resistance property.
