# Stage 1 — PoCol Idle Policy Specification

**Document status:** Stage-1 specification-only. This document SPECIFIES the exhaustion
semantics and the low-power transition chain of **the idle policy within PoCol**. It does
NOT claim that the idle policy is implemented, validated, secure, fair, or
incentive-compatible. Nothing here demonstrates a property of PoCol; it defines structure
only. Final numeric parameter values are NOT assigned at Stage 1.

Companion documents: `STAGE_01_PROTOCOL_SCOPE.md` (scope and naming),
`STAGE_01_ENERGY_MODEL_SPECIFICATION.md` (energy accounting),
`STAGE_01_SECURITY_FLOOR_SPECIFICATION.md` (security-floor policy),
`STAGE_01_RESERVE_POLICY_SPECIFICATION.md` (reserve policy),
`STAGE_01_TERMINOLOGY.md` (symbols and terms).

---

## 0. Naming and baseline (binding)

The algorithm is ALWAYS **PoCol**. The mechanism specified here is **the idle policy within
PoCol** — an operating policy inside PoCol, not a new algorithm, variant, or fork. The
strings "PoCol-E", "Energy-Aware PoCol", and "Enhanced PoCol" are prohibited.

Per the accepted baseline, nonce-domain **partitioning alone does NOT reduce total
fixed-horizon energy** (invariant A1: continuous full-participation energy is fixed at
8.420833333 kWh over the 10,000 s horizon at 141 TH/s and 21.5 J/TH, i.e. 3031.5 W active
power). Any energy reduction attributed to PoCol arises ONLY from **reduced active
power-time** (low-power listening, reserve operation, reduced participation) — never from
partitioning itself. The exhaustion semantics below exist to govern *when* a miner is
permitted to stop drawing active hashing power, and therefore to govern *when* a saving is
even eligible to arise.

The eight mutually exclusive miner states are `REGISTERED`, `RESERVE`, `ACTIVE_HASHING`,
`EXHAUSTED_PENDING`, `LOW_POWER_LISTEN`, `WAKING`, `OFFLINE`, `DISQUALIFIED`. Only
`ACTIVE_HASHING` contributes to the active hash rate.

---

## 1. Assignment order and the definition of a candidate position

### 1.1 Assignment and traversal order

Under PoCol, the nonce domain is partitioned into disjoint ranges, and each participating
miner receives one or more ranges bound to the round `TemplateID` (see
`STAGE_01_PROTOCOL_SCOPE.md`, Section A). Within an assignment, the set of nonce values a
miner is responsible for is its set of **candidate positions**.

For exhaustion to be well defined, the traversal must be **totally ordered and
specified in advance**. Let a miner's current assignment for a given `TemplateID` be the
ordered sequence of candidate positions

    C = ⟨c_1, c_2, …, c_N⟩

where the ordering is fixed by the assignment (the *specified traversal order*) and `N` is
the number of candidate positions in the assignment. The traversal order is a property of
the assignment, not a private choice of the miner: two honest miners given the same
assignment would traverse `C` in the same order. This total order is what makes "all
candidate positions have been traversed" a checkable statement rather than an opinion.

### 1.2 Progress marker

A miner's progress within an assignment is summarised by a **progress marker** `p`, the
index of the highest-numbered candidate position that has been searched under the specified
order, with `0 ≤ p ≤ N`. `p = 0` denotes "no position searched"; `p = N` denotes "every
position in the assignment searched". The progress marker is monotone non-decreasing within
a single assignment: it never moves backward while the assignment is held.

---

## 2. EXACT range exhaustion

**Definition (true range exhaustion).** A miner may claim exhaustion of its current
assignment **only after all candidate positions `c_1 … c_N` in that assignment have been
traversed in the specified order** — that is, only when `p = N` — without a valid solution
having been found. Equivalently: true range exhaustion holds for an assignment `A` at
`TemplateID` `t` iff (i) `A` was validly held by the miner at `t`, (ii) every candidate
position in `A` has been searched under the specified traversal order, and (iii) no searched
position satisfied the round target under the committed template.

True range exhaustion is the ONLY condition that legitimately drives the round-level
`ROUND_EXHAUSTED` reasoning from that miner's assignment. Any claim of "finished" that does
not meet all three conditions is one of the *non-exhaustion terminations* in Section 3 and
MUST be classified as such, not as true exhaustion.

