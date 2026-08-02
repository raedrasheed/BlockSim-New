# Stage 1AC — Event-Reference & Dispatch-Ownership Audit (AC1, AC2)

This audit verifies corrections **AC1** and **AC2**: the pseudocode now defines **one** canonical, immutable `EventRef`
type — `EventRef = (envelope_namespace, event_type, event_time, delta_cycle, microphase, seq)` — that `ScheduleEvent`
derives from the envelope it creates and returns as `scheduled(EventRef, envelope)`; and that same reference is **threaded
by the dispatcher** through `ProcessEventTime` (via `EventQueueContext.current_event_ref`) and injected into the handler as
`dispatched_event_ref`, from which `SetupRetryEvent` reads it as a **mandatory** input rather than from its own payload.
Cancellation, stored retry ownership (`seat_event_ref`), and dispatch ownership (`dispatched_event_ref`) all use the SAME
type; `event_ref`, `envelope`, and `dispatched_event_ref` are not silently interchangeable.

Scope is documentation-only. The algorithm is **PoCol** and the mechanism is the idle policy within PoCol. The A1 baseline
`8.420833333 kWh` is unchanged. No Stage-1A–1AB historical artifact is modified. All lines are quoted from the current
normative documents; line anchors are approximate.

Sources of truth (read-only): `STAGE_01_PROTOCOL_PSEUDOCODE.md`, `STAGE_01_ROUND_STATE_MACHINE.md`. This audit occupies
the `STAGE_01AC_EVENT_REFERENCE_DISPATCH_AUDIT.md` slot of the Stage-1AC deliverable set recorded in
`STAGE_01AC_CORRECTION_REPORT.md` and registered in `STAGE_01AC_SUPERSESSION_REGISTER.md`; the immutable-identity lifecycle
is audited in the peer `STAGE_01AC_EVENT_REFERENCE_LIFECYCLE_AUDIT.md`, the guard order in
`STAGE_01AC_RETRY_GUARD_ORDER_AUDIT.md`, the signature contract in `STAGE_01AC_PROCEDURE_SIGNATURE_CALL_AUDIT.md`, and the
vectors in `STAGE_01AC_SEMANTIC_TEST_VECTORS.md`.

---

## 1. AC1 — the ONE canonical `EventRef` type — PASS

`STRUCTURE EventRef` (`STAGE_01_PROTOCOL_PSEUDOCODE.md`, §0.7e, line 431) declares the single immutable reference and
enumerates exactly the six fields, with an explicit statement that it is NOT a prose alias:

```
431 STRUCTURE EventRef (AC1 — the ONE canonical immutable reference to a queued ordinary event)
432   # AC1: EventRef = (envelope_namespace, event_type, event_time, delta_cycle, microphase, seq). ScheduleEvent DERIVES it
433   #   from the envelope it creates; because seq is the per-run monotonic event_creation_seq (J4, globally unique per run),
434   #   an EventRef identifies EXACTLY ONE queued event. EventRef(envelope) projects those six fields. It is the SAME type
435   #   used by (a) ScheduleEvent's result, (b) stored retry ownership (setup_retry_record.seat_event_ref), and (c) dispatch
436   #   ownership (dispatched_event_ref, injected by ProcessEventTime). It is IMMUTABLE and NOT a prose alias for an
437   #   unspecified subset of an envelope; `event_ref`, `envelope`, and `dispatched_event_ref` are NOT silently interchangeable
438   #   — an envelope is the full queued record, an EventRef is its canonical six-field identity.
439   envelope_namespace
440   event_type
441   event_time
442   delta_cycle
443   microphase
444   seq
```

The comment names the three consumers of the type verbatim — (a) `ScheduleEvent`'s result, (b) stored retry ownership
`setup_retry_record.seat_event_ref`, (c) dispatch ownership `dispatched_event_ref` — and states the immutable, six-field,
non-alias, non-interchangeable properties in one place.

Immediately after the structure, the `EventQueueStatus` note (lines 446–449, directly preceding `PROCEDURE ScheduleEvent`
at line 451) keeps the mutable queue-lifecycle state **separate** from the immutable identity, so cancellation touches
status, never the seat `EventRef`:

```
446 # AC8 event-queue lifecycle state (kept SEPARATE from the immutable EventRef identity):
447 # EventQueueStatus in { QUEUED, DISPATCHING, CONSUMED, CANCELLED }. A retry record stores its IMMUTABLE seat_event_ref
448 #   (never destroyed) AND an event_queue_status; cancellation changes the status, it does NOT erase the seat EventRef used
449 #   for replay-ownership auditing.
```

