# STAGE 8X — RESULTS REPORT

Generated: 2026-08-14T17:08:02Z  
Config hash: `b871c98ea1c612cdbd5a2223ff017610d908ae78fe08d509113f86983218cebf`  
Revision: 1

## 1. Experimental objective

Stage 8X asks whether PoCol's post-range low-power mechanism reduces *physical electrical energy* relative to traditional competitive PoW when every miner is a fixed, real ASIC. Unlike earlier macro experiments it does **not** hold the aggregate network hash rate constant: each miner is one Bitmain Antminer S21 Pro, so aggregate hash rate and aggregate active power both grow with the miner population, and difficulty is coupled to that growth.

## 2. Research question

> Under fixed per-miner ASIC hashing capacity and matched hardware, how does PoCol with post-range low-power operation compare with traditional competitive PoW as miner population scales, in terms of total energy consumption, physical hashing work, duplicate work, accepted block production, and block/round latency?

The design admits a negative, neutral or positive answer; nothing in it presumes PoCol is superior.

## 3. Hardware model

| Quantity | Value | Status |
|---|---|---|
| ASIC | Bitmain Antminer S21 Pro | official nominal specification |
| Per-miner hash rate h | 234 TH/s | official nominal specification |
| Per-miner active power P_active | 3510 W | official nominal specification |
| Efficiency eta | 15 J/TH | official nominal specification |
| Consistency | 234 x 15 = 3510 W | verified in test |
| LP0: P_low = 0.00 P_active | 0.0 W | **experimental sensitivity assumption — idealized lower bound (0 W); not a vendor-certified mode** |
| LP10: P_low = 0.10 P_active | 351.0 W | **experimental sensitivity assumption — 10% of active power; not a vendor-certified mode** |
| LP25: P_low = 0.25 P_active | 877.5 W | **experimental sensitivity assumption — 25% of active power; not a vendor-certified mode** |
| LP50: P_low = 0.50 P_active | 1755.0 W | **experimental sensitivity assumption — 50% of active power; not a vendor-certified mode** |

Source note: the active values are the official Bitmain S21 Pro nominal specification. **Bitmain does not publish the low-power states used here**; LP0/LP10/LP25/LP50 are experimental sensitivity assumptions only.

## 4. Exact parameter table

| Parameter | Value |
|---|---|
| Network sizes N | [100, 200, 300, 400, 500] |
| Seeds | 30 fresh paired master seeds |
| Horizon T | 10000 s |
| Target block interval | 600 s |
| Epoch sweep tau | 600 s |
| Propagation delay | Exp(mean 0.42 s), broadcast to all peers |
| Acceptance rule | longest chain, deterministic first-seen tie-break |
| Transactions | disabled identically for both protocols (see limitations) |
| Primary protocols | ['POW', 'POCOL'] |

## 5. Derivation of aggregate hash rate and power

```
H(N)          = N x 234 TH/s              (computed, never tabulated)
P_active(N)   = N x 3510 W
```

| N | H(N) | P_active(N) |
|---|---|---|
| 100 | 23.4 PH/s | 351 kW |
| 200 | 46.8 PH/s | 702 kW |
| 300 | 70.2 PH/s | 1053 kW |
| 400 | 93.6 PH/s | 1404 kW |
| 500 | 117.0 PH/s | 1755 kW |

Verified programmatically in `test_expected_scaling_table_matches_brief`.

## 6. Derivation and calibration of difficulty

With SHA256d treated as uniform on [0, 2^256), the per-candidate success probability is q = target/2^256 = 1/(D x 2^32), so a network at H_N candidates/s produces blocks at rate H_N q. Setting the expected interval to I_target = 600 s:

```
D_N      = H_N * I_target / 2^32
q_N      = 1 / (H_N * I_target)
target_N = 2^256 / (D_N * 2^32)
```

so D_N is exactly proportional to H_N. A single D_N per N is handed to **both** protocols: D^PoW_N = D^PoCol_N identically. PoCol difficulty was never recalibrated.

