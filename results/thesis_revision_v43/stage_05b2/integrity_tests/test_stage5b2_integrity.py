"""Stage 5B2 data-integrity tests — run against the AGGREGATED outputs after
execution (not part of the frozen scientific `tests/` suite). Verifies group
structure, hash uniqueness, B3/C1 sharing, per-run energy/candidate reconciliation,
delay-only primary invariance, zero-block retention, and NA policy."""

import os
import sys
import csv
import gzip
import json
import math
import collections

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.abspath(os.path.join(HERE, ".."))
ROOT = os.path.abspath(os.path.join(OUT, "..", "..", ".."))
MATRIX = os.path.join(ROOT, "docs", "thesis_revision_v43", "STAGE_05B1G1_FINAL_MATRIX.csv")
CONTINUOUS = {"B0", "B1", "B2", "B3_C1_CONTINUOUS_DISJOINT"}

_matrix = list(csv.DictReader(open(MATRIX)))
_by_id = {r["run_id"]: r for r in _matrix}


def _summaries():
    out = {}
    with gzip.open(os.path.join(OUT, "summary", "summary.jsonl.gz"), "rt") as f:
        for line in f:
            r = json.loads(line)
            out[r["run_id"]] = r
    return out


S = _summaries()


def test_all_1890_present_and_unique():
    assert len(S) == 1890
    assert set(S) == set(_by_id)


def test_groups_63_x_30():
    g = collections.defaultdict(set)
    for rid, row in _by_id.items():
        g[row["scientific_semantics_hash"]].add(row["seed"])
    assert len(g) == 63
    assert all(len(v) == 30 for v in g.values())


def test_unique_run_execution_hashes():
    rex = [row["run_execution_hash"] for row in _by_id.values()]
    assert len(set(rex)) == 1890


def test_no_same_seed_scientific_duplicate():
    c = collections.Counter((row["scientific_semantics_hash"], row["seed"]) for row in _by_id.values())
    assert all(v == 1 for v in c.values())


def test_b3c1_share_one_physical_run():
    dual = [rid for rid, row in _by_id.items() if row["interpretation_labels"] == "B3;C1"]
    assert len(dual) == 870
    assert all(rid in S for rid in dual)


def test_energy_reconciliation_and_anchor():
    for rid, r in S.items():
        row = _by_id[rid]
        assert math.isclose(r["total_energy_kwh"],
                            r["active_energy_kwh"] + r["idle_energy_kwh"] + r["coordination_energy_kwh"],
                            abs_tol=1e-9)
        if row["scenario_id"] != "C2" and float(row["inactive_miner_fraction"]) == 0.0:
            exp = (float(row["network_hash_rate_hps"]) * float(row["efficiency_j_per_th"]) / 1e12
                   * float(row["simulation_duration_s"])) / 3_600_000.0
            assert math.isclose(r["total_energy_kwh"], exp, rel_tol=1e-9)


def test_candidate_reconciliation():
    for r in S.values():
        assert r["total_candidate_evaluations"] == r["distinct_candidate_identities"] + r["duplicate_evaluations"]


def test_delay_only_primary_invariance():
    prim = ["total_energy_kwh", "total_candidate_evaluations", "distinct_candidate_identities",
            "duplicate_evaluations", "accepted_blocks", "effective_block_interval_s",
            "total_active_time_s", "total_idle_time_s"]
    delay_rows = [row for row in _matrix if row["matrix_class"] == "SENS_DELAY"]
    by_key = collections.defaultdict(dict)
    for row in delay_rows:
        by_key[(row["miner_count"], row["seed"])][row["propagation_delay_mean_s"]] = row["run_id"]
    for key, dmap in by_key.items():
        rids = list(dmap.values())
        base = S[rids[0]]
        for rid in rids[1:]:
            for f in prim:
                a, b = base.get(f), S[rid].get(f)
                if a is None and b is None:
                    continue
                if isinstance(a, float):
                    assert math.isclose(a, b, rel_tol=1e-12, abs_tol=1e-12), (key, f, a, b)
                else:
                    assert a == b, (key, f, a, b)


def test_zero_block_runs_retained_with_na():
    zero = [r for r in S.values() if r["accepted_blocks"] == 0]
    assert zero  # B1 large-N rows produce zero blocks within the horizon
    for r in zero:
        assert r["effective_block_interval_s"] is None
        assert r["energy_per_accepted_block_kwh"] is None
        assert r["single_height_stales_per_accepted_block"] is None
        assert r["effective_block_interval_na_reason"] == "no_accepted_blocks"


def test_disjoint_zero_duplicate():
    for rid, r in S.items():
        if _by_id[rid]["scenario_id"] in ("B0", "B3_C1_CONTINUOUS_DISJOINT", "C2"):
            assert r["duplicate_evaluations"] == 0
