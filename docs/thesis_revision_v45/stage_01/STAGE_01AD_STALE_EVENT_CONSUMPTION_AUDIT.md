# Stage 1AD — Stale-Event Consumption Audit (AD7)

This audit verifies correction **AD7 — a stale or terminal dispatch still follows `QUEUED -> DISPATCHING -> CONSUMED`
(the queue entry is always consumed)**: `ProcessEventTime`'s dispatch loop moves a `QUEUED` event to `DISPATCHING`
BEFORE the handler runs and moves it `DISPATCHING -> CONSUMED` AFTER the handler returns, UNCONDITIONALLY of the handler's
exit disposition — so even when `SetupRetryEvent` takes a stale / duplicate / terminal no-op exit
(`setup_retry_stale_noop` / `setup_retry_terminal_stale_noop` / `setup_retry_duplicate_suppressed` /
`template_refresh_retry_stale_noop`), the dispatcher still consumes the central queue entry and a stale dispatch can
NEVER leave the registry at `QUEUED`. The audit was generated AFTER the normative documents
(`STAGE_01_PROTOCOL_PSEUDOCODE.md`, `STAGE_01_ROUND_STATE_MACHINE.md`) and the Stage-1AD semantic test vectors
(`STAGE_01AD_SEMANTIC_TEST_VECTORS.md`, TV252–TV261) were final; it reads them read-only and modifies nothing. The A1
baseline `8.420833333 kWh` is unchanged, and the binding PoCol naming rule is preserved: the algorithm is **PoCol** and the
mechanism under audit is the idle policy within PoCol.

Scope is documentation-only. Line anchors are approximate (`~L`). Quotes are reproduced verbatim from the current normative
documents; each check is corroborated by **TV258** (`STAGE_01AD_SEMANTIC_TEST_VECTORS.md`, ~L84–L92), the vector that
exercises AD7, with the AD9 closure post-condition cross-referenced from `CancelSetupRetriesForRound` (~L2438–2446).

The queue lifecycle is dispatcher-owned (AD4): `ProcessEventTime` is the SOLE writer of `queue_status`, seating publishes
the central entry as `QUEUED` (`ScheduleEvent`, ~L577–582), and `EventQueueStatus` transitions are
`QUEUED -> {DISPATCHING, CANCELLED}`, `DISPATCHING -> CONSUMED`, with `CONSUMED` / `CANCELLED` terminal (§3.10h AD1,
~L967–970). This audit confirms that every stale / terminal / duplicate handler exit rides that dispatcher-owned lifecycle
to `CONSUMED` and writes no `queue_status` of its own.

---

## Every SetupRetryEvent stale / terminal / duplicate exit is consumed by the dispatcher regardless

Control returns from each exit below to `ProcessEventTime`, which has ALREADY moved the dispatched entry `er` from
`QUEUED` to `DISPATCHING` before the handler ran (~L215–216) and UNCONDITIONALLY completes `DISPATCHING -> CONSUMED` after
the handler returns (~L238–239). No exit writes `queue_status` and no exit re-queues; each writes at most the *record*
`status` (via `SetSetupRetryStatus`, the sole record-status writer) and `target_disposition`.

