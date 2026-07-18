"""Fixed 600-second round state machine with explicit miner events.

States: ROUND_INITIALIZING -> ROUND_SEARCHING -> SOLUTION_FOUND -> ROUND_WAITING
        -> ROUND_COMMITTING -> ROUND_CLOSED
(an all-exhausted template re-enters ROUND_SEARCHING with a new TemplateID; a
round with no success ends CLOSED with no committed block — reported honestly).

Per-miner semantics (methodology §2, §4):
- miners with non-empty assignments go ACTIVE at the search-phase start;
- a miner stops INDIVIDUALLY at min(own exhaustion, global discovery, boundary);
- no hashes / no ACTIVE energy after discovery_time;
- everyone waits IDLE (or SLEEP) until round_end where the buffered block is
  committed; the next round starts exactly at the boundary.

The engine is event-explicit per miner but analytical in time (no per-nonce
loop), so M = 8.46e14 (H1) costs the same as M = 100.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional, Callable

from .configuration import (
    ROUND_INITIALIZING, ROUND_SEARCHING, SOLUTION_FOUND, ROUND_WAITING,
    ROUND_COMMITTING, ROUND_CLOSED, PROTO_DUP,
)
from .miner_state import ACTIVE, IDLE, SLEEP


@dataclass
class TemplateOutcome:
    """One immutable template's assignment + success structure.

    local_success[i]: 1-based step inside miner i's assignment at which it would
    find a valid candidate, or None. nonce_value[i]: the global nonce that step
    corresponds to (None for independent headers, where nonces are per-stream).
    """
    template_id: str
    sizes: list
    local_success: list
    nonce_value: list


@dataclass
class RoundResult:
    round_id: int
    round_start: float
    round_end: float
    committed: bool = False
    commit_time: Optional[float] = None
    discovery_time: Optional[float] = None
    winner_id: Optional[int] = None
    winning_nonce: Optional[int] = None
    n_templates: int = 0
    exhausted_templates: int = 0
    attempts: int = 0                    # candidate evaluations this round
    unique_evals: int = 0
    duplicate_evals: int = 0
    post_discovery_idle_s: float = 0.0   # summed over miners
    state_trace: list = field(default_factory=list)


def _finished_state(cfg):
    return SLEEP if cfg.power.use_sleep else IDLE


def run_round(cfg, miners, round_id, round_start, template_provider):
    """Play one fixed round. template_provider(cfg, round_id, template_index)
    -> TemplateOutcome. Returns RoundResult. Miners are left in IDLE/SLEEP at
    round_end (the caller starts the next round at that exact boundary)."""
    r_rate, _ = cfg.per_miner_rate_power()
    fin = _finished_state(cfg)
    res = RoundResult(round_id=round_id, round_start=round_start,
                      round_end=round_start + cfg.round_seconds)
    res.state_trace.append(ROUND_INITIALIZING)

    t = round_start
    template_index = 0
    while True:
        outcome = template_provider(cfg, round_id, template_index)
        res.n_templates += 1
        res.state_trace.append(ROUND_SEARCHING)

        # steps each miner CAN evaluate before the boundary
        budget_steps = int(math.floor((res.round_end - t) * r_rate + 1e-9))
        avail = [min(sz, budget_steps) for sz in outcome.sizes]

        # activate miners with work (empty assignments stay IDLE — invariant)
        for m, a in zip(miners, avail):
            m.assigned_candidates += outcome.sizes[m.miner_id]
            if a > 0:
                m.transition(ACTIVE, t)

        valid = [(s, i) for i, s in enumerate(outcome.local_success)
                 if s is not None and s <= avail[i]]

        if valid:
            t_star, winner = min(valid)          # min LOCAL discovery step
            t_disc = t + t_star / r_rate
            res.state_trace.append(SOLUTION_FOUND)
            res.discovery_time = t_disc
            res.winner_id = winner
            res.winning_nonce = outcome.nonce_value[winner]
            for m, a, sz in zip(miners, avail, outcome.sizes):
                if a <= 0:
                    continue
                steps = min(sz, t_star)          # individual stop: exhaust OR global stop
                stop = t + steps / r_rate
                m.transition(fin, stop)          # no ACTIVE energy after its stop
                m.evaluated_candidates += steps
                m.exhausted_assignment = (steps == sz)
                res.attempts += steps
                res.post_discovery_idle_s += max(0.0, res.round_end - stop)
            miners[winner].found_solution = True
            miners[winner].wins += 1
            if cfg.protocol == PROTO_DUP:
                res.unique_evals += t_star
                res.duplicate_evals += res.attempts - t_star
            else:
                res.unique_evals += res.attempts
            res.committed = True
            res.commit_time = res.round_end
            res.state_trace.append(ROUND_WAITING)
            res.state_trace.append(ROUND_COMMITTING)
            break

        # ---- no success within this template's available steps ----
        scanned = 0
        for m, a, sz in zip(miners, avail, outcome.sizes):
            if a <= 0:
                continue
            stop = t + a / r_rate
            m.transition(fin, stop)              # idles the moment ITS range ends
            m.evaluated_candidates += a
            m.exhausted_assignment = (a == sz)
            res.attempts += a
            scanned = max(scanned, a)
        if cfg.protocol == PROTO_DUP:
            res.unique_evals += scanned
            res.duplicate_evals += sum(avail) - scanned
        else:
            res.unique_evals += sum(avail)

        fully_exhausted = all(a == sz for a, sz in zip(avail, outcome.sizes))
        t_next = t + (scanned / r_rate if scanned else cfg.round_seconds)
        if fully_exhausted and t_next < res.round_end - 1e-9:
            res.exhausted_templates += 1         # honest: no fabricated success
            template_index += 1
            t = t_next
            continue                             # new immutable template, same round
        break                                    # boundary reached: empty round

    res.state_trace.append(ROUND_CLOSED)
    return res


def simulate(cfg, template_provider):
    """Run n_rounds fixed rounds back-to-back over [0, sim_seconds); finalize
    every miner exactly to sim_seconds. Returns (metrics, miners, rounds)."""
    from .miner_state import build_miners
    miners = build_miners(cfg)
    for m in miners:                              # rounds start with miners idle
        m.current_state = IDLE if not cfg.power.use_sleep else SLEEP

    rounds = []
    t = 0.0
    for rid in range(cfg.n_rounds()):
        rr = run_round(cfg, miners, rid, t, template_provider)
        rounds.append(rr)
        t = rr.round_end                          # next round starts AT the boundary
    for m in miners:
        m.finalize(cfg.sim_seconds)

    return _metrics(cfg, miners, rounds), miners, rounds


def _metrics(cfg, miners, rounds):
    accepted = [r for r in rounds if r.committed]
    commits = [r.commit_time for r in accepted]
    intervals = [b - a for a, b in zip(commits, commits[1:])]
    disc = [r.discovery_time - r.round_start for r in accepted]
    total_e = sum(m.cumulative_energy_j for m in miners)
    tx_total = cfg.txs_per_block * len(accepted)
    active_s = sum(m.active_time_s for m in miners)
    idle_s = sum(m.idle_time_s for m in miners)
    sleep_s = sum(m.sleep_time_s for m in miners)
    per_e = [m.cumulative_energy_kwh for m in miners]
    per_w = [m.evaluated_candidates for m in miners]

    def _mean(x): return sum(x) / len(x) if x else float("nan")
    def _median(x):
        if not x: return float("nan")
        s = sorted(x); n = len(s)
        return s[n // 2] if n % 2 else 0.5 * (s[n // 2 - 1] + s[n // 2])
    def _fair(x):
        mu = _mean(x)
        if not x or mu == 0: return 0.0
        var = sum((v - mu) ** 2 for v in x) / len(x)
        return (var ** 0.5) / mu                   # coefficient of variation

    return {
        "protocol": cfg.protocol, "N": cfg.N, "seed": cfg.seed,
        "hardware": cfg.hardware, "idle_ratio": cfg.power.idle_ratio,
        "sleep_ratio": cfg.power.sleep_ratio, "use_sleep": cfg.power.use_sleep,
        "M": cfg.effective_M(), "placement": cfg.placement,
        "p_success": cfg.p_success, "round_seconds": cfg.round_seconds,
        "sim_seconds": cfg.sim_seconds,
        "n_rounds": len(rounds),
        "accepted_blocks": len(accepted),
        "empty_rounds": len(rounds) - len(accepted),
        "exhausted_templates": sum(r.exhausted_templates for r in rounds),
        "mean_discovery_time_s": _mean(disc),
        "median_discovery_time_s": _median(disc),
        "mean_post_discovery_idle_s": _mean(
            [r.post_discovery_idle_s / cfg.N for r in accepted]),
        "accepted_block_interval_s": _mean(intervals) if intervals else
            (cfg.round_seconds if len(accepted) == 1 else float("nan")),
        "throughput_tx_per_s": tx_total / cfg.sim_seconds,
        "total_attempts": sum(r.attempts for r in rounds),
        "unique_candidate_evaluations": sum(r.unique_evals for r in rounds),
        "duplicate_header_evaluations": sum(r.duplicate_evals for r in rounds),
        "active_miner_seconds": active_s,
        "idle_miner_seconds": idle_s,
        "sleep_miner_seconds": sleep_s,
        "pct_time_active": 100.0 * active_s / (cfg.N * cfg.sim_seconds),
        "total_hashes": sum(m.cumulative_hashes for m in miners),
        "total_energy_j": total_e,
        "total_energy_kwh": total_e / 3.6e6,
        "co2_kg": (total_e / 3.6e6) * 0.445,
        "energy_per_accepted_block_kwh": (total_e / 3.6e6) / len(accepted)
            if accepted else float("nan"),
        "energy_per_tx_kwh": (total_e / 3.6e6) / tx_total if tx_total else float("nan"),
        "winner_max_share": (max(m.wins for m in miners) / len(accepted))
            if accepted else float("nan"),
        "per_miner_energy_kwh_min": min(per_e), "per_miner_energy_kwh_max": max(per_e),
        "workload_fairness_cv": _fair(per_w),
        "energy_fairness_cv": _fair(per_e),
    }
