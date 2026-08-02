# Stage 1AD — Queue-Status Ownership Audit (correction AD4)

This is a documentation-only audit of correction **AD4** ("`ProcessEventTime` is the SOLE queue-status owner") in the
Stage-1 formal specification of **PoCol** and the idle policy within PoCol. It verifies, against the frozen source of
truth `STAGE_01_PROTOCOL_PSEUDOCODE.md` (read-only), that the entire dispatch lifecycle of the central
`queued_event_record.queue_status` field is owned by `ProcessEventTime`: BEFORE dispatch it asserts `QUEUED`, moves
`QUEUED → DISPATCHING`, sets `EQ.current_event_ref`, and builds a trusted `OrdinaryDispatchContext`; and AFTER the
handler returns ("after-final") it moves `DISPATCHING → CONSUMED` and clears `EQ.current_event_ref` — including on the
dispatcher-owned integrity path. It further verifies that the ONLY cancellation transition (`QUEUED → CANCELLED`) is
performed by `CancelSetupRetriesForRound` (the single sanctioned exception in AD4/AD9 — a closure terminaliser, NOT an
event handler), that NO event handler writes `queue_status` anywhere in the pseudocode, that `SetupRetryEvent` contains
no `queue_status` write at all (the Stage-1AC `event_queue_status <- CONSUMED` handler writes are gone), and that the
record CREATE in `ScheduleEvent` merely INITIALISES `queue_status = QUEUED` as a field of a new record (not a mutation of
an existing entry). No specification document is modified by this audit; every quoted line is a current line of the
frozen source of truth. The algorithm remains **PoCol** and the mechanism remains the idle policy within PoCol. The A1
baseline `8.420833333 kWh` is preserved.

- **Correction:** AD4 (`ProcessEventTime` is the sole queue-status owner).
- **Source of truth (read-only):** `STAGE_01_PROTOCOL_PSEUDOCODE.md`.
- **Primary procedures:** `ProcessEventTime` (§ dispatch loop), `CancelSetupRetriesForRound`, `SetupRetryEvent`,
  `ScheduleEvent`, `HandleDispatchIntegrityFailure`.
- **Cross-references:** `STAGE_01_ROUND_STATE_MACHINE.md` §3.10h **AD4**; `STAGE_01_TERMINOLOGY.md` Stage-1AD addendum
  (`EventQueueStatus` transition table); `STAGE_01AD_SEMANTIC_TEST_VECTORS.md` **TV255**.
- **Enum + ownership rule.** `EventQueueStatus in { QUEUED, DISPATCHING, CONSUMED, CANCELLED }`; transitions
  `QUEUED → {DISPATCHING, CANCELLED}`, `DISPATCHING → CONSUMED`, with `CONSUMED` / `CANCELLED` terminal
  (`STAGE_01_PROTOCOL_PSEUDOCODE.md:506`–`:510`).

---

## Complete enumeration of every `queue_status <-` write in the pseudocode

A whole-file search for `queue_status <-` (executable mutation) over `STAGE_01_PROTOCOL_PSEUDOCODE.md` returns EXACTLY
four executable writes, plus two comment-only occurrences that are documentation, not mutations. Every executable write
is in `ProcessEventTime` (three) or `CancelSetupRetriesForRound` (one). No write occurs in any event handler.

| Location / line | Transition | Owner | Legitimate? |
|---|---|---|---|
| `:216` `SET queued_event_registry[er].queue_status <- DISPATCHING` | `QUEUED → DISPATCHING` (before dispatch) | `ProcessEventTime` (dispatch loop) | YES — AD4 dispatcher-owned; the sole pre-dispatch owner |
| `:230` `SET queued_event_registry[er].queue_status <- CONSUMED` | `DISPATCHING → CONSUMED` (integrity path) | `ProcessEventTime` (after `HandleDispatchIntegrityFailure`) | YES — AD4/AD8 integrity path; dispatcher drains the corrupt event, never re-`QUEUED` |
| `:239` `SET queued_event_registry[er].queue_status <- CONSUMED` | `DISPATCHING → CONSUMED` (after handler returns) | `ProcessEventTime` (after-final) | YES — AD4 after-final consumption; "no handler wrote it" |
| `:2423` `SET queued_event_registry[snapshot.seat_event_ref].queue_status <- CANCELLED` | `QUEUED → CANCELLED` (closure) | `CancelSetupRetriesForRound` (closure terminaliser) | YES — AD4/AD9 sanctioned exception; the ONE cancellation transition, NOT a handler |
| `:1074`–`:1075` (comment) `queued_event_registry[seat_event_ref].queue_status <- CANCELLED` … `event_queue_status <- CANCELLED` | none (prose) | — (§0.8 AD9 documentation) | N/A — comment describing AD9 and the REMOVED Stage-1AC AC8 mirror; no mutation |

