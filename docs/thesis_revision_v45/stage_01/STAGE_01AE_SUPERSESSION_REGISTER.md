# Stage 1AE — Supersession Register

Stage 1AE supersedes specific Stage-1AD statements about event cancellation, the dispatch loop, the dispatch signature, the
corrupt-retry owner resolution, the scheduler's construction failure mode, and fire-and-forget results; and (AE11) it records
the incomplete Stage-1AD audit and test-vector claims that AE corrects. Each row records the SUPERSEDED statement, the
SUPERSEDING Stage-1AE statement, and the authoritative location in the current `STAGE_01_PROTOCOL_PSEUDOCODE.md` (line
anchors approximate). No Stage-1A–1AD lettered artifact is modified; the historical layers remain frozen, and this register
is the sole record of what Stage 1AE overrides.

## 1. Superseded → superseding statements

| # | Superseded (Stage 1AD) | Superseding (Stage 1AE) | Authoritative location |
|--:|------------------------|--------------------------|------------------------|
| AE1 | Each procedure performed its own raw `CANCEL <ref> on EQ` and (in `CancelSetupRetriesForRound`) a separate `queue_status <- CANCELLED`, so EQ-removal and the central status change were two steps in many places | `CancelQueuedEvent(EventRef, cancellation_reason, cancellation_context)` is the ONE queue-owner cancellation; it atomically removes from EQ and sets `QUEUED → CANCELLED`, and is the sole path that removes an EventRef from EQ | `PROCEDURE CancelQueuedEvent` (~L601) |
| AE2 | Cancellation was spread across ~29 raw `CANCEL … on EQ` / `CANCEL every event in …` / descriptive `CANCEL the pending … for …` sites | Every cancel site calls `CancelQueuedEvent` (set cancellations iterate EventRefs in stable order); no raw `CANCEL … on EQ` remains | every former cancel site (StartWake, AbortPendingWakeForRollback, HandlePropagationFailure, ValidBlockAccept, CloseTemplateAssignments, CloseRoundAssignments, RoundAbort, recovery cleanup, LeaseExpiry, CancelSetupRetriesForRound) |
| AE3 | `ProcessEventTime` iterated a `FOR EACH` snapshot of all QUEUED events at one `(t, delta_cycle)` with a hard `ASSERT record.queue_status = QUEUED` — a handler that cancelled a later same-cycle event would trip that assertion | A `WHILE` loop re-selects/re-reads the smallest current QUEUED EventRef, SKIPS a now-cancelled/absent one (no assert, no dispatch), dispatches exactly one, and re-queries | `ProcessEventTime` dispatch loop (~L207) |
| AE4 | The dispatch schema was split across §0.7g (microphase map) and §0.7g-driver (seating) with no single payload/signature table | §0.7g-schema is the ONE authoritative table (handler, required payload fields, recv env, recv ref, microphase, tie key) covering every queued event type; `ScheduleEvent` validates against it, `ProcessEventTime` dispatches from it | §0.7g-schema (~L756) |
| AE5 | AD5 Design B passed `dispatch_envelope` to EVERY ordinary handler while gating only `dispatched_event_ref` — so a handler like `BlockAcceptancePoint`, which does not declare `dispatch_envelope`, received an undeclared argument | Design B gates BOTH: the dispatcher passes `dispatch_envelope`/`dispatched_event_ref` IFF §0.7g-schema declares `recv env`/`recv ref` = yes | `ProcessEventTime` DISPATCH line (~L237); §0.7g-schema |
| AE6 | `HandleDispatchIntegrityFailure` resolved the corrupt retry's owner from the corrupt payload's `SetupRetryID` | It resolves the owner from `setup_retry_by_seat_event_ref[er]` (the trusted EventRef), verified against `seat_event_ref`; a foreign named id is untouched (audited), a no-owner event mutates nothing | `PROCEDURE HandleDispatchIntegrityFailure` (~L318); reverse map in RunInitialise (~L1900); both seats (~L2215/~L5670) |
| AE7 | `ScheduleEvent` used a raw construction `ASSERT immutable_payload contains EVERY required field` (AD8) that would terminate the simulation on a malformed request | `ScheduleEvent` returns the structured `rejected_payload_schema_mismatch(event_type, missing_or_invalid_fields)` BEFORE any state mutation, added to its RETURNS union | `ScheduleEvent` payload validation (~L567); RETURNS (~L592) |
| AE8 | The seat's seq/EventRef/registry/EQ steps were sequential with no declared atomicity | The successful seat is one ATOMICALLY block (mint seq + EventRef, create record, add registry entry, insert EQ) committing both-or-neither | `ScheduleEvent` ATOMICALLY block (~L572) |
| AE9 | `ScheduleNextHashWork` RETURNED a bare `scheduled` even when `ScheduleEvent` had returned `post_horizon_event_rejected` | It returns `hash_work_seated(EventRef)` / `hash_work_not_seated(reason)`; `StartHashing` and the `HashWorkEvent` continuation report it truthfully | `PROCEDURE ScheduleNextHashWork` (~L2815); `StartHashing` (~L2806) |

