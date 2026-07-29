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

ENGINE_VERSION = "5b1f.1"

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
from fractions import Fraction

from experiments.thesis_revision_v43 import coverage as _cov

STATUS_FOUND = "FOUND_ACTIVE_SOLUTION"
STATUS_EXHAUSTED = "ACTIVE_DOMAIN_EXHAUSTED"
STATUS_NO_ACTIVE = "NO_ACTIVE_MINERS"
STATUS_PARTIAL = "PARTIAL_AT_CUTOFF"


def apportion_int(total: int, weights):
    """Largest-remainder apportionment of an integer `total` over `weights`; the
    returned integer parts sum EXACTLY to total. Used to give each miner an integer
    hash rate summing to the integer network hash rate (Section 7)."""
    n = len(weights)
    w = [max(float(x), 0.0) for x in weights]
    sw = sum(w) or 1.0
    raw = [total * x / sw for x in w]
    floors = [int(math.floor(x)) for x in raw]
    rem = [raw[i] - floors[i] for i in range(n)]
    diff = total - sum(floors)
    if diff > 0:
        order = sorted(range(n), key=lambda i: (-rem[i], i))
        for k in range(diff):
            floors[order[k % n]] += 1
    elif diff < 0:
        order = sorted(range(n), key=lambda i: (rem[i], i))
        need, k = -diff, 0
        while need > 0:
            i = order[k % n]
            if floors[i] > 0:
                floors[i] -= 1
                need -= 1
            k += 1
    assert sum(floors) == total
    return floors


def _completed(rate_int: int, t: Fraction, cap: int) -> int:
    """Candidates completed by a miner of integer rate by rational time t (unified
    convention: completed = floor(rate*t)), capped at `cap`. Exact integer."""
    if t <= 0:
        return 0
    c = (rate_int * t.numerator) // t.denominator
    return int(min(cap, c))


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


class _Accum:
    def __init__(self, n):
        self.active_t = [Fraction(0)] * n
        self.idle_t = [Fraction(0)] * n
        self.offline_t = [Fraction(0)] * n
        self.productive_t = [Fraction(0)] * n
        self.searched_cum = [0] * n
        self.last_pos = [None] * n
        self.stop_reason = [None] * n
        self.m_gen = [0] * n
        self.m_exhaust = [0] * n
        self.m_idle = [0] * n
        self.total_evals = 0
        self.distinct_evals = 0
        self.duplicate_evals = 0
        self.total_sol = 0
        self.active_sol = 0
        self.inactive_sol = 0
        self.accepted = 0
        self.exhausted = 0
        self.partials = 0
        self.stale_blocks = 0
        self.competitor_miners = 0
        self.proposal_miners = 0
        self.potential_finders = 0
        self.template_refresh = 0
        self.nonce_alloc = 0
        self.gen_counter = 0
        self.completion_times = []
        self.per_template = None
        self.block_log = None
        self.gen_rows = None
        self.last_accepted_block_id = "genesis"
        self.coord = {c: dict(message_count=0, bytes=0 if c == "block_propagation" else None)
                      for c in ("block_propagation", "transaction_reconciliation",
                                "template_announcement", "nonce_allocation", "registration")}


def run_scenario(cfg: EngineConfig, emit_log: bool = False, emit_detail: bool = False,
                 emit_generation_detail: bool = False) -> dict:
    n = cfg.miner_count
    S = int(cfg.domain_size())
    p = cfg.p()
    eff_j_per_hash = cfg.efficiency_j_per_th / HASHES_PER_TH
    shares = _shares(cfg)
    # INTEGER per-miner hash rates summing EXACTLY to the integer network rate
    H_net_int = int(round(cfg.network_hash_rate_hps))
    rates_int = apportion_int(H_net_int, list(shares))
    rates = np.array(rates_int, dtype=float)
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
    acc.gen_rows = [] if emit_generation_detail else None
    BIG = Fraction(int(round(cfg.simulation_duration_s)))

    if DISJOINT[cfg.scenario_id]:
        _sim_disjoint(cfg, n, S, p, rates_int, active_ids, inactive, ranges_all, BIG, acc)
    else:
        _sim_frontier(cfg, n, S, p, rates_int, active_ids, inactive, BIG, acc)

    return _build_result(cfg, n, S, p, rates, rates_int, shares, ranges_all, active_ids,
                         inactive, active_power_w, idle_power_w, float(BIG), acc,
                         emit_log, emit_detail, emit_generation_detail)


