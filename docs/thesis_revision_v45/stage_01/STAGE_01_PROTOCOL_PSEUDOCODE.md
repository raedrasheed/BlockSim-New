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

## 0. Concurrency and discrete-event model (Stage 1F, refined in Stage 1G)

Stage-1F made the concurrency and discrete-event semantics of PoCol explicit; **Stage 1G refines
them for causal consistency and determinism**. The normative rules below govern the whole
specification; every procedure conforms to them. Where a Stage-1G rule amends a Stage-1F rule, the
Stage-1G form is authoritative.

**(0.1) Single-threaded discrete-event loop.** The simulator advances one global discrete-event
queue. Each event fires at a definite `event_time`; a handler runs to completion without
preemption. A long-latency physical process (wake ramp, message propagation) is NEVER executed by
a blocking call that occupies the loop; it is represented by SCHEDULING a future event (F5).
Concurrency is modeled by many independent future events, not by parallel handlers, so two miners
"doing something at once" are two independently scheduled events, each firing at its own timestamp.

**(0.2) Event envelope (F1, extended with `delta_cycle` and `microphase` in H2).** Every scheduled
event carries an immutable envelope:

    { event_type, event_time, delta_cycle, microphase, RoundID, TemplateID,
      CandidateID?, PropagationID?, MinerID?, AssignmentID?, assignment_version?, seq }

`CandidateID` and `PropagationID` are REQUIRED on every certificate-arrival, block-arrival,
validation, timeout, cancellation, and resume event. `microphase` is the target microphase (§0.7);
`delta_cycle` is the causal generation within one `event_time` (H2). Events are ordered by the total
key `(event_time, delta_cycle, microphase, stable_tie_key, seq)`, where `stable_tie_key =
(CandidateID, MinerID, AssignmentID)` and `seq` is a strictly monotonic per-run creation counter used
ONLY as the final deterministic tie-break. A propagation context is NEVER identified by `RoundID`
alone.

**(0.3) Central miner-state hook (F6).** No procedure mutates `miner_state` directly. Every
miner-state change is performed by `ApplyMinerStateTransition`, the SOLE owner of residency
accounting, one-shot transition energy, the `H_active = H_honest + H_adversarial` recompute
(I17), `q_adv`/NA, and security-floor scheduling. The keyword `TRANSITION miner_state(...)` does
not appear in any procedure; a state change is always written `CALL ApplyMinerStateTransition(...)`.

**(0.4) Event-scheduled wake (F5).** Every activation into `ACTIVE_HASHING` passes through
`StartWake` (non-blocking) and its scheduled `WakeCompleteEvent`. Miners starting to wake at the
same instant wake independently on their own completion timestamps; no wake serialises another.

**(0.5) Immutable assignment versions (F7, corrected in G2).** An assignment is an immutable
versioned object. Renewal creates a NEW version and SUPERSEDES the old one, linearised atomically at
`renewal_time`. The lineage invariants are **I18a** (`count(status = CURRENT) <= 1` per lineage at
every observable time) and **I18b** (every OPEN lineage has exactly one live head in
`{PENDING, CURRENT, PAUSED}`; a CLOSED lineage has zero live heads). ZERO `CURRENT` versions is legal
while the unique live head is `PENDING` or `PAUSED`, and after closure. A `SolutionEligibilitySnapshot`
resolves to the exact immutable version that was `CURRENT` at discovery, so a solution discovered
under an old version stays verifiable after renewal even once that version is `SUPERSEDED` or `PAUSED`.

**(0.5g) Discovery-time acceptance eligibility (G1).** Acceptance binds to the immutable version that
was VALID and `CURRENT` at the solution's `discovery_time` (invariant **I2**, corrected). The
assignment need NOT remain `CURRENT` at certificate or block arrival; it may later be `PAUSED` or
`SUPERSEDED`. No procedure uses "CURRENT at acceptance" semantics.

**(0.6) Active propagation set (F3, refined in G6).** `active_propagation_set` holds exactly the
contexts whose `status ∈ {PROPAGATING, PENDING_ACCEPTANCE}` — the **propagation-active** contexts.
`DISCOVERED` and `SELF_VALIDATED` contexts exist but are NOT yet propagation-active (they have not
been added to the set). A context leaves the set on `FAILED` (candidate-scoped failure) or on round
acceptance (`ACCEPTED`/`COMPETING`/`STALE`/`CANCELLED`). "A live candidate exists" means a
propagation-active context exists. The predicate

    propagation_quiescent(RoundContext) :=
        active_propagation_set is empty
        AND acceptance_batch_registry has no pending batch for any acceptance timestamp
        AND no live candidate-specific CertificateArrival / BlockAcceptancePoint event remains
        AND block_accepted flag is false

is the ONLY condition under which the round returns to `HASHING` (from `SOLUTION_PROPAGATION`, or
from `SECURITY_RECOVERY` once the floor is restored). Failure of one candidate removes only that
candidate; the round stays in propagation while any other candidate is live. **The round-state and
the propagation set are NOT identified**: `SECURITY_RECOVERY` may coexist with a non-empty
`active_propagation_set` (G8), and there is no "iff" forbidding that coexistence.

**(0.7) Timestamp microphase contract (authoritative: `STAGE_01G_EVENT_MICROPHASE_SPEC.md`; extended
in H2).** At each `event_time` the loop processes events in explicit **microphases**: PHASE 1 terminal
abort / previously-committed closure; PHASE 2 template invalidation/refresh; PHASE 3 collect ALL
full-block arrivals into `acceptance_batch_registry` (each `BlockAcceptancePoint` only REGISTERS and
returns); PHASE 4 run `AcceptanceBatchFinalize` exactly once per (timestamp, acceptance point) —
validate all collected candidates, select a winner, commit acceptance and close the round ATOMICALLY;
PHASE 5 the SINGLE settled-census security evaluation (`FinalizeTimestampSecurityCensus` →
`SecurityFloorEvaluate`, H3, terminal/source-guarded, G10/H4); PHASE 6+ certificate arrivals,
solution-discovery, range completion, reported exhaustion, lease expiry, wake completion, resume,
periodic monitoring. Round-acceptance closure is the atomic result of `AcceptanceBatchFinalize`, not
an independent preceding event. **The authoritative same-timestamp contract is
`STAGE_01G_EVENT_MICROPHASE_SPEC.md`, extended by the H2 delta-cycle rule below; the frozen Stage-1F
`STAGE_01F_EVENT_PRIORITY_TABLE.md` is NOT authoritative.**

**(0.7-H2) Delta-cycle scheduling (no backward travel within a timestamp).** A handler running in
microphase `m` of `(event_time, delta_cycle = k)` may create same-`event_time` events; to keep
scheduling CAUSALLY FORWARD it obeys:
  1. an event whose target `microphase > m` is scheduled in the CURRENT `delta_cycle = k`;
  2. an event whose target `microphase <= m` (same or earlier microphase) is scheduled in
     `delta_cycle = k + 1` (never backward into a phase of cycle `k`);
  3. the loop completes ALL microphases of `delta_cycle k` before processing any event of
     `delta_cycle k + 1` at the same `event_time`;
  4. no event may travel backward into a completed `delta_cycle`.
This rule governs, in particular: `FinalizeTimestampSecurityCensus`/`SecurityFloorEvaluate` scheduled
from miner transitions (H3); a zero-latency `WakeCompleteEvent` (H5); `ResumeFromPause`; candidate-
failure cleanup (`HandlePropagationFailure` and its scheduled resumes); and ANY same-`event_time`
event created inside another handler. The full contract, worked examples, and the required-race table
are in `STAGE_01H_DELTA_CYCLE_CONTRACT.md`. Within a microphase, ties break by
`(CandidateID, MinerID, AssignmentID, seq)`, NEVER by data-structure iteration order.

**(0.7a) Deterministic identifiers and iteration (G7).** `CandidateID` and `PropagationID` are
DETERMINISTIC, not random: `CandidateID = (RoundID, candidate_discovery_seq)` and
`PropagationID = (CandidateID, propagation_attempt_seq)`, where the seqs are monotonic per-scope
counters advanced in deterministic order. Every loop that creates, cancels, or schedules events
iterates in a STABLE sorted order over intrinsic keys (`MinerID`, `CandidateID`, `AssignmentID`,
`assignment_version`); the event-envelope `seq` is assigned ONLY after that deterministic order is
established. The resulting queue order is independent of any hash-map / set iteration order and is
identical across reruns with the same seeds and inputs.

**(0.7b) Event-scheduled hashing (G9).** Hashing is modeled by discrete `HashWorkEvent`s
(`StartHashing` / `HashWorkEvent` / `ScheduleNextHashWork`), NOT by a blocking `WHILE` loop. Each
`HashWorkEvent` evaluates one candidate position or one explicitly bounded chunk, records hash-work
METADATA only, may emit a candidate or range-completion event, then schedules the next `HashWorkEvent`
and returns to the loop. It does **not** increment any state-residency time: `t_ACTIVE_HASHING =
t_hash` is owned SOLELY by `ApplyMinerStateTransition`'s `residency_ledger` and is computed once when
the `ACTIVE_HASHING` interval is closed at its boundary (H7/I19), never accumulated per hash unit. A
pending `HashWorkEvent` becomes a no-op (or is cancelled) once its miner is no longer `ACTIVE_HASHING`
or its exact assignment version is no longer `CURRENT`.

