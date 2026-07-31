# Stage 1R — Correction Report (post-epilogue & transition-identity lock)

**Branch.** `thesis-v45-pocol-stage1r-post-epilogue-transition-identity-lock`
**Base.** `0244ce1f9eacb278320a4cc060962ef49a77b5e5` (Stage 1Q).
**Scope.** Documentation only — no executable source, configuration, DOCX, PDF, or experiment changes.
Protected DOCX drafts byte-identical (draft-42 `2c3afdc5…`, draft-44 `a31400bc…`); Stage 1A–1Q lettered
artifacts unmodified (A–Q-lock).

**Naming rule (binding).** The algorithm is **PoCol**; the mechanism is **the idle policy within PoCol**. No
property is claimed. The A1 baseline is unchanged (`8.420833333 kWh`). No new consensus feature — R1…R6 make the
post-epilogue recovery application causally safe at the drained event_time, collapse the double epilogue into one
decision plus one settlement, thread the full transition envelope into the transition identity, make the recovery
application atomic, give the security-census write order an explicit owner with named sources, and keep the
latest-decision mirror consistent.

## R1 — No same-timestamp event after the ordinary drain

`ApplyRecoveryCompletionAfterEpilogue` (§10a) runs AFTER every ordinary and delta-cycle event at `event_time = t`
has been drained. It, and its branch dispatch `CompleteSecurityRecovery`, now enqueue NOTHING whose
`target_event_time = t`. In particular **branch C** (SECURITY_RECOVERY → ASSIGNMENT; reserve activation /
reassignment; `CompleteAssignmentPhase` → HASHING) no longer performs `ReserveActivate`/`StartWake` at `t`: it
transitions the round to `ASSIGNMENT` and seats ONE `RecoveryAssignmentContinuationEvent` at
`next_representable_simulation_time(t)` — a STRICTLY LATER `event_time` — whose ordinary handler (§10a) performs
`ReserveActivate`/`RangeReassign`/`StartWake`. A zero modeled wake latency after post-epilogue application is
represented at `next_representable_simulation_time(t)`, never at `t`. `ProcessEventTime` (§0.7d) now ASSERTS `no
ordinary event remains with event_time = t` before adding `t` to `finalised_event_times`. Audit:
`STAGE_01R_POST_EPILOGUE_CAUSALITY_AUDIT.md`. TV135/TV136.

## R2 — One security epilogue, one post-application settlement

The prior contradiction (`FinalizeEventTimeSecurityCensus` described as exactly-once yet invoked as "epilogue #1"
and "epilogue #2") is removed. The canonical event-time tail (§0.7d) is: (1) `FinalizeEventTimeSecurityCensus(t)`
EXACTLY ONCE — the sole security-floor decision for `t`; (2) `ApplyRecoveryCompletionAfterEpilogue(t)` — at most
one valid due decision applied; (3) `FinalizePostRecoveryApplicationState(t)` — EXACTLY ONCE when the application
re-dirtied `t`; it is NOT a second security-floor decision — it archives the terminal/post-application census
(source POST_RECOVERY_APPLICATION), clears `security_census_dirty[t]`, seats NO recovery decision, and enqueues NO
event at `t`; (4) ASSERT no ordinary event remains at `t` AND `security_census_dirty[t] = false`, THEN finalise
`t`. For an UNRECOVERABLE application that closes the round, the settlement records a terminal census observation
and clears the dirty flag without invoking `SecurityFloorEvaluate` again. For RESTORED branches, any new
applicability census from later miner activation is generated at the strictly-later continuation `event_time`.
Audit: `STAGE_01R_POST_EPILOGUE_CAUSALITY_AUDIT.md`. TV136/TV142.

## R3 — Thread the full transition envelope

`ApplyMinerStateTransition` (§0.9) now receives the FULL transition envelope — `envelope_namespace`, `event_time`,
`delta_cycle`, `event_seq`, `hook_id` — from ONE `dispatch_envelope`; the namespace fields are never decomposed
away. The immutable `TransitionEventID` now leads with `envelope_namespace` and `hook_id`, so a `RUN_HOOK`
transition and an `ORDINARY_EVENT` transition with identical numeric `(event_time, delta_cycle, event_seq)` are
DISTINCT ids. `ProcessEventTime` (§0.7d) materialises an `ORDINARY_EVENT` dispatch envelope with `hook_id = null`;
`CloseRoundAtHorizon` (§20b) preserves `RUN_HOOK` + `HorizonHookID` through `CloseRoundAssignments` (§17a) →
`EnterLowPowerListen` (§7) → `ApplyMinerStateTransition`, so every nested horizon-close transition carries the
namespace + hook_id in its id. A `RUN_HOOK` envelope missing its `hook_id` is rejected. Audit:
`STAGE_01R_TRANSITION_NAMESPACE_AUDIT.md`. TV137/TV138.

## R4 — Atomic recovery application

`RECOVERY_DECISION_STATUS` (§0.8) adds `APPLYING` and `APPLY_FAILED`. `ApplyRecoveryCompletionAfterEpilogue`
(§10a) now (1) VERIFIES (round SECURITY_RECOVERY, episode current, decision SCHEDULED and due, bound census
version latest, outcome matches the final census, round nonterminal); (2) atomically sets `APPLYING`; (3) executes
`CompleteSecurityRecovery`, which returns an EXPLICIT `recovery_branch_result(success, target | reason)` for each
branch A/B/C/D; (4) marks `APPLIED`, finalises `recovery_outcome_finalised[episode]`, removes from pending, and
clears `current_recovery_episode` ONLY after a successful round transition / successful `RoundAbort`; (5) on a
branch failure records `APPLY_FAILED` and PRESERVES the active episode. At the horizon, after `CloseRoundAtHorizon`
makes the round terminal, every pending decision is cancelled and the application returns `terminal_recovery_noop`
— NO decision is marked `APPLIED` after horizon closure. Audit:
`STAGE_01R_RECOVERY_APPLICATION_ATOMICITY_AUDIT.md`. TV139/TV140.

