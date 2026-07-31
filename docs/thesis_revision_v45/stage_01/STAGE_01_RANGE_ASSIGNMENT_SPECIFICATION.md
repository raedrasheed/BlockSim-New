# Stage 1 — PoCol Range Assignment Specification

**Document status:** Stage-1 specification-only. This document DEFINES the normative
nonce-range **assignment object** for **PoCol** and the rules governing the nonce domain,
allocation, overlap prevention, inactive-miner handling, cancellation, reassignment
provenance, and solution validity. It does NOT claim that any mechanism described here is
implemented, validated, secure, fair, live, or incentive-compatible. Stage 1 SPECIFIES; it
demonstrates no property. No security, fairness, or incentive claim is made anywhere in this
document.

**Naming (binding).** The algorithm is ALWAYS **PoCol**. No suffixed, derivative, or
replacement name (e.g. "PoCol-E", "Energy-Aware PoCol", "Enhanced PoCol") is permitted. The
low-power mechanism is referred to ONLY as **the idle policy within PoCol** — an operating
policy that lives inside PoCol, not a new algorithm, variant, or fork.

**Normative keywords.** MUST, MUST NOT, SHALL, SHALL NOT, SHOULD, and MAY are used in the
RFC-2119 sense. A statement without a normative keyword is descriptive.

**Relationship to the template specification.** Every assignment is defined **relative to one
committed TemplateID** (`STAGE_01_TEMPLATE_SPECIFICATION.md`). An assignment carries meaning
only within its own candidate-identity domain; a `TEMPLATE_REFRESH` opens a new domain in
which prior assignments are void (that document, Section 11).

---

## 1. Purpose

PoCol partitions the nonce domain into **disjoint ranges** and assigns each participating
miner one or more ranges that do not overlap any other miner's ranges for the same committed
template. This document specifies the assignment object that records such a grant and the
exact, deterministic, integer rules by which ranges are allocated, prevented from overlapping
(I1), cancelled, reassigned with provenance (I8b), and used to decide whether a solution is
protocol-valid (I2).

Per the accepted A1 baseline, partitioning ALONE does not reduce total fixed-horizon energy
(8.420833333 kWh at 141 TH/s, 21.5 J/TH, 3031.5 W, 10,000 s). Partitioning organises the
search; any energy reduction claimed for PoCol arises only from reduced **active power-time**
under the idle policy, never from partitioning. This document specifies the partition; it makes
no energy-reduction claim.

---

## 2. The assignment object (normative)

An **assignment** is a record granting a miner authority to search a contiguous nonce range,
under one committed template, for a bounded lease interval. Its normative fields:

| Field | Type | Meaning |
|---|---|---|
| `RoundID` | round identifier | The round this assignment belongs to. Binds the assignment to one round (supports I3 at acceptance). |
| `TemplateID` | template identifier | The committed template (candidate-identity domain) the assignment is valid within. An assignment is meaningless outside its TemplateID. |
| `AssignmentID` | assignment identifier | Unique identifier of this assignment record within `(RoundID, TemplateID)`. |
| `MinerID` | miner identifier | The registered miner granted the range. |
| `range_start` | integer nonce | The starting nonce of the granted range (inclusion rule in Section 4). |
| `range_end` | integer nonce | The ending nonce of the granted range (inclusion rule in Section 4). |
| `range_size` | integer count | The exact count of nonces in the range. A derived integer (Section 4) recorded explicitly so coverage accounting (I8a) never re-derives it from endpoints via floating point. |
| `lease_start` | time | Start of the time-bounded lease during which the grant is active. |
| `lease_expiry` | time | End of the lease; after it the range MAY be reclaimed, renewed, or reassigned (Sections 14, 15). |
| `assignment_version` | integer | Monotonic version of this assignment lineage; incremented on renewal/reassignment so a stale grant cannot be mistaken for the current one. |
| `previous_assignment_reference` | assignment identifier or null | The `AssignmentID` this assignment supersedes (reassignment provenance, I8b); null for an original grant. |
| `signature` / authentication field | authentication token | Authenticates the assignment's issuance under the deployment's fixed authority model. Treated as an authentication field only; Stage 1 makes NO claim that it provides unforgeability, non-repudiation, or any security property. |

**Field-consistency requirements.**

- `range_size` MUST equal the exact integer count of nonces in `[range_start, range_end]`
  under the domain model of Section 3 and the endpoint rule of Section 4. It is recorded, not
  approximated.
