# Stage 1S — Deferred Branch-C Recovery Atomicity Audit (S2/S3)

This is a documentation-only paper audit of two Stage-1S corrections as edited in
`docs/thesis_revision_v45/stage_01/STAGE_01_PROTOCOL_PSEUDOCODE.md`: **S2 — seat
before mutate** (branch C must NOT transition `round_state` to `ASSIGNMENT` before its
`RecoveryAssignmentContinuationEvent` is seated) and **S3 — seating is not applying**
(seating the continuation does not apply `RESTORED`; the decision stays `APPLYING`,
the episode stays ACTIVE, and `RESTORED` is applied only when the continuation reaches
`HASHING`). The consensus algorithm is named **PoCol**; **the idle policy within
PoCol** is referenced here as a mechanism only, and this audit claims no energy,
security, or fairness property of the idle policy within PoCol. S2 and S3 are ordering
and atomicity corrections to the deferred branch-C recovery lifecycle; they never
change how time or energy is counted. The **A1 accepted accounting baseline of
8.420833333 kWh is UNCHANGED** — no census value, residency interval, transition-energy
term, or accounting quantity is edited. This is documentation only: no new consensus
feature is introduced. Every claim below is checked against the pseudocode as edited;
no behavior is inferred beyond the text.

## 1. The three-kind disposition contract (§10a)

`ApplyRecoveryCompletionAfterEpilogue` (§10a, `PROCEDURE` at line 2464) is the ONLY
site that applies or defers a recovery outcome. After the freshness VERIFY (lines
2490–2497) it marks the decision `APPLYING` (line 2500) and calls the INTERNAL branch
dispatch `CompleteSecurityRecovery` (`PROCEDURE` at line 2546), which returns an
EXPLICIT `recovery_branch_result(kind, ...)` with `kind in {SUCCESS, DEFERRED, FAILED}`
(line 2553). The caller dispatches on the kind alone:

| Disposition kind | Branch (source) | Caller action in `ApplyRecoveryCompletionAfterEpilogue` |
|---|---|---|
| `SUCCESS` | A `SOLUTION_PROPAGATION` (2568–2576), B `HASHING` (2577–2582), D `ROUND_ABORTED` (2558–2566) | Mark `APPLIED`; set `recovery_outcome_finalised[episode]`; remove from `pending`; clear `current_recovery_episode`; return `recovery_applied` (lines 2506–2513) |
| `DEFERRED` | C, continuation seated (2604–2609) | Leave decision `APPLYING`; `recovery_outcome_finalised` NOT set; `current_recovery_episode` NOT cleared; decision STAYS in `pending`; round STAYS `SECURITY_RECOVERY`; return `recovery_deferred` (lines 2514–2520) |
| `FAILED` | A/B transition failed (2576, 2582), D abort did not terminate (2566), C horizon-defer (2590–2592) or seat rejected (2610–2612) | Do NOT mark `APPLIED`; record `APPLY_FAILED` (or `HORIZON_DEFERRED` when `reason = horizon_deferred`); PRESERVE the episode; remove from `pending`; round STAYS `SECURITY_RECOVERY`; return `recovery_apply_failed` (lines 2521–2531) |

The episode is cleared on exactly ONE synchronous path — a `SUCCESS` disposition
(branches A/B/D). A `DEFERRED` disposition defers the finalisation entirely to the
continuation; a `FAILED` disposition finalises nothing (§10a NOTE lines 2535–2544).

## 2. S2 — branch C seats its continuation BEFORE any round-state mutation

Branch C (`RESTORED` requiring range redistribution or a new reserve assignment) is
the `ELSE` arm of `CompleteSecurityRecovery` (§10a lines 2583–2612). Under S2 it does
NOT mutate `round_state`; it executes the canonical order and only then reports its
disposition, so the round REMAINS `SECURITY_RECOVERY` throughout the procedure (line
2586–2588):

1. **Compute `t_cont`** — `t_cont <- next_representable_simulation_time(dispatch_envelope.event_time)`
   (line 2589), a STRICTLY LATER `event_time` than the drained application `t` (R1).
2. **Validate `t_cont <= T`** (line 2590) — if `t_cont > run_horizon_T`, record
   `recovery_continuation_horizon_deferred` and RETURN `recovery_branch_result(kind =
   FAILED, reason = horizon_deferred)` (lines 2591–2592). No round-state mutation has
   occurred; the caller records `HORIZON_DEFERRED` and preserves the episode.
