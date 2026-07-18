"""Continuous average-interval mining engine (immediate commit, no slot wait).

Removes the double-scaling defect (methodology §4): the finite domain is sized
from the AGGREGATE hash rate,

    M_total = floor(H_network * domain_time_budget)   (rounded to a multiple of N)

NOT from the per-miner rate. With H_i = H_network/N and M_i = M_total/N, each
equal share exhausts in M_i/H_i = domain_time_budget for EVERY N under H1 —
splitting a fixed-hash-rate network re-assigns candidate ownership; it does not
multiply network speed, and no artificial 600/N discovery time exists.

Difficulty lives exclusively in the target (p_success); the domain size only
bounds one template's search. On template exhaustion a NEW template is created
at the SAME difficulty (unless a D3 retarget boundary was crossed) and mining
continues immediately. Blocks commit AT discovery; the next template starts at
the commit time. Success is never fabricated.

Protocol semantics per template (equal-rate miners, step-based):
- duplicate baseline: every miner scans the whole domain in the same order;
  the first success in numeric order (g*) is found by all simultaneously at
  step g*+1 (winner = lowest id by convention); unique work = g*+1, duplicate
  work = (N-1)*(g*+1).
- pocol disjoint: per-range local successes; t* = min LOCAL step; each miner
  stops individually at min(own size, t*); no duplicate work.
- independent headers: per-miner independent streams with budget = share size;
  earliest per-miner success wins; no duplicate work.
"""
from __future__ import annotations

import math
import hashlib
from dataclasses import dataclass, field
from typing import Optional

from .configuration import (
    DiffExpConfig, PROTO_DUP, PROTO_IND, PROTO_POCOL, D3_RETARGET,
    GRID_EF_KG_PER_KWH,
)
from . import target as tg
from .difficulty import initial_target
from .nonce_partition import partition_nonce_domain, range_size
from .energy import build_miners, ACTIVE, IDLE, SLEEP


@dataclass
class BlockRecord:
    height: int
    commit_time: float          # == discovery time (immediate commit)
    discovery_time: float
    winner_id: int
    winning_nonce: Optional[int]
    template_index: int         # global template counter at discovery
    target: int
    difficulty: float           # expected hashes implied by the target
    attempts_this_template: int # network attempts inside the winning template


def _u(material):
    h = hashlib.sha256(material.encode()).digest()
    return (int.from_bytes(h[:8], "big") + 1) / float(2 ** 64)


def _geom(u, p):
    if p <= 0.0:
        return None
    if p >= 1.0:
        return 1
    return int(math.floor(math.log(u) / math.log1p(-p))) + 1


def _domain_total(cfg: DiffExpConfig) -> int:
    """M_total = H_network * budget (aggregate!), multiple of N, >= N."""
    m = int(cfg.network_hashrate() * cfg.domain_time_budget)
    return max(cfg.N, m - (m % cfg.N))


def _finished_state(cfg):
    return SLEEP if cfg.power.use_sleep else IDLE


def simulate(cfg: DiffExpConfig, retargeter=None):
    """Run the continuous experiment over [0, sim_seconds).

    retargeter: optional retarget.Retargeter (D3). Returns (metrics, miners,
    blocks). Deterministic for a fixed cfg.seed.
    """
    r = cfg.per_miner_hashrate()
    N = cfg.N
    fin = _finished_state(cfg)
    miners = build_miners(cfg)

    target_now = initial_target(cfg)
    if retargeter is not None:
        target_now = retargeter.current_target()

    M_total = _domain_total(cfg)
    shares = partition_nonce_domain(0, M_total, N)
    share_sizes = [range_size(x) for x in shares]

    t = 0.0
    sim_end = cfg.sim_seconds
    blocks = []
    template_counter = 0
    template_exhaustions = 0
    total_attempts = 0
    unique_evals = 0
    duplicate_evals = 0

    while t < sim_end - 1e-9:
        p = tg.p_from_target(target_now)
        tid = f"{cfg.protocol}:{cfg.seed}:{template_counter}"

        # per-miner assignment sizes for this template
        if cfg.protocol == PROTO_DUP:
            sizes = [M_total] * N
        else:                                   # pocol shares / independent budgets
            sizes = list(share_sizes)

        # successes
        if cfg.protocol in (PROTO_DUP, PROTO_POCOL):
            G = []
            for i, sz in enumerate(share_sizes):        # shared template (paired)
                g = _geom(_u(f"shared:{tid}:{i}"), p)
                G.append(g if (g is not None and sz > 0 and g <= sz) else None)
            if cfg.protocol == PROTO_POCOL:
                local = list(G)
                nonces = [shares[i][0] + g - 1 if g is not None else None
                          for i, g in enumerate(G)]
            else:
                globals_ = [shares[i][0] + g - 1 for i, g in enumerate(G)
                            if g is not None]
                if globals_:
                    g_star = min(globals_)
                    local = [g_star + 1] * N
                    nonces = [g_star] * N
                else:
                    local = [None] * N
                    nonces = [None] * N
        else:                                           # independent streams
            local = []
            for i, sz in enumerate(sizes):
                g = _geom(_u(f"indep:{tid}:{i}"), p)
                local.append(g if (g is not None and sz > 0 and g <= sz) else None)
            nonces = [None] * N

        # step budgets truncated by the simulation horizon
        avail = [min(sz, int(math.floor((sim_end - t) * r + 1e-9))) for sz in sizes]
        for m, a in zip(miners, avail):
            m.assigned_candidates += sizes[m.miner_id]
            if a > 0:
                m.transition(ACTIVE, t)

        valid = [(s, i) for i, s in enumerate(local) if s is not None and s <= avail[i]]
        if valid:
            t_star, winner = min(valid)
            t_disc = t + t_star / r
            att = 0
            for m, a, sz in zip(miners, avail, sizes):
                if a <= 0:
                    continue
                steps = min(sz, t_star)
                m.transition(fin, t + steps / r)
                m.evaluated_candidates += steps
                att += steps
            miners[winner].found_solution = True
            miners[winner].wins += 1
            total_attempts += att
            if cfg.protocol == PROTO_DUP:
                unique_evals += t_star
                duplicate_evals += att - t_star
            else:
                unique_evals += att
            blocks.append(BlockRecord(
                height=len(blocks) + 1, commit_time=t_disc, discovery_time=t_disc,
                winner_id=winner, winning_nonce=nonces[winner],
                template_index=template_counter, target=target_now,
                difficulty=tg.difficulty_from_target(target_now),
                attempts_this_template=att))
            # immediate restart at the commit time; optional D3 retarget
            if retargeter is not None:
                target_now = retargeter.on_block(t_disc)
            t = t_disc
        else:
            # no success within available steps: scan, idle individually, retemplate
            scanned_max = 0
            att = 0
            for m, a, sz in zip(miners, avail, sizes):
                if a <= 0:
                    continue
                m.transition(fin, t + a / r)
                m.evaluated_candidates += a
                att += a
                scanned_max = max(scanned_max, a)
            total_attempts += att
            if cfg.protocol == PROTO_DUP:
                unique_evals += scanned_max
                duplicate_evals += att - scanned_max
            else:
                unique_evals += att
            t_next = t + (scanned_max / r if scanned_max else (sim_end - t))
            fully = all(a == sz for a, sz in zip(avail, sizes))
            if fully and t_next < sim_end - 1e-9:
                template_exhaustions += 1        # same difficulty; new template
            t = t_next
        template_counter += 1

    for m in miners:
        m.finalize(sim_end)

    return _metrics(cfg, miners, blocks, template_counter, template_exhaustions,
                    total_attempts, unique_evals, duplicate_evals,
                    target_now), miners, blocks


