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

## 0. Concurrency and discrete-event model (Stage 1F)

Stage-1F makes the concurrency and discrete-event semantics of PoCol explicit. Seven normative
rules govern the whole specification; every procedure below conforms to them.

**(0.1) Single-threaded discrete-event loop.** The simulator advances one global discrete-event
queue. Each event fires at a definite `event_time`; a handler runs to completion without
preemption. A long-latency physical process (wake ramp, message propagation) is NEVER executed by
a blocking call that occupies the loop; it is represented by SCHEDULING a future event (F5).
Concurrency is modeled by many independent future events, not by parallel handlers, so two miners
"doing something at once" are two independently scheduled events, each firing at its own timestamp.

**(0.2) Event envelope (F1).** Every scheduled event carries an immutable envelope:

    { event_type, event_time, RoundID, TemplateID,
      CandidateID?, PropagationID?, MinerID?, AssignmentID?, assignment_version?, seq }

`CandidateID` and `PropagationID` are REQUIRED on every certificate-arrival, block-arrival,
validation, timeout, cancellation, and resume event. `seq` is a strictly monotonic per-run
creation counter used ONLY as the final deterministic tie-break (F8). A propagation context is
NEVER identified by `RoundID` alone.

**(0.3) Central miner-state hook (F6).** No procedure mutates `miner_state` directly. Every
miner-state change is performed by `ApplyMinerStateTransition`, the SOLE owner of residency
accounting, one-shot transition energy, the `H_active = H_honest + H_adversarial` recompute
(I17), `q_adv`/NA, and security-floor scheduling. The keyword `TRANSITION miner_state(...)` does
not appear in any procedure; a state change is always written `CALL ApplyMinerStateTransition(...)`.

**(0.4) Event-scheduled wake (F5).** Every activation into `ACTIVE_HASHING` passes through
`StartWake` (non-blocking) and its scheduled `WakeCompleteEvent`. Miners starting to wake at the
same instant wake independently on their own completion timestamps; no wake serialises another.

**(0.5) Immutable assignment versions (F7).** An assignment is an immutable versioned object.
Renewal creates a NEW version and SUPERSEDES the old one; EXACTLY ONE version per lineage is
`CURRENT`. A `SolutionEligibilitySnapshot` resolves to the exact version that was `CURRENT` at
discovery, so a solution discovered under an old version stays verifiable after renewal.

**(0.6) Active propagation set (F3).** `active_propagation_set` holds every live
`CandidatePropagationContext`. The round is `SOLUTION_PROPAGATION` iff this set is non-empty OR a
same-timestamp acceptance batch or a live candidate-specific acceptance event remains. A context is
"live" while its `status ∈ {DISCOVERED, SELF_VALIDATED, PROPAGATING, PENDING_ACCEPTANCE}`; it
leaves the set on `FAILED` (candidate-scoped failure) or on round acceptance
(`ACCEPTED`/`COMPETING`/`STALE`/`CANCELLED`). The predicate

    propagation_quiescent(RoundContext) :=
        active_propagation_set is empty
        AND no ACCEPTED_CANDIDATE same-timestamp acceptance batch is pending
        AND no live candidate-specific CertificateArrival / BlockAcceptancePoint event remains
        AND no block has been accepted this round

is the ONLY condition under which `SOLUTION_PROPAGATION → HASHING` is permitted (F3). Failure of one
candidate removes only that candidate; the round stays `SOLUTION_PROPAGATION` while any other
candidate is live.

**(0.7) Global event-priority contract (F8).** Same-timestamp events of different types are
ordered by the deterministic priority table of `STAGE_01F_EVENT_PRIORITY_TABLE.md`; ties within a
type break by the event's `(CandidateID, MinerID, AssignmentID, seq)`, NEVER by data-structure
iteration order. The order is reproducible across reruns.

### 0.8 Core data model (Stage 1F)

```
STRUCTURE CandidatePropagationContext (CPC)   # F1: one per discovered candidate solution; immutable identity
  CandidateID                 : fresh globally-unique id (immutable)
  PropagationID               : fresh globally-unique id (immutable)
  RoundID, TemplateID
  certificate                 : signed early-stop certificate (EarlyStopGenerate)
  snapshot                    : SolutionEligibilitySnapshot (immutable, discovery-time)
  finder_MinerID
  discovery_time
  certificate_arrival_events  : set of scheduled per-recipient events (each carries CandidateID/PropagationID)
  block_arrival_event         : the scheduled BlockAcceptancePoint event (carries CandidateID/PropagationID)
  acceptance_timestamp        : set when a block-arrival with outcome ACCEPTED_CANDIDATE fires (else null)
  status                      : one of the candidate statuses below
  failure_reason              : one of {REJECTED, BLOCK_UNAVAILABLE, PROPAGATION_TIMEOUT, NO_VALID_CANDIDATE} or null

# F1 candidate status enum (mutually exclusive):
#   DISCOVERED -> SELF_VALIDATED -> PROPAGATING -> PENDING_ACCEPTANCE -> {ACCEPTED | FAILED}
#   plus, set by another candidate's acceptance: COMPETING, STALE, CANCELLED
CANDIDATE_STATUS in {DISCOVERED, SELF_VALIDATED, PROPAGATING, PENDING_ACCEPTANCE,
                     FAILED, ACCEPTED, COMPETING, STALE, CANCELLED}

STRUCTURE Assignment (immutable version object)   # F7: renewal makes a NEW version; never mutate in place
  AssignmentID                : identity of THIS version (immutable once created)
  assignment_version          : monotonic version number within the lineage
  lineage_id                  : stable id shared by all versions of one assignment lineage
  MinerID, range = [range_start, range_end], RoundID, TemplateID
  status                      : one of {PENDING, CURRENT, PAUSED, SUPERSEDED, CLOSED}
  previous_assignment_reference : prior version's AssignmentID (null for an ORIGINAL first version)
  assignment_origin           : one of {ORIGINAL, RENEWED, REASSIGNED}
  custody_status              : {original, renewed, reassigned, revoked, expired, abandoned, completed, superseded_by_template_refresh}
  actual_frontier, reported_frontier, accepted_frontier
  provenance                  : I9 reassignment/lineage records
  lease_start, lease_expiry
  superseded_at               : set when status becomes SUPERSEDED (else null)
  # F2 pause bookkeeping (set only while PAUSED via VALID_SOLUTION_VERIFIED):
  pause_cause_candidate_id    : the CandidateID whose certificate this holder verified (or null)
  pause_cause_propagation_id  : the matching PropagationID (or null)
  retained_actual_frontier    : the frontier retained at pause (or null)

INVARIANT (F7): for each lineage_id, EXACTLY ONE version has status = CURRENT at any instant.
```

### 0.9 Central miner-state transition hook (F6)

