# Stage 5B1E — Per-Template Chronology

Tests: `test_stage5b1e_chronology.py` (26–30)

## 1. The defect

Exhausted-template records could carry identical `start_time_s` and `end_time_s`
(zero duration), so template chronology was not a real timeline.

## 2. Corrected records

Every template-generation record now carries a real chronology:

`start_time_s`, `end_time_s`, `duration_s`, `exhausted_time_s`,
`active_domain_completion_time_s`, `partial_cutoff_time_s`, and `refresh_cause`.

The generation loop advances a single clock `t`, so generations tile the horizon:
each record spans `[t, t + duration]` and the next begins where the previous ended.

## 3. Invariants (all tested)

| # | Invariant | Test |
|---|-----------|------|
| 1 | `end_time_s ≥ start_time_s` | 27 |
| 2 | exhausted (non-zero) generations have `duration_s > 0` | 26 |
| 3 | generation intervals are monotonic and non-overlapping (`start_{i+1} ≥ end_i`) | 27 |
| 4 | durations reconcile to the horizon: `Σ duration_s = 10 000 s` | 28 |
| 5 | a `PARTIAL_AT_CUTOFF` final generation sets `partial_cutoff_time_s` and ends at the horizon | 29 |
| 6 | `refresh_cause` matches the transition: `accepted_block` (block), `active_domain_exhausted`/`no_active_miners` (exhausted), `simulation_cutoff` (partial) | 30 |

Exhausted generations now take the real `D_ex = max_i τ_i` (see
`STAGE_05B1E_RANGE_LIFECYCLE.md`), so their duration is positive and the timeline is
a faithful, monotonic chronology that sums exactly to the simulation horizon.
