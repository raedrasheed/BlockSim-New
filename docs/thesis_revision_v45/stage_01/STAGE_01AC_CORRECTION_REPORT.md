# Stage 1AC — Correction Report (event-reference & retry-state closure lock)

Stage 1AC is a narrow, documentation-only revision of the Stage-1 formal specification of **PoCol** and the idle policy
within PoCol. It closes eight defects (AC1–AC8) by defining one canonical `EventRef` type, threading it from
`ScheduleEvent` through `ProcessEventTime` to the handler, reordering the `SetupRetryEvent` guard so a terminal replay is
suppressed before payload integrity, scoping an integrity failure to the record's own round, forbidding a malformed
genuine dispatch from leaving its record `SEATED`, making every guard-driven abort follow a legal status path, declaring an
authoritative `SetupRetryStatus` transition table with a named guard, and keeping the immutable event identity separate
from queue state. It changes only the five normative `STAGE_01_*` documents it touches and adds twelve `STAGE_01AC_*`
deliverables. No executable source, configuration, DOCX, or PDF is touched; no experiment is run; the A1 baseline
(`8.420833333 kWh`) is unchanged; and no Stage-1A–1AB historical artifact is modified.

- **Branch:** `thesis-v45-pocol-stage1ac-event-reference-retry-state-lock`
- **Parent commit:** `b575bfa64c25571ffe4359557011a316492e374c` (Stage 1AB)

## Corrections

### AC1 — Define one canonical EventRef type

`EventRef = (envelope_namespace, event_type, event_time, delta_cycle, microphase, seq)` is the one immutable reference to a
queued ordinary event (`STRUCTURE EventRef`). `ScheduleEvent` derives exactly one `EventRef` from the envelope it creates
and returns `scheduled(EventRef, envelope)` (was `scheduled(envelope)`). Cancellation, stored retry ownership
(`seat_event_ref`), and dispatch ownership (`dispatched_event_ref`) all use this type. `EventRef` is not a prose alias for
a subset of an envelope, and `event_ref` / `envelope` / `dispatched_event_ref` are not silently interchangeable. *(Audit:
`STAGE_01AC_EVENT_REFERENCE_DISPATCH_AUDIT.md`; vector TV244.)*

### AC2 — Thread EventRef through ProcessEventTime

`EventQueueContext` gains `current_event_ref : EventRef | null`. When `ProcessEventTime` removes event `e` for dispatch it
sets `EQ.current_event_ref <- EventRef(e)`, dispatches with `dispatch_envelope` and `dispatched_event_ref =
EQ.current_event_ref`, and clears `EQ.current_event_ref` after the handler returns. `SetupRetryEvent` receives
`dispatched_event_ref` from this dispatcher-owned path — never from its payload and never from an undocumented derivation —
as a mandatory input. `ProcessEventTime`, `ScheduleEvent`, `EventQueueContext`, `RunInitialise`, the driver-entry seating
table, `SetupRetryEvent`'s signature, and both retry seating sites are updated. *(Audit:
`STAGE_01AC_EVENT_REFERENCE_DISPATCH_AUDIT.md`; vector TV245.)*

### AC3 — Check terminal replay before payload integrity

`SetupRetryEvent`'s guard order is: (1) validate enough structure to resolve `SetupRetryID`; (2) resolve the record;
(3) verify dispatched `EventRef` ownership; (4) if `status != SEATED` return `setup_retry_duplicate_suppressed` — BEFORE any
payload-integrity abort; (5) determine stale/closed-round disposition from the immutable record; (6) only for a current
owned `SEATED` record validate the payload; (7) current-round target guards + execution. A replay of an `APPLIED` /
`SUPERSEDED` / `CANCELLED` / `ABORTED` retry never aborts a round because replayed payload fields differ. *(Audit:
`STAGE_01AC_RETRY_GUARD_ORDER_AUDIT.md`; vector TV246.)*

### AC4 — Scope integrity failure to the record's round

Membership in the current round is decided from the IMMUTABLE record fields (`rec.RoundID = RoundID_current`, the record's
round nonterminal, `rec.TemplateID_at_seat` current) — never untrusted payload fields. A record of an older or terminal
round is terminalised `SUPERSEDED` / `CANCELLED`; the current round is NOT aborted. A corrupted historical retry event can
never abort a later round. *(Audit: `STAGE_01AC_STALE_INTEGRITY_SCOPE_AUDIT.md`; vector TV247.)*

### AC5 — Do not leave a known record SEATED on malformed dispatch

