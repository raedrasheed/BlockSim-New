# Stage 1V — Procedure Call Graph

A static call-graph audit of `STAGE_01_PROTOCOL_PSEUDOCODE.md` at Stage 1V. Every `CALL <Name>` and every
event-scheduled procedure reference (`ScheduleEvent(EQ, ctx, <Name>, ...)`) is resolved against the set of defined
`PROCEDURE`/`FUNCTION` names. This document exists to demonstrate that the Stage-1V edits (V1–V9) introduced **no
dangling reference** and that every procedure is reachable through a legal caller or is a declared driver / event
handler / entry point.

## Inventory

- **Defined procedures/functions:** 81 (`PROCEDURE` ×79, `FUNCTION` ×2 — `outcome_consistent_with_census`,
  `ClassifyRecoveryWork`).
- **Distinct internal call targets:** every `CALL`/scheduled target resolves to one of the 81 definitions.
- **Dangling references:** **0** (a raw scan reports only the English tokens `is` and `this`, which appear in prose
  such as "… this handler" and "… is CLOSED", never as procedure calls).

The count rises from **76** (Stage 1U) to **81** (Stage 1V) through five NEW procedures:

| New procedure | Correction | Role |
|---------------|-----------|------|
| `ReconcilePendingRecoveryWork` | V1 | reconcile in-flight recovery work against the newest final census before seating |
| `ReserveActivateFromPlan` | V4/V5 | plan-bound reserve activation transaction returning actual references |
| `RollbackParticipantSetup` | V8 | executable rollback of a failed participant setup |
| `RollbackTemplateRefreshSetup` | V8 | executable rollback of a failed template-refresh setup |
| `SetupRetryEvent` | V8 | deterministic strictly-later retry of a rolled-back setup |

## Entry points (no internal caller)

Eleven definitions are not invoked by another procedure via `CALL`; each is a run/round driver, a queue-dispatched event
handler, or a pure helper — the legal roots of the call graph:

| Entry point | Kind |
|-------------|------|
| `RunInitialise` | run driver |
| `RunEventLoopToHorizon` | run driver (owns `ProcessEventTime`) |
| `RoundInitialise` | round driver (seated on the queue) |
| `MinerRegister` | registration entry point |
| `ReserveActivate` | ordinary reserve-activation entry point (dispatched) |
| `LeaseExpiry` | queue-dispatched event handler |
| `ActiveHashRateUpdate` | queue-dispatched event handler |
| `AdversarialParticipationChangeEvent` | queue-dispatched event handler |
| `FullRangeExhaustNoSolution` | queue-dispatched event handler |
| `AcceptanceBatchFinalize` | queue-dispatched event handler |
| `outcome_consistent_with_census` | pure helper (referenced by predicate expansion) |

All other 70 procedures are reachable from these roots, either by a direct `CALL` or by being seated on the event queue
through `ScheduleEvent` (e.g. `WakeCompleteEvent`, `RecoveryWorkDueEvent`, `RecoveryCompletionDueEvent`,
`RecoveryAssignmentContinuationDueEvent`, `RecoveryDeadlineEvent`, `SetupRetryEvent`, `HashWorkEvent`,
`CertificateArrival`, `BlockAcceptancePoint`, `RecoveryCompletionDueEvent`), which `ProcessEventTime` later dispatches.

## Highest fan-in targets (shared infrastructure)

| Target | Distinct callers | Note |
|--------|-----------------|------|
| `ScheduleEvent` | 11 | the sole delta-cycle / seat authority (L6) |
| `ApplyMinerStateTransition` | 11 | the sole miner-state mutation hook (F6/S1) |
| `StartWake` | 8 | the sole non-blocking wake transaction (V3) |
| `RoundAbort` | 6 | the sole declared round-abort path |
| `CreatePendingAssignment` | 6 | the shared PENDING constructor (F4) |
| `SetRecoveryDecisionStatus` | 5 | the sole decision-status mutator (R6) |
| `EnterLowPowerListen` | 5 | the sole idle-entry path (K6) |
| `TransitionRoundState` | 4 | the applicability-entry census helper (M2/K7) |

## The `StartWake` caller set (V2/V3/V9)

`StartWake` is the load-bearing procedure of this stage: after V3 it is a transaction returning a structured
disposition, and V9 requires every caller to inspect that disposition. Its **eight** callers, and how each consumes the
result:

