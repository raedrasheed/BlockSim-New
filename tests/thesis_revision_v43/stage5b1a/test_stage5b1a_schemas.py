"""Stage 5B1A tests 16-21: per-miner / per-template schemas and NA fields."""

import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, ROOT)

from experiments.thesis_revision_v43.scenario_engine import EngineConfig, run_scenario
from experiments.thesis_revision_v43 import schemas

SPECS = [("B0", dict(inactive_miner_fraction=0.15)), ("B1", {}), ("B2", {}),
         ("B3_C1_CONTINUOUS_DISJOINT", {}),
         ("C2", dict(hash_rate_distribution="heterogeneous_moderate",
                     allocation_policy="equal", idle_power_ratio=0.1))]


def _run(scen, **kw):
    return run_scenario(EngineConfig(scen, seed=7, miner_count=50, **kw), emit_detail=True)


# 16
def test_per_miner_schema_complete():
    r = _run("B3_C1_CONTINUOUS_DISJOINT")
    assert len(r["per_miner"]) == 50
    for m in r["per_miner"]:
        assert schemas.validate_fields(m, schemas.PER_MINER_FIELDS) == []


# 17
def test_per_miner_network_reconciliation():
    r = _run("C2", hash_rate_distribution="heterogeneous_moderate",
             allocation_policy="equal", idle_power_ratio=0.1)
    rec = schemas.reconcile_per_miner(r["per_miner"], r)
    assert rec["passed"], rec


# 18
def test_per_template_schema_complete():
    r = _run("B3_C1_CONTINUOUS_DISJOINT")
    assert len(r["per_template"]) >= 1
    for t in r["per_template"]:
        assert schemas.validate_fields(t, schemas.PER_TEMPLATE_FIELDS) == []


# 19
def test_template_domain_reconciliation():
    r = _run("B0", inactive_miner_fraction=0.15)
    rec = schemas.reconcile_per_template(r["per_template"])
    assert rec["passed"], rec
    for t in r["per_template"]:
        # Section 4: searched + unsearched + inactive == assigned (exact integers)
        assert t["assigned_domain_size"] == (t["searched_domain_size"]
                                             + t["unsearched_domain_size"]
                                             + t["inactive_domain_size"])


# 20
def test_stable_schema_across_scenarios():
    keys = None
    for scen, kw in SPECS:
        r = _run(scen, **kw)
        k = set(r["per_miner"][0].keys())
        if keys is None:
            keys = k
        assert k == keys                                    # identical schema for every scenario
    assert keys == set(schemas.PER_MINER_FIELDS)


# 21
def test_na_fields_explicit():
    r = run_scenario(EngineConfig("B1", seed=20260201, miner_count=500))
    # transactions not modelled -> explicit NA + reason, never 0
    assert r["energy_per_transaction_kwh"] is None
    assert r["energy_per_transaction_na_reason"] == "no_committed_transactions"
    assert schemas.is_na(r["energy_per_transaction_kwh"])
    # NA reason codes are from the declared vocabulary
    assert r["energy_per_accepted_block_na_reason"] in schemas.NA_REASONS
