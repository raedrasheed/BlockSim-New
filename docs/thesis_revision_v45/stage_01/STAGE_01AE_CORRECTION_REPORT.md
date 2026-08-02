# Stage 1AE — Correction Report (global-event cancellation & dispatch-schema lock)

Stage 1AE is a narrow, documentation-only revision of the Stage-1 formal specification of **PoCol** and the idle policy
within PoCol. It closes eleven defects (AE1–AE11) by introducing one global queue-owner cancellation operation, reconciling
every cancel site through it, making the event-time dispatch loop robust to mid-batch cancellation, declaring the
authoritative event-type dispatch schema, fixing dispatch-envelope signature agreement, binding corrupt-retry ownership by
EventRef, returning a structured payload-schema rejection, making scheduler registration atomic, reporting fire-and-forget
scheduling results truthfully, adding queue/registry coherence invariants, and superseding the incomplete Stage-1AD audit
claims. It changes only the five normative `STAGE_01_*` documents it touches and adds fifteen `STAGE_01AE_*` deliverables. No
executable source, configuration, DOCX, or PDF is touched; no experiment is run; the A1 baseline (`8.420833333 kWh`) is
unchanged; and no Stage-1A–1AD historical artifact is modified.

- **Branch:** `thesis-v45-pocol-stage1ae-global-event-cancellation-dispatch-schema-lock`
- **Parent commit:** `9d4b7d4315ad5f5c3cf3aca45e4b8b64a0821059` (Stage 1AD)

## Corrections

### AE1 — One global queued-event cancellation procedure

`CancelQueuedEvent(EventRef, cancellation_reason, cancellation_context)` is the SOLE operation that removes an EventRef from
EQ: unknown → `cancellation_unknown_event`; `QUEUED` → atomically remove from EQ and set `QUEUED → CANCELLED`, return
`event_cancelled`; `DISPATCHING` → `event_already_dispatching` with no mutation; `CONSUMED`/`CANCELLED` →
`cancellation_terminal_noop`. The cancellation operation — not each protocol procedure — owns the atomic EQ-removal +
central-registry state update. *(Audit: `STAGE_01AE_GLOBAL_CANCELLATION_AUDIT.md`; vectors TV262/TV263/TV272.)*

### AE2 — Reconcile every existing cancel site

Every wake / resume / certificate-arrival / block-arrival / hash-work / recovery / setup-retry / acceptance-batch /
round-or-template-closure cancellation calls `CancelQueuedEvent`; a set cancellation iterates its EventRefs in stable order
and calls it once each. No procedure executes a raw `CANCEL <ref> on EQ`; no event removed from EQ remains `QUEUED` in the
registry. The reconciled sites include `AbortPendingWakeForRollback`, `StartWake`'s rollback, `HandlePropagationFailure`,
`ValidBlockAccept`, `CloseTemplateAssignments`, `CloseRoundAssignments`, `RoundAbort`, the recovery
deadline/completion/work cancellations, candidate event cleanup, `CancelSetupRetriesForRound`, and `LeaseExpiry`. *(Audit:
`STAGE_01AE_GLOBAL_CANCELLATION_AUDIT.md`; vectors TV262/TV263.)*

### AE3 — ProcessEventTime robust to mid-batch cancellation

`ProcessEventTime` no longer iterates a stale snapshot of all `QUEUED` events at one `(t, delta_cycle)`. It re-selects and
re-reads the smallest current `QUEUED` EventRef each iteration; if the re-read shows it is not `QUEUED` (or absent from EQ)
it skips it (no assert, no dispatch); otherwise it moves `QUEUED → DISPATCHING`, dispatches exactly one event, completes
`DISPATCHING → CONSUMED`, and re-queries. A handler that cancels a later same-time event never causes that event to be
dispatched or an assertion to fail. *(Audit: `STAGE_01AE_MID_BATCH_CANCELLATION_AUDIT.md`; vector TV264.)*

### AE4 — Declare the complete event-type dispatch schema

§0.7g-schema declares, per queued event type, the handler procedure, required `immutable_payload` fields, whether it
receives `dispatch_envelope` (`recv env`), whether it receives `dispatched_event_ref` (`recv ref`), the target microphase,
and the stable tie key — covering every `ScheduleEvent` target. `ScheduleEvent` validates `immutable_payload` against this
table; `ProcessEventTime` dispatches only the arguments it declares. *(Audit: `STAGE_01AE_EVENT_HANDLER_SCHEMA_AUDIT.md`;
vector TV266.)*

### AE5 — Fix dispatch_envelope signature agreement (Design B)

The dispatcher passes `dispatch_envelope` to a handler IFF the schema's `recv env` = yes and `dispatched_event_ref` IFF
`recv ref` = yes — never an undeclared argument. This closes the AD5 defect whereby `dispatch_envelope` was passed to every
ordinary handler including ones (like `BlockAcceptancePoint`) that do not declare it. Every handler signature, payload
schema, call graph, signature audit, and semantic vector agrees. *(Audit: `STAGE_01AE_DISPATCH_SIGNATURE_AUDIT.md`; vector
TV265.)*

### AE6 — Bind corrupt retry ownership by EventRef

`setup_retry_by_seat_event_ref : EventRef → SetupRetryID` is published atomically at seating.
`HandleDispatchIntegrityFailure` resolves the owner from `setup_retry_by_seat_event_ref[er]` (verified against
`seat_event_ref`), NEVER from the corrupt payload's `SetupRetryID`: a missing payload id still resolves the owner from `er`;
a payload naming a foreign valid id leaves that foreign record untouched (mismatch audited); an event with no reverse-bound
owner records the failure and is consumed without mutating an unrelated retry. A corrupt payload can never choose which retry
record is aborted. *(Audit: `STAGE_01AE_CORRUPT_RETRY_OWNERSHIP_AUDIT.md`; vectors TV267/TV268.)*

