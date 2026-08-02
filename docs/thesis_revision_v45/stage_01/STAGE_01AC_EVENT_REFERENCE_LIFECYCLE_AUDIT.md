# Stage 1AC — Event-Reference Lifecycle Audit (correction AC8)

This is a documentation-only audit of correction **AC8** ("keep the immutable event identity separate from queue state")
in the Stage-1 formal specification of **PoCol** and the idle policy within PoCol. It verifies, against the frozen source
of truth `STAGE_01_PROTOCOL_PSEUDOCODE.md` (read-only), that a `setup_retry_record` carries an IMMUTABLE
`seat_event_ref : EventRef` (set once, at the seat) PAIRED with a separate `event_queue_status : EventQueueStatus`, that
`EventQueueStatus` is a declared four-value enum, that both seating procedures publish `seat_event_ref = the EventRef` and
`event_queue_status = QUEUED`, that ownership compares the IMMUTABLE `seat_event_ref`, that consumption marks
`event_queue_status <- CONSUMED` and round-closure cancellation marks `event_queue_status <- CANCELLED` while PRESERVING
`seat_event_ref` (nothing nulls or erases it), and that the AB6-era "clear event_ref to null" is superseded by the queue-
state transition so the closure post-condition is now "no record has `event_queue_status = QUEUED`". No specification
document is modified by this audit; all quoted lines are the current lines of the source of truth. The A1 baseline
(`8.420833333 kWh`) is unchanged.

- **Correction:** AC8 (immutable event identity separate from queue state).
- **Source of truth (read-only):** `STAGE_01_PROTOCOL_PSEUDOCODE.md`.
- **Primary procedures:** `ScheduleEvent`, `PrepareParticipantsForNewRound`, `ContinueTemplateRefreshAssignmentSetup`,
  `SetupRetryEvent`, `CancelSetupRetriesForRound`, `SetSetupRetryStatus`.
- **Requirement:** R213 (with R214 for the test vectors). **Invariant context:** I16 (Stage-1AC clause), I3.
  **Test vector:** TV251.

---

## Check 1 — The record carries `seat_event_ref` (immutable) + `event_queue_status`, `EventQueueStatus` is a declared enum, and both seats publish `seat_event_ref = the EventRef` / `event_queue_status = QUEUED` (PASS)

### 1a. The record type declares an immutable `seat_event_ref : EventRef` and a separate `event_queue_status`

The `setup_retry_records` map is declared in the §0.8 state model initialised at run start. Its record type carries both
the immutable seat reference and the separate queue-lifecycle status field:

> `STAGE_01_PROTOCOL_PSEUDOCODE.md:1613`
> ```
> setup_retry_records         : Z1/AA2/AC1/AC8 — map SetupRetryID -> setup_retry_record { SetupRetryID, setup_kind, RoundID,
>                             : TemplateID_at_seat, TemplateRefreshSetupID, retry_generation, seat_event_ref : EventRef
>                             : (immutable, AC1/AC8), event_queue_status : EventQueueStatus (AC8), status : SetupRetryStatus,
>                             : target_disposition, terminal_closure_pending : bool (AA2) }.
> ```

The same declaration states the seating contract (`STAGE_01_PROTOCOL_PSEUDOCODE.md:1618`): "The seating procedure
publishes `status = SEATED`, `seat_event_ref = the ScheduleEvent EventRef`, `event_queue_status = QUEUED` after a
successful ScheduleEvent". The §0.8 AC8 addendum restates that the pair replaces the earlier single field:

> `STAGE_01_PROTOCOL_PSEUDOCODE.md:1029`
> ```
> # setup_rollback of the retry record: seat_event_ref : EventRef (IMMUTABLE, set at seat) + event_queue_status :
> #   EventQueueStatus { QUEUED, DISPATCHING, CONSUMED, CANCELLED }. Ownership comparisons use the immutable seat_event_ref;
> #   cancellation/consumption changes ONLY event_queue_status and NEVER erases the historical seat EventRef. The Z1-era
> #   single `event_ref` field is REPLACED by this pair.
> ```

