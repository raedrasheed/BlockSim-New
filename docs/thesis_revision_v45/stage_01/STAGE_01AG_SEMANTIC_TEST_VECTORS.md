# Stage 1AG — Semantic Test Vectors (TV288–TV298)

These blocking paper test vectors exercise corrections AG1–AG9 of the dispatch-argument, run-bootstrap & wake-payload lock.
Each vector names the EXACT procedures and preconditions it drives, states the required outcome, and asserts NO behaviour
not written in `STAGE_01_PROTOCOL_PSEUDOCODE.md` / `STAGE_01_MINER_STATE_MACHINE.md` / `STAGE_01_ROUND_STATE_MACHINE.md`.
Every vector preserves the A1 baseline (`8.420833333 kWh`). The algorithm is **PoCol** and the mechanism under test is the
idle policy within PoCol.

Terminology: `BuildHandlerInvocation` binds every handler argument from an EXPLICIT `payload_to_param_map` entry and verifies
`keys(args) = d.handler_inputs` (AG1); `StartWake` seats `WakeCompleteEvent` with `{MinerID, AssignmentID,
assignment_version}` (AG2); `RunEventLoopToHorizon`/`ProcessEventTime` take `RunContext` and resolve
`current_round_context` per dispatch (AG3/AG5); the named seat owners enqueue each wrapper (AG4); `CloseRoundAssignments`
publishes `prior_round_terminal_state` (AG6); `SeatAcceptanceBatchFinalize` is generation-keyed with a type-correct context
(AG7); `stable_tie_key` is descriptor-derived everywhere (AG8).

---

## TV288 — BuildHandlerInvocation produces args whose key set equals each wrapper INPUTS (AG1)

- **Procedures:** `BuildHandlerInvocation`, the six AF4 wrappers.
- **Setup:** dispatch each wrapper descriptor with a valid stored payload.
- **Expected:** for each wrapper, `keys(args)` EQUALS `d.handler_inputs`: `RoundInitialiseEvent` -> `{RunContext,
  round_setup_seq}`; `TemplateCommitEvent` -> `{RoundContext, RoundID_at_seat, candidate_template}`;
  `PrepareParticipantsEvent` -> `{RoundContext, RoundID_at_seat, TemplateID_at_seat, dispatch_envelope}`;
  `MinerRegisterEvent` -> `{RoundContext, join_request, dispatch_envelope}`; `ReserveActivateEvent` -> `{RoundContext,
  RoundID_at_seat, deficit, activation_seq, dispatch_envelope}`; `FullRangeExhaustEvent` -> `{RoundContext, RoundID_at_seat,
  TemplateID_at_seat, dispatch_envelope}`. `RoundID_at_seat`, `TemplateID_at_seat`, `activation_seq`, and `round_setup_seq`
  are each present via an EXPLICIT `payload_to_param_map` entry (no same-name fallback). Result is
  `handler_invocation_built(procedure, args)`.

## TV289 — StartWake seats WakeCompleteEvent with the exact assignment_version (AG2)

- **Procedures:** `StartWake`, `ScheduleEvent`.
- **Setup:** `StartWake` for `target_assignment` (AssignmentID `A`, assignment_version `v`).
- **Expected:** `StartWake` calls `ScheduleEvent(EQ, RoundContext, WakeCompleteEvent, target_event_time, WAKE_COMPLETE,
  {MinerID, AssignmentID = A, assignment_version = v})`. `ScheduleEvent` ACCEPTS the exact closed payload (AF3): omitting
  `assignment_version` would be `rejected_payload_schema_mismatch`. The returned `wake_seated` record retains
  `assignment_version = v`.

## TV290 — A wake for v1 stale-noops after v2 is created; it cannot activate v2 (AG2)

- **Procedures:** `WakeCompleteEvent`, `version(...)`.
- **Setup:** a `WakeCompleteEvent` for `(A, v1)` remains QUEUED; a renewal creates version `v2` for `A`, making `v2` the
  miner's live head and `v1` CLOSED/superseded.
