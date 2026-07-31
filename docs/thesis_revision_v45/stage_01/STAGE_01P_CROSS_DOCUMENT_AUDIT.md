# Stage 1P — Cross-Document Audit (acceptance gates)

The twelve Stage-1P acceptance gates, verified by procedure-call-graph, event-scheduling, and corpus analysis
over `docs/thesis_revision_v45/stage_01/` (not string search alone), plus cross-document consistency and
protected/historical-artifact verification. Name remains **PoCol**; mechanism is **the idle policy within
PoCol**; no property is claimed; the A1 baseline (`8.420833333 kWh`) is unchanged.

| # | Acceptance gate | Result |
|--:|-----------------|--------|
| 1 | `ProcessEventTime(T)` runs exactly once even when no ordinary event exists at `T` | **PASS** — §0.7d-run `RunEventLoopToHorizon` loops `t < T`, then `IF T not in finalised_event_times: ProcessEventTime(T, is_horizon = true, allow_empty_horizon = true)`; §0.7d permits an empty drain at `T`. `STAGE_01P_HORIZON_SENTINEL_AUDIT.md`; TV119/TV120 |
| 2 | A nonterminal round cannot reach `FinalizeSimulationRun` without horizon closure | **PASS** — §20a `FinalizeSimulationRun` asserts `round_state ∈ {ROUND_ACCEPTED, ROUND_ABORTED}`; the only path to terminal at `T` for a nonterminal round is `CloseRoundAtHorizon` (§20b) inside `ProcessEventTime(T)`. TV119 |
| 3 | `T` is always entered into `finalised_event_times` | **PASS** — the synthetic `ProcessEventTime(T)` always runs and unconditionally `ADD t to finalised_event_times` after the epilogue. `STAGE_01P_HORIZON_SENTINEL_AUDIT.md`; TV119/TV120 |
| 4 | The horizon-close envelope has a declared deterministic identity and replay guard | **PASS** — §0.7e `RunHookContext` + `HorizonHookID = (RunID, T, HORIZON_CLOSE)` + reserved `RUN_HOOK_CYCLE`; §20b guards on `applied_run_hook_ids` → `horizon_close_duplicate_noop`; no collision with an ordinary envelope. `STAGE_01P_RUN_HOOK_ENVELOPE_AUDIT.md`; TV125 |
| 5 | `RecoveryDeadlineEvent` does not select an outcome before the event-time epilogue | **PASS** — §9a records `recovery_deadline_reached` + `CaptureSecurityCensusOnRecoveryDeadline` only; it seats no completion and selects no outcome; the epilogue `SecurityFloorEvaluate` (§9) decides. `STAGE_01P_RECOVERY_DEADLINE_DECISION_AUDIT.md`; TV121/TV122 |
| 6 | Same-timestamp floor restoration is visible before the deadline outcome | **PASS** — `CaptureSecurityCensusOnRecoveryDeadline` writes a census that a later same-`t` `ApplyMinerStateTransition` (a floor-restoring `WakeCompleteEvent`) OVERWRITES; the post-quiescence epilogue reads the FINAL census → RESTORED. `STAGE_01P_RECOVERY_DEADLINE_DECISION_AUDIT.md`; TV121 |
| 7 | `completion_pending` is set only after successful enqueue | **PASS** — §9 `SeatRecoveryCompletion` sets `recovery_completion_pending` only in the `IF result = scheduled(...)` branch; a rejection records the disposition and returns `recovery_completion_not_seated`. `STAGE_01P_RECOVERY_COMPLETION_ATOMICITY_AUDIT.md`; TV124 |
| 8 | No completion is attempted after or beyond `T` | **PASS** — §9 `SeatRecoveryCompletion` horizon guard `IF t = run_horizon_T` records `run_ending_no_recovery_action` and seats nothing; §0.7e `ScheduleEvent` rejects `target_event_time > T` (O2). `STAGE_01P_RECOVERY_COMPLETION_ATOMICITY_AUDIT.md`; TV123 |
| 9 | A stale recovery decision cannot be applied | **PASS** — §10a `CompleteSecurityRecovery` returns `recovery_decision_stale_noop` unless `RecoveryDecisionID = latest_recovery_decision[episode].decision_id`; §0.8 `latest_recovery_decision`. `STAGE_01P_RECOVERY_DECISION_VERSION_AUDIT.md`; TV126 |
| 10 | TV119 through TV126 pass on paper | **PASS** — `STAGE_01P_SEMANTIC_TEST_VECTORS.md`; every vector names exact procedures + preconditions with no assumed guard/transition; A1 preserved |
| 11 | No executable source/configuration/DOCX/PDF changes | **PASS** — `git diff` confined to `docs/thesis_revision_v45/stage_01/`; draft-42 `2c3afdc5…`, draft-44 `a31400bc…` byte-identical |
| 12 | No Stage-1A through Stage-1O historical artifact is modified | **PASS** — `git diff --name-only <base>` shows no `STAGE_01[A-O]_*` file; supersessions recorded in `STAGE_01P_SUPERSESSION_REGISTER.md`, not by rewriting prior evidence |

