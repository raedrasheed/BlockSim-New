# Stage 1R — Semantic Test Vectors (TV135–TV142)

Paper test vectors for the post-epilogue & transition-identity lock (R1–R6). Each vector names the EXACT
procedures, preconditions, and transitions in `STAGE_01_PROTOCOL_PSEUDOCODE.md`; no guard, transition, seating, or
cancellation is assumed that is not in the pseudocode. Name remains **PoCol**; the mechanism is **the idle policy
within PoCol**; the A1 baseline (`8.420833333 kWh`) is preserved by every vector (each is a causality / identity /
atomicity / provenance check, never a change to how time or energy is counted).

---

## TV135 — Branch-C RESTORED with zero wake latency runs at the next representable time (R1)

**Setup.** The round is in `SECURITY_RECOVERY` (episode `E`). At `t` the epilogue's final census shows NO breach
and range redistribution is required, so `ApplyRecoveryCompletionAfterEpilogue(t)` marks the due `RESTORED`
decision `APPLYING` and calls `CompleteSecurityRecovery(RESTORED)` → **branch C**.
**Steps.**
1. Branch C `TRANSITION round_state -> ASSIGNMENT` and computes `t_cont = next_representable_simulation_time(t)`
   (`t_cont > t`).
2. It `⇒ RecoveryAssignmentContinuationEvent` at `t_cont` (microphase `RECOVERY_ASSIGNMENT_CONTINUATION`) and
   returns `recovery_branch_result(success = true, target = ASSIGNMENT_CONTINUATION_SEATED)`.
3. At `t_cont` the handler does `ReserveActivate` → `StartWake`; the reserve's modeled wake latency is ZERO, so
   `ScheduleEvent` derives a `WakeCompleteEvent` at `t_cont` (same time, forward delta-cycle, H5).
**Expected.** NO `WakeCompleteEvent` (and no other ordinary event) is placed at the already-drained `t`; the
zero-latency wake executes at `t_cont = next_representable_simulation_time(t)`, strictly later than `t`. A1
preserved.

## TV136 — ProcessEventTime finalisation assertion holds (R1/R2)

**Setup.** `ProcessEventTime(t)` has drained `t` to quiescence and run the epilogue exactly once; a recovery
application at `t` re-dirtied `t` (a RESTORED exit or an UNRECOVERABLE abort).
**Steps.**
1. `FinalizeEventTimeSecurityCensus(t)` runs ONCE (R2 step 1).
2. `ApplyRecoveryCompletionAfterEpilogue(t)` applies at most one decision; any continuation is seated at
   `next_representable_simulation_time(t)` (R1), nothing at `t`.
3. `FinalizePostRecoveryApplicationState(t)` archives the post-application census (source
   `POST_RECOVERY_APPLICATION`) and CLEARS `security_census_dirty[t]` — WITHOUT invoking `SecurityFloorEvaluate`.
**Expected.** The two finalisation ASSERTIONs both hold: `no ordinary event remains with event_time = t` AND
`security_census_dirty[t] = false`; `t` is then added to `finalised_event_times`; EXACTLY ONE security epilogue
ran at `t`. A1 preserved.

## TV137 — Same numeric envelope, distinct namespace → distinct TransitionEventID (R3)

**Setup.** An ORDINARY_EVENT miner transition is dispatched at `(event_time = τ, delta_cycle = k, event_seq = s)`.
The horizon close mints a RUN_HOOK envelope whose numeric `(event_time, delta_cycle, event_seq)` also equals
`(τ, k, s)`.
**Steps.**
1. The ordinary transition builds `TransitionEventID` with `envelope_namespace = ORDINARY_EVENT`, `hook_id = null`
   (materialised by `ProcessEventTime`, §0.7d).
2. The horizon transition builds `TransitionEventID` with `envelope_namespace = RUN_HOOK`,
   `hook_id = HorizonHookID` (threaded from the `horizon_envelope`, §20b).
**Expected.** The two `TransitionEventID`s DIFFER because their leading `envelope_namespace` (and `hook_id`)
differ, even though every numeric field coincides (R3 acceptance requirement). Neither the replay guard nor the
`applied_transition_registry` conflates them. A1 preserved.

## TV138 — Nested run-hook transition replay suppressed on the full RUN_HOOK id (R3)

**Setup.** `CloseRoundAtHorizon` closes the round; a nested `ApplyMinerStateTransition` (via
`CloseRoundAssignments → EnterLowPowerListen`) applies a holder's `ACTIVE_HASHING → LOW_POWER_LISTEN` under the
RUN_HOOK envelope, entering its `TransitionEventID` (carrying `RUN_HOOK` + `HorizonHookID`) into
`applied_transition_registry`.
**Steps.**
1. A replay of the SAME nested transition is presented (same MinerID, same numeric envelope, same RUN_HOOK
   namespace + HorizonHookID).
2. `ApplyMinerStateTransition` finds the COMPLETE RUN_HOOK `TransitionEventID` already in
   `applied_transition_registry` → `duplicate_suppressed`.
**Expected.** The replay is suppressed on the FULL RUN_HOOK `TransitionEventID` (namespace + hook_id + numeric +
identity fields); no second transition energy or residency boundary is charged. A1 preserved.

## TV139 — A decision due at T is never APPLIED after horizon closure (R4)