- **Expected:** when the wake dispatches, `target_assignment = version(A, v1)`; the guard finds `v1` is not the live head and
  `wake_origin_version (v1) != assignment_version(live head) (v2)`, so it returns `stale_wake_noop` BEFORE any transition.
  It NEVER activates `v2`.

## TV291 — RunInitialise returns current_round_context = null; the first RoundInitialiseEvent dispatches on RunContext alone (AG3)

- **Procedures:** `RunInitialise`, `RunEventLoopToHorizon`, `SeatNextRoundBootstrap`, `ProcessEventTime`,
  `BuildHandlerInvocation`, `RoundInitialiseEvent`.
- **Setup:** `RunInitialise(config)` returns `RunContext` with `current_round_context = null`; `RunEventLoopToHorizon` calls
  `SeatNextRoundBootstrap(RunContext)`.
- **Expected:** `SeatNextRoundBootstrap` seats `RoundInitialiseEvent` via `ScheduleEvent` with `RoundContext = null` (its
  descriptor injects `RunContext`, not `RoundContext`). `ProcessEventTime` dispatches it while `current_round_context = null`
  (no `dispatch_context_unavailable`), and `RoundInitialiseEvent` publishes the first RoundContext with no circular input.

## TV292 — Immediately after RoundInitialiseEvent, TemplateCommitEvent uses the freshly published context (AG5)

- **Procedures:** `RoundInitialiseEvent`, `SeatTemplateCommit`, `ProcessEventTime`, `TemplateCommitEvent`.
- **Setup:** `RoundInitialiseEvent` publishes `RunContext.current_round_context <- rc` and calls
  `SeatTemplateCommit(RunContext, rc.RoundID, candidate_template)`.
- **Expected:** when `TemplateCommitEvent` dispatches, `ProcessEventTime` resolves `dispatch_round_context <-
  RunContext.current_round_context = rc` (the NEW round), NOT a null/placeholder/previous context; `TemplateCommitEvent`
  commits for `rc.RoundID`.

## TV293 — Every AF4 wrapper has a literal named ScheduleEvent seating path and a bounded idempotence identity (AG4)

- **Procedures:** `SeatNextRoundBootstrap`, `SeatTemplateCommit`, `SeatPrepareParticipants`, `SeatMinerRegister`,
  `SeatReserveActivate`, `SeatFullRangeExhaust`.
- **Setup:** invoke each owner twice with the same identity.
- **Expected:** each owner calls `ScheduleEvent` with its wrapper's exact closed payload and stores the seated `EventRef` in
  `RunContext.driver_event_seat` keyed by a bounded identity (e.g. `(ROUND_INITIALISE, round_setup_seq)`, `(TEMPLATE_COMMIT,
  RoundID_at_seat, candidate_template_id)`). The SECOND invocation with a live/consumed seat returns `*_already_seated`
  (no second seat) — replay cannot create two rounds or commit one template twice.

## TV294 — Round closure publishes the exact prior terminal round; the next RoundInitialise rebases (AG6)

- **Procedures:** `CloseRoundAssignments`, `SeatNextRoundBootstrap`, `RoundInitialiseEvent`, `RoundInitialise`,
  `SettleResidencyBoundary`.
- **Setup:** a round closes (`ROUND_ACCEPTED` or `ROUND_ABORTED`) via `CloseRoundAssignments`; simulated time remains.
- **Expected:** `CloseRoundAssignments` sets `RunContext.prior_round_terminal_state <- current_round_context` (carrying
  RoundID, round_terminal_time, residency_ledger, terminal disposition) and calls `SeatNextRoundBootstrap`. The next
  `RoundInitialiseEvent` passes `prior_state = RunContext.prior_round_terminal_state` to `RoundInitialise`, which performs
  `SettleResidencyBoundary(REBASE_TO_NEXT_ROUND, prior_state = that exact terminal RoundContext)` using its
  `round_terminal_time` and `residency_ledger`. `prior_round_terminal_state` is not null.