def _draw_delays(r_delay, mean_s, count):
    return [Fraction(str(round(float(r_delay.exponential(max(mean_s, 1e-12))), 9)))
            for _ in range(count)]


def _resolve(discoveries, delays):
    """discoveries: list of dict(miner, offset, q, identity, time). Returns
    (winner, proposal_miners, competitor_miners, stale_blocks). A competitor is a
    distinct miner with a DISTINCT candidate identity; a legitimate stale also
    satisfies time_j < winner_time + per-miner delay_j."""
    if not discoveries:
        return None, 0, 0, 0
    discoveries.sort(key=lambda d: (d["time"], d["miner"]))
    winner = discoveries[0]
    proposal = len(discoveries)
    competitors = [d for d in discoveries[1:]
                   if d["miner"] != winner["miner"] and d["identity"] != winner["identity"]]
    comp_miners = len({d["miner"] for d in competitors})
    stale = 0
    for d, delay in zip(competitors, delays):
        if d["time"] < winner["time"] + delay:
            stale += 1
    return winner, proposal, comp_miners, stale


def _sim_disjoint(cfg, n, S, p, rates_int, active_ids, inactive, ranges_all, BIG, acc):
    scen = cfg.scenario_id
    is_c2 = IDLE[scen]
    is_b0 = (scen == "B0")
    owner = _owner_fn(ranges_all, n)
    active_set = set(active_ids)
    S_i = [ranges_all[i][1] - ranges_all[i][0] + 1 for i in range(n)]
    inactive_count = sum(S_i[i] for i in inactive)
    slow = max(active_ids, key=lambda i: Fraction(S_i[i], rates_int[i])) if active_ids else None
    D_ex = Fraction(S_i[slow], rates_int[slow]) if slow is not None else Fraction(int(cfg.target_block_interval_s))
    r_solk = rng(cfg.seed, "solution_count")
    r_solpos = rng(cfg.seed, "solution_positions")
    r_delay = rng(cfg.seed, "propagation_delay")

    t = Fraction(0)
    while t < BIG:
        acc.gen_counter += 1
        acc.nonce_alloc += 1
        parent_before = acc.last_accepted_block_id
        remaining = BIG - t
        k = int(r_solk.binomial(S, p))
        if k > 0:
            pos = _exact.sample_without_replacement(r_solpos, S, k)
            if pos.size != k:
                raise RuntimeError("sampler invariant")
        else:
            pos = np.empty(0, dtype=np.int64)
        acc.total_sol += k

        # per-miner earliest discovery (one proposal per miner = earliest solution)
        best = {}
        n_inact_sol = 0
        for q in pos.tolist():
            ow = owner(q)
            if ow is None:
                continue
            if ow in active_set:
                d = q - ranges_all[ow][0]
                if ow not in best or d < best[ow][0]:
                    best[ow] = (d, q)
            else:
                n_inact_sol += 1
        discoveries = [dict(miner=i, offset=d, q=q,
                            identity=((i, q) if is_b0 else q),
                            time=Fraction(d + 1, rates_int[i]))
                       for i, (d, q) in best.items()]
        acc.active_sol += len(discoveries)
        acc.inactive_sol += n_inact_sol
        acc.potential_finders += len(discoveries)

        if not active_ids:
            status, t_end, winner = STATUS_NO_ACTIVE, D_ex, None
        elif discoveries:
            delays = _draw_delays(r_delay, cfg.propagation_delay_mean_s, max(len(discoveries) - 1, 0))
            winner, proposal, comp, stale = _resolve(discoveries, delays)
            status, t_end = STATUS_FOUND, winner["time"]
        else:
            status, t_end, winner = STATUS_EXHAUSTED, D_ex, None

        completed = t_end <= remaining
        eff_end = t_end if completed else remaining
        final_status = status if completed else STATUS_PARTIAL

        gen_searched = 0
        gen_rows = []
        for i in active_ids:
            acc.m_gen[i] += 1
            if status == STATUS_FOUND and i == winner["miner"] and completed:
                c_i = winner["offset"] + 1
            else:
                c_i = _completed(rates_int[i], eff_end, S_i[i])
            acc.searched_cum[i] += c_i
            gen_searched += c_i
            acc.last_pos[i] = int(ranges_all[i][0] + c_i - 1) if c_i > 0 else None
            prod_time = Fraction(c_i, rates_int[i])
            acc.productive_t[i] += prod_time
            acc.completion_times.append(float(Fraction(S_i[i], rates_int[i])))
            if is_c2:
                acc.active_t[i] += prod_time
                idl = eff_end - prod_time
                if idl > 0:
                    acc.idle_t[i] += idl
                    acc.m_idle[i] += 1
                nonprod = Fraction(0)
            else:
                acc.active_t[i] += eff_end
                nonprod = eff_end - prod_time
            reached = (status == STATUS_FOUND and i == winner["miner"] and completed)
            if reached:
                sr = "solution_found"
            elif not completed:
                sr = "simulation_cutoff"
            elif c_i >= S_i[i]:
                sr = "range_exhausted"
                acc.m_exhaust[i] += 1
            else:
                sr = "template_refreshed"
            acc.stop_reason[i] = sr
            if acc.gen_rows is not None:
                mine_sol = best.get(i)
                gen_rows.append(dict(
                    run_id=None, template_generation_id=acc.gen_counter, miner_id=i,
                    template_id=f"tmpl-{acc.gen_counter}",
                    assigned_range_start=int(ranges_all[i][0]), assigned_range_end=int(ranges_all[i][1]),
                    assigned_range_size=int(S_i[i]), search_start_position=int(ranges_all[i][0]),
                    candidates_evaluated_this_generation=int(c_i),
                    cumulative_candidates_evaluated=int(acc.searched_cum[i]),
                    last_evaluated_position=acc.last_pos[i],
                    unsearched_candidates_this_generation=int(S_i[i] - c_i),
                    inactive_candidates_this_generation=0,
                    productive_search_time_s=float(prod_time),
                    active_nonproductive_time_s=float(nonprod),
                    idle_time_s=float(eff_end - prod_time) if is_c2 else 0.0,
                    offline_time_s=0.0,
                    earliest_solution_position=(int(mine_sol[1]) if mine_sol else None),
                    earliest_solution_time_s=(float(Fraction(mine_sol[0] + 1, rates_int[i])) if mine_sol else None),
                    stop_reason=sr, completed_range=bool(c_i >= S_i[i]),
                    generated_block_id=None, received_winner_time_s=None))
        for i in inactive:
            acc.offline_t[i] += eff_end
            acc.stop_reason[i] = "inactive"
            if acc.gen_rows is not None:
                gen_rows.append(dict(
                    run_id=None, template_generation_id=acc.gen_counter, miner_id=i,
                    template_id=f"tmpl-{acc.gen_counter}",
                    assigned_range_start=int(ranges_all[i][0]), assigned_range_end=int(ranges_all[i][1]),
                    assigned_range_size=int(S_i[i]), search_start_position=int(ranges_all[i][0]),
                    candidates_evaluated_this_generation=0, cumulative_candidates_evaluated=0,
                    last_evaluated_position=None, unsearched_candidates_this_generation=0,
                    inactive_candidates_this_generation=int(S_i[i]),
                    productive_search_time_s=0.0, active_nonproductive_time_s=0.0,
                    idle_time_s=0.0, offline_time_s=float(eff_end),
                    earliest_solution_position=None, earliest_solution_time_s=None,
                    stop_reason="inactive", completed_range=False,
                    generated_block_id=None, received_winner_time_s=None))

        acc.total_evals += gen_searched
        acc.distinct_evals += gen_searched          # disjoint -> distinct == total, duplicate 0

        is_accepted = completed and status == STATUS_FOUND
        is_exhausted = completed and status in (STATUS_EXHAUSTED, STATUS_NO_ACTIVE)
        is_partial = not completed
        block_id = None
        stale = comp = proposal = 0
        if is_accepted:
            acc.accepted += 1
            block_id = f"blk-{acc.accepted}"
            proposal, comp = len(discoveries), 0
            _, proposal, comp, stale = _resolve(discoveries,
                _draw_delays_none(discoveries, cfg, winner))  # recompute stale deterministically
            acc.proposal_miners += proposal
            acc.competitor_miners += comp
            acc.stale_blocks += stale
            msgs = max(len(active_ids) - 1, 0)
            acc.coord["block_propagation"]["message_count"] += msgs
            acc.coord["block_propagation"]["bytes"] += msgs * cfg.block_size_bytes
            if acc.gen_rows is not None and gen_rows:
                for gr in gen_rows:
                    if gr["miner_id"] == winner["miner"]:
                        gr["generated_block_id"] = block_id
            refresh_cause = "accepted_block"
        elif is_exhausted:
            acc.exhausted += 1
            acc.template_refresh += 1
            refresh_cause = "active_domain_exhausted" if status == STATUS_EXHAUSTED else "no_active_miners"
        else:
            acc.partials += 1
            refresh_cause = "simulation_cutoff"

        if acc.per_template is not None:
            acc.per_template.append(dict(
                run_id=None, round_id=acc.accepted, template_generation_id=acc.gen_counter,
                parent_block_id=parent_before, template_id=f"tmpl-{acc.gen_counter}",
                target=p, mu=cfg.mu, assigned_domain_size=S,
                searched_domain_size=gen_searched, inactive_domain_size=inactive_count,
                unsearched_domain_size=S - gen_searched - inactive_count,
                total_template_solution_count=k, active_range_solution_count=len(discoveries),
                inactive_range_solution_count=n_inact_sol, discoverable_finder_count=len(discoveries),
                total_template_solution_position_count=k,
                active_range_solution_position_count=len(discoveries),
                inactive_range_solution_position_count=n_inact_sol,
                distinct_potential_finder_miner_count=len(discoveries),
                actual_proposal_miner_count=(len(discoveries) if is_accepted else 0),
                actual_competitor_miner_count=comp, legitimate_stale_block_count=stale,
                solution_count=k, finder_count=(1 if is_accepted else 0),
                accepted_block_id=block_id, exhausted=is_exhausted, partial=is_partial,
                completed=completed, accepted=is_accepted, refresh_required=(not is_accepted),
                status=final_status, refresh_cause=refresh_cause,
                start_time_s=float(t), end_time_s=float(t + eff_end), duration_s=float(eff_end),
                exhausted_time_s=(float(eff_end) if is_exhausted else 0.0),
                active_domain_completion_time_s=(float(D_ex) if is_exhausted else None),
                partial_cutoff_time_s=(float(eff_end) if is_partial else None),
                legitimate_competitor_count=comp, obsolete_event_rejection_count=0))
        if acc.gen_rows is not None:
            acc.gen_rows.extend(gen_rows)
        if acc.block_log is not None and is_accepted:
            acc.block_log.append(dict(block_index=acc.accepted, t_start_s=float(t),
                                      duration_s=float(eff_end), winner_id=int(winner["miner"]),
                                      winner_time_s=float(t_end), solutions_found=k,
                                      active_solutions=len(discoveries), inactive_solutions=n_inact_sol,
                                      competitors=comp, stale_blocks=stale,
                                      propagation_messages=max(len(active_ids) - 1, 0)))
        if is_accepted:
            acc.last_accepted_block_id = block_id
        t += eff_end
        if is_partial:
            break


