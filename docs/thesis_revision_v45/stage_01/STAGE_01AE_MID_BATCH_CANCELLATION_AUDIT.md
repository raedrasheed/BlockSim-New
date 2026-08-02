# Stage 1AE — Mid-Batch Cancellation Audit (AE3: `ProcessEventTime` robust to mid-batch cancellation)

This audit verifies correction **AE3** — the event-time dispatch loop of `ProcessEventTime` is robust to MID-BATCH
cancellation — against the frozen source of truth `STAGE_01_PROTOCOL_PSEUDOCODE.md` (read-only). It establishes that the
dispatch loop no longer iterates a STALE snapshot of all `QUEUED` events at one `(t, delta_cycle)`; that it RE-SELECTS
and RE-READS the smallest current `QUEUED` EventRef each iteration; that a re-read of a cancelled/absent event is
SKIPPED (no assert, no dispatch) rather than tripping the old AD4 hard `ASSERT record.queue_status = QUEUED`; that the
dispatcher then moves `QUEUED → DISPATCHING`, dispatches EXACTLY ONE event, completes the **after-final**
`DISPATCHING → CONSUMED` transition, and re-queries; and that the post-drain quiescence assertion (AE10(e)) holds. The
algorithm is **PoCol** and the mechanism under audit is the idle policy within PoCol; both are preserved unchanged. The
A1 baseline **`8.420833333 kWh`** is preserved (AE3 is a structural dispatch-loop correction that changes no energy
accounting). Line anchors (`~L…`) reference `STAGE_01_PROTOCOL_PSEUDOCODE.md` unless another file is named. Blocking
paper test vector **TV264** exercises AE3.

Scope note: only what is WRITTEN in the pseudocode is asserted below. Any residual stale-snapshot iteration or hard
`QUEUED` assertion inside the `ProcessEventTime` dispatch loop would be reported as a FAIL with its location; none was
found.

---

## Checks

