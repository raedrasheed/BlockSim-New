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
- **Energy model (per miner):**
  `E_i = P_hash,i·t_hash,i + P_listen,i·t_listen,i + P_wake,i·t_wake,i + P_offline,i·t_offline,i + E_transition,i + E_coordination,i`.
- **Adversarial share:** `q_adv(t) = H_adversarial(t) / (H_honest(t) + H_adversarial(t))`.
- **Progress evidence** is a **modeled progress-verification abstraction**, never a
  cryptographic proof of range exhaustion.
- **Planned test stages** referenced below:
  - **Stage 2** — structural / state-machine / assignment-accounting simulation.
  - **Stage 3** — energy-accounting simulation.
  - **Stage 4** — adversarial / security simulation.
  - **Stage 5** — analysis, statistics, and reporting-integrity checks.

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
- **Planned test stage.** Stage 2.
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
- **Planned test stage.** Stage 2 (structural) with Stage 4 adversarial out-of-range tests.
- **Consequence of violation.** Out-of-range acceptance; enables the mining-outside-range
  attack; coverage accounting becomes unsound.

### I3 — Every accepted solution matches the current RoundID and TemplateID.

- **Formal statement.** `accepted(s) ⇒ RoundID(s) = RoundID_current ∧ TemplateID(s) =
  TemplateID_committed`.
- **Scope.** Acceptance; binding to the committed template.
- **Required inputs.** Solution's `RoundID`/`TemplateID` fields; committed values.
- **Enforcement point.** Acceptance predicate and template-commitment check.
- **Planned test stage.** Stage 2.
- **Consequence of violation.** Cross-round or stale-template acceptance; replay of prior
  work; template disagreement admitted into the chain.

### I4 — No miner enters LOW_POWER_LISTEN before valid exhaustion or explicit revocation.

- **Formal statement.** A transition `X → LOW_POWER_LISTEN` is permitted only if the miner
  has reached `EXHAUSTED_PENDING` with accepted exhaustion accounting for its assigned range,
  OR its assignment has been explicitly revoked.
- **Scope.** Idle-policy state transitions; transition to low-power listening.
- **Required inputs.** Miner state; exhaustion/progress accounting; revocation records.
- **Enforcement point.** Guard in the transition-to-low-power-listening procedure.
- **Planned test stage.** Stage 2 (state machine) with Stage 3 (energy consequences).
- **Consequence of violation.** Premature idling; coverage gap over an unsearched range;
  unaccounted reduction of active power-time; heightened floor-breach risk.

### I5 — State durations are non-negative and reconcile exactly with the observation horizon.

- **Formal statement.** For each miner `i`, every `t_state,i ≥ 0` and
  `Σ_states t_state,i = T` with `T = 10,000 s`; the per-miner state timeline has no gaps and
  no overlaps.
- **Scope.** Energy accounting; all miner states.
- **Required inputs.** Per-miner state timeline; fixed horizon `T`.
- **Enforcement point.** State-duration reconciliation step (post-round accounting).
- **Planned test stage.** Stage 3.
- **Consequence of violation.** Energy miscount; A1, I6, and I7 broken; results not auditable.

### I6 — Per-miner state energy components sum exactly to per-miner energy.

- **Formal statement.**
  `E_i = P_hash,i·t_hash,i + P_listen,i·t_listen,i + P_wake,i·t_wake,i + P_offline,i·t_offline,i + E_transition,i + E_coordination,i`
  holds with exact equality (no residual term).
- **Scope.** Per-miner energy accounting.
- **Required inputs.** Per-state powers; per-state durations; `E_transition,i`;
  `E_coordination,i`.
- **Enforcement point.** Per-miner energy aggregation.
- **Planned test stage.** Stage 3.
- **Consequence of violation.** Incorrect per-miner energy; unreliable ΔE.

### I7 — Per-miner energies sum exactly to network energy.

- **Formal statement.** `E_total = Σ_i E_i` (exact).
- **Scope.** Network-level energy accounting.
- **Required inputs.** All per-miner energies `E_i`.
- **Enforcement point.** Network energy aggregation.
- **Planned test stage.** Stage 3.
- **Consequence of violation.** Incorrect network energy and ΔE; the A1 comparison
  (`ΔE = E_continuous_control − E_idle_policy`) becomes invalid.

### I8 — Assignment accounting reconciles searched, unsearched, inactive, and reassigned portions.

- **Formal statement.** For the nonce domain of each round, the four measures
  `searched`, `unsearched`, `inactive`, and `reassigned` partition the domain exactly: their
  union is the whole domain and they are pairwise disjoint (measure-exact, no overlap, no
  omission).
- **Scope.** Range assignment, exhaustion, reassignment.
- **Required inputs.** Per-range progress commitments; assignment/lease records; reassignment
  provenance.
- **Enforcement point.** Range-accounting reconciliation (per round and at exhaustion).
- **Planned test stage.** Stage 2.
- **Consequence of violation.** Coverage over- or under-count; false exhaustion undetected;
  double-counting risk (couples to I13).

### I9 — Every reassignment has complete provenance.

- **Formal statement.** Each reassignment event `r` carries a complete record
  `(range, from_miner, to_miner, reason, timestamp, prior_progress_commitment)` with
  `reason ∈ {lease_expiry, exhaustion, departure, conflict, recovery}`.
