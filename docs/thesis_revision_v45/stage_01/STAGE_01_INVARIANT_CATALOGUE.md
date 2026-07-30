# Stage 1 — PoCol Invariant Catalogue (I1..I16)

**Document status:** Stage-1 specification-only. This catalogue DEFINES the numbered
invariants `I1..I16` of **PoCol** with **the idle policy within PoCol** enabled. Defining an
invariant is a specification act. It is NOT a claim that the invariant is implemented,
enforced in code, validated, or that any security, fairness, or incentive property follows
from it. At Stage 1 no invariant is experimentally supported.

The accounting invariant **A1** — continuous full-participation energy over the fixed
10,000 s horizon is fixed at **8.420833333 kWh** (141 TH/s, 21.5 J/TH, 3031.5 W), invariant
to nonce-domain partitioning — is stated in `STAGE_01_PROTOCOL_SCOPE.md` and is the
accounting backdrop for I5–I7 and I13. Energy reductions arise ONLY from reduced active
power-time, never from partitioning.

## Conventions used in this catalogue

- **Miner states (8):** `REGISTERED`, `RESERVE`, `ACTIVE_HASHING`, `EXHAUSTED_PENDING`,
  `LOW_POWER_LISTEN`, `WAKING`, `OFFLINE`, `DISQUALIFIED`.
- **Round states (10):** `ROUND_INITIALISING`, `TEMPLATE_COMMITMENT`, `ASSIGNMENT`,
  `HASHING`, `SECURITY_RECOVERY`, `SOLUTION_PROPAGATION`, `ROUND_ACCEPTED`,
  `ROUND_EXHAUSTED`, `TEMPLATE_REFRESH`, `ROUND_ABORTED`.
- **Energy model (per miner):** state-complete, one residency power per state, no residual
  bucket —
  `E_i = Σ_{s∈States} (P_{i,s} · t_{i,s}) + E_transition,i + E_coordination,i + E_verification,i`,
  summed over the eight miner states, with `Σ_{s} t_{i,s} = T`. `E_verification,i` is a separate
  event-energy term (verification of early-stop certificates), added on top of the residency
  energies and not folded into `P_hash·t_hash`.
- **Adversarial share:** `q_adv(t) = H_adversarial(t) / (H_honest(t) + H_adversarial(t))`.
- **Progress evidence** is a **modeled progress-verification abstraction**, never a
  cryptographic proof of range exhaustion.
- **Planned test stages** (approved stage map) referenced below:
  - **Stage 2** — core miner states and complete energy accounting.
  - **Stage 3** — time-varying hash rate, security floor, reserve activation.
  - **Stage 4** — range leases, reassignment, and modeled progress verification.
  - **Stage 5** — adversarial and incentive model.
  - **Stage 7 / Stage 8** — scientific freeze and execution / statistical analysis (referenced by
    the results-integrity invariants).

Each entry lists the exact statement, a formal statement, scope, required inputs, enforcement
point, planned test stage, and consequence of violation.

---

### I1 — No two simultaneously valid active assignments overlap.

- **Formal statement.** For all miners `a ≠ b` and all times `t`: if assignments `A_a` and
  `A_b` are both VALID and ACTIVE at `t` under the same committed `(RoundID, TemplateID)`,
  then `range(A_a) ∩ range(A_b) = ∅`.
- **Scope.** Range assignment across `ASSIGNMENT` and `HASHING`; per round, per `TemplateID`.
- **Required inputs.** Assignment set with nonce ranges; validity intervals
  `(lease_start, lease_expiry)`; miner state; `(RoundID, TemplateID)`.
- **Enforcement point.** Range-assignment and range-reassignment procedures (overlap guard
  evaluated before an assignment becomes active).
- **Planned test stage.** Stage 2 (with Stage 4 lease / reassignment cases).
- **Consequence of violation.** Duplicate coverage of a nonce region; ambiguous assignment
  provenance; unsound acceptance provenance (couples to I2); double-counting risk (couples to
  I13).

### I2 — Every accepted solution belongs to the signer's valid current assignment.

- **Formal statement.** If solution `s` is accepted, then `nonce(s) ∈ range(A)` for some
  assignment `A` that is VALID and CURRENT for `signer(s)` at acceptance time under the
  committed `(RoundID, TemplateID)`.
- **Scope.** Valid block acceptance; solution submission.
- **Required inputs.** Solution nonce; signer identity; current assignment set;
  `(RoundID, TemplateID)`.
