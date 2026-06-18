# BlockSim Simultor

> ### Consensus-Aware Energy & Carbon Extension
> This fork extends BlockSim with **consensus-aware energy and carbon footprint
> modeling**. It models Proof-of-Work (PoW) energy as an **economically driven**
> quantity (expected reward and coin price are explicit inputs) and
> Proof-of-Stake (PoS) energy as a **validator-count driven** quantity, adds a
> communication-energy model and an emission-factor (γ) carbon model, and ships
> reproducible experiments, figures, and unit tests. See
> [`docs/`](docs/) and the section **"Consensus-Aware Energy & Carbon Extension"**
> at the bottom of this file.

## What is BlockSim Simulator?
**BlockSim** is an open source blockchain simulator, capturing network, consensus and incentives layers of blockchain systems. BlockSim aims to provide simulation constructs that are intuitive, hide unnecessary detail and can be easily manipulated to be applied to a large set of blockchains design and deployment questions (related to performance, reliability, security or other properties of interest). At the core of BlockSim is a Base Model, which contains a number of functional blocks (e.g., blocks, transactions and nodes) common across blockchains, that can be extended and configured as suited for the system and study of interest. BlockSim is implemented in **Python**.

For more details about BlockSim, we refer to our journal paper that can be freely accessed online https://www.frontiersin.org/articles/10.3389/fbloc.2020.00028/full

## Installation and Requirements

Before you can use BlockSim  simulator, you need to have **Python version 3 or above** installed in your machine as well as have the following packages installed:

- pandas 
>pip install pandas
- numpy 
>pip install numpy
- sklearn 
>pip install sklearn
- xlsxwriter
>pip install xlsxwriter

## Running the simulator

Before you run the simulator, you can access the configuration file *InputsConfig.py* to choose the model of interest (Base Model 0, Bitcoin Model 1 and Ethereum Model 2) and to set up the related parameters.
The parameters include the number of nodes (and their fraction of hash power), the block interval time, the block propagation delays, the block and transaction sizes, the block rewards, the tranaction fees etc.
Each model has a slightly different (or additional) parameters to capture it.

To run the simulator, one needs to trigger the main class *Main.py* either from the command line
> python Main.py

or using any Python editor such as Spyder.

## Statistics and Results

The results of the simulator is printed in an excel file at the end of the simulation. The results include the blockchain ledger, number of blocks mined, number of stale (uncles) blocks and the rewards gained by each miner etc. 

## Contact

For any query about how to use or even extend the simulator, feel free to contact me **alharbi.maher@gmail.com**

---

# Consensus-Aware Energy & Carbon Extension

This section documents the energy/carbon revision added in `Models/Energy/`,
`experiments/`, `tests/`, and `docs/`.

## What was added
The two dominant consensus families are modelled as **distinct energy processes**:

- **PoW (economic):** `PowEconomicEnergyModel` — energy is bounded by the fiat
  value of the block reward, *not* by the number of miners.
  - `R_t = (B_t + F_t) × P_t` (expected reward), `E_budget = κ · R_t / C_elec`
    (economic energy), optional technical bound from difficulty/efficiency,
    `E_PoW = min(E_technical, E_budget)`, per-miner `E_i = s_i · E_PoW`.
- **PoS (validator-count):** `PosValidatorEnergyModel` —
  `E_PoS = Σ_v (P_v · T · u_v / 1000) + E_comm`.
- **Communication:** `CommunicationEnergyModel` — counts block/transaction
  messages and bytes; `E_comm = Σ (e_fixed + e_byte · size)`.
- **Carbon:** `CarbonFootprintModel` — `C = E · γ`, with named grid scenarios
  `low (0.05)`, `average (0.475)`, `high (0.82)` kgCO₂e/kWh.

## Requirements (extension)
```bash
pip install pandas numpy matplotlib scipy xlsxwriter python-docx pytest reportlab pillow
```

## How to run the experiments and reproduce the paper figures
```bash
# Run all experiments (30 seeds each) -> results/data/*.csv and results/figures/*.{png,pdf}
python experiments/run_all_revision_experiments.py

# Or run a single experiment
python experiments/run_pow_miner_scaling.py
python experiments/run_pow_price_sensitivity.py
python experiments/run_pos_validator_scaling.py
python experiments/run_carbon_gamma_sensitivity.py
python experiments/run_communication_energy_analysis.py
```

## How to rebuild the revised manuscript
```bash
python docs/build_revised_manuscript.py   # -> docs/...REVISED.docx
python docs/build_revised_pdf.py          # -> docs/...REVISED.pdf
```

## How to run the tests
```bash
python -m pytest tests/ -v
```

## How to configure PoW / PoS / carbon parameters
Use the model classes directly, e.g.:
```python
from Models.Energy import (PowEconomicEnergyModel, PosValidatorEnergyModel,
                           CommunicationEnergyModel, CarbonFootprintModel)

pow_model = PowEconomicEnergyModel(
    block_subsidy=3.125, avg_tx_fees=0.30, coin_price=60000.0,
    electricity_price_per_kwh=0.05, electricity_spend_ratio_kappa=0.80,
    mining_efficiency_j_per_th=21.5)
print(pow_model.energy_budget_per_block_kwh())

pos_model = PosValidatorEnergyModel(validator_count=1000,
    validator_power_watts=100.0, simulation_time_hours=24.0, uptime_ratio=0.99)
print(pos_model.total_energy_kwh())

carbon = CarbonFootprintModel(scenario="average")   # or emission_factor_gamma=0.3
print(carbon.carbon_kg(1000.0))
```
Named baseline scenarios and the seed-based runners live in
`Models/Energy/scenarios.py`.

## Backward compatibility
The extension is **additive**: no existing BlockSim model files were modified,
and `Main.py` / `InputsConfig.py` are unchanged. Existing simulations run exactly
as before.

## Documentation
- `docs/RESPONSE_TO_REVIEWERS.md` — point-by-point response letter.
- `docs/CHANGELOG_REVISION.md` — list of all changes.
- `docs/REPRODUCIBILITY_APPENDIX.md` — seeds, parameters, headline numbers.
- `docs/Extending_BlockSim_Consensus_Aware_Energy_Carbon_REVISED.{docx,pdf}` —
  revised manuscript.
