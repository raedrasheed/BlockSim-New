# Stage 1X — Template-Refresh Retry Audit (X3)

## 0. Scope

This document audits correction **X3** — *"template-refresh initiation is split from the
assignment retry"* — as it appears in the *current* Stage-1 formal specification of **the idle
policy within PoCol**. It is a documentation-only, descriptive audit: it reads and quotes the
committed artifacts and asserts nothing beyond what those artifacts state. It characterises the
final committed state of the corpus; there are no open X3 findings against the template-refresh
control flow.

The objects under audit are the procedures `TemplateRefresh` (INITIATION only) and
`ContinueTemplateRefreshAssignmentSetup` (the NEW X3 continuation that owns the post-`TemplateCommit`
assignment phase), together with their named collaborators `CloseTemplateAssignments`,
`TemplateCommit`, `RollbackTemplateRefreshSetup`, `CompleteAssignmentPhase`, `RoundAbort`, and the
bounded-retry handler `SetupRetryEvent`. Every claim is grounded in the following primary sources,
all under `docs/thesis_revision_v45/stage_01/`. Line numbers were re-established by direct search
against the committed files and are cited as currently observed.

- `STAGE_01_PROTOCOL_PSEUDOCODE.md`
  - `§0.8` marker-definition comment for `TemplateRefreshSetupID` / `template_refresh_setup_committed`
    — lines **798–802** (with the X2 `assignment_by_miner` note at 792–797).
  - `RoundInitialise` per-round reset `template_refresh_setup_committed <- empty map` — line **1431**.
  - `TemplateCommit` — §2, lines **1534–1545** (`round_state = TEMPLATE_COMMITMENT` precondition;
    `TRANSITION round_state -> ASSIGNMENT`).
  - `SetupRetryEvent` — lines **1747–1798** (header at 1747; the `TEMPLATE_REFRESH_SETUP`
    branch at **1782–1788**).
  - `CloseTemplateAssignments` — §19, lines **4650–4706** (header at 4650).
  - `TemplateRefresh` — §19, lines **4708–4742** (header at 4708; the delegating `RETURN CALL`
    at **4734–4735**).
  - `ContinueTemplateRefreshAssignmentSetup` — §19, lines **4744–4819** (header at 4744;
    PRECONDITIONS at **4748–4751**).
  - `RollbackTemplateRefreshSetup` — lines **1718–1745**.
- `STAGE_01_ROUND_STATE_MACHINE.md` — §3.10b Stage-1X addendum, the **X3** block, lines **696–701**
  (with the **X4** block at 703–707).
- `STAGE_01_TERMINOLOGY.md` — Stage-1X terminology addendum, the
  `ContinueTemplateRefreshAssignmentSetup (X3)` entry lines **877–881** and the
  `TemplateRefreshSetupID / template_refresh_setup_committed (X3)` entry lines **882–884**.
- `STAGE_01_INVARIANT_CATALOGUE.md` — invariant **I16**, the Stage-1X **X3/X4** clause lines **338–341**.
- `STAGE_01_TRACEABILITY_MATRIX.csv` — requirement **R171** (line 172, the X3 split) and the
  blocking test-vector requirement **R177** carrying **TV202** (line 178).

The overall algorithm name remains **PoCol**; the mechanism under revision is **the idle policy
within PoCol**. The A1 accepted-baseline energy figure of `8.420833333 kWh` is unchanged by this
correction — X3 re-partitions control flow between two procedures, altering no census value,
residency interval, difficulty, or accounting quantity.

## 1. The correction X3 states

Before X3, a single `TemplateRefresh` procedure owned both the one-time refresh INITIATION
(old-template closure, candidate construction, `TemplateCommit`) and the reversible assignment
phase together with its bounded retry, so a `TEMPLATE_REFRESH_SETUP` retry re-entered
`TemplateRefresh` and risked repeating the closure and the commit. X3 splits the two:
`TemplateRefresh` performs INITIATION ONCE and DELEGATES; the new
`ContinueTemplateRefreshAssignmentSetup` is the SOLE owner of the post-commit assignment phase,
its rollback, and its bounded retry; and a `TEMPLATE_REFRESH_SETUP` `SetupRetryEvent` resumes the
continuation — never `TemplateRefresh`. The round-SM §3.10b X3 block (lines 696–701) states it:

