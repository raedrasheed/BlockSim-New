# Stage 1AD — Supersession Register

Stage 1AD supersedes specific Stage-1AC statements about the queued-event's queue-state ownership, the scheduler payload
and result contract, the dispatch context, and the abort / stale / integrity / round-closure queue lifecycle; and (AD10) it
records the incomplete Stage-1AC audit and test-vector claims that AD corrects. Each row records the SUPERSEDED statement,
the SUPERSEDING Stage-1AD statement, and the authoritative location in the current `STAGE_01_PROTOCOL_PSEUDOCODE.md` (line
anchors approximate). No Stage-1A–1AC lettered artifact (`STAGE_01[A-Z]_*` / `STAGE_01AA_*` / `STAGE_01AB_*` /
`STAGE_01AC_*`) is modified; the historical layers remain frozen, and this register is the sole record of what Stage 1AD
overrides.

## 1. Superseded → superseding statements

| # | Superseded (Stage 1AC) | Superseding (Stage 1AD) | Authoritative location |
|--:|------------------------|--------------------------|------------------------|
| AD1 | The retry record carried its OWN writable `event_queue_status : EventQueueStatus` mirror alongside `seat_event_ref` (AC8), so two queue-state sources (the per-record mirror and the queue on `EQ`) could diverge | One central `queued_event_record` in `queued_event_registry : map EventRef → queued_event_record` is the ONE authoritative queue-status source; the per-record mirror is REMOVED and a `setup_retry_record`'s queue state IS `queued_event_registry[seat_event_ref].queue_status` | `STRUCTURE queued_event_record` (~L493); `queued_event_registry` (~L504); `RunInitialise` init (~L1754); record def w/o mirror (~L2092/~L5527) |
| AD2 | `ScheduleEvent` stored the envelope; the payload delivered to a handler was not pinned as a complete stored set, so a dispatched handler could read advanced ambient globals | `ScheduleEvent` stores the COMPLETE `immutable_payload` at seating; `ProcessEventTime` dispatches `record.immutable_payload`; payload at dispatch = payload at seating | `ScheduleEvent` payload capture (~L571) + assert (~L574); `ProcessEventTime` dispatch (~L236) |
| AD3 | `ScheduleEvent` RETURNS was `scheduled(EventRef, envelope)` with an understated rejection set | RETURNS `scheduled(EventRef, queued_event_record) \| rejected_finalised_time \| post_horizon_event_rejected \| rejected_post_epilogue_not_strictly_later \| rejected_backward_time`; every caller inspects the union | `ScheduleEvent` RETURNS (~L586) |
| AD4 | Queue-state writes were split: `SetupRetryEvent` itself wrote `event_queue_status <- CONSUMED`, so the dispatch lifecycle had more than one owner | `ProcessEventTime` is the SOLE queue-status owner (`QUEUED → DISPATCHING` before dispatch, `DISPATCHING → CONSUMED` after); the only cancellation is `QUEUED → CANCELLED` in `CancelSetupRetriesForRound`; no handler writes `queue_status` | `ProcessEventTime` (~L215–L239); `SetupRetryEvent` (the two `event_queue_status <- CONSUMED` writes removed) |
| AD5 | The dispatcher injected `dispatched_event_ref` without a declared context object and without a stated delivery discipline for handlers that do not accept it | `STRUCTURE OrdinaryDispatchContext = (dispatch_envelope, dispatched_event_ref)`, dispatcher-owned; Design B delivers `dispatched_event_ref` only to a handler declaring it; no undeclared named argument is injected | `STRUCTURE OrdinaryDispatchContext` (~L515); `ProcessEventTime` dispatch (~L222/~L236) |
| AD6 | A guard-driven abort could reach `CancelSetupRetriesForRound` with the record's queue state still `QUEUED`, tripping the AB6/AC8 `event_queue_status = QUEUED` closure assertion during `RoundAbort` | `ProcessEventTime` sets `DISPATCHING` before dispatch, so the closing pass sees `DISPATCHING` (never a stale `QUEUED`); `CancelSetupRetriesForRound` persists `terminal_closure_pending` only, and no `QUEUED` assertion trips | `ProcessEventTime` (~L216); `CancelSetupRetriesForRound` DISPATCHING branch (~L2426) |
| AD7 | Stale/terminal dispatch consumption of the queue entry was implicit; a stale dispatch could be read as leaving the record `QUEUED` | The dispatcher drives `QUEUED → DISPATCHING → CONSUMED` unconditionally of the handler's exit, so a stale dispatch can never leave the registry at `QUEUED` | `ProcessEventTime` (~L216/~L239); `CancelSetupRetriesForRound` post-conditions (~L2432) |
| AD8 | An incomplete/malformed envelope could be constructed and its untrusted fields used as the abort identity | `ScheduleEvent` rejects an incomplete record; `HandleDispatchIntegrityFailure` builds a COMPLETE integrity envelope from the trusted `EventRef` and never uses the corrupt payload as the round-closure transition identity | `ScheduleEvent` assert (~L574); `PROCEDURE HandleDispatchIntegrityFailure` (~L310) |
| AD9 | `CancelSetupRetriesForRound` consulted/mutated the per-record `event_queue_status` mirror (AC8) | It reads/mutates the CENTRAL `queued_event_registry[seat_event_ref].queue_status` (`QUEUED` → cancel + `CANCELLED` + `SEATED → CANCELLED`; `DISPATCHING` → `terminal_closure_pending` only; `CONSUMED`/`CANCELLED` → no rewrite) with registry-based post-conditions | `PROCEDURE CancelSetupRetriesForRound` (~L2411–L2438) |

