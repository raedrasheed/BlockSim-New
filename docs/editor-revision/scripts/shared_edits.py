"""Shared revised texts and change specs used by BOTH the clean-red and the
tracked builders, so the two deliverables cannot diverge."""

# Full-paragraph rewrites: {paragraph_index: new_text}
REWRITES = {
 93: ("The primary evaluation uses the economically driven Proof-of-Work model "
      "(Section D) with a ten-minute (600 s) target block interval, together with "
      "the validator-count Proof-of-Stake model (Section E). Transaction workloads "
      "are modelled as a Poisson process, a common assumption in blockchain "
      "performance studies [4], [17]. To assess scaling behaviour, the miner "
      "population is varied over {50, 100, 500, 1000} and the validator population "
      "over {100, 500, 1000, 5000} while the simulation horizon is held fixed at "
      "24 hours; additional sensitivity sweeps vary the coin price, block reward, "
      "and electricity price for PoW and the hardware class and uptime for PoS. All "
      "parameter values are consolidated in Table 1."),
 96: ("Energy consumption is computed at runtime from the consensus-aware models: "
      "Proof-of-Work energy from the economic model (Eqs. 5-7), driven by the block "
      "reward, coin price, electricity price, hardware efficiency, and the "
      "electricity-spend ratio κ, and Proof-of-Stake energy from the "
      "validator-count model (Eq. 8). Carbon emissions are computed with the "
      "configurable emission factor γ, varied across low, average, and high "
      "grid scenarios (see Results) rather than held fixed, following established "
      "blockchain carbon-footprint analyses [3]. Concretely, carbon is derived via "
      "the standard emission-factor formulation (electricity use × emission "
      "factor), consistent with common GHG accounting practice."),
 101:("The simulation results demonstrate that integrating energy and "
      "carbon-footprint modelling into BlockSim enables meaningful sustainability "
      "analysis while preserving the simulator's original performance-evaluation "
      "capabilities. The consensus-aware models make the distinct energy drivers of "
      "each family explicit: Proof-of-Work energy is governed by mining economics, "
      "whereas Proof-of-Stake energy is governed by validator count and hardware "
      "power, as detailed below."),
 107:("Under the economically driven Proof-of-Work model (Section D), total network "
      "energy is governed by mining economics rather than by the number of miners. "
      "Holding the economic inputs fixed over a 24-hour horizon, the PoW network "
      "total is approximately 467.5 GWh and is essentially invariant across "
      "50-1000 miners (95% CI ± 17.1 GWh), while the mean per-miner energy "
      "falls approximately as 1/N."),
 108:("Network energy scales linearly with coin price, rising from 155.8 GWh at "
      "20,000 USD/coin to 779.1 GWh at 100,000 USD/coin, and inversely with "
      "electricity price, confirming the economic argument of Section D. Increasing "
      "the number of participating miners therefore redistributes a fixed, "
      "economically bounded energy budget rather than increasing it, correcting the "
      "common misconception that Proof-of-Work energy grows with the raw miner "
      "count. These absolute magnitudes are scenario-based model outputs for the "
      "chosen economic assumptions, not real-world measurements of any specific "
      "cryptocurrency. Figure 1 summarizes the sensitivity of PoW network energy to "
      "the number of miners: the network total is invariant to miner count, while "
      "the mean per-miner energy falls approximately as 1/N."),
 115:("Overall, these results reinforce that, in the economically driven regime, "
      "aggregate Proof-of-Work energy is bounded by mining economics - responding "
      "to coin price, block reward, and electricity price rather than to the raw "
      "number of miners - while per-miner energy falls as 1/N. Skewed hashpower "
      "distributions (not shown) redistribute this bounded budget toward dominant "
      "miners without increasing the network total [8]."),
 117:("Because emissions are computed directly from electricity use via the "
      "emission-factor relation C = E·γ (Eq. 9), the carbon results "
      "inherit the energy behaviour: Proof-of-Work emissions are governed by mining "
      "economics and Proof-of-Stake emissions by validator count. For a given "
      "energy level, the dominant driver of carbon is the grid emission factor."),
 129:("A key methodological observation is that Proof-of-Work energy and CO₂ "
      "outcomes depend critically on how mining power is modelled. A naïve "
      "fixed-power baseline that assigns a constant wattage to every miner makes "
      "total network power scale directly with miner count; this is the intuitive "
      "but misleading picture that motivated the economic model, because it "
      "conflates a growing mining industry (more miners ⇒ more total watts) "
      "with the economically constrained reality in which rational miners "
      "collectively spend only up to the fiat value of the block reward. The "
      "economic Proof-of-Work model adopted here instead makes total network energy "
      "invariant to miner count and driven by coin price, reward, and electricity "
      "price (Section D; Figure 1). We therefore report PoW energy through the "
      "economic model and treat the fixed-power, per-miner picture only as a "
      "conceptual contrast, not as a network-level estimate."),
 134:("Although the analysis evaluates three discrete emission-factor scenarios "
      "(low, average, and high grids), these values do not capture the full "
      "temporal and geographical variability of electricity-grid carbon intensity, "
      "nor do they represent real-time or marginal grid emissions. The resulting "
      "carbon estimates should therefore be interpreted as scenario-based "
      "comparisons rather than location-specific operational measurements."),
}

# Whole-paragraph deletions (index in ORIGINAL)
DELETES = [102, 104, 105, 106, 111, 112, 113, 118, 119, 120]

# Paragraph whose TEXT is cleared but drawing kept (renumbered Fig 3 anchor)
CLEAR_TEXT = [114]

# Surgical single-token replacements: [(para_index, old, new), ...]
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

# Deletions of stray prefixes in references
PREFIX_DELETE = [
 (195, "[21] "),   # remove manually-typed duplicate number (Word auto-numbers)
 (185, "] "),       # remove stray bracket
]
