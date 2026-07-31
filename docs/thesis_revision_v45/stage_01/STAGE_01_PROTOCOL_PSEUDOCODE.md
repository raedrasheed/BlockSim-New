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
  - Invariants `I1..I17` are defined in `STAGE_01_INVARIANT_CATALOGUE.md`.
  - Progress evidence is a **modeled progress-verification abstraction**, never a
    cryptographic proof. **Target verification** (checking that one candidate solution's hash
    satisfies the fixed target) is DISTINCT from **progress verification** (modeling a miner's
    claimed range progress): target verification validates a single solution (I11); progress
    verification models claimed coverage adjudicated under I4/I8a. They are not one evidence type.
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
    # D2: activation ALWAYS passes through WAKING; NEVER REGISTERED/RESERVE -> ACTIVE_HASHING directly.
    # (1)-(2) create a PENDING assignment and bind it to the miner.
    CREATE assignment(MinerID, candidate_range, TemplateID, RoundID, lease_start, lease_expiry)
        WITH status = PENDING
    APPEND assignment to assignment_ledger                     # supports I8a
    # (3) REGISTERED -> WAKING (T3) or RESERVE -> WAKING (T4)
    TRANSITION miner_state(MinerID) -> WAKING
    # (4)-(6) wake accounting, I1/RoundID/TemplateID validation, and WAKING -> ACTIVE_HASHING (T5)
    #         are performed by WakeComplete.
    RETURN CALL WakeComplete(RoundContext, MinerID, candidate_range)
  RETURNS: assignment
  NOTE: A zero wake-latency experimental value is permitted later, but the WAKING state and its
        P_wake*t_wake + E_transition accounting path always exist (D2).
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
        certificate <- CALL EarlyStopGenerate(RoundContext, candidate_solution)
        # C6: do NOT accept the block here. Acceptance occurs later, ONLY at the modeled
        #     acceptance point (see ScheduleSolutionPropagation / BlockAcceptancePoint).
        #     ROUND_ACCEPTED is NEVER set at solution-discovery time.
        RETURN CALL ScheduleSolutionPropagation(RoundContext, candidate_solution, certificate,
                                                finder = MinerID)
      ADVANCE cursor
      DECREMENT step_budget
      PERIODICALLY CALL ProgressCommit(assignment, cursor)     # emits progress evidence
    IF cursor beyond range(assignment):
      # D3: actual completion -> record ground truth, then the reported claim, then adjudicate.
      CALL ActualRangeCompletion(RoundContext, assignment)
      CALL ReportedExhaustionClaim(RoundContext, assignment, MinerID)
      RETURN CALL ExhaustionAdjudicate(RoundContext, assignment, MinerID, mode)
  RETURNS: continuation marker (solution | exhausted | preempted)
```

## 6. Range exhaustion (D3: three separate procedures)

`RangeExhaust` is split into three procedures so that a false-exhaustion claim
(`actual_frontier < range_end`) is representable and testable. Ground truth, the reported
claim, and the adjudicated result are distinct layers (C3). None of these procedures involves
I11 — range exhaustion is governed by I4, I8a, and this adjudication model.

```
PROCEDURE ActualRangeCompletion
  INPUTS: RoundContext, assignment
  PRECONDITIONS: actual_frontier(assignment) = range_end
                 AND actual_positions_evaluated(assignment) = range_size
  EFFECTS:
    # D3-A: records simulator GROUND TRUTH ONLY. Touches neither reported nor accepted coverage.
    RECORD actual_frontier(assignment)            <- range_end
    RECORD actual_positions_evaluated(assignment) <- range_size
    RECORD actual_exhaustion(assignment)          <- (no valid solution encountered over the
                                                      actual evaluated sequence)
    RECORD actual_solution_positions(assignment)  <- true solution-bearing positions (if any)
  RETURNS: actual_completion_record
  NOTE: Ground truth is known to the simulator, never asserted by the protocol, and never sets
        accepted coverage.
```

```
PROCEDURE ReportedExhaustionClaim
  INPUTS: RoundContext, assignment, MinerID
  PRECONDITIONS: none                    # D3-B: callable at ANY time, INCLUDING actual_frontier < range_end
  EFFECTS:
    emit final ProgressCommit covering the claimed span         # updates reported_* only (C3)
    SET reported_frontier(assignment)   <- coverage the miner claims to have searched
    SET reported_exhaustion(assignment) <- miner's claim that range(assignment) is fully searched
    # MUST NOT update accepted coverage.
  RETURNS: reported_claim_record
  NOTE: A reported claim is never accepted coverage. False exhaustion is representable here
        (reported_exhaustion = true while actual_frontier < range_end) so that TV2/TV3 are testable.
