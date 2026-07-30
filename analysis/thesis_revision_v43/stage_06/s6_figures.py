#!/usr/bin/env python3
"""Stage 6 — publication figures (vector PDF + high-res PNG + machine-readable plot data).

Design rules (Stage-6 approval §15): show the individual 30 run-level observations (no
bar charts that hide them, no 3D); label every figure with outcome, scenario/levels,
number of physical seeds, uncertainty representation, zero/NA handling, and a
confirmatory/secondary/exploratory tag; export vector + raster + the plotting data.
All jitter is deterministic (seeded). Figures are theme-neutral (light background).
"""
import csv
import json
import os

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import s6_common as C

runs = C.load_runs()
FIG = os.path.join(C.STAGE6, "figures")
PD = os.path.join(C.STAGE6, "plot_data")
for d in (FIG, PD):
    os.makedirs(d, exist_ok=True)

plt.rcParams.update({
    "figure.dpi": 120, "savefig.dpi": 200, "font.size": 9,
    "axes.grid": True, "grid.alpha": 0.25, "axes.axisbelow": True,
    "figure.facecolor": "white", "axes.facecolor": "white",
})
PALETTE = ["#3b6fb0", "#c0603a", "#4f9d69", "#8a5fb0", "#b0a13b"]
INDEX = []


def by(hid=None, **f):
    out = runs if hid is None else [r for r in runs if r["hypothesis_id"] == hid]
    return [r for r in out if all(r.get(k) == v for k, v in f.items())]


def jitter(n, seed, w=0.09):
    return np.random.default_rng(seed).uniform(-w, w, size=n)