| # | Check | Result | Evidence (quote + anchor) | Vector |
|---|-------|--------|---------------------------|--------|
| 1 | The dispatch loop does NOT iterate a stale snapshot of all `QUEUED` events at one `(t, current_delta_cycle)`. | **PASS** | `# AE3: do NOT iterate a STALE snapshot of all QUEUED events at (t, current_delta_cycle) — a handler may CANCEL a LATER` … `same-cycle event mid-batch (via CancelQueuedEvent, AE1), and a snapshot would try to dispatch that now-CANCELLED event and trip the QUEUED assertion. Instead RE-SELECT and RE-READ … each iteration, dispatch EXACTLY ONE, and RE-QUERY the queue.` (~L210–213) | TV264 |
| 2 | It uses a `WHILE` that RE-SELECTS the smallest current `QUEUED` EventRef by `(microphase, stable_tie_key, seq)` each iteration. | **PASS** | `WHILE a QUEUED EventRef exists at (t, current_delta_cycle):` (~L214) and `SET er <- the SMALLEST QUEUED EventRef at (t, current_delta_cycle) by (er.microphase, stable_tie_key, er.seq)  # AE3: re-selected` (~L216) | TV264 |
| 3 | Each iteration RE-READS the one central authoritative record `queued_event_registry[er]`. | **PASS** | `SET record <- queued_event_registry[er]                   # AD1/AE3: RE-READ the ONE central authoritative record` (~L217) | TV264 |
| 4 | Before dispatch: IF the record does not exist OR `queue_status != QUEUED` OR `er` is not pending on EQ → SKIP (`CONTINUE`) with NO assert and NO dispatch. | **PASS** | `IF record does not exist OR record.queue_status != QUEUED OR er is NOT pending on EQ.event_queue:` → `CONTINUE                                                # AE3: reconcile — a cancelled/absent event is never dispatched` (~L221–222) | TV264 |
| 5 | The old AD4 hard `ASSERT record.queue_status = QUEUED` snapshot form is GONE from the dispatch loop. | **PASS** | No `ASSERT record.queue_status = QUEUED` occurs anywhere in `STAGE_01_PROTOCOL_PSEUDOCODE.md` (verified by full-file search); the pre-dispatch guard is now the skip at ~L221–222. The removed form is attested by the AD-era audit `STAGE_01AD_QUEUE_STATUS_OWNERSHIP_AUDIT.md:58` (`ASSERT record.queue_status = QUEUED  # AD4: only a QUEUED event may be dispatched`). | TV264 |
| 6 | It then moves `QUEUED → DISPATCHING` (dispatcher-owned, before the handler). | **PASS** | `SET queued_event_registry[er].queue_status <- DISPATCHING # AD4: QUEUED -> DISPATCHING (dispatcher-owned)` (~L225), under `# AD4/AE3: ProcessEventTime is the SOLE queue-status owner. Dispatch EXACTLY ONE event` (~L223) | TV264 |
| 7 | It dispatches EXACTLY ONE event (schema-declared arguments only, AE5). | **PASS** | `DISPATCH record.event_type WITH immutable_payload = record.immutable_payload, (AND dispatch_envelope … IFF … recv_env = yes), (AND dispatched_event_ref … IFF … recv_ref = yes)   # AE5` (~L245–247); the `WHILE` body dispatches one `er` per iteration. | TV264 |
| 8 | It completes the **after-final** `DISPATCHING → CONSUMED` transition (no handler wrote it). | **PASS** | `SET queued_event_registry[er].queue_status <- CONSUMED    # AD4: DISPATCHING -> CONSUMED (no handler wrote it)` (~L249) and `SET EQ.current_event_ref <- null` (~L250) | TV264 |
| 9 | It then RE-QUERIES the queue (a cancelled later same-cycle event is never dispatched; a forward `+1` cycle event is deferred to the outer LOOP). | **PASS** | `# AE3: the WHILE RE-QUERIES the queue — a handler may have CANCELLED a later same-cycle event (never dispatched) or added a (t, current_delta_cycle+1) event (forward only; handled by the outer LOOP, §0.7-H2).` (~L251–252) | TV264 |
| 10 | A handler that cancels a later same-`(t, delta_cycle)` event via `CancelQueuedEvent` makes that event never dispatched and trips no assertion. | **PASS** | `CancelQueuedEvent` on a `QUEUED` ref does `REMOVE EventRef FROM EQ.event_queue` + `SET queued_event_registry[EventRef].queue_status <- CANCELLED` atomically, `RETURN event_cancelled(EventRef)` (~L654–661); the re-selected/re-read ref then fails the ~L221 guard and is skipped (~L222). | TV264 |
| 11 | Cross-check — the drain-quiescence assertion after the loop asserts no event at `t` is `QUEUED` OR `DISPATCHING` (AE10(e)). | **PASS** | `ASSERT no ordinary event with event_time = t has queue_status QUEUED OR DISPATCHING   # R1/AD4/AE10(e)` (~L298); matches `STAGE_01_INVARIANT_CATALOGUE.md` I21(e) `after ProcessEventTime(t) returns, NO event with event_time = t is QUEUED or DISPATCHING` (~L649). | TV264 |
| 12 | The AE3 statement in the state machine matches the loop: re-select/re-read, skip if not `QUEUED`/absent, else `QUEUED → DISPATCHING`, one dispatch, `DISPATCHING → CONSUMED`, re-query. | **PASS** | `STAGE_01_ROUND_STATE_MACHINE.md` §3.10i: `ProcessEventTime no longer iterates a stale snapshot … re-selects and re-reads the smallest current QUEUED EventRef each iteration; if the re-read shows it is not QUEUED (or absent from EQ), it skips it (no assert, no dispatch); otherwise it moves QUEUED → DISPATCHING, dispatches exactly one event, completes DISPATCHING → CONSUMED, and re-queries.` (~L1044–1048) | TV264 |

---

## OLD stale FOR-EACH snapshot vs NEW `WHILE` re-select / re-read / skip / re-query

