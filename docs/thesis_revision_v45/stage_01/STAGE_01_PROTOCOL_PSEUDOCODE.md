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
  PRECONDITIONS: miner_state = ACTIVE_HASHING; assignment VALID and CURRENT;
                 # E6: hashing is permitted while the round is HASHING, and it CONTINUES for
                 #     not-yet-paused miners during SOLUTION_PROPAGATION and SECURITY_RECOVERY.
                 round_state in {HASHING, SOLUTION_PROPAGATION, SECURITY_RECOVERY}
  EFFECTS:
    SET cursor <- next unsearched nonce in range(assignment)
    # E6: an unpaused miner keeps hashing after the FIRST valid found-solution moves the round to
    #     SOLUTION_PROPAGATION; it stops only when it pauses (PATH B), exhausts (PATH A), the round
    #     closes, or its step budget is spent.
    WHILE cursor within range(assignment)
          AND round_state in {HASHING, SOLUTION_PROPAGATION, SECURITY_RECOVERY}
          AND step_budget > 0:
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
        # E1: capture an IMMUTABLE eligibility snapshot at DISCOVERY time (assignment CURRENT now).
        snapshot <- CALL CreateSolutionEligibilitySnapshot(RoundContext, assignment, candidate_solution)
        # CR1/E2: the SIGNED early-stop certificate is generated ONLY here, from the found solution
        #         and its snapshot -- NEVER from coverage/frontier/claimed exhaustion.
        certificate <- CALL EarlyStopGenerate(RoundContext, candidate_solution, snapshot)
        # C6: do NOT accept the block here; acceptance occurs later ONLY at the modeled acceptance
        #     point. E6: entry to SOLUTION_PROPAGATION happens in ScheduleSolutionPropagation.
        RETURN CALL ScheduleSolutionPropagation(RoundContext, certificate, snapshot, finder = MinerID)
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
      SET entry_stop_reason(MinerID)           <- RANGE_EXHAUSTED   # why the miner left ACTIVE_HASHING (I4)
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

    RECORD entry_stop_reason(MinerID) <- stop_reason           # I4: why the miner left ACTIVE_HASHING
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
    ASSERT custody_status(candidate_range) != completed        # never activate over a completed range
    ASSERT coverage_state(candidate_range) != searched         # never over a searched prefix
    # E4: create and LEDGER a PENDING assignment and BIND it BEFORE waking; activation to CURRENT
    #     happens ONLY inside WakeComplete on a successful wake. This mirrors RangeAssign so a
    #     reserve activation can never reach ACTIVE_HASHING without a bound PENDING assignment.
    SET lease_start  <- now
    SET lease_expiry <- now + default_lease_duration
    CREATE assignment(reserve_miner, candidate_range, TemplateID, RoundID, lease_start, lease_expiry)
        WITH status = PENDING
    APPEND assignment to assignment_ledger                     # supports I8a
    SET custody_status(candidate_range) <- original            # a fresh reserve range, not a reassignment
    # D2: activation ALWAYS passes through WAKING; NEVER RESERVE -> ACTIVE_HASHING directly (T4 -> T5).
    TRANSITION miner_state(reserve_miner) -> WAKING            # T4; incurs wake latency/energy
    # (a) on success WakeComplete validates I1/RoundID/TemplateID and flips PENDING -> CURRENT (T5);
    # (b) on wake failure WakeComplete records reserve_wake_failure and moves the miner OFFLINE,
    #     leaving the PENDING assignment un-activated for the caller to release.
    activation <- CALL WakeComplete(RoundContext, reserve_miner, candidate_range)
    IF activation = activation_failure:
      # E4: never leave a bound-but-un-activated range as if it were held; release it cleanly.
      MARK candidate_range as inactive_unsearched / reassignable    # supports I8a (unsearched only)
      CLOSE the PENDING assignment as not-activated (custody_status <- abandoned)
      RETURN activation_failure
    RETURN activation
  RETURNS: activation_record | activation_failure
  NOTE: PENDING -> CURRENT occurs ONLY in WakeComplete on a successful wake (E4). A failed wake
        never yields a CURRENT assignment; the reserved range is released as inactive_unsearched.
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
  PRECONDITIONS: t >= lease_expiry(assignment)   # the lease window elapsed; renewal not yet decided
  EFFECTS:
    # E9: DECIDE renewal BEFORE invalidating anything. A renewed assignment is NEVER invalidated and
    #     is NEVER routed through RangeReassign or WAKING -- the holder keeps hashing the SAME range.
    IF miner_state(holder) = ACTIVE_HASHING AND holder wishes to continue AND policy allows renewal:
      # ---- RENEWAL (same holder, same range, stays CURRENT; no wake cycle; E5/E9) ----
      ASSERT custody_status(range(assignment)) != completed        # a completed range is not renewable
      # canonical lease renewal: mint a fresh AssignmentID + version bound to the SAME range/holder,
      # and extend the lease window in place. The range and all coverage/progress are preserved.
      SET assignment_version(assignment) <- assignment_version(assignment) + 1
      SET AssignmentID(assignment)       <- fresh AssignmentID bound to the SAME range and holder
      SET lease_start(assignment)        <- t
      SET lease_expiry(assignment)       <- t + lease_duration
      SET custody_status(range(assignment)) <- renewed            # I8b lineage only; coverage unchanged
      PRESERVE range(assignment), actual_frontier, accepted_frontier, reported_frontier, provenance
      KEEP status(assignment) = CURRENT                           # E9: never invalidated on renewal
      # miner_state(holder) stays ACTIVE_HASHING; NO WAKING and NO RangeReassign (E5/E9)
      RETURN renewed
    # ---- EXPIRY WITHOUT RENEWAL: the holder actually stopped -- ONLY NOW invalidate and reassign ----
    INVALIDATE assignment (holder's assignment no longer CURRENT)   # stale mining -> I2 reject
    IF miner_state(holder) = ACTIVE_HASHING:
      # the miner actually stopped: route it off ACTIVE_HASHING via the legal revocation edge (T27).
      CALL EnterLowPowerListen(RoundContext, holder, stop_reason = ASSIGNMENT_REVOKED)
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
  NOTE: Renewal preserves a valid CURRENT assignment on the SAME range with retained progress and
        provenance and requires NO wake cycle (E9); a renewal NEVER changes the range -- a
        changed-range replacement is a reassignment, never a renewal (E5). Only expiry WITHOUT
        renewal invalidates the assignment and reassigns the accepted unsearched suffix.
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
PROCEDURE CreateSolutionEligibilitySnapshot
  INPUTS: RoundContext, assignment, candidate_solution
  PRECONDITIONS: miner_state(candidate_solution.MinerID) = ACTIVE_HASHING;
                 assignment is VALID and CURRENT at discovery time
  EFFECTS:
    # E1: an IMMUTABLE snapshot of eligibility captured at DISCOVERY time. It is never mutated;
    #     later PAUSING of the assignment does not change it.
    CREATE snapshot CONTAINING EXACTLY:
        RoundID                       <- candidate_solution.RoundID
        TemplateID                    <- candidate_solution.TemplateID
        AssignmentID                  <- candidate_solution.AssignmentID
        assignment_version            <- current version of assignment
        MinerID                       <- candidate_solution.MinerID
        nonce                         <- candidate_solution.nonce
        discovery_time                <- now
        range_start                   <- range_start(assignment)
        range_end                     <- range_end(assignment)
        assignment_status_at_discovery<- CURRENT                          # REQUIRED = CURRENT
        candidate_hash                <- candidate_solution.candidate_hash
        target                        <- candidate_solution.target
    ASSERT assignment_status_at_discovery = CURRENT
    RECORD snapshot (immutable)
  RETURNS: snapshot

PROCEDURE EarlyStopGenerate
  INPUTS: RoundContext, found_solution = (RoundID, TemplateID, AssignmentID, MinerID,
          nonce, candidate_hash, target), snapshot
  PRECONDITIONS: round_state in {HASHING, SOLUTION_PROPAGATION, SECURITY_RECOVERY};
                 found_solution is a valid candidate solution discovered in the ACTIVE_HASHING path;
                 snapshot.assignment_status_at_discovery = CURRENT and snapshot binds found_solution
  EFFECTS:
    # CR1: generated ONLY from a found valid solution -- NEVER from coverage/frontier/exhaustion.
    ASSERT found_solution came from a found valid candidate solution
    ASSERT snapshot binds found_solution (same RoundID/TemplateID/AssignmentID/assignment_version/nonce)
    CREATE early_stop_certificate CONTAINING EXACTLY:
        RoundID                  <- found_solution.RoundID
        TemplateID               <- found_solution.TemplateID
        AssignmentID             <- found_solution.AssignmentID
        assignment_version       <- snapshot.assignment_version           # E1: bound version
        MinerID                  <- found_solution.MinerID
        nonce                    <- found_solution.nonce
        candidate_hash           <- found_solution.candidate_hash
        target                   <- found_solution.target
        snapshot_ref             <- snapshot                              # E1: immutable eligibility snapshot
        signature/authentication <- authenticate(found_solution.MinerID, all fields above incl snapshot_ref)
    RECORD early_stop_certificate (proposed, not yet honoured)
  RETURNS: early_stop_certificate
  NOTE: The certificate is a SIGNED object bound to the discovery-time snapshot (E1/E2).
        Validation (SelfValidateFoundSolution / EarlyStopVerify / ValidateCandidate) checks it
        against the SNAPSHOT, NOT against the finder's later (possibly PAUSED) assignment state.
        A progress commitment ("searched up to this frontier") is a separate mechanism.
```

## 16. Early-stop verification

```
PROCEDURE EarlyStopVerify
  INPUTS: RoundContext, certificate, snapshot, verifying_MinerID
  PRECONDITIONS: round_state in {HASHING, SOLUTION_PROPAGATION, SECURITY_RECOVERY};
                 miner_state(verifying_MinerID) = ACTIVE_HASHING
  EFFECTS:
    # CR2: the verifying miner REMAINS in ACTIVE_HASHING and CONTINUES hashing while verifying;
    #      it stays in H_active(t). NO VERIFYING state. E1/E2: validate the SIGNED certificate
    #      against the SNAPSHOT; do NOT require the finder's assignment to be CURRENT now.
    CONTINUE hashing throughout verification                    # verifier stays in H_active(t)
    BEGIN accruing E_verification for verifying_MinerID (separate increment, NOT double-counted)
    result <- CALL ValidateCandidate(RoundContext, certificate, snapshot)   # SAME canonical predicate (E2)
    ADD the incremental verification cost to E_verification
    IF result = ok:
      MARK certificate VERIFIED
      # PATH B: the recipient PAUSES ITS OWN assignment and enters LOW_POWER_LISTEN DIRECTLY
      # (via the canonical disposition); it does NOT pass through EXHAUSTED_PENDING.
      CALL EnterLowPowerListen(RoundContext, verifying_MinerID, stop_reason = VALID_SOLUTION_VERIFIED)
      RETURN VERIFIED
    ELSE:
      RECORD false_early_stop_rejected(certificate)
      DO NOT terminate hashing; NO state transition              # I11 upheld
      RETURN REJECTED
  RETURNS: VERIFIED | REJECTED
  NOTE: Validation is against the discovery snapshot (E1), so a finder's later PAUSED assignment
        does NOT invalidate an already-discovered solution. The recipient's OWN assignment is
        PAUSED on VERIFIED; if the full block is later rejected/unavailable/timed out, the miner
        resumes via ResumeFromPause.
```

## 16a. Resume after a paused (PATH B) stop

```
PROCEDURE ResumeFromPause
  INPUTS: RoundContext, MinerID, trigger
  PRECONDITIONS: miner_state(MinerID) = LOW_POWER_LISTEN with recorded entry_stop_reason = VALID_SOLUTION_VERIFIED;
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
  NOTE: Resume applies ONLY to PATH B pauses (entry_stop_reason = VALID_SOLUTION_VERIFIED). A PATH A
        exhausted range (coverage_state = searched, custody_status = completed) is NOT resumable.
        If instead the full block is ACCEPTED, the round closes (ROUND_ACCEPTED) and the paused
        assignment closes on round closure -- NOT by exhaustion.
```

## 16b. Event-ordered solution propagation (C6) and finder self-validation (D4)

```
PROCEDURE SelfValidateFoundSolution
  INPUTS: RoundContext, certificate, snapshot
  PRECONDITIONS: certificate produced by EarlyStopGenerate from the found solution + snapshot
  EFFECTS:
    # D4/E2: the finder self-validates the SIGNED certificate (including signature) against the
    #        discovery snapshot BEFORE it may stop. SAME predicate as recipients (ValidateCandidate).
    BEGIN accruing E_verification for the finder (separate increment, on top of t_hash, not double-counted)
    result <- CALL ValidateCandidate(RoundContext, certificate, snapshot)
    ADD the incremental verification cost to E_verification
  RETURNS: result
  NOTE: Uses the authenticated certificate object, not an unsigned candidate (E2). Certificate
        generation does not by itself satisfy validation; the finder stops only after this passes (D4).
```

```
PROCEDURE ScheduleSolutionPropagation
  INPUTS: RoundContext, certificate, snapshot, finder
  PRECONDITIONS: round_state in {HASHING, SOLUTION_PROPAGATION, SECURITY_RECOVERY};
                 certificate produced by EarlyStopGenerate from a found valid solution + snapshot
  EFFECTS:
    # D4/E2: the finder MUST self-validate the SIGNED certificate BEFORE it may stop or propagate.
    self_ok <- CALL SelfValidateFoundSolution(RoundContext, certificate, snapshot)
    IF NOT self_ok:
      RECORD invalid_self_certificate(finder, certificate)       # finder does NOT stop; stays ACTIVE_HASHING
      RETURN not_scheduled
    # E6: enter solution propagation at the FIRST valid found-solution event (NOT after acceptance).
    IF round_state = HASHING: TRANSITION round_state -> SOLUTION_PROPAGATION
    # C6: (3) schedule per-recipient certificate-arrival events using modeled propagation delays.
    FOR EACH recipient r in current miners, r != finder:
      cert_delay(r) <- deterministic modeled propagation delay(finder -> r)   # reproducible
      SCHEDULE event CertificateArrival(RoundContext, r, certificate, snapshot) AT now + cert_delay(r)
    # (4) schedule the full-block propagation/arrival event toward the modeled acceptance point.
    block_delay <- deterministic modeled propagation delay(finder -> acceptance_point)  # reproducible
    SCHEDULE event BlockAcceptancePoint(RoundContext, certificate, snapshot, outcome-at-arrival) AT now + block_delay
    # (5) the finder ceases hashing (PATH B, resumable) via the canonical disposition; it does NOT
    #     pass through EXHAUSTED_PENDING. Block-propagation energy is accounted.
    CALL EnterLowPowerListen(RoundContext, finder, stop_reason = VALID_SOLUTION_VERIFIED)
  RETURNS: scheduled_marker
  NOTE: The discrete-event queue orders arrivals; no global set of future solutions is consulted.
        Do NOT call ValidBlockAccept here. Unpaused miners may keep hashing during
        SOLUTION_PROPAGATION (E6); further candidate solutions may still be scheduled.
```

## 16c. Certificate arrival at a recipient (C6)

```
PROCEDURE CertificateArrival
  INPUTS: RoundContext, recipient r, certificate, snapshot
  PRECONDITIONS: this is the scheduled certificate-arrival event for r
  EFFECTS:
    # (6) the recipient stays ACTIVE_HASHING until its certificate-arrival event fully validates.
    #     E1/E2: verification is against the finder's immutable discovery snapshot, carried on the event.
    IF miner_state(r) = ACTIVE_HASHING:
      result <- CALL EarlyStopVerify(RoundContext, certificate, snapshot, verifying_MinerID = r)
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
  INPUTS: RoundContext, certificate, snapshot, outcome
  PRECONDITIONS: this is the scheduled full-block arrival event at the MODELED ACCEPTANCE POINT;
                 outcome in {ACCEPTED_CANDIDATE, REJECTED, BLOCK_UNAVAILABLE, PROPAGATION_TIMEOUT}
  EFFECTS:
    # C6: the modeled acceptance point is EITHER a designated coordinator/validator OR a clearly
    #     identified canonical local view (RoundContext.acceptance_point_policy).
    IF outcome = ACCEPTED_CANDIDATE:
      # D6: batch EXACT-same-timestamp candidates BEFORE accepting; do NOT accept the first event
      #     immediately when other candidate events share the exact acceptance timestamp. Each
      #     batched candidate carries its own (certificate, snapshot) for validation (E1/E2).
      RETURN CALL AcceptanceTimestampBatch(RoundContext, acceptance_timestamp = now)
    ELSE:
      # E3/D5: REJECTED / BLOCK_UNAVAILABLE / PROPAGATION_TIMEOUT -> the SINGLE failure-recovery path.
      RETURN CALL HandlePropagationFailure(RoundContext, certificate, snapshot, failure_reason = outcome)
  RETURNS: accepted_block | resume_scheduled | no_valid_candidate
  NOTE: A strictly-earlier full-block arrival wins by discrete-event queue order; EXACT-timestamp
        ties are arbitrated by AcceptanceTimestampBatch. No event inspects unknown future timestamps.
        Every non-acceptance outcome (including an empty valid batch) funnels through
        HandlePropagationFailure, the ONLY procedure that resumes PATH-B paused miners (E3).
```

## 16d-bis. Propagation-failure recovery (E3)

```
PROCEDURE HandlePropagationFailure
  INPUTS: RoundContext, certificate, snapshot, failure_reason
  PRECONDITIONS: failure_reason in {REJECTED, BLOCK_UNAVAILABLE, PROPAGATION_TIMEOUT,
                 NO_VALID_CANDIDATE}                       # the four non-acceptance outcomes (E3)
  EFFECTS:
    # E3: the SINGLE recovery path for every non-acceptance outcome. It is invoked by
    #     BlockAcceptancePoint (REJECTED/BLOCK_UNAVAILABLE/PROPAGATION_TIMEOUT) and by
    #     AcceptanceTimestampBatch (NO_VALID_CANDIDATE, empty valid batch). No round closure occurs.
    RECORD propagation_failure(RoundID, TemplateID, certificate, failure_reason)
    # (1) return the round to HASHING unless a floor breach requires SECURITY_RECOVERY.
    breach <- CALL SecurityFloorEvaluate(RoundContext, latest (H_active, H_honest, q_adv), floor_state)
    IF breach:
      ENSURE round_state = SECURITY_RECOVERY                # SecurityFloorEvaluate performed the transition
    ELSE:
      # E6: SOLUTION_PROPAGATION was entered at the first found-solution; a failed propagation
      #     returns the round to HASHING so surviving/ resumed miners keep searching.
      IF round_state = SOLUTION_PROPAGATION: TRANSITION round_state -> HASHING
      ELSE: ENSURE round_state = HASHING
    # (2) cancel obsolete events tied to THIS failed candidate so no stale acceptance can fire.
    CANCEL all pending CertificateArrival / BlockAcceptancePoint events carrying this certificate
    # (3)-(4) enumerate EVERY PATH-B paused miner and schedule its resume. ResumeFromPause restores
    #         the paused assignment to CURRENT from its retained actual_frontier, charges wake +
    #         transition energy, and recomputes H_active/H_honest/H_adversarial/q_adv.
    FOR EACH miner M with a PAUSED assignment AND entry_stop_reason(M) = VALID_SOLUTION_VERIFIED:
      SCHEDULE event ResumeFromPause(RoundContext, M, trigger = failure_reason)
    RETURN resume_scheduled
  RETURNS: resume_scheduled
  NOTE: This procedure NEVER accepts a block and NEVER closes the round. It is the sole owner of
        propagation-failure recovery (E3): it returns the round to HASHING (or SECURITY_RECOVERY on
        a breach), cancels the failed candidate's obsolete events, and resumes each PATH-B paused
        miner via ResumeFromPause. A PATH-A exhausted (searched/completed) range is never resumed.
```

## 16e. Same-timestamp acceptance arbitration (D6)

```
PROCEDURE ValidateCandidate
  INPUTS: RoundContext, certificate, snapshot
  PRECONDITIONS: none   # canonical predicate; used by finder self-validation, recipients, and acceptance
  EFFECTS:
    # E1/E2: validate the SIGNED certificate against the IMMUTABLE discovery SNAPSHOT, NOT against
    #        the finder's later (possibly PAUSED) assignment. Does NOT require the assignment to be
    #        CURRENT at certificate/block arrival time.
    ok <- (certificate binds snapshot: same RoundID/TemplateID/AssignmentID/assignment_version/
             nonce/candidate_hash/target)
          AND (snapshot.assignment_status_at_discovery = CURRENT)                    # valid + CURRENT at discovery
          AND (assignment(AssignmentID, assignment_version) was NOT revoked before snapshot.discovery_time)
          AND (snapshot.range_start <= certificate.nonce <= snapshot.range_end)      # I2: nonce in that version's range
          AND (certificate.RoundID = RoundID_current AND certificate.TemplateID = TemplateID_committed)  # I3 bound values
          AND (certificate.candidate_hash is the modeled digest of TemplateID and nonce AND
               satisfies certificate.target under fixed D)                           # target verification (I11)
          AND (certificate.signature/authentication valid for certificate.MinerID over the signed fields)
    IF NOT ok: RECORD invalid_certificate(certificate)
  RETURNS: ok
  NOTE: The SINGLE canonical validation predicate (E2), used identically by
        SelfValidateFoundSolution (finder), EarlyStopVerify (recipients), and AcceptanceTimestampBatch.
        It never requires the finder's assignment to remain CURRENT after discovery (E1).
```

```
PROCEDURE AcceptanceTimestampBatch
  INPUTS: RoundContext, acceptance_timestamp
  PRECONDITIONS: at least one BlockAcceptancePoint(outcome = ACCEPTED_CANDIDATE) event fires at
                 acceptance_timestamp for this acceptance point
  EFFECTS:
    # D6: (1) gather ALL same-acceptance-point candidate events with EXACTLY this timestamp. Each
    #     event carries its own (certificate, snapshot) captured at discovery (E1/E2).
    batch <- all ACCEPTED_CANDIDATE BlockAcceptancePoint events at this acceptance point with
             timestamp = acceptance_timestamp   # each event c has c.certificate and c.snapshot
    # (2)-(3) validate every candidate against ITS OWN discovery snapshot; discard invalid.
    valid <- empty
    FOR EACH candidate event c in batch:
      IF CALL ValidateCandidate(RoundContext, c.certificate, c.snapshot): APPEND c to valid   # E1/E2
    IF valid is empty:
      # E3: no valid candidate -> the SINGLE failure-recovery path (resumes PATH-B paused miners).
      #     Uses the earliest batch event's (certificate, snapshot) only to label the failure record.
      RETURN CALL HandlePropagationFailure(RoundContext, batch.first.certificate,
                                           batch.first.snapshot, failure_reason = NO_VALID_CANDIDATE)
    # (4) among valid candidates choose smallest candidate_hash, then smallest MinerID.
    winner <- argmin over valid of (c.certificate.candidate_hash, then c.certificate.MinerID)
    # (5) record all others as competing/stale.
    FOR EACH c in valid, c != winner: RECORD competing_valid(c.certificate)
    # (6) ONLY AFTER arbitration finishes: accept + close (no round closure occurs before this).
    RETURN CALL ValidBlockAccept(RoundContext, winner.certificate, winner.snapshot)
  RETURNS: accepted_block | not_selected | resume_scheduled
  NOTE: For DIFFERENT timestamps the earliest timestamp wins by discrete-event queue order; this
        procedure arbitrates ONLY exact-timestamp ties. No event inspects unknown future
        timestamps; no round closure occurs before same-timestamp arbitration completes. An empty
        valid batch is a propagation failure (E3), not a silent no-op.
```

## 17. Valid block acceptance

```
PROCEDURE ValidBlockAccept
  INPUTS: RoundContext, winner_certificate, winner_snapshot
  PRECONDITIONS: invoked ONLY from AcceptanceTimestampBatch after arbitration (D6);
                 winner_certificate already validated by ValidateCandidate against winner_snapshot
                 and chosen as the batch winner;
                 # E6: the round entered SOLUTION_PROPAGATION at the FIRST valid found-solution
                 #     (ScheduleSolutionPropagation); acceptance therefore transitions from it.
                 round_state = SOLUTION_PROPAGATION
  EFFECTS:
    IF a block has ALREADY been accepted this round:
      RECORD competing_valid(winner_certificate)                 # a strictly-earlier timestamp already won
      RETURN not_selected
    RECORD accepted_block(winner_certificate)
    # E6: a SINGLE transition; the round is already in SOLUTION_PROPAGATION (no double transition).
    TRANSITION round_state -> ROUND_ACCEPTED
    # D7: centralised round closure (the SINGLE closure path).
    CALL CloseRoundAssignments(RoundContext, disposition = ROUND_ACCEPTED, stop_reason = ROUND_ACCEPTED)
  RETURNS: accepted_block | not_selected
  NOTE: Earliest arrival is the discrete-event queue order (strictly-earlier timestamps win before
        this batch); exact-timestamp ties are arbitrated in AcceptanceTimestampBatch; per-candidate
        validation is done by ValidateCandidate against each candidate's own snapshot (E1/E2). The
        round entered SOLUTION_PROPAGATION at the first found-solution, so this performs the single
        SOLUTION_PROPAGATION -> ROUND_ACCEPTED transition (E6). No chain-wide fork-choice proof is claimed.
```

## 17a. Centralised round closure (D7)

```
PROCEDURE CloseRoundAssignments
  INPUTS: RoundContext, disposition (ROUND_ACCEPTED | ROUND_ABORTED), stop_reason
  PRECONDITIONS: disposition in {ROUND_ACCEPTED, ROUND_ABORTED}; stop_reason = disposition
  EFFECTS:
    # D7/E7: the SINGLE round-closure path. It records a round_closure_disposition (how the ROUND
    #        ended) that is SEPARATE from a miner's entry_stop_reason (why the miner earlier LEFT
    #        ACTIVE_HASHING). Closure NEVER overwrites an existing RANGE_EXHAUSTED or
    #        VALID_SOLUTION_VERIFIED entry reason. Every holder state has an EXPLICIT action below;
    #        there is NO generic "update state consistently" step.
    FOR EACH open assignment X under the closing RoundID/TemplateID:
      SET h <- holder(X)
      PRESERVE coverage_state(X), custody_status(X), provenance history   # closure changes no coverage
      SET round_closure_disposition(X) <- disposition            # E7: separate from entry_stop_reason
      # do NOT reassign X under the closed TemplateID; do NOT mark any unfinished range exhausted
      SWITCH miner_state(h):

        CASE ACTIVE_HASHING:
          # still hashing with NO prior stop reason: closure IS this miner's stop event, so the
          # round disposition legitimately becomes its entry_stop_reason (5th EnterLowPowerListen reason).
          CALL EnterLowPowerListen(RoundContext, h, stop_reason = disposition)   # sets entry_stop_reason(h) <- disposition; closes X

        CASE EXHAUSTED_PENDING:
          # PATH-A holder mid-completion: entry_stop_reason is already RANGE_EXHAUSTED. PRESERVE it.
          ASSERT entry_stop_reason(h) = RANGE_EXHAUSTED
          CLOSE X as round-ended                                 # completed range stays searched/completed
          TRANSITION miner_state(h) -> LOW_POWER_LISTEN          # finishes PATH A; RANGE_EXHAUSTED NOT overwritten

        CASE LOW_POWER_LISTEN:
          # already parked (PATH-A RANGE_EXHAUSTED, PATH-B VALID_SOLUTION_VERIFIED, or ASSIGNMENT_REVOKED).
          ASSERT entry_stop_reason(h) in {RANGE_EXHAUSTED, VALID_SOLUTION_VERIFIED, ASSIGNMENT_REVOKED}
          CLOSE X as round-ended                                 # a PATH-B PAUSED assignment is NOT resumed
          # miner_state(h) stays LOW_POWER_LISTEN; entry_stop_reason(h) unchanged (E7)

        CASE WAKING:
          # a pending activation: cancel it; the miner never reaches ACTIVE_HASHING for this round.
          CANCEL the pending WakeComplete for h
          CLOSE X as round-ended                                 # bound PENDING assignment left un-activated
          TRANSITION miner_state(h) -> LOW_POWER_LISTEN          # park; no entry_stop_reason forced onto the range

        CASE REGISTERED OR RESERVE:
          # holds no CURRENT range under this round; nothing to stop and nothing to resume.
          IF X is a bound PENDING assignment: CLOSE X as round-ended
          # miner_state(h) unchanged (REGISTERED stays REGISTERED; RESERVE stays RESERVE)

        CASE OFFLINE OR DISQUALIFIED:
          # not participating: close the assignment record only.
          CLOSE X as round-ended
          # miner_state(h) unchanged (OFFLINE stays OFFLINE; DISQUALIFIED stays DISQUALIFIED)
    # cancel pending events belonging to the closed round
    CANCEL all pending wake / resume / certificate-arrival / BlockAcceptancePoint events for RoundID
    RECORD round_closure(RoundID, TemplateID, disposition)
    finalise state durations and energy to the EXACT closure time  # I5, I6, I7
  RETURNS: closure_record
  NOTE: This is the ONLY round-closure path. ValidBlockAccept calls it with ROUND_ACCEPTED;
        RoundAbort calls it with ROUND_ABORTED. Only an ACTIVE_HASHING holder receives the
        disposition as its entry_stop_reason (it had none); every already-stopped holder keeps its
        recorded entry_stop_reason and merely records a SEPARATE round_closure_disposition (E7). No
        range is marked exhausted by closure, and nothing is reassigned under the closed TemplateID.
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
PROCEDURE CloseTemplateAssignments
  INPUTS: RoundContext, old_TemplateID
  PRECONDITIONS: round_state = TEMPLATE_REFRESH; a new template is about to be committed
  EFFECTS:
    # E8: template-scoped closure of EVERY assignment under the OLD TemplateID. The ROUND CONTINUES
    #     (this is NOT round closure); coverage/provenance history is PRESERVED, never deleted. Each
    #     holder is routed off the old template ONLY through its LEGAL per-state edge (no illegal
    #     direct transitions), so template refresh never fabricates a transition.
    FOR EACH open assignment X under old_TemplateID:
      SET h <- holder(X)
      PRESERVE historical coverage_state(X), custody_status(X), provenance/reassignment records
      SET custody_status(range(X)) <- superseded_by_template_refresh   # I8b lineage marker (historical)
      SWITCH miner_state(h):
        CASE ACTIVE_HASHING:
          # the old-template assignment is revoked because the template changed (legal T27).
          CALL EnterLowPowerListen(RoundContext, h, stop_reason = ASSIGNMENT_REVOKED)   # -> LOW_POWER_LISTEN
        CASE EXHAUSTED_PENDING:
          # PATH-A holder: finish the exhaustion drop (legal T8); entry_stop_reason RANGE_EXHAUSTED kept.
          CLOSE X
          TRANSITION miner_state(h) -> LOW_POWER_LISTEN                                  # T8
        CASE LOW_POWER_LISTEN:
          # a PAUSED PATH-B assignment is CLOSED (it is NOT resumed under a discarded template).
          CLOSE X
          # miner_state(h) stays LOW_POWER_LISTEN; entry_stop_reason(h) unchanged
        CASE WAKING:
          # the bound assignment is on the discarded template -> fails TemplateID validation (legal T12).
          CANCEL the pending WakeComplete for h ; release the bound range
          TRANSITION miner_state(h) -> OFFLINE                                           # T12
        CASE REGISTERED OR RESERVE OR OFFLINE OR DISQUALIFIED:
          # holds no CURRENT assignment under old_TemplateID; nothing to close; state unchanged
          NO-OP
    CANCEL all pending certificate-arrival / BlockAcceptancePoint / resume events bound to old_TemplateID
    RECORD template_closure(RoundID, old_TemplateID)
  RETURNS: template_closure_record
  NOTE: Template refresh does NOT end the round; it discards the OLD search domain. Old coverage and
        provenance are retained as history (C5). Holders leave the old template ONLY via legal
        miner-state edges (T27 / T8 / T12); no completed old range is ever reassigned (C5/CR-B5).

PROCEDURE TemplateRefresh
  INPUTS: RoundContext
  PRECONDITIONS: round_state in {ROUND_EXHAUSTED, HASHING(systemic template disagreement)}
  EFFECTS:
    # D8/E8: correct round-state sequencing so TemplateCommit ALWAYS runs from TEMPLATE_COMMITMENT;
    #        TEMPLATE_REFRESH NEVER bypasses TEMPLATE_COMMITMENT.
    TRANSITION round_state -> TEMPLATE_REFRESH                  # from ROUND_EXHAUSTED or HASHING
    # E8-(1)/(2): close ALL old-template assignments via the EXPLICIT procedure; history preserved.
    CALL CloseTemplateAssignments(RoundContext, old_TemplateID = TemplateID_current)
    # (3) build the new immutable template WHILE in TEMPLATE_REFRESH (C5: a NEW search domain).
    build new candidate_template
    # E8-(3): move TEMPLATE_REFRESH -> TEMPLATE_COMMITMENT BEFORE calling TemplateCommit (its precondition).
    TRANSITION round_state -> TEMPLATE_COMMITMENT
    # E8-(4): TemplateCommit REQUIRES TEMPLATE_COMMITMENT and transitions the round to ASSIGNMENT.
    new_TemplateID <- CALL TemplateCommit(RoundContext, new candidate_template)   # -> ASSIGNMENT
    # E8-(5): select ONLY eligible miners whose CURRENT state has a LEGAL activation edge into WAKING:
    #         REGISTERED (T3), RESERVE (T4), or the permitted low-power state LOW_POWER_LISTEN (T10).
    #         OFFLINE and DISQUALIFIED miners receive NO assignment; mid-wake WAKING miners are skipped.
    eligible <- { m : miner_state(m) in {REGISTERED, RESERVE, LOW_POWER_LISTEN} }
    FOR EACH miner m in eligible:
      # E8-(6): a FRESH ORIGINAL assignment over the NEW domain (NOT a reassignment lineage; C5).
      CREATE assignment(m, fresh_range(m), new_TemplateID, RoundID, new lease window) WITH status = PENDING
      SET custody_status(fresh_range(m)) <- original
      SET previous_assignment_reference <- null                 # C5: NOT a reassignment lineage
      # E8-(7): use the LEGAL per-source-state transition into WAKING (D2: never *->ACTIVE_HASHING directly).
      SWITCH miner_state(m):
        CASE REGISTERED:        TRANSITION miner_state(m) -> WAKING     # T3
        CASE RESERVE:           TRANSITION miner_state(m) -> WAKING     # T4
        CASE LOW_POWER_LISTEN:  TRANSITION miner_state(m) -> WAKING     # T10 (template-refresh wake trigger)
      # E8-(8): WakeComplete validates I1/RoundID/new_TemplateID and flips PENDING -> CURRENT (T5).
      CALL WakeComplete(RoundContext, m, fresh_range(m))
      # do NOT call RangeReassign for old ranges; do NOT rebind old assignments to new_TemplateID
    ASSERT difficulty unchanged                                 # I12
    # E8-(9): after the intended assignment set is valid, START the new mining phase EXPLICITLY.
    ASSERT round_state = ASSIGNMENT
    TRANSITION round_state -> HASHING                           # E8: explicit ASSIGNMENT -> HASHING
  RETURNS: new_TemplateID
  NOTE: Refresh NEVER bypasses TEMPLATE_COMMITMENT (TemplateCommit runs only from it, D8/E8) and
        NEVER reassigns a completed old range -- old assignments are CLOSED via CloseTemplateAssignments
        and NEW ORIGINAL assignments are created over the new domain (C5). Only eligible REGISTERED /
        RESERVE / LOW_POWER_LISTEN miners are activated, each via its legal edge into WAKING; OFFLINE
        and DISQUALIFIED miners receive no assignment (E8). The round reaches HASHING explicitly.
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

The Stage-1E procedures add **no** new sampling site. `ReserveActivate` (E4) and `TemplateRefresh`
(E8) reach the wake-latency draw ONLY through `WakeComplete` (already item 3); `HandlePropagationFailure`
(E3), `CloseRoundAssignments` (E7), `CloseTemplateAssignments` (E8), `LeaseExpiry` renewal (E9),
`ValidateCandidate`/`SelfValidateFoundSolution`/`EarlyStopVerify` (E1/E2), and the acceptance
cluster (`BlockAcceptancePoint`/`AcceptanceTimestampBatch`/`ValidBlockAccept`, E6) are entirely
deterministic protocol logic — the discrete-event queue order and the exact-timestamp tie-break
(`candidate_hash`, then `MinerID`) contain no random draw.

Every other step is deterministic protocol logic. This separation is deliberate: it keeps the
protocol's decision logic reproducible and audit-checkable against `I1..I17`, while confining
all randomness to clearly labelled model draws that exist solely because Stage-1 evaluation is
a simulation and not a real deployment. None of the above is executable source.
