# Stage 1X — Canonical Closure Enum Audit (X7)

## 1. Scope

This audit documents correction **X7** of the Stage-1X revision to the PoCol formal
specification (the idle policy within PoCol): *every Stage-1X head closure sets
`status` / `custody_status` / `termination_reason` / `revocation_reason` from the CANONICAL
enums only, and records any fine-grained free-text descriptor in a NEW non-enum field
`closure_detail`.* No string outside the canonical enums may appear in `termination_reason`,
`custody_status`, or `revocation_reason`.

The audit is descriptive and documentation-only. It reads the current specification text and
records the state of the corrected contract; it modifies no protocol file. Every claim below is
grounded in the current text of

- `STAGE_01_PROTOCOL_PSEUDOCODE.md` (the normative pseudocode; line references re-established by
  grep against the current file, not inherited from an earlier revision),

with traceability confirmed against `STAGE_01_ROUND_STATE_MACHINE.md`,
`STAGE_01_TERMINOLOGY.md`, `STAGE_01_INVARIANT_CATALOGUE.md`, and
`STAGE_01_TRACEABILITY_MATRIX.csv`.

The A1 energy-accounting baseline (`8.420833333 kWh`,
`STAGE_01_ENERGY_MODEL_SPECIFICATION.md` line 29) is unaffected by this correction and is
preserved unchanged; X7 is a closure-record / enum-hygiene correction with no energy semantics.

## 2. The canonical enums (source of truth)

The `Assignment` version object is declared in §0.8 Core data model (`STRUCTURE Assignment`,
`STAGE_01_PROTOCOL_PSEUDOCODE.md` line 874). The four closure-relevant fields draw from these
canonical enums, and X7 adds `closure_detail` as the sole non-enum descriptor:

| Field | Line(s) | Canonical enum (verbatim) |
|---|---|---|
| `status` | 879 | `{PENDING, CURRENT, PAUSED, SUPERSEDED, CLOSED}` |
| `custody_status` | 889–890 | `{original, renewed, reassigned, revoked, expired, abandoned, completed, superseded_by_template_refresh}` |
| `revocation_reason` | 891–892 | `{adversarial_withdrawal, assignment_revoked, lease_conflict, departure}` (set ONLY when `custody_status = revoked`) |
| `termination_reason` | 894–896 | `{lease_expiry, adversarial_withdrawal, assignment_revoked, abandonment, wake_failure, cancellation, round_closure, template_closure, range_exhausted}` (set ONLY when `status = CLOSED`) |
| `closure_detail` | 900–906 | **NON-ENUM** free-text audit string (NEW at X7) |

The `closure_detail` declaration is explicit and self-scoping. Quoting lines 900–906:

> `closure_detail` : X7 — a NON-ENUM audit string carrying the fine-grained closure provenance (e.g.
> participant_setup_rolled_back, template_refresh_setup_rolled_back, recovery_install_rolled_back,
> range_assign_wake_failed, range_reassign_wake_failed, reserve_activation_wake_failed). It is
> the ONLY field that may hold such free text: NO string outside the canonical enums is ever
> stored in custody_status, revocation_reason, or termination_reason (X7). Every rollback /
> wake-failure close sets termination_reason + custody_status + revocation_reason (where
> applicable) from the canonical enums AND records the specific cause in closure_detail.

Confirmed: the `closure_detail` field is declared **inside the §0.8 `STRUCTURE Assignment`
record** (line 900), immediately after `termination_reason`, and is documented as the exclusive
carrier of free text.

## 3. Stage-1X closure-site inventory

Every Stage-1X `CLOSE ... as CLOSED (...)` that carries a `closure_detail` was located by a
corpus grep for `closure_detail` in `STAGE_01_PROTOCOL_PSEUDOCODE.md`; six closure sites exist,
in six distinct procedures. The table below is filled from the actual quoted `CLOSE` lines.

