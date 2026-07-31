# Stage 1U — Semantic Test Vectors (TV163–TV173)

Paper test vectors for the reserve-recovery & continuation-liveness lock (U1–U7). Each vector names the EXACT
procedures, preconditions, and transitions in `STAGE_01_PROTOCOL_PSEUDOCODE.md`; no guard, transition, seating,
consumption, or classification is assumed that is not in the pseudocode. Name remains **PoCol**; the mechanism is
**the idle policy within PoCol**; the A1 baseline (`8.420833333 kWh`) is preserved by every vector (each is a
control-flow / scheduling / lifecycle / provenance check, never a change to how time or energy is counted).

---

## TV163 — A still-breached census before the deadline seats recovery WORK, not RESTORED (U1)

**Setup.** `SecurityFloorEvaluate` runs while `round_state = SECURITY_RECOVERY`; the FINAL census shows
`breach = true`, `deadline_reached = false`.
**Steps.**
1. The warranted outcome is `NONE` (`outcome_consistent_with_census(RESTORED)` is false — a breached census can never
   justify RESTORED; it is NOT weakened).
2. `ClassifyRecoveryWork` returns `RESERVE_ACTIVATION_REQUIRED`; `SeatRecoveryWork` seats ONE versioned
   `RecoveryWorkDueEvent`.
**Expected.** No `RESTORED` decision is treated as consistent; a versioned reserve-activation recovery-work action is
seated; the round stays `SECURITY_RECOVERY`. The recovery-work action is NOT a `RecoveryOutcome` and is never marked
APPLIED. A1 preserved.

## TV164 — A zero-latency post-epilogue reserve activation seats its wake strictly later (U2)

**Setup.** `ApplyRecoveryWorkAfterEpilogue` at `t` builds a `PostEpilogueSchedulingContext` (`source_event_time = t`)
and commits a `RESERVE_ACTIVATION_REQUIRED` plan; `wake_latency = 0`.
**Steps.**
1. `CommitRecoveryAssignmentPlan` (`scheduling_context = POST_EPILOGUE(pctx)`) calls `ReserveActivate`
   (`scheduling_context = ...`), which calls `StartWake` (`scheduling_context = POST_EPILOGUE(pctx)`).
2. `StartWake`'s POST_EPILOGUE branch computes `target = next_representable_simulation_time(t)` and calls
   `ScheduleEvent(..., post_epilogue_context = pctx)`.
**Expected.** `PostEpilogueSchedulingContext` is threaded through `ReserveActivate → StartWake → ScheduleEvent`; the
`WakeCompleteEvent` is seated at `next_representable_simulation_time(t)`, STRICTLY LATER than `t`, never at the drained
source time. A1 preserved.

## TV165 — A rejected re-arm advances nothing and reports no pending state (U3)

**Setup.** `SeatRecoveryWork` computes `candidate_seq`/`work_id` and `t_due <= T`; `ScheduleEvent` REJECTS the enqueue.
**Steps.**
1. `SeatRecoveryWork` does NOT advance `recovery_work_seq`, publishes NO `work_due_event_ref`, adds nothing to
   `pending_recovery_work`, records `recovery_work_schedule_rejected`, and returns `recovery_work_not_seated`.
**Expected.** The active identity/generation is not advanced, no false event reference is published, and no
`reserve_pending`/pending state is returned; the round stays `SECURITY_RECOVERY`. A1 preserved.

## TV166 — A continuation due fact at t is CONSUMED before ProcessEventTime finalises t (U4)

**Setup.** A branch-C continuation is DUE at `t` (`continuation_due_status = DUE`,
`continuation_due_at_event_time = t`); the census still warrants RESTORED and the version binds.
**Steps.**
1. `ApplyRecoveryAssignmentContinuationAfterEpilogue` applies the continuation and sets
   `continuation_due_status = CONSUMED` (on APPLIED) — or `SUPERSEDED`/`CANCELLED` on the other branches.
