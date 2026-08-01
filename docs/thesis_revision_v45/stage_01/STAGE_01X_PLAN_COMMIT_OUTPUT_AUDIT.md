# Stage 1X — Plan-Commit Output Audit (X5)

This is a documentation-only paper audit of correction **X5** to the recovery
assignment-installation path as edited in
`docs/thesis_revision_v45/stage_01/STAGE_01_PROTOCOL_PSEUDOCODE.md`.

- **X5 — the plan commit returns its rollback record EXPLICITLY.**
  `CommitRecoveryAssignmentPlan`'s success disposition changes from `install_committed`
  (carrying nothing) to `install_committed(rollback_record)`. The rollback record is now a
  first-class RETURN value in EVERY disposition — success and post-mutation failure alike —
  and the obsolete pass-by-reference `plan.rollback_metadata` field is withdrawn. Callers that
  may have to reverse a committed install after a later `CompleteAssignmentPhase` failure
  capture `commit.rollback_record` and pass it to `RollbackRecoveryAssignmentPlan`; no caller
  reads an undeclared `plan.rollback_metadata`.

X5 is an interface-fidelity correction to the recovery-work (§9c) and branch-C
redistribution-continuation (§10a) install path. It introduces no census value, no residency
interval, and no transition-energy term, and it does not alter how the idle policy within
PoCol is accounted; this audit therefore claims no energy, security, or fairness property and
leaves the accepted accounting baseline (A1 = 8.420833333 kWh) unchanged. Every claim below is
checked against the pseudocode as currently edited; line numbers are those of the file at
audit time and were re-confirmed by direct search.

Scope: `CommitRecoveryAssignmentPlan` (§10a, `PROCEDURE` at line 3610; RETURN/RETURNS at lines
3682–3684), `PrepareRecoveryAssignmentPlan` (§10a, `PROCEDURE` at line 3574; X1/X5 note at
lines 3598–3599), `RollbackRecoveryAssignmentPlan` (§ line 3695), the §0.8 core-data-model
recovery-plan record (lines 769–775), and the two post-epilogue callers
`ApplyRecoveryWorkAfterEpilogue` (§9c, `PROCEDURE` at line 2986) and
`ApplyRecoveryAssignmentContinuationAfterEpilogue` (§10a, `PROCEDURE` at line 3448).
Cross-checked against `STAGE_01_ROUND_STATE_MACHINE.md` §3.10b (Stage-1X addendum, X5 at lines
709–711), `STAGE_01_INVARIANT_CATALOGUE.md` I16 (Stage-1X, X5 at line 341), and
`STAGE_01_TERMINOLOGY.md` (Stage-1X addendum, `rollback_record` entry at lines 859–863).

---

## 1. The defect X5 closes

Before X5, the commit's success outcome was an unadorned `install_committed`. A caller that had
to undo a committed install after a subsequent failure had no returned record to reverse it
with — it depended on an undeclared, pass-by-reference `plan.rollback_metadata` field mutated
inside the commit. That is a broken contract: the result union advertised no rollback payload
on success, the `plan` record never declared such a field, and any read of it was reading an
undefined value. X5 makes the commit build the COMPLETE rollback record and RETURN it in the
success disposition (as well as in `install_failed_after_mutation`), so the caller reverses a
committed install from a value the commit actually returned, and the pass-by-reference field is
removed everywhere.

---

## 2. Check 1 — `install_committed` now carries `rollback_record` in the success disposition — PASS

The success RETURN of `CommitRecoveryAssignmentPlan` (line 3682) is:

```
    RETURN install_committed(rollback_record(RecoveryInstallID = plan.RecoveryInstallID, items = created_items))
```

The `RETURNS` block (lines 3683–3684) declares the full result union with the rollback record
explicit in the success arm:

```
  RETURNS: install_committed(rollback_record) | install_failed_before_mutation(reason) |
           install_failed_after_mutation(reason, rollback_record)   # X5: rollback_record explicit in EVERY disposition
```

The success arm carries `rollback_record`; the trailing comment states the record is explicit
in every disposition. PASS.

---

## 3. Check 2 — the commit builds and returns the complete `rollback_record` explicitly in EVERY disposition — PASS

`CommitRecoveryAssignmentPlan` accumulates a per-item record as it commits each spec (line
3621, `SET created_items <- empty   # X1: per-item rollback records (a COMPLETE state
transaction)`), capturing — BEFORE each plan-bound constructor mutates — the pre-wake miner
state, the coverage/custody before-image, and the complete rollback transition envelope (lines
3627–3630), then adding a `rollback_item` from the ACTUAL references each transaction returns
(the reserve-activation add at lines 3636–3638; the redistribution add at lines 3665–3668).

