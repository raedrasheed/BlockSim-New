# Stage 1Z — Pre-Mutation Snapshot Audit (correction Z2)

This audit verifies correction **Z2** of the Stage-1Z formal-specification revision: the ledger *before-image*
(`coverage_custody_before_image`) is captured **before** the PENDING-assignment constructor mutates the coverage-state /
custody ledgers, so a setup rollback restores the exact **pre-constructor** I8a/I8b values. All pseudocode is quoted
verbatim from the current `STAGE_01_PROTOCOL_PSEUDOCODE.md` (line anchors approximate; the quoted text is authoritative).
Scope is confined to the PoCol protocol specification and the idle policy within PoCol. This is a documentation-only
audit; it edits no specification file and preserves the A1 baseline `8.420833333 kWh`.

The audited object is the **capture-then-create order**: for every setup transaction item the before-image line must
*precede* the `CreatePendingAssignment` call, and on a creation failure the captured before-image must be discarded with
no transaction item created. This supersedes the Y-era order (before-image captured *after* creation, post-mutation).

---

## 1. Check (1) — the before-image is captured BEFORE `CreatePendingAssignment` in both setup procedures

### 1.1 `PrepareParticipantsForNewRound` (participant-setup path)

The capture line precedes the constructor call. From `PROCEDURE PrepareParticipantsForNewRound` (~L1711–L1720):

```
# Z2: capture the PRE-CONSTRUCTOR I8a/I8b before-image BEFORE CreatePendingAssignment mutates custody_status /
#   assignment_ledger. On a creation failure the before_image is DISCARDED and NO transaction item is created.
SET before_image <- coverage_custody_before_image(spec.range)   # Z2/I20: snapshot BEFORE creation
# W7: build the head; BRANCH on the constructor result BEFORE reading AssignmentID, setting lease fields, or
#   recording it in the transaction. A creation failure is a DECLARED setup failure (nothing created).
SET cr <- CALL CreatePendingAssignment(RoundContext, m, spec.range,
                assignment_origin = spec.origin, source_assignment = spec.source, reason = spec.rr)   # F4/W7
```

The `SET before_image <- coverage_custody_before_image(spec.range)` statement is **textually and executably prior** to
`SET cr <- CALL CreatePendingAssignment(...)`. **Order: capture-then-create — PASS.**

### 1.2 `ContinueTemplateRefreshAssignmentSetup` (template-refresh-setup path)

The same pattern holds. From `PROCEDURE ContinueTemplateRefreshAssignmentSetup` (~L4980–L4985):

```
# Z2: capture the PRE-CONSTRUCTOR I8a/I8b before-image BEFORE CreatePendingAssignment mutates the ledgers.
SET before_image <- coverage_custody_before_image(fr)   # Z2/I20: snapshot BEFORE creation
SET cr <- CALL CreatePendingAssignment(RoundContext, m, fr,
                assignment_origin = ORIGINAL, source_assignment = null, reason = null)   # F4/W7
IF cr is assignment_creation_failed(reason):
  SET refresh_setup_error <- assignment_creation_failed(reason) ; CONTINUE   # W7/Z2: nothing created; discard before_image
```

The `SET before_image <- coverage_custody_before_image(fr)` statement is prior to `SET cr <- CALL
CreatePendingAssignment(...)`. **Order: capture-then-create — PASS.**

### 1.3 Why "before creation" is exactly "pre-mutation"

`CreatePendingAssignment` is the sole mutator of `custody_status` and `assignment_ledger` on this path. Its constructor
body writes custody and ledgers only on the success branch (from `PROCEDURE CreatePendingAssignment`, ~L1400–L1411):

```
CASE ORIGINAL:
  SET custody_status(range)                <- original
  ...
CASE REASSIGNED:
  ...
  SET custody_status(range)                <- reassigned
  ...
APPEND A to assignment_ledger                                        # supports I8a
RETURN assignment_created(A)                                         # W7: the ONLY success disposition
```

Because these are the mutating writes, a snapshot taken on the line *immediately preceding* the `CreatePendingAssignment`
call is by construction the **pre-mutation** state of `custody_status(range)` / `assignment_ledger`. **PASS.**

---

## 2. Check (2) — a creation failure discards the before-image and creates no item

