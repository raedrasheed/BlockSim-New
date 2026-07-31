# Stage 1 — PoCol Protocol Scope

**Document status:** Stage-1 specification-only. This document DEFINES and DELIMITS the
PoCol protocol at Stage 1. It does NOT claim that any mechanism described here is
implemented, validated, secure, fair, or incentive-compatible. Stage 1 SPECIFIES the
protocol; it does NOT demonstrate any property of it.

---

## 0. Preliminaries

### 0.1 Naming rule (binding)

The algorithm name is ALWAYS **PoCol**. No replacement, suffixed, or derivative name is
permitted anywhere in this documentation set. In particular, the strings "PoCol-E",
"Energy-Aware PoCol", and "Enhanced PoCol" are prohibited.

The low-power mechanism introduced in this stage is described ONLY as **"the idle policy
within PoCol"**, or equivalently **"PoCol with the idle policy enabled"**. The idle policy
is an operating policy that lives INSIDE PoCol. It is not a new algorithm, not a variant,
and not a fork of PoCol.

### 0.2 Accepted baseline (must not be contradicted)

Nonce-domain partitioning **alone** does NOT reduce total fixed-horizon energy. The
frozen reference setting for all Stage-1 reasoning is:

| Quantity | Symbol | Value |
|---|---|---|
| Aggregate hash rate | — | 141 TH/s |
| Mining efficiency | — | 21.5 J/TH |
| Active power | P_active | 3031.5 W |
| Fixed horizon | T | 10,000 s |
| Continuous full-participation energy | E_continuous_control | 8.420833333 kWh |

The final row is the **accounting invariant A1**: under continuous full participation over
the fixed horizon, total energy is fixed at 8.420833333 kWh regardless of how the nonce
domain is partitioned among miners. Any energy reduction claimed for PoCol MUST arise from
**reduced active power-time** (low-power listening, reserve operation, or reduced
participation), and NEVER from partitioning itself.

The idle policy is NOT yet proven to preserve security, service, incentives, or deployment
properties. Those properties are out of scope at Stage 1 (Section C).

### 0.3 Energy model (normative)

Per-miner energy is the **state-complete sum** over the eight miner states

    E_i = Σ_{s∈States} (P_{i,s} · t_{i,s})
        + E_transition,i
        + E_coordination,i
        + E_verification,i

where `States = {REGISTERED, RESERVE, ACTIVE_HASHING, EXHAUSTED_PENDING, LOW_POWER_LISTEN,
WAKING, OFFLINE, DISQUALIFIED}` and each state has exactly one residency power `P_{i,s}` per
the canonical state-to-power mapping of `STAGE_01_ENERGY_MODEL_SPECIFICATION.md` §1.0
(`REGISTERED = P_registered = P_listen`; `RESERVE = P_reserve = P_listen`, **not**
`P_offline`; `ACTIVE_HASHING = P_hash`; `EXHAUSTED_PENDING = P_hash`;
`LOW_POWER_LISTEN = P_listen`; `WAKING = P_wake`; `OFFLINE = P_offline`;
`DISQUALIFIED = P_offline`). `E_verification,i` is a **separate event-energy term**
(validating a received early-stop certificate while the miner remains in `ACTIVE_HASHING`;
CR2), not folded into `P_hash·t_hash`. The durations satisfy `Σ_{s∈States} t_{i,s} = T` with
**no** residual / `t_other` bucket. With total energy `E_total = Σ_i E_i` and the Stage-1
comparison quantity

    ΔE = E_continuous_control − E_idle_policy.

Only the `ACTIVE_HASHING` state contributes to the active hash rate. All energy claims in
this stage are stated against the modeled quantities above, not against real-hardware
measurements.

---

## A. Existing PoCol protocol concepts (INCLUDED)

These concepts are part of PoCol as it stands prior to the idle policy. Stage 1 restates
them so that the idle-policy additions in Section B attach to a fixed, unambiguous base.

1. **Common immutable block template.** All miners in a round mine against one identical,
   immutable block template. Once committed for a round, the template content does not
   change; a new template requires a template refresh (item 7).
2. **TemplateID.** A stable identifier binding a specific immutable block template. Every
   assignment, commitment, and accepted block in the round references its TemplateID so
   that work provably targets one agreed template.
