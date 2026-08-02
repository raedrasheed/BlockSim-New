# Stage 1AE — Procedure Call Graph

This document resolves the procedure call graph of `STAGE_01_PROTOCOL_PSEUDOCODE.md` after corrections AE1–AE11 and records
that it contains NO dangling call. Stage 1AE adds exactly ONE new procedure — `CancelQueuedEvent` (AE1) — so the defined
count rises to **89** callables (88 `PROCEDURE` + 1 `FUNCTION`), from Stage 1AD's 88.

## 1. Resolution method

- **Defined symbols:** every `^PROCEDURE <name>` / `^FUNCTION <name>` header (89 unique names: 88 procedures + the one
  function `ClassifyRecoveryWork`).
- **Call targets:** every `CALL <name>` invocation target.
- **Dispatched handlers:** event handlers (e.g. `SetupRetryEvent`, `BlockAcceptancePoint`) are seated via `ScheduleEvent`
  and dispatched by `ProcessEventTime`, not via `CALL`; a defined handler with no `CALL` site is NOT dangling.
- **Dangling test:** `{ call targets } \ { defined symbols }`. The only lowercase tokens the raw scan surfaces are `is` and
  `this`, from prose fragments, not invocations. **Real dangling calls = 0.**

Mechanical verification of the current tree: 89 defined callables; 0 duplicate definitions; 0 dangling `CALL` targets;
`CancelQueuedEvent` defined once and called at every reconciled cancel site (31 `CALL CancelQueuedEvent` sites);
`HandleDispatchIntegrityFailure` defined once and called once; exactly one `setup_retry_records[*].status <-` write (inside
`SetSetupRetryStatus`); the only executable `queue_status <-` writes are in `ProcessEventTime` (`DISPATCHING`, `CONSUMED`)
and `CancelQueuedEvent` (`CANCELLED`).

## 2. The one new node (AE1)

### 2.1 `CancelQueuedEvent` — the sole queue-owner cancellation

| Property | Value |
|----------|-------|
| Definition | `PROCEDURE CancelQueuedEvent` (immediately after `ScheduleEvent`) |
| In-edges | every cancel site (AE2): `StartWake`, `AbortPendingWakeForRollback`, `CancelSetupRetriesForRound`, `RangeAssignFromPlan`, `CancelActiveRecoveryEpisode`, `ReconcilePendingRecoveryDecisions`, `ReconcilePendingRecoveryWork`, `SeatRecoveryWork`, `ReserveActivateFromPlan`, `RollbackRecoveryAssignmentPlan`, `LeaseExpiry`, `HandlePropagationFailure`, `ValidBlockAccept`, `CloseRoundAssignments`, `CloseTemplateAssignments`, `RoundAbort`, and the `AdversarialParticipationChangeEvent` hash-work-unit cleanup |
| Out-edges | none via `CALL` — it removes the EventRef from `EQ.event_queue`, sets `queue_status`, and records the cancellation |

It is the ONLY operation that removes an EventRef from EQ and is the SOLE writer of the `QUEUED → CANCELLED` edge; the
dispatch-lifecycle edges (`DISPATCHING`, `CONSUMED`) remain owned by `ProcessEventTime` (AD4).

## 3. AE-touched edges (otherwise unchanged topology)

- **`ScheduleEvent` (AE7/AE8):** validates the payload against §0.7g-schema (returns `rejected_payload_schema_mismatch`
  before any mutation) and commits the seat atomically (registry entry + EQ entry both-or-neither). No call edge changed.
- **`ProcessEventTime` (AE3/AE5):** the dispatch loop re-selects/re-reads (skips a cancelled event) and dispatches only the
  schema-declared arguments; new dependence on §0.7g-schema; no new `CALL` edge except the existing corruption edge →
  `HandleDispatchIntegrityFailure`.
- **`HandleDispatchIntegrityFailure` (AE6):** resolves the owner from `setup_retry_by_seat_event_ref` (a map, not a
  procedure); out-edges → `SetSetupRetryStatus`, → `RoundAbort` unchanged.
- **`ScheduleNextHashWork` (AE9):** now returns `hash_work_seated`/`hash_work_not_seated`; its callers (`StartHashing`, the
  `HashWorkEvent` continuation) bind and report it; no new `CALL` edge.

## 4. Full defined-procedure inventory (89)

The Stage-1AD inventory of 88 callables, plus the one new `CancelQueuedEvent`. No procedure was removed or renamed in
Stage 1AE; `ScheduleEvent`, `ProcessEventTime`, `HandleDispatchIntegrityFailure`, `ScheduleNextHashWork`, `StartHashing`,
`CancelSetupRetriesForRound`, and the many former raw-cancel procedures had their bodies updated in place, and the
`setup_retry_by_seat_event_ref` reverse map + §0.7g-schema were added.

## 5. Result

The Stage-1AE call graph resolves with **89 defined callables and 0 dangling calls**. `CancelQueuedEvent` is defined once
and is the sole EQ-removal / `QUEUED → CANCELLED` writer, reached from every reconciled cancel site; `ProcessEventTime`
remains the sole dispatch-lifecycle owner; `SetSetupRetryStatus` remains the sole `status` writer; and `ScheduleEvent`
returns the AE7-augmented result union.
