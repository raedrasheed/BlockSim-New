"""Stage 2 tests for the thesis-path wall-clock energy accounting.

Covers the 20 required Stage-2 checks. All tests are deterministic (module- and
Node-level; no random event loop). The physical invariants use an explicitly
declared numerical tolerance.

Invariant reference:
    141 TH/s * 21.5 J/TH = 3031.5 W
    3031.5 W * 10000 s / 3.6e6 = 8.420833333... kWh
"""

import os
import sys
import math
import inspect

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from Models.Energy.wallclock_energy import (
    J_PER_KWH, HASHES_PER_TH,
    ACTIVE, IDLE, OFFLINE,
    joules_to_kwh, kwh_to_joules, th_per_s_to_hps, efficiency_j_per_hash,
    active_power_w, network_active_power_w, continuous_energy_kwh,
    hashes_to_energy_j, equal_hash_rates_hps,
    MinerEnergyState, WallClockEnergyAccountant,
)

# ---- reference constants ----
NET_HPS = 141e12
EFF_J_PER_TH = 21.5
T_SIM = 10000.0
EXPECTED_POWER_W = 3031.5
EXPECTED_ENERGY_KWH = 3031.5 * 10000.0 / 3_600_000.0   # 8.420833333...

# Declared tolerances
ABS_TOL_W = 1e-6           # power invariants (W)
REL_TOL_MODULE = 1e-12     # exact module arithmetic
REL_TOL_KWH = 1e-9         # energy invariants (kWh)


def _active_state(hash_rate_hps=NET_HPS, idle_power_w=0.0):
    return MinerEnergyState(miner_id=0, hash_rate_hps=hash_rate_hps,
                            efficiency_j_per_th=EFF_J_PER_TH,
                            idle_power_w=idle_power_w)


# 1 -------------------------------------------------------------------------
def test_fixed_network_power_invariant():
    assert math.isclose(network_active_power_w(NET_HPS, EFF_J_PER_TH),
                        EXPECTED_POWER_W, abs_tol=ABS_TOL_W)


# 2 -------------------------------------------------------------------------
def test_continuous_energy_10000_seconds():
    e = continuous_energy_kwh(EXPECTED_POWER_W, T_SIM)
    assert math.isclose(e, EXPECTED_ENERGY_KWH, rel_tol=REL_TOL_KWH)
    assert math.isclose(e, 8.420833333333333, rel_tol=1e-12)


# 3 -------------------------------------------------------------------------
def test_energy_independent_of_miner_count_when_total_hashrate_fixed():
    totals = []
    for n in (100, 200, 300, 400, 500):
        acc = WallClockEnergyAccountant(EFF_J_PER_TH)
        acc.add_equal_miners(n, NET_HPS)
        for mid in acc.miners:
            acc.transition(mid, ACTIVE, 0.0)
        acc.flush_all(T_SIM)
        totals.append(acc.total_energy_kwh())
    for t in totals:
        assert math.isclose(t, EXPECTED_ENERGY_KWH, rel_tol=REL_TOL_KWH)
    # pairwise equal
    assert max(totals) - min(totals) < 1e-9


# 4 -------------------------------------------------------------------------
def test_per_miner_hashrates_sum_to_network_hashrate():
    for n in (100, 200, 300, 400, 500):
        rates = equal_hash_rates_hps(NET_HPS, n)
        assert len(rates) == n
        assert math.isclose(sum(rates), NET_HPS, rel_tol=1e-12)
        acc = WallClockEnergyAccountant(EFF_J_PER_TH)
        acc.add_equal_miners(n, NET_HPS)
        assert math.isclose(acc.sum_hash_rate_hps(), NET_HPS, rel_tol=1e-12)


# 5 -------------------------------------------------------------------------
def test_sum_per_miner_energy_equals_network_energy():
    acc = WallClockEnergyAccountant(EFF_J_PER_TH)
    acc.add_equal_miners(250, NET_HPS)
    for mid in acc.miners:
        acc.transition(mid, ACTIVE, 0.0)
    acc.flush_all(T_SIM)
    per = acc.per_miner_energy_kwh()
    assert math.isclose(sum(per.values()), acc.total_energy_kwh(), rel_tol=1e-12)
    assert math.isclose(sum(per.values()), EXPECTED_ENERGY_KWH, rel_tol=REL_TOL_KWH)


