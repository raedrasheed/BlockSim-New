# Stage 5B1A — Matrix Changelog

Regenerated matrix: `STAGE_05B1A_FINAL_MATRIX.csv`
Predecessors (unchanged, immutable): `STAGE_05A_FINAL_MATRIX.csv`,
`STAGE_05B1_FINAL_MATRIX.csv`
Builder: `experiments/thesis_revision_v43/build_matrix_5b1a.py`

## 1. Provenance

Both earlier matrices remain byte-for-byte frozen. Stage 5B1A writes a new versioned
matrix by reusing the Stage-5B1 semantic-deduplication (naive 2 760 → −870 B3≡C1 →
1 890) and adding measurement-correctness metadata. The scenario/class distribution
is **identical** to Stage 5B1 (and 5A); the B2 exactness fix and the zero-block fix
change *measured outputs*, not the matrix membership.

## 2. Row accounting (unchanged from Stage 5B1)

| Line item | Count |
|-----------|------:|
| Naive planned rows (B3, C1 separate) | 2 760 |
| Exact duplicates removed | 0 |
| B3 ≡ C1 semantic merge | 870 |
| Other semantic duplicates | 0 |
| **Final Stage-5B2 run count** | **1 890** |
| Hard ceiling | 3 500 (under ✅) |

distinct `configuration_hash` = 1 890 · distinct `execution_semantics_hash` = 1 890
· distinct `analysis_group_hash` = 63. The B2 correction does **not** change any
`execution_semantics_hash` (builder asserts stored == recomputed for all 1 890 rows;
test 35).

## 3. New columns vs Stage 5B1

| Column | Meaning |
|--------|---------|
| `expected_zero_block_probability` | analytical P(0 blocks) from config (B1 material; B2 null/unmodeled; else ≈0) |
| `zero_block_risk_category` | `low` / `high` / `very_high` / `unmodeled` |
| `output_schema_version` | `5b1a.1` |
| `retention_full_log` | stratified retention flag (61 True) |
| `retention_reason_codes` | `;`-joined reason codes per retained run |

Zero-block risk distribution: `low` 1 590 · `high` 30 (B1 N=100) · `very_high` 120
(B1 N≥200) · `unmodeled` 150 (B2).

## 4. Checksums

- Matrix SHA-256: `e436609d…d404fc`
- Retention checksum: `2283f2ff…1702e`
- Seed schedule (unchanged): `6122dbd0…b13e10`

## 5. Engine behaviour changes reflected downstream (not in matrix membership)

- **B2** duplicate/distinct now integer-exact (was ≤15% off).
- **B1** now reports 0 accepted blocks in the majority of seeds (zero-block fix);
  block metrics are NA when undefined.
- Per-miner and per-template summaries are emitted for every run.
- Coordination bytes are split by category; only block propagation carries bytes.
