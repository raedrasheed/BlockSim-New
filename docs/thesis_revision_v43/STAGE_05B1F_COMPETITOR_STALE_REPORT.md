# Stage 5B1F — Exact Competitor / Stale-Block Semantics

Engine: `scenario_engine.py` (`_resolve`, per-miner discovery)
Tests: `tests/thesis_revision_v43/stage5b1f/test_stage5b1f_stale.py` (1–10)

## 1. The defect

Stale/competitor blocks were derived from the **second-smallest solution position**
divided by `max_rate` and one **global** propagation delay. That does not model
distinct competing miners: a second valid nonce owned by the *winning* miner, or the
same header found by many miners, was mis-counted.

## 2. Per-miner discovery

For every template generation and active miner the engine builds one
`MinerDiscovery(miner, offset, q, identity, time)` — the miner's **earliest reachable
solution** (a miner stops at its first valid solution, so it contributes **at most one
proposal** per generation). Discovery time uses the unified convention
`time = (offset + 1) / rate` as an exact `Fraction`.

Candidate-header identity:
- common-template scenarios (B1, B2, B3/C1, C2): identity = nonce `q`;
- **B0** independent templates: identity = `(miner, q)` — equal numeric nonces under
  different templates are **distinct** identities.

## 3. Winner and legitimate stale

The winner is the earliest `MinerDiscovery` (rational tie-break by miner id). For each
other discovery `j`, a **competitor** requires: (1) a **different miner**, (2) a
**different candidate identity**. A competitor is a **legitimate stale** iff it also
discovered before receiving the winner:

```
time_j < winner_time + delay_j
```

where `delay_j` is a **separate** propagation delay per winner→miner delivery, drawn
from a winner-scoped named random stream (not one global delay).

Recorded fields: `actual_competitor_miner_count`, `legitimate_stale_block_count`,
`actual_proposal_miner_count`, `distinct_potential_finder_miner_count` (and per-block
competitor detail in the block log).

## 4. Scenario-specific results (all tested)

| Scenario | Stale behaviour |
|----------|-----------------|
| **B1** | all miners reach the same lowest nonce → same identity → **zero** distinct stale, zero competitors (reported honestly) |
| **B2** | each miner's earliest solution comes from its **own seeded circular path**; competitors are other miners' distinct solutions — never the second numeric nonce |
| **B3/C1, C2** | earliest solution in each miner's disjoint range; a miner owning several positions proposes only its earliest |
| **B0** | template identity used, so equal nonces under different templates are distinct |

- A second solution owned by the same miner is **not** a competitor (test 2, 8).
- A distinct miner within the delay window **is** a stale; after the window it is not
  (tests 3, 4); zero delay → no late competitor (test 5).

## 5. Denominators (Section 4)

Both are output with explicit definitions and NA handling:

```
stales_per_accepted_block          = stale_blocks / accepted_blocks
stale_fraction_of_all_valid_blocks = stale_blocks / (accepted_blocks + stale_blocks)
```

`legitimate_stale_rate` is retained as a documented alias of `stales_per_accepted_block`.
Zero-proposal cases are `null` with a reason. At realistic parameters the gap between
the two earliest discoveries (~hundreds of seconds) far exceeds the propagation delay,
so legitimate stales are **rare** — an honest outcome; a small-domain regime that does
produce them is included in validation.
