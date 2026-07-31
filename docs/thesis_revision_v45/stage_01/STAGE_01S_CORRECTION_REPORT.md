# Stage 1S — Correction Report (full-envelope & deferred-recovery-atomicity lock)

**Branch.** `thesis-v45-pocol-stage1s-full-envelope-deferred-recovery-atomicity-lock`
**Base.** `0693556bdb0caa227bdfc414055c9a470f3f2280` (Stage 1R).
**Scope.** Documentation only — no executable source, configuration, DOCX, PDF, or experiment changes.
Protected DOCX drafts byte-identical (draft-42 `2c3afdc5…`, draft-44 `a31400bc…`); Stage 1A–1R lettered
artifacts unmodified (A–R-lock).

**Naming rule (binding).** The algorithm is **PoCol**; the mechanism is **the idle policy within PoCol**. No
property is claimed. The A1 baseline is unchanged (`8.420833333 kWh`). No new consensus feature — S1…S7 make the
miner-transition identity a single explicit object, make branch-C recovery genuinely deferred and atomic, give a
terminal round an explicit recovery-episode cleanup, centralise the census dirty-flag clearing, make the primary
epilogue an unconditional single invocation, and give post-epilogue scheduling an explicit context.

## S1 — One explicit transition-envelope object

`ApplyMinerStateTransition` (§0.9) now takes ONE `transition_envelope` object
(`{envelope_namespace, event_time, delta_cycle, event_seq, hook_id}`), destructured at the top of EFFECTS, and
builds `TransitionEventID` EXCLUSIVELY from that object plus the transition-specific fields. All **14** direct call
sites now pass exactly `transition_envelope = dispatch_envelope`; the R3 "namespace fields travel implicitly"
clause is WITHDRAWN — no identity field is decomposed or omitted at any executable call site. The horizon path
`CloseRoundAtHorizon` (§20b) → `CloseRoundAssignments` (§17a) → `EnterLowPowerListen` (§7) /
`ApplyMinerStateTransition` threads the SAME RUN_HOOK envelope + `HorizonHookID` throughout. Audits:
`STAGE_01S_FULL_ENVELOPE_AUDIT.md`, `STAGE_01S_PROCEDURE_SIGNATURE_CALL_AUDIT.md`. TV143/TV144.

## S2 — Branch C must not mutate before continuation seating succeeds

`CompleteSecurityRecovery` (§10a) branch C now (1) computes `t_cont`, (2) validates `t_cont <= T`, (3) seats ONE
`RecoveryAssignmentContinuationEvent` (through the S7 `PostEpilogueSchedulingContext`), and (4) only then returns
`DEFERRED`. It does NOT transition to `ASSIGNMENT` before a successful seat. A seat rejection or `t_cont > T`
leaves `round_state = SECURITY_RECOVERY`, `current_recovery_episode` set, the decision `APPLY_FAILED` /
`HORIZON_DEFERRED`, and no continuation pending. Audit: `STAGE_01S_DEFERRED_RECOVERY_ATOMICITY_AUDIT.md`.
TV145.

## S3 — Branch C remains APPLYING until the continuation completes

Seating is NOT applying RESTORED: the decision stays `APPLYING`, `recovery_outcome_finalised` is not set,
`current_recovery_episode` is not cleared, and `CompleteSecurityRecovery` returns `DEFERRED`. The
`RecoveryAssignmentContinuationEvent` (§10a) carries `RecoveryEpisodeID`, `RecoveryDecisionID`, `RecoveryOutcome`,
bound `RecoveryCensusVersion`, `RoundID`, `TemplateID`, `state_version`, and at its later `event_time`: verifies
the still-current APPLYING decision + round still `SECURITY_RECOVERY`; prepares + validates the disjoint plan;
transitions `SECURITY_RECOVERY → ASSIGNMENT`; installs the valid disjoint set; runs `CompleteAssignmentPhase →
HASHING`; and ONLY after HASHING marks `APPLIED`, finalises RESTORED, removes from pending, clears the episode. A
failure before the transition → `APPLY_FAILED` and stays `SECURITY_RECOVERY` (episode preserved); a failure after
a state mutation → declared recovery-finalising `RoundAbort` (never leaves `ASSIGNMENT` with an active episode and
no live continuation). Audit: `STAGE_01S_DEFERRED_RECOVERY_ATOMICITY_AUDIT.md`. TV146/TV147/TV148.

## S4 — Terminal recovery cleanup

