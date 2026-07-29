# Stage 5B1F — Per-Miner Per-Generation Accounting

Engine: `scenario_engine.py` (`emit_generation_detail`)
Schema: `schemas.PER_MINER_GENERATION_FIELDS`
Tests: `test_stage5b1f_generation.py` (21–27)

## 1. Artifact

With `emit_generation_detail=True`, `run_scenario` returns `per_miner_generation`: one
machine-readable record per **(run, template generation, miner)** with the fields
(Section 8): `run_id`, `template_generation_id`, `miner_id`, `template_id`,
`assigned_range_{start,end,size}`, `search_start_position`,
`candidates_evaluated_this_generation`, `cumulative_candidates_evaluated`,
`last_evaluated_position`, `unsearched_candidates_this_generation`,
`inactive_candidates_this_generation`, `productive_search_time_s`,
`active_nonproductive_time_s`, `idle_time_s`, `offline_time_s`,
`earliest_solution_position`, `earliest_solution_time_s`, `stop_reason`,
`completed_range`, `generated_block_id`, `received_winner_time_s`.

Emitted for **every** scenario (disjoint and frontier).

## 2. Cumulative vs generation-level are separate

`candidates_evaluated_this_generation` is the exact per-generation progress;
`cumulative_candidates_evaluated` is the running sum. They are **distinct** fields
(test 24). `unsearched_candidates_this_generation` is computed directly as
`assigned_range_size − candidates_evaluated_this_generation` — **not** from a modulo
of the cumulative value (tests 23, 25).

## 3. Reconciliation

For disjoint scenarios the generation rows reconcile exactly to the network total:

```
Σ candidates_evaluated_this_generation == total_candidate_evaluations
```

verified for B0, B3/C1, and C2 including inactive fractions (test 22). Idle rows
appear for C2 (`idle_time_s > 0`), and non-productive-active rows appear for B3/C1
(`active_nonproductive_time_s > 0`, `idle_time_s == 0`) — tests 26, 27.

## 4. Scale note

The artifact is `O(generations × miners)` per run, so it is emitted for validation and
small runs. For the full matrix, Stage 5B2 would emit it only for the retained
full-log runs; the network-total reconciliation makes the summary totals sufficient
for the rest.
