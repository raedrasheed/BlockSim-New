# Stage 1Q — Decision-Supersession Audit (Q3)

## Intro

This audit is a documentation-only record of Stage 1Q correction **Q3 — atomic
decision supersession** in `STAGE_01_PROTOCOL_PSEUDOCODE.md`. The consensus
specification under revision is **PoCol**. Within PoCol, *the idle policy within
PoCol* is referenced strictly as a mechanism; it is not the subject of Q3 and no
behavioural change to it is described here. This audit claims no property and revises
no measured quantity: the A1 baseline of **8.420833333 kWh** is UNCHANGED.

Scope is limited to Q3: the `RECOVERY_DECISION_STATUS` enum, the two recovery-decision
registries (`recovery_decisions`, `pending_recovery_decisions`), the atomic
supersede-before-seat ordering in `ReconcilePendingRecoveryDecisions` (§9), and the
status transitions in `SeatRecoveryCompletion` (§9) and
`ApplyRecoveryCompletionAfterEpilogue` (§10a). Q3 makes each pending recovery decision
an EXPLICIT identity with an explicit lifecycle, replacing a single ambiguous boolean.

## 1. `RECOVERY_DECISION_STATUS` and the two registries (§0.8 Core data model)

`RECOVERY_DECISION_STATUS in {CREATED, SCHEDULED, SUPERSEDED, APPLIED, SCHEDULE_FAILED,
CANCELLED}` (§0.8). Two registries carry Q3, both reset per round by `RoundInitialise`:

- `recovery_decisions` — a map `RecoveryDecisionID -> decision_record { episode,
  outcome, bound_census_version (RecoveryCensusVersion), status, target_time,
  due_event_ref, due_at_event_time }` (§0.8). This makes each decision an EXPLICIT
  identity with an explicit lifecycle, NOT one ambiguous boolean.
- `pending_recovery_decisions` — a map `RecoveryEpisodeID -> SET of RecoveryDecisionIDs`
  whose status is `{CREATED, SCHEDULED}` (§0.8). It is the "remaining scheduled decision
  set" (P4/Q3). A decision is ADDED only after `ScheduleEvent` succeeds and REMOVED on
  `SUPERSEDED`, `CANCELLED`, `APPLIED`, or `SCHEDULE_FAILED`.

A SET (not a boolean) is required because multiple superseded/scheduled decisions may
transiently coexist for one episode: while one decision is being superseded and its
replacement is being seated, both identities are individually tracked. `bound_census_version`
binds a decision to the `RecoveryCensusVersion` that justified it (Q1); `due_event_ref`
holds the queued `RecoveryCompletionDueEvent` handle so it can be cancelled on supersession.

## 2. Atomic supersede-before-seat ordering in `ReconcilePendingRecoveryDecisions` (§9)

The event-time epilogue (`SecurityFloorEvaluate`, §9) runs a FIXED order while
`round_state = SECURITY_RECOVERY`: `CommitRecoveryCensus` (version the FINAL census) →
`ReconcilePendingRecoveryDecisions` (supersede/re-affirm) → `SeatRecoveryCompletion`
(seat the warranted outcome). Reconcile therefore runs to completion BEFORE any
replacement decision is seated.

For each `decision_id` in `pending_recovery_decisions[episode]` (stable order),
`ReconcilePendingRecoveryDecisions` evaluates `outcome_consistent_with_census(D.outcome,
census)` against the newly published `latest_recovery_census[episode]`:

- **Contradicted** — the newer FINAL census does NOT justify `D.outcome`. IMMEDIATELY:
  `SET recovery_decisions[decision_id].status <- SUPERSEDED`; if `D.due_event_ref != null`
  and is still pending on EQ, `CANCEL D.due_event_ref on EQ` (the same CANCEL idiom as
  G8/M3); `REMOVE decision_id from pending_recovery_decisions[episode]`. This happens
  BEFORE any replacement is seated.
- **Still consistent** — `SET recovery_decisions[decision_id].bound_census_version <-
  census.RecoveryCensusVersion` (re-affirm to the newest version).

After Reconcile, NO pending decision retains an older census version: each is either
`SUPERSEDED` (and removed) or re-affirmed to the latest `RecoveryCensusVersion` (§9 NOTE).
A `SUPERSEDED` decision NEVER becomes valid again — its status is terminal-negative.

