#!/usr/bin/env python3
"""Stage 6 — environment lock and scientific-freeze candidate manifest.

Emits:
    docs/thesis_revision_v45/stage_06/STAGE_06_ENVIRONMENT_LOCK.json
    docs/thesis_revision_v45/stage_06/STAGE_06_FREEZE_CANDIDATE_MANIFEST.sha256

The manifest checksums, in `sha256sum -c` format relative to the repository root:

    * every accepted executable source module
    * every accepted test file
    * every Stage-6 experiment script
    * every pilot configuration and pilot artefact
    * every frozen confirmatory configuration
    * the seed registry
    * both matrices
    * every analysis and retention document
    * every Stage-6 deliverable and the Stage-6 test suite
    * the CI workflow

It MUST NOT include confirmatory data.  There is none: `confirmatory/` holds configurations and
registries only, which the manifest covers, and `validate_preregistration.py` check [9] fails
the build if any run output appears there.

Usage:
    python experiments/thesis_revision_v45/stage_06/generate_freeze_manifest.py [--check]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import platform
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
DOCS = REPO_ROOT / "docs" / "thesis_revision_v45" / "stage_06"
MANIFEST = DOCS / "STAGE_06_FREEZE_CANDIDATE_MANIFEST.sha256"
ENVLOCK = DOCS / "STAGE_06_ENVIRONMENT_LOCK.json"

ENGINE_COMMIT = "fb8a34d63d9369336d5c1e7aeecdfcf8263920b2"

#: Globs relative to the repository root, in a fixed order.  The manifest itself and the
#: environment lock are excluded (a file cannot checksum itself).
INCLUDE = [
    "Models/PoCol/stage2/*.py",
    "tests/thesis_revision_v45/stage2/*.py",
    "tests/thesis_revision_v45/stage_06/*.py",
    "experiments/thesis_revision_v45/stage_06/*.py",
    "experiments/thesis_revision_v45/stage_06/pilot/*",
    "experiments/thesis_revision_v45/stage_06/confirmatory/*.csv",
    "experiments/thesis_revision_v45/stage_06/confirmatory/*.md",
    "experiments/thesis_revision_v45/stage_06/confirmatory/frozen_configs/*.json",
    "docs/thesis_revision_v45/stage_06/*.md",
    "docs/thesis_revision_v45/stage_06/*.csv",
    "docs/thesis_revision_v45/stage_06/*.json",
    ".github/workflows/stage6-pocol-preregistration.yml",
]

# Only the manifest itself is excluded — a file cannot checksum itself.  The environment lock
# IS covered: it is written before the manifest is computed.
EXCLUDE_NAMES = {"STAGE_06_FREEZE_CANDIDATE_MANIFEST.sha256"}


def collect() -> list:
    paths = []
    for pattern in INCLUDE:
        for p in sorted(REPO_ROOT.glob(pattern)):
            if not p.is_file() or "__pycache__" in p.parts:
                continue
            if p.name in EXCLUDE_NAMES:
                continue
            paths.append(p)
    # deterministic, de-duplicated total order
    return sorted(set(paths), key=lambda p: str(p.relative_to(REPO_ROOT)))


def environment_lock() -> str:
    try:
        import pytest
        pytest_version = pytest.__version__
    except Exception:                                   # pragma: no cover
        pytest_version = "unavailable"
    try:
        freeze = subprocess.run([sys.executable, "-m", "pip", "freeze"],
                                capture_output=True, text=True, timeout=120)
        deps = sorted(l.strip() for l in freeze.stdout.splitlines() if l.strip())
    except Exception:                                   # pragma: no cover
        deps = []
    payload = {
        "stage": "STAGE_06",
        "engine_commit_sha": ENGINE_COMMIT,
        "stage6_commit_sha": "RECORDED_POST_COMMIT_IN_STAGE_06_COMPLETION_REPORT",
        "result_schema_version": "stage5c.1",
        "python_version": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "pytest_version": pytest_version,
        "os_system": platform.system(),
        "os_release": platform.release(),
        "os_machine": platform.machine(),
        "dependency_list": deps,
        "accepted_test_count": 195,
        "confirmatory_scenarios": 21,
        "confirmatory_master_seeds": 30,
        "expected_stage7_physical_runs": 630,
        "contains_confirmatory_data": False,
    }
    return json.dumps(payload, indent=1, sort_keys=True) + "\n"


def manifest_text(paths: list) -> str:
    lines = [
        "# Stage 6 — scientific-freeze candidate manifest",
        f"# engine commit: {ENGINE_COMMIT}",
        "# format: sha256sum -c, paths relative to the repository root",
        "# contains NO confirmatory data",
        "#",
        "# verify with:",
        "#   sha256sum -c docs/thesis_revision_v45/stage_06/"
        "STAGE_06_FREEZE_CANDIDATE_MANIFEST.sha256",
        "",
    ]
    for p in paths:
        digest = hashlib.sha256(p.read_bytes()).hexdigest()
        lines.append(f"{digest}  {p.relative_to(REPO_ROOT)}")
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true",
                    help="verify every manifest entry without rewriting it")
    args = ap.parse_args(argv)

    if args.check:
        if not MANIFEST.exists():
            print(f"FAIL: {MANIFEST} does not exist", file=sys.stderr)
            return 1
        bad, n = [], 0
        for line in MANIFEST.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            digest, _, rel = line.partition("  ")
            p = REPO_ROOT / rel
            n += 1
            if not p.exists():
                bad.append(f"{rel}: missing")
            elif hashlib.sha256(p.read_bytes()).hexdigest() != digest:
                bad.append(f"{rel}: digest mismatch")
        conf_data = [line.split("  ", 1)[1] for line in MANIFEST.read_text().splitlines()
                     if "/confirmatory/" in line and "frozen_configs" not in line
                     and not line.strip().startswith("#")
                     and not line.endswith(("README_DO_NOT_RUN_IN_STAGE6.md",
                                            "confirmatory_run_registry.csv"))]
        if conf_data:
            bad.append("manifest contains confirmatory data: " + ", ".join(conf_data))
        if bad:
            print(f"FAIL: {len(bad)} manifest problem(s):", file=sys.stderr)
            for b in bad:
                print("  " + b, file=sys.stderr)
            return 1
        print(f"OK: all {n} manifest entries verify")
        return 0

    ENVLOCK.parent.mkdir(parents=True, exist_ok=True)
    ENVLOCK.write_text(environment_lock())
    paths = collect()
    MANIFEST.write_text(manifest_text(paths))
    print(f"wrote {ENVLOCK.relative_to(REPO_ROOT)}")
    print(f"wrote {MANIFEST.relative_to(REPO_ROOT)} covering {len(paths)} files")
    print(f"  manifest sha256: "
          f"{hashlib.sha256(MANIFEST.read_bytes()).hexdigest()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