```

```
PROCEDURE ExhaustionAdjudicate
  INPUTS: RoundContext, assignment, MinerID, mode (honest | adversarial)
  PRECONDITIONS: a ReportedExhaustionClaim exists for assignment
  EFFECTS:
    IF mode = honest AND actual_exhaustion(assignment) is TRUE:
      claim_accepted_or_rejected <- ACCEPTED                   # honest: exact ground-truth completion
    ELSE:                                                       # adversarial path
      # ---- [SIMULATION SAMPLING] ----
      audit_selected <- [SIMULATION SAMPLING] audit_selection_model(assignment)
      # ---- deterministic protocol logic ----
      IF audit_selected:
        audit_result <- compare(reported_exhaustion(assignment), actual_exhaustion(assignment))  # modeled audit, NOT a proof
        claim_accepted_or_rejected <- (audit_result = consistent)
      ELSE:
        # unaudited claim accepted ONLY where the modeled policy explicitly defines it;
        # recorded as MODELED acceptance, never actual proof.
        claim_accepted_or_rejected <- modeled_unaudited_acceptance_policy(assignment)
    # ACCEPTED: promote reported -> accepted coverage and close the range on PATH A
    IF claim_accepted_or_rejected = ACCEPTED:
      SET accepted_frontier(range(assignment)) <- range_end
      SET accepted_exhaustion(assignment)      <- TRUE
      SET accepted_searched(range(assignment)) <- full range     # I8a uses ACCEPTED coverage only (C3)
      SET coverage_state(range(assignment))    <- searched
      SET custody_status(range(assignment))    <- completed      # CR-B5: NOT reassignable under same TemplateID
      SET stop_reason(MinerID)                 <- RANGE_EXHAUSTED
      TRANSITION miner_state(MinerID) -> EXHAUSTED_PENDING       # PATH A only (I4)
    # REJECTED: do NOT mark searched/completed; do NOT enter EXHAUSTED_PENDING
    ELSE:
      RECORD false_exhaustion_detected(MinerID, assignment)      # progress/audit violation, NOT I11
      PRESERVE actual coverage (accepted_frontier unchanged; range NOT searched/completed)
      APPLY adversarial/failure response (RangeReassign of the accepted unsearched suffix,
            or RoundAbort per policy); miner remains ACTIVE_HASHING (no PATH-A transition)
  RETURNS: adjudication_record(claim_accepted_or_rejected)
  NOTE: I11 is NOT involved. EXHAUSTED_PENDING is entered ONLY on ACCEPTED exhaustion;
        coverage_state = searched is set ONLY from ACCEPTED coverage (C2/C3). A reported claim or
        progress commitment NEVER proves that no valid solution exists in the whole range;
        exhaustion findings are modeled, not proven.
```

## 7. Transition to low-power listening

```
PROCEDURE EnterLowPowerListen
  INPUTS: RoundContext, MinerID, stop_reason
  PRECONDITIONS: stop_reason in {RANGE_EXHAUSTED, ASSIGNMENT_REVOKED, VALID_SOLUTION_VERIFIED,
                 ROUND_ACCEPTED, ROUND_ABORTED}                # I4: every entry records a reason
  EFFECTS:
    # C1: reason-specific disposition. There is NO generic "release held range to pool" step.
    SWITCH stop_reason:

      CASE RANGE_EXHAUSTED:                                    # PATH A
        ASSERT miner_state(MinerID) = EXHAUSTED_PENDING
        ASSERT accepted_exhaustion(assignment) = TRUE          # accepted exhaustion accounting exists
        ASSERT coverage_state(range) = searched AND custody_status(range) = completed
        CLOSE the assignment
        # do NOT release or reassign any part of the completed range

      CASE ASSIGNMENT_REVOKED:
        ASSERT miner_state(MinerID) = ACTIVE_HASHING
        PRESERVE accepted searched prefix [range_start, accepted_frontier]
        SET suffix <- accepted unsearched suffix [accepted_frontier + 1, range_end]
        MARK suffix as inactive_unsearched / reassignable      # only the accepted unsearched suffix (C4)
        CLOSE/SUPERSEDE the assignment

      CASE VALID_SOLUTION_VERIFIED:                            # PATH B
        ASSERT miner_state(MinerID) = ACTIVE_HASHING
        ASSERT the honoured early-stop certificate passed I11
        PAUSE the assignment; retain actual_frontier AND accepted_frontier
        # do NOT change coverage to searched; do NOT release the assignment

      CASE ROUND_ACCEPTED OR ROUND_ABORTED:
        CLOSE the assignment because the round ended
        # do NOT mark the range exhausted; do NOT reassign it under the closed TemplateID

    RECORD stop_reason(MinerID) <- stop_reason                 # I4
    TRANSITION miner_state(MinerID) -> LOW_POWER_LISTEN
    BEGIN accumulating t_listen at P_listen                    # supports I6; not active rate
  RETURNS: listen_record(MinerID, stop_reason)
  NOTE: EXHAUSTED_PENDING is the source ONLY for RANGE_EXHAUSTED; the other four reasons enter
        LOW_POWER_LISTEN directly from ACTIVE_HASHING (or on round closure) and never pass
        through EXHAUSTED_PENDING (CR-B1/CR-B2, I4).
