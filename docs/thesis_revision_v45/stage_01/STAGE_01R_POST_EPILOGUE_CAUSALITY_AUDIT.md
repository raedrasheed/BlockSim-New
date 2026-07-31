# Stage 1R — Post-Epilogue Causality Audit (R1/R2)

**Consensus mechanism.** This audit concerns the consensus specification named **PoCol**. Within PoCol,
**the idle policy within PoCol** is referenced solely as a mechanism; no property of the consensus
mechanism is claimed here. This is documentation only, describing the frozen behaviour of
`STAGE_01_PROTOCOL_PSEUDOCODE.md`; it neither introduces nor amends any procedure and adds no consensus
feature. The A1 accepted baseline of **8.420833333 kWh** is UNCHANGED by these corrections and is restated
only for provenance: R1 and R2 are **ordering and settlement** corrections to the event-time tail, never a
change to how simulated time or energy is counted. Any energy difference remains attributable **only to
reduced active power-time** (fewer / shorter `ACTIVE_HASHING` residency intervals), which
`ApplyMinerStateTransition`'s `residency_ledger` measures exactly as before (§0.7b); no boundary is added,
moved, or re-priced by either correction.

**Scope.** Two Stage-1R corrections to the canonical event-time tail:

- **R1 — No same-timestamp ordinary event after the ordinary drain.** Post-epilogue recovery application
  MUST NOT enqueue an ordinary event whose `target_event_time = t`; a zero modeled wake latency is
  represented at `next_representable_simulation_time(t)`, never at `t`.
- **R2 — One security epilogue, one post-application settlement.** The prior "epilogue #1 / epilogue #2"
  contradiction is removed; the tail is one security decision, at most one recovery application, and one
  non-deciding settlement.

Grounded in **§0.7d `ProcessEventTime`**, **§9 `FinalizeEventTimeSecurityCensus` / `SecurityFloorEvaluate`**,
and **§10a** (`ApplyRecoveryCompletionAfterEpilogue`, `CompleteSecurityRecovery`,
`RecoveryAssignmentContinuationEvent`, `FinalizePostRecoveryApplicationState`).

## 1. The canonical event-time tail (§0.7d `ProcessEventTime`)

For a given `event_time = t`, §0.7d `ProcessEventTime` first DRAINS `t` to quiescence: the drain `LOOP`
dispatches every ordinary and delta-cycle event at `t` in `(delta_cycle, microphase, stable_tie_key, seq)`
order and `BREAK`s only when "no ordinary event remains at `event_time = t`". ONLY THEN does it run the
**canonical event-time tail (R2)** as four ordered actions:

1. `FinalizeEventTimeSecurityCensus(t)` — EXACTLY ONCE if `security_census_dirty[t]`; the sole security-floor
   decision for `t` (§9; I-01/I-02).
2. `ApplyRecoveryCompletionAfterEpilogue(t)` — applies AT MOST ONE fresh, matching, due decision (Q2/R4).
3. `FinalizePostRecoveryApplicationState(t)` — EXACTLY ONCE when required; a SETTLEMENT, not a second
   floor decision.
4. Two finalisation ASSERTs, THEN `ADD t to finalised_event_times`:
   - §0.7d step (4) `ASSERT no ordinary event remains with event_time = t` — the R1 guard;
   - §0.7d step (4) `ASSERT security_census_dirty[t] = false` — the R2 guard.

Because `t` is added to `finalised_event_times` only after both ASSERTs pass, every property below reduces to
showing that no tail action re-populates an ordinary event at `t` (R1) and that the dirty flag is settled
without a second decision (R2).

## 2. R1 — No same-timestamp ordinary event after the ordinary drain

The tail runs strictly AFTER the drain `BREAK`, so any ordinary event seated at `target_event_time = t` by a
tail action would be stranded past its own `event_time` and would fail §0.7d step (4)'s first ASSERT. The
pseudocode forbids every such seat:

