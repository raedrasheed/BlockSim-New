# Stage 1AC — Setup-Retry Status Transition Audit (corrections AC6, AC7)

This audit verifies that corrections **AC6** (legal status path for guard-driven aborts) and **AC7**
(the authoritative `SetupRetryStatus` transition table and its sole guard) are correctly realised in the
frozen source of truth `STAGE_01_PROTOCOL_PSEUDOCODE.md`. The algorithm is **PoCol**; the mechanism
exercised here is the idle policy within PoCol. All Stage-1AC artifacts preserve the A1 baseline
(`8.420833333 kWh`); nothing in AC6/AC7 touches the energy model. This is a documentation-only audit — it
reads the pseudocode and the companion Stage-1AC deliverables and edits none of them.

Every claim below is grounded with `file:line` citations into `STAGE_01_PROTOCOL_PSEUDOCODE.md`
(abbreviated **PC** below) and quotes the operative current lines. Grep counts are reported inline.

---

## 0. The guard, the table, and the registry (declaration)

AC7 declares one authoritative transition relation `setup_retry_status_transitions` and one guard
procedure `SetSetupRetryStatus` that owns it; AC6 fixes the legal ordering by which any aborting guard
leaves `SEATED`.

- **PC:840** (the six-member enumeration, unchanged from Y1):
  > `# SetupRetryStatus in { SEATED, APPLYING, APPLIED, SUPERSEDED, CANCELLED, ABORTED } (Y1). Its full lifecycle is owned by`

- **PC:1024–1027** (§0.8 AC7 addendum — the authoritative table + the sole writer):
  > `# --- AC7 SetupRetryStatus transition table + SetSetupRetryStatus guard ---`
  > `# setup_retry_status_transitions: SEATED -> {APPLYING, CANCELLED, SUPERSEDED}; APPLYING -> {APPLIED, SUPERSEDED, CANCELLED,`
  > `#   ABORTED}; APPLIED/SUPERSEDED/CANCELLED/ABORTED are TERMINAL. SetSetupRetryStatus is the SOLE status writer and REJECTS`
  > `#   any illegal transition (especially terminal -> terminal) with no mutation. The seat CREATEs the record at SEATED.`

- **PC:1019–1023** (§0.8 AC6 addendum — the legal abort path):
  > `# --- AC6 legal status path for guard-driven aborts ---`
  > `# A current SEATED retry about to run ANY aborting guard first moves SEATED -> APPLYING, then (after RoundAbort returns and`
  > `#   CancelSetupRetriesForRound has persisted terminal_closure_pending) APPLYING -> ABORTED. There is NEVER a straight`
  > `#   SEATED -> ABORTED and NEVER a terminal -> terminal transition (in particular CANCELLED -> ABORTED is forbidden).`
  > `#   CancelSetupRetriesForRound therefore sees APPLYING and sets terminal_closure_pending (it does not change it to CANCELLED).`

The seat CREATEs the record at `SEATED` and does not call the guard — **PC:1942–1946** (participant seat)
and **PC:5349–5353** (template-refresh seat):
> `# Z1/AC8: publish the setup_retry_record ATOMICALLY with status = SEATED, seat_event_ref = the EventRef (immutable),`
> `#   event_queue_status = QUEUED, AFTER the successful ScheduleEvent. The seat is the ONLY CREATE (AB3).`

Grep counts (`STAGE_01_PROTOCOL_PSEUDOCODE.md`): `SetSetupRetryStatus` = **26**;
`setup_retry_status_transitions` = **3** (PC:1025, 2294, 2299); the keyed status write
`setup_retry_records[...].status <-` = **1** (PC:2304 only — see §1).

---

## 1. PASS — `SetSetupRetryStatus` is the sole status writer, holds the exact table, and rejects illegal (incl. terminal → terminal) transitions with no mutation

`SetSetupRetryStatus` is defined at **PC:2288–2309**. Three facts are checked.