```
PROCEDURE ApplyMinerStateTransition
  INPUTS: MinerID, old_state, new_state, event_time, reason, assignment_ref, candidate_ref
  PRECONDITIONS: old_state = miner_state(MinerID), EXCEPT the registration entry (T1) where
                 old_state = the sentinel NONE and step (1) is a no-op;                  # F6
                 (old_state -> new_state) is a legal miner transition (STAGE_01_MINER_STATE_MACHINE.md §3)
  EFFECTS:
    # F6: the SOLE owner of every miner-state change. It is idempotent per (MinerID, event_time,
    #     new_state): a duplicate call for the same transition at the same event is a NO-OP.
    IF already_applied(MinerID, event_time, old_state -> new_state):
      RETURN duplicate_suppressed                                        # prevent duplicate transitions at the same event
    # (1) close the OLD residency interval at event_time; (2) open the NEW one at event_time.
    IF old_state != NONE: CLOSE residency(MinerID, old_state) at event_time   # accrues P_old * (event_time - last_boundary)
    OPEN  residency(MinerID, new_state) at event_time                    # begins P_new accrual (I5/I6)
    # (3) one-shot boundary energy for this crossing (E_transition and/or E_coordination as defined per edge).
    RECORD E_transition/E_coordination for (old_state -> new_state)      # I6; never folded into P*t; never double-counted
    # (4) assignment status update where the edge specifies one (e.g. WAKING->ACTIVE_HASHING activates PENDING->CURRENT).
    IF edge specifies an assignment status change: UPDATE status(assignment_ref) accordingly
    # (5) atomically set the new miner_state.
    SET miner_state(MinerID) <- new_state
    # (6) recompute the census DETERMINISTICALLY from the post-transition ACTIVE_HASHING set (I17).
    SET H_honest(event_time)      <- SUM over honest miners in ACTIVE_HASHING of modeled hash rate
    SET H_adversarial(event_time) <- SUM over adversarial miners in ACTIVE_HASHING of modeled hash rate
    SET H_active(event_time)      <- H_honest(event_time) + H_adversarial(event_time)   # I17 EXACT at this boundary
    IF H_active(event_time) = 0: SET q_adv(event_time) <- NA             # I17: undefined at zero
    ELSE:                        SET q_adv(event_time) <- H_adversarial(event_time) / H_active(event_time)
    RECORD transition_audit(MinerID, old_state, new_state, event_time, reason, assignment_ref, candidate_ref)
    # (7) schedule (do NOT inline) the security-floor evaluation for this boundary.
    SCHEDULE event SecurityFloorEvaluate(RoundContext, event_time, (H_active, H_honest, q_adv), floor_state)
  RETURNS: transition_record
  NOTE: This is the ONLY writer of miner_state (0.3). It recomputes H_active/H_honest/H_adversarial
        and re-checks I17 at EVERY ACTIVE_HASHING boundary (entry and exit). It never SAMPLES a hash
        rate; the adversarial active-census draw remains solely in ActiveHashRateUpdate. Duplicate
        suppression makes concurrent handlers that reference the same transition safe.
```

### 0.10 Event-scheduled wake (F5)

```
PROCEDURE StartWake
  INPUTS: RoundContext, MinerID, target_assignment, from_state
  PRECONDITIONS: from_state = miner_state(MinerID) in {REGISTERED, RESERVE, EXHAUSTED_PENDING, LOW_POWER_LISTEN};
                 target_assignment is a bound PENDING (or PAUSED-resumed) assignment for MinerID
  EFFECTS:
    # F5: NON-BLOCKING. Begin the wake and RETURN to the event loop immediately; do NOT run the
    #     wake latency inside this handler (that would serialise other miners).
    CALL ApplyMinerStateTransition(MinerID, from_state, WAKING, now, reason = wake_start,
                                   assignment_ref = target_assignment, candidate_ref = null)   # F6
    # ---- [SIMULATION SAMPLING] ----
    wake_latency <- [SIMULATION SAMPLING] wake_latency_model(MinerID)    # the ONLY wake draw (sampling summary item 3)
    # ---- deterministic protocol logic ----
    SCHEDULE event WakeCompleteEvent(RoundContext, MinerID, target_assignment) AT now + wake_latency
    RETURN wake_started                                                  # returns immediately (0.1)
  RETURNS: wake_started

PROCEDURE WakeCompleteEvent
  INPUTS: RoundContext, MinerID, target_assignment
  PRECONDITIONS: this is the scheduled wake-completion event for MinerID; miner_state(MinerID) = WAKING
  EFFECTS:
    # F5: runs at its OWN event timestamp (now = the completion time), independently of any other
    #     miner's wake. Wake residency P_wake * wake_latency is accrued by ApplyMinerStateTransition
    #     when it closed the WAKING interval at this timestamp.
    IF wake_within_deadline(MinerID):                                    # completion timestamp <= wake_deadline
      # validate the bound PENDING (or resumed PAUSED) assignment before hashing.
      VALIDATE target_assignment against I1, current RoundID, committed TemplateID   # re-checks I1/I10/I3
      # WAKING -> ACTIVE_HASHING (T5); the edge activates PENDING -> CURRENT for a fresh assignment,
      # or restores a resumed PAUSED assignment to CURRENT from its retained actual_frontier.
      CALL ApplyMinerStateTransition(MinerID, WAKING, ACTIVE_HASHING, now, reason = ramp_complete,
                                     assignment_ref = target_assignment, candidate_ref = null)   # F6 (activates status, recomputes I17)
      # begin (or resume) hashing from the assignment's frontier; identical for a fresh or resumed range.
      RETURN CALL ActiveHashing(RoundContext, target_assignment, step_budget)
      # activation_record is recorded by ApplyMinerStateTransition above
    ELSE:
      RECORD reserve_wake_failure(MinerID)
      CALL ApplyMinerStateTransition(MinerID, WAKING, OFFLINE, now, reason = wake_deadline_expiry,
                                     assignment_ref = target_assignment, candidate_ref = null)   # T12
      # E4/F5: never leave a bound-but-un-activated range as if held; release it cleanly.
      MARK range(target_assignment) as inactive_unsearched / reassignable   # supports I8a (unsearched only)
      SET custody_status(target_assignment) <- abandoned
      CLOSE target_assignment as not-activated (status PENDING -> CLOSED)   # no CURRENT assignment recorded
      RETURN activation_failure
  RETURNS: activation_record | activation_failure
  NOTE: Three miners that call StartWake at the same timestamp schedule three independent
        WakeCompleteEvents at three (generally different) completion timestamps; they never wake
        serially inside one handler (F5). The former synchronous WakeComplete is replaced by this
        pair; no procedure performs a blocking wake.
```

### 0.11 Shared pending-assignment constructor (F4)

