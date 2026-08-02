# Stage 1AD — Retry-Abort & Round-Closure Queue Lifecycle Audit (corrections AD6, AD9)

This is a documentation-only audit of corrections **AD6** (a guard-driven retry abort runs against the `DISPATCHING`
central queue state, never a stale `QUEUED`) and **AD9** (`CancelSetupRetriesForRound` branches on the central
`queued_event_registry` queue state and terminalises every closing-round retry) in the after-final, frozen source of
truth `STAGE_01_PROTOCOL_PSEUDOCODE.md` (read-only). The algorithm is **PoCol**; the mechanism exercised here is the idle
policy within PoCol. This audit verifies the retry-abort and round-closure queue lifecycle: the retry record moving
`SEATED → APPLYING → ABORTED` in lock-step with the central queue moving `QUEUED → DISPATCHING → CONSUMED`, the
synchronous closure sweep seeing `DISPATCHING` (not a stale `QUEUED`), and the removal of the Stage-1AC per-record
`event_queue_status` mirror. It reads the pseudocode and the companion Stage-1AD deliverables and edits none of them. The
A1 baseline (`8.420833333 kWh`) is preserved — nothing in AD6/AD9 touches the energy model, only the queued-event
lifecycle. Every claim is grounded with `file:line` anchors into `STAGE_01_PROTOCOL_PSEUDOCODE.md` (abbreviated **PC**),
`STAGE_01_ROUND_STATE_MACHINE.md` (**RSM**), and `STAGE_01_INVARIANT_CATALOGUE.md` (**IC**), quoting the operative
current lines, and cross-linked to blocking paper test vectors **TV257**, **TV260**, and **TV261**.

---

## 0. What AD6/AD9 declare (the two authoritative addenda)

**RSM:992–996** (§3.10h AD6 — guard-driven abort against the `DISPATCHING` queue state):
> `**AD6 (guard-driven abort against the DISPATCHING queue state).** A guard-driven retry abort runs`
> `SEATED → APPLYING → ABORTED while the queue moves QUEUED → DISPATCHING → CONSUMED. Because ProcessEventTime sets`
> `DISPATCHING before dispatch (AD4), CancelSetupRetriesForRound — reached synchronously during that abort — sees the retry`
> `APPLYING and the queue DISPATCHING (never a stale QUEUED), so it only persists terminal_closure_pending; the`
> `RoundAbort path never trips a QUEUED assertion, and after the handler returns no event remains DISPATCHING.`

**RSM:1009–1014** (§3.10h AD9 — `CancelSetupRetriesForRound` inspects the central registry):
> `**AD9 (CancelSetupRetriesForRound inspects the central registry).** For each closing-round retry it reads`
> `queued_event_registry[seat_event_ref].queue_status: QUEUED → cancel the event, QUEUED → CANCELLED, and SEATED → CANCELLED`
> `(record); DISPATCHING → do not cancel, persist terminal_closure_pending, let the handler finish, dispatcher later sets`
> `DISPATCHING → CONSUMED; CONSUMED/CANCELLED → no queue rewrite.`

The invariant catalogue restates both under I16 — **IC:430–431** (AD6) and **IC:435–439** (AD9). The underlying
enabler is **AD4** (RSM:982–985): `ProcessEventTime` is the sole queue-status owner, moving `QUEUED → DISPATCHING`
**before** dispatch and `DISPATCHING → CONSUMED` **after** the handler returns; the only cancellation is
`QUEUED → CANCELLED`, performed by the closure terminaliser. **AD1** (RSM:965–970; PC:494–513) removes the AC8
per-record `event_queue_status` mirror: a `setup_retry_record` keeps only its immutable `seat_event_ref`, and its queue
state IS `queued_event_registry[seat_event_ref].queue_status`.

---

## 1. The abort lifecycle traced (record status ↔ queue status ↔ owner)

The table traces the two synchronous transitions of a **current owned SEATED** retry whose guard fires an abort. The
record column is driven by `SetupRetryEvent` through the sole guard `SetSetupRetryStatus` (PC:2463–2484); the queue
column is driven solely by `ProcessEventTime` (PC:213–239); the mid-flight persistence is done by
`CancelSetupRetriesForRound` (PC:2426–2432).

