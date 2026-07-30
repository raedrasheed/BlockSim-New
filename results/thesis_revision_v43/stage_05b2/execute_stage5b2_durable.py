"""Stage 5B2 — DURABLE, RESUMABLE execution harness (recovery-safe).

Reuses the validated config-mapping, QC (families A-J), and pure worker from
execute_stage5b2.py, but persists each run as ONE atomically-written per-run bundle
(<run_id>.run.json.gz) the moment it completes — so a container restart never loses
completed work. On (re)start it skips runs whose bundle already exists AND still
re-passes QC, and executes only the exact resume set. A recovery checkpoint is written
at least every 50 newly completed runs. Append-only ledger is preserved.

Run:  python3 execute_stage5b2_durable.py --workers 3
"""

from __future__ import annotations
import os
import sys
import json
import gzip
import time
import hashlib
import argparse
import collections
import multiprocessing as mp
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.setdefault("STAGE5B2_ROOT", os.path.abspath(os.path.join(HERE, "..", "..", "..")))
import execute_stage5b2 as H     # validated load_matrix / run_one / qc / row_to_config / OUT / ROOT

BUNDLES = os.path.join(H.OUT, "runs")
LEDGER = os.path.join(H.OUT, "logs", "execution_ledger.jsonl")
CKPT = os.path.join(H.ROOT, "docs", "thesis_revision_v43", "STAGE_05B2_RECOVERY_CHECKPOINT.json")


def utc():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def bpath(row):
    return os.path.join(BUNDLES, row["scenario_id"], row["scientific_semantics_hash"][:12],
                        row["run_id"] + ".run.json.gz")


def sha_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 16), b""):
            h.update(c)
    return h.hexdigest()


def already_valid(row):
    """A run counts as recovered-valid iff its bundle exists, its identity matches the
    frozen row, and QC still passes on the stored result (Section 4 revalidation)."""
    p = bpath(row)
    if not os.path.exists(p):
        return False
    try:
        d = json.load(gzip.open(p, "rt", encoding="utf-8"))
        if d.get("ident", {}).get("run_execution_hash") != row["run_execution_hash"]:
            return False
        passed, _ = H.qc(row, d["r"])
        return bool(passed)
    except Exception:
        return False


def write_bundle(row, res):
    p = bpath(row)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tmp = p + f".{os.getpid()}.tmp"          # per-process temp -> no cross-run contention
    with gzip.open(tmp, "wt", encoding="utf-8") as f:
        json.dump(dict(ident=res["ident"], qc_passed=True, r=res["r"]), f, separators=(",", ":"))
    os.replace(tmp, p)                        # atomic promote to final
    return sha_file(p)


def durable_worker(row):
    """Isolated worker: compute + QC + write THIS run's own bundle atomically, then
    return a SMALL payload (no per-miner / per-generation / delivery data crosses the
    pipe — that is what previously overflowed the parent). Each worker writes only its
    own uniquely-named bundle, so runs never contend."""
    res = H.run_one(row)
    small = dict(run_id=res["run_id"], pid=res["pid"], duration=res["duration"],
                 start_utc=res["start_utc"], end_utc=res["end_utc"])
    if not res["ok"]:
        return dict(small, ok=False, error_class=res["error_class"],
                    error_message=res["error_message"], traceback=res["traceback"])
    if not res["passed"]:
        return dict(small, ok=True, passed=False, fails=res["fails"])
    sha = write_bundle(row, res)
    r = res["r"]
    return dict(small, ok=True, passed=True, bundle_sha=sha, ident=res["ident"],
                metrics=dict(accepted_blocks=r["accepted_blocks"],
                             template_generations=r["template_generations"],
                             total_candidate_evaluations=r["total_candidate_evaluations"],
                             total_energy_kwh=r["total_energy_kwh"],
                             single_height_stale_block_count=r["single_height_stale_block_count"],
                             partial_generations=r["partial_generations"]))


def ledger_sha():
    return sha_file(LEDGER) if os.path.exists(LEDGER) else None


def write_checkpoint(counts, last_rid, size_bytes):
    tmp = CKPT + ".tmp"
    import shutil
    free = shutil.disk_usage(H.ROOT).free
    json.dump(dict(utc=utc(), completed_valid=counts["completed_valid"],
                   remaining=counts["remaining"], failed_terminal=counts["failed_terminal"],
                   interrupted_historical=counts["interrupted_historical"],
                   output_size_bytes=size_bytes, free_disk_bytes=free,
                   last_completed_run_id=last_rid, ledger_sha256=ledger_sha()),
              open(tmp, "w"), indent=2)
    os.replace(tmp, CKPT)


