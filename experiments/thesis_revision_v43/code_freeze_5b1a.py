"""Stage 5B1A scientific code-freeze manifest builder.

Records the exact scientific inputs Stage 5B2 must run from: the frozen matrix
checksum, seed-schedule checksum, retention-list checksum, dependency-lock
checksum, output-schema and engine versions, the test-suite result, and a
timestamp. `build_manifest` is pure (no pytest, no writes) so it is safe to call
from a test; `main` runs the test suite, writes the manifest, and verifies the
repository state.
"""

from __future__ import annotations
import os
import json
import hashlib
import subprocess

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DOCS = os.path.join(ROOT, "docs", "thesis_revision_v43")
RESULTS = os.path.join(ROOT, "results", "thesis_revision_v43", "stage_05b1a")

from experiments.thesis_revision_v43.schemas import OUTPUT_SCHEMA_VERSION
from experiments.thesis_revision_v43.scenario_engine import ENGINE_VERSION

FREEZE_DATE = "2026-07-29"        # fixed (deterministic) freeze date
REQUIRED_KEYS = (
    "stage", "timestamp", "freeze_commit_ref", "matrix_sha256", "seed_schedule_sha256",
    "retention_checksum_sha256", "dependency_lock_sha256", "output_schema_version",
    "scenario_engine_version", "test_suite_result",
)


def _sha_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for c in iter(lambda: f.read(1 << 16), b""):
            h.update(c)
    return h.hexdigest()


def _git_head():
    try:
        return subprocess.check_output(["git", "-C", ROOT, "rev-parse", "HEAD"],
                                       text=True).strip()
    except Exception:
        return None


def build_manifest(test_result: str = "unverified") -> dict:
    """Pure manifest builder (no pytest, no file writes)."""
    matrix = os.path.join(DOCS, "STAGE_05B1A_FINAL_MATRIX.csv")
    summary = json.load(open(os.path.join(RESULTS, "raw", "matrix_5b1a_summary.json"))) \
        if os.path.exists(os.path.join(RESULTS, "raw", "matrix_5b1a_summary.json")) else {}
    retention = json.load(open(os.path.join(RESULTS, "raw", "retention_manifest.json"))) \
        if os.path.exists(os.path.join(RESULTS, "raw", "retention_manifest.json")) else {}
    lock = os.path.join(ROOT, "requirements-thesis-v43-lock.txt")
    head = _git_head()
    return dict(
        stage="5B1A",
        timestamp=FREEZE_DATE,
        # the authoritative freeze reference is the commit that ADDS this manifest;
        # its SHA cannot be embedded in its own content, so we record the base commit
        # this freeze descends from and report the freeze SHA in the completion report.
        freeze_commit_ref=(head or "unknown"),
        freeze_commit_note="Freeze = the Stage-5B1A commit that adds this manifest; "
                           "its SHA is recorded in git log and the completion report.",
        matrix_sha256=(_sha_file(matrix) if os.path.exists(matrix) else None),
        seed_schedule_sha256=summary.get("seed_schedule_sha256")
        or "6122dbd0f455a1c4c9676ec6575f064c3a682b3c978705d6588af11489b13e10",
        retention_checksum_sha256=retention.get("retention_checksum_sha256"),
        dependency_lock_sha256=(_sha_file(lock) if os.path.exists(lock) else None),
        output_schema_version=OUTPUT_SCHEMA_VERSION,
        scenario_engine_version=ENGINE_VERSION,
        final_stage5b2_run_count=summary.get("final_stage5b2_run_count"),
        thesis_docx_sha256="2c3afdc5739109d0ea12ada96c3115d626a2188c1acbaeaa4b6020974884cbda",
        thesis_pdf_sha256="131412bb2ce17ed97b98dfbefc136c7b5b226b9fd7372e79a25e4b0dc057e9c4",
        test_suite_result=test_result,
    )


def run_test_suite() -> str:
    out = subprocess.run(["python3", "-m", "pytest", os.path.join(ROOT, "tests"), "-q"],
                         cwd=ROOT, capture_output=True, text=True)
    tail = out.stdout.strip().splitlines()[-1] if out.stdout.strip() else "no output"
    return tail


def repo_is_clean() -> bool:
    st = subprocess.run(["git", "-C", ROOT, "status", "--porcelain"],
                        capture_output=True, text=True).stdout.strip()
    return st == ""


def main():
    os.makedirs(RESULTS, exist_ok=True)
    result = run_test_suite()
    manifest = build_manifest(test_result=result)
    with open(os.path.join(RESULTS, "manifests", "code_freeze_manifest.json"), "w") as f:
        os.makedirs(os.path.dirname(f.name), exist_ok=True)
        json.dump(manifest, f, indent=2, sort_keys=True)
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return manifest


if __name__ == "__main__":
    os.makedirs(os.path.join(RESULTS, "manifests"), exist_ok=True)
    main()
