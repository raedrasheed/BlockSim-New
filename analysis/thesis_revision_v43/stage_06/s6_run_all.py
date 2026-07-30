#!/usr/bin/env python3
"""Stage 6 — reproducible orchestrator: run the whole analysis pipeline in order.

  python3 analysis/thesis_revision_v43/stage_06/s6_run_all.py

1. input-integrity gate (blocks on failure)
2. confirmatory + secondary + descriptive analysis
3. tables
4. figures
Deterministic: same inputs + recorded RNG seeds -> identical outputs.
"""
import subprocess
import sys
import os

HERE = os.path.dirname(os.path.abspath(__file__))


def run(mod):
    print(f"\n=== {mod} ===")
    r = subprocess.run([sys.executable, os.path.join(HERE, mod)], cwd=HERE)
    if r.returncode != 0:
        print(f"FAILED: {mod} (rc={r.returncode})")
        sys.exit(r.returncode)


if __name__ == "__main__":
    run("s6_integrity_gate.py")
    run("s6_analysis.py")
    run("s6_tables.py")
    run("s6_figures.py")
    print("\nSTAGE_06_PIPELINE_COMPLETE")
