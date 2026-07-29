"""Stage 5B1 unified scenario engine for B0, B1, B2, B3_C1_CONTINUOUS_DISJOINT,
and C2. Round-structured discrete engine over a fixed duration; deterministic
(named random streams); decouples hash rate from range size; implements C2 idle
as an in-loop state transition; instruments coordination separately from abstract
protocol activity.

Scenario search semantics (per template generation, finite domain size S):
  * B0  independent templates  -> each miner searches its OWN domain; no cross-miner duplicates.
  * B1  common template, all miners start at nonce 0, ordered forward -> heavy duplicates;
        the fastest miner reaches the lowest solution first (winner_time = min_pos / H_max).
  * B2  common template, seeded random start, forward with single-traversal stop -> partial overlap.
  * B3/C1 common template, disjoint ranges, continuous -> zero overlap.
  * C2  disjoint ranges + in-loop idle after range completion.

Solution count K ~ Binomial(S_cov, p) (exact); positions unique (without
replacement). A round with K=0 over the covered domain exhausts -> new template
generation (bounded). Energy = Sum_i (P_active_i*t_active_i + P_idle_i*t_idle_i).
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Tuple

import numpy as np

J_PER_KWH = 3_600_000.0
HASHES_PER_TH = 1e12
SCENARIOS = ["B0", "B1", "B2", "B3_C1_CONTINUOUS_DISJOINT", "C2"]
COMMON_TEMPLATE = {"B0": False, "B1": True, "B2": True,
                   "B3_C1_CONTINUOUS_DISJOINT": True, "C2": True}
# DISJOINT search/allocation: B0 (independent templates) is modelled with the
# same full-parallel, non-redundant coverage as B3 (each miner distinct work);
# it differs from B3 only in template semantics + coordination (no common-template
# agreement), captured by COMMON_TEMPLATE and the agreement-operation counters.
DISJOINT = {"B0": True, "B1": False, "B2": False,
            "B3_C1_CONTINUOUS_DISJOINT": True, "C2": True}
IDLE = {"B0": False, "B1": False, "B2": False,
        "B3_C1_CONTINUOUS_DISJOINT": False, "C2": True}
AGREEMENT = {"B0": False, "B1": True, "B2": True,
             "B3_C1_CONTINUOUS_DISJOINT": True, "C2": True}   # needs common-template agreement
MAX_REFRESH = 100000


# ---------------------------------------------------------------------------
# Named random streams (independent, reproducible)
# ---------------------------------------------------------------------------
STREAM_NAMES = ("solution_positions", "solution_count", "miner_starts",
                "hash_rate_distribution", "propagation_delay", "inactive_selection",
                "topology", "transaction_arrival")


def derive_stream_seeds(master_seed: int) -> Dict[str, int]:
    """Deterministic per-component seeds; adding a draw to one stream does not
    shift another (each stream is seeded independently from the master)."""
    seeds = {}
    for name in STREAM_NAMES:
        h = hashlib.sha256(f"{master_seed}:{name}".encode()).digest()[:8]
        seeds[name] = int.from_bytes(h, "big")
    return seeds


def rng(master_seed: int, name: str) -> np.random.Generator:
    return np.random.default_rng(derive_stream_seeds(master_seed)[name])


# ---------------------------------------------------------------------------
# Range allocation (decoupled from hash rate)
# ---------------------------------------------------------------------------
def allocate_equal(S: int, n: int) -> List[Tuple[int, int]]:
    """base = S//n candidates each; the first `S%n` miners get base+1. Exact
    cover, no overlap, INDEPENDENT of hash rate. Returns [(start,end_inclusive)]."""
    base, rem = divmod(S, n)
    out = []
    start = 0
    for i in range(n):
        L = base + (1 if i < rem else 0)
        out.append((start, start + L - 1))
        start += L
    assert start == S
    return out


def allocate_weighted(S: int, shares: List[float]) -> List[Tuple[int, int]]:
    """Largest-remainder apportionment: S_i ~ S*w_i, Sum S_i = S exactly,
    deterministic tie-break by index. DEPENDS on hash-rate shares."""
    n = len(shares)
    raw = [S * w for w in shares]
    floors = [int(math.floor(x)) for x in raw]
    deficit = S - sum(floors)
    order = sorted(range(n), key=lambda i: (-(raw[i] - floors[i]), i))
    for k in range(deficit):
        floors[order[k]] += 1
    out = []
    start = 0
    for L in floors:
        L = max(L, 0)
        out.append((start, start + L - 1) if L > 0 else (start, start - 1))
        start += L
    assert start == S
    return out


# ---------------------------------------------------------------------------
# Config + result
# ---------------------------------------------------------------------------
@dataclass
class EngineConfig:
    scenario_id: str
    seed: int
    miner_count: int
    network_hash_rate_hps: float = 141e12
    efficiency_j_per_th: float = 21.5
    simulation_duration_s: float = 10000.0
    target_block_interval_s: float = 600.0
    mu: float = 2.0                         # expected solutions per template generation
    allocation_policy: str = "equal"        # "equal" | "weighted"
    hash_rate_distribution: str = "homogeneous"   # or "heterogeneous_moderate"/"heterogeneous_high"
    idle_power_ratio: float = 0.0
    inactive_miner_fraction: float = 0.0
    propagation_delay_mean_s: float = 0.42

    def p(self) -> float:
        return 1.0 / (self.network_hash_rate_hps * self.target_block_interval_s)

    def domain_size(self) -> int:
        # S chosen so p*S = mu
        return max(int(round(self.mu / self.p())), self.miner_count)


def _shares(cfg: EngineConfig) -> np.ndarray:
    n = cfg.miner_count
    if cfg.hash_rate_distribution == "homogeneous":
        return np.full(n, 1.0 / n)
    sigma = 1.0 if cfg.hash_rate_distribution == "heterogeneous_high" else 0.5
    x = rng(cfg.seed, "hash_rate_distribution").lognormal(0.0, sigma, n)
    return x / x.sum()


def run_scenario(cfg: EngineConfig, emit_log: bool = False) -> dict:
    n = cfg.miner_count
    S = cfg.domain_size()
    p = cfg.p()
    eff_j_per_hash = cfg.efficiency_j_per_th / HASHES_PER_TH
    shares = _shares(cfg)
    rates = shares * cfg.network_hash_rate_hps
    active_power_w = rates * eff_j_per_hash
    idle_power_w = cfg.idle_power_ratio * active_power_w

    # inactive miners (deterministic selection)
    n_inactive = int(round(cfg.inactive_miner_fraction * n))
    inactive = set(rng(cfg.seed, "inactive_selection").choice(n, n_inactive, replace=False).tolist()) \
        if n_inactive > 0 else set()
    active_ids = [i for i in range(n) if i not in inactive]
    H_active = float(sum(rates[i] for i in active_ids)) or 1.0

    # range allocation (decoupled from rate) over the ASSIGNED domain S
    if DISJOINT[cfg.scenario_id]:
        if cfg.allocation_policy == "weighted":
            ranges_all = allocate_weighted(S, list(shares))
        else:
            ranges_all = allocate_equal(S, n)
    else:
        ranges_all = [(0, S - 1)] * n     # common non-partitioned domain

    # per-miner accumulators
    active_t = np.zeros(n); idle_t = np.zeros(n); offline_t = np.zeros(n)
    searched = np.zeros(n, dtype=np.int64)
    inactive_count = sum((ranges_all[i][1] - ranges_all[i][0] + 1) for i in inactive) if DISJOINT[cfg.scenario_id] else 0

    # coordination counters (simulated)
    coord = dict(block_propagation_message_count=0, block_propagation_bytes=0,
                 template_refresh_count=0, nonce_allocation_event_count=0,
                 simulated_message_count=0, simulated_message_bytes=0)

    total_evals = 0.0; distinct_evals = 0.0; duplicate_evals = 0.0
    accepted = 0; exhausted_rounds = 0; legit_stales = 0
    r_solpos = rng(cfg.seed, "solution_positions")
    r_solk = rng(cfg.seed, "solution_count")
    r_starts = rng(cfg.seed, "miner_starts")
    r_delay = rng(cfg.seed, "propagation_delay")
    completion_times = []          # per-round per-miner nominal completion (for dispersion)
    block_log = [] if emit_log else None

    t = 0.0
    BIG = cfg.simulation_duration_s
    while t < BIG:
        # ---- one accepted block = possibly several exhausted template generations ----
        tgen = 0
        exhaust_time = 0.0
        while True:
            coord["nonce_allocation_event_count"] += 1
            k = int(r_solk.binomial(S, p))
            if k > 0:
                # unique solution positions
                pos = np.unique(r_solpos.integers(0, S, size=k * 2))[:k]
                if pos.size:
                    break
            exhausted_rounds += 1
            tgen += 1
            coord["template_refresh_count"] += 1
            exhaust_time += S / H_active           # full covered domain searched
            if tgen > MAX_REFRESH:
                pos = np.array([], dtype=np.int64)
                break

        # ---- discovery time per solution, per scenario ----
        # returns winner_time, winner_id, per-miner searched positions this round
        winner_time, winner_id, round_searched, round_total, round_distinct = _discover(
            cfg, pos, ranges_all, rates, active_ids, S, r_starts, H_active)
        # generation durations: tgen exhausted generations (full-domain search) + 1 success
        D_ex = S / H_active                        # exhausted-generation duration
        gen_success = winner_time
        round_dur = tgen * D_ex + gen_success
        if round_dur <= 0:
            round_dur = cfg.target_block_interval_s
        cap = BIG - t
        if round_dur > cap:                        # partial final round: scale generations
            scale = cap / round_dur
            D_ex *= scale; gen_success *= scale; round_dur = cap
        # ---- per-miner active/idle (per template generation) ----
        for i in range(n):
            if i in inactive:
                offline_t[i] += round_dur
                continue
            L_i = ranges_all[i][1] - ranges_all[i][0] + 1 if DISJOINT[cfg.scenario_id] else S
            tau_i = L_i / max(rates[i], 1e-12)     # nominal completion (decoupled from rate)
            completion_times.append(tau_i)
            if IDLE[cfg.scenario_id]:
                # active until its range completes within each generation; idle after
                a = tgen * min(tau_i, D_ex) + min(tau_i, gen_success)
                idl = tgen * max(0.0, D_ex - tau_i) + max(0.0, gen_success - tau_i)
                active_t[i] += a
                idle_t[i] += idl
            else:
                active_t[i] += round_dur            # continuous: refresh, always hashing
        # searched counts (approximate: covered positions this round)
        total_evals += round_total
        distinct_evals += round_distinct
        duplicate_evals += (round_total - round_distinct)

        accepted += 1
        # coordination: propagate the accepted block to the other miners
        msgs = len(active_ids) - 1 if active_ids else 0
        coord["block_propagation_message_count"] += max(msgs, 0)
        coord["block_propagation_bytes"] += max(msgs, 0) * 1_000_000   # 1 MB block (nominal)
        coord["simulated_message_count"] += max(msgs, 0)
        coord["simulated_message_bytes"] += max(msgs, 0) * 1_000_000
        # legitimate propagation stale: another finder within the delay window
        if len(pos) >= 2 and active_ids:
            second = float(np.partition(pos, 1)[1]) / max(rates[winner_id], 1e-12) if winner_id is not None else 0.0
            delay = float(r_delay.exponential(max(cfg.propagation_delay_mean_s, 1e-12)))
            if 0 < (second - winner_time) < delay:
                legit_stales += 1
        if emit_log:
            block_log.append(dict(
                block_index=accepted, t_start_s=t, round_duration_s=round_dur,
                winner_id=(int(winner_id) if winner_id is not None else None),
                winner_time_s=winner_time, solutions_found=int(len(pos)),
                exhausted_generations=tgen, round_total_evaluations=round_total,
                round_distinct_evaluations=round_distinct,
                propagation_messages=max(msgs, 0)))
        t += round_dur

    # ---- energy ----
    active_energy_kwh = float((active_power_w * active_t).sum()) / J_PER_KWH
    idle_energy_kwh = float((idle_power_w * idle_t).sum()) / J_PER_KWH
    coordination_energy_kwh = 0.0                  # excluded lower bound (idealized)
    total_energy_kwh = active_energy_kwh + idle_energy_kwh + coordination_energy_kwh

    dup_rate = (duplicate_evals / total_evals) if total_evals else 0.0
    comp = np.array(completion_times) if completion_times else np.array([0.0])
    result = dict(
        scenario_id=cfg.scenario_id, seed=cfg.seed, miners=n, domain_size=S, p=p, mu=cfg.mu,
        allocation_policy=cfg.allocation_policy, hash_rate_distribution=cfg.hash_rate_distribution,
        idle_power_ratio=cfg.idle_power_ratio, inactive_fraction=cfg.inactive_miner_fraction,
        # primary outcomes
        total_energy_kwh=total_energy_kwh, active_energy_kwh=active_energy_kwh,
        idle_energy_kwh=idle_energy_kwh, coordination_energy_kwh=coordination_energy_kwh,
        accepted_blocks=accepted, effective_block_interval_s=(BIG / accepted) if accepted else None,
        energy_per_accepted_block_kwh=(total_energy_kwh / accepted) if accepted else None,
        legitimate_stale_rate=(legit_stales / accepted) if accepted else 0.0,
        duplicate_evaluation_rate=dup_rate, exhausted_rounds=exhausted_rounds,
        # domain / coverage
        total_candidate_evaluations=total_evals, distinct_candidate_identities=distinct_evals,
        duplicate_evaluations=duplicate_evals,
        # time
        total_active_time_s=float(active_t.sum()), total_idle_time_s=float(idle_t.sum()),
        total_offline_time_s=float(offline_t.sum()),
        completion_time_mean_s=float(comp.mean()), completion_time_std_s=float(comp.std()),
        # coordination
        **{f"coord_{k}": v for k, v in coord.items()},
        # abstract (unimplemented) protocol activity: common-template scenarios need a
        # per-block agreement; B0 (independent templates) needs none.
        abstract_template_agreement_operations=(accepted if AGREEMENT[cfg.scenario_id] else 0),
        abstract_transaction_reconciliation_operations=(accepted if AGREEMENT[cfg.scenario_id] else 0),
        unimplemented_agreement_energy_kwh=None,             # NOT measured (null, not zero)
        coordination_energy_lower_bound_kwh=0.0,             # explicit idealized lower bound
        inactive_domain=inactive_count, common_template=COMMON_TEMPLATE[cfg.scenario_id],
        idle_policy=IDLE[cfg.scenario_id],
        # in-loop idle state-transition reasons (section 10.6)
        idle_enter_reason=("range_exhausted_no_solution" if IDLE[cfg.scenario_id] else None),
        idle_leave_reason=("new_template_generation_or_accepted_block" if IDLE[cfg.scenario_id] else None),
    )
    if emit_log:
        result["block_log"] = block_log
    return result


def _discover(cfg, pos, ranges_all, rates, active_ids, S, r_starts, H_active):
    """Return (winner_time, winner_id, per_round_searched, round_total, round_distinct)."""
    scen = cfg.scenario_id
    if len(pos) == 0:
        # exhausted with no winner in this generation: nominal full-domain search time
        return S / H_active, (active_ids[0] if active_ids else None), None, 0.0, 0.0
    if DISJOINT[scen]:
        # B0 (independent templates) and B3/C1/C2 (disjoint ranges) both achieve
        # full-parallel, non-redundant coverage -> same discovery physics here.
        # position lies in exactly one miner's range
        best_t = math.inf; best_id = None
        starts = {i: ranges_all[i][0] for i in range(len(rates))}
        for q in pos:
            owner = None
            for i in active_ids:
                a, b = ranges_all[i]
                if a <= q <= b:
                    owner = i; break
            if owner is None:
                continue
            tt = (q - starts[owner]) / max(rates[owner], 1e-12)
            if tt < best_t:
                best_t = tt; best_id = owner
        if best_id is None:
            return S / H_active, (active_ids[0] if active_ids else None), None, 0.0, 0.0
        total = best_t * float(sum(rates[i] for i in active_ids))     # continuous parallel search
        distinct = total                                             # disjoint -> no duplicates
        return best_t, best_id, None, total, distinct
    if scen == "B1":
        # all from 0; fastest miner reaches lowest position first
        rmax = max(rates[i] for i in active_ids); wid = active_ids[int(np.argmax([rates[i] for i in active_ids]))]
        winner_time = float(pos.min()) / rmax
        total = winner_time * float(sum(rates[i] for i in active_ids))
        distinct = winner_time * rmax                # only the fastest miner's coverage is distinct
        return winner_time, wid, None, total, distinct
    if scen == "B2":
        # random starts, forward with wraparound-stop after one traversal
        starts = {i: int(r_starts.integers(0, S)) for i in active_ids}
        best_t = math.inf; best_id = None
        for q in pos:
            for i in active_ids:
                d = (q - starts[i]) % S
                tt = d / max(rates[i], 1e-12)
                if tt < best_t:
                    best_t = tt; best_id = i
        winner_time = best_t
        # coverage = union of per-miner paths [start_i, start_i + rate_i*winner_time)
        covered = 0.0; intervals = []
        for i in active_ids:
            L = min(rates[i] * winner_time, S)
            intervals.append((starts[i], starts[i] + L))
        # merge on a circle approximated linearly (validated on small domains)
        intervals.sort()
        cur_s, cur_e = intervals[0]
        merged = 0.0
        for s, e in intervals[1:]:
            if s <= cur_e:
                cur_e = max(cur_e, e)
            else:
                merged += cur_e - cur_s; cur_s, cur_e = s, e
        merged += cur_e - cur_s
        distinct = min(merged, float(S))
        total = winner_time * float(sum(rates[i] for i in active_ids))
        return winner_time, best_id, None, total, distinct
    # fallback
    return S / H_active, active_ids[0], None, 0.0, 0.0
