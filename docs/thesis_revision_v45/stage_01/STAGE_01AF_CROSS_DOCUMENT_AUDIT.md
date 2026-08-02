# Stage 1AF — Cross-Document Audit (21 acceptance gates)

This audit certifies, against the FINAL Stage-1AF normative tree, that the ten topical audits agree, that the five
modified `STAGE_01_*` documents are mutually consistent, and that every acceptance gate holds. It re-evaluates the tree
only after every normative edit (AF1–AF9), every companion-document update, every semantic vector (TV273–TV287), and
every fold-back correction were complete. The algorithm is **PoCol**; the mechanism is the idle policy within PoCol;
the A1 baseline (`8.420833333 kWh`) is preserved. This supersedes the Stage-1AE cross-document audit's gate marks for
the contracts AF corrects (`STAGE_01AF_SUPERSESSION_REGISTER.md`).

## 1. Topical-audit roll-up

| Topical audit | Correction | Verdict |
|---------------|-----------|---------|
| `STAGE_01AF_EVENT_DESCRIPTOR_AUDIT.md` | AF1 | PASS |
| `STAGE_01AF_DRIVER_EVENT_BINDING_AUDIT.md` | AF4 | PASS (one defect found and corrected in-tree) |
| `STAGE_01AF_DISPATCH_ADAPTER_AUDIT.md` | AF2 | PASS |
| `STAGE_01AF_SCHEDULER_SCHEMA_ENFORCEMENT_AUDIT.md` | AF3 | PASS |
| `STAGE_01AF_QUEUE_POP_AND_CONTEXT_AUDIT.md` | AF5 | PASS |
| `STAGE_01AF_RUNCONTEXT_OWNERSHIP_AUDIT.md` | AF6 | PASS |
| `STAGE_01AF_HASH_RESULT_CONTRACT_AUDIT.md` | AF7 | PASS |
| `STAGE_01AF_ACCEPTANCE_BATCH_SEATING_AUDIT.md` | AF8 | PASS |
| `STAGE_01AF_INTEGRITY_REVERSE_BINDING_AUDIT.md` | AF9 | PASS |
| `STAGE_01AF_PROCEDURE_SIGNATURE_CALL_AUDIT.md` | signatures/RETURNS/call sites | PASS (same defect, corrected in-tree) |

**Fold-back record.** Two independent audits (`STAGE_01AF_DRIVER_EVENT_BINDING_AUDIT.md`,
`STAGE_01AF_PROCEDURE_SIGNATURE_CALL_AUDIT.md`) found one genuine, non-behavioral defect: `PrepareParticipantsEvent`'s
declared RETURNS union omitted the propagated `participant_set_setup_retry_seated(SetupRetryID, reason)` disposition.
The union was corrected in `STAGE_01_PROTOCOL_PSEUDOCODE.md` to enumerate it (at parity with the two sibling propagating
wrappers), and both audit files were updated to record the defect as found-and-fixed. No other defect survived
verification.

## 2. Acceptance gates

