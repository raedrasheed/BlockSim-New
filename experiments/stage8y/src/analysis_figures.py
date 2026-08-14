"""Stage 8Y — publication-quality figures (PNG + PDF + SVG).

Conventions
-----------
* Axes are always labelled with units; there are no dual-axis plots.
* Categorical colour follows the *entity* (protocol), assigned in a fixed order and
  never cycled or repainted when a filter changes the series count. The palette is
  the colour-vision-deficiency-safe Okabe-Ito set, ordered so that every adjacent
  pair clears the CVD separation check (worst adjacent deltaE 9.6 deutan / 8.5
  tritan, normal-vision floor 20.0). Identity is additionally carried by marker
  shape and by an always-present legend, so it is never colour-alone; the CSV/
  Markdown tables provide the required table view.
* Ordered quantities (alpha, active fraction, N) use single-hue sequential ramps.
* Error bars are 95 % confidence intervals across the 30 paired seeds.
* Axes are linear and are not truncated to exaggerate differences. Reference lines
  mark the preregistered thresholds rather than rescaling the data around them.
"""

from __future__ import annotations

import os
from typing import Dict, List

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from experiments.stage8y.config import stage8y_config as C
from experiments.stage8y.src.analysis_stats import describe

COLOR = {
    C.POW: "#0072B2", C.P0_ALL: "#D55E00", C.P3_ENERGY: "#009E73",
    C.P4_RESERVE: "#E69F00", C.P1_EQUAL: "#CC79A7", C.P2_HASHPROP: "#56B4E9",
    C.POW_CT: "#666666",
}
MARKER = {C.POW: "o", C.P0_ALL: "s", C.P3_ENERGY: "^", C.P4_RESERVE: "D",
          C.P1_EQUAL: "v", C.P2_HASHPROP: "P", C.POW_CT: "X"}
NAME = {
    C.POW: "PoW (traditional)", C.P0_ALL: "PoCol-All", C.P3_ENERGY: "PoCol EnergyAware",
    C.P4_RESERVE: "PoCol AdaptiveReserve", C.P1_EQUAL: "PoCol Equal-range",
    C.P2_HASHPROP: "PoCol Hash-proportional", C.POW_CT: "Common-Template PoW [2ndry]",
}
ALPHA_ORDER = ["alpha_0", "alpha_005", "alpha_010", "alpha_025", "alpha_050"]
ALPHA_RAMP = ["#c6dbef", "#9ecae1", "#4292c6", "#2171b5", "#08306b"]
COMP_RAMP = {"H0": "#cfe1f2", "H1": "#9ecae1", "H2": "#4292c6", "H3": "#2171b5",
             "H4": "#08306b"}
N_RAMP = {100: "#c6dbef", 200: "#9ecae1", 300: "#4292c6", 400: "#2171b5", 500: "#08306b"}


def setup():
    plt.rcParams.update({
        "figure.dpi": 130, "savefig.dpi": 300, "font.size": 10.5,
        "axes.grid": True, "grid.alpha": 0.25, "grid.linewidth": 0.6,
        "axes.axisbelow": True, "axes.spines.top": False, "axes.spines.right": False,
        "axes.linewidth": 0.8, "lines.linewidth": 2.0, "lines.markersize": 6.5,
        "legend.frameon": False, "figure.autolayout": True,
    })


def save(fig, stem: str) -> str:
    os.makedirs(C.FIG_DIR, exist_ok=True)
    for ext in ("png", "pdf", "svg"):
        fig.savefig(os.path.join(C.FIG_DIR, f"{stem}.{ext}"), bbox_inches="tight")
    plt.close(fig)
    return stem


def _ci(vals):
    d = describe(list(vals))
    if d["mean"] is None:
        return None, 0.0, 0.0
    return d["mean"], d["mean"] - d["ci95_low"], d["ci95_high"] - d["mean"]


