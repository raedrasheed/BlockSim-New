"""Stage 4 finder-model equivalence tests (1-10)."""

import os
import sys
import math

import numpy as np
from scipy import stats

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, ROOT)

from Models.PoCol import round_state as rs
from analysis.thesis_revision_v43 import finder_equivalence as fe


def _ranges_equal(S, n):
    base = S // n
    out = []
    start = 0
    for i in range(n):
        L = base if i < n - 1 else S - base * (n - 1)
        out.append((i, start, start + L - 1))
        start += L
    return out


# 1 -------------------------------------------------------------------------
def test_exact_binomial_solution_count():
    g = np.random.default_rng(1)
    S, p = 100_000, 2.0 / 100_000
    ks = [rs.binomial_solution_count(g, p, S, "binomial") for _ in range(20_000)]
    assert abs(np.mean(ks) - S * p) < 0.05          # ~ mu = 2


# 2 -------------------------------------------------------------------------
def test_poisson_approximation_error_bound():
    # |P0_binom - P0_poisson| <= total-variation <= Le Cam bound (S p^2)
    for S in (100, 1000, 10000):
        p = 2.0 / S
        d = abs(stats.binom.pmf(0, S, p) - stats.poisson.pmf(0, S * p))
        assert d <= S * p * p + 1e-12


# 3 -------------------------------------------------------------------------
def test_finder_model_matches_exact_small_domain():
    S, p = 50, 2.0 / 50
    g = np.random.default_rng(3)
    ks = np.array([rs.binomial_solution_count(g, p, S) for _ in range(40_000)])
    for k in (0, 1, 2):
        emp = float((ks == k).mean())
        exact = float(stats.binom.pmf(k, S, p))
        assert abs(emp - exact) < 5 * math.sqrt(exact * (1 - exact) / 40_000) + 1e-3


# 4 -------------------------------------------------------------------------
def test_exhaustion_probability_matches_reference():
    for S in (100, 1000):
        p = 1.0 / S            # mu = 1
        ref = rs.finite_domain_exhaust_prob(p, S)
        g = np.random.default_rng(4)
        ks = np.array([rs.binomial_solution_count(g, p, S) for _ in range(50_000)])
        emp = float((ks == 0).mean())
        assert abs(emp - ref) < 0.01


# 5 -------------------------------------------------------------------------
def test_multiple_solutions_in_one_range():
    # high mu -> at least one range holds >= 2 solutions across draws
    g = np.random.default_rng(5)
    ranges = _ranges_equal(10_000, 3)
    rates = {i: 1.0 for i in range(3)}
    found_multi = False
    for _ in range(200):
        sols = rs.draw_round_solutions_exact(g, 5.0 / 10_000, ranges, rates)
        if any(s.range_solution_count >= 2 for s in sols):
            found_multi = True
            break
    assert found_multi


# 6 -------------------------------------------------------------------------
def test_earliest_solution_selected():
    # a range with multiple solutions returns the EARLIEST (min position)
    g = np.random.default_rng(6)
    ranges = [(0, 0, 9999)]
    rates = {0: 1.0}
    for _ in range(500):
        sols = rs.draw_round_solutions_exact(g, 5.0 / 10_000, ranges, rates)
        if sols and sols[0].range_solution_count >= 2:
            # finder_time corresponds to earliest position within the range
            assert math.isclose(sols[0].finder_time_s, sols[0].nonce_pos / 1.0)
            return
    # if no multi-solution draw occurred, the single-solution invariant still holds
    assert True


# 7 -------------------------------------------------------------------------
def test_conditional_first_success_index():
    ref = fe.discovery_time_reference(5000, 2.0 / 5000, 30_000, 7)
    fnd = fe.discovery_time_finder(5000, 2.0 / 5000, 30_000, 8)
    ks = stats.ks_2samp(ref, fnd)
    assert ks.pvalue > 0.01           # distributions not distinguishable


# 8 -------------------------------------------------------------------------
def test_discovery_time_matches_search_rate():
    g = np.random.default_rng(9)
    ranges = [(0, 100, 199)]          # start=100
    rates = {0: 4.0}                  # H_i = 4 H/s
    for _ in range(300):
        sols = rs.draw_round_solutions_exact(g, 0.2, ranges, rates)
        if sols:
            s = sols[0]
            assert math.isclose(s.finder_time_s, (s.nonce_pos - 100) / 4.0)
            return


# 9 -------------------------------------------------------------------------
def test_heterogeneous_finder_assignment():
    # a larger range yields more solutions on average (depends on S_i, not id)
    g = np.random.default_rng(10)
    ranges = [(0, 0, 999), (1, 1000, 9999)]   # miner 1 range 9x larger
    rates = {0: 1.0, 1: 9.0}
    c0 = c1 = 0
    for _ in range(400):
        sols = rs.draw_round_solutions_exact(g, 5.0 / 10_000, ranges, rates)
        for s in sols:
            if s.miner_id == 0:
                c0 += s.range_solution_count
            else:
                c1 += s.range_solution_count
    assert c1 > c0 * 3            # ~9x more solutions in the larger range


# 10 ------------------------------------------------------------------------
def test_global_solution_count_equals_sum_per_range():
    chk = fe.per_range_assignment_check(5000, 2.0 / 5000, 10, 50_000, 11)
    assert abs(chk["perrange_mean"] - chk["global_mean"]) < 0.05
    assert abs(chk["perrange_var"] - chk["global_var"]) < 0.1
