# Stage 1U — Cross-Document Audit (acceptance gates)

The fifteen Stage-1U acceptance gates, verified by procedure-call-graph, signature/call-site, event-scheduling, and
corpus analysis over `docs/thesis_revision_v45/stage_01/` (not string search alone), plus cross-document consistency
and protected/historical-artifact verification. Name remains **PoCol**; mechanism is **the idle policy within PoCol**;
no property is claimed; the A1 baseline (`8.420833333 kWh`) is unchanged.

| # | Acceptance gate | Result |
|--:|-----------------|--------|
| 1 | Reserve-dependent recovery is reachable without treating a breached census as RESTORED | **PASS** — §9c the breach-before-deadline epilogue seats a `RecoveryWorkDueEvent` (`ClassifyRecoveryWork`/`SeatRecoveryWork`) and `ApplyRecoveryWorkAfterEpilogue` activates the reserve while the round stays `SECURITY_RECOVERY`; `outcome_consistent_with_census(RESTORED)` (breach = false) is NOT weakened. `STAGE_01U_RECOVERY_WORK_OUTCOME_SEPARATION_AUDIT.md`; TV163 |
| 2 | `RecoveryOutcome` and recovery-work actions are distinct | **PASS** — `RECOVERY_WORK_ACTION` (§0.8) is never a `RecoveryOutcome` and never marked `APPLIED`; the recovery-work hook sets NO `recovery_outcome_finalised`. `STAGE_01U_RECOVERY_WORK_OUTCOME_SEPARATION_AUDIT.md`; TV163 |
| 3 | `PostEpilogueSchedulingContext` reaches every nested `ScheduleEvent` | **PASS** — §9c/§10a `ApplyRecoveryWorkAfterEpilogue`/`ApplyRecoveryAssignmentContinuationAfterEpilogue` → `CommitRecoveryAssignmentPlan(POST_EPILOGUE(pctx))` → `ReserveActivate`/`RangeReassign`/`StartWake` → `ScheduleEvent(post_epilogue_context)`. `STAGE_01U_POST_EPILOGUE_CONTEXT_THREADING_AUDIT.md`, `STAGE_01U_PROCEDURE_SIGNATURE_CALL_AUDIT.md`; TV164 |
| 4 | Zero-latency post-epilogue wakes are strictly later than the source time | **PASS** — §10 `StartWake`'s `POST_EPILOGUE` branch targets `next_representable_simulation_time(source)` for a zero-latency wake; `ScheduleEvent` requires `target > source` (S7). `STAGE_01U_POST_EPILOGUE_CONTEXT_THREADING_AUDIT.md`; TV164 |
| 5 | A generation is published only after a successful enqueue | **PASS** — §9c `SeatRecoveryWork` advances `recovery_work_seq` and publishes the work record / event ref ONLY inside `IF result = scheduled(...)`. `STAGE_01U_CONTINUATION_REARM_LIVENESS_AUDIT.md`; TV165 |
| 6 | Scheduler failure cannot strand an `APPLYING` decision | **PASS** — a rejected seat records an explicit disposition, reports no pending state, and does not advance the identity; a branch-C `APPLYING` decision is always resolved in one continuation-hook invocation; `pending_recovery_work` is the recovery-work controller. `STAGE_01U_CONTINUATION_REARM_LIVENESS_AUDIT.md`; TV165/TV167 |
| 7 | Every due fact is explicitly consumed / cancelled / superseded | **PASS** — §0.8 `CONTINUATION_DUE_STATUS`; the post-epilogue hooks set `CONSUMED`/`SUPERSEDED`, `CancelActiveRecoveryEpisode` sets `CANCELLED`. `STAGE_01U_CONTINUATION_DUE_CONSUMPTION_AUDIT.md`; TV166 |
| 8 | The final event-time assertion is executable against a declared due status | **PASS** — §0.7d `ProcessEventTime` asserts no `continuation_due_status = DUE` / `due_status = DUE` remains at `t` — an explicit status, not a timestamp field. `STAGE_01U_CONTINUATION_DUE_CONSUMPTION_AUDIT.md`; TV166 |
| 9 | Recovery installation uses named prepare/commit/rollback procedures | **PASS** — §9c/§10a `PrepareRecoveryAssignmentPlan` / `CommitRecoveryAssignmentPlan` / `RollbackRecoveryAssignmentPlan`. `STAGE_01U_RECOVERY_INSTALL_TRANSACTION_AUDIT.md`; TV168/TV169/TV170 |
| 10 | No opaque `INSTALL` / `UNDO` executable macro remains | **PASS** — the macros are removed; a corpus check finds no `INSTALL the disjoint assignment set` / `UNDO the partial install` executable statement. `STAGE_01U_RECOVERY_INSTALL_TRANSACTION_AUDIT.md` |
| 11 | Every `CompleteAssignmentPhase` caller handles its disposition | **PASS** — §2/§19/§10a `PrepareParticipantsForNewRound`, `TemplateRefresh`, and the recovery installation each capture + branch on `assignment_phase_completed \| assignment_phase_failed(reason)`. `STAGE_01U_ASSIGNMENT_PHASE_CALLER_AUDIT.md`; TV171/TV172 |
| 12 | Continuation-due census provenance is distinct | **PASS** — §0.8/§10a `RECOVERY_CONTINUATION_DUE` (continuation) and `RECOVERY_WORK_DUE` (work), distinct from `RECOVERY_COMPLETION_DUE`; `CommitSecurityCensus` has seven named sources. `STAGE_01U_CENSUS_PROVENANCE_AUDIT.md`; TV173 |
| 13 | TV163 through TV173 pass on paper | **PASS** — `STAGE_01U_SEMANTIC_TEST_VECTORS.md`; every vector names exact procedures + preconditions with no assumed guard/transition; A1 preserved |
| 14 | No executable source/configuration/DOCX/PDF changes | **PASS** — `git diff` confined to `docs/thesis_revision_v45/stage_01/`; draft-42 `2c3afdc5…`, draft-44 `a31400bc…` byte-identical |
| 15 | No Stage-1A through Stage-1T historical artifact is modified | **PASS** — `git diff --name-only <base>` shows no `STAGE_01[A-T]_*` file; supersessions recorded in `STAGE_01U_SUPERSESSION_REGISTER.md` |

