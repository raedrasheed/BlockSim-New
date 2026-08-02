# Stage 1AB — Setup-Retry Record Persistence Audit (correction AB3)

This audit verifies that correction **AB3** makes every setup-retry record mutation an explicit keyed
registry update in the frozen source of truth `STAGE_01_PROTOCOL_PSEUDOCODE.md`. The algorithm is
**PoCol**; the mechanism exercised here is the idle policy within PoCol. All Stage-1AB artifacts preserve
the A1 baseline (`8.420833333 kWh`); nothing in AB3 touches the energy model. This is a
documentation-only audit — it reads the pseudocode and the companion Stage-1AB deliverables and edits
none of them.

Every claim below is grounded with `file:line` citations into `STAGE_01_PROTOCOL_PSEUDOCODE.md`
(abbreviated **PC** below) and `STAGE_01_ROUND_STATE_MACHINE.md` (abbreviated **RSM**), and quotes the
operative current lines. Grep counts are reported inline.

---

## 0. The rule, the record type, and the registry (declaration)

AB3 states a single persistence rule and applies it to one record type held in one registry.

- **AB3 rule — PC:932–936** (§0.8 data-model block):
  > `# --- AB3 explicit keyed persistence of every setup-retry lifecycle mutation ---`
  > ``# `SET rec <- setup_retry_records[SetupRetryID]` yields a READ-ONLY snapshot; record-reference write semantics are NOT``
  > `#   assumed. The SEAT is the only CREATE. EVERY subsequent lifecycle change is an explicit keyed UPDATE of`
  > `#   setup_retry_records[SetupRetryID] (status / target_disposition / terminal_closure_pending / event_ref).`
  > `#   CancelSetupRetriesForRound iterates SetupRetryIDs (not detached record values) and UPDATEs by key.`

- **Record type + registry — PC:836–838**:
  > `# setup_retry_record = { SetupRetryID, setup_kind, RoundID, TemplateID_at_seat, TemplateRefreshSetupID, retry_generation,`
  > `#   event_ref, status : SetupRetryStatus, target_disposition, terminal_closure_pending } (terminal_closure_pending : bool,`
  > `#   default false, added AA2). setup_retry_records : map SetupRetryID -> setup_retry_record`

- **RSM §3.10f AB3 — RSM:875–879** restates the rule verbatim in substance: the snapshot is read-only,
  "The SEAT is the only CREATE; every subsequent lifecycle change (`status`, `target_disposition`,
  `terminal_closure_pending`, `event_ref`) is an explicit keyed UPDATE of `setup_retry_records[SetupRetryID]`",
  and `CancelSetupRetriesForRound` "iterates `SetupRetryID`s (not detached record values) and updates each
  record by key."

Grep counts (`STAGE_01_PROTOCOL_PSEUDOCODE.md`):
`SET rec.` = **0**; `SET snapshot.` = **0**; `SET setup_retry_records[` (CREATE) = **2**;
`UPDATE setup_retry_records[SetupRetryID]` = **24**; `UPDATE setup_retry_records[srid]` = **4**.

---

## 1. PASS — `rec` is a read-only snapshot; every SetupRetryEvent mutation is a keyed UPDATE

`SetupRetryEvent` binds `rec` exactly once, as a read-only snapshot, and performs NO write through it.

- **PC:2036** (the single bind, annotated read-only):
  > `SET rec <- setup_retry_records[SetupRetryID]            # AB3: READ-ONLY snapshot; all mutation is keyed UPDATE below`

- **PC:2027–2028** (EFFECTS contract, canonical guard order):
  > `#   APPLYING + capture + RE-READ + classify. AB3: rec is a READ-ONLY snapshot; EVERY lifecycle mutation is a keyed`
  > `#   UPDATE of setup_retry_records[SetupRetryID] (the seat is the only CREATE). ...`

- **PC:2146–2147** (procedure NOTE):
  > ``PERSISTENCE (AB3) — `rec` is a READ-ONLY snapshot; the seat is the only``
  > `CREATE and EVERY subsequent lifecycle change is a keyed UPDATE of setup_retry_records[SetupRetryID].`

