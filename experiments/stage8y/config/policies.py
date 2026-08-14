"""Stage 8Y — active-set selection and reserve-activation policies.

Selection rules (brief section 14). Every rule is deterministic given
(population, target, seed) and every tie-break is documented and stable.

    S1 RANDOM      an unbiased random subset, drawn from a dedicated RNG stream
    S2 HASH_FIRST  rank by h_i descending; tie-break h desc, then id asc
    S3 EFF_FIRST   rank by eta_i = P_i/h_i ascending; tie-break h desc, then id asc
    S4 OPTIMIZE    solve  min sum_{i in A} P_i   s.t.  sum_{i in A} h_i >= H_required

S4 is solved exactly, not greedily. Because the registry contains few distinct
device classes, the search enumerates the unit counts of every class except the
most efficient one and solves the remaining class in closed form. Ties are broken
by the documented rule: lowest power, then highest hash, then lexicographically
smallest count vector in efficiency order, then lowest miner ids.

Targets can be expressed as an active **hash-capacity** fraction (preferred, and
used by the confirmatory policies) or as an active **miner-count** fraction (used
only by the declared secondary sweep, precisely to demonstrate that in a
heterogeneous network the two are not the same number).
"""

from __future__ import annotations

import random
from functools import lru_cache
from typing import Dict, List, Sequence, Tuple

from experiments.stage8y.config.hardware import Miner, Population

S1_RANDOM = "S1_RANDOM"
S2_HASH_FIRST = "S2_HASH_FIRST"
S3_EFF_FIRST = "S3_EFF_FIRST"
S4_OPTIMIZE = "S4_OPTIMIZE"
SELECTION_RULES = (S1_RANDOM, S2_HASH_FIRST, S3_EFF_FIRST, S4_OPTIMIZE)

SELECTION_LABELS = {
    S1_RANDOM: "Random active subset (unbiased control)",
    S2_HASH_FIRST: "Hash-first: highest hash rate first",
    S3_EFF_FIRST: "Efficiency-first: lowest J/TH first",
    S4_OPTIMIZE: "Optimization: min total active power subject to a hash-capacity floor",
}

# Allocation of nonce slots
ALLOC_EQUAL = "equal"
ALLOC_HASH = "hash"


