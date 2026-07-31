# Stage 1 — Range Lease and Reassignment

**Document status:** Stage-1 specification-only. This document DEFINES the range-lease and
reassignment structure of the idle policy within PoCol. It does NOT claim that any mechanism
described here is implemented, validated, secure, fair, or incentive-compatible. Stage 1
SPECIFIES; it does NOT demonstrate any property of what it specifies. All quantities are
modeled quantities under the normative energy model of `STAGE_01_PROTOCOL_SCOPE.md`.

**Naming rule (binding).** The algorithm is ALWAYS **PoCol**. The mechanism specified here is
part of **the idle policy within PoCol** — an operating policy that lives inside PoCol, not a
new algorithm, variant, or fork. The prohibited strings "PoCol-E", "Energy-Aware PoCol", and
"Enhanced PoCol" MUST NOT appear.

**Baseline (must not be contradicted).** Nonce-domain partitioning ALONE does not reduce total
fixed-horizon energy (invariant A1). Leasing and reassignment are *scheduling and coordination*
devices: they organise which miner searches which region of the nonce domain and permit
coverage to be maintained without continuous full participation. Any energy reduction they
enable arises ONLY through reduced active power-time (miners moved to `LOW_POWER_LISTEN`, held
in `RESERVE`, or removed from active hashing), NEVER through partitioning itself.

---

## 1. Purpose and position

The nonce domain of a round is partitioned into disjoint ranges (Protocol Scope, Section A,
item 3). Under the idle policy an assignment of a range is granted as a **time-bounded lease**
rather than an indefinite grant. Leasing makes range custody explicit and revocable, which is
the precondition for reassigning the **unsearched** coverage of a miner that abandons,
departs, or is held in reserve — and therefore the precondition for reducing active
participation without leaving regions of the nonce domain permanently unsearched.
(Exhaustion is not among these reasons: a fully exhausted range is complete, not reassigned;
see Section 5.)

This document specifies the lifecycle of a lease and the provenance rules that make
reassignment auditable. It defines the coverage-state partition (I8a), the orthogonal
custody/provenance model (I8b), the provenance invariant (I9), and the rules governing whether
previously searched positions may be searched again. It does NOT specify reward or penalty values
(see `STAGE_01_REWARD_PENALTY_INTERFACE.md`), nor the progress-verification interface itself (see
`STAGE_01_PROGRESS_VERIFICATION_ABSTRACTION.md`).

---

## 2. The Assignment object

A lease is represented by an **Assignment object**. Its fields are fixed for Stage 1:

| Field | Meaning |
|---|---|
| `RoundID` | The round the assignment belongs to. |
| `TemplateID` | The immutable block template the assigned work targets. |
| `AssignmentID` | Stable unique identifier of this assignment instance. |
| `MinerID` | The miner holding the lease. |
| `range_start` | First nonce position of the leased range (inclusive). |
| `range_end` | Last nonce position of the leased range (inclusive). |
| `range_size` | Count of positions in `[range_start, range_end]`; equals `range_end − range_start + 1`. |
| `lease_start` | Time at which the lease becomes active. |
| `lease_expiry` | Time after which the lease is no longer valid unless renewed. |
| `assignment_version` | Monotonic version counter for this range's assignment lineage. |
| `previous_assignment_reference` | The `AssignmentID` this assignment supersedes, or null for an original assignment. |
| `signature/authentication` | Authentication binding the assignment to the assigning authority so a miner can verify custody. |

An Assignment object is well-formed only if `range_start ≤ range_end`, `range_size` equals the
implied count, `lease_start < lease_expiry`, and `RoundID`/`TemplateID` reference the round's
committed template.

---

## 3. Lease lifecycle

### 3.1 Lease start

