# Stage 1AA — Cross-Document Audit (acceptance gates)

This audit verifies that corrections AA1–AA6 are reflected consistently across every normative document
(`STAGE_01_PROTOCOL_PSEUDOCODE.md`, `STAGE_01_MINER_STATE_MACHINE.md`, `STAGE_01_ROUND_STATE_MACHINE.md`,
`STAGE_01_INVARIANT_CATALOGUE.md`, `STAGE_01_TERMINOLOGY.md`, `STAGE_01_TRACEABILITY_MATRIX.csv`) and the Stage-1AA
deliverables, and that the change respects the documentation-only, A1-preserving discipline. This audit was generated
AFTER the normative documents and the semantic vectors were final and after every Stage-1AA audit subagent completed;
every Stage-1AA deliverable named below EXISTS in the committed tree. Each gate records **PASS** with the grounding
location and corroborating deliverable / test vector. Gate numbering follows the Stage-1AA acceptance list.

## Acceptance gates

| # | Gate | Result |
|--:|------|--------|
| 1 | `RoundAbort` returns the single canonical `round_aborted(abort_record)`; every direct propagator lists and classifies it | **PASS** — `RoundAbort` RETURNS `round_aborted(abort_record(RoundID, TemplateID, reason))`; the direct propagators (`SetupRetryEvent`, `PrepareParticipantsForNewRound`, `ContinueTemplateRefreshAssignmentSetup`, `TemplateRefresh`, `FullRangeExhaustNoSolution`) list `round_aborted` in their RETURNS unions and classify it via `RETURN CALL RoundAbort`. `STAGE_01AA_ROUND_ABORT_RESULT_AUDIT.md`; TV227 |
| 2 | A target `RoundAbort` result maps `setup_retry_record.status = ABORTED` (never `CANCELLED`) | **PASS** — `SetupRetryEvent`'s guard branches and step-8 classification set `ABORTED` on `disp = round_aborted(abort_record)`; the recovery paths call the same canonical `RoundAbort` for effect (`recovery_finalising`). `STAGE_01AA_ROUND_ABORT_RESULT_AUDIT.md`; TV227 |
| 3 | Every SEATED retry record is terminalised at round closure through one named terminaliser | **PASS** — `CancelSetupRetriesForRound` sets a `SEATED` record `CANCELLED` (cancelling its `event_ref`); `CloseRoundAssignments` invokes it and lists `SetupRetryEvent` in its event-cancellation set. `STAGE_01AA_RETRY_TERMINALIZATION_AUDIT.md`; TV228 |
| 4 | An APPLYING record at closure is flagged and finishes terminal, never APPLIED | **PASS** — `CancelSetupRetriesForRound` sets `terminal_closure_pending` on an `APPLYING` record; `SetupRetryEvent`'s classification honours the flag → `ABORTED`/`CANCELLED`, never `APPLIED`. `STAGE_01AA_RETRY_TERMINALIZATION_AUDIT.md`; TV229 |
| 5 | A stale `RoundID` is handled through the record lifecycle (resolve + payload before stale check) | **PASS** — `SetupRetryEvent` resolves the record and payload-matches BEFORE the stale-`RoundID` check; a known `SEATED` record is terminalised `SUPERSEDED` (advanced) / `CANCELLED` (closed), never left `SEATED`. `STAGE_01AA_RETRY_TERMINALIZATION_AUDIT.md`; TV230/TV231 |
| 6 | `assignment_effect_policy` is part of the transition identity | **PASS** — `assignment_effect_policy` is a field of `TransitionEventID`; differing-policy transitions are distinct replay ids and never alias in `applied_transition_registry`. `STAGE_01AA_TRANSITION_POLICY_IDENTITY_AUDIT.md`; TV232 |
| 7 | `STATE_ONLY_ROLLBACK` is legal only on the exact rollback tuple; any other use mutates nothing | **PASS** — step (4b) admits `STATE_ONLY_ROLLBACK` IFF `WAKING → OFFLINE` ∧ `validation_abort` ∧ exact non-null `assignment_ref` ∧ `waking_origin_assignment_ref[MinerID] = assignment_ref`; else `illegal_transition` (logged `illegal_state_only_rollback_tuple`) before the atomic apply. `STAGE_01AA_STATE_ONLY_POLICY_GUARD_AUDIT.md`; TV233 |
| 8 | Every non-rollback caller uses `EDGE_DEFAULT`; the sole `STATE_ONLY_ROLLBACK` caller satisfies the tuple | **PASS** — step 5c's assignment update is gated on `EDGE_DEFAULT`; the only `STATE_ONLY_ROLLBACK` call site is `AbortPendingWakeForRollback`, whose call exactly satisfies the tuple and whose own wake-origin check departs no miner on mismatch. `STAGE_01AA_STATE_ONLY_POLICY_GUARD_AUDIT.md`; TV234 |
| 9 | Rollback-item storage is explicit and keyed | **PASS** — `setup_transaction.rollback_items` is a map keyed by `RollbackItemID`; each item is created `WakeEventRef = null` / `wake_result = NOT_ATTEMPTED` before `StartWake` and updated explicitly by key afterward; the setup rollbacks iterate deterministically by `RollbackItemID` and consume the stored record. `STAGE_01AA_ROLLBACK_ITEM_STORAGE_AUDIT.md`; TV235 |
| 10 | TV227 through TV235 pass on paper | **PASS** — `STAGE_01AA_SEMANTIC_TEST_VECTORS.md`; each vector names exact procedures + preconditions with no assumed guard/transition/edge/result name; A1 preserved |
| 11 | All Stage-1AA audits describe the final committed tree | **PASS** — every Stage-1AA audit was authored after the normative docs and `STAGE_01AA_SEMANTIC_TEST_VECTORS.md` were final; no audit states any Stage-1AA deliverable is missing, pending, or unwritten; this cross-document audit and the checksum manifest are generated last |
| 12 | No executable source/configuration/DOCX/PDF changes occur | **PASS** — `git diff --name-only f224a05` = the 6 normative `STAGE_01_*` docs only; all DOCX/PDF drafts and all executable source/config are absent (byte-identical to the parent) |
| 13 | No Stage-1A through Stage-1Z historical artifact is modified | **PASS** — `git diff --name-only f224a05` shows no `STAGE_01[A-Z]_*` file; supersessions recorded in `STAGE_01AA_SUPERSESSION_REGISTER.md` |
| 14 | Stage 2 is not begun; call graph resolves; naming/baseline preserved | **PASS** — the change is confined to Stage-1 documentation; no Stage-2 artifact is created; the call graph resolves with 86 callables (85 procedures + 1 function) and 0 dangling calls (`CancelSetupRetriesForRound` added, defined once + called once); the A1 baseline `8.420833333 kWh` and the binding **PoCol** naming rule are preserved |