**Finding: PASS.** `EventRef` is defined once, as an immutable six-field type; the queue-lifecycle status is a separate
concern; the type is explicitly not a prose alias and its three consumers are named.

---

## 2. AC1 — `ScheduleEvent` derives exactly one `EventRef` and returns `scheduled(EventRef, envelope)` — PASS

`PROCEDURE ScheduleEvent` (line 451) derives the canonical reference from the envelope it just created and inserted, then
returns both the reference and the envelope. Quoting the derive step and the return (lines 501–506):

```
501     # AC1 (6): DERIVE the ONE canonical EventRef from the envelope just created. seq is globally unique per run (J4), so
502     #     this EventRef identifies EXACTLY the queued envelope. It is the SAME type used by cancellation, stored retry
503     #     ownership (seat_event_ref), and dispatch ownership (dispatched_event_ref).
504     SET event_ref <- EventRef(envelope_namespace = ORDINARY_EVENT, event_type = event_type,
505                               event_time = target_event_time, delta_cycle = dc, microphase = target_microphase, seq = seq)
506   RETURNS: scheduled(event_ref, envelope)   # AC1: the canonical EventRef AND the envelope (was scheduled(envelope)); NOT interchangeable
```

The six constructor arguments at lines 504–505 match the six `STRUCTURE EventRef` fields exactly, and `seq` is the per-run
monotonic `event_creation_seq` minted at lines 490–491, so the derived `EventRef` identifies exactly the one envelope
inserted at line 499. The return type is `scheduled(event_ref, envelope)` — the inline comment records that this
**replaces** the former `scheduled(envelope)` and that the two members are not interchangeable.

**Finding: PASS.** `ScheduleEvent` derives exactly one `EventRef` (all six fields) and returns `scheduled(event_ref,
envelope)`; the reference and the envelope are distinct, co-returned members.

---

## 3. AC2 — `EventQueueContext.current_event_ref : EventRef | null`, initialised null — PASS

`EventQueueContext` (§0.7e) gains the dispatcher-owned field (lines 384–388):

```
384   current_event_ref     : AC2 — EventRef | null. The canonical EventRef of the event currently being dispatched, SET by
385                           ProcessEventTime from the dispatched event's OWN envelope immediately before dispatch and CLEARED
386                           after the handler returns. It is the dispatcher-owned source of `dispatched_event_ref` — a
387                           handler (e.g. SetupRetryEvent) NEVER reads its own future EventRef from its payload or an
388                           undocumented derivation; the dispatcher injects the reference of the ACTUAL event being dispatched.
```

`RunInitialise` (the sole per-run field creator, line 1628) initialises the field to `null` alongside the other `current_*`
dispatch state (line 1634):

```
1633     INITIALISE EventQueueContext EQ WITH event_queue = empty, current_event_time = 0, current_delta_cycle = 0,
1634                current_microphase = 0, current_event_seq = 0, current_event_ref = null, event_creation_seq = 0,   # AC2: current_event_ref
```

**Finding: PASS.** `EventQueueContext.current_event_ref` is typed `EventRef | null`, owned by `ProcessEventTime`, and
initialised to `null` once per run in `RunInitialise`.

---

## 4. AC2 — `ProcessEventTime` SETs, INJECTs, and CLEARs the reference around dispatch — PASS

Inside the drain loop of `ProcessEventTime`, the dispatcher sets `EQ.current_event_ref` to the dispatched event's canonical
`EventRef`, injects it as `dispatched_event_ref`, and clears it after the handler returns (lines 223–228):

```
223         # AC2: the DISPATCHER owns the EventRef. Set EQ.current_event_ref to e's canonical EventRef and inject it as
224         #      dispatched_event_ref so a handler (e.g. SetupRetryEvent) verifies ownership against the ACTUAL dispatched
225         #      event — never from its own payload and never from an undocumented derivation. Cleared after the handler returns.
226         SET EQ.current_event_ref <- EventRef(e)                   # AC2: EventRef(e) = the six-field identity of e's envelope
227         DISPATCH e WITH dispatch_envelope = dispatch_envelope, dispatched_event_ref = EQ.current_event_ref   # AC2
228         SET EQ.current_event_ref <- null                          # AC2: cleared after the handler returns
```

