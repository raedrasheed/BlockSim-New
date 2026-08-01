# Stage 1X — Exact-Assignment Rollback Audit (X2)

## 1. Scope

This audit documents correction **X2** of the Stage-1X thesis revision — *"every `T12`
rollback binds the EXACT assignment version"* — as it applies to the idle policy within
PoCol. It certifies that when a round setup or a committed recovery plan is rolled back and a
miner is left in `WAKING` on a head created by that setup/plan, the sanctioned
`WAKING -> OFFLINE` departure (`T12`) is issued through `ApplyMinerStateTransition` with an
`assignment_ref` that names the **exact `(AssignmentID, assignment_version)` of the head the
miner actually holds** — never `assignment_ref = null` and never an unversioned reference.

Every claim below is grounded in the current text of the source-of-truth specification, read
and re-grepped for this audit (line numbers are those of the files as read now, not carried
over from earlier stages):

- `STAGE_01_PROTOCOL_PSEUDOCODE.md` — the §0.8 `setup_transaction` / `rollback_record` state
  declarations and the executable procedures `PrepareParticipantsForNewRound`,
  `ContinueTemplateRefreshAssignmentSetup`, `RollbackParticipantSetup`,
  `RollbackTemplateRefreshSetup`, `RollbackRecoveryAssignmentPlan`, and
  `CommitRecoveryAssignmentPlan`.

The cross-document anchors (§7) are `STAGE_01_ROUND_STATE_MACHINE.md §3.10b`,
`STAGE_01_TERMINOLOGY.md` (`assignment_by_miner`), and `STAGE_01_INVARIANT_CATALOGUE.md` `I16`.

This is a documentation-only artifact: it reads the corrected specification and records the
evidence for X2; it edits no other file and modifies no pseudocode. The A1 continuous-control
energy baseline of `8.420833333 kWh` (`STAGE_01_ENERGY_MODEL_SPECIFICATION.md`) is orthogonal
to this correction and is preserved unchanged — X2 concerns only which assignment version is
named on the rollback transition, and touches no residency-power or energy-accounting term.

## 2. What X2 requires

The §0.8 state description states the contract for the setup transaction binding directly:

> `# setup_transaction (participant_setup_txn / refresh_setup_txn) additionally carries (X2):`
> `#   assignment_by_miner : map MinerID -> (AssignmentID, assignment_version), populated immediately AFTER`
> `#     assignment_created and BEFORE StartWake, so RollbackParticipantSetup /`
> `#     RollbackTemplateRefreshSetup pass the EXACT assignment version to the WAKING -> OFFLINE (T12)`
> `#     departure (never assignment_ref = null when the miner holds a setup-created PENDING head).`
> — `STAGE_01_PROTOCOL_PSEUDOCODE.md`, lines 793–797

and, for the recovery path, the `rollback_item` field that carries the same version:

> `#     - assignment_version            : the immutable version, so the T12 release + close identify the EXACT head (X2).`
> — `STAGE_01_PROTOCOL_PSEUDOCODE.md`, line 788

The five verification criteria below decompose this contract into declaration, in-loop
population (order-exact), and rollback consumption for the two setup paths and the one
recovery path, plus a negative check that no rollback passes a null/unversioned ref while a
head is held.

## 3. Criterion 1 — both setup transactions declare and initialise `assignment_by_miner` — PASS

`PrepareParticipantsForNewRound` constructs `participant_setup_txn` with the field present and
initialised to empty before the miner loop:

> `SET participant_setup_txn <- setup_transaction(rollback_envelope = dispatch_envelope,`
> `      wakes = empty, created_assignments = empty, prior_states = empty, assignment_by_miner = empty)   # W1/V8/X2`
> — `PrepareParticipantsForNewRound`, `STAGE_01_PROTOCOL_PSEUDOCODE.md`, lines 1573–1574

`ContinueTemplateRefreshAssignmentSetup` constructs `refresh_setup_txn` identically:

> `SET refresh_setup_txn <- setup_transaction(rollback_envelope = dispatch_envelope,`
> `      wakes = empty, created_assignments = empty, prior_states = empty, assignment_by_miner = empty)   # W1/W3/X2`
> — `ContinueTemplateRefreshAssignmentSetup`, `STAGE_01_PROTOCOL_PSEUDOCODE.md`, lines 4758–4759

Both records therefore begin every setup attempt with an explicit, empty `assignment_by_miner`
map — no field is left implicit or populated "from prose" (the X3/W3 note at line 4757 makes
the explicit-population requirement for the refresh path binding). **PASS.**

## 4. Criterion 2 — both loops populate `(AssignmentID, assignment_version)` AFTER `assignment_created`, BEFORE `StartWake` — PASS

