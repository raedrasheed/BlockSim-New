"""Run every revision experiment, generate all paper figures, and produce the
validation (E = P*T) and reproducibility outputs.

Usage:
    python experiments/run_all_revision_experiments.py

All numeric outputs land in results/data/*.csv and all figures in
results/figures/*.{png,pdf}.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from _common import write_csv, save_fig, setup_matplotlib, N_SEEDS, SEED_BASE
from Models.Energy.scenarios import (run_pos_scenario, make_seeds, summarize,
                                     POS_VALIDATOR_POWER, POW_PRICE_LEVELS)
from Models.Energy.energy_models import (PosValidatorEnergyModel,
                                         CarbonFootprintModel, GAMMA_SCENARIOS)

import run_pow_miner_scaling as pow_miners
import run_pow_price_sensitivity as pow_price
import run_pos_validator_scaling as pos_scaling
import run_carbon_gamma_sensitivity as carbon_gamma
import run_communication_energy_analysis as comm_energy


# ---------------------------------------------------------------------------
# Validation: analytical sanity check  E = P * T
# ---------------------------------------------------------------------------
def run_validation():
    """Confirm the simulator's fixed-power accounting matches E = P*T exactly."""
    rows = []
    cases = [(1, 100.0, 10.0), (10, 100.0, 24.0), (500, 100.0, 24.0),
             (1000, 50.0, 24.0), (5000, 250.0, 24.0)]
    max_rel_err = 0.0
    for v, p_w, t_h in cases:
        m = PosValidatorEnergyModel(validator_count=v, validator_power_watts=p_w,
                                    simulation_time_hours=t_h, uptime_ratio=1.0)
        sim = m.total_energy_kwh()
        analytic = v * p_w * t_h / 1000.0
        rel_err = abs(sim - analytic) / analytic if analytic else 0.0
        max_rel_err = max(max_rel_err, rel_err)
        rows.append(dict(validators=v, power_w=p_w, hours=t_h,
                         analytic_E_eq_PT_kwh=analytic, simulator_kwh=sim,
                         rel_error=rel_err))
    write_csv("validation_fixed_power.csv", rows,
              ["validators", "power_w", "hours", "analytic_E_eq_PT_kwh",
               "simulator_kwh", "rel_error"])
    print(f"[Validation] E=P*T fixed-power check: max relative error = {max_rel_err:.2e}")
    return rows, max_rel_err


# ---------------------------------------------------------------------------
# Figures
# ---------------------------------------------------------------------------
def fig_pow_energy_vs_miners(plt, summ):
    counts = [r["miner_count"] for r in summ]
    net = [r["network_energy_mean_kwh"] for r in summ]
    net_ci = [r["network_energy_ci95_kwh"] for r in summ]
    pm = [r["per_miner_mean_kwh"] for r in summ]
    pm_ci = [r["per_miner_ci95_kwh"] for r in summ]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))
    ax1.errorbar(counts, net, yerr=net_ci, marker="o", capsize=4, color="#1f77b4")
    ax1.set_xlabel("Number of miners")
    ax1.set_ylabel("Network energy (kWh / 24 h)")
    ax1.set_title("(a) Total PoW energy is invariant to miner count")
    ax1.set_ylim(0, max(net) * 1.3)

    ax2.errorbar(counts, pm, yerr=pm_ci, marker="s", capsize=4, color="#d62728")
    ax2.set_xlabel("Number of miners")
    ax2.set_ylabel("Mean energy per miner (kWh / 24 h)")
    ax2.set_title("(b) Per-miner energy falls ~1/N")
    ax2.set_yscale("log")
    save_fig(fig, "fig_pow_energy_vs_miners")
    plt.close(fig)


