"""Stage 5B1F internal freeze-INPUT manifest (for freeze #2).

Created BEFORE the corrective commit. Records the frozen inputs and the INTENDED
freeze branch name (thesis-v43-stage5b2-freeze-4) but makes NO claim to contain the
SHA of the commit that will contain it. The authoritative commit SHA is recorded
externally (in the completion report / the new remote freeze branch) after the
commit exists. The old freeze (thesis-v43-stage5b2-freeze-3) is preserved unchanged
as an historical invalidated freeze.
"""

from __future__ import annotations
import os
import json
import hashlib
import subprocess

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DOCS = os.path.join(ROOT, "docs", "thesis_revision_v43")
RESULTS = os.path.join(ROOT, "results", "thesis_revision_v43", "stage_05b1f")

from experiments.thesis_revision_v43.schemas import OUTPUT_SCHEMA_VERSION
from experiments.thesis_revision_v43.scenario_engine import ENGINE_VERSION

INTENDED_FREEZE_BRANCH = "thesis-v43-stage5b2-freeze-4"
SUPERSEDES = "thesis-v43-stage5b2-freeze-3"
THESIS_DOCX_SHA = "2c3afdc5739109d0ea12ada96c3115d626a2188c1acbaeaa4b6020974884cbda"
THESIS_PDF_SHA = "131412bb2ce17ed97b98dfbefc136c7b5b226b9fd7372e79a25e4b0dc057e9c4"

REQUIRED_KEYS = (
    "stage", "matrix_sha256", "seed_schedule_sha256", "retention_checksum_sha256",
    "dependency_lock_sha256", "scenario_engine_version", "output_schema_version",
    "test_suite_result", "thesis_docx_sha256", "thesis_pdf_sha256",
    "intended_freeze_branch", "supersedes_freeze", "self_reference_note",
)
SELF_REFERENCE_NOTE = ("This internal manifest does NOT contain the SHA of the commit "
                       "that contains it; the corrective-commit SHA is recorded externally "
                       f"in the new remote freeze branch '{INTENDED_FREEZE_BRANCH}' and the "
                       "Stage-5B1F completion report.")


def _sha_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for c in iter(lambda: f.read(1 << 16), b""):
            h.update(c)
    return h.hexdigest()


def build_freeze_inputs(test_result: str = "unverified") -> dict:
    matrix = os.path.join(DOCS, "STAGE_05B1F_FINAL_MATRIX.csv")
    sp = os.path.join(RESULTS, "raw", "matrix_5b1f_summary.json")
    summary = json.load(open(sp)) if os.path.exists(sp) else {}
    lock = os.path.join(ROOT, "requirements-thesis-v43-lock.txt")
    return dict(
        stage="5B1F",
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
        intended_freeze_branch=INTENDED_FREEZE_BRANCH,
        supersedes_freeze=SUPERSEDES,
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
    m = build_freeze_inputs(test_result=run_test_suite())
    json.dump(m, open(os.path.join(RESULTS, "manifests", "freeze_input_manifest.json"), "w"),
              indent=2, sort_keys=True)
    print(json.dumps(m, indent=2, sort_keys=True))
    return m


if __name__ == "__main__":
    main()
