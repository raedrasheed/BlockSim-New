# Stage 1 — PoCol Terminology

**Document status:** Stage-1 specification-only. This document is the authoritative glossary
for the PoCol protocol at Stage 1. Every term is defined to be consistent with the canonical
preamble and with `STAGE_01_PROTOCOL_SCOPE.md`. No definition here should be read as claiming
that any mechanism is implemented, validated, secure, fair, or incentive-compatible.

**Naming rule (binding):** the algorithm name is ALWAYS **PoCol**. The low-power mechanism is
described ONLY as "the idle policy within PoCol". The strings "PoCol-E", "Energy-Aware PoCol",
and "Enhanced PoCol" are prohibited.

**Reference cross-links.** "Scope §X" denotes the corresponding section of
`STAGE_01_PROTOCOL_SCOPE.md`. "Preamble" denotes the canonical Stage-1 preamble. "Invariant
Catalogue" denotes the separate document defining I1..I19.

---

## 1. Terminology table

| Term | Symbol / Type | Exact meaning | First-defined-in |
|---|---|---|---|
| PoCol | Algorithm name | The consensus algorithm specified in this thesis. The name is invariant; no suffixed or derivative name is permitted. All concepts in this stage are components or policies of PoCol. | Preamble; Scope §0.1 |
| Idle policy within PoCol | Operating policy | The low-power operating policy that lives INSIDE PoCol (equivalently "PoCol with the idle policy enabled"). It reduces active power-time via low-power listening, reserve operation, and reduced participation. It is NOT a new algorithm or variant, and its properties are unproven at Stage 1. | Preamble; Scope §0.1, §B |
| Common immutable block template | Protocol object | The single identical, immutable block template that all miners in a round mine against. Its content cannot change within a round; changing it requires a template refresh. | Scope §A.1 |
| TemplateID | Identifier / opaque ID | Stable identifier binding one specific common immutable block template. Every assignment, progress commitment, and accepted block references its TemplateID so work provably targets one agreed template. | Scope §A.2 |
| RoundID | Identifier / opaque ID | Stable identifier of a single mining round. Scopes the round-state machine, assignments, and templates belonging to that round. | This document (§1) |
| AssignmentID | Identifier / opaque ID | Stable identifier of one assignment of a nonce range (or ranges) to a miner within a round, binding a MinerID, a TemplateID, and the assigned range(s). | This document (§1) |
| MinerID | Identifier / opaque ID | Stable identifier of a registered miner, established at registration and used to attribute assignments, commitments, and accepted blocks. | Scope §A.4 |
| Nonce domain | Set / search space | The full space of nonce values searched for a given template. Partitioned into disjoint ranges for assignment. By invariant A1, how it is partitioned does not by itself change fixed-horizon energy. | Scope §A.3, §0.2 |
| Disjoint nonce range | Subset of nonce domain | A contiguous subset of the nonce domain assigned to a miner such that it does not overlap any other miner's range for the same template. | Scope §A.3 |
| range_start | Integer bound | Inclusive lower bound of a nonce range (first nonce in the range). | This document (§1) |
| range_end | Integer bound | Exclusive (or inclusive, per convention) upper bound of a nonce range (last nonce boundary). | This document (§1) |
| range_size | Integer count | Number of nonces in a range; range_size = range_end − range_start under the half-open convention. | This document (§1) |
| Lease | Time-bounded grant | A time-bounded grant of a nonce range to a miner; on expiry the range may be reclaimed, renewed, or reassigned rather than held indefinitely. | Scope §B.5 |
| lease_start | Timestamp | The time at which a range lease becomes effective. | Scope §B.5 |
| lease_expiry | Timestamp | The time at which a range lease ceases to be effective, permitting reclamation or reassignment of the range. | Scope §B.5 |
| Searched prefix | Subrange | The leading portion of an assigned range that a miner has already searched (covered), bounded above by the miner's progress frontier. | This document (§1) |
| Unsearched suffix | Subrange | The trailing portion of an assigned range not yet searched, i.e. the complement of the searched prefix within the range. | This document (§1) |
| assigned_domain | Position set | The positions placed under assignment for a `(RoundID, TemplateID)` (the union of leased ranges); the domain reconciled by the I8a coverage-state partition. | This document (§1) |
| Coverage state | Per-position classification | Exactly one of `searched`, `active_unsearched`, or `inactive_unsearched`; the three partition `assigned_domain` exactly and are pairwise disjoint (I8a). The normative I8a measure uses **accepted** coverage: `accepted_searched + active_unsearched + inactive_unsearched = assigned_domain`. Orthogonal to custody status (I8b). | This document (§1) |
| searched | Coverage state | Positions counted as searched under **ACCEPTED adjudication** — i.e. `accepted_searched` (counted at most once per position per template). The normative I8a searched measure uses accepted coverage only, never reported progress. A coverage state, not a custody status. | This document (§1) |
| active_unsearched | Coverage state | Positions under a live lease not yet within a searched prefix. | This document (§1) |
| inactive_unsearched | Coverage state | Positions not under any live lease and not yet searched (custody lapsed — expired, abandoned, or revoked — or awaiting (re)assignment). | This document (§1) |
| Custody status | Per-assignment lineage status | Exactly one of `{original, renewed, reassigned, revoked, expired, abandoned, completed}` (I8b): the lineage/event history of an assignment. Orthogonal to coverage state and NOT an additive coverage term. | This document (§1) |
| original | Custody status | First assignment of a range in its lineage (`previous_assignment_reference = null`). | This document (§1) |
| renewed | Custody status | Custody extended to the SAME holder past `lease_expiry`. | This document (§1) |
| reassigned | Custody status | Custody transferred to a DIFFERENT holder. A custody status, never a coverage term; a reassigned position keeps its own independent coverage state. | This document (§1) |
| revoked | Custody status | Custody withdrawn by the authority before `lease_expiry`. | This document (§1) |
| expired | Custody status | Custody lapsed at `lease_expiry` without renewal. | This document (§1) |
| abandoned | Custody status | Custody relinquished by the holder ceasing sanctioned progress on a live lease. | This document (§1) |
| completed | Custody status | Terminal lineage status of a range fully exhausted under the same `RoundID`/`TemplateID` via PATH A (`coverage_state = searched`). A `completed` range is NOT reassignable: it is not released to the reassignable pool, not marked `inactive_unsearched`, and exhaustion is never a reassignment reason (permitted reassignment reasons are exactly `lease_expiry`, `abandonment`, `revocation`, `departure`, `conflict`, `security_recovery`). Continuation is via new `original` assignments under a new `TemplateID` on template refresh. | This document (§1) |
| REGISTERED | Miner state (1 of 8) | Miner is admitted to PoCol with a MinerID but is not described by any more specific active/reserve/idle state. Mutually exclusive with the other seven miner states. | Preamble; Scope §E |
| RESERVE | Miner state (2 of 8) | Registered and available but not currently assigned an active range; draws no active hashing power until promoted. | Preamble; Scope §B.2, §E |
| ACTIVE_HASHING | Miner state (3 of 8) | Miner is actively hashing an assigned range. The ONLY state that contributes to the active hash rate and to the P_hash·t_hash term. | Preamble; Scope §0.3, §E |
| EXHAUSTED_PENDING | Miner state (4 of 8) | Miner has exhausted its assigned range (own range fully searched, no valid solution found) and awaits round resolution. Reachable ONLY via PATH A range exhaustion (`stop_reason = RANGE_EXHAUSTED`); the verified valid-solution stop (PATH B) never passes through this state. On PATH A the range closes (`coverage_state = searched`, `custody_status = completed`). | Preamble; Scope §E |
| LOW_POWER_LISTEN | Miner state (5 of 8) | Miner monitors round progress at reduced power rather than hashing; contributes to P_listen·t_listen and NOT to the active hash rate. | Preamble; Scope §B.1, §E |
| WAKING | Miner state (6 of 8) | Transitional state entered when leaving a reduced-power state to resume hashing; incurs wake latency and the P_wake·t_wake and E_transition terms. | Preamble; Scope §B.3, §E |
| OFFLINE | Miner state (7 of 8) | Miner is not participating; contributes to the P_offline·t_offline term and not to the active hash rate. | Preamble; Scope §E |
| DISQUALIFIED | Miner state (8 of 8) | Miner has been excluded from participation; produces no valid contribution to the round. | Preamble; Scope §E |
| stop_reason | Transition-reason enum | The mandatory reason recorded on every entry into `LOW_POWER_LISTEN`, exactly one of `{RANGE_EXHAUSTED, ASSIGNMENT_REVOKED, VALID_SOLUTION_VERIFIED, ROUND_ACCEPTED, ROUND_ABORTED}` (amended I4). No unverified certificate may cause the transition. | This document (§1) |
| PATH A | Transition path (range exhaustion) | The local range-exhaustion stop: own assigned range fully searched with no valid solution found, `ACTIVE_HASHING → EXHAUSTED_PENDING → LOW_POWER_LISTEN`, `stop_reason = RANGE_EXHAUSTED`. The range is closed (`coverage_state = searched`, `custody_status = completed`). The ONLY path through `EXHAUSTED_PENDING`. | This document (§1) |
| PATH B | Transition path (verified valid-solution stop) | The verified valid-solution stop: after validating a valid early-stop certificate for the current round, `ACTIVE_HASHING → LOW_POWER_LISTEN` **directly**, `stop_reason = VALID_SOLUTION_VERIFIED`. MUST NOT pass through `EXHAUSTED_PENDING`; during verification the miner stays in `ACTIVE_HASHING`, entering `LOW_POWER_LISTEN` only after all validation steps pass. The assignment is PAUSED, not searched or exhausted. | This document (§1) |
| PAUSED assignment | Assignment status | The status of an assignment after a PATH B valid-solution stop: **resumable** and NOT searched or exhausted. The retained `actual_frontier` is preserved and no unsearched positions are credited as searched. If the full block is later rejected, unavailable, or times out, the miner resumes from the retained `actual_frontier` (`LOW_POWER_LISTEN → WAKING → ACTIVE_HASHING`), with wake and transition energy fully accounted. | This document (§1) |
| ROUND_INITIALISING | Round state (1 of 10) | Round is being set up prior to template commitment. | Preamble; Scope §E |
| TEMPLATE_COMMITMENT | Round state (2 of 10) | The common immutable block template is committed and its TemplateID fixed for the round. | Preamble; Scope §E |
| ASSIGNMENT | Round state (3 of 10) | Disjoint nonce ranges are assigned (or leased) to participating miners. | Preamble; Scope §E |
| HASHING | Round state (4 of 10) | Miners search their assigned ranges against the committed target. | Preamble; Scope §E |
| SECURITY_RECOVERY | Round state (5 of 10) | Round is restoring active honest hash rate toward the security floor after a shortfall; associated with security-floor monitoring. | Preamble; Scope §B.4, §E |
| SOLUTION_PROPAGATION | Round state (6 of 10) | A candidate valid solution is being propagated for acceptance. | Preamble; Scope §E |
| ROUND_ACCEPTED | Round state (7 of 10) | A valid solution has been accepted and accepted-block handling has closed the round. | Preamble; Scope §A.6, §E |
| ROUND_EXHAUSTED | Round state (8 of 10) | The nonce domain coverage is exhausted without an accepted solution under the committed template. | Preamble; Scope §E |
| TEMPLATE_REFRESH | Round state (9 of 10) | The committed template is replaced by a new immutable template with a new TemplateID. | Preamble; Scope §A.7, §E |
| ROUND_ABORTED | Round state (10 of 10) | The round is terminated without acceptance or normal exhaustion. | Preamble; Scope §E |
| Active hash rate | H_active(t) [hash/s] | Total hash rate contributed at time t by miners in ACTIVE_HASHING only. No other miner state contributes to it. | Preamble; Scope §0.3 |
| Honest hash rate | H_honest(t) [hash/s] | The portion of active hash rate contributed by honest (protocol-following) miners at time t. | This document (§1) |
| Adversarial hash rate | H_adversarial(t) [hash/s] | The portion of active hash rate contributed by adversarial miners at time t. | This document (§1) |
| Adversarial share | q_adv(t) [dimensionless, 0..1] | Fraction of active hash rate that is adversarial: q_adv(t) = H_adversarial(t) / (H_honest(t) + H_adversarial(t)). Undefined/NA when H_active(t) = 0 — a security-floor breach is recorded, not treated as zero (I17). | This document (§1) |
| I17 hash-rate identity | Invariant (hash-rate decomposition) | For every event-update time, `H_active(t) = H_honest(t) + H_adversarial(t)` exactly. After miner states are determined, all three quantities are computed **deterministically** from the `ACTIVE_HASHING` census; `H_adversarial` is never sampled independently once `H_active` is known. When `H_active(t) = 0`, `q_adv(t)` is undefined/NA and a security-floor breach is recorded — not treated as zero. | This document (§1) |
| Security floor | Modeled bound | A modeled lower bound on active honest hash rate that participation reduction must not violate. Monitored by the protocol; its enforcement soundness is out of scope at Stage 1. | Scope §B.4, §C |
| Reserve miner | Miner in RESERVE | A registered miner held in RESERVE: available but not actively hashing, promotable to ACTIVE_HASHING when needed. | Scope §B.2 |
| Wake latency | Duration [s] | The delay a miner incurs while in WAKING before it resumes ACTIVE_HASHING after leaving a reduced-power state. | Scope §B.3 |
| Transition | Event / energy term | A change of miner state that carries a transition energy cost E_transition,i (e.g. entering/leaving low-power or waking). | Scope §0.3, §B.3 |
| Coordination energy | E_coordination,i [J] | Per-miner energy attributed to protocol coordination (assignment, leasing, commitments, certificates), distinct from the eight state-residency energies and from the transition (`E_transition`) and verification (`E_verification`) event terms. | Scope §0.3 |
| E_verification | E_verification,i [J] | Separate per-miner event-energy term for verifying an early-stop certificate, added on top of the `ACTIVE_HASHING` residency energy and NOT folded into `P_hash·t_hash` (so not double-counted). A verifying miner remains in `ACTIVE_HASHING`; no `VERIFYING` state exists. | This document (§1) |
| Residency power (per state) | P_state [W] | One residency power per miner state (state-to-power mapping): `P_registered`, `P_reserve`, `P_hash`, `P_listen`, `P_wake`, `P_offline`, ordered `P_offline ≤ P_listen = P_reserve = P_registered ≤ P_hash`, with `P_wake` a transient. No numeric values at Stage 1. Per-miner energy is `E_i = Σ_s (P_{i,s}·t_{i,s}) + E_transition,i + E_coordination,i + E_verification,i` over the eight states, `Σ_s t_{i,s} = T`, no residual. | This document (§1) |
| P_registered | Residency power [W] | Residency power of a `REGISTERED` miner; equals `P_listen`. Does not contribute to `H_active(t)`. | This document (§1) |
| P_reserve | Residency power [W] | Residency power of a `RESERVE` miner: low-power standby equal to `P_listen`, NOT `P_offline`. Does not contribute to `H_active(t)`. | This document (§1) |
| P_hash | Residency power [W] | Residency power of an `ACTIVE_HASHING` miner (and of the transient `EXHAUSTED_PENDING`); the only residency power whose state contributes to `H_active(t)`. | This document (§1) |
| P_listen | Residency power [W] | Residency power of a `LOW_POWER_LISTEN` miner, and the shared low-power level for `REGISTERED` and `RESERVE`. | This document (§1) |
| P_wake | Residency power [W] | Transient residency power of a `WAKING` miner while resuming hashing. | This document (§1) |
| P_offline | Residency power [W] | Residency power of an `OFFLINE` (or `DISQUALIFIED`) miner. | This document (§1) |
| Progress commitment | Attestation object | A miner-emitted attestation of how far its assigned range has been searched. Treated ONLY as a modeled progress-verification abstraction. A progress commitment (`ProgressCommit`) updates the `reported_*` layer ONLY and never the normative I8a (accepted) searched measure. | Scope §B.7 |
| Modeled progress-verification abstraction | Bounded term | The bounded, Stage-1 term for progress commitments and reported range-exhaustion claims. It is explicitly NOT a cryptographic proof and NOT a proof of range exhaustion. Early-stop certificates are a SEPARATE mechanism (generated only from a found valid solution, CR1) and are NOT part of this abstraction. | Preamble; Scope §B.7, §C |
| Checkpoint frontier | Progress marker | The boundary between the searched prefix and the unsearched suffix of a range, as attested by progress commitments; the modeled position up to which coverage is claimed (the **reported** layer, i.e. `reported_frontier`; NOT the accepted I8a measure). | This document (§1) |
| actual_frontier | Simulator ground truth | The true position up to which a range has actually been searched (simulator ground truth, CR5); distinct from `reported_frontier` and `accepted_frontier`. Coverage layer 1 of 3. | This document (§1) |
| actual_searched | Simulator ground truth | Positions actually searched per simulator ground truth (bounded by `actual_frontier`). Ground-truth layer; NOT the normative I8a measure (which uses `accepted_searched`). | This document (§1) |
| actual_positions_evaluated | Simulator ground truth | The true count of nonce positions actually evaluated by a miner. | This document (§1) |
| actual_solution_positions | Simulator ground truth | The true positions that actually satisfy the target within a range. | This document (§1) |
| actual_exhaustion | Simulator ground truth | Whether a range was actually exhausted. The simulator MAY know this exactly; the modeled progress-verification abstraction does NOT prove it. | This document (§1) |
| reported_frontier | Protocol-level claim | The frontier a miner reports having searched — a claim subject to audit, not ground truth; distinct from `actual_frontier` and `accepted_frontier`. Coverage layer 2 of 3. Updated by `ProgressCommit`. | This document (§1) |
| reported_searched | Protocol-level claim | Positions a miner reports as searched (bounded by `reported_frontier`) — a claim subject to audit. Updated by a progress commitment (`ProgressCommit`) ONLY; it is NOT the normative I8a measure and never drives coverage_state on its own. | This document (§1) |
| reported_exhaustion | Protocol-level claim | A miner's reported claim of range exhaustion — subject to audit, not a proof that no valid solution exists in the range. | This document (§1) |
| audit_selected | Protocol-level claim | Whether a reported claim was selected for audit under the modeled audit abstraction. | This document (§1) |
| audit_result | Protocol-level claim | The outcome of the modeled audit of a reported claim (compared against ground truth in adversarial simulations). | This document (§1) |
| claim_accepted_or_rejected | Protocol-level claim | Whether the reported claim was accepted or rejected after audit. All such findings are modeled, not cryptographically proven. | This document (§1) |
| accepted_frontier | Adjudicated coverage | The frontier up to which coverage has been ADJUDICATED as accepted; distinct from `actual_frontier` and `reported_frontier`. Coverage layer 3 of 3. Only `accepted_frontier` promotes `coverage_state` to `searched`; `ProgressCommit` never updates it. | This document (§1) |
| accepted_searched | Adjudicated coverage | Positions counted as searched under ACCEPTED adjudication (bounded by `accepted_frontier`). **This is the coverage the normative I8a measure uses:** `accepted_searched + active_unsearched + inactive_unsearched = assigned_domain`. Honest-mode runs may set accepted = ground truth by explicit model rule; adversarial-mode runs promote reported → accepted only after the modeled audit/detection adjudication. | This document (§1) |
| Accepted reported exhaustion under the modeled audit abstraction | Protocol-level claim outcome | The canonical phrase for an adversarial-path `reported_exhaustion` accepted after comparison with simulator ground truth through the modeled audit/detection abstraction. It is NEVER a cryptographic proof or a verified actual exhaustion. | This document (§1) |
| Early-stop certificate | Certificate object | A certificate generated ONLY after a miner finds a valid candidate solution satisfying the current target; it contains exactly RoundID, TemplateID, AssignmentID, MinerID, nonce, candidate_hash, target, signature/authentication. It is NOT generated from progress commitments, searched-domain coverage, claimed exhaustion, or a progress frontier (CR1); progress verification and early-stop certification are completely separate mechanisms. Carries no security or soundness guarantee at Stage 1. | Scope §B.8, §C |
| Target | Threshold value | The acceptance threshold for a round: a solution is valid only if its digest satisfies the target under the committed template. | Scope §A.5 |
| arrival_time | Reproducible time [s] | The reproducible propagation/arrival time assigned to a valid solution. Under network-arrival semantics (CR6) local acceptance takes the earliest valid arrival; only exact arrival-time ties break by smallest `candidate_hash`, then smallest `MinerID`. | This document (§1) |
| Competing / stale proposal | Solution classification | A valid solution not accepted because another valid solution had an earlier arrival; recorded as `competing`/`stale`. No chain-wide fork-choice proof is claimed. | This document (§1) |
| Difficulty | Fixed parameter | The parameter determining how hard the target is to satisfy. In the confirmatory design difficulty stays FIXED; dynamic-difficulty behavior is out of scope and not confirmed. | Preamble; Scope §C |
| Template refresh | Procedure / round state | Replacement of the committed immutable template with a new immutable template (new TemplateID), transitioning through TEMPLATE_REFRESH. The only sanctioned way mined content changes. | Scope §A.7 |
| Continuous full-participation control | Baseline scenario | The reference scenario in which all miners hash continuously over the fixed horizon. Its modeled energy is the A1 value, 8.420833333 kWh, and serves as E_continuous_control. | Preamble; Scope §0.2, §D |
| ΔE | ΔE [kWh] | The Stage-1 comparison quantity ΔE = E_continuous_control − E_idle_policy. Defined at Stage 1; no particular achieved value is claimed. Any positive ΔE must arise from reduced active power-time, never from partitioning. It decomposes as `Delta_E_total = Delta_E_range_idle + Delta_E_reserve + Delta_E_early_stop − Delta_E_transition_and_wake − Delta_E_coordination_and_verification`. | Preamble; Scope §0.3, §D |
| Delta_E_range_idle | Energy-reduction term [kWh] | Saving from miners exhausting their assigned ranges and entering `LOW_POWER_LISTEN`. | This document (§1) |
| Delta_E_reserve | Energy-reduction term [kWh] | Saving from holding reserve miners outside active hashing (at `P_reserve`). | This document (§1) |
| Delta_E_early_stop | Energy-reduction term [kWh] | A propagation/termination optimisation (stopping once a valid solution arrives); NOT unique to nonce-domain partitioning. | This document (§1) |
| Delta_E_transition_and_wake | Energy-cost term [kWh] | Cost of wake and state transitions; subtracted from total saving. | This document (§1) |
| Delta_E_coordination_and_verification | Energy-cost term [kWh] | Cost of coordination and early-stop verification (`E_coordination` + `E_verification`); subtracted from total saving. | This document (§1) |
| Zero-block run | Run classification | A modeled run in which no block is accepted over the horizon (e.g. resolving to ROUND_EXHAUSTED without acceptance), so block-normalised metrics have no accepted block to normalise against. | This document (§1) |
| NA (undefined block-normalised metric) | Sentinel value | The sentinel recorded for a block-normalised metric that is undefined because the run produced zero accepted blocks; NA denotes "undefined", not zero. | This document (§1) |
| Physical run | Run classification | A modeled run evaluated under the physical/energy accounting (real-power-time terms of the energy model), as opposed to a purely abstract or block-normalised view. | This document (§1) |
| Master seed | Seed value | The root seed from which per-run allocation randomness is derived deterministically, so that assignment/allocation draws are reproducible across runs. | This document (§1) |
| Allocation exponent | alpha (α) [dimensionless] | The exponent parameter governing the shape of the range-allocation distribution across miners (e.g. how range sizes scale). A modeled allocation parameter; carries no fairness or incentive claim at Stage 1. | This document (§1) |
| Reward eligibility | Interface field (deferred) | **NOT SPECIFIED AT STAGE 1 (a valid solution may be recorded as having a solver identity)**. All reward and penalty components are deferred to Stage 5; Stage 1 assigns no reward eligibility (no idle credit, availability reward, work reward, winner reward, or penalty). See `STAGE_01_REWARD_PENALTY_INTERFACE.md`. | This document (§1) |
| Solver identity | Recorded attribute | The `MinerID` recorded as having produced a valid solution. Recording a solver identity is the ONLY reward-related fact at Stage 1; it does NOT assign reward eligibility (which is NOT SPECIFIED AT STAGE 1). | This document (§1) |

