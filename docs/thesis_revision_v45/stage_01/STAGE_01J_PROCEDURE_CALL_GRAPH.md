# Stage 1J — Procedure Call Graph

Extracted from `STAGE_01_PROTOCOL_PSEUDOCODE.md` (post-J1..J9). `→` is a direct `CALL`; `⇒` is a
scheduled discrete `event` — and every `⇒`/`SCHEDULE` is shorthand for a call to the central scheduler
`ScheduleEvent` (§0.7e/J9). **New Stage-1J procedures:** `ScheduleEvent` (J9 sole enqueue interface) and
`PrepareParticipantsForNewRound` (J5 next-round participant path). No procedure was removed. 45
procedures defined; 0 dangling.

## Direct-call (→) and scheduled-event (⇒) edges

```
ProcessEventTime                   → FinalizeEventTimeSecurityCensus     # I-02 driver; runs the epilogue after quiescence
                                     (dispatches queued handlers; all scheduling is via ScheduleEvent, J9)
ScheduleEvent                      (leaf; SOLE enqueue interface — J9: rejects finalised event_time, owns event_creation_seq)
FinalizeEventTimeSecurityCensus    → SecurityFloorEvaluate               # I-01 epilogue; asserts J1 coherence; passes J8 provenance
SecurityFloorEvaluate              (leaf; terminal-first + J8 stale guard + J6 applicability-before-breach + I-05 recovery)
RoundInitialise                    (leaf; initialises ALL registries incl event_creation_seq — I-04/J4)
TemplateCommit                     (leaf)
PrepareParticipantsForNewRound     → CreatePendingAssignment, StartWake  # J5 (T3/T4/T10; runs in ASSIGNMENT before R4)
MinerRegister                      → ApplyMinerStateTransition           # T1, T2
RangeAssign                        → CreatePendingAssignment, StartWake   # F4, F5
StartHashing                       → ScheduleNextHashWork                 # G9
ScheduleNextHashWork               ⇒ HashWorkEvent                        # G9
HashWorkEvent                      → CreateSolutionEligibilitySnapshot, EarlyStopGenerate,
                                     ScheduleSolutionPropagation, ActualRangeCompletion,
                                     ReportedExhaustionClaim, ExhaustionAdjudicate, ProgressCommit,
                                     ScheduleNextHashWork
ActualRangeCompletion              (leaf)
ReportedExhaustionClaim            (leaf)
ExhaustionAdjudicate               → ApplyMinerStateTransition            # T7 (F6)
EnterLowPowerListen                → ApplyMinerStateTransition            # T8/T26/T27/T28/T29; passes candidate_id+propagation_id (J3); CLOSED status (J7)
ActiveHashRateUpdate               (leaf; COMPUTE-ONLY — G3)
AdversarialParticipationChangeEvent→ ApplyMinerStateTransition, RangeAssign, CreatePendingAssignment,
                                     StartWake, ResumeFromPause   # I-06; exit T11 sets status = CLOSED (J7)
ReserveActivate                    → CreatePendingAssignment, StartWake   # F4, F5
StartWake                          → ApplyMinerStateTransition   ⇒ WakeCompleteEvent   # F5, F6
WakeCompleteEvent                  → ApplyMinerStateTransition, StartHashing            # F5/F6/G9 (G4 status-aware failure)
ApplyMinerStateTransition          (leaf; SOLE miner_state writer + residency owner + security-census writer;
                                     J2 replay-before-precondition; J3 full envelope; J1 atomic dirty+latest; J8 provenance)
CreatePendingAssignment            (leaf; ORIGINAL/REASSIGNED only — G2)
LeaseExpiry                        → RenewAssignment, EnterLowPowerListen, RangeReassign   # F7/E9
RenewAssignment                    (leaf; sole renewal path; SUPERSEDED renewal-only — J7)
RangeReassign                      → CreatePendingAssignment, StartWake   # F4, F5
ProgressCommit                     (leaf)
CreateSolutionEligibilitySnapshot  (leaf)
EarlyStopGenerate                  (leaf)
SelfValidateFoundSolution          → ValidateCandidate                   # E2
CreatePropagationContext           (leaf; DISCOVERED + deterministic ids — G6/G7)
ScheduleSolutionPropagation        → CreatePropagationContext, SelfValidateFoundSolution,
                                     EnterLowPowerListen   ⇒ CertificateArrival, BlockAcceptancePoint
CertificateArrival                 → EarlyStopVerify
EarlyStopVerify                    → ValidateCandidate, EnterLowPowerListen
ResumeFromPause                    → StartWake                            # F2/F5 (T30; two-id match G11)
BlockAcceptancePoint               (leaf; REGISTER-ONLY — G5)
ValidateCandidate                  (leaf; discovery-time predicate — G1/I2)
AcceptanceBatchFinalize            → ValidateCandidate, ValidBlockAccept, HandlePropagationFailure   # G5
HandlePropagationFailure           ⇒ ResumeFromPause   # F2/G11; sets NO security_census_dirty (J1)
ValidBlockAccept                   → CloseRoundAssignments                # F3/G8 (accepts from SP or SR — H1)
CloseRoundAssignments              → EnterLowPowerListen, ApplyMinerStateTransition   # E7/F6
CloseTemplateAssignments           → EnterLowPowerListen, ApplyMinerStateTransition   # E8/F6
FullRangeExhaustNoSolution         → TemplateRefresh, RoundAbort
TemplateRefresh                    → CloseTemplateAssignments, TemplateCommit, CreatePendingAssignment, StartWake
RoundAbort                         → CloseRoundAssignments                # G8
```

