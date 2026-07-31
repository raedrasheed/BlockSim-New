# Stage 1 — PoCol Threat Model

**Document status:** Stage-1 specification-only. This document defines the actors and the
adversarial properties considered for **PoCol** with **the idle policy within PoCol** enabled,
and classifies each property by how (and whether) it can be addressed. It is a scoping and
classification document. It does NOT claim that any property is achieved, and — as required at
Stage 1 — it classifies **no** property as experimentally supported. The idle policy is an
operating policy inside PoCol, not a variant or fork.

Canonical references: 8 miner states and 10 round states as listed in
`STAGE_01_PROTOCOL_SCOPE.md`; invariants `I1..I19` in `STAGE_01_INVARIANT_CATALOGUE.md`;
adversarial share `q_adv(t) = H_adversarial(t) / (H_honest(t) + H_adversarial(t))`; progress
evidence is a **modeled progress-verification abstraction**, never a cryptographic proof;
difficulty is FIXED (`I12`).

---

## 1. Classification vocabulary (exactly one per property)

Each property in Section 3 is tagged with exactly one label:

- **SPECIFIED_FOR_LATER_TEST** — the behaviour is representable in the Stage-1 specification
  and is planned for adversarial/structural testing at a later stage (2–5). Specified, not yet
  tested.
- **UNRESOLVED** — the specification does not yet fix a design decision that determines how
  this threat is handled; it is tracked in `STAGE_01_OPEN_QUESTIONS.md`.
- **OUT_OF_SCOPE_FOR_CURRENT_SIMULATOR** — the threat concerns effects the Stage-1 simulator
  does not model (e.g. real network/hardware behaviour) and will not be exercised by it.
- **REQUIRES_FORMAL_PROOF** — a soundness claim about this threat can only be established by a
  formal argument, not by simulation.
- **REQUIRES_REAL_IMPLEMENTATION** — resolving this threat depends on a real deployed
  implementation (real cryptography, real ASIC power states, real network stack), outside any
  simulation.

No property below is labelled "experimentally supported"; that label does not exist at
Stage 1.

---

## 2. Actors: capabilities and limitations

### 2.1 Honest miner
- **Capabilities.** Registers; accepts assignments; hashes only within its valid current
  range; emits truthful progress commitments; propagates any valid solution promptly;
  transitions between states only per the specified guards (`I4`, `I10`).
- **Limitations.** Does not deviate from the protocol; provides the honest hash-rate mass
  `H_honest(t)`; its participation is what the security floors are defined to protect.

### 2.2 Crash-faulty miner
- **Capabilities.** May stop at any time (disappear while hashing or listening; fail to wake).
  No malicious intent.
- **Limitations.** Does not forge messages, lie about progress, or mine out of range. Its
  effect is loss of coverage/liveness, handled by lease expiry, reassignment (`I8`, `I9`), and
  floor recovery.

### 2.3 Rational miner
- **Capabilities.** Deviates only when it perceives a payoff: e.g. free-riding, withholding a
  solution, or continuing to hash while others idle. Follows the protocol where deviation does
  not benefit it.
- **Limitations.** Assumed not to take actions that are purely costly with no benefit. Its
  incentives are NOT proven aligned at Stage 1 (incentive compatibility is out of scope).

### 2.4 Byzantine miner
- **Capabilities.** Arbitrary deviation: mining out of range, false exhaustion, progress
  withholding, template withholding/grinding, replaying stop certificates, timestamp
  manipulation, colluding with others.
- **Limitations.** Cannot break the modeled progress-verification abstraction's target check
  where the specification requires it (`I11`, `I2`, `I3`); cannot cause acceptance of work
  outside a valid current assignment without violating a specified invariant. Whether those
  invariants hold under a real implementation is a separate (later/formal) question.

### 2.5 Adversarial coordinator
- **Capabilities.** May issue conflicting or biased assignments, delay commitments, propose
  false early-stop certificates, or withhold coordination services.
- **Limitations.** In the specification, assignments and acceptances are constrained by
  `I1`, `I2`, `I3`, `I10`, and `I11`; a false early-stop cannot terminate hashing without
  target verification. The *soundness* of these constraints against a genuinely adversarial
  coordinator is not established at Stage 1.

### 2.6 Network adversary
- **Capabilities.** Delays, drops, reorders, or partitions messages between coordinator and
  miners.
- **Limitations.** Does not forge cryptographic material. Its modeled effects are confined to
  timing and reachability; full network behaviour is not modelled by the Stage-1 simulator.

---

## 3. Threat properties and classification

For each property: the actor(s), how it manifests in PoCol, the coupled invariant(s), and the
single classification label.

### 3.1 Mining outside assigned range
- **Actor(s).** Byzantine, rational.
- **Manifestation.** Submitting solutions/progress for nonces outside the signer's valid
  current assignment. Rejected by the acceptance predicate (`I2`).
