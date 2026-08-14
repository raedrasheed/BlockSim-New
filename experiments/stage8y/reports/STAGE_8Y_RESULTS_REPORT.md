# STAGE 8Y — RESULTS REPORT

Generated: 2026-08-14T18:29:37Z  
Config hash: `2d7344a1dac41b6a3484536e18939f294bff62d32a67310254f9a41fc7dfb0d0`  
Revision: 1

## 1. Research question

> Can PoCol exploit heterogeneous miner capabilities, energy-aware allocation, coordinated low-power participation and adaptive reserve activation to reduce total network energy by more than 50 % relative to matched traditional PoW while retaining at least 90 %, and preferably at least 95 %, of accepted-block production?

## 2. Headline answer

| Question | Answer |
|---|---|
| > 50 % saving reached at all? | **YES** |
| > 50 % survives a non-idealized α (> 0)? | **YES** |
| Highest α still reaching > 50 % | **0.05** |
| > 50 % with ≥ 90 % block retention? | **NO** (0 configurations) |
| > 50 % with ≥ 95 % block retention? | **NO** (0 configurations) |
| Best block retention among > 50 % configurations | **68.77%** |
| Maximum saving observed | 53.87% |

## 3. Energy saving by policy and α (all compositions and N pooled)

| Policy | α | Saving mean | 95 % CI | > 50 %? |
|---|---|---|---|---|
| P0_ALL | 0.0 | 0.23% | [0.22%, 0.23%] | no |
| P0_ALL | 0.05 | 0.22% | [0.21%, 0.22%] | no |
| P0_ALL | 0.1 | 0.20% | [0.20%, 0.21%] | no |
| P0_ALL | 0.25 | 0.17% | [0.16%, 0.17%] | no |
| P0_ALL | 0.5 | 0.11% | [0.11%, 0.12%] | no |
| P3_ENERGY | 0.0 | 48.54% | [47.82%, 49.26%] | no |
| P3_ENERGY | 0.05 | 46.11% | [45.43%, 46.80%] | no |
| P3_ENERGY | 0.1 | 43.69% | [43.04%, 44.34%] | no |
| P3_ENERGY | 0.25 | 36.40% | [35.86%, 36.95%] | no |
| P3_ENERGY | 0.5 | 24.27% | [23.91%, 24.63%] | no |
| P4_RESERVE | 0.0 | 45.02% | [44.45%, 45.59%] | no |
| P4_RESERVE | 0.05 | 42.77% | [42.23%, 43.31%] | no |
| P4_RESERVE | 0.1 | 40.52% | [40.01%, 41.03%] | no |
| P4_RESERVE | 0.25 | 33.77% | [33.34%, 34.19%] | no |
| P4_RESERVE | 0.5 | 22.51% | [22.23%, 22.79%] | no |

## 4. Block retention and latency

| comp | N | policy | blocks PoW | blocks PoCol | retention | 95 % CI | latency ratio |
|---|---|---|---|---|---|---|---|
| H0 | 100 | P0_ALL | 17.17 | 17.17 | 100.00% | [100.00%, 100.00%] | 1.000 |
| H0 | 100 | P3_ENERGY | 17.17 | 10.77 | 63.98% | [58.82%, 69.14%] | 1.836 |
| H0 | 100 | P4_RESERVE | 17.17 | 9.63 | 57.42% | [52.63%, 62.21%] | 1.934 |
| H0 | 300 | P0_ALL | 16.13 | 16.13 | 100.00% | [100.00%, 100.00%] | 1.000 |
| H0 | 300 | P3_ENERGY | 16.13 | 9.53 | 59.41% | [53.75%, 65.08%] | 2.076 |
| H0 | 300 | P4_RESERVE | 16.13 | 8.80 | 54.88% | [50.26%, 59.50%] | 2.237 |
| H0 | 500 | P0_ALL | 16.50 | 16.47 | 99.76% | [99.27%, 100.25%] | 0.986 |
| H0 | 500 | P3_ENERGY | 16.50 | 9.93 | 59.96% | [55.07%, 64.85%] | 2.056 |
| H0 | 500 | P4_RESERVE | 16.50 | 9.43 | 59.03% | [53.20%, 64.85%] | 1.976 |
| H2 | 100 | P0_ALL | 16.67 | 16.63 | 99.86% | [99.58%, 100.15%] | 0.998 |
| H2 | 100 | P3_ENERGY | 16.67 | 10.63 | 64.48% | [59.87%, 69.10%] | 1.808 |
| H2 | 100 | P4_RESERVE | 16.67 | 9.87 | 59.75% | [55.46%, 64.03%] | 2.062 |
| H2 | 300 | P0_ALL | 17.70 | 17.60 | 99.54% | [98.85%, 100.23%] | 0.997 |
| H2 | 300 | P3_ENERGY | 17.70 | 11.33 | 64.42% | [59.14%, 69.70%] | 1.773 |
| H2 | 300 | P4_RESERVE | 17.70 | 10.10 | 57.65% | [52.75%, 62.55%] | 1.761 |
| H2 | 500 | P0_ALL | 16.53 | 16.47 | 99.49% | [98.60%, 100.39%] | 0.990 |
| H2 | 500 | P3_ENERGY | 16.53 | 10.43 | 63.15% | [58.91%, 67.39%] | 1.625 |
| H2 | 500 | P4_RESERVE | 16.53 | 9.73 | 59.33% | [54.88%, 63.78%] | 1.574 |
| H4 | 100 | P0_ALL | 17.30 | 17.23 | 99.69% | [98.77%, 100.61%] | 0.997 |
| H4 | 100 | P3_ENERGY | 17.30 | 10.87 | 63.12% | [57.71%, 68.54%] | 1.617 |
| H4 | 100 | P4_RESERVE | 17.30 | 10.23 | 60.18% | [55.99%, 64.37%] | 1.529 |
| H4 | 300 | P0_ALL | 16.63 | 16.70 | 100.39% | [99.83%, 100.95%] | 0.990 |
| H4 | 300 | P3_ENERGY | 16.63 | 11.33 | 68.77% | [63.51%, 74.02%] | 1.502 |
| H4 | 300 | P4_RESERVE | 16.63 | 10.27 | 62.78% | [57.21%, 68.36%] | 1.823 |
| H4 | 500 | P0_ALL | 17.03 | 16.93 | 99.58% | [98.74%, 100.42%] | 0.992 |
| H4 | 500 | P3_ENERGY | 17.03 | 10.43 | 62.29% | [56.53%, 68.04%] | 1.805 |
| H4 | 500 | P4_RESERVE | 17.03 | 9.50 | 56.79% | [51.84%, 61.74%] | 1.778 |

