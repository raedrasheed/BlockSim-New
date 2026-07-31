# Stage 1U — Assignment-Phase Caller Audit (U6)

**Consensus mechanism.** This audit concerns the consensus specification named **PoCol**. Within PoCol,
**the idle policy within PoCol** is referenced solely as a mechanism; no property of the consensus
mechanism is claimed here. This is documentation only, describing the frozen behaviour of
`STAGE_01_PROTOCOL_PSEUDOCODE.md`; it neither adds a consensus feature nor amends any procedure beyond the
already-frozen U6 text it audits. The A1 accepted baseline of **8.420833333 kWh** is UNCHANGED and is
restated only for provenance: **U6 is a control-flow / disposition-handling correction** — it makes every
CALLER of the single `ASSIGNMENT -> HASHING` owner capture and branch on that owner's returned disposition
instead of assuming success. It moves no residency boundary, re-times nothing, and re-prices nothing; U6 is
never a change to how time or energy is counted. Any energy difference remains attributable **only to
reduced active power-time** (fewer / shorter `ACTIVE_HASHING` residency intervals), exactly as
`ApplyMinerStateTransition`'s `residency_ledger` measured before.

**Scope — Stage-1U correction U6 (handle `CompleteAssignmentPhase` at every call site).** Correction T5
(§2b) made `CompleteAssignmentPhase` RETURN an explicit disposition
`assignment_phase_completed | assignment_phase_failed(reason)`, catching a malformed intended assignment set
BEFORE the irreversible `HASHING` transition while the round is STILL `ASSIGNMENT` (reversible). U6 closes
the loop on the CONSUMING side: it establishes that EVERY one of the THREE executable call sites now CAPTURES
that disposition into `disp` and BRANCHES on it, so that no caller returns success while the round remains
`ASSIGNMENT`. The three sites are the two ordinary construction paths
`PrepareParticipantsForNewRound` (§2a, K2 — blocking vector `TV171`) and `TemplateRefresh` (§19, L2 —
blocking vector `TV172`), and the recovery installation
`ApplyRecoveryAssignmentContinuationAfterEpilogue` (§10a, T1). Grounded in **§2b**
(`PROCEDURE CompleteAssignmentPhase`, the single owner), **§2a** (`PrepareParticipantsForNewRound`), **§19**
(`TemplateRefresh`), and **§10a** (`ApplyRecoveryAssignmentContinuationAfterEpilogue`).

## 1. From an owner that returns a disposition to callers that all consume it (U6)

T5 changed the callee: `CompleteAssignmentPhase` is the SOLE executable `ASSIGNMENT -> HASHING` step
(`K2/M2/T5`) and now `RETURNS: assignment_phase_completed | assignment_phase_failed(reason)`. Its NOTE binds
the obligation onto the caller: `A caller (recovery installation, §10a) MUST branch on the disposition rather
than \`ASSERT round_state = HASHING\` (T5)`. A returned disposition that a caller ignores is no safer than the
bare `ASSERT` it replaced — the reversible `assignment_phase_failed` would be discarded and the caller would
proceed to report success with the round still in `ASSIGNMENT`. U6 is exactly the caller-side completion of
that contract: at each of the three `CALL CompleteAssignmentPhase(...)` sites the returned value is bound to a
local `disp` and the control flow branches on it. There is exactly one owner, so every site observes the
identical two-valued disposition; U6 makes every site HANDLE both values.

The three executable call sites are exhaustive:

1. `SET disp <- CALL CompleteAssignmentPhase(RoundContext, dispatch_envelope)` in
   `PrepareParticipantsForNewRound` (§2a, comment `K2/T5: ASSIGNMENT -> HASHING (M1 envelope)`).
2. `SET disp <- CALL CompleteAssignmentPhase(RoundContext, dispatch_envelope)` in `TemplateRefresh` (§19,
   comment `L2/M2/T5: SOLE ASSIGNMENT -> HASHING owner`).
3. `SET disp <- CALL CompleteAssignmentPhase(RoundContext, D.continuation_due_dispatch_envelope)` in
   `ApplyRecoveryAssignmentContinuationAfterEpilogue` (§10a, comment `T5`).

Every other textual occurrence of `CompleteAssignmentPhase` in the specification is a NOTE, precondition, or
comment naming the single owner — none is a second executable invocation. The three above are the complete
caller set that U6 governs.

## 2. Call site 1 — `PrepareParticipantsForNewRound` (§2a, K2; TV171)

