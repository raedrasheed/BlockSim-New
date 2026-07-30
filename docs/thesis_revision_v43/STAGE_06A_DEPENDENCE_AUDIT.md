# Stage 6A — H1 Dependence Audit (clustering across miner counts)

Corrects the H1 inference (Stage 6A §6). The original H1 analysis pooled 150 matched
differences (5 miner-count levels × 30 seeds) and treated them as independent. They are
**not** independent: the **same 30 master seeds recur** across all five miner-count levels,
so the five differences that share a seed are correlated.

## 1. Corrected cluster-aware analysis

1. For each master seed, compute the scenario difference at every miner-count level.
2. Aggregate the five per-N differences within that seed by their **direction-preserving
   mean** → one value per seed.
3. This yields **30 independent seed-cluster values** per contrast.
4. Uncertainty is computed on the 30 clusters: **seed-cluster bootstrap 95% CI**,
   **seed-cluster sign-flip permutation test**, and **Hodges-Lehmann** cluster shift.
5. **N-specific analyses** (30 matched pairs at each N) are retained as robustness.

Reported for every contrast: **physical run pairs = 150** and **independent seed clusters
for uncertainty = 30** — the 150 are never presented as 150 independent replications.

## 2. Corrected results

| Contrast | clusters | mean Δ (rate) | HL Δ | cluster boot 95% CI | Holm p | disposition |
|----------|---------:|--------------:|-----:|---------------------|-------:|-------------|
| B1 − B2 | 30 | +0.3954 | +0.390 | [0.355, 0.437] | 2.0e-4 | SUPPORTED |
| B2 − B3/C1 | 30 | +0.6000 | +0.606 | [0.558, 0.640] | 2.0e-4 | SUPPORTED |
| B1 − B3/C1 | 30 | +0.9954 | +0.995 | [0.995, 0.995] | — | SUPPORTED_BY_DESIGN (deterministic) |

Holm is applied to the two stochastic cluster-level contrasts. N-specific robustness
(per `confirmatory_effects.csv` → `n_specific_robustness`) shows the same direction at
every N (B1−B2 ≈ 0.39–0.42; B2−B3/C1 ≈ 0.58–0.61; B1−B3/C1 ≈ 0.99–0.998).

## 3. Effect of the correction

The cluster CIs are **appropriately wider** than the earlier pooled intervals (e.g. B1−B2
widened from ≈ [0.374, 0.416] to [0.355, 0.437]), reflecting the 30 genuinely independent
units rather than 150. **The H1 conclusion is unchanged:** the ordering B1 > B2 > B3/C1
holds, both stochastic contrasts remain Holm-significant with CIs excluding 0, and the
B1 > B3/C1 contrast is a design identity. This change is reported honestly per §6; it did
not alter the disposition.