---

## 2. Consistency notes

- **Active hash rate is state-restricted.** Only `ACTIVE_HASHING` miners contribute to
  `H_active(t)`, and correspondingly `H_active(t) = H_honest(t) + H_adversarial(t)` over the
  active-hashing population. `LOW_POWER_LISTEN`, `RESERVE`, `WAKING`, `OFFLINE`,
  `EXHAUSTED_PENDING`, `REGISTERED`, and `DISQUALIFIED` contribute nothing to the active
  hash rate.
- **Energy attribution matches the state-complete model.** The energy model of Scope §0.3 is
  state-complete: one residency power per miner state, summed over the **eight** states, with
  `Σ_s t_{i,s} = T` and no residual bucket —
  `E_i = Σ_s (P_{i,s}·t_{i,s}) + E_transition,i + E_coordination,i + E_verification,i`. Each state
  maps to exactly one residency power: `REGISTERED → P_registered (= P_listen)`;
  `RESERVE → P_reserve (= P_listen)`; `ACTIVE_HASHING → P_hash`;
  `EXHAUSTED_PENDING → P_hash` (transient); `LOW_POWER_LISTEN → P_listen`; `WAKING → P_wake`;
  `OFFLINE → P_offline`; `DISQUALIFIED → P_offline`. The event terms `E_transition`,
  `E_coordination`, and `E_verification` are added on top of the residency energies and are not
  double-counted.
