# Stage 1 — PoCol Open Questions Register

**Document status:** Stage-1 specification-only. This is an explicit register of unresolved
design decisions for **PoCol** with **the idle policy within PoCol** enabled. It records what
is not yet finally decided, why it matters, the candidate options, and — for anything that
would otherwise block Stage 2 — the **minimal default decision adopted now** to unblock Stage 2
while remaining scientifically honest. No entry here constitutes a claim that PoCol is
implemented, validated, secure, fair, or incentive-compatible. At Stage 1 no property is
experimentally supported.

## Stage-2-blocking criterion (binding)

A question is **Stage-2-BLOCKING** if, and only if, its answer changes the *semantics* of any
of: **state transitions**; **energy accounting**; **range validity**; **round termination**;
**security-floor triggering**; **reserve activation**; or **template identity**. Questions that
only affect presentation, tuning of numeric constants that do not change semantics, or
later-stage soundness claims are **not** blocking.

Every blocking question below is given a **minimal default decision** that fixes the semantics
just enough for Stage 2 to proceed. Adopting the default is itself the resolution-for-Stage-2;
deeper study is deferred to the noted later stage. Defaults are chosen to be the most
conservative / least-claiming option consistent with the canonical preamble, `A1`, and
`I1..I16`.

Field order per entry: **question | why it matters | candidate options | scientific risk |
implementation dependency | stage where it must be resolved | Stage-2-blocking?** followed by
the **Stage-2 default** where blocking.

---

### Q1 — Exact guard for `EXHAUSTED_PENDING → LOW_POWER_LISTEN`
- **Why it matters.** Defines when idling is legitimate; wrong semantics violates `I4` and
  creates coverage gaps.
- **Candidate options.** (a) idle only after full-range exhaustion accounting is accepted;
  (b) idle after a partial-coverage threshold; (c) idle on explicit revocation only.
- **Scientific risk.** Premature idling silently reduces active power-time and confounds ΔE
  and floor behaviour.
- **Implementation dependency.** State-machine guard; progress-accounting reconciliation.
- **Stage where resolved.** Stage 2 (state machine); revisited Stage 3 (energy).
- **Stage-2-blocking?** **YES** (state transitions).
- **Stage-2 default.** Adopt (a) **plus** (c): a miner may enter `LOW_POWER_LISTEN` only from
  `EXHAUSTED_PENDING` with accepted full-range exhaustion accounting, or on explicit
  revocation. Exactly the `I4` guard; no partial-coverage idling in the confirmatory design.

### Q2 — `WAKING` deadline overrun disposition (`OFFLINE` vs `DISQUALIFIED`)
- **Why it matters.** Determines the terminal state after a failed wake and whether the
  identity may return; affects reserve accounting and floor recovery.
- **Candidate options.** (a) `OFFLINE` (may re-register); (b) `DISQUALIFIED` (terminal);
  (c) policy-parameterised.
- **Scientific risk.** Over-punishing crash faults distorts availability; under-punishing masks
  delayed-wake attacks.
- **Implementation dependency.** Wake-completion procedure; reserve pool bookkeeping.
- **Stage where resolved.** Stage 2 (semantics); Stage 4 (attack sensitivity).
- **Stage-2-blocking?** **YES** (state transitions; reserve activation).
- **Stage-2 default.** On deadline overrun, transition to `OFFLINE` (non-terminal). Treat
  `DISQUALIFIED` as reserved for detected protocol violations (out-of-range, false exhaustion),
  not for mere wake failure.

### Q3 — Attribution of `E_transition` and `E_coordination`
- **Why it matters.** These two terms of the energy model must be attributed to specific
  miners/events or `I6`/`I7` cannot close exactly.
- **Candidate options.** (a) charge fully to the miner incurring the event; (b) split
  coordination cost across participants; (c) charge coordination to a coordinator budget.
- **Scientific risk.** Mis-attribution breaks exact energy reconciliation and biases ΔE.
- **Implementation dependency.** Energy ledger; per-event accounting.
- **Stage where resolved.** Stage 3 (energy accounting).
- **Stage-2-blocking?** **YES** (energy accounting).
- **Stage-2 default.** Charge `E_transition,i` entirely to the miner incurring the transition,
  and `E_coordination,i` entirely to the miner on whose behalf the coordination event occurs.
  This keeps `E_i` a closed per-miner sum (`I6`) and `E_total = Σ_i E_i` exact (`I7`).

