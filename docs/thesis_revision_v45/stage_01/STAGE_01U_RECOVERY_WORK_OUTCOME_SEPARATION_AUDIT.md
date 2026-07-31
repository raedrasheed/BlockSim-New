# Stage 1U — Recovery WORK / Outcome Separation Audit (U1 — recovery WORK is not the RESTORED outcome)

This is a documentation-only paper audit of the Stage-1U correction **U1 — separate recovery
WORK from the RESTORED outcome** as edited in
`docs/thesis_revision_v45/stage_01/STAGE_01_PROTOCOL_PSEUDOCODE.md`. U1 splits two things that
Stage 1T had entangled: (A) the recovery **OUTCOME** decision (`RESTORED` / `UNRECOVERABLE`,
decided ONLY from a FINAL census), and (B) the recovery **WORK** action
(`RESERVE_ACTIVATION_REQUIRED` / `RANGE_REDISTRIBUTION_REQUIRED` / `NONE`, attempted WHILE the
floor is still breached). It establishes that the reserve-dependent `RESTORED` continuation
branch present in Stage 1T was LOGICALLY IMPOSSIBLE and has been REMOVED, and that a
recovery-work action is NEVER a `RecoveryOutcome` and is NEVER marked `APPLIED` as `RESTORED`.
The consensus algorithm is named **PoCol**; **the idle policy within PoCol** is referenced here
only as a named mechanism, and this audit claims no energy, security, or fairness property of the
idle policy within PoCol. U1 is a recovery-LIFECYCLE separation of a work action from an outcome
decision; it is NEVER a change to how time or energy is counted. The **A1 accepted accounting
baseline of 8.420833333 kWh is UNCHANGED** — no census value, residency interval,
transition-energy term, or accounting quantity is edited. This is documentation only: no new
consensus feature is introduced. Every claim below is checked against the pseudocode as edited; no
behaviour is inferred beyond the text.

## 1. Why the reserve-dependent `RESTORED` branch was logically impossible

`RESTORED` has exactly one warrant. `outcome_consistent_with_census` (§9 lines 2276–2281) states
it in one line: `IF outcome = RESTORED: RETURN (census.breach = false)` (§9 line 2279). This
FUNCTION is UNCHANGED by U1 — U1 does not weaken it. `RESTORED` is warranted by, and ONLY by, a
FINAL census that shows NO breach.

A recovery census is computed from the CURRENT `ACTIVE_HASHING` roster.
`CaptureSecurityCensusOnRecoveryDeadline` sets `H_honest(at) <- SUM over honest miners in
ACTIVE_HASHING` and `H_active(at) <- H_honest(at) + H_adversarial(at)` (§9 lines 2496–2498). A
reserve miner is NOT in `ACTIVE_HASHING` until it is activated: `ReserveActivate` ledgers the
reserve at PENDING and "Activation to CURRENT happens ONLY at the scheduled `WakeCompleteEvent` on
a successful wake" (§10 lines 2718–2719). A restoration that DEPENDS on reserve hash rate
therefore presupposes that the reserve has NOT yet woken — which means the current
`ACTIVE_HASHING` census does NOT yet include that hash rate, and, because that is exactly the
deficit motivating the reserve, the current census necessarily STILL breaches the floor.

The Stage-1T reserve-dependent `RESTORED` continuation ELSE thus required, at one and the same
census, BOTH `census.breach = false` (to satisfy `outcome_consistent_with_census(RESTORED,
census)`) AND `census.breach = true` (the very breach the reserve is meant to close). No census
can satisfy both, so the branch was unreachable — dead by contradiction. Removing it removes an
impossible arm, not a live one; `outcome_consistent_with_census(RESTORED)` is NOT weakened, and
its guard (§9 line 2279) is untouched.

## 2. The two axes U1 holds apart: (A) OUTCOME decision vs (B) WORK action

U1 records the separation in §0.8: "A recovery-WORK action (reserve activation / range
redistribution attempted WHILE the floor is still breached) is NEVER a `RecoveryOutcome` and is
NEVER marked `APPLIED` as `RESTORED`. `RESTORED` / `UNRECOVERABLE` are decided ONLY from a final
census (`outcome_consistent_with_census`, unchanged/not weakened)" (§0.8 lines 713–715).

