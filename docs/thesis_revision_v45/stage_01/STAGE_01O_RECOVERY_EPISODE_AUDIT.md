# Stage 1O — Recovery-Episode Idempotence Audit (O4)

This audit is documentation only. It describes the consensus algorithm **PoCol** and, within it,
the idle policy within PoCol strictly as a mechanism; it claims no property of that mechanism. The A1
continuous full-participation baseline (`8.420833333 kWh`) is UNCHANGED. The prohibited
rebranded-algorithm-name variants are not used anywhere in this document.

**Scope.** Stage 1O correction **O4 — recovery-episode idempotence**, as specified in
`docs/thesis_revision_v45/stage_01/STAGE_01_PROTOCOL_PSEUDOCODE.md`. The audit verifies, against the
authoritative pseudocode, that a single security-recovery episode admits **at most one seated
completion event** and **at most one applied outcome**, and that both guarantees are carried by
per-episode registry KEYS — not by a prose "ENSURE exactly one". The procedures audited are
`RoundInitialise` (§1), `SecurityFloorEvaluate` (§9, breach branch and floor-restored epilogue),
`RecoveryDeadlineEvent` (§9a), and `CompleteSecurityRecovery` (§10a); the data model is §0.8 (Core
data model, Stage 1F).

## 1. The recovery-episode data model (§0.8; reset by RoundInitialise, §1)

The O4 registries are declared in §0.8 under the banner "O4 security-recovery episode registries
(reset by RoundInitialise; keyed by RecoveryEpisodeID)". They are per-ROUND state, reset fresh every
round by `RoundInitialise` (§1) alongside the other I-04 per-round registries.

| Field | §0.8 type | Role |
| --- | --- | --- |
| `recovery_episode_seq` | monotonic per-round counter | Advanced by +1 when the round ENTERS SECURITY_RECOVERY; supplies the deterministic episode index (G7-style). |
| `RecoveryEpisodeID` | `(RoundID, recovery_episode_seq)` | The DETERMINISTIC, immutable identity of one recovery episode; the key for both O4 maps. |
| `current_recovery_episode` | RecoveryEpisodeID or null | The ACTIVE episode while `round_state = SECURITY_RECOVERY`; null otherwise. Set on entry, cleared when the episode's completion is finalised. |
| `recovery_completion_pending` | map RecoveryEpisodeID -> boolean | The **seat-once** key: true once the FIRST completion source seats one `CompleteSecurityRecovery` for the episode. |
| `recovery_outcome_finalised` | map RecoveryEpisodeID -> RecoveryOutcome | The **apply-once** key: set ONCE, when `CompleteSecurityRecovery` APPLIES the episode's outcome. |

`RecoveryOutcome in {RESTORED, UNRECOVERABLE}` (O3). `RoundInitialise` (§1) resets all five fields at
round start:

```
SET        recovery_episode_seq      <- 0        # O4: deterministic RecoveryEpisodeID counter
SET        current_recovery_episode  <- null     # O4: no active recovery episode at round start
INITIALISE recovery_completion_pending <- empty map   # O4: per-episode "one completion seated" key
INITIALISE recovery_outcome_finalised  <- empty map   # O4: per-episode "one outcome applied" key
```

## 2. Minting on entry to SECURITY_RECOVERY (§9, breach branch)

When `SecurityFloorEvaluate` (§9) detects a breach from `{HASHING, SOLUTION_PROPAGATION}` (I-05), the
round transitions to SECURITY_RECOVERY and the episode is MINTED deterministically:

```
SET recovery_episode_seq <- recovery_episode_seq + 1
SET episode <- (RoundID_current, recovery_episode_seq)
SET current_recovery_episode <- episode
SET recovery_completion_pending[episode] <- false        # no completion seated yet
```

The same branch then seats the NAMED UNRECOVERABLE source `RecoveryDeadlineEvent` (§9a) through the
sole scheduler, carrying `{RecoveryEpisodeID = episode, RoundID_at_entry, TemplateID_at_entry,
state_version_at_entry}` (J8 epoch). The episode key minted here is what drives at-most-one-completion
idempotence for BOTH completion sources.

## 3. The seat-once key: `recovery_completion_pending` across BOTH sources

At most one completion is SEATED per episode because BOTH sources check and set the same boolean key
`recovery_completion_pending[episode]`. This is the mechanism — the boolean IS the registry key, not a
prose invariant.

**(a) Floor-restored epilogue** (`SecurityFloorEvaluate` §9, `(NOT breach) AND round_state =
SECURITY_RECOVERY`):

```
IF recovery_completion_pending[episode] OR recovery_outcome_finalised[episode] is set:
  RETURN floor_restored_completion_already_pending       # O4: deterministic duplicate no-op
SET recovery_completion_pending[episode] <- true         # O4: this epilogue seats the ONE completion
CALL ScheduleEvent(... CompleteSecurityRecovery ... {RecoveryOutcome = RESTORED ...})
```

**(b) `RecoveryDeadlineEvent`** (§9a), after its stale guard passes:

```
IF recovery_completion_pending[RecoveryEpisodeID]:
  RETURN recovery_deadline_superseded_noop
SET recovery_completion_pending[RecoveryEpisodeID] <- true   # O4: this deadline seats the ONE completion
CALL ScheduleEvent(... CompleteSecurityRecovery ... {RecoveryOutcome = UNRECOVERABLE ...})
```

Whichever source flips `recovery_completion_pending[episode]` to true first seats the ONE completion;
the other source observes the true key and returns its deterministic no-op
(`floor_restored_completion_already_pending` or `recovery_deadline_superseded_noop`).

