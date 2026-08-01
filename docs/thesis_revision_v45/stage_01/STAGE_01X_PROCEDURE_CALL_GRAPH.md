# Stage 1X — Procedure Call Graph

This document resolves the procedure call graph of `STAGE_01_PROTOCOL_PSEUDOCODE.md` after corrections X1–X8 and
records that it contains NO dangling call. The Stage-1X change adds ONE procedure —
`ContinueTemplateRefreshAssignmentSetup` (X3) — raising the defined count from 83 (Stage 1W) to **84**.

## 1. Resolution method

- **Defined symbols:** every `^PROCEDURE <name>` / `^FUNCTION <name>` header (84 unique names).
- **Call targets:** every `CALL <name>` invocation target.
- **Dispatched handlers:** event handlers are seated via `ScheduleEvent(EQ, RoundContext, <Handler>, ...)` and
  dispatched by `ProcessEventTime`, not via `CALL`; they are defined procedures reached through the queue (e.g.
  `SetupRetryEvent`, `WakeCompleteEvent`, `LeaseExpiry`, `RecoveryWorkDueEvent`), so a defined handler with no `CALL`
  site is NOT dangling.
- **Dangling test:** `{ call targets } \ { defined symbols }`. The only tokens the raw scan surfaces are `is` and
  `this`, from prose fragments (`"the CALL is not guarded"`, `"CALL this writer"`, `"CALL this rather than writing"`),
  not invocations. **Real dangling calls = 0.**

## 2. Defined-procedure inventory (84)

`AcceptanceBatchFinalize`, `ActiveHashRateUpdate`, `ActualRangeCompletion`, `AdversarialParticipationChangeEvent`,
`ApplyMinerStateTransition`, `ApplyRecoveryAssignmentContinuationAfterEpilogue`, `ApplyRecoveryCompletionAfterEpilogue`,
`ApplyRecoveryWorkAfterEpilogue`, `BlockAcceptancePoint`, `CancelActiveRecoveryEpisode`,
`CaptureSecurityCensusOnApplicabilityEntry`, `CaptureSecurityCensusOnRecoveryDeadline`, `CertificateArrival`,
`ClassifyRecoveryWork`, `CloseRoundAssignments`, `CloseRoundAtHorizon`, `CloseTemplateAssignments`,
`CommitRecoveryAssignmentPlan`, `CommitRecoveryCensus`, `CommitSecurityCensus`, `CompleteAssignmentPhase`,
`CompleteSecurityRecovery`, **`ContinueTemplateRefreshAssignmentSetup`** (X3, new), `CreatePendingAssignment`,
`CreatePropagationContext`, `CreateSolutionEligibilitySnapshot`, `EarlyStopGenerate`, `EarlyStopVerify`,
`EnterLowPowerListen`, `ExhaustionAdjudicate`, `FinalizeEventTimeSecurityCensus`,
`FinalizePostRecoveryApplicationState`, `FinalizeSimulationRun`, `FullRangeExhaustNoSolution`,
`HandlePropagationFailure`, `HashWorkEvent`, `LeaseExpiry`, `MinerRegister`, `PrepareParticipantsForNewRound`,
`PrepareRecoveryAssignmentPlan`, `ProcessEventTime`, `ProgressCommit`, `RangeAssign`, `RangeAssignFromPlan`,
`RangeReassign`, `RangeReassignFromPlan`, `ReconcilePendingRecoveryDecisions`, `ReconcilePendingRecoveryWork`,
`RecoveryAssignmentContinuationDueEvent`, `RecoveryCompletionDueEvent`, `RecoveryDeadlineEvent`,
`RecoveryWorkDueEvent`, `RenewAssignment`, `ReportedExhaustionClaim`, `ReserveActivate`, `ReserveActivateFromPlan`,
`ResumeFromPause`, `RollbackParticipantSetup`, `RollbackRecoveryAssignmentPlan`, `RollbackTemplateRefreshSetup`,
`RoundAbort`, `RoundInitialise`, `RunEventLoopToHorizon`, `RunInitialise`, `ScheduleEvent`, `ScheduleNextHashWork`,
`ScheduleSolutionPropagation`, `SeatRecoveryCompletion`, `SeatRecoveryWork`, `SecurityFloorEvaluate`,
`SelfValidateFoundSolution`, `SetRecoveryDecisionStatus`, `SettleResidencyBoundary`, `SettleSecurityCensusDirty`,
`SetupRetryEvent`, `StartHashing`, `StartWake`, `TemplateCommit`, `TemplateRefresh`, `TransitionRoundState`,
`ValidBlockAccept`, `ValidateCandidate`, `WakeCompleteEvent`, `outcome_consistent_with_census`.

## 3. X-touched call edges (caller → callee)

The Stage-1X corrections change the edges around the recovery-install, setup-rollback, and template-refresh subgraphs.
Each edge below is grounded at its call site in `STAGE_01_PROTOCOL_PSEUDOCODE.md`.

### 3.1 `ContinueTemplateRefreshAssignmentSetup` (X3, new node)