```

## 8. Active-hash-rate update

```
PROCEDURE ActiveHashRateUpdate
  INPUTS: RoundContext, time t
  PRECONDITIONS: none
  EFFECTS:
    # ---- [SIMULATION SAMPLING] ----
    # CR-B6: the adversarial-behavior model decides WHICH adversarial miners continue in
    # ACTIVE_HASHING at t. This draw sets miner STATES only -- it does NOT produce a hash-rate
    # total. It is the ONLY randomness in this procedure.
    adversarial_active_set <- [SIMULATION SAMPLING] adversarial_participation_model(t)
    APPLY adversarial_active_set to the ACTIVE_HASHING census   # which adversarial miners are active at t
    # ---- deterministic protocol logic ----
    # CR-B6: after states are fixed, all three quantities are computed DETERMINISTICALLY from the
    # active-state census. H_adversarial is NEVER sampled independently after H_active (I17).
    SET H_honest(t)      <- SUM over honest miners in ACTIVE_HASHING of their modeled hash rate
    SET H_adversarial(t) <- SUM over adversarial miners in ACTIVE_HASHING of their modeled hash rate
    SET H_active(t)      <- H_honest(t) + H_adversarial(t)      # exact census decomposition (I17)
    IF H_active(t) = 0:
      SET q_adv(t) <- NA                                        # I17: undefined at zero active hash rate
      # C7: ActiveHashRateUpdate does NOT record breaches or trigger recovery -- it only computes.
      #     SecurityFloorEvaluate alone records the active/honest-floor breaches when H_active = 0.
    ELSE:
      SET q_adv(t) <- H_adversarial(t) / H_active(t)
    RECORD (H_active(t), H_honest(t), H_adversarial(t), q_adv(t))   # values only; no breach/recovery here
  RETURNS: (H_active(t), H_honest(t), H_adversarial(t), q_adv(t))
  NOTE: Only ACTIVE_HASHING contributes to active hash rate; LOW_POWER_LISTEN, WAKING,
        RESERVE, OFFLINE contribute nothing to it. The simulation draws only WHICH adversarial
        miners are active; H_honest(t), H_adversarial(t), and H_active(t) then follow
        deterministically from the census (I17).
