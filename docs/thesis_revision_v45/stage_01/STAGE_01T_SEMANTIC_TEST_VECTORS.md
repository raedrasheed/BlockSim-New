# Stage 1T — Semantic Test Vectors (TV153–TV162)

Paper test vectors for the continuation-epilogue & outcome-integrity lock (T1–T7). Each vector names the EXACT
procedures, preconditions, and transitions in `STAGE_01_PROTOCOL_PSEUDOCODE.md`; no guard, transition, seating,
classification, or cancellation is assumed that is not in the pseudocode. Name remains **PoCol**; the mechanism is
**the idle policy within PoCol**; the A1 baseline (`8.420833333 kWh`) is preserved by every vector (each is a
control-flow / versioning / lifecycle / provenance check, never a change to how time or energy is counted).

---

## TV153 — A DEFERRED branch C seats a Due event that records due + refreshes census, with no transition (T1)

**Setup.** A due RESTORED decision `D` warrants branch C (range redistribution) at `t`; `t_cont =
next_representable_simulation_time(t) <= T`.
**Steps.**
1. `CompleteSecurityRecovery` branch C mints the continuation identity (`continuation_generation <- 1`,
   `continuation_id <- (decision_id, 1)`, `continuation_bound_census_version <- bound_census_version`, T2) and seats
   ONE `RecoveryAssignmentContinuationDueEvent` at `t_cont` through the S7 `PostEpilogueSchedulingContext`, then
   returns `recovery_branch_result(kind = DEFERRED, ...)` WITHOUT mutating `round_state`.
2. At `t_cont` the `RecoveryAssignmentContinuationDueEvent` handler records `continuation_due_at_event_time <-
   t_cont` and `continuation_due_dispatch_envelope`, and refreshes the census via
   `CaptureSecurityCensusOnRecoveryDeadline(..., census_source = RECOVERY_COMPLETION_DUE)`.
**Expected.** The Due event performs NO round-state transition, creates NO assignment, and does NOT mark `D`
APPLIED; it only records the due fact and refreshes the census. `round_state` is `SECURITY_RECOVERY` throughout;
`D` is `APPLYING`. A1 preserved.

## TV154 — The post-epilogue hook applies branch-C RESTORED only after the epilogue, mutually exclusive with the completion hook (T1)

**Setup.** At `t_cont` the census has been refreshed; the FINAL census warrants RESTORED (redistribution-only); the
episode + `APPLYING` decision are current.
**Steps.**
1. `ProcessEventTime(t_cont)` runs its canonical tail: `FinalizeEventTimeSecurityCensus(t_cont)` →
   `ApplyRecoveryCompletionAfterEpilogue(t_cont)` → `ApplyRecoveryAssignmentContinuationAfterEpilogue(t_cont)` →
   `FinalizePostRecoveryApplicationState(t_cont)`.
2. Because no completion is due at `t_cont` for this episode, `ApplyRecoveryCompletionAfterEpilogue` leaves the
   episode active; `ApplyRecoveryAssignmentContinuationAfterEpilogue` then applies branch C.
**Expected.** No branch-C RESTORED result is recorded during the ordinary event drain at `t_cont` — it is applied
ONLY by the post-epilogue hook. Per `RecoveryEpisodeID` at `t_cont` AT MOST ONE of the completion hook and the
continuation hook applies (a completion applied at `t_cont` would have cleared the episode, leaving the continuation
hook `nothing_due`). A1 preserved.

## TV155 — A stale continuation generation is a no-op (T2)

**Setup.** A reserve-dependent step (T6) has already re-armed the continuation with `continuation_generation = 2`
(`D.continuation_generation = 2`); an OLDER `RecoveryAssignmentContinuationDueEvent` carrying
`ContinuationGeneration = 1` is still on `EQ` and fires.
**Steps.**
1. The `RecoveryAssignmentContinuationDueEvent` stale/identity guard evaluates `ContinuationGeneration (= 1) !=
   D.continuation_generation (= 2)`.
**Expected.** The handler returns `recovery_continuation_due_stale_noop(decision_id)` — it records nothing, refreshes
no census, applies nothing. Only the ACTIVE generation's Due event is meaningful. A1 preserved.

## TV156 — A continuation whose bound version differs from the latest recovery census is a no-op (T2)

**Setup.** The continuation for `D` is due at `t`; between seating and application a newer FINAL recovery census was
published, so `latest_recovery_census[episode].RecoveryCensusVersion` advanced, and (in this vector) `D` was NOT
re-affirmed to it (e.g. the reconciliation path that would advance `continuation_bound_census_version` did not run
for this decision because it was superseded).
**Steps.**
1. `ApplyRecoveryAssignmentContinuationAfterEpilogue` reads the AUTHORITATIVE
   `D.continuation_bound_census_version` and COMPARES it to `census.RecoveryCensusVersion`; they differ.
