"""Stage 4 scientific baselines B0-B3 and C1-C2 as a direct, small-scale
candidate-header search model (for dry-run semantic validation, NOT the final
Stage-5 matrix).

Each scenario is one round on a finite domain of `S` candidate positions with N
miners. We track the exact candidate-header identity every miner evaluates,
duplicate evaluations, range overlap, and explicit active/idle/coordination
energy. This isolates the mechanisms:

  B0  Independent-template PoW abstraction   -> distinct templates, 0 duplicates
  B1  Common-template uncoordinated PoW      -> heavy duplicate evaluations
  B2  Common-template randomized-start PoW   -> reduced overlap
  B3  Common-template disjoint-range, continuous -> 0 overlap, continuous active
  C1  PoCol continuous                       -> == B3 in the simulator (see note)
  C2  PoCol post-range idle                  -> active-to-idle after range done

Candidate-header identity (duplicate iff ALL equal):
  (template_id, template_generation_id, parent_id, height, extranonce, nonce)

Key honest findings this model makes measurable:
  * eliminating duplicates does NOT by itself reduce total energy (miners hash
    the same wall-clock time); it improves domain COVERAGE (energy per block);
  * the C2 idle saving is exactly Sum_i idle_time_i * (P_active_i - P_idle_i)
    and is ZERO when every miner's range completes no earlier than the round end
    (e.g. homogeneous equal ranges with mu>=1). It is non-zero only when a miner
    finishes its assigned range before the round ends.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Tuple
import hashlib
import json

SCENARIOS = ["B0", "B1", "B2", "B3", "C1", "C2"]
J_PER_KWH = 3_600_000.0
HASHES_PER_TH = 1e12

# scenario -> (common_template?, allocation, note)
COMMON_TEMPLATE = {"B0": False, "B1": True, "B2": True, "B3": True, "C1": True, "C2": True}
ALLOCATION = {"B0": "independent", "B1": "from_zero", "B2": "randomized_start",
              "B3": "disjoint", "C1": "disjoint", "C2": "disjoint"}
IDLE_POLICY = {"B0": False, "B1": False, "B2": False, "B3": False, "C1": False, "C2": True}


@dataclass
class ScenarioConfig:
    scenario_id: str
    seed: int
    miner_count: int
    domain_size: int                 # S (candidate positions this round)
    p: float                         # per-header success probability
    network_hash_rate_hps: float
    efficiency_j_per_th: float = 21.5
    round_duration_s: float = 600.0  # B
    idle_power_ratio: float = 0.0    # P_idle = ratio * P_active (0 == lower bound)
    coordination_energy_kwh: float = 0.0
    hash_rate_shares: Optional[List[float]] = None   # sums to 1; default homogeneous
    parent_id: int = 0
    height: int = 1
    template_generation_id: int = 0

    def resolved_shares(self) -> List[float]:
        if self.hash_rate_shares is not None:
            s = list(self.hash_rate_shares)
            tot = sum(s)
            return [x / tot for x in s]
        return [1.0 / self.miner_count] * self.miner_count

    def config_hash(self) -> str:
        d = asdict(self); d["hash_rate_shares"] = self.resolved_shares()
        return hashlib.sha256(json.dumps(d, sort_keys=True).encode()).hexdigest()[:16]


def _rates_hps(cfg: ScenarioConfig) -> List[float]:
    return [sh * cfg.network_hash_rate_hps for sh in cfg.resolved_shares()]


def _ranges(cfg: ScenarioConfig) -> List[Tuple[int, int]]:
    """Disjoint [start, end_inclusive) ranges over [0, S) proportional to shares."""
    S = cfg.domain_size
    shares = cfg.resolved_shares()
    lengths = [max(int(sh * S), 1) for sh in shares]
    drift = S - sum(lengths)
    lengths[-1] = max(lengths[-1] + drift, 1)
    out = []
    start = 0
    for L in lengths:
        out.append((start, start + L - 1))
        start += L
    return out


def simulate_round(cfg: ScenarioConfig) -> dict:
    """Direct per-round simulation returning semantic + energy metrics."""
    import numpy as np
    g = np.random.default_rng(cfg.seed)
    N = cfg.miner_count
    S = cfg.domain_size
    B = cfg.round_duration_s
    rates = _rates_hps(cfg)
    eff_j_per_hash = cfg.efficiency_j_per_th / HASHES_PER_TH
    active_power_w = [r * eff_j_per_hash for r in rates]
    idle_power_w = [cfg.idle_power_ratio * ap for ap in active_power_w]

    # per-miner evaluation budget in this round (headers it can hash in B seconds)
    budget = [max(int(r * B), 1) for r in rates]

    # ---- assign candidate-header identities per policy ----
    # identity key excludes miner id: duplicates are cross-miner identical headers.
    seen = {}                       # identity -> count
    total_evals = 0
    per_miner_headers = []          # list of nonce-position lists actually searched
    ranges = _ranges(cfg)
    for i in range(N):
        if ALLOCATION[cfg.scenario_id] == "independent":
            # B0: unique template per miner -> identities never collide cross-miner
            template = ("B0", i)
            nonces = list(range(min(budget[i], S)))
        elif ALLOCATION[cfg.scenario_id] == "from_zero":
            # B1: common template, everyone hashes nonces 0..budget-1
            template = ("common", cfg.template_generation_id)
            nonces = list(range(min(budget[i], S)))
        elif ALLOCATION[cfg.scenario_id] == "randomized_start":
            # B2: common template, randomized start with wraparound
            template = ("common", cfg.template_generation_id)
            start = int(g.integers(0, S))
            nonces = [(start + j) % S for j in range(min(budget[i], S))]
        else:  # disjoint (B3/C1/C2)
            template = ("common", cfg.template_generation_id)
            a, b = ranges[i]
            span = b - a + 1
            nonces = [a + j for j in range(min(budget[i], span))]
        per_miner_headers.append(nonces)
        for nonce in nonces:
            key = (template, cfg.template_generation_id, cfg.parent_id, cfg.height, 0, nonce)
            seen[key] = seen.get(key, 0) + 1
            total_evals += 1

    distinct = len(seen)
    duplicate_evals = total_evals - distinct
    overlap_headers = sum(1 for v in seen.values() if v > 1)

    # ---- energy: explicit active/idle state durations ----
    active_time = []
    idle_time = []
    for i in range(N):
        span = (ranges[i][1] - ranges[i][0] + 1) if ALLOCATION[cfg.scenario_id] == "disjoint" else S
        range_completion_s = span / max(rates[i], 1e-12)     # time to exhaust the assignment
        if IDLE_POLICY[cfg.scenario_id]:
            # C2: active until the assignment is exhausted, then idle to round end
            at = min(range_completion_s, B)
            it = max(0.0, B - at)
        else:
            # B0-B3, C1: continuous -> active the whole round (refresh if exhausted)
            at = B
            it = 0.0
        active_time.append(at)
        idle_time.append(it)

    active_energy_j = sum(active_power_w[i] * active_time[i] for i in range(N))
    idle_energy_j = sum(idle_power_w[i] * idle_time[i] for i in range(N))
    coord_j = cfg.coordination_energy_kwh * J_PER_KWH
    total_energy_kwh = (active_energy_j + idle_energy_j + coord_j) / J_PER_KWH

    # ---- finders (exact per-range Binomial, for reference) ----
    finders = 0
    for i in range(N):
        span = len(per_miner_headers[i])
        if span > 0:
            finders += int(g.binomial(span, cfg.p))

    return dict(
        scenario_id=cfg.scenario_id, seed=cfg.seed, miners=N, domain_size=S,
        config_hash=cfg.config_hash(),
        total_candidate_evaluations=total_evals,
        distinct_candidate_identities=distinct,
        duplicate_evaluations=duplicate_evals,
        duplicate_rate=(duplicate_evals / total_evals) if total_evals else 0.0,
        overlap_headers=overlap_headers,
        unsearched_candidates=max(0, S - distinct) if COMMON_TEMPLATE[cfg.scenario_id] else 0,
        active_energy_kwh=active_energy_j / J_PER_KWH,
        idle_energy_kwh=idle_energy_j / J_PER_KWH,
        coordination_energy_kwh=cfg.coordination_energy_kwh,
        total_energy_kwh=total_energy_kwh,
        total_active_time_s=sum(active_time),
        total_idle_time_s=sum(idle_time),
        finders=finders,
        idle_policy=IDLE_POLICY[cfg.scenario_id],
        common_template=COMMON_TEMPLATE[cfg.scenario_id],
    )
