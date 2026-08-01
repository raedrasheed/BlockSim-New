# Stage 1X — Assignment-Creation Reachability Audit (X6)

## 1. Scope

This audit documents correction **X6** of the Stage-1X revision to the PoCol formal
specification (the idle policy within PoCol): *make the `assignment_creation_failed` disposition
legally REACHABLE by a conforming caller*. The correction concerns the single shared PENDING-head
constructor `CreatePendingAssignment` (`STAGE_01_PROTOCOL_PSEUDOCODE.md` §0.11, procedure at
line 1272). It moves the runtime-varying protocol-validity predicates OUT of that procedure's
`PRECONDITIONS` (leaving only a type/shape prerequisite) and INTO the executable guard already
present in `EFFECTS`, so that a predicate violation is a *declared* `assignment_creation_failed`
result rather than an undefined-behaviour precondition breach.

The audit is descriptive and documentation-only. It reads the current specification text and
records the state of the corrected contract; it modifies no protocol file. Every line reference
below was re-established by direct read against the current files, not inherited from an earlier
revision. Grounding sources:

- `STAGE_01_PROTOCOL_PSEUDOCODE.md` (the normative pseudocode; `CreatePendingAssignment`
  lines 1272–1332 and its direct callers),

with traceability confirmed against `STAGE_01_ROUND_STATE_MACHINE.md` (§3.10b, X6),
`STAGE_01_INVARIANT_CATALOGUE.md` (I16 Stage-1X block; I1), `STAGE_01_TERMINOLOGY.md`
("Reachable `assignment_creation_failed` (X6)"), and `STAGE_01_TRACEABILITY_MATRIX.csv`
(rows R174, R177).

The A1 energy-accounting baseline (`8.420833333 kWh`,
`STAGE_01_ENERGY_MODEL_SPECIFICATION.md` line 29) is unaffected and is preserved unchanged. X6 is
a precondition-vs-guard placement / reachability correction with no energy or time semantics.

## 2. The defect X6 corrects (why placement matters)

A precondition is a *caller obligation*: a well-formed caller must establish it before the call,
and calling with the precondition unmet is undefined behaviour, not a defined failure. If a
runtime-varying predicate — one whose truth can change between a caller's own pre-check and the
constructor body (for example a concurrent same-time mutation that makes the range overlap another
valid active assignment, violating I1) — is stated as a *precondition*, then:

1. `assignment_creation_failed` becomes **unreachable** for a conforming caller. A caller that has
   satisfied every precondition can only observe success, so the failure disposition is dead code
   that the W7 result-contract (every caller branches on the result) can never exercise.
2. A *real* overlap / custody / coverage / provenance / epoch violation that arises after the
   caller's pre-check is a **precondition breach = undefined behaviour**, not the declared
   `assignment_creation_failed(reason)`. The specification would then have no defined meaning for
   the exact race the W7 branch exists to handle.

X6 removes this contradiction by classifying the predicates by *stability*: only the type/shape
prerequisite (which a caller can always guarantee) stays a precondition; the runtime-varying
predicates move to the executable guard that returns a declared value.

## 3. Verification

### 3.1 PASS — PRECONDITIONS reduced to a type/shape prerequisite only, with the explicit "DELIBERATELY NOT preconditions" note

`CreatePendingAssignment`'s `PRECONDITIONS` block (`STAGE_01_PROTOCOL_PSEUDOCODE.md`
lines 1274–1280) reads, verbatim:

```
  PRECONDITIONS: assignment_origin in {ORIGINAL, REASSIGNED}   # X6/G2: TYPE/SHAPE prerequisite ONLY (RENEWED is not
                 #   constructed here). The runtime-VARYING protocol-validity predicates — I1 disjointness;
                 #   custody_status(range) != completed; coverage_state(range) != searched; REASSIGNED source/provenance
                 #   validity; current RoundID/TemplateID validity — are DELIBERATELY NOT preconditions: they are
                 #   evaluated in the executable guard below and a violation returns assignment_creation_failed. So a
                 #   conforming caller can exercise EITHER result (assignment_created / assignment_creation_failed)
                 #   without ever violating a precondition (X6; TV204).
```

Finding: the only constraint the precondition now imposes is the type/shape prerequisite
`assignment_origin in {ORIGINAL, REASSIGNED}` (RENEWED is explicitly excluded — renewal is the sole
province of `RenewAssignment` (F7/G2), not this constructor). The note that follows names, one by
one, the runtime-varying predicates that are **DELIBERATELY NOT** preconditions:

- `I1` disjointness (range overlap);
- `custody_status(range) != completed`;
- `coverage_state(range) != searched`;
- `REASSIGNED` source/provenance validity;
- current `RoundID`/`TemplateID` validity (epoch).