### AE7 — Return a structured payload-schema rejection

`ScheduleEvent` validates `event_type` + `immutable_payload` against §0.7g-schema BEFORE minting `seq`, deriving the
`EventRef`, registering the record, or inserting into EQ, returning `rejected_payload_schema_mismatch(event_type,
missing_or_invalid_fields)` (added to its RETURNS union). No malformed scheduling request terminates the simulation through a
raw assertion (the AD8 construction ASSERT is superseded). *(Audit: `STAGE_01AE_SCHEDULE_REJECTION_AUDIT.md`; vector
TV269.)*

### AE8 — Make ScheduleEvent registration atomic

The successful seat is one atomic transaction — validate time, validate payload, mint seq + EventRef, create the `QUEUED`
record, add the registry entry, and insert the EventRef into EQ, committing both-or-neither — so no registry entry is ever
`QUEUED` without a pending EQ entry and no EQ entry ever lacks a registry entry. *(Audit:
`STAGE_01AE_SCHEDULE_REJECTION_AUDIT.md`; vector TV269.)*

### AE9 — Fix fire-and-forget scheduling results

`ScheduleNextHashWork` captures the `ScheduleEvent` result and returns `hash_work_seated(EventRef)` or
`hash_work_not_seated(reason)` — never `scheduled` after a `post_horizon_event_rejected`; `StartHashing` and the
`HashWorkEvent` continuation report it truthfully. Every remaining for-effect `ScheduleEvent` caller handles every reachable
result or relies only on the deterministic O2 post-horizon rejection. *(Audit: `STAGE_01AE_FIRE_AND_FORGET_RESULT_AUDIT.md`;
vector TV270.)*

### AE10 — Add queue/registry coherence invariants (I21)

An EventRef is present in EQ IFF its registry status is `QUEUED`; the executing EventRef is absent from pending EQ and is
`DISPATCHING`; `CONSUMED`/`CANCELLED` EventRefs are absent from EQ; every `QUEUED` entry is present exactly once; no EventRef
is dispatched more than once; after `ProcessEventTime(t)` no event at `t` is `QUEUED` or `DISPATCHING`; every cancellation
changes EQ membership and registry status atomically. *(Audit: `STAGE_01AE_QUEUE_REGISTRY_COHERENCE_AUDIT.md`; vectors
TV271/TV272.)*

### AE11 — Supersede the incomplete Stage-1AD audits

`STAGE_01AE_SUPERSESSION_REGISTER.md` records the Stage-1AD audit gaps AE corrects: the AD queue-status-ownership audit did
not audit all raw CANCEL sites; the payload-dispatch audit did not establish a complete event-type payload/signature schema;
the dispatch-integrity audit trusted the corrupt payload's `SetupRetryID`; TV257–TV261 did not exercise cancellation of
non-`SetupRetryEvent` events or mid-batch cancellation; and `ScheduleNextHashWork` still returned `scheduled` after a
rejection. Stage-1AD artifacts are frozen. *(See `STAGE_01AE_SUPERSESSION_REGISTER.md`.)*

## Deliverables (15 new `STAGE_01AE_*` files)

1. `STAGE_01AE_CORRECTION_REPORT.md` (this file)
2. `STAGE_01AE_GLOBAL_CANCELLATION_AUDIT.md` (AE1/AE2)
3. `STAGE_01AE_QUEUE_REGISTRY_COHERENCE_AUDIT.md` (AE10/I21)
4. `STAGE_01AE_MID_BATCH_CANCELLATION_AUDIT.md` (AE3)
5. `STAGE_01AE_EVENT_HANDLER_SCHEMA_AUDIT.md` (AE4)
6. `STAGE_01AE_DISPATCH_SIGNATURE_AUDIT.md` (AE5)
7. `STAGE_01AE_CORRUPT_RETRY_OWNERSHIP_AUDIT.md` (AE6)
8. `STAGE_01AE_SCHEDULE_REJECTION_AUDIT.md` (AE7/AE8)
9. `STAGE_01AE_FIRE_AND_FORGET_RESULT_AUDIT.md` (AE9)
10. `STAGE_01AE_PROCEDURE_SIGNATURE_CALL_AUDIT.md`
11. `STAGE_01AE_PROCEDURE_CALL_GRAPH.md`
12. `STAGE_01AE_SEMANTIC_TEST_VECTORS.md` (TV262–TV272)
13. `STAGE_01AE_SUPERSESSION_REGISTER.md`
14. `STAGE_01AE_CROSS_DOCUMENT_AUDIT.md`
15. `STAGE_01AE_CHECKSUM_MANIFEST.sha256`

## Modified normative documents (5)

`STAGE_01_PROTOCOL_PSEUDOCODE.md`, `STAGE_01_ROUND_STATE_MACHINE.md` (adds §3.10i), `STAGE_01_INVARIANT_CATALOGUE.md`
(I16 Stage-1AE clause + new I21), `STAGE_01_TERMINOLOGY.md` (Stage-1AE addendum), `STAGE_01_TRACEABILITY_MATRIX.csv` (rows
R226–R237). The miner state machine is not touched (AE1–AE11 concern the scheduler/dispatcher and the queued-event
cancellation lifecycle only).

## Discipline

Documentation-only; the algorithm remains **PoCol** and the mechanism remains the idle policy within PoCol; the A1 baseline
`8.420833333 kWh` is unchanged; the call graph resolves with 89 callables (88 procedures + 1 function) and 0 dangling
references (Stage 1AE adds the one new procedure `CancelQueuedEvent`, defined once and called at every reconciled cancel
site); and Stage 2 is not begun.
