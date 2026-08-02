# Stage 1AD — Procedure Call Graph

This document resolves the procedure call graph of `STAGE_01_PROTOCOL_PSEUDOCODE.md` after corrections AD1–AD10 and records
that it contains NO dangling call. Stage 1AD adds exactly ONE new procedure — `HandleDispatchIntegrityFailure` (AD8) — so
the defined count rises to **88** callables (87 `PROCEDURE` + 1 `FUNCTION`), from Stage 1AC's 87.

## 1. Resolution method

- **Defined symbols:** every `^PROCEDURE <name>` / `^FUNCTION <name>` header (88 unique names: 87 procedures + the one
  function `ClassifyRecoveryWork`).
- **Call targets:** every `CALL <name>` invocation target.
- **Dispatched handlers:** event handlers (e.g. `SetupRetryEvent`) are seated via `ScheduleEvent` and dispatched by
  `ProcessEventTime`, not via `CALL`; a defined handler with no `CALL` site is NOT dangling.
- **Dangling test:** `{ call targets } \ { defined symbols }`. The only lowercase tokens the raw scan surfaces are `is`
  and `this`, from prose fragments, not invocations. **Real dangling calls = 0.**

Mechanical verification of the current tree: 88 defined callables; 0 duplicate definitions; 0 dangling `CALL` targets;
`HandleDispatchIntegrityFailure` defined once and called once; exactly one `setup_retry_records[*].status <-` write (inside
`SetSetupRetryStatus`).

## 2. The one new node (AD8)

### 2.1 `HandleDispatchIntegrityFailure` — defined once, the dispatcher's integrity path

| Property | Value |
|----------|-------|
| Definition | `PROCEDURE HandleDispatchIntegrityFailure` (between `ProcessEventTime` and `RunEventLoopToHorizon`) |
| In-edges | exactly one: `ProcessEventTime`'s defensive corruption branch (`IF record is detected corrupt: CALL HandleDispatchIntegrityFailure(RoundContext, er, record)`) |
| Out-edges | → `RoundAbort` (captured `disp`, using the COMPLETE trusted-`EventRef` integrity envelope), → `SetSetupRetryStatus` (`APPLYING`/`ABORTED` for a current-round record; `SUPERSEDED` for an old/terminal-round record) |

It records the declared terminal disposition `dispatch_integrity_failure`, never dispatches the corrupt record into a
handler, and never uses the corrupt payload as the round-closure transition identity. `ProcessEventTime` marks the corrupt
event `CONSUMED` (never re-`QUEUED`) after it returns.

## 3. AD-touched edges (otherwise unchanged topology)

### 3.1 `ScheduleEvent` (AD2/AD3/AD8) — richer result, same edges

`ScheduleEvent` now stores the complete `immutable_payload`, asserts its completeness, creates the central
`queued_event_record` (registered `QUEUED`), and returns `scheduled(EventRef, queued_event_record)`. Its result-binding
callers (`StartWake`, `SeatRecoveryCompletion`, `SeatRecoveryWork`, `CompleteSecurityRecovery`, and the two retry seating
sites) extract the canonical `event_ref` field. No call edge changed; the result shape and the stored record are enriched.

### 3.2 `ProcessEventTime` (AD4/AD5/AD7/AD8) — sole queue-status owner + new corruption edge

`ProcessEventTime` moves `QUEUED → DISPATCHING` before dispatch and `DISPATCHING → CONSUMED` after, builds and threads
`OrdinaryDispatchContext`, dispatches the stored `immutable_payload`, and on detected corruption gains a new out-edge
→ `HandleDispatchIntegrityFailure`. No handler writes `queue_status`.

### 3.3 `SetupRetryEvent` (AD2/AD4/AD5) — stored payload, no queue write

- In-edges (unchanged): `ScheduleEvent(SetupRetryEvent, ...)` from the two seating sites; each seat publishes
  `seat_event_ref = event_ref, status = SEATED` (no queue mirror).
- Out-edges: → `PrepareParticipantsForNewRound` / `ContinueTemplateRefreshAssignmentSetup` (targets), → `RoundAbort`
  (captured), → `SetSetupRetryStatus` for every status change. It receives its payload as the stored `immutable_payload`
  (AD2) and `dispatched_event_ref` via the dispatcher-owned `OrdinaryDispatchContext` (AD5); the two Stage-1AC
  `event_queue_status <- CONSUMED` writes are removed (AD4).

### 3.4 `CancelSetupRetriesForRound` (AD1/AD6/AD9)

- In-edge (unchanged): `CloseRoundAssignments` → `CALL CancelSetupRetriesForRound(...)` (defined once, called once).
- Out-edge (unchanged): → `SetSetupRetryStatus` (`SEATED → CANCELLED` for a `QUEUED` retry). It now reads/mutates the
  central `queued_event_registry[seat_event_ref].queue_status` (AD1/AD9): `QUEUED` → cancel + `CANCELLED`; `DISPATCHING` →
  persist `terminal_closure_pending` only; `CONSUMED`/`CANCELLED` → no rewrite.

## 4. Full defined-procedure inventory (88)

The Stage-1AC inventory of 87 callables, plus the one new `HandleDispatchIntegrityFailure`. No procedure was removed or
renamed in Stage 1AD; `ScheduleEvent`, `ProcessEventTime`, `SetupRetryEvent`, `CancelSetupRetriesForRound`, `RunInitialise`,
`StartWake`, `SeatRecoveryCompletion`, `SeatRecoveryWork`, and `CompleteSecurityRecovery` had their bodies / signatures /
records updated in place, and the `queued_event_record` / `queued_event_registry` / `OrdinaryDispatchContext` structures were
added.

## 5. Result

The Stage-1AD call graph resolves with **88 defined callables and 0 dangling calls**. `HandleDispatchIntegrityFailure` is
defined once and called once (from `ProcessEventTime`'s corruption branch); `SetSetupRetryStatus` remains the sole
`setup_retry_records[*].status` writer; `ProcessEventTime` is the sole owner of the `queue_status` dispatch lifecycle (the
only cancellation, `QUEUED → CANCELLED`, is in `CancelSetupRetriesForRound`); and `ScheduleEvent` returns the canonical
`scheduled(EventRef, queued_event_record)`.
