"""Stage 8X validation suite (brief section 25).

Run with:  python -m pytest experiments/stage8x/tests -q
or via:    python -m experiments.stage8x.validate
"""

from __future__ import annotations

import dataclasses
import math
import random

import pytest

from experiments.stage8x.config import difficulty as diffmod
from experiments.stage8x.config import seeds as seedmod
from experiments.stage8x.config import stage8x_config as C
from experiments.stage8x.config.asic import (
    ALPHA_CASES,
    J_PER_KWH,
    S21_PRO,
    S21PRO_ACTIVE_POWER_W,
    S21PRO_EFFICIENCY_J_PER_TH,
    S21PRO_HASHRATE_THS,
    TH,
)
from experiments.stage8x.simulator import energy as energymod
from experiments.stage8x.simulator import hashing
from experiments.stage8x.simulator.engine import simulate
from experiments.stage8x.simulator.powerstate import PowerStateLedger

NETWORK_SIZES = list(C.NETWORK_SIZES)


# --------------------------------------------------------------------------
# 1. Hardware arithmetic
# --------------------------------------------------------------------------
@pytest.mark.parametrize("n", NETWORK_SIZES)
def test_aggregate_hashrate_scales_with_n(n):
    assert S21_PRO.aggregate_hashrate_ths(n) == pytest.approx(n * 234.0)
    assert S21_PRO.aggregate_hashrate_hps(n) == pytest.approx(n * 234.0 * TH)


@pytest.mark.parametrize("n", NETWORK_SIZES)
def test_aggregate_power_scales_with_n(n):
    assert S21_PRO.aggregate_active_power_w(n) == pytest.approx(n * 3510.0)


def test_expected_scaling_table_matches_brief():
    expected = {
        100: (23.4, 351_000.0),
        200: (46.8, 702_000.0),
        300: (70.2, 1_053_000.0),
        400: (93.6, 1_404_000.0),
        500: (117.0, 1_755_000.0),
    }
    for n, (phs, watts) in expected.items():
        assert S21_PRO.aggregate_hashrate_ths(n) / 1000.0 == pytest.approx(phs)
        assert S21_PRO.aggregate_active_power_w(n) == pytest.approx(watts)


def test_per_miner_specs_are_n_invariant():
    for n in NETWORK_SIZES:
        spec = diffmod.derive(n)
        assert S21_PRO.hashrate_ths == 234.0
        assert S21_PRO.active_power_w == 3510.0
        assert spec.range_per_miner == int(round(S21_PRO.hashrate_hps * spec.epoch_sweep_s))


# --------------------------------------------------------------------------
# 2. S21 Pro internal consistency
# --------------------------------------------------------------------------
def test_s21_consistency_234_times_15_equals_3510():
    assert S21PRO_HASHRATE_THS * S21PRO_EFFICIENCY_J_PER_TH == pytest.approx(
        S21PRO_ACTIVE_POWER_W
    )
    assert S21_PRO.consistency_error_w() == pytest.approx(0.0, abs=1e-9)


def test_low_power_is_alpha_times_active():
    for label, alpha in ALPHA_CASES.items():
        assert S21_PRO.low_power_w(alpha) == pytest.approx(alpha * 3510.0)
    assert S21_PRO.low_power_w(0.10) == pytest.approx(351.0)
    assert S21_PRO.low_power_w(0.25) == pytest.approx(877.5)
    assert S21_PRO.low_power_w(0.50) == pytest.approx(1755.0)


# --------------------------------------------------------------------------
# 3. Energy baseline and low-power energy
# --------------------------------------------------------------------------
def test_energy_baseline_full_active_run():
    T = C.HORIZON_S
    res = energymod.account(T, 0.0, S21_PRO.active_power_w, alpha=0.0)
    assert res.total_energy_j == pytest.approx(3510.0 * T)
    assert res.total_energy_kwh == pytest.approx(3510.0 * T / J_PER_KWH)