2. `ProcessEventTime`'s tail asserts `no recovery_decisions[*].continuation_due_status = DUE with
   continuation_due_at_event_time = t`.
**Expected.** The due fact's status is CONSUMED (not inferred from a timestamp) before `t` is finalised; the explicit
assertion holds. A1 preserved.

## TV167 — A re-arm target beyond T enqueues nothing and horizon closure governs (U3)

**Setup.** `SeatRecoveryWork` computes `t_due = t + configured_recovery_completion_delay` with `t_due > run_horizon_T`.
**Steps.**
1. `SeatRecoveryWork` records `recovery_work_horizon_deferred` and returns `recovery_work_horizon_deferred(episode)`
   WITHOUT calling `ScheduleEvent`.
**Expected.** No event is enqueued; no `APPLYING` decision is stranded without a controller (a recovery-work action is
not an APPLYING decision; the branch-C APPLYING decision is always resolved in one continuation-hook invocation);
`CloseRoundAtHorizon` governs run end. A1 preserved.

## TV168 — PrepareRecoveryAssignmentPlan detects an overlap before any mutation (U5)

**Setup.** `ApplyRecoveryWorkAfterEpilogue` (or the continuation hook) calls `PrepareRecoveryAssignmentPlan`; the
proposed specs would violate I1 (overlap).
**Steps.**
1. `PrepareRecoveryAssignmentPlan` (compute-only) verifies I1/I3/I10/I18b and returns
   `plan_invalid(reason = overlap_or_lineage_or_epoch_violation)`.
2. The caller consumes the due fact (`CONSUMED`) and records the plan-invalid disposition WITHOUT any mutation.
**Expected.** NO assignment, state transition, or wake event is created; the round stays `SECURITY_RECOVERY`
(recovery work) or the decision becomes `APPLY_FAILED` with the episode preserved (continuation). A1 preserved.

## TV169 — CommitRecoveryAssignmentPlan fails after partial creation; rollback cancels all (U5)

**Setup.** `CommitRecoveryAssignmentPlan` creates part of the plan (at least one assignment + wake), then a later
constructor fails.
**Steps.**
1. `CommitRecoveryAssignmentPlan` returns `install_failed_after_mutation(reason, rollback_record)`.
2. The caller calls `RollbackRecoveryAssignmentPlan(rollback_record)`, which cancels every plan `created_event` on EQ
   and closes every plan-created live head legally (I18b), restoring the ledgers, and returns `rollback_completed`.
**Expected.** All plan events are cancelled and every plan-created live head is closed; no live partial assignment
remains; the round returns to `SECURITY_RECOVERY` (episode preserved). A1 preserved.

## TV170 — A rollback failure after mutation aborts without fabricating UNRECOVERABLE (U5/T4)

**Setup.** `RollbackRecoveryAssignmentPlan` cannot remove a residual partial assignment.
**Steps.**
1. It returns `rollback_failed(reason = residual_partial_assignment)`.
2. The caller records `recovery_episode_disposition = RECOVERY_INSTALL_FAILED_ABORTED`, does NOT set
   `recovery_outcome_finalised`, and calls `RoundAbort(reason = recovery_install_failed_aborted,
   recovery_finalising = true)`.
**Expected.** The episode records `RECOVERY_INSTALL_FAILED_ABORTED`; NO `UNRECOVERABLE` outcome is fabricated;
`RoundAbort` closes the round. A1 preserved.

## TV171 — PrepareParticipantsForNewRound handles assignment_phase_failed (U6)

**Setup.** `PrepareParticipantsForNewRound` calls `CompleteAssignmentPhase`, which returns
`assignment_phase_failed(malformed_assignment_set)` BEFORE the irreversible `HASHING` transition (round still
`ASSIGNMENT`).
**Steps.**
1. It rolls back the just-created PENDING assignments + their wakes, records `participant_setup_failed`, and returns
   `participant_set_setup_failed(reason)`.
**Expected.** It does NOT return `participant_set_prepared` and does NOT leave an unhandled `ASSIGNMENT` state; the
failure is reversible. A1 preserved.

## TV172 — TemplateRefresh handles assignment_phase_failed (U6)

**Setup.** `TemplateRefresh` calls `CompleteAssignmentPhase`, which returns `assignment_phase_failed(reason)` before
the irreversible `HASHING` transition.
**Steps.**
1. It rolls back the refresh's just-created assignments + wakes and returns `template_refresh_failed(reason)`.
**Expected.** It follows its declared rollback/abort path and does NOT return a successful `new_TemplateID`
disposition with the round left in `ASSIGNMENT`. A1 preserved.

## TV173 — RecoveryCompletionDueEvent and RecoveryAssignmentContinuationDueEvent write distinct census sources (U7)

**Setup.** A `RecoveryCompletionDueEvent` fires at one `event_time`; a `RecoveryAssignmentContinuationDueEvent` fires
at another.
**Steps.**
1. `RecoveryCompletionDueEvent` refreshes the census with `census_source = RECOVERY_COMPLETION_DUE`.
2. `RecoveryAssignmentContinuationDueEvent` refreshes the census with `census_source = RECOVERY_CONTINUATION_DUE`.
**Expected.** The two recovery-timeline checkpoints write DISTINCT `census_source` values through the sole writer
`CommitSecurityCensus`, so "completion is due" and "continuation is due" are distinguishable provenances. A1
preserved.

---

## Coverage summary

| Vector | Correction | Exercises |
|--------|-----------|-----------|
| TV163 | U1 | breach-before-deadline seats recovery WORK; RESTORED never treated as consistent on a breached census |
| TV164 | U2 | zero-latency post-epilogue reserve wake threaded through ReserveActivate→StartWake→ScheduleEvent, strictly later |
| TV165 | U3 | rejected re-arm — no advance, no false ref, no reserve_pending |
| TV166 | U4 | continuation due fact CONSUMED before finalisation; assertion on explicit status |
| TV167 | U3 | re-arm beyond T — no enqueue, no stranded APPLYING, horizon governs |
| TV168 | U5 | Prepare detects overlap before mutation — nothing created |
| TV169 | U5 | Commit fails after partial creation — Rollback cancels all events + closes heads |
| TV170 | U5/T4 | Rollback fails — RECOVERY_INSTALL_FAILED_ABORTED + RoundAbort, no fabricated UNRECOVERABLE |
| TV171 | U6 | PrepareParticipantsForNewRound handles assignment_phase_failed — no unhandled ASSIGNMENT |
| TV172 | U6 | TemplateRefresh handles assignment_phase_failed — no successful new-template disposition |
| TV173 | U7 | completion-due vs continuation-due write distinct census_source values |

All eleven vectors pass on paper against the exact named procedures. No new consensus feature; documentation only;
name remains PoCol; the A1 baseline `8.420833333 kWh` is unchanged. The prohibited rebranded-algorithm-name variants
are not used anywhere in this document.
