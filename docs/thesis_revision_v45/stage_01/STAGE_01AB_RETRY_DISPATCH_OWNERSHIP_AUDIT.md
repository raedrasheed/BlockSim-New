# Stage 1AB — Retry Dispatch Ownership Audit (correction AB5)

This is a documentation-only audit of correction **AB5** ("bind dispatch ownership to the retry event reference") in the
Stage-1 formal specification of **PoCol** and the idle policy within PoCol. It verifies, against the frozen source of truth
`STAGE_01_PROTOCOL_PSEUDOCODE.md` (read-only), that `SetupRetryEvent` carries a `dispatched_event_ref` input with a
documented derivation, that the canonical guard order places the ownership check (step 1c) AFTER record resolution
(step 1b) and BEFORE payload verification (step 2), that a foreign/replayed event (Case B) returns
`setup_retry_stale_noop` and leaves the record `SEATED`, that the genuine event with a mismatched payload (Case C)
terminalises the record via the declared `setup_retry_payload_integrity_failure` abort while cancelling any residual event
ref, and that both seating publishes set `rec.event_ref` to the reference returned by `ScheduleEvent` so a genuine dispatch
matches. No specification document is modified by this audit; every quoted line is the current line of the source of truth.
The algorithm remains **PoCol** and the mechanism remains the idle policy within PoCol; the A1 baseline
(`8.420833333 kWh`) is unchanged.

- **Correction:** AB5 (dispatch ownership bound to the retry event reference).
- **Source of truth (read-only):** `STAGE_01_PROTOCOL_PSEUDOCODE.md`.
- **Primary procedure:** `SetupRetryEvent`; abort producer `RoundAbort`; seating publishers
  `PrepareParticipantsForNewRound` and `ContinueTemplateRefreshAssignmentSetup`.
- **Requirement:** R202. **Invariant context:** I16 (Stage-1AB clause, AB5), I18b. **Test vectors:** TV241, TV242.

---

## Check 1 — The `dispatched_event_ref` INPUT and its documented derivation (PASS)

`SetupRetryEvent` (`PROCEDURE SetupRetryEvent`, `STAGE_01_PROTOCOL_PSEUDOCODE.md:2010`) declares `dispatched_event_ref` in
its INPUTS list:

> `STAGE_01_PROTOCOL_PSEUDOCODE.md:2011`
> ```
> INPUTS: RoundContext, dispatch_envelope, dispatched_event_ref, RoundID, setup_kind, SetupRetryID,
>         TemplateID_at_seat, TemplateRefreshSetupID, retry_generation, reason
> ```

The INPUTS note documents its derivation and its purpose — the canonical event identity materialised from the dispatch,
derivable from `dispatch_envelope`, compared against the record's `event_ref` to establish ownership BEFORE the handler
operates on the record:

> `STAGE_01_PROTOCOL_PSEUDOCODE.md:2017`
> ```
> # AB5: dispatched_event_ref is the reference of THIS dispatched SetupRetryEvent — the canonical event identity
> #   materialised by ProcessEventTime from the dispatch (derivable from dispatch_envelope, §0.7f). It is compared
> #   against the immutable record's event_ref to establish OWNERSHIP before the handler operates on the record.
> ```

The §0.8 state-model block carries the AB5 addendum that fixes the canonical identity equality and enumerates the three
ownership cases:

> `STAGE_01_PROTOCOL_PSEUDOCODE.md:942`
> ```
> # --- AB5 dispatch ownership bound to the retry event reference ---
> # A SetupRetryEvent carries dispatched_event_ref (the canonical identity of the dispatched event, derivable from
> #   dispatch_envelope §0.7f, equal to the seat-stored rec.event_ref for a genuine dispatch). Ownership: (A) unknown
> #   SetupRetryID -> stale no-op; (B) known id but dispatched_event_ref != rec.event_ref -> FOREIGN replay -> stale no-op,
> #   leave the record SEATED for its genuine queued event; (C) the GENUINE event (dispatched_event_ref = rec.event_ref) with
> #   a payload that mismatches the immutable record -> INTEGRITY corruption of the owning event -> terminalise the record
> #   (ABORTED via the declared setup_retry_payload_integrity_failure abort), cancel any residual event ref, store the exact
> #   integrity-abort disposition. The only event a SEATED record owns is never consumed while the record stays SEATED.
> ```

