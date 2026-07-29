"""Stage 5B1F tests 21-27: per-miner per-generation accounting."""

import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, ROOT)

from experiments.thesis_revision_v43.scenario_engine import EngineConfig, run_scenario
from experiments.thesis_revision_v43 import schemas


def _run(scen="B3_C1_CONTINUOUS_DISJOINT", **kw):
    kw.setdefault("miner_count", 30)
    kw.setdefault("seed", 1)
    return run_scenario(EngineConfig(scen, **kw), emit_detail=True, emit_generation_detail=True)


# 21
def test_per_miner_generation_schema():
    r = _run(inactive_miner_fraction=0.15)
    assert r["per_miner_generation"]
    for g in r["per_miner_generation"][:200]:
        assert schemas.validate_fields(g, schemas.PER_MINER_GENERATION_FIELDS) == []


# 22
def test_generation_rows_sum_to_network_total():
    for scen, kw in (("B3_C1_CONTINUOUS_DISJOINT", dict(inactive_miner_fraction=0.15)),
                     ("C2", dict(allocation_policy="equal", idle_power_ratio=0.1)),
                     ("B0", {})):
        r = _run(scen, **kw)
        s = sum(g["candidates_evaluated_this_generation"] for g in r["per_miner_generation"])
        assert s == r["total_candidate_evaluations"]


# 23
def test_final_partial_generation_unsearched():
    r = run_scenario(EngineConfig("B1", seed=20260201, miner_count=100),
                     emit_detail=True, emit_generation_detail=True)
    last_gen = max(g["template_generation_id"] for g in r["per_miner_generation"])
    rows = [g for g in r["per_miner_generation"] if g["template_generation_id"] == last_gen]
    # unsearched-this-generation is computed directly, not via modulo of cumulative
    for g in rows:
        assert g["unsearched_candidates_this_generation"] >= 0


# 24
def test_cumulative_separate_from_generation_progress():
    r = _run()
    for g in r["per_miner_generation"]:
        # cumulative >= this-generation (they are distinct fields)
        assert g["cumulative_candidates_evaluated"] >= g["candidates_evaluated_this_generation"]


# 25
def test_no_modulo_remaining_shortcut():
    # remaining is derived from assigned - this-generation, not cumulative % range
    r = _run(hash_rate_distribution="heterogeneous_moderate", allocation_policy="equal")
    for g in r["per_miner_generation"]:
        if g["assigned_range_size"] and g["inactive_candidates_this_generation"] == 0:
            assert (g["candidates_evaluated_this_generation"]
                    + g["unsearched_candidates_this_generation"]) == g["assigned_range_size"]


# 26
def test_c2_idle_generation_rows():
    r = _run("C2", hash_rate_distribution="heterogeneous_moderate", allocation_policy="equal",
             idle_power_ratio=0.1)
    assert any(g["idle_time_s"] > 0.0 for g in r["per_miner_generation"])


# 27
def test_b3_nonproductive_active_generation_rows():
    r = _run("B3_C1_CONTINUOUS_DISJOINT", hash_rate_distribution="heterogeneous_moderate",
             allocation_policy="equal")
    # B3/C1 continuous power: some rows have non-productive active time, zero idle
    assert any(g["active_nonproductive_time_s"] > 0.0 for g in r["per_miner_generation"])
    assert all(g["idle_time_s"] == 0.0 for g in r["per_miner_generation"])
