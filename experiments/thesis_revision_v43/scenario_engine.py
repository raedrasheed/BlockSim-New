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

ENGINE_VERSION = "5b1g.2"

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
        # --- single-height stale-race DIAGNOSTIC accumulators (Sections 1-3,8) ---
        # one stale per MINER per height; many distinct miners may stale at one height
        self.single_height_stale_blocks = 0      # total admitted stale blocks (0..N_active-1 / height)
        self.actual_stale_producer_miners = 0    # == single_height_stale_blocks
        self.heights_with_any_stale = 0          # heights with >=1 stale (boolean indicator sum)
        self.potential_competitor_miners = 0     # distinct non-winning distinct-identity miners
        self.actual_competitor_miners = 0        # actual admitted competitors (== stale producers)
        self.actual_proposal_miners = 0          # 1 winner + all admitted stales, per accepted height
        self.potential_finders = 0               # per-miner reachable finders (miners)
        # separate, NON-integrated post-winner diagnostic work (5B1G.1 §4).
        # post_winner_* covers EVERY active non-winning miner; stale_producer_postwinner_*
        # is the producer-only subset. Neither enters primary metrics.
        self.post_winner_candidate_evaluations = 0
        self.post_winner_active_time = Fraction(0)
        self.stale_producer_postwinner_candidate_evaluations = 0
        self.stale_producer_postwinner_active_time = Fraction(0)
        # separate main vs stale block propagation (Section 5)
        self.main_block_prop_msgs = 0
        self.main_block_prop_bytes = 0
        self.stale_block_prop_msgs = 0
        self.stale_block_prop_bytes = 0
        self.stale_race_records = None           # machine-readable stale-race records
        self.delivery_delay_records = None       # machine-readable delivery-delay records
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
    acc.stale_race_records = [] if emit_detail else None
    acc.delivery_delay_records = [] if emit_detail else None
    BIG = Fraction(int(round(cfg.simulation_duration_s)))

    if DISJOINT[cfg.scenario_id]:
        _sim_disjoint(cfg, n, S, p, rates_int, active_ids, inactive, ranges_all, BIG, acc)
    else:
        _sim_frontier(cfg, n, S, p, rates_int, active_ids, inactive, BIG, acc)

    return _build_result(cfg, n, S, p, rates, rates_int, shares, ranges_all, active_ids,
                         inactive, active_power_w, idle_power_w, float(BIG), acc,
                         emit_log, emit_detail, emit_generation_detail)


def _draw_delays(r_delay, mean_s, count):
    """Backward-compatible primitive: `count` independent exponential delays from a
    generator. Retained for the low-level competitor/stale unit tests; the ENGINE no
    longer uses anonymous delay lists (Section 4) — it derives a per-DELIVERY delay
    from the full delivery identity via `_delivery_delay`."""
    return [Fraction(str(round(float(r_delay.exponential(max(mean_s, 1e-12))), 9)))
            for _ in range(count)]


def _resolve(discoveries, delays):
    """Low-level competitor/stale classifier PRIMITIVE (kept for unit tests). Given
    per-miner discoveries and a delay list, returns (winner, proposal_count,
    competitor_miner_count, stale_count) under the pairwise rule. The engine does NOT
    call this — it uses `_resolve_stale_race`, which derives recipient-specific delays
    from the delivery identity and admits one stale per non-winning MINER (multiple
    distinct miners may each stale at the same height; no global cap) (Sections 2-4)."""
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


def _delivery_delay(cfg, gen_id, parent_block_id, winner_miner, recipient_miner):
    """Section 4: deterministic propagation delay for ONE winner->recipient delivery.
    One independent stream per (master_seed, template_generation_id, parent_block_id,
    winner_miner_id, recipient_miner_id, "propagation_delay"). Consequences: fully
    reproducible; independent per recipient; NOT a function of competitor-list order;
    adding a recipient never shifts an existing recipient's delay; the same winner in
    a DIFFERENT generation (different gen_id/parent) does not reuse the delay. Returns
    (delay_fraction, stream_key). Zero configured mean -> exact zero delay."""
    key = (f"{cfg.seed}|{gen_id}|{parent_block_id}|{winner_miner}|{recipient_miner}"
           "|propagation_delay")
    mean = cfg.propagation_delay_mean_s
    if mean is None or mean <= 0:
        return Fraction(0), key
    seed = int.from_bytes(hashlib.sha256(key.encode()).digest()[:8], "big")
    val = float(np.random.default_rng(seed).exponential(mean))
    return Fraction(str(round(val, 9))), key


