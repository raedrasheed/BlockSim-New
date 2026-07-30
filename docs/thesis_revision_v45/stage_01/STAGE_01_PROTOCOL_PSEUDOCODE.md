# Stage 1 — PoCol Protocol Pseudocode

> **THIS IS PSEUDOCODE, NOT EXECUTABLE SOURCE.**
> Every block below is structured, language-neutral pseudocode written for specification and
> review. It intentionally uses no importable programming language, no real library, and no
> real API. It cannot be compiled or run. It describes **PoCol** with **the idle policy within
> PoCol** enabled. Nothing here is claimed to be implemented, validated, secure, fair, or
> incentive-compatible; at Stage 1 no property is experimentally supported.

## How to read these procedures

- **Keywords** are uppercase: `PROCEDURE`, `INPUTS`, `PRECONDITIONS`, `EFFECTS`, `RETURNS`,
  `IF/ELSE`, `FOR EACH`, `WHILE`, `ASSERT`, `RECORD`, `TRANSITION`.
- **`[SIMULATION SAMPLING]`** marks every step that draws a random value from the simulation
  model rather than executing deterministic protocol logic. These steps exist ONLY because
  Stage-1 evaluation is a simulation; they are not part of the deployed protocol logic and
  are the ONLY source of randomness. All other steps are deterministic protocol logic.
- Referenced identifiers are canonical:
  - Miner states: `REGISTERED`, `RESERVE`, `ACTIVE_HASHING`, `EXHAUSTED_PENDING`,
    `LOW_POWER_LISTEN`, `WAKING`, `OFFLINE`, `DISQUALIFIED`.
  - Round states: `ROUND_INITIALISING`, `TEMPLATE_COMMITMENT`, `ASSIGNMENT`, `HASHING`,
    `SECURITY_RECOVERY`, `SOLUTION_PROPAGATION`, `ROUND_ACCEPTED`, `ROUND_EXHAUSTED`,
    `TEMPLATE_REFRESH`, `ROUND_ABORTED`.
  - Invariants `I1..I16` are defined in `STAGE_01_INVARIANT_CATALOGUE.md`.
  - Progress evidence is a **modeled progress-verification abstraction**, never a
    cryptographic proof. Target checks are a **modeled progress-verification abstraction**.
  - `q_adv(t) = H_adversarial(t) / (H_honest(t) + H_adversarial(t))`.
  - Difficulty `D` is FIXED (`I12`); the horizon is `T = 10,000 s`.

---

## 1. Round initialisation

```
PROCEDURE RoundInitialise
  INPUTS: config (difficulty D0, horizon T, nonce_domain, floor parameters), prior_state
  PRECONDITIONS: no active round OR prior round dispositioned
  EFFECTS:
    SET RoundID <- fresh monotonic identifier
    SET difficulty D <- D0                          # fixed for the round (I12)
    SET nonce_domain <- config.nonce_domain
    INITIALISE assignment_ledger <- empty           # supports I8
    INITIALISE reassignment_log  <- empty           # supports I9
    INITIALISE energy_ledger     <- empty           # supports I5, I6, I7
    INITIALISE floor_state       <- config.floor parameters
    TRANSITION round_state -> ROUND_INITIALISING
    TRANSITION round_state -> TEMPLATE_COMMITMENT
  RETURNS: RoundContext(RoundID, D, nonce_domain, ledgers)
```

## 2. Template commitment

```
PROCEDURE TemplateCommit
  INPUTS: RoundContext, candidate_template
  PRECONDITIONS: round_state = TEMPLATE_COMMITMENT
  EFFECTS:
    SET TemplateID <- stable identifier bound to candidate_template   # immutable for round
    RECORD committed(RoundID, TemplateID)
    ASSERT difficulty unchanged since RoundInitialise                 # I12
    BROADCAST committed(RoundID, TemplateID) to all REGISTERED miners
    TRANSITION round_state -> ASSIGNMENT
  RETURNS: TemplateID
  NOTE: A later change of mined content requires TemplateRefresh (new TemplateID); the
        committed template is never mutated in place.
```

