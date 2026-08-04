# Stage 8R — Implementation Report: the revised idle and reserve-control policy within PoCol

**Branch:** `thesis-v45-pocol-stage8r-controller-refinement` (from
`b7580a1f3b15b9eaf3ae3a9b0b74452bfbd014e3`, the exact remote HEAD of
`thesis-v45-pocol-stage8m-minimal-analysis`).
The algorithm name remains **PoCol**; this is **the revised idle and reserve-control policy
within PoCol** — not a renamed algorithm.

## 1. What was implemented

| refinement | where | summary |
|---|---|---|
| R1 breach-episode authority | `refinement.py` (`BreachEpisode`), `simulator.py` | immutable-identity episodes with statuses OPEN / RECOVERY_IN_PROGRESS / RECOVERED / ROUND_CLOSED / UNATTAINABLE; at most one live activation batch per episode; repeated observations never double-seat; round closure terminalises everything; nothing crosses a round boundary |
| R2 hysteresis | `ControllerPolicy` (frozen 0.78 / 0.80 / 0.82) | reactive episodes open only below 0.78 × H0; RECOVERED only at ≥ 0.82 × H0 (and no live batch in flight); the central 0.80 target is operational, not a formal security threshold; the deadband is a symmetric two-percentage-point engineering band frozen before the pilot |
| R3 one live batch + cooldown | `_seat_refined_batch`, `_refined_floor_decide` | sufficiency check (physical + valid live + pending capacity) before any seat; cooldown = activation wake latency; inside cooldown a batch may seat only when the prior batch is terminal AND capacity persists below the frozen trigger; minimum-cardinality selection (accepted `select_reserves_to_cover`); requested / completed / cancelled / excess / under rates recorded per batch |
| R4 predictive wake-ahead | `predict_h_future`, `_refined_predictive_check` | forecast from OBSERVABLE state only: per-miner remaining = range_end − accepted cursor, executable rate, plus live wake requests completing inside the lookahead (= wake latency); prediction records carry decision time, lookahead, current H_effective, predicted H_future, expiring miners, live incoming capacity, selected reserves, predicted deficit, actual value at horizon, error, false-positive and late-wake indicators; a prediction is an engineering estimate, not a security proof |
| R5 H_pipeline | `h_pipeline`, `_update_pipeline_stats` | **H_effective stays physical — WAKING contributes zero** (verified R-TEST-02); H_pipeline = H_effective + valid live wake capacity is a separate reporting/scheduling forecast, never substituted into any integrity check; max, time-weighted mean and pipeline-above-target-while-physical-below-target duration are reported |
| R6 bounded suffix reassignment | `_maybe_controller_suffix_reassignment` | EXPLORATORY arm only (`HYSTERESIS_PREDICTIVE_REASSIGNMENT`); fires only with a live/completed reserve batch, predicted capacity below target, an eligible donor whose remaining suffix ≤ the fixed 25-nonce chunk, and no in-flight reassignment; executes through the ACCEPTED Stage-4 voluntary-cancellation → reassignment machinery; one immutable trigger per suffix lineage |

**Controller modes:** `LEGACY_REACTIVE` (default), `HYSTERESIS_ONLY`,
`HYSTERESIS_PREDICTIVE`, `HYSTERESIS_PREDICTIVE_REASSIGNMENT`. All refinements are
disabled by default.

## 2. What was NOT changed

The SHA-256 search, target, difficulty, nonce-domain-size semantics, evaluation-ledger
semantics, accepted-frontier authority, reward model, adversarial model, and physical
hash-rate definitions are untouched. The refined branch replaces ONLY the decision tail of
`EvaluateSecurityFloor`; the observation, measurement and below-floor-interval semantics
are byte-identical in every mode (the refined predictive path adds sparse extra
observations only at its own seat decisions, with identical measurement semantics).

## 3. LEGACY equivalence (the load-bearing guarantee)

`LEGACY_REACTIVE` reproduces the frozen Stage-8M M03 run for confirmatory seed 0
**exactly**: rounds (178), accepted (135), `energy_kwh` (bit-equal 0.014739486249999934),
activations seated/completed (328/226), below-floor duration (bit-equal
275.2608333333294), floor-unattainable count (1092) and ledger entries (6312), with zero
episodes/batches/predictions recorded (R-TEST-01). The 195 accepted engine tests pass
unchanged.

**Declared, expected side effect:** the frozen Stage-6M gate `test_s6m_08` asserts the
engine is byte-identical to the Stage-5D digests; on THIS branch that assertion fails by
construction, because this directive explicitly authorizes engine modification. The
Stage-6M/7M/8M artifacts, tests and manifests are NOT modified — the historical gate keeps
guarding its own frozen lineage, and its functional intent on this branch is carried by
R-TEST-01's exact behavioural reproduction plus the accepted 195-test suite. No Stage-6M/
7M/8M evidence file was touched (verified: their checksum manifests still verify).

## 4. Files

* `Models/PoCol/stage2/refinement.py` — NEW: controller policy, episode/batch/prediction
  structures, forecast helpers (pure).
* `Models/PoCol/stage2/config.py` — `controller: ControllerPolicy` field (LEGACY default).
* `Models/PoCol/stage2/context.py` — controller registries/counters on RunContext; two
  per-round fields on RoundContext.
* `Models/PoCol/stage2/simulator.py` — refined decision tail + predictive hook + batch
  bookkeeping + round-closure terminalisation (all mode-gated).
* `Models/PoCol/stage2/adapter.py` — `_controller_results` reporting block (present, all
  zeros, in every mode).
* `tests/thesis_revision_v45/stage_08r/test_stage8r_controller.py` — R-TEST-01..18.
* `experiments/thesis_revision_v45/stage_08r/diagnose_8r_baseline.py` — Phase-0 read-only
  diagnostic (already reported in `STAGE_08R_BASELINE_DIAGNOSTIC_REPORT.md`).
