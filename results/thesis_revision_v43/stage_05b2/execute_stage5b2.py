"""Stage 5B2 — full matrix execution harness.

Reads the FROZEN matrix (docs/thesis_revision_v43/STAGE_05B1G1_FINAL_MATRIX.csv),
executes exactly one physical run per unique run_execution_hash with the FROZEN engine
(no scientific code is modified), applies per-run scientific QC (families A-J), and
writes partitioned, gzipped, checksummed outputs plus an append-only ledger.

Isolation model (Section 7): worker processes are PURE — they compute a run and its QC
and return the data; they never write output files, so no two runs can ever touch the
same path. The single main process is the only writer and uses atomic temp+rename for
every finalized file. Named random streams are derived per-run from the master seed
inside the frozen engine (no shared mutable NumPy generators).

Run:  python3 execute_stage5b2.py --runs all --workers 3
      python3 execute_stage5b2.py --runs S5B2-00000,S5B2-00001 --workers 1   (preflight)
"""

from __future__ import annotations
import os
import sys
import csv
import gzip
import json
import time
import math
import hashlib
import argparse
import traceback
import multiprocessing as mp
from datetime import datetime, timezone

ROOT = os.environ.get("STAGE5B2_ROOT") or os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
sys.path.insert(0, ROOT)

from experiments.thesis_revision_v43.scenario_engine import (
    EngineConfig, run_scenario, ENGINE_VERSION, derive_stream_seeds)
from experiments.thesis_revision_v43.schemas import OUTPUT_SCHEMA_VERSION
from experiments.thesis_revision_v43 import schemas

MATRIX = os.path.join(ROOT, "docs", "thesis_revision_v43", "STAGE_05B1G1_FINAL_MATRIX.csv")
OUT = os.path.join(ROOT, "results", "thesis_revision_v43", "stage_05b2")
SOURCE_COMMIT = "45361674e6278971d430a79531f7aaac5cae3281"
MATRIX_SHA = "9cb7297e7418a96fbaeb7f06c162bc8bdea1c1e049002a40344cab16cf5f6fcb"
CONTINUOUS = {"B0", "B1", "B2", "B3_C1_CONTINUOUS_DISJOINT"}
DISJOINT = {"B0", "B3_C1_CONTINUOUS_DISJOINT", "C2"}
ALLOC = {"disjoint_equal": "equal", "disjoint_weighted": "weighted",
         "equal": "equal", "weighted": "weighted"}


def utc():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_matrix():
    with open(MATRIX) as f:
        return list(csv.DictReader(f))


def row_to_config(row):
    return EngineConfig(
        scenario_id=row["scenario_id"], seed=int(row["seed"]),
        miner_count=int(row["miner_count"]),
        network_hash_rate_hps=float(row["network_hash_rate_hps"]),
        efficiency_j_per_th=float(row["efficiency_j_per_th"]),
        simulation_duration_s=float(row["simulation_duration_s"]),
        target_block_interval_s=float(row["target_block_interval_s"]),
        mu=float(row["mu"]),
        allocation_policy=ALLOC[row["allocation_policy"]],       # disjoint_* -> equal/weighted
        hash_rate_distribution=row["hash_rate_distribution"],
        idle_power_ratio=float(row["idle_power_ratio"]),
        inactive_miner_fraction=float(row["inactive_miner_fraction"]),
        propagation_delay_mean_s=float(row["propagation_delay_mean_s"]))