- **Enforcement point.** Acceptance predicate (range-membership check) in the valid-block
  acceptance procedure.
- **Planned test stage.** Stage 2 (structural), with Stage 4 (acceptance under leases) and
  Stage 5 (adversarial out-of-range tests).
- **Consequence of violation.** Out-of-range acceptance; enables the mining-outside-range
  attack; coverage accounting becomes unsound.

### I3 — Every accepted solution matches the current RoundID and TemplateID.

- **Formal statement.** `accepted(s) ⇒ RoundID(s) = RoundID_current ∧ TemplateID(s) =
  TemplateID_committed`.
- **Scope.** Acceptance; binding to the committed template.
- **Required inputs.** Solution's `RoundID`/`TemplateID` fields; committed values.
- **Enforcement point.** Acceptance predicate and template-commitment check.
- **Planned test stage.** Stage 2, with Stage 4 (refresh / acceptance) and Stage 5 (adversarial
  template tests).
- **Consequence of violation.** Cross-round or stale-template acceptance; replay of prior
  work; template disagreement admitted into the chain.

### I4 — No miner enters LOW_POWER_LISTEN before valid exhaustion or explicit revocation.

- **Formal statement.** A transition `X → LOW_POWER_LISTEN` is permitted only if the miner
  has reached `EXHAUSTED_PENDING` with accepted exhaustion accounting for its assigned range,
  OR its assignment has been explicitly revoked.
- **Scope.** Idle-policy state transitions; transition to low-power listening.
- **Required inputs.** Miner state; exhaustion/progress accounting; revocation records.
- **Enforcement point.** Guard in the transition-to-low-power-listening procedure.
- **Planned test stage.** Stage 2 (state machine and complete energy accounting), with Stage 4
  (exhaustion / reassignment cases).
- **Consequence of violation.** Premature idling; coverage gap over an unsearched range;
  unaccounted reduction of active power-time; heightened floor-breach risk.

### I5 — State durations are non-negative and reconcile exactly with the observation horizon.

- **Formal statement.** For each miner `i`, every `t_state,i ≥ 0` and
  `Σ_states t_state,i = T` with `T = 10,000 s`, summed over the **eight** miner states; the
  per-miner state timeline has no gaps and no overlaps, and there is **no** residual / `t_other`
  bucket.
- **Scope.** Energy accounting; all eight miner states.
- **Required inputs.** Per-miner state timeline (eight states); fixed horizon `T`.
- **Enforcement point.** State-duration reconciliation step (post-round accounting).
- **Planned test stage.** Stage 2 (complete energy accounting) with Stage 3 (wake / time-varying
  energy).
- **Consequence of violation.** Energy miscount; A1, I6, and I7 broken; results not auditable.

### I6 — Per-miner state energy components sum exactly to per-miner energy.

- **Formal statement.**
  `E_i = Σ_{s∈States} (P_{i,s} · t_{i,s}) + E_transition,i + E_coordination,i + E_verification,i`
  holds with exact equality, summed over the **eight** miner states, with **no** residual term.
  `E_verification,i` is a separate event-energy increment (early-stop certificate verification),
  added on top of the residency energies and not double-counted into `P_hash·t_hash`.
- **Scope.** Per-miner energy accounting.
- **Required inputs.** Per-state residency powers; per-state durations (eight states);
  `E_transition,i`; `E_coordination,i`; `E_verification,i`.
- **Enforcement point.** Per-miner energy aggregation.
- **Planned test stage.** Stage 2 (complete energy accounting) with Stage 3 (wake energy).
- **Consequence of violation.** Incorrect per-miner energy; unreliable ΔE.

### I7 — Per-miner energies sum exactly to network energy.

- **Formal statement.** `E_total = Σ_i E_i` (exact), each `E_i` being the state-complete
  per-miner sum of I6.
- **Scope.** Network-level energy accounting.
- **Required inputs.** All per-miner energies `E_i`.
- **Enforcement point.** Network energy aggregation.
- **Planned test stage.** Stage 2 (complete energy accounting).
- **Consequence of violation.** Incorrect network energy and ΔE; the A1 comparison
  (`ΔE = E_continuous_control − E_idle_policy`) becomes invalid.

### I8a — Coverage-state partition of the assigned domain.

- **Formal statement.** For every assignment, and in aggregate over a round's assigned domain,
  `searched + active_unsearched + inactive_unsearched = assigned_domain`, and the three coverage
  categories are **pairwise disjoint** and **collectively exhaustive** over `assigned_domain`.