## 3. Miner registration

```
PROCEDURE MinerRegister
  INPUTS: RoundContext, join_request
  PRECONDITIONS: round admits participation
  EFFECTS:
    SET MinerID <- identifier for join_request
    CREATE miner_record(MinerID) with declared power parameters
        (P_hash, P_listen, P_wake, P_offline)
    TRANSITION miner_state(MinerID) -> REGISTERED
    OPTIONALLY TRANSITION miner_state(MinerID) -> RESERVE   # held, not yet assigned
  RETURNS: MinerID
  NOTE: Registration is the precondition for any assignment. Sybil considerations are OUT OF
        SCOPE at Stage 1 (see STAGE_01_THREAT_MODEL.md); this procedure does not claim Sybil
        resistance.
```

## 4. Range assignment

```
PROCEDURE RangeAssign
  INPUTS: RoundContext, MinerID, requested_size, lease_duration
  PRECONDITIONS: miner_state(MinerID) in {REGISTERED, RESERVE}; round_state = ASSIGNMENT or HASHING
  EFFECTS:
    SELECT candidate_range from unassigned portion of nonce_domain
    # Deterministic overlap guard -- enforces I1
    FOR EACH active_assignment A in assignment_ledger:
      ASSERT candidate_range INTERSECT range(A) = EMPTY        # I1
    SET lease_start  <- now
    SET lease_expiry <- now + lease_duration
    CREATE assignment(MinerID, candidate_range, TemplateID, RoundID, lease_start, lease_expiry)
    APPEND assignment to assignment_ledger                     # supports I8
    TRANSITION miner_state(MinerID) -> ACTIVE_HASHING
  RETURNS: assignment
```

## 5. Active hashing

```
PROCEDURE ActiveHashing
  INPUTS: RoundContext, assignment, step_budget
  PRECONDITIONS: miner_state = ACTIVE_HASHING; assignment VALID and CURRENT
  EFFECTS:
    SET cursor <- next unsearched nonce in range(assignment)
    WHILE cursor within range(assignment) AND round_state = HASHING AND step_budget > 0:
      # ---- deterministic protocol logic ----
      ASSERT cursor in range(assignment)                       # supports I2 at submission time
      # ---- [SIMULATION SAMPLING] ----
      # Whether this modeled execution meets the fixed target D is drawn from the simulation
      # model; it replaces real hashing. It is the ONLY randomness in this procedure.
      hit <- [SIMULATION SAMPLING] Bernoulli(target_hit_probability(D))
      # ---- deterministic protocol logic ----
      ACCUMULATE t_hash for miner over this step               # supports I5, I6
      CONTRIBUTE this step to active hash rate                 # only ACTIVE_HASHING contributes
      IF hit:
        # A valid candidate solution satisfying the fixed target D was found (active-hashing path).
        candidate_hash <- modeled digest of TemplateID and cursor    # deterministic protocol logic
        candidate_solution <- (RoundID, TemplateID, AssignmentID(assignment), MinerID,
                               cursor AS nonce, candidate_hash, D AS target)
        # CR1: an early-stop certificate is generated ONLY here, from a found valid solution --
        #      NEVER from aggregated progress commitments, searched coverage, or claimed exhaustion.
        CALL EarlyStopGenerate(RoundContext, candidate_solution)
        RETURN CALL ValidBlockAccept(RoundContext, candidate_solution)
      ADVANCE cursor
      DECREMENT step_budget
      PERIODICALLY CALL ProgressCommit(assignment, cursor)     # emits progress evidence
    IF cursor beyond range(assignment):
      RETURN CALL RangeExhaust(RoundContext, assignment)
  RETURNS: continuation marker (solution | exhausted | preempted)
```

## 6. Range exhaustion

