# Stage 1P — Recovery-Decision Version Audit (P5)

## Intro

This audit is a documentation-only record of Stage 1P correction **P5 — decision
versioning for recovery completion** in `STAGE_01_PROTOCOL_PSEUDOCODE.md`. The
consensus specification under revision is **PoCol**. Within PoCol, *the idle policy
within PoCol* is referenced strictly as a mechanism; it is not the subject of P5 and
no behavioural change to it is described here. This audit claims no property of PoCol
and revises no measured quantity: the A1 baseline of **8.420833333 kWh** is UNCHANGED.

Scope is limited to P5: the versioned `RecoveryDecisionID`, the `latest_recovery_decision`
map, the minting and supersession logic in `SeatRecoveryCompletion` (§9), and the
decision-version guard in `CompleteSecurityRecovery` (§10a). P5 sits alongside — and
does not weaken — the O4 apply-once idempotence of a recovery episode.

## 1. The decision-versioning data model (§0.8 Core data model)

Three fields carry P5, all in the O4/P3/P5 security-recovery episode registries that
`RoundInitialise` resets per round:

- `recovery_decision_seq` — a monotonic per-round counter advanced each time the
  event-time epilogue MINTS a recovery decision. It is `SET ... <- 0` by
  `RoundInitialise` (§0.8/RoundInitialise), so decision identities never carry across
  a round boundary.
- `RecoveryDecisionID = (RecoveryEpisodeID, recovery_decision_seq)` — the DETERMINISTIC
  identity of one recovery decision (§0.8, `# RecoveryDecisionID = (RecoveryEpisodeID,
  recovery_decision_seq)`).
- `latest_recovery_decision` — a map `RecoveryEpisodeID -> { decision_id, outcome }`
  holding the LATEST decision for the episode. A `CompleteSecurityRecovery` carrying a
  `decision_id` that is NOT the latest is SUPERSEDED and returns
  `recovery_decision_stale_noop` (§0.8).

`RecoveryDecisionID` is versioned per episode, whereas `RecoveryEpisodeID =
(RoundID, recovery_episode_seq)` (O4) is the immutable episode identity. Multiple
decisions may exist for one episode over time; at most one is ever applied (see §5).

## 2. Minting and `latest_recovery_decision` in `SeatRecoveryCompletion` (§9)

`SeatRecoveryCompletion` is the SOLE seater of `CompleteSecurityRecovery`, called only
by the event-time epilogue (`SecurityFloorEvaluate`) on the FINAL census. Its P5 logic:

1. If `recovery_outcome_finalised[episode]` is set, there is nothing to seat
   (`recovery_completion_already_finalised`) — O4 defers to the already-applied outcome.
2. **No redundant re-seat (SAME outcome).** IF `recovery_completion_pending[episode]`
   AND `latest_recovery_decision[episode]` EXISTS AND its `.outcome = outcome`, RETURN
   `recovery_completion_already_pending(outcome)`. The same standing decision is not
   re-seated.
3. **Mint (fresh or SUPERSEDING outcome).** Otherwise `SET recovery_decision_seq <-
   recovery_decision_seq + 1`; `SET decision_id <- (episode, recovery_decision_seq)`.
4. Seat through the SOLE scheduler `ScheduleEvent` at `(t_next, RECOVERY_COMPLETE)`,
   carrying `{RecoveryEpisodeID, RecoveryDecisionID = decision_id, RecoveryOutcome, ...}`.
5. **On `scheduled(...)` SUCCESS ONLY:** `SET latest_recovery_decision[episode] <-
   { decision_id, outcome }` (the LATEST decision supersedes older ones) and `SET
   recovery_completion_pending[episode] <- true` (P4). RETURN
   `recovery_completion_seated(decision_id, outcome)`.

A DIFFERENT outcome for the SAME standing episode falls through the re-seat guard
(the outcomes differ), mints a new `decision_id`, and — on scheduler success — becomes
the new `latest_recovery_decision`, SUPERSEDING the earlier pending decision.

## 3. The decision-version guard in `CompleteSecurityRecovery` (§10a) and its ordering vs O4 apply-once

`CompleteSecurityRecovery` now takes `RecoveryDecisionID` among its INPUTS. Its guard
order is FIXED:

1. **(a) O4 apply-once, checked FIRST.** IF `recovery_outcome_finalised[RecoveryEpisodeID]`
   is set, RETURN `recovery_completion_duplicate_noop`. A finalised episode absorbs any
   later or replayed completion before decision versions are consulted.
2. **(b) Stale round/episode/epoch.** IF `round_state != SECURITY_RECOVERY` OR
   `RecoveryEpisodeID != current_recovery_episode` OR the round/template/state-version
   provenance is superseded, RETURN `recovery_completion_stale_noop`.
3. **(c) P5 DECISION-VERSION GUARD.** IF `latest_recovery_decision[RecoveryEpisodeID]`
   does NOT EXIST OR `RecoveryDecisionID != latest_recovery_decision[RecoveryEpisodeID].decision_id`,
   RETURN `recovery_decision_stale_noop`. This applies ONLY if the dispatched decision
   is still the LATEST for the episode.
