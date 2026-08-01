# Stage 1AA — Rollback-Item Storage Audit (correction AA6)

This is a documentation-only audit of correction **AA6** ("make rollback-item updates explicit and keyed") in the Stage-1
formal specification of **PoCol** and the idle policy — the *mechanism* under study — within PoCol. It verifies, against
the final committed source of truth `STAGE_01_PROTOCOL_PSEUDOCODE.md` (read-only), that `setup_rollback_item` gains a
`RollbackItemID`, that `setup_transaction.rollback_items` is a keyed map `RollbackItemID -> setup_rollback_item`
(replacing the Z-era list), that both seating loops create the item `NOT_ATTEMPTED` / `null` under a deterministic
`RollbackItemID` BEFORE `StartWake` and update the STORED record explicitly by key afterward, and that both rollback
owners iterate the keyed map deterministically and consume the persisted post-`StartWake` record — never a local-variable
alias. No specification document is modified by this audit; all quoted lines are the current lines of the source of truth.
The A1 baseline (`8.420833333 kWh`) is unchanged.

- **Correction:** AA6 (explicit keyed rollback-item storage).
- **Source of truth (read-only):** `STAGE_01_PROTOCOL_PSEUDOCODE.md`.
- **Primary procedures:** `PrepareParticipantsForNewRound`, `ContinueTemplateRefreshAssignmentSetup`,
  `RollbackParticipantSetup`, `RollbackTemplateRefreshSetup` (and `StartWake` as the wake-result source).
- **Requirement:** R196. **Invariant context:** I16, I18b, I20. **Test vector:** TV235.

---

## Check 1 — `setup_rollback_item` gains `RollbackItemID`; `setup_transaction.rollback_items` is a keyed map (PASS)

The centralised type declaration in the §0.8 state-model block (Z6, amended by AA6) adds `RollbackItemID` to the item and
makes `setup_transaction.rollback_items` a KEYED map:

> `STAGE_01_PROTOCOL_PSEUDOCODE.md:875`
> ```
> # setup_rollback_item = { RollbackItemID, MinerID, AssignmentID, assignment_version, pre_wake_state, before_image,
> #   WakeEventRef (| null), wake_result, rollback_envelope } (RollbackItemID added, AA6). setup_transaction =
> #   { rollback_envelope, rollback_items : map RollbackItemID -> setup_rollback_item } (KEYED, AA6)
> ```

The AA6 addendum in the same block states the create-before / update-after-by-key discipline and enumerates the
`wake_result` domain:

> `STAGE_01_PROTOCOL_PSEUDOCODE.md:908`
> ```
> # --- AA6 explicit keyed rollback-item storage ---
> # setup_rollback_item gains RollbackItemID; setup_transaction.rollback_items is KEYED by RollbackItemID. The item is CREATED
> #   with WakeEventRef = null and wake_result = NOT_ATTEMPTED and ADDED under RollbackItemID BEFORE StartWake; after StartWake
> #   the stored record is UPDATED EXPLICITLY by key — setup_txn.rollback_items[RollbackItemID].wake_result <- wr and
> #   .WakeEventRef <- (actual ref | returned cancelled ref | null). Rollback CONSUMES the stored keyed record, never an
> #   unproven alias to a local variable. wake_result in { NOT_ATTEMPTED, wake_seated, wake_schedule_failed_before_transition,
> #   wake_transition_failed_after_seat }.
> ```

Both transaction initialisers create `rollback_items` as an empty **map** (not a list) keyed by `RollbackItemID`:

- `PrepareParticipantsForNewRound` — `STAGE_01_PROTOCOL_PSEUDOCODE.md:1720`:
  ```
  SET participant_setup_txn <- setup_transaction(rollback_envelope = dispatch_envelope, rollback_items = empty map)   # W1/V8/X2/Y4/Z6/AA6: one centralised map keyed by RollbackItemID
  ```
- `ContinueTemplateRefreshAssignmentSetup` — `STAGE_01_PROTOCOL_PSEUDOCODE.md:5077`:
  ```
  SET refresh_setup_txn <- setup_transaction(rollback_envelope = dispatch_envelope, rollback_items = empty map)   # W1/W3/X2/Y4/Z6/AA6: centralised map keyed by RollbackItemID
  ```

**Result:** the item type carries `RollbackItemID`, and `setup_transaction.rollback_items` is declared and initialised as a
keyed map `RollbackItemID -> setup_rollback_item`, replacing the Z-era list. PASS.

