# Stage 1H — Procedure Call Graph

Extracted from `STAGE_01_PROTOCOL_PSEUDOCODE.md` (post-H1..H9). `→` is a direct `CALL`; `⇒` is a
scheduled discrete `event`. **New Stage-1H procedure:** `FinalizeTimestampSecurityCensus` (H3).
**Rewiring:** `ApplyMinerStateTransition` and `HandlePropagationFailure` no longer schedule
`SecurityFloorEvaluate`; instead `FinalizeTimestampSecurityCensus` (loop microphase 5) is the SOLE
caller of `SecurityFloorEvaluate` (H3), and `AdversarialParticipationChangeEvent` takes
state-specific legal paths (H6). No procedure was removed. 42 procedures defined; 0 dangling.

## Direct-call (→) and scheduled-event (⇒) edges

```
RoundInitialise                    (leaf; inits registries incl security_evaluation_required + residency_ledger — H3/H7)
TemplateCommit                     (leaf)
MinerRegister                      → ApplyMinerStateTransition                         # T1, T2
RangeAssign                        → CreatePendingAssignment, StartWake                # F4, F5
StartHashing                       → ScheduleNextHashWork                              # G9
ScheduleNextHashWork               ⇒ HashWorkEvent                                     # G9
HashWorkEvent                      → CreateSolutionEligibilitySnapshot, EarlyStopGenerate,
                                     ScheduleSolutionPropagation, ActualRangeCompletion,
                                     ReportedExhaustionClaim, ExhaustionAdjudicate, ProgressCommit,
                                     ScheduleNextHashWork      # G9 (records hash METADATA only — H7/I19)
ActualRangeCompletion              (leaf)
ReportedExhaustionClaim            (leaf)
ExhaustionAdjudicate               → ApplyMinerStateTransition                         # T7 (F6)
EnterLowPowerListen                → ApplyMinerStateTransition                         # T8/T26/T27/T28/T29 (F6); explicit assignment_ref (H8)
ActiveHashRateUpdate               (leaf; COMPUTE-ONLY — G3)
AdversarialParticipationChangeEvent→ ApplyMinerStateTransition, RangeAssign, CreatePendingAssignment,
                                     StartWake, ResumeFromPause   # H6 (state-specific enter/exit; exit T11)
FinalizeTimestampSecurityCensus    → SecurityFloorEvaluate                             # H3 (microphase 5; SOLE caller)
SecurityFloorEvaluate              (leaf; invoked ONLY by FinalizeTimestampSecurityCensus — H3; terminal/source-guarded G10/H4)
ReserveActivate                    → CreatePendingAssignment, StartWake               # F4, F5
StartWake                          → ApplyMinerStateTransition   ⇒ WakeCompleteEvent   # F5, F6; zero-latency in delta_cycle+1 (H5)
WakeCompleteEvent                  → ApplyMinerStateTransition, StartHashing           # F5/F6/G9 (G4 status-aware failure)
CreatePendingAssignment            (leaf; ORIGINAL/REASSIGNED only — G2)
LeaseExpiry                        → RenewAssignment, EnterLowPowerListen, RangeReassign   # F7/E9 (assignment_ref — H8)
RenewAssignment                    (leaf; sole renewal path, same lineage — G2)
RangeReassign                      → CreatePendingAssignment, StartWake               # F4, F5
ProgressCommit                     (leaf)
CreateSolutionEligibilitySnapshot  (leaf)
EarlyStopGenerate                  (leaf)
SelfValidateFoundSolution          → ValidateCandidate                                # E2
CreatePropagationContext           (leaf; DISCOVERED + deterministic ids — G6/G7)
ScheduleSolutionPropagation        → CreatePropagationContext, SelfValidateFoundSolution,
                                     EnterLowPowerListen   ⇒ CertificateArrival, BlockAcceptancePoint   # assignment_ref (H8)
CertificateArrival                 → EarlyStopVerify
EarlyStopVerify                    → ValidateCandidate, EnterLowPowerListen            # assignment_ref (H8)
ResumeFromPause                    → StartWake                                         # F2/F5 (T30; two-id match G11; adversarial_reactivation trigger H6)
BlockAcceptancePoint               (leaf; REGISTER-ONLY — G5)
ValidateCandidate                  (leaf; discovery-time predicate — G1/I2, resolves version I18a/I18b)
AcceptanceBatchFinalize            → ValidateCandidate, ValidBlockAccept, HandlePropagationFailure   # G5 (one/timestamp, microphase 4)
HandlePropagationFailure           ⇒ ResumeFromPause          # F2/G11 (two ids); sets security_evaluation_required, does NOT schedule the floor (H3)
ValidBlockAccept                   → CloseRoundAssignments     # F3/G8 (accepts from SOLUTION_PROPAGATION or SECURITY_RECOVERY — H1)
CloseRoundAssignments              → EnterLowPowerListen, ApplyMinerStateTransition   # E7/F6 (clears registries — G8; assignment_ref — H8)
CloseTemplateAssignments           → EnterLowPowerListen, ApplyMinerStateTransition   # E8/F6 (clears old-tmpl ctxs — G8; assignment_ref — H8)
FullRangeExhaustNoSolution         → TemplateRefresh, RoundAbort
TemplateRefresh                    → CloseTemplateAssignments, TemplateCommit, CreatePendingAssignment, StartWake
RoundAbort                         → CloseRoundAssignments     # G8 (dispositions live ctxs, clears registries)
```

