# Stage 1T — Procedure Call Graph

Extracted from `STAGE_01_PROTOCOL_PSEUDOCODE.md` (post-T1..T7). `→` is a direct `CALL`; `⇒` is a scheduled
discrete `event`. **Stage-1T change:** the former single-step `RecoveryAssignmentContinuationEvent` is REPLACED by
a TWO-step contract — the queued `RecoveryAssignmentContinuationDueEvent` (T1 step 1, records due + refreshes
census) and the post-epilogue hook `ApplyRecoveryAssignmentContinuationAfterEpilogue` (T1 step 2, the sole place
branch-C RESTORED is applied). **69 procedures/functions defined; 0 dangling** (net +1 vs Stage 1S: two added, one
removed). The name remains **PoCol**; the mechanism is **the idle policy within PoCol**; the A1 baseline
(`8.420833333 kWh`) is unchanged.

## New / changed edges (Stage 1T)

```
ProcessEventTime             → FinalizeEventTimeSecurityCensus, ApplyRecoveryCompletionAfterEpilogue,
                               ApplyRecoveryAssignmentContinuationAfterEpilogue,   # T1: continuation hook in the canonical tail
                               FinalizePostRecoveryApplicationState, CloseRoundAtHorizon
                               # T7: asserts no ordinary event AND no recovery-continuation application remains due at t
CompleteSecurityRecovery     ⇒ RecoveryAssignmentContinuationDueEvent             # T1/T2/S7: mints continuation identity; seats the DUE event (strictly-later)
CompleteSecurityRecovery     → RoundAbort(recovery_finalising=true), TransitionRoundState, ScheduleEvent(post_epilogue_context)
                                                                                  # branch C: seat-before-mutate -> DEFERRED (S2/S3/T1)
RecoveryAssignmentContinuationDueEvent → CaptureSecurityCensusOnRecoveryDeadline  # T1: records due + refreshes census; NO transition / assignment / APPLIED
ApplyRecoveryAssignmentContinuationAfterEpilogue → SetRecoveryDecisionStatus, CompleteAssignmentPhase,
                               ReserveActivate, RoundAbort(recovery_finalising=true), ScheduleEvent(post_epilogue_context)
                                                                                  # T1..T7: the ONLY place branch-C RESTORED is applied
ReconcilePendingRecoveryDecisions → SetRecoveryDecisionStatus                     # T2 rule B: advances continuation_bound_census_version; cancels a superseded continuation
CompleteAssignmentPhase      → (returns assignment_phase_completed | assignment_phase_failed(reason))   # T5: explicit disposition
CancelActiveRecoveryEpisode  → SetRecoveryDecisionStatus                          # S4/T1: cancels queued RecoveryAssignmentContinuationDueEvent on EQ
```

The remainder of the graph is unchanged from Stage 1S (see `STAGE_01S_PROCEDURE_CALL_GRAPH.md`): the run-level
driver `RunEventLoopToHorizon → {ProcessEventTime, FinalizeSimulationRun}`, the propagation / acceptance chain, the
single `ASSIGNMENT → HASHING` owner `CompleteAssignmentPhase`, the dirty-flag sole clearer `SettleSecurityCensusDirty`
(S5), the recovery-census versioning (`SecurityFloorEvaluate → {CommitRecoveryCensus,
ReconcilePendingRecoveryDecisions, SeatRecoveryCompletion}`), and the completion two-step
(`RecoveryCompletionDueEvent` + `ApplyRecoveryCompletionAfterEpilogue → CompleteSecurityRecovery`).

## Entry points

