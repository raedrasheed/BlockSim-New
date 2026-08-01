# Stage 1X — Cross-Document Audit (acceptance gates)

This audit verifies that corrections X1–X8 are reflected consistently across every normative document
(`STAGE_01_PROTOCOL_PSEUDOCODE.md`, `STAGE_01_ROUND_STATE_MACHINE.md`, `STAGE_01_INVARIANT_CATALOGUE.md`,
`STAGE_01_TERMINOLOGY.md`, `STAGE_01_TRACEABILITY_MATRIX.csv`) and the Stage-1X deliverables, and that the change
respects the documentation-only, A1-preserving discipline. Each gate records **PASS** with the grounding location and
corroborating deliverable / test vector. Gate numbering follows the Stage-1X acceptance list.

## Acceptance gates

| # | Gate | Result |
|--:|------|--------|
| 1 | `RollbackRecoveryAssignmentPlan` is a complete state transaction | **PASS** — from an explicit `rollback_record` of per-item pre-images it cancels every `WakeEventRef`, departs each still-`WAKING` miner to `OFFLINE` via legal `T12`, closes each exact head, restores the ledgers, and returns `rollback_completed(rolled_to_offline, rolled_back_items)` only after verifying no event pending / no head live / no miner `WAKING` (else `rollback_failed(residual_partial_assignment)`); the two post-epilogue callers take `RECOVERY_INSTALL_FAILED_ABORTED` / `RoundAbort` on incoherence. `STAGE_01X_RECOVERY_ROLLBACK_STATE_AUDIT.md`; TV198–TV200 |
| 2 | Every rollback `T12` is bound to the exact assignment version | **PASS** — `assignment_by_miner : MinerID -> (AssignmentID, assignment_version)` is populated after `assignment_created` and before `StartWake`; `RollbackParticipantSetup`/`RollbackTemplateRefreshSetup` and `RollbackRecoveryAssignmentPlan` pass `assignment_version_ref(aid, ver)` — never null when a head is held. `STAGE_01X_EXACT_ASSIGNMENT_ROLLBACK_AUDIT.md`; TV201 |
| 3 | Template-refresh initiation is split from template-assignment retry | **PASS** — `TemplateRefresh` does closure + construction + `TemplateCommit` + the idempotent `template_refresh_setup_committed` marker once and delegates to `ContinueTemplateRefreshAssignmentSetup`; a `TEMPLATE_REFRESH_SETUP` retry resumes the continuation and never re-enters `TemplateRefresh`. `STAGE_01X_TEMPLATE_REFRESH_RETRY_AUDIT.md`; TV202 |
| 4 | `SetupRetryEvent` guards are kind-specific and bounded | **PASS** — both targets require `ASSIGNMENT`; `PARTICIPANT_SETUP` → `PrepareParticipantsForNewRound`, `TEMPLATE_REFRESH_SETUP` → `ContinueTemplateRefreshAssignmentSetup`; `ROUND_INITIALISING`/`TEMPLATE_COMMITMENT` are rejected; an over-budget retry is a declared `RoundAbort(setup_retry_budget_exhausted)`; the phase is never left in `ASSIGNMENT` with no controller. `STAGE_01X_SETUP_RETRY_STATE_AUDIT.md`; TV203/TV204 |
| 5 | The commit returns the rollback record explicitly | **PASS** — `install_committed(rollback_record)`; `CommitRecoveryAssignmentPlan` builds and returns the complete record in every disposition; callers capture `commit.rollback_record`; no `plan.rollback_metadata` field exists (only withdrawn-name comments). `STAGE_01X_PLAN_COMMIT_OUTPUT_AUDIT.md`; TV205 |
| 6 | `assignment_creation_failed` is legally reachable | **PASS** — `CreatePendingAssignment` PRECONDITIONS constrain only type/shape; the runtime predicates (I1/custody/coverage/provenance/epoch) are in the guard and yield `assignment_creation_failed(reason)`, exercisable by a conforming caller. `STAGE_01X_ASSIGNMENT_CREATION_REACHABILITY_AUDIT.md`; TV206 |
| 7 | Head closures use only canonical enums + `closure_detail` | **PASS** — all six Stage-1X closure sites set `status`/`custody_status`/`termination_reason`/`revocation_reason` from the canonical enums and record the descriptor in `closure_detail`; a corpus scan finds no free-text token in any canonical enum field. `STAGE_01X_CANONICAL_CLOSURE_ENUM_AUDIT.md`; TV207 |
| 8 | Rollback is reconciled with energy / residency / census | **PASS** — each rollback `WAKING -> OFFLINE` runs through `ApplyMinerStateTransition`, closing the `WAKING` residency at the rollback `event_time`, charging the transition energy once, opening `OFFLINE`, adding no `H_active`, and changing the census only via `CommitSecurityCensus` on an `ACTIVE_HASHING` membership change; no open `WAKING` residency survives to horizon `T`. `STAGE_01X_ENERGY_RESIDENCY_ROLLBACK_AUDIT.md`; TV208/TV209 |
| 9 | The call graph has no dangling call | **PASS** — 84 procedures defined (adding `ContinueTemplateRefreshAssignmentSetup`); 0 dangling (`STAGE_01X_PROCEDURE_CALL_GRAPH.md`) |
| 10 | Signature ↔ RETURNS ↔ call-site agreement holds for every X-touched procedure | **PASS** — `STAGE_01X_PROCEDURE_SIGNATURE_CALL_AUDIT.md` |
| 11 | TV198 through TV209 pass on paper | **PASS** — `STAGE_01X_SEMANTIC_TEST_VECTORS.md`; each vector names the exact procedures + preconditions with no assumed guard/transition/edge; A1 preserved |
| 12 | No executable source/configuration/DOCX/PDF changes occur | **PASS** — `git diff --name-only a73feff` = the 5 normative `STAGE_01_*` docs only; all DOCX/PDF drafts and all executable source/config are absent from the diff (byte-identical to the parent) |
| 13 | No Stage-1A through Stage-1W historical artifact is modified | **PASS** — `git diff --name-only a73feff` shows no `STAGE_01[A-W]_*` file; supersessions recorded in `STAGE_01X_SUPERSESSION_REGISTER.md` |
| 14 | A1 discipline + naming rule preserved | **PASS** — baseline `8.420833333 kWh` unchanged; the algorithm is **PoCol** and the mechanism is the idle policy within PoCol throughout; no model/vendor/assistant identifier appears in any deliverable |