## 4. The apply-once key: `recovery_outcome_finalised`, checked FIRST (§10a)

`CompleteSecurityRecovery` (§10a) is the sole owner of the applied outcome. Its FIRST action is the O4
episode-idempotence check against `recovery_outcome_finalised[RecoveryEpisodeID]`:

```
IF recovery_outcome_finalised[RecoveryEpisodeID] is set:
  RETURN recovery_completion_duplicate_noop
# then the N2/J8/O4 stale-decision guard:
IF round_state != SECURITY_RECOVERY
   OR RecoveryEpisodeID != current_recovery_episode
   OR RoundID_at_decision != RoundID_current OR TemplateID_at_decision != TemplateID_committed
   OR state_version_at_decision != state_version_current:
  RETURN recovery_completion_stale_noop
SET recovery_outcome_finalised[RecoveryEpisodeID] <- RecoveryOutcome
SET current_recovery_episode <- null
# ... only then dispatch branch A/B/C (RESTORED) or D (UNRECOVERABLE)
```

The apply-once key is SET and `current_recovery_episode` is cleared BEFORE any branch dispatch, so the
episode is finalised atomically at the point of application. Any later or replayed completion for the
same `RecoveryEpisodeID` finds the key set (or the episode no longer current) and returns a
deterministic no-op.

## 5. The keys are the mechanism

`recovery_completion_pending` (keyed by RecoveryEpisodeID) is the **seat-once** key; a source that finds
it true seats nothing. `recovery_outcome_finalised` (keyed by RecoveryEpisodeID) is the **apply-once**
key; a completion that finds it set applies nothing. Idempotence is therefore a property of the two
registry maps under the immutable `RecoveryEpisodeID`, not of any narrative "ENSURE exactly one" clause.

## 6. Idempotence scenarios (deterministic walk-through)

**(i) Floor restored first, deadline later.** The epilogue (§9) finds
`recovery_completion_pending[episode] = false`, sets it true, seats `CompleteSecurityRecovery(RESTORED)`.
Later `RecoveryDeadlineEvent` (§9a) passes its stale guard but observes
`recovery_completion_pending = true` and returns `recovery_deadline_superseded_noop`. Result: exactly one
seated completion (RESTORED wins because seated first); one applied outcome at §10a.

**(ii) Deadline first (floor still breached), floor-restored later.** `RecoveryDeadlineEvent` (§9a)
finds `recovery_completion_pending = false`, sets it true, seats `CompleteSecurityRecovery(UNRECOVERABLE)`.
The later floor-restored epilogue (§9) observes `recovery_completion_pending = true` and returns
`floor_restored_completion_already_pending`. Result: exactly one seated completion (UNRECOVERABLE wins);
one applied outcome at §10a.

**(iii) Duplicate/replayed completion for an already-finalised episode.** The first
`CompleteSecurityRecovery` (§10a) set `recovery_outcome_finalised[RecoveryEpisodeID]` and cleared
`current_recovery_episode`. A second/replayed `CompleteSecurityRecovery` for the same episode hits the
FIRST check, finds the key set, and returns `recovery_completion_duplicate_noop`. Result: still exactly
one applied outcome.

**(iv) Stale-epoch / non-current-episode completion.** A `CompleteSecurityRecovery` (§10a) whose
`RecoveryEpisodeID != current_recovery_episode`, or whose `RoundID`/`TemplateID`/`state_version` at
decision no longer match the current epoch, passes the finalised check but fails the stale-decision
guard and returns `recovery_completion_stale_noop`. Result: no outcome applied by the stale event; the
episode's single genuine completion (if any) governs.

Every scenario terminates in a single seated completion and a single applied outcome, decided
deterministically by which source touched the key first.

## 7. Acceptance checks

| # | Check | Result | Evidence |
| --- | --- | --- | --- |
| A1 | Five O4 fields declared and reset per round | PASS | §0.8 lines under "O4 security-recovery episode registries"; §1 `RoundInitialise` resets all five. |
| A2 | Episode minted deterministically on entry | PASS | §9 breach branch: `recovery_episode_seq += 1`; `episode = (RoundID_current, recovery_episode_seq)`; `current_recovery_episode = episode`. |
| A3 | Seat-once key checked+set in BOTH sources | PASS | §9 epilogue and §9a both gate on `recovery_completion_pending[episode]`. |
| A4 | Apply-once key checked FIRST in §10a | PASS | `IF recovery_outcome_finalised[RecoveryEpisodeID] is set: RETURN recovery_completion_duplicate_noop` is the first statement. |
| A5 | Finalise + clear before branch dispatch | PASS | §10a sets `recovery_outcome_finalised` and `current_recovery_episode <- null` before A/B/C/D. |
| A6 | RESTORED-first / deadline-later resolves once | PASS | Scenario (i): `recovery_deadline_superseded_noop`. |
| A7 | Deadline-first / restored-later resolves once | PASS | Scenario (ii): `floor_restored_completion_already_pending`. |
| A8 | Duplicate and stale completions are no-ops | PASS | Scenarios (iii)/(iv): `recovery_completion_duplicate_noop`, `recovery_completion_stale_noop`. |

---

*Documentation only. Algorithm name: PoCol. The idle policy within PoCol is described as a mechanism
only, with no property claimed. A1 baseline `8.420833333 kWh` unchanged. The prohibited
rebranded-algorithm-name variants are not used anywhere in this document.*
