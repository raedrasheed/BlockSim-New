# Stage 1V — Correction Report (Recovery-Work Transaction & Liveness Lock)

**Scope.** A documentation-only revision of the Stage-1 formal specification of PoCol ("the idle policy within PoCol")
that hardens the recovery-**work** path and the ordinary round-setup path into explicit, executable **transactions**
with structured dispositions and named rollback/liveness continuations. It corrects nine defects (V1–V9) identified in
the independent final-acceptance review of Stage 1U. This stage changes only the normative Stage-1 documents; it does
NOT change how time or energy are counted, so the A1 baseline (`8.420833333 kWh`) is preserved.

**Branch.** `thesis-v45-pocol-stage1v-recovery-work-transaction-liveness-lock` (parent `a8217fe`).

**Invariant of the whole stage.** Every scheduling call carries an EXPLICIT `SchedulingSourceContext`; every
wake/activation/setup is a TRANSACTION that returns a named disposition (never a boolean); every in-flight recovery-work
record has a COMPLETE lifecycle with exactly one live-or-terminal disposition; and no failure path leaves a miner
`WAKING` without a live `WakeCompleteEvent` or a round stranded with no controller.

---

## V1 — Reconcile in-flight recovery WORK before seating new work

**Defect.** While in `SECURITY_RECOVERY`, a recovery-work record already `DUE` at the current `event_time` under census
version `v1` could be orphaned when the epilogue published a newer final census `v2`: the old code path could seat a
*second* work record, stranding the `DUE` record (`due_status = DUE`) so `ApplyRecoveryWorkAfterEpilogue` never consumed
it — failing the `ProcessEventTime` finalisation assertion.

**Correction.** A new procedure `ReconcilePendingRecoveryWork(RoundContext, episode, latest_census_version, event_time)`
runs inside `SecurityFloorEvaluate` AFTER `CommitRecoveryCensus` and `ReconcilePendingRecoveryDecisions` and BEFORE any
`SeatRecoveryWork` consideration. It:
- REBINDS a still-warranted `DUE` record to the latest census version — SAME `RecoveryWorkID`, no replacement — so the
  post-epilogue hook can consume it (`recovery_work_reconciled_rebound`);
- SUPERSEDES a no-longer-warranted `DUE` record and cancels its queued event (`recovery_work_reconciled_superseded`),
  letting the outcome path govern;
- RE-AFFIRMS or SUPERSEDES an `ARMED` future record, never leaving two live in-flight.

`SeatRecoveryWork` is amended to NEVER replace a `DUE` record at the current `event_time` (that responsibility now
belongs solely to `ReconcilePendingRecoveryWork`).

**Where.** `STAGE_01_PROTOCOL_PSEUDOCODE.md`: `ReconcilePendingRecoveryWork` (new); `SecurityFloorEvaluate`
SECURITY_RECOVERY branch (call ordering); `SeatRecoveryWork` non-replacement guard.

## V2 — One explicit SchedulingSourceContext at every call site

**Defect.** Stage 1U permitted "a bare `dispatch_envelope` is read as `ORDINARY_DISPATCH`" — an implicit alias that made
the scheduling source ambiguous, affecting zero-latency target-time computation and post-epilogue causality.

**Correction.** The alias is WITHDRAWN. `SchedulingSourceContext` is a closed two-variant type
`{ ORDINARY_DISPATCH(dispatch_envelope), POST_EPILOGUE(PostEpilogueSchedulingContext) }`, and EVERY scheduling-bearing
call — `StartWake`, `ReserveActivate` / `ReserveActivateFromPlan`, `RangeAssign`, `RangeReassign`,
`CommitRecoveryAssignmentPlan`, and every direct `StartWake` caller — passes it EXPLICITLY.

**Where.** `StartWake` preconditions; `PrepareParticipantsForNewRound`, `TemplateRefresh`, `ResumeFromPause`,
`ReserveActivate`, `CommitRecoveryAssignmentPlan` call sites (all pass `ORDINARY_DISPATCH(dispatch_envelope)` or
`POST_EPILOGUE(pctx)`).

## V3 — StartWake is a transaction with explicit structured outputs

**Defect.** `StartWake` could return an ambiguous boolean and could leave a miner `WAKING` with no live
`WakeCompleteEvent` (or seat a wake without a transition).

**Correction.** `StartWake` is a TRANSACTION returning exactly one of
`wake_seated(AssignmentID, WakeEventRef, wake_target_time, resulting_state = WAKING)` |
`wake_schedule_failed_before_transition(reason)` | `wake_transition_failed_after_seat(reason, WakeEventRef)`.
Canonical order: (1) sample latency; (2) compute the target from the `SchedulingSourceContext` (a POST_EPILOGUE
zero-latency wake targets `next_representable_simulation_time(source)`, strictly later); (3) validate + `ScheduleEvent`
to SEAT the `WakeCompleteEvent`; (4) ONLY after a successful seat, apply the `WAKING` transition; (5) if the transition
fails after the seat, CANCEL the seated event; (6) publish the `WakeEventRef`; (7) return `wake_seated`. No failure
leaves `miner_state = WAKING` without a live `WakeCompleteEvent`.