```
PROCEDURE RangeExhaust
  INPUTS: RoundContext, assignment
  PRECONDITIONS: cursor has traversed all of range(assignment)
  EFFECTS:
    emit final ProgressCommit covering range(assignment)       # modeled progress abstraction
    MARK range(assignment) as searched in assignment_ledger    # supports I8a
    # CR5: separate simulator GROUND TRUTH from the PROTOCOL-LEVEL exhaustion claim.
    SET reported_exhaustion <- miner's claim that range(assignment) is fully searched
    # ---- honest path ----
    # EXHAUSTED_PENDING eligibility uses ACTUAL cursor completion (simulator ground truth).
    IF actual_exhaustion(assignment) is TRUE:                  # actual cursor completed the range
      TRANSITION miner_state(MinerID) -> EXHAUSTED_PENDING
    # ---- adversarial path ----
    ELSE:
      # reported_exhaustion is compared with ground truth through a modeled audit/detection
      # abstraction -- NOT a cryptographic proof.
      # ---- [SIMULATION SAMPLING] ----
      audit_selected <- [SIMULATION SAMPLING] audit_selection_model(assignment)
      # ---- deterministic protocol logic ----
      IF audit_selected:
        audit_result <- compare(reported_exhaustion, actual_exhaustion(assignment))
        claim_accepted_or_rejected <- (audit_result = consistent)
      ELSE:
        claim_accepted_or_rejected <- reported_exhaustion       # unaudited claim taken as reported
      IF claim_accepted_or_rejected:
        TRANSITION miner_state(MinerID) -> EXHAUSTED_PENDING
      ELSE:
        RECORD false_exhaustion_detected(MinerID, assignment)   # NO transition to EXHAUSTED_PENDING
  RETURNS: exhaustion_record(MinerID, range, RoundID, TemplateID)
  NOTE: EXHAUSTED_PENDING is the ONLY legitimate precondition (besides explicit revocation)
        for entering LOW_POWER_LISTEN -- see I4. A progress commitment NEVER proves that no valid
        solution exists in the whole range; exhaustion findings are modeled, not proven.
```

## 7. Transition to low-power listening

```
PROCEDURE EnterLowPowerListen
  INPUTS: RoundContext, MinerID, trigger
  PRECONDITIONS:
    (miner_state(MinerID) = EXHAUSTED_PENDING AND exhaustion accounting accepted)
     OR trigger = EXPLICIT_REVOCATION                          # guard enforces I4
  EFFECTS:
    ASSERT precondition holds                                  # I4: no early idling
    RELEASE any held range back to pool (mark inactive/reassignable)   # supports I8
    TRANSITION miner_state(MinerID) -> LOW_POWER_LISTEN
    BEGIN accumulating t_listen at P_listen                    # supports I6; not active rate
  RETURNS: listen_record(MinerID)
```

## 8. Active-hash-rate update

```
PROCEDURE ActiveHashRateUpdate
  INPUTS: RoundContext, time t
  PRECONDITIONS: none
  EFFECTS:
    SET H_active(t)     <- SUM over miners in ACTIVE_HASHING of their modeled hash rate
    SET H_honest(t)     <- SUM over honest miners in ACTIVE_HASHING
    # ---- [SIMULATION SAMPLING] ----
    # Adversarial active participation for the scenario is drawn from the simulation model.
    H_adversarial(t) <- [SIMULATION SAMPLING] adversarial_participation_model(t)
    # ---- deterministic protocol logic ----
    SET q_adv(t) <- H_adversarial(t) / (H_honest(t) + H_adversarial(t))
    RECORD (H_active(t), H_honest(t), q_adv(t))
  RETURNS: (H_active(t), H_honest(t), q_adv(t))
  NOTE: Only ACTIVE_HASHING contributes to active hash rate; LOW_POWER_LISTEN, WAKING,
        RESERVE, OFFLINE contribute nothing to it.
```

## 9. Security-floor evaluation

