# Stage 1L — Procedure Call Graph

Extracted from `STAGE_01_PROTOCOL_PSEUDOCODE.md` (post-L1..L6). `→` is a direct `CALL`; `⇒` is a
scheduled discrete `event` (every `⇒`/`SCHEDULE` is shorthand for a `ScheduleEvent` call — the SOLE
enqueue interface and SOLE delta-cycle authority, J9/K8/L6). **Stage-1L structural changes:**
`RebaseResidencyAtRoundBoundary` (L5) REPLACES the two K3 procedures `FinalizeRoundResidency` +
`BeginRoundResidency`; `TemplateRefresh` now `→ CompleteAssignmentPhase` (L2) instead of an in-line
`ASSIGNMENT → HASHING`. **48 procedures defined; 0 dangling** (net −1 vs Stage 1K: two removed, one
added).

## Direct-call (→) and scheduled-event (⇒) edges

```
ProcessEventTime                   → FinalizeEventTimeSecurityCensus, ScheduleEvent   # I-02 driver; materialises dispatch_envelope (L1)
RoundInitialise                    → RebaseResidencyAtRoundBoundary                    # L5 single idempotent cross-round rebase (subsequent round)
RebaseResidencyAtRoundBoundary     (leaf; SINGLE idempotent boundary owner — close old + reopen new; boundary_id keyed — L5)
TemplateCommit                     (leaf)
PrepareParticipantsForNewRound     → CreatePendingAssignment, StartWake, CompleteAssignmentPhase   # K1/K2; threads dispatch_envelope (L1)
CompleteAssignmentPhase            → CaptureSecurityCensusOnApplicabilityEntry          # K2 (SOLE ASSIGNMENT->HASHING, R4) + K7
CaptureSecurityCensusOnApplicabilityEntry  (leaf; SECOND coherent census writer — K7)
ScheduleEvent                      (leaf; SOLE enqueue interface + SOLE delta-cycle authority over EventQueueContext — J9/K8/L6)
FinalizeEventTimeSecurityCensus    → SecurityFloorEvaluate                              # I-01 epilogue
SecurityFloorEvaluate              (leaf; terminal-first + stale guard + J6 applicability + I-05 recovery)
MinerRegister                      → ApplyMinerStateTransition                          # T1/T2; threads its own dispatch_envelope (L1)
RangeAssign                        → CreatePendingAssignment, StartWake                 # F4/F5; threads dispatch_envelope (L1)
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
                                     StartWake, ResumeFromPause   # I-06; threads dispatch_envelope to each (L1)
ReserveActivate                    → CreatePendingAssignment, StartWake                 # F4/F5; threads dispatch_envelope (L1)
StartWake                          → ApplyMinerStateTransition   ⇒ WakeCompleteEvent    # F5/F6; envelope in (L1); schedules with ONLY event_time+microphase (L6)
WakeCompleteEvent                  → ApplyMinerStateTransition, StartHashing            # F5/F6/G9
ApplyMinerStateTransition          (leaf; SOLE miner_state writer + residency owner; K5 register-only-applied;
                                     J1/K7 coherent census writer; L1 full envelope from dispatch_envelope)
CreatePendingAssignment            (leaf; ORIGINAL/REASSIGNED only — G2)
LeaseExpiry                        → RenewAssignment, EnterLowPowerListen, RangeReassign # L4 STATUS-AWARE; CLOSE source before reassign
RenewAssignment                    (leaf; sole renewal path; SUPERSEDED renewal-only — J7)
RangeReassign                      → CreatePendingAssignment, StartWake                 # F4/F5; asserts status(source)=CLOSED (L4); threads envelope (L1)
SelfValidateFoundSolution          → ValidateCandidate                                  # E2
CreatePropagationContext           (leaf; DISCOVERED — G6/G7)
ScheduleSolutionPropagation        → CreatePropagationContext, SelfValidateFoundSolution, EnterLowPowerListen,
                                     CaptureSecurityCensusOnApplicabilityEntry   ⇒ CertificateArrival, BlockAcceptancePoint   # K7 on SOLUTION_PROPAGATION entry
CertificateArrival                 → EarlyStopVerify
EarlyStopVerify                    → ValidateCandidate, EnterLowPowerListen
ResumeFromPause                    → StartWake                                          # F2/F5 (T30); envelope from dispatch or caller (L1)
BlockAcceptancePoint               (leaf; REGISTER-ONLY — G5)
ValidateCandidate                  (leaf; discovery-time predicate — G1/I2)
AcceptanceBatchFinalize            → ValidateCandidate, ValidBlockAccept, HandlePropagationFailure   # G5
HandlePropagationFailure           ⇒ ResumeFromPause   # F2/G11; SOLUTION_PROPAGATION->HASHING re-entry is NOT R4 (L2); sets NO security_census_dirty (J1)
ValidBlockAccept                   → CloseRoundAssignments                              # F3/G8
CloseRoundAssignments              → EnterLowPowerListen, ApplyMinerStateTransition     # E7/F6; records round_terminal_time only (L5)
CloseTemplateAssignments           → EnterLowPowerListen, ApplyMinerStateTransition     # E8/F6
FullRangeExhaustNoSolution         → TemplateRefresh, RoundAbort                        # threads dispatch_envelope to TemplateRefresh (L1)
TemplateRefresh                    → CloseTemplateAssignments, TemplateCommit, CreatePendingAssignment, StartWake,
                                     CompleteAssignmentPhase   # L2: reaches HASHING ONLY through CompleteAssignmentPhase
RoundAbort                         → CloseRoundAssignments                              # G8
```

