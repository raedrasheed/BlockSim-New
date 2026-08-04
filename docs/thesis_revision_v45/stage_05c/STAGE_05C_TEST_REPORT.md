# Stage 5C — Test Report

**Command:** `python -m pytest tests/thesis_revision_v45 -v`
**Result:** `185 passed`
**Environment:** Python 3.11, pytest 9.1.1
**Raw evidence:** `evidence/pytest_stage5c.log`, `evidence/pytest_stage5c.junit.xml`

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
| `test_stage5b_ownership_pathb_wake_coverage.py` | 14 | pass |
| **`test_stage5c_record_derived_accounting.py`** | **9** | **pass** |
| **Total** | **185** | **0 failed, 0 skipped, 0 xfailed** |

176 tests were retained from Stage 5B and 9 added (S5C-01 … S5C-07, with S5C-06 parametrised
over both dispositions plus one companion). No test is skipped, marked xfail or conditionally
collected.

## New Stage-5C tests

| Test | Requirement | Key measured figures |
|---|---|---|
| `test_s5c_01_one_real_miner_plus_three_virtual_records_is_four_represented_identities` | S5C-1 | real 1, virtual 3, total **4**, identity ratio **4.0** |
| `test_s5c_02_two_real_miners_plus_five_virtual_records_is_seven_represented_identities` | S5C-1 | real 2, virtual 5, total **7**, identity ratio **7.0** |
| `test_s5c_03_a_split_request_larger_than_the_span_uses_the_records_actually_created` | S5C-1 | requested 8, span 3, records **3**, split ratio **3.0** |
| `test_s5c_04_the_disabled_honest_control_reports_its_real_physical_evaluation_count` | S5C-2 | physical **5,975** = ledger 5,975, residual **0**, zero adversarial effect |
| `test_s5c_05_the_ledger_equality_holds_enabled_and_with_leases_on_and_off` | S5C-2 | four executions, all equal, all residual 0 |
| `test_s5c_06_...[detected]` | S5C-3 | first `None`, replay `None`, full snapshot delta **{}** |
| `test_s5c_06_...[accepted]` | S5C-3 | first/replay/third all `false_exhaustion_accepted` (same object), delta **{}** |
| `test_s5c_06b_replaying_an_over_limit_rejection_counts_one_refusal_per_identity` | S5C-3 | 5 offers → **1** rejection, 0 claims, 0 budget |
| `test_s5c_07_the_ownership_reconciliation_is_split_into_exact_subintervals` | S5C-4 | `[0,40)`, `[40,80)`, `[80,100)`; 100 / 40; ledger `{M000: 80, M001: 20}` |

## Executed-evidence invariants

Produced by `generate_stage5c_metrics.py` across 10 executed micro-scenarios plus three direct
probes:

| Invariant | Value |
|---|---|
| `physical_frontier_never_rewinds` | true |
| `work_reward_union_residual_max` | 0.0 |
| `incentive_reconciliation_residual_max` | 0.0 |
| `subassignment_capacity_residual_max` | 0.0 |
| `entity_physical_capacity_residual_max` | 0.0 |
| `identities_grant_no_physical_capacity` | true |
| `no_abandonment_penalty_without_action` | true |
| `residency_reconciles_in_every_scenario` | true |
| `S5C_1_identity_ratio_equals_real_plus_virtual_records` | true |
| `S5C_1_split_ratio_never_exceeds_created_records` | true |
| `S5C_1_request_never_overrides_records` | true |
| `S5C_1_one_real_plus_three_virtual_is_four` | true |
| `S5C_1_two_real_plus_five_virtual_is_seven` | true |
| `S5C_1_naive_reconstructed_from_record_derived_counts` | true |
| `S5C_2_physical_count_equals_ledger_in_every_scenario` | true |
| `S5C_2_residual_zero_in_every_scenario` | true |
| `S5C_2_no_zero_physical_count_beside_a_non_empty_ledger` | true (**no exemption**) |
| `S5C_2_disabled_control_reports_real_physical_count` | true |
| `S5C_2_disabled_control_has_no_adversarial_effect` | true |
| `S5C_3_replay_state_pure_for_both_dispositions` | true |
| `S5C_3_replay_returns_the_same_stored_result` | true |
| `S5C_3_one_progress_claim_per_action_identity` | true |
| `S5C_3_over_limit_rejection_counted_once` | true |
| `S5C_4_intervals_are_exact` | true |
| `S5C_4_no_raw_duplicate_interval` | true |
| `S5C_4_rows_reconcile_to_metrics` | true |
| `S5C_4_owner_totals_match_the_reward_ledger` | true |
| `S5C_4_second_finalisation_changed_nothing` | true |

## Recorded evidence quantities

| Quantity | Where |
|---|---|
| physical evaluations in the disabled honest control | scenario A: **5,975** |
| evaluation-ledger residual in every scenario | 0 in all 10 |
| per-entity real and virtual identity counts | `entity_reconciliation_rows` per scenario |
| actual `SubAssignmentRecord` count | `subassignment_record_count` per scenario |
| record-derived naive and deduplicated rewards | `naive_identity_reward_total`, `deduplicated_entity_reward_total` |
| split and identity amplification ratios | `assignment_split_amplification_ratio`, `identity_multiplication_amplification_ratio` |
| false-exhaustion replay state delta | `false_exhaustion_replay_S5C_3[*].state_delta_across_replays` = `{}` |
| interval-exact ownership reconciliation | `ownership_reconciliation_S5C_4.rows` |
| duplicate nonce count | `ownership_reconciliation_S5C_4.duplicate_nonce_count` = 40 |
| post-round evaluation count | `post_round_evaluation_count` per scenario |
| incentive reconciliation residual | 0.0 in all 10 |

## Scope

These are deterministic micro-scenarios for evidence only. They are **not** the confirmatory
experiment matrix and no statistical claim is derived from them. They establish no security,
fairness, incentive-compatibility or Sybil-resistance property.