**Run-level drivers / hooks (NOT queued events):** `RunInitialise`, `RunEventLoopToHorizon`, `ProcessEventTime`
(sole event-loop driver), `CloseRoundAtHorizon`, `ApplyRecoveryCompletionAfterEpilogue` (post-epilogue completion),
`ApplyRecoveryAssignmentContinuationAfterEpilogue` (post-epilogue branch-C continuation, T1),
`FinalizePostRecoveryApplicationState` (post-application settlement), `FinalizeSimulationRun`. **Internal helpers
(not entry points):** `CommitSecurityCensus`, `SettleSecurityCensusDirty` (S5), `CommitRecoveryCensus`,
`ReconcilePendingRecoveryDecisions`, `SeatRecoveryCompletion`, `SetRecoveryDecisionStatus`,
`CancelActiveRecoveryEpisode` (S4), `CompleteSecurityRecovery`, `outcome_consistent_with_census`. **Queued driver
entry points / handlers (§0.7g-driver):** `RoundInitialise`, `TemplateCommit`, `PrepareParticipantsForNewRound`,
`MinerRegister`, `ReserveActivate`, `FullRangeExhaustNoSolution`, `RecoveryDeadlineEvent`,
`RecoveryCompletionDueEvent`, `RecoveryAssignmentContinuationDueEvent` (T1), `RoundAbort`, plus the ordinary
handlers.

## Required-property proofs

1. **No dangling calls.** Every called / scheduled name resolves to a defined procedure (69 defined; 0 undefined).
   A mechanical extraction reports only prose false positives — `is` (the "the CALL is not guarded" prose in §0.7d)
   and `this` (the "CALL this rather than …" prose in `CommitSecurityCensus`). The two new procedures introduce no
   dangling reference, and the removed `RecoveryAssignmentContinuationEvent` has no remaining live caller in the
   normative body.

2. **Continuation two-step (T1).** The only path to branch-C RESTORED being APPLIED is
   `ApplyRecoveryAssignmentContinuationAfterEpilogue` (a post-epilogue hook), reached after
   `RecoveryAssignmentContinuationDueEvent` recorded the due fact; `ProcessEventTime` invokes both post-epilogue
   hooks after the epilogue, and at most one applies per episode per event_time.

3. **Continuation version binding (T2).** `CompleteSecurityRecovery` mints the continuation identity;
   `ReconcilePendingRecoveryDecisions` (rule B) keeps `continuation_bound_census_version` current; the hook applies
   only when the ACTIVE generation matches and the bound version equals the latest `RecoveryCensusVersion`.

4. **Installation-phase invariant (T3).** The redistribution-only install is bracketed by
   `recovery_install_in_progress` / `RecoveryInstallID` / `active_recovery_install_decision`; every exit clears them
   and lands in exactly one of `HASHING`+`APPLIED`, `SECURITY_RECOVERY`+`APPLY_FAILED`,
   `ROUND_ABORTED`+`RECOVERY_INSTALL_FAILED_ABORTED`.

5. **No fabricated UNRECOVERABLE (T4).** The install-fail path calls `RoundAbort(recovery_install_failed_aborted)`
   and records `RECOVERY_INSTALL_FAILED_ABORTED` + `APPLY_FAILED_TERMINAL`; genuine `UNRECOVERABLE` remains solely
   `CompleteSecurityRecovery` branch D from a final-census breach.

6. **Assignment-phase disposition (T5).** `CompleteAssignmentPhase` returns `assignment_phase_completed |
   assignment_phase_failed(reason)`; the continuation hook branches on it (rollback vs APPLIED); both the ordinary
   and recovery callers of the single ASSIGNMENT→HASHING owner see the same disposition.

7. **Redistribution-only vs reserve-dependent (T6) & post-epilogue causality (T7).** The hook classifies the
   restoration; the reserve-dependent branch stays `SECURITY_RECOVERY` and re-arms a fresh-generation
   `RecoveryAssignmentContinuationDueEvent` strictly later via `PostEpilogueSchedulingContext`; `ProcessEventTime`
   asserts no recovery-continuation application remains due at `t`.

## Result

**PROCEDURE CALL GRAPH (Stage 1T): PASS** — all seven required properties hold; the two new procedures are correctly
wired; the removed single-step event has no live caller; the signature/disposition change to `CompleteAssignmentPhase`
has conforming call sites; no dangling reference exists (69 defined, 0 undefined). Documentation only; name remains
PoCol; A1 baseline `8.420833333 kWh` unchanged; the prohibited rebranded-algorithm-name variants are not used
anywhere in this document.