### 1b. `EventQueueStatus` is a declared four-value enum, kept SEPARATE from the immutable `EventRef`

The enum is declared alongside the canonical `STRUCTURE EventRef` (§0.7e), explicitly separated from the immutable
identity:

> `STAGE_01_PROTOCOL_PSEUDOCODE.md:446`
> ```
> # AC8 event-queue lifecycle state (kept SEPARATE from the immutable EventRef identity):
> # EventQueueStatus in { QUEUED, DISPATCHING, CONSUMED, CANCELLED }. A retry record stores its IMMUTABLE seat_event_ref
> #   (never destroyed) AND an event_queue_status; cancellation changes the status, it does NOT erase the seat EventRef used
> #   for replay-ownership auditing.
> ```

The `EventRef` type it is separated from is the one canonical immutable reference declared immediately above it
(`STRUCTURE EventRef (AC1 ...)`, `STAGE_01_PROTOCOL_PSEUDOCODE.md:431`), whose §0.8 note names the record field as the
carrier of stored retry ownership (`STAGE_01_PROTOCOL_PSEUDOCODE.md:435`, "stored retry ownership
(`setup_retry_record.seat_event_ref`)").

### 1c. Both seating procedures publish `seat_event_ref = event_ref` and `event_queue_status = QUEUED`

Each seat guards on the canonical `ScheduleEvent` result `scheduled(event_ref, envelope)` and then publishes the record
atomically with the EventRef bound to `seat_event_ref` and the queue state at `QUEUED`:

- `PrepareParticipantsForNewRound` (PARTICIPANT_SETUP) — `STAGE_01_PROTOCOL_PSEUDOCODE.md:1941`:
  ```
  IF r = scheduled(event_ref, envelope):   # AC1: ScheduleEvent returns the canonical EventRef + envelope
    # Z1/AC8: publish the setup_retry_record ATOMICALLY with status = SEATED, seat_event_ref = the EventRef (immutable),
    #   event_queue_status = QUEUED, AFTER the successful ScheduleEvent. The seat is the ONLY CREATE (AB3).
    ATOMICALLY: SET setup_retry_records[srid] <- setup_retry_record(SetupRetryID = srid, setup_kind = PARTICIPANT_SETUP,
          RoundID = RoundID_current, TemplateID_at_seat = TemplateID_committed, TemplateRefreshSetupID = null,
          retry_generation = g, seat_event_ref = event_ref, event_queue_status = QUEUED, status = SEATED,
          target_disposition = null, terminal_closure_pending = false)   # Z1/AA2/AC1/AC8
  ```
- `ContinueTemplateRefreshAssignmentSetup` (TEMPLATE_REFRESH_SETUP) — `STAGE_01_PROTOCOL_PSEUDOCODE.md:5348`:
  ```
  IF r = scheduled(event_ref, envelope):   # AC1: ScheduleEvent returns the canonical EventRef + envelope
    # Z1/AC8: publish the setup_retry_record ATOMICALLY with status = SEATED, seat_event_ref = the EventRef (immutable),
    #   event_queue_status = QUEUED, AFTER the successful ScheduleEvent. The seat is the ONLY CREATE (AB3).
    ATOMICALLY: SET setup_retry_records[srid] <- setup_retry_record(SetupRetryID = srid, setup_kind = TEMPLATE_REFRESH_SETUP,
          RoundID = RoundID_current, TemplateID_at_seat = TemplateID, TemplateRefreshSetupID = TemplateRefreshSetupID,
          retry_generation = g, seat_event_ref = event_ref, event_queue_status = QUEUED, status = SEATED,
          target_disposition = null, terminal_closure_pending = false)   # Z1/AA2/AC1/AC8
  ```

The `event_ref` bound to `seat_event_ref` is exactly the canonical `EventRef` derived by `ScheduleEvent`
(`STAGE_01_PROTOCOL_PSEUDOCODE.md:504`, `SET event_ref <- EventRef(...)`; returned as `scheduled(event_ref, envelope)` at
`:506`). The seat is the ONLY CREATE of the record (AB3), so `seat_event_ref` is set exactly once.

**Result:** the record type carries `seat_event_ref : EventRef (immutable)` + `event_queue_status : EventQueueStatus`;
`EventQueueStatus in { QUEUED, DISPATCHING, CONSUMED, CANCELLED }` is a declared enum kept separate from the immutable
`EventRef`; both seats publish `seat_event_ref = event_ref` and `event_queue_status = QUEUED` after a successful
`ScheduleEvent`. PASS.

---

## Check 2 — Ownership uses the immutable `rec.seat_event_ref`; consumption marks `event_queue_status <- CONSUMED` (PASS)

### 2a. `SetupRetryEvent` ownership compares the immutable `rec.seat_event_ref` (step 3)

The handler resolves the record to a read-only snapshot (`STAGE_01_PROTOCOL_PSEUDOCODE.md:2118`), then — as guard step 3,
BEFORE any status-replay, stale, or payload handling — compares the dispatcher-injected `dispatched_event_ref` against the
IMMUTABLE `rec.seat_event_ref`:

> `STAGE_01_PROTOCOL_PSEUDOCODE.md:2119`
> ```
> # (3) AC5 EVENTREF OWNERSHIP against the IMMUTABLE seat EventRef (AC1/AC8). CASE B — a foreign / replayed event carries a
> #   valid SetupRetryID but a DIFFERENT EventRef: it does NOT own the record; stale-noop and LEAVE the record SEATED for
> #   its genuine queued event (never consume ownership on a foreign ref). Uses seat_event_ref, which cancellation NEVER erases.
> IF dispatched_event_ref != rec.seat_event_ref:
>   RETURN setup_retry_stale_noop(SetupRetryID)           # AC5-B: foreign/replayed dispatch; genuine event remains seated
> ```

The `dispatched_event_ref` compared here is a mandatory input injected by `ProcessEventTime` from the dispatcher-owned
`EQ.current_event_ref` (AC2; `STAGE_01_PROTOCOL_PSEUDOCODE.md:2097`), "NEVER read from the payload". Because the
comparison target is the immutable seat reference, a foreign ref stale-noops and leaves the genuine record SEATED for its
own queued event.

### 2b. Consumption of the genuine owned event marks `event_queue_status <- CONSUMED`

Both consumption sites — the AC5-C integrity abort of a genuine owned event, and the first-dispatch execution path — mark
the queue state CONSUMED after moving the record off SEATED (`SEATED -> APPLYING`, AC6/AC7):

- AC5-C integrity abort of the genuine owning event — `STAGE_01_PROTOCOL_PSEUDOCODE.md:2162`:
  ```
  CALL SetSetupRetryStatus(SetupRetryID, APPLYING)       # AC6: leave SEATED FIRST (the genuine owned event is being consumed)
  UPDATE setup_retry_records[SetupRetryID].event_queue_status <- CONSUMED   # AC8: this genuine event is consumed now
  ```
- First-dispatch execution — `STAGE_01_PROTOCOL_PSEUDOCODE.md:2203`:
  ```
  ATOMICALLY: CALL SetSetupRetryStatus(SetupRetryID, APPLYING)   # Z1/AC7: SEATED -> APPLYING
  UPDATE setup_retry_records[SetupRetryID].event_queue_status <- CONSUMED   # AC8: the genuine owning event is consumed
  ```

Neither write touches `seat_event_ref`; each mutates ONLY `event_queue_status`. The handler's closing NOTE restates the
contract (`STAGE_01_PROTOCOL_PSEUDOCODE.md:2244`): "IDENTITY (AC8) — ownership uses the immutable `seat_event_ref`;
consuming/cancelling changes only `event_queue_status`."

**Result:** ownership uses `rec.seat_event_ref` (the immutable seat reference, step 3), and both consumption sites set
`event_queue_status <- CONSUMED` while leaving `seat_event_ref` untouched. PASS.

---

## Check 3 — `CancelSetupRetriesForRound` sets `event_queue_status <- CANCELLED` and PRESERVES `seat_event_ref`; no code nulls/erases it (PASS)

### 3a. Round-closure cancellation changes only the queue state and preserves the seat reference

The one named round-closure terminaliser iterates matching `SetupRetryIDs` by key. For a still-SEATED record it cancels
the still-queued dispatch using `seat_event_ref`, marks the QUEUE state CANCELLED, and terminalises the record — leaving
the seat reference intact:

> `STAGE_01_PROTOCOL_PSEUDOCODE.md:2260`
> ```
> IF snapshot.status = SEATED:
>   # AA2/AC8: cancel its still-queued dispatch, mark the QUEUE state CANCELLED (the IMMUTABLE seat_event_ref is PRESERVED
>   #   for replay auditing, AC8), then TERMINALISE the record by key through the transition guard (SEATED -> CANCELLED, AC7).
>   IF snapshot.event_queue_status = QUEUED AND snapshot.seat_event_ref is still pending on EQ: CANCEL snapshot.seat_event_ref on EQ
>   UPDATE setup_retry_records[srid].event_queue_status <- CANCELLED              # AC8: queue state only; seat_event_ref preserved
>   CALL SetSetupRetryStatus(srid, CANCELLED)                                     # AA2/AC7: SEATED -> CANCELLED (legal)
> ```

The cancellation reads `snapshot.seat_event_ref` to cancel the queued event on `EQ`, but the only field written is
`event_queue_status <- CANCELLED`; `seat_event_ref` is not assigned. The procedure's NOTE
(`STAGE_01_PROTOCOL_PSEUDOCODE.md:2282`) confirms: "its `event_queue_status` set CANCELLED (the immutable `seat_event_ref`
is PRESERVED for auditing, AC8)".

