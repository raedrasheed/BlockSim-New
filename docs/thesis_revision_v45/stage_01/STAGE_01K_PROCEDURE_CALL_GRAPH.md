# Stage 1K — Procedure Call Graph

Extracted from `STAGE_01_PROTOCOL_PSEUDOCODE.md` (post-K1..K8). `→` is a direct `CALL`; `⇒` is a
scheduled discrete `event` (every `⇒`/`SCHEDULE` is shorthand for a `ScheduleEvent` call, J9/K8). **New
Stage-1K procedures:** `CompleteAssignmentPhase` (K2), `FinalizeRoundResidency` and `BeginRoundResidency`
(K3), `CaptureSecurityCensusOnApplicabilityEntry` (K7). No procedure was removed. 49 procedures defined;
0 dangling.

## Direct-call (→) and scheduled-event (⇒) edges

```
ProcessEventTime                   → FinalizeEventTimeSecurityCensus, ScheduleEvent   # I-02 driver
RoundInitialise                    → FinalizeRoundResidency, BeginRoundResidency       # K3 cross-round rebase (subsequent round)
TemplateCommit                     (leaf)
PrepareParticipantsForNewRound     → CreatePendingAssignment, StartWake, CompleteAssignmentPhase   # K1/K2 (T3/T4/T10 then R4)
CompleteAssignmentPhase            → CaptureSecurityCensusOnApplicabilityEntry          # K2 (ASSIGNMENT->HASHING) + K7
CaptureSecurityCensusOnApplicabilityEntry  (leaf; SECOND coherent census writer — K7)
FinalizeRoundResidency             (leaf; closes old-round intervals — K3)
BeginRoundResidency                (leaf; reopens same state at boundary_time — K3)
ScheduleEvent                      (leaf; SOLE enqueue interface over EventQueueContext; derives delta_cycle — J9/K8)
FinalizeEventTimeSecurityCensus    → SecurityFloorEvaluate                              # I-01 epilogue
SecurityFloorEvaluate              (leaf; terminal-first + stale guard + J6 applicability + I-05 recovery)
MinerRegister                      → ApplyMinerStateTransition                          # T1/T2 (DriverEventEnvelope — K4)
RangeAssign                        → CreatePendingAssignment, StartWake                 # F4/F5
StartHashing                       → ScheduleNextHashWork                               # G9
ScheduleNextHashWork               ⇒ HashWorkEvent                                      # G9
HashWorkEvent                      → ActualRangeCompletion, CreateSolutionEligibilitySnapshot, EarlyStopGenerate,
                                     ExhaustionAdjudicate, ProgressCommit, ReportedExhaustionClaim,
                                     ScheduleNextHashWork, ScheduleSolutionPropagation  # no-op while ASSIGNMENT (K2)
ActualRangeCompletion / ReportedExhaustionClaim / ProgressCommit / CreateSolutionEligibilitySnapshot / EarlyStopGenerate  (leaves)
ExhaustionAdjudicate               → ApplyMinerStateTransition                          # T7
EnterLowPowerListen                → ApplyMinerStateTransition                          # T8/T26/T27/T28/T29; custody_on_close/termination_reason (K6)
ActiveHashRateUpdate               (leaf; COMPUTE-ONLY — G3)
AdversarialParticipationChangeEvent→ ApplyMinerStateTransition, RangeAssign, CreatePendingAssignment,
                                     StartWake, ResumeFromPause   # I-06
ReserveActivate                    → CreatePendingAssignment, StartWake                 # F4/F5
StartWake                          → ApplyMinerStateTransition   ⇒ WakeCompleteEvent    # F5/F6
WakeCompleteEvent                  → ApplyMinerStateTransition, StartHashing            # F5/F6/G9
ApplyMinerStateTransition          (leaf; SOLE miner_state writer + residency owner; K5 register-only-applied;
                                     J1/K7 coherent census writer; K4 full envelope)
CreatePendingAssignment            (leaf; ORIGINAL/REASSIGNED only — G2)
LeaseExpiry                        → RenewAssignment, EnterLowPowerListen, RangeReassign # E9; K6 canonical CLOSE via EnterLowPowerListen
RenewAssignment                    (leaf; sole renewal path; SUPERSEDED renewal-only — J7)
RangeReassign                      → CreatePendingAssignment, StartWake                 # F4/F5
SelfValidateFoundSolution          → ValidateCandidate                                  # E2
CreatePropagationContext           (leaf; DISCOVERED — G6/G7)
ScheduleSolutionPropagation        → CreatePropagationContext, SelfValidateFoundSolution, EnterLowPowerListen,
                                     CaptureSecurityCensusOnApplicabilityEntry   ⇒ CertificateArrival, BlockAcceptancePoint   # K7 on SOLUTION_PROPAGATION entry
CertificateArrival                 → EarlyStopVerify
EarlyStopVerify                    → ValidateCandidate, EnterLowPowerListen
ResumeFromPause                    → StartWake                                          # F2/F5 (T30)
BlockAcceptancePoint               (leaf; REGISTER-ONLY — G5)
ValidateCandidate                  (leaf; discovery-time predicate — G1/I2)
AcceptanceBatchFinalize            → ValidateCandidate, ValidBlockAccept, HandlePropagationFailure   # G5
HandlePropagationFailure           ⇒ ResumeFromPause   # F2/G11; sets NO security_census_dirty (J1)
ValidBlockAccept                   → CloseRoundAssignments                              # F3/G8
CloseRoundAssignments              → EnterLowPowerListen, ApplyMinerStateTransition     # E7/F6
CloseTemplateAssignments           → EnterLowPowerListen, ApplyMinerStateTransition     # E8/F6
FullRangeExhaustNoSolution         → TemplateRefresh, RoundAbort
TemplateRefresh                    → CloseTemplateAssignments, TemplateCommit, CreatePendingAssignment, StartWake
RoundAbort                         → CloseRoundAssignments                              # G8
```

