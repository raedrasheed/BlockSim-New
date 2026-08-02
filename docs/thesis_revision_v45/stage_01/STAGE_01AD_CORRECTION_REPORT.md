# Stage 1AD — Correction Report (queued-event lifecycle & payload lock)

Stage 1AD is a narrow, documentation-only revision of the Stage-1 formal specification of **PoCol** and the idle policy
within PoCol. It closes ten defects (AD1–AD10) by introducing one central `queued_event_record` / `queued_event_registry`
as the single authoritative queue-status source, storing the complete immutable handler payload at seating and delivering
it verbatim at dispatch, completing the `ScheduleEvent` result union, making `ProcessEventTime` the sole owner of the
queue-status lifecycle, threading a complete dispatcher-owned `OrdinaryDispatchContext`, driving the guard-abort / stale /
integrity / round-closure paths through that lifecycle, and superseding the incomplete Stage-1AC audit claims. It changes
only the five normative `STAGE_01_*` documents it touches and adds fourteen `STAGE_01AD_*` deliverables. No executable
source, configuration, DOCX, or PDF is touched; no experiment is run; the A1 baseline (`8.420833333 kWh`) is unchanged; and
no Stage-1A–1AC historical artifact is modified.

- **Branch:** `thesis-v45-pocol-stage1ad-queued-event-lifecycle-payload-lock`
- **Parent commit:** `c855c6958ed0bf51f0a5ad2ed5a2ece002564d15` (Stage 1AC)

## Corrections

### AD1 — One central queued-event record + registry (single authoritative queue-status source)

`STRUCTURE queued_event_record = (event_ref : EventRef immutable, event_type, dispatch_envelope : immutable complete
ordinary-event envelope, immutable_payload, queue_status : EventQueueStatus)`, held in `queued_event_registry : map
EventRef → queued_event_record` — the ONE authoritative queue-status source. `EventQueueStatus` transitions:
`QUEUED → {DISPATCHING, CANCELLED}`; `DISPATCHING → CONSUMED`; `CONSUMED` and `CANCELLED` are terminal. A
`setup_retry_record` keeps only its immutable `seat_event_ref` (plus `status : SetupRetryStatus` and the other non-queue
lifecycle fields); its queue state IS `queued_event_registry[seat_event_ref].queue_status`. The independently-writable
per-record `event_queue_status` mirror added by AC8 is REMOVED, so no second queue-state source can diverge from the
registry. *(Audit: `STAGE_01AD_QUEUED_EVENT_RECORD_AUDIT.md`; vector TV252.)*

### AD2 — Store the complete immutable payload at seating; deliver it at dispatch

`ScheduleEvent` captures `immutable_payload` = the COMPLETE caller-supplied argument set for `event_type` (for a
`SetupRetryEvent` exactly `RoundID`, `setup_kind`, `SetupRetryID`, `TemplateID_at_seat`, `TemplateRefreshSetupID`,
`retry_generation`, `reason`) and stores it in the `queued_event_record`. `ProcessEventTime` dispatches `record.event_type`
WITH `record.immutable_payload` and the record's `OrdinaryDispatchContext`, so the payload at dispatch is identically the
payload at seating — never re-read from advanced ambient globals. *(Audit: `STAGE_01AD_EVENT_PAYLOAD_DISPATCH_AUDIT.md`;
vector TV253.)*

### AD3 — Complete the ScheduleEvent result union

`ScheduleEvent` RETURNS `scheduled(EventRef, queued_event_record) | rejected_finalised_time | post_horizon_event_rejected |
rejected_post_epilogue_not_strictly_later | rejected_backward_time` (was `scheduled(EventRef, envelope)` with the rejection
set understated). Every result-binding caller pattern-matches `scheduled(event_ref, record)` and branches on each rejection
it can receive — the two `ScheduleSolutionPropagation` seats were corrected to inspect the union so a stored/cancellable
reference is never a rejection token — a for-effect caller's only reachable rejection is the deterministic O2 post-horizon
rejection, and no procedure returns a rejection variant absent from this declared set. *(Audit:
`STAGE_01AD_SCHEDULE_RESULT_CONTRACT_AUDIT.md`; vector TV254.)*

