"""Stage 8X — dedicated seed registry.

Stage 8X has its **own** seed namespace. It does not reuse any earlier seed base
(in particular it does not use ``experiments/_common.py::SEED_BASE = 20260101``,
which drives the analytic revision experiments).

Seeds are derived deterministically from a declared namespace string so that the
registry is reproducible from source alone, then frozen to ``stage8x_seeds.json``
and checksummed in the freeze manifest.

Primary and Pilot seeds come from *different* sub-namespaces, so a Pilot seed can
never silently appear in the primary inferential dataset.
"""

from __future__ import annotations

import hashlib
import json
import os
from typing import Dict, List

#: Declared Stage 8X seed namespace. Changing this string changes every seed and
#: therefore constitutes a new experiment revision.
NAMESPACE = "BlockSim-New/Stage8X/PoCol-vs-PoW/AntminerS21Pro/rev1"

N_PRIMARY_SEEDS = 30
N_PILOT_SEEDS = 5

_MASK64 = (1 << 63) - 1


def _derive(label: str, index: int) -> int:
    payload = f"{NAMESPACE}|{label}|{index:04d}".encode("utf-8")
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], "big") & _MASK64


def primary_seeds(count: int = N_PRIMARY_SEEDS) -> List[int]:
    """The 30 fresh paired master seeds used by the frozen primary matrix."""
    return [_derive("primary-master", k) for k in range(1, count + 1)]


def pilot_seeds(count: int = N_PILOT_SEEDS) -> List[int]:
    """Dedicated Pilot seeds. Never merged into the primary dataset."""
    return [_derive("pilot-master", k) for k in range(1, count + 1)]


def registry() -> Dict:
    ps = primary_seeds()
    pl = pilot_seeds()
    body = {
        "namespace": NAMESPACE,
        "experiment": "Stage 8X",
        "derivation": "seed_k = int(sha256('<namespace>|<label>|<k:04d>')[:8]) & (2**63-1)",
        "primary": {"label": "primary-master", "count": len(ps), "seeds": ps},
        "pilot": {"label": "pilot-master", "count": len(pl), "seeds": pl},
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


def file_sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def derive_stream_seed(master_seed: int, purpose: str, index: int = 0) -> int:
    """Split a master seed into an independent, reproducible sub-stream seed.

    Purpose-split streams are what make PoW and PoCol *paired*: miner ``i`` draws
    its k-th search outcome from the same stream under both protocols at the same
    (N, master_seed).
    """
    payload = f"{master_seed}|{purpose}|{index}".encode("utf-8")
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], "big") & _MASK64
