# Stage 8R — Completion Report

**Branch:** `thesis-v45-pocol-stage8r-controller-refinement`, from the exact remote HEAD
`b7580a1f3b15b9eaf3ae3a9b0b74452bfbd014e3` of `thesis-v45-pocol-stage8m-minimal-analysis`
(fetched and recorded before any edit; clean worktree; 204 tests green; Stage-7M/8M
manifests verified; engine digests incl. `search.py` verified unchanged at baseline).

## Three-commit structure (as directed)

| commit | content |
|---|---|
| **1 — implementation** | Phase-0 read-only baseline diagnostic (report + metrics + M03 timeline CSV); the revised controller (R1–R6) behind a LEGACY_REACTIVE default that reproduces the frozen Stage-8M M03 record bit-exactly; R-TEST-01..18; implementation + test reports |
| **2 — preregistration freeze** | scenarios R00/R01/R02/R03; fresh SHA-256 seeds (2 pilot + 12 confirmatory + analysis root), executably disjoint from all 39 previous registry seeds; frozen 0.78/0.80/0.82, lookahead = cooldown = wake latency, 25-nonce chunk; H-R1..H-R5 with Holm family and the joint licensing rule; structural pilot (structure only, all gates pass) — committed BEFORE any confirmatory seed executed |
| **3 — execution + analysis** | 48/48 runs (≤ 2 workers, atomic checkpoints, all integrity gates pass), 3 full diagnostic timelines (R01/R02/R03 seed 0), frozen 48-row dataset, verbatim preregistered analysis (byte-identical re-run), all reports, checksum manifest |

## Verification record

* Structural pilot: 8/8 COMPLETED, every gate pass, worst wall 4.39 s; no parameter tuned.
* Execution: 48/48 COMPLETED, every integrity gate pass, total wall ≈ 59 s; checkpoints
  checksum-verified; exactly 3 timelines with verified digests.
* Tests: 195 accepted + 18 R-TESTs pass at every commit. Frozen Stage-6M gate
  `test_s6m_08` (engine byte-identity to Stage-5D) fails on this branch BY CONSTRUCTION
  (engine modification was authorized); the Stage-6M/7M/8M evidence and manifests are
  untouched and still verify.
* Deterministic checks: `generate_8r.py --check` byte-identical; `analyze_8r.py` re-run
  byte-identical. No CI created or waited for.

## Preregistered outcome (honest, no forced success)

* H-R1 supported (+2.67 blocks, p = 0.00049, Holm); H-R2 supported (below-floor −0.54 s,
  deficit area −3 069 hash·s, unattainable decisions 999.8 → 51.8, p = 0.00024, Holm);
  **H-R3 refuted** in its declared outcome (requests 312.8 → 593.7, p = 1.0) despite the
  batch-decision collapse; **H-R4 FAIL** (blocks ratio 0.852 < 0.90; below-floor 274 s >
  15 s); H-R5 PASS (relative reduction 0.574). **Revised-policy claim: NOT LICENSED.**
* Root cause of the H-R4 failure is structural (4-reserve pool = 1 000 H vs a 3 200 H
  floor), quantified in the analysis report; changing the population would be a new
  experiment.
* The historical Stage-8M conclusion is preserved verbatim and unmodified.

## Deliverables (docs/thesis_revision_v45/stage_08r/)

BASELINE_DIAGNOSTIC_REPORT.md, BASELINE_DIAGNOSTIC_METRICS.json,
BASELINE_TIMELINE_M03_S00.csv, IMPLEMENTATION_REPORT.md, TEST_REPORT.md,
PREREGISTRATION.md, SEED_REGISTRY.csv, EXPERIMENT_MATRIX.csv, RUN_DATASET.csv,
ANALYSIS_REPORT.md, HYPOTHESIS_DECISIONS.csv, ENERGY_DECOMPOSITION.csv,
ACTIVATION_LIFECYCLE_REPORT.csv, LIMITATIONS.md, THESIS_INSERTION_PACKAGE.md,
CHECKSUM_MANIFEST.sha256, COMPLETION_REPORT.md.
Code: `experiments/thesis_revision_v45/stage_08r/`; tests:
`tests/thesis_revision_v45/stage_08r/`. Thesis DOCX/PDF untouched; Stage 9 not begun.
