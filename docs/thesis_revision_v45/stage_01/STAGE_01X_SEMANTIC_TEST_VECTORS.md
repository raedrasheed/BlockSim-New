# Stage 1X — Semantic Test Vectors (TV198–TV209)

These blocking paper test vectors exercise corrections X1–X8 of the recovery-rollback and retry-contract closure.
Each vector names the EXACT procedures and preconditions it drives, states the required outcome, and asserts NO
behaviour that is not written in `STAGE_01_PROTOCOL_PSEUDOCODE.md` (no assumed guard, transition, edge, or result
name). Every vector preserves the A1 baseline (`8.420833333 kWh`): none alters energy inputs, the census computation,
or any experiment. The algorithm is **PoCol** and the mechanism under test is the idle policy within PoCol.

Terminology: `T12` is the authoritative `WAKING -> OFFLINE` miner edge (`STAGE_01_MINER_STATE_MACHINE.md`);
`assignment_version_ref(aid, ver)` is the exact-version assignment reference; the canonical closure enums are
`status` / `custody_status` / `termination_reason` / `revocation_reason`, and `closure_detail` is the non-enum
free descriptor (X7).

---

## TV198 — Commit builds a complete per-item rollback record (X1/X5)

- **Procedures:** `CommitRecoveryAssignmentPlan`, `ReserveActivateFromPlan`, `RangeAssignFromPlan` / `RangeReassignFromPlan`.
- **Setup:** a plan with at least one `RESERVE_ACTIVATION` spec and one `REDISTRIBUTION` spec, committed post-epilogue
  (`scheduling_context = POST_EPILOGUE(pctx)`), all specs valid at revalidation.
- **Expected:** for EVERY committed activation, `created_items` gains a `rollback_item` carrying the ACTUAL
  `MinerID`, `AssignmentID`, `assignment_version`, `WakeEventRef`, the `pre_wake_state` captured BEFORE the constructor,
  the `coverage_custody_before_image` snapshot, the complete `rollback_envelope`, `kind`, and `provenance`. The success
  disposition is `install_committed(rollback_record(RecoveryInstallID, items = created_items))` — the record is returned
  EXPLICITLY, not held pass-by-reference.
- **Asserts nothing** about how a later rollback runs (see TV199) — only that the record is complete and explicit.

## TV199 — Recovery-plan rollback departs a WAKING miner to OFFLINE via T12 with the exact version (X1/X2/X8)

- **Procedures:** `RollbackRecoveryAssignmentPlan`, `ApplyMinerStateTransition`.
- **Setup:** an `install_committed(rollback_record)` whose committed miner `m` is still `WAKING` on its plan-created
  head when a post-commit `CompleteAssignmentPhase` fails; the caller passes the returned `rollback_record`.
- **Expected:** the rollback (1) CANCELS `item.WakeEventRef` first; (2) calls `ApplyMinerStateTransition(m, WAKING,
  OFFLINE, transition_envelope = item.rollback_envelope, reason = cancellation, assignment_ref =
  assignment_version_ref(item.AssignmentID, item.assignment_version), ...)` — the LEGAL `T12` edge with the EXACT
  version (never null); (3) closes the exact head; (4) restores the ledgers; (5) returns
  `rollback_completed(rolled_to_offline, rolled_back_items)` ONLY after verifying no `WakeEventRef` pending, no head
  live, and no affected miner `WAKING`. It CANNOT return `rollback_completed` while `m` is `WAKING` with no live event;
  a residual returns `rollback_failed(residual_partial_assignment)`.
- **Asserts nothing** about census H_* values (unchanged for a WAKING->OFFLINE; see TV208).

## TV200 — Recovery-plan rollback restores the coverage/custody ledgers (X1)

- **Procedures:** `RollbackRecoveryAssignmentPlan`.
- **Setup:** a committed plan whose specs mutated `custody_status` / `coverage_state` for their ranges; the
  `rollback_item.coverage_custody_before_image` holds the I8a/I8b snapshot taken before each constructor.
- **Expected:** for each item the rollback RESTORES the coverage-state / custody ledgers for `item.AssignmentID`'s
  range from `item.coverage_custody_before_image`, so after rollback the ledgers equal their pre-commit values; no
  range remains marked from the rolled-back install.

## TV201 — Setup rollback uses the exact assignment version from `assignment_by_miner`, never null (X2)

- **Procedures:** `PrepareParticipantsForNewRound` / `ContinueTemplateRefreshAssignmentSetup`, then
  `RollbackParticipantSetup` / `RollbackTemplateRefreshSetup`, `ApplyMinerStateTransition`.
