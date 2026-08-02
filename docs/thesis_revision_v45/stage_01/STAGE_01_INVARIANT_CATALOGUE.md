# Stage 1 — PoCol Invariant Catalogue (I1..I19)

**Document status:** Stage-1 specification-only. This catalogue DEFINES the numbered
invariants `I1..I19` of **PoCol** with **the idle policy within PoCol** enabled (I18 added in
Stage 1F for immutable assignment versioning; in Stage 1G, I2 is corrected to discovery-time
eligibility (G1) and I18 is split into the consistent pair I18a/I18b (G2); in Stage 1H, I19 is
added for single-owner, no-double-count state-residency accounting (H7)). Defining an
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

### I2 — Every accepted solution binds to the assignment version that was eligible at DISCOVERY time (corrected, G1).

- **Formal statement (discovery-time eligibility, G1).** If solution `s` is accepted, then `s`
  binds to an IMMUTABLE assignment version `A` such that: (i) `A` was VALID and `CURRENT` for
  `signer(s)` at the solution's `discovery_time`; (ii) `A` was NOT revoked before `discovery_time`;
  (iii) `A` belonged to `signer(s)` at `discovery_time`; (iv) `nonce(s) ∈ range(A)`; (v) `A` is
  bound to the candidate's `(RoundID, TemplateID)`; and (vi) `A` remains resolvable from the
  `SolutionEligibilitySnapshot`. **`A` need NOT remain `CURRENT` at certificate or block arrival —
  it may later be `PAUSED` or `SUPERSEDED`.** Acceptance-time `CURRENT` semantics are NOT used.
- **Scope.** Valid block acceptance; solution submission; discovery-snapshot resolution.
- **Required inputs.** Solution nonce; signer identity; the immutable version resolved from the
  discovery snapshot `(AssignmentID, assignment_version)`; `discovery_time`; `(RoundID, TemplateID)`.
- **Enforcement point.** `ValidateCandidate` (the canonical discovery-snapshot predicate) invoked by
  `AcceptanceBatchFinalize`, `EarlyStopVerify`, and `SelfValidateFoundSolution`.
- **Planned test stage.** Stage 2 (structural), with Stage 4 (acceptance under leases/renewal) and
  Stage 5 (adversarial out-of-range / stale-version tests).
- **Consequence of violation.** Either a genuinely-discovered solution is wrongly rejected because
  its assignment later paused/superseded (the Stage-1F defect), or an out-of-range/never-eligible
  solution is accepted; coverage accounting becomes unsound.

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

### I4 — Entry to LOW_POWER_LISTEN requires one of four legal triggers, each recording a stop_reason.

- **Formal statement.** A miner may enter `LOW_POWER_LISTEN` only after **one** of: (1) accepted
  range-exhaustion accounting via `EXHAUSTED_PENDING`; (2) explicit assignment revocation; (3) a
  fully verified valid-solution early-stop certificate; or (4) round closure. Each such transition
  records exactly one `stop_reason ∈ {RANGE_EXHAUSTED, ASSIGNMENT_REVOKED,
  VALID_SOLUTION_VERIFIED, ROUND_ACCEPTED, ROUND_ABORTED}`. **No unverified certificate may cause
  the transition.** `EXHAUSTED_PENDING` is **exclusive** to the range-exhaustion path.
- **Scope.** Idle-policy state transitions; transition to low-power listening.
- **Required inputs.** Miner state; exhaustion/progress accounting; revocation records; a fully
  verified early-stop certificate; round-closure disposition; the recorded `stop_reason`.
- **Enforcement point.** Guard in the transition-to-low-power-listening procedure (and the direct
  ACTIVE_HASHING → LOW_POWER_LISTEN transition on the verified-solution path).
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
  `accepted_searched + active_unsearched + inactive_unsearched = assigned_domain`, and the three
  coverage categories are **pairwise disjoint** and **collectively exhaustive** over
  `assigned_domain`. The normative I8a measure uses **accepted** coverage only. Reported coverage
  is promoted to `accepted_searched` only by adjudication (a `RangeExhaust` honest-completion or a
  passed audit); a progress commitment (`ProgressCommit`) never updates the normative I8a measure.
- **Scope.** Accepted-coverage-state accounting, per assignment and per round.
- **Required inputs.** Per-range accepted-coverage frontiers (`accepted_frontier`); adjudication
  outcomes (honest-completion or audit); live-lease (active vs. inactive) status;
  `assigned_domain`.
- **Enforcement point.** Coverage-state reconciliation (per round and at exhaustion).
- **Planned test stage.** Stage 2 (assignment cover) with Stage 4 (lease / progress coverage
  states).
- **Consequence of violation.** Coverage over- or under-count; false exhaustion undetected;
  double-counting risk (couples to I13).

### I8b — Custody / provenance model (orthogonal to coverage).

