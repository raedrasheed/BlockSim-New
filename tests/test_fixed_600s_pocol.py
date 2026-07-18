"""Fixed 600-second round experiment — deterministic invariants (spec §16).

Covers invariants 1-22, 25, 27 (stochastic invariants 22-26 are additionally
exercised in tests/test_fixed_600s_stochastic.py). Includes the exact §12
M=100/N=10 example and the §13 multi-round (100-block) example.

Run:  python -m pytest tests/test_fixed_600s_pocol.py -v
  or:  python tests/test_fixed_600s_pocol.py
"""
import os
import sys
import math
import subprocess

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

from experiments.fixed_600s_pocol.configuration import (
    FixedRoundConfig, PowerConfig, PROTO_DUP, PROTO_IND, PROTO_POCOL,
    HW_H1, HW_H2, AGG_ACTIVE_POWER_W,
)
from experiments.fixed_600s_pocol.nonce_partition import (
    partition_nonce_domain, range_size, ranges_are_disjoint, ranges_cover,
)
from experiments.fixed_600s_pocol.round_state import simulate, TemplateOutcome, run_round
from experiments.fixed_600s_pocol import pow_duplicate, pow_independent, pocol_disjoint
from experiments.fixed_600s_pocol.miner_state import build_miners, IDLE

PROVIDER = {
    PROTO_DUP: pow_duplicate.deterministic_provider,
    PROTO_IND: pow_independent.deterministic_provider,
    PROTO_POCOL: pocol_disjoint.deterministic_provider,
}


def _cfg(protocol, N=10, M=100, r=1.0, sim=600.0, q=0.0, placement="last", **kw):
    return FixedRoundConfig(
        N=N, protocol=protocol, hardware=HW_H2, M=M, h2_hashrate_hps=r,
        sim_seconds=sim, placement=placement,
        power=PowerConfig(idle_ratio=q), **kw)


def _run(cfg):
    return simulate(cfg, PROVIDER[cfg.protocol](cfg))


# ===========================================================================
# Invariants 1-3: partitioning
# ===========================================================================
def test_inv1_2_3_partition_disjoint_exhaustive_unique():
    for M, N in [(100, 10), (100, 7), (3, 10), (2**32, 500), (1000, 1)]:
        rg = partition_nonce_domain(0, M, N)
        assert ranges_are_disjoint(rg)                         # 1
        assert ranges_cover(rg, 0, M)                          # 2
        assert sum(range_size(x) for x in rg) == M             # 3: no nonce twice


# ===========================================================================
# Invariant 4: every miner scans only its assigned range
# ===========================================================================
def test_inv4_miner_never_leaves_its_range():
    for placement in ("first", "p25", "middle", "p75", "last"):
        cfg = _cfg(PROTO_POCOL, placement=placement)
        _, miners, _ = _run(cfg)
        rg = partition_nonce_domain(0, 100, 10)
        for m, r in zip(miners, rg):
            assert m.evaluated_candidates <= range_size(r), \
                f"miner {m.miner_id} evaluated beyond its range"


# ===========================================================================
# Invariants 5-11: the section-4 timing example (individual + global stopping)
# ===========================================================================
def _spec4_provider(cfg, rid, tidx):
    sizes = [40, 45, 100] + [100] * 7
    ls = [None, None, 70] + [None] * 7
    nv = [None, None, 9999] + [None] * 7
    return TemplateOutcome("T-spec4", sizes, ls, nv)


def _spec4_run():
    cfg = _cfg(PROTO_POCOL, M=1000)
    return cfg, *simulate(cfg, _spec4_provider)


def test_inv5_idle_immediately_after_exhaustion():
    _, _, miners, _ = _spec4_run()
    assert math.isclose(miners[0].active_time_s, 40.0)   # not 70, not 600
    assert math.isclose(miners[1].active_time_s, 45.0)


def test_inv6_others_continue_after_one_exhausts():
    _, _, miners, _ = _spec4_run()
    assert miners[2].active_time_s > miners[0].active_time_s
    assert math.isclose(miners[2].active_time_s, 70.0)