**(0.7c) Terminal-round security guard (G10).** `SecurityFloorEvaluate` is always SCHEDULED (never
called inline) and carries `(RoundID, TemplateID, state_version)`. It returns `stale_noop` — never
transitioning to `SECURITY_RECOVERY` — when the round is already `ROUND_ACCEPTED`/`ROUND_ABORTED` or
the evaluation belongs to a stale `RoundID`/`TemplateID`/`state_version`.

### 0.8 Core data model (Stage 1F)

```
STRUCTURE CandidatePropagationContext (CPC)   # F1: one per discovered candidate solution; immutable identity
  CandidateID                 : DETERMINISTIC id = (RoundID, candidate_discovery_seq)   # G7, immutable
  PropagationID               : DETERMINISTIC id = (CandidateID, propagation_attempt_seq)  # G7, immutable
  RoundID, TemplateID
  certificate                 : signed early-stop certificate (EarlyStopGenerate)
  snapshot                    : SolutionEligibilitySnapshot (immutable, discovery-time)
  finder_MinerID
  discovery_time
  certificate_arrival_events  : set of scheduled per-recipient events (each carries CandidateID/PropagationID)
  block_arrival_event         : the scheduled BlockAcceptancePoint event (carries CandidateID/PropagationID)
  acceptance_timestamp        : set when a block-arrival with outcome ACCEPTED_CANDIDATE registers (else null)
  status                      : one of the candidate statuses below
  failure_reason              : one of {REJECTED, BLOCK_UNAVAILABLE, PROPAGATION_TIMEOUT, NO_VALID_CANDIDATE} or null

# candidate status enum (mutually exclusive). Every status is REACHABLE (G6):
#   CreatePropagationContext -> DISCOVERED
#   after SelfValidateFoundSolution ok -> SELF_VALIDATED
#   added to active_propagation_set + events scheduled -> PROPAGATING
#   block-arrival registered at the acceptance point -> PENDING_ACCEPTANCE
#   AcceptanceBatchFinalize winner -> ACCEPTED ; candidate-scoped failure -> FAILED
#   other live contexts on another candidate's acceptance -> COMPETING / STALE / CANCELLED
CANDIDATE_STATUS in {DISCOVERED, SELF_VALIDATED, PROPAGATING, PENDING_ACCEPTANCE,
                     FAILED, ACCEPTED, COMPETING, STALE, CANCELLED}
# active_propagation_set membership (G6) = { cpc : status(cpc) in {PROPAGATING, PENDING_ACCEPTANCE} }

STRUCTURE RoundContext registries (initialised by RoundInitialise, cleared on closure; G8)
  active_propagation_set      : set of propagation-active CPCs (status PROPAGATING/PENDING_ACCEPTANCE)
  acceptance_batch_registry   : map (acceptance_timestamp, acceptance_point) -> list of registered block arrivals
  candidate_discovery_seq     : monotonic per-round counter for CandidateID (G7)
  block_accepted              : boolean flag, false until a block is accepted this round
  state_version               : monotonic round-state epoch, bumped on every round-state transition (G10)
  security_evaluation_required : per (event_time, delta_cycle) boolean flag set by ApplyMinerStateTransition
                                 when a miner-state boundary changed the ACTIVE_HASHING census (H3); cleared
                                 by FinalizeTimestampSecurityCensus. NO per-transition floor decision is scheduled.
  residency_ledger            : the SOLE owner of every per-miner state-residency duration t_<state>,
                                 including t_ACTIVE_HASHING = t_hash (H7). Only ApplyMinerStateTransition
                                 opens/closes residency intervals; no other procedure increments a t_<state>.

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

# G2 lineage invariants (replacing the impossible "exactly one CURRENT at every instant"):
INVARIANT I18a: for each lineage_id, count(versions with status = CURRENT) <= 1 at all observable times.
INVARIANT I18b: for each OPEN lineage_id, EXACTLY ONE live head exists in {PENDING, CURRENT, PAUSED};
                after lineage closure, ZERO live heads exist. Same-range renewal is atomic and
                linearised at renewal_time: old CURRENT -> SUPERSEDED and new -> CURRENT in one step,
                so no observer sees two CURRENT versions. ZERO CURRENT is legal while the unique live
                head is PENDING or PAUSED, and after closure.
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
    # current_delta_cycle is the delta-cycle of the event being dispatched (§0.2/§0.7-H2); every caller
    # passes event_time = now, so (event_time, current_delta_cycle) is exactly the settling timestamp.
    RECORD intermediate_census_for_audit(event_time, current_delta_cycle, (H_active, H_honest, H_adversarial, q_adv))  # H3: audit only
    # (7) H3: do NOT schedule an independent floor decision for THIS transition. Instead flag that a
    #     single settled-census evaluation is required for this (event_time, current_delta_cycle); ONE
    #     FinalizeTimestampSecurityCensus runs after all same-time state changes settle. The
    #     intermediate census above is recorded for audit but NEVER triggers a round-state transition.
    IF this transition changed the ACTIVE_HASHING census:
      SET security_evaluation_required[(event_time, current_delta_cycle)] <- true
  RETURNS: transition_record
  NOTE: This is the ONLY writer of miner_state (0.3) and the SOLE owner of state-residency time
        t_<state> including t_ACTIVE_HASHING = t_hash (H7). It recomputes H_active/H_honest/H_adversarial
        and re-checks I17 at EVERY ACTIVE_HASHING boundary. It never SAMPLES a hash rate and never
        schedules a per-transition floor decision (H3): it only sets security_evaluation_required for
        the settled-census evaluation. Duplicate suppression makes concurrent handlers safe.
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
    # H5: a positive latency schedules a future event_time; a ZERO latency (a permitted future
    #     experimental value) schedules at the SAME event_time but in delta_cycle + 1 at the
    #     WakeComplete microphase -- NEVER inserting into a microphase already completed in the
    #     current delta-cycle (delta-cycle rule §0.7-H2).
    IF wake_latency > 0:
      SCHEDULE event WakeCompleteEvent(RoundContext, MinerID, target_assignment)
               AT event_time = now + wake_latency, delta_cycle = 0, microphase = WAKE_COMPLETE
    ELSE:  # wake_latency = 0 (zero-latency wake, H5)
      SCHEDULE event WakeCompleteEvent(RoundContext, MinerID, target_assignment)
               AT event_time = now, delta_cycle = current_delta_cycle + 1, microphase = WAKE_COMPLETE
    RETURN wake_started                                                  # returns immediately (0.1)
  RETURNS: wake_started
  NOTE: H5: zero wake latency is deterministic -- the WakeCompleteEvent fires at the SAME event_time
        in the NEXT delta-cycle's WakeComplete microphase, so a zero-latency resume initiated after the
        wake microphase never travels backward into a completed phase.

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
      # or restores a resumed PAUSED assignment to CURRENT from its retained actual_frontier (I18b: the
      # unique live head becomes CURRENT again).
      CALL ApplyMinerStateTransition(MinerID, WAKING, ACTIVE_HASHING, now, reason = ramp_complete,
                                     assignment_ref = target_assignment, candidate_ref = null)   # F6 (activates status, recomputes I17)
      # G9: begin EVENT-SCHEDULED hashing (NOT a blocking loop); identical for a fresh or resumed range.
      RETURN CALL StartHashing(RoundContext, MinerID, target_assignment)
    ELSE:
      # G4: STATUS-AWARE wake failure. Move the miner OFFLINE via the hook, then branch on the target
      #     assignment's status; a PAUSED resume failure MUST NOT use the PENDING-only "whole range
      #     inactive" rule.
      RECORD wake_failure(MinerID, target_assignment, status = status(target_assignment))
      CALL ApplyMinerStateTransition(MinerID, WAKING, OFFLINE, now, reason = wake_deadline_expiry,
                                     assignment_ref = target_assignment, candidate_ref = null)   # T12
      SWITCH status(target_assignment):

        CASE PENDING:                                          # (A) failed activation of a fresh/reassigned PENDING
          PRESERVE accepted searched prefix [range_start, accepted_frontier]   # preserve accepted coverage
          IF accepted_frontier(range) = range_end:      SET reassignable <- none
          ELSE IF no accepted positions exist:          SET reassignable <- whole range
          ELSE:                                         SET reassignable <- [accepted_frontier + 1, range_end]
          IF reassignable != none: MARK reassignable as inactive_unsearched / reassignable   # I8a (unsearched only)
          SET custody_status(target_assignment) <- abandoned
          CLOSE target_assignment (status PENDING -> CLOSED)   # no CURRENT recorded; ORIGINAL/REASSIGNED provenance kept
          RECORD wake_failure_energy_and_provenance(MinerID, target_assignment, origin = assignment_origin(target_assignment))

        CASE PAUSED:                                           # (B) failed RESUME of a PAUSED (PATH-B) assignment
          # preserve ALL three frontiers; do NOT label the whole range inactive_unsearched.
          PRESERVE actual_frontier, reported_frontier, accepted_frontier of target_assignment
          IF no accepted positions exist:  SET reassignable <- whole range
          ELSE:                            SET reassignable <- [accepted_frontier + 1, range_end]   # SUFFIX only
          MARK reassignable as inactive_unsearched / reassignable
          # explicit disposition: abandoned under resume_wake_failed -- NOT a PENDING-only PAUSED->CLOSED.
          SET custody_status(target_assignment) <- abandoned
          CLOSE/ABANDON target_assignment (status PAUSED -> CLOSED, disposition = resume_wake_failed)
          CLEAR pause_cause_candidate_id(target_assignment), pause_cause_propagation_id(target_assignment),
                retained_actual_frontier(target_assignment)    # candidate pause fields cleared (G4/G11)
          RECORD wake_failure_energy_and_provenance(MinerID, target_assignment, resumed = true)

      RETURN activation_failure
  RETURNS: activation_record | activation_failure
  NOTE: G4: the PENDING and PAUSED wake-failure paths differ -- a PAUSED resume failure preserves the
        three frontiers and reassigns ONLY the accepted unsearched suffix, never the whole range under
        the PENDING-only rule, and clears the candidate pause fields. G9: on success the miner begins
        event-scheduled hashing via StartHashing (no blocking loop). Concurrent wakes stay independent (F5).
```