| Axis | Values | Domain / registry | Decided by | Can be `APPLIED` / finalise an outcome? |
|---|---|---|---|---|
| (A) recovery OUTCOME | `RESTORED`, `UNRECOVERABLE` (`RECOVERY_OUTCOME`, §0.8 lines 693–694) | `recovery_outcome_finalised` (§0.8 lines 673–678) | a FINAL census via `outcome_consistent_with_census` (§9 lines 2276–2281) | YES — this is the outcome |
| (B) recovery WORK | `RESERVE_ACTIVATION_REQUIRED`, `RANGE_REDISTRIBUTION_REQUIRED`, `NONE` (`RECOVERY_WORK_ACTION`, §0.8 line 718) | `recovery_work` / `pending_recovery_work` / `recovery_work_seq` (§0.8 lines 719–729) | `ClassifyRecoveryWork` from a breach-before-deadline census (§9c lines 2519–2531) | NEVER — "is NEVER a `RecoveryDecisionID` and is NEVER `APPLIED`" (§0.8 line 725) |

A WORK action carries its own versioned identity `RecoveryWorkID = (RecoveryEpisodeID,
recovery_work_seq)` (§0.8 line 729) and its own status enum `RECOVERY_WORK_STATUS in {CREATED,
ARMED, DUE, CONSUMED, SUPERSEDED, CANCELLED, SCHEDULE_FAILED}` (§0.8 line 728) — none of which is a
`RECOVERY_DECISION_STATUS` and none of which is `APPLIED`. The two axes never touch:
`ClassifyRecoveryWork` "SELECTS a WORK action, NEVER a RecoveryOutcome" (§9c line 2522) and
"NEVER decides RESTORED/UNRECOVERABLE" (§9c line 2525).

## 3. The canonical flow: breach-before-deadline → WORK → later census → OUTCOME

The `SecurityFloorEvaluate` epilogue (§9 `PROCEDURE` line 2159) chooses the warranted outcome from
the FINAL recovery census while `round_state = SECURITY_RECOVERY` (§9 lines 2242–2244):

- `IF NOT census.breach: SET warranted <- RESTORED` (§9 line 2242);
- `ELSE IF census.breach AND census.deadline_reached: SET warranted <- UNRECOVERABLE` (§9 line 2243);
- `ELSE: SET warranted <- NONE` (§9 line 2244) — a breach BEFORE the deadline.

The `warranted = NONE` branch (§9 lines 2245–2254) is the U1 hinge. Its comment is exact: "a
breach BEFORE the deadline is NOT a RecoveryOutcome. It is the trigger to attempt recovery WORK.
`outcome_consistent_with_census(RESTORED)` is NOT weakened (a breached census can never justify
RESTORED)" (§9 lines 2246–2247). The canonical sequence is then:

1. **Classify.** `SET work_action <- CALL ClassifyRecoveryWork(RoundContext, episode, census)` (§9
   line 2251) returns a `RECOVERY_WORK_ACTION` (§9c lines 2519–2531) — compute-only, "NEVER
   mutates state" (§9c line 2525).
2. **Seat ONE.** `IF work_action != NONE: RETURN CALL SeatRecoveryWork(...)` (§9 lines 2252–2253);
   otherwise `RETURN recovery_pending(census.RecoveryCensusVersion)` — "keep waiting" (§9 line
   2254). `SeatRecoveryWork` (§9c `PROCEDURE` line 2537) seats exactly ONE versioned
   `RecoveryWorkDueEvent` under the U3 ATOMIC protocol: it is idempotent (at most one in-flight
   `RecoveryWorkID`, guarded by `pending_recovery_work[episode]`, §9c lines 2547–2550), publishes
   `recovery_work_seq` / the `work_record` / `pending_recovery_work` ONLY after `ScheduleEvent`
   succeeds (§9c lines 2565–2573), and horizon-defers rather than seat beyond `T` (§9c lines
   2556–2558). It "never marks a decision `APPLIED`" (§9c line 2585).
3. **Record the DUE fact.** The queued `RecoveryWorkDueEvent` (§13e line 515; §9c `PROCEDURE` line
   2589) records `status <- DUE` / `due_status <- DUE` and refreshes the census, "NO reserve
   activation, NO transition, and NO APPLIED (the WORK is the post-epilogue hook)" (§9c lines
   2597–2598).
