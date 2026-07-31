# Stage 1N — Procedure Call Graph

Extracted from `STAGE_01_PROTOCOL_PSEUDOCODE.md` (post-N1..N4). `→` is a direct `CALL`; `⇒` is a scheduled
discrete `event` (every `⇒`/`ScheduleEvent` carries an EXPLICIT `target_microphase`, §0.7g/§0.7g-driver).
**Stage-1N structural changes:** `FinalizeSimulationRun` (N1, the run-level finaliser) and
`CompleteSecurityRecovery` (N2, the executable R13/R14 owner) are ADDED; `RoundAbort` no longer calls
`SettleResidencyBoundary`; the `FINAL_RUN_END` settle now flows ONLY from `FinalizeSimulationRun`. **51
procedures defined; 0 dangling** (net +2 vs Stage 1M).

## New / changed edges (Stage 1N)

```
ProcessEventTime                   → FinalizeEventTimeSecurityCensus, ScheduleEvent   # I-02 driver; dispatch_envelope per event (M1)
RoundInitialise                    → SettleResidencyBoundary                          # M4/L5: mode = REBASE_TO_NEXT_ROUND (subsequent round)
RoundAbort                         → CloseRoundAssignments                            # N1: ONE round; records round_terminal_time; NO SettleResidencyBoundary
FinalizeSimulationRun              → CloseRoundAssignments, SettleResidencyBoundary   # N1: horizon-close nonterminal round; the ONLY FINAL_RUN_END settle; then I5/I6/I7
SettleResidencyBoundary            (leaf; SINGLE idempotent boundary owner — REBASE_TO_NEXT_ROUND | FINAL_RUN_END; boundary_id-keyed — M4/N1)
FinalizeEventTimeSecurityCensus    → SecurityFloorEvaluate                            # I-01 epilogue
SecurityFloorEvaluate              ⇒ CompleteSecurityRecovery   # N2: floor-restored -> seat recovery-completion at a strictly-later event_time (I-02), microphase RECOVERY_COMPLETE
CompleteSecurityRecovery           → TransitionRoundState, CompleteAssignmentPhase, RoundAbort   # N2/R13/R14 (branch C may also activate reserves via ReserveActivate)
TransitionRoundState               → CaptureSecurityCensusOnApplicabilityEntry        # M2: census on floor-applicable entry (incl. recovery exits, N2)
CompleteAssignmentPhase            → TransitionRoundState                             # L2/M2: ASSIGNMENT -> HASHING (R4) + census
CloseRoundAssignments              → EnterLowPowerListen, ApplyMinerStateTransition   # E7/F6; records round_terminal_time only (M4); explicit envelopes (M1)
ReserveActivate                    → CreatePendingAssignment, StartWake               # F4/F5; explicit envelope (M1)
```

The remainder of the graph is unchanged from Stage 1M (see `STAGE_01M_PROCEDURE_CALL_GRAPH.md`): the
event-envelope threading (M1), the single `ASSIGNMENT → HASHING` owner `CompleteAssignmentPhase` (L2), the
propagation/acceptance chain, and the microphase-complete enqueue (M5) all hold.

## Entry points (dispatched by the loop / sim driver)

`ProcessEventTime` (I-02 driver), `RoundInitialise`, `TemplateCommit`, `PrepareParticipantsForNewRound`,
`MinerRegister`, `ReserveActivate`, `LeaseExpiry`, `FullRangeExhaustNoSolution`, `ActiveHashRateUpdate`,
`AdversarialParticipationChangeEvent`, `AcceptanceBatchFinalize`, **`CompleteSecurityRecovery` (N2)**,
`RoundAbort`, **`FinalizeSimulationRun` (N1, run-level terminal)**. Queued handlers (`WakeCompleteEvent`,
`HashWorkEvent`, `CertificateArrival`, `BlockAcceptancePoint`, `ResumeFromPause`) are enqueued via
`ScheduleEvent` (each with an explicit `target_microphase`). Every driver entry point's seating rule (event
type, microphase, tie key, envelope fields, same-time delta-cycle right) is declared in §0.7g-driver (N3).

## Required-property proofs

1. **No dangling calls.** Every called/scheduled name resolves to a defined procedure (51 defined; 0
   undefined). The two new procedures introduce no dangling reference.

2. **Round abort ≠ run end (N1).** `RoundAbort → CloseRoundAssignments` only; its executable body has NO
   `SettleResidencyBoundary` and NO horizon reconciliation. `FinalizeSimulationRun → {CloseRoundAssignments
   (horizon-close), SettleResidencyBoundary (FINAL_RUN_END)}` is the ONLY path to a `FINAL_RUN_END` settle,
   run once (guarded by `run_finalised`) for ACCEPTED/ABORTED/nonterminal final rounds alike.

3. **Executable recovery exit (N2/R13/R14).** `SecurityFloorEvaluate ⇒ CompleteSecurityRecovery` (seated at
   a strictly-later `event_time`, I-02); `CompleteSecurityRecovery → {TransitionRoundState (branches A/B),
   CompleteAssignmentPhase (branch C), RoundAbort (branch D)}`. Branches A/B/C reach a floor-applicable state
   through `TransitionRoundState`/`CompleteAssignmentPhase`, so the applicability-entry census is captured.

4. **Single boundary owner preserved (M4).** `SettleResidencyBoundary` (leaf) is reached only from
   `RoundInitialise` (REBASE) and `FinalizeSimulationRun` (FINAL_RUN_END); `ApplyMinerStateTransition`
   remains the sole owner of intervals for an actual state change.

5. **Complete driver seating (N3).** Every dispatched entry point — including the two new ones — has a
   declared microphase and envelope seating rule (§0.7g-driver); no entry point receives a `dispatch_envelope`
   without one.

## Result

**PROCEDURE CALL GRAPH (Stage 1N): PASS** — all five required reachability properties hold; the new
procedures `FinalizeSimulationRun` and `CompleteSecurityRecovery` are correctly wired; `RoundAbort` performs
no boundary settle; no dangling reference exists (51 defined, 0 undefined).
