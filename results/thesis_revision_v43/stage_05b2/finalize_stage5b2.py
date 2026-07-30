"""Stage 5B2 — finalization: aggregate the 1890 durable per-run bundles into the
Section-16 committed layout, revalidate QC once more, write the complete results
manifest, output index, and checksum manifest, and compute storage statistics.

Reads bundles (the durable source of truth), never re-executes the engine. Writes
gzip-compressed JSONL partitioned by scenario (and by scientific-semantics group for
the two large kinds), individual full-log directories for retained runs, and JSON/CSV
manifests. Single-process, bounded memory (one bundle at a time).
"""

from __future__ import annotations
import os
import sys
import csv
import gzip
import json
import hashlib
import collections

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.setdefault("STAGE5B2_ROOT", os.path.abspath(os.path.join(HERE, "..", "..", "..")))
import execute_stage5b2 as H

OUT = H.OUT
ROOT = H.ROOT
BUNDLES = os.path.join(OUT, "runs")
BIG = {"per_miner_generation", "delivery_delays"}
SUMMARY_EXCLUDE = ("per_miner", "per_template", "per_miner_generation", "block_log",
                   "stale_race_records", "delivery_delay_records")


def sha_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 16), b""):
            h.update(c)
    return h.hexdigest()


class GzW:
    def __init__(self, path):
        self.path = path
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self.tmp = path + ".tmp"
        self.f = gzip.open(self.tmp, "wt", encoding="utf-8")
        self.rows = 0

    def write(self, obj):
        self.f.write(json.dumps(obj, separators=(",", ":")) + "\n")
        self.rows += 1

    def close(self):
        self.f.close()
        os.replace(self.tmp, self.path)
        return sha_file(self.path)


