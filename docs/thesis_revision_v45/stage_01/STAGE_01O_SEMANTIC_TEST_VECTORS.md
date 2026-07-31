# Stage 1O — Semantic Test Vectors (TV111–TV118)

Paper test vectors for the horizon/recovery final lock (O1–O5). Each vector names the EXACT procedures,
preconditions, and transitions in `STAGE_01_PROTOCOL_PSEUDOCODE.md`; no guard, transition, seating, or
cancellation is assumed that is not in the pseudocode. Name remains **PoCol**; the mechanism is **the idle
policy within PoCol**; the A1 baseline (`8.420833333 kWh`) is preserved by every vector (each is an ordering /
reachability / idempotence check, never a change to how time or energy is counted).

---

## TV111 — Nonterminal round at the horizon is closed by `CloseRoundAtHorizon`, then finalised (O1)

**Setup.** A run reaches the fixed horizon `T` with its current round still `HASHING` (nonterminal). Ordinary
events exist at `T`.
**Steps.**
1. `RunEventLoopToHorizon` (§0.7d-run) calls `ProcessEventTime(RoundContext, T, is_horizon = true)`.
2. `ProcessEventTime` DRAINS `T` to quiescence (all ordinary + delta-cycle events).
3. Because `is_horizon` and `round_state = HASHING ∉ {ROUND_ACCEPTED, ROUND_ABORTED}`, it CALLs
   `CloseRoundAtHorizon` (§20b): `CloseRoundAssignments(disposition = ROUND_ABORTED)` with ONE deterministic
   `horizon_envelope`, `horizon_end_disposition ← closed_at_horizon`, `round_terminal_time ← run_horizon_T`,
   `TRANSITION round_state → ROUND_ABORTED`; NO residency settle.
4. The `T` epilogue `FinalizeEventTimeSecurityCensus(T)` runs; `SecurityFloorEvaluate` sees the terminal
   round and returns `terminal_stale_noop` (clears `security_census_dirty[T]`).
5. `ProcessEventTime(T)` returns; `RunEventLoopToHorizon` CALLs `FinalizeSimulationRun` (§20a).
**Expected.** `FinalizeSimulationRun` (guarded by `run_finalised`) performs ONLY the single
`SettleResidencyBoundary(FINAL_RUN_END, (RunID, RUN_END))`, then the I5/I6/I7 reconciliation, then sets
`run_finalised`. The horizon-close happened BEFORE the epilogue; the epilogue was a no-op; the finaliser did
NOT drain or close a round. **Invariants.** I5/I6/I7 (reconciled once at `T`), I19 (idle interval counted
once). A1 preserved.

## TV112 — Accepted final round: `CloseRoundAtHorizon` skipped; single finaliser; re-invocation no-op (O1)

**Setup.** The last round ended `ROUND_ACCEPTED` before `T`; the run driver reaches `T`.
**Steps.**
1. `ProcessEventTime(T, is_horizon = true)` drains `T`. The horizon interposition condition
   `round_state ∉ {ROUND_ACCEPTED, ROUND_ABORTED}` is FALSE (round is `ROUND_ACCEPTED`), so
   `CloseRoundAtHorizon` is SKIPPED.
2. The `T` epilogue is a `terminal_stale_noop`.
3. `RunEventLoopToHorizon` CALLs `FinalizeSimulationRun`.
4. A spurious re-dispatch/re-invocation of `FinalizeSimulationRun` is attempted.
**Expected.** Step 3 performs the ONE `FINAL_RUN_END` settle + I5/I6/I7 + `run_finalised ← true`. Step 4
returns `run_already_finalised` (idempotent guard). The ACCEPTED and (TV111) ABORTED/nonterminal final rounds
use the SAME run-level finaliser path. A1 preserved.

## TV113 — `ProcessEventTime` is the sole event-loop driver; `RUN_FINALISE` is not queued (O1)

