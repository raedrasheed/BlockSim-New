# Stage 1O — Recovery-Outcome Audit (O3)

This audit is a documentation-only record for the PhD-thesis revision of the **PoCol** consensus
specification. It describes PoCol with **the idle policy within PoCol** in effect, treated here strictly
as a mechanism; no security, liveness, or energy property is claimed. The A1 baseline of
**8.420833333 kWh** is UNCHANGED by this correction. The prohibited rebranded-algorithm-name variants are
not used anywhere in this document.

**Scope.** Stage 1O correction **O3 — make `FloorUnrecoverable` (R14) reachable; `RecoveryOutcome`** in
`STAGE_01_PROTOCOL_PSEUDOCODE.md` and `STAGE_01_ROUND_STATE_MACHINE.md`. O3 is a corrective edit to the
recovery-completion contract only; it introduces no new state, alters no threshold, and changes no metric.

---

## 1. The Stage-1N contradiction and how O3 removes it

At Stage 1N, `PROCEDURE CompleteSecurityRecovery` (pseudocode §10a) carried the PRECONDITION
`floor_result = restored`, yet its body opened the abort branch with

```
    IF NOT floor_result = restored:                       # (D) R14 -> abort THIS round (N1)
      RETURN CALL RoundAbort(RoundContext, reason = floor_unrecoverable, dispatch_envelope = dispatch_envelope)
```

The only source that ever seated `CompleteSecurityRecovery` was the floor-restored epilogue, which carried
`{floor_result = restored, ...}`, and the precondition itself asserted `floor_result = restored`.
Therefore `NOT floor_result = restored` could never hold: branch D was UNREACHABLE, and R14
(`FloorUnrecoverable`) was described but NOT executable.

O3 REPLACES the contradictory precondition with a `RecoveryOutcome` precondition that accepts EITHER
outcome. Pseudocode §10a now reads `RecoveryOutcome in {RESTORED, UNRECOVERABLE}`, with the inline note that
this "replaces the contradictory `floor_result = restored`" and that "BOTH outcomes are accepted here;
RESTORED -> branches A/B/C, UNRECOVERABLE -> branch D." Because a settled `UNRECOVERABLE` outcome can now be
carried in, branch D is reachable.

## 2. The `RecoveryOutcome` enum and the four outcome-keyed branches

The `RecoveryOutcome` enum is defined in §0.8 (Core data model):

- `RESTORED` — the floor was restored (branches A/B/C of `CompleteSecurityRecovery`).
- `UNRECOVERABLE` — the floor cannot be restored (branch D → `RoundAbort(floor_unrecoverable)`, round only).

`CompleteSecurityRecovery` (§10a) now takes INPUTS `RoundContext, dispatch_envelope, RecoveryEpisodeID,
RecoveryOutcome, RoundID_at_decision, TemplateID_at_decision, state_version_at_decision`. After the O4
episode-idempotence and stale-decision guards, it dispatches four branches keyed by `RecoveryOutcome`:

| Branch | Outcome / condition | Target and mechanism |
| --- | --- | --- |
| **D** (R14) | `RecoveryOutcome = UNRECOVERABLE` | `RETURN CALL RoundAbort(RoundContext, reason = floor_unrecoverable, dispatch_envelope = dispatch_envelope)` — closes ONLY this round (N1) |
| **A** (R13) | `RESTORED`, `active_propagation_set` non-empty | resume `SOLUTION_PROPAGATION` via `TransitionRoundState`; live candidate contexts and their scheduled certificate/block events PRESERVED (G8) |
| **B** (R13) | `RESTORED`, no context, no assignment change | `HASHING` via `TransitionRoundState` |
| **C** (R13) | `RESTORED`, redistribution needed | `ASSIGNMENT` → `CompleteAssignmentPhase` → `HASHING`, no new template fabricated (I1 disjoint under the same committed `TemplateID`) |

## 3. The named, seated `UNRECOVERABLE` source: `RecoveryDeadlineEvent` (§9a)

The concrete `UNRECOVERABLE` source is `PROCEDURE RecoveryDeadlineEvent` (pseudocode §9a).

- **Where it is seated.** On ENTRY to `SECURITY_RECOVERY`, inside the breach branch of
  `SecurityFloorEvaluate` (§9), the round mints a deterministic `RecoveryEpisodeID = (RoundID_current,
  recovery_episode_seq)` and seats `RecoveryDeadlineEvent` through the SOLE scheduler `ScheduleEvent`, at
  `target_event_time = min(t + recovery_deadline_window, run_horizon_T)`, microphase `RECOVERY_DEADLINE`.
- **What it carries.** `{RecoveryEpisodeID = episode, RoundID_at_entry = RoundID_current, TemplateID_at_entry
  = TemplateID_committed, state_version_at_entry = state_version_current}`.
- **When it seats `UNRECOVERABLE`.** When it fires with the floor STILL breached — round still in
  `SECURITY_RECOVERY`, `RecoveryEpisodeID` equal to `current_recovery_episode`, epoch matching
  (`RoundID`/`TemplateID`/`state_version`), and no completion already pending or finalised — it seats ONE
  `CompleteSecurityRecovery` through `ScheduleEvent` at a strictly-later `event_time` (`> dispatch_envelope.event_time`,
  `<= run_horizon_T`), microphase `RECOVERY_COMPLETE`, carrying `{RecoveryEpisodeID, RecoveryOutcome =
  UNRECOVERABLE, RoundID_at_decision, TemplateID_at_decision, state_version_at_decision}`. If a completion was
  already seated (e.g. by the floor-restored epilogue), the deadline is a deterministic no-op (RESTORED wins
  because it was seated first).