## 2. AE11 — corrected Stage-1AD audit / test-vector claims

Stage-1AD artifacts are FROZEN; the corrections apply only to the Stage-1AE normative tree and are recorded here.

| # | Incomplete Stage-1AD claim | Stage-1AE correction |
|--:|----------------------------|----------------------|
| 1 | `STAGE_01AD_QUEUE_STATUS_OWNERSHIP_AUDIT.md` counted `queue_status` writes but did not audit ALL raw CANCEL sites | AE1/AE2 route every cancellation through `CancelQueuedEvent`; `STAGE_01AE_GLOBAL_CANCELLATION_AUDIT.md` audits every site |
| 2 | `STAGE_01AD_EVENT_PAYLOAD_DISPATCH_AUDIT.md` did not establish a complete event-type payload/signature schema | AE4 declares §0.7g-schema; `STAGE_01AE_EVENT_HANDLER_SCHEMA_AUDIT.md` verifies it against every handler |
| 3 | `STAGE_01AD_DISPATCH_INTEGRITY_CONTEXT_AUDIT.md` trusted the corrupt payload's `SetupRetryID` without proving EventRef ownership | AE6 resolves the owner from `setup_retry_by_seat_event_ref[er]`; `STAGE_01AE_CORRUPT_RETRY_OWNERSHIP_AUDIT.md` verifies it |
| 4 | TV257–TV261 did not exercise cancellation of non-`SetupRetryEvent` events | TV262/TV263 cancel a `CertificateArrival` and a `WakeCompleteEvent` through `CancelQueuedEvent` |
| 5 | The ProcessEventTime `FOR EACH` batch was not tested against cancellation of a later same-cycle event | TV264 exercises mid-batch cancellation of a same-`(t, delta_cycle)` event (AE3) |
| 6 | `ScheduleNextHashWork` still returned `scheduled` after a `ScheduleEvent` rejection | AE9 returns `hash_work_not_seated`; TV270 verifies it |

## 3. Companion normative-document supersessions

| Document | Superseding Stage-1AE addendum |
|----------|-------------------------------|
| `STAGE_01_ROUND_STATE_MACHINE.md` | §3.10i Stage-1AE addendum (AE1–AE11); §3.10a–§3.10h retained as the frozen W…AD layers |
| `STAGE_01_INVARIANT_CATALOGUE.md` | I16 Stage-1AE clause (AE1–AE11) + new **I21** (queue/registry coherence) |
| `STAGE_01_TERMINOLOGY.md` | Stage-1AE terminology addendum (`CancelQueuedEvent`, `setup_retry_by_seat_event_ref`, `rejected_payload_schema_mismatch`, §0.7g-schema, `hash_work_seated`/`hash_work_not_seated`, I21) |
| `STAGE_01_TRACEABILITY_MATRIX.csv` | Rows R226–R237 (AE1–AE11 + the TV262–TV272 block) |

The miner state machine is not modified — AE1–AE11 concern the scheduler/dispatcher and the queued-event cancellation
lifecycle only.

## 4. Freeze statement

Stage-1A through Stage-1AD lettered artifacts (`STAGE_01[A-Z]_*`, `STAGE_01AA_*` … `STAGE_01AD_*`) are byte-identical to the
Stage-1AD parent commit (`9d4b7d4315ad5f5c3cf3aca45e4b8b64a0821059`). Stage 1AE modifies only the five normative
`STAGE_01_*` documents it touches and adds the fifteen `STAGE_01AE_*` deliverables; every override of a prior-letter
statement is recorded in this register.
