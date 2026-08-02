# Stage 2A — Requirement Traceability

Maps every Stage-2A requirement (S2A-1 … S2A-9) and the mandatory Stage-1AJ backlog fixes
to the executable code that realises it and the test(s) that prove it. Algorithm: PoCol.
Mechanism: the idle policy within PoCol. No dynamic difficulty in the confirmatory core.

## S2A-1 — Actual PoCol search core

| Sub-requirement | Code | Test |
|---|---|---|
| Immutable common block template per round | `search.Template` (frozen), `search.make_template`, `simulator._handle_template_commit` (`rc.template`) | SCI-2, SCI-7, E2E-1 |
| Explicit finite nonce domain `[0, D)` | `config.nonce_domain_size`, `search.make_template` | SCI-1 |
| Deterministic disjoint partition into per-miner ranges | `search.partition_domain`; `simulator._handle_prepare_participants` | SCI-1, SCI-2 |
| Per-miner MinerID / hash-rate / range / cursor / assignment version / powers / searched-count | `search.MinerSearchState`; `config.hash_rate_for` | SCI-3, SCI-4 |
| ALL active miners schedule hash work (not one leader) | `simulator._handle_wake_complete` (seats HashWork for every active miner) | SCI-3, E2E-1 |
| Hash-work event: identify round/template/assignment, evaluate one/declared batch, test hash vs fixed target, advance cursor, record searched count, produce success/continuation/exhaustion | `simulator._handle_hash_work` | SCI-2, SCI-3, E2E-1 |
| No two live assignments evaluate the same nonce under one template | disjoint `partition_domain` + per-miner cursor | SCI-1, SCI-2 |
| `solution_after_units` removed as a success mechanism (disabled hook only) | `config.solution_after_units = 0`; not read by `_handle_hash_work` success path | SCI-7 (success is `is_solution`) |

## S2A-2 — Scientific difficulty / success

| Sub-requirement | Code | Test |
|---|---|---|
| Fixed confirmatory difficulty / target (no dynamic difficulty) | `search.target_for_difficulty`; `config.difficulty` | SCI-4, SCI-7 |
| Recorded success model (B — exact without-replacement sampler) | `search.SUCCESS_MODEL`, `search.WithoutReplacementSampler`, `Template.is_solution` | SCI-4, SCI-7 |
| Real per-nonce work | `search.sha256_int` (`WORK_PRIMITIVE = "SHA256(header‖nonce)"`), counted in `searched_count` | SCI-2 |
| Round duration depends on hash rate / target / searched positions / #active miners, not a fixed timer | `_handle_hash_work` (`active_start + searched_count / hash_rate`) | E2E-1, SCI-7 |

## S2A-3 — Idle policy + matched-control energy experiment

| Sub-requirement | Code | Test |
|---|---|---|
| Participation/reserve policy SEPARATE from idle policy | `_handle_prepare_participants` (reserve pool → RESERVE at `P_listen`) | SCI-3 |
| Range completion → post-range idle policy | `_handle_range_exhaust` (ACTIVE_HASHING → LOW_POWER_LISTEN) | SCI-3, SCI-4 |
| CONTROL vs POCOL_IDLE, identical miners/rates/ranges/target/template/seed/round-start/stop | `energy_experiment.run_energy_experiment` | SCI-4, SCI-5, SCI-7 |
| Per-miner `E_i = P_active·t_active + P_idle·t_idle` | `energy_experiment` rows; SCI-4 assertion | SCI-4 |
| `Delta_E_i = t_idle·(P_active − P_idle)`; max abs residual reported | `EnergyExperimentResult.max_abs_residual_j` | SCI-4 |
| Partitioning alone → zero saving when `P_idle == P_active` | `run_energy_experiment(P_idle = P_hash)` | SCI-5 |
| 20-miner/1000 s never labelled A1; A1 = 141 / 21.5 W / 10 000 s = 8.420833333 kWh | `config.a1_continuous_control_kwh`, `A1_BASELINE_KWH` | SCI-6 |

## S2A-4 — Driver-event round binding

| Sub-requirement | Code | Test |
|---|---|---|
| Payloads carry `DriverRequestID`, round scope, `RoundID_at_seat` | `driver.SeatMinerRegister` / `SeatReserveActivate` payloads; `events.DESCRIPTORS` | TV338 |
| Pre-mutation verify: request exists, SEATED, reverse binding matches EventRef, scope admits round, `RoundID_at_seat == RoundID` | `simulator._verify_driver_binding` | TV336, TV338 |
| Stale/cancelled/mismatched → no domain effect | `_handle_miner_register` → `miner_register_no_effect` | TV336, TV338 |

## S2A-5 — Coherent seat / cancel

| Sub-requirement | Code | Test |
|---|---|---|
| Single seat transaction (schedule + publish binding + PENDING→SEATED) | `driver.SeatDriverEventTransaction` | TV333, E2E-1 |
| Scheduler-ok but publication-fail → cancel queued event, remove binding, structured failure | `SeatDriverEventTransaction` compensation (`force_seat_publication_failure` hook) | TV325, TV330 |
| Cancellation captures/inspects the request-status update; declared integrity failure surfaced | `events.CancelQueuedEvent` (`reconcile` result) | TV331 |

## S2A-6 — Legal partial finalization

