"""Core model for the disjoint-nonce worst-case experiment.

Analytical, big-integer safe (no nonce enumeration). See
docs/NONCE_PARTITION_WORST_CASE_METHODOLOGY.md for the equations.

This module builds up in three commits:
  (3/8) synchronous-step engine + global stopping + Mode A duplicate baseline
  (4/8) Mode B disjoint partition
  (5/8) Mode C independent headers + stochastic model + dual-energy assertion
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field, asdict
from typing import Optional

from .partition import range_size, partition_nonce_domain

# Abstract defaults: one evaluation per second, one energy unit per evaluation.
# power = energy_per_attempt * hashrate  =>  e_hash = power/hashrate = energy_per_attempt,
# so per-attempt energy and power*time energy are identical by construction (asserted).
DEFAULT_HASHRATE = 1.0                # candidate evaluations per second (r_i)
DEFAULT_ENERGY_PER_ATTEMPT = 1.0      # abstract energy unit per candidate (e_hash)


@dataclass
class MinerRecord:
    miner_id: int
    range_start: int
    range_end: int          # half-open [range_start, range_end)
    range_size: int
    hashrate: float
    power: float
    attempts: int
    active_time: float
    energy: float
    exhausted: bool         # evaluated its entire assigned range
    found: bool             # evaluated the winning nonce at the global discovery step


@dataclass
class ExperimentResult:
    mode: str
    M: int
    N: int
    solution_found: bool
    winning_nonce: Optional[int]
    winner_id: Optional[int]
    discovery_step: Optional[int]       # t* (evaluations until discovery), None if no solution
    completion_time: float              # wall-clock time to termination (t_end / r)
    total_attempts: int
    aggregate_active_seconds: float
    total_energy: float
    exhausted_ranges: int               # miners that fully scanned their range
    hashrate: float
    energy_per_attempt: float
    power: float
    miners: list = field(default_factory=list)

    def to_dict(self, include_miners=False):
        d = {k: v for k, v in asdict(self).items() if k != "miners"}
        if include_miners:
            d["miners"] = [asdict(m) for m in self.miners]
        return d


def _resolve_solution(solution, M):
    """Map a solution spec to the winning (lowest-index, first-found) nonce or None.

    solution may be: 'first', 'middle', 'last', 'none'/None, an int, or an
    iterable of ints (the lowest is found first in scan order).
    """
    if solution is None or solution == "none":
        return None
    if solution == "first":
        return 0
    if solution == "middle":
        return M // 2
    if solution == "last":
        return M - 1
    if isinstance(solution, int):
        return solution
    vals = [int(v) for v in solution if 0 <= int(v) < M]
    return min(vals) if vals else None


def _run_engine(mode, M, N, ranges, winning_nonce,
                hashrate=DEFAULT_HASHRATE,
                energy_per_attempt=DEFAULT_ENERGY_PER_ATTEMPT):
    """Synchronous-step engine shared by all modes.

    All miners start at t=0 and evaluate one candidate per step at `hashrate`.
    `t_star` is the global termination step: the step at which the winning nonce
    is first evaluated by its owner (min over owners), or the largest range size
    when there is no solution (full exhaustion). Global stopping means steps
    1..t_star occur and nothing after t_star does, so every miner performs
    exactly min(size_i, t_star) attempts.
    """
    if winning_nonce is not None and not (0 <= winning_nonce < M):
        winning_nonce = None  # solution outside the domain == no solution here

    power = energy_per_attempt * hashrate      # so power/hashrate == energy_per_attempt
    e_hash = power / hashrate

    sizes = [range_size(r) for r in ranges]
    max_size = max(sizes) if sizes else 0

    # local discovery step for each miner that owns the winning nonce
    owner_local_steps = []
    if winning_nonce is not None:
        for (s, e) in ranges:
            if s <= winning_nonce < e:
                owner_local_steps.append(winning_nonce - s + 1)

    solution_found = bool(owner_local_steps)
    if solution_found:
        t_star = min(owner_local_steps)          # first owner to reach it wins
    else:
        t_star = max_size                        # run until the last range exhausts

    miners = []
    winner_id = None
    total_attempts = 0
    total_energy = 0.0
    aggregate_active = 0.0
    exhausted_ranges = 0

    for i, (s, e) in enumerate(ranges):
        size = sizes[i]
        attempts = min(size, t_star)
        active_time = attempts / hashrate
        energy_m1 = attempts * e_hash                    # Method 1: per-attempt
        energy_m2 = power * active_time                   # Method 2: power * time
        assert math.isclose(energy_m1, energy_m2, rel_tol=1e-9, abs_tol=1e-9), \
            f"energy methods disagree: {energy_m1} vs {energy_m2}"
        energy = energy_m1

        owns = winning_nonce is not None and s <= winning_nonce < e
        found = owns and (winning_nonce - s + 1 == t_star)
        if found and winner_id is None:
            winner_id = i
        exhausted = (attempts == size)
        if exhausted:
            exhausted_ranges += 1

        miners.append(MinerRecord(
            miner_id=i, range_start=s, range_end=e, range_size=size,
            hashrate=hashrate, power=power, attempts=attempts,
            active_time=active_time, energy=energy,
            exhausted=exhausted, found=found))
        total_attempts += attempts
        total_energy += energy
        aggregate_active += active_time

    return ExperimentResult(
        mode=mode, M=M, N=N,
        solution_found=solution_found,
        winning_nonce=winning_nonce if solution_found else None,
        winner_id=winner_id,
        discovery_step=t_star if solution_found else None,
        completion_time=t_star / hashrate,
        total_attempts=total_attempts,
        aggregate_active_seconds=aggregate_active,
        total_energy=total_energy,
        exhausted_ranges=exhausted_ranges,
        hashrate=hashrate, energy_per_attempt=energy_per_attempt, power=power,
        miners=miners)


# ---------------------------------------------------------------------------
# Mode A — Common-Template Duplicate-Search Baseline
# ---------------------------------------------------------------------------
def duplicate_full_domain(M, N, solution="last",
                          hashrate=DEFAULT_HASHRATE,
                          energy_per_attempt=DEFAULT_ENERGY_PER_ATTEMPT):
    """Mode A: every miner receives the SAME immutable template and the COMPLETE
    nonce domain [0, M), starts at the same nonce, and scans in the same order,
    so all N miners redundantly evaluate identical candidates.

    Final-nonce worst case (solution='last'): every miner evaluates all M
    candidates -> total_attempts = N*M, total_energy = N*M*e_hash.
    """
    winning_nonce = _resolve_solution(solution, M)
    ranges = [(0, M) for _ in range(N)]         # identical whole-domain range for all
    return _run_engine("duplicate_full_domain", M, N, ranges, winning_nonce,
                       hashrate=hashrate, energy_per_attempt=energy_per_attempt)


# ---------------------------------------------------------------------------
# Mode B — PoCol Disjoint-Nonce Allocation
# ---------------------------------------------------------------------------
def disjoint_partition(M, N, solution="last",
                       hashrate=DEFAULT_HASHRATE,
                       energy_per_attempt=DEFAULT_ENERGY_PER_ATTEMPT):
    """Mode B: same immutable template, but the domain [0, M) is split into N
    mutually disjoint sub-ranges (partition.partition_nonce_domain). Each miner
    scans only its own range and never evaluates a nonce assigned to another
    miner, so each candidate is evaluated exactly once.

    Final-nonce worst case (solution='last', M divisible by N): the domain is
    covered once -> total_attempts = M, total_energy = M*e_hash, a 1-1/N
    reduction versus Mode A.
    """
    winning_nonce = _resolve_solution(solution, M)
    ranges = partition_nonce_domain(0, M, N)
    return _run_engine("disjoint_partition", M, N, ranges, winning_nonce,
                       hashrate=hashrate, energy_per_attempt=energy_per_attempt)
