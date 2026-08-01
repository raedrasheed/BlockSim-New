# Stage 1W — Cross-Document Audit (acceptance gates)

This audit verifies that corrections W1–W8 are reflected consistently across every normative document
(`STAGE_01_PROTOCOL_PSEUDOCODE.md`, `STAGE_01_ROUND_STATE_MACHINE.md`, `STAGE_01_INVARIANT_CATALOGUE.md`,
`STAGE_01_TERMINOLOGY.md`, `STAGE_01_TRACEABILITY_MATRIX.csv`) and the Stage-1W deliverables, and that the change
respects the documentation-only, A1-preserving discipline. Each gate records **PASS** with the grounding location and
corroborating deliverable / test vector. Gate numbering follows the Stage-1W acceptance list.

## Acceptance gates

| # | Gate | Result |
|--:|------|--------|
| 1 | No rollback procedure uses a free or placeholder dispatch envelope | **PASS** — `participant_setup_txn` / `refresh_setup_txn` carry an IMMUTABLE `rollback_envelope = dispatch_envelope` (complete `{ envelope_namespace, event_time, delta_cycle, event_seq, hook_id }`); `RollbackParticipantSetup`/`RollbackTemplateRefreshSetup` transition with `transition_envelope = setup_txn.rollback_envelope`; a corpus scan finds no `<the setup dispatch_envelope>` / `<the refresh dispatch_envelope>` placeholder. `STAGE_01W_ROLLBACK_ENVELOPE_AUDIT.md`; TV186 |
| 2 | Every rollback miner transition exists in the authoritative miner state machine | **PASS** — a `WAKING` participant is departed to `OFFLINE` via the legal `T12` edge ONLY (STAGE_01_MINER_STATE_MACHINE.md); no `WAKING -> REGISTERED`/`RESERVE`/`LOW_POWER_LISTEN` (or `WAKING, prior_states[m]`) transition remains. `STAGE_01W_MINER_ROLLBACK_LEGALITY_AUDIT.md`; TV187/TV188 |
| 3 | Setup rollback cannot leave a miner WAKING without a live event | **PASS** — the rollback cancels captured wakes FIRST, then departs any `WAKING` participant to `OFFLINE` (T12), then closes heads; it returns `rollback_failed(residual_partial_setup)` if any participant remains `WAKING` or any wake remains pending. `STAGE_01W_MINER_ROLLBACK_LEGALITY_AUDIT.md`; TV187/TV188 |
| 4 | TemplateRefresh handles StartWake failure before CompleteAssignmentPhase | **PASS** — a non-`wake_seated` result in the refresh loop sets `refresh_setup_error` and BREAKs; `IF refresh_setup_error != null` skips `CompleteAssignmentPhase`, calls `RollbackTemplateRefreshSetup`, and takes the W8 retry/abort path. `STAGE_01W_TEMPLATE_REFRESH_TRANSACTION_AUDIT.md`; TV189 |
| 5 | `refresh_setup_txn` is populated by explicit statements | **PASS** — the transaction is initialised BEFORE the loop and each field is set by explicit in-loop statements (`RECORD refresh_setup_txn.prior_states[m]`, `ADD AssignmentID(...) to refresh_setup_txn.created_assignments`, `ADD wref to refresh_setup_txn.wakes`); no post-loop prose reconstruction remains. `STAGE_01W_TEMPLATE_REFRESH_TRANSACTION_AUDIT.md`; TV189 |
| 6 | `CommitRecoveryAssignmentPlan` handles every structured range result | **PASS** — the REDISTRIBUTION branch branches on `range_assigned`/`range_reassigned` (success), `range_assign_creation_failed`/`range_reassign_creation_failed` (pre-mutation), and `range_assign_wake_failed`/`range_reassign_wake_failed` (self-rolled-back), never an undefined `creation_failed`. `STAGE_01W_STRUCTURED_RANGE_RESULT_AUDIT.md`; TV192/TV193 |
| 7 | No assignment activation is woken twice | **PASS** — the plan-bound constructor performs the SINGLE wake and returns the `WakeEventRef`; the commit captures it and issues no second `StartWake`; no `required_wake_operations` `StartWake` loop remains. `STAGE_01W_STRUCTURED_RANGE_RESULT_AUDIT.md`, `STAGE_01W_PROCEDURE_CALL_GRAPH.md`; TV192 |
| 8 | Plan commit uses plan-bound range constructors without SELECT | **PASS** — `RangeAssignFromPlan`/`RangeReassignFromPlan` take exact spec fields, perform NO `SELECT`, and assert the committed object equals the spec; `CommitRecoveryAssignmentPlan` calls only these by `spec.origin`. `STAGE_01W_PLAN_BOUND_RANGE_AUDIT.md`; TV190/TV191 |
| 9 | `ApplyMinerStateTransition` and `StartWake` use the same declared result names | **PASS** — the hook returns `transition_applied` / `duplicate_suppressed` / `illegal_stale_source` / `illegal_transition` (each carrying `TransitionEventID`); `StartWake` retains the wake only on `transition_applied` and cancels on any other; `transition_record` is withdrawn. `STAGE_01W_TRANSITION_RESULT_CONTRACT_AUDIT.md`; TV194 |
| 10 | Assignment creation failure is handled before any AssignmentID access | **PASS** — `CreatePendingAssignment` returns `assignment_created(assignment)` / `assignment_creation_failed(reason)`; all six callers branch before reading `AssignmentID`, setting lease fields, or recording a transaction entry. `STAGE_01W_ASSIGNMENT_CREATION_RESULT_AUDIT.md`; TV195 |
| 11 | `SetupRetryEvent` is state-compatible, idempotent, and bounded | **PASS** — a retry is seated only when `rolled_to_offline = false`, `setup_retry_generation <= maximum_setup_retries`, and the target is within horizon; `SetupRetryEvent` no-ops a duplicate `SetupRetryID` (`applied_setup_retry_ids`), aborts a state-incompatible retry, and returns `setup_retry_exhausted` beyond the bound. `STAGE_01W_SETUP_RETRY_LIVENESS_AUDIT.md`; TV196/TV197 |
| 12 | TV186 through TV197 pass on paper | **PASS** — `STAGE_01W_SEMANTIC_TEST_VECTORS.md`; each vector names the exact procedures + preconditions with no assumed guard/transition/edge; A1 preserved |
| 13 | No executable source/configuration/DOCX/PDF changes occur | **PASS** — `git diff --name-only e8c9649` = the 5 normative `STAGE_01_*` docs only; all DOCX/PDF drafts and all executable source/config are absent from the diff (byte-identical to the parent) |
| 14 | No Stage-1A through Stage-1V historical artifact is modified | **PASS** — `git diff --name-only e8c9649` shows no `STAGE_01[A-V]_*` file; supersessions recorded in `STAGE_01W_SUPERSESSION_REGISTER.md` |

