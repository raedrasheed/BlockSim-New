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

## Stage-1S terminology addendum (full-envelope & deferred-recovery-atomicity lock)

- **One explicit transition-envelope object (S1).** `ApplyMinerStateTransition` takes ONE `transition_envelope`
  object — `{envelope_namespace, event_time, delta_cycle, event_seq, hook_id}` — and builds `TransitionEventID`
  EXCLUSIVELY from it plus the transition-specific fields. EVERY call site passes exactly `transition_envelope =
  dispatch_envelope` (ORDINARY_EVENT/null, or the RUN_HOOK horizon envelope + `HorizonHookID`). The R3 "namespace
  fields travel implicitly" clause is WITHDRAWN — no identity field is decomposed or omitted at any executable call
  site. The horizon path `CloseRoundAtHorizon → CloseRoundAssignments → EnterLowPowerListen /
  ApplyMinerStateTransition` threads the SAME RUN_HOOK envelope and `HorizonHookID` throughout.
- **Deferred branch-C application (S2/S3).** Branch C (RESTORED with range redistribution) does NOT mutate
  `round_state` before its `RecoveryAssignmentContinuationEvent` is SEATED. `CompleteSecurityRecovery` computes
  `t_cont`, validates `t_cont <= T`, seats the continuation (strictly later than `t`), and returns `DEFERRED`; a
  failed seat / target-beyond-`T` stays `SECURITY_RECOVERY` and marks the decision `APPLY_FAILED`/`HORIZON_DEFERRED`,
  preserving the episode. Seating is NOT applying RESTORED (S3): the decision stays `APPLYING` and the episode stays
  active until `RecoveryAssignmentContinuationEvent` verifies the still-current APPLYING decision, transitions
  `SECURITY_RECOVERY → ASSIGNMENT`, installs the disjoint set, and reaches `HASHING` — only THEN is it `APPLIED` and
  the episode cleared. A failure before the transition stays `SECURITY_RECOVERY`; a failure after it takes a declared
  recovery-finalising `RoundAbort`, so the round never lingers in `ASSIGNMENT` with an active episode and no live
  continuation.
- **`recovery_branch_result` (S3).** The disposition `CompleteSecurityRecovery` returns, with kind in
  {SUCCESS (branches A/B/D), DEFERRED (branch C seated), FAILED}. The caller applies only on SUCCESS, keeps the
  decision APPLYING on DEFERRED, and records `APPLY_FAILED`/`HORIZON_DEFERRED` on FAILED.
- **`CancelActiveRecoveryEpisode` / `TERMINAL_CANCELLED` (S4).** The terminal-cleanup procedure invoked by
  `CloseRoundAssignments` (for every terminal closure EXCEPT the recovery-finalising abort) when an episode is still
  active: it cancels every pending/applying decision and its queued `RecoveryCompletionDueEvent` /
  `RecoveryAssignmentContinuationEvent`, records `recovery_episode_disposition = TERMINAL_CANCELLED`, and clears
  `current_recovery_episode` (without setting `recovery_outcome_finalised`). Enforces `current_recovery_episode !=
  null IFF round_state = SECURITY_RECOVERY`. `recovery_finalising` is the flag threaded to `RoundAbort` /
  `CloseRoundAssignments` marking a closure that IS the application of a recovery outcome (so its cleanup is skipped).
- **`SettleSecurityCensusDirty` (S5).** The SOLE clearer of `security_census_dirty[event_time]`, with
  `settlement_kind in {PRIMARY_EPILOGUE, POST_RECOVERY_APPLICATION}` — called by `FinalizeEventTimeSecurityCensus`
  and `FinalizePostRecoveryApplicationState` respectively. `CommitSecurityCensus` remains the sole setter of
  `dirty = true`.
- **Unconditional single primary epilogue (S6).** `ProcessEventTime` calls `FinalizeEventTimeSecurityCensus(t)`
  EXACTLY ONCE and UNCONDITIONALLY; the procedure owns the dirty check and returns `no_census_change` when nothing
  is dirty. The CALL is not guarded by `IF security_census_dirty[t]`.
- **`PostEpilogueSchedulingContext` (S7).** The declared source of a post-epilogue `ScheduleEvent` call (the
  branch-C continuation seat): `{source_event_time, source_envelope, EventQueueContext, RunContext}`. `ScheduleEvent`
  requires `target_event_time > source_event_time` and derives `delta_cycle = 0`, so a post-epilogue caller can never
  enqueue at the source event_time; `event_creation_seq` is still minted solely by `ScheduleEvent`.
- **Historical freeze.** Stage-1A–1R lettered artifacts are unchanged; Stage-1S supersessions are recorded in
  `STAGE_01S_SUPERSESSION_REGISTER.md`.

## Stage-1T terminology addendum (continuation-epilogue & outcome-integrity lock)

- **`RecoveryAssignmentContinuationDueEvent` (T1 step 1).** The queued event (microphase
  `RECOVERY_ASSIGNMENT_CONTINUATION_DUE`) that a DEFERRED branch C seats through the S7
  `PostEpilogueSchedulingContext` at `next_representable_simulation_time(t)`. It RECORDS the continuation DUE fact
  (`continuation_due_at_event_time`, `continuation_due_dispatch_envelope`) and refreshes the census (via
  `CommitSecurityCensus`, `census_source = RECOVERY_COMPLETION_DUE`); it performs NO round-state transition, creates
  NO assignment, and does NOT mark the decision APPLIED. It REPLACES the former single-step
  `RecoveryAssignmentContinuationEvent` — the queued event no longer does the assignment rebuild.
- **`ApplyRecoveryAssignmentContinuationAfterEpilogue` (T1 step 2 / post-epilogue hook).** The ONLY place branch-C
  RESTORED is APPLIED. `ProcessEventTime` invokes it AFTER `FinalizeEventTimeSecurityCensus(t)` and
  `ApplyRecoveryCompletionAfterEpilogue(t)`; it applies at most one continuation whose
  `continuation_due_at_event_time = t`, so no branch-C RESTORED result is recorded during the ordinary-event drain.
  **T1 mutual exclusion:** at most one of the completion hook and this hook applies per `RecoveryEpisodeID` per
  `event_time` (a completion applied at `t` clears the episode, so this hook then finds nothing due).
