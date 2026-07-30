# Stage 6 — Results Report (Preregistered Statistical Analysis)

Preregistered statistical analysis, scientific interpretation, and results package for the
frozen 1,890-run BlockSim matrix (PoCol). Scientific data are byte-identical to Stage-5B2
results-1; no simulation was rerun. This report integrates the companion documents; all
numbers are reproduced by `analysis/thesis_revision_v43/stage_06/s6_run_all.py`.

## 1. Provenance and integrity

- Scientific source freeze-6 `45361674…`; results-3 `278af17…` (data byte-identical to
  results-1 `d2ef6012…`); bulk archive `thesis-v43-stage5b2-data-1` `b44975d…`; matrix
  SHA-256 `9cb7297e…`; engine/schema `5b1g.2`.
- Input-integrity gate: **12/12 PASS** (`STAGE_06_INTEGRITY_GATE.json`) — 1,890 runs, 63
  groups × 30 seeds, no same-seed duplicate, B3/C1 one dataset (870), 142 zero-block runs
  retained, scientific tree identical to results-1, archive ROUNDTRIP_OK, thesis DOCX/PDF
  checksums unchanged.

## 2. Headline findings

1. **Total fixed-horizon energy is an accounting invariant (A1).** For every continuous
   full-participation scenario and miner count, total energy = `P_total·T` = **8.420833333
   kWh** exactly (max relative deviation 3.6e-16). Search discipline changes coverage and
   energy-per-block, never total energy. **Partitioning alone does not reduce energy.**
2. **Duplicate coverage orders as B1 > B2 > B3/C1 (H1, SUPPORTED).** Redundant
   common-template search (B1 ≈ 0.995 duplicate rate) is near-always zero-block; circular
   disjoint (B2 ≈ 0.60) and disjoint (B3/C1 = 0.0) progressively remove duplication — under
   the immutable-common-template / disjoint idealization only.
3. **C2 energy savings are idle-driven, not partitioning-driven (H3/H4/H5).** Under
   homogeneous equal ranges the idle policy never triggers (saving = 0). Savings appear
   only when **heterogeneity** makes fast miners finish early and idle (H5 C2 equal:
   −3.4/−3.8 kWh). Weighted allocation restores completion symmetry and removes idle — and
   thereby **removes the saving** (energy returns to the anchor). Fairness–energy
   **trade-off**, not guaranteed superiority.
4. **Inactive miners lengthen block interval and cut throughput (H6, SUPPORTED);** raw
   energy falls with participation, but energy-per-accepted-block does not clearly rise
   (INCONCLUSIVE).
5. **Smaller μ increases range exhaustion and template refreshes (H8, SUPPORTED);** the
   realized block-interval increase is directionally consistent but not decisive
   (INCONCLUSIVE).
6. **Propagation delay raises the single-height stale rate (H7, SECONDARY DIAGNOSTIC):**
   0 → 0.0011 → 0.0050 → 0.0471 → 0.1005 stales/block at delay 0/0.42/5/30/60, while all
   primary metrics stay invariant. Not a fork-rate or security claim.

## 3. Required analyses (§12) — dispositions

| Analysis | Frozen id | Disposition |
|----------|-----------|-------------|
| A Energy accounting | A1 + H3 + H6 | invariant confirmed; savings idle-/participation-driven only |
| B Candidate redundancy | H1 | SUPPORTED (idealized assumptions) |
| C Allocation policy | H5 | SUPPORTED fairness + energy trade-off |
| D Miner count | covariate | no fixed-horizon energy scaling with N |
| E Inactive miners | H6 | SUPPORTED (primary); epab INCONCLUSIVE |
| F Scenario comparisons | H1/A1 | exact frozen defs; B3/C1 not double-counted |
| G Propagation delay | H7 | SECONDARY single-height diagnostic |

## 4. Claim classification

A1 SUPPORTED (identity); H1 SUPPORTED; H3 SUPPORTED (identity); H4 SUPPORTED; H5 SUPPORTED
+ trade-off; H6 SUPPORTED (primary) / INCONCLUSIVE (epab); H8 SUPPORTED (exhaustion,
refresh) / INCONCLUSIVE (interval); H7 SECONDARY_DIAGNOSTIC_ONLY; H5x EXPLORATORY. Details:
`STAGE_06_CLAIM_CLASSIFICATION.md`.

## 5. Statistical rigor

Statistical unit = one physical run per frozen seed; seed-matched paired inference; effect
sizes in scientific units first (mean + Hodges-Lehmann) with seed-pair bootstrap 95% CIs;
two-sided paired permutation tests (10,000, seed 6060602); Wilcoxon signed-rank
sensitivity; Holm within each confirmatory family. Zero-block runs retained;
block-normalised metrics NA. Deterministic design identities are reported as identities,
not tests. Robustness in `STAGE_06_ROBUSTNESS_RESULTS.md`.

## 6. Deliverables

Reports: analysis plan, preregistration map, field-usage audit, descriptive, confirmatory,
robustness, secondary, claim classification, limitations, this report, environment,
analysis manifest, checksum manifest. Tables: `results/…/stage_06/tables/` (12 + long +
effects). Figures (PDF+PNG+plotting data): `results/…/stage_06/figures/` and `…/plot_data/`
(10 figures). Models/diagnostics: `…/models/`, `…/diagnostics/`. Analysis code + tests:
`analysis/thesis_revision_v43/stage_06/`.

## 7. Scope

All findings are conditioned on the modelled assumptions, the fixed 10,000-second horizon,
and the frozen aggregate hash-rate setting; B0/B1 are abstractions, not real Bitcoin
mining; no security, fork-chain, fairness, or real-deployment claim is made
(`STAGE_06_LIMITATIONS.md`). No thesis DOCX/PDF was edited; no scientific result was
altered. Stage 6 does not begin thesis insertion.
