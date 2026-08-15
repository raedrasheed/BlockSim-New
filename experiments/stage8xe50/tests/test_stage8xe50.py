"""Stage 8X-E50 validation suite — the 20 required tests of brief section 34."""

import os
import random

import pytest

from experiments.stage8xe50.config.e50_config import (
    ACTIVE_FRACTIONS, ACTIVE_POWER_W, ARM_CONV, ARM_MT, ARMS,
    EFFICIENCY_J_PER_TH, HASHRATE_HPS, N_GRID, S_NONCE, T_RUN_S,
    active_count, difficulty, epoch_ticks_pc, is_slot_active, partition,
    q_per_candidate,
)
from experiments.stage8xe50.config.seeds import (
    pilot_seeds, primary_seeds, verify_disjoint,
)
from experiments.stage8xe50.src.engine_e50 import PCGeometry, run_one
from experiments.stage8xnr.src.noncedomain import union_measure

REPO = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))


# 1 — S21 Pro arithmetic
def test_t01_s21pro_arithmetic():
    assert HASHRATE_HPS == 234e12
    assert ACTIVE_POWER_W == 3510.0
    assert 234.0 * EFFICIENCY_J_PER_TH == ACTIVE_POWER_W


# 2 — 2^32 nonce domain
def test_t02_domain():
    assert S_NONCE == 2 ** 32
    for n in N_GRID:
        for s, e in partition(n):
            assert 0 <= s < e <= S_NONCE


# 3/4 — PoCol partition coverage and disjointness
@pytest.mark.parametrize("n", N_GRID)
def test_t03_t04_partition(n):
    rs = partition(n)
    assert rs[0][0] == 0 and rs[-1][1] == S_NONCE
    for (s1, e1), (s2, e2) in zip(rs, rs[1:]):
        assert e1 == s2                       # tiling => coverage + no overlap
    sizes = [e - s for s, e in rs]
    assert max(sizes) - min(sizes) <= 1


# 5 — MT same-template identity: within an epoch all miners share one template,
# so equal nonce values are exact duplicates (union < sum).
def test_t05_mt_common_template_identity():
    r = run_one(ARM_MT, 100, 42)
    assert r.rho_exact > 0.98                 # ~ (N-1)/N


# 6 — exact duplicate counting: MT rho == (N-1)/N up to truncation effects
@pytest.mark.parametrize("n", [100, 500])
def test_t06_exact_duplicate_counting(n):
    r = run_one(ARM_MT, n, 7)
    assert r.rho_exact == pytest.approx((n - 1) / n, abs=2e-4)


# 7 — unique coverage union arithmetic (toy check of the union function)
def test_t07_union():
    assert union_measure([(0, 10), (5, 10)], 100) == 15
    assert union_measure([(95, 10), (0, 5)], 100) == 10


# 8 — active-set size for every N and fraction
@pytest.mark.parametrize("n", N_GRID)
def test_t08_active_set_size(n):
    import math
    for arm, f in ACTIVE_FRACTIONS.items():
        assert active_count(n, arm) == math.ceil(f * n)
    assert active_count(n, ARM_MT) == n
    assert active_count(n, ARM_CONV) == n


# 9/10 — deterministic rotation and fairness over epochs
def test_t09_t10_rotation_fairness():
    n, k = 100, 10
    counts = [0] * n
    for e in range(n):                        # one full cycle
        act = [s for s in range(n) if is_slot_active(s, n, k, e)]
        assert len(act) == k
        for s in act:
            counts[s] += 1
    assert all(c == k for c in counts)        # exact fairness per cycle
    # deterministic: same epoch index -> same set
    assert ([s for s in range(n) if is_slot_active(s, n, k, 5)]
            == [s for s in range(n) if is_slot_active(s, n, k, 5)])
    g = PCGeometry(n, k)
    total = sum(g.window_sum(e) for e in range(n))
    assert total == k * S_NONCE               # cycle covers k full domains


# 11/12 — low-power energy identity and state-time conservation
@pytest.mark.parametrize("arm", ["E50-PC10", "E50-PC50", ARM_MT, ARM_CONV])
def test_t11_t12_energy_identities(arm):
    r = run_one(arm, 100, 11)
    assert r.identity_errors["state_time_conservation_rel"] < 1e-12
    assert r.identity_errors["work_identity_rel"] < 1e-12
    e = r.energy_j(0.25)
    expect = ACTIVE_POWER_W * (r.t_active_miner_s + 0.25 * r.t_low_miner_s)
    assert e == expect


# 13 — same target across scenarios at same N
@pytest.mark.parametrize("n", N_GRID)
def test_t13_same_target(n):
    qs = {arm: q_per_candidate(n) for arm in ARMS}
    assert len(set(qs.values())) == 1
    assert difficulty(n) * (2 ** 32) * q_per_candidate(n) == pytest.approx(1.0)


