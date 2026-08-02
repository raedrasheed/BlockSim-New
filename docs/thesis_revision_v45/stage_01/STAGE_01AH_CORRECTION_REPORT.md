# Stage 1AH — Correction Report (driver-scheduling, round-rotation & acceptance-lifecycle lock)

Stage 1AH is a documentation-only revision branched from exactly parent
`3658fd8ed52757e72ce7736080b152fcf839ea94` (the Stage-1AG commit) that makes the AG driver machinery *causally* sound
across round rotation, sim-driver intake, and acceptance. The algorithm remains **PoCol**; the mechanism is the idle policy
within PoCol; the A1 baseline (`8.420833333 kWh`) is unchanged. No executable source, configuration, DOCX, or PDF was
modified; no experiment was run; Stage-1A through Stage-1AG artifacts are frozen; Stage 2 is not begun.

## Corrections

- **AH1 — make every scheduling source explicit.** A `SchedulingOrigin` union is defined —
  `ORDINARY_DISPATCH(OrdinaryDispatchContext) | DRIVER(DriverSchedulingContext) | POST_EPILOGUE(PostEpilogueSchedulingContext)`
  (§0.7e). `ScheduleEvent` takes `scheduling_origin` EXPLICITLY and derives `delta_cycle` from the origin's own source
  frame — NEVER from ambient `EQ.current_*`. A `DRIVER` seat derives `delta_cycle = 0` and requires
  `target_event_time >= source_event_time`; a `POST_EPILOGUE` seat requires a strictly-later target; an `ORDINARY_DISPATCH`
  seat applies the §0.7-H2 forward rule against the dispatcher-owned dispatch frame. `rejected_invalid_scheduling_origin`
  and `rejected_driver_target_before_source` are added. Every `ScheduleEvent` call site names its origin (the seat owners,
  `StartWake`, the acceptance/certificate/hash-work/resume/setup-retry seats, and the recovery epilogue seats).

- **AH2 — per-round bootstrap target + one terminal-round publication owner.** `RunContext.round_bootstrap_time =
  config.run_start_time` is REMOVED. Each round's `RoundInitialiseEvent` is seated at its own immutable
  `BootstrapRequest.target_time` (first round → `run_start_time`; a rotation →
  `next_representable_simulation_time(predecessor terminal time)`, strictly later, `≤ T`, never reusing `run_start_time`).
  Ordinary acceptance, ordinary abort, and horizon closure are unified through ONE named owner
  `PublishTerminalRoundAndSeatNext` (called by `CloseRoundAssignments`) in the required order: record `round_terminal_time`
  → publish `prior_round_terminal_state` → create the immutable next `BootstrapRequest` → seat the next bootstrap → inspect
  the result. `RoundAbort` now transitions to `ROUND_ABORTED` BEFORE `CloseRoundAssignments` (matching `ValidBlockAccept`),
  so a bootstrap is never seated while the predecessor round is nonterminal. A horizon / run-hook close publishes the
  terminal state but seats no next round.

- **AH3 — stable request identity before minting.** The `BootstrapRequestID`
  (`RUN_START` | `(prior RoundID, prior terminal time, NEXT_ROUND)`) and the immutable `DriverRequestID` are the replay
  keys, checked BEFORE `round_setup_seq` / `reserve_activation_seq` is read; a replay of the same request returns the same
  seated `EventRef` and seats no second event (`SeatNextRoundBootstrap`, `SeatReserveActivate`, `SeatMinerRegister`).

- **AH4 — explicit driver-request records + event-loop ordering.** The bare `pending_join_requests` /
  `pending_ordinary_reserve_deficits` sets are replaced by a `driver_request` registry
  `{ DriverRequestID, kind, requested_event_time, payload, status, seated_event_ref, disposition }` with status in
  `{PENDING, SEATED, CONSUMED, REJECTED, CANCELLED}`, produced by the named `AdmitDriverRequest`. `SeatPendingDriverRequests`
  inspects each seat result and terminalises the exact record. `RunEventLoopToHorizon` admits + seats all pending driver
  requests BEFORE selecting the next earliest queue event_time (Option A), so intake can never insert an event earlier than
  an already-selected `t`.

- **AH5 — first-round miner admission.** Option A: a `genesis_miner_registry` in `RunContext` is imported by the first
  `RoundInitialise` (as `MINER_JOIN` driver requests) and the round holds an `initial_registration_barrier`;
  `PrepareParticipantsForNewRound` never runs before the declared initial miner set is complete (`TemplateCommitEvent`
  defers participant setup until the barrier is satisfied; `MinerRegister` seats it on completion).

- **AH6 — handle every bootstrap-chain seat result.** `RunEventLoopToHorizon` inspects the initial bootstrap seat;
  `RoundInitialiseEvent` inspects `SeatTemplateCommit`; `TemplateCommitEvent` inspects `SeatPrepareParticipants`;
  `ExhaustionAdjudicate` inspects `SeatFullRangeExhaust`. Each failure takes a declared disposition
  (`bootstrap_seat_failed_run_abort` / `template_commit_seat_failed_round_abort` /
  `participant_setup_seat_failed_round_abort` / `full_range_exhaust_seat_failed_round_abort` / `driver_request_rejected`).
  No caller returns success after a required successor failed to seat; a failed first bootstrap takes the declared
  no-round run path (`FinalizeSimulationRunNoRound`) and never dereferences a null `RoundContext`.