> **X3 (template-refresh initiation is split from the assignment retry).** `TemplateRefresh`
> performs old-template closure + candidate construction + `TemplateCommit` (recording the
> idempotent `template_refresh_setup_committed` marker keyed to the new `TemplateID`), then
> delegates to `ContinueTemplateRefreshAssignmentSetup`, which owns the post-commit assignment
> phase, rollback, and bounded retry. A `TEMPLATE_REFRESH_SETUP` retry resumes
> `ContinueTemplateRefreshAssignmentSetup` only — never re-entering `TemplateRefresh`, and never
> repeating `CloseTemplateAssignments` / candidate construction / `TemplateCommit`.

The five checks below verify each clause against the executable pseudocode.

## 2. Check 1 — `TemplateRefresh` does closure + candidate construction + `TemplateCommit` exactly once, then delegates — PASS

`TemplateRefresh` (lines 4708–4742) performs INITIATION as a straight-line, single-execution
sequence. It snapshots the old TemplateID, transitions into `TEMPLATE_REFRESH`, closes the old
template through the explicit named procedure, builds the new candidate, transitions to
`TEMPLATE_COMMITMENT`, and commits exactly once (lines 4715–4725):

```
    SET old_TemplateID_snapshot <- TemplateID_current          # X3: capture the old TemplateID before the refresh mutates it
    TRANSITION round_state -> TEMPLATE_REFRESH                  # from ROUND_EXHAUSTED or HASHING
    ...
    CALL CloseTemplateAssignments(RoundContext, old_TemplateID = old_TemplateID_snapshot,
                                  dispatch_envelope = dispatch_envelope)   # M1: threaded envelope
    # (3) build the new immutable template WHILE in TEMPLATE_REFRESH (C5: a NEW search domain).
    build new candidate_template
    # E8-(3): move TEMPLATE_REFRESH -> TEMPLATE_COMMITMENT BEFORE calling TemplateCommit (its precondition).
    TRANSITION round_state -> TEMPLATE_COMMITMENT
    # E8-(4): TemplateCommit REQUIRES TEMPLATE_COMMITMENT and transitions the round to ASSIGNMENT.
    new_TemplateID <- CALL TemplateCommit(RoundContext, new candidate_template)   # -> ASSIGNMENT
```

`TemplateCommit` (lines 1534–1545) requires `round_state = TEMPLATE_COMMITMENT` and itself performs
`TRANSITION round_state -> ASSIGNMENT`, so the commit runs once, out of `TEMPLATE_COMMITMENT`, and
leaves the round in `ASSIGNMENT`. Immediately after the commit, `TemplateRefresh` records the
idempotent markers (lines 4728–4731; audited in Check 4) and then DELEGATES the entire assignment
phase with the initial-invocation arguments (lines 4734–4735):

```
    RETURN CALL ContinueTemplateRefreshAssignmentSetup(RoundContext, dispatch_envelope, TemplateID = new_TemplateID,
                     SetupRetryID = null, setup_retry_generation = 0)   # X3
```

The `SetupRetryID = null` and `setup_retry_generation = 0` arguments mark this as the initial (not
a retry) invocation. `TemplateRefresh`'s own NOTE (lines 4737–4742) restates the boundary:

> NOTE: X3: TemplateRefresh performs INITIATION ONLY — old-template closure (CloseTemplateAssignments),
> candidate construction, the TEMPLATE_REFRESH -> TEMPLATE_COMMITMENT -> ASSIGNMENT sequencing,
> TemplateCommit, and the idempotent template_refresh_setup_committed marker — then DELEGATES the
> assignment phase to ContinueTemplateRefreshAssignmentSetup. It is NEVER the retry target ...

