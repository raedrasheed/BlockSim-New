# Response to Reviewers

**Manuscript:** Extending BlockSim with Energy and Carbon Footprint Modeling for Sustainable Blockchain Evaluation
**Authors:** Raed S. Rasheed, Aiman A. AbuSamra

Dear Editor and Reviewers,

We sincerely thank the reviewers for their constructive and detailed comments. We revised the manuscript carefully and conservatively, preserving the original structure and formatting while adding the requested clarifications, models, experiments, limitations, and citations. All newly added or substantially revised text is marked in red in the revised manuscript. Newly added or revised paragraphs are set in 10 pt, justified, and the added mathematics is written in proper Word equation notation. The displayed equations were renumbered sequentially by order of appearance (now numbered 1–11), and all in-text equation references were updated. We also removed the previously uncited carbon-comparison figures (former Figures 4–6) and renumbered the new figures; the new figures are now Figures 4–7 and are provided both as captioned placement markers in the manuscript and as separate image files.

Below we respond to each comment in turn.

---

## Reviewer 1

### Reviewer 1, Major Comment 1

**Comment:** PoW energy consumption is misrepresented because the model omits cryptocurrency price and reward properties; a rational miner spends on electricity up to the expected reward, so PoW energy is highly price-dependent.

**Response:** We agree that the earlier version did not sufficiently account for the economic drivers of PoW energy consumption. The revised manuscript now clarifies that PoW energy depends on the expected mining reward, the cryptocurrency price, the block subsidy, transaction fees, the electricity price, mining efficiency, and difficulty/hashrate assumptions, rather than on the number of miners alone. We added an explicit PoW economic energy model and present its outputs as scenario-based, not as exact real-world measurements.

**Revision made:** We added the subsection "D. Proof-of-Work Economic Energy Model," which introduces the expected per-block reward in fiat, R_t = (B_t + F_t)·P_t (Eq. 5); the economic electricity budget, E_budget,t = κ·R_t / C_elec,t (Eq. 6); and the per-miner allocation, E_i,t = s_i,t·E_PoW,t (Eq. 7), together with an optional technical bound derived from difficulty and per-hash efficiency. A red clarification was also added in the Introduction, and the Results report that the modelled network energy is governed by these economic terms and scales with coin price while remaining essentially invariant to the miner count.

**Location in revised manuscript:** Introduction; Energy Consumption Modeling Extension, subsection "D. Proof-of-Work Economic Energy Model" (Eqs. 5–7); Results and Analysis, subsection "A. Energy Consumption Analysis" (Figure 4).

### Reviewer 1, Major Comment 2

**Comment:** Ethereum has not run PoW for a long time; the De Vries (Patterns) paper should be cited.

**Response:** We corrected all wording that could imply Ethereum currently runs PoW. Ethereum is now described as a Proof-of-Stake system after The Merge (September 2022). Any remaining Ethereum PoW discussion is explicitly labelled as a historical Ethereum-like PoW configuration that does not represent current Ethereum. We added the De Vries (Patterns) reference and cite it in the text as [21].

**Revision made:** We updated the Abstract, Introduction, the Experimental Setup, and the Results so that Ethereum is presented as post-Merge PoS, and we relabelled the former "Ethereum (Model 2)" as a historical Ethereum-like PoW configuration. Reference [21] (De Vries, "Cryptocurrencies on the Road to Sustainability: Ethereum Paving the Way for Bitcoin," Patterns, DOI 10.1016/j.patter.2022.100633) was added to the reference list and cited in the text.

**Location in revised manuscript:** Introduction (paragraph beginning "It is important to clarify the energy characteristics…", where [21] is cited in the Merge discussion); Background and Related Work, subsection "Energy, Permissionlessness, and Sybil Resistance" ([21] cited); Experimental Setup, subsection "B. Consensus and Workload Parameters" (historical Ethereum-like PoW configuration); Results and Analysis, subsection "A. Energy Consumption Analysis" ([21] cited); References [21].

### Reviewer 1, Major Comment 3

**Comment:** PoW and PoS should be modelled as two distinct energy-consumption models.

**Response:** We separated the two consensus families into distinct energy models. PoW is modelled from economic reward, price, electricity price, and mining assumptions, while PoS is modelled from validator count, per-validator power draw, uptime, and communication energy.

