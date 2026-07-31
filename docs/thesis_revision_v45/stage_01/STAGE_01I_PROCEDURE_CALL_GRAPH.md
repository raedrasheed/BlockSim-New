# Stage 1I — Procedure Call Graph

Extracted from `STAGE_01_PROTOCOL_PSEUDOCODE.md` (post-I-01..I-08). `→` is a direct `CALL`; `⇒` is a
scheduled discrete `event`. **New Stage-1I procedures:** `ProcessEventTime` (I-02 event-loop driver)
and `FinalizeEventTimeSecurityCensus` (I-01 event-time epilogue). **Removed:**
`FinalizeTimestampSecurityCensus` (superseded by the event-time epilogue). 43 procedures defined; 0
dangling.

## Direct-call (→) and scheduled-event (⇒) edges

```
ProcessEventTime                   → FinalizeEventTimeSecurityCensus   # I-02 driver; runs the epilogue after quiescence
FinalizeEventTimeSecurityCensus    → SecurityFloorEvaluate             # I-01 epilogue; SOLE caller
SecurityFloorEvaluate              (leaf; terminal-first + legal-source guarded — I-05/G10)
RoundInitialise                    (leaf; initialises ALL per-round + per-run registries — I-04)
TemplateCommit                     (leaf)
MinerRegister                      → ApplyMinerStateTransition                        # T1, T2
RangeAssign                        → CreatePendingAssignment, StartWake               # F4, F5
StartHashing                       → ScheduleNextHashWork                             # G9
ScheduleNextHashWork               ⇒ HashWorkEvent                                    # G9
HashWorkEvent                      → CreateSolutionEligibilitySnapshot, EarlyStopGenerate,
                                     ScheduleSolutionPropagation, ActualRangeCompletion,
                                     ReportedExhaustionClaim, ExhaustionAdjudicate, ProgressCommit,
                                     ScheduleNextHashWork      # G9 (records hash METADATA only — H7/I19)
ActualRangeCompletion              (leaf)
ReportedExhaustionClaim            (leaf)
ExhaustionAdjudicate               → ApplyMinerStateTransition                        # T7 (F6)
EnterLowPowerListen                → ApplyMinerStateTransition                        # T8/T26/T27/T28/T29 (F6); explicit assignment_ref (H8)
ActiveHashRateUpdate               (leaf; COMPUTE-ONLY — G3)
AdversarialParticipationChangeEvent→ ApplyMinerStateTransition, RangeAssign, CreatePendingAssignment,
                                     StartWake, ResumeFromPause   # I-06 (state-specific enter/exit; exit T11; custody I-07)
ReserveActivate                    → CreatePendingAssignment, StartWake               # F4, F5
StartWake                          → ApplyMinerStateTransition   ⇒ WakeCompleteEvent  # F5, F6; zero-latency in delta_cycle+1 (H5)
WakeCompleteEvent                  → ApplyMinerStateTransition, StartHashing           # F5/F6/G9 (G4 status-aware failure)
ApplyMinerStateTransition          (leaf; SOLE miner_state writer + residency owner; TransitionEventID idempotence I-03;
                                     flags security_census_dirty + overwrites latest_security_census I-01)
CreatePendingAssignment            (leaf; ORIGINAL/REASSIGNED only — G2)
LeaseExpiry                        → RenewAssignment, EnterLowPowerListen, RangeReassign   # F7/E9 (assignment_ref — H8)
RenewAssignment                    (leaf; sole renewal path, same lineage — G2)
RangeReassign                      → CreatePendingAssignment, StartWake               # F4, F5
ProgressCommit                     (leaf)
CreateSolutionEligibilitySnapshot  (leaf)
EarlyStopGenerate                  (leaf)
SelfValidateFoundSolution          → ValidateCandidate                               # E2
CreatePropagationContext           (leaf; DISCOVERED + deterministic ids — G6/G7)
ScheduleSolutionPropagation        → CreatePropagationContext, SelfValidateFoundSolution,
                                     EnterLowPowerListen   ⇒ CertificateArrival, BlockAcceptancePoint
CertificateArrival                 → EarlyStopVerify
EarlyStopVerify                    → ValidateCandidate, EnterLowPowerListen
ResumeFromPause                    → StartWake             # F2/F5 (T30; two-id match G11; adversarial_reactivation I-06)
BlockAcceptancePoint               (leaf; REGISTER-ONLY — G5)
ValidateCandidate                  (leaf; discovery-time predicate — G1/I2)
AcceptanceBatchFinalize            → ValidateCandidate, ValidBlockAccept, HandlePropagationFailure   # G5 (one/timestamp)
HandlePropagationFailure           ⇒ ResumeFromPause       # F2/G11 (two ids); sets security_census_dirty[now], does NOT schedule the floor (I-01)
ValidBlockAccept                   → CloseRoundAssignments  # F3/G8 (accepts from SOLUTION_PROPAGATION or SECURITY_RECOVERY — H1)
CloseRoundAssignments              → EnterLowPowerListen, ApplyMinerStateTransition   # E7/F6 (assignment_ref — H8)
CloseTemplateAssignments           → EnterLowPowerListen, ApplyMinerStateTransition   # E8/F6 (assignment_ref — H8)
FullRangeExhaustNoSolution         → TemplateRefresh, RoundAbort
TemplateRefresh                    → CloseTemplateAssignments, TemplateCommit, CreatePendingAssignment, StartWake
RoundAbort                         → CloseRoundAssignments  # G8
```