**Setup.** A recovery decision `D` (`SCHEDULED`) becomes due at `event_time = T` (the horizon). At `T`,
`ProcessEventTime(T)` interposes `CloseRoundAtHorizon` (§20b) BEFORE the epilogue, making the round terminal
(`ROUND_ABORTED`).
**Steps.**
1. `ApplyRecoveryCompletionAfterEpilogue(T)` runs its R4 TERMINAL guard FIRST: `round_state in {ROUND_ACCEPTED,
   ROUND_ABORTED}` is true.
2. It cancels every pending decision of the episode via `SetRecoveryDecisionStatus(..., CANCELLED)` (R6 mirror
   refreshed) and empties `pending_recovery_decisions[episode]`, returning `terminal_recovery_noop`.
**Expected.** `D` is `CANCELLED`, NOT `APPLIED`; no recovery outcome is applied after horizon closure; the mirror
`latest_recovery_decision[episode]` reads `CANCELLED` (never a stale `SCHEDULED`/`CREATED`). A1 preserved.

## TV140 — A decision whose branch fails is not APPLIED and the episode is preserved (R4)

**Setup.** A fresh, matching `SCHEDULED` decision `D` is due at `t`; the round is nonterminal in
`SECURITY_RECOVERY`.
**Steps.**
1. `ApplyRecoveryCompletionAfterEpilogue(t)` VERIFIES `D`, sets `D.status <- APPLYING`
   (`SetRecoveryDecisionStatus`), and calls `CompleteSecurityRecovery`.
2. The branch does NOT reach a legal round transition — `CompleteSecurityRecovery` returns
   `recovery_branch_result(success = false, reason = ...)` (e.g. `continuation_not_seated` when `t_cont > T`).
3. The caller records `D.status <- APPLY_FAILED`, does NOT set `recovery_outcome_finalised[episode]`, does NOT
   clear `current_recovery_episode`, and returns `recovery_apply_failed`.
**Expected.** `D` is `APPLY_FAILED` (never `APPLIED`); the active episode is PRESERVED, so a later epilogue may
re-seat a warranted outcome; no half-applied outcome strands the episode. A1 preserved.

## TV141 — Census-write ordinal from the RunContext counter; completion-due provenance (R5)

**Setup.** Over one `event_time`, an `ApplyMinerStateTransition` and a `RecoveryCompletionDueEvent` each produce a
census.
**Steps.**
1. `ApplyMinerStateTransition` → `CommitSecurityCensus(..., census_source = MINER_STATE_TRANSITION)`; the writer
   increments `RunContext.security_census_write_seq_by_event_time[event_time]` and stamps it as `census_seq`.
2. `RecoveryCompletionDueEvent` → `CaptureSecurityCensusOnRecoveryDeadline(..., census_source =
   RECOVERY_COMPLETION_DUE)` → `CommitSecurityCensus(..., RECOVERY_COMPLETION_DUE)`; the writer increments the
   SAME per-event_time ordinal deterministically.
**Expected.** The census-write order is the EXPLICIT `RunContext` counter (owned solely by `CommitSecurityCensus`,
initialised in `RunInitialise`, preserved across rounds), never an implicit ordinal; the completion-due census
carries source `RECOVERY_COMPLETION_DUE` (distinct from `RECOVERY_DEADLINE`). A1 preserved.

## TV142 — Post-recovery terminal census cleared without a second floor decision (R2/R5)

**Setup.** At `t` the epilogue selected `UNRECOVERABLE`; `ApplyRecoveryCompletionAfterEpilogue(t)` applied it via
`CompleteSecurityRecovery` branch D → `RoundAbort`, moving miners off `ACTIVE_HASHING` (each transition commits a
`MINER_STATE_TRANSITION` census), re-dirtying `t`.
**Steps.**
1. `FinalizePostRecoveryApplicationState(t)` sees `security_census_dirty[t] = true` and the round terminal
   (`ROUND_ABORTED`).
2. It records a `terminal_census_observation(t, …)`, STAMPS the settlement via `CommitSecurityCensus(..., census_source =
   POST_RECOVERY_APPLICATION)`, and CLEARS `security_census_dirty[t]`.
3. It does NOT call `SecurityFloorEvaluate` and seats NO recovery decision.
**Expected.** The terminal census record is created and then cleared by the settlement WITHOUT a second
security-floor decision and WITHOUT seating another recovery decision; the epilogue for `t` still ran exactly once.
A1 preserved.

---

## Coverage summary

| Vector | Correction | Exercises |
|--------|-----------|-----------|
| TV135 | R1 | branch-C RESTORED zero-latency wake at `next_representable_simulation_time(t)`, not at `t` |
| TV136 | R1/R2 | ProcessEventTime finalisation assertion (no event at `t`; `dirty[t]=false`; one epilogue) |
| TV137 | R3 | identical numeric envelope, distinct namespace → distinct `TransitionEventID` |
| TV138 | R3 | nested horizon-hook transition replay suppressed on the full RUN_HOOK id |
| TV139 | R4 | decision due at T cancelled/terminal-noop, never APPLIED after horizon closure |
| TV140 | R4 | branch-failure → `APPLY_FAILED`, episode preserved, not APPLIED |
| TV141 | R5 | census-write ordinal from RunContext counter; `RECOVERY_COMPLETION_DUE` provenance |
| TV142 | R2/R5 | post-recovery terminal census cleared without a second floor decision |

All eight vectors pass on paper against the exact named procedures. No new consensus feature; documentation only;
name remains PoCol; the A1 baseline `8.420833333 kWh` is unchanged. The prohibited rebranded-algorithm-name
variants are not used anywhere in this document.
