# Stage 7 — Scientific Number Audit

Every scientific value inserted in red into draft-43 is taken verbatim from a
machine-readable Stage-6A output; no value was manually approximated where a
machine-readable value exists.

| Inserted value (red) | Exact source | Location |
|----------------------|--------------|----------|
| Total fixed-horizon energy **8.420833333 kWh** | `results/…/stage_06/diagnostics/a1_invariant.json` (`anchor_kwh`) | Abstract, §7.1 notice, §7.4.1–7.4.3, §8.2–8.3 |
| Aggregate hash rate **141 TH/s**, efficiency **21.5 J/TH**, horizon **10,000 s**, aggregate power **3031.5 W** | `s6_common.py` constants; thesis Table 6.1 | Abstract, §7.1, §7.4 |
| A1 max relative deviation **3.6e-16** (< 1e-6) | `a1_invariant.json` (`max_abs_deviation_kwh` / anchor) | §7.4.2 |
| H1 ordering **B1 > B2 > B3/C1**; **150** physical pairs; **30** seed clusters; B3/C1 duplicates **0** | `models/analysis_bundle.json` H1; `STAGE_06A_DEPENDENCE_AUDIT.md` | §8.3 |
| H3 identity max absolute residual **7.1e-15 kWh**, tolerance **1e-9**, **0** failures, **570** C2 runs | `results/…/stage_06a/diagnostics/h3_idle_saving_identity.csv`; `STAGE_06A_H3_IDENTITY_AUDIT.md` | §7.4.3, Abstract |
| H7 count-rate; N=100/500 separate; no binomial/Wilson; delay 0 → 0 observed | `diagnostics/h7_secondary.json`; `STAGE_06A_H7_INTERVAL_AUDIT.md` | §7.4.3, §7.1 |

## Consistency check vs Stage 6A

No red-inserted number conflicts with Stage 6A. The **obsolete black-text figures** that
conflict with Stage 6A (abstract "98–99% / 0.454 vs 33.078 kWh at 400 miners"; §7.4.1
"7.90 vs 0.131 kWh, 98.3%"; miner-count energy scaling) are each **flagged and superseded**
by an adjacent red correction citing the 8.420833333 kWh invariant. Table 6.1's frozen
parameters (141 TH/s, 21.5 J/TH, 10,000 s) are retained and are exactly the parameters
that imply the invariant, so the corrected narrative is now internally consistent with the
thesis's own experimental table.

**Number audit: PASS** — all inserted values match Stage-6A machine-readable outputs; all
conflicting legacy values are superseded in red.