Case A (structurally invalid / unknown `SetupRetryID`) → stale no-op, no record. Case B (known id but foreign
`dispatched_event_ref ≠ rec.seat_event_ref`) → stale no-op that LEAVES the genuine event seated. Case C (known id and
genuine `EventRef` but an incomplete dispatch envelope or a payload mismatch) → corruption of the owning event:
terminalise the record, store an exact integrity disposition, and take the declared current-round integrity-abort path only
if the record belongs to the current nonterminal round. The genuine owned event may not be consumed while the record
remains `SEATED`. *(Audit: `STAGE_01AC_STALE_INTEGRITY_SCOPE_AUDIT.md`; vector TV248.)*

### AC6 — Make guard-driven aborts follow a legal status path

A current `SEATED` retry about to execute any aborting guard first moves `SEATED → APPLYING`, then `SET disp <- CALL
RoundAbort(...)`, then (after `CancelSetupRetriesForRound` persists `terminal_closure_pending`) `APPLYING → ABORTED`.
`CancelSetupRetriesForRound` therefore sees `APPLYING` and sets `terminal_closure_pending` rather than changing the record
to `CANCELLED`. A terminal `SetupRetryStatus` never transitions to another terminal status; in particular
`CANCELLED → ABORTED` is forbidden. *(Audit: `STAGE_01AC_RETRY_STATUS_TRANSITION_AUDIT.md`; vector TV249.)*

### AC7 — Declare the SetupRetryStatus transition table

Authoritative table: `SEATED → {APPLYING, CANCELLED, SUPERSEDED}`; `APPLYING → {APPLIED, SUPERSEDED, CANCELLED, ABORTED}`;
`APPLIED` / `SUPERSEDED` / `CANCELLED` / `ABORTED` are terminal. Every `UPDATE` of `setup_retry_records[*].status` routes
through the named guard `SetSetupRetryStatus`, which rejects every illegal transition — especially a terminal → terminal
rewrite — with no mutation. *(Audit: `STAGE_01AC_RETRY_STATUS_TRANSITION_AUDIT.md`; vector TV250.)*

### AC8 — Keep immutable event identity separate from queue state

The retry record carries `seat_event_ref : EventRef` (immutable, set at seat) and `event_queue_status : EventQueueStatus`
(`{QUEUED, DISPATCHING, CONSUMED, CANCELLED}`). Ownership comparisons use the immutable `seat_event_ref`; cancellation
changes `event_queue_status` (and consumption marks `CONSUMED`) and never destroys the historical identity of the event
that owned the retry record. This pair replaces the Z1-era single `event_ref` field. *(Audit:
`STAGE_01AC_EVENT_REFERENCE_LIFECYCLE_AUDIT.md`; vector TV251.)*

## Deliverables (12 new `STAGE_01AC_*` files)

1. `STAGE_01AC_CORRECTION_REPORT.md` (this file)
2. `STAGE_01AC_EVENT_REFERENCE_DISPATCH_AUDIT.md` (AC1/AC2)
3. `STAGE_01AC_RETRY_GUARD_ORDER_AUDIT.md` (AC3)
4. `STAGE_01AC_STALE_INTEGRITY_SCOPE_AUDIT.md` (AC4/AC5)
5. `STAGE_01AC_RETRY_STATUS_TRANSITION_AUDIT.md` (AC6/AC7)
6. `STAGE_01AC_EVENT_REFERENCE_LIFECYCLE_AUDIT.md` (AC8)
7. `STAGE_01AC_PROCEDURE_SIGNATURE_CALL_AUDIT.md`
8. `STAGE_01AC_PROCEDURE_CALL_GRAPH.md`
9. `STAGE_01AC_SEMANTIC_TEST_VECTORS.md` (TV244–TV251)
10. `STAGE_01AC_SUPERSESSION_REGISTER.md`
11. `STAGE_01AC_CROSS_DOCUMENT_AUDIT.md`
12. `STAGE_01AC_CHECKSUM_MANIFEST.sha256`

## Modified normative documents (5)

`STAGE_01_PROTOCOL_PSEUDOCODE.md`, `STAGE_01_ROUND_STATE_MACHINE.md` (adds §3.10g), `STAGE_01_INVARIANT_CATALOGUE.md`
(I16 Stage-1AC clause), `STAGE_01_TERMINOLOGY.md` (Stage-1AC addendum), `STAGE_01_TRACEABILITY_MATRIX.csv` (rows
R206–R214). The miner state machine is not touched (AC1–AC8 concern the scheduler/dispatcher and the retry-record
lifecycle only).

## Discipline

Documentation-only; the algorithm remains **PoCol** and the mechanism remains the idle policy within PoCol; the A1
baseline `8.420833333 kWh` is unchanged; the call graph resolves with 87 callables (86 procedures + 1 function) and 0
dangling references (Stage 1AC adds the one new procedure `SetSetupRetryStatus`, defined once and called at the setup-retry
status sites); and Stage 2 is not begun.
