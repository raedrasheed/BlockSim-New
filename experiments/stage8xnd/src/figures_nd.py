"""Stage 8X-ND — the 16 required figures (PNG+PDF+SVG)."""

from __future__ import annotations

import csv
import os
import statistics

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from experiments.stage8xnd.config.nd_config import (
    ALPHA_CASES, ARM_PC, ARM_PC_NOLP, ARM_PW, ARM_PW_OFFSET, N_GRID,
    NONCE_DOMAIN_SIZE, partition, sweep_timing,
)

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(HERE, "outputs")
FIG = os.path.join(HERE, "figures")
COLORS = {ARM_PW: "#2c7fb8", ARM_PW_OFFSET: "#8c6bb1", ARM_PC: "#238b45",
          ARM_PC_NOLP: "#d7301f"}
ALL_ARMS = [ARM_PW, ARM_PW_OFFSET, ARM_PC, ARM_PC_NOLP]


def _rows(name):
    with open(os.path.join(OUT, name)) as fh:
        return list(csv.DictReader(fh))


def _save(fig, stem):
    os.makedirs(FIG, exist_ok=True)
    for ext in ("png", "pdf", "svg"):
        fig.savefig(os.path.join(FIG, f"{stem}.{ext}"),
                    dpi=150 if ext == "png" else None, bbox_inches="tight")
    plt.close(fig)


def _get(rows, col, **flt):
    return [float(r[col]) for r in rows
            if all(str(r.get(k)) == str(v) for k, v in flt.items())
            and r.get(col, "") not in ("", "NA")]


def _line(rows, col, ylabel, title, stem, arms=ALL_ARMS, logy=False, **flt):
    fig, ax = plt.subplots(figsize=(6.8, 4.2))
    for arm in arms:
        ys = [statistics.mean(_get(rows, col, N=n, arm=arm, **flt))
              for n in N_GRID]
        ax.plot(N_GRID, ys, "o-", color=COLORS[arm], label=arm)
    ax.set_xlabel("network size N (miners)")
    ax.set_ylabel(ylabel)
    ax.set_title(title, fontsize=10)
    if logy:
        ax.set_yscale("log")
    ax.grid(alpha=0.3, which="both" if logy else "major")
    ax.legend(fontsize=8)
    _save(fig, stem)


