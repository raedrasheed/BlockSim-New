# Stage 1I — Custody-Enum Audit (I-07)

Audits correction **I-07**: `custody_status` takes ONLY a value from the CANONICAL, CLOSED enum, and
an adversarial withdrawal is expressed by the TWO-FIELD representation `custody_status = revoked` +
`revocation_reason = adversarial_withdrawal`, never by an invented custody value. Binds to
`STAGE_01_PROTOCOL_PSEUDOCODE.md` §0.8 (`STRUCTURE Assignment`: `custody_status` /
`revocation_reason`), §8a (`AdversarialParticipationChangeEvent` exit path), §0.10
(`WakeCompleteEvent` wake-failure), §0.11 (`CreatePendingAssignment`), §6 (`ExhaustionAdjudicate`
PATH A), `RenewAssignment`, and `TemplateRefresh`; to `STAGE_01_INVARIANT_CATALOGUE.md` I8b (custody /
provenance model) and I9 (provenance); to `STAGE_01_TERMINOLOGY.md` (Stage-1I addendum); and to
`STAGE_01I_SEMANTIC_TEST_VECTORS.md` TV69. This is a specification act on **PoCol** with the idle
policy within PoCol enabled — not a claim of implementation, enforcement, security, fairness, or any
derived property. No new consensus feature is introduced; the eight miner states and the assignment
schema are unchanged, and the A1 baseline (8.420833333 kWh) is untouched.

## 1. The corrected-away problem

The frozen Stage-1H exit path recorded an adversarial `ACTIVE_HASHING` withdrawal by writing
`custody_status(range(X)) = revoked_adversarial_exit` — an **UNDECLARED custody value outside the
canonical enum** (an ad-hoc, per-cause state fabricated at the exit site). This conflated two
orthogonal facts into one field: the custody/lineage disposition (the range is `revoked`) and the
*cause* of that disposition (an adversarial withdrawal). An open-ended custody vocabulary defeats the
I8b "CANONICAL, CLOSED enum" premise — every new cause would mint a new custody value — and makes the
custody model unauditable against a fixed set.

## 2. The correction

I-07 fixes `custody_status` to a **closed** enum and moves the cause to a **separate**
`revocation_reason` field, set only when `custody_status = revoked`:

- `custody_status ∈ {original, renewed, reassigned, revoked, expired, abandoned, completed,
  superseded_by_template_refresh}` (8 values; no others admissible).
- An adversarial withdrawal is the **two-field** representation
  `custody_status = revoked` **AND** `revocation_reason = adversarial_withdrawal`.
- The token `revoked_adversarial_exit` is **NOT** a `custody_status`; it survives only inside
  prohibition comments.

## 3. Canonical enum (quoted from `STRUCTURE Assignment`, §0.8)

The `custody_status` / `revocation_reason` fields appear verbatim in the §0.8 Assignment struct as:

```
custody_status              : one of the CANONICAL enum ONLY (I-07): {original, renewed, reassigned,
                              revoked, expired, abandoned, completed, superseded_by_template_refresh}
revocation_reason           : set ONLY when custody_status = revoked (else null); one of
                              {adversarial_withdrawal, assignment_revoked, lease_conflict, departure} (I-07).
                              A revocation NEVER invents a new custody_status value; the cause lives HERE.
```

- **8 custody values:** `original`, `renewed`, `reassigned`, `revoked`, `expired`, `abandoned`,
  `completed`, `superseded_by_template_refresh`.
- **4 revocation_reason values (only when `custody_status = revoked`, else `null`):**
  `adversarial_withdrawal`, `assignment_revoked`, `lease_conflict`, `departure`.

## 4. Cross-document consistency

| Document / location | What it says about `custody_status` / `revocation_reason` | Consistent? |
|---|---|---|
| Assignment schema — `STAGE_01_PROTOCOL_PSEUDOCODE.md` §0.8 (`STRUCTURE Assignment`) | Declares `custody_status` = canonical 8-value enum ONLY (I-07); `revocation_reason` set only when `custody_status = revoked`, one of `{adversarial_withdrawal, assignment_revoked, lease_conflict, departure}`; "A revocation NEVER invents a new custody_status value; the cause lives HERE." | **PASS** |
| Adversarial exit — §8a `AdversarialParticipationChangeEvent` (`direction = exit`) | `SET custody_status(range(X)) <- revoked` (comment: "canonical enum value"); `SET revocation_reason(X) <- adversarial_withdrawal` ("I-07 two-field representation"); `RECORD provenance(X): … custody_status = revoked, revocation_reason = adversarial_withdrawal`; I-07 comment forbids `revoked_adversarial_exit`. | **PASS** |
| Invariant catalogue — `STAGE_01_INVARIANT_CATALOGUE.md` I8b | Custody status is from the "CANONICAL, CLOSED enum `{original, renewed, reassigned, revoked, expired, abandoned, completed, superseded_by_template_refresh}` (I-07)"; adversarial withdrawal "sets `custody_status = revoked` and records the cause in the SEPARATE `revocation_reason` field … never an invented value such as `revoked_adversarial_exit`." | **PASS** |
| Terminology — `STAGE_01_TERMINOLOGY.md` Stage-1I addendum ("Canonical custody enum + `revocation_reason` (I-07)") | `custody_status` takes ONLY the canonical 8-value enum; adversarial withdrawal sets `custody_status = revoked` + `revocation_reason = adversarial_withdrawal`; "NEVER invents a custody value such as `revoked_adversarial_exit`. The cause lives in the separate `revocation_reason` field." | **PASS** |
| Test vectors — `STAGE_01I_SEMANTIC_TEST_VECTORS.md` TV69 | Exit sets `custody_status(range(X)) <- revoked` (CANONICAL) and `revocation_reason(X) <- adversarial_withdrawal` (two-field, I-07); "never assigns `custody_status <- revoked_adversarial_exit` or any non-enum value." Expected: `custody_status = revoked` AND `revocation_reason = adversarial_withdrawal`; no undeclared value; I8b canonical enum holds. | **PASS** |

