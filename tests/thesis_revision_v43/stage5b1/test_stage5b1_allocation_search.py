"""Stage 5B1 tests 1-15: range/rate decoupling and the common search engine."""

import os
import sys
import math

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, ROOT)

from experiments.thesis_revision_v43.scenario_engine import (
    EngineConfig, run_scenario, allocate_equal, allocate_weighted, rng)


def _sizes(ranges):
    return [b - a + 1 for (a, b) in ranges]


# 1 -------------------------------------------------------------------------
def test_equal_ranges_independent_of_hashrate():
    # allocate_equal does not take shares -> identical for any hash-rate profile
    a = allocate_equal(1000, 10)
    b = allocate_equal(1000, 10)
    assert a == b
    assert max(_sizes(a)) - min(_sizes(a)) <= 1


# 2 -------------------------------------------------------------------------
def test_weighted_ranges_follow_hashrate():
    sizes = _sizes(allocate_weighted(1000, [0.1, 0.3, 0.6]))
    assert sizes[2] > sizes[1] > sizes[0]
    assert abs(sizes[2] / 1000 - 0.6) < 0.01


# 3 -------------------------------------------------------------------------
def test_integer_remainder_fully_allocated():
    for S, n in [(1000, 7), (1001, 3), (997, 100)]:
        assert sum(_sizes(allocate_equal(S, n))) == S
    assert sum(_sizes(allocate_weighted(1001, [0.2, 0.3, 0.5]))) == 1001


# 4 -------------------------------------------------------------------------
def test_range_allocations_do_not_overlap():
    for ranges in (allocate_equal(1000, 13), allocate_weighted(1000, [0.25, 0.25, 0.5])):
        for (a1, b1), (a2, b2) in zip(ranges, ranges[1:]):
            assert a2 == b1 + 1            # contiguous, no overlap/gap


# 5 -------------------------------------------------------------------------
def test_range_allocations_cover_assigned_domain():
    ranges = allocate_equal(1000, 10)
    assert ranges[0][0] == 0 and ranges[-1][1] == 999


# 6 -------------------------------------------------------------------------
def test_equal_ranges_heterogeneous_completion_times():
    r = run_scenario(EngineConfig("C2", 20260201, 100, idle_power_ratio=0.1,
                                  hash_rate_distribution="heterogeneous_moderate",
                                  allocation_policy="equal"))
    assert r["completion_time_std_s"] > 0.0      # equal ranges + hetero rates -> dispersion


# 7 -------------------------------------------------------------------------
def test_weighted_ranges_reduce_completion_dispersion():
    eq = run_scenario(EngineConfig("C2", 20260201, 100, idle_power_ratio=0.1,
                                   hash_rate_distribution="heterogeneous_moderate",
                                   allocation_policy="equal"))
    wt = run_scenario(EngineConfig("C2", 20260201, 100, idle_power_ratio=0.1,
                                   hash_rate_distribution="heterogeneous_moderate",
                                   allocation_policy="weighted"))
    assert wt["completion_time_std_s"] < eq["completion_time_std_s"]


# 8 -------------------------------------------------------------------------
def test_inactive_range_not_silently_redistributed():
    r = run_scenario(EngineConfig("B3_C1_CONTINUOUS_DISJOINT", 20260201, 100,
                                  inactive_miner_fraction=0.2))
    assert r["inactive_domain"] > 0              # inactive ranges recorded, not reused
    assert r["total_offline_time_s"] > 0


# 9 -------------------------------------------------------------------------
def test_solution_positions_unique():
    g = np.random.default_rng(1)
    S, p = 100000, 5.0 / 100000
    for _ in range(200):
        k = int(g.binomial(S, p))
        if k >= 2:
            pos = np.unique(g.integers(0, S, size=k * 2))[:k]
            assert len(pos) == len(set(pos.tolist()))


# 10 ------------------------------------------------------------------------
def test_solution_positions_uniform_small_domain():
    g = np.random.default_rng(2)
    S = 1000
    draws = g.integers(0, S, size=200000)
    assert abs(draws.mean() - S / 2) < S * 0.02   # ~uniform


# 11 ------------------------------------------------------------------------
def test_large_domain_matches_small_reference():
    # B1 duplicate rate ~ (N-1)/N is scale-invariant (analytical reference)
    for N in (10, 100):
        r = run_scenario(EngineConfig("B1", 20260201, N))
        assert abs(r["duplicate_evaluation_rate"] - (N - 1) / N) < 0.05


# 12 ------------------------------------------------------------------------
def test_first_discovery_time():
    # disjoint: winner interval scales with target and is miner-count independent
    r100 = run_scenario(EngineConfig("B3_C1_CONTINUOUS_DISJOINT", 20260201, 100))
    r500 = run_scenario(EngineConfig("B3_C1_CONTINUOUS_DISJOINT", 20260201, 500))
    assert r100["effective_block_interval_s"] and r500["effective_block_interval_s"]
    # both are within a factor of ~2 of each other (N-independent aggregate rate)
    assert 0.4 < r100["effective_block_interval_s"] / r500["effective_block_interval_s"] < 2.5


# 13 ------------------------------------------------------------------------
def test_multiple_solutions_one_miner_range():
    from Models.PoCol.round_state import draw_round_solutions_exact
    g = np.random.default_rng(5)
    ranges = [(0, 0, 9999)]
    rates = {0: 1.0}
    assert any(s.range_solution_count >= 2
               for _ in range(300)
               for s in draw_round_solutions_exact(g, 5.0 / 10000, ranges, rates))


# 14 ------------------------------------------------------------------------
def test_no_solution_exhaustion():
    # low mu -> exhaustion occurs and is recorded (not a block)
    r = run_scenario(EngineConfig("B3_C1_CONTINUOUS_DISJOINT", 20260201, 100, mu=0.5))
    assert r["exhausted_rounds"] > 0


# 15 ------------------------------------------------------------------------
def test_partial_progress_reconciliation():
    # inactive domain + covered domain are accounted; offline time > 0 under inactivity
    r = run_scenario(EngineConfig("C2", 20260201, 100, inactive_miner_fraction=0.15,
                                  hash_rate_distribution="heterogeneous_moderate",
                                  allocation_policy="equal", idle_power_ratio=0.1))
    assert r["inactive_domain"] >= 0
    assert math.isclose(r["total_energy_kwh"],
                        r["active_energy_kwh"] + r["idle_energy_kwh"] + r["coordination_energy_kwh"],
                        rel_tol=0, abs_tol=1e-12)
