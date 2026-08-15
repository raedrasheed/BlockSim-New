"""Stage 8X-ND validation suite — the 21 required tests of brief section 36."""

import os

import pytest

from experiments.stage8xnd.config.nd_config import (
    ARM_PC, ARM_PC_NOLP, ARM_PW, ARM_PW_OFFSET, HASHRATE_HPS, MAX_NONCE,
    N_GRID, NONCE_DOMAIN_SIZE, PHYSICAL_ARMS, T_RUN_S, difficulty, partition,
    per_miner_domain, predictions, q_per_candidate, sweep_timing,
)
from experiments.stage8xnd.config.seeds import (
    pilot_seeds, primary_seeds, verify_disjoint,
)
from experiments.stage8xnd.src.engine_nd import (
    energy_j, nolp_matches_physical, run_physical,
)

REPO = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))


def test_t01_domain_size():
    assert NONCE_DOMAIN_SIZE == 2 ** 32


def test_t02_max_nonce():
    assert MAX_NONCE == 2 ** 32 - 1
    for n in N_GRID:
        assert partition(n)[-1][1] == MAX_NONCE     # inclusive end, never 2^32


@pytest.mark.parametrize("n", N_GRID)
def test_t03_pw_full_domain(n):
    for i in (0, n // 2, n - 1):
        assert per_miner_domain(n, ARM_PW, i) == NONCE_DOMAIN_SIZE
        assert per_miner_domain(n, ARM_PW_OFFSET, i) == NONCE_DOMAIN_SIZE


@pytest.mark.parametrize("n", N_GRID)
def test_t04_t05_t06_t07_partition(n):
    rs = partition(n)
    # every PC miner gets ONLY its partition
    sizes = [e - s + 1 for s, e in rs]
    for i in (0, n - 1):
        assert per_miner_domain(n, ARM_PC, i) == sizes[i] < NONCE_DOMAIN_SIZE
    # full coverage + zero overlap (contiguous inclusive tiling)
    assert rs[0][0] == 0 and rs[-1][1] == MAX_NONCE
    for (s1, e1), (s2, e2) in zip(rs, rs[1:]):
        assert e1 + 1 == s2
    assert sum(sizes) == NONCE_DOMAIN_SIZE
    # size spread <= 1
    assert max(sizes) - min(sizes) <= 1


def test_t08_t09_sweep_times():
    t = sweep_timing(100)
    assert t["t_full_sweep_s"] == pytest.approx(2 ** 32 / 234e12)
    assert t["t_range_sweep_s"] == pytest.approx(
        t["range_nonces_max"] / 234e12)
    assert t["t_full_sweep_s"] == pytest.approx(1.8355e-5, rel=1e-3)
    assert sweep_timing(500)["t_range_sweep_s"] == pytest.approx(
        3.671e-8, rel=1e-3)


def test_t10_pw_reset_after_full_sweep():
    r = run_physical(ARM_PW, 100, 101)
    # zero-start: a nonce reset per completed sweep (+1 per round boundary)
    assert r.nonce_resets > r.nonce_domain_exhaustions > 0
    per_miner = r.template_epochs_completed / 100
    assert per_miner == pytest.approx(T_RUN_S * HASHRATE_HPS / 2 ** 32,
                                      rel=1e-6)


def test_t11_pc_epoch_reset_after_union_exhaustion():
    r = run_physical(ARM_PC, 100, 102)
    hi = sweep_timing(100)["range_nonces_max"]
    assert r.template_epochs_completed == pytest.approx(
        T_RUN_S * HASHRATE_HPS / hi, rel=1e-6)


def test_t12_header_ids_change():
    # header renewal counts equal completed sweeps (per miner for PW,
    # per network epoch for PC) and are exact integers
    pw = run_physical(ARM_PW, 100, 103)
    assert pw.template_epochs_completed == pw.nonce_domain_exhaustions
    pc = run_physical(ARM_PC, 100, 103)
    assert pc.nonce_domain_exhaustions == pc.template_epochs_completed * 100


def test_t13_same_nonce_different_headers_distinct_candidate():
    # engine-level: ND-PW exact duplication is zero although every miner
    # evaluates every nonce value (cross-miner m_max = N)
    r = run_physical(ARM_PW, 100, 104)
    run_sc = {sc["scope"]: sc for sc in r.scope_rows}["NR-global-run"]
    assert run_sc["rho_exact"] == 0.0
    assert run_sc["m_max"] == 100
    assert run_sc["U_nonce"] == NONCE_DOMAIN_SIZE


def test_t14_low_power_only_after_range_completion():
    r = run_physical(ARM_PC, 400, 105)
    # F_low equals the straggler-gap closed form: low power occurs only in
    # the post-range interval of each epoch
    f = r.t_low_miner_s / (400 * T_RUN_S)
    assert f == pytest.approx(predictions(400)["f_low_expected"], rel=1e-3)


def test_t15_nolp_physicals_identical():
    r = run_physical(ARM_PC, 100, 106)
    chk = nolp_matches_physical(r)
    assert chk["e_nolp_equals_full"] < 1e-6      # E_NOLP = P*N*T exactly
    # physics untouched by policy relabeling
    assert chk["same_C_total"] == float(r.C_total)


@pytest.mark.parametrize("arm", PHYSICAL_ARMS)
def test_t16_state_time_sums(arm):
    r = run_physical(arm, 100, 107)
    assert r.identity_errors["state_time_conservation_rel"] < 1e-12


def test_t17_energy_equation_exact():
    r = run_physical(ARM_PC, 100, 108)
    for a in (0.0, 0.10, 0.25, 0.50):
        assert energy_j(r, ARM_PC, a) == 3510.0 * (
            r.t_active_miner_s + a * r.t_low_miner_s)


@pytest.mark.parametrize("n", N_GRID)
def test_t18_same_target(n):
    assert q_per_candidate(n) == 1.0 / (n * 234e12 * 600.0)
    assert difficulty(n) * 2 ** 32 * q_per_candidate(n) == pytest.approx(1.0)
    # arms share the target by construction: q depends on N only


def test_t19_seed_reproducibility():
    a = run_physical(ARM_PC, 100, 109)
    b = run_physical(ARM_PC, 100, 109)
    assert (a.C_total, a.accepted_blocks, a.intervals_s,
            a.t_low_miner_s) == (b.C_total, b.accepted_blocks,
                                 b.intervals_s, b.t_low_miner_s)


def test_t20_abstraction_vs_toy():
    # the event abstraction's interval arithmetic is validated against
    # explicit set enumeration on toy cyclic domains in the frozen Stage 8X-NR
    # suite (Tests 9/10 there); re-assert the imported functions here.
    from experiments.stage8xnr.src.noncedomain import union_measure
    import random
    rng = random.Random(20)
    S = 128
    for _ in range(50):
        arcs = [(rng.randrange(S), rng.randrange(0, S + 1)) for _ in range(4)]
        explicit = set()
        for st, L in arcs:
            explicit |= {(st + i) % S for i in range(L)}
        assert union_measure(arcs, S) == len(explicit)


def test_t21_analytic_block_rate():
    # pooled over 20 seeds: mean blocks/run within preregistered 10% of 16.67
    for arm in (ARM_PW, ARM_PC):
        blocks = [run_physical(arm, 100, s).accepted_blocks
                  for s in range(300, 320)]
        mean = sum(blocks) / len(blocks)
        assert mean == pytest.approx(T_RUN_S / 600.0, rel=0.10), arm


def test_seeds_registry():
    assert len(primary_seeds()) == 30 and len(pilot_seeds()) == 2
    rep = verify_disjoint(REPO)
    assert rep["disjoint"], rep
    assert any("stage8xe50" in c for c in rep["checked_registries"])


def test_trial_rate_identity_paired():
    # TQ4: paired runs give (near-)identical block sequences for PW and PC
    pw = run_physical(ARM_PW, 100, 110)
    pc = run_physical(ARM_PC, 100, 110)
    assert pw.accepted_blocks == pc.accepted_blocks
    for x, y in zip(pw.intervals_s, pc.intervals_s):
        assert abs(x - y) / x < 0.05
