"""Stage-8U deterministic figure/table core (frozen at COMMIT 1, used by COMMIT 3).

Everything the U-TEST-22 byte-identity gate covers lives here: the canonical table
serialisation (byte-identical across regenerations), the deterministic figure metadata
(no timestamps, no environment state) and the frozen FIG01..FIG18 specification list.
The matplotlib rendering layer (COMMIT 3) consumes these primitives; it may not add
non-deterministic content to any table or metadata record.

Colour discipline: the Okabe-Ito colour-blind-safe palette; no 3D; no truncated bars.
"""
from __future__ import annotations

import hashlib
from typing import Any, Dict, List, Sequence

# Okabe-Ito colour-blind-safe palette (hex, fixed order).
PALETTE = {
    "orange": "#E69F00", "sky_blue": "#56B4E9", "bluish_green": "#009E73",
    "yellow": "#F0E442", "blue": "#0072B2", "vermillion": "#D55E00",
    "reddish_purple": "#CC79A7", "black": "#000000",
}

#: Fixed scenario colour assignment used by every Stage-8U figure.
SCENARIO_COLORS = {
    "W00_POW_POPULATION_MATCHED": PALETTE["vermillion"],
    "W01_POW_ACTIVE_CAPACITY_MATCHED": PALETTE["orange"],
    "P00_POCOL_NO_FLOOR": PALETTE["sky_blue"],
    "P01_POCOL_STAGE8S_COARSE": PALETTE["blue"],
    "P02_POCOL_SINGLE_HANDOFF": PALETTE["bluish_green"],
}

#: The frozen Stage-8U figure plan (id, title, chart kind, scenario scope).
FIGURE_SPECS: List[Dict[str, Any]] = [
    {"figure_id": "FIG01", "title": "Total energy per run, all five scenarios",
     "kind": "grouped_points_mean_ci", "scenarios": "ALL"},
    {"figure_id": "FIG02", "title": "Relative energy difference of P02 versus W00 and "
     "versus W01 (separate panels)", "kind": "paired_panels", "scenarios":
     ["W00_POW_POPULATION_MATCHED", "W01_POW_ACTIVE_CAPACITY_MATCHED",
      "P02_POCOL_SINGLE_HANDOFF"]},
    {"figure_id": "FIG03", "title": "Accepted blocks per run", "kind":
     "grouped_points_mean_ci", "scenarios": "ALL"},
    {"figure_id": "FIG04", "title": "Median and p95 closed-round duration (separate "
     "panels)", "kind": "paired_panels", "scenarios": "ALL"},
    {"figure_id": "FIG05", "title": "Energy per accepted block (NA when a run has zero "
     "blocks)", "kind": "grouped_points_mean_ci", "scenarios": "ALL"},
    {"figure_id": "FIG06", "title": "Total, unique and duplicate physical evaluations",
     "kind": "grouped_bars", "scenarios": "ALL"},
    {"figure_id": "FIG07", "title": "Accepted blocks per million physical evaluations",
     "kind": "grouped_points_mean_ci", "scenarios": "ALL"},
    {"figure_id": "FIG08", "title": "Stacked per-state residency decomposition",
     "kind": "stacked_bars", "scenarios": "ALL"},
    {"figure_id": "FIG09", "title": "Stacked energy decomposition (primary hashing, "
     "range idle, reserve standby, wake transient, activated-reserve hashing, "
     "offline/other)", "kind": "stacked_bars", "scenarios": "ALL"},
    {"figure_id": "FIG10", "title": "Static and useful floor durations and deficit "
     "areas", "kind": "grouped_bars", "scenarios":
     ["P00_POCOL_NO_FLOOR", "P01_POCOL_STAGE8S_COARSE", "P02_POCOL_SINGLE_HANDOFF"]},
    {"figure_id": "FIG11", "title": "Activation requests, incomplete activations, "
     "handoffs and reassignments per closed round", "kind": "grouped_bars",
     "scenarios":
     ["P00_POCOL_NO_FLOOR", "P01_POCOL_STAGE8S_COARSE", "P02_POCOL_SINGLE_HANDOFF"]},
    {"figure_id": "FIG12", "title": "Energy-service Pareto plane (per-seed points and "
     "scenario centroids)", "kind": "scatter_centroids", "scenarios": "ALL"},
    {"figure_id": "FIG13", "title": "Paired per-seed energy slopes W01->P02 and "
     "W00->P02", "kind": "paired_slopes", "scenarios":
     ["W00_POW_POPULATION_MATCHED", "W01_POW_ACTIVE_CAPACITY_MATCHED",
      "P02_POCOL_SINGLE_HANDOFF"]},
    {"figure_id": "FIG14", "title": "Paired per-seed service slopes (accepted blocks)",
     "kind": "paired_slopes", "scenarios":
     ["W00_POW_POPULATION_MATCHED", "W01_POW_ACTIVE_CAPACITY_MATCHED",
      "P02_POCOL_SINGLE_HANDOFF"]},
    {"figure_id": "FIG15", "title": "Representative P02 timeline (H_effective, "
     "H_pipeline, static floor, useful target, live wakes, the handoff event, accepted "
     "blocks)", "kind": "timeline", "scenarios": ["P02_POCOL_SINGLE_HANDOFF"]},
    {"figure_id": "FIG16", "title": "Normalised summary heatmap across scenarios and "
     "metrics", "kind": "heatmap", "scenarios": "ALL"},
    {"figure_id": "FIG17", "title": "Policy evolution 8M -> 8R -> 8S -> P02 "
     "(descriptive only; no cross-stage inferential statistic)", "kind":
     "descriptive_lines", "scenarios": ["P02_POCOL_SINGLE_HANDOFF"]},
    {"figure_id": "FIG18", "title": "Decision dashboard against the frozen pass/fail "
     "criteria", "kind": "dashboard", "scenarios": "ALL"},
]

