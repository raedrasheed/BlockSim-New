# Stage 1M — Cross-Document Audit (acceptance gates)

The twelve Stage-1M acceptance gates, verified by procedure-call-graph, event-envelope, and corpus
analysis over `docs/thesis_revision_v45/stage_01/` (not string search alone), plus cross-document
consistency and protected/historical-artifact verification. Name remains **PoCol**; mechanism is **the
idle policy within PoCol**; no property is claimed; the A1 baseline (`8.420833333 kWh`) is unchanged.

| # | Acceptance gate | Result |
|--:|-----------------|--------|
| 1 | Every `ApplyMinerStateTransition` call passes all three event-envelope fields explicitly | **PASS** — all 14 LIVE hook calls spell out `event_time = dispatch_envelope.event_time`, `delta_cycle = …`, `event_seq = …` (MinerRegister T1/T2 via `dispatch_envelope.*`); the literal `event_seq = dispatch_envelope.event_seq` occurs exactly 14 times, one per call site. The 15th `grep` match is §0.3 prose, and the only `, now,` occurrence is the §0.9 prohibition text. `STAGE_01M_TRANSITION_ENVELOPE_AUDIT.md`; TV98 |
| 2 | No transition-envelope shorthand remains | **PASS** — §0.9 removes the positional shorthand and forbids reading `EQ.current_*` implicitly; every hook-reaching procedure carries an explicit `dispatch_envelope` (26 procedures verified). `STAGE_01M_TRANSITION_ENVELOPE_AUDIT.md` |
| 3 | Every entry into HASHING captures a coherent applicability census | **PASS** — §2a-bis `TransitionRoundState` captures the census on entry to any floor-applicable state; `CompleteAssignmentPhase`, `ScheduleSolutionPropagation`, and `HandlePropagationFailure`'s `SOLUTION_PROPAGATION→HASHING` re-entry all route through it (the re-entry captures even with no paused miner / unchanged `H_active`). `STAGE_01M_APPLICABILITY_ENTRY_AUDIT.md`; TV99 |
| 4 | A PENDING lease expiry cancels wake and resolves WAKING before reassignment | **PASS** — §12 `CASE PENDING` cancels the exact `WakeCompleteEvent`, moves a `WAKING` holder `WAKING→OFFLINE` (`lease_expired_while_waking`), CLOSES the head, preserves accepted coverage, then reassigns only after CLOSED. `STAGE_01M_PENDING_LEASE_EXPIRY_AUDIT.md`; TV100 |
| 5 | WakeCompleteEvent cannot activate a CLOSED assignment | **PASS** — §0.10 `WakeCompleteEvent` BEGINS with a stale-target guard (`status ∈ {PENDING, PAUSED}`, current epoch, own live head) returning `stale_wake_noop`; independent of the HashWorkEvent G9 guard. `STAGE_01M_PENDING_LEASE_EXPIRY_AUDIT.md`; TV101 |
| 6 | One procedure owns round-boundary residency closure | **PASS** — §1a `SettleResidencyBoundary` (`REBASE_TO_NEXT_ROUND` / `FINAL_RUN_END`, idempotent via `boundary_id`) is the SOLE boundary owner; `RoundInitialise` and `RoundAbort` call it; the withdrawn `RebaseResidencyAtRoundBoundary`/`Finalize`/`Begin` have no call site. `STAGE_01M_RESIDENCY_SINGLE_OWNER_AUDIT.md`; TV102 |
| 7 | CloseRoundAssignments performs no competing residency finalisation | **PASS** — §17a: the in-line `finalise state durations and energy to the exact closure time` line is REMOVED (only removal-reference comments remain); it records `round_terminal_time` ONLY. `STAGE_01M_RESIDENCY_SINGLE_OWNER_AUDIT.md`; TV102 |
| 8 | Every enqueue operation has a target microphase | **PASS** — §0.7g canonical event-type→microphase mapping; every real `ScheduleEvent` enqueue (StartWake ×2, ScheduleNextHashWork, ScheduleSolutionPropagation ×2, HandlePropagationFailure) supplies an explicit `target_microphase`; no bare `SCHEDULE event` enqueue remains. `STAGE_01M_SCHEDULER_MICROPHASE_AUDIT.md`; TV103 |
| 9 | Every event-producing loop is deterministically sorted | **PASS** — `TemplateRefresh` (`SORT eligible BY MinerID`), `CloseRoundAssignments`/`CloseTemplateAssignments` (`SORT BY (holder MinerID, AssignmentID)`), and the recipient/resume loops (`SORT BY MinerID`) all sort before seq assignment (G7/J4). `STAGE_01M_SCHEDULER_MICROPHASE_AUDIT.md`; TV103 |
| 10 | TV98 through TV103 pass on paper | **PASS** — `STAGE_01M_SEMANTIC_TEST_VECTORS.md`; every vector names exact procedures + preconditions; no guard/cancellation assumed that is not in the pseudocode; A1 preserved |
| 11 | No executable source, configuration, DOCX, or PDF changes | **PASS** — `git diff` confined to `docs/thesis_revision_v45/stage_01/`; draft-42 `2c3afdc5…`, draft-44 `a31400bc…` byte-identical |
| 12 | No Stage-1A..1L historical artifact is modified | **PASS** — `git diff --name-only <base>` shows no `STAGE_01[A-L]_*` file; supersessions recorded in `STAGE_01M_SUPERSESSION_REGISTER.md`, not by rewriting prior evidence |

