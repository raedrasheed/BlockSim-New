# Stage 1AH — Semantic Test Vectors (TV299–TV312)

These blocking paper test vectors exercise corrections AH1–AH10 of the driver-scheduling, round-rotation &
acceptance-lifecycle lock. Each vector names the EXACT procedures and preconditions it drives, states the required outcome,
and asserts NO behaviour not written in `STAGE_01_PROTOCOL_PSEUDOCODE.md` / `STAGE_01_ROUND_STATE_MACHINE.md`. Every vector
preserves the A1 baseline (`8.420833333 kWh`). The algorithm is **PoCol** and the mechanism under test is the idle policy
within PoCol.

Terminology: `ScheduleEvent` takes an explicit `scheduling_origin` — `ORDINARY_DISPATCH` / `DRIVER` / `POST_EPILOGUE` (AH1);
each round's bootstrap targets its own `BootstrapRequest.target_time` (AH2); `SeatNextRoundBootstrap` /
`SeatReserveActivate` / `SeatMinerRegister` replay on a stable id BEFORE minting a sequence (AH3); sim-driver requests are
`driver_request` records admitted before the event loop selects the next earliest time (AH4); the first round imports a
genesis miner set behind an initial-registration barrier (AH5); every bootstrap-chain seat result is inspected (AH6);
`acceptance_batch_registry` is generation-keyed and a finalize-seat failure routes through the single candidate-failure
owner (AH7); the ONE queue tie key is the descriptor-derived `stable_tie_key` (AH8).

---

## TV299 — ScheduleEvent derives delta_cycle from the explicit origin and rejects an absent origin (AH1)

- **Procedures:** `ScheduleEvent`.
- **Setup:** call `ScheduleEvent` with each of `ORDINARY_DISPATCH(octx)`, `DRIVER(dctx)`, `POST_EPILOGUE(pctx)`, then with an
  unrecognised/absent origin.
- **Expected:** for `ORDINARY_DISPATCH` the derivation reads `octx.dispatch_envelope`/`octx.dispatched_event_ref` (the §0.7-H2
  forward rule); for `DRIVER` it derives `dc = 0` reading `dctx` only (no `EQ.current_*`); for `POST_EPILOGUE` it derives
  `dc = 0` after the strictly-later check. An absent/unrecognised origin returns
  `rejected_invalid_scheduling_origin(event_type, scheduling_origin)`. No path reads `EQ.current_*` for a `DRIVER`/`POST_EPILOGUE`
  seat.

## TV300 — A DRIVER seat whose target precedes its source is rejected (AH1)

- **Procedures:** `ScheduleEvent`, `SeatReserveActivate`.
- **Setup:** build a `DriverSchedulingContext` with `target_event_time < source_event_time` and seat.
- **Expected:** `ScheduleEvent` returns `rejected_driver_target_before_source(event_type, target_event_time, source_event_time)`;
  nothing is enqueued; the seat owner propagates the structured failure (no `EQ.current_*` was read).

## TV301 — The first-round bootstrap targets run_start_time; a rotation targets next_representable(prior terminal) (AH2)

- **Procedures:** `RunInitialise`, `SeatNextRoundBootstrap`, `PublishTerminalRoundAndSeatNext`.
- **Setup:** run start (`current_bootstrap_request.BootstrapRequestID = RUN_START`), then a round closes at
  `round_terminal_time = τ < T`.
- **Expected:** the first `SeatNextRoundBootstrap` seats `RoundInitialiseEvent` at `config.run_start_time`; the rotation's
  `PublishTerminalRoundAndSeatNext` creates a `BootstrapRequest` with `target_time =
  next_representable_simulation_time(τ) > τ` and seats it there. NO subsequent bootstrap targets `run_start_time`; the fixed
  `round_bootstrap_time` does not exist.

## TV302 — PublishTerminalRoundAndSeatNext runs the required order; a horizon close seats no next round (AH2)

- **Procedures:** `CloseRoundAssignments`, `PublishTerminalRoundAndSeatNext`, `CloseRoundAtHorizon`.
- **Setup:** (a) an ordinary `ROUND_ACCEPTED` closure at `τ < T`; (b) a horizon close (`envelope_namespace = RUN_HOOK`).
- **Expected:** in (a) the owner records `round_terminal_time` → publishes `prior_round_terminal_state` → creates the
  immutable next `BootstrapRequest` → seats it → inspects the result, and asserts the round is terminal FIRST; in (b) it
  records terminal time + publishes prior state but returns `terminal_round_published_no_seat` (no next round). A bootstrap
  is never seated while the predecessor round is nonterminal (`RoundAbort` transitions to `ROUND_ABORTED` before closure).

