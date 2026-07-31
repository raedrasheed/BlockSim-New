# Stage 1U — Atomic Re-arm and Continuation Liveness Audit (U3)

This is a documentation-only paper audit of the Stage-1U correction **U3 — atomic
re-arm; continuation liveness** as edited in
`docs/thesis_revision_v45/stage_01/STAGE_01_PROTOCOL_PSEUDOCODE.md`. U3 establishes that a
recovery-work seat / re-arm is COMMITTED only after `ScheduleEvent` succeeds, that a
rejected enqueue advances nothing and publishes nothing, and that no `APPLYING` decision
is ever stranded without a live event, a declared controller, or an explicit
terminal/horizon disposition. The consensus algorithm is named **PoCol**; **the idle
policy within PoCol** is referenced here as a mechanism only, and this audit claims no
energy, security, or fairness property of the idle policy within PoCol. U3 is a
SCHEDULER-ATOMICITY and LIVENESS correction to the recovery-work / branch-C continuation
lifecycle: it changes the ORDER in which a seat is committed and the DISPOSITION recorded
on a rejected enqueue — it never changes how time or energy is counted. The **A1 accepted
accounting baseline of 8.420833333 kWh is UNCHANGED**: no census value, residency interval,
transition-energy term, or accounting quantity is edited. This is documentation only: no
new consensus feature is introduced. Every claim below is checked against the pseudocode as
edited; no behavior is inferred beyond the text.

## 1. The U3 ATOMIC seat/re-arm contract (§9c `SeatRecoveryWork`)

`SeatRecoveryWork` (`PROCEDURE` at line 2537) is the SOLE seater / re-arm of a
recovery-WORK action and implements the U3 ATOMIC protocol. It executes a fixed order —
**compute the candidate identity and target FIRST, publish the active identity ONLY on a
successful enqueue** — so the active work identity is never mutated speculatively:

1. **Compute the candidate identity** — `candidate_seq <- recovery_work_seq + 1` (line
   2553) and `work_id <- (episode, candidate_seq)` (line 2554, the `RecoveryWorkID`). The
   active counter `recovery_work_seq` is NOT touched here; `candidate_seq` is a local
   candidate, not a committed advance.
2. **Compute the target** — `t_due <- t + configured_recovery_completion_delay` (line
   2555), a deterministic strictly-positive delay, so `t_due` is a STRICTLY LATER
   `event_time` than the drained epilogue `t`.
3. **Validate `t_due <= T`** — `IF t_due > run_horizon_T` (line 2556): `RECORD
   recovery_work_horizon_deferred(episode, t_due)` and `RETURN
   recovery_work_horizon_deferred(episode)` (lines 2557–2558) — NO event is enqueued;
   the round stays `SECURITY_RECOVERY` and `CloseRoundAtHorizon` governs run end.
4. **Enqueue WITHOUT mutating the active identity** — `ScheduleEvent(EQ, RoundContext,
   RecoveryWorkDueEvent, target_event_time = t_due, target_microphase = RECOVERY_WORK_DUE,
   {RecoveryEpisodeID = episode, RecoveryWorkID = work_id, WorkGeneration = 1, ...})`
   (lines 2559–2564). Nothing about `recovery_work_seq`, `recovery_work[work_id]`, or
   `pending_recovery_work[episode]` is written before this call returns.
5. **Publish ONLY on success** — `IF result = scheduled(...)` (line 2565): and only then
   `recovery_work_seq <- candidate_seq` (line 2567); `recovery_work[work_id] <-
   work_record(... status = ARMED, work_due_event_ref = result.event_ref, ...)` (lines
   2568–2571); `pending_recovery_work[episode] <- work_id` (line 2572); `RETURN
   recovery_work_seated(work_id, work_action)` (line 2573). The active identity —
   `recovery_work_seq`, the `work_record` with `status = ARMED`, `work_due_event_ref`, and
   the `pending_recovery_work` controller — is published atomically as a unit AFTER a
   confirmed enqueue.