def fig_pow_energy_vs_price(plt, summ):
    rows = [r for r in summ if r["sweep"] == "coin_price"]
    order = ["low", "medium", "high"]
    rows.sort(key=lambda r: order.index(r["level"]))
    prices = [r["value"] for r in rows]
    energy = [r["network_energy_mean_kwh"] for r in rows]
    ci = [r["network_energy_ci95_kwh"] for r in rows]
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.errorbar(prices, energy, yerr=ci, marker="o", capsize=5, color="#2ca02c")
    ax.set_xlabel("Cryptocurrency price (USD/coin)")
    ax.set_ylabel("Network energy (kWh / 24 h)")
    ax.set_title("PoW energy scales with coin price (economic driver)")
    for x, y in zip(prices, energy):
        ax.annotate(f"{y:,.0f}", (x, y), textcoords="offset points",
                    xytext=(0, 8), ha="center", fontsize=9)
    save_fig(fig, "fig_pow_energy_vs_price")
    plt.close(fig)


def fig_pos_energy_vs_validators(plt, summ):
    classes = ["low_power_node", "standard_server", "high_power_server"]
    colors = {"low_power_node": "#1f77b4", "standard_server": "#ff7f0e",
              "high_power_server": "#9467bd"}
    fig, ax = plt.subplots(figsize=(6.5, 4))
    for cls in classes:
        rows = [r for r in summ if r["hw_class"] == cls]
        rows.sort(key=lambda r: r["validator_count"])
        x = [r["validator_count"] for r in rows]
        y = [r["total_energy_mean_kwh"] for r in rows]
        ci = [r["total_energy_ci95_kwh"] for r in rows]
        ax.errorbar(x, y, yerr=ci, marker="o", capsize=4, label=cls.replace("_", " "),
                    color=colors[cls])
    ax.set_xlabel("Number of validators")
    ax.set_ylabel("Total energy (kWh / 24 h)")
    ax.set_title("PoS energy scales linearly with validator count")
    ax.legend()
    save_fig(fig, "fig_pos_energy_vs_validators")
    plt.close(fig)


def fig_carbon_vs_gamma(plt, summ):
    fams = ["PoW_BTC", "PoS_ETH"]
    gnames = ["low", "average", "high"]
    import numpy as np
    x = np.arange(len(gnames))
    width = 0.35
    fig, ax = plt.subplots(figsize=(7, 4))
    for i, fam in enumerate(fams):
        vals, cis = [], []
        for g in gnames:
            row = next(r for r in summ if r["family"] == fam and r["gamma_scenario"] == g)
            vals.append(row["carbon_mean_kg"])
            cis.append(row["carbon_ci95_kg"])
        ax.bar(x + (i - 0.5) * width, vals, width, yerr=cis, capsize=4,
               label=fam.replace("_", " "))
    ax.set_xticks(x)
    ax.set_xticklabels([f"{g}\n(γ={GAMMA_SCENARIOS[g]})" for g in gnames])
    ax.set_xlabel("Grid emission factor scenario")
    ax.set_ylabel("Carbon emissions (kgCO₂e / 24 h)")
    ax.set_title("Carbon emissions under different electricity emission factors")
    ax.set_yscale("log")
    ax.legend()
    save_fig(fig, "fig_carbon_vs_gamma")
    plt.close(fig)


def fig_computation_vs_communication(plt, summ):
    # Fix peer_degree=8, block_size=1 MB; sweep tx rate.
    rows = [r for r in summ if r["peer_degree"] == 8 and abs(r["block_size_mb"] - 1.0) < 1e-6]
    rows.sort(key=lambda r: r["tx_rate_hz"])
    x = [r["tx_rate_hz"] for r in rows]
    comm = [r["comm_energy_mean_kwh"] for r in rows]
    comp = [r["pow_compute_mean_kwh"] for r in rows]
    fig, ax = plt.subplots(figsize=(6.5, 4))
    ax.plot(x, comp, marker="o", label="PoW consensus (computation)", color="#1f77b4")
    ax.plot(x, comm, marker="s", label="Communication", color="#d62728")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Transaction rate (tx/s)")
    ax.set_ylabel("Energy (kWh / 24 h, log scale)")
    ax.set_title("Computation vs communication energy (peer degree 8, 1 MB blocks)")
    ax.legend()
    save_fig(fig, "fig_computation_vs_communication")
    plt.close(fig)


