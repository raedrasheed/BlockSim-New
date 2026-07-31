# Stage 1S — Semantic Test Vectors (TV143–TV152)

Paper test vectors for the full-envelope & deferred-recovery-atomicity lock (S1–S7). Each vector names the EXACT
procedures, preconditions, and transitions in `STAGE_01_PROTOCOL_PSEUDOCODE.md`; no guard, transition, seating, or
cancellation is assumed that is not in the pseudocode. Name remains **PoCol**; the mechanism is **the idle policy
within PoCol**; the A1 baseline (`8.420833333 kWh`) is preserved by every vector (each is a signature / atomicity /
lifecycle / provenance check, never a change to how time or energy is counted).

---

## TV143 — Every ApplyMinerStateTransition call passes one complete envelope (S1)

**Setup.** Enumerate every direct `CALL ApplyMinerStateTransition(...)` in the pseudocode (14 sites: `StartWake`,
`WakeCompleteEvent` ×2, `MinerRegister` ×2, `ExhaustionAdjudicate`, `EnterLowPowerListen`,
`AdversarialParticipationChangeEvent` ×2, `LeaseExpiry`, `CloseRoundAssignments` ×2, `CloseTemplateAssignments`
×2).
**Steps.**
1. Each call passes `transition_envelope = dispatch_envelope` — the single object holding
   `{envelope_namespace, event_time, delta_cycle, event_seq, hook_id}`.
2. `ApplyMinerStateTransition` destructures that object (step (0)) and builds `TransitionEventID` from it plus the
   transition-specific fields.
**Expected.** ZERO call sites omit the namespace or hook identity, and none passes decomposed identity args; the
R3 "namespace fields travel implicitly" clause is withdrawn. A1 preserved.

## TV144 — Same numeric fields, distinct complete envelopes → distinct ids (S1)

**Setup.** An ORDINARY_EVENT transition and a RUN_HOOK (horizon-close) transition have identical numeric
`(event_time, delta_cycle, event_seq)`.
**Steps.**
1. The ordinary call passes `transition_envelope = dispatch_envelope` with `envelope_namespace = ORDINARY_EVENT`,
   `hook_id = null` (materialised by `ProcessEventTime`).
2. The horizon call passes `transition_envelope = horizon_envelope` with `envelope_namespace = RUN_HOOK`,
   `hook_id = HorizonHookID` (threaded through `CloseRoundAssignments` → `EnterLowPowerListen`).
**Expected.** The two `TransitionEventID`s DIFFER because their complete envelopes' `envelope_namespace`/`hook_id`
differ — the actual call-site construction carries them (not a numeric-only subset). A1 preserved.

## TV145 — Branch C with t_cont > T is rejected while the round stays SECURITY_RECOVERY (S2)

**Setup.** A due RESTORED decision `D` warrants branch C (redistribution) at `t`, and
`next_representable_simulation_time(t) > T`.
**Steps.**
1. `CompleteSecurityRecovery` branch C computes `t_cont = next_representable_simulation_time(t)`, finds
   `t_cont > run_horizon_T`, records `recovery_continuation_horizon_deferred`, and returns
   `recovery_branch_result(kind = FAILED, reason = horizon_deferred)` — WITHOUT mutating `round_state`.
2. `ApplyRecoveryCompletionAfterEpilogue` maps `reason = horizon_deferred` to `HORIZON_DEFERRED`, marks `D`
   `HORIZON_DEFERRED`, removes it from pending, and PRESERVES the episode.
**Expected.** `round_state` stays `SECURITY_RECOVERY`, `current_recovery_episode` stays set, `D` is
`HORIZON_DEFERRED`, and no continuation is pending. A1 preserved.

## TV146 — A seated branch-C continuation keeps the decision APPLYING until HASHING (S3)

**Setup.** A due RESTORED decision `D` warrants branch C at `t`; `t_cont = next_representable_simulation_time(t) <=
T`.
**Steps.**
1. `CompleteSecurityRecovery` branch C seats ONE `RecoveryAssignmentContinuationEvent` at `t_cont` (through the S7
   `PostEpilogueSchedulingContext`), stores `D.continuation_event_ref`, and returns
   `recovery_branch_result(kind = DEFERRED, ...)`.
2. `ApplyRecoveryCompletionAfterEpilogue` on DEFERRED leaves `D` `APPLYING`, does NOT set
   `recovery_outcome_finalised`, does NOT clear `current_recovery_episode`, keeps `D` in pending, and returns
   `recovery_deferred`.
**Expected.** Between `t` and `t_cont` the decision is `APPLYING`, the episode is ACTIVE, and the round is still
`SECURITY_RECOVERY` — RESTORED is NOT yet applied. A1 preserved.

## TV147 — The continuation reaches HASHING; only then is the decision APPLIED (S3)

**Setup.** The `RecoveryAssignmentContinuationEvent` for `D` fires at `t_cont`; the episode + `APPLYING` decision
are still current and the round is still `SECURITY_RECOVERY`.
**Steps.**
1. It verifies (step 1/2), PREPAREs + validates the disjoint plan (step 3), transitions `SECURITY_RECOVERY →
   ASSIGNMENT` (step 4), INSTALLs the valid disjoint set (step 5), runs `CompleteAssignmentPhase → HASHING` (step
   6), asserts `round_state = HASHING`.
2. Step 7: marks `D` `APPLIED`, sets `recovery_outcome_finalised[episode] = RESTORED`, removes `D` from pending,
   clears `current_recovery_episode`.
**Expected.** RESTORED is APPLIED ONLY after HASHING is reached; the episode is finalised and cleared exactly
then. A1 preserved.

## TV148 — A continuation failing before mutation stays SECURITY_RECOVERY, episode preserved (S3)

