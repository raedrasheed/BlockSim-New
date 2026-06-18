# Change Log — Conservative Red-Line Revision

This revision edits the **original manuscript in place**, preserving its
structure, headings, numbering, fonts (Times New Roman), figure/reference style,
and writing flow. **All added or changed text is coloured RED** in the DOCX;
unchanged original text is left untouched. No section was removed or rewritten.

Original figures (1–6) are preserved; four new figures were appended as
**Figures 7–10** so existing numbering is not disturbed. Three references were
appended as **[19]–[21]**.

## Exact additions / changes and their location

| # | Location (existing section) | Change | Colour |
|---|---|---|---|
| 1 | Abstract | Relabelled "Proof-of-Work reference models (Bitcoin and Ethereum)" → PoW reference configurations incl. *historical Ethereum-like PoW configuration* not representing current PoS Ethereum | RED (changed span) |
| 2 | Abstract | Appended sentence: PoW economic vs PoS validator distinction; γ varied; scenario-based, not a precise estimator | RED |
| 3 | Keywords | Appended "Proof of Stake, Carbon Footprint, Energy Modeling, Sustainability" | RED |
| 4 | Introduction (after "This study expands upon BlockSim…") | Added paragraph: PoW energy is economically driven (coin price, block subsidy, fees, electricity price, efficiency, difficulty/hashrate); PoS validator-driven; Ethereum Merge / not PoW | RED |
| 5 | Background & Related Work (end) | Added subsection **"Energy, Permissionlessness, and Sybil Resistance"** + paragraph (PoW vs PoS, freeness/cost, Sybil trilemma) citing [16],[4],[19],[20],[8] | RED |
| 6 | Energy Modeling §B (Communication) | Added pointer that communication energy is now instrumented and analysed | RED |
| 7 | Energy Modeling §C (end) | Added subsection **"D. Proof-of-Work Economic Energy Model"** with R=(B+F)·P, E_budget=κR/C_elec, E_technical, E_PoW=min(…), E_i=s_i·E_PoW | RED |
| 8 | Energy Modeling (after D) | Added subsection **"E. Proof-of-Stake Validator Energy Model"** with E_PoS=Σ(P_v·T·u_v)/1000+E_comm | RED |
| 9 | Carbon Footprint Modeling §A | Added paragraph: γ treated as experimental variable (low/avg/high) | RED |
| 10 | Carbon Footprint **Analysis** | Qualified pre-existing "fixed emission factor [3]" → emission factor varied across grid scenarios | RED (changed span) |
| 11 | Experimental Setup §B | Relabelled "Bitcoin (Model 1) and Ethereum (Model 2)" → historical Ethereum-like PoW configuration, not current Ethereum | RED (changed span) |
| 12 | Experimental Setup §C | Qualified "fixed electricity emission factor" → configurable, varied across low/avg/high grids | RED (changed span) |
| 13 | Experimental Setup §D | Replaced "replicated several times … averaged values" → 30 seeds (base+i), mean, standard deviation, 95% CI | RED (changed span) |
| 14 | Results §A | Added paragraphs: scenario-based caveat; PoW total invariant to miner count & price-driven; PoS validator results; PoW/PoS ratio; E=P·T sanity check | RED |
| 15 | Results §A | Added **Figure 7** (PoW energy vs miners) and **Figure 8** (PoS energy vs validators) | RED captions |
| 16 | Results §A | Added communication-energy analysis paragraph + **Figure 9** (computation vs communication) | RED |
| 17 | Carbon Footprint Analysis | Added γ-sensitivity paragraph (numbers) + **Figure 10** (carbon vs γ) | RED |
| 18 | Discussion / Threats to Validity | Added three limitation paragraphs (scenario-based; PoW/PoS sensitivities; regional γ; historical-Ethereum & communication caveats) | RED |
| 19 | References | Appended **[19]** Platt et al. 2021, **[20]** Platt, Platt & McBurney 2024, **[21]** De Vries Patterns 2022/2023 (DOI 10.1016/j.patter.2022.100633) | RED |

## Code changes (minimal, additive)
The supporting models/experiments added in the prior commit are reused to
generate the numbers and Figures 7–10:
- `Models/Energy/` — `PowEconomicEnergyModel`, `PosValidatorEnergyModel`,
  `CommunicationEnergyModel`, `CarbonFootprintModel`.
- `experiments/` — PoW miner scaling, PoW price sensitivity, PoS validator
  scaling, carbon γ sensitivity, communication analysis (30 seeds, mean/std/CI).
- `tests/test_energy_models.py` — 11 unit tests.

No existing BlockSim source file was modified; `Main.py` / `InputsConfig.py`
are unchanged (backward compatible).

## Build
- `docs/conservative_revision.py` → red-line DOCX (edits the original).
- `docs/docx_to_pdf.py` → matching PDF (preserves red + figures).

## Phrase audit (revised DOCX & PDF)
`validated` 0 · `Ethereum miners` 0 · `Ethereum PoW` 0 ·
`Proof-of-Work reference models (Bitcoin and Ethereum)` 0 ·
`replicated several times` 0 · `fixed emission factor` only in the added RED
sentence stating it *is insufficient*. De Vries DOI present.

## Math formatting stage (OMML)
A second stage (`docs/fix_math_omml.py`) converts the added plain-text
mathematics into **native Word equations (OMML)** while keeping them RED:
- Rebuilt the PoW (§D) and PoS (§E) prose so every symbol is inline OMML
  (10 inline equations in §D, 6 in §E).