**Revision made:** We added the subsection "D. Proof-of-Work Economic Energy Model" (Eqs. 5–7) and the subsection "E. Proof-of-Stake Validator Energy Model," which defines E_PoS = (Σ_{v=1}^{V} P_v·T·u_v)/1000 + E_comm (Eq. 8). We report PoW results in Figure 4 and PoS results in Figure 5, and we cite Sedlmeir et al. [16] and Platt et al. [19].

**Location in revised manuscript:** Energy Consumption Modeling Extension, subsections "D. Proof-of-Work Economic Energy Model" (Eqs. 5–7) and "E. Proof-of-Stake Validator Energy Model" (Eq. 8); Results and Analysis, subsection "A. Energy Consumption Analysis" (Figures 4 and 5).

### Reviewer 1, Minor Comment 4

**Comment:** The paper needs a clearer introduction to PoW versus PoS, permissionlessness, Sybil resistance, and the cost/freeness of participation.

**Response:** We added a dedicated discussion of energy consumption, permissionlessness, Sybil resistance, and the cost of participation. We clarify that PoW achieves Sybil resistance through external resource expenditure (computation and therefore electricity), so it is not "free," whereas PoS shifts the cost model toward validator participation and stake. We cite Sedlmeir et al., Platt et al. (2021), Platt, Platt & McBurney (2024), and De Vries.

**Revision made:** We added the subsection "Energy, Permissionlessness, and Sybil Resistance," which contrasts the Sybil-resistance mechanisms of PoW and PoS, discusses the Sybil-attack vulnerability trilemma, and explains why PoW security depends on costly external resources while PoS relies on validator/stake participation. It cites [16], [19], [20], and [21].

**Location in revised manuscript:** Background and Related Work, subsection "Energy, Permissionlessness, and Sybil Resistance."

---

## Reviewer 2

### Reviewer 2, model-limitation comment

**Comment:** The model is limited and should be positioned for preliminary, scenario-based evaluation; the gap with real-world scenarios should be clarified, and the limitations strengthened.

**Response:** We clarified that the framework is intended for preliminary, scenario-based sustainability evaluation. We do not claim field-level validation or precise real-world prediction, and we strengthened the limitations discussion accordingly.

**Revision made:** We added red statements in the Abstract and Results that the absolute energy and carbon values are scenario-based model outputs rather than measurements, and we expanded the limitations with explicit points on the sensitivity of PoW energy to market and hardware assumptions, the sensitivity of PoS energy to validator hardware and uptime, the dependence of carbon on regional grids, and the discrete-event abstraction.

**Location in revised manuscript:** Abstract; Results and Analysis, subsection "A. Energy Consumption Analysis"; Discussion and Threats to Validity, subsection "B. Threats to Validity."

### Reviewer 2, emission-factor (γ) comment

**Comment:** The emission factor γ is configurable but never varied; a sensitivity analysis is needed because the same energy yields different emissions across grids.

**Response:** We added a carbon-emission-factor sensitivity analysis. The revised manuscript now discusses how different grid carbon intensities produce very different emissions for the same energy consumption, and reports results for low, average, and high grids.

**Revision made:** We added a red paragraph defining the low/average/high γ scenarios in the carbon model, and a γ-sensitivity analysis with a new figure showing carbon under the three emission factors.

**Location in revised manuscript:** Carbon Footprint Modeling, subsection "A. Carbon Emission Model"; Results and Analysis, subsection "B. Carbon Footprint Analysis" (Figure 7).

### Reviewer 2, mining-difficulty / dynamics comment

**Comment:** The energy model ignores mining difficulty and the way the cryptographic problem's difficulty varies over time.

**Response:** We added difficulty and hashrate as explicit parameters/hooks in the PoW model, and we clarified the limitation that the simulator remains scenario-based and does not claim full real-world mining-market calibration.

**Revision made:** In the PoW economic model we introduced the expected hashes per block H_block = D·2^32 and the per-hash efficiency ε_hash as part of the technical bound, and the supporting code exposes difficulty, network hashrate, and an optional difficulty-retargeting routine. The limitations note that these are scenario inputs rather than a calibrated market model.

**Location in revised manuscript:** Energy Consumption Modeling Extension, subsection "D. Proof-of-Work Economic Energy Model"; Discussion and Threats to Validity, subsection "B. Threats to Validity."

