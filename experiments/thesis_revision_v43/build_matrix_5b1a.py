"""Stage 5B1A: regenerate the final matrix after the B2 exactness fix and the
zero-block analytical audit. Preserves all earlier matrices (immutable); adds
zero-block risk fields, output-schema version, and stratified full-log retention.
Recomputes and verifies the three semantic hashes. Does NOT execute the matrix.
"""

from __future__ import annotations
import os
import csv
import json
import math
import hashlib

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DOCS = os.path.join(ROOT, "docs", "thesis_revision_v43")
RAW = os.path.join(ROOT, "results", "thesis_revision_v43", "stage_05b1a", "raw")

from experiments.thesis_revision_v43 import build_matrix_5b1 as base
from experiments.thesis_revision_v43 import hashing
from experiments.thesis_revision_v43 import b1_zero_block as zb
from experiments.thesis_revision_v43 import retention_5b1a
from experiments.thesis_revision_v43.schemas import OUTPUT_SCHEMA_VERSION

H_NET = 141e12
T = 10000.0
TARGET = 600.0


def expected_zero_block(row):
    """Expected P(0 blocks) from configuration. Material only for B1; B2 is not a
    closed-form (partial overlap) -> null; full-parallel scenarios are ~0."""
    scen = row["scenario_id"]
    p = 1.0 / (H_NET * TARGET)
    N = int(row["miner_count"])
    if scen == "B1":
        Hu = H_NET / N                                  # homogeneous unique frontier
        return math.exp(-p * Hu * T)
    if scen == "B2":
        return None                                     # not modelled analytically
    H_active = H_NET * (1.0 - float(row.get("inactive_miner_fraction", 0.0) or 0.0))
    return math.exp(-p * H_active * T)


def risk_category(p0):
    if p0 is None:
        return "unmodeled"
    return zb.risk_category(p0)


def build():
    final, stats = base.dedup()                         # 1890 deduped rows (B3==C1 merged)
    # attach new fields + verify hashes are stable after the B2 fix (config-based)
    for r in final:
        p0 = expected_zero_block(r)
        r["expected_zero_block_probability"] = p0
        r["zero_block_risk_category"] = risk_category(p0)
        r["output_schema_version"] = OUTPUT_SCHEMA_VERSION
        # recompute the execution-semantics hash and assert it is UNCHANGED after the
        # B2 fix (the hash is a pure function of configuration, not of the corrected
        # coverage computation). The row carries every config key the hash reads.
        assert hashing.execution_semantics_hash(r) == r["execution_semantics_hash"], r["run_id"]
    # stratified retention
    final, retention = retention_5b1a.design_retention(final)
    return final, stats, retention


FIELDS = ["run_id", "scenario_id", "interpretation_labels", "reused_by_hypotheses",
          "hypothesis_id", "matrix_class", "seed", "miner_count",
          "underlying_execution_model", "network_hash_rate_hps", "efficiency_j_per_th",
          "simulation_duration_s", "target_block_interval_s", "propagation_delay_mean_s",
          "hash_rate_distribution", "mu", "inactive_miner_fraction", "idle_power_ratio",
          "allocation_policy", "expected_zero_block_probability", "zero_block_risk_category",
          "output_schema_version", "configuration_hash", "execution_semantics_hash",
          "analysis_group_hash", "retention_full_log", "retention_reason_codes",
          "validation_only", "expected_output_path", "planned_status"]


def write(final, stats, retention):
    os.makedirs(DOCS, exist_ok=True)
    os.makedirs(RAW, exist_ok=True)
    with open(os.path.join(DOCS, "STAGE_05B1A_FINAL_MATRIX.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader()
        for r in final:
            r.setdefault("expected_output_path",
                         f"results/thesis_revision_v43/stage_05b2/raw/{r['run_id']}.summary.json")
            r.setdefault("planned_status", "PLANNED")
            w.writerow(r)

    by_scen, by_class, by_risk = {}, {}, {}
    for r in final:
        by_scen[r["scenario_id"]] = by_scen.get(r["scenario_id"], 0) + 1
        by_class[r["matrix_class"]] = by_class.get(r["matrix_class"], 0) + 1
        by_risk[r["zero_block_risk_category"]] = by_risk.get(r["zero_block_risk_category"], 0) + 1
    n = len(final)
    summary = dict(
        naive_planned_rows=stats["naive_planned_rows"],
        exact_duplicates_removed=stats["exact_duplicates_removed"],
        b3_c1_merged=stats["b3_c1_merged"],
        other_semantic_duplicates_removed=stats["other_semantic_duplicates_removed"],
        final_stage5b2_run_count=n, ceiling=3500, under_ceiling=n <= 3500,
        distinct_configuration_hashes=len({r["configuration_hash"] for r in final}),
        distinct_execution_semantics_hashes=len({r["execution_semantics_hash"] for r in final}),
        distinct_analysis_group_hashes=len({r["analysis_group_hash"] for r in final}),
        by_scenario=by_scen, by_class=by_class, by_zero_block_risk=by_risk,
        full_log_retained=retention["matrix_retained_count"],
        retention_checksum_sha256=retention["retention_checksum_sha256"],
        output_schema_version=OUTPUT_SCHEMA_VERSION,
        matrix_sha256=None)
    matrix_path = os.path.join(DOCS, "STAGE_05B1A_FINAL_MATRIX.csv")
    summary["matrix_sha256"] = _sha(matrix_path)
    json.dump(summary, open(os.path.join(RAW, "matrix_5b1a_summary.json"), "w"), indent=2)
    json.dump(retention, open(os.path.join(RAW, "retention_manifest.json"), "w"), indent=2)
    return summary


def _sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for c in iter(lambda: f.read(1 << 16), b""):
            h.update(c)
    return h.hexdigest()


if __name__ == "__main__":
    final, stats, retention = build()
    s = write(final, stats, retention)
    print(json.dumps(s, indent=2))