**Expected.** The hook records `recovery_continuation_apply_stale_noop(decision_id)` and returns
`recovery_continuation_apply_stale` — branch C is NOT applied against a stale census version; the carried version is
not silently ignored (it is read and compared). A1 preserved.

## TV157 — A redistribution-only install reaches HASHING synchronously and only then is APPLIED (T3)

**Setup.** At `t` the continuation for `D` is due; the FINAL census satisfies the floor using ONLY currently
`ACTIVE_HASHING` miners (redistribution-only); `D` is `APPLYING`, the version binding matches (T2).
**Steps.**
1. `ApplyRecoveryAssignmentContinuationAfterEpilogue` BEGINs the install phase: `TRANSITION round_state ->
   ASSIGNMENT`; `recovery_install_in_progress <- true`; `RecoveryInstallID <- (episode, recovery_install_seq)`;
   `active_recovery_install_decision <- decision_id`.
2. It INSTALLs the disjoint set (no new template) and calls `CompleteAssignmentPhase`, which returns
   `assignment_phase_completed` (round now `HASHING`).
3. It marks `D` `APPLIED`, sets `recovery_outcome_finalised[episode] <- RESTORED`, removes `D` from pending, clears
   the install registries and `current_recovery_episode`.
**Expected.** The install is SYNCHRONOUS — no event boundary occurs within it, so no epilogue observes the transient
`ASSIGNMENT`-with-active-episode state. The exit is `HASHING` + `APPLIED`; RESTORED is applied ONLY after HASHING is
reached. A1 preserved.

## TV158 — An irreversible post-transition install failure aborts without fabricating UNRECOVERABLE (T4)

**Setup.** At `t` the redistribution-only install has already TRANSITIONed `SECURITY_RECOVERY -> ASSIGNMENT`
(irreversible mutation begun); the disjoint-set install then fails (`install_ok = false`).
**Steps.**
1. `ApplyRecoveryAssignmentContinuationAfterEpilogue` marks `D` `APPLY_FAILED_TERMINAL`, sets
   `recovery_episode_disposition[episode] <- RECOVERY_INSTALL_FAILED_ABORTED`, does NOT set
   `recovery_outcome_finalised`, clears the install registries and `current_recovery_episode`, and calls
   `RoundAbort(reason = recovery_install_failed_aborted, recovery_finalising = true)`.
**Expected.** The round closes via the DECLARED recovery-finalising abort; the outcome is recorded as its OWN
disposition `RECOVERY_INSTALL_FAILED_ABORTED` with status `APPLY_FAILED_TERMINAL` — it is NEVER relabelled as an
`UNRECOVERABLE` floor outcome (which is reserved for `CompleteSecurityRecovery` branch D from a final-census breach),
and `recovery_outcome_finalised` stays UNSET. A1 preserved.

## TV159 — A malformed assignment set returns a disposition and rolls back to SECURITY_RECOVERY (T5)

**Setup.** At `t` the redistribution-only install has TRANSITIONed to `ASSIGNMENT` and installed a set that is
malformed; `CompleteAssignmentPhase` runs.
**Steps.**
1. `CompleteAssignmentPhase` catches the well-formedness failure BEFORE the irreversible `HASHING` transition and
   returns `assignment_phase_failed(reason = malformed_assignment_set)` — the round is STILL `ASSIGNMENT`
   (reversible), no failed `ASSERT`.
2. `ApplyRecoveryAssignmentContinuationAfterEpilogue` takes the `ELSE` branch: it UNDOes the partial install,
   `TRANSITION round_state -> SECURITY_RECOVERY`, clears the install registries, marks `D` `APPLY_FAILED`, and
   removes `D` from pending.
**Expected.** The failure is REVERSIBLE — the round returns to `SECURITY_RECOVERY` with the episode PRESERVED (a
later epilogue may re-seat if still warranted); the malformed set never transitions to `HASHING`. A1 preserved.

## TV160 — A reserve-dependent restoration stays SECURITY_RECOVERY and re-arms a fresh-generation continuation (T6)