| Direction | Edge | Site |
|-----------|------|------|
| in  | `TemplateRefresh` → `ContinueTemplateRefreshAssignmentSetup` | initial call, `SetupRetryID = null`, generation 0 (§19, ~L4734) |
| in  | `SetupRetryEvent` (TEMPLATE_REFRESH_SETUP) → `ContinueTemplateRefreshAssignmentSetup` | retry resume, bounded generation (§2, ~L1787) |
| out | → `CreatePendingAssignment` | per-eligible-miner head creation (~L4764) |
| out | → `StartWake` | per-head wake (~L4774) |
| out | → `CompleteAssignmentPhase` | ASSIGNMENT → HASHING (~L4785) |
| out | → `RollbackTemplateRefreshSetup` | on setup failure (~L4789) |
| out | → `RoundAbort` | rollback-failed / state-incompatible / retries-exhausted / declared abort |
| out | → `ScheduleEvent(SetupRetryEvent, TEMPLATE_REFRESH_SETUP)` | bounded W8 retry seat (~L4804) |

`ContinueTemplateRefreshAssignmentSetup` has 1 definition and **2 call sites** — both reached; no dangling reference.
`TemplateRefresh` no longer calls `CreatePendingAssignment` / `StartWake` / `CompleteAssignmentPhase` directly (those
edges migrated to the continuation, X3).

### 3.2 `CommitRecoveryAssignmentPlan` (X1/X5)

| Direction | Edge | Site |
|-----------|------|------|
| in  | `ApplyRecoveryWorkAfterEpilogue` → `CommitRecoveryAssignmentPlan` | POST_EPILOGUE(pctx) (~L3020) |
| in  | `ApplyRecoveryAssignmentContinuationAfterEpilogue` → `CommitRecoveryAssignmentPlan` | POST_EPILOGUE(pctx) (~L3498) |
| out | → `ReserveActivateFromPlan` | RESERVE_ACTIVATION spec (~L3632) |
| out | → `RangeAssignFromPlan` / `RangeReassignFromPlan` | REDISTRIBUTION spec by origin (~L3653/3658) |

Returns `install_committed(rollback_record)` — the caller captures `commit.rollback_record` (X5).

### 3.3 `RollbackRecoveryAssignmentPlan` (X1/X2/X7/X8)

| Direction | Edge | Site |
|-----------|------|------|
| in  | `ApplyRecoveryWorkAfterEpilogue` → `RollbackRecoveryAssignmentPlan` | install_failed_after_mutation (~L3027) |
| in  | `ApplyRecoveryAssignmentContinuationAfterEpilogue` → `RollbackRecoveryAssignmentPlan` | install_failed_after_mutation (~L3508) |
| in  | `ApplyRecoveryAssignmentContinuationAfterEpilogue` → `RollbackRecoveryAssignmentPlan` | post-`CompleteAssignmentPhase` fail, using `commit_rollback_record` (~L3541) |
| out | → `ApplyMinerStateTransition` | legal `T12` WAKING → OFFLINE per item (~L3712) |

3 in-edges (all capture the explicit `rollback_record`), 1 out-edge to the transition hook.

### 3.4 `RollbackParticipantSetup` / `RollbackTemplateRefreshSetup` (X2/X7)

| Direction | Edge | Site |
|-----------|------|------|
| in  | `PrepareParticipantsForNewRound` → `RollbackParticipantSetup` | on setup failure (~L1640) |
| in  | `ContinueTemplateRefreshAssignmentSetup` → `RollbackTemplateRefreshSetup` | on setup failure (~L4789) |
| out | each → `ApplyMinerStateTransition` | legal `T12` with `assignment_version_ref` from `assignment_by_miner` |

### 3.5 `SetupRetryEvent` (X4, dispatched handler)

| Direction | Edge | Site |
|-----------|------|------|
| in  | `ScheduleEvent(SetupRetryEvent, ...)` from `PrepareParticipantsForNewRound` and `ContinueTemplateRefreshAssignmentSetup` | queue-seated, not `CALL` |
| out | → `PrepareParticipantsForNewRound` | PARTICIPANT_SETUP (~L1781) |
| out | → `ContinueTemplateRefreshAssignmentSetup` | TEMPLATE_REFRESH_SETUP (~L1787) |
| out | → `RoundAbort` | wrong-round-state / budget-exhausted / state-incompatible |

`SetupRetryEvent` is reached only through the queue (X4); a defined handler with no `CALL` site is not dangling.

### 3.6 `CreatePendingAssignment` (X6) — 6 callers

`PrepareParticipantsForNewRound` (~L1615), `RangeAssignFromPlan` (~L1935),
`AdversarialParticipationChangeEvent` (~L2351), `ReserveActivateFromPlan` (~L3109), `RangeReassignFromPlan` (~L3972),
`ContinueTemplateRefreshAssignmentSetup` (~L4764). Each branches on `assignment_created` / `assignment_creation_failed`
before reading `AssignmentID`. (The former direct `TemplateRefresh` caller migrated to the continuation, X3.)

## 4. Result

The Stage-1X call graph resolves with **84 defined procedures and 0 dangling calls**. The new
`ContinueTemplateRefreshAssignmentSetup` is defined once and reached from exactly two call sites (`TemplateRefresh`,
`SetupRetryEvent`); the recovery-install rollback, setup rollback, and template-refresh subgraphs are fully connected;
and every dispatched handler (including `SetupRetryEvent`) is reachable through `ScheduleEvent` / `ProcessEventTime`.
