"""Experiment: PoW energy vs number of miners.

Key message (directly answering Reviewer 1.1 / 1.3a): in the economically driven
PoW model the *total network* energy is essentially invariant to the number of
miners -- it is bounded by the fiat value of the block reward, not by how many
machines share the work. Increasing the miner count only redistributes the same
budget (per-miner energy falls ~1/N).

Outputs:
  results/data/pow_miner_scaling_raw.csv      (per-seed values)
  results/data/pow_miner_scaling_summary.csv  (mean/std/95%CI per miner count)
"""

from _common import write_csv, N_SEEDS, SEED_BASE
from Models.Energy.scenarios import run_pow_scenario, make_seeds, summarize

MINER_COUNTS = [50, 100, 500, 1000]
HORIZON_S = 86400.0  # 24 h


def main():
    seeds = make_seeds(N_SEEDS, SEED_BASE)
    raw_rows, summary_rows = [], []

    for nm in MINER_COUNTS:
        net_energy, per_miner_mean = [], []
        for s in seeds:
            r = run_pow_scenario(seed=s, miner_count=nm, horizon_s=HORIZON_S)
            net_energy.append(r.network_energy_kwh)
            per_miner_mean.append(sum(r.miner_energy_kwh) / nm)
            raw_rows.append(dict(
                miner_count=nm, seed=s,
                network_energy_kwh=r.network_energy_kwh,
                energy_per_block_kwh=r.energy_per_block_kwh,
                num_blocks=r.num_blocks,
                mean_per_miner_kwh=sum(r.miner_energy_kwh) / nm,
                max_miner_kwh=max(r.miner_energy_kwh),
            ))
        ne = summarize(net_energy)
        pm = summarize(per_miner_mean)
        summary_rows.append(dict(
            miner_count=nm,
            network_energy_mean_kwh=ne["mean"], network_energy_std_kwh=ne["std"],
            network_energy_ci95_kwh=ne["ci95_halfwidth"],
            per_miner_mean_kwh=pm["mean"], per_miner_std_kwh=pm["std"],
            per_miner_ci95_kwh=pm["ci95_halfwidth"], n_seeds=ne["n"],
        ))
        print(f"[PoW miners={nm:5d}] network={ne['mean']:.2f}±{ne['ci95_halfwidth']:.2f} kWh "
              f"| per-miner={pm['mean']:.4f}±{pm['ci95_halfwidth']:.4f} kWh")

    write_csv("pow_miner_scaling_raw.csv", raw_rows,
              ["miner_count", "seed", "network_energy_kwh", "energy_per_block_kwh",
               "num_blocks", "mean_per_miner_kwh", "max_miner_kwh"])
    write_csv("pow_miner_scaling_summary.csv", summary_rows,
              ["miner_count", "network_energy_mean_kwh", "network_energy_std_kwh",
               "network_energy_ci95_kwh", "per_miner_mean_kwh", "per_miner_std_kwh",
               "per_miner_ci95_kwh", "n_seeds"])
    return summary_rows


if __name__ == "__main__":
    main()
