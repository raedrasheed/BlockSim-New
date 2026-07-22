# Editor-Mediated Revision — Deliverables

This folder contains the final editor-mediated revision of the manuscript
*"Extending BlockSim with Energy and Carbon Footprint Modeling for Sustainable
Blockchain Evaluation"*, addressing the handling editor's (Prof. Remo Pareschi)
consistency and editorial requests. No new experiments or scientific claims were
introduced; all changes are numerical/consistency/figure/editorial corrections.

## Files

| File | Description |
|---|---|
| `Manuscript_Final_Editor_Revision_Red.docx` | Clean revised manuscript. All inserted/corrected/replacement text in **red** (RGB 255,0,0 / #FF0000); unchanged text black; deleted text removed. |
| `Manuscript_Final_Editor_Revision_Red_Tracked.docx` | Tracked-changes version (`w:ins`/`w:del`) with insertions **also** manually coloured red. Accepting all changes reproduces the clean copy's body text exactly. |
| `Response_to_Handling_Editor.docx` | Point-by-point response to each editor comment. |
| `Final_Consistency_Numerical_and_Red_Text_Audit.docx` | Internal audit: compliance matrix, numerical reconciliation, model/CI/figure/parameter/red-text audits. |
| `Revision_Change_Log.xlsx` | Change log (18 changes) + numerical reconciliation sheet. |
| `Acceptance_Readiness_Checklist.docx` | Final acceptance-readiness checklist. |
| `FINAL_PRE_SUBMISSION_QC_REPORT.docx` | Final journal-acceptance QC pass: issues corrected, items requiring author confirmation, recommendation. |
| `scripts/` | Reproducible build scripts. `shared_edits.py` is the single source of truth consumed by both the clean and tracked builders. |

## Final QC pass (journal-acceptance)

A targeted QC pass (no rewrite) confirmed/added: figures kept as current 1–4
(author-confirmed; old misleading 1–3 already removed); every stochastic
parameter traced to `Models/Energy/scenarios.py` with σ notation (no invented
values); all headline numbers re-verified against `results/data/*.csv`; the only
±CI is on the stochastic PoW network energy; newly added prose shortened;
reference DOIs cleaned (`Website:`→`Available:`, stray trailing punctuation
removed). Three reference-metadata mismatches (Refs [3], [7], [8]) and the
Generative-AI/APC journal fields are flagged for author confirmation rather than
fabricated. Recommendation: **Ready after author confirmation of the listed
items only.**

## Key resolutions

* **Numerical inconsistency (1000 miners):** the conflicting 6092.25 / 6919 /
  6934.13 kWh (and 83.84 / 79.79 kWh) values were traced to single-seed
  fixed-power event-based runs over a 10,000 s horizon; the fixed-power
  presentation was removed (editor's preferred option). Reported energy is now
  the economic-PoW / PoS / communication set, verified against
  `results/data/*.csv` (PoW ≈ 467.5 GWh/24 h, invariant to miner count).
* **Figures:** Figures 1–3 (crypto-labelled, linear-compressed) deleted;
  Figures 4–7 renumbered 1–4; the carbon figure regenerated with generic
  `PoW scenario` / `PoS scenario` labels
  (`experiments/regenerate_carbon_figure_generic.py` →
  `results/figures/fig_carbon_vs_gamma_generic.png`).
* **New Table 1:** consolidated experimental parameters (all-red).
* **New §E:** Randomness, Replications, and Confidence-Interval Construction.
* **Editorial:** `PoW. PoW` → `PoW, PoS`; duplicate `[21]` reference prefix
  removed; duplicated step-density paragraphs removed.

## Author confirmation required

* Generative-AI disclosure: no such section exists in the supplied manuscript
  version; add the factual statement if the target journal requires one.
* APC/publication-charge field: complete in the journal's dedicated field if
  applicable (no APC text is in the scientific body).