4. **Do the WORK, post-epilogue.** `ApplyRecoveryWorkAfterEpilogue` (§9c `PROCEDURE` line 2623),
   invoked by `ProcessEventTime` AFTER `FinalizeEventTimeSecurityCensus(t)`,
   `ApplyRecoveryCompletionAfterEpilogue(t)`, and `ApplyRecoveryAssignmentContinuationAfterEpilogue(t)`
   (§9c lines 2625–2626; canonical tail §7 lines 265–268), performs the work ONLY while "the census
   still shows a breach before the deadline" (§9c lines 2635–2640) via the named U5 plan procedures
   `PrepareRecoveryAssignmentPlan` / `CommitRecoveryAssignmentPlan` / `RollbackRecoveryAssignmentPlan`.
   On `install_committed` the reserve wakes / redistribution heads are seated STRICTLY LATER (U2)
   and "The round STAYS `SECURITY_RECOVERY`; NOTHING is marked `RESTORED`" (§9c lines 2677–2683). It
   "NEVER marks a decision `APPLIED` and NEVER sets `recovery_outcome_finalised`" (§9c lines
   2626–2627, 2690).
5. **A LATER final census decides.** "A later `WakeCompleteEvent` raises `H_honest`, and a later
   final census with NO breach mints `RESTORED`" (§9c lines 2678–2679). At that later event_time
   the epilogue re-runs (§9 lines 2242–2244): no breach → `RESTORED`; breach WITH deadline →
   `UNRECOVERABLE`; breach BEFORE deadline → continue (re-classify WORK). The round STAYS
   `SECURITY_RECOVERY` throughout the work; the OUTCOME is deferred to whichever final census
   settles it.

Thus (B) WORK runs while breached and mutates only assignment/reserve state; (A) OUTCOME is minted
only later, only by a census, and only through the ordinary completion/continuation two-step.

## 4. The continuation is now REDISTRIBUTION-ONLY; the reserve-dependent ELSE is REMOVED

`ApplyRecoveryAssignmentContinuationAfterEpilogue` (§10a `PROCEDURE` line 3040) is "the ONLY place
branch-C `RESTORED` is APPLIED." Its precondition is now explicit: "the continuation is
REDISTRIBUTION-ONLY — its FINAL census shows NO breach, so the floor is already met by currently
`ACTIVE_HASHING` miners and the install only re-partitions disjoint ranges; it NEVER depends on
future reserve hash rate (reserve activation while the floor is still breached is recovery WORK,
§9c, not a continuation)" (§10a lines 3045–3048). Its freshness guard re-checks the census: it
applies only when `outcome_consistent_with_census(RESTORED, census)` holds (§10a line 3067), i.e.
`census.breach = false`. The install passes `RANGE_REDISTRIBUTION_REQUIRED` to
`PrepareRecoveryAssignmentPlan` (§10a line 3076) — never `RESERVE_ACTIVATION_REQUIRED`.

