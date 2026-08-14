"""Stage 8X — thesis-quality figures.

Conventions
-----------
* Every axis is labelled with units; no dual-axis plots anywhere.
* Categorical colour follows the *entity* (protocol), assigned in a fixed order and
  never cycled or repainted. The categorical palette is the Okabe-Ito
  colour-vision-deficiency-safe set, ordered so that every adjacent pair clears the
  CVD separation check (worst adjacent deltaE 11.0 deutan / 8.5 tritan). Protocol
  identity is additionally carried by marker shape and by a legend that is always
  present, so identity is never colour-alone.
* Ordered quantities (alpha, N) use a single-hue *sequential* ramp, light to dark.
* Error bars are 95 % confidence intervals of the mean across the 30 paired seeds.
* Axes are linear and start where the data start; effects are never visually
  exaggerated. Small effects are drawn small.
* Each figure is written as PNG (raster), PDF and SVG (vector).
"""

from __future__ import annotations

import os
from typing import Dict, List

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from experiments.stage8x.analysis.stats import describe
from experiments.stage8x.config import stage8x_config as C
from experiments.stage8x.config.asic import ALPHA_CASES, S21_PRO

# --- validated categorical palette (entity identity) ---
COLOR = {
    C.PROTO_POW: "#0072B2",      # blue
    C.PROTO_POCOL: "#D55E00",    # vermillion
    C.PROTO_POW_MT: "#009E73",   # bluish green (secondary comparator only)
}
MARKER = {C.PROTO_POW: "o", C.PROTO_POCOL: "s", C.PROTO_POW_MT: "^"}
NAME = {C.PROTO_POW: "X-PW (traditional PoW)",
        C.PROTO_POCOL: "X-PC (PoCol)",
        C.PROTO_POW_MT: "X-PW-MT (secondary: common template)"}

# --- sequential ramps for ordered quantities (magnitude, not identity) ---
ALPHA_RAMP = ["#c6dbef", "#6baed6", "#2171b5", "#08306b"]     # LP0 -> LP50
N_RAMP = ["#cfe1f2", "#9ecae1", "#4292c6", "#2171b5", "#08306b"]

ALPHA_ORDER = ["LP0", "LP10", "LP25", "LP50"]


def setup():
    plt.rcParams.update({
        "figure.dpi": 130, "savefig.dpi": 300, "font.size": 10.5,
        "axes.grid": True, "grid.alpha": 0.25, "grid.linewidth": 0.6,
        "axes.axisbelow": True, "axes.spines.top": False, "axes.spines.right": False,
        "axes.linewidth": 0.8, "lines.linewidth": 2.0, "lines.markersize": 6.5,
        "legend.frameon": False, "figure.autolayout": True,
    })


def save(fig, stem: str) -> List[str]:
    os.makedirs(C.FIG_DIR, exist_ok=True)
    out = []
    for ext in ("png", "pdf", "svg"):
        p = os.path.join(C.FIG_DIR, f"{stem}.{ext}")
        fig.savefig(p, bbox_inches="tight")
        out.append(p)
    plt.close(fig)
    return out


def _ci(series_by_n: Dict[int, List[float]]):
    ns = sorted(series_by_n)
    mean, lo, hi = [], [], []
    for n in ns:
        d = describe(series_by_n[n])
        mean.append(d["mean"])
        lo.append((d["mean"] - d["ci95_low"]) if d["mean"] is not None else 0.0)
        hi.append((d["ci95_high"] - d["mean"]) if d["mean"] is not None else 0.0)
    return ns, np.array(mean, dtype=float), np.array([lo, hi], dtype=float)


def _by_n(df, col, protocol=None):
    d = df if protocol is None else df[df.protocol == protocol]
    return {int(n): g[col].dropna().tolist() for n, g in d.groupby("N")}


# ==========================================================================
def fig01_hashrate(paths):
    fig, ax = plt.subplots(figsize=(6.2, 4.0))
    ns = list(C.NETWORK_SIZES)
    y = [S21_PRO.aggregate_hashrate_ths(n) / 1000.0 for n in ns]
    ax.plot(ns, y, marker="o", color=COLOR[C.PROTO_POW], label="H(N) = N x 234 TH/s")
    for x, v in zip(ns, y):
        ax.annotate(f"{v:.1f}", (x, v), textcoords="offset points",
                    xytext=(0, 8), ha="center", fontsize=9, color="#333333")
    ax.set_xlabel("Miner population N (S21 Pro units)")
    ax.set_ylabel("Aggregate network hash rate (PH/s)")
    ax.set_title("Aggregate hash rate scales linearly with miner population")
    ax.set_xticks(ns)
    ax.set_ylim(0, max(y) * 1.15)
    ax.legend(loc="upper left")
    paths["fig01_aggregate_hashrate_vs_N"] = save(fig, "fig01_aggregate_hashrate_vs_N")


