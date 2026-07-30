# Stage 6 — Secondary Diagnostics (H7 single-height stale-race)

`H7` is a **secondary diagnostic sensitivity**, not a confirmatory result (amended in
`STAGE_05B1G_PREREGISTRATION_AMENDMENT.md`). It measures, for one accepted height in
isolation, which non-winning miners would have published a competing block before
receiving the winner. It has **no** fork resolution, no cross-height / chain-reorg
semantics, and its energy and evaluations are deliberately **not** integrated into the
primary metrics. Machine-readable: `diagnostics/h7_secondary.json`,
`tables/table12_secondary_stale.csv`; figure `fig08_h7_delay_singleheight`.

## 1. Interval framework (corrected, Stage 6A §5)

`single_height_stales_per_accepted_block` is a **count-rate** diagnostic: at one accepted
height, **several distinct non-winning miners** may each publish a stale, so the numerator
is a count of distinct stale producers, not a Bernoulli success. **No Wilson,
Clopper-Pearson, or binomial rule-of-three interval is applied to
`stale_block_count / accepted_blocks`.** Uncertainty comes from the **30 run-level values**
per (delay, miner-count) cell with a **seed/run-cluster bootstrap 95% CI** for the mean
count-rate. **N=100 and N=500 are kept separate.** A separate **binary** diagnostic uses
`heights_with_any_stale / accepted_heights` (probability that an accepted height has at
least one modeled stale producer), also run-cluster based.

## 1a. Delay sensitivity (count-rate; B3/C1 homogeneous equal; 30 runs per cell)

| delay (s) | N | mean stales/block | cluster boot 95% CI | any-stale-height fraction (mean) |
|-----------|--:|------------------:|---------------------|---------------------------------:|
| 0 | 100 | 0.0000 | [0.0000, 0.0000] | 0.0000 |
| 0 | 500 | 0.0000 | [0.0000, 0.0000] | 0.0000 |
| 0.42 (base) | 100 | 0.0000 | [0.0000, 0.0000] | 0.0000 |
| 0.42 (base) | 500 | 0.0022 | [0.0000, 0.0067] | 0.0022 |
| 5 | 100 | 0.0036 | [0.0000, 0.0092] | 0.0036 |
| 5 | 500 | 0.0065 | [0.0000, 0.0142] | 0.0065 |
| 30 | 100 | 0.0500 | [0.0311, 0.0704] | 0.0478 |
| 30 | 500 | 0.0442 | [0.0280, 0.0613] | 0.0442 |
| 60 | 100 | 0.1011 | [0.0692, 0.1352] | 0.0945 |
| 60 | 500 | 0.0999 | [0.0715, 0.1300] | 0.0981 |

The single-height stale count-rate rises **monotonically** with propagation delay, as
amended H7 anticipates: a larger `received_winner_time` widens the window in which a
distinct non-winning miner can find a competing solution. An optional pooled-by-seed
curve (30 seed clusters, aggregating the two N per seed) reproduces the same monotone
trend (0, 0.0011, 0.0050, 0.0471, 0.1005). Full per-run values and both CIs are in
`h7_secondary.json` / `table12_secondary_stale.csv`.

At **delay 0**, **0 stale blocks are observed across the 515 (N=100) / 528 (N=500)
accepted heights**. This is reported as an observed zero, not a certainty. Any model-based
zero-event upper reference (e.g. a rule-of-three value over accepted heights) is labelled
**ASSUMPTION-DEPENDENT / SECONDARY** because it would treat accepted heights as independent
Bernoulli trials, which they are not; it is **not** an "exact binomial" interval. See
`STAGE_06A_H7_INTERVAL_AUDIT.md`.

## 2. Primary-metric invariance under delay (`primary_invariance_across_delay`)

Seed-matched to the delay=0.42 baseline, delay-only variation leaves the primary outcomes
**exactly unchanged** (max absolute deviation 0 across all delays and N):

- `total_energy_kwh` — invariant
- `accepted_blocks` — invariant
- `total_candidate_evaluations` — invariant
- `total_active_time_s` — invariant

Only the single-height stale diagnostic and the per-delivery records vary with delay,
confirming the diagnostic is a bolt-on measurement that does not perturb the search or
energy accounting.

## 3. Scope guardrails (what this is NOT)

This diagnostic is **not** a full asynchronous blockchain-network simulation, **not** a
chain-wide fork-rate estimate, **not** a security proof, and **not** a multi-height
stale-chain model. It is a single-height stale-race sensitivity reported for
completeness. No confirmatory or security claim is drawn from it.
