# Stage 1F — Procedure Call Graph

Extracted from `STAGE_01_PROTOCOL_PSEUDOCODE.md` (post-F1..F8). `→` is a direct `CALL`; `⇒` is a
scheduled discrete `event`. New Stage-1F procedures: `ApplyMinerStateTransition`, `StartWake`,
`WakeCompleteEvent`, `CreatePendingAssignment`, `CreatePropagationContext`, `RenewAssignment`.

## Direct-call edges (CALL) and scheduled edges (⇒)

```
RoundInitialise                    (leaf)
TemplateCommit                     (leaf)
MinerRegister                      → ApplyMinerStateTransition                       # T1, T2
RangeAssign                        → CreatePendingAssignment, StartWake              # F4, F5
ActiveHashing                      → CreateSolutionEligibilitySnapshot, EarlyStopGenerate,
                                     ScheduleSolutionPropagation, ActualRangeCompletion,
                                     ReportedExhaustionClaim, ExhaustionAdjudicate, ProgressCommit
ActualRangeCompletion              (leaf)
ReportedExhaustionClaim            (leaf)
ExhaustionAdjudicate               → ApplyMinerStateTransition                       # T7 (F6)
EnterLowPowerListen                → ApplyMinerStateTransition                       # T8/T26/T27/T28/T29 (F6)
ActiveHashRateUpdate               (leaf)   # periodic adversarial-census SAMPLING draw
SecurityFloorEvaluate              (leaf)
ReserveActivate                    → CreatePendingAssignment, StartWake              # F4, F5
StartWake                          → ApplyMinerStateTransition   ⇒ WakeCompleteEvent # F5, F6
WakeCompleteEvent                  → ApplyMinerStateTransition, ActiveHashing        # F5/F6 (T5 or T12)
CreatePendingAssignment            (leaf)   # F4 shared constructor (ORIGINAL/RENEWED/REASSIGNED)
LeaseExpiry                        → RenewAssignment, EnterLowPowerListen, RangeReassign   # F7 / E9
RenewAssignment                    (leaf)   # F7 atomic version swap
RangeReassign                      → CreatePendingAssignment, StartWake              # F4, F5
ProgressCommit                     (leaf)
CreateSolutionEligibilitySnapshot  (leaf)
EarlyStopGenerate                  (leaf)
SelfValidateFoundSolution          → ValidateCandidate
CreatePropagationContext           (leaf)   # F1 mints CandidateID/PropagationID
ScheduleSolutionPropagation        → SelfValidateFoundSolution, CreatePropagationContext,
                                     EnterLowPowerListen   ⇒ CertificateArrival, BlockAcceptancePoint
CertificateArrival                 → EarlyStopVerify
EarlyStopVerify                    → ValidateCandidate, EnterLowPowerListen
ResumeFromPause                    → StartWake                                       # F2/F5 (T30)
BlockAcceptancePoint               → AcceptanceTimestampBatch, HandlePropagationFailure   # F1/F2/F3
ValidateCandidate                  (leaf)   # E1/E2 canonical predicate; resolves versions (I18)
AcceptanceTimestampBatch           → ValidateCandidate, ValidBlockAccept, HandlePropagationFailure
HandlePropagationFailure           → SecurityFloorEvaluate   ⇒ ResumeFromPause       # F2/F3 candidate-scoped
ValidBlockAccept                   → CloseRoundAssignments                           # F3 single closure
CloseRoundAssignments              → EnterLowPowerListen, ApplyMinerStateTransition  # E7/F6
CloseTemplateAssignments           → EnterLowPowerListen, ApplyMinerStateTransition  # E8/F6
ApplyMinerStateTransition          ⇒ SecurityFloorEvaluate                          # F6 (scheduled, not inlined)
FullRangeExhaustNoSolution         → TemplateRefresh, RoundAbort
TemplateRefresh                    → CloseTemplateAssignments, TemplateCommit,
                                     CreatePendingAssignment, StartWake             # E8/F4/F5
RoundAbort                         → CloseRoundAssignments
```

## Required-property proofs

1. **No dangling calls.** Every called/scheduled name resolves to a defined procedure (38 defined;
   0 called-but-undefined). Sim-driver entry points (`RoundInitialise`, `MinerRegister`,
   `RangeAssign`, `ReserveActivate`, `LeaseExpiry`, `FullRangeExhaustNoSolution`,
   `ActiveHashRateUpdate`) are the only defined-but-never-called procedures — as expected.
2. **Single state writer (F6).** The ONLY procedure that changes `miner_state` is
   `ApplyMinerStateTransition`; every state-changing procedure reaches it directly (`MinerRegister`,
   `ExhaustionAdjudicate`, `EnterLowPowerListen`, `WakeCompleteEvent`, `StartWake`,
   `CloseRoundAssignments`, `CloseTemplateAssignments`) — 12 call sites, 0 direct mutations.
3. **Single wake path (F5).** The ONLY wake construct is `StartWake ⇒ WakeCompleteEvent`; the five
   activation callers (`RangeAssign`, `ReserveActivate`, `RangeReassign`, `TemplateRefresh`,
   `ResumeFromPause`) all reach `StartWake`; no synchronous `WakeComplete` exists.
4. **Single pending-assignment constructor (F4).** `CreatePendingAssignment` is called by
   `RangeAssign`, `ReserveActivate`, `RangeReassign`, `TemplateRefresh`; renewal uses the dedicated
   atomic `RenewAssignment`.
5. **Candidate-scoped failure (F2/F3).** `HandlePropagationFailure` is reached only from
   `BlockAcceptancePoint` (non-accept) and `AcceptanceTimestampBatch` (empty batch, once per
   candidate); it `⇒ ResumeFromPause` per matching paused miner and never calls `ValidBlockAccept`.
6. **Single closure path (F3).** `CloseRoundAssignments` is called only by `ValidBlockAccept`
   (ROUND_ACCEPTED) and `RoundAbort` (ROUND_ABORTED); `ValidBlockAccept` clears the propagation set
   and closes exactly once.
7. **Deferred security-floor evaluation (F6).** `ApplyMinerStateTransition ⇒ SecurityFloorEvaluate`
   (scheduled), so floor checks run as prioritised discrete events (F8 priority 5), never inline.

## Result

**PROCEDURE CALL GRAPH (Stage 1F): PASS** — all seven required reachability properties hold; the six
new procedures are correctly wired; no orphaned or dangling call remains.
