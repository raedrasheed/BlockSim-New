# Stage 6 — Preregistration Map

Maps every preregistered hypothesis / research question to its exact analysis. Built
**before** running any confirmatory analysis. Sources: `STAGE_05A_PREREGISTRATION.md`
(frozen), `STAGE_05B1_PREREGISTRATION_AMENDMENT.md` (H2 → Accounting Invariant A1),
`STAGE_05B1G_PREREGISTRATION_AMENDMENT.md` (H7 → secondary diagnostic). Hypothesis→run
membership is taken from the frozen matrix columns `hypothesis_id` / `matrix_class`
(`STAGE_05B1G1_FINAL_MATRIX.csv`, SHA-256 `9cb7297e…`).

## 0. Status after amendments

| Original | Status used in Stage 6 |
|----------|------------------------|
| H1 | **Confirmatory** |
| H2 | **Accounting Invariant A1** (deterministic identity; verified, not tested) |
| H3, H4, H5, H6, H8 | **Confirmatory** |
| H7 | **Secondary diagnostic sensitivity** (single-height stale-race; amended 5B1G) |

Statistical unit (all analyses): **one physical run for one frozen master seed**. B3 and
C1 are one physical dataset (`interpretation_labels = "B3;C1"`), never counted twice.
Pairing: seed-matched on `(miner_count, seed)`. Confidence 95%; α = 0.05; multiplicity =
Holm within each confirmatory hypothesis family; bootstrap = 10,000 (seed 6060601);
permutation = 10,000 (seed 6060602).

---

## A1 — Accounting invariant (former H2)

- **Wording (amended):** for all continuous full-participation scenarios (B0, B1, B2,
  B3/C1), total energy equals `P_total·T` exactly, for every miner count and search
  discipline.
- **Status:** deterministic accounting identity — **verified, not tested**.
- **Independent variable / levels:** scenario {B0,B1,B2,B3/C1} × miner_count {100…500};
  invariance asserted across both.
- **Outcome / canonical field:** `total_energy_kwh`.
- **Statistical unit:** run·seed. **Inclusion:** continuous scenarios, `inactive_fraction=0`,
  `idle_policy=off` (1140 runs). **NA rule:** none (always defined).
- **"Test":** max relative deviation from anchor `8.420833333` kWh vs tolerance 1e-6.
- **Effect size / CI:** deviation magnitude (kWh); no inferential CI (identity).
- **Multiplicity family:** none. **Decision rule:** identity holds iff all
  `|Δ|/anchor < 1e-6`.
- **Matrix groups:** CORE (`H1;A1`) + all continuous full-participation runs.
- **Output:** `table07_energy_decomposition.csv`; `fig02_a1_energy_invariant`.

## H1 — Duplicate coverage (CONFIRMATORY)

- **Wording:** under one common immutable template, B1 has a higher duplicate
  candidate-header evaluation rate than B2 and B3/C1. Direction **B1 > B2 > B3/C1**.
- **IV / levels:** scenario {B1, B2, B3/C1} (B0 = reference/anchor, not in the ordering).
- **Outcome / canonical field:** primary `duplicate_evaluation_rate`; secondary
  `distinct_candidate_identities`, `energy_per_accepted_block_kwh`, exhaustion.
- **Unit:** run·seed. **Pairing:** seed-matched `(miner_count, seed)`. **Clustering
  (Stage 6A §6):** because the 30 master seeds recur across the five miner counts, the 150
  physical differences per contrast are aggregated (direction-preserving mean) to **30
  independent seed-cluster values**, and uncertainty is computed from those 30 clusters —
  never from 150 as independent replications; N-specific analyses (30 pairs each) are
  retained as robustness. **Inclusion:** `H1;A1` CORE (600 runs). **NA rule:** duplicate
  rate always defined; `energy_per_accepted_block_kwh` NA when zero-block (B1 near-always
  zero-block).
- **Test:** paired permutation (two-sided) on differences; **effect size** paired mean
  difference + Hodges-Lehmann; **CI** seed-pair bootstrap 95%; Wilcoxon signed-rank
  sensitivity.
- **Multiplicity family:** H1 = {B1>B2, B2>B3/C1, B1>B3/C1}, Holm. **Decision rule:**
  direction met and Holm-adjusted p < 0.05 with CI excluding 0 (B1>B3/C1 is
  design-deterministic and reported as such).
