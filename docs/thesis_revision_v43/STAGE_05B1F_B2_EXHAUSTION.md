# Stage 5B1F — Exact B2 Domain-Exhaustion Time

Module: `coverage.py` (`b2_exhaustion_time`, `coverage_at_time`,
`exhaustion_time_reference_small`)
Tests: `test_stage5b1f_exhaustion_time.py` (11–16)

## 1. The defect

B2 used `D_ex = S / Σ rates`, which assumes perfect non-overlapping coverage. With
seeded random starts, miners **overlap**, so the domain is exhausted **later**.

## 2. Exact method

The domain is exhausted at the earliest time `t_ex` when the union of all miners'
swept circular arcs covers the whole domain:

```
union_length(t_ex) = S
```

`b2_exhaustion_time` does a monotone binary search over time, computing the union at
each candidate time with the **exact circular interval-union** (`coverage_at_time`).
Each miner covers `min(S, floor(rate_i · t))` candidates from its start; overlap never
counts as new coverage; each miner is capped at one full traversal; inactive miners
(rate 0) contribute no path.

## 3. Properties (all tested)

| # | Property | Test |
|---|----------|------|
| 1 | coverage just before `t_ex` is `< S` | 12 |
| 2 | coverage at `t_ex` is exactly `S` | 11 |
| 3 | overlapping work does not count as new coverage (overlap ⇒ later exhaustion) | 13 |
| 4 | inactive miners contribute no path | 15 |
| 5 | no miner evaluates more than one full traversal | 16 |
| 6 | matches exhaustive small-domain reference | 14 |

The small-domain reference is `t_ex = max_q min_i ((q − start_i) mod S + 1)/rate_i`
(the last position's first-cover time); `b2_exhaustion_time` matches it to 1e-4 on
every tested case (e.g. S=20/30/12).

## 4. Recorded at exhaustion

`b2_exhaustion_time` returns `t_ex` and the exact integer counts at exhaustion
(`total`, `distinct == S`, `duplicate`). The engine uses `t_ex` as the exhausted-B2
generation duration; distinct coverage is exactly `S`, and `total == distinct +
duplicate` holds as exact integers.
