"""Stage 5B1A tests 30-34: coordination message-category separation."""

import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, ROOT)

from experiments.thesis_revision_v43.scenario_engine import EngineConfig, run_scenario
from experiments.thesis_revision_v43 import schemas


def R(scen, **kw):
    return run_scenario(EngineConfig(scen, seed=5, miner_count=100, **kw))


# 30
def test_block_bytes_use_configured_block_size():
    r = R("B3_C1_CONTINUOUS_DISJOINT")
    assert r["block_propagation_bytes"] == r["block_propagation_message_count"] * 1_000_000
    # a different configured block size flows through
    r2 = run_scenario(EngineConfig("B3_C1_CONTINUOUS_DISJOINT", seed=5, miner_count=100,
                                   block_size_bytes=2_000_000))
    assert r2["block_propagation_bytes"] == r2["block_propagation_message_count"] * 2_000_000


# 31
def test_control_message_categories_separate():
    r = R("B3_C1_CONTINUOUS_DISJOINT")
    for c in ("transaction_reconciliation", "template_announcement", "nonce_allocation", "registration"):
        assert f"{c}_message_count" in r
        assert f"{c}_bytes" in r
    # categories are distinct counters, not one undifferentiated total
    assert r["template_announcement_message_count"] != r["registration_message_count"] \
        or r["template_announcement_message_count"] == 0


# 32
def test_abstract_ops_have_no_simulated_bytes_by_default():
    r = R("B3_C1_CONTINUOUS_DISJOINT")
    # control-message bytes are null (size not configured) -> never fabricated
    for c in ("transaction_reconciliation", "template_announcement", "nonce_allocation", "registration"):
        assert r[f"{c}_bytes"] is None
    # only block propagation carries real bytes
    assert r["block_propagation_bytes"] is not None and r["block_propagation_bytes"] >= 0


# 33
def test_unimplemented_energy_remains_null():
    for scen in ("B0", "B1", "B2", "B3_C1_CONTINUOUS_DISJOINT", "C2"):
        r = R(scen) if scen != "C2" else R(scen, allocation_policy="equal")
        assert r["unimplemented_agreement_energy_kwh"] is None
        assert r["coordination_energy_lower_bound_kwh"] == 0.0


# 34
def test_coordination_counter_schema_complete():
    r = R("B3_C1_CONTINUOUS_DISJOINT")
    for f in schemas.COORD_FIELDS:
        assert f in r, f
    for f in schemas.ABSTRACT_FIELDS:
        assert f in r, f
