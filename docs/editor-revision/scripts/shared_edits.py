"""Single source of truth for the editor revision + final QC pass.
Consumed by edit_manuscript.py (clean red), edit_stage2.py (figures/table),
and tracked_build.py (tracked). Guarantees clean and tracked cannot diverge."""

# Full-paragraph rewrites: {ORIGINAL paragraph index: new_text}
REWRITES = {
 # Experimental Setup B (shortened per QC item 7)
 93: ("The primary evaluation uses the economic Proof-of-Work model (Section D; "
      "600 s block interval) and the validator-count Proof-of-Stake model "
      "(Section E), with Poisson transaction workloads [4], [17]. Miner counts "
      "{50, 100, 500, 1000} and validator counts {100, 500, 1000, 5000} are swept "
      "over a fixed 24-hour horizon, together with sweeps of coin price, block "
      "reward, and electricity price for PoW and hardware class and uptime for "
      "PoS. Table 1 lists all parameters."),
 # Experimental Setup C (shortened per QC item 7)
 96: ("PoW energy is computed from the economic model (Eqs. 5-7) and PoS energy "
      "from the validator-count model (Eq. 8); carbon uses the emission factor γ "
      "across low, average, and high grids (see Results), following [3]."),
 # Results opening
 101:("The simulation results demonstrate that integrating energy and "
      "carbon-footprint modelling into BlockSim enables meaningful sustainability "
      "analysis while preserving the simulator's original performance-evaluation "
      "capabilities. The consensus-aware models make the distinct energy drivers of "
      "each family explicit: Proof-of-Work energy is governed by mining economics, "
      "whereas Proof-of-Stake energy is governed by validator count and hardware "
      "power, as detailed below."),
 # Economic PoW lead
 107:("Under the economically driven Proof-of-Work model (Section D), total network "
      "energy is governed by mining economics rather than by the number of miners. "
      "Holding the economic inputs fixed over a 24-hour horizon, the PoW network "
      "total is approximately 467.5 GWh and is essentially invariant across "
      "50-1000 miners (95% CI ± 17.1 GWh), while the mean per-miner energy "
      "falls approximately as 1/N."),
 # Economic PoW continuation (shortened; removed repetition per QC item 6)
 108:("Network energy scales linearly with coin price - from 155.8 GWh at "
      "20,000 USD/coin to 779.1 GWh at 100,000 USD/coin - and inversely with "
      "electricity price, confirming the economic argument of Section D. Increasing "
      "the miner count redistributes this economically bounded budget rather than "
      "enlarging it. These magnitudes are scenario-based model outputs, not "
      "measurements of any specific cryptocurrency (Figure 1)."),
 # Results §A closing
 115:("Overall, these results reinforce that, in the economically driven regime, "
      "aggregate Proof-of-Work energy is bounded by mining economics - responding "
      "to coin price, block reward, and electricity price rather than to the raw "
      "number of miners - while per-miner energy falls as 1/N. Skewed hashpower "
      "distributions (not shown) redistribute this bounded budget toward dominant "
      "miners without increasing the network total [8]."),
 # Carbon lead
 117:("Because emissions are computed directly from electricity use via the "
      "emission-factor relation C = E·γ (Eq. 9), the carbon results "
      "inherit the energy behaviour: Proof-of-Work emissions are governed by mining "
      "economics and Proof-of-Stake emissions by validator count. For a given "
      "energy level, the dominant driver of carbon is the grid emission factor."),
 # Discussion (shortened per QC item 6)
 129:("A key methodological point is that Proof-of-Work energy depends on how "
      "mining power is modelled. A naïve fixed-power baseline, assigning a constant "
      "wattage per miner, makes total power grow with miner count - the intuitive "
      "but misleading picture the economic model corrects, since rational miners "
      "collectively spend only up to the fiat value of the block reward. We "
      "therefore report PoW energy through the economic model (Section D; "
      "Figure 1) and use the fixed-power picture only as a labelled contrast, not "
      "a network-level estimate."),
 # Threats to Validity
 134:("Although the analysis evaluates three discrete emission-factor scenarios "
      "(low, average, and high grids), these values do not capture the full "
      "temporal and geographical variability of electricity-grid carbon intensity, "
      "nor do they represent real-time or marginal grid emissions. The resulting "
      "carbon estimates should therefore be interpreted as scenario-based "
      "comparisons rather than location-specific operational measurements."),
}