# ==========================================================================
def fig01_pareto(paths, energy, alpha_case="alpha_010"):
    fig, ax = plt.subplots(figsize=(7.4, 5.4))
    sub = energy[energy.alpha_case == alpha_case]
    for proto in sorted(sub.protocol.unique()):
        xs, ys = [], []
        for (_c, _n), g in sub[sub.protocol == proto].groupby(["composition", "N"]):
            xs.append(100 * g.EnergySaving.mean())
            ys.append(100 * g.BlockRetention.mean())
        ax.scatter(xs, ys, s=70, color=COLOR[proto], marker=MARKER[proto],
                   edgecolors="white", linewidths=1.0, zorder=3, label=NAME[proto])
    ax.axvline(50, color="#333333", linestyle="--", linewidth=1.4)
    ax.axhline(90, color="#888888", linestyle=":", linewidth=1.2)
    ax.axhline(95, color="#888888", linestyle="-.", linewidth=1.2)
    ax.annotate(">50 % saving", xy=(50, 4), xytext=(52, 4), fontsize=9, color="#333333")
    ax.annotate("90 % retention", xy=(2, 90), xytext=(2, 91), fontsize=9, color="#555555")
    ax.annotate("95 % retention", xy=(2, 95), xytext=(2, 96), fontsize=9, color="#555555")
    ax.set_xlim(-5, 100)
    ax.set_ylim(0, 108)
    ax.set_xlabel("Energy saving vs matched PoW (%)")
    ax.set_ylabel("Block retention  B_PoCol / B_PoW  (%)")
    ax.set_title(f"Energy saving vs block retention ({alpha_case})\n"
                 "target region is upper right of both reference lines")
    ax.legend(fontsize=8.5, loc="lower left")
    paths.append(save(fig, f"fig01_pareto_{alpha_case}"))


def fig02_saving_by_policy(paths, energy):
    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    protos = [p for p in C.PRIMARY_PROTOCOLS if p != C.POW]
    width = 0.8 / len(ALPHA_ORDER)
    x = np.arange(len(protos))
    for i, ac in enumerate(ALPHA_ORDER):
        means, errs = [], [[], []]
        for p in protos:
            m, lo, hi = _ci(energy[(energy.protocol == p)
                                   & (energy.alpha_case == ac)].EnergySaving)
            means.append(100 * (m or 0.0))
            errs[0].append(100 * lo)
            errs[1].append(100 * hi)
        ax.bar(x + i * width - 0.4 + width / 2, means, width * 0.92, yerr=errs,
               capsize=2.5, color=ALPHA_RAMP[i],
               label=f"{ac} (α={C.ALPHA_CASES[ac]:.2f})")
    ax.axhline(50, color="#333333", linestyle="--", linewidth=1.4,
               label="50 % threshold")
    ax.set_xticks(x)
    ax.set_xticklabels([NAME[p] for p in protos], fontsize=9)
    ax.set_ylabel("Energy saving vs matched PoW (%)")
    ax.set_title("Energy saving by PoCol policy and low-power assumption\n"
                 "(α values are model assumptions, not vendor modes)")
    ax.legend(fontsize=8.5, ncol=2)
    paths.append(save(fig, "fig02_saving_by_policy"))


def fig03_retention_by_policy(paths, energy):
    fig, ax = plt.subplots(figsize=(6.8, 4.4))
    protos = [p for p in C.PRIMARY_PROTOCOLS if p != C.POW]
    sub = energy[energy.alpha_case == "alpha_0"]
    means, errs = [], [[], []]
    for p in protos:
        m, lo, hi = _ci(sub[sub.protocol == p].BlockRetention)
        means.append(100 * (m or 0.0))
        errs[0].append(100 * lo)
        errs[1].append(100 * hi)
    ax.bar(range(len(protos)), means, 0.6, yerr=errs, capsize=3,
           color=[COLOR[p] for p in protos])
    ax.axhline(90, color="#888888", linestyle=":", linewidth=1.2, label="90 %")
    ax.axhline(95, color="#888888", linestyle="-.", linewidth=1.2, label="95 %")
    ax.axhline(100, color="#333333", linestyle="-", linewidth=0.8, label="PoW parity")
    ax.set_xticks(range(len(protos)))
    ax.set_xticklabels([NAME[p] for p in protos], fontsize=9)
    ax.set_ylabel("Block retention (%)")
    ax.set_ylim(0, 108)
    ax.set_title("Block retention by PoCol policy (all compositions and N pooled)")
    ax.legend(fontsize=9)
    paths.append(save(fig, "fig03_retention_by_policy"))


