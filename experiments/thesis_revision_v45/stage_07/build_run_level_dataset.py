#!/usr/bin/env python3
"""Stage 7 — build the final run-level dataset: exactly ONE inferential row per physical run.

The inferential unit is one physical run under one master seed.  Rounds, miners, blocks,
transactions and evaluation intervals are NOT independent observations and never become rows.

NA is preserved exactly as produced.  It is never imputed as zero.  Zero-block runs are
retained as data.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import lzma
import pathlib

from _common import (ExecutionPaths, Registry, TERMINAL_SUCCESS,               # noqa: E402
                     build_physical_map, frozen_rows, _atomic_write)

IDENTITY = ["run_id", "scenario_id", "block_id", "master_seed", "seed_index", "pair_id",
            "paired_control_id", "cost_class", "run_status", "config_sha256",
            "engine_commit_sha", "attempt", "wall_clock_seconds",
            "physical_execution_id", "shared_physical_execution", "alias_group_id",
            "materialised_from_run_id", "raw_reclaimed", "raw_sha256",
            "compressed_sha256", "archive_verified", "exception_type", "exception_detail"]
#: Preregistered run-level outcomes the accepted adapter does not emit; the worker computes
#: them from the RunContext before serialisation, so they are REAL values here, never NA
#: placeholders standing in for "we forgot to compute it".
DERIVED = ["median_round_duration", "post_round_evaluation_record_count",
           "post_round_evaluation_nonce_count", "evaluation_missing_terminal_time_count",
           "nonterminal_activation_request_count", "maximum_energy_identity_residual_j",
           "maximum_residency_partition_residual_s", "round_duration_count"]
INTEGRITY = ["duplicate_nonce_count", "post_round_evaluation_count",
             "nonterminal_lease_count", "nonterminal_reassignment_request_count",
             "physical_frontier_rewind_count", "work_reward_union_residual",
             "coverage_gap_nonce_count", "uncovered_nonce_count",
             "incentive_reconciliation_residual", "residency_reconciles"]


def load_payload(physical_id: str, paths) -> dict | None:
    x = paths.archive / f"{physical_id}.json.xz"
    if x.exists():
        return json.loads(lzma.decompress(x.read_bytes()).decode())
    return None


def build() -> tuple:
    import scenarios as S                                                      # noqa: PLC0415
    import generate_confirmatory_matrix as GCM                                 # noqa: PLC0415
    srows = {r["scenario_id"]: r for r in S.confirmatory_rows()}
    outcomes = set()
    for m in (GCM.PRIMARY_OUTCOMES, GCM.SECONDARY_OUTCOMES):
        for v in m.values():
            outcomes |= {x for x in v.split(";") if x and x != "NONE"}
    outcomes = sorted(outcomes)

    paths = ExecutionPaths()
    m = build_physical_map()
    reg = {r["run_id"]: r for r in Registry(paths.registry).read()}
    rows = []
    for fr in frozen_rows():
        rid = fr["run_id"]
        st = reg.get(rid, {})
        srow = srows[fr["scenario_id"]]
        row = {k: "" for k in
               IDENTITY + outcomes + DERIVED + INTEGRITY + ["zero_block_indicator"]}
        row.update({"run_id": rid, "scenario_id": fr["scenario_id"],
                    "block_id": fr.get("block_id", ""), "master_seed": fr["master_seed"],
                    "seed_index": fr["seed_index"], "pair_id": fr["pair_id"],
                    "paired_control_id": srow["paired_control_id"],
                    "cost_class": st.get("cost_class", ""),
                    "run_status": st.get("run_status", "PENDING")})
        for k in ("config_sha256", "engine_commit_sha", "attempt", "wall_clock_seconds",
                  "materialised_from_run_id", "raw_reclaimed", "raw_sha256",
                  "compressed_sha256", "archive_verified", "exception_type",
                  "exception_detail"):
            row[k] = st.get(k, "")
        # The physical identity is a deterministic property of the FROZEN design, so it is
        # always present — even for a row that has not executed yet. Stage 8 can therefore
        # always deduplicate, whatever the execution state.
        L = m["logical"][rid]
        row["physical_execution_id"] = (st.get("physical_execution_id")
                                        or L["physical_execution_id"])
        row["shared_physical_execution"] = (st.get("shared_physical_execution")
                                            or str(L["shared_physical_execution"]).lower())
        row["alias_group_id"] = st.get("alias_group_id") or L["alias_group_id"]
        if st.get("run_status") in TERMINAL_SUCCESS:
            # read ONLY the verified existing artefact: the raw file was reclaimed
            p = load_payload(st.get("physical_execution_id")
                             or m["logical"][rid]["physical_execution_id"], paths)
            if p:
                res = p["results"]
                for name in outcomes:
                    v = res.get(name, "NA")
                    row[name] = "NA" if v is None else v      # NA preserved, never imputed
                for name in INTEGRITY:
                    v = res.get(name, "NA")
                    row[name] = "NA" if v is None else v
                row["zero_block_indicator"] = int(res.get("rounds_accepted", -1) == 0)
                d = p.get("derived", {})
                for name in DERIVED:
                    if name == "round_duration_count":
                        row[name] = len(d.get("round_duration_values", []))
                    else:
                        v = d.get(name, "NA")
                        row[name] = "NA" if v is None else v
        else:
            for name in outcomes + DERIVED + INTEGRITY + ["zero_block_indicator"]:
                row[name] = "NA"                              # not executed: NA, not zero
        rows.append(row)
    return rows, IDENTITY + ["zero_block_indicator"] + outcomes + DERIVED + INTEGRITY


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)
    rows, fields = build()
    buf = io.StringIO(newline="")
    w = csv.DictWriter(buf, fieldnames=fields, lineterminator="\n")
    w.writeheader()
    for r in rows:
        w.writerow(r)
    dest = pathlib.Path(a.out) if a.out else (ExecutionPaths().run_level
                                             / "stage07_run_level.csv")
    _atomic_write(dest, buf.getvalue())
    done = sum(1 for r in rows if r["run_status"] in TERMINAL_SUCCESS)
    zb = sum(1 for r in rows if r["zero_block_indicator"] == 1)
    print(f"wrote {dest}: {len(rows)} rows (one per physical run), {len(fields)} columns")
    pids = {r["physical_execution_id"] for r in rows if r["physical_execution_id"]}
    shared = sum(1 for r in rows if str(r["shared_physical_execution"]).lower() == "true")
    print(f"  terminal-success rows {done}; zero-block runs retained {zb}; "
          f"unique run_ids {len({r['run_id'] for r in rows})}; "
          f"physical executions {len(pids)}; alias rows {shared}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
