# Stage 1W — Structured Range Result Audit (W4)

## 1. Scope

This audit documents correction **W4 — "consume structured range results exactly"** — as it
now stands in the current `STAGE_01_PROTOCOL_PSEUDOCODE.md` (the file re-grepped for this
audit; all line references below are to that file as inspected and are load-bearing only as
anchors, the surrounding text being the authority). W4 governs the REDISTRIBUTION branch of
`CommitRecoveryAssignmentPlan` (§10a recovery-plan commit path): it must call the plan-bound
range constructor exactly once per redistribution spec, chosen by `spec.origin`, and *consume*
that constructor's structured result rather than re-driving the wake itself.

The correction is a control-flow and result-typing revision only. It creates, closes, or wakes
no assignment differently in the energy dimension; the A1 baseline `8.420833333 kWh` is
preserved unchanged, W4 touching only the commit path's branching over structured range results
and not any residency, transition-energy, or hash-work accounting term.

This document is descriptive. It READS the pseudocode, the round state machine, the terminology
glossary, and the traceability matrix; it WRITES only this file and modifies no other.

The requirement, quoted from the round state machine §3.10a addendum
(`STAGE_01_ROUND_STATE_MACHINE.md`, lines 652–656):

> **W4 (consume structured range results exactly).** `CommitRecoveryAssignmentPlan` calls the
> plan-bound range constructor once per REDISTRIBUTION spec, captures the returned `AssignmentID`
> \+ `WakeEventRef` on success (and NEVER seats a second wake), and branches on the declared
> failure results (`range_*_creation_failed` / `range_*_wake_failed`) — never on an undefined
> `creation_failed`. Exactly one `WakeCompleteEvent` per committed activation.

## 2. The defect W4 removes

The pattern W4 eliminates had two distinct faults, both in the recovery-plan commit path.

**(a) The double-wake loop.** The superseded commit logic appended a bare assignment identifier
to the created-set and then re-drove the wake in a separate loop — schematically
`ADD AssignmentID(a)` followed by `FOR EACH wake in spec.required_wake_operations: StartWake(target = a)`.
Because the range constructor (`RangeAssign*` / `RangeReassign*`) is itself a create-then-wake
transaction that already performs one `StartWake`, this second loop seated a *second*
`WakeCompleteEvent` for the same committed activation. The activation could then reach
`ACTIVE_HASHING` twice, or leave an orphan wake event pending on the event queue — a violation of
the "exactly one live head per lineage" discipline (I18b) and of the single-transaction wake
contract.

**(b) The undefined `creation_failed` test.** The superseded logic branched on a bare
`creation_failed(...)` disposition that no range constructor ever returns. The constructors
declare *origin-specific* failure results — `range_assign_creation_failed` /
`range_reassign_creation_failed` for a pre-mutation failure, and `range_assign_wake_failed` /
`range_reassign_wake_failed` for a post-creation wake failure. A test against an undefined
`creation_failed` token is unreachable: a real creation failure would fall through it, leaving the
commit path with no legal branch and no defined disposition.

W4 removes both faults: the commit path now calls the constructor once, consumes its structured
result, and branches only on the constructor's *declared* unions.

## 3. The declared range-result unions

The two ordinary entry points (`RangeAssign`, `RangeReassign`) and their plan-bound counterparts
(`RangeAssignFromPlan`, `RangeReassignFromPlan`) each return one of three declared results. The
`RETURNS` contracts, quoted verbatim from the current pseudocode:

| Constructor | Success | Pre-mutation failure | Post-creation wake failure |
|---|---|---|---|
| `RangeAssign` (1852–1853) | `range_assigned(AssignmentID, WakeEventRef, resulting_state = WAKING)` | `range_assign_creation_failed(reason)` | `range_assign_wake_failed(reason, AssignmentID)` |
| `RangeAssignFromPlan` (1894–1895) | `range_assigned(AssignmentID, WakeEventRef, resulting_state = WAKING)` | `range_assign_creation_failed(reason)` | `range_assign_wake_failed(reason, AssignmentID)` |
| `RangeReassign` (3851–3852) | `range_reassigned(provenance, AssignmentID, WakeEventRef)` | `range_reassign_creation_failed(reason)` | `range_reassign_wake_failed(reason, AssignmentID)` |
| `RangeReassignFromPlan` (3898–3899) | `range_reassigned(provenance, AssignmentID, WakeEventRef)` | `range_reassign_creation_failed(reason)` | `range_reassign_wake_failed(reason, AssignmentID)` |

