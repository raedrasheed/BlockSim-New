# Stage 1S — Procedure Call Graph

Extracted from `STAGE_01_PROTOCOL_PSEUDOCODE.md` (post-S1..S7). `→` is a direct `CALL`; `⇒` is a scheduled
discrete `event`. **Stage-1S additions:** `SettleSecurityCensusDirty` (S5, the sole dirty-flag clearer) and
`CancelActiveRecoveryEpisode` (S4, the terminal recovery cleanup) are ADDED. **68 procedures/functions defined; 0
dangling** (net +2 vs Stage 1R). The name remains **PoCol**; the mechanism is **the idle policy within PoCol**;
the A1 baseline (`8.420833333 kWh`) is unchanged.

## New / changed edges (Stage 1S)

```
ProcessEventTime             → FinalizeEventTimeSecurityCensus (UNCONDITIONAL, S6), ApplyRecoveryCompletionAfterEpilogue,
                               FinalizePostRecoveryApplicationState, CloseRoundAtHorizon
FinalizeEventTimeSecurityCensus → SecurityFloorEvaluate, SettleSecurityCensusDirty(PRIMARY_EPILOGUE)   # S5
FinalizePostRecoveryApplicationState → CommitSecurityCensus, SettleSecurityCensusDirty(POST_RECOVERY_APPLICATION)  # S5
SettleSecurityCensusDirty    → (leaf)                                 # S5: the SOLE clearer of security_census_dirty
ApplyMinerStateTransition    → CommitSecurityCensus                   # S1: takes ONE transition_envelope object; id built from it
ApplyRecoveryCompletionAfterEpilogue → SetRecoveryDecisionStatus, CompleteSecurityRecovery
                                                                      # S3: branch on disposition.kind SUCCESS|DEFERRED|FAILED
CompleteSecurityRecovery     → RoundAbort(recovery_finalising=true), TransitionRoundState, ScheduleEvent(post_epilogue_context)
                                                                      # S2/S3/S7: branch C seats-before-mutate -> DEFERRED
CompleteSecurityRecovery     ⇒ RecoveryAssignmentContinuationEvent    # S2/S7: via PostEpilogueSchedulingContext (strictly-later)
RecoveryAssignmentContinuationEvent → SetRecoveryDecisionStatus, ReserveActivate, CompleteAssignmentPhase, RoundAbort(recovery_finalising=true)
                                                                      # S3: verify -> ASSIGNMENT -> install -> HASHING -> APPLIED
ReconcilePendingRecoveryDecisions → SetRecoveryDecisionStatus         # S3: also CANCELs a superseded decision's continuation_event_ref on EQ
CloseRoundAssignments        → EnterLowPowerListen, ApplyMinerStateTransition, CancelActiveRecoveryEpisode
                                                                      # S4: terminal cleanup unless recovery_finalising
CancelActiveRecoveryEpisode  → SetRecoveryDecisionStatus              # S4: cancel pending/applying decisions; CANCEL due/continuation refs on EQ
RoundAbort                   → CloseRoundAssignments(recovery_finalising)   # S4: threads the finalising-abort flag
```

The remainder of the graph is unchanged from Stage 1R (see `STAGE_01R_PROCEDURE_CALL_GRAPH.md`): the run-level
driver `RunEventLoopToHorizon → {ProcessEventTime, FinalizeSimulationRun}`, the propagation / acceptance chain,
the single `ASSIGNMENT → HASHING` owner `CompleteAssignmentPhase`, and the recovery-census versioning
(`SecurityFloorEvaluate → {CommitRecoveryCensus, ReconcilePendingRecoveryDecisions, SeatRecoveryCompletion}`).

## Entry points

**Run-level drivers / hooks (NOT queued events):** `RunInitialise`, `RunEventLoopToHorizon`, `ProcessEventTime`
(sole event-loop driver), `CloseRoundAtHorizon`, `ApplyRecoveryCompletionAfterEpilogue` (post-epilogue),
`FinalizePostRecoveryApplicationState` (post-application settlement), `FinalizeSimulationRun`. **Internal helpers
(not entry points):** `CommitSecurityCensus`, `SettleSecurityCensusDirty` (S5), `CommitRecoveryCensus`,
`ReconcilePendingRecoveryDecisions`, `SeatRecoveryCompletion`, `SetRecoveryDecisionStatus`,
`CancelActiveRecoveryEpisode` (S4), `CompleteSecurityRecovery`, `outcome_consistent_with_census`. **Queued driver
entry points / handlers (§0.7g-driver):** `RoundInitialise`, `TemplateCommit`, `PrepareParticipantsForNewRound`,
`MinerRegister`, `ReserveActivate`, `FullRangeExhaustNoSolution`, `RecoveryDeadlineEvent`,
`RecoveryCompletionDueEvent`, `RecoveryAssignmentContinuationEvent`, `RoundAbort`, plus the ordinary handlers.

## Required-property proofs

1. **No dangling calls.** Every called / scheduled name resolves to a defined procedure (68 defined; 0 undefined).
   A mechanical extraction reports only prose false positives — `E` (the `SCHEDULE event E(...)` shorthand), `this`
   (the "CALL this rather than …" prose in `CommitSecurityCensus`), and `is` (the "the CALL is not guarded" prose
   in §0.7d). The two new procedures introduce no dangling reference.

2. **One transition-envelope object (S1).** `ApplyMinerStateTransition` receives one `transition_envelope`; all 14
   call sites pass `transition_envelope = dispatch_envelope`; the id is built from that object plus transition fields.

3. **Deferred branch-C atomicity (S2/S3).** The only path to branch-C RESTORED being APPLIED is
   `RecoveryAssignmentContinuationEvent` reaching HASHING; `CompleteSecurityRecovery` branch C returns DEFERRED
   after a successful seat (round stays SECURITY_RECOVERY) and FAILED otherwise.

4. **Terminal cleanup (S4).** `CloseRoundAssignments → CancelActiveRecoveryEpisode` fires for every terminal
   closure except the recovery-finalising abort (recovery_finalising = true); the cleanup clears the active episode.

5. **One dirty-flag clearer (S5) + one epilogue (S6).** `SettleSecurityCensusDirty` is the ONLY procedure clearing
   `security_census_dirty`; `ProcessEventTime` calls `FinalizeEventTimeSecurityCensus` once and unconditionally.

6. **Explicit post-epilogue scheduling (S7).** The branch-C continuation seat is the sole `ScheduleEvent` call
   carrying a `PostEpilogueSchedulingContext`; ScheduleEvent enforces `target_event_time > source_event_time`.

## Result

**PROCEDURE CALL GRAPH (Stage 1S): PASS** — all six required properties hold; the two new procedures are correctly
wired; the signature changes (`ApplyMinerStateTransition`, `CompleteSecurityRecovery`, `RoundAbort`,
`CloseRoundAssignments`, `ScheduleEvent`) have conforming call sites; no dangling reference exists (68 defined, 0
undefined). Documentation only; name remains PoCol; A1 baseline `8.420833333 kWh` unchanged; the prohibited
rebranded-algorithm-name variants are not used anywhere in this document.
