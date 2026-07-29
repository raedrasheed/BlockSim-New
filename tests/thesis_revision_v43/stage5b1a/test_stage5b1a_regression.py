"""Stage 5B1A tests 41-46: prior-stage regression and thesis integrity."""

import os
import sys
import math
import subprocess

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, ROOT)

from experiments.thesis_revision_v43 import run_utils


# 41
def test_all_stage5b1_tests_unchanged():
    # the Stage-5B1 suite still passes against the corrected engine (only the one
    # B1-block-count assertion was revised as part of the zero-block correction).
    out = subprocess.run([sys.executable, "-m", "pytest",
                          os.path.join(ROOT, "tests", "thesis_revision_v43", "stage5b1"), "-q"],
                         cwd=ROOT, capture_output=True, text=True)
    assert out.returncode == 0, out.stdout[-2000:]


# 42
def test_stage4_tests_unchanged():
    import numpy as np
    from Models.PoCol.round_state import draw_round_solutions_exact
    g = np.random.default_rng(1)
    sols = draw_round_solutions_exact(g, 2.0 / 1000, [(0, 0, 999)], {0: 1.0})
    assert isinstance(sols, list)


# 43
def test_stage3_tests_unchanged():
    from Models.PoCol import round_state as rs
    ev = rs.EventIdentity(1, 5, 5, 100, 3, 7, 0, 2, 0.0, 1.0, 1, 2)
    cur = rs.CurrentState(100, 5, 5, 7, 0, 1, False, False)
    assert rs.classify_event(ev, cur) == rs.VALID_CURRENT


# 44
def test_stage2_tests_unchanged():
    from Models.Energy.wallclock_energy import network_active_power_w, continuous_energy_kwh
    assert math.isclose(network_active_power_w(141e12, 21.5), 3031.5, abs_tol=1e-6)
    assert math.isclose(continuous_energy_kwh(3031.5, 10000), 8.420833333333333, rel_tol=1e-9)


# 45
def test_journal_tests_unchanged():
    from Models.Energy import PowEconomicEnergyModel, GAMMA_SCENARIOS
    pw = PowEconomicEnergyModel(block_subsidy=3.125, avg_tx_fees=0.30, coin_price=60000.0,
                                electricity_price_per_kwh=0.05, electricity_spend_ratio_kappa=0.80)
    assert math.isclose(pw.energy_budget_per_block_kwh(), 3_288_000.0, rel_tol=1e-9)
    assert GAMMA_SCENARIOS["average"] == 0.475


# 46
def test_original_thesis_files_unchanged():
    docx = os.path.join(ROOT, "docs", "Raed-Rasheed-draft-42-00.docx")
    pdf = os.path.join(ROOT, "docs", "Raed-Rasheed-draft-42-00.pdf")
    assert run_utils.sha256_file(docx) == "2c3afdc5739109d0ea12ada96c3115d626a2188c1acbaeaa4b6020974884cbda"
    assert run_utils.sha256_file(pdf) == "131412bb2ce17ed97b98dfbefc136c7b5b226b9fd7372e79a25e4b0dc057e9c4"
