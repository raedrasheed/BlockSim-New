# STAGE 8X — EXECUTION REPORT

Generated: 2026-08-14T17:08:02Z
Config hash: `b871c98ea1c612cdbd5a2223ff017610d908ae78fe08d509113f86983218cebf`
Commit at execution: `2d3c243b36e904ca04bf391b0a4adc73c8cbe273`

## 1. Executed matrix

| Phase | Physical runs | File |
|---|---|---|
| Pilot (excluded from inference) | 45 | `outputs/stage8x_pilot_runs.csv` |
| **Primary** | **300** | `outputs/stage8x_physical_runs.csv` |
| Declared secondary diagnostics | 420 | `outputs/stage8x_secondary_runs.csv` |

Derived PoCol energy sensitivity observations: **600** (= 150 PoCol physical runs x 4 alpha cases). These are accounting rows re-priced from recorded state residencies, **not** independent simulations.

## 2. Completeness audit

| Check | Result | Detail |
|---|---|---|
| expected primary physical runs == 300 | PASS | 300 |
| recorded primary physical runs == 300 | PASS | 300 |
| no duplicate run_id | PASS | 300 unique |
| no missing runs | PASS | 0 missing |
| no unexpected runs | PASS | 0 extra |
| 150 PoW physical runs | PASS | 150 |
| 150 PoCol physical runs | PASS | 150 |
| all five N values complete | PASS | [np.int64(100), np.int64(200), np.int64(300), np.int64(400), np.int64(500)] |
| 30 paired seeds at every (N, protocol) | PASS | {(100, 'POCOL'): 30, (100, 'POW'): 30, (200, 'POCOL'): 30, (200, 'POW'): 30, (300, 'POCOL'): 30, (300, 'POW'): 30, (400, 'POCOL'): 30, (400, 'POW'): 30, (500, 'POCOL'): 30, (500, 'POW'): 30} |
| every paired seed complete on both protocols | PASS |  |
| no zero-block runs discarded | PASS | 0 zero-block runs retained |
| state-time conservation < 1e-6 s | PASS | max 1.819e-12 s |
| work identity W = h*t_active (rel err < 1e-9) | PASS | max 1.460e-15 |
| duplicate identity W_total = W_unique + W_dup | PASS |  |
| PoCol exact duplicates == 0 | PASS |  |
| no simulator-artifact domain exhaustion | PASS |  |
| PoW never enters LOW_POWER | PASS |  |
| PoW and PoCol share difficulty at every N | PASS |  |
| single config hash across all runs | PASS | ['b871c98ea1c612cdbd5a2223ff017610d908ae78fe08d509113f86983218cebf'] |
| 600 PoCol alpha energy observations | PASS | 600 |
| 4 alpha cases per PoCol physical run | PASS |  |
| secondary runs recorded separately | PASS | 420 of 420 |

**Overall: PASS**

## 3. Runtime

* total primary simulation time: 13.8 s
* slowest single run: 0.101 s
* mean run: 0.046 s

## 4. Integrity notes

* Runs are resumable by `run_id`; a resumed execution skips completed runs and never duplicates one. Progress and failure logs are under `outputs/`.
* No run was discarded. Zero-block runs, had any occurred, would be retained.
* No seed was selectively re-run. The whole matrix was executed under one frozen configuration hash.
* Pre-existing artifacts were checksummed before and after execution; see `STAGE_8X_VALIDATION_REPORT.md`.