def fig_pow_vs_pos_orders(plt):
    """Literature-order sanity check: PoW vs PoS energy differ by orders of
    magnitude, consistent with Sedlmeir et al. (2020) and Platt et al. (2021)."""
    seeds = make_seeds(N_SEEDS, SEED_BASE)
    import run_pow_miner_scaling as pm
    from Models.Energy.scenarios import run_pow_scenario
    pow_e = summarize([run_pow_scenario(seed=s, miner_count=500).network_energy_kwh
                       for s in seeds])
    pos_e = summarize([run_pos_scenario(seed=s, validator_count=1000,
                                        validator_power_watts=100.0,
                                        simulation_time_hours=24.0).total_energy_kwh
                       for s in seeds])
    fig, ax = plt.subplots(figsize=(5.5, 4))
    labels = ["PoW (Bitcoin-like)\n500 miners", "PoS (Ethereum-like)\n1000 validators"]
    vals = [pow_e["mean"], pos_e["mean"]]
    cis = [pow_e["ci95_halfwidth"], pos_e["ci95_halfwidth"]]
    ax.bar(labels, vals, yerr=cis, capsize=5, color=["#1f77b4", "#ff7f0e"])
    ax.set_yscale("log")
    ax.set_ylabel("Energy (kWh / 24 h, log scale)")
    ax.set_title("PoW vs PoS energy: orders-of-magnitude gap")
    for i, v in enumerate(vals):
        ax.annotate(f"{v:,.1f}", (i, v), textcoords="offset points",
                    xytext=(0, 6), ha="center", fontsize=9)
    save_fig(fig, "fig_pow_vs_pos_orders")
    plt.close(fig)
    return pow_e["mean"], pos_e["mean"]


# ---------------------------------------------------------------------------
def main():
    print("=" * 70)
    print("Running all revision experiments (>=%d seeds each)" % N_SEEDS)
    print("=" * 70)

    pm_summary = pow_miners.main()
    pp_summary = pow_price.main()
    ps_summary = pos_scaling.main()
    cg_summary = carbon_gamma.main()
    ce_summary = comm_energy.main()
    val_rows, max_err = run_validation()

    print("\nGenerating figures ...")
    plt = setup_matplotlib()
    fig_pow_energy_vs_miners(plt, pm_summary)
    fig_pow_energy_vs_price(plt, pp_summary)
    fig_pos_energy_vs_validators(plt, ps_summary)
    fig_carbon_vs_gamma(plt, cg_summary)
    fig_computation_vs_communication(plt, ce_summary)
    pow_mean, pos_mean = fig_pow_vs_pos_orders(plt)

    # Reproducibility summary
    repro = [dict(parameter="seed_count", value=N_SEEDS),
             dict(parameter="seed_base", value=SEED_BASE),
             dict(parameter="seed_list", value=f"{SEED_BASE}..{SEED_BASE + N_SEEDS - 1}"),
             dict(parameter="horizon_seconds", value=86400),
             dict(parameter="pow_miner_counts", value="50;100;500;1000"),
             dict(parameter="pos_validator_counts", value="100;500;1000;5000"),
             dict(parameter="gamma_low", value=GAMMA_SCENARIOS["low"]),
             dict(parameter="gamma_average", value=GAMMA_SCENARIOS["average"]),
             dict(parameter="gamma_high", value=GAMMA_SCENARIOS["high"]),
             dict(parameter="pow_mean_energy_500miners_kwh", value=round(pow_mean, 3)),
             dict(parameter="pos_mean_energy_1000val_kwh", value=round(pos_mean, 3)),
             dict(parameter="pow_pos_ratio", value=round(pow_mean / pos_mean, 1)),
             dict(parameter="validation_max_rel_error", value=f"{max_err:.2e}")]
    write_csv("reproducibility_summary.csv", repro, ["parameter", "value"])

    print("\nAll experiments complete.")
    print(f"  PoW(500 miners) mean energy : {pow_mean:,.1f} kWh / 24 h")
    print(f"  PoS(1000 val)   mean energy : {pos_mean:,.3f} kWh / 24 h")
    print(f"  PoW/PoS ratio               : {pow_mean / pos_mean:,.0f}x")
    print(f"  Validation max rel. error   : {max_err:.2e}")
    print("Figures in results/figures/, data in results/data/")


if __name__ == "__main__":
    main()
