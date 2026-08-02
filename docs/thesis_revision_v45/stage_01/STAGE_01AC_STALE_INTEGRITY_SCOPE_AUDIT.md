# Stage 1AC — Stale / Integrity Scope Audit (AC4, AC5)

This audit verifies corrections **AC4** and **AC5** of the Stage-1 formal specification of **PoCol** and the idle
policy within PoCol: that a `SetupRetryEvent` decides round membership from the **immutable record fields** before any
payload-integrity abort (AC4), and that no malformed dispatch ever leaves a *known* record `SEATED` while consuming the
genuine event it owns (AC5, cases A/B/C). It is a documentation-only audit; no executable source, configuration, or
experiment is touched, and the A1 baseline (`8.420833333 kWh`) is unchanged.

Correction AC4 answers the residual scoping question: a corrupted or replayed retry payload must never be trusted to
decide *which* round it belongs to. Membership in the current round is read only from `rec.RoundID`, the record's own
round state, and `rec.TemplateID_at_seat`; a record of an older or terminal round is terminalised
(`SUPERSEDED` / `CANCELLED`) and never aborts the later round. Correction AC5 closes the malformed-dispatch matrix: an
unknown id is a stale no-op with no record (Case A); a known id carried by a *foreign* EventRef is a stale no-op that
leaves the genuine event `SEATED` (Case B); and a known id whose *genuine* EventRef arrives with an incomplete envelope
or a payload that mismatches the immutable record is corruption of the owning event — the record is terminalised and the
declared current-round integrity abort is taken, but only because step 5 already proved the record belongs to the current
nonterminal round (Case C). The genuine owned event is never consumed while the record stays `SEATED`.

## Sources of truth (read-only)

- `STAGE_01_PROTOCOL_PSEUDOCODE.md` — §0.8 data-model addenda (AC4 lines 1008–1012; AC5 lines 1013–1018; AB5 lines
  978–987; AC8 lines 1028–1032); `SetupRetryEvent` (§2a, the canonical guard order, steps 1–8); `SetSetupRetryStatus`
  (§2a, the sole status writer, AC7); `CancelSetupRetriesForRound` (§2a, AA2); the two seating publishes
  (`PrepareParticipantsForNewRound`, `ContinueTemplateRefreshAssignmentSetup`).
- `STAGE_01_ROUND_STATE_MACHINE.md` — §3.10g Stage-1AC addendum (AC4 lines 930–932; AC5 lines 934–937).

Corroborating (skimmed, all present): `STAGE_01AC_SEMANTIC_TEST_VECTORS.md` (TV247, TV248);
`STAGE_01AC_EVENT_REFERENCE_DISPATCH_AUDIT.md` (AC1/AC2/AC8 ownership plumbing);
`STAGE_01AC_RETRY_GUARD_ORDER_AUDIT.md` (AC3 guard ordering); `STAGE_01AC_RETRY_STATUS_TRANSITION_AUDIT.md` (AC6/AC7
status path); `STAGE_01AC_CORRECTION_REPORT.md` (the AC scope); `STAGE_01AC_CROSS_DOCUMENT_AUDIT.md`.

---

## §0.8 — the AC4 and AC5 contracts are declared

`STAGE_01_PROTOCOL_PSEUDOCODE.md` §0.8 declares AC4 (lines 1008–1012):

```
  # --- AC4 integrity failure scoped to the record's round ---
  # Before any payload-integrity RoundAbort, membership in the current round is decided from the IMMUTABLE RECORD FIELDS
  #   (rec.RoundID = RoundID_current, the record's round nonterminal, rec.TemplateID_at_seat current) — never untrusted
  #   payload fields. A record of an older/terminal round is terminalised SUPERSEDED/CANCELLED; a corrupted HISTORICAL retry
  #   NEVER aborts a later round.
```

and AC5 (lines 1013–1018):

```
  # --- AC5 malformed dispatch does not leave a known record SEATED ---
  # Case A (invalid/unknown SetupRetryID) -> stale no-op (no record). Case B (known id, foreign dispatched_event_ref !=
  #   rec.seat_event_ref) -> stale no-op, LEAVE the genuine record SEATED. Case C (known id, genuine EventRef, but incomplete
  #   dispatch envelope or payload mismatch) -> corruption of the owning event: terminalise the record, store the exact
  #   integrity disposition, take the declared current-round integrity abort ONLY if the record is of the current nonterminal
  #   round. The genuine owned event is NEVER consumed while the record stays SEATED.
```

