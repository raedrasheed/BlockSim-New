# Stage 1X — Setup Retry State Audit (X4)

## 1. Scope

This audit documents correction **X4** of the Stage-1X revision to the PoCol formal
specification (the idle policy within PoCol): *make the `SetupRetryEvent` round-state guards
KIND-SPECIFIC*. Before X4 the retry handler admitted a shared multi-state guard; X4 withdraws
it and requires `round_state = ASSIGNMENT` for BOTH setup kinds, dispatches each kind to its
own owning procedure, and turns retry-budget exhaustion into a declared `RoundAbort` rather
than a silent no-op — while keeping every dispatch a total function that never leaves the
round in `ASSIGNMENT` with no controller.

The audit is descriptive and documentation-only. It reads the current specification text and
records the state of the corrected contract; it modifies no protocol file, runs no code, and
introduces no algorithm, vendor, or tooling name beyond PoCol. Every claim below is grounded
in the current text of

- `STAGE_01_PROTOCOL_PSEUDOCODE.md` — the normative pseudocode; `SetupRetryEvent` occupies
  lines 1747–1797 and the two seating sites are `PrepareParticipantsForNewRound`
  (`PARTICIPANT_SETUP`, lines 1644–1664) and `ContinueTemplateRefreshAssignmentSetup`
  (`TEMPLATE_REFRESH_SETUP`, lines 4793–4811). Line numbers were re-established by grep
  against the current file, not inherited from any earlier revision.

with traceability confirmed against `STAGE_01_ROUND_STATE_MACHINE.md` (§3.10b, X4 block),
`STAGE_01_TERMINOLOGY.md` (Stage-1X addendum, kind-specific `SetupRetryEvent` guard),
`STAGE_01_INVARIANT_CATALOGUE.md` (I16, X3/X4 amendment), and
`STAGE_01_TRACEABILITY_MATRIX.csv` (R172 for X4; R177 for the blocking test vectors
TV203/TV204).

The A1 energy-accounting baseline (`8.420833333 kWh`,
`STAGE_01_ENERGY_MODEL_SPECIFICATION.md` line 29) is unaffected by this correction and is
preserved unchanged. X4 is a control-flow / guard-structure / liveness correction with no
energy or time semantics: it changes *which* round states admit a retry and *how* a rejected
retry terminates, never how any residency interval is charged.

## 2. The X4 correction in brief

X4 restructures the `SetupRetryEvent` guard ladder along three axes:

1. **The shared multi-state guard is WITHDRAWN and replaced by a KIND-SPECIFIC
   `ASSIGNMENT`-only guard.** Both target procedures resume the *post-commit assignment
   phase*, which is legal only from `ASSIGNMENT`; therefore a non-terminal, non-`ASSIGNMENT`
   state (`ROUND_INITIALISING` / `TEMPLATE_COMMITMENT`) is rejected with a declared
   `RoundAbort`, and the target procedure is never called illegally.

2. **Retry-budget exhaustion is a declared `RoundAbort`, not a bare no-op.** An over-budget
   retry does not merely return an `exhausted`/`setup_retry_exhausted` disposition (which
   would strand the round in `ASSIGNMENT` with no controller); it aborts with
   `setup_retry_budget_exhausted`. The already-terminal case is handled *first*, so a round
   that has already reached `ROUND_ACCEPTED`/`ROUND_ABORTED` is a clean no-op that needs no
   controller.

3. **Each kind dispatches to its own owning procedure.** `PARTICIPANT_SETUP` resumes
   `PrepareParticipantsForNewRound`; `TEMPLATE_REFRESH_SETUP` resumes
   `ContinueTemplateRefreshAssignmentSetup` and NEVER re-enters `TemplateRefresh` (no
   re-close, no re-commit).

## 3. The corrected `SetupRetryEvent` guard ladder (operative text)

The corrected handler is a single ordered ladder (`STAGE_01_PROTOCOL_PSEUDOCODE.md`
lines 1747–1797). The operative guards, in dispatch order:

