# Stage 1S — Terminal Recovery Cleanup Audit (S4)

This is a documentation-only paper audit of Stage-1S correction **S4 — terminal recovery
cleanup** as edited in `docs/thesis_revision_v45/stage_01/STAGE_01_PROTOCOL_PSEUDOCODE.md`.
S4 closes one gap: when a round becomes terminal (`ROUND_ACCEPTED` or `ROUND_ABORTED`)
while a recovery episode is still active and its outcome has NOT been applied, the single
closure path must cancel that episode's every pending/scheduled/applying decision, cancel
its still-queued recovery-timeline events, record `recovery_episode_disposition =
TERMINAL_CANCELLED`, and clear `current_recovery_episode` — so a terminal round NEVER
leaves an active recovery episode. The consensus specification is named **PoCol**;
**the idle policy within PoCol** is referenced only as a mechanism, and this audit
claims no energy, security, or fairness property of it. S4 is a lifecycle-cleanup correction to the
recovery-episode registries; it changes no census value, residency interval, or
transition-energy term, so the **A1 accepted accounting baseline of 8.420833333 kWh is
UNCHANGED**. No new consensus feature is introduced; every claim below is checked against
the pseudocode as edited.

## 1. §0.8 registries the correction touches

- `current_recovery_episode` (§0.8 lines 605–607): the `RecoveryEpisodeID` of the active
  episode while `round_state = SECURITY_RECOVERY`; null otherwise. Cleared when the episode
  is finalised (an applied outcome) OR when S4 cancels an unfinished episode.
- `recovery_decisions[...].continuation_event_ref` (§0.8 lines 622–631): the seated
  `RecoveryAssignmentContinuationEvent` of a DEFERRED branch-C decision, stored so
  `CancelActiveRecoveryEpisode` can cancel it on terminal closure (line 630–631).
- `pending_recovery_decisions[episode]` (§0.8 lines 632–638): the set of `{CREATED,
  SCHEDULED}` (or transiently/persistently `APPLYING`) decisions S4 must drain.
- `recovery_outcome_finalised[episode]` (§0.8 lines 644–648): set ONCE, only when an
  outcome is actually APPLIED. Explicitly "NOT set by a TERMINAL_CANCELLED cleanup (S4 —
  no outcome was applied there)" (line 648).
- `recovery_episode_disposition[episode]` (§0.8 lines 649–653): S4's new map,
  `RecoveryEpisodeID -> RECOVERY_EPISODE_DISPOSITION` (enum with the single member
  `TERMINAL_CANCELLED`, §0.8 line 656), recording how an episode ENDED without an applied
  outcome: `TERMINAL_CANCELLED` when the round became terminal while the episode was still
  active. Null while active or when an outcome was applied.
- **S4 INVARIANT** (§0.8 lines 661–663): `current_recovery_episode != null` IFF
  `round_state = SECURITY_RECOVERY` — "a branch-C DEFERRED decision keeps the round in
  SECURITY_RECOVERY until its continuation begins, so the invariant stays simple."

## 2. §9 `CancelActiveRecoveryEpisode` — the terminal cleanup

`CancelActiveRecoveryEpisode` (§9 lines 2161–2188) is called ONLY by `CloseRoundAssignments`
when the round is closing and `current_recovery_episode != null` and the closure is NOT the
recovery-finalising abort (`recovery_finalising = false`) — "NO outcome is being applied
here" (precondition, lines 2163–2165). Its effects, in order:

1. For each `decision_id` in `pending_recovery_decisions[episode]` (stable order by
   `decision_id`, line 2170): if `due_event_ref` is still pending on EQ, CANCEL the queued
   `RecoveryCompletionDueEvent` (lines 2172–2173); if `continuation_event_ref` is still
   pending, CANCEL the queued `RecoveryAssignmentContinuationEvent` (lines 2174–2175);
   then `SetRecoveryDecisionStatus(... CANCELLED)` (line 2176), which keeps the R6 mirror
   consistent.