- **Scope.** Coverage-state accounting, per assignment and per round.
- **Required inputs.** Per-range progress frontiers; live-lease (active vs. inactive) status;
  `assigned_domain`.
- **Enforcement point.** Coverage-state reconciliation (per round and at exhaustion).
- **Planned test stage.** Stage 2 (assignment cover) with Stage 4 (lease / progress coverage
  states).
- **Consequence of violation.** Coverage over- or under-count; false exhaustion undetected;
  double-counting risk (couples to I13).

### I8b — Custody / provenance model (orthogonal to coverage).

- **Formal statement.** Each assignment carries a custody / lineage status in
  `{original, renewed, reassigned, revoked, expired, abandoned}`. These are custody / provenance
  properties and **MUST NOT** appear as additive terms in the coverage-state equation of I8a. A
  `reassigned` position still has an **independent coverage state**
  (`searched` / `active_unsearched` / `inactive_unsearched`); custody and coverage are two
  orthogonal models of the same position.
- **Scope.** Custody / lineage of assignments across renewal and reassignment.
- **Required inputs.** Assignment / lease records; reassignment provenance; lineage links
  (`previous_assignment_reference`, `assignment_version`).
- **Enforcement point.** Custody / lineage tracking in the range-lease and reassignment
  procedures.
- **Planned test stage.** Stage 4 (range leases and reassignment).
- **Consequence of violation.** Unauditable custody; conflation of custody status with a coverage
  term (the removed `reassigned`-as-coverage error); broken provenance.

### I9 — Every reassignment has complete provenance.

- **Formal statement.** Each reassignment event `r` carries a complete record
  `(range, from_miner, to_miner, reason, timestamp, prior_progress_commitment)` with
  `reason ∈ {lease_expiry, exhaustion, departure, conflict, recovery}`.
- **Scope.** Range reassignment.
- **Required inputs.** Reassignment events with all required fields.
- **Enforcement point.** Logging inside the range-reassignment procedure.
- **Planned test stage.** Stage 4 (range leases and reassignment).
- **Consequence of violation.** Unauditable coverage; provenance gaps; I8a/I8b (coverage /
  custody) reconciliation becomes impossible.

### I10 — Reserve activation does not create overlap.

- **Formal statement.** Promoting a `RESERVE` miner to `ACTIVE_HASHING` assigns only ranges
  disjoint from every currently valid active assignment, thereby preserving I1.
- **Scope.** Reserve activation.
- **Required inputs.** Reserve-promotion request; current valid active-assignment set.
- **Enforcement point.** Overlap guard in the reserve-activation procedure (shares the I1
  predicate).
- **Planned test stage.** Stage 3 (reserve activation) with Stage 5 (adversarial reserve cases).
- **Consequence of violation.** Overlap introduced during recovery; duplicate coverage; I1
  and I13 violated exactly when the protocol is under floor stress.

### I11 — A false early-stop message cannot terminate hashing without target verification.

- **Formal statement.** Termination of hashing via an early-stop certificate requires the
  certificate to pass verification against target verification and retained progress
  evidence; an unverified or false certificate MUST NOT cause termination.
- **Scope.** Early-stop certificate generation and verification; security recovery.
- **Required inputs.** Early-stop certificate; round target; retained progress commitments.
- **Enforcement point.** Guard in the early-stop-verification procedure, evaluated before any
  transition out of `HASHING` toward stopping.
- **Planned test stage.** Stage 4 (early-stop certificate verification) with Stage 5 (adversarial
  false-certificate / halting tests).
- **Consequence of violation.** Forced premature stop (a halting attack); coverage abandoned;
  direct security degradation.

### I12 — Difficulty remains constant in the confirmatory protocol.

- **Formal statement.** In the confirmatory design the target/difficulty `D` is fixed for the
  experiment horizon: `D(t) = D_0` for all `t`.
- **Scope.** The entire confirmatory protocol.
- **Required inputs.** Difficulty parameter; round configuration.
- **Enforcement point.** Set at round initialisation and template commitment; held constant
  thereafter.
- **Planned test stage.** Stage 2 (configuration invariant), rechecked through the Stage 7 freeze
  and execution and every later stage.
- **Consequence of violation.** Difficulty variation confounds the energy and security
  comparison; A1 and ΔE are no longer comparable across rounds.

### I13 — Shared physical executions cannot be counted twice.

- **Formal statement.** Every physical hashing execution maps to at most one credited
  `(miner, range, nonce)` coverage record; shared or duplicated executions are de-duplicated
  so that neither coverage nor energy is credited twice.
