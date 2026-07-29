# STAGE 04 — Ablation Plan (Causal Attribution)

Each comparison changes exactly one variable, holding the rest constant, so the
final experiments can attribute effects causally. Primary metric in **bold**.

| # | Comparison | Changed variable | Held constant | Hypothesis | Metric(s) | Expected direction | Confounders |
|---|---|---|---|---|---|---|---|
| A1 | B0 vs B1 | template independence | H_total, power, duration, domain | common template creates duplicate evaluations | **duplicate rate**, distinct headers | B1 ≫ B0 duplicates | none in the abstraction |
| A2 | B1 vs B2 | randomized start | template=common, ranges none | randomized starts reduce overlap | **overlap / duplicate rate** | B2 < B1 | seed, start distribution |
| A3 | B2 vs B3 | disjoint ranges | template=common | formal partition removes overlap | **overlap** (→0), coverage | B3 = 0 overlap | allocation policy |
| A4 | B3/C1 vs C2 | post-range idle | ranges, template, power | idling after range completion saves energy | **total energy**, idle time | C2 ≤ C1 (0 when no early completion) | range/round-time ratio, μ |
| A5 | C2 @0 % vs @{5,10,20,30}% idle | idle power ratio | everything else | saving falls with idle power | **total energy**, saving fraction | monotone ↓ with ratio | idle-time fraction |
| A6 | homogeneous vs heterogeneous | hash-rate distribution | H_total, N | heterogeneity changes completion imbalance & C2 saving | energy, **fairness/imbalance**, stale | context-dependent | allocation policy (A?) |
| A7 | all active vs inactive fraction | inactive-miner fraction | N, H_total | inactive ranges raise exhaustion, lower coverage | **exhausted rounds**, coverage, interval | more inactive → more exhaustion | domain size |
| A8 | low vs high propagation delay | delay | all else | stale rises with delay | **legitimate stale rate** | monotone ↑ | interval, topology |
| A9 | μ (domain size) levels | nonce-domain size | H_total, B | μ controls exhaustion & coverage | **exhaustion prob**, interval | μ↓ → exhaustion↑ | interval calibration |
| A10 | coordination excluded vs configured | coordination energy | all else | coordination overhead reduces net saving | **total energy** (coordination term) | configured ≥ excluded | value not measured (kept separate) |

## Notes on confounded / null effects (already observed in dry-runs)

- **A1/A3 are about *coverage*, not total energy.** Because all miners hash the
  same wall-clock time, B0/B1/B2/B3 have (near) identical *total* energy; the
  effect surfaces in **energy per accepted block** (coverage → find rate), not
  total power. This must be reported as such.
- **A4 can be null.** Under symmetric homogeneous miners with μ ≥ 1, C2 = C1
  (no early completion → no idle). The ablation must include the regime where
  ranges complete early (μ < 1 or heterogeneous equal-range) to observe a
  non-zero A4 effect — otherwise the honest result is "no saving".
- **A10 coordination energy is never invented**; the excluded case is the
  idealized lower bound, the configured case is a labelled sensitivity.
