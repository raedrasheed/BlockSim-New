# STAGE 01Y — T12 Rollback-Closure Ownership Audit (Correction Y5)

**Scope.** Stage 1Y, correction **Y5** of the PoCol formal specification (the idle policy within
PoCol). This is a **documentation-only** audit. It verifies that the single named legal-`T12`
rollback operation and the single assignment-closure owner introduced by Y5 are internally
consistent across the sources of truth and the Stage-1Y layer.

**Sources of truth (read-only, never edited by this audit).**
- `STAGE_01_PROTOCOL_PSEUDOCODE.md` (the executable pseudocode).
- `STAGE_01_MINER_STATE_MACHINE.md` (the authoritative miner state machine).

**Cross-referenced Stage-1Y layer (skimmed, all present).**
`STAGE_01_ROUND_STATE_MACHINE.md` §3.10c (Y5); `STAGE_01_INVARIANT_CATALOGUE.md` I16 Stage-1Y
(Y5); `STAGE_01_TERMINOLOGY.md` (`AbortPendingWakeForRollback`);
`STAGE_01Y_SEMANTIC_TEST_VECTORS.md` (TV216); `STAGE_01_TRACEABILITY_MATRIX.csv` (R182).

**Baseline invariant.** The A1 energy baseline **8.420833333 kWh** is unchanged by Y5; this
correction is a rollback-closure ownership clarification and touches no energy quantity.

---

## 1. What Y5 asserts

Y5 defines exactly **one** named legal-`T12` rollback operation and exactly **one** owner of the
assignment-record close for a rollback:

- The rollback **transition** (`WAKING -> OFFLINE`, edge `T12`) is departed with
  `reason = validation_abort`, which is an **authoritative, already-declared `T12` trigger**
  (`ValidationAbort`) — **not** the assignment `termination_reason`.
- The **assignment-record close** (`status = CLOSED`, `custody_status = revoked`,
  `termination_reason = cancellation`, `revocation_reason = assignment_revoked`, `closure_detail`)
  is performed **exactly once**, by `AbortPendingWakeForRollback` alone.
- The transition **hook** (`ApplyMinerStateTransition`) changes **miner state only** for this
  form; it does not set the assignment-record closure fields. The hook and the operation never
  both close the same assignment.

Each claim is verified below with quoted current lines and reported greps.

---

## 2. Authoritative `T12` trigger set (miner state machine)

`STAGE_01_MINER_STATE_MACHINE.md` §3 transition table, **row T12** (line 530), verbatim trigger
cell:

> `| T12 | `WAKING` | Departure / WakeDeadlineExpiry / ValidationAbort | Ramp not completed or bound assignment fails I1/`TemplateID` validation within wake deadline, or liveness lost | Release bound range; stop wake accrual | `OFFLINE` | End `P_wake`; begin `P_offline` residency | No census change (never entered `H_active(t)`) | Attributable violation instead → `DISQUALIFIED` (T21) |`

So the declared `T12` trigger set is **{ Departure, WakeDeadlineExpiry, ValidationAbort }**, and
`ValidationAbort` is a declared trigger. The census column confirms `T12` makes **No census
change**.

The Stage-1Y addendum **§3.3** (lines 614–640) documents the rollback form without changing this
contract. Key quoted lines:

- Line 616–617:
  > `Stage 1Y does NOT change the authoritative `T12` contract: `T12` (`WAKING -> OFFLINE`) keeps its declared triggers **Departure / WakeDeadlineExpiry / ValidationAbort** (§3 transition table, row T12).`
- Line 621–624 (rollback uses the `ValidationAbort` trigger):
  > `The named rollback operation `AbortPendingWakeForRollback` … departs a still-`WAKING` miner via `T12` with transition `reason = validation_abort` — a trigger already declared for `T12`. It NEVER passes an assignment `termination_reason` (e.g. `cancellation`) as the transition trigger. The bound assignment's `assignment_version` is passed EXACTLY (never null).`