Exhaustion is **assignment-scoped and template-scoped**: it is asserted about one
assignment under one `TemplateID`. A template refresh (new `TemplateID`) voids prior
exhaustion state; positions searched under an old template do not count as searched under a
new one.

---

## 3. Termination taxonomy (mutually exclusive classifications)

Every event that causes a miner to stop hashing on an assignment MUST be classified into
exactly one of the following. The classification is load-bearing: only **true range
exhaustion** is eligible to progress toward `LOW_POWER_LISTEN` under the exhaustion path,
and the classifications differ in their energy accounting and their security-floor effect.

| # | Class | Trigger | `p = N` required? | Range coverage disposition |
|---|---|---|---|---|
| 1 | **True range exhaustion** | All candidate positions traversed, no solution | Yes | Range fully searched under this `TemplateID` |
| 2 | **Early abandonment** | Miner stops before `p = N` (voluntary or fault) | No | Range NOT fully searched; uncovered tail remains |
| 3 | **Lease expiry** | `lease_expiry` reached before `p = N` | No | Range NOT fully searched; reclaimable/renewable |
| 4 | **Temporary communication loss** | Miner unreachable but not known departed | Unknown | Coverage state indeterminate; must be treated as unsearched tail until resolved |
| 5 | **Malicious false exhaustion claim** | Miner asserts `p = N` without having traversed all positions | Claimed, not established | Range NOT actually searched; coverage gap masked |
| 6 | **Assignment revocation** | Protocol withdraws the assignment | No (protocol-initiated) | Range returned to the assignable pool |

### 3.1 True range exhaustion (class 1)

As defined in Section 2. `p = N` is established, not merely claimed. This is the only class
that supports the exhaustion-driven low-power path in Section 4.

### 3.2 Early abandonment (class 2)

The miner ceases active hashing with `p < N`. The unsearched tail `⟨c_{p+1}, …, c_N⟩`
remains uncovered under the current `TemplateID`. Early abandonment MUST NOT be recorded as
exhaustion, and the uncovered tail MUST be treated as a coverage gap (candidate for
reassignment; see `STAGE_01_RESERVE_POLICY_SPECIFICATION.md`). Early abandonment does not by
itself entitle the miner to `LOW_POWER_LISTEN` via the exhaustion path.

### 3.3 Lease expiry (class 3)

Where a range is granted as a time-bounded lease (`lease_start`, `lease_expiry`), reaching
`lease_expiry` with `p < N` terminates the assignment by expiry, not by exhaustion. The
range may be reclaimed or renewed. If `p = N` is genuinely established *before*
`lease_expiry`, the termination is class 1 (true exhaustion), not class 3; the lease clock
does not downgrade a completed search.

### 3.4 Temporary communication loss (class 4)

The miner becomes unreachable while its coverage state is unknown. This MUST NOT be
interpreted as exhaustion or as departure. Until the coverage state is reconciled, the
assignment's positions are treated as **unsearched** for coverage and security-floor
purposes (conservative treatment), and the miner is not credited with progress it cannot
substantiate. Resolution either (a) restores the miner with a reconciled progress marker, or
(b) escalates to `OFFLINE` / assignment revocation.

### 3.5 Malicious false exhaustion claim (class 5)

A miner asserts `p = N` (or emits a progress commitment implying `p = N`) that is not
supported by the required evidence in Section 5. This is an adversarial input, not a
termination the protocol should trust. It MUST be handled as an unsubstantiated claim: the
range is treated as NOT searched (its positions remain a coverage gap), the claim is
recorded, and the miner is subject to the security-floor recording discipline (breaches are
recorded, never silently repaired — invariant **I16**) and, where warranted, to
`DISQUALIFIED`. A false exhaustion claim MUST NEVER be allowed to move a miner into
`LOW_POWER_LISTEN`; that is precisely what invariant **I4** forbids (Section 4).

### 3.6 Assignment revocation (class 6)

The protocol withdraws the assignment (for example, to reassign a range for coverage or
security-floor recovery). Revocation is protocol-initiated and does not assert anything
about `p`. The withdrawn range returns to the assignable pool. Revocation is a legitimate
basis for the miner to cease hashing on that range, but it is not exhaustion.

---

## 4. The low-power transition chain

### 4.1 Chain

