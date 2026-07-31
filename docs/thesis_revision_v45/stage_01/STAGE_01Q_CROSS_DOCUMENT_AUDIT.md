# Stage 1Q — Cross-Document Audit (acceptance gates)

The twelve Stage-1Q acceptance gates, verified by procedure-call-graph, event-scheduling, and corpus analysis
over `docs/thesis_revision_v45/stage_01/` (not string search alone), plus cross-document consistency and
protected/historical-artifact verification. Name remains **PoCol**; mechanism is **the idle policy within
PoCol**; no property is claimed; the A1 baseline (`8.420833333 kWh`) is unchanged.

| # | Acceptance gate | Result |
|--:|-----------------|--------|
| 1 | Every final recovery census receives a monotonic version | **PASS** — §9 `CommitRecoveryCensus` increments `recovery_census_seq` → `RecoveryCensusVersion` and publishes `latest_recovery_census[episode]` on every final census while in `SECURITY_RECOVERY`. `STAGE_01Q_RECOVERY_CENSUS_VERSION_AUDIT.md`; TV127 |
| 2 | A newer census invalidates an older decision even without producing a new completion | **PASS** — §9 `ReconcilePendingRecoveryDecisions` marks a contradicted pending decision SUPERSEDED (removing it) even when the warranted outcome is NONE (breach before deadline). `STAGE_01Q_RECOVERY_CENSUS_VERSION_AUDIT.md`; TV127 |
| 3 | No recovery decision applies before the final census of its application `event_time` | **PASS** — §10a `RecoveryCompletionDueEvent` records due + refreshes the census only; §0.7d runs `ApplyRecoveryCompletionAfterEpilogue` AFTER `FinalizeEventTimeSecurityCensus(t)`, applying only if bound-version = latest AND outcome matches the final census. `STAGE_01Q_RECOVERY_APPLICATION_ORDER_AUDIT.md`; TV128/TV133 |
| 4 | A failed superseding schedule cannot revive or preserve the old decision | **PASS** — §9 `ReconcilePendingRecoveryDecisions` supersedes + removes the old decision BEFORE `SeatRecoveryCompletion`; a rejected schedule → `SCHEDULE_FAILED` (not added to the pending set); the old decision stays `SUPERSEDED`. `STAGE_01Q_DECISION_SUPERSESSION_AUDIT.md`; TV129 |
| 5 | Pending decisions are explicit identities, not one ambiguous boolean | **PASS** — §0.8 `RECOVERY_DECISION_STATUS` + `recovery_decisions` (per-decision record) + `pending_recovery_decisions[episode]` (a SET); the Stage-1P boolean `recovery_completion_pending` is removed. `STAGE_01Q_DECISION_SUPERSESSION_AUDIT.md`; TV129 |
| 6 | Security census has one canonical atomic writer | **PASS** — §0.8a `CommitSecurityCensus` is the SOLE writer (three `census_source` values); §0.9/§9/§9a call it; a grep finds no direct `SET latest_security_census`/`SET security_census_dirty` outside it. `STAGE_01Q_SECURITY_CENSUS_WRITER_AUDIT.md`; TV130 |
| 7 | RunContext and RoundContext ownership are explicit and complete | **PASS** — §1.0 `RunContext` + `RunInitialise` (once per run); §1.1 `RoundInitialise(config, RunContext, prior_state)` inits only per-round registries and RETURNS every per-round recovery registry; `RunEventLoopToHorizon` uses `RunContext.RunHookContext`. `STAGE_01Q_RUNTIME_CONTEXT_OWNERSHIP_AUDIT.md`; TV131 |
| 8 | The horizon hook uses a tagged namespace and deterministic replay state | **PASS** — §0.2 `envelope_namespace in {ORDINARY_EVENT, RUN_HOOK}` + `hook_id`; §20b `CloseRoundAtHorizon` uses `RUN_HOOK` + `HorizonHookID`, collision-free by tag, with IN_PROGRESS/APPLIED replay state. `STAGE_01Q_RUN_HOOK_NAMESPACE_AUDIT.md`; TV132 |
| 9 | Recovery completion time is deterministic and fully defined | **PASS** — §9 `SeatRecoveryCompletion` uses `target_time = t + configured_recovery_completion_delay` (config `> 0`); `t_next` removed; `target_time > T` → `horizon_deferred` (CANCELLED, not enqueued). `STAGE_01Q_RUN_HOOK_NAMESPACE_AUDIT.md`; TV134 |
| 10 | TV127 through TV134 pass on paper | **PASS** — `STAGE_01Q_SEMANTIC_TEST_VECTORS.md`; every vector names exact procedures + preconditions with no assumed guard/transition; A1 preserved |
| 11 | No executable source/configuration/DOCX/PDF changes | **PASS** — `git diff` confined to `docs/thesis_revision_v45/stage_01/`; draft-42 `2c3afdc5…`, draft-44 `a31400bc…` byte-identical |
| 12 | No Stage-1A through Stage-1P historical artifact is modified | **PASS** — `git diff --name-only <base>` shows no `STAGE_01[A-P]_*` file; supersessions recorded in `STAGE_01Q_SUPERSESSION_REGISTER.md` |

