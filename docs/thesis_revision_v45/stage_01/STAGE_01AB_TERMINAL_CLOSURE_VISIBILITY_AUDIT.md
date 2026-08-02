# Stage 1AB — Terminal-Closure Visibility Audit (corrections AB4, AB6)

This audit verifies that corrections **AB4** and **AB6** make a round's closure VISIBLE to a mid-flight
setup-retry handler and STRUCTURALLY TERMINAL on the registry, in the frozen source of truth
`STAGE_01_PROTOCOL_PSEUDOCODE.md`. The algorithm is **PoCol**; the mechanism exercised here is the idle
policy within PoCol. All Stage-1AB artifacts preserve the A1 baseline (`8.420833333 kWh`); nothing in
AB4/AB6 touches the energy model. This is a documentation-only audit — it reads the pseudocode and the
companion Stage-1AB deliverables and edits none of them.

Every claim below is grounded with `file:line` citations into `STAGE_01_PROTOCOL_PSEUDOCODE.md`
(abbreviated **PC**), `STAGE_01_ROUND_STATE_MACHINE.md` (**RSM**), and
`STAGE_01AB_SEMANTIC_TEST_VECTORS.md` (**TV**), and quotes the operative current lines. The two
corrections sit in the Stage-1AB retry-record persistence and abort-contract lock layer; this audit is a
sibling of `STAGE_01AB_CORRECTION_REPORT.md`, `STAGE_01AB_EXACT_ABORT_CONTRACT_AUDIT.md`,
`STAGE_01AB_RETRY_RECORD_PERSISTENCE_AUDIT.md`, `STAGE_01AB_RETRY_DISPATCH_OWNERSHIP_AUDIT.md`,
`STAGE_01AB_PROCEDURE_SIGNATURE_CALL_AUDIT.md`, `STAGE_01AB_PROCEDURE_CALL_GRAPH.md`,
`STAGE_01AB_SEMANTIC_TEST_VECTORS.md`, `STAGE_01AB_SUPERSESSION_REGISTER.md`,
`STAGE_01AB_CROSS_DOCUMENT_AUDIT.md`, and `STAGE_01AB_CHECKSUM_MANIFEST.sha256`.

---

## 0. The field and the invocation edge (declaration)

AB4/AB6 turn on one boolean record field and one keyed terminaliser.

- **PC:836–838** (§0.8 data-model block) — the record carries the persisted closure flag:
  > `# setup_retry_record = { SetupRetryID, setup_kind, RoundID, TemplateID_at_seat, TemplateRefreshSetupID, retry_generation,`
  > `#   event_ref, status : SetupRetryStatus, target_disposition, terminal_closure_pending } (terminal_closure_pending : bool,`
  > `#   default false, added AA2). setup_retry_records : map SetupRetryID -> setup_retry_record`

- **PC:1867** and **PC:5236** — both seating procedures publish the record with the flag cleared:
  > `terminal_closure_pending = false)   # Z1/AA2`

- **PC:892–897** (§0.8 AA2) and **PC:2157** — `CancelSetupRetriesForRound(RoundContext, closing_RoundID,
  cancellation_reason, dispatch_or_run_hook_context)` is the ONE named terminaliser, invoked by
  `CloseRoundAssignments`.

- **PC:4976–4977** — the sole invocation edge inside `CloseRoundAssignments`:
  > `CALL CancelSetupRetriesForRound(RoundContext, closing_RoundID = RoundID,`
  > `       cancellation_reason = round_closed(disposition), dispatch_or_run_hook_context = dispatch_envelope)   # AA2`

  and the same procedure's event-cancellation list explicitly includes the retry event — **PC:4970–4972**:
  > `CANCEL all pending wake / resume / certificate-arrival / BlockAcceptancePoint / HashWorkEvent /`
  > `       ... / SetupRetryEvent events for RoundID   # S4/T1/U1/AA2: recovery-timeline AND setup-retry events cancelled at closure`

Grep counts (`STAGE_01_PROTOCOL_PSEUDOCODE.md`): `terminal_closure_pending` = **11**; `post_target_rec`
= **3**; `CancelSetupRetriesForRound` = **6**.

---