Because the closure/construction/commit statements sit on the straight-line path BEFORE the single
`RETURN CALL` and the procedure is never the retry target (Check 3), each runs exactly once per
refresh. **PASS.**

## 3. Check 2 — `ContinueTemplateRefreshAssignmentSetup` owns only the assignment phase, its rollback, and its bounded retry; its preconditions forbid re-closing / re-constructing / re-committing — PASS

The continuation's PRECONDITIONS (lines 4748–4751) both require the committed post-`TemplateCommit`
state AND prohibit the initiation work in prose:

```
  PRECONDITIONS: round_state = ASSIGNMENT; TemplateID = TemplateID_committed;
                 template_refresh_setup_committed[TemplateID] EXISTS (X3: the old-template closure + TemplateCommit ran
                 EXACTLY once). This procedure NEVER closes the old template, constructs a candidate template, or calls
                 TemplateCommit — it owns ONLY the assignment phase, its rollback, and its bounded retry/abort.
```

`round_state = ASSIGNMENT` and `TemplateID = TemplateID_committed` mean the procedure can only run
after `TemplateCommit` has already committed and transitioned the round; there is no legal entry in
which it would need to close or commit. The body bears this out: it selects eligible miners
(`eligible <- { m : miner_state(m) in {REGISTERED, RESERVE, LOW_POWER_LISTEN} }`, line 4755),
initialises the refresh setup transaction (line 4758), creates PENDING assignments and issues
`StartWake` per miner (lines 4764–4777), calls the single `ASSIGNMENT -> HASHING` owner
`CompleteAssignmentPhase` on success (line 4785), and on any failure invokes the named
`RollbackTemplateRefreshSetup` (line 4789) followed by the bounded W8 retry-or-abort logic (lines
4793–4811). It contains no `CloseTemplateAssignments` call, no `build ... candidate_template`
statement, and no `TemplateCommit` call — consistent with its NOTE (lines 4813–4819):

> NOTE: X3: the SOLE owner of the post-TemplateCommit template-refresh assignment phase ... It NEVER
> re-closes the old template, re-builds a candidate template, or re-commits — those ran EXACTLY once
> in the initial TemplateRefresh (marked by template_refresh_setup_committed[TemplateID]).

**PASS.**

## 4. Check 3 — a `TEMPLATE_REFRESH_SETUP` `SetupRetryEvent` resumes the continuation and never `TemplateRefresh`, so a retry never repeats `CloseTemplateAssignments`, candidate construction, or `TemplateCommit` — PASS

`SetupRetryEvent` (lines 1747–1798) is kind-specific. After its stale/terminal/round-state/budget/
state-compatibility guards (lines 1753–1777) and after registering the idempotence marker (line
1777), the `TEMPLATE_REFRESH_SETUP` branch (lines 1782–1788) asserts the committed identity and
markers and CALLs the continuation — not `TemplateRefresh`:

```
    # setup_kind = TEMPLATE_REFRESH_SETUP: X3/X4 — resume ONLY the post-TemplateCommit assignment phase. The committed
    #   TemplateID must equal the refresh setup's TemplateID and its old-template-closure / new-template-commitment
    #   markers must already exist; the retry NEVER re-enters TemplateRefresh (no re-close / no re-commit).
    ASSERT TemplateID_committed = the refresh setup's TemplateID
           AND template_refresh_setup_committed[TemplateID_committed] EXISTS                # X3/X4: markers present exactly once
    RETURN CALL ContinueTemplateRefreshAssignmentSetup(RoundContext, dispatch_envelope, TemplateID = TemplateID_committed,
                     SetupRetryID = SetupRetryID, setup_retry_generation = setup_retry_generation)   # X3/X4
```

