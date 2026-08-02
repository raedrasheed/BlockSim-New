# Stage 1AB — Semantic Test Vectors (TV236–TV243)

These blocking paper test vectors exercise corrections AB1–AB7 of the retry-record persistence and exact abort-contract
lock. Each vector names the EXACT procedures and preconditions it drives, states the required outcome, and asserts NO
behaviour that is not written in `STAGE_01_PROTOCOL_PSEUDOCODE.md` / `STAGE_01_MINER_STATE_MACHINE.md` (no assumed guard,
transition, edge, or result name). Every vector preserves the A1 baseline (`8.420833333 kWh`). The algorithm is **PoCol**
and the mechanism under test is the idle policy within PoCol.

Terminology: `RoundAbort` returns the exact `round_aborted(abort_record)` (AB1); guard-driven aborts capture the result
before persisting it (AB2); every setup-retry lifecycle mutation is a keyed `UPDATE setup_retry_records[SetupRetryID]`
(AB3); `SetupRetryEvent` re-reads the persisted record after its target returns (AB4); `dispatched_event_ref` binds
dispatch ownership to `rec.event_ref` (AB5); `CancelSetupRetriesForRound` uses keyed updates with closure post-conditions
(AB6).

---

## TV236 — PrepareParticipantsForNewRound's declared and actual abort result are the exact shape (AB1)

- **Procedures:** `PrepareParticipantsForNewRound`, `RoundAbort`.
- **Setup:** a participant setup fails irrecoverably (e.g. `RollbackParticipantSetup` returns `rollback_failed`, or the
  rollback routed a miner to OFFLINE / the retry budget is exhausted), so `PrepareParticipantsForNewRound` returns via
  `RETURN CALL RoundAbort(...)`.
- **Expected:** `PrepareParticipantsForNewRound`'s RETURNS union lists `round_aborted(abort_record)` (the exact shape, not a
  bare `round_aborted`), and the actual value returned by `RoundAbort` is `round_aborted(abort_record(RoundID, TemplateID,
  reason))` — declared shape and actual value coincide, payload included.

## TV237 — ContinueTemplateRefreshAssignmentSetup and TemplateRefresh propagate the exact shape (AB1)

- **Procedures:** `ContinueTemplateRefreshAssignmentSetup`, `TemplateRefresh`, `RoundAbort`.
- **Setup:** a template-refresh setup fails and aborts; the abort propagates up through
  `ContinueTemplateRefreshAssignmentSetup` and `TemplateRefresh`.
- **Expected:** both procedures' RETURNS unions list `round_aborted(abort_record)` — no bare `round_aborted` alias appears
  in either contract — and each propagates the exact `round_aborted(abort_record)` value returned by `RoundAbort`.

## TV238 — A SetupRetryEvent guard abort captures the result, then stores that exact disp (AB2)

- **Procedures:** `SetupRetryEvent`, `RoundAbort`.
- **Setup:** a SEATED retry's genuine dispatch reaches a guard-driven abort (wrong round state, retry budget exhausted, or
  incompatible participant state).
- **Expected:** the handler executes `SET disp <- CALL RoundAbort(...)` FIRST; then
  `UPDATE setup_retry_records[SetupRetryID].status <- ABORTED` and
  `UPDATE setup_retry_records[SetupRetryID].target_disposition <- disp`; then `RETURN disp`. The stored
  `target_disposition` is the exact `round_aborted(abort_record(RoundID, TemplateID, reason))` returned by `RoundAbort`, not
  a bare token written before the abort result existed.

## TV239 — A SEATED record's first dispatch flips SEATED -> APPLYING via a keyed persistent update (AB3)

- **Procedures:** `SetupRetryEvent`.
- **Setup:** a published SEATED record's genuine event dispatches (ownership and payload verified, round current, template
  identity holds, within budget, participants compatible).
- **Expected:** the transition is `ATOMICALLY: UPDATE setup_retry_records[SetupRetryID].status <- APPLYING` — an explicit
  keyed update of the registry entry. Modifying only a local snapshot (`rec.status`) cannot satisfy the test: the persisted
  map entry must read `APPLYING`. `rec` is a read-only snapshot; the seat remains the only CREATE.

## TV240 — An APPLYING target that closes the round finishes ABORTED via the persisted flag, never APPLIED (AB4)

