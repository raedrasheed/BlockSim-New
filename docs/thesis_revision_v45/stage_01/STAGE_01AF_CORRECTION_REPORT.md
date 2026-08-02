# Stage 1AF — Correction Report (executable dispatch binding & queue-pop lock)

Stage 1AF is a documentation-only revision branched from exactly parent
`184648755206e231c8db5545324b6d09f7dd3428` (the Stage-1AE commit) that makes the Stage-1AE event-dispatch schema
EXECUTABLE and locks the queue-pop / dispatch-binding contract. The algorithm remains **PoCol**; the mechanism is the idle
policy within PoCol; the A1 baseline (`8.420833333 kWh`) is unchanged. No executable source, configuration, DOCX, or PDF was
modified; no experiment was run; Stage-1A through Stage-1AE artifacts are frozen; Stage 2 is not begun.

## Corrections

- **AF1 — executable `event_descriptor` set.** The descriptive §0.7g-schema is replaced by one `event_descriptor` per queued
  type (exact closed `allowed_payload_keys` with types, payload-key→handler-parameter mapping, runtime-injected parameters,
  target microphase, descriptor-derived `stable_tie_key` function, cancellation identity), keeping the five categories apart
  (handler inputs / runtime context / stored payload / handler-derived values / stable ordering keys). Corrected rows:
  `RoundInitialiseEvent` (RoundID minted; payload `round_setup_seq`), `TemplateCommitEvent` (TemplateID minted from
  `candidate_template`), `MinerRegisterEvent` (MinerID derived from `join_request`), `WakeCompleteEvent` (payload gains
  `assignment_version`; dispatcher resolves `target_assignment`), `ReserveActivateEvent` (receives a `scheduling_context`
  wrapper). Synchronous `RoundAbort` is REMOVED from the queued schema and the driver-seating table.

- **AF2 — executable dispatch binding.** `BuildHandlerInvocation(event_descriptor, record, RoundContext, RunContext, ctx)`
  returns the exact named handler arguments (WakeComplete `target_assignment ← version(...)`; ReserveActivate wrapper builds
  `scheduling_context = ORDINARY_DISPATCH(...)`; BlockAcceptancePoint no env/ref; SetupRetry env+ref; RoundInitialise
  RunContext). No handler receives an undeclared argument, unresolved alias, or a derived output in place of an input.

- **AF3 — full ScheduleEvent schema enforcement.** Before any mutation: `rejected_event_type_unknown`,
  `rejected_microphase_mismatch`, `rejected_payload_schema_mismatch` (missing / EXTRA / wrong-typed key — the exact closed
  set), `rejected_stable_tie_key_unavailable`. EQ is ordered by the descriptor-derived `stable_tie_key`, not the generic
  `(CandidateID, MinerID, AssignmentID)` tuple.

- **AF4 — driver-event wrappers.** `RoundInitialiseEvent`, `TemplateCommitEvent`, `MinerRegisterEvent`,
  `PrepareParticipantsEvent`, `ReserveActivateEvent`, `FullRangeExhaustEvent`: each stores exactly its payload, receives its
  declared runtime context, calls the domain procedure with exact args, inspects and returns its disposition.

- **AF5 — atomic queue-pop before dispatch.** `ProcessEventTime` atomically POPs the front EventRef, asserts `QUEUED`, sets
  `DISPATCHING`, and sets the complete `EQ.current_*`; after the handler it atomically sets `CONSUMED` and clears every
  `EQ.current_*`. `EQ.event_queue` is the ONE representation (pending QUEUED only); the "by projection" convention is removed;
  the AE3 re-query is preserved (a cancelled event, removed from EQ, is never POPped).

- **AF6 — RunContext ownership.** `RunInitialise` returns every per-run field (EventQueueContext, `queued_event_registry`,
  `setup_retry_records`, `setup_retry_by_seat_event_ref`, `applied_transition_registry`, `transition_rejection_log`,
  security-census maps/counters, `waking_origin_assignment_ref`, `maximum_setup_retries`, `config`,
  `prior_round_terminal_state`, `current_round_context`). No per-run registry is an implicit global.

