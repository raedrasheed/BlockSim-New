# Stage 1M — Procedure Call Graph

Extracted from `STAGE_01_PROTOCOL_PSEUDOCODE.md` (post-M1..M6). `→` is a direct `CALL`; `⇒` is a
scheduled discrete `event` (every `⇒`/`SCHEDULE` is a `ScheduleEvent` call carrying an EXPLICIT
`target_microphase`, §0.7g/M5). **Stage-1M structural changes:** the new round-state helper
`TransitionRoundState` (M2) now owns every dispatched floor-applicable transition and captures the
applicability-entry census; `SettleResidencyBoundary` (M4) replaces `RebaseResidencyAtRoundBoundary` and is
called by BOTH `RoundInitialise` (`REBASE_TO_NEXT_ROUND`) and `RoundAbort` (`FINAL_RUN_END`); every
hook-reaching procedure threads an explicit `dispatch_envelope` (M1). **49 procedures defined; 0 dangling.**

## Direct-call (→) and scheduled-event (⇒) edges

```
ProcessEventTime                   → FinalizeEventTimeSecurityCensus, ScheduleEvent   # I-02 driver; materialises + threads dispatch_envelope (M1)
RoundInitialise                    → SettleResidencyBoundary                          # M4: mode = REBASE_TO_NEXT_ROUND (subsequent round)
SettleResidencyBoundary            (leaf; SINGLE idempotent boundary owner — REBASE_TO_NEXT_ROUND | FINAL_RUN_END, boundary_id-keyed — M4)
TransitionRoundState               → CaptureSecurityCensusOnApplicabilityEntry         # M2: captures census on floor-applicable entry
TemplateCommit                     (leaf)
PrepareParticipantsForNewRound     → CreatePendingAssignment, StartWake, CompleteAssignmentPhase   # threads dispatch_envelope (M1)
CompleteAssignmentPhase            → TransitionRoundState                              # M2: ASSIGNMENT -> HASHING (R4) + census
CaptureSecurityCensusOnApplicabilityEntry  (leaf; SECOND coherent census writer — K7)
ScheduleEvent                      (leaf; SOLE enqueue interface + SOLE delta-cycle authority; explicit target_microphase — L6/M5)
FinalizeEventTimeSecurityCensus    → SecurityFloorEvaluate                             # I-01 epilogue
SecurityFloorEvaluate              (leaf; terminal-first + stale guard + J6 applicability; direct -> SECURITY_RECOVERY, the M2 epilogue exception)
MinerRegister                      → ApplyMinerStateTransition                         # T1/T2; explicit envelope (M1)
RangeAssign                        → CreatePendingAssignment, StartWake                # F4/F5; threads dispatch_envelope (M1)
StartHashing                       → ScheduleNextHashWork                              # G9
ScheduleNextHashWork               → ScheduleEvent ⇒ HashWorkEvent                     # G9/M5 (target_microphase = HASH_WORK)
HashWorkEvent                      → ActualRangeCompletion, CreateSolutionEligibilitySnapshot, EarlyStopGenerate,
                                     ExhaustionAdjudicate, ProgressCommit, ReportedExhaustionClaim,
                                     ScheduleNextHashWork, ScheduleSolutionPropagation  # threads dispatch_envelope (M1)
ActualRangeCompletion / ReportedExhaustionClaim / ProgressCommit / CreateSolutionEligibilitySnapshot / EarlyStopGenerate  (leaves)
ExhaustionAdjudicate               → ApplyMinerStateTransition                         # T7; explicit envelope (M1)
EnterLowPowerListen                → ApplyMinerStateTransition                         # T8/T26/T27/T28/T29; explicit envelope (M1)
ActiveHashRateUpdate               (leaf; COMPUTE-ONLY — G3)
AdversarialParticipationChangeEvent→ ApplyMinerStateTransition, RangeAssign, CreatePendingAssignment,
                                     StartWake, ResumeFromPause   # I-06; threads dispatch_envelope (M1)
ReserveActivate                    → CreatePendingAssignment, StartWake                # F4/F5; threads dispatch_envelope (M1)
StartWake                          → ApplyMinerStateTransition ⇒ WakeCompleteEvent     # F5/F6; explicit envelope in; ScheduleEvent WAKE_COMPLETE (M1/M5)
WakeCompleteEvent                  → ApplyMinerStateTransition, StartHashing           # F5/F6/G9; M3 stale-target guard FIRST; explicit envelope (M1)
ApplyMinerStateTransition          (leaf; SOLE miner_state writer + residency owner; J1/K7 census writer; explicit envelope always M1)
CreatePendingAssignment            (leaf; ORIGINAL/REASSIGNED only — G2)
LeaseExpiry                        → RenewAssignment, EnterLowPowerListen, RangeReassign, ApplyMinerStateTransition   # L4/M3 status-aware; explicit envelope
RenewAssignment                    (leaf; sole renewal path; SUPERSEDED renewal-only — J7)
RangeReassign                      → CreatePendingAssignment, StartWake                # F4/F5; asserts status(source)=CLOSED (L4); explicit envelope
SelfValidateFoundSolution          → ValidateCandidate                                 # E2
CreatePropagationContext           (leaf; DISCOVERED — G6/G7)
ScheduleSolutionPropagation        → CreatePropagationContext, SelfValidateFoundSolution, EnterLowPowerListen,
                                     TransitionRoundState, ScheduleEvent ⇒ CertificateArrival, BlockAcceptancePoint   # M2 HASHING->SP entry; M5 microphases
CertificateArrival                 → EarlyStopVerify                                   # threads dispatch_envelope (M1)
EarlyStopVerify                    → ValidateCandidate, EnterLowPowerListen            # threads dispatch_envelope (M1)
ResumeFromPause                    → StartWake                                         # F2/F5 (T30); explicit envelope (M1)
BlockAcceptancePoint               (leaf; REGISTER-ONLY — G5)
ValidateCandidate                  (leaf; discovery-time predicate — G1/I2)
AcceptanceBatchFinalize            → ValidateCandidate, ValidBlockAccept, HandlePropagationFailure   # G5; threads dispatch_envelope (M1)
HandlePropagationFailure           → TransitionRoundState, ScheduleEvent ⇒ ResumeFromPause   # M2 SP->HASHING re-entry + census; M5 RESUME microphase
ValidBlockAccept                   → CloseRoundAssignments                             # F3/G8; threads dispatch_envelope (M1)
CloseRoundAssignments              → EnterLowPowerListen, ApplyMinerStateTransition    # E7/F6; records round_terminal_time only, NO residency finalise (M4)
CloseTemplateAssignments           → EnterLowPowerListen, ApplyMinerStateTransition    # E8/F6; explicit envelope (M1); stably sorted loop (M5)
FullRangeExhaustNoSolution         → TemplateRefresh, RoundAbort                       # threads dispatch_envelope (M1)
TemplateRefresh                    → CloseTemplateAssignments, TemplateCommit, CreatePendingAssignment, StartWake,
                                     CompleteAssignmentPhase   # sorted eligible loop (M5); HASHING only via CompleteAssignmentPhase (L2/M2)
RoundAbort                         → CloseRoundAssignments, SettleResidencyBoundary    # M4: FINAL_RUN_END settle before I5/I6/I7 checks
```

