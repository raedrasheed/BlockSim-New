# Stage 1T — Correction Report (continuation-epilogue & outcome-integrity lock)

This is a documentation-only scientific revision of the Stage-1 specification of **PoCol** with **the idle policy
within PoCol** enabled. It applies seven narrow corrections (T1–T7) to the security-recovery branch-C continuation:
they make the deferred branch-C application a two-step (Due-event + post-epilogue-hook) contract, bind the
continuation to a versioned identity, bracket its installation phase with explicit state and a three-way exit
invariant, forbid a fabricated `UNRECOVERABLE` outcome on install failure, give `CompleteAssignmentPhase` an
explicit reversible disposition, distinguish redistribution-only from reserve-dependent restoration, and extend the
post-epilogue causality contract to the continuation's own scheduling and finalisation assertion. No executable
source, configuration, DOCX, or PDF is changed; no experiment is run; no new consensus feature is introduced. The
algorithm name remains exactly **PoCol**; the mechanism is described only as **the idle policy within PoCol**; the
accepted A1 baseline (`8.420833333 kWh`) is unchanged — each correction is a control-flow / versioning / lifecycle /
provenance correction, never a change to how time or energy is counted. The prohibited rebranded-algorithm-name
variants are not used anywhere in this document.

## Corrections

### T1 — The branch-C continuation is a two-step contract (Due event + post-epilogue hook).

The former single-step `RecoveryAssignmentContinuationEvent` (whose queued handler transitioned the round and
installed the assignment set during the ordinary event drain) is REPLACED by a two-step contract mirroring the
completion application. Step 1 is the queued `RecoveryAssignmentContinuationDueEvent` (microphase
`RECOVERY_ASSIGNMENT_CONTINUATION_DUE`), which ONLY records the continuation-due fact
(`continuation_due_at_event_time`, `continuation_due_dispatch_envelope`) and refreshes the census via
`CaptureSecurityCensusOnRecoveryDeadline(..., census_source = RECOVERY_COMPLETION_DUE)` — it performs no round-state
transition, creates no assignment, and never marks the decision APPLIED. Step 2 is the post-epilogue hook
`ApplyRecoveryAssignmentContinuationAfterEpilogue`, the ONLY place branch-C RESTORED is applied. `ProcessEventTime`'s
canonical tail runs `FinalizeEventTimeSecurityCensus(t)` → `ApplyRecoveryCompletionAfterEpilogue(t)` →
`ApplyRecoveryAssignmentContinuationAfterEpilogue(t)` → `FinalizePostRecoveryApplicationState(t)`. At most one of the
completion hook and the continuation hook applies per `RecoveryEpisodeID` per `event_time`, so no branch-C RESTORED
result is recorded during the ordinary-event drain. (Pseudocode §0.7d/§0.7g/§10a; round SM §3.10 T1; catalogue I17;
terminology Stage-1T addendum; traceability R134; TV153/TV154.)

### T2 — Continuation version binding (RecoveryContinuationID / ContinuationGeneration).

