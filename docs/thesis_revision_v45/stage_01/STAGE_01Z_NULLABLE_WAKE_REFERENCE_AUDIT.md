# Stage 1Z — Nullable Wake Reference Audit (correction Z3)

This is a documentation-only audit of correction **Z3** ("make wake event references explicitly optional") in the Stage-1
formal specification of **PoCol** and the idle policy within PoCol. It verifies, against the frozen source of truth
`STAGE_01_PROTOCOL_PSEUDOCODE.md` (read-only), that a setup rollback item carries an explicitly nullable `WakeEventRef`
paired with a structured `wake_result`, that `StartWake`'s three structured results map deterministically to
actual-ref / returned-ref / null, that `AbortPendingWakeForRollback` cancels only a non-null still-pending ref, and that
no rollback performs an undefined `wake_by_miner` map lookup. No specification document is modified by this audit; all
quoted lines are the current lines of the source of truth. The A1 baseline (`8.420833333 kWh`) is unchanged.

- **Correction:** Z3 (explicitly-optional wake reference).
- **Source of truth (read-only):** `STAGE_01_PROTOCOL_PSEUDOCODE.md`.
- **Primary procedures:** `StartWake`, `PrepareParticipantsForNewRound`, `ContinueTemplateRefreshAssignmentSetup`,
  `AbortPendingWakeForRollback`.
- **Requirement:** R186. **Invariant context:** I16 (Stage-1Z clause), I18b. **Test vector:** TV222.

---

## Check 1 — The setup item carries `WakeEventRef | null` and `wake_result` (PASS)

The centralised `setup_rollback_item` type is declared in the §0.8 state-model block. The `WakeEventRef` field is
declared explicitly optional and is paired with a `wake_result` field:

> `STAGE_01_PROTOCOL_PSEUDOCODE.md:874`
> ```
> # setup_rollback_item = { MinerID, AssignmentID, assignment_version, pre_wake_state, before_image, WakeEventRef (| null),
> #   wake_result, rollback_envelope }. setup_transaction = { rollback_envelope, rollback_items : [setup_rollback_item] }
> ```

The same block states the construction discipline that makes the field total (a complete item, with the wake fields
defaulting to explicit null, exists BEFORE `StartWake` is invoked):

> `STAGE_01_PROTOCOL_PSEUDOCODE.md:877`
> ```
> #   created assignment has EXACTLY ONE complete rollback_item appended BEFORE StartWake is invoked (WakeEventRef / wake_result
> #   default to null and are set immediately after StartWake, Z3) — so no state exists in which an AssignmentID is present but
> #   its before-image or wake reference is absent.
> ```

Both seating loops materialise this record with the wake fields set to explicit `null` before `StartWake` runs:

- `PrepareParticipantsForNewRound` — `STAGE_01_PROTOCOL_PSEUDOCODE.md:1724`:
  ```
  SET item <- setup_rollback_item(MinerID = m, AssignmentID = AssignmentID(a), assignment_version = assignment_version(a),
        pre_wake_state = spec.from, before_image = before_image, WakeEventRef = null, wake_result = null,
        rollback_envelope = dispatch_envelope)   # Z2/Z3/Z6: complete except wake fields
  ```
- `ContinueTemplateRefreshAssignmentSetup` — `STAGE_01_PROTOCOL_PSEUDOCODE.md:4988`:
  ```
  SET item <- setup_rollback_item(MinerID = m, AssignmentID = AssignmentID(assignment_m),
        assignment_version = assignment_version(assignment_m), pre_wake_state = pre_wake_state,
        before_image = before_image, WakeEventRef = null, wake_result = null, rollback_envelope = dispatch_envelope)   # Z2/Z3/Z6
  ```

**Result:** the setup item carries `WakeEventRef (| null)` plus `wake_result`, and every created assignment has a complete
item with those fields present (explicit null) before any wake is attempted. PASS.

---

## Check 2 — `StartWake`'s three results map to actual-ref / returned-ref / null (PASS)

### 2a. `StartWake` declares exactly three V3 structured returns

`StartWake` (`PROCEDURE StartWake`, `STAGE_01_PROTOCOL_PSEUDOCODE.md:1220`) is a transaction with explicit structured
outputs. Its `RETURNS` signature enumerates the three results, matching the names used by the seating classification:

