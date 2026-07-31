# Stage 1O — Correction Report (horizon/recovery final lock)

**Branch.** `thesis-v45-pocol-stage1o-horizon-recovery-final-lock`
**Base.** `ffc6f9d3f900f97bcfe18be5ee53d3ee7620d981` (Stage 1N).
**Scope.** Documentation only — no executable source, configuration, DOCX, PDF, or experiment changes.
Protected DOCX drafts byte-identical (draft-42 `2c3afdc5…`, draft-44 `a31400bc…`); Stage 1A–1N lettered
artifacts unmodified (A–N-lock).

**Naming rule (binding).** Algorithm is **PoCol**; mechanism is **the idle policy within PoCol**. No
property (energy, security, fairness, incentive) is claimed. The A1 baseline is unchanged
(`8.420833333 kWh`); any modeled energy change is attributable ONLY to reduced active power-time. No new
consensus feature — O1…O5 close the run-end horizon sequence, bind event scheduling to the horizon, make the
existing round-SM R14 recovery contract reachable/executable, add recovery-episode idempotence, and reconcile
the round-state ordering with the event-time security epilogue.

## O1 — Horizon-finalisation refactor

`FinalizeSimulationRun` (§20a) is REMOVED from the ordinary event queue and NO LONGER drains the queue or
closes a round itself. The event loop is driven by a single driver: `ProcessEventTime` (§0.7d) is the SOLE
event-loop driver and is never re-entered from a handler; the RUN-LEVEL driver `RunEventLoopToHorizon`
(§0.7d-run) calls `ProcessEventTime` for every `event_time <= T` and THEN invokes `FinalizeSimulationRun` as a
post-`ProcessEventTime(T)` run-level HOOK. **Canonical horizon sequence:** (1) process every `event_time < T`;
(2) drain all ordinary and delta-cycle events AT `T` to quiescence; (3) if the round is nonterminal, run the
new named hook `CloseRoundAtHorizon` (§20b) — it closes the round via `CloseRoundAssignments`, transitions it
to `ROUND_ABORTED` with a DISTINCT horizon-end disposition, uses ONE deterministic horizon envelope, and
settles NO residency; (4) run the `T` epilogue `FinalizeEventTimeSecurityCensus(T)`, which — the round now
terminal — is a `terminal_stale_noop` that clears `security_census_dirty[T]`; (5) ONLY THEN invoke the
run-level `FinalizeSimulationRun`, which performs ONLY the single `SettleResidencyBoundary(mode =
FINAL_RUN_END, boundary_id = (RunID, RUN_END))` + the I5/I6/I7 reconciliation + sets `run_finalised`. The
former internal `DRAIN the event queue to quiescence for every event_time <= T` is REMOVED. `RUN_FINALISE` is
REMOVED from the ordinary microphase queue map (§0.7g) and the §0.7g-driver seating table; `FinalizeSimulationRun`
and `CloseRoundAtHorizon` are documented as run-level hooks, never queued (§0.7g-driver/§21). Updated:
pseudocode §0.7d/§0.7d-run/§0.7g/§0.7g-driver/§20a/§20b/§21; round SM §3.14; energy model §3; catalogue I19;
terminology (Stage-1O addendum). Audit: `STAGE_01O_HORIZON_FINALISATION_AUDIT.md`. TV111/TV112/TV113.

## O2 — Binding horizon rule for event scheduling

`ScheduleEvent` (§0.7e) now REJECTS any `target_event_time > run_horizon_T`: it records
`post_horizon_event` (audit-only) and returns `post_horizon_event_rejected` — the event is NOT enqueued
(deterministic). `target_event_time = T` is LEGAL; only `> T` is rejected. Because `ScheduleEvent` is the SOLE
enqueue interface, NO pending ordinary event can ever have `event_time > T`, and the run driver drains every
`event_time <= T`, so nothing is stranded past `T`. `run_horizon_T` is a per-run field of `EventQueueContext`
(§0.7e), initialised at run start and preserved across rounds. A floor-restored decision AT `T`
(`SecurityFloorEvaluate` §9) records `run_ending_no_recovery_action` and seats NO `CompleteSecurityRecovery`
(which would need `t_next > T`), so no recovery participation action can change `H_active` after the final
decision at `T`; the round is instead closed by `CloseRoundAtHorizon`. The rule governs `WakeCompleteEvent`,
`HashWorkEvent`, `CertificateArrival`, `BlockAcceptancePoint`, `ResumeFromPause`, `LeaseExpiry`,
`CompleteSecurityRecovery`, `RecoveryDeadlineEvent`, and monitoring/participation events alike. Updated:
pseudocode §0.7e/§9. Audit: `STAGE_01O_POST_HORIZON_EVENT_AUDIT.md`. TV114/TV115.