- **`ApplyRecoveryCompletionAfterEpilogue` (§10a)** performs only decision-status transitions
  (`SetRecoveryDecisionStatus`) and a single internal call to `CompleteSecurityRecovery`. It never calls
  `ScheduleEvent`. Its NOTE states the exit transition "enqueues NOTHING at t — branch C defers to
  `RecoveryAssignmentContinuationEvent` at `next_representable_simulation_time(t)`."
- **`CompleteSecurityRecovery` branch C (§10a; RESTORED requiring redistribution / reserve assignment)** is
  the one branch that needs `ReserveActivate` / `RangeReassign` / `StartWake` (which can seat same-time
  `WakeCompleteEvent`s at zero modeled latency, H5). R1 forbids doing that work at `t`. The branch instead
  `TRANSITION round_state -> ASSIGNMENT`, sets `t_cont <- next_representable_simulation_time(dispatch_envelope.event_time)`
  (strictly later than `t` — zero modeled latency is `t_cont`, not `t`), and seats **exactly one**
  `RecoveryAssignmentContinuationEvent` at `target_event_time = t_cont`. It enqueues NOTHING at `t`. If
  `t_cont > T` the continuation is rejected by O2 (§0.7e) and `CloseRoundAtHorizon` (§20b) governs run end;
  still nothing is seated at `t`.
- **`RecoveryAssignmentContinuationEvent` (§10a)** is the deferred branch-C worker, dispatched at
  `t_cont > t`. Its `ReserveActivate` / `RangeReassign` / `StartWake` and its `CompleteAssignmentPhase`
  (the SOLE `ASSIGNMENT -> HASHING` owner) seat their `WakeCompleteEvent`s "at THIS event_time or later —
  NEVER at the already-finalised application event_time." So all of branch C's participation-changing enqueues
  occur at `>= t_cont > t`.
- **Branches A / B / D and `FinalizePostRecoveryApplicationState`** call no `ScheduleEvent` at `t` at all
  (see §4).

