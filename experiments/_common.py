"""Shared helpers for the revision experiment scripts: paths, CSV/summary
export, deterministic seeds, and consistent matplotlib styling."""

from __future__ import annotations

import csv
import os
import sys

# Make the repository root importable when scripts are run directly.
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

DATA_DIR = os.path.join(ROOT, "results", "data")
FIG_DIR = os.path.join(ROOT, "results", "figures")
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(FIG_DIR, exist_ok=True)

N_SEEDS = 30                    # >= 30 seeds per scenario (reviewer requirement)
SEED_BASE = 20260101           # reproducible seed-generation base


def write_csv(name: str, rows, fieldnames):
    """Write a list of dict rows to results/data/<name>.csv."""
    path = os.path.join(DATA_DIR, name)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fieldnames})
    return path


def setup_matplotlib():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({
        "figure.dpi": 130,
        "savefig.dpi": 200,
        "font.size": 11,
        "axes.grid": True,
        "grid.alpha": 0.3,
        "axes.axisbelow": True,
        "figure.autolayout": True,
    })
    return plt


def save_fig(fig, stem: str):
    """Save a figure as both PNG and PDF in results/figures/."""
    png = os.path.join(FIG_DIR, stem + ".png")
    pdf = os.path.join(FIG_DIR, stem + ".pdf")
    fig.savefig(png, bbox_inches="tight")
    fig.savefig(pdf, bbox_inches="tight")
    return png, pdf
