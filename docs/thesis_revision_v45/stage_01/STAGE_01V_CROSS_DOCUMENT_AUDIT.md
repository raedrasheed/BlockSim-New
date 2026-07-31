# Stage 1V — Cross-Document Audit (acceptance gates)

This audit verifies that corrections V1–V9 are reflected consistently across every normative document
(`STAGE_01_PROTOCOL_PSEUDOCODE.md`, `STAGE_01_ROUND_STATE_MACHINE.md`, `STAGE_01_INVARIANT_CATALOGUE.md`,
`STAGE_01_TERMINOLOGY.md`, `STAGE_01_TRACEABILITY_MATRIX.csv`) and the Stage-1V deliverables, and that the change
respects the documentation-only, A1-preserving discipline. Each gate records **PASS** with the grounding location and
the corroborating deliverable / test vector.

## Acceptance gates

| # | Gate | Result |
|--:|------|--------|
| 1 | In-flight recovery work is reconciled against the newest final census BEFORE new work is seated | **PASS** — §9 `SecurityFloorEvaluate` calls `CommitRecoveryCensus` → `ReconcilePendingRecoveryDecisions` → `ReconcilePendingRecoveryWork(RoundContext, episode, census.RecoveryCensusVersion, t)` → (only then) `ClassifyRecoveryWork`/`SeatRecoveryWork`; a still-warranted `DUE` record is REBOUND (same `RecoveryWorkID`), never replaced. `STAGE_01V_RECOVERY_WORK_RECONCILIATION_AUDIT.md`; TV174/TV175 |
| 2 | Every scheduling call passes an EXPLICIT `SchedulingSourceContext`; the bare-envelope alias is withdrawn | **PASS** — 21 catalogued scheduling sites all explicit (`ORDINARY_DISPATCH` / threaded / `POST_EPILOGUE`); the three previously-implicit sites (`AdversarialParticipationChangeEvent` ×2 `RangeAssign`, `LeaseExpiry` `RangeReassign`) now pass `ORDINARY_DISPATCH(dispatch_envelope)`; zero `SchedulingSourceContext`-typed parameter receives a bare `dispatch_envelope =`. `STAGE_01V_SCHEDULING_CONTEXT_CALL_AUDIT.md`; TV176 |
| 3 | `StartWake` is a transaction with structured outputs; no failure leaves a miner WAKING without a live `WakeCompleteEvent` | **PASS** — §4 `StartWake` seats the event FIRST, applies WAKING only after a successful seat, CANCELS on post-seat transition failure, returns `wake_seated` / `wake_schedule_failed_before_transition` / `wake_transition_failed_after_seat`; zero-latency POST_EPILOGUE targets `next_representable_simulation_time(source)`. `STAGE_01V_WAKE_TRANSACTION_AUDIT.md`; TV177/TV178 |
| 4 | `ReserveActivate` returns actual references and rolls back a post-assignment wake failure | **PASS** — §10 `ReserveActivate`/`ReserveActivateFromPlan` return the three `reserve_activation_*` dispositions; a wake failure after the PENDING assignment is created closes it legally, restores ledgers, asserts the miner stays `RESERVE`, and returns a `rollback_record` built from ACTUAL references. `STAGE_01V_PLAN_COMMIT_FIDELITY_AUDIT.md`; TV178/TV180 |
| 5 | The commit applies EXACTLY the prepared plan (no independent SELECT) | **PASS** — §9c/§10a `CommitRecoveryAssignmentPlan` calls `ReserveActivateFromPlan(reserve_miner = spec.MinerID, candidate_range = spec.range, assignment_origin = spec.origin, source_assignment = spec.source_assignment, …)` and revalidates the exact specs before mutation. `STAGE_01V_PLAN_COMMIT_FIDELITY_AUDIT.md`; TV179 |
| 6 | Security-floor recovery work is separated from coverage repair | **PASS** — §0.8 `RECOVERY_WORK_CLASS { SECURITY_FLOOR_RECOVERY_WORK, COVERAGE_REPAIR_WORK }`; §9c `ClassifyRecoveryWork` returns only `{ RESERVE_ACTIVATION_REQUIRED, NONE }` (`RANGE_REDISTRIBUTION_REQUIRED` removed); `SeatRecoveryWork` seats only `SECURITY_FLOOR_RECOVERY_WORK`. `STAGE_01V_RECOVERY_WORK_SEMANTICS_AUDIT.md`; catalogue I16; TV181 |
| 7 | The recovery-work lifecycle is complete and terminal cleanup cancels EVERY nonterminal record | **PASS** — §0.8 `RECOVERY_WORK_STATUS` (nine values; six persisted, three transient dispositions by the U3 atomic-seat discipline); `SeatRecoveryWork` atomically supersedes a stale prior before publishing; `CancelActiveRecoveryEpisode` iterates every record in `{CREATED, ARMED, DUE, APPLYING}`. `STAGE_01V_RECOVERY_WORK_LIFECYCLE_AUDIT.md`; TV182/TV183 |
| 8 | Ordinary assignment-setup failure has a NAMED executable rollback and an explicit liveness path | **PASS** — §2/§19 `RollbackParticipantSetup`/`RollbackTemplateRefreshSetup` cancel captured `WakeEventRef`s, close heads legally, restore ledgers, verify none WAKING; `PrepareParticipantsForNewRound`/`TemplateRefresh` then seat a strictly-later `SetupRetryEvent` or a declared `RoundAbort`. `STAGE_01V_SETUP_ROLLBACK_LIVENESS_AUDIT.md`; TV184/TV185 |
| 9 | No ambiguous boolean/AND returns; signature, RETURNS, and call sites agree | **PASS** — no `RETURN ScheduleEvent(...) AND …` composite; `RangeAssign`/`RangeReassign` now return structured `range_assigned`/`range_reassigned` (\| `*_wake_failed`) and no `StartWake` result is discarded. `STAGE_01V_PROCEDURE_SIGNATURE_CALL_AUDIT.md` |
| 10 | The procedure call graph has no dangling reference | **PASS** — 81 defined; every `CALL`/scheduled target resolves; 0 called-but-undefined (the two false positives `is`/`this` are prose). `STAGE_01V_PROCEDURE_CALL_GRAPH.md` |
| 11 | TV174–TV185 pass on paper | **PASS** — `STAGE_01V_SEMANTIC_TEST_VECTORS.md`; each vector names exact procedures + preconditions with no assumed guard/transition; A1 preserved |
| 12 | V1–V9 are consistent across pseudocode ↔ round SM ↔ catalogue ↔ terminology ↔ traceability | **PASS** — see the cross-document consistency table below |
| 13 | A1 discipline + binding naming rule | **PASS** — baseline `8.420833333 kWh` unchanged (every correction is control-flow / scheduling / transaction / lifecycle / provenance); zero functional uses of the prohibited variants ("PoCol-E", "Energy-Aware PoCol", "Enhanced PoCol"); no model/vendor/assistant identifier appears in any deliverable |
| 14 | Documentation-only git delta; historical artifacts frozen; protected drafts byte-identical | **PASS** — `git diff --name-only a8217fe` = the 5 normative `STAGE_01_*` docs only; 14 new `STAGE_01V_*` files; no `STAGE_01[A-U]_*` modified; `docs/…draft-42-00`, `…draft-44-00`, and all DOCX/PDF drafts are absent from the diff (byte-identical to the parent) |

