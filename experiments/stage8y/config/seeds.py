"""Stage 8Y — dedicated seed registry.

Stage 8Y has its own namespace, disjoint from Stage 8X and from
``experiments/_common.py``. Four seed groups are generated from four distinct
sub-labels so that Pilot, primary, secondary and long-horizon seeds can never
overlap each other, and a test asserts disjointness from the Stage 8X registry.

Matched comparisons share the master seed: at a given (N, composition, seed index)
the PoW run and every PoCol policy run receive the same master seed and the same
purpose-split, per-miner sub-streams.
"""

from __future__ import annotations

import hashlib
import json
import os
from typing import Dict, List

#: Changing this string changes every Stage 8Y seed and constitutes a new revision.
NAMESPACE = "BlockSim-New/Stage8Y/HeterogeneousEnergyAwarePoCol/rev1"

N_PILOT_SEEDS = 6
N_PRIMARY_SEEDS = 30
N_SECONDARY_SEEDS = 30
N_LONGHORIZON_SEEDS = 30

_MASK63 = (1 << 63) - 1


def _derive(label: str, index: int) -> int:
    payload = f"{NAMESPACE}|{label}|{index:04d}".encode("utf-8")
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], "big") & _MASK63


def pilot_seeds(count: int = N_PILOT_SEEDS) -> List[int]:
    return [_derive("pilot-master", k) for k in range(1, count + 1)]


def primary_seeds(count: int = N_PRIMARY_SEEDS) -> List[int]:
    return [_derive("primary-master", k) for k in range(1, count + 1)]


def secondary_seeds(count: int = N_SECONDARY_SEEDS) -> List[int]:
    return [_derive("secondary-master", k) for k in range(1, count + 1)]


def longhorizon_seeds(count: int = N_LONGHORIZON_SEEDS) -> List[int]:
    return [_derive("longhorizon-master", k) for k in range(1, count + 1)]


def registry() -> Dict:
    groups = {
        "pilot": ("pilot-master", pilot_seeds()),
        "primary": ("primary-master", primary_seeds()),
        "secondary": ("secondary-master", secondary_seeds()),
        "longhorizon": ("longhorizon-master", longhorizon_seeds()),
    }
    body = {
        "namespace": NAMESPACE,
        "experiment": "Stage 8Y",
        "derivation": "seed_k = int(sha256('<namespace>|<label>|<k:04d>')[:8]) & (2**63-1)",
        "groups": {name: {"label": lab, "count": len(s), "seeds": s}
                   for name, (lab, s) in groups.items()},
        "disjointness": "pilot / primary / secondary / longhorizon are pairwise "
                        "disjoint and disjoint from the Stage 8X registry (asserted "
                        "in tests/test_stage8y.py).",
    }
    body["sha256"] = hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return body


def write_registry(path: str) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(registry(), fh, indent=2, sort_keys=True)
        fh.write("\n")
    return path


def derive_stream_seed(master_seed: int, purpose: str, index: int = 0) -> int:
    """Split a master seed into a reproducible per-purpose, per-miner sub-stream."""
    payload = f"{master_seed}|{purpose}|{index}".encode("utf-8")
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], "big") & _MASK63