| N | H_N (H/s) | D_N | q_N | E[hashes/block] |
|---|---|---|---|---|
| 100 | 2.3400e+16 | 3.268942e+09 | 7.122507e-20 | 1.4040e+19 |
| 200 | 4.6800e+16 | 6.537884e+09 | 3.561254e-20 | 2.8080e+19 |
| 300 | 7.0200e+16 | 9.806827e+09 | 2.374169e-20 | 4.2120e+19 |
| 400 | 9.3600e+16 | 1.307577e+10 | 1.780627e-20 | 5.6160e+19 |
| 500 | 1.1700e+17 | 1.634471e+10 | 1.424501e-20 | 7.0200e+19 |

Empirical calibration over the 150 PoW primary runs: pooled mean accepted-block interval = **603.6 s** against the 600 s nominal target (2485 blocks).

## 7. Nonce-domain rationale

The per-epoch candidate domain is derived from the protocol parameters, not tuned:

```
S_N = H_N * tau_epoch          with tau_epoch = I_target = 600 s
L   = S_N / N = h * tau_epoch = 1.404e17 candidates per miner, identical at every N
```

so one epoch holds exactly one block's expected work and P(no solution in an epoch) = e^-1 = 0.36788 by construction. The Stage 8S/8U diagnostic domain of 1600 is not reused. Three exhaustion categories are counted separately: legitimate per-miner range completion, global domain exhaustion (which triggers the documented common-template refresh), and simulator artifact (**0 occurrences**). Observed exhaustion shares are compared with the closed-form prediction in Table G and figure `figD3`.

## 8. Seed rationale

Thirty fresh master seeds are derived from the Stage-8X-only namespace `BlockSim-New/Stage8X/PoCol-vs-PoW/AntminerS21Pro/rev1` and frozen to `outputs/stage8x_seeds.json`. Pilot seeds come from a disjoint sub-namespace so they can never enter the inferential dataset. At each (N, k) the PoW and PoCol runs receive the same master seed and the same purpose-split per-miner sub-streams, so miner i draws its k-th search outcome from the same stream under both protocols.

## 9. Energy-accounting equations

```
E_PoW      = sum_i P_active * t_active,i
E_PoCol(a) = sum_i [ P_active * t_active,i + a * P_active * t_low,i ]
t_active,i + t_low,i = T   for every miner        1 kWh = 3.6e6 J
```

Energy is computed only from measured state residencies. Conservation holds to 1.82e-12 s worst case across all 300 runs. alpha enters the accounting only: each PoCol trajectory is simulated once and re-priced four times.

## 10. Run matrix

* Primary physical runs: **300** = 5 N x 2 protocols x 30 seeds
* PoCol energy sensitivity observations: **600** = 150 x 4 alpha
* Declared secondary diagnostic runs: 420 (reported separately)
* Pilot runs: 45 (excluded from inference)

## 11. Validation results

Stage 8X validation suite: see `STAGE_8X_VALIDATION_REPORT.md`. Completeness audit: **PASS** (22/22 checks).

## 12. Summary statistics

### 12.1 Physical work (Table B)

| N | protocol | W_total (mean) | W_unique | W_duplicate | duplicate ratio | nonce-value reuse ratio |
|---|---|---|---|---|---|---|
| 100 | POW | 2.3400e+20 | 2.3400e+20 | 0.0000e+00 | 0.000000 | 1.000000 |
| 100 | POCOL | 2.3352e+20 | 2.3352e+20 | 0.0000e+00 | 0.000000 | 1.000000 |
| 200 | POW | 4.6800e+20 | 4.6800e+20 | 0.0000e+00 | 0.000000 | 1.000000 |
| 200 | POCOL | 4.6699e+20 | 4.6699e+20 | 0.0000e+00 | 0.000000 | 1.000000 |
| 300 | POW | 7.0200e+20 | 7.0200e+20 | 0.0000e+00 | 0.000000 | 1.000000 |
| 300 | POCOL | 7.0029e+20 | 7.0029e+20 | 0.0000e+00 | 0.000000 | 1.000000 |
| 400 | POW | 9.3600e+20 | 9.3600e+20 | 0.0000e+00 | 0.000000 | 1.000000 |
| 400 | POCOL | 9.3383e+20 | 9.3383e+20 | 0.0000e+00 | 0.000000 | 1.000000 |
| 500 | POW | 1.1700e+21 | 1.1700e+21 | 0.0000e+00 | 0.000000 | 1.000000 |
| 500 | POCOL | 1.1670e+21 | 1.1670e+21 | 0.0000e+00 | 0.000000 | 1.000000 |

