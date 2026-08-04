# Stage 7M — Minimal Frozen Execution Report

**Branch:** `thesis-v45-pocol-stage7m-minimal-execution` (from the Stage-6M freeze commit
`381bcab`).
**Status:** `STAGE_7M_EXECUTION_COMPLETE` — all 32 preregistered runs executed, checkpointed
atomically, checksum-verified, and assembled into the frozen datasets.

This report records **feasibility and integrity only**. No mean, interval, p-value or any
other cross-run effect summary is computed or stated here: the first aggregation of the
energy outcomes happens in Stage 8M, on the frozen 30-row dataset, exactly as preregistered.

---

## 1. Resource preflight (dry run) — PASSED

One dry-run preflight (`run_stage7m.py preflight`) ran before execution. Every executed
preflight seed is an **unassigned PILOT seed** (core class timed on structural-pilot index 0;
X01/X02 classes timed on free pilot indexes 4 and 5) — no confirmatory seed and no assigned
exploratory seed was executed, and no energy quantity was recorded.

| gate | value | verdict |
|---|---|---|
| exactly 32 planned runs | 32 | PASS |
| all 32 run identifiers unique | 32 | PASS |
| zero pre-existing output | none | PASS |
| free disk ≥ 2 GB | 11.34 GB | PASS |
| projected total wall ≤ 4 h (sequential-equivalent × 1.5 safety) | 111.1 s | PASS |
| projected peak RSS ≤ 8 GB at 2 workers (× 1.25 safety) | 0.332 GB | PASS |

Timing samples: CORE (M03, the most expensive core class) 1.41 s / 40.8 MB / 193 rounds;
X01 7.25 s / 101.1 MB / 289 rounds; X02 24.46 s / 136.1 MB / 274 rounds.
Full record: `STAGE_07M_PREFLIGHT_RECORD.json`.

---

## 2. Execution — 32/32 COMPLETED, every integrity gate PASS

`run_stage7m.py execute` ran the 30 confirmatory runs (M01/M02/M03 × confirmatory seed
indexes 0–9) and the 2 exploratory scale checks (X01 pilot[2], X02 pilot[3]) with **2
concurrent workers**, one process per run (`maxtasksperchild=1`) so peak RSS is attributed
per run. Every run checkpointed **atomically** (tmp file + `os.replace`) immediately on
completion; the runner is resumable and skips existing checkpoints.

* Total execution wall: **≈ 47 s** (45.3 s first pass + 1.8 s for one infrastructure
  re-run, §4). Worst single run: X02 at 25.05 s / 150.9 MB RSS.
* All 32 runs `COMPLETED`; **all preregistered deterministic integrity gates pass on every
  run** (energy-identity residual ≤ 1e-8 J; residency-partition residual ≤ 1e-9 s;
  duplicate nonces, post-round evaluation records/nonces, missing terminal times, frontier
  rewinds, work/reward residual, nonterminal leases, nonterminal reassignment requests,
  adversarial action total, nonterminal activation requests all exactly 0; residency
  reconciles; round terminal times strictly increasing; and, with zero offline residency,
  |E_power_null − A1| ≤ 1e-9 kWh).

Compact run-level checkpoints (one JSON per run, all preregistered outcomes + integrity
counts + round-duration summary + residuals + run identity, seed, config SHA-256, engine
SHA-256, wall time, peak RSS, record checksum, status):
`experiments/thesis_revision_v45/stage_07m/runs/*.json` (32 files).
Full ownership/entity/event ledgers were **not** serialised per run, exactly as directed.

## 3. Audit ledgers — exactly the two preregistered runs

Full detailed ledgers (results schema, complete nonce-evaluation ledger, round terminal
times, per-miner residency, activation requests, event log), gzip-compressed, exist for
exactly the two preregistered audit runs and for no others:

| audit run | file | compressed |
|---|---|---:|
| M01_HET_IDLE, seed index 0 | `…/audit/7m-M01_HET_IDLE-s00_full_ledger.json.gz` | 120 KB |
| M03_HET_IDLE_FLOOR, seed index 0 | `…/audit/7m-M03_HET_IDLE_FLOOR-s00_full_ledger.json.gz` | 146 KB |

Each run record stores the audit file's SHA-256; `verify` re-hashes both files.

## 4. One infrastructure re-run (declared)

The first pass of `7m-M03_HET_IDLE_FLOOR-s00` completed its **simulation** but raised
`RecursionError` inside the harness's audit-ledger serialiser: activation-request objects
hold back-references to shared registries, and the naive JSON projection recursed on the
cycle (M01's audit ledger has no activation requests, so it did not trip). The fix is
confined to the harness (`to_jsonable` now detects descent-path cycles); **no simulation or
engine code changed**. The failed checkpoint was deleted and the run re-executed under the
identical frozen seed and config — the engine is deterministic, so this is an
infrastructure re-run, not a scientific re-run. Only the stored exception text of the
failed attempt was inspected before deletion; no outcome value of the failed attempt was
read.

## 5. Checksum verification and datasets

`run_stage7m.py verify` → `OK: all 32 checkpoints verified` (record SHA-256 recomputed for
every checkpoint; audit-ledger digests re-hashed; exactly 2 audit runs).

`run_stage7m.py dataset` (which re-verifies first) wrote the frozen tables:

* `STAGE_07M_CONFIRMATORY_DATASET.csv` — **30 rows** (M01/M02/M03 × seed indexes 0–9),
  43 columns: identity, status, the 26 preregistered outcomes, gate verdicts, wall/RSS,
  config/engine/record SHA-256.
* `STAGE_07M_EXPLORATORY_SCALE_TABLE.csv` — **2 rows** (X01, X02), same columns, role
  `EXPLORATORY_SCALE_CHECK`, hypotheses `NONE`. These rows are descriptive sanity checks
  and may never enter any permutation test, bootstrap interval or confirmatory statement.

## 6. Accepted test suite re-run

After execution, the full accepted suite ran locally on this branch:
`python3 -m pytest tests/thesis_revision_v45/stage2/ -q` → **195 passed** (recorded in the
freeze-commit message). The Stage-6M validation suite also remains green (9 passed). No CI
was created or waited for.

## 7. Standing state

```
STAGE_7M_EXECUTION_COMPLETE
STAGE_8M_ANALYSIS_NOT_YET_STARTED
```

Stage 8M (branch `thesis-v45-pocol-stage8m-minimal-analysis`) must use only the frozen
30-row confirmatory dataset above and the preregistered analysis plan
(`docs/thesis_revision_v45/stage_06m/STAGE_06M_ANALYSIS_PLAN.md`).