## O3 — Reachable FloorUnrecoverable (RecoveryOutcome)

`CompleteSecurityRecovery` (§10a) had a CONTRADICTION at Stage 1N: precondition `floor_result = restored` yet
a branch `IF NOT floor_result = restored: RoundAbort(...)` that could never run, so R14 (FloorUnrecoverable)
was not executable. O3 REPLACES the precondition/branch with `RecoveryOutcome in {RESTORED, UNRECOVERABLE}`:
RESTORED → branches A (live contexts → `SOLUTION_PROPAGATION`), B (no context/no change → `HASHING`), C
(redistribution → `ASSIGNMENT → CompleteAssignmentPhase → HASHING`, no new template); UNRECOVERABLE → branch D
→ `RoundAbort(reason = floor_unrecoverable)` (round only, N1). A NAMED, seated source makes R14 REACHABLE:
`RecoveryDeadlineEvent` (§9a) is seated through `ScheduleEvent` on entry to `SECURITY_RECOVERY` carrying the
`RecoveryEpisodeID` + epoch; when it fires with the floor still breached it seats a `CompleteSecurityRecovery`
carrying `RecoveryOutcome = UNRECOVERABLE`. A concrete source and call path now runs from a recovery episode
to `RoundAbort(floor_unrecoverable)` via branch D — R13 and R14 are both executable with sources. Updated:
pseudocode §0.8 (`RecoveryOutcome` enum)/§9/§9a/§10a; round SM §2.5/§3.10/R13/R14 rows. Audit:
`STAGE_01O_RECOVERY_OUTCOME_AUDIT.md`. TV115/TV116.

## O4 — Recovery-episode idempotence

Recovery completion is made idempotent by a per-episode registry (not prose). §0.8 adds `recovery_episode_seq`,
`RecoveryEpisodeID = (RoundID, recovery_episode_seq)`, `current_recovery_episode`, `recovery_completion_pending`
(map), and `recovery_outcome_finalised` (map), all reset by `RoundInitialise` (§1). On entry to
`SECURITY_RECOVERY` the episode is minted. **Seat-once key:** both completion sources (the floor-restored
epilogue and `RecoveryDeadlineEvent`) check/set `recovery_completion_pending[episode]`, so AT MOST ONE
`CompleteSecurityRecovery` is seated per episode — whichever source fires first wins, the other is a
deterministic no-op (`floor_restored_completion_already_pending` / `recovery_deadline_superseded_noop`).
**Apply-once key:** `CompleteSecurityRecovery` (§10a) checks `recovery_outcome_finalised[RecoveryEpisodeID]`
FIRST (duplicate → `recovery_completion_duplicate_noop`), then a stale-epoch/episode guard
(`recovery_completion_stale_noop`), then finalises the outcome once and clears `current_recovery_episode`.
Updated: pseudocode §0.8/§1/§9/§9a/§10a. Audit: `STAGE_01O_RECOVERY_EPISODE_AUDIT.md`. TV116/TV117.

## O5 — Round-state reconciliation and name replacement

No statement places the security decision BEFORE certificate/discovery events. The canonical order is: ordinary
events + all delta_cycles → horizon closure at `T` if needed → the event-time epilogue
`FinalizeEventTimeSecurityCensus` (I-01/I-02, keyed by `event_time` alone, run AFTER quiescence) → the
run-level `FinalizeSimulationRun` at `T`. The round SM §2.6 same-timestamp ordering is rewritten so
certificate/discovery precede the post-quiescence epilogue. The superseded name
`FinalizeTimestampSecurityCensus` is replaced everywhere in the un-suffixed normative corpus by
`FinalizeEventTimeSecurityCensus` (the real defined procedure): round SM §2.6, invariant catalogue I17
enforcement point, terminology Stage-1H bullet, and traceability R51. Historical Stage-1A–1N lettered
artifacts are NOT modified; supersessions are recorded in `STAGE_01O_SUPERSESSION_REGISTER.md`. Updated:
`STAGE_01_ROUND_STATE_MACHINE.md`, `STAGE_01_INVARIANT_CATALOGUE.md`, `STAGE_01_TERMINOLOGY.md`,
`STAGE_01_ENERGY_MODEL_SPECIFICATION.md`, `STAGE_01_TRACEABILITY_MATRIX.csv`. Audit:
`STAGE_01O_ROUND_STATE_RECONCILIATION_AUDIT.md`. TV118.