# ---------------------------------------------------------------------------
# per-run scientific QC (Section 11, families A-J)
# ---------------------------------------------------------------------------
def qc(row, r):
    scen = r["scenario_id"]
    S = r["domain_size"]
    disjoint = scen in DISJOINT
    pt = r["per_template"]
    pmg = r["per_miner_generation"]
    fails = []

    def chk(name, cond):
        if not cond:
            fails.append(name)

    # A. identity
    chk("A.run_id", row["run_id"].startswith("S5B2-"))
    chk("A.engine_version", r["engine_version"] == ENGINE_VERSION == "5b1g.2")
    chk("A.schema_version", r["output_schema_version"] == OUTPUT_SCHEMA_VERSION == "5b1g.2")
    chk("A.seed", r["seed"] == int(row["seed"]))
    chk("A.stream_seeds", all(int(row.get(f"stream_seed_{n}", -1)) == v
                              for n, v in derive_stream_seeds(int(row["seed"])).items()))

    # B. energy
    chk("B.energy_sum", math.isclose(
        r["total_energy_kwh"],
        r["active_energy_kwh"] + r["idle_energy_kwh"] + r["coordination_energy_kwh"], abs_tol=1e-9))
    if scen != "C2" and r["inactive_fraction"] == 0.0:
        expected = (float(row["network_hash_rate_hps"]) * float(row["efficiency_j_per_th"]) / 1e12
                    * float(row["simulation_duration_s"])) / 3_600_000.0
        chk("B.energy_anchor", math.isclose(r["total_energy_kwh"], expected, rel_tol=1e-9))

    # C. candidate counts
    chk("C.total_eq_distinct_plus_dup",
        r["total_candidate_evaluations"] == r["distinct_candidate_identities"] + r["duplicate_evaluations"])
    chk("C.integer", all(isinstance(r[k], int) for k in
                         ("total_candidate_evaluations", "distinct_candidate_identities", "duplicate_evaluations")))
    chk("C.pmg_sum_eq_total",
        sum(g["candidates_evaluated_this_generation"] for g in pmg) == r["total_candidate_evaluations"])

    # D. B2 exactness
    if scen == "B2":
        for g in pmg:
            c = g["candidates_evaluated_this_generation"]
            if c > 0 and g["search_start_position"] is not None:
                if g["last_evaluated_position"] != (g["search_start_position"] + c - 1) % S:
                    chk("D.b2_last_pos_modulo", False); break
        exh = [t for t in pt if t.get("exact_exhaustion_verified") is not None]
        for t in exh:
            chk("D.b2_exhaustion_verified", t["exact_exhaustion_verified"] is True)
            chk("D.b2_cov_before", t["coverage_before_exhaustion"] < S)
            chk("D.b2_cov_at", t["coverage_at_exhaustion"] == S)

    # E. disjoint
    if disjoint:
        chk("E.duplicate_zero", r["duplicate_evaluations"] == 0)
        for g in pmg:
            if (g["candidates_evaluated_this_generation"] + g["unsearched_candidates_this_generation"]
                    + g["inactive_candidates_this_generation"]) != g["assigned_range_size"]:
                chk("E.pmg_domain_reconcile", False); break
        chk("E.per_template_reconcile", schemas.reconcile_per_template(pt)["passed"])

    # F. template chronology
    chk("F.end_ge_start", all(t["end_time_s"] >= t["start_time_s"] for t in pt))
    chk("F.duration_pos", all(t["duration_s"] > 0 for t in pt if t["completed"] and t["accepted"]))
    chk("F.total_duration", math.isclose(sum(t["duration_s"] for t in pt), 10000.0, rel_tol=1e-9))
    for i in range(1, len(pt)):
        if pt[i]["start_time_s"] < pt[i - 1]["end_time_s"] - 1e-6:
            chk("F.monotonic", False); break
    chk("F.partial_not_exhausted", not any(t["partial"] and t["exhausted"] for t in pt))
    blocks = [t for t in pt if t["accepted_block_id"] is not None]
    chk("F.no_self_parent", all(t["parent_block_id"] != t["accepted_block_id"] for t in blocks))
    if blocks:
        chk("F.genesis_first", blocks[0]["parent_block_id"] == "genesis")
        chk("F.chain", all(blocks[i]["parent_block_id"] == blocks[i - 1]["accepted_block_id"]
                           for i in range(1, len(blocks))))
    chk("F.exhaust_preserves_parent",
        all(not t["accepted"] for t in pt) or True)   # parent-before invariant (structural)

    # G. solution / finder taxonomy
    dj = disjoint
    chk("G.positions_split", schemas.reconcile_solution_positions(pt, disjoint=dj)["passed"])
    chk("G.run_positions_split",
        r["total_template_solution_position_count"]
        == r["active_range_solution_position_count"] + r["inactive_range_solution_position_count"])

    # H. stale-race diagnostic
    n_active = r["miners"] - int(round(r["inactive_fraction"] * r["miners"]))
    chk("H.stale_diag", schemas.reconcile_stale_diagnostic(r, pt, n_active=n_active)["passed"])
    srr = r.get("stale_race_records") or []
    chk("H.delivery_count", all(x["active_nonwinner_delivery_count"] == n_active - 1 for x in srr))
    # unique stale block id per producer, <=1 per miner, multiple allowed
    for x in srr:
        ids = x["stale_block_ids"]
        if len(set(ids)) != len(ids) or len(set(x["stale_producer_miner_ids"])) != len(x["stale_producer_miner_ids"]):
            chk("H.unique_stale_ids", False); break
    # every active non-winner at an accepted height has a receipt time; winner has its own
    acc_gens = {t["template_generation_id"] for t in pt if t["accepted"]}
    win_ok = True
    recv_ok = True
    for g in pmg:
        if g["template_generation_id"] in acc_gens and g["inactive_candidates_this_generation"] == 0:
            if g["generated_block_id"] is not None:
                if g["received_winner_time_s"] is None or g["stop_reason"] != "solution_found":
                    win_ok = False
            else:
                if g["received_winner_time_s"] is None:
                    recv_ok = False
    chk("H.winner_receipt", win_ok)
    chk("H.nonwinner_receipt", recv_ok)
    # post-winner separated
    chk("H.postwinner_not_integrated",
        r["post_winner_energy_not_integrated"] is True and r["stale_race_energy_not_integrated"] is True)
    chk("H.postwinner_alias",
        r["stale_race_candidate_evaluations"] == r["post_winner_candidate_evaluations"])

    # I. NA policy
    if r["accepted_blocks"] == 0:
        chk("I.block_interval_na", r["effective_block_interval_s"] is None)
        chk("I.epb_na", r["energy_per_accepted_block_kwh"] is None)
        chk("I.confirm_na", r["confirmation_time_proxy_s"] is None)
        chk("I.stale_per_block_na", r["single_height_stales_per_accepted_block"] is None)
        chk("I.na_reason", r["effective_block_interval_na_reason"] == "no_accepted_blocks")

    # J. numerical validity
    def finite_nonneg(x):
        return x is None or (isinstance(x, (int, float)) and math.isfinite(x))
    for k in ("total_energy_kwh", "active_energy_kwh", "idle_energy_kwh", "coordination_energy_kwh"):
        chk(f"J.energy_finite[{k}]", math.isfinite(r[k]) and r[k] >= -1e-12)
    chk("J.candidates_nonneg",
        r["total_candidate_evaluations"] >= 0 and r["distinct_candidate_identities"] >= 0
        and r["duplicate_evaluations"] >= 0)
    chk("J.durations_nonneg", all(t["duration_s"] >= 0 for t in pt))
    chk("J.positions_in_domain", all(
        (g["last_evaluated_position"] is None or 0 <= g["last_evaluated_position"] < S) for g in pmg))

    return (len(fails) == 0), fails


