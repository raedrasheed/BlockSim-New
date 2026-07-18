"""Continuous distributed-effort experiment — 20 required invariants + N=10 formula.

Run:  python -m pytest tests/test_continuous_distributed_effort.py -v
  or:  python tests/test_continuous_distributed_effort.py
"""
import os
import sys
import math

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from experiments.nonce_partition.partition import (
    partition_nonce_domain, range_size, ranges_are_disjoint, ranges_cover,
)
from experiments.continuous_distributed_effort.configuration import (
    ExperimentConfig, PowerConfig, build_miners,
    MODE_A, MODE_B, MODE_C1, MODE_C2, SCHED_IMMEDIATE, SCHED_FIXED_SLOT, HW_H1, HW_H2,
    AGG_ACTIVE_POWER_W,
)
from experiments.continuous_distributed_effort.power_states import Miner, ACTIVE, IDLE, SLEEP
from experiments.continuous_distributed_effort.round_model import (
    simulate_continuous, deterministic_outcome, stochastic_outcome,
)
from experiments.continuous_distributed_effort.stochastic_template import (
    pocol_disjoint_outcome, duplicate_baseline_outcome,
)


def _cfg(mode, N=10, M=6000, sched=SCHED_FIXED_SLOT, hw=HW_H2, q=0.10, s=0.0,
         sim=600.0, slot=600.0, p=None, seed=0, use_sleep=False):
    return ExperimentConfig(
        N=N, M=M, mode=mode, schedule=sched, hardware=hw,
        power=PowerConfig(idle_ratio=q, sleep_ratio=s, use_sleep=use_sleep),
        sim_seconds=sim, slot_seconds=slot, p_success=p, seed=seed)


def _run(cfg, outcome_fn=deterministic_outcome):
    return simulate_continuous(cfg, outcome_fn)


# ===========================================================================
# Exact deterministic formula (methodology section 8): N=10, T=600, P=100
# ===========================================================================
def test_exact_formula_N10():
    for q, exp_ratio in [(0.0, 0.1), (0.10, 0.19), (1.0, 1.0)]:
        mA, _ = _run(_cfg(MODE_A, q=q))
        mB, _ = _run(_cfg(MODE_B, q=q))
        assert math.isclose(mA["total_energy_j"], 600000.0)
        assert math.isclose(mB["total_energy_j"] / mA["total_energy_j"], exp_ratio, rel_tol=1e-9)
    # explicit joule checks
    mA, _ = _run(_cfg(MODE_A, q=0.0)); mB, _ = _run(_cfg(MODE_B, q=0.0))
    assert math.isclose(mA["total_energy_j"], 600000.0)
    assert math.isclose(mB["total_energy_j"], 60000.0)


# ===========================================================================
# 1-3, 5: partitioning / duplicate accounting
# ===========================================================================
def test_inv1_pocol_ranges_disjoint():
    for N in (1, 2, 10, 100, 500):
        assert ranges_are_disjoint(partition_nonce_domain(0, 1_000_000, N))


def test_inv2_range_union_is_domain():
    for N in (1, 2, 10, 100, 500):
        assert ranges_cover(partition_nonce_domain(0, 1_000_000, N), 0, 1_000_000)


def test_inv3_no_pocol_header_evaluated_twice():
    o = deterministic_outcome(_cfg(MODE_B, N=10, M=6000))
    # disjoint ranges + each evaluated within its own range => no shared nonce
    assert ranges_are_disjoint(o.ranges)
    assert o.duplicate_evals == 0


def test_inv4_duplicate_baseline_repeats_headers():
    o = deterministic_outcome(_cfg(MODE_A, N=10, M=6000))
    assert all(r == (0, 6000) for r in o.ranges)          # same complete domain
    assert o.duplicate_evals == (10 - 1) * 6000           # repeated work
    assert o.duplicate_evals > 0


