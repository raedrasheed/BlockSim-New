# Stage 1P — Recovery-Completion Atomicity Audit (P4)

This is a documentation-only paper audit of Stage 1P correction **P4 — make
completion seating atomic with scheduler success** — as edited in
`docs/thesis_revision_v45/stage_01/STAGE_01_PROTOCOL_PSEUDOCODE.md`. The
consensus specification is named **PoCol**; **the idle policy within PoCol** is
referenced here as a mechanism only, and this audit claims no energy, security,
or fairness property of it. The **A1 accounting baseline of 8.420833333 kWh is
UNCHANGED** by P4: the correction only reorders when a per-episode pending flag
is set relative to the scheduler call, and edits no accounting quantity, no
census value, and no energy figure. Scope is strictly P4 — the single seater
`SeatRecoveryCompletion` (§9), the event-time epilogue `SecurityFloorEvaluate`
(§9) that is its sole caller, and the horizon guard shared with O2 (§0.7e) and
`CloseRoundAtHorizon` (§20b). Every claim below is checked against the
pseudocode as edited; no behavior is inferred beyond the text.

## 1. The single seater `SeatRecoveryCompletion` and its ordered guards

Under P4 the SOLE seater of `CompleteSecurityRecovery` is
`SeatRecoveryCompletion` (§9, procedure at lines 1895–1939). It is called ONLY
by the event-time epilogue `SecurityFloorEvaluate` (§9): the UNRECOVERABLE path
at line 1867 and the RESTORED path at line 1874. `RecoveryDeadlineEvent` (§9a,
lines 1941–1971) no longer seats any completion — it records the deadline FACT
and dirties the census only (lines 1955–1959, 1970–1971), which is the P3
change on which P4 builds. There is exactly one seating site.

`SeatRecoveryCompletion(RoundContext, episode, outcome, t)` (lines 1896–1898)
evaluates its guards in this fixed order:

1. **O2/P4 horizon guard** (lines 1900–1905) — `IF t = run_horizon_T: RECORD
   run_ending_no_recovery_action(episode); RETURN run_ending_no_recovery_action`.
   A decision AT the horizon seats NOTHING and leaves NO pending flag.
2. **Apply-once guard** (lines 1906–1908) — `IF recovery_outcome_finalised[episode]
   is set: RETURN recovery_completion_already_finalised`.
3. **P5 no-redundant-reseat** (lines 1909–1914) — `IF recovery_completion_pending[episode]
   AND latest_recovery_decision[episode] EXISTS AND
   latest_recovery_decision[episode].outcome = outcome: RETURN
   recovery_completion_already_pending(outcome)`.
4. **Mint the versioned decision id** (lines 1915–1917) — `recovery_decision_seq`
   is bumped and `decision_id <- (episode, recovery_decision_seq)`
   (the `RecoveryDecisionID`).
5. **Seat through the sole scheduler** (lines 1918–1931) — `result <-
   ScheduleEvent(... CompleteSecurityRecovery ...)` at
   `target_event_time = t_next (strictly > t, <= run_horizon_T)`.

## 2. Pending is set ONLY after `scheduled`; never `completion_seated` on rejection

This is the key P4 property. In `SeatRecoveryCompletion` the pending flag and the
latest-decision record are written ONLY inside the success branch of the scheduler
call (lines 1924–1927):

```
IF result = scheduled(...):
  SET latest_recovery_decision[episode] <- { decision_id, outcome }   # P5
  SET recovery_completion_pending[episode] <- true                    # P4: pending set ONLY after successful enqueue
  RETURN recovery_completion_seated(decision_id, outcome)
ELSE:
  RECORD recovery_completion_schedule_rejected(episode, decision_id, result)   # P4
  RETURN recovery_completion_not_seated(result)
```

The reject branch (lines 1928–1931) leaves `recovery_completion_pending[episode]`
at its prior value (`false` on entry to recovery, set at §9 line 1845) — it is
never set on a rejected schedule — records the EXACT scheduling disposition
`recovery_completion_schedule_rejected(episode, decision_id, result)`, and returns
`recovery_completion_not_seated(result)`. The procedure therefore NEVER returns
`recovery_completion_seated` when `ScheduleEvent` did not return `scheduled` (the
declared return set at lines 1932–1933 and the NOTE at lines 1934–1939 confirm
this). Pending-true and `completion_seated` are consequences of a successful
enqueue and of nothing else. This is **gate 7** (atomicity of pending with
scheduler success).

## 3. Behavior at `event_time = T` (horizon guard, no false pending, gate 8)