The exhaustion-driven low-power path is the ordered chain

    ACTIVE_HASHING → EXHAUSTED_PENDING → LOW_POWER_LISTEN

- **`ACTIVE_HASHING`** — the miner is searching its assigned range and contributes to the
  active hash rate. Its energy accrues to `P_hash,i * t_hash,i`.
- **`EXHAUSTED_PENDING`** — the miner has *asserted* completion of its assignment and is
  awaiting adjudication of that assertion against the evidence requirements of Section 5.
  `EXHAUSTED_PENDING` is a holding state: the assertion is pending verification and has NOT
  been accepted. The miner may already have reduced hashing, but it is NOT yet in
  `LOW_POWER_LISTEN` and is NOT yet credited as exhausted.
- **`LOW_POWER_LISTEN`** — the miner monitors round progress at reduced power. Its energy
  accrues to `P_listen,i * t_listen,i`, NOT to the active hash rate. This is the state in
  which the idle policy realises reduced active power-time.

### 4.2 The I4 gate (binding)

**Invariant I4:** *no `LOW_POWER_LISTEN` before valid exhaustion or valid revocation.* The
transition `EXHAUSTED_PENDING → LOW_POWER_LISTEN` MUST NOT occur merely because the miner
*says* it is finished. Entry into `LOW_POWER_LISTEN` on the exhaustion path is permitted
ONLY when the pending exhaustion assertion has been **adjudicated as true range exhaustion**
under Section 2 using the evidence of Section 5 — i.e. `p = N` is established, not claimed.
A self-reported "finished" with insufficient evidence is a class-5 event (Section 3.5), not
an exhaustion, and leaves the miner blocked at `EXHAUSTED_PENDING` (or escalated), never
advanced to `LOW_POWER_LISTEN`.

The only sanctioned entries into `LOW_POWER_LISTEN` are therefore:

1. **Valid exhaustion path** — `ACTIVE_HASHING → EXHAUSTED_PENDING → LOW_POWER_LISTEN`,
   gated by adjudicated true range exhaustion (this document); or
2. **Valid revocation path** — where the protocol has validly revoked the assignment
   (class 6) such that the miner has no active range to search, subject to the same I4
   requirement that the revocation be *valid*.

No other class in Section 3 — early abandonment, lease expiry, communication loss, false
claim — is a valid basis for `LOW_POWER_LISTEN` on the exhaustion path.

### 4.3 States that are NOT on this chain

`RESERVE` (never-activated or held-out miners), `WAKING` (resuming to hash), `OFFLINE`
(unreachable/departed), and `DISQUALIFIED` (excluded) are reached by other transitions and
are specified elsewhere. In particular, a reserve becoming active passes through `WAKING`
into `ACTIVE_HASHING` (see `STAGE_01_RESERVE_POLICY_SPECIFICATION.md`), not through
`EXHAUSTED_PENDING`.

---

## 5. Required evidence: the modeled progress-verification abstraction

### 5.1 What is required (and what is not)

To adjudicate a pending exhaustion assertion as true range exhaustion, PoCol requires a
**modeled progress-verification abstraction**: a modeled commitment attesting that the
progress marker `p` has reached `N` under the specified traversal order for the asserted
assignment and `TemplateID`. Concretely, the abstraction consists of:

1. a **progress commitment** binding the assignment identity (`MinerID`, range identity,
   `TemplateID`) to the claimed progress marker; and, where the design forms one,
2. an **early-stop / exhaustion summary** attesting sufficient covered progress to justify
   halting active hashing for the assignment.

This abstraction is explicitly a **modeled progress-verification abstraction — NOT a
cryptographic proof** and **NOT a complete proof of range exhaustion**. Stage 1 does not
claim it is sound, unforgeable, or non-repudiable; those properties are out of scope (see
`STAGE_01_PROTOCOL_SCOPE.md`, Section C). What Stage 1 specifies is the *structural
requirement* that SOME such modeled commitment exist and be adjudicated before the I4 gate
opens — so that "the miner said so" alone can never open it.

### 5.2 Adjudication and recording

- If the modeled progress-verification abstraction supports `p = N` for the asserted
  assignment/`TemplateID`, the assertion is adjudicated as true range exhaustion and the I4
  gate permits `EXHAUSTED_PENDING → LOW_POWER_LISTEN`.