```
PROCEDURE CreatePendingAssignment
  INPUTS: RoundContext, MinerID, range, assignment_origin, source_assignment, reason
  PRECONDITIONS: assignment_origin in {ORIGINAL, RENEWED, REASSIGNED};
                 range disjoint from all valid active assignments (I1);
                 custody_status(range) != completed AND coverage_state(range) != searched
  EFFECTS:
    # F4: the SINGLE constructor used by RangeAssign, ReserveActivate, RangeReassign, TemplateRefresh.
    #     It sets provenance CORRECTLY from assignment_origin -- a reassignable suffix is NEVER
    #     labelled ORIGINAL.
    SET new_lineage <- (assignment_origin = REASSIGNED ? lineage_id(source_assignment) : fresh lineage_id)
    CREATE assignment version A WITH
        AssignmentID       = fresh id
        assignment_version = (assignment_origin = REASSIGNED ? version(source_assignment)+1 : 1)
        lineage_id         = new_lineage
        MinerID, range, RoundID, TemplateID
        status             = PENDING
        assignment_origin  = assignment_origin
    SWITCH assignment_origin:
      CASE ORIGINAL:
        SET custody_status(range)                <- original
        SET previous_assignment_reference(A)     <- null
      CASE REASSIGNED:
        ASSERT source_assignment is not null AND reason is a permitted reassignment reason
        SET custody_status(range)                <- reassigned
        SET previous_assignment_reference(A)     <- AssignmentID(source_assignment)
        SET prior_pc <- last accepted ProgressCommit covering range(source_assignment)    # I13 de-dup key
        APPEND provenance(A) <- reassignment_record(range, from = source_assignment, reason,
                                                     timestamp = now, prior_pc)          # I9 complete provenance
      CASE RENEWED:
        SET custody_status(range)                <- renewed
        SET previous_assignment_reference(A)     <- AssignmentID(source_assignment)
        COPY actual/reported/accepted frontiers AND provenance FROM source_assignment    # F7 continuity
    APPEND A to assignment_ledger                                        # supports I8a
  RETURNS: A
  NOTE: ORIGINAL is used ONLY for a fresh never-assigned range; a previously-assigned unsearched
        suffix MUST use REASSIGNED with full I9 provenance (F4). RENEWED is used by RenewAssignment
        (F7) and copies the lineage's coverage forward.
```

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
    # F6: every miner-state change routes through the hook (0.3); T1 uses old_state = NONE.
    CALL ApplyMinerStateTransition(MinerID, old_state = NONE, new_state = REGISTERED, event_time = now,
                                   reason = register, assignment_ref = null, candidate_ref = null)   # T1
    OPTIONALLY CALL ApplyMinerStateTransition(MinerID, old_state = REGISTERED, new_state = RESERVE,
                                   event_time = now, reason = admit_to_reserve,
                                   assignment_ref = null, candidate_ref = null)          # T2 (held, not yet assigned)
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
    SELECT candidate_range from unassigned portion of nonce_domain      # fresh, never-assigned -> ORIGINAL
    # F4: the shared constructor performs the I1 overlap guard, ledgers the version, and sets
    #     custody_status = original / previous_assignment_reference = null.
    assignment <- CALL CreatePendingAssignment(RoundContext, MinerID, candidate_range,
                    assignment_origin = ORIGINAL, source_assignment = null, reason = null)
    SET lease_start(assignment)  <- now
    SET lease_expiry(assignment) <- now + lease_duration
    # F5/F6/D2: activation ALWAYS passes through WAKING via the NON-BLOCKING StartWake; WAKING ->
    #           ACTIVE_HASHING (T5) and PENDING -> CURRENT happen later in WakeCompleteEvent.
    RETURN CALL StartWake(RoundContext, MinerID, target_assignment = assignment,
                          from_state = miner_state(MinerID))            # T3 (REGISTERED) or T4 (RESERVE)
  RETURNS: assignment (PENDING; becomes CURRENT at its scheduled WakeCompleteEvent)
  NOTE: A zero wake-latency experimental value is permitted later, but the WAKING state and its
        P_wake*t_wake + E_transition accounting path always exist (D2). StartWake returns to the
        event loop immediately; the miner reaches ACTIVE_HASHING at its own wake-completion event (F5).
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
      # F6: PATH-A exit routes through the hook (recomputes H_active/I17 at the ACTIVE_HASHING boundary).
      CALL ApplyMinerStateTransition(MinerID, ACTIVE_HASHING, EXHAUSTED_PENDING, now,
                                     reason = RANGE_EXHAUSTED, assignment_ref = assignment, candidate_ref = null)   # T7
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
  INPUTS: RoundContext, MinerID, stop_reason,
          pause_cause_candidate_id = null, pause_cause_propagation_id = null    # F2: required for PATH B only
  PRECONDITIONS: stop_reason in {RANGE_EXHAUSTED, ASSIGNMENT_REVOKED, VALID_SOLUTION_VERIFIED,
                 ROUND_ACCEPTED, ROUND_ABORTED};               # I4: every entry records a reason
                 IF stop_reason = VALID_SOLUTION_VERIFIED THEN pause_cause_candidate_id != null
                   AND pause_cause_propagation_id != null      # F2: the pause cause is a specific candidate
  EFFECTS:
    SET from_state <- miner_state(MinerID)
    # C1: reason-specific disposition. There is NO generic "release held range to pool" step.
    SWITCH stop_reason:

      CASE RANGE_EXHAUSTED:                                    # PATH A
        ASSERT from_state = EXHAUSTED_PENDING
        ASSERT accepted_exhaustion(assignment) = TRUE          # accepted exhaustion accounting exists
        ASSERT coverage_state(range) = searched AND custody_status(range) = completed
        CLOSE the assignment
        # do NOT release or reassign any part of the completed range

      CASE ASSIGNMENT_REVOKED:
        ASSERT from_state = ACTIVE_HASHING
        PRESERVE accepted searched prefix [range_start, accepted_frontier]
        SET suffix <- accepted unsearched suffix [accepted_frontier + 1, range_end]
        MARK suffix as inactive_unsearched / reassignable      # only the accepted unsearched suffix (C4)
        CLOSE/SUPERSEDE the assignment

      CASE VALID_SOLUTION_VERIFIED:                            # PATH B
        ASSERT from_state = ACTIVE_HASHING
        ASSERT the honoured early-stop certificate passed I11
        PAUSE the assignment (status CURRENT -> PAUSED); retain actual_frontier AND accepted_frontier
        # F2: record the SPECIFIC candidate that caused this pause, so a later candidate-scoped
        #     failure resumes ONLY the miners paused by that candidate.
        SET pause_cause_candidate_id(assignment)   <- pause_cause_candidate_id
        SET pause_cause_propagation_id(assignment) <- pause_cause_propagation_id
        SET paused_assignment_id(assignment)       <- AssignmentID(assignment)
        SET retained_actual_frontier(assignment)   <- actual_frontier(assignment)
        # do NOT change coverage to searched; do NOT release the assignment

      CASE ROUND_ACCEPTED OR ROUND_ABORTED:
        CLOSE the assignment because the round ended
        # do NOT mark the range exhausted; do NOT reassign it under the closed TemplateID

    RECORD entry_stop_reason(MinerID) <- stop_reason           # I4: why the miner left ACTIVE_HASHING
    # F6: the LOW_POWER_LISTEN entry (and its P_hash/P_listen boundary + I17 recompute) is applied
    #     by the hook. For PATH A the source is EXHAUSTED_PENDING (already off H_active); for the
    #     other reasons the source is ACTIVE_HASHING (this is the H_active exit boundary).
    CALL ApplyMinerStateTransition(MinerID, from_state, LOW_POWER_LISTEN, now,
                                   reason = stop_reason, assignment_ref = assignment,
                                   candidate_ref = pause_cause_candidate_id)     # T8 / T26 / T27 / T28 / T29
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
    # F4: choose the CORRECT provenance. A fresh never-assigned range is ORIGINAL; a previously
    #     assigned unsearched suffix is REASSIGNED (source + reason + full I9 provenance). A
    #     reassignable suffix is NEVER labelled ORIGINAL.
    IF candidate_range is a fresh never-assigned range:
      origin <- ORIGINAL   ; source <- null                         ; reason <- null
    ELSE:
      origin <- REASSIGNED ; source <- source_assignment(candidate_range) ; reason <- security_recovery
    # F4: the shared constructor performs the I1/I10 overlap guard, ledgers the PENDING version, and
    #     sets custody_status + previous_assignment_reference + provenance from origin. Activation to
    #     CURRENT happens ONLY at the scheduled WakeCompleteEvent on a successful wake (E4/F5).
    assignment <- CALL CreatePendingAssignment(RoundContext, reserve_miner, candidate_range,
                    assignment_origin = origin, source_assignment = source, reason = reason)
    SET lease_start(assignment)  <- now
    SET lease_expiry(assignment) <- now + default_lease_duration
    # F5/D2: activation ALWAYS passes through WAKING via the NON-BLOCKING StartWake (T4). PENDING ->
    #        CURRENT and the wake-failure release both occur in WakeCompleteEvent, so several reserve
    #        activations at the same instant wake independently.
    RETURN CALL StartWake(RoundContext, reserve_miner, target_assignment = assignment, from_state = RESERVE)   # T4
  RETURNS: activation_started
  NOTE: PENDING -> CURRENT occurs ONLY at the scheduled WakeCompleteEvent on a successful wake
        (E4/F5); a failed wake yields OFFLINE and WakeCompleteEvent releases the reserved range as
        inactive_unsearched (custody_status = abandoned). Reserve provenance distinguishes ORIGINAL
        from REASSIGNED (F4).