- `(RoundID, TemplateID, AssignmentID)` MUST uniquely identify an assignment record.
- An assignment is a **valid current assignment** for a miner when: its `RoundID`/`TemplateID`
  match the round's committed template; the wall-clock time lies in `[lease_start,
  lease_expiry]`; it has not been cancelled (Section 14); and its `assignment_version` is the
  latest in its lineage. Validity is defined precisely so that I1, I2, and I8a/I8b are checkable.
- The `signature`/authentication field authenticates issuance only. Its presence is required by
  the schema; its cryptographic strength is out of scope at Stage 1.

---

## 3. Nonce domain: linear vs. circular models

The nonce domain is the integer set `[0, N)` of size `N` (equivalently the closed integer
interval `[0, N-1]`). Two domain models are specified; a deployment MUST fix exactly one per
committed template and record which model is in force, because endpoint and wrap-around rules
differ between them.

### 3.1 Linear model

The domain is the ordered integer interval `[0, N-1]` with **no wrap-around**. A range is a
contiguous sub-interval `[range_start, range_end]` with `0 ≤ range_start ≤ range_end ≤ N-1`. A
range never crosses the top boundary; the successor of `N-1` does not exist. This is the
default model and the simplest to reconcile for coverage accounting (I8a).

### 3.2 Circular model

The domain is the residue ring of size `N`: nonce arithmetic is modulo `N`, and the successor
of `N-1` is `0`. A range MAY **wrap around** the top boundary — i.e. `range_start` may be
greater than `range_end`, denoting `{range_start, …, N-1, 0, …, range_end}`. The circular
model exists to allow a single contiguous range to straddle the fold, e.g. after
reassignment of a partially searched region near the boundary.

### 3.3 Handling each model

- The domain model is a per-template constant, committed alongside the assignment set for the
  round; all assignments under one TemplateID MUST use the same model.
- **Linear:** `range_start ≤ range_end` always; any grant with `range_start > range_end` is
  invalid.
- **Circular:** a grant with `range_start > range_end` is a wrap range (Section 5); its size
  and overlap tests use modular arithmetic (Sections 4, 5, 12).
- Overlap (I1), size, and coverage accounting (I8a) MUST be computed under the model in force; mixing
  models within one TemplateID is prohibited.

---

## 4. Endpoint inclusion and exact size

Endpoints are treated **inclusively on both ends**: a range `[range_start, range_end]`
contains both `range_start` and `range_end`.

- **Linear model:** `range_size = range_end − range_start + 1`, an exact integer, valid when
  `range_start ≤ range_end`.
- **Circular model, non-wrap** (`range_start ≤ range_end`): identical,
  `range_size = range_end − range_start + 1`.
- **Circular model, wrap** (`range_start > range_end`):
  `range_size = (N − range_start) + (range_end + 1)`, an exact integer counting
  `{range_start … N-1}` then `{0 … range_end}`.

An empty range is represented explicitly (e.g. by a sentinel with `range_size = 0`), never by
an inverted linear interval. The inclusive convention MUST be applied uniformly so that the
disjoint cover of the domain sums exactly: `Σ range_size = N` across a full partition (Section
12), with no off-by-one gap or overlap at boundaries.

---

## 5. Wrap-around rules

- In the **linear model**, wrap-around is prohibited: a range MUST NOT include both `N-1` and
  `0` as adjacent members. A range needing coverage on both sides of the top boundary MUST be
  expressed as two separate assignments.
- In the **circular model**, a single assignment MAY wrap: `range_start > range_end` denotes
  the wrapped set of Section 4. A wrapped range is treated as one contiguous range for
  ownership and validity but is evaluated with modular arithmetic for size (Section 4), overlap
  (Section 12), and membership (Section 16).
- A wrapped range MUST NOT be "double-counted" across the fold: the two arcs it spans are one
  range with one `range_size`, one `AssignmentID`, and one owner.
- Membership test (used by I2, Section 16): a nonce `n` lies in a wrapped range iff
  `n ≥ range_start` **or** `n ≤ range_end`; in a non-wrap range iff
  `range_start ≤ n ≤ range_end`.

---

## 6. Integer arithmetic (exact; no float → count)

All range boundaries, sizes, counts, shares, and apportionment results are **exact integers**.

- `range_start`, `range_end`, `range_size`, and every per-miner allocation are integers.
- A nonce count MUST NEVER be produced by converting a floating-point value to an integer
  (no `float → count`). Where a real-valued quantity is conceptually involved (a proportional
  share, or a power `rate^alpha`), it MUST be handled by exact integer or exact rational
  arithmetic and reduced to counts by integer apportionment (Section 11), not by rounding a
  float.
- Comparisons that decide apportionment (Section 11) and overlap (Section 12) MUST be exact
  integer comparisons.
- `Σ range_size` over a partition MUST equal `N` exactly. Exact integer arithmetic is what
  makes the coverage-accounting invariant I8a (Section 15) reconcile without residue.

---

## 7. Allocation ordering and deterministic tie handling

Allocation is **deterministic**: given the same committed template, the same set of eligible
miners, the same shares, and the same policy parameters, allocation MUST produce the identical
assignment set on every host.

- Eligible miners are placed in a **canonical order** before allocation. The canonical order
  MUST be a total order fixed by the deployment — e.g. ascending `MinerID` — and MUST be
  applied identically everywhere.
- Ranges are laid down in canonical order across the domain from `0` upward (linear) or from a
  fixed committed origin (circular), so that miner *k* in canonical order receives the *k*-th
  contiguous block. This fixes not just how many nonces each miner gets but **which** nonces.
- **Deterministic tie handling:** wherever a choice is otherwise underdetermined — equal
  fractional remainders in apportionment (Section 11), equal shares, or equal eligibility — the
  tie MUST be broken by the canonical order (ascending `MinerID`), never randomly and never by
  arrival order. Ties resolve identically on all hosts.

---

## 8. Equal-range allocation

Equal allocation is **rate-independent**: it partitions the domain by count only, ignoring
hash rate.

- With `n` eligible miners and domain size `N`: compute `base, rem = divmod(N, n)`. In
  canonical order, the first `rem` miners each receive `base + 1` nonces and the remaining
  `n − rem` miners each receive `base` nonces.
- This yields an exact cover (`Σ range_size = N`), disjoint ranges (I1), and is identical for
  any two configurations that differ only in hash-rate distribution.
- Ranges are contiguous and laid down in canonical order (Section 7), so both the size and the
  location of each miner's range are fixed and reproducible.

---

## 9. Hash-rate-weighted allocation

Weighted allocation is **share-driven**: a miner's range count is proportional (via exact
integer apportionment) to its hash-rate share, so faster miners receive proportionally larger
ranges.

- Let `rate_i` be miner *i*'s hash rate and `W = Σ rate_j` over eligible miners. The target
  share is `rate_i / W`; the exact integer count is obtained by largest-remainder apportionment
  of `N` by weights `rate_i` (Section 11), never by rounding `N · rate_i / W` as a float.
- The result is an exact cover with disjoint ranges (I1) and deterministic tie-breaking
  (Section 7).
- Weighted allocation intentionally couples range to rate. It changes **coverage** — which
  miner searches which region — never total fixed-horizon energy (A1); allocation policy is a
  scheduling device, not an energy lever.

---

## 10. Hybrid allocation using the allocation exponent alpha

Hybrid allocation interpolates between equal (Section 8) and hash-rate-weighted (Section 9)
allocation using a single **allocation exponent** `alpha`.

- The per-miner weight is `w_i = rate_i^alpha` for eligible miner *i*.
- `alpha = 0` gives `w_i = rate_i^0 = 1` for all miners → **equal** allocation (Section 8).
- `alpha = 1` gives `w_i = rate_i` → **hash-rate-weighted** allocation (Section 9).
- `0 < alpha < 1` damps the influence of hash rate; `alpha > 1` amplifies it. `alpha` is a
  fixed, published policy parameter of the round, not a per-miner or dynamic quantity.
- **Exactness requirement.** `rate_i^alpha` is in general real-valued and MUST NOT be turned
  into a count by float rounding (Section 6). The deployment MUST fix a published integer
  scaling: derive integer weights `w_i*` from `rate_i^alpha` at a fixed decimal/fixed-point
  precision (the same precision for all miners), then apportion `N` by the integer weights
  `w_i*` using largest-remainder apportionment (Section 11). The scaling and precision are part
  of the fixed policy so that allocation is fully deterministic and reproducible.
- Whatever `alpha`, the outcome is an exact cover, disjoint ranges (I1), and deterministic ties
  (Section 7).

---

## 11. Exact remainder distribution (integer apportionment)

All weighted and hybrid allocations use **largest-remainder (Hamilton) apportionment** carried
out in exact integer arithmetic, so that per-miner counts are integers summing exactly to `N`.

Given integer weights `w_i` (from Section 9 or the scaled weights of Section 10) with
`W = Σ w_j` over eligible miners, and domain size `N`, for each miner *i*:

1. **Floor quota:** `L_i = (N · w_i) // W` (integer division; exact).
2. **Remainder numerator:** `r_i = (N · w_i) mod W` (exact integer; the fractional part scaled
   by `W`, never a float).
