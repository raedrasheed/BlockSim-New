# Stage 2A — PoCol Executable Scientific-Core Remediation Report

Time-boxed executable remediation of the Stage-2 PoCol simulator package after
independent review. This is a **correction of the existing package**, not a rewrite.

- **Branch:** `thesis-v45-pocol-stage2a-executable-scientific-core-remediation`
- **Parent commit (branch base):** `c990649be010c351fb2b5beb11cb647aed665f88`
- **Frozen Stage-1 normative baseline:** `8c9902e57c0d6557329bc742e39a50ed31b86170`
- **Package:** `Models/PoCol/stage2/` (`config`, `events`, `context`, `driver`,
  `search` *(new)*, `simulator`, `energy_experiment` *(new)*, `adapter` *(new)*, `demo`)
- **Tests:** `tests/thesis_revision_v45/stage2/` — **30 passing** (TV325–TV338, E2E-1…E2E-5,
  SCI-1…SCI-7, adapter). Machine-generated evidence:
  `docs/thesis_revision_v45/stage_02/evidence/pytest_stage2a.log` +
  `pytest_stage2a.junit.xml`.
- **Demo:** `python -m Models.PoCol.stage2.demo`
- **BlockSim entry point:** `Models.PoCol.stage2.adapter.run_pocol_stage2`

The algorithm is **PoCol**; the energy-saving mechanism is **the idle policy within
PoCol** — low-power residency after a miner exhausts its assigned nonce range, NEVER
nonce partitioning. **No dynamic difficulty** is used in the confirmatory core.

---

## Why Stage 2 was rejected, and what Stage 2A changes

Independent review found the Stage-2 core scientifically hollow:

1. success was a fixed `solution_after_units` timer, not real search against a target;
2. only a single "leader" miner scheduled hash work;
3. the reported idle "saving" came from removing a reserve *fraction* from
   participation (and from nonce partitioning), not from real range exhaustion.

Stage 2A replaces the hollow core with a genuine one and keeps the rest of the package.

### S2A-1 — Actual PoCol search core (`search.py`, `simulator.py`)

- **Immutable common block template per round** — `Template` (frozen dataclass:
  `TemplateID`, `RoundID`, `header_bytes`, `difficulty`, `nonce_domain_size`,
  `winning_nonces`, `target`), committed once by `_handle_template_commit` via
  `make_template(seed = template_seed + round_seq)`.
- **Explicit finite nonce domain** `[0, nonce_domain_size)`.
- **Deterministic disjoint partition** — `partition_domain(D, participants)` returns
  contiguous `{MinerID: (start, end)}` whose union is exactly `[0, D)` and whose members
  are pairwise disjoint (SCI-1/SCI-2).
- **Per-miner search state** — `MinerSearchState` carries `MinerID`, `AssignmentID`,
  `assignment_version`, `hash_rate`, `range_start`, `range_end`, `cursor`,
  `searched_count`, `active_power`, `idle_power`, `active_start`, `completion_kind`.
- **All active miners hash** — `_handle_wake_complete` seats a `HashWorkEvent` for
  **every** ACTIVE_HASHING miner (not just a leader); `_handle_hash_work` evaluates one
  declared batch (`batch_size`) of nonces, computes `sha256_int(header‖nonce)` for each
  (real per-nonce work, counted in `searched_count`), tests `Template.is_solution`,
  advances the cursor, and produces success / continuation / range-exhaustion. Two live
  assignments never evaluate the same nonce under one template (disjoint ranges).
- `solution_after_units` is **removed as a success mechanism** — it is a disabled
  (`0`) test-injection hook only.

### S2A-2 — Scientific difficulty / success (`search.py`)

- **Fixed confirmatory target** — `target_for_difficulty(difficulty) = (2^256−1)//difficulty`;
  no dynamic difficulty.
- **Success model — recorded as `B_EXACT_WITHOUT_REPLACEMENT_SAMPLER`.** The winning
  nonce(s) are drawn once per template by a deterministic SplitMix64-style
  without-replacement sampler seeded by the immutable header; the per-nonce work unit is a
  **real SHA-256 digest** of `header‖nonce`, counted. The success predicate is
  `nonce ∈ template.winning_nonces`.
- **Round duration depends on hash rate, target/domain, searched positions and #active
  miners** — the acceptance / exhaustion time is `active_start + searched_count/hash_rate`.
  There is no fixed 3-unit round timer.

### S2A-3 — Correct idle policy + matched-control energy experiment (`energy_experiment.py`)

- The **participation/reserve policy** (a reserve pool held in RESERVE at `P_listen`) is
  kept SEPARATE from the **idle policy** (post-range-exhaustion residency at idle power).
- `_handle_range_exhaust` moves a miner that exhausts its range **before round end** from
  ACTIVE_HASHING to LOW_POWER_LISTEN — this, and only this, is the idle policy.
