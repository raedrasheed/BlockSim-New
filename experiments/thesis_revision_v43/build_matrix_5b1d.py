"""Stage 5B1D: regenerate the matrix after the exact-sampler correction. Scientific
semantics are unchanged, but the scenario-engine version (which feeds
scientific_semantics_hash and run_execution_hash) is bumped to 5b1d.1, so those
hashes change. Preserves every earlier matrix. Does NOT execute the matrix.
"""

from __future__ import annotations
import os
import csv
import json
import hashlib

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DOCS = os.path.join(ROOT, "docs", "thesis_revision_v43")
RAW = os.path.join(ROOT, "results", "thesis_revision_v43", "stage_05b1d", "raw")

from experiments.thesis_revision_v43 import build_matrix_5b1b as b5b1b
from experiments.thesis_revision_v43.scenario_engine import ENGINE_VERSION
from experiments.thesis_revision_v43.schemas import OUTPUT_SCHEMA_VERSION
from experiments.thesis_revision_v43 import build_matrix_5b1 as base


def _sha_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for c in iter(lambda: f.read(1 << 16), b""):
            h.update(c)
    return h.hexdigest()


def build():
    return b5b1b.build()          # reuses the corrected engine version (5b1d.1) in the hashes


def write(final, stats, retention):
    os.makedirs(DOCS, exist_ok=True)
    os.makedirs(RAW, exist_ok=True)
    matrix = os.path.join(DOCS, "STAGE_05B1D_FINAL_MATRIX.csv")
    with open(matrix, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=b5b1b.FIELDS, extrasaction="ignore")
        w.writeheader()
        for r in final:
            r["expected_output_path"] = f"results/thesis_revision_v43/stage_05b2/raw/{r['run_id']}.summary.json"
            r["planned_status"] = "PLANNED"
            w.writerow(r)
    aud = b5b1b.audit(final)
    seed_sched = dict(seed_base=base.SEED_BASE, n_seeds=30, seeds=base.SEEDS)
    summary = dict(
        stage="5B1D", scenario_engine_version=ENGINE_VERSION,
        output_schema_version=OUTPUT_SCHEMA_VERSION,
        final_stage5b2_run_count=len(final), ceiling=3500, under_ceiling=len(final) <= 3500,
        hash_audit=aud,
        full_log_retained=retention["matrix_retained_count"],
        matrix_sha256=_sha_file(matrix),
        seed_schedule_sha256=hashlib.sha256(json.dumps(seed_sched, sort_keys=True).encode()).hexdigest(),
        retention_checksum_sha256=retention["retention_checksum_sha256"],
        dependency_lock_sha256=b5b1b.DEP_LOCK_SHA)
    json.dump(summary, open(os.path.join(RAW, "matrix_5b1d_summary.json"), "w"), indent=2)
    json.dump(aud, open(os.path.join(DOCS, "STAGE_05B1D_HASH_GROUP_AUDIT.json"), "w"), indent=2)
    json.dump(retention, open(os.path.join(RAW, "retention_manifest.json"), "w"), indent=2)
    return summary


if __name__ == "__main__":
    final, stats, retention = build()
    s = write(final, stats, retention)
    print(json.dumps(s, indent=2))
