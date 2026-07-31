# Stage 1J — Assignment Terminal-Status Audit (J7)

Audits correction **J7**: the assignment `status` enum has ONE canonical terminal disposition per
end-of-life. `SUPERSEDED` is reserved EXCLUSIVELY for atomic same-range renewal; `CLOSED` is the
terminal status for EVERY non-renewal end-of-life. Binds to `STAGE_01_PROTOCOL_PSEUDOCODE.md` §0.8
(`STRUCTURE Assignment`: `status : one of {PENDING, CURRENT, PAUSED, SUPERSEDED, CLOSED}` with the
`J7 CANONICAL TERMINAL STATUS` comment), §7 `EnterLowPowerListen` (`CASE RANGE_EXHAUSTED` /
`CASE ASSIGNMENT_REVOKED` / `CASE ROUND_ACCEPTED OR ROUND_ABORTED`), §8a
`AdversarialParticipationChangeEvent` (`direction = exit`), §0.10 `WakeCompleteEvent`
(wake-failure `CASE PENDING` / `CASE PAUSED`), §12 `RenewAssignment`, §17a `CloseRoundAssignments`,
and §19 `CloseTemplateAssignments`; to `STAGE_01_INVARIANT_CATALOGUE.md` I18a/I18b (assignment-lineage
version invariants, G2) and I8b/I9 (custody / provenance, I-07); and to
`STAGE_01J_SEMANTIC_TEST_VECTORS.md` TV78. This is a specification act on **PoCol** with the idle
policy within PoCol enabled — not a claim of implementation, enforcement, security, fairness, or any
derived property. No new consensus feature is introduced; the eight miner states and the assignment
schema are unchanged, and the A1 baseline (8.420833333 kWh) is untouched.

## 1. The corrected-away problem

An earlier reading admitted an ambiguous "CLOSE/SUPERSEDE assignment" operation that conflated two
DISTINCT terminal statuses. `SUPERSEDED` — whose only legitimate meaning is "an older version was
displaced by a newer `CURRENT` version on the SAME lineage" — was liable to be reused for terminations
that publish NO successor version (revocation, adversarial withdrawal, abandonment). That conflation
would leave a lineage with a `SUPERSEDED` head but no `CURRENT` successor, an object indistinguishable
from a real renewal yet with no live head — an unauditable state that defeats the I18a/I18b
head-count reasoning.

## 2. The correction

J7 fixes ONE canonical terminal status per case (§0.8 `STRUCTURE Assignment`, verbatim comment):

- **`SUPERSEDED` is renewal-only.** It is set exclusively by atomic same-range renewal, where a new
  `CURRENT` version is published on the SAME `lineage_id` in the SAME step (`RenewAssignment`, F7/G2;
  I18b). The lineage stays OPEN with exactly one live head (the new `CURRENT`).
- **`CLOSED` is the terminal status for EVERY non-renewal end-of-life:** revocation, adversarial
  withdrawal, abandonment, wake failure, assignment cancellation, round closure, template closure,
  and exhaustion completion. A `CLOSED` lineage has ZERO live heads (I18b).
- There is **no** ambiguous "CLOSE/SUPERSEDE" operation: a version is either **renewed** (old →
  `SUPERSEDED`, new → `CURRENT`) or **terminated** (→ `CLOSED`). The two are disjoint.

For an adversarial withdrawal specifically (§8a exit): `status(X) <- CLOSED`,
`custody_status(range(X)) <- revoked`, `revocation_reason(X) <- adversarial_withdrawal` (I-07
two-field). The lineage of `X` then shows ZERO live heads (I18b).

## 3. End-of-life event → resulting status

