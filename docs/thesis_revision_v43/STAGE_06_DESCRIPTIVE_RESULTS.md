# Stage 6 — Descriptive Results

Full machine-readable descriptives (n, n_defined, mean, SD, median, IQR, min, max, 95%
bootstrap CI, zero and NA counts) for every scientific group × outcome are in
`results/thesis_revision_v43/stage_06/tables/descriptive_long.csv` (1,197 rows). Analysis
population and NA accounting: `table01_population_na.csv`. All 1,890 runs are represented;
B3/C1 is one physical dataset.

## 1. Population and NA (per scenario)

| Scenario | Physical runs | Zero-block | Block-interval defined |
|----------|--------------:|-----------:|-----------------------:|
| B0 | 150 | 0 | 150 |
| B1 | 150 | ~148 | ~2 |
| B2 | 150 | ~ mixed | defined where blocks>0 |
| B3;C1 | 870 | small | mostly defined |
| C2 | 570 | small | mostly defined |

(Exact counts in `table01_population_na.csv` / `table11_zero_block.csv`.) B1 is
near-certainly zero-block — under a common immutable template every active miner
redundantly evaluates the same candidates, so distinct coverage and accepted blocks
collapse. Zero-block runs are retained; block-normalised metrics stay NA for them.

## 2. Energy (unconditional)

For all continuous full-participation runs, `total_energy_kwh` is exactly the accounting
anchor **8.420833333 kWh** (see A1). Energy departs from the anchor only when active
power-time is removed: **inactive miners** (H6: 8.42 → 7.16 → 5.89 kWh as inactive
fraction rises 0.05→0.30) and **C2 idle under heterogeneity** (H5: down to ~5.0/4.6 kWh
for equal allocation).

## 3. Candidate redundancy (`table08_candidate_redundancy.csv`)

Duplicate-evaluation rate by scenario (mean over 150 runs each): B0 = 0.000, B1 ≈ 0.995,
B2 ≈ 0.600, B3/C1 = 0.000. B1's rate is deterministically `(N−1)/N` per miner count; B2's
varies by seed (0.27–0.88); B3/C1 is exactly zero (disjoint ranges). This holds **only**
under the idealized immutable-common-template / disjoint-allocation assumptions.

## 4. Coordination, exhaustion, refreshes

`exhausted_rounds` and `coord_template_refresh_count` grow as μ falls (H8) and, more
mildly, with inactive fraction (H6). `completion_time_std_s` is exactly 0 under
homogeneous equal ranges and large (~770–800 s) under heterogeneity with equal ranges
(H4/H5).

## 5. Distribution shape

Most block-normalised and dispersion metrics are bounded and skewed; the descriptive
table foregrounds median and IQR alongside mean/SD, and confirmatory inference uses
distribution-free paired methods (permutation, bootstrap, Wilcoxon). No intermediate
rounding is applied; publication tables use consistent final rounding.
