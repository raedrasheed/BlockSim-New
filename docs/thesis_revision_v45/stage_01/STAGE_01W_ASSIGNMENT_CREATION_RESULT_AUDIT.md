# Stage 1W — Assignment Creation Result Audit (W7)

## 1. Scope

This audit documents correction **W7** of the Stage-1W revision to the PoCol formal
specification (the idle policy within PoCol): *handle the assignment-constructor failure before
recording anything*. The correction concerns the single shared PENDING-head constructor,
`CreatePendingAssignment`, and the complete set of procedures that invoke it directly:
`PrepareParticipantsForNewRound`, `TemplateRefresh`, `RangeAssignFromPlan`,
`RangeReassignFromPlan`, `ReserveActivateFromPlan`, and `AdversarialParticipationChangeEvent`
(its `LOW_POWER_LISTEN` `T10` re-entry branch).

The correction establishes that `CreatePendingAssignment` returns EXACTLY one of two structured
results — `assignment_created(assignment)` or `assignment_creation_failed(reason)` — and that
every caller branches on that result BEFORE it reads an `AssignmentID`, sets lease fields, or
adds the object to a transaction record. The intended consequence is a global property: no
transaction record ever holds an `AssignmentID` for an object the constructor did not create.

The audit is descriptive and documentation-only. It reads the current specification text and
records the state of the corrected contract; it modifies no protocol file. Every claim below is
grounded in the current text of

- `STAGE_01_PROTOCOL_PSEUDOCODE.md` (the normative pseudocode; line references re-established by
  grep against the current file, not inherited from an earlier revision),

with traceability confirmed against `STAGE_01_ROUND_STATE_MACHINE.md`,
`STAGE_01_TERMINOLOGY.md`, `STAGE_01_INVARIANT_CATALOGUE.md`, `STAGE_01W_SEMANTIC_TEST_VECTORS.md`,
and `STAGE_01_TRACEABILITY_MATRIX.csv`.

The A1 energy-accounting baseline (`8.420833333 kWh`,
`STAGE_01_ENERGY_MODEL_SPECIFICATION.md` line 29) is unaffected by this correction and is
preserved unchanged; W7 is a result-contract / control-flow correction with no energy semantics.

## 2. The defect (pre-W7 state)

Before W7 the constructor returned a bare assignment object `A`. Success and failure were not
distinguished in the return type: the procedure was written to build the PENDING head and return
`A`, with the disjointness / custody / coverage / provenance preconditions expressed only as
*preconditions* rather than as an executable guard that produces a declared failure value. Two
faults followed from this shape:

1. **Failure had no first-class representation.** Because the sole return was the object itself,
   a precondition that no longer held at construction time (for example, a concurrent same-time
   mutation that invalidated the `I1` disjointness of the range) could only surface as an uncaught
   assertion or — worse — as a *partially built* object returned as if valid. There was no
   `assignment_creation_failed(reason)` a caller could branch on.

2. **Callers assumed success and read `AssignmentID`.** With a bare `A`, a caller had no result to
   test, so the natural coding read `AssignmentID(A)`, set `lease_start`/`lease_expiry`, and added
   the object to its setup transaction (`participant_setup_txn` / `refresh_setup_txn`) or returned
   a structured success — all *before* any check that the object was actually created. A rejected
   construction could therefore leave an `AssignmentID` (and a lease, and a transaction entry) for
   an object that either did not exist or existed only partially.

W7 withdraws the bare `A` return and replaces it with an explicit two-alternative result union
plus an executable guard, and it rewrites every caller to branch on that union before any
recording. The pseudocode NOTE records the withdrawal in terms: *"The earlier bare `A` return is
WITHDRAWN."* (`STAGE_01_PROTOCOL_PSEUDOCODE.md` line 1288).

## 3. The corrected constructor: result union + executable guard

`CreatePendingAssignment` is defined at `STAGE_01_PROTOCOL_PSEUDOCODE.md` line 1238. Its EFFECTS
open with the W7 result contract (lines 1244–1249):