```
PROCEDURE SecurityFloorEvaluate
  INPUTS: RoundContext, (H_active(t), H_honest(t), q_adv(t)), floor_state
  PRECONDITIONS: none
  EFFECTS:
    breach <- FALSE
    IF H_active(t) < floor_state.active_floor:
      RECORD breach_event(active_floor, t)                     # I16: recorded, not repaired
      breach <- TRUE
    IF H_honest(t) < floor_state.honest_floor:
      RECORD breach_event(honest_floor, t)                     # I16
      breach <- TRUE
    IF q_adv(t) > floor_state.q_adv_threshold:
      RECORD breach_event(adversarial_share, t)                # I16
      breach <- TRUE
    IF breach:
      TRANSITION round_state -> SECURITY_RECOVERY
  RETURNS: breach
  NOTE: Recovery actions are logged separately and never overwrite breach_event records (I16).
```

## 10. Reserve activation

```
PROCEDURE ReserveActivate
  INPUTS: RoundContext, deficit (rate to restore)
  PRECONDITIONS: round_state = SECURITY_RECOVERY or ASSIGNMENT
  EFFECTS:
    SELECT reserve_miner from miners in RESERVE
    SELECT candidate_range from unsearched/reassignable portion of nonce_domain
    FOR EACH active_assignment A in assignment_ledger:
      ASSERT candidate_range INTERSECT range(A) = EMPTY        # I10 (preserves I1)
    TRANSITION miner_state(reserve_miner) -> WAKING            # incurs wake latency/energy
    RETURN CALL WakeComplete(RoundContext, reserve_miner, candidate_range)
  RETURNS: activation_record | activation_failure
```

## 11. Wake completion

```
PROCEDURE WakeComplete
  INPUTS: RoundContext, MinerID, target_range
  PRECONDITIONS: miner_state(MinerID) = WAKING
  EFFECTS:
    # ---- [SIMULATION SAMPLING] ----
    wake_latency <- [SIMULATION SAMPLING] wake_latency_model(MinerID)
    # ---- deterministic protocol logic ----
    ACCUMULATE t_wake at P_wake for wake_latency; ADD E_transition   # supports I6
    IF wake_latency <= wake_deadline:
      CALL RangeAssign-style activation of target_range to MinerID    # re-checks I1/I10
      TRANSITION miner_state(MinerID) -> ACTIVE_HASHING
      RETURN activation_record
    ELSE:
      RECORD reserve_wake_failure(MinerID)
      TRANSITION miner_state(MinerID) -> OFFLINE                # or DISQUALIFIED per policy
      RETURN activation_failure
```

## 12. Range lease expiry

```
PROCEDURE LeaseExpiry
  INPUTS: RoundContext, assignment, time t
  PRECONDITIONS: t >= lease_expiry(assignment) AND assignment not renewed
  EFFECTS:
    MARK range(assignment) as reassignable in assignment_ledger    # supports I8
    INVALIDATE assignment (holder's assignment no longer CURRENT)   # stale mining -> I2 reject
    IF holder wishes to continue AND policy allows renewal:
      RENEW lease_expiry <- t + lease_duration
    ELSE:
      RETURN CALL RangeReassign(RoundContext, range(assignment),
                                reason=lease_expiry, from_miner=holder)
  RETURNS: lease_disposition (renewed | released)
```

## 13. Range reassignment

```
PROCEDURE RangeReassign
  INPUTS: RoundContext, range, reason, from_miner
  PRECONDITIONS: range is reassignable; reason in {lease_expiry, exhaustion, departure, conflict, recovery}
  EFFECTS:
    SELECT to_miner from {RESERVE, REGISTERED} miners (or via ReserveActivate)
    FOR EACH active_assignment A in assignment_ledger:
      ASSERT range INTERSECT range(A) = EMPTY                   # I1 preserved
    prior_pc <- last accepted ProgressCommit covering range     # de-dup key material (I13)
    CREATE assignment(to_miner, range, TemplateID, RoundID, new lease window)
    APPEND reassignment record
        (range, from_miner, to_miner, reason, timestamp, prior_pc)   # I9 complete provenance
    # CR4: coverage uses I8a; custody/provenance is tracked SEPARATELY as I8b.
    UPDATE assignment_ledger so the coverage partition still holds (I8a):
        searched + active_unsearched + inactive_unsearched = assigned_domain
    # I8b custody/lineage status is orthogonal and is NEVER an additive coverage term.
    SET custody_status(range) <- reassigned   # in {original, renewed, reassigned, revoked, expired, abandoned}
    # The reassigned range retains an INDEPENDENT coverage state
    # (searched / active_unsearched / inactive_unsearched).
  RETURNS: reassignment_record
```

