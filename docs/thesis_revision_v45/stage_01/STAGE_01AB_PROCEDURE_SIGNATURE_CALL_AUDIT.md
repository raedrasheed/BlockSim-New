# Stage 1AB — Procedure Signature & Call-Site Audit

This audit records, for every procedure touched by Stage 1AB, the exact `INPUTS`, the exact `RETURNS` disposition set, and
(where called) that every caller passes arguments matching the signature and inspects the returned disposition explicitly.
All signatures are quoted from the current `STAGE_01_PROTOCOL_PSEUDOCODE.md` (line anchors approximate).

## 1. Signature table (AB-touched procedures)

| Procedure | INPUTS | RETURNS (declared result set) |
|-----------|--------|-------------------------------|
| `RoundAbort` | `RoundContext, reason, dispatch_envelope, recovery_finalising = false` | `round_aborted(abort_record)` |
| `SetupRetryEvent` (AB1/AB2/AB3/AB4/AB5) | `RoundContext, dispatch_envelope, dispatched_event_ref, RoundID, setup_kind, SetupRetryID, TemplateID_at_seat, TemplateRefreshSetupID, retry_generation, reason` | `setup_retry_stale_noop(SetupRetryID)` \| `setup_retry_terminal_stale_noop(SetupRetryID)` \| `setup_retry_duplicate_suppressed(SetupRetryID)` \| `round_aborted(abort_record)` \| `participant_set_prepared` \| `participant_set_setup_retry_seated(SetupRetryID, reason)` \| `TemplateID` \| `template_refresh_retry_seated(SetupRetryID, reason)` \| `template_refresh_retry_stale_noop(TemplateRefreshSetupID)` |
| `CancelSetupRetriesForRound` (AB3/AB6) | `RoundContext, closing_RoundID, cancellation_reason, dispatch_or_run_hook_context` | `setup_retries_terminalised(closing_RoundID)` |
| `PrepareParticipantsForNewRound` (AB1) | `RoundContext, dispatch_envelope` | `participant_set_prepared` \| `participant_set_setup_retry_seated(SetupRetryID, reason)` \| `round_aborted(abort_record)` |
| `ContinueTemplateRefreshAssignmentSetup` (AB1) | `RoundContext, dispatch_envelope, TemplateID, TemplateRefreshSetupID, SetupRetryID, retry_generation` | `TemplateID` \| `template_refresh_retry_seated(SetupRetryID, reason)` \| `template_refresh_retry_stale_noop(TemplateRefreshSetupID)` \| `round_aborted(abort_record)` |
| `TemplateRefresh` (AB1) | `RoundContext, dispatch_envelope` | `new_TemplateID` \| `template_refresh_retry_seated(SetupRetryID, reason)` \| `template_refresh_retry_stale_noop(TemplateRefreshSetupID)` \| `round_aborted(abort_record)` |
| `FullRangeExhaustNoSolution` (AB1) | `RoundContext, dispatch_envelope` | `(TemplateRefresh disposition …)` \| `round_aborted(abort_record)` |

**Signature/contract changes introduced by Stage 1AB:**
- `SetupRetryEvent` gains the `dispatched_event_ref` input (AB5) and its RETURNS enumerates the exact result set with the
  shaped `round_aborted(abort_record)` once and no vague "target procedure's disposition" (AB1).
- `PrepareParticipantsForNewRound`, `ContinueTemplateRefreshAssignmentSetup`, `TemplateRefresh`, `FullRangeExhaustNoSolution`
  RETURNS shape the abort as `round_aborted(abort_record)` (AB1).
- `CancelSetupRetriesForRound` iterates `SetupRetryID`s and mutates by key (AB3); it clears a cancelled record's `event_ref`
  and asserts the closure post-conditions (AB6). Signature unchanged.
- `RoundAbort`'s signature and result are unchanged (the canonical `round_aborted(abort_record)` from Stage 1AA); Stage 1AB
  fixes the CONTRACTS that DECLARE and STORE its result, not `RoundAbort` itself.

## 2. Call-site agreement matrix

### `RoundAbort` (AB1/AB2)

