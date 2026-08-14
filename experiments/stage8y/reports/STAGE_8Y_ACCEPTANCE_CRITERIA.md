# STAGE 8Y — ACCEPTANCE CRITERIA

Generated: 2026-08-14T18:29:37Z

Criteria were preregistered in `config/stage8y_config.py::ACCEPTANCE` before any confirmatory run and are evaluated here verbatim.

| Threshold | Value |
|---|---|
| Energy saving | > 50% |
| Block retention (strong) | ≥ 95% |
| Block retention (moderate) | ≥ 90% |
| Latency ratio | ≤ 1.10 |

## Outcomes

| Outcome | Definition | Met | Configurations |
|---|---|---|---|
| **A** strong success | Saving > 50% AND BlockRetention >= 95% AND LatencyRatio <= 1.10 under at least one confirmatory NON-IDEALIZED alpha (alpha > 0). | NO | 0 |
| **B** moderate success | Saving > 50% AND BlockRetention >= 90% under at least one confirmatory configuration. | NO | 0 |
| **C** energy/performance trade-off | Saving > 50% but BlockRetention < 90%. | YES | 9 |
| **D** threshold not reached | No confirmatory configuration achieves Saving > 50%. | NO | — |
| **E** idealized only | Saving > 50% only under idealized assumptions (alpha = 0 or t_wake = 0) and not under conservative ones. | NO | — |

## Key quantities

| Question | Answer |
|---|---|
| Any configuration > 50 % saving? | YES |
| Any **non-idealized** (α > 0) configuration > 50 %? | YES |
| Highest α still reaching > 50 % | 0.05 |
| Maximum saving observed | 53.87% |
| Configurations with > 50 % saving AND ≥ 90 % retention | 0 |
| Configurations with > 50 % saving AND ≥ 95 % retention | 0 |
| Best retention among > 50 % configurations | 68.77% |

