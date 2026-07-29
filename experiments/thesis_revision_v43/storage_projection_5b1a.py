"""Stage 5B1A storage re-measurement over the EXPANDED per-run artifact set:
run summary + per-miner summary + per-template summary + manifest + stdout/stderr
log + retained full block-log. Uncompressed and gzip-compressed sizes are
measured from files the engine actually produced. Driven by validate_5b1a with a
shared run counter (100-run cap). Nothing here fabricates a size.
"""

from __future__ import annotations
import os
import csv
import gzip
import json

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DOCS = os.path.join(ROOT, "docs", "thesis_revision_v43")
RESULTS = os.path.join(ROOT, "results", "thesis_revision_v43", "stage_05b1a")
PROBE_DIR = os.path.join(RESULTS, "storage_probe")

from experiments.thesis_revision_v43.scenario_engine import EngineConfig
from experiments.thesis_revision_v43 import run_utils

# 9 representative configurations x {N=100, N=500} (Section 8)
PROBE_SPECS = [
    ("B0", {}),
    ("B1", {}),
    ("B2", {}),
    ("B3_C1_CONTINUOUS_DISJOINT", {}),
    ("C2", dict(allocation_policy="equal", idle_power_ratio=0.3)),                       # homogeneous
    ("C2", dict(hash_rate_distribution="heterogeneous_moderate", allocation_policy="equal", idle_power_ratio=0.1)),
    ("C2", dict(hash_rate_distribution="heterogeneous_moderate", allocation_policy="weighted", idle_power_ratio=0.1)),
    ("B3_C1_CONTINUOUS_DISJOINT", dict(propagation_delay_mean_s=60.0)),                  # high delay
    ("B3_C1_CONTINUOUS_DISJOINT", dict(inactive_miner_fraction=0.30)),                   # high inactivity
]
PROBE_TAGS = ["B0", "B1", "B2", "B3_C1", "C2_hom", "C2_het_equal", "C2_het_weighted",
              "high_delay", "high_inactivity"]


def _gz_size(path):
    with open(path, "rb") as f:
        return len(gzip.compress(f.read(), 6))


def measure(runner):
    """runner(cfg, tag, emit_log=True, emit_detail=True) -> result dict (persists a
    summary and counts toward the shared cap). Returns probe rows."""
    os.makedirs(PROBE_DIR, exist_ok=True)
    rows = []
    for (scen, kw), tag in zip(PROBE_SPECS, PROBE_TAGS):
        for N in (100, 500):
            cfg = EngineConfig(scen, seed=1, miner_count=N, **kw)
            r = runner(cfg, f"storage-{tag}-{N}", emit_log=True, emit_detail=True)
            block_log = r.pop("block_log", [])
            per_miner = r.pop("per_miner", [])
            per_template = r.pop("per_template", [])
            base = f"{tag}-{N}"
            files = {}
            files["summary"] = _write(base, "summary", dict(r, status=run_utils.STATUS_COMPLETED))
            files["per_miner"] = _write(base, "per_miner", per_miner)
            files["per_template"] = _write(base, "per_template", per_template)
            files["manifest"] = _write(base, "manifest", dict(
                run_id=base, status=run_utils.STATUS_COMPLETED,
                output_schema_version=r["output_schema_version"], seed=1, scenario=scen))
            files["full_log"] = _write(base, "fulllog", block_log)
            # a small representative stdout/stderr log
            logtxt = os.path.join(PROBE_DIR, f"{base}.stdout.log")
            with open(logtxt, "w") as f:
                f.write(f"[run {base}] scenario={scen} N={N} accepted={r['accepted_blocks']} "
                        f"energy_kwh={r['total_energy_kwh']:.9f}\n")
            files["stdout_log"] = logtxt
            row = dict(scenario=scen, tag=tag, miner_count=N,
                       accepted_blocks=r["accepted_blocks"],
                       per_miner_rows=len(per_miner), per_template_rows=len(per_template))
            for art, path in files.items():
                row[f"{art}_bytes"] = os.path.getsize(path)
                row[f"{art}_gz_bytes"] = _gz_size(path)
            row["total_uncompressed_bytes"] = sum(row[f"{a}_bytes"] for a in files)
            row["total_gz_bytes"] = sum(row[f"{a}_gz_bytes"] for a in files)
            rows.append(row)
    return rows


