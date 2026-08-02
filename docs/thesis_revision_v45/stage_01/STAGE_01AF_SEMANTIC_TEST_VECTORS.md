# Stage 1AF — Semantic Test Vectors (TV273–TV287)

These blocking paper test vectors exercise corrections AF1–AF10 of the executable dispatch-binding & queue-pop lock. Each
vector names the EXACT procedures and preconditions it drives, states the required outcome, and asserts NO behaviour not
written in `STAGE_01_PROTOCOL_PSEUDOCODE.md` / `STAGE_01_MINER_STATE_MACHINE.md` / `STAGE_01_ROUND_STATE_MACHINE.md` (no
assumed guard, transition, edge, or result name). Every vector preserves the A1 baseline (`8.420833333 kWh`). The algorithm
is **PoCol** and the mechanism under test is the idle policy within PoCol.

Terminology: the §0.7g-schema is the executable `event_descriptor` set (AF1); `BuildHandlerInvocation` binds the exact named
handler arguments (AF2); `ScheduleEvent` enforces the full descriptor schema before any mutation (AF3); the six driver-event
wrappers dispatch the domain procedures (AF4); `ProcessEventTime` atomically POPs before dispatch and treats `EQ.event_queue`
as the ONE representation of the pending QUEUED frontier (AF5); `RunContext` owns every per-run field (AF6); `StartHashing`
and `HashWorkEvent` RETURN explicitly with matching shapes (AF7); `SeatAcceptanceBatchFinalize` is the single seat owner
(AF8); `HandleDispatchIntegrityFailure` never raw-asserts on a corrupt reverse binding (AF9).

---

## TV273 — RoundInitialiseEvent mints RoundID; payload is only round_setup_seq (AF1/AF4)

- **Procedures:** `ProcessEventTime`, `BuildHandlerInvocation`, `RoundInitialiseEvent`, `RoundInitialise`.
- **Setup:** a `RoundInitialiseEvent` record is dispatched; its `event_descriptor` declares `allowed_payload_keys =
  { round_setup_seq : Integer }`, `runtime_injected = { RunContext }`, `recv env = no`, `recv ref = no`.
- **Expected:** `BuildHandlerInvocation` injects `RunContext` (never a `RoundContext`, never a `dispatch_envelope`); the wrapper
  resolves `config <- RunContext.config` and `prior_state <- RunContext.prior_round_terminal_state`, calls
  `RoundInitialise(config, RunContext, prior_state)` which MINTS a fresh `RoundID`, publishes `RunContext.current_round_context`,
  and returns `round_initialised(RoundID)`. `RoundID` is a DERIVED value — it is NOT a payload key and NOT the stable tie key
  (which is `(round_setup_seq)`).

## TV274 — TemplateCommitEvent mints TemplateID from candidate_template (AF1/AF4)

- **Procedures:** `ProcessEventTime`, `BuildHandlerInvocation`, `TemplateCommitEvent`, `TemplateCommit`.
- **Setup:** a `TemplateCommitEvent` record with `allowed_payload_keys = { RoundID_at_seat : RoundID, candidate_template :
  CandidateTemplate }`; `round_state = TEMPLATE_COMMITMENT`; `RoundID_at_seat = RoundID_current`.
- **Expected:** the wrapper calls `TemplateCommit(RoundContext, candidate_template)`, which MINTS `TemplateID` and returns it;
  the wrapper returns `template_committed(RoundID_current, TemplateID)`. `TemplateID` is DERIVED, not read from any payload key
  (the AE4 row that listed `TemplateID` as required payload is superseded). If `RoundID_at_seat != RoundID_current` the wrapper
  returns `template_commit_stale_noop(RoundID_at_seat)` and mints nothing.

## TV275 — MinerRegisterEvent derives MinerID from join_request (AF1/AF4)

