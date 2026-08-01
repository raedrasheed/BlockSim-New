# Stage 1Z — Cross-Document Audit (acceptance gates)

This audit verifies that corrections Z1–Z6 are reflected consistently across every normative document
(`STAGE_01_PROTOCOL_PSEUDOCODE.md`, `STAGE_01_MINER_STATE_MACHINE.md`, `STAGE_01_ROUND_STATE_MACHINE.md`,
`STAGE_01_INVARIANT_CATALOGUE.md`, `STAGE_01_TERMINOLOGY.md`, `STAGE_01_TRACEABILITY_MATRIX.csv`) and the Stage-1Z
deliverables, and that the change respects the documentation-only, A1-preserving discipline. This audit was generated
AFTER the normative documents and the semantic vectors were final and after every Stage-1Z audit subagent completed;
every Stage-1Z deliverable named below EXISTS in the committed tree. Each gate records **PASS** with the grounding
location and corroborating deliverable / test vector. Gate numbering follows the Stage-1Z acceptance list.

## Acceptance gates

| # | Gate | Result |
|--:|------|--------|
| 1 | SetupRetryStatus has executable producers for every retained status | **PASS** — SEATED at the seat (after `ScheduleEvent`); APPLYING at the first dispatch; APPLIED / SUPERSEDED / ABORTED / CANCELLED from the captured target result and the guard exits. `STAGE_01Z_SETUP_RETRY_LIFECYCLE_AUDIT.md`; TV219/TV220 |
| 2 | A SEATED retry's first dispatch is not duplicate-suppressed | **PASS** — the guard suppresses IFF `rec.status != SEATED`; a published SEATED record's first dispatch flips `SEATED -> APPLYING` and executes. `STAGE_01Z_SETUP_RETRY_LIFECYCLE_AUDIT.md`; TV219 |
| 3 | Target results update the retry record deterministically | **PASS** — `SetupRetryEvent` CAPTURES `disp <- CALL target` (no direct `RETURN CALL`) and classifies into APPLIED / SUPERSEDED / ABORTED / CANCELLED; `applied` = `status = APPLIED`, set only after the result. `STAGE_01Z_SETUP_RETRY_LIFECYCLE_AUDIT.md`; TV220 |
| 4 | Setup before-images are captured before CreatePendingAssignment | **PASS** — both setup procedures `SET before_image <- coverage_custody_before_image(...)` BEFORE `CreatePendingAssignment`; a creation failure discards it and creates no item. `STAGE_01Z_PREMUTATION_SNAPSHOT_AUDIT.md`; TV221 |
| 5 | Rollback restores the actual pre-constructor ledger state | **PASS** — invariant I20 formalises the pre-constructor restore; `AbortPendingWakeForRollback` / `RollbackRecoveryAssignmentPlan` restore from the item's `before_image`. `STAGE_01Z_PREMUTATION_SNAPSHOT_AUDIT.md`; TV221 |
| 6 | A pre-seat wake-scheduling failure has WakeEventRef = null explicitly | **PASS** — the seating loops set `item.WakeEventRef <- null` on `wake_schedule_failed_before_transition`; the item always exists with an explicit (possibly null) ref. `STAGE_01Z_NULLABLE_WAKE_REFERENCE_AUDIT.md`; TV222 |
| 7 | No rollback performs an undefined wake_by_miner lookup | **PASS** — `AbortPendingWakeForRollback` cancels only a non-null, still-pending `WakeEventRef` read from the centralised `setup_rollback_item`; a scan finds zero `.wake_by_miner[` indexing. `STAGE_01Z_NULLABLE_WAKE_REFERENCE_AUDIT.md`; TV222 |
| 8 | ApplyMinerStateTransition has an executable STATE_ONLY_ROLLBACK policy | **PASS** — `assignment_effect_policy = EDGE_DEFAULT` in the signature; step (5c) gated on `EDGE_DEFAULT`; `STATE_ONLY_ROLLBACK` at the single rollback call site. `STAGE_01Z_T12_ASSIGNMENT_EFFECT_AUDIT.md`; TV223 |
| 9 | Only AbortPendingWakeForRollback closes the rollback assignment | **PASS** — under `STATE_ONLY_ROLLBACK` the hook mutates no assignment; the canonical close is performed once by `AbortPendingWakeForRollback` — the hook and the operation never both close. `STAGE_01Z_T12_ASSIGNMENT_EFFECT_AUDIT.md`; TV223 |
| 10 | A detached/closed assignment rollback is bound to the exact wake-origin version | **PASS** — `waking_origin_assignment_ref[MinerID]` (set on WAKING entry, cleared on WAKING exit) must equal the rollback item's `assignment_version_ref` before the T12; a mismatch returns `wake_abort_failed` and departs no miner. `STAGE_01Z_WAKING_ORIGIN_BINDING_AUDIT.md`; TV224/TV225 |
| 11 | TV219 through TV226 pass on paper | **PASS** — `STAGE_01Z_SEMANTIC_TEST_VECTORS.md`; each vector names exact procedures + preconditions with no assumed guard/transition/edge/result name; A1 preserved |
| 12 | All Stage-1Z audits describe the final committed tree | **PASS** — every Stage-1Z audit was authored after the normative docs and `STAGE_01Z_SEMANTIC_TEST_VECTORS.md` were final; no audit states any Stage-1Z deliverable is missing, pending, or unwritten; this cross-document audit and the checksum manifest are generated last |
| 13 | No executable source/configuration/DOCX/PDF changes occur | **PASS** — `git diff --name-only 479640a` = the 6 normative `STAGE_01_*` docs only; all DOCX/PDF drafts and all executable source/config are absent (byte-identical to the parent) |
| 14 | No Stage-1A through Stage-1Y historical artifact is modified | **PASS** — `git diff --name-only 479640a` shows no `STAGE_01[A-Y]_*` file; supersessions recorded in `STAGE_01Z_SUPERSESSION_REGISTER.md` |
| 15 | Stage 2 is not begun | **PASS** — the change is confined to Stage-1 documentation; no Stage-2 artifact is created; the A1 baseline `8.420833333 kWh` and the binding **PoCol** naming rule are preserved |