def fig02_power(paths):
    fig, ax = plt.subplots(figsize=(6.2, 4.0))
    ns = list(C.NETWORK_SIZES)
    y = [S21_PRO.aggregate_active_power_w(n) / 1e6 for n in ns]
    ax.plot(ns, y, marker="o", color=COLOR[C.PROTO_POW],
            label="P(N) = N x 3510 W")
    for x, v in zip(ns, y):
        ax.annotate(f"{v * 1000:.0f} kW", (x, v), textcoords="offset points",
                    xytext=(0, 8), ha="center", fontsize=9, color="#333333")
    ax.set_xlabel("Miner population N (S21 Pro units)")
    ax.set_ylabel("Full-active network power (MW)")
    ax.set_title("Full-active network power scales linearly with miner population")
    ax.set_xticks(ns)
    ax.set_ylim(0, max(y) * 1.15)
    ax.legend(loc="upper left")
    paths["fig02_active_power_vs_N"] = save(fig, "fig02_active_power_vs_N")


def fig03_total_energy(paths, energy):
    fig, ax = plt.subplots(figsize=(6.6, 4.2))
    ns, mean, err = _ci(_by_n(energy[energy.alpha_case == "LP0"], "PoW_energy_kWh"))
    ax.errorbar(ns, mean, yerr=err, marker=MARKER[C.PROTO_POW],
                color=COLOR[C.PROTO_POW], label=NAME[C.PROTO_POW], capsize=3)
    for i, lab in enumerate(ALPHA_ORDER):
        sub = energy[energy.alpha_case == lab]
        ns2, m2, e2 = _ci(_by_n(sub, "PoCol_energy_kWh"))
        ax.errorbar(ns2, m2, yerr=e2, marker=MARKER[C.PROTO_POCOL],
                    color=ALPHA_RAMP[i], linestyle="--", capsize=3,
                    label=f"X-PC {lab} (alpha={ALPHA_CASES[lab]:.2f})")
    ax.set_xlabel("Miner population N (S21 Pro units)")
    ax.set_ylabel("Total network energy over T = 10 000 s (kWh)")
    ax.set_title("Total energy vs miner count\nPoW baseline and PoCol low-power sensitivity cases")
    ax.set_xticks(ns)
    ax.legend(loc="upper left", fontsize=8.5)
    # Honest reading aid: the five curves are indistinguishable at this scale because
    # the PoCol effect is ~0.2 %. The effect is NOT magnified here; see fig05.
    ax.annotate("all five curves coincide at this scale:\n"
                "the PoCol effect is ~0.2 % (see fig05)",
                xy=(0.97, 0.06), xycoords="axes fraction", ha="right", va="bottom",
                fontsize=8.5, color="#555555")
    paths["fig03_total_energy_vs_N"] = save(fig, "fig03_total_energy_vs_N")


def fig04_saving_vs_alpha(paths, energy):
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    alphas = [ALPHA_CASES[a] for a in ALPHA_ORDER]
    for i, n in enumerate(sorted(energy.N.unique())):
        ys, los, his = [], [], []
        for lab in ALPHA_ORDER:
            d = describe(energy[(energy.N == n) & (energy.alpha_case == lab)]
                         .paired_energy_saving_fraction.tolist())
            ys.append(100 * d["mean"])
            los.append(100 * (d["mean"] - d["ci95_low"]))
            his.append(100 * (d["ci95_high"] - d["mean"]))
        ax.errorbar(alphas, ys, yerr=[los, his], marker="o", capsize=3,
                    color=N_RAMP[i], label=f"N = {n}")
    ax.axhline(0.0, color="#888888", linewidth=0.9, linestyle=":")
    ax.set_xlabel("Low-power sensitivity assumption alpha  (P_low = alpha x 3510 W)")
    ax.set_ylabel("Paired energy saving vs PoW (%)")
    ax.set_title("Energy saving vs alpha\n(alpha values are experimental assumptions, not Bitmain modes)")
    ax.set_xticks(alphas)
    ax.legend(title="Miner population", fontsize=9)
    paths["fig04_energy_saving_vs_alpha"] = save(fig, "fig04_energy_saving_vs_alpha")


