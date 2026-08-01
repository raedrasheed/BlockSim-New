# Stage 1AA — Setup-Retry Terminalisation Audit (corrections AA2, AA3)

This audit verifies that corrections **AA2** (terminalise every SEATED setup-retry record at round closure)
and **AA3** (handle a stale `RoundID` through the record lifecycle) are executably realised in the frozen
source of truth `STAGE_01_PROTOCOL_PSEUDOCODE.md`. The algorithm is **PoCol**; the mechanism exercised here
is the idle policy within PoCol. All Stage-1AA artifacts preserve the A1 baseline (`8.420833333 kWh`);
nothing in AA2 or AA3 touches the energy model. This is a **documentation-only** audit — it reads the
pseudocode, the round state machine, and the companion Stage-1AA deliverables and edits none of them.

Every claim below is grounded with `file:line` citations into `STAGE_01_PROTOCOL_PSEUDOCODE.md`
(abbreviated **PC** below) and the round state machine `STAGE_01_ROUND_STATE_MACHINE.md`
(abbreviated **SM**), and quotes the operative current lines. Grep counts are reported inline.

Grep counts (`STAGE_01_PROTOCOL_PSEUDOCODE.md`):
`CancelSetupRetriesForRound` = **4**; `terminal_closure_pending` = **7**; `setup_retries_terminalised` = **2**;
`setup_retry_terminal_stale_noop` = **3**; `setup_retry_stale_noop` = **11**; `round_closed(disposition)` = **1**.

---

## 0. Declarations (data model and addenda)

- **`terminal_closure_pending` on the record — PC:836–838** (§0.8 Z1 data-model block, AA2 extension):
  > `# setup_retry_record = { SetupRetryID, setup_kind, RoundID, TemplateID_at_seat, TemplateRefreshSetupID, retry_generation,`
  > `#   event_ref, status : SetupRetryStatus, target_disposition, terminal_closure_pending } (terminal_closure_pending : bool,`
  > `#   default false, added AA2). setup_retry_records : map SetupRetryID -> setup_retry_record`

- **AA2 addendum — PC:888–894** (§0.8):
  > `# --- AA2 terminalise every SEATED retry record on round closure ---`
  > `# CancelSetupRetriesForRound(RoundContext, closing_RoundID, cancellation_reason, dispatch_or_run_hook_context) is the ONE`
  > `#   named terminaliser: for each setup_retry_record of closing_RoundID, a SEATED record has its event_ref cancelled (when`
  > `#   still queued) and becomes status = CANCELLED (target_disposition = cancellation_reason); an APPLYING record is NOT`
  > `#   overwritten (a terminal_closure_pending flag is set and the executing handler's captured target result finishes it as`
  > `#   ABORTED/CANCELLED). CloseRoundAssignments INVOKES it, and the round-closure event-cancellation list EXPLICITLY`
  > `#   includes SetupRetryEvent. No terminal or superseded round leaves a SEATED retry record.`

- **AA3 addendum — PC:895–898** (§0.8):
  > `# --- AA3 stale-RoundID handling through the record lifecycle ---`
  > `# SetupRetryEvent resolves setup_retry_records[SetupRetryID] and verifies the payload BEFORE the stale-RoundID check, so a`
  > `#   stale dispatch of a KNOWN SEATED record TERMINALISES it (status = CANCELLED or SUPERSEDED, target_disposition =`
  > `#   setup_retry_stale_noop) rather than leaving it SEATED. A malformed payload that matches no record may stale-noop.`

- **The record field defaults to `false` at BOTH seats.** The two seating procedures publish the record with
  `terminal_closure_pending = false` — **PC:1826–1827** (`PrepareParticipantsForNewRound`, `PARTICIPANT_SETUP`):
  > `retry_generation = g, event_ref = event_ref, status = SEATED, target_disposition = null,`
  > `terminal_closure_pending = false)   # Z1/AA2`

  and **PC:5144–5145** (`ContinueTemplateRefreshAssignmentSetup`, `TEMPLATE_REFRESH_SETUP`):
  > `retry_generation = g, event_ref = event_ref, status = SEATED, target_disposition = null,`
  > `terminal_closure_pending = false)   # Z1/AA2`

  `RunInitialise` initialises the single registry — **PC:1525**:
  > `INITIALISE setup_retry_records         <- empty map     # Z1: SetupRetryID -> setup_retry_record (the single retry registry)`

