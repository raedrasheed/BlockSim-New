# Stage 1R — Procedure Call Graph

Extracted from `STAGE_01_PROTOCOL_PSEUDOCODE.md` (post-R1..R6). `→` is a direct `CALL`; `⇒` is a scheduled
discrete `event`. **Stage-1R additions:** `RecoveryAssignmentContinuationEvent` (R1, the deferred branch-C
worker), `FinalizePostRecoveryApplicationState` (R2, the single post-application settlement), and
`SetRecoveryDecisionStatus` (R6, the sole decision-status mutator) are ADDED. **66 procedures/functions defined;
0 dangling** (net +3 vs Stage 1Q). The name remains **PoCol**; the mechanism is **the idle policy within PoCol**;
the A1 baseline (`8.420833333 kWh`) is unchanged.

## New / changed edges (Stage 1R)

```
ProcessEventTime             → FinalizeEventTimeSecurityCensus, ApplyRecoveryCompletionAfterEpilogue,
                               FinalizePostRecoveryApplicationState, CloseRoundAtHorizon
                                                                      # R2: one epilogue + apply + one settlement (§0.7d)
FinalizeEventTimeSecurityCensus → SecurityFloorEvaluate               # I-01 epilogue (unchanged; exactly once, R2)
ApplyRecoveryCompletionAfterEpilogue → SetRecoveryDecisionStatus, CompleteSecurityRecovery
                                                                      # R4: APPLYING -> (success) APPLIED / (fail) APPLY_FAILED
CompleteSecurityRecovery     → RoundAbort, TransitionRoundState, ScheduleEvent(RecoveryAssignmentContinuationEvent)
                                                                      # R4 dispositions; R1: branch C seats the continuation (never at t)
CompleteSecurityRecovery     ⇒ RecoveryAssignmentContinuationEvent    # R1: at next_representable_simulation_time(t) (> t)
RecoveryAssignmentContinuationEvent → ReserveActivate, CompleteAssignmentPhase
                                                                      # R1: branch-C assignment work at a STRICTLY-later event_time (§10a)
FinalizePostRecoveryApplicationState → CommitSecurityCensus           # R2/R5: stamp POST_RECOVERY_APPLICATION, then CLEAR dirty[t]
SetRecoveryDecisionStatus    → (leaf)                                 # R6: sets status + refreshes latest_recovery_decision mirror
ReconcilePendingRecoveryDecisions → SetRecoveryDecisionStatus         # R6: SUPERSEDED via the sole mutator
SeatRecoveryCompletion       → SetRecoveryDecisionStatus, ScheduleEvent(RecoveryCompletionDueEvent)
                                                                      # R6: SCHEDULED/SCHEDULE_FAILED/CANCELLED via the sole mutator
CommitSecurityCensus         → (leaf; owns security_census_write_seq_by_event_time)   # R5: explicit write ordinal; five sources
ApplyMinerStateTransition    → CommitSecurityCensus                   # R5: PRODUCER (MINER_STATE_TRANSITION); not a direct writer
CaptureSecurityCensusOnRecoveryDeadline → CommitSecurityCensus        # R5: RECOVERY_DEADLINE or RECOVERY_COMPLETION_DUE (census_source param)
RecoveryCompletionDueEvent   → CaptureSecurityCensusOnRecoveryDeadline # R5: census_source = RECOVERY_COMPLETION_DUE (§10a)
CloseRoundAtHorizon          → CloseRoundAssignments                  # R3: RUN_HOOK envelope (namespace + HorizonHookID) threaded onward
CloseRoundAssignments        → EnterLowPowerListen, ApplyMinerStateTransition   # R3: threads envelope_namespace + hook_id
EnterLowPowerListen          → ApplyMinerStateTransition              # R3: threads envelope_namespace + hook_id
```

The remainder of the graph is unchanged from Stage 1Q (see `STAGE_01Q_PROCEDURE_CALL_GRAPH.md`): the run-level
driver `RunEventLoopToHorizon → {ProcessEventTime, FinalizeSimulationRun}`, the propagation / acceptance chain,
the single `ASSIGNMENT → HASHING` owner `CompleteAssignmentPhase`, and the recovery-census versioning
(`SecurityFloorEvaluate → {CommitRecoveryCensus, ReconcilePendingRecoveryDecisions, SeatRecoveryCompletion}`).

