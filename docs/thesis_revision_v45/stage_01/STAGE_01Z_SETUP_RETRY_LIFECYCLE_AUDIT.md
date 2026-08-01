# Stage 1Z — Setup-Retry Status Lifecycle Audit (correction Z1)

This audit verifies that correction **Z1** completes the setup-retry status lifecycle in the frozen
source of truth `STAGE_01_PROTOCOL_PSEUDOCODE.md`. The algorithm is **PoCol**; the mechanism exercised
here is the idle policy within PoCol. All Stage-1Z artifacts preserve the A1 baseline
(`8.420833333 kWh`); nothing in Z1 touches the energy model. This is a documentation-only audit — it
reads the pseudocode and the companion Stage-1Z deliverables and edits none of them.

Every claim below is grounded with `file:line` citations into
`STAGE_01_PROTOCOL_PSEUDOCODE.md` (abbreviated **PC** below) and quotes the operative current lines.
Grep counts are reported inline.

---

## 0. The registry and the enumeration (declaration)

Z1 declares one record type and one registry.

- **PC:836–838** (§0.8 data-model block):
  > `# setup_retry_record = { SetupRetryID, setup_kind, RoundID, TemplateID_at_seat, TemplateRefreshSetupID, retry_generation,`
  > `#   event_ref, status : SetupRetryStatus, target_disposition }. setup_retry_records : map SetupRetryID -> setup_retry_record`
  > `#   is the SINGLE registry (it REPLACES the Y-era applied_setup_retry_ids mirror AND the bare setup_retry_status_by_id).`

- **PC:804** (enumeration):
  > `# SetupRetryStatus in { SEATED, APPLYING, APPLIED, SUPERSEDED, CANCELLED, ABORTED } (Y1). Its full lifecycle is owned by`

- **PC:1447–1454** (RunInitialise field declaration) confirms `setup_retry_records` is a per-run field,
  `SetupRetryID -> setup_retry_record`, and is the single registry replacing the Y-era pair.

Grep counts (`STAGE_01_PROTOCOL_PSEUDOCODE.md`):
`setup_retry_record` = **12**; `setup_retry_records` = **9**; `SetupRetryStatus` = **4**;
`setup_retry_duplicate_suppressed` = **2**.

---

## 1. PASS — every retained SetupRetryStatus has an executable producer

The six-member enumeration `{ SEATED, APPLYING, APPLIED, SUPERSEDED, CANCELLED, ABORTED }` (PC:804) is
covered by executable writes; no status is declared-but-unreachable.

| Status | Executable producer(s) | Grounding |
|---|---|---|
| **SEATED** | Both seating procedures publish the record atomically after a successful `ScheduleEvent`. | PC:1772–1774 (`PrepareParticipantsForNewRound`) and PC:5035–5037 (`ContinueTemplateRefreshAssignmentSetup`) |
| **APPLYING** | First valid dispatch of a SEATED record, before executing the target. | PC:1974 |
| **APPLIED** | Captured target result classified as success. | PC:1983–1984 |
| **SUPERSEDED** | Captured target result classified as a later-generation seat. | PC:1985–1986 |
| **ABORTED** | Captured result `round_aborted` (PC:1987–1988) plus guard-exit aborts (PC:1959, 1965, 1969). | PC:1959,1965,1969,1988 |
| **CANCELLED** | Captured stale disposition (PC:1989–1990) plus terminal/stale guard exits (PC:1943, 1949, 1955). | PC:1943,1949,1955,1990 |

**SEATED — at the seat.** Both seating procedures, on the `scheduled(event_ref)` branch, atomically
publish the record with `status = SEATED`:

- **PC:1770–1774** (`PrepareParticipantsForNewRound`, `PARTICIPANT_SETUP`):
  > `IF r = scheduled(event_ref):`
  > `  # Z1: publish the setup_retry_record ATOMICALLY with status = SEATED AFTER the successful ScheduleEvent.`
  > `  ATOMICALLY: SET setup_retry_records[srid] <- setup_retry_record(SetupRetryID = srid, setup_kind = PARTICIPANT_SETUP,`
  > `        ... status = SEATED, target_disposition = null)   # Z1`

- **PC:5033–5037** (`ContinueTemplateRefreshAssignmentSetup`, `TEMPLATE_REFRESH_SETUP`):
  > `IF r = scheduled(event_ref):`
  > `  # Z1: publish the setup_retry_record ATOMICALLY with status = SEATED AFTER the successful ScheduleEvent.`
  > `  ATOMICALLY: SET setup_retry_records[srid] <- setup_retry_record(SetupRetryID = srid, setup_kind = TEMPLATE_REFRESH_SETUP,`
  > `        ... status = SEATED, target_disposition = null)   # Z1`

