"""Stage-2A idle-policy energy experiment (S2A-3): matched CONTROL vs POCOL_IDLE.

Runs ONE round under two policies with IDENTICAL miners, hash rates, disjoint nonce
ranges, target, template and success position, and the SAME round-start and stopping
condition (SCI-7):

* **CONTROL** — every assigned miner remains at active power until round end.
* **POCOL_IDLE** — a miner that EXHAUSTS its assigned range before round end moves to
  the declared idle/listen power (the idle policy within PoCol).

The saving therefore comes ONLY from post-range idle residency — not from removing a
reserve fraction from participation and not from nonce partitioning.  For every miner it
verifies the residency identity

    E_i        = P_active_i * t_active_i + P_idle_i * t_idle_i
    Delta_E_i  = t_idle_i * (P_active_i - P_idle_i)      ==  E_control_i - E_idle_i

and reports the maximum absolute residual.  With ``P_idle == P_active`` the saving is
exactly zero (SCI-5).  Success model B (a single sampled/placed winning nonce) is used
so the winner and round end are deterministic and identical across the two policies.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import List, Optional

from .config import Stage2Config, JOULES_PER_KWH
from .search import (Template, partition_domain, target_for_difficulty, sha256_int,
                     SUCCESS_MODEL)


@dataclass
class MinerEnergyRow:
    MinerID: str
    hash_rate: float
    range_start: int
    range_end: int
    completion_kind: str          # "SOLUTION" | "EXHAUSTED"
    completion_time: float
    is_winner: bool
    t_active_control: float
    t_idle_control: float
    E_control_j: float
    t_active_idle: float
    t_idle_idle: float
    E_idle_j: float
    delta_e_j: float
    residual_j: float


@dataclass
class EnergyExperimentResult:
    success_model: str
    winner: str
    winning_nonce: int
    round_start: float
    round_end: float
    P_active: float
    P_idle: float
    rows: List[MinerEnergyRow]
    total_control_j: float
    total_idle_j: float
    saving_j: float
    max_abs_residual_j: float

    @property
    def n_idlers(self) -> int:
        return sum(1 for r in self.rows if r.t_idle_idle > 0)


def run_energy_experiment(cfg: Optional[Stage2Config] = None, n_miners: int = 8,
                          winner_index: int = 0, slow_rate: Optional[float] = None,
                          fast_rate: Optional[float] = None,
                          P_active: Optional[float] = None,
                          P_idle: Optional[float] = None) -> EnergyExperimentResult:
    """Run the matched CONTROL vs POCOL_IDLE energy experiment over one round."""
    cfg = cfg or Stage2Config()
    P_active = cfg.P_hash if P_active is None else P_active
    P_idle = cfg.P_listen if P_idle is None else P_idle
    slow_rate = cfg.base_hash_rate if slow_rate is None else slow_rate
    fast_rate = 4.0 * cfg.base_hash_rate if fast_rate is None else fast_rate
    D = cfg.nonce_domain_size
    t_start = 0.0

    ids = [f"M{i:03d}" for i in range(n_miners)]
    ranges = partition_domain(D, ids)
    ids_sorted = sorted(ids)
    winner_id = ids_sorted[winner_index]
    w_start, w_end = ranges[winner_id]
    # place the single winning nonce in the MIDDLE of the (slow) winner's range so the
    # winner searches deep while the faster non-winners exhaust their ranges early.
    winning_nonce = (w_start + w_end) // 2
    header = hashlib.sha256(f"energy|{D}|{cfg.difficulty}|{cfg.template_seed}"
                            .encode()).digest()
    template = Template(TemplateID="tpl-energy", RoundID="energy-round",
                        header_bytes=header, difficulty=cfg.difficulty,
                        nonce_domain_size=D, winning_nonces=frozenset({winning_nonce}),
                        target=target_for_difficulty(cfg.difficulty))

    rows: List[MinerEnergyRow] = []
    # first pass: per-miner completion (real per-nonce SHA-256 work performed + counted).
    per = {}
    for mid in ids_sorted:
        start, end = ranges[mid]
        hr = slow_rate if mid == winner_id else fast_rate
        sol = None
        for nonce in range(start, end):
            _ = sha256_int(template.header_bytes, nonce)   # real work primitive
            if template.is_solution(nonce):
                sol = nonce
                break
        if sol is not None:
            searched = sol - start + 1
            kind = "SOLUTION"
        else:
            searched = end - start
            kind = "EXHAUSTED"
        completion_time = t_start + searched / hr
        per[mid] = dict(start=start, end=end, hr=hr, searched=searched, kind=kind,
                        completion_time=completion_time)

    sol_completions = [(v["completion_time"], mid) for mid, v in per.items()
                       if v["kind"] == "SOLUTION"]
    if not sol_completions:
        raise ValueError("energy experiment: no solution in the nonce domain")
    round_end, winner = min(sol_completions)

    total_c = 0.0
    total_i = 0.0
    max_res = 0.0
    for mid in ids_sorted:
        v = per[mid]
        busy = min(v["completion_time"], round_end) - t_start   # actual searching time
        t_active_c = round_end - t_start
        t_idle_c = 0.0
        E_c = P_active * t_active_c
        t_active_i = busy
        t_idle_i = (round_end - t_start) - busy
        E_i = P_active * t_active_i + P_idle * t_idle_i
        delta = t_idle_i * (P_active - P_idle)
        residual = abs((E_c - E_i) - delta)
        max_res = max(max_res, residual)
        total_c += E_c
        total_i += E_i
        rows.append(MinerEnergyRow(
            MinerID=mid, hash_rate=v["hr"], range_start=v["start"], range_end=v["end"],
            completion_kind=v["kind"], completion_time=v["completion_time"],
            is_winner=(mid == winner), t_active_control=t_active_c, t_idle_control=t_idle_c,
            E_control_j=E_c, t_active_idle=t_active_i, t_idle_idle=t_idle_i, E_idle_j=E_i,
            delta_e_j=delta, residual_j=residual))

    return EnergyExperimentResult(
        success_model=SUCCESS_MODEL, winner=winner, winning_nonce=winning_nonce,
        round_start=t_start, round_end=round_end, P_active=P_active, P_idle=P_idle,
        rows=rows, total_control_j=total_c, total_idle_j=total_i,
        saving_j=total_c - total_i, max_abs_residual_j=max_res)
