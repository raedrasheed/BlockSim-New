# Stage 1AC — Semantic Test Vectors (TV244–TV251)

These blocking paper test vectors exercise corrections AC1–AC8 of the event-reference and retry-state closure lock. Each
vector names the EXACT procedures and preconditions it drives, states the required outcome, and asserts NO behaviour that
is not written in `STAGE_01_PROTOCOL_PSEUDOCODE.md` / `STAGE_01_MINER_STATE_MACHINE.md` (no assumed guard, transition,
edge, or result name). Every vector preserves the A1 baseline (`8.420833333 kWh`). The algorithm is **PoCol** and the
mechanism under test is the idle policy within PoCol.

Terminology: `EventRef = (envelope_namespace, event_type, event_time, delta_cycle, microphase, seq)` (AC1);
`ScheduleEvent` returns `scheduled(EventRef, envelope)`; `ProcessEventTime` injects `dispatched_event_ref =
EQ.current_event_ref` (AC2); a `setup_retry_record` carries the immutable `seat_event_ref` and an `event_queue_status`
(AC8); `SetSetupRetryStatus` enforces the `SetupRetryStatus` transition table (AC7).

---

## TV244 — ScheduleEvent's EventRef is stored and later matched at dispatch (AC1/AC2/AC8)

- **Procedures:** the seating procedure (`PrepareParticipantsForNewRound` / `ContinueTemplateRefreshAssignmentSetup`),
  `ScheduleEvent`, `ProcessEventTime`, `SetupRetryEvent`.
- **Setup:** `ScheduleEvent` seats one `SetupRetryEvent` and returns `scheduled(E, envelope)` (EventRef `E`); the seat
  publishes `setup_retry_records[srid]` with `seat_event_ref = E`, `event_queue_status = QUEUED`, `status = SEATED`. Later,
  `ProcessEventTime` dispatches that same event, setting `EQ.current_event_ref <- EventRef(e)` and injecting
  `dispatched_event_ref = EQ.current_event_ref`.
- **Expected:** `EventRef(e) = E`, so `SetupRetryEvent`'s ownership check `dispatched_event_ref = rec.seat_event_ref`
  succeeds using the dispatcher-injected value — no ambient/derived reference is read. The handler proceeds to its guards.

## TV245 — A missing dispatched_event_ref is rejected at the signature/dispatch audit (AC2)

- **Procedures:** `SetupRetryEvent` (signature), `ProcessEventTime` (dispatch contract).
- **Setup:** consider a dispatch that fails to supply `dispatched_event_ref` to `SetupRetryEvent`.
- **Expected:** `dispatched_event_ref` is a MANDATORY input; the dispatch contract (AC2) requires `ProcessEventTime` to set
  `EQ.current_event_ref` and inject it on every dispatch. The specification therefore rejects a dispatch with no EventRef at
  the signature/dispatch audit — no handler may execute with an undefined `dispatched_event_ref`. (Paper check: the
  `STAGE_01AC_PROCEDURE_SIGNATURE_CALL_AUDIT.md` records `dispatched_event_ref` as mandatory and dispatcher-supplied.)

## TV246 — An APPLIED replay with a corrupted payload is duplicate-suppressed before integrity (AC3)

