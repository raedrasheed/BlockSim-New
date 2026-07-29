# STAGE 04 — Correction Note (Le Cam inequality and KS interpretation)

Satisfies the Stage-5A section-1 requirement. This is the same correction filed
in `STAGE_05A_STAGE4_CORRECTION_NOTE.md` (deliverable #6); both filenames refer
to one correction. Git history is **not** amended; this note is committed within
Stage 5A. It corrects *reporting only* — the underlying Stage-4 evidence, the
exact Binomial sampler, and all code/tests are unchanged (126 tests still pass).
Machine-readable values: `results/thesis_revision_v43/stage_05a/raw/lecam_recomputation.json`.

---

## A. Le Cam numerical inequality (corrected)

The Stage-4 audit displayed, for the thesis regime, `|ΔP₀| = 2.78e-17 ≤ Le Cam
2.36e-17`, which is numerically **false**. The `2.78e-17` was **float64 rounding
noise** (both `P(K=0)` values ≈ 0.13533528323661269 agree to ~16 significant
figures; their double-precision difference is dominated by the eps floor
`eps·P₀ ≈ 3.0e-17`).

Recomputed at 80 decimal digits (mpmath):

| quantity | value |
|---|---|
| regime | thesis: `S = 1.692e17`, `p = 1.182033096926713948e-17`, `μ = S·p = 2.0` |
| `P(K=0)` Binomial `(1−p)^S` | `0.135335283236612690294291655296` |
| `P(K=0)` Poisson `e^{−μ}` | `0.135335283236612691893999494972` |
| **true `\|ΔP₀\|`** | **`1.5997e-18`** (= leading order `e^{−μ}·μp/2`) |
| **Le Cam bound** `Σ pᵢ² = S·p² = μ·p` | **`2.3641e-17`** |
| `\|ΔP₀\| ≤ Le Cam` | **TRUE** (`1.60e-18 ≤ 2.36e-17`, ~15× margin) |
| float64 noise floor `eps·P₀` | `≈ 3.0e-17` (source of the spurious 2.78e-17) |

**Bound convention.** Le Cam's theorem: for independent Bernoulli(pᵢ),
`d_TV(Σ Bernoulli(pᵢ), Poisson(Σ pᵢ)) ≤ Σ pᵢ²`; homogeneously `Σ pᵢ² = S·p² =
μ·p`. Total variation upper-bounds `|ΔP₀|` since `|P_bin(A) − P_pois(A)| ≤ d_TV`
for any event A, so `|ΔP₀| ≤ d_TV ≤ S·p²`. **Corrected statement:** the exact
thesis-regime difference is `1.60e-18`, below the Le Cam bound `2.36e-17`; the
earlier `2.78e-17` is float64 noise and is **retracted**.

Other regimes (float64, unaffected — differences above the floor): `S=20` →
`|ΔP₀|=1.376e-2 ≤ 2.0e-1`; `S=1e5` → `5.41e-5 ≤ 8.0e-4`.

## B. KS interpretation (corrected + effect distance)

**Corrected wording:** *"No statistically detectable distributional difference
was observed under the specified sample size, test, and tolerance."* Failure to
reject equality is not proof of equivalence.

Discovery time, μ=2, S=5000: **D = 0.00817, p = 0.1975**, n = 34 557 / 34 609,
seeds 7 / 8. Bootstrap (400 resamples, seed 20260729) 95% CI for D =
**[0.00522, 0.01618]**, which lies **below** the pre-declared practical-
equivalence tolerance **0.02** (max CDF distance). Mean first-success-index
relative difference 0.55%. **Equivalence conclusion:** the CI for the
distributional distance is entirely below the declared tolerance → the finder
discovery-time distribution is **practically equivalent** (bounded distance) to
the direct Bernoulli first-success distribution, not merely a fail-to-reject.
