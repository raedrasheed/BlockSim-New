"""Continuous multi-round scheduler with power-state energy integration.

Two scheduling policies:
  * IMMEDIATE_RESTART  -- miners never idle; ACTIVE for the whole horizon
                          (control: energy-neutral regardless of mode).
  * FIXED_SLOT_IDLE    -- fixed slots; a miner drops to IDLE/SLEEP when it
                          finishes its assigned work, and the whole round closes
                          (all -> IDLE/SLEEP) at the first success, until the
                          next slot boundary.

This module (commit 3/10) provides the RoundOutcome contract and the scheduler
engine. Mode-specific outcome producers are added in commits 4-7.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional, Callable

from .configuration import (
    ExperimentConfig, build_miners, SCHED_IMMEDIATE, SCHED_FIXED_SLOT,
    MODE_A, MODE_B, MODE_C1, MODE_C2,
)
from .power_states import ACTIVE, IDLE, SLEEP
from experiments.nonce_partition.partition import partition_nonce_domain, range_size


@dataclass
class RoundOutcome:
    """The result of one round on one immutable template.

    evaluated[i] is miner i's candidate count AFTER global stopping (i.e. already
    truncated at t_star). t_star is the termination step (in candidates).
    """
    mode: str
    ranges: list                      # per-miner (start, end) half-open, or budget ranges
    evaluated: list                   # per-miner evaluated candidate count
    t_star: int                       # discovery/termination step (candidates)
    winner_id: Optional[int]
    winning_nonce: Optional[int]
    solution_found: bool
    unique_evals: int                 # distinct complete-header evaluations
    duplicate_evals: int              # repeated complete-header evaluations
    exhausted: list                   # per-miner: finished its whole assigned range


def _finished_state(cfg: ExperimentConfig):
    return SLEEP if cfg.power.use_sleep else IDLE


# ---------------------------------------------------------------------------
# Deterministic final-nonce worst-case outcomes (valid nonce at M-1)
# ---------------------------------------------------------------------------
def deterministic_outcome(cfg: ExperimentConfig, slot_index=0) -> RoundOutcome:
    """Final-nonce worst case: the only valid nonce is at M-1. The template is
    identical every slot, so slot_index is unused. Dispatches by mode."""
    N, M = cfg.N, cfg.M
    if cfg.mode == MODE_A:
        # Every miner scans the SAME complete domain in the SAME order; the
        # solution at M-1 is found only after the full scan -> t*=M, all miners
        # evaluate all M candidates (maximal duplication).
        ranges = [(0, M)] * N
        evaluated = [M] * N
        return RoundOutcome(
            mode=MODE_A, ranges=ranges, evaluated=evaluated, t_star=M,
            winner_id=0, winning_nonce=M - 1, solution_found=True,
            unique_evals=M, duplicate_evals=(N - 1) * M,
            exhausted=[True] * N)

    if cfg.mode == MODE_B:
        # Same immutable template, domain split into disjoint subranges. The
        # solution at M-1 lies in the owner's range; the round terminates when the
        # owner reaches it (local step = owner range size). Other miners are cut
        # off at t* by global stopping (or finish their smaller range earlier).
        ranges = partition_nonce_domain(0, M, N)
        owner = next(i for i, (s, e) in enumerate(ranges) if s <= (M - 1) < e)
        os_, oe = ranges[owner]
        t_star = (M - 1) - os_ + 1                 # owner's local discovery step
        evaluated = [min(range_size(rg), t_star) for rg in ranges]
        exhausted = [ev == range_size(rg) for ev, rg in zip(evaluated, ranges)]
        return RoundOutcome(
            mode=MODE_B, ranges=ranges, evaluated=evaluated, t_star=t_star,
            winner_id=owner, winning_nonce=M - 1, solution_found=True,
            unique_evals=sum(evaluated), duplicate_evals=0, exhausted=exhausted)

    raise NotImplementedError(f"deterministic mode {cfg.mode!r} not implemented yet")


# ---------------------------------------------------------------------------
# Stochastic outcomes (shared template for A & B; corrected local-time winner)
# ---------------------------------------------------------------------------
def stochastic_outcome(cfg: ExperimentConfig, slot_index=0) -> RoundOutcome:
    """A fresh immutable template per slot: template_seed = f(cfg.seed, slot)."""
    from .stochastic_template import (
        pocol_disjoint_outcome, duplicate_baseline_outcome,
    )
    N, M, p = cfg.N, cfg.M, cfg.p_success
    if p is None:
        raise ValueError("stochastic_outcome requires cfg.p_success")
    template_seed = cfg.seed * 1_000_003 + slot_index      # paired across A and B

    if cfg.mode == MODE_A:
        d = duplicate_baseline_outcome(M, N, p, template_seed)
    elif cfg.mode == MODE_B:
        d = pocol_disjoint_outcome(M, N, p, template_seed)
    else:
        raise NotImplementedError(f"stochastic mode {cfg.mode!r} not implemented yet")
    return RoundOutcome(mode=cfg.mode, **d)


def _play_slot(miners, outcome: RoundOutcome, r, slot_start, slot_end, cfg):
    """Integrate one FIXED_SLOT_IDLE slot. Miners are ACTIVE at slot_start.

    Each miner is ACTIVE while doing its evaluated work, then transitions to
    IDLE/SLEEP for the remainder of the slot. Because evaluated[i] is already
    truncated at t_star, a miner never stays ACTIVE past global discovery.
    """
    fin = _finished_state(cfg)
    for i, m in enumerate(miners):
        active_dur = outcome.evaluated[i] / r if r > 0 else 0.0
        active_end = min(slot_start + active_dur, slot_end)
        m.transition(fin, active_end)          # close ACTIVE portion, integrate
        # bookkeeping
        s, e = outcome.ranges[i]
        m.assigned_range_start, m.assigned_range_end = s, e
        m.assigned_candidate_count = e - s
        m.evaluated_candidate_count += outcome.evaluated[i]
        m.exhausted_range = outcome.exhausted[i]
        m.found_solution = m.found_solution or (i == outcome.winner_id)


def simulate_continuous(cfg: ExperimentConfig, outcome_fn: Callable[[ExperimentConfig, int], RoundOutcome]):
    """Run the experiment over [0, sim_seconds). `outcome_fn(cfg, slot_index)`
    returns a fresh RoundOutcome (new immutable template) for each slot/round.

    Returns a metrics dict plus the per-miner list.
    """
    r, p_active = cfg.per_miner_hashrate_power()
    miners = build_miners(cfg)
    sim = cfg.sim_seconds

    n_slots = 0
    successful_rounds = 0
    exhausted_rounds = 0
    unique_evals = 0
    duplicate_evals = 0
    discovery_times = []

    if cfg.schedule == SCHED_IMMEDIATE:
        # Miners never leave ACTIVE: finishing a range/round immediately starts the
        # next template. Energy = N * P * sim by construction (control case).
        # Round metrics are computed analytically from the per-round outcome.
        outcome = outcome_fn(cfg, 0)
        round_steps = outcome.t_star if outcome.t_star and outcome.t_star > 0 else outcome.ranges and max(e - s for s, e in outcome.ranges) or 1
        round_wall = round_steps / r if r > 0 else sim
        n_rounds = int(sim / round_wall) if round_wall > 0 else 0
        n_slots = n_rounds
        if outcome.solution_found:
            successful_rounds = n_rounds
        else:
            exhausted_rounds = n_rounds
        unique_evals = outcome.unique_evals * n_rounds
        duplicate_evals = outcome.duplicate_evals * n_rounds
        if outcome.solution_found:
            discovery_times = [round_wall] * n_rounds
        for m in miners:
            m.finalize(sim)                    # stays ACTIVE the whole horizon

    elif cfg.schedule == SCHED_FIXED_SLOT:
        t = 0.0
        idx = 0
        while t < sim - 1e-9:
            slot_end = min(t + cfg.slot_seconds, sim)
            outcome = outcome_fn(cfg, idx)
            _play_slot(miners, outcome, r, t, slot_end, cfg)
            n_slots += 1
            if outcome.solution_found:
                successful_rounds += 1
                discovery_times.append(outcome.t_star / r if r > 0 else 0.0)
            else:
                exhausted_rounds += 1
            unique_evals += outcome.unique_evals
            duplicate_evals += outcome.duplicate_evals
            t = slot_end
            idx += 1
            if t < sim - 1e-9:
                for m in miners:
                    m.transition(ACTIVE, t)    # next slot: power back up
        for m in miners:
            m.finalize(sim)
    else:
        raise ValueError(f"unknown schedule {cfg.schedule!r}")

    total_energy_j = sum(m.cumulative_energy_j for m in miners)
    active_s = sum(m.active_time_s for m in miners)
    idle_s = sum(m.idle_time_s for m in miners)
    sleep_s = sum(m.sleep_time_s for m in miners)
    co2_kg = (total_energy_j / 3.6e6) * 0.445

    metrics = {
        "N": cfg.N, "M": cfg.M, "mode": cfg.mode, "schedule": cfg.schedule,
        "hardware": cfg.hardware, "idle_ratio": cfg.power.idle_ratio,
        "sleep_ratio": cfg.power.sleep_ratio, "use_sleep": cfg.power.use_sleep,
        "slot_seconds": cfg.slot_seconds, "sim_seconds": sim,
        "per_miner_hashrate_hps": r, "per_miner_active_power_w": p_active,
        "aggregate_active_power_w": p_active * cfg.N,
        "n_slots": n_slots,
        "successful_rounds": successful_rounds,
        "exhausted_rounds": exhausted_rounds,
        "active_miner_seconds": active_s,
        "idle_miner_seconds": idle_s,
        "sleep_miner_seconds": sleep_s,
        "unique_candidate_evaluations": unique_evals,
        "duplicate_header_evaluations": duplicate_evals,
        "total_energy_j": total_energy_j,
        "total_energy_kwh": total_energy_j / 3.6e6,
        "co2_kg": co2_kg,
        "energy_per_successful_round_kwh": (total_energy_j / 3.6e6 / successful_rounds)
                                           if successful_rounds else float("nan"),
        "avg_discovery_time_s": (sum(discovery_times) / len(discovery_times))
                                if discovery_times else float("nan"),
        "pct_time_active": 100.0 * active_s / (cfg.N * sim) if sim else float("nan"),
        "slot_utilization": (successful_rounds / n_slots) if n_slots else float("nan"),
        "total_state_time_s": active_s + idle_s + sleep_s,
    }
    return metrics, miners