| # | Gate | Evidence | Verdict |
|---|------|----------|---------|
| 1 | AF1 — one executable `event_descriptor` per queued type; exact closed payload keys + types; five categories kept apart | `EVENT_DESCRIPTOR_AUDIT` (20 types; STRUCTURE + core/binding tables §0.7g) | PASS |
| 2 | AF1 — corrected rows: RoundInitialise/TemplateCommit/MinerRegister mint/derive their id; WakeComplete carries assignment_version; ReserveActivate gets a scheduling_context wrapper; RoundAbort removed from the queued schema | `EVENT_DESCRIPTOR_AUDIT`; no `ScheduleEvent(...RoundAbort...)` seat exists | PASS |
| 3 | AF2 — `BuildHandlerInvocation` binds the exact named handler args; no undeclared arg / unresolved alias / derived-for-input | `DISPATCH_ADAPTER_AUDIT` (7/7) | PASS |
| 4 | AF2 — WakeComplete `target_assignment ← version(...)`; ReserveActivate never gets a bare envelope; BlockAcceptancePoint no env/ref; SetupRetry both; RoundInitialise RunContext | `DISPATCH_ADAPTER_AUDIT`; TV276/277/278 | PASS |
| 5 | AF3 — full schema enforcement before mutation: unknown type / microphase mismatch / exact-key-set (missing+EXTRA)+type / tie-key unavailable | `SCHEDULER_SCHEMA_ENFORCEMENT_AUDIT`; TV279–282 | PASS |
| 6 | AF3 — EQ ordered by descriptor-derived `stable_tie_key`, not the generic `(CandidateID, MinerID, AssignmentID)` tuple | `SCHEDULER_SCHEMA_ENFORCEMENT_AUDIT` (INSERT line) | PASS |
| 7 | AF4 — six driver-event wrappers: store exact payload, receive declared context, call domain with exact args, return sound disposition, one descriptor row each | `DRIVER_EVENT_BINDING_AUDIT` (6/6 after correction) | PASS |
| 8 | AF5 — atomic POP before dispatch; complete `EQ.current_*` set then atomic CONSUMED + clear; ONE representation; "projection" removed; AE3 re-query preserved | `QUEUE_POP_AND_CONTEXT_AUDIT` (7/7); TV283/284 | PASS |
| 9 | AF6 — `RunInitialise` returns every per-run field; no implicit-global per-run registry | `RUNCONTEXT_OWNERSHIP_AUDIT`; `queued_event_registry` + `setup_retry_by_seat_event_ref` now in RETURNS | PASS |
| 10 | AF7 — `StartHashing` explicit dual RETURN; `HashWorkEvent` continuation `continued(...)` matches RETURNS; caller reconciled | `HASH_RESULT_CONTRACT_AUDIT` (5/5); TV285 | PASS |
| 11 | AF8 — `SeatAcceptanceBatchFinalize` seats via ScheduleEvent; one live seat per (ts, point); stored cancellable EventRef; replay-safe; RoundAbort cancels | `ACCEPTANCE_BATCH_SEATING_AUDIT` (7/7); TV286 | PASS |
| 12 | AF9 — `HandleDispatchIntegrityFailure` non-asserting on corrupt reverse binding; records `dispatch_integrity_owner_binding_corrupt`; mutates nothing; aborts nothing | `INTEGRITY_REVERSE_BINDING_AUDIT` (6/6); TV287 | PASS |
| 13 | AF10 — supersession register records the inaccurate Stage-1AE audit claims (schema conflation; bare-envelope; projection-not-POP; missing RETURN + shape; gates 3/5/6/10/12/13) | `STAGE_01AF_SUPERSESSION_REGISTER.md` | PASS |
| 14 | Signatures — INPUTS/RETURNS/call-site agreement for every AF-touched procedure | `PROCEDURE_SIGNATURE_CALL_AUDIT` (after correction) | PASS |
| 15 | Call graph closes — 0 dangling references, 97 defined callables | `STAGE_01AF_PROCEDURE_CALL_GRAPH.md`; re-verified | PASS |
| 16 | Semantic vectors — TV273–TV287 (15) name only defined procedures/results; preserve A1 | `STAGE_01AF_SEMANTIC_TEST_VECTORS.md` | PASS |
| 17 | Round state machine — §3.10j Stage-1AF addendum (AF1–AF10) consistent with the pseudocode | `STAGE_01_ROUND_STATE_MACHINE.md` §3.10j | PASS |
| 18 | Invariants — I16 Stage-1AF clause added; I21 strengthened with the AF5 one-representation/atomic-pop clause | `STAGE_01_INVARIANT_CATALOGUE.md` | PASS |
| 19 | Terminology — Stage-1AF addendum defines event_descriptor / BuildHandlerInvocation / wrappers / rejection set / atomic-pop / SeatAcceptanceBatchFinalize / owner-binding-corrupt | `STAGE_01_TERMINOLOGY.md` | PASS |
| 20 | Traceability — rows R238–R248 append AF1–AF10 + the TV block; 9 comma-separated fields; no embedded commas | `STAGE_01_TRACEABILITY_MATRIX.csv` (validated) | PASS |
| 21 | Scope/integrity — protected drafts byte-identical; no forbidden model/vendor identifier; A1 `8.420833333 kWh` present; PoCol naming; delta = 5 modified `STAGE_01_*` + 16 new `STAGE_01AF_*`; no source/config/DOCX/PDF; no Stage-1A…1AE artifact modified; Stage 2 not begun | §3 below; `STAGE_01AF_CHECKSUM_MANIFEST.sha256` | PASS |

## 3. Scope & integrity verification

- **Protected drafts byte-identical** (unchanged):
  - `docs/Raed-Rasheed-draft-42-00.docx` = `2c3afdc5739109d0ea12ada96c3115d626a2188c1acbaeaa4b6020974884cbda`
  - `docs/Raed-Rasheed-draft-42-00.pdf` = `131412bb2ce17ed97b98dfbefc136c7b5b226b9fd7372e79a25e4b0dc057e9c4`
  - `docs/Raed-Rasheed-draft-44-00.docx` = `a31400bce212585df8197ee3d63e4eb887b5f5d0f2f8a65b916b2489dbc12340`
- **No forbidden identifier.** A scan for model/vendor identifiers across every modified `STAGE_01_*` document and every
  `STAGE_01AF_*` deliverable returns no match.
- **A1 baseline** `8.420833333 kWh` present and unchanged across the tree; **PoCol** naming and "the idle policy within
  PoCol" mechanism unchanged.
- **Delta confined** to the five modified normative documents (`STAGE_01_PROTOCOL_PSEUDOCODE.md`,
  `STAGE_01_ROUND_STATE_MACHINE.md`, `STAGE_01_INVARIANT_CATALOGUE.md`, `STAGE_01_TERMINOLOGY.md`,
  `STAGE_01_TRACEABILITY_MATRIX.csv`) and the sixteen new `STAGE_01AF_*` deliverables. No executable source,
  configuration, DOCX, or PDF was modified; no Stage-1A…1AE lettered artifact was modified; no experiment was run;
  Stage 2 is not begun.

## 4. Overall verdict

**PASS — all 21 acceptance gates hold against the final Stage-1AF normative tree.** The executable dispatch-binding and
queue-pop contract (AF1–AF10) is realised faithfully; the one genuine defect found during verification
(`PrepareParticipantsEvent` RETURNS enumeration) was corrected in-tree and re-verified; the call graph closes with 0
dangling references over 97 callables; the companion documents are mutually consistent; the protected drafts are
byte-identical; and the A1 baseline and PoCol naming are preserved.