Both primary protocols perform **zero exact-input duplicate work**. For PoCol this is by construction (common template, disjoint ranges) and is asserted in test. For traditional PoW it is because each miner owns a distinct template, so equal nonce values are not equal serialized candidates. The nonce-value reuse ratio is ~1.0 for every protocol, which is exactly the distinction the brief requires: nonce-value reuse is not exact-input duplication.

### 12.2 Service and latency (Table D)

| N | PoW blocks | PoCol blocks | PoW median interval (s) | PoCol median interval (s) | block retention | latency ratio |
|---|---|---|---|---|---|---|
| 100 | 16.30 | 16.13 | 431.3 | 437.5 | 0.9915 | 1.0192 |
| 200 | 16.60 | 16.57 | 433.0 | 435.0 | 0.9985 | 1.0072 |
| 300 | 15.73 | 15.67 | 456.2 | 456.4 | 0.9962 | 1.0000 |
| 400 | 17.27 | 17.17 | 431.8 | 427.0 | 0.9945 | 0.9829 |
| 500 | 16.93 | 16.90 | 430.2 | 429.4 | 0.9981 | 0.9975 |

### 12.3 Low-power residency (Table F)

| N | F_low (mean) | 95% CI | mean episode (s) | max episode (s) | miners entering low | mean simultaneous | transitions balanced |
|---|---|---|---|---|---|---|---|
| 100 | 2.049793e-03 | [1.888e-03, 2.212e-03] | 2.11 | 6.32 | 100.0% | 0.20 | True |
| 200 | 2.168084e-03 | [2.001e-03, 2.336e-03] | 2.35 | 7.94 | 100.0% | 0.43 | True |
| 300 | 2.434237e-03 | [2.248e-03, 2.620e-03] | 2.53 | 7.67 | 100.0% | 0.73 | True |
| 400 | 2.320709e-03 | [2.099e-03, 2.542e-03] | 2.63 | 8.12 | 100.0% | 0.93 | True |
| 500 | 2.568482e-03 | [2.326e-03, 2.811e-03] | 2.77 | 7.94 | 100.0% | 1.28 | True |

### 12.4 Energy (Table C)

| N | alpha case | PoW energy (kWh) | PoCol energy (kWh) | saving (%) | 95% CI (%) |
|---|---|---|---|---|---|
| 100 | LP0 | 975.000 | 973.001 | 0.2050 | [0.1888, 0.2212] |
| 100 | LP10 | 975.000 | 973.201 | 0.1845 | [0.1699, 0.1991] |
| 100 | LP25 | 975.000 | 973.501 | 0.1537 | [0.1416, 0.1659] |
| 100 | LP50 | 975.000 | 974.001 | 0.1025 | [0.0944, 0.1106] |
| 200 | LP0 | 1950.000 | 1945.772 | 0.2168 | [0.2001, 0.2336] |
| 200 | LP10 | 1950.000 | 1946.195 | 0.1951 | [0.1801, 0.2102] |
| 200 | LP25 | 1950.000 | 1946.829 | 0.1626 | [0.1500, 0.1752] |
| 200 | LP50 | 1950.000 | 1947.886 | 0.1084 | [0.1000, 0.1168] |
| 300 | LP0 | 2925.000 | 2917.880 | 0.2434 | [0.2248, 0.2620] |
| 300 | LP10 | 2925.000 | 2918.592 | 0.2191 | [0.2023, 0.2358] |
| 300 | LP25 | 2925.000 | 2919.660 | 0.1826 | [0.1686, 0.1965] |
| 300 | LP50 | 2925.000 | 2921.440 | 0.1217 | [0.1124, 0.1310] |
| 400 | LP0 | 3900.000 | 3890.949 | 0.2321 | [0.2099, 0.2542] |
| 400 | LP10 | 3900.000 | 3891.854 | 0.2089 | [0.1890, 0.2288] |
| 400 | LP25 | 3900.000 | 3893.212 | 0.1741 | [0.1575, 0.1906] |
| 400 | LP50 | 3900.000 | 3895.475 | 0.1160 | [0.1050, 0.1271] |
| 500 | LP0 | 4875.000 | 4862.479 | 0.2568 | [0.2326, 0.2811] |
| 500 | LP10 | 4875.000 | 4863.731 | 0.2312 | [0.2093, 0.2530] |
| 500 | LP25 | 4875.000 | 4865.609 | 0.1926 | [0.1744, 0.2109] |
| 500 | LP50 | 4875.000 | 4868.739 | 0.1284 | [0.1163, 0.1406] |

