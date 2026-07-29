"""Stage 5B1B internal freeze-INPUT manifest.

Created BEFORE the final commit. It records the scientific inputs to be frozen and
the INTENDED annotated-tag name, but makes NO claim to contain the SHA of the
commit that will contain it (a file cannot reliably self-reference its own commit
SHA). The authoritative commit SHA and annotated-tag object SHA are recorded in the
external freeze attestation (the annotated Git tag) AFTER the commit exists.
"""

from __future__ import annotations
import os
import json
import hashlib
import subprocess

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DOCS = os.path.join(ROOT, "docs", "thesis_revision_v43")
RESULTS = os.path.join(ROOT, "results", "thesis_revision_v43", "stage_05b1b")

from experiments.thesis_revision_v43.schemas import OUTPUT_SCHEMA_VERSION
from experiments.thesis_revision_v43.scenario_engine import ENGINE_VERSION

INTENDED_FREEZE_TAG = "thesis-v43-stage5b2-freeze-1"
THESIS_DOCX_SHA = "2c3afdc5739109d0ea12ada96c3115d626a2188c1acbaeaa4b6020974884cbda"
THESIS_PDF_SHA = "131412bb2ce17ed97b98dfbefc136c7b5b226b9fd7372e79a25e4b0dc057e9c4"

REQUIRED_KEYS = (
    "stage", "matrix_sha256", "seed_schedule_sha256", "retention_checksum_sha256",
    "dependency_lock_sha256", "scenario_engine_version", "output_schema_version",
    "test_suite_result", "thesis_docx_sha256", "thesis_pdf_sha256",
    "intended_freeze_tag", "self_reference_note",
)
# a field asserting the manifest does NOT claim its own commit SHA
SELF_REFERENCE_NOTE = ("This internal manifest does NOT contain the SHA of the commit "
                       "that contains it. The final commit SHA and annotated-tag object "
                       "SHA are recorded externally in the annotated tag "
                       f"'{INTENDED_FREEZE_TAG}' created after this commit.")


def _sha_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for c in iter(lambda: f.read(1 << 16), b""):
            h.update(c)
    return h.hexdigest()


def build_freeze_inputs(test_result: str = "unverified") -> dict:
    matrix = os.path.join(DOCS, "STAGE_05B1B_FINAL_MATRIX.csv")
    summary_path = os.path.join(RESULTS, "raw", "matrix_5b1b_summary.json")
    summary = json.load(open(summary_path)) if os.path.exists(summary_path) else {}
    lock = os.path.join(ROOT, "requirements-thesis-v43-lock.txt")
    return dict(
        stage="5B1B",
        matrix_sha256=(_sha_file(matrix) if os.path.exists(matrix) else summary.get("matrix_sha256")),
        seed_schedule_sha256=summary.get("seed_schedule_sha256"),
        retention_checksum_sha256=summary.get("retention_checksum_sha256"),
        dependency_lock_sha256=(_sha_file(lock) if os.path.exists(lock) else None),
        scenario_engine_version=ENGINE_VERSION,
        output_schema_version=OUTPUT_SCHEMA_VERSION,
        final_stage5b2_run_count=summary.get("final_stage5b2_run_count"),
        test_suite_result=test_result,
        thesis_docx_sha256=THESIS_DOCX_SHA,
        thesis_pdf_sha256=THESIS_PDF_SHA,
        intended_freeze_tag=INTENDED_FREEZE_TAG,
        self_reference_note=SELF_REFERENCE_NOTE,
        contains_own_commit_sha=False,
    )


def run_test_suite() -> str:
    out = subprocess.run(["python3", "-m", "pytest", os.path.join(ROOT, "tests"), "-q"],
                         cwd=ROOT, capture_output=True, text=True)
    lines = out.stdout.strip().splitlines()
    return lines[-1] if lines else "no output"


def main():
    os.makedirs(os.path.join(RESULTS, "manifests"), exist_ok=True)
    result = run_test_suite()
    m = build_freeze_inputs(test_result=result)
    with open(os.path.join(RESULTS, "manifests", "freeze_input_manifest.json"), "w") as f:
        json.dump(m, f, indent=2, sort_keys=True)
    print(json.dumps(m, indent=2, sort_keys=True))
    return m


if __name__ == "__main__":
    main()
