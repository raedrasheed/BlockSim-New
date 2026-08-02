# Stage 1AI — Semantic Test Vectors (TV313–TV324)

These blocking paper test vectors exercise corrections AI1–AI10 of the genesis-admission, driver-request-completion &
rotation-result lock. Each vector names the EXACT procedures and preconditions it drives, states the required outcome, and
asserts NO behaviour not written in `STAGE_01_PROTOCOL_PSEUDOCODE.md` / `STAGE_01_ROUND_STATE_MACHINE.md`. Every vector
preserves the A1 baseline (`8.420833333 kWh`). The algorithm is **PoCol** and the mechanism under test is the idle policy
within PoCol.

Terminology: `RunContext.last_finalised_event_time` is the authoritative simulation frontier advanced solely by
`ProcessEventTime` (AI2); `AdmitDriverRequest` records a frontier-derived `driver_admission_time` and derives a stable
`logical_request_id` before minting a `DriverRequestID` (AI2/AI3); `SetDriverRequestStatus` is the single guarded status
mutator and `CompleteDriverRequestOnDispatch` is the dispatcher-owned request-completion owner over the immutable
`driver_request_by_seat_event_ref` reverse binding (AI4); every `driver_request` carries a `DriverRoundScope` (AI5); the
terminal-round publication result is captured in `RunContext.terminal_publication_result` (AI6); `MinerRegister` returns a
distinct barrier/participant-setup disposition (AI7); the synchronous rotation bootstrap carries a `TERMINAL_ROTATION`
origin (AI8).

---

## TV313 — A genesis MinerRegisterEvent is seated in-dispatch at the non-finalised t0, not rejected_finalised_time (AI1)

- **Procedures:** `RoundInitialise`, `RoundInitialiseEvent`, `SeatMinerRegister`, `ScheduleEvent`, `ProcessEventTime`.
- **Setup:** run start with a non-empty `genesis_miner_registry`. `RoundInitialise` (called inside the dispatched
  `RoundInitialiseEvent` at the round-setup time `t0`) admits one `MINER_JOIN` `driver_request` per genesis miner with
  `round_scope = EXACT_ROUND(RoundID)` and `requested_event_time = t0`, and sets the initial-registration barrier. Immediately
  after publishing the RoundContext, `RoundInitialiseEvent` seats each genesis `MinerRegisterEvent` via
  `SeatMinerRegister(..., admission_mode = IN_DISPATCH_GENESIS)`.
- **Expected:** each seat uses `ordinary_dispatch_origin(EQ)` with `target_event_time = EQ.current_event_time = t0`; since `t0`
  is NOT yet in `finalised_event_times` (it is mid-dispatch), `ScheduleEvent` returns `scheduled(...)` — NEVER
  `rejected_finalised_time`. The genesis `MinerRegisterEvent`s dispatch at `t0`; the last genesis `MinerRegister` satisfies the
  barrier and (in ASSIGNMENT) seats participant setup. No genesis request is left PENDING for the outer-loop
  `SeatPendingDriverRequests` (which runs only after `t0` is finalised). Executable invariant holds: every genesis registration
  ends with a live QUEUED `MinerRegisterEvent` at the non-finalised `t0` or a terminal disposition; none remains PENDING after
  `t0` is finalised.

## TV314 — AdmitDriverRequest rejects a requested time behind the simulation frontier (AI2)

- **Procedures:** `AdmitDriverRequest`, `ProcessEventTime`.
- **Setup:** `ProcessEventTime` has finalised event_time `t = 40`, so `RunContext.last_finalised_event_time = 40`. The sim
  driver admits a `MINER_JOIN` with `requested_event_time = 30` (behind the frontier), `round_scope = NEXT_AVAILABLE_ROUND`.
- **Expected:** `AdmitDriverRequest` computes `driver_admission_time = 40` (the frontier, NOT a copy of `requested_event_time`)
  and returns `driver_request_time_before_admission_rejected(30, 40)`; NO `DriverRequestID` is minted, no logical id is
  registered, and the pending index is unchanged.

## TV315 — A DRIVER seat with a context / kind / target mismatch, or a target behind the frontier, is rejected (AI2)

- **Procedures:** `ScheduleEvent`, `SeatMinerRegister`, `SeatReserveActivate`.
- **Setup:** four sub-cases, each building a `DriverSchedulingContext` and calling `ScheduleEvent`: (a) the carried
  `EventQueueContext`/`RunContext` are not the ones `ScheduleEvent` was called with; (b) the driver kind may not seat the
  `event_type` under `driver_kind_may_seat` (e.g. `MINER_JOIN` targeting `ReserveActivateEvent`); (c) `target_event_time` ≠
  `dctx.target_event_time`; (d) `target_event_time < RunContext.last_finalised_event_time`.
- **Expected:** (a) `rejected_driver_context_mismatch`; (b) `rejected_driver_kind_event_type_mismatch`; (c)
  `rejected_driver_target_context_mismatch`; (d) `rejected_driver_target_before_simulation_frontier`. Each rejection occurs
  BEFORE any state mutation (no seq minted, no EQ insertion); the seat owner propagates the structured failure; no
  `EQ.current_*` is read on the DRIVER path.