At `t = run_horizon_T` the horizon guard (§9 lines 1900–1905) fires FIRST, before
the decision id is minted and before any `ScheduleEvent` call: it records
`run_ending_no_recovery_action(episode)` and returns, seating nothing and leaving
`recovery_completion_pending[episode]` false. No strictly-later completion at
`t_next > T` is even attempted, because the guard returns before the scheduler is
reached. The round is then closed by the run-level hook `CloseRoundAtHorizon`
(§20b, lines 3167–3206), which `ProcessEventTime(T)` interposes between the `T`
drain and the `T` epilogue when the round is nonterminal (§0.7d; §21 priority
table lines 3295–3298); it transitions the round to `ROUND_ABORTED` with the
distinct horizon-end disposition (lines 3194–3195). So a nonterminal round at the
horizon is closed by horizon-close, not by a fabricated recovery completion, and
no false `recovery_completion_pending` flag survives.

Independently, `ScheduleEvent` (§0.7e, lines 366–368) rejects any
`target_event_time > run_horizon_T` with `post_horizon_event_rejected`. Combined
with the horizon guard, no `CompleteSecurityRecovery` is ever attempted at or
beyond `T`: a decision AT `T` is stopped by the guard, and a decision that would
land beyond `T` is refused by the scheduler (and would take the reject branch of
§2, never `completion_seated`). This is **gate 8** (no completion attempted after
or beyond `T`); the priority table entry 13b (lines 3288–3290) records that a
seated completion is always at a STRICTLY LATER event_time.

## 4. BEFORE (Stage 1O) vs AFTER (Stage 1P)

| Aspect | BEFORE — Stage 1O | AFTER — Stage 1P |
|--------|-------------------|------------------|
| Order of pending vs schedule (floor-restored) | `SET recovery_completion_pending[episode] <- true` THEN `CALL ScheduleEvent(...)` (1o §9 lines 1821–1822) | Pending set ONLY inside `IF result = scheduled` (§9 lines 1924–1926) |
| Order of pending vs schedule (deadline) | `RecoveryDeadlineEvent` set pending true THEN called `ScheduleEvent` (1o §9a lines 1870–1871) | `RecoveryDeadlineEvent` seats NOTHING (P3, §9a 1955–1959); only `SeatRecoveryCompletion` seats |
| Seating sites | Two (epilogue restored branch + `RecoveryDeadlineEvent`) | One (`SeatRecoveryCompletion`, §9 lines 1895–1939) |
| Rejected schedule | Could leave a FALSE `recovery_completion_pending = true` | Leaves pending false; records `recovery_completion_schedule_rejected` (§9 lines 1928–1931) |
| Return on rejection | Not distinguished from a seated completion | Returns `recovery_completion_not_seated(result)`; never `completion_seated` (§9 lines 1929–1933) |
| At `t = T` | No dedicated horizon guard in the seating path | Horizon guard records `run_ending_no_recovery_action`, no pending (§9 lines 1900–1905) |

The AFTER behavior is a pure ordering correction: the pending flag becomes a
consequence of a successful enqueue rather than a prediction of one. No accounting
quantity, census value, or A1 baseline is altered.

## 5. Acceptance checks

| # | Check | Evidence | Result |
|---|-------|----------|--------|
| 1 | `SeatRecoveryCompletion` is the SOLE seater; epilogue is its only caller | §9 lines 1867, 1874, 1895–1898 | PASS |
| 2 | `RecoveryDeadlineEvent` seats nothing (records the FACT only) | §9a lines 1955–1959, 1970–1971 | PASS |
| 3 | Guards evaluated in order: horizon → finalised → no-redundant-reseat → mint → schedule | §9 lines 1900–1931 | PASS |
| 4 | `recovery_completion_schedule_rejected` recorded on scheduler reject | §9 lines 1928–1931 | PASS |
| 5 | On `t = T`: `run_ending_no_recovery_action` recorded; no false pending flag left | §9 lines 1900–1905 | PASS |
| 6 | Horizon-close governs a nonterminal round at `T` (not a recovery completion) | §20b lines 3167–3206; §0.7d 219–220 | PASS |
| 7 | Gate 7: `recovery_completion_pending` set true ONLY after `ScheduleEvent = scheduled`; never returns `completion_seated` on reject | §9 lines 1924–1933 | PASS |
| 8 | Gate 8: no completion attempted after or beyond `T` (horizon guard + O2) | §9 lines 1900–1905; §0.7e 366–368 | PASS |

---

*Documentation only. The consensus specification is named PoCol; the idle policy
within PoCol is referenced here as a mechanism only, with no energy, security, or
fairness property claimed. The A1 baseline of 8.420833333 kWh is unchanged. The
prohibited rebranded-algorithm-name variants are not used anywhere in this
document.*