The `RangeAssign` contract (lines 1852–1853):

```
  RETURNS: range_assigned(AssignmentID, WakeEventRef, resulting_state = WAKING) |
           range_assign_creation_failed(reason) | range_assign_wake_failed(reason, AssignmentID)
```

and `RangeReassign` (lines 3851–3852):

```
  RETURNS: range_reassigned(provenance, AssignmentID, WakeEventRef) |
           range_reassign_creation_failed(reason) | range_reassign_wake_failed(reason, AssignmentID)
```

Each plan-bound constructor produces its result through one, and only one, `StartWake`. In
`RangeAssignFromPlan` the creation is guarded first (lines 1869–1870):

```
    IF cr is assignment_creation_failed(reason):
      RETURN range_assign_creation_failed(reason = reason)              # W7: nothing created; no AssignmentID exists
```

then a single wake is seated and its structured outcome is returned (lines 1881–1893): on
`wake_seated` the constructor returns `range_assigned(... WakeEventRef = wref ...)`; on a wake
failure it "closes the un-activated head legally and restores the ledgers so no orphan PENDING
remains" (NOTE, lines 1896–1901) and returns `range_assign_wake_failed(reason = wr, AssignmentID =
AssignmentID(assignment))`. `RangeReassignFromPlan` is the structural analogue (lines 3866–3897),
returning `range_reassign_creation_failed`, `range_reassign_wake_failed`, or `range_reassigned`.
Each constructor's NOTE states it "performs EXACTLY ONE StartWake" (lines 1898, 3902). This is the
single wake the commit path consumes.

## 4. The corrected commit consumption

`CommitRecoveryAssignmentPlan` (`STAGE_01_PROTOCOL_PSEUDOCODE.md`, procedure at line 3529)
processes each spec of `plan.new_pending_assignment_specs`. The REDISTRIBUTION branch is the
`ELSE` arm at line 3566. Its intent is stated in the branch comment (lines 3567–3569):

```
        # W5: call the PLAN-BOUND range constructor with the spec's EXACT values (no SELECT), chosen by spec.origin.
        #   W4: it is a create-then-wake TRANSACTION that performs EXACTLY ONE wake and returns a STRUCTURED range
        #   result — the commit path CONSUMES that result and does NOT StartWake again (no double wake).
```

**Single constructor call, chosen by `spec.origin` (lines 3570–3579).** The branch dispatches on
`spec.origin` and issues exactly one call:

```
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

Only one of the two constructors runs, and it runs once; the result is captured in `rr`.

**Success capture — ADD `AssignmentID` + ADD `WakeEventRef`, CONTINUE, no second `StartWake`
(lines 3580–3585):**

```
        IF rr = range_reassigned(prov, aid, wref) OR rr = range_assigned(aid, wref, ws):
          # W5: the committed object equals the exact spec (the constructor asserts this internally too).
          ASSERT rr.AssignmentID resolves MinerID = spec.MinerID AND range = spec.range
                 AND assignment_origin = spec.origin AND source_assignment_ref = spec.source_assignment   # W5
          ADD rr.AssignmentID to created_assignments ; ADD rr.WakeEventRef to created_events   # W4: ACTUAL refs; ONE WakeCompleteEvent per activation
          CONTINUE
```

The success arm appends the constructor's *returned* `rr.AssignmentID` and *returned*
`rr.WakeEventRef`, then `CONTINUE`s to the next spec. There is no `StartWake` in this arm — the
wake already seated inside the constructor is the one whose reference is recorded.

**Creation-failure branch — the DECLARED pre-mutation results (lines 3586–3592):**

```
        IF rr = range_reassign_creation_failed(reason) OR rr = range_assign_creation_failed(reason):
          # W7: nothing was created for this spec (pre-mutation) — reversible if this is the first spec.
          IF created_assignments is empty AND created_events is empty:
            RETURN install_failed_before_mutation(reason)
          SET plan.rollback_metadata <- rollback_record(RecoveryInstallID = plan.RecoveryInstallID,
                created_assignments = created_assignments, created_events = created_events)
          RETURN install_failed_after_mutation(reason, plan.rollback_metadata)
```

