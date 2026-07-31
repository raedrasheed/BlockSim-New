# Stage 1F — Historical Artifact Register (F9)

Stage 1F treats every prior-stage audit / test-vector / manifest artifact (Stage 1A–1E) as a
**historical immutable snapshot**. None is modified in Stage 1F. This register records that
immutability and notes, without rewriting them, where a later normative document supersedes a
statement they contain.

## 1. Frozen artifacts (NOT modified in Stage 1F)

Verified by `git diff --name-only <base> -- .`: no `STAGE_01[A-E]_*` file appears in the Stage-1F
delta. The following remain byte-identical to their Stage-1E state (base
`71396bbdea59e7884ea8259ccb234adb882acb45`):

- Stage 1A: `STAGE_01A_CORRECTION_REPORT.md`, `STAGE_01A_CROSS_DOCUMENT_CONSISTENCY_AUDIT.md`,
  `STAGE_01A_SEMANTIC_DIFF.md`, `STAGE_01A_CHECKSUM_MANIFEST.sha256`
- Stage 1B: `STAGE_01B_CORRECTION_REPORT.md`, `STAGE_01B_CROSS_DOCUMENT_CONSISTENCY_AUDIT.md`,
  `STAGE_01B_EXHAUSTION_REASSIGNMENT_AUDIT.md`, `STAGE_01B_HASHRATE_IDENTITY_AUDIT.md`,
  `STAGE_01B_STATE_PATH_AUDIT.md`, `STAGE_01B_CHECKSUM_MANIFEST.sha256`
- Stage 1C: `STAGE_01C_CONSOLIDATION_REPORT.md`, `STAGE_01C_COVERAGE_LEDGER_AUDIT.md`,
  `STAGE_01C_CROSS_DOCUMENT_AUDIT.md`, `STAGE_01C_EVENT_ORDER_AUDIT.md`,
  `STAGE_01C_PSEUDOCODE_CONFORMANCE_AUDIT.md`, `STAGE_01C_SEMANTIC_TEST_VECTORS.md`,
  `STAGE_01C_CHECKSUM_MANIFEST.sha256`
- Stage 1D: `STAGE_01D_CORRECTION_REPORT.md`, `STAGE_01D_CROSS_DOCUMENT_AUDIT.md`,
  `STAGE_01D_EVENT_QUEUE_AUDIT.md`, `STAGE_01D_PROCEDURE_CALL_GRAPH.md`,
  `STAGE_01D_SEMANTIC_TEST_VECTORS.md`, `STAGE_01D_STATE_INVARIANT_AUDIT.md`,
  `STAGE_01D_CHECKSUM_MANIFEST.sha256`
- Stage 1E: `STAGE_01E_CORRECTION_REPORT.md`, `STAGE_01E_ASSIGNMENT_VALIDITY_AUDIT.md`,
  `STAGE_01E_PROPAGATION_FAILURE_AUDIT.md`, `STAGE_01E_ROUND_CLOSURE_TABLE.md`,
  `STAGE_01E_TEMPLATE_REFRESH_AUDIT.md`, `STAGE_01E_PROCEDURE_CALL_GRAPH.md`,
  `STAGE_01E_SEMANTIC_TEST_VECTORS.md`, `STAGE_01E_CROSS_DOCUMENT_AUDIT.md`,
  `STAGE_01E_CHECKSUM_MANIFEST.sha256`

Their SHA-256 checksums are recorded in `STAGE_01F_CHECKSUM_MANIFEST.sha256` for integrity.

## 2. Normative documents evolved in Stage 1F (current, not historical)

These un-suffixed normative documents are the LIVING specification and were updated in place (this is
permitted — F9 freezes only the lettered stage artifacts):

- `STAGE_01_PROTOCOL_PSEUDOCODE.md` — §0 concurrency/event model; F1–F8 procedures; §21 priority.
- `STAGE_01_MINER_STATE_MACHINE.md` — §1.7 concurrency conventions; T5 event-scheduling note.
- `STAGE_01_ROUND_STATE_MACHINE.md` — §2.6 active-propagation-set rule; R6–R8; F8 note.
- `STAGE_01_INVARIANT_CATALOGUE.md` — I17 boundary note; new I18 (one CURRENT version per lineage).
- `STAGE_01_TRACEABILITY_MATRIX.csv` — rows R32–R38.

## 3. Supersession notes (recorded here, NOT rewritten in the historical files)

| Historical statement | Superseded by (Stage 1F) | Nature |
|----------------------|--------------------------|--------|
| Stage-1D/1E procedure call graphs (`STAGE_01D/E_PROCEDURE_CALL_GRAPH.md`) predate the F-procedures | `STAGE_01F_PROCEDURE_CALL_GRAPH.md` | additive: the F1–F8 procedures and the `ApplyMinerStateTransition`/`StartWake` edges did not exist yet; the historical graphs remain correct for their stage |
| Stage-1E `STAGE_01E_ROUND_CLOSURE_TABLE.md` WAKING row described `WAKING → LOW_POWER_LISTEN` at closure | `STAGE_01_PROTOCOL_PSEUDOCODE.md` §17a (now `WAKING → OFFLINE`, T12) + `STAGE_01F_STATE_TRANSITION_HOOK.md` §4 | correction: the illegal edge is fixed in the normative pseudocode; the historical table is left as the Stage-1E snapshot |
| Stage-1D `STAGE_01D_EVENT_QUEUE_AUDIT.md` treats propagation as single-candidate | `STAGE_01F_CANDIDATE_LIFECYCLE_SPEC.md` + `STAGE_01F_CONCURRENCY_AUDIT.md` | additive: candidate-scoped multi-candidate propagation (F1–F3) generalises it |
| Stage-1E `STAGE_01E_SEMANTIC_TEST_VECTORS.md` (TV18–TV27) assume synchronous wake / single candidate | `STAGE_01F_SEMANTIC_TEST_VECTORS.md` (TV28–TV38) | additive: TV28–TV38 add the concurrency cases; TV18–TV27 remain valid for the properties they test |

No historical file is edited; every supersession is recorded ONLY here, per F9.

## Result

**HISTORICAL ARTIFACT REGISTER (F9): COMPLETE.** Stage 1A–1E artifacts are frozen and unmodified;
the current normative documents evolved in place; all supersessions are recorded here rather than by
rewriting prior-stage evidence.