**Setup.** At `t` the continuation for `D` is due; the FINAL census does NOT satisfy the floor with only currently
`ACTIVE_HASHING` miners — it depends on a PENDING/WAKING reserve (reserve-dependent).
**Steps.**
1. `ApplyRecoveryAssignmentContinuationAfterEpilogue` takes the reserve-dependent `ELSE` branch: it does NOT enter
   the install phase and does NOT finalise RESTORED; it calls `ReserveActivate` (whose `StartWake` seats a
   `WakeCompleteEvent` STRICTLY LATER through `PostEpilogueSchedulingContext`, T7), keeps `round_state =
   SECURITY_RECOVERY`, keeps `D` `APPLYING`, bumps `continuation_generation` to `D.continuation_generation + 1`,
   updates `continuation_id`, and RE-ARMS a strictly-later `RecoveryAssignmentContinuationDueEvent` at
   `next_representable_simulation_time(t)`.
2. At a LATER event_time the reserve is `ACTIVE_HASHING`; the re-armed continuation's post-epilogue application now
   finds the redistribution-only predicate satisfied, installs synchronously (T3), and marks `D` `APPLIED`.
**Expected.** Reserve-dependent RESTORED is NEVER applied while reserves are PENDING/WAKING — a syntactically valid
PENDING set is not treated as restored hash rate; RESTORED is applied ONLY once a later final census confirms the
floor with the reserve `ACTIVE_HASHING`. A1 preserved.

## TV161 — ProcessEventTime asserts no recovery-continuation application remains due at t (T7)

**Setup.** `ProcessEventTime(t)` has drained `t`, run the epilogue, the completion hook, and the continuation hook.
**Steps.**
1. The continuation hook either APPLIED the continuation at `t` (redistribution-only), or RE-ARMED it at a STRICTLY
   LATER event_time (reserve-dependent, T6), or found nothing due — in every case nothing branch-C-related remains
   due at `t`.
2. `ProcessEventTime` evaluates the T7 assertion `no recovery-continuation application remains due at t` (alongside
   the R1 `no ordinary event remains at t` and R2 `security_census_dirty[t] = false` assertions).
**Expected.** The assertion holds — every StartWake/re-arm the continuation seats is at a strictly-later event_time
via `PostEpilogueSchedulingContext`, so `t` is finalised with no continuation application still due at it. A1
preserved.

## TV162 — Reconcile advances a re-affirmed DEFERRED decision's continuation bound version to the latest (T2 rule B)

**Setup.** A DEFERRED branch-C decision `D` (`continuation_id != null`) is still CONSISTENT with a newer FINAL
recovery census published while its continuation is pending.
**Steps.**
1. `ReconcilePendingRecoveryDecisions` re-affirms `D`: it sets `D.bound_census_version <-
   census.RecoveryCensusVersion` and, because `D.continuation_id != null`, sets `D.continuation_bound_census_version
   <- census.RecoveryCensusVersion` (T2 rule B).
**Expected.** The AUTHORITATIVE continuation bound version tracks the LATEST final census, so the eventual
post-epilogue application (TV154/TV157) applies against the current census; the immutable Due event carried only the
generation, never a stale version. (A decision that CONTRADICTS the newer census is SUPERSEDED and its continuation
Due event cancelled — not re-affirmed.) A1 preserved.

---

## Coverage summary

| Vector | Correction | Exercises |
|--------|-----------|-----------|
| TV153 | T1 | Due event records due + refreshes census; NO transition / assignment / APPLIED |
| TV154 | T1 | post-epilogue hook is the sole branch-C application; mutual exclusion with the completion hook |
| TV155 | T2 | a stale `ContinuationGeneration` Due event is a no-op |
| TV156 | T2 | a continuation whose bound version differs from the latest census is a no-op |
| TV157 | T3 | redistribution-only install reaches HASHING synchronously → only then APPLIED |
| TV158 | T4 | irreversible post-transition install failure → `RECOVERY_INSTALL_FAILED_ABORTED` + `APPLY_FAILED_TERMINAL`, no fabricated UNRECOVERABLE |
| TV159 | T5 | malformed set → `assignment_phase_failed` → rollback to `SECURITY_RECOVERY`, episode preserved |
| TV160 | T6 | reserve-dependent restoration stays `SECURITY_RECOVERY`, re-arms fresh generation, applies only when reserve `ACTIVE_HASHING` |
| TV161 | T7 | `ProcessEventTime` asserts no recovery-continuation application remains due at `t` |
| TV162 | T2 | Reconcile rule B advances a re-affirmed DEFERRED decision's `continuation_bound_census_version` to the latest |

All ten vectors pass on paper against the exact named procedures. No new consensus feature; documentation only;
name remains PoCol; the A1 baseline `8.420833333 kWh` is unchanged. The prohibited rebranded-algorithm-name
variants are not used anywhere in this document.
