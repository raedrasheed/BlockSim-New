# Stage 1N — Semantic Test Vectors (TV104–TV110)

Seven blocking test vectors for the Stage-1N run-lifecycle and recovery closure. Each names the exact
procedure(s) in `STAGE_01_PROTOCOL_PSEUDOCODE.md` and its exact preconditions; none assumes a guard,
transition, or cancellation not present in the pseudocode, and none assumes an unmodeled external action.
These extend TV1–TV103 (historical, in `STAGE_01C..M_*`, which are NOT modified in Stage 1N). No property
(energy, security, fairness, incentive) is claimed. The A1 baseline (`8.420833333 kWh`) is unchanged. Name
remains **PoCol**; mechanism is **the idle policy within PoCol**.

---

## TV104 — an early round abort closes only that round; a new round starts afterward (N1)

**Preconditions.** At `event_time t < T` (the fixed horizon), round `r` hits an unrecoverable condition and
`RoundAbort(RoundContext, reason, dispatch_envelope)` is dispatched. Simulated time remains (`t < T`). A
miner `m` continues in `LOW_POWER_LISTEN` with an OPEN residency interval.

**Trace.** `RoundAbort` dispositions the live candidate contexts, calls `CloseRoundAssignments(…,
ROUND_ABORTED, dispatch_envelope)` (which records `round_terminal_time(r) <- t` and moves miners off
`ACTIVE_HASHING`), and `TRANSITION round_state -> ROUND_ABORTED`. Its executable body contains NO
`SettleResidencyBoundary` and NO horizon-`T` reconciliation. Control returns; the sim driver dispatches
`RoundInitialise` for round `r+1` (round SM R21), which calls `SettleResidencyBoundary(mode =
REBASE_TO_NEXT_ROUND, boundary_id = (r, r+1), prior_state = r)` — closing `m`'s interval at `t` and
reopening the same state at `t` for `r+1`.

**Expected.** The abort closes only round `r`; NO residency interval is settled at `RUN_END` during the
early abort (the `(RunID, RUN_END)` boundary is never touched at `t`); round `r+1` starts via
`RoundInitialise`. Reqs: **N1**, §20/§17a/§1/§1a; round SM R21.

## TV105 — the final round is ROUND_ACCEPTED before T; FinalizeSimulationRun reconciles once (N1)

**Preconditions.** Round `r` reaches `ROUND_ACCEPTED` at `t_acc < T` (via `ValidBlockAccept →
CloseRoundAssignments`, recording `round_terminal_time(r) <- t_acc`); no later round starts. The run driver
seats `FinalizeSimulationRun` at `(T, RUN_FINALISE)`.

**Trace.** `FinalizeSimulationRun` finds `run_finalised = false`; drains all events with `event_time <= T`
to quiescence; `round_state = ROUND_ACCEPTED` is already terminal, so the horizon-close step is skipped;
it performs the ONE `SettleResidencyBoundary(mode = FINAL_RUN_END, boundary_id = (RunID, RUN_END))`,
closing every open residency interval at `T` with NO reopen; and only THEN asserts I6 (per-miner sums), I7
(network sum), and I5 (durations reconcile to `T`). Sets `run_finalised <- true`.

**Expected.** `FinalizeSimulationRun` at `T` closes all remaining open residency intervals exactly once and
reconciles I5/I6/I7; the A1 baseline (`8.420833333 kWh`) is unchanged. Reqs: **N1**, §20a/§1a; I5/I6/I7/I19.

## TV106 — the final round is ROUND_ABORTED before T; FinalizeSimulationRun does the single FINAL_RUN_END settle (N1)

**Preconditions.** Round `r` ends `ROUND_ABORTED` at `t_ab < T` (via `RoundAbort`, which recorded
`round_terminal_time(r) <- t_ab` and did NO horizon settle); no later round starts. `FinalizeSimulationRun`
is seated at `(T, RUN_FINALISE)`.

**Trace.** `RoundAbort` performed no `FINAL_RUN_END` settle. `FinalizeSimulationRun` runs once: drains to
`T`; `round_state = ROUND_ABORTED` is terminal (skip horizon-close); performs the ONE
`SettleResidencyBoundary(FINAL_RUN_END, (RunID, RUN_END))`; then reconciles I5/I6/I7.

**Expected.** `FinalizeSimulationRun`, NOT `RoundAbort`, performs the single `FINAL_RUN_END` settle at `T`
(the same run-level finaliser as the ACCEPTED case, TV105); the interval is settled exactly once
(idempotent via `boundary_id`). Reqs: **N1**, §20/§20a/§1a; I5/I6/I7/I19.

## TV107 — recovery succeeds with no live candidate and no redistribution; enter HASHING with a census (N2)

**Preconditions.** Round `r` is in `SECURITY_RECOVERY`; reserves have restored `H_honest(t)` to/above the
floor; `active_propagation_set` is empty; the recovered coverage needs NO range redistribution. The
epilogue's floor-restored decision (§9) seated `CompleteSecurityRecovery` at `(t_next, RECOVERY_COMPLETE)`
carrying `floor_result = restored` and the epoch.

**Trace.** `CompleteSecurityRecovery` passes its stale-decision guard (epoch current), `floor_result =
restored`, `active_propagation_set` empty, no redistribution → branch B: `CALL TransitionRoundState(HASHING,
dispatch_envelope)`, which transitions `SECURITY_RECOVERY -> HASHING` and captures the applicability-entry
census at `dispatch_envelope.event_time`.

