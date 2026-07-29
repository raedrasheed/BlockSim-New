# Stage 5B1A — Final Measurement Corrections Report

Closes the remaining pre-execution validity issues before the frozen matrix runs.
**No full-matrix execution.** Bounded validation only (88 runs ≤ 100 cap; all 53
checks pass — `results/thesis_revision_v43/stage_05b1a/validation_report_5b1a.json`).
Test suite: **235 passed** (46 new Stage-5B1A + 189 prior).

## 1. What changed in the engine

| # | Correction | Effect |
|---|-----------|--------|
| 1 | **Exact B2 circular coverage** (`coverage.py`) replaces the linear-merge approximation | duplicate/distinct counts are now integer-exact vs an exhaustive reference (was ≤15% off) |
| 2 | **Zero-block completion fix** | a block counts only if its round completes within the 10 000 s horizon; B1 now correctly reports **0 blocks** in 67–83% of seeds instead of a forced 1 |
| 3 | **NA-aware block metrics** | `energy_per_accepted_block`, `effective_block_interval`, `confirmation_time_proxy`, `stale_rate` are `null` + reason when undefined — never 0/inf |
| 4 | **Per-miner & per-template summaries** (`emit_detail`) | full stable-schema detail for every run; reconcile to network totals |
| 5 | **Categorized coordination** | five message categories separated; only block propagation carries bytes (configured size); control bytes `null`; abstract agreement energy `null` |
| 6 | **Engine / schema versioning** | `ENGINE_VERSION`, `OUTPUT_SCHEMA_VERSION` stamped on every result |

Each correction is detailed in its own document (B2 exactness, zero-block policy,
storage projection, retention policy, coordination schema, code-freeze manifest).

## 2. The one revised prior-stage test

The zero-block fix makes B1 legitimately produce 0 blocks. Exactly **one** Stage-5B1
assertion encoded the old "B1 always ≥1 block" behaviour
(`test_b1_simultaneous_discovery_handling`) and one runner check (`validate_5b1.py`
`G-B1`). Both were revised to assert the corrected semantics ("at most one block
per completed round, never ~N; may be zero"), preserving their real intent. This is
the only change to the Stage-5B1 test surface; all other Stage-5B1 tests pass
unchanged (`test_all_stage5b1_tests_unchanged`).

## 3. Matrix and freeze

- Regenerated matrix `STAGE_05B1A_FINAL_MATRIX.csv`: **1 890 runs** (unchanged count;
  B3≡C1 audit reproduced), now with `expected_zero_block_probability`,
  `zero_block_risk_category`, `output_schema_version`, `retention_full_log`,
  `retention_reason_codes`. Semantic hashes verified **unchanged** by the B2 fix.
- Stratified retention: **61** full logs (was 41), every scenario × count + every
  sensitivity level + five interesting regimes + 1% remainder; checksum
  `2283f2ff…1702e`.
- Storage re-estimated from the **expanded** artifact set: **≈ 618 MB uncompressed /
  ≈ 20 MB gzip** (supersedes the summary-only 3.3 MB).
- Code-freeze manifest complete: matrix / seed / retention / dependency-lock
  checksums + schema & engine versions + test result + thesis SHAs.

## 4. What is NOT done (awaiting approval)
- The full 1 890-run matrix is **not** executed.
- Stage 5B2 is **not** started.
- No Stage-6 statistical analysis.
- The thesis DOCX/PDF are untouched (SHA-256 verified byte-identical).