This matches the X6 mandate exactly: the moved predicates are the runtime-varying set, and the
retained precondition is type/shape only. **PASS.**

### 3.2 PASS — the moved predicates are evaluated in the executable guard and yield `assignment_creation_failed`

The guard at the head of `EFFECTS` (`STAGE_01_PROTOCOL_PSEUDOCODE.md` lines 1288–1292) evaluates
exactly those predicates and, on any violation, returns the failure disposition creating nothing:

```
    IF range is NOT disjoint from all valid active assignments (I1)
       OR custody_status(range) = completed OR coverage_state(range) = searched
       OR RoundID(RoundContext) != RoundID_current OR (a committed TemplateID is required AND TemplateID_committed is absent)   # X6: epoch validity
       OR (assignment_origin = REASSIGNED AND (source_assignment = null OR reason is NOT a permitted reassignment reason)):
      RETURN assignment_creation_failed(reason = overlap_or_custody_or_provenance_or_epoch_violation)   # W7/X6: nothing created
```

Finding: every predicate named in the "DELIBERATELY NOT preconditions" note (§3.1) appears as a
disjunct of this guard —

- I1 disjointness → `range is NOT disjoint from all valid active assignments (I1)`;
- custody → `custody_status(range) = completed`;
- coverage → `coverage_state(range) = searched`;
- epoch → `RoundID(RoundContext) != RoundID_current OR (a committed TemplateID is required AND TemplateID_committed is absent)`;
- REASSIGNED source/provenance → `assignment_origin = REASSIGNED AND (source_assignment = null OR reason is NOT a permitted reassignment reason)`.

A true disjunct returns `assignment_creation_failed(reason = overlap_or_custody_or_provenance_or_epoch_violation)`
and the annotation `# W7/X6: nothing created` confirms no partial object, ledger entry, or lineage
is produced. The complementary success path is `RETURN assignment_created(A)` (line 1322,
annotated `# W7: the ONLY success disposition`), reached only after the guard passes and the head is
built and appended to `assignment_ledger` (line 1321). The declared return union
`assignment_created(assignment) | assignment_creation_failed(reason)` (line 1323) and the closing
`NOTE` (lines 1324–1327) confirm these are the two — and only two — results. **PASS.**

### 3.3 PASS — `assignment_creation_failed` is reachable by a well-formed caller, and that reachability is now exercisable rather than dead

Because the runtime-varying predicates live in the guard and no longer in the preconditions, a
caller that satisfies the *sole* precondition (`assignment_origin in {ORIGINAL, REASSIGNED}`) is
fully conforming whether the guard passes or fails. Either result —
`assignment_created(A)` or `assignment_creation_failed(reason)` — is therefore obtainable **without
violating any precondition**. The success path is not the unique conforming outcome; the failure
disposition is legally reachable.

Why this matters concretely: the W7 result-contract already requires every direct caller of
`CreatePendingAssignment` to branch on the constructor result *before* reading `AssignmentID`,
setting lease fields, or recording the object in a transaction. Those failure branches already
exist in the current pseudocode. Under the pre-X6 (predicate-as-precondition) shape they were
**dead** — unreachable for a conforming caller. Under X6 the same branches become **exercisable**:
a genuine runtime violation (e.g. a concurrent same-time mutation that makes the range overlap after
the caller's own pre-check) now flows through the guard as the declared `assignment_creation_failed`
value into the caller's existing branch, rather than manifesting as an undefined-behaviour
precondition breach.

The current text carries these live W7-era failure branches at every direct call site (verified by
read of `STAGE_01_PROTOCOL_PSEUDOCODE.md`):

- `PrepareParticipantsForNewRound` — lines 1617–1620;
- `TemplateRefresh` — line 1937;
- the reserve / plan-bound seat path — line 2353;
- `RangeAssignFromPlan` / `RangeReassignFromPlan` / `ReserveActivateFromPlan` seat sites —
  lines 3111, 3974;
- `ContinueTemplateRefreshAssignmentSetup` refresh-seat loop — lines 4766–4768.

A representative site, `PrepareParticipantsForNewRound` (lines 1615–1620), shows the branch that X6
makes reachable:

```
      SET cr <- CALL CreatePendingAssignment(RoundContext, m, spec.range,
                      assignment_origin = spec.origin, source_assignment = spec.source, reason = spec.rr)   # F4/W7
      IF cr is assignment_creation_failed(reason):
        SET participant_setup_error <- assignment_creation_failed(reason)   # W7: nothing created; setup failed
        CONTINUE
      SET a <- cr.assignment                                              # W7: cr = assignment_created(a) — safe to read now
```

The `IF cr is assignment_creation_failed(reason)` arm is precisely the branch that was dead under a
predicate-as-precondition constructor and is exercisable under X6. **PASS.**

### 3.4 PASS — TV195 reachability preserved/updated; TV206 exercises an overlap violation via the guard

`STAGE_01X_SEMANTIC_TEST_VECTORS.md` does not yet exist in the stage directory; the X6 test-vector
mapping is therefore grounded in the current pseudocode guard (§3.2) and the traceability matrix.

- **TV195 (W7) preserved / updated.** TV195 — "A CreatePendingAssignment failure creates nothing"
  (`STAGE_01W_SEMANTIC_TEST_VECTORS.md` line 122; coverage map line 175) exercises the failure
  disposition and the caller's no-partial-state guarantee. Traceability row R174 (X6,
  `STAGE_01_TRACEABILITY_MATRIX.csv` line 175) records that under X6 "TV195 is updated so the
  failure disposition is reachable rather than precondition-excluded" — i.e. TV195's failure
  scenario, previously exercisable only as a precondition breach, is preserved and re-grounded as a
  guard-reachable declared result.
