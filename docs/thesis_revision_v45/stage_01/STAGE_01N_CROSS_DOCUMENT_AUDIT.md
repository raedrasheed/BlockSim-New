# Stage 1N — Cross-Document Audit (acceptance gates)

The ten Stage-1N acceptance gates, verified by procedure-call-graph, event-envelope, and corpus analysis
over `docs/thesis_revision_v45/stage_01/` (not string search alone), plus cross-document consistency and
protected/historical-artifact verification. Name remains **PoCol**; mechanism is **the idle policy within
PoCol**; no property is claimed; the A1 baseline (`8.420833333 kWh`) is unchanged.

| # | Acceptance gate | Result |
|--:|-----------------|--------|
| 1 | `RoundAbort` never performs `FINAL_RUN_END` settlement | **PASS** — §20 `RoundAbort`'s executable body is only `CloseRoundAssignments` + `TRANSITION round_state -> ROUND_ABORTED`; the former `SettleResidencyBoundary(FINAL_RUN_END)` and horizon-`T` reconciliation are removed. `STAGE_01N_RUN_FINALISATION_AUDIT.md`; TV104 |
| 2 | An early aborted round can be followed by `RoundInitialise` | **PASS** — §20 records `round_terminal_time` at the abort `event_time` and returns control; round SM R21 (`ROUND_ABORTED → ROUND_INITIALISING`) restarts; the next `RoundInitialise` performs `SettleResidencyBoundary(REBASE_TO_NEXT_ROUND)`. `STAGE_01N_RUN_FINALISATION_AUDIT.md`; TV104 |
| 3 | One generic `FinalizeSimulationRun` owns final horizon reconciliation | **PASS** — §20a runs once (guarded by `run_finalised`), drains to `T`, horizon-closes a nonterminal round, performs the ONE `SettleResidencyBoundary(FINAL_RUN_END, (RunID, RUN_END))`, then reconciles I5/I6/I7. `STAGE_01N_RUN_FINALISATION_AUDIT.md`; TV105/TV106 |
| 4 | Accepted and aborted final rounds use the SAME run-level finaliser | **PASS** — for `ROUND_ACCEPTED` and `ROUND_ABORTED` final rounds alike, `FinalizeSimulationRun` skips the (already-terminal) horizon-close and performs the single `FINAL_RUN_END` settle + reconciliation; it is the only such path. `STAGE_01N_RUN_FINALISATION_AUDIT.md`; TV105/TV106 |
| 5 | R13 has an executable named procedure | **PASS** — §10a `CompleteSecurityRecovery` implements R13 (branches A/B/C) and R14 (branch D); seated by the §9 floor-restored decision (I-02); the "R13 non-executable" claims are removed. `STAGE_01N_SECURITY_RECOVERY_EXIT_AUDIT.md`; TV107/TV108/TV109 |
| 6 | Every recovery-success branch captures the required applicability census | **PASS** — branch A → `TransitionRoundState(SOLUTION_PROPAGATION)`, branch B → `TransitionRoundState(HASHING)`, branch C → `CompleteAssignmentPhase` (→ `TransitionRoundState(HASHING)`); each captures the census (M2/K7). `STAGE_01N_SECURITY_RECOVERY_EXIT_AUDIT.md`; TV107/TV108/TV109 |
| 7 | Every driver entry point has a declared microphase and envelope seating rule | **PASS** — §0.7g-driver declares event type, microphase, tie key, envelope fields, and same-time delta-cycle right for all 9 sim-driver entry points; `RoundAbort` keeps `TERMINAL_ABORT` (§21 item 1); `FinalizeSimulationRun` is `RUN_FINALISE`. `STAGE_01N_DRIVER_EVENT_MAPPING_AUDIT.md`; TV110 |
| 8 | TV104 through TV110 pass on paper | **PASS** — `STAGE_01N_SEMANTIC_TEST_VECTORS.md`; every vector names exact procedures + preconditions; no guard/transition/cancellation assumed that is not in the pseudocode; A1 preserved |
| 9 | No executable source, configuration, DOCX, or PDF changes | **PASS** — `git diff` confined to `docs/thesis_revision_v45/stage_01/`; draft-42 `2c3afdc5…`, draft-44 `a31400bc…` byte-identical |
| 10 | No Stage-1A..1M historical artifact is modified | **PASS** — `git diff --name-only <base>` shows no `STAGE_01[A-M]_*` file; supersessions recorded in `STAGE_01N_SUPERSESSION_REGISTER.md`, not by rewriting prior evidence |

