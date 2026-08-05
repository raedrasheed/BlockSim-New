#!/usr/bin/env python3
"""Stage 8U — deterministic figure/table generator (FIG01..FIG18).

    python generate_8u.py            # write all figures + captions + index + checksums
    python generate_8u.py --check    # regenerate tables/captions/metadata, verify bytes

Every figure ships as SVG + 300-dpi PNG + source CSV + caption markdown + metadata JSON
+ checksum file.  Tables and metadata are byte-identical across regenerations (the
U-TEST-22 core in figures_8u.py); SVGs use a fixed hashsalt and carry no date.  Style:
Okabe-Ito colour-blind-safe palette, no 3D, no truncated bars, paired per-seed points
visible, means with 95% bootstrap CIs (deterministic substreams of the frozen analysis
root).  FIG17 is descriptive only — it carries NO cross-stage inferential statistic.
"""
from __future__ import annotations

import csv
import glob
import hashlib
import json
import pathlib
import random
import statistics
import sys

import matplotlib
matplotlib.use("Agg")
matplotlib.rcParams["svg.hashsalt"] = "stage8u"
import matplotlib.pyplot as plt                                            # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
DOCS = REPO_ROOT / "docs" / "thesis_revision_v45" / "stage_08u"
FIGDIR = DOCS / "figures"
DATASET = DOCS / "STAGE_08U_RUN_DATASET.csv"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO_ROOT))
import scenarios_8u as S8U                                                 # noqa: E402
import figures_8u as F8U                                                   # noqa: E402

ROOT_SEED = S8U.ANALYSIS_SEED_8U
B = 10_000
W00, W01 = "W00_POW_POPULATION_MATCHED", "W01_POW_ACTIVE_CAPACITY_MATCHED"
P00, P01, P02 = "P00_POCOL_NO_FLOOR", "P01_POCOL_STAGE8S_COARSE", "P02_POCOL_SINGLE_HANDOFF"
ORDER = [W00, W01, P00, P01, P02]
SHORT = {W00: "W00", W01: "W01", P00: "P00", P01: "P01", P02: "P02"}
COL = F8U.SCENARIO_COLORS

SLUG = {
    "FIG01": "total_energy", "FIG02": "relative_energy_vs_pow",
    "FIG03": "accepted_blocks", "FIG04": "round_durations",
    "FIG05": "energy_per_block", "FIG06": "evaluations",
    "FIG07": "blocks_per_million_evals", "FIG08": "residency",
    "FIG09": "energy_decomposition", "FIG10": "floors", "FIG11": "churn",
    "FIG12": "pareto", "FIG13": "energy_slopes", "FIG14": "service_slopes",
    "FIG15": "timeline", "FIG16": "heatmap", "FIG17": "policy_evolution",
    "FIG18": "decision_dashboard",
}

RESIDENCY_COMPONENTS = ("PRIMARY_ACTIVE_HASHING", "PRIMARY_LOW_POWER_LISTEN",
                        "RESERVE_STANDBY", "RESERVE_WAKING",
                        "ACTIVATED_RESERVE_HASHING", "OFFLINE",
                        "COORDINATION_AND_VERIFICATION")
ENERGY_COMPONENTS = ("primary_hashing", "range_idle", "reserve_standby",
                     "wake_transient", "activated_reserve_hashing", "offline_other")


def load():
    with open(DATASET, newline="") as fh:
        rows = list(csv.DictReader(fh))
    by = {}
    for r in rows:
        by.setdefault(r["scenario_id"], []).append(r)
    for rs in by.values():
        rs.sort(key=lambda r: int(r["seed_index"]))
    return by


def f(row, field):
    v = row.get(field)
    return None if v in (None, "", "None") else float(v)


def vals(rows, field):
    return [f(r, field) for r in rows]


def boot_ci(values, label):
    xs = [v for v in values if v is not None]
    rng = random.Random(f"{ROOT_SEED}:FIGBOOT:{label}")
    n = len(xs)
    stats = sorted(statistics.fmean([xs[rng.randrange(n)] for _ in range(n)])
                   for _ in range(B))
    return statistics.fmean(xs), stats[249], stats[9749]