**Setup.** The `RecoveryAssignmentContinuationEvent` for `D` fires; the disjoint plan CANNOT be prepared
(step 3 fails) BEFORE any state mutation.
**Steps.**
1. It marks `D` `APPLY_FAILED`, removes `D` from pending, records `recovery_continuation_plan_invalid`, and
   returns `recovery_continuation_failed` — `round_state` is UNCHANGED (`SECURITY_RECOVERY`).
**Expected.** The round stays `SECURITY_RECOVERY`, the episode is PRESERVED (a later epilogue may re-seat), and no
partial ASSIGNMENT mutation occurred. (A failure AFTER the transition instead takes the declared recovery-finalising
`RoundAbort`, never leaving `ASSIGNMENT` with an active episode and no live continuation.) A1 preserved.

## TV149 — A terminal round cancels a pending/APPLYING decision (S4)

**Setup.** A round is closed (`ROUND_ACCEPTED` via `ValidBlockAccept`, or `ROUND_ABORTED` via
`CloseRoundAtHorizon`) while `current_recovery_episode != null` and a decision is `SCHEDULED`/`APPLYING`; the
closure is NOT the recovery-finalising abort (`recovery_finalising = false`).
**Steps.**
1. `CloseRoundAssignments` cancels the queued recovery-timeline events and calls
   `CancelActiveRecoveryEpisode`.
2. `CancelActiveRecoveryEpisode` cancels every pending/applying decision (and its `due_event_ref` /
   `continuation_event_ref` on `EQ`), records `recovery_episode_disposition[episode] = TERMINAL_CANCELLED`, and
   clears `current_recovery_episode` — WITHOUT setting `recovery_outcome_finalised`.
**Expected.** The episode is `TERMINAL_CANCELLED`, `current_recovery_episode` is null, and the invariant
`current_recovery_episode != null IFF round_state = SECURITY_RECOVERY` holds. A1 preserved.

## TV150 — ProcessEventTime invokes the epilogue exactly once even when dirty[t] is false (S6)

**Setup.** `ProcessEventTime(t)` has drained `t` to quiescence and `security_census_dirty[t] = false` (no
ACTIVE_HASHING boundary occurred at `t`).
**Steps.**
1. `ProcessEventTime` calls `FinalizeEventTimeSecurityCensus(RoundContext, t)` UNCONDITIONALLY (no
   `IF security_census_dirty[t]` guard).
2. The procedure's own `IF NOT security_census_dirty[t]: RETURN no_census_change` fires.
**Expected.** The epilogue is invoked EXACTLY ONCE and returns `no_census_change`; the call is not skipped and not
doubled. A1 preserved.

## TV151 — Both settlements clear dirty[t] only through SettleSecurityCensusDirty (S5)

**Setup.** At some `event_time` the primary epilogue clears the flag; at another, a post-recovery settlement does.
**Steps.**
1. `FinalizeEventTimeSecurityCensus` calls `SettleSecurityCensusDirty(t, PRIMARY_EPILOGUE)`.
2. `FinalizePostRecoveryApplicationState` calls `SettleSecurityCensusDirty(t, POST_RECOVERY_APPLICATION)`.
**Expected.** `security_census_dirty[t]` is cleared ONLY inside `SettleSecurityCensusDirty` (no direct `CLEAR`
exists elsewhere); `CommitSecurityCensus` remains the sole setter of `dirty = true`. A1 preserved.

## TV152 — A post-epilogue continuation is scheduled strictly-later with delta_cycle 0 (S7)

**Setup.** `CompleteSecurityRecovery` branch C seats its `RecoveryAssignmentContinuationEvent` via `ScheduleEvent`
with a `PostEpilogueSchedulingContext` whose `source_event_time = t`.
**Steps.**
1. `ScheduleEvent`'s S7 branch requires `target_event_time (= t_cont) > source_event_time (= t)`; otherwise it
   returns `rejected_post_epilogue_not_strictly_later`.
2. On success it derives `delta_cycle = 0` and mints `event_creation_seq` itself.
**Expected.** The continuation is enqueued at a STRICTLY LATER `event_time` with `delta_cycle = 0`; a post-epilogue
caller can never enqueue at `source_event_time` (R1 structural), and the seq is minted solely by `ScheduleEvent`.
A1 preserved.

---

## Coverage summary

| Vector | Correction | Exercises |
|--------|-----------|-----------|
| TV143 | S1 | every ApplyMinerStateTransition call passes one complete `transition_envelope` |
| TV144 | S1 | identical numeric fields, distinct complete envelopes → distinct `TransitionEventID`s |
| TV145 | S2 | branch C `t_cont > T` rejected; round stays SECURITY_RECOVERY; `HORIZON_DEFERRED` |
| TV146 | S3 | seated continuation keeps the decision APPLYING + episode active until HASHING |
| TV147 | S3 | continuation reaches HASHING → only then APPLIED + episode cleared |
| TV148 | S3 | continuation fails before mutation → stays SECURITY_RECOVERY, episode preserved |
| TV149 | S4 | terminal round → `TERMINAL_CANCELLED`, events cancelled, episode cleared |
| TV150 | S6 | epilogue invoked exactly once even when dirty[t] false → `no_census_change` |
| TV151 | S5 | dirty[t] cleared only through `SettleSecurityCensusDirty` |
| TV152 | S7 | post-epilogue seat strictly-later, `delta_cycle = 0`, via `PostEpilogueSchedulingContext` |

All ten vectors pass on paper against the exact named procedures. No new consensus feature; documentation only;
name remains PoCol; the A1 baseline `8.420833333 kWh` is unchanged. The prohibited rebranded-algorithm-name
variants are not used anywhere in this document.
