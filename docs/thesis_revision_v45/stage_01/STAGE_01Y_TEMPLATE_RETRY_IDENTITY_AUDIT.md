# Stage 1Y — Template-Refresh Retry Identity Audit (Y2)

## 0. Scope

This document audits correction **Y2** — *"exact template-refresh setup identity"* — as it appears
in the *current* Stage-1 formal specification of **PoCol** and the idle policy within PoCol. It is a
documentation-only, descriptive audit: it reads and quotes the committed artifacts and asserts
nothing beyond what those artifacts state. It characterises the final committed state of the corpus;
there are no open Y2 findings against the template-refresh retry identity.

The object under audit is the `TEMPLATE_REFRESH_SETUP` retry identity — the requirement that the
committed template-refresh setup identity `TemplateRefreshSetupID = (RoundID, committed_new_TemplateID)`
be carried EXPLICITLY through the retry path and VERIFIED against the committed marker before any
assignment work runs, so a stale retry for an earlier `TemplateID` can never operate on the current
committed template. The procedures under audit are `TemplateRefresh` (initiation only),
`SetupRetryEvent` (the bounded-retry handler), and `ContinueTemplateRefreshAssignmentSetup` (the sole
owner of the post-`TemplateCommit` assignment phase), together with the marker map
`template_refresh_setup_committed`.

Every claim is grounded in the following primary sources, all under
`docs/thesis_revision_v45/stage_01/`. Line numbers were re-established by direct search against the
committed files and are cited as currently observed.

- `STAGE_01_PROTOCOL_PSEUDOCODE.md`
  - `§0.8` marker-definition comment for `TemplateRefreshSetupID` / `template_refresh_setup_committed`
    (X3) — lines **798–802**; the Y1/Y2/Y3 identity block — lines **803–818** (the Y2 definition and
    carry-and-verify contract at **814–818**).
  - `SetupRetryEvent` — §2a, header at line **1835**; `INPUTS` at **1836–1837**; the Y2 kind-specific
    identity guard at **1859–1868** (the `TEMPLATE_REFRESH_SETUP` branch at **1864–1868**); the
    mark-and-invoke continuation call at **1889–1891**.
  - `TemplateRefresh` — §19, header at line **4813**; the `SET TemplateRefreshSetupID` at **4833**;
    the marker record at **4834–4836**; the delegating `RETURN CALL` at **4840–4842**; `RETURNS` at
    **4843**.
  - `ContinueTemplateRefreshAssignmentSetup` — §19, header at line **4851**; `INPUTS` at **4852**;
    the Y2 `PRECONDITIONS` identity note at **4856–4859**; the on-entry Y2 verification at
    **4863–4868**; the bounded-retry seat that re-carries the exact identity at **4924–4930**.
- `STAGE_01_ROUND_STATE_MACHINE.md` — §3.10c Stage-1Y addendum, the **Y2** block, lines **741–746**.
- `STAGE_01_INVARIANT_CATALOGUE.md` — invariant **I16**, the Stage-1Y **Y2** clause, lines **351–353**.
- `STAGE_01_TERMINOLOGY.md` — the Stage-1Y `TemplateRefreshSetupID (Y2)` entry, lines **913–918**.
- `STAGE_01Y_SEMANTIC_TEST_VECTORS.md` — vectors **TV211** (lines **29–38**) and **TV212** (lines
  **40–48**); the linkage table rows at **122–123**.
- `STAGE_01_TRACEABILITY_MATRIX.csv` — requirement **R179**, line **180**.

The overall algorithm name remains **PoCol**; the mechanism under revision is the idle policy within
PoCol. The A1 accepted-baseline energy figure of `8.420833333 kWh` is unchanged by this correction —
Y2 makes the template-refresh setup identity exact and explicit, altering no census value, residency
interval, difficulty, or accounting quantity.

## 1. What correction Y2 states