# --------------------------------------------------------------------------
# Exact optimiser for S4
# --------------------------------------------------------------------------
@lru_cache(maxsize=4096)
def _optimize_counts(classes: Tuple[Tuple[float, float, int], ...],
                     h_required: float) -> Tuple[int, ...]:
    """min sum n_k*P_k  s.t.  sum n_k*h_k >= h_required, 0 <= n_k <= avail_k.

    ``classes`` is a tuple of (h_k, P_k, available_k) already sorted by efficiency
    P_k/h_k ascending. Returns the chosen count per class. Exact enumeration over
    every class except the first (most efficient), which is solved in closed form.
    """
    k = len(classes)
    best = None  # (power, -hash, counts)

    def consider(counts: List[int]) -> None:
        nonlocal best
        p = sum(c * cl[1] for c, cl in zip(counts, classes))
        h = sum(c * cl[0] for c, cl in zip(counts, classes))
        if h + 1e-9 < h_required:
            return
        key = (p, -h, tuple(counts))
        if best is None or key < best:
            best = key

    def recurse(idx: int, counts: List[int]) -> None:
        if idx == 0:
            # counts is a shared buffer: class 0's count from the previous branch
            # must not leak into the residual, or the closed form under-solves it.
            counts[0] = 0
            h_rest = sum(c * cl[0] for c, cl in zip(counts, classes))
            need = h_required - h_rest
            n0 = 0 if need <= 0 else min(classes[0][2],
                                         -(-int(need * 1e6) // int(classes[0][0] * 1e6)))
            # ensure the ceiling is exact under float arithmetic
            while n0 < classes[0][2] and n0 * classes[0][0] + h_rest + 1e-9 < h_required:
                n0 += 1
            counts[0] = n0
            consider(counts)
            return
        for n in range(classes[idx][2] + 1):
            counts[idx] = n
            recurse(idx - 1, counts)
        counts[idx] = 0

    recurse(k - 1, [0] * k)
    if best is None:                       # requirement exceeds installed capacity
        return tuple(cl[2] for cl in classes)
    return best[2]


def _sorted_classes(pop: Population) -> List[Tuple[str, float, float, List[Miner]]]:
    """Device classes sorted by efficiency ascending; ties by hash descending, key asc."""
    groups: Dict[str, List[Miner]] = {}
    for m in pop.miners:
        groups.setdefault(m.device_key, []).append(m)
    out = []
    for key, ms in groups.items():
        ms.sort(key=lambda m: m.id)
        out.append((key, ms[0].hashrate_hps, ms[0].active_power_w, ms))
    out.sort(key=lambda t: (t[2] / t[1], -t[1], t[0]))
    return out


# --------------------------------------------------------------------------
# Public selection API
# --------------------------------------------------------------------------
def select_active(pop: Population, rule: str, *,
                  target_hash_fraction: float = None,
                  target_count_fraction: float = None,
                  rng: random.Random = None) -> List[int]:
    """Return the sorted list of active miner ids under ``rule``.

    Exactly one of ``target_hash_fraction`` / ``target_count_fraction`` must be set.
    """
    if (target_hash_fraction is None) == (target_count_fraction is None):
        raise ValueError("set exactly one of target_hash_fraction / target_count_fraction")

    miners = list(pop.miners)
    h_total = pop.total_hashrate_hps

    if target_count_fraction is not None:
        k = max(1, min(len(miners), int(round(target_count_fraction * len(miners)))))
        if rule == S1_RANDOM:
            r = rng or random.Random(0)
            order = list(miners)
            r.shuffle(order)
        elif rule == S2_HASH_FIRST:
            order = sorted(miners, key=lambda m: (-m.hashrate_hps, m.id))
        elif rule in (S3_EFF_FIRST, S4_OPTIMIZE):
            # With a fixed miner budget, minimising power for that budget is exactly
            # taking the lowest-power units; efficiency-first is used for S3 and the
            # count-constrained optimum for S4 is the k lowest-power units.
            if rule == S3_EFF_FIRST:
                order = sorted(miners, key=lambda m: (m.active_power_w / m.hashrate_hps,
                                                      -m.hashrate_hps, m.id))
            else:
                order = sorted(miners, key=lambda m: (m.active_power_w, -m.hashrate_hps,
                                                      m.id))
        else:
            raise ValueError(f"unknown rule {rule!r}")
        return sorted(m.id for m in order[:k])

    h_req = float(target_hash_fraction) * h_total
    if h_req >= h_total - 1e-6:
        return [m.id for m in miners]

    if rule == S1_RANDOM:
        r = rng or random.Random(0)
        order = list(miners)
        r.shuffle(order)
    elif rule == S2_HASH_FIRST:
        order = sorted(miners, key=lambda m: (-m.hashrate_hps, m.id))
    elif rule == S3_EFF_FIRST:
        order = sorted(miners, key=lambda m: (m.active_power_w / m.hashrate_hps,
                                              -m.hashrate_hps, m.id))
    elif rule == S4_OPTIMIZE:
        classes = _sorted_classes(pop)
        key = tuple((c[1], c[2], len(c[3])) for c in classes)
        counts = _optimize_counts(key, h_req)
        chosen: List[int] = []
        for cnt, cls in zip(counts, classes):
            chosen.extend(m.id for m in cls[3][:cnt])
        return sorted(chosen)
    else:
        raise ValueError(f"unknown rule {rule!r}")

    chosen, acc = [], 0.0
    for m in order:
        if acc >= h_req - 1e-9:
            break
        chosen.append(m.id)
        acc += m.hashrate_hps
    return sorted(chosen)


def active_fractions(pop: Population, active_ids: Sequence[int]) -> Dict[str, float]:
    """Report r (count), r_H (hash) and r_P (power) for an active set.

    These three numbers are different in a heterogeneous network, which is why the
    brief forbids interpreting a miner-count fraction as a hash-rate fraction.
    """
    s = set(active_ids)
    sel = [m for m in pop.miners if m.id in s]
    return {
        "r_count": len(sel) / pop.n_miners if pop.n_miners else 0.0,
        "r_hash": sum(m.hashrate_hps for m in sel) / pop.total_hashrate_hps,
        "r_power": sum(m.active_power_w for m in sel) / pop.total_power_w,
        "n_active": len(sel),
        "H_active_Hps": sum(m.hashrate_hps for m in sel),
        "P_active_W": sum(m.active_power_w for m in sel),
    }


# --------------------------------------------------------------------------
# Adaptive reserve schedules (policy P4)
# --------------------------------------------------------------------------
#: Staged active hash-capacity targets. Stage s is entered after s * t_trigger
#: seconds of the current round have elapsed without an accepted block.
DEFAULT_RESERVE_SCHEDULE: Tuple[float, ...] = (0.60, 0.75, 0.90, 1.00)

RESERVE_SCHEDULES: Dict[str, Tuple[float, ...]] = {
    "sched_60_75_90_100": (0.60, 0.75, 0.90, 1.00),
    "sched_40_60_80_100": (0.40, 0.60, 0.80, 1.00),
    "sched_50_70_85_100": (0.50, 0.70, 0.85, 1.00),
    "sched_70_80_90_100": (0.70, 0.80, 0.90, 1.00),
    "sched_80_90_95_100": (0.80, 0.90, 0.95, 1.00),
}


def reserve_stage_sets(pop: Population, rule: str, schedule: Sequence[float],
                       rng: random.Random = None) -> List[List[int]]:
    """Nested active sets, one per stage.

    Reserve activation may only *add* capacity, never remove it, so each stage is
    unioned with the previous one. Selection rules that are already monotone in the
    target are unaffected by the union; S4 may not be monotone, so the union makes
    the nesting explicit rather than assumed.
    """
    sets: List[List[int]] = []
    acc: set = set()
    for frac in schedule:
        sel = set(select_active(pop, rule, target_hash_fraction=frac, rng=rng))
        acc |= sel
        sets.append(sorted(acc))
    return sets
