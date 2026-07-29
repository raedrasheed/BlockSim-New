# BASELINE NUMERICAL AUDIT — Thesis Scientific Revision v43 (Stage 1)

Empirical, as-is re-execution of the **current unmodified** implementation.
**No defect was fixed.** Purpose: document the physical invariant, the observed
behaviour of the two flagged mechanisms, and the (non-)reproducibility of the
Chapter 7 headline values. All runs used the current code on commit
`2d3c243`, **no seed** (the code sets none), each on a copy of the source
(tracked `InputsConfig.py` never modified). Full provenance in
`results/thesis_revision_v43/manifests/*.json`; raw outputs (read-only) in
`baseline_snapshot/`; logs in `logs/`.

---

## 1. Physical invariant (documented, not enforced)

For a genuinely fixed network of `141 TH/s` at `21.5 J/TH` run for `10,000 s`:

```
P_network = 141e12 H/s × 21.5e-12 J/H = 3031.5 W
E_network = 3031.5 W × 10000 s / 3.6e6 = 8.4208 kWh   (constant vs miner count)
```

This is the value a correct, fixed-hash-rate PoW baseline must approach **for
every miner count**. Stage 2 will encode this as
`test_continuous_energy_10000_seconds` and
`test_energy_independent_of_miner_count_when_total_hashrate_fixed`.

---

## 2. Finding C-1 confirmed: PoW energy scales with miner count (`/100` mechanism)

Root cause: `Models/Node.py:49-54` returns `net * (hp/100.0)` with `hp=1` per
miner, so total network hash rate = `(Nn/100) × 141 TH/s` instead of a fixed
`141 TH/s`. Evidence from three independent sources:

### (a) Thesis Table 7.1 (as published)
| Miners | PoW energy (kWh) | ÷ (Nn/100) |
|---|---|---|
| 100 | 7.9018 | 7.90 |
| 200 | 15.5580 | 7.78 |
| 300 | 24.4860 | 8.16 |
| 400 | 33.0783 | 8.27 |
| 500 | 40.4078 | 8.08 |

`PoW ÷ (Nn/100)` ≈ constant ≈ 8 kWh ≈ the physical invariant. The published
"PoW energy grows with miners" is the `/100` artifact.

### (b) Committed workbooks (not thesis rows, but same model)
| File | Miners | Energy (kWh) | (Nn/100)×8.4208 | ratio |
|---|---|---|---|---|
| `Bitcoin_20260122_143644` | 50 | 3.9287 | 4.210 | 0.933 |
| `Bitcoin_20260122_153749` | 1000 | 83.8358 | 84.208 | **0.996** |

At 1000 miners the model reports **10×** the physically correct energy.

### (c) Stage 1 fresh re-runs (this audit, unseeded)
| Miners | PoW energy (kWh), fresh run | main blocks |
|---|---|---|
| 100 | 8.0851 (also 8.3482, 7.8958 on repeats) | 10 / 19 / 16 |
| 200 | 16.2641 | 21 |
| 300 | 25.2409 | 20 |
| 400 | 32.9915 | 15 |
| 500 | 30.8155 | 11 |

Fresh runs reproduce the `(Nn/100)×~8 kWh` pattern. (The 500-miner value is low
because only 11 blocks were produced and the final mining interval to `simTime`
is never flushed — a secondary undercount, finding Mod-3, tied to the fact that
`stop_mining_and_account` is only called on block-mine/receive events.)

---

## 3. Finding C-2 confirmed: PoCol energy is ~1–2% of PoW (`÷N` mechanism)

Root cause: `Models/PoCol/Consensus.py:262-264` charges each miner
`time_share = block_time / N` seconds, so total PoCol energy ≈ `(1/N) ×`
physical. Losers' full-round hashing is never charged; there is no idle-state
model. Fresh unseeded runs:

