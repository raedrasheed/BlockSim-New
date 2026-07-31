# Stage 1T — Cross-Document Audit (acceptance gates)

The thirteen Stage-1T acceptance gates, verified by procedure-call-graph, signature/call-site, event-scheduling,
and corpus analysis over `docs/thesis_revision_v45/stage_01/` (not string search alone), plus cross-document
consistency and protected/historical-artifact verification. Name remains **PoCol**; mechanism is **the idle policy
within PoCol**; no property is claimed; the A1 baseline (`8.420833333 kWh`) is unchanged.

| # | Acceptance gate | Result |
|--:|-----------------|--------|
| 1 | The branch-C continuation is a two-step contract (Due event records; post-epilogue hook applies) | **PASS** — §10a `CompleteSecurityRecovery` branch C seats `RecoveryAssignmentContinuationDueEvent` (records due + refreshes census, NO transition/assignment/APPLIED); `ApplyRecoveryAssignmentContinuationAfterEpilogue` is the sole application site. `STAGE_01T_CONTINUATION_EPILOGUE_AUDIT.md`; TV153 |
| 2 | No branch-C RESTORED is applied during the ordinary drain; the two post-epilogue hooks are mutually exclusive per episode per event_time | **PASS** — §0.7d `ProcessEventTime` tail runs `FinalizeEventTimeSecurityCensus → ApplyRecoveryCompletionAfterEpilogue → ApplyRecoveryAssignmentContinuationAfterEpilogue → FinalizePostRecoveryApplicationState`; a completion applied at `t` clears the episode so the continuation hook then finds nothing due. `STAGE_01T_CONTINUATION_EPILOGUE_AUDIT.md`; TV154 |
| 3 | The continuation carries a versioned identity and applies only against the latest final census version | **PASS** — §0.8/§10a `RecoveryContinuationID = (RecoveryDecisionID, ContinuationGeneration)`; the Due event carries the generation, the authoritative `continuation_bound_census_version` (advanced by `ReconcilePendingRecoveryDecisions` rule B, §9) must equal `latest_recovery_census[episode].RecoveryCensusVersion`. `STAGE_01T_CONTINUATION_VERSION_AUDIT.md`; TV155/TV156/TV162 |
| 4 | The install phase has explicit state and a three-way exit invariant | **PASS** — §0.8/§10a `recovery_install_in_progress` / `RecoveryInstallID` / `active_recovery_install_decision` (init in `RoundInitialise`); every exit clears them and lands in `HASHING`+`APPLIED`, `SECURITY_RECOVERY`+`APPLY_FAILED`, or `ROUND_ABORTED`+`RECOVERY_INSTALL_FAILED_ABORTED`. `STAGE_01T_RECOVERY_INSTALLATION_STATE_AUDIT.md`; TV157 |
| 5 | No epilogue observes a transient ASSIGNMENT-with-active-episode state | **PASS** — §10a the redistribution-only install is a SYNCHRONOUS sub-computation with no event boundary within it; the T3 invariant supersedes/reduces to the S4 IFF form `current_recovery_episode != null IFF round_state = SECURITY_RECOVERY`. `STAGE_01T_RECOVERY_INSTALLATION_STATE_AUDIT.md`; TV157 |
| 6 | An install failure is never a fabricated UNRECOVERABLE | **PASS** — §10a an irreversible post-transition install failure records `recovery_episode_disposition = RECOVERY_INSTALL_FAILED_ABORTED`, status `APPLY_FAILED_TERMINAL`, and `RoundAbort(reason = recovery_install_failed_aborted)`; genuine UNRECOVERABLE stays `CompleteSecurityRecovery` branch D (O3/R14). `STAGE_01T_OUTCOME_INTEGRITY_AUDIT.md`; TV158 |
| 7 | `recovery_outcome_finalised` is set only on an actually-applied outcome | **PASS** — §10a set to RESTORED only when the continuation reaches HASHING, or to the branch-A/B/D outcome on SUCCESS; never on an install-failed abort, a reversible failure, or a mere seating. `STAGE_01T_OUTCOME_INTEGRITY_AUDIT.md`; TV158 |
| 8 | `CompleteAssignmentPhase` returns an explicit reversible disposition | **PASS** — `CompleteAssignmentPhase` returns `assignment_phase_completed \| assignment_phase_failed(reason)`; a malformed set is caught BEFORE the irreversible HASHING transition (round still ASSIGNMENT), which the continuation hook rolls back. `STAGE_01T_ASSIGNMENT_PHASE_RESULT_AUDIT.md`; TV159 |
| 9 | Redistribution-only and reserve-dependent restorations are distinguished; reserve-dependent never applies RESTORED before active-hash restoration | **PASS** — §10a the hook classifies on whether the FINAL census meets the floor with only `ACTIVE_HASHING` miners; the reserve-dependent branch stays `SECURITY_RECOVERY`, activates the reserve, and re-arms a fresh-generation continuation. `STAGE_01T_RESERVE_DEPENDENCY_AUDIT.md`; TV160 |
| 10 | Post-epilogue causality: strictly-later scheduling + the finalisation assertion | **PASS** — §10a every StartWake/re-arm is seated strictly later through `PostEpilogueSchedulingContext`; §0.7d `ProcessEventTime` asserts `no recovery-continuation application remains due at t`. `STAGE_01T_CONTINUATION_EPILOGUE_AUDIT.md`; TV161 |
| 11 | TV153 through TV162 pass on paper | **PASS** — `STAGE_01T_SEMANTIC_TEST_VECTORS.md`; every vector names exact procedures + preconditions with no assumed guard/transition; A1 preserved |
| 12 | No executable source/configuration/DOCX/PDF changes | **PASS** — `git diff` confined to `docs/thesis_revision_v45/stage_01/`; draft-42 `2c3afdc5…`, draft-44 `a31400bc…` byte-identical |
| 13 | No Stage-1A through Stage-1S historical artifact is modified | **PASS** — `git diff --name-only <base>` shows no `STAGE_01[A-S]_*` file; supersessions recorded in `STAGE_01T_SUPERSESSION_REGISTER.md` |

