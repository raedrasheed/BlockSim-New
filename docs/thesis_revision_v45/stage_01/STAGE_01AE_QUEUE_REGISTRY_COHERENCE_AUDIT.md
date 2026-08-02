# Stage 1AE — Queue/Registry Coherence Audit (AE10 / I21)

This audit verifies correction **AE10** of Stage 1AE — the **queue/registry coherence invariants**, catalogued as the new
invariant **I21** — as a documentation-only, after-final structural check against the frozen Stage-1AE spec. The algorithm is
**PoCol** and the mechanism under audit is the idle policy within PoCol; nothing here alters behaviour, and the A1 energy
baseline **8.420833333 kWh** is preserved (I21 is a structural coherence invariant and, by its own Scope clause, "does not
change the A1 baseline"). The audit asserts ONLY what is written in the spec; every claim carries a grounding quote and an
approximate line anchor, and any coherence gap is reported as a FAIL with its location.

The coherence property binds two structures declared in `STAGE_01_PROTOCOL_PSEUDOCODE.md`: `EQ.event_queue` (the pending
priority queue of `EventRef`s) and `queued_event_registry` (AD1 — the map `EventRef -> queued_event_record`, described as
"The ONE authoritative queue-status source", ~L527). The registry's `queue_status` ranges over
`{ QUEUED, DISPATCHING, CONSUMED, CANCELLED }` with the transition table `QUEUED -> DISPATCHING | CANCELLED`,
`DISPATCHING -> CONSUMED`, and `CONSUMED`/`CANCELLED` terminal (~L529–532). Ownership is partitioned: "ProcessEventTime is
the SOLE writer of the DISPATCH lifecycle (QUEUED -> DISPATCHING -> CONSUMED); CancelQueuedEvent is the SOLE writer of the
CANCELLATION edge (QUEUED -> CANCELLED) and the SOLE operation that removes an EventRef from EQ" (~L533–535).

I21 is correctly **declared** in the invariant catalogue (`STAGE_01_INVARIANT_CATALOGUE.md`, ~L642–663) and referenced as
**I21** — not the older Stage-1Z **I20** (a different invariant: "A setup/recovery rollback restores the exact
pre-constructor coverage/custody ledgers", catalogue ~L622) — consistently across the corpus: the pseudocode AE10 note
("see STAGE_01_INVARIANT_CATALOGUE I16 Stage-1AE clause / new I21", ~L539); the I16 Stage-1AE clause itself
("**AE10:** the queue/registry coherence invariants hold (I21)", ~L457); the round state machine §3.10i AE10 ("...atomically
(I21)", ~L1084); and terminology ("Queue/registry coherence invariants (I21, AE10)", ~L1138). The only I20 reference in the
round SM (~L783) is the rollback-ledger invariant, used correctly and unrelated to coherence.

## Sources audited (with approximate anchors)

| Document | Section / construct | ~L anchor |
|---|---|---|
| `STAGE_01_PROTOCOL_PSEUDOCODE.md` | `queued_event_record` / `queued_event_registry` decl + AE10 coherence note (a)–(f) | ~L517–546 |
| `STAGE_01_PROTOCOL_PSEUDOCODE.md` | `PROCEDURE ScheduleEvent` — AE8 atomic registration | ~L556–640 |
| `STAGE_01_PROTOCOL_PSEUDOCODE.md` | `PROCEDURE CancelQueuedEvent` — AE1 atomic remove | ~L642–676 |
| `STAGE_01_PROTOCOL_PSEUDOCODE.md` | `PROCEDURE ProcessEventTime` — dispatch + drain assertion | ~L191–308 |
| `STAGE_01_INVARIANT_CATALOGUE.md` | new I21 statement; I16 Stage-1AE clause (AE10→I21) | ~L642–663; ~L443–458 |
| `STAGE_01_ROUND_STATE_MACHINE.md` | §3.10i AE10 addendum | ~L1025, ~L1081–1084 |
| `STAGE_01AE_SEMANTIC_TEST_VECTORS.md` | TV271 (AE10/I21), TV272 (AE1) | ~L96–110 |

## The six coherence invariants (a)–(f)

Each row states the invariant, its written enforcement point, the grounding quote, its anchor, and a verdict. "Stated"
means the invariant is written verbatim in the AE10 pseudocode note (~L540–546) and re-stated in I21 (~L645–652).

| # | Invariant (as written) | Enforcement point | Grounding quote (~L anchor) | Verdict |
|---|---|---|---|---|
| (a) | An `EventRef` is present in `EQ.event_queue` IFF its registry `queue_status = QUEUED`. | `ScheduleEvent` atomic add (QUEUED+insert) and `CancelQueuedEvent` atomic remove (CANCELLED+remove) keep physical EQ membership and QUEUED status in lockstep at the QUEUED boundary; `ProcessEventTime` is the sole status owner off that boundary. | "an EventRef is present in EQ.event_queue IFF its registry queue_status = QUEUED" (~L540; I21(a) ~L645) | PASS |
| (b) | The currently-executing `EventRef` (`EQ.current_event_ref`) is ABSENT from pending EQ and has `queue_status = DISPATCHING`. | `ProcessEventTime` moves `QUEUED -> DISPATCHING` and sets `EQ.current_event_ref <- er` before dispatch; selection only ever peeks the smallest QUEUED EventRef, so a DISPATCHING event is off the pending (QUEUED) frontier. | "the currently-executing EventRef (EQ.current_event_ref) is ABSENT from pending EQ and has queue_status = DISPATCHING" (~L541; I21(b) ~L646); "SET queued_event_registry[er].queue_status <- DISPATCHING" (~L225); "SET EQ.current_event_ref <- er" (~L228) | PASS |
| (c) | A `CONSUMED` or `CANCELLED` `EventRef` is NOT pending in EQ. | `CancelQueuedEvent` removes on `QUEUED -> CANCELLED` (~L658–659); `ProcessEventTime` sets `DISPATCHING -> CONSUMED` (~L249); both statuses are terminal (~L532) and every selection/loop filters on QUEUED (~L208,216). | "a CONSUMED or CANCELLED EventRef is NOT pending in EQ" (~L542; I21(c) ~L647) | PASS |
| (d) | Every QUEUED registry entry appears EXACTLY ONCE in EQ; no `EventRef` dispatched more than once. | `ScheduleEvent` inserts each derived (globally-unique-`seq`) `EventRef` once (~L614–627); `ProcessEventTime` re-selects the smallest current QUEUED EventRef each iteration, guards on `queue_status != QUEUED`, dispatches exactly one, then `-> CONSUMED` — so a consumed/cancelled ref is never re-selected. | "every QUEUED registry entry is present EXACTLY ONCE in EQ; no EventRef is dispatched more than once" (~L543; I21(d) ~L648); "RE-SELECT and RE-READ the smallest current QUEUED EventRef each iteration, dispatch EXACTLY ONE" (~L210–213); guard "record.queue_status != QUEUED ... CONTINUE" (~L221–222) | PASS |
| (e) | After `ProcessEventTime(t)` returns, NO event at `t` is `QUEUED` or `DISPATCHING`. | The drain-to-quiescence loop plus the finalisation assertion, which covers BOTH statuses. | "ASSERT no ordinary event with event_time = t has queue_status QUEUED OR DISPATCHING   # R1/AD4/AE10(e)" (~L298); "after ProcessEventTime(t) returns, NO event at t is QUEUED or DISPATCHING" (~L544; I21(e) ~L649) | PASS |
| (f) | Every enqueue (`ScheduleEvent`, AE8) and every cancellation (`CancelQueuedEvent`, AE1) changes EQ membership AND registry status ATOMICALLY (both-or-neither). | `ScheduleEvent` commits the registry entry + EQ insert inside one `ATOMICALLY` block; `CancelQueuedEvent` commits the EQ remove + `QUEUED -> CANCELLED` inside one `ATOMICALLY` block. | "ATOMICALLY: ... SET queued_event_registry[event_ref] <- record  INSERT event_ref INTO EQ.event_queue" (~L610,625–627); "ATOMICALLY: REMOVE EventRef FROM EQ.event_queue  SET queued_event_registry[EventRef].queue_status <- CANCELLED" (~L657–659); I21(f) "changes EQ membership and queue_status ATOMICALLY (both-or-neither)" (~L650–652) | PASS |

### Enforcement trace (three procedures)

- **`ScheduleEvent` (atomic add, AE8).** After time-bound and payload-schema validation (the structured
  `rejected_payload_schema_mismatch` returns "BEFORE any state mutation", ~L594–605), the seat is "ONE atomic transaction —
  mint seq + EventRef, create the QUEUED queued_event_record, add the registry entry, AND insert the EventRef into EQ,
  committing BOTH-OR-NEITHER" (~L606–609). The single `ATOMICALLY` block (~L610) performs `SET queued_event_registry[...] <-
  record` then `INSERT event_ref INTO EQ.event_queue` (~L625–627): no registry entry is ever QUEUED without a pending EQ
  entry, and no EQ entry ever lacks a record. Grounds (a) and (f)-enqueue.
- **`CancelQueuedEvent` (atomic remove, AE1).** Declared "the SOLE queue-owner cancellation operation" and "the ONLY
  operation that removes an EventRef from EQ" (~L642,645). For `status = QUEUED` a single `ATOMICALLY` block does
  `REMOVE EventRef FROM EQ.event_queue` + `SET ... queue_status <- CANCELLED` (~L657–659), so "no event ever leaves EQ while
  still QUEUED" (~L655–656). A `DISPATCHING` event returns `event_already_dispatching(EventRef)` "with no mutation"
  (~L662–665); `CONSUMED`/`CANCELLED` is a terminal no-op (~L666–667); unknown is a declared no-op (~L651–652). Grounds
  (c), (f)-cancel, and TV272.
- **`ProcessEventTime` (sole dispatch owner: QUEUED -> DISPATCHING -> CONSUMED).** The dispatcher re-selects and re-reads the
  smallest QUEUED EventRef each iteration (~L214–217), skips any that is no longer QUEUED or not pending (~L221–222), sets
  `QUEUED -> DISPATCHING` with `EQ.current_event_ref` (~L225–228), dispatches exactly one handler, then completes
  `DISPATCHING -> CONSUMED` and clears `EQ.current_event_ref` (~L249–250). "No handler writes queue_status" (~L224). The
  finalisation assertion covers BOTH QUEUED and DISPATCHING (~L298). Grounds (b), (d), (e).

## Checks tied to the semantic test vectors

| Check | Invariants exercised | Vector / procedures | Spec grounding (~L) | Verdict |
|---|---|---|---|---|
| Mixed seat/dispatch/cancel across one `(t, delta_cycle)` leaves queue and registry coherent. | (a)(b)(c)(d)(e) | TV271 (AE10/I21): `ScheduleEvent`, `ProcessEventTime`, `CancelQueuedEvent` (~L96–102) | I21(a)–(e) ~L645–649; drain assert ~L298 | PASS |
| Every QUEUED registry entry ↔ exactly one pending EQ entry; DISPATCHING ↔ only the executing ref (absent from EQ). | (a)(b)(d) | TV271 expected clause (~L100–102) | AE10 note ~L540–543; `-> DISPATCHING`+`current_event_ref` ~L225,228 | PASS |
| Every CONSUMED/CANCELLED entry absent from EQ; after `ProcessEventTime(t)` nothing at `t` is QUEUED or DISPATCHING. | (c)(e) | TV271 expected clause (~L102) | drain assert covers QUEUED OR DISPATCHING ~L298; terminal removal ~L658–659,249 | PASS |
| Cancel of a DISPATCHING event is a no-op; dispatcher alone completes `DISPATCHING -> CONSUMED`. | (b)(f) | TV272 (AE1): `CancelQueuedEvent`, `ProcessEventTime` (~L104–110) | `event_already_dispatching` no mutation ~L662–665; `-> CONSUMED` ~L249 | PASS |
| Enqueue is atomic (no seq consumed / no partial seat on a rejected payload). | (f)-enqueue | TV269 (AE7/AE8) corroborates the AE8 `ATOMICALLY` seat | ~L606–627 | PASS |

## Result

All six coherence invariants (a)–(f) are explicitly **stated** (AE10 pseudocode note ~L540–546; I21 ~L645–652) and
structurally **enforced** by the three named procedures, with I21 declared in the catalogue and referenced as **I21**
(never the unrelated Stage-1Z **I20**) across pseudocode, round state machine §3.10i, and terminology. The two failure modes
the audit specifically probed are both ABSENT: the drain-quiescence finalisation assertion covers **both** `QUEUED` **and**
`DISPATCHING` (`ASSERT no ordinary event with event_time = t has queue_status QUEUED OR DISPATCHING`, ~L298), and both
mutating operations are wrapped in single `ATOMICALLY` blocks — `ScheduleEvent` (registry entry + EQ insert, ~L610,625–627)
and `CancelQueuedEvent` (EQ remove + `QUEUED -> CANCELLED`, ~L657–659) — so EQ membership and registry status never diverge.
The vectors TV271 (AE10/I21) and TV272 (AE1) map onto invariants (a)–(f) with no unwritten guard, transition, or result
name. **Overall: all PASS; no coherence gap found.**

One precision note (not a FAIL): off the QUEUED boundary, `ProcessEventTime` records a dispatched event's departure from the
pending frontier via `queue_status` alone (`QUEUED -> DISPATCHING -> CONSUMED`, ~L225,249) — the only explicit physical
`REMOVE ... FROM EQ.event_queue` in the spec is `CancelQueuedEvent`'s (~L658). Invariants (a)/(b)/(c) therefore hold under
the spec's own authoritative-registry reading, in which the pending priority queue is the `QUEUED` projection of the central
registry ("The ONE authoritative queue-status source", ~L527) and every selection, loop condition, and assertion filters on
`QUEUED` status (~L208,216,221,298); no path re-selects, re-dispatches, or asserts against a non-`QUEUED` entry. This is a
representational observation about the dispatch path, not an operational incoherence.