- **Matrix groups:** `matrix_class=CORE`, scenarios B0/B1/B2/B3;C1.
- **Output:** `table08_candidate_redundancy.csv`, `confirmatory_effects.csv`;
  `fig01_h1_duplicate_rate`.

## H3 — C2 idle mechanism (CONFIRMATORY)

- **Wording:** C2 energy reduction, when observed, decomposes as active-time reduction +
  explicit idle-power + explicit coordination. Identity
  `saving = Σ idle_time·(P_active − P_idle)`.
- **IV / levels:** `idle_power_ratio` {0,0.05,0.1,0.2,0.3}, miner_count {100,500};
  scenario C2.
- **Outcome / canonical fields:** `active_energy_kwh`, `idle_energy_kwh`,
  `coordination_energy_kwh`, `total_energy_kwh`, `total_idle_time_s`.
- **Unit:** run·seed. **Inclusion:** C2 (`H3`, `H3;H4`, and the idle-bearing `H5` C2).
  **NA rule:** none for energy.
- **"Test":** decomposition identity (active+idle+coord = total, exact) + magnitude of
  saving vs anchor with seed bootstrap CI where idle triggers.
- **Effect size:** absolute kWh saving, relative %, active/idle split.
- **Multiplicity family:** n/a (identity). **Decision rule:** identity residual = 0 and
  saving attributable to idle time.
- **Matrix groups:** `CORE_C2`, `SENS_IDLE`, C2 portion of `SENS_HETERO`.
- **Output:** `table07_energy_decomposition.csv`; `fig05_h3_energy_decomposition`.

## H4 — Homogeneous completion symmetry (CONFIRMATORY)

- **Wording:** with homogeneous rates and equal ranges, range-completion times are ≈
  equal → post-range idle opportunity ≈ 0.
- **IV / levels:** homogeneous rates + equal allocation (fixed); miner_count {100…500}.
- **Outcome / canonical fields:** `completion_time_std_s` (dispersion),
  `total_idle_time_s`.
- **Unit:** run·seed. **Inclusion:** homogeneous+equal runs (incl. C2 CORE `H3;H4`).
  **NA rule:** none.
- **"Test":** equivalence-to-zero — report max dispersion and max idle.
- **Effect size:** dispersion / idle magnitude (seconds).
- **Multiplicity family:** none. **Decision rule:** dispersion ≈ 0 and idle ≈ 0.
- **Matrix groups:** `CORE_C2` (`H3;H4`) + homogeneous-equal CORE.
- **Output:** `descriptive_long.csv`; `fig03` (context).

## H5 — Heterogeneity & allocation (CONFIRMATORY)

- **Wording:** with heterogeneous miners, equal ranges let fast miners idle;
  hash-rate-weighted ranges reduce completion imbalance and may reduce/eliminate that
  idle. **Trade-off, not guaranteed superiority.**
- **IV / levels:** `allocation_policy` {equal, weighted}; scenario {B3/C1, C2};
  miner_count {100,500}; hash_rate_distribution = heterogeneous_moderate.
- **Outcome / canonical fields:** `total_idle_time_s`, `completion_time_std_s`,
  `total_energy_kwh`.
- **Unit:** run·seed. **Pairing:** `(miner_count, seed)`, weighted vs equal.
  **Inclusion:** `SENS_HETERO` (`H5`, 240 runs). **NA rule:** none.
- **Test:** paired permutation + bootstrap CI + Wilcoxon; **effect size** paired mean /
  HL difference.
- **Multiplicity family:** H5 (Holm across its contrasts). **Decision rule:** weighted
  reduces dispersion/idle (direction, Holm p < 0.05). Energy has **no preregistered
  direction** (trade-off), reported descriptively.
- **Matrix groups:** `SENS_HETERO`.
- **Output:** `table09_allocation_policy.csv`; `fig03`, `fig04`.

## H6 — Inactive miners (CONFIRMATORY)

- **Wording:** ↑ inactive fraction → ↑ unsearched domain, ↑ exhaustion/refresh, ↑ block
  latency; **may** ↓ raw active energy while ↑ energy per accepted block.
- **IV / levels:** `inactive_fraction` {0 (baseline), 0.05, 0.15, 0.30}; miner_count
  {100,500}; scenario B3/C1 homogeneous equal.