## R5 — Explicit security-census write sequence and sources

`RunContext` (§1.0) gains `security_census_write_seq_by_event_time`, initialised in `RunInitialise` and preserved
across rounds; `CommitSecurityCensus` (§0.8a) is its SOLE owner and stamps its explicit deterministic increment as
`census_seq`, replacing the implicit "next per-event_time census-write ordinal". `CENSUS_SOURCE` now has FIVE
values: MINER_STATE_TRANSITION, APPLICABILITY_ENTRY, RECOVERY_DEADLINE, RECOVERY_COMPLETION_DUE,
POST_RECOVERY_APPLICATION. `RecoveryCompletionDueEvent` (§10a) uses `RECOVERY_COMPLETION_DUE` (not
`RECOVERY_DEADLINE`); `FinalizePostRecoveryApplicationState` uses `POST_RECOVERY_APPLICATION`. Every producer
(`ApplyMinerStateTransition`, the capture procedures) CALLS `CommitSecurityCensus` — none is a direct writer of
the two maps; the leftover "a writer … the other writer is CaptureSecurityCensusOnApplicabilityEntry" statement is
withdrawn. Audit: `STAGE_01R_CENSUS_SEQUENCE_AUDIT.md`. TV141.

## R6 — Keep decision mirrors consistent

`latest_recovery_decision` (§0.8) is kept ATOMICALLY consistent with `recovery_decisions` by the sole status
mutator `SetRecoveryDecisionStatus` (§9), which refreshes the mirror whenever it points at the mutated decision.
Every status transition — SCHEDULED, SUPERSEDED, APPLYING, APPLIED, SCHEDULE_FAILED, APPLY_FAILED, CANCELLED —
routes through it (`SeatRecoveryCompletion` horizon-defer/SCHEDULED/SCHEDULE_FAILED, `ReconcilePendingRecoveryDecisions`
SUPERSEDED, `ApplyRecoveryCompletionAfterEpilogue` APPLYING/APPLIED/SUPERSEDED/APPLY_FAILED/CANCELLED). A
latest-decision record can NEVER remain CREATED after the underlying decision became CANCELLED or SCHEDULE_FAILED
(the P5 horizon-defer mirror-lag is fixed). Audit: `STAGE_01R_RECOVERY_APPLICATION_ATOMICITY_AUDIT.md`. TV139/TV140.

## Summary of changed / added artifacts

| Artifact | Change |
|----------|--------|
| `STAGE_01_PROTOCOL_PSEUDOCODE.md` | §0.2/§0.7d ORDINARY_EVENT dispatch envelope (namespace + hook_id, R3); §0.7d canonical event-time TAIL — one epilogue + `ApplyRecoveryCompletionAfterEpilogue` + `FinalizePostRecoveryApplicationState` + finalisation ASSERTIONs (R1/R2); §0.7g/§0.7g-driver `RecoveryAssignmentContinuationEvent` (R1); §0.8 recovery registries + `RECOVERY_DECISION_STATUS` (+APPLYING/APPLY_FAILED, R4) + census-source note (R5); §0.8a `CommitSecurityCensus` explicit write-seq + five sources (R5); §0.9 `ApplyMinerStateTransition` full envelope + `TransitionEventID` (R3), producer-not-writer (R5); §1.0 `RunContext`/`RunInitialise` write-seq (R5); §9 `SetRecoveryDecisionStatus` (R6), `Reconcile`/`SeatRecoveryCompletion` route through it (R6), `CaptureSecurityCensusOnRecoveryDeadline` census_source param (R5); §10a `RecoveryCompletionDueEvent` source (R5), `ApplyRecoveryCompletionAfterEpilogue` atomic apply (R4), `CompleteSecurityRecovery` branch-C defer + dispositions (R1/R4), NEW `RecoveryAssignmentContinuationEvent` (R1) + `FinalizePostRecoveryApplicationState` (R2); §17a/§7/§20b run-hook envelope threaded (R3) |
| `STAGE_01_ROUND_STATE_MACHINE.md` | §3.10 R1/R2/R4 paragraphs; RECOVERY_DECISION_STATUS enum (+APPLYING/APPLY_FAILED); R13/R14 rows (R1 deferral, R4 atomicity, terminal noop) |
| `STAGE_01_INVARIANT_CATALOGUE.md` | I17 enforcement point: five census sources + explicit write-seq owner (R5) + single-epilogue settlement (R2); I19 enforcement point: RUN_HOOK TransitionEventID threading (R3) |
| `STAGE_01_TERMINOLOGY.md` | Stage-1R addendum (R1–R6) |
| `STAGE_01_TRACEABILITY_MATRIX.csv` | R119–R125 (R1–R6 + TV135–TV142) |
| `STAGE_01R_*` (10 new deliverables) | this report + post-epilogue-causality / transition-namespace / recovery-application-atomicity / census-sequence audits + procedure call graph + semantic test vectors + supersession register + cross-document audit + checksum manifest |

No executable source, configuration, DOCX, or PDF file is modified; no Stage 1A–1Q lettered artifact is modified.
The specification conforms to R1–R6 while preserving B1–B9, C1–C10, D1–D9, E1–E10, F1–F9, G1–G11, H1–H9,
I-01…I-08, J1–J9, K1–K8, L1–L6, M1–M6, N1–N4, O1–O5, P1–P5, and Q1–Q7. Name remains PoCol; A1 baseline unchanged.
The prohibited rebranded-algorithm-name variants are not used anywhere in this document.