## 3. Status transitions in `SeatRecoveryCompletion` (§9)

`SeatRecoveryCompletion` is the SOLE seater. It creates a fresh decision record at
`CREATED` (bound to the current census version, `due_event_ref = null`) and sets its
`target_time` (Q7, `t + configured_recovery_completion_delay`) BEFORE scheduling. From
`CREATED` the record moves along exactly one edge:

- `CREATED -> SCHEDULED` — on `ScheduleEvent` success: record `due_event_ref`, `ADD
  decision_id to pending_recovery_decisions[episode]` (added ONLY after success, P4/Q3);
  RETURN `recovery_completion_seated`.
- `CREATED -> SCHEDULE_FAILED` — on scheduler rejection: it is NOT added to the pending
  set; `RECORD recovery_completion_schedule_rejected`; RETURN `recovery_completion_not_seated`.
- `CREATED -> CANCELLED` — when `target_time > run_horizon_T`: `RECORD horizon_deferred`;
  RETURN `recovery_completion_horizon_deferred` (`CloseRoundAtHorizon`, §20b, governs run end).

`pending_recovery_decisions` is updated ONLY on the `SCHEDULED` edge. A failed superseding
schedule leaves the earlier `SUPERSEDED` decision terminal-negative (it was already removed
by Reconcile and is NEVER revived); `pending_recovery_decisions` reflects the remaining
scheduled set; and the round stays `SECURITY_RECOVERY` (§9 SeatRecoveryCompletion ELSE branch).

## 4. Status transitions in `ApplyRecoveryCompletionAfterEpilogue` (§10a)

`ApplyRecoveryCompletionAfterEpilogue` (§10a) is the ONLY place a recovery outcome is
APPLIED. Post-quiescence, for each `decision_id` in `pending_recovery_decisions[episode]`
with `due_at_event_time = t`:

- **Fresh + matches** — `D.status = SCHEDULED` AND `D.bound_census_version =
  census.RecoveryCensusVersion` AND `outcome_consistent_with_census(D.outcome, census)`:
  `status <- APPLIED`; `SET recovery_outcome_finalised[episode] <- D.outcome`; remove from
  pending; then dispatch the R13/R14 branch via `CompleteSecurityRecovery`.
- **Non-latest / contradicted** — otherwise: `status <- SUPERSEDED`; `REMOVE decision_id`;
  `RECORD recovery_apply_stale_noop`. A `RESTORED` decision cannot leave recovery under a
  breach census. A `SUPERSEDED` decision NEVER becomes valid again.

## 5. Worked scenario (TV129-style) — failed superseding schedule

- **t1 — D1 seated (RESTORED).** The FINAL recovery census shows no breach → `warranted =
  RESTORED`. `SeatRecoveryCompletion` mints `D1`, `ScheduleEvent` succeeds: `D1.status =
  SCHEDULED`, `D1` added to `pending_recovery_decisions[episode]`, bound to census `v1`.
- **t2 — newer census selects UNRECOVERABLE; D2 schedule FAILS.** The epilogue publishes
  census `v2` (breach AND deadline reached). `ReconcilePendingRecoveryDecisions` runs FIRST:
  `outcome_consistent_with_census(RESTORED, v2) = (v2.breach = false) = false` → `D1.status
  <- SUPERSEDED`, `CANCEL D1.due_event_ref on EQ`, `D1` removed from the pending set. Then
  `warranted = UNRECOVERABLE`; `SeatRecoveryCompletion` mints `D2` (`target_time <= T`), but
  `ScheduleEvent` REJECTS → `D2.status <- SCHEDULE_FAILED`, `D2` NOT added to pending,
  `recovery_completion_schedule_rejected` recorded, RETURN `recovery_completion_not_seated`.
- **Result.** `D1 = SUPERSEDED` (terminal-negative, never revived), `D2 = SCHEDULE_FAILED`
  (never pending), `pending_recovery_decisions[episode]` empty, `recovery_outcome_finalised`
  NOT set, and the round stays `SECURITY_RECOVERY`. A later FINAL census may mint a fresh
  `D3`; D1's failure-of-replacement never revives D1.

