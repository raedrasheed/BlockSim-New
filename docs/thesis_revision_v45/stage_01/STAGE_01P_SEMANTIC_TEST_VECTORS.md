# Stage 1P — Semantic Test Vectors (TV119–TV126)

Paper test vectors for the horizon-sentinel and recovery-decision lock (P1–P5). Each vector names the EXACT
procedures, preconditions, and transitions in `STAGE_01_PROTOCOL_PSEUDOCODE.md`; no guard, transition,
seating, or cancellation is assumed that is not in the pseudocode. Name remains **PoCol**; the mechanism is
**the idle policy within PoCol**; the A1 baseline (`8.420833333 kWh`) is preserved by every vector (each is an
ordering / reachability / idempotence / atomicity check, never a change to how time or energy is counted).

---

## TV119 — Empty horizon queue: the sentinel still closes and finalises (P1)

**Setup.** The last ordinary event occurs at `t₀ < T` and the queue becomes EMPTY; the current round is still
`HASHING` (nonterminal) at `T`.
**Steps.**
1. `RunEventLoopToHorizon` (§0.7d-run) drains every `event_time < T` via `ProcessEventTime`; the queue holds no
   event at `T`.
2. Because `T not in finalised_event_times`, it makes the SYNTHETIC call `ProcessEventTime(T, is_horizon =
   true, allow_empty_horizon = true, RunHookContext = …)`.
3. `ProcessEventTime(T)` drains `T` — the drain is EMPTY (allowed by `allow_empty_horizon`). The round is
   nonterminal, so it interposes `CloseRoundAtHorizon` (§20b) → `ROUND_ABORTED` (horizon-end disposition, one
   deterministic run-hook envelope). The `T` epilogue `FinalizeEventTimeSecurityCensus(T)` is a
   `terminal_stale_noop` that finalises the `T` census; `T` is added to `finalised_event_times`.
4. `RunEventLoopToHorizon` calls `FinalizeSimulationRun`.
**Expected.** `ProcessEventTime(T)` runs even though no ordinary event exists at `T`; the nonterminal round is
horizon-closed; the `T` epilogue runs; `FinalizeSimulationRun` (asserting the round terminal) performs the
single `FINAL_RUN_END` settle + I5/I6/I7 + `run_finalised`. A1 preserved.

## TV120 — Accepted final round, no event at T: exactly one synthetic step; one settle (P1)

**Setup.** The last round ended `ROUND_ACCEPTED` before `T`; no ordinary event exists at `T`.
**Steps.**
1. The `t < T` loop drains everything before `T`.
2. `T not in finalised_event_times` → the synthetic `ProcessEventTime(T, is_horizon = true,
   allow_empty_horizon = true)` runs ONCE. The round is `ROUND_ACCEPTED` (terminal), so the horizon-close
   condition `round_state ∉ {ROUND_ACCEPTED, ROUND_ABORTED}` is FALSE → `CloseRoundAtHorizon` SKIPPED.
3. The `T` epilogue is a `terminal_stale_noop`; `T` is finalised.
4. `FinalizeSimulationRun` runs.
**Expected.** The synthetic `ProcessEventTime(T)` runs exactly once; `FinalizeSimulationRun` performs the ONE
`FINAL_RUN_END` settle + I5/I6/I7 + `run_finalised`. Residency is settled once. A1 preserved.

## TV121 — Deadline coincides with a floor-restoring WakeCompleteEvent → RESTORED (P3)

**Setup.** The round is in `SECURITY_RECOVERY` with active episode `E`; at `event_time = t_d` both a
`RecoveryDeadlineEvent` for `E` and a `WakeCompleteEvent` that raises `H_honest` back to/above the floor fire.
**Steps.**
1. During the `t_d` drain, `RecoveryDeadlineEvent` (§9a) sets `recovery_deadline_reached[E] <- true` and calls
   `CaptureSecurityCensusOnRecoveryDeadline(t_d)` (records a below-floor census, dirties `t_d`). It selects NO
   outcome and seats NO completion.
2. The `WakeCompleteEvent` transitions its miner to `ACTIVE_HASHING` via `ApplyMinerStateTransition`, which
   OVERWRITES `latest_security_census[t_d]` with the restored (above-floor) census.
3. After `t_d` is quiescent, the epilogue `FinalizeEventTimeSecurityCensus(t_d) → SecurityFloorEvaluate` reads
   the FINAL census: NOT breach → the `(NOT breach) AND SECURITY_RECOVERY` branch → `SeatRecoveryCompletion(E,
   RESTORED, t_d)`.
**Expected.** The deadline records only the fact; the epilogue selects `RESTORED` (never `UNRECOVERABLE`)
because the same-timestamp restoration is visible in the FINAL census. A1 preserved.

## TV122 — Deadline with a persistent breach → UNRECOVERABLE, exactly one completion (P3/P4)

**Setup.** The round is in `SECURITY_RECOVERY` (episode `E`); at `event_time = t_d < T` the deadline fires and
the FINAL census remains below the floor.
**Steps.**
1. `RecoveryDeadlineEvent` sets `recovery_deadline_reached[E] <- true` and captures the (below-floor) census;
   no other same-`t_d` boundary restores the floor.
2. The epilogue `SecurityFloorEvaluate` records `breach_persists`, sees `recovery_deadline_reached[E]` true →
   `SeatRecoveryCompletion(E, UNRECOVERABLE, t_d)`: mints a `RecoveryDecisionID`, `ScheduleEvent(...)` returns
   `scheduled` → sets `latest_recovery_decision[E]` and `recovery_completion_pending[E] <- true` (P4).