def fig05_saving_vs_n(paths, energy):
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    for i, lab in enumerate(ALPHA_ORDER):
        sub = energy[energy.alpha_case == lab]
        ns, mean, err = _ci(_by_n(sub, "paired_energy_saving_fraction"))
        ax.errorbar(ns, 100 * mean, yerr=100 * err, marker="o", capsize=3,
                    color=ALPHA_RAMP[i], label=f"{lab} (alpha={ALPHA_CASES[lab]:.2f})")
    ax.axhline(0.0, color="#888888", linewidth=0.9, linestyle=":")
    ax.set_xlabel("Miner population N (S21 Pro units)")
    ax.set_ylabel("Paired energy saving vs PoW (%)")
    ax.set_title("Energy saving vs miner count, by low-power assumption")
    ax.set_xticks(sorted(energy.N.unique()))
    ax.legend(fontsize=9)
    paths["fig05_energy_saving_vs_N"] = save(fig, "fig05_energy_saving_vs_N")


def fig06_evaluations(paths, raw):
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    for proto in C.PRIMARY_PROTOCOLS:
        ns, mean, err = _ci(_by_n(raw, "total_evaluations", proto))
        ax.errorbar(ns, mean / 1e21, yerr=err / 1e21, marker=MARKER[proto],
                    color=COLOR[proto], label=NAME[proto], capsize=3)
    ax.set_xlabel("Miner population N (S21 Pro units)")
    ax.set_ylabel("Total candidate evaluations over T (x10^21 hashes)")
    ax.set_title("Physical hashing work vs miner count")
    ax.set_xticks(sorted(raw.N.unique()))
    ax.legend()
    paths["fig06_evaluations_vs_N"] = save(fig, "fig06_evaluations_vs_N")


def fig07_duplicates(paths, raw, secondary):
    fig, ax = plt.subplots(figsize=(6.6, 4.2))
    for proto in C.PRIMARY_PROTOCOLS:
        ns, mean, err = _ci(_by_n(raw, "duplicate_evaluations", proto))
        ax.errorbar(ns, mean / 1e21, yerr=err / 1e21, marker=MARKER[proto],
                    color=COLOR[proto], label=NAME[proto] + " [primary]", capsize=3)
    if secondary is not None and len(secondary):
        mt = secondary[secondary.protocol == C.PROTO_POW_MT]
        if len(mt):
            ns, mean, err = _ci(_by_n(mt, "duplicate_evaluations"))
            ax.errorbar(ns, mean / 1e21, yerr=err / 1e21,
                        marker=MARKER[C.PROTO_POW_MT], color=COLOR[C.PROTO_POW_MT],
                        linestyle="--", capsize=3,
                        label=NAME[C.PROTO_POW_MT] + " [secondary]")
    ax.set_xlabel("Miner population N (S21 Pro units)")
    ax.set_ylabel("Exact duplicate candidate evaluations (x10^21 hashes)")
    ax.set_title("Exact-input duplicate work vs miner count\n"
                 "identity = (template, candidate index); nonce-value reuse is NOT duplication")
    ax.set_xticks(sorted(raw.N.unique()))
    ax.legend(fontsize=8.5)
    paths["fig07_duplicate_evaluations_vs_N"] = save(fig, "fig07_duplicate_evaluations_vs_N")


def fig08_blocks(paths, raw):
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    for proto in C.PRIMARY_PROTOCOLS:
        ns, mean, err = _ci(_by_n(raw, "accepted_blocks", proto))
        ax.errorbar(ns, mean, yerr=err, marker=MARKER[proto], color=COLOR[proto],
                    label=NAME[proto], capsize=3)
    ax.axhline(C.HORIZON_S / C.TARGET_INTERVAL_S, color="#888888", linestyle=":",
               linewidth=0.9, label="nominal 10 000 s / 600 s")
    ax.set_xlabel("Miner population N (S21 Pro units)")
    ax.set_ylabel("Accepted blocks per 10 000 s run")
    ax.set_title("Accepted block production vs miner count")
    ax.set_xticks(sorted(raw.N.unique()))
    ax.legend(fontsize=9)
    paths["fig08_accepted_blocks_vs_N"] = save(fig, "fig08_accepted_blocks_vs_N")


