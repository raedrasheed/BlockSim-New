# Stage 5B1D — Impact Audit

The sampler change is a scientific-code change: it alters the `solution_positions`
random stream, so per-seed outputs change. This audit records what is affected, how
it was revalidated, and the freeze invalidation.

## 1. Engine version and hash regeneration

- `ENGINE_VERSION` bumped **`5b1b.1 → 5b1d.1`**.
- `scientific_semantics_hash` and `run_execution_hash` include the engine version, so
  both are **regenerated** for all 1 890 rows. (Scientific *semantics definitions* are
  unchanged; the version bump records the corrected code identity.)
- New matrix `STAGE_05B1D_FINAL_MATRIX.csv`, SHA-256
  `ab47f289b5f13f34b5af65e4c7cea0ee71d7b1e64d40ee04c3d50b4323e1efae`. The Stage-5B1B
  matrix and its hashes are preserved unchanged.

## 2. Outputs affected by the stream change

Every scenario's per-seed positions change → downstream per-seed values
(`min_pos`, winner time, B2 coverage magnitude, per-round evaluation counts, block
timings) change. Structural invariants are unchanged: continuous-energy A1
(8.420833333 kWh), B3/C1 zero duplicates, C2 idle reconciliation, duplicate-rate
ordering B3 < B2 < B1, and the B1 zero-block law.

## 3. Freeze invalidation and historical preservation

- Freeze **`thesis-v43-stage5b2-freeze-1`** (commit `c0ff48e4…`) is **invalidated for
  execution** and preserved unchanged as an historical freeze.
- Stage-5B1B / 5B1A / 5A validation outputs are kept as historical artifacts; 5B1D
  outputs are written to `results/thesis_revision_v43/stage_05b1d/` and are **not**
  mixed with them.

## 4. Revalidation (same design as Stage 5B1B)

`experiments/thesis_revision_v43/validate_5b1d.py` — B1 event-loop zero-block,
5 miner counts × 30 validation seeds (disjoint from the frozen schedule), exact
analytical P_zero, independent direct reference, exact 99% Clopper-Pearson.

| N | exact P0 | direct-ref | event-loop (30) | 99% CI | exact ∈ CI |
|---|---------:|-----------:|----------------:|--------|:---:|
| 100 | 0.8465 | 0.8469 | 0.833 | [0.596, 0.962] | ✅ |
| 200 | 0.9200 | 0.9205 | 0.900 | [0.680, 0.988] | ✅ |
| 300 | 0.9460 | 0.9445 | 0.900 | [0.680, 0.988] | ✅ |
| 400 | 0.9592 | 0.9598 | 0.900 | [0.680, 0.988] | ✅ |
| 500 | 0.9672 | 0.9671 | 0.900 | [0.680, 0.988] | ✅ |

The exact analytical B1 model is unchanged (its input `M = unique_rate·T` does not
depend on the sampler), and it remains consistent with the corrected event loop.
Binomial-count = distinct-position-count reconciliation holds over 2 000 draws.
Scenario sanity (B2 total = distinct + duplicate, B3 energy A1, C2 energy
reconciliation) passes.

## 5. Two prior tests updated (necessitated by the correction)

| Test | Change | Reason |
|------|--------|--------|
| `stage5b1a … test_b2_total_equals_distinct_plus_duplicate` | absolute `< 1e-6` → relative `rel_tol=1e-12` | B2 coverage now ~10¹⁸; the exact integer identity is preserved but float64 loses integer exactness above 2⁵³, so a relative tolerance is correct |
| `stage5b1b … test_freeze_inputs_complete` | hardcoded `"5b1b.1"` → `ENGINE_VERSION` | required engine-version bump; the test now tracks the current version |

No scientific test logic was weakened; both changes are exactness-preserving.

## 6. Full test suite

`python3 -m pytest tests/ -q` → **292 passed** (24 new Stage-5B1D + 268 prior).
Thesis DOCX/PDF byte-identical.

## 7. New freeze

One corrective commit is created (not amending `c0ff48e4…`, not updating the old
branch). After it is pushed, a new remote freeze branch
**`thesis-v43-stage5b2-freeze-2`** must be created pointing exactly to the corrective
commit SHA. Stage 5B2 may run only from freeze branch 2.
