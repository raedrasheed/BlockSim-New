# Stage 1O — Cross-Document Audit (acceptance gates)

The thirteen Stage-1O acceptance gates, verified by procedure-call-graph, event-scheduling, and corpus
analysis over `docs/thesis_revision_v45/stage_01/` (not string search alone), plus cross-document consistency
and protected/historical-artifact verification. Name remains **PoCol**; mechanism is **the idle policy within
PoCol**; no property is claimed; the A1 baseline (`8.420833333 kWh`) is unchanged.

| # | Acceptance gate | Result |
|--:|-----------------|--------|
| 1 | `FinalizeSimulationRun` is REMOVED from the ordinary event queue (run-level hook only) | **PASS** — §20a `FinalizeSimulationRun` INPUTS carry NO `dispatch_envelope`; it is invoked by `RunEventLoopToHorizon` after `ProcessEventTime(T)`; §0.7g-driver removes its seating row. `STAGE_01O_HORIZON_FINALISATION_AUDIT.md`; TV111/TV113 |
| 2 | `ProcessEventTime` is the SOLE event-loop driver, never re-entered from a handler; no internal drain in `FinalizeSimulationRun` | **PASS** — the former `DRAIN the event queue to quiescence for every event_time <= T` is removed from §20a; `RunEventLoopToHorizon` (§0.7d-run) is the only caller of `ProcessEventTime`; no handler calls it. TV113 |
| 3 | `CloseRoundAtHorizon` (§20b) is a named hook interposed BETWEEN the `T` drain and the `T` epilogue; distinct horizon-end disposition; ONE deterministic horizon envelope; NO residency settle | **PASS** — §0.7d interposes `CloseRoundAtHorizon` when `is_horizon AND round nonterminal`; §20b records `horizon_end_disposition <- closed_at_horizon`, uses one `horizon_envelope`, calls `CloseRoundAssignments` only. TV111 |
| 4 | `FinalizeSimulationRun` performs ONLY the single `FINAL_RUN_END` settle + I5/I6/I7 + `run_finalised` | **PASS** — §20a body is `SettleResidencyBoundary(FINAL_RUN_END, (RunID, RUN_END))` then I5/I6/I7 asserts then `run_finalised <- true`; guarded by `run_finalised`. `STAGE_01O_HORIZON_FINALISATION_AUDIT.md`; TV112 |
| 5 | `RUN_FINALISE` is removed from the microphase queue map; documented as a post-`ProcessEventTime(T)` run-level hook | **PASS** — §0.7g note "RUN_FINALISE is NOT in this queue map"; §0.7g-driver and §21 mark `FinalizeSimulationRun`/`CloseRoundAtHorizon` as run-level hooks (never enqueued). TV113 |
| 6 | `ScheduleEvent` rejects `target_event_time > T` (`post_horizon_event_rejected`); `= T` legal; no pending ordinary event `> T` | **PASS** — §0.7e adds the horizon rule before delta-cycle derivation; `run_horizon_T` is an `EventQueueContext` field; the SOLE enqueue interface guarantees no stranded post-horizon event. `STAGE_01O_POST_HORIZON_EVENT_AUDIT.md`; TV114 |
| 7 | A floor-restored decision at `t = T` seats no `CompleteSecurityRecovery`; records `run_ending_no_recovery_action` | **PASS** — §9 floor-restored branch guards `IF t = run_horizon_T` → `RECORD run_ending_no_recovery_action` → RETURN; nothing scheduled past `T`. `STAGE_01O_POST_HORIZON_EVENT_AUDIT.md`; TV115 |
| 8 | `RecoveryOutcome in {RESTORED, UNRECOVERABLE}` replaces the contradictory precondition/branch; R13 and R14 both executable | **PASS** — §10a precondition is `RecoveryOutcome in {RESTORED, UNRECOVERABLE}`; RESTORED → A/B/C, UNRECOVERABLE → D → `RoundAbort(floor_unrecoverable)`; the Stage-1N `floor_result = restored` contradiction is removed. `STAGE_01O_RECOVERY_OUTCOME_AUDIT.md`; TV116 |
| 9 | A named seated source supplies UNRECOVERABLE, giving R14 a concrete source and call path (round only) | **PASS** — §9a `RecoveryDeadlineEvent` is seated via `ScheduleEvent` on entry to `SECURITY_RECOVERY`, carrying `RecoveryEpisodeID`+epoch; it seats `CompleteSecurityRecovery(UNRECOVERABLE)`; branch D closes ONLY the round (N1). `STAGE_01O_RECOVERY_OUTCOME_AUDIT.md`; TV116 |
| 10 | Recovery-episode idempotence: at most one completion seated and one outcome applied per `RecoveryEpisodeID`; duplicate/stale → deterministic no-op via registry keys | **PASS** — §0.8 `recovery_completion_pending`/`recovery_outcome_finalised` keyed by `RecoveryEpisodeID`; §9/§9a seat-once, §10a apply-once (`recovery_completion_duplicate_noop`/`recovery_completion_stale_noop`). `STAGE_01O_RECOVERY_EPISODE_AUDIT.md`; TV117 |
| 11 | No statement places the security decision before certificate/discovery; `FinalizeTimestampSecurityCensus` replaced by `FinalizeEventTimeSecurityCensus` (0 functional occurrences) | **PASS** — round SM §2.6 rewritten (epilogue after certificate/discovery); the rename is applied at round SM §2.6, catalogue I17, terminology Stage-1H bullet, traceability R51; 0 functional references remain (the only mentions of the old name are corrective/supersession statements recording the replacement). `STAGE_01O_ROUND_STATE_RECONCILIATION_AUDIT.md`; TV118 |
| 12 | Call graph has no dangling calls; TV111–TV118 pass on paper | **PASS** — 54 procedures defined, 0 called-but-undefined (`STAGE_01O_PROCEDURE_CALL_GRAPH.md`); every vector names exact procedures + preconditions with no assumed guard/transition (`STAGE_01O_SEMANTIC_TEST_VECTORS.md`) |
| 13 | No executable/config/DOCX/PDF change; protected drafts byte-identical; no Stage-1A..1N lettered artifact modified; A1 unchanged | **PASS** — `git diff` confined to `docs/thesis_revision_v45/stage_01/`; draft-42 `2c3afdc5…`, draft-44 `a31400bc…` byte-identical; `git diff --name-only <base>` shows no `STAGE_01[A-N]_*` file; A1 baseline `8.420833333 kWh` unchanged |

