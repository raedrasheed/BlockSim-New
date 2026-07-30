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
Catalogue" denotes the separate document defining I1..I16.

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
| REGISTERED | Miner state (1 of 8) | Miner is admitted to PoCol with a MinerID but is not described by any more specific active/reserve/idle state. Mutually exclusive with the other seven miner states. | Preamble; Scope §E |
| RESERVE | Miner state (2 of 8) | Registered and available but not currently assigned an active range; draws no active hashing power until promoted. | Preamble; Scope §B.2, §E |
| ACTIVE_HASHING | Miner state (3 of 8) | Miner is actively hashing an assigned range. The ONLY state that contributes to the active hash rate and to the P_hash·t_hash term. | Preamble; Scope §0.3, §E |
| EXHAUSTED_PENDING | Miner state (4 of 8) | Miner has exhausted (or reported completion of) its assigned range and awaits reassignment or round resolution. | Preamble; Scope §E |
| LOW_POWER_LISTEN | Miner state (5 of 8) | Miner monitors round progress at reduced power rather than hashing; contributes to P_listen·t_listen and NOT to the active hash rate. | Preamble; Scope §B.1, §E |
| WAKING | Miner state (6 of 8) | Transitional state entered when leaving a reduced-power state to resume hashing; incurs wake latency and the P_wake·t_wake and E_transition terms. | Preamble; Scope §B.3, §E |
| OFFLINE | Miner state (7 of 8) | Miner is not participating; contributes to the P_offline·t_offline term and not to the active hash rate. | Preamble; Scope §E |
| DISQUALIFIED | Miner state (8 of 8) | Miner has been excluded from participation; produces no valid contribution to the round. | Preamble; Scope §E |
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
| Adversarial share | q_adv(t) [dimensionless, 0..1] | Fraction of active hash rate that is adversarial: q_adv(t) = H_adversarial(t) / (H_honest(t) + H_adversarial(t)). | This document (§1) |
| Security floor | Modeled bound | A modeled lower bound on active honest hash rate that participation reduction must not violate. Monitored by the protocol; its enforcement soundness is out of scope at Stage 1. | Scope §B.4, §C |
| Reserve miner | Miner in RESERVE | A registered miner held in RESERVE: available but not actively hashing, promotable to ACTIVE_HASHING when needed. | Scope §B.2 |
| Wake latency | Duration [s] | The delay a miner incurs while in WAKING before it resumes ACTIVE_HASHING after leaving a reduced-power state. | Scope §B.3 |
| Transition | Event / energy term | A change of miner state that carries a transition energy cost E_transition,i (e.g. entering/leaving low-power or waking). | Scope §0.3, §B.3 |
| Coordination energy | E_coordination,i [J] | Per-miner energy attributed to protocol coordination (assignment, leasing, commitments, certificates), distinct from hashing, listening, wake, and offline terms. | Scope §0.3 |
| Progress commitment | Attestation object | A miner-emitted attestation of how far its assigned range has been searched. Treated ONLY as a modeled progress-verification abstraction. | Scope §B.7 |
| Modeled progress-verification abstraction | Bounded term | The bounded, Stage-1 term for progress commitments and early-stop certificates. It is explicitly NOT a cryptographic proof and NOT a proof of range exhaustion. | Preamble; Scope §B.7, §C |
| Checkpoint frontier | Progress marker | The boundary between the searched prefix and the unsearched suffix of a range, as attested by progress commitments; the modeled position up to which coverage is claimed. | This document (§1) |
| Early-stop certificate | Certificate object | A modeled summary of sufficient covered progress justifying a halt to active hashing for a round before brute-force exhaustion. A modeled abstraction only; carries no security or soundness guarantee at Stage 1. | Scope §B.8, §C |
| Target | Threshold value | The acceptance threshold for a round: a solution is valid only if its digest satisfies the target under the committed template. | Scope §A.5 |
| Difficulty | Fixed parameter | The parameter determining how hard the target is to satisfy. In the confirmatory design difficulty stays FIXED; dynamic-difficulty behavior is out of scope and not confirmed. | Preamble; Scope §C |
| Template refresh | Procedure / round state | Replacement of the committed immutable template with a new immutable template (new TemplateID), transitioning through TEMPLATE_REFRESH. The only sanctioned way mined content changes. | Scope §A.7 |
| Continuous full-participation control | Baseline scenario | The reference scenario in which all miners hash continuously over the fixed horizon. Its modeled energy is the A1 value, 8.420833333 kWh, and serves as E_continuous_control. | Preamble; Scope §0.2, §D |
| ΔE | ΔE [kWh] | The Stage-1 comparison quantity ΔE = E_continuous_control − E_idle_policy. Defined at Stage 1; no particular achieved value is claimed. Any positive ΔE must arise from reduced active power-time, never from partitioning. | Preamble; Scope §0.3, §D |
| Zero-block run | Run classification | A modeled run in which no block is accepted over the horizon (e.g. resolving to ROUND_EXHAUSTED without acceptance), so block-normalised metrics have no accepted block to normalise against. | This document (§1) |
| NA (undefined block-normalised metric) | Sentinel value | The sentinel recorded for a block-normalised metric that is undefined because the run produced zero accepted blocks; NA denotes "undefined", not zero. | This document (§1) |
| Physical run | Run classification | A modeled run evaluated under the physical/energy accounting (real-power-time terms of the energy model), as opposed to a purely abstract or block-normalised view. | This document (§1) |
| Master seed | Seed value | The root seed from which per-run allocation randomness is derived deterministically, so that assignment/allocation draws are reproducible across runs. | This document (§1) |
| Allocation exponent | alpha (α) [dimensionless] | The exponent parameter governing the shape of the range-allocation distribution across miners (e.g. how range sizes scale). A modeled allocation parameter; carries no fairness or incentive claim at Stage 1. | This document (§1) |

---

## 2. Consistency notes

- **Active hash rate is state-restricted.** Only `ACTIVE_HASHING` miners contribute to
  `H_active(t)`, and correspondingly `H_active(t) = H_honest(t) + H_adversarial(t)` over the
  active-hashing population. `LOW_POWER_LISTEN`, `RESERVE`, `WAKING`, `OFFLINE`,
  `EXHAUSTED_PENDING`, `REGISTERED`, and `DISQUALIFIED` contribute nothing to the active
  hash rate.
- **Energy attribution matches the normative model.** Each state maps to at most one power
  term of the energy model of Scope §0.3: hashing → `P_hash·t_hash`; low-power listening →
  `P_listen·t_listen`; waking → `P_wake·t_wake` (plus `E_transition`); offline →
  `P_offline·t_offline`; coordination overhead → `E_coordination`.
- **Modeled abstractions only.** "Progress commitment", "checkpoint frontier", and
  "early-stop certificate" are all instances of the modeled progress-verification
  abstraction. None is a cryptographic proof and none establishes range exhaustion,
  security, or incentive properties at Stage 1 (Scope §C).
- **A1 discipline.** `continuous full-participation control` equals the A1 value
  (8.420833333 kWh). `ΔE` is measured against this baseline and any reduction is
  attributable to reduced active power-time, never to nonce-domain partitioning.
