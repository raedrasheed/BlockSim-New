#!/usr/bin/env python3
"""Stage 6 — data-validation and reproducibility tests.

Run with: python3 -m pytest analysis/thesis_revision_v43/stage_06/tests -q
These verify the analysis population, field-authority compliance, determinism of the
inferential procedures, and that no scientific result was altered.
"""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

import s6_common as C  # noqa: E402
import s6_stats as S  # noqa: E402

RUNS = C.load_runs()


def test_population_1890():
    assert len(RUNS) == 1890


def test_63_groups_30_seeds():
    from collections import Counter
    g = Counter(r["scientific_semantics_hash"] for r in RUNS)
    assert len(g) == 63
    assert set(g.values()) == {30}


def test_no_same_seed_duplicate_within_group():
    from collections import defaultdict
    gs = defaultdict(list)
    for r in RUNS:
        gs[r["scientific_semantics_hash"]].append(r["seed"])
    for ss in gs.values():
        assert len(set(ss)) == len(ss)


def test_b3c1_single_dataset_not_doubled():
    b = [r for r in RUNS if r["scenario_id"] == "B3_C1_CONTINUOUS_DISJOINT"]
    assert len(b) == 870
    assert {r["interpretation_labels"] for r in b} == {"B3;C1"}
    assert len({r["run_execution_hash"] for r in b}) == 870


def test_zero_block_retained_142():
    assert sum(1 for r in RUNS if r["accepted_blocks"] == 0) == 142


def test_a1_energy_invariant_within_tolerance():
    cont = [r for r in RUNS if r["scenario_id"] != "C2"
            and r["inactive_fraction"] == 0.0 and r["idle_policy"] is False]
    dev = max(abs(r["total_energy_kwh"] - C.CONTINUOUS_ENERGY_ANCHOR_KWH) for r in cont)
    assert dev / C.CONTINUOUS_ENERGY_ANCHOR_KWH < 1e-6


def test_h1_duplicate_ordering_direction():
    def rate(sc):
        return np.mean([r["duplicate_evaluation_rate"] for r in RUNS
                        if r["hypothesis_id"] == "H1;A1" and r["scenario_id"] == sc])
    assert rate("B1") > rate("B2") > rate("B3_C1_CONTINUOUS_DISJOINT")


def test_h7_primary_invariance_across_delay():
    b = json.load(open(os.path.join(C.STAGE6, "diagnostics", "h7_secondary.json")))
    for outcome, d in b["primary_invariance_across_delay"].items():
        assert d["invariant"] is True, outcome


def test_forbidden_fields_not_in_descriptive_outcomes():
    import s6_analysis
    for o in s6_analysis.DESC_OUTCOMES:
        assert o not in C.FORBIDDEN_FIELDS, o


def test_permutation_deterministic():
    rng_diff = np.array([0.1, -0.2, 0.3, 0.0, 0.5, -0.1, 0.2, 0.4])
    p1, _ = S.paired_permutation_p(rng_diff, seed=C.RNG_SEED_PERMUTATION, n_perm=5000)
    p2, _ = S.paired_permutation_p(rng_diff, seed=C.RNG_SEED_PERMUTATION, n_perm=5000)
    assert p1 == p2


def test_bootstrap_deterministic():
    x = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0])
    a1 = S.bootstrap_ci_paired(x, seed=C.RNG_SEED_BOOTSTRAP)
    a2 = S.bootstrap_ci_paired(x, seed=C.RNG_SEED_BOOTSTRAP)
    assert a1 == a2


def test_holm_monotone_and_bounded():
    out = S.holm([("a", 0.01), ("b", 0.04), ("c", 0.03)])
    for o in out:
        assert 0.0 <= o["p_holm"] <= 1.0
        assert o["p_holm"] >= o["p_raw"]


def test_wilson_and_rule_of_three():
    lo, hi = S.wilson_ci(5, 100)
    assert 0 <= lo < 0.05 < hi <= 1
    assert abs(S.rule_of_three(300) - 0.01) < 1e-12


def test_deterministic_contrast_flagged():
    # B1 vs B3/C1 duplicate rate at fixed N is deterministic (constant per config)
    a = np.array([0.0] * 30)
    b = np.array([0.99] * 30)
    p, det = S.paired_permutation_p(b - a, seed=1)
    assert det is True and p is None