def main():
    noncem = _rows("stage8xnd_nonce_domain_metrics.csv")
    energym = _rows("stage8xnd_energy_sensitivity.csv")
    svcm = _rows("stage8xnd_service_metrics.csv")
    workm = _rows("stage8xnd_work_metrics.csv")
    lowm = _rows("stage8xnd_low_power_metrics.csv")
    pairm = _rows("stage8xnd_paired_metrics.csv")
    phys = _rows("stage8xnd_physical_runs.csv")

    # 1/2 — conceptual diagrams
    conceptual_pw()
    conceptual_pc()

    # 3 — per-miner nonce count vs N
    fig, ax = plt.subplots(figsize=(6.8, 4.2))
    ax.plot(N_GRID, [NONCE_DOMAIN_SIZE] * len(N_GRID), "o-",
            color=COLORS[ARM_PW], label="ND-PW: |D_i| = 2^32 (every miner)")
    ax.plot(N_GRID, [max(e - s + 1 for s, e in partition(n)) for n in N_GRID],
            "o-", color=COLORS[ARM_PC], label="ND-PC: |R_i| = ⌈2^32/N⌉")
    ax.set_yscale("log")
    ax.set_xlabel("N"); ax.set_ylabel("nonce values assigned per miner")
    ax.set_title("Same domain, different organization: full copy per PoW "
                 "miner vs disjoint partition", fontsize=10)
    ax.grid(alpha=0.3, which="both"); ax.legend(fontsize=8)
    _save(fig, "fignd03_per_miner_nonce_count")

    # 4 — range sweep time vs N
    fig, ax = plt.subplots(figsize=(6.8, 4.2))
    ax.plot(N_GRID, [sweep_timing(n)["t_full_sweep_s"] * 1e6 for n in N_GRID],
            "o-", color=COLORS[ARM_PW], label="ND-PW full-domain sweep (µs)")
    ax.plot(N_GRID, [sweep_timing(n)["t_range_sweep_s"] * 1e6 for n in N_GRID],
            "o-", color=COLORS[ARM_PC], label="ND-PC range sweep (µs)")
    ax.set_yscale("log")
    ax.set_xlabel("N"); ax.set_ylabel("sweep time (µs)")
    ax.set_title("At 234 TH/s the 32-bit domain is a microsecond-scale "
                 "resource (18.355 µs full, 37–184 ns per range)", fontsize=10)
    ax.grid(alpha=0.3, which="both"); ax.legend(fontsize=8)
    _save(fig, "fignd04_sweep_time")

    # 5 — sweeps per second
    fig, ax = plt.subplots(figsize=(6.8, 4.2))
    ax.plot(N_GRID, [sweep_timing(n)["full_sweeps_per_second"]
                     for n in N_GRID], "o-", color=COLORS[ARM_PW],
            label="full-domain sweeps/s per PW miner")
    ax.plot(N_GRID, [sweep_timing(n)["range_sweeps_per_second"]
                     for n in N_GRID], "o-", color=COLORS[ARM_PC],
            label="range sweeps/s per PC miner (= epochs/s)")
    ax.set_yscale("log")
    ax.set_xlabel("N"); ax.set_ylabel("sweeps per second")
    ax.set_title("Domain sweep frequency", fontsize=10)
    ax.grid(alpha=0.3, which="both"); ax.legend(fontsize=8)
    _save(fig, "fignd05_sweeps_per_second")

    # 6 — nonce-value reuse vs N
    _line(noncem, "rho_nonce", r"$\rho_{nonce}$ (run scope)",
          "Numerical nonce-value reuse saturates for both protocols\n"
          "(finite 2^32 domain at 2.34e14 evals/s); cross-miner structure "
          "differs (m_max = N vs 1)",
          "fignd06_nonce_reuse", arms=[ARM_PW, ARM_PW_OFFSET, ARM_PC])

    # 7 — low-power fraction vs N
    fig, ax = plt.subplots(figsize=(6.8, 4.2))
    ys = [statistics.mean(_get(lowm, "F_low", N=n, arm=ARM_PC))
          for n in N_GRID]
    ax.plot(N_GRID, ys, "o-", color=COLORS[ARM_PC], label="ND-PC measured")
    from experiments.stage8xnd.config.nd_config import predictions
    ax.plot(N_GRID, [predictions(n)["f_low_expected"] for n in N_GRID],
            "k--", lw=1, label="straggler-gap closed form")
    ax.set_yscale("log")
    ax.set_xlabel("N"); ax.set_ylabel("F_low (fraction of miner-time)")
    ax.set_title("Post-range low-power residency: 9e-10 … 7e-8 — the 32-bit "
                 "domain is exhausted too quickly for material residency",
                 fontsize=10)
    ax.grid(alpha=0.3, which="both"); ax.legend(fontsize=8)
    _save(fig, "fignd07_flow")

    # 8 — total energy vs N (LP0)
    _line(energym, "energy_kWh", "energy per run (kWh), α = 0",
          "Total energy: all four arms coincide (differences ≤ 7e-8)",
          "fignd08_energy", alpha_case="LP0")

    # 9 — energy saving vs N per alpha (ND-PC)
    fig, ax = plt.subplots(figsize=(6.8, 4.2))
    for case in ALPHA_CASES:
        ys = [statistics.mean(_get(pairm, f"saving_{case}", N=n, arm=ARM_PC))
              for n in N_GRID]
        ax.plot(N_GRID, ys, "o-", label=case)
    ax.set_yscale("log")
    ax.set_xlabel("N"); ax.set_ylabel("ND-PC energy saving vs ND-PW")
    ax.set_title("Energy saving = F_low·(1−α): bounded by 7.1e-8", fontsize=10)
    ax.grid(alpha=0.3, which="both"); ax.legend(fontsize=8)
    _save(fig, "fignd09_saving_vs_N")

    # 10 — accepted blocks vs N
    _line(svcm, "accepted_blocks", "accepted blocks per run (mean)",
          "Block production identical: partitioning does not reduce "
          "independent trials per second (TQ4)", "fignd10_blocks")

    # 11 — block retention vs N
    fig, ax = plt.subplots(figsize=(6.8, 4.2))
    for arm in (ARM_PC, ARM_PC_NOLP, ARM_PW_OFFSET):
        ys = [statistics.mean(_get(pairm, "block_retention", N=n, arm=arm))
              for n in N_GRID]
        ax.plot(N_GRID, ys, "o-", color=COLORS[arm], label=arm)
    ax.axhline(1.0, ls="--", color="grey", lw=1)
    ax.set_ylim(0.9, 1.1)
    ax.set_xlabel("N"); ax.set_ylabel("paired block retention vs ND-PW")
    ax.set_title("Retention = 1.0000 in every paired seed", fontsize=10)
    ax.grid(alpha=0.3); ax.legend(fontsize=8)
    _save(fig, "fignd11_retention")

    # 12 — median block interval vs N
    _line(svcm, "median_interval_s", "median block interval (s, run mean)",
          "Median intervals coincide across arms", "fignd12_median_interval")

    # 13 — energy per block vs N
    _line(energym, "energy_per_block_J", "energy per accepted block (J), α=0",
          "Energy per block identical (ratio = 1.000000)",
          "fignd13_energy_per_block", alpha_case="LP0")

    # 14 — physical hashes vs N
    _line(workm, "W_total", "physical evaluations per run",
          "Physical work identical (PoCol deficit = straggler ≤ 7e-8)",
          "fignd14_work", arms=[ARM_PW, ARM_PW_OFFSET, ARM_PC])

    # 15 — energy saving vs block retention
    fig, ax = plt.subplots(figsize=(6.6, 4.6))
    for n in N_GRID:
        for arm, mk in ((ARM_PC, "o"), (ARM_PC_NOLP, "s")):
            x = statistics.mean(_get(pairm, "block_retention", N=n, arm=arm))
            y = statistics.mean(_get(pairm, "saving_LP0", N=n, arm=arm))
            ax.plot(x, y, mk, color=COLORS[arm],
                    label=arm if n == N_GRID[0] else None)
    ax.set_xlim(0.99, 1.01)
    ax.set_xlabel("paired block retention vs ND-PW")
    ax.set_ylabel("energy saving vs ND-PW (α = 0)")
    ax.set_title("The whole result in one panel: retention exactly 1, saving "
                 "≤ 7e-8 (PC) or 0 (NOLP)", fontsize=10)
    ax.grid(alpha=0.3); ax.legend(fontsize=8)
    _save(fig, "fignd15_saving_vs_retention")

    # 16 — active miner-time vs N
    _line(phys, "t_active_miner_s", "active miner-seconds per run",
          "Active miner-time: equal across arms up to the straggler gap",
          "fignd16_active_time")