def fig04_energy_per_block(paths, energy):
    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    sub = energy[energy.alpha_case == "alpha_010"]
    protos = [C.POW] + [p for p in C.PRIMARY_PROTOCOLS if p != C.POW]
    for i, p in enumerate(protos):
        ns, ms, es = [], [], [[], []]
        for n in sorted(sub.N.unique()):
            g = sub[(sub.N == n)] if p == C.POW else sub[(sub.N == n)
                                                         & (sub.protocol == p)]
            col = ("PoW_energy_per_block_kWh" if p == C.POW
                   else "PoCol_energy_per_block_kWh")
            m, lo, hi = _ci(g[col])
            ns.append(n)
            ms.append(m)
            es[0].append(lo)
            es[1].append(hi)
        ax.errorbar(ns, ms, yerr=es, marker=MARKER[p], color=COLOR[p], capsize=3,
                    label=NAME[p])
    ax.set_xlabel("Miner population N")
    ax.set_ylabel("Energy per accepted block (kWh/block)")
    ax.set_title("Energy per accepted block (α = 0.10)")
    ax.set_xticks(sorted(sub.N.unique()))
    ax.legend(fontsize=9)
    paths.append(save(fig, "fig04_energy_per_block"))


def fig05_intervals(paths, raw):
    fig, axes = plt.subplots(1, 2, figsize=(11.0, 4.4), sharey=True)
    for ax, col, title in ((axes[0], "mean_block_interval", "Mean"),
                           (axes[1], "median_block_interval", "Median")):
        for p in (C.POW,) + tuple(x for x in C.PRIMARY_PROTOCOLS if x != C.POW):
            ns, ms, es = [], [], [[], []]
            for n in sorted(raw.N.unique()):
                m, lo, hi = _ci(raw[(raw.N == n) & (raw.protocol == p)][col])
                ns.append(n)
                ms.append(m)
                es[0].append(lo)
                es[1].append(hi)
            ax.errorbar(ns, ms, yerr=es, marker=MARKER[p], color=COLOR[p], capsize=3,
                        label=NAME[p])
        ax.axhline(C.TARGET_INTERVAL_S, color="#333333", linestyle=":", linewidth=1.0)
        ax.set_xlabel("Miner population N")
        ax.set_title(f"{title} accepted-block interval")
        ax.set_xticks(sorted(raw.N.unique()))
    axes[0].set_ylabel("Accepted-block interval (s)")
    axes[0].legend(fontsize=8.5)
    fig.suptitle("Block latency vs miner population (dotted line = 600 s target)",
                 fontsize=11)
    paths.append(save(fig, "fig05_block_intervals"))


def _trace_panel(ax, traces, col, ylabel, title):
    for p in sorted(traces.protocol.unique()):
        g = traces[traces.protocol == p].sort_values("t")
        ax.step(g.t, 100 * g[col], where="post", color=COLOR[p], label=NAME[p],
                linewidth=1.6)
    ax.set_xlabel("Simulation time (s)")
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.set_ylim(-4, 108)


def fig06_07_08_traces(paths, traces):
    if traces is None or not len(traces):
        return
    sel = traces[(traces.composition == "H2") & (traces.N == 300)]
    if not len(sel):
        return
    fig, ax = plt.subplots(figsize=(8.0, 4.4))
    _trace_panel(ax, sel, "h_active_fraction",
                 "Active hash capacity (% of H_N)",
                 "Active hash fraction over time (H2, N = 300, seed 1)")
    ax.legend(fontsize=8.5, ncol=2)
    paths.append(save(fig, "fig06_active_hash_fraction_over_time"))

    fig, ax = plt.subplots(figsize=(8.0, 4.4))
    _trace_panel(ax, sel, "p_drawn_fraction",
                 "Power drawn (% of P_N)",
                 "Active power fraction over time (H2, N = 300, seed 1)")
    ax.legend(fontsize=8.5, ncol=2)
    paths.append(save(fig, "fig07_active_power_fraction_over_time"))

    res = sel[sel.protocol == C.P4_RESERVE].sort_values("t")
    if len(res):
        fig, ax = plt.subplots(figsize=(8.0, 4.4))
        ax.step(res.t, 100 * res.h_active_fraction, where="post",
                color=COLOR[C.P4_RESERVE], label="active hash capacity")
        ax.step(res.t, 100 * res.p_drawn_fraction, where="post",
                color="#333333", linestyle="--", linewidth=1.3,
                label="power drawn")
        for s, frac in enumerate(C.CONF_RESERVE_SCHEDULE):
            ax.axhline(100 * frac, color="#bbbbbb", linestyle=":", linewidth=0.9)
            ax.annotate(f"stage {s}: {int(100*frac)} %", xy=(0, 100 * frac),
                        xytext=(5, 100 * frac + 1), fontsize=8, color="#777777")
        ax.set_xlabel("Simulation time (s)")
        ax.set_ylabel("Fraction of installed capacity / power (%)")
        ax.set_title("Adaptive-reserve activation trajectory (H2, N = 300, seed 1)")
        ax.set_ylim(-4, 112)
        ax.legend(fontsize=9)
        paths.append(save(fig, "fig08_reserve_activation_trajectory"))


