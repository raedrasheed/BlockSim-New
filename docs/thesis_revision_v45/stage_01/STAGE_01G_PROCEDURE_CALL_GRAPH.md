# Stage 1G — Procedure Call Graph

Extracted from `STAGE_01_PROTOCOL_PSEUDOCODE.md` (post-G1..G11). `→` is a direct `CALL`; `⇒` is a
scheduled discrete `event`. New Stage-1G procedures: `AdversarialParticipationChangeEvent`,
`StartHashing`, `ScheduleNextHashWork`, `HashWorkEvent`, `AcceptanceBatchFinalize`. Removed:
`ActiveHashing` (blocking loop, G9), `AcceptanceTimestampBatch` (folded into `AcceptanceBatchFinalize`, G5).

## Direct-call (→) and scheduled-event (⇒) edges

```
RoundInitialise                    (leaf; inits registries — G8)
TemplateCommit                     (leaf)
MinerRegister                      → ApplyMinerStateTransition                        # T1, T2
RangeAssign                        → CreatePendingAssignment, StartWake               # F4, F5
StartHashing                       → ScheduleNextHashWork                             # G9
ScheduleNextHashWork               ⇒ HashWorkEvent                                    # G9
HashWorkEvent                      → CreateSolutionEligibilitySnapshot, EarlyStopGenerate,
                                     ScheduleSolutionPropagation, ActualRangeCompletion,
                                     ReportedExhaustionClaim, ExhaustionAdjudicate, ProgressCommit,
                                     ScheduleNextHashWork                             # G9 (one bounded unit/event)
ActualRangeCompletion              (leaf)
ReportedExhaustionClaim            (leaf)
ExhaustionAdjudicate               → ApplyMinerStateTransition                        # T7 (F6)
EnterLowPowerListen                → ApplyMinerStateTransition                        # T8/T26/T27/T28/T29 (F6)
ActiveHashRateUpdate               (leaf; COMPUTE-ONLY — G3)
AdversarialParticipationChangeEvent→ ApplyMinerStateTransition, RangeAssign          # G3 (exit T11 / enter)
SecurityFloorEvaluate              (leaf; scheduled + terminal-guarded — G10)
ReserveActivate                    → CreatePendingAssignment, StartWake              # F4, F5
StartWake                          → ApplyMinerStateTransition   ⇒ WakeCompleteEvent  # F5, F6
WakeCompleteEvent                  → ApplyMinerStateTransition, StartHashing          # F5/F6/G9 (G4 status-aware failure)
CreatePendingAssignment            (leaf; ORIGINAL/REASSIGNED only — G2)
LeaseExpiry                        → RenewAssignment, EnterLowPowerListen, RangeReassign   # F7/E9
RenewAssignment                    (leaf; sole renewal path, same lineage — G2)
RangeReassign                      → CreatePendingAssignment, StartWake              # F4, F5
ProgressCommit                     (leaf)
CreateSolutionEligibilitySnapshot  (leaf)
EarlyStopGenerate                  (leaf)
SelfValidateFoundSolution          → ValidateCandidate                              # E2
CreatePropagationContext           (leaf; DISCOVERED + deterministic ids — G6/G7)
ScheduleSolutionPropagation        → CreatePropagationContext, SelfValidateFoundSolution,
                                     EnterLowPowerListen   ⇒ CertificateArrival, BlockAcceptancePoint
CertificateArrival                 → EarlyStopVerify
EarlyStopVerify                    → ValidateCandidate, EnterLowPowerListen
ResumeFromPause                    → StartWake                                       # F2/F5 (T30; two-id match G11)
BlockAcceptancePoint               (leaf; REGISTER-ONLY — G5)
ValidateCandidate                  (leaf; discovery-time predicate — G1/I2, resolves version I18)
AcceptanceBatchFinalize            → ValidateCandidate, ValidBlockAccept, HandlePropagationFailure   # G5 (one/timestamp)
HandlePropagationFailure           ⇒ ResumeFromPause, SecurityFloorEvaluate          # F2/F3/G10/G11 (both ids)
ValidBlockAccept                   → CloseRoundAssignments                           # F3/G8 (accepts from SP or SR)
CloseRoundAssignments              → EnterLowPowerListen, ApplyMinerStateTransition  # E7/F6 (clears registries — G8)
CloseTemplateAssignments           → EnterLowPowerListen, ApplyMinerStateTransition  # E8/F6 (clears old-tmpl ctxs — G8)
FullRangeExhaustNoSolution         → TemplateRefresh, RoundAbort
TemplateRefresh                    → CloseTemplateAssignments, TemplateCommit, CreatePendingAssignment, StartWake
RoundAbort                         → CloseRoundAssignments                           # G8 (dispositions live ctxs, clears registries)
```

