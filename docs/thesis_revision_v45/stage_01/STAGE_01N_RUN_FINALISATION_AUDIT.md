# Stage 1N — Run Finalisation Audit (N1)

A structural audit of Stage-1N correction **N1 — separate round abort from simulation end** — in the
**PoCol** protocol pseudocode (`STAGE_01_PROTOCOL_PSEUDOCODE.md`), describing PoCol with **the idle policy
within PoCol** enabled. N1 splits two concerns that Stage-1M had bundled inside `RoundAbort` (§20): (a) the
termination of ONE round, and (b) the finalisation of the whole simulation RUN at the fixed horizon `T`.
After N1, `RoundAbort` (§20) terminates a single round — it dispositions live candidates, closes assignments
through `CloseRoundAssignments` (§17a) which records `round_terminal_time` at the abort `event_time`,
transitions to `ROUND_ABORTED`, and returns control — and performs NO run-end residency settle and NO
horizon reconciliation. The former in-line `SettleResidencyBoundary(FINAL_RUN_END)` call and the
`ASSERT ... durations reconcile to horizon T` line are REMOVED from `RoundAbort`. A NEW run-level finaliser,
`FinalizeSimulationRun` (§20a), guarded by `run_finalised` (§0.8), is the SINGLE owner of run-end
accounting: it runs EXACTLY ONCE at the horizon `T`, drains events to `T`, horizon-closes a nonterminal
final round, performs the ONE `SettleResidencyBoundary(mode = FINAL_RUN_END, boundary_id = (RunID, RUN_END))`
(§1a), and only then runs the I5/I6/I7 reconciliation. This document is documentation only; it audits
wording and control structure, describes only the idle policy within PoCol, introduces no new consensus
feature, and claims **no** security, fairness, energy, or incentive property. The A1 baseline
(`8.420833333 kWh`) is unchanged.

---

## 1. What N1 corrected (round abort ≠ simulation end)

Stage-1M's `RoundAbort` (§20) carried, in-line, both the round-termination steps AND a run-end settle
(`SettleResidencyBoundary` mode `FINAL_RUN_END`) followed by the horizon-reconciliation asserts. That
conflated a round event (`RoundAbort`, which may occur at any `t < T` and be followed by another round)
with the run's single horizon finalisation. An early abort would then have closed residency at the horizon
`T` even though simulated time remained. N1 separates the two along one axis:

1. **`RoundAbort` (§20) is round-scoped.** Its executable body dispositions the round's candidates, clears
   the propagation registries, calls `CloseRoundAssignments` (§17a) — which records `round_terminal_time`
   at the abort `event_time` and performs NO residency/energy finalisation (M4) — retains the zero-block
   outcome, and transitions `round_state -> ROUND_ABORTED`. It performs NO `FINAL_RUN_END` settle and NO
   `ASSERT ... reconcile to horizon T`. The §20 comment records that *"the former
   `SettleResidencyBoundary(FINAL_RUN_END)` and the `ASSERT durations reconcile to horizon T` are REMOVED —
   an abort at `t < T` must NEVER close residency at the horizon `T`."*
2. **`FinalizeSimulationRun` (§20a) is run-scoped and generic.** It is the NEW single run-level finaliser,
   guarded by the per-run boolean `run_finalised` (§0.8), seated on the queue at `(T, RUN_FINALISE)`
   (§0.7g/N3). It runs EXACTLY ONCE at the horizon `T` for a run whose last round is `ROUND_ACCEPTED`,
   `ROUND_ABORTED`, or nonterminal alike; it owns the ONE `FINAL_RUN_END` settle and the I5/I6/I7
   reconciliation. Its §20a intro states that *"`RoundAbort` (§20) closes ONE round and reconciles NOTHING
   to the horizon; the run-end residency settle and the I5/I6/I7 reconciliation live HERE."*
3. **`SettleResidencyBoundary` (§1a) `FINAL_RUN_END` is re-owned.** The §1a `FINAL_RUN_END` precondition now
   reads *"INVOKED ONLY by `FinalizeSimulationRun` (§20a/N1), never by `RoundAbort`"* — moving the sole
   invocation site of the run-end settle from the round procedure to the run procedure. The
   `REBASE_TO_NEXT_ROUND` mode (owned by `RoundInitialise`, §1) is unchanged by N1.