---

## Check 2 — Participant setup creates the item `NOT_ATTEMPTED` / `null` under a deterministic key before `StartWake`, then updates by key (PASS)

In `PrepareParticipantsForNewRound`, an explicit deterministic `RollbackItemID` is minted, the complete item is
constructed with `WakeEventRef = null` and `wake_result = NOT_ATTEMPTED`, and it is ADDED under its key BEFORE `StartWake`
is invoked:

> `STAGE_01_PROTOCOL_PSEUDOCODE.md:1775`
> ```
> SET rbid <- (PARTICIPANT_SETUP, m, assignment_version_ref(AssignmentID(a), assignment_version(a)))   # AA6: explicit, deterministic RollbackItemID
> SET item <- setup_rollback_item(RollbackItemID = rbid, MinerID = m, AssignmentID = AssignmentID(a),
>       assignment_version = assignment_version(a), pre_wake_state = spec.from, before_image = before_image,
>       WakeEventRef = null, wake_result = NOT_ATTEMPTED, rollback_envelope = dispatch_envelope)   # Z2/Z3/AA6: created wake-unattempted
> SET participant_setup_txn.rollback_items[rbid] <- item                              # AA6: ADD the keyed record BEFORE StartWake
> ```

After `StartWake`, the STORED record is UPDATED EXPLICITLY BY KEY — `wake_result` unconditionally, then `WakeEventRef` by
the three-way `StartWake` disposition (actual ref / returned already-cancelled ref / null) — with no local-variable alias:

> `STAGE_01_PROTOCOL_PSEUDOCODE.md:1780`
> ```
> SET wr <- CALL StartWake(RoundContext, m, target_assignment = a, from_state = spec.from,
>                scheduling_context = ORDINARY_DISPATCH(dispatch_envelope))   # V2/V3: explicit context; structured result
> UPDATE participant_setup_txn.rollback_items[rbid].wake_result <- wr                 # AA6/Z3: update the STORED record BY KEY
> IF wr = wake_seated(waid, wref, wtt, ws):        UPDATE participant_setup_txn.rollback_items[rbid].WakeEventRef <- wref       # AA6/Z3: actual ref
> ELSE IF wr = wake_transition_failed_after_seat(reason, wref): UPDATE participant_setup_txn.rollback_items[rbid].WakeEventRef <- wref   # AA6/Z3: returned (already-cancelled) ref
> ELSE:                                            UPDATE participant_setup_txn.rollback_items[rbid].WakeEventRef <- null       # AA6/Z3: wake_schedule_failed_before_transition -> null
> ```

| `StartWake` result | stored `.wake_result` (by key) | stored `.WakeEventRef` (by key) |
|---|---|---|
| (before `StartWake`) | `NOT_ATTEMPTED` | `null` |
| `wake_seated(...)` | the structured `wake_seated` | the **actual** ref (`wref`) |
| `wake_transition_failed_after_seat(reason, wref)` | the structured failure | the **returned** already-cancelled ref (`wref`) |
| `wake_schedule_failed_before_transition(reason)` (ELSE) | the structured failure | **null** |

Every write targets `participant_setup_txn.rollback_items[rbid]` — the stored record — so no unproven alias is created.
**Result:** PASS.

---

## Check 3 — Template-refresh setup does the identical keyed create-before / update-after (PASS)

`ContinueTemplateRefreshAssignmentSetup` performs the same discipline with its own deterministic key (scoped
`TEMPLATE_REFRESH_SETUP`):

> `STAGE_01_PROTOCOL_PSEUDOCODE.md:5094`
> ```
> SET rbid <- (TEMPLATE_REFRESH_SETUP, m, assignment_version_ref(AssignmentID(assignment_m), assignment_version(assignment_m)))   # AA6: explicit, deterministic RollbackItemID
> SET item <- setup_rollback_item(RollbackItemID = rbid, MinerID = m, AssignmentID = AssignmentID(assignment_m),
>       assignment_version = assignment_version(assignment_m), pre_wake_state = pre_wake_state,
>       before_image = before_image, WakeEventRef = null, wake_result = NOT_ATTEMPTED, rollback_envelope = dispatch_envelope)   # Z2/Z3/AA6
> SET refresh_setup_txn.rollback_items[rbid] <- item                            # AA6: ADD the keyed record BEFORE StartWake
> ```

And the post-`StartWake` explicit keyed update:

