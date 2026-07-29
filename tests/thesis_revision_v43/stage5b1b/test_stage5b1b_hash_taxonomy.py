"""Stage 5B1B tests 11-20: corrected hash taxonomy."""

import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, ROOT)

from experiments.thesis_revision_v43 import hash_taxonomy as ht
from experiments.thesis_revision_v43 import build_matrix_5b1b as b

DEP = "6e211ea7c031a3fab560843690e27e5a3c2aa2a8c363ab483369a2babc8157be"


def _cfg(scen="B3_C1_CONTINUOUS_DISJOINT", **over):
    base = dict(scenario_id=scen, seed=20260201, miner_count=100, mu=2.0,
                hash_rate_distribution="homogeneous", allocation_policy="disjoint_equal",
                inactive_miner_fraction=0.0, propagation_delay_mean_s=0.42,
                idle_power_ratio=0.0, network_hash_rate_hps=141e12, efficiency_j_per_th=21.5,
                simulation_duration_s=10000.0, target_block_interval_s=600.0,
                block_size_bytes=1_000_000, interpretation_labels="B3;C1",
                hypothesis_id="H1;A1", matrix_class="CORE")
    base.update(over)
    return base


# 11
def test_scientific_semantics_hash_excludes_seed():
    a = _cfg(seed=1)
    b_ = _cfg(seed=2)
    assert ht.scientific_semantics_hash(a) == ht.scientific_semantics_hash(b_)


# 12
def test_run_execution_hash_includes_seed():
    a = _cfg(seed=1)
    b_ = _cfg(seed=2)
    assert ht.run_execution_hash(a, DEP) != ht.run_execution_hash(b_, DEP)


# 13
def test_interpretation_hash_does_not_create_physical_run():
    a = _cfg(interpretation_labels="B3")
    b_ = _cfg(interpretation_labels="C1")
    # different interpretation, SAME physical run
    assert ht.interpretation_hash(a) != ht.interpretation_hash(b_)
    assert ht.run_execution_hash(a, DEP) == ht.run_execution_hash(b_, DEP)


# 14
def test_analysis_group_hash_documented():
    # analysis group differs from scientific semantics: it keys on hypothesis/class
    a = _cfg(hypothesis_id="H1;A1", matrix_class="CORE")
    b_ = _cfg(hypothesis_id="OTHER", matrix_class="CORE")
    assert ht.analysis_group_hash(a) != ht.analysis_group_hash(b_)
    assert ht.scientific_semantics_hash(a) == ht.scientific_semantics_hash(b_)   # semantics ignore hypothesis


# 15
def test_same_semantics_different_seeds_group_together():
    final, _, _ = b.build()
    from collections import Counter
    groups = Counter(r["scientific_semantics_hash"] for r in final)
    assert all(c == 30 for c in groups.values())


# 16
def test_same_seed_same_semantics_unique():
    final, _, _ = b.build()
    pairs = [(r["scientific_semantics_hash"], r["seed"]) for r in final]
    assert len(pairs) == len(set(pairs))


# 17
def test_b3_c1_share_run_execution_hash():
    a = _cfg(interpretation_labels="B3")
    b_ = _cfg(interpretation_labels="C1")
    assert ht.run_execution_hash(a, DEP) == ht.run_execution_hash(b_, DEP)


# 18
def test_expected_semantics_group_sizes():
    final, _, _ = b.build()
    sci = {r["scientific_semantics_hash"] for r in final}
    assert len(sci) == 63                               # 63 scientific configs x 30 seeds = 1890


# 19
def test_no_duplicate_run_execution_hash():
    final, _, _ = b.build()
    run = [r["run_execution_hash"] for r in final]
    assert len(run) == len(set(run)) == 1890


# 20
def test_hashes_reproducible():
    a = _cfg()
    assert ht.scientific_semantics_hash(a) == ht.scientific_semantics_hash(_cfg())
    assert ht.run_execution_hash(a, DEP) == ht.run_execution_hash(_cfg(), DEP)
    assert ht.interpretation_hash(a) == ht.interpretation_hash(_cfg())
    assert ht.analysis_group_hash(a) == ht.analysis_group_hash(_cfg())
