# Stage 5B1A — Coordination Message & Byte Schema

Schema: `STAGE_05B1A_COORDINATION_SCHEMA.json`
Engine: `scenario_engine.py` · Tests: `test_stage5b1a_coord.py` (30–34)

Refines the Stage-5B1 single `bytes = messages × 1 MB` assumption into **five
separately-accounted message categories**. Only genuinely-simulated traffic carries
bytes; abstract protocol operations are counted but never assigned fabricated bytes.

## 1. Categories

| Category | `*_message_count` | `*_bytes` |
|----------|-------------------|-----------|
| `block_propagation` | simulated: `(active−1)` per accepted block | **configured** block size (`block_size_bytes`, default 1 MB) |
| `transaction_reconciliation` | abstract: 1 per accepted block (common-template) | `null` (size not configured) |
| `template_announcement` | abstract: 1 per template generation (common-template) | `null` |
| `nonce_allocation` | abstract: 1 per template generation (disjoint) | `null` |
| `registration` | abstract: 1 per active miner (common-template) | `null` |

## 2. Rules (all tested)

1. **Block-propagation bytes use the configured block size** — `bytes = count ×
   block_size_bytes`; passing `block_size_bytes = 2 MB` doubles them (test 30).
2. **Control-message bytes are `null`** — their sizes are not configured, so they
   are declared explicitly unknown, never fabricated (test 32).
3. **Abstract agreement operations get no simulated bytes.** The counts
   `abstract_template_agreement_operations`,
   `abstract_transaction_reconciliation_operations` are preserved, and
   `unimplemented_agreement_energy_kwh = null` (test 33). A break-even analysis can
   later assign a *separately-labelled analytical* byte/energy assumption; the raw
   record assigns none.
4. **Categories are separate counters** (test 31), not one undifferentiated total.
5. Legacy counters preserved for back-compat: `coord_block_propagation_*`,
   `coord_template_refresh_count` (== `exhausted_rounds`),
   `coord_nonce_allocation_event_count`.

## 3. Break-even readiness

The record provides, per run, the **volume** of every coordination category (counts)
and the **only** physically-grounded byte figure (block propagation). A later
break-even table can multiply the abstract counts by candidate control-message sizes
and candidate per-operation energies **as explicit assumptions**, without any
fabricated joules entering the measured dataset. `coordination_energy_kwh = 0` and
`coordination_energy_lower_bound_kwh = 0` remain the explicit idealized lower bound.