After the intended set is established (all `PENDING`, waking), the ordinary next-round path performs the
transition and now captures the disposition. The guiding comment is explicit: `U6: CAPTURE and BRANCH on the
T5 disposition — do NOT return participant_set_prepared while the round is still ASSIGNMENT.`

```
    SET disp <- CALL CompleteAssignmentPhase(RoundContext, dispatch_envelope)  # K2/T5: ASSIGNMENT -> HASHING (M1 envelope)
    IF disp = assignment_phase_failed(reason):
      FOR EACH a in the PENDING assignments created by THIS PrepareParticipantsForNewRound (stable order by MinerID, then CandidateID):
        IF a.wake_event_ref is still pending on EQ: CANCEL a.wake_event_ref on EQ
        CLOSE a as CLOSED (status = CLOSED, custody_status = revoked, reason = participant_setup_failed)   # J7: no live head (I18b)
      RECORD participant_setup_failed(reason)
      RETURN participant_set_setup_failed(reason)                 # round stays ASSIGNMENT for a legal re-setup / abort; NOT success
    RETURN participant_set_prepared
```

On `assignment_phase_completed` the procedure falls through to its existing success result
`RETURN participant_set_prepared`. On `assignment_phase_failed(reason)` — a well-formedness failure caught
BEFORE the irreversible `HASHING` transition, so the round is still `ASSIGNMENT` (reversible) — it rolls back
the just-created state: for every `PENDING` assignment THIS invocation created it CANCELs the still-pending
wake on `EQ` and CLOSEs the assignment (`custody_status = revoked, reason = participant_setup_failed`),
leaving no live head (`I18b`). It then `RECORD participant_setup_failed(reason)` and takes the declared
setup-failure return `participant_set_setup_failed(reason)` — the declared alternative in
`RETURNS: participant_set_prepared | participant_set_setup_failed`. The round stays `ASSIGNMENT` for a legal
re-setup or abort; the procedure NEVER returns `participant_set_prepared` with the round left in `ASSIGNMENT`.
This is precisely `TV171`: `PrepareParticipantsForNewRound receiving assignment_phase_failed does not return
participant_set_prepared and does not leave an unhandled ASSIGNMENT`.

## 3. Call site 2 — `TemplateRefresh` (§19, L2; TV172)

The refresh path builds a fresh `ORIGINAL` set over the new domain, `ASSERT round_state = ASSIGNMENT`, and
then — under the same U6 comment `CAPTURE and BRANCH on the T5 disposition — do NOT return a successful
new_TemplateID while the round is still ASSIGNMENT` — captures and branches:

```
    SET disp <- CALL CompleteAssignmentPhase(RoundContext, dispatch_envelope)   # L2/M2/T5: SOLE ASSIGNMENT -> HASHING owner
    IF disp = assignment_phase_failed(reason):
      FOR EACH a in the PENDING assignments created by THIS TemplateRefresh (stable order by MinerID, then CandidateID):
        IF a.wake_event_ref is still pending on EQ: CANCEL a.wake_event_ref on EQ
        CLOSE a as CLOSED (status = CLOSED, custody_status = revoked, reason = template_refresh_failed)   # J7: no live head (I18b)
      RECORD template_refresh_failed(reason)
      RETURN template_refresh_failed(reason)                       # round stays ASSIGNMENT for a legal re-setup / abort; NOT a new template
    RETURN new_TemplateID
```

On `assignment_phase_completed` the procedure returns its existing success value `RETURN new_TemplateID`. On
`assignment_phase_failed(reason)` — again a pre-`HASHING` well-formedness failure, round still `ASSIGNMENT`
(reversible) — it rolls back the refresh's just-created `PENDING` assignments and wakes (CANCEL the pending
wake on `EQ`, CLOSE each assignment with `custody_status = revoked, reason = template_refresh_failed`), then
`RECORD template_refresh_failed(reason)` and takes the declared refresh-failure return
`template_refresh_failed(reason)` — the declared alternative in `RETURNS: new_TemplateID |
template_refresh_failed`. It NEVER returns a successful new-template disposition with the round in
`ASSIGNMENT`. This is `TV172`: `TemplateRefresh receiving assignment_phase_failed follows its rollback/abort
path and does not return a successful new-template disposition`.

## 4. Call site 3 — the recovery installation `ApplyRecoveryAssignmentContinuationAfterEpilogue` (§10a, T1)

The recovery installation is the caller the T5 NOTE names by name (`MUST branch on the disposition`). After
`commit = install_committed` it captures the disposition and branches into two settled outcomes:

```
    SET disp <- CALL CompleteAssignmentPhase(RoundContext, D.continuation_due_dispatch_envelope)   # T5
    IF disp = assignment_phase_completed:                           # round now HASHING; the FINAL census confirms the floor
      CALL SetRecoveryDecisionStatus(RoundContext, decision_id, APPLIED)     # R4/R6
      SET recovery_outcome_finalised[episode] <- RESTORED                    # set ONLY on an actually-applied outcome (T4)
      RETURN recovery_continuation_applied(decision_id, RESTORED)
    ELSE:  # assignment_phase_failed -> REVERSIBLE (round still ASSIGNMENT). T3 exit (ii): roll the committed plan back.
      SET rb <- CALL RollbackRecoveryAssignmentPlan(RoundContext, plan.rollback_metadata)   # U5: undo the committed install
      IF rb = rollback_failed(rr):
        CALL SetRecoveryDecisionStatus(RoundContext, decision_id, APPLY_FAILED_TERMINAL)
        SET recovery_episode_disposition[episode] <- RECOVERY_INSTALL_FAILED_ABORTED
        CALL RoundAbort(RoundContext, reason = recovery_install_failed_aborted, ... recovery_finalising = true)
        RETURN recovery_continuation_install_aborted(decision_id)
      TRANSITION round_state -> SECURITY_RECOVERY                   # rollback complete; no live partial assignment (U5)
      CALL SetRecoveryDecisionStatus(RoundContext, decision_id, APPLY_FAILED)   # R6
      RETURN recovery_continuation_failed(decision_id)
```

On `assignment_phase_completed` the round is now `HASHING`: the decision is marked `APPLIED`,
`recovery_outcome_finalised[episode]` is set to `RESTORED` (set ONLY on an actually-applied outcome, `T4`),
and the hook returns `recovery_continuation_applied(decision_id, RESTORED)`. This differs from the two
ordinary callers only in that the recovery site had already COMMITTED a plan through
`CommitRecoveryAssignmentPlan` (`U5`), so its `ELSE` (reversible failure) arm undoes that committed install
through the NAMED procedure `RollbackRecoveryAssignmentPlan(RoundContext, plan.rollback_metadata)` rather than
an inline close-loop. When rollback succeeds it `TRANSITION round_state -> SECURITY_RECOVERY`, marks the
decision `APPLY_FAILED`, and returns `recovery_continuation_failed(decision_id)` with the episode preserved.
When rollback itself fails (`rb = rollback_failed(rr)` — an irreversible partial mutation) it takes the
declared abort path: `APPLY_FAILED_TERMINAL`, `recovery_episode_disposition[episode] <-
RECOVERY_INSTALL_FAILED_ABORTED`, `CALL RoundAbort(..., reason = recovery_install_failed_aborted)`, and
returns `recovery_continuation_install_aborted(decision_id)` — never fabricating `UNRECOVERABLE` (`T4`). Every
installation exit thus ends in exactly one of the three settled states its NOTE enumerates: `HASHING +
decision APPLIED; SECURITY_RECOVERY + APPLY_FAILED (rollback complete, episode preserved); ROUND_ABORTED +
RECOVERY_INSTALL_FAILED_ABORTED (T3/T4)`. No exit returns a `RESTORED` success with the round still
`ASSIGNMENT`.

## 5. PASS-check table (one row per call site)