def _resolve_stale_race(discoveries, cfg, gen_id, parent_block_id):
    """SINGLE-HEIGHT STALE-RACE DIAGNOSTIC (Sections 1-4). For ONE accepted height,
    given every miner's earliest reachable discovery, determine the winner and ALL
    admitted stale producers. A non-winning miner j produces a stale block iff it is a
    distinct miner with a distinct candidate identity AND discovered before it would
    have received the winner (discovery_time_j < winner_time + delivery_delay(w->j)).
    A given non-winning miner contributes at most one stale proposal per height (its
    earliest reachable solution), but MULTIPLE distinct miners may each produce a
    stale at the same height -> stale_block_count ranges 0 .. N_active-1. There is NO
    global one-stale-per-height cap. Recipient-specific delays come from
    `_delivery_delay` (order-independent).
    The race's evaluations, active time and energy are reported SEPARATELY and NOT
    integrated into primary metrics."""
    winner = min(discoveries, key=lambda d: (d["time"], d["miner"]))
    # distinct non-winning miners with a DISTINCT identity; keep each miner's EARLIEST
    # reachable solution (one potential stale proposal per miner per height).
    by_miner = {}
    for d in discoveries:
        if d["miner"] == winner["miner"] or d["identity"] == winner["identity"]:
            continue
        cur = by_miner.get(d["miner"])
        if cur is None or (d["time"], d["miner"]) < (cur["time"], cur["miner"]):
            by_miner[d["miner"]] = d
    competitors = [by_miner[m] for m in sorted(by_miner)]
    received, delay_by, delay_key_by, disc_time_by = {}, {}, {}, {}
    producers = []
    for d in competitors:
        delay, key = _delivery_delay(cfg, gen_id, parent_block_id, winner["miner"], d["miner"])
        recv = winner["time"] + delay
        received[d["miner"]] = recv
        delay_by[d["miner"]] = delay
        delay_key_by[d["miner"]] = key
        disc_time_by[d["miner"]] = d["time"]
        if d["time"] < recv:                        # discovered before receiving the winner
            producers.append(d)
    producers.sort(key=lambda d: (d["time"], d["miner"]))
    return dict(
        winner=winner, competitors=competitors,
        potential_competitor_miner_count=len(competitors),
        received=received, delay_by=delay_by, delay_key_by=delay_key_by,
        disc_time_by=disc_time_by, stale_producers=producers)


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
    # NOTE: no in-loop anonymous delay stream (Section 4) — per-delivery delays are
    # derived from the delivery identity when the single stale race is resolved.

    t = Fraction(0)
    while t < BIG:
        acc.gen_counter += 1
        acc.nonce_alloc += 1
        gen_id = acc.gen_counter
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

        # Count ALL sampled positions by region BEFORE reducing to one proposal per
        # miner (Section 6): a miner may own several positions -> more POSITIONS, but
        # still one potential finder MINER.
        best = {}
        n_active_positions = 0
        n_inact_sol = 0
        for q in pos.tolist():
            ow = owner(q)
            if ow is None:
                continue
            if ow in active_set:
                n_active_positions += 1
                d = q - ranges_all[ow][0]
                if ow not in best or d < best[ow][0]:
                    best[ow] = (d, q)
            else:
                n_inact_sol += 1
        discoveries = [dict(miner=i, offset=d, q=q,
                            identity=((i, q) if is_b0 else q),
                            time=Fraction(d + 1, rates_int[i]))
                       for i, (d, q) in best.items()]
        acc.active_sol += n_active_positions
        acc.inactive_sol += n_inact_sol
        acc.potential_finders += len(discoveries)      # potential finder MINERS

        if not active_ids:
            status, t_end, winner = STATUS_NO_ACTIVE, D_ex, None
        elif discoveries:
            winner = min(discoveries, key=lambda d: (d["time"], d["miner"]))
            status, t_end = STATUS_FOUND, winner["time"]
        else:
            status, t_end, winner = STATUS_EXHAUSTED, D_ex, None

        completed = t_end <= remaining
        eff_end = t_end if completed else remaining
        final_status = status if completed else STATUS_PARTIAL
        is_accepted = completed and status == STATUS_FOUND
        is_exhausted = completed and status in (STATUS_EXHAUSTED, STATUS_NO_ACTIVE)
        is_partial = not completed

        gen_searched = 0
        gen_rows = {}
        for i in active_ids:
            acc.m_gen[i] += 1
            if is_accepted and i == winner["miner"]:
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
            reached = (is_accepted and i == winner["miner"])
            if reached:
                spr = "solution_found"
            elif not completed:
                spr = "simulation_cutoff"
            elif c_i >= S_i[i]:
                spr = "range_exhausted"
                acc.m_exhaust[i] += 1
            else:
                spr = "template_refreshed"
            acc.stop_reason[i] = spr
            # lifecycle stop reason (Section 5); patched for winner/producer after
            # the single stale race is resolved
            if not completed:
                life = "simulation_cutoff"
            elif is_accepted:
                life = "winner_received" if i in best else "no_reachable_solution"
            else:
                life = "no_reachable_solution"
            if acc.gen_rows is not None:
                mine_sol = best.get(i)
                own_pos = (int(mine_sol[1]) if mine_sol else None)
                own_t = (float(Fraction(mine_sol[0] + 1, rates_int[i])) if mine_sol else None)
                gen_rows[i] = dict(
                    run_id=None, template_generation_id=gen_id, miner_id=i,
                    template_id=f"tmpl-{gen_id}",
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
                    earliest_solution_position=own_pos, earliest_solution_time_s=own_t,
                    earliest_solution_identity=(str(mine_sol[1]) if mine_sol else None),
                    path_wraps_around=False,           # disjoint ranges are linear (no wrap)
                    path_end_position=acc.last_pos[i], circular_candidates_evaluated=int(c_i),
                    search_progress_reason=spr, stop_reason=life,
                    completed_range=bool(c_i >= S_i[i]),
                    generated_block_id=None, received_winner_time_s=None,
                    propagation_delay_s=None, delivery_stream_key=None,
                    potential_old_parent_solution_position=own_pos,
                    potential_old_parent_solution_time_s=own_t,
                    found_competing_solution_before_receipt=False,
                    produced_stale_block=False, stale_block_id=None)
        for i in inactive:
            acc.offline_t[i] += eff_end
            acc.stop_reason[i] = "inactive"
            if acc.gen_rows is not None:
                gen_rows[i] = dict(
                    run_id=None, template_generation_id=gen_id, miner_id=i,
                    template_id=f"tmpl-{gen_id}",
                    assigned_range_start=int(ranges_all[i][0]), assigned_range_end=int(ranges_all[i][1]),
                    assigned_range_size=int(S_i[i]), search_start_position=int(ranges_all[i][0]),
                    candidates_evaluated_this_generation=0, cumulative_candidates_evaluated=0,
                    last_evaluated_position=None, unsearched_candidates_this_generation=0,
                    inactive_candidates_this_generation=int(S_i[i]),
                    productive_search_time_s=0.0, active_nonproductive_time_s=0.0,
                    idle_time_s=0.0, offline_time_s=float(eff_end),
                    earliest_solution_position=None, earliest_solution_time_s=None,
                    earliest_solution_identity=None,
                    path_wraps_around=False, path_end_position=None,
                    circular_candidates_evaluated=0,
                    search_progress_reason="inactive", stop_reason="inactive",
                    completed_range=False,
                    generated_block_id=None, received_winner_time_s=None,
                    propagation_delay_s=None, delivery_stream_key=None,
                    potential_old_parent_solution_position=None,
                    potential_old_parent_solution_time_s=None,
                    found_competing_solution_before_receipt=False,
                    produced_stale_block=False, stale_block_id=None)

        acc.total_evals += gen_searched
        acc.distinct_evals += gen_searched          # disjoint -> distinct == total, duplicate 0

        block_id = None
        stale_block_count = actual_comp = actual_prop = pot_comp = 0
        stale_pids = []
        disc_by_miner = {d["miner"]: d for d in discoveries}
        if is_accepted:
            acc.accepted += 1
            block_id = f"blk-{acc.accepted}"
            race, producers, stale_block_ids, actual_prop, actual_comp, stale_block_count, \
                delivery_info = _record_stale_race(
                    acc, cfg, gen_id, parent_before, block_id, discoveries, disc_by_miner,
                    active_ids, rates_int, S, winner["time"], True, ranges_all)
            pot_comp = race["potential_competitor_miner_count"]
            stale_pids = [int(p["miner"]) for p in producers]
            _patch_winner_and_deliveries(gen_rows if acc.gen_rows is not None else None,
                                         winner, block_id, delivery_info)
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
                run_id=None, round_id=acc.accepted, template_generation_id=gen_id,
                parent_block_id=parent_before, template_id=f"tmpl-{gen_id}",
                target=p, mu=cfg.mu, assigned_domain_size=S,
                searched_domain_size=gen_searched, inactive_domain_size=inactive_count,
                unsearched_domain_size=S - gen_searched - inactive_count,
                total_template_solution_count=k, active_range_solution_count=n_active_positions,
                inactive_range_solution_count=n_inact_sol, discoverable_finder_count=len(discoveries),
                total_template_solution_position_count=k,
                active_range_solution_position_count=n_active_positions,
                inactive_range_solution_position_count=n_inact_sol,
                distinct_potential_finder_miner_count=len(discoveries),
                potential_competitor_miner_count=(pot_comp if is_accepted else 0),
                actual_proposal_miner_count=actual_prop,
                actual_competitor_miner_count=actual_comp,
                actual_stale_producer_miner_count=stale_block_count,
                stale_block_count=stale_block_count,
                single_height_stale_block_count=stale_block_count,
                height_has_any_stale=bool(stale_block_count > 0),
                stale_producer_miner_ids=list(stale_pids),
                stale_block_ids=[f"stale-{block_id}-m{m}" for m in stale_pids],
                legitimate_stale_block_count=stale_block_count,
                solution_count=k, finder_count=(1 if is_accepted else 0),
                accepted_block_id=block_id, exhausted=is_exhausted, partial=is_partial,
                completed=completed, accepted=is_accepted, refresh_required=(not is_accepted),
                status=final_status, refresh_cause=refresh_cause,
                start_time_s=float(t), end_time_s=float(t + eff_end), duration_s=float(eff_end),
                exhausted_time_s=(float(eff_end) if is_exhausted else 0.0),
                active_domain_completion_time_s=(float(D_ex) if is_exhausted else None),
                partial_cutoff_time_s=(float(eff_end) if is_partial else None),
                exact_exhaustion_verified=None,
                b2_exhaustion_time_fraction_numerator=None,
                b2_exhaustion_time_fraction_denominator=None,
                previous_candidate_event_time_s=None,
                coverage_before_exhaustion=None, coverage_at_exhaustion=None,
                legitimate_competitor_count=actual_comp, obsolete_event_rejection_count=0))
        if acc.gen_rows is not None:
            acc.gen_rows.extend(gen_rows[i] for i in range(n) if i in gen_rows)
        if acc.block_log is not None and is_accepted:
            acc.block_log.append(dict(block_index=acc.accepted, t_start_s=float(t),
                                      duration_s=float(eff_end), winner_id=int(winner["miner"]),
                                      winner_time_s=float(t_end), solutions_found=k,
                                      active_solutions=len(discoveries), inactive_solutions=n_inact_sol,
                                      competitors=actual_comp, stale_blocks=stale_block_count,
                                      propagation_messages=max(len(active_ids) - 1, 0)))
        if is_accepted:
            acc.last_accepted_block_id = block_id
        t += eff_end
        if is_partial:
            break