- **`RecoveryContinuationID` / `ContinuationGeneration` (T2).** `RecoveryContinuationID = (RecoveryDecisionID,
  continuation_generation)`. The immutable Due event carries only the `ContinuationGeneration`; the AUTHORITATIVE
  bound census version is the decision's `continuation_bound_census_version`, kept current by
  `ReconcilePendingRecoveryDecisions` (T2 rule B: a re-affirmed DEFERRED decision's continuation bound version is
  advanced to the latest `RecoveryCensusVersion`). The post-epilogue hook applies branch C only when the ACTIVE
  generation matches (`ContinuationGeneration = D.continuation_generation`) AND
  `continuation_bound_census_version = latest_recovery_census[episode].RecoveryCensusVersion` AND the final census
  still warrants RESTORED — else a stale-noop. A reserve-dependent re-arm mints a FRESH generation
  (`continuation_generation + 1`).
- **`recovery_install_in_progress` / `RecoveryInstallID` / `active_recovery_install_decision` (T3).** The
  installation-phase registries covering the redistribution-only install (a SYNCHRONOUS sub-computation with NO
  event boundary within it). `recovery_install_in_progress` is `true` only between the `SECURITY_RECOVERY →
  ASSIGNMENT` transition and the install's terminal exit; `RecoveryInstallID = (episode, recovery_install_seq)`
  identifies the install; `active_recovery_install_decision` names the decision being installed. **T3 exit
  invariant:** every install ends in exactly one of `HASHING` + decision `APPLIED`; `SECURITY_RECOVERY` +
  `APPLY_FAILED` (rolled back); `ROUND_ABORTED` + `RECOVERY_INSTALL_FAILED_ABORTED`.
- **`RECOVERY_INSTALL_FAILED_ABORTED` / `APPLY_FAILED_TERMINAL` (T4).** The episode disposition and decision status
  for an IRREVERSIBLE branch-C install failure AFTER the transition: the round is closed via the declared
  recovery-finalising `RoundAbort(reason = recovery_install_failed_aborted)`, `recovery_outcome_finalised` is left
  UNSET, and NO `UNRECOVERABLE` outcome is fabricated (UNRECOVERABLE is reserved for a FINAL census that still
  breaches the floor, O3/R14).
- **`assignment_phase_completed` / `assignment_phase_failed(reason)` (T5).** The explicit disposition
  `CompleteAssignmentPhase` returns. A malformed assignment set is caught BEFORE the irreversible `HASHING`
  transition and returns `assignment_phase_failed(malformed_assignment_set)` (round still `ASSIGNMENT` — reversible),
  which the continuation hook rolls back to `SECURITY_RECOVERY`; `assignment_phase_completed` means the round reached
  `HASHING`.
- **Redistribution-only vs reserve-dependent restoration (T6).** A restoration is *redistribution-only* when the
  FINAL census satisfies the floor using ONLY currently `ACTIVE_HASHING` miners (installed synchronously, T3);
  otherwise it is *reserve-dependent* — the hook activates the reserve while the round STAYS `SECURITY_RECOVERY`,
  keeps the decision `APPLYING`, and RE-ARMS a strictly-later continuation (fresh generation). Reserve-dependent
  RESTORED is applied only once a later final census confirms the floor with the reserve `ACTIVE_HASHING`.
- **Post-epilogue continuation causality (T7).** The continuation application runs strictly after the event-time
  epilogue; every `StartWake`/re-arm it seats is placed at a STRICTLY LATER `event_time` through
  `PostEpilogueSchedulingContext`. `ProcessEventTime` asserts `no recovery-continuation application remains due at t`
  before finalising `t`.
- **Historical freeze.** Stage-1A–1S lettered artifacts are unchanged; Stage-1T supersessions are recorded in
  `STAGE_01T_SUPERSESSION_REGISTER.md`.

## Stage-1U terminology addendum (reserve-recovery & continuation-liveness lock)

- **Recovery OUTCOME vs recovery WORK (U1).** A *recovery outcome* is `RESTORED` or `UNRECOVERABLE`, decided ONLY
  from a final census (`outcome_consistent_with_census` unchanged — `RESTORED` requires `census.breach = false`). A
  *recovery-work action* (`RECOVERY_WORK_ACTION` in {`RESERVE_ACTIVATION_REQUIRED`, `RANGE_REDISTRIBUTION_REQUIRED`,
  `NONE`}) is the reserve activation / redistribution attempted WHILE the floor is still breached; it is NEVER a
  `RecoveryOutcome` and is NEVER marked `APPLIED` as `RESTORED`.
- **`ClassifyRecoveryWork` / `SeatRecoveryWork` / `RecoveryWorkDueEvent` / `ApplyRecoveryWorkAfterEpilogue` (U1).** The
  breach-before-deadline epilogue classifies the work (`ClassifyRecoveryWork`, compute-only) and seats ONE versioned
  `RecoveryWorkDueEvent` (`SeatRecoveryWork`, atomic + idempotent, microphase `RECOVERY_WORK_DUE`); the queued Due event
  records the work-due fact + refreshes the census (NO activation); the POST-epilogue hook
  `ApplyRecoveryWorkAfterEpilogue` performs the work while the round STAYS `SECURITY_RECOVERY` and marks NOTHING
  `RESTORED`. `RecoveryWorkID = (RecoveryEpisodeID, recovery_work_seq)`; `pending_recovery_work[episode]` is the
  at-most-one in-flight controller.
- **`SchedulingSourceContext` (U2).** `{ORDINARY_DISPATCH(dispatch_envelope), POST_EPILOGUE(PostEpilogueSchedulingContext)}`.
  `ReserveActivate` / `RangeReassign` / `RangeAssign` / `StartWake` / `CommitRecoveryAssignmentPlan` take an explicit
  `scheduling_context`; a `POST_EPILOGUE` caller threads the `pctx` all the way to `ScheduleEvent`, so a zero-latency
  post-epilogue wake targets `next_representable_simulation_time(source)` and is STRICTLY LATER than the source time.
- **Atomic re-arm (U3).** A recovery-work seat / re-arm advances the active identity ONLY after `ScheduleEvent`
  succeeds (compute candidate identity + target, validate `<= T`, schedule without mutating the active identity,
  publish `status = ARMED` + event ref only on success); a rejection advances nothing, publishes no false reference,
  reports no pending state, and records an explicit disposition. No `APPLYING` decision is stranded without a live
  event, a controller, or an explicit terminal/horizon disposition.