## Required-property proofs

1. **No dangling calls.** Every called/scheduled name resolves to a defined procedure (41 defined; 0
   called-but-undefined). Sim-driver entry points (`RoundInitialise`, `MinerRegister`, `RangeAssign`,
   `ReserveActivate`, `LeaseExpiry`, `FullRangeExhaustNoSolution`, `ActiveHashRateUpdate`,
   `AdversarialParticipationChangeEvent`, `AcceptanceBatchFinalize`) are the only defined-but-never-called
   procedures — as expected (the last two are scheduled by the loop's phases, not by a procedure).
2. **Hashing is event-scheduled, non-blocking (G9).** `WakeCompleteEvent → StartHashing →
   ScheduleNextHashWork ⇒ HashWorkEvent`, and `HashWorkEvent → ScheduleNextHashWork` (one bounded unit
   per event). No `ActiveHashing` WHILE loop exists; no procedure blocks on hashing.
3. **Single state writer (G3/F6).** `ApplyMinerStateTransition` is the ONLY writer of `miner_state`;
   `MinerRegister`, `ExhaustionAdjudicate`, `EnterLowPowerListen`, `StartWake`, `WakeCompleteEvent`,
   `AdversarialParticipationChangeEvent`, `CloseRoundAssignments`, `CloseTemplateAssignments` all reach it
   (0 direct mutations). `ActiveHashRateUpdate` is a compute-only leaf.
4. **Register-then-finalize acceptance (G5).** `BlockAcceptancePoint` is a register-only leaf;
   `AcceptanceBatchFinalize` (one per timestamp) `→ ValidateCandidate*, ValidBlockAccept,
   HandlePropagationFailure`. Round closure (`ValidBlockAccept → CloseRoundAssignments`) is reached
   ONLY through `AcceptanceBatchFinalize` (or `RoundAbort`), never from a block-arrival directly.
5. **Scheduled, terminal-guarded floor evaluation (G10).** `SecurityFloorEvaluate` is a leaf reached
   only via `⇒` from `ApplyMinerStateTransition` and `HandlePropagationFailure`; it is never called inline.
6. **Sole renewal path (G2).** `LeaseExpiry → RenewAssignment` (same-lineage atomic swap);
   `CreatePendingAssignment` (called by `RangeAssign`/`ReserveActivate`/`RangeReassign`/`TemplateRefresh`)
   builds only ORIGINAL/REASSIGNED fresh lineages.
7. **Candidate lifecycle + cleanup (G6/G8).** `ScheduleSolutionPropagation → CreatePropagationContext`
   (DISCOVERED) then advances the status; `ValidBlockAccept`, `RoundAbort`, `CloseRoundAssignments`,
   `CloseTemplateAssignments` disposition live contexts and clear the registries.

## Result

**PROCEDURE CALL GRAPH (Stage 1G): PASS** — all seven required reachability properties hold; the five
new procedures are correctly wired; the removed `ActiveHashing`/`AcceptanceTimestampBatch` leave no
dangling reference.