def _draw_delays_none(discoveries, cfg, winner):
    """Deterministic per-competitor delays for the accepted block, drawn from a
    winner-scoped named stream so stale counting is reproducible and independent of
    the discovery-resolution draw order."""
    if not discoveries or winner is None:
        return []
    comps = [d for d in discoveries if d["miner"] != winner["miner"] and d["identity"] != winner["identity"]]
    r = rng(cfg.seed * 1_000_003 + winner["miner"], "propagation_delay")
    return _draw_delays(r, cfg.propagation_delay_mean_s, len(comps))


def _sim_frontier(cfg, n, S, p, rates_int, active_ids, inactive, BIG, acc):
    scen = cfg.scenario_id
    is_b1 = (scen == "B1")
    max_rate = max((rates_int[i] for i in active_ids), default=1)
    max_id = max(active_ids, key=lambda i: rates_int[i]) if active_ids else None
    D_ex_b1 = Fraction(S, max_rate)
    r_solk = rng(cfg.seed, "solution_count")
    r_solpos = rng(cfg.seed, "solution_positions")
    r_starts = rng(cfg.seed, "miner_starts")
    r_delay = rng(cfg.seed, "propagation_delay")

    t = Fraction(0)
    while t < BIG:
        acc.gen_counter += 1
        acc.nonce_alloc += 1
        parent_before = acc.last_accepted_block_id
        remaining = BIG - t
        k = int(r_solk.binomial(S, p))
        pos = _exact.sample_without_replacement(r_solpos, S, k) if k > 0 else np.empty(0, dtype=np.int64)
        acc.total_sol += k
        starts = ([int(r_starts.integers(0, S)) for _ in active_ids] if scen == "B2" else None)

        discoveries = []
        if active_ids and k > 0:
            if is_b1:
                mn = int(pos.min())
                for i in active_ids:
                    discoveries.append(dict(miner=i, offset=mn, q=mn, identity=mn,
                                            time=Fraction(mn + 1, rates_int[i])))
            else:  # B2: earliest circular solution per miner from its own start
                for idx, i in enumerate(active_ids):
                    st = starts[idx]
                    d_best = min(((int(q) - st) % S for q in pos.tolist()))
                    q_best = (st + d_best) % S
                    discoveries.append(dict(miner=i, offset=d_best, q=q_best, identity=q_best,
                                            time=Fraction(d_best + 1, rates_int[i])))
        acc.active_sol += k
        acc.potential_finders += len(discoveries)

        if not active_ids:
            status, t_end, winner = STATUS_NO_ACTIVE, D_ex_b1, None
        elif k == 0:
            if is_b1:
                status, t_end, winner = STATUS_EXHAUSTED, D_ex_b1, None
            else:
                rates_active = [rates_int[i] for i in active_ids]
                t_ex, _ = _cov.b2_exhaustion_time(starts, rates_active, S)
                status, t_end, winner = STATUS_EXHAUSTED, Fraction(str(round(t_ex, 6))), None
        else:
            delays = _draw_delays(r_delay, cfg.propagation_delay_mean_s, max(len(discoveries) - 1, 0))
            winner, proposal, comp, stale = _resolve(discoveries, delays)
            status, t_end = STATUS_FOUND, winner["time"]

        completed = t_end <= remaining
        eff_end = t_end if completed else remaining
        final_status = status if completed else STATUS_PARTIAL

        gen_total = 0
        gen_rows = []
        disc_by_miner = {d["miner"]: d for d in discoveries}
        for i in active_ids:
            acc.m_gen[i] += 1
            c_i = _completed(rates_int[i], eff_end, S)
            acc.searched_cum[i] += c_i
            gen_total += c_i
            acc.last_pos[i] = int(c_i - 1) if c_i > 0 else None
            prod_time = Fraction(c_i, rates_int[i])
            acc.productive_t[i] += prod_time
            acc.active_t[i] += eff_end
            acc.completion_times.append(float(Fraction(S, rates_int[i])))
            reached = (status == STATUS_FOUND and i == winner["miner"] and completed)
            sr = ("solution_found" if reached else "simulation_cutoff" if not completed
                  else "template_refreshed" if status == STATUS_FOUND else "range_exhausted")
            acc.stop_reason[i] = sr
            if status == STATUS_EXHAUSTED and completed:
                acc.m_exhaust[i] += 1
            if acc.gen_rows is not None:
                md = disc_by_miner.get(i)
                gen_rows.append(dict(
                    run_id=None, template_generation_id=acc.gen_counter, miner_id=i,
                    template_id=f"tmpl-{acc.gen_counter}", assigned_range_start=0,
                    assigned_range_end=int(S - 1), assigned_range_size=int(S),
                    search_start_position=0, candidates_evaluated_this_generation=int(c_i),
                    cumulative_candidates_evaluated=int(acc.searched_cum[i]),
                    last_evaluated_position=acc.last_pos[i],
                    unsearched_candidates_this_generation=int(S - c_i),
                    inactive_candidates_this_generation=0,
                    productive_search_time_s=float(prod_time), active_nonproductive_time_s=float(eff_end - prod_time),
                    idle_time_s=0.0, offline_time_s=0.0,
                    earliest_solution_position=(int(md["q"]) if md else None),
                    earliest_solution_time_s=(float(md["time"]) if md else None),
                    stop_reason=sr, completed_range=bool(c_i >= S),
                    generated_block_id=None, received_winner_time_s=None))
        for i in inactive:
            acc.offline_t[i] += eff_end
            acc.stop_reason[i] = "inactive"
            if acc.gen_rows is not None:
                gen_rows.append(dict(
                    run_id=None, template_generation_id=acc.gen_counter, miner_id=i,
                    template_id=f"tmpl-{acc.gen_counter}", assigned_range_start=0,
                    assigned_range_end=int(S - 1), assigned_range_size=int(S), search_start_position=0,
                    candidates_evaluated_this_generation=0, cumulative_candidates_evaluated=0,
                    last_evaluated_position=None, unsearched_candidates_this_generation=0,
                    inactive_candidates_this_generation=int(S),
                    productive_search_time_s=0.0, active_nonproductive_time_s=0.0,
                    idle_time_s=0.0, offline_time_s=float(eff_end),
                    earliest_solution_position=None, earliest_solution_time_s=None,
                    stop_reason="inactive", completed_range=False,
                    generated_block_id=None, received_winner_time_s=None))
        if acc.gen_rows is not None:
            acc.gen_rows.extend(gen_rows)

        if not active_ids:
            gen_distinct = 0
        elif is_b1:
            gen_distinct = _completed(max_rate, eff_end, S)
        else:
            lengths = _cov.lengths_from_winner_time(float(eff_end), [rates_int[i] for i in active_ids], S)
            covx = _cov.b2_coverage_exact(starts, lengths, S)
            gen_total = int(covx["total_candidate_evaluations"])
            gen_distinct = int(covx["distinct_candidate_evaluations"])
        acc.total_evals += gen_total
        acc.distinct_evals += gen_distinct
        acc.duplicate_evals += (gen_total - gen_distinct)

        is_accepted = completed and status == STATUS_FOUND
        is_exhausted = completed and status in (STATUS_EXHAUSTED, STATUS_NO_ACTIVE)
        is_partial = not completed
        block_id = None
        stale = comp = proposal = 0
        if is_accepted:
            acc.accepted += 1
            block_id = f"blk-{acc.accepted}"
            _, proposal, comp, stale = _resolve(discoveries, _draw_delays_none(discoveries, cfg, winner))
            acc.proposal_miners += proposal
            acc.competitor_miners += comp
            acc.stale_blocks += stale
            msgs = max(len(active_ids) - 1, 0)
            acc.coord["block_propagation"]["message_count"] += msgs
            acc.coord["block_propagation"]["bytes"] += msgs * cfg.block_size_bytes
            refresh_cause = "accepted_block"
        elif is_exhausted:
            acc.exhausted += 1
            acc.template_refresh += 1
            refresh_cause = "active_domain_exhausted"
        else:
            acc.partials += 1
            refresh_cause = "simulation_cutoff"

        if acc.per_template is not None:
            acc.per_template.append(dict(
                run_id=None, round_id=acc.accepted, template_generation_id=acc.gen_counter,
                parent_block_id=parent_before, template_id=f"tmpl-{acc.gen_counter}",
                target=p, mu=cfg.mu, assigned_domain_size=S,
                searched_domain_size=min(S, gen_distinct), inactive_domain_size=0,
                unsearched_domain_size=S - min(S, gen_distinct),
                total_template_solution_count=k, active_range_solution_count=k,
                inactive_range_solution_count=0, discoverable_finder_count=len(discoveries),
                total_template_solution_position_count=k,
                active_range_solution_position_count=k, inactive_range_solution_position_count=0,
                distinct_potential_finder_miner_count=len(discoveries),
                actual_proposal_miner_count=(proposal if is_accepted else 0),
                actual_competitor_miner_count=comp, legitimate_stale_block_count=stale,
                solution_count=k, finder_count=(1 if is_accepted else 0),
                accepted_block_id=block_id, exhausted=is_exhausted, partial=is_partial,
                completed=completed, accepted=is_accepted, refresh_required=(not is_accepted),
                status=final_status, refresh_cause=refresh_cause,
                start_time_s=float(t), end_time_s=float(t + eff_end), duration_s=float(eff_end),
                exhausted_time_s=(float(eff_end) if is_exhausted else 0.0),
                active_domain_completion_time_s=(float(t_end) if is_exhausted else None),
                partial_cutoff_time_s=(float(eff_end) if is_partial else None),
                legitimate_competitor_count=comp, obsolete_event_rejection_count=0))
        if acc.block_log is not None and is_accepted:
            acc.block_log.append(dict(block_index=acc.accepted, t_start_s=float(t),
                                      duration_s=float(eff_end), winner_id=int(winner["miner"]),
                                      winner_time_s=float(t_end), solutions_found=k,
                                      competitors=comp, stale_blocks=stale,
                                      propagation_messages=max(len(active_ids) - 1, 0)))
        if is_accepted:
            acc.last_accepted_block_id = block_id
        t += eff_end
        if is_partial:
            break


