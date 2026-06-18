# Response to Reviewers

**Manuscript:** Extending BlockSim with Consensus-Aware Energy and Carbon Footprint Modeling for Sustainable Blockchain Evaluation
**Authors:** Raed S. Rasheed, Aiman A. AbuSamra

We thank both reviewers for their careful and constructive reading. The reviews
identified a fundamental modelling problem (PoW energy was not economically
driven) and several methodological gaps (Ethereum's consensus, γ sensitivity,
difficulty dynamics, statistics, figures, communication energy, and the
unsupported "validated" claim). We have substantially revised both the
manuscript and the BlockSim code. The most important change is that **Proof-of-
Work energy is now an economically driven model in which the expected mining
reward and the cryptocurrency price are explicit input variables**, and
**Proof-of-Work and Proof-of-Stake are now modelled as two distinct energy
processes**.

Below we respond point by point. Section, equation, figure, and table numbers
refer to the revised manuscript. All reported numbers are produced by the
released experiment scripts and are mutually consistent across text, tables, and
figures (single-source generation).

---

## Reviewer 1

### R1.1 (Major, most critical) — PoW energy misrepresented; price/reward missing

> The energy consumption of PoW-based cryptocurrencies is connected to their price and reward properties ... this variable is entirely missing from the model.

**Response:** We agree, and this was the central flaw. We have replaced the
previous miner-count-based PoW model with an **economic energy model** in which
the expected block reward and the coin price are explicit inputs. A rational
miner spends on electricity up to the fiat value of the expected reward, so the
network energy is bounded by economics, not by the number of machines.

**Revision made:** New Section 4.1 (Proof-of-Work Economic Energy Model)
introduces:
- R_t = (B_t + F_t) × P_t — expected block reward in fiat (Eq. 1),
- E_budget,t = κ × R_t / C_elec,t — economic electricity budget (Eq. 2),
- an optional technical bound E_technical (Eq. 3) and E_PoW = min(E_technical, E_budget), with per-miner allocation E_i = s_i × E_PoW (Eq. 4).

We added `PowEconomicEnergyModel` in `Models/Energy/energy_models.py` with inputs
`coin_price`, `block_subsidy`, `avg_tx_fees`, `electricity_price_per_kwh`,
`electricity_spend_ratio_kappa`, and efficiency/difficulty/hashrate hooks.
Experiment `run_pow_price_sensitivity.py` demonstrates the dependence: network
energy rises linearly with coin price (155.8 → 779.1 GWh/day from 20k → 100k USD)
and with block reward, and falls inversely with electricity price. We also show
(Fig. 1, Table 2) that **total PoW energy is invariant to miner count**, while
per-miner energy falls ~1/N — directly correcting the earlier misrepresentation.

**Location in manuscript:** Section 4.1 (Eqs. 1–4); Section 7.1 (Fig. 1, Table 2);
Section 7.2 (Fig. 2, Table 3); Introduction paragraphs 2–4.

---

### R1.2 (Major) — Ethereum has not run PoW for a long time; cite De Vries 2022

**Response:** Corrected throughout. We no longer present Ethereum as a PoW
chain. We state that Ethereum moved to PoS at The Merge (September 2022), reduced
consensus energy by ~99.95%, and we cite De Vries (2022, *Patterns*).

**Revision made:** Introduction (paragraph 3) and Section 2.3 now state the Merge
explicitly and add the De Vries *Patterns* reference [8]. Any pre-Merge PoW
Ethereum configuration is relabelled "historical Ethereum-like PoW
configuration" and flagged in the limitations (Section 8.2, item 5). The current
Ethereum scenario is modelled with the validator-count PoS model (Section 4.2,
Section 7.3).

**Location in manuscript:** Introduction ¶3; Section 2.3; Section 8.2 item 5;
Reference [8].

---

### R1.3 (Major) — Model PoW and PoS as two distinct energy models

> a. PoW: expected reward (price-dependent) must be an input — cf. Sedlmeir et al. 2020.
> b. PoS: only validator count counts — cf. Platt et al. 2021.

**Response:** Done. The single generic model is replaced by two consensus-aware
models.