def fig09_median_interval(paths, raw):
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    for proto in C.PRIMARY_PROTOCOLS:
        ns, mean, err = _ci(_by_n(raw, "median_block_interval", proto))
        ax.errorbar(ns, mean, yerr=err, marker=MARKER[proto], color=COLOR[proto],
                    label=NAME[proto], capsize=3)
    ax.axhline(C.TARGET_INTERVAL_S * np.log(2), color="#888888", linestyle=":",
               linewidth=0.9, label="exponential median = 600 ln2 = 416 s")
    ax.set_xlabel("Miner population N (S21 Pro units)")
    ax.set_ylabel("Median accepted-block interval (s)")
    ax.set_title("Median block interval vs miner count")
    ax.set_xticks(sorted(raw.N.unique()))
    ax.legend(fontsize=9)
    paths["fig09_median_block_interval_vs_N"] = save(fig, "fig09_median_block_interval_vs_N")


def fig10_retention(paths, energy):
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    sub = energy[energy.alpha_case == "LP0"]
    ns, mean, err = _ci(_by_n(sub, "block_retention"))
    ax.errorbar(ns, mean, yerr=err, marker=MARKER[C.PROTO_POCOL],
                color=COLOR[C.PROTO_POCOL], capsize=3,
                label="B_PoCol / B_PoW (paired seeds)")
    ax.axhline(1.0, color="#888888", linestyle=":", linewidth=0.9,
               label="parity with PoW")
    ax.set_xlabel("Miner population N (S21 Pro units)")
    ax.set_ylabel("Block retention  B_PoCol / B_PoW  (ratio)")
    ax.set_title("Block-retention ratio vs miner count\n(undefined pairs are dropped, never set to zero)")
    ax.set_xticks(ns)
    ax.legend(fontsize=9)
    paths["fig10_block_retention_vs_N"] = save(fig, "fig10_block_retention_vs_N")


def fig11_flow(paths, raw):
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    ns, mean, err = _ci(_by_n(raw, "low_power_fraction", C.PROTO_POCOL))
    ax.errorbar(ns, 100 * mean, yerr=100 * err, marker=MARKER[C.PROTO_POCOL],
                color=COLOR[C.PROTO_POCOL], capsize=3,
                label="F_low = sum_i t_low,i / (N T)")
    ax.axhline(0.0, color="#888888", linestyle=":", linewidth=0.9,
               label="X-PW (always ACTIVE): F_low = 0")
    ax.set_xlabel("Miner population N (S21 Pro units)")
    ax.set_ylabel("Miner-time in LOW_POWER (% of N x T)")
    ax.set_title("PoCol low-power miner-time fraction vs miner count")
    ax.set_xticks(ns)
    ax.legend(fontsize=9)
    paths["fig11_low_power_fraction_vs_N"] = save(fig, "fig11_low_power_fraction_vs_N")


def fig12_energy_per_block(paths, energy):
    fig, ax = plt.subplots(figsize=(6.6, 4.2))
    ns, mean, err = _ci(_by_n(energy[energy.alpha_case == "LP0"],
                              "PoW_energy_per_accepted_block_kWh"))
    ax.errorbar(ns, mean, yerr=err, marker=MARKER[C.PROTO_POW],
                color=COLOR[C.PROTO_POW], label=NAME[C.PROTO_POW], capsize=3)
    for i, lab in enumerate(ALPHA_ORDER):
        sub = energy[energy.alpha_case == lab]
        n2, m2, e2 = _ci(_by_n(sub, "PoCol_energy_per_accepted_block_kWh"))
        ax.errorbar(n2, m2, yerr=e2, marker=MARKER[C.PROTO_POCOL], linestyle="--",
                    color=ALPHA_RAMP[i], capsize=3, label=f"X-PC {lab}")
    ax.set_xlabel("Miner population N (S21 Pro units)")
    ax.set_ylabel("Energy per accepted block (kWh/block)")
    ax.set_title("Energy per accepted block vs miner count")
    ax.set_xticks(ns)
    ax.legend(fontsize=8.5)
    paths["fig12_energy_per_block_vs_N"] = save(fig, "fig12_energy_per_block_vs_N")


