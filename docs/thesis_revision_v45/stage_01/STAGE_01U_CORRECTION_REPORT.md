# Stage 1U — Correction Report (reserve-recovery & continuation-liveness lock)

This is a documentation-only scientific revision of the Stage-1 specification of **PoCol** with **the idle policy
within PoCol** enabled. It applies seven narrow corrections (U1–U7) to the security-recovery machinery: it separates
recovery WORK from the RESTORED outcome (removing a logically impossible reserve-dependent continuation), threads an
explicit post-epilogue scheduling context through the full wake path, makes every re-arm atomic, makes the
continuation/work due fact explicitly consumed, replaces the opaque install/undo macros with named
prepare/commit/rollback procedures, makes every `CompleteAssignmentPhase` caller handle its disposition, and gives the
continuation-due census checkpoint a distinct provenance. No executable source, configuration, DOCX, or PDF is
changed; no experiment is run; no new consensus feature is introduced. The algorithm name remains exactly **PoCol**;
the mechanism is described only as **the idle policy within PoCol**; the accepted A1 baseline (`8.420833333 kWh`) is
unchanged — each correction is a control-flow / scheduling / lifecycle / provenance correction, never a change to how
time or energy is counted. The prohibited rebranded-algorithm-name variants are not used anywhere in this document.

## Corrections

### U1 — Separate recovery WORK from the RESTORED outcome.

The Stage-1T reserve-dependent `RESTORED` continuation was unreachable: `RESTORED` requires `census.breach = false`
(`outcome_consistent_with_census` is NOT weakened), while a reserve-dependent restoration presupposes the current
`ACTIVE_HASHING` census still breaches the floor. The recovery OUTCOME (`RESTORED`/`UNRECOVERABLE`) is now decided
ONLY from a final census; reserve activation / redistribution attempted while the floor is still breached is a
recovery-WORK action (`RECOVERY_WORK_ACTION` in {`RESERVE_ACTIVATION_REQUIRED`, `RANGE_REDISTRIBUTION_REQUIRED`,
`NONE`}), never a `RecoveryOutcome` and never marked `APPLIED` as `RESTORED`. The breach-before-deadline epilogue
classifies the work (`ClassifyRecoveryWork`) and seats ONE versioned `RecoveryWorkDueEvent` (`SeatRecoveryWork`); the
post-epilogue hook `ApplyRecoveryWorkAfterEpilogue` performs it while the round stays `SECURITY_RECOVERY`; a later
no-breach final census mints `RESTORED`. The impossible reserve-dependent ELSE is removed and branch C is now
REDISTRIBUTION-ONLY. (Pseudocode §9/§9c/§10a; round SM §3.10 U1 + R13; catalogue I16; terminology Stage-1U addendum;
traceability R142; TV163.)

### U2 — Thread PostEpilogueSchedulingContext through the full wake path.

`ReserveActivate`, `RangeReassign`, `RangeAssign`, `StartWake`, and `CommitRecoveryAssignmentPlan` take an explicit
`scheduling_context` (`SchedulingSourceContext` in {`ORDINARY_DISPATCH(dispatch_envelope)`,
`POST_EPILOGUE(PostEpilogueSchedulingContext)`}). A post-epilogue caller threads the `pctx` all the way to
`ScheduleEvent`; a positive-latency post-epilogue wake targets `source + latency`, a zero-latency wake targets
`next_representable_simulation_time(source)`, and `target_event_time > source_event_time` always. No procedure creates
a `pctx` and then schedules using only the ordinary dispatch envelope. (Pseudocode §0.8/§9c/§10a; round SM §3.10 U2;
catalogue I17; terminology Stage-1U addendum; traceability R143; TV164; `STAGE_01U_PROCEDURE_SIGNATURE_CALL_AUDIT.md`.)

### U3 — Atomic re-arm.

A seat / re-arm (`SeatRecoveryWork`) advances the active identity ONLY after `ScheduleEvent` succeeds: compute the
candidate identity + target, validate `<= T` (else a horizon-deferred disposition, no enqueue), schedule without
mutating the active identity, and publish (`status = ARMED`, event ref, controller) only on success. A rejection
advances nothing, publishes no false reference, reports no `reserve_pending` state, and records an explicit
disposition. No `APPLYING` decision is left without a live event, a controller (`pending_recovery_work`), or an
explicit terminal/horizon disposition — a branch-C `APPLYING` decision is always resolved in one continuation-hook
invocation. (Pseudocode §9c/§10a; round SM §3.10 U3; catalogue I17; terminology Stage-1U addendum; traceability R144;
TV165/TV167.)

### U4 — Explicitly consume the continuation due fact.

A `CONTINUATION_DUE_STATUS` ({`NOT_DUE`, `DUE`, `CONSUMED`, `SUPERSEDED`, `CANCELLED`}) is added to the continuation
record and every recovery-work record. `RecoveryAssignmentContinuationDueEvent` / `RecoveryWorkDueEvent` set `DUE`;
the post-epilogue hook ATOMICALLY consumes it (`CONSUMED` on apply/settle, `SUPERSEDED` on a stale-noop, `CANCELLED`
on terminal closure) before returning; `ProcessEventTime`'s finalisation assertion checks the EXPLICIT status, not a
timestamp field. (Pseudocode §0.8/§0.7d/§9c/§10a; round SM §3.10 U4; catalogue I17; terminology Stage-1U addendum;
traceability R145; TV166.)

### U5 — Replace INSTALL/UNDO macros with named executable procedures.