`CreatePendingAssignment` is an explicit-result constructor: on the guard failure it returns
`assignment_creation_failed(reason)` and creates nothing (~L1377–L1381):

```
IF range is NOT disjoint from all valid active assignments (I1)
   OR custody_status(range) = completed OR coverage_state(range) = searched
   OR RoundID(RoundContext) != RoundID_current OR (a committed TemplateID is required AND TemplateID_committed is absent)
   OR (assignment_origin = REASSIGNED AND (source_assignment = null OR reason is NOT a permitted reassignment reason)):
  RETURN assignment_creation_failed(reason = overlap_or_custody_or_provenance_or_epoch_violation)   # W7/X6: nothing created
```

Both setup procedures branch on that result **before** building any `setup_rollback_item`, so the captured `before_image`
is abandoned (never stored in an item) and no item is appended:

- `PrepareParticipantsForNewRound` (~L1718–L1720):

```
IF cr is assignment_creation_failed(reason):
  SET participant_setup_error <- assignment_creation_failed(reason)   # W7/Z2: nothing created; discard before_image
  CONTINUE
```

- `ContinueTemplateRefreshAssignmentSetup` (~L4984–L4985):

```
IF cr is assignment_creation_failed(reason):
  SET refresh_setup_error <- assignment_creation_failed(reason) ; CONTINUE   # W7/Z2: nothing created; discard before_image
```

In both, the `CONTINUE` occurs *before* the item-construction line (`SET item <- setup_rollback_item(...)` at ~L1724 /
~L4988), so on a creation failure the local `before_image` is discarded and **no transaction item is added** — nothing is
later restored for an assignment that was never created. **PASS.**

For contrast, the success branch is where the before-image is retained: it is copied into the one complete
`setup_rollback_item` (which is appended **before** `StartWake`). From `PrepareParticipantsForNewRound` (~L1724–L1727):

```
SET item <- setup_rollback_item(MinerID = m, AssignmentID = AssignmentID(a), assignment_version = assignment_version(a),
      pre_wake_state = spec.from, before_image = before_image, WakeEventRef = null, wake_result = null,
      rollback_envelope = dispatch_envelope)   # Z2/Z3/Z6: complete except wake fields
ADD item to participant_setup_txn.rollback_items
```

and identically in `ContinueTemplateRefreshAssignmentSetup` (~L4988–L4991, `before_image = before_image`,
`ADD item to refresh_setup_txn.rollback_items`). So exactly one item carrying the pre-constructor before-image exists per
*created* assignment, and zero items exist for a failed creation. **PASS.**

---

## 3. Check (3) — invariant I20 formalises the pre-constructor restore

`STAGE_01_INVARIANT_CATALOGUE.md` defines I20 (~L539–L547):

```
### I20 — A setup/recovery rollback restores the exact pre-constructor coverage/custody ledgers (Stage 1Z, Z2).

- Formal statement. For every setup transaction item (and every recovery-plan rollback item), the
  `before_image` (`coverage_custody_before_image`) is the I8a/I8b coverage-state / custody-ledger snapshot captured
  immediately before `CreatePendingAssignment` (or the plan-bound constructor) mutates `custody_status(range)` and
  appends to `assignment_ledger`. On rollback, `AbortPendingWakeForRollback` (setup) / `RollbackRecoveryAssignmentPlan`
  (recovery) RESTORES the ledgers for the item's range from that `before_image`, so the post-rollback I8a/I8b values equal
  the exact pre-constructor values — never a post-mutation snapshot. On a creation failure the `before_image` is discarded
  and no transaction item exists, so nothing is restored for an assignment that was never created.
```

I20 exists, is titled for Z2, and states precisely that (a) the before-image is the snapshot taken *immediately before*
the constructor mutates `custody_status(range)` / `assignment_ledger`, and (b) `rollback(before_image)` restores the
**exact pre-constructor** I8a/I8b values (never a post-mutation snapshot). Its scope note also records that the invariant
"does not change the A1 baseline (`8.420833333 kWh`)". **PASS.**

---

## 4. Check (4) — rollback restores from the captured before-image

`AbortPendingWakeForRollback` is the single named operation that restores the ledgers, and it restores from the item's
before-image. From `PROCEDURE AbortPendingWakeForRollback` (~L1831–L1832):

