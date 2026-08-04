#!/usr/bin/env python3
"""Stage 6 — regenerate every generated artefact, in dependency order.

One command so the freeze cannot be assembled by hand.  The order matters: the completion
report reads the pilot report's merged view, and the manifest checksums everything else, so
the manifest must be produced last.

    python experiments/thesis_revision_v45/stage_06/regenerate_all.py            # write
    python experiments/thesis_revision_v45/stage_06/regenerate_all.py --check    # verify only

``--check`` runs every generator in its own ``--check`` mode, so a stale committed artefact is
a failure rather than a silent overwrite.

Artefacts, in the order produced:

    1  seed registry                       generate_seed_registry.py
    2  confirmatory matrix                 generate_confirmatory_matrix.py
    3  exploratory matrix                        "
    4  frozen confirmatory configs               "
    5  confirmatory run registry                 "
    6  hypotheses JSON and Markdown        generate_outcome_dictionary.py
    7  outcome dictionary                        "
    8  pilot matrix and pilot report       generate_pilot_report.py
    9  runtime and archive plan                  "
   10  Stage-7 execution plan              (static deliverable; verified, not generated)
   11  environment lock                    generate_freeze_manifest.py
   12  completion report                   generate_completion_report.py
   13  freeze-candidate manifest           generate_freeze_manifest.py

This script generates nothing itself; it only sequences the generators, so there is exactly one
implementation of every artefact.
"""
from __future__ import annotations

import argparse
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
DOCS = REPO_ROOT / "docs" / "thesis_revision_v45" / "stage_06"

#: (script, label) in dependency order.  The manifest is last: it checksums the others.
STEPS = [
    ("generate_seed_registry.py", "seed registry"),
    ("generate_confirmatory_matrix.py",
     "confirmatory matrix, exploratory matrix, frozen configs, run registry"),
    ("generate_outcome_dictionary.py", "hypotheses JSON/MD and outcome dictionary"),
    ("generate_pilot_report.py", "pilot matrix, pilot report, runtime and archive plan"),
    ("generate_completion_report.py", "completion report"),
    ("generate_freeze_manifest.py", "environment lock and freeze-candidate manifest"),
]

#: Deliverables that are authored rather than generated.  They are verified to exist, so a
#: missing one fails here instead of surfacing later as a manifest gap.
STATIC = ["STAGE_06_PREREGISTRATION.md", "STAGE_06_ANALYSIS_PLAN.md",
          "STAGE_06_PILOT_PLAN.md", "STAGE_06_STAGE7_EXECUTION_PLAN.md",
          "STAGE_06_EXCLUSION_RETENTION_POLICY.md", "STAGE_06_DECISION_LOG.md",
          "STAGE_06_D04_FAULT_SCHEDULE_FREEZE.md"]


def run(script: str, check: bool) -> int:
    cmd = [sys.executable, str(HERE / script)] + (["--check"] if check else [])
    r = subprocess.run(cmd, capture_output=True, text=True)
    out = (r.stdout + r.stderr).strip()
    for line in out.splitlines():
        print(f"      {line}")
    return r.returncode


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true",
                    help="verify every artefact matches its regeneration; write nothing")
    args = ap.parse_args(argv)

    missing = [f for f in STATIC if not (DOCS / f).exists()]
    if missing:
        print(f"FAIL: authored deliverable(s) missing: {missing}", file=sys.stderr)
        return 1
    print(f"[0/{len(STEPS)}] {len(STATIC)} authored deliverables present")

    failed = []
    for i, (script, label) in enumerate(STEPS, start=1):
        verb = "verifying" if args.check else "generating"
        print(f"[{i}/{len(STEPS)}] {verb} {label}")
        if run(script, args.check):
            failed.append(script)

    if failed:
        print(f"\nFAIL: {len(failed)} generator(s) reported an error: {failed}",
              file=sys.stderr)
        return 1
    print(f"\nOK: all {len(STEPS)} generators "
          f"{'verified' if args.check else 'regenerated'} successfully")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
