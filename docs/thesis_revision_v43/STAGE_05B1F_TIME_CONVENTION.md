# Stage 5B1F — Unified Candidate-Time Convention

Engine: `scenario_engine.py` (`_completed`); `coverage.py` (`b2_winner`,
`lengths_from_winner_time`, `exhaustive_winner_reference`)
Tests: `test_stage5b1f_exhaustion_time.py` (17–20)

## 1. One convention for every scenario

The first candidate completes after one hash interval. For candidate offset `d`:

```
discovery_time      = (d + 1) / hash_rate
completed_count(t)  = floor(hash_rate · t),  capped by range / traversal size
```

Consequences (all tested):
- **no candidate completes at t = 0** (test 17);
- the first candidate completes at exactly `1/H` (test 18);
- by the discovery time of offset `d`, exactly `d + 1` candidates are completed
  (test 19);
- exact behaviour at candidate-completion boundaries and just below them (test 20).

## 2. Applied uniformly

| Function | Change |
|----------|--------|
| `_completed(rate, t, cap)` | `floor(rate·t)` via exact integer division on a `Fraction` t |
| `b2_winner` | discovery time `(d + 1)/rate` (was `d/rate`) |
| `lengths_from_winner_time` | `floor(rate·t)` (removed the old `+1`) |
| `exhaustive_winner_reference` | `(d + 1)/rate` to match |
| disjoint / B1 discovery | `Fraction(offset + 1, rate_int)` |

B0, B1, B2, B3/C1, and C2 now all use this single convention, so cross-scenario
comparisons of discovery time and coverage are consistent, and no zero-time block can
exist.

## 3. Exactness

Because `t_end` is a rational `Fraction` and hash rates are integers (see
`STAGE_05B1F_PRECISION_AUDIT.md`), `completed_count = floor(rate·t)` is computed by
exact integer division `(rate · t.numerator) // t.denominator` — exact for every
candidate count, including at boundaries and above 2⁵³.