> `STAGE_01_PROTOCOL_PSEUDOCODE.md:5103`
> ```
> UPDATE refresh_setup_txn.rollback_items[rbid].wake_result <- wr               # AA6/Z3: update the STORED record BY KEY
> IF wr = wake_seated(waid, wref, wtt, ws):        UPDATE refresh_setup_txn.rollback_items[rbid].WakeEventRef <- wref   # AA6/Z3: actual ref
> ELSE IF wr = wake_transition_failed_after_seat(reason, wref): UPDATE refresh_setup_txn.rollback_items[rbid].WakeEventRef <- wref   # AA6/Z3: returned (already-cancelled) ref
> ELSE:                                            UPDATE refresh_setup_txn.rollback_items[rbid].WakeEventRef <- null   # AA6/Z3: wake_schedule_failed_before_transition -> null
> ```

**Result:** the template-refresh loop is byte-for-byte structurally identical to the participant loop — created
`NOT_ATTEMPTED` / `null` under a deterministic `RollbackItemID` before `StartWake`, then updated by key with the same
three-way ref mapping. PASS.

---

## Check 4 — Both rollback owners iterate the keyed map deterministically and consume the stored record (PASS)

`RollbackParticipantSetup` declares its input as the keyed-map transaction and iterates it in a deterministic
sorted-key order, reading each stored record (never an alias):

> `STAGE_01_PROTOCOL_PSEUDOCODE.md:1901`
> ```
> INPUTS: RoundContext, setup_txn   # AA6: { rollback_envelope, rollback_items : map RollbackItemID -> setup_rollback_item } — ONE
>                                   #   complete keyed record per created assignment (RollbackItemID, MinerID, AssignmentID,
>                                   #   assignment_version, pre_wake_state, before_image, WakeEventRef (| null), wake_result,
>                                   #   rollback_envelope); no parallel maps. Each item's wake_result is the persisted post-StartWake value.
> ```

> `STAGE_01_PROTOCOL_PSEUDOCODE.md:1916`
> ```
> FOR EACH RollbackItemID rbid IN SORT(KEYS(setup_txn.rollback_items) ascending):   # AA6: deterministic keyed-map iteration
>   SET item <- setup_txn.rollback_items[rbid]   # AA6: consume the STORED record (never a local-variable alias)
>   SET wr <- CALL AbortPendingWakeForRollback(RoundContext, MinerID = item.MinerID, AssignmentID = item.AssignmentID,
>                  assignment_version = item.assignment_version, WakeEventRef = item.WakeEventRef,
>                  rollback_envelope = setup_txn.rollback_envelope, closure_detail = participant_setup_rolled_back,
>                  coverage_custody_before_image = item.before_image)   # Y4/Y5/Z3/AA6
> ```

`RollbackTemplateRefreshSetup` declares the same keyed shape and iterates identically:

> `STAGE_01_PROTOCOL_PSEUDOCODE.md:1940`
> ```
> INPUTS: RoundContext, setup_txn   # AA6: { rollback_envelope, rollback_items : map RollbackItemID -> setup_rollback_item }
>                                   #   (same keyed shape as RollbackParticipantSetup's setup_txn)
> ```

> `STAGE_01_PROTOCOL_PSEUDOCODE.md:1948`
> ```
> FOR EACH RollbackItemID rbid IN SORT(KEYS(setup_txn.rollback_items) ascending):   # AA6: deterministic keyed-map iteration
>   SET item <- setup_txn.rollback_items[rbid]   # AA6: consume the STORED record (never a local-variable alias)
>   SET wr <- CALL AbortPendingWakeForRollback(RoundContext, MinerID = item.MinerID, AssignmentID = item.AssignmentID,
>                  assignment_version = item.assignment_version, WakeEventRef = item.WakeEventRef,
>                  rollback_envelope = setup_txn.rollback_envelope, closure_detail = template_refresh_setup_rolled_back,
>                  coverage_custody_before_image = item.before_image)   # Y4/Y5/Z3/AA6
> ```

Both owners feed `item.WakeEventRef`, `item.assignment_version`, and `item.before_image` — the persisted post-`StartWake`
fields read from `setup_txn.rollback_items[rbid]` — into `AbortPendingWakeForRollback`. The iteration order is
`SORT(KEYS(...) ascending)`, so rollback is deterministic over the keyed map.

**Result:** both rollback owners iterate the keyed map deterministically and consume the stored keyed record; neither
reads a local-variable alias. PASS.

---

## Check 5 — No residual non-keyed (list / alias) pattern remains (PASS)