## TV303 — A replay of the same BootstrapRequestID seats no second round (AH3)

- **Procedures:** `SeatNextRoundBootstrap`.
- **Setup:** invoke twice with the same `current_bootstrap_request` (same `BootstrapRequestID`).
- **Expected:** the first returns `round_bootstrap_seated(event_ref, brid, seq)` and advances `next_round_setup_seq`; the
  second finds `driver_event_seat[(ROUND_INITIALISE, brid)]` live/consumed and returns
  `round_bootstrap_already_seated(brid, event_ref)` — the SAME EventRef, no second `RoundInitialiseEvent`,
  `next_round_setup_seq` NOT advanced.

## TV304 — A replay of the same reserve DriverRequestID seats no second activation and mints no fresh activation_seq (AH3)

- **Procedures:** `SeatReserveActivate`.
- **Setup:** invoke twice with the same `ORDINARY_RESERVE_DEFICIT` `driver_request` (same `DriverRequestID`).
- **Expected:** the replay key `(RESERVE_ACTIVATE, DriverRequestID)` is checked BEFORE `reserve_activation_seq` is read; the
  second invocation returns `reserve_activate_already_seated(DriverRequestID, event_ref)` and does NOT read+increment
  `reserve_activation_seq` (so no fresh `activation_seq` is minted and no second `ReserveActivateEvent` is seated).

## TV305 — The event loop admits driver requests BEFORE selecting the next earliest event_time (AH4)

- **Procedures:** `RunEventLoopToHorizon`, `SeatPendingDriverRequests`, `AdmitDriverRequest`.
- **Setup:** a `MINER_JOIN` `driver_request` with `requested_event_time = t0` is PENDING when the queue's earliest event is at
  `t1 > t0`.
- **Expected:** the loop calls `SeatPendingDriverRequests` BEFORE `SET t <- earliest`, so the seated `MinerRegisterEvent` at
  `t0` is on the queue when the selection runs; the selection returns `t0` (not `t1`). Intake can never insert an event
  earlier than an already-selected `t` (there is no selected `t` during admission).

## TV306 — A seated driver request is terminalised, not left pending (AH4)

- **Procedures:** `SeatPendingDriverRequests`, `SeatMinerRegister`.
- **Setup:** a PENDING `MINER_JOIN` `driver_request`; run the intake, then run it again.
- **Expected:** after a successful seat the record becomes `status = SEATED` with `seated_event_ref` set and is REMOVED from
  `pending_driver_request_index`; the second intake does not re-seat it. A seated request is never left permanently PENDING;
  a seat failure becomes `status = REJECTED` with `disposition = driver_request_rejected(reason)`.

## TV307 — The first-round genesis set registers before participant setup (AH5)

- **Procedures:** `RoundInitialise`, `AdmitDriverRequest`, `MinerRegister`, `TemplateCommitEvent`, `SeatParticipantSetupOrAbort`,
  `PrepareParticipantsForNewRound`.
- **Setup:** first round (`prior_state = null`) with a non-empty `genesis_miner_registry`.
- **Expected:** `RoundInitialise` admits a `MINER_JOIN` `driver_request` per genesis miner and sets
  `initial_registration_barrier.expected` = the genesis MinerID set (`satisfied = false`); `TemplateCommitEvent` DEFERS
  participant setup while the barrier is pending; `MinerRegister` marks each genesis miner registered and, on completion,
  seats participant setup through `SeatParticipantSetupOrAbort`; `PrepareParticipantsForNewRound` returns
  `participant_setup_registration_barrier_pending` if invoked before the barrier is satisfied. Participant setup never runs
  before the declared initial miner set is complete.

## TV308 — A failed SeatTemplateCommit aborts the round with the declared disposition (AH6)

- **Procedures:** `RoundInitialiseEvent`, `SeatTemplateCommit`, `RoundAbort`.
- **Setup:** `SeatTemplateCommit` returns `template_commit_seat_failed(reason)`.
- **Expected:** `RoundInitialiseEvent` does NOT return success; it calls `RoundAbort(reason =
  template_commit_seat_failed_round_abort(reason))` with the dispatched round-setup frame and returns
  `round_initialise_aborted(...)`. The round is terminal (not stranded in `TEMPLATE_COMMITMENT`). (Symmetrically,
  `TemplateCommitEvent` aborts on `SeatPrepareParticipants` failure and `ExhaustionAdjudicate` aborts on
  `SeatFullRangeExhaust` failure.)

