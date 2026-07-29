"""Stage 5B1A tests 1-8: exact B2 circular coverage vs exhaustive reference."""

import os
import sys
import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, ROOT)

from experiments.thesis_revision_v43 import coverage as cov
from experiments.thesis_revision_v43.scenario_engine import EngineConfig, run_scenario


# 1
def test_b2_interval_union_matches_exhaustive_no_wrap():
    S = 50
    starts = [0, 10, 25, 40]
    lengths = [8, 8, 8, 5]                       # no wrap
    exact = cov.b2_coverage_exact(starts, lengths, S)
    ref = cov.exhaustive_coverage_reference(starts, lengths, S)
    assert exact == ref


# 2
def test_b2_interval_union_matches_exhaustive_wrap():
    S = 50
    starts = [45, 48, 0, 30]
    lengths = [10, 6, 5, 5]                      # 45+10 and 48+6 wrap
    exact = cov.b2_coverage_exact(starts, lengths, S)
    ref = cov.exhaustive_coverage_reference(starts, lengths, S)
    assert exact == ref
    assert exact["distinct_candidate_evaluations"] == ref["distinct_candidate_evaluations"]


# 3
def test_b2_interval_union_multiple_wrapped_paths():
    S = 20
    starts = [15, 18, 19, 17]
    lengths = [10, 10, 10, 10]                   # all wrap, heavy overlap
    exact = cov.b2_coverage_exact(starts, lengths, S)
    ref = cov.exhaustive_coverage_reference(starts, lengths, S)
    assert exact == ref


# 4
def test_b2_full_domain_coverage():
    S = 30
    one = cov.b2_coverage_exact([7], [S], S)
    assert one["distinct_candidate_evaluations"] == S
    multi = cov.b2_coverage_exact([0, 11, 29], [S, S, S], S)
    assert multi["distinct_candidate_evaluations"] == S
    assert multi["duplicate_candidate_evaluations"] == 2 * S


# 5
def test_b2_duplicate_count_exact():
    S = 100
    # two identical arcs -> full overlap
    d = cov.b2_coverage_exact([10, 10], [20, 20], S)
    assert d["distinct_candidate_evaluations"] == 20
    assert d["duplicate_candidate_evaluations"] == 20
    # brute force agrees exactly
    ref = cov.exhaustive_coverage_reference([10, 10], [20, 20], S)
    assert d == ref


# 6
def test_b2_winner_matches_exhaustive_reference():
    S = 37
    starts = [3, 20, 30, 11]
    rates = [1.0, 2.0, 0.5, 3.0]
    pos = np.array([15, 33, 5])
    wt, wid = cov.b2_winner(pos, starts, rates, S)
    wt_ref, wid_ref = cov.exhaustive_winner_reference(pos, starts, rates, S)
    assert abs(wt - wt_ref) < 1e-12
    assert wid == wid_ref


# 7
def test_b2_large_domain_no_enumeration():
    # S ~ 1e17: an enumerating implementation would hang/OOM. Interval method is O(n).
    S = 10 ** 17
    starts = [0, 3 * 10 ** 16, 9 * 10 ** 16]
    lengths = [10 ** 15, 10 ** 15, 2 * 10 ** 16]
    d = cov.b2_coverage_exact(starts, lengths, S)
    assert d["total_candidate_evaluations"] == sum(lengths)
    assert d["distinct_candidate_evaluations"] <= d["total_candidate_evaluations"]
    assert d["distinct_candidate_evaluations"] > 0


# 8
def test_b2_total_equals_distinct_plus_duplicate():
    S = 1000
    rng = np.random.default_rng(0)
    for _ in range(50):
        n = int(rng.integers(1, 12))
        starts = [int(x) for x in rng.integers(0, S, n)]
        lengths = [int(x) for x in rng.integers(0, S + 1, n)]
        d = cov.b2_coverage_exact(starts, lengths, S)
        assert d["total_candidate_evaluations"] == \
            d["distinct_candidate_evaluations"] + d["duplicate_candidate_evaluations"]
    # and end-to-end through the engine at full scale. The identity total ==
    # distinct + duplicate is EXACT in integer space (asserted above); at engine
    # scale the counts are ~1e18 floats, so compare with a relative tolerance
    # (float64 loses integer exactness above 2^53).
    import math
    r = run_scenario(EngineConfig("B2", seed=1, miner_count=100))
    assert math.isclose(r["total_candidate_evaluations"],
                        r["distinct_candidate_identities"] + r["duplicate_evaluations"],
                        rel_tol=1e-12)