| Step | Record status (setup_retry_record) | Central queue status (queued_event_registry[seat_event_ref]) | Owner (procedure : anchor) |
|------|------------------------------------|---------------------------------------------------------------|----------------------------|
| Seat | — → `SEATED` (create) | — → `QUEUED` (ScheduleEvent registered `record`) | seat CREATE : PC:2093–2096 |
| Dispatch begins | `SEATED` (unchanged) | `QUEUED` → `DISPATCHING` (before handler) | `ProcessEventTime` : PC:215–216 |
| Guard leaves SEATED | `SEATED` → `APPLYING` (before `RoundAbort`) | `DISPATCHING` (unchanged) | `SetupRetryEvent`/`SetSetupRetryStatus` : PC:2316,2327,2336,2345 |
| Synchronous closure sweep | `APPLYING` (read-only snapshot) | `DISPATCHING` read; NOT cancelled, NOT rewritten | `CancelSetupRetriesForRound` : PC:2417,2426–2432 |
| Sweep persists intent | `APPLYING` + `terminal_closure_pending ← true` | `DISPATCHING` (unchanged) | `CancelSetupRetriesForRound` : PC:2432 |
| Guard finalises record | `APPLYING` → `ABORTED` | `DISPATCHING` (unchanged) | `SetupRetryEvent`/`SetSetupRetryStatus` : PC:2322,2333,2342,2351 |
| Handler returns | `ABORTED` (terminal) | `DISPATCHING` → `CONSUMED` (after return) | `ProcessEventTime` : PC:239 |

The record and the queue never disagree on ownership: the handler never writes a `queue_status` and the dispatcher never
writes a `status`. The `terminal_closure_pending` flag is the ONE cross-procedure hand-off — persisted by the sweep
(PC:2432), asserted by the guard (PC:2320,2331,2340,2349), consumed on re-read for the target-driven abort variant
(PC:2367–2373). The reach into closure is real and synchronous: `SetupRetryEvent`'s guard calls `RoundAbort` (PC:2317
etc.) → `RoundAbort` calls `CloseRoundAssignments` (PC:5577–5579) → `CloseRoundAssignments` calls
`CancelSetupRetriesForRound` (PC:5268–5269).

---

## 2. Checks

| # | Check | Result | Evidence (quote + anchor) |
|---|-------|--------|---------------------------|
| 1 | `ProcessEventTime` moves `QUEUED → DISPATCHING` BEFORE dispatch (the AD6 enabler) | **PASS** | `SET queued_event_registry[er].queue_status <- DISPATCHING # AD4: QUEUED -> DISPATCHING (dispatcher-owned)` — PC:216 (dispatch at PC:236–237) |
| 2 | `ProcessEventTime` moves `DISPATCHING → CONSUMED` AFTER the handler returns (none stays `DISPATCHING`) | **PASS** | `SET queued_event_registry[er].queue_status <- CONSUMED # AD4: DISPATCHING -> CONSUMED (no handler wrote it)` — PC:239 |
| 3 | Every aborting guard runs `SEATED → APPLYING` BEFORE `RoundAbort`, then `APPLYING → ABORTED` | **PASS** | `SetSetupRetryStatus(…, APPLYING)` then `RoundAbort` then `SetSetupRetryStatus(…, ABORTED)` — PC:2316–2323 (integrity), 2326–2334 (wrong state), 2335–2343 (budget), 2344–2352 (state-incompat) |
| 4 | The synchronous sweep sees the retry `APPLYING` + queue `DISPATCHING` (never a stale `QUEUED`) | **PASS** (TV257) | `SET qstatus <- queued_event_registry[snapshot.seat_event_ref].queue_status` then `ELSE IF qstatus = DISPATCHING:` — PC:2417,2426 |
| 5 | On `DISPATCHING`, the sweep does NOT cancel and does NOT rewrite the queue state; it persists `terminal_closure_pending` ONLY | **PASS** (TV257,TV260) | `# Do NOT cancel the event and do NOT rewrite the queue state … PERSIST terminal_closure_pending` → `UPDATE setup_retry_records[srid].terminal_closure_pending <- true` — PC:2427–2432 |
| 6 | The `RoundAbort` path trips NO `QUEUED` assertion during a mid-flight abort | **PASS** (TV257) | The DISPATCHING branch is taken (PC:2426); post-condition asserts on `= QUEUED` which the mid-flight record (DISPATCHING) does not satisfy — PC:2442; `ASSERT record.queue_status = QUEUED` (PC:215) is per-dispatch and not re-entered by the synchronous sweep |
| 7 | On `QUEUED`, the sweep cancels the EQ event, sets central `QUEUED → CANCELLED`, and `SEATED → CANCELLED` | **PASS** (TV260) | `IF snapshot.seat_event_ref is still pending on EQ: CANCEL …` / `SET queued_event_registry[…].queue_status <- CANCELLED` / `CALL SetSetupRetryStatus(srid, CANCELLED)` — PC:2422–2424 |
| 8 | On `CONSUMED`/`CANCELLED` (terminal), the sweep performs NO queue-state rewrite | **PASS** (TV260) | `ELSE: … CONSUMED or CANCELLED — a TERMINAL queue state … Perform NO queue-state rewrite … SKIP` — PC:2433–2437 |
| 9 | Post: no closing-round event remains `QUEUED`; no terminal retry owns a live `QUEUED` event | **PASS** (TV261) | `ASSERT no id … has … queue_status = QUEUED` (PC:2442); `ASSERT no id … status IN {APPLIED,SUPERSEDED,CANCELLED,ABORTED} has … queue_status = QUEUED` (PC:2443–2444) |
| 10 | Post: every `SEATED` retry terminalised; every `APPLYING` record carries `terminal_closure_pending` (so none stays `DISPATCHING` after its handler returns) | **PASS** (TV261) | `ASSERT no id … has status = SEATED` (PC:2440); `ASSERT every id … status = APPLYING has terminal_closure_pending = true # … so none remains DISPATCHING afterwards` (PC:2446) |
| 11 | The sweep reads the CENTRAL registry only; no per-record queue mirror is consulted or written | **PASS** (TV260) | `# the queue state is read from the CENTRAL queued_event_registry … The record NO LONGER carries an event_queue_status mirror` — PC:2415–2417,2438–2439 |
| 12 | The removed AC8 per-record `event_queue_status` field is not referenced anywhere as a live read/write | **PASS** | grep `event_queue_status` = 9 hits, ALL comments noting AD1 removal (PC:512,1068,1075,1117,1755,2091,2399,2416,5526); grep for a per-record write `.event_queue_status <-` = 0 live writes (only PC:1075, inside a comment describing the AD1 supersession) |
| 13 | `SetSetupRetryStatus` legalises `SEATED → APPLYING`, `APPLYING → ABORTED`, `SEATED → CANCELLED` and rejects terminal → terminal | **PASS** | `SEATED -> {APPLYING, CANCELLED, SUPERSEDED}` / `APPLYING -> {APPLIED, SUPERSEDED, CANCELLED, ABORTED}` / reject illegal with NO mutation — PC:2469–2478 |
| 14 | A1 baseline `8.420833333 kWh` and PoCol idle policy preserved (AD6/AD9 are queue-lifecycle only) | **PASS** | No energy term appears in `ProcessEventTime` dispatch lifecycle (PC:213–239) or `CancelSetupRetriesForRound` (PC:2404–2461); TV257/TV260/TV261 assert the A1 baseline is preserved (Stage-1AD TV header) |

