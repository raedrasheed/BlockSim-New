# Stage 5B1E — Exact Per-Miner Search-Progress Accounting

Tests: `test_stage5b1e_accounting.py` (14–20)

## 1. The defect

The engine represented per-miner work with the shortcut `searched = L_i` (a single
range value) and derived network coverage from `winner_time · Σ rates`. This did not
reflect actual per-generation progress and could not reconcile to the network total.

## 2. Corrected model

Per template generation, active miner *i* evaluates
`c_i = min(S_i, ⌊rate_i · t_end⌋)` candidates from its range start (the winner's is
the exact integer `q_win − a_i + 1`). Cumulative `candidates_evaluated` sums `c_i`
across generations (it may exceed one range size because each new template is
re-searched with fresh candidate identities).

Every per-miner record carries (Section 4): assigned range start/end/size,
`search_start_position`, `candidates_evaluated`, `last_evaluated_position`,
`unsearched_count`, `remaining_unsearched`, `inactive_count`, `active_time_s`,
`idle_time_s`, `offline_time_s`, `productive_search_time_s`, `completion_status`,
and `stop_reason` ∈ {`solution_found`, `range_exhausted`, `template_refreshed`,
`inactive`, `simulation_cutoff`} (plus `competing_block_received`, `reallocated` in
the vocabulary).

## 3. Reconciliations (exact integers)

- **Network:** `Σ_i candidates_evaluated == total_candidate_evaluations` for disjoint
  scenarios (test 17) — verified for B0/B3-C1/C2 including inactive fractions.
- **Domain (per template):** `searched + unsearched + inactive == assigned` exactly
  (test 18), for every generation.
- **Inactive miners:** `candidates_evaluated == 0`, `stop_reason == inactive`,
  `offline_time_s > 0` (test 19).
- Heterogeneous miners show **distinct** per-miner progress (not one constant), and
  an early winner leaves later positions **unsearched** (tests 14, 15).

No single-range value stands in for cumulative multi-generation work.