- **Modeled abstractions only.** "Progress commitment" and "checkpoint frontier" are instances of the modeled
  progress-verification abstraction; neither is a cryptographic proof and neither establishes
  range exhaustion. The "early-stop certificate" is a SEPARATE mechanism, generated only from a
  found valid solution (CR1), and is NOT an instance of the progress-verification abstraction,
  security, or incentive properties at Stage 1 (Scope §C).
- **Three coverage layers; I8a uses accepted only.** Coverage is tracked at three separate
  layers — `actual_frontier`/`actual_searched` (ground truth), `reported_frontier`/
  `reported_searched` (claim), and `accepted_frontier`/`accepted_searched` (adjudicated). A
  progress commitment (`ProgressCommit`) updates the `reported_*` layer ONLY. The normative
  I8a measure uses **accepted** coverage only: `accepted_searched + active_unsearched +
  inactive_unsearched = assigned_domain`; only an ACCEPTED adjudication promotes
  `coverage_state` to `searched`.
- **Reward eligibility is deferred.** Reward eligibility is **NOT SPECIFIED AT STAGE 1**; all
  reward/penalty components are deferred to Stage 5. The single reward-related fact recorded
  at Stage 1 is that a valid solution may be recorded as having a solver identity. This
  wording is consistent across `STAGE_01_REWARD_PENALTY_INTERFACE.md`,
  `STAGE_01_RESERVE_POLICY_SPECIFICATION.md`, `STAGE_01_IDLE_POLICY_SPECIFICATION.md`, and
  `STAGE_01_PROTOCOL_SCOPE.md`.
- **A1 discipline.** `continuous full-participation control` equals the A1 value
  (8.420833333 kWh). `ΔE` is measured against this baseline and any reduction is
  attributable to reduced active power-time, never to nonce-domain partitioning.

## Stage-1G terminology addendum (concurrency & causal-consistency)

- **Discovery-time eligibility (I2, corrected in G1).** Acceptance binds a solution to the
  IMMUTABLE assignment version that was VALID and `CURRENT` at the solution's `discovery_time` and
  resolvable from its `SolutionEligibilitySnapshot`. The version need NOT be `CURRENT` at certificate
  or block arrival (it may be `PAUSED` or `SUPERSEDED`). "`CURRENT` at acceptance" is NOT used.