## Entry points (dispatched by the loop / sim driver)

`ProcessEventTime` (I-02 driver), `RoundInitialise`, `TemplateCommit`, `PrepareParticipantsForNewRound`
(ASSIGNMENT phase, K1/K2), `MinerRegister`, `ReserveActivate`, `LeaseExpiry`, `FullRangeExhaustNoSolution`,
`ActiveHashRateUpdate`, `AdversarialParticipationChangeEvent`, `AcceptanceBatchFinalize`. Queued handlers
(`WakeCompleteEvent`, `HashWorkEvent`, `CertificateArrival`, `BlockAcceptancePoint`, `ResumeFromPause`)
are enqueued via `ScheduleEvent` and dispatched by `ProcessEventTime`. Each dispatched entry point / queued
handler receives its `dispatch_envelope` from `ProcessEventTime` and THREADS it to every synchronous
miner-transition callee (L1).

## Required-property proofs

1. **No dangling calls.** Every called/scheduled name resolves to a defined procedure (48 defined; 0
   called-but-undefined). `RebaseResidencyAtRoundBoundary` is defined and reached from `RoundInitialise`;
   the removed `FinalizeRoundResidency`/`BeginRoundResidency` have NO remaining call site.

2. **Complete envelope threading (L1).** `ProcessEventTime` materialises one `dispatch_envelope` per
   event; every `StartWake` and every driver `ApplyMinerStateTransition` binds its envelope from it (the
   threaded parameter or the equivalent `EQ.current_*` fields, §0.9). No procedure manually stamps
   `next EQ.event_creation_seq`; the seq is owned solely by `ScheduleEvent`.

3. **Single ASSIGNMENT → HASHING owner (L2).** `CompleteAssignmentPhase` is the ONLY procedure performing
   `ASSIGNMENT → HASHING` (R4). Both `PrepareParticipantsForNewRound → CompleteAssignmentPhase` and
   `TemplateRefresh → CompleteAssignmentPhase` route through it. `HandlePropagationFailure`'s
   `SOLUTION_PROPAGATION → HASHING` is a distinct round-SM re-entry, not an assignment-phase completion.

4. **Canonical discovery-before-lease-expiry order (L3).** Solution discovery (priority item 7) precedes
   lease expiry (item 10) at a shared `event_time`, consistent across §0.7, the §21 table, and the frozen
   G microphase spec; `ScheduleSolutionPropagation` captures the immutable snapshot before `LeaseExpiry`.

5. **Status-aware lease termination (L4).** `LeaseExpiry` branches on the assignment's canonical status
   and CLOSES the source (via `EnterLowPowerListen` for CURRENT, in-line for PAUSED/PENDING) BEFORE
   `RangeReassign`, which asserts `status(source) = CLOSED`. `RenewAssignment` is the sole `SUPERSEDED` path.

6. **Single idempotent round-boundary residency owner (L5).** `RoundInitialise → RebaseResidencyAtRoundBoundary`
   is the ONLY cross-round residency rebase; it is idempotent via `boundary_id`; `ApplyMinerStateTransition`
   remains the sole owner of intervals for an actual state change; `CloseRoundAssignments` records
   `round_terminal_time` only.

7. **Central scheduler + sole delta-cycle authority (L6/K8/J9).** `ScheduleEvent` (leaf) is the sole
   enqueue interface and the sole authority over `delta_cycle`; every `⇒`/`SCHEDULE` is a call to it with
   ONLY `(event_time, microphase)`; `StartWake` schedules `WakeCompleteEvent` with no explicit `delta_cycle`.

## Result

**PROCEDURE CALL GRAPH (Stage 1L): PASS** — all seven required reachability properties hold; the new
procedure `RebaseResidencyAtRoundBoundary` is correctly wired and the two superseded procedures have no
remaining call site; `TemplateRefresh` reaches `HASHING` only through `CompleteAssignmentPhase`; no dangling
reference exists (48 defined, 0 undefined).