## 2. AD10 — corrected Stage-1AC audit / test-vector claims

The following Stage-1AC deliverable statements were incomplete. Stage-1AC artifacts are FROZEN; the corrections apply only
to the Stage-1AD normative tree and are recorded here.

| # | Incomplete Stage-1AC claim | Stage-1AD correction |
|--:|----------------------------|----------------------|
| 1 | `STAGE_01AC_EVENT_REFERENCE_LIFECYCLE_AUDIT.md` (AC8) treated the per-record `event_queue_status` mirror as a sound single source and did not audit the stale / guard-abort queue-consumption exits | AD1/AD4/AD7 remove the mirror and make `ProcessEventTime` the sole owner; `STAGE_01AD_QUEUED_EVENT_RECORD_AUDIT.md`, `STAGE_01AD_QUEUE_STATUS_OWNERSHIP_AUDIT.md`, and `STAGE_01AD_STALE_EVENT_CONSUMPTION_AUDIT.md` audit those exits |
| 2 | TV249 (AC6) asserted the abort status path but did not exercise the `event_queue_status = QUEUED` closure-assertion failure that occurs when `CancelSetupRetriesForRound` runs during the abort | TV257/TV261 exercise the guard-abort against the `DISPATCHING` queue state so no `QUEUED` assertion trips (AD6) |
| 3 | TV247 (AC4) checked round-scoped integrity but did NOT test that the stale historical dispatch's queue entry is consumed | TV258 tests `QUEUED → DISPATCHING → CONSUMED` for a stale dispatch (AD7) |
| 4 | TV248 (AC5-C) drove the integrity abort by passing an incomplete `dispatch_envelope` INTO `RoundAbort` as the transition identity | TV259 requires a COMPLETE integrity envelope built from the trusted `EventRef` (AD8); a malformed untrusted envelope never becomes the round-closure identity |
| 5 | The AC1/AC2 audit (`STAGE_01AC_EVENT_REFERENCE_DISPATCH_AUDIT.md`) did not verify complete-payload STORAGE at seating and verbatim DELIVERY at dispatch | AD2 pins the stored payload; `STAGE_01AD_EVENT_PAYLOAD_DISPATCH_AUDIT.md` + TV253 verify it |
| 6 | `ScheduleEvent`'s declared RETURNS (AC1) named `scheduled(EventRef, envelope)` and understated the rejection set | AD3 declares the complete union and audits every caller; `STAGE_01AD_SCHEDULE_RESULT_CONTRACT_AUDIT.md` + TV254 verify it |

## 3. Companion normative-document supersessions

| Document | Superseding Stage-1AD addendum |
|----------|-------------------------------|
| `STAGE_01_ROUND_STATE_MACHINE.md` | §3.10h Stage-1AD addendum (AD1–AD10); §3.10a–§3.10g retained as the frozen W/X/Y/Z/AA/AB/AC layers |
| `STAGE_01_INVARIANT_CATALOGUE.md` | I16 Stage-1AD clause (AD1–AD10) |
| `STAGE_01_TERMINOLOGY.md` | Stage-1AD terminology addendum (`queued_event_record`, `queued_event_registry`, `EventQueueStatus` transition table, `immutable_payload`, `OrdinaryDispatchContext`, `ScheduleEvent` result union, `HandleDispatchIntegrityFailure` / `dispatch_integrity_failure`) |
| `STAGE_01_TRACEABILITY_MATRIX.csv` | Rows R215–R225 (AD1–AD10 + the TV252–TV261 block) |

The miner state machine is not modified — AD1–AD10 concern the scheduler/dispatcher and the retry-record queue lifecycle
only.

## 4. Freeze statement

Stage-1A through Stage-1AC lettered artifacts (`STAGE_01[A-Z]_*`, `STAGE_01AA_*`, `STAGE_01AB_*`, `STAGE_01AC_*`) are
byte-identical to the Stage-1AC parent commit (`c855c6958ed0bf51f0a5ad2ed5a2ece002564d15`). Stage 1AD modifies only the
five normative `STAGE_01_*` documents it touches and adds the fourteen `STAGE_01AD_*` deliverables; every override of a
prior-letter statement is recorded in this register.
