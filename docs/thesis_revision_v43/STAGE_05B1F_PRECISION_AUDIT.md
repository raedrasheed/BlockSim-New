# Stage 5B1F — Precision Audit and Finder Taxonomy

Engine: `scenario_engine.py` (`apportion_int`, `_completed`, `_resolve`)
Tests: `test_stage5b1f_precision.py` (33–37)

## 1. Integer hash rates (Section 7)

The network hash rate is an **integer** number of hashes/s
(`141e12 → 141 000 000 000 000`). `apportion_int` distributes it over the miner shares
by largest-remainder so that

```
Σ miner_hash_rate_hps_int == network_hash_rate_hps_int   (exact, any shares)
```

verified for homogeneous, heterogeneous-moderate, and heterogeneous-high (test 33).
Each result carries `network_hash_rate_hps_int` and `integer_rates_sum_exact = true`;
per-miner rows carry `hash_rate_hps_int`.

## 2. Rational time and exact counts

Discovery times are exact `Fraction(offset + 1, rate_int)`; ordering is exact rational
comparison, equivalent to cross-multiplication `(d_i+1)·H_j` vs `(d_j+1)·H_i`
(test 34). Candidate counts are `_completed = (rate · t.numerator) // t.denominator`,
integer division on integer rate × rational time — **exact**, including above 2⁵³
(test 35). This replaces the earlier `floor(float_rate · float_time)`, so the engine
no longer relies on "Python int type" alone as a claim of exactness: the arithmetic
itself is exact. `total == distinct + duplicate` holds as exact integer equality; for
B2 the exhaustion counts come from the exact circular union.

## 3. Finder / solution taxonomy (Section 11)

Ambiguous fields are replaced/augmented with an explicit taxonomy:

| Field | Meaning |
|-------|---------|
| `total_template_solution_position_count` | number of solution **positions** in the template domain |
| `active_range_solution_position_count` | positions in active ranges |
| `inactive_range_solution_position_count` | positions in inactive ranges |
| `distinct_potential_finder_miner_count` | distinct **miners** with a reachable solution |
| `actual_proposal_miner_count` | miners that actually proposed a block |
| `actual_competitor_miner_count` | distinct miners with a competing (distinct-identity) block |
| `legitimate_stale_block_count` | competing blocks discovered within the delay window |

Solution **positions** are never reported as finder **miners** (test 36): one miner may
own several positions but is a single finder. Actual competitors are always **distinct
miners** — B1's many same-header finders yield `actual_competitor_miner_count = 0`
(test 37).
