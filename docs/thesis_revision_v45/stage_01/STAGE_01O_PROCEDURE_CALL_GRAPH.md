# Stage 1O — Procedure Call Graph

Extracted from `STAGE_01_PROTOCOL_PSEUDOCODE.md` (post-O1..O5). `→` is a direct `CALL`; `⇒` is a scheduled
discrete `event` (every `⇒`/`ScheduleEvent` carries an EXPLICIT `target_microphase`, §0.7g/§0.7g-driver, and
is rejected if `target_event_time > T`, O2). **Stage-1O structural changes:** `RunEventLoopToHorizon` (O1, the
run-level driver), `CloseRoundAtHorizon` (O1, the horizon-close hook), and `RecoveryDeadlineEvent` (O3, the
seated UNRECOVERABLE source) are ADDED; `FinalizeSimulationRun` no longer drains the queue and no longer calls
`CloseRoundAssignments` (the horizon-close moved to `CloseRoundAtHorizon`); `CompleteSecurityRecovery` is now
keyed by `RecoveryOutcome`. **54 procedures defined; 0 dangling** (net +3 vs Stage 1N).

## New / changed edges (Stage 1O)

```
RunEventLoopToHorizon        → ProcessEventTime, FinalizeSimulationRun         # O1: the RUN-LEVEL driver; ProcessEventTime is the sole event-loop driver
ProcessEventTime             → CloseRoundAtHorizon, FinalizeEventTimeSecurityCensus, ScheduleEvent
                                                                               # O1: CloseRoundAtHorizon interposed at t = T (nonterminal) between drain and epilogue
CloseRoundAtHorizon          → CloseRoundAssignments                          # O1: horizon-close of a nonterminal round; ONE deterministic horizon envelope; NO residency settle
FinalizeSimulationRun        → SettleResidencyBoundary                        # O1: the ONLY FINAL_RUN_END settle; then I5/I6/I7. NO drain, NO CloseRoundAssignments now
SettleResidencyBoundary      (leaf; SINGLE idempotent boundary owner — REBASE_TO_NEXT_ROUND | FINAL_RUN_END; boundary_id-keyed — M4/N1)
ScheduleEvent                (leaf; SOLE enqueue interface; O2 rejects target_event_time > run_horizon_T = post_horizon_event_rejected)
SecurityFloorEvaluate        ⇒ RecoveryDeadlineEvent      # O3: on ENTRY to SECURITY_RECOVERY (breach branch), seats the UNRECOVERABLE source at <= T
SecurityFloorEvaluate        ⇒ CompleteSecurityRecovery   # O2/O3/O4: floor-restored -> seat RecoveryOutcome=RESTORED at t_next (> t, <= T); at t = T -> run_ending_no_recovery_action (seats nothing)
RecoveryDeadlineEvent        ⇒ CompleteSecurityRecovery   # O3/O4: floor still breached at deadline -> seat RecoveryOutcome=UNRECOVERABLE at t_next (<= T); guarded by recovery_completion_pending
CompleteSecurityRecovery     → TransitionRoundState, CompleteAssignmentPhase, RoundAbort
                                                          # O3: RESTORED -> A/B (TransitionRoundState) / C (CompleteAssignmentPhase); UNRECOVERABLE -> D (RoundAbort); O4: recovery_outcome_finalised idempotence
TransitionRoundState         → CaptureSecurityCensusOnApplicabilityEntry       # M2: census on floor-applicable entry (incl. recovery exits)
CompleteAssignmentPhase      → TransitionRoundState                            # L2/M2: ASSIGNMENT -> HASHING (R4) + census
RoundAbort                   → CloseRoundAssignments                           # N1: ONE round; records round_terminal_time; NO SettleResidencyBoundary
```

The remainder of the graph is unchanged from Stage 1N (see `STAGE_01N_PROCEDURE_CALL_GRAPH.md`): the
event-envelope threading (M1), the single `ASSIGNMENT → HASHING` owner `CompleteAssignmentPhase` (L2), the
propagation/acceptance chain, and the microphase-complete enqueue (M5) all hold.

## Entry points

