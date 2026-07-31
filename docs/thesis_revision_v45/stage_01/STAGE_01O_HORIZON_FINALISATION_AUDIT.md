# Stage 1O — Horizon-Finalisation Audit (O1)

This is a documentation-only paper audit of Stage 1O correction **O1 — the horizon-finalisation
refactor** — as edited in `docs/thesis_revision_v45/stage_01/STAGE_01_PROTOCOL_PSEUDOCODE.md`. The
consensus algorithm is named **PoCol**; the idle policy within PoCol is referred to here only as a
mechanism, and this audit makes no energy, security, or fairness claim about it. The A1 accounting
baseline is **8.420833333 kWh** and is UNCHANGED by O1: the refactor rearranges *where* the run-end
close, drain, settle, and reconciliation are structurally seated in the pseudocode, and edits no
accounting quantity. Scope is strictly O1 — the split of the former monolithic run finaliser into the
event-loop driver (`ProcessEventTime`, §0.7d), the run-level driver (`RunEventLoopToHorizon`,
§0.7d-run), the named horizon-close hook (`CloseRoundAtHorizon`, §20b), and the narrowed run-level
finaliser (`FinalizeSimulationRun`, §20a). Every claim below is checked against the pseudocode as
edited; no behavior is inferred beyond what the text states.

## 1. Canonical horizon sequence (§0.7d-run steps 1–5)

The canonical horizon sequence is stated explicitly in `RunEventLoopToHorizon` (§0.7d / §0.7d-run) and
its adjoining prose (lines 246–268). Reading it against the procedures, the ordered steps are:

1. **Process every `event_time < T`** — `RunEventLoopToHorizon` selects the earliest unprocessed
   `event_time t` and calls `ProcessEventTime(RoundContext, t, is_horizon = (t == T))` for each one up
   to AND INCLUDING `T`.
2. **Drain `T` to quiescence** — inside `ProcessEventTime(T)` the drain LOOP processes all ordinary and
   delta-cycle events at `T` in deterministic `(delta_cycle, microphase, stable_tie_key, seq)` order
   until no ordinary event remains at `T`.
3. **Horizon-close if nonterminal** — `IF is_horizon AND round_state NOT in {ROUND_ACCEPTED,
   ROUND_ABORTED}: CALL CloseRoundAtHorizon(RoundContext)` (§20b), interposed BETWEEN the drain and the
   epilogue.
4. **Run the `T` epilogue** — `FinalizeEventTimeSecurityCensus(RoundContext, T)` runs once (if
   `security_census_dirty[T]`); the round now being terminal, it is a `terminal_stale_noop` that merely
   clears `security_census_dirty[T]`, then `ADD T to finalised_event_times`.
5. **Only then, the run-level finaliser** — after `ProcessEventTime(T)` returns,
   `RunEventLoopToHorizon` invokes `FinalizeSimulationRun(RunContext, RoundContext)` (§20a) as a
   post-`ProcessEventTime(T)` run-level hook.

Steps 2–4 occur strictly inside `ProcessEventTime(T)`; step 5 occurs strictly after it returns. The
ordering is textual and structural, not scheduled.

## 2. `ProcessEventTime` as the sole event-loop driver, never re-entered

§0.7d states, and the `ProcessEventTime` NOTE (lines 224–227) repeats, that `ProcessEventTime` is the
SOLE event-loop driver and **no handler ever re-enters it**. `RunEventLoopToHorizon` (§0.7d-run) only
SELECTS the next `event_time` — "this run-level loop only SELECTS the next event_time and never itself
dispatches an event" (lines 234–235) — and dispatch of every ordinary/delta-cycle event happens only
within the `ProcessEventTime` drain LOOP.

Under O1 the former re-entrant drain is eliminated at its source. The old `FinalizeSimulationRun`
carried an internal `DRAIN the event queue to quiescence for every event_time <= T`; that step is
REMOVED (§0.7d-run lines 266–268; §20a lines 3010–3011, NOTE 3023–3025). Because `ScheduleEvent`
rejects any `target_event_time > T` (O2/§0.7e), no ordinary event ever remains beyond `T`, so the run
driver's per-`event_time` `ProcessEventTime` sweep has already drained everything `<= T` before the
finaliser is reached. There is consequently no second draining locus and no path by which a finaliser
re-enters the event loop.

## 3. `CloseRoundAtHorizon` (§20b) — the named horizon-close hook

`CloseRoundAtHorizon` is a NEW named run-level hook (§20b, lines 3031–3065). The audited procedure text
shows it:

- is invoked ONLY by `ProcessEventTime(T)`, AFTER the `T` drain and BEFORE the `T` epilogue —
  interposed BETWEEN drain and epilogue (lines 3034, 3061), so the round is already terminal when the
  epilogue runs;
- closes the still-nonterminal round through the single closure path `CloseRoundAssignments(RoundContext,
  disposition = ROUND_ABORTED, stop_reason = ROUND_ABORTED, dispatch_envelope = horizon_envelope)`
  (lines 3054–3055);
- records a DISTINCT horizon-end disposition `RECORD horizon_end_disposition(RoundID) <-
  closed_at_horizon` (line 3058), so run-end closure is auditable as horizon-end rather than an
  unrecoverable-condition abort;
- records `round_terminal_time(RoundID) <- run_horizon_T` via `CloseRoundAssignments` and then
  `TRANSITION round_state -> ROUND_ABORTED` (lines 3052, 3059);
- uses ONE deterministic horizon envelope `{ event_time = run_horizon_T, delta_cycle =
  horizon_close_delta_cycle, event_seq = horizon_close_event_seq }` (lines 3049–3050);