- **Outcome / canonical fields:** `inactive_domain` (unsearched), `exhausted_rounds`,
  `effective_block_interval_s`, `accepted_blocks`, `total_energy_kwh`,
  `energy_per_accepted_block_kwh`.
- **Unit:** run·seed. **Pairing:** vs `inactive=0` baseline (H1;A1 B3/C1 at N∈{100,500}).
  **Inclusion:** `SENS_INACTIVE` (180) + baseline. **NA rule:**
  `energy_per_accepted_block_kwh`/`effective_block_interval_s` NA if zero-block (none in
  this family).
- **Test:** paired permutation + bootstrap CI + Wilcoxon.
- **Multiplicity family:** H6 (Holm). **Decision rule:** each directional sub-claim met +
  Holm p < 0.05 + CI excludes 0. The "↑ energy per accepted block" sub-claim carries the
  preregistered hedge "may".
- **Matrix groups:** `SENS_INACTIVE`.
- **Output:** `table10_inactive_miners.csv`; `fig06_h6_inactive`.

## H7 — Propagation delay (SECONDARY DIAGNOSTIC SENSITIVITY, amended 5B1G)

- **Wording (amended):** within the single-height stale-race diagnostic, ↑ delay ⇒ ↑
  single-height stale rate. Descriptive sensitivity of a diagnostic, **not** a
  confirmatory / fork-rate / security claim.
- **IV / levels:** `propagation_delay_mean_s` {0, 0.42 (baseline), 5, 30, 60};
  miner_count {100,500}; scenario B3/C1 homogeneous equal.
- **Outcome / canonical fields:** `single_height_stales_per_accepted_block`,
  `single_height_stale_fraction_of_valid_proposals`, `single_height_stale_block_count`.
- **Unit:** run·seed. **Inclusion:** `SENS_DELAY` (240) + baseline. **NA rule:** rate NA
  if zero-block (none here). For zero-observation levels, exact one-sided binomial /
  rule-of-three with denominator = accepted blocks.
- **Test:** descriptive sensitivity only (means, medians, Wilson/rule-of-three).
- **Multiplicity family:** none (secondary). **Decision rule:** none confirmatory; also
  verify delay-only variation leaves primary outcomes unchanged.
- **Matrix groups:** `SENS_DELAY`.
- **Output:** `table12_secondary_stale.csv`; `fig08_h7_delay_singleheight`.

## H8 — Finite-domain μ (CONFIRMATORY)

- **Wording:** ↓ μ → ↑ exhaustion probability and template-refresh frequency (and
  effective block interval).
- **IV / levels:** `mu` {0.5, 1.0, 2.0 (baseline)}; miner_count {100,500}; scenario B3/C1
  homogeneous equal.
- **Outcome / canonical fields:** `exhausted_rounds`, `coord_template_refresh_count`,
  `template_generations`, `effective_block_interval_s`.
- **Unit:** run·seed. **Pairing:** vs `mu=2.0` baseline (H1;A1 B3/C1 at N∈{100,500}).
  **Inclusion:** `SENS_MU` (120) + baseline. **NA rule:** interval NA if zero-block
  (none here).
- **Test:** paired permutation + bootstrap CI + Wilcoxon.
- **Multiplicity family:** H8 (Holm). **Decision rule:** direction met + Holm p < 0.05 +
  CI excludes 0.
- **Matrix groups:** `SENS_MU`.
- **Output:** `descriptive_long.csv`, `confirmatory_effects.csv`; `fig07_h8_mu`.

## H5x — High-heterogeneity extension (EXPLORATORY, not preregistered)

- `matrix_class=EXPLORATORY` (60 runs, hetero_high). Descriptive only; labelled
  **EXPLORATORY — NOT PREREGISTERED FOR CONFIRMATORY INFERENCE**. `fig10_h5x_exploratory`.

---

## Conflicts / ambiguities

- The preregistration lists "legitimate stale rate" and "effective block interval" among
  primary outcomes; the 5B1G amendment moved the stale rate to a **secondary
  single-height diagnostic** and renamed it `single_height_stales_per_accepted_block`.
  Stage 6 follows the amendment (H7 secondary). No favourable interpretation was silently
  chosen.
- H2's original "equivalence within tolerance" test is replaced by A1 identity
  verification per the 5B1 amendment.
- No hypothesis was strengthened or invented. Where the preregistration hedges ("may ↑
  energy per accepted block", H6), that hedge is preserved and the sub-claim is judged on
  its own evidence.
