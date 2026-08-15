# Stage 8X-ND — Results Report

**Concept tested (verbatim):** every conventional PoW miner independently uses
the same numerical nonce set 0…2^32−1 with independent headers, versus PoCol
partitioning that same numerical nonce set among miners on a common template
with post-range low power. Exact-input duplication is secondary here and never
redefines the question.

**Matrix:** 5 N × {ND-PW, ND-PW-OFFSET (secondary), ND-PC} × 30 fresh paired
seeds = **450 physical runs** + 150 derived ND-PC-NOLP energy-policy
observations of the ND-PC trajectories. All complete; zero identity
violations; α accounting-only. Theory report frozen before execution;
**40/40 theory-vs-simulation checks passed** (Table ND-N).

## 1. Nonce-domain structure (H-ND1, H-ND2, H-ND3 — all verified)

* **ND-PW:** |D_i| = 2^32 for every miner (structural, instrumented). Each
  miner completed 5.4482e8 full-domain sweeps per run (= T·h/2^32, exact),
  renewing its header after every sweep (header renewals = sweeps, counted).
  Run-scope U_nonce = 2^32 with cross-miner m_max = N: every numerical value
  used by every miner. ρ_nonce ≈ 1 − 2^32/C (saturated); ρ_exact = 0
  (secondary): distinct headers make equal nonce values distinct candidates.
* **ND-PC:** |R_i| = ⌊2^32/N⌋ or ⌈·⌉ (42 949 673 … 8 589 935 nonces), tiling
  0…2^32−1 exactly, zero overlap. Cross-miner nonce overlap within epochs = 0
  (m_max = 1). Each miner sweeps only its range: range sweep time 183.55 ns
  (N=100) → 36.71 ns (N=500); the common template renews 3.269e9·(N/100)
  times per 600 s.

## 2. Timing and low-power (RQ-ND3/4, H-ND4; Tables ND-D/F)

The full domain takes **18.355 µs** per miner; a PoCol range takes
**37–184 ns**. Because the fleet is homogeneous and ranges differ by ≤1 nonce,
all miners finish within one tick (4.27 fs) of each other, and the coordinated
domain is then exhausted — a new epoch begins immediately. Measured low-power
residency is exactly the straggler gap:

| N | F_low measured (= predicted) |
|---|---|
| 100 | 9.313e-10 |
| 200 | 2.421e-8 |
| 300 | 2.421e-8 |
| 400 | 7.078e-8 |
| 500 | 4.750e-8 |

H-ND4 confirmed in sign — ND-PC's active time is less than ND-PC-NOLP's by
exactly this residency — and **Outcome D confirmed in magnitude: the true
32-bit domain is exhausted far too quickly at S21 Pro rates for material
low-power residency.**

## 3. Energy (RQ-ND5, H-ND5; Table ND-G)

E(ND-PW) = E(ND-PW-OFFSET) = E(ND-PC-NOLP) = N·3510·T exactly (975–4875 kWh
per run). ND-PC saving vs ND-PW = F_low·(1−α): **9.3e-10 … 7.1e-8 at α = 0**
(≈ 0.003–0.3 J of a megawatt-hour-scale run), half that at α = 0.5.
ND-PC-NOLP saving = 0 exactly in all 150 observations — **partitioning alone
moves no energy (Outcome C); the entire (negligible) saving is the low-power
policy pricing the straggler gap (H-ND5: energy is P·t, never nonce
organization).**

## 4. Blocks and latency (RQ-ND6, H-ND6; Tables ND-H/I/N)

The §29 validity check governs: N same-valued nonce evaluations under N
distinct headers are N independent trials, so ND-PW's trial rate is N·h.
ND-PC's disjoint ranges under an N×-faster common-template renewal also
deliver N·h (TQ4). Measured: **paired block retention = 1.0000 in every one of
150 ND-PC seeds** (pooled 2660 vs 2660 blocks); latency ratio 1.0000 (mean,
median and P95 intervals coincide); ND-PW pooled mean interval 532.0 s
(horizon-truncated conditional mean of the 600 s process; blocks/run 17.7 vs
16.67 expected, within the preregistered 10 %). **Partitioning caused no
block-production penalty — and no gain.** Outcome E did NOT occur: PoCol does
not reduce total hash trials, because template renewal restores the trials
that domain sharing would otherwise forfeit.

## 5. Energy per block and the §45 criterion (Tables ND-J/L)

Hashes per accepted block and energy per accepted block are identical across
arms (EnergyPerBlockRatio = 1.000000). Applying the preregistered three-part
criterion — EnergySaving, BlockRetention, EnergyPerBlockRatio together:

> EnergySaving ≤ 7.1e-8, BlockRetention = 1.0000, EnergyPerBlockRatio =
> 1.000000. **There is no material energy effect in either direction. The
> organizational change is service-neutral and energy-neutral.**

## 6. Comparison with previous experiments (§43)

* **Stage 8X** measured the same fixed-ASIC low-power mechanism on a 600-s
  candidate-index domain (F_low ≈ 0.002, saving ≈ 0.2 %); Stage 8X-ND shows
  that on the true 32-bit nonce domain the residency shrinks by five orders of
  magnitude because sweeps complete in nanoseconds.
* **Stage 8X-NR** established the metric distinction (nonce-value reuse ≠
  exact-input duplication) that ND uses: ND-PW has total nonce-value sharing
  (m_max = N) with zero exact duplication.
* **Stage 8X-E50** used a same-template baseline, where uncoordinated search
  wastes (N−1)/N and PoCol's coordination recovers up to 90 % energy. Stage
  8X-ND deliberately keeps independent PoW headers — and shows that against
  that (realistic) baseline the recoverable waste is zero.

Together: **PoCol's nonce-domain organization is a coordination property whose
energy value exists only when a shared template makes uncoordinated search
redundant; against independent-header PoW it is energy-neutral and
service-neutral.**

## 7. Outcome classification (§40)

**Outcome D** (dominant): low-power residency is extremely small because the
true 32-bit domain is exhausted in nanoseconds at modern ASIC rates — a valid
and central physical result. **Outcome C** (concurrent): partitioning changes
nonce-domain utilization (cross-miner overlap 0 vs m_max = N) but not energy
unless low-power time exists to price. Outcomes A, B, E did not occur.
