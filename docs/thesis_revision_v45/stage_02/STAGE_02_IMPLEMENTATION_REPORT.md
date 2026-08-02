# Stage 2 — PoCol Core Implementation Report

Executable implementation of the PoCol simulator core from the FROZEN Stage-1 normative
baseline `8c9902e57c0d6557329bc742e39a50ed31b86170`.

- **Branch:** `thesis-v45-pocol-stage2-core-implementation`
- **Package:** `Models/PoCol/stage2/` (`config`, `events`, `context`, `driver`, `simulator`)
- **Tests:** `tests/thesis_revision_v45/stage2/` (TV325–TV338 + E2E-1…E2E-5) — **19 passing**
- **Demo:** `python -m Models.PoCol.stage2.demo`

The algorithm is **PoCol**; the energy-saving mechanism is **the idle policy within
PoCol** — low-power residency (`P_listen`/`P_wake` for RESERVE / LOW_POWER_LISTEN /
WAKING), NEVER nonce partitioning. **No dynamic difficulty** is used in the confirmatory
core.

## 1. Mandatory core execution path (multi-round)

`Models/PoCol/stage2/simulator.py` realises the full path across MULTIPLE rounds:

    RunInitialise -> first-round bootstrap (SeatNextRoundBootstrap, DRIVER/RUN_BOOTSTRAP)
    -> genesis miner admission (AdmitDriverRequest, EXACT_ROUND) + in-dispatch seating (AI1)
    -> TemplateCommit -> participant preparation (PrepareParticipants)
    -> assignment creation -> StartWake -> WakeCompleteEvent -> ACTIVE_HASHING
    -> hash-work scheduling (HashWorkEvent) -> acceptance (AcceptanceEvent) OR round abort
    -> round closure (CloseRoundAssignments) -> next-round bootstrap (TERMINAL_ROTATION)
    -> second round -> ... -> horizon (FinalizeSimulationRun) OR partial termination.

A confirmatory 20-miner / 1000 s run executes **63 rounds** (62 by acceptance, 1 closed
at the horizon), reconciles residency, and shows a **~25 % idle-policy energy saving**
against the A1 continuous-participation control. The implementation is NOT single-round
(E2E-3 asserts ≥ 2 consecutive rounds with no event leakage).

## 2. Priority coverage

- **P0** — event queue, `EventRef`, `ScheduleEvent`, `ProcessEventTime`,
  `RunContext`/`RoundContext`, round bootstrap + rotation, miner state transitions,
  assignment lifecycle, residency + energy accounting. **Implemented + tested.**
- **P1** — driver-request lifecycle, acceptance/abort, cancellation + closure, partial
  finalization. **Implemented + tested.**
- **P2** — defensive corruption handling (structured `Outcome` rejections everywhere; no
  raw asserts on the genesis path), reporting/audit metadata (`RunContext.log`, per-miner
  residency ledger, driver-request registry). **Implemented.**

## 3. Energy acceptance

Per-miner energy is the state-complete residency sum (STAGE_01 s.1), which for the
confirmatory two-power form is

    E_i = P_active_i * t_active_i + P_idle_i * t_idle_i

with `P_active = P_hash = 21.5 W` and `P_idle = P_listen`. `a1_continuous_control_kwh`
reproduces the **A1 baseline exactly** (141 × 21.5 W × 10 000 s / 3 600 000 =
`8.420833333 kWh`, TV338). Every finalised run satisfies **I5** — each miner's state
durations partition `[registered_at, end_time]` — and `E_total < A1(cfg)` from idle
residency, not partitioning (E2E-4, TV338).

## 4. Mandatory Stage-1AJ backlog fixes (executable)

| # | Backlog requirement | Where implemented | Test |
|---|---------------------|-------------------|------|
| 1 | Every driver-seated event carries `DriverRequestID` + exact round scope | `context.DriverRequest` (`round_scope`), `driver._publish_seat` reverse binding | TV330 |
| 2 | No EXACT_ROUND event survives closure into another round | `simulator._close_and_publish` cancels QUEUED round events + seated EXACT_ROUND seats | TV326, E2E-3 |
| 3 | Round closure terminates PENDING and SEATED requests of that round | `simulator._close_and_publish` backlog-3 block | TV325 |
| 4 | NEXT_AVAILABLE_ROUND uses a legal effective seat time | `driver._legal_effective_time` → `DriverRequest.effective_event_time` | TV327 |
| 5 | Preserve immutable original `requested_event_time` | `DriverRequest.requested_event_time` never mutated (separate `effective_event_time`) | TV327 |
| 6 | Legal partial-run finalizer; never call the full-horizon finalizer early | `simulator.FinalizeSimulationRun` (explicit end_time) + `RunEventLoopToHorizon` partial path | TV328, E2E-5 |
| 7 | Explicit keyed driver-request registry updates | `RunContext.set_driver_request_status` (keyed CAS guard) | TV329 |
| 8 | Coherent / compensating seat publication | `driver._publish_seat` (reverse binding + SEATED atomic with the seat) | TV330 |
| 9 | Driver-event cancellation coherent with request cancellation | `events.CancelQueuedEvent` reconciles the bound request | TV331 |
| 10 | Distinct identities for separate reserve incidents | `AdmitDriverRequest` logical id `(RESERVE_ACTIVATION, RoundID, incident_id)` | TV332 / TV333 |
| 11 | Validate exact `RunContext` ownership | `ScheduleEvent` DRIVER/TERMINAL_ROTATION context-identity check | TV334 |
| 12 | Replace raw genesis assertions with structured outcomes | `_handle_round_initialise` returns `round_initialise_aborted(...)` | (no raw assert on genesis path) |

## 5. Frozen Stage-1 contracts honoured

- One enqueue interface (`ScheduleEvent`) derives `delta_cycle` from an EXPLICIT
  `SchedulingOrigin` (ORDINARY_DISPATCH / DRIVER / POST_EPILOGUE / TERMINAL_ROTATION);
  a DRIVER/TERMINAL_ROTATION seat reads no ambient state and is validated against the
  authoritative frontier `RunContext.last_finalised_event_time` (AI2, TV337).
- Genesis registrations are seated in-dispatch at the non-finalised `t0` (AI1), so no
  `rejected_finalised_time` deadlock; the initial-registration barrier gates participant
  setup.
- Stable driver-request identity at admission is idempotent (AI3, TV335); the
  driver-request lifecycle `PENDING→SEATED→CONSUMED/CANCELLED` runs through the single
  guarded mutator with the reverse binding (AI4, TV336).
- The synchronous rotation bootstrap uses a truthful `TERMINAL_ROTATION` origin; the
  run-start bootstrap a `DRIVER(RUN_BOOTSTRAP)` origin (AI8).
- A next-round bootstrap failure propagates to the run controller and terminates the run
  with a declared partial-run disposition (AI6, E2E-5).

## 6. Scope

No Stage-1 normative document (`docs/thesis_revision_v45/stage_01/…`) is modified. The
Stage-1 baseline is frozen at `8c9902e`. Stage-2 adds a new implementation package, its
tests, and this report only.