def fig09_10_residence(paths, raw):
    devs = [d for d in ("S21PRO", "S19XP", "S19JPRO")
            if f"participation_share_{d}" in raw.columns]
    protos = [p for p in C.PRIMARY_PROTOCOLS if p != C.POW]
    sub = raw[(raw.composition == "H4")]
    if len(sub):
        fig, ax = plt.subplots(figsize=(7.4, 4.4))
        x = np.arange(len(protos))
        w = 0.8 / max(1, len(devs))
        ramp = ["#08306b", "#4292c6", "#c6dbef"]
        for i, d in enumerate(devs):
            vals = [100 * (1.0 - sub[sub.protocol == p][f"active_time_share_{d}"].mean())
                    for p in protos]
            ax.bar(x + i * w - 0.4 + w / 2, vals, w * 0.9, color=ramp[i % len(ramp)],
                   label=d)
        ax.set_xticks(x)
        ax.set_xticklabels([NAME[p] for p in protos], fontsize=9)
        ax.set_ylabel("Time parked (LOW_POWER + STANDBY) (% of own time)")
        ax.set_title("Parked residence by hardware class (composition H4)")
        ax.legend(fontsize=9, title="device")
        paths.append(save(fig, "fig09_residence_by_hardware"))

    fig, ax = plt.subplots(figsize=(7.4, 4.4))
    x = np.arange(len(protos))
    for i, (col, lab, c) in enumerate((("F_parked_minertime", "miner-time", "#9ecae1"),
                                       ("F_parked_power_weighted", "power-weighted",
                                        "#08306b"))):
        vals = [100 * raw[raw.protocol == p][col].mean() for p in protos]
        ax.bar(x + i * 0.4 - 0.2, vals, 0.36, color=c, label=lab)
    ax.set_xticks(x)
    ax.set_xticklabels([NAME[p] for p in protos], fontsize=9)
    ax.set_ylabel("Parked residence (%)")
    ax.set_title("Parked residence: miner-time vs power-weighted\n"
                 "(50 % of miners is not 50 % of electrical capacity)")
    ax.legend(fontsize=9)
    paths.append(save(fig, "fig10_power_weighted_residence"))


def fig11_saving_vs_alpha(paths, energy):
    fig, ax = plt.subplots(figsize=(6.8, 4.4))
    alphas = [C.ALPHA_CASES[a] for a in ALPHA_ORDER]
    for p in [x for x in C.PRIMARY_PROTOCOLS if x != C.POW]:
        ys, es = [], [[], []]
        for a in ALPHA_ORDER:
            m, lo, hi = _ci(energy[(energy.protocol == p)
                                   & (energy.alpha_case == a)].EnergySaving)
            ys.append(100 * (m or 0.0))
            es[0].append(100 * lo)
            es[1].append(100 * hi)
        ax.errorbar(alphas, ys, yerr=es, marker=MARKER[p], color=COLOR[p], capsize=3,
                    label=NAME[p])
    ax.axhline(50, color="#333333", linestyle="--", linewidth=1.4, label="50 % threshold")
    ax.set_xlabel("α = P_low / P_active  (model assumption, not a vendor mode)")
    ax.set_ylabel("Energy saving vs matched PoW (%)")
    ax.set_title("Energy saving vs the low-power assumption")
    ax.set_xticks(alphas)
    ax.legend(fontsize=9)
    paths.append(save(fig, "fig11_saving_vs_alpha"))