**Where.** `StartWake` (rewritten as a numbered transaction).

## V4 — ReserveActivate returns actual transaction references

**Defect.** Reserve activation returned success/placeholder values instead of the real `AssignmentID`/
`assignment_version`/`WakeEventRef`, and a post-assignment wake failure left inconsistent state.

**Correction.** `ReserveActivate` (which now SELECTs then delegates) and the new plan-bound `ReserveActivateFromPlan`
return `reserve_activation_committed(MinerID, AssignmentID, assignment_version, WakeEventRef)` |
`reserve_activation_failed_before_mutation(reason)` |
`reserve_activation_failed_after_assignment(reason, AssignmentID, rollback_record)`. On a wake-seat failure AFTER a
PENDING assignment was created, the assignment is closed legally (`CLOSED`/`revoked`), ledgers restored, and the reserve
miner asserted to remain `RESERVE`; the `rollback_record` is built from the ACTUAL returned references.

**Where.** `ReserveActivate` (delegation + V4 RETURNS); `ReserveActivateFromPlan` (new); `CommitRecoveryAssignmentPlan`
(captures actual refs into `created_assignments`/`created_events`).

## V5 — Commit exactly the prepared plan

**Defect.** `CommitRecoveryAssignmentPlan` re-`SELECT`ed the miner/range independently, so what was committed could
diverge from what was prepared and validated.

**Correction.** The commit consumes the EXACT prepared specs. Each spec carries
`{ kind, MinerID, range, origin, source_assignment, required_wake_operations }`; the `RESERVE_ACTIVATION` branch calls
`ReserveActivateFromPlan(reserve_miner = spec.MinerID, candidate_range = spec.range, assignment_origin = spec.origin,
source_assignment = spec.source_assignment, scheduling_context = ...)` — NO independent `SELECT` — and revalidates the
exact specs (I1/I3/I10/I18b) immediately before mutation.

**Where.** `PrepareRecoveryAssignmentPlan` (spec fields); `CommitRecoveryAssignmentPlan` (plan-bound activation).

## V6 — Separate hash-rate recovery from coverage repair

**Defect.** Range redistribution among the SAME active miners was conflated with security-floor hash-rate recovery, so
a coverage-only repair could masquerade as a census-changing, breach-relevant action.

**Correction.** `RECOVERY_WORK_CLASS in { SECURITY_FLOOR_RECOVERY_WORK, COVERAGE_REPAIR_WORK }`:
- `SECURITY_FLOOR_RECOVERY_WORK` — actions that can CHANGE the `ACTIVE_HASHING` census (`H_active`/`H_honest`/`q_adv`):
  reserve activation or a declared honest/adversarial participation replacement;
- `COVERAGE_REPAIR_WORK` — nonce-domain coverage repair that makes NO claim on the census and exerts NO control over the
  breach outcome.

`ClassifyRecoveryWork` returns only `{ RESERVE_ACTIVATION_REQUIRED, NONE }`; `RANGE_REDISTRIBUTION_REQUIRED` is removed
from the security-floor path. Redistribution after a no-breach census stays branch-C redistribution-only
(`COVERAGE_REPAIR_WORK`). Plan specs are tagged with the class.

**Where.** §0.8 registries (`RECOVERY_WORK_CLASS`, `work_record.work_class`); `ClassifyRecoveryWork`;
`PrepareRecoveryAssignmentPlan` (spec tagging); `SeatRecoveryWork` INPUTS (RESERVE-only).

## V7 — Complete recovery-work lifecycle

**Defect.** The work record had no complete status model, and the episode-cancel path only touched the single
`pending_recovery_work` pointer — potentially leaving other nonterminal work records and their queued events live.

**Correction.** `RECOVERY_WORK_STATUS in
{ CREATED, ARMED, DUE, APPLYING, CONSUMED, SUPERSEDED, SCHEDULE_FAILED, HORIZON_DEFERRED, CANCELLED }`. Invariants:
exactly one live-or-terminal disposition per `RecoveryWorkID`; at most one record per episode in `{ARMED, DUE, APPLYING}`;
a new record atomically SUPERSEDES/cancels any prior in-flight BEFORE publishing. `ApplyRecoveryWorkAfterEpilogue` sets
`APPLYING` when the work transaction runs. `CancelActiveRecoveryEpisode` iterates ALL nonterminal work records
(`status in {CREATED, ARMED, DUE, APPLYING}`), not only `pending_recovery_work`.

