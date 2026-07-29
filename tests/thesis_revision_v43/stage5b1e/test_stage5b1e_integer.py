"""Stage 5B1E tests 21-25: exact integer candidate metrics."""

import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, ROOT)

from experiments.thesis_revision_v43.scenario_engine import EngineConfig, run_scenario
from experiments.thesis_revision_v43 import coverage as cov


# 21
def test_b2_counts_remain_python_integers():
    r = run_scenario(EngineConfig("B2", seed=1, miner_count=100))
    for k in ("total_candidate_evaluations", "distinct_candidate_identities", "duplicate_evaluations"):
        assert isinstance(r[k], int), (k, type(r[k]))


# 22
def test_large_counts_above_2pow53_exact():
    # candidate counts far exceed 2^53 (~9.0e15); integer reconciliation stays exact
    r = run_scenario(EngineConfig("B1", seed=20260201, miner_count=100))
    assert r["total_candidate_evaluations"] > 2 ** 53
    assert r["total_candidate_evaluations"] == \
        r["distinct_candidate_identities"] + r["duplicate_evaluations"]
    # coverage.py exact integer union also holds above 2^53
    S = 10 ** 17
    d = cov.b2_coverage_exact([0, 5 * 10 ** 16], [3 * 10 ** 16, 3 * 10 ** 16], S)
    assert isinstance(d["total_candidate_evaluations"], int)
    assert d["total_candidate_evaluations"] == \
        d["distinct_candidate_evaluations"] + d["duplicate_candidate_evaluations"]


# 23
def test_total_equals_distinct_plus_duplicate_exactly():
    for scen, kw in (("B0", {}), ("B1", {}), ("B2", {}),
                     ("B3_C1_CONTINUOUS_DISJOINT", {}),
                     ("C2", dict(allocation_policy="equal", idle_power_ratio=0.1))):
        r = run_scenario(EngineConfig(scen, seed=1, miner_count=100, **kw))
        # EXACT integer equality, no tolerance
        assert r["total_candidate_evaluations"] == \
            r["distinct_candidate_identities"] + r["duplicate_evaluations"]


# 24
def test_no_float_candidate_count_output():
    r = run_scenario(EngineConfig("B3_C1_CONTINUOUS_DISJOINT", seed=1, miner_count=100),
                     emit_detail=True)
    for k in ("total_candidate_evaluations", "distinct_candidate_identities",
              "duplicate_evaluations", "total_template_solution_count",
              "active_range_solution_count", "inactive_range_solution_count"):
        assert isinstance(r[k], int), (k, type(r[k]))
    for m in r["per_miner"]:
        assert isinstance(m["candidates_evaluated"], int)


# 25
def test_disjoint_duplicate_count_exactly_zero():
    for scen, kw in (("B0", {}), ("B3_C1_CONTINUOUS_DISJOINT", {}),
                     ("C2", dict(allocation_policy="equal", idle_power_ratio=0.1)),
                     ("B3_C1_CONTINUOUS_DISJOINT", dict(hash_rate_distribution="heterogeneous_moderate",
                                                        allocation_policy="weighted"))):
        r = run_scenario(EngineConfig(scen, seed=2, miner_count=100, **kw))
        assert r["duplicate_evaluations"] == 0           # disjoint -> exact zero overlap