The §0.8 registry block records the new state normatively: `run_finalised` is *"a per-RUN boolean, false
until `FinalizeSimulationRun` (§20a) runs at the horizon `T`; it guards the SINGLE run-end finalisation so a
re-dispatch is a no-op … Initialised false once at run start and preserved across rounds (I-04). RunID is
the fixed per-run identifier used in the `(RunID, RUN_END)` boundary_id."* The `rebased_boundaries` comment
now records the run-end key as `(RunID, RUN_END)` *"for the single run-end settle (N1)"* — previously
`(RoundID_current, RUN_END)` set by `RoundAbort`.

| Aspect | Stage-1M (M4) | Stage-1N (N1) |
|---|---|---|
| Who performs the run-end `FINAL_RUN_END` settle | `RoundAbort` (§20), in-line, before the I5/I6/I7 asserts | `FinalizeSimulationRun` (§20a) ONLY — the single run-level finaliser |
| Who performs the horizon reconciliation (I5/I6/I7) | `RoundAbort` (§20), in-line asserts | `FinalizeSimulationRun` (§20a), AFTER the final settle |
| `RoundAbort` (§20) scope | ONE round + an in-line run-end settle + horizon asserts | ONE round ONLY (disposition + `CloseRoundAssignments` + terminal transition) |
| Run-end settle `boundary_id` | `(RoundID_current, RUN_END)` (round-keyed) | `(RunID, RUN_END)` (run-keyed) |
| `SettleResidencyBoundary` `FINAL_RUN_END` invoker (§1a) | `RoundAbort` | `FinalizeSimulationRun` ONLY, never `RoundAbort` |
| After an early abort at `t < T` | in-line run-end close at `T` inside `RoundAbort` | `RoundInitialise` (R21) restarts a round; no horizon close |
| Run-end guard | none (each `RoundAbort` settled) | `run_finalised` (§0.8) — runs exactly once |
| Accepted final round run-end path | `ValidBlockAccept` closure + (separately) no in-`RoundAbort` settle | the SAME `FinalizeSimulationRun` (§20a) as an aborted/nonterminal final round |
| `CloseRoundAssignments` (§17a) | records `round_terminal_time` only (M4) | records `round_terminal_time` only (M4) — unchanged |
| Boundary energy | ZERO `E_transition`/`E_coordination` at a settle | ZERO `E_transition`/`E_coordination` at a settle — unchanged |
| A1 baseline | `8.420833333 kWh` | `8.420833333 kWh` — unchanged |

## 2. `RoundAbort` (§20) — the round-scoped executable body

The §20 procedure, in EFFECTS order, is entirely round-scoped. Its substantive residency/accounting step is
the single `CloseRoundAssignments` call (which itself performs NO residency/energy finalisation, M4), plus
the housekeeping that dispositions the round's candidates and the terminal transition:

```
RECORD round_abort(RoundID, TemplateID, reason)
IF any breach_events exist: LEAVE them intact                       # I16
# (1) disposition every live candidate and clear the propagation registries
FOR EACH cpc in SORT(active_propagation_set BY CandidateID ascending):
  SET status(cpc) <- CANCELLED ; CANCEL certificate_arrival_events(cpc) ; CANCEL block_arrival_event(cpc)
CLEAR active_propagation_set ; CLEAR acceptance_batch_registry
# (2)-(3) centralised closure; records round_terminal_time at the abort event_time (M4: no residency finalise)
CALL CloseRoundAssignments(RoundContext, disposition = ROUND_ABORTED, stop_reason = ROUND_ABORTED,
                           dispatch_envelope = dispatch_envelope)
# N1: NO residency settle here. The former SettleResidencyBoundary(FINAL_RUN_END) and the
#     ASSERT durations reconcile to horizon T are REMOVED.
RETAIN zero-block/partial outcome in dataset                        # I14; NA metrics per I15
# (4) terminal transition
TRANSITION round_state -> ROUND_ABORTED                             # bumps state_version (G10)
# (5) RETURN control (sim driver may start another round via RoundInitialise, or FinalizeSimulationRun at T)
```

The §20 NOTE confirms the scope: *"`RoundAbort` terminates ONE round and reconciles NOTHING to the horizon;
an early abort (`t < T`) is followed by `RoundInitialise` when simulated time remains. The generic final-run
flush (drain, horizon-close a nonterminal round, single `FINAL_RUN_END` settle, then I5/I6/I7
reconciliation) is `FinalizeSimulationRun` (§20a), which owns run-end accounting for ACCEPTED and ABORTED
final rounds alike."* No `SettleResidencyBoundary`, no `run_horizon_T`, and no `I5`/`I6`/`I7` assert appears
anywhere in the §20 body.