## Cross-document consistency

| Consistency check | Result |
|-------------------|--------|
| Canonical `RoundAbort` result (pseudocode ↔ round SM ↔ invariant ↔ terminology ↔ traceability) | **PASS** — `round_aborted(abort_record)` ↔ round SM §3.10e AA1 ↔ I16 (Stage-1AA) ↔ terminology `round_aborted(abort_record)` ↔ R191 |
| Retry terminalisation at closure (pseudocode ↔ round SM ↔ invariant ↔ terminology ↔ traceability) | **PASS** — `CancelSetupRetriesForRound` / `terminal_closure_pending` ↔ round SM §3.10e AA2 ↔ I16 ↔ terminology ↔ R192 |
| Stale-`RoundID` terminalisation (pseudocode ↔ round SM ↔ invariant ↔ terminology ↔ traceability) | **PASS** — `SetupRetryEvent` guard order ↔ round SM §3.10e AA3 ↔ I16 ↔ terminology ↔ R193 |
| Transition-policy identity (pseudocode ↔ miner SM ↔ round SM ↔ invariant ↔ terminology ↔ traceability) | **PASS** — `assignment_effect_policy` in `TransitionEventID` ↔ miner SM §3.5 ↔ round SM §3.10e AA4 ↔ I16 ↔ terminology ↔ R194 |
| Legal `STATE_ONLY_ROLLBACK` tuple (pseudocode ↔ miner SM ↔ round SM ↔ invariant ↔ terminology ↔ traceability) | **PASS** — step (4b) guard ↔ miner SM §3.5 ↔ round SM §3.10e AA5 ↔ I16 ↔ terminology ↔ R195 |
| Keyed rollback item (pseudocode ↔ round SM ↔ invariant ↔ terminology ↔ traceability) | **PASS** — `RollbackItemID` / keyed `rollback_items` / `NOT_ATTEMPTED` ↔ round SM §3.10e AA6 ↔ I16/I20 ↔ terminology ↔ R196 |
| Test-vector coverage (traceability ↔ semantic vectors) | **PASS** — R197 ↔ `STAGE_01AA_SEMANTIC_TEST_VECTORS.md` (TV227–TV235) |
| Call graph has no dangling calls | **PASS** — 86 callables; 0 undefined; Stage 1AA adds one procedure `CancelSetupRetriesForRound` (`STAGE_01AA_PROCEDURE_CALL_GRAPH.md`) |
| Signature ↔ RETURNS ↔ call-site agreement | **PASS** — `STAGE_01AA_PROCEDURE_SIGNATURE_CALL_AUDIT.md` |
| Invariant I16 Stage-1AA clause registered; I20 unchanged | **PASS** — `STAGE_01_INVARIANT_CATALOGUE.md` I16 Stage-1AA clause (AA1–AA6); I20 (pre-constructor ledger restore) unchanged — AA6 changes item storage, not the restore semantics |
| Traceability updated | **PASS** — R191–R197 (AA1–AA6 + the TV227–TV235 block) added; the seven new rows each have 9 fields |
| A1 discipline + naming rule | **PASS** — baseline `8.420833333 kWh` unchanged; zero functional uses of a prohibited variant; no model/vendor/assistant identifier in any deliverable |

