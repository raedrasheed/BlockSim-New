# Stage 5B1G — Completion Report

**Stale-Race Diagnostic Isolation, Delay-Stream Correction, Solution-Taxonomy
Correction, and Exact B2 Exhaustion Closure.**

Engine `scenario_engine.py` → `5b1g.1`; output schema `5b1g.1`. Matrix regenerated
(1 890 runs, 63 × 30 unchanged). Full suite **423 passed**. Thesis DOCX/PDF
byte-identical. The 1 890-run matrix is **not** executed; Stage 5B2 is **not** begun.

## Corrected stale model (per the mid-stage correction)

Each non-winning miner may produce **at most one** stale per height; **multiple
distinct miners may each produce a stale at the same height**, so
`stale_block_count ∈ 0 .. N_active-1`. There is **no** global one-stale-per-height
cap. `stale_block_count == actual_stale_producer_miner_count == #stale_block_ids ==
actual_competitor_miner_count`; `actual_proposal_miner_count = 1 + stale_block_count`.
`height_has_any_stale` is a boolean indicator only, never a substitute for the count.
One entry per producer is recorded in `stale_producer_miner_ids`, `stale_block_ids`,
`stale_candidate_identities`, `stale_discovery_times`, and the per-producer
delivery/stale records.

## 15 deliverables

| # | Deliverable |
|---|-------------|
| 1 | `STAGE_05B1G_STALE_DIAGNOSTIC_SCOPE.md` (§1,§2,§3,§8) |
| 2 | `STAGE_05B1G_DELAY_STREAM_AUDIT.md` (§4) |
| 3 | `STAGE_05B1G_SOLUTION_FINDER_TAXONOMY.md` (§6) |
| 4 | `STAGE_05B1G_B2_EXHAUSTION_CLOSURE.md` (§7) |
| 5 | `STAGE_05B1G_PREREGISTRATION_AMENDMENT.md` (§1; + marked amendment in `STAGE_05A_PREREGISTRATION.md`) |
| 6 | `STAGE_05B1G_VALIDATION_REPORT.md` (§10) |
| 7 | `STAGE_05B1G_FINAL_MATRIX.csv` (1 890 rows; SHA `84db950f…`) |
| 8 | `STAGE_05B1G_FREEZE_INPUTS.md` (§11) |
| 9 | `results/…/stage_05b1g/stale_race_and_delivery_delay_records_sample.json` (machine-readable delivery-delay + stale-race records) |
| 10 | `STAGE_05B1G_PER_MINER_GENERATION.md` + updated `schemas.PER_MINER_GENERATION_FIELDS` (§5) |
| 11 | `tests/thesis_revision_v43/stage5b1g/` (50 new tests, incl. the 8 correction tests) |
| 12 | `results/thesis_revision_v43/stage_05b1g/{raw,manifests,logs}/` |
| 13 | `STAGE_05B1G_HASH_GROUP_AUDIT.json` (63 × 30 audit) |
| 14 | `STAGE_05B1G_VALIDATION_RESULTS.json` |
| 15 | `results/…/stage_05b1g/manifests/freeze_input_manifest.json` (non-self-referential) + this report |

## 21 acceptance criteria

| # | Criterion | Evidence |
|---|-----------|----------|
| 1 | Stale model labelled `SINGLE_HEIGHT_STALE_RACE_DIAGNOSTIC`, secondary | scope doc §1; `single_height_stale_race_diagnostic=True` |
| 2 | Isolated from block interval, primary coverage, primary energy, next-height, forks | scope §1; regression test 42 (A1 = 8.420833333 kWh) |
| 3 | H7 → secondary diagnostic sensitivity; no thesis prose edited | prereg amendment; `STAGE_05A_PREREGISTRATION.md` §5 |
| 4 | Recipient-specific `received_winner_time`; stale iff discover before receipt + distinct id + distinct miner | `_resolve_stale_race`; tests 2–4, 16 |
| 5 | One stale per miner per height; many miners may stale one height; range `0..N_active-1`; no global cap | tests `two_/three_stale_producers`, `no_global_one_stale_cap`, `stale_count_within_active_bound` |
| 6 | `actual_stale_producer = actual_competitor`; `actual_proposal = 1 + stales`; `potential ≥ actual` | tests 4,5,6; `reconcile_stale_diagnostic` |
| 7 | No-block heights ⇒ zero taxonomy | test `no_block_zero_taxonomy` |
| 8 | Per-producer lists (ids, block ids, identities, discovery times), unique block ids | tests `stale_block_count_equals_…`, `multiple_stale_block_ids_are_unique` |
| 9 | Stale-race evaluations/active-time/energy separate, not integrated | test 8; `stale_race_energy_not_integrated=True` |
| 10 | Per-delivery deterministic stream from `(seed,gen,parent,winner,recipient)` | delay-stream doc; tests 11,15,17 |
| 11 | Order-independent; adding recipient stable; per-recipient independent | tests 12,13,14 |
| 12 | First unused delay draw + later recomputation removed; race resolved once | `_sim_*` (no `r_delay`); single `_record_stale_race` call |
| 13 | Zero mean ⇒ zero delay ⇒ zero stale | test `zero_delay_produces_no_stale`, test 16 |
| 14 | Per-miner-generation stale fields incl. lifecycle `stop_reason` | per-miner-generation doc; tests 18–22 |
| 15 | Winner row `received_winner_time_s = winner_time`, `solution_found` | test 19 |
| 16 | Main vs stale propagation counted separately | test 23 |
| 17 | All positions counted before reduction; active+inactive = total; positions ≠ finders | solution-taxonomy doc; tests 24–26 |
| 18 | One potential proposal per miner; actual proposals only after stale test | scope §3; `_record_stale_race` |
| 19 | Exact B2 exhaustion via Fraction events; proof `cov(t_prev)<S=cov(t_ex)`; no 6-dp rounding | B2 doc; tests 28–34 |
| 20 | Ten-family reconciliation on ≤150 validation runs incl. ≥2 producers case | validation report; `validate_5b1g.py` (34 runs) |
| 21 | Engine bumped, matrix regenerated 63×30, freezes 1–4 preserved, freeze-4 invalid, freeze-5 created, matrix not executed, one commit | freeze doc; `build_matrix_5b1g`; freeze-branch step below |

## Freeze #5

Corrective commit SHA (recorded externally, non-self-referential) → remote branch
`thesis-v43-stage5b2-freeze-5`. Preserved unchanged: `…-freeze-1` (`c0ff48e`),
`…-2` (`03591d8`), `…-3` (`069a0c5`), `…-4` (`8cb490c`, **invalid for execution**).

**Conclusion: `READY_FOR_STAGE_5B2_FREEZE_5`.** Work stops before Stage 5B2.
