# Stage 8U — Figure Index (FIG01..FIG18)

All figures are generated programmatically from the frozen `STAGE_08U_RUN_DATASET.csv` and `stage8u_results.json`, and are deterministic (fixed SVG hashsalt, no timestamps): tables, captions and metadata regenerate byte-identically under `generate_8u.py --check` (U-TEST-22).  Each figure ships as SVG, 300-dpi PNG, source CSV, caption markdown, metadata JSON and a SHA-256 checksum file, all under `figures/`.

| figure | title | checksum file |
|---|---|---|
| FIG01 | Total energy per run, all five scenarios | `FIG01_total_energy.sha256` |
| FIG02 | Relative energy difference of P02 versus W00 and versus W01 (separate panels) | `FIG02_relative_energy_vs_pow.sha256` |
| FIG03 | Accepted blocks per run | `FIG03_accepted_blocks.sha256` |
| FIG04 | Median and p95 closed-round duration (separate panels) | `FIG04_round_durations.sha256` |
| FIG05 | Energy per accepted block (NA when a run has zero blocks) | `FIG05_energy_per_block.sha256` |
| FIG06 | Total, unique and duplicate physical evaluations | `FIG06_evaluations.sha256` |
| FIG07 | Accepted blocks per million physical evaluations | `FIG07_blocks_per_million_evals.sha256` |
| FIG08 | Stacked per-state residency decomposition | `FIG08_residency.sha256` |
| FIG09 | Stacked energy decomposition (primary hashing, range idle, reserve standby, wake transient, activated-reserve hashing, offline/other) | `FIG09_energy_decomposition.sha256` |
| FIG10 | Static and useful floor durations and deficit areas | `FIG10_floors.sha256` |
| FIG11 | Activation requests, incomplete activations, handoffs and reassignments per closed round | `FIG11_churn.sha256` |
| FIG12 | Energy-service Pareto plane (per-seed points and scenario centroids) | `FIG12_pareto.sha256` |
| FIG13 | Paired per-seed energy slopes W01->P02 and W00->P02 | `FIG13_energy_slopes.sha256` |
| FIG14 | Paired per-seed service slopes (accepted blocks) | `FIG14_service_slopes.sha256` |
| FIG15 | Representative P02 timeline (H_effective, H_pipeline, static floor, useful target, live wakes, the handoff event, accepted blocks) | `FIG15_timeline.sha256` |
| FIG16 | Normalised summary heatmap across scenarios and metrics | `FIG16_heatmap.sha256` |
| FIG17 | Policy evolution 8M -> 8R -> 8S -> P02 (descriptive only; no cross-stage inferential statistic) | `FIG17_policy_evolution.sha256` |
| FIG18 | Decision dashboard against the frozen pass/fail criteria | `FIG18_decision_dashboard.sha256` |