---

## 1. AA2 — terminalise every SEATED retry record at round closure

### 1.1 PASS — `CancelSetupRetriesForRound` is the one named terminaliser (body)

The procedure iterates every record of the closing round in a deterministic order and terminalises by status.

- **Signature + inputs — PC:2076–2079**:
  > `PROCEDURE CancelSetupRetriesForRound                            # AA2: terminalise every setup-retry record of a closing/superseded round`
  > `  INPUTS: RoundContext, closing_RoundID, cancellation_reason, dispatch_or_run_hook_context`

- **Precondition (the AA2 invariant it guarantees) — PC:2080–2081**:
  > `  PRECONDITIONS: called by CloseRoundAssignments for the round being closed (ROUND_ACCEPTED / ROUND_ABORTED), so no`
  > `                 terminal or superseded round leaves a SEATED setup-retry record (AA2).`

- **Deterministic iteration over the closing round's records — PC:2085**:
  > `    FOR EACH rec in SORT({ r in setup_retry_records : r.RoundID = closing_RoundID } BY SetupRetryID ascending):`

- **SEATED branch — cancel the still-queued event, then terminalise CANCELLED — PC:2086–2089**:
  > `      IF rec.status = SEATED:`
  > `        # cancel its still-queued dispatch, then TERMINALISE the record.`
  > `        IF rec.event_ref != null AND rec.event_ref is still pending on EQ: CANCEL rec.event_ref on EQ`
  > `        SET rec.status <- CANCELLED ; SET rec.target_disposition <- cancellation_reason           # AA2`

- **APPLYING branch — NOT overwritten; only the flag is set — PC:2090–2093**:
  > `      ELSE IF rec.status = APPLYING:`
  > `        # do NOT overwrite the executing handler's final classification; mark terminal-closure-pending and let the`
  > `        #   captured target result finish it as ABORTED / CANCELLED (the handler is mid-flight, SetupRetryEvent step 8).`
  > `        SET rec.terminal_closure_pending <- true                                                  # AA2`

- **Already-terminal records untouched — PC:2094**:
  > `      # APPLIED / SUPERSEDED / CANCELLED / ABORTED records are already terminal — left unchanged.`

- **Result + note — PC:2095–2101** returns `setup_retries_terminalised(closing_RoundID)` and restates the
  post-closure invariant ("After a round closes, NO setup-retry record of that round remains SEATED").

The body is exactly the AA2 contract: a SEATED record's queued `event_ref` is cancelled (only when still
pending on EQ) and the record becomes `CANCELLED` with `target_disposition = cancellation_reason`; an
APPLYING record is never overwritten — only `terminal_closure_pending` is raised, deferring the terminal
classification to the mid-flight handler.

### 1.2 PASS — `CloseRoundAssignments` invokes it AND lists `SetupRetryEvent` in the cancellation set

- **The event-cancellation list EXPLICITLY includes `SetupRetryEvent` — PC:4879–4881**:
  > `    CANCEL all pending wake / resume / certificate-arrival / BlockAcceptancePoint / HashWorkEvent /`
  > `           AdversarialParticipationChangeEvent / RecoveryDeadlineEvent / RecoveryCompletionDueEvent /`
  > `           RecoveryAssignmentContinuationDueEvent / RecoveryWorkDueEvent / SetupRetryEvent events for RoundID   # S4/T1/U1/AA2: recovery-timeline AND setup-retry events cancelled at closure`