## 3. `FinalizeSimulationRun` (§20a) — the single run-level finaliser

The §20a procedure is the ONE owner of run-end horizon reconciliation, guarded so it runs exactly once:

```
IF run_finalised: RETURN run_already_finalised                     # N1: EXACTLY ONCE per run
# (1) DRAIN the event queue to quiescence for every event_time <= T (I-02; nothing scheduled past T)
DRAIN the event queue to quiescence for every event_time <= T
# (2) horizon-close a NONTERMINAL final round via the declared horizon-end disposition (D7)
IF round_state NOT in {ROUND_ACCEPTED, ROUND_ABORTED}:
  CALL CloseRoundAssignments(RoundContext, disposition = ROUND_ABORTED, stop_reason = ROUND_ABORTED,
                             dispatch_envelope = dispatch_envelope)
  RECORD horizon_end_disposition(RoundID) <- closed_at_horizon     # I14/I15 NA metrics retained
  TRANSITION round_state -> ROUND_ABORTED                          # terminal at T
# (3) the ONE FINAL_RUN_END settle in the whole specification, keyed by (RunID, RUN_END); NO reopen
CALL SettleResidencyBoundary(RoundContext, mode = FINAL_RUN_END, boundary_id = (RunID, RUN_END))
# (4) I5/I6/I7 reconciliation runs ONLY AFTER the final settle
ASSERT per-miner state-energy sums (I6) ; ASSERT network energy sum (I7)
ASSERT per-miner durations reconcile to the horizon T (I5)
SET run_finalised <- true
```

Its §20a NOTE states it is *"the SINGLE owner of run-end horizon reconciliation, run EXACTLY ONCE at `T` for
a run whose last round is ACCEPTED, ABORTED, or nonterminal alike. `RoundAbort` performs NO horizon settle
… This procedure drains to `T`, horizon-closes a nonterminal round, performs the ONE `FINAL_RUN_END`
`SettleResidencyBoundary`, and THEN runs the I5/I6/I7 reconciliation; it never reopens an interval (the run
is over)."* Step (2) branches on the final round's terminal status, so an ACCEPTED or ABORTED final round
skips the horizon close and proceeds straight to the SAME single settle at step (3) — the generic finaliser
does not care how the last round ended.

## 4. Acceptance properties (asserted with evidence)

| # | Property | Verdict | Ground in the current pseudocode |
|---|---|---|---|
| P1 | `RoundAbort` (§20) NEVER performs `FINAL_RUN_END` settlement — its executable body is candidate disposition + `CloseRoundAssignments` + the `ROUND_ABORTED` terminal transition | HOLDS | §20 body (§2 above): no `SettleResidencyBoundary`, no `run_horizon_T`; §20 comment *"the former `SettleResidencyBoundary(FINAL_RUN_END)` and the `ASSERT durations reconcile to horizon T` are REMOVED"* |
| P2 | An early aborted round (`t < T`) can be followed by `RoundInitialise` | HOLDS | §20 step (5) *"the sim driver may start another round via `RoundInitialise`"*; §20 NOTE *"an early abort (`t < T`) is followed by `RoundInitialise`"*; round SM R21 (`ROUND_ABORTED -> ROUND_INITIALISING`); §2.10 / §3.14 |
| P3 | ONE generic `FinalizeSimulationRun` (§20a) owns final horizon reconciliation | HOLDS | §20a steps (3)-(4): the ONE `FINAL_RUN_END` settle + the I5/I6/I7 asserts; §20a NOTE *"the SINGLE owner of run-end horizon reconciliation"*; I19 *"the `FINAL_RUN_END` settle is owned SOLELY by `FinalizeSimulationRun`"* |
| P4 | Accepted AND aborted final rounds use the SAME run-level finaliser | HOLDS | §20a step (2) `IF round_state NOT in {ROUND_ACCEPTED, ROUND_ABORTED}` skips the horizon close for both, then both reach the SAME step (3) settle; §20a intro *"regardless of whether the last round ended `ROUND_ACCEPTED`, `ROUND_ABORTED`, or remained NONTERMINAL at `T`"* |
| P5 | An early `RoundAbort` at `t < T` NEVER closes residency at `T` | HOLDS | §20 comment *"an abort at `t < T` must NEVER close residency at the horizon `T`. The residency boundary is settled ONLY by `SettleResidencyBoundary`, via the next `RoundInitialise` … OR `FinalizeSimulationRun` at the horizon"*; §3.14 *"An early `RoundAbort` at `t < T` therefore NEVER closes residency at the horizon"* |

