# Stage 2A — Test Report

Machine-generated evidence for this report lives in
`docs/thesis_revision_v45/stage_02/evidence/`:

- `pytest_stage2a.log` — full captured `pytest -v --durations=0` output;
- `pytest_stage2a.junit.xml` — JUnit XML (`<testsuite>` with per-test `<testcase>` records);
- `stage2a_metrics.json` — deterministic scientific / energy / round-count metrics.

The report below is a prose summary of those machine artifacts, not a substitute for them.

## 1. Exact pytest command

```
python3 -m pytest tests/thesis_revision_v45/stage2/ -v --durations=0 \
    -p no:cacheprovider \
    --junitxml=docs/thesis_revision_v45/stage_02/evidence/pytest_stage2a.junit.xml
```

## 2. Environment

| Field | Value |
|---|---|
| Python | 3.11.15 |
| pytest | 9.1.1 |
| pluggy | 1.6.0 |
| Platform | Linux-6.18.5-x86_64-with-glibc2.39 |
| rootdir | `/home/user/blocksim-v45-stage2` |
| Third-party deps | none (stdlib only: `hashlib`, `dataclasses`, `math`) |

## 3. Collection / result summary

| Metric | Value |
|---|---|
| Collected | 30 |
| Passed | 30 |
| Failed | 0 |
| Skipped | 0 |
| Errors | 0 |
| xfailed / xpassed | 0 / 0 |
| Wall-clock duration | 2.70 s |

`30 passed in 2.70s` — see `evidence/pytest_stage2a.log` for the authoritative session line.

## 4. Complete test-name list

Semantic vectors — `tests/thesis_revision_v45/stage2/test_stage2_semantic_vectors.py`:

1. `test_tv325_partial_genesis_third_seat_actually_fails`
2. `test_tv326_template_commit_seat_failure_after_genesis_seats_exist`
3. `test_tv327_queued_exact_round_event_cancelled_before_rotation`
4. `test_tv328_next_available_effective_round_time_binding`
5. `test_tv329_future_events_during_partial_finalization_are_cancelled`
6. `test_tv330_failure_between_schedule_commit_and_request_publication`
7. `test_tv331_cancellation_status_publication_coherent_and_failure_captured`
8. `test_tv332_distinct_equal_deficit_reserve_incidents`
9. `test_tv333_exact_replay_returns_status_eventref_disposition`
10. `test_tv334_foreign_run_context_sharing_eq_rejected`
11. `test_tv335_duplicate_genesis_configuration_structured_failure`
12. `test_tv336_cancelled_request_event_at_dispatch_no_domain_effect`
13. `test_tv337_driver_target_before_frontier_rejected`
14. `test_tv338_driver_binding_stale_round_scope_no_domain_effect`

End-to-end — `tests/thesis_revision_v45/stage2/test_stage2_e2e.py`:

15. `test_e2e1_first_round_reaches_hashing_and_accepts`
16. `test_e2e2_first_round_aborts_then_second_round_starts`
17. `test_e2e3_consecutive_rounds_no_event_leakage`
18. `test_e2e4_reaches_horizon_energy_and_residency_reconcile`
19. `test_e2e5_next_round_bootstrap_failure_partial_finalization`

Scientific — `tests/thesis_revision_v45/stage2/test_stage2_scientific.py`:

20. `test_sci1_disjoint_assignments_cover_domain_exactly`
21. `test_sci2_zero_duplicate_nonce_evaluations`
22. `test_sci3_all_active_miners_contribute_hash_work`
23. `test_sci4_energy_identity_residual_within_tolerance`
24. `test_sci5_pidle_equals_pactive_zero_saving`
25. `test_sci6_canonical_a1_baseline`
26. `test_sci7_matched_control_and_idle_same_success_and_round_end`

BlockSim adapter — `tests/thesis_revision_v45/stage2/test_stage2_adapter.py`:

27. `test_adapter_maps_blocksim_config`
28. `test_adapter_returns_declared_schema`
29. `test_adapter_default_config_is_canonical_a1_control`
30. `test_results_schema_directly`

## 5. Scientific test results (from `evidence/stage2a_metrics.json`)

| Result | Value |
|---|---|
| Success model (recorded) | `B_EXACT_WITHOUT_REPLACEMENT_SAMPLER` |
| Per-nonce work primitive | `SHA256(header‖nonce)` |
| SCI-1 exact cover (D = 800, 8 miners) | `True` (no gap, no overlap) |
| SCI-2 duplicate nonce evaluations | `0` |
| SCI-6 canonical A1 | `8.420833333333333 kWh` (target `8.420833333`, `|Δ| < 1e-9`) |
| A1 parameters | 141 miners × 21.5 W × 10 000 s |

### Energy residuals (SCI-4 / SCI-5, matched CONTROL vs POCOL_IDLE, 8 miners, D = 800)

| Quantity | Value |
|---|---|
| Winner / winning nonce | `M000` / `50` |
| Round end (s) | `0.51` |
| Miners idling early | `7 / 8` |
| E_control (J) | `87.72` |
| E_pocol_idle (J) | `52.503` |
| Idle-policy saving (J) | `35.217` |
| **Max absolute residual (J)** | **`8.88e-16`** (identity `Delta_E_i = t_idle·(P_active − P_idle)` holds to machine precision) |
| Saving when `P_idle == P_active` (SCI-5) | `0.0` (partitioning alone saves nothing) |

## 6. Round counts (confirmatory multi-round run, 8 miners, T = 600 s, D = 1600)

| Metric | Value |
|---|---|
| Rounds executed | `343` |
| Rounds accepted | `342` |
| Rounds aborted | `0` |
| Loop result | `run_completed` |
| Run end time | `600.0` |
| Residency reconciles (I5) | `True` |
| Energy (kWh) | `0.014748989548610886` |
| Matched A1 control (kWh) | `0.028666666666666667` |

The single non-accepted round is the one closed at the horizon; the run is not
single-round (E2E-3 additionally asserts ≥ 2 consecutive rounds without event leakage).

## 7. Queue / request terminal-state counts (same confirmatory run)

| Registry | Terminal-state counts |
|---|---|
| Event queue (`queued_event_registry`) | `CONSUMED: 10099`, `CANCELLED: 1357` — no `QUEUED` / `DISPATCHING` survivors |
| Driver requests (`driver_request_registry`) | `CONSUMED: 8` — no `PENDING` / `SEATED` survivors |

Every event ends `CONSUMED` or `CANCELLED`; every driver request ends `CONSUMED`,
`CANCELLED`, or `REJECTED`. The pending frontier (`event_queue.event_queue`) is empty at
run end.

## 8. Reproduction

```
git checkout thesis-v45-pocol-stage2a-executable-scientific-core-remediation
python3 -m pytest tests/thesis_revision_v45/stage2/ -v --durations=0
python3 -m Models.PoCol.stage2.demo         # runnable demo (canonical A1 + idle experiment)
```

The suite uses only the Python standard library and is deterministic (seeded
without-replacement sampler; no wall-clock, RNG, or network dependence), so a re-run
reproduces the counts above.