```
1754    IF RoundID != RoundID_current:
1755      RETURN setup_retry_stale_noop(SetupRetryID)          # the round moved on; retry is a no-op
1756    IF round_state in {ROUND_ACCEPTED, ROUND_ABORTED}:
1757      RETURN setup_retry_terminal_stale_noop(SetupRetryID) # X4: already terminal; nothing to retry, no controller needed
...
1761    IF round_state != ASSIGNMENT:
1762      RETURN CALL RoundAbort(RoundContext, reason = setup_retry_wrong_round_state(setup_kind, round_state),
1763                             dispatch_envelope = dispatch_envelope, recovery_finalising = false)   # X4
...
1765    IF SetupRetryID in applied_setup_retry_ids:
1766      RETURN setup_retry_duplicate_suppressed(SetupRetryID)
...
1769    IF setup_retry_generation > maximum_setup_retries:
1770      RETURN CALL RoundAbort(RoundContext, reason = setup_retry_budget_exhausted(setup_kind),
1771                             dispatch_envelope = dispatch_envelope, recovery_finalising = false)   # X4
...
1774    IF NOT (every eligible participant of RoundID is in miner_state {REGISTERED, RESERVE, LOW_POWER_LISTEN}):
1775      RETURN CALL RoundAbort(RoundContext, reason = setup_retry_state_incompatible(setup_kind),
1776                             dispatch_envelope = dispatch_envelope, recovery_finalising = false)   # W8
1777    ADD SetupRetryID to applied_setup_retry_ids            # W8: register the idempotent marker BEFORE re-invoking
```

Each verification claim below quotes the operative line(s) from this ladder or from the two
seating/target procedures.

## 4. Verification claims

### Claim 1 — `PARTICIPANT_SETUP` requires `ASSIGNMENT` + a committed eligible `TemplateID`, then calls `PrepareParticipantsForNewRound`. **PASS**

The `ASSIGNMENT` requirement is the shared kind-specific guard at line 1761
(`IF round_state != ASSIGNMENT: ... RETURN CALL RoundAbort(...)`). The
`PARTICIPANT_SETUP`-specific arm then asserts the committed eligible template and dispatches
(`STAGE_01_PROTOCOL_PSEUDOCODE.md` lines 1779–1781):

```
1779    IF setup_kind = PARTICIPANT_SETUP:
1780      ASSERT a committed eligible TemplateID exists for RoundContext                       # X4: PARTICIPANT_SETUP precondition
1781      RETURN CALL PrepareParticipantsForNewRound(RoundContext, dispatch_envelope)          # X4: re-run participant setup
```

Both preconditions (`ASSIGNMENT`; a committed eligible `TemplateID`) are enforced before the
call, and the call target is exactly `PrepareParticipantsForNewRound`. The seating site that
mints this kind (line 1660, `setup_kind = PARTICIPANT_SETUP`) confirms the kind label is the
one the handler branches on. **PASS.**

### Claim 2 — `TEMPLATE_REFRESH_SETUP` requires `ASSIGNMENT` + committed `TemplateID` = the refresh setup's + the closure/commit markers, then calls `ContinueTemplateRefreshAssignmentSetup`. **PASS**

The `ASSIGNMENT` requirement is again the line-1761 guard. The `TEMPLATE_REFRESH_SETUP` arm
(the fall-through past the `PARTICIPANT_SETUP` branch) asserts BOTH the committed-template
identity and the idempotent closure/commit marker before dispatch
(`STAGE_01_PROTOCOL_PSEUDOCODE.md` lines 1785–1788):

```
1785    ASSERT TemplateID_committed = the refresh setup's TemplateID
1786           AND template_refresh_setup_committed[TemplateID_committed] EXISTS                # X3/X4: markers present exactly once
1787    RETURN CALL ContinueTemplateRefreshAssignmentSetup(RoundContext, dispatch_envelope, TemplateID = TemplateID_committed,
1788                     SetupRetryID = SetupRetryID, setup_retry_generation = setup_retry_generation)   # X3/X4
```

The call target is `ContinueTemplateRefreshAssignmentSetup`, never `TemplateRefresh`. The
handler's own NOTE states this explicitly (line 1791–1793): "`TEMPLATE_REFRESH_SETUP` calls
`ContinueTemplateRefreshAssignmentSetup` (NEVER `TemplateRefresh` — no re-close / re-commit)".
It is corroborated at the origin: `TemplateRefresh` records the marker exactly once
(`template_refresh_setup_committed[new_TemplateID] <- refresh_setup_markers(...)`, lines
4729–4731) and its NOTE (lines 4740–4742) states a `TEMPLATE_REFRESH_SETUP` retry "resumes
`ContinueTemplateRefreshAssignmentSetup` ... so a retry NEVER re-closes the old template,
re-builds a candidate template, or re-commits". The target procedure's own PRECONDITIONS
mirror the two asserts (`round_state = ASSIGNMENT; TemplateID = TemplateID_committed;
template_refresh_setup_committed[TemplateID] EXISTS`, lines 4748–4749). **PASS.**