# 6 -------------------------------------------------------------------------
def test_active_idle_time_conservation():
    st = _active_state()
    st.begin_active(0.0)
    st.transition_to(IDLE, 100.0)     # active [0,100]
    st.go_offline(150.0)              # idle   [100,150]
    st.close(200.0)                   # offline[150,200]
    assert math.isclose(st.active_time_s, 100.0)
    assert math.isclose(st.idle_time_s, 50.0)
    assert math.isclose(st.offline_time_s, 50.0)
    assert math.isclose(st.accounted_time_s(), 200.0)   # == full span, no gaps


# 7 -------------------------------------------------------------------------
def test_no_active_idle_overlap():
    st = _active_state()
    st.begin_active(0.0)
    st.transition_to(IDLE, 100.0)
    # accounted time never exceeds elapsed span -> no double counting/overlap
    st.close(120.0)
    assert st.accounted_time_s() <= 120.0 + 1e-12
    assert math.isclose(st.active_time_s + st.idle_time_s, 120.0)
    # time going backwards is rejected
    st2 = _active_state()
    st2.begin_active(100.0)
    try:
        st2.transition_to(IDLE, 50.0)
        assert False, "expected ValueError on backwards time"
    except ValueError:
        pass


# 8 -------------------------------------------------------------------------
def test_state_transition_closes_previous_interval():
    st = _active_state()
    st.begin_active(0.0)
    st.begin_idle(50.0)               # must close the active interval at 50
    assert math.isclose(st.active_time_s, 50.0)
    assert st.idle_time_s == 0.0      # idle interval still open


# 9 -------------------------------------------------------------------------
def test_end_of_simulation_flush():
    st = _active_state()
    st.begin_active(0.0)
    st.flush_at(T_SIM)
    assert math.isclose(st.active_time_s, T_SIM)
    assert math.isclose(st.energy_kwh(), EXPECTED_ENERGY_KWH, rel_tol=REL_TOL_KWH)


# 10 ------------------------------------------------------------------------
def test_end_of_simulation_flush_is_idempotent():
    st = _active_state()
    st.begin_active(0.0)
    st.flush_at(T_SIM)
    e1 = st.energy_kwh()
    st.flush_at(T_SIM)          # second call must add nothing
    st.flush_at(T_SIM)
    e2 = st.energy_kwh()
    assert math.isclose(e1, e2, rel_tol=0.0, abs_tol=0.0)
    assert math.isclose(st.active_time_s, T_SIM)


# 11 ------------------------------------------------------------------------
def test_no_energy_after_simulation_cutoff():
    st = _active_state()
    st.begin_active(0.0)
    st.flush_at(5000.0)         # cutoff at 5000
    assert math.isclose(st.active_time_s, 5000.0)
    # a later flush cannot retroactively add the 5000..10000 window
    st.flush_at(10000.0)
    assert math.isclose(st.active_time_s, 5000.0)
    # and flush never accounts beyond the cutoff even if start < cutoff
    st2 = _active_state()
    st2.begin_active(9000.0)
    st2.flush_at(10000.0)
    assert st2.active_time_s <= 1000.0 + 1e-9


# 12 ------------------------------------------------------------------------
def test_zero_idle_is_explicit_lower_bound():
    st = _active_state(idle_power_w=0.0)     # explicit theoretical lower bound
    st.begin_idle(0.0)
    st.close(1000.0)
    assert math.isclose(st.idle_time_s, 1000.0)
    assert st.idle_energy_j() == 0.0
    assert st.energy_kwh() == 0.0


# 13 ------------------------------------------------------------------------
def test_nonzero_idle_energy_is_accounted():
    st = _active_state(idle_power_w=500.0)
    st.begin_idle(0.0)
    st.close(100.0)
    assert math.isclose(st.idle_energy_j(), 500.0 * 100.0)
    assert st.energy_kwh() > 0.0


# 14 ------------------------------------------------------------------------
def test_stale_producing_active_time_consumes_energy():
    # A miner that was active and produced a (later stale) block still consumed
    # energy for its active time. This validates ACCOUNTING ONLY; it does not
    # repair stale-event behaviour.
    st = _active_state()
    st.begin_active(0.0)
    st.close(100.0)             # produced a block at t=100 that becomes stale
    assert st.active_time_s == 100.0
    assert st.active_energy_j() == st.active_power_w * 100.0
    assert st.energy_kwh() > 0.0