*Note.* The base `STAGE_01_TERMINOLOGY.md` §1 glossary row ("Custody status") predates I-07 and lists
seven values (omits `superseded_by_template_refresh`); the **Stage-1I addendum** carries the
authoritative canonical 8-value enum and matches §0.8 / I8b exactly. `superseded_by_template_refresh`
is a template-refresh lineage marker outside the adversarial-withdrawal scope of I-07; the I-07 verdict
is unaffected.

## 5. No procedure sets `custody_status` outside the canonical enum

Every `SET custody_status(…)` site in `STAGE_01_PROTOCOL_PSEUDOCODE.md` assigns a canonical enum value:

| Procedure / section | Assigned `custody_status` | Canonical? |
|---|---|---|
| §0.11 `CreatePendingAssignment` (CASE ORIGINAL) | `original` | yes |
| §0.11 `CreatePendingAssignment` (CASE REASSIGNED) | `reassigned` | yes |
| `RenewAssignment` (new same-range version) | `renewed` | yes |
| §6 `ExhaustionAdjudicate` (PATH A, accepted completion) | `completed` | yes |
| §0.10 `WakeCompleteEvent` wake-failure (CASE PENDING and CASE PAUSED) | `abandoned` | yes |
| §8a `AdversarialParticipationChangeEvent` exit | `revoked` (+ `revocation_reason = adversarial_withdrawal`) | yes |
| `TemplateRefresh` (I8b lineage marker) | `superseded_by_template_refresh` | yes |

No site assigns a value outside `{original, renewed, reassigned, revoked, expired, abandoned,
completed, superseded_by_template_refresh}`. The string `revoked_adversarial_exit` never appears as an
assigned value: it occurs ONLY inside I-07 prohibition comments — §8a
("never in an invented custody_status value (no `revoked_adversarial_exit`)"), I8b ("never an invented
value such as `revoked_adversarial_exit`"), the Stage-1I terminology addendum, and TV69's negative
assertion — never on the right-hand side of a `SET custody_status`.

## 6. Acceptance-style PASS checklist

| # | Check | Result |
|--:|-------|--------|
| C1 | `custody_status` is a CANONICAL, CLOSED 8-value enum, declared in the §0.8 Assignment struct | **PASS** |
| C2 | Adversarial withdrawal uses the TWO-FIELD representation (`custody_status = revoked` + `revocation_reason = adversarial_withdrawal`) | **PASS** |
| C3 | `revocation_reason` is set ONLY when `custody_status = revoked` (else `null`), from `{adversarial_withdrawal, assignment_revoked, lease_conflict, departure}` | **PASS** |
| C4 | No procedure assigns `custody_status` a value outside the canonical enum | **PASS** |
| C5 | `revoked_adversarial_exit` appears ONLY in prohibition comments, never as an assigned value | **PASS** |
| C6 | Schema (§0.8), procedure (§8a), invariant (I8b), terminology (Stage-1I addendum), and TV (TV69) all AGREE | **PASS** |
| C7 | Custody and coverage stay orthogonal (I8b); the cause lives in `revocation_reason`, not in a coverage term | **PASS** |
| C8 | A1 continuous full-participation baseline **8.420833333 kWh** unchanged; no new consensus feature | **PASS** |

Exercised by **TV69** (an adversarial `ACTIVE_HASHING` withdrawal records `revoked` +
`revocation_reason`, not an invented custody value).

## Result

**Result: CUSTODY ENUM AUDIT (Stage 1I): PASS** — `custody_status` takes ONLY a value from the
canonical, closed enum `{original, renewed, reassigned, revoked, expired, abandoned, completed,
superseded_by_template_refresh}`; an adversarial withdrawal is the two-field representation
`custody_status = revoked` + `revocation_reason = adversarial_withdrawal`; no procedure assigns a
custody value outside the enum and `revoked_adversarial_exit` survives only inside prohibition
comments; the Assignment schema (§0.8), the §8a exit path, I8b, the Stage-1I terminology addendum, and
TV69 all agree, with the A1 baseline 8.420833333 kWh unchanged and no new consensus feature.