- **Formal statement.** Each assignment carries a custody / lineage status from the CANONICAL,
  CLOSED enum `{original, renewed, reassigned, revoked, expired, abandoned, completed,
  superseded_by_template_refresh}` (I-07). No procedure may set `custody_status` to a value outside
  this enum — in particular an adversarial withdrawal sets `custody_status = revoked` and records the
  cause in the SEPARATE `revocation_reason` field (e.g. `adversarial_withdrawal`), never an invented
  value such as `revoked_adversarial_exit`. These are custody / provenance properties and **MUST NOT**
  appear as additive terms in the coverage-state equation of I8a. A `reassigned` position still has an
  **independent coverage state** (`searched` / `active_unsearched` / `inactive_unsearched`); custody
  and coverage are two orthogonal models of the same position. A fully exhausted range has
  `coverage_state = searched` together with `custody_status = completed`, and is **NOT** reassignable
  under the same `TemplateID`.
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
  `reason ∈ {lease_expiry, abandonment, revocation, departure, conflict, security_recovery}`.
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

### I11 — An early-stop certificate cannot terminate hashing unless it passes full certificate validation.

- **Formal statement.** A miner may stop hashing because of an early-stop certificate **only
  after** validating: the current `RoundID`, the current `TemplateID`, the current `AssignmentID`,
  the `MinerID`, `nonce` membership in the identified assignment's range, the recomputed
  `candidate_hash`, `target` satisfaction under fixed `D`, and authentication/signature. A failed
  or partially verified certificate causes **no** hashing-state transition.
- **Scope.** Early-stop certificate validation only. I11 has **no** dependency on progress
  commitments, coverage frontiers, range exhaustion, searched-domain coverage, or any proof of no
  solution. Range exhaustion is governed by **I4, I8a, and the actual-vs-reported progress model**,
  not by I11.
- **Required inputs.** Early-stop certificate; current `RoundID` / `TemplateID` / `AssignmentID`;
  `MinerID`; the nonce range of the identified assignment; the recomputed `candidate_hash`; the
  round target; authentication material.
- **Enforcement point.** Guard in the early-stop-verification procedure, evaluated before any
  transition out of `ACTIVE_HASHING` toward stopping.
- **Planned test stage.** Stage 4 (early-stop certificate verification) with Stage 5 (adversarial
  false-certificate / halting tests).
