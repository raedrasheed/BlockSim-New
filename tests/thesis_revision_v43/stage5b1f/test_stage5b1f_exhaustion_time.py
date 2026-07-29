"""Stage 5B1F tests 11-20: B2 exhaustion time and unified time convention."""

import os
import sys
import math

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, ROOT)

from experiments.thesis_revision_v43 import coverage as cov
from experiments.thesis_revision_v43.scenario_engine import EngineConfig, run_scenario, _completed
from fractions import Fraction


# 11
def test_b2_exhaustion_union_covers_domain():
    for S, starts, rates in [(20, [0, 5, 10, 15], [1.0, 1.0, 1.0, 1.0]), (30, [0, 7, 20], [2.0, 1.0, 3.0])]:
        t_ex, counts = cov.b2_exhaustion_time(starts, rates, S)
        assert counts["distinct_candidate_evaluations"] == S


# 12
def test_b2_before_exhaustion_union_incomplete():
    S, starts, rates = 30, [0, 7, 20], [2.0, 1.0, 3.0]
    t_ex, _ = cov.b2_exhaustion_time(starts, rates, S)
    before = cov.coverage_at_time(starts, rates, S, t_ex * 0.999)["distinct_candidate_evaluations"]
    assert before < S


# 13
def test_b2_overlap_delays_exhaustion():
    S = 20
    spread = cov.b2_exhaustion_time([0, 10], [1.0, 1.0], S)[0]      # well spread
    overlap = cov.b2_exhaustion_time([0, 1], [1.0, 1.0], S)[0]      # nearly identical starts
    assert overlap > spread                                        # overlap wastes work -> later exhaustion


# 14
def test_b2_exhaustion_matches_small_domain_reference():
    for S, starts, rates in [(20, [0, 5, 10, 15], [1.0, 1.0, 1.0, 1.0]),
                             (30, [0, 7, 20], [2.0, 1.0, 3.0]), (12, [3, 3, 3], [1.0, 1.0, 1.0])]:
        t_ex, _ = cov.b2_exhaustion_time(starts, rates, S)
        ref = cov.exhaustion_time_reference_small(starts, rates, S)
        assert math.isclose(t_ex, ref, rel_tol=1e-4)


# 15
def test_inactive_miner_not_in_b2_coverage():
    # a miner with rate 0 contributes no path
    S = 20
    with_inactive = cov.coverage_at_time([0, 5, 10], [1.0, 0.0, 1.0], S, 5)
    without = cov.coverage_at_time([0, 10], [1.0, 1.0], S, 5)
    assert with_inactive["distinct_candidate_evaluations"] == without["distinct_candidate_evaluations"]


# 16
def test_no_repeated_full_traversal():
    # each miner capped at one full traversal S
    S = 10
    c = cov.coverage_at_time([0], [5.0], S, 1000.0)      # would sweep 5000 without cap
    assert c["total_candidate_evaluations"] == S


# 17
def test_no_candidate_at_time_zero():
    assert _completed(1000, Fraction(0), 10 ** 9) == 0


# 18
def test_first_candidate_at_one_hash_interval():
    H = 1000
    assert _completed(H, Fraction(1, H), 10 ** 9) == 1        # first candidate completes at 1/H
    assert _completed(H, Fraction(1, H) - Fraction(1, 10 * H), 10 ** 9) == 0   # just before


# 19
def test_b1_b2_disjoint_same_step_time_convention():
    # all scenarios: completed = floor(rate*t); discovery of offset d at (d+1)/rate
    H = 500
    for d in (0, 1, 7, 99):
        t = Fraction(d + 1, H)
        assert _completed(H, t, 10 ** 9) == d + 1        # exactly d+1 candidates completed at discovery


# 20
def test_exact_boundary_candidate_count():
    H = 3
    assert _completed(H, Fraction(1, H), 100) == 1
    assert _completed(H, Fraction(2, H), 100) == 2
    assert _completed(H, Fraction(2, H) - Fraction(1, 100), 100) == 1   # just below boundary