- **Procedures:** `ProcessEventTime`, `BuildHandlerInvocation`, `MinerRegisterEvent`, `MinerRegister`.
- **Setup:** a `MinerRegisterEvent` record with `allowed_payload_keys = { join_request : JoinRequest }`; `recv env = yes`.
- **Expected:** `BuildHandlerInvocation` binds `join_request -> join_request` and injects `RoundContext` + `dispatch_envelope`;
  the wrapper calls `MinerRegister(RoundContext, join_request, dispatch_envelope)`, which DERIVES `MinerID`; the wrapper returns
  `miner_registered(MinerID)`. `MinerID` is DERIVED, not a payload key (the AE4 row that listed `MinerID` as payload is
  superseded); the stable tie key is `(join_request_id(join_request))`.

## TV276 — WakeCompleteEvent resolves target_assignment via version(AssignmentID, assignment_version) (AF1/AF2)

- **Procedures:** `ProcessEventTime`, `BuildHandlerInvocation`, `WakeCompleteEvent`.
- **Setup:** a `WakeCompleteEvent` record with `allowed_payload_keys = { MinerID, AssignmentID, assignment_version }`
  (assignment_version now present); the miner is `WAKING` bound to that exact version.
- **Expected:** `BuildHandlerInvocation` binds `MinerID -> MinerID` and resolves `target_assignment <-
  version(payload.AssignmentID, payload.assignment_version)`, injects `RoundContext` + `dispatch_envelope`, and calls
  `WakeCompleteEvent(RoundContext, MinerID, target_assignment, dispatch_envelope)`. The handler receives the resolved
  `target_assignment` — never a bare `AssignmentID`. The stable tie key is `(MinerID, AssignmentID, assignment_version)`.

## TV277 — ReserveActivateEvent passes a scheduling_context wrapper; never a bare envelope (AF1/AF2)

- **Procedures:** `ProcessEventTime`, `BuildHandlerInvocation`, `ReserveActivateEvent`, `ReserveActivate`.
- **Setup:** a `ReserveActivateEvent` record with `allowed_payload_keys = { RoundID_at_seat, deficit, activation_seq }`;
  `recv env = yes`; `round_state in {SECURITY_RECOVERY, ASSIGNMENT}`.
- **Expected:** `BuildHandlerInvocation` binds `deficit -> deficit` and injects `RoundContext` + `dispatch_envelope` to the
  WRAPPER; the wrapper calls `ReserveActivate(RoundContext, deficit, scheduling_context = ORDINARY_DISPATCH(dispatch_envelope))`.
  A BARE `dispatch_envelope` NEVER reaches `ReserveActivate` (closing the AE5 executable-line defect). The reserve `MinerID` is
  SELECTed inside `ReserveActivate` (a derived value); the tie key is `(RoundID_at_seat, activation_seq)`, never `(MinerID)`.

## TV278 — BlockAcceptancePoint receives no dispatch_envelope and no dispatched_event_ref (AF1/AF2)

- **Procedures:** `ProcessEventTime`, `BuildHandlerInvocation`, `BlockAcceptancePoint`.
- **Setup:** a `BlockAcceptancePoint` record; its descriptor has `recv env = no`, `recv ref = no`.
- **Expected:** `BuildHandlerInvocation` builds args = { RoundContext, certificate, snapshot, CandidateID, PropagationID,
  outcome } — and the defensive `ASSERT (dispatch_envelope in args) = (recv_env = yes)` holds with BOTH sides false, and the
  `dispatched_event_ref` assertion likewise. No undeclared `dispatch_envelope` or `dispatched_event_ref` is injected (closing
  the AD5/AE5 defect); `BlockAcceptancePoint`'s INPUTS omit both.

## TV279 — ScheduleEvent rejects an unknown event_type before any mutation (AF3)

- **Procedures:** `ScheduleEvent`.
- **Setup:** a scheduling request whose `event_type` has NO descriptor in §0.7g-schema.
- **Expected:** `ScheduleEvent` returns `rejected_event_type_unknown(event_type)` BEFORE minting `seq`, deriving the EventRef,
  registering the record, or inserting into EQ. No `queued_event_registry` entry and no EQ entry is created. No raw assertion.