## Cross-document consistency (gate 12 detail)

| Consistency check | Result |
|-------------------|--------|
| Recovery-work reconciliation (pseudocode ↔ round SM ↔ terminology ↔ traceability) | **PASS** — §9 ↔ round SM §3.10 V1 ↔ Stage-1V addendum ↔ R150 |
| Explicit scheduling context (pseudocode ↔ signature audit ↔ round SM ↔ terminology ↔ traceability) | **PASS** — §0.8/§4/§8/§9c/§10a ↔ `STAGE_01V_PROCEDURE_SIGNATURE_CALL_AUDIT.md` ↔ round SM §3.10 V2 ↔ terminology V2 ↔ R151 |
| StartWake transaction (pseudocode ↔ round SM ↔ terminology ↔ traceability) | **PASS** — §4 ↔ round SM §3.10 V3 ↔ Stage-1V addendum ↔ R152 |
| Reserve-activation references + rollback (pseudocode ↔ round SM ↔ traceability) | **PASS** — §10 ↔ round SM §3.10 V4 ↔ R153 |
| Plan-commit fidelity (pseudocode ↔ round SM ↔ traceability) | **PASS** — §9c/§10a ↔ round SM §3.10 V5 ↔ R154 |
| Recovery-work class separation (pseudocode ↔ catalogue ↔ round SM ↔ traceability) | **PASS** — §0.8/§9c ↔ catalogue I16 (V6) ↔ round SM §3.10 V6 ↔ R155 |
| Recovery-work lifecycle (pseudocode ↔ catalogue ↔ round SM ↔ traceability) | **PASS** — §0.8/§9c/§10a ↔ catalogue I16 (V7) ↔ round SM §3.10 V7 ↔ R156 |
| Setup rollback + liveness (pseudocode ↔ round SM ↔ traceability) | **PASS** — §2/§19/§0.7g ↔ round SM §3.10 V8 ↔ R157 |
| Disposition agreement (pseudocode ↔ signature audit ↔ round SM ↔ traceability) | **PASS** — §4/§12/§13 ↔ `STAGE_01V_PROCEDURE_SIGNATURE_CALL_AUDIT.md` ↔ round SM §3.10 V9 ↔ R158 |
| Test-vector coverage (traceability ↔ semantic vectors) | **PASS** — R159 ↔ `STAGE_01V_SEMANTIC_TEST_VECTORS.md` (TV174–TV185) |
| Call graph has no dangling calls | **PASS** — 81 defined; 0 undefined (`STAGE_01V_PROCEDURE_CALL_GRAPH.md`) |
| Traceability updated | **PASS** — R150–R159 (V1–V9 + TV174–TV185) added |

