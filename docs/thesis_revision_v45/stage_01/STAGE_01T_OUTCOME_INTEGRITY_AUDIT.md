# Stage 1T — Recovery Outcome-Integrity Audit (T4 — no fabricated UNRECOVERABLE)

This is a documentation-only paper audit of the Stage-1T correction **T4 — no
fabricated UNRECOVERABLE / outcome integrity** as edited in
`docs/thesis_revision_v45/stage_01/STAGE_01_PROTOCOL_PSEUDOCODE.md`. T4 requires that an
IRREVERSIBLE branch-C install failure occurring AFTER the `SECURITY_RECOVERY ->
ASSIGNMENT` transition is NEVER relabelled as an `UNRECOVERABLE` floor outcome; it
records its OWN disposition `recovery_episode_disposition = RECOVERY_INSTALL_FAILED_ABORTED`,
marks the decision `APPLY_FAILED_TERMINAL`, leaves `recovery_outcome_finalised` UNSET, and
closes the round through the declared recovery-finalising `RoundAbort(reason =
recovery_install_failed_aborted)`. The consensus algorithm is named **PoCol**; **the idle
policy within PoCol** is referenced here only as a named mechanism, and this audit claims
no energy, security, or fairness property of the idle policy within PoCol. T4 is an
outcome-integrity/reporting correction to how a terminal negative is *labelled and
finalised*; it is NEVER a change to how time or energy is counted. The **A1 accepted
accounting baseline of 8.420833333 kWh is UNCHANGED** — no census value, residency
interval, transition-energy term, or accounting quantity is edited. This is documentation
only: no new consensus feature is introduced. Every claim below is checked against the
pseudocode as edited; no behaviour is inferred beyond the text.

## 1. The three terminal negatives (§0.8 enums; §10a)

A recovery episode can end negatively in three distinct ways. T4 keeps them separate — a
distinct source census, a distinct disposition/status, and a distinct
`recovery_outcome_finalised` state — so that a mere install failure can never masquerade
as a genuine floor breach. The two applied outcomes are `RESTORED` and `UNRECOVERABLE`
(`RECOVERY_OUTCOME in {RESTORED, UNRECOVERABLE}`, §0.8 lines 682–683); the two
non-applied dispositions are `RECOVERY_EPISODE_DISPOSITION in {TERMINAL_CANCELLED,
RECOVERY_INSTALL_FAILED_ABORTED}` (§0.8 line 684); the decision statuses now include the
T4-added `APPLY_FAILED_TERMINAL` alongside `APPLY_FAILED` and `HORIZON_DEFERRED`
(`RECOVERY_DECISION_STATUS`, §0.8 lines 687–688).

| Terminal negative | Source / trigger | Site | `recovery_episode_disposition` | Decision status | `recovery_outcome_finalised[episode]` | `round_state` after | Episode |
|---|---|---|---|---|---|---|---|
| (a) genuine `UNRECOVERABLE` | FINAL census still breaches the floor after the deadline (O3/R14) | `CompleteSecurityRecovery` branch D (§10a lines 2629–2637), finalised by caller (lines 2576–2583) | null (an outcome was applied) | `APPLIED` | set = `UNRECOVERABLE` | `ROUND_ABORTED` | cleared (finalised) |
| (b) `RECOVERY_INSTALL_FAILED_ABORTED` | IRREVERSIBLE post-transition install failure (`install_ok = false`) | `ApplyRecoveryAssignmentContinuationAfterEpilogue` install-fail branch (§10a lines 2781–2791) | `RECOVERY_INSTALL_FAILED_ABORTED` | `APPLY_FAILED_TERMINAL` | **UNSET** | `ROUND_ABORTED` | cleared once (line 2788) |
| (c) reversible `APPLY_FAILED` | pre-transition failure (seat rejected / plan not warranted) OR post-transition rollback (`assignment_phase_failed`) | caller branch-C FAILED arm (§10a lines 2591–2601); continuation rollback ELSE arm (§10a lines 2801–2809) | null (episode still active) | `APPLY_FAILED` (or `HORIZON_DEFERRED`) | **UNSET** | `SECURITY_RECOVERY` | PRESERVED |

The two applied outcomes set `recovery_outcome_finalised`; the two non-applied
dispositions never do. `recovery_episode_disposition` is "Null while the episode is active
or when an outcome was applied (`recovery_outcome_finalised` is set instead)" (§0.8 lines
673–674). (The remaining `RECOVERY_EPISODE_DISPOSITION` value, `TERMINAL_CANCELLED`, is
the S4 cleanup of an episode a terminal round left unfinished, `CancelActiveRecoveryEpisode`
§10a lines 2210–2231 — also not an applied outcome and also leaving
`recovery_outcome_finalised` unset; it is outside the three T4 negatives audited here.)