### Q4 — Reconciling partial-state durations to the fixed horizon on departure
- **Why it matters.** A miner that leaves mid-horizon still needs `Σ_states t_state,i = T`;
  the residual after departure must map to a state.
- **Candidate options.** (a) residual counted as `OFFLINE`; (b) residual excluded (miner's
  timeline ends early); (c) residual as `LOW_POWER_LISTEN`.
- **Scientific risk.** Excluding residual breaks `I5` horizon reconciliation and understates or
  overstates energy.
- **Implementation dependency.** Duration reconciliation step.
- **Stage where resolved.** Stage 3.
- **Stage-2-blocking?** **YES** (energy accounting; state transitions).
- **Stage-2 default.** After departure, the remaining horizon is counted as `OFFLINE` at
  `P_offline`, so every miner's durations sum exactly to `T` (`I5`).

### Q5 — Lease-expiry effect on already-committed progress (coverage state vs. custody)
- **Why it matters.** Determines whether a range's `searched` coverage state survives lease
  expiry and reassignment; drives the `I8a` coverage-state partition
  (`searched` / `active_unsearched` / `inactive_unsearched`), the `I8b` custody status of the
  range (`{original, renewed, reassigned, revoked, expired, abandoned}`), and possible re-search.
- **Candidate options.** (a) the `searched` coverage state persists across the custody change;
  (b) reset the range to unsearched on expiry; (c) retain only if renewed by the same miner.
- **Scientific risk.** Discarding valid progress double-charges active power-time; retaining
  unverifiable progress overstates coverage.
- **Implementation dependency.** Assignment ledger; reassignment provenance.
- **Stage where resolved.** Stage 2 (coverage-state accounting; lease/reassignment cases at
  Stage 4).
- **Stage-2-blocking?** **YES** (range validity).
- **Stage-2 default.** Adopt (a) under the `I8a`/`I8b` split: coverage and custody are
  **orthogonal**, so a position's `searched` coverage state (`I8a`) persists when the range's
  custody status becomes `expired` then `reassigned` (`I8b`); the last *accepted* progress
  commitment is retained as `searched` and carried as `prior_progress_commitment` in the
  reassignment record (`I9`). Only the uncommitted remainder is `active_unsearched` /
  `inactive_unsearched`. `reassigned` is a custody status, never an additive coverage term. No
  double credit (`I13`).

### Q6 — Overlap-resolution precedence for assignment conflicts
- **Why it matters.** When two assignments would overlap, the protocol must deterministically
  choose which one is valid to preserve `I1`.
- **Candidate options.** (a) earliest `lease_start` wins; (b) coordinator-designated priority;
  (c) smallest `MinerID` wins.
- **Scientific risk.** A non-deterministic rule makes `I1` unenforceable and results
  irreproducible.
- **Implementation dependency.** Assignment/reassignment overlap guard.
- **Stage where resolved.** Stage 2.
- **Stage-2-blocking?** **YES** (range validity).
- **Stage-2 default.** Earliest `lease_start` wins; ties broken by smallest `MinerID`. Fully
  deterministic and reproducible.

### Q7 — Round termination on full exhaustion without a solution (`refresh` vs `abort`)
- **Why it matters.** Fixes the disposition semantics of `ROUND_EXHAUSTED`.
- **Candidate options.** (a) `TEMPLATE_REFRESH` and continue mining; (b) `ROUND_ABORTED`;
  (c) policy-parameterised.
- **Scientific risk.** An unfixed rule makes round outcomes ambiguous and breaks comparability
  across repetitions.
- **Implementation dependency.** Exhaustion procedure; template-refresh procedure.
- **Stage where resolved.** Stage 2 (round semantics).
- **Stage-2-blocking?** **YES** (round termination; template identity).
- **Stage-2 default.** Default to `TEMPLATE_REFRESH` (new `TemplateID`, difficulty fixed per
  `I12`); the zero-block outcome is still retained (`I14`) with `NA` block-normalised metrics
  (`I15`). `ROUND_ABORTED` is used only for unrecoverable conditions.

