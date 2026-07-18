# Corrected Experiment Report (PoW vs PoCol)

**Branch:** `claude/fix-energy-round-semantics`
**Runs:** 300 (2 protocols × 5 miner counts × 30 seeds), fresh interpreter each, paired seeds.
**Data:** `results/corrected/{raw_runs.csv, summary_statistics.csv, paired_effect_size.csv,
configuration.json, reproducibility_manifest.json}`.

> **Headline result.** Under corrected, physically grounded wall-clock energy
> accounting, **PoCol provides no energy saving over PoW**. Both protocols consume
> an identical **8.4208 kWh** for the 10 000 s simulation at every miner count
> from 100 to 500. The paired PoCol−PoW energy difference is **5.9 × 10⁻¹⁷ kWh**
> (numerically zero; max absolute pairwise difference 1.8 × 10⁻¹⁵ kWh). The
> previously reported **98–99 % energy saving does not survive correct
> accounting** and was an artefact of the defects fixed in Phases B1–B5.

---

## 1. Energy and CO₂ (the central claim)

Aggregate energy is deterministic — it depends only on network power and
simulated time, not on the protocol, the miner count, or the block count.

| Miner count N | PoW energy (kWh) | PoCol energy (kWh) | PoCol − PoW | % diff |
|---:|---:|---:|---:|---:|
| 100 | 8.4208 | 8.4208 | 0 | 0.00 % |
| 200 | 8.4208 | 8.4208 | 0 | 0.00 % |
| 300 | 8.4208 | 8.4208 | 0 | 0.00 % |
| 400 | 8.4208 | 8.4208 | 0 | 0.00 % |
| 500 | 8.4208 | 8.4208 | 0 | 0.00 % |

- Std of energy across all 300 runs: **~1 × 10⁻¹⁴ kWh** (i.e. exact to floating
  point) for both protocols.
- CO₂ is identical: **3.7473 kg** for both protocols at every N
  (`8.4208 kWh × 0.445 kg/kWh`).
- The value equals the physical bound `P_network · simTime = 3031.5 W · 10000 s =
  8.4208 kWh`, confirming both protocols model the same continuously operating
  hardware.

**Interpretation.** Both Nakamoto PoW and PoCol keep the same hardware powered and
searching for the whole run. Energy is `power × time`; with equal power and equal
time the energy is equal. PoCol's nonce partitioning changes *who* finds the next
block and *how the search space is divided*, not *how much hardware is running*,
so it cannot reduce aggregate energy in this model.

---

## 2. Block production, intervals, and throughput

| N | Protocol | created blks | accepted blks | accepted interval (s) | created interval (s) | throughput (tx/s) |
|---:|:--|---:|---:|---:|---:|---:|
| 100 | PoW   | 17.9 | 17.9 | 548.2 | 579.5 | 3.300 |
| 100 | PoCol | 18.5 | 18.4 | 533.4 | 569.5 | 3.399 |
| 200 | PoW   | 17.4 | 17.4 | 570.8 | 614.1 | 3.202 |
| 200 | PoCol | 17.9 | 17.9 | 543.8 | 576.1 | 3.302 |
| 300 | PoW   | 15.1 | 15.1 | 670.4 | 712.1 | 2.784 |
| 300 | PoCol | 15.5 | 15.5 | 657.7 | 701.8 | 2.851 |
| 400 | PoW   | 16.7 | 16.7 | 598.9 | 644.6 | 3.074 |
| 400 | PoCol | 16.9 | 16.9 | 581.0 | 623.9 | 3.111 |
| 500 | PoW   | 17.2 | 17.2 | 566.5 | 608.3 | 3.164 |
| 500 | PoCol | 16.8 | 16.8 | 591.7 | 625.4 | 3.102 |

- Both protocols realise accepted intervals close to the **600 s target** and
  **close to each other** (overall PoW 591 s vs PoCol 581 s). The comparison is
  controlled: neither runs at a materially faster rate.