Every terminating disposition carries the record built from `created_items`:

- **Success** (line 3682): `RETURN install_committed(rollback_record(RecoveryInstallID =
  plan.RecoveryInstallID, items = created_items))`.
- **`install_failed_after_mutation`, reserve-activation pre-mutation sub-failure** (lines
  3642–3643): `RETURN install_failed_after_mutation(reason, rollback_record(RecoveryInstallID =
  plan.RecoveryInstallID, items = created_items))   # X1/X5: explicit record`.
- **`install_failed_after_mutation`, reserve-activation self-rolled-back spec** (lines
  3647–3648): `RETURN install_failed_after_mutation(reason = r.reason,
  rollback_record(RecoveryInstallID = plan.RecoveryInstallID, items = created_items))`.
- **`install_failed_after_mutation`, redistribution creation failure** (lines 3673–3674):
  `RETURN install_failed_after_mutation(reason, rollback_record(RecoveryInstallID =
  plan.RecoveryInstallID, items = created_items))`.
- **`install_failed_after_mutation`, redistribution wake failure** (lines 3678–3679):
  `RETURN install_failed_after_mutation(reason = rr.reason,
  rollback_record(RecoveryInstallID = plan.RecoveryInstallID, items = created_items))`.

The only disposition that does NOT carry a record is `install_failed_before_mutation` (lines
3620, 3641, 3646, 3672, 3677), which by construction fires only when `created_items is empty` —
nothing was committed, so there is nothing to roll back. The procedure NOTE (lines 3688–3691)
restates the contract: it "builds the COMPLETE rollback_record … from the ACTUAL references the
transactions return, and RETURNS it EXPLICITLY in EVERY disposition — install_committed(rollback_record)
as well as install_failed_after_mutation(reason, rollback_record) — so a caller never relies on
a pass-by-reference field." PASS.

---

## 4. Check 3 — the recovery-plan record and `PrepareRecoveryAssignmentPlan` declare/set NO `rollback_metadata` field — PASS

The §0.8 core-data-model recovery-plan record (lines 769–770) is:

```
  # recovery_assignment_plan = { RecoveryInstallID, source_assignment_versions, accepted_unsearched_suffixes,
  #   selected_reserve_miners, new_pending_assignment_specs (stable creation order) }.
```

Its five fields are `RecoveryInstallID`, `source_assignment_versions`,
`accepted_unsearched_suffixes`, `selected_reserve_miners`, and `new_pending_assignment_specs`.
There is no `rollback_metadata` field.

`PrepareRecoveryAssignmentPlan` (the compute-only planner, `PROCEDURE` at line 3574) sets only
those five fields (lines 3582–3594: `SET plan.RecoveryInstallID`, `SET
plan.source_assignment_versions`, `SET plan.accepted_unsearched_suffixes`, `SET
plan.selected_reserve_miners`, `SET plan.new_pending_assignment_specs`) and never assigns a
rollback field. It carries the explicit X1/X5 note (lines 3598–3599):

```
    # X1/X5: the plan carries NO rollback_metadata field — CommitRecoveryAssignmentPlan builds the complete rollback_record
    #   (items) and returns it EXPLICITLY in every disposition (the obsolete pass-by-reference plan.rollback_metadata is withdrawn).
```

Record and planner agree: no `rollback_metadata` field is declared or set. PASS.

---

## 5. Check 4 — both post-epilogue callers use `commit.rollback_record`; no caller reads `plan.rollback_metadata` — PASS

**`ApplyRecoveryAssignmentContinuationAfterEpilogue` (§10a, `PROCEDURE` at line 3448)** is the
caller that can run `CompleteAssignmentPhase` after committing and therefore must be able to
reverse a committed install. On the success disposition it CAPTURES the returned record (lines
3526–3528):

```
    # commit = install_committed(commit_rollback_record): X5 — CAPTURE the explicit rollback record for a possible
    #   post-CompleteAssignmentPhase rollback (never an undeclared pass-by-reference to plan.rollback_metadata).
    SET commit_rollback_record <- commit.rollback_record
```

and, when `CompleteAssignmentPhase` returns `assignment_phase_failed`, passes that captured
record to the rollback (line 3541):

```
      SET rb <- CALL RollbackRecoveryAssignmentPlan(RoundContext, commit_rollback_record)   # U5/X5: the EXPLICIT record returned by install_committed
```