## Entry points (defined, dispatched by the loop / sim driver)

`ProcessEventTime` (top-level event-time driver, I-02), `RoundInitialise`, `TemplateCommit`,
`PrepareParticipantsForNewRound` (ASSIGNMENT phase, J5), `MinerRegister`, `ReserveActivate`,
`LeaseExpiry`, `FullRangeExhaustNoSolution`, `ActiveHashRateUpdate`,
`AdversarialParticipationChangeEvent`, `AcceptanceBatchFinalize`. Queued event handlers
(`WakeCompleteEvent`, `HashWorkEvent`, `CertificateArrival`, `BlockAcceptancePoint`, `ResumeFromPause`)
are enqueued via `ScheduleEvent` and dispatched by `ProcessEventTime`.

## Required-property proofs

1. **No dangling calls.** Every called/scheduled name resolves to a defined procedure (45 defined; 0
   called-but-undefined). The two new procedures (`ScheduleEvent`, `PrepareParticipantsForNewRound`)
   introduce no dangling reference.

2. **Single security-decision path, coherent + provenanced (J1/J8).** `SecurityFloorEvaluate` is a leaf
   reached ONLY via `FinalizeEventTimeSecurityCensus`, reached ONLY via `ProcessEventTime`.
   `ApplyMinerStateTransition` is the sole writer of `security_census_dirty`/`latest_security_census`
   (written together atomically); `HandlePropagationFailure` sets NO dirty flag (J1). The epilogue asserts
   coherence and passes the census's stored provenance (J8).

3. **Single state writer + replay-before-precondition (F6/J2/J3).** `ApplyMinerStateTransition` is the
   ONLY writer of `miner_state`; its step (1) replay guard (by full `TransitionEventID` incl both
   candidate ids) precedes the step (2) old-state precondition. All state-changing procedures reach it.

4. **Central scheduler (J4/J9).** `ScheduleEvent` is the sole enqueue interface and sole owner of
   `event_creation_seq`; every `⇒`/`SCHEDULE` edge above is a `ScheduleEvent` call. It rejects a
   finalised `event_time`, applies the delta-cycle forward rule, and inserts by the deterministic
   total-order key.

5. **Next-round participation (J5).** `PrepareParticipantsForNewRound → {CreatePendingAssignment,
   StartWake}` binds fresh `ORIGINAL`/`REASSIGNED` `PENDING` under the new `RoundID`/`TemplateID` and
   wakes via T3/T4/T10 before `ASSIGNMENT → HASHING` (R4); it reopens no CLOSED assignment.

6. **Canonical terminal status (J7).** `RenewAssignment` is the sole `SUPERSEDED` (renewal) path; every
   termination (`EnterLowPowerListen` revocation/exhaustion/round-close cases, the adversarial exit)
   sets `status = CLOSED`, leaving zero live heads (I18b).

7. **Register-then-finalize acceptance, event-scheduled hashing preserved (G5/G9).**
   `AcceptanceBatchFinalize → {ValidateCandidate*, ValidBlockAccept, HandlePropagationFailure}`;
   `WakeCompleteEvent → StartHashing → ScheduleNextHashWork ⇒ HashWorkEvent`.

## Result

**PROCEDURE CALL GRAPH (Stage 1J): PASS** — all seven required reachability properties hold; the new
`ScheduleEvent` (sole enqueue) and `PrepareParticipantsForNewRound` (next-round path) are correctly
wired; the single security path is coherent and provenanced; no dangling reference exists (45 defined, 0
undefined).
