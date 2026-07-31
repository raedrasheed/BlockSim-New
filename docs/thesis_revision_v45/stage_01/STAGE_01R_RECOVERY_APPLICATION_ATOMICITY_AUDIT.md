# Stage 1R — Recovery-Application Atomicity and Decision-Mirror Consistency Audit (R4/R6)

This is a documentation-only paper audit of two Stage-1R corrections as edited in
`docs/thesis_revision_v45/stage_01/STAGE_01_PROTOCOL_PSEUDOCODE.md`: **R4 — atomic
recovery application** (a decision is never marked `APPLIED` and the episode is never
cleared before its R13/R14 branch succeeds) and **R6 — keep the decision mirrors
consistent** (`latest_recovery_decision` follows every status transition through the
sole mutator). The consensus specification is named **PoCol**; **the idle policy
within PoCol** is referenced here as a mechanism only, and this audit claims no
energy, security, or fairness property of the idle policy within PoCol. R4 and R6 are atomicity and
consistency corrections to the recovery-decision lifecycle; they never change how
time or energy is counted. The **A1 accepted accounting baseline of 8.420833333 kWh
is UNCHANGED** — no census value, residency interval, transition-energy term, or
accounting quantity is edited. Every claim below is checked against the pseudocode
as edited; no behavior is inferred beyond the text.

## 1. R4 — Atomic recovery application

The registries and the enum are §0.8. `recovery_decisions` (lines 595–600) carries
`status in RECOVERY_DECISION_STATUS`, extended by R4 to
`{CREATED, SCHEDULED, SUPERSEDED, APPLYING, APPLIED, SCHEDULE_FAILED, APPLY_FAILED,
CANCELLED}` (lines 618–619; `APPLYING` + `APPLY_FAILED` added for atomic
application). `recovery_outcome_finalised[episode]` is set ONCE, only when a decision
is `APPLIED` (lines 613–614), and `current_recovery_episode` is the active episode
that R4 must not clear prematurely.

### 1.1 State-transition walk

A decision minted by `SeatRecoveryCompletion` (§9) begins **CREATED** (line 2175),
moves to **SCHEDULED** on scheduler success (line 2192), and is applied ATOMICALLY
by `ApplyRecoveryCompletionAfterEpilogue` (§10a, lines 2367–2433) in the canonical
R4 order:

1. **VERIFY** (§10a lines 2390–2396) — the decision is applied ONLY if `round_state
   = SECURITY_RECOVERY`, `episode = current_recovery_episode` (lines 2383–2384), the
   decision is `SCHEDULED` and due at `t` (`due_at_event_time = t`, line 2388), its
   `bound_census_version` equals the LATEST `latest_recovery_census[episode]`
   version (re-affirmed, not superseded — line 2394), the outcome still matches the
   FINAL census (`outcome_consistent_with_census`, line 2395), and the round is
   nonterminal.
2. **APPLYING** (§10a lines 2401–2403) — the status is set atomically to `APPLYING`
   via `SetRecoveryDecisionStatus`; the episode is NOT finalised and
   `current_recovery_episode` is NOT cleared yet.
3. **EXECUTE** (§10a lines 2404–2405) — `CompleteSecurityRecovery` (§10a lines
   2435–2490) runs the R13/R14 branch and returns an EXPLICIT
   `recovery_branch_result(success, target | reason)`.
4. **APPLIED — success only** (§10a lines 2406–2413) — ONLY after a successful round
   transition or successful `RoundAbort` does the caller set `APPLIED`,
   `recovery_outcome_finalised[episode] <- D.outcome`, remove the decision from
   `pending_recovery_decisions`, and clear `current_recovery_episode <- null`.
5. **APPLY_FAILED — failure branch** (§10a lines 2414–2421) — on a branch failure
   the decision is NOT marked `APPLIED`; it is recorded `APPLY_FAILED`, the episode
   is PRESERVED (`current_recovery_episode` NOT cleared,
   `recovery_outcome_finalised` NOT set), and the decision is left out of pending so
   a later epilogue may re-seat if the outcome is still warranted.

