# Stage 1W — Plan-Bound Range Audit (W5)

This is a documentation-only paper audit of a single Stage-1W correction to the range
assignment and reassignment paths as edited in
`docs/thesis_revision_v45/stage_01/STAGE_01_PROTOCOL_PSEUDOCODE.md`:

- **W5 — plan-bound range constructors.** Two new named procedures,
  `RangeAssignFromPlan` and `RangeReassignFromPlan`, take the EXACT validated spec fields,
  perform NO policy `SELECT`, and assert the committed object equals its spec. The ordinary
  `RangeAssign` / `RangeReassign` entry points retain policy selection and DELEGATE the
  create-then-wake mutation to the plan-bound variants; the recovery-plan commit path
  (`CommitRecoveryAssignmentPlan`) calls ONLY the plan-bound constructors with the plan's
  exact spec values.

W5 is a fidelity / executability correction to the redistribution and reserve-activation
install path within PoCol — specifically the idle policy within PoCol. It introduces no
census value, no residency interval, and no transition-energy term, and it does not alter how
the idle policy is accounted; this audit therefore claims no energy, security, or fairness
property, and the accepted accounting baseline is unchanged (A1 baseline `8.420833333 kWh`
preserved). Every claim below is checked against the pseudocode as currently edited; line
numbers are those of the file at audit time and were re-confirmed by direct search.

**Scope.** `RangeAssign` (§4, line 1836) and `RangeAssignFromPlan` (§4, line 1858);
`RangeReassign` (§13, line 3823) and `RangeReassignFromPlan` (§13, line 3857);
`PrepareRecoveryAssignmentPlan` (§10a, line 3494) and `CommitRecoveryAssignmentPlan` (§10a,
line 3529); the two post-epilogue callers `ApplyRecoveryWorkAfterEpilogue` (§9c, Prepare at
line 2943 / Commit at line 2951) and `ApplyRecoveryAssignmentContinuationAfterEpilogue` (§10a,
Prepare at line 3407 / Commit at line 3421); and the U5 plan-record header (lines 768–775).
Cross-checked against `STAGE_01_ROUND_STATE_MACHINE.md` §3.10a (Stage-1W addendum, W5 at
lines 658–662), `STAGE_01_TERMINOLOGY.md` (Stage-1W addendum, W5 at lines 842–844),
`STAGE_01_TRACEABILITY_MATRIX.csv` (R164 at row line 165; TV190/TV191 at the R168 row, line
169), and `STAGE_01_INVARIANT_CATALOGUE.md` (I1/I9/I18b).

---

## 1. The defect W5 closes

Before W5, redistribution and reserve-driven range creation were expressed through a single
abstract constructor step: the plan carried validated specs, but the commit path re-entered
the *same* range constructor that an ordinary dispatched caller would use. Because that
constructor was the abstract, policy-bearing entry point, its body could re-run policy
`SELECT` — re-choosing a range or a target miner — so the committed object could diverge from
the validated plan even though `PrepareRecoveryAssignmentPlan` had already fixed the exact
`MinerID`, `range`, origin, and source. The anti-requirement recorded against R164 states the
failure directly: "a commit that re-SELECTs a miner or range so the committed object diverges
from the validated plan" (`STAGE_01_TRACEABILITY_MATRIX.csv`, R164, line 165).

The defect is a fidelity gap, not a liveness gap: nothing crashed, but the plan-verification
that `PrepareRecoveryAssignmentPlan` performed compute-only (I1/I3/I10/I18b over the PROPOSED
specs, lines 3519–3522) was not guaranteed to bind the committed object, because a re-`SELECT`
inside the constructor could produce a *different* `(MinerID, range, origin, source)` than the
one that was validated. W5 removes the abstract commit-time constructor and replaces it with
two constructors that take the spec fields as inputs, perform NO `SELECT`, and assert equality
with the spec — so what is validated is exactly what is committed.

---

## 2. The two new plan-bound constructors

Both plan-bound constructors carry the identical W5 header banner and the identical INPUTS
list — the exact validated spec fields — and both declare in their preconditions that they
perform no selection.

**`RangeAssignFromPlan`** (line 1858):