DELETES = [102, 104, 105, 106, 111, 112, 113, 118, 119, 120]
CLEAR_TEXT = [114]

SURGICAL = [
 (109, "Figure 5", "Figure 2"),
 (110, "Figure 6", "Figure 3"),
 (121, "Figure 7", "Figure 4"),
 (130, "predictable scaling in relation to network size and workload intensity",
       "predictable scaling in relation to the economic and hardware drivers of "
       "each consensus mechanism and to workload intensity"),
 (141, "scale predictably with network size, workload intensity, and consensus configuration",
       "scale predictably with the economic and hardware drivers of each consensus "
       "mechanism, workload intensity, and grid carbon intensity"),
]

PREFIX_DELETE = [
 (195, "[21] "),
 (185, "] "),
]

# Reference mechanical fixes (QC item 8). DOIs are hyperlinks; the stray
# punctuation / prefixes are in their own runs, so we operate per-run.
REF_TRAILING_PUNCT = [173, 188]        # delete stray trailing ' ' and '.' runs after DOI
REF_REPLACE_RUN = [(181, "Website:", "Available: ")]  # 'Website:' run -> 'Available: '

# ---- Consolidated parameter table (QC item 3: provenance made explicit) ----
TABLE_HEADER = ["Parameter", "Symbol", "Value / range", "Unit",
                "Model / scenario", "Type", "Source / justification"]