A stale/superseded decision at the VERIFY gate (§10a lines 2393–2400) is set
`SUPERSEDED` and removed, recording `recovery_apply_stale_noop` — a `RESTORED`
decision therefore can never leave recovery under a breach census.

### 1.2 Outcome → decision status → episode disposition

| `ApplyRecoveryCompletionAfterEpilogue` outcome | Decision status | Episode |
|---|---|---|
| `recovery_applied` (branch success, §10a 2406–2413) | `APPLIED` | CLEARED (`current_recovery_episode <- null`; outcome finalised) |
| `recovery_apply_failed` (branch failure, §10a 2414–2421) | `APPLY_FAILED` | PRESERVED (active episode not cleared, not finalised) |
| `recovery_apply_stale_noop` (VERIFY fails, §10a 2393–2400) | `SUPERSEDED` | PRESERVED (removed from pending; never applied under a contradicting census) |
| `terminal_recovery_noop` (terminal/horizon guard, §10a 2372–2382) | `CANCELLED` (every pending decision) | Round already terminal; nothing applied, nothing finalised |
| `nothing_due` / `nothing_applicable_due` (§10a 2383–2385, 2422) | unchanged | unchanged (no episode or no due decision) |

The episode is cleared on exactly ONE path — a successful branch — so a
half-applied outcome can never strand the episode (§10a NOTE lines 2425–2433).

### 1.3 `CompleteSecurityRecovery` — explicit per-branch dispositions

`CompleteSecurityRecovery` (§10a lines 2435–2490) is an INTERNAL branch dispatch
called ONLY by `ApplyRecoveryCompletionAfterEpilogue` after the decision is
`APPLYING`. Every branch returns an EXPLICIT `recovery_branch_result` (lines
2440–2442):

- **(A) SOLUTION_PROPAGATION** (RESTORED, live propagation contexts, §10a lines
  2450–2458) — `TransitionRoundState(... SOLUTION_PROPAGATION ...)` with contexts and
  events preserved (G8); `success = true, target = SOLUTION_PROPAGATION` on a
  confirmed transition, else `success = false, reason = transition_failed`.
- **(B) HASHING** (RESTORED, coverage restored, no redistribution, §10a lines
  2459–2464) — `TransitionRoundState(... HASHING ...)`; `success = true, target =
  HASHING`, else `transition_failed`.
- **(C) ASSIGNMENT_CONTINUATION_SEATED** (RESTORED, redistribution/reserve needed,
  §10a lines 2465–2482) — transitions to `ASSIGNMENT` and seats ONE
  `RecoveryAssignmentContinuationEvent` at `next_representable_simulation_time(t)`
  (R1: nothing enqueued at `t`); `success = true, target =
  ASSIGNMENT_CONTINUATION_SEATED` on scheduler success, else `success = false, reason
  = continuation_not_seated`.
- **(D) ROUND_ABORTED** (UNRECOVERABLE, §10a lines 2443–2448) —
  `RoundAbort(reason = floor_unrecoverable)`, round only (N1); `success = true, target
  = ROUND_ABORTED` when `round_state = ROUND_ABORTED`, else `success = false, reason =
  abort_did_not_terminate`. The caller marks `APPLIED` only on the `success = true`
  disposition, so a failed abort would leave `APPLY_FAILED` and preserve the episode.

### 1.4 Horizon — `terminal_recovery_noop`

`CloseRoundAtHorizon` (§20b lines 3598–3646) is the run-level hook that
`ProcessEventTime(T)` interposes between the `T` drain and the `T` epilogue when the
round is nonterminal; it transitions `round_state -> ROUND_ABORTED` with the distinct
horizon-end disposition (lines 3627–3628). Because the round is terminal by the time
the post-epilogue apply runs, the R4 TERMINAL/HORIZON GUARD in
`ApplyRecoveryCompletionAfterEpilogue` (§10a lines 2372–2382), checked FIRST, fires:
for `round_state in {ROUND_ACCEPTED, ROUND_ABORTED}` it CANCELS every pending
decision of the (now stale) episode via `SetRecoveryDecisionStatus(... CANCELLED)`
(line 2380), empties `pending_recovery_decisions[episode]` (line 2381), and returns
`terminal_recovery_noop` (line 2382). NO decision is ever marked `APPLIED` after
horizon closure (gate 8), and no round-state transition is fabricated post-horizon.