### AD4 — ProcessEventTime is the sole queue-status owner

Before dispatch `ProcessEventTime` asserts `queue_status = QUEUED`, moves `QUEUED → DISPATCHING`, sets
`EQ.current_event_ref`, and builds a trusted `OrdinaryDispatchContext`; after the handler returns it moves
`DISPATCHING → CONSUMED` and clears `EQ.current_event_ref`. The only cancellation transition is `QUEUED → CANCELLED`
(performed by the closure terminaliser `CancelSetupRetriesForRound`, AD9). No event handler writes a `queue_status`; the two
Stage-1AC `event_queue_status <- CONSUMED` writes inside `SetupRetryEvent` are removed. *(Audit:
`STAGE_01AD_QUEUE_STATUS_OWNERSHIP_AUDIT.md`; vector TV255.)*

### AD5 — Thread a complete dispatcher-owned OrdinaryDispatchContext

`STRUCTURE OrdinaryDispatchContext = (dispatch_envelope, dispatched_event_ref)`, constructed and owned by
`ProcessEventTime` from the `queued_event_record` and its `EventRef`. Design B delivery: every ordinary handler receives
`dispatch_envelope`; `dispatched_event_ref` is delivered ONLY to a handler whose declared signature includes it (currently
only `SetupRetryEvent`). No undeclared named argument is injected into a handler that omits it. *(Audit:
`STAGE_01AD_DISPATCH_INTEGRITY_CONTEXT_AUDIT.md`; vector TV256.)*

### AD6 — Guard-driven abort against the DISPATCHING queue state

A guard-driven retry abort runs `SEATED → APPLYING → ABORTED` while the queue moves `QUEUED → DISPATCHING → CONSUMED`.
Because `ProcessEventTime` sets `DISPATCHING` BEFORE dispatch (AD4), `CancelSetupRetriesForRound` — reached synchronously
during the abort — sees the retry `APPLYING` and the queue `DISPATCHING` (never a stale `QUEUED`), so it only persists
`terminal_closure_pending`; the `RoundAbort` path never trips a `QUEUED` assertion, and after the handler returns no event
remains `DISPATCHING`. This closes the Stage-1AC failure in which the record still claimed `QUEUED` during `RoundAbort`.
*(Audit: `STAGE_01AD_RETRY_ABORT_QUEUE_LIFECYCLE_AUDIT.md`; vectors TV257/TV261.)*

### AD7 — Stale/terminal dispatch still consumes the queue state