Since no tail action seats an ordinary event at `t`, §0.7d step (4)'s ASSERT `no ordinary event remains with
event_time = t` holds, and `t` is finalised with the drain still complete. This is a pure re-timing of the
assignment rebuild; it changes no residency boundary, so the A1 baseline (8.420833333 kWh) is unaffected.

## 3. R2 — One security epilogue, one post-application settlement

R2 removes the earlier contradiction whereby `FinalizeEventTimeSecurityCensus` was called "exactly once" yet
invoked as "epilogue #1" and "epilogue #2." The §0.7d tail now names three DISTINCT procedures with disjoint
roles:

- **(1) `FinalizeEventTimeSecurityCensus(t)` — the ONE security decision.** §9 states it "runs EXACTLY ONCE
  per event_time" and is "the SOLE caller of `SecurityFloorEvaluate`." It is the only place at `t` that
  records a breach or mints a recovery episode / decision. It is invoked at most once by the tail (guarded by
  `IF security_census_dirty[t]`).
- **(2) `ApplyRecoveryCompletionAfterEpilogue(t)` — apply at most one due decision.** Its exit transition
  changes `round_state` only (via internal `CompleteSecurityRecovery`); at most one outcome per episode (O4).
- **(3) `FinalizePostRecoveryApplicationState(t)` — the ONE settlement, NOT a second decision.** §10a is
  explicit: if the application did not re-dirty `t` it returns `post_recovery_settlement_noop`; otherwise it
  ARCHIVES the post-application census as an OBSERVATION and stamps it via `CommitSecurityCensus` with
  `census_source = POST_RECOVERY_APPLICATION` over the SAME `H_*` values (R5 — no re-count of time or energy),
  then `CLEAR security_census_dirty[t]`. Its NOTE binds the three prohibitions: it "NEVER calls
  `SecurityFloorEvaluate`, NEVER seats a recovery decision, and NEVER enqueues an event at t." For an
  UNRECOVERABLE application that closed the round it records a `terminal_census_observation`; for a RESTORED
  exit it records a `post_recovery_application_observation` of the already-non-breached census. Any NEW
  applicability census produced by ACTUAL later miner activation is generated at the strictly-later
  continuation `event_time` (§10a `RecoveryAssignmentContinuationEvent`), never at `t`.

Because (3) clears the dirty flag WITHOUT a second `SecurityFloorEvaluate`, §0.7d step (4)'s ASSERT
`security_census_dirty[t] = false` holds, and no second floor decision can re-mint an episode at `t`. The
settlement re-stamps provenance only; it re-prices nothing, so the A1 baseline (8.420833333 kWh) is
unaffected.

## 4. Causal-order table — every post-epilogue enqueue site at `t`

| # | Post-epilogue site (§10a) | Action at `t` | Ordinary event enqueued? | Target `event_time` |
|---|---------------------------|---------------|--------------------------|---------------------|
| 1 | `ApplyRecoveryCompletionAfterEpilogue` | status transitions + one internal `CompleteSecurityRecovery` call | NO — no `ScheduleEvent` | — (nothing) |
| 2 | `CompleteSecurityRecovery` branch A (RESTORED, live propagation) | `TransitionRoundState(SOLUTION_PROPAGATION)`; existing candidate events PRESERVED (G8) | NO — no new seat | — (nothing) |
| 3 | `CompleteSecurityRecovery` branch B (RESTORED, unchanged coverage) | `TransitionRoundState(HASHING)` | NO — no new seat | — (nothing) |
| 4 | `CompleteSecurityRecovery` branch C (RESTORED, redistribution / reserves) | `-> ASSIGNMENT` + seat ONE `RecoveryAssignmentContinuationEvent` | YES — exactly one | `t_cont = next_representable_simulation_time(t) > t` |
| 5 | `CompleteSecurityRecovery` branch D (UNRECOVERABLE) | `RoundAbort(floor_unrecoverable)` — CANCELS live events, `CloseRoundAssignments`; `-> ROUND_ABORTED` | NO — cancels, never seats at `t` | — (nothing) |
| 6 | `FinalizePostRecoveryApplicationState` | `CommitSecurityCensus(... POST_RECOVERY_APPLICATION)` + `CLEAR dirty[t]` | NO — map write only | — (nothing) |
| 7 | `RecoveryAssignmentContinuationEvent` (deferred branch-C worker; dispatched at `t_cont`) | `ReserveActivate` / `RangeReassign` / `StartWake` + `CompleteAssignmentPhase` | its `WakeCompleteEvent`s seat at `t_cont` or later | `>= t_cont > t` |

Every site either enqueues nothing at `t` (rows 1, 2, 3, 5, 6) or enqueues strictly later (rows 4 and its
deferred worker 7). No row targets `t`.

## 5. Result

The Stage-1R tail is causally closed at each `event_time = t`: §0.7d `ProcessEventTime` drains `t` to
quiescence, then runs `FinalizeEventTimeSecurityCensus(t)` once (§9), applies at most one due decision
(`ApplyRecoveryCompletionAfterEpilogue`, §10a), and settles once
(`FinalizePostRecoveryApplicationState`, §10a) without a second floor decision. No post-epilogue procedure
seats an ordinary event at `t` — branch C's assignment rebuild is deferred to a single
`RecoveryAssignmentContinuationEvent` at `next_representable_simulation_time(t) > t` — so §0.7d step (4)'s two
ASSERTs (`no ordinary event remains with event_time = t` and `security_census_dirty[t] = false`) both hold
before `t` is added to `finalised_event_times`. Both corrections are ordering / settlement only; they change
no residency boundary and no cost model, so the A1 accepted baseline of 8.420833333 kWh is unchanged and any
energy difference remains attributable solely to reduced active power-time.

## Footer

This document is documentation only; it makes no property claim about the consensus mechanism. The consensus
mechanism is named **PoCol**, and **the idle policy within PoCol** is referenced solely as a mechanism. The
A1 baseline of **8.420833333 kWh** is unchanged. The prohibited rebranded-algorithm-name variants are not used anywhere in this document.