- Added **displayed, numbered equations (8)–(11)** — R_t=(B_t+F_t)·P_t,
  E_budget,t=κR_t/C_elec,t, E_i,t=s_i,t·E_PoW,t, and
  E_PoS=(Σ_{v=1..V} P_v·T·u_v)/1000+E_comm — built as clones of the original
  equation-table style (so they match Equations 1–7 and continue the numbering).
- Converted inline "E = P × T" in the Results to OMML (E = P · T).
- Greek (κ, γ, ε), proper sub/superscripts, upright roman labels (PoW, PoS,
  elec, budget, comm, block, tx), fraction bars, and Σ with limits are used.
- Audit: no raw LaTeX (`\frac`, `\sum`, `\mathrm`, `_{`, `^{`) and no plain-text
  math tokens (E_PoS, E_budget, gamma, kappa, …) remain. Original Equations
  (1)–(7) are untouched (black); all added equations are red.

Build order: `python docs/conservative_revision.py` then
`python docs/fix_math_omml.py` then `python docs/docx_to_pdf.py`.

## Figure-reference & citation stage
A third stage (`docs/add_figure_refs.py`) adds the missing in-text references
and citation, leaving Figures 1-6 untouched:
- **Figure 7** cited in Results (red): "Figure 7 summarizes the sensitivity of
  PoW network energy to the number of miners ...".
- **Figure 8** cited in Results (red): "As shown in Figure 8, PoS total energy
  scales linearly with the number of validators ...".
- **Figure 9** cited in Results (red): "Figure 9 compares computational
  (consensus) energy with communication energy ...".
- **Figure 10** cited in Carbon Analysis (red): "Figure 10 reports the
  carbon-emission sensitivity under low, average, and high ... γ.".
- **Reference [21]** (De Vries, Patterns) is now cited 3× in the De Vries/Merge
  discussion (Introduction, Background, Results). These red sentences previously
  pointed to [8] (Gervais in the original list); the pointer was corrected to
  [21]. Original black [8] (Gervais) citations are unchanged and still cited.
- Audit: Figures 1-6 images byte-identical (6/6 unchanged); all references
  [1]-[21] cited at least once; every figure number in a caption also appears in
  the text; numbering sequential 1-10, no duplicates; all added sentences RED.

Full build order: `python docs/conservative_revision.py` ->
`python docs/fix_math_omml.py` -> `python docs/add_figure_refs.py` ->
`python docs/docx_to_pdf.py`.

## Formatting-only pass (stage 4)
`docs/format_revision_pass.py` finalises formatting without changing content:
- **New figures de-embedded**: the four embedded new figures (image7-10) are
  replaced by RED, 10 pt, centered placement markers — "[Insert Figure N here:
  ...]" — immediately after the paragraph that cites each figure; captions kept.
- **Separate figure files**: new figures exported to `figures_revision/` as
  Figure7_PoW_energy_sensitivity, Figure8_PoS_validator_scaling,
  Figure9_computation_vs_communication, Figure10_carbon_gamma_sensitivity
  (PNG + PDF each).
- **Added/revised text → 10 pt, justified**; new subsection headings now inherit
  the original Heading-2 style (10 pt) instead of an 11 pt override.
- **Bug fix (Figures 5-6 restored)**: a spanned phrase-replacement in the carbon
  paragraph had earlier removed the embedded original Figures 5 and 6; the
  replacement now preserves image runs. All six original figures (1-6) are again
  byte-identical to the source and remain unchanged.
- Equations (11 displayed) and all in-text references/citations preserved.

Full build order: conservative_revision.py -> fix_math_omml.py ->
add_figure_refs.py -> format_revision_pass.py -> docx_to_pdf.py.

## Numbering & figure-cleanup pass (stage 5)
`docs/renumber_eq_fig.py` — numbering/consistency only, no content rewrite:
- **Equations renumbered by order of appearance** so they run 1–11 with no gaps
  or duplicates. The added PoW/PoS equations, previously (8)–(11), are now
  **(5)–(8)**; the original carbon equations, previously (5)–(7), are now
  **(9)–(11)**. In-text references updated: §D now cites Eq. (5)/(6)/(7); §E now
  cites Eq. (8).
- **Old uncited Figures 4–6 deleted** (the cumulative-CO₂ and Bitcoin-vs-Ethereum
  carbon-comparison plots, images 4–6) together with their two orphaned
  reference sentences ("Figure. 4 shows …", "Figures 5–6 compares …").
- **Figures renumbered**: former Figures 7→**4**, 8→**5**, 9→**6**, 10→**7**
  (markers, captions and in-text references all updated). Figures 1–3 unchanged.
- **Separate figure files renamed** accordingly in `figures_revision/`:
  Figure4_PoW_energy_sensitivity, Figure5_PoS_validator_scaling,
  Figure6_computation_vs_communication, Figure7_carbon_gamma_sensitivity.
- The response letter was updated (former Figures 7–10 → 4–7; note that old
  uncited Figures 4–6 were removed).

> NOTE on earlier sections of this changelog: references above to the added
> figures as "Figures 7–10" and to "Figures 1–6" predate this stage. The
> authoritative final numbering is: original Figures **1–3** retained; old
> Figures **4–6 deleted**; new figures are **4–7**; displayed equations **1–11**.

Full build order: conservative_revision.py → fix_math_omml.py →
add_figure_refs.py → format_revision_pass.py → renumber_eq_fig.py →
docx_to_pdf.py.
