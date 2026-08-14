# STAGE 8Y — FREEZE REPORT

Frozen at: 2026-08-14T18:21:30Z
Revision: 1
Git commit: `ec89b3bbf840c2e27c5e270e21ea6ed29c1155c3`
Git branch: `claude/stage-8x-pocol-energy-osz8ot`
Working tree clean: False
Config hash: `2d7344a1dac41b6a3484536e18939f294bff62d32a67310254f9a41fc7dfb0d0`
Seed registry SHA-256: `6726dfc98a8f80226ad3b6d5a1d1aff0042f19cb04d7d25bc5451ca72ccf7542`

Dirty paths at freeze time:

```
?? experiments/stage8y/
```

The Pilot passed (`STAGE_8Y_PILOT_REPORT.md`) and the validation suite passed (`STAGE_8Y_VALIDATION_REPORT.md`). Everything below is frozen.

## 1. Hardware registry

| Key | Model | h (TH/s) | P (W) | η derived (J/TH) | certification |
|---|---|---|---|---|---|
| S21PRO | Antminer S21 Pro | 234.0 | 3510.0 | 15.000 | url_located_content_not_retrievable |
| S19XP | Antminer S19 XP | 141.0 | 3010.0 | 21.348 | url_located_content_not_retrievable |
| S19JPRO | Antminer S19j Pro 104T | 104.0 | 3068.0 | 29.500 | verified_quote |

No device-specific low-power figure is published by the manufacturer, so none is used. All parked power is `P_low = α·P_active`.

## 2. Hardware compositions

| ID | Mix | Rationale |
|---|---|---|
| H0 | 100% S21PRO | Homogeneous control: 100% S21 Pro. Reproduces the Stage 8X hardware model so that any Stage 8Y effect attributable to heterogeneity can be separated from effects present without it. |
| H1 | 75% S21PRO, 25% S19JPRO | Low heterogeneity: 75/25 newest/older. A network that has largely, but not completely, refreshed to the current generation. |
| H2 | 50% S21PRO, 50% S19JPRO | Medium heterogeneity: 50/50. The balanced two-generation reference case. |
| H3 | 25% S21PRO, 75% S19JPRO | High heterogeneity: 25/75. A network dominated by older, less efficient capacity, with a high-efficiency minority. |
| H4 | 20% S21PRO, 30% S19XP, 50% S19JPRO | Multi-generation realistic skew: 20% S21 Pro, 30% S19 XP, 50% S19j Pro. Three generations with the newest as a minority, reflecting the fact that hardware turnover is gradual and older units keep running while they remain marginally profitable. It spans the full efficiency range available in the registry (15.0 to 29.5 J/TH) with an intermediate class in between. The shares were fixed on this turnover argument BEFORE any Stage 8Y run was executed and were not adjusted toward or away from any energy threshold. |

## 3. Frozen scientific parameters

| Parameter | Value |
|---|---|
| Primary N | [100, 300, 500] |
| Secondary N | [200, 400] |
| Primary compositions | ['H0', 'H2', 'H4'] |
| Primary protocols | ['POW', 'P0_ALL', 'P3_ENERGY', 'P4_RESERVE'] |
| Horizon | 10000.0 s (long: 100000.0 s) |
| Target interval | 600.0 s |
| Epoch sweep τ | 600.0 s |
| Propagation | Exp(mean 0.42 s) |
| Difficulty rule | D = H_N * I_target / 2**32 from FULL installed hardware; one D per (N, composition), handed unchanged to PoW and every PoCol policy; never recalibrated for PoCol. |
| Nonce-domain rule | S = H_N * tau_epoch from FULL installed capacity; one disjoint slot per installed miner; parking a miner leaves its slot unscanned and does not shrink S. |
| Domain semantics | installed |
| Confirmatory selection | S4_OPTIMIZE |
| Confirmatory r_H (P3) | 0.6 |
| Confirmatory schedule (P4) | [0.6, 0.75, 0.9, 1.0] |
| Confirmatory trigger | 300.0 s |
| Confirmatory wake delay | 10.0 s |
| Wake power ratio | 1.0 (Wake transitions draw full active power. This is the conservative choice and is unfavourable to PoCol; no manufacturer wake-power curve exists.) |
| α cases | {'alpha_0': 0.0, 'alpha_005': 0.05, 'alpha_010': 0.1, 'alpha_025': 0.25, 'alpha_050': 0.5} |
| Seeds | 30 primary |

*These values are model-based sensitivity assumptions and are not manufacturer-certified Antminer low-power operating modes. alpha = 0 is an idealized theoretical lower bound, not a physically validated state.*

## 4. Difficulty and nonce domain (primary cells)