Read-only grep for the withdrawn Z-era non-keyed patterns — appending an item to a `rollback_items` list, or mutating a
local `item.` alias:

```
$ grep -nE "ADD item to .*rollback_items|ADD .* to .*rollback_items|SET item\.wake_result|SET item\.WakeEventRef" STAGE_01_PROTOCOL_PSEUDOCODE.md
$ echo $?
1        # no matches; grep exit status 1
```

Match count = **0**. Every write to a rollback item is instead of the keyed forms
`SET <txn>.rollback_items[rbid] <- item` (create-before) and `UPDATE <txn>.rollback_items[rbid].<field> <- …`
(update-after), confirmed at lines 1779 / 1782–1785 (participant) and 5098 / 5103–5106 (template refresh). There is no
`SET item.` statement anywhere in the pseudocode, and no `ADD … to … rollback_items` list append.

Note that the surviving `ADD item to rolled_back_items` at `STAGE_01_PROTOCOL_PSEUDOCODE.md:4022` is a match against a
different symbol — `rolled_back_items`, the recovery-rollback *result accumulator* — and is **not** an append to any
`rollback_items` transaction map; it belongs to the out-of-scope recovery path (Check 6).

**Result:** no residual non-keyed list-append or alias-mutation pattern remains for setup rollback items (grep = 0). PASS.

---

## Check 6 — The recovery-install rollback (`RollbackRecoveryAssignmentPlan`) is out of AA6 scope and unchanged (PASS)

`RollbackRecoveryAssignmentPlan` operates on a **different** record — the recovery-install `rollback_record`, whose
`items` field is an explicit **list** `[rollback_item]` returned by `CommitRecoveryAssignmentPlan` (X1/X5), NOT the
setup-transaction keyed map. The type is declared in §0.8:

> `STAGE_01_PROTOCOL_PSEUDOCODE.md:776`
> ```
> # --- X1/X5 recovery-plan rollback record (a COMPLETE state transaction; returned EXPLICITLY, never pass-by-reference) ---
> # rollback_record = { RecoveryInstallID, items : [rollback_item] }.  CommitRecoveryAssignmentPlan builds it and returns
> #   it EXPLICITLY in EVERY disposition — install_committed(rollback_record) (X5) as well as
> #   install_failed_after_mutation(reason, rollback_record). …
> ```

Its `rollback_item` is a distinct type (`{ MinerID, AssignmentID, assignment_version, WakeEventRef, pre_wake_state,
rollback_envelope, coverage_custody_before_image, kind, provenance }`, `:781`) — carrying `kind` / `provenance` and a
per-item `rollback_envelope`, which the setup item does not. The procedure iterates `rollback_record.items` in stable
list order, not a sorted keyed map:

> `STAGE_01_PROTOCOL_PSEUDOCODE.md:4000`
> ```
> INPUTS: RoundContext, rollback_record   # X1: { RecoveryInstallID, items : [rollback_item] } (returned explicitly by CommitRecoveryAssignmentPlan, X5)
> ```

> `STAGE_01_PROTOCOL_PSEUDOCODE.md:4007`
> ```
> FOR EACH item in rollback_record.items (stable order):
>   IF item.WakeEventRef is still pending on EQ: CANCEL item.WakeEventRef on EQ
> …
> FOR EACH item in rollback_record.items (stable order):
> ```

Because this path consumes `rollback_record.items` and never the setup transaction's `rollback_items`, AA6 does not touch
it: it retains its X1 list form and its `(stable order)` iteration. AA6's keyed-map change applies **only** to
participant setup and template-refresh setup (Checks 2–4). This audit explicitly places the recovery-install rollback
**outside AA6 scope and unchanged**.

**Result:** `RollbackRecoveryAssignmentPlan` is confirmed out of AA6 scope and unmodified. PASS.

---

## PASS / verification table

