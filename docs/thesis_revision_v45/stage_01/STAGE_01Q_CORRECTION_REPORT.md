# Stage 1Q — Correction Report (recovery-freshness & runtime-context lock)

**Branch.** `thesis-v45-pocol-stage1q-recovery-freshness-runtime-context-lock`
**Base.** `bb3564b94aea21ea5a265012e6b9c0bc40774463` (Stage 1P).
**Scope.** Documentation only — no executable source, configuration, DOCX, PDF, or experiment changes.
Protected DOCX drafts byte-identical (draft-42 `2c3afdc5…`, draft-44 `a31400bc…`); Stage 1A–1P lettered
artifacts unmodified (A–P-lock).

**Naming rule (binding).** Algorithm is **PoCol**; mechanism is **the idle policy within PoCol**. No property
is claimed. The A1 baseline is unchanged (`8.420833333 kWh`). No new consensus feature — Q1…Q7 version the
recovery census, apply the recovery outcome only after the dispatch-time epilogue, make decision supersession
atomic and explicit, centralise census writing, make run/round ownership explicit, tag the run-hook namespace,
and make the recovery completion time deterministic.

## Q1 — Version every final recovery census

§0.8 adds `recovery_census_seq` (per-episode monotonic) and `latest_recovery_census[episode]` (record:
RecoveryEpisodeID, RecoveryCensusVersion, event_time, RoundID, TemplateID, state_version, H_active, H_honest,
H_adversarial, q_adv, breach, deadline_reached). While in `SECURITY_RECOVERY`, the epilogue
(`SecurityFloorEvaluate`, §9) calls `CommitRecoveryCensus` (increment the version, publish the record) and
`ReconcilePendingRecoveryDecisions` (supersede a contradicted pending decision — EVEN when the new census
produces no completion — and re-affirm a consistent one to the latest version). A decision binds to a
`RecoveryCensusVersion`, so freshness is judged against every final census, not merely a newer
`RecoveryDecisionID`. Audit: `STAGE_01Q_RECOVERY_CENSUS_VERSION_AUDIT.md`. TV127.

## Q2 — Do not apply recovery before the dispatch-time epilogue

The recovery exit is a TWO-STEP contract (§10a): `RecoveryCompletionDueEvent` (queued) records the decision is
due and refreshes the census — NO transition, NO `RoundAbort`; `ApplyRecoveryCompletionAfterEpilogue`
(post-epilogue hook, called by `ProcessEventTime` after `FinalizeEventTimeSecurityCensus(t)`) applies the
outcome ONLY if the decision's `RecoveryCensusVersion` equals the latest AND the outcome still matches the
FINAL census. `CompleteSecurityRecovery` becomes an INTERNAL branch dispatch called only by the hook.
`ProcessEventTime` runs epilogue → apply → a bounded re-evaluation (the recovery-exit state change may re-dirty
t; the round is then HASHING/terminal so no new decision). So a RESTORED decision never leaves recovery under a
newer breach census. Audit: `STAGE_01Q_RECOVERY_APPLICATION_ORDER_AUDIT.md`. TV128/TV133.

## Q3 — Atomic decision supersession

§0.8 adds `RECOVERY_DECISION_STATUS in {CREATED, SCHEDULED, SUPERSEDED, APPLIED, SCHEDULE_FAILED, CANCELLED}`,
`recovery_decisions` (per-decision record), and `pending_recovery_decisions[episode]` (a SET, replacing the
Stage-1P boolean `recovery_completion_pending`). `ReconcilePendingRecoveryDecisions` marks a contradicted
decision SUPERSEDED and cancels its due event BEFORE any replacement is seated; `SeatRecoveryCompletion` adds a
decision to the pending set ONLY on scheduler success (`SCHEDULE_FAILED` otherwise). A failed superseding
schedule leaves the old decision SUPERSEDED (never revived) and the round stays `SECURITY_RECOVERY`. Audit:
`STAGE_01Q_DECISION_SUPERSESSION_AUDIT.md`. TV129.

## Q4 — Centralise security-census writing

§0.8a adds `CommitSecurityCensus`, the SOLE atomic writer of `latest_security_census[event_time]` +
`security_census_dirty[event_time]`, with three `census_source` values {MINER_STATE_TRANSITION,
APPLICABILITY_ENTRY, RECOVERY_DEADLINE}. `ApplyMinerStateTransition` (§0.9),
`CaptureSecurityCensusOnApplicabilityEntry` (§9), and `CaptureSecurityCensusOnRecoveryDeadline` (§9a) CALL it
rather than writing the maps directly. The "two writers"/"third writer"/"sole writer" statements are removed;
`dirty[t] = true ⇒ latest[t] exists` is structural. Audit: `STAGE_01Q_SECURITY_CENSUS_WRITER_AUDIT.md`. TV130.

## Q5 — Define RunContext and runtime ownership

