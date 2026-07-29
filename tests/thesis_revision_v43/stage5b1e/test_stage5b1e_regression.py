"""Stage 5B1E tests 31-38: scenario regression and prior-suite pass."""

import os
import sys
import math
import subprocess

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, ROOT)

from experiments.thesis_revision_v43.scenario_engine import EngineConfig, run_scenario
from experiments.thesis_revision_v43 import b1_exact as bx
from experiments.thesis_revision_v43 import run_utils

KWH = 8.420833333333333


# 31
def test_b0_independent_template_identity():
    # B0 (independent-template abstraction): homogeneous full participation is
    # numerically equivalent to B3 in energy and block count; NO false duplicates
    # (equal nonces under different templates are distinct identities -> dup == 0).
    b0 = run_scenario(EngineConfig("B0", seed=5, miner_count=100))
    b3 = run_scenario(EngineConfig("B3_C1_CONTINUOUS_DISJOINT", seed=5, miner_count=100))
    assert b0["duplicate_evaluations"] == 0
    assert math.isclose(b0["total_energy_kwh"], b3["total_energy_kwh"], rel_tol=1e-9)
    assert b0["accepted_blocks"] == b3["accepted_blocks"]
    assert b0["abstract_template_agreement_operations"] == 0          # independent templates


# 32
def test_b1_zero_block_revalidation():
    seeds = [20261001 + i for i in range(30)]
    for N in (100, 500):
        z = sum(1 for s in seeds if run_scenario(EngineConfig("B1", seed=s, miner_count=N))["accepted_blocks"] == 0)
        p0 = bx.exact_zero_block(141e12, N, 10000.0, 600.0, 2.0)["expected_zero_block_probability_exact"]
        lo, hi = bx.clopper_pearson(z, len(seeds), 0.01)
        assert lo <= p0 <= hi


# 33
def test_b2_exact_coverage_revalidation():
    r = run_scenario(EngineConfig("B2", seed=1, miner_count=100))
    assert r["total_candidate_evaluations"] == \
        r["distinct_candidate_identities"] + r["duplicate_evaluations"]
    assert 0.0 < r["duplicate_evaluation_rate"] < 0.99


# 34
def test_b3_c1_lifecycle_revalidation():
    r = run_scenario(EngineConfig("B3_C1_CONTINUOUS_DISJOINT", seed=1, miner_count=100))
    assert math.isclose(r["total_energy_kwh"], KWH, rel_tol=1e-9)
    assert r["duplicate_evaluations"] == 0
    assert r["total_idle_time_s"] == 0.0                              # continuous power


# 35
def test_c2_idle_and_energy_revalidation():
    hom = run_scenario(EngineConfig("C2", seed=1, miner_count=100, allocation_policy="equal",
                                    idle_power_ratio=0.3))
    het = run_scenario(EngineConfig("C2", seed=1, miner_count=100,
                                    hash_rate_distribution="heterogeneous_moderate",
                                    allocation_policy="equal", idle_power_ratio=0.1))
    assert hom["total_idle_time_s"] == 0.0 and math.isclose(hom["total_energy_kwh"], KWH, rel_tol=1e-9)
    assert het["total_idle_time_s"] > 0.0 and het["total_energy_kwh"] < KWH
    assert math.isclose(het["total_energy_kwh"],
                        het["active_energy_kwh"] + het["idle_energy_kwh"], abs_tol=1e-12)


# 36
def test_inactive_sensitivity_revalidation():
    full = run_scenario(EngineConfig("B3_C1_CONTINUOUS_DISJOINT", seed=1, miner_count=100))
    inact = run_scenario(EngineConfig("B3_C1_CONTINUOUS_DISJOINT", seed=1, miner_count=100,
                                      inactive_miner_fraction=0.30))
    assert inact["total_energy_kwh"] < full["total_energy_kwh"]       # inactive miners consume nothing
    assert inact["inactive_range_solution_count"] >= 0
    assert inact["accepted_blocks"] <= full["accepted_blocks"]        # unsearched domain -> fewer blocks


# 37
def test_all_prior_tests_pass():
    for suite in ("stage5b1", "stage5b1a", "stage5b1b", "stage5b1d"):
        out = subprocess.run([sys.executable, "-m", "pytest",
                              os.path.join(ROOT, "tests", "thesis_revision_v43", suite), "-q"],
                             cwd=ROOT, capture_output=True, text=True)
        assert out.returncode == 0, (suite, out.stdout[-1500:])


# 38
def test_thesis_files_unchanged():
    docx = os.path.join(ROOT, "docs", "Raed-Rasheed-draft-42-00.docx")
    pdf = os.path.join(ROOT, "docs", "Raed-Rasheed-draft-42-00.pdf")
    assert run_utils.sha256_file(docx) == "2c3afdc5739109d0ea12ada96c3115d626a2188c1acbaeaa4b6020974884cbda"
    assert run_utils.sha256_file(pdf) == "131412bb2ce17ed97b98dfbefc136c7b5b226b9fd7372e79a25e4b0dc057e9c4"