## TV309 — A failed first-round bootstrap takes the declared no-round run path (AH6)

- **Procedures:** `RunEventLoopToHorizon`, `SeatNextRoundBootstrap`, `FinalizeSimulationRunNoRound`.
- **Setup:** the FIRST `SeatNextRoundBootstrap` returns `round_bootstrap_seat_failed(brid, reason)`.
- **Expected:** `RunEventLoopToHorizon` records `run_bootstrap_failed(reason)`, calls `FinalizeSimulationRunNoRound(reason =
  bootstrap_seat_failed_run_abort)`, and returns `run_aborted_no_round(reason)` — it does NOT enter the loop, does NOT run
  the horizon sentinel, and NEVER dereferences a null `RoundContext` (`current_round_context` stays null).

## TV310 — A finalize-seat failure removes the candidate from active_propagation_set (AH7)

- **Procedures:** `BlockAcceptancePoint`, `SeatAcceptanceBatchFinalize`, `HandlePropagationFailure`.
- **Setup:** `SeatAcceptanceBatchFinalize` returns `acceptance_batch_finalize_seat_failed(reason)` for a live candidate.
- **Expected:** `BlockAcceptancePoint` (recv env = yes) calls `HandlePropagationFailure(CandidateID, PropagationID,
  failure_reason = ACCEPTANCE_BATCH_UNFINALISABLE, dispatch_envelope)`, which sets `status = FAILED`, REMOVES the candidate
  from `active_propagation_set`, cancels its remaining events, and resumes only its paused miners. The candidate is NEVER
  left `FAILED` while still in `active_propagation_set`; no arrival is registered (no stranded batch).

## TV311 — A closure cancels acceptance_batch_finalize_seat[key].EventRef (AH7)

- **Procedures:** `CloseRoundAssignments`, `RoundAbort`, `CancelQueuedEvent`.
- **Setup:** a round closes with a live `acceptance_batch_finalize_seat[key] = { generation, EventRef }`.
- **Expected:** the closure cancels `acceptance_batch_finalize_seat[key].EventRef` through `CancelQueuedEvent` (NOT the whole
  `{ generation, EventRef }` record — that was a type error) and then clears `acceptance_batch_finalize_seat`. Both the
  ACCEPTED closure path (`CloseRoundAssignments`) and the abort path (`RoundAbort`) use `.EventRef`.

## TV312 — The only authoritative queue tie key is the descriptor-derived stable_tie_key (AH8)

- **Procedures:** §0.2 ordering contract, §0.7-H2 delta-cycle rule, `ScheduleEvent`, §21 intra-type tie-break.
- **Setup:** inspect the ordering rule in §0.2, the §0.7-H2 within-microphase tie statement, the deterministic-vs-sampling
  summary, the §21 intra-type tie-break, and the `ScheduleEvent` INSERT.
- **Expected:** all state the tie key is `descriptor(event_type).stable_tie_key(immutable_payload)` then `seq`; NO surviving
  positive `(CandidateID, MinerID, AssignmentID[, seq])` tuple is authoritative anywhere. The acceptance VALUE selection
  (`candidate_hash` then `MinerID`) is present but SEPARATE (winner arbitration, not a queue key).

---

## Coverage summary

| Correction | Vectors |
|-----------|---------|
| AH1 explicit scheduling origin | TV299, TV300 |
| AH2 per-round bootstrap target + terminal-round publication | TV301, TV302 |
| AH3 stable request identity before minting | TV303, TV304 |
| AH4 driver-request records + event-loop ordering | TV305, TV306 |
| AH5 first-round miner admission | TV307 |
| AH6 handle every bootstrap-chain seat result | TV308, TV309 |
| AH7 acceptance generation lifecycle + candidate-failure owner | TV310, TV311 |
| AH8 one authoritative queue tie key | TV312 |
| AH9 identity/payload distinctions + RunContext fields | exercised structurally by TV299/TV311/TV312 (dispatch_envelope vs payload; EventRef cancellation) |
| AH10 supersession | recorded in `STAGE_01AH_SUPERSESSION_REGISTER.md` (audited by each AH vector's superseded-claim note) |

All fourteen vectors preserve the A1 baseline (`8.420833333 kWh`), name only procedures/results defined in the normative
tree, and exercise the exact driver-scheduling, round-rotation, and acceptance-lifecycle contract of Stage 1AH.