Each branch-C continuation carries a `RecoveryContinuationID = (RecoveryDecisionID, ContinuationGeneration)`. The
immutable Due event carries ONLY the `ContinuationGeneration`; the authoritative bound census version is the
decision-record field `continuation_bound_census_version`, which `ReconcilePendingRecoveryDecisions` keeps current
(rule B: a re-affirmed DEFERRED decision's continuation bound version is advanced to the latest
`RecoveryCensusVersion`; a superseded decision's continuation Due event is cancelled). The post-epilogue hook applies
branch C ONLY when the ACTIVE generation matches (`ContinuationGeneration = D.continuation_generation`), the bound
version equals `latest_recovery_census[episode].RecoveryCensusVersion`, and the final census still warrants RESTORED
— otherwise a stale-noop. The carried version is not silently ignored; it is read from the authoritative record and
compared. (Pseudocode §0.8/§9/§10a; round SM §3.10 T2; catalogue I17; terminology Stage-1T addendum; traceability
R135; TV155/TV156/TV162.)

### T3 — Installation-phase state and three-way exit invariant.

The redistribution-only branch-C install is a synchronous sub-computation bracketed by three registries —
`recovery_install_in_progress`, `RecoveryInstallID = (episode, recovery_install_seq)`, and
`active_recovery_install_decision` — initialised in `RoundInitialise` (false / 0 / null). Because the install is
synchronous, no event boundary occurs within it, so no epilogue ever observes a transient
`ASSIGNMENT`-with-active-episode state. Every install exit clears the registries and lands in EXACTLY ONE of:
`HASHING` + decision `APPLIED`; `SECURITY_RECOVERY` + `APPLY_FAILED` (a reversible assignment-phase failure rolled
back, episode preserved); `ROUND_ABORTED` + `RECOVERY_INSTALL_FAILED_ABORTED` (an irreversible install failure that
closed the round via the declared recovery-finalising abort). This expanded invariant supersedes and reduces to the
plain S4 form `current_recovery_episode != null IFF round_state = SECURITY_RECOVERY`. (Pseudocode §0.8/§10a; round SM
§3.10 T3; catalogue I16; terminology Stage-1T addendum; traceability R136; TV157.)

### T4 — No fabricated UNRECOVERABLE on install failure.

An irreversible branch-C install failure after the `SECURITY_RECOVERY → ASSIGNMENT` transition is NEVER relabelled
as an `UNRECOVERABLE` floor outcome. It records its own `recovery_episode_disposition =
RECOVERY_INSTALL_FAILED_ABORTED`, marks the decision `APPLY_FAILED_TERMINAL`, leaves `recovery_outcome_finalised`
unset, and closes the round via `RoundAbort(reason = recovery_install_failed_aborted)`. Genuine `UNRECOVERABLE`
remains reserved for a FINAL census that still breaches the floor after the deadline (`CompleteSecurityRecovery`
branch D, O3/R14). `recovery_outcome_finalised[episode]` is set only on an actually-applied outcome — never on an
install-failed abort and never merely because a continuation was seated. This pairs with invariant I16 (breaches
recorded, never silently repaired). (Pseudocode §0.8/§10a; round SM §3.10 T4 + `RECOVERY_DECISION_STATUS` /
`RECOVERY_EPISODE_DISPOSITION` enums; catalogue I16; terminology Stage-1T addendum; traceability R137; TV158.)

### T5 — CompleteAssignmentPhase returns an explicit disposition.

`CompleteAssignmentPhase` returns an explicit disposition `assignment_phase_completed |
assignment_phase_failed(reason)` in place of an assertion-based contract. A malformed assignment set is caught BEFORE
the irreversible `HASHING` transition and returns `assignment_phase_failed(reason = malformed_assignment_set)` while
the round is still `ASSIGNMENT` (reversible); `assignment_phase_completed` means the round reached `HASHING`. The
branch-C continuation consumer rolls a failure back to `SECURITY_RECOVERY` (episode preserved) and marks the decision
APPLIED only on completion. Both the ordinary assignment caller and the recovery continuation caller of the single
ASSIGNMENT→HASHING owner (L2) branch on the same disposition. (Pseudocode `CompleteAssignmentPhase`/§10a; round SM
§3.10 T5; catalogue I16; terminology Stage-1T addendum; traceability R138; TV159.)

### T6 — Redistribution-only vs reserve-dependent restoration.

The post-epilogue continuation hook classifies the restoration. It is *redistribution-only* when the FINAL census
satisfies the floor using only currently `ACTIVE_HASHING` miners — installed synchronously (T3). Otherwise it is
*reserve-dependent*: the hook does not install; it activates the required reserve via `ReserveActivate` (whose
`StartWake` seats a `WakeCompleteEvent` strictly later through the post-epilogue context, T7), keeps the round in
`SECURITY_RECOVERY`, keeps the decision `APPLYING`, and re-arms a strictly-later continuation with a fresh
`continuation_generation`. Reserve-dependent RESTORED is applied only once a later final census confirms the floor
with the reserve `ACTIVE_HASHING` — a syntactically valid PENDING set is not restored hash rate. (Pseudocode §10a;
round SM §3.10 T6 + R13 row; catalogue I16; terminology Stage-1T addendum; traceability R139; TV160.)

### T7 — Post-epilogue continuation causality.

The continuation application runs strictly after the event-time epilogue; every `StartWake` and re-arm it seats is
placed at a strictly-later `event_time` through `PostEpilogueSchedulingContext`. `ProcessEventTime` asserts
`no recovery-continuation application remains due at t` (alongside the R1 `no ordinary event remains at t` and R2
`security_census_dirty[t] = false` assertions) before finalising `t`. (Pseudocode §0.7d/§10a; round SM §3.10 T7;
catalogue I17; terminology Stage-1T addendum; traceability R140; TV161.)

## Deliverables

| # | File | Content |
|--:|------|---------|
| 1 | `STAGE_01T_CORRECTION_REPORT.md` | this report (T1–T7) |
| 2 | `STAGE_01T_CONTINUATION_EPILOGUE_AUDIT.md` | T1/T7 two-step contract + canonical tail + mutual exclusion |
| 3 | `STAGE_01T_CONTINUATION_VERSION_AUDIT.md` | T2 continuation identity + version binding |
| 4 | `STAGE_01T_RECOVERY_INSTALLATION_STATE_AUDIT.md` | T3 install-phase state + three-way exit invariant |
| 5 | `STAGE_01T_OUTCOME_INTEGRITY_AUDIT.md` | T4 no fabricated UNRECOVERABLE + outcome-finalisation discipline |
| 6 | `STAGE_01T_ASSIGNMENT_PHASE_RESULT_AUDIT.md` | T5 `CompleteAssignmentPhase` disposition |
| 7 | `STAGE_01T_RESERVE_DEPENDENCY_AUDIT.md` | T6 redistribution-only vs reserve-dependent restoration |
| 8 | `STAGE_01T_PROCEDURE_CALL_GRAPH.md` | 69 defined, 0 dangling; new/changed edges |
| 9 | `STAGE_01T_SEMANTIC_TEST_VECTORS.md` | TV153–TV162 |
| 10 | `STAGE_01T_SUPERSESSION_REGISTER.md` | T-1…T-7 supersessions of Stage-1S (and earlier) |
| 11 | `STAGE_01T_CROSS_DOCUMENT_AUDIT.md` | thirteen acceptance gates + cross-document consistency |
| 12 | `STAGE_01T_CHECKSUM_MANIFEST.sha256` | sha256 of every Stage-1T deliverable + the five modified normative docs |

Normative documents updated (un-suffixed only): `STAGE_01_PROTOCOL_PSEUDOCODE.md`, `STAGE_01_ROUND_STATE_MACHINE.md`,
`STAGE_01_INVARIANT_CATALOGUE.md`, `STAGE_01_TERMINOLOGY.md`, `STAGE_01_TRACEABILITY_MATRIX.csv`. Historical
`STAGE_01A_*`…`STAGE_01S_*` lettered artifacts are unchanged.

## Result

The specification conforms to T1–T7 while preserving B1–B9, C1–C10, D1–D9, E1–E10, F1–F9, G1–G11, H1–H9,
I-01…I-08, J1–J9, K1–K8, L1–L6, M1–M6, N1–N4, O1–O5, P1–P5, Q1–Q7, R1–R6, and S1–S7. Name remains PoCol; no new
consensus feature; documentation only; protected drafts byte-identical; Stage-1A–1S lettered artifacts frozen; the
A1 baseline `8.420833333 kWh` is unchanged. The prohibited rebranded-algorithm-name variants are not used anywhere
in this document.