### Claim 3 — `ROUND_INITIALISING` and `TEMPLATE_COMMITMENT` are rejected (declared `RoundAbort`, not a silent proceed). **PASS**

The kind-specific guard admits ONLY `ASSIGNMENT`; every other non-terminal round state — the
setup/commit states `ROUND_INITIALISING` and `TEMPLATE_COMMITMENT` — falls through the
line-1761 predicate and takes the declared abort (`STAGE_01_PROTOCOL_PSEUDOCODE.md`
lines 1761–1763):

```
1761    IF round_state != ASSIGNMENT:
1762      RETURN CALL RoundAbort(RoundContext, reason = setup_retry_wrong_round_state(setup_kind, round_state),
1763                             dispatch_envelope = dispatch_envelope, recovery_finalising = false)   # X4
```

The comment above the guard is explicit that this is a rejection, not a fall-through to the
target: "BOTH target procedures require ASSIGNMENT, so ROUND_INITIALISING / TEMPLATE_COMMITMENT
are NOT accepted. A retry dispatched in a non-terminal, non-ASSIGNMENT state is rejected with a
declared abort — the target procedure is NEVER called illegally" (lines 1758–1760). Because
this guard is placed *after* the terminal check (line 1756) and *before* the idempotence,
budget, and state-compatibility guards, a `ROUND_INITIALISING`/`TEMPLATE_COMMITMENT` dispatch
can only exit via `RoundAbort(setup_retry_wrong_round_state)` — never a silent
proceed-to-target and never a bare no-op. **PASS.**

### Claim 4 — An over-budget retry is a declared `RoundAbort(setup_retry_budget_exhausted)`, NOT merely a `setup_retry_exhausted` no-op — and the terminal case is handled first so a terminal round is a clean no-op. **PASS**

The budget guard aborts with a *declared reason*, and its comment states the intent verbatim
(`STAGE_01_PROTOCOL_PSEUDOCODE.md` lines 1767–1771):

```
1767    # X4 BOUND: retry-budget exhaustion cannot strand the round — do NOT merely return exhausted; ABORT with a declared
1768    #   reason (the terminal case was already handled above).
1769    IF setup_retry_generation > maximum_setup_retries:
1770      RETURN CALL RoundAbort(RoundContext, reason = setup_retry_budget_exhausted(setup_kind),
1771                             dispatch_envelope = dispatch_envelope, recovery_finalising = false)   # X4
```

The abort reason is `setup_retry_budget_exhausted(setup_kind)` — a `RoundAbort`, not a bare
`setup_retry_exhausted` disposition. The ordering requirement is satisfied structurally: the
terminal check precedes the budget check (`STAGE_01_PROTOCOL_PSEUDOCODE.md` lines 1756–1757):

```
1756    IF round_state in {ROUND_ACCEPTED, ROUND_ABORTED}:
1757      RETURN setup_retry_terminal_stale_noop(SetupRetryID) # X4: already terminal; nothing to retry, no controller needed
```

Because the terminal case returns *before* the ladder reaches the budget guard, a round that
has already reached `ROUND_ACCEPTED`/`ROUND_ABORTED` is a clean no-op that needs no
controller, while a still-live `ASSIGNMENT` round whose budget is spent takes the declared
abort. The NOTE reinforces the distinction: "BOUNDED (an over-budget retry ABORTS, never
merely 'exhausted')" (lines 1794–1795). **PASS.**

### Claim 5 — Every dispatch ends in exactly one of {target's disposition, terminal/stale no-op, `RoundAbort`}; the phase is NEVER left in `ASSIGNMENT` with no controller. **PASS**

The handler is a total function over its dispatch: every path `RETURN`s, and the `RETURNS`
union enumerates every disposition (`STAGE_01_PROTOCOL_PSEUDOCODE.md` lines 1789–1790):

```
1789  RETURNS: setup_retry_stale_noop | setup_retry_terminal_stale_noop | setup_retry_duplicate_suppressed | round_aborted |
1790           (the re-run target procedure's disposition)
```

The closing NOTE states the liveness guarantee explicitly (lines 1795–1797):