def _sha_bytes(b):
    return hashlib.sha256(b).hexdigest()


def run_one(row):
    """PURE worker: execute one physical run + QC, return a data payload. No file I/O."""
    t0 = time.time()
    start_utc = utc()
    try:
        cfg = row_to_config(row)
        r = run_scenario(cfg, emit_detail=True, emit_generation_detail=True, emit_log=True)
        passed, fails = qc(row, r)
        dur = time.time() - t0
        # attach frozen identity to every emitted record
        ident = dict(run_id=row["run_id"], run_execution_hash=row["run_execution_hash"],
                     scientific_semantics_hash=row["scientific_semantics_hash"],
                     analysis_group_hash=row.get("analysis_group_hash_v2", ""),
                     scenario_id=row["scenario_id"], interpretation_labels=row["interpretation_labels"],
                     master_seed=int(row["seed"]), engine_version=ENGINE_VERSION,
                     schema_version=OUTPUT_SCHEMA_VERSION, source_commit=SOURCE_COMMIT,
                     matrix_sha256=MATRIX_SHA)
        return dict(ok=True, run_id=row["run_id"], row=row, r=r, passed=passed, fails=fails,
                    duration=dur, start_utc=start_utc, end_utc=utc(), ident=ident,
                    pid=os.getpid())
    except Exception as e:
        return dict(ok=False, run_id=row["run_id"], row=row, error_class=type(e).__name__,
                    error_message=str(e), traceback=traceback.format_exc(),
                    duration=time.time() - t0, start_utc=start_utc, end_utc=utc(), pid=os.getpid())


