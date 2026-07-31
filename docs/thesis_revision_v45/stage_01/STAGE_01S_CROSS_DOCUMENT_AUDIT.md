# Stage 1S — Cross-Document Audit (acceptance gates)

The thirteen Stage-1S acceptance gates, verified by procedure-call-graph, signature/call-site, event-scheduling,
and corpus analysis over `docs/thesis_revision_v45/stage_01/` (not string search alone), plus cross-document
consistency and protected/historical-artifact verification. Name remains **PoCol**; mechanism is **the idle policy
within PoCol**; no property is claimed; the A1 baseline (`8.420833333 kWh`) is unchanged.

| # | Acceptance gate | Result |
|--:|-----------------|--------|
| 1 | Every `ApplyMinerStateTransition` call passes one complete explicit envelope | **PASS** — §0.9 signature takes ONE `transition_envelope`; all 14 direct call sites pass `transition_envelope = dispatch_envelope`. `STAGE_01S_FULL_ENVELOPE_AUDIT.md`, `STAGE_01S_PROCEDURE_SIGNATURE_CALL_AUDIT.md`; TV143 |
| 2 | No prose-based implicit argument propagation remains | **PASS** — the R3 "namespace fields travel implicitly" clause is WITHDRAWN in §0.9; the id is built from the destructured object; no numeric-only call site exists. `STAGE_01S_FULL_ENVELOPE_AUDIT.md`; TV143/TV144 |
| 3 | Branch C cannot leave `SECURITY_RECOVERY` before continuation seating succeeds | **PASS** — §10a `CompleteSecurityRecovery` branch C computes `t_cont`, validates `t_cont <= T`, seats, and only THEN returns `DEFERRED`; a failed seat / target-beyond-`T` returns `FAILED` with `round_state` unchanged. `STAGE_01S_DEFERRED_RECOVERY_ATOMICITY_AUDIT.md`; TV145 |
| 4 | Branch C is not APPLIED merely because a continuation was seated | **PASS** — a `DEFERRED` disposition leaves the decision `APPLYING`, `recovery_outcome_finalised` unset, and `current_recovery_episode` intact (§10a `ApplyRecoveryCompletionAfterEpilogue`). `STAGE_01S_DEFERRED_RECOVERY_ATOMICITY_AUDIT.md`; TV146 |
| 5 | APPLIED occurs only after the branch reaches HASHING or a declared terminal disposition succeeds | **PASS** — §10a `RecoveryAssignmentContinuationEvent` marks `APPLIED` (RESTORED) only after `CompleteAssignmentPhase → HASHING`; branches A/B/D mark APPLIED on their SUCCESS; UNRECOVERABLE via `RoundAbort` (terminal). `STAGE_01S_DEFERRED_RECOVERY_ATOMICITY_AUDIT.md`; TV147 |
| 6 | No failure leaves `ASSIGNMENT` with an active recovery episode and no live continuation | **PASS** — §10a a plan-invalid failure BEFORE the transition stays `SECURITY_RECOVERY`; an install failure AFTER the transition takes a declared recovery-finalising `RoundAbort`. `STAGE_01S_DEFERRED_RECOVERY_ATOMICITY_AUDIT.md`; TV148 |
| 7 | Terminal closure clears the active recovery episode with an explicit cancellation disposition | **PASS** — §17a `CloseRoundAssignments` → §9 `CancelActiveRecoveryEpisode` records `TERMINAL_CANCELLED`, cancels events, clears `current_recovery_episode` (unless the recovery-finalising abort). `STAGE_01S_TERMINAL_RECOVERY_CLEANUP_AUDIT.md`; TV149 |
| 8 | Exactly one procedure owns dirty-flag clearing | **PASS** — §0.8a `SettleSecurityCensusDirty` is the ONLY procedure clearing `security_census_dirty` (2 settlement kinds); a grep finds `CLEAR security_census_dirty` ONLY inside it. `STAGE_01S_CENSUS_SETTLEMENT_OWNERSHIP_AUDIT.md`; TV151 |
| 9 | The primary security epilogue is invoked exactly once per `event_time` | **PASS** — §0.7d `ProcessEventTime` calls `FinalizeEventTimeSecurityCensus(t)` UNCONDITIONALLY exactly once; the procedure owns the dirty check (`no_census_change`). `STAGE_01S_CENSUS_SETTLEMENT_OWNERSHIP_AUDIT.md`; TV150 |
| 10 | Post-epilogue scheduling has an explicit valid context | **PASS** — §0.7e `PostEpilogueSchedulingContext` + `ScheduleEvent` `post_epilogue_context` enforce `target_event_time > source_event_time`, `delta_cycle = 0`; the branch-C seat carries it (§10a). `STAGE_01S_POST_EPILOGUE_SCHEDULER_AUDIT.md`; TV152 |
| 11 | TV143 through TV152 pass on paper | **PASS** — `STAGE_01S_SEMANTIC_TEST_VECTORS.md`; every vector names exact procedures + preconditions with no assumed guard/transition; A1 preserved |
| 12 | No executable source/configuration/DOCX/PDF changes | **PASS** — `git diff` confined to `docs/thesis_revision_v45/stage_01/`; draft-42 `2c3afdc5…`, draft-44 `a31400bc…` byte-identical |
| 13 | No Stage-1A through Stage-1R historical artifact is modified | **PASS** — `git diff --name-only <base>` shows no `STAGE_01[A-R]_*` file; supersessions recorded in `STAGE_01S_SUPERSESSION_REGISTER.md` |

