# Stage 1P — Procedure Call Graph

Extracted from `STAGE_01_PROTOCOL_PSEUDOCODE.md` (post-P1..P5). `→` is a direct `CALL`; `⇒` is a scheduled
discrete `event` (every `⇒`/`ScheduleEvent` carries an EXPLICIT `target_microphase`, §0.7g/§0.7g-driver, and
is rejected if `target_event_time > T`, O2). **Stage-1P structural changes:** `SeatRecoveryCompletion` (P4/P5,
the SOLE seater of `CompleteSecurityRecovery`) and `CaptureSecurityCensusOnRecoveryDeadline` (P3) are ADDED;
`RecoveryDeadlineEvent` no longer seats a completion (it records the deadline FACT and dirties the census);
`CloseRoundAtHorizon` uses a deterministic run-hook envelope with a replay guard (P2); `RunEventLoopToHorizon`
makes a synthetic horizon-sentinel `ProcessEventTime(T)` (P1). **56 procedures defined; 0 dangling** (net +2
vs Stage 1O).

## New / changed edges (Stage 1P)

```
RunEventLoopToHorizon        → ProcessEventTime, FinalizeSimulationRun
                                                          # P1: process event_times < T, then ONE synthetic
                                                          #     ProcessEventTime(T, is_horizon, allow_empty_horizon)
ProcessEventTime             → CloseRoundAtHorizon, FinalizeEventTimeSecurityCensus, ScheduleEvent
                                                          # P1/P2: at t = T (nonterminal) interpose CloseRoundAtHorizon
                                                          #        (threading RunHookContext) between drain and epilogue
CloseRoundAtHorizon          → CloseRoundAssignments      # P2: ONE deterministic run-hook envelope (HorizonHookID,
                                                          #     reserved RUN_HOOK_CYCLE); replay -> horizon_close_duplicate_noop
SecurityFloorEvaluate        → SeatRecoveryCompletion     # P3/P4/P5: floor restored -> (RESTORED); deadline+breach -> (UNRECOVERABLE)
SecurityFloorEvaluate        ⇒ RecoveryDeadlineEvent      # O3: on ENTRY to SECURITY_RECOVERY, seat the deadline (<= T)
RecoveryDeadlineEvent        → CaptureSecurityCensusOnRecoveryDeadline
                                                          # P3: record recovery_deadline_reached + dirty the census; NO seat, NO outcome
CaptureSecurityCensusOnRecoveryDeadline (leaf; P3: THIRD coherent writer of security_census_dirty/latest_security_census)
SeatRecoveryCompletion       ⇒ CompleteSecurityRecovery   # P4: pending set ONLY on scheduled; P5: versioned RecoveryDecisionID; O2: none at t = T
CompleteSecurityRecovery     → TransitionRoundState, CompleteAssignmentPhase, RoundAbort
                                                          # O3/P5: RESTORED -> A/B (TransitionRoundState) / C (CompleteAssignmentPhase);
                                                          #        UNRECOVERABLE -> D (RoundAbort); recovery_decision_stale_noop if superseded
```

The remainder of the graph is unchanged from Stage 1O (see `STAGE_01O_PROCEDURE_CALL_GRAPH.md`): the
run-level finaliser `FinalizeSimulationRun → SettleResidencyBoundary` only (no drain, no horizon-close);
`ScheduleEvent` (SOLE enqueue interface; O2 horizon rule); the event-envelope threading (M1); the single
`ASSIGNMENT → HASHING` owner `CompleteAssignmentPhase` (L2); and the propagation/acceptance chain all hold.

## Entry points

**Run-level drivers / hooks (O1/P1/P2; NOT queued events):** `RunEventLoopToHorizon` (the run-level driver,
now with the P1 horizon sentinel), `ProcessEventTime` (the SOLE event-loop driver), `CloseRoundAtHorizon`
(§20b, deterministic run-hook envelope, P2), `FinalizeSimulationRun` (§20a). None is seated on the queue.

**Queued sim-driver entry points (§0.7g-driver):** `RoundInitialise`, `TemplateCommit`,
`PrepareParticipantsForNewRound`, `MinerRegister`, `ReserveActivate`, `FullRangeExhaustNoSolution`,
`RecoveryDeadlineEvent` (records the deadline fact, P3), `CompleteSecurityRecovery`, `RoundAbort`. **Queued
handlers:** `WakeCompleteEvent`, `HashWorkEvent`, `CertificateArrival`, `BlockAcceptancePoint`,
`ResumeFromPause`, `LeaseExpiry`, `ActiveHashRateUpdate`, `AdversarialParticipationChangeEvent`,
`AcceptanceBatchFinalize`. **Internal helpers (not entry points):** `SeatRecoveryCompletion` (called by the
epilogue) and `CaptureSecurityCensusOnRecoveryDeadline` (called by `RecoveryDeadlineEvent`).

## Required-property proofs

1. **No dangling calls.** Every called/scheduled name resolves to a defined procedure (56 defined; 0
   undefined). The two new procedures introduce no dangling reference.

2. **Horizon sentinel (P1).** `RunEventLoopToHorizon` calls `ProcessEventTime` for every `event_time < T`,
   then ONE synthetic `ProcessEventTime(T, is_horizon = true, allow_empty_horizon = true)` (guarded by `T not
   in finalised_event_times`). So `ProcessEventTime(T)` runs exactly once even with no ordinary event at `T`;
   a nonterminal round is horizon-closed there; `FinalizeSimulationRun` asserts the round terminal, so it is
   unreachable without horizon closure.

3. **Deterministic run-hook envelope (P2).** `CloseRoundAtHorizon → CloseRoundAssignments` uses the envelope
   minted from `RunHookContext` (identity `HorizonHookID`, reserved `RUN_HOOK_CYCLE`). `applied_run_hook_ids`
   makes it idempotent (`horizon_close_duplicate_noop` on replay); the reserved cycle prevents collision with
   any ordinary `ScheduleEvent` envelope.

4. **Deadline is a fact (P3).** `RecoveryDeadlineEvent → CaptureSecurityCensusOnRecoveryDeadline` only; it does
   NOT `⇒ CompleteSecurityRecovery`. The single seating edge `SeatRecoveryCompletion ⇒ CompleteSecurityRecovery`
   is reached ONLY from the epilogue `SecurityFloorEvaluate → SeatRecoveryCompletion`, which decides from the
   FINAL census.

5. **Atomic seating (P4).** `SeatRecoveryCompletion` sets `recovery_completion_pending` only after
   `ScheduleEvent` returns `scheduled`; a decision at `t = T` records `run_ending_no_recovery_action` and seats
   nothing. There is no `⇒ CompleteSecurityRecovery` edge with `target_event_time > T`.

6. **Decision versioning (P5).** `CompleteSecurityRecovery` applies only if its `RecoveryDecisionID` equals
   `latest_recovery_decision[episode].decision_id`; otherwise `recovery_decision_stale_noop`. At most one
   applied outcome per episode (`recovery_outcome_finalised`, O4).

## Result

**PROCEDURE CALL GRAPH (Stage 1P): PASS** — all six required reachability properties hold; the two new
procedures are correctly wired; `RecoveryDeadlineEvent` seats no completion; `SeatRecoveryCompletion` is the
sole seater; `CloseRoundAtHorizon` is idempotent; no dangling reference exists (56 defined, 0 undefined).
Documentation only; name remains PoCol; A1 baseline `8.420833333 kWh` unchanged; the prohibited
rebranded-algorithm-name variants are not used anywhere in this document.