§1.0 adds `RunContext` {RunID, EventQueueContext, RunHookContext, rebased_boundaries, run_finalised,
run_horizon_T, per-run census maps} and `RunInitialise`, which creates all per-run fields ONCE. `RoundInitialise`
(§1.1) now takes `RunContext` explicitly, initialises only per-round registries, preserves `RunContext`, and
RETURNS every per-round recovery registry explicitly (recovery_episode_seq, current_recovery_episode,
recovery_deadline_reached, recovery_census_seq, latest_recovery_census, recovery_decision_seq,
recovery_decisions, pending_recovery_decisions, latest_recovery_decision, recovery_outcome_finalised).
`RunEventLoopToHorizon` obtains `RunHookContext` through `RunContext.RunHookContext`. Audit:
`STAGE_01Q_RUNTIME_CONTEXT_OWNERSHIP_AUDIT.md`. TV131.

## Q6 — Tagged run-hook envelope namespace

§0.2 adds `envelope_namespace in {ORDINARY_EVENT, RUN_HOOK}` and an optional `hook_id`. Ordinary `ScheduleEvent`
envelopes are `ORDINARY_EVENT`; `CloseRoundAtHorizon` (§20b) uses `RUN_HOOK` + `hook_id = (RunID, T,
HORIZON_CLOSE)`. Collision freedom derives from the TAG (not the `RUN_HOOK_CYCLE` number); a `TransitionEventID`
includes `envelope_namespace`/`hook_id`. `applied_run_hook_ids` carries an IN_PROGRESS/APPLIED state so a
partial horizon close cannot replay as a second full close. Audit: `STAGE_01Q_RUN_HOOK_NAMESPACE_AUDIT.md`.
TV132/TV133.

## Q7 — Define the recovery completion time

`SeatRecoveryCompletion` (§9) computes `target_time = t + configured_recovery_completion_delay` (declared
config `> 0`, or the next-representable instant), replacing the undefined `t_next`; the `RecoveryCompletionDueEvent`
is seated at that deterministic time. If `target_time > T`, nothing is enqueued, the decision records
`horizon_deferred` (status CANCELLED), a superseded decision stays invalid, and `CloseRoundAtHorizon` governs
run end. Audit: `STAGE_01Q_RUN_HOOK_NAMESPACE_AUDIT.md`. TV134.

## Summary of changed / added artifacts

| Artifact | Change |
|----------|--------|
| `STAGE_01_PROTOCOL_PSEUDOCODE.md` | §0.2 `envelope_namespace`/`hook_id` (Q6); §0.7d ProcessEventTime epilogue+apply+bounded-re-eval (Q2); §0.7e ScheduleEvent ORDINARY_EVENT + RunHookContext IN_PROGRESS/APPLIED (Q6); §0.8 recovery registries (Q1/Q3/Q7 config); §0.8a `CommitSecurityCensus` (Q4); §0.9/§9/§9a route to CommitSecurityCensus (Q4); §1.0 `RunContext`+`RunInitialise`, §1.1 RoundInitialise receives RunContext + explicit RETURNS (Q5); §9 SecurityFloorEvaluate versioning + reconcile + SeatRecoveryCompletion, `CommitRecoveryCensus`, `ReconcilePendingRecoveryDecisions`, `outcome_consistent_with_census` (Q1/Q2/Q3/Q7); §10a `RecoveryCompletionDueEvent` + `ApplyRecoveryCompletionAfterEpilogue` + internal `CompleteSecurityRecovery` (Q2); §20b CloseRoundAtHorizon tagged envelope + IN_PROGRESS/APPLIED (Q6); §0.7g/§0.7g-driver/§21 renamed queued event + post-epilogue hook |
| `STAGE_01_ROUND_STATE_MACHINE.md` | §3.10 (versioned census, two-step application, RESTORED not applied under breach, explicit status); R14 row (epilogue selects UNRECOVERABLE from final census; applied post-epilogue) |
| `STAGE_01_INVARIANT_CATALOGUE.md` | I17 enforcement point: `CommitSecurityCensus` one canonical writer, three sources (Q4) |
| `STAGE_01_TERMINOLOGY.md` | Stage-1Q addendum (Q1–Q7) |
| `STAGE_01_TRACEABILITY_MATRIX.csv` | R112–R118 (Q1–Q7 + TV127–TV134) |
| `STAGE_01Q_*` (11 new deliverables) | this report + recovery-census-version / recovery-application-order / decision-supersession / security-census-writer / runtime-context-ownership / run-hook-namespace audits + procedure call graph + semantic test vectors + supersession register + cross-document audit + checksum manifest |

No executable source, configuration, DOCX, or PDF file is modified; no Stage 1A–1P lettered artifact is
modified. The specification conforms to Q1–Q7 while preserving B1–B9, C1–C10, D1–D9, E1–E10, F1–F9, G1–G11,
H1–H9, I-01…I-08, J1–J9, K1–K8, L1–L6, M1–M6, N1–N4, O1–O5, and P1–P5. Name remains PoCol; A1 baseline
unchanged. The prohibited rebranded-algorithm-name variants are not used anywhere in this document.