## 13. Paired statistical analysis

All comparisons are seed-paired (Delta = PoCol - PoW per seed). Normality of the paired differences is tested (Shapiro-Wilk) before choosing between the paired t-test and the Wilcoxon signed-rank test; the selected test is named per row. Holm-Bonferroni correction is applied within each metric family across the five network sizes. p-values are reported alongside magnitude, CI and effect size, never alone.

### energy_kWh_LP0

| N | mean Delta | 95% CI | median Delta | relative | test | p | Holm p | Cohen d_z | rank-biserial |
|---|---|---|---|---|---|---|---|---|---|
| 100 | -1.9985 | [-2.1566, -1.8405] | -1.9221 | -0.0020 | paired t-test | 1.4077e-21 | 4.2231e-21 | -4.7207 | -1.0000 |
| 200 | -4.2278 | [-4.5544, -3.9012] | -4.1402 | -0.0022 | paired t-test | 7.2800e-22 | 2.9120e-21 | -4.8338 | -1.0000 |
| 300 | -7.1201 | [-7.6648, -6.5755] | -6.9315 | -0.0024 | paired t-test | 5.5440e-22 | 2.7720e-21 | -4.8812 | -1.0000 |
| 400 | -9.0508 | [-9.9135, -8.1880] | -9.0302 | -0.0023 | paired t-test | 2.4266e-19 | 3.8977e-19 | -3.9172 | -1.0000 |
| 500 | -12.5213 | [-13.7054, -11.3373] | -12.5746 | -0.0026 | paired t-test | 1.9488e-19 | 3.8977e-19 | -3.9487 | -1.0000 |

### energy_kWh_LP10

| N | mean Delta | 95% CI | median Delta | relative | test | p | Holm p | Cohen d_z | rank-biserial |
|---|---|---|---|---|---|---|---|---|---|
| 100 | -1.7987 | [-1.9410, -1.6564] | -1.7299 | -0.0018 | paired t-test | 1.4077e-21 | 4.2231e-21 | -4.7207 | -1.0000 |
| 200 | -3.8050 | [-4.0989, -3.5111] | -3.7262 | -0.0020 | paired t-test | 7.2800e-22 | 2.9120e-21 | -4.8338 | -1.0000 |
| 300 | -6.4081 | [-6.8983, -5.9179] | -6.2384 | -0.0022 | paired t-test | 5.5440e-22 | 2.7720e-21 | -4.8812 | -1.0000 |
| 400 | -8.1457 | [-8.9222, -7.3692] | -8.1272 | -0.0021 | paired t-test | 2.4266e-19 | 3.8977e-19 | -3.9172 | -1.0000 |
| 500 | -11.2692 | [-12.3349, -10.2035] | -11.3172 | -0.0023 | paired t-test | 1.9488e-19 | 3.8977e-19 | -3.9487 | -1.0000 |

### energy_kWh_LP25