```

## 11. Wake completion

Wake completion is specified as the event-scheduled pair `StartWake` / `WakeCompleteEvent` in
**§0.10** (F5). The former synchronous `WakeComplete` is removed: no procedure performs a blocking
wake. All activation callers (`RangeAssign`, `ReserveActivate`, `RangeReassign`, `TemplateRefresh`,
`ResumeFromPause`) invoke `StartWake`, and the miner reaches `ACTIVE_HASHING` at its own scheduled
`WakeCompleteEvent`.

## 12. Range lease expiry

```
PROCEDURE RenewAssignment
  INPUTS: RoundContext, old_assignment, t
  PRECONDITIONS: miner_state(holder(old_assignment)) = ACTIVE_HASHING;
                 status(old_assignment) = CURRENT;
                 custody_status(range(old_assignment)) != completed;   # a completed range is not renewable
                 policy allows same-range renewal
  EFFECTS:
    # F7: atomic same-range renewal by IMMUTABLE VERSIONING. The old version is SUPERSEDED (kept
    #     immutable and snapshot-resolvable); a NEW CURRENT version is created on the SAME range.
    #     The identity of the old version is NEVER mutated in place.
    CREATE new version V2 WITH
        AssignmentID       = fresh id
        assignment_version = assignment_version(old_assignment) + 1
        lineage_id         = lineage_id(old_assignment)                 # SAME lineage
        MinerID            = MinerID(old_assignment)                    # SAME holder
        range              = range(old_assignment)                      # SAME range
        RoundID            = RoundID(old_assignment)                    # unchanged
        TemplateID         = TemplateID(old_assignment)                 # unchanged
        assignment_origin  = RENEWED
        custody_status     = renewed
        previous_assignment_reference = AssignmentID(old_assignment)
        COPIED actual_frontier / reported_frontier / accepted_frontier FROM old_assignment   # retained progress
        COPIED provenance FROM old_assignment                          # retained provenance
        lease_start = t ; lease_expiry = t + default_lease_duration
    # ATOMIC swap: supersede old and publish new CURRENT so exactly one version is CURRENT throughout.
    ATOMICALLY:
      SET status(old_assignment)        <- SUPERSEDED
      SET superseded_at(old_assignment) <- t
      APPEND V2 to assignment_ledger
      SET status(V2)                    <- CURRENT
    ASSERT exactly one version with status = CURRENT in lineage_id(V2)  # F7 lineage invariant
    # miner_state(holder) stays ACTIVE_HASHING; NO WAKING; the holder keeps hashing the SAME range.
  RETURNS: V2
  NOTE: The old version stays IMMUTABLE and resolvable (F7/E1): a SolutionEligibilitySnapshot taken
        under it resolves to that SUPERSEDED version, which was CURRENT at discovery and not revoked
        before discovery, so its already-discovered solution remains verifiable after renewal.