The `SetupRetryEvent` handler (`:2239`–`:2402`) contains **no** `queue_status <-` write of any kind; its only
`queue_status` mentions are reads/prose. There is no third owner of any dispatch-lifecycle transition.

---

## Check 1 — Before dispatch, `ProcessEventTime` asserts `QUEUED`, sets `DISPATCHING`, sets `EQ.current_event_ref`, and builds a trusted `OrdinaryDispatchContext` (PASS)

Inside the drain loop of `ProcessEventTime` (`:191`), for each `QUEUED` ordinary event `er` at the current
`(t, delta_cycle)`, the dispatcher asserts the record is `QUEUED`, then moves it to `DISPATCHING` BEFORE the handler:

> `STAGE_01_PROTOCOL_PSEUDOCODE.md:213`
> ```
> # AD4: ProcessEventTime is the SOLE queue-status owner. ONLY a QUEUED event dispatches; move QUEUED -> DISPATCHING
> #      BEFORE the handler. No handler writes queue_status.
> ASSERT record.queue_status = QUEUED                       # AD4: only a QUEUED event may be dispatched
> SET queued_event_registry[er].queue_status <- DISPATCHING # AD4: QUEUED -> DISPATCHING (dispatcher-owned)
> ```

It then sets the current EventRef and builds the complete dispatcher-owned context from the STORED trusted record
(`:219`, `:222`):

> `STAGE_01_PROTOCOL_PSEUDOCODE.md:219`
> ```
> SET EQ.current_event_ref <- er                            # AC2/AD4: the dispatcher owns the EventRef of e
> ...
> SET ctx <- OrdinaryDispatchContext(dispatch_envelope = record.dispatch_envelope, dispatched_event_ref = er)   # AD5
> ```

The context is built from `record.dispatch_envelope` (the immutable complete envelope of the central
`queued_event_record`, `:220`–`:222`), never from untrusted ambient input — the trusted-context requirement of AD4/AD8.

## Check 2 — After the handler returns, `ProcessEventTime` sets `DISPATCHING → CONSUMED` and clears `EQ.current_event_ref` (after-final) (PASS)

Immediately after the `DISPATCH` of the handler (`:236`), the dispatcher completes the lifecycle — the "after-final"
half — and clears the EventRef:

> `STAGE_01_PROTOCOL_PSEUDOCODE.md:238`
> ```
> # AD4: after the handler returns, the dispatcher completes the lifecycle. DISPATCHING -> CONSUMED, clear the EventRef.
> SET queued_event_registry[er].queue_status <- CONSUMED    # AD4: DISPATCHING -> CONSUMED (no handler wrote it)
> SET EQ.current_event_ref <- null                          # AC2/AD4: cleared after the handler returns
> ```

The comment "no handler wrote it" (`:239`) confirms the after-final `CONSUMED` transition is the dispatcher's, not the
handler's. The integrity path also consumes and clears (`:230`–`:231`), covered in Check 4.

## Check 3 — The ONLY `QUEUED → CANCELLED` transition is `CancelSetupRetriesForRound` (sanctioned AD4/AD9 exception; NOT a handler) (PASS)

`CancelSetupRetriesForRound` (`:2404`) is the round-closure terminaliser invoked by `CloseRoundAssignments` (`:2408`),
NOT an event handler dispatched from the queue. It reads the central authoritative queue state (`:2417`) and, only for a
still-`QUEUED` never-dispatched retry, cancels the pending event and performs the one cancellation transition:

> `STAGE_01_PROTOCOL_PSEUDOCODE.md:2418`
> ```
> IF qstatus = QUEUED:
>   ...
>   IF snapshot.seat_event_ref is still pending on EQ: CANCEL snapshot.seat_event_ref on EQ
>   SET queued_event_registry[snapshot.seat_event_ref].queue_status <- CANCELLED   # AD9: QUEUED -> CANCELLED (central registry only)
>   CALL SetSetupRetryStatus(srid, CANCELLED)                                      # AA2/AC7: SEATED -> CANCELLED (legal)
> ```

For a `DISPATCHING` (mid-flight) retry it explicitly does NOT rewrite the queue state, deferring the after-final
`DISPATCHING → CONSUMED` to the dispatcher (`:2426`–`:2432`); for a `CONSUMED`/`CANCELLED` retry it performs no queue-
state rewrite (`:2433`–`:2437`). The §3.10h AD4 clause states this is the sole exception:

> `STAGE_01_ROUND_STATE_MACHINE.md:982`
> ```
> **AD4 (`ProcessEventTime` sole queue-status owner).** Before dispatch it asserts `QUEUED`, moves `QUEUED → DISPATCHING`, sets
> `EQ.current_event_ref`, and builds a trusted `OrdinaryDispatchContext`; after the handler returns it moves
> `DISPATCHING → CONSUMED` and clears `EQ.current_event_ref`. The only cancellation transition is `QUEUED → CANCELLED` (performed
> by the closure terminaliser, AD9). No event handler writes a `queue_status`.
> ```