### 0.11 Shared pending-assignment constructor (F4)

```
PROCEDURE CreatePendingAssignment
  INPUTS: RoundContext, MinerID, range, assignment_origin, source_assignment, reason
  PRECONDITIONS: assignment_origin in {ORIGINAL, REASSIGNED};        # G2: RENEWED removed from this constructor
                 range disjoint from all valid active assignments (I1);
                 custody_status(range) != completed AND coverage_state(range) != searched
  EFFECTS:
    # F4/G2: the SINGLE PENDING constructor used by RangeAssign, ReserveActivate, RangeReassign,
    #        TemplateRefresh. It sets provenance CORRECTLY from assignment_origin -- a reassignable
    #        suffix is NEVER labelled ORIGINAL. RENEWAL is NOT handled here: RenewAssignment (F7/G2) is
    #        the SOLE renewal path and reuses the SOURCE lineage_id; this constructor never renews and
    #        never reuses a lineage for RENEWED.
    # G2/I18b: ORIGINAL and REASSIGNED both open a FRESH lineage (version 1). A reassignment to a
    #          different holder/sub-range is a NEW lineage linked to its source only by
    #          previous_assignment_reference (cross-lineage I9 provenance) -- it is NOT a new version of
    #          the source lineage, so no lineage ever holds two live heads. In-lineage continuity is
    #          RENEWAL only, and RenewAssignment (F7) is the sole path for that.
    CREATE assignment version A WITH
        AssignmentID       = fresh id
        assignment_version = 1
        lineage_id         = fresh lineage_id
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
        SET previous_assignment_reference(A)     <- AssignmentID(source_assignment)   # cross-lineage provenance
        SET prior_pc <- last accepted ProgressCommit covering range(source_assignment)    # I13 de-dup key
        APPEND provenance(A) <- reassignment_record(range, from = source_assignment, reason,
                                                     timestamp = now, prior_pc)          # I9 complete provenance
    APPEND A to assignment_ledger                                        # supports I8a
  RETURNS: A
  NOTE: G2: only ORIGINAL (fresh never-assigned range) and REASSIGNED (accepted unsearched suffix,
        fresh lineage + full I9 provenance) are constructed here. Same-range RENEWAL is performed
        EXCLUSIVELY by RenewAssignment (F7), which creates the new CURRENT version on the SOURCE
        lineage; RENEWED is never a case here and can never create a fresh lineage.
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
    # G8: initialise the propagation/acceptance registries and counters used across the round.
    INITIALISE active_propagation_set    <- empty
    INITIALISE acceptance_batch_registry <- empty
    SET        candidate_discovery_seq   <- 0        # G7: deterministic CandidateID counter
    SET        block_accepted            <- false
    SET        state_version             <- 0        # G10: round-state epoch
    TRANSITION round_state -> ROUND_INITIALISING     # each round-state change bumps state_version (G10)
    TRANSITION round_state -> TEMPLATE_COMMITMENT
  RETURNS: RoundContext(RoundID, D, nonce_domain, ledgers,
                        active_propagation_set, acceptance_batch_registry,
                        candidate_discovery_seq, block_accepted, state_version)
  NOTE: G10: every `TRANSITION round_state -> S` in this document also bumps `state_version` (a round
        epoch); `SecurityFloorEvaluate` carries the epoch to reject stale evaluations.
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

## 5. Active hashing (event-scheduled, G9)

Hashing is modeled by a chain of discrete `HashWorkEvent`s (G9), NOT by a blocking `WHILE` loop.
`StartHashing` schedules the first unit; each `HashWorkEvent` evaluates one bounded unit, may emit a
candidate or range-completion event, then schedules the next unit and returns to the event loop, so
other miners' events (and certificate arrivals) interleave. A pending unit becomes a no-op once its
miner is no longer `ACTIVE_HASHING` or its exact assignment version is no longer `CURRENT`.

```
PROCEDURE StartHashing
  INPUTS: RoundContext, MinerID, assignment
  PRECONDITIONS: miner_state(MinerID) = ACTIVE_HASHING; assignment VALID and CURRENT
  EFFECTS:
    # G9: begin EVENT-SCHEDULED hashing; do NOT loop. Schedule the first unit and return.
    CALL ScheduleNextHashWork(RoundContext, MinerID, assignment,
                              from_cursor = next unsearched nonce in range(assignment))
  RETURNS: hashing_started

PROCEDURE ScheduleNextHashWork
  INPUTS: RoundContext, MinerID, assignment, from_cursor
  PRECONDITIONS: none
  EFFECTS:
    # G9: schedule ONE bounded unit of hash work as a discrete event carrying the exact identity keys.
    SCHEDULE event HashWorkEvent(RoundContext, MinerID, AssignmentID(assignment),
                                 assignment_version(assignment), RoundID, TemplateID, from_cursor)
             AT now + modeled_hash_step_time
  RETURNS: scheduled

