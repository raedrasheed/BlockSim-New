"""Stage 8X-NR — five-arm engine over the explicit 32-bit nonce-value domain.

Physical-event abstraction (brief section 12)
---------------------------------------------
Work is counted in integer TICKS (1 tick = one candidate evaluation per miner =
1/h seconds; h = 2.34e14 evals/s). The SHA-256 acceptance field is i.i.d.
Bernoulli(q) across DISTINCT hash inputs (template_id, nonce32); re-evaluating
an already-evaluated input reproduces the same outcome and can never yield an
independent success. The number of distinct inputs up to and including the first
winner is therefore Geometric(q), sampled exactly; the winning VALUE is uniform
on the 2^32 domain of the winning template epoch. Round mechanics then follow
deterministically from each arm's traversal geometry, so every count below is an
exact integer — no SHA-256 enumeration and no floating-point work accounting.

Distinct-input throughput per arm (the quantity that sets the block rate):
  CONV        N*h  (per-miner templates: every evaluation is a fresh input)
  MT          h    (one common 2^32 domain per epoch; N miners re-cover it, so
                    only S distinct inputs exist per S-tick epoch)
  PC          N*h  (disjoint allocation: every evaluation fresh, like CONV)

Rounds and resets
-----------------
A round is one block race under one previous-block context; it ends at an
accepted block or at the run horizon. Every round boundary renews templates.
Within a round, template epochs renew every 2^32 ticks (CONV/MT) or every
partitioned domain sweep of hi = max range size ticks (PC). ZERO traversals
reset the nonce phase to 0 at every template renewal (counted as nonce resets);
OFFSET traversals continue cyclically (exhaustions counted, no positional
reset). Metric reset points are documented in metrics_nr.

MT-ZERO co-discovery: under exact zero-start synchrony all N miners evaluate the
winning input in the same tick, so each MT-ZERO block is accepted once with N-1
simultaneous stale duplicates. This is an artifact of the deliberately
synchronized control and is reported as such.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from experiments.stage8xnr.config.nr_config import (
    ACTIVE_POWER_W, ALPHA_CASES, ARM_CONV_OFF, ARM_CONV_ZERO, ARM_MT_OFF,
    ARM_MT_ZERO, ARM_PC, ARMS, HASHRATE_HPS, S_NONCE, T_RUN_TICKS, T_RUN_S,
    derive_difficulty, pocol_partition, subsweep_window_ticks,
)
from experiments.stage8xnr.config.seeds import derive_stream_seed
from experiments.stage8xnr.src.metrics_nr import RunAccumulator, ScopeMetrics, scope_from_miners
from experiments.stage8xnr.src.noncedomain import (
    multiplicity_profile, max_multiplicity, measure_covered_at_least,
    pairwise_overlap_summary, union_measure, verify_partition,
)
from experiments.stage8xnr.src.traversal import window as trav_window


def _geometric(rng: random.Random, q: float) -> int:
    """Exact-law Geometric(q) trials-to-first-success via inverse transform."""
    u = rng.random()
    while u <= 0.0:
        u = rng.random()
    return int(math.log(u) / math.log1p(-q)) + 1


@dataclass
class RunResult:
    arm: str
    n_miners: int
    seed: int
    rounds: int = 0
    accepted_blocks: int = 0
    stale_blocks: int = 0
    intervals_s: List[float] = field(default_factory=list)
    round_rows: List[Dict[str, object]] = field(default_factory=list)
    # run-scope work / energy (exact ints for work)
    C_total: int = 0                      # physical evaluations (network)
    t_active_miner_s: float = 0.0
    t_low_miner_s: float = 0.0
    # scoped nonce/exact aggregates
    scope_rows: List[Dict[str, object]] = field(default_factory=list)
    # template accounting
    template_epochs_completed: int = 0    # network-wide completed epochs
    nonce_domain_exhaustions: int = 0
    nonce_resets: int = 0
    # invariant checks
    identity_errors: Dict[str, float] = field(default_factory=dict)

    def energy_j(self, alpha: float) -> float:
        return (ACTIVE_POWER_W * self.t_active_miner_s
                + alpha * ACTIVE_POWER_W * self.t_low_miner_s)


def _round_scope_conv_mt(arm: str, n: int, n_t: int, phases: List[int]
                         ) -> Tuple[ScopeMetrics, Dict[str, int]]:
    """Round-scope nonce metrics for the four always-active PoW arms, plus
    exact-input totals for the round."""
    cover = [trav_window(p, n_t).coverage_arc() for p in phases]
    C = n * n_t
    if arm in (ARM_CONV_ZERO, ARM_CONV_OFF):
        # per-miner distinct templates; within a template each value evaluated
        # once (arc length <= S by construction, asserted in trav_window's
        # decomposition) -> all inputs distinct.
        exact_C, exact_U = C, C
    else:
        # common template per epoch: full epochs contribute U_exact = S each;
        # the truncated final epoch contributes the union of its partial arcs.
        full, rem = divmod(n_t, S_NONCE)
        partial_arcs = [((p + full * S_NONCE) % S_NONCE, rem) for p in phases] \
            if rem else []
        exact_C = C
        exact_U = full * S_NONCE + (union_measure(partial_arcs) if rem else 0)
    lengths = {a[1] for a in cover}
    if lengths == {S_NONCE}:
        pair = {"mean": float(S_NONCE), "median": float(S_NONCE),
                "p95": float(S_NONCE), "max": S_NONCE,
                "overlapping_pairs": n * (n - 1) // 2,
                "n_pairs": n * (n - 1) // 2}
    elif len(set(phases)) == 1:
        L = cover[0][1]
        pair = {"mean": float(L), "median": float(L), "p95": float(L),
                "max": L, "overlapping_pairs": n * (n - 1) // 2 if L else 0,
                "n_pairs": n * (n - 1) // 2}
    elif 2 * cover[0][1] <= S_NONCE:
        pair = pairwise_overlap_summary(phases, cover[0][1])
    else:
        # pathological sub-sweep truncated round with long arcs: exact O(N^2)
        from experiments.stage8xnr.src.noncedomain import arc_intersection_measure
        ovs = [arc_intersection_measure(cover[i], cover[j])
               for i in range(n) for j in range(i + 1, n)]
        ovs.sort()
        import math as _math
        pair = {"mean": sum(ovs) / len(ovs), "median": float(ovs[len(ovs) // 2]),
                "p95": float(ovs[max(0, _math.ceil(0.95 * len(ovs)) - 1)]),
                "max": ovs[-1], "overlapping_pairs": sum(1 for o in ovs if o),
                "n_pairs": len(ovs)}
    sm = scope_from_miners("NR-round", [n_t] * n, cover, exact_C, exact_U,
                           pair_summary=pair)
    return sm, {"C": C}


def _subsweep_scope(arm: str, n: int, n_t: int, phases: List[int],
                    pc_ranges=None) -> ScopeMetrics:
    """First W = floor(S/2N) ticks of the round (sub-saturation diagnostic)."""
    W = min(subsweep_window_ticks(n), n_t)
    if pc_ranges is not None:
        cover = [(s, min(W, e - s)) for s, e in pc_ranges]
        counts = [min(W, e - s) for s, e in pc_ranges]
        C = sum(counts)
        return scope_from_miners("NR-subsweep", counts, cover, C, C,
                                 pairwise_zero=True)
    cover = [(p, W) for p in phases]
    C = n * W
    if arm in (ARM_CONV_ZERO, ARM_CONV_OFF):
        exact_C, exact_U = C, C
    else:
        exact_C, exact_U = C, union_measure(cover)
    if len(set(phases)) == 1:
        pair = {"mean": float(W), "median": float(W), "p95": float(W),
                "max": W, "overlapping_pairs": n * (n - 1) // 2,
                "n_pairs": n * (n - 1) // 2}
    else:
        pair = pairwise_overlap_summary(phases, W)
    return scope_from_miners("NR-subsweep", [W] * n, cover, exact_C, exact_U,
                             pair_summary=pair)


def run_one(arm: str, n: int, seed: int, collect_rounds: bool = True) -> RunResult:
    if arm not in ARMS:
        raise ValueError(f"unknown arm {arm!r}")
    diff = derive_difficulty(n)
    q = diff.q_per_candidate
    rng_rounds = random.Random(derive_stream_seed(seed, "rounds"))
    rng_value = random.Random(derive_stream_seed(seed, "winner-value"))
    rng_miner = random.Random(derive_stream_seed(seed, "winner-miner"))
    rng_off = random.Random(derive_stream_seed(seed, "offsets"))

    offsets = [rng_off.randrange(S_NONCE) for _ in range(n)]
    zero = arm in (ARM_CONV_ZERO, ARM_MT_ZERO)

    ranges = pocol_partition(n) if arm == ARM_PC else None
    if ranges is not None:
        pv = verify_partition(ranges)
        if not (pv["full_coverage"] and pv["overlap"] == 0
                and pv["size_spread_le_1"]):
            raise AssertionError(f"PoCol partition invalid: {pv}")
        lens = [e - s for s, e in ranges]
        hi = max(lens)
        starts_sorted = sorted(s for s, _ in ranges)

    res = RunResult(arm=arm, n_miners=n, seed=seed)
    acc = RunAccumulator()
    t_abs = 0            # absolute ticks elapsed
    parked_ticks = 0     # PC post-range low-power, miner-ticks
    run_epoch_full = 0   # network-wide completed template epochs
    exhaustions = 0
    resets = 0
    # global-run coverage: per-miner union arcs (PC: ranges; others saturate)
    run_cover_full = [False] * n
    run_partial: List[Tuple[int, int]] = [(0, 0)] * n

    while t_abs < T_RUN_TICKS:
        g = _geometric(rng_rounds, q)
        x_star = rng_value.randrange(S_NONCE)
        w_uniform = rng_miner.randrange(n)

        if arm in (ARM_CONV_ZERO, ARM_CONV_OFF):
            n_t_block = -(-g // n)                       # ceil(g/N)
            winner = w_uniform
            co_discovery = 1
        elif arm in (ARM_MT_ZERO, ARM_MT_OFF):
            failed_epochs = (g - 1) // S_NONCE
            if zero:
                first_hit = x_star
                winner = w_uniform                       # exact tie, broken uniformly
                co_discovery = n
            else:
                first_hit = min((x_star - s) % S_NONCE for s in offsets)
                winner = min(range(n),
                             key=lambda i: (x_star - offsets[i]) % S_NONCE)
                co_discovery = 1
            n_t_block = failed_epochs * S_NONCE + first_hit + 1
        else:                                            # ARM_PC
            failed_epochs = (g - 1) // S_NONCE
            owner = min(n - 1, x_star * n // S_NONCE)
            while not (ranges[owner][0] <= x_star < ranges[owner][1]):
                owner += 1 if x_star >= ranges[owner][1] else -1
            x_off = x_star - ranges[owner][0]
            n_t_block = failed_epochs * hi + x_off + 1
            winner = owner
            co_discovery = 1

        block = t_abs + n_t_block <= T_RUN_TICKS
        n_t = n_t_block if block else (T_RUN_TICKS - t_abs)
        if n_t <= 0:
            break

        # ---- phases at round start ----
        if arm == ARM_PC:
            phases = [s for s, _ in ranges]
        elif zero:
            phases = [0] * n
        else:
            phases = [(offsets[i] + t_abs) % S_NONCE for i in range(n)]

        # ---- per-round work / energy / template accounting ----
        if arm == ARM_PC:
            full_ep, tau = divmod(n_t, hi)
            evals = full_ep * S_NONCE + sum(min(tau, L) for L in lens)
            res.C_total += evals
            parked_ticks += full_ep * (n * hi - S_NONCE) \
                + sum(max(0, tau - L) for L in lens)
            run_epoch_full += full_ep
            exhaustions += full_ep * n          # every miner completes its range
            resets += full_ep * n               # repartition -> new range sweep
            eval_counts = [full_ep * L + min(tau, L) for L in lens]
        else:
            res.C_total += n * n_t
            full_ep, rem = divmod(n_t, S_NONCE)
            if arm in (ARM_MT_ZERO, ARM_MT_OFF):
                run_epoch_full += full_ep       # network-common epochs
            else:
                run_epoch_full += full_ep * n   # per-miner template epochs
            exhaustions += full_ep * n
            resets += (full_ep + 1) * n if zero else 0
            eval_counts = [n_t] * n

        # ---- scoped metrics ----
        if arm == ARM_PC:
            cover = [(s, min(eval_counts[i] if full_ep == 0 else lens[i],
                             lens[i])) for i, (s, _) in enumerate(ranges)]
            C_round = res_round_C = sum(eval_counts)
            sm_round = scope_from_miners(
                "NR-round", eval_counts, cover, C_round, C_round,
                pairwise_zero=True)
            prof = multiplicity_profile(cover)
            if max_multiplicity(prof) > 1:
                raise AssertionError("PoCol cross-miner nonce overlap detected")
            sm_sub = _subsweep_scope(arm, n, n_t, phases, pc_ranges=ranges)
        else:
            sm_round, _ = _round_scope_conv_mt(arm, n, n_t, phases)
            sm_sub = _subsweep_scope(arm, n, n_t, phases)

        acc.add_round(res.rounds, n_t / HASHRATE_HPS, block,
                      {"round": sm_round, "subsweep": sm_sub})

        # ---- run-scope coverage bookkeeping ----
        for i in range(n):
            if run_cover_full[i]:
                continue
            if arm == ARM_PC:
                cov = cover[i]
                prev = run_partial[i]
                run_partial[i] = cov if cov[1] >= prev[1] else prev
                if run_partial[i][1] >= lens[i]:
                    pass  # range fully covered; stays partial vs full domain
            else:
                wv = trav_window(phases[i], n_t)
                if wv.covers_domain:
                    run_cover_full[i] = True
                else:
                    a = wv.partial_arc
                    if a[1] > run_partial[i][1]:
                        run_partial[i] = a

        res.rounds += 1
        if block:
            res.accepted_blocks += 1
            res.stale_blocks += co_discovery - 1
            res.intervals_s.append(n_t_block / HASHRATE_HPS)
        t_abs += n_t

    # ---- run-level energy / identities ----
    total_miner_ticks = n * T_RUN_TICKS
    active_ticks = total_miner_ticks - parked_ticks
    res.t_active_miner_s = active_ticks / HASHRATE_HPS
    res.t_low_miner_s = parked_ticks / HASHRATE_HPS
    cons_err = abs((res.t_active_miner_s + res.t_low_miner_s)
                   - n * T_RUN_S) / (n * T_RUN_S)
    work_err = abs(res.C_total - active_ticks) / max(1, active_ticks) \
        if arm == ARM_PC else abs(res.C_total - active_ticks) / active_ticks
    res.identity_errors = {"state_time_conservation_rel": cons_err,
                           "work_identity_rel": work_err}

    # ---- run-scope (NR-global-run) metrics ----
    if arm == ARM_PC:
        cover_run = [(ranges[i][0], min(run_partial[i][1], lens[i]))
                     if not run_cover_full[i] else (0, S_NONCE)
                     for i in range(n)]
        U_run = union_measure(cover_run)
        prof = multiplicity_profile(cover_run)
        run_scope = {
            "scope": "NR-global-run", "C_nonce": res.C_total, "U_nonce": U_run,
            "R_nonce": res.C_total - U_run,
            "rho_nonce": (res.C_total - U_run) / res.C_total,
            "M_ge2": measure_covered_at_least(prof, 2),
            "M_ge3": measure_covered_at_least(prof, 3),
            "m_max": max_multiplicity(prof),
            "mean_mult_reused": 0.0,
            "O_mean": 0.0, "O_median": 0.0, "O_p95": 0.0, "O_max": 0,
            "C_exact": res.C_total, "U_exact": res.C_total,
            "R_exact": 0, "rho_exact": 0.0,
        }
    else:
        cover_run = [(0, S_NONCE) if run_cover_full[i] else run_partial[i]
                     for i in range(n)]
        U_run = union_measure(cover_run)
        prof = multiplicity_profile([c for c in cover_run])
        # exact-input duplication at run scope: CONV never duplicates; MT
        # duplicates within epochs, aggregated from per-round exact counts.
        C_ex = res.C_total
        if arm in (ARM_CONV_ZERO, ARM_CONV_OFF):
            U_ex = C_ex
        else:
            U_ex = sum(int(r["round_U_exact"]) for r in acc.rows)
        run_scope = {
            "scope": "NR-global-run", "C_nonce": res.C_total, "U_nonce": U_run,
            "R_nonce": res.C_total - U_run,
            "rho_nonce": (res.C_total - U_run) / res.C_total,
            "M_ge2": measure_covered_at_least(prof, 2),
            "M_ge3": measure_covered_at_least(prof, 3),
            "m_max": max_multiplicity(prof),
            "mean_mult_reused": (
                sum(m * L for m, L in prof.items() if m >= 2)
                / max(1, measure_covered_at_least(prof, 2))),
            "O_mean": float(S_NONCE) if all(run_cover_full) else -1.0,
            "O_median": float(S_NONCE) if all(run_cover_full) else -1.0,
            "O_p95": float(S_NONCE) if all(run_cover_full) else -1.0,
            "O_max": S_NONCE if all(run_cover_full) else -1,
            "C_exact": C_ex, "U_exact": U_ex, "R_exact": C_ex - U_ex,
            "rho_exact": (C_ex - U_ex) / C_ex if C_ex else 0.0,
        }

    # ---- template-epoch scope (exact closed form, verified on partials) ----
    if arm in (ARM_CONV_ZERO, ARM_CONV_OFF):
        ep = {"C_nonce": S_NONCE, "U_nonce": S_NONCE, "rho_nonce": 0.0,
              "C_exact": S_NONCE, "U_exact": S_NONCE, "rho_exact": 0.0,
              "M_ge2": 0, "M_ge3": 0, "m_max": 1, "mean_mult_reused": 0.0}
    elif arm in (ARM_MT_ZERO, ARM_MT_OFF):
        ep = {"C_nonce": n * S_NONCE, "U_nonce": S_NONCE,
              "rho_nonce": (n - 1) / n,
              "C_exact": n * S_NONCE, "U_exact": S_NONCE,
              "rho_exact": (n - 1) / n, "M_ge2": S_NONCE,
              "M_ge3": S_NONCE if n >= 3 else 0, "m_max": n,
              "mean_mult_reused": float(n)}
    else:
        ep = {"C_nonce": S_NONCE, "U_nonce": S_NONCE, "rho_nonce": 0.0,
              "C_exact": S_NONCE, "U_exact": S_NONCE, "rho_exact": 0.0,
              "M_ge2": 0, "M_ge3": 0, "m_max": 1, "mean_mult_reused": 0.0}
    ep["scope"] = "NR-template-epoch"
    ep["R_nonce"] = ep["C_nonce"] - ep["U_nonce"]
    ep["R_exact"] = ep["C_exact"] - ep["U_exact"]
    ep["O_mean"] = float(S_NONCE) if arm in (ARM_MT_ZERO, ARM_MT_OFF) else 0.0
    ep["O_median"] = ep["O_mean"]
    ep["O_p95"] = ep["O_mean"]
    ep["O_max"] = int(ep["O_mean"])

    res.scope_rows = [run_scope, ep]
    res.round_rows = acc.rows if collect_rounds else []
    res.template_epochs_completed = run_epoch_full
    res.nonce_domain_exhaustions = exhaustions
    res.nonce_resets = resets
    return res