- **`CONTINUATION_DUE_STATUS` (U4).** `{NOT_DUE, DUE, CONSUMED, SUPERSEDED, CANCELLED}` on the continuation record and
  every recovery-work record. The DueEvent sets `DUE`; the post-epilogue hook ATOMICALLY consumes it (`CONSUMED` on
  apply/settle, `SUPERSEDED` on stale-noop, `CANCELLED` on terminal closure) before returning; `ProcessEventTime`
  asserts on the EXPLICIT status, not on a timestamp field.
- **`PrepareRecoveryAssignmentPlan` / `CommitRecoveryAssignmentPlan` / `RollbackRecoveryAssignmentPlan` (U5).** The named
  procedures that replace the opaque `INSTALL` / `UNDO` macros. Prepare is compute-only and verifies I1/I3/I10/I18b
  BEFORE any mutation; Commit threads the `scheduling_context`, creates assignments in stable order, and returns
  `install_committed` / `install_failed_before_mutation` / `install_failed_after_mutation(reason, rollback_record)`;
  Rollback cancels every plan event, closes every plan-created live head legally (I18b), restores the coverage/custody
  ledgers, and returns `rollback_completed` / `rollback_failed` (a failed rollback takes the T4 abort, never a fabricated
  UNRECOVERABLE).
- **CompleteAssignmentPhase disposition at every caller (U6).** `PrepareParticipantsForNewRound`, `TemplateRefresh`, and
  the recovery installation each capture and branch on `assignment_phase_completed | assignment_phase_failed(reason)`; a
  pre-`HASHING` failure rolls back and takes the declared setup/refresh failure path — no caller returns success with
  the round still `ASSIGNMENT`.
- **`RECOVERY_CONTINUATION_DUE` / `RECOVERY_WORK_DUE` census sources (U7/U1).** Distinct census provenances so
  "completion is due", "continuation is due", "recovery work is due", and "deadline reached" are distinguishable;
  `RecoveryAssignmentContinuationDueEvent` uses `RECOVERY_CONTINUATION_DUE` (not `RECOVERY_COMPLETION_DUE`).
- **Historical freeze.** Stage-1A–1T lettered artifacts are unchanged; Stage-1U supersessions are recorded in
  `STAGE_01U_SUPERSESSION_REGISTER.md`.

## Stage-1V terminology addendum (recovery-work transaction & liveness lock)

- **`ReconcilePendingRecoveryWork` (V1).** The procedure `SecurityFloorEvaluate` calls — after `CommitRecoveryCensus`
  and `ReconcilePendingRecoveryDecisions`, before it considers `SeatRecoveryWork` — to reconcile the in-flight
  recovery-work record against the newest final census: a still-warranted DUE record is REBOUND to the latest version
  (same `RecoveryWorkID`, no replacement) so `ApplyRecoveryWorkAfterEpilogue` can consume it; a no-longer-warranted
  record is SUPERSEDED; an ARMED future record is re-affirmed or superseded. `SeatRecoveryWork` never replaces a DUE
  record at the current `event_time`.
- **`SchedulingSourceContext` is explicit at every call site (V2).** The Stage-1U bare-`dispatch_envelope`
  ORDINARY_DISPATCH alias is WITHDRAWN. Every `StartWake` / `ReserveActivate` / `RangeAssign` / `RangeReassign` /
  `CommitRecoveryAssignmentPlan` call passes `scheduling_context = ORDINARY_DISPATCH(dispatch_envelope)` or
  `POST_EPILOGUE(pctx)` explicitly.
- **`StartWake` transaction (V3).** `wake_seated(AssignmentID, WakeEventRef, wake_target_time, resulting_state =
  WAKING)` | `wake_schedule_failed_before_transition(reason)` | `wake_transition_failed_after_seat(reason,
  WakeEventRef)`. It seats the `WakeCompleteEvent` FIRST, then applies the WAKING transition; a post-seat transition
  failure cancels the seated event, so a miner is never left WAKING without a live `WakeCompleteEvent`.
- **`reserve_activation_committed` / `ReserveActivateFromPlan` (V4/V5).** `ReserveActivate` /
  `ReserveActivateFromPlan` return `reserve_activation_committed(MinerID, AssignmentID, assignment_version,
  WakeEventRef)` | `reserve_activation_failed_before_mutation(reason)` |
  `reserve_activation_failed_after_assignment(reason, AssignmentID, rollback_record)`. `ReserveActivateFromPlan` uses
  the plan's EXACT selected values (V5); a wake-seat failure after the PENDING assignment closes it legally and leaves
  the reserve miner in `RESERVE`.
- **`SECURITY_FLOOR_RECOVERY_WORK` vs `COVERAGE_REPAIR_WORK` (V6).** `RECOVERY_WORK_CLASS`: only census-changing
  actions (reserve activation / declared participation replacement) are `SECURITY_FLOOR_RECOVERY_WORK` and control the
  breach-before-deadline logic; a same-active-miner redistribution is `COVERAGE_REPAIR_WORK` (cannot change
  `H_active`/`H_honest`/`q_adv`) and `ClassifyRecoveryWork` no longer returns `RANGE_REDISTRIBUTION_REQUIRED`.
- **`RECOVERY_WORK_STATUS` complete lifecycle (V7).** {CREATED, ARMED, DUE, APPLYING, CONSUMED, SUPERSEDED,
  SCHEDULE_FAILED, HORIZON_DEFERRED, CANCELLED}. Exactly one live/terminal disposition per `RecoveryWorkID`; at most
  one per episode in {ARMED, DUE, APPLYING}; `CancelActiveRecoveryEpisode` cancels EVERY nonterminal work record.
- **`RollbackParticipantSetup` / `RollbackTemplateRefreshSetup` / `SetupRetryEvent` (V8).** The named executable
  rollbacks (cancel captured `WakeEventRef`s, close created heads legally, restore ledgers, verify no participant
  stays WAKING) and the deterministic strictly-later retry event; `PrepareParticipantsForNewRound` / `TemplateRefresh`
  capture each structured `StartWake` result and, on failure, roll back and take an explicit liveness path (retry or
  `RoundAbort`).
