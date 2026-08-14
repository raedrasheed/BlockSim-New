# STAGE 8X — FREEZE REPORT

Frozen at: 2026-08-14T17:07:50Z
Revision: 1
Git commit: `2d3c243b36e904ca04bf391b0a4adc73c8cbe273`
Git branch: `claude/stage-8x-pocol-energy-osz8ot`
Config hash: `b871c98ea1c612cdbd5a2223ff017610d908ae78fe08d509113f86983218cebf`
Seed registry SHA-256: `f1a8fbf884f2a38860670aacddf7b8c7acf5c5edd5a90fd59e51272f4a535041`

The Pilot passed (see `STAGE_8X_PILOT_REPORT.md`) and the validation suite
passed (see `STAGE_8X_VALIDATION_REPORT.md`). Code, configuration, seed
registry and analysis scripts are frozen as of this document.

## 1. Frozen hardware model

| Quantity | Value |
|---|---|
| ASIC | Bitmain Antminer S21 Pro |
| Per-miner hash rate | 234.0 TH/s |
| Per-miner active power | 3510.0 W |
| Efficiency | 15.0 J/TH |

*Active values are the official Bitmain Antminer S21 Pro nominal specification. Low-power values are experimental sensitivity assumptions, not vendor-certified modes.*

Low-power sensitivity cases (**none is a Bitmain-certified mode**):

| Case | alpha | P_low per miner |
|---|---|---|
| LP0 | 0.00 | 0.0 W |
| LP10 | 0.10 | 351.0 W |
| LP25 | 0.25 | 877.5 W |
| LP50 | 0.50 | 1755.0 W |

## 2. Frozen experiment parameters

| Parameter | Value |
|---|---|
| Network sizes N | [100, 200, 300, 400, 500] |
| Horizon T | 10000.0 s |
| Target block interval | 600.0 s |
| Epoch sweep tau | 600.0 s |
| Propagation delay | Exp(mean 0.42 s) |
| Primary seeds | 30 |
| Primary protocols | ['POW', 'POCOL'] |
| Difficulty rule | `D_N = H_N * I_target / 2**32 ; q_N = 1/(H_N*I_target)` |
| Nonce-domain rule | `S_N = H_N * tau_epoch ; L = S_N / N = h * tau_epoch` |
| Matched difficulty | D^PoW_N == D^PoCol_N (single D_N per N) |

## 3. Frozen difficulty and nonce domain by N

| N | H_N (H/s) | D_N | target | q per candidate | S_N (candidates) | L per miner | P(epoch exhaustion) |
|---|---|---|---|---|---|---|---|
| 100 | 2.3400e+16 | 3.268942e+09 | `0x0000000000000001...` | 7.122507e-20 | 1.4040e+19 | 1.4040e+17 | 0.36788 |
| 200 | 4.6800e+16 | 6.537884e+09 | `0x0000000000000000...` | 3.561254e-20 | 2.8080e+19 | 1.4040e+17 | 0.36788 |
| 300 | 7.0200e+16 | 9.806827e+09 | `0x0000000000000000...` | 2.374169e-20 | 4.2120e+19 | 1.4040e+17 | 0.36788 |
| 400 | 9.3600e+16 | 1.307577e+10 | `0x0000000000000000...` | 1.780627e-20 | 5.6160e+19 | 1.4040e+17 | 0.36788 |
| 500 | 1.1700e+17 | 1.634471e+10 | `0x0000000000000000...` | 1.424501e-20 | 7.0200e+19 | 1.4040e+17 | 0.36788 |

## 4. Frozen seed registry

Namespace: `BlockSim-New/Stage8X/PoCol-vs-PoW/AntminerS21Pro/rev1`

Primary master seeds (30):

```
  5276648305985929199, 628757264142989241, 5212820311653467928
  1493634387465783589, 349906842534328690, 2558760955731327512
  7890926658382884983, 3687042657521687600, 5165136745342788261
  3156971904625785319, 8079052055583561862, 1478038051582526088
  431967532912089508, 3282352798337906545, 3447193969005866655
  3787989265829909659, 2197885266553486539, 2431420697959460063
  3695536046059844503, 8644301345824299180, 6968863412458885356
  1228799680501299399, 1913678187707743529, 4932121285862289456
  1808207741461098536, 5227458720195675600, 5875244136080589253
  4508414229999547955, 5719031026733889488, 1452385983224652643
```

Pilot master seeds (5), disjoint from the above:

```
  9214983839595262035, 6173363108739508102, 5143865312279076214, 1979658706891550875, 5064053482760469401
```

## 5. Frozen run matrix

| Phase | Physical runs |
|---|---|
| Primary (5 N x 2 protocols x 30 seeds) | **300** |
| Pilot (excluded from inference) | 45 |
| Declared secondary diagnostics | 420 |

PoCol energy sensitivity observations: **600** (150 PoCol physical runs x 4 alpha cases). These are *derived accounting rows*, not independent physical simulations.

## 6. Frozen code checksums (SHA-256)