def fig13_tradeoff(paths, energy):
    fig, ax = plt.subplots(figsize=(6.6, 4.4))
    for i, lab in enumerate(ALPHA_ORDER):
        xs, ys = [], []
        for n in sorted(energy.N.unique()):
            s = energy[(energy.N == n) & (energy.alpha_case == lab)]
            xs.append(100 * describe(s.block_retention.tolist())["mean"])
            ys.append(100 * describe(s.paired_energy_saving_fraction.tolist())["mean"])
        # Scatter only: block retention is not monotonic in N, so connecting the
        # points across N would imply a trajectory that does not exist.
        ax.scatter(xs, ys, s=55, color=ALPHA_RAMP[i], zorder=3,
                   edgecolors="white", linewidths=1.0,
                   label=f"{lab} (alpha={ALPHA_CASES[lab]:.2f})")
        for n, x, y in zip(sorted(energy.N.unique()), xs, ys):
            if lab == "LP0":
                ax.annotate(f"N={n}", (x, y), textcoords="offset points",
                            xytext=(7, 5), fontsize=8, color="#444444")
    ax.axhline(0.0, color="#888888", linestyle=":", linewidth=0.9)
    ax.axvline(100.0, color="#888888", linestyle=":", linewidth=0.9)
    ax.set_xlabel("Block retention B_PoCol / B_PoW (%)")
    ax.set_ylabel("Paired energy saving vs PoW (%)")
    ax.set_title("Energy-saving versus block-retention trade-off\n"
                 "(upper right = strictly better than PoW; each point is one N)")
    ax.legend(fontsize=9)
    paths["fig13_energy_vs_retention_tradeoff"] = save(fig, "fig13_energy_vs_retention_tradeoff")


# ---------------- diagnostics ----------------
def figD1_interval_distribution(paths, intervals):
    fig, axes = plt.subplots(1, 2, figsize=(10.0, 4.0), sharey=True)
    for ax, proto in zip(axes, C.PRIMARY_PROTOCOLS):
        x = intervals[intervals.protocol == proto].interval_s.dropna().values
        ax.hist(x, bins=40, density=True, color=COLOR[proto], alpha=0.75,
                edgecolor="white", linewidth=0.5)
        grid = np.linspace(0, max(x.max(), 1.0), 300)
        ax.plot(grid, np.exp(-grid / C.TARGET_INTERVAL_S) / C.TARGET_INTERVAL_S,
                color="#333333", linewidth=1.6, linestyle="--",
                label="Exp(mean 600 s) reference")
        ax.set_title(NAME[proto], fontsize=10)
        ax.set_xlabel("Accepted-block interval (s)")
        ax.legend(fontsize=8.5)
    axes[0].set_ylabel("Probability density (1/s)")
    fig.suptitle("Diagnostic: accepted-block interval distributions vs the exponential reference",
                 fontsize=11)
    paths["figD1_block_interval_distributions"] = save(
        fig, "figD1_block_interval_distributions")


def figD2_paired_differences(paths, energy):
    fig, ax = plt.subplots(figsize=(7.0, 4.4))
    ns = sorted(energy.N.unique())
    data = [energy[(energy.N == n) & (energy.alpha_case == "LP0")]
            .paired_energy_difference_kWh.values for n in ns]
    bp = ax.boxplot(data, tick_labels=[str(n) for n in ns], showfliers=True,
                    patch_artist=True, widths=0.55)
    for patch in bp["boxes"]:
        patch.set_facecolor(COLOR[C.PROTO_POCOL])
        patch.set_alpha(0.35)
        patch.set_edgecolor(COLOR[C.PROTO_POCOL])
    for med in bp["medians"]:
        med.set_color("#333333")
    ax.axhline(0.0, color="#888888", linestyle=":", linewidth=0.9)
    ax.set_xlabel("Miner population N (S21 Pro units)")
    ax.set_ylabel("Paired energy difference  E_PoCol(LP0) - E_PoW  (kWh)")
    ax.set_title("Diagnostic: per-seed paired energy differences (30 seeds per N, LP0)")
    paths["figD2_paired_energy_differences"] = save(fig, "figD2_paired_energy_differences")


