"""Stage 5B1G tests 35-42: regression — the stale-race / exhaustion corrections do
NOT perturb primary energy, candidate, chronology, provenance, or B1 exact results."""

import os
import sys
import math

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, ROOT)

from experiments.thesis_revision_v43.scenario_engine import (
    EngineConfig, run_scenario, ENGINE_VERSION)
from experiments.thesis_revision_v43.schemas import OUTPUT_SCHEMA_VERSION
from experiments.thesis_revision_v43 import b1_exact

SCEN = ("B0", "B1", "B2", "B3_C1_CONTINUOUS_DISJOINT", "C2")


# 35
def test_energy_reconciles_every_scenario():
    for scen in SCEN:
        r = run_scenario(EngineConfig(scen, seed=1, miner_count=30,
                                      idle_power_ratio=(0.1 if scen == "C2" else 0.0)))
        assert math.isclose(r["total_energy_kwh"],
                            r["active_energy_kwh"] + r["idle_energy_kwh"]
                            + r["coordination_energy_kwh"], abs_tol=1e-9)


# 36
def test_candidate_reconciles_every_scenario():
    for scen in SCEN:
        r = run_scenario(EngineConfig(scen, seed=2, miner_count=30))
        assert (r["total_candidate_evaluations"]
                == r["distinct_candidate_identities"] + r["duplicate_evaluations"])


# 37
def test_generation_rows_sum_to_network_total_disjoint():
    for scen in ("B0", "B3_C1_CONTINUOUS_DISJOINT", "C2"):
        r = run_scenario(EngineConfig(scen, seed=1, miner_count=25,
                                      inactive_miner_fraction=0.15,
                                      idle_power_ratio=(0.1 if scen == "C2" else 0.0)),
                         emit_generation_detail=True)
        s = sum(g["candidates_evaluated_this_generation"] for g in r["per_miner_generation"])
        assert s == r["total_candidate_evaluations"]


# 38
def test_b1_exact_zero_block_unchanged():
    # the exact analytical B1 zero-block probability is independent of the stale-race
    # correction; the exact vs direct-sampler reconciliation (Stage 5B1B) still holds
    # within an EXACT 99% Clopper-Pearson interval (no arbitrary tolerance).
    N, T, tgt, mu = 50, 10000.0, 600.0, 1.0
    ex = b1_exact.exact_zero_block(141e12, N, T, tgt, mu)
    p_exact = ex["expected_zero_block_probability_exact"]
    ref = b1_exact.direct_reference_sampler(141e12, N, T, tgt, mu, n_samples=4000, seed=20260201)
    lo, hi = b1_exact.clopper_pearson(ref["zeros"], ref["n_samples"], alpha=0.01)
    assert lo <= p_exact <= hi                                # exact within 99% CI


# 39
def test_parent_chain_integrity():
    r = run_scenario(EngineConfig("B3_C1_CONTINUOUS_DISJOINT", seed=1, miner_count=20),
                     emit_detail=True)
    blocks = [t for t in r["per_template"] if t["accepted_block_id"] is not None]
    assert blocks
    assert blocks[0]["parent_block_id"] == "genesis"
    for i, t in enumerate(blocks):
        assert t["parent_block_id"] != t["accepted_block_id"]       # never self-parent
        if i > 0:
            assert t["parent_block_id"] == blocks[i - 1]["accepted_block_id"]


# 40
def test_template_chronology_sums_to_duration():
    for scen in SCEN:
        r = run_scenario(EngineConfig(scen, seed=3, miner_count=20), emit_detail=True)
        assert all(t["end_time_s"] >= t["start_time_s"] for t in r["per_template"])
        assert math.isclose(sum(t["duration_s"] for t in r["per_template"]), 10000.0, rel_tol=1e-9)


# 41
def test_integer_rates_sum_exact():
    for scen in SCEN:
        for dist in ("homogeneous", "heterogeneous_moderate", "heterogeneous_high"):
            r = run_scenario(EngineConfig(scen, seed=1, miner_count=17, hash_rate_distribution=dist))
            assert r["integer_rates_sum_exact"] is True
            assert r["network_hash_rate_hps_int"] == 141_000_000_000_000


# 42
def test_primary_energy_invariant_and_versions():
    # A1 accounting invariant: continuous full-participation total energy is fixed by
    # P_total*T and is UNCHANGED by the single-height stale-race diagnostic.
    for scen in ("B0", "B1", "B2", "B3_C1_CONTINUOUS_DISJOINT"):
        r = run_scenario(EngineConfig(scen, seed=1, miner_count=50))
        assert math.isclose(r["total_energy_kwh"], 8.420833333333333, rel_tol=1e-12)
    assert ENGINE_VERSION == "5b1g.1"
    assert OUTPUT_SCHEMA_VERSION == "5b1g.1"