> `STAGE_01_PROTOCOL_PSEUDOCODE.md:1273`
> ```
> RETURN wake_seated(AssignmentID = AssignmentID(target_assignment), WakeEventRef = wake_event_ref,
>                    wake_target_time = target_time, resulting_state = WAKING)
> RETURNS: wake_seated(AssignmentID, WakeEventRef, wake_target_time, resulting_state = WAKING) |
>          wake_schedule_failed_before_transition(reason) | wake_transition_failed_after_seat(reason, WakeEventRef)
> ```

The two failure results are returned at their canonical sites:

- `wake_schedule_failed_before_transition(reason = seat)` — schedule rejected before any transition; the miner is
  unchanged and nothing is seated (`STAGE_01_PROTOCOL_PSEUDOCODE.md:1255`).
- `wake_transition_failed_after_seat(reason = tr, WakeEventRef = wake_event_ref)` — the WAKING transition failed after
  the seat, so the seated event is CANCELLED and the (already-cancelled) ref is returned
  (`STAGE_01_PROTOCOL_PSEUDOCODE.md:1269`).

The three names — `wake_seated` / `wake_schedule_failed_before_transition` / `wake_transition_failed_after_seat` — are
therefore the actual return names, so the seating classification below is exhaustive over the transaction's disposition.

### 2b. The seating classification (quoted) maps each result to the stored ref

`PrepareParticipantsForNewRound` records the structured result, then assigns `item.WakeEventRef` per branch:

> `STAGE_01_PROTOCOL_PSEUDOCODE.md:1730`
> ```
> SET item.wake_result <- wr                                                          # Z3: record the structured wake result
> IF wr = wake_seated(waid, wref, wtt, ws):        SET item.WakeEventRef <- wref       # Z3: actual ref
> ELSE IF wr = wake_transition_failed_after_seat(reason, wref): SET item.WakeEventRef <- wref   # Z3: returned (already-cancelled) ref
> ELSE:                                            SET item.WakeEventRef <- null       # Z3: wake_schedule_failed_before_transition -> null
> ```

`ContinueTemplateRefreshAssignmentSetup` performs the identical classification:

> `STAGE_01_PROTOCOL_PSEUDOCODE.md:4996`
> ```
> SET item.wake_result <- wr                                                    # Z3: record the structured wake result
> IF wr = wake_seated(waid, wref, wtt, ws):        SET item.WakeEventRef <- wref   # Z3: actual ref
> ELSE IF wr = wake_transition_failed_after_seat(reason, wref): SET item.WakeEventRef <- wref   # Z3: returned (already-cancelled) ref
> ELSE:                                            SET item.WakeEventRef <- null   # Z3: wake_schedule_failed_before_transition -> null
> ```

| `StartWake` result | `item.wake_result` | `item.WakeEventRef` |
|---|---|---|
| `wake_seated(...)` | the structured `wake_seated` | the **actual** ref (`wref`) |
| `wake_transition_failed_after_seat(reason, wref)` | the structured failure | the **returned** already-cancelled ref (`wref`) |
| `wake_schedule_failed_before_transition(reason)` (ELSE) | the structured failure | **null** |

Both loops set `wake_result` unconditionally (line 1730 / 4996) and then classify the ref by the exact three-way
disposition. The ELSE branch is reached only by `wake_schedule_failed_before_transition`, the sole result carrying no
seated ref, and it stores `null`.

**Result:** the three `StartWake` results map to actual-ref / returned-ref / null respectively, identically in both
seating loops. PASS.

---

## Check 3 — `AbortPendingWakeForRollback` cancels only a non-null pending ref (PASS)

`AbortPendingWakeForRollback` (`PROCEDURE AbortPendingWakeForRollback`, `STAGE_01_PROTOCOL_PSEUDOCODE.md:1791`) declares
its `WakeEventRef` input as nullable:

> `STAGE_01_PROTOCOL_PSEUDOCODE.md:1794`
> ```
> # Z3: WakeEventRef is WakeEventRef | null (a pre-transition wake-schedule failure carries null).
> ```

Its cancellation step guards on both non-null and still-pending, so a null ref (and a non-pending ref) cancels nothing
and performs no lookup:

> `STAGE_01_PROTOCOL_PSEUDOCODE.md:1803`
> ```
> # (1) Y4/Z3: cancel the exact WakeCompleteEvent FIRST so no wake can activate anything mid-rollback. WakeEventRef may be
> #   null (a pre-transition wake-schedule failure) — cancel ONLY when it is non-null AND still pending (no undefined lookup).
> IF WakeEventRef != null AND WakeEventRef is still pending on EQ: CANCEL WakeEventRef on EQ
> ```

