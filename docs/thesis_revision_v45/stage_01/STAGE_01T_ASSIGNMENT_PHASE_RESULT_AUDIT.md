# Stage 1T — Assignment-Phase Result Audit (T5)

**Consensus mechanism.** This audit concerns the consensus specification named **PoCol**. Within PoCol,
**the idle policy within PoCol** is referenced solely as a mechanism; no property of the consensus
mechanism is claimed here. This is documentation only, describing the frozen behaviour of
`STAGE_01_PROTOCOL_PSEUDOCODE.md`; it neither adds a consensus feature nor amends any procedure beyond the
already-frozen T5 text it audits. The A1 accepted baseline of **8.420833333 kWh** is UNCHANGED and is
restated only for provenance: **T5 is a control-flow / disposition correction** — it makes the RESULT of the
single `ASSIGNMENT -> HASHING` step an explicit return value instead of a bare assertion. It moves no
residency boundary, re-times nothing, and re-prices nothing; T5 is never a change to how time or energy is
counted. Any energy difference remains attributable **only to reduced active power-time** (fewer / shorter
`ACTIVE_HASHING` residency intervals), exactly as `ApplyMinerStateTransition`'s `residency_ledger` measured
before.

**Scope — Stage-1T correction T5 (`CompleteAssignmentPhase` returns an explicit disposition).**
`CompleteAssignmentPhase` (§2b) now RETURNS an EXPLICIT disposition
`assignment_phase_completed | assignment_phase_failed(reason)` instead of relying on a bare, crash-on-failure
`ASSERT`. A malformed intended assignment set is caught BEFORE the irreversible `HASHING` transition and
returns `assignment_phase_failed(reason = malformed_assignment_set)` while the round is STILL `ASSIGNMENT`
(reversible) — NOT a failed `ASSERT` that strands or crashes a caller. `assignment_phase_completed` means the
round reached `HASHING`. The branch-C recovery continuation consumer
`ApplyRecoveryAssignmentContinuationAfterEpilogue` (§10a, T1) branches on the disposition: on
`assignment_phase_completed` it marks the decision `APPLIED`; on `assignment_phase_failed` it rolls the round
back to `SECURITY_RECOVERY` (reversible pre-HASHING failure, episode preserved). Grounded in **§2b**
(`PROCEDURE CompleteAssignmentPhase`), **§10a** (`PROCEDURE ApplyRecoveryAssignmentContinuationAfterEpilogue`,
branch C, disposition `T5`), and the two ordinary callers **§2a** (`PrepareParticipantsForNewRound`, K2) and
**§19** (`TemplateRefresh`, L2).

## 1. From a bare assertion to an explicit, testable result (§2b)

Before T5, the sole `ASSIGNMENT -> HASHING` step relied on an assertion: a well-formedness violation would
trip a failed `ASSERT` and crash (or leave the caller with no defined recovery), and a caller could only
observe the edge indirectly by re-reading `round_state`. T5 replaces that contract with an EXPLICIT return
value. `CompleteAssignmentPhase`'s signature now declares
`RETURNS: assignment_phase_completed | assignment_phase_failed(reason)` — an explicit executable disposition.
The two failure reasons are named enumerated values (`malformed_assignment_set`, `transition_failed`), and
the single success value (`assignment_phase_completed`) is returned only after the transition helper has run.
The result is testable: a caller distinguishes success from a reversible failure by matching the returned
disposition, never by inspecting a side effect or by surviving an assertion.

The procedure NOTE binds the new obligation on the consuming side: it is `K2/M2/T5: the SOLE executable
ASSIGNMENT -> HASHING step, now returning an EXPLICIT disposition. A caller (recovery installation, §10a)
MUST branch on the disposition rather than \`ASSERT round_state = HASHING\` (T5)`. So the correction is not
merely a wider return type — it re-assigns responsibility from a fatal assertion inside the callee to an
explicit branch inside the caller.

## 2. The pre-HASHING well-formedness catch keeps the failure reversible (§2b)