## 1. AB4 — re-read the record after the target returns

### 1.1 PASS — the handler RE-READS the persisted record, not a pre-target snapshot

Step (8) of `SetupRetryEvent` flips the record `SEATED -> APPLYING` by key, captures the target result
into a local `disp` (no direct `RETURN CALL`), and then RE-READS the persisted record before classifying.

- **PC:2105–2107** (step (8) header + the keyed `APPLYING` flip):
  > `# (8) Z1 FIRST DISPATCH: atomically transition SEATED -> APPLYING (keyed UPDATE, AB3), CAPTURE the target result (no`
  > `#   direct RETURN CALL), then RE-READ the persisted record (AB4) and set the terminal status deterministically.`
  > `ATOMICALLY: UPDATE setup_retry_records[SetupRetryID].status <- APPLYING       # Z1/AB3: the SEATED record is now being applied`

- **PC:2108–2113** (capture into `disp`, both kinds):
  > `IF setup_kind = PARTICIPANT_SETUP:`
  > `  SET disp <- CALL PrepareParticipantsForNewRound(RoundContext, dispatch_envelope)          # X4: re-run participant setup`
  > `ELSE:   # setup_kind = TEMPLATE_REFRESH_SETUP: ...`
  > `  SET disp <- CALL ContinueTemplateRefreshAssignmentSetup(RoundContext, dispatch_envelope, TemplateID = TemplateID_at_seat, ...)`

- **PC:2114–2117** (the AB4 re-read — the load-bearing line):
  > `# AB4 RE-READ: the target may have synchronously invoked RoundAbort -> CloseRoundAssignments -> CancelSetupRetriesForRound,`
  > `#   which PERSISTS terminal_closure_pending on THIS record by key. Classify on the RE-READ persisted record, NEVER on the`
  > `#   pre-target snapshot `rec`.`
  > `SET post_target_rec <- setup_retry_records[SetupRetryID]                       # AB4: re-read after the target returns`

The classification below reads `post_target_rec.terminal_closure_pending`, not the pre-target snapshot
`rec` (bound read-only at **PC:2036**: `SET rec <- setup_retry_records[SetupRetryID]`). Because `rec` is
a READ-ONLY snapshot taken before the target ran (AB3), it CANNOT reflect a flag the target's synchronous
closure persisted; only the re-read `post_target_rec` can. The re-read is therefore necessary, not
decorative.

**Result: PASS.** After the target returns, the handler binds `post_target_rec` from the live registry
entry (PC:2117) and classifies on it.

### 1.2 PASS — the closure flag is checked FIRST and forces ABORTED / CANCELLED, never APPLIED

The classification tests `post_target_rec.terminal_closure_pending` BEFORE any success branch, so a
closed round pre-empts `APPLIED`:

- **PC:2118–2124** (the flag branch, first):
  > `UPDATE setup_retry_records[SetupRetryID].target_disposition <- disp            # Z1/AB3: keyed persistent UPDATE`
  > `IF post_target_rec.terminal_closure_pending = true:`
  > `  # AA2/AB4: the round CLOSED while this record was APPLYING (CancelSetupRetriesForRound persisted the flag); the record`
  > `  #   MUST finish terminal — NEVER APPLIED. A target round_aborted(abort_record) maps to ABORTED (AA1); any other`
  > `  #   captured disposition maps to CANCELLED.`
  > `  IF disp = round_aborted(abort_record): UPDATE setup_retry_records[SetupRetryID].status <- ABORTED`
  > `  ELSE:                                  UPDATE setup_retry_records[SetupRetryID].status <- CANCELLED`

- **PC:2125–2133** (the normal branches, reached ONLY when the flag is false — note the `ELSE IF`
  chaining off the flag test):
  > `ELSE IF disp = participant_set_prepared OR disp is a committed TemplateID value:`
  > `  UPDATE setup_retry_records[SetupRetryID].status <- APPLIED                   # Z1: setup succeeded (round now HASHING)`
  > `ELSE IF disp = participant_set_setup_retry_seated(...) OR disp = template_refresh_retry_seated(...):`
  > `  UPDATE setup_retry_records[SetupRetryID].status <- SUPERSEDED                # Z1: a later generation was seated by the target`
  > `ELSE IF disp = round_aborted(abort_record):`
  > `  UPDATE setup_retry_records[SetupRetryID].status <- ABORTED                   # AA1: a target RoundAbort result maps to ABORTED (never CANCELLED)`
  > `ELSE:   # disp = template_refresh_retry_stale_noop or another declared stale disposition`
  > `  UPDATE setup_retry_records[SetupRetryID].status <- CANCELLED                 # Z1: a declared stale cancellation`
  > `RETURN disp`

