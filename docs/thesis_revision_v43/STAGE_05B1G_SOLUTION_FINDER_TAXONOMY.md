# Stage 5B1G — Solution-Position vs Finder Taxonomy (Section 6)

Engine: `scenario_engine.py` (`_sim_disjoint`, `_sim_frontier`)
Schema: `schemas.reconcile_solution_positions`
Tests: `tests/thesis_revision_v43/stage5b1g/test_stage5b1g_solution_taxonomy.py` (24–27)

## 1. Positions counted before reducing to proposals

Every sampled solution position is counted **before** the reduction to one potential
proposal per miner. In the disjoint sims the loop increments `n_active_positions` for
each sampled position whose owner is an active miner, independently of whether the
same miner already owns an earlier position. Only then is each miner reduced to its
earliest reachable solution (one potential proposal per miner).

| Field | Counts |
|-------|--------|
| `total_template_solution_position_count` | all sampled positions (`= k`) |
| `active_range_solution_position_count` | positions in active ranges |
| `inactive_range_solution_position_count` | positions in inactive ranges |
| `distinct_potential_finder_miner_count` | distinct **miners** with a reachable solution |

The former engine assigned `len(discoveries)` (a miner count) to the active
solution-**position** field. That is fixed: the active-position field now counts
positions, and a separate field counts finder miners.

## 2. Reconciliation

- **Position split (universal):** `active_positions + inactive_positions == total
  positions` for every generation and every scenario (test 24, `bad_position_split`
  empty).
- **Finder ≤ positions (disjoint only):** in disjoint scenarios each active position
  has a single owner, so `distinct_potential_finder_miner_count ≤
  active_range_solution_position_count` (test 25). A miner owning several positions
  raises the position count but **not** the finder count.
- **Common-template caveat:** in B1/B2 every miner can reach every position, so the
  number of potential finder miners may exceed the number of positions; the finder ≤
  position check therefore does **not** apply to common-template scenarios
  (`reconcile_solution_positions(..., disjoint=False)`).

## 3. Multiplicity witnessed

With few miners and high μ (e.g. `B3/C1`, 5 miners, μ = 5) many generations have a
miner owning several positions: `active_range_solution_position_count >
distinct_potential_finder_miner_count` (test 25/26). One potential proposal per miner
is preserved; actual proposals are realised only after the stale-race test
(`STAGE_05B1G_STALE_DIAGNOSTIC_SCOPE.md`).
