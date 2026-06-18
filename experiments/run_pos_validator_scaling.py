"""Experiment: PoS energy vs validator count and validator hardware class.

Answers Reviewer 1.3b: PoS energy is driven by validator count and per-node
hardware power, not by coin price. We sweep validator counts {100,500,1000,5000}
across three hardware classes and an uptime sensitivity, with communication
overhead included.

Outputs:
  results/data/pos_validator_scaling_raw.csv
  results/data/pos_validator_scaling_summary.csv
"""

from _common import write_csv, N_SEEDS, SEED_BASE
from Models.Energy.scenarios import (run_pos_scenario, make_seeds, summarize,
                                      POS_VALIDATOR_POWER)
from Models.Energy.energy_models import CommunicationEnergyModel

VALIDATOR_COUNTS = [100, 500, 1000, 5000]
SIM_HOURS = 24.0
UPTIME_LEVELS = {"0.90": 0.90, "0.99": 0.99, "1.00": 1.00}

# Small fixed per-message energy for validator gossip (attestations etc.).
COMM = CommunicationEnergyModel(tx_energy_per_message_j=0.05, rx_energy_per_message_j=0.05)


def main():
    seeds = make_seeds(N_SEEDS, SEED_BASE)
    raw_rows, summary_rows = [], []

    for cls_name, p_w in POS_VALIDATOR_POWER.items():
        for vc in VALIDATOR_COUNTS:
            totals, comms = [], []
            for s in seeds:
                r = run_pos_scenario(seed=s, validator_count=vc,
                                     validator_power_watts=p_w,
                                     uptime_ratio=0.99,
                                     simulation_time_hours=SIM_HOURS,
                                     comm_model=COMM)
                totals.append(r.total_energy_kwh)
                comms.append(r.communication_energy_kwh)
                raw_rows.append(dict(hw_class=cls_name, validator_power_w=p_w,
                                     validator_count=vc, seed=s,
                                     total_energy_kwh=r.total_energy_kwh,
                                     consensus_energy_kwh=r.consensus_energy_kwh,
                                     communication_energy_kwh=r.communication_energy_kwh))
            su = summarize(totals)
            summary_rows.append(dict(hw_class=cls_name, validator_power_w=p_w,
                                     validator_count=vc,
                                     total_energy_mean_kwh=su["mean"],
                                     total_energy_std_kwh=su["std"],
                                     total_energy_ci95_kwh=su["ci95_halfwidth"],
                                     comm_energy_mean_kwh=summarize(comms)["mean"],
                                     n_seeds=su["n"]))
            print(f"[PoS {cls_name:16s} V={vc:5d}] "
                  f"total={su['mean']:.2f}±{su['ci95_halfwidth']:.3f} kWh")

    # uptime sensitivity at standard server / 1000 validators
    for label, u in UPTIME_LEVELS.items():
        totals = []
        for s in seeds:
            r = run_pos_scenario(seed=s, validator_count=1000,
                                 validator_power_watts=POS_VALIDATOR_POWER["standard_server"],
                                 uptime_ratio=u, simulation_time_hours=SIM_HOURS,
                                 comm_model=COMM)
            totals.append(r.total_energy_kwh)
        su = summarize(totals)
        summary_rows.append(dict(hw_class="uptime_sweep", validator_power_w=100.0,
                                 validator_count=1000,
                                 total_energy_mean_kwh=su["mean"],
                                 total_energy_std_kwh=su["std"],
                                 total_energy_ci95_kwh=su["ci95_halfwidth"],
                                 comm_energy_mean_kwh=u, n_seeds=su["n"]))
        print(f"[PoS uptime={label}] total={su['mean']:.2f}±{su['ci95_halfwidth']:.3f} kWh")

    write_csv("pos_validator_scaling_raw.csv", raw_rows,
              ["hw_class", "validator_power_w", "validator_count", "seed",
               "total_energy_kwh", "consensus_energy_kwh", "communication_energy_kwh"])
    write_csv("pos_validator_scaling_summary.csv", summary_rows,
              ["hw_class", "validator_power_w", "validator_count",
               "total_energy_mean_kwh", "total_energy_std_kwh",
               "total_energy_ci95_kwh", "comm_energy_mean_kwh", "n_seeds"])
    return summary_rows


if __name__ == "__main__":
    main()