- **AH7 — acceptance generation lifecycle + candidate-failure owner.** `acceptance_batch_registry` is generation-keyed
  `(acceptance_timestamp, acceptance_point, batch_generation)` in the core data model; every contract states one
  `AcceptanceBatchFinalize` per that triple. `ACCEPTANCE_BATCH_UNFINALISABLE` is added. A finalize-seat failure fails ONLY
  its own candidate through the single named owner `HandlePropagationFailure` (FAILED + removed from
  `active_propagation_set` + events cancelled + its paused miners resumed) — a `FAILED` candidate is never left in the set.
  `BlockAcceptancePoint` receives its own `dispatch_envelope` (recv env = yes, type-correct). Closure paths cancel
  `acceptance_batch_finalize_seat[key].EventRef` (never the whole `{ generation, EventRef }` record).

- **AH8 — one authoritative queue tie key.** The only queue tie key is
  `descriptor(event_type).stable_tie_key(immutable_payload)` (then `seq`). Every SURVIVING positive
  `(CandidateID, MinerID, AssignmentID[, seq])` ordering rule is removed — §0.7-H2, the deterministic-vs-sampling summary,
  §21 intra-type tie-break, and the companion documents. The acceptance value selection (`candidate_hash` then `MinerID`)
  is kept as distinct winner arbitration, not a queue key.

- **AH9 — identity vs payload distinctions + RunContext field declarations.** `EventRef`, `dispatch_envelope`,
  `immutable_payload`, `queued_event_record`, and `stable_tie_key` are kept distinct (§0.2); the domain identity fields
  (`RoundID`/`TemplateID`/`CandidateID`/`MinerID`/`AssignmentID`/`assignment_version`) are payload, NOT `dispatch_envelope`
  fields. Every driver/bootstrap field is declared directly inside `STRUCTURE RunContext`. The stale note that
  `ProcessEventTime` obtains `RunContext` through `RoundContext.RunContext` is removed (it receives `RunContext` directly).

- **AH10 — supersession.** `STAGE_01AH_SUPERSESSION_REGISTER.md` records the inaccurate Stage-1AG audit claims AH corrects.

## File delta

Modified (5 normative `STAGE_01_*`): `STAGE_01_PROTOCOL_PSEUDOCODE.md`, `STAGE_01_ROUND_STATE_MACHINE.md`,
`STAGE_01_INVARIANT_CATALOGUE.md`, `STAGE_01_TERMINOLOGY.md`, `STAGE_01_TRACEABILITY_MATRIX.csv`.

New (14 `STAGE_01AH_*` deliverables): `STAGE_01AH_CORRECTION_REPORT.md`, `STAGE_01AH_DRIVER_SCHEDULING_CONTEXT_AUDIT.md`,
`STAGE_01AH_BOOTSTRAP_TIME_IDEMPOTENCE_AUDIT.md`, `STAGE_01AH_DRIVER_REQUEST_LIFECYCLE_AUDIT.md`,
`STAGE_01AH_BOOTSTRAP_CHAIN_RESULT_AUDIT.md`, `STAGE_01AH_ACCEPTANCE_GENERATION_LIFECYCLE_AUDIT.md`,
`STAGE_01AH_EVENT_ORDERING_ROOT_AUDIT.md`, `STAGE_01AH_RUNCONTEXT_TERMINAL_PUBLICATION_AUDIT.md`,
`STAGE_01AH_PROCEDURE_SIGNATURE_CALL_AUDIT.md`, `STAGE_01AH_PROCEDURE_CALL_GRAPH.md`,
`STAGE_01AH_SEMANTIC_TEST_VECTORS.md`, `STAGE_01AH_SUPERSESSION_REGISTER.md`, `STAGE_01AH_CROSS_DOCUMENT_AUDIT.md`,
`STAGE_01AH_CHECKSUM_MANIFEST.sha256`.

## Verification

- Call graph resolves with 0 dangling references and 108 defined callables (`STAGE_01AH_PROCEDURE_CALL_GRAPH.md`); Stage-1AG
  was 104 — Stage 1AH adds `AdmitDriverRequest`, `SeatParticipantSetupOrAbort`, `PublishTerminalRoundAndSeatNext`, and
  `FinalizeSimulationRunNoRound`.
- Traceability rows R259–R269 append AH1–AH10 + the TV299–TV312 block (9-field CSV; no embedded commas).
- Fourteen blocking semantic vectors TV299–TV312 (`STAGE_01AH_SEMANTIC_TEST_VECTORS.md`).
- Protected drafts byte-identical; no forbidden model/vendor identifier in any deliverable; A1 baseline present and unchanged
  (`STAGE_01AH_CROSS_DOCUMENT_AUDIT.md`, `STAGE_01AH_CHECKSUM_MANIFEST.sha256`).
