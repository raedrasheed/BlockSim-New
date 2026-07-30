# Stage 5B1G.1 — Validation Report (§7)

Runner: `experiments/thesis_revision_v43/validate_5b1g1.py`
Data: `results/thesis_revision_v43/stage_05b1g1/validation_report_5b1g1.json`,
`STAGE_05B1G1_VALIDATION_RESULTS.json`

**The 1 890-run matrix is NOT executed.** Bounded validation only.

## 1. Coverage — 22 runs (hard cap 50)

Scenarios B0, B1, B2, B3/C1, C2; homogeneous/heterogeneous rates; equal/weighted
allocation; propagation delays **0, 0.42, 5, 30, 60 s**. All required regimes hit:

| Regime | |
|--------|:--:|
| B1 same-identity deliveries (all recipients receive winner, no stale) | ✅ |
| B2 actual random start recorded | ✅ |
| B2 wraparound path provenance | ✅ |
| adversarial Fraction boundary (exact ≠ float) | ✅ |
| miner with no reachable solution still receives winner | ✅ |
| non-stale distinct-identity competitor receives winner | ✅ |
| multiple distinct stale producers at one height | ✅ |
| zero propagation delay ⇒ zero stales | ✅ |
| non-zero propagation delay | ✅ |

## 2. Eight reconciliation families — all pass on every run

| Family | Definition |
|--------|-----------|
| **network_generation_totals** | `Σ per-generation candidates == network total` (exact) |
| **exact_b2_candidates** | `total == distinct + duplicate` (exact integer) |
| **b2_paths** | B2 `last_evaluated_position == (start + c − 1) mod S`; real start recorded |
| **all_nonwinner_deliveries** | each accepted height has exactly `N_active − 1` delivery records (one per active non-winner) |
| **postwinner_separation** | `post_winner_energy_not_integrated`; `stale_race_* == post_winner_*`; `post_winner ≥ stale_producer_postwinner` |
| **primary_energy_invariant** | continuous full-participation `total_energy == 8.420833333 kWh`; else `total == active+idle+coord` |
| **delivery_stream** | every recorded delay reconstructs from its stored identity |
| **stale_diagnostic** | `reconcile_stale_diagnostic` (no cap; counts/ids consistent; range `0..N_active−1`) |

`all_reconciliations_pass = true`.

## 3. Adversarial boundary

`lengths_at_time_exact([49], 1/49, 100) == 1`, whereas `floor(49 · float(1/49)) == 0`.
The exact rational path is required and used throughout; the float path would
undercount by one candidate at this boundary.

## 4. Full test suite

`python3 -m pytest tests/ -q` → **444 passed** (21 new Stage 5B1G.1 tests; all prior
suites, including Stage 5B1G, green). Thesis DOCX/PDF byte-identical.