A lease **starts** when an Assignment object with a fresh `AssignmentID` is issued to a
`MinerID` for a disjoint range and becomes active at `lease_start`. From `lease_start` the
holder is the sole miner sanctioned to search that range for the referenced `RoundID` and
`TemplateID`. Custody is exclusive: at any instant at most one active (non-superseded) lease may
cover any given nonce position for a given `(RoundID, TemplateID)`.

### 3.2 Lease expiry

A lease **expires** at `lease_expiry`. On expiry the range is no longer under the holder's
sanctioned custody. An expired range is eligible for renewal (3.3), reclamation, or
reassignment (Section 5). Expiry does not by itself assert anything about how much of the range
was searched — that is recorded separately by progress checkpoints (Section 4). Expiry converts
custody from "held" to "reclaimable"; it never silently deletes accounting for the range.

### 3.3 Renewal

**Renewal** extends custody of the same range to the same holder past the original
`lease_expiry`. A renewal is issued as a new Assignment object with:

- the SAME `range_start`, `range_end`, `range_size`, `RoundID`, `TemplateID`, and `MinerID`;
- a fresh `AssignmentID`;
- `assignment_version` incremented by one;
- `previous_assignment_reference` set to the superseded `AssignmentID`;
- a later `lease_expiry`.

Renewal is a provenance-preserving operation: the searched prefix accumulated under the prior
lease (Section 4) carries forward, so a renewed holder is not required to re-search positions it
has already searched. Renewal to the same holder is distinguished from reassignment (Section 5)
only by whether `MinerID` changes; both follow the provenance rules of Section 6.

---

## 4. Progress checkpoints, searched prefix, unsearched suffix

### 4.1 Progress checkpoints

A holder searches its leased range and may emit **progress checkpoints** attesting how far the
range has been searched. A progress checkpoint is treated ONLY as a *modeled
progress-verification abstraction*; it is NOT a cryptographic proof that every position up to
the checkpoint was actually hashed. The interface, its audit probability, and its detection
semantics are specified in `STAGE_01_PROGRESS_VERIFICATION_ABSTRACTION.md`; this document uses
only the *frontier* a checkpoint reports.

### 4.2 Searched prefix and unsearched suffix

For a range searched in monotonic order from `range_start`, the last checkpointed frontier
partitions the range into two contiguous parts:

- **Searched prefix** — the positions from `range_start` up to and including the reported
  frontier. These are the positions the holder claims to have searched (subject to audit; the
  claim is modeled, not proven).
- **Unsearched suffix** — the positions from just after the frontier to `range_end`. These are
  the positions still to be searched under the current lease.
- **Reported vs. accepted frontier.** The **reported frontier** is a claim; it is promoted to
  the **accepted frontier** (`accepted_frontier`) only by adjudication (a `RangeExhaust`
  honest-completion or a passed audit). Reassignment (Section 5) operates on the **accepted
  unsearched suffix** measured from `accepted_frontier`, never on an unadjudicated reported claim.

By construction, `|searched prefix| + |unsearched suffix| = range_size` for a live lease.
Stage 1 models search as advancing a single monotonic frontier per lease; non-contiguous search
orders are out of scope at Stage 1 and would require an explicit covered-set representation
rather than a single frontier.

---

## 5. Abandonment, revocation, reassignment

### 5.1 Abandonment

**Abandonment** occurs when a holder ceases to make sanctioned progress on a live lease
**before completing it** — for example on transition to `OFFLINE` or departure. On
abandonment the range's searched prefix (as last checkpointed) is retained for accounting, and
the **accepted unsearched suffix** (`[accepted_frontier + 1, range_end]`) becomes eligible for
reassignment. Abandonment is holder-originated (the
holder stops); revocation (5.2) is authority-originated. Abandonment is distinct from
**exhaustion**: a holder that fully searches its range reaches `EXHAUSTED_PENDING` with the
range **completed** (Section 5.4), which is not abandonment and does not make the range
reassignable.

### 5.2 Revocation

