# STAGE 04 — Proposed Stage-5 Experiment Matrix (DESIGN ONLY — not executed)

Designed, not run. No matrix executes until explicitly approved (decisions in
`STAGE_04_DECISIONS_REQUIRED.md`).

Base configuration: fixed `H_total = 141 TH/s`, `21.5 J/TH`, target interval
`600 s`, duration `10 000 s`, exact Binomial sampler, homogeneous miners,
`μ = 2` domain, baseline propagation delay `0.42 s`, idle power `0 %` (lower
bound), coordination energy excluded.

---

## 1. Core confirmatory matrix

| dimension | levels |
|---|---|
| scenarios | B0, B1, B2, B3, C1, C2 (6) |
| miner counts | 100, 200, 300, 400, 500 (5) |
| seeds | ≥ 30 (deterministic) |

**Runs: 6 × 5 × 30 = 900.**

## 2. Sensitivity matrix (one variable at a time around base; C1 & C2; N ∈ {100, 500})

| dimension | levels | scenarios × counts × seeds | runs |
|---|---|---|---|
| idle-power ratio (C2) | 0, 5, 10, 20, 30 % | 1 × 2 × 30 × 5 | 300 |
| propagation delay | 0, 0.42, 1, 5, 30, 60 s | 2 × 2 × 30 × 6 | 720 |
| inactive-miner fraction | 0, 5, 15, 30 % | 2 × 2 × 30 × 4 | 480 |
| hash-rate dist × allocation | {homog, heterog} × {equal, weighted} | 2×2 × 2 × 2 × 30 | 480 |
| μ (domain size) | 0.5, 1, 2 | 2 × 2 × 30 × 3 | 360 |

**Sensitivity runs ≈ 2 340.** (0 % idle / baseline delay / homogeneous overlap
the core; net new ≈ 2 200.)

## 3. Exploratory matrix (optional; only if approved)

Churn (join/leave), alternative topology, transaction-arrival rate, template-
synchronization duration — proposed ≈ 300 runs, decision-gated.

## Totals and budget

| quantity | estimate |
|---|---|
| total runs (core + sensitivity) | **≈ 3 240** (≈ 3 540 with exploratory) |
| per-run wall time | ≈ 1.5 s (PoW) – 3 s (PoCol N=500) |
| single-thread CPU time | ≈ 2.5 CPU-hours |
| parallel wall time (~14 workers) | ≈ 10–15 min |
| **storage — full workbooks (rejected)** | ~3.2 GB (too large for the environment) |
| **storage — proposed** | one **summary row per run** (single CSV) + small `diag.json` per run ≈ **10–20 MB**; full EnergyLog kept only for a validation subset (~20 runs) |
| expected summary rows | ≈ 3 240 (one per run) |

## Parallelization & failure policy

- **Parallelization:** independent per-run subprocesses on a copy of the source
  (as in Stages 1–3), pooled at `min(16, cores−2)`; each run writes a summary
  row + diag.json; a final reducer concatenates summaries.
- **Immutability:** raw summaries + diags are `chmod 0444`; a manifest records
  config hash, seed, git commit, checksum, timestamps.
- **Failure/retry:** a run that errors or exceeds a documented per-run cap
  (240 s) is retried once with the same seed; a second failure is logged as
  `FAILED` (not silently dropped) and excluded from statistics with the reason
  recorded. No manual editing of raw data.

## Anti-combinatorial-explosion note

The full cross-product (6 scenarios × 5 counts × 6 delays × 5 idle × 4 inactive
× 4 dist/alloc × 3 μ × 30 seeds ≈ 1.3 M runs) is **deliberately avoided**. The
design is core (full cross of scenario × count) + one-variable-at-a-time
sensitivity around a documented base, which is sufficient for the causal ablation
(A1–A10) at ~0.25 % of the full-cross cost.