A stale or terminal dispatch STILL follows `QUEUED → DISPATCHING → CONSUMED` (the dispatcher consumes it unconditionally of
the handler's exit disposition), so a stale dispatch can never leave the registry at `QUEUED`, and a later
`CloseRoundAssignments` never finds a terminal retry record whose central event is falsely `QUEUED`. *(Audit:
`STAGE_01AD_STALE_EVENT_CONSUMPTION_AUDIT.md`; vector TV258.)*

### AD8 — Completeness + integrity of the dispatched record

`ScheduleEvent` asserts `immutable_payload` carries every required field and does NOT construct or register an incomplete
`queued_event_record`. `ProcessEventTime` builds a complete dispatcher-owned `OrdinaryDispatchContext`; on a defensively
detected corrupt registry entry it calls `HandleDispatchIntegrityFailure`, which records the declared terminal disposition
`dispatch_integrity_failure`, builds a COMPLETE integrity envelope from the TRUSTED `EventRef` fields (never the corrupt
payload), terminalises a current nonterminal-round `SEATED` record via `SEATED → APPLYING → ABORTED` with a current-round
`RoundAbort`, and terminalises an older/terminal-round record `SUPERSEDED` WITHOUT aborting the current round. A malformed
untrusted envelope never becomes the transition identity for round closure. *(Audit:
`STAGE_01AD_DISPATCH_INTEGRITY_CONTEXT_AUDIT.md`; vector TV259.)*

### AD9 — CancelSetupRetriesForRound inspects the central registry

For each closing-round retry, `CancelSetupRetriesForRound` reads `queued_event_registry[seat_event_ref].queue_status`:
`QUEUED` → cancel the event on `EQ`, set `QUEUED → CANCELLED`, and `SetSetupRetryStatus(SEATED → CANCELLED)`; `DISPATCHING`
→ do NOT cancel and do NOT rewrite the queue state, persist `terminal_closure_pending` only (the dispatcher later sets
`DISPATCHING → CONSUMED`); `CONSUMED`/`CANCELLED` → no queue rewrite. Post-conditions: no closing-round event remains
`QUEUED`; none remains `DISPATCHING` after its handler returns; every `SEATED` retry is terminalised; no terminal retry
owns a live `QUEUED` event; and no queue status is held in an unsynchronised local mirror. *(Audit:
`STAGE_01AD_RETRY_ABORT_QUEUE_LIFECYCLE_AUDIT.md`; vectors TV260/TV261.)*

### AD10 — Supersede the incomplete Stage-1AC audit claims

`STAGE_01AD_SUPERSESSION_REGISTER.md` records the Stage-1AC audit gaps AD corrects: the AC8 audit missed the stale and
guard-abort queue-consumption exits; TV249 missed the `QUEUED`-assertion failure during `RoundAbort`; TV247 did not test
queue-state consumption; TV248 passed an incomplete envelope into `RoundAbort`; the AC1/AC2 audit did not verify
complete-payload storage/dispatch; and `ScheduleEvent`'s declared RETURNS omitted rejection variants. Stage-1AC artifacts
are frozen; the corrections live only in the Stage-1AD register. *(See `STAGE_01AD_SUPERSESSION_REGISTER.md`.)*

## Deliverables (14 new `STAGE_01AD_*` files)

1. `STAGE_01AD_CORRECTION_REPORT.md` (this file)
2. `STAGE_01AD_QUEUED_EVENT_RECORD_AUDIT.md` (AD1)
3. `STAGE_01AD_EVENT_PAYLOAD_DISPATCH_AUDIT.md` (AD2)
4. `STAGE_01AD_SCHEDULE_RESULT_CONTRACT_AUDIT.md` (AD3)
5. `STAGE_01AD_QUEUE_STATUS_OWNERSHIP_AUDIT.md` (AD4)
6. `STAGE_01AD_RETRY_ABORT_QUEUE_LIFECYCLE_AUDIT.md` (AD6/AD9)
7. `STAGE_01AD_STALE_EVENT_CONSUMPTION_AUDIT.md` (AD7)
8. `STAGE_01AD_DISPATCH_INTEGRITY_CONTEXT_AUDIT.md` (AD5/AD8)
9. `STAGE_01AD_PROCEDURE_SIGNATURE_CALL_AUDIT.md`
10. `STAGE_01AD_PROCEDURE_CALL_GRAPH.md`
11. `STAGE_01AD_SEMANTIC_TEST_VECTORS.md` (TV252–TV261)
12. `STAGE_01AD_SUPERSESSION_REGISTER.md`
13. `STAGE_01AD_CROSS_DOCUMENT_AUDIT.md`
14. `STAGE_01AD_CHECKSUM_MANIFEST.sha256`

## Modified normative documents (5)

`STAGE_01_PROTOCOL_PSEUDOCODE.md`, `STAGE_01_ROUND_STATE_MACHINE.md` (adds §3.10h), `STAGE_01_INVARIANT_CATALOGUE.md`
(I16 Stage-1AD clause), `STAGE_01_TERMINOLOGY.md` (Stage-1AD addendum), `STAGE_01_TRACEABILITY_MATRIX.csv` (rows
R215–R225). The miner state machine is not touched (AD1–AD10 concern the scheduler/dispatcher and the retry-record queue
lifecycle only).

## Discipline

Documentation-only; the algorithm remains **PoCol** and the mechanism remains the idle policy within PoCol; the A1 baseline
`8.420833333 kWh` is unchanged; the call graph resolves with 88 callables (87 procedures + 1 function) and 0 dangling
references (Stage 1AD adds the one new procedure `HandleDispatchIntegrityFailure`, defined once and called once from
`ProcessEventTime`); and Stage 2 is not begun.
