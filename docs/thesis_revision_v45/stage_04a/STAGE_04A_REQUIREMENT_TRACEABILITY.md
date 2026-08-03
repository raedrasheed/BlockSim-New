# Stage 4A — Requirement Traceability

Every Stage-4A requirement (S4A-1 … S4A-9) mapped to its implementation and its locking test(s).
All 14 Stage-4A tests plus the 89 retained tests pass (**103 total**).

| Req | Requirement | Implementation (`Models/PoCol/stage2/`) | Locking test(s) |
|-----|-------------|------------------------------------------|-----------------|
| **S4A-1** | Lease expiry is executable: seat a `RangeLeaseExpiryEvent` for every ACTIVE lease at `lease_expiry_time`; on fire mark EXPIRED, cancel that LeaseID's queued hash/exhaust events, invoke `EvaluateRangeLease(LEASE_TIME_EXPIRED)`; stale-safe. | `events.py` (`RangeLeaseExpiryEvent`, microphase `RANGE_LEASE_EXPIRY=23` after `HASH_WORK=12`); `simulator.py` `_seat_lease_expiry`, `_handle_range_lease_expiry`, `_cancel_lease_deadlines`; `leases.py` `RangeLease.expiry_event_ref` | `test_s4a_01`, `test_s4a_02` |
| **S4A-2** | Progress timeout: `RangeProgressTimeoutEvent`; `RangeProgress.last_progress_time`/`timeout_event_ref`/`timeout_generation`; refresh on **causal advance**, not planning; stale-safe. | `events.py` (`RangeProgressTimeoutEvent`, `RANGE_PROGRESS_TIMEOUT=24`); `simulator.py` `_refresh_progress_timeout` (called from `_handle_hash_work` on `advanced`), `_handle_range_progress_timeout`; `leases.py` fields | `test_s4a_03`, `test_s4a_04` |
| **S4A-3** | `MINER_CANCELLED`: distinct disposition from `MINER_FAILED`. | `events.py` (`MinerCancelledEvent`, `MINER_CANCELLED=22`); `simulator.py` `_handle_miner_cancelled` (LOW_POWER_LISTEN + CANCELLED) vs `_handle_miner_failure` (OFFLINE + REVOKED); `_TRIGGER_TERMINALISATION`; `config.py` `injected_lease_cancellations` | `test_s4a_05` |
| **S4A-4** | `EvaluateRangeLease` authoritative: validate the trigger condition; add a `RangeLeaseObservation` record; don't revoke merely because called. | `simulator.py` `EvaluateRangeLease` (rewritten), `_trigger_condition_satisfied`, `_append_lease_observation`, `_lease_observation_key`; `leases.py` `RangeLeaseObservation`; `context.py` `lease_observations` | `test_s4a_06`, `test_s4a_07` |
| **S4A-5** | `RangeExhaust` is stale-safe under leases. | `simulator.py` `_verify_exhaust_lease` (guard in `_handle_range_exhaust`); `stale_exhaust_events` | `test_s4a_08` |
| **S4A-6** | Remove the overlapping Path-B RRS RangeSlice; reuse Stage-3 activation in `REASSIGNMENT_WAKE_ONLY` scope bound to the original `RangeProgress`; prove slices disjoint. | `simulator.py` `_seat_reserve_reassignment_wake` (wake handle `WH-…`, not a domain slice), `_audit_slice_disjointness`, `SeatReserveActivationTransaction(activation_scope=…)`; `security.py` `ReserveActivationRequest.activation_scope`/`range_reassignment_request_id`; `leases.py` `RESERVE_ACTIVATION_SCOPES`; `context.py` `reassignment_wake_slice_by_id` | `test_s4a_09`, `test_s4a_13` |
| **S4A-7** | Path B fully transactional: rollback leaves no orphan slice / observation / decision / link. | `simulator.py` `_seat_reserve_reassignment_wake._rollback_wake`; `pathb_rollback_count` | `test_s4a_10` |
| **S4A-8** | Reassignment replay natural, returns `range_reassignment_already_exists(...)`, no manual generation rewind. | `simulator.py` `SeatRangeReassignmentTransaction` (`reassignment_by_predecessor` guard + commit registration); `context.py` `reassignment_by_predecessor`; `reassignment_replay_count` | `test_s4a_11` |
| **S4A-9** | Attribute reassignment energy by lifecycle interval (not full residency). | `leases.py` `RangeReassignmentRequest` interval timestamps + residency snapshots; `simulator.py` timestamp/snapshot capture in reassignment start/complete + `_stamp_reassignee_active_end` + `_close_lease_state`; `adapter.py` `_range_lease_results` interval attribution + `reassignment_energy_residual_j` | `test_s4a_12`, `test_s4a_13` |

## Retained coverage (89 tests, unchanged)

* Stage-2 core + adapter + scientific + E2E + semantic vectors (TV325–TV338, E2E-1..5, SCI-1..10).
* Stage-3 / Stage-3A security-floor + reserve activation (S3-01..S3-18, S3A-01..S3A-12).
* Stage-4 range leases + reassignment (S4-01..S4-20).

Backward compatibility is structural: `RangeLeasePolicy.enabled = False` by default, and the
deadline / cancellation events + observation records are only produced when the lease layer is
engaged, so no accepted behaviour changes.