```
    # W7: EXPLICIT CONSTRUCTOR RESULT. This constructor either creates the PENDING head and returns
    #     assignment_created(assignment), or creates NOTHING and returns assignment_creation_failed(reason). The
    #     preconditions above are RE-CHECKED here as an executable guard (a concurrent same-time mutation may have
    #     invalidated them), and a violation is a DECLARED failure — never an uncaught assertion and never a partially
    #     built object. Every caller MUST branch on this result BEFORE reading AssignmentID, setting lease fields, or
    #     adding the object to any transaction record.
```

The **executable guard** re-checks the disjointness / custody / coverage / provenance
preconditions and rejects with the failure result, creating nothing (lines 1250–1253):

```
    IF range is NOT disjoint from all valid active assignments (I1)
       OR custody_status(range) = completed OR coverage_state(range) = searched
       OR (assignment_origin = REASSIGNED AND (source_assignment = null OR reason is NOT a permitted reassignment reason)):
      RETURN assignment_creation_failed(reason = overlap_or_custody_or_provenance_violation)   # W7: nothing created
```

Only when the guard passes are the head fields created, the ledger appended, and the **single
success disposition** returned (lines 1264–1283, terminating in):

```
    APPEND A to assignment_ledger                                        # supports I8a
    RETURN assignment_created(A)                                         # W7: the ONLY success disposition
```

The **RETURNS union** is stated once and matches both branches exactly (line 1284):

```
  RETURNS: assignment_created(assignment) | assignment_creation_failed(reason)   # W7: one explicit constructor result
```

and the closing NOTE (lines 1285–1288) restates the contract and records the withdrawal of the
old return:

```
  NOTE: W7: the constructor returns EXACTLY assignment_created(assignment) (the head was built and ledgered) or
        assignment_creation_failed(reason) (the executable I1/custody/coverage/provenance guard rejected it and NOTHING
        was created). No caller may read AssignmentID, set lease fields, or add the object to a transaction record
        before branching on this result. The earlier bare `A` return is WITHDRAWN.
```

The guard is an *early return that builds nothing*: it precedes the `CREATE assignment version A`
statement (line 1264) and the `APPEND A to assignment_ledger` (line 1282), so on the failure path
no `AssignmentID`, no lineage, and no ledger entry is minted. This is the "creates NOTHING"
property the callers rely on.

## 4. Caller table

There are exactly six direct call sites of `CreatePendingAssignment` in the pseudocode (grep of
`SET cr <- CALL CreatePendingAssignment` and `CALL CreatePendingAssignment`: lines 1575, 1867,
2282, 3035, 3866, 4635). Every one is immediately followed by an
`IF cr is assignment_creation_failed(...)` branch, and the success value is read only through
`SET <var> <- cr.assignment` *after* that branch. The table below records, for each caller, the
call-site line, the guard line, the first success-read line, whether the branch precedes any
`AssignmentID` / lease / transaction access, and the disposition taken on failure.

