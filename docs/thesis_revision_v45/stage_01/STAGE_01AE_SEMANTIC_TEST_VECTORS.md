# Stage 1AE — Semantic Test Vectors (TV262–TV272)

These blocking paper test vectors exercise corrections AE1–AE11 of the global-event cancellation and dispatch-schema lock.
Each vector names the EXACT procedures and preconditions it drives, states the required outcome, and asserts NO behaviour not
written in `STAGE_01_PROTOCOL_PSEUDOCODE.md` / `STAGE_01_MINER_STATE_MACHINE.md` (no assumed guard, transition, edge, or
result name). Every vector preserves the A1 baseline (`8.420833333 kWh`). The algorithm is **PoCol** and the mechanism under
test is the idle policy within PoCol.

Terminology: `CancelQueuedEvent(EventRef, cancellation_reason, cancellation_context)` is the SOLE queue-owner cancellation
(AE1); §0.7g-schema is the authoritative event-type dispatch schema (AE4); `ProcessEventTime` re-selects/re-reads each
iteration (AE3) and dispatches only schema-declared arguments (AE5 Design B); `setup_retry_by_seat_event_ref` binds a corrupt
retry's owner by EventRef (AE6); `ScheduleEvent` returns `rejected_payload_schema_mismatch` before any mutation (AE7) and
registers atomically (AE8); coherence invariant I21 (AE10).

---

## TV262 — HandlePropagationFailure cancels a QUEUED CertificateArrival through the queue owner (AE1/AE2)

- **Procedures:** `HandlePropagationFailure`, `CancelQueuedEvent`.
- **Setup:** a `CertificateArrival` EventRef `E` is `QUEUED` (`queued_event_registry[E].queue_status = QUEUED`, `E` pending on
  EQ); `HandlePropagationFailure` fails the candidate and iterates `certificate_arrival_events(cpc)`.
- **Expected:** for `E` it calls `CancelQueuedEvent(E, …)`, which ATOMICALLY removes `E` from `EQ.event_queue` and sets
  `queued_event_registry[E].queue_status <- CANCELLED`, returning `event_cancelled(E)`. No raw `CANCEL E on EQ` occurs; no
  QUEUED ghost of `E` remains (I21).

## TV263 — AbortPendingWakeForRollback cancels a QUEUED WakeCompleteEvent through the same owner (AE1/AE2)

- **Procedures:** `AbortPendingWakeForRollback`, `CancelQueuedEvent`.
- **Setup:** a wake rollback holds `WakeEventRef = W` for a `QUEUED` `WakeCompleteEvent`.
- **Expected:** `AbortPendingWakeForRollback` calls `CancelQueuedEvent(W, …)` (not a raw EQ cancel); `W` is removed from EQ and
  its registry status becomes `CANCELLED` atomically. No QUEUED ghost remains, and a later re-read of `W` yields
  `CANCELLED`.

## TV264 — A handler cancels a later same-cycle event; ProcessEventTime never dispatches it (AE3)

- **Procedures:** `ProcessEventTime`, a round-closing handler, `CancelQueuedEvent`.
- **Setup:** two events `A` and `B` share one `(t, delta_cycle)`, `A` ordered before `B`. `A`'s handler closes the round,
  whose closure cancels `B` via `CancelQueuedEvent` (`B` → `CANCELLED`, removed from EQ).
- **Expected:** `ProcessEventTime` dispatches `A`, then RE-QUERIES the queue at `(t, delta_cycle)`; `B` is no longer `QUEUED`
  (and not pending on EQ), so it is never selected. Even if `B` were re-selected, the re-read guard (`status != QUEUED`)
  skips it. `B` is never dispatched and no assertion fails.

## TV265 — BlockAcceptancePoint receives exactly its schema-declared arguments (AE4/AE5)

- **Procedures:** `ProcessEventTime`, `BlockAcceptancePoint`.
- **Setup:** a `QUEUED` `BlockAcceptancePoint` is dispatched. §0.7g-schema declares `BlockAcceptancePoint` with `recv env` =
  no, `recv ref` = no.
- **Expected:** `ProcessEventTime` dispatches `BlockAcceptancePoint` with its `immutable_payload` only; it does NOT pass
  `dispatch_envelope` (nor `dispatched_event_ref`), because the schema declares neither. No undeclared argument is injected.

## TV266 — The authoritative schema covers every target and matches every handler INPUTS (AE4)

- **Procedures:** `ScheduleEvent`, `ProcessEventTime`, every queued handler.
- **Setup:** enumerate every `ScheduleEvent` target and every dispatched handler.
- **Expected:** every `ScheduleEvent` target `event_type` appears in §0.7g-schema, and each schema row's required
  `immutable_payload` fields + `recv env` + `recv ref` match that handler's declared INPUTS. `ScheduleEvent` validates a
  request's payload against the row; `ProcessEventTime` dispatches exactly the row's declared arguments.

## TV267 — A corrupt SetupRetryEvent missing SetupRetryID resolves its owner from the EventRef (AE6)

- **Procedures:** `ProcessEventTime`, `HandleDispatchIntegrityFailure`, `SetSetupRetryStatus`, `RoundAbort`.
- **Setup:** a `SetupRetryEvent` whose `immutable_payload` is detected corrupt and is MISSING its `SetupRetryID`; its trusted
  dispatched EventRef `er` is in `setup_retry_by_seat_event_ref` mapping to `owner_id` (a current nonterminal-round SEATED
  record).
