# Stage 5B1D — Distributional Uniformity Audit

Module: `experiments/thesis_revision_v43/uniformity_audit_5b1d.py`
Data: `STAGE_05B1D_UNIFORMITY_RESULTS.json`,
`results/thesis_revision_v43/stage_05b1d/uniformity_results.json`
Tests: 12–14 in `test_stage5b1d_sampler.py`

Exactness is **not** claimed from "zero observed collisions." It is demonstrated by
comparing the sampler's empirical subset frequencies to the exact combinatorial
uniform on small domains.

## 1. Acceptance criterion (declared before running)

Chi-square goodness-of-fit statistic below the **99.9%** critical value (p > 0.001)
for each enumerated case → uniformity not rejected; order-statistic frequency error
< 0.01.

## 2. Subset uniformity (enumerate all C(S,k), Monte-Carlo, chi-square)

| Case | subsets C(S,k) | trials | χ² | dof | crit (99.9%) | p-value | max |freq−1/C| | pass |
|------|---------------:|-------:|----:|----:|-------------:|--------:|-----------------:|:---:|
| S=5, k=2 | 10 | 200 000 | 13.44 | 9 | 27.88 | 0.144 | 0.0020 | ✅ |
| S=6, k=3 | 20 | 300 000 | 9.28 | 19 | 43.82 | 0.969 | 0.0007 | ✅ |
| S=10, k=1 | 10 | 100 000 | 12.99 | 9 | 27.88 | 0.163 | 0.0021 | ✅ |
| S=10, k=9 | 10 | 100 000 | 12.99 | 9 | 27.88 | 0.163 | 0.0021 | ✅ |

The `k=9` case exercises the complement branch (k > S/2) and is also uniform.

## 3. Order-statistic distributions (exact combinatorial reference)

For a uniform k-subset of {0,…,S−1}: `P(min=m)=C(S−1−m,k−1)/C(S,k)`,
`P(max=m)=C(m,k−1)/C(S,k)`.

| Case | max |P(min) error| | max |P(max) error| | pass |
|------|-------------------:|-------------------:|:---:|
| S=10, k=3 | 0.0005 | 0.0013 | ✅ |
| S=8, k=4 | 0.0010 | 0.0016 | ✅ |

Minimum, maximum, and ordered-gap distributions all match their combinatorial
references. The minimum-position audit is the direct fix of the earlier 2× min-bias:
empirical min matches the exact `C(S−1−m,k−1)/C(S,k)` law.

## 4. Verdict

All uniformity and order-statistic checks pass. The sampler produces a uniform
without-replacement k-subset, demonstrated by exact combinatorial comparison — not
merely by the absence of collisions.
