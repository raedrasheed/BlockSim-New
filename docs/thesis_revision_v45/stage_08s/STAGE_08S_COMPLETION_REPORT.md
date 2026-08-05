# Stage 8S — Completion Report (FINAL controller-refinement cycle)

**Branch:** `thesis-v45-pocol-stage8s-useful-floor-coarse-reassignment`, from the exact
remote HEAD `12baeae0cbba54234723d6ec79e4216e4948c689` of
`thesis-v45-pocol-stage8r-controller-refinement` (fetched; clean worktree; 213 tests
green; Stage-8R manifest verified; frozen Stage-8R dataset and analysis unchanged).

## Three-commit structure (as directed)

| commit | content |
|---|---|
| **1 — implementation + tests** | Phase-0 read-only structural feasibility analysis (key finding: the Stage-8R exploratory arm seated ZERO actual reassignments — its floor gain was tail truncation); modes `STAGE8R_PREDICTIVE_STATIC_FLOOR` (reproduces frozen R02 exactly), `USEFUL_FLOOR_ONLY`, `USEFUL_FLOOR_COARSE_REASSIGNMENT` behind the unchanged LEGACY default (reproduces frozen Stage-8M bit-exactly); S8S-TEST-01..22; 235 tests green |
| **2 — preregistration freeze** | S00/S01/S02/S03; fresh SHA-256 seeds (2 pilot + 12 confirmatory + analysis root) disjoint from all 54 previous registry seeds; frozen constants incl. the coarse partition rule, benefit gate, instant awake receivers and reserve admission; H-S1..H-S4 with the Holm family and the final-cycle no-retuning rule; structural pilot 8/8 pass (structure only) — committed BEFORE any confirmatory seed |
| **3 — execution + analysis + reports** | 48/48 runs (≤ 2 workers, atomic checkpoints, all integrity gates pass, ≈ 57 s), 3 timelines (S01/S02/S03 seed 0), frozen 48-row dataset, verbatim frozen analysis (byte-identical re-run), all reports, checksum manifest |

## Verification record

* Structural pilot 8/8 COMPLETED, all gates (modes execute; useful metrics exist; coarse
  fired in every S03 run; chunk union/disjointness pass; admission enforced; feasible).
* Execution 48/48 COMPLETED, all integrity gates pass; checkpoints checksum-verified;
  exactly 3 timelines with verified digests.
* Tests at every commit: 195 accepted + 18 Stage-8R + 22 Stage-8S (235). Historical
  Stage-6M/7M/8M/8R manifests verify throughout; no historical file modified; thesis
  DOCX/PDF untouched; no CI.
* Deterministic checks: `generate_8s.py --check` byte-identical; `analyze_8s.py` re-run
  byte-identical.

## Preregistered outcome (final; no further tuning)

**H-S1 SUPPORTED** (+10.58 blocks vs the Stage-8R controller, p = 1/4096, Holm — the
largest gain of the program); **H-S2 FAIL on one gate** (throughput ratio 0.9039 PASSES
the 0.90 gate for the first time; duration and integrity gates pass; below-useful-floor
28.71 s > 15 s fails); **H-S3 FAIL** (requests and incomplete counts rose; 1.748
reassignments/round > 1.0); **H-S4 PASS** (55.1 % retained accounting benefit).
**Overall structural-policy claim: NOT LICENSED.** Per the frozen final-cycle rule the
result is preserved as-is, remaining limitations are declared as future work, and no
further controller-refinement stage will be opened. Stage 9 not begun.

## Deliverables

All sixteen `STAGE_08S_*` deliverables exist under `docs/thesis_revision_v45/stage_08s/`
(feasibility report + metrics, implementation, tests, preregistration, seed registry,
experiment matrix, run dataset, analysis report, hypothesis decisions, static-and-useful
floor results, reassignment report, energy decomposition, limitations, thesis insertion
package, checksum manifest, this report), with code under
`experiments/thesis_revision_v45/stage_08s/` and tests under
`tests/thesis_revision_v45/stage_08s/`.