## Cross-document consistency

| Check | Result |
|-------|--------|
| Name always **PoCol**; mechanism only "the idle policy within PoCol" | **PASS** — 0 functional uses of any rebranded variant; the only corpus occurrences are pre-existing prohibition clauses inherited from the base; Stage-1S deliverables use zero literal forbidden strings |
| One transition-envelope object (pseudocode ↔ round SM ↔ terminology ↔ traceability) | **PASS** — §0.9 ↔ round SM §3.10 (S1) ↔ Stage-1S addendum ↔ R126 |
| Deferred branch-C atomicity (pseudocode ↔ round SM ↔ traceability) | **PASS** — §10a `CompleteSecurityRecovery`/`RecoveryAssignmentContinuationEvent` ↔ round SM §3.10/R13 (S2/S3) ↔ R127/R128 |
| Terminal recovery cleanup (pseudocode ↔ round SM ↔ terminology ↔ traceability) | **PASS** — §9/§17a/§20/§0.8 ↔ round SM §3.10 (S4) ↔ Stage-1S addendum ↔ R129 |
| One dirty-flag clearer + one epilogue (pseudocode ↔ catalogue ↔ terminology ↔ traceability) | **PASS** — §0.8a/§0.7d ↔ catalogue I17 (S5/S6) ↔ Stage-1S addendum ↔ R130/R131 |
| Explicit post-epilogue scheduling (pseudocode ↔ traceability) | **PASS** — §0.7e/§10a ↔ R132 (S7) |
| Call graph has no dangling calls | **PASS** — 68 defined; 0 called-but-undefined (`STAGE_01S_PROCEDURE_CALL_GRAPH.md`) |
| Traceability updated | **PASS** — R126–R133 (S1–S7 + TV143–TV152) added |
| A1 discipline | **PASS** — baseline `8.420833333 kWh` unchanged; S1–S7 are signature / atomicity / lifecycle / ownership / provenance corrections, never a change to how time or energy is counted |

## Supersession notes

All Stage-1S supersessions of Stage-1R (and earlier) statements are recorded in
`STAGE_01S_SUPERSESSION_REGISTER.md` (7 entries) — historical `STAGE_01[A-R]_*` files are NOT modified.

## Git delta

Modified (5, all un-suffixed normative): `STAGE_01_PROTOCOL_PSEUDOCODE.md`, `STAGE_01_ROUND_STATE_MACHINE.md`,
`STAGE_01_INVARIANT_CATALOGUE.md`, `STAGE_01_TERMINOLOGY.md`, `STAGE_01_TRACEABILITY_MATRIX.csv`. Added (12): the
`STAGE_01S_*` deliverables. No file outside `docs/thesis_revision_v45/stage_01/` is touched; no `STAGE_01[A-R]_*`
file is modified.

## Result

All thirteen acceptance gates pass and all cross-document consistency checks hold. The specification conforms to
S1–S7 while preserving B1–B9, C1–C10, D1–D9, E1–E10, F1–F9, G1–G11, H1–H9, I-01…I-08, J1–J9, K1–K8, L1–L6,
M1–M6, N1–N4, O1–O5, P1–P5, Q1–Q7, and R1–R6. Name remains PoCol; no new consensus feature; documentation only;
protected drafts byte-identical; Stage-1A–1R lettered artifacts frozen; A1 baseline unchanged. The prohibited
rebranded-algorithm-name variants are not used anywhere in this document.