3. **Leftover units:** `R = N − Σ_i L_i` (an exact non-negative integer, `0 ≤ R < n`).
4. **Distribute leftover:** grant one extra nonce each to the `R` miners with the largest
   remainder numerators `r_i`. Ties in `r_i` are broken by the canonical order — ascending
   `MinerID` (Section 7) — deterministically.

The result satisfies `Σ_i L_i = N` exactly, every `L_i` is a non-negative integer, and the
outcome is identical on every host. No floating point participates in steps 1–4. This is the
exact remainder distribution referenced by I8a (Section 15): allocated counts reconcile with the
domain size with zero residue.

---

## 12. Prevention of overlap (I1)

**Invariant I1: no two valid active assignments overlap.** For any committed template, the set
of valid current assignments MUST partition the assigned portion of the domain into pairwise
disjoint ranges.

- **Linear model:** ranges `[a1, b1]` and `[a2, b2]` overlap iff `a1 ≤ b2` and `a2 ≤ b1`.
  Allocation MUST produce ranges for which no two valid current assignments satisfy this
  predicate.
- **Circular model:** overlap is tested with modular membership (Section 5): two ranges overlap
  iff their wrapped/non-wrapped member sets intersect. A wrapped range's two arcs are both
  considered.
- Overlap is checked on the set of **valid current assignments** only (Section 2): cancelled
  assignments (Section 14) and superseded lineage versions (Section 15) are excluded, so a
  reassignment that hands a region from one miner to another does not register as an I1
  violation — the prior assignment is no longer valid current at the moment the successor is.
