# Stage 1Q — Procedure Call Graph

Extracted from `STAGE_01_PROTOCOL_PSEUDOCODE.md` (post-Q1..Q7). `→` is a direct `CALL`; `⇒` is a scheduled
discrete `event`. **Stage-1Q additions:** `CommitSecurityCensus` (Q4, the sole census writer),
`CommitRecoveryCensus` + `ReconcilePendingRecoveryDecisions` (Q1), `RecoveryCompletionDueEvent` +
`ApplyRecoveryCompletionAfterEpilogue` (Q2), and `RunInitialise` (Q5) are ADDED; `CompleteSecurityRecovery`
becomes an INTERNAL branch dispatch (no longer a queued event). **62 procedures defined; 0 dangling** (net +6
vs Stage 1P; `outcome_consistent_with_census` is a helper FUNCTION).

## New / changed edges (Stage 1Q)

```
RunInitialise                → (leaf)                                 # Q5: creates RunContext ONCE per run
RoundInitialise              → SettleResidencyBoundary                # Q5: now takes RunContext; per-round registries only
CommitSecurityCensus         → (leaf)                                 # Q4: SOLE atomic writer of latest_security_census + security_census_dirty
ApplyMinerStateTransition    → CommitSecurityCensus                   # Q4: census_source = MINER_STATE_TRANSITION
CaptureSecurityCensusOnApplicabilityEntry → CommitSecurityCensus       # Q4: census_source = APPLICABILITY_ENTRY
CaptureSecurityCensusOnRecoveryDeadline   → CommitSecurityCensus       # Q4: census_source = RECOVERY_DEADLINE
ProcessEventTime             → CloseRoundAtHorizon, FinalizeEventTimeSecurityCensus, ApplyRecoveryCompletionAfterEpilogue
                                                                      # O1/P1 horizon + I-02 epilogue + Q2 post-epilogue apply (bounded re-eval)
FinalizeEventTimeSecurityCensus → SecurityFloorEvaluate               # I-01 epilogue
SecurityFloorEvaluate        → CommitRecoveryCensus, ReconcilePendingRecoveryDecisions, SeatRecoveryCompletion
                                                                      # Q1: version + reconcile; then seat (if warranted)
SecurityFloorEvaluate        ⇒ RecoveryDeadlineEvent                  # O3: on ENTRY to SECURITY_RECOVERY (deadline <= T)
CommitRecoveryCensus         → (leaf)                                 # Q1: version + publish latest_recovery_census
ReconcilePendingRecoveryDecisions → (leaf; CANCEL due events on EQ)   # Q1/Q3: supersede-or-re-affirm
SeatRecoveryCompletion       ⇒ RecoveryCompletionDueEvent             # Q2/Q7: seat at deterministic target_time (<= T)
RecoveryDeadlineEvent        → CaptureSecurityCensusOnRecoveryDeadline # P3: record deadline fact + refresh census
RecoveryCompletionDueEvent   → CaptureSecurityCensusOnRecoveryDeadline # Q2: record due + refresh census; NO transition
ApplyRecoveryCompletionAfterEpilogue → CompleteSecurityRecovery        # Q2: apply ONLY if fresh + matches final census
CompleteSecurityRecovery     → TransitionRoundState, CompleteAssignmentPhase, RoundAbort   # INTERNAL branch dispatch (A/B/C/D)
CloseRoundAtHorizon          → CloseRoundAssignments                  # O1/Q6: tagged RUN_HOOK envelope; IN_PROGRESS/APPLIED replay state
```

The remainder of the graph is unchanged from Stage 1P (see `STAGE_01P_PROCEDURE_CALL_GRAPH.md`): the run-level
driver `RunEventLoopToHorizon → {ProcessEventTime, FinalizeSimulationRun}`, `FinalizeSimulationRun →
SettleResidencyBoundary`, the propagation/acceptance chain, and the single `ASSIGNMENT → HASHING` owner all
hold.

## Entry points

**Run-level drivers / hooks (NOT queued events):** `RunInitialise` (Q5, once per run), `RunEventLoopToHorizon`
(driver), `ProcessEventTime` (sole event-loop driver), `CloseRoundAtHorizon` (§20b),
`ApplyRecoveryCompletionAfterEpilogue` (§10a, Q2 — post-epilogue), `FinalizeSimulationRun` (§20a). **Internal
helpers (not entry points):** `CommitSecurityCensus`, `CommitRecoveryCensus`,
`ReconcilePendingRecoveryDecisions`, `SeatRecoveryCompletion`, `CompleteSecurityRecovery`,
`outcome_consistent_with_census`. **Queued driver entry points / handlers (§0.7g-driver):** `RoundInitialise`,
`TemplateCommit`, `PrepareParticipantsForNewRound`, `MinerRegister`, `ReserveActivate`,
`FullRangeExhaustNoSolution`, `RecoveryDeadlineEvent`, `RecoveryCompletionDueEvent`, `RoundAbort`, plus the
ordinary handlers (`WakeCompleteEvent`, `HashWorkEvent`, `CertificateArrival`, `BlockAcceptancePoint`,
`ResumeFromPause`, `LeaseExpiry`, `ActiveHashRateUpdate`, `AdversarialParticipationChangeEvent`,
`AcceptanceBatchFinalize`).

## Required-property proofs

1. **No dangling calls.** Every called/scheduled name resolves to a defined procedure (62 defined; 0
   undefined). The six new procedures introduce no dangling reference.

2. **One census writer (Q4).** `CommitSecurityCensus` (leaf) is the ONLY procedure that writes
   `latest_security_census`/`security_census_dirty`; its three callers pass distinct `census_source` values.

3. **Versioned census + reconcile (Q1).** `SecurityFloorEvaluate → {CommitRecoveryCensus,
   ReconcilePendingRecoveryDecisions}` runs on every final recovery census; a contradicted pending decision is
   superseded, a consistent one re-affirmed to the latest version.

4. **Apply after the epilogue (Q2).** `RecoveryCompletionDueEvent` does NOT `⇒ CompleteSecurityRecovery`; the
   only path to the branch dispatch is `ProcessEventTime → ApplyRecoveryCompletionAfterEpilogue →
   CompleteSecurityRecovery`, run AFTER `FinalizeEventTimeSecurityCensus(t)`.

5. **Atomic supersession (Q3).** `ReconcilePendingRecoveryDecisions` supersedes + cancels before
   `SeatRecoveryCompletion` seats a replacement; `pending_recovery_decisions` is a set of explicit
   `RecoveryDecisionID`s with a `RECOVERY_DECISION_STATUS`.

6. **Explicit ownership (Q5) + tagged hook (Q6) + deterministic time (Q7).** `RunInitialise` owns per-run
   fields; `RoundInitialise` returns the per-round recovery registries; `CloseRoundAtHorizon` uses a `RUN_HOOK`
   envelope with an IN_PROGRESS/APPLIED replay state; `SeatRecoveryCompletion` uses
   `configured_recovery_completion_delay` (`> 0`).

## Result

**PROCEDURE CALL GRAPH (Stage 1Q): PASS** — all six required reachability properties hold; the six new
procedures are correctly wired; `CommitSecurityCensus` is the sole census writer; the recovery outcome is
applied only by the post-epilogue hook; no dangling reference exists (62 defined, 0 undefined). Documentation
only; name remains PoCol; A1 baseline `8.420833333 kWh` unchanged; the prohibited rebranded-algorithm-name
variants are not used anywhere in this document.