**APPLYING — at first dispatch.** After all guards pass, step (7) atomically flips the record to
APPLYING before running the target:

- **PC:1972–1974**:
  > `# (7) Z1 FIRST DISPATCH: atomically transition SEATED -> APPLYING, CAPTURE the target result (no direct RETURN CALL),`
  > `#   then set the terminal status deterministically from that result.`
  > `ATOMICALLY: SET rec.status <- APPLYING       # Z1: the SEATED record is now being applied`

**APPLIED / SUPERSEDED / ABORTED / CANCELLED — from the captured result.** After capture, step (7)
classifies the disposition into exactly one terminal status:

- **PC:1982–1990**:
  > `SET rec.target_disposition <- disp`
  > `IF disp = participant_set_prepared OR disp is a committed TemplateID value:`
  > `  SET rec.status <- APPLIED                 # Z1: setup succeeded (round now HASHING)`
  > `ELSE IF disp = participant_set_setup_retry_seated(...) OR disp = template_refresh_retry_seated(...):`
  > `  SET rec.status <- SUPERSEDED              # Z1: a later generation was seated by the target`
  > `ELSE IF disp = round_aborted:`
  > `  SET rec.status <- ABORTED                 # Z1: the target aborted the round`
  > `ELSE:   # disp = template_refresh_retry_stale_noop or another declared stale disposition`
  > `  SET rec.status <- CANCELLED               # Z1: a declared stale cancellation`

**ABORTED / CANCELLED — from guard exits.** The pre-target guards also drive the record to a terminal
status before returning, so no guard exit leaves a record stuck at SEATED/APPLYING:

- Terminal round → CANCELLED — **PC:1943**:
  > `SET rec.status <- CANCELLED ; SET rec.target_disposition <- setup_retry_terminal_stale_noop   # Z1`
- Stale template identity (both kinds) → CANCELLED — **PC:1949** and **PC:1955**:
  > `SET rec.status <- CANCELLED ; SET rec.target_disposition <- setup_retry_stale_noop   # Z1`
- Wrong round state → ABORTED — **PC:1959**:
  > `SET rec.status <- ABORTED ; SET rec.target_disposition <- round_aborted   # Z1`
- Over-budget → ABORTED — **PC:1965**; state-incompatible → ABORTED — **PC:1969** (same shape).

**Result: PASS.** Each of the six retained statuses has at least one reachable, executable write; SEATED
and APPLYING have unique structural producers (seat; first dispatch), and the four terminals are produced
both from the captured target result and from the pre-target guard exits.

---

## 2. PASS — a SEATED retry's first dispatch is NOT duplicate-suppressed (status-based guard)

The idempotence guard (step 2) reads the record's **status**, not its mere presence, and suppresses only
non-SEATED statuses.

- **PC:1936–1940**:
  > `IF setup_retry_records[SetupRetryID] does NOT EXIST:`
  > `  RETURN setup_retry_stale_noop(SetupRetryID)          # never seated (defensive; the seat publishes SEATED)`
  > `SET rec <- setup_retry_records[SetupRetryID]`
  > `IF rec.status != SEATED:`
  > `  RETURN setup_retry_duplicate_suppressed(SetupRetryID)   # Z1: replay of an APPLYING/APPLIED/SUPERSEDED/CANCELLED/ABORTED record`

The guard's own annotation makes the requirement explicit — **PC:1932–1935**:
> `# (2) Z1 STATUS-BASED EXACT-REPLAY IDEMPOTENCE. Look up the ONE record (published SEATED by the seating procedure).`
> `#   A SEATED record is the FIRST valid dispatch and MUST execute (do NOT suppress it). Any NON-SEATED status`
> `#   ... Testing PRESENCE`
> `#   would wrongly suppress the first legitimate dispatch of a published SEATED record (Z1).`

Because the seat publishes `status = SEATED` (§1), the first dispatch reads `rec.status = SEATED`, the
`rec.status != SEATED` test is false, and control falls through to steps (3)–(7) and executes. A replay
after the record has advanced to `APPLYING`/`APPLIED`/`SUPERSEDED`/`CANCELLED`/`ABORTED` matches
`rec.status != SEATED` and returns `setup_retry_duplicate_suppressed`. The procedure NOTE restates this —
**PC:1994–1996**:
> `... A published SEATED record's FIRST dispatch is NEVER duplicate-suppressed — only a record`
> `already APPLYING/APPLIED/SUPERSEDED/CANCELLED/ABORTED is (Z1).`

Note the guard ordering is deliberate: idempotence (2) precedes the terminal check (3) and the
wrong-state abort (5) (**PC:1924–1928**), so a replay of a retry that already succeeded and moved the
round forward is duplicate-suppressed and never re-enters `RoundAbort`.