The `APPLIED` write (PC:2126) lives on the `ELSE IF` arm that is entered ONLY when
`post_target_rec.terminal_closure_pending = true` is false. Consequently, when the round closed
mid-flight, control cannot reach `APPLIED`: the record finishes `ABORTED` (target
`round_aborted(abort_record)`) or `CANCELLED` (any other disposition). The handler NOTE restates the
guarantee — **PC:2149–2153**:
> `... RE-READ (AB4) — after the target returns (it may`
> `have synchronously closed the round and persisted terminal_closure_pending on this record), the handler RE-READS the`
> `persisted record and classifies on the stored terminal_closure_pending: APPLIED (succeeded) / SUPERSEDED (later`
> `generation seated) / ABORTED (a target round_aborted(abort_record), AA1 — never CANCELLED) / CANCELLED (a declared`
> `stale/terminal disposition, or a closed round). A record whose round closed can NEVER finish APPLIED.`

**Result: PASS.** The persisted flag is classified FIRST; a record whose round closed finishes `ABORTED`
or `CANCELLED` and can never finish `APPLIED`.

### 1.3 The synchronous causal chain

AB4 closes a window opened by a re-entrant target. The chain is fully grounded:

| Step | Actor | Grounding |
|---|---|---|
| Handler flips this record `SEATED -> APPLYING` by key, then calls the target | `SetupRetryEvent` step (8) | PC:2107–2113 |
| Target synchronously aborts the round | target → `RoundAbort` | PC:2109/2111 → §0.8 AA1 PC:882–890 |
| Abort closes assignments | `RoundAbort` → `CloseRoundAssignments` | PC:4976 invocation edge |
| Closure terminalises this round's retries | `CloseRoundAssignments` → `CancelSetupRetriesForRound` | PC:4973–4977 |
| The terminaliser PERSISTS the flag on THIS record by key (does not overwrite the APPLYING classification) | `CancelSetupRetriesForRound` APPLYING branch | PC:2174–2177 |
| Target returns; handler observes the persisted flag on RE-READ | `SetupRetryEvent` | PC:2117, 2119 |
| Record finishes `ABORTED` / `CANCELLED`, never `APPLIED` | `SetupRetryEvent` | PC:2123–2124 |

The pivotal insight is ordering: the terminaliser runs INSIDE the target call, so by the time
`SET disp <- CALL target(...)` returns, `setup_retry_records[SetupRetryID].terminal_closure_pending` is
already `true` in the registry — but only a re-read (PC:2117), not the stale `rec` snapshot (PC:2036),
can see it. §0.8 AB4 (**PC:937–941**) and RSM §3.10f AB4 (**RSM:881–885**) state exactly this chain:
> `# A SetupRetryEvent target may synchronously CALL RoundAbort -> CloseRoundAssignments -> CancelSetupRetriesForRound, which`
> `#   PERSISTS terminal_closure_pending on THIS record by key. After SET disp <- CALL target(...), the handler RE-READS`
> `#   post_target_rec <- setup_retry_records[SetupRetryID] and classifies on post_target_rec.terminal_closure_pending (the`
> `#   PERSISTED flag), NOT the pre-target snapshot — so a record whose round closed finishes ABORTED/CANCELLED and NEVER APPLIED.`

---

## 2. AB6 — round-closure terminalisation uses keyed persistent updates + post-conditions

### 2.1 PASS — keyed updates over SetupRetryIDs (not detached record values)

`CancelSetupRetriesForRound` iterates matching `SetupRetryID`s in stable order and mutates each record by
key; `snapshot` is read-only.