def test_inv7_8_9_global_stop_no_hashes_no_active_energy_after_discovery():
    cfg, metrics, miners, rounds = _spec4_run()
    t_disc = rounds[0].discovery_time
    assert math.isclose(t_disc, 70.0)
    for m in miners:
        assert m.active_time_s <= t_disc + 1e-9                        # 7
        assert math.isclose(m.cumulative_hashes, m.hashrate_hps * m.active_time_s)  # 8
        assert math.isclose(m.cumulative_energy_j, m.active_power_w * m.active_time_s)  # 9 (q=0)


def test_inv10_11_idle_to_boundary_next_round_at_boundary():
    cfg = _cfg(PROTO_POCOL, sim=1800.0)                 # 3 rounds
    metrics, miners, rounds = _run(cfg)
    for m in miners:
        assert math.isclose(m.total_state_time_s, 1800.0)              # 10 accounted
    for i, r in enumerate(rounds):
        assert math.isclose(r.round_start, i * 600.0)                  # 11 exact boundary
        assert math.isclose(r.commit_time, r.round_start + 600.0)


# ===========================================================================
# Invariants 12-15: one block/round, equal counts, 600s interval, equal throughput
# ===========================================================================
def test_inv12_13_14_15_block_rate_and_throughput_equality():
    ms = {}
    for proto in (PROTO_DUP, PROTO_IND, PROTO_POCOL):
        cfg = _cfg(proto, sim=10200.0)
        m, _, rounds = _run(cfg)
        assert m["accepted_blocks"] == cfg.n_rounds() == 17            # 12
        assert all(r.committed for r in rounds)
        assert math.isclose(m["accepted_block_interval_s"], 600.0)     # 14
        ms[proto] = m
    assert ms[PROTO_DUP]["accepted_blocks"] == ms[PROTO_POCOL]["accepted_blocks"]  # 13
    assert math.isclose(ms[PROTO_DUP]["throughput_tx_per_s"],
                        ms[PROTO_POCOL]["throughput_tx_per_s"])        # 15
    assert math.isclose(ms[PROTO_IND]["throughput_tx_per_s"],
                        ms[PROTO_POCOL]["throughput_tx_per_s"])


# ===========================================================================
# Invariants 16-17: energy integral + state-time conservation
# ===========================================================================
def test_inv16_17_energy_integral_and_state_time():
    for proto in (PROTO_DUP, PROTO_IND, PROTO_POCOL):
        for q in (0.0, 0.2, 1.0):
            cfg = _cfg(proto, sim=1800.0, q=q)
            _, miners, _ = _run(cfg)
            for m in miners:
                e = (m.active_power_w * m.active_time_s
                     + m.idle_power_w * m.idle_time_s
                     + m.sleep_power_w * m.sleep_time_s)
                assert math.isclose(m.cumulative_energy_j, e, rel_tol=1e-9)   # 16
                assert math.isclose(m.total_state_time_s, 1800.0, abs_tol=1e-6)  # 17


# ===========================================================================
# Invariants 18-21: savings behaviour
# ===========================================================================
def test_inv18_single_miner_no_partitioning_saving():
    a, _, _ = _run(_cfg(PROTO_DUP, N=1, M=100))
    b, _, _ = _run(_cfg(PROTO_POCOL, N=1, M=100))
    assert math.isclose(a["total_energy_j"], b["total_energy_j"])
    assert a["total_attempts"] == b["total_attempts"] == 100


def test_inv19_spec12_exact_90pct_saving():
    """The required §12 example, all expectations exact."""
    cfg_a = _cfg(PROTO_DUP)
    cfg_b = _cfg(PROTO_POCOL)
    a, ma, ra = _run(cfg_a)
    b, mb, rb = _run(cfg_b)
    assert a["total_attempts"] == 1000 and b["total_attempts"] == 100
    assert math.isclose(ra[0].discovery_time, 100.0)
    assert math.isclose(rb[0].discovery_time, 10.0)
    assert rb[0].winner_id == 9 and rb[0].winning_nonce == 99
    assert math.isclose(a["active_miner_seconds"], 1000.0)
    assert math.isclose(b["active_miner_seconds"], 100.0)
    assert math.isclose(b["total_energy_j"] / a["total_energy_j"], 0.1)     # ratio 0.1
    assert a["accepted_blocks"] == b["accepted_blocks"] == 1
    assert math.isclose(a["accepted_block_interval_s"], 600.0)
    assert math.isclose(b["accepted_block_interval_s"], 600.0)
    assert math.isclose(a["throughput_tx_per_s"], b["throughput_tx_per_s"])
    # per-miner: every PoCol miner did at most 10 attempts, idle from t=10
    for m in mb:
        assert m.evaluated_candidates <= 10
        assert math.isclose(m.active_time_s, 10.0)