- **The concrete call path.** A recovery episode now has an executable path to R14:

  ```
  SecurityFloorEvaluate (breach → enter SECURITY_RECOVERY, mint episode, ScheduleEvent RecoveryDeadlineEvent)
    → RecoveryDeadlineEvent fires with floor still breached
      → ScheduleEvent CompleteSecurityRecovery(RecoveryOutcome = UNRECOVERABLE)
        → CompleteSecurityRecovery branch D
          → RoundAbort(reason = floor_unrecoverable)
  ```

  R14 is therefore REACHABLE and EXECUTABLE, not merely "described".

## 4. Round state-machine reconciliation (§2.5 / §3.10 / R13 / R14)

`STAGE_01_ROUND_STATE_MACHINE.md` was updated to reflect the two sources and `RecoveryOutcome`:

- **§2.5 `SECURITY_RECOVERY` exit conditions** now list exit "to `ROUND_ABORTED` if the floor cannot be
  restored by the recovery deadline (via the seated `RecoveryDeadlineEvent` → `RecoveryOutcome =
  UNRECOVERABLE` source, O3)", and state that "Every exit is driven by the executable
  `CompleteSecurityRecovery` (§10a), guarded to one completion per `RecoveryEpisodeID` (O4)."
- **§3.10 What happens after a security-floor violation** states that entering `SECURITY_RECOVERY` "MINTS a
  deterministic `RecoveryEpisodeID` and seats the named `RecoveryDeadlineEvent` (pseudocode §9a) — the
  concrete UNRECOVERABLE source (O3)"; that the exit is "seated with a settled `RecoveryOutcome ∈ {RESTORED,
  UNRECOVERABLE}`" by one of two sources; and that the contract "is NO LONGER 'described but non-executable'
  — a concrete seated source and call path exists for both R13 and R14."
- **R13 row (§4)** reads "EXECUTABLE via `CompleteSecurityRecovery` (pseudocode §10a/N2)", seated by the
  epilogue's floor-restored decision, dispatching branches A/B/C.
- **R14 row (§4)** reads "REACHABLE and EXECUTABLE (O3): the named seated source `RecoveryDeadlineEvent`
  (§9a) seats `CompleteSecurityRecovery` with `RecoveryOutcome = UNRECOVERABLE`, whose branch D (§10a/N2) →
  `RoundAbort(reason = floor_unrecoverable)` closes ONLY this round (N1)."

Both R13 (RESTORED, via the floor-restored epilogue) and R14 (UNRECOVERABLE, via `RecoveryDeadlineEvent`)
now have executable sources and call paths.

## 5. Branch D closes ONLY the round (N1), never the run

Branch D calls `RoundAbort` (pseudocode §20). Its PRECONDITIONS note is explicit: "RoundAbort terminates ONE
round -- it does NOT terminate the simulation RUN and does NOT reconcile to the horizon T. It is NOT the
generic final-run flush (that is `FinalizeSimulationRun`, §20a)." `RoundAbort` records the abort, dispositions
live candidates, closes assignments via `CloseRoundAssignments`, transitions `round_state → ROUND_ABORTED`,
and RETURNS control; it performs NO residency settle and NO horizon-`T` reconciliation. Closing this round
(N1) does not close the run.

## 6. Acceptance checks

| # | Check | Result | Evidence |
| --- | --- | --- | --- |
| A1 | §10a precondition is `RecoveryOutcome in {RESTORED, UNRECOVERABLE}` (not `floor_result = restored`) | PASS | `CompleteSecurityRecovery` PRECONDITIONS, §10a |
| A2 | The Stage-1N `IF NOT floor_result = restored` branch is replaced by `IF RecoveryOutcome = UNRECOVERABLE` | PASS | branch D, §10a |
| A3 | `RecoveryOutcome` enum (RESTORED / UNRECOVERABLE) defined | PASS | §0.8 Core data model |
| A4 | Named seated UNRECOVERABLE source `RecoveryDeadlineEvent` seated on entry via `ScheduleEvent` | PASS | `SecurityFloorEvaluate` breach branch, §9; `RecoveryDeadlineEvent`, §9a |
| A5 | Concrete call path episode → `RecoveryDeadlineEvent` → `CompleteSecurityRecovery(UNRECOVERABLE)` → `RoundAbort(floor_unrecoverable)` | PASS | §9a NOTE; §10a branch D |
| A6 | R14 row states reachable/executable via the seated deadline source | PASS | R14 row, §4; §2.5; §3.10 |
| A7 | Both R13 and R14 have executable sources and call paths | PASS | R13/R14 rows §4; §10a branches A/B/C/D |
| A8 | Branch D closes ONLY the round (N1), never the run | PASS | `RoundAbort` PRECONDITIONS/NOTE, §20 |

---

*Documentation only. Algorithm name: PoCol. The idle policy within PoCol is described as a mechanism only;
no property is claimed. A1 baseline 8.420833333 kWh unchanged. The prohibited rebranded-algorithm-name
variants are not used anywhere in this document.*
