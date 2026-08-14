# STAGE 8X — VALIDATION REPORT

Generated: 2026-08-14T17:08:04Z
Config hash: `b871c98ea1c612cdbd5a2223ff017610d908ae78fe08d509113f86983218cebf`

**Overall: PASS**

## 1. Stage 8X validation suite (brief section 25)

* command: `python -m pytest experiments/stage8x/tests -q`
* result: `74 passed in 1.26s`
* exit code: 0
* elapsed: 1.43 s

Coverage of the required checks:

| Required validation | Test |
|---|---|
| Hardware arithmetic H_N = N x 234 TH/s | `test_aggregate_hashrate_scales_with_n`, `test_expected_scaling_table_matches_brief` |
| Hardware arithmetic P_N = N x 3510 W | `test_aggregate_power_scales_with_n` |
| S21 consistency 234 x 15 = 3510 | `test_s21_consistency_234_times_15_equals_3510` |
| Energy baseline E_i = 3510 x T | `test_energy_baseline_full_active_run`, `test_pow_is_active_for_the_whole_horizon` |
| Low-power energy E = 3510 t_a + a 3510 t_l | `test_low_power_energy_formula` |
| State-time conservation sum_s t_i,s = T | `test_power_state_ledger_conservation_synthetic`, `test_state_time_conservation_in_real_runs` |
| Disjoint PoCol ranges R_i n R_j = empty | `test_pocol_ranges_are_disjoint_and_tile_the_domain` |
| No PoCol exact duplicates | `test_pocol_has_zero_exact_duplicate_evaluations` |
| Nonce reuse is not exact duplication | `test_traditional_pow_has_zero_exact_duplicates_but_high_nonce_reuse`, `test_matched_template_pow_does_produce_exact_duplicates` |
| Matched difficulty D^PoW_N = D^PoCol_N | `test_pow_and_pocol_share_the_same_difficulty_and_target` |
| Difficulty coupled to H_N, 600 s interval | `test_difficulty_is_coupled_to_aggregate_hashrate`, `test_difficulty_yields_600s_expected_interval` |
| Real SHA-256 semantics behind the abstraction | `test_real_double_sha256_matches_target_probability`, `test_candidate_identity_is_template_plus_index` |
| Seed reproducibility | `test_same_seed_reproduces_identical_physical_results` |
| alpha invariance of the trajectory | `test_alpha_is_not_a_simulation_parameter`, `test_alpha_only_changes_energy_not_trajectory` |
| Work-accounting identity W = h x t_active | `test_total_work_equals_rate_times_active_time` |
| Run-matrix shape (300 runs, 600 alpha rows) | `test_config_matrix_shape` |

## 2. Pre-existing test suite (must be unaffected)

* command: `python -m pytest tests -q`
* result: `11 passed in 0.01s`
* exit code: 0

## 3. Non-interference with earlier experiments

* protected files checksummed: 106
* status: **ok**
* changed files: none — every pre-existing artifact is byte-identical.

Stage 8X writes only under `experiments/stage8x/` and imports only the pure,
already-unit-tested `Models.Energy` constants. It never imports `InputsConfig`,
`Main`, `Scheduler`, `Event` or `Statistics` (asserted by
`test_stage8x_never_imports_global_inputsconfig`).
