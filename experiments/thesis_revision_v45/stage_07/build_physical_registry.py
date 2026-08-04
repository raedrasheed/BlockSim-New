#!/usr/bin/env python3
"""Stage 7 — emit the physical-execution registry and the logical->physical alias map.

The frozen design has 22 logical scenarios x 30 master seeds = 660 logical scenario-seed rows.
A05 and B01 have byte-identical executable configurations, so under each shared master seed
they denote ONE physical execution.  The required counts are therefore:

    logical scenario-seed rows   660
    unique physical executions   630
    A05/B01 alias pairs           30

Each physical execution is executed exactly ONCE.  Both logical rows are then materialised
from the same verified output and the same checksum, each carrying physical_execution_id,
shared_physical_execution and alias_group_id so that provenance is explicit and Stage 8 can
never count one physical observation twice.
"""
from __future__ import annotations

import argparse
import csv
import io
import pathlib

from _common import (BASELINE_COMMIT, ExecutionPaths, build_physical_map,      # noqa: E402
                     executor_run_id, _atomic_write)

PHYS_FIELDS = ["physical_execution_id", "config_sha256", "master_seed", "engine_commit_sha",
               "executor_run_id", "cost_class", "logical_row_count", "logical_run_ids"]
ALIAS_FIELDS = ["run_id", "scenario_id", "master_seed", "seed_index", "pair_id",
                "physical_execution_id", "shared_physical_execution", "alias_group_id",
                "executor_run_id", "materialisation"]


def build(paths: ExecutionPaths = None) -> dict:
    paths = paths or ExecutionPaths()
    m = build_physical_map()
    logical, physical = m["logical"], m["physical"]

    pbuf = io.StringIO(newline="")
    pw = csv.DictWriter(pbuf, fieldnames=PHYS_FIELDS, lineterminator="\n")
    pw.writeheader()
    for pid in sorted(physical):
        members = sorted(physical[pid])
        ex = executor_run_id(members)
        pw.writerow({"physical_execution_id": pid,
                     "config_sha256": logical[ex]["config_sha256"],
                     "master_seed": logical[ex]["master_seed"],
                     "engine_commit_sha": BASELINE_COMMIT,
                     "executor_run_id": ex, "cost_class": logical[ex]["cost_class"],
                     "logical_row_count": len(members),
                     "logical_run_ids": ";".join(members)})

    abuf = io.StringIO(newline="")
    aw = csv.DictWriter(abuf, fieldnames=ALIAS_FIELDS, lineterminator="\n")
    aw.writeheader()
    for rid in sorted(logical):
        L = logical[rid]
        ex = executor_run_id(physical[L["physical_execution_id"]])
        aw.writerow({"run_id": rid, "scenario_id": L["scenario_id"],
                     "master_seed": L["master_seed"], "seed_index": L["seed_index"],
                     "pair_id": L["pair_id"],
                     "physical_execution_id": L["physical_execution_id"],
                     "shared_physical_execution": str(L["shared_physical_execution"]).lower(),
                     "alias_group_id": L["alias_group_id"], "executor_run_id": ex,
                     "materialisation": ("EXECUTED" if rid == ex else
                                         "MATERIALISED_FROM_SHARED_PHYSICAL_EXECUTION")})

    paths.root.mkdir(parents=True, exist_ok=True)
    _atomic_write(paths.physical_registry, pbuf.getvalue())
    _atomic_write(paths.alias_map, abuf.getvalue())
    shared = [p for p, v in physical.items() if len(v) > 1]
    return {"logical_rows": len(logical), "physical_executions": len(physical),
            "alias_pairs": len(shared),
            "physical_registry": str(paths.physical_registry),
            "alias_map": str(paths.alias_map)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default=None)
    a = ap.parse_args(argv)
    r = build(ExecutionPaths(a.root) if a.root else None)
    print(f"logical scenario-seed rows : {r['logical_rows']}")
    print(f"unique physical executions : {r['physical_executions']}")
    print(f"alias pairs                : {r['alias_pairs']}")
    print(f"wrote {r['physical_registry']}\n      {r['alias_map']}")
    assert r["logical_rows"] == 660 and r["physical_executions"] == 630 \
        and r["alias_pairs"] == 30, "the frozen counts do not hold"
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
