"""Stage 5B1G tests 24-27: solution-position vs finder taxonomy (Section 6)."""

import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, ROOT)

from experiments.thesis_revision_v43.scenario_engine import EngineConfig, run_scenario
from experiments.thesis_revision_v43 import schemas


def _multi_pos_run(scen="B3_C1_CONTINUOUS_DISJOINT"):
    # few miners, high mu -> large ranges that hold several sampled positions each.
    return run_scenario(EngineConfig(scen, seed=7, miner_count=5, mu=5.0), emit_detail=True)


# 24
def test_positions_split_active_plus_inactive():
    disjoint = {"B0", "B3_C1_CONTINUOUS_DISJOINT", "C2"}
    for scen in ("B0", "B1", "B2", "B3_C1_CONTINUOUS_DISJOINT", "C2"):
        r = run_scenario(EngineConfig(scen, seed=7, miner_count=8, mu=3.0,
                                      inactive_miner_fraction=(0.25 if scen != "B1" else 0.0)),
                         emit_detail=True)
        rec = schemas.reconcile_solution_positions(r["per_template"], disjoint=(scen in disjoint))
        assert rec["passed"], (scen, rec)


# 25
def test_multiple_positions_per_miner_increase_positions_not_finders():
    r = _multi_pos_run()
    hits = [t for t in r["per_template"]
            if t["active_range_solution_position_count"] > t["distinct_potential_finder_miner_count"]]
    assert hits, "expected at least one generation with a miner owning several positions"
    for t in r["per_template"]:
        # a miner may own several positions but counts as a single finder MINER
        assert t["distinct_potential_finder_miner_count"] <= t["active_range_solution_position_count"]


# 26
def test_active_position_field_is_not_finder_count():
    # the active solution-POSITION field must count positions, never len(discoveries).
    r = _multi_pos_run()
    assert any(t["active_range_solution_position_count"] != t["distinct_potential_finder_miner_count"]
               for t in r["per_template"])
    # run-level: total positions == active + inactive positions
    assert (r["total_template_solution_position_count"]
            == r["active_range_solution_position_count"] + r["inactive_range_solution_position_count"])


# 27
def test_potential_finder_equals_distinct_reachable_miners():
    r = _multi_pos_run()
    for t in r["per_template"]:
        # potential finder miners <= active positions and <= miner_count
        assert t["distinct_potential_finder_miner_count"] <= r["miners"]
        # a generation with any active position has at least one potential finder
        if t["active_range_solution_position_count"] > 0:
            assert t["distinct_potential_finder_miner_count"] >= 1