Three ordered actions are present and unambiguous: **SET** (line 226, from `EventRef(e)`), **INJECT** (line 227,
`dispatched_event_ref = EQ.current_event_ref` on the `DISPATCH`), and **CLEAR** (line 228, back to `null`). The dispatcher
is therefore the sole owner of the reference the handler receives.

**Finding: PASS.** `ProcessEventTime` sets `EQ.current_event_ref <- EventRef(e)` before dispatch, injects
`dispatched_event_ref = EQ.current_event_ref`, and clears it after the handler returns.

---

## 5. AC2 — driver-entry seating table: the `SetupRetryEvent` row declares `dispatched_event_ref` mandatory — PASS

The driver-entry seating table (§0.7g-driver, line 587) `SetupRetryEvent` row (line 599) adds `dispatched_event_ref` to the
required envelope fields and marks it a mandatory, dispatcher-injected input, never read from the payload:

```
599 | `SetupRetryEvent` | `SetupRetryEvent` | `ROUND_SETUP` | `(RoundID, setup_kind, SetupRetryID, TemplateID_at_seat, TemplateRefreshSetupID, retry_generation)` | `event_time, delta_cycle, event_seq` + `dispatched_event_ref` (AC2: ProcessEventTime injects `EQ.current_event_ref = EventRef(e)`; a MANDATORY input, never read from the payload) | no (...) |
```

`SetupRetryEvent` is the only seated handler whose "Required envelope fields" cell names `dispatched_event_ref`, consistent
with it being the only handler that performs EventRef ownership matching against a stored `seat_event_ref`.

**Finding: PASS.** The seating table's `SetupRetryEvent` row lists `dispatched_event_ref` as a required, dispatcher-injected
(`EventRef(e)`) input, explicitly not from the payload.

---

## 6. AC2 — `SetupRetryEvent` signature takes `dispatched_event_ref` as mandatory; ownership uses it against `seat_event_ref` — PASS

`PROCEDURE SetupRetryEvent` (line 2090) lists `dispatched_event_ref` in its `INPUTS` and documents that it is injected by
`ProcessEventTime`, never read from the payload, and mandatory (lines 2091–2102):

```
2091   INPUTS: RoundContext, dispatch_envelope, dispatched_event_ref, RoundID, setup_kind, SetupRetryID,
2092           TemplateID_at_seat, TemplateRefreshSetupID, retry_generation, reason
...
2097           # AC2: dispatched_event_ref is the canonical EventRef of THIS dispatched SetupRetryEvent, INJECTED by
2098           #   ProcessEventTime from EQ.current_event_ref (the dispatcher owns it). It is NEVER read from the payload and
2099           #   NEVER derived by prose; it is a MANDATORY input (the dispatch contract guarantees ProcessEventTime always
2100           #   supplies it — TV245). Ownership compares it against the IMMUTABLE rec.seat_event_ref (AC1/AC8).
```

The PRECONDITIONS reinforce that both the envelope and the reference come from `ProcessEventTime` (lines 2101–2102). The
ownership step (guard step 3) compares the injected reference against the immutable stored seat reference (lines 2119–2123):

```
2119     # (3) AC5 EVENTREF OWNERSHIP against the IMMUTABLE seat EventRef (AC1/AC8). CASE B — a foreign / replayed event carries a
2120     #   valid SetupRetryID but a DIFFERENT EventRef: it does NOT own the record; stale-noop and LEAVE the record SEATED for
2121     #   its genuine queued event (never consume ownership on a foreign ref). Uses seat_event_ref, which cancellation NEVER erases.
2122     IF dispatched_event_ref != rec.seat_event_ref:
2123       RETURN setup_retry_stale_noop(SetupRetryID)           # AC5-B: foreign/replayed dispatch; genuine event remains seated
```

The comparison at line 2122 is `dispatched_event_ref != rec.seat_event_ref` — both operands are the same `EventRef` type
(AC1), the left from the dispatcher-owned injection path (AC2), the right the immutable stored seat (AC1/AC8). No payload
field is consulted for ownership.

**Finding: PASS.** `SetupRetryEvent` takes `dispatched_event_ref` as a mandatory input sourced from the dispatcher, and its
step-3 ownership check compares it against the immutable `rec.seat_event_ref`.

---

## 7. AC1/AC2 — both retry seating sites store `seat_event_ref = the returned EventRef` — PASS

Both call sites that seat a `SetupRetryEvent` bind the seat's EventRef from `scheduled(event_ref, envelope)` and store it as
`seat_event_ref`.