- **Procedures:** `SetupRetryEvent`, `CancelSetupRetriesForRound`, `CloseRoundAssignments`, `RoundAbort`.
- **Setup:** a SEATED record dispatches, flips to `APPLYING`, and calls its target; the target synchronously invokes
  `RoundAbort` → `CloseRoundAssignments` → `CancelSetupRetriesForRound`, which PERSISTS
  `terminal_closure_pending <- true` on THIS record by key; then the target returns.
- **Expected:** after the target returns, `SetupRetryEvent` RE-READS `post_target_rec <-
  setup_retry_records[SetupRetryID]` and observes `post_target_rec.terminal_closure_pending = true`; it finishes the record
  `ABORTED` (the target disposition is `round_aborted(abort_record)`) — and could never finish `APPLIED`. Classifying on a
  pre-target snapshot would miss the persisted flag and is explicitly disallowed.

## TV241 — A foreign event with a valid SetupRetryID but different dispatched_event_ref stale-noops (AB5-B)

- **Procedures:** `SetupRetryEvent`.
- **Setup:** an event carries a valid, known `SetupRetryID` whose record is SEATED, but its `dispatched_event_ref` does NOT
  equal `rec.event_ref` (a foreign or replayed dispatch).
- **Expected:** the ownership check `dispatched_event_ref != rec.event_ref` fires; `SetupRetryEvent` returns
  `setup_retry_stale_noop(SetupRetryID)` and takes NO ownership — the record remains `SEATED` and its genuine queued event
  is left to dispatch. The foreign event cannot terminalise or advance a record it does not own.

## TV242 — The genuine event_ref dispatches with a corrupted payload -> integrity abort, no SEATED record left (AB5-C)

- **Procedures:** `SetupRetryEvent`, `RoundAbort`.
- **Setup:** the record's genuine event dispatches (`dispatched_event_ref = rec.event_ref`) but its payload
  (RoundID / setup_kind / TemplateID_at_seat / TemplateRefreshSetupID / retry_generation) disagrees with the immutable
  record.
- **Expected:** this is corruption of the owning event; `SetupRetryEvent` cancels any residual `rec.event_ref` on EQ,
  executes `SET disp <- CALL RoundAbort(reason = setup_retry_payload_integrity_failure(setup_kind), ...)`, persists
  `status <- ABORTED` and `target_disposition <- disp` by key, and returns `disp`. The record cannot remain `SEATED` with
  its only event consumed.

## TV243 — Round closure terminalises SEATED records and flags an APPLYING record, all by key (AB6)

- **Procedures:** `CancelSetupRetriesForRound`, `CloseRoundAssignments`.
- **Setup:** a round with two SEATED setup-retry records and one APPLYING record is closed.
- **Expected:** `CancelSetupRetriesForRound` iterates the matching `SetupRetryID`s; for each SEATED record it cancels the
  queued `event_ref`, `UPDATE ...event_ref <- null`, `UPDATE ...status <- CANCELLED`, `UPDATE ...target_disposition <-
  cancellation_reason`; for the APPLYING record it `UPDATE ...terminal_closure_pending <- true`. After it completes, for the
  closing RoundID: no record has `status = SEATED`, no SEATED record holds a queued `event_ref`, every terminalised record
  has a terminal `target_disposition`, and the APPLYING record has `terminal_closure_pending` persisted. No queued
  `SetupRetryEvent` for the round survives.

---

## Coverage summary

| Vector | Correction | Primary procedures |
|--------|-----------|--------------------|
| TV236 | AB1 | `PrepareParticipantsForNewRound`, `RoundAbort` |
| TV237 | AB1 | `ContinueTemplateRefreshAssignmentSetup`, `TemplateRefresh`, `RoundAbort` |
| TV238 | AB2 | `SetupRetryEvent`, `RoundAbort` |
| TV239 | AB3 | `SetupRetryEvent` |
| TV240 | AB4 | `SetupRetryEvent`, `CancelSetupRetriesForRound`, `CloseRoundAssignments` |
| TV241 | AB5 | `SetupRetryEvent` |
| TV242 | AB5 | `SetupRetryEvent`, `RoundAbort` |
| TV243 | AB6 | `CancelSetupRetriesForRound`, `CloseRoundAssignments` |

All eight vectors are specified against exact procedures and preconditions in the current
`STAGE_01_PROTOCOL_PSEUDOCODE.md` and `STAGE_01_MINER_STATE_MACHINE.md`; none assumes an unwritten guard, transition,
edge, or result name; and all preserve the A1 baseline `8.420833333 kWh`.
