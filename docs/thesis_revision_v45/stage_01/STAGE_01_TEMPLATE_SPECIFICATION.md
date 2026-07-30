# Stage 1 — PoCol Template Commitment Specification

**Document status:** Stage-1 specification-only. This document DEFINES the normative
TemplateID commitment for **PoCol** and the rules governing template proposal, verification,
immutability, conflict handling, refresh, and the target rule. It does NOT claim that any
mechanism described here is implemented, validated, secure, fair, live, or
incentive-compatible. Stage 1 SPECIFIES; it demonstrates no property. No security, fairness,
or incentive claim is made anywhere in this document.

**Naming (binding).** The algorithm is ALWAYS **PoCol**. No suffixed, derivative, or
replacement name (e.g. "PoCol-E", "Energy-Aware PoCol", "Enhanced PoCol") is permitted. The
low-power mechanism is referred to ONLY as **the idle policy within PoCol** — an operating
policy that lives inside PoCol, not a new algorithm, variant, or fork.

**Normative keywords.** MUST, MUST NOT, SHALL, SHALL NOT, SHOULD, and MAY are used in the
RFC-2119 sense. A statement without a normative keyword is descriptive and imposes no
requirement.

---

## 1. Purpose and scope

PoCol requires that, within a round, all participating miners search against **one identical,
immutable block template**. This document specifies the object that binds that template — the
**TemplateID commitment** — so that (a) every assignment and every accepted solution can be
checked against exactly one agreed template, and (b) the disjoint nonce-range assignment
specified in `STAGE_01_RANGE_ASSIGNMENT_SPECIFICATION.md` is anchored to a fixed
candidate-identity domain.

This document specifies **structure and rules**. It does NOT provide, and MUST NOT be read as
providing, a proof that agreement on a common template is reached, that it is reached in
bounded time, or that it is reached in the presence of Byzantine participants. Those are open
questions and are enumerated in Section 13. The specification is deliberately explicit that
**common-template agreement is neither free nor instantaneous** (Section 12).

---

## 2. The TemplateID commitment (normative)

### 2.1 Definition

A **block template** is the complete set of header-determining fields against which a round's
miners search the nonce domain. The **TemplateID** is a stable identifier that binds one
specific block template for the duration of a round.

The TemplateID SHALL be a collision-resistant digest computed over the canonical
serialization of the ordered commitment field set defined in Section 2.2. Two templates are
the **same template** if and only if they produce the same TemplateID; they are **different
templates** if the TemplateID differs in any bit. Candidate-header identity is defined
field-for-field: two candidate headers are duplicates **iff all their fields are equal**.
Because the TemplateID is a function of every commitment field, any change to any committed
field yields a different TemplateID and therefore a different candidate-identity domain
(Section 11).

The canonical serialization MUST be deterministic: field order fixed, encodings
length-prefixed or fixed-width, no optional whitespace, no ambiguous representations. A
miner, a coordinator, and a verifier that hold the same field values MUST compute the
identical TemplateID.

### 2.2 Commitment fields

Each field below is part of the committed template. Every field is an input to the TemplateID
digest; none may be altered after commitment (Section 5) without producing a new TemplateID
and a new candidate-identity domain (Section 11).

1. **Previous block identifier.** The identifier of the parent block on which this round
   builds (the chain tip the round extends). It fixes the fork point. A change in the parent
   identifier is a change of round substance, MUST produce a new TemplateID, and — because a
   different parent implies a different chain position — SHOULD be treated as grounds for a
   fresh round rather than an in-round edit. This field prevents work committed to one tip
   from being counted against a different tip.

2. **Transaction-set or Merkle-root commitment.** A commitment to the exact set and ordering
   of transactions included in the candidate block. Two admissible forms are permitted and
   MUST be distinguished at specification time: (a) a **Merkle-root commitment** binding the
   transaction set by its root only (compact; the body is carried separately and checked
   against the root); or (b) an explicit **transaction-set commitment** binding an ordered
   list. Whichever form the deployment fixes, it MUST be the same form for all miners in the
   round, and it fixes the block body. Differences in transaction selection are the principal
   source of honest template divergence and are handled per Section 7 (mempool differences).