- If it does not, the assertion is classified as class 5 (or, where the shortfall is
  benign and self-declared, class 2/3/4 as appropriate), the range's unsearched tail is
  treated as a coverage gap, and the outcome is **recorded, not silently repaired**
  (invariant **I16**). No amount of assertion volume substitutes for the abstraction.

### 5.3 Interaction with template refresh

Because exhaustion is `TemplateID`-scoped (Section 2), a `TEMPLATE_REFRESH` invalidates
outstanding progress commitments: after refresh, `p` resets to `0` for the new `TemplateID`
and no miner may carry an exhaustion adjudication across templates.

---

## 6. When the idle policy yields a saving — and when it does not

The idle policy targets the only term the A1 invariant leaves free: **active power-time**
`Σ_i P_hash,i * t_hash,i`. Whether a positive saving `ΔE = E_continuous_control −
E_idle_policy` arises is conditional. The exhaustion semantics above determine *eligibility*
to stop hashing; the energy model (`STAGE_01_ENERGY_MODEL_SPECIFICATION.md`) determines
whether stopping actually nets a saving. This section states the qualitative conditions;
the quantitative necessary conditions and degenerate cases are specified normatively in the
energy-model document.

### 6.1 Conditions under which a saving CAN arise

A saving is possible only when **all** of the following hold:

1. **A miner legitimately reaches a reduced-power state.** Some miner is adjudicated into
   `LOW_POWER_LISTEN` (valid exhaustion or valid revocation, Section 4) or held in
   `RESERVE`, for a strictly positive duration. If no miner ever leaves `ACTIVE_HASHING`
   early, active power-time is unchanged and `ΔE = 0`.
2. **Reduced-power draw is below hashing draw.** For the miners that go idle,
   `P_listen,i < P_hash,i` (and reserve/offline draw is below hashing draw). If listening
   costs as much as hashing, moving to it saves nothing.
3. **Transition and coordination overhead is smaller than the gross saving.** The wake,
   transition, and coordination terms (`P_wake,i * t_wake,i`, `E_transition,i`,
   `E_coordination,i`) incurred to realise and later reverse the idle period MUST be smaller
   than the gross active-power-time reduction, or the net saving is non-positive.
4. **The saving is not an artefact of hidden deletion.** Failed runs, zero-block runs, and
   uncovered tails MUST remain in the accounting (invariants I5–I7); a "saving" produced by
   dropping unfavourable runs is not a saving.

### 6.2 Conditions under which NO saving arises

There is no saving (or a net loss) when, among others:

- **No idle opportunity exists.** If assignments are structured so that every miner is
  legitimately hashing for the full horizon (for example, homogeneous rates with equal
  ranges sized to consume the whole horizon), no miner reaches `LOW_POWER_LISTEN` or
  `RESERVE` early and `ΔE = 0`.
- **Idle draw equals hashing draw** (`P_listen = P_hash`) — zero gross saving.
- **Zero idle duration** (`t_listen = 0`, or reserve never held out) — zero saving.
- **Overhead dominates** — wake plus transition (and coordination) costs meet or exceed the
  gross active-power-time reduction, eliminating the net saving.
- **The security floor forbids going idle.** If moving miners to reduced power would breach
  the modeled security floor (`STAGE_01_SECURITY_FLOOR_SPECIFICATION.md`), those miners are
  not permitted to go idle, so the eligible saving is not realised. The idle policy is
  bounded from below by the security-floor policy.

At Stage 1 no particular value of `ΔE` is claimed as achieved. This document specifies only
the conditions that make a saving *eligible*; it asserts no saving.

---

## 7. Invariant references

- **I4** — no `LOW_POWER_LISTEN` before valid exhaustion or valid revocation; the
  self-report "finished" never suffices (Sections 3.5, 4.2, 5).
- **I5–I7** — duration and energy conservation; no hidden deletion of failed or zero-block
  runs (Section 6.1, item 4; full statement in `STAGE_01_ENERGY_MODEL_SPECIFICATION.md`).
- **I16** — security-floor breaches and unsubstantiated claims are recorded, not silently
  repaired (Sections 3.5, 5.2).

All symbols and terms are defined in `STAGE_01_TERMINOLOGY.md`. This document specifies
structure only and makes no implementation, validation, security, fairness, or incentive
claim.
