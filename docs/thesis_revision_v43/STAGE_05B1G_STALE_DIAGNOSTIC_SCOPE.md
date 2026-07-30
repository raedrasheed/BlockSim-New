# Stage 5B1G — Single-Height Stale-Race Diagnostic: Scope, Isolation, Taxonomy

Engine: `experiments/thesis_revision_v43/scenario_engine.py`
(`_resolve_stale_race`, `_record_stale_race`, `_build_result`)
Schema: `schemas.PER_TEMPLATE_FIELDS`, `STALE_RACE_RECORD_FIELDS`,
`reconcile_stale_diagnostic`
Tests: `tests/thesis_revision_v43/stage5b1g/test_stage5b1g_stale.py`

## 1. Reclassification (Section 1)

The stale model is a **`SINGLE_HEIGHT_STALE_RACE_DIAGNOSTIC`**. It resolves, for one
accepted height in isolation, which non-winning miners would have published a
competing block before receiving the winner. It is a **secondary diagnostic**, not a
confirmatory quantity, and is deliberately **isolated** from:

- the canonical block interval (`effective_block_interval_s`);
- the primary coverage counts (`total/distinct/duplicate_candidate_evaluations`);
- the primary energy (`total/active/idle/coordination_energy_kwh`);
- next-height mining and fork resolution (there is none — each height is independent);
- the accounting invariant A1 (continuous full-participation total energy stays
  `8.420833333 kWh`, unchanged by this diagnostic — regression test 42).

Its scope is one height: there is **no** chain reorganisation, no orphaned-subtree
accounting, and no propagation of a stale into the next generation's parent. The
preregistration amendment (`STAGE_05B1G_PREREGISTRATION_AMENDMENT.md`) reclassifies
**H7** from confirmatory to *secondary diagnostic sensitivity*. No thesis prose is
edited.

## 2. Lifecycle — one stale per MINER per height, no global cap (Section 2, corrected)

For an accepted height with winner `w` (earliest discovery, ties by lowest miner id)
and every other miner `j`:

```
received_winner_time_j = winner_time + delivery_delay(w -> j)
miner j produces a stale block  iff
    j != w  AND  identity_j != identity_w  AND  discovery_time_j < received_winner_time_j
```

Each miner contributes **at most one** stale per height (its earliest reachable
solution — `_resolve_stale_race` keeps one entry per miner). **Multiple distinct
miners may each produce a stale at the same height**, so

```
stale_block_count(height)  ∈  0 .. N_active - 1
```

There is **no** global one-stale-per-height cap. In the controlled diagnostic regime
(`B3/C1`, seed 5, 20 miners, 2000 h/s, 1 s interval, 60 s mean delay) heights carry up
to **10** distinct stale producers; 7 377 heights have ≥2 and 4 997 have ≥3.

### Per accepted height (identities enforced and tested)

| Quantity | Definition |
|----------|-----------|
| `actual_stale_producer_miner_count` | # distinct non-winning miners discovering before receipt |
| `stale_block_count` | `== actual_stale_producer_miner_count` (one block per producer) |
| `actual_competitor_miner_count` | `== actual_stale_producer_miner_count` |
| `actual_proposal_miner_count` | `1 + actual_stale_producer_miner_count` (winner + all stales) |
| `potential_competitor_miner_count` | distinct non-winning, distinct-identity miners (`>= actual`) |
| `height_has_any_stale` | boolean `stale_block_count > 0` — an indicator, **never** a substitute for the count |

One entry **per stale producer** is recorded in the machine-readable stale-race record:
`stale_producer_miner_ids`, `stale_block_ids`, `stale_candidate_identities`,
`stale_discovery_times` (and one delivery-delay record per competitor). No blocks are
collapsed. `stale_block_ids` are globally unique (`stale-<block>-m<miner>`).

A generation with **no** accepted block reports `actual_proposal_miner_count = 0`,
`actual_competitor_miner_count = 0`, `stale_block_count = 0`.

## 3. Actual vs potential taxonomy (Section 3)

- `distinct_potential_finder_miner_count` — miners with an earliest reachable solution.
- `potential_competitor_miner_count` — distinct non-winning miners with a **distinct**
  candidate identity (B1's identical-header finders ⇒ 0).
- `actual_*` — realised only **after** the stale-race test above.

`actual_proposal_miner_count` is **never** `len(discoveries)`; it is `1 +` the number of
admitted stale producers.

## 4. Non-integration (Section 2)

The race's extra work is reported separately and **never** folded into primary metrics:

| Field | Meaning |
|-------|---------|
| `stale_race_candidate_evaluations` | Σ over producers of candidates evaluated beyond `winner_time` |
| `stale_race_active_time_s` | Σ over producers of `discovery_time − winner_time` |
| `stale_race_energy_not_integrated` | always `True` |
| `main_block_propagation_message_count` / `_bytes` | winner → every other active miner (integrated coordination) |
| `stale_block_propagation_message_count` / `_bytes` | one broadcast **per admitted stale** (separate; may exceed main) |

`total_candidate_evaluations == distinct + duplicate` holds exactly and excludes the
stale-race extras (test 8).

## 5. Denominators and deprecated aliases (Section 8)

Canonical, `single_height_`-prefixed:

- `single_height_stales_per_accepted_block = stale_block_count / accepted_blocks`
- `single_height_stale_fraction_of_valid_proposals = stale_block_count / (accepted + stale_block_count)`

Deprecated aliases retained for continuity, each mapped explicitly in
`deprecated_stale_alias_map`:

| Deprecated | Canonical target |
|-----------|------------------|
| `legitimate_stale_block_count`, `stale_blocks`, `legitimate_stale_count` | `single_height_stale_block_count` |
| `stales_per_accepted_block`, `legitimate_stale_rate` | `single_height_stales_per_accepted_block` |
| `stale_fraction_of_all_valid_blocks` | `single_height_stale_fraction_of_valid_proposals` |

`reconcile_stale_diagnostic` verifies, on every validation run: per-height count
identities, `actual_proposal == 1 + stales`, unique producer ids, range
`0..N_active-1`, the boolean-indicator identity, zero taxonomy on no-block heights,
the run-level sum, alias equality, and the not-integrated flag.