## Entry points (defined, dispatched by the loop / sim driver — never called by a procedure)

`ProcessEventTime` (top-level event-time driver, I-02), `RoundInitialise`, `MinerRegister`,
`ReserveActivate`, `LeaseExpiry`, `FullRangeExhaustNoSolution`, `ActiveHashRateUpdate`,
`AdversarialParticipationChangeEvent`, `AcceptanceBatchFinalize`. Queued event handlers
(`WakeCompleteEvent`, `HashWorkEvent`, `CertificateArrival`, `BlockAcceptancePoint`, `ResumeFromPause`)
are reached via `⇒` from their schedulers and DISPATCHED by `ProcessEventTime`.

## Required-property proofs

1. **No dangling calls.** Every called/scheduled name resolves to a defined procedure (43 defined; 0
   called-but-undefined). `FinalizeTimestampSecurityCensus` leaves no dangling reference (fully
   replaced by `FinalizeEventTimeSecurityCensus`).

2. **Event-time security epilogue is the sole security path (I-01/I-02).** `SecurityFloorEvaluate` is a
   leaf reached ONLY via `FinalizeEventTimeSecurityCensus`, which is reached ONLY via `ProcessEventTime`
   (the driver, after quiescence). `ApplyMinerStateTransition` and `HandlePropagationFailure` set
   `security_census_dirty[event_time]` / overwrite `latest_security_census[event_time]` but NEVER call
   or schedule a floor decision. There is exactly one security-decision path in the whole graph.

3. **Single state writer + residency owner + idempotence (F6/H7/I-03).** `ApplyMinerStateTransition` is
   the ONLY writer of `miner_state`, the SOLE owner of `residency_ledger`, and the sole builder/checker
   of `TransitionEventID` against `transition_event_registry`. All state-changing procedures
   (`MinerRegister`, `ExhaustionAdjudicate`, `EnterLowPowerListen`, `StartWake`, `WakeCompleteEvent`,
   `AdversarialParticipationChangeEvent`, `CloseRoundAssignments`, `CloseTemplateAssignments`) reach it.

4. **State-specific adversarial change (I-06).** `AdversarialParticipationChangeEvent → {ApplyMinerState
   Transition, RangeAssign, CreatePendingAssignment, StartWake, ResumeFromPause}`. Entry uses a legal
   per-state edge (T3/T4; hook T17 then RangeAssign; T30 resume; fresh T10); a closed or refreshing
   round takes a deferral return (no assignment/wake). Exit reaches `ApplyMinerStateTransition` (T11).

5. **Register-then-finalize acceptance, closure downstream of arbitration (G5/H1).**
   `AcceptanceBatchFinalize → {ValidateCandidate*, ValidBlockAccept, HandlePropagationFailure}`; round
   closure (`ValidBlockAccept → CloseRoundAssignments`) is reached ONLY through `AcceptanceBatchFinalize`
   or `RoundAbort`. `ValidBlockAccept` accepts from `{SOLUTION_PROPAGATION, SECURITY_RECOVERY}`.

6. **Explicit registry initialisation (I-04).** `RoundInitialise` (a leaf) initialises every per-round
   and per-run registry consumed by the procedures above; no consumer reads an uninitialised registry.

7. **Event-scheduled hashing (G9), explicit assignment_ref (H8).** `WakeCompleteEvent → StartHashing →
   ScheduleNextHashWork ⇒ HashWorkEvent`; every `EnterLowPowerListen` caller passes an explicit
   `assignment_ref`.

## Result

**PROCEDURE CALL GRAPH (Stage 1I): PASS** — all seven required reachability properties hold; the new
`ProcessEventTime` (driver) and `FinalizeEventTimeSecurityCensus` (epilogue) form the single security
path; `SecurityFloorEvaluate` is reachable only through the epilogue; no dangling reference exists (43
defined, 0 undefined).