| # | Claim | Evidence (`STAGE_01_PROTOCOL_PSEUDOCODE.md`) | Result |
|---|---|---|---|
| 1 | `setup_rollback_item` gains `RollbackItemID`; `setup_transaction.rollback_items` is a keyed map `RollbackItemID -> setup_rollback_item` | `:875` (type), `:908` (AA6 addendum), inits `:1720` / `:5077` (`empty map`) | PASS |
| 2 | Participant loop creates item `NOT_ATTEMPTED` / `null` under a deterministic `RollbackItemID` before `StartWake`, updates by key after | `:1775`–`:1779` (create/add before), `:1780`–`:1785` (update by key after) | PASS |
| 3 | Template-refresh loop does the identical keyed create-before / update-after | `:5094`–`:5098` (create/add before), `:5101`–`:5106` (update by key after) | PASS |
| 4 | Both rollback owners iterate the keyed map deterministically (`SORT(KEYS(...) ascending)`) and consume the stored record | `:1901` / `:1916`–`:1921` (participant), `:1940` / `:1948`–`:1953` (template refresh) | PASS |
| 5 | No residual non-keyed pattern (`ADD item to … rollback_items`, `SET item.wake_result`, `SET item.WakeEventRef`) | grep = 0 matches | PASS |
| 6 | `RollbackRecoveryAssignmentPlan` (uses `rollback_record.items`, a list) is out of AA6 scope and unchanged | `:776`–`:782` (X1 list type), `:4000`, `:4007`, `:4015` (`rollback_record.items`, stable order) | PASS |

---

## Test-vector linkage — TV235

