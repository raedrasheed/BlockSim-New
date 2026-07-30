#!/usr/bin/env python3
"""Stage 6 §3 — input-integrity gate (12 checks).

Verifies the analysis inputs before any analysis runs. Emits a JSON verdict. If any
check fails, prints STAGE_6_ANALYSIS_BLOCKED and exits non-zero. Never repairs or
regenerates source data.
"""
import json
import os
import subprocess
import sys
from collections import Counter, defaultdict

import s6_common as C


def git(*args):
    return subprocess.check_output(["git", "-C", C.REPO_ROOT, *args], text=True).strip()


def main():
    checks = []

    def rec(n, name, passed, detail):
        checks.append({"n": n, "name": name, "pass": bool(passed), "detail": detail})

    runs = C.load_runs()
    manifest = json.load(open(os.path.join(C.STAGE5B2, "manifests", "results_manifest.json")))

    # 1. analysis branch is built on the authoritative results-3 commit
    #    (Stage 6 checks out results-3 directly; Stage 6A corrective branches build on it).
    head = git("rev-parse", "HEAD")
    try:
        subprocess.check_call(
            ["git", "-C", C.REPO_ROOT, "merge-base", "--is-ancestor",
             C.RESULTS3_COMMIT, "HEAD"])
        anc = True
    except subprocess.CalledProcessError:
        anc = False
    rec(1, "results-3 is HEAD or an ancestor of HEAD (built on results-3)",
        head == C.RESULTS3_COMMIT or anc,
        {"head": head, "results3": C.RESULTS3_COMMIT,
         "head_is_results3": head == C.RESULTS3_COMMIT, "results3_is_ancestor": anc})

    # 2. matrix checksum
    msha = C.sha256_file(C.MATRIX_CSV)
    rec(2, "matrix SHA-256 matches", msha == C.MATRIX_SHA256, {"sha256": msha})

    # 3. results manifest has exactly 1890 identities
    rids = {m["run_id"] for m in manifest}
    rec(3, "results manifest has exactly 1890 identities",
        len(manifest) == C.EXPECTED_RUNS and len(rids) == C.EXPECTED_RUNS,
        {"entries": len(manifest), "distinct_run_ids": len(rids)})

    # 4. final status 1890 COMPLETED_VALID (append-only ledger, last status per run)
    import csv
    ledger = os.path.join(C.DOCS, "STAGE_05B2_EXECUTION_LEDGER.csv")
    final = {}
    with open(ledger) as fh:
        for row in csv.DictReader(fh):
            if row["run_id"].startswith("S5B2-"):
                final[row["run_id"]] = row["status"]
    valid = sum(1 for v in final.values() if v == "COMPLETED_VALID")
    rec(4, "final status = 1890 COMPLETED_VALID",
        len(final) == C.EXPECTED_RUNS and valid == C.EXPECTED_RUNS,
        {"distinct_runs": len(final), "completed_valid": valid})

    # 5. 63 scientific groups
    groups = {r["scientific_semantics_hash"] for r in runs}
    rec(5, "63 scientific groups exist", len(groups) == C.EXPECTED_GROUPS,
        {"groups": len(groups)})

    # 6. each group has 30 seeds
    per_group = Counter(r["scientific_semantics_hash"] for r in runs)
    all30 = all(v == C.EXPECTED_SEEDS_PER_GROUP for v in per_group.values())
    rec(6, "each group has 30 seeds", all30,
        {"distribution": dict(Counter(per_group.values()))})

    # 7. no same-seed scientific duplicate (within a group, 30 distinct seeds)
    dup = 0
    gseeds = defaultdict(list)
    for r in runs:
        gseeds[r["scientific_semantics_hash"]].append(r["seed"])
    for g, ss in gseeds.items():
        if len(set(ss)) != len(ss):
            dup += 1
    rec(7, "no same-seed scientific duplicate", dup == 0, {"groups_with_dup_seed": dup})

    # 8. B3/C1 dual labels refer to one physical dataset
    b3c1 = [r for r in runs if r["scenario_id"] == "B3_C1_CONTINUOUS_DISJOINT"]
    labels = {r["interpretation_labels"] for r in b3c1}
    uxh = {r["run_execution_hash"] for r in b3c1}
    rec(8, "B3/C1 dual labels = one physical dataset",
        labels == {"B3;C1"} and len(uxh) == len(b3c1) == 870,
        {"labels": sorted(labels), "physical_runs": len(uxh)})

    # 9. all 142 zero-block runs present
    zb = sum(1 for r in runs if r["accepted_blocks"] == 0)
    rec(9, "142 zero-block runs present", zb == C.EXPECTED_ZERO_BLOCK, {"zero_block": zb})

    # 10. no scientific output differs from results-1
    sci_dirs = ["summary", "per_miner", "per_template", "block_log", "stale_race", "full_logs"]
    diffs = []
    for d in sci_dirs:
        out = git("diff", "--name-only", C.RESULTS1_COMMIT, "--",
                  f"results/thesis_revision_v43/stage_05b2/{d}/")
        if out:
            diffs.extend(out.splitlines())
    rec(10, "no scientific output differs from results-1", len(diffs) == 0,
        {"changed_files": len(diffs)})

    # 11. bulk archive manifest: 42 chunks, 2196 files, ROUNDTRIP_OK, AVAILABLE_REMOTE_GIT
    bam = json.load(open(os.path.join(C.DOCS, "STAGE_05B2A_BULK_ARCHIVE_MANIFEST.json")))
    n_chunks = sum(a["chunk_count"] for a in bam["archives"])
    n_files = sum(a["original_file_count"] for a in bam["archives"])
    rv = bam["remote_verification"]
    avail = {a["availability_status"] for a in bam["archives"]}
    ok11 = (n_chunks == 42 and n_files == 2196 and rv["result"] == "ROUNDTRIP_OK"
            and avail == {"AVAILABLE_REMOTE_GIT"})
    rec(11, "bulk archive manifest 42/2196/ROUNDTRIP_OK/AVAILABLE_REMOTE_GIT", ok11,
        {"chunks": n_chunks, "files": n_files, "roundtrip": rv["result"],
         "availability": sorted(avail)})

    # 12. thesis DOCX/PDF checksums unchanged
    docx = C.sha256_file(os.path.join(C.REPO_ROOT, "docs", "Raed-Rasheed-draft-42-00.docx"))
    pdf = C.sha256_file(os.path.join(C.REPO_ROOT, "docs", "Raed-Rasheed-draft-42-00.pdf"))
    rec(12, "thesis DOCX/PDF checksums unchanged",
        docx == C.THESIS_DOCX_SHA and pdf == C.THESIS_PDF_SHA,
        {"docx_ok": docx == C.THESIS_DOCX_SHA, "pdf_ok": pdf == C.THESIS_PDF_SHA})

    passed = all(c["pass"] for c in checks)
    verdict = {
        "gate": "STAGE_06_INPUT_INTEGRITY",
        "results3_commit": head,
        "all_pass": passed,
        "checks": checks,
    }
    out = os.path.join(C.STAGE6, "manifests", "STAGE_06_INTEGRITY_GATE.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w") as fh:
        json.dump(verdict, fh, indent=1)
        fh.write("\n")
    for c in checks:
        print(f"  [{'PASS' if c['pass'] else 'FAIL'}] {c['n']:>2}. {c['name']} -> {c['detail']}")
    print()
    if passed:
        print("STAGE_06_INPUT_INTEGRITY_PASS")
        return 0
    print("STAGE_6_ANALYSIS_BLOCKED")
    return 2


if __name__ == "__main__":
    sys.exit(main())
