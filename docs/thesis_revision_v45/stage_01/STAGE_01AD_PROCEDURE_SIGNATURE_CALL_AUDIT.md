# Stage 1AD — Procedure Signature & Call-Site Audit

This audit records, for every procedure touched by Stage 1AD, the exact `INPUTS`, the exact `RETURNS` disposition set, and
(where called) that every caller passes arguments matching the signature and inspects the returned disposition explicitly.
All signatures are quoted from the current `STAGE_01_PROTOCOL_PSEUDOCODE.md` (line anchors approximate). The A1 baseline
(`8.420833333 kWh`) and the binding **PoCol** naming rule are preserved.

## 1. Signature table (AD-touched procedures)

| Procedure | INPUTS | RETURNS (declared result set) |
|-----------|--------|-------------------------------|
| `ScheduleEvent` (AD2/AD3/AD8) | `EventQueueContext EQ, RoundContext, event_type, target_event_time, target_microphase, envelope_fields, post_epilogue_context = null` | `scheduled(EventRef, queued_event_record)` \| `rejected_finalised_time` \| `post_horizon_event_rejected` \| `rejected_post_epilogue_not_strictly_later` \| `rejected_backward_time` |
| `ProcessEventTime` (AD2/AD4/AD5/AD7/AD8) | `RoundContext, event_time t, is_horizon, allow_empty_horizon, RunHookContext = null` | `event_time_finalised(t)` |
| `HandleDispatchIntegrityFailure` (AD8, NEW) | `RoundContext, er, record` | `dispatch_integrity_handled(er)` |
| `SetupRetryEvent` (AD2/AD4/AD5) | `RoundContext, dispatch_envelope, dispatched_event_ref, immutable_payload (RoundID, setup_kind, SetupRetryID, TemplateID_at_seat, TemplateRefreshSetupID, retry_generation, reason)` | `setup_retry_stale_noop(SetupRetryID)` \| `setup_retry_terminal_stale_noop(SetupRetryID)` \| `setup_retry_duplicate_suppressed(SetupRetryID)` \| `round_aborted(abort_record)` \| `participant_set_prepared` \| `participant_set_setup_retry_seated(SetupRetryID, reason)` \| `TemplateID` \| `template_refresh_retry_seated(SetupRetryID, reason)` \| `template_refresh_retry_stale_noop(TemplateRefreshSetupID)` |
| `CancelSetupRetriesForRound` (AD1/AD6/AD9) | `RoundContext, closing_RoundID, cancellation_reason, dispatch_or_run_hook_context` | `setup_retries_terminalised(closing_RoundID)` |
| `SetSetupRetryStatus` (AC7, unchanged) | `SetupRetryID, new_status` | `setup_retry_status_set(SetupRetryID, new_status)` \| `setup_retry_status_transition_rejected(SetupRetryID, current, new_status)` |
| `RunInitialise` (AD1) | `config` | `RunContext(... EventQueueContext = EQ ...; queued_event_registry = empty map ...)` |

**Signature/contract changes introduced by Stage 1AD:**
- `ScheduleEvent` RETURNS `scheduled(EventRef, queued_event_record)` (was `scheduled(EventRef, envelope)`) and its declared
  union now enumerates all four rejection variants (AD3); it stores the complete `immutable_payload` and asserts its
  completeness (AD2/AD8).
- `ProcessEventTime` becomes the sole queue-status owner: `QUEUED → DISPATCHING` before dispatch, `DISPATCHING → CONSUMED`
  after; it builds and threads `OrdinaryDispatchContext` (AD5) and dispatches the stored `immutable_payload` (AD2); on
  detected corruption it calls `HandleDispatchIntegrityFailure` and consumes the event (AD8).
- `HandleDispatchIntegrityFailure` is a NEW procedure (AD8): the one dispatcher-owned integrity path.
- `SetupRetryEvent` receives its payload as the stored `immutable_payload` (AD2) and `dispatched_event_ref` via the
  dispatcher-owned `OrdinaryDispatchContext` (AD5); it no longer writes any `queue_status` (AD4).
- `CancelSetupRetriesForRound` reads/mutates the central `queued_event_registry[seat_event_ref].queue_status` (AD1/AD9); it
  no longer references a per-record `event_queue_status` mirror.
- `setup_retry_record` drops the AC8 `event_queue_status` field; its queue state is
  `queued_event_registry[seat_event_ref].queue_status` (AD1).

## 2. Call-site agreement matrix

### `ScheduleEvent` (AD3) — result binding

