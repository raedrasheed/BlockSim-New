# Stage 1Q — Runtime-Context Ownership Audit (Q5)

This audit records a **documentation-only** revision of the **PoCol** consensus
specification. It concerns how run-level and round-level runtime state is owned
in `docs/thesis_revision_v45/stage_01/STAGE_01_PROTOCOL_PSEUDOCODE.md`. The
mechanism under revision is **the idle policy within PoCol**, referenced here as
a mechanism only; no property of that mechanism is claimed by this document. The
**A1 baseline of 8.420833333 kWh is UNCHANGED** — no energy figure is altered,
because the revision changes only *where* runtime registries are created and how
they are threaded, not what state transitions or energy attributions occur.

**Scope.** Stage 1Q correction **Q5 — define `RunContext` and runtime
ownership**. The audit covers exactly: the new `STRUCTURE RunContext` and
`PROCEDURE RunInitialise` (§1.0), the amended `PROCEDURE RoundInitialise` (§1.1)
that now receives `RunContext` as an input and returns every per-round registry
explicitly, and the run driver `RunEventLoopToHorizon` (§0.7d-run) obtaining the
run-hook envelope owner through `RunContext.RunHookContext`.

## 1. `STRUCTURE RunContext` (§1.0) — the sole owner of run-level state

A run's per-run state now lives in ONE explicit `RunContext`, the SOLE owner of
run-level runtime state. It holds exactly:

- `RunID` — the fixed per-run identifier (used in `(RunID, RUN_END)` and
  `(RunID, T, HORIZON_CLOSE)`).
- `EventQueueContext` — the sole dispatch/scheduling state (§0.7e / K8):
  `event_queue`, the `current_*` fields, `event_creation_seq`,
  `finalised_event_times`, `run_horizon_T`.
- `RunHookContext` — the run-hook envelope owner (§0.7e / P2): `run_hook_seq`,
  `applied_run_hook_ids`.
- `rebased_boundaries` — L5/M4 set of `boundary_id`s already settled by
  `SettleResidencyBoundary` (§1a).
- `run_finalised` — N1 boolean guarding the single run-end finalisation (§20a).
- `run_horizon_T` — O2 fixed simulation horizon `T` (mirrored in
  `EventQueueContext` for `ScheduleEvent`).
- the per-run security-census/registries (I-01/I-04, monotonic across rounds):
  `security_census_dirty`, `latest_security_census`,
  `applied_transition_registry`, `transition_rejection_log`.

## 2. `PROCEDURE RunInitialise` (§1.0) — one-time per-run creation

`RunInitialise` is called **EXACTLY ONCE per run, BEFORE the first
`RoundInitialise`**. It creates ALL per-run fields — the fresh `RunID`, the
`EventQueueContext`, the `RunHookContext` (`run_hook_seq = 0`,
`applied_run_hook_ids = empty set`), `rebased_boundaries` (empty),
`run_finalised = false`, `run_horizon_T = config.horizon_T`, and the four
security-census maps (`security_census_dirty`, `latest_security_census`,
`applied_transition_registry`, `transition_rejection_log`) — and **RETURNS**
`RunContext`. Its closing NOTE fixes the contract: it is the ONE-TIME owner of
every per-run field; `RoundInitialise` **NEVER** (re)creates these — it receives
the `RunContext`, preserves it, and reuses it; and `RunEventLoopToHorizon`
obtains `RunHookContext` through `RunContext.RunHookContext`, never an implicitly
created local object.

## 3. `PROCEDURE RoundInitialise` (§1.1) — receives `RunContext`, per-round only

`RoundInitialise` now takes `INPUTS: config, RunContext, prior_state`. The
`RunContext` is supplied **EXPLICITLY** (created once by `RunInitialise`) and is
reused. The procedure:

1. initialises ONLY the per-round registries (reset FRESH every round, G8/I-04):
   `assignment_ledger`, `reassignment_log`, `energy_ledger`, `floor_state`,
   `active_propagation_set`, `acceptance_batch_registry`,
   `candidate_discovery_seq`, `block_accepted`, `state_version`,
   `residency_ledger`, and the ten recovery registries listed below;
2. **binds `RunContext` by reference** (`EventQueueContext`, `RunHookContext`,
   the security-census maps, `rebased_boundaries`, `run_finalised`,
   `run_horizon_T`) and **never resets** any per-run field;
3. when `prior_state != null`, performs the cross-round residency **rebase** for
   the subsequent round via `SettleResidencyBoundary(mode =
   REBASE_TO_NEXT_ROUND, boundary_id, prior_state)` (§1a), keyed by
   `boundary_id` in `RunContext.rebased_boundaries`;
4. **RETURNS** `RoundContext(RoundID, D, nonce_domain, ledgers, RunContext, …)`
   — with `RunContext` bound by reference — and lists EVERY per-round recovery
   registry EXPLICITLY: `recovery_episode_seq`, `current_recovery_episode`,
   `recovery_deadline_reached`, `recovery_census_seq`, `latest_recovery_census`,
   `recovery_decision_seq`, `recovery_decisions`, `pending_recovery_decisions`,
   `latest_recovery_decision`, `recovery_outcome_finalised`.

Its closing NOTE states the invariant: every normative runtime registry is
EXPLICITLY owned; per-run state is created ONCE by `RunInitialise` and reused via
`RunContext`; `RoundInitialise` initialises ONLY the per-round registries and
returns them explicitly; **no registry exists as an implicit global**.

