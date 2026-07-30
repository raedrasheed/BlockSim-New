# Stage 5B1G — Exact B2 Circular-Exhaustion Closure (Section 7)

Code: `experiments/thesis_revision_v43/coverage.py`
(`b2_exhaustion_time_exact`, `coverage_at_time_exact`)
Engine: `scenario_engine.py` (`_sim_frontier`, B2 `k == 0` branch)
Tests: `tests/thesis_revision_v43/stage5b1g/test_stage5b1g_b2_exhaustion.py` (28–34)

## 1. Defect removed

The former exhaustion time came from a **float binary search** and was then quantised
to six decimals (`Fraction(str(round(t_ex, 6)))`) before entering the event loop. That
is neither exact nor a valid basis for an "exact exhaustion" claim. The float routine
`b2_exhaustion_time` is retained only as an independent cross-check and its docstring
now states it is **not** exact; all six-decimal rounding is removed from the engine.

## 2. Exact rational closure

Under the unified convention a candidate at circular offset `d` from `start_i`
completes at `(d+1)/rate_i`; miner `i` has completed `floor(rate_i · t)` candidates by
time `t`. The domain is exhausted at

```
t_ex = max_q  min_i  ((q - start_i) mod S + 1) / rate_i          (integer rate_i)
```

Because each `g_i(q) = ((q − s_i) mod S + 1)/r_i` is increasing in `q` between the
starts and resets only at `q = s_i`, the min-of-increasing function `f = min_i g_i`
is increasing on each inter-start arc; its maximum over the ring is therefore attained
at one of the `n` positions `q_i = (s_i − 1) mod S` — the position each miner covers
**last**. `b2_exhaustion_time_exact` evaluates `f` exactly (`Fraction`) at those `≤ n`
candidate positions and takes the maximum. `t_ex` is thus an exact rational
`m*/r_{i*}`. The routine is `O(n²)`, exact at any scale, with **no** float and **no**
domain enumeration.

## 3. Returned fields and coverage proof

```
b2_exhaustion_time_fraction_numerator / _denominator   # exact irreducible t_ex
b2_exhaustion_time_s                                    # float view only
previous_candidate_event_time_s                         # largest event time < t_ex
coverage_before_exhaustion   (< S)                      # exact union at t_prev
coverage_at_exhaustion       (= S)                      # exact union at t_ex
exact_exhaustion_verified    (= coverage_before < S and coverage_at == S)
```

`t_prev` is the largest candidate-event time strictly below `t_ex`, found per miner as
`m = (r_j·t_ex.num − 1) // t_ex.den` (largest integer with `m/r_j < t_ex`), capped at
`S`. Coverage at both `t_prev` and `t_ex` is computed by the exact integer
circular-interval union (`coverage_at_time_exact`), giving the proof pair
`coverage(t_prev) < S ≤ coverage(t_ex) = S`.

## 4. Validation

- Exact time equals the independent brute-force reference
  `exhaustion_time_reference_small` on six domains (test 28), to `< 1e-12`.
- `exact_exhaustion_verified` is `True` and the coverage proof holds on every case
  (tests 29, 30).
- For `S=100, starts=[0,25,50,75], rates=[7,3,11,5]`, `t_ex = 50/7` exactly
  (numerator 50, denominator 7) — a non-terminating decimal that a six-decimal
  rounding would corrupt; `t_ex ≠ Fraction(str(round(float(t_ex), 6)))` (tests 31, 32).
- Overlapping starts exhaust strictly later than well-spread starts (test 33).
- The engine records the exact closure fields on every B2 `k == 0` exhaustion
  generation, with `coverage_at_exhaustion == S` and `coverage_before < S`
  (test 34; `b2_exhaustion` reconciliation family in `validate_5b1g.py`).

If a domain could not be exactly closed the routine would return
`exact_exhaustion_verified = False` with bounded coverage and no "exact" claim; in
every exercised configuration exact closure is achieved.