## Cross-document consistency

| Consistency check | Result |
|-------------------|--------|
| Recovery-plan rollback (pseudocode ↔ round SM ↔ invariant ↔ terminology ↔ traceability) | **PASS** — `RollbackRecoveryAssignmentPlan`/`CommitRecoveryAssignmentPlan` ↔ round SM §3.10b X1 ↔ I16 (Stage-1X) ↔ terminology `rollback_record` ↔ R169 |
| Exact assignment version (pseudocode ↔ round SM ↔ terminology ↔ invariant ↔ traceability) | **PASS** — `assignment_by_miner` + `assignment_version_ref` ↔ round SM §3.10b X2 ↔ terminology ↔ I16 ↔ R170 |
| Template-refresh split (pseudocode ↔ round SM ↔ terminology ↔ traceability) | **PASS** — `TemplateRefresh`/`ContinueTemplateRefreshAssignmentSetup` ↔ round SM §3.10b X3 ↔ terminology ↔ R171 |
| Kind-specific setup retry (pseudocode ↔ round SM ↔ invariant ↔ terminology ↔ traceability) | **PASS** — `SetupRetryEvent` ↔ round SM §3.10b X4 ↔ I16 ↔ terminology ↔ R172 |
| Explicit rollback record from commit (pseudocode ↔ round SM ↔ terminology ↔ traceability) | **PASS** — `install_committed(rollback_record)` ↔ round SM §3.10b X5 ↔ terminology ↔ R173 |
| Reachable creation failure (pseudocode ↔ round SM ↔ invariant ↔ terminology ↔ traceability) | **PASS** — `CreatePendingAssignment` guard ↔ round SM §3.10b X6 ↔ I1/I16 ↔ terminology ↔ R174 |
| Canonical closure + `closure_detail` (pseudocode ↔ round SM ↔ invariant ↔ terminology ↔ traceability) | **PASS** — six closure sites + §0.8 `closure_detail` ↔ round SM §3.10b X7 ↔ I18b/I16 ↔ terminology ↔ R175 |
| Rollback energy/residency/census (pseudocode ↔ round SM ↔ invariant ↔ traceability) | **PASS** — `ApplyMinerStateTransition` T12 ↔ round SM §3.10b X8 ↔ I16 + residency/energy invariants ↔ R176 |
| Test-vector coverage (traceability ↔ semantic vectors) | **PASS** — R177 ↔ `STAGE_01X_SEMANTIC_TEST_VECTORS.md` (TV198–TV209) |
| Call graph has no dangling calls | **PASS** — 84 defined; 0 undefined (`STAGE_01X_PROCEDURE_CALL_GRAPH.md`) |
| Traceability updated | **PASS** — R169–R177 (X1–X8 + TV198–TV209) added; the nine new rows each have 9 fields |
| A1 discipline + naming rule | **PASS** — baseline `8.420833333 kWh` unchanged; zero functional uses of a prohibited variant; no model/vendor/assistant identifier in any deliverable |

