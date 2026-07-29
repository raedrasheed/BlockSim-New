# Stage 5B1A — B1 Zero-Block Analytical Audit and NA Policy

Model: `experiments/thesis_revision_v43/b1_zero_block.py`
Table: `STAGE_05B1A_B1_ZERO_BLOCK_TABLE.json`
Tests: `test_stage5b1a_b1_zero_block.py` (9–15)

## 1. The engine defect it corrects

The Stage-5B1 loop incremented `accepted += 1` for the final partial round even
when the round did **not** complete within the 10 000 s horizon. B1 (all miners
race the same path from nonce 0) therefore always reported ≥1 block, when in fact a
single miner's rate governs block production and a block usually is **not** found
in time. The fix: a block is accepted **only if `round_dur ≤ remaining horizon`**;
otherwise miners spend the remaining time searching (energy still accrues) and the
run ends with **0 accepted blocks**.

## 2. Analytical model

In B1 only the leading miner advances the unique frontier, so the effective unique
hash rate is

```
homogeneous   : H_unique = H_total / N
heterogeneous : H_unique = max_i H_i        (== H_total/N when homogeneous)
```

With per-candidate success probability `p = 1/(H_total · target)` over duration `T`:

```
expected_unique_evaluations = H_unique · T
λ  (expected accepted blocks) = p · H_unique · T = T / (target · N)
P(accepted_blocks = 0) = exp(−λ)
```

### B1 zero-block table (N = 100…500, homogeneous, T = 10 000 s, target = 600 s)

| N | H_unique (H/s) | λ = E[blocks] | P0 = exp(−λ) | risk | empirical zero-frac (12 seeds) |
|---|----------------|---------------|--------------|------|-------------------------------|
| 100 | 1.41e12 | 0.1667 | 0.8465 | high | 0.667 |
| 200 | 7.05e11 | 0.0833 | 0.9200 | very_high | 0.750 |
| 300 | 4.70e11 | 0.0556 | 0.9460 | very_high | 0.750 |
| 400 | 3.53e11 | 0.0417 | 0.9592 | very_high | 0.833 |
| 500 | 2.82e11 | 0.0333 | 0.9672 | very_high | 0.833 |

Both the closed form and the seeded engine are **majority-zero and monotone
increasing in N**. The empirical frequency sits slightly below `exp(−λ)` (gap ≤
0.20, within the pre-registered 0.25 band) because the engine draws a **finite**
set of ≈μ solutions per generation (first solution ≈ S/(μ+1)) rather than a
memoryless Bernoulli stream (mean 1/p = S/μ); the finite model finds a reachable
solution somewhat more often. This is a documented, bounded modelling difference,
not a discrepancy in either method.

B1 is retained as an **intentionally constrained common-template worst-case**; the
10 000 s horizon is **not** changed to manufacture blocks.

## 3. Zero-block / zero-denominator NA policy (pre-registered)

When `accepted_blocks = 0`:

| Metric | Value | Reason code |
|--------|-------|-------------|
| `energy_per_accepted_block_kwh` | `null` | `no_accepted_blocks` |
| `effective_block_interval_s` | `null` | `no_accepted_blocks` |
| `confirmation_time_proxy_s` | `null` | `no_accepted_blocks` |
| `legitimate_stale_rate` | `null` | `no_valid_proposals` |
| `energy_per_transaction_kwh` | `null` (always; tx not modelled) | `no_committed_transactions` |
| `throughput_blocks_per_s` | `0.0` (numerator genuinely zero — **not** NA) | — |
| `total_energy_kwh` | real value (energy still consumed) | — |

Rules:
- NA is **JSON null**, never 0, ∞, or a large constant. Every NA carries a
  companion `*_na_reason` from the declared vocabulary (`schemas.NA_REASONS`).
- Zero-block runs are **not excluded** from accepted-block-count, zero-block
  probability, block-production, or failure-to-progress summaries.
- Per-block/per-transaction summaries must report the count of **defined** vs
  **undefined** runs and the reason. Two distinct estimands are reported and never
  conflated: **ratio of totals** (Σ energy / Σ blocks across runs) and the
  **conditional mean** (mean per-run energy-per-block over runs with ≥1 block).
- B1 per-block metrics are **not** compared to other scenarios as if the
  missingness were random.

## 4. Matrix field

Every matrix row carries `expected_zero_block_probability` and
`zero_block_risk_category` (`low` / `high` / `very_high` / `unmodeled`). B1 rows are
`high` (N=100) or `very_high` (N≥200); B2 is `unmodeled` (partial overlap has no
closed form); full-parallel scenarios are `low` (P0 ≈ 5.8e-8).