2. Empty `pending_recovery_decisions[episode]` (line 2177), record
   `recovery_episode_disposition[episode] <- TERMINAL_CANCELLED` (line 2180), and set
   `current_recovery_episode <- null` (line 2181).

It does NOT set `recovery_outcome_finalised` (lines 2178–2179, 2188) — that map is reserved
for an actually-applied RESTORED/UNRECOVERABLE outcome. The NOTE (lines 2183–2188) states
the guarantee: a terminal round NEVER leaves an active recovery episode.

## 3. §17a `CloseRoundAssignments` — the S4 gate and event cancellation

`CloseRoundAssignments` (§17a lines 3414–3510) is the SINGLE round-closure path. S4 adds
the `recovery_finalising = false` input (lines 3416–3417) — "true ONLY when this closure IS
the recovery-finalising abort … then S4 cleanup is SKIPPED." Two S4 edits appear in its body:

- The pending-event cancellation now includes the recovery timeline: `RecoveryDeadlineEvent
  / RecoveryCompletionDueEvent / RecoveryAssignmentContinuationEvent` are cancelled for the
  closing `RoundID` (lines 3480–3484).
- The terminal cleanup gate (lines 3487–3492):
  `IF current_recovery_episode != null AND NOT recovery_finalising: CALL
  CancelActiveRecoveryEpisode(RoundContext, dispatch_envelope)`.

So an unfinished episode is cancelled on every terminal closure EXCEPT the finalising abort.

## 4. §20 `RoundAbort` and the `recovery_finalising` flag