4. **(d) Finalise then dispatch.** `SET recovery_outcome_finalised[RecoveryEpisodeID]
   <- RecoveryOutcome`; `SET current_recovery_episode <- null`; `CLEAR
   recovery_completion_pending[RecoveryEpisodeID]`; then dispatch the RecoveryOutcome
   branch (UNRECOVERABLE -> RoundAbort branch D; RESTORED -> branches A/B/C).

Ordering matters: O4 (a) precedes P5 (c). A completion that already finalised the
episode is a duplicate no-op regardless of decision version; only a not-yet-finalised
episode reaches the version comparison, where a superseded decision no-ops.

## 4. Worked scenario TV126 (superseded recovery decision)

- **t1 — D1 seated.** The epilogue's FINAL census produces outcome O_1. No decision is
  pending; `SeatRecoveryCompletion` mints `decision_id = D1`, `ScheduleEvent` succeeds:
  `latest_recovery_decision[episode] = { D1, O_1 }`, `recovery_completion_pending = true`.
- **t2 — D2 seated (before D1 dispatches).** A newer final census yields a DIFFERENT
  outcome O_2. The SAME-outcome re-seat guard does not fire (O_2 != O_1); a new
  `decision_id = D2` is minted and scheduled successfully:
  `latest_recovery_decision[episode] = { D2, O_2 }`. D2 SUPERSEDES D1.
- **D1 dispatches.** O4 guard (a): not finalised. Guard (b): still the active episode.
  P5 guard (c): `RecoveryDecisionID = D1 != latest.decision_id = D2` -> RETURN
  `recovery_decision_stale_noop`. The OLD outcome O_1 is never applied.
- **D2 dispatches.** Guard (a): still not finalised. Guard (b): episode current. P5
  guard (c): `D2 == latest.decision_id = D2` -> pass. Finalise: `recovery_outcome_finalised
  <- O_2`, `current_recovery_episode <- null`, pending cleared; the O_2 branch is applied.
- **Result.** Exactly one outcome (O_2, the newer final-census decision) is applied to
  the episode; the superseded D1 no-ops. TV126 is registered under R111 in
  `STAGE_01_TRACEABILITY_MATRIX.csv`.

## 5. Reconciling P5 (many decisions over time) with O4 (one APPLIED outcome per episode)

P5 and O4 are complementary, not conflicting. P5 permits MULTIPLE decisions to be minted
and seated for a single `RecoveryEpisodeID` as successive final-census evaluations refine
the outcome; `latest_recovery_decision` records only the most recent. O4 guarantees that
`CompleteSecurityRecovery` FINALISES an episode exactly once (`recovery_outcome_finalised`
is `SET ONCE`). The P5 decision-version guard ensures that of all seated decisions, ONLY
the latest is eligible to finalise; every superseded decision returns
`recovery_decision_stale_noop`, and every post-finalisation completion returns
`recovery_completion_duplicate_noop`. Together: many decisions may be seated, at most one
outcome is ever APPLIED per episode.

## 6. Acceptance checks

| # | Check | Evidence | Result |
|---|-------|----------|--------|
| 1 | `recovery_decision_seq` is a monotonic per-round counter reset by `RoundInitialise`; `RecoveryDecisionID = (RecoveryEpisodeID, recovery_decision_seq)` | §0.8; `RoundInitialise` `SET recovery_decision_seq <- 0` | PASS |
| 2 | `latest_recovery_decision` maps `RecoveryEpisodeID -> {decision_id, outcome}` holding the LATEST decision | §0.8 | PASS |
| 3 | `SeatRecoveryCompletion` mints a fresh `RecoveryDecisionID` and sets `latest_recovery_decision`/`recovery_completion_pending` ONLY on `ScheduleEvent` success | §9 `SeatRecoveryCompletion` EFFECTS | PASS |
| 4 | A DIFFERENT outcome supersedes a pending one; the SAME standing outcome returns `recovery_completion_already_pending` (no re-seat) | §9 re-seat guard + mint | PASS |
| 5 | `CompleteSecurityRecovery` P5 guard: non-latest `RecoveryDecisionID` returns `recovery_decision_stale_noop` | §10a guard (c) | PASS |
| 6 | O4 apply-once (guard a) is checked BEFORE the P5 decision-version guard (guard c) | §10a EFFECTS ordering | PASS |
| 7 | Property (gate 9): a completion whose `RecoveryDecisionID` is NOT the latest is SUPERSEDED — an old RESTORED/UNRECOVERABLE outcome cannot apply after a newer final-census decision | §10a NOTE (P5); §0.8 | PASS |
| 8 | The §0.7g-driver tie key for `CompleteSecurityRecovery` is `(RoundID, RecoveryEpisodeID, RecoveryDecisionID)` | §0.7g-driver seating table | PASS |

---

Documentation only. The consensus specification is named PoCol; *the idle policy within
PoCol* is referenced as a mechanism only. No property is claimed. The A1 baseline
8.420833333 kWh is unchanged. The prohibited rebranded-algorithm-name variants are not
used anywhere in this document.
