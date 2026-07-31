# Stage 1V — Plan-Commit Fidelity Audit (V4, V5)

This is a documentation-only paper audit of two Stage-1V corrections to the recovery
assignment path as edited in
`docs/thesis_revision_v45/stage_01/STAGE_01_PROTOCOL_PSEUDOCODE.md`:

- **V4 — `ReserveActivate` returns actual references.** The reserve-activation entry point
  and its plan-bound mutator return one of three structured transaction dispositions whose
  fields are the ACTUAL references the transaction produced, and a wake-seat failure that
  occurs after a PENDING assignment was created is closed legally rather than left
  half-applied.
- **V5 — commit exactly the prepared plan.** `CommitRecoveryAssignmentPlan` applies the
  EXACT values carried on the prepared specs — it performs no independent re-`SELECT` of the
  reserve miner or range — so what is committed equals what was prepared and validated.

Both are executability / fidelity corrections to the recovery-work and branch-C
redistribution install path. Neither introduces a census value, a residency interval, or a
transition-energy term, and neither alters how the idle policy is accounted; this audit
therefore claims no energy, security, or fairness property and leaves the accepted accounting
baseline unchanged. Every claim below is checked against the pseudocode as currently edited;
line numbers are those of the file at audit time and were re-confirmed by direct search.

Scope: `ReserveActivate` (§10, line 2878), `ReserveActivateFromPlan` (§10, line 2909),
`CreatePendingAssignment` (§ constructor, line 1212), `StartWake` (§ line 1073),
`PrepareRecoveryAssignmentPlan` (§10a, line 3378), `CommitRecoveryAssignmentPlan` (§10a,
line 3410), and the two post-epilogue callers `ApplyRecoveryWorkAfterEpilogue` (§9c, line
2802) and `ApplyRecoveryAssignmentContinuationAfterEpilogue` (§10a, line 3255). Cross-checked
against `STAGE_01_ROUND_STATE_MACHINE.md` §3.10 (Stage-1V addendum, V4/V5 at lines 598–608),
`STAGE_01_INVARIANT_CATALOGUE.md` (I1/I3/I8a/I8b/I9/I10/I17/I18b), and
`STAGE_01_TERMINOLOGY.md` (Stage-1V addendum, lines 800–809).

---

## 1. The defect V4 and V5 close

The recovery installation path had two distinct fidelity gaps, both now retired.

**V4 defect — success without real references, and a stranded post-assignment failure.** The
reserve-activation primitive was a promotion that reported a bare start of activation rather
than a transaction returning the references it created. The current NOTE on `ReserveActivate`
records the corrected contract by contrast: it "returns the V4 structured transaction
disposition (**never a bare `activation_started`**)" (line 2906). A caller that only ever saw
`activation_started` could not record the real `AssignmentID`, `assignment_version`, or
`WakeEventRef`, so `CommitRecoveryAssignmentPlan` could not build a rollback record from
genuine references — the commit-side NOTE names this failure mode directly: rollback metadata
must be built from "the ACTUAL references the transaction returns … **never from undefined
fields**" (lines 3425–3426). Worse, activation always passes through `WAKING` via a
non-blocking `StartWake` (line 2926); if wake seating (or its post-seat transition) failed
*after* a PENDING assignment had already been created, the primitive had no declared
compensation, so the reserve miner could be stranded in an inconsistent partial state.

**V5 defect — commit re-`SELECT`ing independently of prepare.** The mutation half of the
install used to re-derive the reserve miner and range at commit time. Because
`PrepareRecoveryAssignmentPlan` verifies the structural invariants I1/I3/I10/I18b BEFORE any
mutation (line 3400) and returns a compute-only plan, an independent re-`SELECT` inside commit
could bind a *different* reserve miner or range than the one that passed validation — the
committed assignment would then not be the assignment the plan certified. The traceability
matrix names the eliminated hazard as "a commit path re-`SELECT`ing a different reserve miner
or range than the validated plan" (row R154). This is the prepare/commit fidelity gap: the
value that was validated and the value that was mutated could diverge.

