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
  - Invariants `I1..I19` are defined in `STAGE_01_INVARIANT_CATALOGUE.md`.
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

**(0.2) Event envelope (F1, extended with `delta_cycle`/`microphase` in H2; `seq` owned by ScheduleEvent
in J4/J9; `envelope_namespace`/`hook_id` in Q6).** Every scheduled event carries an immutable envelope:

    { envelope_namespace, event_type, event_time, delta_cycle, microphase, RoundID, TemplateID,
      CandidateID?, PropagationID?, MinerID?, AssignmentID?, assignment_version?, seq, hook_id? }

**Q6 (tagged namespace).** `envelope_namespace in {ORDINARY_EVENT, RUN_HOOK}` partitions the identity space:
ordinary queued events (minted by `ScheduleEvent`) carry `envelope_namespace = ORDINARY_EVENT`; a RUN-LEVEL
hook envelope (currently only `CloseRoundAtHorizon`, §20b) carries `envelope_namespace = RUN_HOOK` and a
`hook_id` (e.g. `HorizonHookID = (RunID, T, HORIZON_CLOSE)`). **Collision freedom derives from the namespace
TAG, not from a magic delta-cycle number:** an `ORDINARY_EVENT` envelope and a `RUN_HOOK` envelope are
distinct even if their numeric `event_seq`/`delta_cycle` coincide, because their `envelope_namespace` (and
`hook_id`) differ. A `TransitionEventID` (J3) includes `envelope_namespace` (and `hook_id` when
`RUN_HOOK`), so a run-hook transition and an ordinary transition can never share a `TransitionEventID`.
`CandidateID` and `PropagationID` are REQUIRED on every certificate-arrival, block-arrival,
validation, timeout, cancellation, and resume event. `microphase` is the target microphase (§0.7);
`delta_cycle` is the causal generation within one `event_time` (H2). Events are ordered by the total
key `(event_time, delta_cycle, microphase, stable_tie_key, seq)`, where `stable_tie_key =
(CandidateID, MinerID, AssignmentID)` and `seq` is the value of the single per-run monotonic
`event_creation_seq` counter (J4), assigned atomically by the central scheduler `ScheduleEvent`
(§0.7e/J9) AFTER the deterministic ordering is established, used ONLY as the final tie-break. There is
no ambient undeclared seq: every envelope's `seq` comes from `ScheduleEvent`. A propagation context is
NEVER identified by `RoundID` alone.

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
in H2; security decision relocated to an event-time epilogue in I-01/I-02).** At each `event_time` the
loop processes events in explicit **microphases**: PHASE 1 terminal abort / previously-committed
closure; PHASE 2 template invalidation/refresh; PHASE 3 collect ALL full-block arrivals into
`acceptance_batch_registry` (each `BlockAcceptancePoint` only REGISTERS and returns); PHASE 4 run
`AcceptanceBatchFinalize` exactly once per (timestamp, acceptance point) — validate all collected
candidates, select a winner, commit acceptance and close the round ATOMICALLY; PHASE 5+ certificate
arrivals, solution-discovery, range completion, reported exhaustion, lease expiry, wake completion,
resume, periodic monitoring. Round-acceptance closure is the atomic result of `AcceptanceBatchFinalize`,
not an independent preceding event. **The single security-floor decision is NO LONGER a microphase**
(it could be missed when no later event exists): it is the **event-time EPILOGUE**
`FinalizeEventTimeSecurityCensus(event_time) → SecurityFloorEvaluate`, run EXACTLY ONCE by
`ProcessEventTime` AFTER the whole `event_time` is quiescent (all ordinary and delta-cycle events
drained), keyed by `event_time` alone (I-01/I-02, terminal-first + legal-source guarded, I-05/G10).
**The authoritative same-timestamp contract is `STAGE_01G_EVENT_MICROPHASE_SPEC.md`, extended by the H2
delta-cycle rule below and the I-01/I-02 epilogue; the frozen Stage-1F
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
This rule governs, in particular: a zero-latency `WakeCompleteEvent` (H5); `ResumeFromPause`;
candidate-failure cleanup (`HandlePropagationFailure` and its scheduled resumes); and ANY
same-`event_time` event created inside another handler. The security-floor decision is NOT scheduled
as such an event; it is the event-time epilogue (I-01/I-02) that `ProcessEventTime` runs once after
ALL delta-cycles at `event_time` are drained, so no `delta_cycle` can strand a pending decision. The
full contract, worked examples, and the required-race table are in `STAGE_01H_DELTA_CYCLE_CONTRACT.md`
(extended by `STAGE_01I_EVENT_TIME_EPILOGUE_SPEC.md`). Within a microphase, ties break by
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

**(0.7c) Terminal-round security guard (G10/I-05).** `SecurityFloorEvaluate` is invoked ONLY by the
event-time epilogue and carries `(RoundID, TemplateID, state_version)`. It returns `terminal_stale_noop`
— never transitioning to `SECURITY_RECOVERY` — when the round is already `ROUND_ACCEPTED`/`ROUND_ABORTED`
(checked FIRST, before any breach recording, I-05) or the evaluation belongs to a stale
`RoundID`/`TemplateID`/`state_version`.

**(0.7d) Explicit event-time driver and security epilogue (I-02).** The event loop advances simulated
wall-clock time ONE `event_time` at a time via `ProcessEventTime(event_time)` (below). For a given
`event_time = t` it DRAINS every ordinary and delta-cycle event at `t` — including same-`event_time`
events generated inside handlers — in deterministic `(delta_cycle, microphase, stable_tie_key, seq)`
order, until the queue holds no further ordinary event at `t`. ONLY THEN does it run the security
EPILOGUE `FinalizeEventTimeSecurityCensus(t)` exactly once and UNCONDITIONALLY (S6 — the procedure itself
returns `no_census_change` when nothing is dirty; the CALL is not guarded), mark `t`
finalised, and advance to the next `event_time`. Two guarantees follow: (a) the epilogue runs even when
no later event exists (it is not itself a queued event that could be absent); (b) no ordinary event may
be scheduled into an already-finalised `event_time`, and any participation-changing action produced by
the security decision is scheduled at a **strictly later** `event_time`, so a recovery action can never
change `H_active` after the final decision at `t`.

```
PROCEDURE ProcessEventTime
  INPUTS: RoundContext, event_time t, is_horizon = (t == run_horizon_T), allow_empty_horizon = false,
          RunHookContext = null
          # O1: is_horizon marks the fixed horizon T. P1: allow_empty_horizon permits a SYNTHETIC horizon
          #     invocation at t = T even when NO ordinary event exists at T (the horizon-sentinel step).
          # P2: RunHookContext (the run-hook envelope owner) is supplied by the run driver for the horizon step;
          #     it is threaded to CloseRoundAtHorizon (§20b). It is unused when is_horizon is false.
  PRECONDITIONS: t not in finalised_event_times;
                 t <= run_horizon_T (no ordinary event is ever scheduled beyond T — O2/§0.7e);
                 # P1: normally t is the earliest unprocessed event_time on the queue. The ONE exception is the
                 #     synthetic horizon-sentinel call ProcessEventTime(T, is_horizon = true, allow_empty_horizon
                 #     = true) made by RunEventLoopToHorizon (§0.7d-run) after every event_time < T is drained:
                 #     it is permitted even if the queue holds NO event at T, so the horizon sequence always runs.
  EFFECTS:
    # I-02/P1: DRAIN t to quiescence in deterministic order, INCLUDING handler-generated same-t events. The
    #          drain may be EMPTY (no ordinary event at t) for a synthetic horizon invocation — that is legal.
    LOOP:
      IF no ordinary event remains at event_time = t: BREAK       # quiescent (all delta-cycles drained; empty at a synthetic horizon)
      SET current_delta_cycle <- smallest delta_cycle with a pending event at t
      FOR EACH event e at (t, current_delta_cycle) IN ASCENDING (microphase, stable_tie_key, seq):
        ASSERT t not in finalised_event_times                     # never dispatch into a finalised time
        # L1: MATERIALISE the ONE dispatch envelope for e. Every miner transition and every StartWake done
        #     synchronously while handling e binds ITS (event_time, delta_cycle, event_seq) from THIS record;
        #     no handler reads an ambient/undeclared seq and none manually stamps EQ.event_creation_seq.
        SET EQ.current_microphase <- microphase(e); SET EQ.current_event_seq <- seq(e)
        # R3: MATERIALISE the full ORDINARY_EVENT identity. Every ordinary dispatch envelope carries
        #     envelope_namespace = ORDINARY_EVENT and hook_id = null, so every miner transition done while handling
        #     e threads the COMPLETE identity (namespace fields included) into ApplyMinerStateTransition (§0.9/R3),
        #     never only the numeric (event_time, delta_cycle, event_seq).
        SET dispatch_envelope <- { envelope_namespace = ORDINARY_EVENT, hook_id = null,      # R3: ORDINARY_EVENT identity
                                   event_time = t, delta_cycle = current_delta_cycle, event_seq = seq(e),
                                   microphase = microphase(e) }        # e's OWN enqueued envelope (§0.7f/L1/R3)
        DISPATCH e WITH dispatch_envelope                         # its handler threads dispatch_envelope onward,
                                                                  #   may schedule further events at t per the
                                                                  #   delta-cycle rule (§0.7-H2) or at a later time
      # loop re-evaluates: a handler may have added a (t, current_delta_cycle+1) event (forward only)
    # ---- HORIZON CLOSURE (O1/P1: run-level hook, ONLY at t = T, interposed BETWEEN drain and epilogue) ----
    # After T is drained to quiescence (possibly an EMPTY drain for a synthetic horizon invocation, P1), if the
    # run's current round is still NONTERMINAL, close it at the horizon through the named CloseRoundAtHorizon
    # hook (§20b) so the round is ALREADY terminal when the T epilogue runs. This is a direct CALL, NOT a queued
    # event. CloseRoundAtHorizon moves miners off ACTIVE_HASHING, which sets a COHERENT security_census_dirty[T]
    # + latest_security_census[T] (via ApplyMinerStateTransition) — the T census CREATED by horizon closure (P1).
    IF is_horizon AND round_state NOT in {ROUND_ACCEPTED, ROUND_ABORTED}:
      CALL CloseRoundAtHorizon(RoundContext, RunHookContext)      # O1/§20b/P2: -> ROUND_ABORTED via deterministic run-hook envelope
    # ---- CANONICAL EVENT-TIME TAIL (R2): ONE security epilogue, ONE recovery application, ONE settlement ----
    # R2 removes the earlier "epilogue #1 / epilogue #2" contradiction: FinalizeEventTimeSecurityCensus runs
    # EXACTLY ONCE per event_time and is the SOLE security-floor decision for t; the post-application census is
    # SETTLED (not re-decided) by FinalizePostRecoveryApplicationState. R1 forbids the post-epilogue application
    # from enqueuing any ordinary event at the already-drained t.
    #
    #   (1) FinalizeEventTimeSecurityCensus(t)   — EXACTLY ONCE and UNCONDITIONALLY (S6); the one security-floor
    #                                              decision for t (I-01/I-02; Q1 versions the recovery census while in
    #                                              SECURITY_RECOVERY). The ONLY place at t that records a breach or
    #                                              mints a recovery episode/decision. It is NOT guarded by
    #                                              `IF security_census_dirty[t]` — the procedure OWNS that check and
    #                                              returns no_census_change when nothing is dirty (S6).
    #   (2) ApplyRecoveryCompletionAfterEpilogue(t) — applies AT MOST ONE fresh, matching, due decision (Q2/R4).
    #                                              Its exit transition changes round_state only; R1 FORBIDS it (and
    #                                              CompleteSecurityRecovery branch C) from enqueuing any ordinary
    #                                              event whose target_event_time = t — a zero-latency continuation
    #                                              is seated at next_representable_simulation_time(t) (§10a/R1).
    #   (3) ApplyRecoveryAssignmentContinuationAfterEpilogue(t) — T1: applies branch-C RESTORED (the deferred
    #                                              REDISTRIBUTION-ONLY continuation) AFTER the epilogue, mutually
    #                                              exclusive with (2) for one episode at one event_time; enqueues nothing at t (T7).
    #   (3b) ApplyRecoveryWorkAfterEpilogue(t) — U1: performs recovery WORK (reserve activation / redistribution) while
    #                                              the floor is still breached; the round STAYS SECURITY_RECOVERY and
    #                                              NOTHING is marked RESTORED. Mutually exclusive with (2)/(3) per episode
    #                                              per event_time. Its wakes are seated STRICTLY LATER (U2/T7).
    #   (4) FinalizePostRecoveryApplicationState(t) — EXACTLY ONCE when the application re-dirtied t; a post-
    #                                              application SETTLEMENT, NOT a second security-floor decision. It
    #                                              archives the terminal/post-application census
    #                                              (POST_RECOVERY_APPLICATION, R5) and CLEARS security_census_dirty[t];
    #                                              it NEVER calls SecurityFloorEvaluate, seats a recovery decision,
    #                                              or enqueues an event at t (R2).
    CALL FinalizeEventTimeSecurityCensus(RoundContext, t)        # R2/S6 step 1: the ONE (UNCONDITIONAL) security epilogue for t
    CALL ApplyRecoveryCompletionAfterEpilogue(RoundContext, t)    # R2 step 2 / Q2/R4/S3: post-quiescence recovery COMPLETION application
    CALL ApplyRecoveryAssignmentContinuationAfterEpilogue(RoundContext, t)   # T1: post-epilogue branch-C CONTINUATION application (mutually exclusive with the above)
    CALL ApplyRecoveryWorkAfterEpilogue(RoundContext, t)          # U1: post-epilogue recovery WORK (reserve activation / redistribution); NEVER applies RESTORED
    CALL FinalizePostRecoveryApplicationState(RoundContext, t)    # R2 step 3: single post-application settlement (NOT a 2nd decision)
    # (5) R1/R2/T7/U4 FINALISATION ASSERTION. t may be finalised ONLY when it is quiescent, its census is settled, and
    #     no recovery-continuation / recovery-work application remains due at t (checked via the EXPLICIT due status, U4).
    ASSERT no ordinary event remains with event_time = t          # R1: the post-epilogue application enqueued NOTHING at t (T7: incl. StartWake/re-arm strictly later)
    ASSERT security_census_dirty[t] = false                       # R2: FinalizePostRecoveryApplicationState settled t (no dirty census left)
    ASSERT no recovery_decisions[*].continuation_due_status = DUE with continuation_due_at_event_time = t
                                                                  # U4/T7: every DUE continuation at t was explicitly CONSUMED/SUPERSEDED/CANCELLED (not inferred from a timestamp)
    ASSERT no recovery_work[*].due_status = DUE with due_at_event_time = t
                                                                  # U1/U4: every DUE recovery-work fact at t was explicitly consumed by ApplyRecoveryWorkAfterEpilogue
    ADD t to finalised_event_times                               # t is now closed to ordinary events (P1: T is ALWAYS finalised here)
    # any participation action the decision created was scheduled at a STRICTLY LATER event_time (I-02/R1),
    # so it cannot alter the census that this epilogue already finalised at t.
    ADVANCE simulated wall-clock time to the next event_time on the queue
  RETURNS: event_time_finalised(t)
  NOTE: I-02: FinalizeEventTimeSecurityCensus is an EPILOGUE, not a normal microphase event; it cannot be
        "missed" because it is invoked structurally by this driver after quiescence, not dispatched from
        the queue. Draining to quiescence first guarantees the single decision uses the FINAL
        event-time census (I-01) and that no stranded delta-cycle census can trigger recovery. O1: this is
        the SOLE event-loop driver — no handler ever re-enters it. At the horizon T it interposes the
        run-level CloseRoundAtHorizon hook (§20b) BETWEEN the drain and the epilogue, so the horizon epilogue
        is a terminal_stale_noop; the run-level FinalizeSimulationRun (§20a) is then invoked by the RUN DRIVER
        (§0.7d-run) AFTER ProcessEventTime(T) returns — it is NOT a queued event.

PROCEDURE RunEventLoopToHorizon                                   # O1/P1: the RUN-LEVEL driver (top-level loop)
  INPUTS: RunContext, RoundContext
  PRECONDITIONS: a run is in progress with a fixed horizon run_horizon_T = T; the queue holds only
                 event_times <= T (O2: ScheduleEvent rejects any target_event_time > T)
  EFFECTS:
    # O1: ProcessEventTime is the SOLE event-loop driver; this run-level loop only SELECTS the next
    #     event_time and never itself dispatches an event.
    # P1: process only event_times STRICTLY LESS THAN T here. Any event AT T is drained by the SINGLE
    #     horizon-sentinel invocation below, so the horizon sequence runs EXACTLY ONCE.
    WHILE the queue has an unprocessed event_time t with t < T:
      SET t <- the earliest unprocessed event_time on the queue
      CALL ProcessEventTime(RoundContext, t, is_horizon = false)
    # P1 HORIZON SENTINEL — force EXACTLY ONE horizon-time processing step, even when the queue holds NO event
    #    whose event_time = T. This synthetic invocation drains any events AT T (possibly none), interposes
    #    CloseRoundAtHorizon (§20b) when the round is nonterminal, finalises the T census created by that
    #    closure, and ADDS T to finalised_event_times. It is guarded so it runs at most once.
    IF T not in finalised_event_times:
      CALL ProcessEventTime(RoundContext, T, is_horizon = true, allow_empty_horizon = true,
                            RunHookContext = RunContext.RunHookContext)   # P2: supply the run-hook envelope owner
    # O1: RUN-LEVEL FINALISER — a post-ProcessEventTime(T) run-driver HOOK, NOT a queued event. By now T is in
    #     finalised_event_times, any nonterminal round was horizon-closed inside ProcessEventTime(T) (§20b), and
    #     the T epilogue has run (terminal_stale_noop). FinalizeSimulationRun performs ONLY the single
    #     FINAL_RUN_END settle + I5/I6/I7 reconciliation; it ASSERTS the round is terminal (gate 2).
    CALL FinalizeSimulationRun(RunContext, RoundContext)          # O1/N1: run-level hook (not queued)
  RETURNS: run_completed(T)
  NOTE: O1/P1: the canonical horizon sequence lives HERE — process every event_time < T via ProcessEventTime,
        THEN a SINGLE horizon-sentinel ProcessEventTime(T) (synthetic, allow_empty_horizon) that always runs
        (even with an empty T queue), so a nonterminal round is ALWAYS horizon-closed and T is ALWAYS finalised
        before FinalizeSimulationRun. Nothing below RUN_FINALISE is a queued microphase; FinalizeSimulationRun
        and CloseRoundAtHorizon are run-level hooks, never enqueued.
```

**(0.7d-run) Run-level driver and the canonical horizon sequence (O1; horizon sentinel P1).**
`ProcessEventTime` is the SOLE event-loop driver; a handler NEVER re-enters it. The RUN-LEVEL driver
`RunEventLoopToHorizon` (above) processes every `event_time` **strictly less than** `T` via `ProcessEventTime`,
then makes ONE **horizon-sentinel** invocation `ProcessEventTime(T, is_horizon = true, allow_empty_horizon =
true)` (guarded by `T not in finalised_event_times`), then invokes `FinalizeSimulationRun` (§20a) as a
post-`ProcessEventTime(T)` run-level HOOK. **P1 (force exactly one horizon-time step):** the horizon-sentinel
invocation runs EVEN WHEN the queue holds no event whose `event_time = T`, so the horizon sequence always
occurs exactly once — an ordinary event at `T` is NOT required. The canonical horizon sequence is therefore:
(1) process every `event_time < T`; (2) the horizon sentinel drains any events AT `T` to quiescence (possibly
an EMPTY drain); (3) if the run's current round is still nonterminal, run `CloseRoundAtHorizon` (§20b) — the
named horizon-close hook that closes the round via `CloseRoundAssignments` and transitions it to
`ROUND_ABORTED` with a DISTINCT horizon-end disposition, using ONE deterministic run-hook envelope (P2) and
scheduling NO ordinary event after the drain; (4) run the `T` epilogue `FinalizeEventTimeSecurityCensus(T)`,
which — the round now being terminal — is a `terminal_stale_noop` that FINALISES the `T` census created by
horizon closure (clears `security_census_dirty[T]`) and adds `T` to `finalised_event_times`; (5) ONLY THEN
invoke the run-level `FinalizeSimulationRun`, which ASSERTS the round is terminal (so a nonterminal round
cannot reach it without horizon closure) and performs ONLY the single `FINAL_RUN_END` `SettleResidencyBoundary`
+ the I5/I6/I7 reconciliation + sets `run_finalised`. `FinalizeSimulationRun` and `CloseRoundAtHorizon` are
RUN-LEVEL hooks, NOT queued events; `RUN_FINALISE` is therefore NOT an ordinary microphase in the queue map
(§0.7g/§21) but a post-quiescence run-level action. Because `ScheduleEvent` rejects any `target_event_time >
T` (O2/§0.7e), no ordinary event ever remains with `event_time > T`, so `FinalizeSimulationRun`'s former
internal DRAIN is unnecessary and is REMOVED (the run driver has already drained every `event_time <= T`).

**(0.7e) Central scheduler contract (J9; complete dispatch context K8; sole delta-cycle authority L6).**
Every event enters the queue through ONE interface, `ScheduleEvent` (below), which reads and updates a
single explicit `EventQueueContext`. Throughout this document, an expression `SCHEDULE event E(...) AT
event_time = τ, microphase = m` is SHORTHAND for `CALL ScheduleEvent(EventQueueContext, RoundContext, E,
τ, m, envelope_fields)` — it is NOT a distinct enqueue path; there is exactly ONE enqueue interface.
**The caller supplies the target `event_time` and `microphase` ONLY — it does NOT supply `delta_cycle`;
`ScheduleEvent` DERIVES it (K8).** **L6 (sole delta-cycle authority).** `ScheduleEvent` is the SOLE
authority over `delta_cycle`: NO `SCHEDULE` expression, NO `CALL ScheduleEvent(...)` argument, and NO
handler anywhere in this document supplies, writes, or overrides a `delta_cycle`. Every `delta_cycle`
value that appears in the text is EITHER the value `ScheduleEvent` derived for an enqueued event OR the
`dispatch_envelope.delta_cycle` that `ProcessEventTime` read back from an already-derived envelope at
dispatch. Any `delta_cycle = …` shown in a `SCHEDULE` expression elsewhere is the DERIVED value,
illustrative of what `ScheduleEvent` computes (e.g. the H5 zero-latency wake's forward `delta_cycle + 1`),
never a caller override. In particular, `StartWake` schedules its `WakeCompleteEvent` through
`ScheduleEvent` with ONLY `(target_event_time, target_microphase)` — positive latency → `target_event_time
= now + wake_latency`; zero latency → `target_event_time = now, target_microphase = WAKE_COMPLETE` — and
`ScheduleEvent` alone derives the delta-cycle (future time → 0; same-time zero-latency wake → the forward
cycle, never backward).

```
STRUCTURE EventQueueContext (per-RUN; K8; the sole dispatch/scheduling state)
  event_queue           : the discrete-event priority queue (ordered by the total-order key below)
  current_event_time    : the event_time currently being dispatched (set by ProcessEventTime)
  current_delta_cycle   : the delta_cycle currently being dispatched (H2)
  current_microphase    : the microphase of the event currently being dispatched
  current_event_seq     : L1 — the event_creation_seq of the event currently being dispatched (set by
                          ProcessEventTime from the dispatched event's OWN enqueued envelope). Together
                          (current_event_time, current_delta_cycle, current_event_seq) form the CURRENT
                          `dispatch_envelope` — the ONE sanctioned (event_time, delta_cycle, event_seq) that
                          every synchronous miner transition and every StartWake done while handling the
                          event binds from. It is an EXPLICIT dispatched-envelope field, NOT an ambient seq.
  event_creation_seq    : the ONE per-run monotonic event-creation counter (J4); owned SOLELY here
  finalised_event_times : set of event_times whose epilogue has run (I-02)
  run_horizon_T         : O2 — the fixed simulation horizon T (= run-end event_time). BINDING SCHEDULING
                          BOUND: ScheduleEvent REJECTS any target_event_time > run_horizon_T, so no ordinary
                          event is ever enqueued beyond T (target_event_time = T is legal). Same value the
                          run driver (§0.7d-run) and SettleResidencyBoundary (FINAL_RUN_END) use.

STRUCTURE RunHookContext (per-RUN; P2/Q6 — the SOLE owner of run-hook envelope identity)
  # P2: run-level HOOKS (not queued events) that mutate miner state — currently only the horizon close
  #     (CloseRoundAtHorizon, §20b) — obtain their envelope identity HERE, in the RUN_HOOK namespace (Q6),
  #     never from an ambient/undefined seq and never from EventQueueContext.event_creation_seq.
  run_hook_seq          : monotonic per-run counter for run-hook envelopes (deterministic; separate from
                          EventQueueContext.event_creation_seq). Initialised 0 at run start, preserved across rounds.
  applied_run_hook_ids  : Q6 — map RunHookID -> RUN_HOOK_STATE in {IN_PROGRESS, APPLIED}. A hook is marked
                          IN_PROGRESS when its close begins and APPLIED when it completes, so a PARTIAL invocation
                          cannot be replayed as a second FULL close; a hook already IN_PROGRESS/APPLIED is a
                          deterministic no-op on replay (horizon_close_duplicate_noop). Initialised empty at run
                          start, preserved across rounds.

# P2/Q6 run-hook constants (deterministic identities; collision freedom from the NAMESPACE TAG, not a magic number):
#   RUN_HOOK (envelope_namespace) — the tag that partitions run-hook envelopes from ORDINARY_EVENT envelopes (§0.2).
#                      A RUN_HOOK envelope is distinct from any ORDINARY_EVENT envelope even if their numeric
#                      event_seq/delta_cycle coincide — collision freedom derives from this TAG.
#   RUN_HOOK_CYCLE   — a declared NON-QUEUE delta_cycle value for run-hook envelopes (illustrative; it is NOT the
#                      source of collision freedom — the namespace tag is). ScheduleEvent never produces it.
#   HORIZON_CLOSE    — the run-hook KIND for the horizon close. HorizonHookID = (RunID, run_horizon_T, HORIZON_CLOSE)
#                      is the deterministic identity of the ONE horizon-close hook per run.
# RUN_HOOK_STATE in {IN_PROGRESS, APPLIED}   # Q6: explicit replay state so a partial close cannot replay as a full close

STRUCTURE PostEpilogueSchedulingContext (S7 — the declared source of a POST-EPILOGUE ScheduleEvent call)
  # S7: a post-epilogue scheduling caller is NOT an ordinary dispatched handler and NOT a sim-driver entry; it is
  #     ApplyRecoveryCompletionAfterEpilogue's branch dispatch (CompleteSecurityRecovery), run by ProcessEventTime
  #     AFTER the event_time is drained + the epilogue ran. This context makes that source EXPLICIT and lets
  #     ScheduleEvent enforce that the target is STRICTLY LATER than the drained source event_time.
  source_event_time      : the drained epilogue event_time t (= dispatch_envelope.event_time of the applied decision)
  source_envelope        : the dispatch_envelope of the applied recovery decision (its ORDINARY_EVENT identity)
  EventQueueContext      : the sole dispatch/scheduling state (the same EQ ScheduleEvent updates)
  RunContext             : the per-run owner (§1.0) — for symmetry with the other declared scheduling sources
  # ScheduleEvent(..., post_epilogue_context = this) requires target_event_time > source_event_time and derives
  # delta_cycle = 0; the event_creation_seq is STILL minted solely by ScheduleEvent (J4). No post-epilogue caller
  # may enqueue at source_event_time (R1 structural).

PROCEDURE ScheduleEvent
  INPUTS: EventQueueContext EQ, RoundContext, event_type, target_event_time, target_microphase,
          envelope_fields,   # MinerID?/AssignmentID?/assignment_version?/CandidateID?/PropagationID? as applicable
          post_epilogue_context = null   # S7: present ONLY for a POST-EPILOGUE call (ApplyRecoveryCompletionAfterEpilogue
                                         #     path); a PostEpilogueSchedulingContext (§0.7e). null for all other callers.
                            # K8: NO target_delta_cycle input — the caller cannot set it.
  PRECONDITIONS: S7 — ScheduleEvent may be called from EXACTLY ONE of three declared sources:
                 (1) a HANDLER dispatched by ProcessEventTime (EQ.current_* set); (2) a SIM-DRIVER handler with an
                 explicit DriverEventEnvelope (§0.7f/K4) supplying EQ.current_* values; or (3)
                 ApplyRecoveryCompletionAfterEpilogue's branch dispatch (CompleteSecurityRecovery), which supplies a
                 valid post_epilogue_context. A post-epilogue call MUST carry post_epilogue_context; no other call may.
  EFFECTS:
    # K8/J9 (1): reject scheduling into an already-finalised event_time (I-02).
    IF target_event_time in EQ.finalised_event_times:
      RETURN rejected_finalised_time        # a security-decision participation action MUST use a strictly later time
    # O2 (1-bis): BINDING HORIZON RULE. Reject any event scheduled BEYOND the fixed horizon T. The result is
    #     DETERMINISTIC and the event is NOT enqueued (never queued, never later dispatched), so no pending
    #     ordinary event can remain with event_time > T. target_event_time = T is LEGAL (it is the horizon
    #     itself); only target_event_time > T is rejected.
    IF target_event_time > EQ.run_horizon_T:
      RECORD post_horizon_event(event_type, target_event_time, target_microphase)   # audit-only log
      RETURN post_horizon_event_rejected    # deterministic: the caller records the rejection; nothing is enqueued
    # S7 (2-post): POST-EPILOGUE SCHEDULING RULE. A post-epilogue caller MUST target a STRICTLY LATER event_time than
    #     its source (the drained epilogue event_time), and the derived delta_cycle is DETERMINISTICALLY 0 at that
    #     future event_time. So a post-epilogue caller can NEVER enqueue at source_event_time (R1 becomes structural).
    IF post_epilogue_context != null:
      IF NOT (target_event_time > post_epilogue_context.source_event_time):
        RETURN rejected_post_epilogue_not_strictly_later   # S7: a post-epilogue event at/behind the source is REJECTED
      SET dc <- 0                            # S7: deterministically 0 at the strictly-later future event_time
    # K8 (2): DERIVE the target delta_cycle from the dispatch context; the caller never supplies it.
    ELSE IF target_event_time > EQ.current_event_time:
      SET dc <- 0                            # a FUTURE event_time starts its delta_cycle numbering at 0 (K8)
    ELSE IF target_event_time = EQ.current_event_time:
      # same event_time: forward rule (§0.7-H2). Later target microphase -> same cycle; at/earlier -> +1.
      IF target_microphase > EQ.current_microphase: SET dc <- EQ.current_delta_cycle
      ELSE:                                          SET dc <- EQ.current_delta_cycle + 1   # never backward
    ELSE:                                    # target_event_time < current_event_time
      RETURN rejected_backward_time          # K8: never schedule into the past
    # J9 (3): assign the per-run monotonic seq ATOMICALLY, AFTER the deterministic ordering is established.
    SET EQ.event_creation_seq <- EQ.event_creation_seq + 1
    SET seq <- EQ.event_creation_seq
    # J9 (4): attach the round/template epoch and the candidate envelope fields.
    CREATE envelope = { envelope_namespace = ORDINARY_EVENT,   # Q6: every ScheduleEvent envelope is ORDINARY_EVENT
                        event_type, event_time = target_event_time, delta_cycle = dc, microphase = target_microphase,
                        RoundID = RoundID_current, TemplateID = TemplateID_committed,
                        CandidateID?, PropagationID?, MinerID?, AssignmentID?, assignment_version?,
                        seq }                                   # seq is EQ.event_creation_seq (J4)
    # J9 (5): insert using the deterministic TOTAL-ORDER key.
    INSERT envelope INTO EQ.event_queue ORDERED BY (event_time, delta_cycle, microphase,
                                                    (CandidateID, MinerID, AssignmentID), seq)
  RETURNS: scheduled(envelope)
  NOTE: K8/J9: the SOLE enqueue interface, over the explicit EventQueueContext. It DERIVES delta_cycle
        (caller supplies only event_time + microphase), owns event_creation_seq (J4), rejects finalised
        (I-02), post-horizon (O2: target_event_time > T), and backward event_times, and inserts by the
        deterministic total-order key (G7/H2). Every `SCHEDULE` elsewhere is shorthand for a call here.
        O2: because this is the ONLY enqueue path and it rejects target_event_time > T, the queue can never
        hold an ordinary event beyond the horizon T — the run driver (§0.7d-run) drains every event_time <= T,
        so nothing is stranded past T.
```

**(0.7f) Driver event envelopes (K4; single sanctioned source L1).** A miner-state transition originated
by a SIM-DRIVER entry point (not a queued handler) carries an explicit `DriverEventEnvelope` so its
`(event_time, delta_cycle, event_seq)` are DEFINED, never ambient. **L1 (single source).** A
`DriverEventEnvelope` is obtained from EXACTLY ONE source: the entry point is itself SEATED on the queue
through `ScheduleEvent` (which alone mints `event_creation_seq`, J4/K8) and DISPATCHED by
`ProcessEventTime`, so its `dispatch_envelope` is the current dispatch envelope
`(EQ.current_event_time, EQ.current_delta_cycle, EQ.current_event_seq)`. **A driver entry point MUST NOT
manually stamp `next EQ.event_creation_seq` to build an envelope** — that manual form (permitted as an
alternative under K4) is WITHDRAWN by L1; the seq is owned solely by `ScheduleEvent` and reaches the entry
point only as the dispatched event's own seq. The driver entry points that transition miners —
`MinerRegister`, `PrepareParticipantsForNewRound`, `ReserveActivate`, `RoundInitialise`/`TemplateCommit`
participant actions, and any direct recovery/administrative entry — each receive their `dispatch_envelope`
from `ProcessEventTime` and THREAD it to every `ApplyMinerStateTransition` and every `StartWake`; no such
transition depends on an undeclared ambient `event_seq`, and none consumes a manually stamped seq (L1/K4).

**(0.7g) Canonical event-type → microphase mapping (M5).** EVERY operational enqueue is a `ScheduleEvent`
call (or the `SCHEDULE event E(...) AT event_time = τ, microphase = m` shorthand for one, §0.7e), and it
MUST supply an EXPLICIT `target_microphase` — no enqueue omits it. The target microphase of each event
type is FIXED by the following canonical mapping (ordinals are the same-timestamp inter-type priorities of
§21; a lower ordinal is processed first at a shared `event_time`). The event-time security decision is NOT
a queued microphase — it is the epilogue (I-01/I-02), so it has no mapping entry.

| Event type | Target microphase | §21 priority |
|-----------|-------------------|:-:|
| `BlockAcceptancePoint` (full-block arrival, register-only) | `FULL_BLOCK_ARRIVAL` | 5 |
| `CertificateArrival` | `CERTIFICATE_ARRIVAL` | 6 |
| `HashWorkEvent` (hash unit; may emit discovery/range-completion) | `HASH_WORK` | 7–9 |
| `LeaseExpiry` | `LEASE_EXPIRY` | 10 |
| `WakeCompleteEvent` | `WAKE_COMPLETE` | 11 |
| `ResumeFromPause` | `RESUME` | 12 |
| `AdversarialParticipationChangeEvent` | `PARTICIPATION_CHANGE` | 13a |
| `ActiveHashRateUpdate` / periodic monitoring | `MONITORING` | 13 |
| `RecoveryDeadlineEvent` (P3: records the deadline FACT + refreshes the census; the epilogue decides, §9a) | `RECOVERY_DEADLINE` | 13b |
| `RecoveryCompletionDueEvent` (Q2 step 1: records due + refreshes census; NO transition, §10a) | `RECOVERY_COMPLETION_DUE` | 13c |
| `RecoveryAssignmentContinuationDueEvent` (T1 step 1: records the continuation DUE fact + refreshes the census; NO transition / NO assignment install / NO APPLIED, §10a) | `RECOVERY_ASSIGNMENT_CONTINUATION_DUE` | 13d |
| `RecoveryWorkDueEvent` (U1 step 1: records the recovery-WORK DUE fact + refreshes the census; NO reserve activation / NO transition / NO APPLIED — the WORK is the post-epilogue hook, §9c) | `RECOVERY_WORK_DUE` | 13e |
| `SetupRetryEvent` (V8: deterministic retry of a rolled-back participant / template-refresh setup at a strictly-later event_time; stale-guarded on RoundID) | `ROUND_SETUP` | 0 |

`RecoveryDeadlineEvent`, `RecoveryCompletionDueEvent`, and `RecoveryAssignmentContinuationDueEvent` are ordinary
queued events (seated through `ScheduleEvent`, always at a deterministic `target_time <= T`, Q7/R1/T1). None
applies a recovery outcome: the completion application is `ApplyRecoveryCompletionAfterEpilogue` (Q2) and the
branch-C continuation application is `ApplyRecoveryAssignmentContinuationAfterEpilogue` (T1) — BOTH are
POST-epilogue hooks run by `ProcessEventTime` (not queued microphases); `CompleteSecurityRecovery` is an
INTERNAL branch-dispatch helper the completion hook calls. `RecoveryAssignmentContinuationDueEvent` (T1) only
RECORDS the due fact and refreshes the census at `next_representable_simulation_time(t)`; the branch-C
assignment rebuild + `CompleteAssignmentPhase` is performed by the POST-epilogue hook
`ApplyRecoveryAssignmentContinuationAfterEpilogue` at that strictly-later event_time — a STRICTLY LATER
event_time than the recovery application that seated it — so neither the recovery application nor the
continuation Due event enqueues assignment work at an already-drained event_time.
`RUN_FINALISE` is **NOT** in this queue map (O1): `FinalizeSimulationRun` is a run-level hook invoked by
`RunEventLoopToHorizon` after `ProcessEventTime(T)`, and `CloseRoundAtHorizon` is a run-level hook invoked
inside `ProcessEventTime(T)` — neither is a queued microphase.

`AcceptanceBatchFinalize` (microphase 4) is enqueued once per (timestamp, acceptance point) by
`BlockAcceptancePoint` at microphase `ACCEPTANCE_ARBITRATION`; round-closure/refresh transitions are the
atomic RESULT of dispatched handlers (§21 phases 1–4), not independently enqueued miner events. Every loop
that CREATES or CANCELS events iterates in a STABLE order (by `MinerID`, then `CandidateID`) BEFORE
`ScheduleEvent` assigns the monotonic `event_creation_seq` (J4/G7), so the seq order is reproducible.

**(0.7g-driver) Driver-entry-point seating rules (N3).** Every SIM-DRIVER entry point that is seated on the
event queue has a DECLARED event type, target microphase, stable tie key, required envelope fields, and a
declared right (or not) to create SAME-TIME delta-cycle events. No driver entry point receives a
`dispatch_envelope` without such a normative `ScheduleEvent` seating rule (the envelope is always the
dispatched event's own, per §0.7f). `RoundAbort` retains TERMINAL-ABORT priority (§21 item 1). **O1:**
`FinalizeSimulationRun` and `CloseRoundAtHorizon` are RUN-LEVEL hooks (NOT queued events) and therefore do
NOT appear in the seating table below — `FinalizeSimulationRun` is invoked by `RunEventLoopToHorizon` after
`ProcessEventTime(T)` (§0.7d-run), and `CloseRoundAtHorizon` is invoked inside `ProcessEventTime(T)` between
the `T` drain and the `T` epilogue (§20b) using ONE deterministic run-hook envelope (P2, identity
`HorizonHookID`). `RecoveryDeadlineEvent` (O3/P3, §9a) is a seated queued event that RECORDS the deadline FACT
and dirties the census — it selects NO outcome and seats NO completion; the event-time epilogue decides.

| Driver entry point | Event type | Target microphase | Stable tie key | Required envelope fields | May create same-time delta-cycle events? |
|--------------------|-----------|-------------------|----------------|--------------------------|:--:|
| `RoundInitialise` | `RoundInitialise` | `ROUND_SETUP` | `(RoundID)` | `event_time, delta_cycle, event_seq` | no (round setup is a fresh event_time) |
| `TemplateCommit` | `TemplateCommit` | `TEMPLATE_COMMIT` | `(RoundID, TemplateID)` | `event_time, delta_cycle, event_seq` | no |
| `PrepareParticipantsForNewRound` | `PrepareParticipants` | `ASSIGNMENT_SETUP` | `(RoundID, TemplateID)` | `event_time, delta_cycle, event_seq` | yes — its `StartWake`s may seat same-time `WakeCompleteEvent`s (H2/H5) |
| `MinerRegister` | `MinerRegister` | `REGISTRATION` | `(MinerID)` | `event_time, delta_cycle, event_seq` | no |
| `ReserveActivate` | `ReserveActivate` | `RECOVERY_ACTIVATE` | `(MinerID)` | `event_time, delta_cycle, event_seq` | yes — its `StartWake` may seat a same-time `WakeCompleteEvent` (H5) |
| `FullRangeExhaustNoSolution` | `FullRangeExhaust` | `RANGE_EXHAUST_ADJUDICATE` | `(RoundID, TemplateID)` | `event_time, delta_cycle, event_seq` | no |
| `RecoveryDeadlineEvent` | `RecoveryDeadlineEvent` | `RECOVERY_DEADLINE` | `(RoundID, RecoveryEpisodeID)` | `event_time, delta_cycle, event_seq` | no (P3: records the deadline fact + refreshes the census; seats nothing) |
| `RecoveryCompletionDueEvent` | `RecoveryCompletionDueEvent` | `RECOVERY_COMPLETION_DUE` | `(RoundID, RecoveryEpisodeID, RecoveryDecisionID)` | `event_time, delta_cycle, event_seq` | no (Q2: records due + refreshes census; NO transition — the application is the post-epilogue hook) |
| `RecoveryAssignmentContinuationDueEvent` | `RecoveryAssignmentContinuationDueEvent` | `RECOVERY_ASSIGNMENT_CONTINUATION_DUE` | `(RoundID, RecoveryEpisodeID, RecoveryDecisionID, ContinuationGeneration)` | `event_time, delta_cycle, event_seq` | no (T1: records the continuation DUE fact + refreshes the census; NO transition / NO assignment / NO APPLIED — the branch-C rebuild is the post-epilogue hook `ApplyRecoveryAssignmentContinuationAfterEpilogue`). It carries the full recovery identity + `ContinuationGeneration`; it is seated via the S7 PostEpilogueSchedulingContext (strictly-later) |
| `RecoveryWorkDueEvent` | `RecoveryWorkDueEvent` | `RECOVERY_WORK_DUE` | `(RoundID, RecoveryEpisodeID, RecoveryWorkID, WorkGeneration)` | `event_time, delta_cycle, event_seq` | no (U1: records the recovery-WORK DUE fact + refreshes the census; NO reserve activation / NO transition / NO APPLIED — the WORK is the post-epilogue hook `ApplyRecoveryWorkAfterEpilogue`). It carries the full recovery identity + `WorkGeneration`; it is seated via the U3 atomic seat (published only after a successful enqueue) |
| `SetupRetryEvent` | `SetupRetryEvent` | `ROUND_SETUP` | `(RoundID, setup_kind)` | `event_time, delta_cycle, event_seq` | no (V8: re-invokes PrepareParticipantsForNewRound / TemplateRefresh at a strictly-later event_time after a rolled-back setup; stale-guarded on RoundID) |
| `RoundAbort` | `RoundAbort` | `TERMINAL_ABORT` (§21 item 1) | `(RoundID)` | `event_time, delta_cycle, event_seq` | no |

Run-level hooks (NOT in the seating table, O1/Q2/R2): `CloseRoundAtHorizon` (§20b, invoked inside
`ProcessEventTime(T)` with ONE deterministic run-hook envelope, Q6), `FinalizeSimulationRun` (§20a, invoked by
`RunEventLoopToHorizon` after `ProcessEventTime(T)`, carrying NO dispatch_envelope),
`ApplyRecoveryCompletionAfterEpilogue` (§10a, Q2 — invoked by `ProcessEventTime` after the event-time
epilogue), `ApplyRecoveryAssignmentContinuationAfterEpilogue` (§10a, T1 — the post-epilogue hook that APPLIES the
branch-C continuation, invoked by `ProcessEventTime` after the event-time epilogue and after the completion
application), and `FinalizePostRecoveryApplicationState` (§10a, R2 — the single post-application settlement invoked
by `ProcessEventTime` after the application, NOT a second security-floor decision). None is enqueued; nothing is
ever scheduled past `T` (O2), and none enqueues an ordinary event at the already-drained `event_time` (R1/T1).

Same-timestamp ordering among the queued driver microphases follows the §21 inter-type order, with
`TERMINAL_ABORT` retaining top priority. `RecoveryDeadlineEvent` (`RECOVERY_DEADLINE`) and
`RecoveryCompletionDueEvent` (`RECOVERY_COMPLETION_DUE`) and the epilogue's floor decision are ordered per
I-02 (both recovery events are always seated at a deterministic later `event_time` than the decision/entry
that produced them, Q7).
**Envelope-fields column (N3).** The "required envelope fields" are the
fields the DISPATCHED event carries — every dispatched event has `(event_time, delta_cycle, event_seq)`.
A driver entry point that performs a miner transition or a `StartWake` THREADS its own
`dispatch_envelope` (a `dispatch_envelope` INPUT in its signature, M1); `RoundInitialise` and
`TemplateCommit` perform only round-registry setup and round-state transitions (no
`ApplyMinerStateTransition`, no `StartWake`), so they thread nothing onward and declare NO
`dispatch_envelope` INPUT — their dispatched event still carries the standard envelope, and no entry point
ever receives an envelope without the `ScheduleEvent` seating rule above.

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
  # --- per-ROUND registries (reset by RoundInitialise at each round; I4) ---
  active_propagation_set      : set of propagation-active CPCs (status PROPAGATING/PENDING_ACCEPTANCE)
  acceptance_batch_registry   : map (acceptance_timestamp, acceptance_point) -> list of registered block arrivals
  candidate_discovery_seq     : monotonic per-round counter for CandidateID (G7)
  block_accepted              : boolean flag, false until a block is accepted this round
  state_version               : monotonic round-state epoch, bumped on every round-state transition (G10)
  # --- O4/P3/P5/Q1/Q3 security-recovery episode registries (reset by RoundInitialise; keyed by RecoveryEpisodeID) ---
  recovery_episode_seq        : O4 — monotonic per-round counter advanced when the round ENTERS
                                 SECURITY_RECOVERY. RecoveryEpisodeID = (RoundID, recovery_episode_seq) is the
                                 DETERMINISTIC identity of one recovery episode (G7-style), immutable once minted.
  current_recovery_episode    : O4 — the RecoveryEpisodeID of the round's ACTIVE recovery episode while
                                 round_state = SECURITY_RECOVERY; null otherwise. Set on entry to
                                 SECURITY_RECOVERY, cleared when the episode's completion is finalised.
  recovery_deadline_reached   : P3 — map RecoveryEpisodeID -> boolean. Set true by RecoveryDeadlineEvent (§9a)
                                 when the recovery deadline ELAPSES. It records a FACT only; the epilogue decides.
  recovery_census_seq         : Q1 — monotonic per-episode counter advanced every time the epilogue evaluates a
                                 FINAL event-time census while round_state = SECURITY_RECOVERY. RecoveryCensusVersion =
                                 the value it takes; it VERSIONS each final recovery census.
  latest_recovery_census      : Q1 — map RecoveryEpisodeID -> recovery_census_record. Published by the epilogue on
                                 every final recovery census. A recovery_census_record includes: RecoveryEpisodeID,
                                 RecoveryCensusVersion, event_time, RoundID, TemplateID, state_version, H_active,
                                 H_honest, H_adversarial, q_adv, breach, deadline_reached. A pending decision binds to
                                 a RecoveryCensusVersion; a newer final census re-affirms (same outcome) or SUPERSEDES
                                 (contradicting outcome) it — so freshness is judged against EVERY final census, not
                                 merely against the existence of a newer RecoveryDecisionID.
  recovery_decision_seq       : P5 — monotonic per-round counter advanced each time the epilogue MINTS a recovery
                                 decision. RecoveryDecisionID = (RecoveryEpisodeID, recovery_decision_seq).
  recovery_decisions          : Q3/R4/S3/T1/T2/U4 — map RecoveryDecisionID -> decision_record { episode, outcome,
                                 bound_census_version (RecoveryCensusVersion), status, target_time, due_event_ref,
                                 due_at_event_time, due_dispatch_envelope, continuation_event_ref, continuation_generation,
                                 continuation_id, continuation_bound_census_version, continuation_due_at_event_time,
                                 continuation_due_dispatch_envelope, continuation_due_status (CONTINUATION_DUE_STATUS, U4),
                                 continuation_status (ARMED after a successful re-arm enqueue, U3) }. status in RECOVERY_DECISION_STATUS. This makes
                                 each decision an EXPLICIT identity with an explicit lifecycle, NOT one ambiguous
                                 boolean. R4: after the initial CREATED, EVERY status transition is written by the SOLE
                                 mutator SetRecoveryDecisionStatus (§9). S3: continuation_event_ref is the seated
                                 RecoveryAssignmentContinuationDueEvent (T1) of a DEFERRED branch-C decision (null
                                 otherwise), so Reconcile (on supersession) and CancelActiveRecoveryEpisode (on terminal
                                 closure) can cancel it. T2: continuation_generation / continuation_id identify the
                                 ACTIVE continuation (a reserve-dependent re-arm bumps the generation), and
                                 continuation_bound_census_version is the AUTHORITATIVE bound version that
                                 ReconcilePendingRecoveryDecisions keeps current and that
                                 ApplyRecoveryAssignmentContinuationAfterEpilogue reads + verifies against the latest
                                 final census — the immutable due event carries only the generation, never a stale version.
  pending_recovery_decisions  : Q3/S3 — map RecoveryEpisodeID -> SET of RecoveryDecisionIDs whose status is
                                 {CREATED, SCHEDULED} (still applicable), or APPLYING — TRANSIENTLY for branches A/B/D,
                                 or PERSISTENTLY for a DEFERRED branch-C decision until its continuation reaches HASHING
                                 (S3). It is the "remaining scheduled decision set" (P4/Q3). A decision is ADDED only
                                 after ScheduleEvent succeeds; REMOVED on SUPERSEDED, CANCELLED, APPLIED, SCHEDULE_FAILED,
                                 APPLY_FAILED, or HORIZON_DEFERRED. Multiple superseded/scheduled decisions may
                                 transiently coexist, so a set (not a boolean) is required.
  latest_recovery_decision    : P5/R6 — map RecoveryEpisodeID -> { decision_id, outcome, bound_census_version, status }.
                                 The most-recent decision for the episode. R6: it is a MUTABLE MIRROR kept ATOMICALLY
                                 consistent with recovery_decisions by SetRecoveryDecisionStatus (§9) — its status
                                 NEVER lags the underlying decision (never remains CREATED after the decision became
                                 CANCELLED / SCHEDULE_FAILED / SUPERSEDED / APPLIED / APPLY_FAILED).
  recovery_outcome_finalised  : O4/T4 — map RecoveryEpisodeID -> RecoveryOutcome. Set ONCE, ONLY when an outcome is
                                 ACTUALLY APPLIED: by ApplyRecoveryCompletionAfterEpilogue (branches A/B/D), or by
                                 ApplyRecoveryAssignmentContinuationAfterEpilogue when branch C reaches HASHING
                                 (RESTORED). AT MOST ONE finalised outcome per episode. T4: it is NOT set on a failed
                                 branch-C install (that records recovery_episode_disposition = RECOVERY_INSTALL_FAILED_ABORTED,
                                 never a fabricated UNRECOVERABLE), and NOT set by a TERMINAL_CANCELLED cleanup (S4).
  recovery_episode_disposition : S4/T4 — map RecoveryEpisodeID -> RECOVERY_EPISODE_DISPOSITION. Records how an episode
                                 ENDED WITHOUT an applied outcome: TERMINAL_CANCELLED when a round became terminal
                                 (ROUND_ACCEPTED/ROUND_ABORTED) while the episode was still active and its outcome had
                                 NOT been applied (CancelActiveRecoveryEpisode, §17a); RECOVERY_INSTALL_FAILED_ABORTED
                                 when a branch-C RESTORED installation failed after the irreversible mutation and the
                                 round was aborted (T4, §10a). Null while the episode is active or when an outcome was
                                 applied (recovery_outcome_finalised is set instead).
  # --- T3 branch-C installation registries (per-round; reset by RoundInitialise) ---
  recovery_install_in_progress : T3 — boolean, true ONLY during the SYNCHRONOUS branch-C installation sub-computation
                                 (round_state = ASSIGNMENT) inside ApplyRecoveryAssignmentContinuationAfterEpilogue;
                                 false otherwise. It appears in the T3 episode invariant below.
  recovery_install_seq        : T3 — monotonic per-round counter; RecoveryInstallID = (episode, recovery_install_seq).
  RecoveryInstallID           : T3 — the deterministic identity of one branch-C installation.
  active_recovery_install_decision : T3 — the RecoveryDecisionID whose branch-C installation is in progress (null otherwise).
  # RecoveryOutcome enum (O3): RESTORED (floor restored -> branches A/B/C) | UNRECOVERABLE (floor cannot be restored
  #   -> branch D -> RoundAbort(floor_unrecoverable), round only). RECOVERY_OUTCOME in {RESTORED, UNRECOVERABLE}.
  # RECOVERY_EPISODE_DISPOSITION in {TERMINAL_CANCELLED, RECOVERY_INSTALL_FAILED_ABORTED}   # S4/T4
  # RecoveryDecisionID = (RecoveryEpisodeID, recovery_decision_seq)   # P5: the versioned decision identity
  # RecoveryContinuationID = (RecoveryDecisionID, continuation_generation)   # T2: the ACTIVE continuation identity
  # RECOVERY_DECISION_STATUS in {CREATED, SCHEDULED, SUPERSEDED, APPLYING, APPLIED, SCHEDULE_FAILED,
  #                              APPLY_FAILED, APPLY_FAILED_TERMINAL, HORIZON_DEFERRED, CANCELLED}   # Q3/R4/S2/T4 (APPLY_FAILED_TERMINAL added)
  # A decision binds to RecoveryCensusVersion (Q1); it is APPLIED only after the epilogue of its OWN completion
  #   event_time re-affirms that version and the final census still matches its outcome (Q2).
  # T3 EPISODE INVARIANT (supersedes the S4 form):
  #   current_recovery_episode != null  IFF  ( round_state = SECURITY_RECOVERY
  #     OR ( round_state = ASSIGNMENT AND recovery_install_in_progress = true
  #          AND recovery_decisions[active_recovery_install_decision].status = APPLYING ) )
  #   The ASSIGNMENT branch is exercised ONLY inside the SYNCHRONOUS branch-C installation (no event boundary occurs
  #   within it), so the invariant holds at every event boundary. Every installation exit ends in exactly one of:
  #   HASHING + decision APPLIED; SECURITY_RECOVERY + decision APPLY_FAILED (rollback complete); ROUND_ABORTED +
  #   recovery_episode_disposition = RECOVERY_INSTALL_FAILED_ABORTED (T3/T4/T5). Reserve-dependent restoration is NOT a
  #   branch-C continuation (U1): it is recovery WORK — the round stays SECURITY_RECOVERY (reserve PENDING/WAKING)
  #   until a later final census with NO breach mints RESTORED.
  # --- U1/V6/V7 recovery-WORK registries (per-round; reset by RoundInitialise): work is DISTINCT from an outcome ---
  # A recovery-WORK action (reserve activation attempted WHILE the floor is still breached) is NEVER a RecoveryOutcome
  #   and is NEVER marked APPLIED as RESTORED. RESTORED / UNRECOVERABLE are decided ONLY from a final census
  #   (outcome_consistent_with_census, unchanged/not weakened). Recovery work runs while the round stays
  #   SECURITY_RECOVERY; a LATER final census with NO breach mints RESTORED, or breach+deadline mints UNRECOVERABLE, or
  #   breach-before-deadline continues recovery.
  # V6 RECOVERY_WORK_CLASS in { SECURITY_FLOOR_RECOVERY_WORK, COVERAGE_REPAIR_WORK }:
  #   SECURITY_FLOOR_RECOVERY_WORK — actions that can ACTUALLY change the ACTIVE_HASHING census (H_active/H_honest/q_adv):
  #     reserve activation, or a declared honest/adversarial participation replacement. ONLY this class is returned by
  #     ClassifyRecoveryWork and controls the breach-before-deadline outcome logic.
  #   COVERAGE_REPAIR_WORK — nonce-domain / assignment coverage repair (e.g. RANGE_REDISTRIBUTION_REQUIRED among the SAME
  #     ACTIVE_HASHING miners). It does NOT claim to restore H_active/H_honest/q_adv and does NOT control the
  #     breach-before-deadline outcome logic (a same-active-miner redistribution cannot change the census sums). A
  #     redistribution AFTER a no-breach census is the branch-C redistribution-only continuation (§10a).
  # RECOVERY_WORK_ACTION in { RESERVE_ACTIVATION_REQUIRED (SECURITY_FLOOR_RECOVERY_WORK),
  #                           RANGE_REDISTRIBUTION_REQUIRED (COVERAGE_REPAIR_WORK), NONE }   # U1/V6
  recovery_work_seq           : U1/U3 — monotonic per-round counter advanced each time the epilogue MINTS a recovery-work
                                 action. RecoveryWorkID = (RecoveryEpisodeID, recovery_work_seq).
  recovery_work               : U1/U3/U4/V7 — map RecoveryWorkID -> work_record { episode, action (RECOVERY_WORK_ACTION),
                                 work_class (RECOVERY_WORK_CLASS, V6), bound_census_version (RecoveryCensusVersion),
                                 work_generation, work_id (RecoveryWorkID), status (RECOVERY_WORK_STATUS), work_due_event_ref,
                                 due_at_event_time, due_dispatch_envelope, due_status (CONTINUATION_DUE_STATUS) }. A work
                                 action is an explicit identity with a COMPLETE lifecycle; it is NEVER a RecoveryDecisionID
                                 and is NEVER APPLIED. V7: EVERY RecoveryWorkID has exactly one live or terminal disposition.
  pending_recovery_work       : U1/V7 — map RecoveryEpisodeID -> the AT-MOST-ONE in-flight RecoveryWorkID (null otherwise).
                                 V7 INVARIANT: at most one work record per episode is in {ARMED, DUE, APPLYING}; before a
                                 new work identity is published, the prior one is atomically SUPERSEDED/CANCELLED, its
                                 queued event cancelled, and its due fact consumed (SeatRecoveryWork / ReconcilePendingRecoveryWork).
  # RECOVERY_WORK_STATUS in { CREATED, ARMED, DUE, APPLYING, CONSUMED, SUPERSEDED, SCHEDULE_FAILED, HORIZON_DEFERRED, CANCELLED }   # V7 (complete lifecycle)
  #   V7 persistence note: the SIX in-flight / terminal statuses { ARMED, DUE, APPLYING, CONSUMED, SUPERSEDED, CANCELLED }
  #   are the ones WRITTEN onto a live work_record (ARMED by SeatRecoveryWork's post-enqueue publish; DUE by
  #   RecoveryWorkDueEvent; APPLYING/CONSUMED by ApplyRecoveryWorkAfterEpilogue; SUPERSEDED by ReconcilePendingRecoveryWork/
  #   SeatRecoveryWork; CANCELLED by CancelActiveRecoveryEpisode). The remaining THREE — CREATED (the pre-publication
  #   candidate state before a work_record exists), SCHEDULE_FAILED (a rejected enqueue), and HORIZON_DEFERRED (t_due > T) —
  #   are lifecycle DISPOSITIONS that, by the U3 atomic-seat discipline (a work_record is PUBLISHED only AFTER a successful
  #   enqueue, and recovery_work_seq is never advanced on a rejected/deferred seat), are RETURNED (recovery_work_not_seated /
  #   recovery_work_horizon_deferred) but NEVER persisted onto a live work_record — so no orphaned CREATED/SCHEDULE_FAILED/
  #   HORIZON_DEFERRED record can ever exist. The enum names the complete disposition vocabulary; the six above are the
  #   persisted subset.
  # RecoveryWorkID = (RecoveryEpisodeID, recovery_work_seq)   # U1: the versioned recovery-work identity
  # --- U4 continuation-due status (the branch-C continuation due fact is EXPLICITLY consumed) ---
  # CONTINUATION_DUE_STATUS in { NOT_DUE, DUE, CONSUMED, SUPERSEDED, CANCELLED }   # U4
  #   The branch-C continuation record (recovery_decisions[decision_id]) and every recovery-work record carry a
  #   continuation_due_status / due_status. RecoveryAssignmentContinuationDueEvent (and RecoveryWorkDueEvent) set it to
  #   DUE; the post-epilogue hook ATOMICALLY consumes it (CONSUMED on apply/re-arm, SUPERSEDED on a stale-noop,
  #   CANCELLED on terminal closure) BEFORE returning. ProcessEventTime's final assertion checks the EXPLICIT status,
  #   never a timestamp field that merely equals t. (decision_record gains a `continuation_due_status` field.)
  # --- U2 explicit scheduling-source context threaded through every post-epilogue wake path ---
  # SchedulingSourceContext in { ORDINARY_DISPATCH(dispatch_envelope), POST_EPILOGUE(PostEpilogueSchedulingContext) }
  #   ReserveActivate / RangeReassign / RangeAssign / StartWake / CommitRecoveryAssignmentPlan take an explicit
  #   scheduling_context of this type; a POST_EPILOGUE caller threads its PostEpilogueSchedulingContext all the way to
  #   ScheduleEvent, which enforces target_event_time > source_event_time (a zero-latency wake targets
  #   next_representable_simulation_time(source_event_time); a positive-latency wake targets source_event_time +
  #   latency). No procedure creates a pctx and then schedules using only the old ordinary dispatch envelope.
  # --- U5 named recovery-assignment plan record (replaces the opaque INSTALL/UNDO macros) ---
  # recovery_assignment_plan = { RecoveryInstallID, source_assignment_versions, accepted_unsearched_suffixes,
  #   selected_reserve_miners, new_pending_assignment_specs (stable creation order), rollback_metadata }. Each spec
  #   (W5) carries { kind, MinerID, range, origin, source_assignment, reassignment_reason }. Produced compute-only by
  #   PrepareRecoveryAssignmentPlan (verifies I1/I3/I10/I18b BEFORE any mutation); applied by CommitRecoveryAssignmentPlan
  #   via the plan-bound constructors ReserveActivateFromPlan / RangeReassignFromPlan / RangeAssignFromPlan (W5), each of
  #   which performs the spec's SINGLE implied wake and returns the ACTUAL WakeEventRef (W4: no separate wake loop);
  #   reverted by RollbackRecoveryAssignmentPlan.
  # Q7 recovery-timing CONFIG constants (declared, deterministic):
  #   recovery_deadline_window            : config; > 0. The delay from SECURITY_RECOVERY entry to the deadline event.
  #   configured_recovery_completion_delay: config; > 0 (or the next-representable simulation instant). The
  #                                         DETERMINISTIC delay from a recovery decision's event_time to its
  #                                         RecoveryCompletionDueEvent target_time (replaces the undefined `t_next`).
  residency_ledger            : the SOLE owner of every per-miner state-residency duration t_<state>,
                                 including t_ACTIVE_HASHING = t_hash (H7). Only ApplyMinerStateTransition
                                 opens/closes residency intervals; no other procedure increments a t_<state>.
                                 # K3/L5 CROSS-ROUND CONTINUITY: an OPEN residency interval is never reset by a
                                 # round boundary without a boundary operation. The SINGLE idempotent owner
                                 # SettleResidencyBoundary (§1a/L5/M4) closes and reopens the SAME state at
                                 # the identical boundary_time (old-round energy attributed; NO transition
                                 # energy), so a state that continues across the boundary is counted exactly once
                                 # (I19 amended). It is idempotent via boundary_id — a repeat is a no-op. The
                                 # former FinalizeRoundResidency / BeginRoundResidency are withdrawn (L5).
  # --- event-loop bookkeeping (PER-RUN: initialised once at run start, PRESERVED across rounds; I-04) ---
  # These are keyed by event_time / TransitionEventID (both embed the monotonic run-level seq/event_time),
  # so they MUST persist across round boundaries; a per-round reset would un-finalise past timestamps or
  # drop replay-suppression state. RoundInitialise initialises them ONLY at run start and preserves them after.
  # Q4/J1/R5/U7 COHERENCE: security_census_dirty and latest_security_census are written by EXACTLY ONE procedure,
  #   CommitSecurityCensus (§0.8a), with SEVEN named sources (census_source, R5/U7): MINER_STATE_TRANSITION
  #   (ApplyMinerStateTransition), APPLICABILITY_ENTRY (CaptureSecurityCensusOnApplicabilityEntry, K7),
  #   RECOVERY_DEADLINE (CaptureSecurityCensusOnRecoveryDeadline via RecoveryDeadlineEvent, §9a),
  #   RECOVERY_COMPLETION_DUE (CaptureSecurityCensusOnRecoveryDeadline via RecoveryCompletionDueEvent, §10a),
  #   RECOVERY_CONTINUATION_DUE (CaptureSecurityCensusOnRecoveryDeadline via RecoveryAssignmentContinuationDueEvent,
  #   §10a, U7 — DISTINCT from the completion-due source so "continuation is due" is not conflated with "completion is
  #   due"), RECOVERY_WORK_DUE (CaptureSecurityCensusOnRecoveryDeadline via RecoveryWorkDueEvent, §9c, U1 — the
  #   recovery-WORK checkpoint), and POST_RECOVERY_APPLICATION (FinalizePostRecoveryApplicationState, §10a). It writes the two maps TOGETHER
  #   atomically. INVARIANT (J1): security_census_dirty[t] = true  =>  latest_security_census[t] exists — STRUCTURAL,
  #   since the two writes are the atomic body of the sole writer. The earlier "two writers"/"third writer" framing
  #   is superseded by "one writer, FIVE sources"; NO producer (ApplyMinerStateTransition or any capture procedure)
  #   is a direct writer of the two maps — each COMPUTES a census and CALLS CommitSecurityCensus (R5). The
  #   census-write ordinal is the per-run security_census_write_seq_by_event_time, owned solely by that writer (R5).
  security_census_dirty       : map event_time -> boolean. Set true ONLY by CommitSecurityCensus (Q4/J1), and
                                 ONLY together with latest_security_census[event_time]. S5: Cleared ONLY by
                                 SettleSecurityCensusDirty, called by FinalizeEventTimeSecurityCensus
                                 (settlement_kind = PRIMARY_EPILOGUE) and FinalizePostRecoveryApplicationState
                                 (settlement_kind = POST_RECOVERY_APPLICATION) — no procedure clears the flag directly.
  latest_security_census      : map event_time -> census_record. OVERWRITTEN by CommitSecurityCensus on every
                                 census-changing / applicability-entry / recovery-deadline boundary at that event_time
                                 with the NEWEST census AND its FULL PROVENANCE (J8): census_record = (RoundID_at_census,
                                 TemplateID_at_census, state_version_at_census, census_source, census_seq, H_active,
                                 H_honest, H_adversarial, q_adv). The epilogue decides from THIS value after quiescence
                                 and passes the STORED provenance to SecurityFloorEvaluate (never the current epoch).
  applied_transition_registry : set of TransitionEventIDs that were SUCCESSFULLY APPLIED (K5, formerly
                                 transition_event_registry). A TransitionEventID enters ONLY inside
                                 ApplyMinerStateTransition's atomic apply; a suppressed replay or a rejected
                                 (stale/illegal/malformed) event is NEVER here. Replay suppression checks THIS set.
  transition_rejection_log    : K5 — log of rejected transitions (stale_source / illegal_or_malformed) with the
                                 rejection reason; SEPARATE from applied_transition_registry (rejections are never
                                 registered as applied).
  current_delta_cycle         : the delta_cycle of the event currently being dispatched at this event_time (H2);
                                 a field of EventQueueContext (§0.7e/K8).
  finalised_event_times       : set of event_times whose ProcessEventTime epilogue has run (I-02); no ordinary
                                 event may be scheduled into a finalised event_time. A field of EventQueueContext (K8).
  event_creation_seq          : J4 — the ONE per-RUN monotonic event-creation counter, a field of the
                                 EventQueueContext (§0.7e/K8) owned SOLELY by ScheduleEvent; assigned atomically to
                                 each scheduled event AFTER deterministic stable ordering. It is the `event_seq` in
                                 every event envelope (§0.2) and every TransitionEventID (J3). Initialised once at
                                 run start and preserved across rounds (I-04); there is NO ambient undeclared seq.
  rebased_boundaries          : L5/M4 — per-RUN set of boundary_ids already settled by SettleResidencyBoundary
                                 (§1a). boundary_id = (prior_RoundID, new_RoundID) for a cross-round rebase or
                                 (RunID, RUN_END) for the single run-end settle (N1). IDEMPOTENCE key: a boundary
                                 in this set is a no-op on repeat, so a replayed/retried RoundInitialise or
                                 FinalizeSimulationRun never double-closes or double-attributes an interval (I19).
                                 Initialised empty once at run start and preserved across rounds (I-04).
  run_finalised               : N1 — per-RUN boolean, false until FinalizeSimulationRun (§20a) runs at the horizon
                                 T; it guards the SINGLE run-end finalisation so a re-dispatch is a no-op.
                                 Initialised false once at run start and preserved across rounds (I-04). RunID is the
                                 fixed per-run identifier used in the (RunID, RUN_END) boundary_id.

STRUCTURE Assignment (immutable version object)   # F7: renewal makes a NEW version; never mutate in place
  AssignmentID                : identity of THIS version (immutable once created)
  assignment_version          : monotonic version number within the lineage
  lineage_id                  : stable id shared by all versions of one assignment lineage
  MinerID, range = [range_start, range_end], RoundID, TemplateID
  status                      : one of {PENDING, CURRENT, PAUSED, SUPERSEDED, CLOSED}.
                                # J7 CANONICAL TERMINAL STATUS: SUPERSEDED is used ONLY for atomic same-range
                                # renewal (a new CURRENT version is published on the SAME lineage in the same
                                # step, I18b). CLOSED is the terminal status for EVERY end-of-life that is NOT a
                                # renewal: revocation, adversarial withdrawal, abandonment, wake failure,
                                # assignment cancellation, round closure, template closure. There is no
                                # ambiguous "CLOSE/SUPERSEDE" operation; a version is either renewed (SUPERSEDED
                                # + new CURRENT) or terminated (CLOSED). A CLOSED lineage has ZERO live heads (I18b).
  previous_assignment_reference : prior version's AssignmentID (null for an ORIGINAL first version)
  assignment_origin           : one of {ORIGINAL, RENEWED, REASSIGNED}
  custody_status              : one of the CANONICAL enum ONLY (I-07): {original, renewed, reassigned,
                                revoked, expired, abandoned, completed, superseded_by_template_refresh}
  revocation_reason           : set ONLY when custody_status = revoked (else null); one of
                                {adversarial_withdrawal, assignment_revoked, lease_conflict, departure} (I-07).
                                A revocation NEVER invents a new custody_status value; the cause lives HERE.
  termination_reason          : K6 — set ONLY when status = CLOSED (else null); the cause of closure, one of
                                {lease_expiry, adversarial_withdrawal, assignment_revoked, abandonment,
                                wake_failure, cancellation, round_closure, template_closure, range_exhausted}.
                                It is the declared reason a version reached CLOSED; there is NO undefined
                                "INVALID" assignment state (K6). For lease expiry: status = CLOSED,
                                custody_status = expired, termination_reason = lease_expiry.
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

### 0.8a Central security-census writer (Q4)

**(0.8a) One canonical atomic writer of the event-time security census (Q4; seven sources + explicit write ordinal R5/U1/U7).**
The two maps `latest_security_census[event_time]` and `security_census_dirty[event_time]` are written by EXACTLY
ONE procedure, `CommitSecurityCensus`. The earlier "exactly two writers" / "third writer" / "sole writer" framings
are SUPERSEDED: there is ONE writer with **SEVEN** named `census_source` values (R5/U7/U1) — MINER_STATE_TRANSITION,
APPLICABILITY_ENTRY, RECOVERY_DEADLINE, RECOVERY_COMPLETION_DUE, RECOVERY_CONTINUATION_DUE (U7),
RECOVERY_WORK_DUE (U1), POST_RECOVERY_APPLICATION. Every census producer computes its census and CALLS
`CommitSecurityCensus`; none writes the maps directly. The census-write ORDER is the explicit per-run
`security_census_write_seq_by_event_time` ordinal, owned SOLELY by this writer (R5).

```
PROCEDURE CommitSecurityCensus                                   # Q4: the SOLE atomic writer of the two census maps
  INPUTS: RoundContext, event_time,
          census_provenance,        # (RoundID_at_census, TemplateID_at_census, state_version_at_census) — J8
          H_active, H_honest, H_adversarial, q_adv,
          census_source             # R5/U7/U1: one of CENSUS_SOURCE = {MINER_STATE_TRANSITION, APPLICABILITY_ENTRY,
                                    #     RECOVERY_DEADLINE, RECOVERY_COMPLETION_DUE, RECOVERY_CONTINUATION_DUE (U7),
                                    #     RECOVERY_WORK_DUE (U1), POST_RECOVERY_APPLICATION}
  PRECONDITIONS: the caller has ALREADY computed a coherent census (H_active = H_honest + H_adversarial, I17);
                 called ONLY by the census sources below — nothing writes the two maps directly (R5: producers
                 CALL this writer; NO producer is itself a direct writer of security_census_dirty/latest_security_census)
  EFFECTS:
    # Q4: write BOTH maps TOGETHER, atomically. Because this is the ONLY writer, the J1 coherence invariant
    #     (dirty[t] = true => latest[t] exists) is STRUCTURAL, not a per-caller discipline. Newest write wins.
    ATOMICALLY:
      # R5: advance the EXPLICIT per-event_time census-write ordinal, owned SOLELY by CommitSecurityCensus and
      #     held in the per-run RunContext.security_census_write_seq_by_event_time (initialised by RunInitialise,
      #     §1.0, and PRESERVED across rounds). This REPLACES the implicit "next per-event_time census-write
      #     ordinal": the write order is now a declared deterministic increment with a named owner.
      SET RunContext.security_census_write_seq_by_event_time[event_time] <-
            (RunContext.security_census_write_seq_by_event_time[event_time] OR 0) + 1
      SET latest_security_census[event_time] <- census_record(
            RoundID_at_census       = census_provenance.RoundID_at_census,
            TemplateID_at_census    = census_provenance.TemplateID_at_census,
            state_version_at_census = census_provenance.state_version_at_census,
            census_source           = census_source,                 # Q4: which source produced this census
            census_seq              = RunContext.security_census_write_seq_by_event_time[event_time],   # R5: explicit deterministic ordinal
            H_active = H_active, H_honest = H_honest, H_adversarial = H_adversarial, q_adv = q_adv)   # J8 provenance
      SET security_census_dirty[event_time] <- true
  RETURNS: security_census_committed(event_time, census_source)
  INVARIANT (J1): after EVERY call, security_census_dirty[event_time] = true AND latest_security_census[event_time]
        EXISTS — guaranteed structurally because the two writes are the atomic body of the SOLE writer.
  NOTE: Q4/R5/U7/U1: the SINGLE canonical atomic writer, and the SOLE owner of the census-write ordinal
        (security_census_write_seq_by_event_time). Its SEVEN sources (CENSUS_SOURCE) — ApplyMinerStateTransition
        (MINER_STATE_TRANSITION, §0.9), CaptureSecurityCensusOnApplicabilityEntry (APPLICABILITY_ENTRY, §9),
        CaptureSecurityCensusOnRecoveryDeadline (RECOVERY_DEADLINE from RecoveryDeadlineEvent §9a;
        RECOVERY_COMPLETION_DUE from RecoveryCompletionDueEvent §10a; RECOVERY_CONTINUATION_DUE from
        RecoveryAssignmentContinuationDueEvent §10a, U7; RECOVERY_WORK_DUE from RecoveryWorkDueEvent §9c, U1), and
        FinalizePostRecoveryApplicationState (POST_RECOVERY_APPLICATION, §10a, R2/R5) — CALL this rather than writing
        the maps directly. S5: the dirty flag is CLEARED only by SettleSecurityCensusDirty (below), never directly.

PROCEDURE SettleSecurityCensusDirty                             # S5: the SOLE clearer of security_census_dirty[event_time]
  INPUTS: RoundContext, event_time, settlement_kind   # settlement_kind in {PRIMARY_EPILOGUE, POST_RECOVERY_APPLICATION}
  PRECONDITIONS: called ONLY by FinalizeEventTimeSecurityCensus (settlement_kind = PRIMARY_EPILOGUE, the one
                 security-floor decision) or FinalizePostRecoveryApplicationState (settlement_kind =
                 POST_RECOVERY_APPLICATION, the post-application settlement, R2). NO other procedure clears the flag.
  EFFECTS:
    # S5: CLEAR the dirty flag and RECORD which settlement cleared it. CommitSecurityCensus remains the SOLE setter
    #     of dirty = true and the sole writer of latest_security_census; this procedure is the SOLE clearer.
    CLEAR security_census_dirty[event_time]
    RECORD security_census_dirty_settled(event_time, settlement_kind)
  RETURNS: security_census_dirty_settled(event_time, settlement_kind)
  NOTE: S5: the ONE canonical dirty-flag clearer, with two declared settlement_kinds. This removes the earlier
        contradiction in which FinalizeEventTimeSecurityCensus was called the SOLE clearer while
        FinalizePostRecoveryApplicationState (R2) also cleared the flag: BOTH now clear ONLY through this procedure.
        CommitSecurityCensus (§0.8a) remains the sole setter/writer of dirty = true and the latest census record.
```

### 0.9 Central miner-state transition hook (F6)

```
PROCEDURE ApplyMinerStateTransition
  INPUTS: MinerID, old_state, new_state,
          transition_envelope,        # S1: ONE explicit transition-envelope object (supersedes R3's decomposed inputs)
          reason,
          assignment_ref, candidate_id, propagation_id    # J3: explicit ids; J4: event_seq owned by ScheduleEvent
          # S1 ONE EXPLICIT TRANSITION-ENVELOPE OBJECT. This hook receives ONE object, `transition_envelope`,
          # carrying the COMPLETE dispatch identity (§0.2):
          #     transition_envelope = { envelope_namespace, event_time, delta_cycle, event_seq, hook_id }
          # It builds TransitionEventID EXCLUSIVELY from that object plus the transition-specific fields (MinerID,
          # old_state, new_state, reason, assignment_ref, candidate_id, propagation_id). NO identity field is passed
          # decomposed and NONE is omitted. The R3 clause that omitted namespace fields "travel implicitly" with a
          # numeric-only call site is WITHDRAWN (S1): there is no implicit propagation.
          # EVERY call site passes EXACTLY `transition_envelope = dispatch_envelope` — an ordinary/driver dispatch
          # envelope (envelope_namespace = ORDINARY_EVENT, hook_id = null, materialised by ProcessEventTime, §0.7d)
          # or the RUN_HOOK horizon envelope (envelope_namespace = RUN_HOOK, hook_id = HorizonHookID, §20b). There
          # is NO positional shorthand: a call of the form `ApplyMinerStateTransition(..., now, reason=...)` is NOT
          # permitted, and NO call reads EQ.current_event_time/current_delta_cycle/current_event_seq implicitly.
          # Every procedure that directly OR indirectly calls this hook carries an explicit `dispatch_envelope`
          # parameter and passes it UNCHANGED as `transition_envelope`: a QUEUED handler (WakeCompleteEvent,
          # HashWorkEvent, CertificateArrival, BlockAcceptancePoint, ResumeFromPause) obtains its envelope from its
          # OWN dispatched event (materialised by ProcessEventTime); a SIM-DRIVER entry point (MinerRegister,
          # PrepareParticipantsForNewRound, ReserveActivate, LeaseExpiry, AdversarialParticipationChangeEvent,
          # AcceptanceBatchFinalize, FullRangeExhaustNoSolution) is itself dispatched and receives the same; and a
          # SYNCHRONOUS nested procedure (StartWake, EnterLowPowerListen, ExhaustionAdjudicate, CloseRoundAssignments,
          # CloseTemplateAssignments, ScheduleSolutionPropagation, EarlyStopVerify, CompleteAssignmentPhase,
          # HandlePropagationFailure, ValidBlockAccept, RoundAbort, RangeAssign, RangeReassign, TemplateRefresh)
          # receives the SAME envelope as an explicit input from its caller and passes it as `transition_envelope`.
          # The seq is owned solely by ScheduleEvent (J4); NO procedure stamps `next EQ.event_creation_seq`. NO
          # transition depends on an ambient/undeclared event_seq.
          # candidate_id and propagation_id are BOTH passed by every candidate-triggered
          # caller (J3; null otherwise). assignment_ref resolves AssignmentID/assignment_version.
  PRECONDITIONS: (old_state -> new_state) is a legal miner transition (STAGE_01_MINER_STATE_MACHINE.md §3).
                 # J2/K5: the old-state precondition `old_state = miner_state(MinerID)` is checked in step
                 #     (3), AFTER the replay guard; and the TransitionEventID is added to the APPLIED registry
                 #     ONLY inside the atomic apply (step 5) — never for a suppressed replay or a rejection.
  EFFECTS:
    # F6: the SOLE owner of every miner-state change, and (Q4/R5) a PRODUCER of the security census — it
    #     COMPUTES the post-transition census and CALLS the sole writer CommitSecurityCensus (§0.8a) with
    #     census_source = MINER_STATE_TRANSITION. It is NOT itself a direct writer of security_census_dirty /
    #     latest_security_census (R5: only CommitSecurityCensus writes the two maps); the earlier "a writer …
    #     the other writer is CaptureSecurityCensusOnApplicabilityEntry" framing is withdrawn.
    # (0) S1 DESTRUCTURE the ONE transition_envelope object into its identity fields; the TransitionEventID (step 1)
    #     and the malformed-envelope guard (step 4) are built EXCLUSIVELY from these — there is no other identity source.
    SET envelope_namespace <- transition_envelope.envelope_namespace
    SET event_time         <- transition_envelope.event_time
    SET delta_cycle        <- transition_envelope.delta_cycle
    SET event_seq          <- transition_envelope.event_seq
    SET hook_id            <- transition_envelope.hook_id
    # (1) J2/J3/K5/R3 EVENT-IDENTITY. Build the immutable TransitionEventID from the FULL envelope —
    #     envelope_namespace + hook_id (R3) THEN delta_cycle, event_seq, BOTH candidate ids — so (a) the SAME edge
    #     for the SAME miner at the SAME event_time in DIFFERENT delta-cycles are DISTINCT ids and BOTH apply, (b)
    #     two propagation attempts of ONE CandidateID (different PropagationID) are DISTINCT ids, and (c) a RUN_HOOK
    #     transition and an ORDINARY_EVENT transition with IDENTICAL numeric (event_time, delta_cycle, event_seq)
    #     are DISTINCT ids because their envelope_namespace (and hook_id) differ (R3 acceptance requirement).
    SET TransitionEventID <- (envelope_namespace, hook_id, event_time, delta_cycle, event_seq,
                              MinerID, old_state, new_state, reason,
                              AssignmentID(assignment_ref), assignment_version(assignment_ref),
                              candidate_id, propagation_id)                       # R3: namespace + hook_id in the id (immutable, J3)
    # (2) K5 REPLAY GUARD — check the APPLIED registry. Suppress ONLY an exact-same-id replay of an
    #     ALREADY-APPLIED transition; do NOT read old_state and do NOT charge energy.
    IF TransitionEventID in applied_transition_registry:
      RETURN duplicate_suppressed(TransitionEventID)        # W6: exact replay of an applied transition; no state check, no charge
    # (3) K5 VALIDATE OLD-STATE (non-replay). A stale source is REJECTED and recorded in the REJECTION log,
    #     NOT the applied registry.
    IF old_state != NONE AND old_state != miner_state(MinerID):
      RECORD transition_rejection_log(TransitionEventID, reason_rejected = stale_source,
                                      observed_state = miner_state(MinerID))   # K5: NOT applied
      RETURN illegal_stale_source(TransitionEventID)   # W6
    # (4) K5 VALIDATE LEGALITY + ENVELOPE. An illegal edge or a malformed envelope is REJECTED, logged, and
    #     NOT applied.
    IF (old_state -> new_state) is NOT a legal miner transition
       OR envelope is incomplete (missing envelope_namespace/event_time/delta_cycle/event_seq)   # K4/R3
       OR (envelope_namespace = RUN_HOOK AND hook_id = null)                     # R3: a RUN_HOOK envelope MUST carry its hook_id
       OR (candidate-triggered AND (candidate_id = null OR propagation_id = null)):   # J3
      RECORD transition_rejection_log(TransitionEventID, reason_rejected = illegal_or_malformed)
      RETURN illegal_transition(TransitionEventID)   # W6
    # (5) K5 ATOMIC APPLY. Register-then-apply in ONE atomic step; the id enters the APPLIED registry ONLY here.
    ATOMICALLY:
      ADD TransitionEventID to applied_transition_registry             # K5: only APPLIED transitions are registered
      # (5a) residency boundary: close OLD interval, open NEW (I5/I6/I19/K3 continuity at round boundaries).
      IF old_state != NONE: CLOSE residency(MinerID, old_state) at event_time   # accrues P_old * (event_time - last_boundary)
      OPEN  residency(MinerID, new_state) at event_time
      # (5b) one-shot boundary energy (E_transition/E_coordination per edge). I6; never folded into P*t.
      RECORD E_transition/E_coordination for (old_state -> new_state)
      # (5c) assignment status update where the edge specifies one (J7 terminal status).
      IF edge specifies an assignment status change: UPDATE status(assignment_ref) accordingly
      # (5d) set the new miner_state.
      SET miner_state(MinerID) <- new_state
      # (5e) recompute the census DETERMINISTICALLY from the post-transition ACTIVE_HASHING set (I17).
      SET H_honest(event_time)      <- SUM over honest miners in ACTIVE_HASHING of modeled hash rate
      SET H_adversarial(event_time) <- SUM over adversarial miners in ACTIVE_HASHING of modeled hash rate
      SET H_active(event_time)      <- H_honest(event_time) + H_adversarial(event_time)   # I17 EXACT
      IF H_active(event_time) = 0: SET q_adv(event_time) <- NA           # I17: undefined at zero
      ELSE:                        SET q_adv(event_time) <- H_adversarial(event_time) / H_active(event_time)
      RECORD transition_audit(TransitionEventID, MinerID, old_state, new_state, event_time,
                              delta_cycle, event_seq, reason, assignment_ref, candidate_id, propagation_id)
      RECORD intermediate_census_for_audit(event_time, delta_cycle, (H_active, H_honest, H_adversarial, q_adv))
      # (5f) Q4/J1/J8: publish the census through the SOLE writer CommitSecurityCensus (source MINER_STATE_TRANSITION);
      #      it writes dirty + latest together atomically — never one without the other.
      IF this transition changed the ACTIVE_HASHING census:
        CALL CommitSecurityCensus(RoundContext, event_time,
              census_provenance = (RoundID_current, TemplateID_committed, state_version_current),
              H_active(event_time), H_honest(event_time), H_adversarial(event_time), q_adv(event_time),
              census_source = MINER_STATE_TRANSITION)                   # Q4: sole atomic writer (J8 provenance; newest wins)
    # (6) W6 EXPLICIT SUCCESS DISPOSITION. The atomic apply completed; return the declared applied result carrying the
    #     TransitionEventID. This is the ONLY path that returns transition_applied — every caller that inspects the
    #     result (e.g. StartWake) matches EXACTLY these four declared names, never an undeclared `transition_record`.
    RETURN transition_applied(TransitionEventID)
  RETURNS: transition_applied(TransitionEventID) | duplicate_suppressed(TransitionEventID) |
           illegal_stale_source(TransitionEventID) | illegal_transition(TransitionEventID)   # W6: one explicit result union
  NOTE: W6: ApplyMinerStateTransition returns EXACTLY ONE of four declared results, each carrying the TransitionEventID:
        transition_applied (the atomic step-5 apply succeeded), duplicate_suppressed (an exact replay of an
        already-applied id, step 2), illegal_stale_source (old_state != miner_state, step 3), illegal_transition (an
        illegal edge or a malformed envelope, step 4). The earlier `transition_record` return name is WITHDRAWN. StartWake
        (and any other inspecting caller) branches on `transition_applied` versus the three non-applied results; a
        for-effect caller may ignore the value, but no caller may test a name outside this union.
  NOTE: K5: the TransitionEventID enters applied_transition_registry ONLY inside the atomic apply (step 5),
        so a suppressed replay or a rejected (stale/illegal/malformed) event is NEVER in the applied
        registry — rejections go to transition_rejection_log. J2: replay suppression precedes the old-state
        check. Q4/J1: dirty+latest are written together by the SOLE writer CommitSecurityCensus (§0.8a), which
        this hook calls with census_source = MINER_STATE_TRANSITION.
  NOTE: R3: the TransitionEventID includes envelope_namespace and hook_id, so a RUN_HOOK transition (the horizon
        close, §20b — namespace RUN_HOOK, hook_id HorizonHookID) and an ORDINARY_EVENT transition with the SAME
        numeric (event_time, delta_cycle, event_seq) are DISTINCT ids and BOTH the replay guard and the applied
        registry treat them as different transitions. The five identity fields are threaded from ONE dispatch
        envelope (never decomposed to only the numeric three); a RUN_HOOK envelope missing its hook_id is rejected.
  NOTE: This is the ONLY writer of miner_state (0.3) and the SOLE owner of state-residency time
        t_<state> incl t_ACTIVE_HASHING = t_hash (H7). It recomputes H_active/H_honest/H_adversarial and
        re-checks I17 at EVERY ACTIVE_HASHING boundary; it never SAMPLES a hash rate.
```

### 0.10 Event-scheduled wake (F5)

```
PROCEDURE StartWake                                             # V3/V9: a TRANSACTION with explicit structured outputs
  INPUTS: RoundContext, MinerID, target_assignment, from_state,
          scheduling_context   # V2: SchedulingSourceContext in {ORDINARY_DISPATCH(dispatch_envelope), POST_EPILOGUE(pctx)} — EXPLICIT
  PRECONDITIONS: from_state = miner_state(MinerID) in {REGISTERED, RESERVE, EXHAUSTED_PENDING, LOW_POWER_LISTEN};
                 target_assignment is a bound PENDING (or PAUSED-resumed) assignment for MinerID.
                 # V2: EVERY caller passes scheduling_context EXPLICITLY — ORDINARY_DISPATCH(dispatch_envelope) for a
                 #     dispatched handler, POST_EPILOGUE(pctx) for a post-epilogue install. There is NO bare-envelope
                 #     alias / implicit conversion (the Stage-1U "a bare dispatch_envelope is read as ORDINARY_DISPATCH"
                 #     prose is WITHDRAWN). L1: the underlying dispatch_envelope (for the WAKING transition) is
                 #     scheduling_context's envelope — ORDINARY_DISPATCH(e) -> e; POST_EPILOGUE(pctx) -> pctx.source_envelope.
  EFFECTS:
    SET dispatch_envelope <- (scheduling_context is ORDINARY_DISPATCH(e) ? e : scheduling_context.pctx.source_envelope)   # V2/L1
    # F5: NON-BLOCKING. Begin the wake and RETURN to the event loop immediately; do NOT run the wake latency here.
    # V3 CANONICAL ORDER: (1) sample latency; (2) compute target via SchedulingSourceContext; (3) validate + ScheduleEvent;
    #   (4) ONLY after a successful seat, apply the WAKING transition; (5) if the transition fails after the seat, CANCEL
    #   the seated WakeCompleteEvent; (6) publish the WakeEventRef; (7) return the structured wake_seated result — so NO
    #   failure leaves miner_state = WAKING with no live WakeCompleteEvent (gate 4).
    # (1) ---- [SIMULATION SAMPLING] ----
    wake_latency <- [SIMULATION SAMPLING] wake_latency_model(MinerID)    # the ONLY wake draw (sampling summary item 3)
    # (2) compute target_event_time from the scheduling_context (L6: ScheduleEvent alone derives delta_cycle).
    IF scheduling_context is POST_EPILOGUE(pctx):
      SET src <- pctx.source_event_time
      SET target_time <- (wake_latency > 0 ? src + wake_latency : next_representable_simulation_time(src))   # V3/gate 4: STRICTLY LATER than src
      SET post_ctx <- pctx
    ELSE:  # ORDINARY_DISPATCH(e)
      SET target_time <- now + wake_latency                             # future (ScheduleEvent derives dc = 0) or same-time (forward dc, H5)
      SET post_ctx <- null
    # (3) validate + ScheduleEvent. V9: inspect the scheduler disposition EXPLICITLY (no boolean AND).
    SET seat <- CALL ScheduleEvent(EQ, RoundContext, WakeCompleteEvent,
                     target_event_time = target_time, target_microphase = WAKE_COMPLETE,
                     {MinerID, AssignmentID(target_assignment)},
                     post_epilogue_context = post_ctx)                   # V2/S7: post_ctx present ONLY for POST_EPILOGUE
    IF seat != scheduled(...):
      # V3: the schedule failed BEFORE any transition. The miner is UNCHANGED (still from_state); nothing to cancel.
      RECORD wake_schedule_rejected(MinerID, AssignmentID(target_assignment), seat)
      RETURN wake_schedule_failed_before_transition(reason = seat)
    SET wake_event_ref <- seat.event_ref
    # (4) ONLY AFTER a successful seat: apply the legal WAKING transition (accrues wake residency via F6).
    SET tr <- CALL ApplyMinerStateTransition(MinerID, from_state, WAKING,
                     transition_envelope = dispatch_envelope,           # S1: ONE explicit transition-envelope object
                     reason = wake_start, assignment_ref = target_assignment,
                     candidate_id = null, propagation_id = null)         # F6
    IF tr is NOT transition_applied(teid):
      # (5) V3/W6: the transition did NOT apply (duplicate_suppressed / illegal_stale_source / illegal_transition) AFTER
      #     the seat -> CANCEL the seated WakeCompleteEvent so no orphan wake survives; leave the miner in from_state
      #     (NOT WAKING). W6: `tr` is one of the four declared ApplyMinerStateTransition results; only transition_applied
      #     retains the wake.
      IF wake_event_ref is still pending on EQ: CANCEL wake_event_ref on EQ
      RECORD wake_transition_failed(MinerID, wake_event_ref, tr)
      RETURN wake_transition_failed_after_seat(reason = tr, WakeEventRef = wake_event_ref)
    # (6) PUBLISH the WakeEventRef on the assignment's wake registry, so a later rollback/cancel (V4/V8) can find it.
    SET wake_event_ref_of(target_assignment) <- wake_event_ref
    # (7) return the structured transaction result.
    RETURN wake_seated(AssignmentID = AssignmentID(target_assignment), WakeEventRef = wake_event_ref,
                       wake_target_time = target_time, resulting_state = WAKING)
  RETURNS: wake_seated(AssignmentID, WakeEventRef, wake_target_time, resulting_state = WAKING) |
           wake_schedule_failed_before_transition(reason) | wake_transition_failed_after_seat(reason, WakeEventRef)
  NOTE: V3/V9: StartWake is a TRANSACTION. It seats the WakeCompleteEvent FIRST (inspecting the scheduler disposition
        EXPLICITLY, never a boolean AND — V9), THEN applies the WAKING transition; a transition failure after the seat
        CANCELS the seated event, so no failure leaves miner_state = WAKING without a live WakeCompleteEvent (gate 4).
        V2: the scheduling_context is EXPLICIT at every call site — ORDINARY_DISPATCH(dispatch_envelope) or
        POST_EPILOGUE(pctx); a POST_EPILOGUE zero-latency wake targets next_representable_simulation_time(source), never
        the drained source time, and ScheduleEvent receives post_epilogue_context explicitly. L6/H5: ScheduleEvent alone
        derives delta_cycle. Every caller inspects the structured disposition (V3).

PROCEDURE WakeCompleteEvent
  INPUTS: RoundContext, MinerID, target_assignment, dispatch_envelope   # M1: this queued handler's own envelope
  PRECONDITIONS: this is the scheduled wake-completion event for MinerID;
                 # M1: dispatch_envelope = (event_time, delta_cycle, event_seq) of THIS dispatched
                 #     WakeCompleteEvent, materialised by ProcessEventTime; threaded into every hook call below.
  EFFECTS:
    # M3 STALE-TARGET GUARD (explicit; runs FIRST). A WakeCompleteEvent is NOT protected by the HashWorkEvent
    #    G9 guard -- it is a DISTINCT event that could otherwise activate a CLOSED/reassigned target. Reject
    #    any wake whose target is no longer a live head or whose round/template epoch moved on.
    IF status(target_assignment) NOT in {PENDING, PAUSED}
       OR RoundID(target_assignment) != RoundID_current OR TemplateID(target_assignment) != TemplateID_committed
       OR target_assignment is NOT the miner's bound live head (I18b):
      RETURN stale_wake_noop            # M3: cannot activate a CLOSED/superseded/stale target; miner unchanged
    # F5: runs at its OWN event timestamp (dispatch_envelope.event_time = the completion time), independently
    #     of any other miner's wake. Wake residency P_wake * wake_latency is accrued by ApplyMinerStateTransition
    #     when it closed the WAKING interval at this timestamp.
    ASSERT miner_state(MinerID) = WAKING                                 # non-stale target implies WAKING here
    IF wake_within_deadline(MinerID):                                    # completion timestamp <= wake_deadline
      # validate the bound PENDING (or resumed PAUSED) assignment before hashing.
      VALIDATE target_assignment against I1, current RoundID, committed TemplateID   # re-checks I1/I10/I3
      # WAKING -> ACTIVE_HASHING (T5); the edge activates PENDING -> CURRENT for a fresh assignment,
      # or restores a resumed PAUSED assignment to CURRENT from its retained actual_frontier (I18b: the
      # unique live head becomes CURRENT again).
      CALL ApplyMinerStateTransition(MinerID, WAKING, ACTIVE_HASHING,
                                     transition_envelope = dispatch_envelope, reason = ramp_complete,   # S1: ONE envelope object
                                     assignment_ref = target_assignment, candidate_id = null, propagation_id = null)   # F6 (M1)
      # G9: begin EVENT-SCHEDULED hashing (NOT a blocking loop); identical for a fresh or resumed range.
      RETURN CALL StartHashing(RoundContext, MinerID, target_assignment)
    ELSE:
      # G4: STATUS-AWARE wake failure. Move the miner OFFLINE via the hook, then branch on the target
      #     assignment's status; a PAUSED resume failure MUST NOT use the PENDING-only "whole range
      #     inactive" rule.
      RECORD wake_failure(MinerID, target_assignment, status = status(target_assignment))
      CALL ApplyMinerStateTransition(MinerID, WAKING, OFFLINE,
                                     transition_envelope = dispatch_envelope, reason = wake_deadline_expiry,   # S1: ONE envelope object
                                     assignment_ref = target_assignment, candidate_id = null, propagation_id = null)   # T12 (M1)
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
  NOTE: M3: WakeCompleteEvent BEGINS with an explicit stale-target guard (status in {PENDING, PAUSED},
        current round/template epoch, the miner's own live head); a wake for a CLOSED/superseded/reassigned
        target returns stale_wake_noop and CANNOT activate the miner. This guard is independent of the
        HashWorkEvent G9 guard, which does not protect WakeCompleteEvent. G4: the PENDING and PAUSED
        wake-failure paths differ -- a PAUSED resume failure preserves the three frontiers and reassigns ONLY
        the accepted unsearched suffix, never the whole range under the PENDING-only rule, and clears the
        candidate pause fields. G9: on success the miner begins event-scheduled hashing via StartHashing (no
        blocking loop). Concurrent wakes stay independent (F5). M1: every hook call threads dispatch_envelope.
```

### 0.11 Shared pending-assignment constructor (F4)

```
PROCEDURE CreatePendingAssignment
  INPUTS: RoundContext, MinerID, range, assignment_origin, source_assignment, reason
  PRECONDITIONS: assignment_origin in {ORIGINAL, REASSIGNED};        # G2: RENEWED removed from this constructor
                 range disjoint from all valid active assignments (I1);
                 custody_status(range) != completed AND coverage_state(range) != searched
  EFFECTS:
    # W7: EXPLICIT CONSTRUCTOR RESULT. This constructor either creates the PENDING head and returns
    #     assignment_created(assignment), or creates NOTHING and returns assignment_creation_failed(reason). The
    #     preconditions above are RE-CHECKED here as an executable guard (a concurrent same-time mutation may have
    #     invalidated them), and a violation is a DECLARED failure — never an uncaught assertion and never a partially
    #     built object. Every caller MUST branch on this result BEFORE reading AssignmentID, setting lease fields, or
    #     adding the object to any transaction record.
    IF range is NOT disjoint from all valid active assignments (I1)
       OR custody_status(range) = completed OR coverage_state(range) = searched
       OR (assignment_origin = REASSIGNED AND (source_assignment = null OR reason is NOT a permitted reassignment reason)):
      RETURN assignment_creation_failed(reason = overlap_or_custody_or_provenance_violation)   # W7: nothing created
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
    RETURN assignment_created(A)                                         # W7: the ONLY success disposition
  RETURNS: assignment_created(assignment) | assignment_creation_failed(reason)   # W7: one explicit constructor result
  NOTE: W7: the constructor returns EXACTLY assignment_created(assignment) (the head was built and ledgered) or
        assignment_creation_failed(reason) (the executable I1/custody/coverage/provenance guard rejected it and NOTHING
        was created). No caller may read AssignmentID, set lease fields, or add the object to a transaction record
        before branching on this result. The earlier bare `A` return is WITHDRAWN.
  NOTE: G2: only ORIGINAL (fresh never-assigned range) and REASSIGNED (accepted unsearched suffix,
        fresh lineage + full I9 provenance) are constructed here. Same-range RENEWAL is performed
        EXCLUSIVELY by RenewAssignment (F7), which creates the new CURRENT version on the SOURCE
        lineage; RENEWED is never a case here and can never create a fresh lineage.
```

---

## 1. Run and round initialisation

### 1.0 Run initialisation — explicit run-level ownership (Q5)

A run's per-run state lives in ONE explicit `RunContext`, created ONCE by `RunInitialise` at run start.
`RoundInitialise` receives it explicitly, initialises ONLY per-round registries, preserves/reuses the same
`RunContext` across rounds, and returns every per-round registry explicitly.

```
STRUCTURE RunContext (per-RUN; Q5 — the SOLE owner of run-level runtime state)
  RunID                       : the fixed per-run identifier (used in (RunID, RUN_END) and (RunID, T, HORIZON_CLOSE))
  EventQueueContext           : the sole dispatch/scheduling state (§0.7e/K8): event_queue, current_*, event_creation_seq,
                                finalised_event_times, run_horizon_T
  RunHookContext              : the run-hook envelope owner (§0.7e/P2): run_hook_seq, applied_run_hook_ids
  rebased_boundaries          : L5/M4 — set of boundary_ids already settled by SettleResidencyBoundary (§1a)
  run_finalised               : N1 — boolean; guards the single run-end finalisation (§20a)
  run_horizon_T               : O2 — the fixed simulation horizon T (mirrored in EventQueueContext for ScheduleEvent)
  # per-run security-census/registries (I-01/I-04; keyed by event_time / TransitionEventID, monotonic across rounds):
  security_census_dirty, latest_security_census, applied_transition_registry, transition_rejection_log
  security_census_write_seq_by_event_time   : R5 — map event_time -> monotonic census-write ordinal. The EXPLICIT
                                : deterministic write order for latest_security_census. Owned SOLELY by
                                : CommitSecurityCensus (§0.8a); initialised here and PRESERVED across rounds.
  applied_setup_retry_ids     : W8 — set of already-applied SetupRetryIDs (RoundID, setup_kind, generation), guarding
                                : idempotent replay of SetupRetryEvent (a re-dispatched retry runs the setup at most once).
  maximum_setup_retries       : W8 — config bound on setup_retry_generation per (RoundID, setup_kind); a rolled-back
                                : setup may seat at most this many bounded retries before the round ABORTS.

PROCEDURE RunInitialise                                         # Q5: creates ALL per-run fields ONCE at run start
  INPUTS: config (horizon T, ...)
  PRECONDITIONS: called EXACTLY ONCE per run, BEFORE the first RoundInitialise
  EFFECTS:
    SET RunID <- fresh per-run identifier
    INITIALISE EventQueueContext EQ WITH event_queue = empty, current_event_time = 0, current_delta_cycle = 0,
               current_microphase = 0, current_event_seq = 0, event_creation_seq = 0,
               finalised_event_times = empty set, run_horizon_T = config.horizon_T          # K8/O2 (sole dispatch state)
    INITIALISE RunHookContext WITH run_hook_seq = 0, applied_run_hook_ids = empty set        # P2 (run-hook envelope owner)
    INITIALISE rebased_boundaries          <- empty set     # L5
    INITIALISE run_finalised               <- false         # N1
    INITIALISE security_census_dirty       <- empty map     # I-01
    INITIALISE latest_security_census      <- empty map     # I-01
    INITIALISE security_census_write_seq_by_event_time <- empty map   # R5: explicit census-write ordinal (sole owner: CommitSecurityCensus)
    INITIALISE applied_transition_registry <- empty set     # I-03/K5
    INITIALISE transition_rejection_log    <- empty log     # K5
    INITIALISE applied_setup_retry_ids     <- empty set     # W8: idempotence registry for SetupRetryEvent
    SET        maximum_setup_retries       <- config.maximum_setup_retries   # W8: bounded retry budget per (RoundID, setup_kind)
  RETURNS: RunContext(RunID, EventQueueContext = EQ, RunHookContext, rebased_boundaries, run_finalised,
                      run_horizon_T = config.horizon_T, security_census_dirty, latest_security_census,
                      security_census_write_seq_by_event_time,   # R5
                      applied_transition_registry, transition_rejection_log,
                      applied_setup_retry_ids, maximum_setup_retries)   # W8
  NOTE: Q5: the ONE-TIME owner of every per-run field. RoundInitialise NEVER (re)creates these; it receives the
        RunContext, preserves it, and reuses it. RunEventLoopToHorizon obtains RunHookContext through
        RunContext.RunHookContext (never an implicitly created local object).
```

### 1.1 Round initialisation

```
PROCEDURE RoundInitialise
  INPUTS: config (difficulty D0, horizon T, nonce_domain, floor parameters), RunContext, prior_state
          # Q5: RunContext is supplied EXPLICITLY (created once by RunInitialise); RoundInitialise reuses it.
  PRECONDITIONS: no active round OR prior round dispositioned; RunContext already created by RunInitialise
  EFFECTS:
    SET RoundID <- fresh monotonic identifier
    SET difficulty D <- D0                          # fixed for the round (I12)
    SET nonce_domain <- config.nonce_domain
    INITIALISE assignment_ledger <- empty           # supports I8
    INITIALISE reassignment_log  <- empty           # supports I9
    INITIALISE energy_ledger     <- empty           # supports I5, I6, I7
    INITIALISE floor_state       <- config.floor parameters
    # I-04: PER-ROUND registries -- reset FRESH every round (G8). No field below is an implicit global.
    INITIALISE active_propagation_set    <- empty
    INITIALISE acceptance_batch_registry <- empty
    SET        candidate_discovery_seq   <- 0        # G7: deterministic CandidateID counter
    SET        block_accepted            <- false
    SET        state_version             <- 0        # G10: round-state epoch
    # --- per-round recovery registries (Q5: returned explicitly below) ---
    SET        recovery_episode_seq      <- 0        # O4: deterministic RecoveryEpisodeID counter
    SET        current_recovery_episode  <- null     # O4: no active recovery episode at round start
    INITIALISE recovery_deadline_reached   <- empty map   # P3: per-episode "deadline elapsed" FACT (no outcome)
    SET        recovery_census_seq       <- 0        # Q1: deterministic RecoveryCensusVersion counter
    INITIALISE latest_recovery_census      <- empty map   # Q1: per-episode versioned final recovery census
    SET        recovery_decision_seq     <- 0        # P5: deterministic RecoveryDecisionID counter
    INITIALISE recovery_decisions          <- empty map   # Q3: per-decision record {status, outcome, bound_census_version, ...}
    INITIALISE pending_recovery_decisions  <- empty map   # Q3: per-episode SET of applicable RecoveryDecisionIDs
    INITIALISE latest_recovery_decision    <- empty map   # P5: per-episode latest {decision_id, outcome, bound_census_version, status}
    INITIALISE recovery_outcome_finalised  <- empty map   # O4: per-episode "one outcome applied" key
    INITIALISE recovery_episode_disposition <- empty map  # S4/T4: per-episode TERMINAL_CANCELLED / RECOVERY_INSTALL_FAILED_ABORTED
    SET        recovery_install_in_progress <- false      # T3: no branch-C installation in progress at round start
    SET        recovery_install_seq        <- 0           # T3: deterministic RecoveryInstallID counter
    SET        active_recovery_install_decision <- null   # T3: no installation decision at round start
    SET        recovery_work_seq           <- 0           # U1/U3: deterministic RecoveryWorkID counter
    INITIALISE recovery_work               <- empty map   # U1: per-work-action record {action, status, due_status, ...}
    INITIALISE pending_recovery_work       <- empty map   # U1: per-episode AT-MOST-ONE in-flight RecoveryWorkID
    INITIALISE setup_retry_generation      <- empty map   # W8: per (RoundID, setup_kind) bounded retry counter (absent = 0 retries so far)
    INITIALISE residency_ledger          <- empty    # H7/I19: sole owner of per-miner t_<state> this round
    # Q5: PER-RUN state is NOT (re)created here — it comes from RunContext (RunInitialise, §1.0), preserved across
    #     rounds. RoundInitialise binds RunContext (EventQueueContext, RunHookContext, security_census maps,
    #     rebased_boundaries, run_finalised, run_horizon_T) by reference; it never resets them.
    IF prior_state != null:                          # subsequent round: REBASE residency across the boundary
      # K3/L5/M4 CROSS-ROUND RESIDENCY REBASE between the prior (terminal) round and this one, performed by the
      #    SINGLE idempotent owner SettleResidencyBoundary (§1a) with mode = REBASE_TO_NEXT_ROUND: it closes every
      #    open interval in the prior round (attributing energy to it) AND reopens the SAME state for this round
      #    at the IDENTICAL boundary_time -- NO transition energy. Keyed by boundary_id (RunContext.rebased_boundaries).
      SET boundary_id <- (prior_state.RoundID, RoundID_current)                     # L5: deterministic boundary id
      CALL SettleResidencyBoundary(this RoundContext, mode = REBASE_TO_NEXT_ROUND,
                                   boundary_id = boundary_id, prior_state = prior_state)   # M4/L5 (single owner; idempotent)
    TRANSITION round_state -> ROUND_INITIALISING     # each round-state change bumps state_version (G10)
    TRANSITION round_state -> TEMPLATE_COMMITMENT
  RETURNS: RoundContext(RoundID, D, nonce_domain, ledgers, RunContext,   # Q5: RunContext bound by reference
                        # per-round registries:
                        active_propagation_set, acceptance_batch_registry,
                        candidate_discovery_seq, block_accepted, state_version, residency_ledger,
                        # per-round recovery registries (Q5: returned EXPLICITLY):
                        recovery_episode_seq, current_recovery_episode, recovery_deadline_reached,
                        recovery_census_seq, latest_recovery_census, recovery_decision_seq, recovery_decisions,
                        pending_recovery_decisions, latest_recovery_decision, recovery_outcome_finalised,
                        recovery_episode_disposition,   # S4
                        recovery_install_in_progress, recovery_install_seq, active_recovery_install_decision,   # T3
                        setup_retry_generation)   # W8: per-round bounded setup-retry counter
  NOTE: Q5/I-04: every normative runtime registry is EXPLICITLY owned. Per-run state is created ONCE by
        RunInitialise (§1.0) and reused via RunContext; RoundInitialise initialises ONLY the per-round registries
        (reset each round) and returns them explicitly — including every per-round recovery registry
        (recovery_episode_seq, current_recovery_episode, recovery_deadline_reached, recovery_census_seq,
        latest_recovery_census, recovery_decision_seq, recovery_decisions, pending_recovery_decisions,
        latest_recovery_decision, recovery_outcome_finalised, recovery_episode_disposition). No registry exists as
        an implicit global.
  NOTE: G10: every `TRANSITION round_state -> S` in this document also bumps `state_version` (a round
        epoch); `SecurityFloorEvaluate` carries the epoch to reject stale evaluations.
```

## 1a. Residency boundary — one idempotent owner for BOTH round-boundary and run-end closure (K3; L5; M4)

A miner whose state PERSISTS across a round boundary (it is not transitioned at the boundary) must NOT
have its OPEN residency interval silently reset. The boundary is a bookkeeping settle, not a state
change. **M4/L5:** ONE procedure, `SettleResidencyBoundary`, owns EVERY residency close/reopen at a
boundary — both the cross-round rebase (`mode = REBASE_TO_NEXT_ROUND`: close the old-round interval,
attribute its energy to the old round, and reopen the SAME state at the IDENTICAL `boundary_time` for the
new round with NO transition energy) and the run-end settle (`mode = FINAL_RUN_END`: close every open
interval at the run horizon with NO reopen). It is IDEMPOTENT via a deterministic `boundary_id`, so a
retried/replayed `RoundInitialise` or `RoundAbort` never re-attributes or double-counts an interval. No
other procedure closes a residency interval at a boundary — in particular `CloseRoundAssignments` performs
NO residency/energy finalisation (M4); it records `round_terminal_time` only. The two former procedures
(`FinalizeRoundResidency` / `BeginRoundResidency`) are SUPERSEDED by this single owner. The idle interval
between a round's closure and the next round's `StartWake` (or the run horizon) is therefore counted
EXACTLY ONCE (invariant **I19**, amended for cross-round continuity).

```
PROCEDURE SettleResidencyBoundary
  INPUTS: RoundContext, mode, boundary_id, prior_state = null   # mode in {REBASE_TO_NEXT_ROUND, FINAL_RUN_END}
  PRECONDITIONS: for REBASE_TO_NEXT_ROUND: prior_state reached a terminal round state
                   (ROUND_ACCEPTED/ROUND_ABORTED) and recorded prior_state.round_terminal_time (by
                   CloseRoundAssignments, M4/L5); this round's residency_ledger is initialised (RoundInitialise);
                   boundary_id = (prior_state.RoundID, this RoundContext.RoundID);
                 for FINAL_RUN_END: the run is ending at the fixed horizon T; boundary_id = (RunID, RUN_END);
                   INVOKED ONLY by FinalizeSimulationRun (§20a/N1), never by RoundAbort
  EFFECTS:
    # M4/L5: the SINGLE owner of every boundary residency close/reopen (it REPLACES FinalizeRoundResidency +
    #     BeginRoundResidency, withdrawn). ApplyMinerStateTransition remains the sole owner of intervals for an
    #     ACTUAL state change; this procedure performs ONLY the no-state-change boundary settle.
    # (0) IDEMPOTENCE: a boundary already settled is a NO-OP -- no re-close, no re-attribution, no re-open. A
    #     replayed/retried RoundInitialise / RoundAbort therefore cannot double-count an interval.
    IF boundary_id in rebased_boundaries:
      RETURN settle_noop(boundary_id)                              # M4/L5: idempotent no-op
    IF mode = REBASE_TO_NEXT_ROUND:
      SET boundary_time <- prior_state.round_terminal_time         # recorded ONLY by CloseRoundAssignments (M4/L5)
      SET close_ledger  <- prior_state.residency_ledger ; SET attribute_to <- prior_state.RoundID
    ELSE:  # FINAL_RUN_END
      SET boundary_time <- run_horizon_T                           # the fixed simulation horizon
      SET close_ledger  <- RoundContext.residency_ledger ; SET attribute_to <- RoundID_current
    # (1) CLOSE every OPEN interval in close_ledger at boundary_time and attribute its energy. Boundary close
    #     only -- miner_state is unchanged, so NO E_transition/E_coordination is charged.
    FOR EACH miner m with an OPEN residency interval in close_ledger (stable MinerID order):
      CLOSE residency(m, miner_state(m)) at boundary_time          # accrues P_state * (boundary_time - last_boundary)
      ATTRIBUTE that interval's energy to attribute_to
    # (2) REBASE_TO_NEXT_ROUND ONLY: REOPEN the SAME state at the IDENTICAL boundary_time in the NEW round's
    #     ledger for every miner whose state continues across the boundary. NO transition energy. (FINAL_RUN_END
    #     performs NO reopen -- the run is over.)
    IF mode = REBASE_TO_NEXT_ROUND:
      FOR EACH miner m in {LOW_POWER_LISTEN, REGISTERED, RESERVE, OFFLINE, DISQUALIFIED} whose state
          continues across the boundary (stable MinerID order):
        OPEN residency(m, miner_state(m)) at boundary_time         # same state, same time; continues P_state accrual
        # do NOT charge E_transition/E_coordination: no state change occurred
    # (3) record the boundary as settled so any repeat is a no-op (the idempotence key).
    ADD boundary_id to rebased_boundaries
  RETURNS: residency_boundary_settled(mode, boundary_id, boundary_time)
  NOTE: M4/L5/K3/I19: the ONLY procedure that closes (and, for REBASE, reopens) an open residency interval at
        a boundary. IDEMPOTENT via boundary_id: a repeat is a no-op, so the idle interval between a round's
        closure and the next round's StartWake (or the run horizon) is counted EXACTLY ONCE (I19). The boundary
        contributes ZERO transition energy. CloseRoundAssignments records `round_terminal_time` ONLY and performs
        NO residency finalisation (M4). `t_ACTIVE_HASHING = t_hash` is unaffected (a terminal round has no
        ACTIVE_HASHING miner to continue).
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

## 2a. Next-round participant preparation (J5)

Miners parked in `LOW_POWER_LISTEN` after an accepted/aborted round have NO executable route back to
`ACTIVE_HASHING` unless a named path re-assigns them under the new round. `PrepareParticipantsForNewRound`
is that path: it runs in the `ASSIGNMENT` phase (after `RoundInitialise` and `TemplateCommit`, once a
fresh `RoundID` and committed `TemplateID` exist) and establishes the intended assignment set BEFORE
`ASSIGNMENT -> HASHING` (R4). It binds fresh `ORIGINAL`/`REASSIGNED` `PENDING` assignments to the NEW
identifiers and wakes each miner through its legal per-state edge; it NEVER reopens a CLOSED old-round
assignment (J7).

```
PROCEDURE PrepareParticipantsForNewRound
  INPUTS: RoundContext, dispatch_envelope                          # L1: this entry point's own dispatch envelope
  PRECONDITIONS: RoundInitialise and TemplateCommit have run for THIS round; round_state = ASSIGNMENT;
                 a fresh RoundID and a committed eligible TemplateID exist (the NEW round's identifiers);
                 # L1: dispatch_envelope = (EQ.current_event_time, EQ.current_delta_cycle, EQ.current_event_seq)
                 #     supplied by ProcessEventTime because this entry point was itself seated on the queue
                 #     through ScheduleEvent (§0.7f). NO manual `next EQ.event_creation_seq`.
  EFFECTS:
    # K4/L1: this is a SIM-DRIVER entry point. Every miner action below THREADS this entry point's own
    #     dispatch_envelope, so each StartWake / ApplyMinerStateTransition has a DEFINED
    #     (event_time, delta_cycle, event_seq) — the dispatched event's seq (never ambient, never hand-stamped).
    # W1/V8: maintain a LOCAL setup transaction record — carrying an IMMUTABLE rollback_envelope (this entry point's own
    #   dispatch_envelope: { envelope_namespace, event_time, delta_cycle, event_seq, hook_id }) — so an
    #   assignment_phase_failed can be ROLLED BACK executably with a COMPLETE transition_envelope (no placeholder).
    SET participant_setup_txn <- setup_transaction(rollback_envelope = dispatch_envelope,
          wakes = empty, created_assignments = empty, prior_states = empty)   # W1/V8
    SET participant_setup_error <- null   # V3/V8/W7: set when a CreatePendingAssignment or StartWake fails; checked after the loop
    # J5/K1: enumerate eligible miners in STABLE MinerID order (G7) and give each a legal new-round path.
    FOR EACH MinerID m IN SORT(eligible miners BY MinerID ascending):
      IF participant_setup_error != null: BREAK    # W7/V8: once the setup has failed, mint NO further work; roll back below
      # W7: determine the per-miner spec (origin, range, source, reassignment_reason, from_state); a CASE that offers no
      #   assignment records its explicit disposition and CONTINUEs. Then build + wake through ONE shared branch.
      SET spec <- null
      SWITCH miner_state(m):
        CASE REGISTERED:
          SELECT range from unassigned portion of nonce_domain            # fresh, never-assigned (I1)
          SET spec <- (origin = ORIGINAL, range = range, source = null, rr = null, from = REGISTERED)   # activation via T3
        CASE RESERVE:
          IF the new-round policy places an accepted-unsearched suffix S (with source_assignment) on m:
            SET spec <- (origin = REASSIGNED, range = S, source = source_of(S), rr = reassignment, from = RESERVE)   # F4/I9
          ELSE:
            SELECT range from unassigned portion of nonce_domain          # fresh, never-assigned (I1)
            SET spec <- (origin = ORIGINAL, range = range, source = null, rr = null, from = RESERVE)     # activation via T4
        CASE LOW_POWER_LISTEN:
          # K1: EVERY parked LOW_POWER_LISTEN miner has an EXPLICIT next-round disposition; no fall-through.
          SWITCH previous entry_stop_reason(m):                           # the reason it parked (I4)
            CASE VALID_SOLUTION_VERIFIED OR ROUND_ACCEPTED OR ROUND_ABORTED:
              ARCHIVE previous_round_entry_stop_reason(m) <- entry_stop_reason(m)              # audit history (I4)
              ASSERT no live head remains for m's prior-round lineage (its version is CLOSED, I18b/J7)
              SELECT range from unassigned portion of nonce_domain (NEW TemplateID)            # fresh (I1)
              SET spec <- (origin = ORIGINAL, range = range, source = null, rr = null, from = LOW_POWER_LISTEN)   # T10
            CASE RANGE_EXHAUSTED OR ASSIGNMENT_REVOKED:
              IF new_round_assignment_policy_offers_range(RoundContext, m):
                ARCHIVE previous_round_entry_stop_reason(m) <- entry_stop_reason(m)            # audit history (I4)
                SELECT range <- the policy-offered range (NEW TemplateID)                      # (I1)
                SET spec <- (origin = ORIGINAL, range = range, source = null, rr = null, from = LOW_POWER_LISTEN)   # T10
              ELSE:
                RECORD next_round_disposition(m) <- parked_no_range_offered ; CONTINUE          # explicit, recorded
        CASE OFFLINE OR DISQUALIFIED:
          # J5: NO assignment here. DISQUALIFIED is terminal; an OFFLINE miner rejoins ONLY via the T17 path.
          RECORD next_round_disposition(m) <- deferred_no_assignment ; CONTINUE
        DEFAULT:   # ACTIVE_HASHING / WAKING / EXHAUSTED_PENDING should not occur at a fresh round's ASSIGNMENT
          CONTINUE
      IF spec = null: CONTINUE
      # W7: build the head; BRANCH on the constructor result BEFORE reading AssignmentID, setting lease fields, or
      #   recording it in the transaction. A creation failure is a DECLARED setup failure (nothing created).
      SET cr <- CALL CreatePendingAssignment(RoundContext, m, spec.range,
                      assignment_origin = spec.origin, source_assignment = spec.source, reason = spec.rr)   # F4/W7
      IF cr is assignment_creation_failed(reason):
        SET participant_setup_error <- assignment_creation_failed(reason)   # W7: nothing created; setup failed
        CONTINUE
      SET a <- cr.assignment                                              # W7: cr = assignment_created(a) — safe to read now
      SET lease_start(a) <- now; SET lease_expiry(a) <- now + default_lease_duration
      RECORD participant_setup_txn.prior_states[m] <- spec.from ; ADD AssignmentID(a) to participant_setup_txn.created_assignments   # V8
      SET wr <- CALL StartWake(RoundContext, m, target_assignment = a, from_state = spec.from,
                     scheduling_context = ORDINARY_DISPATCH(dispatch_envelope))   # V2/V3: explicit context; structured result
      IF wr = wake_seated(waid, wref, wtt, ws): ADD wref to participant_setup_txn.wakes   # V8: capture ACTUAL WakeEventRef
      ELSE: SET participant_setup_error <- wr                                             # V3/V8: a wake failure IS a setup failure
    # V8: if a CreatePendingAssignment or StartWake in the loop failed, the setup is already failed — roll back and
    #   decide, do NOT proceed to CompleteAssignmentPhase.
    IF participant_setup_error != null:
      SET setup_reason <- participant_setup_error
    ELSE:
      # K2: the intended assignment set is now established (all PENDING, waking). Perform the EXPLICIT ASSIGNMENT ->
      #     HASHING transition through the named procedure (never prose-only R4). U6: CAPTURE and BRANCH on the disposition.
      SET disp <- CALL CompleteAssignmentPhase(RoundContext, dispatch_envelope)  # K2/T5: ASSIGNMENT -> HASHING (M1 envelope)
      IF disp = assignment_phase_completed: RETURN participant_set_prepared
      SET setup_reason <- disp.reason        # assignment_phase_failed(reason) — reversible (round still ASSIGNMENT)
    # W1/W2/V8: NAMED rollback using the txn's IMMUTABLE rollback_envelope. RollbackParticipantSetup departs any WAKING
    #   participant to OFFLINE via the LEGAL T12 edge and reports rolled_to_offline.
    SET rb <- CALL RollbackParticipantSetup(RoundContext, participant_setup_txn)   # W1/W2/V8
    IF rb = rollback_failed(rr):
      RETURN CALL RoundAbort(RoundContext, reason = participant_setup_rollback_failed,
                             dispatch_envelope = dispatch_envelope, recovery_finalising = false)   # declared abort
    # W8 LIVENESS: seat a bounded, state-compatible SetupRetryEvent ONLY when the rollback left EVERY participant in a
    #   state the setup can legally re-enlist (no miner routed to OFFLINE), the retry budget is not exhausted, and the
    #   strictly-later target is within horizon. Otherwise ABORT — never a retry from an incompatible OFFLINE state.
    IF rb.rolled_to_offline:
      RETURN CALL RoundAbort(RoundContext, reason = participant_setup_failed(setup_reason),
                             dispatch_envelope = dispatch_envelope, recovery_finalising = false)   # W8: retry state-incompatible
    IF setup_retry_generation[(RoundID_current, PARTICIPANT_SETUP)] >= maximum_setup_retries:
      RETURN CALL RoundAbort(RoundContext, reason = participant_setup_retries_exhausted(setup_reason),
                             dispatch_envelope = dispatch_envelope, recovery_finalising = false)   # W8: bounded
    IF next_representable_simulation_time(dispatch_envelope.event_time) <= run_horizon_T:
      SET g <- setup_retry_generation[(RoundID_current, PARTICIPANT_SETUP)] + 1     # W8: advance the bounded generation
      SET setup_retry_generation[(RoundID_current, PARTICIPANT_SETUP)] <- g
      SET srid <- (RoundID_current, PARTICIPANT_SETUP, g)                            # W8: SetupRetryID
      SET r <- CALL ScheduleEvent(EQ, RoundContext, SetupRetryEvent,
                     target_event_time = next_representable_simulation_time(dispatch_envelope.event_time),
                     target_microphase = ROUND_SETUP,
                     {RoundID = RoundID_current, setup_kind = PARTICIPANT_SETUP, SetupRetryID = srid,
                      setup_retry_generation = g, reason = setup_reason})            # W8
      IF r = scheduled(...): RETURN participant_set_setup_retry_seated(srid, setup_reason)
    RETURN CALL RoundAbort(RoundContext, reason = participant_setup_failed(setup_reason),
                           dispatch_envelope = dispatch_envelope, recovery_finalising = false)   # declared abort
  RETURNS: participant_set_prepared | participant_set_setup_retry_seated | round_aborted
  NOTE: K1: EVERY LOW_POWER_LISTEN entry_stop_reason (VALID_SOLUTION_VERIFIED, ROUND_ACCEPTED, ROUND_ABORTED,
        RANGE_EXHAUSTED, ASSIGNMENT_REVOKED) has an explicit disposition; VALID_SOLUTION_VERIFIED never falls through.
        It binds fresh ORIGINAL/REASSIGNED PENDING to the NEW RoundID/TemplateID and wakes via T3/T4/T10, never
        reopening a CLOSED/PAUSED old-round version (J7).
  NOTE: W7: every CreatePendingAssignment result is inspected BEFORE any AssignmentID/lease/transaction access; a
        creation failure sets participant_setup_error and mints no further work (the loop BREAKs). W1: the rollback runs
        with the txn's complete rollback_envelope. W2/W8: RollbackParticipantSetup departs any WAKING participant to
        OFFLINE via T12; a rollback that routed miners to OFFLINE, an exhausted retry budget, or a past-horizon target
        ABORTS — the round is NEVER left in ASSIGNMENT with no controller and NEVER retries from an incompatible state.
        Determinism: stable MinerID order (G7); every StartWake/CreatePendingAssignment routes through the single
        ScheduleEvent enqueue interface (J9/K8).

PROCEDURE RollbackParticipantSetup                              # W1/W2/V8: executable rollback of a failed participant setup
  INPUTS: RoundContext, setup_txn   # W1: { rollback_envelope, wakes: [WakeEventRef], created_assignments: [AssignmentID], prior_states: {MinerID -> state} }
  PRECONDITIONS: called by PrepareParticipantsForNewRound on a CreatePendingAssignment/StartWake failure or an
                 assignment_phase_failed, BEFORE the irreversible HASHING transition (round still ASSIGNMENT). It must
                 leave NO live partial assignment. W1: setup_txn.rollback_envelope is the caller's COMPLETE dispatch
                 envelope { envelope_namespace, event_time, delta_cycle, event_seq, hook_id }.
  EFFECTS:
    SET rolled_to_offline <- false   # W2: true iff any WAKING participant is legally departed to OFFLINE (T12)
    # W2: cancel captured wakes FIRST (so none can activate a head being closed).
    FOR EACH wref in setup_txn.wakes (stable order):
      IF wref is still pending on EQ: CANCEL wref on EQ
    # W2: a participant left WAKING is departed to OFFLINE via the LEGAL T12 edge (the ONLY legal WAKING departure
    #   besides T5/T21) using the txn's COMPLETE rollback_envelope (W1) — NEVER an illegal WAKING->REGISTERED/RESERVE/
    #   LOW_POWER_LISTEN edge and NEVER a placeholder/ambient envelope. T12 releases the bound range and charges no census.
    FOR EACH MinerID m in setup_txn.prior_states:
      IF miner_state(m) = WAKING:
        SET tr <- CALL ApplyMinerStateTransition(m, WAKING, OFFLINE,
               transition_envelope = setup_txn.rollback_envelope, reason = participant_setup_rolled_back,   # W1: complete envelope; T12
               assignment_ref = null, candidate_id = null, propagation_id = null)   # F6
        IF tr is transition_applied(teid): SET rolled_to_offline <- true    # W2/W8: a WAKING participant was legally departed
    # close every created head legally and restore the ledgers.
    FOR EACH aid in setup_txn.created_assignments (stable order):
      IF aid is a live head:
        CLOSE aid as CLOSED (status = CLOSED, custody_status = revoked, reason = participant_setup_rolled_back)   # J7/I18b
      RESTORE the coverage-state / custody ledgers for aid's range (I8a/I8b)
    IF any setup_txn.created_assignments entry remains a live head OR any setup_txn.wakes entry remains pending on EQ
       OR any m in setup_txn.prior_states remains WAKING:
      RETURN rollback_failed(reason = residual_partial_setup)
    RETURN rollback_completed(rolled_to_offline)   # W2/W8: report whether a retry is state-incompatible
  RETURNS: rollback_completed(rolled_to_offline) | rollback_failed(reason)
  NOTE: W1/W2/V8: the NAMED executable rollback for participant setup. It cancels the CAPTURED WakeEventRefs, departs
        any WAKING participant to OFFLINE via the LEGAL T12 edge with the txn's COMPLETE rollback_envelope (never an
        illegal WAKING->prior edge and never a placeholder envelope), closes every created PENDING head legally, and
        restores the ledgers — leaving NO live partial assignment and NO participant WAKING. It reports rolled_to_offline
        so the caller can refuse a state-incompatible retry (W8). A residual it cannot clear returns rollback_failed.

PROCEDURE RollbackTemplateRefreshSetup                          # W1/W2/V8: executable rollback of a failed template-refresh setup
  INPUTS: RoundContext, setup_txn   # W1: same shape as RollbackParticipantSetup's setup_txn (with rollback_envelope)
  PRECONDITIONS: called by TemplateRefresh on a CreatePendingAssignment/StartWake failure or an assignment_phase_failed
                 BEFORE the irreversible HASHING transition. W1: setup_txn.rollback_envelope is complete.
  EFFECTS:
    # W1/W2: identical rollback discipline as RollbackParticipantSetup, for the refresh's just-created assignments/wakes.
    SET rolled_to_offline <- false   # W2
    FOR EACH wref in setup_txn.wakes (stable order):
      IF wref is still pending on EQ: CANCEL wref on EQ
    FOR EACH MinerID m in setup_txn.prior_states:
      IF miner_state(m) = WAKING:
        SET tr <- CALL ApplyMinerStateTransition(m, WAKING, OFFLINE,
               transition_envelope = setup_txn.rollback_envelope, reason = template_refresh_rolled_back,   # W1: complete envelope; T12
               assignment_ref = null, candidate_id = null, propagation_id = null)   # F6
        IF tr is transition_applied(teid): SET rolled_to_offline <- true
    FOR EACH aid in setup_txn.created_assignments (stable order):
      IF aid is a live head:
        CLOSE aid as CLOSED (status = CLOSED, custody_status = revoked, reason = template_refresh_rolled_back)   # J7/I18b
      RESTORE the coverage-state / custody ledgers for aid's range (I8a/I8b)
    IF any created head remains live OR any wake remains pending OR any m remains WAKING:
      RETURN rollback_failed(reason = residual_partial_setup)
    RETURN rollback_completed(rolled_to_offline)   # W2/W8
  RETURNS: rollback_completed(rolled_to_offline) | rollback_failed(reason)
  NOTE: W1/W2/V8: the NAMED executable rollback for template-refresh setup — same legal-edge (T12) + complete-envelope
        discipline as RollbackParticipantSetup, reporting rolled_to_offline for the W8 retry decision.

PROCEDURE SetupRetryEvent                                       # W8: a bounded, idempotent, state-compatible retry of a rolled-back setup
  INPUTS: RoundContext, dispatch_envelope, RoundID, setup_kind, SetupRetryID, setup_retry_generation, reason
          # setup_kind in {PARTICIPANT_SETUP, TEMPLATE_REFRESH_SETUP}; SetupRetryID = (RoundID, setup_kind, generation)
  PRECONDITIONS: a dispatched queued handler seated by PrepareParticipantsForNewRound / TemplateRefresh after a
                 rolled-back setup; its dispatch_envelope is its own (§0.7f). Stale-guarded on RoundID.
  EFFECTS:
    # W8 STALE GUARD: the round must still be the same and in a state where the setup's preconditions can hold.
    IF RoundID != RoundID_current OR round_state NOT in {ASSIGNMENT, ROUND_INITIALISING, TEMPLATE_COMMITMENT}:
      RETURN setup_retry_stale_noop(SetupRetryID)          # the round moved on; retry is a no-op
    # W8 IDEMPOTENCE: a replay of an already-applied SetupRetryID runs the setup at most ONCE.
    IF SetupRetryID in applied_setup_retry_ids:
      RETURN setup_retry_duplicate_suppressed(SetupRetryID)
    # W8 BOUND: never run a retry beyond the budget.
    IF setup_retry_generation > maximum_setup_retries:
      RETURN setup_retry_exhausted(SetupRetryID)
    # W8 STATE COMPATIBILITY: every eligible participant of RoundID must be in a state the setup can legally re-enlist
    #   ({REGISTERED, RESERVE, LOW_POWER_LISTEN}); if a prior rollback stranded a participant OFFLINE, ABORT rather than
    #   retry (do NOT claim a retry path from an incompatible state).
    IF NOT (every eligible participant of RoundID is in miner_state {REGISTERED, RESERVE, LOW_POWER_LISTEN}):
      RETURN CALL RoundAbort(RoundContext, reason = setup_retry_state_incompatible(setup_kind),
                             dispatch_envelope = dispatch_envelope, recovery_finalising = false)   # W8
    ADD SetupRetryID to applied_setup_retry_ids            # W8: register the idempotent marker BEFORE re-invoking
    IF setup_kind = PARTICIPANT_SETUP:
      RETURN CALL PrepareParticipantsForNewRound(RoundContext, dispatch_envelope)   # W8: re-run the setup (its own liveness path governs)
    RETURN CALL TemplateRefresh(RoundContext, dispatch_envelope = dispatch_envelope)   # W8: re-run the refresh
  RETURNS: setup_retry_stale_noop | setup_retry_duplicate_suppressed | setup_retry_exhausted | round_aborted |
           (the re-run setup's disposition)
  NOTE: W8: the retry is STATE-COMPATIBLE (aborts if any eligible participant is OFFLINE), IDEMPOTENT (SetupRetryID +
        applied_setup_retry_ids suppress a duplicate), and BOUNDED (setup_retry_generation <= maximum_setup_retries).
        It re-invokes the setup at a strictly-later event_time, so the round is never stranded in ASSIGNMENT with no
        controller. A round that has moved on no-ops; an incompatible or exhausted retry ABORTS rather than limping on.
```

## 2a-bis. Round-state transition helper — automatic applicability-entry census (M2)

Every entry into a FLOOR-APPLICABLE round state (`HASHING`, `SOLUTION_PROPAGATION`, `SECURITY_RECOVERY`)
must capture a coherent applicability-entry census (K7), so the event-time epilogue can decide the floor
even when no miner-state boundary occurs at that exact `event_time`. To make this automatic and uniform,
ALL non-epilogue round-state transitions route through ONE helper `TransitionRoundState`, which bumps the
state epoch and, whenever the NEW state is floor-applicable, captures the census at
`dispatch_envelope.event_time`. The ONE exception is the recovery transition performed INSIDE
`SecurityFloorEvaluate` (the epilogue): that entry is the RESULT of evaluating an already-coherent census
at the SAME `event_time`, so re-capturing there would re-dirty an event_time whose epilogue is mid-run
(forbidden) — `SecurityFloorEvaluate` therefore keeps its direct transition (documented below), and it is
the ONLY round-state transition not routed through this helper.

```
PROCEDURE TransitionRoundState
  INPUTS: RoundContext, new_state, dispatch_envelope
  PRECONDITIONS: (round_state -> new_state) is a legal round transition (STAGE_01_ROUND_STATE_MACHINE.md);
                 called from a dispatched handler / entry point whose dispatch_envelope is threaded in;
                 NOT called by the SecurityFloorEvaluate epilogue (which transitions to SECURITY_RECOVERY directly)
  EFFECTS:
    TRANSITION round_state -> new_state                          # bumps state_version (G10)
    # M2/K7: capture the applicability-entry census on entry to ANY floor-applicable state, so the epilogue
    #        decides even with no miner-state boundary at this event_time (e.g. H_active = 0, positive-latency
    #        resumes, an unchanged census). Non-applicable states (setup/refresh/exhausted/terminal) capture nothing.
    IF new_state in {HASHING, SOLUTION_PROPAGATION, SECURITY_RECOVERY}:      # floor-applicable states (J6)
      CALL CaptureSecurityCensusOnApplicabilityEntry(RoundContext, entered_state = new_state,
                                                     at = dispatch_envelope.event_time)   # M2/K7
  RETURNS: round_state_transitioned(new_state)
  NOTE: M2: the SINGLE round-state transition owner for every dispatched (non-epilogue) transition. Floor-
        applicable entries ALWAYS capture a coherent census (K7); the only floor-applicable entry NOT routed
        here is the SecurityFloorEvaluate epilogue's HASHING/SOLUTION_PROPAGATION -> SECURITY_RECOVERY, whose
        census is the one the epilogue just evaluated (re-dirtying mid-epilogue is forbidden). N2: the
        recovery-EXIT transitions SECURITY_RECOVERY -> HASHING and SECURITY_RECOVERY -> SOLUTION_PROPAGATION
        ARE executable and route through this helper (from CompleteSecurityRecovery, §10a/R13), so they
        capture the applicability-entry census.
```

## 2b. Assignment-phase completion (K2; census via the M2 helper)

`PrepareParticipantsForNewRound` calls `CompleteAssignmentPhase` after the intended assignment set is
built; the `ASSIGNMENT -> HASHING` transition (R4) is thus an EXECUTABLE named step, not prose. No
`HashWorkEvent` may execute while the round is still `ASSIGNMENT` — hashing begins only after this
transition (and only at each miner's own `WakeCompleteEvent`).

```
PROCEDURE CompleteAssignmentPhase
  INPUTS: RoundContext, dispatch_envelope            # M1: threaded envelope (from the driver entry point)
  PRECONDITIONS: round_state = ASSIGNMENT; a committed RoundID and TemplateID exist; the intended
                 assignment set has been established; every PENDING assignment satisfies I1/I3/I18b;
                 NO assignment is bound to an old RoundID or TemplateID
  EFFECTS:
    # T5: verify the intended set is well-formed and RETURN an EXPLICIT disposition. A well-formedness failure is
    #     caught BEFORE the irreversible HASHING transition and returns assignment_phase_failed — NO failed ASSERT
    #     may strand a caller in ASSIGNMENT (T5/gate 6/gate 7).
    IF NOT (for every PENDING assignment a: a is bound to (RoundID_current, TemplateID_committed)   # I3
            AND a is disjoint per I1 AND a's lineage has exactly one live head, I18b)
       OR some assignment references an old RoundID/TemplateID:
      RETURN assignment_phase_failed(reason = malformed_assignment_set)     # T5: BEFORE the HASHING transition (round still ASSIGNMENT — reversible)
    # M2/K2: the SOLE executable ASSIGNMENT -> HASHING (R4) step, performed through the round-state helper,
    #        which captures the applicability-entry census automatically (floor is decided even at H_active = 0).
    CALL TransitionRoundState(RoundContext, HASHING, dispatch_envelope)     # R4 + K7 capture (M2)
    IF round_state != HASHING:
      RETURN assignment_phase_failed(reason = transition_failed)            # T5: defensive (should not occur)
    RETURN assignment_phase_completed
  RETURNS: assignment_phase_completed | assignment_phase_failed(reason)     # T5: explicit executable disposition
  NOTE: K2/M2/T5: the SOLE executable ASSIGNMENT -> HASHING step, now returning an EXPLICIT disposition. A caller
        (recovery installation, §10a) MUST branch on the disposition rather than `ASSERT round_state = HASHING` (T5):
        an `assignment_phase_failed(malformed_assignment_set)` leaves the round in ASSIGNMENT (reversible — the
        caller rolls back), and a post-transition defensive failure is separate. `HashWorkEvent` is never scheduled
        into a round that remains ASSIGNMENT (a HashWorkEvent dispatched while round_state != HASHING is a no-op,
        §5). The census is captured by the M2 helper on entry to HASHING so the epilogue can decide the floor.
```

## 3. Miner registration

```
PROCEDURE MinerRegister
  INPUTS: RoundContext, join_request, dispatch_envelope            # L1: this entry point's own dispatch envelope
  PRECONDITIONS: round admits participation;
                 # L1: dispatch_envelope = (EQ.current_event_time, EQ.current_delta_cycle, EQ.current_event_seq)
                 #     supplied by ProcessEventTime — MinerRegister is itself seated on the queue through
                 #     ScheduleEvent (§0.7f). NO manual `next EQ.event_creation_seq`.
  EFFECTS:
    SET MinerID <- identifier for join_request
    CREATE miner_record(MinerID) with declared power parameters
        (P_hash, P_listen, P_wake, P_offline)
    # K4/L1: MinerRegister is a SIM-DRIVER entry point; it THREADS its own dispatch_envelope so its
    #     transitions have DEFINED (event_time, delta_cycle, event_seq) -- never ambient, never hand-stamped.
    # F6: every miner-state change routes through the hook (0.3); T1 uses old_state = NONE.
    CALL ApplyMinerStateTransition(MinerID, old_state = NONE, new_state = REGISTERED,
                                   transition_envelope = dispatch_envelope, reason = register,   # S1: ONE envelope object
                                   assignment_ref = null, candidate_id = null, propagation_id = null)   # T1 (L1)
    OPTIONALLY CALL ApplyMinerStateTransition(MinerID, old_state = REGISTERED, new_state = RESERVE,
                                   transition_envelope = dispatch_envelope, reason = admit_to_reserve,   # S1: ONE envelope object
                                   assignment_ref = null, candidate_id = null, propagation_id = null)   # T2 (L1)
  RETURNS: MinerID
  NOTE: Registration is the precondition for any assignment. Sybil considerations are OUT OF
        SCOPE at Stage 1 (see STAGE_01_THREAT_MODEL.md); this procedure does not claim Sybil
        resistance.
```

## 4. Range assignment

```
PROCEDURE RangeAssign
  INPUTS: RoundContext, MinerID, requested_size, lease_duration,
          scheduling_context   # U2: SchedulingSourceContext — ORDINARY_DISPATCH(dispatch_envelope) for a dispatched
                               #   caller, or POST_EPILOGUE(pctx) when CommitRecoveryAssignmentPlan calls it (§10a)
  PRECONDITIONS: miner_state(MinerID) in {REGISTERED, RESERVE}; round_state = ASSIGNMENT or HASHING;
                 # U2: scheduling_context is threaded to StartWake -> ScheduleEvent; a POST_EPILOGUE caller's wake is
                 #     seated STRICTLY LATER. A dispatched caller equivalently passes ORDINARY_DISPATCH(dispatch_envelope).
  EFFECTS:
    # W5: the ORDINARY entry point performs POLICY SELECTION, then delegates the EXACT-values MUTATION to the
    #   plan-bound RangeAssignFromPlan. The recovery-plan commit path (CommitRecoveryAssignmentPlan) calls
    #   RangeAssignFromPlan DIRECTLY with the plan's exact values, so a committed range assignment equals its validated
    #   plan and NEITHER path wakes twice (one create-then-wake transaction).
    SELECT candidate_range from unassigned portion of nonce_domain      # fresh, never-assigned -> ORIGINAL
    RETURN CALL RangeAssignFromPlan(RoundContext, MinerID = MinerID, range = candidate_range,
                     assignment_origin = ORIGINAL, source_assignment = null, reassignment_reason = null,
                     lease_duration = lease_duration, scheduling_context = scheduling_context)   # W5
  RETURNS: range_assigned(AssignmentID, WakeEventRef, resulting_state = WAKING) |
           range_assign_creation_failed(reason) | range_assign_wake_failed(reason, AssignmentID)
  NOTE: W5: RangeAssign SELECTS the fresh ORIGINAL range and delegates the atomic create-then-wake to
        RangeAssignFromPlan; it never performs the mutation itself. It returns the plan-bound constructor's structured
        disposition unchanged.

PROCEDURE RangeAssignFromPlan                                   # W5: plan-bound create-then-wake; EXACT values, NO SELECT
  INPUTS: RoundContext, MinerID, range, assignment_origin, source_assignment, reassignment_reason,
          lease_duration, scheduling_context   # W5: the caller's EXACT validated spec fields (no independent SELECT)
  PRECONDITIONS: miner_state(MinerID) in {REGISTERED, RESERVE}; round_state = ASSIGNMENT or HASHING or SECURITY_RECOVERY;
                 range/origin/source are the caller's exact values (validated by PrepareRecoveryAssignmentPlan for the
                 recovery-plan path, or SELECTed by RangeAssign for the ordinary path). It performs NO SELECT.
  EFFECTS:
    # W7: build the PENDING head via the constructor and BRANCH on its explicit result BEFORE reading AssignmentID or
    #   setting lease fields — a creation failure is a DECLARED disposition, nothing created.
    SET cr <- CALL CreatePendingAssignment(RoundContext, MinerID, range,
                    assignment_origin = assignment_origin, source_assignment = source_assignment, reason = reassignment_reason)
    IF cr is assignment_creation_failed(reason):
      RETURN range_assign_creation_failed(reason = reason)              # W7: nothing created; no AssignmentID exists
    SET assignment <- cr.assignment                                     # W7: cr = assignment_created(assignment)
    # W5: the committed object equals the EXACT spec (no divergence via a re-SELECT).
    ASSERT MinerID(assignment) = MinerID AND range(assignment) = range
           AND assignment_origin(assignment) = assignment_origin
           AND source_assignment_ref(assignment) = source_assignment    # W5
    SET lease_start(assignment)  <- now
    SET lease_expiry(assignment) <- now + lease_duration
    # F5/F6/D2/V3: activation ALWAYS passes through WAKING via the NON-BLOCKING StartWake TRANSACTION; WAKING ->
    #           ACTIVE_HASHING (T5) and PENDING -> CURRENT happen later in WakeCompleteEvent. Exactly ONE wake.
    SET fs <- miner_state(MinerID)   # V3: capture from_state so a failed wake can be asserted / rolled back
    SET wr <- CALL StartWake(RoundContext, MinerID, target_assignment = assignment,
                     from_state = fs,
                     scheduling_context = scheduling_context)        # T3 (REGISTERED) or T4 (RESERVE); V2/V3: STRUCTURED result
    IF wr = wake_seated(waid, wref, wtt, ws):
      RETURN range_assigned(AssignmentID = AssignmentID(assignment), WakeEventRef = wref, resulting_state = WAKING)   # V3/V9
    # V3/V9: the wake FAILED after the PENDING assignment was created. StartWake left the miner in fs (never WAKING)
    #   and cancelled any seated event; ROLL BACK the un-activated head legally and restore the ledgers.
    IF wr = wake_transition_failed_after_seat(reason2, wref):
      IF wref is still pending on EQ: CANCEL wref on EQ                # idempotent; StartWake already cancelled
    CLOSE assignment as CLOSED (status = CLOSED, custody_status = revoked, reason = range_assign_wake_failed)   # J7/I18b: no live head
    RESTORE the coverage-state / custody ledgers for range (I8a/I8b)
    ASSERT miner_state(MinerID) = fs                                  # V3/gate 4: the miner is not left WAKING
    RETURN range_assign_wake_failed(reason = wr, AssignmentID = AssignmentID(assignment))   # V3/V9
  RETURNS: range_assigned(AssignmentID, WakeEventRef, resulting_state = WAKING) |
           range_assign_creation_failed(reason) | range_assign_wake_failed(reason, AssignmentID)
  NOTE: W5/W7: the plan-bound create-then-wake constructor. It uses the EXACT spec values (no SELECT), branches on the
        CreatePendingAssignment result BEFORE any AssignmentID access (W7), asserts the committed object equals the spec
        (W5), performs EXACTLY ONE StartWake, and returns a structured disposition. On a wake failure it closes the
        un-activated head legally and restores the ledgers so no orphan PENDING remains. A zero wake-latency
        experimental value is permitted later, but the WAKING state and its P_wake*t_wake + E_transition accounting
        path always exist (D2); the miner reaches ACTIVE_HASHING at its own wake-completion event (F5).
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
    # G9/M5: schedule ONE bounded unit of hash work through ScheduleEvent with an EXPLICIT target microphase.
    CALL ScheduleEvent(EQ, RoundContext, HashWorkEvent,
                       target_event_time = now + modeled_hash_step_time, target_microphase = HASH_WORK,
                       {MinerID, AssignmentID(assignment), assignment_version(assignment),
                        RoundID, TemplateID, from_cursor})   # M5: explicit microphase; carries identity keys
  RETURNS: scheduled

PROCEDURE HashWorkEvent
  INPUTS: RoundContext, MinerID, AssignmentID, assignment_version, RoundID, TemplateID, cursor, dispatch_envelope
  PRECONDITIONS: this is the scheduled hash-work unit for MinerID (envelope carries the identity keys);
                 # M1: dispatch_envelope = this dispatched HashWorkEvent's own (event_time, delta_cycle, event_seq),
                 #     threaded to ExhaustionAdjudicate and ScheduleSolutionPropagation (both reach the hook).
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
      # K2: ASSIGNMENT is NOT a hashing-capable state, so a HashWorkEvent dispatched while the round is
      #     still ASSIGNMENT (before CompleteAssignmentPhase performed ASSIGNMENT -> HASHING) is a NO-OP.
      #     Hashing begins only AFTER the explicit ASSIGNMENT -> HASHING transition (K2) and each miner's
      #     own WakeCompleteEvent.
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
      RETURN CALL ScheduleSolutionPropagation(RoundContext, certificate, snapshot, finder = MinerID,
                                              dispatch_envelope = dispatch_envelope)   # M1: threaded envelope
    ADVANCE cursor
    PERIODICALLY CALL ProgressCommit(assignment, cursor)        # emits progress evidence
    IF cursor beyond range(assignment):
      # D3: actual completion -> ground truth, reported claim, adjudicate.
      CALL ActualRangeCompletion(RoundContext, assignment)
      CALL ReportedExhaustionClaim(RoundContext, assignment, MinerID)
      RETURN CALL ExhaustionAdjudicate(RoundContext, assignment, MinerID, mode,
                                       dispatch_envelope = dispatch_envelope)   # M1: threaded envelope
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
  INPUTS: RoundContext, assignment, MinerID, mode (honest | adversarial), dispatch_envelope   # M1: threaded envelope
  PRECONDITIONS: a ReportedExhaustionClaim exists for assignment;
                 # M1: dispatch_envelope is the envelope of the dispatched HashWorkEvent that called here.
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
      CALL ApplyMinerStateTransition(MinerID, ACTIVE_HASHING, EXHAUSTED_PENDING,
                                     transition_envelope = dispatch_envelope,   # S1: ONE envelope object
                                     reason = RANGE_EXHAUSTED, assignment_ref = assignment,
                                     candidate_id = null, propagation_id = null)   # T7 (M1)
    # REJECTED: do NOT mark searched/completed; do NOT enter EXHAUSTED_PENDING
    ELSE:
      RECORD false_exhaustion_detected(MinerID, assignment)      # progress/audit violation, NOT I11
      PRESERVE actual coverage (accepted_frontier unchanged; range NOT searched/completed)
      # M1: the policy-dependent adversarial/failure response is applied through the ordinary named
      #     procedures, each threading dispatch_envelope: a revocation first CLOSES the CURRENT head (via
      #     EnterLowPowerListen, stop_reason = ASSIGNMENT_REVOKED) and only THEN reassigns the accepted
      #     unsearched suffix (RangeReassign requires status(source) = CLOSED, L4); or RoundAbort(RoundContext,
      #     reason = false_exhaustion_claim, dispatch_envelope) per policy. Absent such a response the miner
      #     remains ACTIVE_HASHING (no PATH-A transition).
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
          pause_cause_candidate_id = null, pause_cause_propagation_id = null,   # F2: required for PATH B only
          custody_on_close = revoked, termination_reason = assignment_revoked,  # K6: caller may classify the CLOSE
          dispatch_envelope                                                     # M1: explicit envelope threaded in
                                                                                #     (lease expiry -> expired/lease_expiry)
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
        SET status(assignment_ref)         <- CLOSED           # J7: exhaustion completion is CLOSED (not SUPERSEDED)
        SET termination_reason(assignment_ref) <- range_exhausted   # K6 declared reason (custody stays completed)
        # do NOT release or reassign any part of the completed range

      CASE ASSIGNMENT_REVOKED:
        ASSERT from_state = ACTIVE_HASHING
        PRESERVE accepted searched prefix [range_start(assignment_ref), accepted_frontier(assignment_ref)]
        SET suffix <- accepted unsearched suffix [accepted_frontier(assignment_ref) + 1, range_end(assignment_ref)]
        MARK suffix as inactive_unsearched / reassignable      # only the accepted unsearched suffix (C4)
        # J7/K6: revocation/lease-expiry is CLOSED, never SUPERSEDED. The caller classifies the CLOSE:
        #        default revoked/assignment_revoked; lease expiry passes expired/lease_expiry (K6). I18a/I18b
        #        hold: one live CURRENT head before this atomic step, zero after (a CLOSED lineage).
        ATOMICALLY:
          SET status(assignment_ref)              <- CLOSED
          SET custody_status(range(assignment_ref)) <- (custody_on_close = expired ? expired : revoked)
          IF custody_on_close = revoked: SET revocation_reason(assignment_ref) <- assignment_revoked   # I-07
          SET termination_reason(assignment_ref)   <- termination_reason        # K6 (assignment_revoked | lease_expiry)

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
        SET status(assignment_ref) <- CLOSED                   # J7: round closure is CLOSED (not SUPERSEDED)
        # do NOT mark the range exhausted; do NOT reassign it under the closed TemplateID

    RECORD entry_stop_reason(MinerID) <- stop_reason           # I4: why the miner left ACTIVE_HASHING
    # F6: the LOW_POWER_LISTEN entry (and its P_hash/P_listen boundary + I17 recompute) is applied
    #     by the hook. For PATH A the source is EXHAUSTED_PENDING (already off H_active); for the
    #     other reasons the source is ACTIVE_HASHING (this is the H_active exit boundary).
    CALL ApplyMinerStateTransition(MinerID, from_state, LOW_POWER_LISTEN,
                                   transition_envelope = dispatch_envelope,   # S1: ONE envelope object (ORDINARY_EVENT, or RUN_HOOK+HorizonHookID at horizon close)
                                   reason = stop_reason, assignment_ref = assignment_ref,
                                   candidate_id = pause_cause_candidate_id,
                                   propagation_id = pause_cause_propagation_id)  # J3: BOTH ids; T8/T26/T27/T28/T29 (M1/S1)
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
  INPUTS: RoundContext, MinerID, direction, dispatch_envelope   # direction in {enter, exit}; L1 envelope
  PRECONDITIONS: this is a scheduled event emitted by the adversarial-participation model for one
                 adversarial-classified MinerID (the model's [SIMULATION SAMPLING] draw is WHEN/WHICH
                 adversarial miner changes participation -- see the sampling summary);
                 # L1: as a queued handler, its dispatch_envelope is its OWN dispatching event envelope
                 #     (§0.7f); it THREADS that envelope into every RangeAssign / ResumeFromPause / StartWake
                 #     and every ApplyMinerStateTransition (the positional `now` calls bind it, §0.9/L1).
  EFFECTS:
    # G3/H6: the ONLY carrier of a modeled adversarial participation change. It changes miner_state
    #     ONLY through the hook, so residency (single owner, H7), transition energy, the
    #     H_active/H_honest/H_adversarial recompute, and I17 all happen exactly once (F6). It NEVER
    #     adds/removes a miner from H_active directly. Because the census-changing boundary is a hook
    #     transition, the hook flags security_census_dirty[now] and overwrites latest_security_census[now],
    #     and the SINGLE event-time epilogue FinalizeEventTimeSecurityCensus evaluates the floor once (I-01).
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
      # I-07: use the CANONICAL custody enum ONLY. The withdrawal cause lives in revocation_reason,
      #       never in an invented custody_status value (no `revoked_adversarial_exit`).
      SET custody_status(range(X)) <- revoked                    # canonical enum value
      SET revocation_reason(X)     <- adversarial_withdrawal     # I-07 two-field representation
      RECORD provenance(X): previous_assignment_reference, custody_status = revoked, revocation_reason = adversarial_withdrawal
      # H7/G9: cancel this version's pending hash-work units explicitly (they would self-cancel by the
      #        stale guard, but the exit CANCELS them so no unit is charged after the census leaves H_active).
      CANCEL pending HashWorkEvent units for (MinerID, AssignmentID(X), assignment_version(X))
      # J7: adversarial withdrawal TERMINATES the version -- status = CLOSED (never SUPERSEDED; SUPERSEDED
      #     is renewal-only). custody_status = revoked, revocation_reason = adversarial_withdrawal (I-07).
      #     After this, the lineage has ZERO live heads (I18b).
      SET status(X) <- CLOSED                                   # no live CURRENT head remains (I18a/I18b)
      CALL ApplyMinerStateTransition(MinerID, ACTIVE_HASHING, OFFLINE,
             transition_envelope = dispatch_envelope,   # S1: ONE envelope object
             reason = adversarial_withdrawal, assignment_ref = X, candidate_id = null, propagation_id = null)   # T11 (F6/M1)
      RETURN participation_exit_record(MinerID, closed_version = X, reassignable_suffix = suffix, terminal_status = CLOSED)

    ELSE:   # direction = enter
      # ---- ENTRY: reach ACTIVE_HASHING ONLY at a future WakeCompleteEvent (F5); never a direct add. ----
      SWITCH miner_state(MinerID):

        CASE REGISTERED OR RESERVE:
          # H6: no live head exists; create/bind a fresh PENDING and wake. RangeAssign (REGISTERED->WAKING
          #     T3 / RESERVE->WAKING T4) builds a PENDING via CreatePendingAssignment and StartWake (F4/F5).
          RETURN CALL RangeAssign(RoundContext, MinerID, requested_size = modeled,
                                  lease_duration = default_lease_duration,
                                  scheduling_context = ORDINARY_DISPATCH(dispatch_envelope))   # V2: explicit context (L1 envelope)

        CASE OFFLINE:
          # H6: rejoin the round through the hook FIRST (OFFLINE -> REGISTERED, T17), then create/bind a
          #     fresh PENDING and wake -- never a direct census add.
          CALL ApplyMinerStateTransition(MinerID, OFFLINE, REGISTERED,
                 transition_envelope = dispatch_envelope, reason = adversarial_rejoin,   # S1: ONE envelope object
                 assignment_ref = null, candidate_id = null, propagation_id = null)    # T17 (F6/M1)
          RETURN CALL RangeAssign(RoundContext, MinerID, requested_size = modeled,
                                  lease_duration = default_lease_duration,
                                  scheduling_context = ORDINARY_DISPATCH(dispatch_envelope))   # V2: explicit context (L1 envelope)

        CASE LOW_POWER_LISTEN:
          # I-06: STATE-SPECIFIC re-entry split by entry_stop_reason (I4) AND the CURRENT round's liveness.
          #       A closed/refreshing round NEVER receives a fresh assignment or a wake here.
          SWITCH entry_stop_reason(MinerID):

            CASE VALID_SOLUTION_VERIFIED:
              # PATH-B pause: resume the miner's OWN still-PAUSED head via ResumeFromPause carrying ITS
              # recorded pause-cause ids (matched two-id, G11); NEVER RangeAssign (no second live head,
              # I18b). A terminal round would already have CLOSED this head (CloseRoundAssignments), so
              # reaching here implies the round is still live and the head is genuinely PAUSED.
              SET paused <- paused_assignment(MinerID)
              RETURN CALL ResumeFromPause(RoundContext, MinerID, trigger = adversarial_reactivation,
                       pause_cause_candidate_id   = pause_cause_candidate_id(paused),      # G11: matched ids
                       pause_cause_propagation_id = pause_cause_propagation_id(paused),     # T30
                       dispatch_envelope = dispatch_envelope)                               # L1: threaded envelope

            CASE RANGE_EXHAUSTED OR ASSIGNMENT_REVOKED:
              # I-06: a fresh assignment is legal ONLY when the CURRENT round is NONTERMINAL, is NOT
              #       mid-template-refresh, has a committed ELIGIBLE TemplateID, and its assignment
              #       policy permits a fresh range. Otherwise the re-entry is DEFERRED, not forced.
              IF round_state in {ROUND_ACCEPTED, ROUND_ABORTED}:
                RETURN deferred_round_terminal        # closed round: no assignment/wake (see terminal case)
              IF round_state = TEMPLATE_REFRESH:
                RETURN deferred_to_new_template        # governed by the new-template assignment procedure
              IF NOT (a committed eligible TemplateID exists for RoundContext
                      AND assignment_policy_permits_fresh_range(RoundContext)):
                RETURN no_eligible_range_now           # policy offers no fresh range at this instant
              # legal fresh re-entry via T10 (LOW_POWER_LISTEN -> WAKING new assignment), NOT RangeAssign
              # (whose precondition is REGISTERED/RESERVE, T3/T4). Bind a NEW ORIGINAL lineage (I18b).
              SELECT candidate_range from unassigned portion of nonce_domain    # fresh, never-assigned (I1)
              SET cr <- CALL CreatePendingAssignment(RoundContext, MinerID, candidate_range,
                         assignment_origin = ORIGINAL, source_assignment = null, reason = null)   # F4/W7
              IF cr is assignment_creation_failed(reason):
                RETURN participation_reentry_creation_failed(MinerID, reason)   # W7: nothing created; no wake
              SET fresh <- cr.assignment                                        # W7: cr = assignment_created(fresh)
              SET lease_start(fresh)  <- now
              SET lease_expiry(fresh) <- now + default_lease_duration
              RETURN CALL StartWake(RoundContext, MinerID, target_assignment = fresh,
                                    from_state = LOW_POWER_LISTEN,
                                    scheduling_context = ORDINARY_DISPATCH(dispatch_envelope))   # V2/V3: explicit context; structured result

            CASE ROUND_ACCEPTED OR ROUND_ABORTED:
              # I-06: the miner idled because the ROUND ENDED. Do NOT create an assignment in the closed
              #       RoundContext and do NOT StartWake for the closed round. Participation is DEFERRED
              #       to the next RoundInitialise / TemplateCommit / ASSIGNMENT phase, which re-offers
              #       ranges legally under a fresh RoundID/TemplateID.
              RETURN deferred_round_terminal
          # I-06 (TEMPLATE_REFRESH round-state): when the round is refreshing its template, a
          # RANGE_EXHAUSTED/ASSIGNMENT_REVOKED re-entry is deferred (above) to the new-template
          # assignment procedure -- TemplateRefresh commits the new TemplateID and then re-offers ranges
          # (T10 under the new template). No activation is performed against a discarded template.

        DEFAULT:
          # WAKING / ACTIVE_HASHING / EXHAUSTED_PENDING / DISQUALIFIED: already participating or in a
          # transient/terminal state; no participation change is applied.
          RETURN no_change
  RETURNS: participation_change_record
  NOTE: I-06: LOW_POWER_LISTEN re-entry is split by entry_stop_reason: VALID_SOLUTION_VERIFIED resumes
        the own PAUSED head (ResumeFromPause, never RangeAssign); RANGE_EXHAUSTED/ASSIGNMENT_REVOKED
        create a fresh T10 assignment ONLY in a nonterminal, non-refreshing, committed-eligible-template
        round whose policy permits a range; ROUND_ACCEPTED/ROUND_ABORTED defer to the next round; a
        TEMPLATE_REFRESH round defers to the new-template assignment procedure. No assignment or wake is
        ever created against a closed or discarded-template RoundContext.
  NOTE: H6 exit acts ONLY on ACTIVE_HASHING: preserve accepted coverage, expose only the accepted
        unsearched suffix, record the I9 reason/provenance, set custody_status = revoked with
        revocation_reason = adversarial_withdrawal (canonical enum, I-07), cancel the version's pending
        hash units, close the CURRENT head explicitly (no live head remains), depart via T11.
  NOTE: G3: the adversarial-participation SAMPLING is entirely in the SCHEDULING of these events (the
        model draws each miner's enter/exit times); the STATE CHANGE is deterministic and routes
        through the hook. ActiveHashRateUpdate never mutates the census (C7 preserved: floor breaches
        are recorded only by SecurityFloorEvaluate, invoked once per event_time by the event-time
        epilogue FinalizeEventTimeSecurityCensus, I-01).
```

## 9. Security-floor evaluation

```
PROCEDURE CaptureSecurityCensusOnApplicabilityEntry
  INPUTS: RoundContext, entered_state, at   # entered_state in {HASHING, SOLUTION_PROPAGATION, SECURITY_RECOVERY}; at = event_time
  PRECONDITIONS: the round has JUST transitioned INTO entered_state (a floor-APPLICABLE state, J6/K7)
  EFFECTS:
    # K7: the floor must be evaluated when the round ENTERS a floor-applicable state, even if NO
    #     miner-state boundary occurred at this event_time (e.g. ASSIGNMENT -> HASHING with H_active = 0
    #     because no WakeCompleteEvent has yet succeeded). Compute the census NOW and write the SAME two
    #     maps the miner-hook writes, TOGETHER and coherently (J1), so the event-time epilogue decides once.
    SET H_honest(at)      <- SUM over honest miners in ACTIVE_HASHING of modeled hash rate
    SET H_adversarial(at) <- SUM over adversarial miners in ACTIVE_HASHING of modeled hash rate
    SET H_active(at)      <- H_honest(at) + H_adversarial(at)             # I17 (may be 0 at applicability entry)
    IF H_active(at) = 0: SET q_adv(at) <- NA
    ELSE:                SET q_adv(at) <- H_adversarial(at) / H_active(at)
    # Q4: publish through the SOLE writer CommitSecurityCensus (source APPLICABILITY_ENTRY); it writes dirty +
    #     latest together atomically (J1).
    CALL CommitSecurityCensus(RoundContext, at,
          census_provenance = (RoundID_current, TemplateID_committed, state_version_current),
          H_active(at), H_honest(at), H_adversarial(at), q_adv(at),
          census_source = APPLICABILITY_ENTRY)                           # Q4: sole atomic writer
  RETURNS: applicability_census_captured(entered_state, at)
  NOTE: Q4/K7: a SOURCE (APPLICABILITY_ENTRY) of the sole writer CommitSecurityCensus (§0.8a).
        It is invoked on entry to HASHING (by CompleteAssignmentPhase, K2)
        and SOLUTION_PROPAGATION (by ScheduleSolutionPropagation), so a floor breach (e.g. H_active = 0) at
        applicability entry is decided by the epilogue even when no wake succeeds. It NEVER runs while the
        round is still ASSIGNMENT, so no breach is created in a non-applicable state (J6). Entry to
        SECURITY_RECOVERY needs NO separate capture: that entry is itself the RESULT of a
        SecurityFloorEvaluate on an already-coherent census at the SAME event_time (calling this there
        would re-dirty an event_time whose epilogue is mid-run — forbidden).

PROCEDURE FinalizeEventTimeSecurityCensus
  INPUTS: RoundContext, event_time
  PRECONDITIONS: an EVENT-TIME EPILOGUE (I-01/I-02), NOT a normal microphase event that could be missed
                 when no later event exists. It is driven by ProcessEventTime(event_time) AFTER the
                 event_time is QUIESCENT -- every ordinary and delta-cycle event at event_time has been
                 drained -- and runs EXACTLY ONCE per event_time.
  EFFECTS:
    # I-01: keyed by event_time ALONE (never by delta_cycle). If no ACTIVE_HASHING boundary occurred at
    #       this event_time, there is nothing to evaluate.
    IF NOT security_census_dirty[event_time]:
      RETURN no_census_change
    # J1 COHERENCE INVARIANT (asserted before reading): a set dirty flag ALWAYS has a coherent latest
    #    census, because CommitSecurityCensus (§0.8a/Q4) is the SOLE writer and writes both together atomically.
    ASSERT latest_security_census[event_time] EXISTS           # J1: dirty[t] = true  =>  latest[t] exists
    SET census <- latest_security_census[event_time]           # includes J8 provenance
    CALL SettleSecurityCensusDirty(RoundContext, event_time, PRIMARY_EPILOGUE)   # S5: the sole clearer (primary epilogue)
    # J8: pass the census's OWN stored provenance (the epoch it was PRODUCED under), NOT the current one,
    #     so a census produced under an earlier round/template cannot be re-interpreted in a new context.
    RETURN CALL SecurityFloorEvaluate(RoundContext,
                 event_RoundID       = census.RoundID_at_census,
                 event_TemplateID    = census.TemplateID_at_census,
                 event_state_version = census.state_version_at_census,
                 (census.H_active, census.H_honest, census.q_adv), floor_state)
  RETURNS: floor_result
  NOTE: I-01/I-02/J1/J8: the SOLE caller of SecurityFloorEvaluate, run once per QUIESCENT event_time. The
        dirty flag (keyed by event_time) can NEVER be stranded between delta-cycles and NEVER set without
        a coherent latest census; the census's stored provenance travels with it so the epilogue never
        mis-attributes an old-context census to a new round/template. Any recovery action that changes
        participation is scheduled at a STRICTLY LATER event_time (I-02).

PROCEDURE SecurityFloorEvaluate
  INPUTS: RoundContext,
          event_RoundID, event_TemplateID, event_state_version,     # J8: the census's OWN provenance
          (H_active(t), H_honest(t), q_adv(t)), floor_state
  PRECONDITIONS: invoked ONLY by FinalizeEventTimeSecurityCensus on a QUIESCENT event-time census
                 (I-01); never inline (G10); event_* is the epoch the census was PRODUCED under (J8)
  EFFECTS:
    # I-05: TERMINAL-FIRST. Return BEFORE any threshold evaluation or recording for a terminal round.
    IF round_state in {ROUND_ACCEPTED, ROUND_ABORTED}:
      RETURN terminal_stale_noop                               # no observation, no breach, no transition
    # J8 STALE-CENSUS-CONTEXT GUARD. The census carries the epoch it was produced under; if that epoch is
    #    no longer current, it belongs to a superseded round/template/state_version. Record a stale
    #    observation and NEVER evaluate thresholds or trigger recovery for the NEW round/template.
    IF event_RoundID != RoundID_current
       OR event_TemplateID != TemplateID_committed
       OR event_state_version != state_version_current:
      RECORD security_census_observation(stale_census, event_RoundID, event_TemplateID, event_state_version,
                                         H_active(t), H_honest(t), q_adv(t))     # J8: observation only
      RETURN stale_census_observation                          # no recovery in the new context
    # J6 APPLICABILITY BEFORE BREACH RECORDING. Thresholds are evaluated and I16 breach events recorded
    #    ONLY in HASHING / SOLUTION_PROPAGATION / SECURITY_RECOVERY. In setup/refresh/exhausted states
    #    record ONLY a census observation and return the matching observation-only result -- NO
    #    active-floor / honest-floor / adversarial-share breach event is ever recorded there.
    IF round_state NOT in {HASHING, SOLUTION_PROPAGATION, SECURITY_RECOVERY}:
      RECORD security_census_observation(round_state, H_active(t), H_honest(t), q_adv(t))   # J6: no breach
      RETURN (round_state = TEMPLATE_REFRESH ? refresh_observation_only  :
              round_state = ROUND_EXHAUSTED  ? exhausted_observation_only :
              setup_observation_only)          # ROUND_INITIALISING / TEMPLATE_COMMITMENT / ASSIGNMENT
    # ---- APPLICABLE states only (HASHING / SOLUTION_PROPAGATION / SECURITY_RECOVERY) ----
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
    # I-05: the ONLY permitted recovery transitions are HASHING -> SECURITY_RECOVERY and
    #       SOLUTION_PROPAGATION -> SECURITY_RECOVERY.
    IF breach AND round_state in {HASHING, SOLUTION_PROPAGATION}:
      # G8: SR PRESERVES any live propagation contexts; block arrivals/arbitration remain processable.
      TRANSITION round_state -> SECURITY_RECOVERY              # bumps state_version (G10)
      # O4: MINT the recovery episode for this entry (deterministic id, immutable).
      SET recovery_episode_seq <- recovery_episode_seq + 1
      SET episode <- (RoundID_current, recovery_episode_seq)
      SET current_recovery_episode <- episode
      SET recovery_deadline_reached[episode] <- false          # P3: the deadline has not elapsed yet
      # Q1: VERSION this entry census (the FIRST final recovery census of the episode).
      CALL CommitRecoveryCensus(RoundContext, episode, t, breach)   # Q1: recovery_census_seq++, publish latest_recovery_census
      # O3/P3: SEAT the NAMED deadline source. RecoveryDeadlineEvent (§9a) records ONLY the FACT that the
      #   deadline elapsed and refreshes the census — it does NOT select an outcome. If the deadline would fall
      #   beyond T, ScheduleEvent rejects it (O2) and CloseRoundAtHorizon (§20b) terminates the round at the horizon.
      SET r <- CALL ScheduleEvent(EQ, RoundContext, RecoveryDeadlineEvent,
                     target_event_time = min(t + recovery_deadline_window, run_horizon_T),
                     target_microphase = RECOVERY_DEADLINE,
                     {RecoveryEpisodeID = episode, RoundID_at_entry = RoundID_current,
                      TemplateID_at_entry = TemplateID_committed, state_version_at_entry = state_version_current})
      IF r != scheduled(...):
        RECORD recovery_deadline_not_seated(episode, r)        # O2: e.g. past-horizon; horizon-close governs
      RETURN breach
    ELSE IF round_state = SECURITY_RECOVERY:
      # Q1: VERSION every FINAL recovery census while in recovery, and RECONCILE pending decisions against it —
      #   supersede a decision the new census CONTRADICTS (even when the new census produces no completion), and
      #   re-affirm a still-consistent decision to the newest version. Freshness is judged against EVERY final
      #   census, not merely against the existence of a newer RecoveryDecisionID.
      SET episode <- current_recovery_episode
      IF breach: RECORD_ONCE breach_persists(t)               # I16 persistence record; NO self-transition (I-05)
      CALL CommitRecoveryCensus(RoundContext, episode, t, breach)             # Q1: version + publish latest_recovery_census
      CALL ReconcilePendingRecoveryDecisions(RoundContext, episode)          # Q1/Q3: supersede/cancel or re-affirm
      SET census <- latest_recovery_census[episode]
      # V1: RECONCILE any in-flight recovery WORK against THIS final census BEFORE considering SeatRecoveryWork — so a
      #   DUE work record whose census version moved (v1 -> v2) is REBOUND to v2 (same RecoveryWorkID) and can be
      #   consumed by ApplyRecoveryWorkAfterEpilogue, instead of being replaced by a second work record that would
      #   strand the DUE one and fail the finalisation assertion.
      CALL ReconcilePendingRecoveryWork(RoundContext, episode, census.RecoveryCensusVersion, t)   # V1
      # Determine the warranted outcome from the FINAL census (P3): restored -> RESTORED; breach WITH the deadline
      #   reached -> UNRECOVERABLE; breach BEFORE the deadline -> NONE (keep waiting; round stays SECURITY_RECOVERY).
      IF NOT census.breach:                              SET warranted <- RESTORED
      ELSE IF census.breach AND census.deadline_reached: SET warranted <- UNRECOVERABLE
      ELSE:                                              SET warranted <- NONE
      IF warranted = NONE:
        # U1: a breach BEFORE the deadline is NOT a RecoveryOutcome. It is the trigger to attempt recovery WORK.
        #   outcome_consistent_with_census(RESTORED) is NOT weakened (a breached census can never justify RESTORED).
        #   V1: SeatRecoveryWork does NOT replace a DUE work record at THIS event_time (Reconcile already rebound it);
        #   it only seats FRESH work when there is no live in-flight work. The round stays SECURITY_RECOVERY; a LATER
        #   no-breach final census mints RESTORED. Recovery WORK is NEVER an outcome and NEVER APPLIED.
        SET work_action <- CALL ClassifyRecoveryWork(RoundContext, episode, census)   # U1/V6: SECURITY_FLOOR_RECOVERY_WORK only
        IF work_action != NONE:
          RETURN CALL SeatRecoveryWork(RoundContext, episode, work_action, t, census.RecoveryCensusVersion)   # U1/U3/V1
        RETURN recovery_pending(census.RecoveryCensusVersion)                 # no work available; keep waiting (breach before deadline)
      # Seat a completion for the warranted outcome (SeatRecoveryCompletion; the ACTUAL application is deferred
      #   to ApplyRecoveryCompletionAfterEpilogue at the completion event_time, Q2).
      RETURN CALL SeatRecoveryCompletion(RoundContext, episode, warranted, t, census.RecoveryCensusVersion)   # P4/P5/Q2/Q3/Q7
    RETURN no_breach
  RETURNS: breach | breach_persists | recovery_pending | recovery_completion_seated | recovery_completion_not_seated |
           recovery_completion_already_pending | recovery_completion_horizon_deferred |
           recovery_completion_already_finalised | recovery_work_seated | recovery_work_already_pending |
           recovery_work_not_seated | recovery_work_horizon_deferred | no_breach | refresh_observation_only |
           exhausted_observation_only | setup_observation_only | stale_census_observation | terminal_stale_noop
  NOTE: J6/J8/I-05: round-state applicability is checked BEFORE any threshold evaluation. Terminal rounds return
        terminal_stale_noop first; setup/refresh/exhausted states record only an observation; a stale-context
        census never triggers recovery. Recovery is entered only from HASHING/SOLUTION_PROPAGATION. Q1: while in
        SECURITY_RECOVERY, the epilogue VERSIONS every final recovery census (CommitRecoveryCensus) and
        RECONCILES pending decisions (ReconcilePendingRecoveryDecisions) — a newer census supersedes a
        contradicted decision (even if it produces no completion) and re-affirms a still-consistent one. P3: the
        outcome is chosen from the FINAL census (restored -> RESTORED; breach + deadline -> UNRECOVERABLE; breach
        before deadline -> keep waiting), so a same-timestamp WakeCompleteEvent that restores the floor is visible
        first. Q2: SeatRecoveryCompletion seats a RecoveryCompletionDueEvent; the actual transition/abort happens
        only in ApplyRecoveryCompletionAfterEpilogue AFTER the completion event_time's own final census is known.
        I17 holds at every boundary; entering SECURITY_RECOVERY does NOT cancel live candidates (G8).

FUNCTION outcome_consistent_with_census(outcome, census)        # Q1: does a FINAL recovery census still justify an outcome?
  # RESTORED is consistent with a census that shows NO breach; UNRECOVERABLE is consistent with a census that
  # shows a breach AND the deadline reached. Any other combination CONTRADICTS the outcome.
  IF outcome = RESTORED:      RETURN (census.breach = false)
  IF outcome = UNRECOVERABLE: RETURN (census.breach = true AND census.deadline_reached = true)
  RETURN false

PROCEDURE SetRecoveryDecisionStatus                             # R6: the SOLE mutator of a decision's status; keeps latest_recovery_decision consistent
  INPUTS: RoundContext, decision_id, new_status   # new_status in RECOVERY_DECISION_STATUS
  PRECONDITIONS: recovery_decisions[decision_id] EXISTS; (CREATED is set only at creation in SeatRecoveryCompletion,
                 which also creates the mirror — every SUBSEQUENT status transition goes through THIS procedure)
  EFFECTS:
    SET recovery_decisions[decision_id].status <- new_status
    SET episode <- recovery_decisions[decision_id].episode
    # R6: if this decision IS the episode's latest mirror, REFRESH the whole mirror record from recovery_decisions,
    #     so the mirror can NEVER lag the underlying decision — it can never remain CREATED (or any stale status)
    #     after the decision became SCHEDULED / SUPERSEDED / APPLYING / APPLIED / SCHEDULE_FAILED / APPLY_FAILED /
    #     CANCELLED (R6).
    IF latest_recovery_decision[episode] EXISTS AND latest_recovery_decision[episode].decision_id = decision_id:
      SET latest_recovery_decision[episode] <- { decision_id = decision_id,
            outcome = recovery_decisions[decision_id].outcome,
            bound_census_version = recovery_decisions[decision_id].bound_census_version,
            status = new_status }
  RETURNS: recovery_decision_status_set(decision_id, new_status)
  NOTE: R6: the ONE place a RECOVERY_DECISION_STATUS transition is written (after the initial CREATED in
        SeatRecoveryCompletion). Because it refreshes latest_recovery_decision whenever that mirror points at
        decision_id, the mirror is ALWAYS consistent with the underlying decision — no latest-decision record can
        remain CREATED after the decision became CANCELLED or SCHEDULE_FAILED (or any other terminal/transient status).

PROCEDURE CancelActiveRecoveryEpisode                           # S4: terminal cleanup of an UNFINISHED recovery episode
  INPUTS: RoundContext, dispatch_envelope
  PRECONDITIONS: called ONLY by CloseRoundAssignments (§17a) when the round is closing
                 (ROUND_ACCEPTED/ROUND_ABORTED) AND current_recovery_episode != null AND the closure is NOT the
                 recovery-FINALISING abort (recovery_finalising = false). NO outcome is being applied here.
  EFFECTS:
    SET episode <- current_recovery_episode
    # S4: cancel EVERY pending / scheduled / APPLYING recovery decision of the episode, and cancel its queued
    #     RecoveryCompletionDueEvent (due_event_ref) and RecoveryAssignmentContinuationDueEvent (continuation_event_ref).
    FOR EACH decision_id in pending_recovery_decisions[episode] (stable order by decision_id):
      SET D <- recovery_decisions[decision_id]
      IF D.due_event_ref != null AND D.due_event_ref is still pending on EQ:
        CANCEL D.due_event_ref on EQ                            # cancel the queued RecoveryCompletionDueEvent
      IF D.continuation_event_ref != null AND D.continuation_event_ref is still pending on EQ:
        CANCEL D.continuation_event_ref on EQ                   # S3/S4/T1: cancel the queued RecoveryAssignmentContinuationDueEvent
      IF D.continuation_due_status = DUE: SET recovery_decisions[decision_id].continuation_due_status <- CANCELLED   # U4: explicit terminal consumption
      CALL SetRecoveryDecisionStatus(RoundContext, decision_id, CANCELLED)   # S4/R6: cancel + keep the mirror consistent
    SET pending_recovery_decisions[episode] <- empty set
    # V7: cancel EVERY NONTERMINAL recovery-WORK record of the episode — NOT only the one currently referenced by
    #   pending_recovery_work — so no orphan ARMED/DUE/APPLYING work record survives terminal closure.
    FOR EACH work_id in recovery_work WHERE recovery_work[work_id].episode = episode
             AND recovery_work[work_id].status in {CREATED, ARMED, DUE, APPLYING} (stable order by work_id):
      SET W <- recovery_work[work_id]
      IF W.work_due_event_ref != null AND W.work_due_event_ref is still pending on EQ:
        CANCEL W.work_due_event_ref on EQ                       # V7: cancel the queued RecoveryWorkDueEvent
      SET recovery_work[work_id].status <- CANCELLED
      IF W.due_status = DUE: SET recovery_work[work_id].due_status <- CANCELLED   # U4/V7: explicit terminal consumption
    SET pending_recovery_work[episode] <- null                  # V7: no live in-flight work remains
    # S4: record the episode disposition and CLEAR the active episode. Do NOT set recovery_outcome_finalised —
    #     no outcome was applied here (that is reserved for an actually-applied RESTORED/UNRECOVERABLE).
    SET recovery_episode_disposition[episode] <- TERMINAL_CANCELLED
    SET current_recovery_episode <- null
  RETURNS: recovery_episode_terminal_cancelled(episode)
  NOTE: S4: the terminal cleanup for an UNFINISHED recovery episode. Invoked by the single closure path
        CloseRoundAssignments (§17a) for EVERY terminal closure EXCEPT the recovery-finalising RoundAbort (branch D,
        or the continuation's declared install-fail abort), which finalise the episode themselves. It cancels the
        episode's pending/applying decisions and their queued RecoveryCompletionDueEvent /
        RecoveryAssignmentContinuationDueEvent, records TERMINAL_CANCELLED, and clears current_recovery_episode — so a
        terminal round NEVER leaves an active recovery episode (S4 invariant). recovery_outcome_finalised is NOT set.

PROCEDURE CommitRecoveryCensus                                  # Q1: VERSION + publish the FINAL recovery census
  INPUTS: RoundContext, episode, event_time, breach
  PRECONDITIONS: called by the epilogue (SecurityFloorEvaluate) while round_state = SECURITY_RECOVERY, on the
                 FINAL event-time census; the security census maps are already committed by CommitSecurityCensus (Q4)
  EFFECTS:
    SET recovery_census_seq <- recovery_census_seq + 1          # Q1: monotonic RecoveryCensusVersion
    SET c <- latest_security_census[event_time]                 # the FINAL committed security census (Q4)
    SET latest_recovery_census[episode] <- recovery_census_record(
          RecoveryEpisodeID = episode, RecoveryCensusVersion = recovery_census_seq, event_time = event_time,
          RoundID = c.RoundID_at_census, TemplateID = c.TemplateID_at_census, state_version = c.state_version_at_census,
          H_active = c.H_active, H_honest = c.H_honest, H_adversarial = c.H_adversarial, q_adv = c.q_adv,
          breach = breach, deadline_reached = recovery_deadline_reached[episode])
  RETURNS: recovery_census_versioned(episode, recovery_census_seq)
  NOTE: Q1: EVERY final recovery census receives a monotonic version. A pending decision binds to a
        RecoveryCensusVersion; ReconcilePendingRecoveryDecisions then supersedes or re-affirms it against THIS census.

PROCEDURE ReconcilePendingRecoveryDecisions                     # Q1/Q3: supersede-or-re-affirm pending decisions atomically
  INPUTS: RoundContext, episode
  PRECONDITIONS: latest_recovery_census[episode] just published by CommitRecoveryCensus
  EFFECTS:
    SET census <- latest_recovery_census[episode]
    FOR EACH decision_id in pending_recovery_decisions[episode] (stable order):
      SET D <- recovery_decisions[decision_id]
      IF NOT outcome_consistent_with_census(D.outcome, census):
        # Q1/Q3: the newer FINAL census CONTRADICTS this pending decision -> SUPERSEDE it IMMEDIATELY, BEFORE any
        #        attempt to seat a replacement. Cancel its due event when the queue still holds it.
        CALL SetRecoveryDecisionStatus(RoundContext, decision_id, SUPERSEDED)   # Q1/Q3/R6: supersede + keep the mirror consistent
        IF D.due_event_ref != null AND D.due_event_ref is still pending on EQ:
          CANCEL D.due_event_ref on EQ                          # Q3: cancel the pending due event when possible (same CANCEL idiom as G8/M3)
        IF D.continuation_event_ref != null AND D.continuation_event_ref is still pending on EQ:
          CANCEL D.continuation_event_ref on EQ                 # S3/T1: cancel a superseded DEFERRED branch-C continuation Due event (it would stale-noop anyway)
        REMOVE decision_id from pending_recovery_decisions[episode]
      ELSE:
        # still consistent with the FINAL census -> RE-AFFIRM to the newest version (its justification is current)
        SET recovery_decisions[decision_id].bound_census_version <- census.RecoveryCensusVersion
        # T2 rule B: keep the AUTHORITATIVE continuation bound version CURRENT too, so a re-affirmed DEFERRED branch-C
        #   decision's continuation applies against the LATEST final census (its immutable due event carries only the
        #   generation, never a stale version). A superseded decision's continuation was cancelled above.
        IF recovery_decisions[decision_id].continuation_id != null:
          SET recovery_decisions[decision_id].continuation_bound_census_version <- census.RecoveryCensusVersion   # T2
        IF latest_recovery_decision[episode] EXISTS AND latest_recovery_decision[episode].decision_id = decision_id:
          SET latest_recovery_decision[episode].bound_census_version <- census.RecoveryCensusVersion   # R6: mirror follows the re-affirm
  RETURNS: pending_decisions_reconciled(episode, census.RecoveryCensusVersion)
  NOTE: Q1/Q3: after this runs, NO pending decision retains an older census version — each is either SUPERSEDED
        (and removed from pending_recovery_decisions) or re-affirmed to the latest RecoveryCensusVersion. A
        superseded decision NEVER becomes valid again (its status is terminal-negative), so a failed superseding
        schedule can never revive it.

PROCEDURE ReconcilePendingRecoveryWork                          # V1: reconcile in-flight recovery WORK against the newest final census BEFORE seating new work
  INPUTS: RoundContext, episode, latest_census_version, event_time   # latest_census_version = census.RecoveryCensusVersion just published
  PRECONDITIONS: called by SecurityFloorEvaluate AFTER CommitRecoveryCensus + ReconcilePendingRecoveryDecisions and
                 BEFORE it considers SeatRecoveryWork; round_state = SECURITY_RECOVERY; episode = current_recovery_episode
  EFFECTS:
    IF pending_recovery_work[episode] = null: RETURN no_pending_recovery_work(episode)
    SET W <- recovery_work[pending_recovery_work[episode]]
    SET census <- latest_recovery_census[episode]
    SET still_warranted <- (census.breach = true AND census.deadline_reached = false
                            AND CALL ClassifyRecoveryWork(RoundContext, episode, census) != NONE)   # V6: still a security-floor breach before deadline
    # (1) V1: the ACTIVE work is DUE at THIS event_time and still warranted -> REBIND it to the latest version, keep the
    #     SAME RecoveryWorkID, do NOT seat replacement work, and let ApplyRecoveryWorkAfterEpilogue CONSUME it.
    IF W.due_status = DUE AND W.due_at_event_time = event_time:
      IF still_warranted:
        SET recovery_work[W.work_id].bound_census_version <- latest_census_version   # V1: rebind (same WorkID) so the DUE record is consumable
        RETURN recovery_work_reconciled_rebound(W.work_id, latest_census_version)
      # (2) no longer warranted -> SUPERSEDE the DUE record and let the outcome path govern.
      SET recovery_work[W.work_id].status <- SUPERSEDED ; SET recovery_work[W.work_id].due_status <- SUPERSEDED   # V1/V7
      IF W.work_due_event_ref != null AND W.work_due_event_ref is still pending on EQ: CANCEL W.work_due_event_ref on EQ
      SET pending_recovery_work[episode] <- null
      RETURN recovery_work_reconciled_superseded(W.work_id)
    # (3) the work is ARMED for a FUTURE event (not due at THIS event_time). POLICY: RE-AFFIRM the SAME work identity to
    #     the latest census when still warranted; otherwise atomically SUPERSEDE + cancel it. NEVER leave two live in-flight.
    IF W.status = ARMED:
      IF still_warranted:
        SET recovery_work[W.work_id].bound_census_version <- latest_census_version   # V1: re-affirm the same ARMED identity
        RETURN recovery_work_reconciled_reaffirmed(W.work_id, latest_census_version)
      SET recovery_work[W.work_id].status <- SUPERSEDED ; SET recovery_work[W.work_id].due_status <- SUPERSEDED   # V1/V7
      IF W.work_due_event_ref != null AND W.work_due_event_ref is still pending on EQ: CANCEL W.work_due_event_ref on EQ
      SET pending_recovery_work[episode] <- null
      RETURN recovery_work_reconciled_superseded(W.work_id)
    RETURN recovery_work_reconciled_noop(W.work_id)
  RETURNS: recovery_work_reconciled_rebound | recovery_work_reconciled_reaffirmed | recovery_work_reconciled_superseded |
           recovery_work_reconciled_noop | no_pending_recovery_work
  NOTE: V1: closes the invalid due-time sequence where a DUE work W1 (bound to v1) is orphaned by a newer census v2 and
        replaced by a second work W2, leaving W1 DUE and failing the ProcessEventTime finalisation assertion. It REBINDS a
        still-warranted DUE record to the latest version (same RecoveryWorkID, no replacement) so the post-epilogue hook
        can consume it; SUPERSEDES a no-longer-warranted record; and re-affirms or supersedes an ARMED future record —
        NEVER leaving two live in-flight work records. SecurityFloorEvaluate calls it before it considers SeatRecoveryWork.

PROCEDURE SeatRecoveryCompletion                                # P4/P5/Q2/Q3/Q7: seat a RecoveryCompletionDueEvent
  INPUTS: RoundContext, episode, outcome, t, census_version   # outcome in {RESTORED, UNRECOVERABLE}; census_version = current RecoveryCensusVersion
  PRECONDITIONS: called by the epilogue AFTER CommitRecoveryCensus + ReconcilePendingRecoveryDecisions;
                 round_state = SECURITY_RECOVERY; episode = current_recovery_episode
  EFFECTS:
    # O4 apply-once: if the episode's outcome is already finalised, there is nothing to seat.
    IF recovery_outcome_finalised[episode] is set:
      RETURN recovery_completion_already_finalised
    # P5/Q3 no redundant re-seat: a still-valid pending decision with the SAME outcome bound to the CURRENT census
    #   version will apply — do not re-seat. (A contradicted decision was already SUPERSEDED + removed by Reconcile.)
    IF EXISTS decision_id in pending_recovery_decisions[episode] WITH
       recovery_decisions[decision_id].outcome = outcome AND
       recovery_decisions[decision_id].bound_census_version = census_version:
      RETURN recovery_completion_already_pending(outcome)
    # P5: MINT a fresh, versioned decision id (deterministic).
    SET recovery_decision_seq <- recovery_decision_seq + 1
    SET decision_id <- (episode, recovery_decision_seq)         # RecoveryDecisionID
    # Q7: DETERMINISTIC completion time. configured_recovery_completion_delay > 0 (or the next-representable instant).
    SET target_time <- t + configured_recovery_completion_delay
    # Q3: create the decision record (status CREATED, bound to the current census version) BEFORE scheduling.
    SET recovery_decisions[decision_id] <- decision_record(
          episode = episode, outcome = outcome, bound_census_version = census_version,
          status = CREATED, target_time = target_time, due_event_ref = null, due_at_event_time = null)
    SET latest_recovery_decision[episode] <- { decision_id, outcome, bound_census_version = census_version, status = CREATED }
    # Q7/O2 HORIZON: never seat a completion beyond T. Record horizon_deferred; a superseded decision stays invalid;
    #   CloseRoundAtHorizon (§20b) governs run end.
    IF target_time > run_horizon_T:
      CALL SetRecoveryDecisionStatus(RoundContext, decision_id, CANCELLED)   # Q7/O2/R6: cancel + REFRESH mirror (never leaves it CREATED)
      RECORD horizon_deferred(decision_id, target_time)
      RETURN recovery_completion_horizon_deferred(decision_id)
    # P4: schedule the RecoveryCompletionDueEvent; add to pending set ONLY on scheduler SUCCESS.
    SET result <- CALL ScheduleEvent(EQ, RoundContext, RecoveryCompletionDueEvent,
                     target_event_time = target_time, target_microphase = RECOVERY_COMPLETION_DUE,
                     {RecoveryEpisodeID = episode, RecoveryDecisionID = decision_id, RecoveryOutcome = outcome,
                      RecoveryCensusVersion = census_version,
                      RoundID_at_decision = RoundID_current, TemplateID_at_decision = TemplateID_committed,
                      state_version_at_decision = state_version_current})   # Q2/Q7 (deterministic target_time)
    IF result = scheduled(...):
      SET recovery_decisions[decision_id].due_event_ref <- result.event_ref
      CALL SetRecoveryDecisionStatus(RoundContext, decision_id, SCHEDULED)   # P4/R6: SCHEDULED + REFRESH mirror
      ADD decision_id to pending_recovery_decisions[episode]                # P4/Q3: added ONLY after success
      RETURN recovery_completion_seated(decision_id, outcome)
    ELSE:
      # P4/Q3: leave it OUT of pending_recovery_decisions; mark SCHEDULE_FAILED; record disposition. A failed
      #        superseding schedule can NEVER revive an earlier SUPERSEDED decision (that decision was already
      #        removed by Reconcile and its status is terminal-negative). Round stays SECURITY_RECOVERY.
      CALL SetRecoveryDecisionStatus(RoundContext, decision_id, SCHEDULE_FAILED)   # P4/R6: SCHEDULE_FAILED + REFRESH mirror (never leaves it CREATED)
      RECORD recovery_completion_schedule_rejected(episode, decision_id, result)
      RETURN recovery_completion_not_seated(result)
  RETURNS: recovery_completion_seated | recovery_completion_not_seated | recovery_completion_already_pending |
           recovery_completion_already_finalised | recovery_completion_horizon_deferred
  NOTE: P4/P5/Q2/Q3/Q7: the SOLE seater. It seats a RecoveryCompletionDueEvent (Q2 step 1), NOT a direct
        application; the decision record's status moves CREATED -> SCHEDULED (on scheduler success) or ->
        SCHEDULE_FAILED / CANCELLED (horizon_deferred). pending_recovery_decisions is updated ONLY on success
        (P4). The completion time is deterministic (Q7). The actual transition/abort is performed later by
        ApplyRecoveryCompletionAfterEpilogue (§10a), never here.

PROCEDURE RecoveryDeadlineEvent                                  # O3/P3/§9a: records the deadline FACT (no outcome)
  INPUTS: RoundContext, dispatch_envelope, RecoveryEpisodeID, RoundID_at_entry, TemplateID_at_entry,
          state_version_at_entry   # carried by the event seated on entry to SECURITY_RECOVERY (§9 breach branch)
  PRECONDITIONS: a dispatched queued handler (seated through ScheduleEvent at RECOVERY_DEADLINE); its
                 dispatch_envelope is its own (§0.7f)
  EFFECTS:
    # O3/O4 STALE GUARD. The deadline is meaningful ONLY if the round is STILL in recovery, on the SAME
    #   episode and epoch, and no completion has been finalised. Otherwise it is a deterministic no-op.
    IF round_state != SECURITY_RECOVERY
       OR RecoveryEpisodeID != current_recovery_episode
       OR recovery_outcome_finalised[RecoveryEpisodeID] is set
       OR RoundID_at_entry != RoundID_current OR TemplateID_at_entry != TemplateID_committed
       OR state_version_at_entry != state_version_current:
      RETURN recovery_deadline_stale_noop
    # P3: RECORD THE FACT ONLY. The deadline does NOT select an outcome and does NOT seat a completion. It must
    #   NEVER assume that remaining in SECURITY_RECOVERY means the floor is still breached — a same-timestamp
    #   WakeCompleteEvent may restore the floor. The OUTCOME is chosen by the event-time epilogue from the FINAL
    #   census AFTER all same-time ordinary events and delta-cycles complete.
    SET recovery_deadline_reached[RecoveryEpisodeID] <- true
    # P3: create a COHERENT census for THIS event_time so the epilogue has something to decide from even if no
    #   miner boundary occurred at the deadline timestamp. Publishes latest_security_census + security_census_dirty
    #   TOGETHER atomically via the sole writer CommitSecurityCensus (source RECOVERY_DEADLINE, R5).
    CALL CaptureSecurityCensusOnRecoveryDeadline(RoundContext, dispatch_envelope.event_time,
                                                 census_source = RECOVERY_DEADLINE)   # R5: deadline-fact provenance
    RETURN recovery_deadline_recorded(RecoveryEpisodeID)
  RETURNS: recovery_deadline_recorded | recovery_deadline_stale_noop
  NOTE: O3/P3: the deadline is a FACT, not a pre-epilogue outcome. It records recovery_deadline_reached and
        dirties the census; it NEVER selects UNRECOVERABLE and NEVER seats a completion. The event-time epilogue
        (SecurityFloorEvaluate) decides from the FINAL timestamp census — breach persists WITH the deadline
        reached -> UNRECOVERABLE, floor restored -> RESTORED — so a same-timestamp floor restoration is visible
        before the deadline outcome is chosen. The seating (if any) happens through the SOLE seater
        SeatRecoveryCompletion (§9), not here.

PROCEDURE CaptureSecurityCensusOnRecoveryDeadline                # P3: coherent census producer at a recovery-timeline checkpoint
  INPUTS: RoundContext, at,   # at = the event_time (dispatch_envelope.event_time of the recovery-timeline checkpoint event)
          census_source = RECOVERY_DEADLINE   # R5/U7/U1: RECOVERY_DEADLINE (RecoveryDeadlineEvent, §9a),
                                              #   RECOVERY_COMPLETION_DUE (RecoveryCompletionDueEvent, §10a),
                                              #   RECOVERY_CONTINUATION_DUE (RecoveryAssignmentContinuationDueEvent, §10a, U7), or
                                              #   RECOVERY_WORK_DUE (RecoveryWorkDueEvent, §9c, U1)
  PRECONDITIONS: called by one of the FOUR recovery-timeline census checkpoints — RecoveryDeadlineEvent
                 (§9a, RECOVERY_DEADLINE), RecoveryCompletionDueEvent (§10a, RECOVERY_COMPLETION_DUE),
                 RecoveryAssignmentContinuationDueEvent (§10a, RECOVERY_CONTINUATION_DUE, U7), or RecoveryWorkDueEvent
                 (§9c, RECOVERY_WORK_DUE, U1); round_state = SECURITY_RECOVERY (a floor-applicable state)
  EFFECTS:
    # Compute the census NOW from the ACTIVE_HASHING roster (like CaptureSecurityCensusOnApplicabilityEntry, K7)
    # and publish via the sole writer CommitSecurityCensus (Q4), so the epilogue decides once from the FINAL
    # census at `at`. A later same-`at` MINER_STATE_TRANSITION commit (e.g. a WakeCompleteEvent that restores the
    # floor) OVERWRITES latest_security_census[at] with the newer census, so the epilogue reads the FINAL value.
    SET H_honest(at)      <- SUM over honest miners in ACTIVE_HASHING of modeled hash rate
    SET H_adversarial(at) <- SUM over adversarial miners in ACTIVE_HASHING of modeled hash rate
    SET H_active(at)      <- H_honest(at) + H_adversarial(at)             # I17
    IF H_active(at) = 0: SET q_adv(at) <- NA
    ELSE:                SET q_adv(at) <- H_adversarial(at) / H_active(at)
    # Q4/R5: publish through the SOLE writer CommitSecurityCensus with the caller's census_source (RECOVERY_DEADLINE
    #     or RECOVERY_COMPLETION_DUE); it writes dirty + latest together atomically (J1). A later same-`at`
    #     MINER_STATE_TRANSITION commit OVERWRITES it, so the epilogue reads the FINAL census at `at` (P3/gate 6).
    CALL CommitSecurityCensus(RoundContext, at,
          census_provenance = (RoundID_current, TemplateID_committed, state_version_current),
          H_active(at), H_honest(at), H_adversarial(at), q_adv(at),
          census_source = census_source)                               # Q4/R5: sole atomic writer; provenance-distinct source
    RETURN recovery_deadline_census_captured(at)
  NOTE: Q4/P3/R5/U7/U1: a SOURCE of the sole writer CommitSecurityCensus (§0.8a), carrying census_source
        RECOVERY_DEADLINE, RECOVERY_COMPLETION_DUE, RECOVERY_CONTINUATION_DUE (U7), or RECOVERY_WORK_DUE (U1), so the
        FOUR recovery-timeline checkpoints have DISTINCT census provenance. It guarantees the checkpoint timestamp has
        a census for the epilogue to decide from, WITHOUT itself selecting an outcome; a same-timestamp
        MINER_STATE_TRANSITION commit still overwrites it, so the epilogue sees the FINAL census.
```

## 9c. Recovery WORK — reserve activation / redistribution while the floor is still breached (U1/U3/U4/U5)

```
FUNCTION ClassifyRecoveryWork                                    # U1/V6: compute-only — which SECURITY-FLOOR recovery WORK (if any) to attempt
  INPUTS: RoundContext, episode, census   # census = latest_recovery_census[episode] (breach = true, deadline not reached)
  PRECONDITIONS: round_state = SECURITY_RECOVERY; census.breach = true AND census.deadline_reached = false (breach
                 BEFORE the deadline). It selects a SECURITY_FLOOR_RECOVERY_WORK action (V6: one that can CHANGE the
                 ACTIVE_HASHING census), NEVER a RecoveryOutcome and NEVER a coverage-only repair. It is compute-only.
  EFFECTS:
    # V6: ONLY an action that can actually change H_active / H_honest / q_adv is SECURITY_FLOOR_RECOVERY_WORK. A
    #   redistribution AMONG THE SAME ACTIVE_HASHING miners cannot alter H_active/H_honest/q_adv (the census sums over the
    #   SAME active set), so it CANNOT repair the currently defined security-floor breach and is NOT returned here — it is
    #   COVERAGE_REPAIR_WORK (§0.8), which does not control the breach-before-deadline outcome logic. RANGE_REDISTRIBUTION_
    #   REQUIRED is therefore REMOVED from security-floor recovery.
    IF there is at least one miner in RESERVE that can be activated to add honest hash rate toward the deficit:
      RETURN RESERVE_ACTIVATION_REQUIRED           # V6: reserve activation CHANGES the ACTIVE_HASHING census (adds an active miner)
    IF a DECLARED honest/adversarial participation replacement can change the ACTIVE_HASHING census toward the floor:
      RETURN RESERVE_ACTIVATION_REQUIRED           # V6: a census-changing participation replacement is the same work class
    RETURN NONE                                    # no census-changing security-floor work is available (keep waiting)
  RETURNS: RECOVERY_WORK_ACTION in { RESERVE_ACTIVATION_REQUIRED, NONE }   # V6: no coverage-only action here
  NOTE: U1/V6: SECURITY-FLOOR recovery WORK is ONLY an action that can CHANGE the ACTIVE_HASHING census (reserve
        activation / a declared participation replacement). A same-active-miner range redistribution cannot change
        H_active/H_honest/q_adv, so it can never repair a security-floor breach and is classified as COVERAGE_REPAIR_WORK
        (§0.8) — NOT returned here and NOT controlling the breach-before-deadline outcome logic. A redistribution AFTER a
        no-breach census remains the branch-C redistribution-only continuation (§10a), never a breach-repairing action.

PROCEDURE SeatRecoveryWork                                       # U1/U3: seat ONE versioned RecoveryWorkDueEvent (atomic, idempotent)
  INPUTS: RoundContext, episode, work_action, t, census_version   # V6: work_action = RESERVE_ACTIVATION_REQUIRED (SECURITY_FLOOR_RECOVERY_WORK
                                                                  #   only — the sole ClassifyRecoveryWork result other than NONE). SeatRecoveryWork
                                                                  #   is called ONLY from the security-floor breach-before-deadline path, so it never
                                                                  #   seats a COVERAGE_REPAIR_WORK redistribution (that is the branch-C continuation, §10a).
  PRECONDITIONS: called by the epilogue (SecurityFloorEvaluate) in the breach-before-deadline branch;
                 round_state = SECURITY_RECOVERY; episode = current_recovery_episode
  EFFECTS:
    # O4 apply-once: no work once an outcome is finalised.
    IF recovery_outcome_finalised[episode] is set:
      RETURN recovery_work_already_pending(NONE)          # nothing to seat (episode already finalised)
    # V1/V7 at most ONE in-flight recovery-work action per episode ({ARMED, DUE, APPLYING}).
    IF pending_recovery_work[episode] != null:
      SET W0 <- recovery_work[pending_recovery_work[episode]]
      # V1: NEVER replace a DUE work record at the CURRENT event_time. If W0 is DUE at t, ReconcilePendingRecoveryWork
      #   already rebound it (if warranted) or superseded it — SeatRecoveryWork must not seat a second record over it.
      IF W0.status = DUE AND W0.due_at_event_time = t:
        RETURN recovery_work_already_pending(W0.action)   # V1: do not replace a DUE record at the current event_time
      IF W0.status in {ARMED, DUE, APPLYING} AND W0.bound_census_version = census_version:
        RETURN recovery_work_already_pending(W0.action)   # V7: one live in-flight, still current -> do not re-seat
      # V7: a STALE prior in-flight record exists (older version, not DUE-at-t). ATOMICALLY SUPERSEDE/CANCEL it and
      #   consume its due fact BEFORE publishing the replacement, so two live in-flight work records NEVER coexist.
      SET recovery_work[W0.work_id].status <- SUPERSEDED
      IF W0.due_status = DUE: SET recovery_work[W0.work_id].due_status <- SUPERSEDED   # V7: consume the stale due fact
      IF W0.work_due_event_ref != null AND W0.work_due_event_ref is still pending on EQ: CANCEL W0.work_due_event_ref on EQ
      SET pending_recovery_work[episode] <- null
    # U3/V7 ATOMIC SEAT. Compute identity + target BEFORE mutating; publish the active work identity ONLY after
    #   ScheduleEvent succeeds (the prior stale record was already superseded/cancelled above). Never advance the work
    #   seq / publish a ref on a rejected enqueue.
    SET candidate_seq <- recovery_work_seq + 1
    SET work_id <- (episode, candidate_seq)                # RecoveryWorkID
    SET t_due <- t + configured_recovery_completion_delay  # Q7-style deterministic delay (> 0)
    IF t_due > run_horizon_T:                              # O2 horizon: never seat beyond T
      RECORD recovery_work_horizon_deferred(episode, t_due)
      RETURN recovery_work_horizon_deferred(episode)       # keep SECURITY_RECOVERY; CloseRoundAtHorizon governs
    SET result <- CALL ScheduleEvent(EQ, RoundContext, RecoveryWorkDueEvent,
                     target_event_time = t_due, target_microphase = RECOVERY_WORK_DUE,
                     {RecoveryEpisodeID = episode, RecoveryWorkID = work_id, WorkGeneration = 1,
                      RecoveryWorkAction = work_action, RecoveryCensusVersion = census_version,
                      RoundID_at_work = RoundID_current, TemplateID_at_work = TemplateID_committed,
                      state_version_at_work = state_version_current})   # U1/U3
    IF result = scheduled(...):
      # U3 PUBLISH only after success.
      SET recovery_work_seq <- candidate_seq
      SET recovery_work[work_id] <- work_record(episode = episode, action = work_action,
            bound_census_version = census_version, work_generation = 1, work_id = work_id, status = ARMED,
            work_due_event_ref = result.event_ref, due_at_event_time = null, due_dispatch_envelope = null,
            due_status = NOT_DUE)
      SET pending_recovery_work[episode] <- work_id
      RETURN recovery_work_seated(work_id, work_action)
    # U3 REJECTED: do NOT advance recovery_work_seq, do NOT publish a ref, do NOT report pending. Round stays SECURITY_RECOVERY.
    RECORD recovery_work_schedule_rejected(episode, candidate_seq, result)
    RETURN recovery_work_not_seated(result)
  RETURNS: recovery_work_seated | recovery_work_not_seated | recovery_work_already_pending | recovery_work_horizon_deferred
  NOTE: U1/U3: the SOLE seater / re-arm of a recovery-WORK action, implementing the U3 ATOMIC protocol — it computes a
        candidate identity (candidate_seq / work_id) and target t_due, validates t_due <= T (else recovery_work_horizon_deferred
        — no event enqueued), calls ScheduleEvent WITHOUT mutating the active work identity, and PUBLISHES (recovery_work_seq,
        the work_record with status = ARMED, work_due_event_ref, pending_recovery_work) ONLY after a successful enqueue. On a
        rejected enqueue it does NOT advance recovery_work_seq, publishes NO event reference, returns an explicit disposition
        (recovery_work_not_seated), and NEVER reports a pending/reserve_pending state; the round stays SECURITY_RECOVERY (or
        the horizon-close path governs). It is idempotent per episode (at most one in-flight RecoveryWorkID). A recovery-work
        action is NEVER a RecoveryOutcome; it never marks a decision APPLIED. The WORK itself runs in the post-epilogue hook
        ApplyRecoveryWorkAfterEpilogue (§9c). Because a recovery-work action is not an APPLYING decision, no APPLYING decision
        is ever left without a live event, a controller (pending_recovery_work), or an explicit terminal/horizon disposition (U3).

PROCEDURE RecoveryWorkDueEvent                                  # U1/U4: records the work DUE fact + refreshes census; NO work here
  INPUTS: RoundContext, dispatch_envelope, RecoveryEpisodeID, RecoveryWorkID, WorkGeneration, RecoveryWorkAction,
          RecoveryCensusVersion, RoundID_at_work, TemplateID_at_work, state_version_at_work
  PRECONDITIONS: a dispatched queued handler seated by SeatRecoveryWork (or a U3 re-arm) at (t_due, RECOVERY_WORK_DUE);
                 its dispatch_envelope is its own (§0.7f), envelope_namespace = ORDINARY_EVENT
  EFFECTS:
    SET episode <- RecoveryEpisodeID ; SET W <- recovery_work[RecoveryWorkID]
    # U1/U3/U4 STALE + IDENTITY GUARD: meaningful only for the CURRENT episode/epoch, the ACTIVE work generation, and
    #   an ARMED work action, with no outcome finalised. It records ONLY the due fact + refreshes the census; it
    #   performs NO reserve activation, NO transition, and NO APPLIED (the WORK is the post-epilogue hook, §9c).
    IF round_state != SECURITY_RECOVERY
       OR RecoveryEpisodeID != current_recovery_episode
       OR pending_recovery_work[episode] != RecoveryWorkID
       OR W.status != ARMED
       OR WorkGeneration != W.work_generation
       OR recovery_outcome_finalised[episode] is set
       OR RoundID_at_work != RoundID_current OR TemplateID_at_work != TemplateID_committed
       OR state_version_at_work != state_version_current:
      RETURN recovery_work_due_stale_noop(RecoveryWorkID)
    # U4: RECORD that the work is DUE at THIS event_time; stash the dispatch_envelope for the post-epilogue hook.
    SET recovery_work[RecoveryWorkID].status <- DUE
    SET recovery_work[RecoveryWorkID].due_status <- DUE
    SET recovery_work[RecoveryWorkID].due_at_event_time <- dispatch_envelope.event_time
    SET recovery_work[RecoveryWorkID].due_dispatch_envelope <- dispatch_envelope
    # U1: REFRESH a coherent census for THIS event_time (RECOVERY_WORK_DUE provenance) so the epilogue has the FINAL
    #   census to (re)version and decide from — a same-time WakeCompleteEvent that restores the floor still overwrites it.
    CALL CaptureSecurityCensusOnRecoveryDeadline(RoundContext, dispatch_envelope.event_time,
                                                 census_source = RECOVERY_WORK_DUE)   # U1/R5
    RETURN recovery_work_due(RecoveryWorkID, dispatch_envelope.event_time)
  RETURNS: recovery_work_due | recovery_work_due_stale_noop
  NOTE: U1/U4: step 1 of the recovery-work two-step. It NEVER activates a reserve and NEVER decides an outcome; it
        records the due fact (due_status = DUE) and refreshes the census. The WORK is ApplyRecoveryWorkAfterEpilogue,
        run AFTER this event_time's epilogue — so no recovery work runs during the ordinary-event drain.

PROCEDURE ApplyRecoveryWorkAfterEpilogue                        # U1/U3/U4/U5: post-epilogue hook — performs recovery WORK; NEVER applies RESTORED
  INPUTS: RoundContext, event_time t
  PRECONDITIONS: invoked by ProcessEventTime AFTER FinalizeEventTimeSecurityCensus(t), ApplyRecoveryCompletionAfterEpilogue(t),
                 and ApplyRecoveryAssignmentContinuationAfterEpilogue(t); NOT dispatched from the queue. It NEVER marks
                 a decision APPLIED and NEVER sets recovery_outcome_finalised — recovery WORK is not an outcome (U1).
  EFFECTS:
    IF current_recovery_episode = null: RETURN nothing_due          # not in recovery (or an outcome cleared it)
    SET episode <- current_recovery_episode
    IF pending_recovery_work[episode] = null: RETURN nothing_due
    SET work_id <- pending_recovery_work[episode] ; SET W <- recovery_work[work_id]
    IF W.due_status != DUE OR W.due_at_event_time != t: RETURN nothing_applicable_due(t)
    SET census <- latest_recovery_census[episode]
    # U1/U4 FRESHNESS. Perform work ONLY while the census still shows a breach before the deadline and the bound
    #   version is current; otherwise CONSUME the due fact as SUPERSEDED (the epilogue's own outcome decision governs).
    IF round_state != SECURITY_RECOVERY
       OR recovery_outcome_finalised[episode] is set
       OR W.bound_census_version != census.RecoveryCensusVersion
       OR NOT (census.breach = true AND census.deadline_reached = false):
      SET recovery_work[work_id].due_status <- SUPERSEDED           # U4: consumed as superseded
      SET recovery_work[work_id].status <- SUPERSEDED
      SET pending_recovery_work[episode] <- null
      RETURN recovery_work_superseded(work_id)
    # ---- FRESH: perform the WORK. It runs WHILE the floor is still breached; it NEVER applies RESTORED. ----
    SET recovery_work[work_id].status <- APPLYING                  # V7: DUE -> APPLYING while the work transaction runs (lifecycle)
    SET pctx <- PostEpilogueSchedulingContext(source_event_time = t, source_envelope = W.due_dispatch_envelope,
                  EventQueueContext = EQ, RunContext = RoundContext.RunContext)   # U2/T7: strictly-later scheduling
    SET plan <- CALL PrepareRecoveryAssignmentPlan(RoundContext, episode, W.action, census)   # U5: compute-only; verifies I1/I3/I10/I18b
    IF plan = plan_invalid(reason):
      # U4: consume the due fact; keep the episode (a later epilogue re-classifies). No mutation occurred.
      SET recovery_work[work_id].due_status <- CONSUMED
      SET recovery_work[work_id].status <- CONSUMED
      SET pending_recovery_work[episode] <- null
      RECORD recovery_work_plan_invalid(work_id, reason)
      RETURN recovery_work_plan_invalid(work_id)                    # round stays SECURITY_RECOVERY; no reserve activated
    SET commit <- CALL CommitRecoveryAssignmentPlan(RoundContext, plan, scheduling_context = POST_EPILOGUE(pctx))   # U2/U5
    IF commit = install_failed_before_mutation(reason):
      SET recovery_work[work_id].due_status <- CONSUMED
      SET recovery_work[work_id].status <- CONSUMED
      SET pending_recovery_work[episode] <- null
      RETURN recovery_work_commit_failed(work_id, reason)           # no mutation; round stays SECURITY_RECOVERY
    IF commit = install_failed_after_mutation(reason, rollback_record):
      SET rb <- CALL RollbackRecoveryAssignmentPlan(RoundContext, rollback_record)   # U5
      IF rb = rollback_failed(rr):
        # U5/T4: an irreversible partial mutation that cannot be rolled back — abort (never fabricate UNRECOVERABLE).
        SET recovery_work[work_id].due_status <- CONSUMED ; SET recovery_work[work_id].status <- CONSUMED
        SET pending_recovery_work[episode] <- null
        SET recovery_episode_disposition[episode] <- RECOVERY_INSTALL_FAILED_ABORTED   # T4 (NOT recovery_outcome_finalised)
        SET current_recovery_episode <- null
        CALL RoundAbort(RoundContext, reason = recovery_install_failed_aborted,
                        dispatch_envelope = W.due_dispatch_envelope, recovery_finalising = true)   # T4/S4
        RETURN recovery_work_install_aborted(work_id)
      # rollback succeeded: no live partial assignment remains; keep the episode.
      SET recovery_work[work_id].due_status <- CONSUMED ; SET recovery_work[work_id].status <- CONSUMED
      SET pending_recovery_work[episode] <- null
      RETURN recovery_work_rolled_back(work_id)                     # round stays SECURITY_RECOVERY
    # commit = install_committed: the reserve wake(s) / redistribution PENDING heads are seated STRICTLY LATER (U2).
    #   The round STAYS SECURITY_RECOVERY; NOTHING is marked RESTORED (U1). A later WakeCompleteEvent raises H_honest,
    #   and a later final census with NO breach mints RESTORED (via the ordinary completion two-step).
    SET recovery_work[work_id].due_status <- CONSUMED              # U4: consumed on apply
    SET recovery_work[work_id].status <- CONSUMED
    SET pending_recovery_work[episode] <- null
    RETURN recovery_work_applied(work_id, W.action)
  RETURNS: recovery_work_applied | recovery_work_rolled_back | recovery_work_install_aborted | recovery_work_commit_failed |
           recovery_work_plan_invalid | recovery_work_superseded | nothing_due | nothing_applicable_due
  NOTE: U1/U4/U5: the ONLY place recovery WORK is performed. It runs POST-epilogue, activates reserves / redistributes
        coverage via the named PrepareRecoveryAssignmentPlan / CommitRecoveryAssignmentPlan / RollbackRecoveryAssignmentPlan
        procedures, threads the explicit POST_EPILOGUE scheduling_context to every nested ScheduleEvent (U2), and
        EXPLICITLY consumes the due fact (CONSUMED / SUPERSEDED) before returning (U4). It NEVER marks an outcome and
        NEVER sets recovery_outcome_finalised — the round stays SECURITY_RECOVERY and RESTORED is decided ONLY by a
        later no-breach final census (U1). At most one of the completion / continuation / work hooks acts per episode
        per event_time.
```

## 10. Reserve activation

```
PROCEDURE ReserveActivate
  INPUTS: RoundContext, deficit (rate to restore),
          scheduling_context   # U2: SchedulingSourceContext — ORDINARY_DISPATCH(dispatch_envelope) for a dispatched
                               #   entry point, or POST_EPILOGUE(pctx) when CommitRecoveryAssignmentPlan activates a
                               #   reserve from the post-epilogue recovery-work / continuation-install path (§9c/§10a).
  PRECONDITIONS: round_state = SECURITY_RECOVERY or ASSIGNMENT;
                 # U2: ReserveActivate threads its scheduling_context to StartWake -> ScheduleEvent, so a POST_EPILOGUE
                 #     activation seats its WakeCompleteEvent STRICTLY LATER (never at the drained source time). A
                 #     dispatched entry point equivalently passes ORDINARY_DISPATCH(dispatch_envelope). NO manual seq stamping.
  EFFECTS:
    # V5: SELECTION belongs to the ordinary entry point (or PrepareRecoveryAssignmentPlan). It selects the reserve
    #   miner + range + provenance, then delegates the MUTATION to the plan-bound ReserveActivateFromPlan — so the
    #   commit path (CommitRecoveryAssignmentPlan) never re-SELECTs.
    SELECT reserve_miner from miners in RESERVE
    SELECT candidate_range from unsearched/reassignable portion of nonce_domain
    # F4: a fresh never-assigned range is ORIGINAL; a previously assigned unsearched suffix is REASSIGNED.
    IF candidate_range is a fresh never-assigned range:
      origin <- ORIGINAL   ; source <- null
    ELSE:
      origin <- REASSIGNED ; source <- source_assignment(candidate_range)
    RETURN CALL ReserveActivateFromPlan(RoundContext, reserve_miner = reserve_miner, candidate_range = candidate_range,
                     assignment_origin = origin, source_assignment = source, scheduling_context = scheduling_context)   # V4/V5
  RETURNS: reserve_activation_committed(MinerID, AssignmentID, assignment_version, WakeEventRef) |
           reserve_activation_failed_before_mutation(reason) |
           reserve_activation_failed_after_assignment(reason, AssignmentID, rollback_record)
  NOTE: V4/V5: the ordinary reserve-activation entry point. It SELECTS the reserve miner/range/provenance and delegates
        the atomic mutation to ReserveActivateFromPlan; the commit path calls ReserveActivateFromPlan DIRECTLY with the
        plan's exact values, so a committed reserve activation equals its validated plan (V5). It returns the V4
        structured transaction disposition (never a bare activation_started). Reserve provenance distinguishes ORIGINAL
        from REASSIGNED (F4).

PROCEDURE ReserveActivateFromPlan                               # V4/V5: plan-bound reserve activation; a TRANSACTION with actual references
  INPUTS: RoundContext, reserve_miner, candidate_range, assignment_origin, source_assignment,
          scheduling_context   # V5: EXACT plan-selected values (no independent SELECT); V2: explicit scheduling_context
  PRECONDITIONS: reserve_miner in RESERVE; candidate_range + provenance are the plan's validated values (I1/I3/I10/I18b);
                 round_state = SECURITY_RECOVERY or ASSIGNMENT
  EFFECTS:
    SET reason <- (assignment_origin = REASSIGNED ? security_recovery : null)   # F4
    # V5: REVALIDATE the EXACT specs immediately BEFORE mutation (a concurrent same-time change may have invalidated them).
    IF the (reserve_miner, candidate_range, assignment_origin) spec now violates I1 OR I3 OR I10 OR I18b:
      RETURN reserve_activation_failed_before_mutation(reason = revalidation_failed)   # V4: nothing created
    # F4: the shared constructor performs the I1/I10 overlap guard, ledgers the PENDING version, sets custody/provenance.
    SET cr <- CALL CreatePendingAssignment(RoundContext, reserve_miner, candidate_range,
                        assignment_origin = assignment_origin, source_assignment = source_assignment, reason = reason)
    IF cr is assignment_creation_failed(cf):
      RETURN reserve_activation_failed_before_mutation(reason = cf)     # V4/W7: constructor rejected; nothing to roll back
    SET assignment <- cr.assignment                                     # W7: cr = assignment_created(assignment) — safe to read now
    SET lease_start(assignment)  <- now
    SET lease_expiry(assignment) <- now + default_lease_duration
    # F5/D2/V3: activation ALWAYS passes through WAKING via the NON-BLOCKING StartWake TRANSACTION.
    SET wr <- CALL StartWake(RoundContext, reserve_miner, target_assignment = assignment, from_state = RESERVE,
                     scheduling_context = scheduling_context)           # V2/V3
    IF wr = wake_seated(...):
      RETURN reserve_activation_committed(MinerID = reserve_miner, AssignmentID = AssignmentID(assignment),
                assignment_version = assignment_version(assignment), WakeEventRef = wr.WakeEventRef)   # V4: ACTUAL refs
    # V4: wake seating (or its post-seat transition) FAILED after the PENDING assignment was created -> ROLL BACK legally:
    #   close the assignment, restore coverage/custody ledgers, and leave the reserve miner in RESERVE (never stranded WAKING).
    IF wr = wake_transition_failed_after_seat(reason2, wref):
      IF wref is still pending on EQ: CANCEL wref on EQ                 # StartWake already cancelled; idempotent
    CLOSE assignment as CLOSED (status = CLOSED, custody_status = revoked, reason = reserve_activation_wake_failed)   # J7: no live head (I18b)
    RESTORE the coverage-state / custody ledgers for candidate_range (I8a/I8b)
    ASSERT miner_state(reserve_miner) = RESERVE                         # V4/gate 4: the reserve miner stays RESERVE, not WAKING
    SET rollback_record <- rollback_record(RecoveryInstallID = null, created_assignments = {assignment}, created_events = {})
    RETURN reserve_activation_failed_after_assignment(reason = wr, AssignmentID = AssignmentID(assignment),
                                                      rollback_record = rollback_record)   # V4
  RETURNS: reserve_activation_committed(MinerID, AssignmentID, assignment_version, WakeEventRef) |
           reserve_activation_failed_before_mutation(reason) |
           reserve_activation_failed_after_assignment(reason, AssignmentID, rollback_record)
  NOTE: V4/V5: the plan-bound reserve activation. It uses the EXACT plan values (no SELECT), REVALIDATES them before
        mutation, and returns ACTUAL transaction references (AssignmentID, assignment_version, WakeEventRef). If wake
        seating fails after the PENDING assignment is created, it closes the assignment legally, restores the ledgers,
        and leaves the reserve miner in RESERVE — a declared failure disposition, never a stranded WAKING miner (gate 4).
        PENDING -> CURRENT still occurs ONLY at the scheduled WakeCompleteEvent on a successful wake (E4/F5).
```

## 10a. Executable security-recovery completion — two-step contract (Q2/Q3; R13/R14; RecoveryOutcome O3; atomic apply R4; post-drain safety R1; single settlement R2; deferred branch-C atomicity S2/S3; terminal cleanup S4; continuation two-step T1; continuation version binding T2; installation-phase invariant T3; no fabricated UNRECOVERABLE T4; assignment-phase disposition T5; redistribution-only vs reserve-dependent T6; post-epilogue continuation causality T7)

**T1 (branch-C continuation is itself a two-step contract).** Just as the completion application is split into a
queued `RecoveryCompletionDueEvent` (records the due FACT + refreshes the census, NO transition) and a POST-epilogue
hook `ApplyRecoveryCompletionAfterEpilogue` (the ONLY place a completion outcome is applied), the branch-C
continuation is ALSO split: `CompleteSecurityRecovery` branch C seats a queued
`RecoveryAssignmentContinuationDueEvent` that RECORDS the continuation DUE fact and refreshes the census (NO
transition / NO assignment install / NO APPLIED), and the POST-epilogue hook
`ApplyRecoveryAssignmentContinuationAfterEpilogue` is the ONLY place branch-C RESTORED is APPLIED. `ProcessEventTime`
runs BOTH post-epilogue hooks after the event-time epilogue — the completion hook first, then the continuation hook
— so no branch-C RESTORED is ever applied during the ordinary event drain, and neither hook enqueues assignment work
at the already-drained `event_time`.

**S2/S3/S4 (deferred branch-C atomicity, terminal cleanup).** Branch C (RESTORED with range redistribution) is a
DEFERRED application: `CompleteSecurityRecovery` (a) does NOT mutate `round_state` before the continuation is
SEATED — it computes `t_cont`, validates `t_cont <= T`, mints the continuation identity (T2:
`continuation_generation <- 1`, `continuation_id`, `continuation_bound_census_version`), seats ONE
`RecoveryAssignmentContinuationDueEvent` (through the S7 `PostEpilogueSchedulingContext`, so the target is STRICTLY
LATER than `t`), and only THEN returns `DEFERRED`; (b) a failed seat / target-beyond-`T` leaves the round in
`SECURITY_RECOVERY` and marks the decision `APPLY_FAILED`/`HORIZON_DEFERRED`, PRESERVING the episode (S2). Seating is
NOT applying RESTORED (S3): the decision stays `APPLYING`, the episode stays ACTIVE, and RESTORED is APPLIED only
when the POST-epilogue hook `ApplyRecoveryAssignmentContinuationAfterEpilogue` verifies the still-current APPLYING
decision AND the fresh continuation binding (T2), transitions `SECURITY_RECOVERY -> ASSIGNMENT`, installs the
disjoint assignment set, and reaches `HASHING` (a failure before the transition stays `SECURITY_RECOVERY`; a failure
DURING install after the transition takes a declared recovery-finalising `RoundAbort` — the T4
`RECOVERY_INSTALL_FAILED_ABORTED` disposition + `APPLY_FAILED_TERMINAL` status, never a fabricated UNRECOVERABLE — so
the round never lingers in `ASSIGNMENT` with an active episode and no live continuation). **S4:** when a round
becomes terminal while an episode is still active, `CloseRoundAssignments` calls `CancelActiveRecoveryEpisode`
(unless the closure IS the recovery-finalising abort): it cancels every pending/applying decision and its queued
`RecoveryCompletionDueEvent`/`RecoveryAssignmentContinuationDueEvent`, records `TERMINAL_CANCELLED`, and clears
`current_recovery_episode` — so `current_recovery_episode != null` IFF `round_state = SECURITY_RECOVERY`.

**R1/R2/R4/T7 (post-epilogue causality, atomic application, single settlement).** The post-epilogue recovery
application (a) enqueues NOTHING at the already-drained application `event_time` — branch C defers all
`ReserveActivate`/`RangeReassign`/`StartWake` work to a SINGLE `RecoveryAssignmentContinuationDueEvent` seated at
`next_representable_simulation_time(t)`, a STRICTLY LATER `event_time`, whose OWN post-epilogue hook
`ApplyRecoveryAssignmentContinuationAfterEpilogue` performs the rebuild (R1/T7); (b) is ATOMIC — a decision passes
`SCHEDULED -> APPLYING -> APPLIED` and is finalised (episode cleared) ONLY after `CompleteSecurityRecovery` reports
success (branches A/B/D) or the continuation hook reaches HASHING (branch C, S3/T3), else it becomes `APPLY_FAILED`
(pre-transition, episode preserved) or `APPLY_FAILED_TERMINAL` (install-fail abort, T4) (R4); and (c) is settled
ONCE by `FinalizePostRecoveryApplicationState` — a post-application SETTLEMENT that archives the
terminal/post-application census and clears `security_census_dirty[t]` (through the sole clearer
`SettleSecurityCensusDirty`, S5) WITHOUT invoking `SecurityFloorEvaluate` a second time (R2). A terminal/horizon
round applies nothing and cancels the pending set (R4/S4/gate 8).

**Q2 (do not apply recovery before the dispatch-time epilogue).** The recovery exit is a TWO-STEP contract, so
no outcome can be applied before the FINAL census of its own application `event_time` is known: (1)
`RecoveryCompletionDueEvent` is an ordinary queued event that RECORDS that a `RecoveryDecisionID` is due and
REFRESHES the census for that `event_time` — it performs NO round-state transition and NO `RoundAbort`; (2)
`ApplyRecoveryCompletionAfterEpilogue` is invoked by `ProcessEventTime` ONLY after the `event_time` is
quiescent and its FINAL recovery census/version is published (Q1) — it applies the decision ONLY if the
decision's `RecoveryCensusVersion` equals `latest_recovery_census[episode].RecoveryCensusVersion` (re-affirmed,
not superseded) AND the outcome still matches the final census. So a `RESTORED` decision NEVER leaves recovery
when a newer final census shows a breach. The actual R13/R14 transition/abort is performed by
`CompleteSecurityRecovery`, now an INTERNAL branch-dispatch helper called ONLY by
`ApplyRecoveryCompletionAfterEpilogue` (never a queued event).

```
PROCEDURE RecoveryCompletionDueEvent                            # Q2 step 1: records due + refreshes census; NO transition
  INPUTS: RoundContext, dispatch_envelope, RecoveryEpisodeID, RecoveryDecisionID, RecoveryOutcome,
          RecoveryCensusVersion, RoundID_at_decision, TemplateID_at_decision, state_version_at_decision
  PRECONDITIONS: a dispatched queued handler seated at (target_time, RECOVERY_COMPLETION_DUE); its
                 dispatch_envelope is its own (§0.7f), envelope_namespace = ORDINARY_EVENT (Q6)
  EFFECTS:
    # STALE GUARD: meaningful only for the CURRENT episode/epoch, an unfinalised episode, and a decision STILL in
    #   the pending set (not SUPERSEDED/CANCELLED by an intervening final census, Q1/Q3).
    IF round_state != SECURITY_RECOVERY
       OR RecoveryEpisodeID != current_recovery_episode
       OR recovery_outcome_finalised[RecoveryEpisodeID] is set
       OR RecoveryDecisionID NOT in pending_recovery_decisions[RecoveryEpisodeID]
       OR RoundID_at_decision != RoundID_current OR TemplateID_at_decision != TemplateID_committed
       OR state_version_at_decision != state_version_current:
      RETURN recovery_due_stale_noop
    # Q2: RECORD that the decision is DUE at THIS event_time; stash the dispatch_envelope for the eventual apply.
    #   NO round-state transition and NO RoundAbort here.
    SET recovery_decisions[RecoveryDecisionID].due_at_event_time <- dispatch_envelope.event_time
    SET recovery_decisions[RecoveryDecisionID].due_dispatch_envelope <- dispatch_envelope
    # Q2/R5: REFRESH a coherent census for THIS event_time via the sole writer CommitSecurityCensus with the
    #   completion-due source RECOVERY_COMPLETION_DUE (its OWN provenance, distinct from the RECOVERY_DEADLINE
    #   checkpoint), so the epilogue has the FINAL census to (re)version and decide from.
    CALL CaptureSecurityCensusOnRecoveryDeadline(RoundContext, dispatch_envelope.event_time,
                                                 census_source = RECOVERY_COMPLETION_DUE)   # R5: completion-due provenance
    RETURN recovery_completion_due(RecoveryDecisionID, dispatch_envelope.event_time)
  RETURNS: recovery_completion_due | recovery_due_stale_noop
  NOTE: Q2: step 1 of the two-step contract. It NEVER applies an outcome; it only records the due fact and
        refreshes the census. The application (with the final-census freshness check) is
        ApplyRecoveryCompletionAfterEpilogue, run AFTER this event_time's epilogue.

PROCEDURE ApplyRecoveryCompletionAfterEpilogue                  # Q2 step 2 / R4: apply a due decision ATOMICALLY after the epilogue
  INPUTS: RoundContext, event_time t
  PRECONDITIONS: invoked by ProcessEventTime AFTER FinalizeEventTimeSecurityCensus(t) has published the FINAL
                 recovery census version for t (Q1); NOT dispatched from the queue
  EFFECTS:
    # R4 TERMINAL/HORIZON GUARD (checked FIRST). If the round is already terminal — CloseRoundAtHorizon closed it at
    #   T (P1), or a prior UNRECOVERABLE abort closed it — NO pending decision may be applied. Cancel every pending
    #   decision of the (now stale) episode and return terminal_recovery_noop; NO decision is ever marked APPLIED
    #   after horizon closure (gate 8).
    IF round_state in {ROUND_ACCEPTED, ROUND_ABORTED}:
      IF current_recovery_episode != null:
        SET episode <- current_recovery_episode
        FOR EACH decision_id in pending_recovery_decisions[episode] (stable order by decision_id):
          CALL SetRecoveryDecisionStatus(RoundContext, decision_id, CANCELLED)   # R4/R6: cancel + keep the mirror consistent
        SET pending_recovery_decisions[episode] <- empty set
      RETURN terminal_recovery_noop
    IF current_recovery_episode = null: RETURN nothing_due       # not in recovery
    SET episode <- current_recovery_episode
    IF latest_recovery_census[episode] does NOT EXIST: RETURN nothing_due
    SET census <- latest_recovery_census[episode]
    FOR EACH decision_id in pending_recovery_decisions[episode]
        WITH recovery_decisions[decision_id].due_at_event_time = t (stable order by decision_id):
      SET D <- recovery_decisions[decision_id]
      # R4 step 1 — VERIFY. Apply ONLY if the decision is SCHEDULED and due, bound to the LATEST census version
      #   (Reconcile re-affirmed it — no newer final census superseded it), the outcome still matches the FINAL
      #   census at t, AND the round is nonterminal + still in SECURITY_RECOVERY.
      IF D.status != SCHEDULED
         OR D.bound_census_version != census.RecoveryCensusVersion
         OR NOT outcome_consistent_with_census(D.outcome, census)
         OR round_state != SECURITY_RECOVERY:
        CALL SetRecoveryDecisionStatus(RoundContext, decision_id, SUPERSEDED)    # R6: mirror stays consistent
        REMOVE decision_id from pending_recovery_decisions[episode]
        RECORD recovery_apply_stale_noop(decision_id)           # a RESTORED cannot leave recovery under a breach census
        CONTINUE
      # R4/S3 step 2 — atomically mark APPLYING (NOT APPLIED). Do NOT finalise the episode or clear
      #   current_recovery_episode yet; the outcome is committed ONLY after the branch reports SUCCESS.
      CALL SetRecoveryDecisionStatus(RoundContext, decision_id, APPLYING)        # R4 step 2 (R6 mirror)
      # R4/S3 step 3 — execute the R13/R14 branch; it returns an EXPLICIT disposition kind SUCCESS | DEFERRED | FAILED.
      #   Branch C (RESTORED redistribution) returns DEFERRED after seating its continuation (S2/S3); branches A/B/D
      #   return SUCCESS on a completed transition/abort; any branch returns FAILED if no legal transition/seat occurred.
      SET disposition <- CALL CompleteSecurityRecovery(RoundContext, D.due_dispatch_envelope,
                              episode, decision_id, D.outcome, D.bound_census_version)   # S3: full identity for a deferred continuation
      IF disposition.kind = SUCCESS:
        # R4 step 4 — ONLY AFTER a successful round transition / successful RoundAbort (branches A/B/D): mark
        #   APPLIED, finalise the episode outcome, remove from pending, clear the active episode.
        CALL SetRecoveryDecisionStatus(RoundContext, decision_id, APPLIED)       # R4/R6
        SET recovery_outcome_finalised[episode] <- D.outcome
        REMOVE decision_id from pending_recovery_decisions[episode]
        SET current_recovery_episode <- null
        RETURN recovery_applied(decision_id, D.outcome, disposition.target)
      ELSE IF disposition.kind = DEFERRED:
        # S3/T1 — branch C SEATED its RecoveryAssignmentContinuationDueEvent successfully. Seating is NOT applying
        #   RESTORED: the decision REMAINS APPLYING, recovery_outcome_finalised is NOT set, current_recovery_episode is
        #   NOT cleared, the decision STAYS in pending_recovery_decisions (so a newer census can still supersede it),
        #   and the round REMAINS SECURITY_RECOVERY. The continuation applies RESTORED (and finalises the episode) ONLY
        #   when the POST-epilogue hook ApplyRecoveryAssignmentContinuationAfterEpilogue reaches HASHING (§10a T1).
        RETURN recovery_deferred(decision_id, disposition.continuation_ref)
      ELSE:  # disposition.kind = FAILED
        # R4/S2 step 5 — the branch FAILED before a legal transition (an A/B transition failed, or branch C could
        #   not seat a valid continuation / its target fell beyond T). Do NOT mark APPLIED; record APPLY_FAILED (or
        #   HORIZON_DEFERRED when the target fell beyond T); PRESERVE the active episode (current_recovery_episode NOT
        #   cleared, recovery_outcome_finalised NOT set); the round REMAINS SECURITY_RECOVERY, so a later epilogue may
        #   re-seat a warranted outcome.
        SET fail_status <- (disposition.reason = horizon_deferred ? HORIZON_DEFERRED : APPLY_FAILED)
        CALL SetRecoveryDecisionStatus(RoundContext, decision_id, fail_status)   # R4/R6
        REMOVE decision_id from pending_recovery_decisions[episode]
        RECORD recovery_apply_branch_failed(decision_id, disposition.reason)
        RETURN recovery_apply_failed(decision_id, fail_status)
    RETURN nothing_applicable_due(t)
  RETURNS: recovery_applied | recovery_deferred | recovery_apply_stale_noop | recovery_apply_failed |
           terminal_recovery_noop | nothing_due | nothing_applicable_due
  NOTE: Q2/R4/S2/S3: the ONLY place a recovery outcome is applied or DEFERRED, applied ATOMICALLY. A decision passes
        SCHEDULED -> APPLYING -> {APPLIED | (deferred, stays APPLYING) | APPLY_FAILED | HORIZON_DEFERRED}. For
        branches A/B/D a SUCCESS disposition marks APPLIED + finalises + clears the episode. For branch C a DEFERRED
        disposition (S3) leaves the decision APPLYING and the episode ACTIVE with the round still SECURITY_RECOVERY —
        RESTORED is applied ONLY when the seated RecoveryAssignmentContinuationDueEvent's POST-epilogue hook
        ApplyRecoveryAssignmentContinuationAfterEpilogue reaches HASHING (T1); a FAILED
        disposition marks APPLY_FAILED/HORIZON_DEFERRED and PRESERVES the active episode. A terminal/horizon round
        applies nothing (gate 8; primary terminal cleanup is CancelActiveRecoveryEpisode via CloseRoundAssignments,
        S4). It runs post-quiescence, so a RESTORED decision cannot leave recovery when the final census at t shows a
        breach (Q2). At most one outcome per episode (O4). R1: the exit path enqueues NOTHING at t — branch C's
        continuation is seated (through the S7 PostEpilogueSchedulingContext) at next_representable_simulation_time(t).

PROCEDURE CompleteSecurityRecovery                              # INTERNAL branch dispatch (R13/R14); called ONLY by ApplyRecoveryCompletionAfterEpilogue
  INPUTS: RoundContext, dispatch_envelope, episode, decision_id, RecoveryOutcome, bound_census_version
          # O3: RESTORED -> A/B/C; UNRECOVERABLE -> D. S3: episode/decision_id/bound_census_version are threaded so a
          #     branch-C DEFERRED continuation carries the FULL recovery identity.
  PRECONDITIONS: round_state = SECURITY_RECOVERY; the episode's decision was ALREADY freshness-checked and marked
                 APPLYING by ApplyRecoveryCompletionAfterEpilogue (Q2/R4). This procedure is NOT a queued event.
  EFFECTS:
    # R4/S2/S3: EVERY branch returns an EXPLICIT recovery_branch_result(kind, ...), kind in {SUCCESS, DEFERRED, FAILED}.
    #   SUCCESS -> caller marks APPLIED + finalises + clears the episode (branches A/B/D). DEFERRED -> caller leaves
    #   the decision APPLYING and the episode ACTIVE (branch C: continuation seated). FAILED -> caller records
    #   APPLY_FAILED / HORIZON_DEFERRED and PRESERVES the episode. S2: NO branch mutates round_state before its
    #   terminal/deferred step is committed.
    IF RecoveryOutcome = UNRECOVERABLE:
      # (D) R14: the floor cannot be restored -> abort THIS round (not the run, N1). This abort IS the outcome
      #     application, so it is the recovery-FINALISING abort: the S4 terminal cleanup (CancelActiveRecoveryEpisode)
      #     is SKIPPED for this closure and the CALLER finalises the episode (APPLIED, recovery_outcome_finalised).
      CALL RoundAbort(RoundContext, reason = floor_unrecoverable, dispatch_envelope = dispatch_envelope,
                      recovery_finalising = true)                                  # S4: this closure finalises the episode; do NOT cancel it
      IF round_state = ROUND_ABORTED:
        RETURN recovery_branch_result(kind = SUCCESS, target = ROUND_ABORTED)      # R4: successful RoundAbort
      RETURN recovery_branch_result(kind = FAILED, reason = abort_did_not_terminate)   # R4: defensive (should not occur)
    # ---- RecoveryOutcome = RESTORED: branches A/B/C ----
    IF active_propagation_set is non-empty:
      # (A) R13/G8: LIVE propagation contexts remain -> resume propagation (contexts + events PRESERVED). Use the
      #     round-state helper so the SOLUTION_PROPAGATION applicability-entry census is captured (M2).
      ASSERT every cpc in active_propagation_set retains its status in {PROPAGATING, PENDING_ACCEPTANCE}
             AND its scheduled events are intact           # preserve candidate contexts + events (G8)
      CALL TransitionRoundState(RoundContext, SOLUTION_PROPAGATION, dispatch_envelope)   # SECURITY_RECOVERY -> SOLUTION_PROPAGATION (R13); + census
      IF round_state = SOLUTION_PROPAGATION:
        RETURN recovery_branch_result(kind = SUCCESS, target = SOLUTION_PROPAGATION)
      RETURN recovery_branch_result(kind = FAILED, reason = transition_failed)
    ELSE IF recovery restored coverage WITHOUT any range redistribution or new reserve assignment:
      # (B) R13: no live contexts and the assignment set is unchanged -> resume hashing directly (M2 census).
      CALL TransitionRoundState(RoundContext, HASHING, dispatch_envelope)                # SECURITY_RECOVERY -> HASHING (R13); + census
      IF round_state = HASHING:
        RETURN recovery_branch_result(kind = SUCCESS, target = HASHING)
      RETURN recovery_branch_result(kind = FAILED, reason = transition_failed)
    ELSE:
      # (C) R13/R1/S2/S3/T1/U1: RESTORED with range REDISTRIBUTION. It is reached ONLY for a RESTORED outcome
      #     (census.breach = false), so the floor is already met by currently ACTIVE_HASHING miners — the continuation
      #     is REDISTRIBUTION-ONLY and NEVER depends on future reserve hash rate (reserve activation while the floor is
      #     still breached is recovery WORK, §9c, not a RESTORED continuation). It is DEFERRED to a two-step
      #     contract (T1): a SINGLE RecoveryAssignmentContinuationDueEvent seated at next_representable_simulation_time(t)
      #     — a STRICTLY LATER event_time (R1) — records the due fact + refreshes the census, and the POST-EPILOGUE
      #     hook ApplyRecoveryAssignmentContinuationAfterEpilogue applies branch C. S2: DO NOT MUTATE round_state
      #     before the DUE event is SEATED. Compute t_cont, validate t_cont <= T, seat the DUE event, and ONLY THEN
      #     return DEFERRED; the round REMAINS SECURITY_RECOVERY throughout this procedure. The ASSIGNMENT transition
      #     happens INSIDE the post-epilogue hook (T1/T3), never during the ordinary-event drain.
      SET t_cont <- next_representable_simulation_time(dispatch_envelope.event_time)    # (1) R1: strictly later than t
      IF t_cont > run_horizon_T:                                                        # (2) validate t_cont <= T (O2)
        RECORD recovery_continuation_horizon_deferred(decision_id, t_cont)
        RETURN recovery_branch_result(kind = FAILED, reason = horizon_deferred)         # S2: stay SECURITY_RECOVERY; caller -> HORIZON_DEFERRED
      # T2: MINT the ACTIVE continuation identity for this decision and BIND it to the current census version. The
      #     immutable DUE event carries the GENERATION; the AUTHORITATIVE version is the decision's
      #     continuation_bound_census_version (kept current by ReconcilePendingRecoveryDecisions, T2 rule B), which
      #     the post-epilogue application reads and verifies against the latest final census.
      SET recovery_decisions[decision_id].continuation_generation <- 1
      SET recovery_decisions[decision_id].continuation_id <- (decision_id, 1)
      SET recovery_decisions[decision_id].continuation_bound_census_version <- bound_census_version
      # (3) SEAT the DUE event (T1 step 1) through the SOLE scheduler with an explicit S7/T7 PostEpilogueSchedulingContext.
      #     NO round-state mutation has occurred yet (S2); the DUE event only RECORDS + refreshes the census — the
      #     APPLICATION is the post-epilogue hook (T1). It carries the continuation GENERATION, not a raw census version.
      SET pctx <- PostEpilogueSchedulingContext(source_event_time = dispatch_envelope.event_time,
                    source_envelope = dispatch_envelope, EventQueueContext = EQ, RunContext = RoundContext.RunContext)   # S7/T7
      SET r <- CALL ScheduleEvent(EQ, RoundContext, RecoveryAssignmentContinuationDueEvent,
                     target_event_time = t_cont, target_microphase = RECOVERY_ASSIGNMENT_CONTINUATION_DUE,
                     {RecoveryEpisodeID = episode, RecoveryDecisionID = decision_id,
                      ContinuationGeneration = 1, RecoveryOutcome = RecoveryOutcome,
                      RoundID_at_decision = RoundID_current, TemplateID_at_decision = TemplateID_committed,
                      state_version_at_decision = state_version_current},
                     post_epilogue_context = pctx)                                       # T1/T2/S7: strictly-later seat of the DUE event
      IF r = scheduled(...):
        # (4) ONLY AFTER a SUCCESSFUL seat: record the deferred-application state. The round stays SECURITY_RECOVERY
        #     and the decision stays APPLYING (the caller does NOT finalise). Store the continuation ref so a later
        #     supersession (Reconcile) or terminal cleanup (S4) can cancel it.
        SET recovery_decisions[decision_id].continuation_event_ref <- r.event_ref       # S3/S4: cancellable continuation
        RETURN recovery_branch_result(kind = DEFERRED, continuation_ref = r.event_ref)   # S3: seated, NOT applied
      # seat REJECTED (e.g. finalised-time / backward) -> stay SECURITY_RECOVERY, no continuation pending.
      RECORD recovery_continuation_not_seated(decision_id, r)
      RETURN recovery_branch_result(kind = FAILED, reason = continuation_not_seated)     # S2: caller -> APPLY_FAILED
  RETURNS: recovery_branch_result(kind, target | reason | continuation_ref)
  NOTE: R13/R14/O3/R1/R4/S2/S3: the branch dispatch, called ONLY by ApplyRecoveryCompletionAfterEpilogue after the
        decision is marked APPLYING. RESTORED: (A) SOLUTION_PROPAGATION and (B) HASHING transition synchronously and
        return SUCCESS; (C) range redistribution is DEFERRED — it seats ONE RecoveryAssignmentContinuationDueEvent at
        next_representable_simulation_time(t) BEFORE any round-state mutation (S2/T1) and returns DEFERRED, so the round
        stays SECURITY_RECOVERY and the decision stays APPLYING until the POST-EPILOGUE hook
        ApplyRecoveryAssignmentContinuationAfterEpilogue applies branch C (T1/T3).
        UNRECOVERABLE: (D) -> recovery-FINALISING RoundAbort(floor_unrecoverable) (S4). A failed seat / target-beyond-T
        returns FAILED and leaves the round SECURITY_RECOVERY (S2). It never fabricates a template and never settles residency.

PROCEDURE RecoveryAssignmentContinuationDueEvent               # T1 step 1: records the continuation DUE + refreshes census; NO application
  INPUTS: RoundContext, dispatch_envelope, RecoveryEpisodeID, RecoveryDecisionID, ContinuationGeneration,
          RecoveryOutcome, RoundID_at_decision, TemplateID_at_decision, state_version_at_decision   # T2: carries the continuation generation
  PRECONDITIONS: a dispatched queued handler seated by CompleteSecurityRecovery branch C at (t_cont,
                 RECOVERY_ASSIGNMENT_CONTINUATION_DUE); its dispatch_envelope is its own (§0.7f),
                 envelope_namespace = ORDINARY_EVENT (Q6/R3); RecoveryOutcome = RESTORED. (U1: the continuation is a
                 REDISTRIBUTION-ONLY RESTORED continuation — it never depends on future reserve hash rate; reserve
                 activation while the floor is still breached is recovery WORK, §9c, not a continuation.)
  EFFECTS:
    SET episode <- RecoveryEpisodeID
    SET D <- recovery_decisions[RecoveryDecisionID]
    # T1/T2/U4 STALE + IDENTITY GUARD: meaningful only for the CURRENT episode/epoch, an APPLYING decision, and the
    #   ACTIVE continuation generation (ContinuationGeneration = D.continuation_generation). It records ONLY the due
    #   fact (continuation_due_status = DUE) + refreshes the census; it performs NO round-state transition, creates NO
    #   assignment, and does NOT mark the decision APPLIED (T1 — no branch-C RESTORED result during the ordinary drain).
    #   The APPLICATION is the post-epilogue hook (T1 step 2).
    IF round_state != SECURITY_RECOVERY
       OR current_recovery_episode != episode
       OR RecoveryDecisionID NOT in pending_recovery_decisions[episode]
       OR D.status != APPLYING
       OR ContinuationGeneration != D.continuation_generation                    # T2: only the ACTIVE continuation generation
       OR recovery_outcome_finalised[episode] is set
       OR RoundID_at_decision != RoundID_current OR TemplateID_at_decision != TemplateID_committed
       OR state_version_at_decision != state_version_current:
      RETURN recovery_continuation_due_stale_noop(RecoveryDecisionID)
    # T1/U4: RECORD that the continuation is DUE at THIS event_time (continuation_due_status = DUE); stash the
    #   dispatch_envelope for the post-epilogue apply, which will EXPLICITLY consume this due status.
    SET recovery_decisions[RecoveryDecisionID].continuation_due_status <- DUE                      # U4
    SET recovery_decisions[RecoveryDecisionID].continuation_due_at_event_time <- dispatch_envelope.event_time
    SET recovery_decisions[RecoveryDecisionID].continuation_due_dispatch_envelope <- dispatch_envelope
    # T1/U7: REFRESH a coherent census for THIS event_time via the sole writer CommitSecurityCensus with the DISTINCT
    #   source RECOVERY_CONTINUATION_DUE (U7 — "continuation is due" is not conflated with "completion is due"), so the
    #   epilogue has the FINAL census to (re)version and decide from.
    CALL CaptureSecurityCensusOnRecoveryDeadline(RoundContext, dispatch_envelope.event_time,
                                                 census_source = RECOVERY_CONTINUATION_DUE)   # U7: distinct provenance
    RETURN recovery_continuation_due(RecoveryDecisionID, dispatch_envelope.event_time)
  RETURNS: recovery_continuation_due | recovery_continuation_due_stale_noop
  NOTE: T1: step 1 of the two-step continuation contract. It NEVER applies branch C; it records the due fact and
        refreshes the census. The application (with the final-census freshness + version check, T2) is
        ApplyRecoveryAssignmentContinuationAfterEpilogue, run AFTER this event_time's epilogue — so NO branch-C
        RESTORED result is recorded during the ordinary-event drain (T1).

PROCEDURE ApplyRecoveryAssignmentContinuationAfterEpilogue     # T1 step 2 / post-epilogue hook: the ONLY place branch-C RESTORED is APPLIED
  INPUTS: RoundContext, event_time t
  PRECONDITIONS: invoked by ProcessEventTime AFTER FinalizeEventTimeSecurityCensus(t) AND
                 ApplyRecoveryCompletionAfterEpilogue(t) (the T1 canonical tail); NOT dispatched from the queue.
                 T1 MUTUAL EXCLUSION: for one RecoveryEpisodeID at one event_time AT MOST ONE of the completion /
                 continuation / work hooks acts. U1: the continuation is REDISTRIBUTION-ONLY — its FINAL census shows
                 NO breach, so the floor is already met by currently ACTIVE_HASHING miners and the install only
                 re-partitions disjoint ranges; it NEVER depends on future reserve hash rate (reserve activation while
                 the floor is still breached is recovery WORK, §9c, not a continuation).
  EFFECTS:
    IF current_recovery_episode = null: RETURN nothing_due          # not in recovery (or an outcome cleared it — mutual exclusion)
    SET episode <- current_recovery_episode
    IF latest_recovery_census[episode] does NOT EXIST: RETURN nothing_due
    SET census <- latest_recovery_census[episode]
    # U4: locate the decision whose continuation due_status is DUE at t (stable order by decision_id).
    IF NO decision_id in pending_recovery_decisions[episode] WITH
       recovery_decisions[decision_id].continuation_due_status = DUE AND
       recovery_decisions[decision_id].continuation_due_at_event_time = t:
      RETURN nothing_applicable_due(t)
    SET decision_id <- that decision_id ; SET D <- recovery_decisions[decision_id]
    # T2 FRESHNESS + VERSION BINDING. Apply branch C ONLY when the decision + its ACTIVE continuation remain current
    #   AND the FINAL census at t still warrants RESTORED (census.breach = false). The bound version is READ from the
    #   AUTHORITATIVE record (continuation_bound_census_version, kept current by Reconcile rule B, T2) and COMPARED to
    #   latest_recovery_census[episode].RecoveryCensusVersion — the carried version is not silently ignored.
    IF round_state != SECURITY_RECOVERY
       OR D.status != APPLYING
       OR D.continuation_bound_census_version != census.RecoveryCensusVersion
       OR NOT outcome_consistent_with_census(RESTORED, census):
      # U4: EXPLICITLY consume the due fact as SUPERSEDED (superseded by Reconcile, or the census no longer warrants RESTORED).
      SET recovery_decisions[decision_id].continuation_due_status <- SUPERSEDED
      RECORD recovery_continuation_apply_stale_noop(decision_id)
      RETURN recovery_continuation_apply_stale(decision_id)
    # ---- FRESH + WARRANTED (census.breach = false): redistribution-only install via the named U5 plan procedures. ----
    SET pctx <- PostEpilogueSchedulingContext(source_event_time = t, source_envelope = D.continuation_due_dispatch_envelope,
                  EventQueueContext = EQ, RunContext = RoundContext.RunContext)   # U2/T7: strictly-later scheduling
    # U5: compute-only plan (verifies I1/I3/I10/I18b BEFORE any mutation). No opaque INSTALL macro.
    SET plan <- CALL PrepareRecoveryAssignmentPlan(RoundContext, episode, RANGE_REDISTRIBUTION_REQUIRED, census)
    IF plan = plan_invalid(reason):
      # U4/T5: NO mutation occurred (plan is compute-only). Consume the due fact, mark APPLY_FAILED, PRESERVE the episode.
      SET recovery_decisions[decision_id].continuation_due_status <- CONSUMED
      CALL SetRecoveryDecisionStatus(RoundContext, decision_id, APPLY_FAILED)   # R6
      REMOVE decision_id from pending_recovery_decisions[episode]
      RECORD recovery_continuation_plan_invalid(decision_id, reason)
      RETURN recovery_continuation_failed(decision_id)              # round stays SECURITY_RECOVERY (episode preserved)
    # T3: BEGIN the installation phase — a SYNCHRONOUS sub-computation; NO event boundary occurs within it, so no
    #     epilogue observes the transient ASSIGNMENT-with-active-episode state (the T3 invariant holds at every boundary).
    TRANSITION round_state -> ASSIGNMENT                            # bumps state_version (G10)
    SET recovery_install_in_progress <- true                        # T3
    SET recovery_install_seq <- recovery_install_seq + 1 ; SET RecoveryInstallID <- (episode, recovery_install_seq)
    SET active_recovery_install_decision <- decision_id             # T3
    SET commit <- CALL CommitRecoveryAssignmentPlan(RoundContext, plan, scheduling_context = POST_EPILOGUE(pctx))   # U2/U5
    IF commit = install_failed_before_mutation(reason):
      # reversible: no assignment was created. Roll BACK the state transition; consume the due fact; PRESERVE the episode.
      TRANSITION round_state -> SECURITY_RECOVERY
      SET recovery_install_in_progress <- false ; SET active_recovery_install_decision <- null
      SET recovery_decisions[decision_id].continuation_due_status <- CONSUMED
      CALL SetRecoveryDecisionStatus(RoundContext, decision_id, APPLY_FAILED)   # R6
      REMOVE decision_id from pending_recovery_decisions[episode]
      RETURN recovery_continuation_failed(decision_id)
    IF commit = install_failed_after_mutation(reason, rollback_record):
      SET rb <- CALL RollbackRecoveryAssignmentPlan(RoundContext, rollback_record)   # U5
      IF rb = rollback_completed:                                   # no live partial assignment remains (U5)
        TRANSITION round_state -> SECURITY_RECOVERY                 # rollback complete
        SET recovery_install_in_progress <- false ; SET active_recovery_install_decision <- null
        SET recovery_decisions[decision_id].continuation_due_status <- CONSUMED
        CALL SetRecoveryDecisionStatus(RoundContext, decision_id, APPLY_FAILED)   # R6
        REMOVE decision_id from pending_recovery_decisions[episode]
        RETURN recovery_continuation_failed(decision_id)            # episode preserved
      # rb = rollback_failed: an irreversible partial mutation — T4 abort (never fabricate UNRECOVERABLE).
      SET recovery_decisions[decision_id].continuation_due_status <- CANCELLED
      CALL SetRecoveryDecisionStatus(RoundContext, decision_id, APPLY_FAILED_TERMINAL)   # R6
      REMOVE decision_id from pending_recovery_decisions[episode]
      SET recovery_episode_disposition[episode] <- RECOVERY_INSTALL_FAILED_ABORTED       # T4 (NOT recovery_outcome_finalised)
      SET recovery_install_in_progress <- false ; SET active_recovery_install_decision <- null
      SET current_recovery_episode <- null
      CALL RoundAbort(RoundContext, reason = recovery_install_failed_aborted,
                      dispatch_envelope = D.continuation_due_dispatch_envelope, recovery_finalising = true)   # T4/S4
      RETURN recovery_continuation_install_aborted(decision_id)
    # commit = install_committed: run CompleteAssignmentPhase (T5 explicit disposition).
    SET disp <- CALL CompleteAssignmentPhase(RoundContext, D.continuation_due_dispatch_envelope)   # T5
    IF disp = assignment_phase_completed:                           # round now HASHING; the FINAL census confirms the floor
      # T3 exit (i): HASHING + decision APPLIED. This is the moment branch-C RESTORED is actually applied.
      SET recovery_decisions[decision_id].continuation_due_status <- CONSUMED           # U4
      CALL SetRecoveryDecisionStatus(RoundContext, decision_id, APPLIED)     # R4/R6
      SET recovery_outcome_finalised[episode] <- RESTORED                    # set ONLY on an actually-applied outcome (T4)
      REMOVE decision_id from pending_recovery_decisions[episode]
      SET recovery_install_in_progress <- false ; SET active_recovery_install_decision <- null
      SET current_recovery_episode <- null
      RETURN recovery_continuation_applied(decision_id, RESTORED)
    ELSE:  # assignment_phase_failed -> REVERSIBLE (round still ASSIGNMENT). T3 exit (ii): roll the committed plan back.
      SET rb <- CALL RollbackRecoveryAssignmentPlan(RoundContext, plan.rollback_metadata)   # U5: undo the committed install
      IF rb = rollback_failed(rr):
        # irreversible — T4 abort (never fabricate UNRECOVERABLE).
        SET recovery_decisions[decision_id].continuation_due_status <- CANCELLED
        CALL SetRecoveryDecisionStatus(RoundContext, decision_id, APPLY_FAILED_TERMINAL)
        REMOVE decision_id from pending_recovery_decisions[episode]
        SET recovery_episode_disposition[episode] <- RECOVERY_INSTALL_FAILED_ABORTED
        SET recovery_install_in_progress <- false ; SET active_recovery_install_decision <- null
        SET current_recovery_episode <- null
        CALL RoundAbort(RoundContext, reason = recovery_install_failed_aborted,
                        dispatch_envelope = D.continuation_due_dispatch_envelope, recovery_finalising = true)
        RETURN recovery_continuation_install_aborted(decision_id)
      TRANSITION round_state -> SECURITY_RECOVERY                   # rollback complete; no live partial assignment (U5)
      SET recovery_install_in_progress <- false ; SET active_recovery_install_decision <- null
      SET recovery_decisions[decision_id].continuation_due_status <- CONSUMED           # U4
      CALL SetRecoveryDecisionStatus(RoundContext, decision_id, APPLY_FAILED)   # R6
      REMOVE decision_id from pending_recovery_decisions[episode]
      RETURN recovery_continuation_failed(decision_id)
  RETURNS: recovery_continuation_applied | recovery_continuation_failed | recovery_continuation_install_aborted |
           recovery_continuation_apply_stale | nothing_due | nothing_applicable_due
  NOTE: T1..T7 + U1/U4/U5: the ONLY place branch-C RESTORED is APPLIED, run POST-epilogue so NO RESTORED result is
        recorded during the ordinary-event drain (T1). U1: the continuation is REDISTRIBUTION-ONLY (census.breach =
        false) — it never depends on future reserve hash rate (reserve activation while breached is recovery WORK, §9c;
        the impossible reserve-dependent RESTORED ELSE is REMOVED). It reads the AUTHORITATIVE continuation version and
        re-checks the final census (T2), uses the named PrepareRecoveryAssignmentPlan / CommitRecoveryAssignmentPlan /
        RollbackRecoveryAssignmentPlan (U5, no opaque INSTALL/UNDO macro), EXPLICITLY consumes the continuation due fact
        (CONSUMED / SUPERSEDED / CANCELLED, U4) before returning, uses CompleteAssignmentPhase's explicit disposition
        (T5), never fabricates UNRECOVERABLE on an irreversible install failure (T4: RECOVERY_INSTALL_FAILED_ABORTED),
        and schedules every nested wake STRICTLY LATER through the POST_EPILOGUE scheduling_context (U2/T7). Every
        installation exit ends in exactly one of: HASHING + decision APPLIED; SECURITY_RECOVERY + APPLY_FAILED (rollback
        complete, episode preserved); ROUND_ABORTED + RECOVERY_INSTALL_FAILED_ABORTED (T3/T4). Mutually exclusive with
        ApplyRecoveryCompletionAfterEpilogue and ApplyRecoveryWorkAfterEpilogue per episode per event_time (T1/U1).

PROCEDURE PrepareRecoveryAssignmentPlan                         # U5: COMPUTE-ONLY — build a deterministic recovery-assignment plan; NO mutation
  INPUTS: RoundContext, episode, work_action, census   # work_action in {RESERVE_ACTIVATION_REQUIRED, RANGE_REDISTRIBUTION_REQUIRED}
  PRECONDITIONS: round_state = SECURITY_RECOVERY (recovery work, §9c) OR round_state = ASSIGNMENT (a redistribution-only
                 continuation install, §10a). It performs NO state mutation, creates NO assignment, and seats NO event.
  EFFECTS:
    # U5: build the deterministic plan and VERIFY the structural invariants BEFORE any caller mutates. Nothing here is
    #   committed — the plan is a value the caller passes to CommitRecoveryAssignmentPlan (or discards).
    SET recovery_install_seq_preview <- recovery_install_seq + 1
    SET plan.RecoveryInstallID              <- (episode, recovery_install_seq_preview)   # matches the id the caller mints
    SET plan.source_assignment_versions     <- the immutable (AssignmentID, assignment_version) of every source range (I9)
    SET plan.accepted_unsearched_suffixes   <- the accepted_searched / active_unsearched suffixes to redistribute (I8a)
    SET plan.selected_reserve_miners        <- (work_action = RESERVE_ACTIVATION_REQUIRED ? the deterministic reserve set : empty)
    # V5/V6/W5: each spec carries the EXACT committed values so CommitRecoveryAssignmentPlan never re-SELECTs — a
    #   RESERVE_ACTIVATION spec: { kind = RESERVE_ACTIVATION, MinerID (the selected reserve miner), range (candidate_range),
    #   origin (ORIGINAL|REASSIGNED), source_assignment, reassignment_reason }; a REDISTRIBUTION spec:
    #   { kind = REDISTRIBUTION, MinerID, range, origin, source_assignment, reassignment_reason }. W5: reassignment_reason
    #   is a permitted reassignment reason (e.g. security_recovery) for a REASSIGNED origin, null for ORIGINAL. V6: a
    #   RESERVE_ACTIVATION spec is SECURITY_FLOOR_RECOVERY_WORK (it changes the ACTIVE_HASHING census); a REDISTRIBUTION
    #   spec is COVERAGE_REPAIR_WORK (nonce-domain coverage) or a no-breach branch-C redistribution — it does NOT claim to
    #   change H_active/H_honest/q_adv.
    SET plan.new_pending_assignment_specs   <- the new PENDING assignment specs (each with the exact fields above), in a STABLE creation order (by MinerID, then CandidateID)
    # W4: each spec's SINGLE implied wake is performed by its plan-bound constructor (ReserveActivateFromPlan /
    #   RangeReassignFromPlan / RangeAssignFromPlan), which returns the ACTUAL WakeEventRef. The commit path captures that
    #   one ref and NEVER seats a second wake for the same activation — there is no separate required_wake_operations loop.
    SET plan.rollback_metadata              <- an EMPTY rollback record keyed by plan.RecoveryInstallID (filled by Commit)
    # U5: VERIFY I1 (no overlap among valid active assignments), I3 (RoundID/TemplateID match), I10 (reserve activation
    #   adds no overlap), I18b (unique live head per lineage) over the PROPOSED specs — BEFORE any mutation.
    IF the proposed specs would violate I1 OR I3 OR I10 OR I18b:
      RETURN plan_invalid(reason = overlap_or_lineage_or_epoch_violation)   # U5: caller mutates NOTHING (TV168)
    RETURN plan_ready(plan)
  RETURNS: plan_ready(plan) | plan_invalid(reason)
  NOTE: U5: replaces the opaque `INSTALL the disjoint assignment set` macro's PLANNING half. It is COMPUTE-ONLY and
        verifies I1/I3/I10/I18b before any mutation, so a detected overlap creates NO assignment, NO state transition,
        and NO wake event (TV168). Determinism: the specs are in a stable creation order so event_creation_seq is reproducible.

PROCEDURE CommitRecoveryAssignmentPlan                          # U5: apply a prepared plan; thread the explicit scheduling_context
  INPUTS: RoundContext, plan, scheduling_context   # scheduling_context in SchedulingSourceContext (U2): POST_EPILOGUE(pctx) here
  PRECONDITIONS: plan produced by PrepareRecoveryAssignmentPlan (I1/I3/I10/I18b already verified compute-only). The
                 caller has entered the installation phase (round_state = ASSIGNMENT for a continuation; SECURITY_RECOVERY
                 for recovery work that only activates reserves). A POST_EPILOGUE scheduling_context is threaded to every
                 nested ScheduleEvent (U2), so every wake targets a STRICTLY LATER event_time.
  EFFECTS:
    # U5: RE-VERIFY the invariants against the CURRENT state (a concurrent same-time commit may have changed it); if a
    #   violation is detected BEFORE any assignment is created, fail cleanly with NO mutation.
    IF the plan's specs now violate I1 OR I3 OR I10 OR I18b:
      RETURN install_failed_before_mutation(reason = revalidation_failed)   # U5: nothing created
    SET created_assignments <- empty ; SET created_events <- empty
    FOR EACH spec in plan.new_pending_assignment_specs (STABLE creation order):
      # V2: scheduling_context is threaded EXPLICITLY to every constructor / wake (a POST_EPILOGUE caller's wakes are
      #   seated STRICTLY LATER). V5: the commit uses the spec's EXACT plan-selected values (MinerID / range / origin /
      #   source) — NO independent SELECT. V4: it captures the ACTUAL references the transaction returns and builds
      #   rollback_metadata from them, never from undefined fields.
      IF spec.kind = RESERVE_ACTIVATION:                                # V6: a SECURITY_FLOOR_RECOVERY_WORK spec (changes the census)
        SET r <- CALL ReserveActivateFromPlan(RoundContext, reserve_miner = spec.MinerID, candidate_range = spec.range,
                       assignment_origin = spec.origin, source_assignment = spec.source_assignment,
                       scheduling_context = scheduling_context)         # V5/V4: plan-bound; returns ACTUAL refs
        IF r = reserve_activation_committed(mid, aid, aver, wref):
          ADD aid to created_assignments ; ADD wref to created_events   # V4: ACTUAL references from the transaction
          CONTINUE
        IF r = reserve_activation_failed_before_mutation(reason):
          IF created_assignments is empty AND created_events is empty:
            RETURN install_failed_before_mutation(reason)               # V4: reversible; nothing created so far
          SET plan.rollback_metadata <- rollback_record(RecoveryInstallID = plan.RecoveryInstallID,
                created_assignments = created_assignments, created_events = created_events)
          RETURN install_failed_after_mutation(reason, plan.rollback_metadata)
        # r = reserve_activation_failed_after_assignment(reason, aid, rr): this spec ALREADY self-rolled-back (its
        #   assignment closed, miner stays RESERVE). Roll back the EARLIER specs of this install.
        IF created_assignments is empty AND created_events is empty:
          RETURN install_failed_before_mutation(reason = r.reason)      # only this spec touched, and it self-rolled-back
        SET plan.rollback_metadata <- rollback_record(RecoveryInstallID = plan.RecoveryInstallID,
              created_assignments = created_assignments, created_events = created_events)
        RETURN install_failed_after_mutation(reason = r.reason, plan.rollback_metadata)
      ELSE:  # REDISTRIBUTION spec — V6: COVERAGE_REPAIR_WORK, or a no-breach branch-C redistribution
        # W5: call the PLAN-BOUND range constructor with the spec's EXACT values (no SELECT), chosen by spec.origin.
        #   W4: it is a create-then-wake TRANSACTION that performs EXACTLY ONE wake and returns a STRUCTURED range
        #   result — the commit path CONSUMES that result and does NOT StartWake again (no double wake).
        IF spec.origin = REASSIGNED:
          SET rr <- CALL RangeReassignFromPlan(RoundContext, MinerID = spec.MinerID, range = spec.range,
                         assignment_origin = spec.origin, source_assignment = spec.source_assignment,
                         reassignment_reason = spec.reassignment_reason, lease_duration = default_lease_duration,
                         scheduling_context = scheduling_context)        # W4/W5
        ELSE:
          SET rr <- CALL RangeAssignFromPlan(RoundContext, MinerID = spec.MinerID, range = spec.range,
                         assignment_origin = spec.origin, source_assignment = spec.source_assignment,
                         reassignment_reason = spec.reassignment_reason, lease_duration = default_lease_duration,
                         scheduling_context = scheduling_context)        # W4/W5
        IF rr = range_reassigned(prov, aid, wref) OR rr = range_assigned(aid, wref, ws):
          # W5: the committed object equals the exact spec (the constructor asserts this internally too).
          ASSERT rr.AssignmentID resolves MinerID = spec.MinerID AND range = spec.range
                 AND assignment_origin = spec.origin AND source_assignment_ref = spec.source_assignment   # W5
          ADD rr.AssignmentID to created_assignments ; ADD rr.WakeEventRef to created_events   # W4: ACTUAL refs; ONE WakeCompleteEvent per activation
          CONTINUE
        IF rr = range_reassign_creation_failed(reason) OR rr = range_assign_creation_failed(reason):
          # W7: nothing was created for this spec (pre-mutation) — reversible if this is the first spec.
          IF created_assignments is empty AND created_events is empty:
            RETURN install_failed_before_mutation(reason)
          SET plan.rollback_metadata <- rollback_record(RecoveryInstallID = plan.RecoveryInstallID,
                created_assignments = created_assignments, created_events = created_events)
          RETURN install_failed_after_mutation(reason, plan.rollback_metadata)
        # rr = range_reassign_wake_failed(reason, aid) OR range_assign_wake_failed(reason, aid): the plan-bound
        #   constructor ALREADY self-rolled-back THIS spec's head (closed, ledgers restored, miner not WAKING).
        #   Roll back the EARLIER specs of this install.
        IF created_assignments is empty AND created_events is empty:
          RETURN install_failed_before_mutation(reason = rr.reason)      # only this spec touched, and it self-rolled-back
        SET plan.rollback_metadata <- rollback_record(RecoveryInstallID = plan.RecoveryInstallID,
              created_assignments = created_assignments, created_events = created_events)
        RETURN install_failed_after_mutation(reason = rr.reason, plan.rollback_metadata)
    SET plan.rollback_metadata <- rollback_record(RecoveryInstallID = plan.RecoveryInstallID,
          created_assignments = created_assignments, created_events = created_events)   # for a later CompleteAssignmentPhase-fail rollback
    RETURN install_committed
  RETURNS: install_committed | install_failed_before_mutation(reason) | install_failed_after_mutation(reason, rollback_record)
  NOTE: V5/V4/U2: replaces the opaque `INSTALL` macro's MUTATION half. It commits EXACTLY the prepared plan (the spec's
        MinerID / range / origin / source — no independent SELECT, V5), via the plan-bound ReserveActivateFromPlan and
        the redistribution constructors, threading the explicit scheduling_context (a POST_EPILOGUE caller's wakes are
        seated STRICTLY LATER). It builds rollback_metadata from the ACTUAL references the transactions return (V4), and
        distinguishes a reversible pre-mutation failure from an irreversible post-mutation one (returning a rollback record).

PROCEDURE RollbackRecoveryAssignmentPlan                        # U5: explicitly revert a partially/fully committed plan
  INPUTS: RoundContext, rollback_record   # { RecoveryInstallID, created_assignments, created_events }
  PRECONDITIONS: called by ApplyRecoveryAssignmentContinuationAfterEpilogue / ApplyRecoveryWorkAfterEpilogue on an
                 install_failed_after_mutation or a post-commit CompleteAssignmentPhase failure. It must leave NO live
                 partial assignment.
  EFFECTS:
    # U5: cancel every event the plan created, then close/remove every plan-created PENDING head LEGALLY, and restore
    #   the coverage/custody ledgers. Order: events first (so no wake can activate a head being closed), then heads.
    FOR EACH event_ref in rollback_record.created_events (stable order):
      IF event_ref is still pending on EQ: CANCEL event_ref on EQ
    FOR EACH a in rollback_record.created_assignments (stable order):
      IF a is not a live head anymore: CONTINUE                    # already superseded/closed — idempotent
      CLOSE a as CLOSED (status = CLOSED, custody_status = revoked, reason = recovery_install_rolled_back)   # J7: legal close, no live head (I18b)
      RESTORE the coverage-state / custody ledgers to their pre-plan values for a's range (I8a/I8b)
    IF any plan-created PENDING head remains live OR any created event remains pending on EQ:
      RETURN rollback_failed(reason = residual_partial_assignment)  # U5/T4: caller aborts the round (never fabricate UNRECOVERABLE)
    RETURN rollback_completed
  RETURNS: rollback_completed | rollback_failed(reason)
  NOTE: U5: replaces the opaque `UNDO the partial install` macro. It cancels every plan event, closes every plan-created
        live head legally (I18b), and restores the coverage/custody ledgers — leaving NO live partial assignment. If a
        residual partial assignment cannot be removed, it returns rollback_failed and the caller takes the declared
        RECOVERY_INSTALL_FAILED_ABORTED / RoundAbort path (T4) — it NEVER fabricates an UNRECOVERABLE outcome.

PROCEDURE FinalizePostRecoveryApplicationState                  # R2: the ONE post-application SETTLEMENT at t (NOT a 2nd floor decision)
  INPUTS: RoundContext, event_time t
  PRECONDITIONS: invoked by ProcessEventTime AFTER FinalizeEventTimeSecurityCensus(t) (the ONE epilogue) and
                 ApplyRecoveryCompletionAfterEpilogue(t); NOT dispatched from the queue; NOT a security-floor decision
  EFFECTS:
    # R2: if the recovery application did not re-dirty t, there is nothing to settle.
    IF NOT security_census_dirty[t]:
      RETURN post_recovery_settlement_noop(t)                    # no post-application census left to settle
    # R2: a post-application census exists — a RESTORED exit's applicability-entry restatement (M2), or a
    #   UNRECOVERABLE abort's off-ACTIVE_HASHING census (MINER_STATE_TRANSITION). ARCHIVE it as a
    #   terminal/post-application OBSERVATION and CLEAR the dirty flag. This is NOT SecurityFloorEvaluate:
    #   NO breach recording, NO episode/decision minting, NO transition, and NO enqueue at t (R1/R2).
    SET c <- latest_security_census[t]                           # the post-application census (from the exit transition)
    IF round_state in {ROUND_ACCEPTED, ROUND_ABORTED}:
      RECORD terminal_census_observation(t, c.H_active, c.H_honest, c.q_adv)          # R2: UNRECOVERABLE terminal observation
    ELSE:
      RECORD post_recovery_application_observation(t, round_state, c.H_active, c.H_honest, c.q_adv)   # R2: RESTORED restatement (already non-breached)
    # R5: STAMP the settlement's OWN provenance (source POST_RECOVERY_APPLICATION) over the SAME H_* values (no
    #   re-count of time/energy), so the finalised census at t names its true settlement source. CommitSecurityCensus
    #   re-sets security_census_dirty[t]; SettleSecurityCensusDirty below settles it WITHOUT a second floor decision (R2).
    CALL CommitSecurityCensus(RoundContext, t,
          census_provenance = (RoundID_current, TemplateID_committed, state_version_current),
          c.H_active, c.H_honest, c.H_adversarial, c.q_adv,
          census_source = POST_RECOVERY_APPLICATION)            # R5: post-application settlement source
    CALL SettleSecurityCensusDirty(RoundContext, t, POST_RECOVERY_APPLICATION)   # S5: the sole clearer (post-application settlement)
    RETURN post_recovery_settlement_recorded(t, round_state)
  RETURNS: post_recovery_settlement_recorded | post_recovery_settlement_noop
  NOTE: R2: the single post-application SETTLEMENT — NOT a second FinalizeEventTimeSecurityCensus. It NEVER calls
        SecurityFloorEvaluate, NEVER seats a recovery decision, and NEVER enqueues an event at t (R1). It archives
        the census the recovery application left and clears security_census_dirty[t] so t can be finalised (the
        ProcessEventTime tail then ASSERTS dirty[t] = false). For an UNRECOVERABLE application that closed the round
        it records a TERMINAL census observation; for a RESTORED exit it records a post-application observation of
        the already-non-breached census (RESTORED required census.breach = false at t), stamped
        POST_RECOVERY_APPLICATION (R5). Any NEW applicability census from actual later miner activation is generated
        at the STRICTLY LATER continuation event_time (R1/R2), never at t.
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
  INPUTS: RoundContext, assignment, time t, dispatch_envelope   # L1: this entry point's own dispatch envelope
  PRECONDITIONS: t >= lease_expiry(assignment)   # the lease window elapsed; renewal not yet decided
  EFFECTS:
    SET holder <- MinerID(assignment)
    # L4: STATUS-AWARE lease handling. Branch on the CANONICAL status (§0.8/J7) of the EXACT version whose
    #     lease expired -- NOT on miner_state alone. Each status has one explicit, terminal-correct
    #     disposition; a lease event for an ALREADY-terminal version is a stale no-op; and RangeReassign is
    #     reached ONLY after the source version is CLOSED (K6 canonical terminal; SUPERSEDED stays renewal-only).
    SWITCH status(assignment):

      CASE SUPERSEDED OR CLOSED:
        # L4: the version is ALREADY terminal -- SUPERSEDED (renewed onto a NEW CURRENT on the same lineage,
        #     which carries its OWN lease) or CLOSED (terminated). A lease-expiry event for a terminal version
        #     is STALE: its window is moot and it holds no live head. Do NOTHING (I18a/I18b untouched).
        RETURN lease_expiry_noop_terminal(status(assignment))

      CASE CURRENT:
        # E9/F7: DECIDE renewal BEFORE terminating anything. A renewed assignment is NEVER terminated and is
        #        NEVER routed through RangeReassign or WAKING -- the holder keeps hashing the SAME range.
        IF miner_state(holder) = ACTIVE_HASHING AND holder wishes to continue AND policy allows renewal:
          RETURN renewed(CALL RenewAssignment(RoundContext, assignment, t))   # F7: SUPERSEDED + new CURRENT
        # EXPIRY WITHOUT RENEWAL: the holder actually stopped. K6: NO undefined "INVALIDATE"; the canonical
        # CLOSE (status -> CLOSED, custody = expired, termination_reason = lease_expiry) is performed by the
        # SINGLE closer EnterLowPowerListen via the legal revocation edge (T27), which also moves the miner
        # off ACTIVE_HASHING. I18a/I18b hold (one live CURRENT head before, zero after).
        CALL EnterLowPowerListen(RoundContext, holder, stop_reason = ASSIGNMENT_REVOKED,
                                 assignment_ref = assignment,               # H8: the exact expiring version
                                 custody_on_close = expired, termination_reason = lease_expiry,
                                 dispatch_envelope = dispatch_envelope)   # K6 -> CLOSED (M1 envelope)

      CASE PAUSED:
        # L4: the lease expired while the head was PATH-B PAUSED (holder in LOW_POWER_LISTEN,
        #     entry_stop_reason = VALID_SOLUTION_VERIFIED). The PAUSED head is the lineage's unique live head
        #     (I18b). Terminate it canonically (CLOSED/expired/lease_expiry) WITHOUT a wake: the holder is
        #     already LOW_POWER_LISTEN, so re-classify its parked reason to ASSIGNMENT_REVOKED and clear the
        #     pause bookkeeping. NO WAKING, NO second live head, and SUPERSEDED is never used here (J7).
        ASSERT miner_state(holder) = LOW_POWER_LISTEN
               AND entry_stop_reason(holder) = VALID_SOLUTION_VERIFIED
        # M3: explicitly CANCEL any candidate-specific resume/wake events targeting THIS closed assignment, so
        #     no scheduled ResumeFromPause / WakeCompleteEvent can later re-activate the miner onto a CLOSED head.
        CANCEL every scheduled ResumeFromPause for (holder, pause_cause_candidate_id(assignment),
               pause_cause_propagation_id(assignment))
        CANCEL any scheduled WakeCompleteEvent for (holder, AssignmentID(assignment), assignment_version(assignment))
        ATOMICALLY:
          SET status(assignment)                 <- CLOSED
          SET custody_status(range(assignment))  <- expired
          SET termination_reason(assignment)     <- lease_expiry
          CLEAR pause_cause_candidate_id(assignment), pause_cause_propagation_id(assignment),
                retained_actual_frontier(assignment)
          SET entry_stop_reason(holder)          <- ASSIGNMENT_REVOKED    # its head is gone; parked reason updated

      CASE PENDING:
        # M3: EXECUTABLE PENDING lease expiry. The head is bound but not yet activated (miner WAKING or
        #     pre-wake). Resolve the pending wake and the miner state EXPLICITLY before closing/reassigning --
        #     do NOT rely on the HashWorkEvent G9 stale guard (which does not protect WakeCompleteEvent).
        # (1)-(2) M3: identify and CANCEL the exact pending WakeCompleteEvent for this head BEFORE closing.
        CANCEL the scheduled WakeCompleteEvent for (holder, AssignmentID(assignment), assignment_version(assignment))
        # (3) M3: if the holder is WAKING for THIS head, resolve it OFF WAKING via the legal edge (T12) with the
        #     exact dispatch_envelope; a pre-wake holder (REGISTERED/RESERVE/LOW_POWER_LISTEN) needs no edge.
        IF miner_state(holder) = WAKING AND target_assignment(holder) = assignment:
          CALL ApplyMinerStateTransition(holder, WAKING, OFFLINE,
                 transition_envelope = dispatch_envelope, reason = lease_expired_while_waking,   # S1: ONE envelope object
                 assignment_ref = assignment, candidate_id = null, propagation_id = null)   # T12 (M3/M1)
        # (4)-(5) M3: CLOSE the PENDING head canonically and PRESERVE accepted coverage (the accepted searched
        #     prefix is untouched; only the accepted unsearched suffix is exposed by the common tail, step (6)).
        PRESERVE accepted searched prefix [range_start(assignment), accepted_frontier(assignment)]
        ATOMICALLY:
          SET status(assignment)                 <- CLOSED
          SET custody_status(range(assignment))  <- expired
          SET termination_reason(assignment)     <- lease_expiry

    # ---- COMMON REASSIGN TAIL (reached ONLY for CURRENT-without-renewal / PAUSED / PENDING; the renewal and
    #      terminal-no-op cases RETURNed above). The source version is now CLOSED, so RangeReassign's
    #      status(source) = CLOSED precondition (L4) is met. ----
    ASSERT status(assignment) = CLOSED                             # L4: reassign only a CLOSED source's suffix
    # C4: reassign ONLY the accepted unsearched suffix, never the searched prefix.
    IF accepted_frontier(range(assignment)) = range_end:
      RETURN released_nothing_to_reassign                          # range complete; nothing unsearched
    IF no accepted positions exist for range(assignment):
      SET reassignable_suffix <- whole range(assignment)          # [range_start, range_end]
    ELSE:
      SET reassignable_suffix <- [accepted_frontier(range(assignment)) + 1, range_end]
    MARK reassignable_suffix as inactive_unsearched / reassignable  # supports I8a (unsearched only)
    SET rr <- CALL RangeReassign(RoundContext, reassignable_suffix,
                     reason = lease_expiry, from_miner = holder,
                     scheduling_context = ORDINARY_DISPATCH(dispatch_envelope))   # V2: explicit context (L1 envelope); L4: source is CLOSED
    IF rr = range_reassigned(...): RETURN released                # V3/V9: inspect the disposition — the suffix was reassigned and its wake seated
    RETURN released_reassign_wake_failed(reason = rr)             # V3/V9: RangeReassign rolled back the failed wake; the suffix stays reassignable
  RETURNS: lease_disposition (renewed | released | released_reassign_wake_failed | released_nothing_to_reassign | lease_expiry_noop_terminal)
  NOTE: L4/M3: LeaseExpiry is STATUS-AWARE. SUPERSEDED/CLOSED -> stale no-op; CURRENT -> renew (F7) or CLOSE
        via EnterLowPowerListen (K6) then reassign; PAUSED -> cancel candidate-specific resume/wake events then
        CLOSE the paused head without a wake then reassign (M3); PENDING -> EXECUTABLE: cancel the exact pending
        WakeCompleteEvent, resolve a WAKING holder off WAKING (T12, reason = lease_expired_while_waking) with the
        exact dispatch_envelope, CLOSE the un-activated head, then reassign (M3). Renewal preserves a valid
        CURRENT assignment on the SAME range with retained progress/provenance and NO wake cycle (E9); a renewal
        NEVER changes the range (E5). Every reassignment path CLOSES the source FIRST, so RangeReassign always
        sees status(source) = CLOSED (L4). SUPERSEDED remains renewal-only (J7). The WakeCompleteEvent stale
        guard (M3, §0.10) is the independent backstop; the HashWorkEvent G9 guard does NOT protect wakes.
```

## 13. Range reassignment

```
PROCEDURE RangeReassign
  INPUTS: RoundContext, unsearched_suffix, reason, from_miner,
          scheduling_context   # U2: SchedulingSourceContext — ORDINARY_DISPATCH(dispatch_envelope) for a dispatched
                               #   caller, or POST_EPILOGUE(pctx) when CommitRecoveryAssignmentPlan calls it (§9c/§10a)
  PRECONDITIONS: # C4: the caller passes the EXACT accepted unsearched suffix, not a full range:
                 unsearched_suffix = [accepted_frontier(source) + 1, range_end(source)]
                   OR (no accepted positions exist AND unsearched_suffix = whole source range);
                 # CR-B5: exhaustion is NOT a reassignment reason; permitted reasons are exactly:
                 reason in {lease_expiry, abandonment, revocation, departure, conflict, security_recovery};
                 custody_status(unsearched_suffix) != completed;   # a completed range is NOT reassignable
                 coverage_state(unsearched_suffix) != searched;    # no searched prefix is included
                 # L4: the source version must ALREADY be terminal. A suffix is reassigned ONLY after its
                 #     source lineage head reached CLOSED (K6 canonical terminal) -- never while a live
                 #     CURRENT/PAUSED/PENDING head still holds it, and never from a SUPERSEDED renewal head (J7).
                 status(source_assignment(unsearched_suffix)) = CLOSED
  EFFECTS:
    # CR-B5 + C4: only the accepted unsearched suffix is reassigned; a searched prefix or a completed range is NEVER
    #   reassignable. W5: the ORDINARY entry point checks the reassignment preconditions and SELECTS the to_miner, then
    #   delegates the EXACT-values create-then-wake mutation to the plan-bound RangeReassignFromPlan.
    ASSERT custody_status(unsearched_suffix) != completed
    ASSERT coverage_state(unsearched_suffix) != searched
    ASSERT unsearched_suffix contains no accepted searched position   # C4: suffix only
    ASSERT status(source_assignment(unsearched_suffix)) = CLOSED      # L4: reassign only a CLOSED source's suffix
    SELECT to_miner from {RESERVE, REGISTERED} miners (or via ReserveActivate)
    RETURN CALL RangeReassignFromPlan(RoundContext, MinerID = to_miner, range = unsearched_suffix,
                     assignment_origin = REASSIGNED, source_assignment = source_assignment(unsearched_suffix),
                     reassignment_reason = reason, lease_duration = default_lease_duration,
                     scheduling_context = scheduling_context)   # W5
  RETURNS: range_reassigned(provenance, AssignmentID, WakeEventRef) |
           range_reassign_creation_failed(reason) | range_reassign_wake_failed(reason, AssignmentID)
  NOTE: W5: RangeReassign checks the C4/L4 reassignment preconditions, SELECTS the to_miner, and delegates the atomic
        create-then-wake to RangeReassignFromPlan; it never performs the mutation itself and returns that constructor's
        structured disposition unchanged.

PROCEDURE RangeReassignFromPlan                                 # W5: plan-bound create-then-wake reassignment; EXACT values, NO SELECT
  INPUTS: RoundContext, MinerID, range, assignment_origin, source_assignment, reassignment_reason,
          lease_duration, scheduling_context   # W5: the caller's EXACT validated spec fields (no independent SELECT)
  PRECONDITIONS: miner_state(MinerID) in {REGISTERED, RESERVE}; range = an accepted unsearched suffix whose source is
                 CLOSED (L4/C4), with the caller's EXACT validated provenance; round_state = ASSIGNMENT or HASHING or
                 SECURITY_RECOVERY. It performs NO SELECT.
  EFFECTS:
    # W7: build the REASSIGNED PENDING head via the shared constructor (I1 overlap guard + ledger + custody = reassigned
    #   + I9 provenance) and BRANCH on its explicit result BEFORE reading AssignmentID or setting lease fields.
    SET cr <- CALL CreatePendingAssignment(RoundContext, MinerID, range,
                    assignment_origin = assignment_origin, source_assignment = source_assignment, reason = reassignment_reason)
    IF cr is assignment_creation_failed(reason):
      RETURN range_reassign_creation_failed(reason = reason)            # W7: nothing created; no AssignmentID exists
    SET assignment <- cr.assignment                                     # W7: cr = assignment_created(assignment)
    ASSERT MinerID(assignment) = MinerID AND range(assignment) = range
           AND assignment_origin(assignment) = assignment_origin
           AND source_assignment_ref(assignment) = source_assignment    # W5
    SET lease_start(assignment)  <- now
    SET lease_expiry(assignment) <- now + lease_duration
    # F5/D2/V3: to_miner activation passes through WAKING via the NON-BLOCKING StartWake TRANSACTION (T3/T4 -> T5). ONE wake.
    SET fs <- miner_state(MinerID)   # V3: capture from_state so a failed wake can be asserted / rolled back
    SET wr <- CALL StartWake(RoundContext, MinerID, target_assignment = assignment,
                     from_state = fs,
                     scheduling_context = scheduling_context)   # V2/V3: explicit context; STRUCTURED result
    IF wr != wake_seated(...):
      # V3/V9: the wake FAILED after the REASSIGNED PENDING head was created. StartWake left the miner in fs (never
      #   WAKING) and cancelled any seated event; ROLL BACK the un-activated head legally so the suffix stays reassignable.
      IF wr = wake_transition_failed_after_seat(reason2, wref):
        IF wref is still pending on EQ: CANCEL wref on EQ            # idempotent; StartWake already cancelled
      CLOSE assignment as CLOSED (status = CLOSED, custody_status = revoked, reason = range_reassign_wake_failed)   # J7/I18b
      RESTORE the coverage-state / custody ledgers for range (I8a/I8b) so it remains reassignable
      ASSERT miner_state(MinerID) = fs                             # V3/gate 4: the miner is not left WAKING
      RETURN range_reassign_wake_failed(reason = wr, AssignmentID = AssignmentID(assignment))   # V3/V9: structured failure
    SET wref <- wr.WakeEventRef
    # CR4/C3: coverage uses I8a with ACCEPTED coverage; custody/provenance is tracked SEPARATELY as I8b.
    UPDATE assignment_ledger so the coverage partition still holds (I8a):
        accepted_searched + active_unsearched + inactive_unsearched = assigned_domain
    # I8b custody/lineage status is orthogonal and is NEVER an additive coverage term. The reassigned
    # suffix retains an INDEPENDENT coverage state (accepted_searched/active_unsearched/inactive_unsearched).
    RETURN range_reassigned(provenance = provenance(assignment),
                            AssignmentID = AssignmentID(assignment), WakeEventRef = wref)   # V3/V9: structured
  RETURNS: range_reassigned(provenance, AssignmentID, WakeEventRef) |
           range_reassign_creation_failed(reason) | range_reassign_wake_failed(reason, AssignmentID)
  NOTE: W5/W7: the plan-bound create-then-wake reassignment. It uses the EXACT spec values (no SELECT), branches on the
        CreatePendingAssignment result BEFORE any AssignmentID access (W7), asserts the committed object equals the spec
        (W5), performs EXACTLY ONE StartWake, and returns a structured disposition. On a wake failure it closes the
        un-activated head legally and restores the ledgers so the suffix stays reassignable and no orphan PENDING remains.
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
  INPUTS: RoundContext, certificate, snapshot, CandidateID, PropagationID, verifying_MinerID, dispatch_envelope
  PRECONDITIONS: round_state in {HASHING, SOLUTION_PROPAGATION, SECURITY_RECOVERY};
                 miner_state(verifying_MinerID) = ACTIVE_HASHING;      # F2: a paused miner never re-verifies
                 # M1: dispatch_envelope is the envelope of the dispatched CertificateArrival that called here.
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
                               pause_cause_propagation_id = PropagationID,
                               dispatch_envelope = dispatch_envelope)   # M1: threaded envelope
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
  INPUTS: RoundContext, MinerID, trigger, pause_cause_candidate_id, pause_cause_propagation_id,
          dispatch_envelope   # L1: threaded envelope (from ProcessEventTime when dispatched as a queued
                              #     event; from the synchronous caller — AdversarialParticipationChangeEvent —
                              #     when called directly). NEVER manually stamped.
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
    SET wr <- CALL StartWake(RoundContext, MinerID, target_assignment = paused_assignment,
                          from_state = LOW_POWER_LISTEN,
                          scheduling_context = ORDINARY_DISPATCH(dispatch_envelope))   # V2/V3: explicit context; structured result
    IF wr = wake_seated(waid, wref, wtt, ws): RETURN resume_started(MinerID, resumed_from = retained_actual_frontier, WakeEventRef = wref)   # V3
    RETURN resume_wake_failed(MinerID, reason = wr)   # V3: StartWake failed -> the miner is not left WAKING (StartWake guarantees it)
  RETURNS: resume_started(MinerID, resumed_from, WakeEventRef) | resume_wake_failed(MinerID, reason)
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
  INPUTS: RoundContext, certificate, snapshot, finder, dispatch_envelope   # M1: threaded envelope
  PRECONDITIONS: round_state in {HASHING, SOLUTION_PROPAGATION, SECURITY_RECOVERY};
                 certificate produced by EarlyStopGenerate from a found valid solution + snapshot;
                 # M1: dispatch_envelope is the envelope of the dispatched HashWorkEvent that found the solution.
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
    IF was_empty AND round_state = HASHING:
      # M2/K7: HASHING -> SOLUTION_PROPAGATION through the round-state helper, which captures the
      #        applicability-entry census automatically at dispatch_envelope.event_time.
      CALL TransitionRoundState(RoundContext, SOLUTION_PROPAGATION, dispatch_envelope)   # M2 (+ K7 capture)
    # C6/F1/G7: schedule per-recipient certificate-arrival events in a STABLE SORTED order (by MinerID);
    #           each event carries CandidateID/PropagationID (F1/G11) and its target microphase (M5).
    FOR EACH recipient r in SORT({ m in current miners : m != finder } BY MinerID ascending):
      cert_delay(r) <- deterministic modeled propagation delay(finder -> r)   # reproducible
      ev <- CALL ScheduleEvent(EQ, RoundContext, CertificateArrival,
                               target_event_time = now + cert_delay(r), target_microphase = CERTIFICATE_ARRIVAL,
                               {r, cpc.certificate, cpc.snapshot, CandidateID = cpc.CandidateID,
                                PropagationID = cpc.PropagationID})   # M5: explicit microphase
      ADD ev to certificate_arrival_events(cpc)
    # schedule the full-block acceptance event toward the modeled acceptance point (carries the ids).
    block_delay <- deterministic modeled propagation delay(finder -> acceptance_point)  # reproducible
    SET block_arrival_event(cpc) <- CALL ScheduleEvent(EQ, RoundContext, BlockAcceptancePoint,
                          target_event_time = now + block_delay, target_microphase = FULL_BLOCK_ARRIVAL,
                          {cpc.certificate, cpc.snapshot, CandidateID = cpc.CandidateID,
                           PropagationID = cpc.PropagationID, outcome = outcome-at-arrival})   # M5: explicit microphase
    # (5) the finder ceases hashing (PATH B), recording THIS candidate (BOTH ids) as its pause cause (F2/G11).
    CALL EnterLowPowerListen(RoundContext, finder, stop_reason = VALID_SOLUTION_VERIFIED,
                             assignment_ref = version(cpc.snapshot.AssignmentID, cpc.snapshot.assignment_version),  # H8: exact discovery version (CURRENT for the finder now)
                             pause_cause_candidate_id = cpc.CandidateID,
                             pause_cause_propagation_id = cpc.PropagationID,
                             dispatch_envelope = dispatch_envelope)   # M1: threaded envelope
  RETURNS: cpc.CandidateID
  NOTE: G6: status flows DISCOVERED -> SELF_VALIDATED -> PROPAGATING here; PENDING_ACCEPTANCE is set
        when the block arrival REGISTERS at the acceptance point (BlockAcceptancePoint, G5). The set
        holds ONLY PROPAGATING/PENDING_ACCEPTANCE contexts. Do NOT accept here. Further candidates each
        get their OWN context (F1/F3).
```

## 16c. Certificate arrival at a recipient (C6)

```
PROCEDURE CertificateArrival
  INPUTS: RoundContext, recipient r, certificate, snapshot, CandidateID, PropagationID, dispatch_envelope
  PRECONDITIONS: this is the scheduled certificate-arrival event for r (carries CandidateID/PropagationID, F1);
                 the context CandidateID is still live (not FAILED/ACCEPTED/CANCELLED);
                 # M1: dispatch_envelope = this dispatched CertificateArrival's own envelope, threaded to EarlyStopVerify.
  EFFECTS:
    # F2/F3: ignore an arrival whose candidate is no longer live (its events may have been cancelled).
    IF status(context(CandidateID)) not in {PROPAGATING, PENDING_ACCEPTANCE}:
      RETURN ignored_stale_candidate
    # (6) the recipient stays ACTIVE_HASHING until its certificate-arrival event fully validates.
    #     E1/E2: verification is against the finder's immutable discovery snapshot, carried on the event.
    IF miner_state(r) = ACTIVE_HASHING:
      result <- CALL EarlyStopVerify(RoundContext, certificate, snapshot,
                                     CandidateID, PropagationID, verifying_MinerID = r,
                                     dispatch_envelope = dispatch_envelope)   # M1: threaded envelope
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
  INPUTS: RoundContext, CandidateID, PropagationID, failure_reason, dispatch_envelope   # M1: threaded envelope
  PRECONDITIONS: failure_reason in {REJECTED, BLOCK_UNAVAILABLE, PROPAGATION_TIMEOUT, NO_VALID_CANDIDATE};
                 CandidateID identifies a live context (status in {PROPAGATING, PENDING_ACCEPTANCE});
                 # M1: dispatch_envelope is threaded from AcceptanceBatchFinalize (the dispatched handler).
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
      # M5: schedule the candidate-scoped resume through ScheduleEvent with an explicit target microphase.
      #     dispatch_envelope for this ResumeFromPause is supplied by ProcessEventTime when the scheduled
      #     event is DISPATCHED (its own enqueued envelope); it is NOT part of the event payload here.
      CALL ScheduleEvent(EQ, RoundContext, ResumeFromPause,
                         target_event_time = dispatch_envelope.event_time, target_microphase = RESUME,
                         {M, trigger = failure_reason, pause_cause_candidate_id = CandidateID,
                          pause_cause_propagation_id = PropagationID})   # G11: both ids; M5 explicit microphase
    # (3) J1: the candidate failure per se changes no ACTIVE_HASHING census (it only SCHEDULEs candidate-scoped
    #     resume events); those resumes later re-activate miners via ApplyMinerStateTransition (the SOLE hook
    #     writer), which sets dirty + coherent latest census together at their OWN event_time.
    # (4) round-state rule (F3/G8): return to HASHING ONLY when propagation is FULLY quiescent AND the round
    #     is still in SOLUTION_PROPAGATION. During SECURITY_RECOVERY the round stays in recovery (live
    #     candidates preserved, G8); the EXECUTABLE floor-restored exit CompleteSecurityRecovery (§10a/R13)
    #     later returns it to SOLUTION_PROPAGATION (live candidates) or HASHING.
    # M2: the SOLUTION_PROPAGATION -> HASHING RE-ENTRY is a floor-applicable entry, so it is performed through
    #     the round-state helper, which captures the applicability-entry census at dispatch_envelope.event_time.
    #     This capture is REQUIRED even when no miner was paused, all resumes carry positive wake latency, or
    #     H_active did not change at this exact transition -- so the epilogue evaluates the floor on HASHING
    #     re-entry. It is NOT routed through CompleteAssignmentPhase (that owns the ASSIGNMENT -> HASHING edge,
    #     whose precondition is round_state = ASSIGNMENT); both edges nonetheless capture the census (M2).
    IF round_state = SOLUTION_PROPAGATION AND propagation_quiescent(RoundContext):
      CALL TransitionRoundState(RoundContext, HASHING, dispatch_envelope)   # M2: re-entry + applicability census
    # ELSE: the round STAYS SOLUTION_PROPAGATION (other candidates live) or SECURITY_RECOVERY (G8).
    RETURN candidate_failed(CandidateID)
  RETURNS: candidate_failed
  NOTE: Candidate-scoped (F2/F3/G11 on BOTH ids). One candidate's failure NEVER cancels or resumes
        another candidate's events or paused miners. The round remains SOLUTION_PROPAGATION while any
        live candidate exists (F3), and SECURITY_RECOVERY may coexist with live candidates (G8).
        M2: when the failure makes propagation quiescent and returns the round to HASHING, the round-state
        helper captures a coherent applicability-entry census on that HASHING entry (required regardless of
        whether any miner was paused or H_active changed), so a floor breach at that entry is decided by the
        epilogue. The candidate failure itself sets no dirty flag directly (J1). No block is accepted and no
        round is closed here. `propagation_quiescent` is defined in §0.6.
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
  INPUTS: RoundContext, acceptance_timestamp, acceptance_point, dispatch_envelope   # M1: this handler's envelope
  PRECONDITIONS: microphase 4 for (acceptance_timestamp, acceptance_point); runs EXACTLY ONCE for it,
                 AFTER microphase 3 has collected ALL same-timestamp block arrivals (G5);
                 # M1: dispatch_envelope threaded to ValidBlockAccept and HandlePropagationFailure.
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
      CALL ValidBlockAccept(RoundContext, winner.CandidateID, winner.certificate, winner.snapshot,
                            dispatch_envelope = dispatch_envelope)   # M1: threaded envelope
    ELSE:
      # (4) no valid winner at this timestamp -> fail EACH accepted-but-invalid candidate candidate-scoped
      #     (each resumes ONLY its own paused miners; G5/F2). No cross-candidate cancellation.
      FOR EACH a in accepted:
        CALL HandlePropagationFailure(RoundContext, a.CandidateID, a.PropagationID,
                                      failure_reason = NO_VALID_CANDIDATE, dispatch_envelope = dispatch_envelope)   # M1
    # (5) disposition the non-accept arrivals candidate-scoped -- a no-op if the round already closed (2)-(3).
    FOR EACH a in failed:
      IF round_state not in {ROUND_ACCEPTED, ROUND_ABORTED}:
        CALL HandlePropagationFailure(RoundContext, a.CandidateID, a.PropagationID,
                                      failure_reason = a.outcome, dispatch_envelope = dispatch_envelope)   # M1
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
  INPUTS: RoundContext, winner_CandidateID, winner_certificate, winner_snapshot, dispatch_envelope   # M1
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
    CALL CloseRoundAssignments(RoundContext, disposition = ROUND_ACCEPTED, stop_reason = ROUND_ACCEPTED,
                               dispatch_envelope = dispatch_envelope)   # M1: threaded envelope
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
  INPUTS: RoundContext, disposition (ROUND_ACCEPTED | ROUND_ABORTED), stop_reason, dispatch_envelope,   # M1
          recovery_finalising = false   # S4: true ONLY when this closure IS the recovery-finalising abort (branch D /
                                        #     the continuation's declared install-fail abort); then S4 cleanup is SKIPPED.
  PRECONDITIONS: disposition in {ROUND_ACCEPTED, ROUND_ABORTED}; stop_reason = disposition;
                 # M1/R3: the COMPLETE dispatch_envelope (envelope_namespace, event_time, delta_cycle, event_seq,
                 #     hook_id) is threaded to every EnterLowPowerListen and ApplyMinerStateTransition below. At the
                 #     horizon close (§20b) that envelope is the RUN_HOOK one (envelope_namespace = RUN_HOOK,
                 #     hook_id = HorizonHookID); its namespace + hook_id are PRESERVED through to every nested miner
                 #     transition (R3/gate 6), so each nested transition's TransitionEventID carries them.
  EFFECTS:
    # D7/E7: the SINGLE round-closure path. It records a round_closure_disposition (how the ROUND
    #        ended) that is SEPARATE from a miner's entry_stop_reason (why the miner earlier LEFT
    #        ACTIVE_HASHING). Closure NEVER overwrites an existing RANGE_EXHAUSTED or
    #        VALID_SOLUTION_VERIFIED entry reason. Every holder state has an EXPLICIT action below;
    #        there is NO generic "update state consistently" step.
    # M5: iterate in STABLE order (holder MinerID, then AssignmentID) so every EnterLowPowerListen /
    #     ApplyMinerStateTransition / event cancellation below is deterministic before seq assignment (G7/J4).
    FOR EACH open assignment X under the closing RoundID/TemplateID
        IN SORT BY (holder(X) MinerID ascending, AssignmentID(X) ascending):
      SET h <- holder(X)
      PRESERVE coverage_state(X), custody_status(X), provenance history   # closure changes no coverage
      SET round_closure_disposition(X) <- disposition            # E7: separate from entry_stop_reason
      # do NOT reassign X under the closed TemplateID; do NOT mark any unfinished range exhausted
      SWITCH miner_state(h):

        CASE ACTIVE_HASHING:
          # still hashing with NO prior stop reason: closure IS this miner's stop event, so the
          # round disposition legitimately becomes its entry_stop_reason (5th EnterLowPowerListen reason).
          CALL EnterLowPowerListen(RoundContext, h, stop_reason = disposition, assignment_ref = X,
                 dispatch_envelope = dispatch_envelope)   # H8: exact version; sets entry_stop_reason(h) <- disposition; closes X (M1)

        CASE EXHAUSTED_PENDING:
          # PATH-A holder mid-completion: entry_stop_reason is already RANGE_EXHAUSTED. PRESERVE it.
          ASSERT entry_stop_reason(h) = RANGE_EXHAUSTED
          CLOSE X as round-ended                                 # completed range stays searched/completed
          CALL ApplyMinerStateTransition(h, EXHAUSTED_PENDING, LOW_POWER_LISTEN,
                 transition_envelope = dispatch_envelope,   # S1: ONE envelope object (RUN_HOOK+HorizonHookID at horizon close)
                 reason = RANGE_EXHAUSTED, assignment_ref = X, candidate_id = null, propagation_id = null)   # T8 (M1/S1); RANGE_EXHAUSTED NOT overwritten

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
          CALL ApplyMinerStateTransition(h, WAKING, OFFLINE,
                 transition_envelope = dispatch_envelope,   # S1: ONE envelope object (RUN_HOOK+HorizonHookID at horizon close)
                 reason = round_closed_while_waking,
                 assignment_ref = X, candidate_id = null, propagation_id = null)       # T12 (M1/S1); miner rejoins next round via T17

        CASE REGISTERED OR RESERVE:
          # holds no CURRENT range under this round; nothing to stop and nothing to resume.
          IF X is a bound PENDING assignment: CLOSE X as round-ended
          # miner_state(h) unchanged (REGISTERED stays REGISTERED; RESERVE stays RESERVE)

        CASE OFFLINE OR DISQUALIFIED:
          # not participating: close the assignment record only.
          CLOSE X as round-ended
          # miner_state(h) unchanged (OFFLINE stays OFFLINE; DISQUALIFIED stays DISQUALIFIED)
    # cancel pending events belonging to the closed round (G9: including HashWorkEvents; G5: clear the
    # acceptance batch registry so no stale batch finalizes after closure; S4: including the recovery-timeline events).
    CANCEL all pending wake / resume / certificate-arrival / BlockAcceptancePoint / HashWorkEvent /
           AdversarialParticipationChangeEvent / RecoveryDeadlineEvent / RecoveryCompletionDueEvent /
           RecoveryAssignmentContinuationDueEvent / RecoveryWorkDueEvent events for RoundID   # S4/T1/U1: recovery-timeline events cancelled at closure
    CLEAR active_propagation_set                                # no live candidate survives closure
    CLEAR acceptance_batch_registry                             # no pending batch survives closure
    # S4 TERMINAL RECOVERY CLEANUP. If a recovery episode is STILL ACTIVE and this closure is NOT the
    #   recovery-finalising abort (which finalises the episode itself), cancel the episode: mark every
    #   pending/applying decision CANCELLED, record TERMINAL_CANCELLED, and clear current_recovery_episode — so a
    #   terminal round NEVER leaves an active recovery episode (S4 invariant). recovery_outcome_finalised is NOT set.
    IF current_recovery_episode != null AND NOT recovery_finalising:
      CALL CancelActiveRecoveryEpisode(RoundContext, dispatch_envelope)   # S4
    RECORD round_closure(RoundID, TemplateID, disposition)
    # M4: CloseRoundAssignments performs NO residency/energy finalisation. The earlier executable line
    #     `finalise state durations and energy to the EXACT closure time` is REMOVED: it competed with the
    #     single residency-boundary owner. The ONLY residency close/reopen at a round boundary is performed by
    #     SettleResidencyBoundary (§1a), idempotently via boundary_id (L5/M4). CloseRoundAssignments records
    #     `round_terminal_time` ONLY; the next round's RoundInitialise (or the final-run settle) reads it.
    RECORD round_terminal_time(RoundID) <- dispatch_envelope.event_time   # M4/L5: boundary_time for SettleResidencyBoundary
  RETURNS: closure_record
  NOTE: This is the ONLY round-closure path. ValidBlockAccept calls it with ROUND_ACCEPTED;
        RoundAbort calls it with ROUND_ABORTED. Only an ACTIVE_HASHING holder receives the
        disposition as its entry_stop_reason (it had none); every already-stopped holder keeps its
        recorded entry_stop_reason and merely records a SEPARATE round_closure_disposition (E7). No
        range is marked exhausted by closure, and nothing is reassigned under the closed TemplateID.
  NOTE: M4/L5: CloseRoundAssignments records `round_terminal_time` ONLY and performs NO residency/energy
        finalisation. The cross-round residency close/reopen is performed EXCLUSIVELY by SettleResidencyBoundary
        (§1a), idempotently via boundary_id, so the idle interval between this closure and the next round's
        StartWake (or the final-run horizon) is counted EXACTLY ONCE (I19).
```

## 18. Full-range exhaustion without solution

```
PROCEDURE FullRangeExhaustNoSolution
  INPUTS: RoundContext, dispatch_envelope   # L1: this entry point's own dispatch envelope (threaded onward)
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
          RETURN CALL RoundAbort(RoundContext, reason=false_exhaustion_claim, dispatch_envelope = dispatch_envelope)   # M1
    TRANSITION round_state -> ROUND_EXHAUSTED
    RECORD zero_block_outcome(RoundID, TemplateID)              # retained (I14)
    MARK block-normalised metrics for this round as NA          # I15
    IF policy = continue_mining:
      RETURN CALL TemplateRefresh(RoundContext, dispatch_envelope = dispatch_envelope)   # L1: threaded envelope
    ELSE:
      RETURN CALL RoundAbort(RoundContext, reason=exhausted_no_solution, dispatch_envelope = dispatch_envelope)   # M1
  RETURNS: disposition (refresh | abort)
```

## 19. Template refresh

```
PROCEDURE CloseTemplateAssignments
  INPUTS: RoundContext, old_TemplateID, dispatch_envelope   # M1: threaded envelope
  PRECONDITIONS: round_state = TEMPLATE_REFRESH; a new template is about to be committed;
                 # M1: dispatch_envelope threaded to every EnterLowPowerListen and ApplyMinerStateTransition below.
  EFFECTS:
    # E8: template-scoped closure of EVERY assignment under the OLD TemplateID. The ROUND CONTINUES
    #     (this is NOT round closure); coverage/provenance history is PRESERVED, never deleted. Each
    #     holder is routed off the old template ONLY through its LEGAL per-state edge (no illegal
    #     direct transitions), so template refresh never fabricates a transition.
    # M5: iterate in STABLE order (holder MinerID, then AssignmentID) so every EnterLowPowerListen /
    #     ApplyMinerStateTransition / event cancellation below is deterministic before seq assignment (G7/J4).
    FOR EACH open assignment X under old_TemplateID
        IN SORT BY (holder(X) MinerID ascending, AssignmentID(X) ascending):
      SET h <- holder(X)
      PRESERVE historical coverage_state(X), custody_status(X), provenance/reassignment records
      SET custody_status(range(X)) <- superseded_by_template_refresh   # I8b lineage marker (historical)
      SWITCH miner_state(h):
        CASE ACTIVE_HASHING:
          # the old-template assignment is revoked because the template changed (legal T27).
          CALL EnterLowPowerListen(RoundContext, h, stop_reason = ASSIGNMENT_REVOKED,
                                   assignment_ref = X, dispatch_envelope = dispatch_envelope)   # H8; -> LOW_POWER_LISTEN (M1)
        CASE EXHAUSTED_PENDING:
          # PATH-A holder: finish the exhaustion drop (legal T8); entry_stop_reason RANGE_EXHAUSTED kept.
          CLOSE X
          CALL ApplyMinerStateTransition(h, EXHAUSTED_PENDING, LOW_POWER_LISTEN,
                 transition_envelope = dispatch_envelope,   # S1: ONE envelope object
                 reason = RANGE_EXHAUSTED, assignment_ref = X, candidate_id = null, propagation_id = null)     # T8 (F6/M1)
        CASE LOW_POWER_LISTEN:
          # a PAUSED PATH-B assignment is CLOSED (it is NOT resumed under a discarded template).
          CLOSE X
          # miner_state(h) stays LOW_POWER_LISTEN; entry_stop_reason(h) unchanged; no transition
        CASE WAKING:
          # the bound assignment is on the discarded template -> fails TemplateID validation (legal T12).
          CANCEL the pending WakeCompleteEvent for h ; release the bound range
          CALL ApplyMinerStateTransition(h, WAKING, OFFLINE,
                 transition_envelope = dispatch_envelope, reason = template_refresh_wake_abort,   # S1: ONE envelope object
                 assignment_ref = X, candidate_id = null, propagation_id = null)                               # T12 (F6/M1)
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
  INPUTS: RoundContext, dispatch_envelope   # L1: threaded from FullRangeExhaustNoSolution's dispatch envelope
  PRECONDITIONS: round_state in {ROUND_EXHAUSTED, HASHING(systemic template disagreement)};
                 # L1: dispatch_envelope is threaded from the dispatched caller; NO manual seq stamping.
  EFFECTS:
    # D8/E8: correct round-state sequencing so TemplateCommit ALWAYS runs from TEMPLATE_COMMITMENT;
    #        TEMPLATE_REFRESH NEVER bypasses TEMPLATE_COMMITMENT.
    TRANSITION round_state -> TEMPLATE_REFRESH                  # from ROUND_EXHAUSTED or HASHING
    # E8-(1)/(2): close ALL old-template assignments via the EXPLICIT procedure; history preserved.
    CALL CloseTemplateAssignments(RoundContext, old_TemplateID = TemplateID_current,
                                  dispatch_envelope = dispatch_envelope)   # M1: threaded envelope
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
    # W1/W3/V8: initialise the refresh setup TRANSACTION BEFORE the miner loop, carrying an IMMUTABLE rollback_envelope
    #   (this refresh's own dispatch_envelope: { envelope_namespace, event_time, delta_cycle, event_seq, hook_id }).
    #   Every created AssignmentID, prior miner state, and StartWake WakeEventRef is captured by EXPLICIT statements
    #   INSIDE the loop — NEVER reconstructed afterward from prose.
    SET refresh_setup_txn <- setup_transaction(rollback_envelope = dispatch_envelope,
          wakes = empty, created_assignments = empty, prior_states = empty)   # W1/W3
    SET refresh_setup_error <- null   # W3: set on a CreatePendingAssignment or StartWake failure; checked after the loop
    # M5: iterate in STABLE MinerID order so the StartWake events this loop produces are scheduled in a
    #     deterministic order BEFORE ScheduleEvent assigns event_creation_seq (G7/J4).
    FOR EACH miner m IN SORT(eligible BY MinerID ascending):
      IF refresh_setup_error != null: BREAK    # W3: once the refresh has failed, mint NO further work; roll back below
      # E8-(6)/F4/W7: a FRESH ORIGINAL assignment over the NEW domain via the shared constructor; BRANCH on its result
      #   BEFORE reading AssignmentID / setting lease fields / recording it in the transaction.
      SET cr <- CALL CreatePendingAssignment(RoundContext, m, fresh_range(m),
                      assignment_origin = ORIGINAL, source_assignment = null, reason = null)   # F4/W7
      IF cr is assignment_creation_failed(reason):
        SET refresh_setup_error <- assignment_creation_failed(reason) ; CONTINUE   # W7: nothing created; refresh failed
      SET assignment_m <- cr.assignment                                            # W7: cr = assignment_created(assignment_m)
      RECORD refresh_setup_txn.prior_states[m] <- miner_state(m)                   # W3: capture prior state EXPLICITLY
      ADD AssignmentID(assignment_m) to refresh_setup_txn.created_assignments       # W3: capture AssignmentID EXPLICITLY
      SET lease_start(assignment_m)  <- now
      SET lease_expiry(assignment_m) <- now + default_lease_duration
      # E8-(7)/F5: the LEGAL per-source edge into WAKING (T3 REGISTERED / T4 RESERVE / T10 LOW_POWER_LISTEN) via the
      #            NON-BLOCKING StartWake; PENDING -> CURRENT happens at each miner's own WakeCompleteEvent (T5).
      SET wr <- CALL StartWake(RoundContext, m, target_assignment = assignment_m, from_state = miner_state(m),
                     scheduling_context = ORDINARY_DISPATCH(dispatch_envelope))   # V2/V3: explicit context; structured result
      IF wr = wake_seated(waid, wref, wtt, ws): ADD wref to refresh_setup_txn.wakes   # W3: capture ACTUAL WakeEventRef EXPLICITLY
      ELSE: SET refresh_setup_error <- wr                                             # W3: a refresh wake failure IS a setup failure
      # do NOT call RangeReassign for old ranges; do NOT rebind old assignments to new_TemplateID
    ASSERT difficulty unchanged                                 # I12
    # W3: if a CreatePendingAssignment or StartWake failed, DO NOT call CompleteAssignmentPhase — roll back immediately
    #   and take the declared liveness path.
    IF refresh_setup_error != null:
      SET setup_reason <- refresh_setup_error
    ELSE:
      # L2: the intended assignment set is now valid. Perform the ASSIGNMENT -> HASHING transition through the SINGLE
      #     sanctioned owner CompleteAssignmentPhase (K2) — the ONLY executable ASSIGNMENT -> HASHING step. U6: CAPTURE
      #     and BRANCH on the T5 disposition — do NOT return a successful new_TemplateID while the round is still ASSIGNMENT.
      ASSERT round_state = ASSIGNMENT
      SET disp <- CALL CompleteAssignmentPhase(RoundContext, dispatch_envelope)   # L2/M2/T5: SOLE ASSIGNMENT -> HASHING owner
      IF disp = assignment_phase_completed: RETURN new_TemplateID
      SET setup_reason <- disp.reason        # assignment_phase_failed(reason) — reversible (round still ASSIGNMENT)
    # W1/W2/V8: NAMED rollback using the txn's IMMUTABLE rollback_envelope; RollbackTemplateRefreshSetup departs any
    #   WAKING miner to OFFLINE via the LEGAL T12 edge and reports rolled_to_offline.
    SET rb <- CALL RollbackTemplateRefreshSetup(RoundContext, refresh_setup_txn)   # W1/W2/V8
    IF rb = rollback_failed(rr):
      RETURN CALL RoundAbort(RoundContext, reason = template_refresh_rollback_failed,
                             dispatch_envelope = dispatch_envelope, recovery_finalising = false)   # declared abort
    # W8 LIVENESS: bounded, state-compatible retry ONLY when no miner was routed to OFFLINE and the budget/horizon allow;
    #   otherwise ABORT. Never a retry from an incompatible OFFLINE state.
    IF rb.rolled_to_offline:
      RETURN CALL RoundAbort(RoundContext, reason = template_refresh_failed(setup_reason),
                             dispatch_envelope = dispatch_envelope, recovery_finalising = false)   # W8: retry state-incompatible
    IF setup_retry_generation[(RoundID_current, TEMPLATE_REFRESH_SETUP)] >= maximum_setup_retries:
      RETURN CALL RoundAbort(RoundContext, reason = template_refresh_retries_exhausted(setup_reason),
                             dispatch_envelope = dispatch_envelope, recovery_finalising = false)   # W8: bounded
    IF next_representable_simulation_time(dispatch_envelope.event_time) <= run_horizon_T:
      SET g <- setup_retry_generation[(RoundID_current, TEMPLATE_REFRESH_SETUP)] + 1     # W8: advance the bounded generation
      SET setup_retry_generation[(RoundID_current, TEMPLATE_REFRESH_SETUP)] <- g
      SET srid <- (RoundID_current, TEMPLATE_REFRESH_SETUP, g)                            # W8: SetupRetryID
      SET r <- CALL ScheduleEvent(EQ, RoundContext, SetupRetryEvent,
                     target_event_time = next_representable_simulation_time(dispatch_envelope.event_time),
                     target_microphase = ROUND_SETUP,
                     {RoundID = RoundID_current, setup_kind = TEMPLATE_REFRESH_SETUP, SetupRetryID = srid,
                      setup_retry_generation = g, reason = setup_reason})               # W8
      IF r = scheduled(...): RETURN template_refresh_retry_seated(srid, setup_reason)
    RETURN CALL RoundAbort(RoundContext, reason = template_refresh_failed(setup_reason),
                           dispatch_envelope = dispatch_envelope, recovery_finalising = false)   # declared abort
  RETURNS: new_TemplateID | template_refresh_retry_seated | round_aborted
  NOTE: Refresh NEVER bypasses TEMPLATE_COMMITMENT (TemplateCommit runs only from it, D8/E8) and
        NEVER reassigns a completed old range -- old assignments are CLOSED via CloseTemplateAssignments
        and NEW ORIGINAL assignments are created over the new domain (C5). Only eligible REGISTERED /
        RESERVE / LOW_POWER_LISTEN miners are activated, each via its legal edge into WAKING; OFFLINE
        and DISQUALIFIED miners receive no assignment (E8). L2: the round reaches HASHING through the SINGLE
        owner CompleteAssignmentPhase (K2) — the only executable ASSIGNMENT -> HASHING step in the spec.
```

## 20. Round abort

```
PROCEDURE RoundAbort
  INPUTS: RoundContext, reason, dispatch_envelope, recovery_finalising = false   # M1: threaded envelope; S4: finalising-abort flag
  # S4: recovery_finalising = true ONLY when the abort IS the application of a recovery outcome (branch D
  #     floor_unrecoverable, or the continuation's declared install-fail abort). It is threaded to
  #     CloseRoundAssignments so the S4 terminal cleanup (CancelActiveRecoveryEpisode) is SKIPPED for that closure —
  #     the caller finalises the episode. All OTHER aborts use the default false, so an unfinished episode is cancelled.
  PRECONDITIONS: unrecoverable condition (e.g. coordinator failure, unrecoverable floor breach,
                 unresolved partition) OR policy-directed abort;
                 # M1: dispatch_envelope threaded from the dispatched caller into CloseRoundAssignments.
                 # N1: RoundAbort terminates ONE round -- it does NOT terminate the simulation RUN and does
                 #     NOT reconcile to the horizon T. It is NOT the generic final-run flush (that is
                 #     FinalizeSimulationRun, §20a).
  EFFECTS:
    RECORD round_abort(RoundID, TemplateID, reason)
    IF any breach_events exist: LEAVE them intact               # I16: never repaired
    # N1 (1): disposition EVERY live propagation context, cancel its events, and clear the registries (G8). A
    #     miner paused by a cancelled candidate is NOT resumed (the round is ending); it closes via
    #     CloseRoundAssignments with stop_reason = ROUND_ABORTED.
    FOR EACH cpc in SORT(active_propagation_set BY CandidateID ascending):
      SET status(cpc) <- CANCELLED
      CANCEL every event in certificate_arrival_events(cpc)
      CANCEL block_arrival_event(cpc)
    CLEAR active_propagation_set
    CLEAR acceptance_batch_registry                             # cancel any pending acceptance batches
    # N1 (2)-(3): centralised closure of ALL open assignments and miner paths (D7; wires the ROUND_ABORTED
    #     EnterLowPowerListen disposition; cancels pending wake/resume/certificate/hash-work events). This
    #     ALSO records `round_terminal_time(RoundID) <- dispatch_envelope.event_time` (the abort event_time),
    #     which the NEXT round's RoundInitialise (SettleResidencyBoundary REBASE_TO_NEXT_ROUND) or the run-end
    #     FinalizeSimulationRun (FINAL_RUN_END) reads.
    CALL CloseRoundAssignments(RoundContext, disposition = ROUND_ABORTED, stop_reason = ROUND_ABORTED,
                               dispatch_envelope = dispatch_envelope,
                               recovery_finalising = recovery_finalising)   # M1: threaded envelope; S4: finalising-abort flag
    # N1: RoundAbort performs NO residency settle. The former `SettleResidencyBoundary(FINAL_RUN_END)` and
    #     the `ASSERT durations reconcile to horizon T` are REMOVED -- an abort at t < T must NEVER close
    #     residency at the horizon T. The residency boundary is settled ONLY by SettleResidencyBoundary, via
    #     the next RoundInitialise (if simulated time remains) OR FinalizeSimulationRun at the horizon.
    RETAIN zero-block/partial outcome in dataset                # I14; NA metrics per I15
    # N1 (4): move the round to its terminal state (G10); SecurityFloorEvaluate stale-noops after. A terminal
    #     state is not floor-applicable, so this is a direct transition (no applicability census), matching
    #     ValidBlockAccept's ROUND_ACCEPTED.
    TRANSITION round_state -> ROUND_ABORTED                     # bumps state_version (G10)
    # N1 (5): RETURN control. If simulated time remains, the sim driver may start another round via
    #     RoundInitialise; otherwise FinalizeSimulationRun performs the single run-end settle at the horizon.
  RETURNS: abort_record
  NOTE: N1: RoundAbort terminates ONE round and reconciles NOTHING to the horizon; an early abort (t < T)
        is followed by RoundInitialise when simulated time remains. The generic final-run flush (drain,
        horizon-close a nonterminal round, single FINAL_RUN_END settle, then I5/I6/I7 reconciliation) is
        FinalizeSimulationRun (§20a), which owns run-end accounting for ACCEPTED and ABORTED final rounds
        alike. G8: RoundAbort dispositions all live candidates and clears active_propagation_set and
        acceptance_batch_registry, so no stale candidate event or acceptance batch survives the abort (TV47).
```

## 20a. Run-level finalisation (N1; horizon sequence split O1)

`FinalizeSimulationRun` is the SINGLE run-level terminal action for the run-end residency settle and the
I5/I6/I7 reconciliation. **O1:** it is NO LONGER seated on the ordinary event queue and it NO LONGER drains
the queue or closes a round itself. The RUN DRIVER `RunEventLoopToHorizon` (§0.7d-run) drains every
`event_time <= T` via `ProcessEventTime` (the sole event-loop driver), and — when the run's current round is
still nonterminal at `T` — `ProcessEventTime(T)` interposes the named `CloseRoundAtHorizon` hook (§20b)
BETWEEN the `T` drain and the `T` epilogue. `FinalizeSimulationRun` is then invoked by the run driver as a
POST-`ProcessEventTime(T)` run-level HOOK (NOT a queued event): by that point every `event_time <= T` is
finalised, any nonterminal round is already horizon-closed, and the `T` epilogue has run
(`terminal_stale_noop`). `RoundAbort` (§20) closes ONE round and reconciles NOTHING to the horizon.

```
PROCEDURE FinalizeSimulationRun
  INPUTS: RunContext, RoundContext   # O1: a run-level HOOK invoked by RunEventLoopToHorizon after ProcessEventTime(T);
                                     #     NOT a queued event, so it carries NO dispatch_envelope.
  PRECONDITIONS: RunEventLoopToHorizon has processed every event_time <= T (the queue is empty of ordinary
                 events; O2 guarantees none was ever scheduled > T); any nonterminal round has been horizon-closed
                 by CloseRoundAtHorizon (§20b) inside ProcessEventTime(T); the T epilogue has run.
  EFFECTS:
    # N1: EXACTLY ONCE per run (guard); a re-invocation is a no-op.
    IF run_finalised: RETURN run_already_finalised
    # O1: NO internal DRAIN (the run driver already drained every event_time <= T) and NO horizon-close (that is
    #     CloseRoundAtHorizon, §20b). By the precondition round_state is now terminal for every run.
    ASSERT round_state in {ROUND_ACCEPTED, ROUND_ABORTED}                  # O1: horizon-close already ran if needed
    # (1) SINGLE run-end residency settle: close EVERY open residency interval at the horizon T through the ONE
    #     boundary owner, keyed by (RunID, RUN_END); idempotent (rebased_boundaries), NO reopen. This is the
    #     ONLY FINAL_RUN_END settle in the whole specification.
    CALL SettleResidencyBoundary(RoundContext, mode = FINAL_RUN_END,
                                 boundary_id = (RunID, RUN_END))            # N1/M4: the ONLY FINAL_RUN_END settle
    # (2) I5/I6/I7 reconciliation runs ONLY AFTER the final settle (never inside RoundAbort).
    ASSERT per-miner state-energy sums (I6); ASSERT network energy sum (I7)
    ASSERT per-miner durations reconcile to the horizon T (I5)             # every miner's t_<state> sums to T
    SET run_finalised <- true
  RETURNS: run_finalised(T)
  NOTE: N1/O1: the SINGLE owner of the run-end FINAL_RUN_END settle + I5/I6/I7 reconciliation, run EXACTLY
        ONCE at T. O1 narrowed it: the drain and the horizon-close moved OUT (to RunEventLoopToHorizon /
        ProcessEventTime and CloseRoundAtHorizon, §20b); this procedure performs ONLY the single settle,
        the reconciliation, and the run_finalised guard. It is a run-level hook, never a queued event, and
        never reopens an interval (the run is over). RoundAbort performs NO horizon settle; an early abort at
        t < T is followed by RoundInitialise when simulated time remains.
```

## 20b. Horizon-close of a nonterminal round (O1; deterministic run-hook envelope P2)

`CloseRoundAtHorizon` is the NAMED run-level hook that closes a still-nonterminal round AT the fixed horizon
`T`. It is invoked by `ProcessEventTime(T)` (§0.7d) AFTER the `T` drain and BEFORE the `T` epilogue, so the
round is already terminal when the horizon epilogue runs (making that epilogue a `terminal_stale_noop`). It
is a DIRECT run-level CALL, NOT a queued event — no ordinary event exists at `T` after the drain, and O2
guarantees none is scheduled beyond `T`. **P2:** it uses ONE deterministic **run-hook envelope** minted by the
single `RunHookContext` owner (§0.8), NOT an ambient or undefined identity; the envelope's identity is the
`HorizonHookID = (RunID, run_horizon_T, HORIZON_CLOSE)`, and the hook is idempotent per run.

```
PROCEDURE CloseRoundAtHorizon
  INPUTS: RoundContext, RunHookContext   # P2: the run-hook envelope owner; not a dispatched event envelope.
  PRECONDITIONS: t = run_horizon_T has been drained to quiescence by ProcessEventTime; round_state is
                 NONTERMINAL (ProcessEventTime only calls this when round_state NOT in {ROUND_ACCEPTED, ROUND_ABORTED})
  EFFECTS:
    # P2/Q6: the DETERMINISTIC run-hook identity for the horizon close. HorizonHookID is a fixed function of the
    #     run and the horizon; exactly ONE horizon-close envelope exists per run.
    SET HorizonHookID <- (RunID, run_horizon_T, HORIZON_CLOSE)
    # Q6 REPLAY GUARD with explicit state: a hook already IN_PROGRESS or APPLIED is a deterministic no-op, so a
    #     PARTIAL invocation can NEVER be replayed as a second FULL close (no second transition energy / boundary).
    IF HorizonHookID in RunHookContext.applied_run_hook_ids:                # state is IN_PROGRESS or APPLIED
      RETURN horizon_close_duplicate_noop(HorizonHookID)
    # Q6: mark IN_PROGRESS BEFORE any mutation, so a mid-close retry sees IN_PROGRESS and no-ops.
    SET RunHookContext.applied_run_hook_ids[HorizonHookID] <- IN_PROGRESS
    # P2/Q6: mint the ONE deterministic run-hook envelope in the RUN_HOOK namespace. Collision freedom derives
    #     from envelope_namespace = RUN_HOOK + hook_id (§0.2), NOT from the RUN_HOOK_CYCLE number; event_seq is a
    #     deterministic run_hook_seq value. Every miner transition below threads THIS envelope, so each transition
    #     is uniquely identifiable through (MinerID, assignment_version, run-hook envelope) and its TransitionEventID
    #     carries envelope_namespace = RUN_HOOK + hook_id (J3/Q6) — distinct from any ordinary transition.
    SET RunHookContext.run_hook_seq <- RunHookContext.run_hook_seq + 1
    SET horizon_envelope <- { envelope_namespace = RUN_HOOK, event_time = run_horizon_T, delta_cycle = RUN_HOOK_CYCLE,
                              event_seq = RunHookContext.run_hook_seq, hook_id = HorizonHookID }   # Q6/R3: tagged run-hook envelope (full identity threaded)
    # close ALL open assignments/miner paths through the single closure path (D7); records
    # round_terminal_time(RoundID) <- run_horizon_T and moves miners off ACTIVE_HASHING. CloseRoundAssignments
    # performs NO residency finalisation (M4) — that is the subsequent FinalizeSimulationRun FINAL_RUN_END settle.
    CALL CloseRoundAssignments(RoundContext, disposition = ROUND_ABORTED, stop_reason = ROUND_ABORTED,
                               dispatch_envelope = horizon_envelope)       # declared horizon-end closure (D7); Q6 tagged envelope
    # O1: a DISTINCT horizon-end disposition, separate from an ordinary RoundAbort, so run-end closure is
    #     auditable as horizon-end (not an unrecoverable-condition abort).
    RECORD horizon_end_disposition(RoundID) <- closed_at_horizon          # I14/I15 NA metrics retained
    TRANSITION round_state -> ROUND_ABORTED                               # terminal at T (declared horizon-end)
    # Q6: mark APPLIED atomically with the completed close, so any later replay is the deterministic no-op above.
    SET RunHookContext.applied_run_hook_ids[HorizonHookID] <- APPLIED
  RETURNS: round_closed_at_horizon(RoundID, run_horizon_T, HorizonHookID)
  NOTE: O1/P2/Q6: the horizon-close owner, invoked ONLY by ProcessEventTime(T) between the T drain and the T
        epilogue. It closes a nonterminal round via the single CloseRoundAssignments path with a DISTINCT
        horizon-end disposition and ONE deterministic run-hook envelope in the RUN_HOOK namespace (identity
        HorizonHookID). Q6: collision freedom comes from the envelope_namespace TAG (RUN_HOOK vs ORDINARY_EVENT),
        not the RUN_HOOK_CYCLE number; the IN_PROGRESS/APPLIED state makes it idempotent — exactly ONE horizon
        close per run, and a partial invocation cannot replay as a second full close (horizon_close_duplicate_noop,
        no second transition energy or residency boundary). It performs NO residency settle (that is
        FinalizeSimulationRun, §20a). It is a run-level hook, never a queued event.
  NOTE: R3 (full RUN_HOOK envelope preserved end-to-end): the horizon_envelope's envelope_namespace = RUN_HOOK and
        hook_id = HorizonHookID are THREADED unchanged through CloseRoundAssignments (§17a) -> EnterLowPowerListen
        (§7) -> ApplyMinerStateTransition (§0.9), so EVERY nested miner transition of the horizon close carries the
        RUN_HOOK namespace + HorizonHookID in its TransitionEventID (gate 6). A nested run-hook transition therefore
        has a DISTINCT TransitionEventID from any ordinary transition that shares its numeric (event_time,
        delta_cycle, event_seq), and its replay is suppressed on the COMPLETE RUN_HOOK TransitionEventID (TV138).
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
protocol's decision logic reproducible and audit-checkable against `I1..I19`, while confining
all randomness to clearly labelled model draws that exist solely because Stage-1 evaluation is
a simulation and not a real deployment. None of the above is executable source.

---

## 21. Global event-priority contract (F8, superseded by the G5 microphases)

When two or more scheduled events carry the **exact same** `event_time`, they are processed in a
**deterministic** order. **Stage 1G replaces the flat F8 priority sequence with the explicit
microphase contract of §0.7** (full spec in `STAGE_01G_EVENT_MICROPHASE_SPEC.md`, extended by the H2
delta-cycle rule and the I-01/I-02 epilogue): terminal closure → template refresh → collect all block
arrivals → `AcceptanceBatchFinalize` (one atomic arbitration+closure) → certificate/discovery/…
events, and — AFTER the whole `event_time` is quiescent — the single security-floor decision as the
event-time EPILOGUE (`FinalizeEventTimeSecurityCensus`, I-01/I-02, terminal-first + legal-source
guarded, I-05). Where this section's ordering differs from §0.7, **§0.7 (microphases + epilogue) is
authoritative**. The historical F8 table (`STAGE_01F_EVENT_PRIORITY_TABLE.md`) remains a frozen
Stage-1F artifact and is not modified. The two-level structure below is retained for the intra-type
tie-break, which the microphases reuse verbatim.

The contract has two levels:

1. **Inter-type priority.** Same-timestamp events of different types fire in this fixed order
   (highest first), so that no event ever acts on a round/miner/assignment that a
   higher-priority same-timestamp event has already invalidated. **The security-floor decision is NOT
   in this queue** (I-01/I-02): it is the event-time epilogue that `ProcessEventTime` runs ONCE after
   every event below — across all delta-cycles — has been drained at this `event_time`:

       1  RoundAbort closure            (ROUND_ABORTED)
       2  Round-acceptance closure      (ValidBlockAccept -> ROUND_ACCEPTED)
       3  Collect all block arrivals    (BlockAcceptancePoint register) then AcceptanceBatchFinalize (G5)
       4  Template invalidation / refresh (TemplateRefresh / CloseTemplateAssignments)
       5  Full-block arrival            (BlockAcceptancePoint)
       6  Certificate arrival           (CertificateArrival)
       7  Solution discovery            (HashWorkEvent hit -> ScheduleSolutionPropagation)   # L3: BEFORE lease expiry
       8  Range completion              (ActualRangeCompletion / ExhaustionAdjudicate)
       9  Reported exhaustion           (ReportedExhaustionClaim)
      10  Lease expiry                  (LeaseExpiry)                                         # L3: AFTER solution discovery
      11  Wake completion               (WakeCompleteEvent)
      12  Resume-from-pause             (ResumeFromPause)
      13  Periodic monitoring           (ActiveHashRateUpdate / heartbeat)
      13a Recovery deadline             (RecoveryDeadlineEvent, O3/P3): a dispatched queued event (§9a),
                                         microphase RECOVERY_DEADLINE; it RECORDS the deadline FACT and refreshes
                                         the census — it selects NO outcome and seats NOTHING; the epilogue decides
      13b Recovery completion due       (RecoveryCompletionDueEvent, Q2 step 1): a dispatched queued event (§10a),
                                         microphase RECOVERY_COMPLETION_DUE, seated at a deterministic later
                                         event_time (Q7); it RECORDS the decision is due + refreshes the census and
                                         performs NO transition — the application is the post-epilogue hook below
      —  Security-floor decision        (FinalizeEventTimeSecurityCensus -> SecurityFloorEvaluate):
                                         event-time EPILOGUE, run once AFTER quiescence (I-01/I-02), never
                                         as a same-timestamp queued event; it VERSIONS the recovery census (Q1),
                                         reconciles pending decisions, and seats a RecoveryCompletionDueEvent (P3/Q1)
      —  Recovery application (run-level)(ApplyRecoveryCompletionAfterEpilogue, Q2): a POST-epilogue hook run by
                                         ProcessEventTime AFTER the security-floor decision; it APPLIES a due
                                         decision ONLY if fresh (latest census version) + matching the FINAL census;
                                         NOT a queued event
      —  Horizon-close (run-level)      (CloseRoundAtHorizon, O1/P2/§20b): a RUN-LEVEL hook invoked INSIDE
                                         ProcessEventTime(T) between the T drain and the T epilogue when the round
                                         is nonterminal; uses ONE deterministic run-hook envelope (HorizonHookID,
                                         reserved RUN_HOOK_CYCLE); NOT a queued event, NOT RoundAbort (item 1)
      —  Run-level finalisation         (FinalizeSimulationRun, O1/N1): a RUN-LEVEL hook invoked by
                                         RunEventLoopToHorizon AFTER ProcessEventTime(T); NOT a queued microphase
                                         (RUN_FINALISE is NOT in the queue map), NOT a round event

2. **Intra-type tie-break.** Events of the SAME type at the SAME timestamp are ordered by
   `(CandidateID, MinerID, AssignmentID, seq)` lexicographically, where `seq` is the monotonic
   creation counter of the event envelope (§0.2). Acceptance arbitration additionally uses the
   value tie-break `candidate_hash` then `MinerID` (D6). No ordering ever depends on
   data-structure iteration order, so the processing order is identical across reruns (F8).

Consequences enforced by this order (see the table for the full list): a full-block arrival that
shares a timestamp with a round closure is processed **after** the closure and finds the round
already closed (so it cannot accept into a closed round); a `WakeCompleteEvent` sharing a timestamp
with round acceptance is processed **after** the closure and, per `CloseRoundAssignments`, the
waking miner was already moved to `OFFLINE` (T12), so it never activates into a closed round.

**L3 (canonical discovery-before-lease-expiry order).** Solution discovery (item 7) is processed
**BEFORE** lease expiry (item 10) whenever the two share a timestamp — this is the ONE canonical
order, encoded by the priority numbers and enforced identically here, in `§0.7`, and in the
microphase spec. The rationale: a solution found EXACTLY at a lease boundary must be captured
against the CURRENT (still-live) assignment version before that version's lease can expire. Because
discovery fires first, `ScheduleSolutionPropagation` takes the immutable discovery snapshot (E1) of
the still-`CURRENT` head; the finder pauses (`VALID_SOLUTION_VERIFIED`, PATH B); and only THEN does
`LeaseExpiry` run — finding the head `PAUSED` and handling it via the L4 status-aware `CASE PAUSED`
(canonical CLOSE of the paused head, suffix reassign), which cannot retract the already-captured
discovery. The reverse order (lease expiry first) is FORBIDDEN: it would CLOSE/reassign the version
before the same-timestamp discovery is processed, and the discovery's `HashWorkEvent` would then
no-op against a no-longer-live head (G9 stale guard), silently losing a valid boundary solution.
`ValidateCandidate` still resolves each certificate against its immutable discovery snapshot (E1),
so this ordering fixes *which event acts first* so that a validly discovered boundary solution
always *stays valid*. No statement anywhere in the corpus places lease expiry before same-timestamp
discovery (L3).