3. `CompleteSecurityRecovery` dispatches (latest decision, episode current) → finalises `E` → branch D →
   `RoundAbort(floor_unrecoverable)` (round only, N1).
**Expected.** The epilogue selects `UNRECOVERABLE` from the final census and seats EXACTLY ONE completion; R14
is reached. A1 preserved.

## TV123 — Deadline at the horizon T: no completion, horizon closure governs (P4/O2)

**Setup.** The recovery deadline event_time equals `T` (or the epilogue's recovery decision falls at `t = T`),
round in `SECURITY_RECOVERY`.
**Steps.**
1. At `t = T` the epilogue reaches `SeatRecoveryCompletion(E, outcome, T)`; the O2/P4 horizon guard `IF t =
   run_horizon_T` fires FIRST → `RECORD run_ending_no_recovery_action(E)`; seats NOTHING; leaves
   `recovery_completion_pending[E]` FALSE.
2. `CloseRoundAtHorizon` (§20b) closes the still-nonterminal round at `T`.
**Expected.** No strictly-later recovery completion is attempted (it would be `> T`, which `ScheduleEvent`
rejects anyway, O2); no false `recovery_completion_pending` flag is written; horizon closure governs run end.
A1 preserved.

## TV124 — ScheduleEvent rejects the completion: no false pending, no false seated (P4)

**Setup.** In `SeatRecoveryCompletion(E, outcome, t)` (t < T) the `ScheduleEvent` call for
`CompleteSecurityRecovery` returns a rejection (e.g. a finalised or backward target time).
**Steps.**
1. `SeatRecoveryCompletion` mints a `RecoveryDecisionID` and calls `ScheduleEvent(...)`.
2. `result ≠ scheduled` → the ELSE branch: `RECORD recovery_completion_schedule_rejected(E, decision_id,
   result)`; `recovery_completion_pending[E]` REMAINS false; `latest_recovery_decision[E]` is NOT updated;
   RETURN `recovery_completion_not_seated(result)`.
**Expected.** `recovery_completion_pending` remains false and the procedure does NOT report a completion as
seated; the exact scheduling disposition is recorded. A1 preserved.

## TV125 — Horizon-close replay is idempotent (P2)

**Setup.** `CloseRoundAtHorizon` (§20b) has already run once for the run (`HorizonHookID ∈
RunHookContext.applied_run_hook_ids`); it is invoked again (a replay/retry).
**Steps.**
1. `CloseRoundAtHorizon` computes `HorizonHookID = (RunID, run_horizon_T, HORIZON_CLOSE)`.
2. `HorizonHookID ∈ applied_run_hook_ids` → RETURN `horizon_close_duplicate_noop(HorizonHookID)` before any
   `CloseRoundAssignments` call or transition.
**Expected.** The replay is a deterministic no-op: no second `CloseRoundAssignments`, no second
`ROUND_ABORTED` transition, and — because `CloseRoundAssignments`/`ApplyMinerStateTransition` are not
re-invoked — NO second transition energy and NO second residency boundary. A1 preserved.

## TV126 — A superseded recovery decision no-ops at dispatch (P5)

**Setup.** The round is in `SECURITY_RECOVERY` (episode `E`). At `t1` the epilogue seats completion decision
`D1` (say RESTORED); before `D1` dispatches, at `t2` (t1 < t2 < the completion time) a newer FINAL census
warrants a DIFFERENT outcome.
**Steps.**
1. `SeatRecoveryCompletion(E, RESTORED, t1)` → `D1` seated; `latest_recovery_decision[E] = {D1, RESTORED}`;
   `recovery_completion_pending[E] = true`.
2. At `t2` the epilogue warrants UNRECOVERABLE (deadline reached, breach persists) → `SeatRecoveryCompletion(E,
   UNRECOVERABLE, t2)`: outcome differs from the latest, so it seats `D2`; `latest_recovery_decision[E] = {D2,
   UNRECOVERABLE}` (supersedes `D1`).
3. `D1`'s `CompleteSecurityRecovery` dispatches → `recovery_outcome_finalised[E]` unset, episode current, epoch
   ok, but `RecoveryDecisionID D1 ≠ latest_recovery_decision[E].decision_id (D2)` → RETURN
   `recovery_decision_stale_noop`.
4. `D2`'s `CompleteSecurityRecovery` dispatches → it is the latest → finalises `E` → branch D →
   `RoundAbort(floor_unrecoverable)`.
**Expected.** The old (D1) completion returns `recovery_decision_stale_noop`; only the latest (D2) decision is
applied; at most one outcome is applied per episode (O4). A1 preserved.

---

## Coverage summary

| Vector | Correction | Exercises |
|--------|-----------|-----------|
| TV119 | P1 | empty horizon queue → synthetic `ProcessEventTime(T)`, horizon close, finalise |
| TV120 | P1 | accepted final round, no event at T → exactly one synthetic step; one settle |
| TV121 | P3 | deadline + same-time restoration → epilogue picks RESTORED |
| TV122 | P3/P4 | deadline + persistent breach → UNRECOVERABLE, exactly one completion |
| TV123 | P4/O2 | deadline at T → run_ending_no_recovery_action, no false pending, horizon close |
| TV124 | P4 | ScheduleEvent rejection → pending stays false, not reported seated |
| TV125 | P2 | horizon-close replay → `horizon_close_duplicate_noop`, no double energy/boundary |
| TV126 | P5 | superseded decision → `recovery_decision_stale_noop`; latest applies |

All eight vectors pass on paper against the exact named procedures. No new consensus feature; documentation
only; name remains PoCol; the A1 baseline `8.420833333 kWh` is unchanged. The prohibited
rebranded-algorithm-name variants are not used anywhere in this document.