**Setup.** A run in progress; a handler completes at some `event_time < T`.
**Steps.**
1. No handler calls `ProcessEventTime` (it is only called by `RunEventLoopToHorizon`).
2. `FinalizeSimulationRun` (§20a) contains NO `DRAIN the event queue …` step (removed by O1).
3. The event-type → microphase map (§0.7g) and the §0.7g-driver seating table are inspected for
   `RUN_FINALISE`.
**Expected.** ProcessEventTime is the sole event-loop driver and is never re-entered from a handler; the
former re-entrant drain inside `FinalizeSimulationRun` is gone. `RUN_FINALISE` is NOT in the queue map and
`FinalizeSimulationRun`/`CloseRoundAtHorizon` are documented as run-level hooks (never enqueued). A1
preserved.

## TV114 — `ScheduleEvent` rejects any event beyond the horizon; `= T` is legal (O2)

**Setup.** Dispatch context with `EQ.run_horizon_T = T`. Three `ScheduleEvent` calls: (a)
`target_event_time = T + δ` (δ > 0); (b) `target_event_time = T`; (c) `target_event_time = t' < T` (future,
in-bounds).
**Steps.** Each call enters `ScheduleEvent` (§0.7e), the SOLE enqueue interface.
**Expected.** (a) returns `post_horizon_event_rejected` and enqueues NOTHING (records `post_horizon_event`);
(b) is enqueued normally (the horizon itself is legal); (c) is enqueued normally. After any sequence of
`ScheduleEvent` calls, NO pending ordinary event has `event_time > T`. **Invariant.** No stranded post-horizon
event; combined with the run driver draining every `event_time <= T`, the queue is empty of ordinary events
when `FinalizeSimulationRun` runs. A1 preserved.

## TV115 — Floor-restored decision AT `T` seats no recovery; records `run_ending_no_recovery_action` (O2)

**Setup.** The round is in `SECURITY_RECOVERY` with an active episode `E`; at `event_time = T` the census
shows the floor restored (no breach).
**Steps.**
1. The `T` epilogue calls `SecurityFloorEvaluate` (§9); it reaches the `(NOT breach) AND round_state =
   SECURITY_RECOVERY` branch.
2. The O2 horizon guard `IF t = run_horizon_T` holds.
**Expected.** It RECORDs `run_ending_no_recovery_action(E)` and RETURNs `run_ending_no_recovery_action`; NO
`CompleteSecurityRecovery` is scheduled (a `t_next > T` would be rejected by `ScheduleEvent`). No recovery
participation action changes `H_active` after the final decision at `T`; the round is closed by
`CloseRoundAtHorizon` at `T` (TV111). A1 preserved.

## TV116 — FloorUnrecoverable is reachable via the seated `RecoveryDeadlineEvent` (O3)

**Setup.** At `t₀ < T` the census breaches the floor while `round_state = HASHING`.
**Steps.**
1. `SecurityFloorEvaluate` (§9) breach branch: `TRANSITION → SECURITY_RECOVERY`; mints episode `E =
   (RoundID, recovery_episode_seq)`; `current_recovery_episode ← E`; `recovery_completion_pending[E] ← false`;
   seats `RecoveryDeadlineEvent` (§9a) at `min(t₀ + recovery_deadline_window, T)` carrying `E` + epoch.
2. The floor remains breached; no floor-restored decision seats a completion.
3. `RecoveryDeadlineEvent` fires (still `SECURITY_RECOVERY`, episode current, epoch matches,
   `recovery_completion_pending[E]` false): sets pending true and seats `CompleteSecurityRecovery` with
   `RecoveryOutcome = UNRECOVERABLE` at a strictly-later `event_time <= T`.
4. `CompleteSecurityRecovery` (§10a) dispatches: not finalised, not stale → finalises `E`, branch D →
   `RoundAbort(reason = floor_unrecoverable)`.
