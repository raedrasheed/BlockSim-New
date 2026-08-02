# Stage 1AE — Procedure Signature & Call-Site Audit

This audit records, for every procedure touched by Stage 1AE, the exact `INPUTS`, the exact `RETURNS` disposition set, and
(where called) that every caller passes arguments matching the signature and inspects the returned disposition explicitly.
All signatures are quoted from the current `STAGE_01_PROTOCOL_PSEUDOCODE.md` (line anchors approximate). The A1 baseline
(`8.420833333 kWh`) and the binding **PoCol** naming rule are preserved.

## 1. Signature table (AE-touched procedures)

| Procedure | INPUTS | RETURNS (declared result set) |
|-----------|--------|-------------------------------|
| `CancelQueuedEvent` (AE1, NEW) | `EventRef, cancellation_reason, cancellation_context` | `cancellation_unknown_event(EventRef)` \| `event_cancelled(EventRef)` \| `event_already_dispatching(EventRef)` \| `cancellation_terminal_noop(EventRef)` |
| `ScheduleEvent` (AE7/AE8) | `EventQueueContext EQ, RoundContext, event_type, target_event_time, target_microphase, envelope_fields, post_epilogue_context = null` | `scheduled(EventRef, queued_event_record)` \| `rejected_finalised_time` \| `post_horizon_event_rejected` \| `rejected_post_epilogue_not_strictly_later` \| `rejected_backward_time` \| `rejected_payload_schema_mismatch(event_type, missing_or_invalid_fields)` |
| `ProcessEventTime` (AE3/AE5) | `RoundContext, event_time t, is_horizon, allow_empty_horizon, RunHookContext = null` | `event_time_finalised(t)` |
| `HandleDispatchIntegrityFailure` (AE6) | `RoundContext, er, record` | `dispatch_integrity_handled(er)` |
| `ScheduleNextHashWork` (AE9) | `RoundContext, MinerID, assignment, from_cursor` | `hash_work_seated(EventRef)` \| `hash_work_not_seated(reason)` |
| `StartHashing` (AE9) | `RoundContext, MinerID, assignment` | `hashing_started` \| `hashing_not_started(reason)` |
| `SetupRetryEvent` (AE4/AE5) | `RoundContext, dispatch_envelope, dispatched_event_ref, immutable_payload (RoundID, setup_kind, SetupRetryID, TemplateID_at_seat, TemplateRefreshSetupID, retry_generation, reason)` | (unchanged AC/AD disposition set) |
| `BlockAcceptancePoint` (AE5) | `RoundContext, certificate, snapshot, CandidateID, PropagationID, outcome` (NO `dispatch_envelope`) | `registered` \| `ignored_stale_candidate` |
| `RunInitialise` (AE6) | `config` | `RunContext(... setup_retry_by_seat_event_ref = empty map ...)` |

**Signature/contract changes introduced by Stage 1AE:**
- `CancelQueuedEvent` is NEW (AE1): the sole queue-owner cancellation.
- `ScheduleEvent` RETURNS gains `rejected_payload_schema_mismatch` (AE7); the seat body is one atomic transaction (AE8).
- `ProcessEventTime` re-selects/re-reads and skips a cancelled event (AE3), and dispatches only the §0.7g-schema-declared
  arguments (AE5, Design B — both `dispatch_envelope` and `dispatched_event_ref` gated).
- `HandleDispatchIntegrityFailure` resolves the owner from `setup_retry_by_seat_event_ref[er]`, never the corrupt payload
  (AE6).
- `ScheduleNextHashWork` RETURNS `hash_work_seated`/`hash_work_not_seated` (was bare `scheduled`) (AE9); `StartHashing` gains
  `hashing_not_started(reason)`.
- `RunInitialise` initialises `setup_retry_by_seat_event_ref` (AE6); the retry seats publish it atomically.

## 2. Call-site agreement matrix

### `CancelQueuedEvent` (AE1/AE2)

| Caller | Args match | Result handling |
|--------|-----------|-----------------|
| every reconciled cancel site (17 procedures; 31 call sites) | ✓ `(EventRef, cancellation_reason, cancellation_context)` | ✓ for-effect (idempotent no-op on unknown/terminal/dispatching); set cancellations iterate in stable order |

Defined once; called at every cancel site. No raw `CANCEL <ref> on EQ` remains.

### `ScheduleEvent` (AE7/AE8) — result binding

| Caller | Args match | Result handling |
|--------|-----------|-----------------|
| retry seating sites / `StartWake` / `SeatRecoveryCompletion` / `SeatRecoveryWork` / `CompleteSecurityRecovery` / `ScheduleSolutionPropagation` seats | ✓ | ✓ pattern-match `scheduled(event_ref, record)` and branch on rejection (AD3); a malformed request at these trusted internal sites is not reachable, but the structured `rejected_payload_schema_mismatch` is available if one occurred |
| `ScheduleNextHashWork` | ✓ | ✓ binds result, returns `hash_work_seated`/`hash_work_not_seated` (AE9) |

### `ProcessEventTime` (AE5) → dispatched handlers

| Aspect | Check |
|--------|-------|
| Design B delivery | ✓ `dispatch_envelope` passed IFF `§0.7g-schema[event_type].recv_env = yes`; `dispatched_event_ref` IFF `recv_ref = yes`; no undeclared argument |
| `BlockAcceptancePoint` | ✓ `recv env` = no → receives no `dispatch_envelope`; its INPUTS omit it |
| `SetupRetryEvent` | ✓ `recv env` = yes, `recv ref` = yes → receives both |

### `ScheduleNextHashWork` (AE9)

| Caller | Args match | Result handling |
|--------|-----------|-----------------|
| `StartHashing` | ✓ | ✓ binds `hw`; on `hash_work_not_seated` returns `hashing_not_started(reason)` |
| `HashWorkEvent` continuation | ✓ | ✓ `RETURN CALL ScheduleNextHashWork(...)` — the continuation disposition IS `hash_work_seated`/`hash_work_not_seated` |

## 3. Cross-checks performed

1. **Sole cancellation owner.** `CancelQueuedEvent` is the only EQ-removal / `QUEUED → CANCELLED` writer; every cancel site
   calls it; no raw `CANCEL … on EQ` remains (AE1/AE2).
2. **Structured rejection + atomicity.** `ScheduleEvent` validates against §0.7g-schema and returns
   `rejected_payload_schema_mismatch` before any mutation (AE7); the seat is atomic (AE8).
3. **Design B.** The dispatch line gates both `dispatch_envelope` and `dispatched_event_ref` on the schema (AE5); no
   undeclared argument reaches any handler.
4. **Corrupt-retry ownership.** Resolved from `setup_retry_by_seat_event_ref[er]`, never the corrupt payload (AE6).
5. **Truthful fire-and-forget.** `ScheduleNextHashWork`/`StartHashing` report the actual result (AE9).
6. **Coherence.** The I21 queue/registry coherence invariants hold (AE10).
7. **Signature ↔ RETURNS ↔ call-site agreement** holds for every AE-touched procedure; the call graph resolves with 0
   dangling references and 89 defined callables (`STAGE_01AE_PROCEDURE_CALL_GRAPH.md`).

**Result:** for every AE-touched procedure, the signature, the RETURNS disposition set, and all call sites agree; cancellation
has one queue owner, scheduling registration is atomic with a structured rejection, dispatch is schema-gated (Design B),
corrupt-retry ownership is EventRef-bound, and fire-and-forget results are reported truthfully.
