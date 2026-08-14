"""Stage 8X-NR — the 13 required figures + the conceptual diagram.

Same conventions as the earlier stages' figure pipelines: each figure is saved
as PNG, PDF and SVG under experiments/stage8xnr/figures/, conservative axes,
explicit units, log scales only where the data spans decades.
"""

from __future__ import annotations

import csv
import os
import statistics
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from experiments.stage8xnr.config.nr_config import (
    ALPHA_CASES, ARM_CONV_OFF, ARM_CONV_ZERO, ARM_MT_OFF, ARM_MT_ZERO, ARM_PC,
    ARMS, N_GRID, S_NONCE, pocol_partition,
)

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(HERE, "outputs")
FIG = os.path.join(HERE, "figures")

COLORS = {ARM_CONV_ZERO: "#8c6bb1", ARM_CONV_OFF: "#2c7fb8",
          ARM_MT_ZERO: "#fdae61", ARM_MT_OFF: "#d7301f", ARM_PC: "#238b45"}
SHORT = {ARM_CONV_ZERO: "PW-CONV-ZERO", ARM_CONV_OFF: "PW-CONV-OFFSET",
         ARM_MT_ZERO: "PW-MT-ZERO", ARM_MT_OFF: "PW-MT-OFFSET", ARM_PC: "PC"}


def _rows(name):
    with open(os.path.join(OUT, name)) as fh:
        return list(csv.DictReader(fh))


def _cell(rows, arm, n, col):
    return [float(r[col]) for r in rows
            if r["arm"] == arm and int(r["N"]) == n and r.get(col, "") != ""]


def _save(fig, stem):
    os.makedirs(FIG, exist_ok=True)
    for ext in ("png", "pdf", "svg"):
        fig.savefig(os.path.join(FIG, f"{stem}.{ext}"),
                    dpi=150 if ext == "png" else None, bbox_inches="tight")
    plt.close(fig)


def _line_by_arm(runs, col, ylabel, title, stem, arms=ARMS, logy=False,
                 hline=None, hlabel=None):
    fig, ax = plt.subplots(figsize=(7, 4.4))
    for arm in arms:
        ys = [statistics.mean(_cell(runs, arm, n, col)) for n in N_GRID]
        ax.plot(N_GRID, ys, "o-", color=COLORS[arm], label=SHORT[arm])
    if hline is not None:
        ax.axhline(hline, ls="--", color="grey", lw=1, label=hlabel)
    ax.set_xlabel("network size N (miners)")
    ax.set_ylabel(ylabel)
    ax.set_title(title, fontsize=10)
    if logy:
        ax.set_yscale("log")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8)
    _save(fig, stem)