PROCEDURE HashWorkEvent
  INPUTS: RoundContext, MinerID, AssignmentID, assignment_version, RoundID, TemplateID, cursor
  PRECONDITIONS: this is the scheduled hash-work unit for MinerID (envelope carries the identity keys)
  EFFECTS:
    SET assignment <- version(AssignmentID, assignment_version)
    # G9: STALE/CANCELLED-WORK GUARD -- a no-op once the miner is not ACTIVE_HASHING or the EXACT
    #     version is not CURRENT, or the round/template changed, or the round left a hashing-capable
    #     state (covers pause / exhaustion / revocation / offline / disqualification / template refresh
    #     / round closure). Pending units for a stopped miner therefore self-cancel.
    IF miner_state(MinerID) != ACTIVE_HASHING
       OR status(assignment) != CURRENT
       OR RoundID != RoundID_current OR TemplateID != TemplateID_committed
       OR round_state not in {HASHING, SOLUTION_PROPAGATION, SECURITY_RECOVERY}:   # E6/G8 hashing-capable states
      RETURN hash_work_noop
    ASSERT cursor in range(assignment)                          # supports I2 at submission time
    # H7: HashWorkEvent MUST NOT increment any t_<state> residency. The residency_ledger, owned solely
    #     by ApplyMinerStateTransition, computes t_ACTIVE_HASHING = t_hash ONCE when the ACTIVE_HASHING
    #     interval closes. This unit RECORDS work metadata ONLY -- it contributes NO duration term (I19).
    RECORD hash_work_metadata(MinerID, AssignmentID, assignment_version, unit_start = last_unit_time,
             unit_end = now, modeled_hash_evaluations += 1, cursor_progress = cursor,
             work_event_id)                                      # no duration added to the energy ledger
    # ---- [SIMULATION SAMPLING] ----
    hit <- [SIMULATION SAMPLING] Bernoulli(target_hit_probability(D))    # one modeled position/chunk
    # ---- deterministic protocol logic ----
    IF hit:
      candidate_hash <- modeled digest of TemplateID and cursor
      candidate_solution <- (RoundID, TemplateID, AssignmentID, MinerID, cursor AS nonce, candidate_hash, D AS target)
      # E1: IMMUTABLE discovery snapshot at DISCOVERY time (this version is CURRENT now). CR1/E2: the
      #     SIGNED certificate is generated ONLY here, never from coverage/frontier/claimed exhaustion.
      snapshot <- CALL CreateSolutionEligibilitySnapshot(RoundContext, assignment, candidate_solution)
      certificate <- CALL EarlyStopGenerate(RoundContext, candidate_solution, snapshot)
      # C6/E6: acceptance occurs later ONLY at the modeled acceptance point; the finder PAUSES here, so
      #        no further HashWorkEvent is scheduled for it (its next unit, if any, no-ops).
      RETURN CALL ScheduleSolutionPropagation(RoundContext, certificate, snapshot, finder = MinerID)
    ADVANCE cursor
    PERIODICALLY CALL ProgressCommit(assignment, cursor)        # emits progress evidence
    IF cursor beyond range(assignment):
      # D3: actual completion -> ground truth, reported claim, adjudicate.
      CALL ActualRangeCompletion(RoundContext, assignment)
      CALL ReportedExhaustionClaim(RoundContext, assignment, MinerID)
      RETURN CALL ExhaustionAdjudicate(RoundContext, assignment, MinerID, mode)
    # G9: schedule the NEXT unit and return to the loop (non-blocking; other miners/events interleave).
    RETURN CALL ScheduleNextHashWork(RoundContext, MinerID, assignment, from_cursor = cursor)
  RETURNS: hash_work_result (solution | exhausted | continued | noop)
  NOTE: G9: hashing is a chain of discrete units, so a certificate-arrival (or any event) scheduled
        between two units is processed in queue order -- no blocking loop delays it (TV48). Multiple
        miners hash through independently scheduled units, never through nested blocking calls from
        WakeCompleteEvent. Only ACTIVE_HASHING contributes to the active hash rate.
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
  INPUTS: RoundContext, MinerID, stop_reason, assignment_ref,                   # H8: explicit assignment version
          pause_cause_candidate_id = null, pause_cause_propagation_id = null    # F2: required for PATH B only
  PRECONDITIONS: stop_reason in {RANGE_EXHAUSTED, ASSIGNMENT_REVOKED, VALID_SOLUTION_VERIFIED,
                 ROUND_ACCEPTED, ROUND_ABORTED};               # I4: every entry records a reason
                 # H8: assignment_ref is the EXACT immutable assignment VERSION being paused/exhausted/
                 #     revoked/closed; it MUST be a live head (status in {CURRENT, PAUSED}), never a
                 #     SUPERSEDED/CLOSED historical version. There is no undeclared free `assignment`.
                 assignment_ref belongs to MinerID AND status(assignment_ref) in {CURRENT, PAUSED};
                 IF stop_reason = VALID_SOLUTION_VERIFIED THEN pause_cause_candidate_id != null
                   AND pause_cause_propagation_id != null      # F2: the pause cause is a specific candidate
  EFFECTS:
    SET from_state <- miner_state(MinerID)
    # C1: reason-specific disposition. There is NO generic "release held range to pool" step.
    SWITCH stop_reason:

      CASE RANGE_EXHAUSTED:                                    # PATH A
        ASSERT from_state = EXHAUSTED_PENDING
        ASSERT accepted_exhaustion(assignment_ref) = TRUE      # accepted exhaustion accounting exists
        ASSERT coverage_state(range(assignment_ref)) = searched AND custody_status(range(assignment_ref)) = completed
        CLOSE assignment_ref
        # do NOT release or reassign any part of the completed range

      CASE ASSIGNMENT_REVOKED:
        ASSERT from_state = ACTIVE_HASHING
        PRESERVE accepted searched prefix [range_start(assignment_ref), accepted_frontier(assignment_ref)]
        SET suffix <- accepted unsearched suffix [accepted_frontier(assignment_ref) + 1, range_end(assignment_ref)]
        MARK suffix as inactive_unsearched / reassignable      # only the accepted unsearched suffix (C4)
        CLOSE/SUPERSEDE assignment_ref

      CASE VALID_SOLUTION_VERIFIED:                            # PATH B
        ASSERT from_state = ACTIVE_HASHING
        ASSERT the honoured early-stop certificate passed I11
        PAUSE assignment_ref (status CURRENT -> PAUSED); retain actual_frontier AND accepted_frontier
        # F2: record the SPECIFIC candidate that caused this pause, so a later candidate-scoped
        #     failure resumes ONLY the miners paused by that candidate.
        SET pause_cause_candidate_id(assignment_ref)   <- pause_cause_candidate_id
        SET pause_cause_propagation_id(assignment_ref) <- pause_cause_propagation_id
        SET paused_assignment_id(assignment_ref)       <- AssignmentID(assignment_ref)
        SET retained_actual_frontier(assignment_ref)   <- actual_frontier(assignment_ref)
        # do NOT change coverage to searched; do NOT release the assignment

      CASE ROUND_ACCEPTED OR ROUND_ABORTED:
        CLOSE assignment_ref because the round ended
        # do NOT mark the range exhausted; do NOT reassign it under the closed TemplateID

    RECORD entry_stop_reason(MinerID) <- stop_reason           # I4: why the miner left ACTIVE_HASHING
    # F6: the LOW_POWER_LISTEN entry (and its P_hash/P_listen boundary + I17 recompute) is applied
    #     by the hook. For PATH A the source is EXHAUSTED_PENDING (already off H_active); for the
    #     other reasons the source is ACTIVE_HASHING (this is the H_active exit boundary).
    CALL ApplyMinerStateTransition(MinerID, from_state, LOW_POWER_LISTEN, now,
                                   reason = stop_reason, assignment_ref = assignment_ref,
                                   candidate_ref = pause_cause_candidate_id)     # T8 / T26 / T27 / T28 / T29
  RETURNS: listen_record(MinerID, stop_reason)
  NOTE: H8: the exact immutable assignment VERSION is passed explicitly as assignment_ref (never an
        undeclared free variable), so a SUPERSEDED/CLOSED historical version can never be paused or
        closed by accident while immutable versions coexist in the ledger (I18a/I18b).
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
    # G3: COMPUTE-ONLY. It READS the current miner-state census and records the rates. It has NO
    #     [SIMULATION SAMPLING] step. It MUST NOT (a) apply a sampled adversarial active set directly
    #     to miner states, (b) alter the ACTIVE_HASHING census without a state transition, or (c) add
    #     or remove a miner from H_active independently of miner_state. Every membership change is made
    #     by ApplyMinerStateTransition (F6) -- for adversarial miners via scheduled
    #     AdversarialParticipationChangeEvents (§8a), for honest miners via the ordinary transitions.
    SET H_honest(t)      <- SUM over honest miners currently in ACTIVE_HASHING of their modeled hash rate
    SET H_adversarial(t) <- SUM over adversarial miners currently in ACTIVE_HASHING of their modeled hash rate
    SET H_active(t)      <- H_honest(t) + H_adversarial(t)      # exact census decomposition (I17)
    IF H_active(t) = 0: SET q_adv(t) <- NA                      # I17: undefined at zero active hash rate
    ELSE:               SET q_adv(t) <- H_adversarial(t) / H_active(t)
    RECORD (H_active(t), H_honest(t), H_adversarial(t), q_adv(t))   # values only; no state change, no breach
  RETURNS: (H_active(t), H_honest(t), H_adversarial(t), q_adv(t))
  NOTE: G3: read-only re-derivation of the I17 identity at t. The same identity is also recomputed by
        the hook at every ACTIVE_HASHING boundary (F6); this procedure is a periodic snapshot, not a
        writer. Only ACTIVE_HASHING contributes; other states contribute nothing.
