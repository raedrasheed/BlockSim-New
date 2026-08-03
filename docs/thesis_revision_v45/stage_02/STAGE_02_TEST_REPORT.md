# Stage 2B — Test Report

Machine-generated evidence in `docs/thesis_revision_v45/stage_02/evidence/`:
`pytest_stage2b.log` (full `pytest -v --durations=0` output), `pytest_stage2b.junit.xml`
(JUnit XML), `stage2b_metrics.json` (deterministic scientific / ledger / energy metrics).
This report summarises those machine artifacts.

## 1. Exact pytest command

```
python3 -m pytest tests/thesis_revision_v45/stage2/ -v \
    -p no:cacheprovider \
    --junitxml=docs/thesis_revision_v45/stage_02/evidence/pytest_stage2b.junit.xml
```

## 2. Environment

| Field | Value |
|---|---|
| Python | 3.11.15 |
| pytest | 9.1.1 |
| pluggy | 1.6.0 |
| Platform | Linux-6.18.5-x86_64-with-glibc2.39 |
| Third-party deps | none (stdlib only: `hashlib`, `dataclasses`, `math`) |

## 3. Commit provenance

| Field | Value |
|---|---|
| Branch | `thesis-v45-pocol-stage2b-target-causal-search-genesis-rollback-lock` |
| Parent SHA | `64bca1d18554016a8c6aa9688255ff1fb3eb844f` |
| Commit SHA | the resulting HEAD of this branch (a file cannot embed its own commit hash; recorded in the acceptance-review handoff and retrievable via `git rev-parse HEAD`) |

## 4. Collection / result summary

| Metric | Value |
|---|---|
| Collected | 37 |
| Passed | 37 |
| Failed | 0 |
| Skipped | 0 |
| Errors | 0 |
| Duration | 3.80 s |

## 5. Complete test-name list

Semantic vectors — `test_stage2_semantic_vectors.py`:
`test_tv325_partial_genesis_third_seat_fails_round_aborts_through_closure`,
`test_tv326_template_commit_seat_failure_after_genesis_seats_exist`,
`test_tv327_queued_exact_round_event_cancelled_before_rotation`,
`test_tv328_next_available_effective_round_time_binding`,
`test_tv329_future_events_during_partial_finalization_are_cancelled`,
`test_tv330_failure_between_schedule_commit_and_request_publication`,
`test_tv331_cancellation_status_publication_coherent_and_failure_captured`,
`test_tv332_distinct_equal_deficit_reserve_incidents`,
`test_tv333_exact_replay_returns_status_eventref_disposition`,
`test_tv334_foreign_run_context_sharing_eq_rejected`,
`test_tv335_duplicate_genesis_configuration_structured_failure`,
`test_tv336_cancelled_request_event_at_dispatch_no_domain_effect`,
`test_tv337_driver_target_before_frontier_rejected`,
`test_tv338_driver_binding_stale_round_scope_no_domain_effect`.

End-to-end — `test_stage2_e2e.py`:
`test_e2e1_first_round_reaches_hashing_and_accepts`,
`test_e2e2_first_round_aborts_then_second_round_starts`,
`test_e2e3_consecutive_rounds_no_event_leakage`,
`test_e2e4_reaches_horizon_energy_and_residency_reconcile`,
`test_e2e5_next_round_bootstrap_failure_partial_finalization`.

Scientific + target — `test_stage2_scientific.py`:
`test_sci1_simulator_ranges_disjoint_and_cover_domain`,
`test_sci2_ledger_zero_duplicate_template_nonce`,
`test_sci3_every_active_miner_worked_or_justified_zero`,
`test_sci4_no_ledger_completion_after_round_end`,
`test_sci5_searched_count_equals_ledger_count`,
`test_sci6_fixed_target_hash_validation_exact`,
`test_sci7_zero_solution_template_full_domain_exhaustion`,
`test_sci8_matched_control_and_idle_same_template_target_winner_end`,
`test_sci9_pidle_equals_pactive_zero_saving`,
`test_sci10_canonical_a1_baseline`,
`test_s2b1_easier_target_is_superset`,
`test_s2b1_difficulty_changes_success_distribution`,
`test_s2b1_target_is_used_not_stored_and_ignored`,
`test_s2b1_zero_and_multi_solution_outcomes_exist`.

Adapter — `test_stage2_adapter.py`:
`test_adapter_maps_blocksim_config`,
`test_adapter_returns_declared_schema`,
`test_adapter_default_config_is_canonical_a1_reference`,
`test_results_schema_directly`.

## 6. Actual target / difficulty (canonical A1 config)

| Field | Value |
|---|---|
| Difficulty | `1000` |
| Target | `floor((2^256 − 1) / 1000)` = `115792089237316195423570985008687907853269984665640564039457584007913129639` |
| Per-nonce success probability `p = (target+1)/2^256` | `1.000e-03` |

## 7. Deterministic run metrics (`evidence/stage2b_metrics.json`)

Confirmatory run (8 miners, T = 150 s, D = 1200, difficulty 1000):

| Metric | Value |
|---|---|
| Rounds executed | 79 |
| Rounds accepted (block) | 56 |
| Rounds no-block (abort) | 22 |
| Actual evaluation count (ledger) | 52,795 |
| Ledger records | 2,140 |
| **Duplicate count** | **0** |
| **Post-round evaluation count** | **0** |
| searched-count vs ledger mismatches | 0 |
| **Max searched-count / time residual** | **5.00e-12** |
| Residency reconciles (I5) | True |
| Run energy (kWh) | 0.00345 |
| Continuous all-active reference (kWh) | 0.00717 |
| Queue terminal states | `CONSUMED: 3066`, `CANCELLED: 249` |
| Driver-request terminal states | `CONSUMED: 8` |

Deterministic zero-solution run (SCI-7; 6 miners, T = 50 s, D = 600, target = 0):

| Metric | Value |
|---|---|
| Target | 0 (deterministically unsatisfiable) |
| Rounds executed | 25 |
| **Number of zero-solution rounds** | 24 no-block aborts + 1 horizon-closed (0 blocks) |
| Accepted blocks | 0 |
| Round-1 domain fully covered (exhaustion) | True |

Constructed matched identity experiment (8 miners, D = 2400):

| Metric | Value |
|---|---|
| Scenario | `constructed_matched_identity_validation` (seed 35) |
| Winner / winning nonce | `M000` / `205` |
| Round end (s) | 2.06 |
| Miners idling early | 7 / 8 |
| Scenario saving (J) | 220.98 (constructed scenario only) |
| **Max energy-identity residual (J)** | **7.11e-15** |
| Saving when `P_idle == P_active` | 0.0 |

## 8. Reproduction

```
git checkout thesis-v45-pocol-stage2b-target-causal-search-genesis-rollback-lock
python3 -m pytest tests/thesis_revision_v45/stage2/ -v --durations=0
python3 -m Models.PoCol.stage2.demo
```

The suite uses only the Python standard library and is deterministic (fixed SHA-256
targets, no wall-clock / RNG / network), so a re-run reproduces the metrics above.