### 3b. Grep confirmation: nothing nulls or erases `seat_event_ref`

Read-only grep for any mutation that would null, clear, or erase the seat reference:

```
$ grep -nE "seat_event_ref[[:space:]]*<-[[:space:]]*null|seat_event_ref[[:space:]]*<-[[:space:]]*NULL" STAGE_01_PROTOCOL_PSEUDOCODE.md
$ echo $?
1        # no matches; grep exit status 1
```

```
$ grep -nE "(UPDATE|SET).*seat_event_ref[[:space:]]*<-" STAGE_01_PROTOCOL_PSEUDOCODE.md
$ echo $?
1        # no matches; grep exit status 1 — seat_event_ref is NEVER the target of a standalone UPDATE/SET
```

Match count = **0** in both cases. `seat_event_ref` never appears on the left of an assignment: its only value binding is
the field initialiser `seat_event_ref = event_ref` inside the atomic seat CREATE (Check 1c, lines 1946 / 5353). The only
textual pairing of an "erase"/"clear" word with `seat_event_ref` is prose asserting the opposite — that cancellation NEVER
erases it (`STAGE_01_PROTOCOL_PSEUDOCODE.md:2121` and `:2282`). There is no code path that nulls, clears, or erases the
immutable seat reference.

**Result:** `CancelSetupRetriesForRound` sets `event_queue_status <- CANCELLED` (queue state only) via keyed UPDATE and
preserves `seat_event_ref`; grep confirms zero mutations that null/erase the seat reference. PASS.