3. **Disjoint nonce-range assignment.** The nonce domain is partitioned into disjoint
   ranges, and each participating miner is assigned one or more ranges that do not overlap
   any other miner's ranges for that template. Partitioning organises the search; per the
   accepted baseline it does NOT by itself reduce fixed-horizon energy.
4. **Miner registration.** Miners join PoCol through a registration procedure that
   establishes a MinerID and admits the miner to round participation. Registration is the
   precondition for receiving any assignment.
5. **Target validation.** A candidate solution is checked against the round target: a
   solution is valid only if its digest satisfies the target under the committed template.
   Target validation is the acceptance predicate for a proposed block.
6. **Accepted-block handling.** A valid solution is propagated as modeled discrete events
   (early-stop certificate arrival, then full-block arrival) and is accepted only at the
   **modeled acceptance point** — a designated coordinator/validator, or a clearly identified
   canonical local view — after the full block arrives and validates. Block acceptance is
   **NOT** at solution-discovery time. Accepted-block handling then records the accepted
   block, closes the round, and moves round state toward `ROUND_ACCEPTED`; only exactly-equal
   acceptance timestamps break by `candidate_hash`, then `MinerID`.
7. **Template refresh.** PoCol replaces the committed template with a new immutable
   template (a new TemplateID), transitioning through `TEMPLATE_REFRESH`. Refresh is the
   only sanctioned way the mined content changes.

---

## B. New operating-policy concepts — the idle policy within PoCol (INCLUDED, SPECIFIED ONLY)

These concepts constitute **the idle policy within PoCol**. They are specified here as
protocol structure. They are NOT claimed to be implemented, and none of the properties in
Section C is claimed on their behalf. The idle policy exists to reduce **active
power-time**, consistent with the accepted baseline and A1.

1. **Low-power listening.** A participating miner may occupy the `LOW_POWER_LISTEN` state,
   in which it monitors round progress at reduced power rather than hashing. Listening
   contributes to `P_listen,i * t_listen,i` and NOT to the active hash rate.
2. **Reserve miners.** Registered miners may be held in `RESERVE`: admitted and available
   but not currently assigned an active range, so they draw no active hashing power until
   promoted.
3. **Wake-up transitions.** A miner leaving a reduced-power state to resume hashing passes
   through `WAKING`, incurring a wake latency and wake energy (`P_wake,i * t_wake,i`) plus
   any `E_transition,i`.
4. **Security-floor monitoring.** The protocol monitors a security floor — a modeled lower
   bound on active honest hash rate that participation reduction must not violate.
   Monitoring is specified; enforcement soundness is out of scope (Section C).
5. **Range leases.** An assignment of a nonce range may be granted as a time-bounded
   **lease** (with a lease_start and lease_expiry), after which the range may be reclaimed
   or renewed rather than held indefinitely.
6. **Range reassignment.** The **unsearched suffix** of a leased or abandoned range may be
   reassigned to other miners (for example, on lease expiry, abandonment, revocation, miner
   departure, assignment conflict, or security recovery) so that coverage of the nonce domain
   can be maintained without continuous full participation. A fully exhausted range is
   **completed** (`custody_status = completed`) and is NOT reassignable; exhaustion is never a
   reassignment reason.
7. **Progress commitments.** A miner may emit a **progress commitment** attesting how far
   its assigned range has been searched. This is treated ONLY as a *modeled
   progress-verification abstraction*; it is NOT a cryptographic proof of range
   exhaustion.
8. **Early-stop certificates.** The protocol may form an **early-stop certificate** generated
   ONLY from a found valid candidate solution satisfying the current target (never from
   progress commitments, covered progress, or a claimed exhaustion). It is **the only
   solution-triggered mechanism that authorises miners to stop hashing before full-block
   propagation completes.** Miners may also cease hashing for reasons that are not
   solution-triggered: own-range exhaustion; assignment revocation; round acceptance; round
   abort; or offline/disqualification transitions. As with progress commitments, this is a
   modeled abstraction only and carries none of the Section C guarantees.

---

## C. Out-of-scope properties at Stage 1 (NOT CLAIMED)

Each item below is explicitly **out of scope at Stage 1 and is NOT claimed to be
achieved**. Where a mechanism in Section B touches one of these areas, it is specified as
structure only; no soundness, security, fairness, or deployment property follows from that
specification.

1. **Complete cryptographic proof of range exhaustion** — NOT claimed. Range progress is
   handled only via the modeled progress-verification abstraction.