- **TV206 (X6) overlap via the guard.** Traceability row R177 (`STAGE_01_TRACEABILITY_MATRIX.csv`
  line 178) specifies "TV206 a CreatePendingAssignment overlap violation returns
  assignment_creation_failed via the guard not a precondition breach", assigned to the pending
  `STAGE_01X_SEMANTIC_TEST_VECTORS` set. TV206 directly exercises the I1-disjointness disjunct of
  the guard quoted in §3.2 and confirms the declared-failure-not-UB reachability that X6
  establishes.

Both vectors are control-flow / result-contract checks over named procedures; neither alters energy
or time accounting, so the A1 baseline `8.420833333 kWh` is preserved. **PASS.**

Observation (non-blocking): the pseudocode precondition note (line 1280) carries the inline
test-vector cite `(X6; TV204)`, whereas the traceability matrix assigns the overlap-guard
reachability vector to **TV206** (R177, line 178) and **TV204** to the over-budget setup-retry
`RoundAbort` vector. This is a cosmetic cross-reference nuance in a comment; it does not affect the
X6 substance (the precondition reduction and guard evaluation verified in §3.1–§3.3 are unchanged)
and no source file is edited by this audit.

## 4. Cross-document consistency

Pseudocode ↔ round-SM §3.10b X6 ↔ invariant I1 / I16 ↔ terminology are mutually consistent:
`STAGE_01_PROTOCOL_PSEUDOCODE.md` §0.11 (`CreatePendingAssignment`, lines 1272–1332: type/shape-only
PRECONDITIONS + runtime predicates in the executable guard returning `assignment_creation_failed`)
agrees with `STAGE_01_ROUND_STATE_MACHINE.md` §3.10b X6 (lines 713–716: "PRECONDITIONS are
type/shape only; the runtime-varying protocol-validity predicates … are evaluated in the executable
guard and a violation returns `assignment_creation_failed` — a conforming caller can exercise either
result legally"), with `STAGE_01_INVARIANT_CATALOGUE.md` I16 Stage-1X block (X6, lines 342–343:
"`assignment_creation_failed` is reachable without violating a `CreatePendingAssignment` precondition
(runtime predicates live in the guard, not the preconditions)") resting on I1 (lines 47–60: no two
simultaneously valid active assignments overlap — the disjointness predicate the guard enforces at
runtime), and with `STAGE_01_TERMINOLOGY.md` "Reachable `assignment_creation_failed` (X6)"
(lines 891–894: PRECONDITIONS constrain only `assignment_origin in { ORIGINAL, REASSIGNED }`; the
listed runtime-varying predicates are evaluated in the guard and yield
`assignment_creation_failed(reason)`, "so the failure disposition is legally reachable").

## 5. Result

**PASS** — X6 is faithfully realised: `CreatePendingAssignment`'s PRECONDITIONS are reduced to the
type/shape prerequisite `assignment_origin in {ORIGINAL, REASSIGNED}` with the runtime-varying I1 /
custody / coverage / provenance / epoch predicates deliberately moved into the executable guard that
returns `assignment_creation_failed(reason)` creating nothing, making the failure disposition
legally reachable by a conforming caller (exercising the existing W7-era caller branches) rather than
an undefined-behaviour precondition breach; consistent across pseudocode, round-SM §3.10b, invariant
I1/I16, and terminology, with TV195 preserved/updated and TV206 covering guard-based overlap
reachability, and the A1 baseline `8.420833333 kWh` preserved.
