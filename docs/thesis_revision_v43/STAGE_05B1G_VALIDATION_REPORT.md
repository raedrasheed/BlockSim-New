# Stage 5B1G — Validation Report (Section 10)

Runner: `experiments/thesis_revision_v43/validate_5b1g.py`
Data: `results/thesis_revision_v43/stage_05b1g/validation_report_5b1g.json`,
`STAGE_05B1G_VALIDATION_RESULTS.json`

**The 1 890-run matrix is NOT executed.** Bounded validation only.

## 1. Coverage

**34 runs** (hard cap 150): scenarios B0, B1, B2, B3/C1, C2; homogeneous and
heterogeneous rates; equal and weighted allocation; propagation delays
**0, 0.42, 5, 30, 60 s**; one- and multiple-solution templates (μ = 0.5, 1, 3, 5)
including several positions owned by one miner; B2 overlapping starts and low-μ
domain **exhaustion**; inactive fractions 5/15/30 %; a controlled small-domain
high-delay regime producing **many distinct stale producers per height**; and a
long-interval partial-cutoff run.

| Regime hit | |
|-----------|:--:|
| non-zero single-height stales | ✅ |
| ≥2 distinct stale producers at one height | ✅ |
| ≥3 distinct stale producers at one height | ✅ |
| zero-delay ⇒ zero stales | ✅ |
| all delay levels {0, 0.42, 5, 30, 60} | ✅ |
| partial generation at cutoff | ✅ |
| exact B2 domain exhaustion | ✅ |
| multiple positions per miner | ✅ |
| inactive ranges | ✅ |

The controlled multi-producer regime (B3/C1, seed 5, 20 miners, 2000 h/s, 1 s
interval, 60 s mean delay) reaches **10 distinct stale producers at a single height**;
across its heights 7 377 have ≥2 and 4 997 have ≥3 — direct evidence that there is
**no** global one-stale-per-height cap.

## 2. Ten reconciliation families — all pass on every run

| Family | Definition |
|--------|-----------|
| **energy** | `total == active + idle + coordination` |
| **candidates** | `total == distinct + duplicate` (exact integer; excludes stale-race extras) |
| **per_miner_generation** | `Σ per-generation candidates == network total` (disjoint) |
| **template_chronology** | `end ≥ start`; `Σ duration == 10 000 s` |
| **parent_chain** | genesis first; each block → previous accepted; no self-parent |
| **block_proposals** | `#blocks == accepted`; `actual_proposal == 1 + stale_block_count` per accepted height |
| **stale_diagnostic** | `reconcile_stale_diagnostic` — counts identical, `actual_proposal = 1 + stales`, unique producer ids, range `0..N_active-1`, indicator = `count>0`, no-block zero, run sum, alias equality, energy-not-integrated |
| **solution_positions** | `active + inactive positions == total`; finder ≤ positions (disjoint) |
| **b2_exhaustion** | every B2 exhaustion generation `exact_exhaustion_verified` with `coverage_before < S = coverage_at` |
| **delay_stream** | every recorded delivery delay reconstructs from its stored identity |

`all_reconciliations_pass = true`.

## 3. Corrections confirmed

- One stale per **miner** per height; multiple distinct miners may stale at one
  height; `stale_block_count ∈ 0..N_active-1`; no global cap.
- Per-delivery deterministic delay keyed on
  `(seed, generation, parent, winner, recipient)` — order-independent, recipient-independent,
  reproducible; zero mean ⇒ zero delay ⇒ zero stales.
- `actual_proposal = 1 + all stales`, `actual_competitor = stale producers`,
  `potential ≥ actual`; no-block heights zero.
- Solution **positions** counted before reduction to one proposal per miner; positions
  never reported as finder miners.
- Exact rational B2 exhaustion with a coverage proof; no six-decimal rounding.
- Stale-race evaluations/active-time/energy reported separately and never integrated;
  main- vs stale-block propagation counted separately.

## 4. Full test suite

`python3 -m pytest tests/ -q` → **423 passed** (50 new Stage 5B1G tests, all prior
suites green). Thesis DOCX/PDF byte-identical (SHA-256 unchanged).