def main():
    runs = _rows("stage8x_nr_physical_runs.csv")
    energy = _rows("stage8x_nr_energy_sensitivity.csv")

    # 1 — nonce reuse fraction vs N (round scope + epoch scope)
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 4.2))
    for arm in ARMS:
        a1.plot(N_GRID, [statistics.mean(
            _cell(runs, arm, n, "mean_round_rho_nonce")) for n in N_GRID],
            "o-", color=COLORS[arm], label=SHORT[arm])
        a2.plot(N_GRID, [statistics.mean(
            _cell(runs, arm, n, "epoch_rho_nonce")) for n in N_GRID],
            "o-", color=COLORS[arm], label=SHORT[arm])
    a1.set_title("round scope (saturates: every miner sweeps 2^32\n"
                 "every 18.4 µs; repetition-based ρ)", fontsize=9)
    a2.set_title("template-epoch scope (discriminating scope)", fontsize=9)
    for a in (a1, a2):
        a.set_xlabel("N"); a.set_ylabel(r"$\rho_{nonce}$"); a.grid(alpha=0.3)
    a1.set_ylim(0.999999985, 1.0000000005)
    a2.set_ylim(-0.05, 1.05)
    a2.legend(fontsize=8)
    _save(fig, "fignr01_nonce_reuse_fraction_vs_N")

    # 2 — unique nonce-value fraction vs N (U/C, round scope)
    fig, ax = plt.subplots(figsize=(7, 4.4))
    for arm in ARMS:
        ys = []
        for n in N_GRID:
            u = statistics.mean(_cell(runs, arm, n, "run_U_nonce"))
            c = statistics.mean(_cell(runs, arm, n, "run_C_nonce")) \
                if _cell(runs, arm, n, "run_C_nonce") else None
            c = statistics.mean(_cell(runs, arm, n, "C_total_evaluations"))
            ys.append(u / c)
        ax.plot(N_GRID, ys, "o-", color=COLORS[arm], label=SHORT[arm])
    ax.set_yscale("log")
    ax.set_xlabel("network size N (miners)")
    ax.set_ylabel(r"$U_{nonce}/C_{nonce}$ (global-run scope)")
    ax.set_title("Unique nonce-value fraction: 2^32 values / total evaluations",
                 fontsize=10)
    ax.grid(alpha=0.3, which="both")
    ax.legend(fontsize=8)
    _save(fig, "fignr02_unique_nonce_fraction_vs_N")

    # 3 — mean pairwise nonce overlap vs N (round + subsweep)
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 4.2))
    for arm in ARMS:
        a1.plot(N_GRID, [statistics.mean(
            _cell(runs, arm, n, "mean_round_O_mean")) for n in N_GRID],
            "o-", color=COLORS[arm], label=SHORT[arm])
        a2.plot(N_GRID, [statistics.mean(
            _cell(runs, arm, n, "mean_subsweep_O_mean")) for n in N_GRID],
            "o-", color=COLORS[arm], label=SHORT[arm])
    a1.set_title("round scope: PoW pairs share all 2^32 values;\nPoCol pairs share none", fontsize=9)
    a2.set_title("sub-sweep window W=⌊S/2N⌋ (pre-saturation)", fontsize=9)
    for a in (a1, a2):
        a.set_xlabel("N"); a.set_ylabel(r"mean $O_{ij}$ (nonce values)")
        a.grid(alpha=0.3)
        a.set_yscale("symlog")
    a1.legend(fontsize=8)
    _save(fig, "fignr03_pairwise_overlap_vs_N")

    # 4 — nonce reuse vs exact-input duplication (epoch scope scatter)
    fig, ax = plt.subplots(figsize=(6.4, 5.2))
    for arm in ARMS:
        xs = [statistics.mean(_cell(runs, arm, n, "epoch_rho_nonce"))
              for n in N_GRID]
        ys = [statistics.mean(_cell(runs, arm, n, "epoch_rho_exact"))
              for n in N_GRID]
        ax.plot(xs, ys, "o", ms=8, color=COLORS[arm], label=SHORT[arm])
    ax.plot([0, 1], [0, 1], "--", color="grey", lw=1,
            label=r"$\rho_{exact}=\rho_{nonce}$")
    ax.set_xlabel(r"$\rho_{nonce}$ (template-epoch scope)")
    ax.set_ylabel(r"$\rho_{exact}$ (template-epoch scope)")
    ax.set_title("Nonce-value reuse is not exact-input duplication:\n"
                 "CONV sits at (0,0) per epoch yet reuses all values across "
                 "miners in a round;\nMT sits on the diagonal; PC at the origin",
                 fontsize=9)
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8)
    _save(fig, "fignr04_nonce_vs_exact")

    # 5 — three families comparison (epoch-scope reuse + blocks)
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 4.2))
    fams = [ARM_CONV_OFF, ARM_MT_OFF, ARM_PC]
    width = 0.25
    for k, arm in enumerate(fams):
        a1.bar([i + k * width for i in range(len(N_GRID))],
               [statistics.mean(_cell(runs, arm, n, "epoch_rho_nonce"))
                for n in N_GRID], width, color=COLORS[arm], label=SHORT[arm])
        a2.bar([i + k * width for i in range(len(N_GRID))],
               [statistics.mean(_cell(runs, arm, n, "accepted_blocks"))
                for n in N_GRID], width, color=COLORS[arm], label=SHORT[arm])
    for a, t in ((a1, r"$\rho_{nonce}$ per template epoch"),
                 (a2, "accepted blocks per 10 000 s run")):
        a.set_xticks([i + width for i in range(len(N_GRID))])
        a.set_xticklabels(N_GRID)
        a.set_xlabel("N"); a.set_ylabel(t); a.grid(alpha=0.3, axis="y")
    a1.legend(fontsize=8)
    a1.set_title("cross-miner reuse within a template epoch", fontsize=9)
    a2.set_title("service consequence: MT loses (N−1)/N of distinct-input "
                 "throughput", fontsize=9)
    _save(fig, "fignr05_conv_vs_mt_vs_pocol")

    # 6 — zero-start vs random-offset (sub-sweep window)
    fig, ax = plt.subplots(figsize=(7, 4.4))
    for arm in (ARM_CONV_ZERO, ARM_CONV_OFF, ARM_MT_ZERO, ARM_MT_OFF):
        ys = [statistics.mean(_cell(runs, arm, n, "mean_subsweep_rho_nonce"))
              for n in N_GRID]
        ax.plot(N_GRID, ys, "o-", color=COLORS[arm], label=SHORT[arm])
    ax.plot(N_GRID, [(n - 1) / n for n in N_GRID], "k--", lw=1,
            label="(N-1)/N zero-start prediction")
    ax.set_xlabel("network size N (miners)")
    ax.set_ylabel(r"$\rho_{nonce}$ in first $\lfloor S/2N\rfloor$ ticks of round")
    ax.set_title("Traversal-policy sensitivity below saturation\n"
                 "(round-scope values are saturated and identical)", fontsize=10)
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8)
    _save(fig, "fignr06_zero_vs_offset")

    # 7 — physical evaluations vs N
    _line_by_arm(runs, "C_total_evaluations",
                 "total candidate evaluations per run",
                 "Physical work: identical across arms (N × 2.34e14 evals/s "
                 "× 10 000 s;\nPoCol deficit = straggler gap ≤ 5e-8)",
                 "fignr07_physical_evaluations_vs_N")

    # 8 — energy vs N (alpha = 0)
    fig, ax = plt.subplots(figsize=(7, 4.4))
    for arm in ARMS:
        ys = []
        for n in N_GRID:
            es = [float(r["energy_J"]) / 3.6e6 for r in energy
                  if r["arm"] == arm and int(r["N"]) == n
                  and r["alpha_case"] == "LP0"]
            ys.append(statistics.mean(es))
        ax.plot(N_GRID, ys, "o-", color=COLORS[arm], label=SHORT[arm])
    ax.set_xlabel("network size N (miners)")
    ax.set_ylabel("energy per run (kWh), α = 0")
    ax.set_title("Electrical energy: equal wherever active power-time is equal\n"
                 "(all five arms overlap; nonce-reuse patterns differ wildly)",
                 fontsize=10)
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8)
    _save(fig, "fignr08_energy_vs_N")

    # 9 — energy saving vs alpha (PC vs CONV-OFFSET)
    fig, ax = plt.subplots(figsize=(7, 4.4))
    alphas = [ALPHA_CASES[c] for c in ("LP0", "LP10", "LP25", "LP50")]
    for n in N_GRID:
        ys = []
        for case in ("LP0", "LP10", "LP25", "LP50"):
            sav = [float(r["saving_vs_conv_offset"]) for r in energy
                   if r["arm"] == ARM_PC and int(r["N"]) == n
                   and r["alpha_case"] == case
                   and r["saving_vs_conv_offset"] != ""]
            ys.append(statistics.mean(sav))
        ax.plot(alphas, ys, "o-", label=f"N={n}")
    ax.set_xlabel(r"low-power sensitivity $\alpha$ ($P_{low}=\alpha P_{active}$)")
    ax.set_ylabel("PoCol energy saving vs PW-CONV-OFFSET")
    ax.set_title("Energy saving = F_low · (1−α): bounded by the "
                 "straggler gap (≤ 5e-8)", fontsize=10)
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8)
    _save(fig, "fignr09_energy_saving_vs_alpha")

    # 10 — nonce reuse fraction vs energy saving
    fig, ax = plt.subplots(figsize=(6.6, 4.8))
    for arm in ARMS:
        for n in N_GRID:
            x = statistics.mean(_cell(runs, arm, n, "epoch_rho_nonce"))
            base = [float(r["energy_J"]) for r in energy
                    if r["arm"] == ARM_CONV_OFF and int(r["N"]) == n
                    and r["alpha_case"] == "LP0"]
            mine = [float(r["energy_J"]) for r in energy
                    if r["arm"] == arm and int(r["N"]) == n
                    and r["alpha_case"] == "LP0"]
            y = 1 - statistics.mean(mine) / statistics.mean(base)
            ax.plot(x, y, "o", color=COLORS[arm],
                    label=SHORT[arm] if n == N_GRID[0] else None)
    ax.set_xlabel(r"$\rho_{nonce}$ (template-epoch scope)")
    ax.set_ylabel("energy saving vs PW-CONV-OFFSET (α = 0)")
    ax.set_ylim(-1e-7, 1e-7)
    ax.set_title("No relationship: eliminating nonce-value reuse does not by\n"
                 "itself save energy (all points at saving ≈ 0)", fontsize=10)
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8)
    _save(fig, "fignr10_reuse_vs_saving")

    # 11 — low-power residency vs energy saving (PC)
    fig, ax = plt.subplots(figsize=(6.6, 4.8))
    xs, ys = [], []
    for n in N_GRID:
        f = statistics.mean(_cell(runs, ARM_PC, n, "f_low_time"))
        sav = [float(r["saving_vs_conv_offset"]) for r in energy
               if r["arm"] == ARM_PC and int(r["N"]) == n
               and r["alpha_case"] == "LP0" and r["saving_vs_conv_offset"] != ""]
        xs.append(f); ys.append(statistics.mean(sav))
        ax.annotate(f"N={n}", (f, statistics.mean(sav)), fontsize=8,
                    textcoords="offset points", xytext=(5, 4))
    ax.plot(xs, ys, "o", color=COLORS[ARM_PC])
    lim = max(xs) * 1.2
    ax.plot([0, lim], [0, lim], "--", color="grey", lw=1,
            label="saving = F_low (α = 0)")
    ax.set_xlabel("PoCol low-power residency F_low (fraction of miner-time)")
    ax.set_ylabel("energy saving vs PW-CONV-OFFSET (α = 0)")
    ax.set_title("Any saving is exactly the measured low-power residency",
                 fontsize=10)
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8)
    _save(fig, "fignr11_flow_vs_saving")

    # 12 — block retention vs N
    fig, ax = plt.subplots(figsize=(7, 4.4))
    for arm in ARMS:
        ys = []
        for n in N_GRID:
            b = sum(_cell(runs, arm, n, "accepted_blocks"))
            c = sum(_cell(runs, ARM_CONV_OFF, n, "accepted_blocks"))
            ys.append(b / c)
        ax.plot(N_GRID, ys, "o-", color=COLORS[arm], label=SHORT[arm])
    ax.plot(N_GRID, [1 / n for n in N_GRID], "k--", lw=1,
            label="1/N (MT distinct-input prediction)")
    ax.set_yscale("log")
    ax.set_xlabel("network size N (miners)")
    ax.set_ylabel("block retention vs PW-CONV-OFFSET (pooled)")
    ax.set_title("Retention: CONV = PC = 1; common-template uncoordinated "
                 "search collapses to ~1/N", fontsize=10)
    ax.grid(alpha=0.3, which="both")
    ax.legend(fontsize=8)
    _save(fig, "fignr12_block_retention_vs_N")

    # 13 — block latency vs N
    fig, ax = plt.subplots(figsize=(7, 4.4))
    for arm in ARMS:
        ys, ns = [], []
        for n in N_GRID:
            vals = _cell(runs, arm, n, "mean_interval_s")
            if vals:
                ys.append(statistics.mean(vals)); ns.append(n)
        ax.plot(ns, ys, "o-", color=COLORS[arm], label=SHORT[arm])
    ax.axhline(600.0, ls="--", color="grey", lw=1, label="600 s nominal")
    ax.set_yscale("log")
    ax.set_xlabel("network size N (miners)")
    ax.set_ylabel("mean accepted-block interval (s)")
    ax.set_title("Latency: CONV/PC at ~600 s; MT intervals scale ×N "
                 "(few blocks; see Table NR-G run counts)", fontsize=10)
    ax.grid(alpha=0.3, which="both")
    ax.legend(fontsize=8)
    _save(fig, "fignr13_block_latency_vs_N")

    # conceptual diagram
    conceptual()


