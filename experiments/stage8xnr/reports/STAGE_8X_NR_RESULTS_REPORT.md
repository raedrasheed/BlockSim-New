# Stage 8X-NR — Results Report

**Primary matrix:** N ∈ {100, 200, 300, 400, 500} × 5 arms × 30 fresh paired seeds
= **750 physical runs**, T = 10 000 s each, S21 Pro hardware (234 TH/s, 3510 W,
15 J/TH), one shared D_N per N. All 750 runs completed; 25 cells × 30 seeds audit
exact; zero identity violations. Energy α-cases are derived observations, so no
additional simulations were run for them. Pilot runs are excluded throughout.

Four quantities are carried separately in every table, as required:
**nonce-value reuse** ≠ **exact-input duplication** ≠ **physical work** ≠ **energy**.

## 1. Nonce-value reuse (Table NR-B, Figs 1–3)

**Round scope (primary scientific scope).** One S21 Pro sweeps all 2^32 nonce
values every 18.355 µs, so every active miner touches the entire domain millions
of times per round. For all four PoW arms:

| N | ρ_nonce (round, mean) | M_≥2 | m_max | mean pairwise O_ij |
|---|---|---|---|---|
| 100 | 0.999999996960 | 2^32 | 100 | 2^32 |
| 200 | 0.999999998480 | 2^32 | 200 | 2^32 |
| 300 | 0.999999998987 | 2^32 | 300 | 2^32 |
| 400 | 0.999999999240 | 2^32 | 400 | 2^32 |
| 500 | 0.999999999392 | 2^32 | 500 | 2^32 |

Every nonce value is used by **every** miner in every round (m_max = N), exactly
matching the analytic form 1 − 2^32/(N·h·Δ) per round (Table NR-J, error < 1e-9).
PoCol's round-scope ρ_nonce is numerically the same (its miners re-sweep their own
ranges across template epochs — repetition, not sharing) but its cross-miner
columns are **M_≥2 = 0, m_max = 1, O_ij = 0 in every round of all 150 PC runs** —
verified by interval intersection, not assumed.

**Template-epoch scope (the discriminating scope).**

| arm | ρ_nonce per epoch | cross-miner? |
|---|---|---|
| XNR-PW-CONV-* | 0 (a template epoch belongs to one miner) | reuse appears across miners at round scope |
| XNR-PW-MT-* | (N−1)/N: 0.9900 / 0.9950 / 0.9967 / 0.9975 / 0.9980 | yes, all N miners |
| XNR-PC | **0 exactly** (and exact-input 0) at all N | none — disjoint allocation verified |

**Sub-sweep window (traversal sensitivity, Table NR-I, Fig 6).** In the first
⌊S/2N⌋ ticks of each round, before saturation: zero-start ρ_nonce = (N−1)/N
(0.9900…0.9980, exact); random-offset ρ_nonce = 0.210–0.214 vs coverage-model
prediction 0.213 (within 5 %); mean pairwise overlap 108 995 vs W²/S = 115 292
(N=100, within 5 %) against 21 474 836 for zero-start (= W, every pair fully
overlapped). Paired t on ZERO−OFFSET: d_z ≈ 45, p ≈ 1e-30 — reported for
completeness; the practical magnitude (0.99 vs 0.21) is the finding. **At round
scope the two traversals are indistinguishable** (both saturated; all paired
differences exactly zero) — nonce-reuse conclusions must therefore always name
their scope, and zero-start results must not be generalized.

## 2. Exact-input duplication (Table NR-C, Fig 4)

| arm | ρ_exact (round & run scopes) | ρ_exact per epoch |
|---|---|---|
| XNR-PW-CONV-ZERO / -OFFSET | **0 exactly, every run** | 0 |
| XNR-PW-MT-ZERO / -OFFSET | ≈ (N−1)/N (0.9900…0.9980) | (N−1)/N exactly |
| XNR-PC | **0 exactly, every run** | 0 |

Conventional PoW: ρ_nonce ≈ 1 while ρ_exact = 0 — the central conceptual
demonstration (Finding 1). Under a common template, nonce reuse *becomes*
exact-input duplication (Finding 2). PoCol eliminates both within an epoch by
coordination (Finding 3).

## 3. Physical work (Table NR-E, Fig 7)

