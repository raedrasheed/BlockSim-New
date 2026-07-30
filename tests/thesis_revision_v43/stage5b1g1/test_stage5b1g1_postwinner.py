"""Stage 5B1G.1 tests 14-15, 17-18: post-winner diagnostic work covers ALL active
non-winning miners and is never integrated into primary metrics (§4)."""

import os
import sys
import math

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, ROOT)

from experiments.thesis_revision_v43.scenario_engine import EngineConfig, run_scenario


def _nonstale():
    return run_scenario(EngineConfig("B3_C1_CONTINUOUS_DISJOINT", seed=3, miner_count=40, mu=1.0,
                                     propagation_delay_mean_s=0.42),
                        emit_detail=True, emit_generation_detail=True)


def _multi_stale():
    return run_scenario(EngineConfig("B3_C1_CONTINUOUS_DISJOINT", seed=5, miner_count=20, mu=4.0,
                                     network_hash_rate_hps=2000.0, target_block_interval_s=1.0,
                                     propagation_delay_mean_s=60.0),
                        emit_detail=True, emit_generation_detail=True)


# 14
def test_postwinner_work_counts_nonstale_recipients():
    r = _nonstale()
    # every active non-winner mines during the propagation window even with no stale
    assert r["stale_block_count"] == 0                    # this regime yields no stale producers
    assert r["stale_producer_postwinner_candidate_evaluations"] == 0
    assert r["post_winner_candidate_evaluations"] > 0     # yet post-winner work is counted
    assert r["post_winner_active_time_s"] > 0.0
    # the retained legacy field equals the COMPLETE post-winner total (all non-winners)
    assert r["stale_race_candidate_evaluations"] == r["post_winner_candidate_evaluations"]


# 15
def test_postwinner_work_counts_stale_producers():
    r = _multi_stale()
    assert r["stale_block_count"] > 0
    assert r["stale_producer_postwinner_candidate_evaluations"] > 0
    # complete post-winner total includes producers AND non-producers -> >= producer subset
    assert r["post_winner_candidate_evaluations"] >= r["stale_producer_postwinner_candidate_evaluations"]


# 17
def test_postwinner_work_not_in_primary_energy():
    # continuous full-participation total energy is fixed by A1 and unchanged by the
    # (non-integrated) post-winner diagnostic work.
    for scen in ("B0", "B1", "B2", "B3_C1_CONTINUOUS_DISJOINT"):
        r = run_scenario(EngineConfig(scen, seed=1, miner_count=50), emit_detail=True)
        assert math.isclose(r["total_energy_kwh"], 8.420833333333333, rel_tol=1e-12)
        assert r["post_winner_energy_not_integrated"] is True
        assert r["stale_race_energy_not_integrated"] is True


# 18
def test_postwinner_work_not_in_primary_candidate_counts():
    r = _multi_stale()
    # primary per-generation candidate rows sum EXACTLY to the network total; the
    # post-winner diagnostic work is separate and NOT added into that total.
    s = sum(g["candidates_evaluated_this_generation"] for g in r["per_miner_generation"])
    assert s == r["total_candidate_evaluations"]
    assert (r["total_candidate_evaluations"]
            == r["distinct_candidate_identities"] + r["duplicate_evaluations"])
    assert r["post_winner_candidate_evaluations"] > 0     # separate, non-zero, not folded in
