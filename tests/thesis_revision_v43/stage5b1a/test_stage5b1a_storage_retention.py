"""Stage 5B1A tests 22-29: expanded storage probe and stratified retention."""

import os
import sys
import json
import tempfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, ROOT)

from experiments.thesis_revision_v43.scenario_engine import EngineConfig, run_scenario
from experiments.thesis_revision_v43 import storage_projection_5b1a as storage
from experiments.thesis_revision_v43 import retention_5b1a
from experiments.thesis_revision_v43 import build_matrix_5b1a
from experiments.thesis_revision_v43 import run_utils


def _matrix_rows():
    final, stats, retention = build_matrix_5b1a.build()
    return final


# 22
def test_storage_probe_includes_per_miner_files(tmp_path):
    r = run_scenario(EngineConfig("B3_C1_CONTINUOUS_DISJOINT", seed=1, miner_count=100),
                     emit_detail=True)
    p = str(tmp_path / "x.per_miner.json")
    run_utils.atomic_write_json(p, r["per_miner"])
    assert os.path.getsize(p) > 0 and len(json.load(open(p))) == 100
    # the storage probe spec enumerates the 9 required configurations
    assert len(storage.PROBE_SPECS) == 9


# 23
def test_storage_probe_includes_per_template_files(tmp_path):
    r = run_scenario(EngineConfig("C2", seed=1, miner_count=100,
                                  hash_rate_distribution="heterogeneous_moderate",
                                  allocation_policy="equal", idle_power_ratio=0.1),
                     emit_detail=True)
    p = str(tmp_path / "x.per_template.json")
    run_utils.atomic_write_json(p, r["per_template"])
    assert os.path.getsize(p) > 0 and len(json.load(open(p))) >= 1
    # probe covers C2 homogeneous, heterogeneous-equal and heterogeneous-weighted
    tags = set(storage.PROBE_TAGS)
    assert {"C2_hom", "C2_het_equal", "C2_het_weighted"} <= tags


# 24
def test_retention_covers_all_scenario_miner_groups():
    rows = _matrix_rows()
    groups = {(r["scenario_id"], r["miner_count"]) for r in rows}
    covered = {(r["scenario_id"], r["miner_count"]) for r in rows if r["retention_full_log"]}
    assert groups <= covered


# 25
def test_retention_covers_all_sensitivity_levels():
    rows = _matrix_rows()
    codes = ";".join(r["retention_reason_codes"] for r in rows if r["retention_full_log"])
    for token in ("delay_level", "mu_level", "inactive_level", "idle_power_level",
                  "dist:homogeneous", "dist:heterogeneous_equal", "dist:heterogeneous_weighted",
                  "dist:exploratory_high"):
        assert token in codes, token


# 26
def test_retention_contains_zero_block_run():
    rows = _matrix_rows()
    codes = ";".join(r["retention_reason_codes"] for r in rows if r["retention_full_log"])
    assert "expected_zero_block_b1" in codes
    assert "expected_high_exhaustion" in codes
    assert "expected_legitimate_stale" in codes


# 27
def test_retention_contains_nonzero_idle_run():
    rows = _matrix_rows()
    codes = ";".join(r["retention_reason_codes"] for r in rows if r["retention_full_log"])
    assert "expected_nonzero_idle_c2" in codes
    assert "expected_zero_idle_c2" in codes


# 28
def test_retention_is_deterministic():
    rows1 = _matrix_rows()
    rows2 = _matrix_rows()
    r1 = sorted(r["run_id"] for r in rows1 if r["retention_full_log"])
    r2 = sorted(r["run_id"] for r in rows2 if r["retention_full_log"])
    assert r1 == r2


# 29
def test_retention_checksum_reproducible():
    base_rows = [dict(r) for r in _matrix_rows()]
    _, m1 = retention_5b1a.design_retention([dict(r) for r in base_rows])
    _, m2 = retention_5b1a.design_retention([dict(r) for r in base_rows])
    assert m1["retention_checksum_sha256"] == m2["retention_checksum_sha256"]
    # no duplicate retained ids
    ids = m1["matrix_retained_run_ids"]
    assert len(ids) == len(set(ids))
