# Stage 1V — Semantic Test Vectors (TV174–TV185)

Paper test vectors for the recovery-work transaction & liveness lock (V1–V9). Each vector names the EXACT procedures,
preconditions, dispositions, and transitions in `STAGE_01_PROTOCOL_PSEUDOCODE.md`; no guard, transition, seating,
consumption, classification, or rollback is assumed that is not in the pseudocode. The protocol name remains **PoCol**;
the mechanism is **the idle policy within PoCol**; the A1 baseline (`8.420833333 kWh`) is preserved by every vector
(each is a control-flow / scheduling / transaction / lifecycle / provenance check, never a change to how time or energy
is counted).

Each vector lists **Setup**, **Steps** (the pseudocode path exercised), and **Expected** (the observable disposition
that must hold). A vector *passes* iff the named procedures produce exactly the stated disposition.

---

## TV174 — A DUE recovery-work record orphaned by a census-version advance is REBOUND, not replaced (V1)

**Setup.** `round_state = SECURITY_RECOVERY`, episode `E`. A recovery-work record `W1 = (E, k)` is `DUE` at the current
`event_time = t` (`W1.due_status = DUE`, `W1.due_at_event_time = t`), bound to `RecoveryCensusVersion = v1`. The epilogue
`SecurityFloorEvaluate` runs at `t`; `CommitRecoveryCensus` publishes a NEW final census `v2` that STILL shows
`breach = true`, `deadline_reached = false`.
**Steps.**
1. `SecurityFloorEvaluate` calls `CommitRecoveryCensus` (→ `v2`), then `ReconcilePendingRecoveryDecisions`, then
   `ReconcilePendingRecoveryWork(RoundContext, E, v2, t)` — BEFORE it considers `SeatRecoveryWork`.
2. In `ReconcilePendingRecoveryWork`, `W1.due_status = DUE AND W1.due_at_event_time = t`; `still_warranted` is true
   (`census.breach = true`, `census.deadline_reached = false`, `ClassifyRecoveryWork ≠ NONE`).
3. It sets `recovery_work[W1.work_id].bound_census_version <- v2` (SAME `RecoveryWorkID`) and returns
   `recovery_work_reconciled_rebound(W1.work_id, v2)`. No second work record `W2` is seated.
4. In the same epilogue, `SeatRecoveryWork` observes `W0.status = DUE AND W0.due_at_event_time = t` and returns
   `recovery_work_already_pending(W0.action)` (V1 non-replacement guard) — it does NOT seat over the DUE record.
5. `ApplyRecoveryWorkAfterEpilogue(t)` finds `W1.due_status = DUE`, `W1.due_at_event_time = t`,
   `W1.bound_census_version = v2 = census.RecoveryCensusVersion` → performs the work and CONSUMES the due fact.
**Expected.** Exactly one `RecoveryWorkID` (`W1`) exists across the version advance; it is rebound to `v2` (no `W2`), is
consumable by the post-epilogue hook, and the `ProcessEventTime` finalisation assertion (no work record left `due_status
= DUE` at a finalised `t`) passes. A1 preserved.

## TV175 — A DUE recovery-work record no longer warranted becomes SUPERSEDED and the outcome path governs (V1)

**Setup.** As TV174, but the new final census `v2` shows the breach has cleared (`breach = false`) — a same-time
`WakeCompleteEvent` restored the floor. `W1` is `DUE` at `t` under `v1`.
**Steps.**
1. `ReconcilePendingRecoveryWork(RoundContext, E, v2, t)` evaluates `still_warranted` = false
   (`census.breach = false`).
2. It sets `recovery_work[W1.work_id].status <- SUPERSEDED`, `due_status <- SUPERSEDED`, cancels
   `W1.work_due_event_ref` if still pending on `EQ`, sets `pending_recovery_work[E] <- null`, and returns
   `recovery_work_reconciled_superseded(W1.work_id)`.