3. **Timestamp rule or timestamp window.** The template commits either a single timestamp or,
   where a deployment permits limited freedom, a **bounded timestamp window** `[t_min,
   t_max]`. Two miners MUST NOT be free to search arbitrarily different timestamps under one
   TemplateID: either the timestamp is a committed constant (one value → part of the digest),
   or the window bounds are committed and the in-window value is constrained per Section 8.
   An unbounded timestamp is prohibited because it would be a template-grinding surface
   (Section 9).

4. **Target.** The numeric acceptance threshold a candidate digest MUST satisfy to be a valid
   solution. The target is committed as part of the template and is held **constant** for the
   round in the confirmatory design (Section 12 and the Difficulty and Target Rule, Section
   14; invariant I12). The target is not a control knob of the idle policy.

5. **Version.** The block/template structural version, distinguishing serialization or
   consensus-rule generations of the template format itself. It is committed so that a
   candidate header cannot be reinterpreted under a different structural version.

6. **Reward commitment.** A commitment to the block reward disposition (the coinbase or
   equivalent value assignment) for this template. It is committed because it is part of the
   serialized candidate header space: two otherwise-identical templates with different reward
   dispositions are **different** templates with different TemplateIDs and different
   candidate-identity domains. Stage 1 makes NO incentive, fairness, or reward-correctness
   claim about this field; it is specified as a committed input only.

7. **RoundID.** The identifier of the round in which this template is active. Binding the
   RoundID into the template ties the committed template to exactly one round instance and
   supports invariant I3 (an accepted solution MUST match the current RoundID and TemplateID).
   A given TemplateID belongs to exactly one RoundID; reuse of template content across rounds
   still yields distinct commitments because the RoundID differs.

8. **Template proposer / coordinator identifier (if any).** Where the deployment designates a
   proposer or coordinator for the round's template, that identity MAY be committed so that
   the origin of the template is bound into its TemplateID. This field is **optional at
   Stage 1**: a deployment MAY operate without any distinguished proposer (Section 3), in
   which case the field is absent and its absence is itself part of the canonical
   serialization. Including this field does NOT constitute a claim that proposer selection is
   sound, Sybil-resistant, or Byzantine-tolerant (Section 13).

9. **Protocol-version identifier.** The identifier of the PoCol protocol/rule version under
   which the template is to be interpreted, distinct from the structural template **version**
   of field 5. It is committed so that a template cannot be validly evaluated under a
   protocol version other than the one its proposer intended.

All nine fields (with field 8 optional) form the ordered input to the TemplateID digest. The
serialization order MUST be fixed and published. No field may be silently defaulted: a
deployment MUST specify, for each field, the exact encoding and, for optional field 8, the
exact representation of its presence or absence.

---

## 3. Who proposes a template

Stage 1 permits either of two proposer models and requires that a deployment **fix one** and
publish it; it does not, at Stage 1, select between them or claim either is sound:

- **Coordinator-proposed.** A distinguished coordinator (recorded in commitment field 8)
  assembles and proposes the template for the round. The coordinator's identity is committed.
  Stage 1 does NOT specify how the coordinator is selected, nor claim that selection is fair,
  live, or Byzantine-tolerant (Section 13).
- **Self-proposed / no distinguished proposer.** Miners derive the template from shared
  inputs (parent tip, an agreed transaction-selection rule, committed target and versions)
  such that, when inputs agree, all honest miners independently compute the identical
  TemplateID. Field 8 is then absent.

In both models the proposer's output is a **proposal**, not yet the committed template. A
proposal becomes the immutable round template only through the commitment step of Section 5.
Whichever model is fixed, the act of proposing confers no protocol authority beyond producing
a candidate template that every miner independently verifies (Section 4).

---

## 4. How miners verify a template

Before treating a proposed template as the round template, a miner MUST verify it. Verification
is local, deterministic, and independent — no miner is required to trust the proposer's
assertion of validity. A miner SHALL accept a proposed template only if ALL of the following
hold:

1. **Canonical recomputation.** The miner recomputes the TemplateID from the received
   commitment fields under the canonical serialization and obtains the identical TemplateID.
   A mismatch means the received identifier does not bind the received fields; the miner MUST
   reject.
2. **Parent validity.** The previous block identifier (field 1) references a block the miner
   accepts as the current chain tip for this round.
3. **Body consistency.** The transaction-set or Merkle-root commitment (field 2) is
   internally consistent — the supplied body (or root) matches the committed form, and the
   transactions are individually admissible under the miner's local rules.
4. **Timestamp admissibility.** The committed timestamp, or the committed window `[t_min,
   t_max]`, satisfies the bounding rule of Section 8 relative to the parent and the miner's
   clock tolerance.
5. **Target and versions.** The target (field 4), version (field 5), and protocol-version
   identifier (field 9) are the values the miner expects for this round under I12; the target
   MUST equal the round's fixed target.
6. **Round binding.** The RoundID (field 7) matches the round the miner is participating in
   (supports I3).
7. **Proposer admissibility (if field 8 present).** The committed proposer/coordinator
   identifier is one the miner recognises as admissible for this round under the fixed
   proposer model (Section 3). Stage 1 makes no soundness claim about this check.

A miner that fails any check MUST NOT search under the proposed template and MUST treat the
proposal as a conflicting or invalid template per Section 6. Verification does not require, and
MUST NOT be described as providing, a cryptographic proof of anything beyond field-for-field
recomputation of the TemplateID; progress and exhaustion claims elsewhere in PoCol are handled
only via the **modeled progress-verification abstraction**, never as cryptographic proof.

---

## 5. When the template becomes immutable — the `TEMPLATE_COMMITMENT` round state

Template immutability is tied to the round state machine. A round passes through
`ROUND_INITIALISING` → `TEMPLATE_COMMITMENT` → `ASSIGNMENT` → `HASHING` before any solution
search that counts toward the round begins.

- In `TEMPLATE_COMMITMENT`, the proposed template is verified (Section 4) and the TemplateID
  is fixed for the round. **On entry to `ASSIGNMENT`, the committed template is immutable.**
  From that point until the round leaves the hashing phase, no commitment field (Section 2.2)
  may change while retaining the same TemplateID.
- Immutability means: every assignment issued in `ASSIGNMENT` and every candidate searched in
  `HASHING` references the single committed TemplateID. Invariant I3 requires that an accepted
  solution match the current RoundID and TemplateID; immutability is what makes I3 checkable.
- Any subsequent change to template content is NOT an edit of the committed template. It is
  the creation of a **new** template with a **new** TemplateID, reached only through
  `TEMPLATE_REFRESH` (Section 10), which restarts the commitment cycle. There is no in-place
  mutation of a committed template.

The commitment step is therefore the single point at which the round's candidate-identity
domain (Section 11) is fixed. Everything downstream — assignments, leases, progress
commitments, acceptance — is defined relative to that fixed TemplateID.

---

## 6. How conflicting templates are treated

Two proposals **conflict** when they carry different TemplateIDs for the same RoundID (i.e.
they differ in at least one committed field). Because a round mines against exactly one
immutable template, conflicting proposals cannot both be the round template.

- A miner MUST NOT search two conflicting templates as though they were the same round's
  work; work under one TemplateID is not transferable to another (Section 11).
- Before `TEMPLATE_COMMITMENT` completes, resolution of which proposal becomes the committed
  template is a **distributed-agreement problem**, not a local one. Stage 1 does NOT specify a
  guaranteed resolution procedure and does NOT claim one exists; the open questions are listed
  in Section 13. A deployment MUST fix a selection rule (e.g. proposer-designated under the
  coordinator model, or a deterministic tie-break over proposals under the self-proposed
  model), and MUST publish it, but Stage 1 asserts no soundness, liveness, or
  Byzantine-tolerance property of that rule.
- After `TEMPLATE_COMMITMENT` completes for a round, a proposal bearing a different TemplateID
  is, by definition, a proposal for a **different** template. It cannot silently replace the
  committed one; adopting it requires a `TEMPLATE_REFRESH` (Section 10), which produces a new
  round-template generation.
