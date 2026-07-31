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
Catalogue" denotes the separate document defining I1..I17.

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
- **Single settled-census security evaluation (`FinalizeTimestampSecurityCensus`, H3).** A miner
  transition never schedules its own floor decision; instead the hook sets
  `security_evaluation_required[(event_time, delta_cycle)]`. Exactly ONE
  `FinalizeTimestampSecurityCensus` runs in microphase 5 per settled `(event_time, delta_cycle)`,
  reads the FINAL settled census, and calls `SecurityFloorEvaluate` at most once. Intermediate
  same-time census values are retained for AUDIT ONLY and never drive a round-state transition.
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