## Cross-document consistency

| Check | Result |
|-------|--------|
| Name always **PoCol**; mechanism only "the idle policy within PoCol" | **PASS** — 0 functional uses of any rebranded variant; the only corpus occurrences are pre-existing prohibition clauses inherited from the base, none used as a name; Stage-1P deliverables use zero literal forbidden strings |
| Horizon sentinel (pseudocode ↔ round SM) | **PASS** — `RunEventLoopToHorizon` synthetic `ProcessEventTime(T)` ↔ round SM §3.14 (P1); the horizon sequence runs once even with an empty `T` queue |
| Deterministic run-hook envelope (pseudocode ↔ catalogue) | **PASS** — §0.7e/§20b `RunHookContext`/`HorizonHookID`/`RUN_HOOK_CYCLE` ↔ catalogue I19 (no double transition energy/boundary) (P2) |
| Deadline is a fact, epilogue decides (pseudocode ↔ round SM) | **PASS** — §9a/`CaptureSecurityCensusOnRecoveryDeadline` ↔ round SM §2.5/§3.10/R14 (P3) |
| Atomic seating (pseudocode) | **PASS** — `SeatRecoveryCompletion` sets pending only on `scheduled`; a decision at `T` records `run_ending_no_recovery_action` (P4) |
| Decision versioning (pseudocode ↔ §0.7g-driver tie key) | **PASS** — `RecoveryDecisionID` guard in §10a; `(RoundID, RecoveryEpisodeID, RecoveryDecisionID)` tie key in §0.7g-driver (P5) |
| Call graph has no dangling calls | **PASS** — 56 defined; 0 called-but-undefined (`STAGE_01P_PROCEDURE_CALL_GRAPH.md`) |
| Terminology addendum | **PASS** — Stage-1P addendum covers P1–P5 |
| Traceability updated | **PASS** — R106–R111 (P1–P5 + TV119–TV126) added |
| A1 discipline | **PASS** — baseline `8.420833333 kWh` unchanged; P1–P5 are horizon-step / identity / decision-timing / atomicity / versioning corrections, never a change to how time or energy is counted |

## Supersession notes

All Stage-1P supersessions of Stage-1O statements are recorded in `STAGE_01P_SUPERSESSION_REGISTER.md`
(7 entries) — historical `STAGE_01[A-O]_*` files are NOT modified.

## Git delta

Modified (5, all un-suffixed normative): `STAGE_01_PROTOCOL_PSEUDOCODE.md`, `STAGE_01_ROUND_STATE_MACHINE.md`,
`STAGE_01_INVARIANT_CATALOGUE.md`, `STAGE_01_TERMINOLOGY.md`, `STAGE_01_TRACEABILITY_MATRIX.csv`. Added (11):
the `STAGE_01P_*` deliverables. No file outside `docs/thesis_revision_v45/stage_01/` is touched; no
`STAGE_01[A-O]_*` file is modified.

## Result

All twelve acceptance gates pass and all cross-document consistency checks hold. The specification conforms to
P1–P5 while preserving B1–B9, C1–C10, D1–D9, E1–E10, F1–F9, G1–G11, H1–H9, I-01…I-08, J1–J9, K1–K8, L1–L6,
M1–M6, N1–N4, and O1–O5. Name remains PoCol; no new consensus feature; documentation only; protected drafts
byte-identical; Stage-1A–1O lettered artifacts frozen; A1 baseline unchanged. The prohibited
rebranded-algorithm-name variants are not used anywhere in this document.