---

## 2. V4 corrected contract — three dispositions, actual references

### 2.1 The disposition set

`ReserveActivate` and `ReserveActivateFromPlan` share one RETURNS block of exactly three
mutually exclusive dispositions (lines 2900–2902 and 2942–2944, identical):

| Disposition | Fields | Meaning |
| --- | --- | --- |
| `reserve_activation_committed` | `(MinerID, AssignmentID, assignment_version, WakeEventRef)` | activation seated; every field is an ACTUAL reference of the created assignment / wake |
| `reserve_activation_failed_before_mutation` | `(reason)` | nothing was created; reversible; no rollback record needed |
| `reserve_activation_failed_after_assignment` | `(reason, AssignmentID, rollback_record)` | a PENDING assignment was created then the wake failed; the primitive self-rolled-back and reports the closed assignment plus its rollback record |

The success disposition is constructed from live references, not placeholders. On
`wr = wake_seated(...)`, `ReserveActivateFromPlan` returns
`reserve_activation_committed(MinerID = reserve_miner, AssignmentID = AssignmentID(assignment),
assignment_version = assignment_version(assignment), WakeEventRef = wr.WakeEventRef)` with the
inline annotation "V4: ACTUAL refs" (lines 2930–2931). `WakeEventRef` is threaded straight
from the `StartWake` transaction's `wake_seated(AssignmentID, WakeEventRef, wake_target_time,
resulting_state = WAKING)` result (`StartWake` RETURNS, lines 1124–1127); `AssignmentID` and
`assignment_version` are read off the assignment `CreatePendingAssignment` actually built
(constructor, lines 1228–1234).

The two failure dispositions are distinguished by *whether any mutation occurred*:

- Before any mutation — a revalidation failure (line 2918) or a constructor rejection
  `creation_failed(cf)` (lines 2922–2923) — returns `reserve_activation_failed_before_mutation`
  with "nothing created" / "nothing to roll back" annotations.
- After the PENDING assignment exists — a wake-seat failure — returns
  `reserve_activation_failed_after_assignment` carrying the actual `AssignmentID` and a
  `rollback_record` (lines 2940–2941).

### 2.2 The after-assignment compensation

The wake-failure arm (lines 2932–2941) is the V4 legal-close path. When
`wr` is not `wake_seated`, the assignment already exists and must be unwound legally rather
than abandoned:

1. **Cancel any residual event.** If `wr = wake_transition_failed_after_seat(reason2, wref)`
   and `wref` is still pending on the event queue, it is cancelled (lines 2934–2935); the
   annotation notes `StartWake` already cancelled it, so the step is idempotent.
2. **Close the assignment legally.** `CLOSE assignment as CLOSED (status = CLOSED,
   custody_status = revoked, reason = reserve_activation_wake_failed)` — annotated "J7: no live
   head (I18b)" (line 2936). The close is a declared terminal status, never a silent drop, and
   it leaves the lineage with zero live heads.
3. **Restore the ledgers.** `RESTORE the coverage-state / custody ledgers for candidate_range`
   annotated "(I8a/I8b)" (line 2937), returning the coverage partition and custody model to
   their pre-attempt values.
4. **Assert the miner stayed in RESERVE.** `ASSERT miner_state(reserve_miner) = RESERVE`
   annotated "V4/gate 4: the reserve miner stays RESERVE, not WAKING" (line 2938). Because
   `StartWake` seats the `WakeCompleteEvent` first and applies the `WAKING` transition only
   after a successful seat (canonical order, lines 1086–1089), a seat/transition failure never
   left the miner in `WAKING`; the assertion pins that guarantee at the reserve-activation
   layer.
5. **Build the rollback record from actual values.** `rollback_record(RecoveryInstallID =
   null, created_assignments = {assignment}, created_events = {})` (line 2939) — the record
   names the ACTUAL closed assignment (`created_events` is empty because no wake was ever
   seated on this arm).
6. **Return the declared disposition.** `reserve_activation_failed_after_assignment(reason =
   wr, AssignmentID = AssignmentID(assignment), rollback_record = rollback_record)` (lines
   2940–2941).

The NOTE summarises the guarantee: on a post-assignment wake failure the primitive "closes the
assignment legally, restores the ledgers, and leaves the reserve miner in RESERVE — a declared
failure disposition, never a stranded WAKING miner (gate 4)"; and `PENDING -> CURRENT` still
occurs ONLY at the scheduled `WakeCompleteEvent` on a successful wake (lines 2945–2949).

---

## 3. V5 corrected contract — commit consumes exactly the prepared specs

### 3.1 Selection belongs to prepare, not commit

The Stage-1V edit relocates selection out of the mutation path. `ReserveActivate` keeps a
`SELECT` — but only as the *ordinary entry point*: it selects the reserve miner (line 2891),
the candidate range (line 2892), and derives F4 provenance (lines 2894–2897), then delegates
the mutation with `RETURN CALL ReserveActivateFromPlan(RoundContext, reserve_miner =
reserve_miner, candidate_range = candidate_range, assignment_origin = origin, source_assignment
= source, scheduling_context = scheduling_context)` (lines 2898–2899). Its EFFECTS comment is
explicit: "SELECTION belongs to the ordinary entry point (or `PrepareRecoveryAssignmentPlan`)
… then delegates the MUTATION to the plan-bound `ReserveActivateFromPlan` — so the commit path
(`CommitRecoveryAssignmentPlan`) never re-SELECTs" (lines 2888–2890).

`ReserveActivateFromPlan` accordingly takes the selected values as INPUTS —
`reserve_miner, candidate_range, assignment_origin, source_assignment, scheduling_context` —
annotated "EXACT plan-selected values (no independent SELECT)" (lines 2910–2911). It contains
no `SELECT`; it revalidates and mutates the values it was handed.

### 3.2 Commit binds spec fields to parameters — the V5 replacement

`CommitRecoveryAssignmentPlan`, for each `RESERVE_ACTIVATION` spec, replaces any
`ReserveActivate(spec.deficit)`-style re-selection with a direct plan-bound call (lines
3428–3430):

```
SET r <- CALL ReserveActivateFromPlan(RoundContext, reserve_miner = spec.MinerID, candidate_range = spec.range,
               assignment_origin = spec.origin, source_assignment = spec.source_assignment,
               scheduling_context = scheduling_context)         # V5/V4: plan-bound; returns ACTUAL refs