3. `SecurityFloorEvaluate` computes `warranted = RESTORED` (from `NOT census.breach`) and calls `SeatRecoveryCompletion`.
**Expected.** The no-longer-warranted DUE record is SUPERSEDED (a terminal disposition) with its queued event cancelled;
no work is applied; the ordinary completion two-step mints `RESTORED`. No work record is left `DUE`. A1 preserved.

## TV176 — Every StartWake call passes an explicit SchedulingSourceContext, with no alias-based call (V2)

**Setup.** The full pseudocode is scanned for every `CALL StartWake(...)` site: `ReserveActivateFromPlan`,
`CommitRecoveryAssignmentPlan` (redistribution branch), `PrepareParticipantsForNewRound` (four cases),
`TemplateRefresh` (activation loop), and `ResumeFromPause`.
**Steps.**
1. Each site passes `scheduling_context = ORDINARY_DISPATCH(dispatch_envelope)` (dispatched entry points) or
   `scheduling_context = POST_EPILOGUE(pctx)` (post-epilogue install paths) EXPLICITLY.
2. `StartWake`'s preconditions bind `dispatch_envelope <- (ORDINARY_DISPATCH(e) ? e : scheduling_context.pctx.source_envelope)`;
   there is NO bare-envelope alias / implicit ORDINARY_DISPATCH conversion (the Stage-1U alias prose is withdrawn).
**Expected.** Zero `StartWake` call sites rely on an implicit conversion; each passes exactly one of the two
`SchedulingSourceContext` variants. A grep for the withdrawn alias language returns nothing. A1 preserved.

## TV177 — A post-epilogue zero-latency wake seats strictly later and returns actual references (V3)

**Setup.** `ReserveActivateFromPlan` is called from `CommitRecoveryAssignmentPlan` with
`scheduling_context = POST_EPILOGUE(pctx)`, `pctx.source_event_time = t`; `StartWake` samples `wake_latency = 0`.
**Steps.**
1. `StartWake`'s POST_EPILOGUE branch sets `target_time <- next_representable_simulation_time(t)` (strictly later than
   `t`, since `wake_latency = 0`), then `ScheduleEvent(..., post_epilogue_context = pctx)` returns `scheduled(...)`.
2. `StartWake` reads `wake_event_ref <- seat.event_ref`, applies the `WAKING` transition (succeeds), publishes
   `wake_event_ref_of(target_assignment)`, and returns
   `wake_seated(AssignmentID, WakeEventRef, wake_target_time = next_representable_simulation_time(t), resulting_state = WAKING)`.
**Expected.** The returned disposition is `wake_seated(...)` carrying the ACTUAL `AssignmentID`, `WakeEventRef`, and a
`wake_target_time` STRICTLY LATER than `t`; the `WakeCompleteEvent` is never seated at the drained source time. A1
preserved.

## TV178 — A rejected/failed wake never leaves a miner WAKING without a live WakeCompleteEvent (V3, V4)

**Setup.** Two sub-cases inside `ReserveActivateFromPlan` after `CreatePendingAssignment` produced a PENDING head:
(a) `StartWake`'s `ScheduleEvent` REJECTS the enqueue; (b) `ScheduleEvent` succeeds but `ApplyMinerStateTransition` to
`WAKING` fails.
**Steps.**
1. Case (a): `StartWake` returns `wake_schedule_failed_before_transition(reason)`; the miner is UNCHANGED (still
   `RESERVE`), nothing seated.
2. Case (b): `StartWake` cancels the seated `wake_event_ref` on `EQ` and returns
   `wake_transition_failed_after_seat(reason, WakeEventRef)`; the miner is left in `from_state`, NOT `WAKING`.
3. `ReserveActivateFromPlan` (both cases) CLOSES the PENDING assignment as `CLOSED`/`revoked`, restores the coverage /
   custody ledgers, asserts `miner_state(reserve_miner) = RESERVE`, and returns
   `reserve_activation_failed_after_assignment(reason, AssignmentID, rollback_record)`.