`STAGE_01AA_SEMANTIC_TEST_VECTORS.md` exercises AA6 with **TV235** ("A keyed rollback item is created NOT_ATTEMPTED and
updated by key; rollback consumes the stored record (AA6)"). Its procedures are `PrepareParticipantsForNewRound` /
`ContinueTemplateRefreshAssignmentSetup`, `StartWake`, and `RollbackParticipantSetup` / `RollbackTemplateRefreshSetup`.
The vector sets up a setup that builds a `setup_rollback_item` with an explicit `RollbackItemID`, `WakeEventRef = null`,
and `wake_result = NOT_ATTEMPTED`, adds it under its key BEFORE `StartWake`, and — after one of the three `StartWake`
results — updates the STORED record explicitly by key (`rollback_items[RollbackItemID].wake_result <- wr` and
`.WakeEventRef <- actual | returned | null`), never a local-variable alias. On rollback, the owners iterate
`rollback_items` deterministically by `RollbackItemID` and consume the stored record's persisted post-`StartWake`
`wake_result` / `WakeEventRef`. This traces directly to Check 2 / Check 3 (keyed create-before, keyed update-after) and
Check 4 (deterministic keyed iteration of the stored record). The vector preserves the A1 baseline `8.420833333 kWh`.

---

## Cross-document consistency

| Document | Statement | Consistent with pseudocode? |
|---|---|---|
| `STAGE_01_PROTOCOL_PSEUDOCODE.md` (source of truth) | `setup_rollback_item` gains `RollbackItemID`; `rollback_items` is a keyed map; both loops create `NOT_ATTEMPTED` / `null` under a deterministic key before `StartWake` and update by key; both rollback owners iterate `SORT(KEYS(...))` and consume the stored record; recovery-install rollback uses `rollback_record.items` (list) and is untouched (grep = 0 residual). | — (baseline) |
| `STAGE_01_ROUND_STATE_MACHINE.md` §3.10e, clause **AA6** (`:845`) | "`setup_rollback_item` gains a `RollbackItemID` and `setup_transaction.rollback_items` is KEYED by it. The item is CREATED with `WakeEventRef = null` and `wake_result = NOT_ATTEMPTED` … BEFORE `StartWake`; after `StartWake` the STORED record is UPDATED EXPLICITLY by key … Rollback CONSUMES the stored keyed record (iterating deterministically by `RollbackItemID`), never an unproven alias. Applies to participant setup and template-refresh setup." | Yes — matches Checks 1–4 exactly. |
| `STAGE_01_INVARIANT_CATALOGUE.md` **AA6** clause (`:387`) | "`setup_transaction.rollback_items` is keyed by `RollbackItemID`; each item is created `wake_result = NOT_ATTEMPTED` / `WakeEventRef = null` before `StartWake` and updated explicitly by key afterward, and rollback consumes the stored keyed record." | Yes — matches Checks 1–4. |
| `STAGE_01_TERMINOLOGY.md` "`RollbackItemID` + keyed `rollback_items` + `NOT_ATTEMPTED` (AA6)" (`:1001`) | keyed map declaration; item created `WakeEventRef = null` / `wake_result = NOT_ATTEMPTED` before `StartWake`, stored record updated by key; `wake_result in { NOT_ATTEMPTED, wake_seated, wake_schedule_failed_before_transition, wake_transition_failed_after_seat }`; rollback consumes the stored keyed record iterating deterministically. | Yes — matches Check 1 (domain) and Checks 2–4. |
| `STAGE_01AA_SEMANTIC_TEST_VECTORS.md` TV235 (`:103`) | keyed item created `NOT_ATTEMPTED` / `null`, updated by key after `StartWake`, rollback consumes the stored record. | Yes — traces to Checks 2–4. |
| `STAGE_01_TRACEABILITY_MATRIX.csv` **R196** (`:197`) | "Make rollback-item updates explicit and keyed (AA6) … each item is created with `WakeEventRef = null` and `wake_result = NOT_ATTEMPTED` and added under `RollbackItemID` BEFORE `StartWake` then the stored record is updated explicitly by key … rollback consumes the stored keyed record iterating deterministically by `RollbackItemID` never a local-variable alias; applies to participant setup and template-refresh setup." Named defect: "a rollback that reads a stale local-variable alias instead of the stored post-`StartWake` `wake_result`/`WakeEventRef` or an item left without an explicit keyed record." | Yes — the six verified checks are exactly the R196 requirement; the named defect is eliminated (keyed create-before + keyed update-after + stored-record consumption; grep = 0 residual alias/list writes). |

All five cross-references (round state machine §3.10e AA6, invariant catalogue AA6 clause, terminology, TV235, and R196)
agree with the pseudocode source of truth. No divergence found.

---

## Deliverable tree (Stage 1AA)

This audit (`STAGE_01AA_ROLLBACK_ITEM_STORAGE_AUDIT.md`) is a member of the final Stage-1AA deliverable set:

1. `STAGE_01AA_CORRECTION_REPORT.md`
2. `STAGE_01AA_ROUND_ABORT_RESULT_AUDIT.md` (AA1)
3. `STAGE_01AA_RETRY_TERMINALIZATION_AUDIT.md` (AA2)
4. `STAGE_01AA_TRANSITION_POLICY_IDENTITY_AUDIT.md` (AA4)
5. `STAGE_01AA_STATE_ONLY_POLICY_GUARD_AUDIT.md` (AA5)
6. `STAGE_01AA_ROLLBACK_ITEM_STORAGE_AUDIT.md` (AA6) — this file
7. `STAGE_01AA_PROCEDURE_SIGNATURE_CALL_AUDIT.md`
8. `STAGE_01AA_PROCEDURE_CALL_GRAPH.md`
9. `STAGE_01AA_SEMANTIC_TEST_VECTORS.md` (TV227–TV235)
10. `STAGE_01AA_SUPERSESSION_REGISTER.md`
11. `STAGE_01AA_CROSS_DOCUMENT_AUDIT.md`
12. `STAGE_01AA_CHECKSUM_MANIFEST.sha256`

The Stage-1A–1Z lettered artifacts are unchanged; Stage-1AA supersessions are recorded in
`STAGE_01AA_SUPERSESSION_REGISTER.md`.

---

## Result

**PASS** — AA6 is faithfully specified. `setup_rollback_item` carries a `RollbackItemID` and
`setup_transaction.rollback_items` is a keyed map `RollbackItemID -> setup_rollback_item` (both transactions initialise it
as `empty map`). Both seating loops — `PrepareParticipantsForNewRound` (`:1775`–`:1785`) and
`ContinueTemplateRefreshAssignmentSetup` (`:5094`–`:5106`) — create the item with `WakeEventRef = null` and
`wake_result = NOT_ATTEMPTED` under a deterministic `RollbackItemID` BEFORE `StartWake`, then UPDATE the STORED record
EXPLICITLY BY KEY (`.wake_result <- wr`; `.WakeEventRef <- actual | returned | null`), with no local-variable alias. Both
rollback owners — `RollbackParticipantSetup` (`:1916`) and `RollbackTemplateRefreshSetup` (`:1948`) — iterate the keyed
map deterministically via `SORT(KEYS(setup_txn.rollback_items) ascending)` and consume the stored keyed record's persisted
post-`StartWake` fields. No residual non-keyed list-append or alias-mutation pattern remains (grep = 0). The
recovery-install rollback `RollbackRecoveryAssignmentPlan`, which consumes `rollback_record.items` (an X1 list, not the
setup transaction), is explicitly outside AA6 scope and unchanged. The pseudocode, round state machine §3.10e, invariant
catalogue AA6 clause, terminology, TV235, and R196 are mutually consistent. This is a documentation-only audit of the
formal specification of the algorithm **PoCol** and the mechanism it studies — the idle policy within PoCol; the A1
baseline `8.420833333 kWh` is preserved.
