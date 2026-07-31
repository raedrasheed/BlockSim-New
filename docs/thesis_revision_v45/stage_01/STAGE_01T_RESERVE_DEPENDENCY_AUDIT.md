# STAGE 01T — Reserve-Dependent vs Redistribution-Only Restoration Audit (T6)

## Intro

This audit records ONE Stage-1T correction (T6) to the PoCol protocol pseudocode in
`STAGE_01_PROTOCOL_PSEUDOCODE.md`. T6 is a restoration-CLASSIFICATION and LIVENESS correction to the
post-epilogue branch-C continuation hook `ApplyRecoveryAssignmentContinuationAfterEpilogue` (§10a): it
distinguishes a *redistribution-only* RESTORED (installable SYNCHRONOUSLY from currently
`ACTIVE_HASHING` miners) from a *reserve-dependent* RESTORED (whose floor depends on `PENDING`/`WAKING`
reserves not yet `ACTIVE_HASHING`), and it fixes WHEN each may finalise `RESTORED`. It does not add any
consensus feature and does not change how the round transitions, only WHICH of two disciplines the
continuation hook follows once a decision is fresh and warranted.

T6 changes the CLASSIFICATION of a restoration and the LIVENESS discipline that follows from it — never
how time or energy is counted. No residency interval, no `t_<state>` accumulation, and no census H-value
is touched by this correction; the mechanism under discussion is the idle policy within PoCol. The A1
accepted baseline of **8.420833333 kWh is UNCHANGED**. This document is descriptive only.

## The classification point

`ApplyRecoveryAssignmentContinuationAfterEpilogue` (§10a) is the ONLY place branch-C `RESTORED` is
APPLIED, run by `ProcessEventTime` (§0.7d) AFTER the single unconditional event-time epilogue
`FinalizeEventTimeSecurityCensus(t)` and AFTER `ApplyRecoveryCompletionAfterEpilogue(t)` — it is a
post-epilogue hook, NOT a queued microphase. Before any classification runs, the hook applies the T2
FRESHNESS + VERSION BINDING gate: it applies branch C only when

```
round_state = SECURITY_RECOVERY
  AND D.status = APPLYING
  AND D.continuation_bound_census_version = census.RecoveryCensusVersion
  AND outcome_consistent_with_census(RESTORED, census)
```

(reading the AUTHORITATIVE `continuation_bound_census_version` from the decision record, kept current by
`ReconcilePendingRecoveryDecisions`, and comparing it to
`latest_recovery_census[episode].RecoveryCensusVersion`). Only a FRESH and WARRANTED decision reaches
the T6 two-way classification. The classification predicate is exactly:

```
IF the FINAL census at t satisfies the floor using ONLY currently ACTIVE_HASHING miners:   # T6-A redistribution-only
  … synchronous install …
ELSE:                                                                                       # T6-B reserve-dependent
  … activate reserve, stay SECURITY_RECOVERY, re-arm …
```

The predicate reads the FINAL (settled) census at `t` — the one the epilogue published for this settled
`event_time` — and asks whether the floor is met by hash rate that is ALREADY `ACTIVE_HASHING`. That
single question separates the two branches.

## T6-A — redistribution-only (synchronous install → APPLIED)

When the FINAL census at `t` satisfies the floor using ONLY currently `ACTIVE_HASHING` miners, the
restoration is *redistribution-only*: no not-yet-active hash rate is needed, so the assignment set can be
installed SYNCHRONOUSLY. The hook BEGINS the T3 installation phase — a synchronous sub-computation with
NO event boundary within it — by transitioning `round_state -> ASSIGNMENT` (bumping `state_version`,
G10), setting `recovery_install_in_progress <- true`, minting a `RecoveryInstallID`, and INSTALLing the
disjoint assignment set under `(RoundID_current, TemplateID_committed)`. Because no event boundary occurs
inside the install, no epilogue ever observes the transient `ASSIGNMENT`-with-active-episode state (the
T3 episode invariant holds at every boundary). On `CompleteAssignmentPhase` reporting
`assignment_phase_completed` the round is `HASHING`, and THIS is the moment branch-C `RESTORED` is
actually applied:

```
CALL SetRecoveryDecisionStatus(RoundContext, decision_id, APPLIED)     # R4/R6
SET recovery_outcome_finalised[episode] <- RESTORED                    # set ONLY on an actually-applied outcome (T4)
REMOVE decision_id from pending_recovery_decisions[episode]
SET current_recovery_episode <- null
RETURN recovery_continuation_applied(decision_id, RESTORED)
```

Every T3 install exit ends in exactly one of `HASHING` + `APPLIED`, `SECURITY_RECOVERY` +
`APPLY_FAILED` (a reversible pre-`HASHING` failure rolled back), or `ROUND_ABORTED` +
`RECOVERY_INSTALL_FAILED_ABORTED` (a T4 irreversible post-mutation install failure — never a fabricated
`UNRECOVERABLE`). Redistribution-only is the ONLY path on which `recovery_outcome_finalised[episode]`
is set to `RESTORED`.

## T6-B — reserve-dependent (activate reserve, stay SECURITY_RECOVERY, re-arm)

When the ELSE branch is taken the floor depends on `PENDING`/`WAKING` reserves that are NOT yet
`ACTIVE_HASHING`. Here the hook does NOT finalise `RESTORED` and does NOT enter the installation phase.
Instead it:

1. builds a `PostEpilogueSchedulingContext` (`source_event_time = t`, T7) so every scheduled effect is
   seated STRICTLY LATER than `t`;
2. calls `ReserveActivate(RoundContext, deficit, …)`, whose `StartWake` seats a `WakeCompleteEvent`
   STRICTLY LATER through that post-epilogue context (T7) — the reserve reaches `ACTIVE_HASHING` only
   at its own scheduled `WakeCompleteEvent`, never at `t`;
3. keeps the round in `SECURITY_RECOVERY` (no `round_state` mutation);
4. keeps the decision `APPLYING` (the episode stays active; the decision stays in
   `pending_recovery_decisions[episode]` so a newer census can still supersede it);
5. bumps `continuation_generation <- D.continuation_generation + 1` and mints a FRESH
   `continuation_id = (decision_id, continuation_generation)` (T2: a NEW ACTIVE continuation);
6. RE-ARMS a strictly-later `RecoveryAssignmentContinuationDueEvent` at
   `t_rearm = next_representable_simulation_time(t)` carrying the fresh `ContinuationGeneration`, seated
   through the T7 post-epilogue context; and
7. returns `recovery_continuation_reserve_pending(decision_id)` — decision `APPLYING`, episode active,
   round `SECURITY_RECOVERY`.

`RESTORED` is applied ONLY when a LATER final census confirms the floor with the reserve now
`ACTIVE_HASHING` — at which point the redistribution-only predicate (T6-A) HOLDS and the synchronous
install runs. This is exactly the T6/gate 9 rule quoted in the hook: reserve-dependent `RESTORED` is
NEVER applied while reserves are `PENDING`/`WAKING`, because "a syntactically valid PENDING assignment
set is not restored hash rate."

## Why the reserve-dependent path must NOT synchronously install

The synchronous install (T6-A) transitions `SECURITY_RECOVERY -> ASSIGNMENT` and drives the round to
`HASHING`, at which point it marks the decision `APPLIED` and sets
`recovery_outcome_finalised[episode] <- RESTORED`. That sequence declares the reduced-participation
regime RECOVERED. If it were run while the floor is met only on paper — by a `PENDING`/`WAKING` reserve
set that has NOT yet raised `ACTIVE_HASHING` hash rate to the floor — then `RESTORED` would be finalised
against hash rate that does not yet exist. A `PENDING` assignment is bound but not activated; `PENDING ->
CURRENT` and the miner's `ACTIVE_HASHING` entry occur ONLY at the scheduled `WakeCompleteEvent`
(`ReserveActivate` / §11 wake completion). The T6-B classification therefore refuses to install: it
activates the reserve, LEAVES the round in `SECURITY_RECOVERY`, and DEFERS the finalisation to a later
census that can be checked against ACTIVE hash rate. The install is gated on the redistribution-only
predicate precisely so that the floor is always confirmed by `ACTIVE_HASHING` miners before `RESTORED`
is recorded.

## The reserve-dependent re-arm loop