- Detected persistent conflict that cannot be resolved into a single committed template is a
  trigger for view change / `TEMPLATE_REFRESH` or, in the limit, `ROUND_ABORTED` (Section 10).

---

## 7. How mempool differences are handled

Honest miners will in general observe **different mempools** (different pending transaction
sets due to propagation timing). Mempool difference is therefore the principal source of
honest template divergence, and it is handled at the transaction-set / Merkle-root commitment
field (field 2), not by ignoring it:

- The committed template fixes **one** transaction-set/Merkle-root commitment for the round.
  Once committed, a miner's local mempool differences are irrelevant to the round: all miners
  search the single committed body regardless of what their own mempool contains.
- Reconciliation of mempool differences happens **before** commitment, inside the proposal and
  `TEMPLATE_COMMITMENT` steps, via whatever transaction-selection rule the deployment fixes
  (Section 3). Stage 1 specifies that such a rule MUST exist and be deterministic given
  agreed inputs; it does NOT claim the rule achieves agreement under adversarial propagation
  (Section 13).
- A miner whose local view would have produced a different transaction set still MUST, once
  the template is committed and verified (Section 4), search the committed template or decline
  to participate. It MUST NOT search a locally preferred variant under the round's TemplateID,
  because that variant is a **different** template (different Merkle root → different
  TemplateID → different candidate-identity domain, Section 11).
- Mempool-driven divergence that cannot be reconciled into a single committed template is
  handled as a template conflict (Section 6) and may trigger `TEMPLATE_REFRESH` (Section 10).

---

## 8. How timestamp changes are bounded

Timestamps are constrained so they cannot become an unbounded degree of freedom:

- If the template commits a **single timestamp**, that value is part of the TemplateID; it
  cannot change without producing a new TemplateID (and hence a new candidate-identity domain
  and a `TEMPLATE_REFRESH`).
- If the template commits a **timestamp window** `[t_min, t_max]`, the window bounds are
  committed (part of the digest) and MUST be finite and narrow. `t_min` MUST NOT precede the
  parent block's timestamp beyond the deployment's permitted skew, and `t_max` MUST NOT exceed
  the miner's local clock plus a fixed, published forward-tolerance. The window width MUST be
  bounded by a fixed published constant.
- Any in-window timestamp freedom is a **grinding surface** and is limited per Section 9: the
  permitted set of timestamps a miner may serialize under one TemplateID MUST be finite,
  bounded, and identical for all miners.
- A timestamp change that falls outside the committed window is not a re-timestamp of the same
  template; it is a different template requiring `TEMPLATE_REFRESH`.

---

## 9. How template grinding is limited

**Template grinding** is the manufacture of many distinct candidate-identity domains from
nominally the same round work by varying a committed field (timestamp, reward disposition,
transaction ordering, etc.) to multiply the searchable header space. It is limited as follows:

- Every field that could be varied is **committed** and enters the TemplateID (Section 2.2).
  Varying any of them does not extend the current template's domain; it creates a **different**
  template with a different TemplateID (Section 11). Thus grinding cannot enlarge a committed
  template's candidate-identity domain — it can only manufacture new domains, each of which
  would require its own commitment and would be searched under its own TemplateID.
- The **timestamp** freedom is explicitly bounded to a finite committed window (Section 8),
  and the permitted timestamp set is identical for all miners, so timestamp variation cannot
  be used to fan out per-miner domains within one committed template.
- The number of committed templates a round may cycle through (via `TEMPLATE_REFRESH`) SHOULD
  be bounded by a fixed, published policy, so that refresh itself cannot be abused as an
  unbounded grinding channel. Stage 1 specifies that such a bound MUST exist; it does NOT claim
  the bound is incentive-compatible or that it defeats a resource-unbounded adversary (Section
  13). No security claim is made here.
- Grinding limitation is stated as a **structural** property of the commitment (one domain per
  TemplateID), not as a security guarantee.

---

## 10. What triggers view change or template refresh → `TEMPLATE_REFRESH`