`RoundAbort` (§20 lines 3671–3702) gains `recovery_finalising = false` (line 3672) and
threads it verbatim into `CloseRoundAssignments` (lines 3700–3702). The comment (lines
3673–3676) fixes the contract: `true` ONLY when the abort IS the application of a recovery
outcome (branch D `floor_unrecoverable`, or the continuation's declared install-fail abort);
"All OTHER aborts use the default false, so an unfinished episode is cancelled."

The two finalising callers pass `true` explicitly:

- **§10a `CompleteSecurityRecovery` branch D** (lines 2558–2566): the UNRECOVERABLE outcome
  aborts the round via `RoundAbort(reason = floor_unrecoverable, recovery_finalising = true)`
  (lines 2562–2563). This abort IS the outcome application, so S4 cleanup is skipped and the
  caller (`ApplyRecoveryCompletionAfterEpilogue`) finalises the episode (APPLIED,
  `recovery_outcome_finalised <- UNRECOVERABLE`).
- **`RecoveryAssignmentContinuationEvent` declared install-fail abort** (lines 2662–2671):
  after a state mutation, a failed install sets `recovery_outcome_finalised[episode] <-
  UNRECOVERABLE` and `current_recovery_episode <- null` (lines 2667–2668) THEN calls
  `RoundAbort(reason = recovery_assignment_install_failed, recovery_finalising = true)`
  (lines 2669–2670). The episode is already finalised, so S4 cleanup is correctly skipped.

### 4.1 Closure path → `recovery_finalising` → cleanup → disposition

| Closure path | `recovery_finalising` | S4 cleanup fires? | Resulting episode disposition |
|---|---|---|---|
| `ValidBlockAccept` → ROUND_ACCEPTED (§17a call, line 3401) | `false` (default, omitted) | YES, if episode active | `TERMINAL_CANCELLED`; `recovery_outcome_finalised` NOT set |
| `CloseRoundAtHorizon` → ROUND_ABORTED (§20b, line 3802) | `false` (default, omitted) | YES, if episode active | `TERMINAL_CANCELLED`; `recovery_outcome_finalised` NOT set |
| Ordinary `RoundAbort` (§20, default arg) | `false` (default) | YES, if episode active | `TERMINAL_CANCELLED`; `recovery_outcome_finalised` NOT set |
| Branch-D finalising `RoundAbort(floor_unrecoverable)` (§10a, line 2562) | `true` | NO (skipped) | Finalised by caller: `recovery_outcome_finalised = UNRECOVERABLE` |
| Continuation install-fail `RoundAbort` (line 2669) | `true` | NO (skipped) | Finalised by continuation: `recovery_outcome_finalised = UNRECOVERABLE` |

In every `false` row the episode was still active with no applied outcome, so cancellation
records `TERMINAL_CANCELLED`; in every `true` row the caller has already written
`recovery_outcome_finalised`, so no disposition is recorded and cancellation would be wrong.

## 5. The IFF invariant holds at every event boundary

`current_recovery_episode != null` IFF `round_state = SECURITY_RECOVERY` (§0.8 lines
661–663). On **entry to SECURITY_RECOVERY** both sides become true together (§0.8 lines
606–607). Checking each boundary where either side can subsequently change:

- **Branch A/B success** (§10a lines 2568–2582): `TransitionRoundState` leaves
  SECURITY_RECOVERY and the caller clears `current_recovery_episode`, both inside ONE
  synchronous post-epilogue application. Both sides become false together; no event boundary
  falls between them.
- **Branch C DEFERRED** (§10a lines 2583–2609): the round REMAINS SECURITY_RECOVERY and the
  episode stays active until the continuation begins — both sides stay true across the seat
  and the wait. This is exactly the case the §0.8 note keeps simple.
- **Continuation reaches HASHING** (lines 2653–2679): SECURITY_RECOVERY → ASSIGNMENT →
  HASHING and, only after HASHING, `current_recovery_episode <- null` — all within the one
  continuation handler. The transient ASSIGNMENT-with-active-episode window never spans an
  event boundary (lines 2402–2403: "the round never lingers in ASSIGNMENT with an active
  episode and no live continuation").
- **Terminal closure with an active, unfinished episode**: `round_state` → terminal (RHS
  false) and, in the SAME closure, S4 clears `current_recovery_episode` (LHS false). S4 is
  precisely what preserves the invariant here — without it the LHS would remain non-null
  after the RHS went terminal.
- **Recovery-finalising abort**: the caller/continuation clears `current_recovery_episode`
  (LHS false) and the round becomes ROUND_ABORTED (RHS false); S4 cleanup is skipped because
  the episode is already finalised. Consistent.

Every transient window in which the two sides disagree lies strictly inside one synchronous
handler; at every quiescent event boundary the IFF holds.

## 6. Result

Under S4, `CloseRoundAssignments` (§17a) is the SINGLE closure path, and it invokes the new
`CancelActiveRecoveryEpisode` (§9) exactly when `current_recovery_episode != null AND NOT
recovery_finalising`: it cancels every pending/scheduled/applying decision and the episode's
still-queued `RecoveryCompletionDueEvent` / `RecoveryAssignmentContinuationEvent`, records
`recovery_episode_disposition = TERMINAL_CANCELLED`, and clears `current_recovery_episode` —
WITHOUT setting `recovery_outcome_finalised`, because no outcome was applied. The
`recovery_finalising` flag defaults false on `ValidBlockAccept` ROUND_ACCEPTED,
`CloseRoundAtHorizon`, and ordinary `RoundAbort` (so an unfinished episode is always cancelled
there), and is true only on the branch-D `floor_unrecoverable` abort and the continuation's
declared install-fail abort (where the caller finalises the episode and S4 cleanup is skipped).
Consequently `current_recovery_episode != null` IFF `round_state = SECURITY_RECOVERY` holds at
every event boundary, and a terminal round never leaves an active recovery episode. S4 is a
lifecycle-cleanup correction to the recovery-episode registries only; the A1 accepted baseline
of 8.420833333 kWh is unchanged, and no new consensus feature is introduced.

The prohibited rebranded-algorithm-name variants are not used anywhere in this document.
