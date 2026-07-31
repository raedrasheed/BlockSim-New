# Stage 1Q — Recovery-Census Version Audit (Q1)

## Intro

This audit is a documentation-only record of Stage 1Q correction **Q1 — version every
final recovery census** in `STAGE_01_PROTOCOL_PSEUDOCODE.md`. The consensus
specification under revision is **PoCol**. Within PoCol, *the idle policy within PoCol*
is referenced strictly as a mechanism; it is not the subject of Q1 and no behavioural
change to it is described here. This audit claims no property of PoCol and revises no
measured quantity: the A1 baseline of **8.420833333 kWh** is UNCHANGED.

Scope is limited to Q1: the versioned recovery-census record (§0.8 Core data model),
the `CommitRecoveryCensus` writer (§9 Security-floor evaluation), the
`ReconcilePendingRecoveryDecisions` supersede-or-re-affirm procedure (§9), and the fact
that a pending recovery decision BINDS to a `RecoveryCensusVersion` — not merely to a
newer `RecoveryDecisionID`. Q1 sits alongside the P5 decision-versioning and O4
apply-once guarantees and does not weaken them.

## 1. The versioned recovery-census record (§0.8 Core data model)

Two fields carry Q1, both in the O4/P3/P5/Q1 security-recovery episode registries that
`RoundInitialise` resets per round:

- `recovery_census_seq` — a monotonic per-episode counter "advanced every time the
  epilogue evaluates a FINAL event-time census while round_state = SECURITY_RECOVERY.
  RecoveryCensusVersion = the value it takes; it VERSIONS each final recovery census"
  (§0.8). It is `SET recovery_census_seq <- 0` by `RoundInitialise` (§0.8), so census
  versions never carry across a round boundary.
- `latest_recovery_census` — a map `RecoveryEpisodeID -> recovery_census_record`,
  "Published by the epilogue on every final recovery census" (§0.8). The
  `recovery_census_record` includes exactly: `RecoveryEpisodeID`,
  `RecoveryCensusVersion`, `event_time`, `RoundID`, `TemplateID`, `state_version`,
  `H_active`, `H_honest`, `H_adversarial`, `q_adv`, `breach`, and `deadline_reached`
  (§0.8).

Per §0.8, "A pending decision binds to a `RecoveryCensusVersion`; a newer final census
re-affirms (same outcome) or SUPERSEDES (contradicting outcome) it — so freshness is
judged against EVERY final census, not merely against the existence of a newer
`RecoveryDecisionID`."

## 2. `CommitRecoveryCensus` — version + publish (§9)

`CommitRecoveryCensus` (§9) is invoked by the `SecurityFloorEvaluate` epilogue on the
FINAL event-time census while `round_state = SECURITY_RECOVERY` — both on entry
(the FIRST final recovery census of the episode) and on every subsequent final census
in recovery. Its EFFECTS (§9):

- `SET recovery_census_seq <- recovery_census_seq + 1` — the monotonic
  `RecoveryCensusVersion`.
- `SET latest_recovery_census[episode] <- recovery_census_record(...)` with
  `RecoveryCensusVersion = recovery_census_seq`, `breach = breach`, and
  `deadline_reached = recovery_deadline_reached[episode]` — the breach and
  deadline-reached fields are taken from THIS final census.

Its PRECONDITIONS state it is "called by the epilogue (`SecurityFloorEvaluate`) while
round_state = SECURITY_RECOVERY, on the FINAL event-time census" (§9), and its NOTE
records the invariant: "EVERY final recovery census receives a monotonic version." The
census payload (`H_active`, `H_honest`, `H_adversarial`, `q_adv`, `RoundID`,
`TemplateID`, `state_version`) is copied from `latest_security_census[event_time]`, the
FINAL committed security census (Q4).

## 3. `ReconcilePendingRecoveryDecisions` — supersede vs. re-affirm (§9)

Immediately after `CommitRecoveryCensus`, the epilogue calls
`ReconcilePendingRecoveryDecisions` (§9). Its PRECONDITION is that
"`latest_recovery_census[episode]` just published by `CommitRecoveryCensus`" (§9). For
each `decision_id` in `pending_recovery_decisions[episode]` (stable order) it reads
`D <- recovery_decisions[decision_id]` and branches on the consistency predicate:

- **Supersede.** `IF NOT outcome_consistent_with_census(D.outcome, census)` — the newer
  FINAL census CONTRADICTS this pending decision — then `SET
  recovery_decisions[decision_id].status <- SUPERSEDED`, cancel `D.due_event_ref` on the
  event queue when it is still pending, and `REMOVE decision_id from
  pending_recovery_decisions[episode]` (§9). Its NOTE adds that "A superseded decision
  NEVER becomes valid again (its status is terminal-negative)."
- **Re-affirm.** `ELSE` — still consistent with the FINAL census — then `SET
  recovery_decisions[decision_id].bound_census_version <- census.RecoveryCensusVersion`,
  re-affirming its justification to the newest version (§9).

