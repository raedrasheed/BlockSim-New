# Hash-Rate-Aware Difficulty — Results

**Branch:** `claude/pocol-hashrate-aware-difficulty` · **Data:**
`results/hashrate_aware_difficulty/` · **Reproduce:**
`python experiments/hashrate_aware_difficulty/run_matrix.py 100 12` ·
`python -m pytest tests/ -v`

Protocols: **DUP** (common-template duplicate baseline — not normal Bitcoin
mining), **IND** (independent headers, the realistic control), **PoCol**
(disjoint nonce). All runs: continuous average-interval design, immediate
commit, idle-power ratio 0.

---

## 1. The previous defect and the correction

The fixed-600s experiment calibrated the H1 domain as `M = (H/N)·600` and then
split it N ways — an artificial `N²` scaling giving `600/N`-second discoveries
under *fixed aggregate hash rate*. Corrected: `M_total = H_network·budget`;
share exhaust time `M_i/H_i = budget` for every N (tested), and discovery is
governed by `p·H_network` alone. **Difficulty lives only in the 256-bit target**
(`W = H_network·T`, `p = 1/W`, `target = ⌊2²⁵⁶/W⌋−1`), never in domain size
(tested: D1 vs D2 share the identical `M_total`).

## 2. Difficulty by population (analytic, verified by simulation)

| Policy · Mode | Difficulty ratio `D_N/D_ref` | Expected interval |
|---|---|---|
| **H1 · D2** (fixed aggregate 141 TH/s) | **1.0000 for every N** (target bit-identical) | 600 s for every N |
| **H2 · D2** (fixed per-miner) | **= N exactly** (100…500 measured), `target_N ≈ target_1/N` | 600 s for every N |
| **H2 · D1** (constant) | 1.0000 | **600/N** (dilution) |

"Difficulty increases with the number of miners" is correct **only under H2**,
where aggregate hash rate actually grows.

## 3. Primary stochastic results (D2, H1, 100 paired seeds, fresh subprocesses)

| N | proto | blocks | interval (s) | E (kWh) | E/blk (kWh) | hashes/blk | work/blk | dup attempts | exh % |
|--:|:--|--:|--:|--:|--:|--:|--:|--:|--:|
| 100 | DUP | 0.15 | n/a | 8.5892 | 8.589 | 1.44e18 | 8.46e16 | 1.42e18 | 0 |
| 100 | IND | 16.90 | 600 | 8.5892 | 0.539 | 9.02e16 | 8.46e16 | 0 | 13.4 |
| 100 | PoCol | 17.43 | 574 | 8.5892 | 0.518 | 8.68e16 | 8.46e16 | 0 | 12.0 |
| 300 | DUP | 0.04 | n/a | 8.5892 | 8.589 | 1.44e18 | 8.46e16 | 1.43e18 | 0 |
| 300 | IND | 16.59 | 608 | 8.5892 | 0.551 | 9.23e16 | 8.46e16 | 0 | 13.4 |
| 300 | PoCol | 17.17 | 602 | 8.5892 | 0.539 | 9.02e16 | 8.46e16 | 0 | 12.8 |
| 500 | DUP | 0.02 | n/a | 8.5893 | 8.589 | 1.44e18 | 8.46e16 | 1.44e18 | 0 |
| 500 | IND | 17.32 | 584 | 8.5893 | 0.527 | 8.82e16 | 8.46e16 | 0 | 11.7 |
| 500 | PoCol | 17.19 | 595 | 8.5893 | 0.529 | 8.86e16 | 8.46e16 | 0 | 11.8 |

(N=200/400 in the CSVs, same pattern. H2 mirrors it with energy scaling ∝ N:
8.59 → 42.95 kWh at N=100 → 500, intervals 574–604 s, `D/D_1 = N`.)

Key readings:

- **IND and PoCol hold the 600 s expected interval at every N** (584–608 s,
  within Monte-Carlo tolerance of ~17 blocks/run × 100 seeds).
- **DUP cannot hold the schedule:** full duplication makes the network's
  effective rate the *per-miner* rate, so its expected interval is `N·600 s`
  (60 000 s at N=100 ≫ the 10 200 s horizon → ~0 blocks). Its 1.4e18 duplicate
  attempts per (rare) block are pure redundancy.
- **Energy is identical for all three protocols** (continuous operation:
  `E = P_agg·sim`; H1: 8.5892 kWh at every N). PoCol−IND total-energy diff is
  ~1e-16 kWh; **TOST equivalent at every condition**. Energy-per-block differs
  only through blocks committed.
- **Security-work disclosure:** accumulated work per block = 8.46e16 (from the
  target) vs actual hashes per block ≈ 9.0e16 for IND/PoCol — the ~7 % gap is
  exhausted-template overhead (~12–13 % of templates at budget = 2T), disclosed,
  identical across IND/PoCol. Idle waiting is never counted as work.

## 4. D1 constant-difficulty dilution (H2, PoCol, 100 seeds)

| N | 1 | 2 | 5 | 10 |
|---|---|---|---|---|
| interval | 605.7 s | 296.9 s | 117.9 s | 59.6 s |
| expected 600/N | 600 | 300 | 120 | 60 |

Difficulty ratio stays 1.000 — adding miners without retargeting simply speeds
up blocks; this is **not** a maintained-600 s configuration.

## 5. D3 dynamic retarget (H2, start 10× too easy, window 10, clamp [0.25, 4])

| N | initial D | final D | ideal D | behaviour |
|--:|--:|--:|--:|:--|
| 10 | 8.46e13 | 1.05e16 | 8.46e15 | rises ×123, oscillating ≈1.24× ideal |
| 100 | 8.46e13 | 9.88e16 | 8.46e16 | rises ×1168, ≈1.17× ideal |

Retargeting from accepted-block timestamps pushes difficulty to the
hash-rate-correct value (with the expected clamp-limited overshoot/oscillation);
unit tests verify direction, magnitude and clamps exactly.

## 6. PoCol vs independent-header PoW (the §11 rule)

Under equal aggregate hash rate, equal target/difficulty, equal expected work,
equal duration, and equal workload: **PoCol does not beat IND** — identical
total energy (TOST equivalent), statistically indistinguishable energy-per-block
(paired d between −0.12 and +0.02, sign-varying), same interval, same
exhaustion behaviour. PoCol's real, measurable advantage is **only over the
duplicate baseline**, i.e. de-duplication itself — which distinct headers also
achieve.

## 7. Tests

`python -m pytest tests/ -v` → **141 passed** (124 prior + 17 new covering all
22 §16 invariants).