Because nothing was created for this spec, the failure is reversible when it is the first spec
(`install_failed_before_mutation`); otherwise the already-created earlier specs are recorded in a
rollback record and `install_failed_after_mutation` is returned. The test is against the
*origin-specific* `range_reassign_creation_failed` / `range_assign_creation_failed` — never a bare
`creation_failed`.

**Wake-failure branch — the DECLARED post-creation results (lines 3593–3600):**

```
        # rr = range_reassign_wake_failed(reason, aid) OR range_assign_wake_failed(reason, aid): the plan-bound
        #   constructor ALREADY self-rolled-back THIS spec's head (closed, ledgers restored, miner not WAKING).
        #   Roll back the EARLIER specs of this install.
        IF created_assignments is empty AND created_events is empty:
          RETURN install_failed_before_mutation(reason = rr.reason)      # only this spec touched, and it self-rolled-back
        SET plan.rollback_metadata <- rollback_record(RecoveryInstallID = plan.RecoveryInstallID,
              created_assignments = created_assignments, created_events = created_events)
        RETURN install_failed_after_mutation(reason = rr.reason, plan.rollback_metadata)
```

Because the plan-bound constructor already self-rolled-back this spec's head (closed the
un-activated head, restored ledgers, left the miner off `WAKING`), the commit path need only roll
back the *earlier* specs of the install — the current spec having left no residue. Again the test
is against the declared `range_reassign_wake_failed` / `range_assign_wake_failed`.

The four declared branches (success, creation failure, wake failure, and the RESERVE_ACTIVATION
arm of the same loop) are total over the constructors' result unions; no undefined disposition can
fall through.

### Negative confirmation (by grep on the current file)

* **No double-wake loop.** Searching the whole file for
  `required_wake_operations | FOR EACH wake | StartWake(target=a)` returns no double-wake construct
  in the commit path. The only two hits are (i) line 1582, an unrelated in-loop transaction append
  `ADD AssignmentID(a) to participant_setup_txn.created_assignments` inside the participant-setup
  transaction (not a wake loop), and (ii) line 3517, a *planning-side* note that reads: "the commit
  path captures that one ref and NEVER seats a second wake for the same activation — there is no
  separate `required_wake_operations` loop." No `FOR EACH wake ...` loop and no `StartWake(target=a)`
  call exist.

* **No undefined `creation_failed` test.** Filtering all `creation_failed` occurrences to exclude
  the declared unions (`assignment_creation_failed`, `range_assign_creation_failed`,
  `range_reassign_creation_failed`, and the reserve-activation results) leaves a single unrelated hit
  — `participation_reentry_creation_failed` at line 2285, a separately declared union in the
  participation-reentry procedure. Within `CommitRecoveryAssignmentPlan` the only creation-failure
  test is the origin-specific pair at line 3586. No bare `= creation_failed(` test remains.

## 5. Exactly one WakeCompleteEvent per committed activation

The one-wake guarantee is a composition of two facts, each grounded in the current pseudocode.

**(i) Each plan-bound constructor seats exactly one wake.** `StartWake`
(`STAGE_01_PROTOCOL_PSEUDOCODE.md`, procedure at line 1097) is a transaction whose canonical order
seats one `WakeCompleteEvent` via a single `ScheduleEvent` call (lines 1125–1128) and only then
applies the `WAKING` transition; a transition failure after the seat cancels that one event (lines
1140–1146). On success it returns `wake_seated(AssignmentID, WakeEventRef, wake_target_time,
resulting_state = WAKING)` (lines 1150–1151). Each range constructor calls `StartWake` exactly once
(RangeAssignFromPlan line 1881; RangeReassignFromPlan line 3878) — the constructors' NOTEs state
"performs EXACTLY ONE StartWake" (lines 1898, 3902) — so a *successful* constructor call yields
exactly one live `WakeCompleteEvent`, and a *failed* one yields zero (self-rolled-back).

**(ii) The commit path adds no further wake.** The success arm of the REDISTRIBUTION branch
consumes `rr.WakeEventRef` and `CONTINUE`s (lines 3584–3585) without any `StartWake`. The
comment on that line is explicit: `# W4: ACTUAL refs; ONE WakeCompleteEvent per activation`.