```

## 8a. Adversarial participation change (G3)

```
PROCEDURE AdversarialParticipationChangeEvent
  INPUTS: RoundContext, MinerID, direction   # direction in {enter, exit}
  PRECONDITIONS: this is a scheduled event emitted by the adversarial-participation model for one
                 adversarial-classified MinerID (the model's [SIMULATION SAMPLING] draw is WHEN/WHICH
                 adversarial miner changes participation -- see the sampling summary)
  EFFECTS:
    # G3/H6: the ONLY carrier of a modeled adversarial participation change. It changes miner_state
    #     ONLY through the hook, so residency (single owner, H7), transition energy, the
    #     H_active/H_honest/H_adversarial recompute, and I17 all happen exactly once (F6). It NEVER
    #     adds/removes a miner from H_active directly. Because the census-changing boundary is a hook
    #     transition, the hook sets security_evaluation_required[(now, current_delta_cycle)] and the
    #     SINGLE FinalizeTimestampSecurityCensus for this settled timestamp evaluates the floor once (H3).
    # H6: entry and exit take STATE-SPECIFIC legal paths; there is NO generic re-entry that fabricates a
    #     second live head, and NO generic exit that leaves a live CURRENT head behind.

    IF direction = exit:
      # ---- EXIT: only the ACTIVE_HASHING census is affected; a miner not in H_active contributes 0. ----
      IF miner_state(MinerID) != ACTIVE_HASHING:
        RETURN no_census_change            # H6: not in the active census; no fabricated departure edge
      SET X <- current_assignment(MinerID)                      # the EXACT CURRENT version (I18a: unique)
      # H6: preserve accepted coverage; expose ONLY the accepted unsearched suffix (C4), never the prefix.
      PRESERVE accepted searched prefix [range_start(X), accepted_frontier(X)]
      SET suffix <- accepted unsearched suffix [accepted_frontier(X) + 1, range_end(X)]
      MARK suffix as inactive_unsearched / reassignable          # only the accepted unsearched suffix (C4)
      # H6/I9: record the withdrawal reason and provenance on the closed version, then CLOSE/REVOKE the
      #        CURRENT head EXPLICITLY so NO live CURRENT head remains for MinerID (I18a/I18b).
      RECORD withdrawal_reason(X) <- adversarial_withdrawal      # I9 reason
      RECORD provenance(X): previous_assignment_reference, custody_status(range(X)) <- revoked_adversarial_exit
      # H7/G9: cancel this version's pending hash-work units explicitly (they would self-cancel by the
      #        stale guard, but the exit CANCELS them so no unit is charged after the census leaves H_active).
      CANCEL pending HashWorkEvent units for (MinerID, AssignmentID(X), assignment_version(X))
      CLOSE/SUPERSEDE X                                          # no live CURRENT head remains (I18a)
      CALL ApplyMinerStateTransition(MinerID, ACTIVE_HASHING, OFFLINE, now,
             reason = adversarial_withdrawal, assignment_ref = X, candidate_ref = null)   # T11 (F6)
      RETURN participation_exit_record(MinerID, closed_version = X, reassignable_suffix = suffix)

    ELSE:   # direction = enter
      # ---- ENTRY: reach ACTIVE_HASHING ONLY at a future WakeCompleteEvent (F5); never a direct add. ----
      SWITCH miner_state(MinerID):

        CASE REGISTERED OR RESERVE:
          # H6: no live head exists; create/bind a fresh PENDING and wake. RangeAssign (REGISTERED->WAKING
          #     T3 / RESERVE->WAKING T4) builds a PENDING via CreatePendingAssignment and StartWake (F4/F5).
          RETURN CALL RangeAssign(RoundContext, MinerID, requested_size = modeled,
                                  lease_duration = default_lease_duration)

        CASE OFFLINE:
          # H6: rejoin the round through the hook FIRST (OFFLINE -> REGISTERED, T17), then create/bind a
          #     fresh PENDING and wake -- never a direct census add.
          CALL ApplyMinerStateTransition(MinerID, OFFLINE, REGISTERED, now, reason = adversarial_rejoin,
                 assignment_ref = null, candidate_ref = null)    # T17 (F6)
          RETURN CALL RangeAssign(RoundContext, MinerID, requested_size = modeled,
                                  lease_duration = default_lease_duration)

        CASE LOW_POWER_LISTEN:
          # H6: the re-entry path DEPENDS on why the miner is idle (entry_stop_reason, I4).
          IF entry_stop_reason(MinerID) = VALID_SOLUTION_VERIFIED:
            # PATH-B pause: the miner's OWN assignment is still PAUSED (a live head, I18b). Resuming it
            # MUST reuse that head via ResumeFromPause carrying ITS recorded pause-cause ids -- it MUST
            # NOT call RangeAssign (that would mint a SECOND live head and break I18b).
            SET paused <- paused_assignment(MinerID)
            RETURN CALL ResumeFromPause(RoundContext, MinerID, trigger = adversarial_reactivation,
                     pause_cause_candidate_id   = pause_cause_candidate_id(paused),      # G11: matched ids
                     pause_cause_propagation_id = pause_cause_propagation_id(paused))     # T30
          ELSE:
            # entry_stop_reason in {RANGE_EXHAUSTED, ASSIGNMENT_REVOKED, ROUND_ACCEPTED, ROUND_ABORTED}:
            # the prior assignment is CLOSED (NO live head, I18b), so a fresh eligible assignment is
            # legal. The LEGAL re-entry edge from LOW_POWER_LISTEN is T10 (new-assignment wake ->
            # WAKING), NOT RangeAssign (whose precondition is REGISTERED/RESERVE, T3/T4). Bind a fresh
            # PENDING (a NEW ORIGINAL lineage, I18b) via the shared constructor and StartWake from
            # LOW_POWER_LISTEN -- mirroring RangeAssign's body but with the correct legal source edge.
            SELECT candidate_range from unassigned portion of nonce_domain    # fresh, never-assigned (I1)
            fresh <- CALL CreatePendingAssignment(RoundContext, MinerID, candidate_range,
                       assignment_origin = ORIGINAL, source_assignment = null, reason = null)   # F4
            SET lease_start(fresh)  <- now
            SET lease_expiry(fresh) <- now + default_lease_duration
            RETURN CALL StartWake(RoundContext, MinerID, target_assignment = fresh,
                                  from_state = LOW_POWER_LISTEN)                          # T10 (F5/F6)

        DEFAULT:
          # WAKING / ACTIVE_HASHING / EXHAUSTED_PENDING / DISQUALIFIED: already participating or in a
          # transient/terminal state; no participation change is applied.
          RETURN no_change
  RETURNS: participation_change_record
  NOTE: H6: entry is state-specific -- REGISTERED/RESERVE and (post-closure) LOW_POWER_LISTEN create a
        fresh PENDING and wake; OFFLINE rejoins via the hook first; a still-PAUSED LOW_POWER_LISTEN
        resumes its OWN head via ResumeFromPause (never RangeAssign). Exit acts ONLY on ACTIVE_HASHING:
        it preserves accepted coverage, exposes only the accepted unsearched suffix, records the I9
        reason/provenance, cancels the version's pending hash units, closes the CURRENT head explicitly
        (no live head remains), and departs via T11 -- all through the hook.
  NOTE: G3: the adversarial-participation SAMPLING is entirely in the SCHEDULING of these events (the
        model draws each miner's enter/exit times); the STATE CHANGE is deterministic and routes
        through the hook. ActiveHashRateUpdate never mutates the census (C7 preserved: floor breaches
        are still recorded only by SecurityFloorEvaluate, invoked once per settled timestamp by
        FinalizeTimestampSecurityCensus, H3).
```

## 9. Security-floor evaluation

```
PROCEDURE FinalizeTimestampSecurityCensus
  INPUTS: RoundContext, event_time, delta_cycle
  PRECONDITIONS: microphase 5 (§0.7); runs EXACTLY ONCE per (event_time, delta_cycle), AFTER every
                 state-changing event of that (event_time, delta_cycle) has settled (H3)
  EFFECTS:
    # H3: the SINGLE per-timestamp security evaluation. If no ACTIVE_HASHING boundary occurred this
    #     (event_time, delta_cycle), there is nothing to evaluate.
    IF NOT security_evaluation_required[(event_time, delta_cycle)]:
      RETURN no_census_change
    # read the FINAL settled census (the last recomputation by ApplyMinerStateTransition at this
    # (event_time, delta_cycle)); intermediate same-time census values were recorded for AUDIT ONLY.
    SET (H_active, H_honest, q_adv) <- final settled census at (event_time, delta_cycle)
    CLEAR security_evaluation_required[(event_time, delta_cycle)]
    # exactly ONE floor decision for the settled census, carrying the current round epoch (G10/H4).
    RETURN CALL SecurityFloorEvaluate(RoundContext, event_RoundID = RoundID, event_TemplateID = TemplateID,
                 event_state_version = state_version, (H_active, H_honest, q_adv), floor_state)
  RETURNS: floor_result
  NOTE: H3: the ONLY caller of SecurityFloorEvaluate. It runs ONCE per settled (event_time, delta_cycle),
        so the FIRST of several same-time miner transitions never independently triggers recovery from an
        intermediate census. Intermediate census values are retained for audit but never drive a
        round-state transition.

PROCEDURE SecurityFloorEvaluate
  INPUTS: RoundContext, event_RoundID, event_TemplateID, event_state_version,
          (H_active(t), H_honest(t), q_adv(t)), floor_state
  PRECONDITIONS: invoked ONLY by FinalizeTimestampSecurityCensus on a settled census (H3); never
                 inline (G10); carries the (RoundID, TemplateID, state_version) of that evaluation
  EFFECTS:
    # G10: TERMINAL/STALE GUARD. Never act on a stale round/template/epoch.
    IF event_RoundID != RoundID_current
       OR event_TemplateID != TemplateID_committed
       OR event_state_version != state_version_current:
      RETURN terminal_stale_noop                               # no breach recorded, no transition
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
    # H4: SECURITY_RECOVERY may be entered ONLY from a legal source state; from any other state the
    #     final census is recorded as OBSERVATION-ONLY and NO round transition occurs.
    IF breach AND round_state in {HASHING, SOLUTION_PROPAGATION, SECURITY_RECOVERY}:
      # G8: SR may be entered from HASHING or SOLUTION_PROPAGATION and PRESERVES any live propagation
      #     contexts; block arrivals/arbitration remain processable during recovery.
      TRANSITION round_state -> SECURITY_RECOVERY              # bumps state_version (G10)
      RETURN breach
    ELSE IF breach:
      # illegal source: record the census/breach for audit but perform NO transition (H4).
      RETURN (round_state = TEMPLATE_REFRESH        ? refresh_observation_only  :
              round_state = ROUND_EXHAUSTED         ? exhausted_observation_only :
              round_state in {ROUND_ACCEPTED, ROUND_ABORTED} ? terminal_stale_noop :
              setup_observation_only)               # ROUND_INITIALISING / TEMPLATE_COMMITMENT / ASSIGNMENT
    RETURN no_breach
  RETURNS: breach | no_breach | refresh_observation_only | exhausted_observation_only |
           setup_observation_only | terminal_stale_noop
  NOTE: H3/H4: SecurityFloorEvaluate runs ONCE per settled timestamp (via FinalizeTimestampSecurityCensus)
        and transitions to SECURITY_RECOVERY ONLY from {HASHING, SOLUTION_PROPAGATION, SECURITY_RECOVERY};
        from setup (ROUND_INITIALISING/TEMPLATE_COMMITMENT/ASSIGNMENT), TEMPLATE_REFRESH, ROUND_EXHAUSTED,
        or a terminal round it records observation-only and performs NO illegal transition. I17 holds at
        every boundary; `q_adv = NA` is never numerically compared; recovery logs never overwrite breach
        records (I16). Entering SECURITY_RECOVERY does NOT cancel live candidates (G8).
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
      CALL EnterLowPowerListen(RoundContext, holder, stop_reason = ASSIGNMENT_REVOKED,
                               assignment_ref = assignment)     # H8: the exact expiring version
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
                               assignment_ref = current_assignment(verifying_MinerID),   # H8: the verifier's OWN CURRENT version
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
  INPUTS: RoundContext, MinerID, trigger, pause_cause_candidate_id, pause_cause_propagation_id
  PRECONDITIONS: miner_state(MinerID) = LOW_POWER_LISTEN with entry_stop_reason = VALID_SOLUTION_VERIFIED;
                 # candidate-failure triggers (F2/G11) PLUS the single non-failure trigger H6 permits:
                 trigger in {REJECTED, BLOCK_UNAVAILABLE, PROPAGATION_TIMEOUT, NO_VALID_CANDIDATE,
                             adversarial_reactivation};
                 # F2/G11/H6: resume ONLY this miner's OWN paused head -- match BOTH ids. For a candidate
                 #   failure the ids are the failed candidate's; for adversarial_reactivation the caller
                 #   reads them FROM the miner's own PAUSED head, so the match is exact and NO second live
                 #   head is ever minted (I18b) -- this is why H6 routes a PAUSED re-entry here, never RangeAssign.
                 pause_cause_candidate_id(paused_assignment(MinerID))   = pause_cause_candidate_id
                 AND pause_cause_propagation_id(paused_assignment(MinerID)) = pause_cause_propagation_id;
                 the miner's assignment is PAUSED (retained_actual_frontier retained), NOT searched/exhausted
  EFFECTS:
    # CR-B1/F2/G11: a paused PATH B assignment resumes because the SPECIFIC candidate (matched on BOTH
    # CandidateID and PropagationID) that paused it failed; it was never marked searched or completed.
    SET paused_assignment <- the miner's PAUSED assignment (paused_assignment_id)
    # G11: a resume MUST NOT fire for a miner paused by a different propagation context; the two-id
    #      precondition above guarantees this.
    # F2: the miner is no longer paused by any candidate.
    CLEAR pause_cause_candidate_id(paused_assignment), pause_cause_propagation_id(paused_assignment)
    # F5/F6/D5: resume passes through WAKING via the NON-BLOCKING StartWake (T30). The paused
    #           assignment is the wake target; WakeCompleteEvent restores it to CURRENT from
    #           retained_actual_frontier (WAKING -> ACTIVE_HASHING, T5), recomputes H_active/I17 at
    #           the ACTIVE_HASHING boundary (via ApplyMinerStateTransition), and resumes hashing.
    RETURN CALL StartWake(RoundContext, MinerID, target_assignment = paused_assignment,
                          from_state = LOW_POWER_LISTEN)                        # T30
  RETURNS: resume_started(MinerID, resumed_from = retained_actual_frontier)
  NOTE: Resume applies ONLY to PATH B pauses, and ALWAYS to the miner's OWN paused head (matched on
        BOTH ids, F2/G11): for a candidate-failure trigger the ids are the failed candidate's; for the
        single non-failure trigger adversarial_reactivation (H6) the ids are read from the miner's own
        PAUSED head, so no second live head is minted (I18b). A PATH A exhausted range (coverage_state
        = searched, custody_status = completed) is NOT resumable. Resume is event-scheduled (F5);
        several miners resuming at the same instant wake independently. If instead the full block is
        ACCEPTED, the round closes (ROUND_ACCEPTED) and the paused assignment closes on round closure
        -- NOT by exhaustion.
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
  PRECONDITIONS: called at solution discovery, BEFORE self-validation (G6: DISCOVERED is reachable)
  EFFECTS:
    # G7: mint DETERMINISTIC immutable identifiers (never random UUIDs).
    SET candidate_discovery_seq <- candidate_discovery_seq + 1        # per-round monotonic (RoundContext)
    SET CandidateID   <- (RoundID, candidate_discovery_seq)           # G7 deterministic
    SET PropagationID <- (CandidateID, propagation_attempt_seq = 1)   # G7 deterministic (first attempt)
    # G6: the context is born DISCOVERED; it is NOT yet propagation-active (not in active_propagation_set).
    CREATE cpc = CandidatePropagationContext WITH
        CandidateID, PropagationID, RoundID = certificate.RoundID, TemplateID = certificate.TemplateID,
        certificate, snapshot, finder_MinerID = finder, discovery_time = snapshot.discovery_time,
        certificate_arrival_events = empty, block_arrival_event = null,
        acceptance_timestamp = null, status = DISCOVERED, failure_reason = null
    RETURN cpc
  RETURNS: cpc