## Cross-document consistency

| Consistency check | Result |
|-------------------|--------|
| Rollback envelope (pseudocode ↔ round SM ↔ terminology ↔ invariant ↔ traceability) | **PASS** — §2/§19 ↔ round SM §3.10a W1 ↔ terminology W1 ↔ I16 W1/W2 ↔ R160 |
| Legal rollback edges (pseudocode ↔ miner SM ↔ round SM ↔ traceability) | **PASS** — §2/§19 + T12 ↔ round SM §3.10a W2 ↔ I16 W1/W2 ↔ R161 |
| Template-refresh transaction (pseudocode ↔ round SM ↔ terminology ↔ traceability) | **PASS** — §19 ↔ round SM §3.10a W3 ↔ terminology W3 ↔ R162 |
| Structured range results (pseudocode ↔ round SM ↔ terminology ↔ traceability) | **PASS** — §9c/§10a ↔ round SM §3.10a W4 ↔ terminology W4 ↔ R163 |
| Plan-bound range constructors (pseudocode ↔ round SM ↔ terminology ↔ traceability) | **PASS** — §5/§13/§10a ↔ round SM §3.10a W5 ↔ terminology W5 ↔ R164 |
| Transition result union (pseudocode ↔ round SM ↔ terminology ↔ invariant ↔ traceability) | **PASS** — §0.9/§4 ↔ round SM §3.10a W6 ↔ terminology W6 ↔ I16 W6/W7 ↔ R165 |
| Assignment-creation result (pseudocode ↔ round SM ↔ terminology ↔ invariant ↔ traceability) | **PASS** — §3 + callers ↔ round SM §3.10a W7 ↔ terminology W7 ↔ I16 W6/W7 ↔ R166 |
| Bounded state-compatible retry (pseudocode ↔ round SM ↔ terminology ↔ invariant ↔ traceability) | **PASS** — §1.0/§1.1/§2/§19 ↔ round SM §3.10a W8 ↔ terminology W8 ↔ I16 W8 ↔ R167 |
| Test-vector coverage (traceability ↔ semantic vectors) | **PASS** — R168 ↔ `STAGE_01W_SEMANTIC_TEST_VECTORS.md` (TV186–TV197) |
| Call graph has no dangling calls | **PASS** — 83 defined; 0 undefined (`STAGE_01W_PROCEDURE_CALL_GRAPH.md`) |
| Traceability updated | **PASS** — R160–R168 (W1–W8 + TV186–TV197) added |
| A1 discipline + naming rule | **PASS** — baseline `8.420833333 kWh` unchanged; zero functional uses of the prohibited variants; no model/vendor/assistant identifier in any deliverable |

