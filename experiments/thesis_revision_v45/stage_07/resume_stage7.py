#!/usr/bin/env python3
"""Stage 7 — resume.  Re-executes ONLY PENDING, RUNNING (interrupted) and
FAILED_INFRASTRUCTURE run IDs.

A COMPLETED or RERUN_COMPLETED run is never re-executed.  A FAILED_MODEL run is never retried:
it stops the frozen execution by design.  An infrastructure retry reuses the identical
(scenario_id, master_seed) pair and the identical frozen configuration — no replacement seed is
ever drawn, and the seed registry is never extended.

    python resume_stage7.py --preflight host.json [--dry-run]
"""
from __future__ import annotations

import argparse
import pathlib
import sys

from _common import (FAILED_INFRASTRUCTURE, FAILED_MODEL, PENDING, RUNNING,    # noqa: E402
                     Registry, RESUMABLE, TERMINAL_SUCCESS)
import run_stage7                                                              # noqa: E402


def plan(reg: Registry) -> dict:
    rows = reg.read()
    out = {"resumable": [], "already_done": [], "blocked_model": []}
    for r in rows:
        if r["run_status"] in TERMINAL_SUCCESS:
            out["already_done"].append(r["run_id"])
        elif r["run_status"] == FAILED_MODEL:
            out["blocked_model"].append(r["run_id"])
        elif r["run_status"] in RESUMABLE:
            out["resumable"].append(r["run_id"])
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--preflight", required=True)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    reg = Registry()
    if not reg.path.exists():
        print("no registry yet — run run_stage7.py first")
        return 1
    p = plan(reg)
    print(f"already terminal-success : {len(p['already_done'])}  (never re-executed)")
    print(f"resumable                : {len(p['resumable'])}")
    print(f"blocked by model failure : {len(p['blocked_model'])}")
    if p["blocked_model"]:
        print("A model/scientific failure is recorded. The frozen execution is stopped and "
              "the engine must NOT be modified. Resume is refused.")
        return 3
    if a.dry_run:
        for rid in p["resumable"][:8]:
            print(f"  would resume {rid}")
        return 0
    return run_stage7.main(["--preflight", a.preflight])


if __name__ == "__main__":
    raise SystemExit(main())
