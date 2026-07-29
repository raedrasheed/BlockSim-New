# Stage 5B1 — Parallel-Execution Reproducibility

Stage 5B2 will execute ~1 890 runs, likely in parallel. This document establishes
that parallel execution cannot change any scientific result.

## 1. Determinism by construction

- **Pure function.** `run_scenario(cfg)` reads only its `EngineConfig` and derived
  named-stream RNGs; it holds no global state and does not touch
  `InputsConfig` (validated: `test_isolated_output_directories`).
- **Named streams.** Every RNG is seeded as
  `int(sha256("{master_seed}:{stream_name}"))` (`derive_stream_seeds`). Streams are
  mutually independent; consuming one does not perturb another
  (`test_stream_independence`, check `F2`).
- **No wall-clock / no `Math.random`.** Nothing in the engine reads system time or
  a global RNG.

## 2. Direct test: 20 sequential vs 20 concurrent

Category F runs 20 configs (cycling B0/B1/B2/B3_C1/C2, distinct seeds) **twice**:
once sequentially, once through an 8-worker `ThreadPoolExecutor` over the *same*
config objects, interleaved with unrelated runs.

Outcome key compared per run: `(total_energy_kwh, accepted_blocks,
total_active_time_s, total_idle_time_s, duplicate_evaluation_rate)`.

**Result:** `F1` — 0 mismatches across all 20 pairs; sequential and concurrent
outcomes are bit-for-bit identical.

## 3. Output-isolation safety for Stage 5B2

- Each run writes to a **unique** path keyed by `run_id`
  (`results/.../stage_05b2/raw/{run_id}.summary.json`).
- Writes are **atomic** (`run_utils.atomic_write_json`: temp file + `fsync` +
  `os.replace`), so a crashed or racing worker never leaves a partial file that
  reads as complete (`test_atomic_manifest_write`, `test_partial_run_not_marked_complete`).
- Completion is gated on `status == COMPLETED`; partial writes are never observed
  as done.

## 4. Consequence

Stage 5B2 may parallelise freely (process- or thread-level) with no effect on
results and no risk of corrupt/duplicate output. Reproducing a single run only
requires its `run_id` → config row in `STAGE_05B1_FINAL_MATRIX.csv` and the frozen
seed schedule (SHA-256 `6122dbd0…b13e10`).
