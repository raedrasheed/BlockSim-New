"""Stage 5B1A tests 35-40: regenerated matrix, semantic hashes, and code freeze."""

import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, ROOT)

from experiments.thesis_revision_v43 import hashing
from experiments.thesis_revision_v43 import build_matrix_5b1a
from experiments.thesis_revision_v43 import code_freeze_5b1a
from experiments.thesis_revision_v43.schemas import OUTPUT_SCHEMA_VERSION
from experiments.thesis_revision_v43.scenario_engine import ENGINE_VERSION


def _cfg(scen, **over):
    base = dict(scenario_id=scen, seed=1, miner_count=100, mu=2.0,
                hash_rate_distribution="homogeneous", allocation_policy="disjoint_equal",
                inactive_miner_fraction=0.0, propagation_delay_mean_s=0.42,
                idle_power_ratio=0.0, network_hash_rate_hps=141e12,
                efficiency_j_per_th=21.5, simulation_duration_s=10000.0,
                target_block_interval_s=600.0)
    base.update(over)
    return base


# 35
def test_execution_semantics_hash_after_b2_fix():
    # the B2 coverage correction does NOT change the (config-based) semantics hash
    b2 = _cfg("B2")
    h = hashing.execution_semantics_hash(b2)
    assert h == hashing.execution_semantics_hash(_cfg("B2"))          # stable
    assert h != hashing.execution_semantics_hash(_cfg("B1"))          # distinct exec models
    assert h != hashing.execution_semantics_hash(_cfg("B3_C1_CONTINUOUS_DISJOINT"))


# 36
def test_same_seed_same_semantics_unique():
    final, stats, retention = build_matrix_5b1a.build()
    sem = [r["execution_semantics_hash"] for r in final]
    assert len(sem) == len(set(sem)) == 1890                          # every run a unique execution


# 37
def test_b3_c1_still_single_run():
    b3 = _cfg("B3_C1_CONTINUOUS_DISJOINT"); b3["interpretation_labels"] = "B3"
    c1 = _cfg("B3_C1_CONTINUOUS_DISJOINT"); c1["interpretation_labels"] = "C1"
    assert hashing.execution_semantics_hash(b3) == hashing.execution_semantics_hash(c1)
    final, _, _ = build_matrix_5b1a.build()
    dual = [r for r in final if ";" in r["interpretation_labels"]]
    assert len(dual) == 870 and all(r["scenario_id"] == "B3_C1_CONTINUOUS_DISJOINT" for r in dual)


# 38
def test_zero_block_fields_present():
    final, _, _ = build_matrix_5b1a.build()
    for r in final:
        assert "expected_zero_block_probability" in r
        assert r["zero_block_risk_category"] in ("low", "moderate", "high", "very_high", "unmodeled")
        assert r["output_schema_version"] == OUTPUT_SCHEMA_VERSION
        assert "retention_full_log" in r and "retention_reason_codes" in r
    # B1 rows carry a material zero-block risk
    b1 = [r for r in final if r["scenario_id"] == "B1"]
    assert all(r["zero_block_risk_category"] in ("high", "very_high") for r in b1)


# 39
def test_matrix_checksum_reproducible():
    a = build_matrix_5b1a.build()[0]
    b = build_matrix_5b1a.build()[0]
    ka = [(r["run_id"], r["configuration_hash"], r["execution_semantics_hash"]) for r in a]
    kb = [(r["run_id"], r["configuration_hash"], r["execution_semantics_hash"]) for r in b]
    assert ka == kb                                                  # deterministic build


# 40
def test_code_freeze_manifest_complete():
    m = code_freeze_5b1a.build_manifest(test_result="checked")
    for key in code_freeze_5b1a.REQUIRED_KEYS:
        assert key in m, key
    assert m["output_schema_version"] == OUTPUT_SCHEMA_VERSION
    assert m["scenario_engine_version"] == ENGINE_VERSION
    assert m["thesis_docx_sha256"] == "2c3afdc5739109d0ea12ada96c3115d626a2188c1acbaeaa4b6020974884cbda"
