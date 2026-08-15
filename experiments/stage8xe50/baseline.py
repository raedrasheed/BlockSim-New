"""Stage 8X-E50 — protected-artifact SHA-256 baseline.

    python -m experiments.stage8xe50.baseline --record     # create the baseline
    python -m experiments.stage8xe50.baseline --check      # verify nothing changed

Stage 8X-E50 must not modify Stage 8X, Stage 8Y, Stage 8Z, any earlier experiment, any thesis document,
any legacy model, test or result. This module takes a SHA-256 fingerprint of every
such artifact, stores it under ``experiments/stage8xe50/manifests/``, and re-verifies
it after execution.

Anything under ``experiments/stage8xe50/`` is deliberately excluded: that is the only
tree Stage 8X-E50 is permitted to write to.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from typing import Dict, List

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
MANIFEST_DIR = os.path.join(HERE, "manifests")
BASELINE_FILE = os.path.join(MANIFEST_DIR, "stage8xe50_protected_baseline.json")

#: Everything Stage 8X-E50 must leave byte-identical.
PROTECTED_PATHS: List[str] = [
    "Models",
    "results",
    "docs",
    "tests",
    "experiments/stage8x",
    "experiments/stage8xnr",
    "experiments/stage8y",
    "experiments/stage8z",
    "experiments/_common.py",
    "experiments/run_all_revision_experiments.py",
    "experiments/run_carbon_gamma_sensitivity.py",
    "experiments/run_communication_energy_analysis.py",
    "experiments/run_pos_validator_scaling.py",
    "experiments/run_pow_miner_scaling.py",
    "experiments/run_pow_price_sensitivity.py",
    "InputsConfig.py",
    "Main.py",
    "Statistics.py",
    "Scheduler.py",
    "Event.py",
    "README.md",
]

#: Root-level thesis / manuscript artifacts are matched by extension.
PROTECTED_ROOT_SUFFIXES = (".xlsx", ".docx", ".pdf")


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def protected_digest() -> Dict[str, str]:
    digests: Dict[str, str] = {}

    def add(path: str) -> None:
        digests[os.path.relpath(path, REPO_ROOT)] = sha256_file(path)

    for rel in PROTECTED_PATHS:
        abs_path = os.path.join(REPO_ROOT, rel)
        if os.path.isfile(abs_path):
            add(abs_path)
        elif os.path.isdir(abs_path):
            for dirpath, dirs, files in os.walk(abs_path):
                dirs[:] = [d for d in dirs if d != "__pycache__"]
                for fn in sorted(files):
                    if fn.endswith(".pyc"):
                        continue
                    add(os.path.join(dirpath, fn))

    for fn in sorted(os.listdir(REPO_ROOT)):
        p = os.path.join(REPO_ROOT, fn)
        if os.path.isfile(p) and fn.endswith(PROTECTED_ROOT_SUFFIXES):
            add(p)

    return dict(sorted(digests.items()))


def record() -> Dict:
    os.makedirs(MANIFEST_DIR, exist_ok=True)
    digests = protected_digest()
    body = {
        "experiment": "Stage8XE50",
        "recorded_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "protected_paths": PROTECTED_PATHS,
        "protected_root_suffixes": list(PROTECTED_ROOT_SUFFIXES),
        "file_count": len(digests),
        "files": digests,
    }
    body["baseline_sha256"] = hashlib.sha256(
        json.dumps(digests, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    with open(BASELINE_FILE, "w", encoding="utf-8") as fh:
        json.dump(body, fh, indent=2, sort_keys=True)
        fh.write("\n")
    return body


def check() -> Dict:
    if not os.path.exists(BASELINE_FILE):
        return {"status": "NO-BASELINE", "changed": [], "added": [], "removed": [],
                "file_count": 0}
    with open(BASELINE_FILE, encoding="utf-8") as fh:
        stored = json.load(fh)
    base = stored["files"]
    now = protected_digest()
    changed = sorted(k for k in set(base) & set(now) if base[k] != now[k])
    added = sorted(set(now) - set(base))
    removed = sorted(set(base) - set(now))
    ok = not (changed or added or removed)
    return {
        "status": "OK" if ok else "VIOLATION",
        "file_count": len(now),
        "baseline_file_count": stored["file_count"],
        "baseline_sha256": stored["baseline_sha256"],
        "current_sha256": hashlib.sha256(
            json.dumps(now, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
        "changed": changed, "added": added, "removed": removed,
        "recorded_utc": stored["recorded_utc"],
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Stage 8X-E50 protected-artifact baseline")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--record", action="store_true")
    g.add_argument("--check", action="store_true")
    args = ap.parse_args(argv)

    if args.record:
        body = record()
        print(f"recorded {body['file_count']} protected files")
        print(f"baseline_sha256 = {body['baseline_sha256']}")
        print(f"-> {BASELINE_FILE}")
        return 0

    res = check()
    print(f"protected-artifact check: {res['status']} "
          f"({res.get('file_count', 0)} files, baseline recorded {res.get('recorded_utc')})")
    print(f"baseline_sha256 = {res.get('baseline_sha256')}")
    print(f"current_sha256  = {res.get('current_sha256')}")
    for kind in ("changed", "added", "removed"):
        for f in res.get(kind, []):
            print(f"  {kind.upper()}: {f}")
    return 0 if res["status"] == "OK" else 1


if __name__ == "__main__":
    sys.exit(main())
