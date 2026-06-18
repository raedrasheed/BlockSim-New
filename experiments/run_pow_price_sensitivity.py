"""Experiment: PoW energy vs cryptocurrency price (and reward/electricity price).

Directly answers Reviewer 1.1: expected mining reward and coin price are now
explicit inputs. We sweep coin price (low/medium/high), block reward, and
electricity price, and show network energy responds as the economics dictate.

Outputs:
  results/data/pow_price_sensitivity_raw.csv
  results/data/pow_price_sensitivity_summary.csv
"""

from _common import write_csv, N_SEEDS, SEED_BASE
from Models.Energy.scenarios import (run_pow_scenario, make_seeds, summarize,
                                      POW_PRICE_LEVELS)

MINER_COUNT = 500
HORIZON_S = 86400.0
ELEC_PRICES = {"cheap": 0.03, "typical": 0.05, "expensive": 0.10}  # USD/kWh
BLOCK_SUBSIDIES = {"low": 1.5625, "base": 3.125, "high": 6.25}     # BTC/block


def _sweep(varname, values, fixed, raw_rows, summary_rows):
    seeds = make_seeds(N_SEEDS, SEED_BASE)
    for label, val in values.items():
        kwargs = dict(fixed)
        kwargs[varname] = val
        energies = []
        for s in seeds:
            r = run_pow_scenario(seed=s, miner_count=MINER_COUNT,
                                 horizon_s=HORIZON_S, **kwargs)
            energies.append(r.network_energy_kwh)
            raw_rows.append(dict(sweep=varname, level=label, value=val, seed=s,
                                 network_energy_kwh=r.network_energy_kwh,
                                 expected_reward_fiat=r.expected_reward_fiat))
        su = summarize(energies)
        summary_rows.append(dict(sweep=varname, level=label, value=val,
                                 network_energy_mean_kwh=su["mean"],
                                 network_energy_std_kwh=su["std"],
                                 network_energy_ci95_kwh=su["ci95_halfwidth"],
                                 n_seeds=su["n"]))
        print(f"[PoW {varname}={label:9s} ({val})] "
              f"network={su['mean']:.2f}±{su['ci95_halfwidth']:.2f} kWh")


def main():
    raw_rows, summary_rows = [], []
    _sweep("coin_price", POW_PRICE_LEVELS, dict(), raw_rows, summary_rows)
    _sweep("electricity_price_per_kwh", ELEC_PRICES, dict(), raw_rows, summary_rows)
    _sweep("block_subsidy", BLOCK_SUBSIDIES, dict(), raw_rows, summary_rows)

    write_csv("pow_price_sensitivity_raw.csv", raw_rows,
              ["sweep", "level", "value", "seed", "network_energy_kwh",
               "expected_reward_fiat"])
    write_csv("pow_price_sensitivity_summary.csv", summary_rows,
              ["sweep", "level", "value", "network_energy_mean_kwh",
               "network_energy_std_kwh", "network_energy_ci95_kwh", "n_seeds"])
    return summary_rows


if __name__ == "__main__":
    main()
