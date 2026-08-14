# STAGE 8Y — EXECUTION REPORT

Generated: 2026-08-14T18:29:37Z
Config hash: `2d7344a1dac41b6a3484536e18939f294bff62d32a67310254f9a41fc7dfb0d0`
Commit at execution: `ec89b3bbf840c2e27c5e270e21ea6ed29c1155c3`

## 1. Executed matrix

| Phase | Classification | Physical runs | α observations |
|---|---|---|---|
| Pilot | excluded from all inference | 378 | 0 |
| Primary | **confirmatory** | 1080 | 4050 |
| Secondary | exploratory / sensitivity | 2880 | 9000 |
| Long horizon | confirmatory (T=100 000 s) | 360 | 1350 |

α observations are **derived accounting rows** re-priced from recorded state residencies, not independent physical simulations.

## 2. Completeness audit

| Check | Result | Detail |
|---|---|---|
| primary matrix size == 1080 | PASS | 1080 |
| primary runs recorded == 1080 | PASS | 1080 |
| no duplicate primary run_id | PASS | 1080 |
| no missing primary runs | PASS | 0 |
| no unexpected primary runs | PASS | 0 |
| 270 runs for POW | PASS | 270 |
| 270 runs for P0_ALL | PASS | 270 |
| 270 runs for P3_ENERGY | PASS | 270 |
| 270 runs for P4_RESERVE | PASS | 270 |
| all primary compositions complete | PASS |  |
| all primary N complete | PASS |  |
| 30 seeds at every cell | PASS |  |
| state-time conservation < 1e-6 s | PASS | 3.638e-12 |
| no negative residence | PASS |  |
| work identity < 1e-9 | PASS | 7.625e-15 |
| duplicate identity holds | PASS |  |
| PoCol exact duplicates == 0 | PASS |  |
| PoW exact duplicates == 0 | PASS |  |
| PoW never parked | PASS |  |
| one difficulty per (composition, N) | PASS |  |
| single config hash | PASS | ['2d7344a1dac41b6a3484536e18939f294bff62d32a67310254f9a41fc7dfb0d0'] |
| no zero-block runs discarded | PASS | 0 retained |
| primary alpha observations == 4050 | PASS | 4050 |
| 5 alpha cases per PoCol run | PASS |  |
| secondary runs recorded | PASS | 2880 of 2880 |
| long-horizon runs recorded | PASS | 360 of 360 |
| pilot kept separate from primary | PASS |  |

**Overall: PASS**

## 3. Runtime

* primary simulation time: 49.1 s
* slowest single run: 0.130 s
* long-horizon simulation time: 162.7 s

## 4. Integrity

* Runs are resumable by `run_id`; completed runs are skipped, never duplicated.
* No run was discarded and no seed was selectively re-run.
* Zero-block runs would be retained; none occurred.
* Pilot, primary, secondary and long-horizon datasets use disjoint seed groups and disjoint run-ID prefixes and are never pooled.