## Entry points (dispatched by the loop / sim driver)

`ProcessEventTime` (I-02 driver), `RoundInitialise`, `TemplateCommit`, `PrepareParticipantsForNewRound`
(ASSIGNMENT phase, K1/K2), `MinerRegister`, `ReserveActivate`, `LeaseExpiry`, `FullRangeExhaustNoSolution`,
`ActiveHashRateUpdate`, `AdversarialParticipationChangeEvent`, `AcceptanceBatchFinalize`. Queued handlers
(`WakeCompleteEvent`, `HashWorkEvent`, `CertificateArrival`, `BlockAcceptancePoint`, `ResumeFromPause`)
are enqueued via `ScheduleEvent` and dispatched by `ProcessEventTime`.

## Required-property proofs

1. **No dangling calls.** Every called/scheduled name resolves to a defined procedure (49 defined; 0
   called-but-undefined). The four new procedures introduce no dangling reference.

2. **Executable next-round handoff (K1/K2).** `PrepareParticipantsForNewRound → {CreatePendingAssignment,
   StartWake, CompleteAssignmentPhase}`; `CompleteAssignmentPhase` performs the ASSIGNMENT→HASHING
   transition (R4) and `→ CaptureSecurityCensusOnApplicabilityEntry`. No `HashWorkEvent` executes while
   the round is `ASSIGNMENT` (guard no-op).

3. **Cross-round residency rebase (K3).** `RoundInitialise → {FinalizeRoundResidency, BeginRoundResidency}`
   at the boundary; these are the ONLY no-state-change residency close/reopen; `ApplyMinerStateTransition`
   remains the sole owner for actual state changes.

4. **Two coherent census writers (K7/J1).** `SecurityFloorEvaluate` is reached only via
   `FinalizeEventTimeSecurityCensus` (epilogue). The census `dirty`/`latest` maps are written only by
   `ApplyMinerStateTransition` (miner boundary) and `CaptureSecurityCensusOnApplicabilityEntry`
   (applicability entry, reached from `CompleteAssignmentPhase` and `ScheduleSolutionPropagation`), each
   writing both together.

5. **Register-only-applied transitions (K5).** `ApplyMinerStateTransition` adds the `TransitionEventID` to
   `applied_transition_registry` ONLY inside its atomic apply; rejections go to `transition_rejection_log`.

6. **Central scheduler over an explicit context (K8/J9).** `ScheduleEvent` (leaf) is the sole enqueue
   interface over `EventQueueContext`, derives `delta_cycle`, owns `event_creation_seq`; every `⇒`/`SCHEDULE`
   is a call to it. Driver transitions carry a `DriverEventEnvelope` (K4).

7. **Canonical lease termination (K6).** `LeaseExpiry → EnterLowPowerListen` performs the canonical CLOSE
   (`CLOSED`/`expired`/`lease_expiry`); `RenewAssignment` is the sole `SUPERSEDED` path.

## Result

**PROCEDURE CALL GRAPH (Stage 1K): PASS** — all seven required reachability properties hold; the four new
procedures (`CompleteAssignmentPhase`, `FinalizeRoundResidency`, `BeginRoundResidency`,
`CaptureSecurityCensusOnApplicabilityEntry`) are correctly wired; no dangling reference exists (49
defined, 0 undefined).