The well-formedness check runs BEFORE the irreversible `HASHING` transition, so a caught malformation leaves
the round in `ASSIGNMENT` — reversible. The guarded condition is the intended set's structural validity:

```
    IF NOT (for every PENDING assignment a: a is bound to (RoundID_current, TemplateID_committed)   # I3
            AND a is disjoint per I1 AND a's lineage has exactly one live head, I18b)
       OR some assignment references an old RoundID/TemplateID:
      RETURN assignment_phase_failed(reason = malformed_assignment_set)     # T5: BEFORE the HASHING transition (round still ASSIGNMENT — reversible)
```

The comment states the ordering explicitly: `A well-formedness failure is caught BEFORE the irreversible
HASHING transition and returns assignment_phase_failed — NO failed ASSERT may strand a caller in ASSIGNMENT
(T5/gate 6/gate 7).` Because the `RETURN` fires before `TransitionRoundState(..., HASHING, ...)`, no state
epoch is bumped, no applicability-entry census is captured for `HASHING`, and `round_state` is still
`ASSIGNMENT`. The malformation therefore never becomes a fait accompli in `HASHING`; the caller can roll back
cleanly. The NOTE confirms the invariant on the executable side: `an assignment_phase_failed(malformed_
assignment_set) leaves the round in ASSIGNMENT (reversible — the caller rolls back)`, and `a HashWorkEvent
dispatched while round_state != HASHING is a no-op` (§5) — so even a stray hash event cannot exploit the
still-`ASSIGNMENT` window.

## 3. The disposition tail of `CompleteAssignmentPhase` (§2b, verbatim)

Only after the well-formedness gate passes does the procedure perform the single sanctioned transition and
then return success — with a defensive post-transition guard in between:

```
    # M2/K2: the SOLE executable ASSIGNMENT -> HASHING (R4) step, performed through the round-state helper,
    #        which captures the applicability-entry census automatically (floor is decided even at H_active = 0).
    CALL TransitionRoundState(RoundContext, HASHING, dispatch_envelope)     # R4 + K7 capture (M2)
    IF round_state != HASHING:
      RETURN assignment_phase_failed(reason = transition_failed)            # T5: defensive (should not occur)
    RETURN assignment_phase_completed
  RETURNS: assignment_phase_completed | assignment_phase_failed(reason)     # T5: explicit executable disposition
```

Three exhaustive outcomes result: (a) `assignment_phase_failed(reason = malformed_assignment_set)` before the
transition, round still `ASSIGNMENT`; (b) `assignment_phase_failed(reason = transition_failed)`, the
defensive post-transition reason that `should not occur`; (c) `assignment_phase_completed`, meaning the round
reached `HASHING`. The census that lets the epilogue decide the floor is captured by the `M2` helper on entry
to `HASHING` (`R4 + K7`), unchanged by T5 — the correction wraps the edge in a disposition, it does not
re-time or re-count the census.

## 4. The recovery continuation consumer branches on the disposition (§10a branch C)

`ApplyRecoveryAssignmentContinuationAfterEpilogue` (§10a, T1 — the ONLY place branch-C RESTORED is APPLIED)
is the consumer that MUST branch. In the redistribution-only arm it installs the disjoint set, then captures
and switches on the disposition:

```
      SET disp <- CALL CompleteAssignmentPhase(RoundContext, D.continuation_due_dispatch_envelope)   # T5: explicit disposition
      IF disp = assignment_phase_completed:                         # round now HASHING; the FINAL census confirms the floor (redistribution-only)
        # T3 exit (i): HASHING + decision APPLIED. This is the moment branch-C RESTORED is actually applied.
        CALL SetRecoveryDecisionStatus(RoundContext, decision_id, APPLIED)     # R4/R6
        SET recovery_outcome_finalised[episode] <- RESTORED                    # set ONLY on an actually-applied outcome (T4)
        ...
        RETURN recovery_continuation_applied(decision_id, RESTORED)
      ELSE:  # assignment_phase_failed -> REVERSIBLE (round still ASSIGNMENT). T3 exit (ii): roll back.
        # T5: roll back to SECURITY_RECOVERY, UNDO any partial PENDING assignment created by the install, mark the
        #   decision APPLY_FAILED, PRESERVE the episode (a later epilogue may re-seat if still warranted).
        UNDO the partial install (close any PENDING assignment created here; cancel any wake it seated)
        TRANSITION round_state -> SECURITY_RECOVERY                 # bumps state_version (G10); rollback complete
        ...
        CALL SetRecoveryDecisionStatus(RoundContext, decision_id, APPLY_FAILED)   # R6 mirror
        RETURN recovery_continuation_failed(decision_id)
```