- **Scope.** Range reassignment.
- **Required inputs.** Reassignment events with all required fields.
- **Enforcement point.** Logging inside the range-reassignment procedure.
- **Planned test stage.** Stage 2.
- **Consequence of violation.** Unauditable coverage; provenance gaps; I8 reconciliation
  becomes impossible.

### I10 — Reserve activation does not create overlap.

- **Formal statement.** Promoting a `RESERVE` miner to `ACTIVE_HASHING` assigns only ranges
  disjoint from every currently valid active assignment, thereby preserving I1.
- **Scope.** Reserve activation.
- **Required inputs.** Reserve-promotion request; current valid active-assignment set.
- **Enforcement point.** Overlap guard in the reserve-activation procedure (shares the I1
  predicate).
- **Planned test stage.** Stage 2.
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
- **Planned test stage.** Stage 4.
- **Consequence of violation.** Forced premature stop (a halting attack); coverage abandoned;
  direct security degradation.

### I12 — Difficulty remains constant in the confirmatory protocol.

- **Formal statement.** In the confirmatory design the target/difficulty `D` is fixed for the
  experiment horizon: `D(t) = D_0` for all `t`.
- **Scope.** The entire confirmatory protocol.
- **Required inputs.** Difficulty parameter; round configuration.
- **Enforcement point.** Set at round initialisation and template commitment; held constant
  thereafter.
- **Planned test stage.** Stage 2 (configuration invariant), rechecked in every later stage.
- **Consequence of violation.** Difficulty variation confounds the energy and security
  comparison; A1 and ΔE are no longer comparable across rounds.

### I13 — Shared physical executions cannot be counted twice.

- **Formal statement.** Every physical hashing execution maps to at most one credited
  `(miner, range, nonce)` coverage record; shared or duplicated executions are de-duplicated
  so that neither coverage nor energy is credited twice.
- **Scope.** Coverage accounting and energy accounting (couples to I1, I8, I10).
- **Required inputs.** Execution-to-assignment mapping; de-duplication keys.
- **Enforcement point.** De-duplication step in coverage/energy accounting.
- **Planned test stage.** Stage 3 (energy) with Stage 2 (coverage).
- **Consequence of violation.** Inflated coverage or energy; ΔE and the A1 comparison
  corrupted.

### I14 — Zero-block outcomes remain retained.

- **Formal statement.** Rounds or experiment repetitions that yield zero accepted blocks are
  retained in the dataset; a zero-block result is a valid recorded outcome and is never
  dropped.
- **Scope.** Results recording; dataset integrity.
- **Required inputs.** Round outcome records.
- **Enforcement point.** Results-recording / dataset-assembly step.
- **Planned test stage.** Stage 5 (with Stage 3 accounting).
- **Consequence of violation.** Survivorship bias; skewed energy and rate statistics.

### I15 — Undefined block-normalised metrics remain NA.

- **Formal statement.** Any per-block-normalised metric whose denominator (block count) is
  zero is recorded as `NA`; it is never recorded as `0` and never imputed.
- **Scope.** Metrics computation and reporting.
- **Required inputs.** Block counts; metric numerators.
- **Enforcement point.** Metrics-computation step.
- **Planned test stage.** Stage 5.
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
- **Planned test stage.** Stage 4 (breach behaviour) with Stage 5 (reporting integrity).
- **Consequence of violation.** Hidden security degradation; overstated safety; dishonest
  reporting of the reduced-participation regime.

---

## Cross-reference summary

| ID | one-line statement | primary test stage | primary enforcement point |
|---|---|---|---|
| I1 | No overlap among valid active assignments | Stage 2 | assignment / reassignment overlap guard |
| I2 | Accepted solution lies in signer's valid assignment | Stage 2 (+4) | acceptance predicate |
| I3 | Accepted solution matches current RoundID/TemplateID | Stage 2 | acceptance + commitment check |
| I4 | No early LOW_POWER_LISTEN without exhaustion/revocation | Stage 2 (+3) | listen-transition guard |
| I5 | Non-negative durations reconcile to horizon T | Stage 3 | duration reconciliation |
| I6 | State energies sum to per-miner energy | Stage 3 | per-miner aggregation |
| I7 | Per-miner energies sum to network energy | Stage 3 | network aggregation |
| I8 | Range accounting partitions the domain exactly | Stage 2 | range reconciliation |
| I9 | Reassignments carry complete provenance | Stage 2 | reassignment logging |
| I10 | Reserve activation adds no overlap | Stage 2 | reserve-activation guard |
| I11 | No termination without target verification | Stage 4 | early-stop verification guard |
| I12 | Difficulty fixed in confirmatory design | Stage 2 (all) | round init / commitment |
| I13 | No double-counting of shared executions | Stage 3 (+2) | accounting de-duplication |
| I14 | Zero-block outcomes retained | Stage 5 (+3) | results recording |
| I15 | Undefined block-normalised metrics are NA | Stage 5 | metrics computation |
| I16 | Floor breaches recorded, never silently repaired | Stage 4 (+5) | floor eval + recording |

No invariant above is asserted to hold in any implementation at Stage 1; each is a
specification target with a planned verification stage.