```
PROCEDURE RangeAssignFromPlan                                   # W5: plan-bound create-then-wake; EXACT values, NO SELECT
  INPUTS: RoundContext, MinerID, range, assignment_origin, source_assignment, reassignment_reason,
          lease_duration, scheduling_context   # W5: the caller's EXACT validated spec fields (no independent SELECT)
  PRECONDITIONS: miner_state(MinerID) in {REGISTERED, RESERVE}; round_state = ASSIGNMENT or HASHING or SECURITY_RECOVERY;
                 range/origin/source are the caller's exact values (validated by PrepareRecoveryAssignmentPlan for the
                 recovery-plan path, or SELECTed by RangeAssign for the ordinary path). It performs NO SELECT.
```

Its spec-equality assertion, placed immediately after the head is created and before the lease
fields are set (lines 1872–1875):

```
    # W5: the committed object equals the EXACT spec (no divergence via a re-SELECT).
    ASSERT MinerID(assignment) = MinerID AND range(assignment) = range
           AND assignment_origin(assignment) = assignment_origin
           AND source_assignment_ref(assignment) = source_assignment    # W5
```

**`RangeReassignFromPlan`** (line 3857) carries the same INPUTS list (lines 3858–3859) and the
same no-`SELECT` precondition ("It performs NO SELECT.", line 3862), with the exact-suffix /
CLOSED-source provenance stated explicitly:

```
PROCEDURE RangeReassignFromPlan                                 # W5: plan-bound create-then-wake reassignment; EXACT values, NO SELECT
  INPUTS: RoundContext, MinerID, range, assignment_origin, source_assignment, reassignment_reason,
          lease_duration, scheduling_context   # W5: the caller's EXACT validated spec fields (no independent SELECT)
  PRECONDITIONS: miner_state(MinerID) in {REGISTERED, RESERVE}; range = an accepted unsearched suffix whose source is
                 CLOSED (L4/C4), with the caller's EXACT validated provenance; round_state = ASSIGNMENT or HASHING or
                 SECURITY_RECOVERY. It performs NO SELECT.
```

Its spec-equality assertion (lines 3871–3873) is the same four-field predicate:

```
    ASSERT MinerID(assignment) = MinerID AND range(assignment) = range
           AND assignment_origin(assignment) = assignment_origin
           AND source_assignment_ref(assignment) = source_assignment    # W5
```

Both constructors then set `lease_start`/`lease_expiry` from the passed `lease_duration`,
perform EXACTLY ONE `StartWake` transaction threaded with the caller's `scheduling_context`
(lines 1881–1883 and 3878–3880), and return a structured disposition
(`range_assigned` / `range_assign_creation_failed` / `range_assign_wake_failed`, lines
1894–1895; and the `range_reassign_*` analogues, lines 3898–3899). On a post-creation wake
failure each closes the un-activated head legally and restores the coverage / custody ledgers
so no orphan PENDING remains (lines 1888–1893 and 3881–3889).

**No-`SELECT` confirmation (by search).** A direct grep for `SELECT` over the body of each
plan-bound procedure returns only COMMENT text — the banner "NO SELECT", the INPUTS gloss "no
independent SELECT", the precondition "It performs NO SELECT.", the assertion comment "no
divergence via a re-SELECT", and the NOTE "It uses the EXACT spec values (no SELECT)". There
is NO executable `SELECT ...` statement in either procedure. By contrast, the ordinary entry
points each contain a real `SELECT` statement (line 1848 and line 3846; see §4). The expected
W5 content is therefore present, not absent.

---

## 3. The delegation split — ordinary SELECT-then-delegate vs plan-bound exact-values

W5 partitions responsibility cleanly: policy SELECTION lives in the ordinary entry point;
EXACT-value MUTATION lives in the plan-bound constructor.

**`RangeAssign`** (line 1836) SELECTs the fresh ORIGINAL range, then delegates (lines
1844–1851):

