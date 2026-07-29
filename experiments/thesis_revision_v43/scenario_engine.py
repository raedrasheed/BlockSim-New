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

from experiments.thesis_revision_v43 import coverage as _cov
from experiments.thesis_revision_v43 import exact_sampling as _exact
from experiments.thesis_revision_v43.schemas import OUTPUT_SCHEMA_VERSION

ENGINE_VERSION = "5b1e.1"

J_PER_KWH = 3_600_000.0
HASHES_PER_TH = 1e12
SCENARIOS = ["B0", "B1", "B2", "B3_C1_CONTINUOUS_DISJOINT", "C2"]

# nominal message sizes (bytes). Block size is configured; control-message sizes
# are declared UNKNOWN (None) so control bytes are never fabricated (Section 10).
DEFAULT_BLOCK_SIZE_BYTES = 1_000_000
CONTROL_MESSAGE_SIZE_BYTES = None      # explicitly not configured -> bytes = null
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
    deterministic tie-break by index. DEPENDS on hash-rate shares. Robust to
    float share-sum rounding (deficit of EITHER sign): a positive deficit adds 1
    to the largest fractional remainders; a negative deficit (floors overshoot S
    because sum(shares) rounded above 1) removes 1 from the smallest remainders
    among positive floors, so Sum S_i == S exactly for any float shares."""
    n = len(shares)
    raw = [S * w for w in shares]
    floors = [int(math.floor(x)) for x in raw]
    rem = [raw[i] - floors[i] for i in range(n)]
    diff = S - sum(floors)
    if diff > 0:
        order = sorted(range(n), key=lambda i: (-rem[i], i))   # largest remainder first
        for k in range(diff):
            floors[order[k % n]] += 1
    elif diff < 0:
        order = sorted(range(n), key=lambda i: (rem[i], i))    # smallest remainder first
        need, k = -diff, 0
        while need > 0:
            i = order[k % n]
            if floors[i] > 0:
                floors[i] -= 1
                need -= 1
            k += 1
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
    block_size_bytes: int = DEFAULT_BLOCK_SIZE_BYTES     # configured block-propagation size

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



import bisect

STATUS_FOUND = "FOUND_ACTIVE_SOLUTION"
STATUS_EXHAUSTED = "ACTIVE_DOMAIN_EXHAUSTED"
STATUS_NO_ACTIVE = "NO_ACTIVE_MINERS"
STATUS_PARTIAL = "PARTIAL_AT_CUTOFF"


class _Accum:
    """Shared per-run accumulators. Candidate counts are Python ints (exact, no
    float cast); times/energy are floats."""
    def __init__(self, n):
        self.active_t = np.zeros(n)              # active-power time (energy)
        self.idle_t = np.zeros(n)
        self.offline_t = np.zeros(n)
        self.productive_t = np.zeros(n)          # time actually spent evaluating candidates
        self.searched_cum = [0] * n              # cumulative candidates evaluated (int)
        self.last_pos = [None] * n
        self.stop_reason = [None] * n
        self.m_gen = np.zeros(n, dtype=np.int64)
        self.m_exhaust = np.zeros(n, dtype=np.int64)
        self.m_idle = np.zeros(n, dtype=np.int64)
        self.total_evals = 0                     # int
        self.distinct_evals = 0                  # int
        self.duplicate_evals = 0                 # int
        self.total_sol = 0                       # int: solutions across all templates
        self.active_sol = 0
        self.inactive_sol = 0
        self.accepted = 0
        self.exhausted = 0
        self.legit = 0
        self.partials = 0
        self.template_refresh = 0
        self.nonce_alloc = 0
        self.gen_counter = 0
        self.completion_times = []
        self.per_template = None
        self.block_log = None
        self.last_block_id = "genesis"
        self.coord = {c: dict(message_count=0, bytes=0 if c == "block_propagation" else None)
                      for c in ("block_propagation", "transaction_reconciliation",
                                "template_announcement", "nonce_allocation", "registration")}


def _owner_fn(ranges_all, n):
    nonempty = [(ranges_all[i][0], ranges_all[i][1], i) for i in range(n)
                if ranges_all[i][1] >= ranges_all[i][0]]
    starts = [a for a, b, i in nonempty]

    def owner(q):
        j = bisect.bisect_right(starts, q) - 1
        if 0 <= j < len(nonempty):
            a, b, i = nonempty[j]
            if a <= q <= b:
                return i
        return None
    return owner


def run_scenario(cfg: EngineConfig, emit_log: bool = False, emit_detail: bool = False) -> dict:
    n = cfg.miner_count
    S = int(cfg.domain_size())
    p = cfg.p()
    eff_j_per_hash = cfg.efficiency_j_per_th / HASHES_PER_TH
    shares = _shares(cfg)
    rates = shares * cfg.network_hash_rate_hps
    active_power_w = rates * eff_j_per_hash
    idle_power_w = cfg.idle_power_ratio * active_power_w

    n_inactive = int(round(cfg.inactive_miner_fraction * n))
    inactive = set(rng(cfg.seed, "inactive_selection").choice(n, n_inactive, replace=False).tolist()) \
        if n_inactive > 0 else set()
    active_ids = [i for i in range(n) if i not in inactive]

    if DISJOINT[cfg.scenario_id]:
        ranges_all = (allocate_weighted(S, list(shares)) if cfg.allocation_policy == "weighted"
                      else allocate_equal(S, n))
    else:
        ranges_all = [(0, S - 1)] * n

    acc = _Accum(n)
    acc.per_template = [] if emit_detail else None
    acc.block_log = [] if emit_log else None
    BIG = cfg.simulation_duration_s

    if DISJOINT[cfg.scenario_id]:
        _sim_disjoint(cfg, n, S, p, rates, active_ids, inactive, ranges_all, BIG,
                      emit_log, emit_detail, acc)
    else:
        _sim_frontier(cfg, n, S, p, rates, active_ids, inactive, BIG,
                      emit_log, emit_detail, acc)

    return _build_result(cfg, n, S, p, rates, shares, ranges_all, active_ids, inactive,
                         active_power_w, idle_power_w, BIG, acc, emit_log, emit_detail)


# ---------------------------------------------------------------------------
# Exact disjoint-range simulation (B0, B3/C1, C2)
# ---------------------------------------------------------------------------
def _sim_disjoint(cfg, n, S, p, rates, active_ids, inactive, ranges_all, BIG,
                  emit_log, emit_detail, acc):
    scen = cfg.scenario_id
    is_c2 = IDLE[scen]
    owner = _owner_fn(ranges_all, n)
    active_set = set(active_ids)
    S_i = [ranges_all[i][1] - ranges_all[i][0] + 1 for i in range(n)]
    inactive_count = sum(S_i[i] for i in inactive)
    # exhausted-generation duration = slowest ACTIVE assigned range (Section 2)
    D_ex = max((S_i[i] / rates[i] for i in active_ids), default=cfg.target_block_interval_s)
    r_solk = rng(cfg.seed, "solution_count")
    r_solpos = rng(cfg.seed, "solution_positions")
    r_delay = rng(cfg.seed, "propagation_delay")

    t = 0.0
    while t < BIG:
        acc.gen_counter += 1
        acc.nonce_alloc += 1
        remaining = BIG - t
        k = int(r_solk.binomial(S, p))
        if k > 0:
            pos = _exact.sample_without_replacement(r_solpos, S, k)
            if pos.size != k or np.unique(pos).size != k:
                raise RuntimeError(f"sampler invariant: k={k} len={pos.size}")
        else:
            pos = np.empty(0, dtype=np.int64)
        acc.total_sol += k

        act_sols = []              # (discovery_time, owner, q)
        n_inact_sol = 0
        for q in pos.tolist():
            ow = owner(q)
            if ow is None:
                continue
            if ow in active_set:
                act_sols.append(((q - ranges_all[ow][0] + 1) / rates[ow], ow, q))
            else:
                n_inact_sol += 1
        acc.active_sol += len(act_sols)
        acc.inactive_sol += n_inact_sol

        if not active_ids:
            status, t_end, winner, q_win = STATUS_NO_ACTIVE, D_ex, None, None
        elif act_sols:
            act_sols.sort()
            t_end, winner, q_win = act_sols[0]
            status = STATUS_FOUND
        else:
            status, t_end, winner, q_win = STATUS_EXHAUSTED, D_ex, None, None

        completed = t_end <= remaining + 1e-9
        eff_end = t_end if completed else remaining
        final_status = status if completed else STATUS_PARTIAL

        gen_searched = 0
        for i in active_ids:
            acc.m_gen[i] += 1
            if status == STATUS_FOUND and i == winner and completed:
                c_i = q_win - ranges_all[i][0] + 1                      # exact integer
            else:
                c_i = min(S_i[i], int(math.floor(rates[i] * eff_end)))
            acc.searched_cum[i] += c_i
            gen_searched += c_i
            acc.last_pos[i] = int(ranges_all[i][0] + c_i - 1) if c_i > 0 else None
            prod_time = c_i / rates[i]
            acc.productive_t[i] += prod_time
            acc.completion_times.append(S_i[i] / rates[i])
            if is_c2:
                acc.active_t[i] += prod_time
                idl = eff_end - prod_time
                if idl > 1e-12:
                    acc.idle_t[i] += idl
                    acc.m_idle[i] += 1
            else:
                acc.active_t[i] += eff_end                              # continuous power
            # stop reason (Section 4)
            if status == STATUS_FOUND and i == winner and completed:
                acc.stop_reason[i] = "solution_found"
            elif not completed:
                acc.stop_reason[i] = "simulation_cutoff"
            elif c_i >= S_i[i]:
                acc.stop_reason[i] = "range_exhausted"
                acc.m_exhaust[i] += 1
            else:
                acc.stop_reason[i] = "template_refreshed"
        for i in inactive:
            acc.offline_t[i] += eff_end
            acc.stop_reason[i] = "inactive"

        # disjoint -> distinct == total, duplicate == 0 (exact integers)
        acc.total_evals += gen_searched
        acc.distinct_evals += gen_searched

        legit = 0
        block_id = None
        if completed and status == STATUS_FOUND:
            acc.accepted += 1
            block_id = f"blk-{acc.accepted}"
            msgs = max(len(active_ids) - 1, 0)
            acc.coord["block_propagation"]["message_count"] += msgs
            acc.coord["block_propagation"]["bytes"] += msgs * cfg.block_size_bytes
            if len(act_sols) >= 2:
                second_dt = act_sols[1][0]
                delay = float(r_delay.exponential(max(cfg.propagation_delay_mean_s, 1e-12)))
                if 0 < (second_dt - t_end) < delay:
                    acc.legit += 1
                    legit = 1
            acc.last_block_id = block_id
            refresh_cause = "accepted_block"
        elif completed:
            acc.exhausted += 1
            acc.template_refresh += 1
            refresh_cause = "active_domain_exhausted" if status == STATUS_EXHAUSTED else "no_active_miners"
        else:
            acc.partials += 1
            refresh_cause = "simulation_cutoff"

        if emit_detail:
            active_completion = D_ex if status != STATUS_FOUND else None
            acc.per_template.append(dict(
                run_id=None, round_id=acc.accepted, template_generation_id=acc.gen_counter,
                parent_block_id=acc.last_block_id, template_id=f"tmpl-{acc.gen_counter}",
                target=p, mu=cfg.mu, assigned_domain_size=S,
                searched_domain_size=gen_searched, inactive_domain_size=inactive_count,
                unsearched_domain_size=S - gen_searched - inactive_count,
                total_template_solution_count=k, active_range_solution_count=len(act_sols),
                inactive_range_solution_count=n_inact_sol, discoverable_finder_count=len(act_sols),
                solution_count=k, finder_count=(1 + legit if block_id else 0),
                accepted_block_id=block_id, exhausted=(status != STATUS_FOUND),
                status=final_status, refresh_cause=refresh_cause,
                start_time_s=t, end_time_s=t + eff_end, duration_s=eff_end,
                exhausted_time_s=(eff_end if status == STATUS_EXHAUSTED else 0.0),
                active_domain_completion_time_s=active_completion,
                partial_cutoff_time_s=(eff_end if not completed else None),
                legitimate_competitor_count=legit, obsolete_event_rejection_count=0))
        if emit_log and block_id:
            acc.block_log.append(dict(
                block_index=acc.accepted, t_start_s=t, duration_s=eff_end,
                winner_id=int(winner), winner_time_s=t_end, solutions_found=k,
                active_solutions=len(act_sols), inactive_solutions=n_inact_sol,
                propagation_messages=max(len(active_ids) - 1, 0)))
        t += eff_end
        if not completed:
            break


# ---------------------------------------------------------------------------
# Frontier simulation (B1 common-from-zero, B2 seeded random starts)
# ---------------------------------------------------------------------------
def _sim_frontier(cfg, n, S, p, rates, active_ids, inactive, BIG, emit_log, emit_detail, acc):
    scen = cfg.scenario_id
    unique_rate = (float(max((rates[i] for i in active_ids), default=1.0)) if scen == "B1"
                   else float(sum(rates[i] for i in active_ids)) or 1.0)
    D_ex = S / (unique_rate or 1.0)
    r_solk = rng(cfg.seed, "solution_count")
    r_solpos = rng(cfg.seed, "solution_positions")
    r_starts = rng(cfg.seed, "miner_starts")
    r_delay = rng(cfg.seed, "propagation_delay")
    max_rate = float(max((rates[i] for i in active_ids), default=1.0))

    t = 0.0
    while t < BIG:
        acc.gen_counter += 1
        acc.nonce_alloc += 1
        remaining = BIG - t
        k = int(r_solk.binomial(S, p))
        if k > 0:
            pos = _exact.sample_without_replacement(r_solpos, S, k)
        else:
            pos = np.empty(0, dtype=np.int64)
        acc.total_sol += k

        rates_list = [float(rates[i]) for i in active_ids]
        starts_list = ([int(r_starts.integers(0, S)) for _ in active_ids]
                       if scen == "B2" else None)
        if not active_ids:
            status, t_end, winner = STATUS_NO_ACTIVE, D_ex, None
        elif k == 0:
            status, t_end, winner = STATUS_EXHAUSTED, D_ex, None
        elif scen == "B1":
            winner = active_ids[int(np.argmax([rates[i] for i in active_ids]))]
            t_end = float(pos.min() + 1) / max_rate
            status = STATUS_FOUND
        else:  # B2
            wt, widx = _cov.b2_winner(pos, starts_list, rates_list, S)
            if widx is None or not math.isfinite(wt):
                status, t_end, winner = STATUS_EXHAUSTED, D_ex, None
            else:
                winner, t_end, status = active_ids[widx], wt, STATUS_FOUND

        completed = t_end <= remaining + 1e-9
        eff_end = t_end if completed else remaining
        final_status = status if completed else STATUS_PARTIAL

        # per-miner integer candidate counts
        gen_total = 0
        for i in active_ids:
            acc.m_gen[i] += 1
            c_i = min(S, int(math.floor(rates[i] * eff_end)))
            acc.searched_cum[i] += c_i
            gen_total += c_i
            acc.last_pos[i] = int(c_i - 1) if c_i > 0 else None
            acc.productive_t[i] += c_i / rates[i]
            acc.active_t[i] += eff_end                    # continuous power
            acc.completion_times.append(S / rates[i])
            acc.stop_reason[i] = ("solution_found" if (status == STATUS_FOUND and i == winner and completed)
                                  else "simulation_cutoff" if not completed
                                  else "template_refreshed" if status == STATUS_FOUND
                                  else "range_exhausted")
            if status == STATUS_EXHAUSTED and completed:
                acc.m_exhaust[i] += 1
        for i in inactive:
            acc.offline_t[i] += eff_end
            acc.stop_reason[i] = "inactive"

        # distinct coverage (uniform across status): B1 miners all start at 0 so they
        # overlap (distinct = fastest coverage); B2 uses the exact circular union.
        if not active_ids:
            gen_distinct = 0
        elif scen == "B1":
            gen_distinct = min(S, int(math.floor(max_rate * eff_end)))
        else:  # B2 exact circular union over the swept arcs
            lengths = _cov.lengths_from_winner_time(eff_end, rates_list, S)
            covx = _cov.b2_coverage_exact(starts_list, lengths, S)
            gen_total = int(covx["total_candidate_evaluations"])
            gen_distinct = int(covx["distinct_candidate_evaluations"])

        acc.total_evals += gen_total
        acc.distinct_evals += gen_distinct
        acc.duplicate_evals += (gen_total - gen_distinct)

        legit = 0
        block_id = None
        if completed and status == STATUS_FOUND:
            acc.accepted += 1
            block_id = f"blk-{acc.accepted}"
            msgs = max(len(active_ids) - 1, 0)
            acc.coord["block_propagation"]["message_count"] += msgs
            acc.coord["block_propagation"]["bytes"] += msgs * cfg.block_size_bytes
            if len(pos) >= 2:
                second = float(np.partition(pos, 1)[1] + 1) / max_rate
                delay = float(r_delay.exponential(max(cfg.propagation_delay_mean_s, 1e-12)))
                if 0 < (second - t_end) < delay:
                    acc.legit += 1
                    legit = 1
            acc.last_block_id = block_id
            refresh_cause = "accepted_block"
        elif completed:
            acc.exhausted += 1
            acc.template_refresh += 1
            refresh_cause = "active_domain_exhausted"
        else:
            acc.partials += 1
            refresh_cause = "simulation_cutoff"

        if emit_detail:
            acc.per_template.append(dict(
                run_id=None, round_id=acc.accepted, template_generation_id=acc.gen_counter,
                parent_block_id=acc.last_block_id, template_id=f"tmpl-{acc.gen_counter}",
                target=p, mu=cfg.mu, assigned_domain_size=S,
                searched_domain_size=min(S, gen_distinct), inactive_domain_size=0,
                unsearched_domain_size=S - min(S, gen_distinct),
                total_template_solution_count=k, active_range_solution_count=k,
                inactive_range_solution_count=0, discoverable_finder_count=k,
                solution_count=k, finder_count=(1 + legit if block_id else 0),
                accepted_block_id=block_id, exhausted=(status != STATUS_FOUND),
                status=final_status, refresh_cause=refresh_cause,
                start_time_s=t, end_time_s=t + eff_end, duration_s=eff_end,
                exhausted_time_s=(eff_end if status == STATUS_EXHAUSTED else 0.0),
                active_domain_completion_time_s=(D_ex if status == STATUS_EXHAUSTED else None),
                partial_cutoff_time_s=(eff_end if not completed else None),
                legitimate_competitor_count=legit, obsolete_event_rejection_count=0))
        if emit_log and block_id:
            acc.block_log.append(dict(
                block_index=acc.accepted, t_start_s=t, duration_s=eff_end,
                winner_id=int(winner), winner_time_s=t_end, solutions_found=k,
                propagation_messages=max(len(active_ids) - 1, 0)))
        t += eff_end
        if not completed:
            break


# ---------------------------------------------------------------------------
# Result construction
# ---------------------------------------------------------------------------
def _build_result(cfg, n, S, p, rates, shares, ranges_all, active_ids, inactive,
                  active_power_w, idle_power_w, BIG, acc, emit_log, emit_detail):
    scen = cfg.scenario_id
    active_energy_kwh = float((active_power_w * acc.active_t).sum()) / J_PER_KWH
    idle_energy_kwh = float((idle_power_w * acc.idle_t).sum()) / J_PER_KWH
    coordination_energy_kwh = 0.0
    total_energy_kwh = active_energy_kwh + idle_energy_kwh + coordination_energy_kwh

    # candidate-count reconciliation is EXACT integer arithmetic
    assert acc.total_evals == acc.distinct_evals + acc.duplicate_evals
    dup_rate = (acc.duplicate_evals / acc.total_evals) if acc.total_evals else 0.0
    comp = np.array(acc.completion_times) if acc.completion_times else np.array([0.0])
    inactive_count = sum((ranges_all[i][1] - ranges_all[i][0] + 1) for i in inactive) \
        if DISJOINT[scen] else 0

    n_gen = acc.gen_counter
    acc.coord["nonce_allocation"]["message_count"] = n_gen if DISJOINT[scen] else 0
    acc.coord["template_announcement"]["message_count"] = n_gen if COMMON_TEMPLATE[scen] else 0
    acc.coord["transaction_reconciliation"]["message_count"] = acc.accepted if AGREEMENT[scen] else 0
    acc.coord["registration"]["message_count"] = len(active_ids) if COMMON_TEMPLATE[scen] else 0
    cat_flat = {}
    for c, v in acc.coord.items():
        cat_flat[f"{c}_message_count"] = v["message_count"]
        cat_flat[f"{c}_bytes"] = v["bytes"]

    has_blocks = acc.accepted > 0
    block_na = None if has_blocks else "no_accepted_blocks"
    non_productive_active = float((acc.active_t - acc.productive_t).clip(min=0).sum())

    result = dict(
        output_schema_version=OUTPUT_SCHEMA_VERSION, engine_version=ENGINE_VERSION,
        scenario_id=scen, seed=cfg.seed, miners=n, domain_size=S, p=p, mu=cfg.mu,
        allocation_policy=cfg.allocation_policy, hash_rate_distribution=cfg.hash_rate_distribution,
        idle_power_ratio=cfg.idle_power_ratio, inactive_fraction=cfg.inactive_miner_fraction,
        total_energy_kwh=total_energy_kwh, active_energy_kwh=active_energy_kwh,
        idle_energy_kwh=idle_energy_kwh, coordination_energy_kwh=coordination_energy_kwh,
        accepted_blocks=acc.accepted, block_metrics_defined=has_blocks,
        effective_block_interval_s=((BIG / acc.accepted) if has_blocks else None),
        effective_block_interval_na_reason=block_na,
        energy_per_accepted_block_kwh=((total_energy_kwh / acc.accepted) if has_blocks else None),
        energy_per_accepted_block_na_reason=block_na,
        throughput_blocks_per_s=(acc.accepted / BIG if BIG else 0.0),
        energy_per_transaction_kwh=None,
        energy_per_transaction_na_reason="no_committed_transactions",
        confirmation_time_proxy_s=((BIG / acc.accepted) if has_blocks else None),
        confirmation_time_proxy_na_reason=block_na,
        legitimate_stale_rate=((acc.legit / acc.accepted) if has_blocks else None),
        legitimate_stale_rate_na_reason=(None if has_blocks else "no_valid_proposals"),
        legitimate_stale_count=acc.legit,
        duplicate_evaluation_rate=dup_rate, exhausted_rounds=acc.exhausted,
        partial_generations=acc.partials,
        # EXACT integer candidate counts (Python ints)
        total_candidate_evaluations=acc.total_evals,
        distinct_candidate_identities=acc.distinct_evals,
        duplicate_evaluations=acc.duplicate_evals,
        # solution accounting (Section 1.6)
        total_template_solution_count=acc.total_sol,
        active_range_solution_count=acc.active_sol,
        inactive_range_solution_count=acc.inactive_sol,
        discoverable_finder_count=acc.active_sol,
        # time
        total_active_time_s=float(acc.active_t.sum()), total_idle_time_s=float(acc.idle_t.sum()),
        total_offline_time_s=float(acc.offline_t.sum()),
        total_productive_search_time_s=float(acc.productive_t.sum()),
        non_productive_active_time_s=non_productive_active,
        completion_time_mean_s=float(comp.mean()), completion_time_std_s=float(comp.std()),
        template_generations=n_gen,
        coord_block_propagation_message_count=acc.coord["block_propagation"]["message_count"],
        coord_block_propagation_bytes=acc.coord["block_propagation"]["bytes"],
        coord_simulated_message_count=acc.coord["block_propagation"]["message_count"],
        coord_simulated_message_bytes=acc.coord["block_propagation"]["bytes"],
        coord_template_refresh_count=acc.template_refresh,
        coord_nonce_allocation_event_count=acc.nonce_alloc,
        **cat_flat,
        abstract_template_agreement_operations=(acc.accepted if AGREEMENT[scen] else 0),
        abstract_transaction_reconciliation_operations=(acc.accepted if AGREEMENT[scen] else 0),
        unimplemented_agreement_energy_kwh=None,
        coordination_energy_lower_bound_kwh=0.0,
        inactive_domain=inactive_count, common_template=COMMON_TEMPLATE[scen],
        idle_policy=IDLE[scen],
        idle_enter_reason=("range_exhausted_no_solution" if IDLE[scen] else None),
        idle_leave_reason=("new_template_generation_or_accepted_block" if IDLE[scen] else None),
    )
    if emit_log:
        result["block_log"] = acc.block_log
    if emit_detail:
        result["per_miner"] = _build_per_miner(cfg, n, rates, shares, ranges_all, inactive,
                                               active_power_w, idle_power_w, acc, S)
        result["per_template"] = acc.per_template
    return result


def _build_per_miner(cfg, n, rates, shares, ranges_all, inactive, active_power_w,
                     idle_power_w, acc, S):
    disjoint = DISJOINT[cfg.scenario_id]
    out = []
    for i in range(n):
        a, b = ranges_all[i]
        L_i = (b - a + 1) if disjoint else int(S)
        is_inactive = i in inactive
        searched = 0 if is_inactive else int(acc.searched_cum[i])
        inactive_cand = L_i if (is_inactive and disjoint) else 0
        # generation-level remaining is per-template; the cumulative here reflects total work
        remaining_unsearched = (0 if is_inactive else max(0, L_i - (searched % L_i if L_i else 0))) \
            if disjoint else None
        state = "offline" if is_inactive else ("idled" if acc.m_idle[i] > 0 else "active")
        reasons = {}
        if acc.m_exhaust[i]:
            reasons["range_exhausted"] = int(acc.m_exhaust[i])
        if acc.m_idle[i]:
            reasons["entered_idle"] = int(acc.m_idle[i])
        out.append(dict(
            run_id=None, miner_id=i, hash_rate_hps=float(rates[i]),
            hash_rate_share=float(shares[i]), allocation_policy=cfg.allocation_policy,
            range_start=int(a), range_end=int(b), range_size=int(L_i) if disjoint else None,
            search_start_position=int(a) if disjoint else 0,
            candidates_evaluated=searched,
            searched_count=searched,
            last_evaluated_position=acc.last_pos[i],
            unsearched_count=(int(L_i - min(searched, L_i)) if disjoint else None),
            remaining_unsearched=remaining_unsearched,
            inactive_count=inactive_cand,
            active_time_s=float(acc.active_t[i]), idle_time_s=float(acc.idle_t[i]),
            offline_time_s=float(acc.offline_t[i]),
            productive_search_time_s=float(acc.productive_t[i]),
            active_energy_kwh=float(active_power_w[i] * acc.active_t[i]) / J_PER_KWH,
            idle_energy_kwh=float(idle_power_w[i] * acc.idle_t[i]) / J_PER_KWH,
            template_generations_participated=int(acc.m_gen[i]),
            range_exhaustion_count=int(acc.m_exhaust[i]),
            idle_entry_count=int(acc.m_idle[i]), final_state=state,
            completion_status=(acc.stop_reason[i] or "inactive"),
            stop_reason=(acc.stop_reason[i] or "inactive"),
            state_transition_reason_counts=reasons))
    return out
