# Stage 4B — Test Report

Command: `python -m pytest tests/thesis_revision_v45/stage2/ -v --durations=0`.

Result: **115 passed, 0 failed, 0 errored, 0 skipped** in ≈14.4 s (Python 3.11, pytest).
Evidence: `evidence/pytest_stage4b.log`, `evidence/pytest_stage4b.junit.xml`.

* **103 retained** — Stage-2 / Stage-3 / Stage-3A / Stage-4 / Stage-4A (TV325–TV338, E2E-1..5,
  SCI-1..10, S3-01..S3-18, S3A-01..S3A-12, S4-01..S4-20, S4A-01..S4A-14). All unchanged.
* **12 new** — Stage-4B (`test_stage4b_terminal_pathb_replay_energy.py`).

## Stage-4B locking tests

| Test | Requirement | What it locks |
|------|-------------|---------------|
| `test_s4b_01_lease_expiry_before_wake_never_activates_the_miner` | S4B-1 | A lease expiring at 0.5 before its wake at 1.0 idles the miner to LOW_POWER_LISTEN, cancels the queued `WakeCompleteEvent`, and the later wake is a no-op; a full run leaves no ACTIVE_HASHING / WAKING miner. |
| `test_s4b_02_expiry_after_wake_no_active_miner_without_active_lease` | S4B-1 | After a time-expiry that fires while the miner is ACTIVE, no miner is left ACTIVE without a live ACTIVE lease; residency reconciles. |
| `test_s4b_03_progress_timeout_transitions_miner_to_low_power` | S4B-1 | A PROGRESS_TIMEOUT idles the timed-out miner to LOW_POWER_LISTEN (never OFFLINE, never left ACTIVE / WAKING). |
| `test_s4b_04_unknown_trigger_is_rejected_and_leaves_state_unchanged` | S4B-2 | An unknown trigger is rejected with no mutation / counter (except `unknown_trigger_rejections`) / state change and no REVOKED fallback. |
| `test_s4b_05_range_exhaust_without_lease_id_is_rejected` | S4B-3 | A RangeExhaust payload missing its `LeaseID` performs no effect (`stale_exhaust_events` + 1; the miner stays ACTIVE). |
| `test_s4b_06_premature_current_lease_range_exhaust_is_no_effect` | S4B-3 | A RangeExhaust for the current ACTIVE lease whose range is not exhausted (frontier below `range_end`) performs no state / termination effect. |
| `test_s4b_07_every_frontier_advance_bumps_progress_generation_and_refreshes_timeout` | S4B-8 | A causal advance bumps `progress_generation` and `timeout_generation` and updates `last_progress_time`; planning bumps nothing; a tampered stale-generation deadline is a no-op across the whole run. |
| `test_s4b_08_pathb_uses_wake_handle_and_creates_no_range_slice` | S4B-4 | Path B wakes the reserve via a NON-domain wake handle scoped REASSIGNMENT_WAKE_ONLY; no `WH-` entry leaks into `reserve_slice_by_id` / `reserve_slices`; the reassigned lease binds to the original `PS-` slice; no overlap / duplicate nonce. |
| `test_s4b_09_pathb_start_seat_failure_leaves_no_orphan` | S4B-5 | A Path-B start-seat failure rolls back fully — no orphan wake handle / observation / decision / link, no WAKING miner, no SEATED / STARTED request, `pathb_rollback_count` ≥ 1. |
| `test_s4b_10_pathb_complete_seat_failure_leaves_no_orphan_or_inflight` | S4B-5 | A Path-B complete-seat failure cleans every linked state (request FAILED with a terminal time + closed wake interval, wake handle + links removed, no WAKING miner, no in-flight request) and the round reaches a terminal disposition before the horizon. |
| `test_s4b_11_natural_replay_returns_complete_stored_result` | S4B-6 | Re-observing the same terminal predecessor lease returns `range_reassignment_already_exists` with the exact stored request / status / EventRefs / successor lease / disposition, creating nothing new and bumping no lifecycle counter. |
| `test_s4b_12_per_request_energy_attribution_is_complete_and_reconciles` | S4B-7 | The per-request report includes predecessor / standby / wake / active intervals + all timestamps + status / disposition for COMPLETED and FAILED requests, does not omit a failed wake's energy (present + reconciles exactly; a real failed-wake interval is positively attributed), and reconciles with the residency ledger (`max_energy_residual_j` < 1 × 10⁻⁶). |

## Metrics cross-check (`RANGE_LEASE_METRICS.json`)

Six deterministic scenarios; every one holds the structural invariants:
`live_active_or_waking_miner_count = 0`, `nonterminal_lease_count = 0`,
`nonterminal_reassignment_request_count = 0`, `live_wake_handle_count = 0`,
`wake_handles_in_nonce_domain_registry = 0`, `overlapping_slice_count = 0`,
`duplicate_nonce_count = 0`, `residency_reconciles = true`, and
`energy_report_max_residual_j ≤ 1.9 × 10⁻¹⁴` (floating-point noise, well below 1 × 10⁻⁶).

* `s1_time_expiry_terminalises_miner` — 146 expiries → 146 miners terminalised.
* `s2_progress_timeout_low_power` — 2664 progress timeouts → 2664 miners terminalised, 2656
  queued wakes cancelled.
* `s3_pathb_wake_handle` — one Path-B wake handle created; none in any nonce-domain registry.
* `s4_pathb_start_seat_failure` — start-seat failure → 1 rollback, 1 FAILED request, no orphan.
* `s5_pathb_complete_seat_failure` — complete-seat failure → `wake_complete_seat_failures = 1`,
  1 rollback, 1 FAILED request, no orphan / in-flight.
* `s6_energy_attribution` — combined Path-A + Path-B; per-request energy reconciles exactly.