| Procedure (header line) | CLOSE line | `status` | `custody_status` | `termination_reason` | `revocation_reason` | `closure_detail` |
|---|---|---|---|---|---|---|
| `RollbackParticipantSetup` (1678) | 1704–1705 | `CLOSED` | `revoked` | `cancellation` | `assignment_revoked` | `participant_setup_rolled_back` |
| `RollbackTemplateRefreshSetup` (1718) | 1737–1738 | `CLOSED` | `revoked` | `cancellation` | `assignment_revoked` | `template_refresh_setup_rolled_back` |
| `RangeAssignFromPlan` (1926) | 1958–1959 | `CLOSED` | `revoked` | `wake_failure` | `assignment_revoked` | `range_assign_wake_failed` |
| `ReserveActivateFromPlan` (3098) | 3126–3127 | `CLOSED` | `revoked` | `wake_failure` | `assignment_revoked` | `reserve_activation_wake_failed` |
| `RollbackRecoveryAssignmentPlan` (3695) | 3720–3721 | `CLOSED` | `revoked` | `cancellation` | `assignment_revoked` | `recovery_install_rolled_back` |
| `RangeReassignFromPlan` (3963) | 3992–3993 | `CLOSED` | `revoked` | `wake_failure` | `assignment_revoked` | `range_reassign_wake_failed` |

Verbatim quotations of the two closure clauses (one per closure family):

Rollback close (three sites — `cancellation`), e.g. `RollbackRecoveryAssignmentPlan` lines 3720–3721:

> `CLOSE item.AssignmentID as CLOSED (status = CLOSED, custody_status = revoked, termination_reason = cancellation,`
> `revocation_reason = assignment_revoked, closure_detail = recovery_install_rolled_back)   # X7: canonical fields (J7/I18b)`

Wake-failure close (three sites — `wake_failure`), e.g. `RangeAssignFromPlan` lines 1958–1959:

> `CLOSE assignment as CLOSED (status = CLOSED, custody_status = revoked, termination_reason = wake_failure,`
> `revocation_reason = assignment_revoked, closure_detail = range_assign_wake_failed)   # X7 canonical (J7/I18b): no live head`

## 4. Verification

### 4.1 PASS — every canonical field draws only from its canonical enum

Checking each of the six sites' four canonical fields against the §2 enums (enum member names in
parentheses):

- `status` = `CLOSED` at all six sites — a member of `{PENDING, CURRENT, PAUSED, SUPERSEDED, CLOSED}` (879). **PASS**
- `custody_status` = `revoked` at all six sites — a member of `{original, renewed, reassigned, revoked, ...}` (889–890). **PASS**
- `termination_reason` = `cancellation` (sites 1, 2, 5) and `wake_failure` (sites 3, 4, 6) — both members of `{lease_expiry, adversarial_withdrawal, assignment_revoked, abandonment, wake_failure, cancellation, round_closure, template_closure, range_exhausted}` (894–896). **PASS**
- `revocation_reason` = `assignment_revoked` at all six sites — a member of `{adversarial_withdrawal, assignment_revoked, lease_conflict, departure}` (891–892), and legal because `custody_status = revoked` at every site (the field is set ONLY when `custody_status = revoked`, per 891). **PASS**

No canonical field at any of the six sites holds a value outside its enum. **PASS.**

### 4.2 PASS — `closure_detail` is a NEW non-enum descriptor carrying every free-text token

`closure_detail` is declared in the §0.8 `STRUCTURE Assignment` record (line 900) as a NON-ENUM
audit string and is the ONLY field permitted to hold free text (900–906). A corpus grep for
`closure_detail = <token>` returns exactly the six expected free-text descriptors, each used
exactly once, and each confined to `closure_detail`:

| Free-text token | Occurrences | Sole host field |
|---|---|---|
| `participant_setup_rolled_back` | 1 | `closure_detail` |
| `template_refresh_setup_rolled_back` | 1 | `closure_detail` |
| `recovery_install_rolled_back` | 1 | `closure_detail` |
| `range_assign_wake_failed` | 1 | `closure_detail` |
| `range_reassign_wake_failed` | 1 | `closure_detail` |
| `reserve_activation_wake_failed` | 1 | `closure_detail` |

All six mandated tokens are present and are carried by `closure_detail`, not by any canonical
enum field. **PASS.**

### 4.3 PASS — corpus scan finds NO free text in `termination_reason` / `custody_status` / `revocation_reason`

A whole-file scan of `STAGE_01_PROTOCOL_PSEUDOCODE.md` enumerating every right-hand value
assigned to each canonical field (`grep -oE "<field> = [a-z_]+"`, deduplicated) returns:

- `termination_reason` = `{assignment_revoked (×1), cancellation (×3), lease_expiry (×3), wake_failure (×3)}` — every value is a `termination_reason` enum member.
- `custody_status` = `{completed (×1), expired (×1), revoked (×10)}` — every value is a `custody_status` enum member.
- `revocation_reason` = `{adversarial_withdrawal (×3), assignment_revoked (×6)}` — every value is a `revocation_reason` enum member.

