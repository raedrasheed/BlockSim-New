"""Hash-rate-aware difficulty — invariants (spec §16; grows with each commit).

Run:  python -m pytest tests/test_hashrate_aware_difficulty.py -v
  or:  python tests/test_hashrate_aware_difficulty.py
"""
import os
import sys
import math
import statistics

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

from experiments.hashrate_aware_difficulty.configuration import (
    DiffExpConfig, DifficultyConfig, PowerConfig,
    PROTO_DUP, PROTO_IND, PROTO_POCOL, HW_H1, HW_H2,
    D1_CONSTANT, D2_SCALED, D3_RETARGET, AGG_HASHRATE_HPS,
)
from experiments.hashrate_aware_difficulty import target as tg
from experiments.hashrate_aware_difficulty.difficulty import (
    initial_target, difficulty_ratio_vs_reference,
)
from experiments.hashrate_aware_difficulty.mining_round import simulate, _domain_total


def _cfg(protocol=PROTO_POCOL, N=10, hardware=HW_H2, mode=D2_SCALED, seed=0,
         sim=10200.0, h2_rate=100.0, budget=1200.0, **dkw):
    return DiffExpConfig(
        N=N, protocol=protocol, hardware=hardware,
        difficulty=DifficultyConfig(mode=mode, **dkw),
        seed=seed, sim_seconds=sim, h2_miner_hashrate_hps=h2_rate,
        domain_time_budget=budget)


# ===========================================================================
# Section-4 mandatory test: the double-scaling defect is gone
# ===========================================================================
def test_no_double_scaling_share_exhaust_time_is_budget():
    """H1: M_total = H_network*budget (NOT (H/N)*budget). Each equal share then
    exhausts in exactly `budget` seconds for EVERY N: T_i = M_i/H_i = budget."""
    for N in (1, 2, 5, 10, 100, 500):
        cfg = DiffExpConfig(N=N, hardware=HW_H1, domain_time_budget=1200.0)
        M_total = _domain_total(cfg)
        assert abs(M_total - AGG_HASHRATE_HPS * 1200.0) <= cfg.N, (N, M_total)
        m_i = M_total / N
        h_i = cfg.per_miner_hashrate()
        assert math.isclose(m_i / h_i, 1200.0, rel_tol=1e-9), \
            f"N={N}: share exhaust time {m_i/h_i} != budget (double scaling back?)"


def test_no_double_scaling_discovery_not_600_over_N():
    """H1 + D2: discovery-time distribution is governed by p*H_network alone, so
    the MEAN block interval must stay ~600 s for every N — the old artificial
    600/N discovery must not exist."""
    means = {}
    for N in (1, 10, 100):
        ivs = []
        for seed in range(30):
            m, _, _ = simulate(_cfg(PROTO_POCOL, N=N, hardware=HW_H1,
                                    mode=D2_SCALED, seed=seed, sim=30000.0))
            if m["accepted_blocks"] >= 2:
                ivs.append(m["mean_block_interval_s"])
        means[N] = statistics.mean(ivs)
        assert abs(means[N] - 600.0) / 600.0 < 0.20, \
            f"H1 N={N}: mean interval {means[N]:.1f}s not ~600s"
    # and N=100 must NOT be ~6s (the defect's signature)
    assert means[100] > 100.0, f"600/N artifact returned: {means[100]}"


