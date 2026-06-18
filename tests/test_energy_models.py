"""Unit tests for the consensus-aware energy/carbon models.

Run with:  python -m pytest tests/ -v
"""

import os
import sys
import math

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from Models.Energy import (
    PowEconomicEnergyModel,
    PosValidatorEnergyModel,
    CommunicationEnergyModel,
    CarbonFootprintModel,
    GAMMA_SCENARIOS,
)


def _pow(**over):
    base = dict(
        block_subsidy=3.125,
        avg_tx_fees=0.30,
        coin_price=60000.0,
        electricity_price_per_kwh=0.05,
        electricity_spend_ratio_kappa=0.80,
    )
    base.update(over)
    return PowEconomicEnergyModel(**base)


# ---- R1.1 / R1.3a : PoW energy depends on price and reward ----
def test_pow_energy_depends_on_price_and_reward():
    low = _pow(coin_price=20000.0)
    high = _pow(coin_price=100000.0)
    # Higher coin price -> strictly higher economic energy budget.
    assert high.energy_budget_per_block_kwh() > low.energy_budget_per_block_kwh()
    # Exactly linear in price (5x price -> 5x energy).
    ratio = high.energy_budget_per_block_kwh() / low.energy_budget_per_block_kwh()
    assert math.isclose(ratio, 5.0, rel_tol=1e-9)

    # Higher block reward (subsidy + fees) -> higher energy at fixed price.
    base = _pow()
    richer = _pow(block_subsidy=6.25)
    assert richer.network_energy_per_block_kwh() > base.network_energy_per_block_kwh()


def test_pow_energy_changes_with_electricity_price():
    cheap = _pow(electricity_price_per_kwh=0.03)
    pricey = _pow(electricity_price_per_kwh=0.12)
    # Cheaper electricity -> a larger budget buys more kWh per block.
    assert cheap.energy_budget_per_block_kwh() > pricey.energy_budget_per_block_kwh()
    # Inverse proportionality.
    ratio = cheap.energy_budget_per_block_kwh() / pricey.energy_budget_per_block_kwh()
    assert math.isclose(ratio, 0.12 / 0.03, rel_tol=1e-9)


def test_pow_kappa_bounds_validation():
    try:
        _pow(electricity_spend_ratio_kappa=1.5)
        assert False, "kappa > 1 must raise"
    except ValueError:
        pass


def test_pow_miner_allocation_sums_to_network():
    m = _pow()
    shares = [0.5, 0.3, 0.2]
    parts = m.allocate_to_miners(shares, num_blocks=100)
    assert math.isclose(sum(parts), m.network_energy_kwh(100), rel_tol=1e-12)


def test_pow_technical_cap_is_minimum():
    # With a tiny technical bound, network energy must equal the technical value.
    m = _pow(coin_price=1e9, mining_efficiency_j_per_th=21.5, difficulty=1.0)
    assert m.technical_energy_per_block_kwh() is not None
    assert math.isclose(m.network_energy_per_block_kwh(),
                        m.technical_energy_per_block_kwh(), rel_tol=1e-12)


# ---- R1.3b : PoS energy scales with validator count ----
def test_pos_energy_scales_with_validator_count():
    def e(v):
        return PosValidatorEnergyModel(
            validator_count=v, validator_power_watts=100.0,
            simulation_time_hours=24.0, uptime_ratio=1.0).total_energy_kwh()
    assert e(1000) > e(500) > e(100)
    # Linear in validator count.
    assert math.isclose(e(1000) / e(100), 10.0, rel_tol=1e-9)


def test_pos_energy_independent_of_coin_price():
    # PoS model has no price input at all -> structurally price-independent.
    m = PosValidatorEnergyModel(validator_count=500, validator_power_watts=100.0,
                                simulation_time_hours=24.0)
    assert not hasattr(m, "coin_price")


# ---- R2.E : carbon scales with gamma ----
def test_carbon_scales_with_gamma():
    energy = 1000.0  # kWh
    low = CarbonFootprintModel(scenario="low").carbon_kg(energy)
    avg = CarbonFootprintModel(scenario="average").carbon_kg(energy)
    high = CarbonFootprintModel(scenario="high").carbon_kg(energy)
    assert high > avg > low
    # C = E * gamma exactly.
    assert math.isclose(avg, energy * GAMMA_SCENARIOS["average"], rel_tol=1e-12)


# ---- R2.F : communication energy is counted ----
def test_communication_energy_is_counted():
    cm = CommunicationEnergyModel(tx_energy_per_message_j=2.0, rx_energy_per_message_j=1.0)
    cm.record_transmit(kind="block", count=10)
    cm.record_receive(kind="block", count=10)
    cm.record_transmit(kind="tx", count=100)
    cm.record_receive(kind="tx", count=100)
    assert cm.block_messages_tx == 10 and cm.block_messages_rx == 10
    assert cm.tx_messages_tx == 100 and cm.tx_messages_rx == 100
    assert cm.total_messages == 220
    # energy = 10*2 + 10*1 + 100*2 + 100*1 = 330 J
    assert math.isclose(cm.energy_j, 330.0, rel_tol=1e-12)
    assert cm.total_energy_kwh() > 0.0


def test_communication_broadcast_accounting():
    cm = CommunicationEnergyModel(tx_energy_per_message_j=1.0, rx_energy_per_message_j=1.0)
    cm.account_broadcast(num_messages=5, num_nodes=10, peer_degree=4, kind="block")
    # directed = 5*10*4 = 200 transmits and 200 receives
    assert cm.block_messages_tx == 200 and cm.block_messages_rx == 200


# ---- R2.I : fixed-power sanity check E = P * T ----
def test_fixed_power_sanity_check_matches_E_equals_P_times_T():
    # One validator at 100 W for 10 hours => E = P*T = 100*10/1000 = 1.0 kWh.
    m = PosValidatorEnergyModel(validator_count=1, validator_power_watts=100.0,
                                simulation_time_hours=10.0, uptime_ratio=1.0)
    assert math.isclose(m.total_energy_kwh(), 1.0, rel_tol=1e-12)

    # Network of N identical machines => E = N * P * T.
    n, p_w, t_h = 250, 100.0, 24.0
    mn = PosValidatorEnergyModel(validator_count=n, validator_power_watts=p_w,
                                 simulation_time_hours=t_h, uptime_ratio=1.0)
    assert math.isclose(mn.total_energy_kwh(), n * p_w * t_h / 1000.0, rel_tol=1e-12)
