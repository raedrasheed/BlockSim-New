#!/usr/bin/env python3
"""Stage 6 — common loader, constants, and canonical field authority.

Loads the frozen Stage-5B2 per-run `summary` table (the authoritative one-line-per-run
dataset, 1890 rows) and merges the few run-level design variables that live only in the
frozen matrix (propagation delay, hypothesis_id, matrix_class), joined on the unique
`run_execution_hash`. No scientific quantity is recomputed here; this module only reads
frozen outputs and exposes them for analysis.

Nothing in this module (or anywhere in Stage 6) modifies a scientific result.
"""
import gzip
import hashlib
import json
import os

# ---- authoritative identifiers (Stage-6 approval §1) ----
FREEZE6_COMMIT = "45361674e6278971d430a79531f7aaac5cae3281"
RESULTS1_COMMIT = "d2ef6012afc8275c108ef56737a54a156abe5ceb"
RESULTS2_COMMIT = "9347ec969bd59a3337582571668ae2140c40485b"
RESULTS3_COMMIT = "278af17e76416c6018df6ffa23795904ae5a4e89"
DATA1_COMMIT = "b44975dd0803e3912f6151398a5a93c34eb95082"
MATRIX_SHA256 = "9cb7297e7418a96fbaeb7f06c162bc8bdea1c1e049002a40344cab16cf5f6fcb"
ENGINE_VERSION = "5b1g.2"
OUTPUT_SCHEMA_VERSION = "5b1g.2"
THESIS_DOCX_SHA = "2c3afdc5739109d0ea12ada96c3115d626a2188c1acbaeaa4b6020974884cbda"
THESIS_PDF_SHA = "131412bb2ce17ed97b98dfbefc136c7b5b226b9fd7372e79a25e4b0dc057e9c4"

EXPECTED_RUNS = 1890
EXPECTED_GROUPS = 63
EXPECTED_SEEDS_PER_GROUP = 30
EXPECTED_ZERO_BLOCK = 142

# continuous full-participation accounting anchor (A1); P_total = H_net * eff = 3031.5 W
CONTINUOUS_ENERGY_ANCHOR_KWH = 8.420833333333333
P_TOTAL_W = 3031.5
HORIZON_S = 10000.0

# analysis-level statistical parameters (recorded before inspecting outcomes)
ALPHA = 0.05
CONF_LEVEL = 0.95
N_BOOTSTRAP = 10000
N_PERMUTATION = 10000
# named, recorded analysis RNG seeds (independent of the frozen simulation seeds)
RNG_SEED_BOOTSTRAP = 6060601
RNG_SEED_PERMUTATION = 6060602

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
STAGE5B2 = os.path.join(REPO_ROOT, "results", "thesis_revision_v43", "stage_05b2")
DOCS = os.path.join(REPO_ROOT, "docs", "thesis_revision_v43")
SUMMARY_GLOB = os.path.join(STAGE5B2, "summary", "summary.jsonl.gz")
MATRIX_CSV = os.path.join(DOCS, "STAGE_05B1G1_FINAL_MATRIX.csv")
STAGE6 = os.path.join(REPO_ROOT, "results", "thesis_revision_v43", "stage_06")

# ---- canonical field authority (Stage-6 approval §5) ----
CANON = {
    "finder": "distinct_potential_finder_miner_count",
    "solution_positions": [
        "total_template_solution_position_count",
        "active_range_solution_position_count",
        "inactive_range_solution_position_count",
    ],
    "candidate": [
        "total_candidate_evaluations",
        "distinct_candidate_identities",
        "duplicate_evaluations",
        "duplicate_evaluation_rate",
    ],
    "stale_diag": [
        "single_height_stale_block_count",
        "single_height_stales_per_accepted_block",
        "single_height_stale_fraction_of_valid_proposals",
        "actual_stale_producer_miner_count",
        "actual_competitor_miner_count",
        "actual_proposal_miner_count",
    ],
    "post_winner": [
        "post_winner_candidate_evaluations",
        "post_winner_active_time_s",
        "stale_producer_postwinner_candidate_evaluations",
        "stale_producer_postwinner_active_time_s",
    ],
}
# fields explicitly forbidden as authoritative analytical outcomes (§5)
FORBIDDEN_FIELDS = {
    "discoverable_finder_count",
    "unsearched_count",
    "remaining_unsearched",
    "legitimate_stale_block_count",
    "legitimate_stale_count",
    "legitimate_stale_rate",
    "stale_block_count",
    "stale_blocks",
    "stales_per_accepted_block",
    "stale_fraction_of_all_valid_blocks",
}


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for c in iter(lambda: fh.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def _num(x):
    if x is None or x == "":
        return None
    try:
        f = float(x)
        return int(f) if f.is_integer() else f
    except (TypeError, ValueError):
        return x


def load_matrix():
    import csv
    with open(MATRIX_CSV) as fh:
        return list(csv.DictReader(fh))


def load_runs():
    """Return a list of run dicts: the frozen summary record augmented with the
    matrix-only design fields (propagation delay, hypothesis_id, matrix_class,
    reused_by_hypotheses), joined on run_execution_hash. 1890 rows."""
    runs = []
    with gzip.open(SUMMARY_GLOB, "rt") as fh:
        for line in fh:
            if line.strip():
                runs.append(json.loads(line))
    mat = {r["run_execution_hash"]: r for r in load_matrix()}
    assert len(mat) == EXPECTED_RUNS, f"matrix rows {len(mat)}"
    for r in runs:
        m = mat[r["run_execution_hash"]]
        r["propagation_delay_mean_s"] = _num(m["propagation_delay_mean_s"])
        r["hypothesis_id"] = m["hypothesis_id"]
        r["matrix_class"] = m["matrix_class"]
        r["reused_by_hypotheses"] = m["reused_by_hypotheses"]
        r["miner_count"] = _num(m["miner_count"])
    assert len(runs) == EXPECTED_RUNS, f"summary rows {len(runs)}"
    return runs


def runs_by(runs, **filters):
    """Filter helper: runs_by(runs, scenario_id='B1', miners=200)."""
    out = []
    for r in runs:
        if all(r.get(k) == v for k, v in filters.items()):
            out.append(r)
    return out


if __name__ == "__main__":
    runs = load_runs()
    print("loaded runs:", len(runs))
    print("matrix sha256 matches:", sha256_file(MATRIX_CSV) == MATRIX_SHA256)
    from collections import Counter
    print("hypothesis_id:", dict(Counter(r["hypothesis_id"] for r in runs)))
    print("zero-block:", sum(1 for r in runs if r["accepted_blocks"] == 0))