def _metrics(cfg, miners, blocks, n_templates, exhaustions, attempts,
             unique_evals, duplicate_evals, final_target):
    commits = [b.commit_time for b in blocks]
    intervals = [b2 - b1 for b1, b2 in zip(commits, commits[1:])]
    total_e = sum(m.cumulative_energy_j for m in miners)
    active_s = sum(m.active_time_s for m in miners)
    idle_s = sum(m.idle_time_s for m in miners)
    sleep_s = sum(m.sleep_time_s for m in miners)
    hashes = sum(m.cumulative_hashes for m in miners)
    tx_total = cfg.txs_per_block * len(blocks)
    mean_diff = (sum(b.difficulty for b in blocks) / len(blocks)) if blocks else \
        tg.difficulty_from_target(final_target)
    mean_target = (sum(b.target for b in blocks) / len(blocks)) if blocks else \
        float(final_target)

    def _mean(x): return sum(x) / len(x) if x else float("nan")
    def _median(x):
        if not x: return float("nan")
        s = sorted(x); n = len(s)
        return s[n // 2] if n % 2 else 0.5 * (s[n // 2 - 1] + s[n // 2])

    return {
        "protocol": cfg.protocol, "N": cfg.N, "seed": cfg.seed,
        "hardware": cfg.hardware, "difficulty_mode": cfg.difficulty.mode,
        "t_target": cfg.t_target, "sim_seconds": cfg.sim_seconds,
        "per_miner_hashrate_hps": cfg.per_miner_hashrate(),
        "aggregate_hashrate_hps": cfg.network_hashrate(),
        "initial_difficulty": tg.difficulty_from_target(initial_target(cfg)),
        "mean_difficulty": mean_diff,
        "mean_target": mean_target,
        "final_difficulty": tg.difficulty_from_target(final_target),
        "accepted_blocks": len(blocks),
        "mean_block_interval_s": _mean(intervals),
        "median_block_interval_s": _median(intervals),
        "first_block_time_s": commits[0] if commits else float("nan"),
        "n_templates": n_templates,
        "template_exhaustions": exhaustions,
        "template_exhaustion_rate": exhaustions / n_templates if n_templates else float("nan"),
        "total_attempts": attempts,
        "unique_header_attempts": unique_evals,
        "duplicate_header_attempts": duplicate_evals,
        "total_hashes": hashes,
        "active_miner_seconds": active_s,
        "idle_miner_seconds": idle_s,
        "sleep_miner_seconds": sleep_s,
        "active_fraction": active_s / (cfg.N * cfg.sim_seconds),
        "idle_fraction": idle_s / (cfg.N * cfg.sim_seconds),
        "total_energy_j": total_e,
        "total_energy_kwh": total_e / 3.6e6,
        "co2_kg": (total_e / 3.6e6) * GRID_EF_KG_PER_KWH,
        "energy_per_accepted_block_kwh": (total_e / 3.6e6) / len(blocks)
            if blocks else float("nan"),
        "energy_per_tx_kwh": (total_e / 3.6e6) / tx_total if tx_total else float("nan"),
        "throughput_tx_per_s": tx_total / cfg.sim_seconds,
        # security-work metrics (section 15): from the target, never from waiting
        "accumulated_work_per_block": mean_diff,
        "actual_hashes_per_accepted_block": hashes / len(blocks) if blocks else float("nan"),
        "domain_M_total": _domain_total(cfg),
        "share_exhaust_time_s": (_domain_total(cfg) / cfg.N) / cfg.per_miner_hashrate(),
    }