## 5. Energy-saving decomposition (mandatory)

Because every miner is in exactly one state and WAKING is charged at full active power, `P_N·T = pw_active + pw_waking + pw_low + pw_standby` holds exactly, so the saving is exactly `(1−α)·(pw_low + pw_standby)`. Two orthogonal exact decompositions are reported.

| comp | policy | share: reduced participation | share: efficient selection | share: post-range | share: reserve standby | SelectivityGain |
|---|---|---|---|---|---|---|
| H0 | P0_ALL | 100.00% | 0.00% | 100.00% | 0.00% | 1.000 |
| H0 | P3_ENERGY | 100.00% | -0.00% | 0.39% | 99.61% | 1.000 |
| H0 | P4_RESERVE | 100.53% | -0.53% | 61.99% | 38.01% | 0.995 |
| H2 | P0_ALL | 100.05% | -0.05% | 100.00% | 0.00% | 1.000 |
| H2 | P3_ENERGY | 74.68% | 25.32% | 0.21% | 99.79% | 1.339 |
| H2 | P4_RESERVE | 94.14% | 5.86% | 48.44% | 51.56% | 1.063 |
| H4 | P0_ALL | 100.03% | -0.03% | 100.00% | 0.00% | 1.000 |
| H4 | P3_ENERGY | 77.19% | 22.81% | 0.23% | 99.77% | 1.296 |
| H4 | P4_RESERVE | 95.35% | 4.65% | 51.01% | 48.99% | 1.049 |

`dE_stale = 0` by construction: an ACTIVE miner draws the same power whether its work is useful or stale, so eliminating stale work does not reduce energy unless it also reduces active time. The stale-work *evaluation* difference is reported in Table J as a physical-work diagnostic and is deliberately **not** folded into the energy identity.

## 6. Security-hash analysis