PROCEDURE LeaseExpiry
  INPUTS: RoundContext, assignment, time t
  PRECONDITIONS: t >= lease_expiry(assignment)   # the lease window elapsed; renewal not yet decided
  EFFECTS:
    # E9: DECIDE renewal BEFORE invalidating anything. A renewed assignment is NEVER invalidated and
    #     is NEVER routed through RangeReassign or WAKING -- the holder keeps hashing the SAME range.
    IF miner_state(holder) = ACTIVE_HASHING AND holder wishes to continue AND policy allows renewal:
      # ---- RENEWAL (same holder, same range, stays CURRENT; no wake cycle; E5/E9/F7) ----
      # F7: renewal is an ATOMIC immutable version swap; the old version is SUPERSEDED and a new
      #     CURRENT version is created on the SAME range with copied progress/provenance.
      RETURN renewed(CALL RenewAssignment(RoundContext, assignment, t))
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
    # F4: the shared constructor creates a PENDING REASSIGNED version: it performs the I1 overlap
    #     guard, ledgers the version, sets custody_status = reassigned, records
    #     previous_assignment_reference = source, and appends the I9 provenance (with prior_pc, I13).
    #     A reassignable suffix is therefore NEVER labelled ORIGINAL.
    assignment <- CALL CreatePendingAssignment(RoundContext, to_miner, unsearched_suffix,
                    assignment_origin = REASSIGNED,
                    source_assignment = source_assignment(unsearched_suffix), reason = reason)
    SET lease_start(assignment)  <- now
    SET lease_expiry(assignment) <- now + default_lease_duration
    # F5/D2: to_miner activation passes through WAKING via the NON-BLOCKING StartWake (T3/T4 -> T5).
    CALL StartWake(RoundContext, to_miner, target_assignment = assignment,
                   from_state = miner_state(to_miner))
    # CR4/C3: coverage uses I8a with ACCEPTED coverage; custody/provenance is tracked SEPARATELY as I8b.
    UPDATE assignment_ledger so the coverage partition still holds (I8a):
        accepted_searched + active_unsearched + inactive_unsearched = assigned_domain
    # I8b custody/lineage status is orthogonal and is NEVER an additive coverage term. The reassigned
    # suffix retains an INDEPENDENT coverage state (accepted_searched/active_unsearched/inactive_unsearched).
  RETURNS: provenance(assignment)   # the I9 reassignment record created by CreatePendingAssignment
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
  INPUTS: RoundContext, certificate, snapshot, CandidateID, PropagationID, verifying_MinerID
  PRECONDITIONS: round_state in {HASHING, SOLUTION_PROPAGATION, SECURITY_RECOVERY};
                 miner_state(verifying_MinerID) = ACTIVE_HASHING       # F2: a paused miner never re-verifies
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
      # PATH B: the recipient PAUSES ITS OWN assignment and enters LOW_POWER_LISTEN DIRECTLY.
      # F2: record THIS candidate as the pause cause so a later candidate-scoped failure resumes
      #     ONLY the miners paused by this candidate.
      CALL EnterLowPowerListen(RoundContext, verifying_MinerID, stop_reason = VALID_SOLUTION_VERIFIED,
                               pause_cause_candidate_id = CandidateID,
                               pause_cause_propagation_id = PropagationID)
      RETURN VERIFIED
    ELSE:
      RECORD false_early_stop_rejected(certificate)
      DO NOT terminate hashing; NO state transition              # I11 upheld
      RETURN REJECTED
  RETURNS: VERIFIED | REJECTED
  NOTE: Validation is against the discovery snapshot (E1). F2 multi-candidate policy: a miner
        verifies a certificate ONLY while ACTIVE_HASHING; once PAUSED it is not ACTIVE_HASHING, so a
        second candidate's CertificateArrival is ignored (§16c). Therefore a miner has AT MOST ONE
        pause cause at a time, and that pause cause is unambiguous.
```

## 16a. Resume after a paused (PATH B) stop

```
PROCEDURE ResumeFromPause
  INPUTS: RoundContext, MinerID, trigger, pause_cause_candidate_id
  PRECONDITIONS: miner_state(MinerID) = LOW_POWER_LISTEN with entry_stop_reason = VALID_SOLUTION_VERIFIED;
                 trigger in {REJECTED, BLOCK_UNAVAILABLE, PROPAGATION_TIMEOUT, NO_VALID_CANDIDATE};
                 # F2: resume ONLY because THIS miner's pause cause failed.
                 pause_cause_candidate_id(paused_assignment(MinerID)) = pause_cause_candidate_id;
                 the miner's assignment is PAUSED (retained_actual_frontier retained), NOT searched/exhausted
  EFFECTS:
    # CR-B1/F2: a paused PATH B assignment resumes because the SPECIFIC candidate that paused it
    # failed; it was never marked searched or completed, so no coverage was falsely credited.
    SET paused_assignment <- the miner's PAUSED assignment (paused_assignment_id)
    # F2: the miner is no longer paused by any candidate.
    CLEAR pause_cause_candidate_id(paused_assignment), pause_cause_propagation_id(paused_assignment)
    # F5/F6/D5: resume passes through WAKING via the NON-BLOCKING StartWake (T30). The paused
    #           assignment is the wake target; WakeCompleteEvent restores it to CURRENT from
    #           retained_actual_frontier (WAKING -> ACTIVE_HASHING, T5), recomputes H_active/I17 at
    #           the ACTIVE_HASHING boundary (via ApplyMinerStateTransition), and resumes hashing.
    RETURN CALL StartWake(RoundContext, MinerID, target_assignment = paused_assignment,
                          from_state = LOW_POWER_LISTEN)                        # T30
  RETURNS: resume_started(MinerID, resumed_from = retained_actual_frontier)
  NOTE: Resume applies ONLY to PATH B pauses whose pause_cause matches the FAILED candidate (F2). A
        PATH A exhausted range (coverage_state = searched, custody_status = completed) is NOT
        resumable. Resume is event-scheduled (F5); several miners resuming at the same instant wake
        independently. If instead the full block is ACCEPTED, the round closes (ROUND_ACCEPTED) and
        the paused assignment closes on round closure -- NOT by exhaustion.
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
PROCEDURE CreatePropagationContext
  INPUTS: RoundContext, certificate, snapshot, finder
  PRECONDITIONS: certificate self-validated (SelfValidateFoundSolution ok)
  EFFECTS:
    # F1: mint IMMUTABLE unique identifiers and build the candidate's propagation context.
    SET CandidateID   <- fresh globally-unique id (immutable)
    SET PropagationID <- fresh globally-unique id (immutable)
    CREATE cpc = CandidatePropagationContext WITH
        CandidateID, PropagationID, RoundID = certificate.RoundID, TemplateID = certificate.TemplateID,
        certificate, snapshot, finder_MinerID = finder, discovery_time = snapshot.discovery_time,
        certificate_arrival_events = empty, block_arrival_event = null,
        acceptance_timestamp = null, status = SELF_VALIDATED, failure_reason = null
    RETURN cpc
  RETURNS: cpc

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
    # F1: build the candidate's immutable propagation context (fresh CandidateID/PropagationID).
    cpc <- CALL CreatePropagationContext(RoundContext, certificate, snapshot, finder)
    # F3: register the live context. The round is SOLUTION_PROPAGATION iff active_propagation_set
    #     is non-empty; entering the FIRST live context performs HASHING -> SOLUTION_PROPAGATION (E6).
    SET was_empty <- (active_propagation_set is empty)
    ADD cpc to active_propagation_set
    SET status(cpc) <- PROPAGATING
    IF was_empty AND round_state = HASHING: TRANSITION round_state -> SOLUTION_PROPAGATION
    # C6/F1: (3) schedule per-recipient certificate-arrival events; every event carries CandidateID/PropagationID.
    FOR EACH recipient r in current miners, r != finder:
      cert_delay(r) <- deterministic modeled propagation delay(finder -> r)   # reproducible
      ev <- SCHEDULE event CertificateArrival(RoundContext, r, cpc.certificate, cpc.snapshot,
                                              CandidateID = cpc.CandidateID, PropagationID = cpc.PropagationID)
                          AT now + cert_delay(r)
      ADD ev to certificate_arrival_events(cpc)
    # (4) schedule the full-block acceptance event toward the modeled acceptance point (carries the ids).
    block_delay <- deterministic modeled propagation delay(finder -> acceptance_point)  # reproducible
    SET block_arrival_event(cpc) <- SCHEDULE event BlockAcceptancePoint(RoundContext, cpc.certificate,
                          cpc.snapshot, CandidateID = cpc.CandidateID, PropagationID = cpc.PropagationID,
                          outcome = outcome-at-arrival) AT now + block_delay
    SET status(cpc) <- PENDING_ACCEPTANCE
    # (5) the finder ceases hashing (PATH B, resumable) via the canonical disposition, recording THIS
    #     candidate as its pause cause (F2); it does NOT pass through EXHAUSTED_PENDING.
    CALL EnterLowPowerListen(RoundContext, finder, stop_reason = VALID_SOLUTION_VERIFIED,
                             pause_cause_candidate_id = cpc.CandidateID,
                             pause_cause_propagation_id = cpc.PropagationID)
  RETURNS: cpc.CandidateID
  NOTE: The discrete-event queue orders arrivals; no global set of future solutions is consulted.
        Do NOT call ValidBlockAccept here. Unpaused miners may keep hashing during
        SOLUTION_PROPAGATION and may discover FURTHER candidates, each of which gets its OWN
        CandidatePropagationContext added to active_propagation_set (E6/F1/F3).
