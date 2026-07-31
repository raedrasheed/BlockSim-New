# Stage 1U — Procedure Call Graph

Extracted from `STAGE_01_PROTOCOL_PSEUDOCODE.md` (post-U1..U7). `→` is a direct `CALL`; `⇒` is a scheduled discrete
`event`. **Stage-1U additions:** the recovery-WORK path `ClassifyRecoveryWork` / `SeatRecoveryWork` /
`RecoveryWorkDueEvent` / `ApplyRecoveryWorkAfterEpilogue` (U1), and the named install-transaction procedures
`PrepareRecoveryAssignmentPlan` / `CommitRecoveryAssignmentPlan` / `RollbackRecoveryAssignmentPlan` (U5). **76
procedures/functions defined; 0 dangling** (net +7 vs Stage 1T). The name remains **PoCol**; the mechanism is **the
idle policy within PoCol**; the A1 baseline (`8.420833333 kWh`) is unchanged.

## New / changed edges (Stage 1U)

```
SecurityFloorEvaluate        → ClassifyRecoveryWork, SeatRecoveryWork          # U1: breach-before-deadline seats recovery WORK (not an outcome)
SeatRecoveryWork             ⇒ RecoveryWorkDueEvent                            # U1/U3: atomic seat (published only after a successful enqueue)
RecoveryWorkDueEvent         → CaptureSecurityCensusOnRecoveryDeadline(RECOVERY_WORK_DUE)   # U1/U4: records DUE + refreshes census; NO work
ProcessEventTime             → ApplyRecoveryCompletionAfterEpilogue, ApplyRecoveryAssignmentContinuationAfterEpilogue,
                               ApplyRecoveryWorkAfterEpilogue, FinalizePostRecoveryApplicationState   # U1: work hook in the canonical tail
ApplyRecoveryWorkAfterEpilogue → PrepareRecoveryAssignmentPlan, CommitRecoveryAssignmentPlan, RollbackRecoveryAssignmentPlan,
                               RoundAbort(recovery_finalising=true)            # U1/U5: performs WORK; NEVER marks RESTORED
ApplyRecoveryAssignmentContinuationAfterEpilogue → PrepareRecoveryAssignmentPlan, CommitRecoveryAssignmentPlan,
                               RollbackRecoveryAssignmentPlan, CompleteAssignmentPhase, SetRecoveryDecisionStatus, RoundAbort
                                                                              # U1/U4/U5: REDISTRIBUTION-ONLY; reserve-dependent ELSE removed
CommitRecoveryAssignmentPlan → ReserveActivate, RangeReassign, RangeAssign, StartWake   # U2: threads scheduling_context to every nested wake
ReserveActivate              → CreatePendingAssignment, StartWake             # U2: scheduling_context threaded to StartWake -> ScheduleEvent
StartWake                    → ApplyMinerStateTransition, ScheduleEvent(post_epilogue_context)   # U2: pctx reaches ScheduleEvent; strictly-later
PrepareParticipantsForNewRound → CompleteAssignmentPhase                       # U6: captures assignment_phase_completed | assignment_phase_failed
TemplateRefresh              → CompleteAssignmentPhase                          # U6: captures the disposition; rollback/abort on failure
RecoveryAssignmentContinuationDueEvent → CaptureSecurityCensusOnRecoveryDeadline(RECOVERY_CONTINUATION_DUE)   # U7: distinct provenance
CancelActiveRecoveryEpisode  → SetRecoveryDecisionStatus                        # U1/U4: also cancels the in-flight RecoveryWorkDueEvent + consumes due facts
```

The remainder of the graph is unchanged from Stage 1T (see `STAGE_01T_PROCEDURE_CALL_GRAPH.md`): the run-level driver
`RunEventLoopToHorizon → {ProcessEventTime, FinalizeSimulationRun}`, the completion two-step
(`RecoveryCompletionDueEvent` + `ApplyRecoveryCompletionAfterEpilogue → CompleteSecurityRecovery`), the single
`ASSIGNMENT → HASHING` owner `CompleteAssignmentPhase`, and the recovery-census versioning.

## Entry points