PROCEDURE ScheduleSolutionPropagation
  INPUTS: RoundContext, certificate, snapshot, finder
  PRECONDITIONS: round_state in {HASHING, SOLUTION_PROPAGATION, SECURITY_RECOVERY};
                 certificate produced by EarlyStopGenerate from a found valid solution + snapshot
  EFFECTS:
    # G6: build the context DISCOVERED first (so DISCOVERED is reachable), then self-validate.
    cpc <- CALL CreatePropagationContext(RoundContext, certificate, snapshot, finder)   # status = DISCOVERED
    # D4/E2: the finder MUST self-validate the SIGNED certificate BEFORE it may stop or propagate.
    self_ok <- CALL SelfValidateFoundSolution(RoundContext, certificate, snapshot)
    IF NOT self_ok:
      RECORD invalid_self_certificate(finder, certificate)       # finder does NOT stop; stays ACTIVE_HASHING
      SET status(cpc) <- FAILED ; SET failure_reason(cpc) <- NO_VALID_CANDIDATE   # never propagation-active
      RETURN not_scheduled
    SET status(cpc) <- SELF_VALIDATED                            # G6: reachable status
    # F3/G6/G8: register the PROPAGATION-ACTIVE context. Entering the FIRST propagation-active context
    #           performs HASHING -> SOLUTION_PROPAGATION (E6). Round-state and the set are NOT identified:
    #           the set may be non-empty in SECURITY_RECOVERY too (G8).
    SET was_empty <- (active_propagation_set is empty)
    SET status(cpc) <- PROPAGATING
    ADD cpc to active_propagation_set                           # membership = {PROPAGATING, PENDING_ACCEPTANCE}
    IF was_empty AND round_state = HASHING: TRANSITION round_state -> SOLUTION_PROPAGATION
    # C6/F1/G7: schedule per-recipient certificate-arrival events in a STABLE SORTED order (by MinerID);
    #           each event carries CandidateID/PropagationID (F1/G11).
    FOR EACH recipient r in SORT({ m in current miners : m != finder } BY MinerID ascending):
      cert_delay(r) <- deterministic modeled propagation delay(finder -> r)   # reproducible
      ev <- SCHEDULE event CertificateArrival(RoundContext, r, cpc.certificate, cpc.snapshot,
                                              CandidateID = cpc.CandidateID, PropagationID = cpc.PropagationID)
                          AT now + cert_delay(r)
      ADD ev to certificate_arrival_events(cpc)
    # schedule the full-block acceptance event toward the modeled acceptance point (carries the ids).
    block_delay <- deterministic modeled propagation delay(finder -> acceptance_point)  # reproducible
    SET block_arrival_event(cpc) <- SCHEDULE event BlockAcceptancePoint(RoundContext, cpc.certificate,
                          cpc.snapshot, CandidateID = cpc.CandidateID, PropagationID = cpc.PropagationID,
                          outcome = outcome-at-arrival) AT now + block_delay
    # (5) the finder ceases hashing (PATH B), recording THIS candidate (BOTH ids) as its pause cause (F2/G11).
    CALL EnterLowPowerListen(RoundContext, finder, stop_reason = VALID_SOLUTION_VERIFIED,
                             assignment_ref = version(cpc.snapshot.AssignmentID, cpc.snapshot.assignment_version),  # H8: exact discovery version (CURRENT for the finder now)
                             pause_cause_candidate_id = cpc.CandidateID,
                             pause_cause_propagation_id = cpc.PropagationID)
  RETURNS: cpc.CandidateID
  NOTE: G6: status flows DISCOVERED -> SELF_VALIDATED -> PROPAGATING here; PENDING_ACCEPTANCE is set
        when the block arrival REGISTERS at the acceptance point (BlockAcceptancePoint, G5). The set
        holds ONLY PROPAGATING/PENDING_ACCEPTANCE contexts. Do NOT accept here. Further candidates each
        get their OWN context (F1/F3).
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
                 PROPAGATION_TIMEOUT}; processed in microphase 3 (G5)
  EFFECTS:
    # G5: REGISTER-ONLY. This handler MUST NOT directly accept, arbitrate, or close the round; it only
    #     records its arrival and returns. Arbitration + closure happen once in AcceptanceBatchFinalize
    #     (microphase 4), AFTER all same-timestamp block arrivals have been collected.
    # F2/F3: ignore an arrival whose candidate is no longer live (already ACCEPTED/FAILED/CANCELLED).
    IF status(context(CandidateID)) not in {PROPAGATING, PENDING_ACCEPTANCE}:
      RETURN ignored_stale_candidate
    SET status(context(CandidateID)) <- PENDING_ACCEPTANCE       # G6: reachable status set on arrival
    SET acceptance_timestamp(context(CandidateID)) <- now
    # register into the acceptance batch for (this timestamp, this acceptance point).
    APPEND (certificate, snapshot, CandidateID, PropagationID, outcome)
           to acceptance_batch_registry[(now, RoundContext.acceptance_point)]
    ENSURE exactly one AcceptanceBatchFinalize(RoundContext, acceptance_timestamp = now,
           acceptance_point = RoundContext.acceptance_point) is scheduled for microphase 4 of THIS
           (timestamp, acceptance point)                         # G5: single finalize per (ts, point)
    RETURN registered
  RETURNS: registered | ignored_stale_candidate
  NOTE: G5: a block arrival never accepts or fails a candidate directly. ALL same-timestamp arrivals
        (ACCEPTED_CANDIDATE and non-accept alike) are collected in acceptance_batch_registry; the ONE
        AcceptanceBatchFinalize for the timestamp validates the accepted candidates, selects a winner,
        commits acceptance and closes the round atomically, and dispositions the non-accept arrivals
        candidate-scoped. No event inspects unknown future timestamps.
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
    ASSERT PropagationID = PropagationID(cpc)                       # G11: both envelope ids must match
    SET status(cpc)         <- FAILED
    SET failure_reason(cpc) <- failure_reason
    RECORD propagation_failure(RoundID, TemplateID, CandidateID, PropagationID, failure_reason)
    REMOVE cpc from active_propagation_set                          # F3: ONLY this candidate leaves the set
    # (1) cancel ONLY this candidate's obsolete events (F2): its per-recipient certificate-arrival
    #     events and its block-arrival event. Another candidate's events are NEVER cancelled here.
    CANCEL every event in certificate_arrival_events(cpc)
    CANCEL block_arrival_event(cpc)
    # (2) resume ONLY miners whose pause cause matches BOTH ids of THIS candidate (F2/G11). Iterate in a
    #     STABLE sorted order by MinerID (G7). A miner paused by another candidate is left unchanged.
    FOR EACH miner M in SORT({ m : m has a PAUSED assignment
                               AND pause_cause_candidate_id(paused_assignment(m))   = CandidateID
                               AND pause_cause_propagation_id(paused_assignment(m)) = PropagationID }
                             BY MinerID ascending):
      SCHEDULE event ResumeFromPause(RoundContext, M, trigger = failure_reason,
                                     pause_cause_candidate_id = CandidateID,
                                     pause_cause_propagation_id = PropagationID)   # G11: both ids on the resume event
    # (3) H3: do NOT schedule an independent floor decision here. The candidate-scoped resumes above
    #     re-activate miners in a later delta-cycle; each re-activation boundary sets
    #     security_evaluation_required, and the SINGLE FinalizeTimestampSecurityCensus for that settled
    #     timestamp performs the one floor decision (microphase 5, delta-cycle rule §0.7-H2).
    SET security_evaluation_required[(now, current_delta_cycle)] <- true   # settled-census eval, not per-transition
    # (4) round-state rule (F3/G8): return to HASHING ONLY when propagation is FULLY quiescent AND the
    #     round is still in SOLUTION_PROPAGATION. During SECURITY_RECOVERY the round stays in recovery
    #     (live candidates are preserved, G8); a later floor-restored step returns it (round SM R13).
    IF round_state = SOLUTION_PROPAGATION AND propagation_quiescent(RoundContext):
      TRANSITION round_state -> HASHING
    # ELSE: the round STAYS SOLUTION_PROPAGATION (other candidates live) or SECURITY_RECOVERY (G8).
    RETURN candidate_failed(CandidateID)
  RETURNS: candidate_failed
  NOTE: Candidate-scoped (F2/F3/G11 on BOTH ids). One candidate's failure NEVER cancels or resumes
        another candidate's events or paused miners. The round remains SOLUTION_PROPAGATION while any
        live candidate exists (F3), and SECURITY_RECOVERY may coexist with live candidates (G8).
        The floor evaluation is NOT scheduled per failure (H3); it is the single settled-census
        evaluation via FinalizeTimestampSecurityCensus. No block is accepted and no round is closed
        here. `propagation_quiescent` is defined in §0.6.
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
        SelfValidateFoundSolution (finder), EarlyStopVerify (recipients), and AcceptanceBatchFinalize
        (acceptance). It resolves the snapshot's (AssignmentID, assignment_version) to that immutable
        version (I18) and validates DISCOVERY-time eligibility (I2/G1); it never requires the finder's
        assignment to remain CURRENT after discovery (E1).