3. **Seat ONE continuation** — build the S7 `PostEpilogueSchedulingContext` (lines
   2595–2596) and `ScheduleEvent(... RecoveryAssignmentContinuationEvent ...)` at
   `target_event_time = t_cont`, carrying the full recovery identity (lines 2597–2603).
4. **Only then record deferred-application state** — ONLY on `r = scheduled(...)` does
   it store `recovery_decisions[decision_id].continuation_event_ref <- r.event_ref` and
   RETURN `recovery_branch_result(kind = DEFERRED, ...)` (lines 2604–2609). A REJECTED
   seat records `recovery_continuation_not_seated` and RETURNS `kind = FAILED, reason =
   continuation_not_seated` (lines 2610–2612).

Consequently a seat failure or `t_cont > T` leaves `round_state = SECURITY_RECOVERY`,
`current_recovery_episode` set, decision status `APPLY_FAILED` (seat rejected) or
`HORIZON_DEFERRED` (target beyond `T`), and NO continuation pending — because
`continuation_event_ref` is stored ONLY on a successful seat (line 2608). The
`ASSIGNMENT` transition is not performed here at all; it happens INSIDE the continuation
(S3, line 2588).

## 3. S3 — seating is not applying; the seven-step continuation is the only place branch-C RESTORED is applied

On a `DEFERRED` disposition the caller leaves the decision `APPLYING`,
`recovery_outcome_finalised` unset, `current_recovery_episode` uncleared, and the
decision persistently in `pending_recovery_decisions` (§0.8 lines 632–635) so a newer
final census can still supersede it. `CompleteSecurityRecovery` therefore returns
DEFERRED, not SUCCESS. The continuation carries `RecoveryEpisodeID`,
`RecoveryDecisionID`, `RecoveryOutcome`, the bound `RecoveryCensusVersion`,
`RoundID_at_decision`, `TemplateID_at_decision`, and `state_version_at_decision` (§10a
lines 2599–2602, 2623–2624). At its later `event_time`,
`RecoveryAssignmentContinuationEvent` (`PROCEDURE` at line 2622) runs seven steps:

1. **Verify episode + APPLYING decision still current** (lines 2631–2641) — `round_state
   = SECURITY_RECOVERY`, `current_recovery_episode = episode`, `RecoveryDecisionID in
   pending`, `D.status = APPLYING`, `recovery_outcome_finalised` unset, and the
   round/template/state-version bindings match; else `recovery_continuation_stale_noop`,
   NO mutation.
2. **Verify round still `SECURITY_RECOVERY`** — the `round_state != SECURITY_RECOVERY`
   disjunct of the same guard (line 2634); a closed/transitioned round is a stale no-op.
3. **Prepare + validate the disjoint assignment plan** (lines 2642–2652) — deterministic
   under the committed `TemplateID` (I1/I10 disjoint; no new template). If the plan is
   not valid: `SetRecoveryDecisionStatus(... APPLY_FAILED)`, remove from `pending`,
   record `recovery_continuation_plan_invalid`, RETURN `recovery_continuation_failed` —
   a failure BEFORE any state mutation; round STAYS `SECURITY_RECOVERY`, episode PRESERVED.
4. **Transition `SECURITY_RECOVERY -> ASSIGNMENT`** (lines 2654–2655) — bumps
   `state_version` (G10). This is the first state mutation; failures after it take the
   declared rollback path (step 5).
5. **Install the valid disjoint set** (lines 2656–2661) — activate reserves via
   `ReserveActivate` and reassign accepted-unsearched suffixes via the ordinary named
   procedures. If the install did NOT produce a valid disjoint CURRENT-or-PENDING
   assignment set (lines 2662–2671): `APPLY_FAILED`, remove from `pending`, set
   `recovery_outcome_finalised[episode] <- UNRECOVERABLE`, clear
   `current_recovery_episode`, and take the DECLARED recovery-finalising
   `RoundAbort(reason = recovery_assignment_install_failed, recovery_finalising = true)`
   — so the round NEVER lingers in `ASSIGNMENT` with an active episode and no live
   continuation; RETURN `recovery_continuation_aborted`.
