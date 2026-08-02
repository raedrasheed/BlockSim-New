# Stage 1AD — Semantic Test Vectors (TV252–TV261)

These blocking paper test vectors exercise corrections AD1–AD10 of the queued-event lifecycle and payload lock. Each vector
names the EXACT procedures and preconditions it drives, states the required outcome, and asserts NO behaviour that is not
written in `STAGE_01_PROTOCOL_PSEUDOCODE.md` / `STAGE_01_MINER_STATE_MACHINE.md` (no assumed guard, transition, edge, or
result name). Every vector preserves the A1 baseline (`8.420833333 kWh`). The algorithm is **PoCol** and the mechanism under
test is the idle policy within PoCol.

Terminology: `queued_event_record = (event_ref : EventRef immutable, event_type, dispatch_envelope, immutable_payload,
queue_status : EventQueueStatus)` held in `queued_event_registry : map EventRef → queued_event_record` — the ONE
authoritative queue-status source (AD1); `EventQueueStatus` transitions `QUEUED → {DISPATCHING, CANCELLED}`,
`DISPATCHING → CONSUMED`, with `CONSUMED`/`CANCELLED` terminal; `ScheduleEvent` returns
`scheduled(EventRef, queued_event_record)` (AD3); `ProcessEventTime` is the sole queue-status owner (AD4) and builds the
dispatcher-owned `OrdinaryDispatchContext = (dispatch_envelope, dispatched_event_ref)` (AD5, Design B); a
`setup_retry_record` keeps only its immutable `seat_event_ref` and its queue state IS
`queued_event_registry[seat_event_ref].queue_status`.

---

## TV252 — ScheduleEvent registers one central record; the retry record keeps no queue mirror (AD1)

- **Procedures:** the seating procedure (`PrepareParticipantsForNewRound` / `ContinueTemplateRefreshAssignmentSetup`),
  `ScheduleEvent`.
- **Setup:** `ScheduleEvent` seats one `SetupRetryEvent` and returns `scheduled(E, record)` (EventRef `E`, central
  `queued_event_record` `record`); the seat publishes `setup_retry_records[srid]` with `seat_event_ref = E`, `status = SEATED`.
- **Expected:** `queued_event_registry[E]` exists with `queue_status = QUEUED`, and it is the ONLY place the event's queue
  state lives. `setup_retry_records[srid]` carries `seat_event_ref = E` and NO writable `event_queue_status` field; the
  record's queue state is read as `queued_event_registry[seat_event_ref].queue_status`. There is no per-record queue mirror
  that could diverge from the registry.

## TV253 — The complete payload stored at seating is dispatched verbatim (AD2)

- **Procedures:** `ScheduleEvent`, `ProcessEventTime`, `SetupRetryEvent`.
- **Setup:** `ScheduleEvent` seats a `SetupRetryEvent`, storing `record.immutable_payload =` the complete argument set
  (`RoundID`, `setup_kind`, `SetupRetryID`, `TemplateID_at_seat`, `TemplateRefreshSetupID`, `retry_generation`, `reason`).
  Between seating and dispatch the ambient `RoundID_current` / `TemplateID_committed` advance.
- **Expected:** `ProcessEventTime` dispatches `record.event_type` WITH `immutable_payload = record.immutable_payload` — the
  payload at dispatch is identically the payload captured at seating. `SetupRetryEvent` reads its `TemplateID_at_seat` etc.
  from the stored payload, not from the advanced ambient state, so a stale field cannot be substituted with current globals.

## TV254 — A ScheduleEvent rejection variant is handled, not treated as a seat (AD3)

- **Procedures:** `ScheduleEvent`, a result-binding caller (`StartWake` / `SeatRecoveryCompletion` / `SeatRecoveryWork` /
  `CompleteSecurityRecovery` / the retry seating sites).
- **Setup:** a caller invokes `ScheduleEvent` and the target `event_time` is already in `EQ.finalised_event_times` (or is
  post-horizon / backward / at-or-behind a post-epilogue source).
- **Expected:** `ScheduleEvent` returns the exact rejection variant from its declared union
  (`rejected_finalised_time` / `post_horizon_event_rejected` / `rejected_backward_time` /
  `rejected_post_epilogue_not_strictly_later`); the caller's `IF … = scheduled(event_ref, record)` binding does NOT match,
  so the caller takes its rejection branch (e.g. `StartWake` returns `wake_schedule_failed_before_transition`). No caller
  treats a rejection as a successful seat because a variant is missing from the declared union.