| End-of-life event | Resulting status | Where in the spec | I18b live-head outcome |
|---|---|---|---|
| Same-range renewal | **SUPERSEDED** (+ new `CURRENT`) | §12 `RenewAssignment`: `SET status(old_assignment) <- SUPERSEDED` + `SET status(V2) <- CURRENT`, same `lineage_id` | lineage stays OPEN; the new `CURRENT` is the unique live head |
| Revocation | **CLOSED** | §7 `EnterLowPowerListen` `CASE ASSIGNMENT_REVOKED`: `SET status(assignment_ref) <- CLOSED`; `custody_status <- revoked`; `revocation_reason <- assignment_revoked` | zero live heads |
| Adversarial withdrawal | **CLOSED** (+ `custody_status = revoked`, `revocation_reason = adversarial_withdrawal`) | §8a `AdversarialParticipationChangeEvent` (exit): `SET status(X) <- CLOSED`; `custody_status(range(X)) <- revoked`; `revocation_reason(X) <- adversarial_withdrawal`; departs via T11 | zero live heads |
| Abandonment (wake-failure disposition, fresh `PENDING`) | **CLOSED** (`custody_status = abandoned`) | §0.10 `WakeCompleteEvent` `CASE PENDING`: `CLOSE target_assignment (status PENDING -> CLOSED)`; `custody_status <- abandoned` | zero live heads |
| Wake failure (`PAUSED` resume) | **CLOSED** (`custody_status = abandoned`, `disposition = resume_wake_failed`) | §0.10 `WakeCompleteEvent` `CASE PAUSED`: `CLOSE/ABANDON target_assignment (status PAUSED -> CLOSED, disposition = resume_wake_failed)` | zero live heads |
| Assignment cancellation (bound `PENDING` un-activated at `WAKING`) | **CLOSED** | §17a `CloseRoundAssignments` `CASE WAKING`: cancel `WakeCompleteEvent`, `CLOSE X as round-ended`, T12; §19 `CloseTemplateAssignments` `CASE WAKING` (same) | zero live heads |
| Round closure | **CLOSED** | §7 `EnterLowPowerListen` `CASE ROUND_ACCEPTED OR ROUND_ABORTED`: `SET status(assignment_ref) <- CLOSED` (invoked by §17a `CloseRoundAssignments`) | zero live heads |
| Template closure | **CLOSED** (`custody_status = superseded_by_template_refresh`) | §19 `CloseTemplateAssignments`: `ACTIVE_HASHING` → `EnterLowPowerListen ASSIGNMENT_REVOKED` (→ CLOSED); `PAUSED` PATH-B → `CLOSE X`; custody marker `superseded_by_template_refresh` | zero live heads |
| Exhaustion completion | **CLOSED** (`custody_status = completed`) | §7 `EnterLowPowerListen` `CASE RANGE_EXHAUSTED`: `SET status(assignment_ref) <- CLOSED` ("exhaustion completion is CLOSED (not SUPERSEDED)") | zero live heads |

Note: `superseded_by_template_refresh` is a **custody** marker (I8b lineage history), NOT the version
`status`; the version `status` on template closure is `CLOSED`. Likewise `abandoned`, `revoked`,
`completed` are custody values orthogonal to the `CLOSED` version status (I8b).

## 4. Argument: SUPERSEDED never terminates; every CLOSED lineage has zero live heads

Exactly ONE procedure writes `SUPERSEDED`: §12 `RenewAssignment`, and it does so ATOMICALLY together
with publishing a new `CURRENT` on the SAME `lineage_id` (`SET status(old_assignment) <- SUPERSEDED`;
`SET status(V2) <- CURRENT`; `ASSERT exactly one version with status = CURRENT in lineage_id(V2)`).
`RenewAssignment` is the SOLE renewal path (F7/G2); `CreatePendingAssignment` opens only
ORIGINAL/REASSIGNED FRESH lineages and never renews. Therefore `SUPERSEDED` can appear ONLY when a
successor `CURRENT` exists — never as a termination, and never leaving a lineage headless.

Every termination writes `CLOSED`: `EnterLowPowerListen` (`RANGE_EXHAUSTED`, `ASSIGNMENT_REVOKED`,
`ROUND_ACCEPTED`/`ROUND_ABORTED`), the §8a exit path, the §0.10 wake-failure paths, and the WAKING
cancellations under §17a/§19. None of these publishes a successor version. By I18b, a CLOSED lineage
has ZERO live heads in `{PENDING, CURRENT, PAUSED}`. Hence revocation and adversarial-withdrawal
lineages close cleanly: the CURRENT head is closed explicitly, no live head survives, and no phantom
`SUPERSEDED`-without-successor state can arise.

## 5. Pseudocode verification (former "CLOSE/SUPERSEDE" now explicit `SET status <- CLOSED`)

| Site | Text in `STAGE_01_PROTOCOL_PSEUDOCODE.md` | Verdict |
|---|---|---|
| §7 `EnterLowPowerListen` `CASE ASSIGNMENT_REVOKED` | `SET status(assignment_ref) <- CLOSED   # J7: revocation is CLOSED, never SUPERSEDED` | explicit CLOSED |
| §8a `AdversarialParticipationChangeEvent` (exit) | `SET status(X) <- CLOSED   # no live CURRENT head remains (I18a/I18b)`; comment "adversarial withdrawal TERMINATES the version -- status = CLOSED (never SUPERSEDED; SUPERSEDED is renewal-only)" | explicit CLOSED |
| §7 `EnterLowPowerListen` `CASE RANGE_EXHAUSTED` | `SET status(assignment_ref) <- CLOSED   # J7: exhaustion completion is CLOSED (not SUPERSEDED)` | explicit CLOSED |
| §7 `EnterLowPowerListen` `CASE ROUND_ACCEPTED OR ROUND_ABORTED` | `SET status(assignment_ref) <- CLOSED   # J7: round closure is CLOSED (not SUPERSEDED)` | explicit CLOSED |
| §0.10 `WakeCompleteEvent` `CASE PENDING` / `CASE PAUSED` | `CLOSE target_assignment (status PENDING -> CLOSED)` / `CLOSE/ABANDON target_assignment (status PAUSED -> CLOSED, disposition = resume_wake_failed)` | explicit CLOSED |
| §12 `RenewAssignment` (the ONLY SUPERSEDED writer) | `SET status(old_assignment) <- SUPERSEDED` atomically with `SET status(V2) <- CURRENT` on the same `lineage_id` | SUPERSEDED renewal-only |