## Cross-document consistency

| Consistency check | Result |
|-------------------|--------|
| Setup-retry lifecycle (pseudocode ↔ round SM ↔ invariant ↔ terminology ↔ traceability) | **PASS** — `setup_retry_records` ↔ round SM §3.10d Z1 ↔ I16 (Stage-1Z) ↔ terminology `setup_retry_record` ↔ R184 |
| Pre-mutation snapshot (pseudocode ↔ round SM ↔ invariant ↔ terminology ↔ traceability) | **PASS** — before-image before creation ↔ round SM §3.10d Z2 ↔ I20 + I16 ↔ terminology ↔ R185 |
| Nullable wake reference (pseudocode ↔ round SM ↔ invariant ↔ terminology ↔ traceability) | **PASS** — `WakeEventRef | null` ↔ round SM §3.10d Z3 ↔ I16 ↔ terminology ↔ R186 |
| T12 assignment-effect policy (pseudocode ↔ miner SM ↔ round SM ↔ invariant ↔ terminology ↔ traceability) | **PASS** — `assignment_effect_policy` ↔ miner SM §3.4 ↔ round SM §3.10d Z4 ↔ I16 ↔ terminology ↔ R187 |
| Wake-origin binding (pseudocode ↔ miner SM ↔ round SM ↔ invariant ↔ terminology ↔ traceability) | **PASS** — `waking_origin_assignment_ref` ↔ miner SM §3.4 ↔ round SM §3.10d Z5 ↔ I16/I19 ↔ terminology ↔ R188 |
| Centralised rollback item (pseudocode ↔ round SM ↔ invariant ↔ terminology ↔ traceability) | **PASS** — `setup_rollback_item` / `rollback_items` ↔ round SM §3.10d Z6 ↔ I16/I20 ↔ terminology ↔ R189 |
| Test-vector coverage (traceability ↔ semantic vectors) | **PASS** — R190 ↔ `STAGE_01Z_SEMANTIC_TEST_VECTORS.md` (TV219–TV226) |
| Call graph has no dangling calls | **PASS** — 85 defined; 0 undefined; Stage 1Z adds no new procedure (`STAGE_01Z_PROCEDURE_CALL_GRAPH.md`) |
| Signature ↔ RETURNS ↔ call-site agreement | **PASS** — `STAGE_01Z_PROCEDURE_SIGNATURE_CALL_AUDIT.md` |
| New invariant I20 registered | **PASS** — `STAGE_01_INVARIANT_CATALOGUE.md` §I20 (pre-constructor ledger restore, Z2) |
| Traceability updated | **PASS** — R184–R190 (Z1–Z6 + TV219–TV226) added; the seven new rows each have 9 fields |
| A1 discipline + naming rule | **PASS** — baseline `8.420833333 kWh` unchanged; zero functional uses of a prohibited variant; no model/vendor/assistant identifier in any deliverable |

