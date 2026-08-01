# Stage 1Y — Setup-Retry Replay Audit (Y1: idempotence before the mutating guards)

This audit verifies that correction **Y1** is fully realised in the Stage-1 formal specification of **PoCol** and the
idle policy within PoCol. Y1 reorders `SetupRetryEvent` so EXACT-replay idempotence is checked BEFORE the mutating
(terminal / wrong-round-state) guards, guaranteeing that a replay of a retry that already succeeded and moved the round
forward (e.g. to `HASHING`) is duplicate-suppressed and NEVER aborts the round.

This is a documentation-only audit. It reads, and does not modify, the source of truth
(`STAGE_01_PROTOCOL_PSEUDOCODE.md`) or any companion document. No executable source is touched, no experiment is run,
and the A1 baseline `8.420833333 kWh` is unchanged.

## Source of truth

- `STAGE_01_PROTOCOL_PSEUDOCODE.md:1835` — `PROCEDURE SetupRetryEvent` (tag line `# W8/X4/Y1/Y2/Y3: a bounded,
  idempotent, state-compatible retry of a rolled-back setup`). The procedure body runs `1835`–`1904`.
- `STAGE_01_PROTOCOL_PSEUDOCODE.md:804` — the `SetupRetryStatus` enum declaration in §0.8 (Core data model).
- `STAGE_01_PROTOCOL_PSEUDOCODE.md:1389`–`1393`, `1416`–`1423` — the `RunContext` / `RunInitialise` ownership of
  `applied_setup_retry_ids` and `setup_retry_status_by_id` in §1.0 (Run initialisation, Q5).

The canonical Y1 guard order is stated as an EFFECTS preamble at `STAGE_01_PROTOCOL_PSEUDOCODE.md:1845`–`1848`:

```
    # Y1 CANONICAL GUARD ORDER: (1) event shape + RoundID identity; (2) EXACT-replay idempotence; (3) terminal; (4)
    #   kind-specific template identity; (5) target round state; (6) budget + participant compatibility; (7) mark + invoke.
    #   Idempotence (2) precedes the terminal check (3) AND the wrong-state abort (5), so a replay of a retry that already
    #   succeeded and moved the round to HASHING is duplicate-suppressed — it NEVER calls RoundAbort for a forward round.
```

The executable gates that follow this preamble realise exactly that order:

| Gate | Purpose | Lines | Disposition on hit |
|------|---------|-------|--------------------|
| (1) | event shape + `RoundID` identity | `1849`–`1851` | `setup_retry_stale_noop` |
| (2) | **EXACT-replay idempotence (Y1)** | `1852`–`1855` | `setup_retry_duplicate_suppressed` |
| (3) | terminal (`ROUND_ACCEPTED`/`ROUND_ABORTED`) | `1856`–`1858` | `setup_retry_terminal_stale_noop` |
| (4) | kind-specific exact template identity (Y2) | `1859`–`1868` | `setup_retry_stale_noop` |
| (5) | target round state (`!= ASSIGNMENT`) | `1869`–`1872` | `RoundAbort` |
| (6) | budget + participant compatibility | `1873`–`1880` | `RoundAbort` |
| (7) | atomically mark `APPLYING`, then invoke target | `1881`–`1891` | target disposition |

## PASS checks

### (1) Idempotence is checked BEFORE the terminal check — PASS

The idempotence gate (2) appears in the source at `STAGE_01_PROTOCOL_PSEUDOCODE.md:1852`–`1855`:

```
    # (2) Y1 EXACT-REPLAY IDEMPOTENCE — BEFORE the terminal and wrong-state guards. A SetupRetryID already SEATED/APPLYING/
    #   APPLIED/SUPERSEDED (i.e., recorded) runs the setup at most ONCE; a post-success replay is suppressed, never aborted.
    IF SetupRetryID in applied_setup_retry_ids OR SetupRetryID in setup_retry_status_by_id:
      RETURN setup_retry_duplicate_suppressed(SetupRetryID)   # Y1: precedes every wrong-state abort (gate 1/2)
```