The NOTE records the removal in terms: "the continuation is REDISTRIBUTION-ONLY (`census.breach =
false`) — it never depends on future reserve hash rate (reserve activation while breached is
recovery WORK, §9c; **the impossible reserve-dependent `RESTORED` ELSE is REMOVED**)" (§10a lines
3151–3153). The T3 episode invariant carries the same statement: "Reserve-dependent restoration is
NOT a branch-C continuation (U1): it is recovery WORK — the round stays `SECURITY_RECOVERY`
(reserve PENDING/WAKING) until a later final census with NO breach mints `RESTORED`" (§0.8 lines
709–711). Reading the edited body of the procedure (§10a lines 3049–3147) confirms there is no
reserve-activation ELSE arm: every exit is HASHING + `APPLIED`; `SECURITY_RECOVERY` +
`APPLY_FAILED` (rollback complete, episode preserved); or `ROUND_ABORTED` +
`RECOVERY_INSTALL_FAILED_ABORTED` (§10a lines 3159–3160).

## 5. A redistribution AFTER an already-restored census stays a `RESTORED` continuation only when it needs no future reserve hash rate

The two axes can touch at exactly one point, and U1 pins it precisely. `ClassifyRecoveryWork`'s
NOTE: "A `RANGE_REDISTRIBUTION_REQUIRED` that does NOT depend on future reserve hash rate is the
ONLY redistribution that could ALSO be applied as a `RESTORED` continuation once a no-breach census
exists (§10a); while the census still shows a breach, both classifications are WORK, never
`RESTORED`" (§9c lines 2532–2535). The distinguishing predicate is dependence on FUTURE reserve
hash rate, not the redistribution mechanics:

- WHILE breached (`census.breach = true`), a `RANGE_REDISTRIBUTION_REQUIRED` is WORK, seated by
  `SeatRecoveryWork` and run by `ApplyRecoveryWorkAfterEpilogue`, which leaves the round
  `SECURITY_RECOVERY` and sets no outcome (§9c lines 2677–2683).
- ONCE a no-breach final census exists (`census.breach = false`), a redistribution that closes the
  floor using only currently `ACTIVE_HASHING` miners — needing no reserve wake — is applied as the
  branch-C `RESTORED` continuation by `ApplyRecoveryAssignmentContinuationAfterEpilogue`, which
  reaches HASHING and `SET recovery_outcome_finalised[episode] <- RESTORED` "set ONLY on an
  actually-applied outcome" (§10a lines 3120–3124).

The redistribution stays a `RESTORED` continuation only in the second case, because only there is
the floor already met by active hash rate and the census already shows no breach. If restoration
depended on a reserve not yet woken, the census would still breach (§1), the continuation guard
`outcome_consistent_with_census(RESTORED, census)` would fail (§10a line 3067), and the action
would remain WORK.

## 6. `recovery_outcome_finalised` is written ONLY on an actually-applied outcome — never by WORK

`recovery_outcome_finalised` is "Set ONCE, ONLY when an outcome is ACTUALLY APPLIED: by
`ApplyRecoveryCompletionAfterEpilogue` (branches A/B/D), or by
`ApplyRecoveryAssignmentContinuationAfterEpilogue` when branch C reaches HASHING (`RESTORED`)"
(§0.8 lines 673–676). Those are the two — and only two — writers. `ApplyRecoveryWorkAfterEpilogue`
is NOT among them: its header and NOTE both state it "NEVER marks a decision `APPLIED` and NEVER
sets `recovery_outcome_finalised` — recovery WORK is not an outcome (U1)" (§9c lines 2626–2627),
"the round stays `SECURITY_RECOVERY` and `RESTORED` is decided ONLY by a later no-breach final
census (U1)" (§9c line 2690). Every terminating arm of `ApplyRecoveryWorkAfterEpilogue`
(§9c lines 2641–2683) clears `pending_recovery_work[episode]` and returns a `recovery_work_*`
disposition; none writes `recovery_outcome_finalised`.

## 7. PASS-check table (exact names)

| # | Check | Verdict | Evidence (exact names / lines) |
|---|---|---|---|
| 1 | `RESTORED` warrant UNCHANGED: requires `census.breach = false` | PASS | `outcome_consistent_with_census`: `IF outcome = RESTORED: RETURN (census.breach = false)` (§9 line 2279) |
| 2 | Reserve-dependent `RESTORED` continuation ELSE is REMOVED | PASS | NOTE "the impossible reserve-dependent `RESTORED` ELSE is REMOVED" (§10a line 3153); body has no reserve arm (§10a lines 3049–3147) |
| 3 | Continuation is REDISTRIBUTION-ONLY (`census.breach = false`) | PASS | precondition (§10a lines 3045–3048); guard `outcome_consistent_with_census(RESTORED, census)` (§10a line 3067); plan action `RANGE_REDISTRIBUTION_REQUIRED` (§10a line 3076) |
| 4 | A WORK action is a distinct `RECOVERY_WORK_ACTION`, never a `RecoveryOutcome` | PASS | `RECOVERY_WORK_ACTION in {RESERVE_ACTIVATION_REQUIRED, RANGE_REDISTRIBUTION_REQUIRED, NONE}` (§0.8 line 718); "NEVER a `RecoveryOutcome` ... NEVER marked `APPLIED` as `RESTORED`" (§0.8 lines 713–714) |
| 5 | Breach-before-deadline routes to WORK, not to an outcome | PASS | `warranted = NONE` → `ClassifyRecoveryWork` → `SeatRecoveryWork` (§9 lines 2244–2253) |
| 6 | `ClassifyRecoveryWork` selects WORK only, never an outcome | PASS | "SELECTS a WORK action, NEVER a RecoveryOutcome" (§9c line 2522); "NEVER decides RESTORED/UNRECOVERABLE" (§9c line 2525) |
| 7 | `SeatRecoveryWork` seats ONE versioned `RecoveryWorkDueEvent`; never `APPLIED` | PASS | atomic idempotent seat (§9c lines 2537–2573); "never marks a decision `APPLIED`" (§9c line 2585) |
| 8 | `RecoveryWorkDueEvent` records the DUE fact only; no activation / no transition / no `APPLIED` | PASS | §13e line 515; "NO reserve activation, NO transition, and NO APPLIED" (§9c lines 2597–2598) |
| 9 | `ApplyRecoveryWorkAfterEpilogue` performs WORK, keeps `SECURITY_RECOVERY`, sets no outcome | PASS | "The round STAYS `SECURITY_RECOVERY`; NOTHING is marked `RESTORED`" (§9c lines 2677–2683); "NEVER sets `recovery_outcome_finalised`" (§9c lines 2627, 2690) |
| 10 | OUTCOME is decided ONLY from a later final census | PASS | epilogue selection (§9 lines 2242–2244); "a later final census with NO breach mints `RESTORED`" (§9c lines 2678–2679) |
| 11 | `recovery_outcome_finalised` has exactly two writers, WORK not among them | PASS | §0.8 lines 673–676; continuation `<- RESTORED` at HASHING (§10a line 3124); WORK sets it nowhere (§9c lines 2641–2683) |
| 12 | Post-restoration redistribution stays `RESTORED` only when it needs no future reserve hash rate | PASS | `ClassifyRecoveryWork` NOTE (§9c lines 2532–2535) |

## 8. Failure-mode contrast

Two mislabellings U1 makes structurally impossible:

- **A breached census treated as `RESTORED`.** Suppose the current `ACTIVE_HASHING` census still
  breaches the floor. `outcome_consistent_with_census(RESTORED, census)` returns
  `census.breach = false` → false (§9 line 2279), so neither the epilogue's `warranted <- RESTORED`
  arm (which requires `NOT census.breach`, §9 line 2242) nor the continuation's apply guard (§10a
  line 3067) admits it. A breach BEFORE the deadline yields `warranted = NONE` (§9 line 2244),
  routing to `ClassifyRecoveryWork` / `SeatRecoveryWork` — WORK, not an outcome. There is no path
  by which a breached census produces a `RESTORED` finalisation.

- **Reserve-dependent restoration applied BEFORE active-hash restoration.** Suppose restoration
  depended on reserves not yet woken and were marked `RESTORED` at the moment reserves are
  activated. This is exactly the impossible Stage-1T ELSE, and it is gone (§10a line 3153).
  Activation reaches CURRENT only at the later `WakeCompleteEvent` (§10 lines 2718–2719), so the
  census at the activation instant still breaches; `ApplyRecoveryWorkAfterEpilogue` on
  `install_committed` keeps `SECURITY_RECOVERY` and marks nothing `RESTORED` (§9c lines 2677–2683,
  2690). `RESTORED` is minted only after a LATER final census — computed once the woken reserve is
  in `ACTIVE_HASHING` and `H_honest` has risen (§9c lines 2678–2679) — shows no breach. The outcome
  can never precede the active-hash restoration it reports.

## 9. Result

U1 separates the recovery WORK action (B) from the recovery OUTCOME decision (A). The
reserve-dependent `RESTORED` continuation of Stage 1T was logically impossible — `RESTORED`
requires `census.breach = false` (§9 line 2279) while a reserve-dependent restoration presupposes
the current `ACTIVE_HASHING` census still breaches (reserves reach CURRENT only at a later
`WakeCompleteEvent`, §10 lines 2718–2719) — so its removal removes an unreachable arm and does NOT
weaken `outcome_consistent_with_census(RESTORED)`, whose one-line guard is untouched. A recovery-work
action is a `RECOVERY_WORK_ACTION` (`RESERVE_ACTIVATION_REQUIRED` / `RANGE_REDISTRIBUTION_REQUIRED`
/ `NONE`, §0.8 line 718) with its own `RecoveryWorkID`, status, and registries
(`recovery_work` / `pending_recovery_work` / `recovery_work_seq`, §0.8 lines 719–729); it is NEVER a
`RecoveryOutcome` and is NEVER `APPLIED` as `RESTORED` (§0.8 lines 713–714). The canonical flow —
final census shows breach before deadline → `ClassifyRecoveryWork` → `SeatRecoveryWork` seats ONE
versioned `RecoveryWorkDueEvent` → post-epilogue `ApplyRecoveryWorkAfterEpilogue` activates
reserves / prepares coverage while the round STAYS `SECURITY_RECOVERY` → a LATER final census
decides (no breach → `RESTORED`; breach + deadline → `UNRECOVERABLE`; breach before deadline →
continue) — keeps the outcome decision in the census and the work in the post-epilogue hook.
`ApplyRecoveryAssignmentContinuationAfterEpilogue` is now REDISTRIBUTION-ONLY (`census.breach =
false`, §10a lines 3045–3048, 3067), and a redistribution performed after an already-restored
census stays a `RESTORED` continuation only when it does not depend on future reserve hash rate
(§9c lines 2532–2535). U1 is a recovery-lifecycle separation of a work action from an outcome
decision; it introduces no new consensus feature, and the A1 accepted baseline of 8.420833333 kWh
is unchanged — no census value, residency interval, or transition-energy term is edited, and
nothing about how time or energy is counted is altered.

The prohibited rebranded-algorithm-name variants are not used anywhere in this document.
