# STAGE 05A — Stage-4 Documentary Correction Note

Corrects two reporting issues in `STAGE_04_FINDER_EQUIVALENCE_AUDIT.md` **without
changing the underlying experimental evidence**. Git history is not amended;
this note is committed within Stage 5A. (Also satisfies the section-1
requirement for a Stage-4 correction note.)

---

## A. Le Cam numerical inequality (corrected)

**Problem.** The Stage-4 report displayed, for the thesis regime,
`|ΔP₀| = 2.78e-17 ≤ Le Cam 2.36e-17`, which is numerically **false**
(2.78e-17 > 2.36e-17).

**Cause.** `2.78e-17` was **float64 rounding noise**, not the true difference.
`P(K=0)` for both Binomial and Poisson is ≈ 0.13533528323661269; the two values
agree to ~16 significant figures, so their float64 difference is dominated by
the machine-epsilon floor `eps·P₀ ≈ 2⁻⁵² × 0.1353 ≈ 3.0e-17`. The true
difference is far smaller and cannot be resolved in double precision.

**Correct computation (mpmath, 80 decimal digits).**

Thesis regime: `S = 1.692e17`, `p = 1.182e-17`, `μ = S·p = 2.0`.

| quantity | value |
|---|---|
| `P(K=0)` Binomial `(1−p)^S` | `0.135335283236612690294291655296` |
| `P(K=0)` Poisson `e^{−μ}` | `0.135335283236612691893999494972` |
| **true `\|ΔP₀\|`** | **`1.59971e-18`** |
| leading-order `e^{−μ}·μp/2` | `1.59971e-18` (matches) |
| **Le Cam bound** `Σ pᵢ² = S·p² = μ·p` | **`2.36407e-17`** |
| `\|ΔP₀\| ≤ Le Cam` | **TRUE** (`1.60e-18 ≤ 2.36e-17`) |
| float64 noise floor `eps·P₀` | `≈ 3.0e-17` (explains the spurious 2.78e-17) |

**Bound convention.** Le Cam's theorem: for independent Bernoulli(pᵢ),
`d_TV(Σ Bernoulli(pᵢ), Poisson(Σ pᵢ)) ≤ Σ pᵢ²`. Homogeneously `Σ pᵢ² = S·p² = μ·p`.
Total-variation distance upper-bounds `|ΔP₀|` (since `|P_bin(A) − P_pois(A)| ≤
d_TV` for any event A), so the correct chain is
`|ΔP₀| ≤ d_TV ≤ S·p²`. With the **true** value `1.60e-18`, the inequality holds
with ~15× margin. **Corrected statement:** *"The exact Binomial→Poisson
difference at the thesis regime is 1.60e-18, which is below the Le Cam TV bound
2.36e-17; the earlier 2.78e-17 was float64 rounding noise and is retracted."*

Machine-readable values are in
`results/thesis_revision_v43/stage_05a/raw/lecam_recomputation.json`.

### Other regimes (unchanged, recomputed for completeness)
| regime | μ | true `\|ΔP₀\|` | Le Cam `S·p²` | holds? |
|---|---|---|---|---|
| S = 20 | 2 | 1.376e-2 | 2.0e-1 | yes |
| S = 1e5 | 2 | 5.41e-5 | 8.0e-4 | yes |
| thesis | 2 | 1.60e-18 | 2.36e-17 | yes |

These were computed in float64 in Stage 4 and are unaffected (their differences
are well above the float64 floor).

---

## B. KS interpretation (corrected + effect-distance added)

**Problem.** Stage 4 wrote that the discovery-time distributions are
"indistinguishable". Failure to reject equality is **not** proof of equivalence.

**Corrected wording.** *"No statistically detectable distributional difference
was observed under the specified sample size, test, and tolerance."*

**Reported statistics (discovery time, μ = 2, S = 5000):**

| quantity | value |
|---|---|
| KS statistic D | 0.00817 |
| p-value | 0.1975 |
| n (reference / finder) | 34 557 / 34 609 |
| seeds (ref / finder) | 7 / 8 |
| bootstrap mean D | 0.01005 |
| **bootstrap 95% CI for D** | **[0.00522, 0.01618]** (400 resamples, seed 20260729) |
| declared practical-equivalence tolerance (max CDF distance) | 0.02 |
| CI upper bound < tolerance? | **yes** (0.0162 < 0.02) |
| mean first-success index rel. difference | 0.55 % |

**Equivalence conclusion (proper form):** the bootstrap 95% confidence interval
for the distributional distance D lies **entirely below** the pre-declared
practical-equivalence tolerance of 0.02, so the finder discovery-time
distribution is **practically equivalent** to the direct Bernoulli first-success
distribution at this sample size and tolerance. This is a bounded-distance
equivalence statement, not a bare "fail-to-reject".

---

## C. Scope of correction
Only the *reporting/interpretation* changed. The audit's evidence, the exact
Binomial sampler, and all Stage-4 code/tests are unchanged (126 tests still
pass). No thesis file was touched.