- I1 is a property **per TemplateID**: it constrains assignments within one candidate-identity
  domain. It says nothing across a `TEMPLATE_REFRESH`, where a new domain and a fresh
  assignment set begin.
- Allocation policies (Sections 8–11) are constructed to establish I1 by laying down
  contiguous, non-abutting-then-overlapping ranges in canonical order that exactly cover the
  domain. Any assignment that would violate I1 MUST NOT be issued.

---

## 13. Treatment of inactive miners

A miner that is not actively searching (e.g. in `RESERVE`, `LOW_POWER_LISTEN`, `WAKING`,
`OFFLINE`, `EXHAUSTED_PENDING`, or `DISQUALIFIED`) is handled explicitly so the domain remains
accounted for (I8a):

- A `RESERVE` miner holds no active range and draws no active hashing power; it is not
  allocated a range until promoted to `ACTIVE_HASHING`.
- A range whose owner ceases active search **before completing it** (miner departs, goes
  `OFFLINE`, enters `LOW_POWER_LISTEN` on a paused valid-solution stop, or is `DISQUALIFIED`)
  becomes eligible for cancellation (Section 14) and/or reassignment of its **unsearched
  suffix** (Section 15). Until reassigned, the unsearched region it covered is recorded in the
  coverage accounting as **inactive_unsearched** (unsearched-and-unassigned) rather than
  silently dropped.
- A range that its owner **fully exhausts** (PATH A: own assigned range searched to
  completion via `ACTIVE_HASHING → EXHAUSTED_PENDING`, no valid solution encountered) is
  **complete**, not inactive: its coverage state is `searched` and its custody status is
  `completed` (Section 15). A completed range is **not** returned for reassignment, is **not**
  recorded as `inactive_unsearched`, and is **not** reassignable under the same `TemplateID`.
- Inactive regions MUST appear in the I8a coverage accounting (Section 15) so that
  searched + active_unsearched + inactive_unsearched reconciles to the full domain. An inactive
  miner's former range is never both "assigned to it" and "available for reassignment"
  simultaneously; the assignment lineage (Section 15) records the transition.
- Nothing here claims that inactive-miner handling preserves the security floor or any
  service property; those are out of scope at Stage 1.

---

## 14. Assignment cancellation

An assignment MAY be **cancelled** before its natural completion (before exhaustion or lease
expiry) — e.g. on miner departure, disqualification, lease reclamation, or `TEMPLATE_REFRESH`.