The `IF disp = assignment_phase_completed` arm is the moment branch-C RESTORED is `actually applied`: the
decision is marked `APPLIED`, `recovery_outcome_finalised[episode]` is set to `RESTORED` (set ONLY on an
actually-applied outcome, T4), and the hook returns `recovery_continuation_applied`. The `ELSE` arm handles
the reversible failure: because `assignment_phase_failed` left the round in `ASSIGNMENT`, the hook UNDOes the
partial install, transitions back to `SECURITY_RECOVERY`, marks the decision `APPLY_FAILED`, and PRESERVES
the episode so a later epilogue may re-seat if still warranted. No `RESTORED` outcome is finalised on the
failure path — the two arms are mutually exclusive and each ends in exactly one settled state.

## 5. Both callers of the single ASSIGNMENT→HASHING owner see a consistent disposition (L2)

`CompleteAssignmentPhase` is the SINGLE executable `ASSIGNMENT -> HASHING` owner (`L2`) — `the only executable
ASSIGNMENT -> HASHING step in the spec`. Because there is exactly one owner, the disposition contract is the
same for every caller; each observes the identical `assignment_phase_completed | assignment_phase_failed(reason)`
value set. There are two caller classes:

1. **Ordinary assignment path.** `PrepareParticipantsForNewRound` (§2a, K2) calls
   `CALL CompleteAssignmentPhase(RoundContext, dispatch_envelope)  # K2: ASSIGNMENT -> HASHING (M1 envelope)`,
   and `TemplateRefresh` (§19, L2) calls
   `CALL CompleteAssignmentPhase(RoundContext, dispatch_envelope)   # L2/M2: SOLE ASSIGNMENT -> HASHING owner`
   after asserting `round_state = ASSIGNMENT`. On these construction paths the intended set is well-formed by
   construction, so the owner returns `assignment_phase_completed` and the round reaches `HASHING`. The return
   value is nonetheless the SAME explicit disposition — the well-formedness guard is present for both callers,
   so a violation on either path would surface as the identical reversible `assignment_phase_failed`, never a
   crash.
2. **Recovery continuation path.** `ApplyRecoveryAssignmentContinuationAfterEpilogue` (§10a, T1) captures the
   disposition into `disp` and branches (§4). This is the caller the NOTE names explicitly: it `MUST branch on
   the disposition rather than \`ASSERT round_state = HASHING\``.

Both classes route through the one owner, so the disposition is well-defined and consistent for each: a single
success value meaning `HASHING` reached, and a reversible `assignment_phase_failed` that leaves the round in
`ASSIGNMENT` for the caller to handle.

## 6. PASS-check table (exact names)

