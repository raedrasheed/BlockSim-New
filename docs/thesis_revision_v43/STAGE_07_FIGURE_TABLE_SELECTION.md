# Stage 7 — Figure and Table Selection

Selection of Stage-6A figures/tables that materially support the corrected thesis
argument. **Insertion of the figure image files into the DOCX is deferred** (see the
rendering limitation in `STAGE_07_RENDERING_REPORT.md`); this document records the
selection and the required corrected captions so the examiner copy's figure/table set is
specified and ready to embed once a working Word renderer is available.

## Selected figures (core set)

| # | Stage-6A figure | Thesis placement | Label |
|---|-----------------|------------------|-------|
| 1 | `fig01_h1_duplicate_rate` | §7.4 / candidate-redundancy subsection | CONFIRMATORY |
| 2 | `fig02_a1_energy_invariant` | §7.4.1 (replaces the obsolete PoW-vs-PoCol energy figure) | INVARIANT |
| 3 | `fig03_h5_completion_dispersion` | §7.5 / allocation subsection | CONFIRMATORY |
| 4 | `fig04_h5_c2_energy_tradeoff` | §7.4.3 | CONFIRMATORY |
| 5 | `fig06_h6_inactive` | §7.5 inactive-miner subsection | CONFIRMATORY |
| 6 | `fig07_h8_mu` | §7.5 μ-sensitivity subsection | CONFIRMATORY |
| 7 | `fig08_h7_delay_singleheight` | §7.5 secondary-diagnostic subsection or appendix | SECONDARY |
| 8 | `fig10_h5x_exploratory` | appendix | EXPLORATORY — NOT PREREGISTERED |

Corrected caption for fig04 (to be embedded verbatim): *"H5 [CONFIRMATORY] C2 idle-energy
trade-off under heterogeneous hash rates: weighted ranges remove modeled idle and return
energy to the fixed-power anchor. Each line connects seed-matched runs; equal-size ranges
create idle opportunity under heterogeneity; hash-rate-weighted ranges reduce
completion-time dispersion and remove that idle opportunity; the result is a
completion-balance versus idle-energy trade-off, not a reward or incentive result."*

## Selected tables (core set)

Analysis population + NA counts (`table01`), hypothesis disposition (`table03`),
confirmatory effects (`confirmatory_effects.csv`), energy decomposition (`table07`),
candidate redundancy (`table08`), allocation-policy trade-off (`table09`), inactive-miner
analysis (`table10`), zero-block results (`table11`), H7 secondary diagnostic (`table12`).
Detailed robustness (`table06`) → appendix. Every table must state the physical-run sample
size; the H1 table must state **150 physical pairs / 30 independent seed clusters**; B3/C1
must not be double-counted.

## Note

The obsolete draft-42 figures (Figures 7.4–7.8: PoW-vs-PoCol energy/carbon curves implying
miner-count energy scaling and 98–99% reduction) are superseded by the A1-invariant and
corrected-energy figures above and are flagged in red in the text. Actual image embedding
and re-captioning in the DOCX are pending a functional renderer.
