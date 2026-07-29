"""Stage 5B1B tests 21-27: freeze-input manifest and checksum reproducibility."""

import os
import sys
import re
import json

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, ROOT)

from experiments.thesis_revision_v43 import freeze_inputs_5b1b as fi
from experiments.thesis_revision_v43 import build_matrix_5b1b as b
from experiments.thesis_revision_v43 import build_matrix_5b1 as base
from experiments.thesis_revision_v43 import retention_5b1a
from experiments.thesis_revision_v43 import run_utils
import hashlib
import json as _json


# 21
def test_internal_manifest_has_no_false_self_commit_claim():
    m = fi.build_freeze_inputs(test_result="x")
    assert m["contains_own_commit_sha"] is False
    assert "self_reference_note" in m and "does NOT contain the SHA" in m["self_reference_note"]
    # no value is a bare 40-hex commit SHA masquerading as this commit's id
    for k, v in m.items():
        if isinstance(v, str) and re.fullmatch(r"[0-9a-f]{40}", v):
            assert False, f"field {k} looks like a commit SHA claim"


# 22
def test_matrix_checksum_reproducible():
    a = b.build()[0]
    c = b.build()[0]
    ka = [(r["run_id"], r["run_execution_hash"], r["scientific_semantics_hash"]) for r in a]
    kc = [(r["run_id"], r["run_execution_hash"], r["scientific_semantics_hash"]) for r in c]
    assert ka == kc


# 23
def test_seed_checksum_reproducible():
    sched = dict(seed_base=base.SEED_BASE, n_seeds=30, seeds=base.SEEDS)
    h1 = hashlib.sha256(_json.dumps(sched, sort_keys=True).encode()).hexdigest()
    h2 = hashlib.sha256(_json.dumps(sched, sort_keys=True).encode()).hexdigest()
    assert h1 == h2 == "6122dbd0f455a1c4c9676ec6575f064c3a682b3c978705d6588af11489b13e10"


# 24
def test_retention_checksum_reproducible():
    final = b.build()[0]
    _, m1 = retention_5b1a.design_retention([dict(r) for r in final])
    _, m2 = retention_5b1a.design_retention([dict(r) for r in final])
    assert m1["retention_checksum_sha256"] == m2["retention_checksum_sha256"]


# 25
def test_dependency_lock_checksum_reproducible():
    lock = os.path.join(ROOT, "requirements-thesis-v43-lock.txt")
    assert run_utils.sha256_file(lock) == run_utils.sha256_file(lock)
    assert run_utils.sha256_file(lock) == \
        "6e211ea7c031a3fab560843690e27e5a3c2aa2a8c363ab483369a2babc8157be"


# 26
def test_freeze_inputs_complete():
    m = fi.build_freeze_inputs(test_result="checked")
    for key in fi.REQUIRED_KEYS:
        assert key in m, key
    assert m["intended_freeze_tag"] == "thesis-v43-stage5b2-freeze-1"
    assert m["scenario_engine_version"] == "5b1b.1"


# 27
def test_thesis_checksums_unchanged():
    docx = os.path.join(ROOT, "docs", "Raed-Rasheed-draft-42-00.docx")
    pdf = os.path.join(ROOT, "docs", "Raed-Rasheed-draft-42-00.pdf")
    assert run_utils.sha256_file(docx) == "2c3afdc5739109d0ea12ada96c3115d626a2188c1acbaeaa4b6020974884cbda"
    assert run_utils.sha256_file(pdf) == "131412bb2ce17ed97b98dfbefc136c7b5b226b9fd7372e79a25e4b0dc057e9c4"