**Revocation** is an authority-originated withdrawal of a live lease before `lease_expiry` — for
example on lease-policy change, security-recovery action, or detected misbehaviour. Revocation
supersedes the current Assignment object and marks the range reclaimable exactly as expiry does,
with the last checkpointed searched prefix retained.

### 5.3 Reassignment

**Reassignment** issues a new Assignment object for the **accepted unsearched suffix** of a range
(which may be the whole range when no accepted searched positions exist) to a DIFFERENT `MinerID`.
Reassignment is the mechanism by which unsearched coverage of the nonce domain is maintained
without requiring the original holder to continue. Only an **accepted unsearched suffix** may be
reassigned; a searched prefix is never reassigned, and a **completed / exhausted** range is
never reassigned (Section 5.4).

**Permitted reassignment reasons** are EXACTLY:

```
{ lease_expiry, abandonment, revocation, departure, conflict, security_recovery }
```

Exhaustion is NOT a reassignment reason and MUST NOT appear in any reassignment-reason set.

**Accepted unsearched suffix (the exact reassignable region).** For every one of the permitted
reasons — `lease_expiry`, `abandonment`, `revocation`, `departure`, `conflict`,
`security_recovery` — reassignment transfers ONLY the accepted unsearched suffix, computed from
the accepted frontier:

```
suffix_start        = accepted_frontier + 1
reassignable_suffix = [suffix_start, range_end]
```

- If no accepted searched positions exist, the suffix MAY be the whole range.
- If `accepted_frontier = range_end`, the range is **completed** and **no suffix exists**
  (nothing is reassignable; Section 5.4).
- `RangeReassign` receives the **exact** unsearched suffix `[suffix_start, range_end]`, never the
  original full range and never a searched prefix.

The reassigned Assignment object:

- references the accepted unsearched suffix being transferred;
- carries a fresh `AssignmentID` and the new holder's `MinerID`;
- increments `assignment_version`;
- sets `previous_assignment_reference` to the superseded `AssignmentID` (Section 6);
- carries its own `lease_start`/`lease_expiry`.

Reassignment of only the accepted unsearched suffix narrows `range_start` to just after the
accepted frontier (`accepted_frontier + 1`) so that the new lease does not re-cover the prior
searched prefix (subject to Section 7).

### 5.4 Completed / exhausted ranges are not reassignable

A range that its holder **fully exhausts** — its entire assigned range searched with no valid
solution found (PATH A, reaching `EXHAUSTED_PENDING` with the range completed) — is
**complete**, not reclaimable. A completed / exhausted range:

- has `custody_status = completed` (Section 8.3) and `coverage_state = searched`;
- is **NOT** released to the reassignable pool;
- is **NOT** marked `inactive_unsearched`;
- is **NOT** reassigned under the same `TemplateID`.

A **template refresh** does not reassign a completed range, and is **not** a reassignment event
at all. On `TemplateRefresh` the protocol:

- **closes all assignments under the old `TemplateID`** and preserves their historical coverage
  and provenance (the old-domain accounting still reconciles under I8a/I9);
- **creates a new immutable template and a fresh `TemplateID`** (a new candidate-identity
  domain);
- **creates new ORIGINAL assignments** over the new domain with
  `previous_assignment_reference = null`;
- does **NOT** call `RangeReassign` for the old ranges;
- does **NOT** rebind old assignments to the new domain;
- **keeps difficulty fixed** (`D(t) = D_0`; I12).

Issuing new original assignments under the new `TemplateID` is not a reassignment of the
completed (or any) old range. Only genuinely **unsearched** coverage — an accepted unsearched
suffix left by expiry, abandonment, revocation, departure, conflict, or security_recovery — is
ever reassigned.

---

## 6. Provenance preservation (I9)

**Invariant I9 — full provenance for every reassignment.** Every reassignment (and every
renewal) MUST carry complete provenance linking it to the assignment it supersedes. Concretely:

- `previous_assignment_reference` MUST be set to the `AssignmentID` of the immediately
  superseded assignment (null only for an original, never for a reassignment or renewal).