- **Assignment version / lineage / live head (I18a/I18b, G2).** An `Assignment` is an immutable
  versioned object with a stable `lineage_id`. `I18a`: at most one `CURRENT` version per lineage (zero
  is legal). `I18b`: each OPEN lineage has exactly one live head in `{PENDING, CURRENT, PAUSED}`; a
  CLOSED lineage has none. Renewal (`RenewAssignment`) is the sole in-lineage continuation and is
  atomic at `renewal_time`; `ORIGINAL`/`REASSIGNED` open FRESH lineages.
- **Candidate propagation context / status.** `CandidatePropagationContext` (CPC) has a DETERMINISTIC
  `CandidateID = (RoundID, candidate_discovery_seq)` and `PropagationID = (CandidateID,
  propagation_attempt_seq)` (G7). Status: `DISCOVERED → SELF_VALIDATED → PROPAGATING →
  PENDING_ACCEPTANCE → {ACCEPTED | FAILED}` plus `COMPETING`/`STALE`/`CANCELLED`. `active_propagation_set`
  holds ONLY `{PROPAGATING, PENDING_ACCEPTANCE}` contexts (G6).
- **Microphases (G5).** The per-timestamp ordering: terminal closure → template refresh → collect all
  block arrivals → `AcceptanceBatchFinalize` (one atomic arbitration+closure) → security-floor
  evaluation (terminal-guarded) → certificate/discovery/… events. `BlockAcceptancePoint` only
  registers; round-acceptance closure is the atomic result of `AcceptanceBatchFinalize`.
- **Central state hook / event-scheduled hashing / compute-only census.** `ApplyMinerStateTransition`
  is the sole writer of `miner_state` (F6). Hashing is a chain of `HashWorkEvent`s (`StartHashing` /
  `ScheduleNextHashWork`), non-blocking (G9). `ActiveHashRateUpdate` is compute-only;
  `AdversarialParticipationChangeEvent` carries each modeled adversarial entry/exit through the hook
  (G3). `SecurityFloorEvaluate` is always scheduled and terminal-guarded (G10).

## Stage-1H terminology addendum (timestamp-causality lock)

- **`delta_cycle` and the event total order (H2).** Each discrete event carries an envelope
  `(event_time, delta_cycle, microphase, stable_tie_key, seq)`, ordered lexicographically, where
  `stable_tie_key = (CandidateID, MinerID, AssignmentID)`. `delta_cycle` is a same-`event_time`
  causal layer: a handler in microphase `m` of `delta_cycle k` may schedule a same-`event_time` event
  into cycle `k` if its target microphase is later than `m`, else into cycle `k+1` — NEVER backward
  into a completed microphase. The loop finishes all microphases of cycle `k` before any event of
  cycle `k+1` at the same `event_time`. The authoritative same-`event_time` contract is
  `STAGE_01G_EVENT_MICROPHASE_SPEC.md` **extended by this delta-cycle rule**; the frozen Stage-1F
  `STAGE_01F_EVENT_PRIORITY_TABLE.md` is NOT authoritative.
- **Single settled-census security evaluation (`FinalizeEventTimeSecurityCensus`, H3; renamed and relocated
  to the event-time epilogue by I-01/I-02; O5).** A miner transition never schedules its own floor decision;
  instead the coherent writers set `security_census_dirty[event_time]`. Exactly ONE
  `FinalizeEventTimeSecurityCensus` runs as the event-time EPILOGUE per settled `event_time` — **AFTER the
  whole `event_time` is quiescent** (never in a microphase placed before certificate/discovery events),
  keyed by `event_time` ALONE — reads the FINAL settled census, and calls `SecurityFloorEvaluate` at most
  once. Intermediate same-time census values are retained for AUDIT ONLY and never drive a round-state
  transition. (The superseded H3 name `FinalizeTimestampSecurityCensus` and its `(event_time, delta_cycle)`
  microphase-5 keying are no longer used, O5.)
- **Legal `SECURITY_RECOVERY` sources (H4).** `SecurityFloorEvaluate` may transition to
  `SECURITY_RECOVERY` ONLY from `{HASHING, SOLUTION_PROPAGATION, SECURITY_RECOVERY}`. From setup
  states (`ROUND_INITIALISING`/`TEMPLATE_COMMITMENT`/`ASSIGNMENT`), `TEMPLATE_REFRESH`,
  `ROUND_EXHAUSTED`, or a terminal round it records an observation-only result and performs NO
  transition.
- **Zero-latency wake (H5).** A wake with `wake_latency = 0` schedules its `WakeCompleteEvent` at the
  SAME `event_time` in `delta_cycle + 1` at the `WAKE_COMPLETE` microphase, so it never travels
  backward into a completed phase; a positive latency schedules a future `event_time`. The `WAKING`
  residency and its `P_wake·t_wake + E_transition` accounting path always exist (D2).
- **State-specific adversarial entry/exit (H6).** Entry: `REGISTERED`/`RESERVE` → bind fresh `PENDING`
  + `StartWake`; `OFFLINE` → hook `OFFLINE→REGISTERED` first, then bind + wake; a still-`PAUSED`
  `LOW_POWER_LISTEN` head → resume its OWN head via `ResumeFromPause` (matched ids, never `RangeAssign`);
  a post-closure `LOW_POWER_LISTEN` → fresh `ORIGINAL` head + `StartWake` (T10). Exit acts ONLY on
  `ACTIVE_HASHING`: preserve accepted coverage, expose only the accepted unsearched suffix, record the
  I9 reason/provenance, cancel the version's pending `HashWorkEvent`s, close the `CURRENT` head
  explicitly (no live head remains), depart via T11 — all through the hook.
- **Residency single owner (`residency_ledger`, I19/H7).** Every per-miner `t_<state>` (including
  `t_ACTIVE_HASHING = t_hash`) is produced ONCE by the `residency_ledger` owned by
  `ApplyMinerStateTransition`, opened/closed at the state boundaries. A `HashWorkEvent` records
  hash-work METADATA only and adds ZERO duration, so no `ACTIVE_HASHING` interval is counted twice.
- **Explicit `assignment_ref` (H8).** `EnterLowPowerListen` receives the EXACT immutable assignment
  version being paused/exhausted/revoked/closed as `assignment_ref` (a live head in
  `{CURRENT, PAUSED}`); there is no undeclared free `assignment`. Every caller passes the precise
  version, so a `SUPERSEDED`/`CLOSED` historical version can never be paused or closed by accident.

## Stage-1I terminology addendum (execution-contract lock)

- **Event-time security epilogue (I-01/I-02).** The single security-floor decision is keyed by
  `event_time` ALONE, not by `(event_time, delta_cycle)`. `ApplyMinerStateTransition` sets
  `security_census_dirty[event_time]` and OVERWRITES `latest_security_census[event_time]` with the
  newest post-transition census. After the whole `event_time` is quiescent, `ProcessEventTime` runs the
  EPILOGUE `FinalizeEventTimeSecurityCensus(event_time)` exactly once, deciding from
  `latest_security_census[event_time]`. Because it is an epilogue (not a queued microphase event) it
  cannot be missed when no later event exists, and no intermediate delta-cycle census can strand a
  pending decision or independently trigger recovery.
- **`ProcessEventTime` / quiescence (I-02).** The event-loop driver that DRAINS every ordinary and
  delta-cycle event at one `event_time` (in `(delta_cycle, microphase, stable_tie_key, seq)` order,
  including handler-generated same-time events) BEFORE running the security epilogue and marking the
  `event_time` finalised. No ordinary event may be scheduled into a finalised `event_time`; any
  participation-changing action from the security decision is scheduled at a STRICTLY LATER
  `event_time`, so it cannot alter `H_active` after the final decision at this timestamp.
- **`TransitionEventID` (I-03).** The immutable identity of ONE applied transition:
  `(event_time, delta_cycle, seq, MinerID, old_state, new_state, reason, AssignmentID,
  assignment_version, CandidateID?, PropagationID?)`. `ApplyMinerStateTransition` suppresses ONLY an
  exact-same-`TransitionEventID` replay; a legitimate repeat of the SAME state edge for the SAME miner
  at the SAME `event_time` in a DIFFERENT `delta_cycle` has a DISTINCT id and is applied (not
  suppressed). Recorded in `transition_audit`.
- **Runtime registries (I-04).** `RoundInitialise` explicitly initialises and returns every normative
  registry; none is an implicit global. Per-ROUND registries (`active_propagation_set`,
  `acceptance_batch_registry`, `candidate_discovery_seq`, `block_accepted`, `state_version`,
  `residency_ledger`) reset each round; per-RUN event-loop bookkeeping (`security_census_dirty`,
  `latest_security_census`, `transition_event_registry`, `finalised_event_times`,
  `current_delta_cycle`) is initialised once at run start and preserved across rounds.
- **Terminal-first / persistent-recovery security (I-05).** `SecurityFloorEvaluate` returns
  `terminal_stale_noop` for `ROUND_ACCEPTED`/`ROUND_ABORTED` BEFORE any breach recording. Recovery is
  entered ONLY via `HASHING → SECURITY_RECOVERY` or `SOLUTION_PROPAGATION → SECURITY_RECOVERY`. A
  breach that persists while already in `SECURITY_RECOVERY` records `breach_persists` with NO
  `SECURITY_RECOVERY → SECURITY_RECOVERY` self-transition and NO `state_version` bump.