The reserve-dependent branch is a self-re-arming loop that terminates in a redistribution-only install
(or in supersession / a terminal round). Each pass:

```
FINAL census at t: floor NOT met by ACTIVE_HASHING alone   (T6-B: reserve-dependent)
  -> ReserveActivate(deficit)          # StartWake -> WakeCompleteEvent STRICTLY LATER (T7)
  -> round STAYS SECURITY_RECOVERY     # no round_state mutation
  -> decision STAYS APPLYING           # episode active; still in pending_recovery_decisions
  -> continuation_generation += 1      # T2: fresh ACTIVE continuation identity
  -> RE-ARM RecoveryAssignmentContinuationDueEvent at next_representable_simulation_time(t)  # T7 strictly later
  -> RETURN recovery_continuation_reserve_pending

… reserve reaches ACTIVE_HASHING at its WakeCompleteEvent (strictly later) …

FINAL census at t' > t: floor NOW met by ACTIVE_HASHING alone   (T6-A: redistribution-only)
  -> TRANSITION SECURITY_RECOVERY -> ASSIGNMENT (T3 synchronous install)
  -> INSTALL disjoint assignment set -> CompleteAssignmentPhase -> HASHING
  -> SetRecoveryDecisionStatus(decision_id, APPLIED)
  -> recovery_outcome_finalised[episode] <- RESTORED
  -> RETURN recovery_continuation_applied(decision_id, RESTORED)
```

Every re-arm is STRICTLY LATER (T7), carries a FRESH `continuation_generation`, and is guarded at
dispatch by `RecoveryAssignmentContinuationDueEvent` (§10a T1), which is meaningful only for the CURRENT
episode/epoch, an `APPLYING` decision, and `ContinuationGeneration = D.continuation_generation` — so a
stale generation is a `recovery_continuation_due_stale_noop`. The loop cannot finalise `RESTORED` on any
pass whose census fails the ACTIVE-hash predicate; it can only re-arm, be superseded by a contradicting
final census (`Reconcile`), or be cancelled on terminal closure (S4). The T3 episode invariant records
this directly: "A reserve-dependent restoration keeps the round in `SECURITY_RECOVERY` (reserve
`PENDING`/`WAKING`) until a later final census confirms the floor (T6)."

## RESTORED is never applied before active-hash restoration

The set of statements that finalise a restoration —
`SetRecoveryDecisionStatus(decision_id, APPLIED)` for branch C and
`recovery_outcome_finalised[episode] <- RESTORED` — appear in the pseudocode ONLY inside the
redistribution-only arm of `ApplyRecoveryAssignmentContinuationAfterEpilogue`, on the
`assignment_phase_completed` exit where "the round now HASHING; the FINAL census confirms the floor
(redistribution-only)." The reserve-dependent arm contains NEITHER statement: it returns
`recovery_continuation_reserve_pending` with the decision still `APPLYING` and
`recovery_outcome_finalised[episode]` UNSET. Because the redistribution-only predicate is a precondition
of every finalisation, and that predicate requires the floor to be met by `ACTIVE_HASHING` miners, no
reserve-dependent `RESTORED` can be recorded before the reserve is actually active.

## Tie to invariant I16

I16 (STAGE_01_INVARIANT_CATALOGUE.md) requires that security-floor breaches are recorded, not silently
repaired in the reported data. Its T6 clause states: "a `RESTORED` outcome that depends on
`PENDING`/`WAKING` reserves is NOT applied while those reserves are inactive — a syntactically valid
`PENDING` assignment set is not treated as restored hash rate, so the reduced-participation regime is
never reported as recovered before the reserve is `ACTIVE_HASHING`." The reserve-dependent re-arm loop is
exactly the mechanism that enforces this: while the reserve is `PENDING`/`WAKING` the round remains in
`SECURITY_RECOVERY` and the episode remains unfinalised, so the reduced-participation regime continues to
be reported as unrecovered. The I16 "Consequence of violation" names the failure this prevents — "a
reserve-dependent restoration reported as recovered before the reserve is actually active." T6 removes
that consequence by construction.

## PASS-check table