- **PC:2164–2167** (keyed iteration + read-only snapshot):
  > `# AB3/AA2: iterate the matching SetupRetryIDs (NOT detached record values) in STABLE order and mutate EACH record by KEY.`
  > `#   BOTH PARTICIPANT_SETUP and TEMPLATE_REFRESH_SETUP records carry the seat-time RoundID. `snapshot` is READ-ONLY.`
  > `FOR EACH SetupRetryID srid IN SORT({ id : setup_retry_records[id] EXISTS AND setup_retry_records[id].RoundID = closing_RoundID } ascending):`
  > `  SET snapshot <- setup_retry_records[srid]                                        # AB3: READ-ONLY snapshot; mutate by key below`

### 2.2 PASS — a cancelled SEATED record has its event_ref CLEARED to null

The SEATED branch cancels the still-queued dispatch, CLEARS the now-dead reference to null, then
terminalises the record — every mutation an explicit keyed UPDATE:

- **PC:2168–2173**:
  > `IF snapshot.status = SEATED:`
  > `  # AA2/AB6: cancel its still-queued dispatch, CLEAR the now-dead event reference, then TERMINALISE the record by key.`
  > `  IF snapshot.event_ref != null AND snapshot.event_ref is still pending on EQ: CANCEL snapshot.event_ref on EQ`
  > `  UPDATE setup_retry_records[srid].event_ref <- null                            # AB6: the record owns NO live event`
  > `  UPDATE setup_retry_records[srid].status <- CANCELLED                          # AA2/AB3: keyed persistent UPDATE`
  > `  UPDATE setup_retry_records[srid].target_disposition <- cancellation_reason    # AA2/AB3`

The `event_ref <- null` write (PC:2171) is what makes post-condition (2) hold non-vacuously at the
record level: a cancelled SEATED record retains no reference to a queued event.

### 2.3 PASS — an APPLYING record is flagged, not overwritten

The APPLYING branch persists `terminal_closure_pending` by key and does NOT touch `status` /
`target_disposition`, deferring the terminal classification to the mid-flight handler's re-read (AB4,
§1). Already-terminal records are left unchanged.

- **PC:2174–2178**:
  > `ELSE IF snapshot.status = APPLYING:`
  > `  # AA2/AB4: do NOT overwrite the executing handler's classification; PERSIST terminal_closure_pending by KEY so the`
  > `  #   mid-flight handler RE-READS it (SetupRetryEvent step 8) and finishes ABORTED / CANCELLED, never APPLIED.`
  > `  UPDATE setup_retry_records[srid].terminal_closure_pending <- true             # AA2/AB3: keyed persistent UPDATE`
  > `# APPLIED / SUPERSEDED / CANCELLED / ABORTED records are already terminal — left unchanged.`

### 2.4 PASS — the four asserted post-conditions

After the loop, the procedure ASSERTS four closure post-conditions for `closing_RoundID`; because every
mutation above was a keyed persistent UPDATE, these hold on the registry itself:

- **PC:2179–2183**:
  > `# AB6 POST-CONDITIONS for closing_RoundID (every mutation above was a keyed persistent UPDATE, so these hold on the registry):`
  > `ASSERT no id with setup_retry_records[id].RoundID = closing_RoundID has status = SEATED                       # AB6 (1)`
  > `ASSERT no id with setup_retry_records[id].RoundID = closing_RoundID AND status = SEATED has a queued event_ref on EQ   # AB6 (2) (vacuous given (1))`
  > `ASSERT every id terminalised here (status transitioned to CANCELLED) has a terminal target_disposition        # AB6 (3)`
  > `ASSERT every id with setup_retry_records[id].RoundID = closing_RoundID AND status = APPLYING has terminal_closure_pending = true   # AB6 (4)`

| # | Post-condition (PC line) | Established by |
|---|---|---|
| (1) | no record of `closing_RoundID` is `SEATED` — PC:2180 | SEATED branch flips every match to `CANCELLED` (PC:2172) |
| (2) | no `SEATED` record holds a queued `event_ref` — PC:2181 (vacuous given (1)) | `event_ref <- null` (PC:2171) plus (1) |
| (3) | every terminalised (`CANCELLED`) record has a terminal `target_disposition` — PC:2182 | `target_disposition <- cancellation_reason` (PC:2173) |
| (4) | every `APPLYING` record has `terminal_closure_pending = true` — PC:2183 | APPLYING branch (PC:2177) |