- **The invocation — PC:4882–4886**:
  > `    # AA2: TERMINALISE every setup-retry record of this closing RoundID through the ONE named terminaliser — a SEATED`
  > `    #   record has its (now-cancelled) event_ref released and becomes CANCELLED; an APPLYING record is left for its`
  > `    #   executing handler to finish (ABORTED/CANCELLED). No terminal/superseded round leaves a SEATED retry record.`
  > `    CALL CancelSetupRetriesForRound(RoundContext, closing_RoundID = RoundID,`
  > `           cancellation_reason = round_closed(disposition), dispatch_or_run_hook_context = dispatch_envelope)   # AA2`

`CloseRoundAssignments` is documented as the ONLY round-closure path (PC:4903: "ValidBlockAccept calls it
with ROUND_ACCEPTED; RoundAbort calls it with ROUND_ABORTED"), so both terminal dispositions route through
the terminaliser. The cancellation of the queued `SetupRetryEvent` (PC:4881) precedes the record
terminalisation (PC:4885), so by the time `CancelSetupRetriesForRound` runs, a SEATED record's `event_ref`
is already off EQ — its guarded `CANCEL … on EQ` (PC:2088) is a no-op, and the status flip to `CANCELLED`
(PC:2089) is what removes the SEATED state.

### 1.3 PASS — `SetupRetryEvent` step 8 honours `terminal_closure_pending` (forces terminal, never APPLIED)

The step-8 classification checks the flag FIRST, so an APPLYING record whose round closed mid-flight can only
finish `ABORTED` or `CANCELLED` — never `APPLIED`.

- **PC:2046–2053**:
  > `    # Z1/AA2 CLASSIFY the captured result into the terminal status:`
  > `    SET rec.target_disposition <- disp`
  > `    IF rec.terminal_closure_pending = true:`
  > `      # AA2: the round CLOSED while this record was APPLYING (CancelSetupRetriesForRound flagged it); the record MUST finish`
  > `      #   terminal — NEVER APPLIED. A target round_aborted(abort_record) maps to ABORTED (AA1); any other captured`
  > `      #   disposition maps to CANCELLED.`
  > `      IF disp = round_aborted(abort_record): SET rec.status <- ABORTED`
  > `      ELSE:                                  SET rec.status <- CANCELLED`

Because the `terminal_closure_pending = true` branch (PC:2048) precedes the ordinary success branch
(PC:2054–2055, `disp = participant_set_prepared OR … committed TemplateID -> APPLIED`), a flagged record can
never reach the `APPLIED` write. The two flagged outcomes are exhaustive (`round_aborted(abort_record) ->
ABORTED`, everything else `-> CANCELLED`), so the record is always driven to a terminal status.

### 1.4 AA2 postcondition — no terminal/superseded round leaves a SEATED retry record

The postcondition holds by construction across the two structural exits from `SEATED`:

| Record status at closure | Path | Terminal outcome | Grounding |
|---|---|---|---|
| `SEATED` (queued dispatch not yet fired) | `CancelSetupRetriesForRound` SEATED branch | `event_ref` cancelled; `status = CANCELLED`, `target_disposition = round_closed(disposition)` | PC:2086–2089; PC:4885–4886 |
| `APPLYING` (handler mid-flight) | flag set at closure; classified by the handler's captured result | `terminal_closure_pending = true` then `ABORTED` (target `round_aborted`) or `CANCELLED` (otherwise) — never `APPLIED` | PC:2090–2093; PC:2048–2053 |
| `APPLIED`/`SUPERSEDED`/`CANCELLED`/`ABORTED` | already terminal | left unchanged | PC:2094 |

A SEATED record cannot survive closure: either its queued event is still pending (SEATED branch flips it to
CANCELLED) or the event already fired and advanced it out of SEATED (to APPLYING, handled by the flag; or to
a terminal status, left unchanged). The invariant statement is asserted at PC:2080–2081, PC:2099–2101, and
PC:894.

---

## 2. AA3 — stale `RoundID` handling through the record lifecycle

### 2.1 PASS — the canonical guard order (resolve + payload-match precede the stale check)

`SetupRetryEvent`'s guards run in the exact order AA3 requires. The order is stated at PC:1980–1984 and then
realised line-for-line:

| Step | Guard | Grounding | Behaviour |
|---|---|---|---|
| (1) | event shape | PC:1985–1987 | malformed envelope / structurally-invalid `SetupRetryID` -> `setup_retry_stale_noop` (no record to terminalise) |
| (1b) | RESOLVE `setup_retry_records[SetupRetryID]` | PC:1988–1991 | unknown/never-seated id -> `setup_retry_stale_noop` (nothing to terminalise) |
| (2) | payload match vs the immutable record | PC:1992–1996 | any field disagreement -> `setup_retry_stale_noop`, record LEFT for its correct dispatch (does not own it) |
| (3) | status-based idempotence | PC:1997–2000 | `rec.status != SEATED` -> `setup_retry_duplicate_suppressed` |
| (4) | stale-`RoundID` / closed-round TERMINALISATION | PC:2001–2009 | advanced round -> `SUPERSEDED`; closed round -> `CANCELLED` |
| (5) | kind-specific exact template identity | PC:2010–2021 | stale template -> `CANCELLED`, `setup_retry_stale_noop` |
| (6) | target round state (`ASSIGNMENT`) | PC:2022–2026 | non-`ASSIGNMENT` -> `ABORTED`, `RoundAbort` |
| (7) | budget + participant compatibility | PC:2027–2036 | over-budget / state-incompatible -> `ABORTED`, `RoundAbort` |
| (8) | `SEATED -> APPLYING` + capture + classify | PC:2037–2062 | first dispatch executes the target |

- **The order is declared — PC:1980–1984**:
  > `    # AA3/Z1 CANONICAL GUARD ORDER: (1) event shape; (1b) RESOLVE the record; (2) payload matches the immutable record;`
  > `    #   (3) STATUS-based EXACT-replay idempotence; (4) stale-RoundID / closed-round TERMINALISATION; (5) template identity;`
  > `    #   (6) target round state; (7) budget + participant compat; (8) SEATED -> APPLYING + capture + classify. AA3: the record`
  > `    #   is RESOLVED before the stale-RoundID check, so a stale dispatch of a KNOWN SEATED record TERMINALISES it (never`
  > `    #   leaves it SEATED); idempotence (3) still precedes the stale/terminal/target guards (Z1).`

- **Resolution (1b) — PC:1988–1991**:
  > `    # (1b) AA3 RESOLVE the ONE record. An unknown id (never seated) is a no-op.`
  > `    IF setup_retry_records[SetupRetryID] does NOT EXIST:`
  > `      RETURN setup_retry_stale_noop(SetupRetryID)          # never seated / unknown; nothing to terminalise`
  > `    SET rec <- setup_retry_records[SetupRetryID]`

- **Payload match (2) — PC:1992–1996**:
  > `    # (2) AA3 PAYLOAD MATCH. A payload whose fields disagree with the immutable record is a corrupted dispatch — no-op;`
  > `    #   the record is LEFT for its correct dispatch (a mismatched dispatch does not own — or terminalise — the record).`
  > `    IF NOT (RoundID = rec.RoundID AND setup_kind = rec.setup_kind AND TemplateID_at_seat = rec.TemplateID_at_seat`
  > `            AND TemplateRefreshSetupID = rec.TemplateRefreshSetupID AND retry_generation = rec.retry_generation):`
  > `      RETURN setup_retry_stale_noop(SetupRetryID)`

Steps (1b) and (2) are textually and structurally BEFORE the stale-`RoundID` check at (4) (PC:2001–2009).
This is the AA3 correction: the record is resolved and the payload verified against the immutable record
before any stale disposition is applied, so a stale dispatch of a KNOWN record can terminalise it.

### 2.2 PASS — a known SEATED record is terminalised SUPERSEDED / CANCELLED, never left SEATED

Because step (3) suppresses only NON-SEATED records (PC:1999), a genuinely-SEATED record falls through to the
stale-terminalisation check (4), which drives it to a terminal status:

- **PC:2001–2009**:
  > `    # (4) AA3 STALE-RoundID / CLOSED-ROUND TERMINALISATION. The record is KNOWN and SEATED; a stale dispatch must NOT`
  > `    #   leave it SEATED. Round advanced (RoundID moved on) -> SUPERSEDED; round terminal (closed) -> CANCELLED; either way`
  > `    #   target_disposition is the stale no-op and the event returns a stale no-op.`
  > `    IF RoundID != RoundID_current:`
  > `      SET rec.status <- SUPERSEDED ; SET rec.target_disposition <- setup_retry_stale_noop   # AA3: round advanced past r1`
  > `      RETURN setup_retry_stale_noop(SetupRetryID)`
  > `    IF round_state in {ROUND_ACCEPTED, ROUND_ABORTED}:`
  > `      SET rec.status <- CANCELLED ; SET rec.target_disposition <- setup_retry_terminal_stale_noop   # AA3: closed round`
  > `      RETURN setup_retry_terminal_stale_noop(SetupRetryID)`

| Stale condition | `rec.status` written | `rec.target_disposition` | returned disposition | Grounding |
|---|---|---|---|---|
| Round advanced (`RoundID != RoundID_current`) | `SUPERSEDED` | `setup_retry_stale_noop` | `setup_retry_stale_noop(SetupRetryID)` | PC:2004–2006 |
| Round terminal (`round_state ∈ {ROUND_ACCEPTED, ROUND_ABORTED}`) | `CANCELLED` | `setup_retry_terminal_stale_noop` | `setup_retry_terminal_stale_noop(SetupRetryID)` | PC:2007–2009 |

In both branches the record's `status` is overwritten away from `SEATED` before the handler returns — the
known record does NOT remain SEATED. The procedure NOTE restates this — **PC:2065–2068**:
> `  NOTE: AA1/AA3/Z1/Y1/Y2/Y3/X3/X4/W8: AA3 RESOLVES the record and verifies the payload BEFORE the stale-RoundID check, so a`
> `        stale dispatch of a KNOWN SEATED record TERMINALISES it (SUPERSEDED for an advanced round, CANCELLED for a closed`
> `        round) rather than leaving it SEATED; a malformed/mismatched payload stale-noops without terminalising a record it`
> `        cannot own.`

### 2.3 PASS — a malformed/mismatched payload stale-noops WITHOUT terminalising a record it cannot own

The two pre-stale no-op exits do NOT write any record status:

- **Unknown id (1b), PC:1989–1990** — returns `setup_retry_stale_noop` with no `SET rec.*` (there is no `rec`
  to write; the lookup missed).
- **Mismatched payload (2), PC:1994–1996** — returns `setup_retry_stale_noop` with no `SET rec.*`; the comment
  is explicit that "the record is LEFT for its correct dispatch (a mismatched dispatch does not own — or
  terminalise — the record)" (PC:1993). So a corrupted dispatch cannot terminalise a record it does not match,
  leaving the real (SEATED) record intact for its legitimate dispatch, which is what preserves AA3's
  own-the-record discipline.