No procedure performs an ambiguous "CLOSE/SUPERSEDE" or writes `SUPERSEDED` on any non-renewal path.

## 6. Worked example (TV78 — adversarial withdrawal → CLOSED, never SUPERSEDED, zero live heads)

**Preconditions.** An adversarial miner is `ACTIVE_HASHING` on `CURRENT` version `X`;
`AdversarialParticipationChangeEvent(exit)` fires (§8a).

**Trace.** The exit preserves the accepted searched prefix, exposes only the accepted unsearched
suffix (C4), records `withdrawal_reason(X) <- adversarial_withdrawal` (I9), sets
`custody_status(range(X)) <- revoked` and `revocation_reason(X) <- adversarial_withdrawal` (I-07),
cancels `X`'s pending `HashWorkEvent` units, and sets `status(X) <- CLOSED` — NOT `SUPERSEDED`, which
is renewal-only — then departs `ACTIVE_HASHING -> OFFLINE` via T11 through `ApplyMinerStateTransition`.

**Expected.** `status(X) = CLOSED` (never `SUPERSEDED`); `custody_status = revoked`;
`revocation_reason = adversarial_withdrawal`; the lineage of `X` has ZERO live heads (I18b). Matches
TV78 (Reqs J7, I-07, I18a, I18b).

## 7. Acceptance-style PASS checklist

| # | Check | Result |
|--:|-------|--------|
| C1 | `SUPERSEDED` is renewal-ONLY — written exclusively by `RenewAssignment`, atomically with a new `CURRENT` on the same `lineage_id` | **PASS** |
| C2 | `CLOSED` is the terminal status for EVERY termination (revocation, adversarial withdrawal, abandonment, wake failure, assignment cancellation, round closure, template closure, exhaustion completion) | **PASS** |
| C3 | Adversarial withdrawal uses the two-field custody representation: `custody_status = revoked` + `revocation_reason = adversarial_withdrawal` (I-07) | **PASS** |
| C4 | Every CLOSED lineage has ZERO live heads in `{PENDING, CURRENT, PAUSED}` (I18b); revocation/withdrawal lineages close cleanly | **PASS** |
| C5 | No ambiguous "CLOSE/SUPERSEDE" operation remains; each former site is an explicit `SET status <- CLOSED` (§7 `ASSIGNMENT_REVOKED`, §8a exit, §7 `RANGE_EXHAUSTED`, §7 `ROUND_ACCEPTED`/`ROUND_ABORTED`, §0.10 wake-failure) | **PASS** |
| C6 | Schema (§0.8), procedures (§7/§8a/§0.10/§12/§17a/§19), invariants (I18a/I18b, I8b), and TV78 all AGREE | **PASS** |
| C7 | A1 continuous full-participation baseline **8.420833333 kWh** unchanged; no new consensus feature | **PASS** |

Exercised by **TV78** (an adversarial `ACTIVE_HASHING` withdrawal closes as `CLOSED`, never
`SUPERSEDED`, with zero live heads).

## Result

**Result: ASSIGNMENT TERMINAL STATUS AUDIT (Stage 1J): PASS** — `SUPERSEDED` is used ONLY for atomic
same-range renewal (a new `CURRENT` published on the same lineage in the same step, `RenewAssignment`,
G2/I18b), and `CLOSED` is the single terminal status for every non-renewal end-of-life — revocation,
adversarial withdrawal, abandonment, wake failure, assignment cancellation, round closure, template
closure, and exhaustion completion; an adversarial withdrawal closes with `status = CLOSED`,
`custody_status = revoked`, `revocation_reason = adversarial_withdrawal` (I-07) and zero live heads
(I18b); no ambiguous "CLOSE/SUPERSEDE" operation remains, and the §0.8 schema, the §7/§8a/§0.10/§12
procedures, I18a/I18b, and TV78 all agree, with the A1 baseline 8.420833333 kWh unchanged and no new
consensus feature.
