# Stage 1AH — Driver-Request Lifecycle & Event-Loop Ordering Audit (AH4)

**Audit target:** AH4 — explicit driver-request records + event-loop ordering.
**Scope:** documentation-only pseudocode revision (Stage 1AH). This audit inspects ONLY the
final normative tree under `docs/thesis_revision_v45/stage_01/`; the primary artifact is
`STAGE_01_PROTOCOL_PSEUDOCODE.md`. No historical Stage-1A…1AG artifact is modified and no
executable source is claimed.

**Context invariants (unchanged by AH4).** The algorithm is **PoCol** and the mechanism is
**the idle policy within PoCol** (`STAGE_01_PROTOCOL_PSEUDOCODE.md:6`–`7`). The A1 accepted
energy baseline **`8.420833333 kWh`** is unchanged — AH4 is a structural driver-request
lifecycle and event-ordering revision that touches no census value, residency interval, or
transition-energy quantity.

All line anchors below are `file:line` into `STAGE_01_PROTOCOL_PSEUDOCODE.md` unless a different
file is named.

---

## Check AH4.1 — `STRUCTURE driver_request`, its enums, and removal of the bare pending sets

**Requirement.** `STRUCTURE driver_request` exists with fields
`{ DriverRequestID, kind, requested_event_time, payload, status, seated_event_ref, disposition }`;
status enum `{PENDING, SEATED, CONSUMED, REJECTED, CANCELLED}`; kind
`{MINER_JOIN, ORDINARY_RESERVE_DEFICIT}`. The bare `pending_join_requests` /
`pending_ordinary_reserve_deficits` sets must NOT appear as live RunContext fields — only as a
REMOVED/superseded note.

**Evidence.**
- `STRUCTURE driver_request` declared at `2717`, with all seven required fields present:
  `DriverRequestID` (`2718`), `kind` (`2719`), `requested_event_time` (`2720`), `payload` (`2722`),
  `status` (`2723`), `seated_event_ref` (`2724`), `disposition` (`2725`).
- Status enum `DriverRequestStatus in { PENDING, SEATED, CONSUMED, REJECTED, CANCELLED }` at
  `2723` (field) and `2701` (RunContext type comment).
- Kind enum `DriverRequestKind in { MINER_JOIN, ORDINARY_RESERVE_DEFICIT }` at `2719` (field)
  and `2702` (RunContext type comment).
- Bare-pending-set removal: a repository-wide search for `pending_join_requests` /
  `pending_ordinary_reserve_deficits` in the primary file returns exactly ONE hit — `2694` —
  which is the REMOVED/superseded note "it REPLACES the AG4 bare pending sets
  (pending_join_requests / pending_ordinary_reserve_deficits)". Neither name appears as a live
  RunContext field, in `RunInitialise`, or in the `RunContext` RETURNS list. The authoritative
  replacement fields are `driver_request_registry` (`2691`), `driver_request_seq` (`2695`), and
  `pending_driver_request_index` (`2696`), created in `RunInitialise` at `2763`–`2765` and
  returned at `2776`.

**Result: PASS.**

---

## Check AH4.2 — `AdmitDriverRequest` is the named PRODUCER

**Requirement.** `AdmitDriverRequest` mints a DriverRequestID, creates a PENDING record, and adds
it to `pending_driver_request_index`; it is the sole producer.

**Evidence.**
- `PROCEDURE AdmitDriverRequest` declared at `1518`, annotated "the NAMED producer of a
  sim-driver request record"; "This is the ONLY producer of a driver_request; it REPLACES
  appending to the AG bare pending sets" (`1522`).
- Mints the id: `driver_request_seq` incremented (`1524`), immutable
  `drid <- (RunContext.RunID, RunContext.driver_request_seq)` (`1525`).
- Creates a PENDING record: `driver_request(... status = PENDING, seated_event_ref = null,
  disposition = null)` (`1526`–`1527`), stored in the registry (`1528`).
- Adds to the worklist: `ADD drid TO RunContext.pending_driver_request_index` (`1529`); returns
  `driver_request_admitted(drid)` (`1530`).
- Consumers exercise this producer: `RoundInitialise` admits the genesis MINER_JOIN via
  `CALL AdmitDriverRequest(...)` (`2868`).

**Result: PASS.**

---

## Check AH4.3 — `SeatPendingDriverRequests` iterates, routes, inspects, and terminalises

**Requirement.** Iterate PENDING records in stable DriverRequestID order; route
MINER_JOIN → `SeatMinerRegister` and ORDINARY_RESERVE_DEFICIT → `SeatReserveActivate`; inspect
each seat result; terminalise the exact record (SEATED / REJECTED, removed from the pending
index); no seated request left permanently PENDING.

