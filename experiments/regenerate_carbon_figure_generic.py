"""Regenerate the carbon-vs-gamma figure with GENERIC consensus labels.

This is an editor-mediated figure revision: the previously embedded carbon
figure used cryptocurrency-specific legend labels ("PoW BTC", "PoS ETH").
Per the handling editor's instruction to generalise to PoW/PoS scenarios,
this script reproduces the identical data (from the unchanged
results/data/carbon_gamma_sensitivity_summary.csv) with generic legend
labels "PoW scenario" and "PoS scenario". No data are changed.

Output: results/figures/fig_carbon_vs_gamma_generic.{png,pdf}
"""
import csv, os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SUMMARY = os.path.join(ROOT, "results", "data", "carbon_gamma_sensitivity_summary.csv")
FIGDIR = os.path.join(ROOT, "results", "figures")

GAMMA = {"low": 0.05, "average": 0.475, "high": 0.82}
# generic display labels replacing PoW_BTC / PoS_ETH
FAM_LABEL = {"PoW_BTC": "PoW scenario", "PoS_ETH": "PoS scenario"}

def load():
    rows = []
    with open(SUMMARY) as f:
        for r in csv.DictReader(f):
            rows.append(r)
    return rows

def main():
    plt.rcParams.update({"figure.dpi": 130, "savefig.dpi": 200, "font.size": 11,
                         "axes.grid": True, "grid.alpha": 0.3, "axes.axisbelow": True,
                         "figure.autolayout": True})
    rows = load()
    fams = ["PoW_BTC", "PoS_ETH"]
    gnames = ["low", "average", "high"]
    x = np.arange(len(gnames)); width = 0.35
    fig, ax = plt.subplots(figsize=(7, 4))
    for i, fam in enumerate(fams):
        vals, cis = [], []
        for g in gnames:
            row = next(r for r in rows if r["family"] == fam and r["gamma_scenario"] == g)
            vals.append(float(row["carbon_mean_kg"]))
            cis.append(float(row["carbon_ci95_kg"]))
        ax.bar(x + (i - 0.5) * width, vals, width, yerr=cis, capsize=4,
               label=FAM_LABEL[fam])
    ax.set_xticks(x)
    ax.set_xticklabels([f"{g}\n(γ={GAMMA[g]})" for g in gnames])
    ax.set_xlabel("Grid emission factor scenario")
    ax.set_ylabel("Carbon emissions (kgCO₂e / 24 h)")
    ax.set_title("Carbon emissions under different electricity emission factors")
    ax.set_yscale("log")
    ax.legend()
    os.makedirs(FIGDIR, exist_ok=True)
    png = os.path.join(FIGDIR, "fig_carbon_vs_gamma_generic.png")
    pdf = os.path.join(FIGDIR, "fig_carbon_vs_gamma_generic.pdf")
    fig.savefig(png, bbox_inches="tight"); fig.savefig(pdf, bbox_inches="tight")
    plt.close(fig)
    print("wrote", png)

if __name__ == "__main__":
    main()