Both contracts are declared verbatim and match the §3.10g round-SM addendum (AC4 lines 930–932; AC5 lines 934–937).
The canonical guard order they rely on is fixed in the `SetupRetryEvent` EFFECTS header (lines 2104–2111):

```
    # AC3 CANONICAL GUARD ORDER: (1) structure to resolve the id; (2) RESOLVE the record; (3) AC5 EVENTREF OWNERSHIP
    #   (dispatched_event_ref vs rec.seat_event_ref); (4) AC3 STATUS-based replay (non-SEATED -> duplicate-suppress) BEFORE
    #   any payload/integrity handling; (5) AC4 stale/closed-round disposition decided from the IMMUTABLE RECORD fields;
    #   (6) ONLY for a current owned SEATED record: validate the dispatch envelope + payload (a failure is a CURRENT-round
    #   integrity abort, AC5-C); (7) current-round target guards; (8) target execution.
```

The audit below verifies steps (1)–(6) against this declared order. **PASS (declarations present).**

---

# Part 1 — AC4: integrity scoped to the record's round

## Check A4.1 — step 5 uses `rec.RoundID` / `round_state` / `rec.TemplateID_at_seat`, never payload fields

Step (5) of `SetupRetryEvent` decides round membership. Its comment states the source explicitly (lines 2129–2132):

```
    # (5) AC4 STALE / CLOSED-ROUND DISPOSITION decided from the IMMUTABLE RECORD FIELDS (never the untrusted payload). If the
    #   record's own round is not the current round, or its round is terminal, or the record's committed template identity is
    #   no longer current, TERMINALISE the record — do NOT abort the current round. A corrupted historical retry can never
    #   abort a later round.
```