assert len(FIGURE_SPECS) == 18
assert [s["figure_id"] for s in FIGURE_SPECS] == [f"FIG{i:02d}" for i in range(1, 19)]


def canonical_cell(v: Any) -> str:
    """Canonical, locale-independent cell rendering (repr for floats: round-trippable)."""
    if isinstance(v, float):
        return repr(v)
    if v is None:
        return "NA"
    return str(v)


def serialize_table(rows: Sequence[Dict[str, Any]], fieldnames: Sequence[str]) -> str:
    """Byte-deterministic CSV text: fixed field order, '\n' newlines, canonical cells.

    Commas/quotes inside cells are forbidden by construction (numeric/identifier data
    only) and asserted, so no quoting rules can introduce ambiguity."""
    out = [",".join(fieldnames)]
    for row in rows:
        cells = []
        for f in fieldnames:
            c = canonical_cell(row.get(f))
            assert "," not in c and '"' not in c and "\n" not in c, \
                f"non-canonical cell for field {f!r}: {c!r}"
            cells.append(c)
        out.append(",".join(cells))
    return "\n".join(out) + "\n"


def figure_metadata(figure_id: str, source_csv_name: str,
                    scenario_ids: Sequence[str]) -> Dict[str, Any]:
    """Deterministic metadata for one figure: identity, spec fields and sources only —
    never a timestamp, hostname, library version or any other environment state."""
    spec = next(s for s in FIGURE_SPECS if s["figure_id"] == figure_id)
    scope = spec["scenarios"]
    return {
        "figure_id": figure_id,
        "title": spec["title"],
        "kind": spec["kind"],
        "scenario_scope": scope if isinstance(scope, str) else list(scope),
        "scenario_ids": sorted(scenario_ids),
        "source_csv": source_csv_name,
        "palette": "okabe-ito",
        "style_rules": ["colour_blind_safe", "no_3d", "no_truncated_bars",
                        "paired_seed_points_visible", "mean_with_95ci"],
    }


def checksum_text(text: str) -> str:
    """SHA-256 of the exact byte serialisation (UTF-8)."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
