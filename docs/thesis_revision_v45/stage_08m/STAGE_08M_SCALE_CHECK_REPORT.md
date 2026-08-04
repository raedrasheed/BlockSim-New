# Stage 8M — Exploratory Scale-Check Report (DESCRIPTIVE ONLY)

**These two 141-miner runs are non-inferential.** They entered no permutation test, no
bootstrap interval and no confirmatory statement, and they carry no hypothesis
(`hypotheses = NONE` in the frozen matrix). One existing PILOT seed each. They exist to show
that the minimal 20-miner confirmatory core is not an artifact of small scale in **runtime,
memory, integrity or direction** — nothing more.

| | X01_SCALE_HET_IDLE | X02_SCALE_HET_IDLE_FLOOR |
|---|---|---|
| miners / domain / batch | 141 / 4000 / 50 | 141 / 4000 / 50 |
| floor | disabled | 0.80 × H0(141, het) = 22 480 |
| seed | PILOT index 2 | PILOT index 3 |
| status | COMPLETED | COMPLETED |
| all integrity gates | PASS | PASS |
| wall / peak RSS | 7.7 s / 109 MB | 25.1 s / 151 MB |
| rounds accepted | 283 | 268 |
| E_idle (kWh) | 0.109566 | 0.107020 |
| E_power_null (kWh) | 0.252625 | 0.252625 |
| relative reduction (descriptive) | 0.5663 | 0.5764 |
| total_duration_below_floor (s) | 0.0 | 290.81 |
| floor_unattainable_count | 0 | 2 494 |

Descriptive observations (no inference):

* **Direction sanity holds at scale.** The per-run relative reduction at 141 miners
  (≈ 0.57) has the same sign and similar magnitude as the 20-miner confirmatory estimates
  (H-M1 mean 0.5387), so the confirmatory direction is not a small-scale artifact.
* **Integrity holds at scale.** Every deterministic gate passes at 141 miners.
* **The floor-degradation pattern recurs at scale.** X02 spends 290.8 s of a 300 s horizon
  below the floor with 2 494 unattainable observations — descriptively consistent with the
  confirmatory H-M3 limit failures at 20 miners. This corroborates (but cannot itself
  establish) that the H-M3 result reflects the engine's wake/floor semantics rather than
  the small confirmatory scale.
* **Resource feasibility.** Worst case 25.1 s / 151 MB per run — far inside the Stage-7M
  ceilings.

No confidence interval, p-value or pass/fail is attached to any number above, and none may
be derived from them in later stages: the frozen exclusion (`X01/X02 never enter any
estimator`) is permanent.