| Caller | Context passed (V2) | Disposition handling (V3/V9) |
|--------|--------------------|------------------------------|
| `ReserveActivateFromPlan` | threaded `scheduling_context` | `wake_seated` → `reserve_activation_committed`; failure → close assignment + restore ledgers + `reserve_activation_failed_after_assignment` |
| `CommitRecoveryAssignmentPlan` (redistribution) | threaded `scheduling_context` | `wake_seated` → capture `WakeEventRef` into `created_events`; else → `install_failed_after_mutation` |
| `PrepareParticipantsForNewRound` (4 cases) | `ORDINARY_DISPATCH(dispatch_envelope)` | `wake_seated` → capture into `participant_setup_txn.wakes`; else → set `participant_setup_error` → rollback + liveness |
| `TemplateRefresh` (activation loop) | `ORDINARY_DISPATCH(dispatch_envelope)` | `wake_seated` → `refresh_wake` into `refresh_setup_txn`; else → `refresh_wake_failed` → rollback + liveness |
| `ResumeFromPause` | `ORDINARY_DISPATCH(dispatch_envelope)` | `wake_seated` → `resume_started(..., WakeEventRef)`; else → `resume_wake_failed(reason)` |
| `AdversarialParticipationChangeEvent` (T10 re-entry) | `ORDINARY_DISPATCH(dispatch_envelope)` | returns the `StartWake` disposition as its `participation_change_record` |
| `RangeAssign` | threaded `scheduling_context` | `wake_seated` → `range_assigned(AssignmentID, WakeEventRef, resulting_state)`; failure → close head + restore ledgers + `ASSERT` from_state + `range_assign_wake_failed` |
| `RangeReassign` | threaded `scheduling_context` | `wake_seated` → `range_reassigned(provenance, AssignmentID, WakeEventRef)`; failure → close head + restore ledgers + `ASSERT` from_state + `range_reassign_wake_failed` |

No `StartWake` call site discards the result and none returns a boolean/`AND` composite (V9). `RangeAssign` and
`RangeReassign`, previously the two exceptions (they returned `assignment`/`provenance` and — for `RangeReassign` —
discarded the wake result), are now create-then-wake transactions consistent with the others.

## Recovery-work subgraph (V1/V6/V7)

```
SecurityFloorEvaluate
  ├─ CommitRecoveryCensus
  ├─ ReconcilePendingRecoveryDecisions ─ SetRecoveryDecisionStatus
  ├─ ReconcilePendingRecoveryWork ───── ClassifyRecoveryWork          (V1; V6 classify)
  ├─ ClassifyRecoveryWork                                             (V6)
  ├─ SeatRecoveryWork ───────────────── ScheduleEvent(RecoveryWorkDueEvent)   (V1/V7)
  └─ SeatRecoveryCompletion ─────────── ScheduleEvent(RecoveryCompletionDueEvent)

RecoveryWorkDueEvent ── CaptureSecurityCensusOnRecoveryDeadline       (records DUE)
ApplyRecoveryWorkAfterEpilogue                                        (V7: DUE→APPLYING→CONSUMED)
  ├─ PrepareRecoveryAssignmentPlan
  ├─ CommitRecoveryAssignmentPlan ───── ReserveActivateFromPlan ─ StartWake   (V4/V5)
  │                                └──── RangeReassign / RangeAssign ─ StartWake
  └─ RollbackRecoveryAssignmentPlan                                   (on install_failed_after_mutation)

CancelActiveRecoveryEpisode                                          (V7: cancels ALL nonterminal work records)
  └─ SetRecoveryDecisionStatus
```

## Setup-rollback subgraph (V8)

```
PrepareParticipantsForNewRound
  ├─ CreatePendingAssignment ×N
  ├─ StartWake ×N ───────────── (capture into participant_setup_txn)
  ├─ CompleteAssignmentPhase                       (K2/T5 disposition)
  ├─ RollbackParticipantSetup ── ApplyMinerStateTransition   (restore prior state)
  ├─ ScheduleEvent(SetupRetryEvent)                (liveness: strictly-later retry)
  └─ RoundAbort                                    (liveness: declared abort)

TemplateRefresh
  ├─ CloseTemplateAssignments / TemplateCommit
  ├─ CreatePendingAssignment ×N ; StartWake ×N ── (capture into refresh_setup_txn)
  ├─ CompleteAssignmentPhase
  ├─ RollbackTemplateRefreshSetup ── ApplyMinerStateTransition
  ├─ ScheduleEvent(SetupRetryEvent)
  └─ RoundAbort

SetupRetryEvent ── PrepareParticipantsForNewRound | TemplateRefresh   (re-invoke the setup)
```

## Method

The graph was extracted by scanning the pseudocode for two reference forms — `CALL <Name>` and
`ScheduleEvent(EQ, <ctx>, <Name>, …)` — and resolving each target against the 81 defined `PROCEDURE`/`FUNCTION`
names. A reference that resolves to no definition is a *dangling* reference; the Stage-1V pseudocode has none. The two
false positives (`is`, `this`) are English words following the token `CALL`-adjacent prose and are not procedure
invocations.

**Result: 81 procedures defined; every internal reference resolves; 0 dangling references.**