def test_inv5_unique_and_duplicate_reported_separately():
    a = deterministic_outcome(_cfg(MODE_A, N=10, M=6000))
    b = deterministic_outcome(_cfg(MODE_B, N=10, M=6000))
    assert a.unique_evals == 6000 and a.duplicate_evals == 54000
    assert b.unique_evals == 6000 and b.duplicate_evals == 0


# ===========================================================================
# 6-7: energy integration and state-time conservation
# ===========================================================================
def test_inv6_energy_is_integral_of_power_over_time():
    m = Miner(0, hashrate_hps=1.0, active_power_w=100, idle_power_w=10, sleep_power_w=1)
    m.transition(IDLE, 60.0)      # ACTIVE 0..60
    m.transition(SLEEP, 200.0)    # IDLE 60..200
    m.finalize(600.0)             # SLEEP 200..600
    expected = 100 * 60 + 10 * 140 + 1 * 400
    assert math.isclose(m.cumulative_energy_j, expected)
    assert math.isclose(m.cumulative_hashes, 1.0 * 60)   # hashes only while ACTIVE


def test_inv7_total_state_time_equals_sim():
    for mode in (MODE_A, MODE_B, MODE_C1, MODE_C2):
        _, miners = _run(_cfg(mode, sim=10000.0, slot=600.0, q=0.1))
        for m in miners:
            assert math.isclose(m.total_state_time_s, 10000.0, abs_tol=1e-6)


# ===========================================================================
# 8-9: fixed-slot idle behaviour and global stopping
# ===========================================================================
def test_inv8_no_active_after_completing_range_fixed_slot():
    _, miners = _run(_cfg(MODE_B, N=10, M=6000, sim=600.0, slot=600.0, q=0.1))
    for m in miners:
        assert m.active_time_s < 600.0            # finished early
        assert m.idle_time_s > 0.0                # idled the remainder
        assert math.isclose(m.active_time_s, 60.0, abs_tol=1e-6)


def test_inv9_no_evaluation_after_global_discovery():
    o = deterministic_outcome(_cfg(MODE_B, N=10, M=6000))
    assert max(o.evaluated) <= o.t_star


# ===========================================================================
# 10-13: scheduling / power-ratio behaviour
# ===========================================================================
def test_inv10_immediate_restart_is_energy_neutral():
    mA, _ = _run(_cfg(MODE_A, sched=SCHED_IMMEDIATE, sim=10000.0, q=0.0))
    mB, _ = _run(_cfg(MODE_B, sched=SCHED_IMMEDIATE, sim=10000.0, q=0.0))
    assert math.isclose(mA["total_energy_j"], mB["total_energy_j"])
    assert math.isclose(mA["pct_time_active"], 100.0)


def test_inv11_fixed_slot_matches_formula():
    for N in (2, 5, 10, 20, 100):
        for q in (0.0, 0.05, 0.2, 0.5):
            M = 600 * N                      # divisible, r=M/slot=N
            mA, _ = _run(_cfg(MODE_A, N=N, M=M, q=q))
            mB, _ = _run(_cfg(MODE_B, N=N, M=M, q=q))
            ratio = mB["total_energy_j"] / mA["total_energy_j"]
            assert math.isclose(ratio, 1.0 / N + q * (1 - 1.0 / N), rel_tol=1e-9)


def test_inv12_idle_ratio_one_no_saving():
    mA, _ = _run(_cfg(MODE_A, q=1.0)); mB, _ = _run(_cfg(MODE_B, q=1.0))
    assert math.isclose(mA["total_energy_j"], mB["total_energy_j"])


def test_inv13_idle_ratio_zero_max_saving():
    for N in (2, 10, 100):
        M = 600 * N
        mA, _ = _run(_cfg(MODE_A, N=N, M=M, q=0.0))
        mB, _ = _run(_cfg(MODE_B, N=N, M=M, q=0.0))
        red = 1 - mB["total_energy_j"] / mA["total_energy_j"]
        assert math.isclose(red, 1 - 1.0 / N, rel_tol=1e-9)