- **State-specific low-power re-entry (I-06).** Adversarial re-entry of a `LOW_POWER_LISTEN` miner is
  split by `entry_stop_reason`: `VALID_SOLUTION_VERIFIED` resumes the own PAUSED head via
  `ResumeFromPause`; `RANGE_EXHAUSTED`/`ASSIGNMENT_REVOKED` create a fresh T10 assignment ONLY in a
  nonterminal, non-refreshing, committed-eligible-template round whose policy permits a range;
  `ROUND_ACCEPTED`/`ROUND_ABORTED` create NO assignment or wake in the closed round (deferred to the
  next round); a `TEMPLATE_REFRESH` round defers to the new-template assignment procedure.
- **Canonical custody enum + `revocation_reason` (I-07).** `custody_status` takes ONLY a value from the
  canonical enum `{original, renewed, reassigned, revoked, expired, abandoned, completed,
  superseded_by_template_refresh}`. An adversarial withdrawal sets `custody_status = revoked` and
  `revocation_reason = adversarial_withdrawal`; it NEVER invents a custody value such as
  `revoked_adversarial_exit`. The cause lives in the separate `revocation_reason` field.

## Stage-1J terminology addendum (implementation-handoff lock)

- **Security-census coherence (J1).** `ApplyMinerStateTransition` is the SOLE writer of
  `security_census_dirty[event_time]` and `latest_security_census[event_time]`, and writes them TOGETHER
  atomically. INVARIANT: `security_census_dirty[t] = true ⇒ latest_security_census[t] exists`.
  `FinalizeEventTimeSecurityCensus` asserts this before reading. Candidate failure
  (`HandlePropagationFailure`) sets NO dirty flag — it changes no `ACTIVE_HASHING` census; only the later
  re-activation boundaries do, through the hook.
- **Replay-before-precondition (J2).** In `ApplyMinerStateTransition` the `TransitionEventID` replay guard
  is evaluated FIRST; an exact replay returns `duplicate_suppressed` WITHOUT reading `old_state` and
  WITHOUT charging energy. The `old_state = miner_state(MinerID)` precondition is checked only for a
  non-replay (a replay necessarily arrives after the first event already changed `miner_state`).
- **Complete transition envelope (J3).** `ApplyMinerStateTransition` receives/resolves the full envelope
  including explicit `candidate_id` AND `propagation_id` (replacing the ambiguous `candidate_ref`); every
  candidate-triggered caller passes BOTH. `TransitionEventID` therefore distinguishes two propagation
  attempts of one `CandidateID` (different `PropagationID`).
- **`event_creation_seq` (J4).** The ONE per-run monotonic event-creation counter, owned SOLELY by the
  central scheduler `ScheduleEvent`, assigned atomically after deterministic ordering; it is the `seq`
  in every event envelope and every `TransitionEventID`. Initialised once at run start, preserved across
  rounds (I-04). No ambient undeclared seq exists.
- **`PrepareParticipantsForNewRound` (J5).** The named `ASSIGNMENT`-phase procedure that gives every
  eligible miner a legal new-round path (REGISTERED→T3, RESERVE→T4, `LOW_POWER_LISTEN` parked by
  `ROUND_ACCEPTED`/`ROUND_ABORTED`→fresh `ORIGINAL` under the new `RoundID`/`TemplateID` via T10),
  establishing the intended assignment set BEFORE `ASSIGNMENT → HASHING` (R4). It never reopens a CLOSED
  old-round assignment.
- **Floor applicability before breach (J6).** `SecurityFloorEvaluate` checks round-state applicability
  BEFORE evaluating thresholds: setup/refresh/exhausted states record only a `security_census_observation`
  (no I16 breach event); only `HASHING`/`SOLUTION_PROPAGATION`/`SECURITY_RECOVERY` record breaches.
- **Canonical terminal status (J7).** `SUPERSEDED` is used ONLY for atomic same-range renewal; `CLOSED`
  is the terminal status for every non-renewal end-of-life (revocation, adversarial withdrawal,
  abandonment, wake failure, cancellation, round closure, template closure). There is no ambiguous
  "CLOSE/SUPERSEDE"; a CLOSED lineage has zero live heads (I18b).
- **Security-census provenance (J8).** `latest_security_census[event_time]` carries the epoch it was
  PRODUCED under (`RoundID_at_census`, `TemplateID_at_census`, `state_version_at_census`, `census_seq`)
  plus the census values. The epilogue passes the STORED provenance to `SecurityFloorEvaluate`; a
  stale-context census records `stale_census_observation` and never triggers recovery in the new
  round/template.
- **Central scheduler `ScheduleEvent` (J9).** The sole event-enqueue interface: it rejects a finalised
  `event_time`, assigns `event_creation_seq`, applies the delta-cycle forward rule, attaches
  `RoundID`/`TemplateID` and the candidate envelope fields, and inserts by the deterministic total-order
  key. Every `SCHEDULE` in the specification is shorthand for a `ScheduleEvent` call.

## Stage-1K terminology addendum (core-handoff closure)

- **Complete next-round eligibility (K1).** `PrepareParticipantsForNewRound` gives EVERY parked
  `LOW_POWER_LISTEN` miner an explicit next-round disposition for all five stop reasons; a
  `VALID_SOLUTION_VERIFIED` finder/recipient is archived, its old head confirmed CLOSED, and re-assigned
  a fresh `ORIGINAL` under the NEW `RoundID`/`TemplateID` via T10 (never reopening a PAUSED/CLOSED head).
- **`CompleteAssignmentPhase` (K2).** The named procedure that performs the executable `ASSIGNMENT →
  HASHING` transition (R4) after the intended assignment set is built; a `HashWorkEvent` is a no-op while
  the round is still `ASSIGNMENT`.
- **Cross-round residency rebase (`FinalizeRoundResidency`/`BeginRoundResidency`, K3; SUPERSEDED by L5).**
  A state that persists across a round boundary is closed for the old round and reopened at the IDENTICAL
  `boundary_time` for the new round with NO transition energy; the idle interval is counted exactly once
  (I19 amended). **L5 supersedes the two-procedure form with the single idempotent owner
  `RebaseResidencyAtRoundBoundary` (see the Stage-1L addendum).**
- **`DriverEventEnvelope` (K4).** The explicit `(event_time, delta_cycle, event_seq)` a sim-driver
  transition carries so it is never ambient; sourced from `ScheduleEvent` or stamped from the
  `EventQueueContext`.
- **Applied-transition registry (K5).** A `TransitionEventID` enters `applied_transition_registry` ONLY
  inside `ApplyMinerStateTransition`'s atomic apply; a suppressed replay or a rejected (stale/illegal/
  malformed) transition is never registered — rejections go to `transition_rejection_log`.
- **Canonical lease termination (`termination_reason`, K6).** Lease expiry closes the CURRENT version
  canonically (`status = CLOSED`, `custody_status = expired`, `termination_reason = lease_expiry`); there
  is NO undefined `INVALIDATE` state. `SUPERSEDED` remains renewal-only; I18a/I18b hold throughout.
- **`CaptureSecurityCensusOnApplicabilityEntry` (K7).** The second coherent writer of the security
  census; invoked on entry to `HASHING` (by `CompleteAssignmentPhase`) and `SOLUTION_PROPAGATION`, it
  writes a coherent dirty+latest even when no miner boundary occurred (e.g. `H_active = 0`), so the
  epilogue evaluates the floor. It never runs while the round is `ASSIGNMENT`.
- **`EventQueueContext` (K8; extended L1).** The single explicit dispatch/scheduling state (`event_queue`,
  `current_event_time`, `current_delta_cycle`, `current_microphase`, `current_event_seq` (L1),
  `event_creation_seq`, `finalised_event_times`, `rebased_boundaries` (L5)). `ScheduleEvent` DERIVES the
  target `delta_cycle` from it; a caller supplies only `event_time` + `microphase` and cannot override
  `delta_cycle`.

## Stage-1L terminology addendum (final contract reconciliation)

- **`dispatch_envelope` (L1).** The ONE `(event_time, delta_cycle, event_seq)` of the event currently being
  handled, materialised by `ProcessEventTime` from the dispatched event's own enqueued envelope and exposed
  identically as the `EventQueueContext` current-dispatch fields (`current_event_time`,
  `current_delta_cycle`, `current_event_seq`). Every synchronous miner transition and every `StartWake` done
  while handling the event BINDS its envelope from `dispatch_envelope`; queued handlers thread their own,
  and sim-driver entry points (`MinerRegister`, `PrepareParticipantsForNewRound`, `ReserveActivate`, …) are
  themselves seated on the queue through `ScheduleEvent` and receive it on dispatch. A driver entry point
  NEVER manually stamps `next EQ.event_creation_seq` (the K4 manual-stamp alternative is withdrawn); the seq
  is owned solely by `ScheduleEvent`. No `ApplyMinerStateTransition` call omits any of the three fields.
- **Single `ASSIGNMENT → HASHING` owner (L2).** `CompleteAssignmentPhase` is the SOLE executable
  `ASSIGNMENT → HASHING` (R4) step: both `PrepareParticipantsForNewRound` and `TemplateRefresh` route
  through it (the former in-line `TRANSITION round_state -> HASHING` in `TemplateRefresh` is removed). The
  `SOLUTION_PROPAGATION → HASHING` re-entry is a DISTINCT round-SM edge, not an assignment-phase completion.
