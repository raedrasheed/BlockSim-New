# Stage 1AA — Procedure Call Graph

This document resolves the procedure call graph of `STAGE_01_PROTOCOL_PSEUDOCODE.md` after corrections AA1–AA6 and records
that it contains NO dangling call. Stage 1AA adds exactly ONE new procedure — `CancelSetupRetriesForRound` (AA2) — so the
defined count rises to **86** callables (85 `PROCEDURE` + 1 `FUNCTION`), from Stage 1Z's 85.

## 1. Resolution method

- **Defined symbols:** every `^PROCEDURE <name>` / `^FUNCTION <name>` header (86 unique names: 85 procedures +
  the one function `ClassifyRecoveryWork`).
- **Call targets:** every `CALL <name>` invocation target.
- **Dispatched handlers:** event handlers (e.g. `SetupRetryEvent`) are seated via `ScheduleEvent` and dispatched by
  `ProcessEventTime`, not via `CALL`; a defined handler with no `CALL` site is NOT dangling.
- **Dangling test:** `{ call targets } \ { defined symbols }`. The only lowercase tokens the raw scan surfaces are `is`
  and `this`, from prose fragments (`CALL this hook`, `... CALL ... is ...`), not invocations. **Real dangling calls = 0.**

## 2. The one new node (AA2)

### 2.1 `CancelSetupRetriesForRound` — defined once, called once

| Property | Value |
|----------|-------|
| Definition | `PROCEDURE CancelSetupRetriesForRound` (§17a-adjacent, after `SetupRetryEvent`) |
| In-edge | `CloseRoundAssignments` → `CALL CancelSetupRetriesForRound(RoundContext, closing_RoundID = RoundID, cancellation_reason = round_closed(disposition), dispatch_or_run_hook_context = dispatch_envelope)` |
| Out-edges | none via `CALL` — it CANCELs a queued `event_ref` on `EQ` and mutates `setup_retry_records` in place |
| Callers | exactly 1 (`CloseRoundAssignments`) |

It iterates `{ r in setup_retry_records : r.RoundID = closing_RoundID }` in stable `SetupRetryID` order: a `SEATED` record
has its `event_ref` cancelled (if still pending) and becomes `CANCELLED`; an `APPLYING` record is flagged
`terminal_closure_pending`; already-terminal records are unchanged. It returns `setup_retries_terminalised(closing_RoundID)`.

## 3. AA-touched edges (otherwise unchanged topology)

Stage 1AA changes the DATA and RESULT NAMES threaded across existing edges; apart from the one new node, the call topology
is unchanged from Stage 1Z.

### 3.1 `RoundAbort` (AA1) — one canonical result on every abort edge

`RoundAbort` returns `round_aborted(abort_record)` and is the sole abort producer. The `RETURN CALL RoundAbort(...)`
propagators — `SetupRetryEvent`, `PrepareParticipantsForNewRound`, `ContinueTemplateRefreshAssignmentSetup`,
`TemplateRefresh`, `FullRangeExhaustNoSolution` — carry the canonical name in their RETURNS unions. The recovery paths
(`ApplyRecoveryWorkAfterEpilogue`, `ApplyRecoveryAssignmentContinuationAfterEpilogue`, `CompleteSecurityRecovery` via
`RoundAbort(floor_unrecoverable)`) instead `CALL RoundAbort` for effect with `recovery_finalising = true` and return their
own recovery-specific disposition — they do not surface a bare `abort_record`. No call edge changed; only the result name
is standardised.

### 3.2 `CloseRoundAssignments` (AA2) — one new out-edge

- New out-edge: `CloseRoundAssignments` → `CancelSetupRetriesForRound` (§2.1).
- The round-closure event-cancellation set now explicitly lists `SetupRetryEvent` alongside the recovery-timeline events.

### 3.3 `SetupRetryEvent` (AA1/AA3) — dispatched handler, reordered guards

- In-edges (unchanged): `ScheduleEvent(SetupRetryEvent, ...)` from `PrepareParticipantsForNewRound` and
  `ContinueTemplateRefreshAssignmentSetup`; each seating site publishes `setup_retry_records[srid]` with `status = SEATED`
  and `terminal_closure_pending = false`.
- Out-edges (unchanged): → `PrepareParticipantsForNewRound` (PARTICIPANT_SETUP), → `ContinueTemplateRefreshAssignmentSetup`
  (TEMPLATE_REFRESH_SETUP), → `RoundAbort`. The disposition is CAPTURED (no direct `RETURN CALL` for the target) and
  classified; a target `round_aborted(abort_record)` sets `ABORTED` (AA1).

### 3.4 `ApplyMinerStateTransition` (AA4/AA5)

- `assignment_effect_policy` becomes a field of `TransitionEventID` (AA4) — no new call edge.
- The AA5 legal-tuple guard rejects an illegal `STATE_ONLY_ROLLBACK` before the atomic apply — no new call edge; the sole
  `STATE_ONLY_ROLLBACK` caller remains `AbortPendingWakeForRollback`.

### 3.5 The two setup rollback owners (AA6)

`RollbackParticipantSetup` and `RollbackTemplateRefreshSetup` iterate the KEYED `setup_txn.rollback_items` deterministically
by `RollbackItemID` and call `AbortPendingWakeForRollback` per stored item — the call edge is unchanged; only the storage
(keyed map) and the explicit-by-key update discipline changed. `RollbackRecoveryAssignmentPlan` (recovery-install rollback,
`rollback_record.items`) is OUTSIDE the AA6 setup scope and is unchanged.

## 4. Full defined-procedure inventory (86)

The Stage-1Z inventory of 85 callables, plus the one new `CancelSetupRetriesForRound`. No procedure was removed or renamed
in Stage 1AA; `RoundAbort`, `SetupRetryEvent`, `CloseRoundAssignments`, `ApplyMinerStateTransition`,
`AbortPendingWakeForRollback`, the two setup rollback owners, the two seating procedures, and `FullRangeExhaustNoSolution`
had their bodies/signatures updated in place.

## 5. Result

The Stage-1AA call graph resolves with **86 defined callables and 0 dangling calls**. `CancelSetupRetriesForRound` is
defined once and reached from exactly one call site (`CloseRoundAssignments`); `AbortPendingWakeForRollback` remains
defined once and reached from three call sites; every dispatched handler (including `SetupRetryEvent`) is reachable through
`ScheduleEvent` / `ProcessEventTime`.