**Result: PASS.** The first dispatch of a SEATED retry executes; suppression is keyed on non-SEATED
status, never on presence.

---

## 3. PASS — target results update the record deterministically (capture-then-classify)

Step (7) captures the target result into a local (`disp`) rather than tail-returning the call, then
classifies deterministically, then returns the captured value.

- **PC:1975–1980** (capture, both kinds):
  > `IF setup_kind = PARTICIPANT_SETUP:`
  > `  SET disp <- CALL PrepareParticipantsForNewRound(RoundContext, dispatch_envelope)          # X4: re-run participant setup`
  > `ELSE:   # setup_kind = TEMPLATE_REFRESH_SETUP: ...`
  > `  SET disp <- CALL ContinueTemplateRefreshAssignmentSetup(RoundContext, dispatch_envelope, TemplateID = TemplateID_at_seat,`
  > `                   TemplateRefreshSetupID = TemplateRefreshSetupID,`
  > `                   SetupRetryID = SetupRetryID, retry_generation = retry_generation)   # X3/X4/Y2/Y3`

- **PC:1981–1991** (classify, then return the captured disposition) — quoted in §1 — records the
  disposition into `rec.target_disposition` (PC:1982), sets exactly one terminal status, and ends with
  `RETURN disp` (PC:1991).

There is no `RETURN CALL <target>` in this handler: the target is always bound to `disp` first
(PC:1976, PC:1978), the record is updated from `disp`, and only then does the handler return. This is
the "capture-then-classify (no direct RETURN CALL)" contract stated at PC:1972 and reiterated in the
NOTE at PC:1996–1999. Consequently `rec.status` and `rec.target_disposition` are always a deterministic
function of the observed target result — the record can never be left mid-flight after the target has
returned.

**Result: PASS.** The record is updated by capture-then-classify; the terminal status and
`target_disposition` are deterministic functions of the captured disposition.

---

## 4. PASS — the Y-era mirror is removed and "applied" is defined precisely

**Old identifiers withdrawn from live code.** Grep counts (`STAGE_01_PROTOCOL_PSEUDOCODE.md`):

- `applied_setup_retry_ids` = **4** — all at PC:806, PC:838, PC:1450, PC:1999.
- `setup_retry_status_by_id` = **3** — all at PC:805, PC:838, PC:1450.

Every one of these mentions is a Z-comment explaining the removal/supersession, not a live declaration,
initialisation, read, or write. A targeted search for any executable producer/writer of the old
identifiers
(`INITIALISE|SET` against `applied_setup_retry_ids`/`setup_retry_status_by_id`) returns **none**.
Representative comments:

- **PC:838**:
  > `#   is the SINGLE registry (it REPLACES the Y-era applied_setup_retry_ids mirror AND the bare setup_retry_status_by_id).`
- **PC:1450** (RunInitialise field note):
  > `... REPLACES the Y-era applied_setup_retry_ids mirror AND the bare setup_retry_status_by_id). ...`
- **PC:1999** (SetupRetryEvent NOTE):
  > `... the redundant applied_setup_retry_ids mirror is REMOVED.`

**RunInitialise initialises the new registry, not the old identifiers.** — **PC:1477**:
> `INITIALISE setup_retry_records         <- empty map     # Z1: SetupRetryID -> setup_retry_record (the single retry registry)`

and threads it into the returned `RunContext` (**PC:1484**). No `INITIALISE applied_setup_retry_ids` or
`INITIALISE setup_retry_status_by_id` exists.

**"applied" defined precisely.** "applied" is defined as `status = APPLIED`, set only after the target
result is known:

- **PC:846** (§0.8):
  > `#   "applied" is DEFINED as status = APPLIED and is set ONLY after the target result is known.`
- **PC:1998–1999** (SetupRetryEvent NOTE):
  > `... "applied" is DEFINED as status =`
  > `APPLIED and is set ONLY after the target result is known; the redundant applied_setup_retry_ids mirror is REMOVED.`

This is structurally enforced: `APPLIED` is written only at PC:1984, which is downstream of the capture
at PC:1976/1978 — no id is ever added to an "applied" set before the target's disposition is observed.
The failure mode Z1 closes (an id promoted to "applied" before the result is known, or a presence-based
guard suppressing a legitimate first dispatch) is therefore unreachable.

**Result: PASS.** The Y-era mirror `applied_setup_retry_ids` and the bare `setup_retry_status_by_id` are
withdrawn from live code (remaining mentions are Z-comments only); `RunInitialise` initialises
`setup_retry_records`; "applied" ≡ `status = APPLIED`, set only after the captured result.

---

## 5. Test-vector linkage (TV219, TV220)

