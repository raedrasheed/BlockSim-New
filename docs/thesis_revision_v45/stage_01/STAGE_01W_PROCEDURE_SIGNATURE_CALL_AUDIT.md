# Stage 1W — Procedure Signature & Call-Site Audit

This audit records, for every procedure touched by Stage 1W, the exact `INPUTS`, the exact `RETURNS` disposition set,
and (where called) that every caller passes arguments matching the signature and inspects the returned disposition
explicitly before acting on it. All signatures are quoted from the current `STAGE_01_PROTOCOL_PSEUDOCODE.md`.

## 1. Signature table (W-touched procedures)

| Procedure | INPUTS | RETURNS (declared result set) |
|-----------|--------|-------------------------------|
| `ApplyMinerStateTransition` | `MinerID, old_state, new_state, transition_envelope, reason, assignment_ref, candidate_id, propagation_id` | `transition_applied(TransitionEventID)` \| `duplicate_suppressed(TransitionEventID)` \| `illegal_stale_source(TransitionEventID)` \| `illegal_transition(TransitionEventID)` |
| `CreatePendingAssignment` | `RoundContext, MinerID, range, assignment_origin, source_assignment, reason` | `assignment_created(assignment)` \| `assignment_creation_failed(reason)` |
| `StartWake` | `RoundContext, MinerID, target_assignment, from_state, scheduling_context` | `wake_seated(AssignmentID, WakeEventRef, wake_target_time, resulting_state = WAKING)` \| `wake_schedule_failed_before_transition(reason)` \| `wake_transition_failed_after_seat(reason, WakeEventRef)` |
| `RangeAssign` | `RoundContext, MinerID, requested_size, lease_duration, scheduling_context` | `range_assigned(AssignmentID, WakeEventRef, resulting_state = WAKING)` \| `range_assign_creation_failed(reason)` \| `range_assign_wake_failed(reason, AssignmentID)` |
| `RangeAssignFromPlan` | `RoundContext, MinerID, range, assignment_origin, source_assignment, reassignment_reason, lease_duration, scheduling_context` | (identical to `RangeAssign`) |
| `RangeReassign` | `RoundContext, unsearched_suffix, reason, from_miner, scheduling_context` | `range_reassigned(provenance, AssignmentID, WakeEventRef)` \| `range_reassign_creation_failed(reason)` \| `range_reassign_wake_failed(reason, AssignmentID)` |
| `RangeReassignFromPlan` | `RoundContext, MinerID, range, assignment_origin, source_assignment, reassignment_reason, lease_duration, scheduling_context` | (identical to `RangeReassign`) |
| `ReserveActivateFromPlan` | `RoundContext, reserve_miner, candidate_range, assignment_origin, source_assignment, scheduling_context` | `reserve_activation_committed(MinerID, AssignmentID, assignment_version, WakeEventRef)` \| `reserve_activation_failed_before_mutation(reason)` \| `reserve_activation_failed_after_assignment(reason, AssignmentID, rollback_record)` |
| `CommitRecoveryAssignmentPlan` | `RoundContext, plan, scheduling_context` | `install_committed` \| `install_failed_before_mutation(reason)` \| `install_failed_after_mutation(reason, rollback_record)` |
| `RollbackParticipantSetup` | `RoundContext, setup_txn` (with `rollback_envelope`) | `rollback_completed(rolled_to_offline)` \| `rollback_failed(reason)` |
| `RollbackTemplateRefreshSetup` | `RoundContext, setup_txn` (with `rollback_envelope`) | `rollback_completed(rolled_to_offline)` \| `rollback_failed(reason)` |
| `SetupRetryEvent` | `RoundContext, dispatch_envelope, RoundID, setup_kind, SetupRetryID, setup_retry_generation, reason` | `setup_retry_stale_noop` \| `setup_retry_duplicate_suppressed` \| `setup_retry_exhausted` \| `round_aborted` \| (the re-run setup's disposition) |
| `PrepareParticipantsForNewRound` | `RoundContext, dispatch_envelope` | `participant_set_prepared` \| `participant_set_setup_retry_seated(SetupRetryID, reason)` \| `round_aborted` |
| `TemplateRefresh` | `RoundContext, dispatch_envelope` | `new_TemplateID` \| `template_refresh_retry_seated(SetupRetryID, reason)` \| `round_aborted` |

## 2. Call-site agreement matrix

For each callee, every caller and the two checks: **args match** (the caller passes exactly the signature's
parameters) and **result inspected** (the caller branches on the declared disposition before acting).

### `ApplyMinerStateTransition` (W6)

| Caller | Args match | Result inspected |
|--------|-----------|------------------|
| `StartWake` | ✓ | ✓ `IF tr is NOT transition_applied(teid)` → cancel seated event, return `wake_transition_failed_after_seat` |
| `RollbackParticipantSetup` / `RollbackTemplateRefreshSetup` | ✓ (`transition_envelope = setup_txn.rollback_envelope`; `WAKING -> OFFLINE`) | ✓ `IF tr is transition_applied(teid): rolled_to_offline <- true` |
| other callers (WakeCompleteEvent, LeaseExpiry, AdversarialParticipationChangeEvent, …) | ✓ | for-effect (value legitimately ignored; none tests a name outside the union) |

### `CreatePendingAssignment` (W7)

| Caller | Args match | Result inspected (before any AssignmentID/lease/txn access) |
|--------|-----------|-----------------------------------------------------------|
| `PrepareParticipantsForNewRound` | ✓ | ✓ `IF cr is assignment_creation_failed(reason): participant_setup_error <- ... ; CONTINUE` |
| `TemplateRefresh` | ✓ | ✓ `IF cr is assignment_creation_failed(reason): refresh_setup_error <- ... ; CONTINUE` |
| `RangeAssignFromPlan` | ✓ | ✓ `IF cr is assignment_creation_failed(reason): RETURN range_assign_creation_failed(reason)` |
| `RangeReassignFromPlan` | ✓ | ✓ `IF cr is assignment_creation_failed(reason): RETURN range_reassign_creation_failed(reason)` |
| `ReserveActivateFromPlan` | ✓ | ✓ `IF cr is assignment_creation_failed(cf): RETURN reserve_activation_failed_before_mutation(reason = cf)` |
| `AdversarialParticipationChangeEvent` | ✓ | ✓ `IF cr is assignment_creation_failed(reason): RETURN participation_reentry_creation_failed(...)` |

### `StartWake` (W6 consumer)

| Caller | Args match | Result inspected |
|--------|-----------|------------------|
| `RangeAssignFromPlan`, `RangeReassignFromPlan`, `ReserveActivateFromPlan` | ✓ | ✓ `wake_seated` → success; else close head + structured failure |
| `PrepareParticipantsForNewRound`, `TemplateRefresh` | ✓ `ORDINARY_DISPATCH(dispatch_envelope)` | ✓ `wake_seated` → capture; else set `*_setup_error` |
| `ResumeFromPause`, `AdversarialParticipationChangeEvent` | ✓ | ✓ `wake_seated` → started; else failure |

### Plan-bound range constructors (W4/W5)

| Callee | Caller | Args match | Result inspected |
|--------|--------|-----------|------------------|
| `RangeAssignFromPlan` | `RangeAssign`, `CommitRecoveryAssignmentPlan` (spec.origin = ORIGINAL) | ✓ exact spec fields | ✓ `range_assigned` / `range_assign_creation_failed` / `range_assign_wake_failed` |
| `RangeReassignFromPlan` | `RangeReassign`, `CommitRecoveryAssignmentPlan` (spec.origin = REASSIGNED) | ✓ exact spec fields | ✓ `range_reassigned` / `range_reassign_creation_failed` / `range_reassign_wake_failed` |

### Setup rollback / retry (W1/W2/W8)

| Callee | Caller | Args match | Result inspected |
|--------|--------|-----------|------------------|
| `RollbackParticipantSetup` | `PrepareParticipantsForNewRound` | ✓ `(RoundContext, participant_setup_txn)` | ✓ `rollback_failed` → abort; `rollback_completed(rolled_to_offline)` → W8 decision |
| `RollbackTemplateRefreshSetup` | `TemplateRefresh` | ✓ `(RoundContext, refresh_setup_txn)` | ✓ same |
| `SetupRetryEvent` (seated) | `PrepareParticipantsForNewRound`, `TemplateRefresh` | ✓ `{RoundID, setup_kind, SetupRetryID, setup_retry_generation, reason}` | ✓ dispatched handler applies W8 guards; the seat decision inspects `rb.rolled_to_offline` + generation bound |

## 3. Cross-checks performed

1. **No `transition_record` return.** `ApplyMinerStateTransition`'s RETURNS and every return statement use the
   four-variant W6 union; `transition_record` survives only in the withdrawn-name NOTE prose.
2. **No undefined `creation_failed` test.** All callers test `assignment_creation_failed` / the range constructors'
   `range_*_creation_failed`; a scan finds no unqualified `= creation_failed(` test.
3. **No placeholder rollback envelope.** No `<the setup dispatch_envelope>` / `<the refresh dispatch_envelope>` /
   `<the spec's constructor>` token remains; rollback transitions use `setup_txn.rollback_envelope`.
4. **No illegal rollback edge.** No `ApplyMinerStateTransition(m, WAKING, REGISTERED/RESERVE/LOW_POWER_LISTEN, ...)` or
   `WAKING, setup_txn.prior_states[m]` remains; rollback uses `WAKING -> OFFLINE` (T12) only.
5. **No double wake.** `CommitRecoveryAssignmentPlan` has no `required_wake_operations` `StartWake` loop; each committed
   activation wakes exactly once via its plan-bound constructor.
6. **Signature ↔ RETURNS ↔ call-site agreement** holds for every W-touched procedure; the call graph resolves with
   0 dangling references (`STAGE_01W_PROCEDURE_CALL_GRAPH.md`).

**Result:** for every W-touched procedure, the signature, the RETURNS disposition set, and all call sites agree.