- **Consequence of violation.** Forced premature stop (a halting attack) on a false or partial
  certificate; direct security degradation.

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
  (pairs with the `SECURITY_RECOVERY` responses in the failure table). **T4 (no fabricated
  UNRECOVERABLE):** an IRREVERSIBLE branch-C install failure that occurs AFTER the
  `SECURITY_RECOVERY → ASSIGNMENT` transition is recorded as its own disposition
  `recovery_episode_disposition = RECOVERY_INSTALL_FAILED_ABORTED` with decision status
  `APPLY_FAILED_TERMINAL` and closes the round via the declared recovery-finalising `RoundAbort`; it is
  NEVER relabelled as an `UNRECOVERABLE` floor outcome (which is reserved for a FINAL census that still
  breaches the floor after the deadline, O3/R14) and NEVER sets `recovery_outcome_finalised`. **T6:** a
  RESTORED outcome that depends on PENDING/WAKING reserves is NOT applied while those reserves are
  inactive — a syntactically valid PENDING assignment set is not treated as restored hash rate, so the
  reduced-participation regime is never reported as recovered before the reserve is `ACTIVE_HASHING`.
  **T3 (install-phase integrity):** the redistribution-only install is a synchronous sub-computation with
  no event boundary within it, so no epilogue ever observes — or records a floor decision from — a
  transient `ASSIGNMENT`-with-active-episode state; every install exit ends in exactly one of `HASHING`
  + `APPLIED`, `SECURITY_RECOVERY` + `APPLY_FAILED` (rolled back), or `ROUND_ABORTED` +
  `RECOVERY_INSTALL_FAILED_ABORTED`. **U1 (recovery work is not an outcome; supersedes the T6 framing):** the
  RESTORED / UNRECOVERABLE outcome is decided ONLY from a final census (`outcome_consistent_with_census`
  is NOT weakened — a breached census can never justify RESTORED). Reserve activation / redistribution
  attempted while the floor is still breached is a recovery-WORK action (`RecoveryWorkDueEvent` +
  `ApplyRecoveryWorkAfterEpilogue`), NEVER a `RecoveryOutcome` and NEVER marked `APPLIED` as `RESTORED`;
  the round stays `SECURITY_RECOVERY` and a LATER no-breach final census mints `RESTORED`. So a
  still-breached census is never reported as a repaired/RESTORED floor, and the impossible reserve-dependent
  `RESTORED` continuation is removed. **V6 (security-floor recovery work must change the census):** only an
  action that can ACTUALLY change the `ACTIVE_HASHING` census — `H_active`/`H_honest`/`q_adv` (reserve
  activation, or a declared honest/adversarial participation replacement) — is `SECURITY_FLOOR_RECOVERY_WORK`
  and controls the breach-before-deadline logic. A range redistribution AMONG THE SAME `ACTIVE_HASHING`
  miners cannot change those census sums, so it can never repair a security-floor breach; it is
  `COVERAGE_REPAIR_WORK` (`ClassifyRecoveryWork` no longer returns `RANGE_REDISTRIBUTION_REQUIRED`), and a
  redistribution after a no-breach census remains the branch-C redistribution-only continuation. **V7:** each
  `RecoveryWorkID` has exactly one live or terminal disposition and at most one per episode is
  {ARMED, DUE, APPLYING}; terminal closure cancels EVERY nonterminal work record, so no orphan survives.
  **W1/W2 (legal setup rollback):** an ordinary-setup rollback (`RollbackParticipantSetup` /
  `RollbackTemplateRefreshSetup`) transitions with the setup transaction's IMMUTABLE `rollback_envelope`
  (a complete `{ envelope_namespace, event_time, delta_cycle, event_seq, hook_id }`) and departs any `WAKING`
  participant to `OFFLINE` via the LEGAL `T12` edge ONLY — no placeholder envelope and no illegal
  `WAKING -> REGISTERED`/`RESERVE`/`LOW_POWER_LISTEN` edge is ever passed to `ApplyMinerStateTransition`; after
  rollback no participant remains `WAKING` and no live partial assignment remains. **W6/W7 (declared results):**
  `ApplyMinerStateTransition` returns exactly one of {transition_applied, duplicate_suppressed, illegal_stale_source,
  illegal_transition} and `CreatePendingAssignment` returns exactly one of {assignment_created,
  assignment_creation_failed}; a wake is retained (and an `AssignmentID`/lease/transaction entry recorded) ONLY on the
  applied/created result. **W8 (bounded state-compatible retry):** a `SetupRetryEvent` is seated only when rollback left
  every eligible participant re-enlistable (never routed to `OFFLINE`), the retry generation is within
  `maximum_setup_retries`, and the target is within horizon; it is idempotent on `SetupRetryID`, else the round aborts.
  **X1/X2 (recovery + setup rollback are complete, version-exact state transactions):** `RollbackRecoveryAssignmentPlan`
  and the setup rollbacks depart every still-`WAKING` miner to `OFFLINE` via the legal `T12` edge using the EXACT
  assignment version (`rollback_record` items / `setup_txn.assignment_by_miner`, never `assignment_ref = null`) and a
  complete rollback envelope; they cannot report `rollback_completed` while any affected miner is `WAKING` without a live
  `WakeCompleteEvent`. **X3/X4:** template-refresh initiation (`TemplateRefresh`) is split from the post-commit
  assignment retry (`ContinueTemplateRefreshAssignmentSetup`); a retry never repeats the old-template closure or
  `TemplateCommit`, `SetupRetryEvent` guards are kind-specific (both require `ASSIGNMENT`), and an over-budget retry
  aborts rather than stranding the round. **X5:** `CommitRecoveryAssignmentPlan` returns `install_committed(rollback_record)`
  explicitly. **X6:** `assignment_creation_failed` is reachable without violating a `CreatePendingAssignment`
  precondition (runtime predicates live in the guard, not the preconditions). **X7:** every rollback/wake-failure close
  uses canonical `custody_status`/`revocation_reason`/`termination_reason` values plus a non-enum `closure_detail`.
  **X8:** each rollback `WAKING -> OFFLINE` closes `WAKING` residency at the rollback time and charges transition energy
  exactly once (F6/T12), so no `WAKING` residency survives to horizon `T`.
- **Stage-1Y clause (retry-identity & rollback-closure lock).**
  **Y1:** `SetupRetryEvent` checks EXACT-replay idempotence (a `SetupRetryID` recorded in `applied_setup_retry_ids` /
  `setup_retry_status_by_id`) BEFORE the terminal check and the wrong-round-state abort, so a replay of a retry that
  already succeeded and moved the round to `HASHING` returns `setup_retry_duplicate_suppressed` and NEVER aborts the round.
  **Y2:** a `TEMPLATE_REFRESH_SETUP` retry carries and verifies the EXACT `TemplateID_at_seat` and
  `TemplateRefreshSetupID = (RoundID, committed_new_TemplateID)` against `template_refresh_setup_committed`; there is no
  ambient "the refresh setup's TemplateID", and a stale-`TemplateID` retry never operates on the current template.
  **Y3:** the scalar `retry_generation` and the map `setup_retry_generation_by_scope`
  `(RoundID, setup_kind, TemplateRefreshSetupID_or_null)` are distinct identifiers — no identifier is both a scalar and a
  map. **Y4:** a rollback resolves every affected `WAKING` miner UNCONDITIONALLY (independent of whether the head is still
  live) and its coherence gate is "no affected miner remains `WAKING`". **Y5:** the ONE named operation
  `AbortPendingWakeForRollback` departs a `WAKING` miner via `T12` using its authoritative `ValidationAbort` trigger
  (`reason = validation_abort`, declared in `STAGE_01_MINER_STATE_MACHINE.md` §3), never the assignment
  `termination_reason`, and is the SINGLE owner of the canonical assignment close — the transition hook and the operation
  never both close the same assignment.
