"""Stage 5B1A tests 9-15: B1 zero-block analytical model and NA policy."""

import os
import sys
import math

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, ROOT)

from experiments.thesis_revision_v43 import b1_zero_block as zb
from experiments.thesis_revision_v43.scenario_engine import EngineConfig, run_scenario


# 9
def test_b1_unique_rate_homogeneous():
    rates = [10.0] * 5
    assert zb.h_unique(rates, homogeneous=True) == 10.0        # == H_total / N
    assert math.isclose(zb.h_unique(rates, True) * 5, sum(rates))


# 10
def test_b1_unique_rate_heterogeneous():
    rates = [1.0, 5.0, 2.0, 9.0, 3.0]
    assert zb.h_unique(rates, homogeneous=False) == 9.0        # == max_i H_i


# 11
def test_b1_zero_block_probability():
    table = zb.b1_table()
    assert [r["miner_count"] for r in table] == [100, 200, 300, 400, 500]
    p0 = [r["zero_block_probability"] for r in table]
    assert all(0.5 < x < 1.0 for x in p0)                      # majority-zero, well-defined
    assert all(p0[i] < p0[i + 1] for i in range(len(p0) - 1))  # increasing in N
    # closed form P0 == exp(-p*H_unique*T)
    r = table[0]
    assert math.isclose(r["zero_block_probability"], math.exp(-r["expected_accepted_blocks"]), rel_tol=1e-12)


# 12
def test_b1_seeded_zero_block_frequency_matches_reference():
    # Stage 5B1B: no arbitrary tolerance. The EXACT P0 must lie inside the event-loop
    # 99% Clopper-Pearson interval (validation seeds, disjoint from the frozen schedule).
    from experiments.thesis_revision_v43 import b1_exact as bx
    seeds = [20261001 + i for i in range(12)]
    for N in (100, 500):
        zeros = sum(1 for s in seeds
                    if run_scenario(EngineConfig("B1", seed=s, miner_count=N))["accepted_blocks"] == 0)
        p0 = bx.exact_zero_block(141e12, N, 10000.0, 600.0, 2.0)["expected_zero_block_probability_exact"]
        lo, hi = bx.clopper_pearson(zeros, len(seeds), 0.01)
        assert lo <= p0 <= hi, (N, zeros, p0, lo, hi)


# 13
def test_zero_block_metrics_are_na():
    # find a zero-block B1 run (N=500 is very_high risk)
    r = run_scenario(EngineConfig("B1", seed=20260201, miner_count=500))
    assert r["accepted_blocks"] == 0
    assert r["energy_per_accepted_block_kwh"] is None
    assert r["energy_per_accepted_block_na_reason"] == "no_accepted_blocks"
    assert r["effective_block_interval_s"] is None
    assert r["confirmation_time_proxy_s"] is None
    assert r["legitimate_stale_rate"] is None
    # NOT encoded as 0 / inf / large constant
    for k in ("energy_per_accepted_block_kwh", "effective_block_interval_s"):
        assert r[k] is None
    # throughput numerator genuinely zero -> 0.0 is a real value, not NA
    assert r["throughput_blocks_per_s"] == 0.0


# 14
def test_zero_block_run_not_excluded():
    # a zero-block run still reports accepted_blocks and participates in summaries
    r = run_scenario(EngineConfig("B1", seed=20260201, miner_count=500))
    assert "accepted_blocks" in r and r["accepted_blocks"] == 0
    assert r["block_metrics_defined"] is False
    assert math.isclose(r["total_energy_kwh"], 8.420833333333333, rel_tol=1e-9)  # energy still counted


# 15
def test_ratio_of_totals_separate_from_conditional_mean():
    seeds = [20260201 + i for i in range(12)]
    runs = [run_scenario(EngineConfig("B1", seed=s, miner_count=100)) for s in seeds]
    tot_e = sum(r["total_energy_kwh"] for r in runs)
    tot_b = sum(r["accepted_blocks"] for r in runs)
    ratio_of_totals = tot_e / tot_b
    cond = [r["energy_per_accepted_block_kwh"] for r in runs if r["accepted_blocks"] > 0]
    cond_mean = sum(cond) / len(cond)
    # both defined and they are DIFFERENT estimands
    assert ratio_of_totals > 0 and cond_mean > 0
    assert not math.isclose(ratio_of_totals, cond_mean, rel_tol=1e-6) or len(cond) == len(runs)
    # undefined runs are counted, not dropped silently
    assert len(runs) - len(cond) == sum(1 for r in runs if r["accepted_blocks"] == 0)