**(a) It holds the exact AC7 table.** The transition relation embedded in the guard's EFFECTS is
verbatim the AC7 addendum — **PC:2294–2297**:
> `# AC7 AUTHORITATIVE TRANSITION TABLE (setup_retry_status_transitions):`
> `#   SEATED   -> { APPLYING, CANCELLED, SUPERSEDED }`
> `#   APPLYING -> { APPLIED, SUPERSEDED, CANCELLED, ABORTED }`
> `#   APPLIED, SUPERSEDED, CANCELLED, ABORTED are TERMINAL (no outgoing edge).`

This matches the §0.8 addendum (PC:1025–1026) and the round-state-machine §3.10g AC7 clause
(`STAGE_01_ROUND_STATE_MACHINE.md:945–948`) member-for-member: `SEATED` has exactly the three
non-terminal successors `{APPLYING, CANCELLED, SUPERSEDED}`; `APPLYING` has exactly the four terminal
successors `{APPLIED, SUPERSEDED, CANCELLED, ABORTED}`; the four terminals have no outgoing edge.

**(b) It is the SOLE writer of `setup_retry_records[*].status`.** The guard's precondition asserts sole
ownership — **PC:2290–2292**:
> `PRECONDITIONS: setup_retry_records[SetupRetryID] EXISTS. This is the ONLY procedure that writes`
> `               setup_retry_records[SetupRetryID].status (every SetupRetryEvent / CancelSetupRetriesForRound status change`
> `               routes through here); the seating publish CREATES the record with status = SEATED and does not call this.`

This is structurally enforced. A grep for the keyed status write
`setup_retry_records[...].status <-` returns exactly **one** hit — **PC:2304**, inside the guard's
EFFECTS:
> `UPDATE setup_retry_records[SetupRetryID].status <- new_status                     # AC3/AC7: the ONE keyed status write`

The broader grep `\.status <-` (13 hits) resolves to this one `setup_retry_records` write (PC:2304) plus
12 writes into the *distinct* `recovery_decisions` / `recovery_work` registries (PC:3103, 3145, 3225,
3235, 3421, 3484, 3517, 3521, 3528, 3535, 3543, 3552, 3562) — none of which is `setup_retry_records`. The
guard's own read `SET current <- setup_retry_records[SetupRetryID].status` (PC:2298) is a READ, not a
write. `SetupRetryEvent` and `CancelSetupRetriesForRound` never write `.status` directly; the pre-target
snapshot `rec` is read-only (PC:2118: "all mutation is keyed UPDATE via SetSetupRetryStatus"). So every
status change in the specification routes through this one guard, and the seat is the only CREATE.

**(c) It rejects illegal transitions — in particular terminal → terminal — with NO mutation.** The guard
tests membership in the table and, on a miss, records the violation and returns a rejection *before* any
UPDATE — **PC:2298–2305**:
> `SET current <- setup_retry_records[SetupRetryID].status`
> `IF (current -> new_status) is NOT in setup_retry_status_transitions:`
> `  # AC7: reject an illegal transition — in particular ANY terminal -> terminal rewrite (e.g. CANCELLED -> ABORTED) — with`
> `  #   NO mutation. A terminal status is FINAL.`
> `  RECORD illegal_setup_retry_status_transition(SetupRetryID, current, new_status)`
> `  RETURN setup_retry_status_transition_rejected(SetupRetryID, current, new_status)`
> `UPDATE setup_retry_records[SetupRetryID].status <- new_status                     # AC3/AC7: the ONE keyed status write`
> `RETURN setup_retry_status_set(SetupRetryID, new_status)`

Because the rejection `RETURN` (PC:2303) precedes the sole UPDATE (PC:2304), an illegal transition — most
importantly a terminal-source rewrite such as `CANCELLED -> ABORTED`, which is absent from the table
(the four terminals have no outgoing edge, PC:2297) — leaves `setup_retry_records[SetupRetryID].status`
untouched. The NOTE restates the guarantee — **PC:2307–2309**:
> `NOTE: AC7: the authoritative guard for every setup_retry_record.status change. It enforces the transition table and`
> `      REJECTS every illegal rewrite — most importantly a terminal -> terminal transition (CANCELLED -> ABORTED, etc.) —`
> `      with no mutation, so a terminal SetupRetryStatus is truly final.`