def save(fig, name, caption, tag, plot_rows, plot_cols):
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, name + ".pdf"))
    fig.savefig(os.path.join(FIG, name + ".png"))
    plt.close(fig)
    with open(os.path.join(PD, name + ".csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=plot_cols)
        w.writeheader()
        w.writerows(plot_rows)
    INDEX.append({"figure": name, "tag": tag, "caption": caption,
                  "files": [name + ".pdf", name + ".png"],
                  "plot_data": name + ".csv"})


def strip(ax, groups, seed0, colors=None):
    """groups: list of (label, values). Plots individual points + median bar + IQR."""
    rows = []
    for i, (lab, vals) in enumerate(groups):
        v = np.asarray(vals, float)
        x = i + jitter(v.size, seed0 + i)
        c = (colors or PALETTE)[i % len(PALETTE)]
        ax.scatter(x, v, s=12, alpha=0.6, color=c, edgecolors="none", zorder=3)
        med = np.median(v)
        q1, q3 = np.percentile(v, [25, 75])
        ax.plot([i - 0.25, i + 0.25], [med, med], color="black", lw=2, zorder=4)
        ax.plot([i, i], [q1, q3], color="black", lw=1, zorder=4)
        for val in v:
            rows.append({"group": lab, "value": float(val)})
    ax.set_xticks(range(len(groups)))
    ax.set_xticklabels([g[0] for g in groups])
    return rows


# ---- FIG 1: H1 duplicate rate ordering ----
def fig01():
    order = [("B0", "B0"), ("B1", "B1"), ("B2", "B2"),
             ("B3/C1", "B3_C1_CONTINUOUS_DISJOINT")]
    groups = [(lab, [r["duplicate_evaluation_rate"] for r in by("H1;A1", scenario_id=sc)])
              for lab, sc in order]
    fig, ax = plt.subplots(figsize=(6.2, 4.0))
    rows = strip(ax, groups, 101)
    ax.set_ylabel("duplicate_evaluation_rate")
    ax.set_xlabel("scenario (n=150 physical seeds each; 5 miner counts × 30 seeds)")
    ax.set_title("H1 [CONFIRMATORY] duplicate candidate-header evaluation rate\n"
                 "ordering B1 > B2 > B3/C1 (immutable common template, disjoint ranges)")
    save(fig, "fig01_h1_duplicate_rate",
         "Duplicate-evaluation rate by scenario; black bar = median, whisker = IQR; "
         "each point is one run. Under the idealized immutable-common-template / "
         "disjoint-allocation assumptions only. No zero/NA (rate defined for all).",
         "CONFIRMATORY", rows, ["group", "value"])


# ---- FIG 2: A1 energy invariant ----
def fig02():
    order = [("B0", "B0"), ("B1", "B1"), ("B2", "B2"),
             ("B3/C1", "B3_C1_CONTINUOUS_DISJOINT")]
    groups = [(lab, [r["total_energy_kwh"] for r in by("H1;A1", scenario_id=sc)])
              for lab, sc in order]
    fig, ax = plt.subplots(figsize=(6.2, 4.0))
    rows = strip(ax, groups, 201)
    ax.axhline(C.CONTINUOUS_ENERGY_ANCHOR_KWH, color="#c0603a", ls="--", lw=1.2,
               label="accounting anchor P·T = 8.420833333 kWh")
    ax.set_ylabel("total_energy_kwh (10,000 s horizon)")
    ax.set_xlabel("scenario (n=150 each)")
    ax.set_ylim(8.4206, 8.4210)
    ax.legend(loc="upper right", fontsize=7)
    ax.set_title("A1 [ACCOUNTING INVARIANT] total energy = P_total·T exactly,\n"
                 "independent of miner count and search discipline")
    save(fig, "fig02_a1_energy_invariant",
         "Total energy per run vs the deterministic accounting anchor; all continuous "
         "full-participation runs coincide with 8.420833333 kWh (max deviation < 1e-6 "
         "relative). Invariant, not an empirical test.",
         "INVARIANT", rows, ["group", "value"])


# ---- FIG 3: H5 completion dispersion equal vs weighted (paired) ----
def fig03():
    fig, axes = plt.subplots(1, 2, figsize=(8.2, 4.2), sharey=True)
    rows = []
    panels = [("B3_C1_CONTINUOUS_DISJOINT", "B3/C1 (continuous)"), ("C2", "C2 (idle policy)")]
    for ax, (scen, title) in zip(axes, panels):
        for N, col in [(100, PALETTE[0]), (500, PALETTE[1])]:
            eq = {r["seed"]: r["completion_time_std_s"] for r in by(
                "H5", scenario_id=scen, miner_count=N, allocation_policy="equal")}
            wt = {r["seed"]: r["completion_time_std_s"] for r in by(
                "H5", scenario_id=scen, miner_count=N, allocation_policy="weighted")}
            for s in sorted(eq):
                ax.plot([0, 1], [eq[s], wt[s]], color=col, alpha=0.45, lw=0.8, zorder=2)
                rows.append({"scenario": scen, "miner_count": N, "seed": s,
                             "equal": eq[s], "weighted": wt[s]})
            ax.scatter([0] * len(eq), list(eq.values()), s=10, color=col, zorder=3,
                       label=f"N={N}")
            ax.scatter([1] * len(wt), list(wt.values()), s=10, color=col, zorder=3)
        ax.set_xticks([0, 1]); ax.set_xticklabels(["equal", "weighted"])
        ax.set_title(title); ax.legend(fontsize=7)
    axes[0].set_ylabel("completion_time_std_s (range-completion dispersion)")
    fig.suptitle("H5 [CONFIRMATORY] heterogeneous rates: weighted allocation removes "
                 "completion-time dispersion\n(seed-matched pairs, hetero_moderate, "
                 "n=30 per config)")
    save(fig, "fig03_h5_completion_dispersion",
         "Seed-matched equal→weighted completion-time dispersion. Weighted ranges drive "
         "dispersion to ~0 in both scenarios. No NA.",
         "CONFIRMATORY", rows, ["scenario", "miner_count", "seed", "equal", "weighted"])


# ---- FIG 4: H5 C2 energy trade-off (paired) ----
def fig04():
    fig, ax = plt.subplots(figsize=(6.2, 4.2))
    rows = []
    for N, col in [(100, PALETTE[0]), (500, PALETTE[1])]:
        eq = {r["seed"]: r["total_energy_kwh"] for r in by(
            "H5", scenario_id="C2", miner_count=N, allocation_policy="equal")}
        wt = {r["seed"]: r["total_energy_kwh"] for r in by(
            "H5", scenario_id="C2", miner_count=N, allocation_policy="weighted")}
        for s in sorted(eq):
            ax.plot([0, 1], [eq[s], wt[s]], color=col, alpha=0.45, lw=0.8)
            rows.append({"miner_count": N, "seed": s, "equal": eq[s], "weighted": wt[s]})
        ax.scatter([0] * len(eq), list(eq.values()), s=12, color=col, label=f"N = {N} miners")
        ax.scatter([1] * len(wt), list(wt.values()), s=12, color=col)
    ax.axhline(C.CONTINUOUS_ENERGY_ANCHOR_KWH, color="grey", ls="--", lw=1,
               label="Fixed-power anchor: 8.4208 kWh")
    ax.set_xticks([0, 1]); ax.set_xticklabels(["Equal ranges", "Hash-rate-weighted ranges"])
    ax.set_ylabel("Total energy over 10,000 s (kWh)"); ax.legend(fontsize=7)
    ax.set_title("H5 [CONFIRMATORY] C2 idle-energy trade-off under heterogeneous hash "
                 "rates:\nweighted ranges remove modeled idle and return energy to the "
                 "fixed-power anchor")
    save(fig, "fig04_h5_c2_energy_tradeoff",
         "Each line connects seed-matched runs. Under heterogeneous hash rates, "
         "equal-size ranges allow faster miners to complete earlier and enter the modeled "
         "idle state, reducing energy below the fixed-power anchor. Hash-rate-weighted "
         "ranges equalize modeled range-completion times, remove that idle opportunity, and "
         "return energy to the anchor. This is a completion-balance versus idle-energy "
         "trade-off, not an incentive-fairness or reward-fairness result.",
         "CONFIRMATORY", rows, ["miner_count", "seed", "equal", "weighted"])


# ---- FIG 5: H3 C2 energy decomposition ----
def fig05():
    fig, ax = plt.subplots(figsize=(6.6, 4.2))
    rows = []
    grp = by("H5", scenario_id="C2", allocation_policy="equal")  # idle-bearing C2
    grp = sorted(grp, key=lambda r: (r["miner_count"], r["seed"]))
    x = np.arange(len(grp))
    active = np.array([r["active_energy_kwh"] for r in grp])
    idlee = np.array([r["idle_energy_kwh"] for r in grp])
    saving = C.CONTINUOUS_ENERGY_ANCHOR_KWH - np.array([r["total_energy_kwh"] for r in grp])
    ax.bar(x, active, color=PALETTE[0], label="active_energy_kwh")
    ax.bar(x, idlee, bottom=active, color=PALETTE[4], label="idle_energy_kwh")
    ax.bar(x, saving, bottom=active + idlee, color="#d9d9d9",
           label="idle-driven saving vs anchor")
    ax.axhline(C.CONTINUOUS_ENERGY_ANCHOR_KWH, color="black", ls="--", lw=1,
               label="anchor 8.4208 kWh")
    for r, xi, a, i, sv in zip(grp, x, active, idlee, saving):
        rows.append({"miner_count": r["miner_count"], "seed": r["seed"],
                     "active_energy_kwh": float(a), "idle_energy_kwh": float(i),
                     "saving_vs_anchor_kwh": float(sv),
                     "total_energy_kwh": r["total_energy_kwh"]})
    ax.set_ylabel("energy (kWh)"); ax.set_xlabel("C2 heterogeneous equal-range runs (N=100 then N=500, by seed)")
    ax.legend(fontsize=7, loc="lower center", ncol=2)
    ax.set_title("H3 [CONFIRMATORY] C2 energy decomposition: active + idle + saving = anchor\n"
                 "saving = Σ idle_time·(P_active − P_idle); identity holds exactly")
    save(fig, "fig05_h3_energy_decomposition",
         "Per-run C2 energy decomposition (idle-bearing, heterogeneous equal ranges). "
         "active+idle energy plus the idle-driven saving reconstruct the accounting "
         "anchor exactly. This bar stack shows a deterministic identity per run, not a "
         "sample summary.",
         "CONFIRMATORY", rows,
         ["miner_count", "seed", "active_energy_kwh", "idle_energy_kwh",
          "saving_vs_anchor_kwh", "total_energy_kwh"])


# ---- FIG 6: H6 inactive miners ----
def fig06():
    fig, axes = plt.subplots(1, 2, figsize=(8.6, 4.2))
    rows = []
    levels = [0.0, 0.05, 0.15, 0.30]
    for ax, outcome, ylab in [(axes[0], "effective_block_interval_s", "effective_block_interval_s"),
                              (axes[1], "accepted_blocks", "accepted_blocks")]:
        groups = []
        for inf in levels:
            if inf == 0.0:
                vals = [r[outcome] for r in runs if r["hypothesis_id"] == "H1;A1"
                        and r["scenario_id"] == "B3_C1_CONTINUOUS_DISJOINT"
                        and r["miner_count"] in (100, 500) and r[outcome] is not None]
            else:
                vals = [r[outcome] for r in by("H6", inactive_fraction=inf)
                        if r[outcome] is not None]
            groups.append((f"{inf:g}", vals))
            for v in vals:
                rows.append({"outcome": outcome, "inactive_fraction": inf, "value": v})
        strip(ax, groups, 601 if outcome[0] == "e" else 611)
        ax.set_ylabel(ylab)
        ax.set_xlabel("inactive_fraction")
    fig.suptitle("H6 [CONFIRMATORY] inactive miners → longer block interval & fewer "
                 "accepted blocks\n(B3/C1 homogeneous equal; baseline 0 = H1;A1; n=60 per "
                 "level; block interval defined for all — no zero-block)")
    save(fig, "fig06_h6_inactive",
         "Effective block interval and accepted blocks vs inactive_fraction; baseline "
         "(0) from the H1;A1 continuous runs. Points are runs; bar=median, whisker=IQR. "
         "No zero-block runs in this family, so block interval is defined throughout.",
         "CONFIRMATORY", rows, ["outcome", "inactive_fraction", "value"])


# ---- FIG 7: H8 mu ----
def fig07():
    fig, axes = plt.subplots(1, 2, figsize=(8.6, 4.2))
    rows = []
    levels = [0.5, 1.0, 2.0]
    for ax, outcome, ylab in [(axes[0], "exhausted_rounds", "exhausted_rounds"),
                              (axes[1], "coord_template_refresh_count", "template refreshes")]:
        groups = []
        for mu in levels:
            if mu == 2.0:
                vals = [r[outcome] for r in runs if r["hypothesis_id"] == "H1;A1"
                        and r["scenario_id"] == "B3_C1_CONTINUOUS_DISJOINT"
                        and r["miner_count"] in (100, 500)]
            else:
                vals = [r[outcome] for r in by("H8", mu=mu)]
            groups.append((f"{mu:g}", vals))
            for v in vals:
                rows.append({"outcome": outcome, "mu": mu, "value": v})
        strip(ax, groups, 701 if outcome[0] == "e" else 711)
        ax.set_ylabel(ylab); ax.set_xlabel("mu (finite-domain factor)")
    fig.suptitle("H8 [CONFIRMATORY] smaller μ → more range exhaustion & template refreshes\n"
                 "(B3/C1 homogeneous equal; baseline μ=2.0 = H1;A1; n=60 per level)")
    save(fig, "fig07_h8_mu",
         "Range exhaustion and template refreshes vs μ; baseline μ=2.0 from the H1;A1 "
         "continuous runs. Points are runs; bar=median, whisker=IQR. Monotone increase "
         "as μ falls.",
         "CONFIRMATORY", rows, ["outcome", "mu", "value"])


# ---- FIG 8: H7 delay single-height diagnostic (count-rate, N kept separate) ----
def fig08():
    from s6_stats import bootstrap_ci_mean_cluster
    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    rows = []
    h7 = by("H7")
    levels = [0.0, 0.42, 5.0, 30.0, 60.0]

    def level_runs(dl, N):
        if dl == 0.42:
            return [r for r in runs if r["hypothesis_id"] == "H1;A1"
                    and r["scenario_id"] == "B3_C1_CONTINUOUS_DISJOINT"
                    and r["miner_count"] == N]
        return [r for r in h7 if r["propagation_delay_mean_s"] == dl
                and r["miner_count"] == N]

    for i, dl in enumerate(levels):
        for N, off, col in [(100, -0.16, PALETTE[0]), (500, 0.16, PALETTE[1])]:
            s = level_runs(dl, N)
            v = np.array([r["single_height_stales_per_accepted_block"] for r in s])
            x = i + off + jitter(v.size, 800 + i * 2 + (0 if N == 100 else 1), w=0.06)
            ax.scatter(x, v, s=12, color=col, alpha=0.6, edgecolors="none", zorder=3)
            m = float(v.mean())
            lo, hi = bootstrap_ci_mean_cluster(v, seed=C.RNG_SEED_BOOTSTRAP)
            ax.plot([i + off, i + off], [lo, hi], color="black", lw=1, zorder=4)
            ax.plot([i + off - 0.08, i + off + 0.08], [m, m], color="black", lw=2, zorder=4)
            for r in s:
                rows.append({"delay_s": dl, "miner_count": N, "seed": r["seed"],
                             "sh_stales_per_accepted_block": r["single_height_stales_per_accepted_block"],
                             "level_mean": m, "cluster_boot_lo": lo, "cluster_boot_hi": hi})
    from matplotlib.lines import Line2D
    ax.legend(handles=[Line2D([0], [0], marker="o", color="w", markerfacecolor=PALETTE[0], label="N = 100 miners"),
                       Line2D([0], [0], marker="o", color="w", markerfacecolor=PALETTE[1], label="N = 500 miners"),
                       Line2D([0], [0], color="black", lw=1, label="run-cluster bootstrap 95% CI")],
              fontsize=7, loc="upper left")
    ax.set_xticks(range(len(levels)))
    ax.set_xticklabels([f"{d:g}" for d in levels])
    ax.set_ylabel("single_height_stales_per_accepted_block (count-rate)")
    ax.set_xlabel("propagation_delay_mean_s")
    ax.set_title("H7 [SECONDARY — SINGLE-HEIGHT STALE-RACE DIAGNOSTIC] delay sensitivity\n"
                 "count-rate per accepted block; N kept separate; NOT a fork-rate or "
                 "security claim; primary metrics unchanged across delay")
    save(fig, "fig08_h7_delay_singleheight",
         "Run-level single-height stales per accepted block vs propagation delay (B3/C1; "
         "N=100 and N=500 shown separately, 30 runs each). Bar = level mean, whisker = "
         "seed/run-cluster bootstrap 95% CI. This is a COUNT-RATE diagnostic (several "
         "distinct miners may stale at one accepted height), so no binomial/Wilson interval "
         "is used. At delay=0, zero stale blocks are observed across the accepted heights. "
         "Secondary diagnostic only; energy, candidate counts, accepted blocks and active "
         "time are identical across delays.",
         "SECONDARY", rows,
         ["delay_s", "miner_count", "seed", "sh_stales_per_accepted_block",
          "level_mean", "cluster_boot_lo", "cluster_boot_hi"])


# ---- FIG 9: zero-block probability by scenario ----
def fig09():
    from s6_stats import wilson_ci
    fig, ax = plt.subplots(figsize=(6.6, 4.0))
    rows = []
    order = [("B0", "B0"), ("B1", "B1"), ("B2", "B2"),
             ("B3/C1", "B3_C1_CONTINUOUS_DISJOINT"), ("C2", "C2")]
    xs, ps, los, his = [], [], [], []
    for i, (lab, sc) in enumerate(order):
        s = [r for r in runs if r["scenario_id"] == sc]
        k = sum(1 for r in s if r["accepted_blocks"] == 0)
        n = len(s)
        p = k / n
        lo, hi = wilson_ci(k, n)
        xs.append(i); ps.append(p)
        los.append(max(0.0, p - lo)); his.append(max(0.0, hi - p))
        rows.append({"scenario": sc, "n": n, "zero_block": k, "prob": p,
                     "wilson_lo": lo, "wilson_hi": hi})
    ax.errorbar(xs, ps, yerr=[los, his], fmt="o", color=PALETTE[0], capsize=3)
    ax.set_xticks(xs); ax.set_xticklabels([o[0] for o in order])
    ax.set_ylabel("P(zero accepted blocks)")
    ax.set_xlabel("scenario (all runs incl. all miner counts)")
    ax.set_title("[DESCRIPTIVE] zero-block probability by scenario (Wilson 95% CI)\n"
                 "B1 near-certain zero-block (redundant common-template search)")
    save(fig, "fig09_zero_block",
         "Zero-block probability per scenario with Wilson 95% intervals. Zero-block runs "
         "are retained, never discarded; block-normalised metrics stay NA for them.",
         "DESCRIPTIVE", rows,
         ["scenario", "n", "zero_block", "prob", "wilson_lo", "wilson_hi"])


# ---- FIG 10: H5x exploratory (heterogeneous_high) ----
def fig10():
    fig, ax = plt.subplots(figsize=(6.2, 4.0))
    rows = []
    groups = []
    for N in (100, 500):
        vals = [r["completion_time_std_s"] for r in by("H5x", miner_count=N)]
        groups.append((f"hetero_high N={N}", vals))
        for r in by("H5x", miner_count=N):
            rows.append({"miner_count": N, "seed": r["seed"],
                         "completion_time_std_s": r["completion_time_std_s"]})
    strip(ax, groups, 1001)
    ax.set_ylabel("completion_time_std_s")
    ax.set_title("H5x [EXPLORATORY — NOT PREREGISTERED FOR CONFIRMATORY INFERENCE]\n"
                 "high heterogeneity, equal ranges: completion dispersion")
    save(fig, "fig10_h5x_exploratory",
         "Exploratory completion-time dispersion under high heterogeneity with equal "
         "ranges (B3/C1, equal). Exploratory only — not used to confirm any hypothesis.",
         "EXPLORATORY", rows, ["miner_count", "seed", "completion_time_std_s"])


def main():
    for f in (fig01, fig02, fig03, fig04, fig05, fig06, fig07, fig08, fig09, fig10):
        f()
    with open(os.path.join(FIG, "figures_index.json"), "w") as fh:
        json.dump(INDEX, fh, indent=1)
        fh.write("\n")
    print(f"wrote {len(INDEX)} figures (pdf+png) + plot_data + figures_index.json")


if __name__ == "__main__":
    main()