```

The parameter binding is one-to-one from the spec, with no derivation:

| `ReserveActivateFromPlan` parameter | Bound at commit from | Prepared spec field | Pseudocode |
| --- | --- | --- | --- |
| `reserve_miner` | `spec.MinerID` | RESERVE_ACTIVATION spec `MinerID` (the selected reserve miner) | 3428 ← 3391 |
| `candidate_range` | `spec.range` | spec `range` (candidate_range) | 3428 ← 3391 |
| `assignment_origin` | `spec.origin` | spec `origin` (`ORIGINAL` \| `REASSIGNED`) | 3429 ← 3392 |
| `source_assignment` | `spec.source_assignment` | spec `source_assignment` | 3429 ← 3392 |
| `scheduling_context` | the commit's threaded `scheduling_context` | `POST_EPILOGUE(pctx)` from the caller | 3430 ← 3411 |

The inline annotation at the loop head is categorical: "the commit uses the spec's EXACT
plan-selected values (MinerID / range / origin / source) — NO independent SELECT" (lines
3424–3425), and the closing NOTE repeats that it "commits EXACTLY the prepared plan (the spec's
MinerID / range / origin / source — no independent SELECT, V5), via the plan-bound
`ReserveActivateFromPlan`" (lines 3470–3471). No `SELECT` statement appears anywhere inside
`CommitRecoveryAssignmentPlan` (lines 3410–3468).

### 3.3 Revalidate-before-mutate

Commit re-checks the invariants against current state before touching anything: "IF the plan's
specs now violate I1 OR I3 OR I10 OR I18b: RETURN
install_failed_before_mutation(reason = revalidation_failed)" annotated "nothing created"
(lines 3419–3420). The plan-bound primitive revalidates a second time at the point of use, on
exactly the specs it was handed: "REVALIDATE the EXACT specs immediately BEFORE mutation (a
concurrent same-time change may have invalidated them)"; a violation returns
`reserve_activation_failed_before_mutation(reason = revalidation_failed)` with "nothing
created" (lines 2916–2918). Validation and mutation thus operate on the same values —
the fidelity property V5 asserts.

### 3.4 Capture actual references

On success the commit records the transaction's ACTUAL references, not the plan's predictions:
`IF r = reserve_activation_committed(mid, aid, aver, wref): ADD aid to created_assignments; ADD
wref to created_events` annotated "ACTUAL references from the transaction" (lines 3431–3432).
The redistribution branch does the same for its `StartWake` results, capturing
`wake_seated(waid, wref, wtt, ws)` and adding `wref` to `created_events` (lines 3460–3461).
`created_assignments` and `created_events` accumulate real references in stable order and are
sealed into `plan.rollback_metadata` on any post-mutation failure (lines 3437–3438, 3444–3445,
3463–3464) and on success (lines 3466–3467).

---

## 4. Prepare → Commit fidelity chain

The following table traces each committed field from `PrepareRecoveryAssignmentPlan` through
the carried spec into `CommitRecoveryAssignmentPlan` and on to `ReserveActivateFromPlan`,
showing there is no independent re-selection at any hop. Prepare fixes each
`RESERVE_ACTIVATION` spec as `{ kind = RESERVE_ACTIVATION, MinerID (the selected reserve
miner), range (candidate_range), origin (ORIGINAL|REASSIGNED), source_assignment,
required_wake_operations }` (lines 3390–3393).

| Committed field | Fixed in Prepare | Carried on spec | Consumed in Commit | Passed to `ReserveActivateFromPlan` | Re-selected in commit? |
| --- | --- | --- | --- | --- | --- |
| reserve miner | `plan.selected_reserve_miners` / `spec.MinerID` (3389, 3391) | `spec.MinerID` | `spec.MinerID` (3428) | `reserve_miner` (3428) | No |
| candidate range | `plan.accepted_unsearched_suffixes` / `spec.range` (3388, 3391) | `spec.range` | `spec.range` (3428) | `candidate_range` (3428) | No |
| provenance origin | `spec.origin` (3392) | `spec.origin` | `spec.origin` (3429) | `assignment_origin` (3429) | No |
| source assignment | `plan.source_assignment_versions` / `spec.source_assignment` (3387, 3392) | `spec.source_assignment` | `spec.source_assignment` (3429) | `source_assignment` (3429) | No |
| required wakes | `spec.required_wake_operations` / `plan.required_wake_operations` (3392, 3398) | `spec.required_wake_operations` | redistribution `StartWake` loop (3457) | n/a (implied by reserve activation) | No |
| creation order | `new_pending_assignment_specs`, STABLE order by MinerID then CandidateID (3397) | plan order | `FOR EACH spec … (STABLE creation order)` (3422) | n/a | No |

Every reserve-activation input consumed by the mutation is the field the plan wrote; the only
`SELECT` in the whole chain is in `PrepareRecoveryAssignmentPlan` (or the ordinary
`ReserveActivate` entry point), before invariant verification. The commit path re-verifies but
never re-selects. The two post-epilogue callers preserve the chain end-to-end:
`ApplyRecoveryWorkAfterEpilogue` prepares then commits with the same episode/action (lines
2828, 2836), and `ApplyRecoveryAssignmentContinuationAfterEpilogue` does the same for the
`RANGE_REDISTRIBUTION_REQUIRED` continuation (lines 3291, 3305), each threading
`POST_EPILOGUE(pctx)` into commit so nested wakes are seated strictly later.

---

## 5. Rollback and consistency argument for the after-assignment failure path

The after-assignment path is the delicate one: a PENDING assignment exists, the wake has
failed, and the system must return to a consistent state without leaving a half-installed head.
The argument that it does so has three parts.

**(a) Self-rollback inside the primitive is complete and leaves no live head.** On the wake
failure arm `ReserveActivateFromPlan` cancels any residual event (2934–2935), closes the
assignment `CLOSED / revoked` (2936), restores the I8a/I8b ledgers (2937), and asserts the
miner is back in `RESERVE` (2938). The close is annotated "no live head (I18b)" — so the
lineage the constructor opened at version 1 (constructor, lines 1228–1234) ends with zero live
heads, satisfying I18b's "zero after closure" clause (catalogue line 508). Coverage returns to
its partition (I8a, catalogue line 496) and custody to its pre-attempt model (I8b, catalogue
line 497). No overlap can persist because the range is closed and its ledgers restored (I1/I10,
catalogue lines 489, 499).

**(b) The disposition truthfully reports what was created.** The `rollback_record` names
`created_assignments = {assignment}` and `created_events = {}` from the actual references (line
2939), and the disposition carries the actual `AssignmentID` (lines 2940–2941). A caller
therefore receives a faithful account of the single object created and already closed — not an
undefined field.

**(c) The commit caller composes the self-rollback with the rest of the install.** When commit
observes `r = reserve_activation_failed_after_assignment(reason, aid, rr)` it treats the spec
as already self-rolled-back — "this spec ALREADY self-rolled-back (its assignment closed, miner
stays RESERVE)" (lines 3440–3441) — and then reconciles the *earlier* specs of the same
install:

- If no earlier spec had mutated (`created_assignments` and `created_events` both empty), the
  whole install is reversible and commit returns `install_failed_before_mutation(reason =
  r.reason)` — "only this spec touched, and it self-rolled-back" (lines 3442–3443).
- Otherwise commit seals `plan.rollback_metadata` from the ACTUAL earlier references and
  returns `install_failed_after_mutation(reason = r.reason, plan.rollback_metadata)` (lines
  3444–3446), handing the caller a rollback record `RollbackRecoveryAssignmentPlan` (line 3476)
  can replay to close the earlier heads legally and restore their ledgers.

The composition is sound precisely because the failing spec self-cleaned and reported real
references: commit never has to reason about a partially-mutated failing spec, only about the
earlier fully-committed ones. This is the V4 property (actual references, legal close) enabling
the V5 property (a commit that mirrors the plan) to remain consistent under partial failure.

---

## 6. Traceability to invariants and terminology

**Requirements.** `STAGE_01_TRACEABILITY_MATRIX.csv` carries both corrections as explicit
rows:

- **R153 (V4)** — "`ReserveActivate` returns actual transaction references … if wake seating
  fails after the PENDING assignment is created the assignment is closed legally the
  coverage/custody ledgers restored and the reserve miner left in RESERVE … rollback_metadata
  is built only from the actual returned references", with eliminated hazard "a reserve
  activation returning only `activation_started`; a reserve miner stranded WAKING after a
  wake-seat failure; rollback metadata built from undefined fields", invariants I1;I8a;I8b;I10;I17.
- **R154 (V5)** — "Commit exactly the prepared plan … `CommitRecoveryAssignmentPlan` uses those
  exact values via the plan-bound `ReserveActivateFromPlan` with no independent SELECT
  revalidating the exact specs immediately before mutation", eliminated hazard "a commit path
  re-SELECTing a different reserve miner or range than the validated plan", invariants
  I1;I3;I10;I18b.
- **R146 (U5)** — the enclosing named-procedure requirement (Prepare/Commit/Rollback) that V4/V5
  refine.

**Invariants** (`STAGE_01_INVARIANT_CATALOGUE.md`):

| Invariant | Statement (catalogue) | Role in V4/V5 |
| --- | --- | --- |
| I1 | No overlap among valid active assignments (line 489) | revalidated before mutation (2917, 3419); restored on rollback |
| I3 | Accepted solution matches current RoundID/TemplateID (line 491) | revalidated before commit (3419) |
| I8a | Accepted coverage states partition the assigned domain exactly (line 496) | restored on after-assignment close (2937) |
| I8b | Custody / provenance model (line 497) | restored on after-assignment close (2937) |
| I9 | Reassignments carry complete provenance (line 498) | REASSIGNED provenance set by the constructor (1240–1245); carried as `source_assignment` |
| I10 | Reserve activation adds no overlap (line 499) | revalidated at both layers (2917, 3419) |
| I17 | H_active = H_honest + H_adversarial, census-deterministic (line 506) | reserve activation is the census-changing V6 work class; unchanged by a failed, rolled-back activation |
| I18b | Every OPEN lineage has exactly one live head; zero after closure (line 508) | the legal `CLOSED` close leaves zero live heads (2936) |

**Gate 4.** The reserve miner never lingers in `WAKING`: `StartWake` cancels a post-seat
transition on failure (lines 1116–1120, "gate 4"), and `ReserveActivateFromPlan` asserts
`miner_state = RESERVE` on the failure arm (line 2938, "V4/gate 4"). The `WAKING`-without-live-
`WakeCompleteEvent` state is unreachable through this path.

**Terminology** (`STAGE_01_TERMINOLOGY.md`, Stage-1V addendum). The
`reserve_activation_committed` / `ReserveActivateFromPlan` entry (lines 804–809) states the
three-disposition signature and that "`ReserveActivateFromPlan` uses the plan's EXACT selected
values (V5); a wake-seat failure after the PENDING assignment closes it legally and leaves the
reserve miner in `RESERVE`." The `StartWake` transaction entry (lines 800–803) supplies the
`wake_seated` / `wake_schedule_failed_before_transition` / `wake_transition_failed_after_seat`
result set the V4 dispositions consume.

**Round state machine** (`STAGE_01_ROUND_STATE_MACHINE.md` §3.10, "What happens after a
security-floor violation"). The Stage-1V addendum states V4 (lines 598–603) and V5 (lines
605–608) in the same words as the pseudocode: V4 gives the three dispositions and the
legal-close-plus-`RESERVE` guarantee; V5 states that Prepare "selects the reserve miners /
ranges / origin / source / creation order / wake operations" and Commit "uses those EXACT
values via the plan-bound `ReserveActivateFromPlan` (no independent SELECT), revalidating the
exact specs immediately before mutation, and builds `rollback_metadata` from the ACTUAL
references the transactions return."

---

## 7. Findings

- **V4 is present and internally consistent.** Both `ReserveActivate` (2900–2902) and
  `ReserveActivateFromPlan` (2942–2944) declare the identical three-disposition RETURNS block;
  the success disposition is built from actual `AssignmentID` / `assignment_version` /
  `WakeEventRef` (2930–2931); the after-assignment arm closes legally, restores I8a/I8b ledgers,
  asserts `RESERVE`, and returns a `rollback_record` built from the actual closed assignment
  (2932–2941). The NOTE confirms "never a bare `activation_started`" (2906).
- **V5 is present and internally consistent.** `CommitRecoveryAssignmentPlan` binds
  `ReserveActivateFromPlan`'s parameters directly from `spec.MinerID` / `spec.range` /
  `spec.origin` / `spec.source_assignment` (3428–3430), revalidates before mutation (3419),
  captures actual references (3431–3432), and contains no `SELECT`. Prepare fixes each spec's
  exact fields in stable order (3390–3397); the fidelity chain (§4) shows no re-selection at any
  hop.
- **Cross-document agreement.** The pseudocode, the §3.10 Stage-1V addendum, the Stage-1V
  terminology addendum, the invariant catalogue, and traceability rows R153/R154 state the same
  contract in the same terms. No contradictions were found, and no expected content was missing.