`STAGE_01Z_SEMANTIC_TEST_VECTORS.md` (abbreviated **TV** below) exercises Z1 with two blocking paper
vectors; both name only procedures/dispositions that exist in the pseudocode and both preserve the A1
baseline `8.420833333 kWh` (TV:6).

- **TV219 — "A SEATED retry's first dispatch executes and is not a duplicate (Z1)"** (TV:17–26). It
  drives the seat (publishing `setup_retry_records[srid]` with `status = SEATED`) and the first fire, and
  requires the status-based guard to read `rec.status = SEATED`, NOT suppress, and atomically flip
  `SEATED -> APPLYING` and execute — with the explicit note that "a presence-only guard would have
  wrongly suppressed it." This is exactly the behaviour grounded in §2 (PC:1932–1940) and the SEATED
  producers in §1 (PC:1774, PC:5037). **Linkage holds.**

- **TV220 — "Target results drive the record deterministically; a replay is suppressed (Z1)"**
  (TV:28–37). Setup A (success) requires `rec.status = APPLIED` and a subsequent replay to return
  `setup_retry_duplicate_suppressed` with no re-run and no `RoundAbort`; Setup B (later generation)
  requires `SUPERSEDED`; Setup C (abort) requires `ABORTED`; in all cases `rec.target_disposition`
  records the captured disposition. This maps one-to-one onto the capture-then-classify block in §3
  (PC:1982–1991) and the non-SEATED suppression in §2 (PC:1939–1940). **Linkage holds.**

The vector file's coverage table (TV:101–103) records TV219/TV220 under correction **Z1** against the
seating procedure and `SetupRetryEvent` — consistent with the producers audited above.

---

## 6. Cross-document consistency

The Z1 statement is identical in substance across the five companion artifacts and the pseudocode.

| Document | Location | Consistency check |
|---|---|---|
| Pseudocode | PC:804, 836–838, 1447–1454, 1770–1774, 1932–1999, 5033–5037 | Registry, enum, SEATED at seat, status-guard, capture-then-classify, terminals — all present. |
| Round state machine §3.10d Z1 | `STAGE_01_ROUND_STATE_MACHINE.md:773–779` | "single registry", seat publishes SEATED, first dispatch flips `SEATED -> APPLYING` and EXECUTES ("a SEATED record is NEVER duplicate-suppressed"), captured result → `APPLIED`/`SUPERSEDED`/`ABORTED`/`CANCELLED`, replay suppressed IFF non-SEATED, Y-era pair withdrawn, "applied" = `status = APPLIED`. Matches PC verbatim in substance. |
| Invariant catalogue I16 (Stage-1Z clause) | `STAGE_01_INVARIANT_CATALOGUE.md:363–367` | Same lifecycle statement under the I16 Stage-1Z clause; "a SEATED record is never duplicate-suppressed"; Y-era mirror "withdrawn". Consistent. |
| Terminology | `STAGE_01_TERMINOLOGY.md:942–949` | `setup_retry_record` / `setup_retry_records` entry gives the exact field set, "SINGLE setup-retry registry, replacing the Y-era `applied_setup_retry_ids` and `setup_retry_status_by_id`", the seat→first-dispatch→captured-terminal lifecycle, non-SEATED suppression, and "applied" ≡ `status = APPLIED`. Consistent. |
| Traceability matrix R184 | `STAGE_01_TRACEABILITY_MATRIX.csv:185` | Requirement text restates Z1 field-for-field; owning procedures `SetupRetryEvent; PrepareParticipantsForNewRound; ContinueTemplateRefreshAssignmentSetup; RunInitialise`; invariants `I16; I18b`; negative case "a SEATED retry whose first dispatch is duplicate-suppressed because presence not status was tested or an id added to applied before the target result is known"; status `SPECIFIED`. Consistent with the procedures audited above. |

The chain pseudocode ↔ round-SM §3.10d Z1 ↔ invariant I16 (Stage-1Z) ↔ terminology ↔ R184 is coherent:
one registry, one record per `SetupRetryID`, a status-based guard, a capture-then-classify terminal
assignment, the removed Y-era mirror, and a precise definition of "applied". No document contradicts
another, and no document references a live `applied_setup_retry_ids` / `setup_retry_status_by_id`.

---

## 7. Result

**PASS** — Z1 completes the setup-retry status lifecycle: every retained `SetupRetryStatus` has an
executable producer, a SEATED retry's first dispatch executes under a status-based (not presence-based)
guard, target results update the single `setup_retry_records` registry deterministically via
capture-then-classify, the Y-era `applied_setup_retry_ids` / `setup_retry_status_by_id` mirror is
removed from live code, and "applied" ≡ `status = APPLIED` set only after the target result is known;
TV219/TV220 and the round-SM §3.10d / I16 / terminology / R184 chain are consistent, with the A1
baseline `8.420833333 kWh` preserved.