def fig12_saving_vs_wake(paths, sec_energy, sec_raw):
    w = sec_energy[sec_energy.tag.astype(str).str.startswith("wake")]
    if not len(w):
        return
    lookup = {t: sec_raw[sec_raw.tag == t].wake_s.iloc[0] for t in w.tag.unique()}
    fig, ax = plt.subplots(figsize=(6.8, 4.4))
    for i, a in enumerate(ALPHA_ORDER):
        pts = sorted(((lookup[t], g.EnergySaving.mean())
                      for t, g in w[w.alpha_case == a].groupby("tag")))
        ax.plot([p[0] for p in pts], [100 * p[1] for p in pts], marker="o",
                color=ALPHA_RAMP[i], label=f"{a} (α={C.ALPHA_CASES[a]:.2f})")
    ax.axhline(50, color="#333333", linestyle="--", linewidth=1.4)
    ax.set_xlabel("Wake delay t_wake (s)")
    ax.set_ylabel("Energy saving vs matched PoW (%)")
    ax.set_title("Energy saving vs wake delay (AdaptiveReserve, H2, N = 300)\n"
                 "waking draws full active power")
    ax.legend(fontsize=8.5)
    paths.append(save(fig, "fig12_saving_vs_wake_delay"))


def fig13_saving_vs_active_fraction(paths, sec_energy, sec_raw):
    sel = sec_energy[sec_energy.tag.astype(str).str.startswith("sel_")]
    if not len(sel):
        return
    fig, ax = plt.subplots(figsize=(7.4, 4.8))
    rules = sorted({t.split("_rh")[0].replace("sel_", "") for t in sel.tag.unique()})
    cmap = {r: c for r, c in zip(rules, ["#0072B2", "#D55E00", "#009E73", "#E69F00"])}
    for rule in rules:
        pts = []
        for t, g in sel[sel.alpha_case == "alpha_010"].groupby("tag"):
            if not t.startswith(f"sel_{rule}_rh"):
                continue
            rh = sec_raw[sec_raw.tag == t].r_hash_initial.mean()
            pts.append((rh, g.EnergySaving.mean(), g.BlockRetention.mean()))
        pts.sort()
        if pts:
            ax.plot([100 * p[0] for p in pts], [100 * p[1] for p in pts], marker="o",
                    color=cmap.get(rule, "#666666"), label=rule)
    ax.axhline(50, color="#333333", linestyle="--", linewidth=1.4)
    ax.set_xlabel("Initial active hash fraction r_H (%)")
    ax.set_ylabel("Energy saving vs matched PoW (%)  [α = 0.10]")
    ax.set_title("Energy saving vs initial active hash fraction, by selection rule\n"
                 "(H2, N = 300)")
    ax.legend(fontsize=8.5, title="selection rule")
    paths.append(save(fig, "fig13_saving_vs_active_hash_fraction"))


def fig14_15_composition(paths, energy):
    for stem, col, ylab, thr in (
            ("fig14_composition_vs_saving", "EnergySaving",
             "Energy saving vs matched PoW (%)", 50),
            ("fig15_composition_vs_retention", "BlockRetention",
             "Block retention (%)", 90)):
        fig, ax = plt.subplots(figsize=(7.2, 4.4))
        comps = sorted(energy.composition.unique())
        protos = [p for p in C.PRIMARY_PROTOCOLS if p != C.POW]
        x = np.arange(len(comps))
        w = 0.8 / len(protos)
        sub = energy[energy.alpha_case == ("alpha_010" if col == "EnergySaving"
                                           else "alpha_0")]
        for i, p in enumerate(protos):
            ys, es = [], [[], []]
            for c in comps:
                m, lo, hi = _ci(sub[(sub.composition == c)
                                    & (sub.protocol == p)][col])
                ys.append(100 * (m or 0.0))
                es[0].append(100 * lo)
                es[1].append(100 * hi)
            ax.bar(x + i * w - 0.4 + w / 2, ys, w * 0.9, yerr=es, capsize=2.5,
                   color=COLOR[p], label=NAME[p])
        ax.axhline(thr, color="#333333", linestyle="--", linewidth=1.3)
        ax.set_xticks(x)
        ax.set_xticklabels(comps)
        ax.set_xlabel("Hardware composition")
        ax.set_ylabel(ylab)
        ax.set_title(f"{ylab.split('(')[0].strip()} by hardware composition")
        ax.legend(fontsize=8.5)
        paths.append(save(fig, stem))