The procedure then returns `setup_retries_terminalised(closing_RoundID)` (**PC:2184–2185**), and its NOTE
restates the guarantee — **PC:2186–2192**:
> `... A SEATED record's queued`
> `SetupRetryEvent is cancelled, its event_ref CLEARED to null (AB6: no live event remains), and the record becomes`
> `CANCELLED; an APPLYING record is not overwritten — terminal_closure_pending is PERSISTED by key so its mid-flight`
> `handler re-reads it (AB4) and finishes ABORTED/CANCELLED. After a round closes, NO setup-retry record of that round`
> `remains SEATED and none holds a queued event (AB6 post-conditions) ...`

§0.8 AB6 (**PC:950–954**) and RSM §3.10f AB6 (**RSM:896–899**) match this in substance:
> `# CancelSetupRetriesForRound uses keyed UPDATEs (AB3), CLEARS a cancelled SEATED record's event_ref to null, and after it`
> `#   completes for closing_RoundID: no record has status = SEATED; no SEATED record has a queued event_ref; every`
> `#   terminalised (CANCELLED) record has a terminal target_disposition; every APPLYING record has terminal_closure_pending`
> `#   persisted in the registry.`

**Result: PASS.** The terminaliser mutates every matching record by key, clears a cancelled SEATED
record's `event_ref` to null, flags (never overwrites) an APPLYING record, and asserts the four closure
post-conditions on the registry.

---

## 3. Verification summary

| Check | Correction | Grounding | Result |
|---|---|---|---|
| Handler re-reads `post_target_rec <- setup_retry_records[SetupRetryID]` after the target returns | AB4 | PC:2114–2117 | PASS |
| Classification tests `post_target_rec.terminal_closure_pending` FIRST | AB4 | PC:2119 (before PC:2125 `APPLIED`) | PASS |
| A closed round forces `ABORTED` / `CANCELLED`, never `APPLIED` | AB4 | PC:2123–2124, NOTE PC:2153 | PASS |
| Synchronous target → RoundAbort → CloseRoundAssignments → CancelSetupRetriesForRound → persisted flag → re-read | AB4 | PC:2107–2117, 4976, 2174–2177; §0.8 PC:937–941 | PASS |
| `CancelSetupRetriesForRound` iterates SetupRetryIDs and UPDATEs by key | AB6 | PC:2164–2167 | PASS |
| Cancelled SEATED record's `event_ref` cleared to null | AB6 | PC:2171 | PASS |
| APPLYING record flagged (`terminal_closure_pending <- true`), not overwritten | AB6 | PC:2174–2177 | PASS |
| Four closure post-conditions asserted | AB6 | PC:2180, 2181, 2182, 2183 | PASS |
| AA2 invocation edge in `CloseRoundAssignments`; SetupRetryEvent in the cancellation list | AB4/AB6 | PC:4970–4977 | PASS |
| `terminal_closure_pending` declared (default false), cleared at both seats | AB4/AB6 | PC:836–838, 1867, 5236 | PASS |

---

## 4. Test-vector linkage (TV240, TV243)

`STAGE_01AB_SEMANTIC_TEST_VECTORS.md` exercises AB4 with **TV240** and AB6 with **TV243**; both name only
procedures/dispositions that exist in the pseudocode and both preserve the A1 baseline `8.420833333 kWh`
(TV:6).

- **TV240 — "An APPLYING target that closes the round finishes ABORTED via the persisted flag, never
  APPLIED (AB4)"** (TV:55–64). It drives a SEATED record to `APPLYING`, has the target synchronously run
  `RoundAbort -> CloseRoundAssignments -> CancelSetupRetriesForRound` (persisting
  `terminal_closure_pending <- true` by key), and requires `SetupRetryEvent` to RE-READ
  `post_target_rec <- setup_retry_records[SetupRetryID]`, observe the flag, and finish `ABORTED` —
  "could never finish `APPLIED`", with classification on a pre-target snapshot "explicitly disallowed".
  This maps one-to-one onto §1 (PC:2117, PC:2119, PC:2123). Its coverage row names `SetupRetryEvent`,
  `CancelSetupRetriesForRound`, `CloseRoundAssignments` under AB4 (TV:107). **Linkage holds.**