**Run-level drivers / hooks (NOT queued events):** `RunInitialise`, `RunEventLoopToHorizon`, `ProcessEventTime`
(sole event-loop driver), `CloseRoundAtHorizon`, `ApplyRecoveryCompletionAfterEpilogue`,
`ApplyRecoveryAssignmentContinuationAfterEpilogue`, `ApplyRecoveryWorkAfterEpilogue` (U1, post-epilogue recovery
work), `FinalizePostRecoveryApplicationState`, `FinalizeSimulationRun`. **Internal helpers (not entry points):**
`CommitSecurityCensus`, `SettleSecurityCensusDirty`, `CommitRecoveryCensus`, `ReconcilePendingRecoveryDecisions`,
`SeatRecoveryCompletion`, `SetRecoveryDecisionStatus`, `CancelActiveRecoveryEpisode`, `CompleteSecurityRecovery`,
`ClassifyRecoveryWork` (U1), `SeatRecoveryWork` (U1), `PrepareRecoveryAssignmentPlan` /
`CommitRecoveryAssignmentPlan` / `RollbackRecoveryAssignmentPlan` (U5), `outcome_consistent_with_census`. **Queued
driver entry points / handlers (§0.7g-driver):** …`RecoveryCompletionDueEvent`,
`RecoveryAssignmentContinuationDueEvent`, `RecoveryWorkDueEvent` (U1), `RoundAbort`, plus the ordinary handlers.

## Required-property proofs

1. **No dangling calls.** Every called / scheduled name resolves to a defined procedure (76 defined; 0 undefined). A
   mechanical extraction reports only the prose false positives `is` and `this`. `ReserveActivate` (which lost its
   Stage-1T caller when the reserve-dependent continuation ELSE was removed) is now called by
   `CommitRecoveryAssignmentPlan` (U2/U5), so it has a live caller again.

2. **Recovery work is separate from the outcome (U1).** `SecurityFloorEvaluate` → `ClassifyRecoveryWork` /
   `SeatRecoveryWork` → `RecoveryWorkDueEvent` → `ApplyRecoveryWorkAfterEpilogue`; none marks a decision APPLIED or
   sets `recovery_outcome_finalised`. The reserve-dependent RESTORED continuation ELSE is removed.

3. **Post-epilogue context threading (U2).** `ApplyRecoveryWorkAfterEpilogue` / `ApplyRecoveryAssignmentContinuationAfterEpilogue`
   → `CommitRecoveryAssignmentPlan(POST_EPILOGUE(pctx))` → `ReserveActivate` / `RangeReassign` / `StartWake` →
   `ScheduleEvent(post_epilogue_context)`.

4. **Atomic re-arm (U3).** `SeatRecoveryWork` advances `recovery_work_seq` and publishes the work reference only after
   `ScheduleEvent` succeeds.

5. **Explicit due consumption (U4).** `RecoveryAssignmentContinuationDueEvent` / `RecoveryWorkDueEvent` set `DUE`; the
   post-epilogue hooks consume (CONSUMED/SUPERSEDED) and `CancelActiveRecoveryEpisode` cancels (CANCELLED);
   `ProcessEventTime` asserts on the explicit status.

6. **Named install transaction (U5).** `PrepareRecoveryAssignmentPlan` (compute-only) → `CommitRecoveryAssignmentPlan`
   → `RollbackRecoveryAssignmentPlan`; no opaque INSTALL/UNDO macro remains.

7. **Disposition at every CompleteAssignmentPhase caller (U6).** `PrepareParticipantsForNewRound`, `TemplateRefresh`,
   and `ApplyRecoveryAssignmentContinuationAfterEpilogue` each branch on the disposition.

8. **Distinct census provenance (U7).** `RecoveryAssignmentContinuationDueEvent` uses `RECOVERY_CONTINUATION_DUE`;
   `RecoveryWorkDueEvent` uses `RECOVERY_WORK_DUE`; both distinct from `RECOVERY_COMPLETION_DUE`.

## Result

**PROCEDURE CALL GRAPH (Stage 1U): PASS** — all eight required properties hold; the seven new procedures are correctly
wired; `ReserveActivate` regains a live caller; the signature changes (`StartWake`, `ReserveActivate`, `RangeReassign`,
`RangeAssign`, `CommitRecoveryAssignmentPlan`) have conforming call sites; no dangling reference exists (76 defined, 0
undefined). Documentation only; name remains PoCol; A1 baseline `8.420833333 kWh` unchanged; the prohibited
rebranded-algorithm-name variants are not used anywhere in this document.