**On P1 (no run-end settle in `RoundAbort`).** The §20 body reaches a residency interval only through
`CloseRoundAssignments` (§17a), which — after M4 — records `round_terminal_time <- dispatch_envelope.event_time`
(the abort `event_time`) and performs NO residency/energy finalisation. `RoundAbort` writes no
`run_horizon_T`, invokes no `SettleResidencyBoundary`, and asserts no I5/I6/I7. The abort `event_time` it
records is the boundary instant the LATER settle reads — either the next `RoundInitialise`
(`REBASE_TO_NEXT_ROUND`) or `FinalizeSimulationRun` (`FINAL_RUN_END`).

**On P4 (same finaliser for accepted and aborted).** `FinalizeSimulationRun` step (2) is a single guarded
branch: only a NONTERMINAL final round is horizon-closed; an ACCEPTED final round (closed earlier by
`ValidBlockAccept -> CloseRoundAssignments`) and an ABORTED final round (closed by `RoundAbort ->
CloseRoundAssignments`) are both already terminal, so both skip step (2) and share the ONE step-(3) settle
and step-(4) reconciliation. There is no accept-specific or abort-specific run-end path.

**On P5 (no horizon close on early abort).** Because the `FINAL_RUN_END` settle is removed from `RoundAbort`
and re-owned exclusively by `FinalizeSimulationRun` at `(T, RUN_FINALISE)`, an abort that fires while
simulated time remains records only its own `round_terminal_time` at `t < T`; the continuing idle occupancy
is next settled by the following `RoundInitialise` at that same `t` (`REBASE_TO_NEXT_ROUND`), NOT at `T`. The
horizon close at `T` happens once, later, in the run finaliser.

## 5. Ownership table — the `FINAL_RUN_END` residency settle

Every site that could reach the run-end `FINAL_RUN_END` settlement, and its sole owner after N1.

| Site (procedure §) | Run-end `FINAL_RUN_END` settle? | I5/I6/I7 horizon reconciliation? | Ground |
|---|---|---|---|
| `FinalizeSimulationRun` §20a | YES — performs the ONE `SettleResidencyBoundary(mode = FINAL_RUN_END, boundary_id = (RunID, RUN_END))` | YES — the I5/I6/I7 asserts, run ONLY AFTER the settle | §20a steps (3)-(4); §20a NOTE |
| `RoundAbort` §20 | NO — former `SettleResidencyBoundary(FINAL_RUN_END)` REMOVED | NO — former `ASSERT ... reconcile to horizon T` REMOVED | §20 body + §20 comment |
| `RoundInitialise` §1 (ELSE branch) | NO — invokes `REBASE_TO_NEXT_ROUND` only, `boundary_id = (prior_RoundID, RoundID_current)` | NO | §1 ELSE branch; §1a `REBASE_TO_NEXT_ROUND` |
| `SettleResidencyBoundary` §1a (`FINAL_RUN_END`) | executes the settle, but INVOKED ONLY by `FinalizeSimulationRun` (§20a/N1), never by `RoundAbort` | closes at `run_horizon_T`, NO reopen | §1a `FINAL_RUN_END` precondition + branch |
| `CloseRoundAssignments` §17a | NO — records `round_terminal_time` ONLY (M4) | NO | §17a M4 comment; `RECORD round_terminal_time(RoundID)` |
| `CompleteSecurityRecovery` §10a (branch D) | NO — calls `RoundAbort`, which never settles residency (N1) | NO | §10a NOTE *"never settles residency (that is `FinalizeSimulationRun` / the next `RoundInitialise`, N1)"* |

After N1, exactly one procedure (`FinalizeSimulationRun`, §20a) invokes the `FINAL_RUN_END` settle and owns
the horizon reconciliation; `SettleResidencyBoundary` (§1a) remains the sole executor of the settle itself,
and `ApplyMinerStateTransition` (§0.9) remains the sole owner of residency intervals for an ACTUAL
state-change (unchanged by N1).

## 6. Comparison — `RoundAbort` (§20) vs `FinalizeSimulationRun` (§20a)