## TV255 — ProcessEventTime owns QUEUED → DISPATCHING → CONSUMED; no handler writes queue_status (AD4)

- **Procedures:** `ProcessEventTime`, `SetupRetryEvent`.
- **Setup:** a `QUEUED` `SetupRetryEvent` is the next event at `(t, current_delta_cycle)`.
- **Expected:** `ProcessEventTime` asserts `record.queue_status = QUEUED`, sets `QUEUED → DISPATCHING`, sets
  `EQ.current_event_ref`, dispatches, and AFTER the handler returns sets `DISPATCHING → CONSUMED` and clears
  `EQ.current_event_ref`. `SetupRetryEvent` performs NO `queue_status` write of any kind. The dispatch lifecycle has exactly
  one owner.

## TV256 — Design B delivers dispatched_event_ref only to a handler that declares it (AD5)

- **Procedures:** `ProcessEventTime`, `SetupRetryEvent`, and any ordinary handler that does NOT declare `dispatched_event_ref`.
- **Setup:** `ProcessEventTime` builds `ctx = OrdinaryDispatchContext(dispatch_envelope = record.dispatch_envelope,
  dispatched_event_ref = er)` and dispatches two events: one `SetupRetryEvent` and one ordinary handler whose signature omits
  `dispatched_event_ref`.
- **Expected:** every handler receives `dispatch_envelope = ctx.dispatch_envelope`; `dispatched_event_ref =
  ctx.dispatched_event_ref` is passed ONLY to `SetupRetryEvent` (whose signature declares it). No undeclared named argument
  is injected into the handler that omits it, and no handler derives its own `dispatched_event_ref` from ambient state.

## TV257 — A guard-driven abort sees DISPATCHING at closure, never a stale QUEUED (AD6)

- **Procedures:** `SetupRetryEvent`, `ProcessEventTime`, `CancelSetupRetriesForRound`, `RoundAbort`, `CloseRoundAssignments`.
- **Setup:** a current owned `SEATED` retry is dispatched (so `ProcessEventTime` already set its
  `queue_status = DISPATCHING`) and reaches an aborting guard; the handler moves `SEATED → APPLYING` and calls
  `RoundAbort → CloseRoundAssignments → CancelSetupRetriesForRound`.
- **Expected:** `CancelSetupRetriesForRound` reads `queued_event_registry[seat_event_ref].queue_status = DISPATCHING` and the
  record `status = APPLYING`; it does NOT cancel the event and does NOT rewrite the queue state — it only persists
  `terminal_closure_pending`. No `QUEUED` assertion trips during the abort (the Stage-1AC failure this corrects). Back in the
  handler, `SetSetupRetryStatus(ABORTED)`; the dispatcher then completes `DISPATCHING → CONSUMED`, so no event remains
  `DISPATCHING` after the handler returns.

## TV258 — A stale dispatch still consumes its queue entry (AD7)

- **Procedures:** `ProcessEventTime`, `SetupRetryEvent`, `CloseRoundAssignments`, `CancelSetupRetriesForRound`.
- **Setup:** a `SetupRetryEvent` whose record is already terminal (e.g. `SUPERSEDED`) is dispatched — a stale replay that the
  handler resolves to a stale/duplicate no-op.
- **Expected:** even though the handler takes a no-op exit, `ProcessEventTime` still drives
  `QUEUED → DISPATCHING → CONSUMED`; the registry entry ends `CONSUMED`, never left at `QUEUED`. A later
  `CloseRoundAssignments` / `CancelSetupRetriesForRound` therefore never finds a terminal retry record whose central event is
  falsely `QUEUED`.

## TV259 — An incomplete record is rejected at construction; corruption uses a complete integrity envelope (AD8)

- **Procedures:** `ScheduleEvent`, `ProcessEventTime`, `HandleDispatchIntegrityFailure`, `RoundAbort`, `SetSetupRetryStatus`.
- **Setup (a):** a caller invokes `ScheduleEvent` with a payload missing a required field for the target handler.
- **Setup (b):** a registry entry is (defensively) detected corrupt at dispatch: one whose owning `SetupRetryID` resolves to
  a current nonterminal-round `SEATED` record, and one whose record belongs to an older/terminal round.