### Q8 — Accepted-solution rule for competing valid solutions (network arrival)
- **Why it matters.** Determines which of several valid blocks is accepted, i.e. how the round
  terminates.
- **Candidate options.** (a) network-arrival: accept the earliest valid arrival by a reproducible
  propagation time; (b) a global-oracle deterministic order on `(TemplateID, nonce, MinerID)`;
  (c) coordinator choice.
- **Scientific risk.** A global-oracle ordering asserts a chain-wide fork-choice the model does
  not establish; "first received" without a reproducible arrival time is non-deterministic in
  simulation and irreproducible.
- **Implementation dependency.** Valid-block acceptance procedure; reproducible
  propagation/arrival-time model.
- **Stage where resolved.** Stage 2.
- **Stage-2-blocking?** **YES** (round termination).
- **Stage-2 default.** Adopt (a) **network-arrival semantics**: each valid solution receives a
  reproducible propagation/arrival time; local acceptance takes the **earliest valid arrival**;
  the other valid solutions are recorded as `competing`/`stale`. Only exact arrival-time ties
  break deterministically by smallest `candidate_hash`, then smallest `MinerID`. Deterministic and
  reproducible; satisfies `I2`/`I3`; **no chain-wide fork-choice proof is claimed**. The former
  global-oracle rule ("smallest `(TemplateID, nonce, MinerID)`") is **not** used.

### Q9 — Definition and cadence of the security floors
- **Why it matters.** Fixes when `SECURITY_RECOVERY` triggers; three distinct floors exist
  (active rate, honest rate, `q_adv(t)` threshold).
- **Candidate options.** (a) continuous evaluation; (b) fixed-interval evaluation;
  (c) event-driven (on each state change).
- **Scientific risk.** Coarse cadence can miss transient breaches; ambiguous floor definitions
  make `I16` records inconsistent.
- **Implementation dependency.** Active-hash-rate update; security-floor evaluation.
- **Stage where resolved.** Stage 2 (trigger semantics); Stage 4 (sensitivity).
- **Stage-2-blocking?** **YES** (security-floor triggering).
- **Stage-2 default.** Evaluate all three floors event-driven on every active-hash-rate update
  and every miner state change; a breach of any floor triggers `SECURITY_RECOVERY` and is
  recorded (`I16`). Numeric floor values are configuration inputs, fixed per experiment.

### Q10 — Reserve-promotion selection rule
- **Why it matters.** Determines which `RESERVE` miner is promoted during recovery; affects
  reproducibility and overlap guarding.
- **Candidate options.** (a) deterministic order (smallest `MinerID`); (b) largest declared
  hash rate first; (c) random draw.
- **Scientific risk.** A random rule adds uncontrolled variance to recovery energy and floor
  restoration.
- **Implementation dependency.** Reserve-activation procedure.
- **Stage where resolved.** Stage 2.
- **Stage-2-blocking?** **YES** (reserve activation).
- **Stage-2 default.** Promote reserves in a deterministic order by smallest `MinerID`, always
  subject to the `I10` overlap guard. (Wake *latency* remains a simulation-sampled quantity;
  the *selection* is deterministic.)

### Q11 — Template-identity semantics across refresh
- **Why it matters.** Determines whether refresh always yields a new `TemplateID` and how
  assignments rebind; underpins `I3`.
- **Candidate options.** (a) refresh always mints a new `TemplateID` and rebinds all
  assignments; (b) reuse `TemplateID` if content is byte-identical; (c) version the template.
- **Scientific risk.** Reusing an identifier for changed content admits template disagreement
  and breaks acceptance binding.
- **Implementation dependency.** Template-commitment and template-refresh procedures.
- **Stage where resolved.** Stage 2.
- **Stage-2-blocking?** **YES** (template identity).
- **Stage-2 default.** Every `TEMPLATE_REFRESH` mints a fresh `TemplateID` and rebinds all
  active assignments to it; a committed template is never mutated in place. Satisfies `I3`.

### Q12 — Progress-commitment granularity (interval between commitments)
- **Why it matters.** Sets the resolution of the searched-vs-unsearched measure and thus the
  `I8a` coverage-state accounting (`searched` / `active_unsearched` / `inactive_unsearched`) and
  reassignment carry-over.
