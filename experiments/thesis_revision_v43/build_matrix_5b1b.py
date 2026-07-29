"""Stage 5B1B: regenerate the matrix with the corrected hash taxonomy (scientific
semantics separated from stochastic run identity), exact B1 zero-block fields, and
all named stream seeds. Preserves every earlier matrix. Does NOT execute the matrix.
"""

from __future__ import annotations
import os
import csv
import json
import math
import hashlib

import mpmath as mp

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DOCS = os.path.join(ROOT, "docs", "thesis_revision_v43")
RAW = os.path.join(ROOT, "results", "thesis_revision_v43", "stage_05b1b", "raw")

from experiments.thesis_revision_v43 import build_matrix_5b1 as base
from experiments.thesis_revision_v43 import hash_taxonomy as ht
from experiments.thesis_revision_v43 import b1_exact as bx
from experiments.thesis_revision_v43 import b1_zero_block as zb
from experiments.thesis_revision_v43 import retention_5b1a
from experiments.thesis_revision_v43.schemas import OUTPUT_SCHEMA_VERSION
from experiments.thesis_revision_v43.scenario_engine import ENGINE_VERSION, derive_stream_seeds

mp.mp.dps = 50
LOCK = os.path.join(ROOT, "requirements-thesis-v43-lock.txt")


def _sha_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for c in iter(lambda: f.read(1 << 16), b""):
            h.update(c)
    return h.hexdigest()


DEP_LOCK_SHA = _sha_file(LOCK)


def exact_zero_fields(row):
    scen = row["scenario_id"]
    N = int(row["miner_count"])
    frac = float(row.get("inactive_miner_fraction", 0.0) or 0.0)
    mu = float(row["mu"])
    H = float(row["network_hash_rate_hps"])
    T = float(row["simulation_duration_s"])
    tgt = float(row["target_block_interval_s"])
    if scen == "B2":
        return dict(expected_zero_block_probability_exact=None,
                    expected_zero_block_probability_poisson=None,
                    expected_unique_candidate_evaluations=None,
                    expected_full_template_generations=None,
                    expected_partial_generation_candidates=None,
                    zero_block_risk_category="unmodeled",
                    analytical_model_version="b1-exact-1")
    if scen == "B1":
        ex = bx.exact_zero_block(H, N, T, tgt, mu)                 # unique_rate = H/N
    else:
        H_active = H * (1.0 - frac)
        ex = bx.exact_zero_block(H, N, T, tgt, mu, hetero_rates=[H_active])
    p0 = ex["expected_zero_block_probability_exact"]
    return dict(
        expected_zero_block_probability_exact=p0,
        expected_zero_block_probability_poisson=ex["expected_zero_block_probability_poisson"],
        expected_unique_candidate_evaluations=ex["expected_unique_candidate_evaluations"],
        expected_full_template_generations=ex["expected_full_template_generations"],
        expected_partial_generation_candidates=ex["expected_partial_generation_candidates"],
        zero_block_risk_category=zb.risk_category(p0),
        analytical_model_version=ex["analytical_model_version"])


def build():
    final, stats = base.dedup()
    for r in final:
        r.update(exact_zero_fields(r))
        r["scientific_semantics_hash"] = ht.scientific_semantics_hash(r)
        r["run_execution_hash"] = ht.run_execution_hash(r, DEP_LOCK_SHA)
        r["interpretation_hash"] = ht.interpretation_hash(r)
        r["analysis_group_hash_v2"] = ht.analysis_group_hash(r)
        r["master_seed"] = r["seed"]
        r["output_schema_version"] = OUTPUT_SCHEMA_VERSION
        r["scenario_engine_version"] = ENGINE_VERSION
        for name, val in derive_stream_seeds(int(r["seed"])).items():
            r[f"stream_seed_{name}"] = val
    final, retention = retention_5b1a.design_retention(final)
    return final, stats, retention