## Cross-document consistency

| Check | Result |
|-------|--------|
| Name always **PoCol**; mechanism only "the idle policy within PoCol" | **PASS** — 0 functional uses of any rebranded variant; the only corpus occurrences are pre-existing prohibition clauses inherited from the base; Stage-1T deliverables use zero literal forbidden strings |
| Continuation two-step (pseudocode ↔ round SM ↔ terminology ↔ traceability) | **PASS** — §0.7d/§0.7g/§10a ↔ round SM §3.10 (T1) ↔ Stage-1T addendum ↔ R134 |
| Continuation version binding (pseudocode ↔ round SM ↔ terminology ↔ traceability) | **PASS** — §0.8/§9/§10a ↔ round SM §3.10 (T2) ↔ Stage-1T addendum ↔ R135 |
| Install-phase state + exit invariant (pseudocode ↔ catalogue ↔ terminology ↔ traceability) | **PASS** — §0.8/§10a ↔ catalogue I16 (T3) ↔ Stage-1T addendum ↔ R136 |
| No fabricated UNRECOVERABLE (pseudocode ↔ round SM enums ↔ catalogue ↔ traceability) | **PASS** — §0.8/§10a ↔ round SM `RECOVERY_DECISION_STATUS`/`RECOVERY_EPISODE_DISPOSITION` (T4) ↔ catalogue I16 ↔ R137 |
| Assignment-phase disposition (pseudocode ↔ round SM ↔ terminology ↔ traceability) | **PASS** — `CompleteAssignmentPhase`/§10a ↔ round SM §3.10 (T5) ↔ Stage-1T addendum ↔ R138 |
| Redistribution-only vs reserve-dependent (pseudocode ↔ round SM R13 ↔ catalogue ↔ traceability) | **PASS** — §10a ↔ round SM §3.10/R13 (T6) ↔ catalogue I16 ↔ R139 |
| Post-epilogue causality (pseudocode ↔ catalogue ↔ traceability) | **PASS** — §0.7d/§10a ↔ catalogue I17 (T7) ↔ R140 |
| Call graph has no dangling calls | **PASS** — 69 defined; 0 called-but-undefined (`STAGE_01T_PROCEDURE_CALL_GRAPH.md`) |
| Traceability updated | **PASS** — R134–R141 (T1–T7 + TV153–TV162) added |
| A1 discipline | **PASS** — baseline `8.420833333 kWh` unchanged; T1–T7 are control-flow / versioning / lifecycle / provenance corrections, never a change to how time or energy is counted |

## Supersession notes

All Stage-1T supersessions of Stage-1S (and earlier) statements are recorded in
`STAGE_01T_SUPERSESSION_REGISTER.md` (7 entries) — historical `STAGE_01[A-S]_*` files are NOT modified; the
Stage-1R/1S terminology and traceability addenda describing the superseded single-step
`RecoveryAssignmentContinuationEvent` model are preserved as historical records.

## Git delta

Modified (5, all un-suffixed normative): `STAGE_01_PROTOCOL_PSEUDOCODE.md`, `STAGE_01_ROUND_STATE_MACHINE.md`,
`STAGE_01_INVARIANT_CATALOGUE.md`, `STAGE_01_TERMINOLOGY.md`, `STAGE_01_TRACEABILITY_MATRIX.csv`. Added (12): the
`STAGE_01T_*` deliverables. No file outside `docs/thesis_revision_v45/stage_01/` is touched; no `STAGE_01[A-S]_*`
file is modified.

## Result

All thirteen acceptance gates pass and all cross-document consistency checks hold. The specification conforms to
T1–T7 while preserving B1–B9, C1–C10, D1–D9, E1–E10, F1–F9, G1–G11, H1–H9, I-01…I-08, J1–J9, K1–K8, L1–L6,
M1–M6, N1–N4, O1–O5, P1–P5, Q1–Q7, R1–R6, and S1–S7. Name remains PoCol; no new consensus feature; documentation
only; protected drafts byte-identical; Stage-1A–1S lettered artifacts frozen; A1 baseline unchanged. The prohibited
rebranded-algorithm-name variants are not used anywhere in this document.
