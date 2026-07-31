# Stage 1P — Horizon-Sentinel Audit (P1)

This is a documentation-only paper audit of Stage 1P correction **P1 — force exactly one
horizon-time processing step** — as edited in
`docs/thesis_revision_v45/stage_01/STAGE_01_PROTOCOL_PSEUDOCODE.md`. The consensus algorithm is
named **PoCol**; the idle policy within PoCol is referred to here only as a mechanism, and this
audit makes no energy, security, or fairness claim about it. The A1 accounting baseline is
**8.420833333 kWh** and is UNCHANGED by P1: the correction only forces the horizon-time step to
run exactly once even when no ordinary event lands on `T`, and edits no accounting quantity. Scope
is strictly P1 — the reshaped run-level loop in `RunEventLoopToHorizon` (§0.7d-run), the synthetic
horizon-sentinel invocation of `ProcessEventTime` (§0.7d) with `allow_empty_horizon = true`, and
the two structural gates in `FinalizeSimulationRun` (§20a) and `CloseRoundAtHorizon` (§20b). Every
claim below is checked against the pseudocode as edited; no behavior is inferred beyond the text.

## 1. The reshaped `RunEventLoopToHorizon` loop and the synthetic sentinel

`RunEventLoopToHorizon` (§0.7d-run, procedure at lines 242–271) is the run-level driver. Under P1 it
processes only event_times **strictly less than** `T`, then makes ONE horizon-sentinel call, then the
run-level finaliser. Reading the procedure body:

1. **Process every `event_time < T`** — the loop guard is `WHILE the queue has an unprocessed
   event_time t with t < T` (line 251); it selects the earliest unprocessed `t` (line 252) and calls
   `ProcessEventTime(RoundContext, t, is_horizon = false)` (line 253). No call in this loop touches `T`.
2. **The horizon sentinel** — after the loop, guarded by `IF T not in finalised_event_times` (line
   258), it calls `ProcessEventTime(RoundContext, T, is_horizon = true, allow_empty_horizon = true,
   RunHookContext = RunContext.RunHookContext)` (lines 259–260). The prose (§0.7d-run, lines 279–281)
   states this "runs EVEN WHEN the queue holds no event whose `event_time = T`, so the horizon sequence
   always occurs exactly once — an ordinary event at `T` is NOT required."
3. **Then the run-level finaliser** — `CALL FinalizeSimulationRun(RunContext, RoundContext)` (line 265),
   a post-`ProcessEventTime(T)` run-level hook, NOT a queued event.

The guard `T not in finalised_event_times` makes the sentinel run **at most once**; the unconditional
placement after the `t < T` loop makes it run **at least once**. Together the horizon-time step runs
EXACTLY ONCE, which is the P1 guarantee (§0.7d-run prose, lines 274–281; procedure NOTE, lines 267–271).

## 2. Empty drain at `T` — no ordinary event at `T`

The correctness of P1 rests on `ProcessEventTime` accepting a call at `t = T` when the queue holds no
event whose `event_time = T`. The edited procedure (§0.7d, lines 182–240) supports this:

- **INPUTS** add `allow_empty_horizon = false` (line 183); the comment (lines 185–186) states it
  "permits a SYNTHETIC horizon invocation at `t = T` even when NO ordinary event exists at `T` (the
  horizon-sentinel step)."
- **PRECONDITIONS** (lines 189–194) keep `t not in finalised_event_times` and `t <= run_horizon_T`, and
  add the explicit exception (lines 191–194): the synthetic horizon-sentinel call "is permitted even if
  the queue holds NO event at `T`, so the horizon sequence always runs."
- **The drain LOOP** breaks immediately when empty: `IF no ordinary event remains at event_time = t:
  BREAK` (line 199). The comment (lines 196–197) states the drain "may be EMPTY (no ordinary event at
  `t`) for a synthetic horizon invocation — that is legal."

Even with an empty drain, the horizon sequence still runs in full:

- **Horizon closure interposed** — `IF is_horizon AND round_state NOT in {ROUND_ACCEPTED,
  ROUND_ABORTED}: CALL CloseRoundAtHorizon(RoundContext, RunHookContext)` (lines 219–220), placed
  BETWEEN the drain and the epilogue. `CloseRoundAtHorizon` (§20b) moves miners off `ACTIVE_HASHING`,
  which sets a COHERENT `security_census_dirty[T]` + `latest_security_census[T]` — i.e. the `T` census
  is CREATED by horizon closure (lines 217–218).
- **The `T` epilogue** — `IF security_census_dirty[T]: CALL FinalizeEventTimeSecurityCensus(RoundContext,
  T)` (lines 222–223). The round now being terminal after horizon closure, this is a
  `terminal_stale_noop` that FINALISES the `T` census created by that closure and clears
  `security_census_dirty[T]` (lines 224–227).
- **`T` added to `finalised_event_times`** — `ADD t to finalised_event_times` (line 228), with the
  inline note "P1: `T` is ALWAYS finalised here."

