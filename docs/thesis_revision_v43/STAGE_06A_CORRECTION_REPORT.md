# Stage 6A — Statistical and Interpretive Correction Report

Corrective analysis branch `thesis-v43-stage6-analysis-2`, created from the accepted
Stage-6 commit `547ea339c64aa2475b8faa4e88b934925d550df4` (analysis-1, preserved
unchanged). No simulation was rerun; no scientific result, seed, engine, matrix,
preregistration, or thesis file was modified. This branch fixes four analysis/wording
defects identified in the final audit.

## Defect 1 — Unsupported "fairness" wording (H5)

All protocol-level / economic **fairness claims** are removed from Stage-6 analysis
scripts, reports, claim files, table labels, figure titles, captions, plotting-data
metadata, and manifests, and replaced with precise modeling terms: **modeled
range-completion balance / completion-time symmetry / completion-time dispersion reduction
/ modeled workload proportionality**. H5's disposition is now:

> **SUPPORTED for reduced modeled completion-time imbalance and idle; documented energy
> trade-off.**

No reward-, incentive-, participation-, economic-, proof-of-effort-, or Sybil-resistance
claim is made. Where prose disclaims these (e.g. the exact fig04 caption "not an
incentive-fairness or reward-fairness result"), it is a **negation**, not a claim. The
earlier positive figure-title wording (a "restores …" phrasing) is removed.
`STAGE_06_LIMITATIONS.md` remains consistent with all H5 reports.

## Defect 2 — H3 idle-saving identity not directly verified

The preregistered identity `saving = Σ_j idle_time_j·(P_active_j − P_idle_j)/3.6e6` is now
verified **directly from per-miner records** for all **570** C2 runs, using frozen
parameters. **Max absolute residual 7.1e-15 kWh** (tolerance 1e-9), **0 failures**. H3 is
classified **SUPPORTED**; had it not reconciled, the sub-claim would be
`NOT_TESTABLE_AS_PREREGISTERED`. Details: `STAGE_06A_H3_IDENTITY_AUDIT.md`,
`results/thesis_revision_v43/stage_06a/diagnostics/h3_idle_saving_identity.csv`.

## Defect 3 — Invalid binomial/Wilson intervals on a stale count-rate (H7)

Wilson / Clopper-Pearson / binomial rule-of-three intervals on
`stale_block_count / accepted_blocks` are **removed** (several distinct miners may stale at
one accepted height, so it is not a Bernoulli rate). H7 now uses **run-level count-rate
descriptives with a seed/run-cluster bootstrap 95% CI**, **N=100 and N=500 kept separate**,
plus a **separate binary** diagnostic `heights_with_any_stale / accepted_heights`. Delay=0
reports "0 stale blocks observed across the accepted heights"; any model-based zero-event
bound is labelled ASSUMPTION-DEPENDENT / SECONDARY and is not called "exact binomial". H7
remains **SECONDARY_DIAGNOSTIC_ONLY**. Details: `STAGE_06A_H7_INTERVAL_AUDIT.md`.

## Defect 4 — H1 pooled inference ignored seed clustering

H1 uncertainty is now computed from **30 independent seed clusters** (the 30 master seeds
recur across five miner counts, so the 150 physical pairs are not independent). Per seed,
the five per-N differences are aggregated by their direction-preserving mean; seed-cluster
bootstrap / permutation / Hodges-Lehmann operate on the 30 clusters; N-specific analyses
(30 pairs each) are retained as robustness. **Physical run pairs = 150; independent
clusters = 30** are reported separately, and the 150 are never presented as independent
replications. The three scientific contrasts (B1>B2, B2>B3/C1, B1>B3/C1) are retained with
Holm on the stochastic cluster-level contrasts. **The H1 conclusion is unchanged** (ordering
holds; cluster CIs appropriately wider but exclude 0). Details:
`STAGE_06A_DEPENDENCE_AUDIT.md`.

## Regenerated outputs

`confirmatory_effects.csv`, `claim_classification.json`, `analysis_bundle.json`,
`confirmatory_results.json`, `h7_secondary.json`, `a1_invariant.json`,
`table03_hypothesis_test_map.csv`, `table06_robustness.csv`, `table12_secondary_stale.csv`,
`fig04_h5_c2_energy_tradeoff` (PDF/PNG/plot data), `fig08_h7_delay_singleheight`
(PDF/PNG/plot data), the affected reports, figures/tables indexes, the analysis manifest,
and the checksum manifest. New: `stage_06a/diagnostics/h3_idle_saving_identity.csv` and the
four `STAGE_06A_*` documents. Unaffected numeric outputs (A1, H4, H5, H6, H8 tables and
their figures/plot-data) are regenerated identically by the deterministic pipeline.

## Integrity and quality gates (§8)

- Input-integrity gate **12/12 PASS**.
- Frozen scientific test suite: **444 passed, 0 failed**.
- Stage-5B2 data-integrity tests: **10 passed**.
- Stage-6 + Stage-6A analysis tests: **30 passed** (14 Stage-6 + 16 Stage-6A).
- Full analysis pipeline reproduces **byte-identical** numeric outputs and the H3
  identity CSV on re-run (deterministic RNG).
- Scientific data tree byte-identical to results-1 (0 changed files across
  summary/per_miner/per_template/block_log/stale_race/full_logs). The only Stage-5B2
  manifest that differs from results-1 is `bundle_manifest.json`, which is the **accepted
  Stage 5B2A reconciliation** (identical to results-3), not a Stage-6/6A change.
- Thesis DOCX/PDF byte-identical (`2c3afdc5…`, `131412bb…`).
- Delta vs analysis-1 (`547ea339…`): 6 files added, 39 modified, 0 deleted — analysis
  only.

Reproduce with `python3 analysis/thesis_revision_v43/stage_06/s6_run_all.py` (+
`s6_claims.py`).