Because the retry re-enters at `ContinueTemplateRefreshAssignmentSetup` — whose body contains none
of the initiation statements (Check 2) — a retry structurally cannot repeat
`CloseTemplateAssignments`, candidate construction, or `TemplateCommit`. The handler's NOTE (lines
1791–1797) confirms: *"TEMPLATE_REFRESH_SETUP calls ContinueTemplateRefreshAssignmentSetup (NEVER
TemplateRefresh — no re-close / re-commit)."* The retry also carries the non-null `SetupRetryID` and
the advanced `setup_retry_generation`, distinguishing it from `TemplateRefresh`'s initial
`SetupRetryID = null, setup_retry_generation = 0` call. **PASS.**

## 5. Check 4 — `template_refresh_setup_committed[new_TemplateID]` is an idempotent marker keyed to the committed new `TemplateID`, set once in `TemplateRefresh` and asserted-present in both the continuation and the retry — PASS

The map is defined in the `§0.8` comment block (lines 798–802):

> `TemplateRefreshSetupID` : X3 — an idempotent identity keyed to the committed new TemplateID,
> marking that the old-template closure + candidate-template construction + TemplateCommit ran
> EXACTLY ONCE. `template_refresh_setup_committed[TemplateID]` records the markers; a
> TEMPLATE_REFRESH_SETUP retry resumes ONLY the post-TemplateCommit assignment phase
> (ContinueTemplateRefreshAssignmentSetup), never repeating CloseTemplateAssignments /
> candidate-template construction / TemplateCommit.

It is reset per round in `RoundInitialise` (line 1431):

```
    INITIALISE template_refresh_setup_committed <- empty map   # X3: per new-TemplateID marker that closure + TemplateCommit ran exactly once
```

It is SET exactly once, keyed to `new_TemplateID`, in `TemplateRefresh` immediately after the commit
(lines 4728–4731):

```
    SET TemplateRefreshSetupID <- (RoundID_current, new_TemplateID)                     # X3: idempotent identity
    SET template_refresh_setup_committed[new_TemplateID] <- refresh_setup_markers(
          RoundID = RoundID_current, old_TemplateID = old_TemplateID_snapshot,
          TemplateRefreshSetupID = TemplateRefreshSetupID)                              # X3: closure + commit happened once
```

It is asserted-present as a precondition of the continuation — *"template_refresh_setup_committed[TemplateID]
EXISTS (X3: the old-template closure + TemplateCommit ran EXACTLY once)"* (lines 4749–4750, quoted
in full in Check 2) — and asserted-present again in the retry branch before re-entry — *"AND
template_refresh_setup_committed[TemplateID_committed] EXISTS"* (line 1786, quoted in Check 3). The
marker is thus keyed to the committed new TemplateID, written once, and read (never re-written) by
both the initial delegation and every retry, giving the intended idempotence. **PASS.**

## 6. Check 5 — the continuation always exits with the committed `TemplateID` (round `HASHING`), a bounded retry seat, or a declared `RoundAbort` — never leaving `round_state = ASSIGNMENT` with no controller — PASS

The continuation's declared result type is `TemplateID | template_refresh_retry_seated |
round_aborted` (line 4812). Every exit path realises exactly one of those and hands the round to a
defined controller:

- **Success — committed TemplateID, round `HASHING`.** On `assignment_phase_completed` from the sole
  `ASSIGNMENT -> HASHING` owner `CompleteAssignmentPhase`, line 4786:
  `IF disp = assignment_phase_completed: RETURN TemplateID     # success: round now HASHING`.
- **Rollback failure — declared abort.** Lines 4790–4792: on `rollback_failed(rr)`,
  `RETURN CALL RoundAbort(..., reason = template_refresh_rollback_failed, ...)`.
- **State-incompatible rollback — declared abort.** Lines 4794–4796: if the rollback routed a miner
  to `OFFLINE`, `RETURN CALL RoundAbort(..., reason = template_refresh_failed(setup_reason), ...)`.
- **Budget exhausted — declared abort.** Lines 4797–4799: at/over `maximum_setup_retries`,
  `RETURN CALL RoundAbort(..., reason = template_refresh_retries_exhausted(setup_reason), ...)`.