Composing (i) and (ii): for every committed activation the number of `WakeCompleteEvent`s seated is
exactly one — the constructor's — and the commit path records precisely that event's reference in
`created_events`, so a later `RollbackRecoveryAssignmentPlan` (procedure at line 3611) can cancel
exactly the events the plan created. The double-wake defect of §2(a) is thereby closed: there is no
second seat to cancel and no orphan wake to survive. This directly upholds I18b (unique live head
per open lineage; `STAGE_01_INVARIANT_CATALOGUE.md` line 405 and I18b/G2 summary line 520) and I16
(floor breaches recorded, never silently repaired; catalogue §I16 at line 284) — the two invariants
R163 maps to.

## 6. Map to TV192 / TV193

The blocking test vectors for the W1–W8 closure are declared in the traceability matrix at row
**R168** (`STAGE_01_TRACEABILITY_MATRIX.csv`, line 169), which names the vector file
`STAGE_01W_SEMANTIC_TEST_VECTORS`. The two vectors that exercise W4 are, quoted from R168:

* **TV192** — "CommitRecoveryAssignmentPlan consumes a success range result without a second
  StartWake." This is discharged by the success arm of §4 (lines 3580–3585): on
  `range_assigned` / `range_reassigned` the commit path appends `rr.AssignmentID` and
  `rr.WakeEventRef` and `CONTINUE`s, issuing no `StartWake` — matched to the single-wake argument of
  §5.

* **TV193** — "a range_reassign_wake_failed follows the declared failure branch with coherent
  rollback metadata." This is discharged by the wake-failure branch of §4 (lines 3593–3600): a
  `range_reassign_wake_failed` (or `range_assign_wake_failed`) is a *declared* result; the spec's
  own head is already self-rolled-back by the constructor, and the earlier specs are captured in a
  `rollback_record` built from the actual returned references (`created_assignments`,
  `created_events`) for `RollbackRecoveryAssignmentPlan`.

**Absence noted.** As of this audit the named vector file `STAGE_01W_SEMANTIC_TEST_VECTORS.md` is
not present in the stage_01 directory (no `STAGE_01W_*` artefacts exist yet). TV192 and TV193 are
therefore *specified* in the traceability matrix (R168) but *not yet realised* as paper vectors.
The corrected pseudocode supports both vectors as written; authoring the vector file remains
outstanding.

## 7. Traceability

| Anchor | Location | Content (verified) |
|---|---|---|
| Round SM §3.10a **W4** | `STAGE_01_ROUND_STATE_MACHINE.md` lines 652–656 | The W4 requirement: one constructor call per REDISTRIBUTION spec, capture `AssignmentID` + `WakeEventRef` on success, never a second wake, branch on `range_*_creation_failed` / `range_*_wake_failed`, one `WakeCompleteEvent` per committed activation. |
| Terminology **W4** | `STAGE_01_TERMINOLOGY.md` lines 839–841 | "Structured range result (W4)." `RangeAssign*` / `RangeReassign*` return `range_assigned` / `range_assign_creation_failed` / `range_assign_wake_failed` (and the `range_reassign_*` analogues); `CommitRecoveryAssignmentPlan` consumes the success result's `AssignmentID` + `WakeEventRef` and never wakes twice. |
| **R163** | `STAGE_01_TRACEABILITY_MATRIX.csv` line 164 | "Consume structured range results exactly (W4)"; procedures `CommitRecoveryAssignmentPlan; RangeAssignFromPlan; RangeReassignFromPlan`; invariants I16; I18b; anti-pattern "a commit path that double-wakes a committed assignment or tests an undefined creation_failed result"; status SPECIFIED. |
| **R168 / TV192, TV193** | `STAGE_01_TRACEABILITY_MATRIX.csv` line 169 | Blocking vectors for W1–W8; TV192 (consume success without a second StartWake), TV193 (`range_reassign_wake_failed` follows the declared branch with coherent rollback metadata); vector file `STAGE_01W_SEMANTIC_TEST_VECTORS` (not yet present). |
| Invariants | `STAGE_01_INVARIANT_CATALOGUE.md` I16 (line 284), I18b (lines 405, 520) | I16 — floor breaches recorded, never silently repaired; I18b — every OPEN lineage has exactly one live head. |

The correction is consistent across the four artefacts: the pseudocode implements the single-call /
consume / declared-branch discipline; the round state machine and terminology state it in prose;
the traceability matrix records it as R163 (SPECIFIED) with its test vectors declared under R168.
The only open item is the physical `STAGE_01W_SEMANTIC_TEST_VECTORS.md` file backing TV192/TV193.
The A1 baseline `8.420833333 kWh` is unaffected by W4 and preserved.