## Summary of changed / added artifacts

| Artifact | Change |
|----------|--------|
| `STAGE_01_PROTOCOL_PSEUDOCODE.md` | §0.7d `ProcessEventTime` horizon interposition + `RunEventLoopToHorizon` (O1); §0.7d-run run-driver note (O1); §0.7e `run_horizon_T` + binding horizon rule (O2); §0.7g `RECOVERY_DEADLINE`/`RECOVERY_COMPLETE` + RUN_FINALISE not queued (O1/O3); §0.7g-driver run-level hooks removed from table + `RecoveryDeadlineEvent` row (O1/O3); §0.8 `RecoveryOutcome`/episode registries + `run_horizon_T` (O2/O3/O4); §1 RoundInitialise resets episode registries + EQ `run_horizon_T` (O2/O4); §9 SecurityFloorEvaluate breach-entry (episode + `RecoveryDeadlineEvent`) + floor-restored (O2 guard + O4 idempotence + `RecoveryOutcome`) (O2/O3/O4); §9a `RecoveryDeadlineEvent` (O3); §10a `CompleteSecurityRecovery` (`RecoveryOutcome`, O4 idempotence, R14 branch) (O3/O4); §20a `FinalizeSimulationRun` narrowed (O1); §20b `CloseRoundAtHorizon` (O1); §21 RUN_FINALISE/RECOVERY_DEADLINE/RECOVERY_COMPLETE run-level ordering (O1/O3) |
| `STAGE_01_ROUND_STATE_MACHINE.md` | §2.5 exit conditions (RecoveryDeadlineEvent/RecoveryOutcome/episode); §2.6 same-timestamp ordering (epilogue after certificate/discovery; rename) (O5); §3.10 (two recovery sources + RecoveryOutcome + episode); §3.14 (O1 canonical horizon sequence); R14 row reachable via seated source (O3) |
| `STAGE_01_INVARIANT_CATALOGUE.md` | I17 enforcement point rename → `FinalizeEventTimeSecurityCensus` epilogue (O5); I19 enforcement point adds `CloseRoundAtHorizon`, narrows `FinalizeSimulationRun` (O1) |
| `STAGE_01_ENERGY_MODEL_SPECIFICATION.md` | §3 boundary-settle paragraph: O1 clause (drain + horizon-close moved out; finaliser only settle + reconcile; A1 unchanged) |
| `STAGE_01_TERMINOLOGY.md` | Stage-1H bullet rename/relocation (O5); Stage-1N `FinalizeSimulationRun` bullet O1 supersession pointer; Stage-1O addendum (O1–O5) |
| `STAGE_01_TRACEABILITY_MATRIX.csv` | R51 rename + epilogue keying (O5); R100–R105 added (O1–O5 + TV111–TV118) |
| `STAGE_01O_*` (11 new deliverables) | this report + horizon-finalisation / post-horizon-event / recovery-outcome / recovery-episode / round-state-reconciliation audits + procedure call graph + semantic test vectors + supersession register + cross-document audit + checksum manifest |

No executable source, configuration, DOCX, or PDF file is modified; no Stage 1A–1N lettered artifact is
modified. The specification conforms to O1–O5 while preserving B1–B9, C1–C10, D1–D9, E1–E10, F1–F9, G1–G11,
H1–H9, I-01…I-08, J1–J9, K1–K8, L1–L6, M1–M6, and N1–N4. Name remains PoCol; the idle policy within PoCol is
described as a mechanism only; A1 baseline unchanged. The prohibited rebranded-algorithm-name variants are not
used anywhere in this document.
