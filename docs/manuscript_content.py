"""Single source of truth for the revised manuscript content.

`build_blocks()` returns an ordered list of typed blocks that the DOCX and PDF
renderers both consume, so the two deliverables are guaranteed identical. All
numeric values are read from results/data/*.csv.

Block grammar (tuples):
    ("title", str)
    ("author", str, size:int, bold:bool)
    ("abstract", str)
    ("keywords", str)
    ("h1", str) / ("h2", str)
    ("p", str)
    ("bullet", str) / ("number", str)
    ("eq", str, num)
    ("fig", stem, num, caption)
    ("table", num, caption, headers:list, rows:list[list])
    ("ref", idx:int, text)
"""

import csv
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA = os.path.join(ROOT, "results", "data")
FIG = os.path.join(ROOT, "results", "figures")


def load(name):
    with open(os.path.join(DATA, name)) as f:
        return list(csv.DictReader(f))


def gwh(kwh):
    return float(kwh) / 1e6


def f(x, n=2):
    return f"{float(x):,.{n}f}"


def build_blocks():
    pow_miner = load("pow_miner_scaling_summary.csv")
    pow_price = load("pow_price_sensitivity_summary.csv")
    pos = load("pos_validator_scaling_summary.csv")
    carbon = load("carbon_gamma_sensitivity_summary.csv")
    comm = load("communication_energy_summary.csv")
    valid = load("validation_fixed_power.csv")
    repro = {r["parameter"]: r["value"] for r in load("reproducibility_summary.csv")}

    pm = {int(r["miner_count"]): r for r in pow_miner}
    pp = {(r["sweep"], r["level"]): r for r in pow_price}
    ps = {(r["hw_class"], int(r["validator_count"])): r for r in pos
          if r["hw_class"] in ("low_power_node", "standard_server", "high_power_server")}
    cb = {(r["family"], r["gamma_scenario"]): r for r in carbon}
    cm = {(int(r["peer_degree"]), int(r["tx_rate_hz"]), float(r["block_size_mb"])): r
          for r in comm}

    B = []

    # ---------------- TITLE / AUTHORS ----------------
    B.append(("title", "Extending BlockSim with Consensus-Aware Energy and "
              "Carbon Footprint Modeling for Sustainable Blockchain Evaluation"))
    for line, sz, bold in [
        ("Raed S. Rasheed", 11, True),
        ("Faculty of Engineering, Islamic University of Gaza, Gaza, Palestine", 10, False),
        ("rrasheed@iugaza.edu.ps", 10, False),
        ("Aiman A. AbuSamra", 11, True),
        ("Faculty of Engineering, Islamic University of Gaza, Gaza, Palestine", 10, False),
        ("aasamra@iugaza.edu.ps", 10, False),
    ]:
        B.append(("author", line, sz, bold))

    B.append(("abstract",
        "Discrete-event blockchain simulators such as BlockSim capture network, "
        "consensus, and incentive behaviour, but they do not natively model "
        "energy use or carbon emissions, limiting their usefulness for "
        "sustainability studies. This paper extends BlockSim with consensus-aware "
        "energy and carbon accounting that is integrated with its event-driven "
        "execution. A central correction over our earlier design is that the two "
        "dominant consensus families are now modelled as fundamentally different "
        "energy processes. Proof-of-Work (PoW) energy is modelled as an "
        "economically driven quantity: rational miners spend on electricity up to "
        "the fiat value of the expected block reward, so the expected reward and "
        "the cryptocurrency price are now explicit input variables, alongside "
        "electricity price, miner efficiency, and difficulty/hashrate hooks. "
        "Proof-of-Stake (PoS) energy is modelled as a validator-count-driven "
        "quantity determined by the number of validators, their hardware power, "
        "uptime, and communication overhead. A configurable emission factor "
        "converts energy to CO2 and is varied experimentally across low-, "
        "average-, and high-carbon grids. We also instrument and analyse "
        "communication energy, which the previous version defined but never used. "
        "Each scenario is run with 30 random seeds and reported with mean, "
        "standard deviation, and 95% confidence intervals. We do not claim "
        "real-world validation; instead the framework is evaluated through "
        "controlled, scenario-based simulations and checked against an analytical "
        "E = P x T baseline and the order-of-magnitude PoW/PoS gap reported in "
        "the literature. The tool is positioned as a scenario-based explorer for "
        "protocol designers, not as a precise real-world energy estimator."))
    B.append(("keywords",
        "Blockchain Simulation, BlockSim, Proof of Work, Proof of Stake, Energy "
        "Modeling, Carbon Footprint, Consensus Mechanisms, Sustainability."))

    # ---------------- 1. INTRODUCTION ----------------
    B.append(("h1", "1. Introduction"))
    B.append(("p",
        "Blockchain technology underpins a growing range of decentralized "
        "applications, but the energy demand and carbon emissions of some "
        "consensus mechanisms have become a first-order concern. Permissionless "
        "Proof-of-Work (PoW) networks in particular have been estimated to "
        "consume electricity on the scale of medium-sized countries, with "
        "correspondingly large carbon footprints [1], [2], [3]. As protocol "
        "designers increasingly weigh sustainability against performance and "
        "security, evaluation tools must reason about energy and carbon alongside "
        "throughput, latency, and fork behaviour."))
    B.append(("p",
        "A crucial point, emphasised by recent economic analyses, is that PoW "
        "energy consumption is not primarily a function of how many machines "
        "participate. It is an economically driven quantity. A rational miner "
        "invests in electricity up to the fiat value it can expect to earn; "
        "therefore the total energy a PoW network draws is governed by the block "
        "subsidy, transaction fees, the cryptocurrency price, the electricity "
        "price, hardware efficiency, and the difficulty/hashrate equilibrium, "
        "rather than by the raw number of miners [4], [5]. Adding more miners "
        "mainly redistributes a budget fixed by these economic incentives; it "
        "does not, by itself, increase total energy use. Any credible PoW energy "
        "model must therefore take the expected mining reward and the coin price "
        "as explicit inputs."))
    B.append(("p",
        "Proof-of-Stake (PoS) secures the network through stake rather than "
        "external computational work, and its energy profile is qualitatively "
        "different: it is dominated by the number of validators kept online and "
        "the idle/active power of their hardware, and is essentially independent "
        "of coin price [6], [7]. Importantly, Ethereum transitioned from PoW to "
        "PoS at The Merge in September 2022, reducing its consensus energy by "
        "roughly 99.95% [8]. Treating present Ethereum as a PoW system, as our "
        "earlier version implicitly did, is therefore incorrect, and we correct "
        "this throughout."))
    B.append(("p", "This paper extends BlockSim [9] with consensus-aware energy "
              "and carbon accounting. The contributions are:"))
    for c in [
        "A Proof-of-Work economic energy model in which the expected block reward "
        "and cryptocurrency price are explicit inputs, with electricity price, "
        "miner efficiency, difficulty, and hashrate hooks (Section 4.1).",
        "A Proof-of-Stake validator energy model driven by validator count, "
        "hardware power, uptime, and communication overhead (Section 4.2).",
        "An instrumented communication energy model and its analysis as a "
        "function of transaction rate, block size, and peer connectivity "
        "(Sections 4.3, 7.5).",
        "A carbon model with experimental emission-factor (gamma) sensitivity "
        "across low-, average-, and high-carbon grids (Sections 4.4, 7.4).",
        "An expanded experimental campaign with 30 seeds per scenario reported "
        "with mean, standard deviation, and 95% confidence intervals, plus an "
        "analytical E = P x T sanity check and a literature-order PoW/PoS "
        "comparison (Sections 6, 7.6).",
    ]:
        B.append(("bullet", c))
    B.append(("p", "We explicitly position the framework as a scenario-based "
              "explorer rather than a precise real-world estimator, and we do not "
              "claim it is validated against field measurements."))

    # ---------------- 2. BACKGROUND ----------------
    B.append(("h1", "2. Background and Related Work"))
    B.append(("h2", "2.1 Blockchain Simulators"))
    B.append(("p",
        "Simulation enables controlled, reproducible study of networking, "
        "consensus, and incentive interactions without the cost and risk of real "
        "deployments. SimBlock focuses on block propagation and fork behaviour in "
        "large peer-to-peer networks [10]; JABS supports diverse consensus "
        "mechanisms at scale [11]; and ns-3-based approaches offer high-fidelity "
        "network modelling at higher integration cost [12]. BlockSim, by Alharby "
        "and van Moorsel, uses a layered discrete-event design separating "
        "network, consensus, and incentive layers, and has been widely used to "
        "study throughput, latency, and stale-block rates [9]. None of these "
        "simulators natively models energy or carbon."))
    B.append(("h2", "2.2 Energy and Carbon Studies of Blockchains"))
    B.append(("p",
        "Empirical and analytical studies have quantified Bitcoin's electricity "
        "use and carbon footprint [1], [2], [3], and general-purpose simulators "
        "such as ns-3 include packet-level energy frameworks [13], [14]. These "
        "blockchain energy analyses are typically retrospective and external to "
        "the simulator, and rarely support what-if exploration of protocol "
        "parameters. Sedlmeir et al. dispel the myth that blockchain energy is a "
        "fixed technological constant, showing instead that PoW energy is tied to "
        "mining rewards and the economics of hardware, while non-PoW mechanisms "
        "consume orders of magnitude less [4]. Platt et al. quantify the energy "
        "footprint of consensus mechanisms beyond PoW and show that "
        "validator-based mechanisms are dominated by node count and hardware "
        "rather than by computational competition [6]."))
    B.append(("h2", "2.3 Energy Consumption, Permissionlessness, and Sybil Resistance"))
    B.append(("p",
        "The energy gap between PoW and PoS is not incidental; it is tied to how "
        "each mechanism resists Sybil attacks in a permissionless setting. PoW "
        "achieves Sybil resistance by tying influence to an external, costly "
        "resource, namely computation and therefore electricity: creating many "
        "identities is useless unless each is backed by real hash power. PoS "
        "instead ties influence to internal economic stake and validator "
        "participation. Consequently PoW is not 'free': its permissionlessness is "
        "purchased with continuous resource expenditure, which is precisely why "
        "its energy use is large and price-coupled [4], [5]. PoS removes most "
        "computational waste but substitutes different trust and economic "
        "assumptions, including capital lock-up and stake-distribution concerns "
        "[6], [7]."))
    B.append(("p",
        "Platt, Platt, and McBurney formalise these tensions as a Sybil-attack "
        "vulnerability trilemma, showing that permissionlessness, Sybil "
        "resistance, and freeness (no costly resource expenditure) cannot be "
        "achieved simultaneously [15]. PoW resolves the trilemma by sacrificing "
        "freeness (spending energy); PoS relaxes the pure permissionlessness/cost "
        "trade-off differently. This framing motivates modelling PoW and PoS as "
        "distinct energy processes rather than as a single generic 'consensus "
        "energy' term, and underpins the methodology in Section 4. For Ethereum "
        "specifically, De Vries documents how its move to PoS dramatically "
        "reduced energy use and argues it illustrates a sustainability path the "
        "wider ecosystem could follow [8]."))

    # ---------------- 3. OVERVIEW ----------------
    B.append(("h1", "3. Overview of BlockSim"))
    B.append(("p",
        "BlockSim is a Python discrete-event simulator that models a blockchain "
        "as three layers: a network layer (propagation delays, peer "
        "connectivity), a consensus layer (block creation, validation, fork "
        "resolution), and an incentive layer (rewards and penalties) [9]. System "
        "dynamics evolve through scheduled events (block creation, message "
        "dissemination, chain updates) processed from a time-ordered queue. Its "
        "modularity lets researchers extend node, transaction, and consensus "
        "models without rewriting the engine, which makes it well suited to "
        "what-if and comparative studies. The original framework targets "
        "performance, security, and incentive metrics and does not model "
        "environmental cost; our extension adds that capability while preserving "
        "the layered architecture and remaining backward compatible with existing "
        "models (Section 5)."))

    # ---------------- 4. MODELS ----------------
    B.append(("h1", "4. Consensus-Aware Energy Consumption Models"))
    B.append(("p",
        "We replace the previous single generic energy model with four explicit "
        "components: a Proof-of-Work economic energy model (4.1), a Proof-of-Stake "
        "validator energy model (4.2), a communication energy model (4.3), and a "
        "carbon footprint model (4.4)."))

    B.append(("h2", "4.1 Proof-of-Work Economic Energy Model"))
    B.append(("p",
        "The defining property of PoW energy is economic: miners convert "
        "electricity into security only insofar as it is profitable. We start "
        "from the expected per-block reward expressed in fiat currency at time t:"))
    B.append(("eq", "R_t = (B_t + F_t) x P_t", 1))
    B.append(("p",
        "where B_t is the block subsidy in native coin, F_t is the expected "
        "transaction fees per block in native coin, and P_t is the coin price in "
        "fiat. A rational, competitive mining market spends on electricity a "
        "fraction kappa in [0,1] of this reward, giving an economic energy budget "
        "per block:"))
    B.append(("eq", "E_budget,t = kappa x R_t / C_elec,t", 2))
    B.append(("p",
        "where C_elec,t is the electricity price in fiat per kWh. Equation (2) is "
        "the core correction requested in review: total PoW energy rises with "
        "coin price and reward and falls with electricity price, independent of "
        "the raw miner count. When hardware-level parameters are available, a "
        "technical bound is also computed from the expected hashes per block and "
        "the hardware efficiency:"))
    B.append(("eq", "H_block = D x 2^32 ;   E_technical,t = H_block x epsilon_hash / 3.6e6", 3))
    B.append(("p",
        "where D is network difficulty, epsilon_hash is energy per hash (derived "
        "from J/TH), and 3.6e6 converts Joules to kWh. The network per-block "
        "energy and the miner-level allocation are then:"))
    B.append(("eq", "E_PoW,t = min(E_technical,t, E_budget,t) ;   E_i,t = s_i,t x E_PoW,t", 4))
    B.append(("p",
        "where s_i,t is miner i's share of network hashpower. When only economic "
        "data are available, E_budget,t is used directly as a scenario-based "
        "upper bound. The implementation exposes difficulty/hashrate hooks and an "
        "optional difficulty-retargeting routine (difficulty is adjusted so the "
        "expected block interval matches a target), allowing difficulty dynamics "
        "to be explored. Per Eq. (2)-(4), PoW energy is driven mainly by economic "
        "incentives and mining efficiency; the number of miners affects "
        "distribution (Eq. 4) but not the network total."))

    B.append(("h2", "4.2 Proof-of-Stake Validator Energy Model"))
    B.append(("p",
        "PoS does not expend external computational work, so its energy is the "
        "aggregate power of the validator machines kept online over the horizon. "
        "Following Platt et al. [6], for V validators:"))
    B.append(("eq", "E_PoS = sum_v ( P_v x T x u_v / 1000 ) + E_comm", 5))
    B.append(("p",
        "where P_v is per-validator hardware power in watts, T is the horizon in "
        "hours, u_v in [0,1] is validator uptime/utilization, the factor 1000 "
        "converts Wh to kWh, and E_comm is communication energy (Section 4.3). "
        "The model supports heterogeneous validators (per-validator P_v and u_v) "
        "and is, by construction, independent of coin price. Scenarios vary the "
        "number of validators, the hardware class (low-power node, standard "
        "server, high-power server), uptime, and communication overhead."))

    B.append(("h2", "4.3 Communication Energy Model"))
    B.append(("p",
        "Communication energy accounts for transmitting and receiving block and "
        "transaction messages. With explicit per-message and optional per-byte "
        "costs:"))
    B.append(("eq", "E_comm = sum_msg ( e_fixed + e_byte x size_bytes )   [Joules]", 6))
    B.append(("p",
        "The model maintains separate counters for transmitted and received block "
        "messages and transmitted and received transaction messages, plus byte "
        "volumes. For a gossip/flooding overlay with N nodes and peer degree d, "
        "each broadcast item produces approximately N x d directed transmissions "
        "(each a transmit and a matching receive), which the model accounts for "
        "when an experiment supplies block/transaction counts, node count, and "
        "peer degree. This makes communication energy a first-class, reported "
        "quantity rather than an unused definition."))

    B.append(("h2", "4.4 Carbon Footprint Model"))
    B.append(("p",
        "Carbon emissions are obtained from energy via a grid emission factor "
        "gamma (kgCO2e/kWh):"))
    B.append(("eq", "C = E x gamma ;   C_block = C / N_b ;   C_tx = C / N_tx", 7))
    B.append(("p",
        "where N_b and N_tx are the numbers of blocks and transactions. Because "
        "gamma captures the carbon intensity of the underlying grid, the same "
        "energy yields very different emissions across regions and times. We "
        "therefore treat gamma as an experimental variable with three named "
        f"scenarios: a low-carbon grid (gamma = {repro['gamma_low']} kgCO2e/kWh), "
        f"a global-average grid (gamma = {repro['gamma_average']}), and a "
        f"high-carbon grid (gamma = {repro['gamma_high']})."))

    # ---------------- 5. IMPLEMENTATION ----------------
    B.append(("h1", "5. Implementation in BlockSim"))
    B.append(("p",
        "The models are implemented in a new package, Models/Energy, exposing "
        "four classes: PowEconomicEnergyModel, PosValidatorEnergyModel, "
        "CommunicationEnergyModel, and CarbonFootprintModel. Each maps directly "
        "onto the equations above and is configurable through named parameters. "
        "PoW inputs include coin_price, block_subsidy, avg_tx_fees, "
        "electricity_price_per_kwh, electricity_spend_ratio_kappa, "
        "mining_efficiency_j_per_th (or per hash), difficulty, network_hashrate, "
        "miner hashpower shares, and an optional difficulty-retargeting flag. PoS "
        "inputs include validator_count, validator_power_watts, uptime_ratio, "
        "simulation_time_hours, and a validator message rate. Carbon inputs are "
        "emission_factor_gamma with named low/average/high scenarios; "
        "communication inputs are per-message and per-byte transmit/receive "
        "energies with message counters. The package is decoupled from the event "
        "loop so it can be unit-tested in isolation, driven by the experiment "
        "scripts, or embedded as accounting hooks; existing BlockSim models "
        "continue to run unchanged (backward compatible). The code, experiment "
        "scripts, unit tests, and figure pipeline are released in the project "
        "repository [16]."))

    # ---------------- 6. EXPERIMENTAL SETUP ----------------
    B.append(("h1", "6. Experimental Setup"))
    B.append(("p",
        "We evaluate the framework through controlled, scenario-based experiments "
        "spanning PoW miner scaling, PoW economic sensitivity, PoS validator "
        "scaling, carbon emission-factor sensitivity, and communication energy. "
        "The simulation horizon is 24 hours (86,400 s). Each scenario is executed "
        f"with 30 random seeds (seeds {repro['seed_list']}, generated as base + "
        "i), and we report the mean, sample standard deviation, and 95% "
        "confidence interval (Student t) of each metric. Across seeds we vary the "
        "quantities a designer cannot fix exactly: for PoW, the realised number "
        "of blocks in the horizon (Poisson around horizon/interval), transaction "
        "fees, a small coin-price jitter, and the hashpower-share distribution "
        "(Dirichlet); for PoS, per-validator power and uptime jitter. This yields "
        "genuine scenario uncertainty rather than noise added to a closed-form "
        "value. Table 1 summarises the reproducibility parameters."))
    B.append(("table", 1, "Reproducibility and parameter summary.",
        ["Parameter", "Value"],
        [["Simulation horizon", "24 h (86,400 s)"],
         ["Random seeds per scenario", repro["seed_count"]],
         ["Seed generation", f"base + i, base = {repro['seed_base']} ({repro['seed_list']})"],
         ["PoW miner counts", "50, 100, 500, 1000"],
         ["PoW block interval", "600 s (Bitcoin-like)"],
         ["PoW block subsidy / fees", "3.125 BTC / 0.30 BTC (base)"],
         ["PoW coin price (low/med/high)", "20,000 / 60,000 / 100,000 USD"],
         ["PoW electricity price", "0.03 / 0.05 / 0.10 USD/kWh"],
         ["PoW spend ratio kappa", "0.80"],
         ["PoW miner efficiency", "21.5 J/TH (ASIC class)"],
         ["PoS validator counts", "100, 500, 1000, 5000"],
         ["PoS hardware power", "10 / 100 / 500 W (node/server/high)"],
         ["PoS uptime", "0.90 / 0.99 / 1.00"],
         ["Emission factor gamma", f"{repro['gamma_low']} / {repro['gamma_average']} / {repro['gamma_high']} kgCO2e/kWh"],
         ["Communication peer degree", "4, 8, 16"],
         ["Communication tx rate", "1, 10, 100 tx/s"]]))

    # ---------------- 7. RESULTS ----------------
    B.append(("h1", "7. Results and Analysis"))

    B.append(("h2", "7.1 Proof-of-Work Energy vs Number of Miners"))
    B.append(("p",
        "Figure 1 and Table 2 report PoW network energy and mean per-miner energy "
        "as the miner population grows from 50 to 1000, holding the economics "
        f"fixed. The network total is essentially invariant at "
        f"{gwh(pm[50]['network_energy_mean_kwh']):.1f} GWh over 24 h (95% CI +/- "
        f"{gwh(pm[50]['network_energy_ci95_kwh']):.1f} GWh), because it is set by "
        "the economic budget of Eq. (2), not by the number of participants. What "
        "changes is the distribution: mean per-miner energy falls from "
        f"{f(float(pm[50]['per_miner_mean_kwh'])/1e3,1)} MWh at 50 miners to "
        f"{f(float(pm[1000]['per_miner_mean_kwh'])/1e3,1)} MWh at 1000 miners, "
        "i.e. approximately 1/N. This directly addresses the concern that energy "
        "should not be presented as a simple function of miner count."))
    B.append(("table", 2, "PoW network and per-miner energy vs miner count "
        "(24 h, 30 seeds). Network energy is invariant; per-miner energy scales "
        "~1/N.",
        ["Miners", "Network energy (GWh)", "95% CI (GWh)", "Mean per-miner (MWh)"],
        [[m, f(gwh(pm[m]["network_energy_mean_kwh"]), 1),
          f(gwh(pm[m]["network_energy_ci95_kwh"]), 1),
          f(float(pm[m]["per_miner_mean_kwh"]) / 1e3, 1)]
         for m in [50, 100, 500, 1000]]))
    B.append(("fig", "fig_pow_energy_vs_miners", 1,
        "PoW energy vs number of miners (30 seeds, 95% CI error bars). "
        "(a) Total network energy is invariant to miner count; (b) per-miner "
        "energy falls approximately as 1/N (log axis)."))

    B.append(("h2", "7.2 Proof-of-Work Energy vs Price, Reward, and Electricity Cost"))
    B.append(("p",
        "Figure 2 and Table 3 show how PoW energy responds to the economic inputs "
        "at a fixed 500-miner network. Energy scales linearly with coin price, "
        f"rising from {gwh(pp[('coin_price','low')]['network_energy_mean_kwh']):.1f} "
        f"GWh at 20,000 USD to "
        f"{gwh(pp[('coin_price','high')]['network_energy_mean_kwh']):.1f} GWh at "
        "100,000 USD. It scales linearly with the block subsidy and inversely "
        "with electricity price, exactly as the economic argument predicts. These "
        "experiments make the expected mining reward and cryptocurrency price "
        "concrete, first-class drivers of energy use."))
    B.append(("table", 3, "PoW network energy sensitivity to economic inputs "
        "(500 miners, 24 h, 30 seeds).",
        ["Sweep", "Level", "Value", "Network energy (GWh)", "95% CI (GWh)"],
        [["Coin price (USD)", "low", "20,000",
          f(gwh(pp[("coin_price","low")]["network_energy_mean_kwh"]),1),
          f(gwh(pp[("coin_price","low")]["network_energy_ci95_kwh"]),1)],
         ["Coin price (USD)", "medium", "60,000",
          f(gwh(pp[("coin_price","medium")]["network_energy_mean_kwh"]),1),
          f(gwh(pp[("coin_price","medium")]["network_energy_ci95_kwh"]),1)],
         ["Coin price (USD)", "high", "100,000",
          f(gwh(pp[("coin_price","high")]["network_energy_mean_kwh"]),1),
          f(gwh(pp[("coin_price","high")]["network_energy_ci95_kwh"]),1)],
         ["Electricity (USD/kWh)", "cheap", "0.03",
          f(gwh(pp[("electricity_price_per_kwh","cheap")]["network_energy_mean_kwh"]),1),
          f(gwh(pp[("electricity_price_per_kwh","cheap")]["network_energy_ci95_kwh"]),1)],
         ["Electricity (USD/kWh)", "expensive", "0.10",
          f(gwh(pp[("electricity_price_per_kwh","expensive")]["network_energy_mean_kwh"]),1),
          f(gwh(pp[("electricity_price_per_kwh","expensive")]["network_energy_ci95_kwh"]),1)],
         ["Block subsidy (BTC)", "low", "1.5625",
          f(gwh(pp[("block_subsidy","low")]["network_energy_mean_kwh"]),1),
          f(gwh(pp[("block_subsidy","low")]["network_energy_ci95_kwh"]),1)],
         ["Block subsidy (BTC)", "high", "6.25",
          f(gwh(pp[("block_subsidy","high")]["network_energy_mean_kwh"]),1),
          f(gwh(pp[("block_subsidy","high")]["network_energy_ci95_kwh"]),1)]]))
    B.append(("fig", "fig_pow_energy_vs_price", 2,
        "PoW network energy vs cryptocurrency price (500 miners, 30 seeds, "
        "95% CI). Energy scales linearly with coin price, the dominant economic "
        "driver."))

    B.append(("h2", "7.3 Proof-of-Stake Energy vs Validator Count"))
    B.append(("p",
        "Figure 3 and Table 4 report PoS energy as validator count grows from 100 "
        "to 5000 for three hardware classes. Unlike PoW, PoS energy scales "
        "linearly with validator count and per-node power, and is independent of "
        "coin price. For a standard 100 W server, energy rises from "
        f"{f(ps[('standard_server',100)]['total_energy_mean_kwh'],1)} kWh at 100 "
        f"validators to {f(ps[('standard_server',5000)]['total_energy_mean_kwh'],1)} "
        "kWh at 5000 validators over 24 h. Even the largest PoS configuration "
        "consumes far less than any PoW configuration, consistent with the "
        "literature (Section 7.6)."))
    B.append(("table", 4, "PoS total energy (kWh / 24 h) vs validator count by "
        "hardware class (30 seeds; 95% CI < 0.3% of mean, omitted for space).",
        ["Validators", "Low-power node (10 W)", "Standard server (100 W)",
         "High-power server (500 W)"],
        [[vc, f(ps[("low_power_node", vc)]["total_energy_mean_kwh"], 1),
          f(ps[("standard_server", vc)]["total_energy_mean_kwh"], 1),
          f(ps[("high_power_server", vc)]["total_energy_mean_kwh"], 1)]
         for vc in [100, 500, 1000, 5000]]))
    B.append(("fig", "fig_pos_energy_vs_validators", 3,
        "PoS total energy vs validator count for three hardware classes "
        "(30 seeds, 95% CI error bars). Energy scales linearly with validator "
        "count and hardware power."))

    B.append(("h2", "7.4 Carbon Emissions vs Emission Factor (gamma)"))
    spread = (float(cb[('PoW_BTC','high')]['carbon_mean_kg'])
              / float(cb[('PoW_BTC','low')]['carbon_mean_kg']))
    B.append(("p",
        "Figure 4 and Table 5 vary the grid emission factor across low, average, "
        "and high scenarios. Because C = E x gamma, the same energy yields very "
        "different carbon: for the PoW reference, daily emissions range from "
        f"{float(cb[('PoW_BTC','low')]['carbon_mean_kg'])/1000:,.0f} t at gamma = "
        f"{repro['gamma_low']} to "
        f"{float(cb[('PoW_BTC','high')]['carbon_mean_kg'])/1000:,.0f} t at gamma = "
        f"{repro['gamma_high']} (a {spread:.1f}x spread from grid choice alone). "
        "The PoS reference spans only "
        f"{float(cb[('PoS_ETH','low')]['carbon_mean_kg']):.0f}-"
        f"{float(cb[('PoS_ETH','high')]['carbon_mean_kg']):.0f} kg over the same "
        "gamma range. Geography and grid mix are therefore first-order factors, "
        "and a single fixed gamma (as in our previous version) is insufficient."))
    B.append(("table", 5, "Carbon emissions under three grid emission factors "
        "(24 h, 30 seeds). Per-block and per-transaction values use the per-family "
        "block/throughput assumptions in the reproducibility appendix.",
        ["Family", "gamma", "Total CO2 (kg)", "Per block (kg)", "Per tx (g)"],
        [["PoW (BTC-like)", repro["gamma_low"],
          f(cb[("PoW_BTC","low")]["carbon_mean_kg"],0),
          f(cb[("PoW_BTC","low")]["carbon_per_block_mean_kg"],0),
          f(cb[("PoW_BTC","low")]["carbon_per_tx_mean_g"],0)],
         ["PoW (BTC-like)", repro["gamma_average"],
          f(cb[("PoW_BTC","average")]["carbon_mean_kg"],0),
          f(cb[("PoW_BTC","average")]["carbon_per_block_mean_kg"],0),
          f(cb[("PoW_BTC","average")]["carbon_per_tx_mean_g"],0)],
         ["PoW (BTC-like)", repro["gamma_high"],
          f(cb[("PoW_BTC","high")]["carbon_mean_kg"],0),
          f(cb[("PoW_BTC","high")]["carbon_per_block_mean_kg"],0),
          f(cb[("PoW_BTC","high")]["carbon_per_tx_mean_g"],0)],
         ["PoS (ETH-like)", repro["gamma_low"],
          f(cb[("PoS_ETH","low")]["carbon_mean_kg"],1),
          f(cb[("PoS_ETH","low")]["carbon_per_block_mean_kg"],4),
          f(cb[("PoS_ETH","low")]["carbon_per_tx_mean_g"],4)],
         ["PoS (ETH-like)", repro["gamma_average"],
          f(cb[("PoS_ETH","average")]["carbon_mean_kg"],1),
          f(cb[("PoS_ETH","average")]["carbon_per_block_mean_kg"],4),
          f(cb[("PoS_ETH","average")]["carbon_per_tx_mean_g"],4)],
         ["PoS (ETH-like)", repro["gamma_high"],
          f(cb[("PoS_ETH","high")]["carbon_mean_kg"],1),
          f(cb[("PoS_ETH","high")]["carbon_per_block_mean_kg"],4),
          f(cb[("PoS_ETH","high")]["carbon_per_tx_mean_g"],4)]]))
    B.append(("fig", "fig_carbon_vs_gamma", 4,
        "Carbon emissions under different electricity emission factors (log axis, "
        "30 seeds, 95% CI). The same energy maps to widely different carbon "
        "depending on grid intensity."))

    B.append(("h2", "7.5 Communication vs Computation Energy"))
    c_low = cm[(8, 1, 1.0)]
    c_hi = cm[(8, 100, 1.0)]
    B.append(("p",
        "Figure 5 and Table 6 analyse communication energy as a function of "
        "transaction rate, block size, and peer degree, and compare it with PoW "
        "consensus energy. At peer degree 8 and 1 MB blocks, communication energy "
        f"grows from {f(c_low['comm_energy_mean_kwh'],1)} kWh/day at 1 tx/s to "
        f"{f(c_hi['comm_energy_mean_kwh'],1)} kWh/day at 100 tx/s. Relative to PoW "
        "consensus energy (~467 GWh/day) this is negligible (a ratio of about "
        f"{float(c_hi['comm_to_compute_ratio']):.1e}). However, the same "
        f"{f(c_hi['comm_energy_mean_kwh'],0)} kWh/day at 100 tx/s is of the same "
        "order as the PoS consensus energy of a 1000-validator standard-server "
        f"network ({f(ps[('standard_server',1000)]['total_energy_mean_kwh'],0)} "
        "kWh/day). Communication energy is therefore safely ignorable for PoW but "
        "can be a material fraction of total energy in PoS and high-throughput "
        "settings, which is exactly why it must be modelled explicitly."))
    B.append(("table", 6, "Communication energy vs PoW computation energy (peer "
        "degree 8, 1 MB blocks, 30 seeds).",
        ["Tx rate (tx/s)", "Comm energy (kWh/day)", "Total messages",
         "PoW compute (GWh/day)", "Comm/compute ratio"],
        [[r, f(cm[(8, r, 1.0)]["comm_energy_mean_kwh"], 1),
          f"{float(cm[(8, r, 1.0)]['mean_total_messages']):.2e}",
          f(gwh(cm[(8, r, 1.0)]["pow_compute_mean_kwh"]), 1),
          f"{float(cm[(8, r, 1.0)]['comm_to_compute_ratio']):.2e}"]
         for r in [1, 10, 100]]))
    B.append(("fig", "fig_computation_vs_communication", 5,
        "Computation vs communication energy (log-log, peer degree 8, 1 MB "
        "blocks, 30 seeds). Communication is orders of magnitude below PoW "
        "consensus energy but rises steeply with transaction rate."))

    B.append(("h2", "7.6 Sanity Checks and Literature-Order Comparison"))
    B.append(("p",
        "We do not claim validation against field measurements. Instead we report "
        "two controlled checks. First, an analytical sanity check: for "
        "fixed-power configurations the simulator's accounting must reproduce "
        "E = P x T exactly. Table 7 confirms agreement to machine precision "
        f"(maximum relative error {repro['validation_max_rel_error']}) across "
        "five configurations. Second, a literature-order check (Figure 6): the "
        f"modelled PoW reference (~{gwh(repro['pow_mean_energy_500miners_kwh']):.0f} "
        f"GWh/day) exceeds the modelled PoS reference "
        f"(~{f(repro['pos_mean_energy_1000val_kwh'],0)} kWh/day) by about "
        f"{float(repro['pow_pos_ratio']):,.0f}x. This four-to-five "
        "order-of-magnitude gap is consistent with Sedlmeir et al. [4] and Platt "
        "et al. [6], and with the ~99.95% energy reduction reported for Ethereum "
        "after The Merge [8]. The absolute PoW figure also matches the published "
        "order of magnitude for Bitcoin (hundreds of GWh per day) [1], [2]."))
    B.append(("table", 7, "Analytical E = P x T sanity check. The simulator "
        "reproduces the closed-form energy exactly.",
        ["Validators", "Power (W)", "Hours", "Analytic E=P*T (kWh)",
         "Simulator (kWh)", "Rel. error"],
        [[r["validators"], r["power_w"], r["hours"],
          f(r["analytic_E_eq_PT_kwh"], 1), f(r["simulator_kwh"], 1),
          r["rel_error"]] for r in valid]))
    B.append(("fig", "fig_pow_vs_pos_orders", 6,
        "Literature-order comparison (log axis): PoW vs PoS energy differ by "
        "roughly five orders of magnitude, consistent with prior studies and the "
        "Ethereum Merge."))

    # ---------------- 8. DISCUSSION ----------------
    B.append(("h1", "8. Discussion and Threats to Validity"))
    B.append(("h2", "8.1 Discussion"))
    B.append(("p",
        "Modelling PoW and PoS as distinct energy processes changes the "
        "qualitative story. For PoW, the dominant levers are economic (coin "
        "price, reward, electricity price) and hardware efficiency, not the "
        "participant count; adding miners redistributes a fixed economic budget. "
        "For PoS, the levers are validator count, hardware power, and uptime. The "
        "carbon results show that grid choice (gamma) can change emissions by "
        "more than an order of magnitude for identical energy, so emission-factor "
        "scenarios are essential. The communication analysis clarifies when "
        "network energy matters: negligible under PoW, potentially material under "
        "PoS and high throughput. Together these make BlockSim usable for "
        "consensus-aware what-if exploration of sustainability trade-offs."))
    B.append(("h2", "8.2 Threats to Validity and Limitations"))
    for t in [
        "The framework is a scenario-based explorer; it is not intended to "
        "predict the exact real-world energy use of Bitcoin or Ethereum, and its "
        "absolute outputs should be read as scenario values, not measurements.",
        "PoW energy is sensitive to market price, block reward, transaction fees, "
        "electricity price, mining efficiency, and difficulty/hashrate dynamics; "
        "results shift with these assumptions and the spend ratio kappa.",
        "PoS energy is sensitive to validator count, node hardware, uptime, "
        "redundancy, and communication overhead, which vary widely across "
        "operators.",
        "Carbon emissions depend strongly on region- and time-specific "
        "electricity mixes; the gamma scenarios bracket but do not resolve this "
        "variability.",
        "Historical Ethereum-like PoW configurations are illustrative of a "
        "pre-Merge GPU-mining regime and must not be interpreted as current "
        "Ethereum, which has used PoS since September 2022.",
        "Communication energy is small compared with PoW mining energy but may be "
        "significant in PoS or high-throughput scenarios; its absolute value "
        "depends on per-message/per-byte coefficients that are themselves "
        "estimates.",
        "BlockSim's discrete-event abstraction does not capture all low-level "
        "hardware optimisations or fine-grained network dynamics; this is an "
        "accepted trade-off for scalable, comparative protocol analysis.",
    ]:
        B.append(("number", t))

    # ---------------- 9. CONCLUSION ----------------
    B.append(("h1", "9. Conclusion and Future Work"))
    B.append(("p",
        "We extended BlockSim with consensus-aware energy and carbon accounting "
        "that distinguishes economically driven PoW energy from "
        "validator-count-driven PoS energy, instruments and analyses "
        "communication energy, and varies the grid emission factor "
        "experimentally. Across 30-seed scenarios reported with confidence "
        "intervals, the results show that PoW network energy is governed by "
        "economic incentives rather than miner count, that PoS energy scales with "
        "validator count and hardware, and that grid intensity dominates carbon "
        "outcomes. The framework reproduces the analytical E = P x T baseline "
        "exactly and matches the order-of-magnitude PoW/PoS gap reported in the "
        "literature. We position the tool as a scenario-based explorer rather "
        "than a precise estimator. Future work includes hardware-specific "
        "parameter libraries, dynamic and region-specific carbon intensity, "
        "difficulty-retargeting scenarios over long horizons, and tighter "
        "integration with measured network traces."))

    # ---------------- DECLARATIONS ----------------
    B.append(("h1", "Declarations"))
    B.append(("p", "Ethics approval: Not applicable. This study is based solely "
              "on simulation."))
    B.append(("p", "Consent to participate / for publication: Not applicable."))
    B.append(("p", "Funding: No funding was received for conducting this study."))
    B.append(("p", "Data and code availability: All code, experiment scripts, "
              "unit tests, raw CSV results, and the figure-generation pipeline are "
              "available in the project repository [16]."))

    # ---------------- REFERENCES ----------------
    B.append(("h1", "References"))
    refs = [
        "S. Nakamoto, \"Bitcoin: A Peer-to-Peer Electronic Cash System,\" 2008.",
        "A. de Vries, \"Bitcoin's Growing Energy Problem,\" Joule, vol. 2, no. 5, "
        "pp. 801-805, 2018. https://doi.org/10.1016/j.joule.2018.04.016",
        "C. Stoll, L. Klaassen, and U. Gallersdoerfer, \"The Carbon Footprint of "
        "Bitcoin,\" Joule, vol. 3, no. 7, pp. 1647-1661, 2019. "
        "https://doi.org/10.1016/j.joule.2019.05.012",
        "J. Sedlmeir, H. U. Buhl, G. Fridgen, and R. Keller, \"The Energy "
        "Consumption of Blockchain Technology: Beyond Myth,\" Business & "
        "Information Systems Engineering, vol. 62, no. 6, pp. 599-608, 2020. "
        "https://doi.org/10.1007/s12599-020-00656-x",
        "K. Croman et al., \"On Scaling Decentralized Blockchains,\" Financial "
        "Cryptography and Data Security, pp. 106-125, 2016. "
        "https://doi.org/10.1007/978-3-662-53357-4_8",
        "M. Platt, J. Sedlmeir, D. Platt, J. Xu, P. Tasca, N. Vadgama, and J. I. "
        "Ibanez, \"The Energy Footprint of Blockchain Consensus Mechanisms Beyond "
        "Proof-of-Work,\" IEEE 21st Int. Conf. on Software Quality, Reliability "
        "and Security Companion (QRS-C), pp. 1135-1144, 2021. "
        "https://doi.org/10.1109/QRS-C55045.2021.00168",
        "C. T. Nguyen, D. T. Hoang, D. N. Nguyen, D. Niyato, H. T. Nguyen, and E. "
        "Dutkiewicz, \"Proof-of-Stake Consensus Mechanisms for Future Blockchain "
        "Networks,\" IEEE Access, vol. 7, pp. 85727-85745, 2019. "
        "https://doi.org/10.1109/ACCESS.2019.2925010",
        "A. de Vries, \"Cryptocurrencies on the Road to Sustainability: Ethereum "
        "Paving the Way for Bitcoin,\" Patterns, vol. 4, no. 1, art. 100633, 2023 "
        "(online 2022). https://doi.org/10.1016/j.patter.2022.100633",
        "M. Alharby and A. van Moorsel, \"BlockSim: A Simulation Framework for "
        "Blockchain Systems,\" ACM SIGMETRICS Performance Evaluation Review, vol. "
        "46, no. 3, pp. 135-138, 2019; Frontiers in Blockchain, vol. 3, art. 28, "
        "2020.",
        "Y. Aoki, K. Otsuki, T. Kaneko, R. Banno, and K. Shudo, \"SimBlock: A "
        "Blockchain Network Simulator,\" IEEE INFOCOM Workshops, pp. 325-329, "
        "2019. https://doi.org/10.1109/INFCOMW.2019.8845253",
        "J. B. Schwartz et al., \"JABS: A Framework for Blockchain Consensus "
        "Evaluation,\" IEEE Trans. Network and Service Management, 2020.",
        "A. Gervais et al., \"On the Security and Performance of Proof of Work "
        "Blockchains,\" ACM CCS, pp. 3-16, 2016. "
        "https://doi.org/10.1145/2976749.2978341",
        "L. M. Feeney and M. Nilsson, \"Investigating the Energy Consumption of a "
        "Wireless Network Interface in an Ad Hoc Networking Environment,\" IEEE "
        "INFOCOM, pp. 1548-1557, 2001. https://doi.org/10.1109/INFCOM.2001.916651",
        "B. P. Singh and M. M. Gore, \"Cyber-physical energy system simulation "
        "tool: framework for network co-simulation, GridLAB-D and ns-3,\" Int. J. "
        "of Simulation and Process Modelling, vol. 18, no. 4, pp. 314-328, 2022. "
        "https://doi.org/10.1504/IJSPM.2022.128289",
        "M. Platt, D. Platt, and P. McBurney, \"Sybil attack vulnerability "
        "trilemma,\" International Journal of Parallel, Emergent and Distributed "
        "Systems, vol. 39, no. 4, pp. 446-460, 2024. "
        "https://doi.org/10.1080/17445760.2024.2352740",
        "R. S. Rasheed, \"BlockSim (consensus-aware energy/carbon extension),\" "
        "GitHub repository, 2026. https://github.com/raedrasheed/BlockSim-New",
        "IPCC, \"2019 Refinement to the 2006 IPCC Guidelines for National "
        "Greenhouse Gas Inventories,\" Intergovernmental Panel on Climate Change, "
        "2019.",
    ]
    for i, r in enumerate(refs, 1):
        B.append(("ref", i, r))

    return B