## 4. `RunEventLoopToHorizon` (§0.7d-run) obtains `RunHookContext` via `RunContext`

The run-level driver `RunEventLoopToHorizon` takes `INPUTS: RunContext,
RoundContext`. At the horizon sentinel it invokes
`ProcessEventTime(RoundContext, T, is_horizon = true, allow_empty_horizon =
true, RunHookContext = RunContext.RunHookContext)` — the run-hook envelope owner
is drawn **from `RunContext.RunHookContext`**, not from an implicitly created
local object. It then invokes `FinalizeSimulationRun(RunContext, RoundContext)`
as a post-`ProcessEventTime(T)` run-level hook. Verified: the horizon call
passes `RunHookContext = RunContext.RunHookContext` (§0.7d-run, line at
`ProcessEventTime(… RunHookContext = RunContext.RunHookContext)`).

## 5. Ownership table — per-run vs per-round

| Field / registry | Owner procedure | Scope | Reset each round? |
| --- | --- | --- | --- |
| `RunID` | `RunInitialise` (§1.0) | per-run | no (created once) |
| `EventQueueContext` | `RunInitialise` (§1.0) | per-run | no |
| `RunHookContext` | `RunInitialise` (§1.0) | per-run | no |
| `rebased_boundaries` | `RunInitialise` (§1.0) | per-run | no |
| `run_finalised` | `RunInitialise` (§1.0) | per-run | no |
| `run_horizon_T` | `RunInitialise` (§1.0) | per-run | no |
| `security_census_dirty` | `RunInitialise` (§1.0) | per-run | no |
| `latest_security_census` | `RunInitialise` (§1.0) | per-run | no |
| `applied_transition_registry` | `RunInitialise` (§1.0) | per-run | no |
| `transition_rejection_log` | `RunInitialise` (§1.0) | per-run | no |
| `assignment_ledger` / `reassignment_log` / `energy_ledger` / `floor_state` | `RoundInitialise` (§1.1) | per-round | yes |
| `active_propagation_set` / `acceptance_batch_registry` | `RoundInitialise` (§1.1) | per-round | yes |
| `candidate_discovery_seq` / `block_accepted` / `state_version` | `RoundInitialise` (§1.1) | per-round | yes |
| `residency_ledger` | `RoundInitialise` (§1.1) | per-round | yes |
| `recovery_episode_seq` / `current_recovery_episode` | `RoundInitialise` (§1.1) | per-round | yes |
| `recovery_deadline_reached` | `RoundInitialise` (§1.1) | per-round | yes |
| `recovery_census_seq` / `latest_recovery_census` | `RoundInitialise` (§1.1) | per-round | yes |
| `recovery_decision_seq` / `recovery_decisions` | `RoundInitialise` (§1.1) | per-round | yes |
| `pending_recovery_decisions` / `latest_recovery_decision` | `RoundInitialise` (§1.1) | per-round | yes |
| `recovery_outcome_finalised` | `RoundInitialise` (§1.1) | per-round | yes |

## 6. BEFORE vs AFTER

| Aspect | BEFORE | AFTER (Stage 1Q / Q5) |
| --- | --- | --- |
| Per-run field creation | inline in `RoundInitialise`'s `IF prior_state = null` branch | owned by `RunInitialise` (§1.0), called once before the first round |
| `RunContext` | none (per-run fields loose) | explicit `STRUCTURE RunContext`, sole owner of run-level state |
| `RunInitialise` | absent | present; runs EXACTLY ONCE, RETURNS `RunContext` |
| `RoundInitialise` inputs | `config, prior_state` | `config, RunContext, prior_state` (reuses `RunContext`) |
| `RunHookContext` at horizon | implicitly local object | `RunContext.RunHookContext` (threaded explicitly) |
| Per-round recovery registries | partly implicit | all ten RETURNED EXPLICITLY by `RoundInitialise` |
| Implicit globals | possible | none — every registry has a named owner |

## 7. Acceptance checks (gate 7)

| # | Check | Status | §-evidence |
| --- | --- | --- | --- |
| 1 | `STRUCTURE RunContext` holds all ten per-run fields (RunID, EventQueueContext, RunHookContext, rebased_boundaries, run_finalised, run_horizon_T, four census/registry maps) | PASS | §1.0 |
| 2 | `RunInitialise` called EXACTLY ONCE before the first `RoundInitialise`; creates all per-run fields; RETURNS `RunContext` | PASS | §1.0 |
| 3 | `RoundInitialise` takes `config, RunContext, prior_state`; binds `RunContext` by reference; never resets per-run state | PASS | §1.1 |
| 4 | `RoundInitialise` initialises ONLY per-round registries and does the subsequent-round residency rebase | PASS | §1.1 / §1a |
| 5 | `RoundInitialise` RETURNS all ten recovery registries explicitly | PASS | §1.1 |
| 6 | `RunEventLoopToHorizon` passes `RunHookContext = RunContext.RunHookContext` to `ProcessEventTime(T)` | PASS | §0.7d-run |
| 7 | `RunContext` and `RoundContext` ownership explicit and complete; no registry is an implicit global | PASS | §1.0 / §1.1 (closing NOTEs) |

---

Documentation only. The consensus specification is named **PoCol**. **The idle
policy within PoCol** is referenced here as a mechanism only; no property is
claimed. The **A1 baseline of 8.420833333 kWh is unchanged**. The prohibited
rebranded-algorithm-name variants are not used anywhere in this document.