@pytest.mark.parametrize("alpha", [0.0, 0.10, 0.25, 0.50])
@pytest.mark.parametrize("t_a,t_l", [(10000.0, 0.0), (7000.0, 3000.0), (0.0, 10000.0)])
def test_low_power_energy_formula(alpha, t_a, t_l):
    res = energymod.account(t_a, t_l, S21_PRO.active_power_w, alpha)
    assert res.total_energy_j == pytest.approx(3510.0 * t_a + alpha * 3510.0 * t_l)


def test_joule_to_kwh_conversion_constant():
    assert J_PER_KWH == 3.6e6
    res = energymod.account(3.6e6 / 3510.0, 0.0, 3510.0, 0.0)
    assert res.total_energy_kwh == pytest.approx(1.0)


def test_energy_saving_fraction_and_na_handling():
    assert energymod.energy_saving_fraction(80.0, 100.0) == pytest.approx(0.2)
    assert energymod.energy_saving_fraction(100.0, 0.0) is None
    assert energymod.account(1.0, 1.0, 3510.0, 0.0).energy_per_block_kwh(0) is None


# --------------------------------------------------------------------------
# 4. State-time conservation
# --------------------------------------------------------------------------
def test_power_state_ledger_conservation_synthetic():
    led = PowerStateLedger(3, 100.0)
    led.to_low_power(0, 20.0)
    led.to_active(0, 50.0)
    led.to_low_power(1, 10.0)
    led.close()
    assert led.t_active[0] + led.t_low[0] == pytest.approx(100.0)
    assert led.t_low[0] == pytest.approx(30.0)
    assert led.t_low[1] == pytest.approx(90.0)
    assert led.t_low[2] == pytest.approx(0.0)
    assert led.conservation_error() == pytest.approx(0.0, abs=1e-9)
    assert led.low_power_fraction == pytest.approx(120.0 / 300.0)


@pytest.mark.parametrize("protocol", [C.PROTO_POW, C.PROTO_POCOL])
def test_state_time_conservation_in_real_runs(protocol):
    cfg = C.RunConfig(protocol=protocol, n_miners=100,
                      seed=seedmod.pilot_seeds()[0], seed_index=1, phase="pilot")
    r = simulate(cfg)
    assert r.power_state_summary["state_time_conservation_error_s"] < 1e-6
    assert r.active_miner_seconds + r.low_power_miner_seconds == pytest.approx(
        r.n_miners * r.simulation_seconds, rel=1e-12
    )


def test_pow_is_active_for_the_whole_horizon():
    cfg = C.RunConfig(protocol=C.PROTO_POW, n_miners=100,
                      seed=seedmod.pilot_seeds()[0], seed_index=1, phase="pilot")
    r = simulate(cfg)
    assert r.low_power_miner_seconds == pytest.approx(0.0)
    assert r.active_miner_seconds == pytest.approx(100 * C.HORIZON_S)


# --------------------------------------------------------------------------
# 5. Disjoint PoCol ranges
# --------------------------------------------------------------------------
@pytest.mark.parametrize("n", NETWORK_SIZES)
def test_pocol_ranges_are_disjoint_and_tile_the_domain(n):
    spec = diffmod.derive(n)
    ranges = diffmod.disjoint_ranges(spec)
    assert len(ranges) == n
    assert ranges[0][0] == 0
    assert ranges[-1][1] == spec.nonce_domain
    for i in range(len(ranges) - 1):
        assert ranges[i][1] == ranges[i + 1][0]         # contiguous
        assert ranges[i][1] <= ranges[i + 1][0]         # R_i ∩ R_{i+1} = empty
    # explicit pairwise emptiness on a sample of pairs
    rng = random.Random(0)
    for _ in range(200):
        i, j = rng.randrange(n), rng.randrange(n)
        if i == j:
            continue
        a, b = ranges[i], ranges[j]
        assert max(a[0], b[0]) >= min(a[1], b[1])       # empty intersection
    assert sum(e - s for s, e in ranges) == spec.nonce_domain