- **Within budget and horizon — bounded retry seat.** Lines 4800–4809: advance the generation, mint
  `SetupRetryID = (RoundID_current, TEMPLATE_REFRESH_SETUP, g)`, `ScheduleEvent(... SetupRetryEvent
  ... setup_kind = TEMPLATE_REFRESH_SETUP ...)`, and
  `IF r = scheduled(...): RETURN template_refresh_retry_seated(srid, setup_reason)`.
- **Otherwise (beyond horizon / not scheduled) — declared abort.** Lines 4810–4811:
  `RETURN CALL RoundAbort(..., reason = template_refresh_failed(setup_reason), ...)`.

The NOTE closes the argument (lines 4818–4819): *"Success returns the committed TemplateID (round
HASHING); every other exit is a bounded retry seat or a declared RoundAbort — the round is never
left in ASSIGNMENT with no controller."* The retry seat is itself safe: `SetupRetryEvent`'s own
guards and NOTE (lines 1789–1797) guarantee *"NEVER leaving ASSIGNMENT with no controller"* — an
over-budget or state-incompatible or wrong-phase retry `RoundAbort`s rather than stranding the
round, and a stale/terminal dispatch is a no-op that needs no controller. No path returns control
while leaving `round_state = ASSIGNMENT` uncontrolled. **PASS.**

## 7. Test-vector linkage (TV202)

The blocking test vector for this correction is **TV202**, carried by requirement **R177** in
`STAGE_01_TRACEABILITY_MATRIX.csv` (line 178):

> TV202 a TEMPLATE_REFRESH_SETUP retry runs ContinueTemplateRefreshAssignmentSetup and repeats no
> CloseTemplateAssignments or TemplateCommit

TV202 targets the file `STAGE_01X_SEMANTIC_TEST_VECTORS` against the named procedures
`ContinueTemplateRefreshAssignmentSetup` and `SetupRetryEvent` (among the R177 procedure list),
under invariants including `I16`. It is exactly the property proven by Checks 3–4 above: the
`TEMPLATE_REFRESH_SETUP` branch of `SetupRetryEvent` (lines 1782–1788) re-enters the continuation
(never `TemplateRefresh`), and the continuation's body (lines 4744–4819) contains no
`CloseTemplateAssignments` and no `TemplateCommit`. TV202's status in the matrix is **SPECIFIED**;
the Stage-1X semantic-test-vector file named as its target is the outstanding R177 deliverable
(paper vector specified, execution deferred to Stage 2 per the matrix). The corresponding X3
requirement row is **R171** (line 172), which enumerates the same split and names
`TemplateRefresh; ContinueTemplateRefreshAssignmentSetup; SetupRetryEvent; CloseTemplateAssignments;
TemplateCommit; CompleteAssignmentPhase` under `I16; I18b`.

## 8. Cross-document consistency

The X3 mechanism is stated consistently across the four documents, and the call-graph is extended
by exactly the one new procedure:

| Source | Statement of the X3 split | Consistent |
|---|---|---|
| Pseudocode (`STAGE_01_PROTOCOL_PSEUDOCODE.md`) | `TemplateRefresh` (4708–4742) initiates once + delegates (4734–4735); `ContinueTemplateRefreshAssignmentSetup` (4744–4819) owns only the assignment phase (4748–4751); `SetupRetryEvent` TEMPLATE_REFRESH_SETUP branch (1782–1788) resumes the continuation; marker set once (4728–4731), reset per round (1431), asserted in both (4749–4750, 1786) | Authoritative |
| Round-SM §3.10b (`STAGE_01_ROUND_STATE_MACHINE.md`, 696–701) | X3 block: `TemplateRefresh` does closure + construction + `TemplateCommit` + idempotent marker, then delegates; retry resumes `ContinueTemplateRefreshAssignmentSetup` only, never repeating `CloseTemplateAssignments` / construction / `TemplateCommit` | ✔ matches |
| Terminology (`STAGE_01_TERMINOLOGY.md`, 877–884) | `ContinueTemplateRefreshAssignmentSetup (X3)` owns only selection/creation, `StartWake`, `CompleteAssignmentPhase`, rollback, bounded retry-or-abort; `SetupRetryEvent(TEMPLATE_REFRESH_SETUP)` calls it and never re-enters `TemplateRefresh`; `template_refresh_setup_committed[new_TemplateID]` records that closure + construction + commit already occurred | ✔ matches |
| Invariant I16 (`STAGE_01_INVARIANT_CATALOGUE.md`, 338–341) | **X3/X4:** template-refresh initiation (`TemplateRefresh`) is split from the post-commit assignment retry (`ContinueTemplateRefreshAssignmentSetup`); a retry never repeats the old-template closure or `TemplateCommit`; an over-budget retry aborts rather than stranding the round | ✔ matches |

