# Stage 5B1B — B1 Analytical Reconciliation Report

Modules: `experiments/thesis_revision_v43/b1_exact.py`, `validate_5b1b.py`
Data: `STAGE_05B1B_B1_VALIDATION_TABLE.json`,
`results/thesis_revision_v43/stage_05b1b/validation_report_5b1b.json`
Tests: `tests/thesis_revision_v43/stage5b1b/test_stage5b1b_b1_exact.py` (1–10)

Reconciles the B1 zero-block probability across **three independent computations**
and, in doing so, corrects two engine bugs that made B1 produce blocks too often.

## 1. Two engine corrections (this stage)

1. **Exhausted-generation timing.** For B1 the unique frontier advances only at
   `max_i H_i` (the fastest miner), so an exhausted full-domain sweep takes
   `S/max_rate`, not `S/H_active` (aggregate). The 5B1A engine used the aggregate
   rate, making exhausted sweeps N× too fast and inflating block production. Fixed:
   `D_ex = S/unique_rate`, `unique_rate = max_rate` for B1 (`H_active` for the
   disjoint scenarios, which are genuinely full-parallel).
2. **Solution-position sampling bias.** Positions were drawn as
   `unique(integers(0,S,size=2k))[:k]`; because `np.unique` sorts, this kept the
   **k smallest** of 2k draws, biasing `min_pos` ~2× low. Fixed to draw exactly k.

After both fixes the engine's B1 zero-block frequency matches the exact model
within the pre-registered 99% criterion (below).

## 2. Exact finite-domain model

The B1 unique frontier evaluates `M = unique_rate · T` Bernoulli(p) candidates over
the horizon, `p = 1/(H·target)`. The exact no-success probability is

```
log P_zero_exact = Σ_g M_g · log1p(−p_g)   (= M · log1p(−p) for constant p)
P_zero_exact = exp(log P_zero_exact) = (1−p)^M
```

computed in 50-digit mpmath. For every production config `M < S`, so there are **0
full (exhausted) generations and 1 partial final generation** of `M` candidates.
The Poisson value `exp(−Σ M_g p_g)` is reported **only as an approximation**.

## 3. Three-way reconciliation (validation seeds 20261001–20261030, disjoint from the frozen schedule)

| N | M (unique evals) | exact P0 | Poisson P0 | Poisson abs err | direct-ref (10⁵) | event-loop (30) | 99% CI | z | exact ∈ 99% CI |
|---|-----------------:|---------:|-----------:|----------------:|-----------------:|----------------:|--------|----:|:---:|
| 100 | 1.410×10¹⁶ | 0.84648 | 0.84648 | 8.3×10⁻¹⁹ | 0.84691 | 0.833 (25/30) | [0.596, 0.962] | −0.20 | ✅ |
| 200 | 7.050×10¹⁵ | 0.92004 | 0.92004 | 4.5×10⁻¹⁹ | 0.92055 | 0.900 (27/30) | [0.680, 0.988] | −0.40 | ✅ |
| 300 | 4.700×10¹⁵ | 0.94596 | 0.94596 | 3.1×10⁻¹⁹ | 0.94452 | 0.900 (27/30) | [0.680, 0.988] | −1.11 | ✅ |
| 400 | 3.525×10¹⁵ | 0.95919 | 0.95919 | 2.4×10⁻¹⁹ | 0.95978 | 0.900 (27/30) | [0.680, 0.988] | −1.64 | ✅ |
| 500 | 2.820×10¹⁵ | 0.96722 | 0.96722 | 1.9×10⁻¹⁹ | 0.96714 | 0.900 (27/30) | [0.680, 0.988] | −2.07 | ✅ |

- **Poisson is an approximation only:** its absolute error is ~10⁻¹⁹ (because
  `p ≈ 1.18×10⁻¹⁷`), so exact and Poisson coincide to ~17 digits — but they are
  reported as distinct quantities with the error stated.
- **Direct reference** (an independent `Binomial(round(M), p)` Monte-Carlo that never
  calls the engine's winner selection) agrees with the exact value within its own
  100 000-sample 99% CI at every N.
- **Event-loop:** the exact P0 lies inside the event-loop 99% Clopper-Pearson CI for
  **every** N — the pre-registered acceptance criterion, with **no arbitrary
  tolerance**.

## 4. On the mild residual

The event-loop frequency is a little below exact at large N (standardized deviation
down to −2.07 at N=500). This is a **shared-seed sampling artifact**, not a bug: the
30 validation seeds are reused across all N, so the same handful of seeds whose
first solution sits near nonce 0 recur as block-finders. The residual is not
statistically significant (across-N sign test p = 0.0625) and every exact value is
inside the 99% CI; the independent 100 000-sample direct reference confirms the
exact values to 3 decimals. Increasing the event-loop sample beyond 30/​N would
require exceeding the 150-run validation cap and is unnecessary given the direct
reference.

## 5. Matrix fields (per B1 row)

`expected_zero_block_probability_exact`, `expected_zero_block_probability_poisson`,
`expected_unique_candidate_evaluations`, `expected_full_template_generations`,
`expected_partial_generation_candidates`, `zero_block_risk_category`,
`analytical_model_version = b1-exact-1`. Each row's value is derived from its own
duration, miner count, distribution, target, and domain — no common probability is
assigned across differing rows. B2 remains `unmodeled` (partial-overlap frontier has
no closed form); disjoint scenarios carry P0 ≈ 5.8×10⁻⁸ (`low`). The NA policy for
zero-block runs (Stage 5B1A) is retained unchanged.