- **Stage-1Z clause (retry-lifecycle & rollback-snapshot lock).**
  **Z1:** the setup-retry status lifecycle is complete — `setup_retry_records[SetupRetryID]` (one record per retry) is the
  single registry; the seat publishes `SEATED`, the first dispatch flips `SEATED -> APPLYING` and executes (a SEATED
  record is never duplicate-suppressed), and the captured target result sets `APPLIED` / `SUPERSEDED` / `ABORTED` /
  `CANCELLED`; a replay is duplicate-suppressed IFF the status is already non-SEATED; the Y-era
  `applied_setup_retry_ids` / `setup_retry_status_by_id` mirror is withdrawn. **Z2:** each setup item's `before_image` is
  captured BEFORE `CreatePendingAssignment` and rollback restores the exact pre-constructor ledgers (see I20). **Z3:** a
  setup item's `WakeEventRef` is explicitly nullable with a `wake_result`; a rollback cancels only a non-null pending ref
  (no undefined lookup). **Z4:** `ApplyMinerStateTransition` takes `assignment_effect_policy` (`EDGE_DEFAULT` |
  `STATE_ONLY_ROLLBACK`); the rollback passes `STATE_ONLY_ROLLBACK` so the hook mutates no assignment and
  `AbortPendingWakeForRollback` owns the single close. **Z5:** the `T12` `ValidationAbort` rollback is bound to the exact
  `waking_origin_assignment_ref[MinerID]` (set on WAKING entry, cleared on WAKING exit); a mismatch departs no miner.
  **Z6:** `setup_transaction.rollback_items` (one complete `setup_rollback_item` per created assignment, appended before
  `StartWake`) replaces the Y-era parallel maps — no partial-map state.
- **Stage-1AA clause (retry-terminalisation & transition-policy identity lock).**
  **AA1:** `RoundAbort` RETURNS the single canonical `round_aborted(abort_record)`; every propagating procedure lists it in
  its RETURNS union and classifies the exact result, and a target `round_aborted` maps `setup_retry_record.status = ABORTED`
  (never `CANCELLED`). **AA2:** `CancelSetupRetriesForRound` (invoked by `CloseRoundAssignments`, which also lists
  `SetupRetryEvent` in its event-cancellation set) terminalises every `SEATED` record of the closing round to `CANCELLED`
  and flags an `APPLYING` record `terminal_closure_pending` (its handler finishes it `ABORTED`/`CANCELLED`) — no terminal or
  superseded round leaves a `SEATED` retry record. **AA3:** `SetupRetryEvent` resolves the record and verifies the payload
  BEFORE the stale-`RoundID` check, so a stale dispatch of a known `SEATED` record is terminalised (`SUPERSEDED`/`CANCELLED`)
  rather than left `SEATED`. **AA4:** `assignment_effect_policy` is a field of `TransitionEventID`, so transitions with
  different assignment side effects are distinct replay ids. **AA5:** `STATE_ONLY_ROLLBACK` is legal IFF the exact
  `WAKING → OFFLINE` / `validation_abort` / exact-non-null `assignment_ref` / matching `waking_origin_assignment_ref` tuple
  holds; any other use is `illegal_transition` with no mutation. **AA6:** `setup_transaction.rollback_items` is keyed by
  `RollbackItemID`; each item is created `wake_result = NOT_ATTEMPTED` / `WakeEventRef = null` before `StartWake` and updated
  explicitly by key afterward, and rollback consumes the stored keyed record.
- **Stage-1AB clause (retry-record persistence & exact abort-contract lock).**
  **AB1:** every direct value-propagator lists the exact `round_aborted(abort_record)` shape (never the bare constructor);
  `SetupRetryEvent`'s RETURNS names it once and enumerates the target dispositions explicitly. **AB2:** every guard-driven
  abort captures `disp <- CALL RoundAbort(...)` first, then persists `status = ABORTED` and `target_disposition = disp` by
  key — the stored disposition is the exact returned `round_aborted(abort_record)`. **AB3:** `rec` is a read-only snapshot;
  the seat is the only CREATE and every subsequent lifecycle mutation is a keyed UPDATE of `setup_retry_records[SetupRetryID]`;
  `CancelSetupRetriesForRound` iterates `SetupRetryID`s and updates by key. **AB4:** after its target returns,
  `SetupRetryEvent` re-reads the persisted record and classifies on the stored `terminal_closure_pending`, so a record whose
  round closed can never finish `APPLIED`. **AB5:** `dispatched_event_ref` binds ownership — an unknown id or a foreign
  `dispatched_event_ref ≠ rec.event_ref` stale-noops (leaving the genuine record seated), and the genuine event with a
  mismatched payload is an integrity abort that terminalises the record and cancels any residual event. **AB6:**
  `CancelSetupRetriesForRound` uses keyed updates and clears a cancelled record's `event_ref`, so after closure no record is
  `SEATED` and none holds a queued event.