**Evidence.**
- `PROCEDURE SeatPendingDriverRequests` declared at `1533` ("the named SIM-DRIVER intake — routes
  each PENDING request to its owner").
- Stable-order iteration: `FOR EACH drid IN SORT(RunContext.pending_driver_request_index BY
  DriverRequestID ascending)` (`1548`); PENDING-only guard `IF dr.status != PENDING: CONTINUE`
  (`1550`).
- Routing: `CASE MINER_JOIN: ... SeatMinerRegister(...)` (`1552`);
  `CASE ORDINARY_RESERVE_DEFICIT: ... SeatReserveActivate(...)` (`1553`). Both owners take the
  `driver_request` record and return structured results (`SeatMinerRegister` at `1447`,
  RETURNS `1468`–`1469`; `SeatReserveActivate` at `1471`, RETURNS `1497`–`1498`).
- Inspection of each result: `SWITCH res` (`1554`) with explicit cases for seated (`1555`),
  already-seated/replay (`1559`), and seat-failed (`1563`).
- Terminalisation of the exact record and removal from the pending index:
  seated → `status <- SEATED`, `REMOVE drid FROM ... pending_driver_request_index` (`1556`–`1558`);
  replay → `status <- SEATED`, removed (`1560`–`1562`);
  seat-failed → `status <- REJECTED`, removed (`1564`–`1566`).
- "No seated request is left permanently PENDING" restated in the NOTE at `1575`.

**Result: PASS.**

---

## Check AH4.4 — Event-loop ordering fix (Option A): intake BEFORE earliest-time selection

**Requirement.** `RunEventLoopToHorizon` calls `SeatPendingDriverRequests` BEFORE it selects the
next earliest queue `event_time`, so intake can never insert an event earlier than an
already-selected `t`. There must be no "select earliest `t`, then `SeatPendingDriverRequests`,
then process `t`" hazard.

**Evidence.** `PROCEDURE RunEventLoopToHorizon` at `487`. The loop body (`514`–`518`) is:

```
    WHILE true:
      CALL SeatPendingDriverRequests(RunContext)                  # AG4/AH4: named sim-driver intake — runs BEFORE selection
      IF the queue has NO unprocessed event_time t with t < T: BREAK   # AH4: re-check AFTER admission (intake may have added events)
      SET t <- the earliest unprocessed event_time on the queue   # AH4: selection sees every just-admitted driver event
      CALL ProcessEventTime(RunContext, t, is_horizon = false)    # AG3: pass the RUN context; the round is resolved per dispatch
```

The order per iteration is unambiguous: (1) `SeatPendingDriverRequests` at `515`, (2) the
`t`-selection at `517`, (3) `ProcessEventTime(t)` at `518`. Admission precedes selection, so at
admission time there is no selected `t`; a driver event seated by intake is already on the queue
when line `517` picks the earliest time, and the earliest-time selection therefore observes it.
The pre-loop comment at `510`–`513` states this is AH4 Option A and that it removes the AG hazard
"select earliest t, then insert a driver event earlier than t, then process the old t". No such
"select-then-seat-then-process" sequence appears anywhere in the procedure.

`SeatPendingDriverRequests`' own PRECONDITIONS restate the guarantee: it is "called by
RunEventLoopToHorizon BEFORE it selects the next earliest queue event_time … and can NEVER be
earlier than an already-selected t (there is no selected t at admission time)" (`1535`–`1537`).

**Result: PASS.**

---

## Check AH4.5 — Structural proof text present (intake before selection ⇒ no earlier insertion)

**Requirement.** The structural proof that intake-before-selection prevents any earlier
insertion is present in the final text.

**Evidence.**
- Pre-loop proof: "ADMIT + SEAT all pending sim-driver requests BEFORE selecting the next
  earliest queue event_time, so a driver event this intake seats is ALREADY on the queue when
  the selection runs — it can never be inserted EARLIER than an already-selected t (there is no
  selected t during admission). This removes the AG hazard …" (`510`–`513`).
- Procedure NOTE proof: "the loop SEATS all pending sim-driver requests
  (SeatPendingDriverRequests) BEFORE it selects the next earliest queue event_time, so a
  just-admitted driver event is always visible to the selection and can never be inserted earlier
  than an already-selected t" (`538`–`541`).
- Corroborated by the supersession register entry certifying this audit
  (`STAGE_01AH_SUPERSESSION_REGISTER.md:35`–`39`).

**Result: PASS.**

---

## Overall verdict

**PASS.** All five AH4 requirements are satisfied against the final normative text of
`STAGE_01_PROTOCOL_PSEUDOCODE.md`: the explicit `driver_request` structure with its complete
field set and both enums exists (`2717`–`2725`, `2701`–`2702`) with the bare pending sets removed
to a superseded note (`2694`); `AdmitDriverRequest` is the sole named producer (`1518`–`1531`);
`SeatPendingDriverRequests` iterates PENDING records in stable DriverRequestID order, routes,
inspects, and terminalises each exact record with no seated request left permanently PENDING
(`1533`–`1575`); `RunEventLoopToHorizon` runs `SeatPendingDriverRequests` before the
earliest-time selection under Option A with no select-then-seat-then-process hazard
(`487`, `510`–`518`, `538`–`543`); and the structural proof text is present (`510`–`513`,
`538`–`541`). The algorithm remains **PoCol**, the mechanism remains **the idle policy within
PoCol**, and the A1 baseline **`8.420833333 kWh`** is unchanged. No defects require a fix.