def dir_size(path):
    tot = 0
    for r, _, fs in os.walk(path):
        for fn in fs:
            try:
                tot += os.path.getsize(os.path.join(r, fn))
            except OSError:
                pass
    return tot


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=3)
    args = ap.parse_args()

    matrix = H.load_matrix()
    os.makedirs(os.path.dirname(LEDGER), exist_ok=True)
    led_rows = [json.loads(l) for l in open(LEDGER)] if os.path.exists(LEDGER) else []
    prev_attempt = collections.defaultdict(int)
    for r in led_rows:
        if r.get("run_id") and r.get("run_id") != "RECOVERY":
            prev_attempt[r["run_id"]] = max(prev_attempt[r["run_id"]], r.get("attempt", 1))
    hist_interrupted = sum(1 for r in led_rows if r.get("status") == "INTERRUPTED")

    resume, recovered = [], []
    for row in matrix:
        (recovered if already_valid(row) else resume).append(row)

    print(json.dumps(dict(planned=len(matrix), recovered_completed_valid=len(recovered),
                          resume_set=len(resume), reconcile=len(recovered) + len(resume) == 1890),
                     indent=2))

    ledf = open(LEDGER, "a")

    def emit(e):
        ledf.write(json.dumps(e) + "\n")
        ledf.flush()

    counts = dict(completed_valid=len(recovered), remaining=len(resume), failed_terminal=0,
                  interrupted_historical=hist_interrupted)
    manifests = []
    done_since_ckpt = 0
    last_rid = None
    t0 = time.time()
    row_by_id = {r["run_id"]: r for r in matrix}
    ctx = mp.get_context("spawn")
    with ctx.Pool(processes=args.workers) as pool:
        for res in pool.imap_unordered(durable_worker, resume, chunksize=1):
            rid = res["run_id"]
            row = row_by_id[rid]
            attempt = prev_attempt[rid] + 1
            base = dict(run_id=rid, run_execution_hash=row["run_execution_hash"],
                        scientific_semantics_hash=row["scientific_semantics_hash"],
                        analysis_group_hash=row.get("analysis_group_hash_v2", ""),
                        scenario=row["scenario_id"], interpretation_labels=row["interpretation_labels"],
                        master_seed=int(row["seed"]), attempt=attempt, worker_pid=res["pid"],
                        host=os.uname().nodename, utc_start=res["start_utc"], utc_end=res["end_utc"],
                        duration_s=round(res["duration"], 4), source_commit=H.SOURCE_COMMIT,
                        matrix_sha256=H.MATRIX_SHA, retry_reason=("recovery_resume" if attempt > 1 else ""))
            if not res["ok"]:
                counts["failed_terminal"] += 1
                fa = os.path.join(H.OUT, "failed_attempts", f"{rid}.attempt{attempt}.error.json")
                os.makedirs(os.path.dirname(fa), exist_ok=True)
                json.dump(dict(base, status="FAILED_TERMINAL", error_class=res["error_class"],
                               error_message=res["error_message"], traceback=res["traceback"]),
                          open(fa, "w"), indent=2)
                emit(dict(base, status="FAILED_TERMINAL", exit_code=1,
                          error_class=res["error_class"], error_message=res["error_message"],
                          output_dir=fa))
                continue
            if not res["passed"]:
                counts["failed_terminal"] += 1
                fa = os.path.join(H.OUT, "failed_attempts", f"{rid}.attempt{attempt}.qc_fail.json")
                os.makedirs(os.path.dirname(fa), exist_ok=True)
                json.dump(dict(base, status="FAILED_TERMINAL", qc_failures=res["fails"]),
                          open(fa, "w"), indent=2)
                emit(dict(base, status="FAILED_TERMINAL", exit_code=2, error_class="QC_FAILURE",
                          error_message=";".join(res["fails"]), output_dir=fa))
                continue
            m = res["metrics"]
            manifests.append(dict(res["ident"], bundle=os.path.relpath(bpath(row), H.ROOT),
                                  bundle_sha256=res["bundle_sha"], qc_passed=True, **m))
            emit(dict(base, status="COMPLETED_VALID", exit_code=0, error_class="", error_message="",
                      output_dir=os.path.relpath(bpath(row), H.ROOT), bundle_sha256=res["bundle_sha"]))
            counts["completed_valid"] += 1
            counts["remaining"] -= 1
            last_rid = rid
            done_since_ckpt += 1
            if done_since_ckpt >= 50:
                write_checkpoint(counts, last_rid, dir_size(BUNDLES))
                done_since_ckpt = 0
    ledf.close()
    write_checkpoint(counts, last_rid, dir_size(BUNDLES))
    os.makedirs(os.path.join(H.OUT, "manifests"), exist_ok=True)
    json.dump(manifests, open(os.path.join(H.OUT, "manifests", "bundle_manifest.json"), "w"), indent=2)
    counts["wall_clock_s"] = round(time.time() - t0, 2)
    print(json.dumps(counts, indent=2))
    return counts


if __name__ == "__main__":
    main()