```

## 16c. Certificate arrival at a recipient (C6)

```
PROCEDURE CertificateArrival
  INPUTS: RoundContext, recipient r, certificate, snapshot, CandidateID, PropagationID
  PRECONDITIONS: this is the scheduled certificate-arrival event for r (carries CandidateID/PropagationID, F1);
                 the context CandidateID is still live (not FAILED/ACCEPTED/CANCELLED)
  EFFECTS:
    # F2/F3: ignore an arrival whose candidate is no longer live (its events may have been cancelled).
    IF status(context(CandidateID)) not in {PROPAGATING, PENDING_ACCEPTANCE}:
      RETURN ignored_stale_candidate
    # (6) the recipient stays ACTIVE_HASHING until its certificate-arrival event fully validates.
    #     E1/E2: verification is against the finder's immutable discovery snapshot, carried on the event.
    IF miner_state(r) = ACTIVE_HASHING:
      result <- CALL EarlyStopVerify(RoundContext, certificate, snapshot,
                                     CandidateID, PropagationID, verifying_MinerID = r)
      # (7) on VERIFIED, EarlyStopVerify pauses r into LOW_POWER_LISTEN recording THIS candidate as
      #     the pause cause (F2). On REJECTED, r stays ACTIVE_HASHING and keeps hashing (I11).
    ELSE:
      IGNORE                                                     # F2: r not ACTIVE_HASHING (already paused by some candidate)
  RETURNS: verify_result
```

## 16d. Block acceptance point (C6)

```
PROCEDURE BlockAcceptancePoint
  INPUTS: RoundContext, certificate, snapshot, CandidateID, PropagationID, outcome
  PRECONDITIONS: this is the scheduled full-block arrival event at the MODELED ACCEPTANCE POINT
                 for CandidateID (F1); outcome in {ACCEPTED_CANDIDATE, REJECTED, BLOCK_UNAVAILABLE,
                 PROPAGATION_TIMEOUT}
  EFFECTS:
    # F2/F3: ignore an arrival whose candidate is no longer live (already ACCEPTED/FAILED/CANCELLED).
    IF status(context(CandidateID)) not in {PROPAGATING, PENDING_ACCEPTANCE}:
      RETURN ignored_stale_candidate
    SET acceptance_timestamp(context(CandidateID)) <- now
    # C6: the modeled acceptance point is EITHER a designated coordinator/validator OR a clearly
    #     identified canonical local view (RoundContext.acceptance_point_policy).
    IF outcome = ACCEPTED_CANDIDATE:
      # D6: batch EXACT-same-timestamp candidates BEFORE accepting; this candidate joins the batch
      #     for the current acceptance timestamp (each batched candidate carries its own ids/cert/snapshot).
      RETURN CALL AcceptanceTimestampBatch(RoundContext, acceptance_timestamp = now)
    ELSE:
      # E3/D5/F2: REJECTED / BLOCK_UNAVAILABLE / PROPAGATION_TIMEOUT -> the CANDIDATE-SCOPED
      #           failure-recovery path (resumes ONLY miners paused by THIS candidate).
      RETURN CALL HandlePropagationFailure(RoundContext, CandidateID, PropagationID, failure_reason = outcome)
  RETURNS: accepted_block | resume_scheduled | ignored_stale_candidate
  NOTE: A strictly-earlier full-block arrival wins by discrete-event queue order; EXACT-timestamp
        ties are arbitrated by AcceptanceTimestampBatch. No event inspects unknown future timestamps.
        Every non-acceptance outcome funnels through the candidate-scoped HandlePropagationFailure
        (E3/F2), which resumes ONLY the miners paused by THIS candidate.