```
1795        STATE-COMPATIBLE (an OFFLINE-stranded participant ABORTS). Every dispatch ends in exactly one of: the target's
1796        disposition (setup succeeded / a later bounded retry live / round aborted); round terminal; or a stale terminal
1797        no-op — NEVER leaving ASSIGNMENT with no controller.
```

The branch structure realises this exhaustively. Reading the ladder top to bottom, every
dispatch resolves at exactly one guard:

| Ladder position | Condition | Disposition | Controller left in `ASSIGNMENT`? |
|-----------------|-----------|-------------|----------------------------------|
| line 1754 | `RoundID != RoundID_current` | `setup_retry_stale_noop` | n/a — round moved on |
| line 1756 | `round_state in {ROUND_ACCEPTED, ROUND_ABORTED}` | `setup_retry_terminal_stale_noop` | n/a — round terminal |
| line 1761 | `round_state != ASSIGNMENT` (non-terminal) | `RoundAbort(setup_retry_wrong_round_state)` | no — declared abort |
| line 1765 | `SetupRetryID in applied_setup_retry_ids` | `setup_retry_duplicate_suppressed` | no — the prior dispatch already installed the controller / disposition |
| line 1769 | `setup_retry_generation > maximum_setup_retries` | `RoundAbort(setup_retry_budget_exhausted)` | no — declared abort |
| line 1774 | some eligible participant not re-enlistable | `RoundAbort(setup_retry_state_incompatible)` | no — declared abort |
| lines 1779–1781 | `setup_kind = PARTICIPANT_SETUP` | `PrepareParticipantsForNewRound`'s disposition | no — target owns the phase (success → HASHING, later bounded retry, or its own `RoundAbort`) |
| lines 1785–1788 | `setup_kind = TEMPLATE_REFRESH_SETUP` | `ContinueTemplateRefreshAssignmentSetup`'s disposition | no — target owns the phase |

There is no fall-through path: the ladder either returns a no-op (stale/terminal/duplicate),
returns a `RoundAbort`, or hands the `ASSIGNMENT` phase to a named owning procedure that
itself terminates in success (→ `HASHING`), a further bounded retry seat, or a declared
`RoundAbort` (target NOTEs at lines 1865–1871 and 4813–4819). Consequently the round is never
left in `ASSIGNMENT` with no controller. **PASS.**

## 5. Test-vector linkage (TV203, TV204)

The X4 contract is exercised by two blocking paper test vectors, logged under R177 of
`STAGE_01_TRACEABILITY_MATRIX.csv` (the Stage-1X X1–X8 test-vector row, whose artefact column
names `STAGE_01X_SEMANTIC_TEST_VECTORS`):

- **TV203** — "a `PARTICIPANT_SETUP` retry in the wrong phase is rejected and a valid one runs
  `PrepareParticipantsForNewRound`." This binds Claims 1 and 3: the wrong-phase rejection is
  the line-1761 `RoundAbort(setup_retry_wrong_round_state)` guard, and the valid path is the
  line-1779–1781 dispatch to `PrepareParticipantsForNewRound` after the committed-eligible
  `TemplateID` assert.

- **TV204** — "an over-budget setup retry executes `RoundAbort` and never leaves `ASSIGNMENT`
  with no controller." This binds Claims 4 and 5: the over-budget path is the line-1769–1771
  `RoundAbort(setup_retry_budget_exhausted)` guard, and the "never leaves `ASSIGNMENT` with no
  controller" clause is the closing NOTE (lines 1795–1797) together with the exhaustive branch
  table above.

Both vectors name `SetupRetryEvent`, `PrepareParticipantsForNewRound`,
`ContinueTemplateRefreshAssignmentSetup`, and `RoundAbort` among their exercised procedures
(R177 state/event column) and are recorded with status `SPECIFIED`.

## 6. Cross-document consistency

The X4 contract is stated identically across the four governing documents.

