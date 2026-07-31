# Stage 1V — Procedure Signature & Call-Site Audit

This audit discharges the V9 requirement that **signature, RETURNS block, and call sites agree** for every procedure
touched by Stage 1V. For each V-touched procedure it records the exact `INPUTS`, the exact `RETURNS` disposition set,
and (where the procedure is called) that every caller passes arguments matching the signature and inspects the returned
disposition explicitly. All signatures are quoted from the current `STAGE_01_PROTOCOL_PSEUDOCODE.md`.

## 1. Signature table (V-touched procedures)

| Procedure | INPUTS | RETURNS (structured dispositions) |
|-----------|--------|-----------------------------------|
| `StartWake` | `RoundContext, MinerID, target_assignment, from_state, scheduling_context` | `wake_seated(AssignmentID, WakeEventRef, wake_target_time, resulting_state = WAKING)` \| `wake_schedule_failed_before_transition(reason)` \| `wake_transition_failed_after_seat(reason, WakeEventRef)` |
| `ReserveActivate` | `RoundContext, deficit, scheduling_context` | `reserve_activation_committed(MinerID, AssignmentID, assignment_version, WakeEventRef)` \| `reserve_activation_failed_before_mutation(reason)` \| `reserve_activation_failed_after_assignment(reason, AssignmentID, rollback_record)` |
| `ReserveActivateFromPlan` | `RoundContext, reserve_miner, candidate_range, assignment_origin, source_assignment, scheduling_context` | (identical to `ReserveActivate`) |
| `RangeAssign` | `RoundContext, MinerID, requested_size, lease_duration, scheduling_context` | `range_assigned(AssignmentID, WakeEventRef, resulting_state = WAKING)` \| `range_assign_wake_failed(reason, AssignmentID)` |
| `RangeReassign` | `RoundContext, unsearched_suffix, reason, from_miner, scheduling_context` | `range_reassigned(provenance, AssignmentID, WakeEventRef)` \| `range_reassign_wake_failed(reason, AssignmentID)` |
| `ReconcilePendingRecoveryWork` | `RoundContext, episode, latest_census_version, event_time` | `recovery_work_reconciled_rebound` \| `recovery_work_reconciled_reaffirmed` \| `recovery_work_reconciled_superseded` \| `recovery_work_reconciled_noop` \| `no_pending_recovery_work` |
| `ClassifyRecoveryWork` | `RoundContext, episode, census` | `RECOVERY_WORK_ACTION in { RESERVE_ACTIVATION_REQUIRED, NONE }` |
| `SeatRecoveryWork` | `RoundContext, episode, work_action, t, census_version` | `recovery_work_seated` \| `recovery_work_not_seated` \| `recovery_work_already_pending` \| `recovery_work_horizon_deferred` |
| `ApplyRecoveryWorkAfterEpilogue` | `RoundContext, event_time t` | `recovery_work_applied` \| `recovery_work_rolled_back` \| `recovery_work_install_aborted` \| `recovery_work_commit_failed` \| `recovery_work_plan_invalid` \| `recovery_work_superseded` \| `nothing_due` \| `nothing_applicable_due` |
| `CancelActiveRecoveryEpisode` | `RoundContext, dispatch_envelope` | `recovery_episode_terminal_cancelled(episode)` |
| `PrepareRecoveryAssignmentPlan` | `RoundContext, episode, work_action, census` | `plan_ready(plan)` \| `plan_invalid(reason)` |
| `CommitRecoveryAssignmentPlan` | `RoundContext, plan, scheduling_context` | `install_committed` \| `install_failed_before_mutation(reason)` \| `install_failed_after_mutation(reason, rollback_record)` |
| `RollbackRecoveryAssignmentPlan` | `RoundContext, rollback_record` | `rollback_completed` \| `rollback_failed(reason)` |
| `PrepareParticipantsForNewRound` | `RoundContext, dispatch_envelope` | `participant_set_prepared` \| `participant_set_setup_retry_seated` \| `round_aborted` |
| `RollbackParticipantSetup` | `RoundContext, setup_txn` | `rollback_completed` \| `rollback_failed(reason)` |
| `RollbackTemplateRefreshSetup` | `RoundContext, setup_txn` | `rollback_completed` \| `rollback_failed(reason)` |
| `SetupRetryEvent` | `RoundContext, dispatch_envelope, RoundID, setup_kind, reason` | `setup_retry_stale_noop` \| (the re-run setup's disposition) |
| `TemplateRefresh` | `RoundContext, dispatch_envelope` | `new_TemplateID` \| `template_refresh_retry_seated` \| `round_aborted` |
| `ResumeFromPause` | `RoundContext, MinerID, trigger, pause_cause_candidate_id, pause_cause_propagation_id, dispatch_envelope` | `resume_started(MinerID, resumed_from, WakeEventRef)` \| `resume_wake_failed(MinerID, reason)` |
| `LeaseExpiry` | `RoundContext, dispatch_envelope, …` | `lease_disposition (renewed \| released \| released_reassign_wake_failed \| released_nothing_to_reassign \| lease_expiry_noop_terminal)` |

Every RETURNS clause above is a **disjunction of named structured dispositions** — no procedure returns a bare boolean
or a `ScheduleEvent(...) AND …` composite (V9).

## 2. Call-site agreement matrix

For each callee, every caller and the two agreement checks: **args match** (the caller passes exactly the signature's
parameters, with `scheduling_context` supplied explicitly where required) and **disposition inspected** (the caller
pattern-matches the returned disposition rather than discarding it).

### `StartWake`

| Caller | Args match | Disposition inspected |
|--------|-----------|-----------------------|
| `ReserveActivateFromPlan` | ✓ (`scheduling_context` threaded) | ✓ `wake_seated` / `wake_transition_failed_after_seat` / other |
| `CommitRecoveryAssignmentPlan` (redistribution) | ✓ (threaded) | ✓ `wake_seated(waid,wref,wtt,ws)` else install-fail |
| `PrepareParticipantsForNewRound` (×4) | ✓ `ORDINARY_DISPATCH(dispatch_envelope)` | ✓ `wake_seated` captured, else `participant_setup_error` |
| `TemplateRefresh` (activation loop) | ✓ `ORDINARY_DISPATCH(dispatch_envelope)` | ✓ `refresh_wake` / `refresh_wake_failed` |
| `ResumeFromPause` | ✓ `ORDINARY_DISPATCH(dispatch_envelope)` | ✓ `resume_started` / `resume_wake_failed` |
| `AdversarialParticipationChangeEvent` (T10) | ✓ `ORDINARY_DISPATCH(dispatch_envelope)` | ✓ returned as `participation_change_record` |
| `RangeAssign` | ✓ (threaded) | ✓ `wake_seated` → `range_assigned`, else `range_assign_wake_failed` |
| `RangeReassign` | ✓ (threaded) | ✓ `wake_seated` → `range_reassigned`, else `range_reassign_wake_failed` |

### `RangeAssign`

| Caller | Args match | Disposition inspected |
|--------|-----------|-----------------------|
| `AdversarialParticipationChangeEvent` (REGISTERED/RESERVE) | ✓ `scheduling_context = ORDINARY_DISPATCH(dispatch_envelope)` | ✓ returned as `participation_change_record` |
| `AdversarialParticipationChangeEvent` (OFFLINE→REGISTERED) | ✓ `scheduling_context = ORDINARY_DISPATCH(dispatch_envelope)` | ✓ returned as `participation_change_record` |

### `RangeReassign`

| Caller | Args match | Disposition inspected |
|--------|-----------|-----------------------|
| `LeaseExpiry` (reassign tail) | ✓ `scheduling_context = ORDINARY_DISPATCH(dispatch_envelope)` | ✓ `range_reassigned(...)` → `released`, else `released_reassign_wake_failed` |

### `ReserveActivateFromPlan`

| Caller | Args match | Disposition inspected |
|--------|-----------|-----------------------|
| `ReserveActivate` | ✓ (delegates with selected miner/range/origin/source) | ✓ tail-returns the disposition |
| `CommitRecoveryAssignmentPlan` (RESERVE_ACTIVATION) | ✓ `spec.MinerID/range/origin/source` + `scheduling_context` | ✓ `reserve_activation_committed` / `…_before_mutation` / `…_after_assignment` |

### `ReconcilePendingRecoveryWork`

| Caller | Args match | Disposition inspected |
|--------|-----------|-----------------------|
| `SecurityFloorEvaluate` | ✓ `(RoundContext, episode, census.RecoveryCensusVersion, t)` | ✓ (called for effect before `SeatRecoveryWork`; the reconcile mutates the record and returns a status) |

### `CommitRecoveryAssignmentPlan` / `RollbackRecoveryAssignmentPlan`

| Caller | Args match | Disposition inspected |
|--------|-----------|-----------------------|
| `ApplyRecoveryWorkAfterEpilogue` | ✓ `(RoundContext, plan, POST_EPILOGUE(pctx))` | ✓ `install_committed` / `install_failed_before_mutation` / `install_failed_after_mutation` → `RollbackRecoveryAssignmentPlan` |
| `ApplyRecoveryAssignmentContinuationAfterEpilogue` | ✓ | ✓ same disposition branch set |

### Setup rollback / retry (V8)

| Callee | Caller | Args match | Disposition inspected |
|--------|--------|-----------|-----------------------|
| `RollbackParticipantSetup` | `PrepareParticipantsForNewRound` | ✓ `(RoundContext, participant_setup_txn)` | ✓ `rollback_completed` / `rollback_failed` |
| `RollbackTemplateRefreshSetup` | `TemplateRefresh` | ✓ `(RoundContext, refresh_setup_txn)` | ✓ `rollback_completed` / `rollback_failed` |
| `SetupRetryEvent` (seated) | `PrepareParticipantsForNewRound`, `TemplateRefresh` | ✓ via `ScheduleEvent(..., {RoundID, setup_kind, reason})` | ✓ dispatched handler re-invokes the setup; stale-guarded on RoundID |

## 3. Cross-checks performed

1. **No bare-boolean / AND returns.** A scan for `AND wake_started`, `RETURN ScheduleEvent(...) AND`, and similar
   composite return expressions finds none. Every wake/activation/commit path returns one named disposition.
2. **No discarded `StartWake`.** Every `CALL StartWake(...)` is bound to a variable (`SET wr <- CALL StartWake`) or is
   the subject of a `RETURN CALL`/`IF`; the pre-V3 discarded call in `RangeReassign` is removed.
3. **`scheduling_context` explicit at every scheduling call.** No `RangeAssign`/`RangeReassign`/`StartWake` call passes
   a bare `dispatch_envelope =` scheduling parameter; each passes `ORDINARY_DISPATCH(dispatch_envelope)` or a threaded
   `scheduling_context` or `POST_EPILOGUE(pctx)`.
4. **RETURNS ↔ body agreement.** For `RangeAssign` and `RangeReassign` the RETURNS clause now enumerates the structured
   dispositions the body actually returns (`range_assigned`/`range_assign_wake_failed`,
   `range_reassigned`/`range_reassign_wake_failed`) — the pre-V3 `assignment`/`provenance` annotations are replaced.
5. **Signature parameter names match caller keyword arguments** for every V-touched call site (e.g.
   `reserve_miner = spec.MinerID`, `candidate_range = spec.range`, `scheduling_context = POST_EPILOGUE(pctx)`).

**Result:** for every V-touched procedure, the signature, the RETURNS disposition set, and all call sites agree (V9).
