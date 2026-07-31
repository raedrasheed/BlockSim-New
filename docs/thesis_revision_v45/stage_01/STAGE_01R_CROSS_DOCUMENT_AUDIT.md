# Stage 1R — Cross-Document Audit (acceptance gates)

The thirteen Stage-1R acceptance gates, verified by procedure-call-graph, event-scheduling, and corpus analysis
over `docs/thesis_revision_v45/stage_01/` (not string search alone), plus cross-document consistency and
protected/historical-artifact verification. Name remains **PoCol**; mechanism is **the idle policy within
PoCol**; no property is claimed; the A1 baseline (`8.420833333 kWh`) is unchanged.

| # | Acceptance gate | Result |
|--:|-----------------|--------|
| 1 | Post-epilogue recovery application cannot enqueue an ordinary event at the already-drained `event_time` | **PASS** — §10a `ApplyRecoveryCompletionAfterEpilogue`/`CompleteSecurityRecovery` branch C transitions to `ASSIGNMENT` and seats ONE `RecoveryAssignmentContinuationEvent` at `next_representable_simulation_time(t) > t`; branches A/B/D seat nothing at `t`. `STAGE_01R_POST_EPILOGUE_CAUSALITY_AUDIT.md`; TV135 |
| 2 | No `event_time` is finalised while an ordinary event at that time remains | **PASS** — §0.7d `ProcessEventTime` ASSERTS `no ordinary event remains with event_time = t` BEFORE `ADD t to finalised_event_times`. `STAGE_01R_POST_EPILOGUE_CAUSALITY_AUDIT.md`; TV136 |
| 3 | `FinalizeEventTimeSecurityCensus` has one unambiguous invocation per `event_time` | **PASS** — §0.7d tail calls it EXACTLY ONCE (R2 step 1); the former "epilogue #2" is removed; §21/§0.7 confirm the epilogue is a single event-time action. `STAGE_01R_POST_EPILOGUE_CAUSALITY_AUDIT.md`; TV136 |
| 4 | Post-application settlement is not a second security decision | **PASS** — §10a `FinalizePostRecoveryApplicationState` archives the terminal/post-application census (source POST_RECOVERY_APPLICATION) and clears `security_census_dirty[t]` WITHOUT calling `SecurityFloorEvaluate`, seating no decision, enqueuing nothing at `t`. `STAGE_01R_POST_EPILOGUE_CAUSALITY_AUDIT.md`; TV142 |
| 5 | `TransitionEventID` contains `envelope_namespace` and `hook_id` where applicable | **PASS** — §0.9 builds `TransitionEventID` leading with `envelope_namespace` + `hook_id`; §0.7d materialises ORDINARY_EVENT/`hook_id=null`; a RUN_HOOK envelope missing its `hook_id` is rejected. `STAGE_01R_TRANSITION_NAMESPACE_AUDIT.md`; TV137 |
| 6 | Every nested run-hook transition preserves the full RUN_HOOK envelope | **PASS** — §20b `CloseRoundAtHorizon` threads `envelope_namespace = RUN_HOOK` + `HorizonHookID` through §17a `CloseRoundAssignments` → §7 `EnterLowPowerListen` → §0.9 `ApplyMinerStateTransition`; each nested transition carries them in its id. `STAGE_01R_TRANSITION_NAMESPACE_AUDIT.md`; TV138 |
| 7 | No decision is marked APPLIED before its recovery branch succeeds | **PASS** — §10a `ApplyRecoveryCompletionAfterEpilogue` sets `APPLYING`, calls `CompleteSecurityRecovery` (explicit per-branch disposition), and marks `APPLIED` + finalises ONLY on success; a failure records `APPLY_FAILED` and preserves the episode. `STAGE_01R_RECOVERY_APPLICATION_ATOMICITY_AUDIT.md`; TV140 |
| 8 | A terminal/horizon round cannot apply a pending recovery decision | **PASS** — §10a `ApplyRecoveryCompletionAfterEpilogue` TERMINAL guard (round in {ROUND_ACCEPTED, ROUND_ABORTED}) cancels every pending decision and returns `terminal_recovery_noop`; §20b closes the round before the T epilogue. `STAGE_01R_RECOVERY_APPLICATION_ATOMICITY_AUDIT.md`; TV139 |
| 9 | Census write ordering has an explicit `RunContext` owner | **PASS** — §1.0 `RunContext.security_census_write_seq_by_event_time` (initialised in `RunInitialise`, preserved across rounds) is incremented and stamped as `census_seq` by §0.8a `CommitSecurityCensus` (its sole owner). `STAGE_01R_CENSUS_SEQUENCE_AUDIT.md`; TV141 |
| 10 | Recovery-completion-due census provenance has its own source value | **PASS** — §10a `RecoveryCompletionDueEvent` calls `CaptureSecurityCensusOnRecoveryDeadline(..., census_source = RECOVERY_COMPLETION_DUE)`; `CENSUS_SOURCE` has five distinct values incl. RECOVERY_COMPLETION_DUE and POST_RECOVERY_APPLICATION. `STAGE_01R_CENSUS_SEQUENCE_AUDIT.md`; TV141 |
| 11 | TV135 through TV142 pass on paper | **PASS** — `STAGE_01R_SEMANTIC_TEST_VECTORS.md`; every vector names exact procedures + preconditions with no assumed guard/transition; A1 preserved |
| 12 | No executable source/configuration/DOCX/PDF changes | **PASS** — `git diff` confined to `docs/thesis_revision_v45/stage_01/`; draft-42 `2c3afdc5…`, draft-44 `a31400bc…` byte-identical |
| 13 | No Stage-1A through Stage-1Q historical artifact is modified | **PASS** — `git diff --name-only <base>` shows no `STAGE_01[A-Q]_*` file; supersessions recorded in `STAGE_01R_SUPERSESSION_REGISTER.md` |

