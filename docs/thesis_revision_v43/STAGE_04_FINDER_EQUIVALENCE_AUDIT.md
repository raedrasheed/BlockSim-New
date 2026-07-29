# STAGE 04 — Finder-Model Equivalence Audit (Objective A, GATE)

**Verdict: PASS.** The finder-based finite-domain abstraction is equivalent,
within explicitly bounded error, to a direct finite-domain Bernoulli hashing
process. The simulator now uses **exact per-range Binomial** sampling by default
(`Models/PoCol/round_state.draw_round_solutions_exact`, `Consensus.solution_sampler
= "binomial"`); Poisson is retained only as a labelled diagnostic.

Code: `analysis/thesis_revision_v43/finder_equivalence.py`. Data (read-only):
`results/thesis_revision_v43/stage_04/raw/finder_equivalence.csv`. Tests:
`tests/thesis_revision_v43/stage4/test_stage4_finder_equivalence.py` (1–10).
Seed 20260729, 200 000 trials per estimator unless noted.

---

## 1. Solution-count distribution across μ regimes

For each μ ∈ {0.1, 0.5, 1, 2, 5} (domain S = 5 000, p = μ/S), three samplers —
**direct Bernoulli** (S iid coin flips, chunked), **exact Binomial** (numpy),
and **Poisson** — were compared to the analytical reference. Every estimator's
P(K=0) lay within 5 standard errors of its analytical value, and the sample mean
matched μ. This confirms numpy's Binomial reproduces the definitional Bernoulli
sum, and that the finder count is exactly Binomial.

## 2. Binomial → Poisson approximation error (Le Cam)

Le Cam's theorem bounds the total-variation distance
`d_TV(Binomial(n,p), Poisson(np)) ≤ Σ pᵢ² = S·p²` (homogeneous). Measured
`|P(K=0)_binom − P(K=0)_pois|` against this bound:

| regime | μ | \|ΔP₀\| | Le Cam bound S·p² |
|---|---|---|---|
| small S = 20 | 2 | **1.38e-2** | 2.00e-1 |
| S = 1e5 | 2 | 5.41e-5 | 8.00e-4 |
| **thesis (S = 1.69e17, p = 1.18e-17)** | 2 | **2.78e-17** | 2.36e-17 |

The Poisson error is **material at tiny S (≈1.4 %)** but **at the floating-point
floor (~1e-17) in the thesis regime**. Because the thesis domain is astronomically
large, Poisson and Binomial are indistinguishable there; nonetheless the
simulator uses **exact Binomial** so the model is exact in *all* regimes and no
approximation is relied upon. Poisson is **not** claimed to be exact.

## 3. Per-range assignment equivalence

`K = Σᵢ Kᵢ` where `Kᵢ ~ Binomial(Sᵢ, p)` independently — a standard identity
(sum of independent Binomials with common p is Binomial(ΣSᵢ, p)). Measured over
50 000 trials for n ∈ {2, 10, 100} ranges: per-range-sum mean and variance match
the global Binomial(S,p) mean and variance (|Δmean| < 0.05). The simulator's
per-range draw therefore respects each miner's own range size Sᵢ, not miner
identity (tests 9, 10, `test_heterogeneous_finder_assignment`).

## 4. Discovery-time (first-success index) equivalence

The finder discovery rule (place Kᵢ solutions at uniform positions, take the
minimum) reproduces the first-success index of a direct ordered Bernoulli search
(the min-position identity). Compared over 40 000 trials:

| μ | ref mean index (direct Bernoulli) | finder mean index | rel. error | KS stat | KS p-value |
|---|---|---|---|---|---|
| 0.5 | 2296.8 | 2310.0 | 0.57 % | 0.011 | 0.291 |
| 2.0 | 1719.7 | 1708.4 | 0.66 % | 0.007 | 0.364 |
| 5.0 | 965.6 | 968.2 | 0.27 % | 0.008 | 0.141 |

KS p-values > 0.14 → the discovery-time distributions are statistically
indistinguishable. Discovery time equals `(nonce_pos − range_start)/H_i` by
construction (test 8), and the earliest of multiple solutions in a range is
selected (tests 5, 6).

## 5. Handling of multiple solutions per range

`draw_round_solutions_exact` records `range_solution_count` (Kᵢ) but schedules
only the **earliest** discovery per miner (section 4.6). Additional same-range
solutions do not create extra events.

## 6. Conclusion

All four equivalence dimensions (count distribution, Poisson error bound,
per-range assignment, discovery time) pass within declared tolerances. **Final
quantitative claims may rely on the finder model**, which is now exact
(Binomial). The gate is satisfied.
