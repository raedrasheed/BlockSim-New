# Stage 1X — Correction Report (recovery-rollback & retry-contract lock)

Stage 1X is a narrow, documentation-only revision of the Stage-1 formal specification of **PoCol** and the idle policy
within PoCol. It closes eight defects (X1–X8) in the recovery-install rollback, the setup rollback, the template-refresh
transaction, the setup-retry contract, the plan-commit output, assignment-creation reachability, head-closure fields,
and the rollback energy/residency accounting. It changes only the five normative `STAGE_01_*` documents and adds fifteen
`STAGE_01X_*` deliverables. No executable source, configuration, DOCX, or PDF is touched; no experiment is run; the A1
baseline (`8.420833333 kWh`) is unchanged; and no Stage-1A–1W historical artifact is modified.

- **Branch:** `thesis-v45-pocol-stage1x-recovery-rollback-retry-contract-lock`
- **Parent commit:** `a73feff740e3055262bbf4ee703eb7d29600952b` (Stage 1W)

## Corrections

### X1 — `RollbackRecoveryAssignmentPlan` is a complete state transaction

`CommitRecoveryAssignmentPlan` now captures, for every committed activation, a per-item rollback pre-image
(`rollback_item = { MinerID, AssignmentID, assignment_version, WakeEventRef, pre_wake_state, rollback_envelope,
coverage_custody_before_image, kind, provenance }`) BEFORE the plan-bound constructor mutates. `RollbackRecoveryAssignmentPlan`
consumes the resulting `rollback_record` and (1) cancels every `WakeEventRef`, (2) departs each still-`WAKING` miner to
`OFFLINE` via the legal `T12` edge with the exact `assignment_ref` (never null) and the item's complete
`rollback_envelope`, (3) closes each exact head canonically, (4) restores the coverage/custody ledgers from the
before-image, and (5) verifies coherence — it can NEVER return `rollback_completed` while a miner is `WAKING` with no
live event, returning `rollback_failed(residual_partial_assignment)` instead. `ApplyRecoveryWorkAfterEpilogue` and
`ApplyRecoveryAssignmentContinuationAfterEpilogue` consume the structured result and take the
`RECOVERY_INSTALL_FAILED_ABORTED` / `RoundAbort` path on incoherence — never fabricating `UNRECOVERABLE`.
*(Audit: `STAGE_01X_RECOVERY_ROLLBACK_STATE_AUDIT.md`; vectors TV198–TV200.)*

### X2 — Every rollback `T12` is bound to the exact assignment version

`participant_setup_txn` and `refresh_setup_txn` carry `assignment_by_miner : MinerID -> (AssignmentID,
assignment_version)`, populated after `assignment_created` and before `StartWake`. `RollbackParticipantSetup` and
`RollbackTemplateRefreshSetup` iterate the map and pass `assignment_version_ref(aid, ver)` — the exact version, never
null when the miner holds a setup-created `PENDING` head. The recovery-plan rollback passes `item.assignment_version`
analogously. *(Audit: `STAGE_01X_EXACT_ASSIGNMENT_ROLLBACK_AUDIT.md`; vector TV201.)*

### X3 — Template-refresh initiation split from template-assignment retry

`TemplateRefresh` performs initiation only — old-template closure (`CloseTemplateAssignments`), candidate construction,
`TEMPLATE_REFRESH -> TEMPLATE_COMMITMENT -> ASSIGNMENT` sequencing, `TemplateCommit`, and the idempotent
`template_refresh_setup_committed[new_TemplateID]` marker — then delegates to the new
`ContinueTemplateRefreshAssignmentSetup`, which is the sole owner of the post-`TemplateCommit` assignment phase, its
rollback, and its bounded retry. A `SetupRetryEvent(TEMPLATE_REFRESH_SETUP)` resumes the continuation and never re-enters
`TemplateRefresh`, so a retry never repeats `CloseTemplateAssignments`, candidate construction, or `TemplateCommit`.
*(Audit: `STAGE_01X_TEMPLATE_REFRESH_RETRY_AUDIT.md`; vector TV202.)*

### X4 — Kind-specific, bounded `SetupRetryEvent` guards

`SetupRetryEvent` now guards per kind: `PARTICIPANT_SETUP` requires `ASSIGNMENT` + a committed eligible `TemplateID` and
calls `PrepareParticipantsForNewRound`; `TEMPLATE_REFRESH_SETUP` requires `ASSIGNMENT` + the committed `TemplateID` equal
to the refresh setup's + the closure/commit markers and calls `ContinueTemplateRefreshAssignmentSetup`.
`ROUND_INITIALISING`/`TEMPLATE_COMMITMENT` are rejected with a declared `RoundAbort`; a terminal round is a
`setup_retry_terminal_stale_noop`; an over-budget retry is a declared `RoundAbort(setup_retry_budget_exhausted)` (not a
bare `setup_retry_exhausted`); and the phase is never left in `ASSIGNMENT` with no controller. *(Audit:
`STAGE_01X_SETUP_RETRY_STATE_AUDIT.md`; vectors TV203–TV204.)*

### X5 — Commit returns the rollback record explicitly

`install_committed` becomes `install_committed(rollback_record)`. `CommitRecoveryAssignmentPlan` builds and returns the
complete `rollback_record` explicitly in every disposition (success and `install_failed_after_mutation`); the callers
capture `commit.rollback_record`; and there is no undeclared pass-by-reference `plan.rollback_metadata` (the field is
removed from the plan record and appears only in withdrawn-name comments). The result union, the RETURNS block, and all
call sites agree. *(Audit: `STAGE_01X_PLAN_COMMIT_OUTPUT_AUDIT.md`; vector TV205.)*

