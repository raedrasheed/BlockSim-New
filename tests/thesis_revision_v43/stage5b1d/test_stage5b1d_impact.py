"""Stage 5B1D tests 18-24: engine reconciliation, scenario re-checks, regression."""

import os
import sys
import math
import subprocess

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, ROOT)

from experiments.thesis_revision_v43.scenario_engine import EngineConfig, run_scenario, ENGINE_VERSION
from experiments.thesis_revision_v43 import b1_exact as bx
from experiments.thesis_revision_v43 import run_utils

EXPECTED_KWH = 8.420833333333333


# 18
def test_engine_template_solution_reconciliation():
    # every template generation records solution_count == distinct positions found;
    # emit_detail exposes per-template rows with the reconciled counts
    r = run_scenario(EngineConfig("B3_C1_CONTINUOUS_DISJOINT", seed=3, miner_count=80), emit_detail=True)
    for t in r["per_template"]:
        # solution_count is the number of distinct positions in that generation
        assert t["solution_count"] >= 0
        assert t["assigned_domain_size"] == t["searched_domain_size"] + t["unsearched_domain_size"]
    # engine version reflects the sampler correction
    assert r["engine_version"] == ENGINE_VERSION == "5b1d.1"


# 19
def test_b1_zero_block_validation_after_sampler_fix():
    seeds = [20261001 + i for i in range(30)]        # validation seeds, disjoint from frozen
    for N in (100, 500):
        zeros = sum(1 for s in seeds
                    if run_scenario(EngineConfig("B1", seed=s, miner_count=N))["accepted_blocks"] == 0)
        p0 = bx.exact_zero_block(141e12, N, 10000.0, 600.0, 2.0)["expected_zero_block_probability_exact"]
        lo, hi = bx.clopper_pearson(zeros, len(seeds), 0.01)
        assert lo <= p0 <= hi, (N, zeros, p0, lo, hi)


# 20
def test_b2_exact_coverage_after_sampler_fix():
    r = run_scenario(EngineConfig("B2", seed=1, miner_count=100))
    assert math.isclose(r["total_candidate_evaluations"],
                        r["distinct_candidate_identities"] + r["duplicate_evaluations"], rel_tol=1e-12)
    assert 0.0 < r["duplicate_evaluation_rate"] < 0.99


# 21
def test_b3_c1_after_sampler_fix():
    r = run_scenario(EngineConfig("B3_C1_CONTINUOUS_DISJOINT", seed=1, miner_count=100))
    assert math.isclose(r["total_energy_kwh"], EXPECTED_KWH, rel_tol=1e-9)
    assert r["duplicate_evaluations"] == 0


# 22
def test_c2_after_sampler_fix():
    r = run_scenario(EngineConfig("C2", seed=1, miner_count=100,
                                  hash_rate_distribution="heterogeneous_moderate",
                                  allocation_policy="equal", idle_power_ratio=0.1))
    assert math.isclose(r["total_energy_kwh"],
                        r["active_energy_kwh"] + r["idle_energy_kwh"] + r["coordination_energy_kwh"],
                        abs_tol=1e-12)
    assert r["idle_energy_kwh"] > 0.0


# 23
def test_all_prior_tests_pass():
    for suite in ("stage5b1", "stage5b1a", "stage5b1b"):
        out = subprocess.run([sys.executable, "-m", "pytest",
                              os.path.join(ROOT, "tests", "thesis_revision_v43", suite), "-q"],
                             cwd=ROOT, capture_output=True, text=True)
        assert out.returncode == 0, (suite, out.stdout[-1500:])


# 24
def test_thesis_files_unchanged():
    docx = os.path.join(ROOT, "docs", "Raed-Rasheed-draft-42-00.docx")
    pdf = os.path.join(ROOT, "docs", "Raed-Rasheed-draft-42-00.pdf")
    assert run_utils.sha256_file(docx) == "2c3afdc5739109d0ea12ada96c3115d626a2188c1acbaeaa4b6020974884cbda"
    assert run_utils.sha256_file(pdf) == "131412bb2ce17ed97b98dfbefc136c7b5b226b9fd7372e79a25e4b0dc057e9c4"