**Result: PASS.** `SetSetupRetryStatus` (PC:2288–2309) holds the exact AC7 table, is the sole writer of
`setup_retry_records[*].status` (the only keyed write is PC:2304), and rejects illegal transitions —
including every terminal → terminal rewrite — with no mutation.

---

## 2. PASS — every `SetSetupRetryStatus` call site is legal under the table

Every `CALL SetSetupRetryStatus(...)` in `SetupRetryEvent` (PC:2090–2247) and
`CancelSetupRetriesForRound` (PC:2249–2286) is enumerated below with its source status (established by
the preceding guard flow) and target status, and checked against the table
`SEATED -> {APPLYING, CANCELLED, SUPERSEDED}`; `APPLYING -> {APPLIED, SUPERSEDED, CANCELLED, ABORTED}`.

| # | Procedure / step | Line | Transition | Source established by | Legal? |
|---|---|---|---|---|---|
| 1 | `SetupRetryEvent` (5) record's round advanced | PC:2134 | `SEATED -> SUPERSEDED` | step (4) guarantees `rec.status = SEATED` (PC:2127) | Yes |
| 2 | `SetupRetryEvent` (5) closed/terminal round | PC:2138 | `SEATED -> CANCELLED` | still `SEATED` (no prior write on this path) | Yes |
| 3 | `SetupRetryEvent` (5) participant template stale | PC:2143 | `SEATED -> SUPERSEDED` | still `SEATED` | Yes |
| 4 | `SetupRetryEvent` (5) refresh template stale | PC:2150 | `SEATED -> SUPERSEDED` | still `SEATED` | Yes |
| 5 | `SetupRetryEvent` (6) integrity abort — leave SEATED | PC:2162 | `SEATED -> APPLYING` | still `SEATED` | Yes |
| 6 | `SetupRetryEvent` (6) integrity abort — terminalise | PC:2169 | `APPLYING -> ABORTED` | row 5 moved it to `APPLYING` | Yes |
| 7 | `SetupRetryEvent` (7) wrong round state — leave SEATED | PC:2174 | `SEATED -> APPLYING` | still `SEATED` | Yes |
| 8 | `SetupRetryEvent` (7) wrong round state — terminalise | PC:2180 | `APPLYING -> ABORTED` | row 7 moved it to `APPLYING` | Yes |
| 9 | `SetupRetryEvent` (7) budget exhausted — leave SEATED | PC:2183 | `SEATED -> APPLYING` | still `SEATED` | Yes |
| 10 | `SetupRetryEvent` (7) budget exhausted — terminalise | PC:2189 | `APPLYING -> ABORTED` | row 9 moved it to `APPLYING` | Yes |
| 11 | `SetupRetryEvent` (7) state incompatible — leave SEATED | PC:2192 | `SEATED -> APPLYING` | still `SEATED` | Yes |
| 12 | `SetupRetryEvent` (7) state incompatible — terminalise | PC:2198 | `APPLYING -> ABORTED` | row 11 moved it to `APPLYING` | Yes |
| 13 | `SetupRetryEvent` (8) first dispatch | PC:2203 | `SEATED -> APPLYING` | still `SEATED` (all guards passed) | Yes |
| 14 | `SetupRetryEvent` (8) closed-while-APPLYING + abort | PC:2219 | `APPLYING -> ABORTED` | row 13 moved it to `APPLYING` | Yes |
| 15 | `SetupRetryEvent` (8) closed-while-APPLYING + other | PC:2220 | `APPLYING -> CANCELLED` | row 13 moved it to `APPLYING` | Yes |
| 16 | `SetupRetryEvent` (8) target success | PC:2222 | `APPLYING -> APPLIED` | row 13 moved it to `APPLYING` | Yes |
| 17 | `SetupRetryEvent` (8) later generation seated | PC:2224 | `APPLYING -> SUPERSEDED` | row 13 moved it to `APPLYING` | Yes |
| 18 | `SetupRetryEvent` (8) target `round_aborted` | PC:2226 | `APPLYING -> ABORTED` | row 13 moved it to `APPLYING` | Yes |
| 19 | `SetupRetryEvent` (8) declared stale disposition | PC:2228 | `APPLYING -> CANCELLED` | row 13 moved it to `APPLYING` | Yes |
| 20 | `CancelSetupRetriesForRound` SEATED branch | PC:2265 | `SEATED -> CANCELLED` | `IF snapshot.status = SEATED` (PC:2260) | Yes |