**OLD (AD4 snapshot form — now REMOVED).** The Stage-1AD dispatcher took a snapshot of ALL `QUEUED` events at one
`(t, delta_cycle)` and iterated it (a FOR-EACH-style pass over the batch). For each `er` in that frozen batch it executed
a HARD pre-dispatch assertion — `ASSERT record.queue_status = QUEUED  # AD4: only a QUEUED event may be dispatched`
(`STAGE_01AD_QUEUE_STATUS_OWNERSHIP_AUDIT.md:58`; catalogued in `STAGE_01AD_PROCEDURE_SIGNATURE_CALL_AUDIT.md:56`) —
before moving `QUEUED → DISPATCHING`. The defect: if `A`'s handler (dispatched earlier in the same batch) closed the
round and that closure CANCELLED a later same-cycle event `B` via `CancelQueuedEvent` (`B → CANCELLED`, removed from
EQ), the snapshot still held `B` and would reach it. The `record` re-read on the now-`CANCELLED` `B` no longer satisfied
`= QUEUED`, so the hard assertion FIRED — a spurious termination on a perfectly legal mid-batch cancellation. The stale
snapshot could also, in principle, attempt to dispatch an event already drained.

**NEW (AE3 `WHILE` form — current pseudocode).** The dispatcher holds NO batch. Each iteration RE-SELECTS the smallest
current `QUEUED` EventRef by `(er.microphase, stable_tie_key, er.seq)` (~L216) and RE-READS the one authoritative
record `queued_event_registry[er]` (~L217). It then applies a defensive RECONCILE guard instead of a hard assert:
`IF record does not exist OR record.queue_status != QUEUED OR er is NOT pending on EQ.event_queue: CONTINUE`
(~L221–222) — a cancelled/absent event is SKIPPED, never asserted, never dispatched. Only a still-`QUEUED`,
still-pending `er` proceeds: `QUEUED → DISPATCHING` (~L225), EXACTLY ONE `DISPATCH` (~L245–247), then the after-final
`DISPATCHING → CONSUMED` (~L249) and `EQ.current_event_ref <- null` (~L250). The `WHILE` then RE-QUERIES (~L251–252).
Because selection is re-evaluated against live queue state every iteration, a handler that cancels a later same-cycle
event simply removes it from consideration; in the single-threaded model a non-`QUEUED` event is never re-selected at
all, and the ~L221 guard makes that structural even if it were. TV264 is the direct exercise: `A` dispatches, the
round-closing handler cancels `B` via `CancelQueuedEvent`, the loop re-queries, `B` is neither `QUEUED` nor pending, `B`
is never dispatched, and no assertion fails. The residual end-of-time invariant is the AE10(e) quiescence assertion
(~L298), aligned with I21(e).

---

## Result

All twelve checks **PASS**. The `ProcessEventTime` dispatch loop is a `WHILE` that re-selects the smallest current
`QUEUED` EventRef by `(microphase, stable_tie_key, seq)`, re-reads the central `queued_event_registry` record, skips
(`CONTINUE`) any record that is missing, not `QUEUED`, or not pending on EQ — with NO assertion and NO dispatch — and
otherwise performs a single `QUEUED → DISPATCHING`, one schema-declared dispatch, and the after-final
`DISPATCHING → CONSUMED` before re-querying. The old AD4 hard `ASSERT record.queue_status = QUEUED` snapshot form is
absent from the entire pseudocode; no residual stale-snapshot iteration remains in the dispatch loop. A handler that
cancels a later same-`(t, delta_cycle)` event through `CancelQueuedEvent` (AE1: atomic EQ-removal + `QUEUED →
CANCELLED`) guarantees that event is never dispatched and trips no assertion (TV264). The post-drain quiescence
assertion (~L298) enforces AE10(e)/I21(e). AE3 is a structural correction only: PoCol and its idle policy are
preserved, and the A1 baseline `8.420833333 kWh` is unchanged. No FAIL was found.