## TV280 — ScheduleEvent rejects a wrong target_microphase (AF3)

- **Procedures:** `ScheduleEvent`.
- **Setup:** a request for a declared `event_type` whose `target_microphase` differs from `descriptor(event_type).target_microphase`
  (e.g. a `HashWorkEvent` targeted at `WAKE_COMPLETE`).
- **Expected:** `ScheduleEvent` returns `rejected_microphase_mismatch(event_type, target_microphase, expected_microphase)`
  before any mutation. Nothing is enqueued.

## TV281 — ScheduleEvent rejects an EXTRA payload key (exact closed set) before any mutation (AF3)

- **Procedures:** `ScheduleEvent`.
- **Setup:** a `WakeCompleteEvent` request whose payload carries `{ MinerID, AssignmentID, assignment_version, foo }` — an
  EXTRA key `foo` not in `allowed_payload_keys`.
- **Expected:** `ScheduleEvent` computes `extra_fields = { foo }` and returns `rejected_payload_schema_mismatch(event_type,
  missing_fields = {}, extra_fields = { foo }, type_invalid_fields = {})` BEFORE any state mutation. A missing key or a
  wrong-typed value is rejected the same way (the AE7 required-fields-only check permitted extra keys; AF3 supersedes it).

## TV282 — ScheduleEvent rejects an underivable stable tie key (AF3)

- **Procedures:** `ScheduleEvent`.
- **Setup:** a request whose validated payload does not carry every key named by `descriptor(event_type).stable_tie_key`
  (a constructed corner case where the tie-key inputs are absent).
- **Expected:** `ScheduleEvent` returns `rejected_stable_tie_key_unavailable(event_type)` before any mutation — the event
  cannot be totally ordered, so it is not enqueued. When the tie key IS derivable, EQ is ordered by
  `descriptor.stable_tie_key`, never the generic `(CandidateID, MinerID, AssignmentID)` tuple.

## TV283 — ProcessEventTime atomically POPs, sets the complete context, dispatches, then CONSUMEs and clears (AF5)

- **Procedures:** `ProcessEventTime`, `BuildHandlerInvocation`.
- **Setup:** one QUEUED event `E` at the current `(t, delta_cycle)`; `EQ.event_queue` holds pending QUEUED events only.
- **Expected:** `ProcessEventTime` ATOMICALLY POPs `E` from `EQ.event_queue`, asserts `queued_event_registry[E].queue_status =
  QUEUED`, sets it `DISPATCHING`, and sets `EQ.current_event_time / current_delta_cycle / current_microphase / current_event_seq
  / current_event_ref` from `E.*` — all indivisibly; dispatches via `BuildHandlerInvocation`; then ATOMICALLY sets `E` `CONSUMED`
  and CLEARS every `EQ.current_*`. While `DISPATCHING`, `E` is NOT on `EQ.event_queue` (the ONE representation). No "by
  projection" inference is used.

## TV284 — A mid-batch cancelled same-cycle event is removed from EQ and never POPped (AF5, preserves AE3)

- **Procedures:** `ProcessEventTime`, a round-closing handler, `CancelQueuedEvent`.
- **Setup:** two events `A` and `B` share one `(t, delta_cycle)`, `A` ordered before `B`; `A`'s handler closes the round, whose
  closure cancels `B` via `CancelQueuedEvent` (`B` → `CANCELLED`, removed from `EQ.event_queue`).
- **Expected:** `ProcessEventTime` POPs and dispatches `A`, then RE-POPs the front of `EQ.event_queue`; `B` is already absent
  from `EQ.event_queue` (removed by `CancelQueuedEvent`), so it is never POPped and never dispatched. No stale-snapshot skip
  guard is needed because the POP re-queries the live frontier each iteration.

