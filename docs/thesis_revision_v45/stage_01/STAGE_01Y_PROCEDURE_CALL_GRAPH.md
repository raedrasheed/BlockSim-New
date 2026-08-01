# Stage 1Y — Procedure Call Graph

This document resolves the procedure call graph of `STAGE_01_PROTOCOL_PSEUDOCODE.md` after corrections Y1–Y5 and
records that it contains NO dangling call. The Stage-1Y change adds ONE procedure —
`AbortPendingWakeForRollback` (Y5) — raising the defined count from 84 (Stage 1X) to **85**.

## 1. Resolution method

- **Defined symbols:** every `^PROCEDURE <name>` / `^FUNCTION <name>` header (85 unique names).
- **Call targets:** every `CALL <name>` invocation target.
- **Dispatched handlers:** event handlers are seated via `ScheduleEvent(EQ, RoundContext, <Handler>, ...)` and dispatched
  by `ProcessEventTime`, not via `CALL`; a defined handler with no `CALL` site (e.g. `SetupRetryEvent`) is NOT dangling.
- **Dangling test:** `{ call targets } \ { defined symbols }`. The only tokens the raw scan surfaces are `is` and `this`,
  from prose fragments, not invocations. **Real dangling calls = 0.**

## 2. New node — `AbortPendingWakeForRollback` (Y5)

| Direction | Edge | Site |
|-----------|------|------|
| in  | `RollbackParticipantSetup` → `AbortPendingWakeForRollback` | per affected miner (§2, ~L1784) |
| in  | `RollbackTemplateRefreshSetup` → `AbortPendingWakeForRollback` | per affected miner (§2, ~L1816) |
| in  | `RollbackRecoveryAssignmentPlan` → `AbortPendingWakeForRollback` | per rollback_item (§10a, ~L3818) |
| out | → `ApplyMinerStateTransition` | legal `T12` `WAKING -> OFFLINE`, `reason = validation_abort` |

`AbortPendingWakeForRollback` is defined ONCE and reached from exactly THREE call sites — the three rollback owners; it
is the single node through which every rollback wake-abort + canonical assignment close flows (Y5). It calls only
`ApplyMinerStateTransition` (the `T12` hook).

## 3. Y-touched call edges (caller → callee)

### 3.1 The three rollback owners (Y4/Y5)

Each now resolves every affected `WAKING` miner UNCONDITIONALLY through `AbortPendingWakeForRollback`:

- `RollbackRecoveryAssignmentPlan` → `AbortPendingWakeForRollback` (per `rollback_record.items`).
- `RollbackParticipantSetup` → `AbortPendingWakeForRollback` (per `setup_txn.assignment_by_miner`).
- `RollbackTemplateRefreshSetup` → `AbortPendingWakeForRollback` (per `setup_txn.assignment_by_miner`).

The former direct `ApplyMinerStateTransition` `T12` edges from the three rollback procedures are withdrawn — that edge
now lives inside `AbortPendingWakeForRollback` (one owner). `RollbackRecoveryAssignmentPlan`'s in-edges are unchanged:
`ApplyRecoveryWorkAfterEpilogue` (install_failed_after_mutation) and `ApplyRecoveryAssignmentContinuationAfterEpilogue`
(install_failed_after_mutation + post-CompleteAssignmentPhase fail).

### 3.2 `SetupRetryEvent` (Y1/Y2/Y3, dispatched handler)

| Direction | Edge | Site |
|-----------|------|------|
| in  | `ScheduleEvent(SetupRetryEvent, ...)` from `PrepareParticipantsForNewRound` and `ContinueTemplateRefreshAssignmentSetup` | queue-seated |
| out | → `PrepareParticipantsForNewRound` | `PARTICIPANT_SETUP`, after Y1 idempotence + Y2 identity + state/budget guards |
| out | → `ContinueTemplateRefreshAssignmentSetup` | `TEMPLATE_REFRESH_SETUP`, passing the exact `TemplateRefreshSetupID` + scalar `retry_generation` |
| out | → `RoundAbort` | wrong-round-state / budget-exhausted / state-incompatible |

### 3.3 `ContinueTemplateRefreshAssignmentSetup` (Y2/Y3/Y4) — 2 call sites

| Caller | Site |
|--------|------|
| `TemplateRefresh` | initial call, `TemplateRefreshSetupID` set, `SetupRetryID = null`, `retry_generation = 0` (~L4840) |
| `SetupRetryEvent` (TEMPLATE_REFRESH_SETUP) | retry resume, exact `TemplateRefreshSetupID` + scalar `retry_generation` (~L1889) |

Its callees are unchanged (`CreatePendingAssignment`, `StartWake`, `CompleteAssignmentPhase`,
`RollbackTemplateRefreshSetup`, `RoundAbort`, `ScheduleEvent(SetupRetryEvent)`).

## 4. Full defined-procedure inventory (85)

The 84 Stage-1X procedures (see `STAGE_01X_PROCEDURE_CALL_GRAPH.md`) plus **`AbortPendingWakeForRollback`** (Y5). No
procedure was removed or renamed; `SetupRetryEvent`, the three rollback owners, `TemplateRefresh`,
`ContinueTemplateRefreshAssignmentSetup`, `PrepareParticipantsForNewRound`, `RoundInitialise`, and `RunInitialise` had
their bodies/signatures updated in place.

## 5. Result

The Stage-1Y call graph resolves with **85 defined procedures and 0 dangling calls**. The new
`AbortPendingWakeForRollback` is defined once and reached from exactly three call sites (the three rollback owners); the
setup-retry, template-refresh, and rollback subgraphs are fully connected; and every dispatched handler (including
`SetupRetryEvent`) is reachable through `ScheduleEvent` / `ProcessEventTime`.