- **Scope.** Coverage accounting and energy accounting (couples to I1, I8a, I10).
- **Required inputs.** Execution-to-assignment mapping; de-duplication keys.
- **Enforcement point.** De-duplication step in coverage/energy accounting.
- **Planned test stage.** Stage 2 (coverage and complete energy accounting), with execution-level
  de-duplication rechecked at Stage 7.
- **Consequence of violation.** Inflated coverage or energy; ΔE and the A1 comparison
  corrupted.

### I14 — Zero-block outcomes remain retained.

- **Formal statement.** Rounds or experiment repetitions that yield zero accepted blocks are
  retained in the dataset; a zero-block result is a valid recorded outcome and is never
  dropped.
- **Scope.** Results recording; dataset integrity.
- **Required inputs.** Round outcome records.
- **Enforcement point.** Results-recording / dataset-assembly step.
- **Planned test stage.** Stage 8 (statistical analysis; dataset retention enforced from the
  Stage 7 execution).
- **Consequence of violation.** Survivorship bias; skewed energy and rate statistics.

### I15 — Undefined block-normalised metrics remain NA.

- **Formal statement.** Any per-block-normalised metric whose denominator (block count) is
  zero is recorded as `NA`; it is never recorded as `0` and never imputed.
- **Scope.** Metrics computation and reporting.
- **Required inputs.** Block counts; metric numerators.
- **Enforcement point.** Metrics-computation step.
- **Planned test stage.** Stage 8 (statistical analysis).
- **Consequence of violation.** Fabricated or biased normalised metrics; misleading
  energy-per-block figures.

### I16 — Security-floor breaches are recorded, not silently repaired in the reported data.

- **Formal statement.** Any breach of the active hash-rate floor, the honest hash-rate floor,
  or the `q_adv(t)` threshold is recorded as an event in the reported data; recovery actions
  are logged separately and never overwrite or erase the breach record.
- **Scope.** Security-floor evaluation; reporting.
- **Required inputs.** Floor/threshold evaluations; breach events; recovery logs.
- **Enforcement point.** Security-floor-evaluation step plus the results-recording step
  (pairs with the `SECURITY_RECOVERY` responses in the failure table).
- **Planned test stage.** Stage 3 (security-floor breach behaviour) with Stage 5 (adversarial) and
  Stage 8 (reporting-integrity) checks.
- **Consequence of violation.** Hidden security degradation; overstated safety; dishonest
  reporting of the reduced-participation regime.

---

## Cross-reference summary

| ID | one-line statement | primary test stage | primary enforcement point |
|---|---|---|---|
| I1 | No overlap among valid active assignments | Stage 2 (+4) | assignment / reassignment overlap guard |
| I2 | Accepted solution lies in signer's valid assignment | Stage 2 (+4/5) | acceptance predicate |
| I3 | Accepted solution matches current RoundID/TemplateID | Stage 2 (+4/5) | acceptance + commitment check |
| I4 | No early LOW_POWER_LISTEN without exhaustion/revocation | Stage 2 (+4) | listen-transition guard |
| I5 | Non-negative durations reconcile to horizon T | Stage 2 (+3) | duration reconciliation |
| I6 | State energies sum to per-miner energy | Stage 2 (+3) | per-miner aggregation |
| I7 | Per-miner energies sum to network energy | Stage 2 | network aggregation |
| I8a | Coverage states partition the assigned domain exactly | Stage 2 (+4) | coverage-state reconciliation |
| I8b | Custody / provenance model (orthogonal to coverage) | Stage 4 | custody / lineage tracking |
| I9 | Reassignments carry complete provenance | Stage 4 | reassignment logging |
| I10 | Reserve activation adds no overlap | Stage 3 (+5) | reserve-activation guard |
| I11 | No termination without target verification | Stage 4 (+5) | early-stop verification guard |
| I12 | Difficulty fixed in confirmatory design | Stage 2 (all) | round init / commitment |
| I13 | No double-counting of shared executions | Stage 2 (+7) | accounting de-duplication |
| I14 | Zero-block outcomes retained | Stage 8 (+7) | results recording |
| I15 | Undefined block-normalised metrics are NA | Stage 8 | metrics computation |
| I16 | Floor breaches recorded, never silently repaired | Stage 3 (+5/8) | floor eval + recording |

No invariant above is asserted to hold in any implementation at Stage 1; each is a
specification target with a planned verification stage.