- Throughput tracks block interval and is statistically indistinguishable between
  protocols. It is *not* a PoCol advantage.

---

## 3. Forks / stale blocks

| Protocol | mean stale rate |
|:--|---:|
| PoW   | 0.000 % |
| PoCol | 0.039 % |

After the Phase B2 round-closure fix, the earlier **62–76 % artefactual stale
rate collapses to ~0** for both protocols. PoCol shows a single stale block in
one of 150 PoCol runs (loser-lag + exhaustion timing); it is negligible and,
under wall-clock accounting, carries no extra energy.

---

## 4. PoCol-specific overhead: exhausted rounds

| Protocol | mean exhausted rounds / run |
|:--|---:|
| PoW   | 0.00 |
| PoCol | 2.80 |

PoCol's finite nonce domain can exhaust (zero-success template) before a valid
header is found, forcing a redraw. PoW has no analogue. This is a **latency
overhead unique to PoCol** (~2.8 exhausted templates per run). It does **not**
reduce energy — hardware keeps running during the redraw — and slightly widens
PoCol's block-time distribution. It is reported here rather than hidden.

---

## 5. Paired effect sizes (PoCol − PoW)

Energy, per miner count, paired by seed (n = 30 pairs each):

| N | PoW mean (kWh) | PoCol mean (kWh) | mean diff | % | Cohen's d |
|---:|---:|---:|---:|---:|---:|
| 100 | 8.42083 | 8.42083 | 3.0e-16 | 0.0 % | 0.24* |
| 200 | 8.42083 | 8.42083 | 0 | 0.0 % | n/a |
| 300 | 8.42083 | 8.42083 | 0 | 0.0 % | n/a |
| 400 | 8.42083 | 8.42083 | 0 | 0.0 % | n/a |
| 500 | 8.42083 | 8.42083 | 0 | 0.0 % | n/a |

\* The non-zero Cohen's d at N = 100 is a floating-point artefact: the paired
differences are at the 10⁻¹⁶ kWh level (machine epsilon on ~8.42), so both the
mean difference and its std are numerically zero and their ratio is meaningless.
Where the difference is exactly 0.0 the std is 0 and d is undefined (n/a).

Energy-per-accepted-block differs by only −6 % to +3 % across N with small,
sign-varying Cohen's d (|d| ≤ 0.18) — consistent with block-count sampling noise,
not a systematic PoCol effect.

---

## 6. Honest conclusion

**Does PoCol save energy versus PoW? No.** In this simulator, with correct
wall-clock energy accounting and a controlled configuration, PoCol and PoW
consume **the same** aggregate energy and emit the **same** CO₂. PoCol is
**energy-neutral**, not energy-saving, and carries a small PoCol-specific latency
overhead (exhausted rounds) that PoW does not.

This is a **neutral-to-slightly-negative** result for PoCol, and it is the
scientifically valid one. The prior 98–99 % saving was produced by (a) charging
energy per block instead of per unit wall-clock time, (b) a hash-rate
normalisation that only held at N = 100, and (c) a guaranteed-single-nonce
success model that suppressed forks and exhaustion. All three are corrected here.

**A genuine energy argument for a collaborative consensus would require modelling
a mechanism this simulator does not contain** — e.g. miners powering hardware
*down* when not assigned a nonce sub-range, or a lower aggregate hash rate being
sufficient for equivalent security. Neither is assumed here, and neither should
be assumed without an explicit, defended physical model.

---

## 7. Reproducibility

```bash
# full matrix (writes results/corrected/*)
python experiments/run_matrix.py 30 8

# a single run (fresh interpreter, prints one JSON record)
python experiments/run_scenario.py PoCol 300 7
python experiments/run_scenario.py PoW   300 7

# methodology tests
python -m pytest tests/ -v
```

`results/corrected/reproducibility_manifest.json` pins the git commit, Python and
package versions, platform, seed list, and exact per-run commands.