---

## 2a. The Stage-1AC bug AD6 fixes (present and coherent)

The Stage-1AC design kept an independently-writable per-record `event_queue_status` mirror (AC8). A retry dispatched and
then aborting mid-flight would have its per-record mirror still reading `QUEUED` (the dispatcher had not stamped it),
so the synchronous `CloseRoundAssignments → CancelSetupRetriesForRound` sweep could observe a **stale `QUEUED`** for an
event that was actually being dispatched — tripping a `QUEUED`-branch cancel/assertion against a live handler. The AD
supersession record names this exactly: *"TV249 missed the `QUEUED`-assertion failure during `RoundAbort`"* (RSM:1017;
IC AD10 IC:439). AD fixes it with two coherent moves, both verified present:

1. **AD4 ordering** — `ProcessEventTime` stamps `QUEUED → DISPATCHING` **before** the handler runs (PC:216), so the
   central state already reads `DISPATCHING` by the time the synchronous sweep is reached.
2. **AD9 central read** — `CancelSetupRetriesForRound` reads `queued_event_registry[seat_event_ref].queue_status`
   (PC:2417), sees `DISPATCHING`, and takes the do-nothing-but-persist branch (PC:2426–2432). It never sees `QUEUED`
   for the mid-flight retry, so no `QUEUED` cancel/assertion trips.

The two moves are mutually reinforcing and there is no remaining path by which the sweep can observe `QUEUED` for a
mid-flight retry: the per-record mirror that could have gone stale no longer exists (Check 12), and the single central
source is transitioned by the dispatcher before dispatch (Check 1). The fix is present and coherent — no FAIL.

---

## 3. The AD9 branch table (`CancelSetupRetriesForRound`, PC:2404–2461)

`CancelSetupRetriesForRound` iterates the matching `SetupRetryID`s in stable order (PC:2413), takes a read-only
`snapshot` (PC:2414), reads the ONE authoritative queue state from the central registry (PC:2417), and branches on it.
Every mutation is a keyed persistent UPDATE against the record OR the central registry — there is no local mirror to
fall out of sync (PC:2438–2439).

