# STAGE 8Y — VALIDATION REPORT

Generated: 2026-08-14T18:21:36Z
Config hash: `2d7344a1dac41b6a3484536e18939f294bff62d32a67310254f9a41fc7dfb0d0`

**Overall: PASS**

## 1. Test suites

| Suite | Command | Result | Exit |
|---|---|---|---|
| Stage 8Y | `pytest experiments/stage8y/tests` | `116 passed in 3.59s` | 0 |
| Legacy (pre-existing) | `pytest tests` | `11 passed in 0.01s` | 0 |
| Stage 8X (must be unaffected) | `pytest experiments/stage8x/tests` | `74 passed in 1.19s` | 0 |

## 2. Required validation coverage (brief section 36)

| Requirement | Test |
|---|---|
| heterogeneous hash rate | `test_heterogeneous_aggregates`, `test_aggregate_hashrate_is_not_held_constant` |
| heterogeneous power | `test_heterogeneous_aggregates` |
| ASIC registry loading | `test_registry_loads_and_is_self_consistent`, `test_device_efficiency_spread_is_real` |
| active-set selection | `test_selection_meets_the_hash_floor`, `test_efficiency_first_picks_the_efficient_devices_first` |
| optimization correctness | `test_S4_is_exactly_optimal` (vs exhaustive enumeration) |
| deterministic tie breaking | `test_selection_is_deterministic_with_stable_tie_break` |
| equal range allocation | `test_equal_slots_make_fast_miners_finish_first` |
| hash-proportional allocation | `test_hash_proportional_slots_equalise_completion_time` |
| energy-aware policy | `test_p3_never_activates_reserves`, `test_selectivity_gain_exceeds_one_when_heterogeneous` |
| reserve activation | `test_reserve_activation_produces_wake_transitions`, `test_reserve_activation_raises_active_capacity_above_stage_zero` |
| wake transition | `test_zero_wake_delay_produces_no_waking_residence`, `test_wake_delay_costs_energy_and_is_conservative` |
| state residence | `test_ledger_four_state_conservation_synthetic`, `test_state_time_conservation_in_real_runs` |
| energy accounting | `test_energy_formula_matches_state_times`, `test_pow_energy_reference_is_full_active`, `test_power_identity_holds_exactly` |
| target calculation | `test_difficulty_is_derived_from_full_installed_hardware` |
| nonce-domain integrity | `test_slots_are_disjoint_and_tile_the_domain`, `test_domain_is_not_reduced_by_parking_miners` |
| exact duplicate accounting | `test_duplicate_identity_and_pocol_zero_duplicates`, `test_nonce_value_reuse_is_not_exact_duplication` |
| paired seed reproducibility | `test_seed_reproducibility`, `test_matched_runs_share_seed_and_hardware` |
| PoW/PoCol matched parameters | `test_matched_difficulty_across_all_protocols` |
| no PoCol-specific recalibration | `test_no_pocol_specific_difficulty_recalibration_in_source`, `test_difficulty_does_not_depend_on_active_fraction` |
| no hash work in forbidden states | `test_work_equals_integral_of_active_hashrate` |
| no range overlap / rescan | `test_completed_ranges_are_not_rescanned` |
| no double-counted evaluations | `test_work_equals_integral_of_active_hashrate` |
| α is accounting-only | `test_alpha_is_accounting_only`, `test_alpha_changes_only_energy_not_trajectory` |
| decomposition exactness | `test_decomposition_is_exact_and_additive`, `test_selection_term_is_zero_in_the_homogeneous_control` |
| seed disjointness incl. Stage 8X | `test_seed_groups_are_disjoint_and_fresh`, `test_seeds_are_disjoint_from_stage8x` |

## 3. Protected-artifact verification

* protected files fingerprinted: **218**
* baseline recorded: 2026-08-14T17:40:27Z
* baseline SHA-256: `2e9e6f76fadc3a9b8854cf0ea5a4a2cdfe93fe5f7df11c15150fcf69b2f7606b`
* current SHA-256: `2e9e6f76fadc3a9b8854cf0ea5a4a2cdfe93fe5f7df11c15150fcf69b2f7606b`
* status: **OK**
* **Zero unintended modifications.** Every pre-existing artifact — `Models/`, `results/`, `docs/`, `tests/`, all of `experiments/stage8x/`, the legacy scripts, the root simulator modules and every thesis `.docx`/`.pdf`/`.xlsx` — is byte-identical.

Stage 8Y writes only under `experiments/stage8y/`. Its single external import is `experiments.stage8x.simulator.hashing`, read-only, which guarantees an identical SHA-256 and candidate-identity semantics between the two experiment families.