# ===========================================================================
# Section-9 mandatory numerical example — Case A (D1 CONSTANT under H2)
# reference: 1 miner @ 100 c/s, T=600 => W_1 = 60000, p_1 = 1/60000
# ===========================================================================
def test_spec9_caseA_constant_difficulty_gives_60s():
    """N=10 under H2 with CONSTANT difficulty: H=1000 c/s, E[T] = 60000/1000 = 60 s."""
    t1 = tg.target_for(100.0, 600.0)
    cfgA = _cfg(PROTO_POCOL, N=10, hardware=HW_H2, mode=D1_CONSTANT, h2_rate=100.0)
    assert initial_target(cfgA) == t1                       # frozen at reference
    assert math.isclose(tg.p_from_target(t1), 1.0 / 60000.0, rel_tol=1e-6)
    assert math.isclose(tg.expected_block_time(t1, 1000.0), 60.0, rel_tol=1e-6)
    # simulated mean interval ~ 60 s
    ivs = []
    for seed in range(30):
        m, _, _ = simulate(_cfg(PROTO_POCOL, N=10, hardware=HW_H2,
                                mode=D1_CONSTANT, h2_rate=100.0,
                                seed=seed, sim=12000.0))
        if m["accepted_blocks"] >= 5:
            ivs.append(m["mean_block_interval_s"])
    mean = statistics.mean(ivs)
    assert abs(mean - 60.0) / 60.0 < 0.15, f"constant-difficulty interval {mean:.1f}s != ~60s"


# ===========================================================================
# Section-9 mandatory example — Case B (D2 SCALED under H2) + section-10 H1 test
# ===========================================================================
def test_spec9_caseB_scaled_difficulty_gives_600s_and_10x():
    t1 = tg.target_for(100.0, 600.0)
    cfg10 = _cfg(PROTO_POCOL, N=10, hardware=HW_H2, mode=D2_SCALED, h2_rate=100.0)
    t10 = initial_target(cfg10)
    d1 = tg.difficulty_from_target(t1)
    d10 = tg.difficulty_from_target(t10)
    assert math.isclose(tg.p_from_target(t10), 1.0 / 600000.0, rel_tol=1e-6)
    assert math.isclose(d10 / d1, 10.0, rel_tol=1e-6)          # D_10 = 10 * D_1
    assert math.isclose(t10 / t1, 0.1, rel_tol=1e-4)           # target_10 ~ target_1/10
    assert math.isclose(tg.expected_block_time(t10, 1000.0), 600.0, rel_tol=1e-6)
    ivs = []
    for seed in range(30):
        m, _, _ = simulate(_cfg(PROTO_POCOL, N=10, hardware=HW_H2,
                                mode=D2_SCALED, h2_rate=100.0,
                                seed=seed, sim=30000.0))
        if m["accepted_blocks"] >= 2:
            ivs.append(m["mean_block_interval_s"])
    mean = statistics.mean(ivs)
    assert abs(mean - 600.0) / 600.0 < 0.20, f"scaled interval {mean:.1f}s != ~600s"


def test_spec10_H1_difficulty_constant_in_N():
    """H1 (H_network fixed at 1000 c/s): difficulty/target identical for every N;
    W = 600000; increasing N only divides work allocation, never network speed."""
    ref = None
    for N in (1, 2, 5, 10, 100):
        cfg = DiffExpConfig(
            N=N, protocol=PROTO_POCOL, hardware=HW_H1,
            difficulty=DifficultyConfig(mode=D2_SCALED))
        # override the aggregate via reference: use h2-style small numbers by
        # scaling -- emulate H=1000 c/s with a custom config
        cfg = DiffExpConfig(
            N=N, protocol=PROTO_POCOL, hardware=HW_H2,
            difficulty=DifficultyConfig(mode=D2_SCALED,
                                        reference_hashrate_hps=1000.0),
            h2_miner_hashrate_hps=1000.0 / N)   # fixed aggregate = 1000 for every N
        t = initial_target(cfg)
        d = tg.difficulty_from_target(t)
        assert math.isclose(d, 600000.0, rel_tol=1e-9)     # W constant
        if ref is None:
            ref = t
        assert t == ref                                    # target identical
        assert math.isclose(tg.expected_block_time(t, 1000.0), 600.0, rel_tol=1e-9)
        assert math.isclose(difficulty_ratio_vs_reference(cfg), 1.0, rel_tol=1e-9)