- `assignment_version` MUST be strictly greater than the superseded assignment's version.
- `RoundID` and `TemplateID` MUST be preserved unchanged across the lineage; a change of
  template requires a new original assignment under the new `TemplateID`, not a reassignment.

The chain of `previous_assignment_reference` links forms an auditable lineage from any current
Assignment object back to the original assignment of its range. No range may change custody
without appending to this lineage. Provenance makes reassignment reconstructable: given the
lineage, the searched prefix contributed under each successive holder is attributable, which is
required for the reconciliation of Section 8 and for the reward/penalty interface's
reassignment-reward and abandonment-penalty terms.

---

## 7. Re-searching previously searched positions

Whether previously searched positions may be searched again is governed by the following rules;
they exist so that aggregate progress accounting cannot be inflated or corrupted by re-searching.

**MAY be re-searched (permitted):**

1. On a **new TemplateID** (template refresh). A searched prefix is defined relative to a
   specific `(RoundID, TemplateID)`. When the template changes, all prior search is stale;
   positions are searched afresh against the new template and no prior prefix carries over.
2. When a prior searched prefix **cannot be relied upon** — for example a checkpoint failed
   audit, or provenance for the prior prefix is incomplete (I9 unsatisfied). In that case the
   affected positions are treated as unsearched and MAY be re-searched, and the unreliable prior
   claim MUST NOT be counted toward searched coverage.

**MUST NOT be re-searched as counted progress (prohibited double-counting):**

3. Within the **same `(RoundID, TemplateID)`**, positions in a *reliable* searched prefix
   inherited across renewal or suffix-only reassignment MUST NOT be re-searched and counted a
   second time. Re-searching them wastes active power-time (contrary to the idle policy's
   purpose) and, if counted, would double-count coverage.

Re-searching for redundancy or verification is not forbidden as an activity, but redundant
searches of an already-counted reliable prefix MUST NOT increase the searched total. Searched
coverage is counted at most once per position per `(RoundID, TemplateID)`.

---

## 8. Coverage-state partition (I8a) and custody/provenance model (I8b)