STREAM_COLS = [f"stream_seed_{n}" for n in derive_stream_seeds(0).keys()]
FIELDS = (["run_id", "scenario_id", "interpretation_labels", "reused_by_hypotheses",
           "hypothesis_id", "matrix_class", "master_seed", "seed", "miner_count",
           "underlying_execution_model", "network_hash_rate_hps", "efficiency_j_per_th",
           "simulation_duration_s", "target_block_interval_s", "propagation_delay_mean_s",
           "hash_rate_distribution", "mu", "inactive_miner_fraction", "idle_power_ratio",
           "allocation_policy", "expected_zero_block_probability_exact",
           "expected_zero_block_probability_poisson", "expected_unique_candidate_evaluations",
           "expected_full_template_generations", "expected_partial_generation_candidates",
           "zero_block_risk_category", "analytical_model_version",
           "scientific_semantics_hash", "run_execution_hash", "interpretation_hash",
           "analysis_group_hash_v2", "output_schema_version", "scenario_engine_version"]
          + STREAM_COLS +
          ["retention_full_log", "retention_reason_codes", "validation_only",
           "expected_output_path", "planned_status"])


def audit(final):
    from collections import Counter
    sci = Counter(r["scientific_semantics_hash"] for r in final)
    run = Counter(r["run_execution_hash"] for r in final)
    same_seed = Counter((r["scientific_semantics_hash"], r["seed"]) for r in final)
    dual = [r for r in final if ";" in r["interpretation_labels"]]
    return dict(
        rows=len(final),
        distinct_scientific_semantics=len(sci),
        distinct_run_execution=len(run),
        distinct_interpretation=len({r["interpretation_hash"] for r in final}),
        distinct_analysis_group=len({r["analysis_group_hash_v2"] for r in final}),
        semantics_group_size_distribution=dict(Counter(sci.values())),
        groups_not_30=[h for h, c in sci.items() if c != 30],
        duplicate_run_execution_hashes=[h for h, c in run.items() if c > 1],
        duplicate_same_seed_semantics=[k for k, c in same_seed.items() if c > 1],
        b3_c1_dual_rows=len(dual))


def write(final, stats, retention):
    os.makedirs(DOCS, exist_ok=True)
    os.makedirs(RAW, exist_ok=True)
    matrix = os.path.join(DOCS, "STAGE_05B1B_FINAL_MATRIX.csv")
    with open(matrix, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader()
        for r in final:
            r.setdefault("expected_output_path",
                         f"results/thesis_revision_v43/stage_05b2/raw/{r['run_id']}.summary.json")
            r.setdefault("planned_status", "PLANNED")
            w.writerow(r)
    aud = audit(final)
    seed_sched = dict(seed_base=base.SEED_BASE, n_seeds=30, seeds=base.SEEDS)
    summary = dict(
        final_stage5b2_run_count=len(final), ceiling=3500, under_ceiling=len(final) <= 3500,
        hash_audit=aud,
        full_log_retained=retention["matrix_retained_count"],
        matrix_sha256=_sha_file(matrix),
        seed_schedule_sha256=hashlib.sha256(json.dumps(seed_sched, sort_keys=True).encode()).hexdigest(),
        retention_checksum_sha256=retention["retention_checksum_sha256"],
        dependency_lock_sha256=DEP_LOCK_SHA,
        output_schema_version=OUTPUT_SCHEMA_VERSION, scenario_engine_version=ENGINE_VERSION)
    json.dump(summary, open(os.path.join(RAW, "matrix_5b1b_summary.json"), "w"), indent=2)
    json.dump(aud, open(os.path.join(DOCS, "STAGE_05B1B_HASH_GROUP_AUDIT.json"), "w"), indent=2)
    json.dump(retention, open(os.path.join(RAW, "retention_manifest.json"), "w"), indent=2)
    return summary


if __name__ == "__main__":
    final, stats, retention = build()
    s = write(final, stats, retention)
    print(json.dumps(s, indent=2))
