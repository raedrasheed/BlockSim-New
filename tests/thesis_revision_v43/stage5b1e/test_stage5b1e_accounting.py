"""Stage 5B1E tests 14-20: exact per-miner search-progress accounting."""

import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, ROOT)

from experiments.thesis_revision_v43.scenario_engine import EngineConfig, run_scenario


def _run(scen="B3_C1_CONTINUOUS_DISJOINT", **kw):
    kw.setdefault("miner_count", 60)
    kw.setdefault("seed", 1)
    return run_scenario(EngineConfig(scen, **kw), emit_detail=True)


# 14
def test_per_miner_searched_uses_actual_progress():
    r = _run(hash_rate_distribution="heterogeneous_moderate", allocation_policy="equal")
    # candidates_evaluated is the real cumulative progress, not a single-range constant
    vals = {m["candidates_evaluated"] for m in r["per_miner"]}
    assert len(vals) > 1                                    # heterogeneous -> different progress


# 15
def test_early_winner_leaves_unsearched_candidates():
    r = _run(hash_rate_distribution="heterogeneous_moderate", allocation_policy="weighted")
    # at least one active miner did not fully search its range in the final state
    assert any(m["final_state"] != "offline" and m["last_evaluated_position"] is not None
               and m["range_end"] is not None and m["last_evaluated_position"] < m["range_end"]
               for m in r["per_miner"])


# 16
def test_cumulative_progress_across_generations():
    r = _run(mu=2.0)
    # cumulative candidates can exceed a single range size (re-search on new templates)
    assert any(m["candidates_evaluated"] > (m["range_size"] or 0) for m in r["per_miner"]) or \
        r["template_generations"] == 1


# 17
def test_per_miner_sum_equals_network_total():
    for scen, kw in (("B3_C1_CONTINUOUS_DISJOINT", {}),
                     ("C2", dict(hash_rate_distribution="heterogeneous_moderate",
                                 allocation_policy="equal", idle_power_ratio=0.1)),
                     ("B0", dict(inactive_miner_fraction=0.15))):
        r = _run(scen, **kw)
        assert sum(m["candidates_evaluated"] for m in r["per_miner"]) == r["total_candidate_evaluations"]


# 18
def test_range_domain_exact_reconciliation():
    r = _run("B0", inactive_miner_fraction=0.15)
    for t in r["per_template"]:
        assert (t["searched_domain_size"] + t["unsearched_domain_size"]
                + t["inactive_domain_size"]) == t["assigned_domain_size"]


# 19
def test_inactive_miner_summary():
    r = _run("B0", inactive_miner_fraction=0.30)
    inact = [m for m in r["per_miner"] if m["final_state"] == "offline"]
    assert inact
    for m in inact:
        assert m["candidates_evaluated"] == 0
        assert m["stop_reason"] == "inactive"
        assert m["offline_time_s"] > 0.0


# 20
def test_stop_reasons_complete():
    valid = {"solution_found", "range_exhausted", "template_refreshed", "inactive",
             "simulation_cutoff", "competing_block_received", "reallocated"}
    for scen, kw in (("B3_C1_CONTINUOUS_DISJOINT", dict(inactive_miner_fraction=0.15)),
                     ("C2", dict(allocation_policy="equal", idle_power_ratio=0.1)),
                     ("B1", {}), ("B2", {})):
        r = _run(scen, **kw)
        for m in r["per_miner"]:
            assert m["stop_reason"] in valid, (scen, m["stop_reason"])