## TV295 — BlockAcceptancePoint passes a type-correct context and handles every seat result (AG7)

- **Procedures:** `BlockAcceptancePoint`, `SeatAcceptanceBatchFinalize`, `ScheduleEvent`.
- **Setup:** a block arrival at `(now, acceptance_point)`.
- **Expected:** `BlockAcceptancePoint` calls `SeatAcceptanceBatchFinalize(RoundContext, now, acceptance_point)` with NO
  `source_context` (no `ORDINARY_DISPATCH(EventRef)` is built); `ScheduleEvent` uses the trusted dispatcher current context.
  On `acceptance_batch_finalize_seated`/`_already_seated` the arrival is registered into that generation's batch and the
  handler returns `registered`; on `acceptance_batch_finalize_seat_failed` NO batch entry is created (nothing stranded) and
  the candidate is failed candidate-scoped. A pending batch can never lack a finalize event.

## TV296 — A later-delta same-timestamp arrival opens a new batch generation + finalize (AG7)

- **Procedures:** `BlockAcceptancePoint`, `SeatAcceptanceBatchFinalize`, `AcceptanceBatchFinalize`.
- **Setup:** generation 0's `AcceptanceBatchFinalize` for `(t, point)` has already dispatched (CONSUMED); a NEW block arrival
  at the same `t` appears in a later delta cycle.
- **Expected:** `SeatAcceptanceBatchFinalize` observes the current generation's seat is terminal and seats generation 1 with
  a fresh `AcceptanceBatchFinalize` (payload `batch_generation = 1`); the new arrival registers into
  `acceptance_batch_registry[(t, point, 1)]`, which generation-1 finalize processes. No arrival is stranded.

## TV297 — The root §0.2 rule and ScheduleEvent derive stable_tie_key from the same descriptor (AG8)

- **Procedures:** §0.2 event-envelope contract, `ScheduleEvent`.
- **Setup:** inspect the ordering rule in §0.2 and the EQ INSERT in `ScheduleEvent`.
- **Expected:** both state `stable_tie_key = descriptor(event_type).stable_tie_key(immutable_payload)`; no universal
  `(CandidateID, MinerID, AssignmentID)` tuple is authoritative anywhere (§0.2, ScheduleEvent, I21, terminology,
  traceability agree on the one descriptor-derived rule).

## TV298 — A missing wrapper argument yields handler_invocation_binding_failed before the handler call (AG1)

- **Procedures:** `BuildHandlerInvocation`, `ProcessEventTime`.
- **Setup:** construct (defensively) a descriptor whose `payload_to_param_map` would omit one required wrapper argument, so
  the produced `args` lack a member of `d.handler_inputs`.
- **Expected:** `BuildHandlerInvocation` computes non-empty `missing_args` and returns
  `handler_invocation_binding_failed(event_type, missing_args, extra_args)` — NOT a raw assertion. `ProcessEventTime` records
  `dispatch_binding_failed`, marks the event CONSUMED, and does NOT call the handler.

---

## Coverage summary

| Correction | Vectors |
|-----------|---------|
| AG1 explicit wrapper payload bindings + verify | TV288, TV298 |
| AG2 wake seat carries + verifies assignment_version | TV289, TV290 |
| AG3 executable first-round bootstrap | TV291 |
| AG4 named driver-event seating owners | TV293 |
| AG5 current round context after rotation | TV292 |
| AG6 publish prior terminal round + rebase | TV294 |
| AG7 acceptance-batch context / result / generation | TV295, TV296 |
| AG8 descriptor-derived root ordering | TV297 |
| AG9 supersession | recorded in `STAGE_01AG_SUPERSESSION_REGISTER.md` (audited by each AG vector's superseded-claim note) |

All eleven vectors preserve the A1 baseline (`8.420833333 kWh`), name only procedures/results defined in the normative
tree, and exercise the exact dispatch-argument, run-bootstrap, and wake-payload contract of Stage 1AG.