The stale-terminalisation writes (PC:2005, PC:2008) are reachable ONLY after both (1b) resolution and (2)
payload match succeed, so terminalisation is confined to the record the dispatch genuinely owns.

---

## 3. Verification tables

### 3.1 AA2 checklist

| # | AA2 requirement | Grounding | Verdict |
|---|---|---|---|
| A2.1 | `CancelSetupRetriesForRound` exists with the 4-arg signature | PC:2076–2079 | PASS |
| A2.2 | SEATED record: cancel still-queued `event_ref`, set `CANCELLED` + `target_disposition = cancellation_reason` | PC:2086–2089 | PASS |
| A2.3 | APPLYING record: NOT overwritten; `terminal_closure_pending <- true` | PC:2090–2093 | PASS |
| A2.4 | Terminal records left unchanged; deterministic iteration | PC:2085, PC:2094 | PASS |
| A2.5 | `CloseRoundAssignments` INVOKES it (both dispositions) | PC:4885–4886 | PASS |
| A2.6 | Event-cancellation list EXPLICITLY includes `SetupRetryEvent` | PC:4879–4881 | PASS |
| A2.7 | `terminal_closure_pending : bool`, default false, on the record | PC:837–838; PC:1827; PC:5145 | PASS |
| A2.8 | Step-8 honours the flag: forces `ABORTED`/`CANCELLED`, never `APPLIED` | PC:2048–2053 | PASS |
| A2.9 | Postcondition: no terminal/superseded round leaves a SEATED record | PC:2080–2081; PC:2099–2101; PC:894 | PASS |