def figD3_exhaustion(paths, raw):
    fig, ax = plt.subplots(figsize=(6.6, 4.2))
    ns = sorted(raw.N.unique())
    obs = []
    for n in ns:
        s = raw[(raw.N == n) & (raw.protocol == C.PROTO_POCOL)]
        e, b = s.epoch_exhaustions.mean(), s.accepted_blocks.mean()
        obs.append(e / (e + b) if (e + b) else np.nan)
    ax.plot(ns, obs, marker="s", color=COLOR[C.PROTO_POCOL],
            label="observed share of epochs ending in domain exhaustion")
    ax.axhline(np.exp(-1.0), color="#333333", linestyle="--", linewidth=1.5,
               label="closed-form prediction  e^-1 = 0.368")
    ax.set_ylim(0, 0.6)
    ax.set_xlabel("Miner population N (S21 Pro units)")
    ax.set_ylabel("Share of epochs ending in global domain exhaustion")
    ax.set_title("Diagnostic: nonce-domain exhaustion rate vs closed-form prediction")
    ax.set_xticks(ns)
    ax.legend(fontsize=9)
    paths["figD3_exhaustion_rate"] = save(fig, "figD3_exhaustion_rate")


def figD4_epoch_sensitivity(paths, secondary, raw):
    sub = secondary[(secondary.protocol == C.PROTO_POCOL)] if secondary is not None else None
    if sub is None or not len(sub):
        return
    fig, ax = plt.subplots(figsize=(6.8, 4.4))
    for i, n in enumerate(sorted(sub.N.unique())):
        pw = raw[(raw.N == n) & (raw.protocol == C.PROTO_POW)].accepted_blocks.mean()
        base = raw[(raw.N == n) & (raw.protocol == C.PROTO_POCOL)]
        taus = [C.EPOCH_SWEEP_S] + sorted(sub[sub.N == n].epoch_sweep_s.unique(),
                                          reverse=True)
        xs, ys = [], []
        for tau in taus:
            s = base if tau == C.EPOCH_SWEEP_S else sub[(sub.N == n) & (sub.epoch_sweep_s == tau)]
            if not len(s):
                continue
            xs.append(100 * s.accepted_blocks.mean() / pw)
            ys.append(100 * s.low_power_fraction.mean())
        ax.plot(xs, ys, marker="o", color=N_RAMP[i * 2], label=f"N = {n}")
        # Stagger annotations per series: the tau = 300 s and 600 s points sit almost
        # on top of each other near F_low = 0, which is the real data, not an artifact.
        for j, (tau, x, y) in enumerate(zip(taus, xs, ys)):
            ax.annotate(f"{int(tau)} s", (x, y), textcoords="offset points",
                        xytext=(6, 5 + 10 * i - 4 * (j % 2)), fontsize=8,
                        color=N_RAMP[i * 2] if i else "#8fa8c0")
    ax.margins(x=0.10, y=0.12)
    ax.set_xlabel("Block retention B_PoCol / B_PoW (%)")
    ax.set_ylabel("Low-power miner-time fraction F_low (%)")
    ax.set_title("Secondary S2: PoCol epoch-allocation sensitivity\n"
                 "labels give tau_epoch; 600 s is the frozen primary setting")
    ax.legend(fontsize=9)
    paths["figD4_epoch_allocation_sensitivity"] = save(
        fig, "figD4_epoch_allocation_sensitivity")


# ==========================================================================
def build_all(raw: pd.DataFrame, energy: pd.DataFrame, intervals: pd.DataFrame,
              secondary: pd.DataFrame = None) -> Dict[str, List[str]]:
    setup()
    paths: Dict[str, List[str]] = {}
    fig01_hashrate(paths)
    fig02_power(paths)
    fig03_total_energy(paths, energy)
    fig04_saving_vs_alpha(paths, energy)
    fig05_saving_vs_n(paths, energy)
    fig06_evaluations(paths, raw)
    fig07_duplicates(paths, raw, secondary)
    fig08_blocks(paths, raw)
    fig09_median_interval(paths, raw)
    fig10_retention(paths, energy)
    fig11_flow(paths, raw)
    fig12_energy_per_block(paths, energy)
    fig13_tradeoff(paths, energy)
    figD1_interval_distribution(paths, intervals)
    figD2_paired_differences(paths, energy)
    figD3_exhaustion(paths, raw)
    figD4_epoch_sensitivity(paths, secondary, raw)
    return paths