## 6. Proof sketch — a failed superseding schedule can never apply the earlier decision

Let D1 be a pending decision that a newer FINAL census contradicts, and let the superseding
schedule of its replacement D2 fail.

1. `ReconcilePendingRecoveryDecisions` runs BEFORE `SeatRecoveryCompletion` in the epilogue
   order (§2 above). It sets `D1.status <- SUPERSEDED` and REMOVES D1 from
   `pending_recovery_decisions[episode]` — unconditionally, before D2 is even minted.
2. `ApplyRecoveryCompletionAfterEpilogue` (§10a) iterates ONLY members of
   `pending_recovery_decisions[episode]`. D1 is not a member, so it is never iterated.
3. Even if D1's queued `RecoveryCompletionDueEvent` were dispatched, its stale guard
   (§10a step 1) rejects any `RecoveryDecisionID NOT in pending_recovery_decisions` →
   `recovery_due_stale_noop`; no `due_at_event_time` is set for D1.
4. No procedure writes `SCHEDULED` onto a `SUPERSEDED` record; `SUPERSEDED` is terminal-
   negative. The §10a freshness test (`D.status = SCHEDULED`) would fail for D1 regardless.
5. D2's `SCHEDULE_FAILED` writes NO field of D1 and adds nothing to the pending set.

Therefore neither D2's failure nor any subsequent event can cause D1 to apply. ∎ (sketch)

## 7. Acceptance checks

| # | Check | Evidence | Result |
|---|-------|----------|--------|
| 1 | `RECOVERY_DECISION_STATUS in {CREATED, SCHEDULED, SUPERSEDED, APPLIED, SCHEDULE_FAILED, CANCELLED}`; `recovery_decisions` maps `RecoveryDecisionID -> {episode, outcome, bound_census_version, status, target_time, due_event_ref, due_at_event_time}` | §0.8 | PASS |
| 2 | `pending_recovery_decisions[episode]` is a SET of `RecoveryDecisionIDs` (status `CREATED`/`SCHEDULED`); ADDED only after `ScheduleEvent` success; REMOVED on `SUPERSEDED`/`CANCELLED`/`APPLIED`/`SCHEDULE_FAILED` | §0.8 | PASS |
| 3 | `ReconcilePendingRecoveryDecisions` marks a contradicted pending decision `SUPERSEDED`, cancels its `due_event_ref` on EQ when pending, and removes it — IMMEDIATELY, BEFORE any replacement is seated (epilogue order `CommitRecoveryCensus` → `Reconcile` → `Seat`) | §9 | PASS |
| 4 | `SeatRecoveryCompletion` transitions `CREATED -> SCHEDULED` (add to pending) / `SCHEDULE_FAILED` (not added) / `CANCELLED` (horizon_deferred) | §9 SeatRecoveryCompletion EFFECTS | PASS |
| 5 | `ApplyRecoveryCompletionAfterEpilogue`: `SCHEDULED` + re-affirmed + consistent -> `APPLIED`; non-latest/contradicted -> `SUPERSEDED` + removed; a `SUPERSEDED` decision never becomes valid again | §10a EFFECTS | PASS |
| 6 | Gate 4: a failed superseding schedule (`SCHEDULE_FAILED`) cannot revive or preserve the earlier `SUPERSEDED` decision; no procedure writes `SCHEDULED` onto a `SUPERSEDED` record | §9 Reconcile NOTE; §9 Seat ELSE branch; §10a | PASS |
| 7 | Gate 5: pending decisions are explicit `RecoveryDecisionID` identities held in a SET (not one ambiguous boolean); multiple superseded/scheduled decisions may transiently coexist | §0.8 | PASS |
| 8 | TV129-style: D1 `RESTORED` pending; newer census selects `UNRECOVERABLE` but scheduling D2 fails → D1 `SUPERSEDED`, D2 `SCHEDULE_FAILED`, round stays `SECURITY_RECOVERY` | §9; §10a | PASS |

---

Documentation only. The consensus specification is named PoCol; *the idle policy within
PoCol* is referenced as a mechanism only. No property is claimed. The A1 baseline
8.420833333 kWh is unchanged. The prohibited rebranded-algorithm-name variants are not
used anywhere in this document.