| # | Caller (procedure) | Call site | Failure branch | Success read (`… <- cr.assignment`) | Branch precedes any `AssignmentID`/lease/txn access? | Failure disposition |
|---|---|---|---|---|---|---|
| 1 | `PrepareParticipantsForNewRound` (shared branch) | line 1575 | line 1577 `IF cr is assignment_creation_failed(reason)` | line 1580 `SET a <- cr.assignment` | **Yes.** Lines 1581–1582 (`lease_start`/`lease_expiry`, `ADD AssignmentID(a) to participant_setup_txn.created_assignments`) are unreachable on failure — the `CONTINUE` at 1579 skips them. | `SET participant_setup_error <- assignment_creation_failed(reason)` then `CONTINUE` (line 1578). The loop guard at 1538 (`IF participant_setup_error != null: BREAK`) mints no further work; the round takes the named `RollbackParticipantSetup` + W8 retry/abort path (lines 1589–1623). |
| 2 | `TemplateRefresh` | line 4635 | line 4637 `IF cr is assignment_creation_failed(reason)` | line 4639 `SET assignment_m <- cr.assignment` | **Yes.** The explicit transaction writes (line 4641 `ADD AssignmentID(assignment_m) to refresh_setup_txn.created_assignments`) and lease writes (4642–4643) follow the success read; the `CONTINUE` at 4638 skips them. | `SET refresh_setup_error <- assignment_creation_failed(reason) ; CONTINUE` (line 4638). Loop guard at 4632 BREAKs; `CompleteAssignmentPhase` is NOT called (4652); `RollbackTemplateRefreshSetup` + W8 retry/abort runs (4654–4689). |
| 3 | `RangeAssignFromPlan` | line 1867 | line 1869 `IF cr is assignment_creation_failed(reason)` | line 1871 `SET assignment <- cr.assignment` | **Yes.** The `ASSERT … = AssignmentID`-adjacent spec check (1873–1875), lease writes (1876–1877), and `StartWake` (1881) all follow the success read; the failure branch returns at 1870. | `RETURN range_assign_creation_failed(reason = reason)` (line 1870) — "nothing created; no AssignmentID exists". |
| 4 | `RangeReassignFromPlan` | line 3866 | line 3868 `IF cr is assignment_creation_failed(reason)` | line 3870 `SET assignment <- cr.assignment` | **Yes.** Spec asserts (3871–3873), lease writes (3874–3875), and `StartWake` (3878) follow the success read; the failure branch returns at 3869. | `RETURN range_reassign_creation_failed(reason = reason)` (line 3869) — "nothing created; no AssignmentID exists". |
| 5 | `ReserveActivateFromPlan` | line 3035 | line 3037 `IF cr is assignment_creation_failed(cf)` | line 3039 `SET assignment <- cr.assignment` | **Yes.** Lease writes (3040–3041) and `StartWake` (3043) follow the success read; the failure branch returns at 3038. | `RETURN reserve_activation_failed_before_mutation(reason = cf)` (line 3038) — "constructor rejected; nothing to roll back". |
| 6 | `AdversarialParticipationChangeEvent` (`T10` re-entry) | line 2282 | line 2284 `IF cr is assignment_creation_failed(reason)` | line 2286 `SET fresh <- cr.assignment` | **Yes.** Lease writes (2287–2288) and `StartWake` (2289) follow the success read; the failure branch returns at 2285. | `RETURN participation_reentry_creation_failed(MinerID, reason)` (line 2285) — "nothing created; no wake". |

Notes on the individual entries:

- **Shared branch (row 1).** `PrepareParticipantsForNewRound` factors the per-miner spec
  computation (a `SWITCH miner_state(m)` over `REGISTERED` / `RESERVE` / `LOW_POWER_LISTEN` /
  `OFFLINE` / `DISQUALIFIED`, lines 1542–1571) *before* the single shared
  `SET cr <- CALL CreatePendingAssignment(...)` + `IF cr is assignment_creation_failed(reason)`
  guard (lines 1575–1580). Every activation path therefore builds and branches through one
  W7-guarded site, not per-`CASE` duplicates. The NOTE at lines 1629–1635 records this:
  *"every CreatePendingAssignment result is inspected BEFORE any AssignmentID/lease/transaction
  access; a creation failure sets participant_setup_error and mints no further work (the loop
  BREAKs)."*
- **`T10` re-entry (row 6).** The `LOW_POWER_LISTEN` /
  `RANGE_EXHAUSTED`-or-`ASSIGNMENT_REVOKED` case builds a fresh `ORIGINAL` PENDING head *directly*
  via `CreatePendingAssignment` (line 2282) under the legal `T10` edge, so it is a direct caller.
  The `REGISTERED` / `RESERVE` (line 2238) and `OFFLINE` (line 2248) cases of the same procedure
  instead route through `RangeAssign → RangeAssignFromPlan`, so their W7 branch is discharged
  inside row 3; the comment at line 2237 documents that indirection
  (*"RangeAssign … builds a PENDING via CreatePendingAssignment and StartWake"*). The
  `VALID_SOLUTION_VERIFIED` case (line 2257) resumes a paused head via `ResumeFromPause` and
  constructs nothing.

