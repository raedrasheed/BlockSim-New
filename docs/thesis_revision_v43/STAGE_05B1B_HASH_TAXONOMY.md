# Stage 5B1B — Corrected Hash Taxonomy

Module: `experiments/thesis_revision_v43/hash_taxonomy.py`
Tests: `tests/thesis_revision_v43/stage5b1b/test_stage5b1b_hash_taxonomy.py` (11–20)

## 1. The defect

The Stage-5B1 `execution_semantics_hash` **included the master seed**, so it
identified a *run*, not a *scientific configuration*. It could not group the 30
seeds of one configuration, conflating scientific execution semantics with
stochastic run identity.

## 2. Four explicit layers

| Layer | Hash | Includes | Excludes |
|-------|------|----------|----------|
| A | `scientific_semantics_hash` | executable scenario (exec model), miner count, duration, network hash rate, distribution & params, efficiency, target & interval, μ / domain, allocation policy (disjoint), search policy, idle policy, idle-power ratio (when active), inactive fraction, propagation-delay model, block config, **engine version** | seed, stream seeds, run_id, path, timestamp, worker, B3-vs-C1 labels, retention flags, presentation |
| B | `run_execution_hash` | scientific_semantics_hash + master seed + **all 8 derived stream seeds** + engine version + dependency-lock checksum | — (identifies ONE physical run) |
| C | `interpretation_hash` | interpretive labels + reporting role (hypothesis, class) | — (never creates a physical run) |
| D | `analysis_group_hash` | exec model + hypothesis + matrix class + design factors | seed (identifies the intended comparison group) |

`output_schema_version` is **excluded** from layer A (it changes output format, not
measured values); `engine_version` is **included** (it can change measured values).

## 3. How the layers relate

- **A groups, B identifies.** All 30 seeds of a configuration share one
  `scientific_semantics_hash` (layer A) but have 30 distinct `run_execution_hash`
  (layer B). Seeds are excluded from A (test 11) and included in B (test 12).
- **B3 vs C1.** They differ in `interpretation_hash` (layer C) but share one
  `run_execution_hash` (layer B) — one physical run, two interpretations (tests 13,
  17).
- **A vs D.** `scientific_semantics_hash` is one exact executable config;
  `analysis_group_hash` is the intended statistical/paired group and keys on
  hypothesis + class. They are conceptually distinct (test 14): a design that pooled
  several configs into one comparison would give a coarser D than A. In *this*
  matrix each analysis cell is exactly one scientific config, so both partitions
  happen to have **63** groups.

## 4. Audit result (1 890 rows)

| Quantity | Count |
|----------|------:|
| distinct `scientific_semantics_hash` | **63** (each repeated across 30 seeds) |
| distinct `run_execution_hash` | **1 890** (every physical run unique) |
| distinct `interpretation_hash` | 12 |
| distinct `analysis_group_hash` | 63 |
| semantics groups not of size 30 | 0 |
| duplicate run-execution hashes | 0 |
| duplicate same-seed same-semantics pairs | 0 |
| B3;C1 dual-label rows (one run each) | 870 |

`63 × 30 = 1 890`. The number 63 is not forced — it is the count of distinct
non-seed scientific configurations the frozen design specifies, confirmed by the
audit (`STAGE_05B1B_HASH_GROUP_AUDIT.json`).