- **No boolean/AND returns (V9).** Every procedure inspects the scheduler disposition explicitly and returns one
  declared structured result; `RETURN ScheduleEvent(...) AND wake_started`-style constructs are removed.
- **Historical freeze.** Stage-1A–1U lettered artifacts are unchanged; Stage-1V supersessions are recorded in
  `STAGE_01V_SUPERSESSION_REGISTER.md`.

## Stage-1W terminology addendum (legal-rollback & plan-transaction lock)

- **`rollback_envelope` (W1).** An IMMUTABLE field of the setup transaction (`participant_setup_txn` /
  `refresh_setup_txn`), set at creation to the setup's own dispatch envelope
  (`{ envelope_namespace, event_time, delta_cycle, event_seq, hook_id }`). Every rollback transition uses it as its
  `transition_envelope`; no placeholder, ambient, or undeclared envelope is used.
- **Legal rollback edge (W2).** A setup rollback departs a `WAKING` participant to `OFFLINE` via the authoritative
  `T12` edge only; the illegal `WAKING -> REGISTERED`/`RESERVE`/`LOW_POWER_LISTEN` edges are never used.
  `RollbackParticipantSetup` / `RollbackTemplateRefreshSetup` return `rollback_completed(rolled_to_offline)`.
- **`refresh_setup_txn` populated in-loop (W3).** `TemplateRefresh` initialises the transaction before its miner loop
  and populates each field with EXPLICIT statements as it creates assignments and seats wakes; a wake/creation failure
  sets `refresh_setup_error`, skips `CompleteAssignmentPhase`, and takes the named rollback + liveness path.
- **Structured range result (W4).** `RangeAssign*`/`RangeReassign*` return `range_assigned` / `range_assign_creation_failed`
  / `range_assign_wake_failed` (and the `range_reassign_*` analogues); `CommitRecoveryAssignmentPlan` consumes the
  success result's `AssignmentID` + `WakeEventRef` and never wakes twice.
- **Plan-bound range constructor (W5).** `RangeAssignFromPlan` / `RangeReassignFromPlan` take the exact validated spec
  fields (`MinerID`, `range`, `assignment_origin`, `source_assignment`, `reassignment_reason`, `lease_duration`,
  `scheduling_context`) and perform NO `SELECT`; the ordinary entry points select policy and delegate.
- **Transition result union (W6).** `ApplyMinerStateTransition` returns `transition_applied(TransitionEventID)` |
  `duplicate_suppressed(TransitionEventID)` | `illegal_stale_source(TransitionEventID)` |
  `illegal_transition(TransitionEventID)`.
- **Assignment-creation result (W7).** `CreatePendingAssignment` returns `assignment_created(assignment)` |
  `assignment_creation_failed(reason)`; every caller branches before any `AssignmentID` access, lease update, or
  transaction-record entry.
- **`SetupRetryID` / bounded retry (W8).** `SetupRetryID = (RoundID, setup_kind, setup_retry_generation)`; a retry is
  seated only when it is state-compatible (no participant `OFFLINE`), idempotent (`applied_setup_retry_ids`), and within
  `maximum_setup_retries`; otherwise `RoundAbort`.
- **Historical freeze.** Stage-1A–1V lettered artifacts are unchanged; Stage-1W supersessions are recorded in
  `STAGE_01W_SUPERSESSION_REGISTER.md`.

## Stage-1X terminology addendum (recovery-rollback & retry-contract lock)

- **`rollback_record` / `rollback_item` (X1/X5).** `CommitRecoveryAssignmentPlan` builds and RETURNS an explicit
  `install_committed(rollback_record)`, where `rollback_record = { RecoveryInstallID, items:[rollback_item] }` and each
  `rollback_item = { MinerID, AssignmentID, assignment_version, WakeEventRef, pre_wake_state,
  rollback_envelope, coverage_custody_before_image, kind, provenance }` is captured BEFORE its plan-bound constructor
  mutates state. There is no pass-by-reference `plan.rollback_metadata`; the record is the sole rollback contract.
- **Recovery-plan rollback as a complete state transaction (X1/X8).** `RollbackRecoveryAssignmentPlan(RoundContext,
  rollback_record)` cancels every `WakeEventRef`, departs each still-`WAKING` miner to `OFFLINE` via the legal `T12`
  edge — with `assignment_ref = assignment_version_ref(item.AssignmentID, item.assignment_version)` (never null) and
  `transition_envelope = item.rollback_envelope` — closes each head canonically, restores the coverage/custody ledgers
  from `coverage_custody_before_image`, and verifies no event pending / no head live / no miner `WAKING` before
  returning `rollback_completed(rolled_to_offline, rolled_back_items)`; otherwise `rollback_failed(reason)`. It never
  returns `rollback_completed` while a miner is `WAKING` with no live event. Each `T12` closes the WAKING residency at
  the rollback `event_time`, charges the transition energy once, opens `OFFLINE`, adds no `H_active`, and updates the
  census only via `CommitSecurityCensus` when `ACTIVE_HASHING` membership changes.
- **`assignment_by_miner` (X2).** A field of `participant_setup_txn` / `refresh_setup_txn`,
  `assignment_by_miner : MinerID -> (AssignmentID, assignment_version)`, populated after `assignment_created` and before
  `StartWake`. Setup rollbacks (`RollbackParticipantSetup` / `RollbackTemplateRefreshSetup`) iterate it and pass the
  EXACT `assignment_version_ref(aid, ver)` to `T12` (never null when the miner holds a setup-created `PENDING` head).
- **`ContinueTemplateRefreshAssignmentSetup` (X3).** A procedure that owns ONLY eligible-miner selection/creation,
  `StartWake`, `CompleteAssignmentPhase`, rollback, and bounded retry-or-abort for a template refresh.
  `TemplateRefresh` performs closure + candidate construction + `TemplateCommit` and then CALLs it; a
  `SetupRetryEvent(TEMPLATE_REFRESH_SETUP)` also calls it and NEVER re-enters `TemplateRefresh`, so a retry never repeats
  `CloseTemplateAssignments`, candidate construction, or `TemplateCommit`.