## 14. Progress commitment

```
PROCEDURE ProgressCommit
  INPUTS: RoundContext, assignment, cursor
  PRECONDITIONS: miner_state = ACTIVE_HASHING
  EFFECTS:
    # CR5: distinguish simulator GROUND TRUTH from the PROTOCOL-LEVEL claim.
    # ---- simulator ground truth (known to the simulator, not asserted by the protocol) ----
    actual_frontier            <- true cursor position reached in range(assignment)
    actual_positions_evaluated <- true count of positions evaluated so far
    actual_solution_positions  <- true set of solution-bearing positions in range (if any)
    # ---- protocol-level claim (what the miner reports) ----
    reported_frontier <- coverage the miner claims, from lower bound up to cursor
    CREATE progress_commitment(MinerID, range(assignment), reported_frontier, RoundID, TemplateID, t)
    RECORD progress_commitment                                  # modeled progress-verification abstraction
    UPDATE searched measure in assignment_ledger for this range # supports I8a
  RETURNS: progress_commitment
  NOTE: This is a MODELED PROGRESS-VERIFICATION ABSTRACTION, NOT a cryptographic proof of
        range exhaustion. A progress commitment states "I claim to have searched up to this
        frontier"; it NEVER proves that no valid solution exists in the whole range. It cannot
        by itself justify stopping without target verification (I11).
```

## 15. Early-stop certificate generation

```
PROCEDURE EarlyStopGenerate
  INPUTS: RoundContext, found_solution = (RoundID, TemplateID, AssignmentID, MinerID,
          nonce, candidate_hash, target)
  PRECONDITIONS: round_state in {HASHING, SECURITY_RECOVERY};
                 found_solution is a valid candidate solution satisfying the current target,
                 discovered in the ACTIVE_HASHING path (see ActiveHashing)
  EFFECTS:
    # CR1: an early-stop certificate is generated ONLY after a miner finds a valid candidate
    # solution satisfying the current target. It MUST NOT be generated from aggregated progress
    # commitments, searched-domain coverage, claimed exhaustion, sufficient coverage, or a
    # progress frontier. Progress verification and early-stop certification are completely
    # separate mechanisms (see ProgressCommit, which is a distinct procedure).
    ASSERT found_solution came from a found valid candidate solution     # NOT from coverage/frontier
    CREATE early_stop_certificate CONTAINING EXACTLY:
        RoundID                  <- found_solution.RoundID
        TemplateID               <- found_solution.TemplateID
        AssignmentID             <- found_solution.AssignmentID
        MinerID                  <- found_solution.MinerID
        nonce                    <- found_solution.nonce
        candidate_hash           <- found_solution.candidate_hash
        target                   <- found_solution.target
        signature/authentication <- authenticate(found_solution.MinerID, the fields above)
    RECORD early_stop_certificate (proposed, not yet honoured)
  RETURNS: early_stop_certificate
  NOTE: A progress commitment says "I claim to have searched up to this frontier." An early-stop
        certificate says "I found this exact valid solution." Generation alone NEVER stops
        hashing; it must pass EarlyStopVerify, which requires target verification (I11).
```

## 16. Early-stop verification

