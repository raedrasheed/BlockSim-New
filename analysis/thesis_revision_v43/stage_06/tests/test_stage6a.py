#!/usr/bin/env python3
"""Stage 6A — correction tests (16 required, §8).

Run: python3 -m pytest analysis/thesis_revision_v43/stage_06/tests/test_stage6a.py -q
"""
import json
import os
import subprocess
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

import s6_common as C  # noqa: E402
import s6_stats as S  # noqa: E402
import s6_analysis as A  # noqa: E402

BUNDLE = json.load(open(os.path.join(C.STAGE6, "models", "analysis_bundle.json")))
STAGE6A = os.path.join(C.REPO_ROOT, "results", "thesis_revision_v43", "stage_06a")

# Positive fairness CLAIM patterns that must never appear (disclaimers using the
# hyphenated forms "incentive-fairness"/"reward-fairness" are explicitly allowed and,
# per the approved fig04 caption, are required negations).
FORBIDDEN_CLAIMS = [
    "restores fairness", "improves fairness", "ensures fairness", "guarantees fairness",
    "reward fairness", "incentive fairness", "participation fairness",
    "economic fairness", "proof-of-effort fairness", "supported (fairness)", "fairer",
]


def _stage6_text_files():
    roots = [
        os.path.join(C.REPO_ROOT, "analysis", "thesis_revision_v43", "stage_06"),
        os.path.join(C.REPO_ROOT, "results", "thesis_revision_v43", "stage_06"),
        STAGE6A,
    ]
    files = []
    for root in roots:
        for dp, _dn, fs in os.walk(root):
            if "__pycache__" in dp or os.sep + "tests" in dp:
                continue  # the test files define the forbidden-pattern list itself
            for f in fs:
                if f.rsplit(".", 1)[-1] in ("py", "json", "csv", "md", "txt"):
                    files.append(os.path.join(dp, f))
    for f in sorted(os.listdir(C.DOCS)):
        if f.startswith("STAGE_06"):
            files.append(os.path.join(C.DOCS, f))
    return files


# 1. no unsupported fairness wording (positive claims) remains
def test_01_no_fairness_claims():
    hits = []
    for path in _stage6_text_files():
        txt = open(path, errors="ignore").read().lower()
        for pat in FORBIDDEN_CLAIMS:
            if pat in txt:
                hits.append((os.path.basename(path), pat))
    assert not hits, hits


# 2. H5 terminology uses completion-time balance/symmetry
def test_02_h5_completion_terms():
    cc = json.load(open(os.path.join(C.STAGE6, "models", "claim_classification.json")))
    note = cc["hypotheses"]["H5"]["note"].lower()
    assert "completion" in note and "trade-off" in note
    assert "fairness" not in cc["hypotheses"]["H5"]["overall"].lower()


# 3. H3 per-miner saving identity reconciles per run
def test_03_h3_identity_reconciles_each_run():
    recs, summ = A.h3_idle_saving_identity()
    assert summ["runs_checked"] == 570
    assert all(r["pass"] for r in recs)
    assert summ["failed_run_count"] == 0


# 4. H3 residual within declared tolerance
def test_04_h3_residual_within_tolerance():
    summ = BUNDLE["H3"]["preregistered_idle_saving_identity"]
    assert summ["identity_verified"] is True
    assert summ["max_abs_residual_kwh"] <= summ["tolerance_abs_kwh"]


# 5. H7 stale-block rate does not use a binomial denominator
def test_05_h7_no_binomial_denominator():
    h7 = BUNDLE["H7_secondary"]
    assert "NO binomial" in h7["interval_framework"] or "no binomial" in h7["interval_framework"].lower()
    for lv in h7["levels"]:
        for k in lv:
            assert "wilson" not in k.lower()
            assert "clopper" not in k.lower()
            assert "binomial" not in k.lower() or "assumption_dependent" in k.lower()


# 6. H7 intervals are run/seed-cluster based
def test_06_h7_cluster_intervals():
    for lv in BUNDLE["H7_secondary"]["levels"]:
        assert "mean_count_rate_cluster_boot_ci95" in lv
        assert len(lv["run_level_sh_stales_per_accepted_block"]) == lv["n_runs"]