- **`TemplateRefreshSetupID` / `template_refresh_setup_committed` (X3).** An idempotent marker keyed to the committed
  new `TemplateID`; `template_refresh_setup_committed[new_TemplateID] = true` records that closure + construction +
  commit already occurred, so re-entry via `ContinueTemplateRefreshAssignmentSetup` resumes only assignment seating.
- **Kind-specific `SetupRetryEvent` guard (X4).** `PARTICIPANT_SETUP` requires `phase = ASSIGNMENT` and a committed
  eligible `TemplateID`, then calls `PrepareParticipantsForNewRound`; `TEMPLATE_REFRESH_SETUP` requires `phase =
  ASSIGNMENT`, the committed `TemplateID` equal to the refresh setup's, and the closure/commit markers, then calls
  `ContinueTemplateRefreshAssignmentSetup`. `ROUND_INITIALISING` / `TEMPLATE_COMMITMENT` are rejected; an over-budget
  retry is a `RoundAbort` (not merely `setup_retry_exhausted`) unless already terminal; the phase is never left in
  `ASSIGNMENT` with no controller.
- **Reachable `assignment_creation_failed` (X6).** `CreatePendingAssignment` PRECONDITIONS constrain only type/shape
  (`assignment_origin in { ORIGINAL, REASSIGNED }`); the runtime-varying predicates (I1 overlap, `custody != completed`,
  `coverage != searched`, source/provenance, `RoundID`/`TemplateID` validity) are evaluated in the guard and yield
  `assignment_creation_failed(reason)`, so the failure disposition is legally reachable.
- **Canonical closure fields + `closure_detail` (X7).** Every Stage-1X head closure sets `status`, `custody_status`,
  `termination_reason`, and `revocation_reason` from the canonical enums only, and records the non-enum free descriptor
  in `closure_detail`. Fixed uses: participant setup rollback (`termination_reason = cancellation`,
  `revocation_reason = assignment_revoked`, `closure_detail = participant_setup_rolled_back`); template refresh setup
  rollback (`closure_detail = template_refresh_setup_rolled_back`); recovery-plan rollback
  (`closure_detail = recovery_install_rolled_back`); range/reserve wake failure (`termination_reason = wake_failure`,
  `closure_detail = range_assign_wake_failed` / `range_reassign_wake_failed` / `reserve_activation_wake_failed`). No
  string outside the canonical enums appears in `termination_reason`, `custody_status`, or `revocation_reason`.
- **Historical freeze.** Stage-1A–1W lettered artifacts are unchanged; Stage-1X supersessions are recorded in
  `STAGE_01X_SUPERSESSION_REGISTER.md`.

## Stage-1Y terminology addendum (retry-identity & rollback-closure lock)

- **`SetupRetryStatus` (Y1).** An enum `{ SEATED, APPLYING, APPLIED, SUPERSEDED, CANCELLED, ABORTED }` recorded per
  `SetupRetryID` in `setup_retry_status_by_id`. `SetupRetryEvent` checks EXACT-replay idempotence (a `SetupRetryID` in
  `applied_setup_retry_ids` / `setup_retry_status_by_id`) BEFORE the terminal check and the wrong-round-state abort, so a
  replay of a retry that already succeeded and advanced the round (e.g. to `HASHING`) returns
  `setup_retry_duplicate_suppressed` and NEVER calls `RoundAbort` for a forward round.
- **`TemplateRefreshSetupID` (Y2).** `= (RoundID, committed_new_TemplateID)`. A `TEMPLATE_REFRESH_SETUP` retry payload
  carries BOTH `TemplateID_at_seat` and `TemplateRefreshSetupID` explicitly; `SetupRetryEvent` and
  `ContinueTemplateRefreshAssignmentSetup` VERIFY the exact `TemplateRefreshSetupID` against
  `template_refresh_setup_committed[TemplateID_at_seat].TemplateRefreshSetupID` on the initial invocation and every retry.
  There is no ambient "the refresh setup's TemplateID"; a stale-`TemplateID` retry takes a declared stale disposition and
  never operates on the current committed template.
- **`retry_generation` vs `setup_retry_generation_by_scope` (Y3).** `retry_generation` is the SCALAR generation carried
  as an input by `SetupRetryEvent` / `ContinueTemplateRefreshAssignmentSetup`; the bounded per-scope counter registry is
  the DISTINCT map `setup_retry_generation_by_scope : (RoundID, setup_kind, TemplateRefreshSetupID_or_null) -> generation`.
  No identifier is both a scalar and a map. `SetupRetryID` carries the full scope:
  `(RoundID, TemplateID, PARTICIPANT_SETUP, retry_generation)` /
  `(TemplateRefreshSetupID, TEMPLATE_REFRESH_SETUP, retry_generation)`.
- **`setup_txn.wake_by_miner` / `setup_txn.before_image_by_miner` (Y4).** Per-miner maps captured after
  `assignment_created` and before `StartWake`, so a setup rollback can cancel the EXACT wake and restore the EXACT
  before-image for every affected miner through the one named operation.
- **`AbortPendingWakeForRollback` (Y5).** The ONE named rollback wake-abort operation used by
  `RollbackRecoveryAssignmentPlan`, `RollbackParticipantSetup`, and `RollbackTemplateRefreshSetup`. It cancels the exact
  `WakeCompleteEvent`, departs a still-`WAKING` miner `WAKING -> OFFLINE` via the legal `T12` `ValidationAbort` trigger
  (`reason = validation_abort`, declared in `STAGE_01_MINER_STATE_MACHINE.md` §3 — NOT the assignment
  `termination_reason`), binds the EXACT assignment version, lets `ApplyMinerStateTransition` close the `WAKING` residency
  + charge transition energy once (no census change), performs the SINGLE canonical assignment close, restores the
  before-image, and returns `wake_abort_completed` / `wake_abort_failed`. It resolves a `WAKING` miner UNCONDITIONALLY
  (Y4) — a `CLOSED`/revoked/detached head does not make a `WAKING` miner safe — and is the SOLE owner of the assignment
  close for a rollback (the transition hook changes miner state only for this form).
- **Historical freeze.** Stage-1A–1X lettered artifacts are unchanged; Stage-1Y supersessions are recorded in
  `STAGE_01Y_SUPERSESSION_REGISTER.md`.

## Stage-1Z terminology addendum (retry-lifecycle & rollback-snapshot lock)