## Cross-document consistency

| Check | Result |
|-------|--------|
| Name always **PoCol**; mechanism only "the idle policy within PoCol" | **PASS** — 0 occurrences of any forbidden name string in the normative corpus |
| Round abort ≠ run end (pseudocode ↔ round SM ↔ energy model ↔ I19) | **PASS** — `RoundAbort` round-only; `FinalizeSimulationRun` run-level owner of `FINAL_RUN_END` + I5/I6/I7; consistent across §20/§20a, round SM §2.10/§3.14, energy §3, catalogue I19 (N1) |
| Executable recovery exit (pseudocode ↔ round SM) | **PASS** — `CompleteSecurityRecovery` (§10a) ↔ round SM R13/R14/§3.10; every success branch captures the census (N2) |
| Complete driver seating map | **PASS** — §0.7g-driver ↔ §21 (RECOVERY_COMPLETE item 13a, RUN_FINALISE run-level, TERMINAL_ABORT item 1) (N3) |
| Single boundary owner preserved | **PASS** — `SettleResidencyBoundary` reached only from `RoundInitialise` (REBASE) and `FinalizeSimulationRun` (FINAL_RUN_END); `ApplyMinerStateTransition` still sole interval owner (M4/N1) |
| Invariant catalogue updated | **PASS** — I19 FINAL_RUN_END owner reassigned to `FinalizeSimulationRun` (N1) |
| Terminology addendum | **PASS** — Stage-1N addendum covers N1–N4 |
| Traceability updated | **PASS** — R92 updated; R95–R99 (N1–N4 + TV104–TV110) |
| Call graph has no dangling calls | **PASS** — 51 defined; 0 called-but-undefined (`STAGE_01N_PROCEDURE_CALL_GRAPH.md`) |
| A1 discipline | **PASS** — baseline `8.420833333 kWh` unchanged; run finalisation is an accounting boundary that partitions `[0, T]` exactly once, never a total change |

## Supersession notes

All Stage-1N supersessions of prior-stage statements are recorded in `STAGE_01N_SUPERSESSION_REGISTER.md`
(6 entries) — historical `STAGE_01[A-M]_*` files are NOT modified.

## Git delta

Modified (6, all un-suffixed normative): `STAGE_01_PROTOCOL_PSEUDOCODE.md`, `STAGE_01_ROUND_STATE_MACHINE.md`,
`STAGE_01_ENERGY_MODEL_SPECIFICATION.md`, `STAGE_01_INVARIANT_CATALOGUE.md`, `STAGE_01_TERMINOLOGY.md`,
`STAGE_01_TRACEABILITY_MATRIX.csv`. Added (9): the `STAGE_01N_*` deliverables. No file outside
`docs/thesis_revision_v45/stage_01/` is touched; no `STAGE_01[A-M]_*` file is modified.

## Result

All ten acceptance gates pass and all cross-document consistency checks hold. The specification conforms to
N1–N4 while preserving B1–B9, C1–C10, D1–D9, E1–E10, F1–F9, G1–G11, H1–H9, I-01…I-08, J1–J9, K1–K8, L1–L6,
and M1–M6. Name remains PoCol; no new consensus feature; documentation only; protected drafts
byte-identical; Stage-1A–1M lettered artifacts frozen; A1 baseline unchanged.