### X6 — Reachable `assignment_creation_failed`

`CreatePendingAssignment` PRECONDITIONS now constrain only type/shape (`assignment_origin in {ORIGINAL, REASSIGNED}`);
the runtime-varying predicates (I1 overlap, `custody != completed`, `coverage != searched`, REASSIGNED
source/provenance, RoundID/TemplateID epoch validity) are evaluated in the executable guard and yield
`assignment_creation_failed(reason)`. A conforming caller can therefore reach either disposition without a precondition
breach, so the W7-era caller failure branches are exercisable. *(Audit:
`STAGE_01X_ASSIGNMENT_CREATION_REACHABILITY_AUDIT.md`; vector TV206.)*

### X7 — Canonical closure fields + `closure_detail`

Every Stage-1X head closure sets `status`, `custody_status`, `termination_reason`, and `revocation_reason` from the
canonical enums only and records the free descriptor in the new non-enum `closure_detail`: participant setup rollback
(`termination_reason = cancellation`, `revocation_reason = assignment_revoked`,
`closure_detail = participant_setup_rolled_back`); template-refresh setup rollback
(`closure_detail = template_refresh_setup_rolled_back`); recovery-install rollback
(`closure_detail = recovery_install_rolled_back`); range/reserve wake failure (`termination_reason = wake_failure`,
`closure_detail = range_assign_wake_failed` / `range_reassign_wake_failed` / `reserve_activation_wake_failed`). No
free-text string appears in a canonical enum field. *(Audit: `STAGE_01X_CANONICAL_CLOSURE_ENUM_AUDIT.md`; vector
TV207.)*

### X8 — Rollback reconciled with energy, residency, and census

Each rollback `WAKING -> OFFLINE` runs through `ApplyMinerStateTransition`, which closes the `WAKING` residency at the
rollback `event_time`, charges the transition energy exactly once, opens the `OFFLINE` residency, adds no `H_active`,
and updates the census only via `CommitSecurityCensus` when `ACTIVE_HASHING` membership changes. Because a rolled-back
miner never entered `ACTIVE_HASHING`, the departure perturbs no `H_active`/`H_honest`/`q_adv`; and no open `WAKING`
residency survives to horizon `T`. This preserves the energy-accounting integrity underlying the A1 baseline without
altering the baseline figure. *(Audit: `STAGE_01X_ENERGY_RESIDENCY_ROLLBACK_AUDIT.md`; vectors TV208–TV209.)*

## Editorial cross-reference corrections (Stage-1X consistency)

Two stale cross-references were corrected so the normative pseudocode matches the Stage-1X contract:
- The `CreatePendingAssignment` reachability note cited `TV204`; corrected to `TV206` (TV204 is the over-budget
  setup-retry abort vector).
- The `SetupRetryEvent` seating-table descriptor named `TemplateRefresh` as the `TEMPLATE_REFRESH_SETUP` retry target;
  corrected to `ContinueTemplateRefreshAssignmentSetup` (X3/X4) with the kind-specific / bounded / idempotent wording.

## Deliverables (15 new `STAGE_01X_*` files)

1. `STAGE_01X_CORRECTION_REPORT.md` (this file)
2. `STAGE_01X_RECOVERY_ROLLBACK_STATE_AUDIT.md` (X1)
3. `STAGE_01X_EXACT_ASSIGNMENT_ROLLBACK_AUDIT.md` (X2)
4. `STAGE_01X_TEMPLATE_REFRESH_RETRY_AUDIT.md` (X3)
5. `STAGE_01X_SETUP_RETRY_STATE_AUDIT.md` (X4)
6. `STAGE_01X_PLAN_COMMIT_OUTPUT_AUDIT.md` (X5)
7. `STAGE_01X_ASSIGNMENT_CREATION_REACHABILITY_AUDIT.md` (X6)
8. `STAGE_01X_CANONICAL_CLOSURE_ENUM_AUDIT.md` (X7)
9. `STAGE_01X_ENERGY_RESIDENCY_ROLLBACK_AUDIT.md` (X8)
10. `STAGE_01X_PROCEDURE_SIGNATURE_CALL_AUDIT.md`
11. `STAGE_01X_PROCEDURE_CALL_GRAPH.md`
12. `STAGE_01X_SEMANTIC_TEST_VECTORS.md` (TV198–TV209)
13. `STAGE_01X_SUPERSESSION_REGISTER.md`
14. `STAGE_01X_CROSS_DOCUMENT_AUDIT.md`
15. `STAGE_01X_CHECKSUM_MANIFEST.sha256`

## Modified normative documents (5)

`STAGE_01_PROTOCOL_PSEUDOCODE.md`, `STAGE_01_ROUND_STATE_MACHINE.md`, `STAGE_01_INVARIANT_CATALOGUE.md`,
`STAGE_01_TERMINOLOGY.md`, `STAGE_01_TRACEABILITY_MATRIX.csv`.

## Discipline

Documentation-only; the algorithm remains **PoCol** and the mechanism remains the idle policy within PoCol; the A1
baseline `8.420833333 kWh` is unchanged; the call graph resolves with 84 procedures and 0 dangling references; and
Stage 2 is not begun.