C_total = N·2.34e14·10 000 evaluations for every arm (2.340e20 … 1.170e21),
identical across arms at each N except PoCol's straggler deficit of ≤ 5e-8
fraction. Nonce-reuse patterns spanning 0 → (N−1)/N produced **no difference in
physical evaluations** — reuse does not add or remove hashing while miners stay
active; it only changes how informative each hash is.

## 4. Energy (Table NR-F, Figs 8–11) and the key hypothesis (brief §17)

Verified per run and per N (`stage8x_nr_key_hypothesis.json`): the four PoW arms
have **bit-identical t_active and bit-identical energy** at every N despite
nonce-reuse differing between 0.21 and 0.998 at sub-sweep scope and exact
duplication differing between 0 and 0.998 — *equal active power-time ⇒ equal
energy, regardless of nonce-reuse pattern*. PoCol's saving vs CONV-OFFSET at
α = 0 is its measured low-power residency exactly:

| N | F_low (measured = predicted) | saving at α = 0 | at α = 0.5 |
|---|---|---|---|
| 100 | 9.313e-10 | 9.31e-10 | 4.66e-10 |
| 200 | 2.421e-08 | 2.42e-08 | 1.21e-08 |
| 300 | 2.421e-08 | 2.42e-08 | 1.21e-08 |
| 400 | 7.078e-08 | 7.08e-08 | 3.54e-08 |
| 500 | 4.750e-08 | 4.75e-08 | 2.37e-08 |

(F_low is non-monotone because it equals (N_short·1)/(N·hi), set by 2^32 mod N.)
At N = 100 that is ~0.0035 J of a 975 kWh run. **Eliminating nonce-value overlap
produced no energy benefit by itself** (Finding 4); with the full 2^32 domain
sweepable in 18 µs, post-range low-power residency is a few nanoseconds per epoch,
so the Stage 8X mechanism (Finding 5) is quantitatively negligible here — an
honest negative result on RQ-XNR5/6 for this configuration.

## 5. Service (Tables NR-G/NR-H, Figs 12–13)

* CONV and PC: 16.13 blocks/run mean at every N (pooled CONV interval 586.9 s vs
  600 s nominal); PC retention vs CONV = **1.000** at every N (identical paired
  block counts; PC median/p95 intervals equal to CONV's). Disjoint allocation
  fully preserves service.
* MT: 0.033–0.067 blocks/run (2 blocks in 30 runs at N=100; 1 at N≥200), against
  a predicted mean of T/(600N) = 0.167…0.033 — retention ~1/N (Fig 12). With one
  common template, only 2^32 distinct inputs exist per epoch, so N miners deliver
  one miner's distinct-input throughput. MT intervals (from the few observed
  blocks: 3 971 s at N=100) are reported with explicit run counts and not
  over-interpreted. MT-ZERO additionally shows N−1 stale co-discoveries per block
  (synchrony artifact of the diagnostic control).
* Template renewal (NR-H, N=100 per run): CONV 5.448e10 miner-epochs
  (= 5.448e8 per miner), MT 5.448e8 network-epochs, PC 5.448e10 partitioned
  sweeps; exhaustion and reset counters exact; OFFSET arms have 0 nonce resets,
  ZERO arms reset every epoch.

## 6. Analytical validation (Table NR-J)

55 prediction-vs-measurement checks across all N: **55 within tolerance, 0
failures** — including exact-zero requirements (PC epoch reuse, CONV ρ_exact),
1e-12-tolerance closed forms (MT (N−1)/N, zero-start (N−1)/N), 5 %-tolerance
stochastic models (offset coverage, W²/S pairwise overlap, F_low), and the block
counts.

## 7. Findings mapped to brief §34

1. **Finding 1 — confirmed:** conventional PoW: substantial nonce-value reuse
   (every value used by all N miners each round), exact-input duplication 0.
2. **Finding 2 — confirmed:** common-template PoW: both, at (N−1)/N; and the
   corrected 2^32 domain makes the service cost extreme (retention ~1/N).
3. **Finding 3 — confirmed and verified:** PoCol within-epoch nonce-value overlap
   = 0 and exact-input duplication = 0; a coordination property.
4. **Finding 4 — confirmed:** equal active power-time ⇒ equal energy, independent
   of reuse pattern.
5. **Finding 5 — confirmed in sign, negligible in size here:** PoCol's saving
   equals its measured low-power residency, ≤ 7.1e-8.