The consistency predicate is `outcome_consistent_with_census(outcome, census)` (§9):
`RESTORED` is consistent "iff `census.breach = false`"; `UNRECOVERABLE` is consistent
"iff `census.breach = true AND census.deadline_reached = true`"; any other combination
CONTRADICTS the outcome. The procedure NOTE states the post-condition: "after this runs,
NO pending decision retains an older census version — each is either SUPERSEDED (and
removed from `pending_recovery_decisions`) or re-affirmed to the latest
`RecoveryCensusVersion`."

## 4. Binding to `RecoveryCensusVersion`, not to a newer decision id

`SecurityFloorEvaluate` (§9) calls `CommitRecoveryCensus` then
`ReconcilePendingRecoveryDecisions` BEFORE it reads `census <-
latest_recovery_census[episode]` and derives the warranted outcome (RESTORED when
`NOT census.breach`; UNRECOVERABLE when `census.breach AND census.deadline_reached`;
otherwise NONE). A decision therefore BINDS to a `RecoveryCensusVersion`: §0.8 records
that "A decision binds to `RecoveryCensusVersion` (Q1); it is APPLIED only after the
epilogue of its OWN completion event_time re-affirms that version and the final census
still matches its outcome." The consequence is the Q1 property: a newer final census can
SUPERSEDE an older pending decision even when the newer census produces NO new
completion (warranted = NONE), because supersession is driven by the census, not by the
minting of a newer `RecoveryDecisionID`.

## 5. Worked examples

**(a) Pending RESTORED, then a breach-before-deadline census.** A `RESTORED` decision is
pending (`bound_census_version = v`). A later final event-time census in recovery shows
`breach = true` with `deadline_reached = false`. `CommitRecoveryCensus` publishes version
`v+1`. `ReconcilePendingRecoveryDecisions` evaluates
`outcome_consistent_with_census(RESTORED, census)` = (`census.breach = false`) = FALSE,
so the pending `RESTORED` is marked SUPERSEDED and removed IMMEDIATELY. The epilogue then
computes `warranted`: `breach AND NOT deadline_reached` -> NONE, so it returns
`recovery_pending(v+1)` and the round stays SECURITY_RECOVERY. The older decision is
invalidated even though the new census seats NO new completion.

**(b) Pending UNRECOVERABLE, then a restored census.** An `UNRECOVERABLE` decision is
pending. A later final census shows `breach = false`. `CommitRecoveryCensus` publishes the
new version; `ReconcilePendingRecoveryDecisions` evaluates
`outcome_consistent_with_census(UNRECOVERABLE, census)` = (`breach = true AND
deadline_reached = true`) = FALSE, so the pending `UNRECOVERABLE` is SUPERSEDED and
removed. The epilogue derives `warranted = RESTORED` (`NOT census.breach`) and
`SeatRecoveryCompletion` may seat a fresh `RESTORED` decision bound to the new version.

## 6. Acceptance checks

| # | Check (gate) | Evidence | Result |
|---|--------------|----------|--------|
| 1 | `recovery_census_seq` is a monotonic per-episode counter reset by `RoundInitialise` | §0.8; `RoundInitialise` `SET recovery_census_seq <- 0` | PASS |
| 2 | `latest_recovery_census` record carries `RecoveryCensusVersion`, `breach`, and `deadline_reached` from the final census | §0.8 record fields; §9 `CommitRecoveryCensus` EFFECTS | PASS |
| 3 | (Gate 1) EVERY final event-time census in SECURITY_RECOVERY is versioned — entry census and each subsequent one | §9 `SecurityFloorEvaluate` (entry + in-recovery `CommitRecoveryCensus` calls); §9 `CommitRecoveryCensus` NOTE | PASS |
| 4 | `outcome_consistent_with_census`: RESTORED iff `breach=false`; UNRECOVERABLE iff `breach=true AND deadline_reached=true` | §9 `outcome_consistent_with_census` | PASS |
| 5 | Reconcile marks a contradicted decision SUPERSEDED, cancels its due event, removes it from `pending_recovery_decisions`; re-affirms a consistent one to the latest version | §9 `ReconcilePendingRecoveryDecisions` EFFECTS | PASS |
| 6 | (Gate 2) A newer final census invalidates an older pending decision EVEN when it produces no new completion (warranted = NONE) | §9 `SecurityFloorEvaluate` (Reconcile before warranted; NONE -> `recovery_pending`); example (a) | PASS |
| 7 | A decision BINDS to `RecoveryCensusVersion` (re-affirmed each final census), not merely to a newer `RecoveryDecisionID` | §0.8 binding note; §9 `ReconcilePendingRecoveryDecisions` re-affirm branch | PASS |
| 8 | A SUPERSEDED decision is terminal-negative and never revived by a later failed schedule | §9 `ReconcilePendingRecoveryDecisions` NOTE; §9 `SeatRecoveryCompletion` NOTE | PASS |

---

Documentation only. The consensus specification is named PoCol; *the idle policy within
PoCol* is referenced as a mechanism only. No property is claimed. The A1 baseline
8.420833333 kWh is unchanged. The prohibited rebranded-algorithm-name variants are not
used anywhere in this document.