def conceptual():
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(9, 6.4),
                                 gridspec_kw={"hspace": 0.55})
    S = 1.0
    # top: conventional PoW — three miners, same 32-bit domain, own templates
    miners = [("Miner A (template T_A)", 0.00, "#2c7fb8"),
              ("Miner B (template T_B)", 0.35, "#d7301f"),
              ("Miner C (template T_C)", 0.70, "#8c6bb1")]
    for k, (label, off, color) in enumerate(miners):
        y = 2 - k * 0.8
        a1.barh(y, S, left=0, height=0.5, color="none", edgecolor="grey", lw=0.8)
        a1.barh(y, S - off, left=off, height=0.5, color=color, alpha=0.45)
        a1.barh(y, off, left=0, height=0.5, color=color, alpha=0.45)
        a1.annotate(label, (-0.02, y), ha="right", va="center", fontsize=9)
        a1.annotate("start", (off, y + 0.32), fontsize=7, color=color)
    a1.axvline(0.52, color="black", lw=1.2, ls=":")
    a1.annotate("nonce = 0x851E...: evaluated by ALL miners\n= nonce-value reuse"
                "\nbut under T_A ≠ T_B ≠ T_C\n= NOT exact-input "
                "duplication", (1.03, 1.6), fontsize=8, va="center")
    a1.set_xlim(-0.35, 1.45); a1.set_ylim(-0.1, 3.1)
    a1.set_title("Conventional PoW: independent miners share the same 32-bit "
                 "nonce-value domain [0, 2³²−1]", fontsize=10)
    a1.set_xticks([0, 1]); a1.set_xticklabels(["0", r"$2^{32}-1$"])
    a1.set_yticks([])
    for s in ("left", "right", "top"):
        a1.spines[s].set_visible(False)

    # bottom: PoCol — disjoint ranges, one common template
    cols = ["#2c7fb8", "#d7301f", "#8c6bb1"]
    bounds = [0, 1 / 3, 2 / 3, 1.0]
    y = 1.0
    for k in range(3):
        a2.barh(y, bounds[k + 1] - bounds[k], left=bounds[k], height=0.5,
                color=cols[k], alpha=0.55)
        a2.annotate(f"$R_{{{'ABC'[k]}}}$",
                    ((bounds[k] + bounds[k + 1]) / 2, y), ha="center",
                    va="center", fontsize=11)
    a2.barh(y, 1.0, left=0, height=0.5, color="none", edgecolor="black", lw=1)
    a2.annotate("one common immutable template T; "
                r"$R_A\cap R_B=R_B\cap R_C=R_A\cap R_C=\varnothing$",
                (0.5, 1.6), ha="center", fontsize=9)
    a2.annotate("within one template epoch: nonce-value reuse = 0 AND "
                "exact-input duplication = 0", (0.5, 0.35), ha="center",
                fontsize=9)
    a2.set_xlim(-0.35, 1.45); a2.set_ylim(0, 2.1)
    a2.set_title("PoCol: deterministic disjoint nonce allocation of the same "
                 "32-bit domain", fontsize=10)
    a2.set_xticks([0, 1 / 3, 2 / 3, 1])
    a2.set_xticklabels(["0", r"$\lfloor S/3\rfloor$", r"$\lfloor 2S/3\rfloor$",
                        r"$2^{32}-1$"])
    a2.set_yticks([])
    for s in ("left", "right", "top"):
        a2.spines[s].set_visible(False)
    _save(fig, "fignr00_conceptual_nonce_domain")


if __name__ == "__main__":
    main()
    print("figures written to", FIG)