`CancelActiveRecoveryEpisode` (§9), invoked by `CloseRoundAssignments` (§17a) for every terminal closure EXCEPT
the recovery-finalising abort, cancels every pending/scheduled/applying decision and its queued
`RecoveryCompletionDueEvent` / `RecoveryAssignmentContinuationEvent`, records `recovery_episode_disposition =
TERMINAL_CANCELLED`, and clears `current_recovery_episode` — without setting `recovery_outcome_finalised`. The
`recovery_finalising` flag (threaded to `RoundAbort`/`CloseRoundAssignments`) marks a closure that IS the
application of a recovery outcome (branch D, or the continuation's install-fail abort), so its cleanup is skipped.
The invariant `current_recovery_episode != null IFF round_state = SECURITY_RECOVERY` holds. Audit:
`STAGE_01S_TERMINAL_RECOVERY_CLEANUP_AUDIT.md`. TV149.

## S5 — One security-census dirty-flag clearer

`SettleSecurityCensusDirty` (§0.8a) is the SOLE clearer of `security_census_dirty[event_time]`, with
`settlement_kind in {PRIMARY_EPILOGUE, POST_RECOVERY_APPLICATION}`. `FinalizeEventTimeSecurityCensus` (§9) clears
it for `PRIMARY_EPILOGUE`; `FinalizePostRecoveryApplicationState` (§10a) for `POST_RECOVERY_APPLICATION`. The
data-model comment and every normative statement now say so — the earlier "FinalizeEventTimeSecurityCensus is the
sole clearer" claim is removed. `CommitSecurityCensus` remains the sole setter of `dirty = true` and the sole
writer of the latest census. Audit: `STAGE_01S_CENSUS_SETTLEMENT_OWNERSHIP_AUDIT.md`. TV151.

## S6 — Exactly one primary epilogue invocation

`ProcessEventTime` (§0.7d) now calls `FinalizeEventTimeSecurityCensus(RoundContext, t)` EXACTLY ONCE and
UNCONDITIONALLY after the ordinary drain and horizon close; the `IF security_census_dirty[t]` guard is removed —
the procedure owns that check and returns `no_census_change` when nothing is dirty. `ApplyRecoveryCompletionAfterEpilogue`
and `FinalizePostRecoveryApplicationState` run after it in the declared order. Audit:
`STAGE_01S_CENSUS_SETTLEMENT_OWNERSHIP_AUDIT.md`. TV150.

## S7 — Explicit post-epilogue scheduling context

`ScheduleEvent` (§0.7e) gains a `post_epilogue_context` input and a `PostEpilogueSchedulingContext` structure
(`{source_event_time, source_envelope, EventQueueContext, RunContext}`). ScheduleEvent may be called from exactly
three declared sources; a post-epilogue call (the branch-C continuation seat) MUST target `target_event_time >
source_event_time` and derives `delta_cycle = 0`, so a post-epilogue caller can never enqueue at
`source_event_time` (R1 made structural); `event_creation_seq` is still minted solely by `ScheduleEvent`. Audit:
`STAGE_01S_POST_EPILOGUE_SCHEDULER_AUDIT.md`. TV152.

## Summary of changed / added artifacts

| Artifact | Change |
|----------|--------|
| `STAGE_01_PROTOCOL_PSEUDOCODE.md` | §0.7d unconditional single epilogue (S6); §0.7e `PostEpilogueSchedulingContext` + `ScheduleEvent` post-epilogue rule (S7); §0.7g-driver continuation seating row (S3); §0.8 registries (`continuation_event_ref`, `HORIZON_DEFERRED`, `recovery_episode_disposition`/`RECOVERY_EPISODE_DISPOSITION`, IFF invariant, S3/S4) + `RoundInitialise` (S4); §0.8a `CommitSecurityCensus` note + `SettleSecurityCensusDirty` (S5); §0.9 `ApplyMinerStateTransition` one-object signature + destructure + all 14 call sites (S1); §9 `CancelActiveRecoveryEpisode` (S4) + `ReconcilePendingRecoveryDecisions` cancels continuation (S3) + `FinalizeEventTimeSecurityCensus` uses SettleSecurityCensusDirty (S5); §10a `ApplyRecoveryCompletionAfterEpilogue` three-kind disposition (S3) + `CompleteSecurityRecovery` seat-before-mutate/DEFERRED (S2/S3) + `RecoveryAssignmentContinuationEvent` seven-step worker (S3) + `FinalizePostRecoveryApplicationState` uses SettleSecurityCensusDirty (S5); §17a `CloseRoundAssignments` recovery_finalising + S4 cleanup + recovery-event cancel; §20 `RoundAbort` recovery_finalising (S4) |
| `STAGE_01_ROUND_STATE_MACHINE.md` | §3.10 S1/S2/S3/S4/S5/S6/S7 paragraphs; RECOVERY_DECISION_STATUS enum (+HORIZON_DEFERRED); R13 row (deferred branch C) |
| `STAGE_01_INVARIANT_CATALOGUE.md` | I17 enforcement point: single dirty-flag clearer (S5) + unconditional single epilogue (S6) |
| `STAGE_01_TERMINOLOGY.md` | Stage-1S addendum (S1–S7) |
| `STAGE_01_TRACEABILITY_MATRIX.csv` | R126–R133 (S1–S7 + TV143–TV152) |
| `STAGE_01S_*` (12 new deliverables) | this report + full-envelope / deferred-recovery-atomicity / terminal-recovery-cleanup / census-settlement-ownership / post-epilogue-scheduler / procedure-signature-call audits + procedure call graph + semantic test vectors + supersession register + cross-document audit + checksum manifest |

No executable source, configuration, DOCX, or PDF file is modified; no Stage 1A–1R lettered artifact is modified.
The specification conforms to S1–S7 while preserving B1–B9, C1–C10, D1–D9, E1–E10, F1–F9, G1–G11, H1–H9,
I-01…I-08, J1–J9, K1–K8, L1–L6, M1–M6, N1–N4, O1–O5, P1–P5, Q1–Q7, and R1–R6. Name remains PoCol; A1 baseline
unchanged. The prohibited rebranded-algorithm-name variants are not used anywhere in this document.