- **Canonical discovery-before-lease-expiry order (L3).** When a solution discovery and a lease expiry share
  an `event_time`, discovery (priority item 7) is processed BEFORE lease expiry (item 10) — the one
  canonical order, agreeing across `§0.7`, the priority table, and `STAGE_01G_EVENT_MICROPHASE_SPEC.md §4`.
  A boundary discovery captures its immutable snapshot against the still-`CURRENT` head before that head's
  lease can expire; the reverse order is forbidden. No corpus statement places lease expiry first.
- **Status-aware lease expiry (L4).** `LeaseExpiry` branches on the canonical status of the exact expiring
  version: `SUPERSEDED`/`CLOSED` → stale no-op; `CURRENT` → renew (F7) or canonical CLOSE (K6) then reassign;
  `PAUSED` → CLOSE the paused head without a wake then reassign; `PENDING` → CLOSE the un-activated head then
  reassign. Every reassignment path CLOSES the source FIRST, so `RangeReassign` asserts
  `status(source) = CLOSED`. `SUPERSEDED` remains renewal-only.
- **`RebaseResidencyAtRoundBoundary` (L5; RENAMED/GENERALISED to `SettleResidencyBoundary` in M4).** The
  SINGLE idempotent owner of the cross-round residency rebase (superseding `FinalizeRoundResidency`/
  `BeginRoundResidency`). It closes the old-round interval and reopens the same state at the identical
  `boundary_time = round_terminal_time` with NO transition energy, idempotent via `boundary_id` (a repeat is
  a no-op). **M4 renames it `SettleResidencyBoundary` and adds a `FINAL_RUN_END` mode (see the Stage-1M
  addendum).** `CloseRoundAssignments` records `round_terminal_time` ONLY; the idle interval is counted once (I19).
- **`ScheduleEvent` sole delta-cycle authority (L6).** `ScheduleEvent` is the ONLY authority over
  `delta_cycle`: no `SCHEDULE` expression, `ScheduleEvent` argument, or handler supplies or overrides one;
  every `delta_cycle` shown is the value `ScheduleEvent` derived (or the `dispatch_envelope.delta_cycle` read
  back at dispatch). `StartWake` schedules `WakeCompleteEvent` with ONLY `(target_event_time,
  target_microphase)`: positive latency → `now + wake_latency`; zero latency → `now` at `WAKE_COMPLETE`.

## Stage-1M terminology addendum (minimal executable closure)

- **Explicit `dispatch_envelope` threading; no shorthand (M1).** The Stage-1L positional shorthand is
  REMOVED: no `ApplyMinerStateTransition(..., now, reason=...)` form and no implicit read of
  `EQ.current_event_time/current_delta_cycle/current_event_seq`. EVERY procedure that directly or indirectly
  calls the hook carries an explicit `dispatch_envelope` input and threads it; every hook call spells out
  `event_time = dispatch_envelope.event_time`, `delta_cycle = dispatch_envelope.delta_cycle`,
  `event_seq = dispatch_envelope.event_seq`. A queued handler obtains its envelope from its own dispatched
  event; a synchronous nested procedure receives the same envelope as an explicit input.
- **`TransitionRoundState` — automatic applicability-entry census (M2).** The single round-state transition
  helper for every dispatched (non-epilogue) transition: it bumps `state_version` and, whenever the new
  state is floor-applicable (`HASHING`, `SOLUTION_PROPAGATION`, `SECURITY_RECOVERY`), calls
  `CaptureSecurityCensusOnApplicabilityEntry(at = dispatch_envelope.event_time)`. It makes EVERY entry into
  HASHING capture a census — including `HandlePropagationFailure`'s `SOLUTION_PROPAGATION → HASHING` re-entry,
  even with no paused miner, positive-latency resumes, or an unchanged `H_active`. The ONE exception is the
  `SecurityFloorEvaluate` epilogue's `→ SECURITY_RECOVERY` (re-dirtying a mid-epilogue event_time is forbidden).
- **Executable PENDING lease expiry + `WakeCompleteEvent` stale guard (M3).** `LeaseExpiry` `CASE PENDING`
  cancels the exact pending `WakeCompleteEvent`, moves a `WAKING` holder `WAKING → OFFLINE`
  (`reason = lease_expired_while_waking`, explicit envelope), CLOSES the head, and only then reassigns;
  `CASE PAUSED` also cancels candidate-specific resume/wake events. `WakeCompleteEvent` BEGINS with an explicit
  stale-target guard (`status ∈ {PENDING, PAUSED}`, current round/template epoch, the miner's own live head)
  returning `stale_wake_noop` — it does NOT rely on the `HashWorkEvent` G9 guard.
- **`SettleResidencyBoundary` (M4).** The SINGLE idempotent owner of BOTH the round-boundary rebase
  (`REBASE_TO_NEXT_ROUND`) and the run-end close (`FINAL_RUN_END`), keyed by `boundary_id`.
  `CloseRoundAssignments` performs NO residency/energy finalisation (the in-line finalise line is removed);
  it records `round_terminal_time` only. `RoundAbort` settles via `FINAL_RUN_END` before its I5/I6/I7 checks.
- **Canonical event-type → microphase mapping (M5).** Every operational enqueue is a `ScheduleEvent` call
  (or its `SCHEDULE` shorthand) supplying an EXPLICIT `target_microphase` from the §0.7g mapping
  (`FULL_BLOCK_ARRIVAL`, `CERTIFICATE_ARRIVAL`, `HASH_WORK`, `LEASE_EXPIRY`, `WAKE_COMPLETE`, `RESUME`,
  `PARTICIPATION_CHANGE`, `MONITORING`). No enqueue omits a microphase; every event-producing loop is stably
  sorted (`MinerID`, then `CandidateID`/`AssignmentID`) before the seq is assigned.

## Stage-1N terminology addendum (run-lifecycle & recovery closure)

- **Round abort vs. simulation end (N1).** `RoundAbort` terminates exactly ONE round: disposition
  candidates, close assignments, record `round_terminal_time` at the abort `event_time`, transition to
  `ROUND_ABORTED`, and return control so `RoundInitialise` may start another round when simulated time
  remains. It performs NO `FINAL_RUN_END` settle and NO horizon-`T` reconciliation.
- **`FinalizeSimulationRun` (N1; narrowed by O1 — see the Stage-1O addendum).** The SINGLE run-level
  finaliser, run EXACTLY ONCE at the fixed horizon `T`, guarded by the per-run `run_finalised` flag. It
  performs the ONE `SettleResidencyBoundary(mode = FINAL_RUN_END, boundary_id = (RunID, RUN_END))` (no
  reopen) and only THEN the I5/I6/I7 reconciliation. **O1 SUPERSESSION:** it is NO LONGER a queued event and
  NO LONGER drains the queue or closes a round itself — the drain is the run driver's (`RunEventLoopToHorizon`
  via `ProcessEventTime`) and the horizon-close of a nonterminal round is `CloseRoundAtHorizon`'s (§20b);
  `FinalizeSimulationRun` is invoked as a post-`ProcessEventTime(T)` RUN-LEVEL hook. An early `RoundAbort` at
  `t < T` never closes residency at `T`.
- **`CompleteSecurityRecovery` (N2/R13/R14).** The EXECUTABLE recovery-exit owner. Seated on the queue by
  the epilogue's floor-restored decision (§9, at a strictly-later `event_time`, I-02), it branches: (A) live
  propagation contexts remain → `SECURITY_RECOVERY → SOLUTION_PROPAGATION` (contexts + events preserved,
  G8); (B) no context, no assignment change → `SECURITY_RECOVERY → HASHING`; (C) redistribution needed →
  `SECURITY_RECOVERY → ASSIGNMENT → CompleteAssignmentPhase → HASHING` (no new template); (D) floor
  unrecoverable → `RoundAbort(reason = floor_unrecoverable)`. Branches A/B/C reach a floor-applicable state
  through `TransitionRoundState`/`CompleteAssignmentPhase`, so the applicability-entry census is captured
  (M2). R13/R14 are no longer "described but non-executable".
- **Driver-entry-point seating rules (N3).** Every sim-driver entry point seated on the queue
  (`RoundInitialise`, `TemplateCommit`, `PrepareParticipantsForNewRound`, `MinerRegister`, `ReserveActivate`,
  `FullRangeExhaustNoSolution`, `CompleteSecurityRecovery`, `RoundAbort`, `FinalizeSimulationRun`) has a
  declared event type, target microphase, stable tie key, required envelope fields, and a declared right to
  create same-time delta-cycle events (§0.7g-driver). No driver entry point receives a `dispatch_envelope`
  without a normative `ScheduleEvent` seating rule. `RoundAbort` keeps `TERMINAL_ABORT` priority (§21 item
  1); `FinalizeSimulationRun` is `RUN_FINALISE`, a run-level terminal processed after every ordinary round
  event, not an ordinary round event. **(Superseded by O1: `FinalizeSimulationRun` is NOT seated on the queue
  — see the Stage-1O addendum.)**

## Stage-1O terminology addendum (horizon/recovery final lock)