- **Planned test stage.** Stage 3 (security-floor breach behaviour) with Stage 5 (adversarial) and
  Stage 8 (reporting-integrity) checks.
- **Consequence of violation.** Hidden security degradation; overstated safety; dishonest
  reporting of the reduced-participation regime; a branch-C install failure silently reported as a
  genuine `UNRECOVERABLE` floor breach, or a reserve-dependent restoration reported as recovered before
  the reserve is actually active.

### I17 — Active hash rate decomposes exactly into honest and adversarial contributions.

- **Formal statement.** For every event-update time `t`,
  `H_active(t) = H_honest(t) + H_adversarial(t)` **exactly**, where `H_honest(t)` is the sum of the
  hash rates of honest miners in `ACTIVE_HASHING`, `H_adversarial(t)` is the sum of the hash rates
  of adversarial miners in `ACTIVE_HASHING`, and `H_active(t)` is the sum of the hash rates of all
  miners in `ACTIVE_HASHING`. `H_adversarial(t)` is computed **deterministically** from the
  active-state census and is **never** sampled independently after `H_active(t)`. When
  `H_active(t) = 0`, `q_adv(t)` is **undefined / NA** and a security-floor breach is recorded — it
  is **not** treated as zero.
- **Scope.** Time-varying hash-rate accounting; adversarial-share (`q_adv`) computation;
  security-floor evaluation.
- **Required inputs.** Per-miner honest/adversarial classification; the per-miner active-state
  census at `t`; per-miner modeled hash rates.
- **Enforcement point.** The central `ApplyMinerStateTransition` hook (Stage 1F, F6) recomputes
  `H_honest`/`H_adversarial`/`H_active` from the post-transition `ACTIVE_HASHING` census and
  re-checks this identity at **every** `ACTIVE_HASHING` entry and exit boundary. Every
  adversarial-participation change is carried by a scheduled `AdversarialParticipationChangeEvent`
  (G3/H6) that mutates the census ONLY through this hook; `ActiveHashRateUpdate` is **compute-only**
  (no sampling, no census mutation — G3). **Q4/R5/U7/U1:** the census maps `latest_security_census[event_time]` and
  `security_census_dirty[event_time]` have ONE canonical atomic writer, `CommitSecurityCensus`, with **seven**
  named `census_source` values (R5/U7/U1): MINER_STATE_TRANSITION, APPLICABILITY_ENTRY, RECOVERY_DEADLINE,
  RECOVERY_COMPLETION_DUE (the completion-due checkpoint, §10a), RECOVERY_CONTINUATION_DUE (the branch-C
  continuation-due checkpoint `RecoveryAssignmentContinuationDueEvent`, §10a, U7), RECOVERY_WORK_DUE (the
  recovery-work checkpoint `RecoveryWorkDueEvent`, §9c, U1), and POST_RECOVERY_APPLICATION (the single
  post-application settlement `FinalizePostRecoveryApplicationState`, §10a/R2). Every producer (this hook and the
  capture procedures) CALLS `CommitSecurityCensus` rather than writing the maps directly — NO producer is itself a
  direct writer (R5) — and `dirty[t] = true ⇒ latest[t] exists` is structural. **R5:** the census-write order is
  the EXPLICIT per-run counter `security_census_write_seq_by_event_time` (a `RunContext` field owned SOLELY by
  `CommitSecurityCensus`, initialised in `RunInitialise` and preserved across rounds), replacing the implicit
  "next per-event_time ordinal". The single settled-census event-time epilogue `FinalizeEventTimeSecurityCensus`
  (H3, keyed by `event_time` alone per I-01/I-02; O5) reads the FINAL census EXACTLY ONCE per settled `event_time`
  — AFTER the whole `event_time` is quiescent, never before certificate/discovery events — and invokes
  `SecurityFloorEvaluate` exactly once; no per-transition floor decision is scheduled. **R2:** any post-application
  re-dirty at `t` is settled by `FinalizePostRecoveryApplicationState` (a settlement, NOT a second floor decision),
  so the epilogue still runs exactly once per `event_time`. **S6:** `ProcessEventTime` invokes
  `FinalizeEventTimeSecurityCensus(t)` EXACTLY ONCE and UNCONDITIONALLY (the procedure owns the dirty check and
  returns `no_census_change` when nothing is dirty); the CALL is no longer guarded by `IF security_census_dirty[t]`.
  **S5:** the dirty flag is cleared by EXACTLY ONE procedure `SettleSecurityCensusDirty` with two declared
  settlement kinds (`PRIMARY_EPILOGUE` from the epilogue, `POST_RECOVERY_APPLICATION` from the settlement), removing
  the earlier contradiction in which the epilogue was named the sole clearer while the settlement also cleared it;
  `CommitSecurityCensus` remains the sole setter of `dirty = true` and the sole writer of the latest census.
  **T1/T7:** the branch-C continuation application (`ApplyRecoveryAssignmentContinuationAfterEpilogue`) runs
  STRICTLY AFTER the single event-time epilogue and the completion application, so it never re-decides the floor;
  it reads and re-verifies the FINAL versioned census (T2: its `continuation_bound_census_version` must equal
  `latest_recovery_census[episode].RecoveryCensusVersion`) before applying, and every `StartWake`/re-arm it seats
  is placed at a STRICTLY LATER `event_time` through `PostEpilogueSchedulingContext` — so no census the continuation
  produces lands at the already-settled `event_time`.