So a no-ordinary-event-at-`T` run still executes drain (empty) → horizon closure → epilogue → finalise,
exactly as a run with events at `T` would (§0.7d-run steps 2–4, lines 282–288).

## 3. Gate 2 (`FinalizeSimulationRun` asserts terminal) and gate 3 (`T` always finalised)

**Gate 2 — `FinalizeSimulationRun` asserts a terminal round (§20a, lines 3126–3153).** The narrowed
finaliser carries a precondition that any nonterminal round "has been horizon-closed by
`CloseRoundAtHorizon` (§20b) inside `ProcessEventTime(T)`" (lines 3130–3131) and an explicit assertion
`ASSERT round_state in {ROUND_ACCEPTED, ROUND_ABORTED}` (line 3137). Because the sentinel of §1 always
interposes `CloseRoundAtHorizon` for a nonterminal round BEFORE `FinalizeSimulationRun` is reached, a
nonterminal round can NEVER reach `FinalizeSimulationRun` without horizon closure — the assertion would
otherwise fail. `FinalizeSimulationRun` then performs ONLY the single `FINAL_RUN_END`
`SettleResidencyBoundary` keyed by `(RunID, RUN_END)` (lines 3141–3142) + the I5/I6/I7 reconciliation
(lines 3143–3145) + `SET run_finalised <- true` (line 3146); it neither drains nor closes a round
(lines 3135–3136).

**Gate 3 — `T` is always in `finalised_event_times`.** The sentinel of §1 runs unconditionally after the
`t < T` loop (guarded only against double-execution), and `ProcessEventTime(T)` unconditionally reaches
`ADD t to finalised_event_times` (line 228) after its drain/closure/epilogue. Therefore `T ∈
finalised_event_times` holds by the time `FinalizeSimulationRun` is invoked — precisely the state its
precondition assumes (§20a, lines 3129–3131; §0.7d-run, lines 261–264). The guard on the sentinel
(`IF T not in finalised_event_times`, line 258) is the same predicate, so the sentinel is skipped only
in the already-finalised case, never leaving `T` unfinalised.

## 4. BEFORE (Stage 1O) vs AFTER (Stage 1P)

| Aspect | BEFORE — Stage 1O | AFTER — Stage 1P |
|--------|-------------------|------------------|
| Run-level loop guard | `WHILE ... t <= T` — the loop itself dispatched `T` | `WHILE ... t < T` (line 251) — the loop stops before `T` |
| Horizon-time step | Implicit: relied on an event existing at `T` (`is_horizon = (t == T)`) | Explicit synthetic sentinel `ProcessEventTime(T, is_horizon = true, allow_empty_horizon = true)` (lines 259–260) |
| No ordinary event at `T` | Horizon-time step could be skipped entirely | Sentinel forces the step; empty drain is legal (lines 196–199) |
| `allow_empty_horizon` input | Absent | Added, default `false`; `true` for the sentinel (lines 183, 185–186) |
| Run-once discipline | Loop-position dependent | Guarded `IF T not in finalised_event_times` (line 258) — exactly once |
| `FinalizeSimulationRun` reachability | Terminal-state assert present, but not guaranteed reached with closure when no `T` event | Sentinel guarantees closure precedes the assert (gate 2, line 3137) |

The AFTER behavior is a pure structural forcing of the horizon-time step: no accounting quantity, no
census value, and no A1 baseline is altered — the correction only ensures the step occurs exactly once.

## 5. Acceptance checks

| # | Check | Evidence | Result |
|---|-------|----------|--------|
| 1 | Run-level loop processes only `event_time < T` | §0.7d-run lines 251–253 | PASS |
| 2 | Exactly one horizon-sentinel `ProcessEventTime(T)`, guarded run-once | §0.7d-run lines 258–260; NOTE 267–271 | PASS |
| 3 | Sentinel runs even with NO event at `T` (empty drain legal) | §0.7d lines 189–199; §0.7d-run 279–281 | PASS |
| 4 | `allow_empty_horizon` added; permits synthetic call at `t = T` | §0.7d lines 183, 185–186, 191–194 | PASS |
| 5 | Horizon closure interposed BETWEEN drain and epilogue at `T`; creates coherent `T` census | §0.7d lines 217–220 | PASS |
| 6 | `T` epilogue is a `terminal_stale_noop` that finalises the `T` census and clears `dirty[T]` | §0.7d lines 222–228 | PASS |
| 7 | Gate 2: `FinalizeSimulationRun` asserts `round_state in {ROUND_ACCEPTED, ROUND_ABORTED}` | §20a lines 3130–3131, 3137 | PASS |
| 8 | Gate 3: `T` is ALWAYS added to `finalised_event_times` before the finaliser | §0.7d line 228; §0.7d-run 261–264 | PASS |

---

*Documentation only. The algorithm is named PoCol; the idle policy within PoCol is described here only
as a mechanism, with no energy, security, or fairness property claimed. The A1 accounting baseline
8.420833333 kWh is unchanged. The prohibited rebranded-algorithm-name variants are not used anywhere in
this document.*
