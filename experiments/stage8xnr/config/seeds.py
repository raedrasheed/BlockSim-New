"""Stage 8X-NR — fresh seed registry, disjoint from Stage 8X/8Y/8Z.

30 fresh paired primary seeds and 2 dedicated Pilot seeds, derived
deterministically from a Stage-8X-NR-specific master label so the registry is
reproducible, and verified disjoint from every earlier registry in-tree
(the original Stage 8X seeds are deliberately NOT reused; brief section 10).

Per-purpose streams: every (seed, purpose, index) triple gets an independent
64-bit stream seed via SHA-256, so paired arms consume identical round-process
randomness (common random numbers) while offsets and attributions stay
independent per purpose.
"""

from __future__ import annotations

import hashlib
import json
import os
from typing import Dict, List

_MASTER_LABEL = "BlockSim-PoCol-stage8xnr-2026-nonce-reuse"

N_PRIMARY_SEEDS = 30
N_PILOT_SEEDS = 2


def _derive(label: str) -> int:
    return int.from_bytes(
        hashlib.sha256(label.encode("utf-8")).digest()[:8], "big"
    )


def primary_seeds() -> List[int]:
    return [_derive(f"{_MASTER_LABEL}/primary/{k}") for k in range(N_PRIMARY_SEEDS)]


def pilot_seeds() -> List[int]:
    return [_derive(f"{_MASTER_LABEL}/pilot/{k}") for k in range(N_PILOT_SEEDS)]


def derive_stream_seed(master_seed: int, purpose: str, index: int = 0) -> int:
    """Independent 64-bit stream seed for one (run-seed, purpose, index)."""
    label = f"{_MASTER_LABEL}/stream/{master_seed}/{purpose}/{index}"
    return _derive(label)


# ---------------- disjointness against earlier registries -----------------
_EARLIER_REGISTRIES = [
    "experiments/stage8x/outputs/stage8x_seeds.json",
    "experiments/stage8y/config/stage8y_seeds.json",
]


def _collect_ints(obj) -> List[int]:
    out: List[int] = []
    if isinstance(obj, dict):
        for v in obj.values():
            out.extend(_collect_ints(v))
    elif isinstance(obj, list):
        for v in obj:
            out.extend(_collect_ints(v))
    elif isinstance(obj, int) and not isinstance(obj, bool):
        out.append(obj)
    return out


def verify_disjoint(repo_root: str) -> Dict[str, object]:
    ours = set(primary_seeds()) | set(pilot_seeds())
    earlier: set = set()
    checked = []
    for rel in _EARLIER_REGISTRIES:
        path = os.path.join(repo_root, rel)
        if os.path.exists(path):
            with open(path) as fh:
                earlier |= set(_collect_ints(json.load(fh)))
            checked.append(rel)
    # Stage 8Z halted before writing its registry JSON; read its seed module
    # directly (read-only import) so disjointness covers all three stages.
    try:
        from experiments.stage8z.config import seeds as z
        earlier |= set(z.pilot_seeds()) | set(z.exploratory_seeds()) \
            | set(z.confirmatory_seeds()) | set(z.longhorizon_seeds())
        checked.append("experiments/stage8z/config/seeds.py (module)")
    except Exception:
        pass
    overlap = ours & earlier
    return {
        "checked_registries": checked,
        "n_new_seeds": len(ours),
        "n_earlier_values": len(earlier),
        "overlap": sorted(overlap),
        "disjoint": not overlap,
    }


def registry_dict(repo_root: str) -> Dict[str, object]:
    return {
        "experiment": "stage8xnr",
        "master_label": _MASTER_LABEL,
        "primary_seeds": primary_seeds(),
        "pilot_seeds": pilot_seeds(),
        "disjointness": verify_disjoint(repo_root),
    }


def registry_sha256(repo_root: str) -> str:
    return hashlib.sha256(
        json.dumps(registry_dict(repo_root), sort_keys=True).encode()
    ).hexdigest()
