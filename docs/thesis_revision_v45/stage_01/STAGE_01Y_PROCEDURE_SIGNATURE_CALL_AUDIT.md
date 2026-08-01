# Stage 1Y — Procedure Signature & Call-Site Audit

This audit records, for every procedure touched by Stage 1Y, the exact `INPUTS`, the exact `RETURNS` disposition set,
and (where called) that every caller passes arguments matching the signature and inspects the returned disposition
explicitly before acting on it. All signatures are quoted from the current `STAGE_01_PROTOCOL_PSEUDOCODE.md` (line
anchors approximate).

## 1. Signature table (Y-touched procedures)

| Procedure | INPUTS | RETURNS (declared result set) |
|-----------|--------|-------------------------------|
| `AbortPendingWakeForRollback` (Y5, new) | `RoundContext, MinerID, AssignmentID, assignment_version, WakeEventRef, rollback_envelope, closure_detail, coverage_custody_before_image` | `wake_abort_completed(MinerID, AssignmentID, departed_to_offline)` \| `wake_abort_failed(MinerID, AssignmentID, reason)` |
| `SetupRetryEvent` (Y1/Y2/Y3) | `RoundContext, dispatch_envelope, RoundID, setup_kind, SetupRetryID, TemplateID_at_seat, TemplateRefreshSetupID, retry_generation, reason` | `setup_retry_stale_noop` \| `setup_retry_terminal_stale_noop` \| `setup_retry_duplicate_suppressed` \| `round_aborted` \| *(the re-run target's disposition)* |
| `ContinueTemplateRefreshAssignmentSetup` (Y2/Y3/Y4) | `RoundContext, dispatch_envelope, TemplateID, TemplateRefreshSetupID, SetupRetryID, retry_generation` | `TemplateID` \| `template_refresh_retry_seated` \| `template_refresh_retry_stale_noop` \| `round_aborted` |
| `TemplateRefresh` (Y2) | `RoundContext, dispatch_envelope` | `new_TemplateID` \| `template_refresh_retry_seated` \| `template_refresh_retry_stale_noop` \| `round_aborted` |
| `RollbackRecoveryAssignmentPlan` (Y4/Y5) | `RoundContext, rollback_record` | `rollback_completed(rolled_to_offline, rolled_back_items)` \| `rollback_failed(reason)` |
| `RollbackParticipantSetup` (Y4/Y5) | `RoundContext, setup_txn` *(now also `wake_by_miner`, `before_image_by_miner`)* | `rollback_completed(rolled_to_offline)` \| `rollback_failed(reason)` |
| `RollbackTemplateRefreshSetup` (Y4/Y5) | `RoundContext, setup_txn` *(same shape)* | `rollback_completed(rolled_to_offline)` \| `rollback_failed(reason)` |
| `ApplyMinerStateTransition` (used by Y5 T12) | `MinerID, old_state, new_state, transition_envelope, reason, assignment_ref, candidate_id, propagation_id` | `transition_applied(TransitionEventID)` \| `duplicate_suppressed(TransitionEventID)` \| `illegal_stale_source(TransitionEventID)` \| `illegal_transition(TransitionEventID)` |
| `PrepareParticipantsForNewRound` (Y3/Y4) | `RoundContext, dispatch_envelope` | `participant_set_prepared` \| `participant_set_setup_retry_seated` \| `round_aborted` |
| `RunInitialise` / `RoundInitialise` (Y1/Y3) | *(as before)* | *(RunContext / per-round registries, now incl. `setup_retry_status_by_id`, `setup_retry_generation_by_scope`)* |

**Signature changes introduced by Stage 1Y:**
- `AbortPendingWakeForRollback` is added (Y5) — the one named rollback wake-abort + sole assignment-closure owner.
- `SetupRetryEvent` gains `TemplateID_at_seat` and `TemplateRefreshSetupID`, and its `setup_retry_generation` scalar is
  renamed `retry_generation` (Y2/Y3).
- `ContinueTemplateRefreshAssignmentSetup` gains `TemplateRefreshSetupID`, renames `setup_retry_generation` →
  `retry_generation`, and gains the `template_refresh_retry_stale_noop` disposition (Y2/Y3).
- `TemplateRefresh` propagates the continuation's new `template_refresh_retry_stale_noop` disposition (Y2).
- The three rollback owners take the same INPUT shape but delegate the per-miner departure/close to
  `AbortPendingWakeForRollback`; `setup_txn` gains `wake_by_miner` and `before_image_by_miner` (Y4).

## 2. Call-site agreement matrix

### `AbortPendingWakeForRollback` (Y5)

| Caller | Args match | Result inspected |
|--------|-----------|------------------|
| `RollbackParticipantSetup` | ✓ `(RoundContext, m, aid, ver, wake_by_miner[m], rollback_envelope, participant_setup_rolled_back, before_image_by_miner[m])` | ✓ `wake_abort_completed(...)` → set `rolled_to_offline` if departed; `wake_abort_failed` → `rollback_failed` |
| `RollbackTemplateRefreshSetup` | ✓ same, `closure_detail = template_refresh_setup_rolled_back` | ✓ same |
| `RollbackRecoveryAssignmentPlan` | ✓ `(RoundContext, item.MinerID, item.AssignmentID, item.assignment_version, item.WakeEventRef, item.rollback_envelope, recovery_install_rolled_back, item.coverage_custody_before_image)` | ✓ `wake_abort_completed` → add to `rolled_back_items`; `wake_abort_failed` → `rollback_failed` |

### `ApplyMinerStateTransition` — Stage-1Y T12 caller

| Caller | Args match | Result inspected |
|--------|-----------|------------------|
| `AbortPendingWakeForRollback` | ✓ `(MinerID, WAKING, OFFLINE, transition_envelope = rollback_envelope, reason = validation_abort, assignment_ref = assignment_version_ref(AssignmentID, assignment_version), null, null)` | ✓ `transition_applied` / `duplicate_suppressed` → `departed_to_offline = true`; else `wake_abort_failed` |

`reason = validation_abort` is a declared `T12` trigger (`STAGE_01_MINER_STATE_MACHINE.md` §3). No rollback passes the
assignment `termination_reason` as the transition trigger; the three rollback owners no longer call
`ApplyMinerStateTransition` directly.

### `ContinueTemplateRefreshAssignmentSetup` (Y2/Y3)

| Caller | Args match | Result inspected |
|--------|-----------|------------------|
| `TemplateRefresh` | ✓ `(..., TemplateID = new_TemplateID, TemplateRefreshSetupID, SetupRetryID = null, retry_generation = 0)` | ✓ `RETURN CALL` — disposition IS `TemplateRefresh`'s return |
| `SetupRetryEvent` (TEMPLATE_REFRESH_SETUP) | ✓ `(..., TemplateID = TemplateID_at_seat, TemplateRefreshSetupID, SetupRetryID, retry_generation)` | ✓ `RETURN CALL` — disposition IS the event's return |

### `SetupRetryEvent` targets (Y1)

| Target | Args match | Result inspected |
|--------|-----------|------------------|
| `PrepareParticipantsForNewRound` | ✓ after Y1 idempotence + Y2 identity + state/budget guards + APPLYING mark | ✓ `RETURN CALL` |
| `ContinueTemplateRefreshAssignmentSetup` | ✓ same + exact `TemplateRefreshSetupID` | ✓ `RETURN CALL` |
| `RoundAbort` | ✓ `(RoundContext, reason, dispatch_envelope, recovery_finalising = false)` | ✓ declared abort |

## 3. Cross-checks performed

1. **Idempotence precedes mutating guards.** `SetupRetryEvent` step (2) tests `applied_setup_retry_ids` /
   `setup_retry_status_by_id` BEFORE the terminal (3) and wrong-round-state (5) guards (Y1).
2. **Exact template identity.** Both `SetupRetryEvent` and `ContinueTemplateRefreshAssignmentSetup` verify
   `TemplateRefreshSetupID` against `template_refresh_setup_committed[TemplateID_at_seat]` (Y2); a scan finds no live
   "the refresh setup's TemplateID" ambient phrase.
3. **No generation shadowing.** `retry_generation` is only a scalar; `setup_retry_generation_by_scope` is only a map; a
   scan finds no `setup_retry_generation[` map indexing and no scalar/map dual use (Y3).
4. **Unconditional WAKING resolution.** The three rollback owners call `AbortPendingWakeForRollback` for every affected
   miner without a "live bound head" precondition; the coherence gate is "no affected miner remains WAKING" (Y4).
5. **One T12 trigger + one closure owner.** `reason = validation_abort` at the sole T12 rollback site; the canonical
   assignment close appears only inside `AbortPendingWakeForRollback` (Y5).
6. **Signature ↔ RETURNS ↔ call-site agreement** holds for every Y-touched procedure; the call graph resolves with 0
   dangling references and 85 defined procedures (`STAGE_01Y_PROCEDURE_CALL_GRAPH.md`).

**Result:** for every Y-touched procedure, the signature, the RETURNS disposition set, and all call sites agree.