- Line 625–633 (one assignment-status owner, option B):
  > `For this rollback form, `ApplyMinerStateTransition` (the `T12` hook) changes miner state ONLY … It does NOT set the assignment-record closure fields. The SINGLE canonical assignment close (`status = CLOSED`, `custody_status = revoked`, `termination_reason = cancellation`, `revocation_reason = assignment_revoked`, `closure_detail = …`) is performed EXACTLY ONCE by `AbortPendingWakeForRollback`. The transition hook and the rollback operation never both release/close the same assignment.`
- Line 639–640 (supersession scope):
  > `This addendum supersedes the Stage-1W/1X description of the rollback edge as a bare `T12` with `reason = cancellation`; Stage-1A–1X lettered artifacts are unchanged (see `STAGE_01Y_SUPERSESSION_REGISTER.md`).`

**Finding (§3.3 + row T12): the `T12` trigger set is unchanged and §3.3 documents the rollback
form and the single closure owner. PASS.**

---

## 3. `AbortPendingWakeForRollback` — the one named operation

`PROCEDURE AbortPendingWakeForRollback` begins at line **1721**
(`grep -n "PROCEDURE AbortPendingWakeForRollback"` → `1721`). Its Y5-load-bearing steps, quoted:

**(1) Cancel the exact `WakeCompleteEvent` first** (line 1732–1733):
> `# (1) Y4: cancel the exact WakeCompleteEvent FIRST so no wake can activate anything mid-rollback.`
> `IF WakeEventRef is still pending on EQ: CANCEL WakeEventRef on EQ`

**(2) Depart `WAKING -> OFFLINE` via `T12` with `reason = validation_abort`, EXACT version**
(line 1740–1744):
> `IF miner_state(MinerID) = WAKING:`
> `  SET tr <- CALL ApplyMinerStateTransition(MinerID, WAKING, OFFLINE,`
> `         transition_envelope = rollback_envelope, reason = validation_abort,                      # Y5: authoritative T12 trigger`
> `         assignment_ref = assignment_version_ref(AssignmentID, assignment_version),               # Y2/X2: EXACT version, never null`
> `         candidate_id = null, propagation_id = null)   # F6/X8: closes WAKING residency, charges E_transition once, no census change (T12)`

The step-(2) comment (line 1734–1738) states the field separation explicitly:
> `# (2) Y5: depart a still-WAKING miner WAKING -> OFFLINE via the LEGAL T12 edge using its authoritative ValidationAbort`
> `#   trigger (reason = validation_abort — a T12 trigger declared in STAGE_01_MINER_STATE_MACHINE.md §3, NOT the`
> `#   assignment termination_reason). ApplyMinerStateTransition (F6/X8) owns miner state + residency + one-shot energy +`
> `#   census; for THIS rollback form it changes miner state ONLY and does NOT set the assignment-record closure fields`
> `#   (Y5 option B — the canonical assignment close is owned HERE, step 3). It binds the EXACT assignment version (Y2/X2).`

**(3) The single canonical assignment close** (line 1749–1753):
> `# (3) Y5: the SINGLE canonical assignment close (X7 fields). Performed EXACTLY ONCE here, only if the head is still`
> `#   live (a head already CLOSED by an earlier self-rollback is left as-is — idempotent).`
> `IF AssignmentID (version assignment_version) is a live head:`
> `  CLOSE AssignmentID (version assignment_version) as CLOSED (status = CLOSED, custody_status = revoked,`
> `        termination_reason = cancellation, revocation_reason = assignment_revoked, closure_detail = closure_detail)   # X7 canonical; Y5 sole owner`

**(6) Restore the ledgers** (line 1754–1755):
> `# (6) Y5: restore the coverage-state / custody ledgers from the before-image (I8a/I8b).`
> `RESTORE the coverage-state / custody ledgers for AssignmentID's range FROM coverage_custody_before_image`

**(4/5 residual gate + 7 structured return)** (line 1756–1760):
> `IF miner_state(MinerID) = WAKING:`
> `  RETURN wake_abort_failed(MinerID = MinerID, AssignmentID = AssignmentID, reason = residual_waking)`
> `RETURN wake_abort_completed(MinerID = MinerID, AssignmentID = AssignmentID, departed_to_offline = departed_to_offline)`
> `RETURNS: wake_abort_completed(MinerID, AssignmentID, departed_to_offline) | wake_abort_failed(MinerID, AssignmentID, reason)`

