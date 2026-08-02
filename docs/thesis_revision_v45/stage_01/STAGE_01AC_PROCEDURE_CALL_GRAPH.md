# Stage 1AC — Procedure Call Graph

This document resolves the procedure call graph of `STAGE_01_PROTOCOL_PSEUDOCODE.md` after corrections AC1–AC8 and records
that it contains NO dangling call. Stage 1AC adds exactly ONE new procedure — `SetSetupRetryStatus` (AC7) — so the defined
count rises to **87** callables (86 `PROCEDURE` + 1 `FUNCTION`), from Stage 1AB's 86.

## 1. Resolution method

- **Defined symbols:** every `^PROCEDURE <name>` / `^FUNCTION <name>` header (87 unique names: 86 procedures + the one
  function `ClassifyRecoveryWork`).
- **Call targets:** every `CALL <name>` invocation target.
- **Dispatched handlers:** event handlers (e.g. `SetupRetryEvent`) are seated via `ScheduleEvent` and dispatched by
  `ProcessEventTime`, not via `CALL`; a defined handler with no `CALL` site is NOT dangling.
- **Dangling test:** `{ call targets } \ { defined symbols }`. The only lowercase tokens the raw scan surfaces are `is`
  and `this`, from prose fragments, not invocations. **Real dangling calls = 0.**

## 2. The one new node (AC7)

### 2.1 `SetSetupRetryStatus` — defined once, the sole status writer

| Property | Value |
|----------|-------|
| Definition | `PROCEDURE SetSetupRetryStatus` (after `CancelSetupRetriesForRound`) |
| In-edges | every setup-retry status change: `SetupRetryEvent` (stale/closed dispositions, the four guard aborts, the first-dispatch APPLYING, the step-8 terminal classification) and `CancelSetupRetriesForRound` (SEATED → CANCELLED on closure) |
| Out-edges | none via `CALL` — it reads `setup_retry_records[SetupRetryID].status`, checks the transition table, and performs the ONE keyed `status` UPDATE (or rejects) |

It enforces `setup_retry_status_transitions` (`SEATED → {APPLYING, CANCELLED, SUPERSEDED}`; `APPLYING → {APPLIED,
SUPERSEDED, CANCELLED, ABORTED}`; the rest terminal) and rejects every illegal transition — especially a terminal → terminal
rewrite — with no mutation. It is the ONLY writer of `setup_retry_records[*].status` (the seat CREATE aside).

## 3. AC-touched edges (otherwise unchanged topology)

### 3.1 `ScheduleEvent` (AC1) — richer result, same edges

`ScheduleEvent` now derives an `EventRef` and returns `scheduled(EventRef, envelope)`; its callers that bind the result
(`StartWake`, `SeatRecoveryCompletion`, `SeatRecoveryWork`, `CompleteSecurityRecovery`, and the two retry seating sites)
extract the canonical `event_ref` field. No call edge changed; the result shape is canonicalised.

### 3.2 `ProcessEventTime` (AC2) — injects `dispatched_event_ref`

`ProcessEventTime` sets `EQ.current_event_ref <- EventRef(e)`, dispatches with `dispatched_event_ref =
EQ.current_event_ref`, and clears it after the handler returns. `SetupRetryEvent` (dispatched, not `CALL`ed) receives the
injected reference. No new `CALL` edge.

### 3.3 `SetupRetryEvent` (AC3/AC4/AC5/AC6) — reordered guards, status via the guard

- In-edges (unchanged): `ScheduleEvent(SetupRetryEvent, ...)` from the two seating sites; each seat publishes
  `seat_event_ref = event_ref`, `event_queue_status = QUEUED`, `status = SEATED`.
- Out-edges: → `PrepareParticipantsForNewRound` / `ContinueTemplateRefreshAssignmentSetup` (targets), → `RoundAbort`
  (captured), and → `SetSetupRetryStatus` for EVERY status change (new AC7 edge). Ownership compares
  `dispatched_event_ref` (AC2) against `rec.seat_event_ref` (AC8).

### 3.4 `CancelSetupRetriesForRound` (AC6/AC7/AC8)

- In-edge (unchanged): `CloseRoundAssignments` → `CALL CancelSetupRetriesForRound(...)` (defined once, called once).
- New out-edge: → `SetSetupRetryStatus` (SEATED → CANCELLED). It sets `event_queue_status <- CANCELLED` (AC8, preserving
  `seat_event_ref`) and, for an `APPLYING` record, persists `terminal_closure_pending` (no status change).

## 4. Full defined-procedure inventory (87)

The Stage-1AB inventory of 86 callables, plus the one new `SetSetupRetryStatus`. No procedure was removed or renamed in
Stage 1AC; `ScheduleEvent`, `ProcessEventTime`, `SetupRetryEvent`, `CancelSetupRetriesForRound`, `RunInitialise`,
`StartWake`, `SeatRecoveryCompletion`, `SeatRecoveryWork`, and `CompleteSecurityRecovery` had their bodies / signatures /
records updated in place.

## 5. Result

The Stage-1AC call graph resolves with **87 defined callables and 0 dangling calls**. `SetSetupRetryStatus` is defined once
and is the sole `setup_retry_records[*].status` writer, reached from `SetupRetryEvent` and `CancelSetupRetriesForRound`;
`SetupRetryEvent` remains a dispatched handler receiving the dispatcher-injected `dispatched_event_ref`; `ScheduleEvent`
returns the canonical `scheduled(EventRef, envelope)`.