def _build_result(cfg, n, S, p, rates, rates_int, shares, ranges_all, active_ids, inactive,
                  active_power_w, idle_power_w, BIG, acc, emit_log, emit_detail, emit_gen):
    scen = cfg.scenario_id
    at = np.array([float(x) for x in acc.active_t])
    it = np.array([float(x) for x in acc.idle_t])
    ot = np.array([float(x) for x in acc.offline_t])
    pt = np.array([float(x) for x in acc.productive_t])
    active_energy_kwh = float((active_power_w * at).sum()) / J_PER_KWH
    idle_energy_kwh = float((idle_power_w * it).sum()) / J_PER_KWH
    coordination_energy_kwh = 0.0
    total_energy_kwh = active_energy_kwh + idle_energy_kwh + coordination_energy_kwh

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
    non_productive_active = float((at - pt).clip(min=0).sum())
    stales = acc.stale_blocks
    all_valid = acc.accepted + stales

    result = dict(
        output_schema_version=OUTPUT_SCHEMA_VERSION, engine_version=ENGINE_VERSION,
        scenario_id=scen, seed=cfg.seed, miners=n, domain_size=S, p=p, mu=cfg.mu,
        allocation_policy=cfg.allocation_policy, hash_rate_distribution=cfg.hash_rate_distribution,
        idle_power_ratio=cfg.idle_power_ratio, inactive_fraction=cfg.inactive_miner_fraction,
        network_hash_rate_hps_int=sum(rates_int), integer_rates_sum_exact=(sum(rates_int) == int(round(cfg.network_hash_rate_hps))),
        total_energy_kwh=total_energy_kwh, active_energy_kwh=active_energy_kwh,
        idle_energy_kwh=idle_energy_kwh, coordination_energy_kwh=coordination_energy_kwh,
        accepted_blocks=acc.accepted, block_metrics_defined=has_blocks,
        effective_block_interval_s=((BIG / acc.accepted) if has_blocks else None),
        effective_block_interval_na_reason=block_na,
        energy_per_accepted_block_kwh=((total_energy_kwh / acc.accepted) if has_blocks else None),
        energy_per_accepted_block_na_reason=block_na,
        throughput_blocks_per_s=(acc.accepted / BIG if BIG else 0.0),
        energy_per_transaction_kwh=None, energy_per_transaction_na_reason="no_committed_transactions",
        confirmation_time_proxy_s=((BIG / acc.accepted) if has_blocks else None),
        confirmation_time_proxy_na_reason=block_na,
        # stale semantics with documented denominators (Section 4)
        legitimate_stale_block_count=stales,
        stale_blocks=stales,
        stales_per_accepted_block=((stales / acc.accepted) if has_blocks else None),
        stales_per_accepted_block_na_reason=block_na,
        stale_fraction_of_all_valid_blocks=((stales / all_valid) if all_valid > 0 else None),
        stale_fraction_na_reason=(None if all_valid > 0 else "no_valid_proposals"),
        legitimate_stale_rate=((stales / acc.accepted) if has_blocks else None),   # alias of stales_per_accepted_block (documented)
        legitimate_stale_rate_na_reason=(None if has_blocks else "no_valid_proposals"),
        legitimate_stale_count=stales,
        actual_competitor_miner_count=acc.competitor_miners,
        actual_proposal_miner_count=acc.proposal_miners,
        distinct_potential_finder_miner_count=acc.potential_finders,
        duplicate_evaluation_rate=dup_rate, exhausted_rounds=acc.exhausted,
        partial_generations=acc.partials,
        total_candidate_evaluations=acc.total_evals,
        distinct_candidate_identities=acc.distinct_evals,
        duplicate_evaluations=acc.duplicate_evals,
        total_template_solution_count=acc.total_sol,
        active_range_solution_count=acc.active_sol,
        inactive_range_solution_count=acc.inactive_sol,
        discoverable_finder_count=acc.active_sol,
        total_template_solution_position_count=acc.total_sol,
        active_range_solution_position_count=acc.active_sol,
        inactive_range_solution_position_count=acc.inactive_sol,
        total_active_time_s=float(at.sum()), total_idle_time_s=float(it.sum()),
        total_offline_time_s=float(ot.sum()), total_productive_search_time_s=float(pt.sum()),
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
        unimplemented_agreement_energy_kwh=None, coordination_energy_lower_bound_kwh=0.0,
        inactive_domain=inactive_count, common_template=COMMON_TEMPLATE[scen], idle_policy=IDLE[scen],
        idle_enter_reason=("range_exhausted_no_solution" if IDLE[scen] else None),
        idle_leave_reason=("new_template_generation_or_accepted_block" if IDLE[scen] else None),
    )
    if emit_log:
        result["block_log"] = acc.block_log
    if emit_detail:
        result["per_miner"] = _build_per_miner(cfg, n, rates, rates_int, shares, ranges_all,
                                               inactive, active_power_w, idle_power_w, acc, S, at, it, ot, pt)
        result["per_template"] = acc.per_template
    if emit_gen:
        result["per_miner_generation"] = acc.gen_rows
    return result