The closing `NOTE` (line 1761–1767) restates the ownership contract:
> `the transition hook and this operation NEVER both close the same assignment (Y5): the hook changes miner state only for this form; this operation owns the assignment-record close.`

All seven declared effects are present and the field separation is explicit inside the one
operation.

---

## 4. Field separation: `validation_abort` (transition) vs `cancellation` (assignment record)

Two fields carry distinct meanings and are never conflated:

| Field | Value in the rollback form | Where set | Role |
|---|---|---|---|
| transition `reason` | `validation_abort` | `ApplyMinerStateTransition(... WAKING, OFFLINE, reason = validation_abort ...)` (L1742) | The `T12` **transition trigger** (`ValidationAbort`), a declared miner-SM trigger (row T12, L530). |
| assignment `termination_reason` | `cancellation` | `CLOSE … as CLOSED (… termination_reason = cancellation …)` (L1752–1753) | An **assignment-record closure field**, alongside `revocation_reason = assignment_revoked` and `closure_detail`. |

`validation_abort` is passed **only** to the transition hook; `cancellation` is written **only**
onto the assignment record. `ApplyMinerStateTransition` treats `reason` as the transition trigger
(see §6), so `validation_abort` is the correct field to carry it. The assignment
`termination_reason = cancellation` is never handed to the hook as a transition trigger.

**Finding: the transition trigger (`validation_abort`, a declared `T12` trigger) and the
assignment-record `termination_reason` (`cancellation`) are separate fields, never conflated.
PASS.**

---

## 5. Single-owner verification (reported greps)

### 5.1 `grep -n "CLOSE .* as CLOSED" STAGE_01_PROTOCOL_PSEUDOCODE.md`

```
1752:      CLOSE AssignmentID (version assignment_version) as CLOSED (status = CLOSED, custody_status = revoked,
2064:    CLOSE assignment as CLOSED (status = CLOSED, custody_status = revoked, termination_reason = wake_failure,
3232:    CLOSE assignment as CLOSED (status = CLOSED, custody_status = revoked, termination_reason = wake_failure,
4097:      CLOSE assignment as CLOSED (status = CLOSED, custody_status = revoked, termination_reason = wake_failure,
```

Annotated by owning procedure and `termination_reason`:

| Line | Owning procedure | `termination_reason` | `closure_detail` | Form |
|---|---|---|---|---|
| **1752** | **`AbortPendingWakeForRollback`** | **`cancellation`** | `closure_detail` (param) | **The Y5 canonical rollback close** |
| 2064 | `RangeAssignFromPlan` | `wake_failure` | `range_assign_wake_failed` | Create-then-wake self-revert (not a rollback-owner) |
| 3232 | `ReserveActivateFromPlan` | `wake_failure` | `reserve_activation_wake_failed` | Create-then-wake self-revert (not a rollback-owner) |
| 4097 | `RangeReassignFromPlan` | `wake_failure` | `range_reassign_wake_failed` | Create-then-wake self-revert (not a rollback-owner) |

The **only** `CLOSE … as CLOSED` bearing `termination_reason = cancellation` (the Y5 canonical
rollback close) is at **line 1752, inside `AbortPendingWakeForRollback`**. The other three closes
are a distinct wake-failure self-revert form (`termination_reason = wake_failure`) inside the
plan-bound create-then-wake procedures — a different closure kind, not the setup/recovery rollback
close, and none of them is one of the three rollback owners.

### 5.2 `grep -n "WAKING, OFFLINE" STAGE_01_PROTOCOL_PSEUDOCODE.md`

```
1260:      CALL ApplyMinerStateTransition(MinerID, WAKING, OFFLINE,
1741:      SET tr <- CALL ApplyMinerStateTransition(MinerID, WAKING, OFFLINE,
3991:          CALL ApplyMinerStateTransition(holder, WAKING, OFFLINE,
4665:          CALL ApplyMinerStateTransition(h, WAKING, OFFLINE,
4789:          CALL ApplyMinerStateTransition(h, WAKING, OFFLINE,
```

