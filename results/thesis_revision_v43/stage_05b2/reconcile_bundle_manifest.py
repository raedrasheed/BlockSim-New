#!/usr/bin/env python3
"""Stage 5B2A — reconcile bundle_manifest.json to the complete 1890 durable bundles.

The finalize pass wrote bundle_manifest.json with 1761 entries (it was produced
before the final recovery batch's revalidated bundles were folded in). This script
regenerates the manifest DIRECTLY from the 1890 on-disk durable bundles, then
verifies:

  * every recomputed bundle SHA-256 equals results_manifest.json's bundle_sha256;
  * every run_id already present in the old bundle_manifest keeps an identical
    entry (sha256 + all metrics) — i.e. nothing that was recorded is changed;
  * the reconciled run_id set equals results_manifest.json's 1890 run_ids exactly.

It only ever ADDS the missing entries; it never alters an existing correct one.
Idempotent: running it on an already-complete manifest is a no-op (content-identical).
"""
import gzip
import hashlib
import json
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
RUNS = os.path.join(BASE, "runs")
MANI = os.path.join(BASE, "manifests")
BUNDLE_MANIFEST = os.path.join(MANI, "bundle_manifest.json")
RESULTS_MANIFEST = os.path.join(MANI, "results_manifest.json")
REPO_ROOT = os.path.abspath(os.path.join(BASE, "..", "..", ".."))

ENTRY_KEYS = [
    "run_id", "run_execution_hash", "scientific_semantics_hash",
    "analysis_group_hash", "scenario_id", "interpretation_labels",
    "master_seed", "engine_version", "schema_version", "source_commit",
    "matrix_sha256", "bundle", "bundle_sha256", "qc_passed",
    "accepted_blocks", "template_generations", "total_candidate_evaluations",
    "total_energy_kwh", "single_height_stale_block_count", "partial_generations",
]
METRIC_KEYS = [
    "accepted_blocks", "template_generations", "total_candidate_evaluations",
    "total_energy_kwh", "single_height_stale_block_count", "partial_generations",
]


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def build_entry(gz_path):
    d = json.load(gzip.open(gz_path))
    ident = d["ident"]
    r = d["r"]
    rel = os.path.relpath(gz_path, REPO_ROOT)
    entry = {
        "run_id": ident["run_id"],
        "run_execution_hash": ident["run_execution_hash"],
        "scientific_semantics_hash": ident["scientific_semantics_hash"],
        "analysis_group_hash": ident["analysis_group_hash"],
        "scenario_id": ident["scenario_id"],
        "interpretation_labels": ident["interpretation_labels"],
        "master_seed": ident["master_seed"],
        "engine_version": ident["engine_version"],
        "schema_version": ident["schema_version"],
        "source_commit": ident["source_commit"],
        "matrix_sha256": ident["matrix_sha256"],
        "bundle": rel,
        "bundle_sha256": sha256_file(gz_path),
        "qc_passed": d["qc_passed"],
        "accepted_blocks": r["accepted_blocks"],
        "template_generations": r["template_generations"],
        "total_candidate_evaluations": r["total_candidate_evaluations"],
        "total_energy_kwh": r["total_energy_kwh"],
        "single_height_stale_block_count": r["single_height_stale_block_count"],
        "partial_generations": r["partial_generations"],
    }
    return entry


def main():
    old = {e["run_id"]: e for e in json.load(open(BUNDLE_MANIFEST))}
    res = {e["run_id"]: e for e in json.load(open(RESULTS_MANIFEST))}
    print(f"old bundle_manifest entries : {len(old)}")
    print(f"results_manifest entries    : {len(res)}")

    gz_paths = []
    for dirpath, _dirs, files in os.walk(RUNS):
        for fn in files:
            if fn.endswith(".run.json.gz"):
                gz_paths.append(os.path.join(dirpath, fn))
    gz_paths.sort()
    print(f"durable bundles on disk     : {len(gz_paths)}")

    entries = {}
    sha_mismatch = []
    old_changed = []
    for i, gz in enumerate(gz_paths, 1):
        e = build_entry(gz)
        rid = e["run_id"]
        entries[rid] = e
        # cross-check vs results_manifest bundle_sha256
        if rid not in res:
            sha_mismatch.append((rid, "NOT_IN_RESULTS_MANIFEST"))
        elif res[rid]["bundle_sha256"] != e["bundle_sha256"]:
            sha_mismatch.append((rid, f"results={res[rid]['bundle_sha256']} disk={e['bundle_sha256']}"))
        # existing bundle_manifest entry must be unchanged for shared keys
        if rid in old:
            o = old[rid]
            for k in ("bundle_sha256", *METRIC_KEYS, "qc_passed"):
                if o.get(k) != e.get(k):
                    old_changed.append((rid, k, o.get(k), e.get(k)))
        if i % 300 == 0:
            print(f"  hashed {i}/{len(gz_paths)}")

    disk_ids = set(entries)
    res_ids = set(res)
    only_disk = sorted(disk_ids - res_ids)
    only_res = sorted(res_ids - disk_ids)
    newly_added = sorted(disk_ids - set(old))

    print(f"newly added run_ids         : {len(newly_added)}")
    print(f"sha256 mismatches vs results: {len(sha_mismatch)}")
    print(f"changed existing entries    : {len(old_changed)}")
    print(f"disk-only run_ids           : {len(only_disk)}")
    print(f"results-only run_ids        : {len(only_res)}")

    problems = bool(sha_mismatch or old_changed or only_disk or only_res)
    if problems:
        print("!! RECONCILIATION PROBLEMS !!")
        for x in sha_mismatch[:10]:
            print("  sha:", x)
        for x in old_changed[:10]:
            print("  changed:", x)
        for x in only_disk[:10]:
            print("  only_disk:", x)
        for x in only_res[:10]:
            print("  only_res:", x)
        sys.exit(2)

    if len(entries) != 1890:
        print(f"!! expected 1890 entries, got {len(entries)}")
        sys.exit(3)

    out = [entries[rid] for rid in sorted(entries)]
    # normalise key ordering
    out = [{k: e[k] for k in ENTRY_KEYS} for e in out]
    with open(BUNDLE_MANIFEST, "w") as fh:
        json.dump(out, fh, indent=1, sort_keys=False)
        fh.write("\n")
    print(f"WROTE {BUNDLE_MANIFEST} with {len(out)} entries")
    print("RECONCILE_OK")


if __name__ == "__main__":
    main()
