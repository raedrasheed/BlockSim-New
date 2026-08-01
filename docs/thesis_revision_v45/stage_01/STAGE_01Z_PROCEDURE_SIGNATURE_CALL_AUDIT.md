# Stage 1Z — Procedure Signature & Call-Site Audit

This audit records, for every procedure touched by Stage 1Z, the exact `INPUTS`, the exact `RETURNS` disposition set, and
(where called) that every caller passes arguments matching the signature and inspects the returned disposition explicitly.
All signatures are quoted from the current `STAGE_01_PROTOCOL_PSEUDOCODE.md` (line anchors approximate).

## 1. Signature table (Z-touched procedures)

| Procedure | INPUTS | RETURNS (declared result set) |
|-----------|--------|-------------------------------|
| `ApplyMinerStateTransition` (Z4/Z5) | `MinerID, old_state, new_state, transition_envelope, reason, assignment_ref, candidate_id, propagation_id, assignment_effect_policy = EDGE_DEFAULT` | `transition_applied(TransitionEventID)` \| `duplicate_suppressed(TransitionEventID)` \| `illegal_stale_source(TransitionEventID)` \| `illegal_transition(TransitionEventID)` |
| `AbortPendingWakeForRollback` (Z3/Z4/Z5) | `RoundContext, MinerID, AssignmentID, assignment_version, WakeEventRef (\| null), rollback_envelope, closure_detail, coverage_custody_before_image` | `wake_abort_completed(MinerID, AssignmentID, departed_to_offline)` \| `wake_abort_failed(MinerID, AssignmentID, reason)` |
| `SetupRetryEvent` (Z1) | `RoundContext, dispatch_envelope, RoundID, setup_kind, SetupRetryID, TemplateID_at_seat, TemplateRefreshSetupID, retry_generation, reason` | `setup_retry_stale_noop` \| `setup_retry_terminal_stale_noop` \| `setup_retry_duplicate_suppressed` \| `round_aborted` \| *(the re-run target's disposition)* |
| `RollbackParticipantSetup` (Z6) | `RoundContext, setup_txn` *(= `{ rollback_envelope, rollback_items:[setup_rollback_item] }`)* | `rollback_completed(rolled_to_offline)` \| `rollback_failed(reason)` |
| `RollbackTemplateRefreshSetup` (Z6) | `RoundContext, setup_txn` *(same shape)* | `rollback_completed(rolled_to_offline)` \| `rollback_failed(reason)` |
| `RollbackRecoveryAssignmentPlan` (uses Z4/Z5 via the named op) | `RoundContext, rollback_record` | `rollback_completed(rolled_to_offline, rolled_back_items)` \| `rollback_failed(reason)` |
| `PrepareParticipantsForNewRound` (Z1/Z2/Z3/Z6) | `RoundContext, dispatch_envelope` | `participant_set_prepared` \| `participant_set_setup_retry_seated` \| `round_aborted` |
| `ContinueTemplateRefreshAssignmentSetup` (Z1/Z2/Z3/Z6) | `RoundContext, dispatch_envelope, TemplateID, TemplateRefreshSetupID, SetupRetryID, retry_generation` | `TemplateID` \| `template_refresh_retry_seated` \| `template_refresh_retry_stale_noop` \| `round_aborted` |
| `StartWake` (Z3/Z5) | `RoundContext, MinerID, target_assignment, from_state, scheduling_context` | `wake_seated(...)` \| `wake_schedule_failed_before_transition(reason)` \| `wake_transition_failed_after_seat(reason, WakeEventRef)` |
| `RunInitialise` (Z1/Z5) | `config` | `RunContext(... setup_retry_records, waking_origin_assignment_ref, maximum_setup_retries)` |

**Signature/record changes introduced by Stage 1Z:**
- `ApplyMinerStateTransition` gains `assignment_effect_policy = EDGE_DEFAULT` (Z4) and sets/clears
  `waking_origin_assignment_ref` in its atomic apply (Z5).
- `AbortPendingWakeForRollback`'s `WakeEventRef` is now explicitly nullable (Z3); it passes `STATE_ONLY_ROLLBACK` (Z4) and
  verifies the wake-origin binding (Z5).
- `setup_transaction` becomes `{ rollback_envelope, rollback_items:[setup_rollback_item] }` (Z6), replacing the Y-era
  parallel maps; the two rollback owners iterate `rollback_items`.
- The retry registry becomes `setup_retry_records : SetupRetryID -> setup_retry_record` (Z1), replacing
  `applied_setup_retry_ids` + `setup_retry_status_by_id`.

## 2. Call-site agreement matrix

### `AbortPendingWakeForRollback` (Z3/Z4/Z5/Z6)

| Caller | Args match | Result inspected |
|--------|-----------|------------------|
| `RollbackParticipantSetup` | ✓ `(..., WakeEventRef = item.WakeEventRef (\| null), coverage_custody_before_image = item.before_image, closure_detail = participant_setup_rolled_back)` | ✓ `wake_abort_completed` → set `rolled_to_offline`; `wake_abort_failed` → `rollback_failed` |
| `RollbackTemplateRefreshSetup` | ✓ same, `closure_detail = template_refresh_setup_rolled_back` | ✓ same |
| `RollbackRecoveryAssignmentPlan` | ✓ `(..., WakeEventRef = item.WakeEventRef, coverage_custody_before_image = item.coverage_custody_before_image, closure_detail = recovery_install_rolled_back)` | ✓ same |

### `ApplyMinerStateTransition` (Z4) — `assignment_effect_policy`

| Caller | Args match | Result inspected |
|--------|-----------|------------------|
| `AbortPendingWakeForRollback` | ✓ passes `assignment_effect_policy = STATE_ONLY_ROLLBACK` | ✓ `transition_applied` / `duplicate_suppressed` → departed; else `wake_abort_failed` |
| every other caller (`StartWake`, `WakeCompleteEvent`, `MinerRegister`, `LeaseExpiry`, setup/close paths, …) | ✓ omits the parameter → default `EDGE_DEFAULT` | for-effect / branch as before |

`STATE_ONLY_ROLLBACK` appears at exactly one call site (inside `AbortPendingWakeForRollback`); every other transition uses
`EDGE_DEFAULT`, so the hook applies the edge's assignment-status change everywhere except the rollback form.

### `SetupRetryEvent` (Z1) — status lifecycle

| Aspect | Check |
|--------|-------|
| Duplicate guard | ✓ reads `setup_retry_records[SetupRetryID]`; suppresses IFF `status != SEATED`; a SEATED record's first dispatch runs |
| First dispatch | ✓ atomically `rec.status <- APPLYING` before invoking the target |
| Capture result | ✓ `SET disp <- CALL target(...)` (no direct `RETURN CALL`); classify → `APPLIED` / `SUPERSEDED` / `ABORTED` / `CANCELLED` |
| Terminal / stale / abort exits | ✓ set `rec.status` (`CANCELLED` / `ABORTED`) and `rec.target_disposition` before returning |

### Seating publish (Z1)

| Site | Check |
|------|-------|
| `PrepareParticipantsForNewRound` | ✓ on `scheduled(event_ref)`, ATOMICALLY publishes `setup_retry_records[srid]` with `status = SEATED` |
| `ContinueTemplateRefreshAssignmentSetup` | ✓ same |

### `StartWake` (Z3/Z5)

| Aspect | Check |
|--------|-------|
| Nullable wake recording | ✓ the seating loops set `item.WakeEventRef` to the actual ref (`wake_seated`), the returned ref (`wake_transition_failed_after_seat`), or null (`wake_schedule_failed_before_transition`) |
| Wake-origin set | ✓ StartWake's `ApplyMinerStateTransition(..., from_state, WAKING, assignment_ref = target_assignment)` triggers the hook's `waking_origin_assignment_ref` set |

## 3. Cross-checks performed

1. **Status-based duplicate guard.** `SetupRetryEvent` tests `rec.status != SEATED`, never mere presence (Z1); a scan finds
   no `applied_setup_retry_ids` / `setup_retry_status_by_id` in live code.
2. **Before-image before creation.** Both seating loops capture `before_image` (or `coverage_custody_before_image`) BEFORE
   `CreatePendingAssignment` (Z2).
3. **Nullable wake.** `AbortPendingWakeForRollback` cancels `IF WakeEventRef != null AND ... pending`; no live indexing of
   an absent map entry remains (Z3).
4. **One assignment-effect owner.** `STATE_ONLY_ROLLBACK` at the single rollback site; the hook's step (5c) is gated on
   `assignment_effect_policy = EDGE_DEFAULT` (Z4).
5. **Wake-origin binding.** Set on WAKING entry, cleared on WAKING exit in the hook; verified in
   `AbortPendingWakeForRollback` before the T12 (Z5).
6. **Centralised item.** `setup_transaction.rollback_items` iterated by both setup rollbacks; no parallel-map field
   remains in live code (Z6).
7. **Signature ↔ RETURNS ↔ call-site agreement** holds for every Z-touched procedure; the call graph resolves with 0
   dangling references and 85 defined procedures (`STAGE_01Z_PROCEDURE_CALL_GRAPH.md`).

**Result:** for every Z-touched procedure, the signature, the RETURNS disposition set, and all call sites agree.