TABLE_ROWS = [
 ["Block subsidy", "B_t", "3.125 (swept 1.5625 / 3.125 / 6.25)", "coin/block", "PoW economic", "Input (swept)", "scenarios.py POW_BITCOIN_BASE (post-2024-halving assumption)"],
 ["Avg. transaction fees", "F_t", "0.30 (Gaussian σ=40% per seed)", "coin/block", "PoW economic", "Stochastic", "scenarios.py fee_jitter=0.40 (assumption)"],
 ["Coin price", "P_t", "60,000 (swept 20,000 / 60,000 / 100,000; Gaussian σ=5% per seed)", "USD/coin", "PoW economic", "Swept + stochastic", "scenarios.py price_jitter=0.05 (assumption)"],
 ["Electricity price", "C_elec", "0.05 (swept 0.03 / 0.05 / 0.10)", "USD/kWh", "PoW economic", "Input (swept)", "run_pow_price_sensitivity.py (industrial-mining assumption)"],
 ["Electricity-spend ratio", "κ", "0.80", "-", "PoW economic", "Deterministic input", "scenarios.py (assumption, κ ∈ [0,1])"],
 ["Mining efficiency", "-", "21.5", "J/TH", "PoW economic (technical bound)", "Deterministic input", "scenarios.py (ASIC-class anchor, assumption)"],
 ["Block interval (PoW)", "-", "600", "s", "PoW economic", "Deterministic input", "scenarios.py (~10-min target, assumption)"],
 ["Miner count", "N", "50; 100; 500; 1000", "miners", "PoW economic", "Swept", "run_pow_miner_scaling.py; small-to-moderate networks [6]"],
 ["Blocks in horizon", "-", "Poisson(T / block interval)", "blocks", "PoW economic", "Stochastic", "scenarios.py _poisson"],
 ["Hashpower shares", "s_i", "Dirichlet(1,…,1)", "-", "PoW economic", "Stochastic", "scenarios.py _dirichlet_ones"],
 ["Per-miner power (fixed-power contrast baseline)", "P_miner", "2500 (illustrative)", "W", "Naïve fixed-power baseline", "Illustrative assumption", "Prior §C text; contrast only, not used for network-level estimates"],
 ["Validator power", "P_v", "10 / 100 / 500 (low / standard / high; Gaussian σ=10% per seed)", "W", "PoS validator", "Swept + stochastic", "scenarios.py POS_VALIDATOR_POWER; power_jitter=0.10"],
 ["Validator uptime", "u_v", "0.99 (swept 0.90 / 0.99 / 1.00; Gaussian σ=1% per seed)", "-", "PoS validator", "Swept + stochastic", "scenarios.py uptime_jitter=0.01 (assumption)"],
 ["Validator count", "V", "100; 500; 1000; 5000", "validators", "PoS validator", "Swept", "run_pos_validator_scaling.py"],
 ["Validator gossip message rate", "-", "5", "msg/validator/s", "PoS validator", "Deterministic input", "scenarios.py msg_rate_per_validator_hz=5 (assumption)"],
 ["Peer degree", "-", "4; 8; 16", "peers", "Communication", "Swept", "run_communication_energy_analysis.py"],
 ["Block size", "-", "0.5; 1; 2", "MB", "Communication", "Swept", "run_communication_energy_analysis.py"],
 ["Transaction rate", "-", "1; 10; 100", "tx/s", "Communication", "Swept", "run_communication_energy_analysis.py"],
 ["Transaction size", "-", "512", "bytes", "Communication", "Deterministic input", "run_communication_energy_analysis.py (assumption)"],
 ["TX / RX energy per message", "e_tx / e_rx", "0.10 / 0.05", "J/msg", "Communication", "Deterministic input", "run_communication_energy_analysis.py; radio/NIC order-of-magnitude [11]"],
 ["TX / RX energy per byte", "-", "2×10⁻⁶ / 1×10⁻⁶", "J/byte", "Communication", "Deterministic input", "run_communication_energy_analysis.py [11]"],
 ["Nodes (comm. overlay)", "-", "500", "nodes", "Communication", "Deterministic input", "run_communication_energy_analysis.py"],
 ["Grid emission factor", "γ", "0.05 / 0.475 / 0.82 (low / average / high)", "kgCO₂e/kWh", "Carbon", "Swept", "scenarios.py GAMMA_SCENARIOS; IEA/IPCC ranges [13], [14]"],
 ["Transactions per block (normalization)", "-", "2000", "tx/block", "Carbon", "Deterministic input", "run_carbon_gamma_sensitivity.py (assumption)"],
 ["Simulation horizon", "T", "86,400 (24 h)", "s", "All models", "Deterministic input", "experiment scripts (common horizon)"],
 ["Random seeds", "-", "30 (20260101-20260130; base + i, i = 0..29)", "-", "All stochastic runs", "-", "_common.py N_SEEDS, SEED_BASE"],
 ["Confidence interval", "-", "95% (Student-t across seeds)", "-", "All stochastic runs", "-", "scenarios.py ci95_halfwidth"],
]
PARAM_LEAD = ("Table 1 consolidates every parameter required to reproduce the "
              "experiments; each value is traceable to the released code or CSV "
              "outputs and is marked as a deterministic input, a swept level, or a "
              "stochastic (seed-varying) quantity.")
PARAM_CAPTION = ("Table 1. Consolidated experimental parameters (all values "
                 "verified against the released code, CSV outputs, and equations).")

# ---- Randomness / CI subsection (QC item 6: shortened) ----
RAND_HEAD = "E. Randomness, Replications, and Confidence-Interval Construction"
RAND_BODY = ("The energy equations (Sections D and E) are deterministic in their "
             "inputs; a fixed-power configuration reproduces E = P·T exactly "
             "(maximum relative error 0.00). The 30-seed confidence intervals arise "
             "solely from scenario inputs that vary across seeds in the released "
             "code (Models/Energy/scenarios.py): for PoW, a Poisson block count and "
             "Gaussian jitter on coin price (σ = 5%) and transaction fees "
             "(σ = 40%), with Dirichlet hashpower shares; for PoS, Gaussian jitter "
             "on per-validator power (σ = 10%) and uptime (σ = 1%). Intervals are "
             "Student-t 95% across the 30 seeds (20260101-20260130); deterministic "
             "quantities are reported as exact values without intervals.")
