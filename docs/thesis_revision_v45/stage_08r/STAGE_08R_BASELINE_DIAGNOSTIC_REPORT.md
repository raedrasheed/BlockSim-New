# Stage 8R — Baseline Diagnostic Report (READ-ONLY, from frozen Stage-7M/8M data)

**Baseline:** `thesis-v45-pocol-stage8m-minimal-analysis` @
`b7580a1f3b15b9eaf3ae3a9b0b74452bfbd014e3` (fetched, clean worktree, 204 tests green,
Stage-7M/8M manifests verified, engine digests incl. `search.py` unchanged).

**No simulation was executed for this report.** Inputs are exclusively the frozen compact
run records (all 10 seeds of M01/M03) and the two frozen audit ledgers (M01 seed 0, M03
seed 0). The old experiment was not rerun. Numeric record:
`STAGE_08R_BASELINE_DIAGNOSTIC_METRICS.json`; representative timeline:
`STAGE_08R_BASELINE_TIMELINE_M03_S00.csv`.

Every statement below is labeled **[OBSERVED]** (read from a frozen record),
**[DERIVED]** (computed under a stated assumption), **[HYPOTHESIS]** (causal
interpretation), or **[UNRESOLVED]** (not derivable from the frozen data).

---

## 1. Per-seed summary (all 10 seeds) [OBSERVED unless noted]

Means over the 10 confirmatory seeds (full per-seed table in the metrics JSON):

| metric | M01 | M03 | note |
|---|---|---|---|
| closed rounds | 222.3 | 183.9 | |
| accepted blocks | 173.9 | 143.4 | |
| accepted blocks / closed round | 0.782 | 0.780 | [DERIVED] — **nearly identical** |
| median round duration (s) | 1.172 | 1.173 | |
| approx. mean round duration (s) | 1.350 | 1.632 | [DERIVED] horizon/rounds, upper bound |
| below-floor duration (s) | n/a | 274.8 | |
| floor-unattainable count | n/a | 1 036.2 | |
| activations seated / completed | 0 / 0 | 318.1 / 207.3 | |
| incomplete activations | 0 | 110.8 | [DERIVED] seated − completed |
| E_idle (kWh) | 0.01653 | 0.01488 | M03 uses **less** energy |

Fields not derivable per seed from compact records (persisted for audit seeds only):
p90/p95 round duration, unclosed tail, per-state residency, activation lifecycle split,
inter-round setup gap. **[UNRESOLVED per-seed; DERIVED below for the audit seeds.]**

## 2. Audit-seed depth (seed index 0) [DERIVED from full frozen ledgers]

| metric | M01-s00 | M03-s00 |
|---|---|---|
| closed rounds / accepted / no-block | 216 / 162 / 53 | 178 / 135 / 42 |
| blocks per closed round | 0.750 | 0.758 |
| round duration median / mean (s) | 1.201 / 1.389 | 1.190 / 1.685 |
| round duration p90 / p95 / max (s) | 2.0 / 2.0 / 2.0 | **3.0 / 3.0 / 3.0** |
| unclosed final tail (s) | 0.0 | 0.0 |
| reserve WAKING residency (s, 4 reserves) | 0 | **239.14** |
| reserve ACTIVE_HASHING residency (s) | 0 | **80.91** |
| activations seated / started / completed | — | 328 / 328 / 226 |
| cancelled before start / during wake | — | 0 / 102 |
| cancellation disposition | — | all `cancelled_at_round_close` [OBSERVED] |
| superseded / schedule-failed | — | no such states exist in the accepted schema [UNRESOLVED/OBSERVED-absence] |
| wake energy, completed wakes (J) | — | 2 429.5 |
| wake energy, wakes cancelled mid-flight (J) | — | ≈ 141 |
| floor deficit area (hash·s) | — | **839 878** [DERIVED] |
| maximum floor deficit (hash) | — | 3 200 (= full floor) [DERIVED] |
| below-floor duration, reconstructed (s) | — | 280.3 [DERIVED] vs 275.26 [OBSERVED] |