- **Setup:** a setup that created a `PENDING` head for miner `m` and seated its wake (so
  `assignment_by_miner[m] = (AssignmentID, assignment_version)` was recorded AFTER `assignment_created` and BEFORE
  `StartWake`), then failed on a later miner, leaving `m` `WAKING`.
- **Expected:** the named rollback iterates `assignment_by_miner`, and for `m` departs `WAKING -> OFFLINE` via `T12`
  with `assignment_ref = assignment_version_ref(aid, ver)` — the EXACT recorded version, NEVER null — so the T12
  transition resolves the precise head it must close.

## TV202 — Template-refresh retry resumes the continuation and repeats no closure/commit (X3)

- **Procedures:** `SetupRetryEvent` (`setup_kind = TEMPLATE_REFRESH_SETUP`), `ContinueTemplateRefreshAssignmentSetup`.
- **Setup:** `TemplateRefresh` already ran once (it captured `old_TemplateID_snapshot`, called `CloseTemplateAssignments`,
  built the candidate, ran `TemplateCommit`, set `template_refresh_setup_committed[new_TemplateID]`, and delegated to
  `ContinueTemplateRefreshAssignmentSetup`); a wake failed, a bounded `SetupRetryEvent(TEMPLATE_REFRESH_SETUP)` was
  seated; the round is still `ASSIGNMENT` with the committed `TemplateID` unchanged.
- **Expected:** the retry ASSERTS `TemplateID_committed = the refresh setup's TemplateID` and
  `template_refresh_setup_committed[TemplateID_committed]` present, then CALLS `ContinueTemplateRefreshAssignmentSetup`
  — it NEVER re-enters `TemplateRefresh`, so `CloseTemplateAssignments`, candidate construction, and `TemplateCommit`
  do NOT run a second time (the committed `TemplateID` is unchanged and no old-template head is re-closed).

## TV203 — Kind-specific participant-setup retry guard (X4)

- **Procedures:** `SetupRetryEvent` (`setup_kind = PARTICIPANT_SETUP`), `PrepareParticipantsForNewRound`, `RoundAbort`.
- **Setup A (wrong phase):** a `PARTICIPANT_SETUP` retry is dispatched while `round_state = TEMPLATE_COMMITMENT`
  (non-terminal, non-`ASSIGNMENT`).
- **Expected A:** the kind-specific guard rejects it with `RoundAbort(setup_retry_wrong_round_state(...))` — the target
  procedure is NEVER called illegally.
- **Setup B (valid):** the same retry dispatched with `round_state = ASSIGNMENT`, a committed eligible `TemplateID`
  present, an unused `SetupRetryID`, and every eligible participant re-enlistable.
- **Expected B:** the retry registers `SetupRetryID`, ASSERTS the committed eligible `TemplateID`, and CALLs
  `PrepareParticipantsForNewRound`.

## TV204 — Over-budget setup retry aborts rather than stranding the round (X4)

- **Procedures:** `SetupRetryEvent`, `RoundAbort`.
- **Setup:** a non-terminal round in `ASSIGNMENT`; the retry arrives with
  `setup_retry_generation > maximum_setup_retries`.
- **Expected:** the event returns `RoundAbort(setup_retry_budget_exhausted(setup_kind))` — a DECLARED abort, NOT a
  bare `setup_retry_exhausted` no-op — and the round is never left in `ASSIGNMENT` with no controller. (If the round
  were already `ROUND_ACCEPTED` / `ROUND_ABORTED`, the terminal case returns `setup_retry_terminal_stale_noop` first,
  needing no controller.)

## TV205 — Caller captures `commit.rollback_record` and rolls back after CompleteAssignmentPhase (X5)

- **Procedures:** `ApplyRecoveryAssignmentContinuationAfterEpilogue`, `CommitRecoveryAssignmentPlan`,
  `CompleteAssignmentPhase`, `RollbackRecoveryAssignmentPlan`.
- **Setup:** a continuation whose `CommitRecoveryAssignmentPlan` returns `install_committed(rollback_record)`, and whose
  subsequent `CompleteAssignmentPhase` returns `assignment_phase_failed(reason)`.
- **Expected:** the caller captured `commit_rollback_record <- commit.rollback_record` and passes THAT record to
  `RollbackRecoveryAssignmentPlan` — never an undeclared `plan.rollback_metadata`. On `rollback_failed` it takes the
  declared `RECOVERY_INSTALL_FAILED_ABORTED` / `RoundAbort` path.

## TV206 — Assignment-creation failure is reachable through the guard, not a precondition breach (X6)

- **Procedures:** `CreatePendingAssignment`.
- **Setup:** a conforming caller with `assignment_origin = ORIGINAL` (type/shape precondition satisfied) whose `range`
  now overlaps a valid active assignment (I1 violated at call time, e.g. after a concurrent same-time mutation).