## Cross-document consistency

| Check | Result |
|-------|--------|
| Name always **PoCol**; mechanism only "the idle policy within PoCol" | **PASS** — 0 functional uses of any rebranded variant; the only corpus occurrences are pre-existing prohibition clauses inherited from the base, none used as a name; Stage-1R deliverables use zero literal forbidden strings |
| One epilogue + settlement (pseudocode ↔ round SM ↔ invariant ↔ terminology) | **PASS** — §0.7d/§10a ↔ round SM §3.10 (R2) ↔ catalogue I17 (R2) ↔ Stage-1R addendum (R2) |
| Post-drain causality (pseudocode ↔ round SM ↔ traceability) | **PASS** — §0.7d/§10a `RecoveryAssignmentContinuationEvent` ↔ round SM §3.10/R13 (R1) ↔ R119 |
| Full transition envelope (pseudocode ↔ catalogue ↔ terminology ↔ traceability) | **PASS** — §0.9/§0.2/§20b ↔ catalogue I19 (R3) ↔ Stage-1R addendum ↔ R121 |
| Atomic application (pseudocode ↔ round SM ↔ traceability) | **PASS** — §10a `APPLYING`/`APPLY_FAILED`/`terminal_recovery_noop` ↔ round SM §3.10/R13/R14 (R4) ↔ R122 |
| Five census sources + write-seq owner (pseudocode ↔ catalogue ↔ terminology ↔ traceability) | **PASS** — §0.8a/§1.0 ↔ catalogue I17 (R5) ↔ Stage-1R addendum ↔ R123 |
| Consistent decision mirror (pseudocode ↔ terminology ↔ traceability) | **PASS** — §9 `SetRecoveryDecisionStatus` ↔ Stage-1R addendum (R6) ↔ R124 |
| Call graph has no dangling calls | **PASS** — 66 defined; 0 called-but-undefined (`STAGE_01R_PROCEDURE_CALL_GRAPH.md`) |
| Traceability updated | **PASS** — R119–R125 (R1–R6 + TV135–TV142) added |
| A1 discipline | **PASS** — baseline `8.420833333 kWh` unchanged; R1–R6 are causality / identity / atomicity / provenance / consistency corrections, never a change to how time or energy is counted |

## Supersession notes

All Stage-1R supersessions of Stage-1Q (and earlier) statements are recorded in
`STAGE_01R_SUPERSESSION_REGISTER.md` (6 entries) — historical `STAGE_01[A-Q]_*` files are NOT modified.

## Git delta

Modified (5, all un-suffixed normative): `STAGE_01_PROTOCOL_PSEUDOCODE.md`, `STAGE_01_ROUND_STATE_MACHINE.md`,
`STAGE_01_INVARIANT_CATALOGUE.md`, `STAGE_01_TERMINOLOGY.md`, `STAGE_01_TRACEABILITY_MATRIX.csv`. Added (10): the
`STAGE_01R_*` deliverables. No file outside `docs/thesis_revision_v45/stage_01/` is touched; no `STAGE_01[A-Q]_*`
file is modified.

## Result

All thirteen acceptance gates pass and all cross-document consistency checks hold. The specification conforms to
R1–R6 while preserving B1–B9, C1–C10, D1–D9, E1–E10, F1–F9, G1–G11, H1–H9, I-01…I-08, J1–J9, K1–K8, L1–L6,
M1–M6, N1–N4, O1–O5, P1–P5, and Q1–Q7. Name remains PoCol; no new consensus feature; documentation only; protected
drafts byte-identical; Stage-1A–1Q lettered artifacts frozen; A1 baseline unchanged. The prohibited
rebranded-algorithm-name variants are not used anywhere in this document.