| Caller | Args match | Result handling |
|--------|-----------|-----------------|
| both retry seating sites | ✓ | ✓ `IF r = scheduled(event_ref, record):` → store `seat_event_ref = event_ref, status = SEATED` (no queue mirror) |
| `StartWake` | ✓ | ✓ `IF seat is NOT scheduled(event_ref, record): ... RETURN wake_schedule_failed_before_transition` else `SET wake_event_ref <- event_ref` |
| `SeatRecoveryCompletion` | ✓ | ✓ `IF result = scheduled(event_ref, record):` → `due_event_ref <- event_ref` |
| `SeatRecoveryWork` | ✓ | ✓ `IF result = scheduled(event_ref, record):` → `work_due_event_ref = event_ref` |
| `CompleteSecurityRecovery` | ✓ | ✓ `IF r = scheduled(event_ref, record):` → `continuation_event_ref <- event_ref` |
| other seats (`IF … = scheduled(...)` wildcard) | ✓ | ✓ presence-only check; no field extraction |

Every result-binding caller extracts the canonical `event_ref` field; the second tuple slot is the central
`queued_event_record`. A rejection variant does not match the success pattern, so the caller takes its rejection branch (no
rejection is treated as a seat).

### `ProcessEventTime` (AD4/AD5) → dispatched handlers

| Aspect | Check |
|--------|-------|
| Queue-status lifecycle | ✓ `ASSERT record.queue_status = QUEUED`; `QUEUED → DISPATCHING` before dispatch; `DISPATCHING → CONSUMED` after; `EQ.current_event_ref` set/cleared |
| Context construction | ✓ `SET ctx <- OrdinaryDispatchContext(dispatch_envelope = record.dispatch_envelope, dispatched_event_ref = er)` |
| Stored-payload delivery (AD2) | ✓ `DISPATCH record.event_type WITH immutable_payload = record.immutable_payload, dispatch_envelope = ctx.dispatch_envelope` |
| Design B (AD5) | ✓ `dispatched_event_ref = ctx.dispatched_event_ref` passed IFF the handler's signature declares it (only `SetupRetryEvent`) |
| Corruption path (AD8) | ✓ `IF record is detected corrupt: CALL HandleDispatchIntegrityFailure(...); queue_status <- CONSUMED; CONTINUE` |

### `HandleDispatchIntegrityFailure` (AD8)

| Caller | Args match | Result handling |
|--------|-----------|-----------------|
| `ProcessEventTime` (corruption branch) | ✓ `(RoundContext, er, record)` | ✓ for-effect; the dispatcher then sets `DISPATCHING → CONSUMED` and continues the drain |

Defined once; called once. Out-edges: → `SetSetupRetryStatus` (APPLYING/ABORTED/SUPERSEDED), → `RoundAbort` (captured
`disp`). It builds the integrity envelope from the trusted `EventRef`, never the corrupt payload.

### `CancelSetupRetriesForRound` (AD9)

| Caller | Args match | Result handling |
|--------|-----------|-----------------|
| `CloseRoundAssignments` | ✓ | ✓ for-effect; defined once, called once |

Out-edge: → `SetSetupRetryStatus` (SEATED → CANCELLED for a `QUEUED` retry). Reads/mutates
`queued_event_registry[snapshot.seat_event_ref].queue_status` only; a `DISPATCHING` retry gets `terminal_closure_pending`
persisted; a `CONSUMED`/`CANCELLED` queue state is not rewritten.

## 3. Cross-checks performed

1. **One authoritative queue-state source.** The record CREATE (`ScheduleEvent`) sets `queue_status = QUEUED`; every later
   queue-state write is `queued_event_registry[*].queue_status <-` in `ProcessEventTime` (DISPATCHING, CONSUMED — incl. the
   integrity path) and `CancelSetupRetriesForRound` (CANCELLED). No `setup_retry_record.event_queue_status` field exists
   (AD1/AD4).
2. **Complete payload.** `ScheduleEvent` asserts `immutable_payload` completeness (AD8) and `ProcessEventTime` dispatches
   `record.immutable_payload` (AD2).
3. **Result union.** `ScheduleEvent`'s declared RETURNS enumerates the success + four rejection variants (AD3); every caller
   inspects it.
4. **Design B.** `dispatched_event_ref` is delivered only to `SetupRetryEvent` (AD5); no undeclared named argument is
   injected.
5. **Integrity.** `HandleDispatchIntegrityFailure` (defined once, called once) uses a complete trusted-`EventRef` envelope
   (AD8).
6. **Closure lifecycle.** `CancelSetupRetriesForRound` branches on the central queue state and its post-conditions hold on
   the registry (AD6/AD9).
7. **Signature ↔ RETURNS ↔ call-site agreement** holds for every AD-touched procedure; the call graph resolves with 0
   dangling references and 88 defined callables (`STAGE_01AD_PROCEDURE_CALL_GRAPH.md`).

**Result:** for every AD-touched procedure, the signature, the RETURNS disposition set, and all call sites agree; the queue
state has one authoritative source (the central `queued_event_registry`, owned by `ProcessEventTime`), the stored payload is
delivered verbatim, and the integrity path uses a complete trusted envelope.
