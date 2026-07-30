"""Stage 5B1G.1 tests 5-9: B2 path provenance — actual seeded start, circular last
position, wraparound; B1 start 0; disjoint start = range start (§2)."""

import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, ROOT)

from experiments.thesis_revision_v43.scenario_engine import EngineConfig, run_scenario


def _gen_rows(scen, **kw):
    kw.setdefault("miner_count", 12)
    kw.setdefault("seed", 5)
    r = run_scenario(EngineConfig(scen, **kw), emit_detail=True, emit_generation_detail=True)
    return r, r["per_miner_generation"]


# 5
def test_b2_actual_random_start_recorded():
    r, rows = _gen_rows("B2", mu=4.0)
    active = [g for g in rows if g["candidates_evaluated_this_generation"] > 0]
    starts = {g["search_start_position"] for g in active}
    assert None not in starts
    assert any(s != 0 for s in starts)                   # real seeded starts, not all zero
    assert len(starts) > 1                               # distinct per-miner starts


# 6
def test_b2_last_position_uses_modulo_start():
    r, rows = _gen_rows("B2", mu=4.0)
    S = r["domain_size"]
    checked = 0
    for g in rows:
        c = g["candidates_evaluated_this_generation"]
        if c > 0 and g["search_start_position"] is not None:
            assert g["last_evaluated_position"] == (g["search_start_position"] + c - 1) % S
            checked += 1
    assert checked > 0


# 7
def test_b2_wraparound_path_provenance():
    r, rows = _gen_rows("B2", mu=4.0)
    S = r["domain_size"]
    wrapped = [g for g in rows if g["path_wraps_around"]]
    assert wrapped                                       # some arcs wrap the ring
    for g in wrapped:
        c = g["candidates_evaluated_this_generation"]
        assert g["search_start_position"] + c > S        # wrap iff arc crosses S
        assert g["path_end_position"] == (g["search_start_position"] + c - 1) % S
        assert g["circular_candidates_evaluated"] == c


# 8
def test_b1_start_remains_zero():
    r, rows = _gen_rows("B1", miner_count=50)
    for g in rows:
        if g["candidates_evaluated_this_generation"] > 0:
            assert g["search_start_position"] == 0        # B1 always starts at nonce 0
            assert g["path_wraps_around"] is False


# 9
def test_disjoint_start_remains_range_start():
    for scen in ("B0", "B3_C1_CONTINUOUS_DISJOINT", "C2"):
        r, rows = _gen_rows(scen, mu=2.0, idle_power_ratio=(0.1 if scen == "C2" else 0.0))
        for g in rows:
            if g["candidates_evaluated_this_generation"] > 0:
                assert g["search_start_position"] == g["assigned_range_start"]
                assert g["path_wraps_around"] is False    # linear ranges never wrap
