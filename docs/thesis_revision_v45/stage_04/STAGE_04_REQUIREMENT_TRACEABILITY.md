# Stage 4 — Requirement Traceability

Maps every Stage-4 requirement (S4-1 … S4-13), mandatory test (S4-01 … S4-20) and acceptance
gate to the executable code and test that realises it.  Algorithm: PoCol.  Mechanism: the
idle policy within PoCol.  Reassignment is a liveness/coverage mechanism (never energy-saving).

## Requirements → code

| Req | Code |
|---|---|
| S4-1 range-lease model + lifecycle | `leases.RangeLease`, `LEASE_STATUSES`; `simulator._create_range_progress_and_lease` |
| S4-2 authoritative range progress | `leases.RangeProgress`; frontier advance in `simulator._handle_hash_work` |
| S4-3 lease primary + reserve; ledger + hash/exhaust identity | `simulator._handle_prepare_participants` / `_handle_reserve_activation_complete`; `events` optional LeaseID keys; `_verify_hash_lease`; `context.EvaluationRecord` |
| S4-4 lease policy + explicit triggers | `leases.RangeLeasePolicy`, `LEASE_TRIGGERS`; `config.injected_lease_faults`; `simulator._handle_miner_failure` |
| S4-5 authoritative lease observation (idempotent) | `simulator.EvaluateRangeLease`, `_lease_observation_key` |
| S4-6 deterministic reassignment selection | `leases.select_reassignment_candidate`; `simulator._eligible_reassignment_candidates` |
| S4-7 reassignment decision + request identity | `leases.RangeReassignmentDecision` / `RangeReassignmentRequest`, `reassignment_request_id` |
| S4-8 causal reassignment events | `events` `RangeReassignmentStart/Complete` descriptors; `simulator._verify_reassignment_identity`, handlers |
| S4-9 transactional lease transitions | `simulator.RevokeRangeLeaseTransaction`, `SeatRangeReassignmentTransaction`, `_bind_reassigned_lease` (all-or-none + rollback) |
| S4-10 interaction with Stage-3 reserve activation | `simulator._seat_reserve_reassignment_wake`, `_bind_reserve_reassignment_if_any` (reuse accepted `SeatReserveActivationTransaction`) |
| S4-11 no-eligible-miner policy | `simulator._apply_no_eligible_policy`, `_handle_range_reassignment_retry` |
| S4-12 round closure + exhaustion | `simulator._close_lease_state`, `_maybe_terminate_no_block` |
| S4-13 energy + timing accounting | `adapter._range_lease_results` |

## Tests → requirement

| Test | Requirement |
|---|---|
| S4-01 every primary gets one ACTIVE lease | S4-1, S4-3 |
| S4-02 every activated reserve gets one ACTIVE lease | S4-3 |
| S4-03 committed progress is exact | S4-2 |
| S4-04 planning does not advance frontier | S4-2 |
| S4-05 failure revokes lease + cancels queued hash event | S4-4, S4-9 |
| S4-06 new lease begins at committed frontier | S4-2, S4-8 |
| S4-07 reassignee evaluates no nonce below frontier | S4-2, S4-8 |
| S4-08 zero duplicate nonce across predecessor/successor | S4-2, S4-8 |
| S4-09 stale old-lease hash event → no effect | S4-3 |
| S4-10 exact replay → no second lease/event | S4-7 |
| S4-11 two runs select the same reassignee | S4-6 |
| S4-12 reserve reassignee uses accepted Stage-3 wake | S4-10 |
| S4-13 no-eligible CONTINUE records uncovered suffix | S4-11, S4-12 |
| S4-14 no-eligible ABORT closes through owner | S4-11 |
| S4-15 seat failure → coherent lease/progress state | S4-9 |
| S4-16 closure terminalises all leases + requests | S4-12 |
| S4-17 full-domain rejected with unassigned suffix | S4-12 |
| S4-18 true full-domain after reassignment covers all once | S4-2, S4-12 |
| S4-19 reassignment energy == residency terms | S4-13 |
| S4-20 lease/policy change never changes target/difficulty | S4-4 |

Retained (all rerun, unchanged): the 37 Stage-2B + 19 Stage-3 + 12 Stage-3A tests (68 total).
The only edits are the adapter schema-version assertions (`stage3a.1` → `stage4.1`).

## Acceptance gates → evidence

| Gate | Evidence |
|---|---|
| 1 one authoritative current lease per searchable slice | `_create_range_progress_and_lease`; S4-01, S4-02 |
| 2 committed frontier monotonic + causal | `_handle_hash_work` asserts; S4-03; metrics `max_progress_frontier_residual == 0` |
| 3 reassignment starts at the committed frontier | S4-06 |
| 4 no committed nonce re-evaluated | S4-07, S4-08; metrics `duplicate_nonce_count == 0` |
| 5 old-lease events stale-safe | `_verify_hash_lease`; S4-09 |
| 6 reassignment selection deterministic | `select_reassignment_candidate`; S4-11 |
| 7 request replay → no duplicate lease/event | S4-10 |
| 8 lease/reassignment transactional / compensated | `Revoke/Seat` transactions; S4-15 |
| 9 reserve activation & reassignment distinct | S4-12 |
| 10 selected reserve reassignees use accepted Stage-3 lifecycle | `_seat_reserve_reassignment_wake`; S4-12 |
| 11 no-eligible behaviour explicit | S4-13, S4-14 |
| 12 unfinished suffixes never hidden | S4-13, S4-17; metrics `uncovered_nonce_count` |
| 13 full-domain exhaustion requires every suffix completed | `_maybe_terminate_no_block`; S4-17, S4-18 |
| 14 reassignment energy + latency fully accounted | S4-19; adapter fields; metrics residuals 0 |
| 15 target/difficulty unchanged | S4-20 |
| 16 S4-01 … S4-20 pass | 20/20 |
| 17 all 68 accepted tests still pass | 68/68 |
| 18 GitHub Actions succeeds | `.github/workflows/stage4-pocol-tests.yml` |
| 19 Stage 1 / Stage 2B / Stage 3A preserved | search core byte-identical; `stage_01/`,`stage_02/`,`stage_03/`,`stage_03a/` unchanged |
| 20 Stage 5 not begun | no rewards/Sybil/selfish-mining/adversarial/dynamic-difficulty code |
