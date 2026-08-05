"""Stage-8U matched same-template PoW control (ADDITIVE — no legacy PoW code touched).

The Phase-0 audit (STAGE_08U_POW_BASELINE_AUDIT.md) found no existing PoW implementation
that can be fairly matched to the accepted PoCol Stage-2 engine.  This module implements
the matched control from the accepted primitives themselves:

* the SAME immutable per-round template stream — ``make_template(f"round-{{k}}",
  difficulty, D, template_seed + k)`` with k = 1, 2, ... exactly as the engine commits
  templates (``simulator.py``: ``rid = f"round-{{run_ctx.round_seq}}"``, seed
  ``cfg.template_seed + run_ctx.round_seq`` with a pre-incremented 1-based sequence);
* the SAME SHA-256 work primitive, fixed target (``target_for_difficulty``), fixed
  difficulty, nonce-domain size, horizon, batch size, actual per-miner hash rates and
  power values;
* the SAME block-acceptance point: the FIRST valid target-coupled solution by simulation
  time wins the round (the engine seats acceptance at the winning nonce's exact per-nonce
  completion time inside its planned batch — mirrored here);
* the SAME stale-event cancellation discipline at acceptance: work not committed strictly
  before the acceptance time performs no effect (the engine's in-flight planned batches
  commit zero work once the round is terminal — mirrored here);
* NO dynamic difficulty anywhere.

The one deliberate difference IS the treatment: PoW miners do not coordinate.  Every
mining node searches the FULL nonce domain independently, starting from a deterministic
seed-derived offset with wraparound; overlap is allowed and measured
(``total/unique/duplicate_physical_evaluations``).

Declared closure rules (documented modelling choices, deterministic under exact rational
arithmetic — all times are ``fractions.Fraction``):

* BLOCK: the round closes at the first valid solution's exact completion time.  Work not
  strictly earlier is cancelled (acceptance cancels stale work); the winner's final
  partial batch commits exactly through the winning nonce.  Ties are broken
  deterministically by (time, MinerID string, nonce).
* EXHAUSTED: with no solution in the domain, the round closes when the FIRST miner
  completes full-domain coverage (its own coverage proves the domain empty — the
  protocol-level analogue of the engine's full-domain exhaustion closure; this is the
  PoW-favourable minimal rule and is recorded as a declared assumption).  Exhaustion is
  not an acceptance, so whole batches completing exactly AT the closure time commit.
* HORIZON: the final round is truncated at the horizon; whole batches completing at or
  before the horizon commit; no block.

Oracle scans (the per-template solution set) determine ONLY timing/closure — exactly as
the engine's ``_first_solution_in`` planning scan — and are never counted as physical
evaluations.  Physical evaluations count only causally committed work, so
``post_round_evaluation_count == 0`` holds by construction and is still recorded and
asserted.  Energy is the accepted wall-clock residency model: mining nodes hold
ACTIVE_HASHING for the whole horizon (PoW never idles); W01 standby nodes hold
RESERVE_STANDBY at ``P_reserve`` for the whole horizon.  The energy and residency
identities are computed and their residuals recorded.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
from typing import Any, Dict, List, Optional, Sequence, Tuple
import hashlib

from .search import Template, make_template, target_for_difficulty

J_PER_KWH = 3.6e6

POW_SCENARIO_KINDS = ("POW_POPULATION_MATCHED", "POW_ACTIVE_CAPACITY_MATCHED")


@dataclass(frozen=True)
class MatchedPoWConfig:
    """Frozen configuration of one matched same-template PoW control run."""

    scenario_id: str
    scenario_kind: str                    # one of POW_SCENARIO_KINDS
    difficulty: int
    nonce_domain_size: int
    horizon_seconds: float
    batch_size: int
    template_seed: int
    master_seed: int
    miner_ids: Tuple[str, ...]            # mining nodes (search the full domain)
    hash_rates: Tuple[float, ...]         # actual per-miner rates, aligned to miner_ids
    standby_ids: Tuple[str, ...] = ()     # W01: non-mining standby nodes at P_reserve
    P_hash: float = 21.5
    P_reserve: float = 2.15

    def __post_init__(self) -> None:
        if self.scenario_kind not in POW_SCENARIO_KINDS:
            raise ValueError(f"unsupported PoW scenario kind: {self.scenario_kind!r}")
        if len(self.miner_ids) != len(self.hash_rates):
            raise ValueError("miner_ids and hash_rates must align")
        if not self.miner_ids:
            raise ValueError("at least one mining node is required")
        for r in self.hash_rates:
            if r <= 0 or float(r) != float(int(r)):
                raise ValueError("hash rates must be positive integral nonces/second")
        if self.nonce_domain_size <= 0 or self.batch_size <= 0 or self.difficulty <= 0:
            raise ValueError("domain, batch size and difficulty must be positive")

    @property
    def target(self) -> int:
        return target_for_difficulty(self.difficulty)


def pow_start_offset(master_seed: int, round_index: int, miner_id: str,
                     domain: int) -> int:
    """Deterministic seed-derived full-domain starting offset for one miner and round."""
    h = hashlib.sha256(
        f"pow-offset|{master_seed}|{round_index}|{miner_id}".encode()).digest()
    return int.from_bytes(h[:8], "big") % domain


def _ceil_frac(x: Fraction) -> int:
    """Exact ceiling of a non-negative Fraction."""
    return -((-x.numerator) // x.denominator)


def _floor_frac(x: Fraction) -> int:
    """Exact floor of a non-negative Fraction."""
    return x.numerator // x.denominator


def _circular_union_size(arcs: Sequence[Tuple[int, int]], domain: int) -> int:
    """Exact size of the union of circular arcs (start, length) on Z_domain."""
    ivs: List[Tuple[int, int]] = []
    for start, length in arcs:
        if length <= 0:
            continue
        if length >= domain:
            return domain
        s = start % domain
        e = s + length
        if e <= domain:
            ivs.append((s, e))
        else:
            ivs.append((s, domain))
            ivs.append((0, e - domain))
    if not ivs:
        return 0
    ivs.sort()
    total = 0
    cur_s, cur_e = ivs[0]
    for s, e in ivs[1:]:
        if s <= cur_e:
            cur_e = max(cur_e, e)
        else:
            total += cur_e - cur_s
            cur_s, cur_e = s, e
    total += cur_e - cur_s
    return total


@dataclass
class PoWRoundRecord:
    """One matched-PoW round: identity, closure, winner and evaluation accounting."""

    round_index: int
    RoundID: str
    TemplateID: str
    start_time: float
    close_time: float
    close_kind: str                       # BLOCK | EXHAUSTED | HORIZON
    solutions_in_domain: int
    winner_miner_id: Optional[str] = None
    winning_nonce: Optional[int] = None
    winner_offset: Optional[int] = None
    total_physical_evaluations: int = 0
    unique_physical_evaluations: int = 0
    duplicate_physical_evaluations: int = 0
    evaluations_by_miner: Dict[str, int] = field(default_factory=dict)

    @property
    def duration(self) -> float:
        return self.close_time - self.start_time


def _round_solutions(tpl: Template) -> List[int]:
    """ORACLE scan of the whole domain (timing/closure determination only — exactly like
    the engine's planning scan; never counted as physical evaluations)."""
    return [v for v in range(tpl.nonce_domain_size) if tpl.is_solution(v)]


def run_matched_pow(cfg: MatchedPoWConfig) -> Dict[str, Any]:
    """Execute one matched same-template PoW control run (exact rational timing)."""
    D = cfg.nonce_domain_size
    batch = cfg.batch_size
    horizon = Fraction(cfg.horizon_seconds).limit_denominator(10**9)
    rates = [int(r) for r in cfg.hash_rates]
    miners = list(cfg.miner_ids)
    max_rate = max(rates)
    rounds: List[PoWRoundRecord] = []
    first_valid_solutions: List[Dict[str, Any]] = []
    T = Fraction(0)
    k = 0
    while T < horizon:
        k += 1
        rid = f"round-{k}"
        tpl = make_template(RoundID=rid, difficulty=cfg.difficulty,
                            nonce_domain_size=D, seed=cfg.template_seed + k)
        assert tpl.target == cfg.target, "the fixed target must never vary per round"
        offsets = {mid: pow_start_offset(cfg.master_seed, k, mid, D) for mid in miners}
        sols = _round_solutions(tpl)
        # ---- closure determination (exact rational times, relative to round start) ----
        winner: Optional[Tuple[Fraction, str, int]] = None
        if sols:
            for mid, rate in zip(miners, rates):
                o = offsets[mid]
                for v in sols:
                    pos = (v - o) % D                 # 0-indexed position in search order
                    t_v = Fraction(pos + 1, rate)     # exact per-nonce completion time
                    cand = (t_v, str(mid), v)
                    if winner is None or cand < winner:
                        winner = cand
            close_rel, win_mid, win_nonce = winner
            kind = "BLOCK"
        else:
            close_rel = Fraction(D, max_rate)         # first full-domain coverage closes
            win_mid, win_nonce = None, None
            kind = "EXHAUSTED"
        truncated = T + close_rel > horizon
        if truncated:
            close_abs = horizon
            kind = "HORIZON"
            win_mid, win_nonce = None, None
        else:
            close_abs = T + close_rel
        window = close_abs - T
        # ---- causal evaluation accounting (committed work only) -----------------------
        evals: Dict[str, int] = {}
        arcs: List[Tuple[int, int]] = []
        for mid, rate in zip(miners, rates):
            if kind == "BLOCK":
                if mid == win_mid:
                    n = ((win_nonce - offsets[mid]) % D) + 1   # through the winning nonce
                else:
                    # whole batches completing STRICTLY before the acceptance time commit;
                    # acceptance cancels everything else (stale-event cancellation).
                    x = window * rate / batch
                    n = min(D, max(0, (_ceil_frac(x) - 1)) * batch)
            else:
                # EXHAUSTED / HORIZON closures are not acceptances: whole batches
                # completing at or before the closure time commit.
                x = window * rate / batch
                n = min(D, _floor_frac(x) * batch)
            evals[mid] = n
            arcs.append((offsets[mid], n))
        total = sum(evals.values())
        unique = _circular_union_size(arcs, D)
        rec = PoWRoundRecord(
            round_index=k, RoundID=rid, TemplateID=tpl.TemplateID,
            start_time=float(T), close_time=float(close_abs), close_kind=kind,
            solutions_in_domain=len(sols), winner_miner_id=win_mid,
            winning_nonce=win_nonce,
            winner_offset=(offsets[win_mid] if win_mid is not None else None),
            total_physical_evaluations=total, unique_physical_evaluations=unique,
            duplicate_physical_evaluations=total - unique, evaluations_by_miner=evals)
        rounds.append(rec)
        if kind == "BLOCK":
            first_valid_solutions.append({
                "round_index": k, "RoundID": rid, "winner_miner_id": win_mid,
                "winning_nonce": win_nonce, "accepted_at": float(close_abs)})
        T = close_abs
        if truncated:
            break
    # ---- energy + residency (wall-clock model; identities computed, residuals kept) ---
    horizon_f = float(horizon)
    residency: Dict[str, Dict[str, float]] = {}
    energy_by_state = {"ACTIVE_HASHING": 0.0, "RESERVE_STANDBY": 0.0}
    energy_total_j = 0.0
    for mid in miners:
        residency[mid] = {"ACTIVE_HASHING": horizon_f}
        e = cfg.P_hash * horizon_f
        energy_by_state["ACTIVE_HASHING"] += e / J_PER_KWH
        energy_total_j += e
    for sid in cfg.standby_ids:
        residency[sid] = {"RESERVE_STANDBY": horizon_f}
        e = cfg.P_reserve * horizon_f
        energy_by_state["RESERVE_STANDBY"] += e / J_PER_KWH
        energy_total_j += e
    energy_kwh = energy_total_j / J_PER_KWH
    energy_identity_residual_j = abs(
        energy_total_j - sum(v * J_PER_KWH for v in energy_by_state.values()))
    residency_partition_residual_s = max(
        (abs(horizon_f - sum(states.values())) for states in residency.values()),
        default=0.0)
    accepted = [r for r in rounds if r.close_kind == "BLOCK"]
    closed = [r for r in rounds if r.close_kind in ("BLOCK", "EXHAUSTED")]
    return {
        "scenario_id": cfg.scenario_id,
        "scenario_kind": cfg.scenario_kind,
        "consensus_label": "matched same-template PoW control",
        "master_seed": cfg.master_seed,
        "template_seed": cfg.template_seed,
        "difficulty": cfg.difficulty,
        "target": cfg.target,
        "nonce_domain_size": D,
        "batch_size": batch,
        "horizon_seconds": horizon_f,
        "mining_node_count": len(miners),
        "standby_node_count": len(cfg.standby_ids),
        "rounds_executed": len(rounds),
        "rounds_accepted": len(accepted),
        "rounds_exhausted": sum(1 for r in rounds if r.close_kind == "EXHAUSTED"),
        "rounds_horizon_truncated": sum(1 for r in rounds if r.close_kind == "HORIZON"),
        "round_durations_closed": [r.duration for r in closed],
        "accepted_round_durations": [r.duration for r in accepted],
        "total_physical_evaluations": sum(r.total_physical_evaluations for r in rounds),
        "unique_physical_evaluations": sum(r.unique_physical_evaluations for r in rounds),
        "duplicate_physical_evaluations": sum(r.duplicate_physical_evaluations
                                              for r in rounds),
        "post_round_evaluation_count": 0,     # by construction; asserted in U-TEST-04
        "first_valid_solutions": first_valid_solutions,
        "energy_kwh": energy_kwh,
        "energy_kwh_by_state": energy_by_state,
        "energy_identity_residual_j": energy_identity_residual_j,
        "residency_partition_residual_s": residency_partition_residual_s,
        "residency_seconds_by_node": residency,
        "rounds": rounds,
    }
