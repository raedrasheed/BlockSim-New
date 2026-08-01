# Stage 1X — Supersession Register

Stage 1X supersedes specific Stage-1U/1V/1W statements about recovery-install rollback, setup rollback, the
template-refresh transaction, the setup-retry contract, the plan-commit output, assignment-creation reachability, head
closure fields, and the rollback energy/residency accounting. Each row records the SUPERSEDED statement, the SUPERSEDING
Stage-1X statement, and the authoritative location in the current `STAGE_01_PROTOCOL_PSEUDOCODE.md` (line anchors
approximate). No Stage-1A–1W lettered artifact (`STAGE_01[A-W]_*`) is modified; the historical layers remain frozen, and
this register is the sole record of what Stage 1X overrides.

## 1. Superseded → superseding statements

| # | Superseded (Stage 1U/1V/1W) | Superseding (Stage 1X) | Authoritative location |
|--:|------------------------------|-------------------------|------------------------|
| X1 | `RollbackRecoveryAssignmentPlan` reverts a partially/fully committed plan (U5/W-era) treating the plan object as the rollback source | It is a COMPLETE state transaction over an explicit `rollback_record` of per-item pre-images; it cancels every `WakeEventRef`, departs each still-`WAKING` miner to `OFFLINE` via legal `T12`, closes each exact head, restores the ledgers, and can never return `rollback_completed` while a miner is `WAKING` with no live event | `RollbackRecoveryAssignmentPlan` (~L3695); `CommitRecoveryAssignmentPlan` `created_items` (~L3621) |
| X2 | Setup rollback (W1/W2/V8) departs a `WAKING` participant to `OFFLINE` via `T12` with an unversioned / possibly-null `assignment_ref` | The setup transaction carries `assignment_by_miner : MinerID -> (AssignmentID, assignment_version)`; every rollback `T12` passes `assignment_version_ref(aid, ver)` — the exact version, never null when a head is held | `PrepareParticipantsForNewRound` (~L1623); `ContinueTemplateRefreshAssignmentSetup` (~L4771); `RollbackParticipantSetup` (~L1698); `RollbackTemplateRefreshSetup` (~L1732) |
| X3 | `TemplateRefresh` (W3) owns closure + construction + `TemplateCommit` AND the assignment phase AND its rollback/retry; a `TEMPLATE_REFRESH_SETUP` retry re-invokes `TemplateRefresh` | `TemplateRefresh` performs INITIATION only (closure + construction + `TemplateCommit` + idempotent `template_refresh_setup_committed` marker) and delegates to the new `ContinueTemplateRefreshAssignmentSetup`, which is the sole owner of the assignment phase, its rollback, and its bounded retry; a `TEMPLATE_REFRESH_SETUP` retry resumes the continuation and never re-closes / re-commits | `TemplateRefresh` (~L4708); `ContinueTemplateRefreshAssignmentSetup` (~L4744) |
| X4 | `SetupRetryEvent` (W8) uses a shared multi-state guard and returns `setup_retry_exhausted` when over budget | Kind-specific guards: both targets require `ASSIGNMENT` (`ROUND_INITIALISING`/`TEMPLATE_COMMITMENT` rejected); `PARTICIPANT_SETUP` → `PrepareParticipantsForNewRound`, `TEMPLATE_REFRESH_SETUP` → `ContinueTemplateRefreshAssignmentSetup`; an over-budget retry is a declared `RoundAbort(setup_retry_budget_exhausted)`, a terminal round is a `setup_retry_terminal_stale_noop`, and the phase is never left in `ASSIGNMENT` with no controller | `SetupRetryEvent` (~L1747) |
| X5 | `CommitRecoveryAssignmentPlan` returns a bare `install_committed`, with rollback carried by an implicit `plan.rollback_metadata` | `install_committed(rollback_record)`: the commit builds and RETURNS the complete `rollback_record` explicitly in every disposition; callers capture `commit.rollback_record`; no `plan.rollback_metadata` field exists (only withdrawn-name comments remain) | `CommitRecoveryAssignmentPlan` (~L3682); callers (~L3020, ~L3498, ~L3528) |
| X6 | `CreatePendingAssignment` (W7) lists the runtime-varying protocol-validity predicates (I1, custody, coverage, provenance, epoch) among its PRECONDITIONS, so `assignment_creation_failed` is unreachable without a precondition breach | PRECONDITIONS constrain only type/shape (`assignment_origin in {ORIGINAL, REASSIGNED}`); the runtime predicates move into the executable guard and yield `assignment_creation_failed(reason)`, so a conforming caller can reach either disposition | `CreatePendingAssignment` (~L1272) |
| X7 | Rollback / wake-failure closures set descriptive tokens (e.g. `range_assign_wake_failed`) directly in `termination_reason` / `revocation_reason` | Every Stage-1X closure sets `status`/`custody_status`/`termination_reason`/`revocation_reason` from the canonical enums only and records the free descriptor in the new non-enum `closure_detail`; no free-text string appears in a canonical enum field | assignment record §0.8 `closure_detail`; `RollbackParticipantSetup` (~L1704), `RollbackTemplateRefreshSetup` (~L1737), `RollbackRecoveryAssignmentPlan` (~L3720), `RangeAssignFromPlan` (~L1958), `RangeReassignFromPlan` (~L3992), `ReserveActivateFromPlan` (~L3126) |
| X8 | Rollback departure of a `WAKING` miner (W2) described only as a legal-edge transition, without reconciling residency/energy/census | Each rollback `WAKING -> OFFLINE` runs through `ApplyMinerStateTransition`, which closes the `WAKING` residency at the rollback `event_time`, charges the transition energy once, opens `OFFLINE`, adds no `H_active`, and changes the census only via `CommitSecurityCensus` on an `ACTIVE_HASHING` membership change; no open `WAKING` residency survives to horizon `T` | `RollbackRecoveryAssignmentPlan` X8 note (~L3705); `ApplyMinerStateTransition` (F6) |

