# Stage 6 — Analysis Plan

Preregistered statistical analysis of the frozen 1,890-run matrix. This plan and the
test-selection rules were fixed **before** inspecting p-values.

## 1. Sources and integrity

- Scientific source: freeze-6 `45361674…`; engine/schema `5b1g.2`.
- Authoritative results: results-3 `278af17…` (byte-identical scientific data to
  results-1 `d2ef6012…`); bulk data on `thesis-v43-stage5b2-data-1` `b44975d…`.
- Matrix SHA-256 `9cb7297e…`. Input-integrity gate: 12/12 PASS
  (`STAGE_06_INTEGRITY_GATE.json`). No scientific result, seed, engine, or thesis file is
  modified in Stage 6.

## 2. Statistical unit and dependence (§6)

- Unit = **one physical run for one frozen master seed** (1,890 units, 63 groups × 30
  seeds).
- Nested observations (miners, template generations, blocks, nonce positions, stale
  records, delivery records) are **not** independent replications.
- B3 and C1 are one physical dataset (`interpretation_labels="B3;C1"`, 870 runs); never
  counted twice, never compared as independent samples.
- Paired analyses use seed-matched pairing on `(miner_count, seed)`.

## 3. Outcome policy (§7, §8)

- Zero-block runs (142) are retained. Block-normalised metrics
  (`effective_block_interval_s`, `energy_per_accepted_block_kwh`,
  `confirmation_time_proxy_s`, `single_height_stales_per_accepted_block`) stay **NA** when
  `accepted_blocks=0` — never imputed. Each metric reports total / defined / undefined
  counts and the reason (`table01_population_na.csv`).
- Unconditional outcomes (`accepted_blocks`, `total_energy_kwh`, zero-block indicator,
  `exhausted_rounds`, candidate counts) use all 30 seeds.
- Descriptives per group×outcome: n, n_defined, mean, SD, median, IQR, min, max, 95% CI,
  zero and NA counts (`descriptive_long.csv`). Bounded/skewed metrics foreground
  median/IQR and distribution-free intervals.

## 4. Test-selection rule (fixed in advance, §9)

For every seed-matched confirmatory contrast, in order: (1) paired effect estimate
(mean difference + Hodges-Lehmann); (2) seed-pair bootstrap 95% CI (10,000 resamples,
seed 6060601); (3) two-sided paired sign-flip permutation test (10,000, seed 6060602);
(4) Wilcoxon signed-rank as a non-parametric sensitivity check. A difference vector that
is constant (design-deterministic) is flagged and reported as an identity, not an
empirical test. No test is chosen after seeing significance.

## 5. Effect sizes (§10)

Every inferential comparison reports the effect in scientific units first (paired mean
difference and Hodges-Lehmann shift), a standardized paired effect (dz), and a bootstrap
CI. Relative change is reported only where the reference mean is non-zero. Significance is
never stated without a magnitude.

## 6. Multiplicity (§11)

Holm step-down within each confirmatory hypothesis family (H1, H5, H6, H8). Deterministic
design identities are excluded from the p-value families. Raw and Holm-adjusted p, family
definition, family size, and the α=0.05 decision are reported
(`confirmatory_effects.csv`, `table06_robustness.csv`). Secondary (H7) and exploratory
(H5x) analyses are never mixed into confirmatory correction families.

## 7. Required analyses (§12) mapped to frozen ids

A energy accounting → **A1** + **H3** + **H6**; B candidate redundancy → **H1**;
C allocation policy → **H5**; D miner count → covariate across families (no claim that
fixed-horizon energy scales with N at fixed aggregate hash/power); E inactive miners →
**H6**; F scenario comparisons → **H1/A1** (exact frozen definitions; no double count of
B3/C1); G propagation-delay sensitivity → **H7** secondary single-height diagnostic.

## 8. Reproducibility (§19)

All outputs come from committed scripts under `analysis/thesis_revision_v43/stage_06/`,
runnable as `python3 s6_run_all.py`. Environment, input checksums, script checksums,
RNG seeds, replicate counts, α, and the Holm procedure are recorded in
`STAGE_06_ENVIRONMENT.json` and `STAGE_06_ANALYSIS_MANIFEST.json`; output checksums in
`STAGE_06_CHECKSUM_MANIFEST.sha256`.

## 9. Deliverables

Reports listed in approval §20; tables in `results/…/stage_06/tables/`; figures (PDF +
PNG + plotting data) in `results/…/stage_06/figures/` and `…/plot_data/`; models and
diagnostics under `…/models/` and `…/diagnostics/`. No revised thesis DOCX is produced in
Stage 6.