| Check | Guarantee | Exact names cited |
|-------|-----------|-------------------|
| Classification is two-way on ACTIVE hash rate | `IF the FINAL census at t satisfies the floor using ONLY currently ACTIVE_HASHING miners` chooses T6-A; `ELSE` chooses T6-B | `ApplyRecoveryAssignmentContinuationAfterEpilogue` (§10a) |
| Only fresh + warranted decisions are classified | T2 gate: `round_state = SECURITY_RECOVERY` AND `D.status = APPLYING` AND `D.continuation_bound_census_version = census.RecoveryCensusVersion` AND `outcome_consistent_with_census(RESTORED, census)` | `continuation_bound_census_version`, `ReconcilePendingRecoveryDecisions` |
| Redistribution-only finalises RESTORED | synchronous T3 install → `HASHING` → `SetRecoveryDecisionStatus(…, APPLIED)`, `recovery_outcome_finalised[episode] <- RESTORED` | `CompleteAssignmentPhase` = `assignment_phase_completed` |
| Reserve-dependent does NOT finalise | returns `recovery_continuation_reserve_pending`; decision stays `APPLYING`; `recovery_outcome_finalised` UNSET; round stays `SECURITY_RECOVERY` | T6-B ELSE branch |
| Reserve activation is strictly later | `ReserveActivate` `StartWake` → `WakeCompleteEvent` STRICTLY LATER via `PostEpilogueSchedulingContext` | `ReserveActivate`, T7 |
| Re-arm is strictly later with fresh generation | `t_rearm = next_representable_simulation_time(t)`; `continuation_generation <- D.continuation_generation + 1`; re-armed `RecoveryAssignmentContinuationDueEvent` | T6/T7, `ContinuationGeneration` |
| RESTORED never applied while reserve inactive | T6/gate 9: "a syntactically valid PENDING set is not restored hash rate" | I16 (T6 clause) |

## Failure mode this correction excludes

The excluded failure mode is: `RESTORED` finalised on a valid-but-`PENDING` reserve set that has NOT yet
raised `ACTIVE_HASHING` hash rate to the floor. Under that failure the hook would take the synchronous
install on a census whose floor is met only by not-yet-active reserves, transition to `ASSIGNMENT` and
`HASHING`, mark the decision `APPLIED`, and set `recovery_outcome_finalised[episode] <- RESTORED` — thus
reporting the reduced-participation regime as recovered while the hash rate backing that report is still
`PENDING`/`WAKING`. T6 makes this impossible: the ACTIVE-hash predicate gates the install, the ELSE
branch performs NO finalisation, and the round is held in `SECURITY_RECOVERY` across every re-arm until a
later FINAL census confirms the floor with the reserve `ACTIVE_HASHING`. The `PENDING` set is treated as
what it is — bound but inactive — and never as restored hash rate.

## Result

After T6 the post-epilogue continuation hook `ApplyRecoveryAssignmentContinuationAfterEpilogue` (§10a)
CLASSIFIES every fresh, warranted branch-C `RESTORED` into exactly one of two disciplines by a single
predicate on the FINAL census at `t`. Redistribution-only (the floor is met using ONLY currently
`ACTIVE_HASHING` miners) runs the T3 synchronous install and is the ONLY path that marks the decision
`APPLIED` and sets `recovery_outcome_finalised[episode] <- RESTORED`. Reserve-dependent (the floor
depends on `PENDING`/`WAKING` reserves) activates the reserve via `ReserveActivate` (StartWake →
`WakeCompleteEvent` STRICTLY LATER, T7), keeps the round in `SECURITY_RECOVERY`, keeps the decision
`APPLYING`, bumps `continuation_generation`, and re-arms a strictly-later
`RecoveryAssignmentContinuationDueEvent` — applying `RESTORED` ONLY once a later FINAL census confirms the
floor with the reserve `ACTIVE_HASHING`. Reserve-dependent `RESTORED` is therefore NEVER applied while
reserves are inactive, which is exactly what invariant I16 requires. No accounting of time or energy
changed: T6 is a restoration-classification and liveness correction, never a change to how time or energy
is counted; the A1 accepted baseline of 8.420833333 kWh is UNCHANGED, and no consensus feature was added.
T6 is documented here only.

The prohibited rebranded-algorithm-name variants are not used anywhere in this document.