| N | mean Delta | 95% CI | median Delta | relative | test | p | Holm p | Cohen d_z | rank-biserial |
|---|---|---|---|---|---|---|---|---|---|
| 100 | -1.4989 | [-1.6175, -1.3803] | -1.4416 | -0.0015 | paired t-test | 1.4077e-21 | 4.2231e-21 | -4.7207 | -1.0000 |
| 200 | -3.1708 | [-3.4158, -2.9259] | -3.1052 | -0.0016 | paired t-test | 7.2800e-22 | 2.9120e-21 | -4.8338 | -1.0000 |
| 300 | -5.3401 | [-5.7486, -4.9316] | -5.1986 | -0.0018 | paired t-test | 5.5440e-22 | 2.7720e-21 | -4.8812 | -1.0000 |
| 400 | -6.7881 | [-7.4352, -6.1410] | -6.7727 | -0.0017 | paired t-test | 2.4266e-19 | 3.8977e-19 | -3.9172 | -1.0000 |
| 500 | -9.3910 | [-10.2791, -8.5030] | -9.4310 | -0.0019 | paired t-test | 1.9488e-19 | 3.8977e-19 | -3.9487 | -1.0000 |

### energy_kWh_LP50

| N | mean Delta | 95% CI | median Delta | relative | test | p | Holm p | Cohen d_z | rank-biserial |
|---|---|---|---|---|---|---|---|---|---|
| 100 | -0.9993 | [-1.0783, -0.9202] | -0.9611 | -0.0010 | paired t-test | 1.4077e-21 | 4.2231e-21 | -4.7207 | -1.0000 |
| 200 | -2.1139 | [-2.2772, -1.9506] | -2.0701 | -0.0011 | paired t-test | 7.2800e-22 | 2.9120e-21 | -4.8338 | -1.0000 |
| 300 | -3.5601 | [-3.8324, -3.2877] | -3.4658 | -0.0012 | paired t-test | 5.5440e-22 | 2.7720e-21 | -4.8812 | -1.0000 |
| 400 | -4.5254 | [-4.9568, -4.0940] | -4.5151 | -0.0012 | paired t-test | 2.4266e-19 | 3.8977e-19 | -3.9172 | -1.0000 |
| 500 | -6.2607 | [-6.8527, -5.6686] | -6.2873 | -0.0013 | paired t-test | 1.9488e-19 | 3.8977e-19 | -3.9487 | -1.0000 |

### accepted_blocks

| N | mean Delta | 95% CI | median Delta | relative | test | p | Holm p | Cohen d_z | rank-biserial |
|---|---|---|---|---|---|---|---|---|---|
| 100 | -0.1667 | [-0.3389, 0.0055] | 0.0000 | -0.0102 | Wilcoxon signed-rank | 0.0588 | 0.2939 | -0.3614 | -1.0000 |
| 200 | -0.0333 | [-0.1015, 0.0348] | 0.0000 | -0.0020 | Wilcoxon signed-rank | 0.3173 | 0.6346 | -0.1826 | -1.0000 |
| 300 | -0.0667 | [-0.1614, 0.0281] | 0.0000 | -0.0042 | Wilcoxon signed-rank | 0.1573 | 0.4719 | -0.2628 | -1.0000 |
| 400 | -0.1000 | [-0.2139, 0.0139] | 0.0000 | -0.0058 | Wilcoxon signed-rank | 0.0833 | 0.3331 | -0.3277 | -1.0000 |
| 500 | -0.0333 | [-0.1015, 0.0348] | 0.0000 | -0.0020 | Wilcoxon signed-rank | 0.3173 | 0.6346 | -0.1826 | -1.0000 |

### active_miner_seconds