Collapsing to distinct edges, exactly seven transitions are exercised, and every one is a member of the
AC7 table:

| Transition | Sites | In table? |
|---|---|---|
| `SEATED -> APPLYING` | PC:2162, 2174, 2183, 2192, 2203 | Yes (`SEATED -> {APPLYING, …}`) |
| `SEATED -> CANCELLED` | PC:2138, 2265 | Yes (`SEATED -> {…, CANCELLED, …}`) |
| `SEATED -> SUPERSEDED` | PC:2134, 2143, 2150 | Yes (`SEATED -> {…, SUPERSEDED}`) |
| `APPLYING -> APPLIED` | PC:2222 | Yes (`APPLYING -> {APPLIED, …}`) |
| `APPLYING -> SUPERSEDED` | PC:2224 | Yes (`APPLYING -> {…, SUPERSEDED, …}`) |
| `APPLYING -> CANCELLED` | PC:2220, 2228 | Yes (`APPLYING -> {…, CANCELLED, …}`) |
| `APPLYING -> ABORTED` | PC:2169, 2180, 2189, 2198, 2219, 2226 | Yes (`APPLYING -> {…, ABORTED}`) |

No call site requests `SEATED -> APPLIED`, `SEATED -> ABORTED`, or any terminal-source edge; those are
absent from both the call sites and the table. `CancelSetupRetriesForRound`'s only guard call is the
`SEATED -> CANCELLED` at PC:2265 — the `APPLYING` branch (PC:2267–2271) deliberately does NOT call the
guard (see §3).

**Result: PASS.** Every one of the 20 `SetSetupRetryStatus` call sites in the two procedures requests a
transition that is a member of the AC7 table; the seven distinct edges are all legal, and no illegal edge
is ever requested.

---

## 3. PASS — AC6: aborting guards go SEATED → APPLYING → ABORTED; no straight SEATED → ABORTED; cancellation sets `terminal_closure_pending`, never CANCELLED → ABORTED

**(a) Each aborting guard does `SEATED -> APPLYING` BEFORE `RoundAbort`.** All four aborting guards in
`SetupRetryEvent` share the identical shape: `SetSetupRetryStatus(APPLYING)` first, then the captured
`RoundAbort`, then `SetSetupRetryStatus(ABORTED)`. The step-6 owning-event integrity abort — **PC:2162–2169**:
> `CALL SetSetupRetryStatus(SetupRetryID, APPLYING)       # AC6: leave SEATED FIRST (the genuine owned event is being consumed)`
> `UPDATE setup_retry_records[SetupRetryID].event_queue_status <- CONSUMED   # AC8: this genuine event is consumed now`
> `SET disp <- CALL RoundAbort(RoundContext, reason = setup_retry_payload_integrity_failure(setup_kind), ...)   # AB2/AC5-C: capture the abort FIRST`
> `SET post_abort_rec <- setup_retry_records[SetupRetryID]                   # AC6: re-read`
> `ASSERT post_abort_rec.terminal_closure_pending = true OR round_state in {ROUND_ACCEPTED, ROUND_ABORTED}   # AC6: round terminalised coherently`
> `UPDATE setup_retry_records[SetupRetryID].target_disposition <- disp       # AB2: store the EXACT round_aborted(abort_record)`
> `CALL SetSetupRetryStatus(SetupRetryID, ABORTED)        # AC6/AC7: APPLYING -> ABORTED (legal; never SEATED -> ABORTED)`