Its `install_failed_after_mutation` branch likewise reverses from the returned record, not a
pass-by-reference field (lines 3507–3508):

```
    IF commit = install_failed_after_mutation(reason, rollback_record):
      SET rb <- CALL RollbackRecoveryAssignmentPlan(RoundContext, rollback_record)   # U5/X1: structured rollback result
```

**`ApplyRecoveryWorkAfterEpilogue` (§9c, `PROCEDURE` at line 2986)** reverses from the returned
record in its `install_failed_after_mutation` branch (lines 3026–3027):

```
    IF commit = install_failed_after_mutation(reason, rollback_record):
      SET rb <- CALL RollbackRecoveryAssignmentPlan(RoundContext, rollback_record)   # U5/X1: structured rollback result
```

On the success disposition, this caller structurally performs NO later
`CompleteAssignmentPhase` — reserve activation completes at each miner's own
`WakeCompleteEvent` — so it needs no post-commit rollback; the captured record is retained for
audit only. The success-arm comment states this precisely (lines 3043–3046):

```
    # commit = install_committed(commit_rollback_record): the reserve wake(s) / redistribution PENDING heads are seated
    #   STRICTLY LATER (U2). X5: the caller CAPTURES commit.rollback_record; the recovery-work path performs NO later
    #   CompleteAssignmentPhase (activation completes at each miner's own WakeCompleteEvent), so the record is retained
    #   for audit and no post-commit rollback is required on this path.
```

Both callers therefore consume the record RETURNED by the commit — `commit.rollback_record` /
the `install_failed_after_mutation(reason, rollback_record)` binding — and neither reads
`plan.rollback_metadata`. The consuming procedure `RollbackRecoveryAssignmentPlan` confirms the
same input contract in its INPUTS line (line 3696): `INPUTS: RoundContext, rollback_record   #
X1: { RecoveryInstallID, items : [rollback_item] } (returned explicitly by
CommitRecoveryAssignmentPlan, X5)`. PASS.

---

## 6. Check 5 — corpus scan finds NO executable SET or read of `plan.rollback_metadata` — PASS

A full-file search for `rollback_metadata` across `STAGE_01_PROTOCOL_PSEUDOCODE.md` returns
exactly four occurrences, ALL inside `#` comments / NOTE text, and NONE an executable `SET
plan.rollback_metadata <- …` or an executable read:

- **Line 779** — header data-model NOTE: "… `install_failed_after_mutation(reason,
  rollback_record)`. The obsolete plan.rollback_metadata pass-by-reference field is WITHDRAWN."
- **Line 3527** — continuation-caller comment: "… (never an undeclared pass-by-reference to
  plan.rollback_metadata)."
- **Lines 3598–3599** — `PrepareRecoveryAssignmentPlan` X1/X5 comment: "the plan carries NO
  rollback_metadata field … the obsolete pass-by-reference plan.rollback_metadata is withdrawn."

No executable line writes or reads `plan.rollback_metadata`. Every surviving mention is a
withdrawn-name annotation documenting the removal. PASS.

---

## 7. Check 6 — result union, RETURNS, and all call sites agree exactly — PASS

The three surfaces of the contract agree:

- **Result union / RETURNS** (lines 3683–3684): `install_committed(rollback_record) |
  install_failed_before_mutation(reason) | install_failed_after_mutation(reason,
  rollback_record)`.
- **Every RETURN inside the body** produces exactly one of those three shapes:
  `install_committed(rollback_record(…))` (3682); `install_failed_before_mutation(reason)`
  (3620, 3641, 3646, 3672, 3677); `install_failed_after_mutation(reason, rollback_record(…))`
  (3642–3643, 3647–3648, 3673–3674, 3678–3679). No RETURN emits a shape absent from the union,
  and no union arm lacks a producing RETURN.
- **Every call site branches on exactly these three arms.** The continuation caller matches
  `install_failed_before_mutation(reason)` (line 3499), `install_failed_after_mutation(reason,
  rollback_record)` (line 3507), and `install_committed(commit_rollback_record)` (lines
  3526–3528). The recovery-work caller matches `install_failed_before_mutation(reason)` (line
  3021), `install_failed_after_mutation(reason, rollback_record)` (line 3026), and
  `install_committed(commit_rollback_record)` (lines 3043–3049). The record consumed downstream
  by `RollbackRecoveryAssignmentPlan` (INPUTS line 3696) is the same `{ RecoveryInstallID,
  items : [rollback_item] }` shape the commit constructs.

Union, body RETURNs, and both callers are in exact agreement, with the rollback record present
on the success arm and on every post-mutation-failure arm. PASS.

---

## 8. Test-vector linkage (TV205)

`STAGE_01_TRACEABILITY_MATRIX.csv` row **R177** enumerates the Stage-1X blocking test vectors
(TV198–TV209). The vector that exercises X5 is **TV205 — "a caller captures
`commit.rollback_record` and uses it to roll back after `CompleteAssignmentPhase`."** That
vector maps directly onto the audited executable path in
`ApplyRecoveryAssignmentContinuationAfterEpilogue`: the capture `SET commit_rollback_record <-
commit.rollback_record` (line 3528) followed, on `assignment_phase_failed`, by `CALL
RollbackRecoveryAssignmentPlan(RoundContext, commit_rollback_record)` (line 3541). The
companion vectors situate it: **TV198** (the commit builds a `rollback_record` whose items carry
the exact `AssignmentID` / `assignment_version` / `WakeEventRef` / before-image for every
committed activation) covers the record-construction verified in Check 2, and **TV199/TV200**
(the rollback departs each still-`WAKING` miner via `T12` and restores the before-image) cover
the record's consumer. R177's named procedures include `CommitRecoveryAssignmentPlan` and
`RollbackRecoveryAssignmentPlan`; its invariant column includes I16. Linkage present and
consistent.

---

## 9. Cross-document consistency (pseudocode ↔ round-SM §3.10b X5 ↔ terminology ↔ invariant I16)

- **Round state machine §3.10b (X5), lines 709–711** state the contract verbatim:
  "`CommitRecoveryAssignmentPlan` returns `install_committed(rollback_record)`; callers capture
  `commit.rollback_record` for a later `CompleteAssignmentPhase`-failure rollback. The obsolete
  `plan.rollback_metadata` pass-by-reference field is withdrawn." This matches the pseudocode
  RETURN (line 3682), the caller capture (line 3528), and the withdrawn-field annotations
  exactly.
- **Terminology, Stage-1X addendum, lines 859–863** define the record and its home: "…
  `CommitRecoveryAssignmentPlan` builds and RETURNS an explicit `install_committed(rollback_record)`,
  where `rollback_record = { RecoveryInstallID, items:[rollback_item] }` and each `rollback_item
  = { MinerID, AssignmentID, assignment_version, WakeEventRef, pre_wake_state,
  rollback_envelope, coverage_custody_before_image, kind, provenance }` … There is no
  pass-by-reference `plan.rollback_metadata`; the record is the sole rollback contract." This
  matches the pseudocode `rollback_item` shape (lines 780–782 and the add sites 3636–3638 /
  3665–3668) field-for-field.
- **Invariant I16 (Stage-1X), line 341** records the same: "**X5:** `CommitRecoveryAssignmentPlan`
  returns `install_committed(rollback_record)` explicitly." I16's X1/X2 detail (lines 334–337)
  keys the legal `T12` rollback to the `rollback_record` items and the exact assignment version,
  which is the record this commit now returns.

**One observation, non-blocking.** The round-SM Stage-1V paragraph **V5 (line 608)** still uses
the pre-X5 term when it says the commit "builds `rollback_metadata` from the ACTUAL references
the transactions return." This is a description in the superseded V-layer addendum; the
Stage-1X §3.10b addendum (line 711) explicitly withdraws `plan.rollback_metadata` and locks the
naming to `install_committed(rollback_record)`, exactly as the pseudocode's own withdrawn-name
NOTES retain the old term while the current contract uses `rollback_record`. The authoritative
X5 block, the terminology entry, and I16 are all consistent with the pseudocode; the V5
paragraph is a historical-layer residue of the earlier name, not a live-contract divergence.
Recommend a one-word refresh of the V5 wording to `rollback_record` at a future editorial pass
for uniform terminology; it does not affect the X5 result.

---

## 10. Result

**PASS** — X5 is faithfully realised: `CommitRecoveryAssignmentPlan` returns
`install_committed(rollback_record)` and builds the complete record explicitly in every
success and post-mutation-failure disposition; the recovery-plan record and
`PrepareRecoveryAssignmentPlan` declare/set no `rollback_metadata`; both post-epilogue callers
reverse from the returned record (never `plan.rollback_metadata`); the corpus scan finds only
withdrawn-name comments; and the result union, RETURNS, and every call site agree — consistent
with round-SM §3.10b, terminology, invariant I16, and TV205 (baseline A1 = 8.420833333 kWh
unchanged).