## 2. Companion normative-document supersessions

| Document | Superseding Stage-1X addendum |
|----------|-------------------------------|
| `STAGE_01_ROUND_STATE_MACHINE.md` | §3.10b Stage-1X addendum (X1–X8 blocks) supersedes the §3.10a Stage-1W statements it names; §3.10a is retained as the frozen W-era layer |
| `STAGE_01_INVARIANT_CATALOGUE.md` | I16 Stage-1X clause (X1–X8) extends the recovery-rollback/retry invariant |
| `STAGE_01_TERMINOLOGY.md` | Stage-1X terminology addendum (`rollback_record`/`rollback_item`, `assignment_by_miner`, `ContinueTemplateRefreshAssignmentSetup`, `TemplateRefreshSetupID`/`template_refresh_setup_committed`, kind-specific `SetupRetryEvent`, `install_committed(rollback_record)`, reachable `assignment_creation_failed`, canonical closure fields + `closure_detail`) |
| `STAGE_01_TRACEABILITY_MATRIX.csv` | Rows R169–R177 (X1–X8 + the TV198–TV209 block) |

## 3. Historical-layer residue (recorded, not modified)

The following W/V-era descriptive residue remains in the frozen historical layers; it is SUPERSEDED by the Stage-1X
statements above and is recorded here rather than edited, preserving the historical-layer discipline:

- `STAGE_01_ROUND_STATE_MACHINE.md` §3.10a **V5** paragraph still uses the word `rollback_metadata` descriptively; the
  authoritative §3.10b **X5** block withdraws the field. This is superseded historical-layer prose, not a live-contract
  divergence (the executable pseudocode has no `plan.rollback_metadata`).

## 4. Freeze statement

Stage-1A through Stage-1W lettered artifacts (`STAGE_01[A-W]_*`) are byte-identical to the Stage-1W parent commit
(`a73feff740e3055262bbf4ee703eb7d29600952b`). Stage 1X modifies only the five normative `STAGE_01_*` documents and adds
the fifteen `STAGE_01X_*` deliverables; every override of a prior-letter statement is recorded in this register.