The same procedure serves a RE-ARM: a subsequent seat mints the next `candidate_seq`
(`recovery_work_seq + 1`), targets a fresh `t_due`, and publishes the new `RecoveryWorkID`
only on success — so a re-arm that is rejected leaves the prior committed generation
untouched. On the branch-C continuation record the analogue is
`continuation_status` (§0.8 line 649), "`ARMED` after a successful re-arm enqueue, U3":
the continuation is likewise marked `ARMED` only once its enqueue is confirmed.

Idempotence is preserved orthogonally: if `pending_recovery_work[episode] != null` and the
in-flight work is `ARMED`/`DUE` on the current census version, `SeatRecoveryWork` returns
`recovery_work_already_pending(W0.action)` (lines 2547–2550) rather than seating a
redundant event — at most one in-flight `RecoveryWorkID` per episode.

## 2. Reject dispositions the design must handle

On a rejected enqueue the design records an EXPLICIT disposition and advances nothing. The
enumerated cases are:

| Reject case | Guard / trigger | Disposition recorded and returned | State left |
|---|---|---|---|
| Target beyond the horizon | `t_due > run_horizon_T` (line 2556) | `RECORD recovery_work_horizon_deferred(episode, t_due)`; `RETURN recovery_work_horizon_deferred(episode)` (lines 2557–2558) — no event enqueued | round stays `SECURITY_RECOVERY`; `CloseRoundAtHorizon` (§20b) governs run end |
| Schedule rejection (general) | `result != scheduled(...)` after `ScheduleEvent` (line 2565 fails) | `RECORD recovery_work_schedule_rejected(episode, candidate_seq, result)`; `RETURN recovery_work_not_seated(result)` (lines 2575–2576) | round stays `SECURITY_RECOVERY`; NO advance, NO ref, NO pending |
| Episode already finalised | `recovery_outcome_finalised[episode]` is set (line 2543) | `RETURN recovery_work_already_pending(NONE)` (line 2544) — nothing to seat | unchanged (O4 apply-once) |
| In-flight work already armed | `pending_recovery_work[episode] != null` and `W0.status in {ARMED, DUE}` on the bound version (lines 2547–2549) | `RETURN recovery_work_already_pending(W0.action)` (line 2550) — no re-seat | unchanged (idempotent) |

On the two REJECT cases that abort a fresh seat (horizon-beyond-`T` and general schedule
rejection) the U3 REJECTED contract (line 2574) is exact: **do NOT advance
`recovery_work_seq`, do NOT publish a `work_due_event_ref`, do NOT report a
pending/reserve_pending state.** No `reserve_pending` or pending status is ever reported on
a rejected enqueue; the round stays `SECURITY_RECOVERY` (or the horizon-close path
governs). The declared return surface is exactly `recovery_work_seated |
recovery_work_not_seated | recovery_work_already_pending | recovery_work_horizon_deferred`
(line 2577) — a rejected seat resolves into one of these named dispositions, never a
silent no-op.

## 3. LIVENESS — no stranded `APPLYING` decision

The liveness property is stated at the `SeatRecoveryWork` NOTE (lines 2586–2587): "Because
a recovery-work action is not an APPLYING decision, no APPLYING decision is ever left
without a live event, a controller (`pending_recovery_work`), or an explicit
terminal/horizon disposition (U3)." Two disjoint facts carry it:

**(a) A recovery-work action is not an `APPLYING` decision.** A recovery-WORK action is an
explicit identity with its own lifecycle (`RECOVERY_WORK_STATUS`, §0.8 line 728) and is
NEVER a `RecoveryDecisionID` and NEVER marked `APPLIED` (§0.8 lines 724–725);
`SeatRecoveryWork` never sets `recovery_outcome_finalised` and never marks a decision
`APPLIED` (NOTE lines 2584–2586). So seating or re-arming work does not, and cannot,
create an `APPLYING` decision. Whichever way a seat resolves, its controller is
`pending_recovery_work[episode]`: on success it points at the live `ARMED` work whose
`work_due_event_ref` is queued; on a reject it is left `null` under an explicit
`recovery_work_not_seated` / `recovery_work_horizon_deferred` disposition — never a
dangling half-published identity.

**(b) A branch-C `APPLYING` decision is always resolved in ONE continuation-hook
invocation.** `ApplyRecoveryAssignmentContinuationAfterEpilogue` (`PROCEDURE` at line 3040)
is the ONLY place branch-C `RESTORED` is applied, and every path through it terminates the
`APPLYING` decision in that single invocation:

- **`APPLIED` at `HASHING`** — `disp = assignment_phase_completed` (line 3120):
  `SetRecoveryDecisionStatus(... APPLIED)`, `recovery_outcome_finalised[episode] <-
  RESTORED`, decision removed from `pending`, `current_recovery_episode` cleared (lines
  3122–3128).
- **`APPLY_FAILED` on rollback** — a pre-mutation failure or a `rollback_completed` after
  a mutated commit rolls `round_state -> SECURITY_RECOVERY`, sets
  `SetRecoveryDecisionStatus(... APPLY_FAILED)`, and removes the decision from `pending`
  (lines 3091–3107, 3129–3147); the episode is PRESERVED for a later re-classification.
- **`APPLY_FAILED_TERMINAL` on abort** — an irreversible `rollback_failed` sets
  `SetRecoveryDecisionStatus(... APPLY_FAILED_TERMINAL)`, records
  `recovery_episode_disposition[episode] <- RECOVERY_INSTALL_FAILED_ABORTED` (never a
  fabricated `UNRECOVERABLE`), clears `current_recovery_episode`, and takes the declared
  recovery-finalising `RoundAbort(... recovery_finalising = true)` (lines 3108–3117,
  3131–3141).

The NOTE states the exhaustive exit set (lines 3159–3161): "Every installation exit ends
in exactly one of: HASHING + decision APPLIED; SECURITY_RECOVERY + APPLY_FAILED (rollback
complete, episode preserved); ROUND_ABORTED + RECOVERY_INSTALL_FAILED_ABORTED (T3/T4)."
Because the installation phase is a SYNCHRONOUS sub-computation with no event boundary
inside it (T3 invariant, §0.8 lines 702–711), no epilogue ever observes a transient
`ASSIGNMENT`-with-active-episode-and-no-live-continuation state — the decision leaves
`APPLYING` before the hook returns. `ProcessEventTime`'s final assertions reinforce this:
the post-epilogue application enqueues NOTHING at the drained `t` (line 272, R1/T7 — any
`StartWake`/re-arm is strictly later), and every `DUE` continuation at `t` is EXPLICITLY
`CONSUMED`/`SUPERSEDED`/`CANCELLED`, never inferred from a timestamp (line 275, U4/T7).

## 4. PASS-check table (exact names cited)

| Acceptance concern | Where enforced (verbatim) | Verdict |
|---|---|---|
| Seat committed ONLY after `ScheduleEvent` succeeds | `SeatRecoveryWork` lines 2565–2573: publish `recovery_work_seq`/`work_record`(`status = ARMED`)/`work_due_event_ref`/`pending_recovery_work` inside `IF result = scheduled(...)` | PASS |
| Candidate identity + `t_rearm` computed FIRST | `candidate_seq <- recovery_work_seq + 1` (2553); `work_id <- (episode, candidate_seq)` (2554); `t_due <- t + configured_recovery_completion_delay` (2555) | PASS |
| `t_rearm` validated `<= T` before enqueue | `IF t_due > run_horizon_T` → `recovery_work_horizon_deferred` (2556–2558), no event enqueued | PASS |
| `ScheduleEvent` called WITHOUT mutating the active identity | `ScheduleEvent(... RecoveryWorkDueEvent, target_event_time = t_due, target_microphase = RECOVERY_WORK_DUE, ...)` (2559–2564) precedes every publish | PASS |
| Rejected enqueue does NOT advance the generation/seq | U3 REJECTED (2574): "do NOT advance `recovery_work_seq`"; `recovery_work_seq <- candidate_seq` sits only on the success arm (2567) | PASS |
| Rejected enqueue publishes NO event reference | `work_due_event_ref = result.event_ref` set only on success (2570); reject returns `recovery_work_not_seated(result)` (2576) with no ref | PASS |
| Rejected enqueue reports NO `reserve_pending`/pending state | U3 REJECTED (2574): "do NOT report a pending/reserve_pending state … the round stays SECURITY_RECOVERY"; NOTE 2582–2584 | PASS |
| Explicit reject disposition recorded | `RECORD recovery_work_schedule_rejected(episode, candidate_seq, result)` (2575); horizon: `RECORD recovery_work_horizon_deferred(episode, t_due)` (2557) | PASS |
| A recovery-work action is NOT an `APPLYING` decision | §0.8 lines 724–725 (work is never a `RecoveryDecisionID`, never `APPLIED`); NOTE lines 2584–2587 | PASS |
| Branch-C `APPLYING` resolved in ONE hook invocation | `ApplyRecoveryAssignmentContinuationAfterEpilogue` exits: `APPLIED` (3122–3128) / `APPLY_FAILED` (3091–3107, 3142–3147) / `APPLY_FAILED_TERMINAL` (3108–3117, 3131–3141); exit set NOTE 3159–3161 | PASS |
| No `APPLYING` left without event / controller / terminal disposition | `SeatRecoveryWork` NOTE 2586–2587; `pending_recovery_work` controller (§0.8 line 726); T3 invariant §0.8 702–711 | PASS |