```

```
PROCEDURE AcceptanceBatchFinalize
  INPUTS: RoundContext, acceptance_timestamp, acceptance_point
  PRECONDITIONS: microphase 4 for (acceptance_timestamp, acceptance_point); runs EXACTLY ONCE for it,
                 AFTER microphase 3 has collected ALL same-timestamp block arrivals (G5)
  EFFECTS:
    # G5: the SINGLE arbitration+closure point for this timestamp. Round-acceptance closure is the
    #     ATOMIC RESULT of this procedure -- it is NOT an independent event that precedes arbitration.
    SET batch <- acceptance_batch_registry[(acceptance_timestamp, acceptance_point)]
    # split by outcome; iterate in STABLE order by CandidateID (G7).
    SET accepted <- SORT([ a in batch : a.outcome = ACCEPTED_CANDIDATE ] BY a.CandidateID ascending)
    SET failed   <- SORT([ a in batch : a.outcome != ACCEPTED_CANDIDATE ] BY a.CandidateID ascending)
    # (1) validate every ACCEPTED candidate against ITS OWN discovery snapshot (E1/E2).
    SET valid <- [ a in accepted : CALL ValidateCandidate(RoundContext, a.certificate, a.snapshot) ]
    IF valid is non-empty AND NOT block_accepted:
      # (2) select the winner deterministically: smallest candidate_hash, then smallest MinerID (D6/G7).
      winner <- argmin over valid of (a.certificate.candidate_hash, then a.certificate.MinerID)
      # (3) the losing same-timestamp valid candidates become COMPETING; ValidBlockAccept then cancels
      #     ALL non-winner live contexts and closes the round EXACTLY ONCE (atomic; G5/F3).
      FOR EACH a in valid, a != winner: SET status(context(a.CandidateID)) <- COMPETING
      CALL ValidBlockAccept(RoundContext, winner.CandidateID, winner.certificate, winner.snapshot)
    ELSE:
      # (4) no valid winner at this timestamp -> fail EACH accepted-but-invalid candidate candidate-scoped
      #     (each resumes ONLY its own paused miners; G5/F2). No cross-candidate cancellation.
      FOR EACH a in accepted:
        CALL HandlePropagationFailure(RoundContext, a.CandidateID, a.PropagationID, failure_reason = NO_VALID_CANDIDATE)
    # (5) disposition the non-accept arrivals candidate-scoped -- a no-op if the round already closed (2)-(3).
    FOR EACH a in failed:
      IF round_state not in {ROUND_ACCEPTED, ROUND_ABORTED}:
        CALL HandlePropagationFailure(RoundContext, a.CandidateID, a.PropagationID, failure_reason = a.outcome)
    CLEAR acceptance_batch_registry[(acceptance_timestamp, acceptance_point)]
  RETURNS: accepted_block | no_valid_candidate
  NOTE: G5: exactly one finalize per (timestamp, acceptance point). All same-timestamp block arrivals
        are collected (microphase 3) BEFORE this runs; arbitration selects a deterministic winner
        (candidate_hash then MinerID); acceptance + closure are atomic here (causally downstream of
        arbitration). Different timestamps: the earliest ACCEPTED timestamp's finalize sets
        block_accepted, so a later finalize accepts nothing (its accepted candidates fail scoped).