## Cross-document consistency

| Check | Result |
|-------|--------|
| Name always **PoCol**; mechanism only "the idle policy within PoCol" | **PASS** — 0 functional uses of any rebranded variant; the only corpus occurrences are pre-existing prohibition clauses inherited from the base; Stage-1U deliverables use zero literal forbidden strings |
| Recovery-work vs outcome separation (pseudocode ↔ round SM ↔ catalogue ↔ terminology ↔ traceability) | **PASS** — §9/§9c/§10a ↔ round SM §3.10 (U1)/R13 ↔ catalogue I16 ↔ Stage-1U addendum ↔ R142 |
| Scheduling-context threading (pseudocode ↔ signature audit ↔ traceability) | **PASS** — §0.8/§9c/§10a ↔ `STAGE_01U_PROCEDURE_SIGNATURE_CALL_AUDIT.md` ↔ R143 |
| Atomic re-arm + due consumption (pseudocode ↔ terminology ↔ traceability) | **PASS** — §9c/§0.7d ↔ Stage-1U addendum ↔ R144/R145 |
| Named install transaction (pseudocode ↔ catalogue ↔ traceability) | **PASS** — §9c/§10a/§0.8 ↔ catalogue I16 ↔ R146 |
| CompleteAssignmentPhase disposition at every caller (pseudocode ↔ traceability) | **PASS** — §2/§19/§10a ↔ R147 |
| Census provenance (pseudocode ↔ catalogue ↔ traceability) | **PASS** — §0.8/§9a/§9c/§10a ↔ catalogue I17 ↔ R148 |
| Call graph has no dangling calls | **PASS** — 76 defined; 0 called-but-undefined (`STAGE_01U_PROCEDURE_CALL_GRAPH.md`); `ReserveActivate` regains a live caller |
| Traceability updated | **PASS** — R142–R149 (U1–U7 + TV163–TV173) added |
| A1 discipline | **PASS** — baseline `8.420833333 kWh` unchanged; U1–U7 are control-flow / scheduling / lifecycle / provenance corrections, never a change to how time or energy is counted |

## Supersession notes

All Stage-1U supersessions of Stage-1T (and earlier) statements are recorded in
`STAGE_01U_SUPERSESSION_REGISTER.md` (7 entries) — historical `STAGE_01[A-T]_*` files are NOT modified; the Stage-1T
terminology and traceability addenda describing the superseded reserve-dependent continuation are preserved as
historical records.

## Git delta

Modified (5, all un-suffixed normative): `STAGE_01_PROTOCOL_PSEUDOCODE.md`, `STAGE_01_ROUND_STATE_MACHINE.md`,
`STAGE_01_INVARIANT_CATALOGUE.md`, `STAGE_01_TERMINOLOGY.md`, `STAGE_01_TRACEABILITY_MATRIX.csv`. Added (14): the
`STAGE_01U_*` deliverables. No file outside `docs/thesis_revision_v45/stage_01/` is touched; no `STAGE_01[A-T]_*` file
is modified.

## Result

All fifteen acceptance gates pass and all cross-document consistency checks hold. The specification conforms to U1–U7
while preserving B1–B9, C1–C10, D1–D9, E1–E10, F1–F9, G1–G11, H1–H9, I-01…I-08, J1–J9, K1–K8, L1–L6, M1–M6, N1–N4,
O1–O5, P1–P5, Q1–Q7, R1–R6, S1–S7, and T1–T7. Name remains PoCol; no new consensus feature; documentation only;
protected drafts byte-identical; Stage-1A–1T lettered artifacts frozen; A1 baseline unchanged. The prohibited
rebranded-algorithm-name variants are not used anywhere in this document.