# --------------------------------------------------------------------------
# 6. No PoCol exact duplicates
# --------------------------------------------------------------------------
@pytest.mark.parametrize("n", [100, 300, 500])
def test_pocol_has_zero_exact_duplicate_evaluations(n):
    cfg = C.RunConfig(protocol=C.PROTO_POCOL, n_miners=n,
                      seed=seedmod.pilot_seeds()[1], seed_index=2, phase="pilot")
    r = simulate(cfg)
    assert r.duplicate_evaluations == 0
    assert r.duplicate_ratio == pytest.approx(0.0)
    assert r.unique_evaluations == r.total_evaluations


def test_traditional_pow_has_zero_exact_duplicates_but_high_nonce_reuse():
    """Distinct templates => distinct serialized inputs, even with identical nonces."""
    cfg = C.RunConfig(protocol=C.PROTO_POW, n_miners=100,
                      seed=seedmod.pilot_seeds()[1], seed_index=2, phase="pilot")
    r = simulate(cfg)
    assert r.duplicate_evaluations == 0
    # ... yet essentially every 32-bit nonce value is evaluated many times over.
    assert r.nonce_value_reuse_ratio > 0.999999


def test_matched_template_pow_does_produce_exact_duplicates():
    cfg = C.RunConfig(protocol=C.PROTO_POW_MT, n_miners=100,
                      seed=seedmod.pilot_seeds()[1], seed_index=2,
                      phase="secondary", tag="MT")
    r = simulate(cfg)
    assert r.duplicate_evaluations > 0
    assert 0.20 < r.duplicate_ratio < 0.50      # theory: 1-(1-1/N)^N -> 1-e^-1


def test_duplicate_identity_holds():
    for proto in (C.PROTO_POW, C.PROTO_POCOL, C.PROTO_POW_MT):
        cfg = C.RunConfig(protocol=proto, n_miners=100,
                          seed=seedmod.pilot_seeds()[2], seed_index=3, phase="pilot")
        r = simulate(cfg)
        assert r.total_evaluations == r.unique_evaluations + r.duplicate_evaluations


# --------------------------------------------------------------------------
# 7. Matched difficulty
# --------------------------------------------------------------------------
@pytest.mark.parametrize("n", NETWORK_SIZES)
def test_pow_and_pocol_share_the_same_difficulty_and_target(n):
    seed = seedmod.primary_seeds()[0]
    a = C.RunConfig(protocol=C.PROTO_POW, n_miners=n, seed=seed, seed_index=1)
    b = C.RunConfig(protocol=C.PROTO_POCOL, n_miners=n, seed=seed, seed_index=1)
    assert a.spec.difficulty == b.spec.difficulty
    assert a.spec.target_int == b.spec.target_int
    assert a.spec.q_per_candidate == b.spec.q_per_candidate


@pytest.mark.parametrize("n", NETWORK_SIZES)
def test_difficulty_is_coupled_to_aggregate_hashrate(n):
    spec = diffmod.derive(n)
    h_total = S21_PRO.aggregate_hashrate_hps(n)
    assert spec.difficulty == pytest.approx(h_total * 600.0 / 2 ** 32)
    assert spec.expected_hashes_per_block == pytest.approx(h_total * 600.0)
    # D_N proportional to H_N
    base = diffmod.derive(100)
    assert spec.difficulty / base.difficulty == pytest.approx(n / 100.0)


def test_difficulty_yields_600s_expected_interval():
    for n in NETWORK_SIZES:
        spec = diffmod.derive(n)
        h_total = S21_PRO.aggregate_hashrate_hps(n)
        assert 1.0 / (h_total * spec.q_per_candidate) == pytest.approx(600.0)


def test_target_probability_mapping():
    for n in NETWORK_SIZES:
        spec = diffmod.derive(n)
        assert spec.target_int / hashing.TWO_256 == pytest.approx(
            spec.q_per_candidate, rel=1e-9
        )


# --------------------------------------------------------------------------
# 8. Real SHA-256 semantics behind the rate abstraction
# --------------------------------------------------------------------------
def test_real_double_sha256_matches_target_probability():
    """Monte-Carlo on genuinely hashed candidates pins q = target / 2**256."""
    target = hashing.TWO_256 // 64          # q = 1/64, tractable to measure
    trials = 20000
    hits, q = hashing.monte_carlo_success_rate(target, trials, seed=12345)
    assert q == pytest.approx(1.0 / 64.0, rel=1e-9)
    se = math.sqrt(q * (1 - q) / trials)
    assert abs(hits / trials - q) < 4.0 * se