- **Expected:** the runtime guard evaluates I1 (and custody/coverage/epoch/provenance) and returns
  `assignment_creation_failed(reason = overlap_or_custody_or_provenance_or_epoch_violation)` creating NOTHING — this is
  a DECLARED, reachable disposition, not an undefined-behaviour precondition violation. A well-formed caller can drive
  EITHER `assignment_created` or `assignment_creation_failed` without ever breaching a precondition.

## TV207 — Every Stage-1X closure sets only canonical enum fields plus a `closure_detail` (X7)

- **Procedures:** `RollbackParticipantSetup`, `RollbackTemplateRefreshSetup`, `RollbackRecoveryAssignmentPlan`,
  `RangeAssignFromPlan`, `RangeReassignFromPlan`, `ReserveActivateFromPlan`.
- **Setup:** drive each closure site (setup rollback, template-refresh setup rollback, recovery-install rollback,
  range/reserve wake failure).
- **Expected:** every closure sets `status`, `custody_status`, `termination_reason`, `revocation_reason` from the
  canonical enums ONLY (`cancellation` / `wake_failure` for `termination_reason`; `assignment_revoked` for
  `revocation_reason`; `revoked` for `custody_status`; `CLOSED` for `status`), and records the descriptive token in the
  non-enum `closure_detail` (`participant_setup_rolled_back` / `template_refresh_setup_rolled_back` /
  `recovery_install_rolled_back` / `range_assign_wake_failed` / `range_reassign_wake_failed` /
  `reserve_activation_wake_failed`). NO free-text string appears in a canonical enum field.

## TV208 — A rollback T12 closes WAKING residency, charges one transition, adds no H_active (X8)

- **Procedures:** `RollbackRecoveryAssignmentPlan` / `RollbackParticipantSetup` / `RollbackTemplateRefreshSetup`,
  `ApplyMinerStateTransition`, `CommitSecurityCensus`.
- **Setup:** a miner `m` `WAKING` on a rolled-back head; the rollback departs it via `T12` at rollback `event_time`.
- **Expected:** `ApplyMinerStateTransition` CLOSES `m`'s `WAKING` residency at the rollback `event_time`, charges the
  transition energy (`E_transition` / `E_coordination`) EXACTLY once, and OPENS the `OFFLINE` residency. Because `m`
  never entered `ACTIVE_HASHING`, the departure adds NO `H_active` and changes NO `ACTIVE_HASHING` membership, so it
  triggers NO census change via `CommitSecurityCensus` (H_active / H_honest / q_adv unchanged). Energy accounting stays
  consistent with the A1 baseline; the baseline figure is not altered.

## TV209 — After a full recovery-plan rollback, no open WAKING residency survives to horizon T (X8)

- **Procedures:** `RollbackRecoveryAssignmentPlan`.
- **Setup:** a fully committed plan (every activation `WAKING`) rolled back after a post-commit failure.
- **Expected:** every affected miner's `WAKING` residency is closed at the rollback `event_time` (via `T12`), so the
  coherence check (`no item.MinerID remains WAKING on a plan-created head`) holds and `rollback_completed` is returned;
  NO open `WAKING` residency remains to be force-settled at horizon `T` (consistent with the residency single-owner
  invariant).

---

## Coverage summary

| Vector | Correction | Primary procedures |
|--------|-----------|--------------------|
| TV198 | X1/X5 | `CommitRecoveryAssignmentPlan` |
| TV199 | X1/X2/X8 | `RollbackRecoveryAssignmentPlan`, `ApplyMinerStateTransition` |
| TV200 | X1 | `RollbackRecoveryAssignmentPlan` |
| TV201 | X2 | `RollbackParticipantSetup` / `RollbackTemplateRefreshSetup` |
| TV202 | X3 | `SetupRetryEvent`, `ContinueTemplateRefreshAssignmentSetup` |
| TV203 | X4 | `SetupRetryEvent`, `PrepareParticipantsForNewRound` |
| TV204 | X4 | `SetupRetryEvent`, `RoundAbort` |
| TV205 | X5 | `ApplyRecoveryAssignmentContinuationAfterEpilogue`, `RollbackRecoveryAssignmentPlan` |
| TV206 | X6 | `CreatePendingAssignment` |
| TV207 | X7 | all six Stage-1X closure sites |
| TV208 | X8 | `ApplyMinerStateTransition`, `CommitSecurityCensus` |
| TV209 | X8 | `RollbackRecoveryAssignmentPlan` |

All twelve vectors are specified against exact procedures and preconditions in the current
`STAGE_01_PROTOCOL_PSEUDOCODE.md`; none assumes an unwritten guard, transition, edge, or result name; and all preserve
the A1 baseline `8.420833333 kWh`.