`TEMPLATE_REFRESH` is the only sanctioned path by which the mined content of a round changes.
It replaces the committed template with a **new** immutable template bearing a **new**
TemplateID and restarts the commitment cycle (`TEMPLATE_REFRESH` → `TEMPLATE_COMMITMENT` →
`ASSIGNMENT` → `HASHING`). A refresh does not edit the prior template; it supersedes it.

Triggers for view change / `TEMPLATE_REFRESH` include, at minimum:

1. **Parent change.** The chain tip the round builds on changes (a new accepted block, or a
   reorg): the previous block identifier (field 1) is stale, so the template MUST be refreshed
   (or the round restarted).
2. **Unresolvable template conflict.** Conflicting proposals (Section 6) cannot be reduced to
   a single committed template within the commitment step.
3. **Timestamp-window expiry.** The committed timestamp window (Section 8) has elapsed, so no
   in-window timestamp remains admissible.
4. **Transaction-set invalidation.** A committed transaction becomes inadmissible (e.g.
   conflicting spend confirmed elsewhere), invalidating field 2.
5. **Proposer/coordinator failure or replacement.** Under the coordinator model, the committed
   proposer (field 8) is unavailable or replaced, requiring a new proposal — this is the
   view-change case.
6. **Governance-directed target change.** A target change MUST arrive only through the
   separately-governed mechanism of Section 14 and is realised as a refresh to a new template
   carrying the new committed target; it is never an in-place edit (I12).

A refresh MUST NOT be triggered as a side effect of idle-policy activity: idle entry, reserve
activation, wake transitions, lease expiry, or a security-floor breach do NOT of themselves
change the committed target and do NOT rewrite the committed template (Sections 12, 14). Where
the protocol cannot form a fresh committed template at all, the round terminates via
`ROUND_ABORTED` rather than mutating a committed template.

---

## 11. Why a changed template creates a NEW candidate-identity domain (relation to H1)

The H1 finding concerns **duplicate serialized candidate-header evaluations among honest
miners**: candidate-header identity is defined field-for-field, so two candidate headers are
duplicates **iff all their fields are equal**. Disjoint nonce-range assignment eliminates
duplicate serialized candidate-header evaluations **within one committed template**, because
each nonce is searched by at most one miner under one TemplateID.

That elimination is meaningful **only relative to a fixed candidate-identity domain**. The
domain is fixed by the committed template:

- A candidate header serialized under TemplateID `T` embeds every committed field of `T`.
- A different template `T′` (differing in any committed field — parent, transaction-set/Merkle
  root, timestamp, target, version, reward commitment, RoundID, proposer, protocol version)
  produces **different serialized candidate headers** for the same nonce. A nonce `n` under
  `T` and the same nonce `n` under `T′` are **different** candidate identities, because not all
  fields are equal.
- Therefore a changed template does not extend the current domain; it opens a **new
  candidate-identity domain**. Disjointness and non-duplication established under `T` say
  nothing about `T′`: the same nonce may be searched under both `T` and `T′` without violating
  within-template non-duplication, precisely because they are distinct identities.

Consequences for the specification:

- Non-duplication (the H1-relevant property, under modeled assumptions) is a **per-TemplateID**
  property. Assignments, leases, and progress commitments MUST be interpreted only within their
  own TemplateID; they carry no meaning across a `TEMPLATE_REFRESH`.
- On refresh, all prior assignments are, with respect to the new domain, void: the range
  assignment specification requires assignments to carry TemplateID (see
  `STAGE_01_RANGE_ASSIGNMENT_SPECIFICATION.md`) so that a solution under the new TemplateID can
  never be validated against an assignment issued under the old one (supports I2, I3).
- This is why the target and every other field are committed rather than free (Section 2.2):
  the entire non-duplication argument depends on a single, fixed, agreed candidate-identity
  domain per round-template generation.

No security or optimality claim is made here; the statement is structural. It says only that
"different template ⇒ different serialized candidate headers ⇒ different candidate-identity
domain", which is what makes per-template disjointness well defined.

---

## 12. Common-template agreement is NOT free or instantaneous

This specification MUST NOT be read as assuming that all miners costlessly and immediately hold
the same committed template. Reaching a single committed TemplateID is a **distributed-agreement
problem** with real cost and real failure modes:

- Proposals must be disseminated, verified, and reconciled (Sections 3, 4, 6, 7). This takes
  time and communication and can fail.
- Honest miners start from **different mempools** (Section 7) and possibly different views of
  the chain tip (Section 10), so divergence is the default, not the exception.
- Agreement in the presence of faulty or adversarial participants is not provided here and is
  not claimed (Section 13).

Stage 1 therefore treats "all miners mine one common immutable template" as a **specified
precondition of the round's hashing phase**, established through `TEMPLATE_COMMITMENT`, and NOT
as a free-standing assumption that is automatically satisfied. The cost and reachability of
that precondition are exactly the unresolved matters of Section 13. Any later-stage energy
comparison (ΔE against the A1 invariant) must not silently assume zero-cost, instantaneous
template agreement; the coordination and transition terms of the energy model are where such
costs would appear.

---

## 13. Unresolved distributed-agreement questions

The following questions are **open at Stage 1**. They are recorded here as unresolved; nothing
elsewhere in this document should be read as answering them. Listing a question does not imply
a solution exists.

1. **Proposer selection.** How is the template proposer/coordinator (commitment field 8)
   selected each round? Is selection deterministic, live, and resistant to capture? Stage 1
   fixes only that a model is chosen and published, not that selection is sound or
   Sybil-resistant.
2. **Byzantine template disagreement.** What guarantees, if any, hold when participants
   propose or attest to conflicting templates dishonestly? No Byzantine-agreement result is
   provided.
3. **View-change cost.** What is the latency, message, and energy cost of a view change /
   `TEMPLATE_REFRESH`, and how is it bounded? How does it enter the energy model's coordination
   and transition terms?
4. **Termination / liveness of commitment.** Is `TEMPLATE_COMMITMENT` guaranteed to terminate
   with a single committed template under partial synchrony or asynchrony? Under what timing
   model?
5. **Conflict-resolution soundness.** Does the deployment's fixed conflict-selection rule
   (Section 6) converge all honest miners to the same TemplateID? Under what fault assumptions?
6. **Mempool reconciliation under adversarial propagation.** Does the fixed
   transaction-selection rule (Section 7) yield agreement when transaction propagation is
   adversarially delayed or partitioned?
7. **Refresh-count bound vs. grinding.** Is the bound on refreshes per round (Section 9)
   simultaneously sufficient to limit grinding and permissive enough for liveness? Is it
   incentive-compatible?
8. **Parent-change interaction.** How do frequent tip changes (Section 10) interact with
   in-progress commitment, and can they be exploited to force churn?
9. **Proposer accountability.** Is a faulty or equivocating proposer detectable and, if so,
   with what evidence? Stage 1 provides none.
10. **Interaction with the idle policy.** How do reserve miners, low-power-listening miners,
    and waking miners participate in (or abstain from) template agreement, and does reduced
    participation degrade agreement reachability? Out of scope to answer here.
11. **Target-change governance mechanism.** The separately-governed target-change mechanism of
    Section 14 is named but not designed; its agreement properties are entirely open.

These questions are the boundary of the Stage-1 template specification. They are open
problems, not deferred implementation details, and they must be resolved before any liveness,
security, or agreement property may be claimed for template commitment in PoCol.

---

## 14. Difficulty and Target Rule

This section governs the **target** committed in field 4 and its relationship to template
refresh. It is normative and is bound by invariant **I12 (difficulty constant in the
confirmatory protocol)**.

### 14.1 Difficulty is held constant

In the **core confirmatory design of PoCol, difficulty is held constant**. The committed
target (field 4) is fixed for the round and does not vary as a function of participation,
scheduling, or the idle policy. Every miner in a round searches against the identical fixed
target, and every round in the confirmatory design uses the governed constant difficulty.
This is invariant I12 and MUST NOT be violated by any mechanism specified in this
documentation set.

### 14.2 Idle policy does NOT lower difficulty

None of the idle-policy events lowers difficulty or the target, automatically or otherwise:

- **Idle entry** (a miner moving to `LOW_POWER_LISTEN`) MUST NOT change the target.
- **Reserve activation** (promotion of a `RESERVE` miner to `ACTIVE_HASHING`) MUST NOT change
  the target.
