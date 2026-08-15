"""Stage 8X-E50 — the 15 required figures (PNG+PDF+SVG)."""

from __future__ import annotations

import csv
import os
import statistics

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from experiments.stage8xe50.config.e50_config import (
    ACTIVE_FRACTIONS, ALPHA_CASES, ARM_CONV, ARM_MT, ARMS, N_GRID, PC_ARMS,
    active_count,
)

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(HERE, "outputs")
FIG = os.path.join(HERE, "figures")

FRACS = [ACTIVE_FRACTIONS[a] for a in PC_ARMS]
ALPHA_COLORS = {"LP0": "#238b45", "LP10": "#2c7fb8", "LP25": "#d7301f",
                "LP50": "#8c6bb1"}


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
    out = []
    for r in rows:
        if all(str(r.get(k)) == str(v) for k, v in flt.items()) \
                and r.get(col, "") not in ("", "NA"):
            out.append(float(r[col]))
    return out


def main():
    tabB = _rows("stage8xe50_tableB_mt100.csv")
    tabD = _rows("stage8xe50_tableD_coverage_retention.csv")
    tabE = _rows("stage8xe50_tableE_energy_saving.csv")
    tabF = _rows("stage8xe50_tableF_block_retention.csv")
    tabG = _rows("stage8xe50_tableG_latency.csv")
    tabH = _rows("stage8xe50_tableH_energy_per_block.csv")
    tabI = _rows("stage8xe50_tableI_low_power.csv")
    tabJ = _rows("stage8xe50_tableJ_fairness.csv")
    tabK = _rows("stage8xe50_tableK_feasible_points.csv")
    cov = _rows("stage8xe50_unique_coverage.csv")

    def pc_series(table, col, n, **flt):
        return [
            _get(table, col, N=n, arm=arm, **flt)[0]
            if _get(table, col, N=n, arm=arm, **flt) else None
            for arm in PC_ARMS]

    # 1 — MT100 exact duplication vs N
    fig, ax = plt.subplots(figsize=(6.6, 4.2))
    ax.plot(N_GRID, [_get(tabB, "rho_exact_mean", N=n)[0] for n in N_GRID],
            "o-", color="#d7301f", label="measured")
    ax.plot(N_GRID, [(n - 1) / n for n in N_GRID], "k--", lw=1,
            label="(N-1)/N predicted")
    ax.set_xlabel("N"); ax.set_ylabel(r"$\rho_{exact}$ (E50-MT100)")
    ax.set_title("Exact duplication of the same-template control", fontsize=10)
    ax.grid(alpha=0.3); ax.legend(fontsize=8)
    _save(fig, "fige50_01_mt100_duplication_vs_N")

    # 2 — unique coverage rate vs N
    fig, ax = plt.subplots(figsize=(6.6, 4.2))
    for arm, color in ((ARM_MT, "#d7301f"), (ARM_CONV, "#2c7fb8"),
                       ("E50-PC10", "#238b45"), ("E50-PC50", "#8c6bb1")):
        ys = [statistics.mean(_get(cov, "unique_coverage_rate_per_s",
                                   N=n, arm=arm)) for n in N_GRID]
        ax.plot(N_GRID, ys, "o-", color=color, label=arm)
    ax.set_yscale("log")
    ax.set_xlabel("N"); ax.set_ylabel("unique candidate inputs per second")
    ax.set_title("Unique-coverage rate: MT100 = one miner's worth (h);\n"
                 "PoCol = k·h; CONV reference = N·h", fontsize=10)
    ax.grid(alpha=0.3, which="both"); ax.legend(fontsize=8)
    _save(fig, "fige50_02_unique_rate_vs_N")

    # 3 — coverage retention vs active fraction
    fig, ax = plt.subplots(figsize=(6.6, 4.2))
    for n in N_GRID:
        ax.plot(FRACS, [_get(tabD, "retention_mean", N=n, arm=a)[0]
                        for a in PC_ARMS], "o-", label=f"N={n}")
    ax.axhline(0.95, ls="--", color="grey", lw=1, label="0.95 constraint")
    ax.set_yscale("log")
    ax.set_xlabel("active fraction A")
    ax.set_ylabel("UniqueCoverageRetention vs MT100")
    ax.set_title("PoCol exceeds MT100 unique coverage k-fold at every "
                 "fraction", fontsize=10)
    ax.grid(alpha=0.3, which="both"); ax.legend(fontsize=8)
    _save(fig, "fige50_03_coverage_retention")

    # 4 — energy saving vs active fraction per alpha
    fig, ax = plt.subplots(figsize=(6.6, 4.2))
    for case in ALPHA_CASES:
        ys = [statistics.mean(_get(tabE, "saving_mean", N=300, arm=a,
                                   alpha_case=case)) for a in PC_ARMS]
        ax.plot(FRACS, ys, "o-", color=ALPHA_COLORS[case], label=case)
    ax.axhline(0.5, ls="--", color="grey", lw=1, label="50%")
    ax.set_xlabel("active fraction A")
    ax.set_ylabel("energy saving vs MT100 (N = 300; identical at all N)")
    ax.set_title("Saving = (1−A)(1−α): exceeds 50% only for α ≤ 0.25 at the "
                 "tested fractions", fontsize=10)
    ax.grid(alpha=0.3); ax.legend(fontsize=8)
    _save(fig, "fige50_04_saving_vs_fraction")

    # 5 — block retention vs active fraction
    fig, ax = plt.subplots(figsize=(6.6, 4.2))
    for n in N_GRID:
        ys = [_get(tabF, "pooled_block_retention", N=n, arm=a)[0]
              for a in PC_ARMS]
        ax.plot(FRACS, ys, "o-", label=f"N={n} (MT pooled "
                f"{int(_get(tabF, 'pooled_MT100_blocks', N=n, arm='E50-PC10')[0])} blocks)")
    ax.axhline(0.90, ls="--", color="grey", lw=1, label="0.90 constraint")
    ax.set_yscale("log")
    ax.set_xlabel("active fraction A")
    ax.set_ylabel("pooled BlockRetention vs MT100")
    ax.set_title("PoCol out-produces the same-template control at every "
                 "fraction (sparse MT100 denominators shown)", fontsize=10)
    ax.grid(alpha=0.3, which="both"); ax.legend(fontsize=7)
    _save(fig, "fige50_05_block_retention")

    # 6 — median latency ratio vs active fraction
    fig, ax = plt.subplots(figsize=(6.6, 4.2))
    for n in N_GRID:
        ys = [_get(tabG, "median_latency_ratio", N=n, arm=a)[0]
              if _get(tabG, "median_latency_ratio", N=n, arm=a) else None
              for a in PC_ARMS]
        ax.plot(FRACS, ys, "o-", label=f"N={n}")
    ax.axhline(1.20, ls="--", color="grey", lw=1, label="1.20 constraint")
    ax.set_xlabel("active fraction A")
    ax.set_ylabel("pooled median latency ratio vs MT100")
    ax.set_title("Latency ratios ≤ 1.20 everywhere (horizon-truncated "
                 "intervals; MT100 counts in Table E50-G)", fontsize=10)
    ax.grid(alpha=0.3); ax.legend(fontsize=8)
    _save(fig, "fige50_06_latency_ratio")

    # 7 — energy saving vs block retention
    fig, ax = plt.subplots(figsize=(6.6, 4.6))
    for case in ("LP0", "LP50"):
        xs, ys = [], []
        for r in tabK:
            if r["pooled_block_retention"] not in ("", "NA"):
                xs.append(float(r["pooled_block_retention"]))
                ys.append(float(r[f"saving_{case}"]))
        ax.plot(xs, ys, "o", color=ALPHA_COLORS[case], label=case, alpha=0.7)
    ax.axhline(0.5, ls="--", color="grey", lw=1)
    ax.axvline(0.9, ls=":", color="grey", lw=1, label="0.90 retention")
    ax.set_xscale("log")
    ax.set_xlabel("pooled BlockRetention vs MT100")
    ax.set_ylabel("energy saving vs MT100")
    ax.set_title("No energy-service trade against MT100: saving and "
                 "retention improve together", fontsize=10)
    ax.grid(alpha=0.3, which="both"); ax.legend(fontsize=8)
    _save(fig, "fige50_07_saving_vs_retention")

    # 8 — energy saving vs coverage retention
    fig, ax = plt.subplots(figsize=(6.6, 4.6))
    for case in ("LP0", "LP50"):
        xs = [float(r["coverage_retention"]) for r in tabK]
        ys = [float(r[f"saving_{case}"]) for r in tabK]
        ax.plot(xs, ys, "o", color=ALPHA_COLORS[case], label=case, alpha=0.7)
    ax.axvline(0.95, ls=":", color="grey", lw=1, label="0.95 coverage")
    ax.set_xscale("log")
    ax.set_xlabel("UniqueCoverageRetention vs MT100")
    ax.set_ylabel("energy saving vs MT100")
    ax.set_title("Coverage constraint never binds: retention ≥ k ≥ 10 "
                 "at every point", fontsize=10)
    ax.grid(alpha=0.3, which="both"); ax.legend(fontsize=8)
    _save(fig, "fige50_08_saving_vs_coverage")

    # 9/10 — Pareto frontier (saving vs retention), constraint-highlighted
    for stem, highlight in (("fige50_09_pareto", False),
                            ("fige50_10_pareto_constrained", True)):
        fig, ax = plt.subplots(figsize=(6.6, 4.6))
        for r in tabK:
            if r["pooled_block_retention"] in ("", "NA"):
                continue
            x = float(r["pooled_block_retention"])
            y = float(r["saving_LP0"])
            feas = r["feasible"] == "True"
            ax.plot(x, y, "o" if feas else "x",
                    color="#238b45" if (feas or not highlight) else "#d7301f",
                    alpha=0.75)
        ax.axhline(0.5, ls="--", color="grey", lw=1, label="50% saving")
        if highlight:
            ax.axvline(0.9, ls=":", color="grey", lw=1,
                       label="0.90 retention constraint")
        ax.set_xscale("log")
        ax.set_xlabel("pooled BlockRetention vs MT100")
        ax.set_ylabel("energy saving vs MT100 (α = 0)")
        ax.set_title("Pareto view: every tested point is feasible; the "
                     "frontier is the A-sweep itself", fontsize=10)
        ax.grid(alpha=0.3, which="both"); ax.legend(fontsize=8)
        _save(fig, stem)

    # 11 — energy per block vs active fraction
    fig, ax = plt.subplots(figsize=(6.6, 4.2))
    n = 300
    ys, labels = [], []
    for arm in PC_ARMS + [ARM_MT, ARM_CONV]:
        v = _get(tabH, "energy_per_block_J_mean", N=n, arm=arm,
                 alpha_case="LP0")
        ys.append(v[0] / 3.6e6 if v else None)
        labels.append(arm.replace("E50-", ""))
    ax.bar(range(len(ys)), [y or 0 for y in ys],
           color=["#238b45"] * len(PC_ARMS) + ["#d7301f", "#2c7fb8"])
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=45, fontsize=7)
    ax.set_yscale("log")
    ax.set_ylabel("energy per accepted block (kWh), α = 0, N = 300")
    ax.set_title("PoCol restores conventional-PoW energy per block "
                 "(all PC bars = CONV bar); MT100 is ~N× worse", fontsize=10)
    ax.grid(alpha=0.3, axis="y", which="both")
    _save(fig, "fige50_11_energy_per_block")

    # 12 — low-power fraction vs energy saving
    fig, ax = plt.subplots(figsize=(6.6, 4.2))
    for case in ALPHA_CASES:
        xs, ys = [], []
        for narm in [(n, a) for n in N_GRID for a in PC_ARMS]:
            n_, a_ = narm
            xs.append(_get(tabI, "F_low_mean", N=n_, arm=a_)[0])
            ys.append(_get(tabE, "saving_mean", N=n_, arm=a_,
                           alpha_case=case)[0])
        ax.plot(xs, ys, ".", color=ALPHA_COLORS[case], label=case, alpha=0.7)
    xs = [i / 100 for i in range(0, 95, 5)]
    ax.plot(xs, xs, "k--", lw=0.8, label="saving = F_low (α = 0)")
    ax.set_xlabel("low-power residency F_low")
    ax.set_ylabel("energy saving vs MT100")
    ax.set_title("Saving = F_low·(1−α): energy tracks measured low-power "
                 "residency exactly", fontsize=10)
    ax.grid(alpha=0.3); ax.legend(fontsize=8)
    _save(fig, "fige50_12_flow_vs_saving")

    # 13 — fairness index vs active fraction
    fig, ax = plt.subplots(figsize=(6.6, 4.2))
    for n in N_GRID:
        ax.plot(FRACS, [_get(tabJ, "jain_index", N=n, arm=a)[0]
                        for a in PC_ARMS], "o-", label=f"N={n}")
    ax.set_ylim(0.999999, 1.0000002)
    ax.set_xlabel("active fraction A")
    ax.set_ylabel("Jain fairness index of per-miner duty")
    ax.set_title("Sliding-window rotation: duty exactly k/N per miner "
                 "(Jain ≈ 1 − 1e-17)", fontsize=10)
    ax.grid(alpha=0.3); ax.legend(fontsize=8)
    _save(fig, "fige50_13_fairness")

    # 14 — feasible / infeasible map
    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    for r in tabK:
        x = ACTIVE_FRACTIONS[r["arm"]]
        y = int(r["N"])
        feas = r["feasible"] == "True"
        ax.plot(x, y, "o" if feas else "x", ms=11,
                color="#238b45" if feas else "#d7301f")
    ax.set_xlabel("active fraction A"); ax.set_ylabel("N")
    ax.set_title("Preregistered feasibility (coverage ≥ 0.95, blocks ≥ 0.90, "
                 "latency ≤ 1.20): 40/40 points feasible", fontsize=10)
    ax.grid(alpha=0.3)
    _save(fig, "fige50_14_feasibility_map")

    # 15 — conceptual diagram
    conceptual()