# ===========================================================================
# 14-15: candidate budgets
# ===========================================================================
def test_inv14_C1_and_B_equal_total_budget():
    o_b = deterministic_outcome(_cfg(MODE_B, N=10, M=6000))
    o_c1 = deterministic_outcome(_cfg(MODE_C1, N=10, M=6000))
    assert sum(range_size(r) for r in o_b.ranges) == 6000
    assert sum(range_size(r) for r in o_c1.ranges) == 6000


def test_inv15_C2_total_budget_is_N_times_M():
    o_c2 = deterministic_outcome(_cfg(MODE_C2, N=10, M=6000))
    assert sum(range_size(r) for r in o_c2.ranges) == 10 * 6000


# ===========================================================================
# 16-17: corrected stochastic winner (min local time, not min global nonce)
# ===========================================================================
def test_inv16_17_winner_is_min_local_time():
    M, N, p = 1_000_000, 10, 5e-5
    later_wins = 0
    for seed in range(200):
        B = pocol_disjoint_outcome(M, N, p, seed)
        A = duplicate_baseline_outcome(M, N, p, seed)
        if not B["solution_found"]:
            continue
        # B winner's local step is the minimum local success across ranges
        ranges = B["ranges"]
        assert B["winning_nonce"] == ranges[B["winner_id"]][0] + B["t_star"] - 1
        if A["solution_found"] and B["winning_nonce"] > A["winning_nonce"]:
            later_wins += 1
    assert later_wins > 0, "a numerically later nonce should sometimes win on local time"


# ===========================================================================
# 18-19: reproducibility and state isolation
# ===========================================================================
def test_inv18_deterministic_under_fixed_seed():
    cfg = _cfg(MODE_B, N=50, M=1_000_000, p=1e-5, seed=7, sim=10000.0)
    m1, _ = _run(cfg, stochastic_outcome)
    m2, _ = _run(cfg, stochastic_outcome)
    assert m1 == m2


def test_inv19_no_global_state_contamination():
    # run A, then B, then A again in-process; the model is pure-functional, so the
    # second A must exactly equal the first (no leakage). The matrix runner also
    # uses fresh subprocesses per run.
    a1, _ = _run(_cfg(MODE_A, N=20, M=12000, q=0.1))
    _b, _ = _run(_cfg(MODE_B, N=20, M=12000, q=0.1))
    a2, _ = _run(_cfg(MODE_A, N=20, M=12000, q=0.1))
    assert a1 == a2


# ===========================================================================
# 20: the existing corrected 8.4208 kWh experiment is unchanged
# ===========================================================================
def test_inv20_corrected_experiment_unchanged():
    import csv
    path = os.path.join(os.path.dirname(__file__), "..", "results", "corrected", "raw_runs.csv")
    assert os.path.exists(path), "results/corrected/raw_runs.csv must exist untouched"
    with open(path) as fh:
        rows = list(csv.DictReader(fh))
    energies = [float(r["energy_kWh"]) for r in rows]
    assert energies, "no rows in corrected raw_runs.csv"
    for e in energies:
        assert math.isclose(e, 8.420833333333333, rel_tol=1e-6), f"corrected energy changed: {e}"
    # cross-check: H1 IMMEDIATE_RESTART over 10000 s reproduces 8.4208 kWh
    m, _ = _run(_cfg(MODE_A, N=100, M=600 * 100, hw=HW_H1, sched=SCHED_IMMEDIATE,
                     sim=10000.0, q=0.0))
    assert math.isclose(m["total_energy_kwh"], 8.420833333333333, rel_tol=1e-6)
    assert math.isclose(AGG_ACTIVE_POWER_W, 3031.5)


def _run_all():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for fn in fns:
        try:
            fn(); print(f"PASS  {fn.__name__}")
        except AssertionError as e:
            failed += 1; print(f"FAIL  {fn.__name__}: {e}")
        except Exception as e:
            failed += 1; print(f"ERROR {fn.__name__}: {type(e).__name__}: {e}")
    print(f"\n{len(fns)-failed}/{len(fns)} passed")
    return failed


if __name__ == "__main__":
    sys.exit(1 if _run_all() else 0)
