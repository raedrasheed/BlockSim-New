# Stage 4A — Test Report

**103 tests pass** (89 accepted Stage-2B / Stage-3 / Stage-3A / Stage-4 tests **retained
unchanged** + 14 new Stage-4A tests). Python 3.11, pytest. Raw evidence:
`evidence/pytest_stage4a.log`, `evidence/pytest_stage4a.junit.xml`.

```
python -m pytest tests/thesis_revision_v45/stage2/ -v --durations=0 -p no:cacheprovider
=> 103 passed
python -m Models.PoCol.stage2.demo   # standalone smoke: OK
```

## New Stage-4A tests (`test_stage4a_lease_lifecycle.py`)

| Test | What it locks |
|------|---------------|
| `test_s4a_01_lease_expiry_is_executable` | A finite `lease_duration` arms a real `RangeLeaseExpiryEvent` at `lease_expiry_time` for every ACTIVE lease; on fire the lease is EXPIRED (or REASSIGNED); a single-miner run leaves it EXPIRED. |
| `test_s4a_02_expiry_cancels_that_leases_queued_events` | The expiry terminalisation cancels that LeaseID's queued hash/exhaust events; no expiry/timeout event is left QUEUED after close. |
| `test_s4a_03_progress_timeout_is_executable` | A finite `progress_timeout` arms a real `RangeProgressTimeoutEvent` that fires and terminalises (EXPIRED), counted in `progress_timeouts`. |
| `test_s4a_04_progress_timeout_refreshes_on_causal_advance_not_planning` | Planning a batch refreshes nothing; a causal frontier advance refreshes `last_progress_time` + bumps `timeout_generation`; superseded deadlines are stale-safe; residency reconciles. |
| `test_s4a_05_miner_cancelled_is_distinct_from_failure` | `MINER_CANCELLED` → LOW_POWER_LISTEN + lease CANCELLED; `MINER_FAILED` → OFFLINE + lease REVOKED; counters distinct. |
| `test_s4a_06_evaluate_range_lease_is_authoritative` | A premature `LEASE_TIME_EXPIRED` records `condition_satisfied=False` / `LEASE_REMAINS_ACTIVE` and does **not** revoke. |
| `test_s4a_07_one_observation_per_observation_and_replay_is_idempotent` | Exactly one `RangeLeaseObservation` per observation; exact replay of the same trigger EventRef is idempotent (`lease_observation_replay_count`). |
| `test_s4a_08_range_exhaust_is_stale_safe_under_leases` | A RangeExhaustEvent from a superseded lease is a no-op (`stale_exhaust_events`); the successor is not idled, the slice not mis-completed. |
| `test_s4a_09_pathb_removes_overlapping_slice_and_binds_original_progress` | Path B uses `REASSIGNMENT_WAKE_ONLY` scope bound to the ORIGINAL progress; `overlapping_slice_count == 0`; no `WH-`/`RRS-` domain slice; dup=0, post=0. |
| `test_s4a_10_pathb_wake_rollback_leaves_no_orphan` | A failed Path-B wake seat rolls back fully — no orphan wake-handle slice, synthetic observation/decision or link; FAILED request registered; all leases terminal. |
| `test_s4a_11_reassignment_replay_is_natural` | Re-observing the same terminal predecessor lease returns `range_reassignment_already_exists` with no second request and **no manual generation rewind**. |
| `test_s4a_12_reassignment_energy_attributed_by_lifecycle_interval` | Reassignment active energy < the reassignee's full ACTIVE residency (its own primary work is excluded); `reassignment_energy_residual_j` ≈ 0; residency reconciles. |
| `test_s4a_13_exact_metrics_across_all_correction_scenarios` | Across expiry / timeout / cancel / Path-A / Path-B: energy residual 0, dup 0, post-round 0, overlap 0, non-terminal 0, reconciles, ≥1 observation. |
| `test_s4a_14_disabled_by_default_and_target_unchanged` | Lease-disabled runs seat no deadline/cancellation events and record no observations; target/difficulty never change; declared scopes are `(RESERVE_DOMAIN_CLAIM, REASSIGNMENT_WAKE_ONLY)`. |

## Confirmatory metrics

See `RANGE_LEASE_METRICS.json` / `evidence/stage4a_metrics.json`. Across all six scenarios
(time-expiry, progress-timeout, miner-cancelled, Path-A failure, Path-B reserve wake, Path-B
wake rollback): `duplicate_nonce_count = 0`, `post_round_evaluation_count = 0`,
`overlapping_slice_count = 0`, `nonterminal_lease_count = 0`,
`nonterminal_reassignment_request_count = 0`, `reassignment_energy_residual_j = 0.0`, and
per-miner residency reconciles.