The three step-7 current-round target guards repeat the same ordering — wrong round state
(PC:2174–2180), budget exhausted (PC:2183–2189), and state-incompatible participants (PC:2192–2198) —
each with `SetSetupRetryStatus(APPLYING)` on the line *before* its `CALL RoundAbort(...)` and
`SetSetupRetryStatus(ABORTED)` only *after* the abort result is captured and stored. The step comment is
explicit — **PC:2171–2172**:
> `# (7) X4/W8 CURRENT-ROUND TARGET GUARDS. Each aborting guard follows the AC6 legal path SEATED -> APPLYING -> ABORTED,`
> `#   capturing the abort result FIRST (AB2) and persisting ABORTED via SetSetupRetryStatus.`

**(b) There is NO straight `SEATED -> ABORTED` anywhere.** Every one of the six `APPLYING -> ABORTED`
call sites (PC:2169, 2180, 2189, 2198, 2219, 2226) is reached only after the record has already been
moved to `APPLYING` earlier on the same control-flow path — the four guard aborts by their own
`SEATED -> APPLYING` (rows 5/7/9/11 of §2), and the two step-8 aborts by the first-dispatch
`SEATED -> APPLYING` at PC:2203. Independently, the guard itself makes a straight `SEATED -> ABORTED`
unreachable: `ABORTED` is not a successor of `SEATED` in the table (PC:2295), so even if some path
attempted it, `SetSetupRetryStatus` would reject it with no mutation (§1c). Grep confirms the pairing:
`SetSetupRetryStatus(SetupRetryID, ABORTED)` and `SetSetupRetryStatus(srid, ...)` never appear without a
preceding `APPLYING` write on the path.

**(c) `CancelSetupRetriesForRound` sets `terminal_closure_pending` on an APPLYING record — never
`CANCELLED -> ABORTED`.** When the terminaliser encounters a record that a mid-flight handler has already
moved to `APPLYING`, it does NOT rewrite the status; it persists `terminal_closure_pending` by key and
lets the owning handler finish the terminal transition itself — **PC:2267–2272**:
> `ELSE IF snapshot.status = APPLYING:`
> `  # AA2/AB4/AC6: do NOT overwrite the executing handler's classification (never APPLYING -> CANCELLED here); PERSIST`
> `  #   terminal_closure_pending by KEY so the mid-flight handler RE-READS it (SetupRetryEvent) and finishes`
> `  #   APPLYING -> ABORTED / CANCELLED itself (AC7). This is why an aborting guard first moves SEATED -> APPLYING (AC6).`
> `  UPDATE setup_retry_records[srid].terminal_closure_pending <- true             # AA2/AB3: keyed persistent UPDATE`
> `# APPLIED / SUPERSEDED / CANCELLED / ABORTED records are already terminal — left unchanged (AC7: no terminal -> terminal).`

This closes the AC6 loop. Because the aborting guard moved the record to `APPLYING` *before* calling
`RoundAbort` (step (a)), the synchronous `RoundAbort -> CloseRoundAssignments -> CancelSetupRetriesForRound`
sees `APPLYING` (not `SEATED`), so it takes the `ELSE IF` branch (PC:2267) and sets
`terminal_closure_pending` rather than transitioning the record to `CANCELLED`. Control returns to the
guard, which re-reads (`post_abort_rec`, PC:2166/2177/2186/2195), asserts closure coherence (PC:2167/
2178/2187/2196), stores the exact `round_aborted` disposition, and performs the single legal
`APPLYING -> ABORTED` (PC:2169/2180/2189/2198). No terminal record is ever the *source* of a transition,
so a `CANCELLED -> ABORTED` (or any terminal → terminal) rewrite never occurs — the already-terminal arm
of the loop (PC:2272) leaves such records untouched. The NOTE confirms it — **PC:2283–2285**:
> `… the record becomes CANCELLED via SetSetupRetryStatus (SEATED -> CANCELLED). An APPLYING record is`
> `NOT overwritten — terminal_closure_pending is PERSISTED so its mid-flight handler finishes it APPLYING -> ABORTED /`
> `CANCELLED (so the terminaliser never performs a CANCELLED -> ABORTED or other terminal -> terminal rewrite).`

The step-8 first-dispatch path realises the same discipline for a target that closes the round *while the
record is APPLYING*: after the re-read (`post_target_rec`, PC:2214), a persisted
`terminal_closure_pending` maps `APPLYING -> ABORTED` on a captured `round_aborted` (PC:2219) and
`APPLYING -> CANCELLED` otherwise (PC:2220) — both legal, and both from an `APPLYING` source, never from
a terminal one.