def _build_per_miner(cfg, n, rates, rates_int, shares, ranges_all, inactive, active_power_w,
                     idle_power_w, acc, S, at, it, ot, pt):
    disjoint = DISJOINT[cfg.scenario_id]
    out = []
    for i in range(n):
        a, b = ranges_all[i]
        L_i = (b - a + 1) if disjoint else int(S)
        is_inactive = i in inactive
        searched = 0 if is_inactive else int(acc.searched_cum[i])
        inactive_cand = L_i if (is_inactive and disjoint) else 0
        state = "offline" if is_inactive else ("idled" if acc.m_idle[i] > 0 else "active")
        reasons = {}
        if acc.m_exhaust[i]:
            reasons["range_exhausted"] = int(acc.m_exhaust[i])
        if acc.m_idle[i]:
            reasons["entered_idle"] = int(acc.m_idle[i])
        out.append(dict(
            run_id=None, miner_id=i, hash_rate_hps=float(rates[i]), hash_rate_hps_int=int(rates_int[i]),
            hash_rate_share=float(shares[i]), allocation_policy=cfg.allocation_policy,
            range_start=int(a), range_end=int(b), range_size=int(L_i) if disjoint else None,
            search_start_position=int(a) if disjoint else 0,
            candidates_evaluated=searched, searched_count=searched,
            last_evaluated_position=acc.last_pos[i],
            unsearched_count=(int(L_i - min(searched, L_i)) if disjoint else None),
            remaining_unsearched=(0 if is_inactive else (int(L_i - min(searched, L_i)) if disjoint else None)),
            inactive_count=inactive_cand,
            active_time_s=float(at[i]), idle_time_s=float(it[i]), offline_time_s=float(ot[i]),
            productive_search_time_s=float(pt[i]),
            active_energy_kwh=float(active_power_w[i] * at[i]) / J_PER_KWH,
            idle_energy_kwh=float(idle_power_w[i] * it[i]) / J_PER_KWH,
            template_generations_participated=int(acc.m_gen[i]),
            range_exhaustion_count=int(acc.m_exhaust[i]), idle_entry_count=int(acc.m_idle[i]),
            final_state=state, completion_status=(acc.stop_reason[i] or "inactive"),
            stop_reason=(acc.stop_reason[i] or "inactive"), state_transition_reason_counts=reasons))
    return out
