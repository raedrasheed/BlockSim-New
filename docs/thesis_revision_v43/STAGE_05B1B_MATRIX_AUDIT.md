# Stage 5B1B — Matrix Audit

Matrix: `STAGE_05B1B_FINAL_MATRIX.csv`
Audit: `STAGE_05B1B_HASH_GROUP_AUDIT.json`
Builder: `experiments/thesis_revision_v43/build_matrix_5b1b.py`
Predecessors (unchanged, immutable): `STAGE_05A_FINAL_MATRIX.csv`,
`STAGE_05B1_FINAL_MATRIX.csv`, `STAGE_05B1A_FINAL_MATRIX.csv`

## 1. Composition (unchanged membership)

1 890 runs · under the 3 500 ceiling. Scenario distribution B0 150 · B1 150 · B2 150
· B3_C1 870 · C2 570. The B2 exactness fix (5B1A) and the B1 engine fixes (5B1B)
change *measured outputs*, not matrix membership.

## 2. Hash-group audit

| Property | Expected | Observed |
|----------|---------|----------|
| distinct `scientific_semantics_hash` | 63 | **63** |
| each semantics group size | 30 | **30** (all) |
| distinct `run_execution_hash` | 1 890 | **1 890** |
| duplicate run-execution hashes | 0 | **0** |
| duplicate same-seed same-semantics pairs | 0 | **0** |
| B3/C1 share one physical run | yes | **870 dual rows** |
| distinct `analysis_group_hash` | 63 | 63 |
| distinct `interpretation_hash` | — | 12 |

Group-size distribution: `{30: 63}` — every one of the 63 scientific configurations
has exactly its 30 seeds, no more, no fewer.

## 3. New columns vs Stage 5B1A

- Four-layer hashes: `scientific_semantics_hash`, `run_execution_hash`,
  `interpretation_hash`, `analysis_group_hash_v2`.
- Master seed + **all 8 named stream seeds** per row
  (`stream_seed_solution_positions`, `…_solution_count`, `…_miner_starts`,
  `…_hash_rate_distribution`, `…_propagation_delay`, `…_inactive_selection`,
  `…_topology`, `…_transaction_arrival`).
- Exact B1 zero-block fields: `expected_zero_block_probability_exact` and
  `_poisson`, `expected_unique_candidate_evaluations`,
  `expected_full_template_generations`, `expected_partial_generation_candidates`,
  `analytical_model_version`.
- `scenario_engine_version = 5b1b.1`, `output_schema_version = 5b1a.1`.
- Retention flags/reasons (61 full logs) carried forward from Stage 5B1A.

## 4. Full checksums (64-hex)

| Artifact | SHA-256 |
|----------|---------|
| Matrix | `306d82834395a6bb159dbacf713eaf2290a7ada52c1e9c451c031d09014edce5` |
| Seed schedule | `6122dbd0f455a1c4c9676ec6575f064c3a682b3c978705d6588af11489b13e10` |
| Retention list | `2283f2ff69bcabf423267b2984ef4acfce852b217b39e1efe8061e583bc1702e` |
| Dependency lock | `6e211ea7c031a3fab560843690e27e5a3c2aa2a8c363ab483369a2babc8157be` |

All four are reproducible (tests 22–25). The matrix is not executed in this stage.