| N | mean Delta | 95% CI | median Delta | relative | test | p | Holm p | Cohen d_z | rank-biserial |
|---|---|---|---|---|---|---|---|---|---|
| 100 | -2049.7931 | [-2211.9308, -1887.6554] | -1971.3895 | -0.0020 | paired t-test | 1.4077e-21 | 4.2231e-21 | -4.7207 | -1.0000 |
| 200 | -4336.1680 | [-4671.1339, -4001.2021] | -4246.4012 | -0.0022 | paired t-test | 7.2800e-22 | 2.9120e-21 | -4.8338 | -1.0000 |
| 300 | -7302.7124 | [-7861.3596, -6744.0653] | -7109.2362 | -0.0024 | paired t-test | 5.5440e-22 | 2.7720e-21 | -4.8812 | -1.0000 |
| 400 | -9282.8356 | [-10167.7290, -8397.9423] | -9261.7594 | -0.0023 | paired t-test | 2.4266e-19 | 3.8977e-19 | -3.9172 | -1.0000 |
| 500 | -12842.4099 | [-14056.8463, -11627.9734] | -12897.0412 | -0.0026 | paired t-test | 1.9488e-19 | 3.8977e-19 | -3.9487 | -1.0000 |

### total_evaluations

| N | mean Delta | 95% CI | median Delta | relative | test | p | Holm p | Cohen d_z | rank-biserial |
|---|---|---|---|---|---|---|---|---|---|
| 100 | -4.7965e+17 | [-5.1759e+17, -4.4171e+17] | -4.6131e+17 | -0.0020 | paired t-test | 1.4077e-21 | 4.2231e-21 | -4.7207 | -1.0000 |
| 200 | -1.0147e+18 | [-1.0930e+18, -9.3628e+17] | -9.9366e+17 | -0.0022 | paired t-test | 7.2800e-22 | 2.9120e-21 | -4.8338 | -1.0000 |
| 300 | -1.7088e+18 | [-1.8396e+18, -1.5781e+18] | -1.6636e+18 | -0.0024 | paired t-test | 5.5440e-22 | 2.7720e-21 | -4.8812 | -1.0000 |
| 400 | -2.1722e+18 | [-2.3792e+18, -1.9651e+18] | -2.1673e+18 | -0.0023 | paired t-test | 2.4266e-19 | 3.8977e-19 | -3.9172 | -1.0000 |
| 500 | -3.0051e+18 | [-3.2893e+18, -2.7209e+18] | -3.0179e+18 | -0.0026 | paired t-test | 1.9488e-19 | 3.8977e-19 | -3.9487 | -1.0000 |

### median_block_interval

| N | mean Delta | 95% CI | median Delta | relative | test | p | Holm p | Cohen d_z | rank-biserial |
|---|---|---|---|---|---|---|---|---|---|
| 100 | 6.2054 | [-5.7066, 18.1174] | 0.0000 | 0.0144 | Wilcoxon signed-rank | 0.0926 | 0.2778 | 0.1945 | 0.6000 |
| 200 | 2.0106 | [-2.1190, 6.1403] | 0.0000 | 0.0046 | Wilcoxon signed-rank | 0.0409 | 0.1913 | 0.1818 | 0.6970 |
| 300 | 0.2362 | [-1.3122, 1.7846] | 0.0000 | 5.1766e-04 | Wilcoxon signed-rank | 0.0383 | 0.1913 | 0.0570 | 0.6286 |
| 400 | -4.8853 | [-12.4061, 2.6355] | 0.0000 | -0.0113 | Wilcoxon signed-rank | 0.8785 | 0.8785 | -0.2426 | 0.0545 |
| 500 | -0.8218 | [-5.7111, 4.0675] | 0.0000 | -0.0019 | Wilcoxon signed-rank | 0.2026 | 0.4052 | -0.0628 | 0.4545 |

## 14. Sensitivity analysis

### 14.1 Low-power assumption alpha

Energy saving is exactly F_low x (1 - alpha) by construction, so it decays linearly in alpha. Means across N:

| alpha case | P_low (W) | mean saving (%) | min N saving (%) | max N saving (%) |
|---|---|---|---|---|
| LP0 | 0.0 | 0.2308 | 0.2050 | 0.2568 |
| LP10 | 351.0 | 0.2077 | 0.1845 | 0.2312 |
| LP25 | 877.5 | 0.1731 | 0.1537 | 0.1926 |
| LP50 | 1755.0 | 0.1154 | 0.1025 | 0.1284 |