```
# (6) Y5/Z2: restore the coverage-state / custody ledgers from the PRE-CONSTRUCTOR before-image (I8a/I8b/I20).
RESTORE the coverage-state / custody ledgers for AssignmentID's range FROM coverage_custody_before_image
```

The before-image reaches this operation from the setup transaction item without alteration: `RollbackParticipantSetup`
passes `coverage_custody_before_image = item.before_image` (~L1866), and `RollbackTemplateRefreshSetup` does the same;
`AbortPendingWakeForRollback` accepts it as the `coverage_custody_before_image` input (~L1792–L1793). Because that
before-image was the pre-mutation snapshot (Section 1) and `CreatePendingAssignment` performs the only intervening
mutation (Section 1.3), the `RESTORE ... FROM coverage_custody_before_image` yields exactly the pre-constructor I8a/I8b
state required by I20. The canonical assignment close (~L1828–L1830) and the restore are owned solely here, so no double
close and no post-mutation restore can occur. **PASS.**

---

## 5. Recovery-plan path (`CommitRecoveryAssignmentPlan`) — confirmed already correct (pre-X)

The recovery-plan install captures its before-image before its plan-bound constructor, so the recovery path was already
correct prior to the X/Z corrections and remains consistent with Z2. From `PROCEDURE CommitRecoveryAssignmentPlan`
(~L3832–L3833), inside the per-spec loop and *before* the `ReserveActivateFromPlan` / `RangeReassignFromPlan` /
`RangeAssignFromPlan` constructor calls:

```
SET pre_wake_state <- miner_state(spec.MinerID)                                            # X1
SET before_image   <- coverage_custody_before_image(spec.range)                            # X1: I8a/I8b snapshot
```

The captured `before_image` is stored per item as `coverage_custody_before_image = before_image` (~L3842 / ~L3872) and,
on rollback, `RollbackRecoveryAssignmentPlan` forwards `coverage_custody_before_image = item.coverage_custody_before_image`
into `AbortPendingWakeForRollback` (~L3919–L3920), which runs the same `RESTORE ... FROM coverage_custody_before_image`.
I20's formal statement explicitly ranges over "every recovery-plan rollback item" as well as the setup items, so the
setup-path Z2 correction and the pre-existing recovery-path X1 capture are governed by the same invariant. **PASS
(confirmed, unchanged).**

---

## 6. Contrast with the superseded Y-era order

Under the Y layer the before-image was captured **after** the constructor (post-mutation), via per-miner parallel maps.
`STAGE_01_TERMINOLOGY.md` still describes the withdrawn Y-era mechanism (~L925–L927):

```
- `setup_txn.wake_by_miner` / `setup_txn.before_image_by_miner` (Y4). Per-miner maps captured after
  `assignment_created` and before `StartWake`, so a setup rollback can cancel the EXACT wake and restore the EXACT
  before-image for every affected miner through the one named operation.
```

`STAGE_01Z_SUPERSESSION_REGISTER.md` records the exact before→after change for Z2: from "The setup before-image was
captured AFTER `CreatePendingAssignment` (post-mutation)" to "The before-image is captured BEFORE
`CreatePendingAssignment` (pre-constructor); invariant I20 requires rollback to restore the exact pre-constructor I8a/I8b
values". The audited current pseudocode (Sections 1–2) matches the *after* column: capture-then-create, before-image
discarded on creation failure. **The Z2 supersession is realised in the pseudocode.**

---

## 7. Test-vector linkage (TV221)

`STAGE_01Z_SEMANTIC_TEST_VECTORS.md` provides **TV221** (~L39–L46), which exercises precisely the audited behaviour:

```
## TV221 — The before-image is captured before creation; rollback restores it (Z2/I20)

- Procedures: `PrepareParticipantsForNewRound` / `ContinueTemplateRefreshAssignmentSetup`, `CreatePendingAssignment`,
  `AbortPendingWakeForRollback`.
- Setup: a setup item captures `before_image = coverage_custody_before_image(range)` BEFORE `CreatePendingAssignment`;
  the constructor then sets `custody_status(range)` and appends to `assignment_ledger`; the setup later fails and rolls back.
- Expected: the item's `before_image` is the pre-constructor I8a/I8b state; on rollback the coverage/custody ledgers
  for the item's range are restored to exactly those pre-constructor values (invariant I20) — never the post-mutation state.
```

