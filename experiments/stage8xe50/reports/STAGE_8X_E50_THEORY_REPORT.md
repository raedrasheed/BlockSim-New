# Stage 8X-E50 — Theory Report (written before Pilot and primary execution)

Purpose: preregister the analytical expectations for every primary quantity so
that no parameter can be tuned toward a 50 % result after data are seen. All
derivations use the frozen hardware profile (S21 Pro: h = 2.34e14 evals/s,
P = 3510 W per unit), the explicit 32-bit domain S = 2^32, the fixed-per-miner
difficulty q_N = 1/(N·h·600), and T = 10 000 s.

## 1. The matched template-renewal rule (the load-bearing definition)

One rule for all arms: **a template epoch ends when every ACTIVE miner has
completed its assigned traversal for that epoch** (or a block ends the round).

* E50-MT100: the assignment of an uncoordinated miner is the full 2^32 domain
  (from its own offset). Epoch length = 2^32 ticks = 18.355 µs.
* E50-PC(A): the assignment is the miner's own disjoint range,
  len_i ∈ {⌊S/N⌋, ⌈S/N⌉}. Epoch length = ⌈S/N⌉ ticks (the straggler tick of
  short-range miners is post-range low power, as in Stage 8X-NR).
* E50-CONV100 (external reference): per-miner template, full-domain sweep,
  renewal per miner — identical to Stage 8X-NR's CONV-OFFSET.

The single intended difference between MT100 and PC(A) is uncoordinated
overlapping search vs coordinated disjoint search. The consequence — PoCol
turns templates over ~N× faster because its per-epoch assignment is N× smaller
— **is** the coordination effect, not an artifact: fresh templates are what
convert evaluations into distinct inputs.

## 2. Unique-coverage rates (RQ-E50-1)

A common template epoch contains exactly S distinct candidate inputs, however
many miners sweep it (§25 saturation).

| arm | distinct inputs per epoch | epoch ticks | unique-coverage rate |
|---|---|---|---|
| MT100 | S | S | **h** (one miner's worth) |
| PC(A), k = ⌈A·N⌉ active | Σ active len ≈ k·S/N | ⌈S/N⌉ | **k·h** |
| CONV100 | N·S (per-miner templates) | S | **N·h** |

Predicted run totals: U_MT100 = h·T = 2.340e18 (independent of N);
U_PC(A) = k·h·T; U_CONV = N·h·T.

**Predicted UniqueCoverageRetention = U_PC/U_MT = k = A·N.** Even one active
miner (k = 1) matches 100 % of MT100's unique coverage; every tested fraction
(k ≥ 10) exceeds it by an order of magnitude or more. The ≥ 0.95 coverage
constraint is therefore predicted feasible at ALL tested fractions, including
A = 10 % — the low fractions are retained as preregistered diagnostics anyway.

MT100 exact duplication: ρ_exact = (N−1)/N = 0.990…0.998 (measured in Stage
8X-NR and re-measured here). CONV100: ρ_exact = 0. PC: ρ_exact = 0, verified.

## 3. Block production and latency (constraints §18)

Blocks arrive at rate q × (unique-coverage rate):

| arm | block rate (s⁻¹) | E[blocks per 10 000 s run] |
|---|---|---|
| MT100 | h·q = 1/(600N) | 16.67/N = 0.167…0.033 |
| PC(A) | k·h·q = k/(600N) | 16.67·k/N = 16.67·A |
| CONV100 | N·h·q = 1/600 | 16.67 |

**Predicted BlockRetention (pooled) = k = A·N ≥ 10 at every tested point** —
PoCol out-produces MT100 at every fraction, because MT100 wastes (N−1)/N of its
evaluations on duplicates. Predicted MedianLatencyRatio ≈ 1/k ≤ 0.1 ≪ 1.20.
Per-seed paired block ratios will often be NA (MT100 has 0 blocks in most
runs — P(≥1 block) = 1−e^(−16.67/N) ≈ 0.15 at N = 100); retention is therefore
evaluated pooled per cell, with per-seed ratios reported where defined
(preregistered NA rule, test 18).

## 4. Energy (RQ-E50-2/3)

With sliding-window rotation (§ methods), every miner's duty fraction is
exactly k/N, so aggregate active miner-time = k·T and
F_low = (N−k)/N + O(1e-8) straggler. Hence

```
E_PC(α) = P·T·[k + α(N−k)]      E_MT100 = P·T·N
EnergySaving(α) = (1 − k/N)(1 − α)
```

Predicted savings by fraction (exact, up to ~1e-8):

| A | LP0 | LP10 | LP25 | LP50 |
|---|---|---|---|---|
| 10 % | 0.900 | 0.810 | 0.675 | **0.450** |
| 20 % | 0.800 | 0.720 | 0.600 | 0.400 |
| 30 % | 0.700 | 0.630 | 0.525 | 0.350 |
| 40 % | 0.600 | 0.540 | 0.450 | 0.300 |
| 50 % | 0.500 | 0.450 | 0.375 | 0.250 |
| 60 % | 0.400 | 0.360 | 0.300 | 0.200 |
| 80 % | 0.200 | 0.180 | 0.150 | 0.100 |
| 100 % | ~0 | ~0 | ~0 | ~0 |

## 5. Predicted feasibility and headline quantities

All (N, A) points are predicted feasible (coverage k ≥ 1, blocks k ≥ 1,
latency 1/k ≤ 1). Therefore:

* **MaxEnergySaving under constraints** = at A = 10 %: 90.0 % (LP0), 81.0 %
  (LP10), 67.5 % (LP25), 45.0 % (LP50).
* **Predicted answer to RQ-E50-3:** yes for α ∈ {0, 0.10, 0.25}; **no for
  α = 0.50** — the best tested point reaches only 45.0 % because
  (1−A)(1−α) ≤ 0.45 for A ≥ 0.10.
* **MaxBlockRetentionAt50:** among points with saving ≥ 50 %: LP0 → A = 50 %
  (retention N/2×), LP10 → A = 40 %, LP25 → A = 30 %, LP50 → none (NA).

## 6. Energy per accepted block — the mandatory sanity anchor (§41)

```
E_block(PC, α=0)  = P·T·k / (16.67·k/N)  = P·T·N/16.67
E_block(CONV100)  = P·T·N / 16.67        (identical)
E_block(MT100)    = P·T·N / (16.67/N)    = N × the above
```

**PoCol's disjoint coordination restores exactly conventional PoW's energy per
block; it cannot beat it.** Every joule PoCol saves against MT100 comes from
duplication that conventional independent-template PoW never performs
(ρ_exact,CONV = 0, established in Stage 8X-NR). The predicted >50 % savings are
therefore comparator-specific by construction, and the final report must say so
(§41/§42) — this is preregistered here, before any run.

## 7. Causal chain to be measured (§44)

same-template overlapping search → ρ_exact = (N−1)/N (measured) → PoCol
preserves unique coverage with k ≪ N active (U ratio = k, measured) → low-power
miner-time F_low = 1−k/N (measured) → E saving = (1−k/N)(1−α) (measured).
Each arrow is a separate measured table; energy is never inferred alone.

## 8. What the simulation adds beyond this theory

The stochastic quantities: realized block counts and intervals (few-event
Poisson at MT100's rate — the pooled-retention and NA behaviour must be
demonstrated, not assumed), truncation effects at the horizon, the exact
straggler corrections, per-seed paired distributions, and verification that
every deterministic prediction above is reproduced by the engine's exact
integer accounting. Any deviation beyond stated tolerances fails the run.