- **Coupled invariants.** I1, I2, I13.
- **Classification.** **SPECIFIED_FOR_LATER_TEST** (Stage 4 out-of-range acceptance tests).

### 3.2 Continuing to mine while honest miners idle
- **Actor(s).** Rational, Byzantine.
- **Manifestation.** A miner keeps `ACTIVE_HASHING` (and thus keeps its share of active
  power-time and hash rate) while others move to `LOW_POWER_LISTEN`, potentially raising its
  relative `q_adv(t)`.
- **Coupled invariants.** I16 (floor/share breaches recorded), I4 (others' idling legitimacy).
- **Classification.** **SPECIFIED_FOR_LATER_TEST** (Stage 4 share-under-idle scenarios).

### 3.3 False completion (false exhaustion)
- **Actor(s).** Byzantine, rational.
- **Manifestation.** Claiming a range is exhausted while a remainder is unsearched, to idle
  early. Adversarial **reported exhaustion** (`reported_exhaustion`) is compared against
  **simulator ground truth** (`actual_exhaustion`/`actual_frontier`) through the modeled
  audit/detection abstraction (`I8`); false-exhaustion detection is **modeled, not proven**
  (CR-B4). When a reported claim is accepted it is recorded as **"accepted reported exhaustion
  under the modeled audit abstraction"** — never a cryptographic proof or a verified actual
  exhaustion.
- **Coupled invariants.** I8, I4.
- **Classification.** **SPECIFIED_FOR_LATER_TEST** (Stage 2 accounting + Stage 4 adversarial).

### 3.4 Solution withholding
- **Actor(s).** Rational, Byzantine.
- **Manifestation.** Finding a valid block and not propagating it. Not directly detectable at
  Stage 1 (no proof-of-possession); prolongs honest active power-time. Where competing valid
  solutions do arrive, they are resolved by **network-arrival semantics** (earliest valid
  arrival; ties by `candidate_hash` then `MinerID`; others recorded competing/stale): each
  recipient continues hashing while validating and, on successful validation, **pauses** its
  assignment (PATH B, `stop_reason = VALID_SOLUTION_VERIFIED`, retained `actual_frontier`
  preserved) rather than marking its range exhausted, and resumes if the full block is later
  rejected or times out — consistent with `STAGE_01_EARLY_STOP_CERTIFICATE.md`; **no chain-wide
  fork-choice proof** is claimed (CR-B9).
- **Coupled invariants.** none directly enforceable at Stage 1.
- **Classification.** **UNRESOLVED** (detection/mitigation design not fixed; tracked in Open
  Questions).

### 3.5 Template withholding
- **Actor(s).** Adversarial coordinator, Byzantine.
- **Manifestation.** Not delivering the committed template (or delivering it late) so miners
  cannot bind work to `TemplateID`. Handled by template-commitment checks and, if systemic,
  `TEMPLATE_REFRESH`.
- **Coupled invariants.** I3.
- **Classification.** **SPECIFIED_FOR_LATER_TEST** (Stage 4 coordinator scenarios).

### 3.6 Template grinding
- **Actor(s).** Adversarial coordinator, Byzantine.
- **Manifestation.** Searching over many candidate templates to bias which template is
  committed. In the confirmatory design the template is committed once and difficulty is fixed
  (`I12`), constraining but not proving resistance.
- **Coupled invariants.** I3, I12.
- **Classification.** **REQUIRES_FORMAL_PROOF** (grinding-resistance is a soundness claim, not
  a simulation outcome).

### 3.7 Timestamp manipulation
- **Actor(s).** Byzantine, adversarial coordinator, network adversary.
- **Manifestation.** Falsifying lease/commit/certificate timestamps to affect lease expiry,
  certificate freshness, or ordering.
- **Coupled invariants.** I9 (provenance timestamps), I11 (certificate freshness).
- **Classification.** **REQUIRES_REAL_IMPLEMENTATION** (a trustworthy time/clock source is an
  implementation concern; the simulator uses a modeled clock).

### 3.8 Assignment manipulation
- **Actor(s).** Adversarial coordinator.
- **Manifestation.** Issuing overlapping, biased, or invalid assignments. Constrained by the
  overlap guards (`I1`, `I10`) and reassignment provenance (`I9`).
- **Coupled invariants.** I1, I9, I10.
- **Classification.** **SPECIFIED_FOR_LATER_TEST** (Stage 2 overlap/provenance + Stage 4
  adversarial-coordinator tests).

### 3.9 Sybil identities
- **Actor(s).** Byzantine, rational.
- **Manifestation.** Registering many identities to gain assignments, reserve slots, or share.
  Registration at Stage 1 does not establish Sybil cost.
- **Coupled invariants.** none (no Sybil-cost invariant defined).
- **Classification.** **REQUIRES_REAL_IMPLEMENTATION** (Sybil cost depends on a real
  identity/resource-binding mechanism).

### 3.10 Free riding
- **Actor(s).** Rational.
- **Manifestation.** Drawing rewards/participation credit while contributing little real work
  (e.g. minimal hashing, reliance on reserves). Incentive alignment not modelled.
- **Coupled invariants.** I8 (coverage accounting), I13 (no double credit).
- **Classification.** **UNRESOLVED** (reward/incentive semantics not fixed; tracked in Open
  Questions).

### 3.11 Replayed stop certificates
- **Actor(s).** Byzantine, network adversary.
- **Manifestation.** Re-submitting an old early-stop certificate to halt current hashing.
  Blocked by binding to current `(RoundID, TemplateID)` and by `I11` (no termination without
  target verification).
- **Coupled invariants.** I3, I11.
- **Classification.** **SPECIFIED_FOR_LATER_TEST** (Stage 4 replay tests).

### 3.12 Delayed wake attacks
- **Actor(s).** Byzantine (reserve miner), network adversary.
- **Manifestation.** A promoted reserve deliberately or effectively fails to wake within the
  deadline, so the intended floor top-up never materialises.
- **Coupled invariants.** I10 (activation without overlap), I16 (breach recorded).
- **Classification.** **SPECIFIED_FOR_LATER_TEST** (Stage 4 reserve/recovery timing tests).

### 3.13 Reserve exhaustion
- **Actor(s).** Byzantine coalition, environment.
- **Manifestation.** Driving repeated floor breaches until no `RESERVE` miners remain to
  restore the floor, forcing continue-under-breach or abort.
- **Coupled invariants.** I16 (breach recorded, not repaired), I10.
- **Classification.** **SPECIFIED_FOR_LATER_TEST** (Stage 4 depletion scenarios).

### 3.14 Network partition
- **Actor(s).** Network adversary.
- **Manifestation.** Splitting coordinator and miners so neither side can form valid quorum
  commitments/acceptances; potential conflicting progress on heal.
- **Coupled invariants.** I3 (single committed template/round on reconciliation).
- **Classification.** **OUT_OF_SCOPE_FOR_CURRENT_SIMULATOR** (full partition/network dynamics
  are not modelled; only paused-participation energy effects are).

### 3.15 Coalition behaviour
- **Actor(s).** Byzantine + rational coalitions (possibly with an adversarial coordinator).
- **Manifestation.** Coordinated combinations of the above — e.g. joint withholding plus
  continuing-while-others-idle to push `q_adv(t)` above threshold.
- **Coupled invariants.** I16, I11, I2, I1.
- **Classification.** **REQUIRES_FORMAL_PROOF** (coalition-resistance/majority thresholds are
  soundness claims, not established by simulation).

---

## 4. Classification summary

| # | property | actor(s) | classification |
|---|---|---|---|
| 3.1 | Mining outside assigned range | Byzantine, rational | SPECIFIED_FOR_LATER_TEST |
| 3.2 | Continuing to mine while honest miners idle | rational, Byzantine | SPECIFIED_FOR_LATER_TEST |
| 3.3 | False completion (false exhaustion) | Byzantine, rational | SPECIFIED_FOR_LATER_TEST |
| 3.4 | Solution withholding | rational, Byzantine | UNRESOLVED |
| 3.5 | Template withholding | adversarial coordinator, Byzantine | SPECIFIED_FOR_LATER_TEST |
| 3.6 | Template grinding | adversarial coordinator, Byzantine | REQUIRES_FORMAL_PROOF |
| 3.7 | Timestamp manipulation | Byzantine, coordinator, network | REQUIRES_REAL_IMPLEMENTATION |
| 3.8 | Assignment manipulation | adversarial coordinator | SPECIFIED_FOR_LATER_TEST |
| 3.9 | Sybil identities | Byzantine, rational | REQUIRES_REAL_IMPLEMENTATION |
| 3.10 | Free riding | rational | UNRESOLVED |
| 3.11 | Replayed stop certificates | Byzantine, network | SPECIFIED_FOR_LATER_TEST |
| 3.12 | Delayed wake attacks | Byzantine, network | SPECIFIED_FOR_LATER_TEST |
| 3.13 | Reserve exhaustion | Byzantine coalition | SPECIFIED_FOR_LATER_TEST |
| 3.14 | Network partition | network adversary | OUT_OF_SCOPE_FOR_CURRENT_SIMULATOR |
| 3.15 | Coalition behaviour | Byzantine + rational | REQUIRES_FORMAL_PROOF |

**Binding statement.** None of the properties above is classified as experimentally supported
at Stage 1. Every `SPECIFIED_FOR_LATER_TEST` entry denotes a *plan* to test at a later stage,
not a demonstrated guarantee; every `REQUIRES_FORMAL_PROOF` and `REQUIRES_REAL_IMPLEMENTATION`
entry denotes work that no amount of Stage-1 simulation can settle; and the two `UNRESOLVED`
entries are open design questions carried in `STAGE_01_OPEN_QUESTIONS.md`. No security,
fairness, or incentive-compatibility claim is made for PoCol or for the idle policy within
PoCol at Stage 1.