- **Run-level driver & canonical horizon sequence (O1).** `ProcessEventTime` is the SOLE event-loop driver
  (no handler re-enters it). The RUN-LEVEL driver `RunEventLoopToHorizon` (pseudocode §0.7d-run) calls
  `ProcessEventTime` for every `event_time <= T`, then invokes `FinalizeSimulationRun` as a
  post-`ProcessEventTime(T)` run-level HOOK. Canonical order: process events `< T`; drain all ordinary +
  delta-cycle events AT `T` to quiescence; if nonterminal, `CloseRoundAtHorizon` (§20b); the `T` epilogue
  `FinalizeEventTimeSecurityCensus(T)` (a `terminal_stale_noop`); then the run-level `FinalizeSimulationRun`.
- **`CloseRoundAtHorizon` (O1, §20b).** The NAMED run-level hook that closes a still-nonterminal round at the
  horizon `T` via `CloseRoundAssignments` with a DISTINCT horizon-end disposition and ONE deterministic
  horizon envelope, transitioning it to `ROUND_ABORTED`. It runs INSIDE `ProcessEventTime(T)` between the `T`
  drain and the `T` epilogue; it is NOT a queued event and performs NO residency settle.
- **`FinalizeSimulationRun` narrowed (O1, §20a).** A run-level HOOK (NOT a queued event, carries NO
  `dispatch_envelope`). It performs ONLY the single `FINAL_RUN_END` `SettleResidencyBoundary` + the I5/I6/I7
  reconciliation + sets `run_finalised`. The former internal DRAIN and horizon-close are REMOVED (they are
  the run driver's and `CloseRoundAtHorizon`'s). `RUN_FINALISE` is NOT an ordinary microphase in the queue map.
- **Binding horizon rule for `ScheduleEvent` (O2).** `ScheduleEvent` REJECTS any `target_event_time > T`
  (`run_horizon_T`), records `post_horizon_event_rejected`, and enqueues nothing — a deterministic result.
  `target_event_time = T` is legal. Consequently NO pending ordinary event ever has `event_time > T`. A
  floor-restored decision AT `T` therefore seats NO `CompleteSecurityRecovery` (it would be past `T`): it
  records `run_ending_no_recovery_action` and the round is closed by `CloseRoundAtHorizon`.
- **`RecoveryOutcome` (O3).** The settled result carried by a recovery-completion event, one of `{RESTORED,
  UNRECOVERABLE}` — replacing the contradictory `floor_result = restored` precondition/branch in
  `CompleteSecurityRecovery`. `RESTORED` → branches A/B/C; `UNRECOVERABLE` → branch D →
  `RoundAbort(reason = floor_unrecoverable)` (round only).
- **`RecoveryDeadlineEvent` (O3, §9a).** The NAMED, seated source that makes R14 (FloorUnrecoverable)
  REACHABLE. Seated through `ScheduleEvent` on entry to `SECURITY_RECOVERY`, carrying `RecoveryEpisodeID` +
  epoch; when it fires with the floor still breached it seats `CompleteSecurityRecovery` with
  `RecoveryOutcome = UNRECOVERABLE`. A concrete source and call path from a recovery episode to
  `RoundAbort(floor_unrecoverable)` now exists.
- **`RecoveryEpisodeID` and episode idempotence (O4).** `RecoveryEpisodeID = (RoundID, recovery_episode_seq)`
  is the deterministic identity of one recovery episode, minted on entry to `SECURITY_RECOVERY`.
  `recovery_completion_pending[episode]` guarantees AT MOST ONE completion event is seated per episode across
  BOTH sources (a duplicate seats nothing); `recovery_outcome_finalised[episode]` guarantees AT MOST ONE
  outcome is APPLIED per episode (a duplicate/stale completion is a deterministic no-op). Not prose "ENSURE
  exactly one" — the registry keys are the mechanism.
- **Round-state reconciliation & name replacement (O5).** No statement places the security decision BEFORE
  certificate/discovery events; the decision is the post-quiescence event-time epilogue
  `FinalizeEventTimeSecurityCensus` (I-01/I-02). The superseded name `FinalizeTimestampSecurityCensus` is
  replaced everywhere by `FinalizeEventTimeSecurityCensus`. Historical Stage-1A–1N lettered artifacts are
  unchanged; supersessions are recorded in `STAGE_01O_SUPERSESSION_REGISTER.md`.

## Stage-1P terminology addendum (horizon sentinel & recovery-decision lock)

- **Horizon sentinel (P1).** `RunEventLoopToHorizon` processes every `event_time` **strictly less than** `T`,
  then makes ONE synthetic horizon invocation `ProcessEventTime(T, is_horizon = true, allow_empty_horizon =
  true)` (guarded by `T not in finalised_event_times`). It runs EVEN WHEN the queue holds no event at `T`, so
  the horizon sequence occurs EXACTLY once: a nonterminal round is always horizon-closed (`CloseRoundAtHorizon`),
  the `T` census created by that closure is finalised, `T` is always added to `finalised_event_times`, and
  `FinalizeSimulationRun` runs only afterward (and ASSERTS the round is terminal, so a nonterminal round can
  never reach it without horizon closure). An ordinary event at `T` is NOT required.
- **`RunHookContext` & the deterministic run-hook envelope (P2).** Run-level hooks that mutate miner state
  obtain their envelope identity from the SOLE owner `RunHookContext` (`run_hook_seq`, `applied_run_hook_ids`),
  never from an ambient/undefined seq and never from the ordinary `event_creation_seq`. The horizon close uses
  `HorizonHookID = (RunID, T, HORIZON_CLOSE)`; its envelope is `{event_time = T, delta_cycle = RUN_HOOK_CYCLE
  (reserved), event_seq = run_hook_seq, hook_id = HorizonHookID}`. `RUN_HOOK_CYCLE` is never produced by
  `ScheduleEvent`, so a run-hook envelope cannot collide with an ordinary event envelope; `applied_run_hook_ids`
  makes the hook idempotent (exactly one horizon close per run; a replay returns `horizon_close_duplicate_noop`
  with no second transition energy or residency boundary). The undefined `horizon_close_delta_cycle` /
  `horizon_close_event_seq` are removed.
- **Recovery deadline is a FACT, not a pre-epilogue outcome (P3).** `RecoveryDeadlineEvent` records ONLY
  `recovery_deadline_reached[episode]` and creates a coherent census for its timestamp via
  `CaptureSecurityCensusOnRecoveryDeadline` (the third coherent writer of `security_census_dirty` /
  `latest_security_census`). It selects NO outcome and seats NO completion. The event-time epilogue
  (`SecurityFloorEvaluate`) SELECTS the outcome from the FINAL timestamp census — a persistent breach WITH the
  deadline reached → `UNRECOVERABLE`; a restored floor → `RESTORED` — so a same-timestamp `WakeCompleteEvent`
  that restores the floor is visible before the deadline outcome is chosen. Remaining in `SECURITY_RECOVERY`
  never implies the floor is still breached.
- **Atomic completion seating (P4).** The SOLE seater `SeatRecoveryCompletion` sets
  `recovery_completion_pending[episode]` ONLY AFTER `ScheduleEvent` returns `scheduled`; a rejected schedule
  leaves it false and records the exact disposition, and never reports a completion as seated. A decision AT
  `T` records `run_ending_no_recovery_action`, seats nothing, and leaves no false pending flag; the horizon
  close governs run end.
- **Recovery decision versioning (P5).** `RecoveryDecisionID = (RecoveryEpisodeID, recovery_decision_seq)`;
  `latest_recovery_decision[episode]` holds the latest `{decision_id, outcome}`. A `CompleteSecurityRecovery`
  carries its `RecoveryDecisionID` and applies its outcome ONLY if the episode is current AND its decision is
  the LATEST for the episode; a superseded decision returns `recovery_decision_stale_noop`. This prevents an
  old `RESTORED`/`UNRECOVERABLE` outcome from being applied after a newer final-census decision exists. A
  different outcome supersedes a pending one; the same standing outcome is not re-seated.
- **Historical freeze.** Stage-1A–1O lettered artifacts are unchanged; Stage-1P supersessions are recorded in
  `STAGE_01P_SUPERSESSION_REGISTER.md`.

## Stage-1Q terminology addendum (recovery-freshness & runtime-context lock)

- **Versioned final recovery census (Q1).** While in `SECURITY_RECOVERY`, the epilogue VERSIONS every final
  event-time census: `recovery_census_seq` increments and `latest_recovery_census[episode]` is published
  (fields: RecoveryEpisodeID, RecoveryCensusVersion, event_time, RoundID, TemplateID, state_version, H_active,
  H_honest, H_adversarial, q_adv, breach, deadline_reached). A pending decision binds to a
  `RecoveryCensusVersion`; `ReconcilePendingRecoveryDecisions` SUPERSEDES a decision the new census contradicts
  (even when the new census produces no completion) and re-affirms a still-consistent one — so freshness is
  judged against EVERY final census, not merely against the existence of a newer `RecoveryDecisionID`.
- **Two-step recovery application (Q2).** The recovery exit no longer applies on dispatch. Step 1 —
  `RecoveryCompletionDueEvent` (queued) records that a `RecoveryDecisionID` is due and refreshes the census; it
  performs NO transition and NO `RoundAbort`. Step 2 — `ApplyRecoveryCompletionAfterEpilogue` (post-epilogue
  hook run by `ProcessEventTime`) applies the outcome ONLY after the `event_time` is quiescent and its final
  census version is published, and ONLY if the decision's `RecoveryCensusVersion` equals
  `latest_recovery_census[episode].RecoveryCensusVersion` AND the outcome still matches the FINAL census. So a
  `RESTORED` decision never leaves recovery under a newer breach census. The R13/R14 transition/abort is the
  internal `CompleteSecurityRecovery` branch dispatch, called only by the post-epilogue hook.