---

## Check 4 — The AB6-era "clear event_ref to null" is superseded by "event_queue_status <- CANCELLED" (identity preserved), and the closure post-condition is now "no record has event_queue_status = QUEUED" (PASS)

### 4a. The AB6 "clear event_ref to null" step is explicitly superseded

The §0.8 AB6 lineage note records that the former single-field clear is replaced by the queue-state transition:

> `STAGE_01_PROTOCOL_PSEUDOCODE.md:988`
> ```
> # --- AB6 round-closure terminalisation uses keyed persistent updates + post-conditions ---
> # CancelSetupRetriesForRound uses keyed UPDATEs (AB3), marks a cancelled SEATED record's event_queue_status CANCELLED (AC8,
> #   was "clear event_ref to null" in AB6), and after it completes for closing_RoundID: no record has status = SEATED; no
> #   record of that round has event_queue_status = QUEUED; every terminalised (CANCELLED) record has a terminal
> #   target_disposition; every APPLYING record has terminal_closure_pending persisted in the registry.
> ```

This is corroborated by the §0.8 AC8 note (`STAGE_01_PROTOCOL_PSEUDOCODE.md:1031`, "The Z1-era single `event_ref` field is
REPLACED by this pair"): the earlier design carried one `event_ref` field that closure nulled to signal cancellation; AC8
splits identity from queue state so the same signal is now the `event_queue_status <- CANCELLED` transition, and the
identity survives. Note that the ONLY residual `... <- null` assignment on an event reference anywhere is the dispatcher
clearing its own ambient `EQ.current_event_ref <- null` after a handler returns (AC2;
`STAGE_01_PROTOCOL_PSEUDOCODE.md:228`) — that is dispatcher scaffolding, not the record's seat reference.

### 4b. The closure post-condition is now stated on `event_queue_status = QUEUED`

The AB6/AC8 post-conditions asserted after `CancelSetupRetriesForRound` completes for `closing_RoundID` include the
no-queued-event condition expressed on the queue-state field (not on a nulled reference):

> `STAGE_01_PROTOCOL_PSEUDOCODE.md:2274`
> ```
> ASSERT no id with setup_retry_records[id].RoundID = closing_RoundID has status = SEATED                       # AB6 (1)
> ASSERT no id with setup_retry_records[id].RoundID = closing_RoundID has event_queue_status = QUEUED           # AB6 (2)/AC8: no queued event survives
> ```

The procedure NOTE restates it (`STAGE_01_PROTOCOL_PSEUDOCODE.md:2286`): "After a round closes, NO setup-retry record of
that round remains SEATED and none holds a QUEUED event (AB6/AC8 post-conditions)." The record whose queued event was
cancelled therefore ends `status = CANCELLED` with `event_queue_status = CANCELLED` and `seat_event_ref` still populated
for audit — no queued event survives, and no historical identity is destroyed.

**Result:** the AB6-era "clear event_ref to null" is superseded by `event_queue_status <- CANCELLED` (identity preserved),
and the closure post-condition is expressed as "no record of the round has `event_queue_status = QUEUED`". PASS.

---

## PASS summary

| Check | Claim | Evidence (`STAGE_01_PROTOCOL_PSEUDOCODE.md`) | Result |
|---|---|---|---|
| 1 | Record carries `seat_event_ref : EventRef` (immutable) + `event_queue_status`; `EventQueueStatus` enum declared; both seats publish `seat_event_ref = event_ref` / `event_queue_status = QUEUED` | `:1613`–`:1618` (record type + seating contract); `:446`–`:449` (enum, §0.7e); `:1029`–`:1032` (§0.8 AC8); `:1941`/`:1946` and `:5348`/`:5353` (the two seats) | PASS |
| 2 | Ownership compares the immutable `rec.seat_event_ref` (step 3); consumption sets `event_queue_status <- CONSUMED` | `:2119`–`:2123` (ownership); `:2162`–`:2163` (integrity-abort consume); `:2203`–`:2204` (first-dispatch consume); `:2244` (NOTE) | PASS |
| 3 | `CancelSetupRetriesForRound` sets `event_queue_status <- CANCELLED` and PRESERVES `seat_event_ref`; grep = 0 nulls/erases | `:2260`–`:2265`; `:2282` (NOTE); grep (2×) exit 1, match count 0; `:2121`/`:2282` prose "NEVER erases" | PASS |
| 4 | AB6-era "clear event_ref to null" superseded by `event_queue_status <- CANCELLED`; closure post-condition now "no record has `event_queue_status = QUEUED`" | `:988`–`:992` (supersession); `:1031`–`:1032` (field replaced); `:2274`–`:2275` (post-condition); `:2286` (NOTE) | PASS |

---

## Test-vector linkage — TV251

`STAGE_01AC_SEMANTIC_TEST_VECTORS.md` exercises AC8 with **TV251** ("Round closure cancels the queued event but preserves
the immutable seat EventRef (AC8)", `STAGE_01AC_SEMANTIC_TEST_VECTORS.md:82`). Its procedures are
`CancelSetupRetriesForRound` and `CloseRoundAssignments`; its setup is "a round with a `SEATED` retry record whose
`event_queue_status = QUEUED` is closed"; its expected outcome is that `CancelSetupRetriesForRound` "cancels the queued
event on `EQ`, sets `event_queue_status <- CANCELLED`, and terminalises the record `SEATED → CANCELLED` via
`SetSetupRetryStatus` — while the immutable `seat_event_ref` REMAINS available for replay auditing", and that "After
closure no record of the round is `SEATED` and none has `event_queue_status = QUEUED`". This traces directly to the
cancellation branch verified in Check 3 (`:2260`–`:2265`) and the post-conditions verified in Check 4 (`:2274`–`:2275`).
The companion vector **TV244** (AC1/AC2/AC8) exercises the seat publishing `seat_event_ref = E` / `event_queue_status =
QUEUED` and ownership against that stored `E`, corroborating Checks 1 and 2. Both vectors are specified against exact
procedures in the current pseudocode and preserve the A1 baseline `8.420833333 kWh`.

---

## Cross-document consistency

| Document | Statement | Consistent with pseudocode? |
|---|---|---|
| `STAGE_01_PROTOCOL_PSEUDOCODE.md` (source of truth) | Record carries `seat_event_ref : EventRef` (immutable) + `event_queue_status`; `EventQueueStatus in {QUEUED, DISPATCHING, CONSUMED, CANCELLED}`; both seats publish `seat_event_ref = event_ref` / `event_queue_status = QUEUED`; ownership uses `rec.seat_event_ref`; consume → CONSUMED; closure → CANCELLED with `seat_event_ref` preserved; grep = 0 nulls/erases. | — (baseline) |
| `STAGE_01_ROUND_STATE_MACHINE.md` §3.10g, clause **AC8** (`:950`) | "The retry record carries `seat_event_ref : EventRef` (immutable, set at seat) and `event_queue_status : { QUEUED, DISPATCHING, CONSUMED, CANCELLED }`. Ownership uses `seat_event_ref`; cancellation / consumption changes only `event_queue_status` and never erases the historical seat EventRef used for replay auditing." | Yes — matches Checks 1–4 exactly. |
| `STAGE_01_INVARIANT_CATALOGUE.md` I16 Stage-1AC clause, **AC8** (`:414`) | "the record's immutable `seat_event_ref` is preserved for ownership/audit while cancellation changes only `event_queue_status`." | Yes — matches Checks 2 and 3. |
| `STAGE_01_TERMINOLOGY.md` "`seat_event_ref` + `event_queue_status` (AC8)" (`:1058`) and "`EventQueueStatus` (AC8)" (`:1062`) | `seat_event_ref` immutable set at seat; ownership uses it; cancellation/consumption changes only `event_queue_status`, never erasing the historical seat EventRef; the pair replaces the Z1-era single `event_ref`; `EventQueueStatus = { QUEUED, DISPATCHING, CONSUMED, CANCELLED }`. | Yes — matches Checks 1, 2, 3, 4. |
| `STAGE_01AC_SEMANTIC_TEST_VECTORS.md` TV251 (`:82`) | round-closure cancels the queued event, sets `event_queue_status = CANCELLED`, `SEATED → CANCELLED`; `seat_event_ref` remains for audit; no record `SEATED` and none `QUEUED` after closure. | Yes — traces to the cancellation branch and post-conditions. |
| `STAGE_01_TRACEABILITY_MATRIX.csv` **R213** (`:214`) | "Keep immutable event identity separate from queue state (AC8); a `setup_retry_record` carries `seat_event_ref : EventRef` (immutable set at seat) and `event_queue_status : EventQueueStatus in {QUEUED DISPATCHING CONSUMED CANCELLED}`; ownership comparisons use the immutable `seat_event_ref`; cancellation changes `event_queue_status` (and consumption marks CONSUMED) and never destroys the historical identity … `CancelSetupRetriesForRound` marks a cancelled SEATED record `event_queue_status = CANCELLED` while preserving `seat_event_ref`" — defect: "a cancellation that erases the seat EventRef needed for replay-ownership auditing." | Yes — the four verified checks are exactly R213; the named defect is eliminated (grep = 0). |

All five cross-references (round state machine §3.10g AC8, invariant I16 Stage-1AC clause, terminology, TV251, and R213)
agree with the pseudocode source of truth. No divergence found.

---

## Deliverable tree (Stage 1AC)

This audit (`STAGE_01AC_EVENT_REFERENCE_LIFECYCLE_AUDIT.md`) is deliverable 6 of the Stage-1AC set. The final Stage-1AC
deliverable tree is:

1. `STAGE_01AC_CORRECTION_REPORT.md`
2. `STAGE_01AC_EVENT_REFERENCE_DISPATCH_AUDIT.md` (AC1/AC2)
3. `STAGE_01AC_RETRY_GUARD_ORDER_AUDIT.md` (AC3)
4. `STAGE_01AC_STALE_INTEGRITY_SCOPE_AUDIT.md` (AC4/AC5)
5. `STAGE_01AC_RETRY_STATUS_TRANSITION_AUDIT.md` (AC6/AC7)
6. `STAGE_01AC_EVENT_REFERENCE_LIFECYCLE_AUDIT.md` (AC8) — this file
7. `STAGE_01AC_PROCEDURE_SIGNATURE_CALL_AUDIT.md`
8. `STAGE_01AC_PROCEDURE_CALL_GRAPH.md`
9. `STAGE_01AC_SEMANTIC_TEST_VECTORS.md` (TV244–TV251)
10. `STAGE_01AC_SUPERSESSION_REGISTER.md`
11. `STAGE_01AC_CROSS_DOCUMENT_AUDIT.md`
12. `STAGE_01AC_CHECKSUM_MANIFEST.sha256`

The five modified normative documents are `STAGE_01_PROTOCOL_PSEUDOCODE.md`, `STAGE_01_ROUND_STATE_MACHINE.md` (adds
§3.10g), `STAGE_01_INVARIANT_CATALOGUE.md` (I16 Stage-1AC clause), `STAGE_01_TERMINOLOGY.md` (Stage-1AC addendum), and
`STAGE_01_TRACEABILITY_MATRIX.csv` (rows R206–R214). The miner state machine is not touched (AC1–AC8 concern the
scheduler/dispatcher and the retry-record lifecycle only). The Stage-1A–1AB lettered artifacts are unchanged.

---

## Discipline

This audit is documentation-only: it modifies no specification document and quotes the current lines of the frozen source
of truth. The algorithm remains **PoCol** and the mechanism remains the idle policy within PoCol. The A1 baseline
`8.420833333 kWh` is preserved. Every claim above is grounded in the current `STAGE_01_PROTOCOL_PSEUDOCODE.md`; no guard,
transition, field, or result name is assumed that the pseudocode does not define.

---

## Result

**PASS** — AC8 is faithfully specified: the `setup_retry_record` carries an IMMUTABLE `seat_event_ref : EventRef` set once
at the seat, paired with a separate `event_queue_status : EventQueueStatus in { QUEUED, DISPATCHING, CONSUMED, CANCELLED }`;
`EventQueueStatus` is a declared enum kept separate from the immutable `EventRef`; both seats publish `seat_event_ref =
event_ref` and `event_queue_status = QUEUED`; ownership compares the immutable `rec.seat_event_ref`; consumption marks
`event_queue_status <- CONSUMED` and round-closure cancellation marks `event_queue_status <- CANCELLED` while PRESERVING
`seat_event_ref` (grep = 0 nulls/erases); the AB6-era "clear event_ref to null" is superseded by the queue-state
transition, so the closure post-condition is "no record of the round has `event_queue_status = QUEUED`"; and the
pseudocode, round state machine §3.10g AC8, invariant I16 Stage-1AC clause, terminology, TV251, and R213 are mutually
consistent.