```
PROCEDURE EarlyStopVerify
  INPUTS: RoundContext, early_stop_certificate, verifying_MinerID
  PRECONDITIONS: round_state in {HASHING, SECURITY_RECOVERY};
                 miner_state(verifying_MinerID) = ACTIVE_HASHING
  EFFECTS:
    # CR2: the verifying miner REMAINS in ACTIVE_HASHING and CONTINUES hashing while verifying;
    # it stays included in H_active(t). NO VERIFYING miner state is introduced.
    # I11: no termination of hashing without target verification.
    CONTINUE hashing throughout verification                    # verifier stays in H_active(t)
    BEGIN accruing E_verification for verifying_MinerID
        (separate coordination/verification energy increment, added ON TOP OF the ACTIVE_HASHING
         residency energy and NOT double-counted -- t_hash still counts the full active duration)
    step1 <- (certificate.RoundID = RoundID_current)            # I3
    step2 <- (certificate.TemplateID = TemplateID_committed)    # I3-style binding
    step3 <- (certificate.AssignmentID identifies a VALID CURRENT assignment held by
              certificate.MinerID)
    step4 <- (certificate.nonce in range(assignment(certificate.AssignmentID)))   # I2
    step5 <- (certificate.candidate_hash is the modeled digest of TemplateID and nonce AND
              satisfies certificate.target under fixed D)        # target verification (I11)
    step6 <- (certificate.signature/authentication is valid for certificate.MinerID)
    ADD the incremental verification cost to E_verification
    IF step1 AND step2 AND step3 AND step4 AND step5 AND step6:
      MARK certificate VERIFIED
      # Only AFTER ALL certificate-validation steps pass may the verifier leave ACTIVE_HASHING.
      TRANSITION miner_state(verifying_MinerID) -> EXHAUSTED_PENDING
      RETURN VERIFIED
    ELSE:
      RECORD false_early_stop_rejected(certificate)
      # CR2: a failed certificate produces NO hashing-state transition; verifier stays ACTIVE_HASHING.
      DO NOT terminate hashing; NO state transition              # I11 upheld
      RETURN REJECTED
  RETURNS: VERIFIED | REJECTED
```

## 17. Valid block acceptance

```
PROCEDURE ValidBlockAccept
  INPUTS: RoundContext, candidate_solution = (RoundID, TemplateID, AssignmentID, MinerID,
          nonce, candidate_hash, target)
  PRECONDITIONS: round_state in {HASHING, SECURITY_RECOVERY}
  EFFECTS:
    A <- assignment(candidate_solution.AssignmentID) of candidate_solution.MinerID
    ASSERT A is VALID and CURRENT
    ASSERT candidate_solution.nonce in range(A)                 # I2
    ASSERT candidate_solution.RoundID = RoundID_current         # I3
    ASSERT candidate_solution.TemplateID = TemplateID_committed # I3
    target_ok <- target verification of nonce under TemplateID and fixed D, yielding
                 candidate_hash that satisfies target
                 (modeled progress-verification abstraction)    # I11-consistent
    IF NOT target_ok:
      RETURN rejected
    # CR6: competing valid solutions use NETWORK-ARRIVAL semantics.
    # The global-oracle rule "smallest (TemplateID, nonce, MinerID)" is REMOVED as the primary
    # accepted-solution rule.
    SET arrival_time <- reproducible propagation/arrival time of candidate_solution
                        (deterministic modeled propagation; reproducible)
    RECORD candidate_solution WITH arrival_time in the round's valid-solution set
    accepted <- the valid solution with the EARLIEST arrival_time
    IF two or more valid solutions share the EXACT SAME earliest arrival_time:
      # deterministic secondary rule used ONLY for exact arrival-time ties
      accepted <- among the tied solutions, the one with smallest candidate_hash,
                  then smallest MinerID
    FOR EACH other valid solution s in the round's valid-solution set, s != accepted:
      RECORD competing_valid(s)                                 # competing/stale proposals
    IF candidate_solution != accepted:
      RETURN not_selected
    RECORD accepted_block(accepted)
    TRANSITION round_state -> SOLUTION_PROPAGATION
    TRANSITION round_state -> ROUND_ACCEPTED
  RETURNS: accepted_block | rejected | not_selected
  NOTE: Local acceptance uses the earliest valid arrival; no chain-wide fork-choice proof is
        claimed.
```

## 18. Full-range exhaustion without solution