- **Security-floor breach** (active honest hash rate falling below the modeled floor) MUST NOT
  automatically lower the target; it drives round handling toward `SECURITY_RECOVERY`, not a
  difficulty reduction.

The idle policy reduces **active power-time**, never difficulty. Making difficulty a function
of participation would both violate I12 and conflate the energy result with a difficulty
effect; it is prohibited in the confirmatory design.

### 14.3 Target changes require a separately-governed mechanism

Any change to the committed target requires a **new, separately-governed difficulty/target
mechanism** that is NOT specified or designed in this document. Such a mechanism, if it exists,
is external to the confirmatory design, is governed independently, and its outputs enter PoCol
only as a governed new committed target. This document neither designs a difficulty controller
nor authorises one; specifying the interaction below MUST NOT be read as designing one.

### 14.4 Dynamic-difficulty experiments are exploratory and isolated

Any dynamic-difficulty behaviour is **exploratory only** and MUST be isolated from the
confirmatory design: run separately, reported separately, and never mixed into the confirmatory
result. A dynamic-difficulty experiment is not part of PoCol's core design and carries none of
this document's structural statements. Confirmatory conclusions MUST be drawn only under
constant difficulty (I12).

### 14.5 How target and template refresh interact (without designing a controller)

The permitted interaction is limited and mechanical:

- A target change is realised **exclusively** as a `TEMPLATE_REFRESH` (Section 10, trigger 6):
  the new governed target is committed as field 4 of a **new** template with a **new**
  TemplateID. There is no in-place edit of a committed target; a committed template's target is
  immutable for its round-template generation (Section 5).
- Within any single committed template, the target is constant (I12). Refresh boundaries are
  the only points at which a governed target value could differ, and only if the external
  governed mechanism has produced a new value.
- The refresh path merely **carries** a governed target into a newly committed template; it
  performs no computation of difficulty, contains no feedback loop, and reads no idle-policy or
  participation signal. It MUST NOT infer, adjust, or interpolate a target.
- Consequently, in the confirmatory design where the governed target is the fixed constant,
  every refresh commits the **same** target, and I12 holds across refreshes as well as within
  a round.

This preserves a clean separation: template refresh is the transport for a governed target;
it is not, and MUST NOT become, a difficulty controller.

---

## 15. Reference identifiers used in this document

- **Miner states (8, mutually exclusive):** `REGISTERED`, `RESERVE`, `ACTIVE_HASHING`,
  `EXHAUSTED_PENDING`, `LOW_POWER_LISTEN`, `WAKING`, `OFFLINE`, `DISQUALIFIED`.
- **Round states (10):** `ROUND_INITIALISING`, `TEMPLATE_COMMITMENT`, `ASSIGNMENT`,
  `HASHING`, `SECURITY_RECOVERY`, `SOLUTION_PROPAGATION`, `ROUND_ACCEPTED`, `ROUND_EXHAUSTED`,
  `TEMPLATE_REFRESH`, `ROUND_ABORTED`.
- **Invariants referenced:** I1 (no two valid active assignments overlap); I2 (an accepted
  solution lies in the signer's valid current assignment); I3 (an accepted solution matches the
  current RoundID and TemplateID); I8a (coverage-state partition:
  searched + active_unsearched + inactive_unsearched = assigned_domain) with I8b (orthogonal
  custody model {original, renewed, reassigned, revoked, expired, abandoned}, non-additive);
  I12 (difficulty constant in the confirmatory
  protocol). I1, I2, I8a, and I8b are specified operationally in
  `STAGE_01_RANGE_ASSIGNMENT_SPECIFICATION.md`.
- **Accounting invariant A1:** continuous full-participation energy is fixed at
  **8.420833333 kWh** (141 TH/s, 21.5 J/TH, 3031.5 W active power, 10,000 s horizon), invariant
  to how the nonce domain is partitioned. Partitioning ALONE does not reduce total fixed-horizon
  energy; reduction arises only from reduced active power-time.

No text in this document claims that PoCol, or the idle policy within PoCol, is implemented,
validated, secure, fair, live, or incentive-compatible.