# 14 — same template-renewal rule MT vs PoCol: epoch ends when active miners
# complete their assignment => epoch ticks = assignment length in both arms.
def test_t14_matched_renewal():
    n = 100
    r_mt = run_one(ARM_MT, n, 3)
    ep_mt = T_RUN_S / r_mt.epochs_completed
    assert ep_mt == pytest.approx(S_NONCE / HASHRATE_HPS, rel=1e-6)
    r_pc = run_one("E50-PC100", n, 3)
    ep_pc = T_RUN_S / r_pc.epochs_completed
    assert ep_pc == pytest.approx(epoch_ticks_pc(n) / HASHRATE_HPS, rel=1e-6)


# 15 — zero exact duplication in PoCol
@pytest.mark.parametrize("arm", ["E50-PC10", "E50-PC50", "E50-PC100"])
def test_t15_pocol_zero_duplication(arm):
    r = run_one(arm, 100, 15)
    assert r.R_exact == 0 and r.rho_exact == 0.0


# 16 — analytical union coverage on toy domains
def test_t16_analytical_union_toy():
    rng = random.Random(16)
    S = 200
    for _ in range(100):
        starts = [rng.randrange(S) for _ in range(5)]
        L = rng.randrange(1, S)
        arcs = [(s, L) for s in starts]
        explicit = set()
        for s in starts:
            explicit |= {(s + i) % S for i in range(L)}
        assert union_measure(arcs, S) == len(explicit)


# 17 — domain saturation handling: MT unique coverage rate == h (one miner's
# worth) regardless of N; PC rate == k*h.
@pytest.mark.parametrize("n", [100, 500])
def test_t17_saturation(n):
    mt = run_one(ARM_MT, n, 17)
    assert mt.U_exact == pytest.approx(HASHRATE_HPS * T_RUN_S, rel=1e-6)
    pc = run_one("E50-PC20", n, 17)
    k = active_count(n, "E50-PC20")
    assert pc.U_exact == pytest.approx(k * HASHRATE_HPS * T_RUN_S, rel=1e-6)


# 18 — NA handling when zero blocks
def test_t18_na_handling():
    r = run_one(ARM_MT, 500, 18)              # MT500 almost surely 0 blocks
    if r.accepted_blocks == 0:
        assert r.intervals_s == []            # no fabricated intervals
    from experiments.stage8xe50.src.run_matrix import _median
    assert _median([]) == ""                  # NA propagates as empty


# 19 — paired seed reproducibility
def test_t19_reproducibility():
    a = run_one("E50-PC30", 100, 19)
    b = run_one("E50-PC30", 100, 19)
    assert (a.C_total, a.U_exact, a.accepted_blocks, a.intervals_s) == \
           (b.C_total, b.U_exact, b.accepted_blocks, b.intervals_s)
    c = run_one("E50-PC30", 100, 20)
    assert (a.C_total, a.accepted_blocks) != (c.C_total, c.accepted_blocks) \
        or a.intervals_s != c.intervals_s


# 20 — no change in physical trajectory when only alpha changes
def test_t20_alpha_accounting_only():
    r = run_one("E50-PC40", 100, 21)
    base = (r.C_total, r.U_exact, r.t_active_miner_s, r.t_low_miner_s,
            tuple(r.intervals_s))
    energies = [r.energy_j(a) for a in (0.0, 0.10, 0.25, 0.50)]
    after = (r.C_total, r.U_exact, r.t_active_miner_s, r.t_low_miner_s,
             tuple(r.intervals_s))
    assert base == after
    assert energies == sorted(energies)       # monotone in alpha


# seeds registry
def test_seeds_disjoint_and_frozen():
    assert len(primary_seeds()) == 30 and len(set(primary_seeds())) == 30
    assert len(pilot_seeds()) == 2
    rep = verify_disjoint(REPO)
    assert rep["disjoint"], rep
    assert any("stage8x_nr" in c for c in rep["checked_registries"])


# engine-level theory checks (predictions frozen in the theory report)
def test_theory_energy_saving_formula():
    n = 100
    mt = run_one(ARM_MT, n, 22)
    pc = run_one("E50-PC10", n, 22)
    k = pc.k_active
    saving = 1 - pc.energy_j(0.0) / mt.energy_j(0.0)
    assert saving == pytest.approx((1 - k / n), abs=1e-6)
    saving50 = 1 - pc.energy_j(0.5) / mt.energy_j(0.5)
    assert saving50 == pytest.approx((1 - k / n) * 0.5, abs=1e-6)


def test_theory_block_rates():
    # pooled over seeds, PC k=10 should out-produce MT by ~k
    n = 100
    mt_blocks = sum(run_one(ARM_MT, n, s).accepted_blocks for s in range(40, 70))
    pc_blocks = sum(run_one("E50-PC10", n, s).accepted_blocks
                    for s in range(40, 70))
    assert pc_blocks > mt_blocks              # strictly more useful throughput
