# Stage 8X-NR — Results Report

**Primary matrix:** N ∈ {100, 200, 300, 400, 500} × 3 primary arms
(XNR-PW-CONV-OFFSET, XNR-PW-MT-OFFSET, XNR-PC) × 30 fresh paired seeds =
**450 primary physical runs**, plus the two deliberately synchronized zero-start
diagnostic arms (XNR-PW-CONV-ZERO, XNR-PW-MT-ZERO) on the same seeds =
300 secondary diagnostic runs, **750 runs in total**, T = 10 000 s each, S21 Pro
hardware (234 TH/s, 3510 W, 15 J/TH), one shared D_N per N. All runs completed;
25 cells × 30 seeds audit exact; zero identity violations. Energy α-cases are
derived observations, so no additional simulations were run for them. Pilot runs
are excluded throughout. Zero-start results are reported separately and are never
generalized to all PoW implementations.

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

## 6a. Core conceptual table (verified by Tests 6–8 and the primary data)

| Situation | Same nonce value? | Same header/template? | Exact duplicate? |
|---|---|---|---|
| Different templates, same nonce (CONV) | Yes | No | **No** |
| Same template, same nonce (MT) | Yes | Yes | **Yes** |
| Same template, different nonce (MT) | No | Yes | No |
| PoCol disjoint ranges | No within epoch | Yes (common template) | No |

## 6b. Extended cross-miner multiplicity and pairwise overlap (Table NR-K)

Round scope: for every PoW arm, every nonce value is used by all N miners
(M_≥2 = M_≥3 = 2^32, m_max = mean multiplicity = N, pairwise O mean = median =
P95 = max = 2^32); PoCol: all of these are 0 (m_max = 1). Sub-sweep window
(offset arms, N = 100): reused values are mostly pairwise collisions — mean
multiplicity among reused values 2.19, m_max ≈ 3.9, M_≥2 = 3.86e8, M_≥3 =
6.2e7; the pairwise distribution is heavy-tailed (mean 108 995, median 0,
P95 = 0, max 2.1e7 — only ~1/N of pairs overlap at all, but two adjacent
offsets can overlap almost fully). Zero-start: every pair overlaps completely
(mean = median = P95 = max = W, multiplicity = N).

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

## 8. Assessment for a future adaptive active-set experiment (brief §21–22)

The next-step theorem check comes out as follows, from the measured semantics:

* **Conventional independent-template PoW wastes nothing to duplication.** Its
  nonce-value reuse is total (every value used by all N miners per round) yet its
  exact-input duplication is zero: every one of the N·h·T evaluations is a fresh,
  independent Bernoulli(q) attempt. There is **no work-removal opportunity in
  conventional PoW that does not proportionally remove success probability** —
  removing any fraction φ of active hashing removes exactly φ of the block rate.
* **Common-template PoW wastes (N−1)/N to duplication**, and PoCol's disjoint
  allocation recovers all of it (blocks ×N at equal energy). This is the only
  regime where coordination removes work without removing useful probability —
  but that baseline is a controlled comparator, not deployed Bitcoin practice.
* **Consequently, for an adaptive active-set experiment on homogeneous S21 Pro
  hardware:** block retention ≈ mean active-hash fraction (confirmed here and in
  Stages 8Y/8Z), so at ≥90 % retention the active fraction must be ≥0.90 and the
  maximum energy saving is ≈10 % (at α = 0; less for α > 0). **>50 % energy
  saving with ≥90 % block production is not theoretically feasible under the
  measured semantics with homogeneous hardware.** Stage 8Y measured exactly this
  trade (53.9 % saving came with ≈60 % retention), and Stage 8Z's preregistered
  ceiling showed that even a 1.97× heterogeneous efficiency spread caps the
  90 %-retention saving at ~15 %. Reaching 50 % saving at 90 % retention would
  require parking only units ≥ ~5.6× less efficient than those left running —
  a hardware-fleet property, not a protocol property.
* **Recommendation:** a further adaptive active-set experiment aimed at >50 %
  saving with ≥90 % retention is **not scientifically justified** on this
  hardware model; the linear energy-retention bound is now confirmed three
  independent ways. A future experiment is justified only if it tests a different
  mechanism: (i) strongly heterogeneous fleets (efficiency spread ≥ ~5.6× for the
  50 %/90 % target), (ii) demand-following operation where retention below 90 %
  is acceptable at off-peak times, or (iii) throughput/coordination claims
  against a common-template baseline, where PoCol's ×N distinct-input advantage
  is real and measured. This assessment is recorded before any such experiment is
  designed, per the brief.
