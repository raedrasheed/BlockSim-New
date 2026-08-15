# Stage 8X-ND — Theory Report (written before Pilot and primary execution)

Purpose: answer TQ1–TQ6 and the §29 validity check from the frozen hardware and
domain geometry alone, and preregister every deterministic expectation —
including unfavourable ones — before any run.

Frozen inputs: S21 Pro h = 2.34e14 evals/s per miner, P = 3510 W; explicit
32-bit nonce-value domain S = 2^32 (max valid nonce 2^32−1); N ∈ {100…500};
T = 10 000 s; q_N = 1/(N·h·600); partition start_i = ⌊i·2^32/N⌋.

## TQ1 — Full-domain sweep time (one PoW miner)

```
t_full = 2^32 / 2.34e14 = 1.8355e-5 s = 18.355 µs
```

Full-domain sweeps per miner per second: 1/t_full = **54 482 s⁻¹**.

## TQ2 — PoCol range sweep time

Range size L_N = 2^32/N (±1 nonce; exact sizes ⌊(i+1)S/N⌋−⌊iS/N⌋):

| N | L_N (nonces) | t_range = L_N/h | sweeps/s |
|---|---|---|---|
| 100 | 42 949 673 | 183.55 ns | 5.448e6 |
| 200 | 21 474 837 | 91.77 ns | 1.090e7 |
| 300 | 14 316 558 | 61.18 ns | 1.634e7 |
| 400 | 10 737 419 | 45.89 ns | 2.179e7 |
| 500 | 8 589 935 | 36.71 ns | 2.724e7 |

## TQ3 — Full nonce-domain cycles per 600 s expected block interval

Per conventional miner: 600/t_full = **3.269e7 sweeps**; network-wide N times
that. A PoCol coordinated epoch (all ranges complete) lasts ⌈S/N⌉ ticks =
t_range, so PoCol renews its common template **3.269e7·N times per 600 s**.
Header/template renewal is therefore the dominant clock in both systems: the
2^32 field is a microsecond-scale resource at modern ASIC rates.

## §29 validity check (mandatory)

**«Under different PoW headers, if N miners each perform one hash using the
same numerical nonce value, are those N independent candidate evaluations?»
YES.** Distinct headers make (Header_i, nonce) distinct serialized inputs; the
i.i.d. Bernoulli(q) field gives each an independent success chance (this is
the same model validated by real double-SHA-256 Monte Carlo in Stage 8X and
re-verified in Stage 8X-NR test 6). One numerical nonce value is NOT one
global cryptographic opportunity when headers differ. Consequently ND-PW
receives **N independent target trials** from N same-valued nonce evaluations.

## TQ4 — Does partitioning reduce independent trials per second?

**No.** Two rates must not be confused:

* ND-PW: every evaluation is a fresh input (distinct headers) → trial rate
  **N·h**.
* ND-PC: within one common-template epoch only S distinct inputs exist, but
  disjoint ranges mean every evaluation is fresh, and the epoch (hence the
  template) renews every t_range = S/(N·h) seconds. Trial rate =
  S per t_range = **N·h** as well.

Partitioning the numerical domain does not by itself reduce (or increase)
independent cryptographic trials per second; the common template's saturation
is exactly compensated by N×-faster template renewal. The trial-rate identity
holds because PoCol never re-evaluates an input and never idles (except the
straggler gap below).

## TQ5 — Expected block-production consequence

Since both arms sustain trial rate N·h at the same q_N: **block rate identical,
1/600 s⁻¹; expected 16.67 blocks per run in both arms; BlockRetention ≈ 1.0;
LatencyRatio ≈ 1.0; EnergyPerBlockRatio ≈ 1.0.** The only deficit is PoCol's
straggler gap: ranges differ by ≤1 nonce, so short-range miners idle ≤1 tick
(4.27 fs) per epoch — a trial-rate deficit of order 1e-8, invisible at any
achievable statistical power.

## TQ6 — Is substantial low-power residency physically plausible?

**No — this is the central preregistered (unfavourable) prediction.** A PoCol
miner finishes its range and the coordinated domain is then complete (all
miners finish within 1 tick of each other, homogeneous fleet), so a new common
epoch begins immediately. The only low-power time is the straggler gap:

```
F_low = N_short·(hi−lo) / (N·hi)
      = 9.313e-10 (N=100), 2.421e-8 (200), 2.421e-8 (300),
        7.078e-8 (400), 4.750e-8 (500)
```

Predicted energy saving = F_low·(1−α): at most **7.1e-8** (α = 0) — a few
millijoules of a ~975–4875 kWh run. Substantial residency would require a
miner to WAIT after finishing while others still search — impossible when all
ranges complete simultaneously — or an altered epoch/template semantics
(slower renewal), which would directly cut the trial rate and block production
(the E50/8Y trade). **Under the true 2^32 geometry and real S21 Pro rate, the
partitioning + post-range low-power mechanism cannot produce a material energy
effect. Predicted outcome: D (with C), and this is preregistered before
execution.**

## Nonce-domain utilization predictions (RQ-ND1/2)

ND-PW: C_nonce = N·h·T = 2.34e20…1.17e21 per run; every miner traverses the
full domain 5.448e8 times per run; U_nonce(run) = 2^32; aggregate visits per
nonce value = N·h·T/2^32 ≈ 5.4e10·(N/100); cross-miner multiplicity m_max = N.
ND-PC: C_nonce identical minus the 1e-8 straggler deficit; each miner visits
only its own L_N values (5.448e8·N... per-miner sweeps of its range =
T/t_range = 5.448e8·N/ ... = T·h/L_N); cross-miner overlap **0 within every
epoch**; per-value visit count equals PW's in aggregate. Exact-input
duplication (secondary): 0 in both arms.

## Why the experiment still runs

Execution is not redundant: the zero-start primary control (the researcher's
literal M_i → 0,1,…,2^32−1 model) has not been run as a primary arm against
PoCol before (Stage 8X-NR's primary used offset traversal); the ND-PC-NOLP
control that separates partitioning from low-power policy is new; and the
trial-rate identity of TQ4 — the scientifically decisive fact — deserves
direct measurement (block retention ≈ 1.0 with tight paired CIs) rather than
assertion. Cost is seconds of compute. All predictions above stand to be
falsified by the run.
