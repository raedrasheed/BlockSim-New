# Stage 1Q — Semantic Test Vectors (TV127–TV134)

Paper test vectors for the recovery-freshness & runtime-context lock (Q1–Q7). Each vector names the EXACT
procedures, preconditions, and transitions in `STAGE_01_PROTOCOL_PSEUDOCODE.md`; no guard, transition,
seating, or cancellation is assumed that is not in the pseudocode. Name remains **PoCol**; the mechanism is
**the idle policy within PoCol**; the A1 baseline (`8.420833333 kWh`) is preserved by every vector (each is a
freshness / ordering / ownership / identity check, never a change to how time or energy is counted).

---

## TV127 — A newer pre-deadline breach supersedes a pending RESTORED (Q1)

**Setup.** The round is in `SECURITY_RECOVERY` (episode `E`). At `t1` the final census shows NO breach → the
epilogue seats a `RESTORED` decision `D1` (bound `RecoveryCensusVersion = V1`, `SCHEDULED`, in
`pending_recovery_decisions[E]`).
**Steps.**
1. At `t2` (t1 < t2, before `D1` applies) a census boundary makes the FINAL census a BREACH, but the recovery
   deadline has NOT elapsed (`deadline_reached = false`).
2. The epilogue at `t2` calls `CommitRecoveryCensus` → `V2`; `ReconcilePendingRecoveryDecisions` finds `D1`
   (RESTORED) contradicted by the breach census (`outcome_consistent_with_census(RESTORED, census)` is false
   since `breach = true`) → `D1.status <- SUPERSEDED`, cancels `D1`'s due event, removes `D1` from
   `pending_recovery_decisions[E]`.
3. The warranted outcome from `V2` is `NONE` (breach BEFORE deadline → keep waiting).
**Expected.** `D1` is SUPERSEDED immediately and can never leave recovery; NO replacement completion is
required yet; the round STAYS `SECURITY_RECOVERY`. A1 preserved.

## TV128 — A due RESTORED is rejected post-quiescence after a same-time breach (Q2)

**Setup.** A `RESTORED` decision `D` (bound `V`) becomes due at `event_time = t` (its `RecoveryCompletionDueEvent`
is scheduled at `t`).
**Steps.**
1. During the drain of `t`: `RecoveryCompletionDueEvent(D)` records `D.due_at_event_time <- t`, stashes its
   dispatch_envelope, and refreshes the census (`CaptureSecurityCensusOnRecoveryDeadline` → `CommitSecurityCensus`);
   it performs NO transition. A miner DEPARTURE at the same `t` (via `ApplyMinerStateTransition`) drives the
   FINAL census to a BREACH (overwriting `latest_security_census[t]`).
2. Epilogue at `t`: `CommitRecoveryCensus` → `V'`; `Reconcile` finds `D` (RESTORED) contradicted → `D.status <-
   SUPERSEDED`, removed from pending.
3. `ApplyRecoveryCompletionAfterEpilogue(t)`: `D` is due at `t` but `D.status != SCHEDULED` (it is SUPERSEDED)
   → `recovery_apply_stale_noop(D)`.
**Expected.** The due event records only `completion_due`; the post-quiescence application REJECTS the RESTORED
decision as stale — it does not leave recovery under the breach census. A1 preserved.

## TV129 — A failed superseding schedule leaves the old decision SUPERSEDED (Q3)

**Setup.** `D1` (`RESTORED`) is pending (`SCHEDULED`, bound `V1`).
**Steps.**
1. At `t2` the FINAL census selects `UNRECOVERABLE` (breach + deadline reached, `V2`). `Reconcile` finds `D1`
   contradicted → `D1.status <- SUPERSEDED`, cancels its due event, removes from pending.
2. `SeatRecoveryCompletion(E, UNRECOVERABLE, t2, V2)` mints `D2`; `ScheduleEvent` for `D2`'s
   `RecoveryCompletionDueEvent` is REJECTED → `D2.status <- SCHEDULE_FAILED`, `D2` NOT added to
   `pending_recovery_decisions[E]`; `recovery_completion_schedule_rejected` recorded.
**Expected.** `D1` remains `SUPERSEDED` (never revived), `D2` is `SCHEDULE_FAILED`, and the round remains
`SECURITY_RECOVERY` (no completion applied). A failed superseding schedule can never revive `D1`. A1
preserved.

## TV130 — All three census sources use the one canonical writer (Q4)

**Setup.** Over a run, an `ACTIVE_HASHING` boundary, an applicability entry, and a recovery-deadline
checkpoint each produce a census.
**Steps.**
1. `ApplyMinerStateTransition` (§0.9) → `CommitSecurityCensus(..., census_source = MINER_STATE_TRANSITION)`.
2. `CaptureSecurityCensusOnApplicabilityEntry` (§9) → `CommitSecurityCensus(..., APPLICABILITY_ENTRY)`.
3. `CaptureSecurityCensusOnRecoveryDeadline` (§9a) → `CommitSecurityCensus(..., RECOVERY_DEADLINE)`.
**Expected.** No source writes `latest_security_census`/`security_census_dirty` directly (a grep finds those
`SET`s ONLY inside `CommitSecurityCensus`, §0.8a); after every write, `security_census_dirty[t] = true` implies
`latest_security_census[t]` EXISTS (structural J1). A1 preserved.