## TV316 — A replayed admission of the same logical request returns the SAME DriverRequestID (AI3)

- **Procedures:** `AdmitDriverRequest`.
- **Setup:** admit a `MINER_JOIN` for join request `J` (deriving `logical_request_id = JOIN_REQUEST(join_request_id(J))`),
  yielding `DriverRequestID d1`; then admit the SAME `J` again (a replay).
- **Expected:** the first admission advances `driver_request_seq`, mints `d1`, and registers
  `driver_request_by_logical_id[logical_id] = d1`; the second returns `driver_request_already_admitted(d1)` — the SAME
  `DriverRequestID` — and advances NO new sequence, creates no second record, no second EventRef, and no second protocol
  effect.

## TV317 — SetDriverRequestStatus refuses an illegal transition (AI4)

- **Procedures:** `SetDriverRequestStatus`.
- **Setup:** a `driver_request` in status `CONSUMED`. Call `SetDriverRequestStatus(expected_status = SEATED, new_status =
  CONSUMED, ...)` (a stale expectation) and, separately, attempt `PENDING → CONSUMED` (an edge not in the table).
- **Expected:** the stale-expectation call returns `driver_request_status_mismatch(drid, CONSUMED, SEATED)` (the CAS guard); the
  `PENDING → CONSUMED` call returns `driver_request_illegal_transition(drid, PENDING, CONSUMED)`. The status is NEVER driven
  back to `SEATED` from a terminal `CONSUMED`/`CANCELLED` (no SEATED-while-CONSUMED/CANCELLED). No other procedure writes
  `driver_request.status` directly.

## TV318 — A dispatched driver seat becomes CONSUMED with the handler result via the reverse binding (AI4)

- **Procedures:** `SeatReserveActivate`, `ScheduleEvent`, `ProcessEventTime`, `CompleteDriverRequestOnDispatch`,
  `SetDriverRequestStatus`.
- **Setup:** an `ORDINARY_RESERVE_DEFICIT` `driver_request` is seated by `SeatReserveActivate`, which publishes
  `driver_request_by_seat_event_ref[event_ref] = DriverRequestID` and transitions PENDING → SEATED atomically with the seat.
  `ProcessEventTime` later dispatches that `ReserveActivateEvent`.
- **Expected:** after the handler returns, `ProcessEventTime` calls `CompleteDriverRequestOnDispatch(seat_event_ref = er,
  disposition = driver_request_consumed(handler_result))`, which resolves the EXACT request via the reverse binding and
  transitions SEATED → CONSUMED through `SetDriverRequestStatus`, recording the actual `handler_result` as `consumed_result`. A
  non-driver event (a bootstrap `RoundInitialiseEvent`, an ordinary in-round event) has no reverse binding and is a declared
  no-op (`driver_request_not_a_seat`).

## TV319 — A cancelled driver seat reconciles the exact request to CANCELLED (AI4)

- **Procedures:** `CancelQueuedEvent`, `SetDriverRequestStatus`.
- **Setup:** a SEATED `MINER_JOIN` whose QUEUED `MinerRegisterEvent` is cancelled during round closure
  (`CloseRoundAssignments` → `CancelQueuedEvent`).
- **Expected:** `CancelQueuedEvent` removes the EventRef from EQ (`QUEUED → CANCELLED`) and, via the reverse binding, calls
  `SetDriverRequestStatus(expected_status = SEATED, new_status = CANCELLED, disposition =
  driver_request_seat_cancelled(...))`. The request never dangles `SEATED`; a subsequent dispatch-completion attempt (were the
  event somehow re-processed) would `status_mismatch` and leave it terminal — never resurrected to CONSUMED.

## TV320 — A stale EXACT_ROUND scope is rejected by the intake, not seated under a terminal round (AI5)

- **Procedures:** `SeatPendingDriverRequests`, `SetDriverRequestStatus`.
- **Setup:** a PENDING `driver_request` with `round_scope = EXACT_ROUND(R1)` while the current round is `R2` (or `R1` is now
  terminal), so `SCOPE_ADMITS(EXACT_ROUND(R1), kind, rc)` = `SCOPE_STALE`.
- **Expected:** `SeatPendingDriverRequests` does NOT route the request to a seat owner; it transitions PENDING → REJECTED via
  `SetDriverRequestStatus(disposition = driver_request_scope_stale(EXACT_ROUND(R1), rc.RoundID))`, removes it from the pending
  index, and records the rejection. It is never silently seated under a terminal round and then executed against a different
  round. A `NEXT_AVAILABLE_ROUND` request against a non-admitting round yields `SCOPE_WAIT` and stays PENDING.

## TV321 — A next-round seat failure sets NEXT_ROUND_BOOTSTRAP_FAILED and terminates the run PARTIAL (AI6)

