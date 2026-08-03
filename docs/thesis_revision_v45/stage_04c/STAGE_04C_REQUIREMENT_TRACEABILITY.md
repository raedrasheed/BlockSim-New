# Stage 4C — Requirement Traceability

Every Stage-4C requirement (S4C-1 … S4C-6) mapped to its implementation and its locking test(s).
All 9 Stage-4C tests plus the 115 retained tests pass (**124 total**). Baseline
`8750c5ecc8571b962e0f9d69e63f4ca7fe5ffdf3`; `search.py` byte-identical.

| Req | Requirement | Implementation (`Models/PoCol/stage2/`) | Locking test(s) |
|-----|-------------|------------------------------------------|-----------------|
| **S4C-1** | Every energy field is a true request-interval residency delta (predecessor active/idle, reassignee standby) via exact start/end snapshots on `RangeLease` + `RangeReassignmentRequest`; never final run residency when the request terminal is earlier. | `simulator.py`: time-aware `_residency(m, state, t)` (adds the open interval), `_stamp_lease_start_residency`, revoke/seat snapshots in `SeatRangeReassignmentTransaction`, `_stamp_request_terminal`, wake-start snapshots in both wake paths; `leases.py`: `RangeLease.*_residency_at_lease_start`, `RangeReassignmentRequest.revocation_time` + `*_at_revocation` / `*_at_request_terminal` / `*_at_seat` / `*_at_wake_start`; `adapter.py`: `reassignment_energy_report` exact per-component deltas | `test_s4c_01`, `test_s4c_02`, `test_s4c_03` |
| **S4C-2** | Verify all five components independently; expose one residual per component + `max_request_energy_residual_j`; interval-overlap audit (no residency charged twice); aggregate ≤ integrated run residency. | `adapter.py`: `reassignment_energy_report` five residuals + `max_request_energy_residual_j` + `overlapping_charged_interval_count` + `aggregate_exceeds_run_residency_count` + chained-predecessor rule; `simulator.py`: `_eligible_reassignment_candidates` in-flight-reassignee exclusion (one reassignment per miner) | `test_s4c_04`, `test_s4c_05` |
| **S4C-3** | Both Path-B seat-failure points clear the linked reserve fields / reverse links / wake handle; update the synthetic decision to a terminal failure outcome; no `ACTIVATION_SEATED` decision without a failed terminal; no registry references the removed WakeHandleID. | `simulator.py`: `_fail_pathb_wake` (complete-seat) + `_terminalise_synthetic_activation_decision` + `_clear_reserve_record_activation_fields`; `SeatReserveActivationTransaction` rollback + `_rollback_wake` (start-seat); `security.py`: `ReserveActivationDecision.disposition` | `test_s4c_06` |
| **S4C-4** | Store explicit Path-B identity (`WakeHandleID`, `OriginalRangeSliceID`, `RangeReassignmentRequestID`) on `ReserveActivationRequest`; `ReserveSliceID` not overloaded; auditable after handle removal. | `security.py`: `ReserveActivationRequest.WakeHandleID` / `OriginalRangeSliceID` / `RangeReassignmentRequestID`; `simulator.py`: set in `SeatReserveActivationTransaction` via `_seat_reserve_reassignment_wake` | `test_s4c_07` |
| **S4C-5** | Both deadline payloads carry all declared fields explicitly; safe extraction; no default `expected_lease_status`; missing/tampered → `range_deadline_no_effect("missing_or_tampered_identity")`, no KeyError, no mutation; current EventRef must equal the armed deadline ref. | `events.py`: `_PROGRESS_TIMEOUT_PAYLOAD_KEYS` + `expected_lease_status`; `simulator.py`: `_refresh_progress_timeout` (adds it), `_verify_deadline_identity` (`_DEADLINE_REQUIRED`, safe `.get`, EventRef match), `_handle_range_lease_expiry` / `_handle_range_progress_timeout` return `range_deadline_no_effect` | `test_s4c_08` |
| **S4C-6** | Exact replay + unknown-trigger rejection are state-pure (no protocol state / sequence / counter change); the three diagnostic counters do not increment protocol state. | `context.py`: `RunContext.lease_diagnostics` namespace; `simulator.py`: `EvaluateRangeLease` (unknown-trigger + observation replay) and `SeatRangeReassignmentTransaction` (natural + defensive replay) increment only `lease_diagnostics`; `adapter.py`: `_range_lease_results` sources the three counters from `lease_diagnostics` | `test_s4c_09` |

## Retained coverage (115 tests, unchanged)

Stage-2 / Stage-3 / Stage-3A / Stage-4 / Stage-4A / Stage-4B (TV325–TV338, E2E-1..5, SCI-1..10,
S3-01..S3-18, S3A-01..S3A-12, S4-01..S4-20, S4A-01..S4A-14, S4B-01..S4B-12).

Three retained white-box assertions were **relocated** (not weakened / renamed) to read the moved
diagnostic counters from `lease_diagnostics` instead of `lease_stats`, as the S4C-6 data model
requires: the S4A observation-replay assertion, S4A-11 (`reassignment_replay_count`) and S4B-04
(`unknown_trigger_rejections`). Each keeps its exact `+ 1` / `>= 1` assertion strength; S4B-04 is
additionally strengthened to assert full `lease_stats` purity.