```
PROCEDURE FullRangeExhaustNoSolution
  INPUTS: RoundContext
  PRECONDITIONS: assignment_ledger shows the entire nonce_domain searched under the I8a
                 coverage partition AND no accepted_block
  EFFECTS:
    # CR4: reconcile using the I8a coverage partition; custody status (I8b) is NOT a coverage term.
    ASSERT searched measure = measure(nonce_domain)             # I8a reconciliation
    # CR5: the protocol-level exhaustion claim (reported_exhaustion) is distinct from simulator
    # ground truth (actual_exhaustion). No progress commitment proves that no valid solution
    # exists in the whole range.
    SET reported_exhaustion <- aggregate reported coverage of the nonce_domain
    IF simulation = adversarial:
      # ---- [SIMULATION SAMPLING] ----
      audit_selected <- [SIMULATION SAMPLING] audit_selection_model(nonce_domain)
      # ---- deterministic protocol logic ----
      IF audit_selected:
        audit_result <- compare(reported_exhaustion, actual_exhaustion(nonce_domain))
        claim_accepted_or_rejected <- (audit_result = consistent)
        IF NOT claim_accepted_or_rejected:
          RECORD false_exhaustion_detected(RoundID, TemplateID)
          RETURN CALL RoundAbort(RoundContext, reason=false_exhaustion_claim)
    TRANSITION round_state -> ROUND_EXHAUSTED
    RECORD zero_block_outcome(RoundID, TemplateID)              # retained (I14)
    MARK block-normalised metrics for this round as NA          # I15
    IF policy = continue_mining:
      RETURN CALL TemplateRefresh(RoundContext)
    ELSE:
      RETURN CALL RoundAbort(RoundContext, reason=exhausted_no_solution)
  RETURNS: disposition (refresh | abort)
```

## 19. Template refresh

```
PROCEDURE TemplateRefresh
  INPUTS: RoundContext
  PRECONDITIONS: round_state in {ROUND_EXHAUSTED, HASHING(systemic template disagreement)}
  EFFECTS:
    TRANSITION round_state -> TEMPLATE_REFRESH
    build new candidate_template
    RETURN CALL TemplateCommit(RoundContext, new candidate_template)  # yields new TemplateID
    # existing assignments are rebound to the new TemplateID via RangeAssign/RangeReassign
    ASSERT difficulty unchanged                                 # I12
  RETURNS: new TemplateID
  NOTE: Refresh is the ONLY sanctioned way mined content changes; it never mutates a committed
        template in place.
```

## 20. Round abort

```
PROCEDURE RoundAbort
  INPUTS: RoundContext, reason
  PRECONDITIONS: unrecoverable condition (e.g. coordinator failure, unrecoverable floor breach,
                 unresolved partition) OR policy-directed abort
  EFFECTS:
    RECORD round_abort(RoundID, TemplateID, reason)
    IF any breach_events exist: LEAVE them intact               # I16: never repaired
    finalise energy_ledger; ASSERT per-miner sums (I6) and network sum (I7);
        ASSERT durations reconcile to horizon T (I5)
    RETAIN zero-block/partial outcome in dataset                # I14; NA metrics per I15
    TRANSITION round_state -> ROUND_ABORTED
  RETURNS: abort_record
```

---

## Deterministic-vs-sampling summary

The ONLY `[SIMULATION SAMPLING]` steps in the entire specification are:

1. **ActiveHashing** — whether a modeled execution meets the fixed target `D`.
2. **ActiveHashRateUpdate** — the adversarial active-participation contribution
   `H_adversarial(t)`.
3. **WakeComplete** — the wake latency draw.
4. **RangeExhaust** and **FullRangeExhaustNoSolution** — the adversarial-path audit selection
   (`audit_selection_model`) that decides whether a `reported_exhaustion` claim is audited
   against simulator ground truth (`actual_exhaustion`). This is the modeled audit/detection
   abstraction of CR5; the comparison itself (`audit_result`, `claim_accepted_or_rejected`) is
   deterministic once the audit is selected.

Every other step is deterministic protocol logic. This separation is deliberate: it keeps the
protocol's decision logic reproducible and audit-checkable against `I1..I16`, while confining
all randomness to clearly labelled model draws that exist solely because Stage-1 evaluation is
a simulation and not a real deployment. None of the above is executable source.