`rec` is subsequently **read** — for status (`rec.status`, PC:2056), ownership (`rec.event_ref`, PC:2040,
2048), and payload identity (`rec.RoundID`, `rec.setup_kind`, `rec.TemplateID_at_seat`,
`rec.TemplateRefreshSetupID`, `rec.retry_generation`, PC:2046–2047) — but never written. Grep confirms:
`SET rec.<field>` = **0** across the whole file. Every lifecycle write in the handler is instead a keyed
UPDATE — e.g. **PC:2107**:
> `ATOMICALLY: UPDATE setup_retry_records[SetupRetryID].status <- APPLYING       # Z1/AB3: the SEATED record is now being applied`

The post-target classification does not reuse `rec` either: it RE-READS the persisted record into a fresh
snapshot before deciding — **PC:2117**:
> `SET post_target_rec <- setup_retry_records[SetupRetryID]                       # AB4: re-read after the target returns`

**Result: PASS.** `rec` is bound once as a read-only snapshot (PC:2036); no `SET rec.<field>` exists
(grep = 0); every mutation is `UPDATE setup_retry_records[SetupRetryID].<field> <- ...`.

---

## 2. PASS — the seat is the only CREATE; every other write is a keyed UPDATE

Grep for the create form `SET setup_retry_records[...] <- setup_retry_record(...)` returns exactly **2**
occurrences, both on the `scheduled(event_ref)` branch of a seating procedure, publishing `status = SEATED`:

- **PC:1863–1867** (`PrepareParticipantsForNewRound`, `PARTICIPANT_SETUP`):
  > `# Z1: publish the setup_retry_record ATOMICALLY with status = SEATED AFTER the successful ScheduleEvent.`
  > `ATOMICALLY: SET setup_retry_records[srid] <- setup_retry_record(SetupRetryID = srid, setup_kind = PARTICIPANT_SETUP,`
  > `      RoundID = RoundID_current, TemplateID_at_seat = TemplateID_committed, TemplateRefreshSetupID = null,`
  > `      retry_generation = g, event_ref = event_ref, status = SEATED, target_disposition = null,`
  > `      terminal_closure_pending = false)   # Z1/AA2`

- **PC:5232–5236** (`ContinueTemplateRefreshAssignmentSetup`, `TEMPLATE_REFRESH_SETUP`):
  > `# Z1: publish the setup_retry_record ATOMICALLY with status = SEATED AFTER the successful ScheduleEvent.`
  > `ATOMICALLY: SET setup_retry_records[srid] <- setup_retry_record(SetupRetryID = srid, setup_kind = TEMPLATE_REFRESH_SETUP,`
  > `      RoundID = RoundID_current, TemplateID_at_seat = TemplateID, TemplateRefreshSetupID = TemplateRefreshSetupID,`
  > `      retry_generation = g, event_ref = event_ref, status = SEATED, target_disposition = null,`
  > `      terminal_closure_pending = false)   # Z1/AA2`

