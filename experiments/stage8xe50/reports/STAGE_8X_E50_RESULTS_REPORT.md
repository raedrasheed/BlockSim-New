# Stage 8X-E50 — Results Report

**Comparator discipline (read first):** every number below compares PoCol
against **E50-MT100, the same-template competitive PoW control** — a
deliberately artificial baseline that holds the template common to isolate
search coordination. It is **not Bitcoin mainnet and not conventional
independent-template PoW**. The conventional reference E50-CONV100 is reported
separately (§6) and the mandatory §41 statement appears in §7.

**Matrix:** 5 N × 10 arms × 30 fresh paired seeds = **1500 physical runs**,
T = 10 000 s, S21 Pro fleet, one D_N per N for all arms (never retargeted for
reduced active sets). 50 cells × 30 seeds complete; zero identity violations;
α-cases derived from state-time (no per-α trajectories). Pilot excluded.

## 1. The causal chain (§44), measured link by link

1. **Same-template overlapping search → large exact-input duplication.**
   MT100 ρ_exact = 0.99000/0.99500/0.99667/0.99750/0.99800 at N = 100…500 —
   exactly (N−1)/N (Table E50-B). Its unique-coverage rate is h = 2.34e14
   inputs/s — one miner's worth — at every N (U = 2.3400e18 per run).
2. **PoCol preserves unique coverage with fewer active miners.**
   U_PC = k·h·T exactly; UniqueCoverageRetention = k = A·N at every point
   (Table E50-D): even PC10 delivers 10×…50× MT100's unique coverage;
   the ≥0.95 constraint is met by 30/30 seeds at every (N, A). ρ_exact,PC = 0
   in all 1200 PoCol runs (Table E50-C).
3. **Fewer active miners → low-power miner-time.** F_low = 1 − k/N exactly
   (0.900 at PC10 … 0.000 at PC100), duty k/N per miner, Jain index 1.0000
   (Tables E50-I/J).
4. **Low-power time → lower energy.** Saving = (1 − k/N)(1 − α), measured to
   1e-8 of prediction at all 40 (N, A) points × 4 α (Table E50-E).

## 2. Service (Tables E50-F/G)

Pooled accepted blocks (30 runs per cell): MT100 produced 3/2/1/1/1 blocks at
N = 100…500 (its rate is 1/(600N) s⁻¹ — the duplication cost); PoCol produced
50·(k/10) blocks — e.g. PC10: 50, PC50: 250, PC100: 508 = CONV100 exactly.
**Pooled BlockRetention = 16.7×…250× ≥ 0.90 everywhere.** Per-seed block ratios
are NA in most seeds (MT100 has zero blocks in ≥27/30 runs per cell — reported,
not imputed). Pooled median-latency ratios: 0.24–1.04, all ≤ 1.20; MT100's
sparse denominators (1–3 runs with blocks) are flagged per cell in Table E50-G.

## 3. Preregistered feasibility (Table E50-K, Fig 14)

**40/40 (N, A) points feasible** (coverage ≥ 0.95 ✓, pooled blocks ≥ 0.90 ✓,
latency ≤ 1.20 ✓). No constraint ever binds; the coverage constraint is
exceeded k-fold, not marginally.

## 4. Headline quantities (Tables E50-L/M)

| α | MaxEnergySaving (feasible) | at | > 50 %? | MaxBlockRetentionAt50 |
|---|---|---|---|---|
| LP0 (α=0) | **90.00 %** | PC10, any N | **yes** | 250× (PC50) |
| LP10 | **81.00 %** | PC10 | **yes** | 202× (PC40) |
| LP25 | **67.50 %** | PC10 | **yes** | 162× (PC30) |
| LP50 | **45.00 %** | PC10 | **no** | **NA — no scenario reaches 50 %** |

This is **Outcome A** of brief §40 for α ∈ {0, 0.10, 0.25} and **Outcome B**
for α = 0.50 (maximum 45.0 %: (1−A)(1−α) ≤ 0.45 for A ≥ 0.10; savings above
that at α = 0.5 would require A < 0.10, outside the frozen grid).

Approved wording instance (§42): *Under the controlled common-template
comparator, PoCol's disjoint search required substantially less simultaneously
active ASIC capacity to preserve comparable unique candidate coverage,
producing 90.0 % / 81.0 % / 67.5 % lower modeled electrical energy at
α = 0 / 0.10 / 0.25 while retaining ≥ 1670 % of accepted-block output.*

## 5. Energy per accepted block (Table E50-H, Fig 11)

E_block(PC, any A, α=0) = E_block(CONV100) = P·N·T/16.67 exactly; E_block(MT100)
is ~N× larger. PoCol's coordination **restores** conventional-PoW efficiency
per block; it does not surpass it. Total-energy saving and energy-per-block
tell the same story here because block retention rises with saving — there is
no scenario that saves energy while worsening energy per block.

## 6. Conventional reference E50-CONV100 (external, separate)

ρ_exact = 0 in all 150 CONV runs; 508 pooled blocks per N (16.9/run, ~600 s
intervals); U = C = N·h·T. **Relative to CONV100, PoCol at fraction A delivers
exactly fraction A of blocks for fraction A of energy** — no free energy.
The E50 savings exist because MT100 wastes (N−1)/N of its evaluations; CONV100
wastes none.

## 7. Mandatory boundary statement (§41)

Conventional independent-template PoW shows ExactDuplication ≈ 0 (here: exactly
0). **The E50 result therefore does NOT imply any comparable energy advantage
against conventional independent-template PoW.** The >50 % savings are valid
only against the same-template competitive PoW control, whose duplication
creates the coordination opportunity by construction.

## 8. Paired statistics (stage8xe50_paired_stats.csv)

Coverage retention and energy savings are deterministic given (N, A, α): per-
seed SDs are ≤ 1e-7 and CIs degenerate — magnitudes are reported and
hypothesis tests deliberately omitted. Block/latency per-seed ratios carry the
NA accounting of §2; pooled values are the preregistered basis of the filter.