- **`setup_retry_record` / `setup_retry_records` (Z1).** `setup_retry_record = { SetupRetryID, setup_kind, RoundID,
  TemplateID_at_seat, TemplateRefreshSetupID, retry_generation, event_ref, status : SetupRetryStatus,
  target_disposition }`; `setup_retry_records : SetupRetryID -> setup_retry_record` is the SINGLE setup-retry registry,
  replacing the Y-era `applied_setup_retry_ids` and `setup_retry_status_by_id`. Lifecycle: the seating procedure publishes
  `status = SEATED` (atomically, after a successful `ScheduleEvent`); `SetupRetryEvent`'s first dispatch flips
  `SEATED -> APPLYING` and executes; the captured target result sets `APPLIED` / `SUPERSEDED` / `ABORTED` / `CANCELLED`.
  A replay is duplicate-suppressed IFF the status is already non-`SEATED` (a SEATED record's first dispatch always runs).
  "applied" ≡ `status = APPLIED`, set only after the target result is known.
- **`coverage_custody_before_image` — pre-mutation snapshot (Z2/I20).** The I8a/I8b snapshot captured immediately BEFORE
  `CreatePendingAssignment` (or a plan-bound constructor) mutates the ledgers. Rollback restores the exact pre-constructor
  values (invariant I20); on a creation failure it is discarded and no item is created.
- **Nullable `WakeEventRef` + `wake_result` (Z3).** A setup rollback item's `WakeEventRef` is `WakeEventRef | null`
  (null when `StartWake` returned `wake_schedule_failed_before_transition`; the returned already-cancelled ref when
  `wake_transition_failed_after_seat`; the actual ref when `wake_seated`), paired with the structured `wake_result`.
  `AbortPendingWakeForRollback` cancels it ONLY when non-null and still pending — no undefined map lookup.
- **`assignment_effect_policy` (Z4).** `ApplyMinerStateTransition` parameter in `{ EDGE_DEFAULT, STATE_ONLY_ROLLBACK }`
  (default `EDGE_DEFAULT`). `STATE_ONLY_ROLLBACK` (passed only by `AbortPendingWakeForRollback`) makes the hook change
  miner state / residency / energy / census only, performing NO assignment mutation; the operation then performs the
  single canonical close. Every other caller uses `EDGE_DEFAULT`.
- **`waking_origin_assignment_ref` (Z5).** `MinerID -> assignment_version_ref`, set on entry to `WAKING` and cleared on any
  `WAKING` departure inside `ApplyMinerStateTransition`. The `T12` `ValidationAbort` rollback is legal only when
  `miner_state = WAKING` and this association equals the rollback item's exact `assignment_version_ref` — even for a
  `CLOSED` / detached head; a mismatch returns `wake_abort_failed` and departs no miner.
- **`setup_rollback_item` / `setup_transaction.rollback_items` (Z6).** `setup_rollback_item = { MinerID, AssignmentID,
  assignment_version, pre_wake_state, before_image, WakeEventRef (| null), wake_result, rollback_envelope }`;
  `setup_transaction = { rollback_envelope, rollback_items : [setup_rollback_item] }` replaces the Y-era parallel maps
  (`assignment_by_miner` / `wake_by_miner` / `before_image_by_miner` / `prior_states`). Every created assignment has
  exactly one complete item appended BEFORE `StartWake` — no partial-map state.
- **Historical freeze.** Stage-1A–1Y lettered artifacts are unchanged; Stage-1Z supersessions are recorded in
  `STAGE_01Z_SUPERSESSION_REGISTER.md`.

## Stage-1AA terminology addendum (retry-terminalisation & transition-policy identity lock)

- **`round_aborted(abort_record)` (AA1).** The SINGLE canonical result of `RoundAbort` (`abort_record =
  abort_record(RoundID, TemplateID, reason)`), replacing the bare `abort_record`; `RoundAbort` is the sole abort producer
  and no bare `abort_record` or prose alias appears anywhere. Every procedure that PROPAGATES the result to its own caller
  — `SetupRetryEvent`, `PrepareParticipantsForNewRound`, `ContinueTemplateRefreshAssignmentSetup`, `TemplateRefresh`,
  `FullRangeExhaustNoSolution` — lists `round_aborted` in its RETURNS union and classifies the exact
  `round_aborted(abort_record)` result via `RETURN CALL RoundAbort`. The recovery paths (`CompleteSecurityRecovery`
  branch D, `ApplyRecoveryWorkAfterEpilogue`, `ApplyRecoveryAssignmentContinuationAfterEpilogue`) instead CALL the same
  canonical `RoundAbort` for effect (`recovery_finalising = true`) and return their own recovery-specific disposition. A
  target's `round_aborted` maps `setup_retry_record.status = ABORTED`, never `CANCELLED`.
- **`CancelSetupRetriesForRound` (AA2).** The one named terminaliser `CancelSetupRetriesForRound(RoundContext,
  closing_RoundID, cancellation_reason, dispatch_or_run_hook_context)`, invoked by `CloseRoundAssignments`. For each
  `setup_retry_record` of `closing_RoundID`: a `SEATED` record has its still-queued `event_ref` cancelled and becomes
  `CANCELLED` (`target_disposition = cancellation_reason`); an `APPLYING` record is flagged `terminal_closure_pending` and
  left for its executing handler to finish `ABORTED` / `CANCELLED`. `CloseRoundAssignments` also lists `SetupRetryEvent`
  among the events cancelled at closure. Postcondition: no closed/superseded round leaves a `SEATED` retry record.
- **`terminal_closure_pending` (AA2).** A boolean field of `setup_retry_record` (default `false`), set by
  `CancelSetupRetriesForRound` on an `APPLYING` record when its round closes; `SetupRetryEvent`'s classification honours it,
  finishing the record `ABORTED` (target `round_aborted`) or `CANCELLED` (any other captured disposition) — never `APPLIED`.
- **Stale-`RoundID` terminalisation in `SetupRetryEvent` (AA3).** The guard order resolves the record and verifies the
  payload BEFORE the stale-`RoundID` check, so a stale dispatch of a known `SEATED` record is terminalised — `SUPERSEDED`
  (round advanced) or `CANCELLED` (closed round), `target_disposition = setup_retry_stale_noop` — rather than left `SEATED`.
  A malformed/mismatched payload may stale-noop without terminalising a record it cannot own.
- **`assignment_effect_policy` in `TransitionEventID` (AA4, design A).** `assignment_effect_policy in { EDGE_DEFAULT,
  STATE_ONLY_ROLLBACK }` is a FIELD of the immutable `TransitionEventID`; two otherwise-identical transitions with
  different assignment side effects are distinct replay ids, so the applied/replay registry never aliases them.
- **Legal `STATE_ONLY_ROLLBACK` tuple + `illegal_state_only_rollback_tuple` (AA5).** `STATE_ONLY_ROLLBACK` is legal IFF
  `old_state = WAKING` AND `new_state = OFFLINE` AND `reason = validation_abort` AND `assignment_ref` is exact and non-null
  AND `waking_origin_assignment_ref[MinerID] = assignment_ref`; any other use is rejected `illegal_transition` (logged
  `illegal_state_only_rollback_tuple`) with no mutation. Every non-rollback caller uses `EDGE_DEFAULT`.
- **`RollbackItemID` + keyed `rollback_items` + `NOT_ATTEMPTED` (AA6).** `setup_rollback_item` gains a `RollbackItemID` and
  `setup_transaction = { rollback_envelope, rollback_items : map RollbackItemID -> setup_rollback_item }`. An item is
  created `WakeEventRef = null` / `wake_result = NOT_ATTEMPTED` and added under its key BEFORE `StartWake`; the stored record
  is then updated explicitly by key. `wake_result in { NOT_ATTEMPTED, wake_seated, wake_schedule_failed_before_transition,
  wake_transition_failed_after_seat }`. Rollback consumes the stored keyed record (iterating deterministically by
  `RollbackItemID`), never a local-variable alias.
- **Historical freeze.** Stage-1A–1Z lettered artifacts are unchanged; Stage-1AA supersessions are recorded in
  `STAGE_01AA_SUPERSESSION_REGISTER.md`.

## Stage-1AB terminology addendum (retry-record persistence & exact abort-contract lock)

- **Exact `round_aborted(abort_record)` contract (AB1).** Every direct value-propagator's RETURNS union lists the EXACT
  shaped result `round_aborted(abort_record)`, never the bare constructor `round_aborted`. `SetupRetryEvent`'s RETURNS names
  the shaped result once and ENUMERATES the re-run target dispositions explicitly. A bare `round_aborted` may appear only as
  an exact pattern match, a constructor invocation, or a type declaration — each carrying its payload.
- **Capture-before-persist abort (AB2).** In `SetupRetryEvent`, each guard-driven abort executes
  `SET disp <- CALL RoundAbort(...)` FIRST and only then persists `status <- ABORTED` and `target_disposition <- disp` by
  key; the stored `target_disposition` is the exact `round_aborted(abort_record(RoundID, TemplateID, reason))` returned by
  `RoundAbort` (never a token written before the abort exists).
- **Keyed persistent lifecycle update (AB3).** `SET rec <- setup_retry_records[SetupRetryID]` is a READ-ONLY snapshot;
  record-reference write semantics are not assumed. The seat is the only CREATE; every subsequent change to `status`,
  `target_disposition`, `terminal_closure_pending`, or `event_ref` is an explicit keyed `UPDATE setup_retry_records[...]`.
  `CancelSetupRetriesForRound` iterates `SetupRetryID`s (not detached records) and updates by key.
- **Post-target re-read (AB4).** After a `SetupRetryEvent` target returns, the handler RE-READS
  `post_target_rec <- setup_retry_records[SetupRetryID]` and classifies on the persisted `terminal_closure_pending`, because
  the target may have synchronously closed the round and persisted that flag by key; a record whose round closed can never
  finish `APPLIED`.
- **`dispatched_event_ref` — dispatch ownership (AB5).** The canonical identity of the dispatched `SetupRetryEvent`
  (derivable from `dispatch_envelope`), equal to the seat-stored `rec.event_ref` for a genuine dispatch. Ownership: unknown
  id → stale no-op; `dispatched_event_ref ≠ rec.event_ref` (foreign/replayed) → stale no-op leaving the record `SEATED` for
  its genuine event; genuine event with a mismatched payload → integrity abort (`setup_retry_payload_integrity_failure`)
  that terminalises the record `ABORTED` and cancels any residual event ref. A `SEATED` record's only event is never
  consumed while the record stays `SEATED`.
- **`setup_retry_payload_integrity_failure` (AB5).** The declared `RoundAbort` reason for the AB5-C integrity abort — the
  genuine owning event's payload disagrees with the immutable record.
- **Closure post-conditions (AB6).** `CancelSetupRetriesForRound` uses keyed updates and clears a cancelled record's
  `event_ref` to null; after it completes for a closing round, no record is `SEATED`, no `SEATED` record holds a queued
  `event_ref`, every terminalised record has a terminal `target_disposition`, and every `APPLYING` record has
  `terminal_closure_pending` persisted.
- **Historical freeze.** Stage-1A–1AA lettered artifacts are unchanged; Stage-1AB supersessions (including the corrected
  Stage-1AA audit claims, AB7) are recorded in `STAGE_01AB_SUPERSESSION_REGISTER.md`.

## Stage-1AC terminology addendum (event-reference & retry-state closure lock)

- **`EventRef` (AC1).** The one canonical immutable reference to a queued ordinary event:
  `EventRef = (envelope_namespace, event_type, event_time, delta_cycle, microphase, seq)`. `ScheduleEvent` derives exactly
  one and returns `scheduled(EventRef, …)` (AC1 named the second slot `envelope`; AD3 replaces it with the central
  `queued_event_record` — see the Stage-1AD addendum below). The same type is used by cancellation, stored retry ownership
  (`seat_event_ref`), and dispatch ownership (`dispatched_event_ref`). `event_ref`, `envelope`, and `dispatched_event_ref`
  are not silently interchangeable — an envelope is the full queued record; an EventRef is its canonical six-field identity.
- **`current_event_ref` / dispatcher-owned `dispatched_event_ref` (AC2).** `EventQueueContext.current_event_ref : EventRef |
  null` is set by `ProcessEventTime` to `EventRef(e)` before dispatching `e`, injected as `dispatched_event_ref`, and
  cleared after the handler returns. A handler (e.g. `SetupRetryEvent`) receives `dispatched_event_ref` from this
  dispatcher-owned path — never from its own payload — as a mandatory input.
- **`seat_event_ref` + `event_queue_status` (AC8).** A `setup_retry_record` carries `seat_event_ref : EventRef` (immutable,
  set at seat) and `event_queue_status : EventQueueStatus`. Ownership comparisons use `seat_event_ref`;
  cancellation/consumption changes only `event_queue_status`, never erasing the historical seat EventRef. This pair replaces
  the Z1-era single `event_ref` record field.
- **`EventQueueStatus` (AC8).** `{ QUEUED, DISPATCHING, CONSUMED, CANCELLED }` — the queue-lifecycle state of a retry
  record's seated event, kept separate from the immutable `seat_event_ref` identity.
- **`SetupRetryStatus` transition table + `SetSetupRetryStatus` (AC7).** Authoritative table:
  `SEATED → {APPLYING, CANCELLED, SUPERSEDED}`; `APPLYING → {APPLIED, SUPERSEDED, CANCELLED, ABORTED}`;
  `APPLIED`/`SUPERSEDED`/`CANCELLED`/`ABORTED` terminal. `SetSetupRetryStatus` is the sole status writer and rejects every
  illegal transition — especially a terminal → terminal rewrite such as `CANCELLED → ABORTED` — with no mutation
  (`setup_retry_status_transition_rejected`, logging `illegal_setup_retry_status_transition`).
- **Terminal-replay-before-integrity guard order (AC3) + record-scoped integrity (AC4/AC5).** `SetupRetryEvent` resolves the
  record, verifies EventRef ownership, then suppresses a non-SEATED replay BEFORE any payload-integrity abort; stale/closed
  disposition is decided from the immutable record fields (never the payload), so a corrupted historical retry is
  terminalised and never aborts a later round, and a genuine malformed dispatch cannot leave its record SEATED.
- **Legal abort status path (AC6).** A current SEATED retry about to run any aborting guard first moves `SEATED → APPLYING`,
  then `APPLYING → ABORTED` after `RoundAbort` (with `CancelSetupRetriesForRound` persisting `terminal_closure_pending`).
- **`setup_retry_payload_integrity_failure` (AC5).** The declared `RoundAbort` reason for the AC5-C integrity abort of a
  current owned SEATED record whose genuine dispatch envelope/payload is corrupt.
- **Historical freeze.** Stage-1A–1AB lettered artifacts are unchanged; Stage-1AC supersessions are recorded in
  `STAGE_01AC_SUPERSESSION_REGISTER.md`.

## Stage-1AD terminology addendum (queued-event lifecycle & payload lock)

- **`queued_event_record` (AD1).** The central binding of a queued ordinary event:
  `queued_event_record = (event_ref : EventRef immutable, event_type, dispatch_envelope : immutable complete
  ordinary-event envelope, immutable_payload, queue_status : EventQueueStatus)`. Created by `ScheduleEvent` and stored in the
  registry keyed by its `EventRef`. It is the single authoritative binding of a queued event's identity, envelope, handler
  payload, and queue lifecycle state.
- **`queued_event_registry` (AD1).** `map EventRef → queued_event_record` — the ONE authoritative queue-status source. A
  `setup_retry_record` no longer stores its own queue state; its current queue state IS
  `queued_event_registry[seat_event_ref].queue_status`. The Stage-1AC per-record `event_queue_status` mirror is removed.
- **`EventQueueStatus` transition table (AD1, supersedes the AC8 enum's ownership).** `{ QUEUED, DISPATCHING, CONSUMED,
  CANCELLED }` with transitions `QUEUED → {DISPATCHING, CANCELLED}`; `DISPATCHING → CONSUMED`; `CONSUMED` and `CANCELLED`
  terminal. `ProcessEventTime` is the sole writer of the dispatch-lifecycle transitions (`DISPATCHING`, `CONSUMED`);
  `CancelSetupRetriesForRound` performs the only `QUEUED → CANCELLED` cancellation (AD4/AD9).
- **`immutable_payload` (AD2).** The complete set of caller-supplied handler arguments captured by `ScheduleEvent` at
  seating (for a `SetupRetryEvent` exactly `RoundID`, `setup_kind`, `SetupRetryID`, `TemplateID_at_seat`,
  `TemplateRefreshSetupID`, `retry_generation`, `reason`) and delivered verbatim by `ProcessEventTime` at dispatch — payload
  at dispatch equals payload at seating.
- **`OrdinaryDispatchContext` (AD5).** `(dispatch_envelope, dispatched_event_ref)`, constructed and owned by
  `ProcessEventTime` from the `queued_event_record` and its `EventRef`. Design B delivery: every ordinary handler receives
  `dispatch_envelope`; `dispatched_event_ref` is delivered only to a handler whose declared signature includes it (currently
  only `SetupRetryEvent`). No undeclared named argument is injected into a handler that omits it.
- **`ScheduleEvent` result union (AD3).** `scheduled(EventRef, queued_event_record) | rejected_finalised_time |
  post_horizon_event_rejected | rejected_post_epilogue_not_strictly_later | rejected_backward_time` — the complete declared
  set; the success variant carries the canonical `EventRef` and the central `queued_event_record` (was
  `scheduled(EventRef, envelope)`).
- **`HandleDispatchIntegrityFailure` / `dispatch_integrity_failure` (AD8).** The one dispatcher-owned integrity path, called
  by `ProcessEventTime` only when a registry entry is detected corrupt. It records the declared terminal disposition
  `dispatch_integrity_failure`, builds a COMPLETE integrity envelope from the trusted `EventRef` fields, and (for a
  `SetupRetryEvent` whose `SetupRetryID` resolves) terminalises the record — a current nonterminal-round record via a
  current-round integrity abort with that complete envelope, an old/terminal-round record without aborting the current round.
  A malformed untrusted envelope never becomes the transition identity for round closure.
- **Historical freeze.** Stage-1A–1AC lettered artifacts are unchanged; Stage-1AD supersessions (including the AC8
  per-record `event_queue_status` mirror and the incomplete Stage-1AC audit claims) are recorded in
  `STAGE_01AD_SUPERSESSION_REGISTER.md`.