The procedure's closing NOTE restates the contract (`STAGE_01_PROTOCOL_PSEUDOCODE.md:1839`): "It accepts a nullable
WakeEventRef and cancels it only when non-null and pending (Z3)."

**Result:** the cancellation fires only when `WakeEventRef != null AND WakeEventRef is still pending on EQ`; the INPUTS
note declares the parameter `WakeEventRef | null`. PASS.

---

## Check 4 — No rollback performs an undefined `wake_by_miner` lookup (PASS)

Read-only grep for any live indexing of the withdrawn parallel map:

```
$ grep -nE "\.(wake_by_miner)\[" STAGE_01_PROTOCOL_PSEUDOCODE.md
$ echo $?
1        # no matches; grep exit status 1
```

Match count = **0**. The only textual occurrences of `wake_by_miner` are the two prose notes that name it as a
*withdrawn* Y-era map — the §0.8 declaration comment (`STAGE_01_PROTOCOL_PSEUDOCODE.md:876`, "REPLACES the Y-era
parallel maps (assignment_by_miner / wake_by_miner / …)") and the `RollbackParticipantSetup` INPUTS note
(`STAGE_01_PROTOCOL_PSEUDOCODE.md:1850`, "no parallel maps"). Neither is a live subscript; there is no `.wake_by_miner[…]`
indexing anywhere in the pseudocode.

The rollback instead reads `item.WakeEventRef` from the centralised record. Because a missing item is impossible — every
created assignment appends a complete `setup_rollback_item` (with the wake fields defaulting to explicit `null`) BEFORE
`StartWake` is invoked (Z6; `STAGE_01_PROTOCOL_PSEUDOCODE.md:877` and the build sites at lines 1724 / 4988) — there is no
state in which an `AssignmentID` is present but its wake reference is absent, and no code path evaluates an absent map
entry for a miner whose wake was never seated (the exact defect R186 records).

**Result:** grep = 0 (no live `wake_by_miner` indexing); the rollback reads the always-present `item.WakeEventRef` from
the centralised record. PASS.

---

## Test-vector linkage — TV222

`STAGE_01Z_SEMANTIC_TEST_VECTORS.md` exercises Z3 with **TV222** ("A pre-transition wake-schedule failure yields
WakeEventRef = null and a clean rollback (Z3)"). Its procedures are `StartWake`, `PrepareParticipantsForNewRound` /
`ContinueTemplateRefreshAssignmentSetup`, and `AbortPendingWakeForRollback`; its expected outcome is that the item
records `WakeEventRef = null` and `wake_result = wake_schedule_failed_before_transition`, and that on rollback
`AbortPendingWakeForRollback` "sees `WakeEventRef = null` and cancels nothing (no undefined map lookup)", the miner was
never `WAKING` so no T12 departs, and the assignment is closed and the before-image restored. This traces directly to the
ELSE branch verified in Check 2 (null on `wake_schedule_failed_before_transition`) and the guarded cancellation verified
in Check 3. The companion vector **TV226** (Z6) asserts that each created assignment carries exactly one complete
`setup_rollback_item` with an explicit (possibly null) `WakeEventRef`, corroborating Check 1 and Check 4.

---

## Cross-document consistency

| Document | Statement | Consistent with pseudocode? |
|---|---|---|
| `STAGE_01_PROTOCOL_PSEUDOCODE.md` (source of truth) | `setup_rollback_item` has `WakeEventRef (| null)` + `wake_result`; three `StartWake` results → actual / returned / null; `AbortPendingWakeForRollback` cancels only a non-null pending ref; no `wake_by_miner` indexing (grep = 0). | — (baseline) |
| `STAGE_01_ROUND_STATE_MACHINE.md` §3.10d, clause **Z3** (`:785`) | "A setup item carries `WakeEventRef : WakeEventRef | null` and `wake_result`. `wake_seated` stores the actual ref; `wake_schedule_failed_before_transition` stores null; `wake_transition_failed_after_seat` stores the returned (already-cancelled) ref. `AbortPendingWakeForRollback` cancels only a non-null, still-pending ref; no rollback performs an undefined map lookup." | Yes — matches Checks 1–4 exactly. |
| `STAGE_01_INVARIANT_CATALOGUE.md` I16 Stage-1Z clause, **Z3** (`:368`) | "a setup item's `WakeEventRef` is explicitly nullable with a `wake_result`; a rollback cancels only a non-null pending ref (no undefined lookup)." | Yes — matches Checks 1 and 3. |
| `STAGE_01_TERMINOLOGY.md` "Nullable `WakeEventRef` + `wake_result` (Z3)" (`:953`) | null on `wake_schedule_failed_before_transition`, returned already-cancelled ref on `wake_transition_failed_after_seat`, actual ref on `wake_seated`; "`AbortPendingWakeForRollback` cancels it ONLY when non-null and still pending — no undefined map lookup." | Yes — matches Check 2's three-way mapping and Check 3. |
| `STAGE_01Z_SEMANTIC_TEST_VECTORS.md` TV222 (`:48`) | pre-transition schedule failure → `WakeEventRef = null` + `wake_result = wake_schedule_failed_before_transition`; rollback cancels nothing, no undefined lookup. | Yes — traces to the ELSE branch and the guarded cancel. |
| `STAGE_01_TRACEABILITY_MATRIX.csv` **R186** (`:187`) | "Make wake event references explicitly optional (Z3) … StartWake wake_seated stores the actual ref, wake_schedule_failed_before_transition stores null, wake_transition_failed_after_seat stores the returned already-cancelled ref; AbortPendingWakeForRollback … cancels it only when non-null and still pending; no rollback evaluates an absent map entry" — defect: "a rollback that performs an undefined wake_by_miner lookup for a miner whose wake was never seated." | Yes — the four verified checks are exactly the R186 requirement; the named defect is eliminated (grep = 0, complete item before StartWake). |

All five cross-references (round state machine §3.10d Z3, invariant I16 Stage-1Z clause, terminology, TV222, and R186)
agree with the pseudocode source of truth. No divergence found.

---

## Deliverable tree (Stage 1Z)

This audit (`STAGE_01Z_NULLABLE_WAKE_REFERENCE_AUDIT.md`) is deliverable 4 of the Stage-1Z set. The final Stage-1Z
deliverable tree is:

1. `STAGE_01Z_CORRECTION_REPORT.md`
2. `STAGE_01Z_SETUP_RETRY_LIFECYCLE_AUDIT.md` (Z1)
3. `STAGE_01Z_PREMUTATION_SNAPSHOT_AUDIT.md` (Z2)
4. `STAGE_01Z_NULLABLE_WAKE_REFERENCE_AUDIT.md` (Z3) — this file
5. `STAGE_01Z_T12_ASSIGNMENT_EFFECT_AUDIT.md` (Z4)
6. `STAGE_01Z_WAKING_ORIGIN_BINDING_AUDIT.md` (Z5)
7. `STAGE_01Z_PROCEDURE_SIGNATURE_CALL_AUDIT.md`
8. `STAGE_01Z_PROCEDURE_CALL_GRAPH.md`
9. `STAGE_01Z_SEMANTIC_TEST_VECTORS.md` (TV219–TV226)
10. `STAGE_01Z_SUPERSESSION_REGISTER.md`
11. `STAGE_01Z_CROSS_DOCUMENT_AUDIT.md`
12. `STAGE_01Z_CHECKSUM_MANIFEST.sha256`

The six modified normative documents are `STAGE_01_PROTOCOL_PSEUDOCODE.md`, `STAGE_01_MINER_STATE_MACHINE.md`,
`STAGE_01_ROUND_STATE_MACHINE.md`, `STAGE_01_INVARIANT_CATALOGUE.md`, `STAGE_01_TERMINOLOGY.md`, and
`STAGE_01_TRACEABILITY_MATRIX.csv`. The Stage-1A–1Y lettered artifacts are unchanged.

---

## Result

**PASS** — Z3 is faithfully specified: the setup item carries `WakeEventRef | null` + `wake_result`; `StartWake`'s three
results map to actual-ref / returned-ref / null; `AbortPendingWakeForRollback` cancels only a non-null still-pending ref;
no rollback performs an undefined `wake_by_miner` lookup (grep = 0), because every created assignment has a complete item
with an explicit (possibly null) `WakeEventRef` before `StartWake`; and the pseudocode, round state machine §3.10d,
invariant I16, terminology, TV222, and R186 are mutually consistent.
