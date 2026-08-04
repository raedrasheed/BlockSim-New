# Stage 6M — Analysis Plan (frozen before confirmatory execution)

**Data**: the frozen 30-row Stage-7M confirmatory dataset only. **Unit**: one physical run
under one master seed. n = 10 paired seeds per contrast. **Analysis seed**:
13165134141831138817 (Stage-6 analysis seed, unchanged), used for the bootstrap RNG.

## Estimators

For a paired vector d_1..d_10:

* exact paired sign-permutation: enumerate all 2^10 = 1024 assignments s in {−1,+1}^10 of the
  statistic mean(s_i x d_i); one-sided p = #{mean >= observed} / 1024 (direction preregistered
  as reduction for H-M1);
* paired bootstrap: 10 000 resamples of the 10 seeds with replacement; percentile 95 % CI for
  the mean and for the relative difference;
* report mean, median, relative difference, CI, exact p.

## H-M1 (M01, within-run null)
d_i = E_power_null(i) − E_idle(i). Success = ALL of: mean relative reduction >= 5 %;
bootstrap 95 % lower bound > 0; exact one-sided p < 0.05.

## H-M2 (M02, within-run null)
Same estimators, **descriptive**: mean, median, 95 % CI, relative difference. No pass/fail,
no equivalence claim, no generalisation.

## H-M3 (M03 vs M01, same seed)
Per-seed ratios accepted_blocks and median_round_duration (M03/M01); report their means,
medians and bootstrap CIs; evaluate the four preregistered limits; report
floor_unattainable_count honestly. Deterministic limits are not given p-values.

## Deterministic gates
Evaluated exactly, without p-values, per run, per §8 of the preregistration. Any failure
blocks inference.

## Exclusions
None outcome-based. Zero-block runs stay. NA stays NA. X01/X02 never enter any estimator.
If an interval is wide or includes zero: the result is inconclusive, and is reported so.
