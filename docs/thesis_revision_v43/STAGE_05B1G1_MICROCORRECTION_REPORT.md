# Stage 5B1G.1 — Micro-Correction Completion Report

**Three narrow corrections to the frozen 5B1G engine — no redesign, no new
hypotheses.** Engine `scenario_engine.py` → `5b1g.2`; output schema → `5b1g.2`. Matrix
regenerated (1 890 runs, 63 × 30 unchanged). Full suite **444 passed**. Thesis
DOCX/PDF byte-identical. The 1 890-run matrix is **not** executed; Stage 5B2 is
**not** begun.

## The three corrections

1. **Exact B2 primary coverage (§1).** `_sim_frontier` no longer converts `eff_end`
   to float before deriving candidate counts. A new `coverage.lengths_at_time_exact`
   computes `completed_i = min(S, floor(rate_i · t))` with pure integer/Fraction
   arithmetic, and the SAME exact per-miner lengths feed the per-miner-generation
   rows, the network total, the circular union, the distinct count and the duplicate
   count. `Σ per_miner_generation.candidates_evaluated_this_generation ==
   total_candidate_evaluations` holds as an exact integer identity (asserted in the
   engine and tested). At the adversarial boundary `rate=49, t=1/49` the exact path
   gives 1 where the float path gives 0.

2. **B2 path provenance (§2).** Every B2 active miner records its actual seeded
   circular start `search_start_position = starts[idx]` (0 only when the seeded start
   is 0); `last_evaluated_position = (start + c_i − 1) mod S` (null when `c_i == 0`);
   plus `path_wraps_around`, `path_end_position`, `circular_candidates_evaluated`.
   B1 keeps start 0; disjoint keeps the assigned-range start; inactive B2 miners
   record a null start.

3. **Winner delivery + post-winner work for EVERY active non-winner (§3,§4).** For
   each accepted height a deterministic delivery is derived for every active
   non-winning miner — potential competitor, stale producer, same-identity
   independent finder, or no-solution miner alike — with `propagation_delay_s`,
   `received_winner_time_s`, `delivery_stream_key`, earliest reachable solution
   time/identity, `produced_stale_block`, and a lifecycle `stop_reason`. Post-winner
   diagnostic totals are accumulated over ALL active non-winners
   (`t_stop_j = min(received_winner_time_j, solution_time_j)`):
   `post_winner_candidate_evaluations`, `post_winner_active_time_s`,
   `post_winner_energy_not_integrated = true`. The producer-only subset is reported
   as `stale_producer_postwinner_candidate_evaluations` /
   `stale_producer_postwinner_active_time_s`. The retained legacy names
   `stale_race_candidate_evaluations` / `stale_race_active_time_s` are defined to
   equal the **complete** post-winner totals (all non-winners), never the
   producer-only subset. None of these enter primary candidate counts, primary
   energy, or the block interval.

Potential-competitor classification is unchanged and separate: distinct miner AND
distinct candidate identity AND a reachable solution exists.

## 21 acceptance criteria

| # | Criterion | Evidence |
|---|-----------|----------|
| 1 | B2 candidate counts exact Fraction/integer end to end | `lengths_at_time_exact`; tests 2,3 |
| 2 | No float time derives candidate counts | test 1 (engine source), `float(eff_end)` only in time-output fields |
| 3 | B2 actual random starts recorded | test 5 |
| 4 | B2 last positions use circular modulo | test 6 |
| 5 | Every active non-winner has a delivery record | test 10; validation `all_nonwinner_deliveries` |
| 6 | B1 same-identity miners receive winner, no stale | tests 11,16 |
| 7 | Post-winner work includes all active non-winners | tests 14,15 |
| 8 | Post-winner work separate from primary metrics | tests 17,18; `post_winner_energy_not_integrated` |
| 9 | Broad stale-race fields not producer-only without explicit naming | `stale_race_* == post_winner_*` (complete); `stale_producer_postwinner_*` named subset (test 14) |
| 10 | No contradictory one-stale-per-height documentation | test 19 (engine + docs scan) |
| 11 | All new and prior tests pass | full suite 444 passed; test 20 |
| 12 | Draft-42 DOCX/PDF byte-identical | test 21; SHA-256 unchanged |
| 13 | 1 890-run matrix not executed | matrix builder writes PLANNED rows only |
| 14 | One corrective commit pushed | see Freeze #6 |
| 15 | Freeze branch 6 created | see Freeze #6 |
| 16 | Conclusion | `READY_FOR_STAGE_5B2_FREEZE_6` |
| 17 | Adversarial Fraction boundary tested | test 4; validation `adversarial_boundary` |
| 18 | Wraparound path provenance | test 7 |
| 19 | B1 start 0 / disjoint start = range start | tests 8,9 |
| 20 | No-solution miner receives winner | test 12 |
| 21 | Non-stale competitor receives winner | test 13 |

## Full 64-character checksums

| Input | SHA-256 |
|-------|---------|
| Matrix `STAGE_05B1G1_FINAL_MATRIX.csv` | `9cb7297e7418a96fbaeb7f06c162bc8bdea1c1e049002a40344cab16cf5f6fcb` |
| Seed schedule | `6122dbd0f455a1c4c9676ec6575f064c3a682b3c978705d6588af11489b13e10` |
| Retention list | `2283f2ff69bcabf423267b2984ef4acfce852b217b39e1efe8061e583bc1702e` |
| Dependency lock | `6e211ea7c031a3fab560843690e27e5a3c2aa2a8c363ab483369a2babc8157be` |
| Thesis DOCX | `2c3afdc5739109d0ea12ada96c3115d626a2188c1acbaeaa4b6020974884cbda` |
| Thesis PDF | `131412bb2ce17ed97b98dfbefc136c7b5b226b9fd7372e79a25e4b0dc057e9c4` |

## Freeze #6

Corrective commit SHA (recorded externally, non-self-referential) → remote branch
`thesis-v43-stage5b2-freeze-6`. Preserved unchanged: `…-freeze-1` (`c0ff48e`),
`…-2` (`03591d8`), `…-3` (`069a0c5`), `…-4` (`8cb490c`), `…-5` (`e7f046b`,
**invalid for execution**).

**Conclusion: `READY_FOR_STAGE_5B2_FREEZE_6`.** Work stops before Stage 5B2.