**Expected.** `CompleteSecurityRecovery` enters `HASHING` through `TransitionRoundState` and captures a
coherent applicability census, so the epilogue evaluates the floor on the HASHING entry. Reqs: **N2/R13**,
§10a/§2a-bis; K7/M2.

## TV108 — recovery succeeds while a candidate remains live; enter SOLUTION_PROPAGATION preserving events (N2)

**Preconditions.** Round `r` is in `SECURITY_RECOVERY` with a live candidate `C` in `active_propagation_set`
(status `PROPAGATING`/`PENDING_ACCEPTANCE`) whose certificate/block events are scheduled (G8). Reserves
restored the floor. `CompleteSecurityRecovery` was seated at `(t_next, RECOVERY_COMPLETE)`.

**Trace.** `CompleteSecurityRecovery` guard passes; `active_propagation_set` is non-empty → branch A:
ASSERT `C` retains its status and its scheduled events are intact (preserve contexts + events, G8); `CALL
TransitionRoundState(SOLUTION_PROPAGATION, dispatch_envelope)` (`SECURITY_RECOVERY -> SOLUTION_PROPAGATION`,
census captured). `C`'s events are not cancelled.

**Expected.** `CompleteSecurityRecovery` enters `SOLUTION_PROPAGATION` and preserves that candidate's
context and scheduled events; the applicability census is captured. Reqs: **N2/R13/G8**, §10a/§2a-bis.

## TV109 — recovery requires assignment changes; ASSIGNMENT → CompleteAssignmentPhase → HASHING (N2)

**Preconditions.** Round `r` is in `SECURITY_RECOVERY`; reserves restored the floor; `active_propagation_set`
is empty; coverage requires range redistribution / reserve assignment. `CompleteSecurityRecovery` seated at
`(t_next, RECOVERY_COMPLETE)`.

**Trace.** `CompleteSecurityRecovery` guard passes; no live context; redistribution required → branch C:
`TRANSITION round_state -> ASSIGNMENT`; BUILD the valid disjoint assignment set under `(RoundID_current,
TemplateID_committed)` (activate reserves via `ReserveActivate(…, dispatch_envelope)` and/or reassign
accepted unsearched suffixes — NO new template, I1 disjoint); then `CALL CompleteAssignmentPhase(RoundContext,
dispatch_envelope)`, which performs `ASSIGNMENT -> HASHING` (R4) and captures the HASHING census (L2/M2).

**Expected.** The path is `SECURITY_RECOVERY -> ASSIGNMENT -> CompleteAssignmentPhase -> HASHING`; no new
template is fabricated; the HASHING-entry census is captured. Reqs: **N2/R13**, §10a/§2b; L2/M2/I1.

## TV110 — every listed driver entry point has a declared microphase and a deterministic envelope (N3)

**Preconditions.** The nine sim-driver entry points of §0.7g-driver are seated on the queue over a run:
`RoundInitialise`, `TemplateCommit`, `PrepareParticipantsForNewRound`, `MinerRegister`, `ReserveActivate`,
`FullRangeExhaustNoSolution`, `CompleteSecurityRecovery`, `RoundAbort`, `FinalizeSimulationRun`.

**Trace.** For each, the §0.7g-driver table declares its event type, `target_microphase` (`ROUND_SETUP`,
`TEMPLATE_COMMIT`, `ASSIGNMENT_SETUP`, `REGISTRATION`, `RECOVERY_ACTIVATE`, `RANGE_EXHAUST_ADJUDICATE`,
`RECOVERY_COMPLETE`, `TERMINAL_ABORT`, `RUN_FINALISE`), stable tie key, required envelope fields
`(event_time, delta_cycle, event_seq)`, and its same-time delta-cycle right. Each is dispatched by
`ProcessEventTime`, which materialises the ONE `dispatch_envelope` from the event's own enqueued envelope
(§0.7f) and threads it into the procedure. `RoundAbort` keeps `TERMINAL_ABORT` (§21 item 1);
`FinalizeSimulationRun` is `RUN_FINALISE`, processed after every ordinary round event.

**Expected.** Every listed driver entry point is scheduled with a declared `target_microphase` and receives
a deterministic `dispatch_envelope` under a normative `ScheduleEvent` seating rule; no entry point receives
an envelope without such a rule. Reqs: **N3**, §0.7g-driver/§0.7f/§21.

---

**Coverage.** TV104 (N1 early abort → RoundInitialise, no RUN_END settle), TV105 (N1 accepted final →
FinalizeSimulationRun once), TV106 (N1 aborted final → FinalizeSimulationRun, not RoundAbort, does the
FINAL_RUN_END settle), TV107 (N2 recovery → HASHING with census), TV108 (N2 recovery → SOLUTION_PROPAGATION
preserving events), TV109 (N2 recovery redistribution → ASSIGNMENT → CompleteAssignmentPhase → HASHING),
TV110 (N3 driver microphase + envelope seating). Every vector names exact procedures and preconditions,
assumes no guard/transition/cancellation absent from the pseudocode, preserves the A1 baseline
(`8.420833333 kWh`), and claims no property. Name remains PoCol; mechanism is the idle policy within PoCol.