## Entry points

**Run-level drivers / hooks (NOT queued events):** `RunInitialise` (Q5), `RunEventLoopToHorizon` (driver),
`ProcessEventTime` (sole event-loop driver), `CloseRoundAtHorizon` (§20b), `ApplyRecoveryCompletionAfterEpilogue`
(§10a, Q2/R4 — post-epilogue), `FinalizePostRecoveryApplicationState` (§10a, R2 — post-application settlement),
`FinalizeSimulationRun` (§20a). **Internal helpers (not entry points):** `CommitSecurityCensus`,
`CommitRecoveryCensus`, `ReconcilePendingRecoveryDecisions`, `SeatRecoveryCompletion`, `SetRecoveryDecisionStatus`,
`CompleteSecurityRecovery`, `outcome_consistent_with_census`. **Queued driver entry points / handlers
(§0.7g-driver):** `RoundInitialise`, `TemplateCommit`, `PrepareParticipantsForNewRound`, `MinerRegister`,
`ReserveActivate`, `FullRangeExhaustNoSolution`, `RecoveryDeadlineEvent`, `RecoveryCompletionDueEvent`,
`RecoveryAssignmentContinuationEvent` (R1), `RoundAbort`, plus the ordinary handlers (`WakeCompleteEvent`,
`HashWorkEvent`, `CertificateArrival`, `BlockAcceptancePoint`, `ResumeFromPause`, `LeaseExpiry`,
`ActiveHashRateUpdate`, `AdversarialParticipationChangeEvent`, `AcceptanceBatchFinalize`).

## Required-property proofs

1. **No dangling calls.** Every called / scheduled name resolves to a defined procedure (66 defined; 0
   undefined). A mechanical extraction reports only two false positives — `E` (the `SCHEDULE event E(...)`
   shorthand placeholder in §0.7e) and `this` (the prose "CALL this rather than writing the maps directly" in
   `CommitSecurityCensus`) — neither is a real call. The three new procedures introduce no dangling reference.

2. **No same-timestamp enqueue after the drain (R1).** The only post-epilogue paths that could enqueue are
   `ApplyRecoveryCompletionAfterEpilogue → CompleteSecurityRecovery`. Branch C `⇒ RecoveryAssignmentContinuationEvent`
   at `next_representable_simulation_time(t) > t`; branches A/B/D perform no enqueue at `t`. `ProcessEventTime`
   asserts no ordinary event remains at `t` before finalising it.

3. **One epilogue, one settlement (R2).** `ProcessEventTime` calls `FinalizeEventTimeSecurityCensus` at most once,
   then `ApplyRecoveryCompletionAfterEpilogue`, then `FinalizePostRecoveryApplicationState` (which does NOT call
   `SecurityFloorEvaluate`). The second `FinalizeEventTimeSecurityCensus` call is gone.

4. **Full transition envelope in the id (R3).** `ApplyMinerStateTransition` builds `TransitionEventID` with
   `envelope_namespace` + `hook_id` leading; the run-hook path threads `RUN_HOOK` + `HorizonHookID` end-to-end.

5. **Atomic application (R4).** The only path to `APPLIED` is `ApplyRecoveryCompletionAfterEpilogue` after
   `CompleteSecurityRecovery` returns `success`; a failed branch yields `APPLY_FAILED`; a terminal round yields
   `terminal_recovery_noop`.

6. **One census-write owner + consistent mirror (R5/R6).** `CommitSecurityCensus` is the sole writer and the sole
   owner of `security_census_write_seq_by_event_time`; `SetRecoveryDecisionStatus` is the sole status mutator and
   keeps `latest_recovery_decision` consistent.

## Result

**PROCEDURE CALL GRAPH (Stage 1R): PASS** — all six required reachability / causality properties hold; the three
new procedures are correctly wired; no dangling reference exists (66 defined, 0 undefined). Documentation only;
name remains PoCol; A1 baseline `8.420833333 kWh` unchanged; the prohibited rebranded-algorithm-name variants are
not used anywhere in this document.
