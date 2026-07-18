"""Deterministic nonce-domain partitioning.

Interval convention: the nonce domain is the HALF-OPEN integer interval
[domain_start, domain_end); size M = domain_end - domain_start. Every returned
sub-range (start, end) also denotes the half-open interval [start, end).

Guarantees (verified in tests/test_nonce_partition.py):
- ranges are mutually disjoint;
- their union is exactly [domain_start, domain_end);
- no nonce is assigned twice and none is omitted;
- range sizes differ by at most one (remainders distributed deterministically to
  the lowest-indexed miners);
- supports M < N (surplus miners get empty ranges), N = 1, and very large M
  (pure integer arithmetic, no enumeration).
"""
from __future__ import annotations


def partition_nonce_domain(domain_start, domain_end, miner_count):
    """Split [domain_start, domain_end) into `miner_count` half-open sub-ranges.

    Returns a list of (start, end) tuples, one per miner, in miner-index order.
    An empty range is represented as (x, x) (size 0). Runs in O(miner_count);
    domain_end may be arbitrarily large (e.g. 2**32 or 2**256).
    """
    if miner_count <= 0:
        raise ValueError(f"miner_count must be positive, got {miner_count}")
    M = domain_end - domain_start
    if M < 0:
        raise ValueError(f"empty/negative domain: [{domain_start}, {domain_end})")

    base = M // miner_count          # floor share
    rem = M % miner_count            # first `rem` miners get one extra nonce
    ranges = []
    cur = domain_start
    for i in range(miner_count):
        size = base + (1 if i < rem else 0)
        ranges.append((cur, cur + size))
        cur += size
    # postcondition: exact coverage
    assert cur == domain_end, (cur, domain_end)
    return ranges


def range_size(r):
    """Size of a half-open range (start, end)."""
    start, end = r
    return end - start


def ranges_are_disjoint(ranges):
    """True iff no two half-open ranges overlap (ignoring empty ranges)."""
    ordered = sorted((s, e) for (s, e) in ranges if e > s)
    for (s1, e1), (s2, e2) in zip(ordered, ordered[1:]):
        if s2 < e1:
            return False
    return True


def ranges_cover(ranges, domain_start, domain_end):
    """True iff the union of ranges is exactly [domain_start, domain_end)."""
    if not ranges_are_disjoint(ranges):
        return False
    if sum(range_size(r) for r in ranges) != (domain_end - domain_start):
        return False
    ordered = sorted((s, e) for (s, e) in ranges if e > s)
    if not ordered:
        return domain_end == domain_start
    if ordered[0][0] != domain_start or ordered[-1][1] != domain_end:
        return False
    for (s1, e1), (s2, e2) in zip(ordered, ordered[1:]):
        if e1 != s2:                 # gap between consecutive ranges
            return False
    return True


def owner_of(ranges, nonce):
    """Index of the miner whose half-open range contains `nonce`, else None."""
    for i, (s, e) in enumerate(ranges):
        if s <= nonce < e:
            return i
    return None
