# Stage 6 — Confirmatory Results

Confirmatory hypotheses H1, H3, H4, H5, H6, H8 (H2 → accounting invariant A1; H7 →
secondary diagnostic). Seed-matched paired inference; effect in scientific units first;
Holm within each family; α = 0.05. Machine-readable: `confirmatory_effects.csv`,
`models/confirmatory_results.json`. Permutation p is floored at 1/(10,000+1) ≈ 1e-4.

## A1 — Accounting invariant (verified by identity)

Across **1,140** continuous full-participation runs, `total_energy_kwh` equals the anchor
`P_total·T = 8.420833333 kWh`; max relative deviation **3.6e-16** (≪ 1e-6 tolerance).
Independent of miner count and search discipline. **Confirmed as a deterministic identity**
— not an empirical superiority claim. Search discipline changes coverage and
energy-per-accepted-block, never total energy. (`fig02`, `table07`.)

## H1 — Duplicate coverage: B1 > B2 > B3/C1 — SUPPORTED

Paired (150 pairs each, pooled over 5 miner counts):

| Contrast | mean Δ (rate) | HL Δ | 95% CI | Holm p | note |
|----------|--------------:|-----:|--------|-------:|------|
| B1 − B2 | +0.395 | +0.392 | [0.374, 0.416] | 3e-4 | stochastic |
| B2 − B3/C1 | +0.600 | +0.603 | [0.579, 0.621] | 3e-4 | stochastic |
| B1 − B3/C1 | +0.995 | +0.996 | [0.995, 0.996] | — | design-deterministic |

Ordering holds; direction met for all three; the two stochastic contrasts survive Holm.
**Bounded wording:** duplication ordering applies under an immutable common template and
disjoint assigned ranges; the exact-zero B3/C1 duplication does **not** generalize to
independently changing real-world headers. (`fig01`, `table08`.)

## H3 — C2 idle energy decomposition — SUPPORTED (identity)

`active_energy + idle_energy + coordination_energy = total_energy` exactly (max residual
0 kWh across all 570 C2 runs). Under **homogeneous + equal** ranges the idle policy never
activates (max idle time 0 s for every `idle_power_ratio`), so the saving is **exactly 0**
and total energy = anchor. Idle-driven savings appear only under **heterogeneity-induced
early completion** (H5 C2 equal: mean saving +3.38 kWh at N=100, +3.81 kWh at N=500).
The saving equals `Σ idle_time·(P_active − P_idle)`; energy reduction is attributable to
reduced **active power-time**, never to partitioning. (`fig05`, `table07`.)

## H4 — Homogeneous completion symmetry — SUPPORTED

With homogeneous rates and equal ranges, `completion_time_std_s` is exactly 0 (max 0.0
over all homogeneous-equal runs) and C2 `total_idle_time_s` is exactly 0 → post-range
idle opportunity = 0. (`fig03` context, `descriptive_long.csv`.)

## H5 — Heterogeneity & allocation — SUPPORTED (fairness) + documented TRADE-OFF (energy)

Seed-matched weighted vs equal (hetero_moderate; 30 pairs per config; Holm within H5):

- **Completion dispersion** (`completion_time_std_s`): weighted − equal ≈ −769 s (B3/C1
  N=100), −800 s (N=500); Holm p 8e-4; CI excludes 0. Weighted drives dispersion to ~0.
- **C2 idle** (`total_idle_time_s`): weighted − equal ≈ −3.87e5 s (N=100), −2.23e6 s
  (N=500); Holm p 8e-4. Weighted removes idle.
- **C2 energy** (`total_energy_kwh`, no preregistered direction): weighted − equal
  **+3.38 / +3.81 kWh** — weighted **removes** the idle-driven saving, returning energy to
  the anchor.
- On continuous B3/C1 there is no idle to remove and energy is invariant either way.

Weighted allocation improves fairness (completion symmetry, no idle) but **eliminates the
C2 idle energy saving** — a trade-off, not guaranteed PoCol superiority. (`fig03`, `fig04`,
`table09`.)

## H6 — Inactive miners — SUPPORTED (primary directions); one INCONCLUSIVE sub-claim

Seed-matched vs the inactive=0 baseline (30 pairs per config; Holm within H6):

- `inactive_domain` (unsearched) ↑ with inactive fraction — design-deterministic.
- `effective_block_interval_s` ↑ (e.g. +52.7 s at 0.05 → +210–285 s at 0.30; Holm p
  2.4e-3–7.8e-3, CI excludes 0) — SUPPORTED.
- `accepted_blocks` ↓ (−1.1 → −5.3 across levels; Holm p 2.4e-3–7.8e-3) — SUPPORTED.
- `total_energy_kwh` ↓ (−0.42 → −2.53 kWh) — design-deterministic (fewer active miners).
- `exhausted_rounds` ↑ directionally but small; survives Holm only at the highest
  inactive fraction — mixed.
- `energy_per_accepted_block_kwh`: the preregistered "may ↑" sub-claim is **INCONCLUSIVE**
  — the paired effect is small and its CI includes 0 (energy falls roughly in proportion
  to blocks).

Energy reduction is attributable to **reduced participation**, not to partitioning.
(`fig06`, `table10`.)

## H8 — Finite-domain μ — SUPPORTED (exhaustion & refresh); block-interval INCONCLUSIVE

Seed-matched vs the μ=2.0 baseline (30 pairs per config; Holm within H8):

- `exhausted_rounds` ↑ (+6.9–7.1 at μ=1.0; +23.1 at μ=0.5; Holm p 1.6e-3) — SUPPORTED.
- template refreshes (`coord_template_refresh_count`, `template_generations`) ↑ (Holm p
  1.6e-3) — SUPPORTED.
- `effective_block_interval_s` ↑ in the expected direction but not decisive (Holm p
  0.63–0.77, wide CI crossing 0) — **INCONCLUSIVE**.

Smaller μ increases range exhaustion and template refreshes monotonically; the realized
block interval trends up but is noisy. (`fig07`.)

## Multiplicity families

H1 (3 tests), H5 (12), H6 (24 stochastic), H8 (16). Raw + Holm-adjusted p, family sizes,
and decisions in `confirmatory_effects.csv` / `table06_robustness.csv`. Deterministic
identities are excluded from p-families and reported as identities.