**Expected.** No miner is left `WAKING` without a live `WakeCompleteEvent`; the PENDING assignment is closed legally
(never left dangling); the reserve miner stays `RESERVE`. A1 preserved.

## TV179 — CommitRecoveryAssignmentPlan activates exactly the plan-selected miner/range/provenance (V5)

**Setup.** `PrepareRecoveryAssignmentPlan` produced a plan whose sole spec is
`{ kind = RESERVE_ACTIVATION, MinerID = m, range = r, origin = REASSIGNED, source_assignment = s, required_wake_operations }`.
**Steps.**
1. `CommitRecoveryAssignmentPlan` iterates the spec and calls
   `ReserveActivateFromPlan(reserve_miner = m, candidate_range = r, assignment_origin = REASSIGNED,
   source_assignment = s, scheduling_context = POST_EPILOGUE(pctx))` — NO independent `SELECT` of a miner or range.
2. `ReserveActivateFromPlan` REVALIDATES the exact `(m, r, REASSIGNED)` spec against I1/I3/I10/I18b before mutation,
   then `CreatePendingAssignment(RoundContext, m, r, assignment_origin = REASSIGNED, source_assignment = s, ...)`.
**Expected.** The committed activation uses exactly `m`, `r`, `REASSIGNED`, `s` from the validated plan; a committed
reserve activation equals its prepared-and-validated plan (no divergence via re-selection). A1 preserved.

## TV180 — A reserve-activation rollback record holds the ACTUAL returned references (V4)

**Setup.** `CommitRecoveryAssignmentPlan` commits a two-spec plan: spec 1 (`RESERVE_ACTIVATION`) succeeds returning
`reserve_activation_committed(mid1, aid1, aver1, wref1)`; spec 2 fails after mutation.
**Steps.**
1. On spec 1, `CommitRecoveryAssignmentPlan` adds the ACTUAL `aid1` to `created_assignments` and the ACTUAL `wref1` to
   `created_events`.
2. On spec 2's `install_failed_after_mutation` (or a `wake_seated`-absent StartWake disposition), it builds
   `plan.rollback_metadata <- rollback_record(RecoveryInstallID = plan.RecoveryInstallID,
   created_assignments = {aid1, ...}, created_events = {wref1, ...})` and returns
   `install_failed_after_mutation(reason, plan.rollback_metadata)`.
3. `RollbackRecoveryAssignmentPlan(rollback_record)` cancels each `created_events` ref (e.g. `wref1`) first, then closes
   each `created_assignments` head (e.g. `aid1`) legally.
**Expected.** The rollback record contains the ACTUAL `AssignmentID`/`WakeEventRef` values the activation transactions
returned (never undefined/placeholder fields); rollback finds and reverts exactly those references. A1 preserved.

## TV181 — A breach repairable only by same-active-miner redistribution has no security-floor recovery action (V6)

**Setup.** `round_state = SECURITY_RECOVERY`; the FINAL census shows `breach = true`, `deadline_reached = false`; there
is NO reserve miner that can be activated and NO declared honest/adversarial participation replacement — the only
available coverage move is a redistribution AMONG the SAME `ACTIVE_HASHING` miners.
**Steps.**
1. `ClassifyRecoveryWork(RoundContext, E, census)` finds no census-changing action available and returns `NONE`
   (`RANGE_REDISTRIBUTION_REQUIRED` is REMOVED from `ClassifyRecoveryWork`).
2. `SecurityFloorEvaluate` therefore returns `recovery_pending(census.RecoveryCensusVersion)` — it seats NO recovery
   work; the round stays `SECURITY_RECOVERY`.