| Caller | Args match | Result handling |
|--------|-----------|-----------------|
| `SetupRetryEvent` guard aborts (wrong round state / budget / incompat / AB5 integrity) | ✓ `(RoundContext, reason, dispatch_envelope, recovery_finalising = false)` | ✓ `SET disp <- CALL RoundAbort(...)` (captured, AB2) → keyed `UPDATE status <- ABORTED`, `UPDATE target_disposition <- disp` → `RETURN disp` |
| `SetupRetryEvent` step-8 classification (target abort) | n/a (result captured from the target) | ✓ `disp = round_aborted(abort_record)` → keyed `UPDATE status <- ABORTED` (or ABORTED under `terminal_closure_pending`) |
| `PrepareParticipantsForNewRound` / `ContinueTemplateRefreshAssignmentSetup` / `TemplateRefresh` / `FullRangeExhaustNoSolution` | ✓ same | ✓ `RETURN CALL RoundAbort(...)`; RETURNS lists `round_aborted(abort_record)` |
| recovery paths | ✓ `RoundAbort(reason = recovery_install_failed_aborted / floor_unrecoverable, recovery_finalising = true)` | ✓ called for effect; return their own recovery disposition (unchanged from Stage 1AA) |

### `SetupRetryEvent` (AB3/AB4/AB5) — ownership, persistence, re-read

| Aspect | Check |
|--------|-------|
| Dispatch ownership (AB5) | ✓ `(1b)` resolve → `(1c)` `IF dispatched_event_ref != rec.event_ref: RETURN setup_retry_stale_noop` (foreign; record left SEATED) → `(2)` genuine-event payload mismatch → integrity abort |
| Read-only snapshot (AB3) | ✓ `SET rec <- setup_retry_records[SetupRetryID]` used only for reads; every mutation is `UPDATE setup_retry_records[SetupRetryID].<field> <- …` |
| Capture-before-store (AB2) | ✓ every guard abort captures `disp <- CALL RoundAbort(...)` before the keyed `UPDATE`s |
| Post-target re-read (AB4) | ✓ `SET post_target_rec <- setup_retry_records[SetupRetryID]` after the target; classification reads `post_target_rec.terminal_closure_pending` |
| Seat is the only CREATE | ✓ the two seating publishes are the only `SET setup_retry_records[srid] <- setup_retry_record(...)`; all else is keyed UPDATE |

### `CancelSetupRetriesForRound` (AB3/AB6)

| Caller | Args match | Result handling |
|--------|-----------|-----------------|
| `CloseRoundAssignments` | ✓ `(RoundContext, closing_RoundID = RoundID, cancellation_reason = round_closed(disposition), dispatch_or_run_hook_context = dispatch_envelope)` | ✓ called for effect; iterates `SetupRetryID`s, keyed UPDATEs, clears `event_ref`, asserts AB6 post-conditions; returns `setup_retries_terminalised(closing_RoundID)` |

## 3. Cross-checks performed

1. **Exact abort shape.** Every propagator's RETURNS lists `round_aborted(abort_record)`; a scan finds no bare
   `round_aborted` result-contract alias (only prose comments and payload-bearing occurrences remain) (AB1).
2. **Capture-before-store.** Each `SetupRetryEvent` guard abort does `SET disp <- CALL RoundAbort(...)` before persisting
   `status <- ABORTED` / `target_disposition <- disp` by key (AB2).
3. **Keyed persistence.** No `SET rec.<field>` remains; every lifecycle mutation is a keyed `UPDATE
   setup_retry_records[SetupRetryID]`; `CancelSetupRetriesForRound` iterates ids (AB3).
4. **Post-target re-read.** `SetupRetryEvent` re-reads the persisted record and classifies on the stored
   `terminal_closure_pending` (AB4).
5. **Dispatch ownership.** `dispatched_event_ref` is an input, compared to `rec.event_ref` before payload verification;
   foreign → stale-noop (record left SEATED); genuine mismatch → integrity abort (AB5).
6. **Closure post-conditions.** `CancelSetupRetriesForRound` clears `event_ref` and asserts no SEATED record / no queued
   event remains (AB6).
7. **Signature ↔ RETURNS ↔ call-site agreement** holds for every AB-touched procedure; the call graph resolves with 0
   dangling references and 86 defined callables (`STAGE_01AB_PROCEDURE_CALL_GRAPH.md`).

**Result:** for every AB-touched procedure, the signature, the RETURNS disposition set, and all call sites agree; the abort
result contract is exact, and every setup-retry lifecycle mutation is a keyed persistent update.