The `SetupRetryEvent` NOTE states the AC6/AC7 invariant in one line — **PC:2242–2244**:
> `LEGAL STATUS PATH (AC6/AC7) — every aborting guard goes SEATED -> APPLYING (before RoundAbort) -> ABORTED via SetSetupRetryStatus;`
> `no SEATED -> ABORTED and no terminal -> terminal rewrite ever occurs.`

**Result: PASS.** Every aborting guard performs `SEATED -> APPLYING` before `RoundAbort` and
`APPLYING -> ABORTED` after (PC:2162/2169, 2174/2180, 2183/2189, 2192/2198); no straight
`SEATED -> ABORTED` exists (all six `APPLYING -> ABORTED` sites are preceded by an `APPLYING` write, and
the guard would reject a `SEATED -> ABORTED` anyway); and `CancelSetupRetriesForRound` sets
`terminal_closure_pending` on an `APPLYING` record (PC:2271) instead of ever writing `CANCELLED -> ABORTED`.

---

## 4. Test-vector linkage (TV249, TV250)

`STAGE_01AC_SEMANTIC_TEST_VECTORS.md` (abbreviated **TV** below) exercises AC6 and AC7 with two blocking
paper vectors; both name only procedures/dispositions that exist in the pseudocode and both preserve the
A1 baseline `8.420833333 kWh`.

- **TV249 — "A guard abort goes SEATED → APPLYING → ABORTED, never CANCELLED → ABORTED (AC6)"**
  (TV:65–72). It drives a current owned `SEATED` retry into an aborting guard and requires the handler to
  `SetSetupRetryStatus(APPLYING)` first, then `disp <- CALL RoundAbort(...)`, whereupon
  `RoundAbort -> CloseRoundAssignments -> CancelSetupRetriesForRound` "sees the record `APPLYING` and
  persists `terminal_closure_pending` (it does NOT change it to `CANCELLED`)", and finally
  `SetSetupRetryStatus(ABORTED)` — "No straight `SEATED -> ABORTED` and no `CANCELLED -> ABORTED`
  transition ever occurs." This maps one-to-one onto the guard ordering in §3(a) (PC:2162/2169,
  2174/2180, 2183/2189, 2192/2198) and the `APPLYING` branch of the terminaliser in §3(c) (PC:2267–2271).
  Its listed procedures (`SetupRetryEvent`, `CancelSetupRetriesForRound`, `RoundAbort`,
  `SetSetupRetryStatus`) are exactly those audited. **Linkage holds.**

- **TV250 — "An illegal CANCELLED → ABORTED transition is rejected with no mutation (AC7)"**
  (TV:74–80). It starts from an already-`CANCELLED` (terminal) record, has some path attempt
  `SetSetupRetryStatus(SetupRetryID, ABORTED)`, and requires that `(CANCELLED -> ABORTED)` — absent from
  `setup_retry_status_transitions` — cause `SetSetupRetryStatus` to record
  `illegal_setup_retry_status_transition` and return `setup_retry_status_transition_rejected` "with NO
  mutation — the record stays `CANCELLED`. A terminal status is final." This maps one-to-one onto the
  rejection block in §1(c) (PC:2298–2303) and the table's terminal rows (PC:2297). **Linkage holds.**

The vector file's coverage table (TV:102–103) records TV249 under correction **AC6** against
`SetupRetryEvent`, `CancelSetupRetriesForRound`, `RoundAbort`, and TV250 under **AC7** against
`SetSetupRetryStatus` — consistent with the procedures audited above.

---

## 5. Cross-document consistency

The AC6/AC7 statement is identical in substance across the pseudocode, its §0.8 addenda, the round state
machine, and the Stage-1AC test vectors.