**(a) PARTICIPANT_SETUP** — `PrepareParticipantsForNewRound` (lines 1941–1947):

```
1941       IF r = scheduled(event_ref, envelope):   # AC1: ScheduleEvent returns the canonical EventRef + envelope
1942         # Z1/AC8: publish the setup_retry_record ATOMICALLY with status = SEATED, seat_event_ref = the EventRef (immutable),
1943         #   event_queue_status = QUEUED, AFTER the successful ScheduleEvent. The seat is the ONLY CREATE (AB3).
1944         ATOMICALLY: SET setup_retry_records[srid] <- setup_retry_record(SetupRetryID = srid, setup_kind = PARTICIPANT_SETUP,
1945               RoundID = RoundID_current, TemplateID_at_seat = TemplateID_committed, TemplateRefreshSetupID = null,
1946               retry_generation = g, seat_event_ref = event_ref, event_queue_status = QUEUED, status = SEATED,
1947               target_disposition = null, terminal_closure_pending = false)   # Z1/AA2/AC1/AC8
```

**(b) TEMPLATE_REFRESH_SETUP** — `ContinueTemplateRefreshAssignmentSetup` (lines 5348–5354):

```
5348       IF r = scheduled(event_ref, envelope):   # AC1: ScheduleEvent returns the canonical EventRef + envelope
5349         # Z1/AC8: publish the setup_retry_record ATOMICALLY with status = SEATED, seat_event_ref = the EventRef (immutable),
5350         #   event_queue_status = QUEUED, AFTER the successful ScheduleEvent. The seat is the ONLY CREATE (AB3).
5351         ATOMICALLY: SET setup_retry_records[srid] <- setup_retry_record(SetupRetryID = srid, setup_kind = TEMPLATE_REFRESH_SETUP,
5352               RoundID = RoundID_current, TemplateID_at_seat = TemplateID, TemplateRefreshSetupID = TemplateRefreshSetupID,
5353               retry_generation = g, seat_event_ref = event_ref, event_queue_status = QUEUED, status = SEATED,
5354               target_disposition = null, terminal_closure_pending = false)   # Z1/AA2/AC1/AC8
```

In both sites the pattern-match `IF r = scheduled(event_ref, envelope)` (lines 1941, 5348) binds `event_ref` to the
`EventRef` co-returned by `ScheduleEvent`, and the record stores `seat_event_ref = event_ref` (lines 1946, 5353) alongside
`event_queue_status = QUEUED` and `status = SEATED`. This is exactly the reference the dispatcher will later inject and the
step-3 ownership check will match. The registry field type is fixed at `seat_event_ref : EventRef (immutable, AC1/AC8)`
(`STRUCTURE RunContext`, line 1614).

**Finding: PASS.** Both seating sites store `seat_event_ref = event_ref`, where `event_ref` is the `EventRef` from
`scheduled(event_ref, envelope)`; the stored field is typed `EventRef` and immutable.

---

## 8. Cancellation, ownership, and dispatch all use the `EventRef` type; no bare `scheduled(envelope)`; no silent interchange — PASS

**One type across all three roles.** The `STRUCTURE EventRef` comment (lines 434–436) names the three consumers, and each
is realised in the pseudocode with that type:

- **`ScheduleEvent`'s result** — `scheduled(event_ref, envelope)` (line 506), `event_ref` derived at lines 504–505.
- **Stored retry ownership** — `setup_retry_record.seat_event_ref : EventRef` (registry declaration line 1614; stored at
  lines 1946 and 5353; matched at line 2122).
- **Dispatch ownership** — `dispatched_event_ref`, injected from `EQ.current_event_ref` (`= EventRef(e)`) at lines 226–227,
  received as a mandatory input at line 2091.

The wake path uses the same type for the same purpose: `StartWake` binds `wake_event_ref <- event_ref` from a
`scheduled(event_ref, envelope)` seat (lines 1418–1422), and rollback/cancel operations cancel that reference (e.g.
`CANCEL WakeEventRef on EQ`, line 1978). Cancellation of a retry record changes only `event_queue_status` and never erases
the immutable `seat_event_ref` (lines 447–449; AC8 note lines 1028–1032), so ownership auditing survives cancellation.

