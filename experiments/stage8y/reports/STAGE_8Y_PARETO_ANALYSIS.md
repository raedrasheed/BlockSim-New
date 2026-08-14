# STAGE 8Y — PARETO ANALYSIS

Generated: 2026-08-14T18:29:37Z

The empirical frontier is computed over **all confirmatory configurations** (composition × N × policy × α), not by picking the single largest saving. A configuration is Pareto-optimal when no other configuration is at least as good on both energy saving and block retention and strictly better on one.

## Region occupancy

| Region | Configurations |
|---|---|
| >50 % saving AND ≥95 % retention | **0** |
| >50 % saving AND 90–95 % retention | **0** |
| >50 % saving AND <90 % retention | **9** |
| ≤50 % saving | **126** |

## Pareto-optimal configurations

| Configuration | Saving | Retention | mean active hash | mean active power | E/block change | mean security hash | min security hash | main source | outcome |
|---|---|---|---|---|---|---|---|---|---|
| P3_ENERGY / H2 / N=300 / alpha_0 | 53.87% | 64.42% | 59.85% | 46.13% | -24.36% | 59.85% | 0.00% | reduced hash participation (75% of ΔE); state origin: reserve standby residence | C (idealized alpha) |
| P3_ENERGY / H2 / N=100 / alpha_0 | 53.28% | 64.48% | 60.03% | 46.72% | -25.29% | 60.03% | 0.00% | reduced hash participation (75% of ΔE); state origin: reserve standby residence | C (idealized alpha) |
| P3_ENERGY / H4 / N=300 / alpha_0 | 51.86% | 68.77% | 60.00% | 48.14% | -27.30% | 60.00% | 0.00% | reduced hash participation (77% of ΔE); state origin: reserve standby residence | C (idealized alpha) |
| P0_ALL / H4 / N=500 / alpha_0 | 0.25% | 99.58% | 99.75% | 99.75% | 0.05% | 99.75% | 0.00% | reduced hash participation (100% of ΔE); state origin: post-range low-power residence | D |
| P0_ALL / H0 / N=500 / alpha_0 | 0.25% | 99.76% | 99.75% | 99.75% | 0.02% | 99.75% | 0.00% | reduced hash participation (100% of ΔE); state origin: post-range low-power residence | D |
| P0_ALL / H0 / N=300 / alpha_0 | 0.24% | 100.00% | 99.76% | 99.76% | -0.25% | 99.76% | 0.00% | reduced hash participation (100% of ΔE); state origin: post-range low-power residence | D |
| P0_ALL / H4 / N=300 / alpha_0 | 0.23% | 100.39% | 99.77% | 99.77% | -0.59% | 99.77% | 0.00% | reduced hash participation (100% of ΔE); state origin: post-range low-power residence | D |

This is the table that makes the cost of energy saving impossible to hide: every point that clears 50 % also states what it gave up in block retention, in active hash capacity and in security hash fraction.