**Reconstruction validity.** H_effective(t) was rebuilt from the frozen evaluation ledger
(per-miner rates derived from batch-completion cadence; assignment start ≈ first completion
− batch/rate; end = last completion; activated reserves start at wake completion). The
reconstructed below-floor duration differs from the engine-recorded value by **1.8 %**
(280.3 vs 275.3 s), which bounds the reconstruction error of the deficit area. [DERIVED,
assumption-labeled]

## 3. The causal decomposition [DERIVED + HYPOTHESIS]

1. **[DERIVED]** Blocks-per-closed-round is *equal within 1 %* (0.750 vs 0.758). The
   accepted-block deficit at the audit seed (162 → 135) is therefore driven almost
   entirely by the **closed-round deficit** (216 → 178 = 38 rounds), i.e. by
   round-duration **inflation** (mean +0.297 s/round × 178 rounds ≈ 52.8 s of horizon),
   not by lower per-round success.
2. **[OBSERVED]** The medians are identical (1.147 s) while the means differ — the
   inflation lives in the **tail rounds** (the no-block/aborted rounds that must exhaust
   the whole claimed domain), not in typical rounds.
3. **[DERIVED]** Activation churn is extreme: 328 wakes in 178 rounds (1.84/round). The
   four reserves spend **239 s waking versus 81 s hashing** — a 3:1 wake-to-work ratio.
   102 of 328 wakes (31 %) are cancelled at round close and contribute zero work.
4. **[DERIVED + HYPOTHESIS]** The tail inflation is **quantized at exactly +1.0 s** — the
   activation wake latency: M01's no-block tail rounds close at exactly 2.0 s
   (p90 = p95 = max = 2.0) while M03's close at exactly 3.0 s (p90 = p95 = max = 3.0),
   with medians essentially unchanged. This is strong direct evidence that **wake-latency
   serialization on the tail-round critical path dominates the inflation**: a tail round
   cannot close until its late-seated reserve wake (1.0 s) and the subsequent
   reserve-slice hashing complete, and the slice hashing fits inside the same 1.0 s
   quantum on the event grid. Wake latency is still **not claimed as the strictly sole
   cause** — reserve-slice tail hashing (81 s total) shares the added quantum, and the
   per-round split inside the 1.0 s is below the grid's resolution.
   **[UNRESOLVED below 1.0 s precision.]**
5. **[DERIVED]** The floor is *structurally* unattainable most of the time: the maximum
   deficit reaches the full floor value (3 200), the deficit area is ≈ 840 k hash·s, and
   every seed logs ~1 000 unattainable observations. With zero tolerance, a floor breach
   opens as soon as enough primaries exhaust; reserves that then wake are (a) delayed
   1.0 s, (b) small in rate, and (c) frequently cancelled at round close — so recovery
   almost never completes before the round ends.
6. **[OBSERVED]** M03 consumes *less* energy than M01 (0.01488 vs 0.01653 kWh): the legacy
   controller pays its throughput cost **without** restoring capacity — the worst corner
   of the trade-off.

## 4. What the refined controller must therefore fix [HYPOTHESIS → design]

* **Churn**: one live activation batch per breach episode + hysteresis (0.78/0.80/0.82)
  + cooldown should cut the 1.84 seats/round and the 31 % cancel rate (targets H-R3).
* **Lateness**: predictive wake-ahead with lookahead = wake latency should start wakes
  *before* exhaustion, overlapping the 1.0 s latency with remaining primary work
  (targets H-R1/H-R2 round-inflation).
* **Honest capacity metric**: H_pipeline reports the incoming-wake forecast without
  polluting the physical H_effective (R5).
* **Tail work**: bounded suffix reassignment (R6, exploratory only) addresses the
  reserve-slice tail by letting woken capacity do useful work.

## 5. Uncertainties carried forward [UNRESOLVED]

* Per-seed depth metrics exist only for seed 0 (the preregistered audit scope); other
  seeds' compact records are consistent with the same mechanism but cannot prove it
  per-seed.
* The exact critical-path share of wake latency vs reserve-tail hashing in the 52.8 s
  inflation is not fully determined by the frozen artifacts.
* The engine's internal floor-observation time series (4 709 observations) was not
  serialized in the audit payload; the deficit area is a validated reconstruction
  (±1.8 %), not an engine-recorded integral.