The Stage-1AD terminology addendum states the same ownership split — dispatch-lifecycle writes (`DISPATCHING`,
`CONSUMED`) are `ProcessEventTime`'s alone; the one `QUEUED → CANCELLED` cancellation is
`CancelSetupRetriesForRound`'s (`STAGE_01_TERMINOLOGY.md:1090`–`:1093`).

## Check 4 — The integrity path is dispatcher-owned; it also consumes `DISPATCHING → CONSUMED` (PASS)

The defensive corruption branch is still owned by `ProcessEventTime`: it calls the dispatcher-owned
`HandleDispatchIntegrityFailure` and then consumes the drained event itself (`:228`–`:232`):

> `STAGE_01_PROTOCOL_PSEUDOCODE.md:228`
> ```
> IF record is detected corrupt (immutable_payload incomplete for record.event_type OR dispatch_envelope incomplete):
>   CALL HandleDispatchIntegrityFailure(RoundContext, er, record)   # AD8: dispatcher-owned; uses a complete integrity context
>   SET queued_event_registry[er].queue_status <- CONSUMED  # AD4: DISPATCHING -> CONSUMED (the corrupt event is drained, never re-QUEUED)
>   SET EQ.current_event_ref <- null
> ```

The corruption terminal disposition is recorded through `HandleDispatchIntegrityFailure`; the `CONSUMED` write itself is
performed by `ProcessEventTime`, keeping the integrity path within the sole owner (AD4/AD8).

## Check 5 — `SetupRetryEvent` contains NO `queue_status` write (the Stage-1AC `event_queue_status <- CONSUMED` writes are gone) (PASS)

The `SetupRetryEvent` handler (`:2239`–`:2402`) performs no `queue_status` mutation. Its precondition names its queue
state as an EXTERNAL, dispatcher-driven fact — `queued_event_registry[dispatched_event_ref].queue_status = DISPATCHING
while it runs` (`:2256`) — and step (8) states the handler explicitly does not write it:

> `STAGE_01_PROTOCOL_PSEUDOCODE.md:2354`
> ```
> # ... AD4: the handler
> #   does NOT write the queue status — the queued event is already DISPATCHING (dispatcher-owned) and ProcessEventTime
> #   sets DISPATCHING -> CONSUMED after this handler returns.
> ```

The whole-file `queue_status <-` search returns no line within `:2239`–`:2402`; the guard-abort exits move only the
`SetupRetryStatus` (`SEATED → APPLYING → ABORTED`) via `SetSetupRetryStatus`, never the queue status. The §0.8 AC8/AD1
history confirms the Stage-1AC per-record `event_queue_status` mirror — the field the AC8-era handler wrote `CONSUMED` —
is REMOVED, with the queue state relocated to the central registry (`:1067`–`:1068`, `:1115`–`:1121`); the removed write
survives only as prose in the AD9 supersession comment (`:1074`–`:1075`), not as an executable statement.

## Check 6 — The record CREATE in `ScheduleEvent` INITIALISES `queue_status = QUEUED` (a field init, not a mutation) (PASS)

`ScheduleEvent` (`:523`) constructs the ONE central `queued_event_record` and registers it; `queue_status = QUEUED` is a
field of the constructor call (assignment `=`, not the mutation operator `<-`), i.e. an initialiser of a NEW entry:

> `STAGE_01_PROTOCOL_PSEUDOCODE.md:577`
> ```
> # AD1 (6): CREATE the ONE central queued_event_record and REGISTER it with queue_status = QUEUED — the SINGLE
> #     authoritative queue-status source. ...
> SET record <- queued_event_record(event_ref = event_ref, event_type = event_type, dispatch_envelope = dispatch_envelope,
>                                   immutable_payload = immutable_payload, queue_status = QUEUED)
> SET queued_event_registry[event_ref] <- record                       # AD1: the ONE authoritative registry
> ```

This is the birth of the record at `QUEUED`, not a transition of an existing entry; it is therefore excluded from the
dispatch-lifecycle ownership rule (which governs mutations of an already-registered entry) and does not contradict AD4.

---

## PASS summary