## TV131 — Run/round ownership is explicit and complete (Q5)

**Setup.** A run starts.
**Steps.**
1. `RunInitialise` (§1.0) is called ONCE and creates `RunContext` with `EventQueueContext`, `RunHookContext`,
   `rebased_boundaries`, `run_finalised`, `run_horizon_T`, and the per-run census maps.
2. `RoundInitialise(config, RunContext, prior_state)` (§1.1) initialises ONLY per-round registries, binds
   `RunContext`, and RETURNS every per-round recovery registry: `recovery_episode_seq`,
   `current_recovery_episode`, `recovery_deadline_reached`, `recovery_census_seq`, `latest_recovery_census`,
   `recovery_decision_seq`, `recovery_decisions`, `pending_recovery_decisions`, `latest_recovery_decision`,
   `recovery_outcome_finalised`.
**Expected.** `RunInitialise` owns the one-time per-run creation; `RoundInitialise` returns every declared
per-round recovery registry explicitly; `RunEventLoopToHorizon` obtains `RunHookContext` via
`RunContext.RunHookContext` (not an implicit local). A1 preserved.

## TV132 — Same numeric event_seq, distinct tagged identities (Q6)

**Setup.** An ordinary event carries `event_seq = k` (`envelope_namespace = ORDINARY_EVENT`). The horizon
close mints a run-hook envelope whose `run_hook_seq` also numerically equals `k`
(`envelope_namespace = RUN_HOOK`, `hook_id = (RunID, T, HORIZON_CLOSE)`).
**Steps.**
1. Each envelope's `TransitionEventID` (J3) includes `envelope_namespace` (and `hook_id` when `RUN_HOOK`).
**Expected.** The two `TransitionEventID`s are DISTINCT because their `envelope_namespace`/`hook_id` differ —
collision freedom comes from the TAG, not the numeric `event_seq`/`delta_cycle`. A1 preserved.

## TV133 — Horizon close before the epilogue; terminal-stale-noop; no seat at T (Q2/O1)

**Setup.** The run reaches the horizon `T` with the round nonterminal (in `SECURITY_RECOVERY`).
**Steps.**
1. `ProcessEventTime(T)` drains `T`, then interposes `CloseRoundAtHorizon` (§20b) → `ROUND_ABORTED` (BEFORE the
   epilogue).
2. The `T` epilogue `FinalizeEventTimeSecurityCensus(T)` sees the terminal round → `terminal_stale_noop`;
   because the round is terminal, `SecurityFloorEvaluate` never runs its `SECURITY_RECOVERY` branch, so
   `SeatRecoveryCompletion` does NOT execute at `T`.
**Expected.** `CloseRoundAtHorizon` runs before the security epilogue; the terminal epilogue returns
`terminal_stale_noop`; no recovery completion is seated at `T`. A1 preserved.

## TV134 — Deterministic completion delay; a target beyond T is not enqueued (Q7)

**Setup.** The epilogue at `t` warrants a recovery outcome for episode `E`.
**Steps.**
1. `SeatRecoveryCompletion` computes `target_time = t + configured_recovery_completion_delay`
   (`configured_recovery_completion_delay > 0`, declared config).
2. Case (a) `target_time <= T`: the `RecoveryCompletionDueEvent` is seated at `target_time`; `D.status <-
   SCHEDULED`. Case (b) `target_time > T`: `D.status <- CANCELLED`; `horizon_deferred(D, target_time)` recorded;
   NOTHING is enqueued.
**Expected.** The completion time is deterministic; a target beyond `T` is not enqueued, and no older
SUPERSEDED decision is revived; `CloseRoundAtHorizon` governs run end. A1 preserved.

---

## Coverage summary

| Vector | Correction | Exercises |
|--------|-----------|-----------|
| TV127 | Q1 | newer pre-deadline breach supersedes a pending RESTORED; round stays in recovery |
| TV128 | Q2 | due RESTORED rejected post-quiescence after a same-time breach |
| TV129 | Q3 | failed superseding schedule → D1 SUPERSEDED, D2 SCHEDULE_FAILED, round stays |
| TV130 | Q4 | three census sources → one `CommitSecurityCensus`; dirty ⇒ latest |
| TV131 | Q5 | `RunInitialise` creates RunContext; `RoundInitialise` returns every recovery registry |
| TV132 | Q6 | same numeric event_seq; distinct tagged `TransitionEventID`s |
| TV133 | Q2/O1 | horizon close before epilogue; terminal-stale-noop; no seat at T |
| TV134 | Q7 | deterministic completion delay; target beyond T not enqueued; no revival |

All eight vectors pass on paper against the exact named procedures. No new consensus feature; documentation
only; name remains PoCol; the A1 baseline `8.420833333 kWh` is unchanged. The prohibited
rebranded-algorithm-name variants are not used anywhere in this document.
