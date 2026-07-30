"""Stage 5B1G.1 tests 19-21: no contradictory one-stale docstring, all prior tests
pass, thesis files byte-identical (§5, §6)."""

import os
import sys
import glob
import hashlib
import inspect
import subprocess

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, ROOT)

from experiments.thesis_revision_v43 import scenario_engine

THESIS_DOCX_SHA = "2c3afdc5739109d0ea12ada96c3115d626a2188c1acbaeaa4b6020974884cbda"
THESIS_PDF_SHA = "131412bb2ce17ed97b98dfbefc136c7b5b226b9fd7372e79a25e4b0dc057e9c4"

# contradictory standalone claims that must NOT remain anywhere in the engine/docs
FORBIDDEN = (
    "<=1 admitted stale per accepted height",
    "at most one stale is admitted per height",
    "at most ONE stale is admitted per height",
    "<=1 stale per height",
    "one stale per height (the earliest",
)


def _sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for c in iter(lambda: f.read(1 << 16), b""):
            h.update(c)
    return h.hexdigest()


# 19
def test_no_global_one_stale_docstring_remains():
    doc = scenario_engine._resolve_stale_race.__doc__ or ""
    low = " ".join((doc.lower()).split())                  # normalise line breaks/indent
    assert "multiple distinct" in low                      # corrected statement present
    assert "no global one-stale-per-height cap" in low     # explicit no-cap statement
    # the engine source carries no contradictory standalone one-stale-per-height claim
    src = inspect.getsource(scenario_engine)
    for bad in FORBIDDEN:
        assert bad not in src, bad
    # nor do the Stage 5B1G / 5B1G.1 docs
    for md in glob.glob(os.path.join(ROOT, "docs", "thesis_revision_v43", "STAGE_05B1G*.md")):
        text = open(md, encoding="utf-8").read()
        for bad in FORBIDDEN:
            assert bad not in text, (md, bad)


# 20
def test_all_prior_tests_pass():
    # the immediately prior stage's full suite still passes unchanged
    out = subprocess.run([sys.executable, "-m", "pytest",
                          os.path.join(ROOT, "tests", "thesis_revision_v43", "stage5b1g"), "-q"],
                         cwd=ROOT, capture_output=True, text=True)
    assert out.returncode == 0, out.stdout[-2000:]


# 21
def test_thesis_files_unchanged():
    docx = os.path.join(ROOT, "docs", "Raed-Rasheed-draft-42-00.docx")
    pdf = os.path.join(ROOT, "docs", "Raed-Rasheed-draft-42-00.pdf")
    assert _sha(docx) == THESIS_DOCX_SHA
    assert _sha(pdf) == THESIS_PDF_SHA