- **TV243 — "Round closure terminalises SEATED records and flags an APPLYING record, all by key (AB6)"**
  (TV:86–95). It closes a round holding two SEATED records and one APPLYING record and requires, per
  SEATED record, `CANCEL` of the queued `event_ref`, `UPDATE ...event_ref <- null`,
  `UPDATE ...status <- CANCELLED`, `UPDATE ...target_disposition <- cancellation_reason`; for the
  APPLYING record, `UPDATE ...terminal_closure_pending <- true`; and afterwards the four closure
  post-conditions (no `SEATED`, no queued `event_ref`, terminal `target_disposition`, persisted
  `terminal_closure_pending`) plus "no queued `SetupRetryEvent` for the round survives". This maps
  one-to-one onto §2 (PC:2168–2183) and the cancellation list at PC:4972. Its coverage row names
  `CancelSetupRetriesForRound`, `CloseRoundAssignments` under AB6 (TV:110). **Linkage holds.**

---

## 5. Cross-document consistency

The AB4/AB6 statements are identical in substance across the pseudocode, the round state machine, and the
test vectors.

| Document | Location | Consistency check |
|---|---|---|
| Pseudocode — §0.8 addenda | PC:937–941 (AB4), PC:950–954 (AB6) | Re-read-after-target and keyed-update + post-conditions stated verbatim in substance. |
| Pseudocode — `SetupRetryEvent` step (8) | PC:2105–2133, NOTE PC:2140–2155 | Keyed `APPLYING` flip, capture, re-read `post_target_rec`, flag-first classification forcing ABORTED/CANCELLED, "can NEVER finish APPLIED". |
| Pseudocode — `CancelSetupRetriesForRound` | PC:2157–2192 | Keyed iteration, `event_ref <- null` on cancelled SEATED, APPLYING flagged not overwritten, four asserted post-conditions. |
| Pseudocode — `CloseRoundAssignments` | PC:4970–4977 | Sole AA2 invocation edge; SetupRetryEvent explicitly in the round-closure event-cancellation list. |
| Round SM §3.10f | RSM:881–885 (AB4), RSM:896–899 (AB6); AA2 at RSM:822–828 | Re-read causal chain and closure post-conditions match PC in substance. |
| Test vectors | TV:55–64 (TV240), TV:86–95 (TV243), coverage TV:107/110 | Exercise the exact re-read, keyed updates, and post-conditions above. |

The chain pseudocode §0.8 ↔ `SetupRetryEvent` step (8) ↔ `CancelSetupRetriesForRound` ↔
`CloseRoundAssignments` ↔ RSM §3.10f ↔ TV240/TV243 is coherent: the terminaliser persists closure by
key, and the mid-flight handler re-reads that persisted state before classifying. No document contradicts
another.

---

## 6. Result

**PASS** — corrections AB4 and AB6 hold in the current specification. AB4: `SetupRetryEvent` step (8)
re-reads `post_target_rec <- setup_retry_records[SetupRetryID]` after its target returns (PC:2117) and
classifies on `post_target_rec.terminal_closure_pending` FIRST (PC:2119), so a record whose round closed
synchronously through `RoundAbort -> CloseRoundAssignments -> CancelSetupRetriesForRound` finishes
`ABORTED` or `CANCELLED` (PC:2123–2124) and can NEVER finish `APPLIED`. AB6: `CancelSetupRetriesForRound`
mutates each matching record by key (PC:2164–2167), clears a cancelled SEATED record's `event_ref` to
null (PC:2171), flags an APPLYING record without overwriting it (PC:2177), and asserts the four closure
post-conditions (PC:2180–2183). TV240 (AB4) and TV243 (AB6) and the pseudocode / RSM §3.10f chain are
consistent. This is a documentation-only audit of **PoCol** and the idle policy within PoCol; the A1
baseline `8.420833333 kWh` is preserved and the energy model is untouched.
