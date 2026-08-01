# Stage 1AA — Procedure Signature & Call-Site Audit

This audit records, for every procedure touched by Stage 1AA, the exact `INPUTS`, the exact `RETURNS` disposition set, and
(where called) that every caller passes arguments matching the signature and inspects the returned disposition explicitly.
All signatures are quoted from the current `STAGE_01_PROTOCOL_PSEUDOCODE.md` (line anchors approximate).

## 1. Signature table (AA-touched procedures)

| Procedure | INPUTS | RETURNS (declared result set) |
|-----------|--------|-------------------------------|
| `RoundAbort` (AA1) | `RoundContext, reason, dispatch_envelope, recovery_finalising = false` | `round_aborted(abort_record)` |
| `CancelSetupRetriesForRound` (AA2, NEW) | `RoundContext, closing_RoundID, cancellation_reason, dispatch_or_run_hook_context` | `setup_retries_terminalised(closing_RoundID)` |
| `CloseRoundAssignments` (AA2) | `RoundContext, disposition, stop_reason, dispatch_envelope, recovery_finalising = false` | `closure_record` |
| `SetupRetryEvent` (AA1/AA3) | `RoundContext, dispatch_envelope, RoundID, setup_kind, SetupRetryID, TemplateID_at_seat, TemplateRefreshSetupID, retry_generation, reason` | `setup_retry_stale_noop` \| `setup_retry_terminal_stale_noop` \| `setup_retry_duplicate_suppressed` \| `round_aborted(abort_record)` \| *(the re-run target's disposition)* |
| `ApplyMinerStateTransition` (AA4/AA5) | `MinerID, old_state, new_state, transition_envelope, reason, assignment_ref, candidate_id, propagation_id, assignment_effect_policy = EDGE_DEFAULT` | `transition_applied(TransitionEventID)` \| `duplicate_suppressed(TransitionEventID)` \| `illegal_stale_source(TransitionEventID)` \| `illegal_transition(TransitionEventID)` |
| `PrepareParticipantsForNewRound` (AA6/AA1) | `RoundContext, dispatch_envelope` | `participant_set_prepared` \| `participant_set_setup_retry_seated` \| `round_aborted` |
| `ContinueTemplateRefreshAssignmentSetup` (AA6/AA1) | `RoundContext, dispatch_envelope, TemplateID, TemplateRefreshSetupID, SetupRetryID, retry_generation` | `TemplateID` \| `template_refresh_retry_seated` \| `template_refresh_retry_stale_noop` \| `round_aborted` |
| `RollbackParticipantSetup` (AA6) | `RoundContext, setup_txn` *(= `{ rollback_envelope, rollback_items : map RollbackItemID -> setup_rollback_item }`)* | `rollback_completed(rolled_to_offline)` \| `rollback_failed(reason)` |
| `RollbackTemplateRefreshSetup` (AA6) | `RoundContext, setup_txn` *(same keyed shape)* | `rollback_completed(rolled_to_offline)` \| `rollback_failed(reason)` |
| `TemplateRefresh` (AA1) | `RoundContext, dispatch_envelope` | `new_TemplateID` \| `template_refresh_retry_seated` \| `template_refresh_retry_stale_noop` \| `round_aborted` |
| `FullRangeExhaustNoSolution` (AA1) | `RoundContext, dispatch_envelope` | *(TemplateRefresh disposition)* \| `round_aborted(abort_record)` |

**Signature/record changes introduced by Stage 1AA:**
- `RoundAbort` RETURNS the canonical `round_aborted(abort_record)` (was a bare `abort_record`) (AA1).
- `CancelSetupRetriesForRound` is a NEW procedure (AA2).
- `setup_retry_record` gains `terminal_closure_pending : bool` (default `false`) (AA2).
- `TransitionEventID` gains `assignment_effect_policy` as a field (AA4); `ApplyMinerStateTransition` gains the AA5
  legal-tuple guard (step 4b).
- `setup_rollback_item` gains `RollbackItemID`; `setup_transaction.rollback_items` becomes a map keyed by `RollbackItemID`;
  `wake_result` gains the `NOT_ATTEMPTED` value (AA6).

## 2. Call-site agreement matrix

### `RoundAbort` (AA1) — canonical propagation

| Caller | Args match | Result inspected |
|--------|-----------|------------------|
| `SetupRetryEvent` (step 6/7 guards + step 8 capture) | ✓ `(RoundContext, reason, dispatch_envelope, recovery_finalising = false)` | ✓ classifies the exact `round_aborted(abort_record)` → `rec.status = ABORTED` |
| `PrepareParticipantsForNewRound` | ✓ same | ✓ `RETURN CALL RoundAbort(...)` propagates `round_aborted` (in RETURNS union) |
| `ContinueTemplateRefreshAssignmentSetup` | ✓ same | ✓ same |
| `TemplateRefresh` | ✓ same | ✓ same |
| `FullRangeExhaustNoSolution` | ✓ same | ✓ `RETURN CALL RoundAbort(...)`; RETURNS lists `round_aborted(abort_record)` |
| recovery paths (`ApplyRecoveryWorkAfterEpilogue`, `ApplyRecoveryAssignmentContinuationAfterEpilogue`, `CompleteSecurityRecovery`) | ✓ `RoundAbort(reason = recovery_install_failed_aborted / floor_unrecoverable, ...)` | ✓ called for effect; each returns its own declared recovery result (does not surface a bare `abort_record`) |

### `CancelSetupRetriesForRound` (AA2)

| Caller | Args match | Result inspected |
|--------|-----------|------------------|
| `CloseRoundAssignments` | ✓ `(RoundContext, closing_RoundID = RoundID, cancellation_reason = round_closed(disposition), dispatch_or_run_hook_context = dispatch_envelope)` | ✓ called for effect (in-place terminalisation); returns `setup_retries_terminalised(closing_RoundID)` |

Defined once; exactly one caller. It terminalises `SEATED` → `CANCELLED` (event_ref cancelled if pending) and flags an
`APPLYING` record `terminal_closure_pending`.

### `SetupRetryEvent` (AA1/AA3) — guard order

| Aspect | Check |
|--------|-------|
| Guard order | ✓ (1) shape → (1b) resolve record → (2) payload match → (3) status-based idempotence → (4) stale/terminal terminalisation → (5) template identity → (6) target round state → (7) budget + compat → (8) SEATED→APPLYING + capture + classify |
| Stale terminalisation (AA3) | ✓ a known `SEATED` record for an advanced round → `SUPERSEDED`; for a closed round → `CANCELLED`; never left `SEATED` |
| Abort classification (AA1) | ✓ captured `disp = round_aborted(abort_record)` → `rec.status = ABORTED` (never `CANCELLED`) |
| Closure honouring (AA2) | ✓ if `rec.terminal_closure_pending`, classification forces terminal (`ABORTED`/`CANCELLED`), never `APPLIED` |

### `ApplyMinerStateTransition` (AA4/AA5)

| Aspect | Check |
|--------|-------|
| Policy in id (AA4) | ✓ `TransitionEventID` includes `assignment_effect_policy` as its final field |
| Legal-tuple guard (AA5) | ✓ step (4b): `STATE_ONLY_ROLLBACK` legal IFF `WAKING → OFFLINE` ∧ `reason = validation_abort` ∧ exact non-null `assignment_ref` ∧ `waking_origin_assignment_ref[MinerID] = assignment_version_ref(...)`; else `illegal_transition` with no mutation |
| Caller policy | ✓ every non-rollback caller omits the parameter → default `EDGE_DEFAULT`; only `AbortPendingWakeForRollback` passes `STATE_ONLY_ROLLBACK`, and its call exactly satisfies the AA5 tuple |

### The two setup rollback owners + seating procedures (AA6)

| Aspect | Check |
|--------|-------|
| Keyed create-before-StartWake | ✓ both seating procedures create the item with `RollbackItemID`, `WakeEventRef = null`, `wake_result = NOT_ATTEMPTED`, and add it under its key BEFORE `StartWake` |
| Explicit update-by-key | ✓ after `StartWake`, both update `rollback_items[rbid].wake_result <- wr` and `.WakeEventRef <- actual | returned | null` — no local-variable alias |
| Deterministic consumption | ✓ `RollbackParticipantSetup` / `RollbackTemplateRefreshSetup` iterate `SORT(KEYS(rollback_items) ascending)` and read the STORED record |

## 3. Cross-checks performed

1. **Canonical abort name.** `RoundAbort` returns `round_aborted(abort_record)`; every propagator lists and classifies it;
   a scan finds no bare `RETURN abort_record` producer and no prose-only abort alias in a RETURNS union (AA1).
2. **Terminalisation coverage.** `CloseRoundAssignments` both cancels `SetupRetryEvent` events for the round AND calls
   `CancelSetupRetriesForRound`; a `SEATED` record becomes `CANCELLED`; an `APPLYING` record is flagged and finished by its
   handler (AA2).
3. **Record-before-stale order.** `SetupRetryEvent` resolves + payload-matches BEFORE the stale-`RoundID` check; a known
   `SEATED` record cannot remain `SEATED` after a stale dispatch (AA3).
4. **Policy identity.** `assignment_effect_policy` is a `TransitionEventID` field; the replay guard cannot alias
   differing-policy transitions (AA4).
5. **Tuple guard.** `STATE_ONLY_ROLLBACK` is rejected off the exact rollback tuple with no mutation; the only accepting
   call site is `AbortPendingWakeForRollback` (AA5).
6. **Keyed storage.** `rollback_items` is a map keyed by `RollbackItemID`; items are created `NOT_ATTEMPTED` and updated
   by key; rollback consumes the stored record; no residual `ADD item to ... rollback_items` / `SET item.wake_result` /
   `SET item.WakeEventRef` pattern remains (AA6).
7. **Signature ↔ RETURNS ↔ call-site agreement** holds for every AA-touched procedure; the call graph resolves with 0
   dangling references and 86 defined callables (`STAGE_01AA_PROCEDURE_CALL_GRAPH.md`).

**Result:** for every AA-touched procedure, the signature, the RETURNS disposition set, and all call sites agree.