**Call-graph delta.** X3 adds exactly one procedure, `ContinueTemplateRefreshAssignmentSetup`, on
the edge previously internal to `TemplateRefresh`: the new call-graph is
`TemplateRefresh -> ContinueTemplateRefreshAssignmentSetup -> { CreatePendingAssignment, StartWake,
CompleteAssignmentPhase, RollbackTemplateRefreshSetup, RoundAbort, ScheduleEvent(SetupRetryEvent) }`,
and `SetupRetryEvent(TEMPLATE_REFRESH_SETUP) -> ContinueTemplateRefreshAssignmentSetup`.
`TemplateRefresh` retains its direct edges to `CloseTemplateAssignments` and `TemplateCommit`, which
the continuation and the retry no longer reach.

**One non-blocking descriptive-annotation observation.** The executable `SetupRetryEvent` procedure
body (lines 1747–1798) — the authoritative dispatch — correctly routes `TEMPLATE_REFRESH_SETUP` to
`ContinueTemplateRefreshAssignmentSetup` and never to `TemplateRefresh`. However, the event-envelope
descriptor table row for `SetupRetryEvent` at line 563 still carries a V8-era parenthetical,
*"(V8: re-invokes PrepareParticipantsForNewRound / TemplateRefresh at a strictly-later event_time
after a rolled-back setup; stale-guarded on RoundID)"*, naming `TemplateRefresh` as a re-invocation
target. This is a descriptive annotation in a tabular envelope descriptor, not executable dispatch;
it does not affect any of Checks 1–5, which read the procedure bodies. It is recorded here as a
descriptive-text follow-up (refresh the line-563 parenthetical to
`ContinueTemplateRefreshAssignmentSetup`), not as a defect in the X3 mechanism.

**A1 baseline.** X3 is a control-flow re-partition between two procedures; it introduces no census,
residency, difficulty, or energy change. The A1 continuous full-participation baseline of
`8.420833333 kWh` is unchanged.

## 9. Result

**PASS** — X3 is fully realised: `TemplateRefresh` performs old-template closure + candidate
construction + `TemplateCommit` exactly once and delegates via `RETURN CALL
ContinueTemplateRefreshAssignmentSetup(... SetupRetryID = null, setup_retry_generation = 0)`; the
continuation owns only the assignment phase, its rollback, and its bounded retry (preconditions
forbidding re-close / re-construct / re-commit); a `TEMPLATE_REFRESH_SETUP` `SetupRetryEvent`
resumes the continuation and never `TemplateRefresh`; the idempotent
`template_refresh_setup_committed[new_TemplateID]` marker is set once and asserted-present in both;
every continuation exit yields the committed TemplateID (round `HASHING`), a bounded retry seat, or a
declared `RoundAbort`, never leaving `ASSIGNMENT` uncontrolled — consistent across pseudocode,
round-SM §3.10b, terminology, and invariant I16, with TV202 (R177) as the specified blocking vector
and the A1 baseline `8.420833333 kWh` unchanged (one non-blocking line-563 descriptor-text
follow-up noted).
