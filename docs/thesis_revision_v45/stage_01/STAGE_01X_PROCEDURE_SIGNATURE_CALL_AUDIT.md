# Stage 1X — Procedure Signature & Call-Site Audit

This audit records, for every procedure touched by Stage 1X, the exact `INPUTS`, the exact `RETURNS` disposition set,
and (where called) that every caller passes arguments matching the signature and inspects the returned disposition
explicitly before acting on it. All signatures are quoted from the current `STAGE_01_PROTOCOL_PSEUDOCODE.md` (line
anchors approximate).

## 1. Signature table (X-touched procedures)

| Procedure | INPUTS | RETURNS (declared result set) |
|-----------|--------|-------------------------------|
| `CreatePendingAssignment` (X6) | `RoundContext, MinerID, range, assignment_origin, source_assignment, reason` | `assignment_created(assignment)` \| `assignment_creation_failed(reason)` |
| `CommitRecoveryAssignmentPlan` (X1/X5) | `RoundContext, plan, scheduling_context` | `install_committed(rollback_record)` \| `install_failed_before_mutation(reason)` \| `install_failed_after_mutation(reason, rollback_record)` |
| `RollbackRecoveryAssignmentPlan` (X1/X2/X7/X8) | `RoundContext, rollback_record` *(= `{ RecoveryInstallID, items:[rollback_item] }`)* | `rollback_completed(rolled_to_offline, rolled_back_items)` \| `rollback_failed(reason)` |
| `RollbackParticipantSetup` (X2/X7) | `RoundContext, setup_txn` *(with `rollback_envelope`, `assignment_by_miner`)* | `rollback_completed(rolled_to_offline)` \| `rollback_failed(reason)` |
| `RollbackTemplateRefreshSetup` (X2/X7) | `RoundContext, setup_txn` *(with `rollback_envelope`, `assignment_by_miner`)* | `rollback_completed(rolled_to_offline)` \| `rollback_failed(reason)` |
| `SetupRetryEvent` (X4) | `RoundContext, dispatch_envelope, RoundID, setup_kind, SetupRetryID, setup_retry_generation, reason` | `setup_retry_stale_noop` \| `setup_retry_terminal_stale_noop` \| `setup_retry_duplicate_suppressed` \| `round_aborted` \| *(the re-run target's disposition)* |
| `TemplateRefresh` (X3) | `RoundContext, dispatch_envelope` | `new_TemplateID` \| `template_refresh_retry_seated` \| `round_aborted` *(propagates the continuation's disposition)* |
| `ContinueTemplateRefreshAssignmentSetup` (X3, new) | `RoundContext, dispatch_envelope, TemplateID, SetupRetryID, setup_retry_generation` | `TemplateID` \| `template_refresh_retry_seated` \| `round_aborted` |
| `ApplyMinerStateTransition` (used by X1/X2 T12) | `MinerID, old_state, new_state, transition_envelope, reason, assignment_ref, candidate_id, propagation_id` | `transition_applied(TransitionEventID)` \| `duplicate_suppressed(TransitionEventID)` \| `illegal_stale_source(TransitionEventID)` \| `illegal_transition(TransitionEventID)` |
| `ReserveActivateFromPlan` (X7 closure) | `RoundContext, reserve_miner, candidate_range, assignment_origin, source_assignment, scheduling_context` | `reserve_activation_committed(MinerID, AssignmentID, assignment_version, WakeEventRef)` \| `reserve_activation_failed_before_mutation(reason)` \| `reserve_activation_failed_after_assignment(reason, AssignmentID, rollback_record)` |
| `RangeAssignFromPlan` (X7 closure) | `RoundContext, MinerID, range, assignment_origin, source_assignment, reassignment_reason, lease_duration, scheduling_context` | `range_assigned(AssignmentID, WakeEventRef, resulting_state = WAKING)` \| `range_assign_creation_failed(reason)` \| `range_assign_wake_failed(reason, AssignmentID)` |
| `RangeReassignFromPlan` (X7 closure) | `RoundContext, MinerID, range, assignment_origin, source_assignment, reassignment_reason, lease_duration, scheduling_context` | `range_reassigned(provenance, AssignmentID, WakeEventRef)` \| `range_reassign_creation_failed(reason)` \| `range_reassign_wake_failed(reason, AssignmentID)` |

**Signature changes introduced by Stage 1X:**
- `RollbackRecoveryAssignmentPlan` INPUT changed from `(RoundContext, plan)` to `(RoundContext, rollback_record)` and
  its success disposition gained `rolled_back_items` (X1/X5).
- `install_committed` gained a `rollback_record` payload (X5).
- `TemplateRefresh` delegates and now propagates `ContinueTemplateRefreshAssignmentSetup`'s disposition (X3); the new
  `ContinueTemplateRefreshAssignmentSetup` procedure is added.
- `SetupRetryEvent` gained the `setup_retry_terminal_stale_noop` variant and replaced the bare over-budget
  `setup_retry_exhausted` with a declared `round_aborted` (X4).
- `CreatePendingAssignment` PRECONDITIONS reduced to a type/shape prerequisite; RETURNS unchanged (X6).

## 2. Call-site agreement matrix

For each callee, every caller and the two checks: **args match** (the caller passes exactly the signature's
parameters) and **result inspected** (the caller branches on the declared disposition before acting).

### `CommitRecoveryAssignmentPlan` (X1/X5)

| Caller | Args match | Result inspected |
|--------|-----------|------------------|
| `ApplyRecoveryWorkAfterEpilogue` | ✓ `(RoundContext, plan, scheduling_context = POST_EPILOGUE(pctx))` | ✓ branches `install_committed(rollback_record)` / `install_failed_before_mutation` / `install_failed_after_mutation(reason, rollback_record)`; captures `commit.rollback_record` |
| `ApplyRecoveryAssignmentContinuationAfterEpilogue` | ✓ same | ✓ same; sets `commit_rollback_record <- commit.rollback_record` for a later CompleteAssignmentPhase-fail rollback |

### `RollbackRecoveryAssignmentPlan` (X1)

| Caller | Args match | Result inspected |
|--------|-----------|------------------|
| `ApplyRecoveryWorkAfterEpilogue` (install_failed_after_mutation) | ✓ `(RoundContext, rollback_record)` | ✓ `rollback_completed(rolled_to_offline, rolled_back_items)` → continue; `rollback_failed` → RECOVERY_INSTALL_FAILED_ABORTED / RoundAbort |
| `ApplyRecoveryAssignmentContinuationAfterEpilogue` (install_failed_after_mutation) | ✓ same | ✓ same |
| `ApplyRecoveryAssignmentContinuationAfterEpilogue` (post-`CompleteAssignmentPhase` fail) | ✓ `(RoundContext, commit_rollback_record)` | ✓ same |

### `RollbackParticipantSetup` / `RollbackTemplateRefreshSetup` (X2/X7)

| Callee | Caller | Args match | Result inspected |
|--------|--------|-----------|------------------|
| `RollbackParticipantSetup` | `PrepareParticipantsForNewRound` | ✓ `(RoundContext, participant_setup_txn)` *(carries `assignment_by_miner`)* | ✓ `rollback_failed` → abort; `rollback_completed(rolled_to_offline)` → W8 retry/abort decision |
| `RollbackTemplateRefreshSetup` | `ContinueTemplateRefreshAssignmentSetup` | ✓ `(RoundContext, refresh_setup_txn)` *(carries `assignment_by_miner`)* | ✓ same |

### `ContinueTemplateRefreshAssignmentSetup` (X3)

| Caller | Args match | Result inspected |
|--------|-----------|------------------|
| `TemplateRefresh` | ✓ `(RoundContext, dispatch_envelope, TemplateID = new_TemplateID, SetupRetryID = null, setup_retry_generation = 0)` | ✓ `RETURN CALL` — its disposition IS `TemplateRefresh`'s return |
| `SetupRetryEvent` (TEMPLATE_REFRESH_SETUP) | ✓ `(RoundContext, dispatch_envelope, TemplateID = TemplateID_committed, SetupRetryID, setup_retry_generation)` | ✓ `RETURN CALL` — its disposition IS the event's return |

### `SetupRetryEvent` (X4) — dispatched targets

| Target | Args match | Result inspected |
|--------|-----------|------------------|
| `PrepareParticipantsForNewRound` (PARTICIPANT_SETUP) | ✓ `(RoundContext, dispatch_envelope)` after ASSERT committed eligible TemplateID | ✓ `RETURN CALL` — target's disposition propagates |
| `ContinueTemplateRefreshAssignmentSetup` (TEMPLATE_REFRESH_SETUP) | ✓ after ASSERT TemplateID_committed = refresh setup's + marker present | ✓ `RETURN CALL` — target's disposition propagates |
| `RoundAbort` (wrong-state / budget / state-incompatible) | ✓ `(RoundContext, reason, dispatch_envelope, recovery_finalising = false)` | ✓ declared abort return |

### `CreatePendingAssignment` (X6) — 6 callers

| Caller | Args match | Result inspected (before any AssignmentID/lease/txn access) |
|--------|-----------|-----------------------------------------------------------|
| `PrepareParticipantsForNewRound` | ✓ | ✓ `IF cr is assignment_creation_failed(reason): ... CONTINUE` |
| `ContinueTemplateRefreshAssignmentSetup` | ✓ | ✓ `IF cr is assignment_creation_failed(reason): refresh_setup_error <- ... ; CONTINUE` |
| `RangeAssignFromPlan` | ✓ | ✓ `RETURN range_assign_creation_failed(reason)` |
| `RangeReassignFromPlan` | ✓ | ✓ `RETURN range_reassign_creation_failed(reason)` |
| `ReserveActivateFromPlan` | ✓ | ✓ `RETURN reserve_activation_failed_before_mutation(reason)` |
| `AdversarialParticipationChangeEvent` | ✓ | ✓ branches before reading `AssignmentID` |

### `ApplyMinerStateTransition` — Stage-1X T12 rollback callers

| Caller | Args match | Result inspected |
|--------|-----------|------------------|
| `RollbackRecoveryAssignmentPlan` | ✓ `(item.MinerID, WAKING, OFFLINE, transition_envelope = item.rollback_envelope, reason = cancellation, assignment_ref = assignment_version_ref(item.AssignmentID, item.assignment_version), null, null)` | ✓ `IF tr is transition_applied(teid): rolled_to_offline <- true` |
| `RollbackParticipantSetup` / `RollbackTemplateRefreshSetup` | ✓ `(m, WAKING, OFFLINE, transition_envelope = setup_txn.rollback_envelope, reason = cancellation, assignment_ref = assignment_version_ref(aid, ver), null, null)` | ✓ same |

## 3. Cross-checks performed

1. **`install_committed` carries the record.** The RETURNS block and the success `RETURN` both read
   `install_committed(rollback_record)`; no bare `install_committed` survives (X5).
2. **Rollback input is the record, not the plan.** `RollbackRecoveryAssignmentPlan` INPUTS is `rollback_record`; every
   caller passes the record returned by `install_committed` / `install_failed_after_mutation`, never
   `plan.rollback_metadata` (X5) — a corpus scan finds `rollback_metadata` only in withdrawn-name comments.
3. **T12 only, exact version.** Every Stage-1X rollback transition passes `WAKING, OFFLINE` with
   `assignment_version_ref(...)` (never null when a head is held); no illegal `WAKING -> REGISTERED/RESERVE/LOW_POWER_LISTEN`
   edge appears (X1/X2).
4. **Retry never re-enters TemplateRefresh.** `SetupRetryEvent`'s TEMPLATE_REFRESH_SETUP branch calls
   `ContinueTemplateRefreshAssignmentSetup`; no `CALL TemplateRefresh` exists inside `SetupRetryEvent` (X3).
5. **Over-budget aborts.** `SetupRetryEvent` returns `RoundAbort(setup_retry_budget_exhausted)` for an over-budget
   retry (no bare `setup_retry_exhausted`), with the terminal case handled first (X4).
6. **Canonical closures.** Every `FromPlan`/rollback closure sets canonical enum fields + `closure_detail` (X7).
7. **Signature ↔ RETURNS ↔ call-site agreement** holds for every X-touched procedure; the call graph resolves with
   0 dangling references and 84 defined procedures (`STAGE_01X_PROCEDURE_CALL_GRAPH.md`).

**Result:** for every X-touched procedure, the signature, the RETURNS disposition set, and all call sites agree.