- **Atomic decision supersession + explicit status (Q3).** `RECOVERY_DECISION_STATUS in {CREATED, SCHEDULED,
  SUPERSEDED, APPLIED, SCHEDULE_FAILED, CANCELLED}`. `recovery_decisions` (per-decision record) and
  `pending_recovery_decisions[episode]` (a SET of RecoveryDecisionIDs, not a boolean) track the applicable set.
  A newer final census marks a contradicted decision SUPERSEDED and cancels its due event BEFORE any replacement
  is seated; if the replacement schedule fails (`SCHEDULE_FAILED`), the old decision stays SUPERSEDED (never
  revived), `pending_recovery_decisions` reflects the remaining scheduled set, and the round stays
  `SECURITY_RECOVERY`.
- **One canonical census writer (Q4).** `CommitSecurityCensus` is the SOLE atomic writer of
  `latest_security_census[event_time]` + `security_census_dirty[event_time]`, with three `census_source` values
  {MINER_STATE_TRANSITION, APPLICABILITY_ENTRY, RECOVERY_DEADLINE}. `ApplyMinerStateTransition`,
  `CaptureSecurityCensusOnApplicabilityEntry`, and `CaptureSecurityCensusOnRecoveryDeadline` CALL it rather than
  writing the maps directly; the "two writers"/"third writer"/"sole writer" statements are replaced by "one
  writer, three sources". `dirty[t] = true ⇒ latest[t] exists` is structural.
- **Explicit RunContext ownership (Q5).** `RunContext` {RunID, EventQueueContext, RunHookContext,
  rebased_boundaries, run_finalised, run_horizon_T, and the per-run security-census maps} is created ONCE by
  `RunInitialise`. `RoundInitialise` receives `RunContext` explicitly, initialises ONLY per-round registries,
  preserves/reuses `RunContext`, and RETURNS every per-round recovery registry explicitly.
  `RunEventLoopToHorizon` obtains `RunHookContext` through `RunContext.RunHookContext`.
- **Tagged run-hook namespace (Q6).** `envelope_namespace in {ORDINARY_EVENT, RUN_HOOK}`. Ordinary
  `ScheduleEvent` envelopes are `ORDINARY_EVENT`; `CloseRoundAtHorizon` uses `RUN_HOOK` + `hook_id = (RunID, T,
  HORIZON_CLOSE)`. Collision freedom derives from the TAG (not the `RUN_HOOK_CYCLE` number); a `TransitionEventID`
  includes `envelope_namespace`/`hook_id`. `applied_run_hook_ids` carries an IN_PROGRESS/APPLIED state so a
  partial horizon close cannot replay as a second full close.
- **Deterministic recovery completion time (Q7).** `target_time = decision_time +
  configured_recovery_completion_delay` (config `> 0`, or the next-representable instant), replacing the
  undefined `t_next`. If `target_time > T`, no completion is seated, the decision records `horizon_deferred`
  (status CANCELLED), a superseded decision stays invalid, and `CloseRoundAtHorizon` governs run end.
- **Historical freeze.** Stage-1A–1P lettered artifacts are unchanged; Stage-1Q supersessions are recorded in
  `STAGE_01Q_SUPERSESSION_REGISTER.md`.

## Stage-1R terminology addendum (post-epilogue & transition-identity lock)

- **No same-timestamp event after the ordinary drain (R1).** The post-epilogue recovery application
  (`ApplyRecoveryCompletionAfterEpilogue`) and its branch dispatch `CompleteSecurityRecovery` may NOT directly or
  indirectly enqueue an ordinary event whose `target_event_time` equals the already-drained application
  `event_time` `t`. Branch C (`SECURITY_RECOVERY → ASSIGNMENT`, reserve activation / reassignment,
  `CompleteAssignmentPhase → HASHING`) transitions to `ASSIGNMENT` and seats ONE
  `RecoveryAssignmentContinuationEvent` at `next_representable_simulation_time(t)` — a STRICTLY LATER `event_time`
  — whose ordinary handler performs `ReserveActivate`/`RangeReassign`/`StartWake`. A zero modeled wake latency after
  application is represented at `next_representable_simulation_time(t)`, never at `t`. Before adding `t` to
  `finalised_event_times`, `ProcessEventTime` ASSERTS no ordinary event remains at `t`.
- **`RecoveryAssignmentContinuationEvent` (R1).** The ordinary queued event
  (`RECOVERY_ASSIGNMENT_CONTINUATION`) that carries out branch-C assignment work at a strictly-later `event_time`,
  so the post-epilogue application enqueues nothing at the drained `event_time`.
- **One security epilogue, one post-application settlement (R2).** `FinalizeEventTimeSecurityCensus(t)` runs
  EXACTLY ONCE per `event_time` and is the SOLE security-floor decision for `t`. The prior "epilogue #1 / epilogue
  #2" framing is removed. `FinalizePostRecoveryApplicationState(t)` is a post-application SETTLEMENT — run once when
  the application re-dirtied `t` — that archives the terminal/post-application census and clears
  `security_census_dirty[t]` WITHOUT invoking `SecurityFloorEvaluate` again, seats no recovery decision, and
  enqueues no event at `t`.
- **`FinalizePostRecoveryApplicationState` (R2).** The single post-application settlement hook. For an
  UNRECOVERABLE application that closes the round it records a terminal census observation; for a RESTORED exit it
  records a post-application observation of the already-non-breached census; any NEW applicability census from later
  miner activation is generated at the strictly later continuation `event_time`.
- **Full transition envelope (R3).** `ApplyMinerStateTransition` receives ONE explicit transition envelope —
  `envelope_namespace`, `event_time`, `delta_cycle`, `event_seq`, `hook_id` — sourced from the caller's
  `dispatch_envelope`; the namespace fields are NEVER decomposed away. `TransitionEventID` includes
  `envelope_namespace` and `hook_id`, so a `RUN_HOOK` transition and an `ORDINARY_EVENT` transition with identical
  numeric `(event_time, delta_cycle, event_seq)` are DISTINCT ids. `ProcessEventTime` materialises an
  `ORDINARY_EVENT` dispatch envelope with `hook_id = null`; `CloseRoundAtHorizon` preserves `RUN_HOOK` +
  `HorizonHookID` through `CloseRoundAssignments → EnterLowPowerListen → ApplyMinerStateTransition`.
- **Atomic recovery application (R4).** `RECOVERY_DECISION_STATUS` adds `APPLYING` and `APPLY_FAILED`. A decision is
  verified, atomically set `APPLYING`, and marked `APPLIED` (with the episode finalised + cleared) ONLY after
  `CompleteSecurityRecovery` reports a successful round transition or `RoundAbort`; a branch failure yields
  `APPLY_FAILED` and PRESERVES the active episode. `CompleteSecurityRecovery` returns an explicit success/failure
  disposition per branch. At the horizon (after `CloseRoundAtHorizon` makes the round terminal) pending decisions
  are cancelled and the application returns `terminal_recovery_noop` — no decision is marked `APPLIED` after horizon
  closure.
- **Explicit census-write sequence and five sources (R5).** `security_census_write_seq_by_event_time` is a
  `RunContext` field — an EXPLICIT deterministic per-`event_time` census-write ordinal owned SOLELY by
  `CommitSecurityCensus`, initialised in `RunInitialise` and preserved across rounds — replacing the implicit "next
  ordinal". `CENSUS_SOURCE` = {MINER_STATE_TRANSITION, APPLICABILITY_ENTRY, RECOVERY_DEADLINE,
  RECOVERY_COMPLETION_DUE, POST_RECOVERY_APPLICATION}. `RecoveryCompletionDueEvent` uses `RECOVERY_COMPLETION_DUE`
  (not `RECOVERY_DEADLINE`); `FinalizePostRecoveryApplicationState` uses `POST_RECOVERY_APPLICATION`. Every producer
  (the miner hook and the capture procedures) CALLS `CommitSecurityCensus`; none is a direct writer of the maps.
- **Consistent latest-decision mirror (R6).** `latest_recovery_decision` is kept ATOMICALLY consistent with
  `recovery_decisions` by the sole status mutator `SetRecoveryDecisionStatus` on every transition to SCHEDULED /
  SUPERSEDED / APPLYING / APPLIED / SCHEDULE_FAILED / APPLY_FAILED / CANCELLED — it can never remain CREATED after
  the underlying decision became CANCELLED or SCHEDULE_FAILED.
- **`SetRecoveryDecisionStatus` (R6).** The SOLE mutator of a decision's status after its initial CREATED; it also
  refreshes `latest_recovery_decision` when that mirror points at the decision, making mirror consistency structural.
- **`next_representable_simulation_time(t)` (R1).** The next representable simulation instant strictly greater than
  `t`; the deterministic target for a zero-modeled-latency continuation after post-epilogue recovery application.
- **Historical freeze.** Stage-1A–1Q lettered artifacts are unchanged; Stage-1R supersessions are recorded in
  `STAGE_01R_SUPERSESSION_REGISTER.md`.