**Expected.** A concrete source (`RecoveryDeadlineEvent`) and call path reach `RoundAbort(floor_unrecoverable)`
via branch D; R14 is executable. `RoundAbort` closes ONLY this round (N1); the run continues (or is finalised
at `T` per O1). A1 preserved.

## TV117 — Recovery-episode idempotence: one completion, one applied outcome (O4)

**Setup.** The round is in `SECURITY_RECOVERY` with active episode `E`; a `RecoveryDeadlineEvent` for `E` is
pending.
**Steps.**
1. At `t₁ < T` the census shows the floor restored → `SecurityFloorEvaluate` floor-restored branch:
   `recovery_completion_pending[E]` is false and `recovery_outcome_finalised[E]` unset → sets pending true and
   seats `CompleteSecurityRecovery(RESTORED)` at `t_next > t₁`.
2. `RecoveryDeadlineEvent` later fires for `E`: it sees `recovery_completion_pending[E] = true` → returns
   `recovery_deadline_superseded_noop` (seats nothing).
3. `CompleteSecurityRecovery(RESTORED)` dispatches: `recovery_outcome_finalised[E]` unset, episode current,
   epoch matches → sets `recovery_outcome_finalised[E] ← RESTORED`, `current_recovery_episode ← null`, and
   runs branch A/B/C.
4. A duplicate/replayed `CompleteSecurityRecovery` for `E` arrives.
**Expected.** Exactly ONE completion is seated (RESTORED wins because seated first); the deadline is a
deterministic no-op; exactly ONE outcome is applied; the duplicate returns `recovery_completion_duplicate_noop`.
The symmetric case (deadline first → UNRECOVERABLE wins, floor-restored later → `floor_restored_completion_
already_pending`) holds by the same keys. A1 preserved.

## TV118 — Security decision is the post-quiescence epilogue, never before certificate/discovery (O5)

**Setup.** At a shared `event_time = t` a `CertificateArrival`, a solution-discovery `HashWorkEvent` hit, and
an `ACTIVE_HASHING` census boundary all occur.
**Steps.**
1. `ProcessEventTime(t)` drains `t`: certificate arrival (microphase `CERTIFICATE_ARRIVAL`) and solution
   discovery (`HASH_WORK`) are processed in their microphases; the census boundary sets
   `security_census_dirty[t]`.
2. Only AFTER `t` is quiescent does `ProcessEventTime` run the epilogue `FinalizeEventTimeSecurityCensus(t)`
   → `SecurityFloorEvaluate` (once).
**Expected.** The security decision NEVER runs before certificate/discovery; it is the post-quiescence
event-time epilogue keyed by `event_time` alone (I-01/I-02). The name used throughout the normative corpus is
`FinalizeEventTimeSecurityCensus`; the superseded name is absent. Round SM §2.6 states this order. A1
preserved.

---

## Coverage summary

| Vector | Correction | Exercises |
|--------|-----------|-----------|
| TV111 | O1 | nonterminal horizon close → terminal-stale epilogue → single finaliser |
| TV112 | O1 | accepted final round; single finaliser path; `run_finalised` guard |
| TV113 | O1 | sole event-loop driver; no internal drain; `RUN_FINALISE` not queued |
| TV114 | O2 | `ScheduleEvent` post-horizon rejection; `= T` legal; no stranded event |
| TV115 | O2 | floor decision at `T` → `run_ending_no_recovery_action`; no recovery past `T` |
| TV116 | O3 | R14 reachable via seated `RecoveryDeadlineEvent` → branch D → `RoundAbort` |
| TV117 | O4 | episode idempotence: one completion seated, one outcome applied |
| TV118 | O5 | security decision only as post-quiescence epilogue; canonical name |

All eight vectors pass on paper against the exact named procedures. No new consensus feature; documentation
only; name remains PoCol; the A1 baseline `8.420833333 kWh` is unchanged. The prohibited
rebranded-algorithm-name variants are not used anywhere in this document.