Annotated by owning procedure and transition `reason`:

| Line | Owning procedure | transition `reason` | `T12` trigger | Rollback form? |
|---|---|---|---|---|
| 1260 | `WakeCompleteEvent` (wake-failure path) | `wake_deadline_expiry` | WakeDeadlineExpiry | No |
| **1741** | **`AbortPendingWakeForRollback`** | **`validation_abort`** | **ValidationAbort** | **Yes — the Y5 rollback edge** |
| 3991 | `LeaseExpiry` (PENDING case) | `lease_expired_while_waking` | (T12, lease path) | No |
| 4665 | `CloseRoundAssignments` (WAKING case) | `round_closed_while_waking` | (T12, round-close path) | No |
| 4789 | `CloseTemplateAssignments` (WAKING case) | `template_refresh_wake_abort` | (T12, template-refresh path) | No |

The **only** `WAKING -> OFFLINE` transition carrying the **rollback** trigger
`reason = validation_abort` is at **line 1741, inside `AbortPendingWakeForRollback`**. Every other
`WAKING -> OFFLINE` occurrence is a distinct non-rollback `T12` form with its own reason
(`wake_deadline_expiry` / `lease_expired_while_waking` / `round_closed_while_waking` /
`template_refresh_wake_abort`), in a non-rollback-owner procedure. The rollback `T12` transition
appears **only** inside `AbortPendingWakeForRollback`.

### 5.3 The three rollback owners no longer open-code the transition or the close

Procedure spans:
- `RollbackParticipantSetup` — lines 1769–1804.
- `RollbackTemplateRefreshSetup` — lines 1806–1833.
- `RollbackRecoveryAssignmentPlan` — lines 3801–3843.

None of these spans contains a `CLOSE … as CLOSED` hit (§5.1 hits are at 1752 / 2064 / 3232 /
4097 — none in these ranges) or a `WAKING, OFFLINE` hit (§5.2 hits are at 1260 / 1741 / 3991 /
4665 / 4789 — none in these ranges). Each owner instead **calls** the one named operation:

- `RollbackParticipantSetup` (L1784):
  > `SET wr <- CALL AbortPendingWakeForRollback(RoundContext, MinerID = m, AssignmentID = aid, assignment_version = ver, … closure_detail = participant_setup_rolled_back, …)`
- `RollbackTemplateRefreshSetup` (L1816):
  > `SET wr <- CALL AbortPendingWakeForRollback(RoundContext, MinerID = m, AssignmentID = aid, assignment_version = ver, … closure_detail = template_refresh_setup_rolled_back, …)`
- `RollbackRecoveryAssignmentPlan` (L3818):
  > `SET wr <- CALL AbortPendingWakeForRollback(RoundContext, MinerID = item.MinerID, AssignmentID = item.AssignmentID, assignment_version = item.assignment_version, … closure_detail = recovery_install_rolled_back, …)`

**Finding: the rollback `T12` departure (`validation_abort`) and the canonical rollback close
(`termination_reason = cancellation`) live only inside `AbortPendingWakeForRollback`; the three
rollback owners open-code neither and delegate to the one named operation. PASS.**

---

## 6. `reason` is the transition trigger (`ApplyMinerStateTransition`)

`PROCEDURE ApplyMinerStateTransition` (begins line 1028) takes `reason` as an input (line 1031)
and folds it into the immutable `TransitionEventID` (line 1082–1085):

> `SET TransitionEventID <- (envelope_namespace, hook_id, event_time, delta_cycle, event_seq,`
> `                          MinerID, old_state, new_state, reason,`
> `                          AssignmentID(assignment_ref), assignment_version(assignment_ref),`
> `                          candidate_id, propagation_id)                       # R3: namespace + hook_id in the id (immutable, J3)`

and records it in the transition audit (line 1122–1123):
> `RECORD transition_audit(TransitionEventID, MinerID, old_state, new_state, event_time,`
> `                        delta_cycle, event_seq, reason, assignment_ref, candidate_id, propagation_id)`