- Cancellation makes the assignment no longer a **valid current assignment** (Section 2):
  after cancellation the miner has no authority to search that range, and a solution it finds
  there is not protocol-valid (I2, Section 16).
- Cancellation MUST be explicit and recorded (with the point of cancellation), so that overlap
  checking (I1) and coverage accounting (I8a) can exclude the cancelled assignment and, where applicable,
  admit a successor.
- Cancellation of an assignment under a committed template does not by itself change the
  committed template or the target; template/target changes occur only through
  `TEMPLATE_REFRESH` under the separately-governed target rule (see
  `STAGE_01_TEMPLATE_SPECIFICATION.md`, Section 14; I12).
- On `TEMPLATE_REFRESH`, all assignments of the prior TemplateID are void with respect to the
  new candidate-identity domain; they need not be individually cancelled to lose validity in
  the new domain, but the coverage accounting for the old domain MUST still reconcile (I8a).

---

## 15. Reassignment provenance (previous_assignment_reference; I8a/I8b)

When an **unsearched suffix** of a range is granted to a new miner after cancellation, lease
expiry, or departure, the successor assignment records its origin via
`previous_assignment_reference`. Exhaustion is **not** a reassignment trigger: a fully
exhausted range is complete (`coverage_state = searched`, `custody_status = completed`) and is
not reassigned under the same `TemplateID` (Section 13).

- `previous_assignment_reference` holds the `AssignmentID` of the assignment being superseded;
  it is null only for an original grant.
- `assignment_version` increments along a lineage, so the latest version is distinguishable
  from stale ones. Only the latest version in a lineage can be a valid current assignment
  (Section 2); this prevents a superseded grant and its successor from both appearing active
  and violating I1 (Section 12).
- **Invariant I8a: coverage states partition the domain.** For each committed template, every
  nonce of the domain MUST be classifiable into exactly one **coverage state**:
  - **searched** — covered by (portions of) assignments whose owners searched them;
  - **active_unsearched** — covered by a valid current (live) assignment but not yet searched;
  - **inactive_unsearched** — not searched and not covered by any valid current assignment
    (Section 13).
  The three coverage states MUST be disjoint and exhaustive, summing exactly to `N` (exact
  integer arithmetic, Section 6).
- **Invariant I8b: custody/provenance, orthogonal to coverage.** Independently of its coverage
  state, each assignment carries a custody status in
  `{original, renewed, reassigned, revoked, expired, abandoned, completed}`. These are
  custody/lineage properties and MUST NOT appear as additive terms in the I8a coverage
  equation: **`reassigned` is a custody status, not a coverage class.** A reassigned position
  still has an independent coverage state (`searched`, `active_unsearched`, or
  `inactive_unsearched`). The `completed` custody status marks a range that its owner fully
  exhausted (PATH A); a completed range's coverage state is `searched`, and — unlike a lapsed
  custody — it is **not** reassignable under the same `TemplateID`.
  `previous_assignment_reference` is the link that lets reassigned regions be traced to their
  origin so the coverage accounting closes without double-counting.
- Provenance is **per TemplateID**: a lineage lives within one candidate-identity domain and
  does not cross a `TEMPLATE_REFRESH`.

Reassignment provenance is what allows coverage of the nonce domain to be maintained under the
idle policy (reserve promotion, lease reclamation) while keeping the domain fully accounted.
No claim is made that reassignment preserves security, liveness, or fairness.

---

## 16. Solution validity rule (I2)

**A solution is protocol-valid ONLY when its nonce belongs to the miner's valid current
assignment.** This is invariant I2.

For an accepted solution with nonce `n` proposed by miner *m*:

1. There MUST exist an assignment `A` with `A.MinerID = m` that is a **valid current
   assignment** (Section 2): matching `RoundID`/`TemplateID`, within `[lease_start,
   lease_expiry]`, not cancelled, and the latest `assignment_version` in its lineage.
2. `n` MUST lie within `A`'s range under the membership test of Section 5 (non-wrap:
   `range_start ≤ n ≤ range_end`; wrap: `n ≥ range_start` or `n ≤ range_end`).
3. The solution MUST match the current RoundID and TemplateID (I3, checked against the
   committed template of `STAGE_01_TEMPLATE_SPECIFICATION.md`).