## 5. No orphan `AssignmentID` in any transaction record

The W7 property to be shown is: *no transaction record contains an `AssignmentID` for an object
that was not created.* The argument is compositional over the two ways an `AssignmentID` can enter
a transaction record.

**(a) The constructor mints an `AssignmentID` only on the created path.** The `AssignmentID` field
is assigned inside `CREATE assignment version A` (line 1265), which is reached only after the guard
at lines 1250–1253 passes. On the failure path the guard's `RETURN assignment_creation_failed(...)`
(line 1253) executes before any `CREATE`, so `assignment_creation_failed(reason)` carries **no**
`AssignmentID` — there is no identifier for a caller to record.

**(b) Every transaction write is dominated by the success branch.** The only two procedures that
add an `AssignmentID` to a transaction record are the two setup-transaction owners:

- `PrepareParticipantsForNewRound`:
  `ADD AssignmentID(a) to participant_setup_txn.created_assignments` (line 1582), reached only
  after `SET a <- cr.assignment` (line 1580), which is reached only when the failure branch (1577)
  did not fire.
- `TemplateRefresh`:
  `ADD AssignmentID(assignment_m) to refresh_setup_txn.created_assignments` (line 4641), reached
  only after `SET assignment_m <- cr.assignment` (line 4639), which is reached only when the
  failure branch (4637) did not fire (the `CONTINUE` at 4638 otherwise skips the loop body).

The plan-bound and re-entry callers (rows 3–6) hold no setup transaction; each returns its
`*_creation_failed` disposition on the failure branch (lines 1870, 3869, 3038, 2285) *before* any
`AssignmentID` read, so none records an identifier for a non-created object either. `cr.assignment`
is dereferenced only inside the success arm (`cr = assignment_created(...)`), so `AssignmentID(...)`
is never evaluated against the failure alternative.

Because (a) the failure result carries no `AssignmentID` and (b) every transaction insertion is
control-flow-dominated by the `assignment_created` success arm, no `created_assignments` set — and
no downstream rollback record derived from it — can ever contain an `AssignmentID` for an object
the constructor rejected. This is the property `I18b`/`I1` and R166 require of the setup and
plan-commit transactions.

**Grep confirmations (current file).**

- Unqualified failure test: `grep -n "= creation_failed("` over `STAGE_01_PROTOCOL_PSEUDOCODE.md`
  — **no matches**. Every failure test is qualified: the constructor result is tested as
  `assignment_creation_failed(...)` (lines 1577, 1869, 2284, 3037, 3868, 4637), and the plan-commit
  consumer distinguishes the delegated dispositions `range_reassign_creation_failed` /
  `range_assign_creation_failed` (line 3586). There is no bare `creation_failed` predicate anywhere.
- No unbranched success read: each of the six `CALL CreatePendingAssignment` sites (1575, 1867,
  2282, 3035, 3866, 4635) is immediately followed (next executable line) by
  `IF cr is assignment_creation_failed(...)`, and the first `cr.assignment` read (1580, 1871, 2286,
  3039, 3870, 4639) and the first `AssignmentID`/lease write occur only inside the success arm.
  No site reads `AssignmentID` or sets a lease field between the `CALL` and its guard.

## 6. Mapping to TV195

`STAGE_01W_SEMANTIC_TEST_VECTORS.md` line 122 defines **TV195 — "A CreatePendingAssignment failure
creates nothing (W7)."** The vector exercises exactly the W7 contract audited here:

> **Setup.** A caller (e.g. `PrepareParticipantsForNewRound`, `RangeAssignFromPlan`, or
> `ReserveActivateFromPlan`) calls `CreatePendingAssignment`, whose executable
> I1/custody/coverage/provenance guard fails.
> **Steps.** (1) `CreatePendingAssignment` returns `assignment_creation_failed(reason)` and creates
> NO assignment, ledger entry, or lineage. (2) The caller branches on the result BEFORE any
> `AssignmentID` access: it sets no lease fields, seats no `StartWake`, and adds no `AssignmentID`
> to any transaction record (it sets its `*_setup_error` / returns a `*_creation_failed`
> disposition).
> **Expected.** No lease field, `AssignmentID`, wake, or transaction entry exists for the
> non-created object. A1 preserved.