```
    # W5: the ORDINARY entry point performs POLICY SELECTION, then delegates the EXACT-values MUTATION to the
    #   plan-bound RangeAssignFromPlan. The recovery-plan commit path (CommitRecoveryAssignmentPlan) calls
    #   RangeAssignFromPlan DIRECTLY with the plan's exact values, so a committed range assignment equals its validated
    #   plan and NEITHER path wakes twice (one create-then-wake transaction).
    SELECT candidate_range from unassigned portion of nonce_domain      # fresh, never-assigned -> ORIGINAL
    RETURN CALL RangeAssignFromPlan(RoundContext, MinerID = MinerID, range = candidate_range,
                     assignment_origin = ORIGINAL, source_assignment = null, reassignment_reason = null,
                     lease_duration = lease_duration, scheduling_context = scheduling_context)   # W5
```

Its NOTE (lines 1854–1856) confirms it "never performs the mutation itself" and "returns the
plan-bound constructor's structured disposition unchanged."

**`RangeReassign`** (line 3823) checks the C4/L4 reassignment preconditions, SELECTs the target
miner, then delegates (lines 3839–3850):

```
    ASSERT status(source_assignment(unsearched_suffix)) = CLOSED      # L4: reassign only a CLOSED source's suffix
    SELECT to_miner from {RESERVE, REGISTERED} miners (or via ReserveActivate)
    RETURN CALL RangeReassignFromPlan(RoundContext, MinerID = to_miner, range = unsearched_suffix,
                     assignment_origin = REASSIGNED, source_assignment = source_assignment(unsearched_suffix),
                     reassignment_reason = reason, lease_duration = default_lease_duration,
                     scheduling_context = scheduling_context)   # W5
```

Its NOTE (lines 3853–3855) likewise confirms it "delegates the atomic create-then-wake to
RangeReassignFromPlan; it never performs the mutation itself and returns that constructor's
structured disposition unchanged."

The split is exhaustive: the two ordinary procedures own the only two executable `SELECT`
statements on these paths (a fresh-range SELECT for ORIGINAL assignment; a target-miner SELECT
for REASSIGNED reassignment), while the two plan-bound procedures own the mutation and the
spec-equality guard and perform no selection at all. A committed range object therefore always
equals the `(MinerID, range, origin, source)` its caller supplied — SELECTed by the ordinary
entry point on an ordinary dispatch, or validated by `PrepareRecoveryAssignmentPlan` on the
recovery path.

---

## 4. The prepare -> commit fidelity chain

The recovery-plan install path is now spec-bound end to end. `PrepareRecoveryAssignmentPlan`
(line 3494) is COMPUTE-ONLY: it builds each spec with the exact fields and verifies
I1/I3/I10/I18b over the PROPOSED specs BEFORE any mutation (lines 3519–3522), returning
`plan_ready(plan)` or `plan_invalid(reason)`. Each spec carries the W5 fields — the header
gloss at lines 3506–3510 lists a REDISTRIBUTION spec as
`{ kind = REDISTRIBUTION, MinerID, range, origin, source_assignment, reassignment_reason }`,
with `reassignment_reason` "a permitted reassignment reason (e.g. security_recovery) for a
REASSIGNED origin, null for ORIGINAL" — and the U5 plan-record header confirms each spec
carries `{ kind, MinerID, range, origin, source_assignment, reassignment_reason }` (lines
770–771).

`CommitRecoveryAssignmentPlan` (line 3529) then dispatches each REDISTRIBUTION spec to the
plan-bound constructor CHOSEN BY `spec.origin`, passing the spec's exact values (lines
3566–3579):

```
      ELSE:  # REDISTRIBUTION spec — V6: COVERAGE_REPAIR_WORK, or a no-breach branch-C redistribution
        # W5: call the PLAN-BOUND range constructor with the spec's EXACT values (no SELECT), chosen by spec.origin.
        IF spec.origin = REASSIGNED:
          SET rr <- CALL RangeReassignFromPlan(RoundContext, MinerID = spec.MinerID, range = spec.range,
                         assignment_origin = spec.origin, source_assignment = spec.source_assignment,
                         reassignment_reason = spec.reassignment_reason, lease_duration = default_lease_duration,
                         scheduling_context = scheduling_context)        # W4/W5
        ELSE:
          SET rr <- CALL RangeAssignFromPlan(RoundContext, MinerID = spec.MinerID, range = spec.range,
                         assignment_origin = spec.origin, source_assignment = spec.source_assignment,
                         reassignment_reason = spec.reassignment_reason, lease_duration = default_lease_duration,
                         scheduling_context = scheduling_context)        # W4/W5
```