**Revision made:**
- **PoW (4.1):** economic model above; cites Sedlmeir et al. [4].
- **PoS (4.2):** `PosValidatorEnergyModel` implementing
  E_PoS = Σ_v (P_v × T × u_v / 1000) + E_comm (Eq. 5), driven by validator count,
  hardware power, uptime, and communication overhead; cites Platt et al. [6].
  Experiment `run_pos_validator_scaling.py` sweeps validator counts
  {100, 500, 1000, 5000} across three hardware classes (Fig. 3, Table 4). The PoS
  model has no coin-price input by construction.

**Location in manuscript:** Sections 4.1 and 4.2; Sections 7.1–7.3; References
[4], [6].

---

### R1.4 (Minor) — Introduce energy properties of consensus mechanisms; permissionlessness, Sybil resistance, freeness; cite Platt, Platt & McBurney 2024

**Response:** Added a dedicated subsection.

**Revision made:** New Section 2.3 ("Energy Consumption, Permissionlessness, and
Sybil Resistance") explains that PoW achieves Sybil resistance via external,
costly resource expenditure (and is therefore not "free"), whereas PoS uses
stake; it discusses the Sybil-attack vulnerability trilemma and cites Platt,
Platt & McBurney (2024) [15], Sedlmeir et al. [4], Platt et al. [6], and De Vries
[8].

**Location in manuscript:** Section 2.3; References [4], [6], [8], [15].

---

## Reviewer 2

### R2.A — Title, abstract, contribution; remove overclaims; position as scenario tool; keywords

**Response & revision made:**
1. **Title** changed to "Extending BlockSim with **Consensus-Aware** Energy and
   Carbon Footprint Modeling for Sustainable Blockchain Evaluation."
2. **Abstract** rewritten to state that PoW energy is economically driven and PoS
   energy is validator-count driven.
3. The word "**validated**" is removed; we now say the framework is "evaluated
   through controlled scenario-based simulations" and report only the sanity
   checks we actually implemented.
4. The tool is explicitly positioned as a **scenario-based explorer, not a
   precise real-world estimator** (Abstract; Introduction ¶ final; Section 8.2).
5. **Keywords** updated to include PoW, PoS, Carbon Footprint, Blockchain
   Simulation, Energy Modeling.

**Location:** Title; Abstract; Keywords; Section 8.2.

---

### R2.B — Stronger introduction and PoW/PoS comparison; correct Ethereum

**Response & revision made:** Introduction now explains the economic drivers of
PoW energy (subsidy, fees, coin price, electricity price, efficiency,
difficulty/hashrate). Section 2.3 contrasts PoW and PoS on Sybil resistance and
freeness. All statements implying Ethereum runs PoW are corrected (see R1.2).

**Location:** Introduction ¶2–4; Sections 2.2–2.3.

---

### R2.C — Replace single generic model with separate PoW/PoS; add comm and carbon models

**Response & revision made:** New Section 4 "Consensus-Aware Energy Consumption
Models" with subsections 4.1 PoW economic, 4.2 PoS validator, 4.3 communication,
4.4 carbon, matching the requested equations (Eqs. 1–7). Difficulty/hashrate
parameters and an optional retargeting routine are included (Section 4.1; code
`retarget_difficulty`).

**Location:** Section 4 (all subsections); Eqs. 1–7.

---

### R2.D — Ethereum correction

**Response & revision made:** See R1.2. Ethereum is presented as PoS; any PoW
Ethereum is labelled historical; De Vries [8] added; The Merge stated.

**Location:** Introduction ¶3; Sections 2.3, 7.3; Section 8.2 item 5.

---

### R2.E — Carbon model and γ sensitivity

**Response & revision made:** The carbon model C = E × γ is retained (Eq. 7) and
γ is now varied experimentally across **low (0.05), average (0.475), and high
(0.82) kgCO₂e/kWh** grids (`run_carbon_gamma_sensitivity.py`). New Figure 4
("Carbon emissions under different electricity emission factors") and Table 5
report total, per-block, and per-transaction carbon. We discuss that identical
energy maps to a ~16× range of carbon depending on grid (Section 7.4).

**Location:** Section 4.4; Section 7.4 (Fig. 4, Table 5).

---

### R2.F — Communication-energy model defined but not analyzed

**Response & revision made:** The communication model is now instrumented and
analyzed. `CommunicationEnergyModel` counts transmitted/received block and
transaction messages and bytes (Eq. 6). `run_communication_energy_analysis.py`
varies transaction rate (1/10/100 tx/s), block size (0.5/1/2 MB), and peer degree
(4/8/16). Figure 5 and Table 6 report communication energy separately from
consensus energy. We show it is negligible versus PoW (ratio ~3×10⁻⁶) but
comparable to PoS consensus energy at 100 tx/s (~1,455 vs ~2,387 kWh/day), so it
matters in PoS/high-throughput settings (Section 7.5).

**Location:** Section 4.3; Section 7.5 (Fig. 5, Table 6); Section 8.2 item 6.

---

### R2.G — Experimental design, statistics, reproducibility table

**Response & revision made:** Experiments expanded to PoW miner scaling, PoW
economic sensitivity (price, reward, electricity), PoS validator/hardware/uptime
scaling, carbon γ sensitivity, and communication analysis. Each scenario is run
with **30 random seeds** (seeds 20260101–20260130, generated as base + i) and
reported with **mean, standard deviation, and 95% confidence interval** (Student
t). A **reproducibility table** (Table 1) lists horizon, block interval, seed
count, miner/validator counts, reward/price/electricity assumptions, γ values,
and efficiency assumptions. Carbon is reported per block and per transaction
(Table 5).

**Location:** Section 6 (Table 1); Sections 7.1–7.5 (Tables 2–6).

---

### R2 (figures) — Figures uninformative / visually misleading

**Response & revision made:** The previous overlay figures (Bitcoin compressed to
a flat line; mismatched y-axes) are removed. New figures follow the requested
rules:
- **Fig. 1** PoW energy vs miners with error bars (two panels: invariant total;
  1/N per-miner on log axis).
- **Fig. 2** PoW energy vs coin price with error bars.
- **Fig. 3** PoS energy vs validator count with error bars (three hardware
  classes).
- **Fig. 4** Carbon vs γ (log axis, avoids compressing PoS against PoW).
- **Fig. 5** Computation vs communication energy (log-log).
- **Fig. 6** PoW vs PoS orders-of-magnitude comparison (log axis).

We use log axes or separate panels wherever magnitudes differ by orders of
magnitude, never placing disparate linear values on one axis. Captions and
numbering are corrected, and every figure is paired with a numerical table.

**Location:** Figures 1–6 and Tables 2–7.

---

### R2 (validation) — "Validated" without validation; inconsistent values

**Response & revision made:** We removed the "validated" claim. Instead Section
7.6 reports (i) an **analytical sanity check** confirming the simulator
reproduces E = P × T to machine precision (Table 7; max relative error 0.00) and
(ii) a **literature-order check** showing the PoW/PoS energy gap (~197,000×) is
consistent with Sedlmeir et al. [4], Platt et al. [6], and the ~99.95% Merge
reduction [8]. All numbers are generated from a single pipeline so text, tables,
and figures match exactly; the earlier inconsistent Ethereum-at-1000-miners
values no longer appear.

**Location:** Abstract; Section 7.6 (Table 7, Fig. 6); Section 8.

---

### R2 (limitations) — Strengthen threats to validity

**Response & revision made:** Section 8.2 now enumerates seven explicit
limitations: scenario-based (not predictive); PoW sensitivity to price/reward/
fees/electricity/efficiency/difficulty; PoS sensitivity to validator count/
hardware/uptime/redundancy/communication; carbon dependence on regional/temporal
grid mix; historical-Ethereum caveat; communication energy caveat; and the
discrete-event abstraction caveat.

**Location:** Section 8.2 (items 1–7).

---

## Summary of new references added
[4] Sedlmeir et al. 2020; [6] Platt et al. 2021 (QRS-C); [7] Nguyen et al. 2019
(PoS); [8] De Vries 2022 (Patterns); [15] Platt, Platt & McBurney 2024 (Sybil
trilemma). The reference list was de-duplicated and reformatted consistently.

We believe the revision addresses every point raised and significantly improves
the contribution. We thank the reviewers again for their guidance.
