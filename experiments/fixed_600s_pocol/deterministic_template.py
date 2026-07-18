"""Deterministic valid-nonce placement for the primary controlled experiment.

The primary deterministic experiment guarantees exactly one valid nonce per
template (=> exactly one accepted block per round). Placements: first / p25 /
middle / p75 / last, or an explicit nonce set (used to demonstrate that a
numerically LATER nonce can be discovered EARLIER via its local position).

Difficulty is not used to delay anything: placement decides WHEN discovery
happens; the fixed-round scheduler alone decides when the block commits.
"""
from __future__ import annotations

from .configuration import resolve_placement


def valid_nonces(cfg, M):
    """The template's valid-nonce set (sorted, 0-based, within [0, M))."""
    if cfg.explicit_nonces is not None:
        ns = sorted(int(v) for v in cfg.explicit_nonces if 0 <= int(v) < M)
        if not ns:
            raise ValueError("explicit_nonces contains no nonce inside [0, M)")
        return ns
    return [resolve_placement(cfg.placement, M)]