| Document | Location | Consistency check |
|---|---|---|
| Pseudocode — guard | PC:2288–2309 | `SetSetupRetryStatus` holds the exact table (PC:2294–2297), is the sole `.status` writer (PC:2290–2292, 2304), rejects illegal incl. terminal → terminal with no mutation (PC:2298–2303). |
| Pseudocode — call sites | PC:2134,2138,2143,2150,2162,2169,2174,2180,2183,2189,2192,2198,2203,2219,2220,2222,2224,2226,2228,2265 | All 20 sites legal under the table (§2); AC6 abort ordering `SEATED -> APPLYING -> ABORTED` at every guard (§3). |
| Pseudocode — §0.8 AC6 | PC:1019–1023 | "first moves SEATED -> APPLYING … then APPLYING -> ABORTED"; "NEVER a straight SEATED -> ABORTED and NEVER a terminal -> terminal"; cancellation "sees APPLYING and sets terminal_closure_pending". Matches §3 verbatim in substance. |
| Pseudocode — §0.8 AC7 | PC:1024–1027 | The transition table and "SetSetupRetryStatus is the SOLE status writer and REJECTS any illegal transition (especially terminal -> terminal) with no mutation". Matches §1 verbatim in substance. |
| Round state machine §3.10g AC6 | `STAGE_01_ROUND_STATE_MACHINE.md:939–943` | Same legal abort path; "never a straight `SEATED → ABORTED` and never a terminal → terminal transition (in particular `CANCELLED → ABORTED` is forbidden)"; "`CancelSetupRetriesForRound` therefore sees `APPLYING` and sets `terminal_closure_pending`". Consistent. |
| Round state machine §3.10g AC7 | `STAGE_01_ROUND_STATE_MACHINE.md:945–948` | Authoritative table stated member-for-member; "`SetSetupRetryStatus` is the sole status writer and rejects every illegal transition (especially terminal → terminal) with no mutation". Consistent. |
| Test vectors | `STAGE_01AC_SEMANTIC_TEST_VECTORS.md:65–80, 102–103` | TV249 (AC6) and TV250 (AC7) exercise exactly the audited paths (§4). Consistent. |

The chain pseudocode guard ↔ pseudocode call sites ↔ §0.8 AC6/AC7 ↔ round-SM §3.10g AC6/AC7 ↔ TV249/
TV250 is coherent: one authoritative table, one sole guard, a legal `SEATED -> APPLYING -> ABORTED` abort
path with no straight `SEATED -> ABORTED` and no terminal → terminal rewrite, and a cancellation that
sets `terminal_closure_pending` on an `APPLYING` record. No document contradicts another. These AC6/AC7
findings sit within the broader Stage-1AC deliverable set (the correction report, the event-reference and
dispatch audits, the retry-guard-order and stale-integrity-scope audits, the event-reference lifecycle
audit, the procedure signature/call and call-graph audits, the semantic test vectors, the supersession
register, the cross-document audit, and the checksum manifest), each of which treats the same frozen
pseudocode as its source of truth.

---

## 6. Result

**PASS** — AC6 and AC7 are correctly realised. `SetSetupRetryStatus` (PC:2288–2309) holds the exact
authoritative table `SEATED -> {APPLYING, CANCELLED, SUPERSEDED}`,
`APPLYING -> {APPLIED, SUPERSEDED, CANCELLED, ABORTED}` with four terminal statuses, is the sole writer of
`setup_retry_records[*].status` (the only keyed write is PC:2304), and rejects every illegal transition —
above all any terminal → terminal rewrite such as `CANCELLED -> ABORTED` — with no mutation (§1). All 20
guard call sites in `SetupRetryEvent` and `CancelSetupRetriesForRound` request only the seven legal edges
of the table (§2). Every aborting guard follows the AC6 legal path `SEATED -> APPLYING` (before
`RoundAbort`) then `APPLYING -> ABORTED`; no straight `SEATED -> ABORTED` exists; and
`CancelSetupRetriesForRound` sets `terminal_closure_pending` on an `APPLYING` record rather than ever
performing `CANCELLED -> ABORTED` (§3). TV249 (AC6) and TV250 (AC7) and the round-SM §3.10g AC6/AC7
chain are consistent (§§4–5). This is a documentation-only audit of the PoCol specification and the idle
policy within PoCol, with the A1 baseline `8.420833333 kWh` preserved.
