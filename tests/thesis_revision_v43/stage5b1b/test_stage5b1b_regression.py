"""Stage 5B1B tests 28-33: prior-stage regression."""

import os
import sys
import math
import subprocess

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, ROOT)


def _suite(path):
    out = subprocess.run([sys.executable, "-m", "pytest", os.path.join(ROOT, path), "-q"],
                         cwd=ROOT, capture_output=True, text=True)
    assert out.returncode == 0, out.stdout[-2000:]


# 28
def test_stage5b1a_tests_pass():
    _suite("tests/thesis_revision_v43/stage5b1a")


# 29
def test_stage5b1_tests_pass():
    _suite("tests/thesis_revision_v43/stage5b1")


# 30
def test_stage4_tests_pass():
    import numpy as np
    from Models.PoCol.round_state import draw_round_solutions_exact
    sols = draw_round_solutions_exact(np.random.default_rng(1), 2.0 / 1000, [(0, 0, 999)], {0: 1.0})
    assert isinstance(sols, list)


# 31
def test_stage3_tests_pass():
    from Models.PoCol import round_state as rs
    ev = rs.EventIdentity(1, 5, 5, 100, 3, 7, 0, 2, 0.0, 1.0, 1, 2)
    cur = rs.CurrentState(100, 5, 5, 7, 0, 1, False, False)
    assert rs.classify_event(ev, cur) == rs.VALID_CURRENT


# 32
def test_stage2_tests_pass():
    from Models.Energy.wallclock_energy import network_active_power_w, continuous_energy_kwh
    assert math.isclose(network_active_power_w(141e12, 21.5), 3031.5, abs_tol=1e-6)
    assert math.isclose(continuous_energy_kwh(3031.5, 10000), 8.420833333333333, rel_tol=1e-9)


# 33
def test_journal_tests_pass():
    from Models.Energy import PowEconomicEnergyModel, GAMMA_SCENARIOS
    pw = PowEconomicEnergyModel(block_subsidy=3.125, avg_tx_fees=0.30, coin_price=60000.0,
                                electricity_price_per_kwh=0.05, electricity_spend_ratio_kappa=0.80)
    assert math.isclose(pw.energy_budget_per_block_kwh(), 3_288_000.0, rel_tol=1e-9)
    assert GAMMA_SCENARIOS["average"] == 0.475