| comp | N | H_N (H/s) | P_N (W) | η_net | D | q | S |
|---|---|---|---|---|---|---|---|
| H0 | 100 | 2.3400e+16 | 351000 | 15.000 | 3.268942e+09 | 7.122507e-20 | 1.4040e+19 |
| H0 | 300 | 7.0200e+16 | 1053000 | 15.000 | 9.806827e+09 | 2.374169e-20 | 4.2120e+19 |
| H0 | 500 | 1.1700e+17 | 1755000 | 15.000 | 1.634471e+10 | 1.424501e-20 | 7.0200e+19 |
| H2 | 100 | 1.6900e+16 | 328900 | 19.462 | 2.360903e+09 | 9.861933e-20 | 1.0140e+19 |
| H2 | 300 | 5.0700e+16 | 986700 | 19.462 | 7.082708e+09 | 3.287311e-20 | 3.0420e+19 |
| H2 | 500 | 8.4500e+16 | 1644500 | 19.462 | 1.180451e+10 | 1.972387e-20 | 5.0700e+19 |
| H4 | 100 | 1.4110e+16 | 313900 | 22.247 | 1.971144e+09 | 1.181195e-19 | 8.4660e+18 |
| H4 | 300 | 4.2330e+16 | 941700 | 22.247 | 5.913433e+09 | 3.937318e-20 | 2.5398e+19 |
| H4 | 500 | 7.0550e+16 | 1569500 | 22.247 | 9.855721e+09 | 2.362391e-20 | 4.2330e+19 |

## 5. Seed registry

Namespace: `BlockSim-New/Stage8Y/HeterogeneousEnergyAwarePoCol/rev1`

**pilot** (6 seeds):

```
  4090561990393436418, 6838684854956031349, 6329054989252639623
  8163042629132292708, 4852802856419981608, 1121034527795832081
```

**primary** (30 seeds):

```
  8130977030838769163, 4647866675757887467, 1989633920448304007
  4664050418518895039, 4312536253712814195, 1923384035995295764
  5970003501861214187, 3536223456970348905, 5755498848245515654
  7560162670533313979, 8174500689932262578, 4102370935243066338
  7445073405389867729, 3690131547872387883, 6927386137577913889
  2865763732212451759, 5555941558528184881, 6291690635984895342
  8678260928731344775, 3675193905331863324, 76408378121421718
  2105458320642740607, 1334784042938412638, 5493616296601861894
  4741983282246553004, 623555073379540022, 5872401816003698851
  9111692088497971717, 3258766509526299410, 8403036571643851313
```

**secondary** (30 seeds):

```
  8063686115461822543, 8334383792207353191, 6889695668962070368
  4087591021073051263, 6547292525179712211, 112793446144040634
  7662812207209883313, 7848051508590293418, 5913046009108803253
  6050333513346762126, 1545388458953111946, 6766663637513695711
  8035403522107751096, 3006782300171895878, 1713677149701154578
  7174273983104418752, 8264207956071345440, 8402483419494942885
  7582273092638728973, 1555328268468604092, 5555094656930633322
  1811211645397239193, 9180234268426441910, 4090175954229657827
  9111172304724268236, 7827457778916401294, 8242744616703041774
  5144033880547668264, 194090456105594422, 4839620536546032277
```

**longhorizon** (30 seeds):

```
  8954845426650740938, 477200057691319694, 1968042618328328173
  3632877765199869996, 6003832703350169553, 4549607262503327023
  8841621915921197854, 4447881767266756583, 3134041250368350729
  6178980511906558985, 6238549325645359936, 5562852976513239712
  707868699202258078, 6410566829429296708, 2077976382410379722
  1830988843354664416, 8936008837500200607, 5666594887584047244
  6210219425330187883, 1509113868345929592, 8922332654234879308
  8534181642547133905, 8124562099205701016, 4264918121932318869
  3839734850396128861, 874709438858448558, 7152334502628813485
  5650422624823212391, 2704408619800324465, 3741578835868721631
```

## 6. Run matrix

| Phase | Physical runs |
|---|---|
| pilot | 378 |
| primary | 1080 |
| secondary | 2880 |
| longhorizon | 360 |
| primary_alpha_observations | 4050 |

## 7. Statistical plan

| Element | Specification |
|---|---|
| pairing | seed-paired PoCol - PoW at matched (composition, N, seed) |
| tests | Shapiro-Wilk assumption check, then paired t-test or Wilcoxon signed-rank; magnitude, t-based CI and paired bootstrap CI, Cohen's d_z and rank-biserial reported alongside every p-value |
| multiplicity | Holm-Bonferroni within each metric family across confirmatory cells |
| threshold_assessment | bootstrap CI around EnergySaving vs 0.50 and around BlockRetention vs 0.90 / 0.95 |

## 8. Acceptance criteria

| Criterion | Definition |
|---|---|
| saving_threshold | 0.5 |
| retention_strong | 0.95 |
| retention_moderate | 0.9 |
| latency_ratio_max | 1.1 |
| outcome_A | Saving > 50% AND BlockRetention >= 95% AND LatencyRatio <= 1.10 under at least one confirmatory NON-IDEALIZED alpha (alpha > 0). |
| outcome_B | Saving > 50% AND BlockRetention >= 90% under at least one confirmatory configuration. |
| outcome_C | Saving > 50% but BlockRetention < 90%. |
| outcome_D | No confirmatory configuration achieves Saving > 50%. |
| outcome_E | Saving > 50% only under idealized assumptions (alpha = 0 or t_wake = 0) and not under conservative ones. |

