"""Nonce-domain partitioning for the fixed-600s experiment.

Delegates to the already-tested implementation in
experiments/nonce_partition/partition.py (half-open [start, end) intervals,
disjoint, exhaustive, sizes differ by <= 1, deterministic remainders, M < N
supported, O(N) big-int arithmetic) and adds the assignment view used by the
round engine: miners with empty ranges stay IDLE for the whole search phase.
"""
from __future__ import annotations

from experiments.nonce_partition.partition import (   # re-export (tested)
    partition_nonce_domain, range_size, ranges_are_disjoint, ranges_cover, owner_of,
)

__all__ = [
    "partition_nonce_domain", "range_size", "ranges_are_disjoint", "ranges_cover",
    "owner_of", "assignments_for",
]


def assignments_for(protocol, M, N):
    """Per-miner candidate assignments for one template.

    Returns (ranges, sizes) where ranges[i] is miner i's half-open interval:
    - pocol_disjoint_nonce:       disjoint partition of [0, M)
    - common_template_duplicate:  the complete domain [0, M) for every miner
    - independent_header_pow:     a per-miner BUDGET of partition size (equal
                                  total budget M; represented as [0, size_i)
                                  positions in the miner's own stream)
    """
    from .configuration import PROTO_DUP, PROTO_IND, PROTO_POCOL
    if protocol == PROTO_POCOL:
        ranges = partition_nonce_domain(0, M, N)
    elif protocol == PROTO_DUP:
        ranges = [(0, M) for _ in range(N)]
    elif protocol == PROTO_IND:
        ranges = [(0, range_size(r)) for r in partition_nonce_domain(0, M, N)]
    else:
        raise ValueError(f"unknown protocol {protocol!r}")
    return ranges, [range_size(r) for r in ranges]
