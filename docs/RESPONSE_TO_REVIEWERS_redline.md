# Response to Reviewers (Conservative Revision)

**Manuscript:** Extending BlockSim with Energy and Carbon Footprint Modeling for Sustainable Blockchain Evaluation
**Authors:** Raed S. Rasheed, Aiman A. AbuSamra

We thank both reviewers. In line with a conservative revision, we retained the
original manuscript structure, headings, numbering, figure style, and reference
style, and **added the reviewer-requested content as targeted insertions**. In
the revised DOCX, **all new or changed text is shown in red** for easy
identification. Below we respond point by point; locations refer to the existing
section names (no sections were renumbered). Reported numbers are scenario-based
model outputs produced by the released experiment scripts.

---

## Reviewer 1

**R1.1 — PoW energy is economically driven (price/reward).**
Response: Agreed. Revision made: added a red clarification in the Introduction
and a new red subsection "D. Proof-of-Work Economic Energy Model" in the Energy
Consumption Modeling section, where the expected reward R=(B+F)·P and the
economic budget E_budget=κ·R/C_elec make coin price, subsidy, fees, and
electricity price explicit; Results §A reports that the network total is
invariant to miner count and scales with coin price. Location: Introduction;
Energy Modeling §D; Results §A; Figures 4.

**R1.2 — Ethereum is no longer PoW; cite De Vries 2022.**
Response: Corrected. Revision made: red statements that Ethereum moved to PoS at
The Merge (Sept 2022) appear in the Introduction, Experimental Setup §B, Results
§A, and Threats to Validity; reference [21] (De Vries, Patterns, DOI
10.1016/j.patter.2022.100633) added. Location: Introduction; §B; Results;
References [21].

**R1.3 — Model PoW and PoS as two distinct models.**
Response: Done. Revision made: red subsection "D. Proof-of-Work Economic Energy
Model" and red subsection "E. Proof-of-Stake Validator Energy Model"
(E_PoS=Σ(P_v·T·u_v)/1000+E_comm) added; PoS results and Figure 5 added. Cites
Sedlmeir [16] and Platt et al. [19]. Location: Energy Modeling §D, §E; Results
§A; Figure 5.

**R1.4 — Permissionlessness, Sybil resistance, freeness; cite Platt/Platt/McBurney 2024.**
Response: Added. Revision made: new red subsection "Energy, Permissionlessness,
and Sybil Resistance" in Background, discussing PoW vs PoS, freeness/cost, and
the Sybil-attack vulnerability trilemma, citing [16], [4], [19], [20], [8].
Location: Background & Related Work.

---

## Reviewer 2

**R2.1 — Position as preliminary scenario-based tool, not precise estimator.**
Response: Done. Revision made: red statements in the Abstract, Results §A, and
Threats to Validity that absolute values are scenario-based model outputs, not
real-world measurements. Location: Abstract; Results; Threats.

**R2.2 — γ sensitivity.**
Response: Added. Revision made: red paragraph in Carbon Footprint Modeling §A
defining low/average/high γ; red γ-sensitivity results paragraph and Figure 7
in Carbon Footprint Analysis. Location: Carbon Modeling §A; Carbon Analysis;
Figure 7.

**R2.3 — Mining difficulty / hashrate dynamics.**
Response: Added as parameters/hooks. Revision made: red text in Energy Modeling
§D introduces H_block=D·2^32, ε_hash, and difficulty/hashrate dependence; the
code exposes difficulty, network hashrate, and an optional retargeting routine.
Location: Energy Modeling §D.

**R2.4 — Seeds, replications, standard deviation, 95% CI.**
Response: Done. Revision made: red replacement in Experimental Setup §D — 30
independent seeds (base+i), mean, standard deviation, and 95% confidence
interval; CIs shown in Figures 4–7 and Results §A. Location: §D; Results;
Figures 4–7.

**R2.5 — Inconsistent values across text/figures/tables.**
Response: Addressed. Revision made: added numbers are generated from a single
pipeline (CSV → text/figures) and are mutually consistent; the previously
inconsistent Ethereum-vs-Bitcoin framing is relabelled as a historical
Ethereum-like PoW configuration. Location: Results; Carbon Analysis.

**R2.6 — Improve criticized figures, keep style.**
Response: Done. Revision made: original Figures 1–3 are retained; the uncited old carbon-comparison plots (former Figures 4–6) were removed, and
four improved figures with error bars and appropriate log/separate axes were
added as Figures 4–7 (energy vs miners, PoS vs
validators, computation vs communication, carbon vs γ), avoiding the compressed
single-axis comparison the reviewer flagged. Location: Results; Carbon Analysis.

**R2.7 — Communication-energy model defined but not analyzed.**
Response: Fixed. Revision made: red pointer in Energy Modeling §B and a red
communication-energy analysis in Results §A (transaction rate / block size /
peer degree), with Figure 6, reported separately from consensus energy.
Location: Energy Modeling §B; Results §A; Figure 6.

**R2.8 — Remove/qualify "validated".**
Response: The word "validated" does not appear in the manuscript. Revision made:
we use "analytical sanity check (E = P × T)" and "evaluated through controlled
scenario-based simulations"; no validation against field data is claimed.
Location: Results §A; Threats to Validity.

---

## New references added
[19] Platt et al. 2021 (QRS-C, DOI 10.1109/QRS-C55045.2021.00168);
[20] Platt, Platt & McBurney 2024 (DOI 10.1080/17445760.2024.2352740);
[21] De Vries 2022/2023, Patterns (DOI 10.1016/j.patter.2022.100633).
Sedlmeir et al. 2020 was already cited as [16].

We believe these targeted additions address every comment while preserving the
original manuscript. We thank the reviewers for their guidance.