## 9. Frozen code checksums

| File | SHA-256 |
|---|---|
| `experiments/stage8y/config/hardware_registry.json` | `5fd33ba0a41202a7bf03d6f4545d40c331381c0f4aa23cc2360d589e30c0cb7c` |
| `experiments/stage8y/config/hardware.py` | `c062c1761f9007bf4908839aa94efb0287483df63135b8ca4d30ee73a250430f` |
| `experiments/stage8y/config/difficulty.py` | `8a19d1e8e8684a49f24c104d36227563b19eaf48a9934fd694d2c495d82cd53a` |
| `experiments/stage8y/config/policies.py` | `3abff1050f884ca72ab3c1be1b7661b5ceef787b3bd54ac8660e445c4d9b5d0b` |
| `experiments/stage8y/config/seeds.py` | `e3ad607184e500e7741ba10a0678b448019fd225f75edd3e007da34440a43dfe` |
| `experiments/stage8y/config/stage8y_config.py` | `5120997cd571fcbc9ebb6074c60caf01ab519531c3e1ff8d7137140a2c18d864` |
| `experiments/stage8y/src/powerstate.py` | `7d40a52a48c4a6977b55eb6c2b337afda5beeb357ff32eb3f729d2709d126759` |
| `experiments/stage8y/src/energy.py` | `65893f9587988cd53114824cd0b25807b1379f7007e0fde17b3923256eab934d` |
| `experiments/stage8y/src/engine.py` | `510e954a75aa54de725e0d4d200d240466c5a7395354add58a982a630ad4adc0` |
| `experiments/stage8y/src/metrics.py` | `faa847628ccd24b2e19016c96048c35a4feb29b7a60da401752c1f50918cdb6f` |
| `experiments/stage8y/src/analysis_stats.py` | `65d69713b399be7216d5179184ed593de427d8dfb3087299ea399e116307b222` |
| `experiments/stage8y/src/analysis_tables.py` | `a50856f5ce5340a6c2bd6959683d11ae1d4d6732dc5a9bcf6b927f580d4f8510` |
| `experiments/stage8y/src/analysis_figures.py` | `1bbd922cf76ce02289ba4d61be54fe3dda79c744742cc7d60507c21881d68c98` |
| `experiments/stage8y/tests/test_stage8y.py` | `8a1fb0af02c50b858b3a8f612e5b650023dfa8f9f98b55e0f221fa0cb9a8fae5` |
| `experiments/stage8y/run.py` | `4a58b1e44969e9226dd6172443834c0257bc131d0bf2e3092179b770873ac6ef` |
| `experiments/stage8y/analyze.py` | `415633954f5f115c521f9ab67918ff077c798c92006edfec3ddb73bd48d60fff` |
| `experiments/stage8y/validate.py` | `77303249a68bb60eb62b94195b5e4c3380603d082347e71de8cf39c89e5dc272` |
| `experiments/stage8y/freeze.py` | `1c66549e335a8e7eb248ab82c3b1e82ac41e0fd30addced3ca79c6f94dbd6188` |
| `experiments/stage8y/baseline.py` | `3e1826170900ae2218d38c48800fcb6f26896181c202a623872a52c8c5604dab` |

## 10. Environment

| Item | Value |
|---|---|
| Python | 3.11.15 (CPython) |
| Platform | Linux-6.18.5-fc-v20-x86_64-with-glibc2.39 |
| Machine | x86_64 |
| numpy | 2.4.6 |
| pandas | 3.0.5 |
| scipy | 1.17.1 |
| matplotlib | 3.11.1 |

## 11. Post-freeze rule

No scientific parameter may change after the freeze. A change requires: rerun the Pilot from scratch, document the change, increment REVISION and refreeze. Serialization or implementation corrections are permitted only if scientifically neutral and fully documented. Selective re-running of unfavourable seeds is prohibited.

## 12. Post-freeze amendments

### A1 (2026-08-14) — `experiments/stage8y/config/stage8y_config.py::secondary_matrix`

* **Defect:** The SECONDARY matrix contained no traditional-PoW baseline at the secondary reference cell (H2, N=300), so every secondary sensitivity run there had no matched control and all of its paired rows were silently dropped from the secondary energy table.
* **Fix:** Added 30 matched POW runs at (H2, N=300) on the secondary seeds (tag 'base'). Existing secondary runs were untouched and were not re-executed; the 30 new control runs were appended.
* **Scope:** Adds a control to a declared SECONDARY/exploratory analysis. It changes no scientific parameter, no confirmatory run, no primary result, and config_hash is unchanged (frozen_parameters records the secondary grid values, not the enumerated run list). Detected by an empty secondary sensitivity table during analysis, before any secondary result was read.