- **Planned test stage.** Stage 3 (time-varying hash rate, security floor, reserve activation).
- **Consequence of violation.** Inconsistent hash-rate decomposition; `q_adv(t)` derived from an
  independently sampled adversarial term; a zero-active-rate regime silently reported as safe
  instead of as a recorded floor breach.

---

### I18a / I18b — Assignment-lineage version invariants (Stage 1F I18, corrected in G2).

An assignment is an immutable versioned object with a stable `lineage_id` shared by all versions of
one holder-range. **The Stage-1F formulation "exactly one CURRENT per lineage at every instant" is
replaced by two consistent invariants** (the old form was impossible while a lineage's unique head is
`PENDING` or `PAUSED`, or after closure):

- **I18a (at-most-one CURRENT).** For each `lineage_id`, `count(versions with status = CURRENT) <= 1`
  at all observable times. Zero CURRENT versions is LEGAL.
- **I18b (unique live head).** For each OPEN `lineage_id`, EXACTLY ONE version is a live head in
  `{PENDING, CURRENT, PAUSED}`; after lineage closure, ZERO live heads exist. A same-range lease
  renewal is an **atomic** operation linearised at `renewal_time`: it marks the old `CURRENT` version
  `SUPERSEDED` (with `superseded_at`) and publishes a new `CURRENT` version on the SAME range/holder
  with copied actual/reported/accepted frontiers and provenance, in ONE step, so no observer sees two
  CURRENT versions. The old version's identity is never mutated in place; it stays immutable and
  resolvable, so a `SolutionEligibilitySnapshot` taken under it resolves to that exact version.

- **Scope.** Range-lease renewal; assignment versioning; discovery-snapshot resolution. Internal
  structural consistency invariants; they introduce no new consensus feature.
- **Required inputs.** The assignment version ledger keyed by `(lineage_id, assignment_version)`;
  per-version `status`; the `renewal_time`.
- **Enforcement point.** `RenewAssignment` (atomic supersede-and-publish, SOLE renewal path — G2);
  `CreatePendingAssignment` (opens ORIGINAL/REASSIGNED fresh lineages, never RENEWED); `ValidateCandidate`
  resolves each snapshot's `(AssignmentID, assignment_version)` to its immutable version. **J7 canonical
  terminal status:** `SUPERSEDED` is used ONLY for atomic same-range renewal (a new `CURRENT` is published
  in the same step); every non-renewal end-of-life (revocation, adversarial withdrawal, abandonment, wake
  failure, cancellation, round closure, template closure) sets `status = CLOSED`. A CLOSED lineage has
  ZERO live heads (I18b) — in particular an adversarial withdrawal closes with `status = CLOSED`,
  `custody_status = revoked`, `revocation_reason = adversarial_withdrawal` (I-07), leaving no live head.
- **Planned test stage.** Stage 4 (leases, reassignment, renewal).
- **Consequence of violation.** Two CURRENT versions in one lineage (ambiguous acceptance target); a
  renewal that mutates identity in place (invalidating a discovery snapshot, violating E1/I2); or an
  impossible "always exactly one CURRENT" requirement that a PENDING/PAUSED head cannot satisfy.

---

### I19 — State-residency time has a single owner and is never double-counted (H7; cross-round continuity K3; single idempotent boundary owner L5).

