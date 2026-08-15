"""Stage 8X-NR — exact cyclic interval arithmetic on the 32-bit nonce domain.

The nonce-value domain is the cyclic group Z_S with S = 2**32. A miner's
evaluated nonce values over any scope form either the full domain (>= one
complete sweep) or a cyclic arc [start, start+len) mod S. This module computes
unions, intersections and multiplicity profiles of such arcs *exactly*, with
integer arithmetic, never materialising 2**32 booleans (brief sections 12/19).

An arc is represented as (start, length) with 0 <= start < S, 0 <= length <= S.
Internally an arc is split into at most two linear half-open intervals.
"""

from __future__ import annotations

import math
from typing import Dict, Iterable, List, Sequence, Tuple

from experiments.stage8xnr.config.nr_config import S_NONCE

Arc = Tuple[int, int]              # (start, length) on the cycle
Linear = Tuple[int, int]           # half-open [a, b) with 0 <= a < b <= S


def arc_to_linear(arc: Arc, domain: int = S_NONCE) -> List[Linear]:
    """Split a cyclic arc into 1 or 2 linear half-open intervals."""
    start, length = arc
    if length <= 0:
        return []
    if length >= domain:
        return [(0, domain)]
    start %= domain
    end = start + length
    if end <= domain:
        return [(start, end)]
    return [(start, domain), (0, end - domain)]


def union_measure(arcs: Sequence[Arc], domain: int = S_NONCE) -> int:
    """|union of arcs| — exact, O(k log k)."""
    segs: List[Linear] = []
    for a in arcs:
        segs.extend(arc_to_linear(a, domain))
    if not segs:
        return 0
    segs.sort()
    total = 0
    cs, ce = segs[0]
    for s, e in segs[1:]:
        if s > ce:
            total += ce - cs
            cs, ce = s, e
        else:
            ce = max(ce, e)
    total += ce - cs
    return total


def arc_intersection_measure(a: Arc, b: Arc, domain: int = S_NONCE) -> int:
    """|V_a ∩ V_b| for two cyclic arcs — exact."""
    out = 0
    for s1, e1 in arc_to_linear(a, domain):
        for s2, e2 in arc_to_linear(b, domain):
            out += max(0, min(e1, e2) - max(s1, s2))
    return out


def multiplicity_profile(arcs: Sequence[Arc], domain: int = S_NONCE) -> Dict[int, int]:
    """measure of {x : exactly m arcs cover x} for m >= 1 — sweep line, exact.

    Input arcs are one per miner (each miner contributes coverage 0 or 1 per
    value: full-sweep arcs are clamped to length S first by the caller if the
    question is *miner multiplicity* rather than evaluation counts).
    """
    events: List[Tuple[int, int]] = []
    for a in arcs:
        for s, e in arc_to_linear(a, domain):
            events.append((s, +1))
            events.append((e, -1))
    if not events:
        return {}
    events.sort()
    profile: Dict[int, int] = {}
    depth = 0
    prev = 0
    for pos, delta in events:
        if pos > prev and depth > 0:
            profile[depth] = profile.get(depth, 0) + (pos - prev)
        depth += delta
        prev = pos
    return profile


def measure_covered_at_least(profile: Dict[int, int], m: int) -> int:
    return sum(v for k, v in profile.items() if k >= m)


def max_multiplicity(profile: Dict[int, int]) -> int:
    return max(profile.keys(), default=0)


# ---------------- pairwise overlap of equal-length offset arcs ------------
def pairwise_overlap_summary(
    starts: Sequence[int], length: int, domain: int = S_NONCE
) -> Dict[str, float]:
    """Mean / median / max of O_ij over all unordered pairs of arcs
    [s_i, s_i+length) on the cycle — exact, O(N log N + overlapping pairs).

    For two arcs of equal length L at circular offset d = (s_j - s_i) mod S the
    intersection is max(0, L-d) + max(0, d - (S-L)); with L <= S/2 at most one
    term is non-zero, and each unordered overlapping pair is seen exactly once
    as a forward neighbour within distance < L.
    """
    n = len(starts)
    n_pairs = n * (n - 1) // 2
    if n < 2:
        return {"mean": 0.0, "median": 0.0, "p95": 0.0, "max": 0,
                "overlapping_pairs": 0, "n_pairs": 0}
    if length >= domain:
        return {"mean": float(domain), "median": float(domain),
                "p95": float(domain), "max": domain,
                "overlapping_pairs": n_pairs, "n_pairs": n_pairs}
    if 2 * length > domain:
        raise ValueError("summary shortcut requires length <= S/2")
    xs = sorted(s % domain for s in starts)
    overlaps: List[int] = []
    for i, s in enumerate(xs):
        j = i + 1
        while True:
            if j >= len(xs):
                d = xs[j - len(xs)] + domain - s
            else:
                d = xs[j] - s
            if d >= length or d >= domain or j - i >= len(xs):
                break
            overlaps.append(length - d)
            j += 1
    overlaps.sort()
    k = len(overlaps)
    total = sum(overlaps)
    # order statistics over ALL n_pairs values (n_pairs - k zeros, then
    # sorted overlaps): value at 0-based index i
    def order_stat(i: int) -> float:
        if i < n_pairs - k:
            return 0.0
        return float(overlaps[i - (n_pairs - k)])

    median = order_stat(n_pairs // 2)                       # upper median
    p95 = order_stat(max(0, math.ceil(0.95 * n_pairs) - 1))
    return {
        "mean": total / n_pairs,
        "median": median,
        "p95": p95,
        "max": max(overlaps) if overlaps else 0,
        "overlapping_pairs": k,
        "n_pairs": n_pairs,
    }


# ---------------- PoCol partition checks ----------------------------------
def verify_partition(ranges: Sequence[Linear], domain: int = S_NONCE) -> Dict[str, object]:
    """Machine-checkable: full coverage, zero overlap, size spread <= 1."""
    xs = sorted(ranges)
    overlap = 0
    for (s1, e1), (s2, e2) in zip(xs, xs[1:]):
        if s2 < e1:
            overlap += e1 - s2
    covered = union_measure([(s, e - s) for s, e in xs], domain)
    sizes = [e - s for s, e in xs]
    return {
        "covered": covered,
        "full_coverage": covered == domain,
        "overlap": overlap,
        "size_min": min(sizes),
        "size_max": max(sizes),
        "size_spread_le_1": max(sizes) - min(sizes) <= 1,
    }


# ---------------- occupancy model (brief section 18) ----------------------
def expected_unique_random(m: int, domain: int) -> float:
    """E[U] = S(1-(1-1/S)^m) — uniform sampling WITH replacement only.

    Valid only where the traversal model is random sampling; sequential arcs use
    the exact interval geometry above instead.
    """
    if m < 0:
        raise ValueError("m must be >= 0")
    return domain * (1.0 - (1.0 - 1.0 / domain) ** m)