## Editorial cross-reference corrections

Two stale intra-document cross-references were corrected so the pseudocode matches the Stage-1X contract:
`CreatePendingAssignment`'s reachability note now cites `TV206` (was `TV204`); the `SetupRetryEvent` seating-table
descriptor now names `ContinueTemplateRefreshAssignmentSetup` for `TEMPLATE_REFRESH_SETUP` (was `TemplateRefresh`), with
the kind-specific / idempotent / bounded wording.

## Git delta

- **Modified (5):** `STAGE_01_PROTOCOL_PSEUDOCODE.md`, `STAGE_01_ROUND_STATE_MACHINE.md`,
  `STAGE_01_INVARIANT_CATALOGUE.md`, `STAGE_01_TERMINOLOGY.md`, `STAGE_01_TRACEABILITY_MATRIX.csv`.
- **New (15):** `STAGE_01X_CORRECTION_REPORT.md`, `STAGE_01X_RECOVERY_ROLLBACK_STATE_AUDIT.md`,
  `STAGE_01X_EXACT_ASSIGNMENT_ROLLBACK_AUDIT.md`, `STAGE_01X_TEMPLATE_REFRESH_RETRY_AUDIT.md`,
  `STAGE_01X_SETUP_RETRY_STATE_AUDIT.md`, `STAGE_01X_PLAN_COMMIT_OUTPUT_AUDIT.md`,
  `STAGE_01X_ASSIGNMENT_CREATION_REACHABILITY_AUDIT.md`, `STAGE_01X_CANONICAL_CLOSURE_ENUM_AUDIT.md`,
  `STAGE_01X_ENERGY_RESIDENCY_ROLLBACK_AUDIT.md`, `STAGE_01X_PROCEDURE_SIGNATURE_CALL_AUDIT.md`,
  `STAGE_01X_PROCEDURE_CALL_GRAPH.md`, `STAGE_01X_SEMANTIC_TEST_VECTORS.md`, `STAGE_01X_SUPERSESSION_REGISTER.md`,
  `STAGE_01X_CROSS_DOCUMENT_AUDIT.md`, `STAGE_01X_CHECKSUM_MANIFEST.sha256`.
- **Scope:** every changed/new path is under `docs/thesis_revision_v45/stage_01/`. No executable source, configuration,
  DOCX, or PDF is modified; no `STAGE_01[A-W]_*` historical lettered artifact is modified.
- **Protected drafts (byte-identical to the parent, recorded for the audit):**
  `docs/Raed-Rasheed-draft-42-00.docx` `2c3afdc5739109d0ea12ada96c3115d626a2188c1acbaeaa4b6020974884cbda`;
  `docs/Raed-Rasheed-draft-42-00.pdf` `131412bb2ce17ed97b98dfbefc136c7b5b226b9fd7372e79a25e4b0dc057e9c4`;
  `docs/Raed-Rasheed-draft-44-00.docx` `a31400bce212585df8197ee3d63e4eb887b5f5d0f2f8a65b916b2489dbc12340`.

## Result

Stage 1X discharges all 14 acceptance gates: corrections X1–X8 are reflected consistently across the pseudocode, round
state machine, invariant catalogue, terminology, and traceability matrix; the call graph resolves with no dangling
reference (84 procedures); TV198–TV209 are specified against exact procedures; the git delta is confined to the Stage-1
documentation set; protected drafts and Stage-1A–1W lettered artifacts are byte-identical to the parent; and the A1
baseline (`8.420833333 kWh`) and the binding **PoCol** naming rule are preserved.
