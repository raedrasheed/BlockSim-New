# Stage 6A — H7 Interval Audit (count-rate correction)

Corrects the H7 uncertainty intervals (Stage 6A §5). The original H7 analysis applied
Wilson / Clopper-Pearson / binomial rule-of-three intervals to
`single_height_stale_block_count / accepted_blocks`. That is **invalid**: at one accepted
height, **several distinct non-winning miners** may each publish a stale block, so the
numerator is a **count of distinct stale producers**, not the number of Bernoulli
successes over accepted-block trials. A binomial denominator of accepted blocks does not
apply.

## 1. Corrected framework

`single_height_stales_per_accepted_block` is treated as a **count-rate diagnostic**. For
each `(delay, miner_count)` cell (30 runs = 30 seeds):

1. report the **30 run-level values**;
2. report **mean, median, SD, IQR, min, max**;
3. compute a **seed/run-cluster bootstrap 95% CI** for the mean count-rate (resampling the
   30 run-level values — each run is one independent seed at that cell);
4. keep **N=100 and N=500 separate**;
5. an optional **pooled** curve resamples **30 seed clusters** (aggregating the two N per
   seed) — it never treats accepted blocks as independent Bernoulli trials.

A **separate binary diagnostic** uses `heights_with_any_stale / accepted_heights` =
**"probability that an accepted height has at least one modeled stale producer"**, reported
as a per-run proportion with a run-cluster bootstrap CI. Even this binary outcome accounts
for clustering within physical runs (per-run proportions, resampled by run).

**No Wilson, Clopper-Pearson, or binomial interval is applied to the stale count.** The
term "exact binomial" is not used anywhere for a raw stale-count interval.

## 2. Corrected results (B3/C1 homogeneous equal; 30 runs per cell)

| delay (s) | N | mean stales/block | cluster boot 95% CI | any-stale-height fraction |
|-----------|--:|------------------:|---------------------|--------------------------:|
| 0 | 100 | 0.0000 | [0.0000, 0.0000] | 0.0000 |
| 0 | 500 | 0.0000 | [0.0000, 0.0000] | 0.0000 |
| 0.42 | 100 | 0.0000 | [0.0000, 0.0000] | 0.0000 |
| 0.42 | 500 | 0.0022 | [0.0000, 0.0067] | 0.0022 |
| 5 | 100 | 0.0036 | [0.0000, 0.0092] | 0.0036 |
| 5 | 500 | 0.0065 | [0.0000, 0.0142] | 0.0065 |
| 30 | 100 | 0.0500 | [0.0311, 0.0704] | 0.0478 |
| 30 | 500 | 0.0442 | [0.0280, 0.0613] | 0.0442 |
| 60 | 100 | 0.1011 | [0.0692, 0.1352] | 0.0945 |
| 60 | 500 | 0.0999 | [0.0715, 0.1300] | 0.0981 |

## 3. Delay = 0 (zero observations)

At delay 0, **0 stale blocks are observed across the 515 (N=100) / 528 (N=500) accepted
heights**. This is reported as an observed zero. Any model-based zero-event upper reference
(e.g. a rule-of-three value over accepted heights) is explicitly labelled
**ASSUMPTION-DEPENDENT / SECONDARY** in `h7_secondary.json`, because it would treat accepted
heights as independent Bernoulli trials, which they are not. It is **not** an exact-binomial
interval and is not used to support any claim.

## 4. Status

H7 remains **SECONDARY_DIAGNOSTIC_ONLY**. Primary outcomes (energy, accepted blocks,
candidate counts, active time) are identical across delay (max deviation 0). Updated
outputs: `STAGE_06_SECONDARY_DIAGNOSTICS.md`, `table12_secondary_stale.csv`,
`h7_secondary.json`, `fig08_h7_delay_singleheight` (PDF/PNG/plot data).