def fig16_duplicates(paths, raw, sec_raw):
    fig, ax = plt.subplots(figsize=(7.6, 4.6))
    protos = [C.POW] + list(C.PRIMARY_PROTOCOLS[1:])
    frames = [raw]
    if sec_raw is not None and len(sec_raw):
        frames.append(sec_raw[sec_raw.protocol == C.POW_CT])
        protos = protos + [C.POW_CT]
    allr = pd.concat(frames, ignore_index=True)
    x = np.arange(len(protos))
    dup = [100 * allr[allr.protocol == p].duplicate_ratio.mean() for p in protos]
    reuse = [100 * allr[allr.protocol == p].nonce_value_reuse_ratio.mean()
             for p in protos]
    ax.bar(x - 0.2, dup, 0.36, color="#D55E00", label="exact-input duplicate ratio")
    ax.bar(x + 0.2, reuse, 0.36, color="#56B4E9", label="nonce-value reuse ratio")
    ax.set_xticks(x)
    ax.set_xticklabels([NAME[p] for p in protos], fontsize=8, rotation=12)
    ax.set_ylabel("Fraction of evaluations (%)")
    ax.set_title("Exact-input duplication vs nonce-value reuse\n"
                 "identity = (template, candidate index); equal nonces under different "
                 "templates are NOT duplicates")
    ax.legend(fontsize=9)
    paths.append(save(fig, "fig16_duplicates_vs_nonce_reuse"))


def fig17_18_scaling(paths, raw, energy):
    fig, ax = plt.subplots(figsize=(6.8, 4.4))
    for p in (C.POW,) + tuple(x for x in C.PRIMARY_PROTOCOLS if x != C.POW):
        ns, ms, es = [], [], [[], []]
        for n in sorted(raw.N.unique()):
            m, lo, hi = _ci(raw[(raw.N == n) & (raw.protocol == p)].total_evaluations)
            ns.append(n)
            ms.append((m or 0) / 1e21)
            es[0].append(lo / 1e21)
            es[1].append(hi / 1e21)
        ax.errorbar(ns, ms, yerr=es, marker=MARKER[p], color=COLOR[p], capsize=3,
                    label=NAME[p])
    ax.set_xlabel("Miner population N")
    ax.set_ylabel("Total candidate evaluations (×10²¹)")
    ax.set_title("Physical hashing work vs miner population")
    ax.set_xticks(sorted(raw.N.unique()))
    ax.legend(fontsize=9)
    paths.append(save(fig, "fig17_work_scaling"))

    fig, ax = plt.subplots(figsize=(6.8, 4.4))
    sub = energy[energy.alpha_case == "alpha_010"]
    ns = sorted(sub.N.unique())
    m0 = [sub[sub.N == n].PoW_energy_kWh.mean() for n in ns]
    ax.plot(ns, m0, marker=MARKER[C.POW], color=COLOR[C.POW], label=NAME[C.POW])
    for p in [x for x in C.PRIMARY_PROTOCOLS if x != C.POW]:
        ms = [sub[(sub.N == n) & (sub.protocol == p)].PoCol_energy_kWh.mean()
              for n in ns]
        ax.plot(ns, ms, marker=MARKER[p], color=COLOR[p], label=NAME[p])
    ax.set_xlabel("Miner population N")
    ax.set_ylabel("Total network energy over 10 000 s (kWh)")
    ax.set_title("Energy scaling with miner population (α = 0.10)")
    ax.set_xticks(ns)
    ax.legend(fontsize=9)
    paths.append(save(fig, "fig18_energy_scaling"))