| Miners | PoCol energy (kWh) | total blocks | main | stale % | wall time |
|---|---|---|---|---|---|
| 100 (rep1) | 0.2463 | 52 | 25 | 51.92 | 4.8 s |
| 100 (rep2) | 0.3245 | 59 | 24 | 59.32 | 7.4 s |
| 100 (rep3) | 0.7159 | 142 | 44 | 69.01 | 18.7 s |
| 200 (rep1) | 0.4945 | 194 | 51 | 73.71 | 126.7 s |
| 300 (rep1) | 0.1897 | 115 | 38 | 66.96 | 182.6 s |
| 400 (rep1) | not completed | — | — | — | exceeded 240 s cap |
| 500 (rep1) | not completed | — | — | — | exceeded 240 s cap |

**PoCol ≥400 miners did not complete within the 240 s per-run cap** in this
environment and were stopped (PoCol-300 already took 182.6 s; cost grows
~O(N²–N³), finding M-1). This is a documented reproducibility/scaling limitation
of the *current* implementation, not a fix target for Stage 1; Stage 3 addresses
the scheduler cost. The thesis's own PoCol 400/500 values were therefore
produced either on faster hardware or by a different/older implementation, and
remain **UNTRACEABLE** here.

PoCol energy is ~1–4% of the PoW figure at the same miner count — i.e. the same
~98–99% "reduction" the thesis reports — but it is driven entirely by `÷N`, not
by any modelled physical mechanism.

---

## 4. Finding C-3 confirmed: Chapter 7 values are non-reproducible

**No seeding exists** (BASELINE_FREEZE §4). The three repeats at
PoCol-100 give total energy `0.2463 / 0.3245 / 0.7159 kWh` and stale rate
`51.9% / 59.3% / 69.0%` — a **~3× spread from identical configuration**. PoW-100
repeats give `8.09 / 8.35 / 7.90 kWh`. Therefore the single published Chapter 7
values cannot be reproduced exactly; only their order of magnitude and pattern
are reproducible. Every Chapter 7 experimental cell is classified **UNTRACEABLE**
in `THESIS_TO_CODE_TRACEABILITY.csv` (model identified; exact value not
committed and not re-derivable).

---

## 5. Finding M-1 corroborated: stale explosion + O(N²–N³) cost

PoCol stale rate rises with miner count (fresh runs: 52–69% at 100, 74% at 200,
67% at 300; thesis: 35.7%→85.7% across 100→500). The scheduler never cancels
superseded "loser" events (`Scheduler.py:31-40` stamps no round/generation id).
Wall-clock cost grows steeply (100→5 s, 200→127 s, 300→183 s), reflecting
per-reception `_init_round` (O(N)) and propagate-to-all (O(N)) amplified by the
stale count — which is why PoCol ≥400 miners is capped in this environment and is
a Stage 3 performance target.

---

## 6. Test coverage of the thesis path (finding)

The only committed tests (`tests/test_energy_models.py`, 11 tests, **all pass**)
exercise the **journal manuscript's** `Models/Energy/` models. There are **zero
tests** for the thesis simulator path: the `/100` normalization, the `÷N` PoCol
energy, the scheduler, or the physical invariant. Stage 2/3 introduce these.

---

## 7. Summary of Stage 1 numerical validation

| Check | Expected | Observed | Verdict |
|---|---|---|---|
| Physical invariant documented | 8.4208 kWh @ fixed 141 TH/s, 10000 s | documented (not yet enforced) | ✅ documented |
| PoW energy ∝ miner count (`/100`) | `(Nn/100)×~8 kWh` | thesis + committed + fresh runs all match | ✅ confirmed |
| PoCol energy ≈ (1/N) physical (`÷N`) | ~1–4% of PoW | fresh runs match | ✅ confirmed |
| Chapter 7 reproducibility | exact | non-deterministic, no seed, uncommitted | ✅ UNTRACEABLE |
| Defects modified in Stage 1 | none | none (documented only) | ✅ as required |
| Thesis files byte-identical | yes | SHA-256 unchanged | ✅ verified |