```

## 17. Valid block acceptance

```
PROCEDURE ValidBlockAccept
  INPUTS: RoundContext, winner_CandidateID, winner_certificate, winner_snapshot
  PRECONDITIONS: invoked ONLY from AcceptanceBatchFinalize after arbitration (G5/D6);
                 winner_certificate already validated by ValidateCandidate against winner_snapshot
                 and chosen as the batch winner;
                 # G8: acceptance may close a round that is in SOLUTION_PROPAGATION OR SECURITY_RECOVERY,
                 #     provided the winner's RoundID/TemplateID are still valid; a valid accepted
                 #     candidate may close a recovery-state round.
                 round_state in {SOLUTION_PROPAGATION, SECURITY_RECOVERY}
                 AND winner_certificate.RoundID = RoundID_current
                 AND winner_certificate.TemplateID = TemplateID_committed
  EFFECTS:
    # F3: close the round EXACTLY ONCE. A second entry (a later same-round acceptance) is a no-op.
    IF block_accepted:
      SET status(context(winner_CandidateID)) <- COMPETING       # a strictly-earlier timestamp already won
      RETURN not_selected
    RECORD accepted_block(winner_certificate)
    SET block_accepted <- true                                   # G8 flag; single closure
    SET status(context(winner_CandidateID)) <- ACCEPTED
    # F3: mark EVERY OTHER live context stale/cancelled and cancel THEIR remaining events (winner
    #     excluded). Iterate in STABLE sorted order by CandidateID (G7). This is the ONE place
    #     cross-candidate cancellation is legitimate (acceptance).
    FOR EACH other cpc in SORT(active_propagation_set BY CandidateID ascending), other.CandidateID != winner_CandidateID:
      SET status(other) <- (other was a same-timestamp valid loser ? COMPETING : CANCELLED)
      CANCEL every event in certificate_arrival_events(other)
      CANCEL block_arrival_event(other)
    CLEAR active_propagation_set                                  # no live candidate remains after acceptance
    # E6/G8: a SINGLE transition to ROUND_ACCEPTED, from SOLUTION_PROPAGATION or SECURITY_RECOVERY.
    TRANSITION round_state -> ROUND_ACCEPTED                      # bumps state_version (G10)
    # D7: centralised round closure (the SINGLE closure path); paused miners of cancelled candidates
    #     are closed by round closure (ROUND_ACCEPTED), NOT resumed.
    CALL CloseRoundAssignments(RoundContext, disposition = ROUND_ACCEPTED, stop_reason = ROUND_ACCEPTED)
  RETURNS: accepted_block | not_selected
  NOTE: G8: a valid accepted candidate closes the round from SOLUTION_PROPAGATION OR SECURITY_RECOVERY.
        Acceptance sets the winner ACCEPTED, marks all other live candidates COMPETING/STALE/CANCELLED,
        cancels their events, and closes the round EXACTLY ONCE (block_accepted guard). Miners paused by
        a cancelled candidate are NOT resumed (the round ended); they close with stop_reason =
        ROUND_ACCEPTED via CloseRoundAssignments. No chain-wide fork-choice proof is claimed.
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
          CALL EnterLowPowerListen(RoundContext, h, stop_reason = disposition, assignment_ref = X)   # H8: exact version; sets entry_stop_reason(h) <- disposition; closes X

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
    # cancel pending events belonging to the closed round (G9: including HashWorkEvents; G5: clear the
    # acceptance batch registry so no stale batch finalizes after closure).
    CANCEL all pending wake / resume / certificate-arrival / BlockAcceptancePoint / HashWorkEvent /
           AdversarialParticipationChangeEvent events for RoundID
    CLEAR active_propagation_set                                # no live candidate survives closure
    CLEAR acceptance_batch_registry                             # no pending batch survives closure
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
          CALL EnterLowPowerListen(RoundContext, h, stop_reason = ASSIGNMENT_REVOKED,
                                   assignment_ref = X)   # H8: exact old-template version; -> LOW_POWER_LISTEN
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
    # G8/G9/TV50: discard old-template candidate contexts, their events, hash events, and batches
    # WITHOUT modifying any historical record.
    FOR EACH cpc in SORT(active_propagation_set BY CandidateID ascending) WHERE TemplateID(cpc) = old_TemplateID:
      SET status(cpc) <- CANCELLED
      CANCEL every event in certificate_arrival_events(cpc)
      CANCEL block_arrival_event(cpc)
      REMOVE cpc from active_propagation_set
    CANCEL all pending certificate-arrival / BlockAcceptancePoint / resume / HashWorkEvent events bound
           to old_TemplateID
    CLEAR every acceptance_batch_registry entry whose acceptance_point candidates are bound to old_TemplateID
    RECORD template_closure(RoundID, old_TemplateID)
  RETURNS: template_closure_record
  NOTE: G8/TV50: template refresh clears old-template candidate contexts, batch registries, hash
        events, and propagation events, but modifies NO historical record. Template refresh does NOT
        end the round; it discards the OLD search domain. Old coverage and
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
    # G8: disposition EVERY live propagation context, cancel its events, and clear the registries. A
    #     miner paused by a cancelled candidate is NOT resumed (the round is ending); it closes via
    #     CloseRoundAssignments with stop_reason = ROUND_ABORTED.
    FOR EACH cpc in SORT(active_propagation_set BY CandidateID ascending):
      SET status(cpc) <- CANCELLED
      CANCEL every event in certificate_arrival_events(cpc)
      CANCEL block_arrival_event(cpc)
    CLEAR active_propagation_set
    CLEAR acceptance_batch_registry                             # cancel any pending acceptance batches
    # D7: centralised closure of ALL open assignments and miner paths (wires the ROUND_ABORTED
    #     EnterLowPowerListen disposition; cancels pending wake/resume/certificate/hash-work events).
    CALL CloseRoundAssignments(RoundContext, disposition = ROUND_ABORTED, stop_reason = ROUND_ABORTED)
    finalise energy_ledger; ASSERT per-miner sums (I6) and network sum (I7);
        ASSERT durations reconcile to horizon T (I5)
    RETAIN zero-block/partial outcome in dataset                # I14; NA metrics per I15
    TRANSITION round_state -> ROUND_ABORTED                     # bumps state_version (G10); SecurityFloorEvaluate stale-noops after
  RETURNS: abort_record
  NOTE: G8: RoundAbort dispositions all live candidates and clears active_propagation_set and
        acceptance_batch_registry, so no stale candidate event or acceptance batch survives the abort (TV47).
```

---

## Deterministic-vs-sampling summary

The ONLY `[SIMULATION SAMPLING]` steps in the entire specification are:

1. **HashWorkEvent** — whether a modeled execution unit meets the fixed target `D` (G9; formerly the
   `ActiveHashing` loop step).
2. **AdversarialParticipationChangeEvent scheduling** — WHEN/WHICH adversarial miner enters or exits
   `ACTIVE_HASHING` (the adversarial-participation model draw, G3). Each such event applies its state
   change through `ApplyMinerStateTransition`; `H_honest(t)`, `H_adversarial(t)`, `H_active(t)` are
   then computed **deterministically** from the census by the hook and by `ActiveHashRateUpdate`
   (which is now COMPUTE-ONLY — it never samples or mutates the census). `H_adversarial(t)` is
   **never** sampled independently after `H_active(t)` (I17).
3. **StartWake** — the wake latency draw (F5). The draw now lives in `StartWake`; the scheduled
   `WakeCompleteEvent` consumes it deterministically at the completion timestamp. Every activation
   caller (`RangeAssign`, `ReserveActivate`, `RangeReassign`, `TemplateRefresh`, `ResumeFromPause`)
   reaches this single draw through `StartWake`.
4. **ExhaustionAdjudicate** and **FullRangeExhaustNoSolution** — the adversarial-path audit selection
   (`audit_selection_model`) that decides whether a `reported_exhaustion` claim is audited
   against simulator ground truth (`actual_exhaustion`). This is the modeled audit/detection
   abstraction of CR5; the comparison itself (`audit_result`, `claim_accepted_or_rejected`) is
   deterministic once the audit is selected.

The Stage-1F/1G procedures add **no** new sampling site beyond relocating the adversarial-participation
draw (item 2) into `AdversarialParticipationChangeEvent` scheduling. `ApplyMinerStateTransition` (F6),
`WakeCompleteEvent`/`StartHashing`/`HashWorkEvent` state logic (F5/G9), `CreatePendingAssignment` (F4/G2),
`CreatePropagationContext` (F1/G6), `HandlePropagationFailure` (E3/F2/F3), `RenewAssignment` (F7),
`AdversarialParticipationChangeEvent` (its STATE CHANGE, G3), the acceptance cluster
(`BlockAcceptancePoint` register + `AcceptanceBatchFinalize`, G5/E6/F3), and the microphase / event
ordering (G5/F8) are entirely deterministic. Identifiers are deterministic (`CandidateID =
(RoundID, seq)`, G7); iteration is stably sorted; the tie-breaks (`candidate_hash` then `MinerID` for
acceptance; `(CandidateID, MinerID, AssignmentID, seq)` within an event type) contain **no** random
draw and are independent of data-structure iteration order.

Every other step is deterministic protocol logic. This separation is deliberate: it keeps the
protocol's decision logic reproducible and audit-checkable against `I1..I17`, while confining
all randomness to clearly labelled model draws that exist solely because Stage-1 evaluation is
a simulation and not a real deployment. None of the above is executable source.

---

## 21. Global event-priority contract (F8, superseded by the G5 microphases)

When two or more scheduled events carry the **exact same** `event_time`, they are processed in a
**deterministic** order. **Stage 1G replaces the flat F8 priority sequence with the explicit
microphase contract of §0.7** (full spec in `STAGE_01G_EVENT_MICROPHASE_SPEC.md`): terminal
closure → template refresh → collect all block arrivals → `AcceptanceBatchFinalize` (one atomic
arbitration+closure) → security-floor evaluation (terminal-guarded) → certificate/discovery/…
events. Where this section's ordering differs from §0.7, **§0.7 (microphases) is authoritative**.
The historical F8 table (`STAGE_01F_EVENT_PRIORITY_TABLE.md`) remains a frozen Stage-1F artifact and
is not modified. The two-level structure below is retained for the intra-type tie-break, which the
microphases reuse verbatim.

The contract has two levels:

1. **Inter-type priority.** Same-timestamp events of different types fire in this fixed order
   (highest first), so that no event ever acts on a round/miner/assignment that a
   higher-priority same-timestamp event has already invalidated:

       1  RoundAbort closure            (ROUND_ABORTED)
       2  Round-acceptance closure      (ValidBlockAccept -> ROUND_ACCEPTED)
       3-4  Collect all block arrivals (BlockAcceptancePoint register) then AcceptanceBatchFinalize (G5)
       4  Template invalidation / refresh (TemplateRefresh / CloseTemplateAssignments)
       5  Security-floor evaluation / breach (SecurityFloorEvaluate)
       6  Full-block arrival            (BlockAcceptancePoint)
       7  Certificate arrival           (CertificateArrival)
       8  Solution discovery            (HashWorkEvent hit -> ScheduleSolutionPropagation)
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