### 3.2 AA3 checklist

| # | AA3 requirement | Grounding | Verdict |
|---|---|---|---|
| A3.1 | Guard order (1) shape, (1b) resolve, (2) payload, (3) idempotence, (4) stale, (5) template, (6) round state, (7) budget+compat, (8) apply | PC:1980–1984; PC:1985–2062 | PASS |
| A3.2 | Resolution (1b) precedes the stale-`RoundID` check | PC:1988–1991 vs PC:2001–2009 | PASS |
| A3.3 | Payload match (2) precedes the stale-`RoundID` check | PC:1992–1996 vs PC:2001–2009 | PASS |
| A3.4 | Idempotence (3) suppresses only NON-SEATED, so SEATED reaches (4) | PC:1997–2000 | PASS |
| A3.5 | Advanced round -> `SUPERSEDED`, `target_disposition = setup_retry_stale_noop` | PC:2004–2006 | PASS |
| A3.6 | Closed round -> `CANCELLED`, `target_disposition = setup_retry_terminal_stale_noop` | PC:2007–2009 | PASS |
| A3.7 | A known SEATED record is NOT left SEATED after a stale dispatch | PC:2005, PC:2008; PC:2065–2068 | PASS |
| A3.8 | Malformed/mismatched payload stale-noops without terminalising a record it cannot own | PC:1989–1990; PC:1994–1996 | PASS |

