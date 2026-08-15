"""Stage 8X-E50 — engine: common-template control, conventional reference, and
PoCol reduced-active-set disjoint search. Exact integer-tick accounting.

Abstraction (identical to Stage 8X-NR, revalidated by the E50 test suite): the
SHA-256 acceptance field is i.i.d. Bernoulli(q) over DISTINCT inputs
(template_id, nonce32); re-evaluating an input reproduces its outcome. The
number of distinct inputs up to the first winner is Geometric(q); the winner is
uniform on the winning epoch's searched set. 1 tick = one evaluation per miner
= 1/h seconds.

Matched renewal rule (one rule, all arms): a template epoch ends when every
ACTIVE miner completes its assigned traversal — full domain for E50-MT100
(uncoordinated), own disjoint range for E50-PC* — or when a block ends the
round. E50-CONV100 renews per miner on nonce-domain exhaustion.

PoCol arms: the 2^32 domain is partitioned over the FULL population N
(prefix P[i] = floor(i*S/N)); only the k = ceil(A*N) miners in the sliding
rotation window search their own ranges; inactive owners' ranges stay
unsearched (no borrowing, no reassignment, no handoff). Distinct inputs per
epoch = sum of active range lengths, computed O(1) from the prefix; over any N
consecutive epochs the total is exactly k*S.

Difficulty: one q_N = 1/(N*h*600) for every arm at a given N. Active fraction
NEVER changes the target (brief sections 13-14).
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from experiments.stage8xe50.config.e50_config import (
    ACTIVE_FRACTIONS, ACTIVE_POWER_W, ARM_CONV, ARM_MT, ARMS, HASHRATE_HPS,
    S_NONCE, T_RUN_S, T_RUN_TICKS, active_count, epoch_ticks_pc, partition,
    q_per_candidate,
)
from experiments.stage8xe50.config.seeds import derive_stream_seed
from experiments.stage8xnr.src.noncedomain import union_measure  # read-only


def _geometric(rng: random.Random, q: float) -> int:
    u = rng.random()
    while u <= 0.0:
        u = rng.random()
    return int(math.log(u) / math.log1p(-q)) + 1


@dataclass
class RunResult:
    arm: str
    n_miners: int
    seed: int
    k_active: int
    rounds: int = 0
    accepted_blocks: int = 0
    intervals_s: List[float] = field(default_factory=list)
    C_total: int = 0              # physical evaluations
    U_exact: int = 0              # unique exact candidate inputs
    epochs_completed: int = 0
    exhaustions: int = 0          # assigned-traversal completions
    t_active_miner_s: float = 0.0
    t_low_miner_s: float = 0.0
    # fairness / low-power structure (closed form, exact)
    duty_min: float = 0.0
    duty_max: float = 0.0
    duty_sd: float = 0.0
    jain_index: float = 1.0
    transitions_total: int = 0
    active_episode_s: float = 0.0
    low_episode_s: float = 0.0
    identity_errors: Dict[str, float] = field(default_factory=dict)

    @property
    def R_exact(self) -> int:
        return self.C_total - self.U_exact

    @property
    def rho_exact(self) -> float:
        return self.R_exact / self.C_total if self.C_total else 0.0

    def energy_j(self, alpha: float) -> float:
        return ACTIVE_POWER_W * (self.t_active_miner_s
                                 + alpha * self.t_low_miner_s)


# ---------------- PoCol epoch arithmetic (O(1) via prefix) ----------------
class PCGeometry:
    def __init__(self, n: int, k: int):
        self.n, self.k = n, k
        self.P = [i * S_NONCE // n for i in range(n + 1)]   # prefix of lengths
        self.hi = epoch_ticks_pc(n)
        self.lo = min(self.P[i + 1] - self.P[i] for i in range(n))

    def window_sum(self, start: int, k: int = None) -> int:
        """Sum of range lengths over slots [start, start+k) mod n."""
        k = self.k if k is None else k
        a = start % self.n
        b = a + k
        if b <= self.n:
            return self.P[b] - self.P[a]
        return (self.P[self.n] - self.P[a]) + self.P[b - self.n]

    def n_hi_in_window(self, start: int) -> int:
        """Number of hi-length ranges among the active window."""
        return self.window_sum(start) - self.k * self.lo

    def work_partial(self, start: int, tau: int) -> int:
        """Sum over active slots of min(tau, len_i) for tau <= hi ticks."""
        if tau >= self.hi:
            return self.window_sum(start)
        if tau <= self.lo:
            return self.k * tau
        nhi = self.n_hi_in_window(start)
        return nhi * tau + (self.k - nhi) * self.lo

    def locate(self, start: int, v: int) -> Tuple[int, int]:
        """Map v in [0, window_sum) to (slot, offset) inside the window."""
        a = start % self.n
        for j in range(self.k):
            s = (a + j) % self.n
            L = self.P[s + 1] - self.P[s]
            if v < L:
                return s, v
            v -= L
        raise AssertionError("v outside window coverage")


def run_one(arm: str, n: int, seed: int) -> RunResult:
    if arm not in ARMS:
        raise ValueError(f"unknown arm {arm!r}")
    q = q_per_candidate(n)
    k = active_count(n, arm)
    rng_rounds = random.Random(derive_stream_seed(seed, "rounds"))
    rng_value = random.Random(derive_stream_seed(seed, "winner-value"))
    rng_off = random.Random(derive_stream_seed(seed, "offsets"))
    offsets = [rng_off.randrange(S_NONCE) for _ in range(n)]

    res = RunResult(arm=arm, n_miners=n, seed=seed, k_active=k)
    t_abs = 0
    e_abs = 0                     # global epoch counter (rotation continuity)
    work = 0                      # powered-active miner-ticks (= evaluations)
    U = 0
    is_pc = arm in ACTIVE_FRACTIONS
    geo = PCGeometry(n, k) if is_pc else None

    while t_abs < T_RUN_TICKS:
        g = _geometric(rng_rounds, q)
        remaining = T_RUN_TICKS - t_abs

        if arm == ARM_CONV:
            n_t_block = -(-g // n)
            n_t = min(n_t_block, remaining)
            block = n_t_block <= remaining
            res.C_total += n * n_t
            U += n * n_t                          # per-miner templates: fresh
            full, _rem = divmod(n_t, S_NONCE)
            res.epochs_completed += full * n
            res.exhaustions += full * n
            work += n * n_t
            rng_value.randrange(S_NONCE)          # stream alignment

        elif arm == ARM_MT:
            x_star = rng_value.randrange(S_NONCE)
            failed_epochs = (g - 1) // S_NONCE
            first_hit = min((x_star - s) % S_NONCE for s in offsets)
            n_t_block = failed_epochs * S_NONCE + first_hit + 1
            n_t = min(n_t_block, remaining)
            block = n_t_block <= remaining
            res.C_total += n * n_t
            full, rem = divmod(n_t, S_NONCE)
            # unique: S per completed epoch + union of partial arcs
            if rem:
                arcs = [((s + t_abs) % S_NONCE, rem) for s in offsets]
                # phases advance with absolute time under cyclic traversal
                U += full * S_NONCE + union_measure(arcs)
            else:
                U += full * S_NONCE
            res.epochs_completed += full
            res.exhaustions += full * n
            work += n * n_t

        else:                                     # PoCol reduced active set
            hi = geo.hi
            per_cycle = k * S_NONCE               # distinct inputs per N epochs
            f_cycles, rem_d = divmod(g - 1, per_cycle)
            # walk at most N epochs of the final cycle
            j = 0
            e = e_abs + f_cycles * n
            while True:
                U_ep = geo.window_sum(e + j)
                if rem_d < U_ep:
                    break
                rem_d -= U_ep
                j += 1
            slot, off = geo.locate(e + j, rng_value.randrange(geo.window_sum(e + j)))
            n_t_block = (f_cycles * n + j) * hi + off + 1
            if n_t_block <= remaining:
                block = True
                n_t = n_t_block
                full_epochs = f_cycles * n + j
                tau = off + 1
                w = f_cycles * per_cycle
                for jj in range(j):
                    w += geo.window_sum(e_abs + f_cycles * n + jj)
                w += geo.work_partial(e + j, tau)
            else:
                block = False
                n_t = remaining
                full_epochs, tau = divmod(n_t, hi)
                fc, je = divmod(full_epochs, n)
                w = fc * per_cycle
                for jj in range(je):
                    w += geo.window_sum(e_abs + fc * n + jj)
                if tau:
                    w += geo.work_partial(e_abs + full_epochs, tau)
            res.C_total += w
            U += w                                # disjoint + fresh templates
            res.epochs_completed += full_epochs
            res.exhaustions += full_epochs * k
            work += w
            e_abs += full_epochs + (1 if (block or tau) else 0)

        res.rounds += 1
        if block:
            res.accepted_blocks += 1
            res.intervals_s.append(n_t_block / HASHRATE_HPS)
        t_abs += n_t

    # ---- energy state-time (recorded once; alpha is accounting-only) ----
    total_ticks = n * T_RUN_TICKS
    res.U_exact = U
    res.t_active_miner_s = work / HASHRATE_HPS
    res.t_low_miner_s = (total_ticks - work) / HASHRATE_HPS
    res.identity_errors = {
        "state_time_conservation_rel": abs(
            (res.t_active_miner_s + res.t_low_miner_s) - n * T_RUN_S)
            / (n * T_RUN_S),
        "work_identity_rel": abs(res.C_total - work) / max(1, work),
        "unique_le_total": 0.0 if res.U_exact <= res.C_total else 1.0,
    }

    # ---- fairness / episode structure (closed form) ----
    if is_pc:
        E_tot = res.epochs_completed
        cycles = E_tot / n if n else 0.0
        duties = [(k * (geo.P[i + 1] - geo.P[i])) / (n * geo.hi)
                  for i in range(n)]
        mean_d = sum(duties) / n
        res.duty_min, res.duty_max = min(duties), max(duties)
        res.duty_sd = (sum((d - mean_d) ** 2 for d in duties) / n) ** 0.5
        res.jain_index = (sum(duties) ** 2) / (n * sum(d * d for d in duties))
        res.transitions_total = int(2 * cycles * n)     # 2 per miner per cycle
        res.active_episode_s = k * geo.hi / HASHRATE_HPS
        res.low_episode_s = (n - k) * geo.hi / HASHRATE_HPS
    else:
        res.duty_min = res.duty_max = 1.0
        res.duty_sd = 0.0
        res.jain_index = 1.0
        res.transitions_total = 0
        res.active_episode_s = T_RUN_S
        res.low_episode_s = 0.0
    return res