## Cross-document consistency

| Check | Result |
|-------|--------|
| Name always **PoCol**; mechanism only "the idle policy within PoCol" | **PASS** — 0 functional uses of any rebranded variant; the only occurrences in the corpus are pre-existing prohibition clauses inherited from the base (Stage 1N), none used as an algorithm name; Stage-1O deliverables use zero literal forbidden strings |
| Horizon sequence (pseudocode ↔ round SM ↔ energy model ↔ catalogue) | **PASS** — run driver drains via `ProcessEventTime`; `CloseRoundAtHorizon` closes a nonterminal round; `FinalizeEventTimeSecurityCensus(T)` terminal-stale-noop; run-level `FinalizeSimulationRun` settles + reconciles — consistent across pseudocode §0.7d/§0.7d-run/§20a/§20b, round SM §3.14, energy §3, catalogue I19 (O1) |
| Binding horizon rule (pseudocode ↔ traceability) | **PASS** — `ScheduleEvent` rejects `> T`; no recovery action past `T`; R101 records O2 (O2) |
| Executable R13/R14 with sources (pseudocode ↔ round SM) | **PASS** — `CompleteSecurityRecovery` (§10a) ↔ round SM R13/R14/§2.5/§3.10; `RecoveryDeadlineEvent` (§9a) is the UNRECOVERABLE source (O3) |
| Recovery-episode idempotence registry (pseudocode ↔ traceability) | **PASS** — `RecoveryEpisodeID`-keyed registries; R103 records O4 (O4) |
| Security decision only as post-quiescence epilogue (pseudocode ↔ round SM ↔ terminology ↔ catalogue) | **PASS** — §2.6/I17/terminology renamed and reordered; R51/R104 (O5) |
| Single boundary owner preserved | **PASS** — `SettleResidencyBoundary` reached only from `RoundInitialise` (REBASE) and `FinalizeSimulationRun` (FINAL_RUN_END); `CloseRoundAtHorizon`/`RoundAbort` call `CloseRoundAssignments` (record-only) (M4/O1) |
| Call graph has no dangling calls | **PASS** — 54 defined; 0 called-but-undefined (`STAGE_01O_PROCEDURE_CALL_GRAPH.md`) |
| Traceability updated | **PASS** — R51 renamed; R100–R105 (O1–O5 + TV111–TV118) added |
| Terminology addendum | **PASS** — Stage-1O addendum covers O1–O5; Stage-1H/Stage-1N pointers updated |
| A1 discipline | **PASS** — baseline `8.420833333 kWh` unchanged; O1–O5 are ordering / reachability / idempotence / naming corrections, never a change to how time or energy is counted |

## Note on the superseded name

`FinalizeTimestampSecurityCensus` has ZERO functional (defined-procedure) references in the normative corpus:
the pseudocode uses only the defined `FinalizeEventTimeSecurityCensus`. The old name survives ONLY inside
corrective/supersession statements that name it to record its replacement (`STAGE_01_TERMINOLOGY.md` Stage-1H
bullet and Stage-1O addendum; `STAGE_01_TRACEABILITY_MATRIX.csv` R104; `STAGE_01O_SUPERSESSION_REGISTER.md`).
Historical Stage-1A..1N lettered artifacts retain the old name as a frozen historical record.

## Supersession notes

All Stage-1O supersessions of prior-stage statements are recorded in `STAGE_01O_SUPERSESSION_REGISTER.md`
(7 entries) — historical `STAGE_01[A-N]_*` files are NOT modified.

## Git delta

Modified (6, all un-suffixed normative): `STAGE_01_PROTOCOL_PSEUDOCODE.md`, `STAGE_01_ROUND_STATE_MACHINE.md`,
`STAGE_01_ENERGY_MODEL_SPECIFICATION.md`, `STAGE_01_INVARIANT_CATALOGUE.md`, `STAGE_01_TERMINOLOGY.md`,
`STAGE_01_TRACEABILITY_MATRIX.csv`. Added (11): the `STAGE_01O_*` deliverables. No file outside
`docs/thesis_revision_v45/stage_01/` is touched; no `STAGE_01[A-N]_*` file is modified.

## Result

All thirteen acceptance gates pass and all cross-document consistency checks hold. The specification conforms
to O1–O5 while preserving B1–B9, C1–C10, D1–D9, E1–E10, F1–F9, G1–G11, H1–H9, I-01…I-08, J1–J9, K1–K8, L1–L6,
M1–M6, and N1–N4. Name remains PoCol; no new consensus feature; documentation only; protected drafts
byte-identical; Stage-1A–1N lettered artifacts frozen; A1 baseline unchanged. The prohibited
rebranded-algorithm-name variants are not used anywhere in this document.
