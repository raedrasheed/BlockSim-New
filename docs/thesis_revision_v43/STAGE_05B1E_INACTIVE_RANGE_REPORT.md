# Stage 5B1E — Inactive-Range Correctness

Engine: `experiments/thesis_revision_v43/scenario_engine.py`
Tests: `tests/thesis_revision_v43/stage5b1e/test_stage5b1e_inactive.py` (1–7)

## 1. The defect

For disjoint scenarios the engine sampled K solutions over the **whole** domain S.
Some positions fall inside ranges assigned to **inactive** miners. The old
`_discover` fallback returned a finite winner time and a nominal winner even when no
active miner owned any solution, so the loop could accept a block **no active miner
could have discovered** — a fabricated block.

## 2. Corrected semantics

Each generation now classifies every solution position by its owning range:

| Quantity | Field |
|----------|-------|
| Solutions in the whole template domain | `total_template_solution_count` |
| Solutions in **active** assigned ranges | `active_range_solution_count` |
| Solutions in **inactive** ranges | `inactive_range_solution_count` |
| Active solutions actually discoverable | `discoverable_finder_count` |

`_discover` returns an **explicit status** — never a fabricated winner:

- `FOUND_ACTIVE_SOLUTION` — an active miner's search path reaches a solution → block;
- `ACTIVE_DOMAIN_EXHAUSTED` — active ranges searched, no active solution → refresh;
- `NO_ACTIVE_MINERS`;
- `PARTIAL_AT_CUTOFF` — the horizon ended mid-generation.

A solution located **only** in an inactive range therefore does **not**: create a
block, assign a winner, increment `accepted_blocks`, increment the stale count,
trigger propagation, or trigger agreement operations. When all active ranges
complete without an active solution the generation is classified exhausted and the
template refreshes under the frozen policy; inactive/unsearched positions are
recorded separately.

## 3. Validation

An inactive-only generation is produced deterministically (B3, N=10, 50 % inactive,
seed 1): `total_template_solution_count > 0`, `active_range_solution_count = 0`,
`accepted_block_id = None`, `status = ACTIVE_DOMAIN_EXHAUSTED`. Across the validation
matrix (`STAGE_05B1E_VALIDATION_REPORT.md`) the **inactive-range reconciliation**
holds on every run: no inactive-only generation carries a block, and
`Σ per-miner candidates == network total`. Block propagation messages equal
`accepted_blocks × (active − 1)` exactly — inactive-only generations add none.