def test_candidate_identity_is_template_plus_index():
    a = hashing.candidate_bytes("tpl-A", 5)
    b = hashing.candidate_bytes("tpl-B", 5)
    c = hashing.candidate_bytes("tpl-A", 6)
    assert a != b and a != c                       # same nonce, different template
    assert hashing.candidate_bytes("tpl-A", 5) == a
    # candidate_index decomposes into (extranonce, nonce)
    assert hashing.candidate_bytes("t", 2 ** 32 + 7)[-8:] == (1).to_bytes(4, "big") + (7).to_bytes(4, "big")


def test_scan_ledger_exact_duplicate_arithmetic():
    led = hashing.ScanLedger()
    led.record("t1", 0, 100)
    led.record("t1", 50, 150)      # 50 overlapping
    led.record("t2", 0, 100)       # different template: never a duplicate
    assert led.total_evaluations == 300
    assert led.unique_evaluations() == 250
    assert led.duplicate_evaluations() == 50


def test_winner_oracle_rate():
    """Expected winners over a domain equals q * domain (law of large numbers)."""
    rng = random.Random(7)
    q, dom, reps = 1e-3, 10_000, 400
    counts = [len(hashing.sample_winners(rng, dom, q)) for _ in range(reps)]
    assert abs(sum(counts) / reps - q * dom) < 0.5


# --------------------------------------------------------------------------
# 9. Seed reproducibility and registry hygiene
# --------------------------------------------------------------------------
@pytest.mark.parametrize("protocol", [C.PROTO_POW, C.PROTO_POCOL, C.PROTO_POW_MT])
def test_same_seed_reproduces_identical_physical_results(protocol):
    cfg = C.RunConfig(protocol=protocol, n_miners=200,
                      seed=seedmod.pilot_seeds()[3], seed_index=4, phase="pilot")
    r1, r2 = simulate(cfg), simulate(cfg)
    for f in ("accepted_blocks", "blocks_created", "total_evaluations",
              "unique_evaluations", "duplicate_evaluations", "range_completions",
              "epoch_exhaustions", "active_miner_seconds", "low_power_miner_seconds"):
        assert getattr(r1, f) == getattr(r2, f)
    assert r1.block_intervals == r2.block_intervals


def test_seed_registry_is_fresh_and_partitioned():
    prim, pil = seedmod.primary_seeds(), seedmod.pilot_seeds()
    assert len(prim) == 30 and len(set(prim)) == 30
    assert len(pil) == 5 and len(set(pil)) == 5
    assert not (set(prim) & set(pil))            # Pilot seeds never enter the primary set
    assert "Stage8X" in seedmod.NAMESPACE
    assert seedmod.primary_seeds() == prim       # deterministic
    # not the legacy revision-experiment base
    assert 20260101 not in prim


def test_seed_pairing_between_protocols():
    runs = C.primary_matrix()
    by_key = {}
    for r in runs:
        by_key.setdefault((r.n_miners, r.seed_index), {})[r.protocol] = r.seed
    for (_n, _k), d in by_key.items():
        assert d[C.PROTO_POW] == d[C.PROTO_POCOL]


# --------------------------------------------------------------------------
# 10. alpha invariance of the physical trajectory
# --------------------------------------------------------------------------
def test_alpha_is_not_a_simulation_parameter():
    fields = {f.name for f in dataclasses.fields(C.RunConfig)}
    assert "alpha" not in fields and "p_low" not in fields
    src = open("experiments/stage8x/simulator/engine.py", encoding="utf-8").read()
    assert "alpha" not in src.lower().replace("alphabet", "")


