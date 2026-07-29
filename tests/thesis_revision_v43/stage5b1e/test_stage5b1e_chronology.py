"""Stage 5B1E tests 26-30: per-template chronology."""

import os
import sys
import math

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, ROOT)

from experiments.thesis_revision_v43.scenario_engine import EngineConfig, run_scenario


def _pt(scen="B3_C1_CONTINUOUS_DISJOINT", **kw):
    kw.setdefault("miner_count", 40)
    kw.setdefault("seed", 1)
    return run_scenario(EngineConfig(scen, **kw), emit_detail=True)["per_template"]


# 26
def test_exhausted_generation_positive_duration():
    pt = _pt(mu=0.5)                                     # low mu -> exhausted generations
    exh = [t for t in pt if t["status"] == "ACTIVE_DOMAIN_EXHAUSTED"]
    assert exh
    for t in exh:
        assert t["duration_s"] > 0.0
        assert t["end_time_s"] > t["start_time_s"]


# 27
def test_template_times_monotonic():
    pt = _pt(inactive_miner_fraction=0.15, mu=1.0)
    for i in range(len(pt)):
        assert pt[i]["end_time_s"] >= pt[i]["start_time_s"]              # end >= start
    for i in range(len(pt) - 1):
        assert pt[i + 1]["start_time_s"] >= pt[i]["end_time_s"] - 1e-6   # non-overlapping, ordered


# 28
def test_template_durations_sum_to_run_time():
    pt = _pt(mu=1.0)
    total = sum(t["duration_s"] for t in pt)
    assert math.isclose(total, 10000.0, rel_tol=1e-9)                    # tile the horizon exactly


# 29
def test_partial_template_cutoff_time():
    pt = _pt()
    last = pt[-1]
    if last["status"] == "PARTIAL_AT_CUTOFF":
        assert last["partial_cutoff_time_s"] is not None
        assert math.isclose(last["end_time_s"], 10000.0, rel_tol=1e-9)
    else:
        assert last["partial_cutoff_time_s"] is None


# 30
def test_refresh_cause_matches_transition():
    pt = _pt(mu=0.5, inactive_miner_fraction=0.15)
    for t in pt:
        if t["accepted_block_id"] is not None:
            assert t["refresh_cause"] == "accepted_block"
        elif t["status"] == "ACTIVE_DOMAIN_EXHAUSTED":
            assert t["refresh_cause"] in ("active_domain_exhausted", "no_active_miners")
        elif t["status"] == "PARTIAL_AT_CUTOFF":
            assert t["refresh_cause"] == "simulation_cutoff"