Because `reason` is a component of the `TransitionEventID` (the transition trigger/identity), the
rollback edge correctly carries its `T12` trigger as `reason = validation_abort`. The
assignment-record `termination_reason` is not an input to this hook and never becomes part of a
`TransitionEventID`.

The hook is also the sole owner of the miner-state/residency/energy/census effects (NOTE at
L1154–1156, and step 5a–5f at L1107–1131); for the rollback form it makes **no census change** —
consistent with the `T12` census column (row T12, L530) since the miner never entered
`ACTIVE_HASHING`.

**Finding: `ApplyMinerStateTransition` treats `reason` as the transition trigger; `validation_abort`
is the correct field to carry the `T12` trigger. PASS.**

---

## 7. Audit results (per Y5 acceptance point)

| # | Acceptance point | Grounding | Result |
|---|---|---|---|
| 1 | Rollback `T12` departure uses `reason = validation_abort`, a trigger declared in the authoritative miner state machine | Pseudocode L1741–1742; miner-SM row T12 L530; §3.3 L621–624 | **PASS** |
| 2 | Assignment `termination_reason = cancellation` is an assignment-record field, never the transition trigger | Pseudocode L1752–1753 (record) vs L1741–1742 (transition); comment L1734–1738; §4 table | **PASS** |
| 3 | `AbortPendingWakeForRollback` is the SINGLE owner of the canonical assignment close | Grep §5.1 (only L1752 carries `termination_reason = cancellation`, inside the operation); step (3) L1749–1753 | **PASS** |
| 4 | The transition hook and the operation never both close the same assignment (three rollback owners open-code neither) | Hook changes miner state only (L1736–1738; miner-SM §3.3 L625–633); grep §5.2/§5.3 (rollback edge only at L1741; no close/transition inside the three owner spans) | **PASS** |
| 5 | Miner-SM §3.3 documents this and the `T12` trigger set is unchanged (Departure / WakeDeadlineExpiry / ValidationAbort) | Miner-SM row T12 L530; §3.3 L614–640 | **PASS** |

---

## 8. Test-vector linkage (TV216)

`STAGE_01Y_SEMANTIC_TEST_VECTORS.md` **TV216** (lines 82–91), "Rollback T12 uses the
authoritative ValidationAbort trigger; one closure owner (Y5)":

> `- **Expected:** the departure calls `ApplyMinerStateTransition(m, WAKING, OFFLINE, reason = validation_abort, assignment_ref = assignment_version_ref(AssignmentID, assignment_version), ...)` — `validation_abort` is a declared `T12` trigger in `STAGE_01_MINER_STATE_MACHINE.md` §3, and the version is exact. The transition hook changes miner state only (residency close + one-shot energy + no census change); the canonical assignment close (`termination_reason = cancellation`, `revocation_reason = assignment_revoked`, `closure_detail`) is performed by `AbortPendingWakeForRollback` ONLY. The hook and the operation never both close the same assignment.`

The TV216 index row (L127) binds it to Y5 with procedures
`AbortPendingWakeForRollback`, `ApplyMinerStateTransition`. TV216 mirrors, one-for-one, the
pseudocode form audited in §3–§6: same call signature, same field separation, same single-owner
close, same hook/operation non-overlap. **Linkage consistent.**

---

## 9. Cross-document consistency

Pseudocode ↔ miner-SM §3.3 T12 ↔ round-SM §3.10c (Y5) ↔ invariant I16 (Y5) ↔ terminology ↔ R182:

| Document / locus | Quoted assertion (abridged to load-bearing text) | Agrees with pseudocode? |
|---|---|---|
| `STAGE_01_PROTOCOL_PSEUDOCODE.md` `AbortPendingWakeForRollback` (L1721–1767) | departs via `reason = validation_abort`; single canonical close `termination_reason = cancellation`; hook and op never both close | — (source) |
| `STAGE_01_MINER_STATE_MACHINE.md` row T12 (L530) + §3.3 (L614–640) | triggers `Departure / WakeDeadlineExpiry / ValidationAbort` unchanged; rollback uses `reason = validation_abort`, "NOT … an assignment `termination_reason` … as the transition trigger"; `AbortPendingWakeForRollback` performs the close "EXACTLY ONCE" | Yes |
| `STAGE_01_ROUND_STATE_MACHINE.md` §3.10c (L760–765) | "departs a `WAKING` miner via `T12` using its authoritative `ValidationAbort` trigger (`reason = validation_abort` …), NOT the assignment `termination_reason` … SINGLE owner of the canonical assignment close … The hook and the operation never both close the same assignment." | Yes |
| `STAGE_01_INVARIANT_CATALOGUE.md` I16 Stage-1Y (L357–361) | "the ONE named operation `AbortPendingWakeForRollback` departs a `WAKING` miner via `T12` using its authoritative `ValidationAbort` trigger (`reason = validation_abort`, declared in … §3), never the assignment `termination_reason`, and is the SINGLE owner of the canonical assignment close" | Yes |
| `STAGE_01_TERMINOLOGY.md` (L928–936) | `AbortPendingWakeForRollback` = the one named rollback wake-abort; `reason = validation_abort` "NOT the assignment `termination_reason`"; "SOLE owner of the assignment close for a rollback (the transition hook changes miner state only for this form)" | Yes |
| `STAGE_01Y_SEMANTIC_TEST_VECTORS.md` TV216 (L82–91) | executable expectation matching the pseudocode form (see §8) | Yes |
| `STAGE_01_TRACEABILITY_MATRIX.csv` R182 (L183) | "Define one legal T12 rollback trigger and one closure owner (Y5) … via the authoritative T12 ValidationAbort trigger (reason = validation_abort … not the assignment termination_reason) … performs the SINGLE canonical assignment close … the transition hook and the operation never both close the same assignment"; invariants `I16;I18b;I19`; status `SPECIFIED` | Yes |
| `STAGE_01Y_SUPERSESSION_REGISTER.md` Y5 (L18) | supersedes the prior "`reason = cancellation` (the assignment `termination_reason` used as the transition trigger)" open-coded form with the single named operation and single close owner | Yes |

All seven cross-references agree with the pseudocode and with one another. No conflict detected.

---

## 10. Final Stage-1Y deliverable tree (context)

Stage-1Y deliverables present in
`docs/thesis_revision_v45/stage_01/`, with this audit added:

- `STAGE_01Y_CORRECTION_REPORT.md`
- `STAGE_01Y_PROCEDURE_CALL_GRAPH.md`
- `STAGE_01Y_PROCEDURE_SIGNATURE_CALL_AUDIT.md`
- `STAGE_01Y_RETRY_GENERATION_OWNERSHIP_AUDIT.md`
- `STAGE_01Y_SEMANTIC_TEST_VECTORS.md`
- `STAGE_01Y_SETUP_RETRY_REPLAY_AUDIT.md`
- `STAGE_01Y_SUPERSESSION_REGISTER.md`
- `STAGE_01Y_TEMPLATE_RETRY_IDENTITY_AUDIT.md`
- `STAGE_01Y_T12_CLOSURE_OWNERSHIP_AUDIT.md` (this document)

The sources of truth (`STAGE_01_PROTOCOL_PSEUDOCODE.md`, `STAGE_01_MINER_STATE_MACHINE.md`) and
the Stage-1A–1X lettered artifacts are unchanged; Stage-1Y supersessions are recorded in
`STAGE_01Y_SUPERSESSION_REGISTER.md`. The A1 baseline **8.420833333 kWh** is preserved.

---

## 11. Result

**PASS — Y5 defines exactly one named legal-`T12` rollback operation
(`AbortPendingWakeForRollback`, departing `WAKING -> OFFLINE` via the authoritative
`ValidationAbort` trigger `reason = validation_abort`) and exactly one assignment-closure owner
(the same operation performs the sole canonical close `termination_reason = cancellation`); the
transition trigger and the assignment-record `termination_reason` are separate fields never
conflated, the hook and the operation never both close the same assignment, the three rollback
owners open-code neither, and the pseudocode is consistent with miner-SM row T12 / §3.3, round-SM
§3.10c, invariant I16, terminology, TV216, and R182.**