## Git delta

- **Modified (5):** `STAGE_01_PROTOCOL_PSEUDOCODE.md`, `STAGE_01_ROUND_STATE_MACHINE.md`,
  `STAGE_01_INVARIANT_CATALOGUE.md`, `STAGE_01_TERMINOLOGY.md`, `STAGE_01_TRACEABILITY_MATRIX.csv`.
- **New (14):** `STAGE_01V_CORRECTION_REPORT.md`, `STAGE_01V_RECOVERY_WORK_RECONCILIATION_AUDIT.md`,
  `STAGE_01V_SCHEDULING_CONTEXT_CALL_AUDIT.md`, `STAGE_01V_WAKE_TRANSACTION_AUDIT.md`,
  `STAGE_01V_PLAN_COMMIT_FIDELITY_AUDIT.md`, `STAGE_01V_RECOVERY_WORK_SEMANTICS_AUDIT.md`,
  `STAGE_01V_RECOVERY_WORK_LIFECYCLE_AUDIT.md`, `STAGE_01V_SETUP_ROLLBACK_LIVENESS_AUDIT.md`,
  `STAGE_01V_PROCEDURE_SIGNATURE_CALL_AUDIT.md`, `STAGE_01V_PROCEDURE_CALL_GRAPH.md`,
  `STAGE_01V_SEMANTIC_TEST_VECTORS.md`, `STAGE_01V_SUPERSESSION_REGISTER.md`,
  `STAGE_01V_CROSS_DOCUMENT_AUDIT.md`, `STAGE_01V_CHECKSUM_MANIFEST.sha256`.
- **Scope:** every changed/new path is under `docs/thesis_revision_v45/stage_01/`. No executable source, configuration,
  DOCX, or PDF is modified; no `STAGE_01[A-U]_*` historical lettered artifact is modified.

## Result

Stage 1V discharges all 14 acceptance gates: corrections V1–V9 are reflected consistently across the pseudocode, round
state machine, invariant catalogue, terminology, and traceability matrix; the call graph resolves with no dangling
reference (81 procedures); TV174–TV185 are specified against exact procedures; the git delta is confined to the Stage-1
documentation set; protected drafts and Stage-1A–1U lettered artifacts are byte-identical to the parent; and the A1
baseline (`8.420833333 kWh`) and the binding **PoCol** naming rule are preserved.