- The mandatory experiment (`run_energy_experiment`) runs ONE round under **CONTROL**
  (every assigned miner at active power until round end) vs **POCOL_IDLE** (a miner that
  exhausts its range early drops to idle power), with **identical** miners, hash rates,
  disjoint ranges, target, template, seeded success position, round-start and stopping
  condition. For every miner it verifies

      E_i        = P_active_i · t_active_i + P_idle_i · t_idle_i
      Delta_E_i  = t_idle_i · (P_active_i − P_idle_i)  ==  E_control_i − E_idle_i

  and reports the **maximum absolute residual** (measured `8.88e-16 J`, SCI-4). With
  `P_idle == P_active` the saving is exactly `0.0` (SCI-5), so nonce partitioning alone
  produces no saving.
- The canonical **A1** control is `a1_continuous_control_kwh(Stage2Config())` =
  141 × 21.5 W × 10 000 s / 3 600 000 = **8.420833333 kWh** (SCI-6). A 20-miner / 1000 s
  scenario is **never** labelled A1.

### S2A-4 — Driver-event round binding (`simulator._verify_driver_binding`)

`MinerRegisterEvent` and `ReserveActivateEvent` payloads carry `DriverRequestID`,
`round_scope`, and `RoundID_at_seat`. Before ANY domain mutation, `_verify_driver_binding`
checks the request exists, is `SEATED`, the reverse binding matches the dispatched
`EventRef`, the scope admits the current `RoundContext`, and `RoundID_at_seat` equals the
current `RoundID`. A stale / cancelled / mismatched seat yields `miner_register_no_effect`
(TV336, TV338).

### S2A-5 — Coherent seat / cancel (`driver.SeatDriverEventTransaction`, `events.CancelQueuedEvent`)

`SeatDriverEventTransaction` schedules the event, then publishes the reverse binding and
drives `PENDING → SEATED` as one transaction. If scheduler insertion succeeds but request
publication fails (`force_seat_publication_failure` injection, or a status mismatch), it
**cancels the newly queued event and removes the reverse binding** (compensation) and
returns a structured `seat_publication_failed` (TV325, TV330). `CancelQueuedEvent`
captures and returns the reconcile result: a coherent commit
(`driver_request_status_set`) or a declared integrity failure
(`driver_request_status_mismatch`), never swallowed (TV331).

### S2A-6 — Legal partial finalizer (`simulator.FinalizeSimulationRunPartial`)

Cancels every remaining QUEUED event (reconciling any bound driver request via the queue
owner), terminalises every non-terminal driver request, closes current assignments,
settles residency and attributes energy **only** through `partial_end_time`, asserts no
QUEUED/DISPATCHING event and no PENDING/SEATED request remains, and records a partial-run
disposition — it never claims a full-horizon run (TV329, E2E-5).

### S2A-7 — Required semantic tests

Exact TV325–TV338 semantics (not renamed approximations), E2E-1…E2E-5 retained against the
real search core, and new SCI-1…SCI-7. See `STAGE_02_TEST_REPORT.md` and
`STAGE_02_REQUIREMENT_TRACEABILITY.md`.

### S2A-8 — Minimal BlockSim integration (`adapter.py`)

`stage2config_from_blocksim` maps a BlockSim-style config mapping (e.g. `Nn`/`simTime`)
onto `Stage2Config`; `run_pocol_stage2` runs the core and returns round/block/energy in the
declared schema (`RESULT_SCHEMA_VERSION = "stage2a.1"`). The legacy simulator is not
replaced, no frozen Stage-1 document is changed, and the standalone demo is preserved.

---

## Mandatory core execution path (multi-round, real search)

`Models/PoCol/stage2/simulator.py` realises the full path across MULTIPLE rounds:

    RunInitialise -> first-round bootstrap (SeatNextRoundBootstrap)
    -> genesis miner admission (EXACT_ROUND) + in-dispatch seating (AI1)
    -> TemplateCommit (immutable Template + finite nonce domain)
    -> participant preparation (disjoint range partition; reserve pool held at P_listen)
    -> assignment creation -> StartWake -> WakeCompleteEvent -> ACTIVE_HASHING
    -> HashWorkEvent for EVERY active miner (real batched SHA-256 search vs the target)
    -> acceptance (winning nonce found) OR range exhaustion -> idle OR round abort
    -> round closure -> next-round bootstrap -> ... -> horizon OR partial termination.

A confirmatory 8-miner / 600 s run executes **343 rounds** (342 by acceptance, 1 closed at
the horizon), reconciles residency, and shows an idle-policy saving against the A1
continuous-participation control (`0.01475 kWh` vs `0.02867 kWh` matched control). E2E-3
asserts ≥ 2 consecutive rounds with no event leakage, so the implementation is not
single-round.

## Scope

No Stage-1 normative document (`docs/thesis_revision_v45/stage_01/…`) is modified; the
Stage-1 baseline stays frozen at `8c9902e`. Stage 2A modifies the Stage-2 package,
replaces its test suite with the exact vectors, and adds this evidence set only.