## Required-property proofs

1. **No dangling calls.** Every called/scheduled name resolves to a defined procedure (42 defined; 0
   called-but-undefined). The defined-but-never-called-by-a-procedure names —
   `RoundInitialise`, `MinerRegister`, `ReserveActivate`, `LeaseExpiry`, `FullRangeExhaustNoSolution`,
   `ActiveHashRateUpdate`, `AdversarialParticipationChangeEvent`, `AcceptanceBatchFinalize`,
   `FinalizeTimestampSecurityCensus` — are exactly the sim-driver / loop-microphase entry points
   (the last two are dispatched by the loop's microphases 4 and 5, not by a procedure).

2. **Single settled-census security evaluation (H3).** `SecurityFloorEvaluate` is a leaf reached
   ONLY via `FinalizeTimestampSecurityCensus → SecurityFloorEvaluate`. `ApplyMinerStateTransition`
   and `HandlePropagationFailure` no longer schedule it; they set
   `security_evaluation_required[(event_time, delta_cycle)]`. One `FinalizeTimestampSecurityCensus`
   runs per settled `(event_time, delta_cycle)` in microphase 5, so no per-transition floor decision
   exists and no intermediate census can drive recovery.

3. **Single state writer (F6), single residency owner (H7/I19).** `ApplyMinerStateTransition` is the
   ONLY writer of `miner_state` and the SOLE owner of `residency_ledger` (every `t_<state>` incl
   `t_ACTIVE_HASHING = t_hash`). `MinerRegister`, `ExhaustionAdjudicate`, `EnterLowPowerListen`,
   `StartWake`, `WakeCompleteEvent`, `AdversarialParticipationChangeEvent`, `CloseRoundAssignments`,
   `CloseTemplateAssignments` all reach it (0 direct mutations). `HashWorkEvent` records metadata only
   and adds no residency (0 duration).

4. **State-specific adversarial change through the hook (H6).**
   `AdversarialParticipationChangeEvent → {ApplyMinerStateTransition, RangeAssign,
   CreatePendingAssignment, StartWake, ResumeFromPause}`. Entry uses a legal per-state edge
   (`RangeAssign` T3/T4 from REGISTERED/RESERVE; hook T17 then `RangeAssign` from OFFLINE;
   `ResumeFromPause` T30 for a still-PAUSED head; fresh `CreatePendingAssignment` + `StartWake` T10 for
   a post-closure LOW_POWER_LISTEN). Exit reaches `ApplyMinerStateTransition` (T11) after closing the
   CURRENT head. No path mutates the census directly.

5. **Register-then-finalize acceptance (G5), closure downstream of arbitration (H1).**
   `BlockAcceptancePoint` is a register-only leaf; `AcceptanceBatchFinalize` (one per timestamp,
   microphase 4) `→ {ValidateCandidate*, ValidBlockAccept, HandlePropagationFailure}`. Round closure
   (`ValidBlockAccept → CloseRoundAssignments`) is reached ONLY through `AcceptanceBatchFinalize` (or
   `RoundAbort`), never from a block-arrival directly. `ValidBlockAccept` accepts from
   `{SOLUTION_PROPAGATION, SECURITY_RECOVERY}`.

6. **Event-scheduled, non-blocking hashing (G9), explicit assignment_ref (H8).**
   `WakeCompleteEvent → StartHashing → ScheduleNextHashWork ⇒ HashWorkEvent`, and `HashWorkEvent →
   ScheduleNextHashWork` (one bounded unit/event). Every `EnterLowPowerListen` caller —
   `LeaseExpiry`, `EarlyStopVerify`, `ScheduleSolutionPropagation`, `CloseRoundAssignments`,
   `CloseTemplateAssignments` — passes an explicit `assignment_ref` (H8).

7. **Sole renewal path (G2), candidate lifecycle + cleanup (G6/G8).** `LeaseExpiry → RenewAssignment`
   (same-lineage atomic swap); `CreatePendingAssignment` builds only ORIGINAL/REASSIGNED fresh
   lineages. `ScheduleSolutionPropagation → CreatePropagationContext` (DISCOVERED) then advances the
   status; `ValidBlockAccept`, `RoundAbort`, `CloseRoundAssignments`, `CloseTemplateAssignments`
   disposition live contexts and clear the registries.

## Result

**PROCEDURE CALL GRAPH (Stage 1H): PASS** — all seven required reachability properties hold; the new
`FinalizeTimestampSecurityCensus` is the sole caller of `SecurityFloorEvaluate` (H3); the rewired
`AdversarialParticipationChangeEvent` (H6) reaches only legal per-state edges; no dangling reference
exists (42 defined, 0 undefined).
