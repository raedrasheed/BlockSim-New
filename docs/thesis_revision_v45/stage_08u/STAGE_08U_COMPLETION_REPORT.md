# Stage 8U — Completion Report

**Branch:** `thesis-v45-pocol-stage8u-single-handoff-pow-comparison`, from the exact
remote HEAD `bb588e881b667ed021d6cdbbda9971a14a0ae259` of
`thesis-v45-pocol-stage8s-useful-floor-coarse-reassignment` (fetched and recorded before
any edit; clean worktree; 235 accepted tests green; Stage-8S checksum manifest verified;
Stage-8S dataset and analysis unchanged; difficulty 1000 and its fixed target
`floor((2^256−1)/1000)` verified frozen; matplotlib 3.11.1 available).

**Outcome: the single-handoff useful-work policy within PoCol is NOT LICENSED.**
H-U1 PASS, **H-U2 FAIL**, H-U3 PASS, **H-U5 FAIL**, all integrity gates PASS in 60/60
runs.  Per the directive this closes the refinement line: no retuning, no Stage 8V, no
Stage 9, results preserved.

## Three-commit structure (as directed)

| commit | content |
|---|---|
| **1 — implementation** | Phase-0 read-only PoW baseline audit (written before any engine edit); the ADDITIVE `Models/PoCol/stage2/matched_pow.py` matched same-template PoW control (W00/W01); the `USEFUL_FLOOR_SINGLE_HANDOFF` mode (U1–U5) behind an unchanged `LEGACY_REACTIVE` default; the frozen deterministic figure/table core; U-TEST-01..22; implementation + test reports |
| **2 — preregistration freeze** | the exactly-five scenarios; fresh SHA-256 seeds (2 pilot + 12 confirmatory + analysis root) executably disjoint from all 69 seeds of every previous registry; the execution harness; the structural pilot (10/10, structure only); `STAGE_08U_PREREGISTRATION.md` with H-U1..H-U5, the joint licensing rule, the Holm family and the frozen figure plan — committed BEFORE any confirmatory seed executed |
| **3 — execution + analysis** | 60/60 confirmatory runs (≤ 2 workers, atomic checkpoints, all integrity gates pass), the frozen 60-row dataset, the verbatim preregistered analysis, FIG01–FIG18 with byte-identical regeneration, all comparison tables and reports, checksum manifest |

## Verification record

* **Structural pilot**: 10/10 COMPLETED, every gate pass, worst wall 2.98 s. No
  parameter, seed, margin, target, difficulty or scenario definition was tuned after it.
  One harness defect was fixed during the pilot and is recorded in the preregistration:
  the one-reserve-wake-per-round integrity gate was initially mis-scoped onto the P01
  coarse baseline, which may legitimately seat several wakes per round; it now applies
  to P02 only. No engine or experimental definition changed.
* **Execution**: 60/60 COMPLETED, every integrity gate pass, total wall ≈ 69 s;
  checkpoints checksum-verified; exactly 2 diagnostic timelines with verified digests.
* **Tests**: **257 passed** — 195 accepted Stage-2 + 18 Stage-8R + 22 Stage-8S + 22
  Stage-8U. Every previously accepted test retained and unmodified.
* **Determinism**: `generate_8u.py --check` reports every table, caption and metadata
  file byte-identical; the full 60-run execution was reproduced bit-exactly after an
  environment reset (identical record checksums, identical analysis output).
* **Historical evidence**: the Stage-8S checksum manifest verifies at this commit; the
  Stage-8M, Stage-8R and Stage-8S datasets, analyses and reports are byte-identical and
  are never reinterpreted as new-controller results.
* No CI was created or waited for; all evidence is local tests, deterministic validators
  and checksum manifests. Thesis DOCX/PDF untouched. Stage 9 not begun.

## Preregistered outcome (honest, no forced success)