| # | Check | Exact name(s) cited | Location | Verdict |
|---|-------|---------------------|----------|---------|
| 1 | Disposition is an explicit return type, not a bare assertion | `RETURNS: assignment_phase_completed \| assignment_phase_failed(reason)` | §2b `CompleteAssignmentPhase` | PASS |
| 2 | Malformed set caught BEFORE the irreversible transition, round still `ASSIGNMENT` (reversible) | `RETURN assignment_phase_failed(reason = malformed_assignment_set)` precedes `TransitionRoundState(RoundContext, HASHING, dispatch_envelope)` | §2b | PASS |
| 3 | Success means the round reached `HASHING` | `RETURN assignment_phase_completed` after `TransitionRoundState(..., HASHING, ...)` | §2b | PASS |
| 4 | Defensive post-transition guard is separate, not a crash | `IF round_state != HASHING: RETURN assignment_phase_failed(reason = transition_failed)` | §2b | PASS |
| 5 | Recovery consumer branches on the disposition | `SET disp <- CALL CompleteAssignmentPhase(...)`; `IF disp = assignment_phase_completed` → `SetRecoveryDecisionStatus(..., APPLIED)`; `ELSE` → rollback | §10a branch C | PASS |
| 6 | Failure path is reversible, episode preserved | `TRANSITION round_state -> SECURITY_RECOVERY`; `SetRecoveryDecisionStatus(..., APPLY_FAILED)`; `PRESERVE the episode` | §10a branch C | PASS |
| 7 | Single ASSIGNMENT→HASHING owner; both caller classes see one consistent disposition | `CompleteAssignmentPhase` (K2/L2 sole owner); callers `PrepareParticipantsForNewRound` (§2a), `TemplateRefresh` (§19), `ApplyRecoveryAssignmentContinuationAfterEpilogue` (§10a) | §2a / §19 / §10a | PASS |
| 8 | No residency boundary moved, no re-count | census still captured by the `M2` helper (`R4 + K7`); A1 `8.420833333 kWh` unchanged | §2b | PASS |

## 7. Contrast — the failure mode T5 removes

Two failure modes are precluded. First, **crash-on-failed-ASSERT**: under the prior bare-assertion contract a
malformed intended assignment set would trip a failed `ASSERT` and crash — or leave a caller stranded in
`ASSIGNMENT` with no defined disposition, so the recovery continuation could neither mark the decision
`APPLIED` nor roll back cleanly. T5's pre-HASHING `assignment_phase_failed(reason = malformed_assignment_set)`
turns that into a reversible, testable result the caller branches on. Second, **transition-despite-malformed**:
performing the `ASSIGNMENT -> HASHING` edge and only then discovering the set is malformed would make the
malformation irreversible — the round would be in `HASHING`, the applicability-entry census captured for a
malformed set, and a `HashWorkEvent` could execute. T5 forecloses this by ordering the well-formedness gate
strictly before `TransitionRoundState(..., HASHING, ...)`, so a malformed set is never carried into `HASHING`.
The residual defensive `transition_failed` reason (`should not occur`) is returned, not asserted, so even the
theoretical post-transition anomaly yields a handled disposition rather than a crash.

## 8. Result

T5 is realised exactly as specified: `CompleteAssignmentPhase` (§2b) RETURNS an explicit
`assignment_phase_completed | assignment_phase_failed(reason)` disposition; a malformed intended set is caught
BEFORE the irreversible `HASHING` transition and returns `assignment_phase_failed(reason =
malformed_assignment_set)` while the round is STILL `ASSIGNMENT` (reversible); `assignment_phase_completed`
means the round reached `HASHING`; and a defensive `assignment_phase_failed(reason = transition_failed)`
covers the post-transition anomaly. The branch-C consumer `ApplyRecoveryAssignmentContinuationAfterEpilogue`
(§10a) branches on the disposition — `APPLIED` on completion, rollback to `SECURITY_RECOVERY` with the episode
preserved on failure — and the two ordinary callers `PrepareParticipantsForNewRound` (§2a) and
`TemplateRefresh` (§19) see the identical disposition from the single ASSIGNMENT→HASHING owner (L2). This is a
control-flow / disposition correction only: it seats no new residency boundary and changes no cost model, so
the A1 accepted baseline of **8.420833333 kWh** is unchanged and any energy difference remains attributable
solely to reduced active power-time.

## Footer

This document is documentation only; it makes no property claim about the consensus mechanism. The consensus
mechanism is named **PoCol**, and **the idle policy within PoCol** is referenced solely as a mechanism. The
A1 baseline of **8.420833333 kWh** is unchanged. The prohibited rebranded-algorithm-name variants are not used anywhere in this document.