### 3.3 Cross-document consistency

| Document | Location | Consistency check |
|---|---|---|
| Round SM §3.10e AA2 | SM:819–825 | Names `CancelSetupRetriesForRound` (4 args), SEATED -> `event_ref` cancel + `CANCELLED`, APPLYING -> `terminal_closure_pending` flag + handler finishes `ABORTED`/`CANCELLED`, `CloseRoundAssignments` invokes it, list includes `SetupRetryEvent`, "No terminal or superseded round leaves a SEATED retry record." Matches PC in substance. |
| Round SM §3.10e AA3 | SM:827–832 | RESOLVE + payload-match BEFORE the stale-`RoundID` check; known SEATED -> `SUPERSEDED`/`CANCELLED`; idempotence still precedes stale/terminal/target; malformed payload may stale-noop but a known SEATED record never remains SEATED. Matches PC in substance. |
| §0.8 addenda | PC:888–898 | AA2/AA3 prose identical in substance to the SM §3.10e clauses and to the procedure bodies. |

---

## 4. Test-vector linkage (TV228, TV229 — AA2; TV230, TV231 — AA3)

`STAGE_01AA_SEMANTIC_TEST_VECTORS.md` (abbreviated **TV** below) exercises AA2 and AA3 with four blocking
paper vectors; each names only procedures/dispositions that exist in the pseudocode, and every vector
preserves the A1 baseline `8.420833333 kWh` (TV:6).

- **TV228 — "Round closure cancels a SEATED retry record's queued event and sets CANCELLED (AA2)"**
  (TV:29–38). Drives `CloseRoundAssignments` on a round with a SEATED record + queued `SetupRetryEvent`;
  requires `SetupRetryEvent` in the cancellation set and the invocation of `CancelSetupRetriesForRound(…,
  cancellation_reason = round_closed(disposition), …)`, with the SEATED record cancelled and set
  `CANCELLED` / `target_disposition = round_closed(disposition)`, and "After closure NO setup-retry record of
  that round remains SEATED." Maps one-to-one onto §1.1–§1.2 (PC:2086–2089, PC:4879–4886). **Linkage holds.**