| Central `queue_status` | Cancel EQ event? | Central queue rewrite | Record transition | Anchor |
|------------------------|------------------|-----------------------|-------------------|--------|
| `QUEUED` (never dispatched; record `SEATED`) | Yes — `CANCEL snapshot.seat_event_ref on EQ` if still pending | `QUEUED → CANCELLED` (central only) | `SEATED → CANCELLED` via `SetSetupRetryStatus`; `seat_event_ref` preserved | PC:2418–2425 |
| `DISPATCHING` (mid-flight; record `APPLYING`) | No | None — dispatcher alone drives `DISPATCHING → CONSUMED` (AD4) | none here; `terminal_closure_pending ← true`, handler finishes `APPLYING → ABORTED/CANCELLED` | PC:2426–2432 |
| `CONSUMED` or `CANCELLED` (terminal) | No | None (both terminal) | none — record already terminal; `SKIP` (no terminal → terminal, AC7) | PC:2433–2437 |

The branch structure is total over the four-value `EventQueueStatus` enum (`QUEUED`, `DISPATCHING`, `CONSUMED`,
`CANCELLED`; RSM:967–968), collapsing the two terminal queue states into one `ELSE`. The `DISPATCHING` branch is the AD6
join point: it is the ONLY branch that neither cancels nor rewrites the queue, deferring completion to the dispatcher's
`DISPATCHING → CONSUMED` (PC:239) and to the mid-flight handler's `APPLYING → ABORTED/CANCELLED` (PC:2322/2372–2373).
The post-conditions (PC:2440–2446) close the loop: no `SEATED` survives (PC:2440), no `QUEUED` survives (PC:2442), no
terminal retry owns a live `QUEUED` event (PC:2443–2444), and every `APPLYING` record carries `terminal_closure_pending`
so none is left `DISPATCHING` once its handler returns (PC:2446). The blanket `CANCEL all pending … SetupRetryEvent
events for RoundID` in `CloseRoundAssignments` (PC:5262–5264) is scoped to *pending* (i.e. `QUEUED`) events and runs
immediately before this terminaliser; it therefore cannot cancel a mid-flight `DISPATCHING` event (only `QUEUED →
CANCELLED` is a legal EventQueueStatus edge, RSM:967–968), which is consistent with the `DISPATCHING` branch leaving the
event untouched — no FAIL.

---

## Result

**AD6 and AD9 PASS.** The retry-abort and round-closure queue lifecycle is realised coherently in the after-final frozen
`STAGE_01_PROTOCOL_PSEUDOCODE.md`. A guard-driven abort runs the record `SEATED → APPLYING → ABORTED` (via the sole
guard `SetSetupRetryStatus`) while `ProcessEventTime` runs the central queue `QUEUED → DISPATCHING → CONSUMED`, stamping
`DISPATCHING` **before** dispatch (PC:216) so the synchronous `CancelSetupRetriesForRound` sweep reached through
`RoundAbort → CloseRoundAssignments` reads `DISPATCHING` (PC:2417,2426), never a stale `QUEUED`; it persists
`terminal_closure_pending` only, no `QUEUED` assertion trips, and after the handler returns no event remains
`DISPATCHING` (PC:239) — this is exactly the Stage-1AC bug (AC8 stale per-record mirror; TV249) that AD fixes, and the
fix is present. `CancelSetupRetriesForRound` branches on the central registry across all four EventQueueStatus values
(QUEUED cancel + `QUEUED → CANCELLED` + `SEATED → CANCELLED`; DISPATCHING persist-only; CONSUMED/CANCELLED no rewrite)
and its post-conditions guarantee no closing-round event stays `QUEUED`, no terminal retry owns a live `QUEUED` event,
every `SEATED` retry is terminalised, and every `APPLYING` record carries `terminal_closure_pending`. The removed AC8
per-record `event_queue_status` mirror is referenced nowhere as a live read or write — the nine remaining textual
occurrences are all comments documenting its removal, and there are zero per-record mirror writes. TV257 (AD6 mid-flight
`DISPATCHING` sweep), TV260 (AD9 central-registry branch table), and TV261 (AD9 post-closure post-conditions) exercise
these paths against the exact procedures. No genuine inconsistency was found: no `QUEUED` assertion can trip during a
mid-flight abort and no residual per-record queue mirror exists. This audit is documentation-only; the algorithm is
PoCol with the idle policy within PoCol; the A1 baseline `8.420833333 kWh` is preserved.