| # | Call site (exact name) | Capture | Success branch | Pre-HASHING failure branch (round still `ASSIGNMENT`, reversible) | Vector | Verdict |
|---|------------------------|---------|----------------|-------------------------------------------------------------------|--------|---------|
| 1 | `PrepareParticipantsForNewRound` (§2a, K2) | `SET disp <- CALL CompleteAssignmentPhase(RoundContext, dispatch_envelope)` | `RETURN participant_set_prepared` | roll back this round's `PENDING` assignments + wakes (`CANCEL a.wake_event_ref`, `CLOSE a ... reason = participant_setup_failed`), `RECORD participant_setup_failed(reason)`, `RETURN participant_set_setup_failed(reason)` — NOT `participant_set_prepared` | `TV171` | PASS |
| 2 | `TemplateRefresh` (§19, L2) | `SET disp <- CALL CompleteAssignmentPhase(RoundContext, dispatch_envelope)` | `RETURN new_TemplateID` | roll back the refresh's `PENDING` assignments + wakes (`CANCEL a.wake_event_ref`, `CLOSE a ... reason = template_refresh_failed`), `RECORD template_refresh_failed(reason)`, `RETURN template_refresh_failed(reason)` — NOT a successful `new_TemplateID` | `TV172` | PASS |
| 3 | `ApplyRecoveryAssignmentContinuationAfterEpilogue` (§10a, T1) | `SET disp <- CALL CompleteAssignmentPhase(RoundContext, D.continuation_due_dispatch_envelope)` | `assignment_phase_completed` -> `SetRecoveryDecisionStatus(..., APPLIED)`, `recovery_outcome_finalised[episode] <- RESTORED`, `RETURN recovery_continuation_applied(decision_id, RESTORED)` | `ELSE` -> `RollbackRecoveryAssignmentPlan(...)` then `TRANSITION round_state -> SECURITY_RECOVERY` + `APPLY_FAILED` (`recovery_continuation_failed`), or on `rollback_failed` -> `RECOVERY_INSTALL_FAILED_ABORTED` + `RoundAbort` (`recovery_continuation_install_aborted`) | (T3/T4) | PASS |

All three sites bind the owner's return into `disp`, branch on
`assignment_phase_completed | assignment_phase_failed(reason)`, and — on the reversible pre-`HASHING` failure
— roll back the just-created assignments/wakes and take a declared failure path. None returns success while
the round remains `ASSIGNMENT`.

## 6. Failure-mode contrast — a caller that ignores the disposition

U6 precludes the failure mode named in the traceability threat column for R147: `a caller ignoring the
disposition and returning success while the round is still ASSIGNMENT; a malformed set crashing on a failed
ASSERT`. Consider the counterfactual at any of the three sites: a caller that writes
`CALL CompleteAssignmentPhase(...)` WITHOUT `SET disp <- ...`, or that captures `disp` but does not branch,
and unconditionally proceeds to `RETURN participant_set_prepared` / `RETURN new_TemplateID` / mark the
decision `APPLIED`. Because T5's `assignment_phase_failed(reason = malformed_assignment_set)` fires BEFORE the
irreversible `HASHING` transition, the round would still be `ASSIGNMENT` — yet the caller would report a
completed setup, a refreshed template, or a `RESTORED` recovery outcome. The just-created `PENDING`
assignments and their wakes would remain live and uncancelled, `round_state` would be a stranded `ASSIGNMENT`
that no caller handled, and (before T5) the same malformation would instead have tripped a failed `ASSERT`.
U6 forecloses this uniformly: each site binds `disp`, tests
`IF disp = assignment_phase_failed(reason)` (or, at the recovery site, the `assignment_phase_completed` /
`ELSE` split), rolls back the just-created state, and returns the declared failure value — so a still-
`ASSIGNMENT` round is always the RESULT of a handled failure path, never a success return.

## 7. Result

U6 is realised exactly as specified. All THREE executable `CompleteAssignmentPhase` call sites capture the
disposition into `disp` and branch on `assignment_phase_completed | assignment_phase_failed(reason)`:
`PrepareParticipantsForNewRound` (§2a) returns `participant_set_prepared` on success and, on a pre-`HASHING`
failure, rolls back the just-created `PENDING` assignments + wakes and returns
`participant_set_setup_failed(reason)` (`TV171`); `TemplateRefresh` (§19) returns `new_TemplateID` on success
and, on a pre-`HASHING` failure, rolls back and returns `template_refresh_failed(reason)` (`TV172`); and
`ApplyRecoveryAssignmentContinuationAfterEpilogue` (§10a) marks the decision `APPLIED` / `RESTORED` on
success and, on failure, uses `RollbackRecoveryAssignmentPlan` and either returns to `SECURITY_RECOVERY`
(`APPLY_FAILED`) or takes the declared `RECOVERY_INSTALL_FAILED_ABORTED` / `RoundAbort` path. No caller
returns success while the round remains `ASSIGNMENT`. This is a control-flow / disposition-handling
correction only: it seats no new residency boundary and changes no cost model, so the A1 accepted baseline of
**8.420833333 kWh** is unchanged and any energy difference remains attributable solely to reduced active
power-time.

## Footer

This document is documentation only; it makes no property claim about the consensus mechanism. The consensus
mechanism is named **PoCol**, and **the idle policy within PoCol** is referenced solely as a mechanism. The
A1 baseline of **8.420833333 kWh** is unchanged. The prohibited rebranded-algorithm-name variants are not
used anywhere in this document.