## Entry points (dispatched by the loop / sim driver)

`ProcessEventTime` (I-02 driver), `RoundInitialise`, `TemplateCommit`, `PrepareParticipantsForNewRound`,
`MinerRegister`, `ReserveActivate`, `LeaseExpiry`, `FullRangeExhaustNoSolution`, `ActiveHashRateUpdate`,
`AdversarialParticipationChangeEvent`, `AcceptanceBatchFinalize`. Queued handlers (`WakeCompleteEvent`,
`HashWorkEvent`, `CertificateArrival`, `BlockAcceptancePoint`, `ResumeFromPause`) are enqueued via
`ScheduleEvent` (each with an explicit `target_microphase`) and dispatched by `ProcessEventTime`. Every
dispatched entry point / queued handler receives its `dispatch_envelope` from `ProcessEventTime` and
THREADS it to every synchronous callee that reaches `ApplyMinerStateTransition` (M1).

## Required-property proofs

1. **No dangling calls.** Every called/scheduled name resolves to a defined procedure (49 defined; 0
   called-but-undefined). `SettleResidencyBoundary` and `TransitionRoundState` are defined and reached;
   the withdrawn `RebaseResidencyAtRoundBoundary`/`FinalizeRoundResidency`/`BeginRoundResidency` have no
   call site.

2. **Explicit envelope threading (M1).** Every procedure that directly or indirectly reaches
   `ApplyMinerStateTransition` carries an explicit `dispatch_envelope` and threads it; every one of the 15
   hook call sites spells out `event_time`/`delta_cycle`/`event_seq`. No positional `now` form remains.

3. **Census on every floor-applicable entry (M2).** `TransitionRoundState` is reached from
   `CompleteAssignmentPhase` (ASSIGNMENT→HASHING), `ScheduleSolutionPropagation` (HASHING→SOLUTION_PROPAGATION),
   and `HandlePropagationFailure` (SOLUTION_PROPAGATION→HASHING re-entry); each captures the census. The
   epilogue `SecurityFloorEvaluate`'s `→ SECURITY_RECOVERY` is the sole documented exception.

4. **Executable wake handling (M3).** `LeaseExpiry` cancels the exact `WakeCompleteEvent` and resolves a
   `WAKING` holder before closing/reassigning; `WakeCompleteEvent` guards its target first (`stale_wake_noop`).

5. **Single residency-boundary owner (M4).** `RoundInitialise → SettleResidencyBoundary` (REBASE) and
   `RoundAbort → SettleResidencyBoundary` (FINAL_RUN_END) are the ONLY boundary residency close/reopen;
   `CloseRoundAssignments` performs none. `ApplyMinerStateTransition` remains the sole owner of intervals
   for an actual state change.

6. **Microphase-complete enqueue (M5).** Every `⇒`/`ScheduleEvent` carries an explicit `target_microphase`
   from the §0.7g mapping; every event-producing loop is stably sorted before seq assignment.

## Result

**PROCEDURE CALL GRAPH (Stage 1M): PASS** — all six required reachability properties hold; the new
procedures `TransitionRoundState` and `SettleResidencyBoundary` are correctly wired and the withdrawn
residency procedures have no remaining call site; no dangling reference exists (49 defined, 0 undefined).