**Expected.** No `SECURITY_FLOOR_RECOVERY_WORK` action is seated that would falsely claim to change
`H_active`/`H_honest`/`q_adv`; a same-active-miner redistribution is classified as `COVERAGE_REPAIR_WORK` and does not
control the breach-before-deadline outcome logic. A1 preserved.

## TV182 — An older ARMED work record is atomically re-affirmed or superseded — never two live in-flight (V1, V7)

**Setup.** A recovery-work record `W1 = (E, k)` is `ARMED` for a FUTURE `RecoveryWorkDueEvent` (not due at the current
`t`), bound to `v1`. The epilogue at `t` publishes a newer census `v2`.
**Steps.**
1. `ReconcilePendingRecoveryWork` reaches the `W.status = ARMED` branch. If `still_warranted`, it sets
   `bound_census_version <- v2` (SAME identity) and returns `recovery_work_reconciled_reaffirmed(W1.work_id, v2)`;
   otherwise it sets `status <- SUPERSEDED`, `due_status <- SUPERSEDED`, cancels the queued event, clears
   `pending_recovery_work[E]`, and returns `recovery_work_reconciled_superseded(W1.work_id)`.
2. If `SeatRecoveryWork` is later reached with a STALE prior in-flight record (older version, not DUE-at-`t`), it
   ATOMICALLY sets `W0.status <- SUPERSEDED`, consumes its due fact, cancels `W0.work_due_event_ref`, and clears
   `pending_recovery_work[E]` BEFORE publishing the replacement.
**Expected.** At most one work record per episode is ever in `{ARMED, DUE, APPLYING}`; the stale record is superseded /
cancelled atomically before any replacement is published — two live in-flight records never coexist. A1 preserved.

## TV183 — Terminal closure cancels EVERY nonterminal work record, not only the pending pointer (V7)

**Setup.** Episode `E` has `pending_recovery_work[E] = Wb`, and ALSO a second nonterminal record `Wa` (status `ARMED`,
e.g. left after a prior seating race) whose `work_id` is not the current `pending_recovery_work` pointer. The round
becomes terminal (`ROUND_ACCEPTED` / `ROUND_ABORTED`) with the episode still active and `recovery_finalising = false`.
**Steps.**
1. `CloseRoundAssignments` calls `CancelActiveRecoveryEpisode`.
2. Its work loop iterates `FOR EACH work_id in recovery_work WHERE episode = E AND status in
   {CREATED, ARMED, DUE, APPLYING}` — covering BOTH `Wa` and `Wb`. For each it cancels `work_due_event_ref` (if pending
   on `EQ`), sets `status <- CANCELLED`, and (if `due_status = DUE`) sets `due_status <- CANCELLED`.
3. It sets `pending_recovery_work[E] <- null`, records `TERMINAL_CANCELLED`, and clears `current_recovery_episode`.
**Expected.** No `ARMED`/`DUE`/`APPLYING` work record survives terminal closure — including a record NOT referenced by
`pending_recovery_work`; no orphan queued `RecoveryWorkDueEvent` remains on `EQ`. A1 preserved.

## TV184 — PrepareParticipantsForNewRound rolls back a failed setup and takes an explicit liveness path (V8)

**Setup.** `PrepareParticipantsForNewRound` runs at the new round's `ASSIGNMENT`; it captured each `StartWake` result
into `participant_setup_txn` (wakes, created_assignments, prior_states). Then `CompleteAssignmentPhase` returns
`assignment_phase_failed(reason)` (round still `ASSIGNMENT`, reversible).
**Steps.**
1. It calls `RollbackParticipantSetup(RoundContext, participant_setup_txn)`, which cancels the CAPTURED `WakeEventRefs`
   first, closes each created PENDING head legally, restores the ledgers, and (via `ApplyMinerStateTransition`) restores
   any miner left `WAKING` to its captured prior state — returning `rollback_completed`.