- **Formal statement.** For every miner and every occupancy of a state, the residency duration
  `t_<state>` (including `t_ACTIVE_HASHING = t_hash`) is produced **exactly once**, by the single
  `residency_ledger` owned by `ApplyMinerStateTransition`, which opens the interval at the entry
  boundary and closes it at the exit boundary and accrues `P_<state> · (t_exit − t_entry)`. No other
  procedure increments any `t_<state>`: in particular a `HashWorkEvent` records hash-work **metadata
  only** and adds **zero** duration, so the elapsed time of an `ACTIVE_HASHING` occupancy is counted
  once (at the boundary) and never a second time per hash unit. For each `(miner, state occupancy)`
  the sum of all recorded residency contributions equals the single boundary-to-boundary interval,
  and these intervals partition the miner's timeline with the state-energy accounting of I5/I6.
  **Cross-round continuity (K3, amended; single idempotent owner L5; unified with run-end M4):** a state
  that PERSISTS across a boundary is NOT reset silently; the boundary is a bookkeeping settle performed by
  ONE procedure, `SettleResidencyBoundary` (M4/L5, which SUPERSEDES the former `FinalizeRoundResidency` /
  `BeginRoundResidency`). With `mode = REBASE_TO_NEXT_ROUND` it closes the open interval (attributing its
  energy to the OLD round) AND reopens the SAME state at the IDENTICAL `boundary_time = round_terminal_time`
  for the new round, charging NO transition energy; with `mode = FINAL_RUN_END` it closes every open
  interval at the run horizon with NO reopen. It is **idempotent** via a deterministic `boundary_id`
  (`(prior_RoundID, new_RoundID)` or `(RunID, RUN_END)`): a replayed or retried `RoundInitialise`
  (`REBASE_TO_NEXT_ROUND`) or `FinalizeSimulationRun` (`FINAL_RUN_END`) re-invoking it is a no-op, so a
  boundary is never applied twice. **N1:** the `FINAL_RUN_END` settle is owned SOLELY by
  `FinalizeSimulationRun` (the run-level finaliser that runs EXACTLY ONCE at the horizon `T`); **`RoundAbort`
  performs NO run-end settle** — it terminates ONE round, and an early abort at `t < T` is followed by a
  `RoundInitialise` `REBASE_TO_NEXT_ROUND` boundary. **M4:** `CloseRoundAssignments` performs NO
  residency/energy finalisation — it records `round_terminal_time` ONLY; the earlier in-line `finalise
  state durations and energy to the exact closure time` is removed, so there is no competing owner. The idle
  interval between a round's closure and the next round's `StartWake` (or the run horizon) is therefore
  counted **exactly once**, across the boundary.
- **Scope.** Per-miner residency-time accounting; the `ACTIVE_HASHING`/`t_hash` boundary in
  particular; the interaction between event-scheduled hashing (G9) and residency accrual. A
  structural accounting invariant; it introduces no new consensus feature and does not change the
  A1 baseline (`8.420833333 kWh`) — any energy change is attributable ONLY to reduced active
  power-time, never to a change in how time is counted.
- **Required inputs.** The `residency_ledger` interval log keyed by `(MinerID, state, entry_time)`;
  the per-state power levels `P_<state>`; the ordered `ApplyMinerStateTransition` boundaries.
- **Enforcement point.** `ApplyMinerStateTransition` (SOLE residency owner — opens/closes every
  interval, H7); `HashWorkEvent` (records metadata only, increments no `t_<state>` — H7/G9);
  `SettleResidencyBoundary` (M4/L5 — the ONLY boundary residency close/reopen: a SINGLE idempotent owner
  keyed by `boundary_id`, with `REBASE_TO_NEXT_ROUND` (from `RoundInitialise`) and `FINAL_RUN_END` (from
  `FinalizeSimulationRun` ONLY, N1) modes, superseding `FinalizeRoundResidency`/`BeginRoundResidency`);
  `FinalizeSimulationRun` (N1/O1 — the run-level HOOK that owns the single `FINAL_RUN_END` settle at the
  horizon `T` and the subsequent I5/I6/I7 reconciliation; O1 narrowed it so it no longer drains the queue or
  closes a round — the drain is the run driver's and the horizon-close is `CloseRoundAtHorizon`'s;
  `RoundAbort` does NOT settle at the horizon);
  `CloseRoundAtHorizon` (O1/P2 — the run-level hook that closes a still-nonterminal round at `T` via
  `CloseRoundAssignments` with a distinct horizon-end disposition, BEFORE the `FINAL_RUN_END` settle; performs
  NO residency finalisation itself. P2: it uses ONE deterministic run-hook envelope (`HorizonHookID`, reserved
  `RUN_HOOK_CYCLE`) and is idempotent via `applied_run_hook_ids`, so a replayed horizon close produces
  `horizon_close_duplicate_noop` — NO second transition energy and NO second residency boundary; it always runs
  exactly once per run via the P1 horizon sentinel. **R3:** the horizon envelope's `envelope_namespace = RUN_HOOK`
  and `hook_id = HorizonHookID` are threaded through `CloseRoundAssignments → EnterLowPowerListen →
  ApplyMinerStateTransition`, so every nested horizon-close miner transition carries them in its
  `TransitionEventID` and is distinct from — and replay-suppressed independently of — any ordinary transition that
  shares its numeric `(event_time, delta_cycle, event_seq)`);
  `CloseRoundAssignments` (records `round_terminal_time` ONLY, performs NO residency finalisation — M4);
  `residency_ledger` (single writer). I5/I6 reconcile the
  resulting durations and energies.
- **Planned test stage.** Stage 3 (state-residency and energy accounting).
- **Consequence of violation.** The same `ACTIVE_HASHING` interval charged twice (once at the
  boundary and again per hash unit), inflating `t_hash`/`E_hash`; a residency time written by two
  owners; or an energy figure whose reduction is mis-attributed to double-counted time rather than
  to reduced active power-time.

---