The ordering matters because it guarantees the recorded version is the head's **actual creation
version**: the map entry is written only after the constructor result has been branched on and
the created assignment read, and it is written before the wake that raises the miner into
`WAKING`.

### 4.1 `PrepareParticipantsForNewRound`

The constructor result is branched first (a failure sets `participant_setup_error` and
`CONTINUE`s, minting nothing), so the assignment is read only on the created result:

> `IF cr is assignment_creation_failed(reason):`
> `  SET participant_setup_error <- assignment_creation_failed(reason)   # W7: nothing created; setup failed`
> `  CONTINUE`
> `SET a <- cr.assignment                                              # W7: cr = assignment_created(a) — safe to read now`
> — lines 1617–1620

The map is then populated, and `StartWake` follows on the next line:

> `SET participant_setup_txn.assignment_by_miner[m] <- (AssignmentID(a), assignment_version(a))   # X2: EXACT version, populated BEFORE StartWake`
> `SET wr <- CALL StartWake(RoundContext, m, target_assignment = a, from_state = spec.from, …)`
> — lines 1623–1624

Population (1623) is strictly **after** `assignment_created` is read (1620) and strictly
**before** `StartWake` (1624). The version stored is `assignment_version(a)` of the just-created
head.

### 4.2 `ContinueTemplateRefreshAssignmentSetup`

Same discipline — read the created head only after the failure branch, populate the map, then
wake:

> `IF cr is assignment_creation_failed(reason):`
> `  SET refresh_setup_error <- assignment_creation_failed(reason) ; CONTINUE   # W7: nothing created`
> `SET assignment_m <- cr.assignment                                            # W7: cr = assignment_created(assignment_m)`
> — lines 4766–4768

> `SET refresh_setup_txn.assignment_by_miner[m] <- (AssignmentID(assignment_m), assignment_version(assignment_m))   # X2: EXACT version BEFORE StartWake`
> `…`
> `SET wr <- CALL StartWake(RoundContext, m, target_assignment = assignment_m, from_state = miner_state(m), …)`
> — lines 4771, 4774

Population (4771) is after the created read (4768) and before `StartWake` (4774). In both loops
the recorded pair is the head's true `(AssignmentID, assignment_version)` at creation, so a
later `T12` departure identifies exactly the version the miner is waking on. **PASS.**

## 5. Criterion 3 — `RollbackParticipantSetup` / `RollbackTemplateRefreshSetup` iterate the map and pass `assignment_version_ref(aid, ver)` (exact, never null) to the legal `T12` — PASS

### 5.1 `RollbackParticipantSetup`

The rollback iterates `assignment_by_miner` in stable `MinerID` order and, for any miner still
`WAKING`, departs it via the legal `WAKING -> OFFLINE` edge (`T12`) with the exact version:

> `FOR EACH (MinerID m, (aid, ver)) in setup_txn.assignment_by_miner (stable order by MinerID):`
> `  IF miner_state(m) = WAKING:`
> `    SET tr <- CALL ApplyMinerStateTransition(m, WAKING, OFFLINE,`
> `           transition_envelope = setup_txn.rollback_envelope, reason = cancellation,          # W1: complete envelope; X7 canonical; T12`
> `           assignment_ref = assignment_version_ref(aid, ver),                                 # X2: EXACT version, never null`
> `           candidate_id = null, propagation_id = null)   # F6`
> — `RollbackParticipantSetup`, `STAGE_01_PROTOCOL_PSEUDOCODE.md`, lines 1694–1699

The input contract confirms the map is part of the transaction shape the rollback consumes:

> `INPUTS: RoundContext, setup_txn   # W1/X2: { rollback_envelope, wakes: [WakeEventRef], created_assignments: [AssignmentID],`
> `                                  #   prior_states: {MinerID -> state}, assignment_by_miner: {MinerID -> (AssignmentID, assignment_version)} }`
> — lines 1679–1680

### 5.2 `RollbackTemplateRefreshSetup`