## Git delta

- **Modified (6):** `STAGE_01_PROTOCOL_PSEUDOCODE.md`, `STAGE_01_MINER_STATE_MACHINE.md`, `STAGE_01_ROUND_STATE_MACHINE.md`,
  `STAGE_01_INVARIANT_CATALOGUE.md`, `STAGE_01_TERMINOLOGY.md`, `STAGE_01_TRACEABILITY_MATRIX.csv`.
- **New (12):** `STAGE_01Z_CORRECTION_REPORT.md`, `STAGE_01Z_SETUP_RETRY_LIFECYCLE_AUDIT.md`,
  `STAGE_01Z_PREMUTATION_SNAPSHOT_AUDIT.md`, `STAGE_01Z_NULLABLE_WAKE_REFERENCE_AUDIT.md`,
  `STAGE_01Z_T12_ASSIGNMENT_EFFECT_AUDIT.md`, `STAGE_01Z_WAKING_ORIGIN_BINDING_AUDIT.md`,
  `STAGE_01Z_PROCEDURE_SIGNATURE_CALL_AUDIT.md`, `STAGE_01Z_PROCEDURE_CALL_GRAPH.md`,
  `STAGE_01Z_SEMANTIC_TEST_VECTORS.md`, `STAGE_01Z_SUPERSESSION_REGISTER.md`, `STAGE_01Z_CROSS_DOCUMENT_AUDIT.md`,
  `STAGE_01Z_CHECKSUM_MANIFEST.sha256`.
- **Scope:** every changed/new path is under `docs/thesis_revision_v45/stage_01/`. No executable source, configuration,
  DOCX, or PDF is modified; no `STAGE_01[A-Y]_*` historical lettered artifact is modified.
- **Protected drafts (byte-identical to the parent, recorded for the audit):**
  `docs/Raed-Rasheed-draft-42-00.docx` `2c3afdc5739109d0ea12ada96c3115d626a2188c1acbaeaa4b6020974884cbda`;
  `docs/Raed-Rasheed-draft-42-00.pdf` `131412bb2ce17ed97b98dfbefc136c7b5b226b9fd7372e79a25e4b0dc057e9c4`;
  `docs/Raed-Rasheed-draft-44-00.docx` `a31400bce212585df8197ee3d63e4eb887b5f5d0f2f8a65b916b2489dbc12340`.

## Result

Stage 1Z discharges all 15 acceptance gates: corrections Z1–Z6 are reflected consistently across the pseudocode, miner
state machine, round state machine, invariant catalogue (with new invariant I20), terminology, and traceability matrix;
the call graph resolves with no dangling reference (85 procedures; Stage 1Z adds no new procedure); TV219–TV226 are
specified against exact procedures; every Stage-1Z audit describes the final committed tree; the git delta is confined to
the Stage-1 documentation set; protected drafts and Stage-1A–1Y lettered artifacts are byte-identical to the parent; and
the A1 baseline (`8.420833333 kWh`) and the binding **PoCol** naming rule are preserved.
