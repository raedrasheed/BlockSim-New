# Stage 5B1E — Integer Candidate-Metrics Audit

Tests: `test_stage5b1e_integer.py` (21–25)

## 1. Requirement (Section 6)

Candidate-count metrics are exact **Python integers** end to end — never cast to
float. The reconciliation

```
total_candidate_evaluations == distinct_candidate_evaluations + duplicate_candidate_evaluations
```

must hold with **exact integer equality** (no relative tolerance). Rates, times,
energy, and percentages remain floating-point. An estimated quantity would carry an
`_estimated` suffix; none is used for candidate counts.

## 2. What is exact

| Metric | Type | Basis |
|--------|------|-------|
| `total_candidate_evaluations` | int | Σ per-miner `c_i` (disjoint) / Σ arc lengths (B2) |
| `distinct_candidate_identities` | int | = total (disjoint) / exact circular union (B2) / fastest coverage (B1) |
| `duplicate_evaluations` | int | total − distinct |
| `total_template_solution_count`, `active_/inactive_range_solution_count` | int | K and range classification |
| per-miner `candidates_evaluated` | int | cumulative `c_i` |

The accumulators are Python ints (unbounded precision), so the reconciliation is
exact even far above 2⁵³. B2 coverage (`coverage.py`) is integer interval arithmetic,
exact above 2⁵³ as well.

## 3. Results

- **Disjoint (B0, B3/C1, C2, equal & weighted):** `duplicate_evaluations == 0`
  exactly — no fabricated overlap (test 25).
- **Above 2⁵³:** B1 total ≈ 10¹⁸ with `total == distinct + duplicate` exact; B2
  interval-union exact for S = 10¹⁷ (test 22).
- **All scenarios:** exact integer reconciliation, no float tolerance (test 23); all
  candidate fields are `int` (tests 21, 24).

Note: the old B2 engine-level reconciliation test used a relative tolerance because
counts were stored as floats; with Python-int accumulators the equality is now
**exact**, and the corresponding assertions use exact `==`.