### I20 — A setup/recovery rollback restores the exact pre-constructor coverage/custody ledgers (Stage 1Z, Z2).

- **Formal statement.** For every setup transaction item (and every recovery-plan rollback item), the
  `before_image` (`coverage_custody_before_image`) is the I8a/I8b coverage-state / custody-ledger snapshot captured
  **immediately before** `CreatePendingAssignment` (or the plan-bound constructor) mutates `custody_status(range)` and
  appends to `assignment_ledger`. On rollback, `AbortPendingWakeForRollback` (setup) / `RollbackRecoveryAssignmentPlan`
  (recovery) RESTORES the ledgers for the item's range from that `before_image`, so the post-rollback I8a/I8b values equal
  the exact pre-constructor values — never a post-mutation snapshot. On a creation failure the `before_image` is discarded
  and no transaction item exists, so nothing is restored for an assignment that was never created.
- **Scope.** The setup transaction items (`PrepareParticipantsForNewRound`, `ContinueTemplateRefreshAssignmentSetup`) and
  the recovery-plan rollback items (`CommitRecoveryAssignmentPlan`); a structural rollback-fidelity invariant. It does not
  change the A1 baseline (`8.420833333 kWh`).
- **Required inputs.** The `before_image` captured before creation (Z2); the item's `range`; the I8a/I8b ledgers.
- **Enforcement point.** `PrepareParticipantsForNewRound` / `ContinueTemplateRefreshAssignmentSetup` (capture before
  `CreatePendingAssignment`, Z2); `CommitRecoveryAssignmentPlan` (capture before the constructor, X1);
  `AbortPendingWakeForRollback` / `RollbackRecoveryAssignmentPlan` (restore from `before_image`).
- **Consequence of violation.** A rollback that restores a post-mutation ledger state (leaving a range marked
  `original`/`reassigned`/searched by an assignment that was rolled back), so coverage/custody accounting diverges from
  the true pre-setup state.

---

## Cross-reference summary

| ID | one-line statement | primary test stage | primary enforcement point |
|---|---|---|---|
| I1 | No overlap among valid active assignments | Stage 2 (+4) | assignment / reassignment overlap guard |
| I2 | Accepted solution binds to the assignment version eligible at DISCOVERY time (not CURRENT-at-acceptance; G1) | Stage 2 (+4/5) | ValidateCandidate discovery-snapshot predicate |
| I3 | Accepted solution matches current RoundID/TemplateID | Stage 2 (+4/5) | acceptance + commitment check |
| I4 | LOW_POWER_LISTEN entry needs one of four triggers, each with a stop_reason | Stage 2 (+4) | listen-transition guard |
| I5 | Non-negative durations reconcile to horizon T | Stage 2 (+3) | duration reconciliation |
| I6 | State energies sum to per-miner energy | Stage 2 (+3) | per-miner aggregation |
| I7 | Per-miner energies sum to network energy | Stage 2 | network aggregation |
| I8a | Accepted coverage states partition the assigned domain exactly (accepted_searched + active_unsearched + inactive_unsearched) | Stage 2 (+4) | coverage-state reconciliation |
| I8b | Custody / provenance model (orthogonal to coverage) | Stage 4 | custody / lineage tracking |
| I9 | Reassignments carry complete provenance | Stage 4 | reassignment logging |
| I10 | Reserve activation adds no overlap | Stage 3 (+5) | reserve-activation guard |
| I11 | No stop without full early-stop certificate validation | Stage 4 (+5) | early-stop verification guard |
| I12 | Difficulty fixed in confirmatory design | Stage 2 (all) | round init / commitment |
| I13 | No double-counting of shared executions | Stage 2 (+7) | accounting de-duplication |
| I14 | Zero-block outcomes retained | Stage 8 (+7) | results recording |
| I15 | Undefined block-normalised metrics are NA | Stage 8 | metrics computation |
| I16 | Floor breaches recorded, never silently repaired | Stage 3 (+5/8) | floor eval + recording |
| I17 | H_active = H_honest + H_adversarial (census-deterministic; recomputed at every ACTIVE_HASHING boundary via ApplyMinerStateTransition, F6); q_adv NA at zero active rate | Stage 3 | central transition hook + active-hash-rate decomposition |
| I18a | At most one CURRENT version per lineage; zero CURRENT is legal (G2) | Stage 4 | RenewAssignment / version ledger |
| I18b | Every OPEN lineage has exactly one live head in {PENDING, CURRENT, PAUSED}; zero after closure; renewal atomic at renewal_time (G2) | Stage 4 | RenewAssignment / CreatePendingAssignment |
| I19 | State-residency time (incl. t_ACTIVE_HASHING = t_hash) has a single owner (residency_ledger via ApplyMinerStateTransition) and is never double-counted; HashWorkEvent adds zero duration (H7) | Stage 3 | central transition hook / residency_ledger |

No invariant above is asserted to hold in any implementation at Stage 1; each is a
specification target with a planned verification stage.
