"""Stage-2B idle-policy energy experiment (S2B-3/S2B-6): a CONSTRUCTED matched
identity-validation scenario — NOT a general PoCol saving measurement.

Runs ONE round under two policies over IDENTICAL miners, hash rates, disjoint nonce
ranges, template, fixed target, real per-nonce evaluations, winner/no-winner outcome and
round end (SCI-8):

* **CONTROL** — every assigned miner remains at active power until round end.
* **POCOL_IDLE** — a miner that finishes (exhausts, or solves) its assigned range before
  round end moves to the declared idle/listen power (the idle policy within PoCol).

Success is coupled to the fixed target exactly as in the simulator: a nonce is a solution
iff ``sha256_int(header, nonce) <= target``.  A deterministic seed scan selects a header
for which the earliest solution (in simulation time) belongs to the slow miner while the
fast miners finish their ranges earlier — a clean idle demonstration.  For every miner it
verifies

    E_i        = P_active_i * t_active_i + P_idle_i * t_idle_i
    Delta_E_i  = t_idle_i * (P_active_i - P_idle_i)      ==  E_control_i - E_idle_i

and reports the maximum absolute residual.  With ``P_idle == P_active`` the saving is
exactly zero (SCI-9).  The returned ``saving_j`` is the saving of THIS constructed
scenario only; it must not be reported as a general PoCol saving percentage (S2B-6).
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from .config import Stage2Config
from .search import Template, target_for_difficulty, sha256_int, SUCCESS_MODEL


@dataclass
class MinerEnergyRow:
    MinerID: str
    hash_rate: float
    range_start: int
    range_end: int
    completion_kind: str          # "SOLUTION" | "EXHAUSTED"
    completion_time: float
    searched: int
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
    scenario: str
    seed: int
    difficulty: int
    target: int
    winner: Optional[str]
    winning_nonce: Optional[int]
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


def _constructed_ranges(D: int, ids: List[str]) -> Dict[str, Tuple[int, int]]:
    """A disjoint cover of ``[0, D)``: the slow winner (ids[0]) gets a large range, the
    fast miners split the remainder.  Covers the whole domain with no overlap."""
    n = len(ids)
    r0 = D // 2 if n > 1 else D
    ranges: Dict[str, Tuple[int, int]] = {ids[0]: (0, r0)}
    rest = ids[1:]
    if rest:
        base = (D - r0) // len(rest)
        rem = (D - r0) % len(rest)
        start = r0
        for i, mid in enumerate(rest):
            size = base + (1 if i < rem else 0)
            ranges[mid] = (start, start + size)
            start += size
        assert start == D
    return ranges


def _first_solution(header: bytes, target: int, start: int, end: int) -> Optional[int]:
    for nonce in range(start, end):
        if sha256_int(header, nonce) <= target:
            return nonce
    return None


def run_energy_experiment(cfg: Optional[Stage2Config] = None, n_miners: int = 8,
                          difficulty: int = 600, slow_rate: float = 100.0,
                          fast_rate: float = 400.0, P_active: Optional[float] = None,
                          P_idle: Optional[float] = None,
                          seed_scan: int = 4000) -> EnergyExperimentResult:
    """Run the constructed matched CONTROL vs POCOL_IDLE identity-validation scenario."""
    cfg = cfg or Stage2Config()
    P_active = cfg.P_hash if P_active is None else P_active
    P_idle = cfg.P_listen if P_idle is None else P_idle
    D = cfg.nonce_domain_size
    t_start = 0.0
    ids = [f"M{i:03d}" for i in range(n_miners)]
    ranges = _constructed_ranges(D, ids)
    rates = {mid: (slow_rate if mid == ids[0] else fast_rate) for mid in ids}
    target = target_for_difficulty(difficulty)

    chosen = None
    for seed in range(seed_scan):
        header = hashlib.sha256(f"energy2b|{D}|{difficulty}|{seed}".encode()).digest()
        per = {}
        for mid in ids:
            start, end = ranges[mid]
            sol = _first_solution(header, target, start, end)
            searched = (sol - start + 1) if sol is not None else (end - start)
            kind = "SOLUTION" if sol is not None else "EXHAUSTED"
            completion = t_start + searched / rates[mid]
            per[mid] = dict(start=start, end=end, sol=sol, searched=searched,
                            kind=kind, completion=completion)
        solvers = [(per[m]["completion"], m) for m in ids if per[m]["kind"] == "SOLUTION"]
        if not solvers:
            continue
        round_end, winner = min(solvers)
        # want a clean idle demonstration: the SLOW miner wins and >=1 fast miner idles.
        if winner != ids[0]:
            continue
        n_idle = sum(1 for m in ids if per[m]["completion"] < round_end - 1e-15)
        if n_idle < 1:
            continue
        chosen = (seed, header, per, round_end, winner)
        break
    if chosen is None:
        raise ValueError("energy experiment: no matched slow-winner scenario found in scan")

    seed, header, per, round_end, winner = chosen
    winning_nonce = per[winner]["sol"]
    rows: List[MinerEnergyRow] = []
    total_c = total_i = max_res = 0.0
    for mid in ids:
        v = per[mid]
        busy = min(v["completion"], round_end) - t_start
        t_active_c = round_end - t_start
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
            MinerID=mid, hash_rate=rates[mid], range_start=v["start"], range_end=v["end"],
            completion_kind=v["kind"], completion_time=v["completion"], searched=v["searched"],
            is_winner=(mid == winner), t_active_control=t_active_c, t_idle_control=0.0,
            E_control_j=E_c, t_active_idle=t_active_i, t_idle_idle=t_idle_i, E_idle_j=E_i,
            delta_e_j=delta, residual_j=residual))

    return EnergyExperimentResult(
        success_model=SUCCESS_MODEL, scenario="constructed_matched_identity_validation",
        seed=seed, difficulty=difficulty, target=target, winner=winner,
        winning_nonce=winning_nonce, round_start=t_start, round_end=round_end,
        P_active=P_active, P_idle=P_idle, rows=rows, total_control_j=total_c,
        total_idle_j=total_i, saving_j=total_c - total_i, max_abs_residual_j=max_res)
