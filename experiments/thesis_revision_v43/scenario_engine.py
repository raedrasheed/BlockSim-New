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
from experiments.thesis_revision_v43.schemas import OUTPUT_SCHEMA_VERSION

ENGINE_VERSION = "5b1a.1"

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


def run_scenario(cfg: EngineConfig, emit_log: bool = False, emit_detail: bool = False) -> dict:
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
    m_generations = np.zeros(n, dtype=np.int64)       # template generations participated
    m_range_exhaust = np.zeros(n, dtype=np.int64)     # times this miner finished its range with no solution
    m_idle_entries = np.zeros(n, dtype=np.int64)      # in-loop idle entries
    inactive_count = sum((ranges_all[i][1] - ranges_all[i][0] + 1) for i in inactive) if DISJOINT[cfg.scenario_id] else 0

    # coordination counters — per message category (Section 10). Only block
    # propagation is simulated; the other categories are declared with count 0 and
    # bytes null (not simulated) so nothing is fabricated.
    coord_cat = {c: dict(message_count=0, bytes=0 if c == "block_propagation" else None)
                 for c in ("block_propagation", "transaction_reconciliation",
                           "template_announcement", "nonce_allocation", "registration")}
    template_refresh_count = 0
    nonce_allocation_event_count = 0

    per_template = [] if emit_detail else None
    gen_counter = 0
    last_block_id = "genesis"

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
    active_dom = S - inactive_count if DISJOINT[cfg.scenario_id] else S
    while t < BIG:
        # ---- one accepted block = possibly several exhausted template generations ----
        tgen = 0
        round_start = t
        while True:
            nonce_allocation_event_count += 1
            k = int(r_solk.binomial(S, p))
            if k > 0:
                # unique solution positions
                pos = np.unique(r_solpos.integers(0, S, size=k * 2))[:k]
                if pos.size:
                    break
            exhausted_rounds += 1
            tgen += 1
            template_refresh_count += 1
            gen_counter += 1
            for i in active_ids:
                m_range_exhaust[i] += 1
            if emit_detail:
                per_template.append(dict(
                    run_id=None, round_id=accepted, template_generation_id=gen_counter,
                    parent_block_id=last_block_id, template_id=f"tmpl-{gen_counter}",
                    target=p, mu=cfg.mu, assigned_domain_size=S,
                    searched_domain_size=active_dom, unsearched_domain_size=S - active_dom,
                    inactive_domain_size=inactive_count, solution_count=0, finder_count=0,
                    accepted_block_id=None, exhausted=True, refresh_cause="no_solution_in_domain",
                    start_time_s=round_start, end_time_s=round_start,
                    legitimate_competitor_count=0, obsolete_event_rejection_count=0))
            if tgen > MAX_REFRESH:
                pos = np.array([], dtype=np.int64)
                break

        # ---- discovery time per solution, per scenario ----
        winner_time, winner_id, round_searched, round_total, round_distinct = _discover(
            cfg, pos, ranges_all, rates, active_ids, S, r_starts, H_active)
        # generation durations: tgen exhausted generations (full-domain search) + 1 success
        D_ex = S / H_active                        # exhausted-generation duration
        gen_success = winner_time
        round_dur = tgen * D_ex + gen_success
        if round_dur <= 0:
            round_dur = cfg.target_block_interval_s
        cap = BIG - t
        # ZERO-BLOCK FIX: a block is accepted only if the round COMPLETES within the
        # horizon. If not, miners spend the remaining time searching (energy still
        # accrues) but NO block is accepted -> honest zero-block outcome (esp. B1).
        completed = round_dur <= cap + 1e-9
        if not completed:
            scale = (cap / round_dur) if round_dur > 0 else 0.0
            D_ex *= scale; gen_success *= scale; round_dur = cap
        # ---- per-miner active/idle (per template generation) ----
        for i in range(n):
            if i in inactive:
                offline_t[i] += round_dur
                continue
            m_generations[i] += (tgen + 1)
            L_i = ranges_all[i][1] - ranges_all[i][0] + 1 if DISJOINT[cfg.scenario_id] else S
            tau_i = L_i / max(rates[i], 1e-12)     # nominal completion (decoupled from rate)
            completion_times.append(tau_i)
            if IDLE[cfg.scenario_id]:
                a = tgen * min(tau_i, D_ex) + min(tau_i, gen_success)
                idl = tgen * max(0.0, D_ex - tau_i) + max(0.0, gen_success - tau_i)
                active_t[i] += a
                idle_t[i] += idl
                if idl > 0:
                    m_idle_entries[i] += 1
            else:
                active_t[i] += round_dur            # continuous: refresh, always hashing
        total_evals += round_total
        distinct_evals += round_distinct
        duplicate_evals += (round_total - round_distinct)
        gen_counter += 1
        searched_dom = int(min(S, round(round_distinct)))

        if completed:
            accepted += 1
            block_id = f"blk-{accepted}"
            msgs = len(active_ids) - 1 if active_ids else 0
            coord_cat["block_propagation"]["message_count"] += max(msgs, 0)
            coord_cat["block_propagation"]["bytes"] += max(msgs, 0) * cfg.block_size_bytes
            legit = 0
            if len(pos) >= 2 and active_ids:
                second = float(np.partition(pos, 1)[1]) / max(rates[winner_id], 1e-12) if winner_id is not None else 0.0
                delay = float(r_delay.exponential(max(cfg.propagation_delay_mean_s, 1e-12)))
                if 0 < (second - winner_time) < delay:
                    legit_stales += 1
                    legit = 1
            if emit_detail:
                per_template.append(dict(
                    run_id=None, round_id=accepted, template_generation_id=gen_counter,
                    parent_block_id=last_block_id, template_id=f"tmpl-{gen_counter}",
                    target=p, mu=cfg.mu, assigned_domain_size=S,
                    searched_domain_size=searched_dom, unsearched_domain_size=S - searched_dom,
                    inactive_domain_size=inactive_count, solution_count=int(len(pos)),
                    finder_count=1 + legit, accepted_block_id=block_id, exhausted=False,
                    refresh_cause="accepted_block", start_time_s=round_start,
                    end_time_s=round_start + round_dur, legitimate_competitor_count=legit,
                    obsolete_event_rejection_count=0))
            last_block_id = block_id
            if emit_log:
                block_log.append(dict(
                    block_index=accepted, t_start_s=round_start, round_duration_s=round_dur,
                    winner_id=(int(winner_id) if winner_id is not None else None),
                    winner_time_s=winner_time, solutions_found=int(len(pos)),
                    exhausted_generations=tgen, round_total_evaluations=round_total,
                    round_distinct_evaluations=round_distinct, propagation_messages=max(msgs, 0)))
        else:
            # incomplete final generation: horizon reached, NO accepted block
            if emit_detail:
                per_template.append(dict(
                    run_id=None, round_id=accepted, template_generation_id=gen_counter,
                    parent_block_id=last_block_id, template_id=f"tmpl-{gen_counter}",
                    target=p, mu=cfg.mu, assigned_domain_size=S,
                    searched_domain_size=searched_dom, unsearched_domain_size=S - searched_dom,
                    inactive_domain_size=inactive_count, solution_count=int(len(pos)),
                    finder_count=0, accepted_block_id=None, exhausted=False,
                    refresh_cause="horizon_reached", start_time_s=round_start,
                    end_time_s=round_start + round_dur, legitimate_competitor_count=0,
                    obsolete_event_rejection_count=0))
        t += round_dur

    # ---- energy ----
    active_energy_kwh = float((active_power_w * active_t).sum()) / J_PER_KWH
    idle_energy_kwh = float((idle_power_w * idle_t).sum()) / J_PER_KWH
    coordination_energy_kwh = 0.0                  # excluded lower bound (idealized)
    total_energy_kwh = active_energy_kwh + idle_energy_kwh + coordination_energy_kwh

    dup_rate = (duplicate_evals / total_evals) if total_evals else 0.0
    comp = np.array(completion_times) if completion_times else np.array([0.0])

    # ---- coordination category counters (Section 10): block propagation is truly
    # simulated (count + bytes); other categories are counted abstractly, bytes null.
    n_generations = gen_counter
    scen = cfg.scenario_id
    coord_cat["nonce_allocation"]["message_count"] = n_generations if DISJOINT[scen] else 0
    coord_cat["template_announcement"]["message_count"] = n_generations if COMMON_TEMPLATE[scen] else 0
    coord_cat["transaction_reconciliation"]["message_count"] = accepted if AGREEMENT[scen] else 0
    coord_cat["registration"]["message_count"] = len(active_ids) if COMMON_TEMPLATE[scen] else 0
    cat_flat = {}
    for c, v in coord_cat.items():
        cat_flat[f"{c}_message_count"] = v["message_count"]
        cat_flat[f"{c}_bytes"] = v["bytes"]                    # null for all but block_propagation

    # ---- NA-aware block metrics (Section 4): undefined => null + reason ----
    has_blocks = accepted > 0
    block_na = None if has_blocks else "no_accepted_blocks"

    result = dict(
        output_schema_version=OUTPUT_SCHEMA_VERSION, engine_version=ENGINE_VERSION,
        scenario_id=cfg.scenario_id, seed=cfg.seed, miners=n, domain_size=S, p=p, mu=cfg.mu,
        allocation_policy=cfg.allocation_policy, hash_rate_distribution=cfg.hash_rate_distribution,
        idle_power_ratio=cfg.idle_power_ratio, inactive_fraction=cfg.inactive_miner_fraction,
        # primary outcomes
        total_energy_kwh=total_energy_kwh, active_energy_kwh=active_energy_kwh,
        idle_energy_kwh=idle_energy_kwh, coordination_energy_kwh=coordination_energy_kwh,
        accepted_blocks=accepted,
        block_metrics_defined=has_blocks,
        effective_block_interval_s=((BIG / accepted) if has_blocks else None),
        effective_block_interval_na_reason=block_na,
        energy_per_accepted_block_kwh=((total_energy_kwh / accepted) if has_blocks else None),
        energy_per_accepted_block_na_reason=block_na,
        # throughput numerator is genuinely zero when no blocks -> 0.0 is a real value
        throughput_blocks_per_s=(accepted / BIG if BIG else 0.0),
        # transactions are not modelled -> per-transaction metrics are NA by design
        energy_per_transaction_kwh=None,
        energy_per_transaction_na_reason="no_committed_transactions",
        confirmation_time_proxy_s=((BIG / accepted) if has_blocks else None),
        confirmation_time_proxy_na_reason=block_na,
        legitimate_stale_rate=((legit_stales / accepted) if has_blocks else None),
        legitimate_stale_rate_na_reason=(None if has_blocks else "no_valid_proposals"),
        legitimate_stale_count=legit_stales,
        duplicate_evaluation_rate=dup_rate, exhausted_rounds=exhausted_rounds,
        # domain / coverage
        total_candidate_evaluations=total_evals, distinct_candidate_identities=distinct_evals,
        duplicate_evaluations=duplicate_evals,
        # time
        total_active_time_s=float(active_t.sum()), total_idle_time_s=float(idle_t.sum()),
        total_offline_time_s=float(offline_t.sum()),
        completion_time_mean_s=float(comp.mean()), completion_time_std_s=float(comp.std()),
        # coordination (legacy flat keys kept for back-compat) + categorized keys
        coord_block_propagation_message_count=coord_cat["block_propagation"]["message_count"],
        coord_block_propagation_bytes=coord_cat["block_propagation"]["bytes"],
        coord_simulated_message_count=coord_cat["block_propagation"]["message_count"],
        coord_simulated_message_bytes=coord_cat["block_propagation"]["bytes"],
        coord_template_refresh_count=template_refresh_count,      # == exhausted_rounds
        coord_nonce_allocation_event_count=nonce_allocation_event_count,
        template_generations=n_generations,
        **cat_flat,
        # abstract (unimplemented) protocol activity: counts only, never bytes.
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
    if emit_detail:
        result["per_miner"] = _build_per_miner(
            cfg, n, rates, shares, ranges_all, inactive, active_power_w, idle_power_w,
            active_t, idle_t, offline_t, m_generations, m_range_exhaust, m_idle_entries)
        result["per_template"] = per_template
    return result


def _build_per_miner(cfg, n, rates, shares, ranges_all, inactive, active_power_w,
                     idle_power_w, active_t, idle_t, offline_t, m_generations,
                     m_range_exhaust, m_idle_entries):
    """Per-miner summary rows (Section 6). Sums reconcile to the network totals by
    construction (built from the same accumulators)."""
    disjoint = DISJOINT[cfg.scenario_id]
    out = []
    for i in range(n):
        a, b = ranges_all[i]
        L_i = (b - a + 1) if disjoint else int(cfg.domain_size())
        is_inactive = i in inactive
        searched = 0 if is_inactive else L_i           # active miner covers its range each generation
        state = "offline" if is_inactive else ("idled" if m_idle_entries[i] > 0 else "active")
        reasons = {}
        if m_range_exhaust[i]:
            reasons["range_exhausted_no_solution"] = int(m_range_exhaust[i])
        if m_idle_entries[i]:
            reasons["entered_idle"] = int(m_idle_entries[i])
        out.append(dict(
            run_id=None, miner_id=i, hash_rate_hps=float(rates[i]),
            hash_rate_share=float(shares[i]), allocation_policy=cfg.allocation_policy,
            range_start=int(a), range_end=int(b), range_size=int(L_i) if disjoint else None,
            searched_count=int(searched) if disjoint else None,
            unsearched_count=int(L_i - searched) if disjoint else None,
            inactive_count=(L_i if (is_inactive and disjoint) else 0),
            active_time_s=float(active_t[i]), idle_time_s=float(idle_t[i]),
            offline_time_s=float(offline_t[i]),
            active_energy_kwh=float(active_power_w[i] * active_t[i]) / J_PER_KWH,
            idle_energy_kwh=float(idle_power_w[i] * idle_t[i]) / J_PER_KWH,
            template_generations_participated=int(m_generations[i]),
            range_exhaustion_count=int(m_range_exhaust[i]),
            idle_entry_count=int(m_idle_entries[i]), final_state=state,
            state_transition_reason_counts=reasons))
    return out


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
        # random starts, single forward traversal; EXACT circular interval-union
        # coverage (coverage.py). Integer candidate counts, no domain enumeration.
        starts_list = [int(r_starts.integers(0, S)) for _ in active_ids]
        rates_list = [float(rates[i]) for i in active_ids]
        winner_time, widx = _cov.b2_winner(pos, starts_list, rates_list, S)
        if widx is None or not math.isfinite(winner_time):
            return S / H_active, (active_ids[0] if active_ids else None), None, 0.0, 0.0
        best_id = active_ids[widx]
        lengths = _cov.lengths_from_winner_time(winner_time, rates_list, S)
        cov = _cov.b2_coverage_exact(starts_list, lengths, S)
        return (winner_time, best_id, None,
                float(cov["total_candidate_evaluations"]),
                float(cov["distinct_candidate_evaluations"]))
    # fallback
    return S / H_active, active_ids[0], None, 0.0, 0.0