The three membership tests read **record** fields (and, for the round-state test, the current `round_state` which — since
`rec.RoundID = RoundID_current` has already been established — *is* the record's own round state), never any payload
input of the handler:

```
    IF rec.RoundID != RoundID_current:                                                          # line 2133 — immutable rec.RoundID
      CALL SetSetupRetryStatus(SetupRetryID, SUPERSEDED)     # AC4/AC7: SEATED -> SUPERSEDED (record's round advanced past current)
      ...
    IF round_state in {ROUND_ACCEPTED, ROUND_ABORTED}:       # line 2137 — the record's (current) round is terminal
      CALL SetSetupRetryStatus(SetupRetryID, CANCELLED)      # AC4/AC7: SEATED -> CANCELLED (closed round)
      ...
    IF rec.setup_kind = PARTICIPANT_SETUP:                                                       # line 2141
      IF NOT (a committed eligible TemplateID exists for RoundContext AND rec.TemplateID_at_seat = TemplateID_committed):   # line 2142 — immutable rec.TemplateID_at_seat
        CALL SetSetupRetryStatus(SetupRetryID, SUPERSEDED)   # AC4/AC7: the record's seat-time template is no longer the committed template
        ...
    ELSE:   # rec.setup_kind = TEMPLATE_REFRESH_SETUP
      IF NOT (rec.TemplateID_at_seat = TemplateID_committed                                       # line 2147 — immutable rec fields
              AND template_refresh_setup_committed[rec.TemplateID_at_seat] EXISTS
              AND rec.TemplateRefreshSetupID = template_refresh_setup_committed[rec.TemplateID_at_seat].TemplateRefreshSetupID):
        CALL SetSetupRetryStatus(SetupRetryID, SUPERSEDED)   # AC4/AC7: the record's seat-time refresh template is no longer current
        ...
```

Every predicate at lines 2133, 2137, 2142, 2147–2149 reads `rec.RoundID`, `round_state` (the record's round), or
`rec.TemplateID_at_seat` / `rec.TemplateRefreshSetupID` / `rec.setup_kind`. The handler's payload inputs (`RoundID`,
`TemplateID_at_seat`, `TemplateRefreshSetupID`, `retry_generation`) are **not** consulted here — they are first read only
at step (6), and only to detect corruption of the *already-scoped* current record (line 2160). Because `rec` is the
read-only snapshot of `setup_retry_records[SetupRetryID]` bound at step (2) (line 2118), the fields are the immutable ones
published at the seat (lines 1944–1947): `RoundID = RoundID_current`, `TemplateID_at_seat = TemplateID_committed`,
`seat_event_ref = event_ref`, `status = SEATED`. Membership uses the record, never untrusted payload. **PASS.**

## Check A4.2 — a non-current / terminal-round record is terminalised (`SUPERSEDED`/`CANCELLED`), not aborted

Each of the four step-5 branches ends in a `SetSetupRetryStatus` terminalisation followed by a stale-disposition
`RETURN` — never a `RoundAbort`:

- `rec.RoundID != RoundID_current` → `SUPERSEDED` (line 2134), `target_disposition <- setup_retry_stale_noop`
  (line 2135), `RETURN setup_retry_stale_noop(SetupRetryID)` (line 2136).
- the record's round is terminal → `CANCELLED` (line 2138), `RETURN setup_retry_terminal_stale_noop(SetupRetryID)`
  (line 2140).
- the participant-setup seat-time template is no longer committed → `SUPERSEDED` (line 2143), `RETURN
  setup_retry_stale_noop` (line 2145).
- the template-refresh seat-time template/refresh identity is no longer current → `SUPERSEDED` (line 2150), `RETURN
  setup_retry_stale_noop` (line 2152).

None of these branches reaches step (6) or calls `RoundAbort`; each returns a stale no-op *before* any payload-integrity
handling. The `SUPERSEDED` / `CANCELLED` writes are legal `SEATED ->` edges in the AC7 table (`SEATED -> {APPLYING,
CANCELLED, SUPERSEDED}`, lines 2295, 1025) and go through the sole status writer `SetSetupRetryStatus`. So a corrupted
*historical* retry (one whose immutable `rec.RoundID` predates `RoundID_current`, or whose round has closed) is
terminalised and **cannot abort the later current round**. The handler NOTE restates this (lines 2239–2241):

```
        SCOPE (AC4) — stale/closed disposition uses the IMMUTABLE record fields (rec.RoundID, the
        record's round state, rec.TemplateID_at_seat), so a corrupted HISTORICAL retry is terminalised (SUPERSEDED/CANCELLED)
        and never aborts a later round.
```

Terminalised, never aborted. **PASS.**

### AC4 result table

| Immutable-field condition (step 5) | Predicate (line) | Status edge (line) | Disposition (line) | Aborts current round? |
|---|---|---|---|---|
| `rec.RoundID != RoundID_current` | 2133 | `SEATED -> SUPERSEDED` (2134) | `setup_retry_stale_noop` (2135–2136) | **No** |
| record's round terminal (`round_state ∈ {ROUND_ACCEPTED, ROUND_ABORTED}`) | 2137 | `SEATED -> CANCELLED` (2138) | `setup_retry_terminal_stale_noop` (2139–2140) | **No** |
| participant-setup `rec.TemplateID_at_seat != TemplateID_committed` | 2142 | `SEATED -> SUPERSEDED` (2143) | `setup_retry_stale_noop` (2144–2145) | **No** |
| template-refresh seat identity no longer current | 2147–2149 | `SEATED -> SUPERSEDED` (2150) | `setup_retry_stale_noop` (2151–2152) | **No** |

**AC4 PASS** — membership is decided from `rec.RoundID` / `round_state` / `rec.TemplateID_at_seat`, and every
non-current / terminal-round / stale-template record is terminalised `SUPERSEDED`/`CANCELLED` and returns a stale no-op
before any payload-integrity abort (TV247).

---

# Part 2 — AC5: no known record left SEATED on malformed dispatch

## Case A — structurally-invalid or unknown `SetupRetryID` → stale no-op (no record)

Steps (1) and (2) resolve the id before anything else. A structurally-invalid id resolves to no record, and an id that
was never seated does not exist in the registry:

```
    # (1) AC5-A STRUCTURE: enough to resolve the SetupRetryID. A structurally-invalid id resolves to no record — stale no-op.
    IF SetupRetryID is not structurally valid:
      RETURN setup_retry_stale_noop(SetupRetryID)           # line 2114 — AC5-A: cannot resolve a record
    # (2) AC5-A RESOLVE the ONE record (READ-ONLY snapshot). An unknown id (never seated) is a stale no-op.
    IF setup_retry_records[SetupRetryID] does NOT EXIST:
      RETURN setup_retry_stale_noop(SetupRetryID)           # line 2117 — AC5-A: never seated / unknown; nothing to terminalise
```

There is no record to terminalise and no `SEATED` record to strand — the disposition is a pure stale no-op. **PASS.**

## Case B — known id but foreign `dispatched_event_ref` → stale no-op, genuine event left `SEATED`

Step (3) compares the dispatcher-injected `dispatched_event_ref` (AC2; a mandatory input, never read from the payload,
lines 2097–2100) against the immutable `rec.seat_event_ref`. A mismatch is a foreign or replayed dispatch that does not
own the record:

```
    # (3) AC5 EVENTREF OWNERSHIP against the IMMUTABLE seat EventRef (AC1/AC8). CASE B — a foreign / replayed event carries a
    #   valid SetupRetryID but a DIFFERENT EventRef: it does NOT own the record; stale-noop and LEAVE the record SEATED for
    #   its genuine queued event (never consume ownership on a foreign ref). Uses seat_event_ref, which cancellation NEVER erases.
    IF dispatched_event_ref != rec.seat_event_ref:
      RETURN setup_retry_stale_noop(SetupRetryID)           # line 2123 — AC5-B: foreign/replayed dispatch; genuine event remains seated
```

The `RETURN` at line 2123 performs **no** status transition and **no** `event_queue_status` write — it does not call
`SetSetupRetryStatus`, so the record stays `SEATED`, and it does not touch `event_queue_status`, so the genuine queued
event (`event_queue_status = QUEUED`, published at line 1946) is untouched and still owned by the genuine dispatch whose
EventRef equals `rec.seat_event_ref`. The comparison uses `rec.seat_event_ref`, which AC8 guarantees is immutable and is
never erased by cancellation or consumption (lines 1028–1031). The genuine event remains seated for its own future
dispatch. **PASS.**

## Case C — genuine EventRef + incomplete envelope / payload mismatch → current-round integrity abort

Control reaches step (6) only after step (3) proved ownership (`dispatched_event_ref = rec.seat_event_ref`), step (4)
proved the record is still `SEATED` (a non-`SEATED` replay is duplicate-suppressed at line 2128, *before* any payload
check — AC3), and step (5) proved the record belongs to the **current nonterminal round with the current template**.
Only then is the payload/envelope validated against the immutable record:

```
    # (6) AC5-C OWNING-EVENT INTEGRITY — ONLY for a CURRENT OWNED SEATED record (established current nonterminal round + current
    #   template in step 5). Validate the dispatch envelope AND the payload against the immutable record. A failure is corruption
    #   of the genuine owning event: it may NOT remain SEATED with its only event consumed. Since the record belongs to the
    #   CURRENT NONTERMINAL round, take the declared current-round integrity abort via the AC6 legal path
    #   (SEATED -> APPLYING -> ABORTED).
    IF dispatch_envelope is incomplete
       OR NOT (RoundID = rec.RoundID AND setup_kind = rec.setup_kind AND TemplateID_at_seat = rec.TemplateID_at_seat
               AND TemplateRefreshSetupID = rec.TemplateRefreshSetupID AND retry_generation = rec.retry_generation):
      CALL SetSetupRetryStatus(SetupRetryID, APPLYING)       # line 2162 — AC6: leave SEATED FIRST (the genuine owned event is being consumed)
      UPDATE setup_retry_records[SetupRetryID].event_queue_status <- CONSUMED   # line 2163 — AC8: this genuine event is consumed now
      SET disp <- CALL RoundAbort(RoundContext, reason = setup_retry_payload_integrity_failure(setup_kind),
                        dispatch_envelope = dispatch_envelope, recovery_finalising = false)   # line 2164 — AB2/AC5-C: capture the abort FIRST
      SET post_abort_rec <- setup_retry_records[SetupRetryID]                   # line 2166 — AC6: re-read
      ASSERT post_abort_rec.terminal_closure_pending = true OR round_state in {ROUND_ACCEPTED, ROUND_ABORTED}   # line 2167 — AC6
      UPDATE setup_retry_records[SetupRetryID].target_disposition <- disp       # line 2168 — AB2: store the EXACT round_aborted(abort_record)
      CALL SetSetupRetryStatus(SetupRetryID, ABORTED)        # line 2169 — AC6/AC7: APPLYING -> ABORTED (legal; never SEATED -> ABORTED)
      RETURN disp                                            # line 2170
```

Three properties hold:

1. **The abort is a current-round abort taken only when the record belongs to the current nonterminal round.** The guard
   ordering makes this structural: any non-current / terminal / stale-template record has already returned a stale no-op
   at step (5) (lines 2133–2152), so step (6) is *unreachable* for a historical record. `RoundAbort` at line 2164 therefore
   always aborts the round the record actually belongs to — the current one — satisfying AC5-C's "only if the record is of
   the current nonterminal round".
2. **The status path is the legal AC6 one.** The record moves `SEATED -> APPLYING` *first* (line 2162), then, after
   `RoundAbort` returns (and after any synchronous `CancelSetupRetriesForRound` persists `terminal_closure_pending`, which
   line 2167 asserts), `APPLYING -> ABORTED` (line 2169). Both writes go through `SetSetupRetryStatus`; there is no
   straight `SEATED -> ABORTED` and no terminal → terminal rewrite (AC7 table, lines 2294–2297).
3. **The exact disposition is stored.** `disp <- CALL RoundAbort(...)` is captured *first* (line 2164, AB2) and persisted
   as `target_disposition` (line 2168) before the terminal status is set — the stored disposition is the exact
   `round_aborted(abort_record)` shape, never a bare token.

Current-round integrity abort via `SEATED -> APPLYING -> ABORTED`, taken only for a current owned SEATED record. **PASS.**

## Check A5.x — the genuine owned event is never consumed while the record stays `SEATED`

Consumption of the genuine event (`event_queue_status <- CONSUMED`) occurs at exactly two points, and both are strictly
*after* the record has left `SEATED`:

- the Case C integrity path (line 2163) sets `CONSUMED` only after `SetSetupRetryStatus(APPLYING)` at line 2162, i.e. the
  record is `APPLYING`, no longer `SEATED`;
- the first-dispatch success path (line 2204) sets `CONSUMED` only after `SetSetupRetryStatus(APPLYING)` at line 2203.

In Case B (foreign ref), the record is left `SEATED` and `event_queue_status` is **not** touched (line 2123 returns
directly). In Case A there is no record at all. The §0.8 AB5 contract states the invariant (line 985): "The only event a
SEATED record owns is never consumed while the record stays SEATED", echoed by AC5 (line 1018) and by the handler NOTE
(lines 2245–2246): "consuming/cancelling changes only event_queue_status. A record whose round closed can NEVER finish
APPLIED." No path both leaves the record `SEATED` and marks its event `CONSUMED`. **PASS.**

### AC5 result tables

**Case A — invalid / unknown id (no record):**

| Sub-case | Trigger | Step (line) | Disposition | Record / event left |
|---|---|---|---|---|
| A1 structurally-invalid id | `SetupRetryID` not structurally valid | 1 (2113–2114) | `setup_retry_stale_noop` | no record to strand |
| A2 unknown id (never seated) | `setup_retry_records[SetupRetryID]` does not EXIST | 2 (2116–2117) | `setup_retry_stale_noop` | no record to strand |

**Case B — foreign EventRef (genuine event left SEATED):**

| Sub-case | Trigger | Step (line) | Disposition | Record / event left |
|---|---|---|---|---|
| B foreign / replayed dispatch | `dispatched_event_ref != rec.seat_event_ref` | 3 (2122–2123) | `setup_retry_stale_noop` | record stays **SEATED**; `event_queue_status = QUEUED` untouched; genuine event still owns it |

**Case C — genuine EventRef, corrupt envelope / payload (current-round integrity abort):**

| Sub-case | Trigger | Precondition (from steps 3–5) | Step (lines) | Status path | Disposition |
|---|---|---|---|---|---|
| C incomplete envelope or payload mismatch | `dispatch_envelope` incomplete **or** payload ≠ immutable `rec` | owned (3), still `SEATED` (4), current nonterminal round + current template (5) | 6 (2159–2170) | `SEATED -> APPLYING -> ABORTED` (AC6) | `round_aborted(abort_record)` via `setup_retry_payload_integrity_failure(setup_kind)`; `event_queue_status <- CONSUMED` |

**AC5 PASS** — Case A is a stale no-op with no record; Case B is a stale no-op that leaves the genuine event `SEATED`;
Case C terminalises the record through the legal `SEATED -> APPLYING -> ABORTED` path with the exact integrity
disposition stored, and takes the current-round abort only because step 5 already proved current-round membership. No
path consumes the genuine event while the record remains `SEATED` (TV248).

---

## Test-vector linkage (TV247, TV248)

`STAGE_01AC_SEMANTIC_TEST_VECTORS.md` exercises both corrections:

- **TV247 — A corrupted historical retry from `r1` does not abort the later round `r2` (AC4)** (procedures
  `SetupRetryEvent`, `SetSetupRetryStatus`). Setup: a genuine owned record seated in `r1` (`rec.RoundID = r1`, still
  `SEATED`); `RoundID_current = r2 ≠ r1`; the dispatch payload is corrupted. Expected: after ownership and the non-`SEATED`
  check, step 5 reads `rec.RoundID ≠ RoundID_current` and terminalises `SUPERSEDED` (via `SetSetupRetryStatus`,
  `target_disposition = setup_retry_stale_noop`); the handler returns `setup_retry_stale_noop`; round `r2` is **not**
  aborted and the payload is never consulted for membership. This is precisely Checks A4.1 and A4.2.

- **TV248 — A genuine EventRef with an incomplete dispatch envelope terminalises the record (AC5-C)** (procedures
  `SetupRetryEvent`, `RoundAbort`, `SetSetupRetryStatus`). Setup: a current owned `SEATED` record (current nonterminal
  round, current template) whose genuine event dispatches (`dispatched_event_ref = rec.seat_event_ref`) with an incomplete
  `dispatch_envelope` (or a payload mismatch). Expected: step 6 detects the corruption; `SEATED -> APPLYING` (AC6),
  `event_queue_status <- CONSUMED` (AC8), `disp <- CALL RoundAbort(setup_retry_payload_integrity_failure(setup_kind), ...)`,
  then `APPLYING -> ABORTED` with `target_disposition = disp`; the record cannot remain `SEATED` with its only event
  consumed. This is precisely Case C and Check A5.x.

The coverage summary lists `TV247 | AC4 | SetupRetryEvent, SetSetupRetryStatus` and `TV248 | AC5 | SetupRetryEvent,
RoundAbort`. Both audited corrections are covered. **PASS.**

---

## Cross-document consistency

| Source | Statement of AC4 / AC5 | Agrees |
|---|---|---|
| `STAGE_01_PROTOCOL_PSEUDOCODE.md` §0.8 (AC4 1008–1012; AC5 1013–1018; AB5 978–987; AC8 1028–1032) | membership from immutable rec fields; historical retry terminalised not aborted; Case A/B/C matrix; genuine event never consumed while SEATED | yes |
| `STAGE_01_PROTOCOL_PSEUDOCODE.md` §2a `SetupRetryEvent` steps 1–6 (2112–2170) + NOTE (2235–2247) | executable realisation: step 5 reads `rec.RoundID`/`round_state`/`rec.TemplateID_at_seat`; steps 1–3 are Cases A/B; step 6 is Case C via `SEATED -> APPLYING -> ABORTED` | yes |
| `STAGE_01_PROTOCOL_PSEUDOCODE.md` `SetSetupRetryStatus` (2288–2309) | AC7 table makes `SEATED -> {APPLYING, CANCELLED, SUPERSEDED}` and `APPLYING -> {…, ABORTED}` the only edges used by AC4/AC5 | yes |
| `STAGE_01_ROUND_STATE_MACHINE.md` §3.10g (AC4 930–932; AC5 934–937) | identical prose: immutable-field scoping; older/terminal round terminalised; Case A/B/C with the current-round-only integrity abort | yes |
| `STAGE_01AC_SEMANTIC_TEST_VECTORS.md` TV247, TV248 | exercise the AC4 historical-record scoping and the AC5-C integrity abort against the exact procedures | yes |
| `STAGE_01AC_RETRY_GUARD_ORDER_AUDIT.md` (AC3) | the guard order that makes step 6 unreachable for a historical record and puts the non-SEATED replay check before payload integrity | yes |
| `STAGE_01AC_RETRY_STATUS_TRANSITION_AUDIT.md` (AC6/AC7) | the legal `SEATED -> APPLYING -> ABORTED` path and the terminal-final table used by Case C | yes |

All sources describe the identical contract: round membership is read from the immutable record fields, a
historical/terminal-round record is terminalised (`SUPERSEDED`/`CANCELLED`) and never aborts a later round (AC4); a
malformed dispatch is a stale no-op with no record (A) or leaves the genuine event `SEATED` (B), while a genuine but
corrupt dispatch terminalises the record through the legal `SEATED -> APPLYING -> ABORTED` path and aborts only the
current nonterminal round the record belongs to (C), never consuming the genuine event while the record stays `SEATED`.
No divergence. **PASS.**

---

## Deliverable context

This audit is one of the Stage-1AC deliverables (per `STAGE_01AC_CORRECTION_REPORT.md`). The final Stage-1AC tree
comprises the `STAGE_01AC_*` deliverables — the correction report (`STAGE_01AC_CORRECTION_REPORT.md`); the per-correction
audits `STAGE_01AC_EVENT_REFERENCE_DISPATCH_AUDIT.md`, `STAGE_01AC_RETRY_GUARD_ORDER_AUDIT.md`, this file
(`STAGE_01AC_STALE_INTEGRITY_SCOPE_AUDIT.md`, AC4/AC5), `STAGE_01AC_RETRY_STATUS_TRANSITION_AUDIT.md`, and
`STAGE_01AC_EVENT_REFERENCE_LIFECYCLE_AUDIT.md`; the procedure signature/call audit
(`STAGE_01AC_PROCEDURE_SIGNATURE_CALL_AUDIT.md`) and procedure call graph (`STAGE_01AC_PROCEDURE_CALL_GRAPH.md`); the
semantic test vectors (`STAGE_01AC_SEMANTIC_TEST_VECTORS.md`, TV244–TV251); the supersession register
(`STAGE_01AC_SUPERSESSION_REGISTER.md`); the cross-document audit (`STAGE_01AC_CROSS_DOCUMENT_AUDIT.md`); and the checksum
manifest (`STAGE_01AC_CHECKSUM_MANIFEST.sha256`) — alongside the modified normative `STAGE_01_*` documents
(`STAGE_01_PROTOCOL_PSEUDOCODE.md`, `STAGE_01_ROUND_STATE_MACHINE.md`, and the corroborating catalogue / terminology /
traceability artifacts). The Stage-1A–1AB lettered artifacts are unchanged; Stage-1AC supersessions are recorded in
`STAGE_01AC_SUPERSESSION_REGISTER.md`. This revision is documentation-only: the algorithm remains PoCol, the mechanism
remains the idle policy within PoCol, and the A1 baseline `8.420833333 kWh` is preserved.

---

## Result

**PASS — AC4 and AC5 fully realised. AC4: `SetupRetryEvent` step 5 decides current-round membership from the IMMUTABLE
record fields `rec.RoundID` / the record's `round_state` / `rec.TemplateID_at_seat` (lines 2133, 2137, 2142, 2147–2149),
never untrusted payload; a non-current, terminal-round, or stale-template record is terminalised `SUPERSEDED`/`CANCELLED`
via `SetSetupRetryStatus` and returns a stale no-op before any payload-integrity abort, so a corrupted historical retry
never aborts a later round (TV247). AC5: Case A (invalid/unknown id, lines 2113–2117) is a stale no-op with no record;
Case B (foreign `dispatched_event_ref != rec.seat_event_ref`, lines 2122–2123) is a stale no-op that leaves the genuine
event `SEATED` with `event_queue_status` untouched; Case C (genuine EventRef with incomplete envelope or payload
mismatch, lines 2159–2170) terminalises the record through the legal `SEATED -> APPLYING -> ABORTED` path (AC6), consumes
the genuine event only after leaving `SEATED`, stores the exact `round_aborted(abort_record)` integrity disposition, and
takes the current-round abort only because step 5 already proved current-round membership; the genuine owned event is
never consumed while the record stays `SEATED` (TV248) — consistent across the pseudocode §0.8/§2a, round-SM §3.10g, and
the Stage-1AC guard-order, status-transition, and test-vector deliverables. Documentation-only; PoCol and the idle policy
within PoCol are unchanged; the A1 baseline `8.420833333 kWh` is preserved.**
