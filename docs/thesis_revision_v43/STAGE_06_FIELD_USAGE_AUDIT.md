# Stage 6 — Field-Usage Audit

Confirms Stage 6 uses the frozen Stage-5B2 field authority
(`STAGE_05B2_FIELD_AUTHORITY_MAP.json`) and never uses deprecated / non-authoritative
fields for analytical claims. Enforced in code by `s6_common.CANON` /
`s6_common.FORBIDDEN_FIELDS` and by
`tests/test_stage6.py::test_forbidden_fields_not_in_descriptive_outcomes`.

## 1. Canonical fields used

| Purpose | Canonical field(s) used |
|---------|-------------------------|
| Finder miners | `distinct_potential_finder_miner_count` |
| Solution positions | `total_template_solution_position_count`, `active_range_solution_position_count`, `inactive_range_solution_position_count` |
| Candidates | `total_candidate_evaluations`, `distinct_candidate_identities`, `duplicate_evaluations`, `duplicate_evaluation_rate` |
| Stale diagnostic (secondary) | `single_height_stale_block_count`, `single_height_stales_per_accepted_block`, `single_height_stale_fraction_of_valid_proposals`, `actual_stale_producer_miner_count`, `actual_competitor_miner_count`, `actual_proposal_miner_count` |
| Post-winner diagnostic | `post_winner_candidate_evaluations`, `post_winner_active_time_s`, `stale_producer_postwinner_candidate_evaluations`, `stale_producer_postwinner_active_time_s` |
| Energy | `total_energy_kwh`, `active_energy_kwh`, `idle_energy_kwh`, `coordination_energy_kwh` |
| Timing / production | `accepted_blocks`, `effective_block_interval_s`, `completion_time_std_s`, `total_idle_time_s`, `exhausted_rounds`, `template_generations`, `coord_template_refresh_count` |
| Domain | `inactive_domain` (unsearched inactive range) |

Detailed range/search reconciliation uses the `per_miner_generation` bulk data
(archived on the bulk-data branch) where needed; summary-level analysis uses the
authoritative per-run `summary` table.

## 2. Fields explicitly NOT used as authoritative analytical outcomes

Per the field-authority map, these are excluded from analytical claims (and blocked in
`FORBIDDEN_FIELDS`):

- `discoverable_finder_count` — superseded by `distinct_potential_finder_miner_count`.
- `per_miner.unsearched_count`, `per_miner.remaining_unsearched` — bookkeeping, not
  authoritative outcomes.
- Deprecated stale aliases when canonical `single_height_*` fields exist:
  `legitimate_stale_block_count`, `legitimate_stale_count`, `legitimate_stale_rate`,
  `stale_block_count`, `stale_blocks`, `stales_per_accepted_block`,
  `stale_fraction_of_all_valid_blocks` (the summary carries a
  `deprecated_stale_alias_map` documenting these).

Solutions found in **inactive** ranges (`inactive_range_solution_position_count`) are
counted as diagnostic positions, **never** as discoverable accepted blocks (H6).

## 3. NA and denominator conventions

- Block-normalised fields carry explicit `*_na_reason` (e.g.
  `effective_block_interval_na_reason`) and are NA when `accepted_blocks=0`.
- The single-height stale rate denominator is accepted blocks (opportunities); for
  zero-observation delay levels an exact one-sided binomial / rule-of-three bound is used.

## 4. Verification

`test_forbidden_fields_not_in_descriptive_outcomes` and the analysis modules confirm no
forbidden field appears among descriptive or confirmatory outcomes. PASS.