# 7. binary any-stale outcome is separate from the stale-block count rate
def test_07_binary_any_stale_separate():
    h7 = BUNDLE["H7_secondary"]
    assert "binary_any_stale_definition" in h7
    for lv in h7["levels"]:
        assert "any_stale_height_fraction_mean" in lv
        assert "mean" in lv  # the count-rate mean is a different field


# 8. H7 remains secondary diagnostic only
def test_08_h7_secondary_only():
    assert BUNDLE["H7_secondary"]["classification"] == "SECONDARY_DIAGNOSTIC_ONLY"


# 9. H1 uncertainty uses 30 seed clusters
def test_09_h1_30_clusters():
    for c in BUNDLE["H1"]["contrasts"]:
        assert c["n_clusters"] == 30
        assert c["cluster_unit"] == "master_seed"


# 10. H1 physical-pair count and cluster count separately reported
def test_10_h1_pairs_and_clusters_reported():
    assert BUNDLE["H1"]["physical_run_pairs_per_contrast"] == 150
    assert BUNDLE["H1"]["independent_clusters"] == 30
    for c in BUNDLE["H1"]["contrasts"]:
        assert c["physical_run_pairs"] == 150 and c["n_clusters"] == 30


# 11. H1 N-specific robustness results exist
def test_11_h1_n_specific_robustness():
    for c in BUNDLE["H1"]["contrasts"]:
        ns = c["n_specific_robustness"]
        assert set(int(k) for k in ns) == {100, 200, 300, 400, 500}
        assert all(v["n_pairs"] == 30 for v in ns.values())


# 12. Holm correction reproduces after the H1 correction
def test_12_holm_reproduces():
    cs = BUNDLE["H1"]["contrasts"]
    holm = S.holm([(c["label"], c["perm_p"]) for c in cs])
    for c, h in zip(cs, holm):
        assert (c.get("p_holm") is None and h["p_holm"] is None) or \
               abs(c["p_holm"] - h["p_holm"]) < 1e-12


# 13. figure 04 contains no fairness CLAIM (title/caption); disclaimer forms allowed
def test_13_fig04_no_fairness_claim():
    idx = {f["figure"]: f for f in json.load(
        open(os.path.join(C.STAGE6, "figures", "figures_index.json")))}
    f4 = idx["fig04_h5_c2_energy_tradeoff"]
    blob = (f4["caption"] + " " + " ".join(f4.get("files", []))).lower()
    for pat in FORBIDDEN_CLAIMS:
        assert pat not in blob, pat
    assert f4["tag"] == "CONFIRMATORY"


# 14. all affected tables and figures reproduce (files present)
def test_14_affected_outputs_present():
    T = os.path.join(C.STAGE6, "tables")
    for t in ("confirmatory_effects.csv", "table06_robustness.csv",
              "table12_secondary_stale.csv", "table03_hypothesis_test_map.csv"):
        assert os.path.isfile(os.path.join(T, t))
    F = os.path.join(C.STAGE6, "figures")
    for fig in ("fig04_h5_c2_energy_tradeoff", "fig08_h7_delay_singleheight"):
        assert os.path.isfile(os.path.join(F, fig + ".pdf"))
        assert os.path.isfile(os.path.join(F, fig + ".png"))
    assert os.path.isfile(os.path.join(STAGE6A, "diagnostics", "h3_idle_saving_identity.csv"))


# 15. no Stage-5B2 scientific output changed
def test_15_scientific_tree_unchanged():
    out = subprocess.check_output(
        ["git", "-C", C.REPO_ROOT, "diff", "--name-only", C.RESULTS1_COMMIT, "--",
         "results/thesis_revision_v43/stage_05b2/summary",
         "results/thesis_revision_v43/stage_05b2/per_miner",
         "results/thesis_revision_v43/stage_05b2/per_template",
         "results/thesis_revision_v43/stage_05b2/block_log",
         "results/thesis_revision_v43/stage_05b2/stale_race",
         "results/thesis_revision_v43/stage_05b2/full_logs"], text=True).strip()
    assert out == "", out


# 16. thesis DOCX/PDF remain byte-identical
def test_16_thesis_unchanged():
    docx = C.sha256_file(os.path.join(C.REPO_ROOT, "docs", "Raed-Rasheed-draft-42-00.docx"))
    pdf = C.sha256_file(os.path.join(C.REPO_ROOT, "docs", "Raed-Rasheed-draft-42-00.pdf"))
    assert docx == C.THESIS_DOCX_SHA
    assert pdf == C.THESIS_PDF_SHA