## 5. Failure-mode contrast

The correction is legible against the two defects it forecloses:

- **An advanced generation or a published event ref on a rejected enqueue.** A
  non-atomic design that advanced `recovery_work_seq` (or wrote `pending_recovery_work` /
  `work_due_event_ref`) BEFORE confirming `result = scheduled(...)` would, on a rejected
  enqueue, leave a `RecoveryWorkID` whose `work_due_event_ref` names an event that was
  never queued — a controller pointing at nothing, with the seq counter permanently past a
  generation that never armed. U3 forecloses this: the active identity is written only
  inside the `IF result = scheduled(...)` arm (lines 2565–2573), and the reject arm
  advances nothing, publishes no ref, and returns the explicit `recovery_work_not_seated`
  (line 2576) with `pending_recovery_work[episode]` left `null`.
- **A stranded `APPLYING` decision with no controller.** A design that could seat a
  branch-C continuation, fail its enqueue, yet leave the decision `APPLYING` with no queued
  continuation event and no retry controller would strand the decision — the round could
  linger with an active episode and nothing scheduled to resolve it. U3 (with T1/T3/T4)
  forecloses this: a recovery-work action is not an `APPLYING` decision at all, so its
  reject cannot strand one; and every branch-C `APPLYING` decision is resolved to `APPLIED`
  / `APPLY_FAILED` / `APPLY_FAILED_TERMINAL` inside the single
  `ApplyRecoveryAssignmentContinuationAfterEpilogue` invocation (exit set NOTE lines
  3159–3161), so no `APPLYING` decision is ever left without a live continuation event, the
  declared `pending_recovery_work` controller for recovery work, or an explicit
  terminal/horizon disposition.

## 6. Result

Under U3, `SeatRecoveryWork` (§9c) commits a recovery-work seat / re-arm ONLY after
`ScheduleEvent` succeeds: it computes `candidate_seq` and `work_id` and the strictly-later
`t_due`, validates `t_due <= T` (else `recovery_work_horizon_deferred`, no event enqueued),
calls `ScheduleEvent` without mutating the active work identity, and publishes
`recovery_work_seq`, the `work_record` with `status = ARMED`, `work_due_event_ref`, and the
`pending_recovery_work` controller ONLY on `result = scheduled(...)`. On a rejected enqueue
it advances no seq, publishes no event reference, reports no `reserve_pending`/pending
state, records an explicit `recovery_work_not_seated` (or `recovery_work_horizon_deferred`)
disposition, and leaves the round in `SECURITY_RECOVERY` (or the horizon-close path
governs). A recovery-work action is never an `APPLYING` decision, and every branch-C
`APPLYING` decision is resolved in one `ApplyRecoveryAssignmentContinuationAfterEpilogue`
invocation — `APPLIED` at `HASHING`, `APPLY_FAILED` on rollback, or
`APPLY_FAILED_TERMINAL` on abort — so no `APPLYING` decision is ever left without a live
continuation event, a declared controller (`pending_recovery_work` for recovery work), or
an explicit terminal/horizon disposition. U3 operates purely on the ordering and atomicity
of the seat/re-arm and on continuation liveness; the A1 accepted baseline of 8.420833333
kWh is unchanged, and no new consensus feature is introduced.

The prohibited rebranded-algorithm-name variants are not used anywhere in this document.