### 14.2 Secondary S1 — common-template PoW comparator (X-PW-MT)

This comparator is **not** part of the primary energy comparison. It exists because exact-input duplication is degenerate (zero) for both primary protocols, so the duplicate-work axis can only be measured against miners that genuinely share one template.

| N | MT duplicate ratio | theoretical 1-(1-1/N)^N | MT blocks | PoW blocks | PoCol blocks | blocks lost to duplication |
|---|---|---|---|---|---|---|
| 100 | 0.3285 | 0.3660 | 11.27 | 16.30 | 16.13 | 30.9% |
| 200 | 0.3296 | 0.3670 | 10.73 | 16.60 | 16.57 | 35.3% |
| 300 | 0.3287 | 0.3673 | 11.50 | 15.73 | 15.67 | 26.9% |
| 400 | 0.3313 | 0.3674 | 10.87 | 17.27 | 17.17 | 37.1% |
| 500 | 0.3281 | 0.3675 | 11.63 | 16.93 | 16.90 | 31.3% |

### 14.3 Secondary S2 — PoCol epoch-allocation sensitivity

How much candidate space the common template allocates per epoch (tau_epoch = 600 s is the frozen primary value). Smaller allocations mean more frequent template agreement, hence more low-power residency **and** proportionally fewer blocks.

Because PoW is ACTIVE for the whole horizon, the saving columns below are the analytic identity F_low x (1 - alpha) rather than a per-seed paired statistic; the primary comparison in section 12.4 is fully seed-paired.

| N | tau (s) | frozen primary? | F_low | block retention | saving LP0 (%) | saving LP25 (%) |
|---|---|---|---|---|---|---|
| 100 | 600 | yes | 0.00205 | 0.9898 | 0.205 | 0.154 |
| 100 | 300 | no | 0.00540 | 1.0429 | 0.540 | 0.405 |
| 100 | 60 | no | 0.03284 | 1.0736 | 3.284 | 2.463 |
| 100 | 6 | no | 0.26522 | 0.7178 | 26.522 | 19.892 |
| 300 | 600 | yes | 0.00243 | 0.9958 | 0.243 | 0.183 |
| 300 | 300 | no | 0.00651 | 1.0445 | 0.651 | 0.488 |
| 300 | 60 | no | 0.03976 | 1.0339 | 3.976 | 2.982 |
| 300 | 6 | no | 0.30378 | 0.8326 | 30.378 | 22.783 |
| 500 | 600 | yes | 0.00257 | 0.9980 | 0.257 | 0.193 |
| 500 | 300 | no | 0.00695 | 0.9724 | 0.695 | 0.521 |
| 500 | 60 | no | 0.04294 | 0.9449 | 4.294 | 3.221 |
| 500 | 6 | no | 0.32048 | 0.7657 | 32.048 | 24.036 |

## 15. Causal decomposition

The brief requires the causal chain to be tested rather than assumed:

```
disjoint work allocation -> assigned-range completion -> low-power residency
     -> reduced active ASIC-time -> reduced energy
```

Each link is measured separately.

| Link | Evidence | Value |
|---|---|---|
| Duplicate-work reduction | exact duplicates PoCol vs PoW | 0 vs 0 (both zero: **no reduction is available against traditional PoW**) |
| Assigned-range completion | mean range completions per run | 2767.8 |
| Low-power residency | F_low pooled mean | 2.308261e-03 |
| Reduced active ASIC-time | mean active miner-seconds PoCol vs PoW | 2992837.2 vs 3000000.0 (0.2388% reduction) |
| Reduced energy | mean paired saving at LP0 | 0.2308% |

Duplicate-work reduction and energy reduction are therefore **distinct and non-substitutable quantities**: against traditional PoW there is no duplicate work to remove, yet a small energy reduction still occurs, and it is caused entirely by low-power residency during common-template agreement. The reverse statement — that duplicate-work reduction equals energy saving — is false in this experiment and is not made.

## 16. Figures