2. **Real ASIC power-state enforcement** — NOT claimed. Miner states are modeled states,
   not enforced hardware power states.
3. **Proven incentive compatibility** — NOT claimed. No incentive-compatibility result is
   asserted for the idle policy or for base PoCol. Relatedly, **reward eligibility is NOT
   SPECIFIED AT STAGE 1**: all reward and penalty components are deferred to Stage 5, and the
   only reward-related fact recorded at Stage 1 is that a valid solution may be recorded as
   having a solver identity (see `STAGE_01_REWARD_PENALTY_INTERFACE.md`).
4. **Proven Sybil resistance** — NOT claimed.
5. **Full chain-wide consensus-security proof** — NOT claimed. No end-to-end
   consensus-security proof is provided at Stage 1.
6. **Production deployment readiness** — NOT claimed. Nothing here asserts readiness for
   deployment.
7. **Dynamic-difficulty confirmation** — NOT claimed. Difficulty stays FIXED in the
   confirmatory design; dynamic-difficulty behavior is not confirmed.
8. **Real-hardware energy measurements** — NOT claimed. All energy quantities are modeled
   under the normative energy model, not measured on real hardware.

No text in this document should be read as claiming that PoCol, or the idle policy within
PoCol, is implemented, validated, secure, fair, or incentive-compatible.

---

## D. Relationship to the accepted A1 invariant

Invariant A1 fixes continuous full-participation energy over the fixed horizon at
8.420833333 kWh and establishes that this value is **invariant to how the nonce domain is
partitioned**. Consequently:

- Disjoint nonce-range assignment (Section A, item 3) is a *scheduling and coordination*
  device. It organises which miner searches which region of the nonce domain. By A1 it
  does not, on its own, change `E_total` over the horizon.
- Therefore the idle policy within PoCol targets the ONLY term that A1 leaves free: the
  **active power-time**. It seeks to reduce `Σ_i P_hash,i * t_hash,i` by moving miners into
  `LOW_POWER_LISTEN`, holding them in `RESERVE`, or otherwise reducing participation, while
  paying the smaller listening, wake, transition, coordination, and verification terms of the
  energy model.
- The comparison quantity is `ΔE = E_continuous_control − E_idle_policy`, where
  `E_continuous_control` is exactly the A1 value (8.420833333 kWh) under continuous full
  participation, and `E_idle_policy` is the modeled total under PoCol with the idle policy
  enabled.
- **Matched-control basis.** The continuous full-participation control and the idle-policy
  scenario match on: installed/registered aggregate hash-rate capacity at the start; miner
  hardware and efficiency; fixed difficulty; target; fixed observation horizon; and
  workload/template rules where applicable. They do **not** execute the same total work: under
  the idle policy `H_active(t)` may decrease, realised hash evaluations may decrease, and
  accepted-block count, block interval, and security exposure may change. A fixed-capacity,
  fixed-horizon **energy** comparison (`ΔE`) is therefore **not** by itself a service-equivalent
  or security-equivalent comparison; service and security non-inferiority are evaluated only
  after the frozen experiments.

Any positive ΔE claimed at later stages must be attributable to reduced active power-time
under the energy model, NEVER to partitioning. At Stage 1, ΔE is defined but no particular
value of ΔE is claimed as achieved or validated. The security-floor monitoring of Section B
exists precisely because reducing active power-time must not be allowed (at later stages)
to drop active honest hash rate below the modeled floor; whether that constraint is
actually preserved is out of scope here (Section C).

---

## E. Reference identifiers used in this document

- **Miner states (8, mutually exclusive):** `REGISTERED`, `RESERVE`, `ACTIVE_HASHING`,
  `EXHAUSTED_PENDING`, `LOW_POWER_LISTEN`, `WAKING`, `OFFLINE`, `DISQUALIFIED`.
- **Round states (10):** `ROUND_INITIALISING`, `TEMPLATE_COMMITMENT`, `ASSIGNMENT`,
  `HASHING`, `SECURITY_RECOVERY`, `SOLUTION_PROPAGATION`, `ROUND_ACCEPTED`,
  `ROUND_EXHAUSTED`, `TEMPLATE_REFRESH`, `ROUND_ABORTED`.
- **Invariants:** referenced by ID as I1..I17, defined in the separate Invariant Catalogue;
  the accounting invariant A1 is stated in Section 0.2.

Terminology for every symbol and term above is defined in
`STAGE_01_TERMINOLOGY.md`.