Identical discipline over the same transaction shape ("same shape as `RollbackParticipantSetup`'s
`setup_txn` (with `rollback_envelope` AND `assignment_by_miner`)", line 1719):

> `FOR EACH (MinerID m, (aid, ver)) in setup_txn.assignment_by_miner (stable order by MinerID):`
> `  IF miner_state(m) = WAKING:`
> `    SET tr <- CALL ApplyMinerStateTransition(m, WAKING, OFFLINE,`
> `           transition_envelope = setup_txn.rollback_envelope, reason = cancellation,          # W1: complete envelope; X7 canonical; T12`
> `           assignment_ref = assignment_version_ref(aid, ver),                                 # X2: EXACT version, never null`
> `           candidate_id = null, propagation_id = null)   # F6`
> — `RollbackTemplateRefreshSetup`, `STAGE_01_PROTOCOL_PSEUDOCODE.md`, lines 1728–1733

In both procedures the `assignment_ref` is `assignment_version_ref(aid, ver)`, where `(aid, ver)`
is the pair recorded in criterion 2 — the exact head. The subsequent close loop then closes that
same `aid (version ver)` head with canonical fields (lines 1702–1706 / 1735–1739), so the audit,
release, and close all name one version. **PASS.**

## 6. Criterion 4 — `RollbackRecoveryAssignmentPlan` passes `item.assignment_version` (never null) — PASS

The recovery-plan rollback consumes a `rollback_record` of per-item records and departs each
still-`WAKING` miner on its plan-created head via `T12` with the exact per-item version:

> `FOR EACH item in rollback_record.items (stable order):`
> `  IF miner_state(item.MinerID) = WAKING AND item.AssignmentID is item.MinerID's bound live head:`
> `    SET tr <- CALL ApplyMinerStateTransition(item.MinerID, WAKING, OFFLINE,`
> `           transition_envelope = item.rollback_envelope, reason = cancellation,           # X2/X7: complete envelope; legal T12`
> `           assignment_ref = assignment_version_ref(item.AssignmentID, item.assignment_version),   # X2: EXACT version, never null`
> `           candidate_id = null, propagation_id = null)   # F6/X8`
> — `RollbackRecoveryAssignmentPlan`, `STAGE_01_PROTOCOL_PSEUDOCODE.md`, lines 3710–3715

The `item.assignment_version` consumed here is the **actual** version captured by
`CommitRecoveryAssignmentPlan` when the head was created — from the reserve-activation result:

> `IF r = reserve_activation_committed(mid, aid, aver, wref):`
> `  ADD rollback_item(MinerID = spec.MinerID, AssignmentID = aid, assignment_version = aver, WakeEventRef = wref, …) to created_items          # X1: ACTUAL refs`
> — lines 3635–3638

and from the range-(re)assignment result:

> `ADD rollback_item(MinerID = spec.MinerID, AssignmentID = rr.AssignmentID,`
> `      assignment_version = assignment_version(rr.AssignmentID), WakeEventRef = rr.WakeEventRef, …) to created_items   # X1/W4`
> — lines 3665–3666

So the version threaded into the `T12` departure is the immutable creation version of the exact
plan-created head, consistent with the §0.8 `rollback_item` field note (line 788). **PASS.**

## 7. Criterion 5 — no rollback passes a null/unversioned `assignment_ref` while a setup/plan-created `PENDING` head is held — PASS

An exhaustive grep of every `assignment_ref =` site in `STAGE_01_PROTOCOL_PSEUDOCODE.md`
resolves the three rollback `WAKING -> OFFLINE` (`T12`) departures — lines 1698, 1732, and
3714 — **all** to an exact `assignment_version_ref(...)` (criteria 3 and 4 above). The only three
occurrences of the literal `assignment_ref = null` are non-rollback edges on which the miner
holds no head:

- line 1891 — `T1` (`NONE -> REGISTERED`, `MinerRegister`): registration; no assignment exists;
- line 1894 — `T2` (`REGISTERED -> RESERVE`, admit to reserve): no head held;
- line 2316 — `T17` (`OFFLINE -> REGISTERED`, adversarial rejoin): the rejoin precedes any head —
  a fresh `PENDING` is created only afterward, via `RangeAssign` (line 2317).

None of the three is a rollback of a `WAKING` miner holding a setup-created or plan-created
`PENDING` head, so the "never `assignment_ref = null`" guarantee of §0.8 (lines 793–797) and of
the §0.8 `rollback_item` note (line 788) holds without exception.

The completeness of each rollback is additionally enforced by its residual guard, which refuses
`rollback_completed` while any created head is still live or any affected miner is still `WAKING`:

> `IF any aid in setup_txn.assignment_by_miner remains a live head OR any setup_txn.wakes entry remains pending on EQ`
> `   OR any m in setup_txn.assignment_by_miner remains WAKING:`
> `  RETURN rollback_failed(reason = residual_partial_setup)`
> — `RollbackParticipantSetup`, lines 1707–1709 (and `RollbackTemplateRefreshSetup`, lines 1740–1741)

> `IF any item.WakeEventRef remains pending on EQ`
> `   OR any item.AssignmentID remains a live head`
> `   OR any item.MinerID remains WAKING on a plan-created head:`
> `  RETURN rollback_failed(reason = residual_partial_assignment)`
> — `RollbackRecoveryAssignmentPlan`, lines 3725–3728

A rollback that could not name (and therefore could not depart/close) a held head cannot pass
these guards, so a null/unversioned departure of a still-held head is unreachable in a completed
rollback. **PASS.**

## 8. Test-vector linkage

The Stage-1X blocking test vectors registered against requirement **R177** in
`STAGE_01_TRACEABILITY_MATRIX.csv` (planned artifact `STAGE_01X_SEMANTIC_TEST_VECTORS`) exercise
this correction on the exact named procedures:

- **TV201 (setup-rollback version exactness).** *"a setup rollback passes the exact
  `assignment_version_ref` from `assignment_by_miner` and never a null ref"* (R177). This vector
  is the direct dynamic witness for criteria 1–3 and 5 of this audit: it drives
  `RollbackParticipantSetup` / `RollbackTemplateRefreshSetup` through the T12 departure at
  lines 1698 / 1732 and asserts the `assignment_ref` equals the `(aid, ver)` recorded at
  lines 1623 / 4771 — and is never `null`.

- **TV199 (recovery-rollback — version-exact aspect).** *"`RollbackRecoveryAssignmentPlan`
  departs a still-`WAKING` committed miner to `OFFLINE` via `T12` with the exact
  `assignment_version_ref` and `rollback_envelope` and returns `rollback_completed` only after no
  miner is `WAKING`"* (R177). The version-exact aspect of TV199 is the dynamic witness for
  criterion 4: the `assignment_ref` passed at line 3714 must be
  `assignment_version_ref(item.AssignmentID, item.assignment_version)` for the exact plan-created
  head, and the residual guard (lines 3725–3728) must have cleared before `rollback_completed`.

- **Supporting: TV198 (record fidelity).** *"`CommitRecoveryAssignmentPlan` builds a
  `rollback_record` whose items carry the exact `AssignmentID` `assignment_version`
  `WakeEventRef` and before-image for every committed activation"* (R177) — the provenance for
  the exact `item.assignment_version` that TV199 later consumes (lines 3636 / 3665–3666).

## 9. Cross-document consistency

The X2 contract is stated coherently across all four authoritative documents, with no divergence
in field name, population order, or the "exact version, never null" clause:

- **Pseudocode** (`STAGE_01_PROTOCOL_PSEUDOCODE.md`): §0.8 declaration lines 793–797 and 788;
  populated at lines 1623 / 4771; consumed at lines 1698 / 1732 / 3714. **↔**
- **Round state machine** (`STAGE_01_ROUND_STATE_MACHINE.md §3.10b`, "X2 — every T12 rollback
  binds the exact assignment version", lines 691–694): *"`participant_setup_txn` / `refresh_setup_txn`
  carry `assignment_by_miner : MinerID -> (AssignmentID, assignment_version)`, populated after
  `assignment_created` and before `StartWake`; `RollbackParticipantSetup` /
  `RollbackTemplateRefreshSetup` pass that exact version as `assignment_ref` … never `null` when the
  miner holds a setup-created `PENDING` head."* **↔**
- **Terminology** (`STAGE_01_TERMINOLOGY.md`, `assignment_by_miner (X2)` entry, lines 873–876):
  *"populated after `assignment_created` and before `StartWake`. Setup rollbacks … iterate it and
  pass the EXACT `assignment_version_ref(aid, ver)` to `T12` (never null when the miner holds a
  setup-created `PENDING` head)."* **↔**
- **Invariant catalogue** (`STAGE_01_INVARIANT_CATALOGUE.md`, `I16` Stage-1X clause, lines 334–338):
  *"X1/X2 … `RollbackRecoveryAssignmentPlan` and the setup rollbacks depart every still-`WAKING`
  miner to `OFFLINE` via the legal `T12` edge using the EXACT assignment version (`rollback_record`
  items / `setup_txn.assignment_by_miner`, never `assignment_ref = null`) and a complete rollback
  envelope."*

All four name the same field, the same after-`assignment_created` / before-`StartWake` population
point, and the same "exact version, never null" rollback consumption. No contradiction found.

## 10. Result

**PASS — correction X2 is fully realised:** both setup transactions declare and initialise
`assignment_by_miner`; both setup loops populate `(AssignmentID, assignment_version)` after
`assignment_created` and before `StartWake`; `RollbackParticipantSetup`,
`RollbackTemplateRefreshSetup`, and `RollbackRecoveryAssignmentPlan` all depart every still-`WAKING`
miner via the legal `T12` edge with the exact `assignment_version_ref` and never a null/unversioned
reference; and the pseudocode, round state machine §3.10b, terminology, and invariant I16 are mutually
consistent.