def conceptual():
    fig, axes = plt.subplots(3, 1, figsize=(9, 7.2),
                             gridspec_kw={"hspace": 0.65})
    a1, a2, a3 = axes
    cols = ["#2c7fb8", "#d7301f", "#8c6bb1", "#fdae61"]
    # MT competitive overlap
    for i in range(4):
        a1.barh(3 - i, 1.0, left=0, height=0.55, color=cols[i], alpha=0.35)
        a1.annotate(f"miner {i+1}: full domain from own offset",
                    (1.02, 3 - i), fontsize=8, va="center")
    a1.set_title("E50-MT100 (same-template control): every active miner "
                 "re-covers the same 2³² domain — (N−1)/N duplicate inputs",
                 fontsize=9)
    # PoCol full active
    for i in range(4):
        a2.barh(1, 0.25, left=0.25 * i, height=0.55, color=cols[i], alpha=0.7)
    a2.annotate("all N owners active: disjoint ranges, zero duplication",
                (1.02, 1), fontsize=8, va="center")
    a2.set_title("E50-PC100: disjoint allocation of the same domain",
                 fontsize=9)
    # PoCol reduced active set
    a3.barh(1, 0.25, left=0.0, height=0.55, color=cols[0], alpha=0.9)
    for i in range(1, 4):
        a3.barh(1, 0.25, left=0.25 * i, height=0.55, color="lightgrey",
                edgecolor="grey", hatch="//")
    a3.annotate("1 of 4 owners active; inactive owners in LOW POWER;\n"
                "template renews when the active owner finishes its range → "
                "fresh domains keep unique coverage at k·h",
                (1.02, 1), fontsize=8, va="center")
    a3.set_title("E50-PC25-style reduced active set: coverage preserved, "
                 "(1−A)(1−α) energy avoided", fontsize=9)
    for a in axes:
        a.set_xlim(0, 2.3)
        a.set_ylim(0, 4 if a is a1 else 2)
        a.set_xticks([0, 1])
        a.set_xticklabels(["0", r"$2^{32}-1$"])
        a.set_yticks([])
        for s in ("left", "right", "top"):
            a.spines[s].set_visible(False)
    _save(fig, "fige50_15_conceptual")


if __name__ == "__main__":
    main()
    print("figures written to", FIG)