| Action | `RoundAbort` (§20) | `FinalizeSimulationRun` (§20a) |
|---|---|---|
| Scope | ONE round | The whole RUN |
| Guard against re-entry | none (round SM prevents re-abort of a terminal round) | `run_finalised` (§0.8): `IF run_finalised: RETURN run_already_finalised` |
| Disposition live candidates / clear registries | YES (`active_propagation_set`, `acceptance_batch_registry`) | NO (done earlier; run is quiescent) |
| Close open assignments | YES — `CloseRoundAssignments(ROUND_ABORTED)` | ONLY IF final round is NONTERMINAL at `T` — `CloseRoundAssignments(ROUND_ABORTED)` as the declared horizon-end disposition |
| Record `round_terminal_time` | YES — at the abort `event_time` (via `CloseRoundAssignments`) | YES — at `T` (via the horizon-end `CloseRoundAssignments`), for a nonterminal final round only |
| Drain events to horizon `T` | NO | YES — every `event_time <= T` to quiescence (I-02) |
| `FINAL_RUN_END` residency settle | NO (REMOVED) | YES — the ONE `SettleResidencyBoundary(FINAL_RUN_END, (RunID, RUN_END))` |
| I5/I6/I7 horizon reconciliation | NO (REMOVED) | YES — AFTER the final settle |
| Terminal transition | `TRANSITION round_state -> ROUND_ABORTED` | horizon-close transition only for a nonterminal final round; ACCEPTED/ABORTED skip it |
| Followed by | `RoundInitialise` (R21) if simulated time remains | nothing — the run is over (`run_finalised <- true`) |
| Runs how many times per run | once per aborted round (0..N) | EXACTLY ONCE, at `T` |

## 7. Reconciliation with I19 / the energy model §3 / the round state machine (A1 unchanged)

- **I19 (single-owner residency, N1 clause).** The catalogue entry states *"the `FINAL_RUN_END` settle is
  owned SOLELY by `FinalizeSimulationRun` (the run-level finaliser that runs EXACTLY ONCE at the horizon
  `T`); `RoundAbort` performs NO run-end settle — it terminates ONE round, and an early abort at `t < T` is
  followed by a `RoundInitialise` `REBASE_TO_NEXT_ROUND` boundary."* Its enforcement-point list names
  `FinalizeSimulationRun` as *"the run-level finaliser that owns the single `FINAL_RUN_END` settle at the
  horizon `T` and the subsequent I5/I6/I7 reconciliation; `RoundAbort` does NOT"* and records
  `FINAL_RUN_END` as *"from `FinalizeSimulationRun` ONLY, N1."*
- **Energy model §3 (boundary residency settle).** The paragraph now states that *"the `FINAL_RUN_END`
  settle is owned SOLELY by `FinalizeSimulationRun` (Stage-1N, §20a) — the run-level finaliser that runs
  EXACTLY ONCE at the horizon `T` for a run whose last round is ACCEPTED, ABORTED, or nonterminal alike, and
  runs the I5/I6/I7 reconciliation ONLY AFTER that final settle,"* and that *"`RoundAbort` no longer
  performs any run-end settle or horizon reconciliation — it terminates ONE round, and an early abort at
  `t < T` is followed by `RoundInitialise` (a `REBASE_TO_NEXT_ROUND` boundary), never a horizon close."* The
  per-miner durations still partition `[0, T]` (I5).
- **Round state machine §2.10 / §3.10 / §3.14.** §2.10 (`ROUND_ABORTED`) records the *"Round-scope only
  (N1)"* rule: `RoundAbort` *"terminates exactly ONE round … performs no run-end residency settle and no
  reconciliation to the fixed horizon `T`; an early abort at `t < T` is followed by `RoundInitialise`
  (R21),"* while *"the single run-level finaliser `FinalizeSimulationRun` (pseudocode §20a) — NOT
  `RoundAbort` — owns the one `FINAL_RUN_END` residency settle and the I5/I6/I7 horizon reconciliation."*
  §3.10 records that the floor-unrecoverable branch calls `RoundAbort(reason = floor_unrecoverable)`, *"which
  closes ONLY this round (N1)."* §3.14 (*"What happens at the end of the simulation run (N1)"*) states *"Round
  abort and simulation end are DISTINCT,"* that the run *"ends exactly once, at the fixed horizon `T` … through
  the single run-level finaliser `FinalizeSimulationRun`,"* and that *"An early `RoundAbort` at `t < T`
  therefore NEVER closes residency at the horizon."*