## 2. R6 — Keep decision mirrors consistent

`latest_recovery_decision[episode]` is a MUTABLE MIRROR of the most-recent decision
(§0.8 lines 608–612). Under R6 it is kept ATOMICALLY consistent by the SOLE status
mutator `SetRecoveryDecisionStatus` (§9 lines 2090–2110): whenever the mirror points
at the decision being transitioned, the whole mirror record is refreshed from
`recovery_decisions` (lines 2101–2105), so its status can NEVER lag — it can never
remain `CREATED` after the decision became `CANCELLED`, `SCHEDULE_FAILED`,
`SUPERSEDED`, `APPLYING`, `APPLIED`, or `APPLY_FAILED`. `CREATED` is written only at
creation in `SeatRecoveryCompletion` (which also creates the mirror, line 2176);
every SUBSEQUENT transition routes through the helper.

| Status-mutation site | Procedure (section) | Transition via `SetRecoveryDecisionStatus` |
|---|---|---|
| Horizon-defer at seating | `SeatRecoveryCompletion` (§9, line 2180) | `CANCELLED` — mirror refreshed, never left `CREATED` |
| Scheduler success | `SeatRecoveryCompletion` (§9, line 2192) | `SCHEDULED` |
| Scheduler reject | `SeatRecoveryCompletion` (§9, line 2199) | `SCHEDULE_FAILED` — never left `CREATED` |
| Newer census contradicts pending | `ReconcilePendingRecoveryDecisions` (§9, line 2138) | `SUPERSEDED` |
| Atomic apply, step 2 | `ApplyRecoveryCompletionAfterEpilogue` (§10a, line 2403) | `APPLYING` |
| Branch success | `ApplyRecoveryCompletionAfterEpilogue` (§10a, line 2409) | `APPLIED` |
| VERIFY fails (stale) | `ApplyRecoveryCompletionAfterEpilogue` (§10a, line 2397) | `SUPERSEDED` |
| Branch failure | `ApplyRecoveryCompletionAfterEpilogue` (§10a, line 2418) | `APPLY_FAILED` |
| Terminal/horizon guard | `ApplyRecoveryCompletionAfterEpilogue` (§10a, line 2380) | `CANCELLED` |

Every status write after the initial `CREATED` routes through
`SetRecoveryDecisionStatus`; no procedure assigns `recovery_decisions[...].status`
directly except that sole mutator and the creation site. The re-affirm path in
`ReconcilePendingRecoveryDecisions` (§9 lines 2143–2146) updates only
`bound_census_version` and explicitly mirrors it too. Consequently a
`latest_recovery_decision` record can NEVER remain `CREATED` after the underlying
decision became `CANCELLED` or `SCHEDULE_FAILED` (§0.8 lines 610–612; §9 NOTE lines
2107–2110), and the mirror status never lags the decision through any of the eight
status-change sites above.

## 3. Result

Under R4, `ApplyRecoveryCompletionAfterEpilogue` (§10a) is the ONLY site that
finalises a recovery outcome, and it does so atomically: VERIFY → `APPLYING` →
execute `CompleteSecurityRecovery` (which returns an explicit success/failure
disposition for each of branches A/B/C/D) → `APPLIED` with the episode cleared ONLY
on branch success; a branch failure yields `APPLY_FAILED` with the episode
preserved, a stale decision yields `SUPERSEDED`, and a terminal/horizon round yields
`terminal_recovery_noop` with every pending decision `CANCELLED` and none applied.
Under R6, the sole mutator `SetRecoveryDecisionStatus` (§9) is invoked on every
status transition and refreshes `latest_recovery_decision` whenever it points at the
mutated decision, so the mirror is always consistent with `recovery_decisions`. Both
corrections operate purely on the decision lifecycle and status bookkeeping; the A1
accepted baseline of 8.420833333 kWh is unchanged, and no new consensus feature is
introduced.

The prohibited rebranded-algorithm-name variants are not used anywhere in this document.
