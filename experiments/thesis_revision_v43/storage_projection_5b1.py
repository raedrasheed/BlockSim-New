"""Stage 5B1 storage re-estimation from ACTUAL full-loop output.

Measures the on-disk size of a real per-run summary and a real per-run full log
(emitted by the engine), then projects the total footprint of the frozen
Stage-5B2 matrix under the retention policy (all summaries kept; ~1% + one per
scenario/count keep full logs). No fabricated sizes: every byte figure is the
size of a file the engine actually produced.
"""

from __future__ import annotations
import os
import sys
import csv
import json

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)

from experiments.thesis_revision_v43.scenario_engine import EngineConfig, run_scenario
from experiments.thesis_revision_v43 import run_utils

DOCS = os.path.join(ROOT, "docs", "thesis_revision_v43")
RESULTS = os.path.join(ROOT, "results", "thesis_revision_v43", "stage_05b1")
PROBE = os.path.join(RESULTS, "storage_probe")

# representative configs spanning the size range (continuous vs C2, small vs N=500)
PROBES = [
    ("B3_C1_CONTINUOUS_DISJOINT", dict(seed=1, miner_count=100)),
    ("B3_C1_CONTINUOUS_DISJOINT", dict(seed=1, miner_count=500)),
    ("C2", dict(seed=1, miner_count=500, hash_rate_distribution="heterogeneous_moderate",
                allocation_policy="equal", idle_power_ratio=0.1)),
    ("B1", dict(seed=1, miner_count=500)),
]


def measure():
    os.makedirs(PROBE, exist_ok=True)
    summ_sizes, log_sizes = [], []
    rows = []
    for scen, kw in PROBES:
        cfg = EngineConfig(scen, **kw)
        r = run_scenario(cfg, emit_log=True)
        log = r.pop("block_log")
        sp = os.path.join(PROBE, f"{scen}-{kw['miner_count']}.summary.json")
        lp = os.path.join(PROBE, f"{scen}-{kw['miner_count']}.fulllog.json")
        run_utils.atomic_write_json(sp, dict(r, status=run_utils.STATUS_COMPLETED))
        run_utils.atomic_write_json(lp, dict(summary=r, block_log=log,
                                             status=run_utils.STATUS_COMPLETED))
        ss, ls = os.path.getsize(sp), os.path.getsize(lp)
        summ_sizes.append(ss); log_sizes.append(ls)
        rows.append(dict(scenario=scen, miner_count=kw["miner_count"],
                         accepted_blocks=r["accepted_blocks"],
                         summary_bytes=ss, full_log_bytes=ls, log_records=len(log)))
    return summ_sizes, log_sizes, rows


def project(summ_sizes, log_sizes):
    matrix = os.path.join(DOCS, "STAGE_05B1_FINAL_MATRIX.csv")
    mrows = list(csv.DictReader(open(matrix)))
    n_runs = len(mrows)
    n_full = sum(1 for r in mrows if r["retain_full_log"] == "True")
    summ_med = sorted(summ_sizes)[len(summ_sizes) // 2]
    summ_p95 = max(summ_sizes)                       # small probe set -> use max as 95th proxy
    log_med = sorted(log_sizes)[len(log_sizes) // 2]
    log_p95 = max(log_sizes)
    # policy: every run keeps a summary; retained runs additionally keep a full log
    total_expected = n_runs * summ_med + n_full * log_med
    total_p95 = n_runs * summ_p95 + n_full * log_p95
    return dict(
        matrix_runs=n_runs, full_log_retained=n_full,
        summary_bytes=dict(median=summ_med, p95_proxy=summ_p95,
                           min=min(summ_sizes), max=max(summ_sizes)),
        full_log_bytes=dict(median=log_med, p95_proxy=log_p95,
                            min=min(log_sizes), max=max(log_sizes)),
        projected_total_bytes_expected=total_expected,
        projected_total_bytes_p95=total_p95,
        projected_total_mb_expected=round(total_expected / 1e6, 3),
        projected_total_mb_p95=round(total_p95 / 1e6, 3),
        retention_policy="all summaries + (1 per scenario/count and ~1% deterministic) full logs")


def main():
    summ, logs, rows = measure()
    proj = project(summ, logs)
    report = dict(probes=rows, projection=proj)
    run_utils.atomic_write_json(os.path.join(RESULTS, "storage_projection.json"), report)
    print(json.dumps(report, indent=2))
    return report


if __name__ == "__main__":
    main()