## 2. (a) Genuine `UNRECOVERABLE` — the ONLY source of an `UNRECOVERABLE` floor outcome

`UNRECOVERABLE` is reserved for a FINAL census that still breaches the floor after the
deadline. Its warrant is checked by `outcome_consistent_with_census`: `IF outcome =
UNRECOVERABLE: RETURN (census.breach = true AND census.deadline_reached = true)` (§9 line
2185), matching the epilogue's selection `census.breach AND census.deadline_reached ->
UNRECOVERABLE` (line 2157). It is applied on exactly one path:
`CompleteSecurityRecovery` branch D takes the declared recovery-finalising
`RoundAbort(RoundContext, reason = floor_unrecoverable, recovery_finalising = true)`
(§10a lines 2633–2634) and returns `recovery_branch_result(kind = SUCCESS, target =
ROUND_ABORTED)` (line 2636). The caller's `SUCCESS` arm then marks the decision `APPLIED`
and sets `recovery_outcome_finalised[episode] <- D.outcome` (§10a lines 2579–2580) — here
`D.outcome = UNRECOVERABLE`. The `RoundAbort` reason is `floor_unrecoverable`, never
`recovery_install_failed_aborted`; the two are textually distinct.

## 3. (b) `RECOVERY_INSTALL_FAILED_ABORTED` / `APPLY_FAILED_TERMINAL` — irreversible post-transition install failure

Inside `ApplyRecoveryAssignmentContinuationAfterEpilogue` (§10a `PROCEDURE` line 2741, the
ONLY place branch-C `RESTORED` is applied) the redistribution-only path transitions
`SECURITY_RECOVERY -> ASSIGNMENT` (line 2772, bumps `state_version`) and installs the
disjoint set. When `install_ok = false` the failure is IRREVERSIBLE — the state mutation
has already occurred — so the branch executes the declared T4 sequence (lines 2781–2791):

1. `SetRecoveryDecisionStatus(RoundContext, decision_id, APPLY_FAILED_TERMINAL)` (line
   2784) — via the sole status mutator (`SetRecoveryDecisionStatus`, §9 line 2188).
2. `REMOVE decision_id from pending_recovery_decisions[episode]` (line 2785).
3. `SET recovery_episode_disposition[episode] <- RECOVERY_INSTALL_FAILED_ABORTED` (line
   2786) — the comment reads "T4 (NOT `recovery_outcome_finalised`)".
4. Clear the installation registries and `SET current_recovery_episode <- null` "cleared
   exactly once" (lines 2787–2788).
5. `RoundAbort(RoundContext, reason = recovery_install_failed_aborted, ...,
   recovery_finalising = true)` (lines 2789–2790) — the DECLARED recovery-finalising
   abort, so the round never lingers in `ASSIGNMENT` with an active episode and no live
   continuation; `RETURN recovery_continuation_install_aborted(decision_id)` (line 2791).

`recovery_outcome_finalised[episode]` is NOT written on this path. There is no
`recovery_outcome_finalised[episode] <- UNRECOVERABLE` anywhere in the install-fail
branch, and the `RoundAbort` reason is `recovery_install_failed_aborted`, not
`floor_unrecoverable`. The install failure therefore records its OWN disposition and never
counterfeits a floor-breach outcome. The T3 episode invariant confirms this is one of the
three declared install exits: "`ROUND_ABORTED` + `recovery_episode_disposition =
RECOVERY_INSTALL_FAILED_ABORTED`" (§0.8 lines 697–698; §10a NOTE lines 2841–2842).

## 4. (c) Reversible `APPLY_FAILED` — pre-transition or rollback failure preserves the episode

A reversible negative is one that leaves no irreversible mutation, so the episode is
PRESERVED and a later epilogue may re-seat a warranted outcome. It arises two ways:

- **Pre-transition** — branch C could not seat a valid continuation or its target fell
  beyond `T`. `CompleteSecurityRecovery` returns `kind = FAILED`; the caller's FAILED arm
  records `HORIZON_DEFERRED` (target beyond `T`) or `APPLY_FAILED` (seat rejected),
  PRESERVES the episode (`current_recovery_episode` NOT cleared, `recovery_outcome_finalised`
  NOT set) and keeps `round_state = SECURITY_RECOVERY` (§10a lines 2591–2601). The
  pre-installation stale/unwarranted guard inside the continuation likewise records
  `recovery_continuation_apply_stale_noop` with NO mutation, leaving the decision
  `APPLYING` for a later re-arm (§10a lines 2762–2767).
- **Post-transition but reversible rollback** — the install produced no valid disjoint set
  yet `CompleteAssignmentPhase` reports `assignment_phase_failed` (round still
  `ASSIGNMENT`). The continuation UNDOES the partial install, transitions
  `ASSIGNMENT -> SECURITY_RECOVERY` (rollback complete), marks the decision `APPLY_FAILED`,
  and PRESERVES the episode (§10a lines 2801–2809). This is the reversible sibling of the
  install-fail abort: same event, but because a clean rollback was possible the outcome is
  `APPLY_FAILED` (episode preserved), not `APPLY_FAILED_TERMINAL` (episode finalised via
  abort).

In neither reversible case is `recovery_outcome_finalised` written and in neither is
`UNRECOVERABLE` produced.

## 5. `recovery_outcome_finalised[episode]` is set ONLY on an actually-applied outcome

`recovery_outcome_finalised` is a map "Set ONCE, ONLY when an outcome is ACTUALLY APPLIED"
(§0.8 lines 662–667). The two — and only two — writers are:

- `ApplyRecoveryCompletionAfterEpilogue`'s SUCCESS arm (branches A/B/D), `recovery_outcome_finalised[episode]
  <- D.outcome` (§10a line 2580) — `RESTORED` for A/B, `UNRECOVERABLE` for D;
- `ApplyRecoveryAssignmentContinuationAfterEpilogue` when branch C reaches `HASHING`,
  `recovery_outcome_finalised[episode] <- RESTORED` "set ONLY on an actually-applied
  outcome (T4)" (§10a line 2796).

The §0.8 gloss states it explicitly: "T4: it is NOT set on a failed branch-C install (that
records `recovery_episode_disposition = RECOVERY_INSTALL_FAILED_ABORTED`, never a
fabricated UNRECOVERABLE), and NOT set by a `TERMINAL_CANCELLED` cleanup (S4)" (§0.8 lines
665–667). It is therefore never set merely because a continuation was seated (S3), never
on an install-fail abort (§3), and never on a reversible `APPLY_FAILED` (§4).

## 6. No path converts an install failure into a fabricated `UNRECOVERABLE`

The distinguishing evidence is the pair of DISTINCT `RoundAbort` reasons, both
`recovery_finalising = true` but textually separate:

| Terminal negative | `RoundAbort(reason = ...)` | `recovery_outcome_finalised` written? |
|---|---|---|
| genuine `UNRECOVERABLE` (branch D) | `floor_unrecoverable` (§10a line 2633) | yes — `UNRECOVERABLE` (§10a line 2580) |
| install-fail abort (T4) | `recovery_install_failed_aborted` (§10a line 2789) | no (§10a lines 2782–2786) |

The install-fail branch (§10a lines 2781–2791) contains no assignment of `UNRECOVERABLE`
to `recovery_outcome_finalised` and does not call `RoundAbort(reason = floor_unrecoverable)`;
the branch-D path (§10a lines 2629–2637) is the sole producer of an `UNRECOVERABLE`
finalised outcome and is gated on `outcome_consistent_with_census(UNRECOVERABLE, census)`,
i.e. a real `census.breach AND census.deadline_reached` (§9 line 2185). The two terminal
negatives are thus structurally unable to be confused. The continuation NOTE affirms it:
the hook "NEVER fabricates UNRECOVERABLE on install failure (T4:
RECOVERY_INSTALL_FAILED_ABORTED)" (§10a line 2838).

## 7. Tie to invariant I16

I16 (STAGE_01_INVARIANT_CATALOGUE §I16) requires that "Security-floor breaches are
recorded, not silently repaired in the reported data," and its T4 clause states an
irreversible branch-C install failure "is recorded as its own disposition
`recovery_episode_disposition = RECOVERY_INSTALL_FAILED_ABORTED` with decision status
`APPLY_FAILED_TERMINAL` and closes the round via the declared recovery-finalising
`RoundAbort`; it is NEVER relabelled as an `UNRECOVERABLE` floor outcome (which is reserved
for a FINAL census that still breaches the floor after the deadline, O3/R14) and NEVER sets
`recovery_outcome_finalised`" (I16 lines 292–298). The catalogue's "Consequence of
violation" names exactly the failure T4 forbids: "a branch-C install failure silently
reported as a genuine `UNRECOVERABLE` floor breach" (I16 lines 309–312). The pseudocode as
audited enforces the invariant: an install failure records its own disposition and does not
overwrite or invent a floor-breach outcome, so the reported data neither erases a real
breach nor manufactures a false one.

## 8. PASS-check table (exact names)

| # | Check | Verdict | Evidence (exact names / lines) |
|---|---|---|---|
| 1 | `UNRECOVERABLE` only from a final-census breach after the deadline | PASS | `outcome_consistent_with_census(UNRECOVERABLE, census)` requires `census.breach AND census.deadline_reached` (§9 line 2185); branch D `RoundAbort(reason = floor_unrecoverable)` (§10a line 2633) |
| 2 | Install failure records `RECOVERY_INSTALL_FAILED_ABORTED`, not `UNRECOVERABLE` | PASS | `recovery_episode_disposition[episode] <- RECOVERY_INSTALL_FAILED_ABORTED` (§10a line 2786) |
| 3 | Install failure marks `APPLY_FAILED_TERMINAL` | PASS | `SetRecoveryDecisionStatus(..., APPLY_FAILED_TERMINAL)` (§10a line 2784); status added to `RECOVERY_DECISION_STATUS` (§0.8 lines 687–688) |
| 4 | Install failure closes via declared recovery-finalising abort, distinct reason | PASS | `RoundAbort(reason = recovery_install_failed_aborted, recovery_finalising = true)` (§10a lines 2789–2790) |
| 5 | Install-fail abort does NOT set `recovery_outcome_finalised` | PASS | comment "NOT `recovery_outcome_finalised`" (§10a line 2786); §0.8 lines 665–667 |
| 6 | `recovery_outcome_finalised` set only on an actually-applied outcome | PASS | `<- RESTORED` at HASHING (§10a line 2796); `<- D.outcome` on SUCCESS A/B/D (§10a line 2580); "Set ONCE, ONLY when an outcome is ACTUALLY APPLIED" (§0.8 line 662) |
| 7 | Reversible `APPLY_FAILED` preserves the episode (round stays / returns `SECURITY_RECOVERY`) | PASS | caller FAILED arm (§10a lines 2591–2601); rollback ELSE arm `-> SECURITY_RECOVERY`, `APPLY_FAILED` (§10a lines 2801–2809) |
| 8 | No path converts an install failure into a fabricated `UNRECOVERABLE` | PASS | install-fail branch (§10a lines 2781–2791) has no `floor_unrecoverable` / no `<- UNRECOVERABLE`; NOTE "NEVER fabricates UNRECOVERABLE on install failure" (§10a line 2838) |
| 9 | Every install exit ends in exactly one declared terminal state | PASS | T3 invariant: `HASHING + APPLIED` / `SECURITY_RECOVERY + APPLY_FAILED` / `ROUND_ABORTED + RECOVERY_INSTALL_FAILED_ABORTED` (§0.8 lines 696–698; §10a lines 2841–2842) |
| 10 | Ties to I16 (breaches recorded, never silently repaired) | PASS | I16 T4 clause (lines 292–298); consequence-of-violation (lines 309–312) |

## 9. Result

The three terminal negatives are held apart precisely. A genuine `UNRECOVERABLE` outcome
is produced ONLY by `CompleteSecurityRecovery` branch D from a final census that still
breaches the floor after the deadline, via `RoundAbort(reason = floor_unrecoverable)` and
the caller's SUCCESS finalisation `recovery_outcome_finalised[episode] <- UNRECOVERABLE`
(§10a lines 2629–2637, 2580). An IRREVERSIBLE post-transition install failure records its
OWN disposition `recovery_episode_disposition = RECOVERY_INSTALL_FAILED_ABORTED`, marks the
decision `APPLY_FAILED_TERMINAL`, leaves `recovery_outcome_finalised` UNSET, and closes the
round via the declared `RoundAbort(reason = recovery_install_failed_aborted)` (§10a lines
2781–2791) — a distinct reason from `floor_unrecoverable`, so it is never relabelled as a
floor outcome. A reversible pre-transition or rollback failure records `APPLY_FAILED` (or
`HORIZON_DEFERRED`), preserves the episode, and keeps or returns `round_state =
SECURITY_RECOVERY` (§10a lines 2591–2601, 2801–2809). `recovery_outcome_finalised` is
written only on an actually-applied outcome — `RESTORED` when the continuation reaches
`HASHING`, `UNRECOVERABLE` when branch D's abort succeeds — and never on an install-failed
abort, a reversible failure, or a mere seating. This pairs with invariant I16: a
security-floor situation is recorded as what it actually is, and an install failure is
never silently reported as a genuine floor breach. T4 is an outcome-integrity/reporting
correction to labelling and finalisation only; it introduces no new consensus feature, and
the A1 accepted baseline of 8.420833333 kWh is unchanged — no census value, residency
interval, or transition-energy term is edited, and nothing about how time or energy is
counted is altered.

The prohibited rebranded-algorithm-name variants are not used anywhere in this document.