```

## 9. Security-floor evaluation

```
PROCEDURE SecurityFloorEvaluate
  INPUTS: RoundContext, (H_active(t), H_honest(t), q_adv(t)), floor_state
  PRECONDITIONS: none
  EFFECTS:
    breach <- FALSE
    # C7: this procedure ALONE records breaches and triggers recovery. RECORD_ONCE suppresses
    #     duplicate breach records for the same (event, threshold, t).
    IF H_active(t) == 0:
      # zero active hash rate: q_adv(t) = NA. Record active- AND honest-floor breaches; do NOT
      # compare NA with maximum_adversarial_share (NA is never numerically compared).
      RECORD_ONCE breach_event(active_floor, t)                # I16
      RECORD_ONCE breach_event(honest_floor, t)                # I16
      breach <- TRUE
    ELSE:
      IF H_active(t) < floor_state.active_floor:
        RECORD_ONCE breach_event(active_floor, t)              # I16
        breach <- TRUE
      IF H_honest(t) < floor_state.honest_floor:
        RECORD_ONCE breach_event(honest_floor, t)             # I16
        breach <- TRUE
      IF q_adv(t) != NA AND q_adv(t) > floor_state.q_adv_threshold:
        RECORD_ONCE breach_event(adversarial_share, t)        # I16
        breach <- TRUE
    IF breach:
      TRANSITION round_state -> SECURITY_RECOVERY
  RETURNS: breach
  NOTE: I17 (`H_active = H_honest + H_adversarial`) holds exactly at every event-update time.
        ActiveHashRateUpdate computes the quantities only; this procedure is the SOLE owner of
        breach recording and recovery. `q_adv = NA` is never numerically compared. Recovery
        actions are logged separately and never overwrite breach_event records (I16).
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
      # D2: validate the bound PENDING assignment; do NOT recurse into RangeAssign.
      VALIDATE target_range against I1, current RoundID, and committed TemplateID   # re-checks I1/I10/I3
      ACTIVATE the bound assignment: status PENDING -> CURRENT
      TRANSITION miner_state(MinerID) -> ACTIVE_HASHING                 # T5
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
    INVALIDATE assignment (holder's assignment no longer CURRENT)   # stale mining -> I2 reject
    IF holder wishes to continue AND policy allows renewal:
      RENEW lease_expiry <- t + lease_duration
      RETURN renewed
    # C4: reassign ONLY the accepted unsearched suffix, never the searched prefix.
    IF accepted_frontier(range(assignment)) = range_end:
      RETURN released_nothing_to_reassign                          # range complete; nothing unsearched
    IF no accepted positions exist for range(assignment):
      SET reassignable_suffix <- whole range(assignment)          # [range_start, range_end]
    ELSE:
      SET reassignable_suffix <- [accepted_frontier(range(assignment)) + 1, range_end]
    MARK reassignable_suffix as inactive_unsearched / reassignable  # supports I8a (unsearched only)
    RETURN CALL RangeReassign(RoundContext, reassignable_suffix,
                              reason=lease_expiry, from_miner=holder)
  RETURNS: lease_disposition (renewed | released | released_nothing_to_reassign)
```

## 13. Range reassignment

```
PROCEDURE RangeReassign
  INPUTS: RoundContext, unsearched_suffix, reason, from_miner
  PRECONDITIONS: # C4: the caller passes the EXACT accepted unsearched suffix, not a full range:
                 unsearched_suffix = [accepted_frontier(source) + 1, range_end(source)]
                   OR (no accepted positions exist AND unsearched_suffix = whole source range);
                 # CR-B5: exhaustion is NOT a reassignment reason; permitted reasons are exactly:
                 reason in {lease_expiry, abandonment, revocation, departure, conflict, security_recovery};
                 custody_status(unsearched_suffix) != completed;   # a completed range is NOT reassignable
                 coverage_state(unsearched_suffix) != searched     # no searched prefix is included
  EFFECTS:
    # CR-B5 + C4: only the accepted unsearched suffix is reassigned; a searched prefix or a
    # completed range is NEVER reassignable.
    ASSERT custody_status(unsearched_suffix) != completed
    ASSERT coverage_state(unsearched_suffix) != searched
    ASSERT unsearched_suffix contains no accepted searched position   # C4: suffix only
    SELECT to_miner from {RESERVE, REGISTERED} miners (or via ReserveActivate)
    FOR EACH active_assignment A in assignment_ledger:
      ASSERT unsearched_suffix INTERSECT range(A) = EMPTY             # I1 preserved
    prior_pc <- last accepted ProgressCommit covering the source range   # de-dup key material (I13)
    CREATE assignment(to_miner, unsearched_suffix, TemplateID, RoundID, new lease window)
        WITH status = PENDING
    # D2: to_miner activation passes through WAKING; never REGISTERED/RESERVE -> ACTIVE_HASHING directly.
    TRANSITION miner_state(to_miner) -> WAKING
    CALL WakeComplete(RoundContext, to_miner, unsearched_suffix)     # validates I1/RoundID/TemplateID; T5 -> ACTIVE_HASHING
    APPEND reassignment record
        (unsearched_suffix, from_miner, to_miner, reason, timestamp, prior_pc)   # I9 complete provenance
    # CR4/C3: coverage uses I8a with ACCEPTED coverage; custody/provenance is tracked SEPARATELY as I8b.
    UPDATE assignment_ledger so the coverage partition still holds (I8a):
        accepted_searched + active_unsearched + inactive_unsearched = assigned_domain
    # I8b custody/lineage status is orthogonal and is NEVER an additive coverage term.
    SET custody_status(unsearched_suffix) <- reassigned   # in {original, renewed, reassigned, revoked, expired, abandoned, completed}
    # The reassigned suffix retains an INDEPENDENT coverage state
    # (accepted_searched / active_unsearched / inactive_unsearched).
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
    UPDATE reported_searched(range(assignment)) <- reported_frontier   # C3: REPORTED layer ONLY
    # C3: ProgressCommit MUST NOT update the normative I8a accepted_searched measure. I8a uses
    #     ACCEPTED coverage only; reported coverage is promoted to accepted ONLY by adjudication
    #     (RangeExhaust honest-completion / audit), never directly by a progress commitment.
  RETURNS: progress_commitment
  NOTE: This is a MODELED PROGRESS-VERIFICATION ABSTRACTION, NOT a cryptographic proof of
        range exhaustion. A progress commitment states "I claim to have searched up to this
        frontier"; it NEVER proves that no valid solution exists in the whole range, and it can
        never by itself close a range as searched or stop hashing. Closing a range as searched
        requires adjudicated (accepted) exhaustion (C2); stopping early requires a verified
        solution certificate (I11). These are distinct mechanisms.
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
      # CR-B1/CR-B2 (PATH B): only AFTER ALL certificate-validation steps pass, the verifier
      # transitions ACTIVE_HASHING -> LOW_POWER_LISTEN DIRECTLY. It does NOT pass through
      # EXHAUSTED_PENDING (which is exclusive to range exhaustion, PATH A / I4).
      PAUSE assignment(verifying_MinerID)                        # retain actual_frontier
      # The paused assignment is NOT closed: do NOT set coverage_state = searched and do NOT set
      # custody_status = completed; no unsearched positions are credited as searched.
      SET stop_reason <- VALID_SOLUTION_VERIFIED                 # recorded per I4
      TRANSITION miner_state(verifying_MinerID) -> LOW_POWER_LISTEN
      RETURN VERIFIED
    ELSE:
      RECORD false_early_stop_rejected(certificate)
      # CR-B2: a failed or partial certificate produces NO hashing-state transition; the verifier
      # stays in ACTIVE_HASHING and keeps hashing.
      DO NOT terminate hashing; NO state transition              # I11 upheld
      RETURN REJECTED
  RETURNS: VERIFIED | REJECTED
  NOTE: On PATH B the assignment is PAUSED (actual_frontier retained), never marked searched or
        exhausted. If the full block is later rejected, unavailable, or times out, the miner
        resumes via ResumeFromPause (LOW_POWER_LISTEN -> WAKING -> ACTIVE_HASHING).
```

## 16a. Resume after a paused (PATH B) stop

```
PROCEDURE ResumeFromPause
  INPUTS: RoundContext, MinerID, trigger
  PRECONDITIONS: miner_state(MinerID) = LOW_POWER_LISTEN with recorded stop_reason = VALID_SOLUTION_VERIFIED;
                 trigger in {BLOCK_REJECTED, BLOCK_UNAVAILABLE, PROPAGATION_TIMEOUT};
                 the miner's assignment is PAUSED (actual_frontier retained), NOT searched/exhausted
  EFFECTS:
    # CR-B1: a paused PATH B assignment resumes; it was never marked searched or completed, so no
    # coverage was falsely credited. The miner wakes and continues from where it paused.
    TRANSITION miner_state(MinerID) -> WAKING                   # wake/transition energy accounted below
    # ---- [SIMULATION SAMPLING] ----
    wake_latency <- [SIMULATION SAMPLING] wake_latency_model(MinerID)
    # ---- deterministic protocol logic ----
    ACCUMULATE t_wake at P_wake for wake_latency; ADD E_transition   # supports I5, I6 (wake + transition energy)
    SET cursor <- retained actual_frontier of the paused assignment  # resume exactly where it paused
    RESTORE paused_assignment status -> CURRENT from the retained actual_frontier   # D5: assignment CURRENT again
    TRANSITION miner_state(MinerID) -> ACTIVE_HASHING                 # T5
    CALL ActiveHashRateUpdate(RoundContext, now)                     # D5: recompute H_active/H_honest/H_adversarial/q_adv
    RETURN CALL ActiveHashing(RoundContext, paused_assignment, step_budget)   # continues from actual_frontier
  RETURNS: resume_record(MinerID, resumed_from = actual_frontier)
  NOTE: Resume applies ONLY to PATH B pauses (stop_reason = VALID_SOLUTION_VERIFIED). A PATH A
        exhausted range (coverage_state = searched, custody_status = completed) is NOT resumable.
        If instead the full block is ACCEPTED, the round closes (ROUND_ACCEPTED) and the paused
        assignment closes on round closure -- NOT by exhaustion.
```

## 16b. Event-ordered solution propagation (C6) and finder self-validation (D4)

```
PROCEDURE SelfValidateFoundSolution
  INPUTS: RoundContext, candidate_solution, finder
  PRECONDITIONS: miner_state(finder) = ACTIVE_HASHING
  EFFECTS:
    # D4: explicit I11-equivalent self-validation the finder MUST pass before it may stop.
    BEGIN accruing E_verification for finder (separate increment, on top of t_hash, not double-counted)
    step1 <- (candidate_solution.RoundID = RoundID_current)                        # I3
    step2 <- (candidate_solution.TemplateID = TemplateID_committed)                # I3
    step3 <- (candidate_solution.AssignmentID identifies finder's VALID CURRENT assignment)
    step4 <- (candidate_solution.nonce in range(assignment(candidate_solution.AssignmentID)))   # I2
    step5 <- (candidate_solution.candidate_hash is the modeled digest of TemplateID and nonce AND
              satisfies candidate_solution.target under fixed D)                    # target verification (I11)
    step6 <- (candidate_solution.signature/authentication is valid for finder)
    ADD the incremental verification cost to E_verification
  RETURNS: (step1 AND step2 AND step3 AND step4 AND step5 AND step6)
  NOTE: I11 fields exactly. Certificate generation does not by itself satisfy these checks; the
        finder may stop only after this self-validation passes (D4).
```

```
PROCEDURE ScheduleSolutionPropagation
  INPUTS: RoundContext, candidate_solution, certificate, finder
  PRECONDITIONS: round_state in {HASHING, SECURITY_RECOVERY};
                 certificate was produced by EarlyStopGenerate from a found valid solution
  EFFECTS:
    # D4: the finder MUST self-validate (I11-equivalent) BEFORE it may stop or propagate.
    #     Certificate generation does NOT automatically satisfy the I11 checks.
    self_ok <- CALL SelfValidateFoundSolution(RoundContext, candidate_solution, finder)
    IF NOT self_ok:
      RECORD invalid_self_solution(finder, candidate_solution)   # finder does NOT stop; stays ACTIVE_HASHING
      RETURN not_scheduled
    # C6: event-ordered propagation. NO block acceptance occurs here; ROUND_ACCEPTED is not set.
    # (3) schedule per-recipient certificate-arrival events using modeled propagation delays.
    FOR EACH recipient r in current miners, r != finder:
      cert_delay(r) <- deterministic modeled propagation delay(finder -> r)   # reproducible
      SCHEDULE event CertificateArrival(RoundContext, r, certificate) AT now + cert_delay(r)
    # (4) schedule the full-block propagation/arrival event toward the modeled acceptance point.
    block_delay <- deterministic modeled propagation delay(finder -> acceptance_point)  # reproducible
    SCHEDULE event BlockAcceptancePoint(RoundContext, candidate_solution) AT now + block_delay
    # (5) the finder ceases hashing under the solution-found rule; its assignment is PAUSED
    #     (PATH B, resumable), and block-propagation energy is accounted (P_hash residency ends;
    #     E_coordination for propagation). The finder does NOT pass through EXHAUSTED_PENDING.
    CALL EnterLowPowerListen(RoundContext, finder, stop_reason = VALID_SOLUTION_VERIFIED)
  RETURNS: scheduled_marker
  NOTE: The discrete-event queue orders arrivals; no global set of future solutions is consulted.
        Do NOT call ValidBlockAccept here.
```

## 16c. Certificate arrival at a recipient (C6)

```
PROCEDURE CertificateArrival
  INPUTS: RoundContext, recipient r, certificate
  PRECONDITIONS: this is the scheduled certificate-arrival event for r
  EFFECTS:
    # (6) the recipient stays ACTIVE_HASHING until its certificate-arrival event fully validates.
    IF miner_state(r) = ACTIVE_HASHING:
      result <- CALL EarlyStopVerify(RoundContext, certificate, verifying_MinerID = r)
      # (7) on VERIFIED, EarlyStopVerify pauses r into LOW_POWER_LISTEN
      #     (stop_reason = VALID_SOLUTION_VERIFIED, assignment PAUSED). On REJECTED, r stays
      #     ACTIVE_HASHING and keeps hashing (I11); no transition.
    ELSE:
      IGNORE                                                     # r not currently hashing
  RETURNS: verify_result
```

## 16d. Block acceptance point (C6)

```
PROCEDURE BlockAcceptancePoint
  INPUTS: RoundContext, candidate_solution, outcome
  PRECONDITIONS: this is the scheduled full-block arrival event at the MODELED ACCEPTANCE POINT;
                 outcome in {ACCEPTED_CANDIDATE, REJECTED, BLOCK_UNAVAILABLE, PROPAGATION_TIMEOUT}
  EFFECTS:
    # C6: the modeled acceptance point is EITHER a designated coordinator/validator OR a clearly
    #     identified canonical local view (RoundContext.acceptance_point_policy).
    IF outcome = ACCEPTED_CANDIDATE:
      # D6: batch EXACT-same-timestamp candidates BEFORE accepting; do NOT accept the first event
      #     immediately when other candidate events share the exact acceptance timestamp.
      RETURN CALL AcceptanceTimestampBatch(RoundContext, acceptance_timestamp = now)
    ELSE:
      # D5: REJECTED / BLOCK_UNAVAILABLE / PROPAGATION_TIMEOUT -> resume paused miners.
      # (1) keep/return the round to HASHING unless a floor breach requires SECURITY_RECOVERY.
      breach <- CALL SecurityFloorEvaluate(RoundContext, latest (H_active, H_honest, q_adv), floor_state)
      IF NOT breach: ENSURE round_state = HASHING
      # (2)-(3) enumerate every PAUSED VALID_SOLUTION_VERIFIED miner and schedule its resume.
      FOR EACH miner M with a PAUSED assignment AND stop_reason(M) = VALID_SOLUTION_VERIFIED:
        SCHEDULE event ResumeFromPause(RoundContext, M, trigger = outcome)
      # (4)-(6) listening/wake/transition/resumed-hashing energy accounting, assignment-CURRENT
      #         restore, and H_active/H_honest/H_adversarial/q_adv recompute occur inside
      #         ResumeFromPause (which calls ActiveHashRateUpdate).
      RETURN resume_scheduled
  RETURNS: accepted_block | resume_scheduled | no_valid_candidate
  NOTE: A strictly-earlier full-block arrival wins by discrete-event queue order; EXACT-timestamp
        ties are arbitrated by AcceptanceTimestampBatch. No event inspects unknown future timestamps.
```

## 16e. Same-timestamp acceptance arbitration (D6)

```
PROCEDURE ValidateCandidate
  INPUTS: RoundContext, candidate_solution
  PRECONDITIONS: none
  EFFECTS:
    A <- assignment(candidate_solution.AssignmentID) of candidate_solution.MinerID
    ok <- (A is VALID and CURRENT)
          AND (candidate_solution.nonce in range(A))                # I2
          AND (candidate_solution.RoundID = RoundID_current)        # I3
          AND (candidate_solution.TemplateID = TemplateID_committed)# I3
          AND (candidate_solution.candidate_hash is the modeled digest of TemplateID and nonce
               AND satisfies candidate_solution.target under fixed D)   # target verification (modeled, I11-consistent)
          AND (candidate_solution.signature/authentication valid for candidate_solution.MinerID)
    IF NOT ok: RECORD invalid_block(candidate_solution)
  RETURNS: ok
```

```
PROCEDURE AcceptanceTimestampBatch
  INPUTS: RoundContext, acceptance_timestamp
  PRECONDITIONS: at least one BlockAcceptancePoint(outcome = ACCEPTED_CANDIDATE) event fires at
                 acceptance_timestamp for this acceptance point
  EFFECTS:
    # D6: (1) gather ALL same-acceptance-point candidate events with EXACTLY this timestamp.
    batch <- all ACCEPTED_CANDIDATE BlockAcceptancePoint candidates at this acceptance point with
             timestamp = acceptance_timestamp
    # (2)-(3) validate every candidate; discard invalid.
    valid <- empty
    FOR EACH candidate c in batch:
      IF CALL ValidateCandidate(RoundContext, c): APPEND c to valid
    IF valid is empty:
      RETURN no_valid_candidate                                     # round stays HASHING; nothing accepted
    # (4) among valid candidates choose smallest candidate_hash, then smallest MinerID.
    winner <- argmin over valid of (candidate_hash, then MinerID)
    # (5) record all others as competing/stale.
    FOR EACH c in valid, c != winner: RECORD competing_valid(c)
    # (6) ONLY AFTER arbitration finishes: accept + close (no round closure occurs before this).
    RETURN CALL ValidBlockAccept(RoundContext, winner)
  RETURNS: accepted_block | not_selected | no_valid_candidate
  NOTE: For DIFFERENT timestamps the earliest timestamp wins by discrete-event queue order; this
        procedure arbitrates ONLY exact-timestamp ties. No event inspects unknown future
        timestamps; no round closure occurs before same-timestamp arbitration completes.
```

## 17. Valid block acceptance

```
PROCEDURE ValidBlockAccept
  INPUTS: RoundContext, winner_solution
  PRECONDITIONS: invoked ONLY from AcceptanceTimestampBatch after arbitration (D6);
                 winner_solution already validated by ValidateCandidate and chosen as the batch winner;
                 round_state in {HASHING, SECURITY_RECOVERY, SOLUTION_PROPAGATION}
  EFFECTS:
    IF a block has ALREADY been accepted this round:
      RECORD competing_valid(winner_solution)                    # a strictly-earlier timestamp already won
      RETURN not_selected
    RECORD accepted_block(winner_solution)
    TRANSITION round_state -> SOLUTION_PROPAGATION
    TRANSITION round_state -> ROUND_ACCEPTED
    # D7: centralised round closure (the SINGLE closure path).
    CALL CloseRoundAssignments(RoundContext, disposition = ROUND_ACCEPTED, stop_reason = ROUND_ACCEPTED)
  RETURNS: accepted_block | not_selected
  NOTE: Earliest arrival is the discrete-event queue order (strictly-earlier timestamps win before
        this batch); exact-timestamp ties are arbitrated in AcceptanceTimestampBatch; per-candidate
        validation is done by ValidateCandidate. No chain-wide fork-choice proof is claimed.
```

## 17a. Centralised round closure (D7)

```
PROCEDURE CloseRoundAssignments
  INPUTS: RoundContext, disposition (ROUND_ACCEPTED | ROUND_ABORTED), stop_reason
  PRECONDITIONS: disposition in {ROUND_ACCEPTED, ROUND_ABORTED}; stop_reason matches disposition
  EFFECTS:
    # D7: the SINGLE round-closure path. Enumerate ALL open assignments regardless of holder state
    #     (ACTIVE_HASHING, EXHAUSTED_PENDING, LOW_POWER_LISTEN, WAKING, OFFLINE).
    FOR EACH open assignment X under the closing RoundID/TemplateID:
      PRESERVE coverage_state(X) and provenance/custody history   # do NOT mark unfinished ranges exhausted
      # do NOT reassign X under the closed TemplateID
      IF miner_state(holder(X)) = ACTIVE_HASHING:
        CALL EnterLowPowerListen(RoundContext, holder(X), stop_reason = stop_reason)   # wires the 5th disposition
      ELSE:
        RECORD stop_reason(holder(X)) <- stop_reason
        CLOSE X as round-ended; update miner_state(holder(X)) consistently
        (a paused/exhausted/waking holder is NOT resumed; a WAKING holder's pending activation is cancelled)
    # cancel pending events belonging to the closed round
    CANCEL all pending wake / resume / certificate-arrival / BlockAcceptancePoint events for RoundID
    RECORD round_closure(RoundID, TemplateID, disposition)
    finalise state durations and energy to the EXACT closure time  # I5, I6, I7
  RETURNS: closure_record
  NOTE: This is the ONLY round-closure path. ValidBlockAccept calls it with ROUND_ACCEPTED;
        RoundAbort calls it with ROUND_ABORTED. The ROUND_ABORTED disposition wires the fifth
        EnterLowPowerListen reason into an actual path. No range is marked exhausted by closure,
        and nothing is reassigned under the closed TemplateID.
```

## 18. Full-range exhaustion without solution

```
PROCEDURE FullRangeExhaustNoSolution
  INPUTS: RoundContext
  PRECONDITIONS: # C9: the entire assigned domain must be ACCEPTED searched coverage (I8a);
                 # reported coverage alone is INSUFFICIENT.
                 accepted_searched measure = measure(nonce_domain)
                 AND active_unsearched measure = 0 AND inactive_unsearched measure = 0
                 AND no accepted_block
  EFFECTS:
    # CR4/C3/C9: reconcile using the I8a ACCEPTED coverage partition; custody status (I8b) is
    # NOT a coverage term. Do NOT enter ROUND_EXHAUSTED while any active_unsearched or
    # inactive_unsearched coverage remains.
    ASSERT accepted_searched measure = measure(nonce_domain)    # I8a: accepted coverage only
    ASSERT active_unsearched measure = 0 AND inactive_unsearched measure = 0
    # C9: every accepted coverage claim must have a defined adjudication outcome. For adversarial
    #     runs, an unaudited claim may be accepted ONLY where the modeled policy explicitly defines
    #     it, recorded as MODELED acceptance (not actual proof).
    IF simulation = adversarial:
      FOR EACH range r contributing to accepted_searched:
        ASSERT adjudication_outcome(r) is DEFINED               # audited, or modeled-policy accepted
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
    # D8: correct round-state sequencing so TemplateCommit runs from TEMPLATE_COMMITMENT.
    TRANSITION round_state -> TEMPLATE_REFRESH                  # from ROUND_EXHAUSTED or HASHING
    # C5: a new TemplateID is a NEW search domain, not a reassignment-lineage event.
    # (1) close all assignments under the OLD TemplateID (template-scoped; the round continues)
    FOR EACH assignment X under the old TemplateID:
      CLOSE X                                                   # closed because the template changed
    # (2) preserve their historical coverage/provenance records (do not delete the ledger history)
    PRESERVE historical coverage_state / custody_status / reassignment records of old assignments
    # (3) build the new immutable template WHILE in TEMPLATE_REFRESH
    build new candidate_template
    # D8: move TEMPLATE_REFRESH -> TEMPLATE_COMMITMENT BEFORE calling TemplateCommit (its precondition)
    TRANSITION round_state -> TEMPLATE_COMMITMENT
    new_TemplateID <- CALL TemplateCommit(RoundContext, new candidate_template)   # requires TEMPLATE_COMMITMENT;
                                                                                  # TemplateCommit transitions -> ASSIGNMENT
    # (4) create NEW ORIGINAL assignments over the new candidate-identity domain (round_state = ASSIGNMENT)
    FOR EACH participating miner m:
      CREATE assignment(m, fresh_range(m), new_TemplateID, RoundID, new lease window) WITH status = PENDING
      SET custody_status(fresh_range(m)) <- original
      SET previous_assignment_reference <- null                 # C5: not a reassignment lineage
      # D2: activation passes through WAKING; never REGISTERED/RESERVE -> ACTIVE_HASHING directly.
      TRANSITION miner_state(m) -> WAKING
      CALL WakeComplete(RoundContext, m, fresh_range(m))        # validates I1/RoundID/TemplateID; T5 -> ACTIVE_HASHING
      # do NOT call RangeReassign for old ranges; do NOT rebind old assignments to new_TemplateID
    ASSERT difficulty unchanged                                 # I12
  RETURNS: new_TemplateID
  NOTE: Refresh is the ONLY sanctioned way mined content changes; it never mutates a committed
        template in place, and it NEVER reassigns a completed old range -- old assignments are
        closed and new ORIGINAL assignments are created over the new domain (C5).
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
    # D7: centralised closure of ALL open assignments and miner paths (wires the ROUND_ABORTED
    #     EnterLowPowerListen disposition; cancels pending wake/resume/certificate events).
    CALL CloseRoundAssignments(RoundContext, disposition = ROUND_ABORTED, stop_reason = ROUND_ABORTED)
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
2. **ActiveHashRateUpdate** — WHICH adversarial miners continue in `ACTIVE_HASHING` at `t` (the
   active-state census). `H_honest(t)`, `H_adversarial(t)`, and `H_active(t)` are then computed
   **deterministically** from that census; `H_adversarial(t)` is **never** sampled independently
   after `H_active(t)` (I17).
3. **WakeComplete** and **ResumeFromPause** — the wake latency draw.
4. **ExhaustionAdjudicate** and **FullRangeExhaustNoSolution** — the adversarial-path audit selection
   (`audit_selection_model`) that decides whether a `reported_exhaustion` claim is audited
   against simulator ground truth (`actual_exhaustion`). This is the modeled audit/detection
   abstraction of CR5; the comparison itself (`audit_result`, `claim_accepted_or_rejected`) is
   deterministic once the audit is selected.

Every other step is deterministic protocol logic. This separation is deliberate: it keeps the
protocol's decision logic reproducible and audit-checkable against `I1..I17`, while confining
all randomness to clearly labelled model draws that exist solely because Stage-1 evaluation is
a simulation and not a real deployment. None of the above is executable source.