- performs NO residency settle — `CloseRoundAssignments performs NO residency finalisation (M4)` and the
  settle is deferred to the subsequent `FinalizeSimulationRun` FINAL_RUN_END settle (lines 3052–3053,
  3063);
- is a DIRECT run-level CALL, NOT a queued event (lines 3036–3037).

## 4. `FinalizeSimulationRun` (§20a) — narrowed responsibilities

O1 NARROWS `FinalizeSimulationRun` (§20a, lines 2988–3029). It is NO LONGER seated on the ordinary event
queue and carries NO `dispatch_envelope` (lines 2991, 3002–3003); the former internal DRAIN is REMOVED
(lines 3010–3011); the horizon-close step is REMOVED and now lives in `CloseRoundAtHorizon` (lines 3010,
3024–3025). It performs ONLY: (1) the single `SettleResidencyBoundary(RoundContext, mode = FINAL_RUN_END,
boundary_id = (RunID, RUN_END))` — the ONLY FINAL_RUN_END settle in the whole specification (lines
3016–3017); (2) the I5/I6/I7 reconciliation (lines 3018–3020); then (3) `SET run_finalised <- true`
(line 3021). It is guarded exactly-once by `IF run_finalised: RETURN run_already_finalised` (line 3009),
and asserts `round_state in {ROUND_ACCEPTED, ROUND_ABORTED}` on entry (line 3012).

| Aspect | BEFORE (Stage 1N) | AFTER (Stage 1O / O1) |
|--------|-------------------|------------------------|
| Queue seating | Seated on ordinary event queue, carried a dispatch_envelope | Run-level hook; NOT queued; carries NO dispatch_envelope |
| Drain to quiescence `<= T` | Performed internally by the finaliser | REMOVED — the run driver drains via `ProcessEventTime` |
| Horizon-close of nonterminal round | Performed internally by the finaliser | REMOVED — moved to `CloseRoundAtHorizon` (§20b) |
| Run-end residency settle | Performed (FINAL_RUN_END) | Retained — the single `SettleResidencyBoundary(FINAL_RUN_END, (RunID, RUN_END))` |
| I5/I6/I7 reconciliation | Performed | Retained |
| `run_finalised` guard | Exactly-once guard | Retained — exactly-once |

The AFTER column is precisely {single settle + reconcile + set `run_finalised`}, a run-level hook.

## 5. `RUN_FINALISE` removed from the queue map; run-level hooks never enqueued

`RUN_FINALISE` is REMOVED from the ordinary microphase queue map. §0.7g states `RUN_FINALISE` is **NOT**
in the queue map (lines 391–394), and the §0.7g-driver seating table no longer lists
`FinalizeSimulationRun`: "`FinalizeSimulationRun` and `CloseRoundAtHorizon` are RUN-LEVEL hooks (NOT
queued events) and therefore do NOT appear in the seating table below" (lines 406–411), with a closing
note that neither is enqueued and nothing is scheduled past `T` (lines 425–428). §21 documents both as
run-level hooks outside the inter-type priority list — `CloseRoundAtHorizon` "NOT a queued event, NOT
the same as RoundAbort (item 1)" and `FinalizeSimulationRun` "NOT a queued microphase (RUN_FINALISE is
NOT in the queue map), NOT a round event" (lines 3154–3159). The epilogue at `T` is a
`terminal_stale_noop`: because `CloseRoundAtHorizon` has already made the round terminal before the
epilogue, `FinalizeEventTimeSecurityCensus(T)` records no observation, no breach, no transition, and
only clears `security_census_dirty[T]` (§0.7d lines 210–214; §0.7d-run lines 261–262).

## 6. Acceptance checks

| # | Check | Evidence | Result |
|---|-------|----------|--------|
| 1 | `ProcessEventTime` is the sole event-loop driver; no handler re-enters it | §0.7d lines 224–227, 234–235 | PASS |
| 2 | Canonical horizon sequence: events `< T`; drain `T`; close-if-nonterminal; epilogue; then finaliser | §0.7d-run lines 256–264; §0.7d lines 203–215 | PASS |
| 3 | `CloseRoundAtHorizon` interposed BETWEEN drain and epilogue, distinct disposition, one envelope, no residency settle | §20b lines 3034–3063 | PASS |
| 4 | `FinalizeSimulationRun` no longer queued, carries no dispatch_envelope, internal DRAIN and horizon-close removed | §20a lines 2991, 3002–3003, 3010–3011, 3024–3025 | PASS |
| 5 | `FinalizeSimulationRun` performs ONLY settle + I5/I6/I7 + `run_finalised`, guarded exactly once | §20a lines 3009, 3016–3021 | PASS |
| 6 | `FinalizeSimulationRun` invoked as a post-`ProcessEventTime(T)` run-level hook, not a queued event | §0.7d-run lines 240–244, 255 | PASS |
| 7 | `RUN_FINALISE` removed from queue map; run-level hooks absent from seating table | §0.7g lines 391–394; §0.7g-driver lines 406–428; §21 lines 3154–3159 | PASS |
| 8 | `T` epilogue is a `terminal_stale_noop` clearing `security_census_dirty[T]` | §0.7d lines 210–214; §0.7d-run lines 261–262 | PASS |

---

*Documentation only. The algorithm is named PoCol; the idle policy within PoCol is described here only
as a mechanism, with no energy, security, or fairness property claimed. The A1 accounting baseline
8.420833333 kWh is unchanged. The prohibited rebranded-algorithm-name variants are not used anywhere in
this document.*