def _record_stale_race(acc, cfg, gen_id, parent_block_id, block_id, discoveries,
                       disc_by_miner, active_ids, rates_int, S, winner_time, disjoint,
                       ranges_all):
    """Resolve the single-height stale race ONCE for an accepted height, admitting ALL
    qualifying stale producers (one per distinct miner, no global cap). Derive a
    winner-delivery for EVERY active non-winning miner (5B1G.1 §3), accumulate the
    post-winner diagnostic work over ALL of them (§4), count main- vs stale-block
    propagation, emit machine-readable delivery-delay and stale-race records, and
    return (race, producers, stale_block_ids, actual_proposal, actual_competitor,
    stale_block_count, delivery_info). Primary metrics are untouched."""
    race = _resolve_stale_race(discoveries, cfg, gen_id, parent_block_id)
    winner = race["winner"]
    wid = winner["miner"]
    producers = race["stale_producers"]                    # one entry per distinct miner
    producer_ids = {p["miner"] for p in producers}
    stale_block_count = len(producers)
    actual_competitor = stale_block_count                  # == number of stale producers
    actual_proposal = 1 + stale_block_count                # winner + all admitted stales
    stale_block_ids = [f"stale-{block_id}-m{int(p['miner'])}" for p in producers]
    producer_block = {int(p["miner"]): sid for p, sid in zip(producers, stale_block_ids)}
    n_active = len(active_ids)

    acc.single_height_stale_blocks += stale_block_count
    acc.actual_stale_producer_miners += stale_block_count
    acc.actual_competitor_miners += actual_competitor
    acc.actual_proposal_miners += actual_proposal
    acc.potential_competitor_miners += race["potential_competitor_miner_count"]
    if stale_block_count > 0:
        acc.heights_with_any_stale += 1

    # MAIN-block propagation: the winner delivers its block to every OTHER active
    # miner (integrated coordination). Each admitted STALE block gossips to the same
    # peers; stale propagation is counted SEPARATELY and NOT integrated (Sections 2,5).
    main_msgs = max(n_active - 1, 0)
    acc.main_block_prop_msgs += main_msgs
    acc.main_block_prop_bytes += main_msgs * cfg.block_size_bytes
    acc.coord["block_propagation"]["message_count"] += main_msgs
    acc.coord["block_propagation"]["bytes"] += main_msgs * cfg.block_size_bytes
    acc.stale_block_prop_msgs += stale_block_count * main_msgs
    acc.stale_block_prop_bytes += stale_block_count * main_msgs * cfg.block_size_bytes

    # --- winner delivery + post-winner diagnostic work for EVERY active non-winner ---
    delivery_info = {}
    for j in active_ids:
        if j == wid:
            continue
        delay, key = _delivery_delay(cfg, gen_id, parent_block_id, wid, j)
        recv = winner_time + delay
        d = disc_by_miner.get(j)
        t_sol = d["time"] if d else None
        same_identity = bool(d is not None and d["identity"] == winner["identity"])
        potential_comp = bool(d is not None and d["identity"] != winner["identity"])
        produced = j in producer_ids
        t_stop = min(recv, t_sol) if t_sol is not None else recv     # §4 stop time
        cap = (ranges_all[j][1] - ranges_all[j][0] + 1) if disjoint else S
        ev = max(_completed(rates_int[j], t_stop, cap) - _completed(rates_int[j], winner_time, cap), 0)
        dt = t_stop - winner_time
        acc.post_winner_candidate_evaluations += int(ev)
        if dt > 0:
            acc.post_winner_active_time += dt
        if produced:
            acc.stale_producer_postwinner_candidate_evaluations += int(ev)
            if dt > 0:
                acc.stale_producer_postwinner_active_time += dt
            sr = "stale_block_generated"
        elif t_sol is not None:
            sr = "winner_received"                    # had a solution (same-id or after receipt)
        else:
            sr = "no_reachable_solution"              # received the winner, found nothing
        delivery_info[j] = dict(
            delay=delay, recv=recv, key=key, t_sol=t_sol, t_stop=t_stop, produced=produced,
            same_identity=same_identity, potential_competitor=potential_comp, stop_reason=sr,
            stale_block_id=producer_block.get(j),
            identity=(d["identity"] if d is not None else None))
        if acc.delivery_delay_records is not None:
            acc.delivery_delay_records.append(dict(
                template_generation_id=gen_id, parent_block_id=parent_block_id,
                winner_miner_id=int(wid), recipient_miner_id=int(j),
                propagation_delay_s=float(delay), received_winner_time_s=float(recv),
                recipient_discovery_time_s=(float(t_sol) if t_sol is not None else None),
                recipient_earliest_solution_identity=(str(d["identity"]) if d is not None else None),
                delivery_stream_key=key,
                discovered_before_receipt=bool(t_sol is not None and t_sol < recv),
                potential_competitor=potential_comp, produced_stale_block=produced,
                same_identity_independent_discovery=same_identity, stop_reason=sr))

    if acc.stale_race_records is not None:
        acc.stale_race_records.append(dict(
            template_generation_id=gen_id, parent_block_id=parent_block_id,
            accepted_block_id=block_id, winner_miner_id=int(wid),
            winner_time_s=float(winner["time"]),
            potential_finder_miner_count=len(discoveries),
            potential_competitor_miner_count=race["potential_competitor_miner_count"],
            actual_stale_producer_miner_count=stale_block_count,
            actual_proposal_miner_count=actual_proposal,
            actual_competitor_miner_count=actual_competitor,
            stale_block_count=stale_block_count,
            single_height_stale_block_count=stale_block_count,
            height_has_any_stale=bool(stale_block_count > 0),
            active_nonwinner_delivery_count=len(delivery_info),
            stale_producer_miner_ids=[int(p["miner"]) for p in producers],
            stale_block_ids=list(stale_block_ids),
            stale_candidate_identities=[str(p["identity"]) for p in producers],
            stale_discovery_times=[float(p["time"]) for p in producers],
            stale_race_energy_not_integrated=True))
    return (race, producers, stale_block_ids, actual_proposal, actual_competitor,
            stale_block_count, delivery_info)