## TV285 — StartHashing and HashWorkEvent RETURN with matching result shapes (AF7)

- **Procedures:** `StartHashing`, `ScheduleNextHashWork`, `HashWorkEvent`.
- **Setup:** a miner in `ACTIVE_HASHING` with a `CURRENT` assignment; the first unit seats successfully; a later unit is
  scheduled as the continuation.
- **Expected:** `StartHashing` on `hash_work_seated(event_ref)` RETURNs `hashing_started(event_ref)` EXPLICITLY (no successful
  fall-through without a RETURN), and RETURNs `hashing_not_started(reason)` at the horizon. `HashWorkEvent`'s continuation
  RETURNs `continued(hash_work_seated(EventRef))` (or `continued(hash_work_not_seated(reason))` at the horizon), matching its
  declared RETURNS union shape exactly — never a bare `hash_work_seated`.

## TV286 — SeatAcceptanceBatchFinalize seats exactly one live finalize per (timestamp, point); replay-safe (AF8)

- **Procedures:** `BlockAcceptancePoint`, `SeatAcceptanceBatchFinalize`, `ScheduleEvent`.
- **Setup:** two `BlockAcceptancePoint` arrivals at the SAME `(now, acceptance_point)` register into
  `acceptance_batch_registry[(now, acceptance_point)]`, each calling `SeatAcceptanceBatchFinalize`.
- **Expected:** the FIRST call seats through `ScheduleEvent` with the descriptor payload `{ acceptance_timestamp, acceptance_point }`,
  stores the EventRef in `acceptance_batch_finalize_seat[(now, acceptance_point)]`, and returns
  `acceptance_batch_finalize_seated(event_ref)`. The SECOND call finds the live QUEUED seat and returns
  `acceptance_batch_finalize_already_seated(event_ref)` — NO second seat, NO unregistered queued event. The stored EventRef is
  cancellable through `CancelQueuedEvent` (RoundAbort cancels it).

## TV287 — HandleDispatchIntegrityFailure records corruption without asserting, mutating, or aborting (AF9)

- **Procedures:** `ProcessEventTime`, `HandleDispatchIntegrityFailure`.
- **Setup:** a corrupt `SetupRetryEvent` record `er` whose reverse binding is corrupt — `setup_retry_by_seat_event_ref[er]`
  points to a record whose `seat_event_ref != er` (or the owner record is missing, or two records claim `er`).
- **Expected:** `HandleDispatchIntegrityFailure` does NOT raw-ASSERT; it RECORDS `dispatch_integrity_owner_binding_corrupt(er)`
  and RETURNs it, mutating NO retry record and aborting NO round; `ProcessEventTime` then marks `er` `CONSUMED` and clears the
  context. The run does not crash under corrupted ownership metadata.

---

## Coverage summary

| Correction | Vectors |
|-----------|---------|
| AF1 executable event_descriptor set (derived id vs payload; assignment_version; RoundAbort removed) | TV273, TV274, TV275, TV276 |
| AF2 executable dispatch binding (BuildHandlerInvocation) | TV276, TV277, TV278 |
| AF3 full ScheduleEvent schema enforcement | TV279, TV280, TV281, TV282 |
| AF4 driver-event wrappers | TV273, TV274, TV275, TV277 |
| AF5 atomic POP + one representation | TV283, TV284 |
| AF6 RunContext ownership | TV273 (config/prior_state/current_round_context resolved from RunContext) |
| AF7 hashing result contract | TV285 |
| AF8 SeatAcceptanceBatchFinalize | TV286 |
| AF9 non-asserting integrity handler | TV287 |
| AF10 supersession | recorded in `STAGE_01AF_SUPERSESSION_REGISTER.md` (audited by every AF vector's superseded-claim note) |

All fifteen vectors preserve the A1 baseline (`8.420833333 kWh`), name only procedures/results defined in the normative tree,
and exercise the exact executable dispatch-binding and queue-pop contract of Stage 1AF.