* **H-U1 churn — PASS.** Reassignments 0.4535 per closed round (≤ 1.0); activation
  requests 0.00 versus P01's 646.67; incomplete activations 0.00 versus 425.00. Both
  Holm contrasts rejected at p = 0.000488. The Stage-8S churn failure is not merely
  reduced but eliminated.
* **H-U2 service vs the capacity-matched PoW control — FAIL.** Accepted-block ratio
  0.6770 (gate ≥ 0.90); median-duration ratio 5.2190 (gate ≤ 1.10). Paired block
  difference −78.08 (CI [−88.58, −68.17], p = 0.000488, Holm-rejected against P02). The
  cause is partitioned search: a PoCol round waits for the single miner owning the
  winning nonce, while every uncoordinated PoW node can find any solution — at roughly
  nine times the physical work.
* **H-U3 energy vs the capacity-matched PoW control — PASS.** Relative reduction 0.4495
  (CI [0.4487, 0.4502]), paired difference −0.013208 kWh (p = 0.000488, Holm-rejected).
* **H-U4 population-matched sensitivity (no gate).** Energy −54.86%; blocks −85.75;
  median duration +0.989 s; total evaluations −1 307 776; duplicates 0 versus 1 228 115;
  energy per accepted block −4.577e-5 kWh.
* **H-U5 operational useful-work limit — FAIL.** Mean duration below the useful floor
  23.13 s (gate ≤ 15 s), improved from the Stage-8S baseline's 27.70 s on these same
  fresh seeds. Every structural component passed exactly: zero nonterminal handoff
  epochs, activations, leases and reassignments; zero duplicate nonces; zero post-round
  evaluations; zero physical-frontier rewinds.
* **Joint rule: NOT LICENSED.**

## Scope discipline

SHA-256 evaluation semantics, the accepted target, fixed difficulty, nonce-domain
semantics, physical hash rates, the immutable evaluation ledger and the
accepted/actual/physical frontier authorities are unmodified (U-TEST-19 plus the 235
retained accepted tests). The historical static floor was never lowered or redefined and
the static and useful floor families remain independently computed and reported (U5).
`H_effective` stays physical — WAKING miners contribute zero. Legacy PoW code was audited
read-only and left byte-identical; no old thesis PoW numbers were reused, because their
assumptions differ (documented per implementation in the Phase-0 audit).

## Deliverables (docs/thesis_revision_v45/stage_08u/)

STAGE_08U_POW_BASELINE_AUDIT.md, STAGE_08U_IMPLEMENTATION_REPORT.md,
STAGE_08U_TEST_REPORT.md, STAGE_08U_PREREGISTRATION.md, STAGE_08U_SEED_REGISTRY.csv,
STAGE_08U_EXPERIMENT_MATRIX.csv, STAGE_08U_RUN_DATASET.csv,
STAGE_08U_ANALYSIS_REPORT.md, STAGE_08U_HYPOTHESIS_DECISIONS.csv,
POW_POCOL_COMPARISON_TABLE.csv, POW_POCOL_EFFECT_ESTIMATES.csv,
POW_POCOL_FIGURE_INDEX.md, POW_POCOL_CAPTION_PACKAGE.md, STAGE_08U_LIMITATIONS.md,
STAGE_08U_THESIS_INSERTION_PACKAGE.md, STAGE_08U_CHECKSUM_MANIFEST.sha256,
STAGE_08U_COMPLETION_REPORT.md, and `figures/` (FIG01–FIG18 × SVG + 300-dpi PNG + CSV +
caption + metadata + checksum = 108 files).
Code: `experiments/thesis_revision_v45/stage_08u/`; tests:
`tests/thesis_revision_v45/stage_08u/`; the additive control:
`Models/PoCol/stage2/matched_pow.py`.

## Final state

This was the final improvement attempt. The joint gate failed on H-U2 and H-U5; the
result is preserved as recorded, the remaining limitations are documented in
`STAGE_08U_LIMITATIONS.md` as future work, and refinement stops here.