def conceptual_pw():
    fig, ax = plt.subplots(figsize=(8.6, 3.6))
    cols = ["#2c7fb8", "#d7301f", "#8c6bb1"]
    for i in range(3):
        ax.barh(2 - i, 1.0, left=0, height=0.5, color=cols[i], alpha=0.5)
        ax.annotate(f"$M_{{{i+1}}}$ (header $H_{{{i+1}}}$): 0, 1, 2, …, "
                    r"$2^{32}-1$", (1.03, 2 - i), fontsize=9, va="center")
    ax.annotate(r"$D_1 = D_2 = D_3 = D = \{0,\ldots,2^{32}-1\}$"
                "\nsame numerical nonce-value domain, independent headers",
                (0.5, -0.75), ha="center", fontsize=9)
    ax.set_xlim(0, 2.1); ax.set_ylim(-1.2, 2.8)
    ax.set_xticks([0, 1]); ax.set_xticklabels(["0", r"$2^{32}-1$"])
    ax.set_yticks([])
    ax.set_title("Conventional PoW (ND-PW): every miner independently owns "
                 "the full 32-bit nonce-value domain", fontsize=10)
    for s in ("left", "right", "top"):
        ax.spines[s].set_visible(False)
    _save(fig, "fignd01_conceptual_pw_full_domain")


def conceptual_pc():
    fig, ax = plt.subplots(figsize=(8.6, 3.0))
    cols = ["#2c7fb8", "#d7301f", "#8c6bb1"]
    bounds = [0, 1 / 3, 2 / 3, 1.0]
    for i in range(3):
        ax.barh(1, bounds[i + 1] - bounds[i], left=bounds[i], height=0.5,
                color=cols[i], alpha=0.65)
        ax.annotate(f"$R_{{{i+1}}}$", ((bounds[i] + bounds[i + 1]) / 2, 1),
                    ha="center", va="center", fontsize=11)
    ax.barh(1, 1.0, left=0, height=0.5, color="none", edgecolor="black")
    ax.annotate(r"$D = R_1 \cup R_2 \cup R_3$,  $R_i \cap R_j = \varnothing$;"
                "  common immutable template;  ACTIVE → LOW POWER after own "
                "range", (0.5, 0.25), ha="center", fontsize=9)
    ax.set_xlim(0, 1.35); ax.set_ylim(0, 1.8)
    ax.set_xticks([0, 1 / 3, 2 / 3, 1])
    ax.set_xticklabels(["0", r"$\lfloor S/3\rfloor$", r"$\lfloor 2S/3\rfloor$",
                        r"$2^{32}-1$"])
    ax.set_yticks([])
    ax.set_title("PoCol (ND-PC): ONE 32-bit nonce-value domain partitioned "
                 "among miners", fontsize=10)
    for s in ("left", "right", "top"):
        ax.spines[s].set_visible(False)
    _save(fig, "fignd02_conceptual_pc_partition")


if __name__ == "__main__":
    main()
    print("figures written to", FIG)