**No bare `scheduled(...)` without an envelope.** Every result-shaped occurrence of `scheduled(` in
`STAGE_01_PROTOCOL_PSEUDOCODE.md` is the two-member `scheduled(event_ref, envelope)` form — the definition (line 506) and
every consumer (lines 1418, 1941, 3285, 3440, 3899, 5348). The one remaining occurrence, `IF r != scheduled(...)` at line
3037, is a negative wildcard shape-match (any `scheduled(...)` result), not a bare single-member `scheduled(envelope)`
constructor. No `scheduled(envelope)` (envelope-only) and no `scheduled(event_ref)` (ref-only) return form remains.

**No silent interchange.** The type comment (lines 437–438) and the §0.8 addendum (line 997) both state that `event_ref`,
`envelope`, and `dispatched_event_ref` are NOT silently interchangeable; consumers that need the canonical identity read
`event_ref` / `seat_event_ref` / `dispatched_event_ref`, and consumers that need the full queued record read `envelope` /
`dispatch_envelope`. `SetupRetryEvent` ownership uses the reference (line 2122); its payload-integrity check uses the
`dispatch_envelope` and payload separately (lines 2159–2161) — the two are never conflated.

**Finding: PASS.** The single `EventRef` type serves the result, stored-ownership, and dispatch-ownership roles (and the
wake ref); no bare `scheduled(envelope)`/`scheduled(event_ref)` form survives; and the reference and the envelope are never
silently interchanged.

---

## 9. Test-vector linkage (TV244, TV245)

`STAGE_01AC_SEMANTIC_TEST_VECTORS.md` exercises AC1/AC2 as **TV244** and **TV245**.

**TV244 — dispatch ownership succeeds via the injected ref** (line 16). Its setup and expectation match this audit exactly:
`ScheduleEvent` seats one `SetupRetryEvent` and returns `scheduled(E, envelope)`; the seat publishes
`setup_retry_records[srid]` with `seat_event_ref = E` (§7 above); `ProcessEventTime` later dispatches that event, setting
`EQ.current_event_ref <- EventRef(e)` and injecting `dispatched_event_ref = EQ.current_event_ref` (§4 above); because
`EventRef(e) = E`, the step-3 ownership check `dispatched_event_ref = rec.seat_event_ref` succeeds using the
dispatcher-injected value with no ambient/derived reference read (§6 above). Its procedures are the seating procedure,
`ScheduleEvent`, `ProcessEventTime`, and `SetupRetryEvent` (lines 18–25); coverage classes AC1/AC2/AC8 (line 97).

**TV245 — `dispatched_event_ref` mandatory; a missing ref is rejected at the signature/dispatch audit** (line 27). A
dispatch that fails to supply `dispatched_event_ref` is rejected because the input is mandatory (signature line 2091; row
line 599) and the dispatch contract (AC2) requires `ProcessEventTime` to set `EQ.current_event_ref` and inject it on every
dispatch (lines 226–227); no handler may execute with an undefined `dispatched_event_ref` (vector lines 31–34, which cite
`STAGE_01AC_PROCEDURE_SIGNATURE_CALL_AUDIT.md` recording the input as mandatory and dispatcher-supplied). Coverage class
AC2 (line 98). The mandatory-input guarantee is asserted in the signature comment itself (line 2099, naming TV245).

Both vectors preserve the A1 baseline `8.420833333 kWh`.

---

## 10. Cross-document consistency

The AC1/AC2 statement is identical in substance across the pseudocode structures/procedures, the §0.8 correction addenda,
and the round state machine §3.10g.

