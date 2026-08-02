# Stage 1AC — Procedure Signature & Call-Site Audit

This audit records, for every procedure touched by Stage 1AC, the exact `INPUTS`, the exact `RETURNS` disposition set, and
(where called) that every caller passes arguments matching the signature and inspects the returned disposition explicitly.
All signatures are quoted from the current `STAGE_01_PROTOCOL_PSEUDOCODE.md` (line anchors approximate).

## 1. Signature table (AC-touched procedures)

| Procedure | INPUTS | RETURNS (declared result set) |
|-----------|--------|-------------------------------|
| `ScheduleEvent` (AC1) | `EventQueueContext EQ, RoundContext, event_type, target_event_time, target_microphase, envelope_fields, post_epilogue_context = null` | `scheduled(EventRef, envelope)` \| `rejected_finalised_time` \| `post_horizon_event_rejected` \| `rejected_post_epilogue_not_strictly_later` \| `rejected_backward_time` |
| `ProcessEventTime` (AC2) | `RoundContext, event_time t, is_horizon, allow_empty_horizon, RunHookContext = null` | `event_time_finalised(t)` |
| `SetupRetryEvent` (AC2/AC3/AC4/AC5/AC6/AC8) | `RoundContext, dispatch_envelope, dispatched_event_ref, RoundID, setup_kind, SetupRetryID, TemplateID_at_seat, TemplateRefreshSetupID, retry_generation, reason` | `setup_retry_stale_noop(SetupRetryID)` \| `setup_retry_terminal_stale_noop(SetupRetryID)` \| `setup_retry_duplicate_suppressed(SetupRetryID)` \| `round_aborted(abort_record)` \| `participant_set_prepared` \| `participant_set_setup_retry_seated(SetupRetryID, reason)` \| `TemplateID` \| `template_refresh_retry_seated(SetupRetryID, reason)` \| `template_refresh_retry_stale_noop(TemplateRefreshSetupID)` |
| `SetSetupRetryStatus` (AC7, NEW) | `SetupRetryID, new_status` | `setup_retry_status_set(SetupRetryID, new_status)` \| `setup_retry_status_transition_rejected(SetupRetryID, current, new_status)` |
| `CancelSetupRetriesForRound` (AC6/AC7/AC8) | `RoundContext, closing_RoundID, cancellation_reason, dispatch_or_run_hook_context` | `setup_retries_terminalised(closing_RoundID)` |
| `RunInitialise` (AC2) | `config` | `RunContext(... EventQueueContext = EQ with current_event_ref = null ...)` |

**Signature/contract changes introduced by Stage 1AC:**
- `ScheduleEvent` RETURNS `scheduled(EventRef, envelope)` (was `scheduled(envelope)`) (AC1).
- `EventQueueContext` gains `current_event_ref : EventRef | null`; `ProcessEventTime` sets/injects/clears it (AC2).
- `SetupRetryEvent`'s `dispatched_event_ref` is now dispatcher-supplied (AC2), a mandatory input; its guard order is
  reordered (AC3), scoped to the immutable record (AC4/AC5), and every status change routes through `SetSetupRetryStatus`.
- `SetSetupRetryStatus` is a NEW procedure (AC7): the sole status writer + transition guard.
- `setup_retry_record` replaces `event_ref` with `seat_event_ref : EventRef` + `event_queue_status : EventQueueStatus`
  (AC8).

## 2. Call-site agreement matrix

### `ScheduleEvent` (AC1) — result binding

| Caller | Args match | Result handling |
|--------|-----------|-----------------|
| both retry seating sites | ✓ | ✓ `IF r = scheduled(event_ref, envelope):` → store `seat_event_ref = event_ref`, `event_queue_status = QUEUED` |
| `StartWake` | ✓ | ✓ `IF seat is NOT scheduled(event_ref, envelope): ...` else `SET wake_event_ref <- event_ref` |
| `SeatRecoveryCompletion` | ✓ | ✓ `IF result = scheduled(event_ref, envelope):` → `due_event_ref <- event_ref` |
| `SeatRecoveryWork` | ✓ | ✓ `IF result = scheduled(event_ref, envelope):` → `work_due_event_ref = event_ref` |
| `CompleteSecurityRecovery` | ✓ | ✓ `IF r = scheduled(event_ref, envelope):` → `continuation_event_ref <- event_ref` |
| other seats (`IF … = scheduled(...)` wildcard) | ✓ | ✓ presence-only check; no field extraction |

### `ProcessEventTime` (AC2) → `SetupRetryEvent`

| Aspect | Check |
|--------|-------|
| EventRef injected | ✓ `SET EQ.current_event_ref <- EventRef(e)` before dispatch; `DISPATCH e WITH dispatch_envelope = dispatch_envelope, dispatched_event_ref = EQ.current_event_ref`; cleared after |
| Mandatory input | ✓ `dispatched_event_ref` is in the `SetupRetryEvent` INPUTS; the dispatch contract always supplies it (TV245) |

### `SetSetupRetryStatus` (AC7)

| Caller | Args match | Result handling |
|--------|-----------|-----------------|
| `SetupRetryEvent` (all status changes) | ✓ `(SetupRetryID, new_status)` | ✓ each transition is legal under the table (SEATED→APPLYING/CANCELLED/SUPERSEDED; APPLYING→APPLIED/SUPERSEDED/CANCELLED/ABORTED) |
| `CancelSetupRetriesForRound` | ✓ `(srid, CANCELLED)` (SEATED → CANCELLED) | ✓ for-effect; an APPLYING record is left (terminal_closure_pending) |

Defined once; the ONLY `setup_retry_records[*].status <-` write is inside `SetSetupRetryStatus`.

## 3. Cross-checks performed

1. **Canonical EventRef.** `ScheduleEvent` returns `scheduled(EventRef, envelope)`; no bare `scheduled(event_ref)` (no
   envelope) remains; every result-binding caller extracts the canonical `event_ref` (AC1).
2. **Dispatcher-owned ref.** `ProcessEventTime` sets/injects/clears `EQ.current_event_ref`; `SetupRetryEvent` reads
   `dispatched_event_ref` (mandatory input), not its payload (AC2).
3. **Guard order.** Ownership → non-SEATED replay → stale/closed (immutable record) → payload integrity → target guards
   (AC3/AC4/AC5).
4. **Legal status path.** Every abort goes SEATED → APPLYING → ABORTED via `SetSetupRetryStatus`; no straight
   SEATED → ABORTED; no terminal → terminal (AC6/AC7).
5. **Status guard.** `SetSetupRetryStatus` is the sole status writer and rejects illegal transitions with no mutation
   (AC7).
6. **Identity vs queue state.** Ownership uses `rec.seat_event_ref`; cancellation/consumption change only
   `event_queue_status`; `seat_event_ref` is never erased (AC8).
7. **Signature ↔ RETURNS ↔ call-site agreement** holds for every AC-touched procedure; the call graph resolves with 0
   dangling references and 87 defined callables (`STAGE_01AC_PROCEDURE_CALL_GRAPH.md`).

**Result:** for every AC-touched procedure, the signature, the RETURNS disposition set, and all call sites agree; the
EventRef type is canonical and dispatcher-threaded, and every setup-retry status change is a guarded legal transition.