def sha(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Artifacts:
    def __init__(self):
        self.captions = {}
        self.index_rows = []
        self.check_failures = []
        self.check_mode = False

    def emit(self, fig_id, fig, rows, fieldnames, caption, scenario_ids):
        slug = SLUG[fig_id]
        base = FIGDIR / f"{fig_id}_{slug}"
        csv_text = F8U.serialize_table(rows, fieldnames)
        meta = F8U.figure_metadata(fig_id, f"{fig_id}_{slug}.csv", scenario_ids)
        meta_text = json.dumps(meta, indent=1, sort_keys=True) + "\n"
        cap_text = f"# {fig_id} — {meta['title']}\n\n{caption}\n"
        if self.check_mode:
            for suffix, text in ((".csv", csv_text), (".metadata.json", meta_text),
                                 ("_caption.md", cap_text)):
                p = base.parent / (base.name + suffix)
                if not p.exists() or p.read_text() != text:
                    self.check_failures.append(base.name + suffix)
            plt.close(fig)
            return
        FIGDIR.mkdir(parents=True, exist_ok=True)
        (base.parent / (base.name + ".csv")).write_text(csv_text)
        (base.parent / (base.name + ".metadata.json")).write_text(meta_text)
        (base.parent / (base.name + "_caption.md")).write_text(cap_text)
        fig.savefig(base.parent / (base.name + ".svg"), format="svg",
                    metadata={"Date": None}, bbox_inches="tight")
        fig.savefig(base.parent / (base.name + ".png"), format="png", dpi=300,
                    bbox_inches="tight")
        plt.close(fig)
        files = [base.name + s for s in
                 (".svg", ".png", ".csv", "_caption.md", ".metadata.json")]
        chk = "".join(f"{sha(FIGDIR / n)}  {n}\n" for n in files)
        (base.parent / (base.name + ".sha256")).write_text(chk)
        self.captions[fig_id] = cap_text
        self.index_rows.append({"figure_id": fig_id, "title": meta["title"],
                                "files": files, "checksum_file": base.name + ".sha256"})


ART = Artifacts()


def scen_axis(ax, label, scen=None):
    scen = scen or ORDER
    ax.set_xticks(range(len(scen)))
    ax.set_xticklabels([SHORT[s] for s in scen])
    ax.set_ylabel(label)
    ax.grid(True, axis="y", alpha=0.3)


def points_mean_ci(fig_id, by, field, ylabel, caption, scen=ORDER):
    rows, fieldnames = [], ["scenario_id", "seed_index", "value"]
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    for i, sid in enumerate(scen):
        xs = vals(by[sid], field)
        for j, v in enumerate(xs):
            rows.append({"scenario_id": sid, "seed_index": j, "value": v})
        pres = [v for v in xs if v is not None]
        jit = [i + (j - 5.5) * 0.03 for j in range(len(pres))]
        ax.scatter(jit, pres, s=18, color=COL[sid], alpha=0.75, zorder=3)
        if pres:
            m, lo, hi = boot_ci(pres, f"{fig_id}:{sid}")
            ax.errorbar([i], [m], yerr=[[m - lo], [hi - m]], fmt="D", color="black",
                        markerfacecolor=COL[sid], capsize=5, zorder=4, markersize=7)
            rows.append({"scenario_id": sid, "seed_index": "MEAN", "value": m})
            rows.append({"scenario_id": sid, "seed_index": "CI95_LOW", "value": lo})
            rows.append({"scenario_id": sid, "seed_index": "CI95_HIGH", "value": hi})
    scen_axis(ax, ylabel, scen)
    ax.set_ylim(bottom=0)                                  # never a truncated axis
    ART.emit(fig_id, fig, rows, fieldnames, caption, scen)


def main(check=False) -> int:
    ART.check_mode = check
    by = load()
    palette = list(F8U.PALETTE.values())

    # FIG01 -----------------------------------------------------------------------
    points_mean_ci(
        "FIG01", by, "E_idle_kwh", "total energy per run (kWh)",
        "Total executed energy per 300 s run for the two matched same-template PoW "
        "controls and the three PoCol arms; per-seed points with means and 95% "
        "bootstrap CIs.  Controlled simulator comparison — not a claim about any "
        "deployed network.")

    # FIG02 -----------------------------------------------------------------------
    rows, fn = [], ["control", "pocol_scenario", "seed_index", "relative_reduction"]
    fig, axes = plt.subplots(1, 2, figsize=(9.5, 4.2), sharey=True)
    for ax, ctrl in zip(axes, (W00, W01)):
        for k, pid in enumerate((P00, P01, P02)):
            rel = [(f(c, "E_idle_kwh") - f(t, "E_idle_kwh")) / f(c, "E_idle_kwh")
                   for t, c in zip(by[pid], by[ctrl])]
            for j, v in enumerate(rel):
                rows.append({"control": ctrl, "pocol_scenario": pid, "seed_index": j,
                             "relative_reduction": v})
            m, lo, hi = boot_ci(rel, f"FIG02:{ctrl}:{pid}")
            rows += [{"control": ctrl, "pocol_scenario": pid, "seed_index": "MEAN",
                      "relative_reduction": m},
                     {"control": ctrl, "pocol_scenario": pid, "seed_index": "CI95_LOW",
                      "relative_reduction": lo},
                     {"control": ctrl, "pocol_scenario": pid, "seed_index": "CI95_HIGH",
                      "relative_reduction": hi}]
            jit = [k + (j - 5.5) * 0.03 for j in range(len(rel))]
            ax.scatter(jit, rel, s=16, color=COL[pid], alpha=0.75, zorder=3)
            ax.errorbar([k + 0.22], [m], yerr=[[m - lo], [hi - m]], fmt="D",
                        color="black", markerfacecolor=COL[pid], capsize=4, zorder=4,
                        markersize=6)
        ax.axhline(0.0, color="black", lw=0.8)
        ax.set_xticks(range(3))
        ax.set_xticklabels([SHORT[P00], SHORT[P01], SHORT[P02]])
        ax.set_title(f"versus {SHORT[ctrl]}", fontsize=10)
        ax.grid(True, axis="y", alpha=0.3)
    axes[0].set_ylabel("relative energy reduction (E_ctrl − E_PoCol)/E_ctrl")
    ART.emit("FIG02", fig, rows, fn,
             "Per-seed paired relative total-energy difference of every PoCol arm "
             "against each matched PoW control, shown separately (W00 "
             "population-matched is SENSITIVITY; W01 active-capacity-matched carries "
             "the preregistered H-U3 gate).  The two controls answer different "
             "matching questions and are never merged.", ORDER)

    # FIG03 -----------------------------------------------------------------------
    points_mean_ci(
        "FIG03", by, "rounds_accepted", "accepted blocks per run",
        "Accepted blocks per 300 s run; per-seed points with means and 95% bootstrap "
        "CIs.  The preregistered H-U2 service gate compares P02 with W01 only.")

    # FIG04 -----------------------------------------------------------------------
    rows, fn = [], ["scenario_id", "metric", "seed_index", "value_s"]
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.2))
    for ax, field, lab in ((axes[0], "median_round_duration", "median"),
                           (axes[1], "p95_round_duration", "p95")):
        for i, sid in enumerate(ORDER):
            xs = [v for v in vals(by[sid], field) if v is not None]
            for j, v in enumerate(xs):
                rows.append({"scenario_id": sid, "metric": lab, "seed_index": j,
                             "value_s": v})
            m, lo, hi = boot_ci(xs, f"FIG04:{lab}:{sid}")
            rows += [{"scenario_id": sid, "metric": lab, "seed_index": "MEAN",
                      "value_s": m},
                     {"scenario_id": sid, "metric": lab, "seed_index": "CI95_LOW",
                      "value_s": lo},
                     {"scenario_id": sid, "metric": lab, "seed_index": "CI95_HIGH",
                      "value_s": hi}]
            jit = [i + (j - 5.5) * 0.03 for j in range(len(xs))]
            ax.scatter(jit, xs, s=16, color=COL[sid], alpha=0.75, zorder=3)
            ax.errorbar([i], [m], yerr=[[m - lo], [hi - m]], fmt="D", color="black",
                        markerfacecolor=COL[sid], capsize=4, zorder=4, markersize=6)
        scen_axis(ax, f"{lab} closed-round duration (s)")
        ax.set_ylim(bottom=0)
    ART.emit("FIG04", fig, rows, fn,
             "Median (left panel) and 95th-percentile (right panel) closed-round "
             "durations per run, in separate panels as preregistered; per-seed points "
             "with means and 95% bootstrap CIs.", ORDER)

    # FIG05 -----------------------------------------------------------------------
    points_mean_ci(
        "FIG05", by, "energy_per_accepted_block_kwh", "energy per accepted block (kWh)",
        "Energy per accepted block.  A run with zero accepted blocks is recorded as NA "
        "and excluded from the mean rather than imputed; no such run occurred among the "
        "60 confirmatory runs.")

    # FIG06 -----------------------------------------------------------------------
    rows, fn = [], ["scenario_id", "metric", "seed_index", "value"]
    fig, ax = plt.subplots(figsize=(8.5, 4.4))
    metrics = [("total_physical_evaluations", "total"),
               ("unique_physical_evaluations", "unique"),
               ("duplicate_physical_evaluations", "duplicate")]
    width = 0.8 / len(metrics)
    for k, (field, lab) in enumerate(metrics):
        means, offs = [], []
        for i, sid in enumerate(ORDER):
            xs = [v for v in vals(by[sid], field) if v is not None]
            for j, v in enumerate(xs):
                rows.append({"scenario_id": sid, "metric": lab, "seed_index": j,
                             "value": v})
            m = statistics.fmean(xs)
            rows.append({"scenario_id": sid, "metric": lab, "seed_index": "MEAN",
                         "value": m})
            off = i + (k - 1) * width
            means.append(m)
            offs.append(off)
            ax.scatter([off] * len(xs), xs, s=8, color="black", alpha=0.45, zorder=4)
        ax.bar(offs, means, width=width * 0.92, label=lab, color=palette[k], zorder=2)
    scen_axis(ax, "physical evaluations per run")
    ax.set_ylim(bottom=0)
    ax.legend(fontsize=8)
    ART.emit("FIG06", fig, rows, fn,
             "Total, unique and duplicate committed physical SHA-256 evaluations per "
             "run.  PoCol's disjoint-range coordination holds duplicates at exactly "
             "zero; the uncoordinated matched PoW controls duplicate most of their "
             "work.  Bars are means, black points the 12 per-seed values; the axis "
             "starts at zero.", ORDER)

    # FIG07 -----------------------------------------------------------------------
    points_mean_ci(
        "FIG07", by, "blocks_per_million_physical_evaluations",
        "accepted blocks per million evaluations",
        "Work-efficiency of service: accepted blocks per million committed physical "
        "evaluations; per-seed points with means and 95% bootstrap CIs.")

    # FIG08 -----------------------------------------------------------------------
    rows, fn = [], ["scenario_id", "component", "mean_residency_s"]
    fig, ax = plt.subplots(figsize=(9, 4.6))
    bottoms = [0.0] * len(ORDER)
    for k, comp in enumerate(RESIDENCY_COMPONENTS):
        heights = []
        for sid in ORDER:
            if sid in (W00, W01):
                if comp == "PRIMARY_ACTIVE_HASHING":
                    v = statistics.fmean(f(r, "mining_node_count") * 300.0
                                         for r in by[sid])
                elif comp == "RESERVE_STANDBY":
                    v = statistics.fmean(f(r, "standby_node_count") * 300.0
                                         for r in by[sid])
                else:
                    v = 0.0
            else:
                v = statistics.fmean(f(r, f"residency_{comp}_s") for r in by[sid])
            heights.append(v)
            rows.append({"scenario_id": sid, "component": comp, "mean_residency_s": v})
        ax.bar(range(len(ORDER)), heights, bottom=bottoms, label=comp,
               color=palette[k % 8], width=0.62)
        bottoms = [b + h for b, h in zip(bottoms, heights)]
    scen_axis(ax, "mean node-seconds per run")
    ax.legend(fontsize=7, loc="center left", bbox_to_anchor=(1.0, 0.5))
    ART.emit("FIG08", fig, rows, fn,
             "Stacked mean per-state residency (node-seconds; the whole population is "
             "20 nodes × 300 s).  The matched PoW controls hold every mining node in "
             "ACTIVE_HASHING for the entire horizon — W01 additionally holds 4 "
             "non-mining standby nodes at RESERVE_STANDBY — while the PoCol arms spend "
             "most node-time in LOW_POWER_LISTEN once assigned ranges complete.", ORDER)

    # FIG09 -----------------------------------------------------------------------
    def energy_components(sid):
        if sid in (W00, W01):
            act = statistics.fmean(f(r, "energy_kwh_active_hashing") for r in by[sid])
            res = statistics.fmean(f(r, "energy_kwh_reserve_standby") for r in by[sid])
            return {"primary_hashing": act, "range_idle": 0.0, "reserve_standby": res,
                    "wake_transient": 0.0, "activated_reserve_hashing": 0.0,
                    "offline_other": 0.0}
        g = lambda c: statistics.fmean(f(r, f"energy_{c}_kwh") for r in by[sid])
        return {"primary_hashing": g("PRIMARY_ACTIVE_HASHING"),
                "range_idle": g("PRIMARY_LOW_POWER_LISTEN"),
                "reserve_standby": g("RESERVE_STANDBY"),
                "wake_transient": g("RESERVE_WAKING"),
                "activated_reserve_hashing": g("ACTIVATED_RESERVE_HASHING"),
                "offline_other": g("OFFLINE") + g("COORDINATION_AND_VERIFICATION")}

    rows, fn = [], ["scenario_id", "component", "mean_energy_kwh"]
    fig, ax = plt.subplots(figsize=(9, 4.6))
    bottoms = [0.0] * len(ORDER)
    for k, comp in enumerate(ENERGY_COMPONENTS):
        heights = []
        for sid in ORDER:
            v = energy_components(sid)[comp]
            heights.append(v)
            rows.append({"scenario_id": sid, "component": comp, "mean_energy_kwh": v})
        ax.bar(range(len(ORDER)), heights, bottom=bottoms, label=comp,
               color=palette[k % 8], width=0.62)
        bottoms = [b + h for b, h in zip(bottoms, heights)]
    scen_axis(ax, "mean energy per run (kWh)")
    ax.legend(fontsize=8, loc="center left", bbox_to_anchor=(1.0, 0.5))
    ART.emit("FIG09", fig, rows, fn,
             "Stacked mean energy decomposition per run: primary hashing, range idle "
             "(LOW_POWER_LISTEN), reserve standby, wake transient, activated-reserve "
             "hashing and offline/other.  Reserve and wake components are reported "
             "separately from range-idle, as preregistered — the two savings are never "
             "combined into a single figure.", ORDER)

    # FIG10 -----------------------------------------------------------------------
    pscen = [P00, P01, P02]
    rows, fn = [], ["scenario_id", "metric", "seed_index", "value"]
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.2))
    for ax, fields, labs, ylab in (
            (axes[0], ("duration_below_static_floor", "duration_below_useful_floor"),
             ("below static floor", "below useful floor"), "duration (s)"),
            (axes[1], ("static_floor_deficit_area_hash_s", "useful_floor_deficit_area"),
             ("static deficit area", "useful deficit area"), "deficit area (hash·s)")):
        width = 0.35
        for k, (field, lab) in enumerate(zip(fields, labs)):
            means, offs = [], []
            for i, sid in enumerate(pscen):
                xs = [v for v in vals(by[sid], field) if v is not None]
                for j, v in enumerate(xs):
                    rows.append({"scenario_id": sid, "metric": lab, "seed_index": j,
                                 "value": v})
                m = statistics.fmean(xs)
                rows.append({"scenario_id": sid, "metric": lab, "seed_index": "MEAN",
                             "value": m})
                off = i + (k - 0.5) * width
                means.append(m)
                offs.append(off)
                ax.scatter([off] * len(xs), xs, s=8, color="black", alpha=0.45,
                           zorder=4)
            ax.bar(offs, means, width=width * 0.92, label=lab, color=palette[k],
                   zorder=2)
        ax.set_xticks(range(len(pscen)))
        ax.set_xticklabels([SHORT[s] for s in pscen])
        ax.set_ylabel(ylab)
        ax.set_ylim(bottom=0)
        ax.grid(True, axis="y", alpha=0.3)
        ax.legend(fontsize=8)
    ART.emit("FIG10", fig, rows, fn,
             "Static-floor and useful-floor families for the PoCol arms, reported "
             "independently (U5: the historical static floor is never lowered or "
             "redefined): durations below each floor (left) and deficit areas (right).  "
             "Bars are means; black points are per-seed values.", pscen)

    # FIG11 -----------------------------------------------------------------------
    rows, fn = [], ["scenario_id", "metric", "seed_index", "value_per_closed_round"]
    fig, ax = plt.subplots(figsize=(8.5, 4.4))
    metrics = [("activations_per_closed_round", None, "activation requests"),
               ("incomplete_activation_request_count", "rounds_executed",
                "incomplete activations"),
               ("handoffs_per_closed_round", None, "handoffs"),
               ("reassignments_per_closed_round", None, "reassignments")]
    width = 0.8 / len(metrics)
    for k, (field, per, lab) in enumerate(metrics):
        means, offs = [], []
        for i, sid in enumerate(pscen):
            xs = []
            for j, r in enumerate(by[sid]):
                v = f(r, field)
                v = 0.0 if v is None else v
                if per:
                    v = v / max(1.0, f(r, per))
                xs.append(v)
                rows.append({"scenario_id": sid, "metric": lab, "seed_index": j,
                             "value_per_closed_round": v})
            m = statistics.fmean(xs)
            rows.append({"scenario_id": sid, "metric": lab, "seed_index": "MEAN",
                         "value_per_closed_round": m})
            off = i + (k - 1.5) * width
            means.append(m)
            offs.append(off)
            ax.scatter([off] * len(xs), xs, s=8, color="black", alpha=0.45, zorder=4)
        ax.bar(offs, means, width=width * 0.92, label=lab, color=palette[k], zorder=2)
    ax.set_xticks(range(len(pscen)))
    ax.set_xticklabels([SHORT[s] for s in pscen])
    ax.set_ylabel("events per closed round")
    ax.set_ylim(bottom=0)
    ax.grid(True, axis="y", alpha=0.3)
    ax.legend(fontsize=8)
    ART.emit("FIG11", fig, rows, fn,
             "Controller churn per closed round for the PoCol arms: activation "
             "requests, incomplete activations, committed handoffs and total "
             "reassignments.  The single-handoff arm removes reserve-wake churn "
             "entirely and holds reassignments below one per round by construction.",
             pscen)

    # FIG12 -----------------------------------------------------------------------
    rows, fn = [], ["scenario_id", "seed_index", "energy_kwh", "accepted_blocks"]
    fig, ax = plt.subplots(figsize=(7.5, 5.2))
    for sid in ORDER:
        es = vals(by[sid], "E_idle_kwh")
        bs = vals(by[sid], "rounds_accepted")
        for j, (e, b_) in enumerate(zip(es, bs)):
            rows.append({"scenario_id": sid, "seed_index": j, "energy_kwh": e,
                         "accepted_blocks": b_})
        ax.scatter(bs, es, s=20, color=COL[sid], alpha=0.7, label=SHORT[sid])
        ce, cb = statistics.fmean(es), statistics.fmean(bs)
        rows.append({"scenario_id": sid, "seed_index": "CENTROID", "energy_kwh": ce,
                     "accepted_blocks": cb})
        ax.scatter([cb], [ce], s=200, color=COL[sid], edgecolor="black", marker="*",
                   zorder=5)
    ax.set_xlabel("accepted blocks per run (service)")
    ax.set_ylabel("total energy per run (kWh)")
    ax.set_xlim(left=0)
    ax.set_ylim(bottom=0)
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=8)
    ART.emit("FIG12", fig, rows, fn,
             "Energy–service plane: one point per seed plus scenario centroids "
             "(stars).  Lower is cheaper, further right is more service; the PoCol "
             "arms sit far below the matched PoW controls in energy at reduced block "
             "counts.", ORDER)

    # FIG13 / FIG14 ---------------------------------------------------------------
    for fig_id, field, ylab, capn in (
            ("FIG13", "E_idle_kwh", "total energy per run (kWh)",
             "Paired per-seed energy slopes from each matched PoW control to the "
             "single-handoff PoCol arm (left: W01, the preregistered gate control; "
             "right: W00, sensitivity).  Every seed's line falls."),
            ("FIG14", "rounds_accepted", "accepted blocks per run",
             "Paired per-seed service slopes (accepted blocks) from each matched PoW "
             "control to the single-handoff PoCol arm (left: W01 gate control; right: "
             "W00 sensitivity).  Every seed's line falls, which is why the "
             "preregistered H-U2 block-ratio gate fails.")):
        rows, fn = [], ["control", "seed_index", "control_value", "p02_value"]
        fig, axes = plt.subplots(1, 2, figsize=(9, 4.2), sharey=True)
        for ax, ctrl in zip(axes, (W01, W00)):
            cv = vals(by[ctrl], field)
            pv = vals(by[P02], field)
            for j, (c, p) in enumerate(zip(cv, pv)):
                rows.append({"control": ctrl, "seed_index": j, "control_value": c,
                             "p02_value": p})
                ax.plot([0, 1], [c, p], color=COL[ctrl], alpha=0.55, lw=1.2)
                ax.scatter([0, 1], [c, p], s=14, color=[COL[ctrl], COL[P02]], zorder=3)
            ax.set_xticks([0, 1])
            ax.set_xticklabels([SHORT[ctrl], "P02"])
            ax.set_xlim(-0.3, 1.3)
            ax.grid(True, axis="y", alpha=0.3)
            ax.set_title(f"{SHORT[ctrl]} → P02", fontsize=10)
        axes[0].set_ylabel(ylab)
        axes[0].set_ylim(bottom=0)
        ART.emit(fig_id, fig, rows, fn, capn, [W00, W01, P02])

    # FIG15 -----------------------------------------------------------------------
    import Models.PoCol.stage2.simulator as SIM                        # noqa: PLC0415
    from Models.PoCol.stage2.simulator import run_simulation           # noqa: PLC0415
    samples = []
    orig = SIM._update_pipeline_stats

    def wrapped(run_ctx, rc, now):
        h_eff, pipe = orig(run_ctx, rc, now)
        samples.append((now, h_eff, pipe, run_ctx._useful_last_target))
        return h_eff, pipe

    SIM._update_pipeline_stats = wrapped
    try:
        seed0 = S8U.confirmatory_seeds_8u()[0]
        cfg0 = S8U.build_config_8u(S8U.SCENARIOS[4], seed0)
        run0 = run_simulation(cfg0, run_id="8u-fig15-p02-s00")
    finally:
        SIM._update_pipeline_stats = orig
    t_lo, t_hi = 0.0, 30.0                                # representative window
    win = sorted([s for s in samples if t_lo <= s[0] <= t_hi], key=lambda x: x[0])
    accepts = sorted({rec.completion_time for rec in run0.evaluation_ledger
                      if rec.contained_solution and t_lo <= rec.completion_time <= t_hi})
    handoffs = sorted(e.opened_at for e in run0.handoff_epochs.values()
                      if e.status in ("COMMITTED", "COMPLETED", "ROUND_CLOSED")
                      and t_lo <= e.opened_at <= t_hi)
    wakes = sorted(q_.seated_at for q_ in run0.activation_requests.values()
                   if t_lo <= q_.seated_at <= t_hi)
    rows = [{"time_s": t, "H_effective": h, "H_pipeline": p, "H_useful_target": u}
            for (t, h, p, u) in win]
    fn = ["time_s", "H_effective", "H_pipeline", "H_useful_target"]
    fig, ax = plt.subplots(figsize=(10, 4.4))
    ts = [x[0] for x in win]
    ax.step(ts, [x[1] for x in win], where="post", color=COL[P02],
            label="H_effective (physical)", lw=1.4)
    ax.step(ts, [x[2] for x in win], where="post", color=F8U.PALETTE["blue"],
            label="H_pipeline (forecast only)", lw=1.0, alpha=0.8)
    ax.step(ts, [x[3] for x in win], where="post", color=F8U.PALETTE["orange"],
            label="H_useful_target", lw=1.0)
    ax.axhline(3200.0, color="black", ls="--", lw=1.0, label="static floor (3200 H)")
    for i, t in enumerate(accepts):
        ax.axvline(t, color=F8U.PALETTE["bluish_green"], alpha=0.25, lw=0.8,
                   label="accepted block" if i == 0 else None)
    for i, t in enumerate(handoffs):
        ax.axvline(t, color=F8U.PALETTE["vermillion"], ls=":", lw=1.4,
                   label="handoff committed" if i == 0 else None)
    for i, t in enumerate(wakes):
        ax.axvline(t, color=F8U.PALETTE["reddish_purple"], ls="-.", lw=1.4,
                   label="reserve wake request" if i == 0 else None)
    ax.set_xlabel("simulation time (s)")
    ax.set_ylabel("hash rate (nonces/s)")
    ax.set_ylim(bottom=0)
    ax.legend(fontsize=7, loc="lower right")
    ART.emit("FIG15", fig, rows, fn,
             f"Representative P02 timeline (confirmatory seed 0, first {t_hi:.0f} s of "
             "the horizon): physical H_effective, the H_pipeline scheduling forecast "
             "(never a security metric), the useful-work-aware target, the historical "
             "static 3200 H floor, accepted blocks (vertical bands), committed "
             "handoffs (dotted) and reserve-wake requests (dash-dotted).", [P02])

    # FIG16 -----------------------------------------------------------------------
    metrics16 = [("E_idle_kwh", "energy"), ("rounds_accepted", "blocks"),
                 ("median_round_duration", "median duration"),
                 ("p95_round_duration", "p95 duration"),
                 ("total_physical_evaluations", "total evaluations"),
                 ("duplicate_physical_evaluations", "duplicate evaluations"),
                 ("blocks_per_million_physical_evaluations", "blocks per M evals"),
                 ("energy_per_accepted_block_kwh", "energy per block"),
                 ("activations_per_closed_round", "activations per round")]
    rows, fn = [], ["metric", "scenario_id", "mean_value", "normalised"]
    grid = []
    for field, lab in metrics16:
        ms = []
        for sid in ORDER:
            xs = [v for v in vals(by[sid], field) if v is not None]
            ms.append(statistics.fmean(xs) if xs else 0.0)
        lo, hi = min(ms), max(ms)
        norm = [(m - lo) / (hi - lo) if hi > lo else 0.0 for m in ms]
        grid.append(norm)
        for sid, m, n in zip(ORDER, ms, norm):
            rows.append({"metric": lab, "scenario_id": sid, "mean_value": m,
                         "normalised": n})
    fig, ax = plt.subplots(figsize=(7.5, 5.0))
    im = ax.imshow(grid, cmap="cividis", aspect="auto", vmin=0.0, vmax=1.0)
    ax.set_xticks(range(len(ORDER)))
    ax.set_xticklabels([SHORT[s] for s in ORDER])
    ax.set_yticks(range(len(metrics16)))
    ax.set_yticklabels([lab for _f, lab in metrics16], fontsize=8)
    for yi in range(len(metrics16)):
        for xi in range(len(ORDER)):
            ax.text(xi, yi, f"{grid[yi][xi]:.2f}", ha="center", va="center", fontsize=7,
                    color="white" if grid[yi][xi] < 0.5 else "black")
    fig.colorbar(im, ax=ax, label="normalised per metric (min→0, max→1)")
    ART.emit("FIG16", fig, rows, fn,
             "Normalised summary heatmap of scenario means; each metric row is scaled "
             "min→0 and max→1 with the raw means preserved in the source CSV.  A "
             "perceptually uniform, colour-blind-safe colormap is used; the "
             "normalisation direction carries no value judgement — integrity gates "
             "passed in all 60 runs and are therefore constant across the panel.",
             ORDER)

    # FIG17 -----------------------------------------------------------------------
    m03 = [json.load(open(p)) for p in sorted(glob.glob(str(
        REPO_ROOT / "experiments/thesis_revision_v45/stage_07m/runs/7m-M03_*-s*.json")))]
    with open(REPO_ROOT / "docs/thesis_revision_v45/stage_08r/STAGE_08R_RUN_DATASET.csv",
              newline="") as fh:
        r02 = [r for r in csv.DictReader(fh)
               if r["scenario_id"] == "R02_REVISED_CONTROLLER"]
    with open(REPO_ROOT / "docs/thesis_revision_v45/stage_08s/STAGE_08S_RUN_DATASET.csv",
              newline="") as fh:
        s03 = [r for r in csv.DictReader(fh)
               if r["scenario_id"] == "S03_USEFUL_FLOOR_COARSE_REASSIGNMENT"]
    stages = [
        ("8M (M03)", statistics.fmean(r["rounds_accepted"] for r in m03),
         statistics.fmean(r["reserve_activations_seated"] for r in m03),
         statistics.fmean(r["total_duration_below_floor"] for r in m03)),
        ("8R (R02)", statistics.fmean(float(r["rounds_accepted"]) for r in r02),
         statistics.fmean(float(r["activation_requests_seated"]) for r in r02),
         statistics.fmean(float(r["total_duration_below_floor"]) for r in r02)),
        ("8S (S03)", statistics.fmean(float(r["rounds_accepted"]) for r in s03),
         statistics.fmean(float(r["activation_requests_seated"]) for r in s03),
         statistics.fmean(float(r["duration_below_static_floor"]) for r in s03)),
        ("8U (P02)", statistics.fmean(float(r["rounds_accepted"]) for r in by[P02]),
         statistics.fmean(float(r["activation_requests_seated"]) for r in by[P02]),
         statistics.fmean(float(r["duration_below_static_floor"]) for r in by[P02])),
    ]
    rows = [{"stage": s, "mean_accepted_blocks": b, "mean_activation_requests": a,
             "mean_duration_below_static_floor_s": d} for s, b, a, d in stages]
    fn = ["stage", "mean_accepted_blocks", "mean_activation_requests",
          "mean_duration_below_static_floor_s"]
    fig, axes = plt.subplots(1, 3, figsize=(11, 3.8))
    labels = [s for s, *_ in stages]
    for ax, idx, ylab in ((axes[0], 1, "mean accepted blocks"),
                          (axes[1], 2, "mean activation requests"),
                          (axes[2], 3, "mean s below static floor")):
        ys = [row[idx] for row in stages]
        ax.plot(range(4), ys, "-o", color=COL[P02])
        ax.set_xticks(range(4))
        ax.set_xticklabels(labels, fontsize=8)
        ax.set_ylabel(ylab, fontsize=9)
        ax.set_ylim(bottom=0)
        ax.grid(True, axis="y", alpha=0.3)
    ART.emit("FIG17", fig, rows, fn,
             "DESCRIPTIVE ONLY: policy evolution across the frozen primary arms of "
             "stages 8M (legacy reactive), 8R (predictive static floor), 8S (coarse "
             "reassignment) and 8U (single handoff).  Each stage used its own fresh "
             "seed registry, so NO cross-stage inferential statistic or p-value is "
             "computed or implied.", [P02])

    # FIG18 -----------------------------------------------------------------------
    results = json.loads((HERE / "stage8u_results.json").read_text())
    crits = []
    for h in ("H_U1", "H_U2", "H_U3", "H_U5"):
        for k, v in sorted(results[h]["checks"].items()):
            crits.append((h.replace("_", "-"), k, v["value"], v["pass"]))
        crits.append((h.replace("_", "-"), "DECISION", results[h]["decision"],
                      results[h]["decision"] == "PASS"))
    crits.append(("INTEGRITY", "all deterministic gates in all 60 runs",
                  "PASS" if results["integrity_all_pass"] else "FAIL",
                  results["integrity_all_pass"]))
    crits.append(("OVERALL", "single-handoff policy claim",
                  "LICENSED" if results["single_handoff_policy_claim_licensed"]
                  else "NOT LICENSED",
                  results["single_handoff_policy_claim_licensed"]))
    rows = [{"hypothesis": h, "criterion": k,
             "value": (f"{v:.4f}" if isinstance(v, float) else str(v)), "pass": ok}
            for h, k, v, ok in crits]
    fn = ["hypothesis", "criterion", "value", "pass"]
    fig, ax = plt.subplots(figsize=(10, 0.40 * len(crits) + 1.0))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, len(crits))
    ax.axis("off")
    for i, (h, k, v, ok) in enumerate(reversed(crits)):
        colr = F8U.PALETTE["bluish_green"] if ok else F8U.PALETTE["vermillion"]
        ax.add_patch(plt.Rectangle((0.0, i), 1.0, 0.9, color=colr, alpha=0.25))
        ax.text(0.01, i + 0.42, f"{h}: {k}", fontsize=8, va="center")
        ax.text(0.72, i + 0.42, f"{v:.4f}" if isinstance(v, float) else str(v),
                fontsize=8, va="center")
        ax.text(0.95, i + 0.42, "PASS" if ok else "FAIL", fontsize=8, va="center",
                fontweight="bold")
    ax.set_title("Stage-8U decision dashboard — frozen preregistered criteria",
                 fontsize=11)
    ART.emit("FIG18", fig, rows, fn,
             "Decision dashboard against the frozen preregistered pass/fail criteria of "
             "STAGE_08U_PREREGISTRATION.md §5.  The joint licensing rule is H-U1 ∧ "
             "H-U2 ∧ H-U3 ∧ H-U5 ∧ all integrity gates; the honest outcome is shown "
             "unmodified.", ORDER)

    # ---- index + caption package ---------------------------------------------------
    if not check:
        lines = ["# Stage 8U — Figure Index (FIG01..FIG18)", "",
                 "All figures are generated programmatically from the frozen "
                 "`STAGE_08U_RUN_DATASET.csv` and `stage8u_results.json`, and are "
                 "deterministic (fixed SVG hashsalt, no timestamps): tables, captions "
                 "and metadata regenerate byte-identically under "
                 "`generate_8u.py --check` (U-TEST-22).  Each figure ships as SVG, "
                 "300-dpi PNG, source CSV, caption markdown, metadata JSON and a "
                 "SHA-256 checksum file, all under `figures/`.", "",
                 "| figure | title | checksum file |", "|---|---|---|"]
        for row in ART.index_rows:
            lines.append(f"| {row['figure_id']} | {row['title']} "
                         f"| `{row['checksum_file']}` |")
        (DOCS / "POW_POCOL_FIGURE_INDEX.md").write_text("\n".join(lines) + "\n")
        cap = ["# Stage 8U — Caption Package", "",
               "Naming discipline: the algorithm is **PoCol**; the treatment is **the "
               "single-handoff useful-work policy within PoCol**; W00 and W01 are "
               "**matched same-template PoW controls** and are never described as "
               "Bitcoin, the Bitcoin network or real-world PoW.  Every comparison "
               "below is a controlled simulator comparison under matched templates, "
               "targets, difficulty, horizon, rates, powers and seeds; W00 and W01 "
               "answer different matching questions and are never merged.", ""]
        for fid in sorted(ART.captions):
            cap.append(ART.captions[fid])
        (DOCS / "POW_POCOL_CAPTION_PACKAGE.md").write_text("\n".join(cap))
        print(f"wrote {len(ART.index_rows)} figures + index + caption package")
    else:
        if ART.check_failures:
            print("BYTE-IDENTITY FAILURES:", ART.check_failures)
            return 2
        print("check OK: every table, caption and metadata file byte-identical")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(check="--check" in sys.argv[1:]))