| Document | Anchor | Statement of AC1/AC2 |
|----------|--------|----------------------|
| `STAGE_01_PROTOCOL_PSEUDOCODE.md` — `STRUCTURE EventRef` | §0.7e l.431–444 | `EventRef` = six fields; ONE immutable reference; the three consumers named; not a prose alias; not interchangeable |
| `STAGE_01_PROTOCOL_PSEUDOCODE.md` — `EventQueueStatus` note | l.446–449 | queue lifecycle kept SEPARATE from the immutable seat `EventRef`; cancellation changes status only |
| `STAGE_01_PROTOCOL_PSEUDOCODE.md` — `ScheduleEvent` | derive l.504–505; return l.506 | derives one `EventRef`; `RETURNS: scheduled(event_ref, envelope)` (was `scheduled(envelope)`) |
| `STAGE_01_PROTOCOL_PSEUDOCODE.md` — `EventQueueContext` / `RunInitialise` | l.384–388; l.1634 | `current_event_ref : EventRef | null`; initialised `null` per run |
| `STAGE_01_PROTOCOL_PSEUDOCODE.md` — `ProcessEventTime` | l.226–228 | SET `EQ.current_event_ref <- EventRef(e)`; INJECT `dispatched_event_ref = EQ.current_event_ref`; CLEAR to `null` |
| `STAGE_01_PROTOCOL_PSEUDOCODE.md` — seating table | l.599 | `SetupRetryEvent` requires `dispatched_event_ref`; MANDATORY; dispatcher-injected; not from payload |
| `STAGE_01_PROTOCOL_PSEUDOCODE.md` — `SetupRetryEvent` | INPUTS l.2091–2100; ownership l.2122 | `dispatched_event_ref` mandatory input from `ProcessEventTime`; matched `!= rec.seat_event_ref` |
| `STAGE_01_PROTOCOL_PSEUDOCODE.md` — seating sites | l.1946; l.5353 | `seat_event_ref = event_ref` (the returned `EventRef`), both retry kinds |
| `STAGE_01_PROTOCOL_PSEUDOCODE.md` — §0.8 addenda AC1/AC2 | l.993–1002 | canonical `EventRef` type + dispatcher-owned threading; not silently interchangeable; mandatory input |
| `STAGE_01_ROUND_STATE_MACHINE.md` — §3.10g AC1 | l.914–918 | `EventRef` = six fields, ONE immutable ref; `ScheduleEvent` returns `scheduled(EventRef, envelope)`; cancellation / `seat_event_ref` / `dispatched_event_ref` all use this type; not interchangeable |
| `STAGE_01_ROUND_STATE_MACHINE.md` — §3.10g AC2 | l.920–923 | `EventQueueContext` gains `current_event_ref : EventRef | null`; `ProcessEventTime` sets/injects/clears; `SetupRetryEvent` receives it from the dispatcher path, never the payload, as a mandatory input |

All anchors agree: one immutable six-field `EventRef`; `ScheduleEvent` derives it and returns `scheduled(event_ref,
envelope)`; the dispatcher owns and threads it through `ProcessEventTime`; `SetupRetryEvent` reads it as a mandatory input
and matches it against the immutable `seat_event_ref`; and the reference is never conflated with the envelope. No
contradiction was found across the documents.

---

## 11. Verification summary

| # | Check | Result |
|---|-------|--------|
| 1 | `EventRef` defined once as an immutable six-field type; queue status kept separate (`EventQueueStatus`) | PASS |
| 2 | `ScheduleEvent` derives one `EventRef` and returns `scheduled(event_ref, envelope)` | PASS |
| 3 | `EventQueueContext.current_event_ref : EventRef | null`; `RunInitialise` initialises it `null` | PASS |
| 4 | `ProcessEventTime` SETs `EventRef(e)`, INJECTs `dispatched_event_ref`, CLEARs after the handler | PASS |
| 5 | Seating-table `SetupRetryEvent` row lists `dispatched_event_ref` as a mandatory, dispatcher-injected input | PASS |
| 6 | `SetupRetryEvent` signature takes `dispatched_event_ref` (mandatory); step-3 ownership uses it vs `seat_event_ref` | PASS |
| 7 | Both retry seats store `seat_event_ref = the returned EventRef` from `scheduled(event_ref, envelope)` | PASS |
| 8 | Cancellation / ownership / dispatch all use the `EventRef` type; no bare `scheduled(envelope)`; no silent interchange | PASS |
| 9 | TV244 (ownership via injected ref) and TV245 (missing ref rejected) linkage confirmed | PASS |
| 10 | Cross-document consistency (pseudocode structures/procedures ↔ §0.8 addenda ↔ round-SM §3.10g) | PASS |

**Result:** AC1 and AC2 PASS. There is one canonical, immutable `EventRef = (envelope_namespace, event_type, event_time,
delta_cycle, microphase, seq)`; `ScheduleEvent` derives exactly one from the envelope and returns `scheduled(event_ref,
envelope)`; `ProcessEventTime` owns and threads it through `EQ.current_event_ref` (SET → INJECT → CLEAR); `SetupRetryEvent`
receives `dispatched_event_ref` as a mandatory dispatcher-supplied input and matches it against the immutable
`seat_event_ref` stored at both seating sites; cancellation, stored ownership, and dispatch ownership all use the same
type, no bare `scheduled(envelope)` form remains, and the reference and the envelope are never silently interchanged.
TV244 exercises the successful injected-ref dispatch and TV245 the rejection of a missing reference. The revision is
documentation-only; the algorithm is PoCol with the idle policy within PoCol; the A1 baseline `8.420833333 kWh` is
preserved.