The opaque `INSTALL the disjoint assignment set` / `UNDO the partial install` macros are replaced by
`PrepareRecoveryAssignmentPlan` (compute-only; returns a deterministic plan; verifies I1/I3/I10/I18b before any
mutation), `CommitRecoveryAssignmentPlan` (receives the explicit `scheduling_context`; creates assignments in stable
order; returns `install_committed` / `install_failed_before_mutation` / `install_failed_after_mutation(reason,
rollback_record)`), and `RollbackRecoveryAssignmentPlan` (cancels every plan event, closes every plan-created live
head legally, restores the ledgers, leaves no live partial assignment; `rollback_completed` / `rollback_failed`). A
rollback that fails after mutation takes the declared `RECOVERY_INSTALL_FAILED_ABORTED` + `RoundAbort` — never a
fabricated `UNRECOVERABLE`. (Pseudocode §0.8/§9c/§10a; round SM §3.10 U5; catalogue I16; terminology Stage-1U
addendum; traceability R146; TV168/TV169/TV170.)

### U6 — Handle CompleteAssignmentPhase at every call site.

All three `CompleteAssignmentPhase` callers — `PrepareParticipantsForNewRound`, `TemplateRefresh`, and the recovery
installation — capture and branch on `assignment_phase_completed | assignment_phase_failed(reason)`. A pre-`HASHING`
failure rolls back the just-created assignments/wakes and takes the declared setup/refresh failure path
(`participant_set_setup_failed` / `template_refresh_failed`); no caller returns success while the round remains
`ASSIGNMENT`. (Pseudocode §2/§19/§10a; round SM §3.10 U6; catalogue I16; terminology Stage-1U addendum; traceability
R147; TV171/TV172.)

### U7 — Continuation-due census provenance.

A distinct census source `RECOVERY_CONTINUATION_DUE` is added; `RecoveryAssignmentContinuationDueEvent` uses it (not
`RECOVERY_COMPLETION_DUE`), and `RecoveryWorkDueEvent` uses `RECOVERY_WORK_DUE`. `CommitSecurityCensus` now has seven
named sources, so "completion is due", "continuation is due", "recovery work is due", and "deadline reached" are
distinguishable provenances. (Pseudocode §0.8/§9a/§9c/§10a; round SM §3.10 U7; catalogue I17; terminology Stage-1U
addendum; traceability R148; TV173.)

## Deliverables

| # | File | Content |
|--:|------|---------|
| 1 | `STAGE_01U_CORRECTION_REPORT.md` | this report (U1–U7) |
| 2 | `STAGE_01U_RECOVERY_WORK_OUTCOME_SEPARATION_AUDIT.md` | U1 recovery WORK vs RESTORED outcome |
| 3 | `STAGE_01U_POST_EPILOGUE_CONTEXT_THREADING_AUDIT.md` | U2 scheduling-context threading |
| 4 | `STAGE_01U_CONTINUATION_REARM_LIVENESS_AUDIT.md` | U3 atomic re-arm + liveness |
| 5 | `STAGE_01U_CONTINUATION_DUE_CONSUMPTION_AUDIT.md` | U4 explicit due-fact consumption |
| 6 | `STAGE_01U_RECOVERY_INSTALL_TRANSACTION_AUDIT.md` | U5 prepare/commit/rollback |
| 7 | `STAGE_01U_ASSIGNMENT_PHASE_CALLER_AUDIT.md` | U6 disposition at every caller |
| 8 | `STAGE_01U_CENSUS_PROVENANCE_AUDIT.md` | U7 distinct census provenance |
| 9 | `STAGE_01U_PROCEDURE_SIGNATURE_CALL_AUDIT.md` | signature/call-site + post-epilogue threading |
| 10 | `STAGE_01U_PROCEDURE_CALL_GRAPH.md` | 76 defined, 0 dangling; new/changed edges |
| 11 | `STAGE_01U_SEMANTIC_TEST_VECTORS.md` | TV163–TV173 |
| 12 | `STAGE_01U_SUPERSESSION_REGISTER.md` | U-1…U-7 supersessions of Stage-1T (and earlier) |
| 13 | `STAGE_01U_CROSS_DOCUMENT_AUDIT.md` | fifteen acceptance gates + cross-document consistency |
| 14 | `STAGE_01U_CHECKSUM_MANIFEST.sha256` | sha256 of every Stage-1U deliverable + the four modified normative docs |

Normative documents updated (un-suffixed only): `STAGE_01_PROTOCOL_PSEUDOCODE.md`, `STAGE_01_ROUND_STATE_MACHINE.md`,
`STAGE_01_INVARIANT_CATALOGUE.md`, `STAGE_01_TERMINOLOGY.md`, `STAGE_01_TRACEABILITY_MATRIX.csv`. Historical
`STAGE_01A_*`…`STAGE_01T_*` lettered artifacts are unchanged.

## Result

The specification conforms to U1–U7 while preserving B1–B9, C1–C10, D1–D9, E1–E10, F1–F9, G1–G11, H1–H9, I-01…I-08,
J1–J9, K1–K8, L1–L6, M1–M6, N1–N4, O1–O5, P1–P5, Q1–Q7, R1–R6, S1–S7, and T1–T7. Name remains PoCol; no new consensus
feature; documentation only; protected drafts byte-identical; Stage-1A–1T lettered artifacts frozen; the A1 baseline
`8.420833333 kWh` is unchanged. The prohibited rebranded-algorithm-name variants are not used anywhere in this
document.