If any condition fails, the solution is **not protocol-valid**, regardless of whether its
digest satisfies the target. A nonce searched outside a miner's valid current assignment — in
another miner's range, in an inactive region, under a cancelled or superseded assignment, or
under the wrong TemplateID — does not yield a protocol-valid solution. I2 is what turns the
partition from an advisory schedule into a validity condition: acceptance is gated on
assignment membership, not merely on satisfying the target.

Progress toward exhausting an assigned range is handled only via the **modeled
progress-verification abstraction**; it is NOT a cryptographic proof of range exhaustion, and
nothing in this section claims otherwise. Exhaustion has two distinct, non-cryptographic
meanings and MUST NOT be described as "target-verified exhaustion" or as a proof that no valid
solution exists in the range:

- **Honest simulation path:** a range is exhausted by **actual cursor completion** —
  `actual_frontier = range_end`, `actual_positions_evaluated = range_size`,
  `actual_exhaustion = true`, and no valid solution was encountered during the actual
  evaluated sequence.
- **Adversarial simulation path:** exhaustion is an **accepted reported exhaustion under the
  modeled audit abstraction** (`reported_exhaustion` compared with simulator ground truth
  through the modeled audit/detection abstraction), never a cryptographic proof and never
  verified actual exhaustion.

A fully exhausted range is complete: its coverage state is `searched` and its custody status
is `completed` (Section 15); it is not reassignable under the same `TemplateID`.

---

## 17. Scientific consequence

Within the specified model, imposing the assignment object and validity rule (I2) changes
PoCol from **unrestricted independent candidate generation** — every miner free to serialize
and evaluate any candidate header for any nonce — to **assignment-constrained candidate
evaluation**: a solution counts only when its nonce lies in the proposing miner's valid current
assignment under the committed TemplateID.

This is the structural change that makes per-template non-duplication (the H1-relevant
property: no duplicate serialized candidate-header evaluations among honest miners under one
committed template, since candidate-header identity holds iff all fields are equal) well
defined, because each nonce is searched by at most one miner within one candidate-identity
domain (I1, I2). It also makes the domain fully accountable (I8a) under exact integer
arithmetic.

This consequence is a statement **about the specified model only**. It is NOT a claim about the
behaviour of real miners, real hardware, or a deployed network, and it asserts no security,
fairness, liveness, incentive, or energy-reduction property. Consistent with the A1 baseline,
the assignment structure organises the search; it does not, by itself, reduce total
fixed-horizon energy — any energy reduction in PoCol arises only from reduced active power-time
under the idle policy, specified elsewhere and not claimed here.

---

## 18. Reference identifiers used in this document

- **Miner states (8, mutually exclusive):** `REGISTERED`, `RESERVE`, `ACTIVE_HASHING`,
  `EXHAUSTED_PENDING`, `LOW_POWER_LISTEN`, `WAKING`, `OFFLINE`, `DISQUALIFIED`.
- **Round states (10):** `ROUND_INITIALISING`, `TEMPLATE_COMMITMENT`, `ASSIGNMENT`,
  `HASHING`, `SECURITY_RECOVERY`, `SOLUTION_PROPAGATION`, `ROUND_ACCEPTED`, `ROUND_EXHAUSTED`,
  `TEMPLATE_REFRESH`, `ROUND_ABORTED`.
- **Invariants referenced:** I1 (no two valid active assignments overlap; Section 12); I2 (an
  accepted solution lies in the signer's valid current assignment; Section 16); I3 (an accepted
  solution matches the current RoundID and TemplateID; Section 16); I8a (coverage states
  partition the assigned domain: searched + active_unsearched + inactive_unsearched =
  assigned_domain; Section 15); I8b (custody/provenance model
  `{original, renewed, reassigned, revoked, expired, abandoned, completed}`, orthogonal to
  coverage — `reassigned` is custody, not a coverage class; a `completed` (fully exhausted)
  range is `searched` in coverage and not reassignable under the same `TemplateID`;
  Section 15); I12 (difficulty constant in the
  confirmatory protocol; referenced via the target rule of
  `STAGE_01_TEMPLATE_SPECIFICATION.md`).
- **Accounting invariant A1:** continuous full-participation energy is fixed at
  **8.420833333 kWh** (141 TH/s, 21.5 J/TH, 3031.5 W active power, 10,000 s horizon), invariant
  to how the nonce domain is partitioned. Partitioning ALONE does not reduce total fixed-horizon
  energy; reduction arises only from reduced active power-time.

No text in this document claims that PoCol, or the idle policy within PoCol, is implemented,
validated, secure, fair, live, or incentive-compatible.
