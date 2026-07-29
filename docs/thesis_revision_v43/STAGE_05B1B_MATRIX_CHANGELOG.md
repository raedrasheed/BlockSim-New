# Stage 5B1B — Matrix Changelog

Regenerated matrix: `STAGE_05B1B_FINAL_MATRIX.csv`
Predecessors (unchanged, immutable): `STAGE_05A_FINAL_MATRIX.csv`,
`STAGE_05B1_FINAL_MATRIX.csv`, `STAGE_05B1A_FINAL_MATRIX.csv`
Builder: `experiments/thesis_revision_v43/build_matrix_5b1b.py`

## 1. Provenance

All earlier matrices remain byte-for-byte frozen. Stage 5B1B reuses the Stage-5B1
semantic dedup (naive 2 760 → −870 B3≡C1 → 1 890) and adds the corrected hash
taxonomy, exact B1 fields, and all stream seeds. Matrix **membership is unchanged**;
the changes are in provenance metadata and in engine behaviour (below).

## 2. Row accounting (unchanged)

Naive 2 760 → −0 exact → −870 B3≡C1 → −0 other semantic → **1 890** final ≤ 3 500.

## 3. Engine behaviour changes reflected downstream (not in membership)

| Change | Effect |
|--------|--------|
| B1 exhausted-generation timing `S/max_rate` | B1 no longer produces blocks too fast |
| B1 solution-position sampling (draw exactly k) | removes ~2× `min_pos` downward bias |
| Combined | engine B1 zero-frequency now matches the exact model within the 99% CI |

`scenario_engine_version` bumped `5b1a.1 → 5b1b.1` (behaviour change).

## 4. New / changed columns vs Stage 5B1A

| Column | Change |
|--------|--------|
| `scientific_semantics_hash` | NEW — semantics only, seed excluded (63 groups) |
| `run_execution_hash` | NEW — semantics + seed + streams + engine + deps (1 890 unique) |
| `interpretation_hash` | NEW — labels/role; B3 vs C1 differ, share run hash |
| `analysis_group_hash_v2` | NEW — intended comparison group |
| `master_seed` + `stream_seed_*` (×8) | NEW — full seed provenance |
| `expected_zero_block_probability_exact` / `_poisson` | NEW — replaces the single 5B1A probability |
| `expected_unique_candidate_evaluations`, `expected_full_template_generations`, `expected_partial_generation_candidates` | NEW |
| `analytical_model_version` | NEW (`b1-exact-1`) |
| `scenario_engine_version` | `5b1a.1` → `5b1b.1` |
| `zero_block_risk_category` | recomputed from exact P0 |

## 5. Removed arbitrary tolerance

The 5B1A B1 validation used a 0.25 absolute tolerance. Stage 5B1B replaces it
everywhere with the exact-P0-within-99%-Clopper-Pearson-CI criterion (the 5B1A test
and runner check were updated accordingly). No arbitrary tolerance remains.

## 6. Full checksums (64-hex)

- Matrix `306d82834395a6bb159dbacf713eaf2290a7ada52c1e9c451c031d09014edce5`
- Seed schedule `6122dbd0f455a1c4c9676ec6575f064c3a682b3c978705d6588af11489b13e10`
- Retention list `2283f2ff69bcabf423267b2984ef4acfce852b217b39e1efe8061e583bc1702e`
- Dependency lock `6e211ea7c031a3fab560843690e27e5a3c2aa2a8c363ab483369a2babc8157be`