The terminal gate (3) appears strictly LATER, at `STAGE_01_PROTOCOL_PSEUDOCODE.md:1856`–`1858`:

```
    # (3) TERMINAL. Already accepted/aborted: nothing to retry, no controller needed.
    IF round_state in {ROUND_ACCEPTED, ROUND_ABORTED}:
      RETURN setup_retry_terminal_stale_noop(SetupRetryID)   # X4
```

Gate (2) at line `1854` textually and executionally precedes gate (3) at line `1857`. Because gate (2) `RETURN`s on a
recorded `SetupRetryID`, control never falls through to the terminal check for a replayed retry. **PASS.**

### (2) Idempotence is checked BEFORE the wrong-round-state `RoundAbort` — PASS

The only wrong-round-state `RoundAbort` in this procedure is gate (5), at `STAGE_01_PROTOCOL_PSEUDOCODE.md:1869`–`1872`:

```
    # (5) X4 TARGET ROUND STATE. BOTH targets require ASSIGNMENT; a non-terminal non-ASSIGNMENT dispatch is a declared abort.
    IF round_state != ASSIGNMENT:
      RETURN CALL RoundAbort(RoundContext, reason = setup_retry_wrong_round_state(setup_kind, round_state),
                             dispatch_envelope = dispatch_envelope, recovery_finalising = false)   # X4
```

The idempotence gate (2) at line `1854` precedes gate (5) at line `1870` by construction. A replayed retry `RETURN`s
`setup_retry_duplicate_suppressed` at line `1855` and never reaches the `round_state != ASSIGNMENT` test. The budget /
participant-compatibility `RoundAbort`s of gate (6) (`1873`–`1880`) are likewise downstream of gate (2) and therefore
also unreachable on a replay. **PASS.**

### (3) A post-`HASHING` replay returns `setup_retry_duplicate_suppressed` with no `RoundAbort` — PASS

Trace the key required behaviour: a retry that already succeeded ran gate (7) (`1881`–`1891`), which added its
`SetupRetryID` to `applied_setup_retry_ids` and set `setup_retry_status_by_id[SetupRetryID] <- APPLYING`, then invoked
its target; the target completed and drove `ASSIGNMENT -> HASHING` (via `CompleteAssignmentPhase` /
`TransitionRoundState`, `STAGE_01_PROTOCOL_PSEUDOCODE.md:1964`–`1966`). On the EXACT-same-`SetupRetryID` re-dispatch
while `round_state = HASHING`:

- Gate (1) (`1849`–`1851`) passes — `RoundID` is still current, the envelope is complete — so no stale no-op.
- Gate (2) (`1854`) finds the `SetupRetryID` recorded (in `applied_setup_retry_ids`, and with status `APPLYING`/`APPLIED`
  in `setup_retry_status_by_id`) and `RETURN`s `setup_retry_duplicate_suppressed(SetupRetryID)` at `1855`.
- Gate (5)'s `round_state != ASSIGNMENT` test (`1870`), which WOULD `RoundAbort` for the forward `HASHING` round, is
  never reached.

The EFFECTS preamble at `1847`–`1848` and the closing NOTE at `1894`–`1896` both assert precisely this outcome. No
`RoundAbort` occurs for the forward round. **PASS.**

### (4) `SetupRetryStatus` is defined and `APPLYING` is marked atomically BEFORE invoking the target — PASS

The enum is declared in §0.8 at `STAGE_01_PROTOCOL_PSEUDOCODE.md:804`:

```
  # SetupRetryStatus in { SEATED, APPLYING, APPLIED, SUPERSEDED, CANCELLED, ABORTED } (Y1). setup_retry_status_by_id :
```

The `RunContext` field carrying it, and its per-run initialisation, are declared in §1.0:

- `STAGE_01_PROTOCOL_PSEUDOCODE.md:1391`–`1393` — `setup_retry_status_by_id : Y1 — map SetupRetryID -> SetupRetryStatus
  in { SEATED, APPLYING, APPLIED, SUPERSEDED, CANCELLED, ABORTED }. Owned by SetupRetryEvent; a SetupRetryID recorded
  here (any status) is duplicate-suppressed on replay BEFORE any wrong-state abort (Y1).`
- `STAGE_01_PROTOCOL_PSEUDOCODE.md:1416`–`1417` — `INITIALISE applied_setup_retry_ids <- empty set` /
  `INITIALISE setup_retry_status_by_id <- empty map # Y1`.
- `STAGE_01_PROTOCOL_PSEUDOCODE.md:1423` — both fields are returned in the `RunContext` (`... applied_setup_retry_ids,
  setup_retry_status_by_id, maximum_setup_retries) # W8/Y1`).

The APPLYING marking is performed atomically in gate (7), BEFORE either target is invoked, at
`STAGE_01_PROTOCOL_PSEUDOCODE.md:1881`–`1891`:

```
    # (7) Y1 ATOMICALLY mark APPLYING (register the idempotent marker BEFORE re-invoking) then invoke the kind-specific target.
    ATOMICALLY:
      ADD SetupRetryID to applied_setup_retry_ids
      SET setup_retry_status_by_id[SetupRetryID] <- APPLYING
    IF setup_kind = PARTICIPANT_SETUP:
      RETURN CALL PrepareParticipantsForNewRound(RoundContext, dispatch_envelope)          # X4: re-run participant setup
    ...
    RETURN CALL ContinueTemplateRefreshAssignmentSetup(RoundContext, dispatch_envelope, TemplateID = TemplateID_at_seat,
                     TemplateRefreshSetupID = TemplateRefreshSetupID,
                     SetupRetryID = SetupRetryID, retry_generation = retry_generation)   # X3/X4/Y2/Y3
```

The `ATOMICALLY` block (`1882`–`1884`) records the idempotent marker before the target `CALL`s at `1886` /
`1889`–`1891`, so an in-flight re-dispatch that arrives while the target is running (or after it advanced the round)
sees a recorded `SetupRetryID` at gate (2) and is suppressed. The enum, its owner, and the atomic ordering are all
present. **PASS.**

### (5) The `RETURNS` union and the closing `NOTE` reflect the reorder — PASS

The `RETURNS` union enumerates the duplicate disposition alongside the stale/terminal/abort dispositions, at
`STAGE_01_PROTOCOL_PSEUDOCODE.md:1892`–`1893`:

```
  RETURNS: setup_retry_stale_noop | setup_retry_terminal_stale_noop | setup_retry_duplicate_suppressed | round_aborted |
           (the re-run target procedure's disposition)
```

The closing `NOTE` restates the canonical order and the forward-round guarantee, at
`STAGE_01_PROTOCOL_PSEUDOCODE.md:1894`–`1896`:

```
  NOTE: Y1/Y2/Y3/X3/X4/W8: the CANONICAL guard order checks EXACT-replay idempotence (2) BEFORE the terminal (3) and the
        wrong-state abort (5), so a replay of a retry that already succeeded and moved the round forward (e.g. to HASHING)
        returns setup_retry_duplicate_suppressed and NEVER RoundAbort (gates 1/2).
```

`setup_retry_duplicate_suppressed` is a first-class member of the `RETURNS` union, and the `NOTE` names the reorder
(idempotence (2) before terminal (3) and wrong-state abort (5)) and the "never `RoundAbort` for a forward round"
consequence. **PASS.**

## Test-vector linkage