| File | SHA-256 |
|---|---|
| `experiments/stage8x/config/asic.py` | `588fa9953d0d87ed8538d1ae68b76e6177bb90ae5569115c5c603ccd0bf2b812` |
| `experiments/stage8x/config/difficulty.py` | `ed97fa46c89d62f85e216a32fb661b197812eb992b03a01992c4bf69e6be0d44` |
| `experiments/stage8x/config/seeds.py` | `643330ce75ecb68de50c16ef25eb2f10d0b87f6a4c312ad18ea1580198fed1fb` |
| `experiments/stage8x/config/stage8x_config.py` | `9cc52a1c45820f00779ad6404963593cdcb81d9af0ac19d3289f0455767787fc` |
| `experiments/stage8x/simulator/hashing.py` | `c756dd675f0315708e20cce800c3fc4d8a8db816e005fef967785f6f43d4a16e` |
| `experiments/stage8x/simulator/powerstate.py` | `7afc6fe6226f24e7793f4e1a80e29e87ffb16c56d312d085ecfdccfca5951495` |
| `experiments/stage8x/simulator/energy.py` | `372e1ec0052fc8f6a0bd15487cbcd1b7e0d64ea14dbcf78ff4c39279ce9321de` |
| `experiments/stage8x/simulator/engine.py` | `07ef462ca18824164666e508cf292fdf3db9a9ab78acce26b2bd2cc78c8a0580` |
| `experiments/stage8x/analysis/stats.py` | `979e5c2710593408071179330b10af839935d26e8e95b1d7e7a033500fff46fe` |
| `experiments/stage8x/analysis/tables.py` | `2b09b029c053b7efee54edbb2f3b0070623bb2632ee2aa17d5e2e1e2fc59cd48` |
| `experiments/stage8x/analysis/figures.py` | `0df33813c2c4a4545cc2fceb755f938d1bee1f938ce211c6894e87564b0e4b6b` |
| `experiments/stage8x/tests/test_stage8x.py` | `72adace7daddc21eb3d9d36f6030a5b08a1a3dddcf837d2e0b0851a78588cac9` |
| `experiments/stage8x/run.py` | `62d4167e21277162cf5151f2bbab0d1f2187825507b1c1a62aa079db7828e963` |
| `experiments/stage8x/validate.py` | `ab7a4ed0822842d39a43985ff17ba53ff340bf453b5773504bc4aed638933c02` |
| `experiments/stage8x/freeze.py` | `7c0cca42f839943fd5c34ea9ac54a50af754cc0fb574af5ddec0d26465a6d4ca` |
| `experiments/stage8x/analyze.py` | `84cdc7e3bcb28ae6191516acbf4560bd6aeb385aacf24e8b96fa1c985652a3c6` |

## 7. Environment

| Item | Value |
|---|---|
| Python | 3.11.15 (CPython) |
| Platform | Linux-6.18.5-fc-v20-x86_64-with-glibc2.39 |
| Machine | x86_64 |
| numpy | 2.4.6 |
| pandas | 3.0.5 |
| scipy | 1.17.1 |
| matplotlib | 3.11.1 |

## 8. Post-freeze rule

No scientific parameter may change after primary results are observed. A critical defect requires: stop, document, fix, increment REVISION, re-run ALL affected primary runs. Selective re-running of unfavourable seeds is prohibited.

## 9. Post-freeze amendments

### A1 (2026-08-14) - `experiments/stage8x/analysis/tables.py`

* **Defect:** Table H's reference column `theoretical_duplicate_ratio` used 1-(1-1/N)^N, which is the expected *coverage* fraction, not the expected duplicate ratio.
* **Fix:** Corrected to (1-1/N)^N -> e^-1 = 0.3679, the expected duplicate ratio for N miners scanning L candidates at independent uniform offsets in a shared domain S = N*L.
* **Scope:** Display-only reference column in a declared SECONDARY diagnostic table. No physical run, no primary result, no frozen parameter and no config_hash is affected; no run was re-executed.

### A2 (2026-08-14) - `experiments/stage8x/config/asic.py`

* **Defect:** ALPHA_LABELS repeated the phrase 'sensitivity assumption', which the report template already prefixes, producing 'experimental sensitivity assumption - sensitivity assumption, 10% of active power'.
* **Fix:** Trimmed the redundant prefix from the LP10/LP25/LP50 label strings.
* **Scope:** Human-readable label strings only. No numeric value, no alpha, no frozen parameter and no config_hash is affected (config_hash covers ALPHA_CASES values, not ALPHA_LABELS text); no run was re-executed.

### A3 (2026-08-14) - `experiments/stage8x/analyze.py`

* **Defect:** The interpretation paragraph said 'the reduction in physical evaluations ... is zero', conflating the (zero) duplicate-work reduction with the (non-zero, 0.24%) reduction in total physical evaluations.
* **Fix:** Reworded to state both quantities explicitly and to report the measured total-evaluation reduction alongside the energy reduction.
* **Scope:** Report prose only. No data, no frozen parameter, no config_hash; no run was re-executed.