| comp | N | policy | mean security hash fraction | min instantaneous |
|---|---|---|---|---|
| H0 | 100 | P0_ALL | 99.81% | 0.00% |
| H0 | 100 | P3_ENERGY | 59.87% | 0.00% |
| H0 | 100 | P4_RESERVE | 56.65% | 0.00% |
| H0 | 100 | POW | 100.00% | 100.00% |
| H0 | 300 | P0_ALL | 99.76% | 0.00% |
| H0 | 300 | P3_ENERGY | 59.84% | 0.00% |
| H0 | 300 | P4_RESERVE | 56.81% | 0.00% |
| H0 | 300 | POW | 100.00% | 100.00% |
| H0 | 500 | P0_ALL | 99.75% | 0.00% |
| H0 | 500 | P3_ENERGY | 60.02% | 0.00% |
| H0 | 500 | P4_RESERVE | 57.60% | 0.00% |
| H0 | 500 | POW | 100.00% | 100.00% |
| H2 | 100 | P0_ALL | 99.81% | 0.00% |
| H2 | 100 | P3_ENERGY | 60.03% | 0.00% |
| H2 | 100 | P4_RESERVE | 55.82% | 0.00% |
| H2 | 100 | POW | 100.00% | 100.00% |
| H2 | 300 | P0_ALL | 99.77% | 0.00% |
| H2 | 300 | P3_ENERGY | 59.85% | 0.00% |
| H2 | 300 | P4_RESERVE | 56.40% | 0.00% |
| H2 | 300 | POW | 100.00% | 100.00% |
| H2 | 500 | P0_ALL | 99.75% | 0.00% |
| H2 | 500 | P3_ENERGY | 59.92% | 0.00% |
| H2 | 500 | P4_RESERVE | 56.42% | 0.00% |
| H2 | 500 | POW | 100.00% | 100.00% |
| H4 | 100 | P0_ALL | 99.81% | 0.00% |
| H4 | 100 | P3_ENERGY | 60.02% | 0.00% |
| H4 | 100 | P4_RESERVE | 56.31% | 0.00% |
| H4 | 100 | POW | 100.00% | 100.00% |
| H4 | 300 | P0_ALL | 99.77% | 0.00% |
| H4 | 300 | P3_ENERGY | 60.00% | 0.00% |
| H4 | 300 | P4_RESERVE | 56.74% | 0.00% |
| H4 | 300 | POW | 100.00% | 100.00% |
| H4 | 500 | P0_ALL | 99.75% | 0.00% |
| H4 | 500 | P3_ENERGY | 59.85% | 0.00% |
| H4 | 500 | P4_RESERVE | 56.02% | 0.00% |
| H4 | 500 | POW | 100.00% | 100.00% |

Reducing the active set reduces the instantaneous cost of attacking the chain. Block-retention parity does **not** imply unchanged security and is not presented as if it did.

## 7. Fairness

| comp | policy | participation share by device | reward share by device | Gini (active time) | miners never active |
|---|---|---|---|---|---|
| H0 | P0_ALL | S21PRO:100.0% | S21PRO:100.0% | 7.914e-05 | 0.0 |
| H0 | P3_ENERGY | S21PRO:100.0% | S21PRO:100.0% | 0.399 | 119.7 |
| H0 | P4_RESERVE | S21PRO:100.0% | S21PRO:100.0% | 0.080 | 0.0 |
| H0 | POW | S21PRO:100.0% | S21PRO:100.0% | 0.000 | 0.0 |
| H2 | P0_ALL | S21PRO:50.0%, S19JPRO:50.0% | S21PRO:71.8%, S19JPRO:28.2% | 7.962e-05 | 0.0 |
| H2 | P3_ENERGY | S21PRO:99.2%, S19JPRO:0.8% | S21PRO:99.7%, S19JPRO:0.3% | 0.564 | 169.7 |
| H2 | P4_RESERVE | S21PRO:59.3%, S19JPRO:40.7% | S21PRO:77.1%, S19JPRO:22.9% | 0.111 | 0.0 |
| H2 | POW | S21PRO:50.0%, S19JPRO:50.0% | S21PRO:71.9%, S19JPRO:28.1% | 0.000 | 0.0 |
| H4 | P0_ALL | S21PRO:20.0%, S19XP:30.0%, S19JPRO:50.0% | S21PRO:33.1%, S19XP:33.6%, S19JPRO:33.3% | 7.963e-05 | 0.0 |
| H4 | P3_ENERGY | S21PRO:42.4%, S19XP:57.6%, S19JPRO:0.0% | S21PRO:51.7%, S19XP:48.3%, S19JPRO:0.0% | 0.530 | 159.0 |
| H4 | P4_RESERVE | S21PRO:24.0%, S19XP:35.2%, S19JPRO:40.8% | S21PRO:36.8%, S19XP:35.5%, S19JPRO:27.7% | 0.107 | 0.0 |
| H4 | POW | S21PRO:20.0%, S19XP:30.0%, S19JPRO:50.0% | S21PRO:33.5%, S19XP:33.4%, S19JPRO:33.1% | 0.000 | 0.0 |

## 8. Physical work and the duplicate distinction

| policy | W_total mean | exact duplicate ratio | nonce-value reuse ratio |
|---|---|---|---|
| P0_ALL | 5.4279e+20 | 0.0000% | 100.000000% |
| P3_ENERGY | 3.2606e+20 | 0.0000% | 100.000000% |
| P4_RESERVE | 3.0857e+20 | 0.0000% | 100.000000% |
| POW | 5.4410e+20 | 0.0000% | 100.000000% |
| POW_CT | 5.0700e+20 | 32.7886% | 100.000000% |

Exact-input duplication requires an identical full hash input `(template, candidate index)`. Traditional PoW miners build distinct templates, so their exact duplicate work is zero even though nonce-value reuse is essentially total. Only the clearly-labelled secondary Common-Template Independent PoW comparator produces real duplicates.