Row **R183** of `STAGE_01_TRACEABILITY_MATRIX.csv:184` registers the blocking test vectors for the retry-identity and
rollback-closure lock (Y1–Y5) and names the two vectors that exercise Y1 replay in `STAGE_01Y_SEMANTIC_TEST_VECTORS.md`:

- **TV210** (`STAGE_01Y_SEMANTIC_TEST_VECTORS.md:18`–`27`) — "Replay after a successful HASHING transition is
  duplicate-suppressed, never aborted (Y1)." A seated `SetupRetryEvent` fires, is marked `APPLYING`, runs its target,
  and the target succeeds — the round transitions to `HASHING`. The EXACT-same `SetupRetryID` is re-dispatched while
  `round_state = HASHING`. Expected: gate (1) passes (`RoundID` still current), gate (2) finds the `SetupRetryID`
  recorded and returns `setup_retry_duplicate_suppressed`; the wrong-round-state guard (gate 5) is NEVER reached and no
  `RoundAbort` occurs. This is exactly PASS checks (1)–(3) above.
- **TV218** (`STAGE_01Y_SEMANTIC_TEST_VECTORS.md:103`–`113`) — "TemplateRefreshSetupID replay after a completed
  assignment setup is suppressed (Y1/Y2)." A `TEMPLATE_REFRESH_SETUP` retry whose `SetupRetryID` already ran to a
  successful assignment setup is re-dispatched; the Y1 idempotence guard returns `setup_retry_duplicate_suppressed`, no
  target runs again, and (via the `template_refresh_setup_committed[TemplateID]` marker) no old-template closure /
  candidate-template construction / `TemplateCommit` is repeated. This confirms the idempotence gate governs the
  `TEMPLATE_REFRESH_SETUP` target (`ContinueTemplateRefreshAssignmentSetup`) as well as `PARTICIPANT_SETUP`.

Both vectors are specified against the exact current procedures and dispositions in `STAGE_01_PROTOCOL_PSEUDOCODE.md`;
neither assumes an unwritten guard or result name; both preserve the A1 baseline `8.420833333 kWh`
(`STAGE_01Y_SEMANTIC_TEST_VECTORS.md:131`–`133`).

## Cross-document consistency

The Y1 statement is identical across the source of truth and every companion, and is traced by row **R178**:

- **Pseudocode** — `STAGE_01_PROTOCOL_PSEUDOCODE.md:1845`–`1848` (guard-order preamble), `1852`–`1855` (gate 2),
  `1894`–`1896` (closing NOTE): idempotence (2) before terminal (3) and wrong-state abort (5); post-`HASHING` replay →
  `setup_retry_duplicate_suppressed`, never `RoundAbort`.
- **Round state machine §3.10c Y1** — `STAGE_01_ROUND_STATE_MACHINE.md:728` (addendum header), `735`–`739` (Y1 block):
  "`SetupRetryEvent` checks EXACT-replay idempotence ... BEFORE the terminal check and BEFORE the wrong-round-state
  abort. A replay of a retry that already succeeded and moved the round to `HASHING` returns
  `setup_retry_duplicate_suppressed` — it NEVER calls `RoundAbort` ... `SetupRetryStatus` ∈ { `SEATED`, `APPLYING`,
  `APPLIED`, `SUPERSEDED`, `CANCELLED`, `ABORTED` }."
- **Invariant I16 Stage-1Y clause** — `STAGE_01_INVARIANT_CATALOGUE.md:347` (Stage-1Y clause header), `348`–`350` (Y1):
  idempotence checked before the terminal check and the wrong-round-state abort, so a post-`HASHING` replay returns
  `setup_retry_duplicate_suppressed` and NEVER aborts the round.
- **Terminology addendum** — `STAGE_01_TERMINOLOGY.md:906` (addendum header), `908`–`912` (`SetupRetryStatus` (Y1)):
  the enum `{ SEATED, APPLYING, APPLIED, SUPERSEDED, CANCELLED, ABORTED }` recorded per `SetupRetryID` in
  `setup_retry_status_by_id`, with idempotence before the terminal check and the wrong-round-state abort.