## Cross-document consistency

| Check | Result |
|-------|--------|
| Name always **PoCol**; mechanism only "the idle policy within PoCol" | **PASS** — 0 occurrences of any forbidden name string in the normative corpus |
| Explicit envelope threading (pseudocode ↔ call graph) | **PASS** — every hook-reaching procedure threads `dispatch_envelope`; all 15 hook calls explicit (M1) |
| Census on every floor-applicable entry | **PASS** — `TransitionRoundState` captures for `{HASHING, SOLUTION_PROPAGATION, SECURITY_RECOVERY}`; epilogue `→SECURITY_RECOVERY` is the sole documented exception (M2) |
| Executable wake handling | **PASS** — PENDING lease expiry cancels the wake + resolves WAKING; `WakeCompleteEvent` stale guard first (M3) |
| Single residency-boundary owner | **PASS** — `SettleResidencyBoundary` (REBASE/FINAL_RUN_END); `CloseRoundAssignments` no finalisation; I19 + energy-model I5 updated (M4) |
| Microphase-complete, deterministic enqueue | **PASS** — §0.7g mapping; explicit microphase per enqueue; loops sorted (M5) |
| Invariant catalogue updated | **PASS** — I19 amended for the unified single boundary owner (M4) |
| Terminology addendum | **PASS** — Stage-1M addendum covers M1–M6; residency entry annotated renamed/generalised |
| Traceability updated | **PASS** — R77/R87 updated to `SettleResidencyBoundary`; R89–R94 (M1–M6) |
| Call graph has no dangling calls | **PASS** — 49 defined; 0 called-but-undefined (`STAGE_01M_PROCEDURE_CALL_GRAPH.md`) |
| A1 discipline | **PASS** — baseline `8.420833333 kWh` unchanged; the M4 settle changes only how time is split across boundaries, never the total |

## Supersession notes

All Stage-1M supersessions of prior-stage statements are recorded in
`STAGE_01M_SUPERSESSION_REGISTER.md` (6 entries) — historical `STAGE_01[A-L]_*` files are NOT modified.
TV96 (frozen Stage-1L) is superseded on paper by TV102, not by editing the frozen vector.

## Git delta

Modified (5, all un-suffixed normative): `STAGE_01_PROTOCOL_PSEUDOCODE.md`,
`STAGE_01_INVARIANT_CATALOGUE.md`, `STAGE_01_TERMINOLOGY.md`, `STAGE_01_TRACEABILITY_MATRIX.csv`,
`STAGE_01_ENERGY_MODEL_SPECIFICATION.md`. Added (11): the `STAGE_01M_*` deliverables. No file outside
`docs/thesis_revision_v45/stage_01/` is touched; no `STAGE_01[A-L]_*` file is modified.

## Result

All twelve acceptance gates pass and all cross-document consistency checks hold. The specification
conforms to M1–M6 while preserving B1–B9, C1–C10, D1–D9, E1–E10, F1–F9, G1–G11, H1–H9, I-01…I-08,
J1–J9, K1–K8, and L1–L6. Name remains PoCol; no new consensus feature; documentation only; protected
drafts byte-identical; Stage-1A–1L lettered artifacts frozen; A1 baseline unchanged.