- **Candidate options.** (a) fixed nonce-count interval; (b) fixed time interval; (c) adaptive.
- **Scientific risk.** Too coarse a granularity loses coverage detail and can mask false
  exhaustion; adaptive granularity complicates reproducibility.
- **Implementation dependency.** Progress-commitment procedure; range ledger.
- **Stage where resolved.** Stage 2 (accounting resolution).
- **Stage-2-blocking?** **YES** (range validity).
- **Stage-2 default.** Fixed nonce-count interval per range (a configuration constant). The
  searched measure is defined at that granularity; the constant does not change semantics,
  only resolution.

### Q13 — Detection/mitigation of solution withholding
- **Why it matters.** Withholding prolongs honest active power-time and is a fairness/liveness
  concern; currently undetectable at Stage 1.
- **Candidate options.** (a) accept undetectability at Stage 1; (b) add a proof-of-possession
  mechanism; (c) add timing heuristics.
- **Scientific risk.** Claiming detection without a mechanism would be dishonest; heuristics may
  produce false positives.
- **Implementation dependency.** Would require real cryptographic proof-of-possession
  (implementation-level).
- **Stage where resolved.** Deferred — REQUIRES_REAL_IMPLEMENTATION; not settled by simulation.
- **Stage-2-blocking?** **NO** (does not change any of the seven blocking semantics; the round
  simply proceeds as if unsolved). Tracked as `UNRESOLVED` in the threat model.

### Q14 — Reward / incentive semantics (free-riding)
- **Why it matters.** Determines whether rational miners are motivated to contribute real work.
- **Candidate options.** (a) no reward model at Stage 1; (b) coverage-proportional reward;
  (c) solution-only reward.
- **Scientific risk.** Any incentive claim at Stage 1 would be unsupported; a reward model
  interacts with Sybil/free-riding threats not modelled here.
- **Implementation dependency.** Out of the current simulator's scope.
- **Stage where resolved.** Deferred — REQUIRES_FORMAL_PROOF and/or REQUIRES_REAL_IMPLEMENTATION.
- **Stage-2-blocking?** **NO** (no reward term appears in the energy model or the seven blocking
  semantics). Tracked as `UNRESOLVED` in the threat model.

### Q15 — Reporting representation of `NA` block-normalised metrics
- **Why it matters.** Ensures `I15` is applied consistently in outputs.
- **Candidate options.** (a) explicit `NA` token; (b) omit the field; (c) sentinel value.
- **Scientific risk.** A sentinel could be mistaken for a real value; omission loses the
  zero-block signal.
- **Implementation dependency.** Metrics/reporting layer only.
- **Stage where resolved.** Stage 5 (reporting).
- **Stage-2-blocking?** **NO** (presentation only; does not change semantics).

### Q16 — Numeric values of the security-floor thresholds
- **Why it matters.** The specific active-floor, honest-floor, and `q_adv` threshold values
  affect how often recovery triggers.
- **Candidate options.** (a) fixed per-experiment configuration; (b) swept across a range.
- **Scientific risk.** Presenting a single tuned value as canonical could overstate robustness;
  sweeping is more honest but larger.
- **Implementation dependency.** Configuration inputs to floor evaluation.
- **Stage where resolved.** Stage 4 (sensitivity sweep).
- **Stage-2-blocking?** **NO** — the *triggering semantics* are fixed by Q9's default; only the
  numeric constants remain to be studied, and changing a constant does not change semantics.

---

## Final summary line

**No Stage-2-blocking question remains semantically unresolved.** Every question that touches
the seven blocking semantics (state transitions, energy accounting, range validity, round
termination, security-floor triggering, reserve activation, template identity) — Q1–Q12 — has
an adopted **minimal default decision** above that fixes its semantics for Stage 2 while
remaining the most conservative, least-claiming option consistent with the canonical preamble,
the `A1` accounting invariant, and `I1..I16`. The remaining open items (Q13, Q14 `UNRESOLVED`;
Q15, Q16 non-blocking) affect later-stage soundness, incentives, reporting, or numeric tuning
only, and do not block Stage 2. No default above asserts that any security, fairness,
incentive, or energy-reduction property is achieved; each merely fixes semantics so Stage 2 can
proceed honestly.
