"""Corrected stochastic shared-template model.

The earlier nonce-partition stochastic model took the smallest GLOBAL successful
nonce and mapped it to a range. That is wrong for parallel disjoint search: with
all ranges searched concurrently, the earliest solution in WALL-CLOCK time is the
one with the smallest LOCAL discovery step, which may sit in a numerically later
range.

For each disjoint subrange we draw a first local success G_i ~ Geometric(p) from a
deterministic range-specific seed derived from the shared template seed (so Mode A
and Mode B see the SAME shared-template success set, paired). No nonce is
enumerated.
"""
from __future__ import annotations

import math
import hashlib

from experiments.nonce_partition.partition import partition_nonce_domain, range_size


def _derive_seed(template_seed, i):
    """Deterministic, stable per-range seed (independent of Python hash salting)."""
    h = hashlib.sha256(f"{int(template_seed)}:{int(i)}".encode()).digest()
    return int.from_bytes(h[:8], "big")


def _geometric_first_success_from_u(u, p):
    """1-based first Bernoulli(p) success from a uniform u in (0,1]; may be huge."""
    if p <= 0.0:
        return math.inf
    if p >= 1.0:
        return 1
    if u <= 0.0:
        u = 5e-324
    return int(math.floor(math.log(u) / math.log1p(-p))) + 1


def range_first_successes(M, N, p, template_seed):
    """Return (ranges, G) where G[i] is range i's 1-based first local success, or
    None if the range contains no success (G_i > range_size_i)."""
    import random
    ranges = partition_nonce_domain(0, M, N)
    G = []
    for i, rg in enumerate(ranges):
        size = range_size(rg)
        rng = random.Random(_derive_seed(template_seed, i))
        g = _geometric_first_success_from_u(rng.random(), p)
        G.append(g if (size > 0 and g <= size) else None)
    return ranges, G


def pocol_disjoint_outcome(M, N, p, template_seed):
    """Mode B outcome fields. t_star = min LOCAL discovery step over valid ranges;
    the winner may be a numerically later range."""
    ranges, G = range_first_successes(M, N, p, template_seed)
    valid = [(g, i) for i, g in enumerate(G) if g is not None]
    sizes = [range_size(rg) for rg in ranges]
    if valid:
        t_star, winner = min(valid)                 # smallest local step wins
        winning_nonce = ranges[winner][0] + t_star - 1
        solution_found = True
    else:                                           # exhausted round: no success
        winner, winning_nonce, solution_found = None, None, False
        t_star = max(sizes) if sizes else 0
    evaluated = [min(sz, t_star) for sz in sizes]
    exhausted = [ev == sz for ev, sz in zip(evaluated, sizes)]
    return {
        "ranges": ranges, "evaluated": evaluated, "t_star": t_star,
        "winner_id": winner, "winning_nonce": winning_nonce,
        "solution_found": solution_found,
        "unique_evals": sum(evaluated), "duplicate_evals": 0,
        "exhausted": exhausted,
    }


def duplicate_baseline_outcome(M, N, p, template_seed):
    """Mode A outcome fields, using the SAME per-range success set. All miners scan
    the whole domain in numeric order, so the winner is the smallest GLOBAL
    successful nonce (this generally differs from the Mode B winner)."""
    ranges, G = range_first_successes(M, N, p, template_seed)
    globals_ = [ranges[i][0] + g - 1 for i, g in enumerate(G) if g is not None]
    if globals_:
        g_global = min(globals_)                    # smallest global nonce
        t_star = g_global + 1                       # scan steps to reach it
        winner, winning_nonce, solution_found = 0, g_global, True
    else:
        t_star, winner, winning_nonce, solution_found = M, None, None, False
    evaluated = [t_star] * N                         # every miner scans t_star
    return {
        "ranges": [(0, M)] * N, "evaluated": evaluated, "t_star": t_star,
        "winner_id": winner, "winning_nonce": winning_nonce,
        "solution_found": solution_found,
        "unique_evals": t_star, "duplicate_evals": (N - 1) * t_star,
        "exhausted": [t_star >= M] * N,
    }