| Sub-requirement | Code | Test |
|---|---|---|
| Cancel every remaining QUEUED event; reconcile bound requests; terminalise pending requests | `simulator.FinalizeSimulationRunPartial` | TV329, E2E-5 |
| Close current assignments; settle residency & attribute energy only through `partial_end_time` | `FinalizeSimulationRunPartial` (`settle_residency_to`) | TV329, E2E-5 |
| Assert no QUEUED/DISPATCHING event and no PENDING/SEATED request; record partial disposition; never claim full-horizon | `FinalizeSimulationRunPartial` asserts + `run_disposition` | TV329, E2E-5 |
| Future queued events before bootstrap failure are cancelled | future seat + partial finalizer | TV329 |

## S2A-7 — Required semantic tests

| Vector | Semantics | File |
|---|---|---|
| TV325 | partial genesis seating where the THIRD seat actually fails (compensation) | `test_stage2_semantic_vectors.py` |
| TV326 | TemplateCommit seat failure AFTER all genesis seats exist (structured abort) | ″ |
| TV327 | queued EXACT_ROUND registration cancelled before rotation | ″ |
| TV328 | NEXT_AVAILABLE effective round/time binding (requested immutable) | ″ |
| TV329 | future queued events during partial finalization are cancelled | ″ |
| TV330 | failure between ScheduleEvent commit and request publication | ″ |
| TV331 | cancellation status-publication (coherent + declared mismatch captured) | ″ |
| TV332 | two distinct equal-deficit reserve incidents → distinct identities | ″ |
| TV333 | exact replay returns status, EventRef, disposition | ″ |
| TV334 | foreign RunContext sharing the SAME EQ is rejected | ″ |
| TV335 | duplicate genesis configuration → structured failure (no raw assert) | ″ |
| TV336 | cancelled request event reaching dispatch → NO domain effect | ″ |
| TV337 | driver target before the simulation frontier rejected | ″ |
| TV338 | driver-binding stale RoundID/scope at dispatch → NO domain effect | ″ |
| E2E-1…E2E-5 | full multi-round path, abort→second round, no leakage, horizon reconcile, partial finalization | `test_stage2_e2e.py` |
| SCI-1 | disjoint assignments cover the declared nonce domain exactly | `test_stage2_scientific.py` |
| SCI-2 | zero duplicate nonce evaluations under one template | ″ |
| SCI-3 | all active miners contribute hash work | ″ |
| SCI-4 | idle-policy energy identity residual within tolerance | ″ |
| SCI-5 | `P_idle = P_active` → zero saving | ″ |
| SCI-6 | canonical A1 reproduces 8.420833333 kWh | ″ |
| SCI-7 | matched control & idle use the same success position and round end | ″ |

## S2A-8 — BlockSim integration

| Sub-requirement | Code | Test |
|---|---|---|
| Map BlockSim config → Stage2Config | `adapter.stage2config_from_blocksim` | `test_stage2_adapter.py` |
| Return round/block/energy in a declared schema | `adapter.results_schema`, `RESULT_SCHEMA_VERSION` | `test_stage2_adapter.py` |
| No frozen Stage-1 doc changed; standalone demo preserved | `adapter.py` (additive); `demo.py` | `test_stage2_adapter.py`, demo run |

## S2A-9 — Evidence

| Artifact | Path |
|---|---|
| Implementation report | `STAGE_02_IMPLEMENTATION_REPORT.md` |
| Requirement traceability | `STAGE_02_REQUIREMENT_TRACEABILITY.md` (this file) |
| Test report | `STAGE_02_TEST_REPORT.md` |
| Known limitations | `STAGE_02_KNOWN_LIMITATIONS.md` |
| Checksum manifest | `STAGE_02_CHECKSUM_MANIFEST.sha256` |
| Machine-generated pytest log | `evidence/pytest_stage2a.log`, `evidence/pytest_stage2a.junit.xml` |
| Deterministic metrics | `evidence/stage2a_metrics.json` |
| CI workflow | `.github/workflows/stage2a-pocol-tests.yml` |

## Mandatory Stage-1AJ backlog fixes (executable)

| # | Backlog requirement | Where | Test |
|---|---|---|---|
| 1 | Every driver-seated event carries `DriverRequestID` + exact round scope | `driver.SeatMinerRegister` / `SeatReserveActivate` payloads | TV338 |
| 2 | No EXACT_ROUND event survives closure into another round | `simulator._close_and_publish` | TV327, E2E-3 |
| 3 | Round closure terminates PENDING and SEATED requests of that round | `_close_and_publish` backlog-3 block | TV327 |
| 4 | NEXT_AVAILABLE_ROUND uses a legal effective seat time | `driver._legal_effective_time` → `effective_event_time` | TV328 |
| 5 | Preserve immutable original `requested_event_time` | `context.DriverRequest.requested_event_time` | TV328 |
| 6 | Legal partial-run finalizer; never call full-horizon finalizer early | `simulator.FinalizeSimulationRunPartial` | TV329, E2E-5 |
| 7 | Explicit keyed driver-request registry updates | `RunContext.set_driver_request_status` | TV331, TV336 |
| 8 | Coherent / compensating seat publication | `driver.SeatDriverEventTransaction` | TV325, TV330 |
| 9 | Driver-event cancellation coherent with request cancellation | `events.CancelQueuedEvent` reconcile | TV327, TV331 |
| 10 | Distinct identities for separate reserve incidents | `RunContext.admit_driver_request` logical id | TV332 |
| 11 | Validate exact `RunContext` ownership | `events.ScheduleEvent` DRIVER/TERMINAL_ROTATION check vs `EventQueue.owner_run_context` | TV334 |
| 12 | Replace raw genesis assertions with structured outcomes | `simulator._handle_round_initialise` → `round_initialise_aborted` | TV335 |
