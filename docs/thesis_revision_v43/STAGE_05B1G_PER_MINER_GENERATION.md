# Stage 5B1G — Per-Miner-Generation Stale-Race Output (Section 5)

Engine: `scenario_engine.py` (`_sim_disjoint`, `_sim_frontier`)
Schema: `schemas.PER_MINER_GENERATION_FIELDS`, `GENERATION_STOP_REASONS`
Tests: `tests/thesis_revision_v43/stage5b1g/test_stage5b1g_generation.py` (18–23)

## 1. Extended record

Each per-(run, generation, miner) record (emitted with `emit_generation_detail=True`)
carries the Stage 5B1F search-progress fields plus the stale-race lifecycle fields:

| Field | Meaning |
|-------|---------|
| `received_winner_time_s` | `winner_time + delay(w→miner)`; for the winner, its own `winner_time`; `None` if no block this height |
| `propagation_delay_s` | this miner's recipient-specific delivery delay (`None` for winner / no block) |
| `potential_old_parent_solution_position` / `_time_s` | this miner's earliest reachable competing solution (its stale would extend the old parent) |
| `found_competing_solution_before_receipt` | `True` iff `discovery_time < received_winner_time` |
| `produced_stale_block` | `True` iff this miner is an admitted stale producer at this height |
| `stale_block_id` | this producer's unique stale block id (`stale-<block>-m<miner>`), else `None` |
| `search_progress_reason` | preserved 5B1F search classification (`range_exhausted`, `template_refreshed`, …) |
| `stop_reason` | **lifecycle** reason ∈ `GENERATION_STOP_REASONS` |

`stop_reason` (lifecycle) vocabulary:

```
solution_found        winner — generated the main block
stale_block_generated a distinct non-winning miner that discovered before receipt (admitted stale)
winner_received       a competitor that received the winner without an admitted stale
no_reachable_solution active miner with no reachable solution this generation (incl. exhausted heights)
simulation_cutoff     generation interrupted by the horizon (partial)
inactive              offline miner
```

## 2. Guarantees (tested)

- Schema is complete on every record and `stop_reason` is always a member of the
  vocabulary (test 18).
- The **winner** row has `generated_block_id` set, `received_winner_time_s ==
  winner_time`, `stop_reason == "solution_found"`, `produced_stale_block == False`
  (test 19) — `received_winner_time_s` is never left null when a winner exists.
- **Every** admitted stale producer's row has `produced_stale_block == True`, a unique
  `stale_block_id`, a non-null `propagation_delay_s` and `received_winner_time_s`,
  `found_competing_solution_before_receipt == True`, and
  `stop_reason == "stale_block_generated"` (test 20). Multiple producers at one height
  yield multiple such rows — they are **not** collapsed. The producer id set per
  generation equals the per-template `stale_producer_miner_ids`
  (`test_stale_producer_ids_match_generation_rows`).
- A distinct-identity competitor that did not produce an admitted stale has
  `stop_reason == "winner_received"` with a recorded delay (test 21).
- A miner with no reachable solution has `stop_reason == "no_reachable_solution"` and
  null solution fields (test 22).

## 3. Propagation counted separately (Section 5)

`main_block_propagation_message_count/_bytes` count one winner broadcast to every
other active miner per accepted height; `stale_block_propagation_message_count/_bytes`
count one broadcast **per admitted stale** (so with several stales per height the
stale total exceeds the main total). A zero-delay run has zero stale propagation and
non-zero main propagation (test 23).