```

## 16d-bis. Propagation-failure recovery (E3)

```
PROCEDURE HandlePropagationFailure
  INPUTS: RoundContext, CandidateID, PropagationID, failure_reason
  PRECONDITIONS: failure_reason in {REJECTED, BLOCK_UNAVAILABLE, PROPAGATION_TIMEOUT, NO_VALID_CANDIDATE};
                 CandidateID identifies a live context (status in {PROPAGATING, PENDING_ACCEPTANCE})
  EFFECTS:
    SET cpc <- context(CandidateID)
    # E3/F2/F3: fail ONLY this candidate. This procedure NEVER touches another candidate's context,
    #           events, or paused miners, and NEVER accepts a block or closes the round.
    SET status(cpc)         <- FAILED
    SET failure_reason(cpc) <- failure_reason
    RECORD propagation_failure(RoundID, TemplateID, CandidateID, PropagationID, failure_reason)
    REMOVE cpc from active_propagation_set                          # F3: ONLY this candidate leaves the set
    # (1) cancel ONLY this candidate's obsolete events (F2): its per-recipient certificate-arrival
    #     events and its block-arrival event. Another candidate's events are NEVER cancelled here.
    CANCEL every event in certificate_arrival_events(cpc)
    CANCEL block_arrival_event(cpc)
    # (2) resume ONLY miners whose pause cause is THIS candidate (F2). A miner paused by another
    #     live candidate, or with no matching pause cause, is left unchanged.
    FOR EACH miner M with a PAUSED assignment AND
             pause_cause_candidate_id(paused_assignment(M)) = CandidateID:
      SCHEDULE event ResumeFromPause(RoundContext, M, trigger = failure_reason,
                                     pause_cause_candidate_id = CandidateID)   # candidate-scoped resume (F2)
    # (3) round-state rule (F3): evaluate the security floor, then decide the round state.
    breach <- CALL SecurityFloorEvaluate(RoundContext, latest (H_active, H_honest, q_adv), floor_state)
    IF breach:
      # F3 defined rule: a floor breach moves the round to SECURITY_RECOVERY and PRESERVES the
      #     remaining live candidate contexts in active_propagation_set; on recovery the round
      #     returns to SOLUTION_PROPAGATION if the set is still non-empty, else to HASHING.
      ENSURE round_state = SECURITY_RECOVERY                        # SecurityFloorEvaluate performed the transition
    ELSE IF round_state = SOLUTION_PROPAGATION AND propagation_quiescent(RoundContext):
      # F3: return to HASHING ONLY when propagation is FULLY quiescent (no block accepted, set empty,
      #     no same-timestamp acceptance batch pending, no live candidate-specific acceptance event).
      TRANSITION round_state -> HASHING
    # ELSE: the round STAYS SOLUTION_PROPAGATION because other candidates are still live (F3).
    RETURN candidate_failed(CandidateID)
  RETURNS: candidate_failed
  NOTE: Candidate-scoped (F2/F3). One candidate's failure NEVER cancels or resumes another
        candidate's certificate-arrival, block-arrival, acceptance-batch, or timeout events, and
        NEVER resumes a miner paused by a different live candidate. The round remains
        SOLUTION_PROPAGATION while any live candidate exists (F3). `propagation_quiescent` is
        defined in §0.6. No block is accepted and no round is closed here.
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
    # D6/F1: (1) gather ALL same-acceptance-point candidate events with EXACTLY this timestamp. Each
    #     event carries its own CandidateID/PropagationID/certificate/snapshot (E1/E2/F1).
    batch <- all ACCEPTED_CANDIDATE BlockAcceptancePoint events at this acceptance point with
             timestamp = acceptance_timestamp   # each event c has c.CandidateID, c.certificate, c.snapshot
    # (2)-(3) validate every candidate against ITS OWN discovery snapshot; discard invalid.
    valid <- empty
    FOR EACH candidate event c in batch:
      IF CALL ValidateCandidate(RoundContext, c.certificate, c.snapshot): APPEND c to valid   # E1/E2
    IF valid is empty:
      # E3/F2: no valid candidate -> fail EACH batched candidate INDIVIDUALLY (candidate-scoped), so
      #        each resumes ONLY its own paused miners. No cross-candidate cancellation occurs.
      FOR EACH candidate event c in batch:
        CALL HandlePropagationFailure(RoundContext, c.CandidateID, c.PropagationID,
                                      failure_reason = NO_VALID_CANDIDATE)
      RETURN no_valid_candidate
    # (4) among valid candidates choose smallest candidate_hash, then smallest MinerID (F8 deterministic).
    winner <- argmin over valid of (c.certificate.candidate_hash, then c.certificate.MinerID)
    # (5) the losing same-timestamp valid candidates become COMPETING (their contexts are handled by
    #     ValidBlockAccept, which cancels ALL non-winner live contexts and closes the round once, F3).
    FOR EACH c in valid, c != winner: SET status(context(c.CandidateID)) <- COMPETING
    # (6) ONLY AFTER arbitration finishes: accept + close (no round closure occurs before this).
    RETURN CALL ValidBlockAccept(RoundContext, winner.CandidateID, winner.certificate, winner.snapshot)
  RETURNS: accepted_block | not_selected | no_valid_candidate
  NOTE: For DIFFERENT timestamps the earliest timestamp wins by discrete-event queue order; this
        procedure arbitrates ONLY exact-timestamp ties (F8 tie-break: candidate_hash then MinerID).
        An empty valid batch fails each batched candidate candidate-scoped (E3/F2), not as one
        blanket failure. No round closure occurs before same-timestamp arbitration completes.
```

## 17. Valid block acceptance

```
PROCEDURE ValidBlockAccept
  INPUTS: RoundContext, winner_CandidateID, winner_certificate, winner_snapshot
  PRECONDITIONS: invoked ONLY from AcceptanceTimestampBatch after arbitration (D6);
                 winner_certificate already validated by ValidateCandidate against winner_snapshot
                 and chosen as the batch winner;
                 # E6: the round entered SOLUTION_PROPAGATION at the FIRST valid found-solution.
                 round_state = SOLUTION_PROPAGATION
  EFFECTS:
    # F3: close the round EXACTLY ONCE. A second entry (a later same-round acceptance) is a no-op.
    IF a block has ALREADY been accepted this round:
      SET status(context(winner_CandidateID)) <- COMPETING       # a strictly-earlier timestamp already won
      RETURN not_selected
    RECORD accepted_block(winner_certificate)
    SET status(context(winner_CandidateID)) <- ACCEPTED
    # F3: mark EVERY OTHER live context stale/cancelled and cancel THEIR remaining events. The winner
    #     is excluded. This is the ONE place cross-candidate cancellation is legitimate (acceptance).
    FOR EACH other cpc in active_propagation_set, other.CandidateID != winner_CandidateID:
      SET status(other) <- (other was a same-timestamp valid loser ? COMPETING : CANCELLED)
      CANCEL every event in certificate_arrival_events(other)
      CANCEL block_arrival_event(other)
    CLEAR active_propagation_set                                  # no live candidate remains after acceptance
    # E6: a SINGLE transition; the round is already in SOLUTION_PROPAGATION (no double transition).
    TRANSITION round_state -> ROUND_ACCEPTED
    # D7: centralised round closure (the SINGLE closure path); paused miners of cancelled candidates
    #     are closed by round closure (ROUND_ACCEPTED), NOT resumed.
    CALL CloseRoundAssignments(RoundContext, disposition = ROUND_ACCEPTED, stop_reason = ROUND_ACCEPTED)
  RETURNS: accepted_block | not_selected
  NOTE: F3: acceptance of one candidate sets it ACCEPTED, marks all other live candidates
        COMPETING/STALE/CANCELLED, cancels their remaining events, and closes the round EXACTLY
        ONCE. Miners paused by a cancelled candidate are NOT resumed (the round ended); they close
        with stop_reason = ROUND_ACCEPTED via CloseRoundAssignments. No chain-wide fork-choice proof
        is claimed.
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
          CALL ApplyMinerStateTransition(h, EXHAUSTED_PENDING, LOW_POWER_LISTEN, now,
                 reason = RANGE_EXHAUSTED, assignment_ref = X, candidate_ref = null)   # T8; RANGE_EXHAUSTED NOT overwritten

        CASE LOW_POWER_LISTEN:
          # already parked (PATH-A RANGE_EXHAUSTED, PATH-B VALID_SOLUTION_VERIFIED, or ASSIGNMENT_REVOKED).
          ASSERT entry_stop_reason(h) in {RANGE_EXHAUSTED, VALID_SOLUTION_VERIFIED, ASSIGNMENT_REVOKED}
          CLOSE X as round-ended                                 # a PATH-B PAUSED assignment is NOT resumed
          # miner_state(h) stays LOW_POWER_LISTEN; entry_stop_reason(h) unchanged (E7); no transition

        CASE WAKING:
          # a pending activation: cancel it; the miner never reaches ACTIVE_HASHING for this round.
          # F6/F8: WAKING -> LOW_POWER_LISTEN is ILLEGAL (miner SM §3.1); the legal closure edge is
          #        WAKING -> OFFLINE (T12), which also prevents activation into a closed round (TV37).
          CANCEL the pending WakeCompleteEvent for h
          CLOSE X as round-ended                                 # bound PENDING assignment left un-activated
          CALL ApplyMinerStateTransition(h, WAKING, OFFLINE, now, reason = round_closed_while_waking,
                 assignment_ref = X, candidate_ref = null)       # T12 (legal); miner rejoins next round via T17

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
          CALL ApplyMinerStateTransition(h, EXHAUSTED_PENDING, LOW_POWER_LISTEN, now,
                 reason = RANGE_EXHAUSTED, assignment_ref = X, candidate_ref = null)     # T8 (F6)
        CASE LOW_POWER_LISTEN:
          # a PAUSED PATH-B assignment is CLOSED (it is NOT resumed under a discarded template).
          CLOSE X
          # miner_state(h) stays LOW_POWER_LISTEN; entry_stop_reason(h) unchanged; no transition
        CASE WAKING:
          # the bound assignment is on the discarded template -> fails TemplateID validation (legal T12).
          CANCEL the pending WakeCompleteEvent for h ; release the bound range
          CALL ApplyMinerStateTransition(h, WAKING, OFFLINE, now, reason = template_refresh_wake_abort,
                 assignment_ref = X, candidate_ref = null)                               # T12 (F6)
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
      # E8-(6)/F4: a FRESH ORIGINAL assignment over the NEW domain via the shared constructor
      #            (I1 guard + ledger + custody_status = original + previous_assignment_reference = null).
      assignment_m <- CALL CreatePendingAssignment(RoundContext, m, fresh_range(m),
                        assignment_origin = ORIGINAL, source_assignment = null, reason = null)
      SET lease_start(assignment_m)  <- now
      SET lease_expiry(assignment_m) <- now + default_lease_duration
      # E8-(7)/F5: the LEGAL per-source edge into WAKING (T3 REGISTERED / T4 RESERVE / T10
      #            LOW_POWER_LISTEN) is performed by the NON-BLOCKING StartWake; PENDING -> CURRENT
      #            happens at each miner's own WakeCompleteEvent (T5), so activations wake in parallel.
      CALL StartWake(RoundContext, m, target_assignment = assignment_m, from_state = miner_state(m))
      # do NOT call RangeReassign for old ranges; do NOT rebind old assignments to new_TemplateID
    ASSERT difficulty unchanged                                 # I12
    # E8-(9)/F5: the intended assignment set is now valid (every eligible miner has a bound PENDING
    #            assignment on the new domain and its wake is scheduled). START the new mining phase
    #            EXPLICITLY; miners reach ACTIVE_HASHING at their own later WakeCompleteEvents, never
    #            before the round is HASHING (§3.2).
    ASSERT round_state = ASSIGNMENT
    TRANSITION round_state -> HASHING                           # E8: explicit ASSIGNMENT -> HASHING (R4)
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
3. **StartWake** — the wake latency draw (F5). The draw now lives in `StartWake`; the scheduled
   `WakeCompleteEvent` consumes it deterministically at the completion timestamp. Every activation
   caller (`RangeAssign`, `ReserveActivate`, `RangeReassign`, `TemplateRefresh`, `ResumeFromPause`)
   reaches this single draw through `StartWake`.