- **Procedures:** `SetupRetryEvent`.
- **Setup:** a retry record is `APPLIED`; its genuine event's EventRef is replayed (`dispatched_event_ref =
  rec.seat_event_ref`) but the payload fields are corrupted.
- **Expected:** after ownership (step 3), the guard `IF rec.status != SEATED` fires (step 4, BEFORE any payload-integrity
  handling) and returns `setup_retry_duplicate_suppressed(SetupRetryID)`. NO `RoundAbort` occurs — a terminal replay never
  aborts a round because of differing replayed payload fields.

## TV247 — A corrupted historical retry from r1 does not abort the later round r2 (AC4)

- **Procedures:** `SetupRetryEvent`, `SetSetupRetryStatus`.
- **Setup:** a genuine owned retry record was seated in round `r1` (`rec.RoundID = r1`, still `SEATED`); the current round
  is now `r2` (`RoundID_current = r2 ≠ r1`); the dispatch's payload is corrupted.
- **Expected:** after ownership + the non-SEATED check, step 5 decides membership from the IMMUTABLE record: `rec.RoundID ≠
  RoundID_current`, so the record is terminalised `SUPERSEDED` (via `SetSetupRetryStatus`, `target_disposition =
  setup_retry_stale_noop`) and the handler returns `setup_retry_stale_noop`. The current round `r2` is NOT aborted — the
  payload is never consulted to decide round membership.

## TV248 — A genuine EventRef with an incomplete dispatch envelope terminalises the record (AC5-C)

- **Procedures:** `SetupRetryEvent`, `RoundAbort`, `SetSetupRetryStatus`.
- **Setup:** a current owned `SEATED` record (current nonterminal round, current template) whose genuine event dispatches
  (`dispatched_event_ref = rec.seat_event_ref`) but with an incomplete `dispatch_envelope` (or a payload mismatch).
- **Expected:** step 6 detects the owning-event corruption; the record moves `SEATED → APPLYING` (AC6),
  `event_queue_status <- CONSUMED` (AC8), `disp <- CALL RoundAbort(reason =
  setup_retry_payload_integrity_failure(setup_kind), ...)`, then `APPLYING → ABORTED` with `target_disposition = disp`. The
  record cannot remain `SEATED` with its only event consumed.

## TV249 — A guard abort goes SEATED → APPLYING → ABORTED, never CANCELLED → ABORTED (AC6)

- **Procedures:** `SetupRetryEvent`, `CancelSetupRetriesForRound`, `RoundAbort`, `SetSetupRetryStatus`.
- **Setup:** a current owned `SEATED` retry reaches an aborting guard (e.g. wrong round state, budget exhausted).
- **Expected:** the handler first `SetSetupRetryStatus(APPLYING)` (SEATED → APPLYING), then `disp <- CALL RoundAbort(...)`;
  `RoundAbort → CloseRoundAssignments → CancelSetupRetriesForRound` sees the record `APPLYING` and persists
  `terminal_closure_pending` (it does NOT change it to `CANCELLED`); back in the handler, `SetSetupRetryStatus(ABORTED)`
  (APPLYING → ABORTED). No straight `SEATED → ABORTED` and no `CANCELLED → ABORTED` transition ever occurs.

## TV250 — An illegal CANCELLED → ABORTED transition is rejected with no mutation (AC7)

- **Procedures:** `SetSetupRetryStatus`.
- **Setup:** a record is already `CANCELLED` (terminal); some path attempts `SetSetupRetryStatus(SetupRetryID, ABORTED)`.
- **Expected:** `(CANCELLED → ABORTED)` is not in `setup_retry_status_transitions`; `SetSetupRetryStatus` records
  `illegal_setup_retry_status_transition` and returns `setup_retry_status_transition_rejected` with NO mutation — the record
  stays `CANCELLED`. A terminal status is final.

## TV251 — Round closure cancels the queued event but preserves the immutable seat EventRef (AC8)

- **Procedures:** `CancelSetupRetriesForRound`, `CloseRoundAssignments`.
- **Setup:** a round with a `SEATED` retry record whose `event_queue_status = QUEUED` is closed.
- **Expected:** `CancelSetupRetriesForRound` cancels the queued event on `EQ`, sets `event_queue_status <- CANCELLED`, and
  terminalises the record `SEATED → CANCELLED` via `SetSetupRetryStatus` — while the immutable `seat_event_ref` REMAINS
  available for replay auditing. After closure no record of the round is `SEATED` and none has `event_queue_status =
  QUEUED` (no queued event survives).

---

## Coverage summary

| Vector | Correction | Primary procedures |
|--------|-----------|--------------------|
| TV244 | AC1/AC2/AC8 | seating, `ScheduleEvent`, `ProcessEventTime`, `SetupRetryEvent` |
| TV245 | AC2 | `SetupRetryEvent` signature, `ProcessEventTime` |
| TV246 | AC3 | `SetupRetryEvent` |
| TV247 | AC4 | `SetupRetryEvent`, `SetSetupRetryStatus` |
| TV248 | AC5 | `SetupRetryEvent`, `RoundAbort` |
| TV249 | AC6 | `SetupRetryEvent`, `CancelSetupRetriesForRound`, `RoundAbort` |
| TV250 | AC7 | `SetSetupRetryStatus` |
| TV251 | AC8 | `CancelSetupRetriesForRound`, `CloseRoundAssignments` |

All eight vectors are specified against exact procedures and preconditions in the current
`STAGE_01_PROTOCOL_PSEUDOCODE.md`; none assumes an unwritten guard, transition, edge, or result name; and all preserve the
A1 baseline `8.420833333 kWh`.