### Reviewer 2, preliminary-experiments / statistics comment

**Comment:** The experiments are preliminary; no seed count, standard deviation, or confidence interval is reported, and some quantities take different values across text and figures; "replicated several times" is vague.

**Response:** We strengthened the statistical reporting. Each scenario is now run with 30 random seeds, and we report the mean, standard deviation, and 95% confidence interval. We replaced the vague phrase "replicated several times," and we verified consistency between the text, the figures, and the generated outputs.

**Revision made:** We replaced the methodology text with a red description of the 30-seed protocol (seeds generated as base + i) and mean/standard-deviation/95% confidence-interval reporting, and the new figures display 95% confidence intervals. As an analytical sanity check we also confirm that fixed-power configurations reproduce E = P·T; we do not claim field validation.

**Location in revised manuscript:** Experimental Setup, subsection "D. Evaluation Metrics and Methodology"; Results and Analysis, subsection "A. Energy Consumption Analysis"; new Figures 4–7.

### Reviewer 2, figure-quality comment

**Comment:** Figures are not informative and are sometimes misleading; values of very different magnitude are placed on a single linear axis, and side-by-side panels use different y-scales.

**Response:** We reorganized the figures. We removed the previously uncited carbon-comparison plots (former Figures 4–6), kept Figures 1–3 unchanged, and added clearer figures with error bars and logarithmic or separate axes to avoid compressing disparate magnitudes onto one linear scale. The new figures were renumbered sequentially.

**Revision made:** The new figures are: Figure 4 — PoW energy versus number of miners (economic model; 30 seeds, 95% CI); Figure 5 — PoS total energy versus validator count for three hardware classes (30 seeds, 95% CI); Figure 6 — computation versus communication energy (log–log); and Figure 7 — carbon emissions under low/average/high grid emission factors. Each is cited in the text near its placement marker, and the separate image files are named accordingly.

**Location in revised manuscript:** Results and Analysis, subsections "A. Energy Consumption Analysis" (Figures 4–6) and "B. Carbon Footprint Analysis" (Figure 7).

### Reviewer 2, communication-energy comment

**Comment:** The communication-energy model is defined but never used or analysed.

**Response:** The communication-energy model is now discussed and analysed. We added an analysis of communication energy as a function of transaction rate, block size, and peer connectivity, and a figure comparing computational/consensus energy with communication energy. We note that communication energy can be negligible compared with PoW mining energy but becomes relevant in PoS and high-throughput scenarios.

**Revision made:** We added a red pointer in the communication-energy model description and a red analysis paragraph in the Results, reported separately from consensus energy, with Figure 6 comparing computation and communication energy.

**Location in revised manuscript:** Energy Consumption Modeling Extension, subsection "B. Communication Energy Model"; Results and Analysis, subsection "A. Energy Consumption Analysis" (Figure 6).

### Reviewer 2, "validated" wording

**Comment:** The framework is described as "validated," but no validation is performed.

**Response:** We do not describe the framework as validated. We use the terms "analytical sanity check" and "scenario-based evaluation," and we make no claim of validation against field measurements.

**Revision made:** The Results report an analytical sanity check confirming that fixed-power configurations reproduce E = P·T, and the limitations restate that the tool is a scenario-based explorer rather than a precise estimator.

**Location in revised manuscript:** Results and Analysis, subsection "A. Energy Consumption Analysis"; Discussion and Threats to Validity, subsection "B. Threats to Validity."

---

## New references added

- [19] M. Platt et al., "The Energy Footprint of Blockchain Consensus Mechanisms Beyond Proof-of-Work," IEEE QRS-C, 2021 (DOI 10.1109/QRS-C55045.2021.00168).
- [20] M. Platt, D. Platt, and P. McBurney, "Sybil attack vulnerability trilemma," Int. J. of Parallel, Emergent and Distributed Systems, 2024 (DOI 10.1080/17445760.2024.2352740).
- [21] A. de Vries, "Cryptocurrencies on the Road to Sustainability: Ethereum Paving the Way for Bitcoin," Patterns, 2022/2023 (DOI 10.1016/j.patter.2022.100633).

Sedlmeir et al. (2020) was already in the reference list as [16] and is now cited in the new discussion.

We hope these revisions meet the reviewers' expectations, and we thank them again for their careful and constructive feedback.