- **Pseudocode ↔ round state machine §3.10b (X4 block).**
  `STAGE_01_ROUND_STATE_MACHINE.md` lines 703–707 (X4): "`SetupRetryEvent` requires
  `round_state = ASSIGNMENT` for BOTH kinds (`ROUND_INITIALISING` / `TEMPLATE_COMMITMENT` are
  rejected); `PARTICIPANT_SETUP` calls `PrepareParticipantsForNewRound`,
  `TEMPLATE_REFRESH_SETUP` calls `ContinueTemplateRefreshAssignmentSetup` (asserting the
  committed `TemplateID` matches the refresh setup's and its markers exist). An over-budget
  retry `RoundAbort`s (never merely `setup_retry_exhausted`); every dispatch ends in the
  target's disposition, a round-terminal state, or a stale terminal no-op." This matches the
  pseudocode guards of §§3–4 line for line (the `ASSIGNMENT`-only guard, the two kind arms,
  the budget abort, and the three-way disposition).

- **Pseudocode ↔ terminology (Stage-1X addendum, X4 entry).**
  `STAGE_01_TERMINOLOGY.md` lines 885–890: "`PARTICIPANT_SETUP` requires `phase = ASSIGNMENT`
  and a committed eligible `TemplateID`, then calls `PrepareParticipantsForNewRound`;
  `TEMPLATE_REFRESH_SETUP` requires `phase = ASSIGNMENT`, the committed `TemplateID` equal to
  the refresh setup's, and the closure/commit markers, then calls
  `ContinueTemplateRefreshAssignmentSetup`. `ROUND_INITIALISING` / `TEMPLATE_COMMITMENT` are
  rejected; an over-budget retry is a `RoundAbort` (not merely `setup_retry_exhausted`) unless
  already terminal; the phase is never left in `ASSIGNMENT` with no controller." Every clause
  corresponds to a quoted pseudocode guard above, including the "unless already terminal"
  ordering (Claim 4).

- **Pseudocode ↔ invariant I16 (X3/X4 amendment).**
  `STAGE_01_INVARIANT_CATALOGUE.md` lines 338–341 (I16, the "security-floor breaches are
  recorded, not silently repaired" invariant, line 284): "**X3/X4:** template-refresh
  initiation (`TemplateRefresh`) is split from the post-commit assignment retry
  (`ContinueTemplateRefreshAssignmentSetup`); a retry never repeats the old-template closure
  or `TemplateCommit`, `SetupRetryEvent` guards are kind-specific (both require `ASSIGNMENT`),
  and an over-budget retry aborts rather than stranding the round." The I16 binding places the
  kind-specific-guard and abort-not-strand guarantees inside the recorded-not-repaired
  discipline: an unrecoverable setup is *declared* as a `RoundAbort`, never masked by a
  wrong-phase proceed or a bare exhaustion no-op.

- **Traceability matrix.** R172 (`STAGE_01_TRACEABILITY_MATRIX.csv` line 173) is the X4
  correction record and restates the contract verbatim (kind-specific `ASSIGNMENT` guard, the
  two dispatch targets, `ROUND_INITIALISING`/`TEMPLATE_COMMITMENT` rejected, over-budget
  `RoundAbort` "not merely `setup_retry_exhausted` unless already terminal", "the phase is
  never left in `ASSIGNMENT` with no controller"), naming invariants `I16;I18b` and status
  `SPECIFIED`. TV203/TV204 are logged under R177 (§5).

All four documents agree; no divergence was found in the X4 contract.

**Observation (non-blocking, outside X4 scope).** The inline cross-reference at
`STAGE_01_PROTOCOL_PSEUDOCODE.md` line 1280 reads "`(X6; TV204)`" inside the
`CreatePendingAssignment` precondition note. Per R177, TV204 is the *over-budget setup-retry*
vector (Claim 4/5), while the `CreatePendingAssignment` reachability property is TV206; the
inline id therefore appears to be a stray reference (TV206 intended). This concerns the X6
constructor note, not the X4 `SetupRetryEvent` guards, and does not affect any X4 verdict; it
is recorded here only for cross-document accuracy and left unedited (source-of-truth files are
read-only).

## 7. Result

**PASS** — X4 is fully realised: `SetupRetryEvent` enforces a kind-specific `ASSIGNMENT`-only
guard, dispatches `PARTICIPANT_SETUP` → `PrepareParticipantsForNewRound` and
`TEMPLATE_REFRESH_SETUP` → `ContinueTemplateRefreshAssignmentSetup` under their exact
committed-template preconditions, rejects `ROUND_INITIALISING`/`TEMPLATE_COMMITMENT` and an
over-budget retry with declared `RoundAbort`s (terminal handled first), and ends every
dispatch in exactly one of {target disposition, terminal/stale no-op, `RoundAbort`} — never
leaving `ASSIGNMENT` with no controller; consistent across pseudocode, round-SM §3.10b,
terminology, and invariant I16, with TV203/TV204 linkage, and the A1 baseline
`8.420833333 kWh` preserved.