- **A1 discipline.** N1 only relocates WHO performs the run-end close and reconciliation (from the round
  procedure to the run procedure); it changes no power level, no duration, and no total. The A1 baseline —
  continuous full-participation energy over `T = 10,000 s` — remains **8.420833333 kWh**, UNCHANGED. Any
  modeled energy difference remains attributable ONLY to reduced active power-time, never to how or where the
  run-end boundary is closed. N1 is a structural control-flow correction and introduces **no new consensus
  feature**.

## 8. Acceptance-style PASS checklist

| # | Check | Result | Ground |
|---|---|---|---|
| C1 | `RoundAbort` (§20) performs NO `FINAL_RUN_END` settlement — body is candidate disposition + `CloseRoundAssignments` + `ROUND_ABORTED` transition | PASS | §20 body; §20 comment (REMOVED lines); §2 |
| C2 | An early aborted round (`t < T`) can be followed by `RoundInitialise` (R21) | PASS | §20 step (5) + NOTE; round SM R21; §2.10 / §3.14 |
| C3 | ONE generic `FinalizeSimulationRun` (§20a) owns final horizon reconciliation | PASS | §20a steps (3)-(4) + NOTE; I19 (N1); energy model §3 |
| C4 | Accepted AND aborted final rounds use the SAME run-level finaliser | PASS | §20a step (2) guard + intro; §3.14 |
| C5 | An early `RoundAbort` at `t < T` NEVER closes residency at `T` | PASS | §20 comment; §3.14; §1a `FINAL_RUN_END` precondition |
| C6 | `SettleResidencyBoundary` (§1a) `FINAL_RUN_END` is INVOKED ONLY by `FinalizeSimulationRun`, never by `RoundAbort` | PASS | §1a `FINAL_RUN_END` precondition; §20a step (3); ownership table §5 |
| C7 | `run_finalised` (§0.8) guards the single run-end finalisation; init false at run start, preserved across rounds (I-04) | PASS | §0.8 `run_finalised`; §1 RoundInitialise (`INITIALISE`/`PRESERVE run_finalised`); §20a guard |
| C8 | Run-end `boundary_id` is `(RunID, RUN_END)` (run-keyed), idempotent via `rebased_boundaries` | PASS | §0.8 `rebased_boundaries` (N1); §20a step (3); §1a step (0)/(3) |
| C9 | `CloseRoundAssignments` (§17a) still records `round_terminal_time` ONLY and performs no residency finalisation (M4) | PASS | §17a M4 comment; `RECORD round_terminal_time(RoundID)` |
| C10 | A1 baseline unchanged; any energy change attributable only to reduced active power-time; no new consensus feature | PASS | §7; I19 scope note; energy model §3; A1 = 8.420833333 kWh |

---

## Result

**Result: RUN FINALISATION AUDIT (Stage 1N): PASS** — Stage-1N correction N1 separates round abort from
simulation end. `RoundAbort` (§20) now terminates exactly ONE round — it dispositions live candidates and
clears `active_propagation_set`/`acceptance_batch_registry`, calls `CloseRoundAssignments` (§17a) which
records `round_terminal_time` at the abort `event_time` and performs NO residency/energy finalisation (M4),
retains the zero-block outcome, and transitions `round_state -> ROUND_ABORTED`, then returns control — and
performs NO run-end residency settle and NO horizon reconciliation, its former in-line
`SettleResidencyBoundary(FINAL_RUN_END)` and `ASSERT durations reconcile to horizon T` lines REMOVED, so an
early abort at `t < T` is followed by `RoundInitialise` (R21) and NEVER closes residency at the horizon `T`;
the NEW run-level finaliser `FinalizeSimulationRun` (§20a), guarded by the per-run `run_finalised` (§0.8) and
seated at `(T, RUN_FINALISE)` (§0.7g/N3), is the SINGLE owner of run-end accounting — running EXACTLY ONCE
at the horizon `T` for an ACCEPTED, ABORTED, or nonterminal final round alike, draining events to `T`,
horizon-closing a nonterminal final round through the declared horizon-end disposition, performing the ONE
`SettleResidencyBoundary(mode = FINAL_RUN_END, boundary_id = (RunID, RUN_END))` (§1a, now INVOKED ONLY by
`FinalizeSimulationRun`, never by `RoundAbort`), and only THEN running the I5/I6/I7 reconciliation with no
reopen; the residency single-owner discipline (I19), the energy-model §3 boundary-settle paragraph, and the
round state machine §2.10/§3.10/§3.14 all match this control flow, and the A1 baseline (`8.420833333 kWh`)
is unchanged — N1 relocates only WHO performs the run-end close and reconciliation, never a total, adding no
new consensus feature.