| SetupRetryEvent exit (disposition) | Trigger (step / ~L) | Record-status write | Writes queue_status / re-queues? | Dispatcher consumes the queue entry |
|---|---|---|---|---|
| `setup_retry_stale_noop` (structurally-invalid id, AC5-A) | step 1, ~L2267–2268 | none (no record) | No / No | `QUEUED -> DISPATCHING` (~L216) then `DISPATCHING -> CONSUMED` (~L239) |
| `setup_retry_stale_noop` (unknown / never-seated id, AC5-A) | step 2, ~L2270–2271 | none (no record) | No / No | `QUEUED -> DISPATCHING -> CONSUMED` (~L216, ~L239) |
| `setup_retry_stale_noop` (foreign `dispatched_event_ref`, AC5-B) | step 3, ~L2276–2277 | none (record left SEATED) | No / No | dispatched entry `er` `-> DISPATCHING -> CONSUMED`; the genuine `seat_event_ref` (a DIFFERENT entry) legitimately stays `QUEUED` for its own dispatch |
| `setup_retry_duplicate_suppressed` (non-SEATED replay, AC3) | step 4, ~L2281–2282 | none (record already terminal) | No / No | `QUEUED -> DISPATCHING -> CONSUMED` (~L216, ~L239) |
| `setup_retry_stale_noop` (`rec.RoundID != RoundID_current`, AC4) | step 5, ~L2287–2290 | `SEATED -> SUPERSEDED` | No / No | `QUEUED -> DISPATCHING -> CONSUMED` (~L216, ~L239) |
| `setup_retry_terminal_stale_noop` (record's round terminal, AC4) | step 5, ~L2291–2294 | `SEATED -> CANCELLED` | No / No | `QUEUED -> DISPATCHING -> CONSUMED` (~L216, ~L239) |
| `setup_retry_stale_noop` (participant seat-template no longer committed, AC4) | step 5, ~L2295–2299 | `SEATED -> SUPERSEDED` | No / No | `QUEUED -> DISPATCHING -> CONSUMED` (~L216, ~L239) |
| `setup_retry_stale_noop` (template-refresh seat identity no longer current, AC4) | step 5, ~L2300–2306 | `SEATED -> SUPERSEDED` | No / No | `QUEUED -> DISPATCHING -> CONSUMED` (~L216, ~L239) |
| `template_refresh_retry_stale_noop` (target returned a declared stale disposition; step 8) | ~L2380–2381 | `SEATED -> APPLYING -> CANCELLED` | No / No (queue already `DISPATCHING`, dispatcher-owned) | `QUEUED -> DISPATCHING -> CONSUMED` (~L216, ~L239) |

Every stale / terminal / duplicate exit returns control to the dispatcher, which consumes the dispatched entry. None of
the four named no-op dispositions re-queues, and none writes `queue_status` — the dispatcher owns it (AD4). The
`template_refresh_retry_stale_noop` case reaches step 8 (`SEATED -> APPLYING`), receives the stale disposition from
`ContinueTemplateRefreshAssignmentSetup`, and finishes `APPLYING -> CANCELLED` (~L2380–2381); its queue state is
`DISPATCHING` throughout (dispatcher-owned) and the handler note is explicit that "the handler does NOT write the queue
status … ProcessEventTime sets `DISPATCHING -> CONSUMED` after this handler returns" (~L2353–2356). The foreign-ref row is
the one subtlety: the *dispatched* entry `er` is consumed, while the genuine `rec.seat_event_ref` — a distinct registry
entry — correctly remains `QUEUED` for its own future dispatch (AC5-B); a stale dispatch never strands the entry it was
dispatched from.

---

## Checks

| Check | Result |
|-------|--------|
| **C1.** `ProcessEventTime` moves `QUEUED -> DISPATCHING` BEFORE the handler, for every dispatched `QUEUED` event, unconditionally of what the handler will do. | **PASS** — `PROCEDURE ProcessEventTime` (~L213–216): `ProcessEventTime is the SOLE queue-status owner. ONLY a QUEUED event dispatches; move QUEUED -> DISPATCHING BEFORE the handler` … `ASSERT record.queue_status = QUEUED` … `SET queued_event_registry[er].queue_status <- DISPATCHING`. Matches TV258 Expected (~L89–90) and TV255 (~L57–59). |
| **C2.** `ProcessEventTime` moves `DISPATCHING -> CONSUMED` AFTER the handler returns, UNCONDITIONALLY of the handler's exit disposition. | **PASS** — `ProcessEventTime` (~L238–239): `after the handler returns, the dispatcher completes the lifecycle. DISPATCHING -> CONSUMED, clear the EventRef` … `SET queued_event_registry[er].queue_status <- CONSUMED    # AD4: DISPATCHING -> CONSUMED (no handler wrote it)`. The `SET … CONSUMED` is a straight-line statement after `DISPATCH` (~L236), with no branch on the handler's return value. TV258 (~L89–91): "even though the handler takes a no-op exit, `ProcessEventTime` still drives `QUEUED -> DISPATCHING -> CONSUMED`". |
| **C3.** No `SetupRetryEvent` stale / terminal / duplicate no-op exit writes `queue_status` or re-queues the event (the dispatcher owns `queue_status`, AD4). | **PASS** — the step 1–5 exits (`RETURN` at ~L2268, ~L2271, ~L2277, ~L2282, ~L2290, ~L2294, ~L2299, ~L2306) write only the record `status` via `SetSetupRetryStatus` and `target_disposition`; none touches `queue_status`. The step-8 note is explicit (~L2353–2356): `the handler does NOT write the queue status — the queued event is already DISPATCHING (dispatcher-owned) and ProcessEventTime sets DISPATCHING -> CONSUMED after this handler returns`. Handler NOTE (~L2398): `the queue state lives SOLELY in the central queued_event_registry`. TV255 (~L59): `SetupRetryEvent performs NO queue_status write of any kind`. |
| **C4.** Each stale / terminal exit terminalises only the *record* (or leaves it as-is) and never leaves the dispatched event `QUEUED`; the entry is already `DISPATCHING` when any exit is taken. | **PASS** — because C1 moved `er` to `DISPATCHING` (~L216) before the handler body executed, every subsequent `RETURN` (~L2268…~L2381) hands back an entry that is `DISPATCHING`, never `QUEUED`; C2 then sets it `CONSUMED`. The AC4 exits write the record `SEATED -> SUPERSEDED` (~L2288, ~L2297, ~L2304) or `SEATED -> CANCELLED` (~L2292); the AC3/AC5 exits write nothing to the record. In no path is a dispatched entry returned at `QUEUED`. |
| **C5.** Therefore a stale dispatch can NEVER leave the registry at `QUEUED`. | **PASS** — `STAGE_01_ROUND_STATE_MACHINE.md` §3.10h AD7 (~L998–1000): `A stale or terminal dispatch STILL follows QUEUED -> DISPATCHING -> CONSUMED (the dispatcher consumes it), so a stale dispatch can never leave the registry at QUEUED`. Enforced by C1+C2 in `ProcessEventTime`. TV258 (~L90–91): `the registry entry ends CONSUMED, never left at QUEUED`. |
| **C6.** A later `CloseRoundAssignments` / `CancelSetupRetriesForRound` (AD9) never finds a terminal retry record whose central event is falsely `QUEUED`. | **PASS** — a stale-dispatched record is terminalised (SUPERSEDED / CANCELLED) with its central event `CONSUMED` (C2/C5), so at closure `CancelSetupRetriesForRound` reads `qstatus` from `queued_event_registry[seat_event_ref]` (~L2417) as a terminal `CONSUMED` / `CANCELLED` and takes the `SKIP` branch — `no queue-state rewrite; record already terminal` (~L2433–2437). Post-condition holds verbatim: `no terminal retry owns a live QUEUED event` (~L2443–2444) and `no closing-round event remains QUEUED` (~L2441–2442). §3.10h AD7 (~L1000): `a later CloseRoundAssignments never finds a terminal retry record whose central event is falsely QUEUED`. TV258 (~L91–92). |
| **C7.** Even the defensive corrupt-record path consumes the entry (never re-`QUEUED`), reinforcing AD7 through the AD8 dispatcher-integrity route. | **PASS** — `ProcessEventTime` (~L228–232): on a detected-corrupt record it calls `HandleDispatchIntegrityFailure`, then `SET queued_event_registry[er].queue_status <- CONSUMED  # AD4: DISPATCHING -> CONSUMED (the corrupt event is drained, never re-QUEUED)` and `CONTINUE`. `HandleDispatchIntegrityFailure` NOTE (~L343–344): `ProcessEventTime marks the corrupt event CONSUMED (never re-QUEUED) after this returns`. (AD8-scoped; cited only as it corroborates the AD7 consume-regardless property.) |
| **C8.** AD7 is stated identically in the round-state machine and exercised by TV258 (cross-document corroboration). | **PASS** — §3.10h AD7 (~L998–1000) restates the `QUEUED -> DISPATCHING -> CONSUMED` consume-regardless rule and the "never falsely `QUEUED` at closure" corollary; AD4 (~L982–985) fixes `ProcessEventTime` as the sole `queue_status` owner and `DISPATCHING -> CONSUMED` after the handler; `STAGE_01AD_SEMANTIC_TEST_VECTORS.md` TV258 (~L84–92) drives a terminal (`SUPERSEDED`) record's stale replay through `ProcessEventTime` / `SetupRetryEvent` / `CloseRoundAssignments` / `CancelSetupRetriesForRound` and asserts the entry ends `CONSUMED`. No divergence across sources. |

---

## Result

**PASS — AD7 fully realised, no FAIL.** `ProcessEventTime`'s dispatch loop asserts `QUEUED` and moves the dispatched entry
`QUEUED -> DISPATCHING` BEFORE the handler runs (~L215–216), then moves it `DISPATCHING -> CONSUMED` as a straight-line
statement AFTER the handler returns (~L238–239), unconditionally of the handler's exit disposition. Consequently every
`SetupRetryEvent` no-op exit — `setup_retry_stale_noop` (AC5-A unknown/invalid id, AC5-B foreign ref, and the AC4
non-current-round / terminal-template SUPERSEDED cases at ~L2268/2271/2277/2290/2299/2306),
`setup_retry_terminal_stale_noop` (AC4 terminal round, ~L2294), `setup_retry_duplicate_suppressed` (AC3 non-SEATED replay,
~L2282), and `template_refresh_retry_stale_noop` (the step-8 stale disposition, ~L2380–2381) — hands control back to a
dispatcher that consumes the queue entry regardless; none of them writes `queue_status` or re-queues, and each writes at
most the record `status` through `SetSetupRetryStatus`. A stale dispatch therefore can never leave the registry at `QUEUED`
(§3.10h AD7, ~L998–1000), and the AD9 closure post-conditions `no closing-round event remains QUEUED` and `no terminal
retry owns a live QUEUED event` (~L2441–2444) hold when `CloseRoundAssignments -> CancelSetupRetriesForRound` runs later.
The defensive corrupt-record path likewise consumes without re-`QUEUED` (AD8, ~L228–232). Consistent across the pseudocode
`ProcessEventTime` / `SetupRetryEvent` / `CancelSetupRetriesForRound`, the round-state machine §3.10h (AD4/AD7/AD9), and
TV258. Documentation-only; PoCol and the idle policy within PoCol are unchanged; the A1 baseline `8.420833333 kWh` is
preserved.