**Run-level drivers / hooks (O1; NOT queued events):** `RunEventLoopToHorizon` (the run-level driver),
`ProcessEventTime` (the SOLE event-loop driver, I-02), `CloseRoundAtHorizon` (horizon-close hook, §20b),
`FinalizeSimulationRun` (run-end finaliser hook, §20a). None of these is seated on the queue; `RUN_FINALISE`
is NOT in the microphase queue map.

**Queued sim-driver entry points (§0.7g-driver):** `RoundInitialise`, `TemplateCommit`,
`PrepareParticipantsForNewRound`, `MinerRegister`, `ReserveActivate`, `FullRangeExhaustNoSolution`,
`RecoveryDeadlineEvent` (O3), `CompleteSecurityRecovery`, `RoundAbort`. **Queued handlers:**
`WakeCompleteEvent`, `HashWorkEvent`, `CertificateArrival`, `BlockAcceptancePoint`, `ResumeFromPause`,
`LeaseExpiry`, `ActiveHashRateUpdate`, `AdversarialParticipationChangeEvent`, `AcceptanceBatchFinalize`. Every
one is enqueued via `ScheduleEvent` with an explicit `target_microphase` and is subject to the O2 horizon rule
(`target_event_time <= T`).

## Required-property proofs

1. **No dangling calls.** Every called/scheduled name resolves to a defined procedure (54 defined; 0
   undefined). The three new procedures (`RunEventLoopToHorizon`, `CloseRoundAtHorizon`,
   `RecoveryDeadlineEvent`) introduce no dangling reference.

2. **Single event-loop driver + run-level finaliser (O1).** `ProcessEventTime` is reached only from
   `RunEventLoopToHorizon` (never from a handler). `FinalizeSimulationRun` is reached only from
   `RunEventLoopToHorizon` AFTER `ProcessEventTime(T)`; it calls ONLY `SettleResidencyBoundary` (the ONE
   `FINAL_RUN_END` settle) — it no longer drains or calls `CloseRoundAssignments`. The horizon-close of a
   nonterminal round is `CloseRoundAtHorizon → CloseRoundAssignments`, reached only from `ProcessEventTime(T)`
   between the drain and the epilogue.

3. **No post-horizon event (O2).** `ScheduleEvent` (the SOLE enqueue interface) rejects any
   `target_event_time > run_horizon_T`, so no `⇒` edge can create an event beyond `T`. A floor-restored
   decision at `t = T` takes the `run_ending_no_recovery_action` path and creates NO `⇒ CompleteSecurityRecovery`.

4. **R14 reachable (O3).** A path exists `SecurityFloorEvaluate ⇒ RecoveryDeadlineEvent ⇒
   CompleteSecurityRecovery(UNRECOVERABLE) → RoundAbort(floor_unrecoverable)`. R13 is reached by
   `SecurityFloorEvaluate ⇒ CompleteSecurityRecovery(RESTORED) → {TransitionRoundState |
   CompleteAssignmentPhase}`. Branches A/B/C reach a floor-applicable state, so the applicability-entry census
   is captured (M2).

5. **Episode idempotence (O4).** Both `⇒ CompleteSecurityRecovery` edges are gated by
   `recovery_completion_pending[episode]` (at most one seated); `CompleteSecurityRecovery` gates on
   `recovery_outcome_finalised[episode]` (at most one applied). Neither is a dangling or unguarded edge.

6. **Single boundary owner preserved (M4).** `SettleResidencyBoundary` (leaf) is reached only from
   `RoundInitialise` (REBASE) and `FinalizeSimulationRun` (FINAL_RUN_END). `RoundAbort` and
   `CloseRoundAtHorizon` both call `CloseRoundAssignments`, which records `round_terminal_time` only (no
   residency settle).

## Result

**PROCEDURE CALL GRAPH (Stage 1O): PASS** — all six required reachability properties hold; the three new
procedures are correctly wired; `ProcessEventTime` is the sole event-loop driver; `FinalizeSimulationRun`
performs no drain and no horizon-close; R14 has a concrete source and call path; no dangling reference exists
(54 defined, 0 undefined). Documentation only; name remains PoCol; A1 baseline `8.420833333 kWh` unchanged;
the prohibited rebranded-algorithm-name variants are not used anywhere in this document.
