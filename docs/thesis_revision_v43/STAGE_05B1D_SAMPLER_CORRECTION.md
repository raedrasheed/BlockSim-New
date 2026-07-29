# Stage 5B1D — Exact Solution-Position Sampling Correction

Module: `experiments/thesis_revision_v43/exact_sampling.py`
Tests: `tests/thesis_revision_v43/stage5b1d/test_stage5b1d_sampler.py` (1–17)

## 1. The rejected defect

Stage 5B1C's READY verdict was **correctly rejected**. The frozen sampler was

```python
pos = np.unique(rng.integers(0, S, size=k))
```

This is with-replacement sampling plus deduplication: on a collision `len(pos) < k`,
so it does **not** guarantee exactly k distinct positions. "Probabilistically unique
because S is large" is not exact without-replacement sampling. Freeze
`thesis-v43-stage5b2-freeze-1` is therefore an **historical invalidated freeze**
(preserved unchanged; never moved, overwritten, deleted, or reused).

## 2. The exact algorithm

`sample_without_replacement(rng, S, k)` returns exactly k distinct integers sampled
uniformly without replacement (each of the C(S,k) subsets equally likely), using
**Floyd's algorithm** (Bentley & Floyd, *Programming Pearls*, CACM 1987; Knuth TAOCP
Vol. 2, Alg. S/R):

```
selected = {}
for j in [S-k, S-1]:
    t = uniform integer in [0, j]        # inclusive
    add (t if t not in selected else j)
```

- **Exactly k draws** from the named stream → O(k) time, **O(k) memory**; never
  allocates an array of size S. For k > S/2 (only reachable at small S — at thesis
  scale k = Binomial(S,p) is tiny) it samples the (S−k)-element complement to keep
  work O(min(k, S−k)); that branch enumerates the small domain and is never reached
  at thesis scale.
- No oversampling; **no `[:k]` truncation**; no with-replacement+unique dedup.

## 3. Ordering semantics (Section 4)

Sampling occurs **without replacement first**; the completed exact k-subset is then
**sorted** (`arr.sort()`) so the engine can identify the earliest solution. Sorting
is applied only after the exact subset exists — never as truncation of a larger
sample.

## 4. Hard reconciliation invariant (Section 6)

The engine asserts, for every template generation with `k = Binomial(S,p) > 0`:

```
pos = exact_sampling.sample_without_replacement(r_solpos, S, k)
if pos.size != k or np.unique(pos).size != k:
    raise RuntimeError(...)          # stops the run; never silently reduces k
```

so `sampled_solution_count == len(solution_positions) == distinct_positions` always.

## 5. Edge cases (all tested)

k=0 (empty), k=1, k=S (full domain), k=S−1, small S, S=10¹⁷ small k (no allocation),
invalid k<0 and k>S (raise `ValueError`), deterministic reproducibility, int64
dtype. Tests 1–17.

## 6. Impact

Changing the position sampler changes the `solution_positions` random stream, so
every scenario's per-seed outputs change (see `STAGE_05B1D_IMPACT_AUDIT.md`). The
scenario-engine version is bumped `5b1b.1 → 5b1d.1`; `scientific_semantics_hash` and
`run_execution_hash` (which include the engine version) are regenerated.
Distributional uniformity is validated in `STAGE_05B1D_UNIFORMITY_AUDIT.md`.