def test_alpha_only_changes_energy_not_trajectory():
    cfg = C.RunConfig(protocol=C.PROTO_POCOL, n_miners=300,
                      seed=seedmod.pilot_seeds()[4], seed_index=5, phase="pilot")
    r = simulate(cfg)
    prices = energymod.account_all_alphas(
        r.active_miner_seconds, r.low_power_miner_seconds, S21_PRO.active_power_w
    )
    r2 = simulate(cfg)
    # trajectory identical regardless of any energy pricing performed
    assert (r.accepted_blocks, r.total_evaluations, r.block_intervals,
            r.active_miner_seconds, r.low_power_miner_seconds) == (
        r2.accepted_blocks, r2.total_evaluations, r2.block_intervals,
        r2.active_miner_seconds, r2.low_power_miner_seconds)
    # only energy-derived quantities move, and monotonically in alpha
    tot = [prices[k].total_energy_kwh for k in ("LP0", "LP10", "LP25", "LP50")]
    assert tot == sorted(tot)
    assert all(p.active_energy_j == pytest.approx(prices["LP0"].active_energy_j)
               for p in prices.values())


# --------------------------------------------------------------------------
# 11. Work-accounting identity and block-interval calibration
# --------------------------------------------------------------------------
@pytest.mark.parametrize("protocol", [C.PROTO_POW, C.PROTO_POCOL, C.PROTO_POW_MT])
def test_total_work_equals_rate_times_active_time(protocol):
    cfg = C.RunConfig(protocol=protocol, n_miners=200,
                      seed=seedmod.pilot_seeds()[0], seed_index=1, phase="pilot")
    r = simulate(cfg)
    assert r.work_accounting_error < 1e-9
    assert r.total_evaluations == pytest.approx(
        S21_PRO.hashrate_hps * r.active_miner_seconds, rel=1e-9
    )


def test_pow_mean_block_interval_is_near_600s():
    """Statistical calibration check across the dedicated pilot seeds."""
    blocks, horizon = 0, 0.0
    for k, s in enumerate(seedmod.pilot_seeds(), start=1):
        r = simulate(C.RunConfig(protocol=C.PROTO_POW, n_miners=300,
                                 seed=s, seed_index=k, phase="pilot"))
        blocks += r.accepted_blocks
        horizon += r.simulation_seconds
    mean_interval = horizon / blocks
    assert 400.0 < mean_interval < 900.0        # ~600 s +- Poisson sampling error


def test_predicted_epoch_exhaustion_probability():
    spec = diffmod.derive(100)
    assert spec.expected_winners_per_epoch == pytest.approx(1.0, rel=1e-6)
    assert spec.p_epoch_exhaustion == pytest.approx(math.exp(-1.0), rel=1e-6)


# --------------------------------------------------------------------------
# 12. Non-interference with earlier experiments
# --------------------------------------------------------------------------
def test_stage8x_never_imports_global_inputsconfig():
    import os

    root = "experiments/stage8x"
    banned = ("InputsConfig", "from Main", "import Main", "from Scheduler",
              "from Statistics", "from Event")
    for dirpath, _dirs, files in os.walk(root):
        for fn in files:
            if not fn.endswith(".py"):
                continue
            path = os.path.join(dirpath, fn)
            src = open(path, encoding="utf-8").read()
            for b in banned:
                # references inside documentation strings are fine; imports are not
                for line in src.splitlines():
                    ls = line.strip()
                    if ls.startswith(("import ", "from ")) and b.split()[-1] in ls:
                        raise AssertionError(f"{path} imports {b}")


def test_config_matrix_shape():
    runs = C.primary_matrix()
    assert len(runs) == 300
    assert len({r.run_id for r in runs}) == 300
    assert sum(1 for r in runs if r.protocol == C.PROTO_POW) == 150
    assert sum(1 for r in runs if r.protocol == C.PROTO_POCOL) == 150
    assert {r.n_miners for r in runs} == set(NETWORK_SIZES)
    for n in NETWORK_SIZES:
        assert sum(1 for r in runs if r.n_miners == n) == 60
    assert len(ALPHA_CASES) == 4
    assert 300 // 2 * len(ALPHA_CASES) == 600      # PoCol sensitivity observations