def main():
    matrix = H.load_matrix()
    by_id = {r["run_id"]: r for r in matrix}
    retained = {r["run_id"] for r in matrix
                if str(r.get("retention_full_log", "")).lower() in ("true", "1")}

    writers = {}

    def w(kind, scen, group=None):
        if kind in BIG and group:
            key = (kind, scen, group)
            path = os.path.join(OUT, kind, scen, f"{kind}-{scen}-{group}.jsonl.gz")
        else:
            key = (kind, scen)
            path = os.path.join(OUT, kind, f"{kind}-{scen}.jsonl.gz")
        if key not in writers:
            writers[key] = GzW(path)
        return writers[key]

    summary_w = GzW(os.path.join(OUT, "summary", "summary.jsonl.gz"))
    manifest = []
    index_rows = []
    qc_fail = []
    stats = collections.Counter()
    scen_counts = collections.Counter()
    group_seed = collections.defaultdict(set)

    bundle_files = []
    for r, _, fs in os.walk(BUNDLES):
        for fn in fs:
            if fn.endswith(".run.json.gz"):
                bundle_files.append(os.path.join(r, fn))
    assert len(bundle_files) == 1890, f"expected 1890 bundles, found {len(bundle_files)}"

    for bf in sorted(bundle_files):
        d = json.load(gzip.open(bf, "rt", encoding="utf-8"))
        rid = d["ident"]["run_id"]
        row = by_id[rid]
        r = d["r"]
        passed, fails = H.qc(row, r)      # final revalidation gate
        if not passed:
            qc_fail.append(dict(run_id=rid, fails=fails))
            continue
        scen = row["scenario_id"]
        grp = row["scientific_semantics_hash"][:12]
        scen_counts[scen] += 1
        group_seed[row["scientific_semantics_hash"]].add(row["seed"])
        summary_w.write(dict(d["ident"], **{k: v for k, v in r.items() if k not in SUMMARY_EXCLUDE}))
        for m in r["per_miner"]:
            w("per_miner", scen).write({**m, "run_id": rid})
        for t in r["per_template"]:
            w("per_template", scen).write({**t, "run_id": rid})
        for g in r["per_miner_generation"]:
            w("per_miner_generation", scen, grp).write({**g, "run_id": rid})
        stats["pmg_rows"] += len(r["per_miner_generation"])
        for b in (r.get("block_log") or []):
            w("block_log", scen).write({**b, "run_id": rid})
        for x in (r.get("stale_race_records") or []):
            w("stale_race", scen).write({**x, "run_id": rid})
            stats["stale_records"] += 1
        for dd in (r.get("delivery_delay_records") or []):
            w("delivery_delays", scen, grp).write({**dd, "run_id": rid})
            stats["delivery_records"] += 1
        if r["accepted_blocks"] == 0:
            stats["zero_block_runs"] += 1
        if r["partial_generations"] > 0:
            stats["partial_generation_runs"] += 1
        # retained full-log per-run directory
        if rid in retained:
            fl = os.path.join(OUT, "full_logs", rid)
            os.makedirs(fl, exist_ok=True)
            json.dump(dict(d["ident"], summary={k: v for k, v in r.items() if k not in SUMMARY_EXCLUDE}),
                      open(os.path.join(fl, "summary.json"), "w"), indent=2)
            for kind, key in (("per_miner", "per_miner"), ("per_template", "per_template"),
                              ("per_miner_generation", "per_miner_generation"),
                              ("block_log", "block_log"), ("stale_race", "stale_race_records"),
                              ("delivery_delays", "delivery_delay_records")):
                with gzip.open(os.path.join(fl, f"{kind}.jsonl.gz"), "wt", encoding="utf-8") as fh:
                    for rec in (r.get(key) or []):
                        fh.write(json.dumps({**rec, "run_id": rid}, separators=(",", ":")) + "\n")
        manifest.append(dict(d["ident"], bundle_sha256=sha_file(bf),
                             accepted_blocks=r["accepted_blocks"],
                             template_generations=r["template_generations"],
                             total_candidate_evaluations=r["total_candidate_evaluations"],
                             total_energy_kwh=r["total_energy_kwh"],
                             single_height_stale_block_count=r["single_height_stale_block_count"],
                             retained_full_log=(rid in retained), qc_passed=True))
        index_rows.append(dict(run_id=rid, scenario=scen,
                               scientific_semantics_hash=row["scientific_semantics_hash"],
                               run_execution_hash=row["run_execution_hash"], seed=int(row["seed"]),
                               accepted_blocks=r["accepted_blocks"],
                               pmg_rows=len(r["per_miner_generation"]),
                               retained_full_log=(rid in retained)))

    file_checksums = {os.path.relpath(summary_w.path, ROOT): summary_w.close()}
    for wtr in writers.values():
        file_checksums[os.path.relpath(wtr.path, ROOT)] = wtr.close()

    md = os.path.join(OUT, "manifests")
    os.makedirs(md, exist_ok=True)
    json.dump(manifest, open(os.path.join(md, "results_manifest.json"), "w"), indent=2)
    with open(os.path.join(md, "output_index.csv"), "w", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=["run_id", "scenario", "scientific_semantics_hash",
                                           "run_execution_hash", "seed", "accepted_blocks",
                                           "pmg_rows", "retained_full_log"])
        wr.writeheader()
        for x in sorted(index_rows, key=lambda z: z["run_id"]):
            wr.writerow(x)

    # full checksum manifest over ALL committed output files (summary/per_*/stale/delivery/
    # block_log/full_logs/manifests/logs), excluding the local-only durable bundles.
    checks = {}
    for d in ("summary", "per_miner", "per_template", "per_miner_generation", "block_log",
              "stale_race", "delivery_delays", "full_logs", "manifests", "logs"):
        base = os.path.join(OUT, d)
        for r, _, fs in os.walk(base):
            for fn in fs:
                p = os.path.join(r, fn)
                checks[os.path.relpath(p, ROOT)] = sha_file(p)
    with open(os.path.join(md, "..", "STAGE_05B2_CHECKSUM_MANIFEST.sha256"), "w") as f:
        for path in sorted(checks):
            f.write(f"{checks[path]}  {path}\n")
    # also copy checksum manifest into docs for delivery
    import shutil
    shutil.copy(os.path.join(OUT, "STAGE_05B2_CHECKSUM_MANIFEST.sha256"),
                os.path.join(ROOT, "docs", "thesis_revision_v43", "STAGE_05B2_CHECKSUM_MANIFEST.sha256"))

    result = dict(bundles=len(bundle_files), aggregated=len(manifest), qc_fail=len(qc_fail),
                  groups=len(group_seed), each_group_30=all(len(s) == 30 for s in group_seed.values()),
                  scenario_counts=dict(scen_counts), stats=dict(stats),
                  committed_output_files=len(checks))
    json.dump(result, open(os.path.join(md, "aggregation_summary.json"), "w"), indent=2)
    print(json.dumps(dict(result, qc_failures=qc_fail[:10]), indent=2))
    return result


if __name__ == "__main__":
    main()