# ===========================================================================
# D3 retargeting (invariants 15-18)
# ===========================================================================
def test_inv15_16_retarget_up_when_blocks_too_fast():
    from experiments.hashrate_aware_difficulty.retarget import Retargeter
    t0 = tg.target_for(1000.0, 600.0)
    rt = Retargeter(t0, window_blocks=10, t_target=600.0)
    # 10 accepted blocks in 3000 s (2x too fast) -> difficulty *2, target /2
    for i in range(10):
        rt.on_block((i + 1) * 300.0)
    assert len(rt.history) == 1                          # fired on the window, not per block
    _, old, adj, new = rt.history[0]
    assert math.isclose(adj, 2.0, rel_tol=1e-9)
    assert math.isclose(tg.difficulty_from_target(new) /
                        tg.difficulty_from_target(old), 2.0, rel_tol=1e-6)
    assert new < old                                     # target decreased


def test_inv17_retarget_down_when_blocks_too_slow():
    from experiments.hashrate_aware_difficulty.retarget import Retargeter
    t0 = tg.target_for(1000.0, 600.0)
    rt = Retargeter(t0, window_blocks=10, t_target=600.0)
    for i in range(10):
        rt.on_block((i + 1) * 1200.0)                    # 2x too slow
    _, old, adj, new = rt.history[0]
    assert math.isclose(adj, 0.5, rel_tol=1e-9)
    assert new > old                                     # target increased (easier)


def test_inv18_retarget_clamps():
    from experiments.hashrate_aware_difficulty.retarget import Retargeter
    t0 = tg.target_for(1000.0, 600.0)
    rt = Retargeter(t0, window_blocks=10, clamp_min=0.25, clamp_max=4.0)
    for i in range(10):
        rt.on_block((i + 1) * 1.0)                       # absurdly fast: raw = 600
    assert math.isclose(rt.history[0][2], 4.0)           # clamped up
    rt2 = Retargeter(t0, window_blocks=10, clamp_min=0.25, clamp_max=4.0)
    for i in range(10):
        rt2.on_block((i + 1) * 1e6)                      # absurdly slow
    assert math.isclose(rt2.history[0][2], 0.25)         # clamped down


def test_d3_end_to_end_converges_toward_600s():
    """Start 10x TOO EASY (initial_factor=0.1 -> fast blocks); retargeting must
    raise difficulty and push intervals toward 600 s."""
    from experiments.hashrate_aware_difficulty.retarget import Retargeter
    cfg = _cfg(PROTO_POCOL, N=10, hardware=HW_H2, mode=D3_RETARGET,
               h2_rate=100.0, seed=5, sim=60000.0, d3_initial_factor=0.1,
               d3_window_blocks=10)
    rt = Retargeter(initial_target(cfg), window_blocks=10, t_target=600.0)
    m, _, blocks = simulate(cfg, retargeter=rt)
    assert len(rt.history) >= 1                          # retargets happened
    d_first = blocks[0].difficulty
    d_last = blocks[-1].difficulty
    assert d_last > d_first * 1.5, "difficulty did not rise from a too-easy start"
    # late-run intervals near 600 s (use the last half of blocks)
    commits = [b.commit_time for b in blocks]
    late = [b - a for a, b in zip(commits, commits[1:])][len(commits) // 2:]
    mean_late = statistics.mean(late)
    assert 300.0 < mean_late < 1200.0, f"late intervals {mean_late:.0f}s not near 600s"


def _run_all():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for fn in fns:
        try:
            fn(); print(f"PASS  {fn.__name__}")
        except AssertionError as e:
            failed += 1; print(f"FAIL  {fn.__name__}: {e}")
        except Exception as e:
            failed += 1; print(f"ERROR {fn.__name__}: {type(e).__name__}: {e}")
    print(f"\n{len(fns)-failed}/{len(fns)} passed")
    return failed


if __name__ == "__main__":
    sys.exit(1 if _run_all() else 0)