A complementary scan for any of the six `closure_detail` tokens appearing on the right of a
canonical field — `grep -nE "(termination_reason|custody_status|revocation_reason) = (participant_setup_rolled_back|template_refresh_setup_rolled_back|recovery_install_rolled_back|range_assign_wake_failed|range_reassign_wake_failed|reserve_activation_wake_failed)"` —
returns **no matches**. No free-text descriptor is ever placed in a canonical enum field
across the entire corpus. **Scan result: PASS (zero free-text strings in the three canonical
fields).**

## 5. Test-vector linkage (TV207)

`STAGE_01_TRACEABILITY_MATRIX.csv` row R177 (line 178) carries the Stage-1X recovery-rollback /
retry-contract closure vectors (TV198–TV209). The X7 vector is:

> `TV207 every Stage-1X closure sets only canonical enum fields and a closure_detail`

TV207 sits in the row whose test-vector document is `STAGE_01X_SEMANTIC_TEST_VECTORS`, whose
named procedures include `RollbackRecoveryAssignmentPlan`, `CommitRecoveryAssignmentPlan`,
`ContinueTemplateRefreshAssignmentSetup`, `SetupRetryEvent`, `CreatePendingAssignment`,
`ApplyMinerStateTransition`, and `CommitSecurityCensus`, and whose invariant set includes
`I18b` and `I16`. TV207 is precisely the observable this audit verifies at the six closure
sites: canonical enum fields only, plus a `closure_detail`.

## 6. Cross-document consistency

The X7 contract is stated consistently across the four normative documents:

- **Pseudocode (source of truth).** §0.8 `STRUCTURE Assignment` declares the canonical enums
  (lines 879, 889–896) and the new non-enum `closure_detail` (900–906); the six closure sites
  (§3 above) apply it verbatim.
- **Round state machine §3.10b (Stage-1X addendum), clause X7** (`STAGE_01_ROUND_STATE_MACHINE.md`
  lines 718–721): "Every rollback / wake-failure close sets `status = CLOSED`, `custody_status`,
  `termination_reason`, and (where applicable) `revocation_reason` from the canonical enums, and
  records the fine-grained cause in the non-enum `closure_detail` audit field. No string outside
  the canonical enums is stored in `termination_reason`, `custody_status`, or `revocation_reason`."
  This matches the pseudocode exactly.
- **Invariant catalogue.** The Stage-1X clause **X7** in the invariant narrative
  (`STAGE_01_INVARIANT_CATALOGUE.md` lines 343–344): "every rollback/wake-failure close uses
  canonical `custody_status`/`revocation_reason`/`termination_reason` values plus a non-enum
  `closure_detail`." This is anchored to **I18b** (lines 409–437: an OPEN lineage has exactly one
  live head; a CLOSED lineage has ZERO live heads; `J7` canonical terminal status — `CLOSED` for
  every non-renewal end-of-life, with `custody_status = revoked` / `revocation_reason` from the
  enum), so each X7 close both uses canonical fields and leaves zero live heads. It is likewise
  consistent with **I16** (lines 284–288: breaches recorded, not silently repaired) — a rollback
  close is a recorded, canonically-typed terminal event, never a silent overwrite.
- **Terminology** (`STAGE_01_TERMINOLOGY.md` lines 895–902), entry "Canonical closure fields +
  `closure_detail` (X7)": enumerates the same fixed uses site-by-site (participant setup rollback,
  template-refresh setup rollback, recovery-plan rollback, range/reserve wake failure) with the
  identical `closure_detail` tokens, and closes with "No string outside the canonical enums
  appears in `termination_reason`, `custody_status`, or `revocation_reason`."

All four documents agree: canonical enums for `status`/`custody_status`/`termination_reason`/
`revocation_reason`, and the non-enum `closure_detail` as the sole carrier of the fine-grained
descriptor. No divergence found.

## 7. Result

**PASS — X7 verified.** All six Stage-1X head-closure sites set `status = CLOSED`,
`custody_status = revoked`, `termination_reason ∈ {cancellation, wake_failure}`, and
`revocation_reason = assignment_revoked` from the canonical §0.8 enums only; each fine-grained
cause is carried solely by the new non-enum `closure_detail` field; a whole-corpus scan finds
zero free-text strings in `termination_reason` / `custody_status` / `revocation_reason`; and the
contract is consistent across pseudocode §0.8, round-SM §3.10b (X7), invariant catalogue
(X7 / I18b / I16), terminology, and test vector TV207.