4. **ExhaustionAdjudicate** and **FullRangeExhaustNoSolution** — the adversarial-path audit selection
   (`audit_selection_model`) that decides whether a `reported_exhaustion` claim is audited
   against simulator ground truth (`actual_exhaustion`). This is the modeled audit/detection
   abstraction of CR5; the comparison itself (`audit_result`, `claim_accepted_or_rejected`) is
   deterministic once the audit is selected.

The Stage-1F procedures add **no** new sampling site. `ApplyMinerStateTransition` (F6),
`WakeCompleteEvent` (F5), `CreatePendingAssignment` (F4), `CreatePropagationContext` (F1),
`HandlePropagationFailure` (E3/F2/F3), `RenewAssignment` (F7), the acceptance cluster (E6/F3), and
the whole event-priority contract (F8) are entirely deterministic protocol logic. The discrete-event
queue order, the same-timestamp priority table, and the tie-breaks (`candidate_hash` then `MinerID`
for acceptance; `(CandidateID, MinerID, AssignmentID, seq)` within an event type) contain **no**
random draw and are independent of data-structure iteration order.

Every other step is deterministic protocol logic. This separation is deliberate: it keeps the
protocol's decision logic reproducible and audit-checkable against `I1..I17`, while confining
all randomness to clearly labelled model draws that exist solely because Stage-1 evaluation is
a simulation and not a real deployment. None of the above is executable source.

---

## 21. Global event-priority contract (F8)

When two or more scheduled events carry the **exact same** `event_time`, they are processed in a
**deterministic** order fixed by the global event-priority contract (F8). The complete priority
table, the per-pair race resolutions, and the required-race walkthroughs are in
`STAGE_01F_EVENT_PRIORITY_TABLE.md`; that document is normative and this section binds to it.

The contract has two levels:

1. **Inter-type priority.** Same-timestamp events of different types fire in this fixed order
   (highest first), so that no event ever acts on a round/miner/assignment that a
   higher-priority same-timestamp event has already invalidated:

       1  RoundAbort closure            (ROUND_ABORTED)
       2  Round-acceptance closure      (ValidBlockAccept -> ROUND_ACCEPTED)
       3  Same-timestamp acceptance arbitration (AcceptanceTimestampBatch)
       4  Template invalidation / refresh (TemplateRefresh / CloseTemplateAssignments)
       5  Security-floor evaluation / breach (SecurityFloorEvaluate)
       6  Full-block arrival            (BlockAcceptancePoint)
       7  Certificate arrival           (CertificateArrival)
       8  Solution discovery            (ActiveHashing hit -> ScheduleSolutionPropagation)
       9  Range completion              (ActualRangeCompletion / ExhaustionAdjudicate)
      10  Reported exhaustion           (ReportedExhaustionClaim)
      11  Lease expiry                  (LeaseExpiry)
      12  Wake completion               (WakeCompleteEvent)
      13  Resume-from-pause             (ResumeFromPause)
      14  Periodic monitoring           (ActiveHashRateUpdate / heartbeat)

2. **Intra-type tie-break.** Events of the SAME type at the SAME timestamp are ordered by
   `(CandidateID, MinerID, AssignmentID, seq)` lexicographically, where `seq` is the monotonic
   creation counter of the event envelope (§0.2). Acceptance arbitration additionally uses the
   value tie-break `candidate_hash` then `MinerID` (D6). No ordering ever depends on
   data-structure iteration order, so the processing order is identical across reruns (F8).

Consequences enforced by this order (see the table for the full list): a full-block arrival that
shares a timestamp with a round closure is processed **after** the closure and finds the round
already closed (so it cannot accept into a closed round); a `WakeCompleteEvent` sharing a timestamp
with round acceptance is processed **after** the closure and, per `CloseRoundAssignments`, the
waking miner was already moved to `OFFLINE` (T12), so it never activates into a closed round;
solution discovery sharing a timestamp with a lease expiry is processed **after** the lease-expiry
decision, so the discovery is evaluated against the assignment version the priority order has
established. `ValidateCandidate` still resolves each certificate against its immutable discovery
snapshot (E1), so these orderings change *which event acts first*, never *whether a validly
discovered solution stays valid*.
