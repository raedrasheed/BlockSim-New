"""Experiment: carbon emissions vs grid emission factor (gamma).

Answers Reviewer 2.E: gamma is now varied experimentally across low/average/high
grids. The same energy value yields very different carbon depending on the grid.
We apply the three gamma scenarios to representative PoW and PoS energy levels
and report carbon, carbon per block, and carbon per transaction.

Outputs:
  results/data/carbon_gamma_sensitivity_raw.csv
  results/data/carbon_gamma_sensitivity_summary.csv
"""

from _common import write_csv, N_SEEDS, SEED_BASE
from Models.Energy.scenarios import (run_pow_scenario, run_pos_scenario,
                                      make_seeds, summarize)
from Models.Energy.energy_models import CarbonFootprintModel, GAMMA_SCENARIOS

HORIZON_S = 86400.0
TXS_PER_BLOCK = 2000.0   # nominal throughput assumption for per-tx normalization


def main():
    seeds = make_seeds(N_SEEDS, SEED_BASE)
    raw_rows, summary_rows = [], []

    # Build a representative energy sample for each consensus family.
    families = {
        "PoW_BTC": lambda s: run_pow_scenario(seed=s, miner_count=500, horizon_s=HORIZON_S),
        "PoS_ETH": lambda s: run_pos_scenario(seed=s, validator_count=1000,
                                              validator_power_watts=100.0,
                                              simulation_time_hours=HORIZON_S / 3600.0),
    }

    for fam, runner in families.items():
        for gname, gamma in GAMMA_SCENARIOS.items():
            carb_kg, carb_block, carb_tx = [], [], []
            cm = CarbonFootprintModel(emission_factor_gamma=gamma)
            for s in seeds:
                r = runner(s)
                if fam.startswith("PoW"):
                    energy = r.network_energy_kwh
                    nblocks = r.num_blocks
                else:
                    energy = r.total_energy_kwh
                    nblocks = HORIZON_S / 12.0  # ETH PoS ~12 s slots
                ntx = nblocks * TXS_PER_BLOCK
                carb_kg.append(cm.carbon_kg(energy))
                carb_block.append(cm.carbon_per_block_kg(energy, nblocks))
                carb_tx.append(cm.carbon_per_tx_kg(energy, ntx))
                raw_rows.append(dict(family=fam, gamma_scenario=gname, gamma=gamma,
                                     seed=s, energy_kwh=energy,
                                     carbon_kg=cm.carbon_kg(energy),
                                     carbon_per_block_kg=cm.carbon_per_block_kg(energy, nblocks),
                                     carbon_per_tx_g=cm.carbon_per_tx_kg(energy, ntx) * 1000.0))
            su = summarize(carb_kg)
            summary_rows.append(dict(family=fam, gamma_scenario=gname, gamma=gamma,
                                     carbon_mean_kg=su["mean"], carbon_std_kg=su["std"],
                                     carbon_ci95_kg=su["ci95_halfwidth"],
                                     carbon_per_block_mean_kg=summarize(carb_block)["mean"],
                                     carbon_per_tx_mean_g=summarize(carb_tx)["mean"] * 1000.0,
                                     n_seeds=su["n"]))
            print(f"[Carbon {fam:8s} gamma={gname:8s} ({gamma})] "
                  f"C={su['mean']:.2f}±{su['ci95_halfwidth']:.2f} kg")

    write_csv("carbon_gamma_sensitivity_raw.csv", raw_rows,
              ["family", "gamma_scenario", "gamma", "seed", "energy_kwh",
               "carbon_kg", "carbon_per_block_kg", "carbon_per_tx_g"])
    write_csv("carbon_gamma_sensitivity_summary.csv", summary_rows,
              ["family", "gamma_scenario", "gamma", "carbon_mean_kg",
               "carbon_std_kg", "carbon_ci95_kg", "carbon_per_block_mean_kg",
               "carbon_per_tx_mean_g", "n_seeds"])
    return summary_rows


if __name__ == "__main__":
    main()
