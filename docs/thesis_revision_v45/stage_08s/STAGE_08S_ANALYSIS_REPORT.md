# Stage 8S — Analysis Report (FINAL refinement cycle)

**Input:** the frozen 48-row `STAGE_08S_RUN_DATASET.csv` only (SHA-256 in
`stage8s_results.json`). **Plan:** `STAGE_08S_PREREGISTRATION.md`, executed verbatim by
`analyze_8s.py` (n = 12 fresh paired seeds; 4096 exact sign assignments; 10 000 paired
bootstrap resamples; analysis root 16767666002914861861; Holm over exactly three declared
p-values; byte-identical re-run). All 48 runs pass every deterministic integrity gate.

## Historical conclusions (preserved, not rewritten)

The Stage-8M and Stage-8R findings stand unchanged: a large, consistent low-power-state
accounting difference; both static-floor controllers exceeding the joint operational
limits; the Stage-8R controller improving throughput and decision churn without making the
static 0.80 × H0 floor attainable; the four-reserve pool at ~1 000 H against ~3 200 H.

## 1. Primary results

| hypothesis | result | key numbers |
|---|---|---|
| **H-S1 throughput recovery** (S03 vs S01, `accepted_blocks`) | **SUPPORTED** (Holm) | **+10.58 blocks** (150.2 → 160.8; 95 % CI [+9.08, +12.08]; p = 0.00024 = 1/4096) — the largest throughput gain of the entire refinement program |
| **H-S2 operational usefulness** (S03 vs S00, deterministic) | **FAIL** (one gate) | blocks ratio **0.9039 ≥ 0.90 — the historically failing throughput gate PASSES for the first time**; duration ratio 1.0005 ≤ 1.10 PASS; every per-run zero (nonterminal counts, duplicates, post-round, frontier rewinds) PASS; **below-useful-floor 28.71 s > 15 s FAIL** |
| **H-S3 churn reduction** (S03 vs S01) | **FAIL** (all counts) | requests 642.3 vs 596.7 (MORE; p = 1.0); incomplete 414.0 vs 386.7 (MORE; p = 1.0); reassignments/round **1.748 > 1.0**; rejected workless wakes 0 (reported) |
| **H-S4 retained energy benefit** (S03, within-run power null) | **PASS** | relative reduction **0.5505** (CI [0.5495, 0.5515]; ≥ 0.20); absolute CI lower 0.0197 kWh > 0 |
| **Overall structural-policy claim** | **NOT LICENSED** | H-S2 and H-S3 fail; per the frozen FINAL-cycle rule there is no further tuning |

## 2. What the useful-work-aware policy actually did (descriptive means, n = 12)

| metric | S00 | S01 (=S02*) | S03 |
|---|---|---|---|
| accepted blocks / closed rounds | 177.9 / 223.8 | 150.3 / 189.8 | **160.8 / 203.7** |
| mean / p95 round duration (s) | 1.341 / 2.00 | 1.582 / 2.86 | **1.474 / 2.33** |
| below static floor (s) — SECONDARY historical | 0 | 273.8 | 271.8 |
| below USEFUL floor (s) — PRIMARY | 0 | 42.25 | **28.71** (−32 %) |
| useful-floor deficit area (hash·s) | 0 | 53 515 | 42 807 |
| time-weighted H_useful_available / target | — | 676 / 613 | 675 / 607 |
| activation requests seated / incomplete | 0 | 596.7 / 386.7 | 642.3 / 414.0 |
| coarse repartitions / chunk assignments per run | — | — | 201.8 / 355.6 (mean chunk 26.6 nonces) |
| lineage-replay preventions / receiver-busy preventions | — | — | 0 / (in duplicate counter) |
| reserve wakes with bound work / useful-completion ratio | — | 596.7 / 0.910 | 642.3 / 0.877 |
| E_idle (kWh) / relative reduction | 0.0165 / 0.538 | 0.0153 / 0.572 | 0.0161 / 0.551 |

*S01 and S02 produced identical runs on every seed: without a work-delivery mechanism the
useful target reduces to min(floor, H_effective) at decision time, so `USEFUL_FLOOR_ONLY`
makes the same decisions as the static predictive controller — an honest component
finding: the useful floor matters only when paired with a mechanism that can act on it.

**Tail mechanics (the H-S1 mechanism):** the coarse repartition truncated the no-block
tail from the wrong side — by finishing the work instead of dropping it: p95 round
duration fell from 2.86 s to 2.33 s while blocks-per-round stayed equal (0.7915 vs
0.7894), so all recovered time became extra rounds (189.8 → 203.7).

## 3. Honest reading of the two failures

* **Below-useful-floor 28.7 s vs 15 s.** The counterfactual metric counts every second in
  which an already-awake receiver could have taken work but did not. The frozen
  constraints that keep the mechanism disciplined — one repartition per donor lineage per
  episode, the strict benefit gate, batch-quantized chunks — are exactly what leaves those
  seconds on the table. Halving 42.25 s to 28.71 s was real but not enough for the frozen
  15 s gate.
* **Churn.** S03 seats MORE activation requests than S01 (642 vs 597): the extra rounds it
  wins each bring their own reserve-batch cycle, and the coarse mechanism adds 1.75
  reassignments per closed round against a frozen limit of 1.0. The preregistered churn
  hypothesis is refuted for the second time; total-activity reduction and throughput
  recovery pulled in opposite directions at this scale, and the frozen rule does not allow
  trading one for the other after the fact.

## 4. Energy attribution (per-run means, S03)

range-idle difference 0.00442 kWh + reserve standby 0.00472 kWh + wake transient
0.00086 kWh; activated-reserve hashing cost 0.00019 kWh. Reserve/wake components are never
merged with the range-idle component. The retained benefit (55.1 %) is an accounting
result against the within-run power null, not an unconditional protocol comparison.

## 5. Final verdict (frozen rule, FINAL cycle)

**The structural-policy claim is NOT LICENSED** (H-S2's useful-floor gate and H-S3 fail;
H-S1 and H-S4 pass). As preregistered for this final cycle: no further tuning, no Stage
8T, no seed/margin/target change. The result is preserved as-is for thesis integration.
The remaining structural limitations — the 15 s useful-floor gate under discipline
constraints, and churn that scales with recovered rounds — are identified as future work
in `STAGE_08S_LIMITATIONS.md`.