- **Procedures:** `CloseRoundAssignments`, `PublishTerminalRoundAndSeatNext`, `RunEventLoopToHorizon`, `FinalizeSimulationRun`.
- **Setup:** a round closes (ordinary acceptance or abort); `PublishTerminalRoundAndSeatNext` returns
  `terminal_round_published_seat_failed(brid, reason)` (the next bootstrap could not be seated).
- **Expected:** `CloseRoundAssignments` stores the result in `RunContext.terminal_publication_result`, sets
  `RunContext.next_round_bootstrap_status = NEXT_ROUND_BOOTSTRAP_FAILED`, and returns `closure_record(publication_result =
  ...)`. On the next iteration `RunEventLoopToHorizon` observes `NEXT_ROUND_BOOTSTRAP_FAILED`, finalises the run against the
  ALREADY-terminal predecessor round via `FinalizeSimulationRun`, and returns `run_completed_partial(next_round_bootstrap_failed)`
  — a declared PARTIAL-RUN disposition — rather than spinning with no next round. The publication result is NEVER discarded.

## TV322 — A participant-setup abort during the barrier-completing registration returns _participant_setup_aborted (AI7)

- **Procedures:** `MinerRegister`, `MinerRegisterEvent`, `SeatParticipantSetupOrAbort`, `CompleteDriverRequestOnDispatch`.
- **Setup:** the LAST declared genesis miner registers during ASSIGNMENT (TemplateID committed), completing the barrier;
  `SeatParticipantSetupOrAbort` returns `participant_setup_aborted(reason)` (the participant-setup seat failed).
- **Expected:** `MinerRegister` returns `miner_registered_participant_setup_aborted(MinerID,
  participant_setup_seat_failed_round_abort(reason))` — NOT a plain `miner_registered` success. `MinerRegisterEvent` propagates
  the disposition; when the `MinerRegisterEvent` dispatch completes, the driver_request records this SAME disposition as its
  `consumed_result` (via `CompleteDriverRequestOnDispatch`). A barrier-member registration that does NOT complete the barrier
  returns `miner_registered_barrier_pending`; a successful barrier completion returns `miner_registered_participant_setup_seated`.

## TV323 — The rotation bootstrap carries TERMINAL_ROTATION; the run-start bootstrap carries DRIVER (AI8)

- **Procedures:** `SeatNextRoundBootstrap`, `PublishTerminalRoundAndSeatNext`, `ScheduleEvent`.
- **Setup:** (a) run start — `SeatNextRoundBootstrap` called by `RunEventLoopToHorizon` with
  `current_bootstrap_request.predecessor_round_id = RUN_START`; (b) a rotation — `SeatNextRoundBootstrap` called synchronously
  by `PublishTerminalRoundAndSeatNext` with a rotation `BootstrapRequest`.
- **Expected:** (a) the seat carries `DRIVER(DriverSchedulingContext(driver_source_kind = RUN_BOOTSTRAP, ...))` — a genuine
  outside-dispatch sim-driver seat; (b) the seat carries `TERMINAL_ROTATION(TerminalRotationSchedulingContext(...))` — the
  truthful classification of a seat made synchronously from inside a terminal-publication handler. In both cases `ScheduleEvent`
  derives `delta_cycle = 0`, reads NO `EQ.current_*`, and requires the target strictly after the predecessor terminal time
  (rotation) and not behind the frontier; `driver_kind_may_seat(ROUND_ROTATION_BOOTSTRAP, RoundInitialiseEvent)` holds. No
  next-round event is seated before the predecessor round is terminal (the `PublishTerminalRoundAndSeatNext` ASSERT).

## TV324 — The full stage_01 tree manifest is self-excluded and verifies twice (AI9)

- **Procedures / artifacts:** `STAGE_01AI_CHECKSUM_MANIFEST.sha256`, `STAGE_01AI_CROSS_DOCUMENT_AUDIT.md`.
- **Setup:** compute the Stage-1AI checksum manifest over the ENTIRE `stage_01` tree (every Stage-1A through Stage-1AI file),
  `LC_ALL=C`-sorted, EXCLUDING the manifest itself; verify it twice (`sha256sum -c`).
- **Expected:** the manifest covers every stage_01 file except itself (a full-tree coverage profile, superseding the
  delta-only convention of earlier stages), lists no path outside `stage_01`, and both verification passes report OK for every
  line. A silently modified historical Stage-1A–1AH artifact would be detected by this full-tree manifest (unlike a delta-only
  manifest). The coverage profile is documented in the AI cross-document audit.

---

**Coverage.** TV313–TV324 exercise every Stage-1AI correction: AI1 (TV313), AI2 (TV314, TV315), AI3 (TV316), AI4 (TV317,
TV318, TV319), AI5 (TV320), AI6 (TV321), AI7 (TV322), AI8 (TV323), AI9 (TV324); AI10 (the supersession of inaccurate
Stage-1AH audit claims) is recorded in `STAGE_01AI_SUPERSESSION_REGISTER.md`. Each vector names only procedures and result
tokens defined in the Stage-1AI normative tree, changes no executable source or configuration, preserves the A1 baseline
(`8.420833333 kWh`), and keeps the PoCol naming and the "idle policy within PoCol" mechanism.
