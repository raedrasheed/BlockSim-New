# Stage 1AG — Correction Report (dispatch-argument, run-bootstrap & wake-payload lock)

Stage 1AG is a documentation-only revision branched from exactly parent
`bed71f56aba2ffe1f526ab04aaf3aafa25e2e480` (the Stage-1AF commit) that makes the AF driver-event machinery genuinely
executable end-to-end. The algorithm remains **PoCol**; the mechanism is the idle policy within PoCol; the A1 baseline
(`8.420833333 kWh`) is unchanged. No executable source, configuration, DOCX, or PDF was modified; no experiment was run;
Stage-1A through Stage-1AF artifacts are frozen; Stage 2 is not begun.

## Corrections

- **AG1 — explicit wrapper payload bindings + verification.** Every AF4 wrapper payload field has an EXPLICIT
  `payload_to_param_map` entry (no `(none)`/prose, no unwritten same-name fallback). The descriptor gains `handler_inputs`
  (ground-truth INPUTS); `BuildHandlerInvocation` verifies `keys(args) = handler_inputs` and returns
  `handler_invocation_built(procedure, args)` or `handler_invocation_binding_failed(event_type, missing_args, extra_args)`
  (never a raw assert); `ProcessEventTime` records `dispatch_binding_failed` and does not call the handler.

- **AG2 — wake seat carries the exact assignment_version.** `StartWake` seats `WakeCompleteEvent` with
  `{MinerID, AssignmentID, assignment_version}`; the `wake_seated` record retains `assignment_version`; `WakeCompleteEvent`
  resolves `version(AssignmentID, assignment_version)` and verifies it equals the miner's live-head version before any
  transition. A renewed/superseded version is never activated by an older wake.

- **AG3 / AG5 — executable first-round bootstrap + dynamic round context.** `RunEventLoopToHorizon` and `ProcessEventTime`
  take `RunContext`; each dispatch resolves `RoundContext <- RunContext.current_round_context`. `RoundInitialiseEvent` is
  dispatchable while `current_round_context = null`. No post-rotation event receives a stale RoundContext; a required-but-null
  RoundContext is a structured `dispatch_context_unavailable`.

- **AG4 — named driver-event seating owners.** `SeatNextRoundBootstrap`, `SeatTemplateCommit`, `SeatPrepareParticipants`,
  `SeatMinerRegister`, `SeatReserveActivate`, `SeatFullRangeExhaust`, and the `SeatPendingDriverRequests` intake enqueue each
  wrapper through `ScheduleEvent` with structured results and bounded idempotence identities (`RunContext.driver_event_seat`).
  Every driver wrapper has a reachable named seating path; replay cannot create two rounds or commit one template twice.

- **AG6 — publish the prior terminal round.** `CloseRoundAssignments` (the single terminal-round closure owner) publishes
  `prior_round_terminal_state <- current_round_context` (RoundID, round_terminal_time, residency_ledger, terminal
  disposition) before the next bootstrap; `RoundInitialise` passes it to `SettleResidencyBoundary(REBASE_TO_NEXT_ROUND)`.

- **AG7 — acceptance-batch context, result & generation.** The type-incorrect `ORDINARY_DISPATCH(EQ.current_event_ref)` is
  removed; `SeatAcceptanceBatchFinalize` takes no `source_context`. `BlockAcceptancePoint` seats first, captures the result
  (seated/already → registered; seat_failed → declared candidate failure with no stranded batch), and registers into the
  finalize's `batch_generation`; a later-delta same-timestamp arrival after a consumed finalize opens a new generation.

- **AG8 — root event-ordering rule.** `stable_tie_key = descriptor(event_type).stable_tie_key(immutable_payload)` in §0.2,
  ScheduleEvent, I21, terminology, and traceability; the universal `(CandidateID, MinerID, AssignmentID)` claim is withdrawn;
  the dispatch_envelope identity, the immutable payload, and the descriptor-derived ordering key are kept distinct.

- **AG9 — supersession.** `STAGE_01AG_SUPERSESSION_REGISTER.md` records the inaccurate Stage-1AF audit claims AG corrects.

## File delta

Modified (5 normative `STAGE_01_*`): `STAGE_01_PROTOCOL_PSEUDOCODE.md`, `STAGE_01_ROUND_STATE_MACHINE.md`,
`STAGE_01_INVARIANT_CATALOGUE.md`, `STAGE_01_TERMINOLOGY.md`, `STAGE_01_TRACEABILITY_MATRIX.csv`.

New (14 `STAGE_01AG_*` deliverables): `STAGE_01AG_CORRECTION_REPORT.md`, `STAGE_01AG_WRAPPER_ARGUMENT_BINDING_AUDIT.md`,
`STAGE_01AG_WAKE_VERSION_PAYLOAD_AUDIT.md`, `STAGE_01AG_RUN_BOOTSTRAP_AUDIT.md`, `STAGE_01AG_ROUND_CONTEXT_ROTATION_AUDIT.md`,
`STAGE_01AG_DRIVER_EVENT_SEATING_AUDIT.md`, `STAGE_01AG_ACCEPTANCE_BATCH_CONTEXT_AUDIT.md`,
`STAGE_01AG_EVENT_ORDERING_CONSISTENCY_AUDIT.md`, `STAGE_01AG_PROCEDURE_SIGNATURE_CALL_AUDIT.md`,
`STAGE_01AG_PROCEDURE_CALL_GRAPH.md`, `STAGE_01AG_SEMANTIC_TEST_VECTORS.md`, `STAGE_01AG_SUPERSESSION_REGISTER.md`,
`STAGE_01AG_CROSS_DOCUMENT_AUDIT.md`, `STAGE_01AG_CHECKSUM_MANIFEST.sha256`.

## Verification

- Call graph resolves with 0 dangling references and 104 defined callables (`STAGE_01AG_PROCEDURE_CALL_GRAPH.md`).
- Traceability rows R249–R258 append AG1–AG9 + the TV288–TV298 block (9-field CSV; no embedded commas).
- Eleven blocking semantic vectors TV288–TV298 (`STAGE_01AG_SEMANTIC_TEST_VECTORS.md`).
- Protected drafts byte-identical; no forbidden model/vendor identifier in any deliverable; A1 baseline present and unchanged
  (`STAGE_01AG_CROSS_DOCUMENT_AUDIT.md`, `STAGE_01AG_CHECKSUM_MANIFEST.sha256`).