| Figure | File stem |
|---|---|
| fig01 aggregate hashrate vs N | `figures/fig01_aggregate_hashrate_vs_N.{png,pdf,svg}` |
| fig02 active power vs N | `figures/fig02_active_power_vs_N.{png,pdf,svg}` |
| fig03 total energy vs N | `figures/fig03_total_energy_vs_N.{png,pdf,svg}` |
| fig04 energy saving vs alpha | `figures/fig04_energy_saving_vs_alpha.{png,pdf,svg}` |
| fig05 energy saving vs N | `figures/fig05_energy_saving_vs_N.{png,pdf,svg}` |
| fig06 evaluations vs N | `figures/fig06_evaluations_vs_N.{png,pdf,svg}` |
| fig07 duplicate evaluations vs N | `figures/fig07_duplicate_evaluations_vs_N.{png,pdf,svg}` |
| fig08 accepted blocks vs N | `figures/fig08_accepted_blocks_vs_N.{png,pdf,svg}` |
| fig09 median block interval vs N | `figures/fig09_median_block_interval_vs_N.{png,pdf,svg}` |
| fig10 block retention vs N | `figures/fig10_block_retention_vs_N.{png,pdf,svg}` |
| fig11 low power fraction vs N | `figures/fig11_low_power_fraction_vs_N.{png,pdf,svg}` |
| fig12 energy per block vs N | `figures/fig12_energy_per_block_vs_N.{png,pdf,svg}` |
| fig13 energy vs retention tradeoff | `figures/fig13_energy_vs_retention_tradeoff.{png,pdf,svg}` |
| figD1 block interval distributions | `figures/figD1_block_interval_distributions.{png,pdf,svg}` |
| figD2 paired energy differences | `figures/figD2_paired_energy_differences.{png,pdf,svg}` |
| figD3 exhaustion rate | `figures/figD3_exhaustion_rate.{png,pdf,svg}` |
| figD4 epoch allocation sensitivity | `figures/figD4_epoch_allocation_sensitivity.{png,pdf,svg}` |

## 17. Limitations

See `STAGE_8X_LIMITATIONS.md` for the full statement. The required limitations are reproduced there verbatim.

## 18. Conservative interpretation

Under the fixed per-miner S21-Pro-equivalent model with matched difficulty, PoCol reduced active-power residency by 0.2388% relative to the paired PoW control, producing a mean paired energy reduction of 0.2308% at alpha = 0 and 0.1731% at alpha = 0.25, while retaining 99.58% of accepted-block production.

The mechanism is fully explained by low-power residency: miners spent F_low = 2.308e-03 of their miner-time in the low-power state, and the observed energy saving equals F_low x (1 - alpha) to within numerical precision. There was **no** duplicate-work reduction to contribute, because traditional PoW with distinct per-miner templates already performs zero exact-input duplicate work. Duplicate-work elimination and electrical-energy reduction are therefore distinct quantities: here the duplicate-work reduction is exactly zero, while the reduction in *total* physical evaluations (0.2388%) tracks the energy reduction at alpha = 0 exactly, both being consequences of the same idle miner-time and neither being a consequence of the other.

Energy savings decreased as the assumed low-power draw increased (0.2308% at alpha = 0 down to 0.1154% at alpha = 0.50), demonstrating that the magnitude of PoCol's electrical benefit depends materially on realizable hardware power-state behaviour. Because no S21 Pro low-power mode is vendor-specified, even the LP0 figure should be read as an idealized upper bound on this mechanism, not as an achievable device capability.

Against the declared secondary common-template comparator the picture is different in kind: there, disjoint allocation removes a large, measurable fraction of wasted evaluations, and the corresponding block-production penalty of the duplicating comparator is substantial. That result supports disjoint allocation as a defence against *coordinated-template redundancy*, not as a general energy reduction versus independent competitive mining.

Stage 8X does **not** demonstrate that PoCol reduces the energy consumption of a real Bitcoin network, does not validate any behaviour on physical S21 Pro hardware, and does not support a claim of superiority on energy grounds.
