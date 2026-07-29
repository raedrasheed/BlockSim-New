# Stage 5B1 — Matrix Changelog

Regenerated matrix: `STAGE_05B1_FINAL_MATRIX.csv`
Frozen predecessor: `STAGE_05A_FINAL_MATRIX.csv` (**unchanged, immutable**)
Builder: `experiments/thesis_revision_v43/build_matrix_5b1.py`

## 1. Provenance

The Stage-5A matrix remains byte-for-byte frozen. Stage 5B1 writes a **new
versioned** matrix, derived by a re-runnable builder that adds two hashes and a
transparent semantic-deduplication audit. The final scenario/class distribution
is **identical** to Stage 5A — Stage 5B1 changes the *derivation and provenance*,
not the experimental content.

## 2. Row-accounting (deliverable §18)

| Line item | Count |
|-----------|------:|
| Naive planned rows (B3 and C1 enumerated separately) | **2 760** |
| Rows removed as exact duplicates (`configuration_hash`) | **0** |
| Rows merged through B3/C1 reuse (`execution_semantics_hash`) | **870** |
| Rows removed as other semantic duplicates | **0** |
| Validation-only rows (in executable matrix) | **0** |
| **Final Stage-5B2 run count** | **1 890** |
| Hard ceiling | 3 500 |
| Under ceiling | ✅ |

## 3. What changed vs Stage 5A

| Aspect | Stage 5A | Stage 5B1 |
|--------|----------|-----------|
| Hashes per row | 1 (`configuration_hash`) | 3 (`configuration`, `execution_semantics`, `analysis_group`) |
| B3/C1 provenance | pre-merged label `B3;C1` (asserted) | **derived** via `execution_semantics_hash` (audited, 870 reuse rows) |
| H2 status | confirmatory hypothesis | **reclassified to Accounting Invariant A1** (see amendment) |
| `reused_by_hypotheses` column | — | added |
| `retain_full_log` column | — | added (41 full logs) |
| `validation_only` column | — | added |
| Row provenance | frozen list | re-runnable builder + summary JSON |

## 4. New columns in `STAGE_05B1_FINAL_MATRIX.csv`

`execution_semantics_hash`, `analysis_group_hash`, `reused_by_hypotheses`,
`retain_full_log`, `validation_only`, plus the original Stage-5A columns.
`run_id` re-indexed as `S5B2-00000 … S5B2-01889`.

## 5. Hashes and checksums

- distinct `configuration_hash` = 1 890
- distinct `execution_semantics_hash` = 1 890 (every run a unique execution)
- distinct `analysis_group_hash` = 63
- seed schedule SHA-256 = `6122dbd0…b13e10` (unchanged from Stage 5A)
- full-log retention sample SHA-256 = `b894c5e7…801cec`

## 6. Distribution (unchanged from Stage 5A)

By scenario: B0 150 · B1 150 · B2 150 · B3_C1 870 · C2 570.
By class: CORE 600 · CORE_C2 150 · SENS_IDLE 300 · SENS_HETERO 240 · SENS_MU 120
· SENS_INACTIVE 180 · SENS_DELAY 240 · EXPLORATORY 60.
