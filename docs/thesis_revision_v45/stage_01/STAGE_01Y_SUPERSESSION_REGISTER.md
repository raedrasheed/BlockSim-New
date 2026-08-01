# Stage 1Y — Supersession Register

Stage 1Y supersedes specific Stage-1W/1X statements about the setup-retry guard order, the template-refresh retry
identity, the retry-generation registry, the rollback resolution of affected `WAKING` miners, and the rollback `T12`
trigger / assignment-closure ownership. Each row records the SUPERSEDED statement, the SUPERSEDING Stage-1Y statement,
and the authoritative location in the current `STAGE_01_PROTOCOL_PSEUDOCODE.md` / `STAGE_01_MINER_STATE_MACHINE.md`
(line anchors approximate). No Stage-1A–1X lettered artifact (`STAGE_01[A-X]_*`) is modified; the historical layers
remain frozen, and this register is the sole record of what Stage 1Y overrides.

## 1. Superseded → superseding statements

| # | Superseded (Stage 1W/1X) | Superseding (Stage 1Y) | Authoritative location |
|--:|---------------------------|-------------------------|------------------------|
| Y1 | `SetupRetryEvent` checked the wrong-round-state abort (and terminal) BEFORE the idempotence guard, so a replay of a retry that already succeeded and moved the round to `HASHING` could `RoundAbort` | The canonical guard order checks EXACT-replay idempotence BEFORE the terminal and wrong-round-state guards; a post-success replay returns `setup_retry_duplicate_suppressed`, never `RoundAbort`; a `SetupRetryStatus` enum + `setup_retry_status_by_id` records the retry lifecycle | `SetupRetryEvent` (~L1823) |
| Y2 | `SetupRetryEvent` / `ContinueTemplateRefreshAssignmentSetup` referred to "the refresh setup's TemplateID" as an ambient value | The retry payload carries `TemplateID_at_seat` + `TemplateRefreshSetupID = (RoundID, committed_new_TemplateID)` explicitly, and both procedures verify the exact `TemplateRefreshSetupID` against `template_refresh_setup_committed` on the initial invocation and every retry; a stale-`TemplateID` retry takes a declared stale disposition | `SetupRetryEvent` (~L1823); `ContinueTemplateRefreshAssignmentSetup` (~L4880); `TemplateRefresh` (~L4844) |
| Y3 | `setup_retry_generation` was used BOTH as a scalar input and as a map `setup_retry_generation[(RoundID, setup_kind)]` (identifier shadowing) | The SCALAR `retry_generation` and the DISTINCT map `setup_retry_generation_by_scope` `(RoundID, setup_kind, TemplateRefreshSetupID_or_null)` are separate identifiers; `SetupRetryID` carries the complete scope | `SetupRetryEvent`, `PrepareParticipantsForNewRound`, `ContinueTemplateRefreshAssignmentSetup`, `RoundInitialise` |
| Y4 | The rollback departed a miner only `IF miner_state = WAKING AND AssignmentID is the miner's bound live head`, and the recovery-plan coherence gate was "no miner WAKING on a plan-created head" | Every affected `WAKING` miner is resolved UNCONDITIONALLY (independent of whether the head is still live); the coherence gate is "no affected miner remains `WAKING`"; a rollback that cannot resolve an affected `WAKING` miner returns `rollback_failed` and the caller aborts the install | `RollbackRecoveryAssignmentPlan` (~L3794); `RollbackParticipantSetup` (~L1767); `RollbackTemplateRefreshSetup` (~L1800) |
| Y5 | Rollback departed a `WAKING` miner via `T12` with `reason = cancellation` (the assignment `termination_reason` used as the transition trigger), and the assignment close was open-coded in each rollback caller | The ONE named `AbortPendingWakeForRollback` departs via the authoritative `T12` `ValidationAbort` trigger (`reason = validation_abort`), is the SINGLE owner of the canonical assignment close, and the transition hook changes miner state only for this form — the hook and the operation never both close the same assignment | `AbortPendingWakeForRollback` (~L1709); `STAGE_01_MINER_STATE_MACHINE.md` §3.3 |

## 2. Companion normative-document supersessions

| Document | Superseding Stage-1Y addendum |
|----------|-------------------------------|
| `STAGE_01_MINER_STATE_MACHINE.md` | §3.3 Stage-1Y addendum — the `T12` `ValidationAbort` rollback form and its single closure owner (supersedes the W/X description of the rollback edge as a bare `T12` with `reason = cancellation`) |
| `STAGE_01_ROUND_STATE_MACHINE.md` | §3.10c Stage-1Y addendum (Y1–Y5); §3.10a/§3.10b retained as the frozen W/X layers |
| `STAGE_01_INVARIANT_CATALOGUE.md` | I16 Stage-1Y clause (Y1–Y5) |
| `STAGE_01_TERMINOLOGY.md` | Stage-1Y terminology addendum (`SetupRetryStatus`, `TemplateRefreshSetupID`, `retry_generation` vs `setup_retry_generation_by_scope`, `wake_by_miner`/`before_image_by_miner`, `AbortPendingWakeForRollback`) |
| `STAGE_01_TRACEABILITY_MATRIX.csv` | Rows R178–R183 (Y1–Y5 + the TV210–TV218 block) |

## 3. Coverage note on the frozen Stage-1X semantic vectors (Y7)

The frozen `STAGE_01X_SEMANTIC_TEST_VECTORS.md` (TV198–TV209) did NOT cover all mandatory Stage-1X scenarios that
independent review subsequently required — specifically: a setup-retry replay AFTER a successful `HASHING` transition
(idempotence-before-wrong-state-abort); a template-refresh retry carrying and resolving its EXACT `TemplateID_at_seat` /
`TemplateRefreshSetupID` (and the stale-older-`TemplateID` case); the scalar-vs-map retry-generation ownership; a
rollback of an affected `WAKING` miner whose head is already `CLOSED`/unbound; and the single-owner canonical close via
the authoritative `ValidationAbort` `T12` trigger. Stage-1Y's **TV210–TV218** provide the missing executable coverage.
The Stage-1X artifacts are frozen and are NOT edited; this register records the gap and its Stage-1Y closure.

## 4. Freeze statement

Stage-1A through Stage-1X lettered artifacts (`STAGE_01[A-X]_*`) are byte-identical to the Stage-1X parent commit
(`1fd776fd79f469de920194dccdebebede4a35a9e`). Stage 1Y modifies only the six normative `STAGE_01_*` documents and adds
the twelve `STAGE_01Y_*` deliverables; every override of a prior-letter statement is recorded in this register.