**Where.** §0.8 registries (`RECOVERY_WORK_STATUS`, at-most-one invariant); `SeatRecoveryWork` (atomic supersede);
`ApplyRecoveryWorkAfterEpilogue` (`APPLYING`); `CancelActiveRecoveryEpisode` (iterate all nonterminal).

## V8 — Executable ordinary assignment-setup rollback + retry liveness

**Defect.** Ordinary round-setup failure had no NAMED executable rollback and no explicit liveness continuation — a
failed setup could orphan wake events / half-created assignments and stall the round.

**Correction.** Two NAMED procedures `RollbackParticipantSetup` and `RollbackTemplateRefreshSetup`. The setup
procedures (`PrepareParticipantsForNewRound`, `TemplateRefresh`) capture each structured `StartWake` result into a local
`setup_transaction` (wakes / created_assignments / prior_states). On `assignment_phase_failed` (or a StartWake failure)
they call the named rollback (cancel captured `WakeEventRef`s, close created heads legally, restore ledgers, verify none
`WAKING`), then take an explicit liveness path: seat a deterministic `SetupRetryEvent` (strictly-later, `ROUND_SETUP`
microphase, RoundID-stale-guarded) or `RoundAbort`. Every caller handles the disposition.

**Where.** `PrepareParticipantsForNewRound`, `TemplateRefresh` (capture + failure handler); `RollbackParticipantSetup`,
`RollbackTemplateRefreshSetup`, `SetupRetryEvent` (new); §0.7g microphase/seating maps (`SetupRetryEvent` rows).

## V9 — Remove ambiguous boolean/AND returns

**Defect.** Constructs such as `RETURN ScheduleEvent(...) AND wake_started` conflated a scheduler disposition with a
transition result, hiding partial-failure states.

**Correction.** Every procedure inspects the named disposition EXPLICITLY. `StartWake` inspects the `ScheduleEvent`
result (`seat != scheduled(...)`) before any transition and never returns a boolean; callers pattern-match
`wake_seated(...)` / the two failure dispositions. Signatures, `RETURNS` clauses, and call sites agree.

**Where.** `StartWake` and all its callers; `ReserveActivateFromPlan`, `CommitRecoveryAssignmentPlan`,
`PrepareParticipantsForNewRound`, `TemplateRefresh`, `ResumeFromPause`.

---

## Summary of pseudocode changes

| Procedure | Status | Corrections |
|-----------|--------|-------------|
| `ReconcilePendingRecoveryWork` | new | V1 |
| `ReserveActivateFromPlan` | new | V4, V5 |
| `RollbackParticipantSetup` | new | V8 |
| `RollbackTemplateRefreshSetup` | new | V8 |
| `SetupRetryEvent` | new | V8 |
| `StartWake` | rewritten | V2, V3, V9 |
| `ReserveActivate` | revised | V2, V4, V5 |
| `RangeAssign` | revised | V2, V3, V9 |
| `RangeReassign` | revised | V2, V3, V9 |
| `AdversarialParticipationChangeEvent` | revised | V2 |
| `LeaseExpiry` | revised | V2, V9 |
| `CommitRecoveryAssignmentPlan` | revised | V2, V4, V5, V6, V9 |
| `PrepareRecoveryAssignmentPlan` | revised | V5, V6 |
| `ClassifyRecoveryWork` | revised | V6 |
| `SeatRecoveryWork` | revised | V1, V6, V7 |
| `ApplyRecoveryWorkAfterEpilogue` | revised | V7 |
| `CancelActiveRecoveryEpisode` | revised | V7 |
| `SecurityFloorEvaluate` | revised | V1 |
| `PrepareParticipantsForNewRound` | revised | V2, V3, V8, V9 |
| `TemplateRefresh` | revised | V2, V3, V8, V9 |
| `ResumeFromPause` | revised | V2, V3, V9 |
| §0.8 registries | revised | V6, V7 |
| §0.7g microphase/seating maps | revised | V8 |

The procedure inventory grows from 76 (Stage 1U) to **81** defined procedures/functions. The call graph resolves with
**zero** dangling references (see `STAGE_01V_PROCEDURE_CALL_GRAPH.md`).

## Normative documents updated

- `STAGE_01_PROTOCOL_PSEUDOCODE.md` — the V1–V9 procedure edits above.
- `STAGE_01_ROUND_STATE_MACHINE.md` — §3.10 Stage-1V addendum (nine V-blocks).
- `STAGE_01_INVARIANT_CATALOGUE.md` — I16 V6/V7 clauses.
- `STAGE_01_TERMINOLOGY.md` — Stage-1V terminology addendum.
- `STAGE_01_TRACEABILITY_MATRIX.csv` — rows R150–R159 (V1–V9 + the TV174–TV185 block).

## Test vectors

`STAGE_01V_SEMANTIC_TEST_VECTORS.md` defines TV174–TV185, one or more per correction; each names the exact procedures
and expected dispositions and preserves the A1 baseline.