- **Traceability R178** — `STAGE_01_TRACEABILITY_MATRIX.csv:179`: "Reorder setup-retry idempotence before mutating
  guards (Y1); `SetupRetryEvent` checks EXACT-replay idempotence ... BEFORE the terminal check and BEFORE the
  wrong-round-state abort; ... returns `setup_retry_duplicate_suppressed` and NEVER calls `RoundAbort` for a forward
  round; `SetupRetryStatus` in {SEATED APPLYING APPLIED SUPERSEDED CANCELLED ABORTED} is marked `APPLYING` atomically
  before the target is invoked", mapped to invariants I16;I18b.

**Consistency line:** pseudocode (`1845`–`1855`, `1881`–`1896`) ↔ round-SM §3.10c Y1 (`735`–`739`) ↔ invariant I16
Stage-1Y Y1 (`348`–`350`) ↔ terminology `SetupRetryStatus` (Y1) (`908`–`912`) ↔ traceability R178 (`179`) all state the
same guard order, the same enum, the same atomic-`APPLYING` marking, and the same forward-round guarantee — no drift.

## Final Stage-1Y deliverable tree

`/home/user/blocksim-v45-stage1y/docs/thesis_revision_v45/stage_01/` contains the modified normative documents and the
Stage-1Y deliverable set. The Stage-1Y (`STAGE_01Y_*`) deliverables are:

```
STAGE_01Y_CORRECTION_REPORT.md                 # Y1–Y5 correction summary
STAGE_01Y_SETUP_RETRY_REPLAY_AUDIT.md          # Y1 — this audit
STAGE_01Y_TEMPLATE_RETRY_IDENTITY_AUDIT.md     # Y2
STAGE_01Y_RETRY_GENERATION_OWNERSHIP_AUDIT.md  # Y3
STAGE_01Y_ROLLBACK_WAKING_COMPLETENESS_AUDIT.md # Y4
STAGE_01Y_T12_CLOSURE_OWNERSHIP_AUDIT.md       # Y5
STAGE_01Y_PROCEDURE_SIGNATURE_CALL_AUDIT.md
STAGE_01Y_PROCEDURE_CALL_GRAPH.md
STAGE_01Y_SEMANTIC_TEST_VECTORS.md             # TV210–TV218
STAGE_01Y_SUPERSESSION_REGISTER.md
STAGE_01Y_CROSS_DOCUMENT_AUDIT.md
STAGE_01Y_CHECKSUM_MANIFEST.sha256
```

The six modified normative documents are `STAGE_01_PROTOCOL_PSEUDOCODE.md`, `STAGE_01_MINER_STATE_MACHINE.md`,
`STAGE_01_ROUND_STATE_MACHINE.md`, `STAGE_01_INVARIANT_CATALOGUE.md`, `STAGE_01_TERMINOLOGY.md`, and
`STAGE_01_TRACEABILITY_MATRIX.csv`. The Stage-1A–1X lettered artifacts are unchanged (historical freeze).

## Result

**PASS** — Y1 is fully realised: `SetupRetryEvent` checks EXACT-replay idempotence (gate 2, `STAGE_01_PROTOCOL_PSEUDOCODE.md:1854`–`1855`) before the terminal check (gate 3, `1857`) and before the wrong-round-state `RoundAbort` (gate 5, `1870`–`1872`); a post-`HASHING` replay returns `setup_retry_duplicate_suppressed` and never aborts the forward round; `SetupRetryStatus` is defined (`804`) and marked `APPLYING` atomically before the target is invoked (`1882`–`1891`); the `RETURNS` union (`1892`–`1893`) and closing `NOTE` (`1894`–`1896`) reflect the reorder; and the statement is consistent across pseudocode, round-SM §3.10c, invariant I16, terminology, and traceability rows R178/R183.