The `event_ref` against which `dispatched_event_ref` is compared is a declared field of the persisted record —
`setup_retry_record = { …, event_ref, status : SetupRetryStatus, target_disposition, terminal_closure_pending }`
(`STAGE_01_PROTOCOL_PSEUDOCODE.md:836`) — so the comparison is against a stored, immutable-per-seat value, not an ambient
quantity.

**Result:** `dispatched_event_ref` is a declared INPUT of `SetupRetryEvent`; its derivation ("derivable from
`dispatch_envelope`, §0.7f", "equal to the seat-stored `rec.event_ref` for a genuine dispatch") is documented both at the
INPUTS note and in the §0.8 AB5 addendum. PASS.

---

## Check 2 — Guard order: ownership (1c) is AFTER resolution (1b) and BEFORE payload verification (2) (PASS)

The canonical guard order is declared at the top of the EFFECTS block, naming step 1b (RESOLVE the record), step 1c
(AB5 DISPATCH OWNERSHIP: `dispatched_event_ref` vs `rec.event_ref`) and step 2 (payload matches the immutable record,
integrity abort on mismatch) in that fixed sequence:

> `STAGE_01_PROTOCOL_PSEUDOCODE.md:2023`
> ```
> # AB5/AA3/Z1 CANONICAL GUARD ORDER: (1) event shape; (1b) RESOLVE the record; (1c) AB5 DISPATCH OWNERSHIP
> #   (dispatched_event_ref vs rec.event_ref); (2) payload matches the immutable record (a mismatch on the GENUINE owning
> #   event is an INTEGRITY ABORT, AB5-C); (3) STATUS-based EXACT-replay idempotence; (4) stale-RoundID / closed-round
> ```

The executable steps appear in exactly that order. Step 1b resolves the ONE record as a read-only snapshot (and Case A —
an unknown id — is handled here):

> `STAGE_01_PROTOCOL_PSEUDOCODE.md:2033`
> ```
> # (1b) AA3 RESOLVE the ONE record (READ-ONLY snapshot, AB3). CASE A — an unknown id (never seated) is a no-op.
> IF setup_retry_records[SetupRetryID] does NOT EXIST:
>   RETURN setup_retry_stale_noop(SetupRetryID)          # AB5-A: never seated / unknown; nothing to terminalise
> SET rec <- setup_retry_records[SetupRetryID]            # AB3: READ-ONLY snapshot; all mutation is keyed UPDATE below
> ```

Step 1c — the ownership check — comes immediately after resolution and before any payload comparison
(`STAGE_01_PROTOCOL_PSEUDOCODE.md:2037`–`2041`, quoted in Check 3). Step 2 — the payload/integrity check — begins at
`STAGE_01_PROTOCOL_PSEUDOCODE.md:2042` and is reached ONLY when `dispatched_event_ref = rec.event_ref`:

> `STAGE_01_PROTOCOL_PSEUDOCODE.md:2042`
> ```
> # (2) AB5-C INTEGRITY OF THE OWNING EVENT. dispatched_event_ref = rec.event_ref, so THIS is the record's genuine event.
> ```

The closing NOTE restates the ordering as a normative property — ownership is checked BEFORE payload verification:

> `STAGE_01_PROTOCOL_PSEUDOCODE.md:2140`
> ```
> NOTE: AB5/AB4/AB3/AB2/AA1/AA3/Z1/Y1/Y2/Y3/X3/X4/W8: OWNERSHIP (AB5) — the handler resolves the record and checks
>       dispatched_event_ref = rec.event_ref BEFORE payload verification; a FOREIGN event (different ref) stale-noops and
> ```

**Result:** resolution (1b, lines 2033–2036) precedes ownership (1c, lines 2037–2041), which precedes payload/integrity
verification (2, lines 2042–2053); the declared guard-order comment (line 2023) and the NOTE (line 2140) both assert the
same sequence. PASS.

---

## Check 3 — Case B: foreign/replayed event stale-noops and LEAVES the record SEATED (PASS)

Step 1c is the ownership branch. A known `SetupRetryID` whose `dispatched_event_ref` does not equal the record's stored
`event_ref` is a foreign or replayed event that does not own the record; it returns `setup_retry_stale_noop(SetupRetryID)`
and performs NO keyed UPDATE, so the record is left `SEATED` for its genuine queued event:

> `STAGE_01_PROTOCOL_PSEUDOCODE.md:2037`
> ```
> # (1c) AB5 DISPATCH OWNERSHIP. The ONLY event that may operate on a record is the record's OWN queued event. CASE B — a
> #   foreign / replayed event carries a valid SetupRetryID but a DIFFERENT dispatched_event_ref: it does NOT own the
> #   record; stale-noop and LEAVE the record SEATED for its genuine queued event (never consume ownership on a foreign ref).
> IF dispatched_event_ref != rec.event_ref:
>   RETURN setup_retry_stale_noop(SetupRetryID)          # AB5-B: foreign/corrupt replay; genuine event remains seated
> ```

The branch body is a single `RETURN` of the stale no-op disposition; it contains no `UPDATE setup_retry_records[…]`, no
`CANCEL`, and no status change. Because `rec` is a read-only snapshot (`STAGE_01_PROTOCOL_PSEUDOCODE.md:2036`) and this
branch writes nothing, the record's `status` remains `SEATED` and its `event_ref` remains its genuine queued reference —
exactly the invariant "the only event a `SEATED` record owns must not be consumed while the record remains `SEATED`". This
is the outcome asserted by **TV241** in `STAGE_01AB_SEMANTIC_TEST_VECTORS.md` ("A foreign event with a valid SetupRetryID
but different `dispatched_event_ref` stale-noops (AB5-B)"): the check fires, `SetupRetryEvent` returns
`setup_retry_stale_noop(SetupRetryID)` and takes NO ownership, the record remains `SEATED`, and its genuine queued event is
left to dispatch.

**Result:** Case B returns `setup_retry_stale_noop(SetupRetryID)` and mutates nothing (no UPDATE, no CANCEL, no status
change), leaving the record `SEATED`. PASS.

---

## Check 4 — Case C: genuine event, mismatched payload — cancel residual ref, capture abort, persist ABORTED, return disp (PASS)

Step 2 is reached only when `dispatched_event_ref = rec.event_ref` (Check 2), i.e. THIS is the record's genuine owning
event. If the genuine event's payload disagrees with the immutable record on any of the identity fields, the owning event
itself is corrupt; the record must not remain `SEATED` with its only event consumed. The handler (a) cancels any residual
still-pending event ref, (b) captures `disp <- CALL RoundAbort(reason = setup_retry_payload_integrity_failure(…))` FIRST,
(c) persists `status <- ABORTED` and `target_disposition <- disp` by key, and (d) returns `disp`:

> `STAGE_01_PROTOCOL_PSEUDOCODE.md:2042`
> ```
> # (2) AB5-C INTEGRITY OF THE OWNING EVENT. dispatched_event_ref = rec.event_ref, so THIS is the record's genuine event.
> #   If the genuine event's payload disagrees with the IMMUTABLE record, the owning event itself is corrupted: the record
> #   must NOT remain SEATED with its only event consumed. TERMINALISE via a declared integrity abort — capture the abort
> #   result FIRST (AB2), then persist ABORTED + the exact returned disposition by key, and cancel any residual event ref.
> IF NOT (RoundID = rec.RoundID AND setup_kind = rec.setup_kind AND TemplateID_at_seat = rec.TemplateID_at_seat
>         AND TemplateRefreshSetupID = rec.TemplateRefreshSetupID AND retry_generation = rec.retry_generation):
>   IF rec.event_ref != null AND rec.event_ref is still pending on EQ: CANCEL rec.event_ref on EQ   # AB5-C: no live event left
>   SET disp <- CALL RoundAbort(RoundContext, reason = setup_retry_payload_integrity_failure(setup_kind),
>                     dispatch_envelope = dispatch_envelope, recovery_finalising = false)   # AB2/AB5-C: capture the abort FIRST
>   UPDATE setup_retry_records[SetupRetryID].status <- ABORTED                              # AB3: keyed persistent UPDATE
>   UPDATE setup_retry_records[SetupRetryID].target_disposition <- disp                     # AB2: store the EXACT round_aborted(abort_record)
>   RETURN disp
> ```

Every element of AB5-C is present and in the declared order: the residual-ref cancellation is guarded on non-null AND
still-pending (`IF rec.event_ref != null AND rec.event_ref is still pending on EQ: CANCEL rec.event_ref on EQ`); the abort
is captured into `disp` FIRST (AB2) via the declared reason `setup_retry_payload_integrity_failure(setup_kind)`; the record
is then terminalised with two keyed UPDATEs (`status <- ABORTED`, `target_disposition <- disp`); and the handler returns
the exact captured `disp`. The stored `target_disposition` is the exact `round_aborted(abort_record)` value returned by
`RoundAbort`, never a bare token written before the abort result exists. This is the outcome asserted by **TV242** in
`STAGE_01AB_SEMANTIC_TEST_VECTORS.md` ("The genuine event_ref dispatches with a corrupted payload -> integrity abort, no
SEATED record left (AB5-C)"): `SetupRetryEvent` cancels any residual `rec.event_ref` on EQ, executes
`SET disp <- CALL RoundAbort(reason = setup_retry_payload_integrity_failure(setup_kind), …)`, persists `status <- ABORTED`
and `target_disposition <- disp` by key, and returns `disp`, so the record cannot remain `SEATED` with its only event
consumed.

**Result:** on the genuine event with a mismatched payload, the handler cancels any residual pending event ref, captures
`disp <- CALL RoundAbort(reason = setup_retry_payload_integrity_failure(…))` first, persists `ABORTED` +
`target_disposition = disp` by key, and returns `disp`. PASS.

---

## Check 5 — The seating publishes set `rec.event_ref` to the `ScheduleEvent`-returned reference (PASS)

For the ownership equality to distinguish a genuine dispatch from a foreign one, the seated record's `event_ref` must be
the exact reference of the event that `ScheduleEvent` enqueued. Both seating publishers bind `event_ref` to the reference
destructured from the successful `ScheduleEvent` result `scheduled(event_ref)`.

`PrepareParticipantsForNewRound` seats the PARTICIPANT_SETUP retry record:

> `STAGE_01_PROTOCOL_PSEUDOCODE.md:1856`
> ```
> SET r <- CALL ScheduleEvent(EQ, RoundContext, SetupRetryEvent,
>                target_event_time = next_representable_simulation_time(dispatch_envelope.event_time),
>                target_microphase = ROUND_SETUP,
>                {RoundID = RoundID_current, setup_kind = PARTICIPANT_SETUP, SetupRetryID = srid,
>                 TemplateID_at_seat = TemplateID_committed, TemplateRefreshSetupID = null,
>                 retry_generation = g, reason = setup_reason})                   # W8/Y2/Y3: exact identity + scalar generation
> IF r = scheduled(event_ref):
>   # Z1: publish the setup_retry_record ATOMICALLY with status = SEATED AFTER the successful ScheduleEvent.
>   ATOMICALLY: SET setup_retry_records[srid] <- setup_retry_record(SetupRetryID = srid, setup_kind = PARTICIPANT_SETUP,
>         RoundID = RoundID_current, TemplateID_at_seat = TemplateID_committed, TemplateRefreshSetupID = null,
>         retry_generation = g, event_ref = event_ref, status = SEATED, target_disposition = null,
>         terminal_closure_pending = false)   # Z1/AA2
> ```

`ContinueTemplateRefreshAssignmentSetup` seats the TEMPLATE_REFRESH_SETUP retry record identically:

> `STAGE_01_PROTOCOL_PSEUDOCODE.md:5225`
> ```
> SET r <- CALL ScheduleEvent(EQ, RoundContext, SetupRetryEvent,
>                target_event_time = next_representable_simulation_time(dispatch_envelope.event_time),
>                target_microphase = ROUND_SETUP,
>                {RoundID = RoundID_current, setup_kind = TEMPLATE_REFRESH_SETUP, SetupRetryID = srid,
>                 TemplateID_at_seat = TemplateID, TemplateRefreshSetupID = TemplateRefreshSetupID,
>                 retry_generation = g, reason = setup_reason})               # W8/X3/Y2/Y3: the retry resumes THIS procedure (never TemplateRefresh) with the EXACT identity
> IF r = scheduled(event_ref):
>   # Z1: publish the setup_retry_record ATOMICALLY with status = SEATED AFTER the successful ScheduleEvent.
>   ATOMICALLY: SET setup_retry_records[srid] <- setup_retry_record(SetupRetryID = srid, setup_kind = TEMPLATE_REFRESH_SETUP,
>         RoundID = RoundID_current, TemplateID_at_seat = TemplateID, TemplateRefreshSetupID = TemplateRefreshSetupID,
>         retry_generation = g, event_ref = event_ref, status = SEATED, target_disposition = null,
>         terminal_closure_pending = false)   # Z1/AA2
> ```

In both publishers the record's `event_ref` field is set to the `event_ref` bound by the `IF r = scheduled(event_ref)`
pattern — i.e. the reference of the event `ScheduleEvent` actually enqueued — and the record is published atomically with
`status = SEATED` only on the successful-schedule branch. When `ProcessEventTime` later dispatches that same enqueued
event, its `dispatched_event_ref` (derivable from `dispatch_envelope`, Check 1) equals the stored `rec.event_ref`, so the
genuine dispatch passes the step-1c ownership check while any foreign/replayed event fails it.

**Result:** both seating publishes set `rec.event_ref <- event_ref` where `event_ref` is the reference returned by
`ScheduleEvent` as `scheduled(event_ref)`, so a genuine dispatch's `dispatched_event_ref` matches the seat-stored
reference. PASS.

---

## PASS / verification tables

### Ownership cases (steps 1b / 1c / 2)

| Case | Condition | Guard step | Action | Record after | Source of truth |
|---|---|---|---|---|---|
| A | `setup_retry_records[SetupRetryID]` does NOT exist (unknown / never seated) | 1b (`:2034`) | `RETURN setup_retry_stale_noop(SetupRetryID)` | no record to leave (none exists) | `:2033`–`2036` |
| B | known id, `dispatched_event_ref != rec.event_ref` (foreign/replayed) | 1c (`:2040`) | `RETURN setup_retry_stale_noop(SetupRetryID)`; no UPDATE, no CANCEL | **`SEATED`** — genuine event untouched | `:2037`–`2041` |
| C | genuine event (`dispatched_event_ref = rec.event_ref`), payload mismatch | 2 (`:2046`) | cancel residual ref; `disp <- CALL RoundAbort(setup_retry_payload_integrity_failure)`; UPDATE `ABORTED` + `target_disposition <- disp`; `RETURN disp` | **`ABORTED`**, exact stored disposition, no live event | `:2042`–`2053` |

### AB5 obligation checklist

| # | Obligation (AB5) | Verified at | Verdict |
|---|---|---|---|
| 1 | `dispatched_event_ref` is a declared `SetupRetryEvent` INPUT | `:2011` | PASS |
| 2 | Derivation documented (from `dispatch_envelope`, §0.7f; = seat-stored `rec.event_ref` for a genuine dispatch) | `:2017`–`2019`, `:942`–`949` | PASS |
| 3 | Guard order: 1c ownership AFTER 1b resolve, BEFORE 2 payload | `:2023`, `:2033`–`2042`, NOTE `:2140` | PASS |
| 4 | Case A unknown id → stale no-op | `:2034`–`2035` | PASS |
| 5 | Case B foreign ref → `setup_retry_stale_noop`, no mutation, record `SEATED` | `:2040`–`2041` | PASS |
| 6 | Case C cancels any residual still-pending event ref | `:2048` | PASS |
| 7 | Case C captures `disp <- CALL RoundAbort(setup_retry_payload_integrity_failure)` FIRST | `:2049`–`2050` | PASS |
| 8 | Case C persists `ABORTED` + `target_disposition = disp` by key, returns `disp` | `:2051`–`2053` | PASS |
| 9 | Seating publishes set `rec.event_ref` to the `ScheduleEvent`-returned reference | `:1862`–`1866`, `:5231`–`5235` | PASS |
| 10 | A `SEATED` record's only event is never consumed while it stays `SEATED` | Case B (no mutation) + Case C (terminalises before consuming) | PASS |

---

## Cross-document consistency

| Document | Statement | Consistent with pseudocode? |
|---|---|---|
| `STAGE_01_PROTOCOL_PSEUDOCODE.md` (source of truth) | `dispatched_event_ref` INPUT + derivation; guard order 1b→1c→2; Case B stale no-op leaves `SEATED`; Case C integrity abort terminalises + cancels residual ref; seats bind `event_ref` to `scheduled(event_ref)`. | — (baseline) |
| `STAGE_01_ROUND_STATE_MACHINE.md` §3.10f, clause **AB5** (`:887`) | "A `SetupRetryEvent` carries `dispatched_event_ref` … equal to the seat-stored `rec.event_ref` for a genuine dispatch. (A) unknown id → stale no-op; (B) `dispatched_event_ref ≠ rec.event_ref` → foreign/replayed → stale no-op that LEAVES the record `SEATED`; (C) genuine event with a mismatched payload → integrity abort via `setup_retry_payload_integrity_failure` (`ABORTED`, exact stored disposition), cancelling any residual event ref." | Yes — matches Checks 1–5 exactly. |
| `STAGE_01_INVARIANT_CATALOGUE.md` I16 Stage-1AB clause, **AB5** (`:398`) | "`dispatched_event_ref` binds ownership — an unknown id or a foreign `dispatched_event_ref ≠ rec.event_ref` stale-noops (leaving the genuine record seated), and the genuine event with a mismatched payload is an integrity abort that terminalises the record and cancels any residual event." | Yes — matches Checks 3 and 4. |
| `STAGE_01_TERMINOLOGY.md` "`dispatched_event_ref` — dispatch ownership (AB5)" (`:1031`) and "`setup_retry_payload_integrity_failure` (AB5)" (`:1037`) | unknown id → stale no-op; foreign/replayed ref → stale no-op leaving the record `SEATED`; genuine event + mismatched payload → integrity abort that terminalises `ABORTED` and cancels any residual event ref; the declared abort reason names the payload disagreement. | Yes — matches Checks 1, 3, 4. |
| `STAGE_01_TRACEABILITY_MATRIX.csv` **R202** (`:203`) | "Bind dispatch ownership to the retry event reference (AB5) … case A unknown id stale-noops; case B a foreign/replayed `dispatched_event_ref` stale-noops and leaves the record SEATED; case C the genuine mismatched-payload event terminalises via `setup_retry_payload_integrity_failure`, stores the exact integrity-abort disposition and cancels any residual event ref." Defect: "a foreign event that takes ownership of another retry record or a genuine corrupted-payload dispatch that consumes the event yet leaves the record SEATED." | Yes — the five verified checks are exactly the R202 requirement; the named defect is eliminated (Case B leaves `SEATED` without consuming; Case C terminalises before releasing). |
| `STAGE_01AB_SEMANTIC_TEST_VECTORS.md` TV241 (`:66`), TV242 (`:75`) | TV241: foreign ref → `setup_retry_stale_noop`, record remains `SEATED`, genuine event left to dispatch. TV242: genuine mismatched payload → cancel residual `rec.event_ref`, `RoundAbort(setup_retry_payload_integrity_failure)`, persist `ABORTED` + `target_disposition <- disp` by key, return `disp`; no `SEATED` record left. | Yes — TV241 traces to Check 3, TV242 to Check 4. |

All cross-references (round state machine §3.10f AB5, invariant I16 Stage-1AB clause, terminology `dispatched_event_ref` /
`setup_retry_payload_integrity_failure` entries, R202, and TV241/TV242) agree with the pseudocode source of truth. No
divergence found.

---

## Deliverable tree (Stage 1AB)

This audit (`STAGE_01AB_RETRY_DISPATCH_OWNERSHIP_AUDIT.md`) is deliverable 4 of the Stage-1AB set. The Stage-1AB
deliverable tree is:

1. `STAGE_01AB_CORRECTION_REPORT.md`
2. `STAGE_01AB_EXACT_ABORT_CONTRACT_AUDIT.md` (AB1/AB2)
3. `STAGE_01AB_RETRY_RECORD_PERSISTENCE_AUDIT.md` (AB3)
4. `STAGE_01AB_RETRY_DISPATCH_OWNERSHIP_AUDIT.md` (AB5) — this file
5. `STAGE_01AB_TERMINAL_CLOSURE_VISIBILITY_AUDIT.md` (AB4/AB6)
6. `STAGE_01AB_PROCEDURE_SIGNATURE_CALL_AUDIT.md`
7. `STAGE_01AB_PROCEDURE_CALL_GRAPH.md`
8. `STAGE_01AB_SEMANTIC_TEST_VECTORS.md` (TV236–TV243)
9. `STAGE_01AB_SUPERSESSION_REGISTER.md`
10. `STAGE_01AB_CROSS_DOCUMENT_AUDIT.md`
11. `STAGE_01AB_CHECKSUM_MANIFEST.sha256`

The five modified normative documents are `STAGE_01_PROTOCOL_PSEUDOCODE.md`, `STAGE_01_ROUND_STATE_MACHINE.md` (§3.10f),
`STAGE_01_INVARIANT_CATALOGUE.md` (I16 Stage-1AB clause), `STAGE_01_TERMINOLOGY.md` (Stage-1AB addendum), and
`STAGE_01_TRACEABILITY_MATRIX.csv` (rows R198–R205). The miner state machine is not touched. The Stage-1A–1AA lettered
artifacts are unchanged.

---

## Result

**PASS** — AB5 is faithfully specified. `SetupRetryEvent` carries a declared `dispatched_event_ref` INPUT with a documented
derivation (`STAGE_01_PROTOCOL_PSEUDOCODE.md:2011`, `:2017`, `:942`); the canonical guard order places the ownership check
(1c) after record resolution (1b) and before payload verification (2) (`:2023`, `:2033`–`2042`, NOTE `:2140`); Case B
returns `setup_retry_stale_noop` and mutates nothing, leaving the record `SEATED` for its genuine queued event (`:2037`–
`2041`); Case C, on the genuine event with a mismatched payload, cancels any residual still-pending event ref, captures
`disp <- CALL RoundAbort(reason = setup_retry_payload_integrity_failure(…))` first, persists `ABORTED` +
`target_disposition = disp` by key, and returns `disp` (`:2042`–`2053`); and both seating publishes set `rec.event_ref` to
the `ScheduleEvent`-returned reference so a genuine dispatch matches (`:1862`–`1866`, `:5231`–`5235`). The only event a
`SEATED` record owns is never consumed while the record remains `SEATED`. The pseudocode, round state machine §3.10f,
invariant I16 Stage-1AB clause, terminology, R202, and test vectors TV241/TV242 are mutually consistent. This is a
documentation-only audit of **PoCol** and the idle policy within PoCol; the A1 baseline `8.420833333 kWh` is preserved.