Step (1) corresponds to §3 (the executable guard at lines 1250–1253 returning
`assignment_creation_failed`, with `CREATE`/`APPEND` unreached). Step (2) and the Expected clause
correspond to §4 (each caller's branch-before-access) and §5 (no orphan `AssignmentID` in any
transaction record). The vector's coverage-map row confirms the mapping: TV195 → correction W7 →
primary procedures `CreatePendingAssignment` (+ every caller)
(`STAGE_01W_SEMANTIC_TEST_VECTORS.md` line 175). TV195 is a control-flow / result-contract check
that alters no energy or time accounting, so it preserves the A1 baseline.

## 7. Traceability

| Anchor | Location | What it establishes for W7 |
|---|---|---|
| Round state machine §3.10a addendum, **W7** | `STAGE_01_ROUND_STATE_MACHINE.md` §3.10a (heading line 633); W7 clause lines 670–673 | "**W7 (assignment-creation result).** `CreatePendingAssignment` returns `assignment_created(assignment)` \| `assignment_creation_failed(reason)`; every caller branches on the result BEFORE reading `AssignmentID`, setting lease fields, or adding the object to a transaction record. No transaction record contains an `AssignmentID` for an object that was not created." Matches the constructor union (§3) and the caller discipline (§4). |
| Terminology addendum, **Assignment-creation result (W7)** | `STAGE_01_TERMINOLOGY.md` lines 848–850 | "**Assignment-creation result (W7).** `CreatePendingAssignment` returns `assignment_created(assignment)` \| `assignment_creation_failed(reason)`; every caller branches before any `AssignmentID` access, lease update, or transaction-record entry." Fixes the two-alternative return-type vocabulary used throughout §§3–5. |
| Invariant catalogue, **I16 — W6/W7 clause** | `STAGE_01_INVARIANT_CATALOGUE.md` I16 (heading line 284); W6/W7 clause lines 327–331 | "**W6/W7 (declared results):** `ApplyMinerStateTransition` returns exactly one of {transition_applied, duplicate_suppressed, illegal_stale_source, illegal_transition} and `CreatePendingAssignment` returns exactly one of {assignment_created, assignment_creation_failed}; a wake is retained (and an `AssignmentID`/lease/transaction entry recorded) ONLY on the applied/created result." Ties W7's created-only recording rule to the same "declared results, no silent repair" invariant that governs W6, and situates it beside the W1/W2 legal-rollback clause (lines 322–327) it precedes. |
| Traceability matrix, **R166** | `STAGE_01_TRACEABILITY_MATRIX.csv` line 167 | Requirement R166: "Handle assignment-constructor failure before recording (W7); `CreatePendingAssignment` returns `assignment_created(assignment)` or `assignment_creation_failed(reason)` and every caller (`PrepareParticipantsForNewRound` `TemplateRefresh` `RangeAssignFromPlan` `RangeReassignFromPlan` `ReserveActivateFromPlan` `AdversarialParticipationChangeEvent`) branches before reading `AssignmentID` setting lease fields or adding the object to a transaction record so no transaction record holds an `AssignmentID` for an object that was not created." State/event set: the six procedures above + `CreatePendingAssignment`; invariants `I1; I18b`; threat "a caller that reads `AssignmentID` or records a transaction entry for an assignment the constructor did not create"; status **SPECIFIED**. R168 additionally registers TV195 as the blocking test vector for W7 (line 169). |

The four anchors are mutually consistent and consistent with the pseudocode read in §§3–5: a
single constructor returning exactly `assignment_created(assignment) | assignment_creation_failed(reason)`,
an executable guard that builds nothing on rejection, and six callers each of which branches on
that result before any `AssignmentID` / lease / transaction access — with the bare-`A` return
provably withdrawn and no unqualified `creation_failed` predicate remaining in the current text.