- **TV229 — "An APPLYING retry at closure is flagged and finishes terminal, never APPLIED (AA2)"**
  (TV:40–48). An APPLYING record at closure gets `terminal_closure_pending = true` (not overwritten); the
  mid-flight handler classifies `ABORTED` if the captured result is `round_aborted(abort_record)` else
  `CANCELLED`, "NEVER left APPLYING and NEVER classified APPLIED under a closed round." Maps onto §1.1
  (PC:2090–2093) and §1.3 (PC:2048–2053). **Linkage holds.**

- **TV230 — "A stale dispatch for an advanced round terminalises a known SEATED record as SUPERSEDED
  (AA3)"** (TV:50–58). A SEATED record for `r1` with `RoundID_current != r1` and a matching payload; requires
  resolution + payload-match BEFORE the stale check, no duplicate-suppression (status still SEATED), then
  `rec.status = SUPERSEDED` / `target_disposition = setup_retry_stale_noop` and return
  `setup_retry_stale_noop`; "The known record does NOT remain SEATED." Maps onto §2.1–§2.2 (PC:1988–1996,
  PC:2004–2006). **Linkage holds.**

- **TV231 — "A stale dispatch for a closed round terminalises a known SEATED record as CANCELLED (AA3)"**
  (TV:60–69). A SEATED record for the current `RoundID` with `round_state ∈ {ROUND_ACCEPTED, ROUND_ABORTED}`;
  after resolution + payload match + non-SEATED idempotence, the terminal-round branch sets `rec.status =
  CANCELLED` / `target_disposition = setup_retry_terminal_stale_noop` and returns
  `setup_retry_terminal_stale_noop`; the parenthetical records that "a malformed payload matching no record
  instead returns `setup_retry_stale_noop` without terminalising any record." Maps onto §2.2 (PC:2007–2009)
  and §2.3 (PC:1989–1996). **Linkage holds.**

The vector file's coverage table (TV:123–126) records TV228/TV229 under **AA2** against
`CloseRoundAssignments` / `CancelSetupRetriesForRound` / `SetupRetryEvent`, and TV230/TV231 under **AA3**
against `SetupRetryEvent` — consistent with the procedures audited above.

---

## 5. Result

**PASS (AA2).** `CancelSetupRetriesForRound` (PC:2076–2101) is the one named terminaliser: for each record of
the closing round it cancels a SEATED record's still-queued `event_ref` and sets it `CANCELLED`
(`target_disposition = cancellation_reason`), flags an APPLYING record `terminal_closure_pending = true`
without overwriting it, and leaves already-terminal records unchanged. `CloseRoundAssignments` invokes it for
both terminal dispositions (PC:4885–4886) and EXPLICITLY lists `SetupRetryEvent` in the round-closure
event-cancellation set (PC:4879–4881). The record carries `terminal_closure_pending : bool` (default false,
PC:837–838; PC:1827; PC:5145), and `SetupRetryEvent`'s step-8 classification checks the flag first and forces
`ABORTED`/`CANCELLED`, never `APPLIED` (PC:2048–2053). No terminal or superseded round leaves a SEATED retry
record.

**PASS (AA3).** `SetupRetryEvent` (PC:1970–2074) runs the canonical guard order — (1) shape, (1b) resolve,
(2) payload match, (3) status idempotence, (4) stale/terminal terminalisation, (5) template identity,
(6) round state, (7) budget+compat, (8) apply — with resolution (PC:1988–1991) and payload match
(PC:1992–1996) BEFORE the stale-`RoundID` check (PC:2001–2009). A known SEATED record dispatched stale is
terminalised `SUPERSEDED` (advanced round, PC:2004–2006) or `CANCELLED` (closed round, PC:2007–2009) rather
than left SEATED, while a malformed/mismatched payload stale-noops without touching a record it cannot own
(PC:1989–1996).

The pseudocode ↔ round-SM §3.10e (SM:805–832) ↔ §0.8 addenda (PC:888–898) chain is coherent, and
TV228/TV229/TV230/TV231 link one-to-one onto the audited procedures. This is a documentation-only audit; the
algorithm is **PoCol**, the mechanism is the idle policy within PoCol, and the A1 baseline `8.420833333 kWh`
is preserved.