TV221 names the same two setup procedures, the same constructor, and the same rollback operation as this audit, and its
"Expected" clause is the exact I20 restore-to-pre-constructor obligation verified in Sections 1–4. The vector's summary
row also maps `TV221 | Z2/I20 | seating procedures, CreatePendingAssignment, AbortPendingWakeForRollback`. **Linkage
consistent — PASS.** (The adjacent TV222–TV225 cover the sibling Z3/Z4/Z5 clauses and are out of scope here.)

---

## 8. Cross-document consistency

| Artifact | Locus | Statement | Agrees with audited pseudocode |
|---|---|---|---|
| `STAGE_01_PROTOCOL_PSEUDOCODE.md` | `PrepareParticipantsForNewRound` (~L1713, L1716); `ContinueTemplateRefreshAssignmentSetup` (~L4981, L4982) | `SET before_image <- coverage_custody_before_image(...)` precedes `CALL CreatePendingAssignment(...)`; failure branch discards, `CONTINUE` | — (source of truth) |
| `STAGE_01_ROUND_STATE_MACHINE.md` | §3.10d, "Z2 (pre-mutation ledger snapshot)" (~L781–L783) | before-image captured "IMMEDIATELY BEFORE `CreatePendingAssignment`"; rollback restores exact pre-constructor I8a/I8b (I20); on creation failure discarded and no item made | ✓ matches |
| `STAGE_01_INVARIANT_CATALOGUE.md` | I20 (~L539); I16 Stage-1Z clause Z2 (~L367–L368) | I20 formalises the pre-constructor restore; I16 Z2 clause: "each setup item's `before_image` is captured BEFORE `CreatePendingAssignment` and rollback restores the exact pre-constructor ledgers (see I20)" | ✓ matches |
| `STAGE_01_TERMINOLOGY.md` | `coverage_custody_before_image` — pre-mutation snapshot (Z2/I20) (~L950–L952) | snapshot "captured immediately BEFORE `CreatePendingAssignment` ... rollback restores the exact pre-constructor values (I20); on a creation failure it is discarded and no item is created" | ✓ matches |
| `STAGE_01Z_SEMANTIC_TEST_VECTORS.md` | TV221 (~L39) | before-image captured before creation; rollback restores pre-constructor state (Z2/I20) | ✓ matches |
| `STAGE_01_TRACEABILITY_MATRIX.csv` | R185 | capture `coverage_custody_before_image(spec.range)` BEFORE `CreatePendingAssignment`; on creation failure discard and create no item; I20 requires rollback to restore exact pre-constructor I8a/I8b; anti-pattern = "snapshot taken after the constructor mutated ... so rollback restores a post-mutation state"; status `SPECIFIED` | ✓ matches |

All six documents describe the same order (capture-then-create), the same discard-on-failure rule, the same restore
obligation (I20), and the same superseded anti-pattern (post-mutation snapshot). R185 lists exactly the four procedures
audited here (`PrepareParticipantsForNewRound; ContinueTemplateRefreshAssignmentSetup; CreatePendingAssignment;
AbortPendingWakeForRollback`) and traces to invariants `I20; I18b`. The I16 Stage-1Z clause Z2 (invariant-catalogue
~L367) and round-SM §3.10d Z2 both cite I20 as the formal home of the restore obligation, matching the catalogue's I20
entry. **Cross-document consistency — PASS.**

---

## 9. Result

**PASS** — Correction Z2 is faithfully specified: in both `PrepareParticipantsForNewRound` and
`ContinueTemplateRefreshAssignmentSetup` the ledger before-image is captured **before** `CreatePendingAssignment` (the
sole `custody_status`/`assignment_ledger` mutator), a creation failure discards the before-image and creates no
transaction item, invariant I20 formalises the exact pre-constructor restore (mirrored by the recovery-plan X1 capture),
`AbortPendingWakeForRollback` restores from the captured before-image, and TV221 plus the round-SM §3.10d Z2, invariant
I20/I16, terminology, and traceability R185 are mutually consistent; the A1 baseline `8.420833333 kWh` is unaffected.