6. **Run `CompleteAssignmentPhase` -> `HASHING`** (lines 2672–2674) — the SOLE
   `ASSIGNMENT -> HASHING` owner (L2/M2 census); `ASSERT round_state = HASHING`.
7. **Only after HASHING: mark APPLIED + finalise RESTORED** (lines 2675–2681) —
   `SetRecoveryDecisionStatus(... APPLIED)`, `recovery_outcome_finalised[episode] <-
   RESTORED`, remove from `pending`, clear `current_recovery_episode`; RETURN
   `recovery_continuation_completed`. This is the moment branch-C `RESTORED` is actually
   applied — seating (§2) did NOT apply it (§10a NOTE lines 2684–2685).

## 4. Acceptance-concern → procedure/step map

| Acceptance concern | Where enforced |
|---|---|
| Branch C does not mutate `round_state` before seating the continuation | `CompleteSecurityRecovery` branch C, order (1)–(4): compute `t_cont` → validate `<= T` → seat → record deferred state (§10a lines 2586–2609); no `TransitionRoundState` in the branch |
| Seat failure / `t_cont > T` leaves `SECURITY_RECOVERY`, episode set, `APPLY_FAILED`/`HORIZON_DEFERRED`, no continuation pending | `CompleteSecurityRecovery` lines 2590–2592 (horizon) and 2610–2612 (seat reject); caller lines 2521–2531; `continuation_event_ref` stored only on success (line 2608) |
| Seating is NOT applying: decision stays `APPLYING`, `recovery_outcome_finalised` not set, episode not cleared, returns `DEFERRED` not `SUCCESS` | Caller `DEFERRED` arm `ApplyRecoveryCompletionAfterEpilogue` lines 2514–2520; branch C returns `kind = DEFERRED` (line 2609) |
| APPLIED only at `HASHING` (or a declared terminal disposition) — never on a mere seat | `RecoveryAssignmentContinuationEvent` step 7 lines 2675–2681 (`HASHING` → `APPLIED`/`RESTORED`); step 5 lines 2665–2671 (declared abort → `UNRECOVERABLE`) |
| Failure BEFORE the transition → `APPLY_FAILED`, stay `SECURITY_RECOVERY`, preserve episode | `RecoveryAssignmentContinuationEvent` step 3 lines 2646–2652 |
| No `ASSIGNMENT` with an active episode and no live continuation (failure AFTER a state mutation → declared recovery-finalising `RoundAbort`) | `RecoveryAssignmentContinuationEvent` step 5 lines 2662–2671 (`recovery_finalising = true`); S4 invariant §0.8 lines 661–663 |
| Continuation carries the full recovery identity (episode/decision/outcome/census-version/round/template/state-version) | Seat payload §10a lines 2599–2602; handler `INPUTS` lines 2623–2624 |

## 5. Result

Under S2, branch C of `CompleteSecurityRecovery` (§10a) performs no `round_state`
mutation before its `RecoveryAssignmentContinuationEvent` is seated: it computes
`t_cont`, validates `t_cont <= T`, seats exactly one continuation through the S7
`PostEpilogueSchedulingContext`, and only then records the deferred-application state —
so a horizon-deferred target or a rejected seat leaves the round in `SECURITY_RECOVERY`
with the episode preserved, the decision `HORIZON_DEFERRED` or `APPLY_FAILED`, and no
continuation pending. Under S3, seating is not applying `RESTORED`: the branch returns
`DEFERRED`, the decision remains `APPLYING`, `recovery_outcome_finalised` is unset, and
`current_recovery_episode` is uncleared until the seated continuation verifies it is
still current, prepares and validates the disjoint plan, transitions
`SECURITY_RECOVERY -> ASSIGNMENT`, installs the valid disjoint set, reaches `HASHING`
via `CompleteAssignmentPhase`, and only THEN marks `APPLIED` and finalises `RESTORED`; a
failure before the transition stays `SECURITY_RECOVERY` with the episode preserved, and
a failure after a state mutation takes the declared recovery-finalising `RoundAbort`, so
the round never lingers in `ASSIGNMENT` with an active episode and no live continuation.
Both corrections operate purely on the deferred branch-C ordering and atomicity; the A1
accepted baseline of 8.420833333 kWh is unchanged, and no new consensus feature is
introduced.

The prohibited rebranded-algorithm-name variants are not used anywhere in this document.