## Cross-document consistency

| Check | Result |
|-------|--------|
| Name always **PoCol**; mechanism only "the idle policy within PoCol" | **PASS** — 0 functional uses of any rebranded variant; the only corpus occurrences are pre-existing prohibition clauses inherited from the base, none used as a name; Stage-1Q deliverables use zero literal forbidden strings |
| Versioned census + reconcile (pseudocode ↔ round SM ↔ terminology) | **PASS** — §9 `CommitRecoveryCensus`/`ReconcilePendingRecoveryDecisions` ↔ round SM §3.10 ↔ Stage-1Q addendum (Q1) |
| Two-step application (pseudocode ↔ round SM) | **PASS** — §10a `RecoveryCompletionDueEvent`/`ApplyRecoveryCompletionAfterEpilogue` ↔ round SM §3.10/R14 (Q2) |
| One census writer (pseudocode ↔ catalogue ↔ terminology) | **PASS** — §0.8a `CommitSecurityCensus` ↔ catalogue I17 ↔ Stage-1Q addendum (Q4) |
| Explicit ownership (pseudocode) | **PASS** — §1.0/§1.1 `RunInitialise`/`RoundInitialise` explicit RETURNS (Q5) |
| Tagged run-hook namespace + deterministic time (pseudocode ↔ traceability) | **PASS** — §0.2/§20b/§9 ↔ R117 (Q6/Q7) |
| Call graph has no dangling calls | **PASS** — 62 defined; 0 called-but-undefined (`STAGE_01Q_PROCEDURE_CALL_GRAPH.md`) |
| Traceability updated | **PASS** — R112–R118 (Q1–Q7 + TV127–TV134) added |
| A1 discipline | **PASS** — baseline `8.420833333 kWh` unchanged; Q1–Q7 are freshness / ordering / ownership / identity corrections, never a change to how time or energy is counted |

## Supersession notes

All Stage-1Q supersessions of Stage-1P statements are recorded in `STAGE_01Q_SUPERSESSION_REGISTER.md`
(7 entries) — historical `STAGE_01[A-P]_*` files are NOT modified.

## Git delta

Modified (5, all un-suffixed normative): `STAGE_01_PROTOCOL_PSEUDOCODE.md`, `STAGE_01_ROUND_STATE_MACHINE.md`,
`STAGE_01_INVARIANT_CATALOGUE.md`, `STAGE_01_TERMINOLOGY.md`, `STAGE_01_TRACEABILITY_MATRIX.csv`. Added (11):
the `STAGE_01Q_*` deliverables. No file outside `docs/thesis_revision_v45/stage_01/` is touched; no
`STAGE_01[A-P]_*` file is modified.

## Result

All twelve acceptance gates pass and all cross-document consistency checks hold. The specification conforms to
Q1–Q7 while preserving B1–B9, C1–C10, D1–D9, E1–E10, F1–F9, G1–G11, H1–H9, I-01…I-08, J1–J9, K1–K8, L1–L6,
M1–M6, N1–N4, O1–O5, and P1–P5. Name remains PoCol; no new consensus feature; documentation only; protected
drafts byte-identical; Stage-1A–1P lettered artifacts frozen; A1 baseline unchanged. The prohibited
rebranded-algorithm-name variants are not used anywhere in this document.
