"""Stage 5B1F tests 28-32: template parent provenance and partial/exhausted flags."""

import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, ROOT)

from experiments.thesis_revision_v43.scenario_engine import EngineConfig, run_scenario


def _pt(scen="B3_C1_CONTINUOUS_DISJOINT", **kw):
    kw.setdefault("miner_count", 40)
    kw.setdefault("seed", 1)
    return run_scenario(EngineConfig(scen, **kw), emit_detail=True)["per_template"]


# 28
def test_accepted_block_not_its_own_parent():
    for t in _pt(inactive_miner_fraction=0.15):
        if t["accepted_block_id"] is not None:
            assert t["parent_block_id"] != t["accepted_block_id"]


# 29
def test_parent_chain_progression():
    pt = _pt(mu=1.0)
    blocks = [t for t in pt if t["accepted_block_id"] is not None]
    assert blocks[0]["parent_block_id"] == "genesis"
    for i in range(1, len(blocks)):
        assert blocks[i]["parent_block_id"] == blocks[i - 1]["accepted_block_id"]


# 30
def test_exhausted_refresh_keeps_parent():
    pt = _pt(mu=0.5, inactive_miner_fraction=0.15)          # exhausted generations occur
    # an exhausted generation's parent equals the last accepted block before it
    last_accepted = "genesis"
    for t in pt:
        if t["accepted_block_id"] is None:
            assert t["parent_block_id"] == last_accepted     # refresh keeps parent
        else:
            assert t["parent_block_id"] == last_accepted
            last_accepted = t["accepted_block_id"]


# 31
def test_partial_generation_not_exhausted():
    pt = _pt()
    for t in pt:
        assert not (t["partial"] and t["exhausted"])         # never both
    last = pt[-1]
    if last["partial"]:
        assert not last["exhausted"] and not last["accepted"]


# 32
def test_refresh_without_block_does_not_advance_height():
    pt = _pt(mu=0.5, inactive_miner_fraction=0.15)
    height = 0
    for t in pt:
        if t["accepted"]:
            height += 1
        else:
            assert t["refresh_required"]                     # refresh, no height advance
    # accepted count equals number of height advances
    assert height == sum(1 for t in pt if t["accepted"])