## Git delta

- **Modified (6):** `STAGE_01_PROTOCOL_PSEUDOCODE.md`, `STAGE_01_MINER_STATE_MACHINE.md`, `STAGE_01_ROUND_STATE_MACHINE.md`,
  `STAGE_01_INVARIANT_CATALOGUE.md`, `STAGE_01_TERMINOLOGY.md`, `STAGE_01_TRACEABILITY_MATRIX.csv`.
- **New (12):** `STAGE_01AA_CORRECTION_REPORT.md`, `STAGE_01AA_ROUND_ABORT_RESULT_AUDIT.md`,
  `STAGE_01AA_RETRY_TERMINALIZATION_AUDIT.md`, `STAGE_01AA_TRANSITION_POLICY_IDENTITY_AUDIT.md`,
  `STAGE_01AA_STATE_ONLY_POLICY_GUARD_AUDIT.md`, `STAGE_01AA_ROLLBACK_ITEM_STORAGE_AUDIT.md`,
  `STAGE_01AA_PROCEDURE_SIGNATURE_CALL_AUDIT.md`, `STAGE_01AA_PROCEDURE_CALL_GRAPH.md`,
  `STAGE_01AA_SEMANTIC_TEST_VECTORS.md`, `STAGE_01AA_SUPERSESSION_REGISTER.md`, `STAGE_01AA_CROSS_DOCUMENT_AUDIT.md`,
  `STAGE_01AA_CHECKSUM_MANIFEST.sha256`.
- **Scope:** every changed/new path is under `docs/thesis_revision_v45/stage_01/`. No executable source, configuration,
  DOCX, or PDF is modified; no `STAGE_01[A-Z]_*` historical lettered artifact is modified.
- **Protected drafts (byte-identical to the parent, recorded for the audit):**
  `docs/Raed-Rasheed-draft-42-00.docx` `2c3afdc5739109d0ea12ada96c3115d626a2188c1acbaeaa4b6020974884cbda`;
  `docs/Raed-Rasheed-draft-42-00.pdf` `131412bb2ce17ed97b98dfbefc136c7b5b226b9fd7372e79a25e4b0dc057e9c4`;
  `docs/Raed-Rasheed-draft-44-00.docx` `a31400bce212585df8197ee3d63e4eb887b5f5d0f2f8a65b916b2489dbc12340`.

## Result

Stage 1AA discharges all 14 acceptance gates: corrections AA1–AA6 are reflected consistently across the pseudocode, miner
state machine (new §3.5), round state machine (new §3.10e), invariant catalogue (I16 Stage-1AA clause), terminology, and
traceability matrix; the call graph resolves with no dangling reference (86 callables; Stage 1AA adds the one procedure
`CancelSetupRetriesForRound`, defined once and called once from `CloseRoundAssignments`); TV227–TV235 are specified against
exact procedures; every Stage-1AA audit describes the final committed tree; the git delta is confined to the Stage-1
documentation set; protected drafts and Stage-1A–1Z lettered artifacts are byte-identical to the parent; and the A1
baseline (`8.420833333 kWh`) and the binding **PoCol** naming rule are preserved.
