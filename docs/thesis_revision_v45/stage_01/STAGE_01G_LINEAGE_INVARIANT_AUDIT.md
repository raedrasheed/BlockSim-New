# Stage 1G — Lineage-Invariant Audit (G2)

Audits correction **G2**: the impossible Stage-1F invariant I18 ("exactly one CURRENT per lineage
at every instant") is replaced by the consistent pair **I18a / I18b**. Binds to
`STAGE_01_PROTOCOL_PSEUDOCODE.md` §0.5 (F7/G2), §0.8 data model, `RenewAssignment`,
`CreatePendingAssignment`; and `STAGE_01_INVARIANT_CATALOGUE.md` I18a/I18b. Documentation only:
this is a specification act, not a claim of implementation, enforcement, or any derived property.

## 1. The corrected pair (I18a / I18b)

An assignment is an immutable versioned object with a stable `lineage_id` shared by all versions of
one holder-range. The old form was impossible whenever a lineage's unique head is `PENDING` or
`PAUSED`, or after closure — those states legally hold **zero** CURRENT versions.

- **I18a (at-most-one CURRENT).** For each `lineage_id`,
  `count(versions with status = CURRENT) <= 1` at all observable times. **Zero CURRENT is legal.**
- **I18b (unique live head).** Every OPEN `lineage_id` has EXACTLY ONE live head in
  `{PENDING, CURRENT, PAUSED}`; a CLOSED lineage has ZERO live heads.
- **Atomic renewal.** A same-range renewal is linearised at `renewal_time`: the old CURRENT version
  becomes `SUPERSEDED` and the new version becomes `CURRENT` in ONE step, so no observer ever sees
  two CURRENT versions in the lineage.

## 2. Lineage-status lifecycle

| Step | Head status | count(CURRENT) | live heads | Zero-CURRENT legal? |
|------|-------------|:--------------:|:----------:|:-------------------:|
| Open (PENDING) | `PENDING` | 0 | 1 | yes (head not yet activated) |
| Activate | `CURRENT` | 1 | 1 | — |
| Pause (VALID_SOLUTION_VERIFIED) | `PAUSED` | 0 | 1 | yes (paused head) |
| Resume | `CURRENT` | 1 | 1 | — |
| … renew (atomic swap) | `CURRENT` (new version) | 1 | 1 | — |
| Close (round end / abandon) | `CLOSED` | 0 | 0 | yes (closed lineage) |

`PENDING`, `PAUSED`, and `CLOSED` all satisfy I18a with zero CURRENT versions; only `CURRENT`
carries the single CURRENT version. At every step exactly one live head exists until closure (I18b).

## 3. Renewal audit (RenewAssignment — sole renewal path)

`RenewAssignment(old_assignment, t)` is the SOLE renewal path (F7/G2). It:

- CREATEs a NEW version `V2` on the SAME `lineage_id`, SAME range / holder / `RoundID` / `TemplateID`,
  with `assignment_version + 1` and `assignment_origin = RENEWED`, `custody_status = renewed`;
- COPIES `actual_frontier` / `reported_frontier` / `accepted_frontier` and provenance from the old
  version; sets `previous_assignment_reference = AssignmentID(old_assignment)`;
- ATOMICALLY sets `status(old) = SUPERSEDED` (`superseded_at = t`) and `status(V2) = CURRENT`, then
  ASSERTs exactly one version with `status = CURRENT` in the lineage post-swap;
- performs NO wake cycle — the holder stays `ACTIVE_HASHING` and keeps hashing the same range.

The old version's identity is never mutated in place; it stays immutable and snapshot-resolvable, so
a `SolutionEligibilitySnapshot` taken under it resolves to that exact `SUPERSEDED` version.

## 4. Constructor audit (CreatePendingAssignment)

Under G2, `CreatePendingAssignment` accepts only `assignment_origin ∈ {ORIGINAL, REASSIGNED}` —
`RENEWED` is REMOVED from this constructor. Both cases open a **FRESH** `lineage_id` with
`assignment_version = 1`:

- **ORIGINAL** — a fresh never-assigned range; `previous_assignment_reference = null`,
  `custody_status = original`.
- **REASSIGNED** — an accepted unsearched suffix moved to a (possibly different) holder; it links to
  its source ONLY via `previous_assignment_reference` (cross-lineage I9 provenance). It is NOT a new
  version of the source lineage.

Because a REASSIGNED position starts its own lineage, no lineage ever holds two live heads.
Same-lineage continuity is RENEWAL only, and `RenewAssignment` is the sole path for it; `RENEWED`
can never create a fresh lineage because it is not a case in this constructor.

## 5. Properties

| # | Property | Result |
|--:|----------|--------|
| P1 | I18a holds — at most one CURRENT per lineage | **PASS** — the atomic supersede-and-publish in `RenewAssignment` sets old→SUPERSEDED and new→CURRENT in one linearised step; no observer sees two CURRENT versions |
| P2 | I18b holds — one live head per OPEN lineage, zero after closure | **PASS** — the head progresses PENDING→CURRENT→PAUSED→CURRENT→CLOSED; exactly one live head in `{PENDING, CURRENT, PAUSED}` until closure, zero after |
| P3 | Zero CURRENT is legal during PENDING / PAUSED / CLOSED | **PASS** — the lifecycle table records `count(CURRENT) = 0` at those states; I18a permits it explicitly |
| P4 | Renewal never mutates identity in place; old version stays resolvable | **PASS** — `V2` gets a fresh `AssignmentID`; the old version's fields are untouched (only `status`/`superseded_at` retire it), so a discovery snapshot still resolves it (protects E1 / I2) |
| P5 | REASSIGNED to a different holder is a NEW lineage | **PASS** — `CreatePendingAssignment(REASSIGNED)` opens a fresh `lineage_id` linked only by `previous_assignment_reference`, so no two-live-head situation ever arises |
| P6 | RENEWED removed from the constructor | **PASS** — `CreatePendingAssignment` accepts only `{ORIGINAL, REASSIGNED}` (G2); renewal is exclusively `RenewAssignment` on the source lineage |

## Result

**LINEAGE-INVARIANT AUDIT (G2/I18a/I18b): PASS.** The impossible I18 is replaced by the consistent
pair: I18a bounds each lineage to at most one CURRENT version (zero legal), I18b keeps exactly one
live head per open lineage (zero after closure), and renewal is an atomic supersede-and-publish that
no observer sees as two CURRENT versions. Exercised by TV40 (and TV35 historical).
