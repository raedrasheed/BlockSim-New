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
import random
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


# ---------------------------------------------------------------------------
# Dual-method energy accounting (explicit, per section 8)
# ---------------------------------------------------------------------------
def energy_by_attempts(m: MinerRecord) -> float:
    """Method 1: attempts * (power/hashrate) = attempts * e_hash."""
    return m.attempts * (m.power / m.hashrate)


def energy_by_power_time(m: MinerRecord) -> float:
    """Method 2: power * active_time."""
    return m.power * m.active_time


def assert_energy_methods_agree(result: ExperimentResult, tol=1e-9) -> bool:
    """Assert per-miner Method 1 == Method 2 within floating-point tolerance.
    The saving must come from fewer attempts / shorter active time, never from
    dividing a final energy value by N."""
    for m in result.miners:
        e1, e2 = energy_by_attempts(m), energy_by_power_time(m)
        assert math.isclose(e1, e2, rel_tol=tol, abs_tol=tol), \
            f"miner {m.miner_id}: attempts-energy {e1} != power-time energy {e2}"
    return True


# ---------------------------------------------------------------------------
# Stochastic (target-based) solution model
# ---------------------------------------------------------------------------
def bernoulli_p_from_target(target, bits=256):
    """Bitcoin-style success probability p = (target + 1) / 2**bits."""
    return (int(target) + 1) / float(2 ** bits)


def _geometric_first_success(rng, p):
    """1-based index of the first Bernoulli(p) success (may exceed any domain M).

    Drawn as a geometric jump so large domains are never enumerated:
        P(G > k) = (1-p)^k  =>  G = floor(ln U / ln(1-p)) + 1,  U ~ Uniform(0,1).
    """
    if p <= 0.0:
        return math.inf
    if p >= 1.0:
        return 1
    u = rng.random()
    if u <= 0.0:
        u = 5e-324                       # smallest positive double, avoids log(0)
    return int(math.floor(math.log(u) / math.log1p(-p))) + 1


def duplicate_full_domain_stochastic(M, N, p, seed,
                                     hashrate=DEFAULT_HASHRATE,
                                     energy_per_attempt=DEFAULT_ENERGY_PER_ATTEMPT):
    """Mode A, stochastic: one shared template assigns each nonce success/fail.
    All miners scan the same order and stop at the first success (or exhaust).
    Uses ONE geometric draw (the shared first-success position) so it PAIRS with
    the disjoint stochastic run at the same seed."""
    rng = random.Random(seed)
    g = _geometric_first_success(rng, p)         # 1-based shared first-success step
    sol = (g - 1) if g <= M else "none"          # 0-based index, or no solution
    return duplicate_full_domain(M, N, solution=sol,
                                 hashrate=hashrate, energy_per_attempt=energy_per_attempt)


def disjoint_partition_stochastic(M, N, p, seed,
                                  hashrate=DEFAULT_HASHRATE,
                                  energy_per_attempt=DEFAULT_ENERGY_PER_ATTEMPT):
    """Mode B, stochastic: SAME shared template as Mode A (identical seed -> same
    shared first-success position g), but the domain is partitioned. Paired with
    Mode A by construction."""
    rng = random.Random(seed)
    g = _geometric_first_success(rng, p)         # identical draw -> paired with Mode A
    sol = (g - 1) if g <= M else "none"
    return disjoint_partition(M, N, solution=sol,
                              hashrate=hashrate, energy_per_attempt=energy_per_attempt)


# ---------------------------------------------------------------------------
# Mode C — Independent Candidate Headers (reference / control)
# ---------------------------------------------------------------------------
def independent_candidate_headers_stochastic(M, N, p, seed,
                                             hashrate=DEFAULT_HASHRATE,
                                             energy_per_attempt=DEFAULT_ENERGY_PER_ATTEMPT):
    """Mode C: each miner searches a DISTINCT candidate header (its own
    independent success sequence). No two miners repeat identical complete-header
    work, so the 1/N duplicate-search saving does not apply. The network stops at
    the earliest per-miner success; every miner has performed t* = min_i G_i
    attempts by then (none succeeded earlier).

    This is a reference control, never mixed with Modes A/B.
    """
    rng = random.Random(seed)
    Gs = [_geometric_first_success(rng, p) for _ in range(N)]   # one draw per miner
    power = energy_per_attempt * hashrate
    e_hash = power / hashrate

    finite = [(g, i) for i, g in enumerate(Gs) if g <= M]
    if finite:
        gmin, winner_id = min(finite)            # earliest success, tie -> lowest id
        t_star = gmin
        solution_found = True
    else:
        winner_id, t_star, solution_found = None, M, False

    miners = []
    total_attempts = 0
    total_energy = 0.0
    aggregate_active = 0.0
    exhausted_ranges = 0
    for i in range(N):
        attempts = min(t_star, M)                 # every miner reaches the global stop step
        active_time = attempts / hashrate
        energy = attempts * e_hash
        found = (i == winner_id)
        exhausted = (attempts == M)               # scanned the whole domain (no success found)
        if exhausted:
            exhausted_ranges += 1
        miners.append(MinerRecord(
            miner_id=i, range_start=0, range_end=M, range_size=M,
            hashrate=hashrate, power=power, attempts=attempts,
            active_time=active_time, energy=energy,
            exhausted=exhausted, found=found))
        total_attempts += attempts
        total_energy += energy
        aggregate_active += active_time

    return ExperimentResult(
        mode="independent_candidate_headers", M=M, N=N,
        solution_found=solution_found,
        winning_nonce=(t_star - 1) if solution_found else None,
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
# Comparison (baseline vs pocol)
# ---------------------------------------------------------------------------
def compare_modes(baseline: ExperimentResult, pocol: ExperimentResult) -> dict:
    """Attempt/energy/time ratios and duplicate work avoided (baseline vs pocol)."""
    a_att, b_att = baseline.total_attempts, pocol.total_attempts
    a_en, b_en = baseline.total_energy, pocol.total_energy
    a_t, b_t = baseline.completion_time, pocol.completion_time
    return {
        "baseline_attempts": a_att,
        "pocol_attempts": b_att,
        "duplicate_evaluations_avoided": a_att - b_att,
        "attempts_ratio": (b_att / a_att) if a_att else float("nan"),
        "attempts_reduction_pct": (100.0 * (1 - b_att / a_att)) if a_att else float("nan"),
        "energy_ratio": (b_en / a_en) if a_en else float("nan"),
        "energy_reduction_pct": (100.0 * (1 - b_en / a_en)) if a_en else float("nan"),
        "time_ratio": (b_t / a_t) if a_t else float("nan"),
        "time_reduction_pct": (100.0 * (1 - b_t / a_t)) if a_t else float("nan"),
    }