On success the commit path re-asserts spec equality against the returned object (lines
3580–3583) — a second, caller-side check on top of the constructor's own internal W5 assertion:

```
        IF rr = range_reassigned(prov, aid, wref) OR rr = range_assigned(aid, wref, ws):
          # W5: the committed object equals the exact spec (the constructor asserts this internally too).
          ASSERT rr.AssignmentID resolves MinerID = spec.MinerID AND range = spec.range
                 AND assignment_origin = spec.origin AND source_assignment_ref = spec.source_assignment   # W5
```

The following table traces each W5 spec field from its plan slot, through the plan-bound
parameter, to the committed object it binds. It is exact — no field is dropped, defaulted at
commit time, or re-selected.

| Spec field (`PrepareRecoveryAssignmentPlan`) | Plan-bound parameter (`Range*FromPlan`) | Committed / asserted object property |
|---|---|---|
| `spec.MinerID` | `MinerID` | `MinerID(assignment) = MinerID` (constructor, lines 1873 / 3871); `rr…MinerID = spec.MinerID` (commit, line 3582) |
| `spec.range` | `range` | `range(assignment) = range` (constructor, lines 1873 / 3871); `rr…range = spec.range` (commit, line 3582) |
| `spec.origin` | `assignment_origin` | `assignment_origin(assignment) = assignment_origin` (constructor, lines 1874 / 3872); also selects the constructor at line 3570 |
| `spec.source_assignment` | `source_assignment` | `source_assignment_ref(assignment) = source_assignment` (constructor, lines 1875 / 3873); `rr…source_assignment_ref = spec.source_assignment` (commit, line 3583) |
| `spec.reassignment_reason` | `reassignment_reason` | passed to `CreatePendingAssignment(… reason = reassignment_reason)` (lines 1868 / 3867); `security_recovery` for REASSIGNED, `null` for ORIGINAL (header 3509–3510) |
| `default_lease_duration` | `lease_duration` | `lease_expiry(assignment) <- now + lease_duration` (lines 1877 / 3875) |
| `scheduling_context` (= `POST_EPILOGUE(pctx)`) | `scheduling_context` | threaded to the single `StartWake -> ScheduleEvent`, wake seated STRICTLY LATER (lines 1881–1883 / 3878–3880) |

Both recovery callers reach this commit path with a `POST_EPILOGUE` scheduling context:
`ApplyRecoveryWorkAfterEpilogue` (§9c) prepares the plan at line 2943 and commits at line 2951
(`scheduling_context = POST_EPILOGUE(pctx)`), and
`ApplyRecoveryAssignmentContinuationAfterEpilogue` (§10a) prepares at line 3407 and commits at
line 3421 with the same context. Neither caller performs any range or miner selection of its
own — selection was done compute-only in `PrepareRecoveryAssignmentPlan`, and the commit uses
the spec's exact values via the plan-bound constructors.

---

## 5. Mapping to TV190 / TV191

The two blocking test vectors that exercise W5 by name are recorded on the R168 row of
`STAGE_01_TRACEABILITY_MATRIX.csv` (line 169), targeting `STAGE_01W_SEMANTIC_TEST_VECTORS`:

- **TV190** — "RangeAssignFromPlan commits exactly `spec.MinerID` and `spec.range` returning
  one AssignmentID and one WakeEventRef." This is discharged by `RangeAssignFromPlan`'s W5
  spec-equality assertion (lines 1873–1875), its single-wake structure (one `StartWake`, lines
  1881–1883; NOTE "performs EXACTLY ONE StartWake", lines 1896–1901), and its
  `range_assigned(AssignmentID, WakeEventRef, resulting_state = WAKING)` return (line 1885),
  consumed once by the commit path with no second wake (lines 3580–3584; W4 at lines 3568–3569).