# 15 ------------------------------------------------------------------------
def test_no_redundancy_double_counting():
    st = _active_state()
    st.begin_active(0.0)
    st.close(100.0)
    # energy is P*t exactly -- NOT multiplied by any redundancy factor
    assert math.isclose(st.active_energy_j(), st.active_power_w * 100.0,
                        rel_tol=1e-12)
    # sum over a network equals a single count of active energy
    acc = WallClockEnergyAccountant(EFF_J_PER_TH)
    acc.add_equal_miners(10, NET_HPS)
    for mid in acc.miners:
        acc.transition(mid, ACTIVE, 0.0)
    acc.flush_all(100.0)
    expected = network_active_power_w(NET_HPS, EFF_J_PER_TH) * 100.0 / J_PER_KWH
    assert math.isclose(acc.total_energy_kwh(), expected, rel_tol=1e-12)


# 16 ------------------------------------------------------------------------
def test_no_block_time_divided_by_miner_count():
    # N miners active for the same T with the same aggregate hash rate must give
    # the SAME total energy regardless of N (would differ by 1/N under the old
    # block_time/N division).
    def total(n):
        acc = WallClockEnergyAccountant(EFF_J_PER_TH)
        acc.add_equal_miners(n, NET_HPS)
        for mid in acc.miners:
            acc.transition(mid, ACTIVE, 0.0)
        acc.flush_all(T_SIM)
        return acc.total_energy_kwh()
    assert math.isclose(total(100), total(500), rel_tol=1e-12)
    # and the deprecated PoCol hook no longer determines energy
    from Models.PoCol import Consensus as pocol_consensus
    assert pocol_consensus.Consensus.apply_energy_for_created_block(object()) is None
    src = inspect.getsource(pocol_consensus)
    assert "block_time / float(N)" not in src
    assert "time_share" not in src


# 17 ------------------------------------------------------------------------
def test_hash_based_and_power_based_crosscheck():
    st = _active_state()
    st.begin_active(0.0)
    st.close(3600.0)
    # power-based and hash-count-based active energy agree under compatible
    # assumptions (active_power == hash_rate * J/hash).
    assert math.isclose(st.active_energy_j(), st.hash_based_active_energy_j(),
                        rel_tol=1e-12)


# 18 ------------------------------------------------------------------------
def test_existing_journal_energy_models_unchanged():
    from Models.Energy import (PowEconomicEnergyModel, PosValidatorEnergyModel,
                               CarbonFootprintModel, GAMMA_SCENARIOS)
    pw = PowEconomicEnergyModel(block_subsidy=3.125, avg_tx_fees=0.30,
                                coin_price=60000.0, electricity_price_per_kwh=0.05,
                                electricity_spend_ratio_kappa=0.80)
    assert math.isclose(pw.energy_budget_per_block_kwh(), 3_288_000.0, rel_tol=1e-9)
    pos = PosValidatorEnergyModel(validator_count=1000, validator_power_watts=100.0,
                                  simulation_time_hours=24.0, uptime_ratio=1.0)
    assert math.isclose(pos.total_energy_kwh(), 2400.0, rel_tol=1e-9)
    assert GAMMA_SCENARIOS["average"] == 0.475
    assert math.isclose(CarbonFootprintModel(scenario="average").carbon_kg(1000.0),
                        475.0, rel_tol=1e-12)


# 19 ------------------------------------------------------------------------
def test_energy_units_conversion():
    assert math.isclose(joules_to_kwh(3_600_000.0), 1.0, rel_tol=1e-12)
    assert math.isclose(kwh_to_joules(1.0), 3_600_000.0, rel_tol=1e-12)
    assert math.isclose(th_per_s_to_hps(141.0), 141e12, rel_tol=1e-12)
    assert math.isclose(efficiency_j_per_hash(21.5), 21.5e-12, rel_tol=1e-12)
    assert math.isclose(hashes_to_energy_j(1e12, 21.5), 21.5, rel_tol=1e-12)
    assert J_PER_KWH == 3_600_000.0 and HASHES_PER_TH == 1e12


# 20 ------------------------------------------------------------------------
def test_homogeneous_100_500_miner_power_equivalence():
    powers = []
    for n in (100, 200, 300, 400, 500):
        acc = WallClockEnergyAccountant(EFF_J_PER_TH)
        acc.add_equal_miners(n, NET_HPS)
        powers.append(acc.total_active_power_w())
    for p in powers:
        assert math.isclose(p, EXPECTED_POWER_W, abs_tol=ABS_TOL_W)
    assert max(powers) - min(powers) < ABS_TOL_W