- **Expected:** `HandleDispatchIntegrityFailure` resolves `owner_id <- setup_retry_by_seat_event_ref[er]`, asserts
  `setup_retry_records[owner_id].seat_event_ref = er`, and terminalises ONLY that record (`SEATED → APPLYING → ABORTED` via a
  current-round `RoundAbort` with the complete integrity envelope). No SEATED owner remains after the event is consumed; the
  missing payload id is never needed.

## TV268 — A corrupt payload naming a foreign SetupRetryID leaves that record untouched (AE6)

- **Procedures:** `HandleDispatchIntegrityFailure`, `SetSetupRetryStatus`.
- **Setup:** a corrupt `SetupRetryEvent` whose dispatched EventRef `er` owns `owner_id`, but whose (corrupt) payload NAMES a
  different valid `foreign_id != owner_id`.
- **Expected:** the owner is resolved from `er` (→ `owner_id`); the mismatch is audited
  (`setup_retry_owner_mismatch`); the FOREIGN record `foreign_id` is NOT touched; only `owner_id` is dispositioned. A corrupt
  payload never chooses which retry record is aborted.

## TV269 — An incomplete payload is rejected before any state mutation (AE7/AE8)

- **Procedures:** `ScheduleEvent`.
- **Setup:** a caller invokes `ScheduleEvent` with an `immutable_payload` missing a required field for the target
  `event_type` (per §0.7g-schema).
- **Expected:** `ScheduleEvent` returns `rejected_payload_schema_mismatch(event_type, missing_or_invalid_fields)` BEFORE it
  increments `event_creation_seq`, derives the `EventRef`, registers a `queued_event_record`, or inserts into EQ. No seq is
  consumed, no registry entry is created, and nothing is enqueued (atomicity, AE8).

## TV270 — ScheduleNextHashWork past the horizon reports not-seated, never scheduled (AE9)

- **Procedures:** `ScheduleNextHashWork`, `ScheduleEvent`.
- **Setup:** `ScheduleNextHashWork` targets `now + modeled_hash_step_time > T`, so `ScheduleEvent` returns
  `post_horizon_event_rejected` (O2).
- **Expected:** `ScheduleNextHashWork` returns `hash_work_not_seated(post_horizon_event_rejected)` — NEVER `scheduled`. The
  caller (`StartHashing` / `HashWorkEvent`) reports the truthful continuation disposition (hashing ends at the horizon).

## TV271 — After mixed dispatch and cancellation the queue and registry are coherent (AE10 / I21)

- **Procedures:** `ScheduleEvent`, `ProcessEventTime`, `CancelQueuedEvent`.
- **Setup:** a mix of seated, dispatched, and cancelled events across a `(t, delta_cycle)`.
- **Expected:** the I21 coherence invariants hold — every `QUEUED` registry entry corresponds to exactly one pending EQ
  entry; `DISPATCHING` corresponds only to the currently-executing EventRef (absent from pending EQ); every `CONSUMED` or
  `CANCELLED` entry is absent from EQ; and after `ProcessEventTime(t)` no event at `t` is `QUEUED` or `DISPATCHING`.

## TV272 — Cancellation of a DISPATCHING event is a no-op; the dispatcher completes it (AE1)

- **Procedures:** `CancelQueuedEvent`, `ProcessEventTime`.
- **Setup:** a cancellation is attempted on an EventRef whose `queue_status = DISPATCHING` (its handler is mid-flight).
- **Expected:** `CancelQueuedEvent` returns `event_already_dispatching(EventRef)` with NO mutation (the queue state is not
  rewritten and the event is not removed). `ProcessEventTime`, the sole dispatch owner, later completes
  `DISPATCHING → CONSUMED` when the handler returns.

---

## Coverage summary

| Vector | Correction | Primary procedures |
|--------|-----------|--------------------|
| TV262 | AE1/AE2 | `HandlePropagationFailure`, `CancelQueuedEvent` |
| TV263 | AE1/AE2 | `AbortPendingWakeForRollback`, `CancelQueuedEvent` |
| TV264 | AE3 | `ProcessEventTime`, `CancelQueuedEvent` |
| TV265 | AE4/AE5 | `ProcessEventTime`, `BlockAcceptancePoint` |
| TV266 | AE4 | `ScheduleEvent`, `ProcessEventTime`, all handlers |
| TV267 | AE6 | `HandleDispatchIntegrityFailure`, `SetSetupRetryStatus`, `RoundAbort` |
| TV268 | AE6 | `HandleDispatchIntegrityFailure` |
| TV269 | AE7/AE8 | `ScheduleEvent` |
| TV270 | AE9 | `ScheduleNextHashWork`, `ScheduleEvent` |
| TV271 | AE10 (I21) | `ScheduleEvent`, `ProcessEventTime`, `CancelQueuedEvent` |
| TV272 | AE1 | `CancelQueuedEvent`, `ProcessEventTime` |

All eleven vectors are specified against exact procedures and preconditions in the current
`STAGE_01_PROTOCOL_PSEUDOCODE.md`; none assumes an unwritten guard, transition, edge, or result name; and all preserve the
A1 baseline `8.420833333 kWh`.