Assignment accounting uses **two orthogonal models** of every position: a **coverage state**
(how far the position has been searched) and a **custody status** (the lineage/event history of
the position's leases). They are reconciled **separately**; a custody status is NOT an additive
term in the coverage equation.

### 8.1 Coverage-state partition (I8a)

**Invariant I8a — coverage states partition the assigned domain.** For every range within a
`(RoundID, TemplateID)`, and in aggregate across the round's assigned domain, the coverage
accounting MUST reconcile exactly:

```
accepted_searched + active_unsearched + inactive_unsearched = assigned_domain
```

where, for the scope being reconciled:

- **assigned_domain** — total positions placed under assignment (the union of leased ranges);
- **searched** — positions counted as searched under reliable, provenance-complete checkpoints
  (counted at most once per position per template, per Section 7);
- **active_unsearched** — positions under a **live** lease not yet within a searched prefix;
- **inactive_unsearched** — positions not currently under any live lease and not yet searched
  (their custody has lapsed — expired, abandoned, or revoked — or they await (re)assignment).
  A **completed / exhausted** range is NOT `inactive_unsearched`: its positions are `searched`
  and its custody status is `completed` (Sections 5.4, 8.3).

The three coverage categories MUST be **pairwise disjoint** and **collectively exhaustive** over
`assigned_domain` at every reconciliation point. A position is in exactly one coverage state at
any instant.

### 8.2 No gap or overlap may be hidden by aggregate counts

The equality of I8a is necessary but NOT sufficient. Reconciliation MUST hold **positionally**,
not merely in aggregate:

- **No hidden gap.** No position within `assigned_domain` may be absent from all three coverage
  categories. A position that is neither searched, nor under a live lease (`active_unsearched`),
  nor `inactive_unsearched` is an accounting gap and is prohibited — even if the aggregate totals
  happen to sum correctly.
- **No hidden overlap.** No position may be counted in more than one coverage category, and no
  position may be under two live leases at once (custody is exclusive, Section 3.1). In particular
  a reassigned suffix MUST NOT remain counted as `active_unsearched` under the superseded lease.

Because compensating errors can make aggregate sums balance while a gap in one region is masked
by an overlap in another, I8a is enforced against the position-level partition of each range —
via `range_start`/`range_end` boundaries and the provenance lineage — and not against totals
alone. Aggregate counts are a summary of the positional partition, never a substitute for it.

### 8.3 Custody/provenance model (I8b), orthogonal to coverage

**Invariant I8b — custody/provenance is orthogonal to coverage.** Independently of its coverage
state, each assignment (and hence each position it covers) carries a custody/lineage status in:

```
{original, renewed, reassigned, revoked, expired, abandoned, completed}
```

- **original** — the first assignment of the range in its lineage (`previous_assignment_reference
  = null`);
- **renewed** — custody extended to the **same** holder past `lease_expiry` (Section 3.3);
- **reassigned** — custody transferred to a **different** holder (Section 5.3);
- **revoked** — custody withdrawn by the authority before `lease_expiry` (Section 5.2);
- **expired** — custody lapsed at `lease_expiry` without renewal (Section 3.2);
- **abandoned** — custody relinquished by the holder ceasing sanctioned progress (Section 5.1);
- **completed** — the range was fully exhausted by its holder (PATH A; Section 5.4). A
  `completed` range's coverage state is `searched`; it is not released to the reassignable
  pool, not marked `inactive_unsearched`, and not reassigned under the same `TemplateID`.

These are custody/lineage properties and **MUST NOT** appear as additive terms in the coverage
equation of I8a. In particular, **`reassigned` is NOT a coverage term**: a reassigned position
still has an **independent coverage state** (`searched`, `active_unsearched`, or
`inactive_unsearched`). For example, a position searched under a prior holder whose custody is
now `reassigned` to a successor remains `searched` in the coverage partition; a position whose
unsearched suffix is `reassigned` to a live successor lease is `active_unsearched`. Custody
explains *who holds (or held) the lease and why custody changed*; coverage explains *how much of
the position has been searched*. The two models are reconciled separately and are never summed
together.

---

## 9. Referenced identifiers

- **Miner states:** `REGISTERED`, `RESERVE`, `ACTIVE_HASHING`, `EXHAUSTED_PENDING`,
  `LOW_POWER_LISTEN`, `WAKING`, `OFFLINE`, `DISQUALIFIED`.
- **Assignment object fields:** `RoundID`, `TemplateID`, `AssignmentID`, `MinerID`,
  `range_start`, `range_end`, `range_size`, `lease_start`, `lease_expiry`, `assignment_version`,
  `previous_assignment_reference`, `signature/authentication`.
- **Invariants used here:** **I8a** (coverage states partition the assigned domain:
  accepted_searched + active_unsearched + inactive_unsearched = assigned_domain, positionally with no
  hidden gap or overlap); **I8b** (custody/provenance model
  `{original, renewed, reassigned, revoked, expired, abandoned, completed}`, orthogonal to
  coverage — a reassigned position keeps an independent coverage state, `reassigned` is never
  an additive coverage term, and a `completed`/exhausted range is `searched` in coverage and
  not reassignable under the same `TemplateID`); **I9** (every reassignment has full
  provenance).
- **Related documents:** `STAGE_01_PROTOCOL_SCOPE.md`,
  `STAGE_01_PROGRESS_VERIFICATION_ABSTRACTION.md`, `STAGE_01_EARLY_STOP_CERTIFICATE.md`,
  `STAGE_01_REWARD_PENALTY_INTERFACE.md`.

Nothing in this document claims that leasing or reassignment is implemented, secure, fair, or
incentive-compatible. Stage 1 specifies the structure only.