- **Expected (a):** `ScheduleEvent` asserts `immutable_payload contains EVERY required field` and does NOT construct or
  register an incomplete `queued_event_record`.
- **Expected (b):** `ProcessEventTime` calls `HandleDispatchIntegrityFailure`, which builds a COMPLETE integrity envelope
  from the trusted `EventRef` fields (never the corrupt payload). For the current nonterminal-round record it terminalises
  `SEATED → APPLYING → ABORTED` via `RoundAbort(reason = setup_retry_payload_integrity_failure(…), dispatch_envelope =
  integrity_envelope)`; for the old/terminal-round record it sets `SUPERSEDED` WITHOUT aborting the current round. The
  dispatcher then marks the corrupt event `CONSUMED` (never re-`QUEUED`). A malformed untrusted envelope never becomes the
  round-closure transition identity.

## TV260 — CancelSetupRetriesForRound branches on the central queue state (AD9)

- **Procedures:** `CancelSetupRetriesForRound`, `SetSetupRetryStatus`, `CloseRoundAssignments`.
- **Setup:** a closing round with three retry records — one whose central event is `QUEUED` (record `SEATED`), one whose
  event is `DISPATCHING` (record `APPLYING`, handler mid-flight), and one whose event is already `CONSUMED` (record
  terminal).
- **Expected:** for the `QUEUED` one, cancel the event on `EQ`, set `queued_event_registry[seat_event_ref].queue_status ←
  CANCELLED` and `SetSetupRetryStatus(SEATED → CANCELLED)`; for the `DISPATCHING` one, do NOT cancel and do NOT rewrite the
  queue state — persist `terminal_closure_pending` only; for the `CONSUMED` one, perform no queue-state rewrite. No terminal
  queue state is ever rewritten.

## TV261 — After closure no closing-round event is QUEUED and none stays DISPATCHING (AD9)

- **Procedures:** `CancelSetupRetriesForRound`, `ProcessEventTime`, `SetupRetryEvent`, `CloseRoundAssignments`.
- **Setup:** the round of TV260 is closed; the mid-flight (`DISPATCHING`) retry's handler subsequently returns.
- **Expected:** `CancelSetupRetriesForRound`'s post-conditions hold — no closing-round event's
  `queued_event_registry[seat_event_ref].queue_status = QUEUED`; every `SEATED` retry is terminalised; and no terminal retry
  owns a live `QUEUED` event. The `DISPATCHING` retry finishes `APPLYING → ABORTED/CANCELLED` and the dispatcher completes
  `DISPATCHING → CONSUMED`, so once its handler returns no closing-round event remains `DISPATCHING`. No queue status is held
  in an unsynchronised local mirror.

---

## Coverage summary

| Vector | Correction | Primary procedures |
|--------|-----------|--------------------|
| TV252 | AD1 | seating, `ScheduleEvent` |
| TV253 | AD2 | `ScheduleEvent`, `ProcessEventTime`, `SetupRetryEvent` |
| TV254 | AD3 | `ScheduleEvent`, result-binding callers |
| TV255 | AD4 | `ProcessEventTime`, `SetupRetryEvent` |
| TV256 | AD5 | `ProcessEventTime`, `SetupRetryEvent` |
| TV257 | AD6 | `SetupRetryEvent`, `ProcessEventTime`, `CancelSetupRetriesForRound`, `RoundAbort` |
| TV258 | AD7 | `ProcessEventTime`, `SetupRetryEvent`, `CloseRoundAssignments` |
| TV259 | AD8 | `ScheduleEvent`, `ProcessEventTime`, `HandleDispatchIntegrityFailure`, `RoundAbort` |
| TV260 | AD9 | `CancelSetupRetriesForRound`, `SetSetupRetryStatus` |
| TV261 | AD9 | `CancelSetupRetriesForRound`, `ProcessEventTime`, `SetupRetryEvent` |

All ten vectors are specified against exact procedures and preconditions in the current `STAGE_01_PROTOCOL_PSEUDOCODE.md`;
none assumes an unwritten guard, transition, edge, or result name; and all preserve the A1 baseline `8.420833333 kWh`.