## Git delta

- **Modified (5):** `STAGE_01_PROTOCOL_PSEUDOCODE.md`, `STAGE_01_ROUND_STATE_MACHINE.md`,
  `STAGE_01_INVARIANT_CATALOGUE.md`, `STAGE_01_TERMINOLOGY.md`, `STAGE_01_TRACEABILITY_MATRIX.csv`.
- **New (15):** `STAGE_01W_CORRECTION_REPORT.md`, `STAGE_01W_ROLLBACK_ENVELOPE_AUDIT.md`,
  `STAGE_01W_MINER_ROLLBACK_LEGALITY_AUDIT.md`, `STAGE_01W_TEMPLATE_REFRESH_TRANSACTION_AUDIT.md`,
  `STAGE_01W_STRUCTURED_RANGE_RESULT_AUDIT.md`, `STAGE_01W_PLAN_BOUND_RANGE_AUDIT.md`,
  `STAGE_01W_TRANSITION_RESULT_CONTRACT_AUDIT.md`, `STAGE_01W_ASSIGNMENT_CREATION_RESULT_AUDIT.md`,
  `STAGE_01W_SETUP_RETRY_LIVENESS_AUDIT.md`, `STAGE_01W_PROCEDURE_SIGNATURE_CALL_AUDIT.md`,
  `STAGE_01W_PROCEDURE_CALL_GRAPH.md`, `STAGE_01W_SEMANTIC_TEST_VECTORS.md`, `STAGE_01W_SUPERSESSION_REGISTER.md`,
  `STAGE_01W_CROSS_DOCUMENT_AUDIT.md`, `STAGE_01W_CHECKSUM_MANIFEST.sha256`.
- **Scope:** every changed/new path is under `docs/thesis_revision_v45/stage_01/`. No executable source, configuration,
  DOCX, or PDF is modified; no `STAGE_01[A-V]_*` historical lettered artifact is modified.

## Result

Stage 1W discharges all 14 acceptance gates: corrections W1–W8 are reflected consistently across the pseudocode, round
state machine, invariant catalogue, terminology, and traceability matrix; the call graph resolves with no dangling
reference (83 procedures); TV186–TV197 are specified against exact procedures; the git delta is confined to the Stage-1
documentation set; protected drafts and Stage-1A–1V lettered artifacts are byte-identical to the parent; and the A1
baseline (`8.420833333 kWh`) and the binding **PoCol** naming rule are preserved.
