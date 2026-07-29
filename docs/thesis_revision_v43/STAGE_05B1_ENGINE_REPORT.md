# Stage 5B1 — Final Scenario-Engine Report

This report documents the unified scenario engine that resolves the four Stage-5A
blockers and produces the executable model for the frozen Stage-5B2 matrix. The
engine is `experiments/thesis_revision_v43/scenario_engine.py`. **No full-matrix
execution was performed in this stage** — only the bounded validation set of §
`STAGE_05B1_VALIDATION_REPORT.md`.

## 1. What the engine is

A round-structured, discrete, deterministic model over a fixed wall-clock
duration `T` (default 10 000 s). For each scenario it computes, from first
principles:

- solution counts per template generation, `K ~ Binomial(S, p)` (exact draw);
- per-miner search / discovery time under the scenario's search discipline;
- per-miner active and idle **time**;
- energy `E = Σᵢ (P_active,i · t_active,i + P_idle,i · t_idle,i) + E_coord`;
- coordination and abstract-protocol **counters** (separately from energy).

The five executable scenarios are `B0, B1, B2, B3_C1_CONTINUOUS_DISJOINT, C2`
(`SCENARIOS`). Their search disciplines are given in
`STAGE_05B1_SCENARIO_SEMANTICS.md`.

## 2. The four Stage-5A blockers and their resolution

| # | Stage-5A blocker | Resolution in the engine |
|---|------------------|--------------------------|
| 1 | Range size coupled to hash rate | `allocate_equal` (rate-independent) and `allocate_weighted` (share-driven) separate *range* from *rate*; see `STAGE_05B1_RANGE_ALLOCATION.md`. |
| 2 | B1/B2 not in the event loop | `_discover` implements B1 (common template, all from 0) and B2 (seeded random starts) inside the round loop; both produce accepted blocks and reconciled duplicate work. |
| 3 | C2 idle applied post-hoc | Idle is an **in-loop** state transition: a miner that finishes its range within a generation accrues `idle_t`; energy is accumulated in the same loop, never subtracted afterwards. |
| 4 | Coordination not instrumented | Simulated messages/bytes/refreshes are counted; abstract (unimplemented) agreement operations are counted separately; `unimplemented_agreement_energy_kwh = null` (not zero). |

## 3. Determinism

All randomness flows through **named streams** (`STREAM_NAMES`), each seeded
independently as `int(sha256("{master}:{name}"))`. Adding a draw to one stream
does not shift another. `run_scenario` is a **pure function of its config**;
running the same config sequentially or concurrently yields bit-identical
outcomes (validated, `STAGE_05B1_PARALLEL_REPRODUCIBILITY.md`).

## 4. Accounting Invariant A1 (was H2)

For every **continuous** scenario (`B0, B1, B2, B3_C1`) under matched aggregate
hash rate, active power, and duration, total energy is the deterministic
identity

```
E = P_total · T = (141e12 · 21.5 / 1e12) W · 10 000 s / 3.6e6
  = 3031.5 W · 10 000 s = 8.420833333… kWh
```

independent of miner count and search discipline. This is an **accounting
identity, not an empirical hypothesis** — see
`STAGE_05B1_PREREGISTRATION_AMENDMENT.md`. The engine reproduces
`8.420833333 kWh` for B0/B1/B2/B3_C1 across all validated counts (100–500).

## 5. Optional full-log emission

`run_scenario(cfg, emit_log=True)` additionally returns `block_log`, a list of
one record per accepted block (winner, winner time, solutions found, exhausted
generations, per-round evaluation counts, propagation messages). It is **off by
default** and does not change any measured outcome (regression-tested). It backs
the measured storage projection.

## 6. What the engine deliberately does NOT claim

- No total-energy reduction from deduplication, disjoint ranges, or common
  templates. Dedup changes **coverage/energy-per-block**, not total energy.
- No C2 saving in the homogeneous equal-range baseline (idle ≡ 0 there).
- No fairness / incentive / Sybil conclusions (those mechanisms are unimplemented).
- Coordination energy is reported as an explicit **idealized lower bound of 0**,
  with the unmeasured agreement cost recorded as `null`.