def test_inv20_idle_ratio_one_zero_saving():
    a, _, _ = _run(_cfg(PROTO_DUP, q=1.0))
    b, _, _ = _run(_cfg(PROTO_POCOL, q=1.0))
    assert math.isclose(a["total_energy_j"], b["total_energy_j"])


def test_inv21_idle_zero_is_idealized_upper_bound():
    """q=0 gives the maximum saving; every q>0 saves strictly less."""
    prev = None
    for q in (0.0, 0.05, 0.2, 0.5, 1.0):
        a, _, _ = _run(_cfg(PROTO_DUP, q=q))
        b, _, _ = _run(_cfg(PROTO_POCOL, q=q))
        red = 1 - b["total_energy_j"] / a["total_energy_j"]
        if prev is not None:
            assert red < prev + 1e-12, "saving must shrink as idle power grows"
        prev = red


# ===========================================================================
# Invariant 22 (deterministic form): later nonce discovered earlier
# ===========================================================================
def test_inv22_later_nonce_earlier_local_discovery():
    cfg = _cfg(PROTO_POCOL, explicit_nonces=(55, 90))
    _, _, rounds = _run(cfg)
    assert rounds[0].winning_nonce == 90          # numerically later
    assert math.isclose(rounds[0].discovery_time, 1.0)   # ...but locally first


# ===========================================================================
# Invariant 25 (deterministic reproducibility) + §13 multi-round example
# ===========================================================================
def test_inv25_deterministic_reproducibility():
    m1, _, _ = _run(_cfg(PROTO_POCOL, sim=10200.0))
    m2, _, _ = _run(_cfg(PROTO_POCOL, sim=10200.0))
    assert m1 == m2


def test_spec13_multi_round_100_blocks():
    for proto in (PROTO_DUP, PROTO_POCOL):
        m, _, rounds = _run(_cfg(proto, sim=60000.0))
        assert m["accepted_blocks"] == 100
        assert math.isclose(m["accepted_block_interval_s"], 600.0)
    a, _, _ = _run(_cfg(PROTO_DUP, sim=60000.0))
    b, _, _ = _run(_cfg(PROTO_POCOL, sim=60000.0))
    assert math.isclose(a["throughput_tx_per_s"], b["throughput_tx_per_s"])


# ===========================================================================
# H1 spot check: calibrated M -> DUP worst case fills the whole slot
# ===========================================================================
def test_h1_calibration_and_ratio():
    a, _, ra = _run(FixedRoundConfig(N=100, protocol=PROTO_DUP, hardware=HW_H1,
                                     sim_seconds=600.0, placement="last"))
    b, _, rb = _run(FixedRoundConfig(N=100, protocol=PROTO_POCOL, hardware=HW_H1,
                                     sim_seconds=600.0, placement="last"))
    assert math.isclose(ra[0].discovery_time, 600.0, rel_tol=1e-6)   # full slot
    assert rb[0].discovery_time <= 600.0 / 100 + 1e-6                # <= slot/N
    assert math.isclose(b["total_energy_j"] / a["total_energy_j"], 0.01, rel_tol=1e-6)
    assert math.isclose(a["total_energy_j"],
                        AGG_ACTIVE_POWER_W * 600.0, rel_tol=1e-6)    # full-power slot


# ===========================================================================
# Invariant 27: protected result directories byte-identical
# ===========================================================================
def test_inv27_protected_results_unchanged():
    protected = ["results/corrected", "results/nonce_partition_worst_case",
                 "results/continuous_distributed_effort", "results/mainsim_idle_after_range"]
    r = subprocess.run(["git", "status", "--porcelain", "--"] + protected,
                       capture_output=True, text=True, cwd=ROOT)
    assert r.stdout.strip() == "", f"protected results modified:\n{r.stdout}"
    r2 = subprocess.run(["git", "diff", "--quiet", "HEAD", "--"] + protected, cwd=ROOT)
    assert r2.returncode == 0, "protected results differ from HEAD"


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