| Check | Claim | Evidence (`STAGE_01_PROTOCOL_PSEUDOCODE.md`) | TV255 | Result |
|---|---|---|---|---|
| 1 | Before dispatch: assert `QUEUED`; `QUEUED → DISPATCHING`; set `EQ.current_event_ref`; build trusted `OrdinaryDispatchContext` | `:213`–`:216` (assert + `DISPATCHING`); `:219` (event ref); `:222` (context from stored record) | ✓ | **PASS** |
| 2 | After the handler returns (after-final): `DISPATCHING → CONSUMED`; clear `EQ.current_event_ref` | `:238`–`:240` | ✓ | **PASS** |
| 3 | The ONLY `QUEUED → CANCELLED` is `CancelSetupRetriesForRound` — a closure terminaliser, NOT a handler (sanctioned AD4/AD9 exception) | `:2417`–`:2424` (write); `:2426`–`:2437` (no rewrite on `DISPATCHING`/terminal); state machine `§3.10h:982`–`:985`; terminology `:1090`–`:1093` | ✓ | **PASS** |
| 4 | Integrity path is dispatcher-owned and also consumes `DISPATCHING → CONSUMED` | `:228`–`:231` | ✓ | **PASS** |
| 5 | `SetupRetryEvent` writes NO `queue_status`; the Stage-1AC `event_queue_status <- CONSUMED` writes are gone | `:2256` (state is external); `:2354`–`:2356` (handler does not write); whole-file `<-` search = 0 in `:2239`–`:2402`; `:1067`/`:1074`–`:1075` (removed AC8 mirror) | ✓ | **PASS** |
| 6 | `ScheduleEvent` CREATE initialises `queue_status = QUEUED` (field init, not a mutation) | `:577`–`:582` | — | **PASS** |
| 7 | Whole-pseudocode enumeration: exactly four executable `queue_status <-` writes — three in `ProcessEventTime`, one in `CancelSetupRetriesForRound`; none in any handler | `:216`, `:230`, `:239`, `:2423` (executable); `:1074`–`:1075` (comment only) | ✓ | **PASS** |

---

## Test-vector linkage — TV255

`STAGE_01AD_SEMANTIC_TEST_VECTORS.md` exercises AD4 with **TV255** ("`ProcessEventTime` owns `QUEUED → DISPATCHING →
CONSUMED`; no handler writes `queue_status`", `STAGE_01AD_SEMANTIC_TEST_VECTORS.md:53`). Its procedures are
`ProcessEventTime` and `SetupRetryEvent`; its expectation is that `ProcessEventTime` asserts `record.queue_status =
QUEUED`, sets `QUEUED → DISPATCHING`, sets `EQ.current_event_ref`, dispatches, and AFTER the handler returns sets
`DISPATCHING → CONSUMED` and clears `EQ.current_event_ref`, while `SetupRetryEvent` performs NO `queue_status` write of
any kind — "The dispatch lifecycle has exactly one owner" (`:59`–`:60`). This matches Checks 1, 2 and 5 line-for-line.

---

## Discipline

This audit is documentation-only: it modifies no specification document and quotes the current lines of the frozen source
of truth. Every claim above is grounded in the current `STAGE_01_PROTOCOL_PSEUDOCODE.md`, `STAGE_01_ROUND_STATE_MACHINE.md`
§3.10h, `STAGE_01_TERMINOLOGY.md`, and `STAGE_01AD_SEMANTIC_TEST_VECTORS.md`; no guard, transition, field, or result name
is assumed that the pseudocode does not define. The algorithm remains **PoCol** and the mechanism remains the idle policy
within PoCol. The A1 baseline `8.420833333 kWh` is preserved.

---

## Result

**PASS** — AD4 is faithfully specified. `ProcessEventTime` is the sole owner of the dispatch-lifecycle queue-status
transitions: before dispatch it asserts `QUEUED`, moves `QUEUED → DISPATCHING`, sets `EQ.current_event_ref`, and builds a
trusted `OrdinaryDispatchContext` from the stored record; after the handler returns (after-final) it moves
`DISPATCHING → CONSUMED` and clears `EQ.current_event_ref`, on both the normal path (`:239`) and the dispatcher-owned
integrity path (`:230`). A whole-pseudocode enumeration finds exactly four executable `queue_status <-` writes — three in
`ProcessEventTime` (`:216` `DISPATCHING`, `:230` and `:239` `CONSUMED`) and one in `CancelSetupRetriesForRound` (`:2423`
`CANCELLED`) — and no others; the two remaining textual occurrences (`:1074`–`:1075`, `:5526`–`:5527`) are AD9/AD1
comments, not mutations. `CancelSetupRetriesForRound` is the single sanctioned exception (the `QUEUED → CANCELLED`
closure transition, AD4/AD9) and is a closure terminaliser, not an event handler; `SetupRetryEvent` writes no
`queue_status` at all (the Stage-1AC `event_queue_status <- CONSUMED` handler writes are gone with the removed AC8
mirror); and `ScheduleEvent` merely initialises `queue_status = QUEUED` as a field of a newly created record. No event
handler writes `queue_status`, and there is no second dispatch-lifecycle owner. No FAIL found — all checks PASS. The
pseudocode, round state machine §3.10h AD4, the terminology `EventQueueStatus` transition table, and TV255 are mutually
consistent.