`TemplateRefreshSetupID` is the idempotent identity keyed to the committed new `TemplateID`. Before
Y2, the retry path could resolve the template through an ambient phrase ("the refresh setup's
`TemplateID`") rather than an explicit input or a record lookup, admitting a stale retry that
resolves the *current* committed template and operates on it. Y2 makes the identity EXACT and
EXPLICIT end-to-end:

- the identity is defined as `TemplateRefreshSetupID = (RoundID, committed_new_TemplateID)`;
- the `TEMPLATE_REFRESH_SETUP` retry payload carries BOTH `TemplateID_at_seat` and
  `TemplateRefreshSetupID` explicitly;
- both `SetupRetryEvent` and `ContinueTemplateRefreshAssignmentSetup` VERIFY the exact
  `TemplateRefreshSetupID` against `template_refresh_setup_committed[TemplateID_at_seat].TemplateRefreshSetupID`
  on the initial invocation AND every retry;
- no ambient "the refresh setup's `TemplateID`" is used as a value anywhere;
- a stale retry for an earlier `TemplateID` takes a declared stale disposition and never operates on
  the current committed template.

The `§0.8` state-dictionary block records the contract directly (lines **814–818**):

```
  # TemplateRefreshSetupID = (RoundID, committed_new_TemplateID) (Y2). A TEMPLATE_REFRESH_SETUP SetupRetryEvent payload
  #   carries BOTH TemplateID_at_seat AND TemplateRefreshSetupID explicitly; ContinueTemplateRefreshAssignmentSetup
  #   receives and VERIFIES the exact TemplateRefreshSetupID on the initial invocation AND every retry against
  #   template_refresh_setup_committed[TemplateID_at_seat].TemplateRefreshSetupID — there is no ambient
  #   "the refresh setup's TemplateID" (Y2). A stale retry for an earlier TemplateID takes a declared stale disposition.
```

## 2. Check 1 — `TemplateRefresh` passes the exact `TemplateRefreshSetupID` — PASS

`TemplateRefresh` (header line **4813**) computes the identity from the committed round and template
and then records it in the marker map before delegating. Line **4833**:

```
    SET TemplateRefreshSetupID <- (RoundID_current, new_TemplateID)                     # X3/Y2: idempotent identity = (RoundID, committed_new_TemplateID)
```

The marker is recorded so the identity is retrievable on later verification (lines **4834–4836**):

```
    SET template_refresh_setup_committed[new_TemplateID] <- refresh_setup_markers(
          RoundID = RoundID_current, old_TemplateID = old_TemplateID_snapshot,
          TemplateRefreshSetupID = TemplateRefreshSetupID)                              # X3: closure + commit happened once
```

The delegation to the continuation passes the EXACT `TemplateRefreshSetupID` (not an ambient value),
with the initial-invocation markers `SetupRetryID = null` and `retry_generation = 0` (lines
**4840–4842**):

```
    RETURN CALL ContinueTemplateRefreshAssignmentSetup(RoundContext, dispatch_envelope, TemplateID = new_TemplateID,
                     TemplateRefreshSetupID = TemplateRefreshSetupID,
                     SetupRetryID = null, retry_generation = 0)   # X3/Y2/Y3
```

The value passed is exactly the value set at line 4833 and recorded at 4834–4836. The `RETURNS`
clause (line **4843**) notes the initial call "cannot be stale". **PASS** — `TemplateRefresh` sets
`TemplateRefreshSetupID <- (RoundID_current, new_TemplateID)`, records it in
`template_refresh_setup_committed[new_TemplateID]`, and forwards precisely that identifier with
`SetupRetryID = null, retry_generation = 0`.

## 3. Check 2 — `SetupRetryEvent` carries `TemplateID_at_seat` + `TemplateRefreshSetupID` and verifies both against the committed marker before the continuation — PASS

`SetupRetryEvent` (header line **1835**) receives both identifiers explicitly in its `INPUTS` (lines
**1836–1837**):

```
  INPUTS: RoundContext, dispatch_envelope, RoundID, setup_kind, SetupRetryID,
          TemplateID_at_seat, TemplateRefreshSetupID, retry_generation, reason
```

The canonical guard order places the kind-specific EXACT-template-identity check as guard (4), before
the target-round-state / budget guards and before the mark-and-invoke step. The
`TEMPLATE_REFRESH_SETUP` branch verifies BOTH `TemplateID_at_seat` and `TemplateRefreshSetupID`
against the committed marker (lines **1864–1868**):

```
    ELSE:   # setup_kind = TEMPLATE_REFRESH_SETUP
      IF NOT (TemplateID_at_seat = TemplateID_committed
              AND template_refresh_setup_committed[TemplateID_at_seat] EXISTS
              AND TemplateRefreshSetupID = template_refresh_setup_committed[TemplateID_at_seat].TemplateRefreshSetupID):
        RETURN setup_retry_stale_noop(SetupRetryID)          # Y2: stale TemplateID / TemplateRefreshSetupID — never operate on the current template
```

Only after this verification (and the state/budget guards) does the handler mark the retry `APPLYING`
and invoke the continuation, forwarding the EXACT `TemplateRefreshSetupID` and the seat-time
`TemplateID_at_seat` (lines **1889–1891**):

```
    RETURN CALL ContinueTemplateRefreshAssignmentSetup(RoundContext, dispatch_envelope, TemplateID = TemplateID_at_seat,
                     TemplateRefreshSetupID = TemplateRefreshSetupID,
                     SetupRetryID = SetupRetryID, retry_generation = retry_generation)   # X3/X4/Y2/Y3
```

The verification (guard 4) strictly precedes the continuation call. **PASS** — the payload carries
`TemplateID_at_seat` and `TemplateRefreshSetupID`; both are checked against
`template_refresh_setup_committed[TemplateID_at_seat].TemplateRefreshSetupID` (and against
`TemplateID_committed`) before the continuation runs; a mismatch returns `setup_retry_stale_noop`.

## 4. Check 3 — `ContinueTemplateRefreshAssignmentSetup` re-verifies the exact identity on the initial invocation AND every retry — PASS

`ContinueTemplateRefreshAssignmentSetup` (header line **4851**) takes `TemplateRefreshSetupID` as an
explicit input (line **4852**):

```
  INPUTS: RoundContext, dispatch_envelope, TemplateID, TemplateRefreshSetupID, SetupRetryID, retry_generation
```

Its `PRECONDITIONS` state the Y2 exact-identity requirement (lines **4856–4859**), and the first act
of `EFFECTS` is the on-entry verification, returning the declared stale disposition on any mismatch
(lines **4863–4868**):

```
    # Y2: VERIFY the exact template identity before doing any work — a stale TemplateRefreshSetupID / TemplateID never
    #   operates on the current committed template (the SetupRetryEvent guard also checks this; re-checked here defensively).
    IF NOT (TemplateID = TemplateID_committed
            AND template_refresh_setup_committed[TemplateID] EXISTS
            AND TemplateRefreshSetupID = template_refresh_setup_committed[TemplateID].TemplateRefreshSetupID):
      RETURN template_refresh_retry_stale_noop(TemplateRefreshSetupID)   # Y2: declared stale disposition; NEVER operate on the current template
```

This entry check runs on BOTH paths into the procedure: the initial invocation from `TemplateRefresh`
(§2 above, `SetupRetryID = null`) and every `TEMPLATE_REFRESH_SETUP` retry from `SetupRetryEvent`
(§3 above). The `INPUTS` note (lines **4854–4855**) confirms the identity is passed explicitly on both:
"`TemplateRefreshSetupID` is passed EXPLICITLY on BOTH the initial invocation and every retry (never
an ambient 'the refresh setup's TemplateID')." When this procedure seats its own bounded retry it
re-carries the exact identity into the next `SetupRetryEvent` payload (lines **4924–4930**):

```
      SET srid <- (TemplateRefreshSetupID, TEMPLATE_REFRESH_SETUP, g)                     # Y3: full-scope SetupRetryID
      SET r <- CALL ScheduleEvent(EQ, RoundContext, SetupRetryEvent,
                     target_event_time = next_representable_simulation_time(dispatch_envelope.event_time),
                     target_microphase = ROUND_SETUP,
                     {RoundID = RoundID_current, setup_kind = TEMPLATE_REFRESH_SETUP, SetupRetryID = srid,
                      TemplateID_at_seat = TemplateID, TemplateRefreshSetupID = TemplateRefreshSetupID,
                      retry_generation = g, reason = setup_reason})               # W8/X3/Y2/Y3: the retry resumes THIS procedure (never TemplateRefresh) with the EXACT identity
```

The seeded payload carries the verified `TemplateID` (as `TemplateID_at_seat`) and the verified
`TemplateRefreshSetupID`, so the next `SetupRetryEvent` re-verifies (§3) and re-enters this procedure,
which re-verifies again on entry. **PASS** — the exact identity is re-verified on the initial
invocation and on every retry, and the verified identity is re-carried into each subsequent retry
seat; a mismatch returns `template_refresh_retry_stale_noop`.

## 5. Check 4 — no ambient "the refresh setup's TemplateID" value remains — PASS

A whole-file search of `STAGE_01_PROTOCOL_PSEUDOCODE.md` for the phrase `refresh setup's TemplateID`
returns exactly four occurrences — lines **818**, **1859**, **1899**, and **4855** — and every one is
an explicit NEGATION forbidding the phrase's use as a value, not a use of it as a value:

- **818:** `#   "the refresh setup's TemplateID" (Y2).` — the tail of the §0.8 contract sentence
  beginning "there is no ambient" (line 817).
- **1859:** `# (4) Y2 KIND-SPECIFIC EXACT TEMPLATE IDENTITY (no ambient "the refresh setup's TemplateID").`
- **1899:** `ambient "the refresh setup's TemplateID"). Y3: ...` — the tail of the `SetupRetryEvent`
  NOTE clause "no ambient" (line 1898).
- **4855:** `#   EXPLICITLY on BOTH the initial invocation and every retry (never an ambient "the refresh setup's TemplateID").`

In each site the identity is required to resolve through an explicit input (`TemplateRefreshSetupID`,
`TemplateID_at_seat`) or a record lookup (`template_refresh_setup_committed[...]`). No control-flow
statement reads "the refresh setup's TemplateID" as a value. **PASS** — the ambient phrase survives
only inside prohibitions of itself; every value is an explicit input or a committed-record lookup.

## 6. Check 5 — a stale older-`TemplateID` retry takes a declared stale disposition and never operates on the current committed template — PASS

Two independent gates enforce this:

1. **`SetupRetryEvent` guard (4)** (lines **1864–1868**, quoted in §3). If a retry seated for an
   earlier `TemplateID_old` arrives after a further refresh committed `TemplateID_new`, then
   `TemplateID_at_seat (= TemplateID_old) != TemplateID_committed` (or the `TemplateRefreshSetupID`
   no longer matches the committed marker), so the guard returns `setup_retry_stale_noop(SetupRetryID)`.
   The continuation is never called, so no assignment is created against the current template.

2. **`ContinueTemplateRefreshAssignmentSetup` on-entry check** (lines **4865–4868**, quoted in §4).
   If the continuation is entered directly with a stale identity, the defensive on-entry check fails
   and returns `template_refresh_retry_stale_noop(TemplateRefreshSetupID)` before any eligible-miner
   selection, assignment creation, or `StartWake` runs (all of which begin only after the check, from
   line **4869** onward).

Both dispositions are declared in the respective `RETURNS` clauses — `setup_retry_stale_noop` at line
**1892** and `template_refresh_retry_stale_noop` at line **4934** (and propagated by `TemplateRefresh`
at line **4843**). The `§0.8` contract states the same outcome: "A stale retry for an earlier
TemplateID takes a declared stale disposition" (line **818**). **PASS** — a stale older-`TemplateID`
retry is caught by the `SetupRetryEvent` guard (or, defensively, the continuation's on-entry check),
returns a declared stale no-op, and never operates on the current committed template.

## 7. Test-vector linkage (TV211, TV212)

`STAGE_01Y_SEMANTIC_TEST_VECTORS.md` carries two vectors that exercise the Y2 identity contract; the
linkage table (lines **122–123**) binds both to `SetupRetryEvent` and
`ContinueTemplateRefreshAssignmentSetup` under correction Y2.

- **TV211 — "Template-refresh retry carries and resolves the exact identity before the continuation
  runs" (Y2)** (lines **29–38**). Setup: `TemplateRefresh` committed a new `TemplateID` and set
  `template_refresh_setup_committed[new_TemplateID].TemplateRefreshSetupID`; a bounded `SetupRetryEvent`
  is seated with `TemplateID_at_seat = new_TemplateID` and `TemplateRefreshSetupID = (RoundID,
  new_TemplateID)`. Expected: the retry verifies `TemplateID_at_seat = TemplateID_committed` AND
  `TemplateRefreshSetupID = template_refresh_setup_committed[TemplateID_at_seat].TemplateRefreshSetupID`
  BEFORE marking `APPLYING` and calling `ContinueTemplateRefreshAssignmentSetup`, and the continuation
  re-verifies on entry. This is the positive-path witness for Checks 2 and 3 (§§3–4): both sites
  resolve to the committed marker before any assignment work runs.

- **TV212 — "A stale template-refresh retry from an older TemplateID cannot operate on the newer
  template" (Y2)** (lines **40–48**). Setup: a `TEMPLATE_REFRESH_SETUP` retry seated for an EARLIER
  `TemplateID_old` arrives after a further refresh committed `TemplateID_new` (so
  `TemplateID_committed = TemplateID_new != TemplateID_old`). Expected: the kind-specific guard finds
  the mismatch and returns `setup_retry_stale_noop` — it never operates on `TemplateID_new`; if the
  continuation were entered directly, its defensive Y2 check returns `template_refresh_retry_stale_noop`;
  no assignment is created against the current template. This is the stale-path witness for Check 5
  (§6), matching both gates exactly.

Both vectors are consistent with the current pseudocode line-for-line; there is no vector describing a
stale retry that resolves an ambient `TemplateID` and operates on the newer committed template (such a
path is removed by Y2 and is recorded as the anti-behaviour in R179, §8).

## 8. Cross-document consistency

The Y2 statement is identical in substance across the corpus.

- **Pseudocode (source of truth).** `§0.8` lines **814–818** define
  `TemplateRefreshSetupID = (RoundID, committed_new_TemplateID)`, the explicit dual-field payload, the
  verify-against-`template_refresh_setup_committed` contract on initial-and-every-retry, the removal of
  the ambient phrase, and the declared stale disposition. The three procedures (`TemplateRefresh` 4833
  / 4840–4842; `SetupRetryEvent` 1864–1868 / 1889–1891; `ContinueTemplateRefreshAssignmentSetup`
  4856–4859 / 4863–4868 / 4924–4930) implement it (§§2–6).

- **Round state machine — §3.10c Stage-1Y addendum, Y2 block (lines 741–746).** "A
  `TEMPLATE_REFRESH_SETUP` retry payload carries BOTH `TemplateID_at_seat` AND
  `TemplateRefreshSetupID = (RoundID, committed_new_TemplateID)`.
  `ContinueTemplateRefreshAssignmentSetup` receives and VERIFIES the exact `TemplateRefreshSetupID`
  against `template_refresh_setup_committed[TemplateID_at_seat].TemplateRefreshSetupID` on the initial
  invocation AND every retry; there is no ambient 'the refresh setup's TemplateID'. A stale retry for
  an earlier `TemplateID` takes a declared stale disposition and never operates on the current
  committed template." Matches the pseudocode verbatim in intent and identity formula.

- **Invariant catalogue — I16, Stage-1Y Y2 clause (lines 351–353).** "a `TEMPLATE_REFRESH_SETUP`
  retry carries and verifies the EXACT `TemplateID_at_seat` and `TemplateRefreshSetupID = (RoundID,
  committed_new_TemplateID)` against `template_refresh_setup_committed`; there is no ambient 'the
  refresh setup's TemplateID', and a stale-`TemplateID` retry never operates on the current template."
  Consistent with the pseudocode and the round-SM.

- **Terminology — `TemplateRefreshSetupID (Y2)` entry (lines 913–918).** "`= (RoundID,
  committed_new_TemplateID)`. A `TEMPLATE_REFRESH_SETUP` retry payload carries BOTH `TemplateID_at_seat`
  and `TemplateRefreshSetupID` explicitly; `SetupRetryEvent` and `ContinueTemplateRefreshAssignmentSetup`
  VERIFY the exact `TemplateRefreshSetupID` against
  `template_refresh_setup_committed[TemplateID_at_seat].TemplateRefreshSetupID` on the initial
  invocation and every retry. There is no ambient 'the refresh setup's TemplateID'; a stale-`TemplateID`
  retry takes a declared stale disposition and never operates on the current committed template." Same
  identity formula, same dual-field payload, same verification sites.

- **Traceability matrix — R179 (line 180).** "Carry the exact template-refresh setup identity (Y2);
  the SetupRetryEvent payload carries TemplateID_at_seat and TemplateRefreshSetupID = (RoundID
  committed_new_TemplateID) for setup_kind = TEMPLATE_REFRESH_SETUP; ContinueTemplateRefreshAssignmentSetup
  receives and verifies the exact TemplateRefreshSetupID on the initial invocation and every retry
  against template_refresh_setup_committed[TemplateID_at_seat].TemplateRefreshSetupID; no ambient
  the-refresh-setups-TemplateID phrase remains; a stale retry for an earlier TemplateID takes a
  declared stale disposition and never operates on the current committed template." The row lists
  `state_or_event = SetupRetryEvent; ContinueTemplateRefreshAssignmentSetup; TemplateRefresh`,
  `invariant = I16; I18b`, the threat "a stale template-refresh retry that resolves an ambient
  TemplateID and operates on the newer committed template", and `status = SPECIFIED`. The requirement
  text, the named procedures, and the linked invariant all agree with the pseudocode, the round-SM
  §3.10c, the I16 Y2 clause, and the terminology entry.

No inconsistency was found across the five documents: the identity formula
`(RoundID, committed_new_TemplateID)`, the explicit dual-field payload, the
verify-on-initial-and-every-retry contract against `template_refresh_setup_committed`, the elimination
of the ambient phrase, and the declared stale disposition are stated identically everywhere they
appear.

## 9. Result

**PASS — Y2 is fully specified and internally consistent.** `TemplateRefresh` sets and forwards the
exact `TemplateRefreshSetupID = (RoundID, committed_new_TemplateID)`; `SetupRetryEvent` carries
`TemplateID_at_seat` + `TemplateRefreshSetupID` and verifies both against the committed marker before
the continuation; `ContinueTemplateRefreshAssignmentSetup` re-verifies the exact identity on the
initial invocation and every retry; no ambient "the refresh setup's TemplateID" value remains; and a
stale older-`TemplateID` retry takes a declared stale disposition (`setup_retry_stale_noop` /
`template_refresh_retry_stale_noop`) and never operates on the current committed template — consistent
across pseudocode, round-SM §3.10c (Y2), invariant I16 (Y2), terminology, R179, and vectors TV211/TV212.
