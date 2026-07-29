"""Stage 5B1A exact circular-coverage for B2 (seeded random starts, single
forward traversal on a ring of size S).

Each miner i searches an arc of `length_i` distinct candidates starting at
`start_i`, stepping forward modulo S. Its searched set is
    { (start_i + k) mod S : 0 <= k < length_i }.
Represented exactly as integer half-open intervals on [0, S):
  * length == 0            -> [] (no candidates)
  * length >= S            -> [(0, S)] (whole ring covered once)
  * start + length <= S    -> [(start, start + length)]           (no wrap)
  * otherwise              -> [(start, S), (0, start + length - S)] (wrap)

`interval_union_length` returns the exact integer count of distinct covered
candidates via a sort-and-merge (O(n log n)); it NEVER enumerates the domain, so
it is safe at full simulator scale (S ~ 1e17).

Reconciliation is exact by construction:
    total    = sum(length_i)
    distinct = |union of arcs|
    duplicate = total - distinct
"""

from __future__ import annotations
import math
from typing import List, Tuple, Dict


def circular_intervals(start: int, length: int, S: int) -> List[Tuple[int, int]]:
    """Exact integer half-open intervals covered by one miner's forward arc."""
    if S <= 0:
        return []
    length = int(length)
    start = int(start) % S
    if length <= 0:
        return []
    if length >= S:
        return [(0, S)]                                   # full ring, counted once
    end = start + length
    if end <= S:
        return [(start, end)]
    return [(start, S), (0, end - S)]                     # wraparound split


def interval_union_length(intervals: List[Tuple[int, int]]) -> int:
    """Exact count of distinct integer positions covered by half-open intervals.
    O(n log n) merge; no domain enumeration."""
    if not intervals:
        return 0
    ivs = sorted(intervals)
    total = 0
    cur_s, cur_e = ivs[0]
    for s, e in ivs[1:]:
        if s <= cur_e:                                    # overlap or touch
            if e > cur_e:
                cur_e = e
        else:
            total += cur_e - cur_s
            cur_s, cur_e = s, e
    total += cur_e - cur_s
    return total


def b2_coverage_exact(starts: List[int], lengths: List[int], S: int) -> Dict[str, int]:
    """Exact (total, distinct, duplicate) integer candidate counts for B2."""
    all_iv = []
    total = 0
    for st, ln in zip(starts, lengths):
        ln = min(int(ln), S)                              # single-traversal cap
        total += ln
        all_iv.extend(circular_intervals(st, ln, S))
    distinct = interval_union_length(all_iv)
    return dict(total_candidate_evaluations=total,
                distinct_candidate_evaluations=distinct,
                duplicate_candidate_evaluations=total - distinct)


def b2_winner(pos, starts: List[int], rates, S: int):
    """Earliest solution discovery under the UNIFIED time convention: a solution at
    circular offset d = (q - start_i) mod S is discovered at (d + 1) / rate_i.
    winner_time = min over (miner i, solution q). Returns (winner_time, winner_id);
    ties broken by lowest miner index."""
    best_t = math.inf
    best_id = None
    for i, (st, r) in enumerate(zip(starts, rates)):
        if r <= 0:
            continue
        for q in pos:
            d = (int(q) - int(st)) % S
            tt = (d + 1) / r
            if tt < best_t:
                best_t = tt
                best_id = i
    return best_t, best_id


def lengths_from_winner_time(winner_time: float, rates, S: int) -> List[int]:
    """Candidates completed by each miner by winner_time under the unified
    convention: completed = floor(rate * winner_time), capped at one traversal S."""
    out = []
    for r in rates:
        if r <= 0 or not math.isfinite(winner_time):
            out.append(0)
            continue
        out.append(min(S, int(math.floor(r * winner_time))))
    return out


def exhaustive_coverage_reference(starts: List[int], lengths: List[int], S: int) -> Dict[str, int]:
    """Brute-force set-based reference (SMALL S only) — enumerates every covered
    position. Used purely to validate `b2_coverage_exact`."""
    covered = set()
    total = 0
    for st, ln in zip(starts, lengths):
        ln = min(int(ln), S)
        total += ln
        for k in range(ln):
            covered.add((int(st) + k) % S)
    return dict(total_candidate_evaluations=total,
                distinct_candidate_evaluations=len(covered),
                duplicate_candidate_evaluations=total - len(covered))


def coverage_at_time(starts, rates, S, t) -> Dict[str, int]:
    """Exact integer coverage of the circular domain by all miners' swept arcs at
    time t. Each miner i covers min(S, floor(rate_i * t)) candidates from start_i.
    Uses the unified convention (candidate d completes at (d+1)/rate) implicitly via
    floor(rate*t). Returns exact total/distinct/duplicate integers."""
    lengths = [min(int(S), int(math.floor(r * t))) for r in rates]
    return b2_coverage_exact(starts, lengths, S)


def b2_exhaustion_time(starts, rates, S):
    """Earliest time t_ex at which the union of all swept circular arcs covers the
    WHOLE domain S (union_length == S). Monotone binary search over time using the
    exact circular interval-union; overlap never counts as new coverage; each miner
    is capped at one full traversal. Returns (t_ex, counts_at_exhaustion). Miners
    with rate <= 0 (inactive) contribute no path (pass their rate as 0)."""
    active = [r for r in rates if r > 0]
    if not active:
        return math.inf, dict(total_candidate_evaluations=0,
                              distinct_candidate_evaluations=0,
                              duplicate_candidate_evaluations=0)
    hi = float(S) / min(active)                    # slowest miner covers S alone by here
    lo = 0.0
    # ensure hi actually exhausts (guard float)
    while coverage_at_time(starts, rates, S, hi)["distinct_candidate_evaluations"] < S:
        hi *= 2.0
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if coverage_at_time(starts, rates, S, mid)["distinct_candidate_evaluations"] >= S:
            hi = mid
        else:
            lo = mid
    counts = coverage_at_time(starts, rates, S, hi)
    if counts["distinct_candidate_evaluations"] < S:   # final nudge for float boundary
        hi = math.nextafter(hi, math.inf)
        counts = coverage_at_time(starts, rates, S, hi)
    return hi, counts


def exhaustion_time_reference_small(starts, rates, S):
    """Brute-force reference (SMALL S): first-cover time of every position is
    min_i ((q - start_i) mod S + 1)/rate_i; the domain is exhausted at the max over
    positions. O(S*n) -- small domains only."""
    worst = 0.0
    for q in range(S):
        first = math.inf
        for st, r in zip(starts, rates):
            if r <= 0:
                continue
            d = (q - int(st)) % S
            first = min(first, (d + 1) / r)
        worst = max(worst, first)
    return worst


def exhaustive_winner_reference(pos, starts: List[int], rates, S: int):
    """Brute-force winner (SMALL S) — identical rule to `b2_winner`, kept separate
    so tests compare two independent implementations."""
    best = math.inf
    best_id = None
    for q in pos:
        for i, (st, r) in enumerate(zip(starts, rates)):
            if r <= 0:
                continue
            steps = (int(q) - int(st)) % S
            t = (steps + 1) / r                     # unified convention: (d+1)/rate
            if t < best:
                best = t
                best_id = i
    return best, best_id