Both are keyed by the freshly minted `srid` (the newly created record's own SetupRetryID; PC:1855, 5224)
and both construct a complete `setup_retry_record(...)` value — the CREATE. No `SET
setup_retry_records[SetupRetryID] <- ...` form exists anywhere: the grep for the create form matches only
these two `[srid]` publishes, and neither writes over an existing record. Every mutation of an
already-seated record is a per-field keyed UPDATE (§1, §3, §4), never a whole-record re-`SET`.

**Result: PASS.** The two seating publishes (PC:1864, PC:5233) are the only CREATE operations (grep = 2);
no other site re-creates or whole-record-overwrites a registry entry.

---

## 3. PASS — CancelSetupRetriesForRound iterates SetupRetryIDs and updates by key

The terminaliser loops over **ids**, not detached record values, and binds `snapshot` read-only.

- **PC:2166–2167** (iterate ids; read-only snapshot):
  > `FOR EACH SetupRetryID srid IN SORT({ id : setup_retry_records[id] EXISTS AND setup_retry_records[id].RoundID = closing_RoundID } ascending):`
  > `  SET snapshot <- setup_retry_records[srid]                                        # AB3: READ-ONLY snapshot; mutate by key below`

- **PC:2164–2165** (EFFECTS contract):
  > `# AB3/AA2: iterate the matching SetupRetryIDs (NOT detached record values) in STABLE order and mutate EACH record by KEY.`
  > `` #   BOTH PARTICIPANT_SETUP and TEMPLATE_REFRESH_SETUP records carry the seat-time RoundID. `snapshot` is READ-ONLY. ``

`snapshot` is only **read** — for the branch predicate (`snapshot.status`, PC:2168, 2174) and the residual
event ref (`snapshot.event_ref`, PC:2170). Grep confirms `SET snapshot.<field>` = **0**. Every mutation is
a keyed UPDATE on `setup_retry_records[srid]` — the SEATED branch (**PC:2171–2173**):
> `UPDATE setup_retry_records[srid].event_ref <- null                            # AB6: the record owns NO live event`
> `UPDATE setup_retry_records[srid].status <- CANCELLED                          # AA2/AB3: keyed persistent UPDATE`
> `UPDATE setup_retry_records[srid].target_disposition <- cancellation_reason    # AA2/AB3`

and the APPLYING branch (**PC:2177**):
> `UPDATE setup_retry_records[srid].terminal_closure_pending <- true             # AA2/AB3: keyed persistent UPDATE`

Because the writes land in the registry by key, the closing post-conditions hold on the registry itself —
**PC:2179–2183** (AB6 (1)–(4)) assert no id of `closing_RoundID` remains `SEATED`, none holds a queued
`event_ref`, every CANCELLED id has a terminal `target_disposition`, and every APPLYING id has
`terminal_closure_pending = true`. The NOTE restates it — **PC:2186–2188**:
> `` mutates EACH record through a keyed persistent UPDATE (AB3) — `snapshot` is read-only. ``

**Result: PASS.** `CancelSetupRetriesForRound` iterates `SetupRetryID`s (PC:2166), binds `snapshot`
read-only (PC:2167, grep `SET snapshot.` = 0), and mutates each record via `UPDATE
setup_retry_records[srid].<field>` (PC:2171–2173, 2177).

---

## 4. Enumeration of every keyed UPDATE site

All **24** `UPDATE setup_retry_records[SetupRetryID]` sites live in `SetupRetryEvent`; the **4**
`UPDATE setup_retry_records[srid]` sites live in `CancelSetupRetriesForRound`. Each is a keyed persistent
update; none writes through `rec` / `snapshot`.

| # | Lifecycle change | Trigger | Fields updated (keyed) | Grounding |
|---|---|---|---|---|
| 1 | **SEATED → APPLYING** | First valid dispatch (step 8) | `status <- APPLYING` | PC:2107 |
| 2 | **Stale → SUPERSEDED** | Round advanced (RoundID moved on) | `status <- SUPERSEDED`; `target_disposition <- setup_retry_stale_noop` | PC:2062–2063 |
| 3 | **Stale → CANCELLED** | Round terminal/closed (`ROUND_ACCEPTED`/`ROUND_ABORTED`) | `status <- CANCELLED`; `target_disposition <- setup_retry_terminal_stale_noop` | PC:2066–2067 |
| 4 | **Template-identity → CANCELLED** (PARTICIPANT_SETUP) | seat-time TemplateID no longer committed | `status <- CANCELLED`; `target_disposition <- setup_retry_stale_noop` | PC:2073–2074 |
| 5 | **Template-identity → CANCELLED** (TEMPLATE_REFRESH_SETUP) | stale TemplateID / TemplateRefreshSetupID | `status <- CANCELLED`; `target_disposition <- setup_retry_stale_noop` | PC:2080–2081 |
| 6 | **Guard abort → ABORTED** (AB5-C payload integrity) | genuine owning event, mismatched payload | `status <- ABORTED`; `target_disposition <- disp` | PC:2051–2052 |
| 7 | **Guard abort → ABORTED** (wrong round state) | `round_state != ASSIGNMENT` | `status <- ABORTED`; `target_disposition <- disp` | PC:2088–2089 |
| 8 | **Guard abort → ABORTED** (budget exhausted) | `retry_generation > maximum_setup_retries` | `status <- ABORTED`; `target_disposition <- disp` | PC:2096–2097 |
| 9 | **Guard abort → ABORTED** (state incompatible) | an eligible participant not in a re-enlistable state | `status <- ABORTED`; `target_disposition <- disp` | PC:2102–2103 |
| 10 | **Terminal classification — disposition** | after target returns (always) | `target_disposition <- disp` | PC:2118 |
| 11 | **Terminal classification — closure pending** | `post_target_rec.terminal_closure_pending = true` | `status <- ABORTED` (`disp = round_aborted`) or `status <- CANCELLED` (otherwise) | PC:2123–2124 |
| 12 | **Terminal classification — APPLIED** | `disp = participant_set_prepared` or committed TemplateID | `status <- APPLIED` | PC:2126 |
| 13 | **Terminal classification — SUPERSEDED** | `disp = ..._retry_seated(...)` | `status <- SUPERSEDED` | PC:2128 |
| 14 | **Terminal classification — ABORTED** | `disp = round_aborted(abort_record)` | `status <- ABORTED` | PC:2130 |
| 15 | **Terminal classification — CANCELLED** | declared stale disposition | `status <- CANCELLED` | PC:2132 |
| 16 | **Closure — clear event_ref** (SEATED branch) | `CancelSetupRetriesForRound`, SEATED record | `event_ref <- null` | PC:2171 |
| 17 | **Closure — CANCELLED** (SEATED branch) | `CancelSetupRetriesForRound`, SEATED record | `status <- CANCELLED` | PC:2172 |
| 18 | **Closure — disposition** (SEATED branch) | `CancelSetupRetriesForRound`, SEATED record | `target_disposition <- cancellation_reason` | PC:2173 |
| 19 | **Closure — mark pending** (APPLYING branch) | `CancelSetupRetriesForRound`, APPLYING record | `terminal_closure_pending <- true` | PC:2177 |

The `status`-writing UPDATEs by `SetupRetryID` are: PC:2051, 2062, 2066, 2073, 2080, 2088, 2096, 2102,
2107, 2123, 2124, 2126, 2128, 2130, 2132; the `target_disposition`-writing UPDATEs by `SetupRetryID` are:
PC:2052, 2063, 2067, 2074, 2081, 2089, 2097, 2103, 2118 — jointly the **24** counted. The `srid`-keyed
UPDATEs are PC:2171, 2172, 2173, 2177 — the **4** counted. Every terminal status
(`SUPERSEDED`/`CANCELLED`/`ABORTED`/`APPLIED`) and every terminal `target_disposition`, plus the
`APPLYING` transition, the `terminal_closure_pending` flag, and the cleared `event_ref`, is written by a
keyed UPDATE — matching the AB3 field list "status / target_disposition / terminal_closure_pending /
event_ref" (PC:935).

---

## 5. Test-vector linkage (TV239)

`STAGE_01AB_SEMANTIC_TEST_VECTORS.md` exercises AB3 with the blocking paper vector **TV239 — "A SEATED
record's first dispatch flips SEATED -> APPLYING via a keyed persistent update (AB3)"** (TV239:46–53). It
requires that the transition be `ATOMICALLY: UPDATE setup_retry_records[SetupRetryID].status <- APPLYING`
— "an explicit keyed update of the registry entry", with the explicit negative that "Modifying only a
local snapshot (`rec.status`) cannot satisfy the test: the persisted map entry must read `APPLYING`", and
the affirmation that "`rec` is a read-only snapshot; the seat remains the only CREATE." This maps
one-to-one onto the keyed transition grounded in §1/§4 (PC:2107), the read-only snapshot in §1 (PC:2036,
grep `SET rec.` = 0), and the single CREATE in §2 (PC:1864, PC:5233). The vector names only
procedures/dispositions that exist in the pseudocode and preserves the A1 baseline `8.420833333 kWh`
(TV:6). **Linkage holds.**

---

## 6. Cross-document consistency

The AB3 statement is identical in substance across the pseudocode, the round state machine, and the
Stage-1AB deliverable set.

| Document | Location | Consistency check |
|---|---|---|
| Pseudocode | PC:836–838, 932–936, 2036, 2051–2132, 2166–2177 | Record type, AB3 rule, read-only `rec`, 24 keyed UPDATEs in `SetupRetryEvent`, keyed-by-`srid` closure in `CancelSetupRetriesForRound` — all present. |
| Round state machine §3.10f | RSM:875–879 | "read-only snapshot"; "The SEAT is the only CREATE"; every change is "an explicit keyed UPDATE of `setup_retry_records[SetupRetryID]`" over `status`/`target_disposition`/`terminal_closure_pending`/`event_ref`; `CancelSetupRetriesForRound` "iterates `SetupRetryID`s (not detached record values) and updates each record by key". Matches PC in substance. |
| `STAGE_01AB_SEMANTIC_TEST_VECTORS.md` | TV239 (:46–53); table (:106) | TV239 pins the keyed `APPLYING` UPDATE under AB3 against `SetupRetryEvent`; consistent with §1/§4. |
| `STAGE_01AB_CORRECTION_REPORT.md`; `STAGE_01AB_EXACT_ABORT_CONTRACT_AUDIT.md`; `STAGE_01AB_RETRY_DISPATCH_OWNERSHIP_AUDIT.md`; `STAGE_01AB_TERMINAL_CLOSURE_VISIBILITY_AUDIT.md`; `STAGE_01AB_PROCEDURE_SIGNATURE_CALL_AUDIT.md`; `STAGE_01AB_PROCEDURE_CALL_GRAPH.md`; `STAGE_01AB_SUPERSESSION_REGISTER.md`; `STAGE_01AB_CROSS_DOCUMENT_AUDIT.md`; `STAGE_01AB_CHECKSUM_MANIFEST.sha256` | Stage-1AB deliverable set | The AB3 keyed-persistence rule is the shared premise of the abort-contract (AB2), re-read (AB4), ownership (AB5), and closure (AB6) corrections audited by the siblings; the supersession of the Stage-1AA local-`rec` assumption is recorded per RSM:901–904 (AB7). No sibling contradicts the keyed-UPDATE rule. |

The chain pseudocode ↔ RSM §3.10f (AB3) ↔ TV239 ↔ the Stage-1AB deliverable set is coherent: one record
type, one registry, a single CREATE at the seat, and every subsequent lifecycle change a keyed persistent
UPDATE. No document references a write through a detached `rec` / `snapshot` value.

---

## 7. Result

**PASS** — AB3 makes every setup-retry record update explicitly persistent. In `SetupRetryEvent`, `rec` is
bound exactly once as a read-only snapshot (PC:2036) and never written (grep `SET rec.` = 0); all 24
lifecycle mutations are keyed `UPDATE setup_retry_records[SetupRetryID].<field>` writes (PC:2051–2132),
spanning SEATED→APPLYING, stale SUPERSEDED/CANCELLED, template-identity CANCELLED, the four guard aborts,
and the post-target terminal classification. The seat is the only CREATE — exactly two
`SET setup_retry_records[srid] <- setup_retry_record(...)` publishes (PC:1864, PC:5233). In
`CancelSetupRetriesForRound`, the loop iterates `SetupRetryID`s (PC:2166), binds `snapshot` read-only
(PC:2167, grep `SET snapshot.` = 0), and terminalises via 4 keyed `UPDATE setup_retry_records[srid]`
writes (PC:2171–2173, 2177). TV239 and the PC ↔ RSM §3.10f ↔ Stage-1AB deliverable-set chain are
consistent, with the A1 baseline `8.420833333 kWh` preserved. This is a documentation-only audit; the
algorithm is PoCol and the mechanism is the idle policy within PoCol.