- **AF7 — hashing result contract.** `StartHashing` RETURNs `hashing_started(event_ref)` / `hashing_not_started(reason)`
  explicitly (no successful fall-through). `HashWorkEvent`'s continuation RETURNs `continued(hash_work_seated(EventRef) |
  hash_work_not_seated(reason))`, matching its declared RETURNS shape; the `WakeCompleteEvent` caller RETURNS is reconciled.

- **AF8 — acceptance-batch seating owner.** `SeatAcceptanceBatchFinalize(acceptance_timestamp, acceptance_point,
  source_context)` replaces the prose "ENSURE … is scheduled": seats through `ScheduleEvent`, one live seat per
  `(timestamp, point)` via the per-round `acceptance_batch_finalize_seat` map, stores the cancellable EventRef, replay-safe;
  `RoundAbort` cancels live seats.

- **AF9 — non-asserting reverse-binding corruption.** `HandleDispatchIntegrityFailure` records
  `dispatch_integrity_owner_binding_corrupt(er)` (mutating no retry, aborting no round) instead of raw-asserting when the
  reverse binding is corrupt (missing record, `seat_event_ref` mismatch, or duplicate ownership).

- **AF10 — supersession.** `STAGE_01AF_SUPERSESSION_REGISTER.md` records the inaccurate Stage-1AE audit claims AF corrects
  (schema conflation of derived/tie-key identities with payload; the bare-envelope-vs-wrapper dispatch claim; the
  projection-not-POP coherence convention; the missing `StartHashing` RETURN and `HashWorkEvent` shape mismatch; and the
  cross-document gates 3, 5, 6, 10, 12, 13 wrongly marked PASS).

## File delta

Modified (5 normative `STAGE_01_*`): `STAGE_01_PROTOCOL_PSEUDOCODE.md`, `STAGE_01_ROUND_STATE_MACHINE.md`,
`STAGE_01_INVARIANT_CATALOGUE.md`, `STAGE_01_TERMINOLOGY.md`, `STAGE_01_TRACEABILITY_MATRIX.csv`.

New (16 `STAGE_01AF_*` deliverables): `STAGE_01AF_CORRECTION_REPORT.md`, `STAGE_01AF_EVENT_DESCRIPTOR_AUDIT.md`,
`STAGE_01AF_DRIVER_EVENT_BINDING_AUDIT.md`, `STAGE_01AF_DISPATCH_ADAPTER_AUDIT.md`,
`STAGE_01AF_SCHEDULER_SCHEMA_ENFORCEMENT_AUDIT.md`, `STAGE_01AF_QUEUE_POP_AND_CONTEXT_AUDIT.md`,
`STAGE_01AF_RUNCONTEXT_OWNERSHIP_AUDIT.md`, `STAGE_01AF_HASH_RESULT_CONTRACT_AUDIT.md`,
`STAGE_01AF_ACCEPTANCE_BATCH_SEATING_AUDIT.md`, `STAGE_01AF_INTEGRITY_REVERSE_BINDING_AUDIT.md`,
`STAGE_01AF_PROCEDURE_SIGNATURE_CALL_AUDIT.md`, `STAGE_01AF_PROCEDURE_CALL_GRAPH.md`,
`STAGE_01AF_SEMANTIC_TEST_VECTORS.md`, `STAGE_01AF_SUPERSESSION_REGISTER.md`, `STAGE_01AF_CROSS_DOCUMENT_AUDIT.md`,
`STAGE_01AF_CHECKSUM_MANIFEST.sha256`.

## Verification

- Call graph resolves with 0 dangling references and 97 defined callables (`STAGE_01AF_PROCEDURE_CALL_GRAPH.md`).
- Traceability rows R238–R248 append AF1–AF10 + the TV273–TV287 block (9-field CSV; no embedded commas).
- Fifteen blocking semantic vectors TV273–TV287 (`STAGE_01AF_SEMANTIC_TEST_VECTORS.md`).
- Protected drafts byte-identical; no forbidden model/vendor identifier in any deliverable; A1 baseline present and unchanged
  (`STAGE_01AF_CROSS_DOCUMENT_AUDIT.md`, `STAGE_01AF_CHECKSUM_MANIFEST.sha256`).