def _patch_winner_and_deliveries(gen_rows, winner, block_id, delivery_info):
    """Patch the per-miner-generation rows for an accepted height: the winner row
    (solution_found + its own receipt time), and EVERY active non-winner's delivery
    (receipt time, delay, stream key, before-receipt flag, produced-stale, lifecycle
    stop reason) — including same-identity and no-solution miners (5B1G.1 §3,§5)."""
    if gen_rows is None:
        return
    w = gen_rows.get(winner["miner"])
    if w is not None:
        w["generated_block_id"] = block_id
        w["received_winner_time_s"] = float(winner["time"])
        w["stop_reason"] = "solution_found"
    for j, info in delivery_info.items():
        gr = gen_rows.get(j)
        if gr is None:
            continue
        gr["received_winner_time_s"] = float(info["recv"])
        gr["propagation_delay_s"] = float(info["delay"])
        gr["delivery_stream_key"] = info["key"]
        gr["found_competing_solution_before_receipt"] = bool(
            info["t_sol"] is not None and info["t_sol"] < info["recv"])
        if info["produced"]:
            gr["produced_stale_block"] = True
            gr["stale_block_id"] = info["stale_block_id"]
        gr["stop_reason"] = info["stop_reason"]


def _sim_frontier(cfg, n, S, p, rates_int, active_ids, inactive, BIG, acc):
    scen = cfg.scenario_id
    is_b1 = (scen == "B1")
    max_rate = max((rates_int[i] for i in active_ids), default=1)
    D_ex_b1 = Fraction(S, max_rate)
    r_solk = rng(cfg.seed, "solution_count")
    r_solpos = rng(cfg.seed, "solution_positions")
    r_starts = rng(cfg.seed, "miner_starts")
    # NOTE: no in-loop anonymous delay stream (Section 4).

    t = Fraction(0)
    while t < BIG:
        acc.gen_counter += 1
        acc.nonce_alloc += 1
        gen_id = acc.gen_counter
        parent_before = acc.last_accepted_block_id
        remaining = BIG - t
        k = int(r_solk.binomial(S, p))
        pos = _exact.sample_without_replacement(r_solpos, S, k) if k > 0 else np.empty(0, dtype=np.int64)
        acc.total_sol += k
        starts = ([int(r_starts.integers(0, S)) for _ in active_ids] if scen == "B2" else None)
        is_b2 = (scen == "B2")
        # actual seeded circular start per active miner (B2); B1 always starts at 0
        start_by_miner = ({i: int(starts[idx]) for idx, i in enumerate(active_ids)}
                          if is_b2 else {i: 0 for i in active_ids})

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
        acc.active_sol += k                            # positions (single shared domain)
        acc.potential_finders += len(discoveries)      # potential finder MINERS

        b2_exh = None
        if not active_ids:
            status, t_end, winner = STATUS_NO_ACTIVE, D_ex_b1, None
        elif k == 0:
            if is_b1:
                status, t_end, winner = STATUS_EXHAUSTED, D_ex_b1, None
            else:
                rates_active = [rates_int[i] for i in active_ids]
                b2_exh = _cov.b2_exhaustion_time_exact(starts, rates_active, S)   # EXACT (Section 7)
                t_end = Fraction(b2_exh["b2_exhaustion_time_fraction_numerator"],
                                 b2_exh["b2_exhaustion_time_fraction_denominator"])
                status, winner = STATUS_EXHAUSTED, None
        else:
            winner = min(discoveries, key=lambda d: (d["time"], d["miner"]))
            status, t_end = STATUS_FOUND, winner["time"]

        completed = t_end <= remaining
        eff_end = t_end if completed else remaining
        final_status = status if completed else STATUS_PARTIAL
        is_accepted = completed and status == STATUS_FOUND
        is_exhausted = completed and status in (STATUS_EXHAUSTED, STATUS_NO_ACTIVE)
        is_partial = not completed

        gen_total = 0
        gen_rows = {}
        disc_by_miner = {d["miner"]: d for d in discoveries}
        # EXACT per-miner completed counts at the exact rational eff_end — the SINGLE
        # source used for per-miner rows AND B2 union coverage (Section 1, no float).
        active_lengths = _cov.lengths_at_time_exact([rates_int[i] for i in active_ids], eff_end, S)
        len_by_miner = {i: active_lengths[idx] for idx, i in enumerate(active_ids)}
        for i in active_ids:
            acc.m_gen[i] += 1
            c_i = len_by_miner[i]                       # exact; == _completed(rate_i, eff_end, S)
            sstart = start_by_miner[i]                  # real seeded start (B2) / 0 (B1)
            acc.searched_cum[i] += c_i
            gen_total += c_i
            # circular last position from the ACTUAL start (Section 2)
            last_pos = ((sstart + c_i - 1) % S) if c_i > 0 else None
            acc.last_pos[i] = last_pos
            wraps = bool(c_i > 0 and sstart + c_i > S)
            prod_time = Fraction(c_i, rates_int[i])
            acc.productive_t[i] += prod_time
            acc.active_t[i] += eff_end
            acc.completion_times.append(float(Fraction(S, rates_int[i])))
            reached = (is_accepted and i == winner["miner"])
            spr = ("solution_found" if reached else "simulation_cutoff" if not completed
                   else "template_refreshed" if status == STATUS_FOUND else "range_exhausted")
            acc.stop_reason[i] = spr
            if status == STATUS_EXHAUSTED and completed:
                acc.m_exhaust[i] += 1
            if not completed:
                life = "simulation_cutoff"
            elif is_accepted:
                life = "winner_received" if i in disc_by_miner else "no_reachable_solution"
            else:
                life = "no_reachable_solution"
            if acc.gen_rows is not None:
                md = disc_by_miner.get(i)
                own_pos = (int(md["q"]) if md else None)
                own_t = (float(md["time"]) if md else None)
                gen_rows[i] = dict(
                    run_id=None, template_generation_id=gen_id, miner_id=i,
                    template_id=f"tmpl-{gen_id}", assigned_range_start=0,
                    assigned_range_end=int(S - 1), assigned_range_size=int(S),
                    search_start_position=int(sstart),
                    candidates_evaluated_this_generation=int(c_i),
                    cumulative_candidates_evaluated=int(acc.searched_cum[i]),
                    last_evaluated_position=last_pos,
                    unsearched_candidates_this_generation=int(S - c_i),
                    inactive_candidates_this_generation=0,
                    productive_search_time_s=float(prod_time), active_nonproductive_time_s=float(eff_end - prod_time),
                    idle_time_s=0.0, offline_time_s=0.0,
                    earliest_solution_position=own_pos, earliest_solution_time_s=own_t,
                    earliest_solution_identity=(str(md["identity"]) if md else None),
                    path_wraps_around=wraps, path_end_position=last_pos,
                    circular_candidates_evaluated=int(c_i),
                    search_progress_reason=spr, stop_reason=life,
                    completed_range=bool(c_i >= S),
                    generated_block_id=None, received_winner_time_s=None,
                    propagation_delay_s=None, delivery_stream_key=None,
                    potential_old_parent_solution_position=own_pos,
                    potential_old_parent_solution_time_s=own_t,
                    found_competing_solution_before_receipt=False,
                    produced_stale_block=False, stale_block_id=None)
        for i in inactive:
            acc.offline_t[i] += eff_end
            acc.stop_reason[i] = "inactive"
            if acc.gen_rows is not None:
                gen_rows[i] = dict(
                    run_id=None, template_generation_id=gen_id, miner_id=i,
                    template_id=f"tmpl-{gen_id}", assigned_range_start=0,
                    assigned_range_end=int(S - 1), assigned_range_size=int(S),
                    search_start_position=(None if is_b2 else 0),   # B2 inactive: null start
                    candidates_evaluated_this_generation=0, cumulative_candidates_evaluated=0,
                    last_evaluated_position=None, unsearched_candidates_this_generation=0,
                    inactive_candidates_this_generation=int(S),
                    productive_search_time_s=0.0, active_nonproductive_time_s=0.0,
                    idle_time_s=0.0, offline_time_s=float(eff_end),
                    earliest_solution_position=None, earliest_solution_time_s=None,
                    earliest_solution_identity=None,
                    path_wraps_around=False, path_end_position=None,
                    circular_candidates_evaluated=0,
                    search_progress_reason="inactive", stop_reason="inactive",
                    completed_range=False,
                    generated_block_id=None, received_winner_time_s=None,
                    propagation_delay_s=None, delivery_stream_key=None,
                    potential_old_parent_solution_position=None,
                    potential_old_parent_solution_time_s=None,
                    found_competing_solution_before_receipt=False,
                    produced_stale_block=False, stale_block_id=None)

        if not active_ids:
            gen_distinct = 0
        elif is_b1:
            gen_distinct = _completed(max_rate, eff_end, S)
        else:
            # EXACT circular union from the SAME exact per-miner lengths (no float).
            covx = _cov.b2_coverage_exact(starts, active_lengths, S)
            assert int(covx["total_candidate_evaluations"]) == gen_total   # rows == network total
            gen_distinct = int(covx["distinct_candidate_evaluations"])
        acc.total_evals += gen_total
        acc.distinct_evals += gen_distinct
        acc.duplicate_evals += (gen_total - gen_distinct)

        block_id = None
        stale_block_count = actual_comp = actual_prop = pot_comp = 0
        stale_pids = []
        if is_accepted:
            acc.accepted += 1
            block_id = f"blk-{acc.accepted}"
            race, producers, stale_block_ids, actual_prop, actual_comp, stale_block_count, \
                delivery_info = _record_stale_race(
                    acc, cfg, gen_id, parent_before, block_id, discoveries, disc_by_miner,
                    active_ids, rates_int, S, winner["time"], False, None)
            pot_comp = race["potential_competitor_miner_count"]
            stale_pids = [int(p["miner"]) for p in producers]
            _patch_winner_and_deliveries(gen_rows if acc.gen_rows is not None else None,
                                         winner, block_id, delivery_info)
            refresh_cause = "accepted_block"
        elif is_exhausted:
            acc.exhausted += 1
            acc.template_refresh += 1
            refresh_cause = "active_domain_exhausted"
        else:
            acc.partials += 1
            refresh_cause = "simulation_cutoff"

        if acc.gen_rows is not None:
            acc.gen_rows.extend(gen_rows[i] for i in range(n) if i in gen_rows)

        if acc.per_template is not None:
            acc.per_template.append(dict(
                run_id=None, round_id=acc.accepted, template_generation_id=gen_id,
                parent_block_id=parent_before, template_id=f"tmpl-{gen_id}",
                target=p, mu=cfg.mu, assigned_domain_size=S,
                searched_domain_size=min(S, gen_distinct), inactive_domain_size=0,
                unsearched_domain_size=S - min(S, gen_distinct),
                total_template_solution_count=k, active_range_solution_count=k,
                inactive_range_solution_count=0, discoverable_finder_count=len(discoveries),
                total_template_solution_position_count=k,
                active_range_solution_position_count=k, inactive_range_solution_position_count=0,
                distinct_potential_finder_miner_count=len(discoveries),
                potential_competitor_miner_count=(pot_comp if is_accepted else 0),
                actual_proposal_miner_count=actual_prop,
                actual_competitor_miner_count=actual_comp,
                actual_stale_producer_miner_count=stale_block_count,
                stale_block_count=stale_block_count,
                single_height_stale_block_count=stale_block_count,
                height_has_any_stale=bool(stale_block_count > 0),
                stale_producer_miner_ids=list(stale_pids),
                stale_block_ids=[f"stale-{block_id}-m{m}" for m in stale_pids],
                legitimate_stale_block_count=stale_block_count,
                solution_count=k, finder_count=(1 if is_accepted else 0),
                accepted_block_id=block_id, exhausted=is_exhausted, partial=is_partial,
                completed=completed, accepted=is_accepted, refresh_required=(not is_accepted),
                status=final_status, refresh_cause=refresh_cause,
                start_time_s=float(t), end_time_s=float(t + eff_end), duration_s=float(eff_end),
                exhausted_time_s=(float(eff_end) if is_exhausted else 0.0),
                active_domain_completion_time_s=(float(t_end) if is_exhausted else None),
                partial_cutoff_time_s=(float(eff_end) if is_partial else None),
                exact_exhaustion_verified=(bool(b2_exh["exact_exhaustion_verified"])
                                           if b2_exh is not None else None),
                b2_exhaustion_time_fraction_numerator=(b2_exh["b2_exhaustion_time_fraction_numerator"]
                                                       if b2_exh is not None else None),
                b2_exhaustion_time_fraction_denominator=(b2_exh["b2_exhaustion_time_fraction_denominator"]
                                                         if b2_exh is not None else None),
                previous_candidate_event_time_s=(b2_exh["previous_candidate_event_time_s"]
                                                 if b2_exh is not None else None),
                coverage_before_exhaustion=(b2_exh["coverage_before_exhaustion"]
                                            if b2_exh is not None else None),
                coverage_at_exhaustion=(b2_exh["coverage_at_exhaustion"]
                                        if b2_exh is not None else None),
                legitimate_competitor_count=actual_comp, obsolete_event_rejection_count=0))
        if acc.block_log is not None and is_accepted:
            acc.block_log.append(dict(block_index=acc.accepted, t_start_s=float(t),
                                      duration_s=float(eff_end), winner_id=int(winner["miner"]),
                                      winner_time_s=float(t_end), solutions_found=k,
                                      competitors=actual_comp, stale_blocks=stale_block_count,
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
    # SINGLE_HEIGHT_STALE_RACE_DIAGNOSTIC (Sections 1,8): one stale per non-winning
    # MINER per height, many distinct miners may stale one height (0..N_active-1, no
    # global cap); a secondary diagnostic, isolated from the primary metrics.
    stales = acc.single_height_stale_blocks
    all_valid = acc.accepted + stales
    sh_per_block = (stales / acc.accepted) if has_blocks else None
    sh_fraction = (stales / all_valid) if all_valid > 0 else None

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
        # --- SINGLE-HEIGHT STALE-RACE DIAGNOSTIC (secondary; Sections 1,2,8) ---
        # one stale per MINER per height; a height may carry several distinct stales.
        single_height_stale_race_diagnostic=True,
        stale_block_count=stales,                               # total admitted stale blocks
        single_height_stale_block_count=stales,
        heights_with_any_stale=acc.heights_with_any_stale,      # boolean indicator sum (not a substitute)
        accepted_heights=acc.accepted,
        # canonical single_height_ denominators (Section 8)
        single_height_stales_per_accepted_block=sh_per_block,
        single_height_stales_per_accepted_block_na_reason=block_na,
        single_height_stale_fraction_of_valid_proposals=sh_fraction,
        single_height_stale_fraction_na_reason=(None if all_valid > 0 else "no_valid_proposals"),
        # DEPRECATED aliases (explicit mapping to the single_height_ names)
        legitimate_stale_block_count=stales,                    # == single_height_stale_block_count
        stale_blocks=stales,                                    # == single_height_stale_block_count
        legitimate_stale_count=stales,                          # == single_height_stale_block_count
        stales_per_accepted_block=sh_per_block,                 # == single_height_stales_per_accepted_block
        stales_per_accepted_block_na_reason=block_na,
        stale_fraction_of_all_valid_blocks=sh_fraction,         # == single_height_stale_fraction_of_valid_proposals
        stale_fraction_na_reason=(None if all_valid > 0 else "no_valid_proposals"),
        legitimate_stale_rate=sh_per_block,                     # == single_height_stales_per_accepted_block
        legitimate_stale_rate_na_reason=(None if has_blocks else "no_valid_proposals"),
        deprecated_stale_alias_map={
            "legitimate_stale_block_count": "single_height_stale_block_count",
            "stale_blocks": "single_height_stale_block_count",
            "legitimate_stale_count": "single_height_stale_block_count",
            "stales_per_accepted_block": "single_height_stales_per_accepted_block",
            "stale_fraction_of_all_valid_blocks": "single_height_stale_fraction_of_valid_proposals",
            "legitimate_stale_rate": "single_height_stales_per_accepted_block"},
        # actual vs potential taxonomy (Section 3)
        distinct_potential_finder_miner_count=acc.potential_finders,
        potential_competitor_miner_count=acc.potential_competitor_miners,
        actual_competitor_miner_count=acc.actual_competitor_miners,
        actual_proposal_miner_count=acc.actual_proposal_miners,
        actual_stale_producer_miner_count=acc.actual_stale_producer_miners,
        # post-winner diagnostic work reported SEPARATELY, NEVER integrated into
        # primary metrics (5B1G.1 §4). post_winner_* covers EVERY active non-winner;
        # stale_producer_postwinner_* is the producer-only subset.
        post_winner_candidate_evaluations=acc.post_winner_candidate_evaluations,
        post_winner_active_time_s=float(acc.post_winner_active_time),
        post_winner_energy_not_integrated=True,
        stale_producer_postwinner_candidate_evaluations=acc.stale_producer_postwinner_candidate_evaluations,
        stale_producer_postwinner_active_time_s=float(acc.stale_producer_postwinner_active_time),
        # retained legacy names — defined to EQUAL the COMPLETE post-winner totals
        # (all active non-winners), NOT the producer-only subset.
        stale_race_candidate_evaluations=acc.post_winner_candidate_evaluations,
        stale_race_active_time_s=float(acc.post_winner_active_time),
        stale_race_energy_not_integrated=True,
        # main-block vs stale-block propagation counted separately (Section 5)
        main_block_propagation_message_count=acc.main_block_prop_msgs,
        main_block_propagation_bytes=acc.main_block_prop_bytes,
        stale_block_propagation_message_count=acc.stale_block_prop_msgs,
        stale_block_propagation_bytes=acc.stale_block_prop_bytes,
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
        result["stale_race_records"] = acc.stale_race_records
        result["delivery_delay_records"] = acc.delivery_delay_records
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