## 9. Long-horizon confirmation

| comp | policy | α | saving (10 000 s) | saving (100 000 s) | Δ |
|---|---|---|---|---|---|
| H0 | P0_ALL | 0.0 | 0.24% | 0.25% | 0.01% |
| H0 | P0_ALL | 0.1 | 0.22% | 0.23% | 0.01% |
| H0 | P0_ALL | 0.25 | 0.18% | 0.19% | 0.01% |
| H0 | P3_ENERGY | 0.0 | 40.16% | 40.17% | 0.01% |
| H0 | P3_ENERGY | 0.1 | 36.15% | 36.16% | 0.01% |
| H0 | P3_ENERGY | 0.25 | 30.12% | 30.13% | 0.01% |
| H0 | P4_RESERVE | 0.0 | 42.96% | 42.56% | -0.40% |
| H0 | P4_RESERVE | 0.1 | 38.67% | 38.31% | -0.36% |
| H0 | P4_RESERVE | 0.25 | 32.22% | 31.92% | -0.30% |
| H2 | P0_ALL | 0.0 | 0.23% | 0.25% | 0.02% |
| H2 | P0_ALL | 0.1 | 0.21% | 0.23% | 0.02% |
| H2 | P0_ALL | 0.25 | 0.17% | 0.19% | 0.02% |
| H2 | P3_ENERGY | 0.0 | 53.87% | 53.88% | 0.01% |
| H2 | P3_ENERGY | 0.1 | 48.48% | 48.50% | 0.01% |
| H2 | P3_ENERGY | 0.25 | 40.40% | 40.41% | 0.01% |
| H2 | P4_RESERVE | 0.0 | 46.30% | 44.95% | -1.36% |
| H2 | P4_RESERVE | 0.1 | 41.67% | 40.45% | -1.22% |
| H2 | P4_RESERVE | 0.25 | 34.73% | 33.71% | -1.02% |
| H4 | P0_ALL | 0.0 | 0.23% | 0.25% | 0.02% |
| H4 | P0_ALL | 0.1 | 0.21% | 0.23% | 0.02% |
| H4 | P0_ALL | 0.25 | 0.17% | 0.19% | 0.02% |
| H4 | P3_ENERGY | 0.0 | 51.86% | 51.88% | 0.02% |
| H4 | P3_ENERGY | 0.1 | 46.68% | 46.69% | 0.01% |
| H4 | P3_ENERGY | 0.25 | 38.90% | 38.91% | 0.01% |
| H4 | P4_RESERVE | 0.0 | 45.50% | 44.38% | -1.12% |
| H4 | P4_RESERVE | 0.1 | 40.95% | 39.95% | -1.00% |
| H4 | P4_RESERVE | 0.25 | 34.12% | 33.29% | -0.84% |

## 10. Acceptance criteria

See `STAGE_8Y_ACCEPTANCE_CRITERIA.md`. Outcome A NOT met; B NOT met; C MET; D NOT met; E NOT met.

## 11. Figures

* `figures/fig01_pareto_alpha_010.{png,pdf,svg}`
* `figures/fig01_pareto_alpha_0.{png,pdf,svg}`
* `figures/fig02_saving_by_policy.{png,pdf,svg}`
* `figures/fig03_retention_by_policy.{png,pdf,svg}`
* `figures/fig04_energy_per_block.{png,pdf,svg}`
* `figures/fig05_block_intervals.{png,pdf,svg}`
* `figures/fig06_active_hash_fraction_over_time.{png,pdf,svg}`
* `figures/fig07_active_power_fraction_over_time.{png,pdf,svg}`
* `figures/fig08_reserve_activation_trajectory.{png,pdf,svg}`
* `figures/fig09_residence_by_hardware.{png,pdf,svg}`
* `figures/fig10_power_weighted_residence.{png,pdf,svg}`
* `figures/fig11_saving_vs_alpha.{png,pdf,svg}`
* `figures/fig12_saving_vs_wake_delay.{png,pdf,svg}`
* `figures/fig13_saving_vs_active_hash_fraction.{png,pdf,svg}`
* `figures/fig14_composition_vs_saving.{png,pdf,svg}`
* `figures/fig15_composition_vs_retention.{png,pdf,svg}`
* `figures/fig16_duplicates_vs_nonce_reuse.{png,pdf,svg}`
* `figures/fig17_work_scaling.{png,pdf,svg}`
* `figures/fig18_energy_scaling.{png,pdf,svg}`
* `figures/fig19_selectivity_gain.{png,pdf,svg}`
* `figures/fig20_long_horizon_validation.{png,pdf,svg}`

## 12. Limitations

See `STAGE_8Y_LIMITATIONS.md`, which must be read before quoting any number from this report.