- **TV191** — "RangeReassignFromPlan commits the validated suffix and provenance without
  SELECT." This is discharged by `RangeReassignFromPlan`'s CLOSED-source / exact-suffix
  precondition and "It performs NO SELECT." clause (lines 3860–3862), its four-field W5
  assertion binding the committed provenance (lines 3871–3873), and the grep confirmation in §2
  that its body contains no executable `SELECT`.

The same R168 row also lists TV192 ("CommitRecoveryAssignmentPlan consumes a success range
result without a second StartWake"), which corroborates the single-wake consumption relied on
above (commit-path `CONTINUE` after capturing the one returned `WakeEventRef`, line 3584).

---

## 6. Traceability

- **Round state machine, §3.10a W5** (`STAGE_01_ROUND_STATE_MACHINE.md`, lines 658–662).
  The addendum states W5 in full: `RangeAssignFromPlan` and `RangeReassignFromPlan` "take the
  exact validated spec fields (`MinerID`, `range`, `assignment_origin`, `source_assignment`,
  `reassignment_reason`, `lease_duration`, `scheduling_context`) and perform NO `SELECT`; the
  ordinary `RangeAssign` / `RangeReassign` entry points do policy selection and delegate. The
  recovery-plan commit path calls ONLY the plan-bound constructors and asserts the committed
  object equals its spec." The pseudocode audited here matches this addendum field-for-field.
- **Terminology, W5** (`STAGE_01_TERMINOLOGY.md`, lines 842–844). The "Plan-bound range
  constructor (W5)" entry names both constructors, lists the identical seven spec fields,
  states "perform NO `SELECT`", and states "the ordinary entry points select policy and
  delegate." Consistent with the pseudocode INPUTS lists (lines 1859–1860 / 3858–3859) and the
  ordinary-entry-point delegation (§3).
- **R164** (`STAGE_01_TRACEABILITY_MATRIX.csv`, row line 165). R164 is the requirement W5
  discharges: "Add plan-bound range constructors (W5) … take the exact validated spec fields …
  perform NO SELECT and assert the committed object equals the spec; the ordinary
  RangeAssign/RangeReassign entry points do policy selection and delegate; the recovery-plan
  commit path calls only the plan-bound constructors." Its named procedures
  (`RangeAssignFromPlan; RangeReassignFromPlan; RangeAssign; RangeReassign;
  CommitRecoveryAssignmentPlan; PrepareRecoveryAssignmentPlan`), its invariants (I1; I9; I18b),
  and its anti-requirement (a commit that re-SELECTs so the committed object diverges from the
  validated plan) all correspond to the pseudocode as audited; the row is marked SPECIFIED.

---

## 7. Conclusion

W5 is present and internally consistent in the current pseudocode. Two new plan-bound
constructors — `RangeAssignFromPlan` (line 1858) and `RangeReassignFromPlan` (line 3857) —
take the exact validated spec fields, contain no executable `SELECT` (confirmed by search),
and assert the committed object equals its spec across `MinerID` / `range` / origin /
`source_assignment` (lines 1873–1875 and 3871–3873). The ordinary `RangeAssign` (line 1836)
and `RangeReassign` (line 3823) entry points retain the only two policy `SELECT` statements
(lines 1848 and 3846) and delegate the exact-value create-then-wake mutation to the plan-bound
variants. `PrepareRecoveryAssignmentPlan` (line 3494) fixes each spec's exact fields
(including `reassignment_reason`) compute-only, and `CommitRecoveryAssignmentPlan` (line 3529)
dispatches by `spec.origin` to the plan-bound constructor with `spec.MinerID` / `spec.range` /
`spec.origin` / `spec.source_assignment` / `spec.reassignment_reason` (lines 3570–3583) — no
re-`SELECT` on the commit path. The correction is a pure fidelity / executability refinement
of the redistribution and reserve-activation install path within PoCol (the idle policy within
PoCol); it introduces no census, residency, or transition-energy term, and the A1 baseline
`8.420833333 kWh` is preserved. The requirement (R164), its cross-document statements
(round-SM §3.10a W5; terminology W5), and its test vectors (TV190/TV191) are mutually
consistent with the audited pseudocode.