def _write(base, art, obj):
    path = os.path.join(PROBE_DIR, f"{base}.{art}.json")
    run_utils.atomic_write_json(path, obj)
    return path


def _pct(sorted_vals, q):
    if not sorted_vals:
        return 0
    import math
    idx = min(len(sorted_vals) - 1, int(math.ceil(q * len(sorted_vals))) - 1)
    return sorted_vals[max(idx, 0)]


def project(rows, matrix_path):
    """Project total footprint of the frozen matrix under the retention policy:
    every run keeps summary + per-miner + per-template + manifest + stdout log;
    retained runs additionally keep the full block-log."""
    mrows = list(csv.DictReader(open(matrix_path)))
    n_runs = len(mrows)
    n_full = sum(1 for r in mrows if r.get("retention_full_log") == "True")

    # per-run bytes EXCLUDING the full log (kept for every run)
    always = ["summary", "per_miner", "per_template", "manifest", "stdout_log"]
    per_run_unc = sorted(sum(r[f"{a}_bytes"] for a in always) for r in rows)
    per_run_gz = sorted(sum(r[f"{a}_gz_bytes"] for a in always) for r in rows)
    full_unc = sorted(r["full_log_bytes"] for r in rows)
    full_gz = sorted(r["full_log_gz_bytes"] for r in rows)

    def stat(vals):
        return dict(median=vals[len(vals) // 2], p95=_pct(vals, 0.95),
                    max=vals[-1], min=vals[0])

    exp_unc = n_runs * stat(per_run_unc)["median"] + n_full * stat(full_unc)["median"]
    exp_gz = n_runs * stat(per_run_gz)["median"] + n_full * stat(full_gz)["median"]
    p95_unc = n_runs * stat(per_run_unc)["p95"] + n_full * stat(full_unc)["p95"]
    p95_gz = n_runs * stat(per_run_gz)["p95"] + n_full * stat(full_gz)["p95"]

    return dict(
        matrix_runs=n_runs, full_logs_retained=n_full,
        per_run_uncompressed_bytes=stat(per_run_unc),
        per_run_gz_bytes=stat(per_run_gz),
        full_log_uncompressed_bytes=stat(full_unc),
        full_log_gz_bytes=stat(full_gz),
        by_artifact_type_median_bytes={
            a: sorted(r[f"{a}_bytes"] for r in rows)[len(rows) // 2]
            for a in ("summary", "per_miner", "per_template", "manifest", "stdout_log", "full_log")},
        projected_final_bytes_expected=exp_unc,
        projected_final_bytes_p95=p95_unc,
        projected_final_gz_bytes_expected=exp_gz,
        projected_final_mb_expected=round(exp_unc / 1e6, 3),
        projected_final_mb_p95=round(p95_unc / 1e6, 3),
        projected_final_gz_mb_expected=round(exp_gz / 1e6, 3),
        # temporary storage: all runs keep a full log until retention prunes ->
        # worst-case every run's full log co-resident
        projected_temporary_mb_expected=round(
            (n_runs * (stat(per_run_unc)["median"] + stat(full_unc)["median"])) / 1e6, 3),
        retention_policy="every run keeps summary+per_miner+per_template+manifest+stdout; "
                         "retained runs additionally keep the full block-log")


def write_report(rows, matrix_path):
    proj = project(rows, matrix_path)
    report = dict(probes=rows, projection=proj)
    run_utils.atomic_write_json(os.path.join(RESULTS, "storage_projection_5b1a.json"), report)
    return report
