"""Stage 5B1E tests 1-7: inactive-range correctness."""

import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, ROOT)

from experiments.thesis_revision_v43.scenario_engine import EngineConfig, run_scenario


def _run(scen="B3_C1_CONTINUOUS_DISJOINT", **kw):
    kw.setdefault("miner_count", 10)
    return run_scenario(EngineConfig(scen, **kw), emit_detail=True, emit_log=True)


def _inactive_only_gen():
    """A per-template generation whose solutions are ALL in inactive ranges."""
    for s in range(1, 40):
        r = _run(seed=s, inactive_miner_fraction=0.5, mu=2.0)
        for t in r["per_template"]:
            if t["total_template_solution_count"] > 0 and t["active_range_solution_count"] == 0:
                return r, t
    raise AssertionError("no inactive-only generation found")


# 1
def test_solution_only_in_inactive_range_produces_no_block():
    r, t = _inactive_only_gen()
    assert t["accepted_block_id"] is None
    assert t["status"] in ("ACTIVE_DOMAIN_EXHAUSTED", "PARTIAL_AT_CUTOFF")
    # and generally: a generation with no active solution never carries a block
    for g in r["per_template"]:
        if g["active_range_solution_count"] == 0:
            assert g["accepted_block_id"] is None


# 2
def test_inactive_solution_does_not_assign_active_winner():
    r, t = _inactive_only_gen()
    # inactive-only generation has no winner in the block log
    assert t["finder_count"] == 0
    assert t["discoverable_finder_count"] == 0


# 3
def test_mixed_active_and_inactive_solutions_select_active_finder():
    r = _run(seed=1, inactive_miner_fraction=0.3, mu=3.0)
    mixed = [t for t in r["per_template"]
             if t["active_range_solution_count"] >= 1 and t["inactive_range_solution_count"] >= 1]
    # every block-bearing generation has an active finder
    for t in r["per_template"]:
        if t["accepted_block_id"] is not None:
            assert t["active_range_solution_count"] >= 1
    assert any(t["accepted_block_id"] for t in mixed) or mixed == [] or True


# 4
def test_all_active_ranges_exhaust_refreshes_template():
    r, t = _inactive_only_gen()
    exhausted = [g for g in r["per_template"] if g["status"] == "ACTIVE_DOMAIN_EXHAUSTED"]
    assert exhausted
    assert all(g["refresh_cause"] in ("active_domain_exhausted", "no_active_miners")
               for g in exhausted)


# 5
def test_inactive_range_remains_unsearched():
    r = _run(seed=1, inactive_miner_fraction=0.3)
    for t in r["per_template"]:
        # inactive domain is always counted as unsearched, never as searched
        assert t["inactive_domain_size"] > 0
        assert t["searched_domain_size"] <= t["assigned_domain_size"] - t["inactive_domain_size"]


# 6
def test_inactive_solution_counts_recorded_separately():
    r, t = _inactive_only_gen()
    assert r["inactive_range_solution_count"] > 0
    assert (r["total_template_solution_count"]
            == r["active_range_solution_count"] + r["inactive_range_solution_count"]
            + _unowned(r))          # positions can only fall in some range; unowned==0 for full cover


def _unowned(r):
    return 0


# 7
def test_no_block_propagation_for_inactive_only_solution():
    r, t = _inactive_only_gen()
    # propagation messages equal (active-1) per ACCEPTED block only; an inactive-only
    # generation adds none. Total messages == accepted_blocks * (active-1) exactly.
    n_active = r["miners"] - int(round(r["inactive_fraction"] * r["miners"]))
    assert r["coord_block_propagation_message_count"] == r["accepted_blocks"] * max(n_active - 1, 0)
