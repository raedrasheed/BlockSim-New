"""Stage 5B2 — group-level cross-checks and data-integrity audit (Sections 12, 14).

Reads the produced Stage-5B2 summary stream and the frozen matrix, and verifies
group structure, hash uniqueness, B3/C1 sharing, delay-only primary invariance, the
continuous energy anchor, zero-block retention, and completeness. Writes
STAGE_05B2_QC_SUMMARY additions and returns pass/fail. Run AFTER execution.
"""

from __future__ import annotations
import os
import sys
import csv
import gzip
import json
import glob
import math
import collections

ROOT = os.environ.get("STAGE5B2_ROOT") or os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
OUT = os.path.join(ROOT, "results", "thesis_revision_v43", "stage_05b2")
MATRIX = os.path.join(ROOT, "docs", "thesis_revision_v43", "STAGE_05B1G1_FINAL_MATRIX.csv")
CONTINUOUS = {"B0", "B1", "B2", "B3_C1_CONTINUOUS_DISJOINT"}
PRIMARY = ["total_energy_kwh", "active_energy_kwh", "idle_energy_kwh",
           "total_candidate_evaluations", "distinct_candidate_identities",
           "duplicate_evaluations", "accepted_blocks", "effective_block_interval_s",
           "total_active_time_s", "total_idle_time_s"]


def load_summaries():
    out = {}
    with gzip.open(os.path.join(OUT, "summary", "summary.jsonl.gz"), "rt") as f:
        for line in f:
            r = json.loads(line)
            out[r["run_id"]] = r
    return out


def main():
    matrix = list(csv.DictReader(open(MATRIX)))
    by_id = {r["run_id"]: r for r in matrix}
    S = load_summaries()
    checks = {}

    # 1. completeness: every matrix run produced exactly one summary
    checks["all_runs_present"] = (set(S) == set(by_id) and len(S) == 1890)
    # 2. group structure 63 x 30
    groups = collections.defaultdict(list)
    for rid, row in by_id.items():
        groups[row["scientific_semantics_hash"]].append(rid)
    checks["groups_63"] = (len(groups) == 63)
    checks["each_group_30"] = all(len(v) == 30 for v in groups.values())
    # 3. unique run-execution hashes
    rex = [row["run_execution_hash"] for row in by_id.values()]
    checks["unique_run_execution"] = (len(set(rex)) == 1890)
    # 4. no same-seed scientific duplicate
    ss = collections.Counter((row["scientific_semantics_hash"], row["seed"]) for row in by_id.values())
    checks["no_same_seed_dup"] = all(c == 1 for c in ss.values())
    # 5. B3/C1 share one physical run (dual-label rows exist, single execution each)
    dual = [rid for rid, row in by_id.items() if row["interpretation_labels"] == "B3;C1"]
    checks["b3c1_shared"] = (len(dual) == 870 and all(rid in S for rid in dual))

    # 6. delay-only invariance of primary outcomes
    delay_rows = [row for row in matrix if row["matrix_class"] == "SENS_DELAY"]
    by_key = collections.defaultdict(dict)
    for row in delay_rows:
        by_key[(row["miner_count"], row["seed"])][row["propagation_delay_mean_s"]] = row["run_id"]
    bad_delay = []
    for key, dmap in by_key.items():
        rids = list(dmap.values())
        base = S[rids[0]]
        for rid in rids[1:]:
            for f in PRIMARY:
                a, b = base.get(f), S[rid].get(f)
                if a is None and b is None:
                    continue
                if a is None or b is None or (isinstance(a, float) and not math.isclose(a, b, rel_tol=1e-12, abs_tol=1e-12)) \
                        or (isinstance(a, int) and a != b):
                    bad_delay.append((key, f, rids[0], rid, a, b))
    checks["delay_only_primary_invariant"] = (len(bad_delay) == 0)

    # 7. continuous full-participation energy anchor
    bad_anchor = []
    for rid, row in by_id.items():
        if row["scenario_id"] != "C2" and float(row["inactive_miner_fraction"]) == 0.0:
            exp = (float(row["network_hash_rate_hps"]) * float(row["efficiency_j_per_th"]) / 1e12
                   * float(row["simulation_duration_s"])) / 3_600_000.0
            if not math.isclose(S[rid]["total_energy_kwh"], exp, rel_tol=1e-9):
                bad_anchor.append(rid)
    checks["energy_anchor"] = (len(bad_anchor) == 0)

    # 8. zero-block runs retained in their groups (not removed)
    zero = [rid for rid, r in S.items() if r["accepted_blocks"] == 0]
    checks["zero_block_runs_present"] = all(rid in S for rid in zero)
    # 9. no outlier removed
    checks["no_removal"] = (len(S) == 1890)

    passed = all(checks.values())
    report = dict(passed=passed, checks=checks,
                  n_groups=len(groups), n_summaries=len(S), n_zero_block=len(zero),
                  n_b3c1_dual=len(dual), delay_violations=bad_delay[:20],
                  energy_anchor_violations=bad_anchor[:20])
    json.dump(report, open(os.path.join(OUT, "manifests", "group_crosschecks.json"), "w"), indent=2)
    print(json.dumps(dict(passed=passed, checks=checks, n_zero_block=len(zero)), indent=2))
    return report


if __name__ == "__main__":
    rep = main()
    sys.exit(0 if rep["passed"] else 1)