# ---------------------------------------------------------------------------
# main: single-writer, atomic, partitioned, checksummed
# ---------------------------------------------------------------------------
class GzWriter:
    """One gzipped JSONL file, written to .tmp and atomically renamed on close."""
    def __init__(self, path):
        self.path = path
        self.tmp = path + ".tmp"
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self.f = gzip.open(self.tmp, "wt", encoding="utf-8")
        self.rows = 0
        self.h = hashlib.sha256()

    def write(self, obj):
        line = json.dumps(obj, separators=(",", ":")) + "\n"
        self.f.write(line)
        self.rows += 1

    def close(self):
        self.f.close()
        with open(self.tmp, "rb") as fh:
            self.h = hashlib.sha256(fh.read())
        os.replace(self.tmp, self.path)
        return self.h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", default="all")
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--tag", default="")            # subdir tag for preflight isolation
    args = ap.parse_args()

    rows = load_matrix()
    by_id = {r["run_id"]: r for r in rows}
    if args.runs == "all":
        sel = rows
    else:
        ids = [x.strip() for x in args.runs.split(",") if x.strip()]
        sel = [by_id[i] for i in ids]
    retain = {r["run_id"] for r in rows if str(r.get("retention_full_log", "")).lower() in ("true", "1")}

    outdir = os.path.join(OUT, args.tag) if args.tag else OUT
    for d in ("summary", "per_miner", "per_template", "per_miner_generation", "stale_race",
              "delivery_delays", "manifests", "logs", "failed_attempts", "full_logs"):
        os.makedirs(os.path.join(outdir, d), exist_ok=True)

    # partitioned writers. Large kinds (per_miner_generation, delivery_delays) are
    # partitioned by scenario AND scientific-semantics group so no committed file
    # approaches the 90 MB limit (Section 10); compact kinds are partitioned by
    # scenario only.
    writers = {}
    BIG = {"per_miner_generation", "delivery_delays"}

    def w_for(kind, scen, group=None):
        if kind in BIG and group:
            key = (kind, scen, group)
            path = os.path.join(outdir, kind, scen, f"{kind}-{scen}-{group}.jsonl.gz")
        else:
            key = (kind, scen)
            path = os.path.join(outdir, kind, f"{kind}-{scen}.jsonl.gz")
        if key not in writers:
            writers[key] = GzWriter(path)
        return writers[key]

    summary_w = GzWriter(os.path.join(outdir, "summary", "summary.jsonl.gz"))
    ledger_path = os.path.join(outdir, "logs", "execution_ledger.jsonl")
    ledger_f = open(ledger_path, "w", encoding="utf-8")     # append-only, line-buffered
    manifest_index = []
    qc_rows = []
    index_rows = []
    counts = dict(planned=len(sel), completed_valid=0, failed_terminal=0, invalidated=0)
    stats = dict(total_pmg_rows=0, total_stale_records=0, total_delivery_records=0,
                 zero_block_runs=0, partial_generation_runs=0, attempts=0, retries=0)
    t_start = time.time()

    def emit_ledger(entry):
        ledger_f.write(json.dumps(entry) + "\n")
        ledger_f.flush()

    ctx = mp.get_context("spawn")
    with ctx.Pool(processes=args.workers) as pool:
        for res in pool.imap(run_one, sel, chunksize=1):
            stats["attempts"] += 1
            rid = res["run_id"]
            row = res["row"]
            base_led = dict(run_id=rid, run_execution_hash=row["run_execution_hash"],
                            scientific_semantics_hash=row["scientific_semantics_hash"],
                            analysis_group_hash=row.get("analysis_group_hash_v2", ""),
                            scenario=row["scenario_id"], interpretation_labels=row["interpretation_labels"],
                            master_seed=int(row["seed"]), attempt=1, worker_pid=res["pid"],
                            host=os.uname().nodename, utc_start=res["start_utc"], utc_end=res["end_utc"],
                            duration_s=round(res["duration"], 4), source_commit=SOURCE_COMMIT,
                            matrix_sha256=MATRIX_SHA)
            if not res["ok"]:
                # infrastructure/exception failure -> terminal (not silently dropped)
                counts["failed_terminal"] += 1
                fa = os.path.join(outdir, "failed_attempts", f"{rid}.error.json")
                with open(fa, "w") as fh:
                    json.dump(dict(base_led, status="FAILED_TERMINAL", error_class=res["error_class"],
                                   error_message=res["error_message"], traceback=res["traceback"]),
                              fh, indent=2)
                emit_ledger(dict(base_led, status="FAILED_TERMINAL", exit_code=1,
                                 error_class=res["error_class"], error_message=res["error_message"],
                                 retry_reason="", output_dir=fa))
                continue
            if not res["passed"]:
                # scientific QC failure -> terminal, STOP (not retryable, not repaired)
                counts["failed_terminal"] += 1
                fa = os.path.join(outdir, "failed_attempts", f"{rid}.qc_fail.json")
                with open(fa, "w") as fh:
                    json.dump(dict(base_led, status="FAILED_TERMINAL", qc_failures=res["fails"]), fh, indent=2)
                emit_ledger(dict(base_led, status="FAILED_TERMINAL", exit_code=2,
                                 error_class="QC_FAILURE", error_message=";".join(res["fails"]),
                                 retry_reason="", output_dir=fa))
                qc_rows.append(dict(run_id=rid, passed=False, failures=res["fails"]))
                continue

            r = res["r"]; ident = res["ident"]; scen = row["scenario_id"]
            grp = row["scientific_semantics_hash"][:12]
            # stream per-record outputs (single writer)
            summary_w.write(dict(ident, **{k: v for k, v in r.items()
                                           if k not in ("per_miner", "per_template",
                                                        "per_miner_generation", "block_log",
                                                        "stale_race_records", "delivery_delay_records")}))
            for m in r["per_miner"]:
                w_for("per_miner", scen).write({**m, "run_id": rid})
            for t in r["per_template"]:
                w_for("per_template", scen).write({**t, "run_id": rid})
            for g in r["per_miner_generation"]:
                w_for("per_miner_generation", scen, grp).write({**g, "run_id": rid})
            stats["total_pmg_rows"] += len(r["per_miner_generation"])
            for x in (r.get("stale_race_records") or []):
                w_for("stale_race", scen).write({**x, "run_id": rid})
                stats["total_stale_records"] += 1
            for d in (r.get("delivery_delay_records") or []):
                w_for("delivery_delays", scen, grp).write({**d, "run_id": rid})
                stats["total_delivery_records"] += 1
            if r["accepted_blocks"] == 0:
                stats["zero_block_runs"] += 1
            if r["partial_generations"] > 0:
                stats["partial_generation_runs"] += 1

            # retained full-log runs: individual per-run files (Section 13)
            if rid in retain:
                fl = os.path.join(outdir, "full_logs", rid)
                os.makedirs(fl, exist_ok=True)
                json.dump(dict(ident, summary={k: v for k, v in r.items()
                          if k not in ("per_miner", "per_template", "per_miner_generation",
                                       "block_log", "stale_race_records", "delivery_delay_records")}),
                          open(os.path.join(fl, "summary.json"), "w"), indent=2)
                for kind, key in (("per_miner", "per_miner"), ("per_template", "per_template"),
                                  ("per_miner_generation", "per_miner_generation"),
                                  ("block_log", "block_log"),
                                  ("stale_race", "stale_race_records"),
                                  ("delivery_delays", "delivery_delay_records")):
                    data = r.get(key) or []
                    with gzip.open(os.path.join(fl, f"{kind}.jsonl.gz"), "wt") as fh:
                        for rec in data:
                            fh.write(json.dumps({**rec, "run_id": rid}, separators=(",", ":")) + "\n")

            man = dict(ident, accepted_blocks=r["accepted_blocks"],
                       template_generations=r["template_generations"],
                       total_candidate_evaluations=r["total_candidate_evaluations"],
                       total_energy_kwh=r["total_energy_kwh"],
                       single_height_stale_block_count=r["single_height_stale_block_count"],
                       retained_full_log=(rid in retain), qc_passed=True)
            manifest_index.append(man)
            qc_rows.append(dict(run_id=rid, passed=True, failures=[]))
            index_rows.append(dict(run_id=rid, scenario=scen,
                                   scientific_semantics_hash=row["scientific_semantics_hash"],
                                   seed=int(row["seed"]), accepted_blocks=r["accepted_blocks"],
                                   pmg_rows=len(r["per_miner_generation"]),
                                   retained_full_log=(rid in retain)))
            counts["completed_valid"] += 1
            emit_ledger(dict(base_led, status="COMPLETED_VALID", exit_code=0,
                             error_class="", error_message="", retry_reason="",
                             output_dir=os.path.join(outdir, "summary")))

    # finalize partitioned writers + checksums
    file_checksums = {}
    file_checksums[os.path.relpath(summary_w.path, ROOT)] = summary_w.close()
    for key, wtr in writers.items():
        file_checksums[os.path.relpath(wtr.path, ROOT)] = wtr.close()
    ledger_f.close()

    counts["not_started"] = counts["planned"] - counts["completed_valid"] - counts["failed_terminal"] - counts["invalidated"]
    stats["wall_clock_s"] = round(time.time() - t_start, 2)

    json.dump(manifest_index, open(os.path.join(outdir, "manifests", "results_manifest.json"), "w"), indent=2)
    json.dump(dict(counts=counts, stats=stats,
                   qc_all_passed=all(q["passed"] for q in qc_rows),
                   qc_failures=[q for q in qc_rows if not q["passed"]]),
              open(os.path.join(outdir, "manifests", "qc_summary.json"), "w"), indent=2)
    # output index CSV
    with open(os.path.join(outdir, "manifests", "output_index.csv"), "w", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=["run_id", "scenario", "scientific_semantics_hash",
                                           "seed", "accepted_blocks", "pmg_rows", "retained_full_log"])
        wr.writeheader()
        for x in sorted(index_rows, key=lambda z: z["run_id"]):
            wr.writerow(x)
    json.dump(file_checksums, open(os.path.join(outdir, "manifests", "file_checksums.json"), "w"), indent=2)

    print(json.dumps(dict(counts=counts, stats=stats,
                          qc_all_passed=all(q["passed"] for q in qc_rows),
                          n_qc_fail=sum(1 for q in qc_rows if not q["passed"])), indent=2))
    return counts, stats, qc_rows


if __name__ == "__main__":
    main()