2. If a setup retry is warranted and `next_representable_simulation_time(dispatch_envelope.event_time) <= run_horizon_T`,
   it seats `SetupRetryEvent` (`setup_kind = PARTICIPANT_SETUP`) at that strictly-later time (`ROUND_SETUP` microphase)
   and returns `participant_set_setup_retry_seated(setup_reason)`; otherwise it returns
   `RoundAbort(..., participant_setup_failed(setup_reason), recovery_finalising = false)`. (A `rollback_failed`
   escalates directly to a declared `RoundAbort`.)
**Expected.** After a failed setup no participant remains `WAKING` for a rolled-back head and no created wake stays live
on `EQ`; the round is NEVER stranded in `ASSIGNMENT` with no controller — it deterministically retries or aborts. A1
preserved.

## TV185 — TemplateRefresh rolls back a failed refresh and executes a declared retry/abort path (V8)

**Setup.** `TemplateRefresh` built the new template, created fresh ORIGINAL PENDING heads for eligible miners, and
assembled `refresh_setup_txn` from the ACTUAL `WakeEventRef`s its `StartWake` transactions returned. Then
`CompleteAssignmentPhase` returns `assignment_phase_failed(reason)` (round still `ASSIGNMENT`).
**Steps.**
1. It calls `RollbackTemplateRefreshSetup(RoundContext, refresh_setup_txn)` — identical discipline to
   `RollbackParticipantSetup`: cancel captured wakes, close created heads legally, restore ledgers, verify none `WAKING`.
2. On `rollback_completed`: if a refresh retry is warranted within the horizon it seats `SetupRetryEvent`
   (`setup_kind = TEMPLATE_REFRESH_SETUP`) and returns `template_refresh_retry_seated(reason)`; otherwise it returns
   `RoundAbort(..., template_refresh_failed(reason), recovery_finalising = false)`. A `rollback_failed` escalates to a
   declared `RoundAbort`.
**Expected.** A failed template refresh leaves no live partial assignment and no orphan wake; the round takes an
explicit declared liveness path (retry or abort), never returning a successful `new_TemplateID` while still in
`ASSIGNMENT`. A1 preserved.

---

## Coverage map

| Vector | Correction | Primary procedures exercised |
|--------|-----------|------------------------------|
| TV174  | V1        | `SecurityFloorEvaluate`, `ReconcilePendingRecoveryWork`, `SeatRecoveryWork`, `ApplyRecoveryWorkAfterEpilogue` |
| TV175  | V1        | `ReconcilePendingRecoveryWork`, `SeatRecoveryCompletion` |
| TV176  | V2        | `StartWake` (all call sites), `SchedulingSourceContext` |
| TV177  | V3        | `StartWake`, `ScheduleEvent`, `ReserveActivateFromPlan` |
| TV178  | V3/V4     | `StartWake`, `ReserveActivateFromPlan` |
| TV179  | V5        | `PrepareRecoveryAssignmentPlan`, `CommitRecoveryAssignmentPlan`, `ReserveActivateFromPlan` |
| TV180  | V4        | `CommitRecoveryAssignmentPlan`, `RollbackRecoveryAssignmentPlan` |
| TV181  | V6        | `ClassifyRecoveryWork`, `SecurityFloorEvaluate` |
| TV182  | V1/V7     | `ReconcilePendingRecoveryWork`, `SeatRecoveryWork` |
| TV183  | V7        | `CancelActiveRecoveryEpisode`, `CloseRoundAssignments` |
| TV184  | V8        | `PrepareParticipantsForNewRound`, `RollbackParticipantSetup`, `SetupRetryEvent` |
| TV185  | V8        | `TemplateRefresh`, `RollbackTemplateRefreshSetup`, `SetupRetryEvent` |

All twelve vectors are control-flow / scheduling / transaction / lifecycle / provenance checks over named procedures in
`STAGE_01_PROTOCOL_PSEUDOCODE.md`; none alters the energy or time accounting, so the A1 baseline `8.420833333 kWh` is
preserved by every vector.
