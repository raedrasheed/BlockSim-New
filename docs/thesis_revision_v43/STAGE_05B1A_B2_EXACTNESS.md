# Stage 5B1A — B2 Exact Circular-Coverage Correction

Module: `experiments/thesis_revision_v43/coverage.py`
Tests: `tests/thesis_revision_v43/stage5b1a/test_stage5b1a_b2_exact.py` (1–8)

## 1. The defect

B2 (common template, seeded random starts, single forward traversal) measures
**duplicate rate** and **distinct coverage** — both *primary* outcomes. Stage 5B1
computed coverage with a **linear** interval merge that ignored the ring topology:
a miner whose arc runs off the end of the domain (`start + length > S`) was not
wrapped back to `[0, …)`, so the wrapped portion was mis-counted. The Stage-5B1
report acknowledged agreement with a circular brute force only "within ~15%". That
is not acceptable for a primary outcome.

## 2. The exact method

Each miner's searched set is the circular arc
`{ (start_i + k) mod S : 0 ≤ k < length_i }`, represented as **exact integer
half-open intervals**:

| Case | Intervals |
|------|-----------|
| `length == 0` | `[]` |
| `length ≥ S` | `[(0, S)]` (whole ring, once) |
| `start + length ≤ S` | `[(start, start+length)]` |
| otherwise (wrap) | `[(start, S), (0, start+length−S)]` |

`interval_union_length` sorts and merges the intervals — **O(n log n)**, no domain
enumeration — giving the exact integer count of distinct covered positions. Then

```
total     = Σ length_i                      (single-traversal capped at S)
distinct  = |union of all arcs|
duplicate = total − distinct
```

so `total = distinct + duplicate` holds **by construction**. Winner time and
identity come from `b2_winner`: `winner_time = min over (miner i, solution q) of
((q − start_i) mod S)/rate_i`.

## 3. Exactness evidence (tests 1–8, all pass)

| Test | Property | Result |
|------|----------|--------|
| 1 | union == exhaustive, no wrap | exact |
| 2 | union == exhaustive, with wrap | exact |
| 3 | multiple wrapped paths, heavy overlap | exact |
| 4 | one / many miners cover whole domain → distinct == S | exact |
| 5 | duplicate count exact (identical arcs) | exact |
| 6 | winner time & identity == independent reference | exact |
| 7 | S = 10¹⁷ handled with no enumeration | O(n) |
| 8 | total == distinct + duplicate (50 random cases + engine) | exact |

Edge cases covered: zero-length paths, full-domain traversal, wraparound,
overlapping wrapped/non-wrapped arcs, identical starts, one miner covering the
whole domain, multiple miners covering the whole domain.

## 4. Consequence for the science

At full scale the exact method gives B2 duplicate rates of **0.34–0.58** (seeds),
firmly between B3/C1 (0) and B1 (~0.99) — the qualitative ordering **B3 < B2 < B1**
is preserved, now with integer-exact values. The ≤15% approximation error is
eliminated. The correction changes only the *measured coverage numbers*; the B2
`execution_semantics_hash` is a pure function of configuration and is **unchanged**
(test 35), so the matrix identity and dedup are unaffected.
