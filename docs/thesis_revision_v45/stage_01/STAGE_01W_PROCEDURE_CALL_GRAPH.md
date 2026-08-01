# Stage 1W — Procedure Call Graph

A static call-graph audit of `STAGE_01_PROTOCOL_PSEUDOCODE.md` at Stage 1W. Every `CALL <Name>` and every
event-scheduled procedure reference (`ScheduleEvent(EQ, ctx, <Name>, ...)`) is resolved against the set of defined
`PROCEDURE`/`FUNCTION` names. This document demonstrates that the Stage-1W edits (W1–W8) introduced **no dangling
reference** and that every procedure is reachable through a legal caller or is a declared driver / event handler /
entry point.

## Inventory

- **Defined procedures/functions:** 83 (`PROCEDURE` ×81, `FUNCTION` ×2 — `outcome_consistent_with_census`,
  `ClassifyRecoveryWork`).
- **Dangling references:** **0** (a raw scan reports only the English tokens `is` and `this`, never procedure calls).

The count rises from **81** (Stage 1V) to **83** (Stage 1W) through two NEW plan-bound range constructors:

| New procedure | Correction | Role |
|---------------|-----------|------|
| `RangeAssignFromPlan` | W5 | plan-bound create-then-wake ORIGINAL assignment (exact values, no SELECT) |
| `RangeReassignFromPlan` | W5 | plan-bound create-then-wake REASSIGNED assignment (exact values, no SELECT) |

## Entry points (no internal caller)

Eleven definitions are not invoked by another procedure via `CALL`; each is a run/round driver, a queue-dispatched
event handler, or a pure helper — the legal roots of the call graph:

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

All other 72 procedures are reachable from these roots, either by a direct `CALL` or by being seated on the event
queue through `ScheduleEvent` (e.g. `WakeCompleteEvent`, `SetupRetryEvent`, `RecoveryWorkDueEvent`,
`RecoveryCompletionDueEvent`, `RecoveryAssignmentContinuationDueEvent`, `RecoveryDeadlineEvent`, `HashWorkEvent`,
`CertificateArrival`, `BlockAcceptancePoint`), which `ProcessEventTime` later dispatches.

## Highest fan-in targets (shared infrastructure)

| Target | Distinct callers | Note |
|--------|-----------------|------|
| `ScheduleEvent` | 11 | the sole delta-cycle / seat authority (L6) |
| `ApplyMinerStateTransition` | 11 | the sole miner-state mutation hook (F6/S1); W6 result union |
| `StartWake` | 7 | the sole non-blocking wake transaction (V3) |
| `RoundAbort` | 7 | the sole declared round-abort path |
| `CreatePendingAssignment` | 6 | the shared PENDING constructor (F4); W7 result union |
| `SetRecoveryDecisionStatus` | 5 | the sole decision-status mutator (R6) |
| `EnterLowPowerListen` | 5 | the sole idle-entry path (K6) |
| `TransitionRoundState` | 4 | the applicability-entry census helper (M2/K7) |

`StartWake`'s fan-in drops from 8 (Stage 1V) to 7 because `CommitRecoveryAssignmentPlan` no longer calls `StartWake`
directly — its REDISTRIBUTION branch now calls the plan-bound `RangeReassignFromPlan` / `RangeAssignFromPlan`, each of
which performs the single wake internally (W4: no double wake).

## The create-then-wake constructor chain (W4/W5/W6/W7)

Every reserve/range activation is a create-then-wake transaction: `CreatePendingAssignment` (W7 result) → `StartWake`
(V3 transaction) → `ApplyMinerStateTransition` (W6 result). The plan-bound constructors and the commit path:

```
CommitRecoveryAssignmentPlan
  ├─ RESERVE_ACTIVATION spec ── ReserveActivateFromPlan ── CreatePendingAssignment (W7)
  │                                                    └── StartWake ── ApplyMinerStateTransition (W6)
  └─ REDISTRIBUTION spec ────── RangeReassignFromPlan / RangeAssignFromPlan (W5, by spec.origin)
                                        ├─ CreatePendingAssignment (W7)
                                        └─ StartWake ── ApplyMinerStateTransition (W6)
     (W4: the commit captures the returned AssignmentID + WakeEventRef; it never seats a second StartWake)

RangeAssign  (ordinary) ── SELECT ── RangeAssignFromPlan          (W5 delegation)
RangeReassign(ordinary) ── SELECT ── RangeReassignFromPlan        (W5 delegation)
```

## The setup rollback + retry subgraph (W1/W2/W3/W8)

```
PrepareParticipantsForNewRound
  ├─ CreatePendingAssignment (W7 branch) ; StartWake (per miner) ── (capture into participant_setup_txn, W1 rollback_envelope)
  ├─ CompleteAssignmentPhase                              (K2/T5 disposition)
  ├─ RollbackParticipantSetup ── ApplyMinerStateTransition (WAKING -> OFFLINE, T12; W2) ; reports rolled_to_offline
  ├─ ScheduleEvent(SetupRetryEvent)                       (W8: bounded, state-compatible, SetupRetryID)
  └─ RoundAbort                                           (W8: rolled_to_offline / exhausted / past-horizon)

TemplateRefresh
  ├─ CreatePendingAssignment (W7 branch) ; StartWake      ── (in-loop capture into refresh_setup_txn, W1/W3)
  ├─ CompleteAssignmentPhase                              (only if refresh_setup_error = null)
  ├─ RollbackTemplateRefreshSetup ── ApplyMinerStateTransition (T12; W2)
  ├─ ScheduleEvent(SetupRetryEvent)                       (W8)
  └─ RoundAbort                                           (W8)

SetupRetryEvent ── (W8 stale/idempotence/bound/state-compat guards) ── PrepareParticipantsForNewRound | TemplateRefresh
```

## Method

The graph was extracted by scanning the pseudocode for two reference forms — `CALL <Name>` and
`ScheduleEvent(EQ, <ctx>, <Name>, …)` — and resolving each target against the 83 defined `PROCEDURE`/`FUNCTION`
names. A reference that resolves to no definition is a *dangling* reference; the Stage-1W pseudocode has none. The two
false positives (`is`, `this`) are English words following the token `CALL`-adjacent prose and are not procedure
invocations.

**Result: 83 procedures defined; every internal reference resolves; 0 dangling references.**