def fig19_selectivity(paths, raw):
    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    protos = [p for p in C.PRIMARY_PROTOCOLS if p != C.POW]
    comps = sorted(raw.composition.unique())
    x = np.arange(len(protos))
    w = 0.8 / len(comps)
    for i, c in enumerate(comps):
        ys = [raw[(raw.protocol == p) & (raw.composition == c)].SelectivityGain.mean()
              for p in protos]
        ax.bar(x + i * w - 0.4 + w / 2, ys, w * 0.9, color=COMP_RAMP.get(c, "#4292c6"),
               label=c)
    ax.axhline(1.0, color="#333333", linestyle="--", linewidth=1.3,
               label="1.0 = capacity-neutral parking")
    ax.set_xticks(x)
    ax.set_xticklabels([NAME[p] for p in protos], fontsize=9)
    ax.set_ylabel("SelectivityGain = PowerRemoved / CapacityRemoved")
    ax.set_title("Selectivity: does the policy park electrically expensive capacity?\n"
                 "> 1 parks expensive capacity; < 1 parks cheap capacity")
    ax.legend(fontsize=8.5, title="composition")
    paths.append(save(fig, "fig19_selectivity_gain"))


def fig20_longhorizon(paths, lon_energy, energy):
    if lon_energy is None or not len(lon_energy):
        return
    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    protos = [p for p in C.PRIMARY_PROTOCOLS if p != C.POW]
    comps = sorted(lon_energy.composition.unique())
    labels, short, long_, es_s, es_l = [], [], [], [[], []], [[], []]
    for c in comps:
        for p in protos:
            g_l = lon_energy[(lon_energy.composition == c) & (lon_energy.protocol == p)
                             & (lon_energy.alpha_case == "alpha_010")]
            g_s = energy[(energy.composition == c) & (energy.protocol == p)
                         & (energy.N == C.LONG_HORIZON_N)
                         & (energy.alpha_case == "alpha_010")]
            if not len(g_l) or not len(g_s):
                continue
            ms, lo, hi = _ci(g_s.EnergySaving)
            ml, lo2, hi2 = _ci(g_l.EnergySaving)
            labels.append(f"{c}\n{NAME[p].split()[-1]}")
            short.append(100 * ms)
            long_.append(100 * ml)
            es_s[0].append(100 * lo)
            es_s[1].append(100 * hi)
            es_l[0].append(100 * lo2)
            es_l[1].append(100 * hi2)
    x = np.arange(len(labels))
    ax.bar(x - 0.2, short, 0.36, yerr=es_s, capsize=2.5, color="#9ecae1",
           label="T = 10 000 s")
    ax.bar(x + 0.2, long_, 0.36, yerr=es_l, capsize=2.5, color="#08306b",
           label="T = 100 000 s")
    ax.axhline(50, color="#333333", linestyle="--", linewidth=1.3)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=8)
    ax.set_ylabel("Energy saving vs matched PoW (%)  [α = 0.10]")
    ax.set_title("Long-horizon confirmation (N = 300)")
    ax.legend(fontsize=9)
    paths.append(save(fig, "fig20_long_horizon_validation"))


# ==========================================================================
def build_all(raw, energy, traces, sec_raw, sec_energy, lon_raw, lon_energy) -> List[str]:
    setup()
    paths: List[str] = []
    fig01_pareto(paths, energy, "alpha_010")
    fig01_pareto(paths, energy, "alpha_0")
    fig02_saving_by_policy(paths, energy)
    fig03_retention_by_policy(paths, energy)
    fig04_energy_per_block(paths, energy)
    fig05_intervals(paths, raw)
    fig06_07_08_traces(paths, traces)
    fig09_10_residence(paths, raw)
    fig11_saving_vs_alpha(paths, energy)
    if sec_energy is not None and len(sec_energy):
        fig12_saving_vs_wake(paths, sec_energy, sec_raw)
        fig13_saving_vs_active_fraction(paths, sec_energy, sec_raw)
    fig14_15_composition(paths, energy)
    fig16_duplicates(paths, raw, sec_raw)
    fig17_18_scaling(paths, raw, energy)
    fig19_selectivity(paths, raw)
    fig20_longhorizon(paths, lon_energy, energy)
    return paths
