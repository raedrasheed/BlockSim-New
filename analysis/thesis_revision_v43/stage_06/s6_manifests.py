#!/usr/bin/env python3
"""Stage 6 — environment + analysis manifest + checksum manifest generators (§19).

  python3 s6_manifests.py env       -> STAGE_06_ENVIRONMENT.json
  python3 s6_manifests.py manifest  -> STAGE_06_ANALYSIS_MANIFEST.json
  python3 s6_manifests.py checksums -> STAGE_06_CHECKSUM_MANIFEST.sha256  (run LAST)
"""
import json
import os
import platform
import sys

import s6_common as C

HERE = os.path.dirname(os.path.abspath(__file__))
DOCS = C.DOCS
STAGE6 = C.STAGE6


def pkg_versions():
    out = {}
    for m in ("numpy", "scipy", "matplotlib", "mpmath", "pandas"):
        try:
            out[m] = __import__(m).__version__
        except Exception:
            out[m] = "not-installed"
    return out


def gen_env():
    env = {
        "stage": "6",
        "purpose": "preregistered statistical analysis (analysis-only environment)",
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
        "packages": pkg_versions(),
        "note": "matplotlib is an ANALYSIS-ONLY dependency used for figure rendering; it "
                "is not part of the frozen scientific-engine environment. The frozen "
                "dependency lock, engine, seeds, matrix, and preregistration are unchanged "
                "in Stage 6. numpy/scipy versions match the frozen scientific environment.",
        "analysis_rng": {
            "bootstrap_seed": C.RNG_SEED_BOOTSTRAP,
            "permutation_seed": C.RNG_SEED_PERMUTATION,
            "describe_bootstrap_seed": 6060600,
            "generator": "numpy.random.default_rng (PCG64); no global default RNG used",
            "n_bootstrap": C.N_BOOTSTRAP, "n_permutation": C.N_PERMUTATION,
        },
        "alpha": C.ALPHA, "confidence_level": C.CONF_LEVEL,
        "multiplicity_procedure": "Holm within each confirmatory hypothesis family",
    }
    p = os.path.join(DOCS, "STAGE_06_ENVIRONMENT.json")
    json.dump(env, open(p, "w"), indent=1)
    open(p, "a").write("\n")
    print("wrote", p)


def gen_manifest():
    inputs = {
        "matrix_csv": C.MATRIX_CSV,
        "summary_jsonl_gz": C.SUMMARY_GLOB,
        "results_manifest": os.path.join(C.STAGE5B2, "manifests", "results_manifest.json"),
        "execution_ledger": os.path.join(DOCS, "STAGE_05B2_EXECUTION_LEDGER.csv"),
        "field_authority_map": os.path.join(DOCS, "STAGE_05B2_FIELD_AUTHORITY_MAP.json"),
    }
    input_ck = {k: C.sha256_file(v) for k, v in inputs.items() if os.path.exists(v)}
    scripts = sorted(f for f in os.listdir(HERE) if f.endswith(".py"))
    script_ck = {f: C.sha256_file(os.path.join(HERE, f)) for f in scripts}
    tests_dir = os.path.join(HERE, "tests")
    test_ck = {f: C.sha256_file(os.path.join(tests_dir, f))
               for f in sorted(os.listdir(tests_dir)) if f.endswith(".py")}
    man = {
        "stage": "6", "generated_for_results_commit_base": C.RESULTS3_COMMIT,
        "sources": {
            "freeze6_commit": C.FREEZE6_COMMIT, "results1_commit": C.RESULTS1_COMMIT,
            "results2_commit": C.RESULTS2_COMMIT, "results3_commit": C.RESULTS3_COMMIT,
            "bulk_data_branch": "thesis-v43-stage5b2-data-1",
            "bulk_data_commit": C.DATA1_COMMIT,
            "matrix_sha256": C.MATRIX_SHA256,
            "engine_version": C.ENGINE_VERSION,
            "output_schema_version": C.OUTPUT_SCHEMA_VERSION,
        },
        "expected": {"runs": C.EXPECTED_RUNS, "groups": C.EXPECTED_GROUPS,
                     "seeds_per_group": C.EXPECTED_SEEDS_PER_GROUP,
                     "zero_block": C.EXPECTED_ZERO_BLOCK},
        "input_checksums": input_ck,
        "analysis_script_checksums": script_ck,
        "test_checksums": test_ck,
        "statistics": {
            "unit": "one physical run per frozen master seed",
            "pairing": "seed-matched on (miner_count, seed)",
            "alpha": C.ALPHA, "confidence_level": C.CONF_LEVEL,
            "n_bootstrap": C.N_BOOTSTRAP, "n_permutation": C.N_PERMUTATION,
            "rng_seed_bootstrap": C.RNG_SEED_BOOTSTRAP,
            "rng_seed_permutation": C.RNG_SEED_PERMUTATION,
            "multiplicity": "Holm within each confirmatory family (H1,H5,H6,H8)",
            "deterministic_output_ordering": True,
        },
        "confirmatory_hypotheses": ["H1", "H3", "H4", "H5", "H6", "H8"],
        "accounting_invariant": ["A1 (former H2)"],
        "secondary_diagnostic": ["H7 (single-height stale-race)"],
        "exploratory": ["H5x"],
        "reproduce": "python3 analysis/thesis_revision_v43/stage_06/s6_run_all.py",
        "deliverable_docs": [f"docs/thesis_revision_v43/{d}" for d in (
            "STAGE_06_ANALYSIS_PLAN.md", "STAGE_06_PREREGISTRATION_MAP.md",
            "STAGE_06_FIELD_USAGE_AUDIT.md", "STAGE_06_DESCRIPTIVE_RESULTS.md",
            "STAGE_06_CONFIRMATORY_RESULTS.md", "STAGE_06_ROBUSTNESS_RESULTS.md",
            "STAGE_06_SECONDARY_DIAGNOSTICS.md", "STAGE_06_CLAIM_CLASSIFICATION.md",
            "STAGE_06_LIMITATIONS.md", "STAGE_06_RESULTS_REPORT.md",
            "STAGE_06_ENVIRONMENT.json", "STAGE_06_ANALYSIS_MANIFEST.json",
            "STAGE_06_QUALITY_GATES.json", "STAGE_06_CHECKSUM_MANIFEST.sha256")],
        "stage_6a_corrections": {
            "branch": "thesis-v43-stage6-analysis-2",
            "base_commit": "547ea339c64aa2475b8faa4e88b934925d550df4",
            "defects_fixed": [
                "H5 fairness overclaim -> modeled completion-balance terms",
                "H3 preregistered idle-saving identity verified directly per-miner",
                "H7 count-rate intervals (seed/run-cluster bootstrap; no binomial/Wilson) "
                "+ separate binary any-stale diagnostic",
                "H1 seed-cluster inference (30 clusters, not 150 pooled pairs)"],
            "docs": [f"docs/thesis_revision_v43/{d}" for d in (
                "STAGE_06A_CORRECTION_REPORT.md", "STAGE_06A_DEPENDENCE_AUDIT.md",
                "STAGE_06A_H3_IDENTITY_AUDIT.md", "STAGE_06A_H7_INTERVAL_AUDIT.md")],
            "new_diagnostic": "results/thesis_revision_v43/stage_06a/diagnostics/"
                              "h3_idle_saving_identity.csv",
        },
    }
    p = os.path.join(DOCS, "STAGE_06_ANALYSIS_MANIFEST.json")
    json.dump(man, open(p, "w"), indent=1)
    open(p, "a").write("\n")
    print("wrote", p)


def gen_checksums():
    """SHA-256 of every Stage-6 output + analysis code + Stage-6 docs (self excluded)."""
    root = C.REPO_ROOT
    targets = []
    for base in (os.path.join(root, "results", "thesis_revision_v43", "stage_06"),
                 os.path.join(root, "results", "thesis_revision_v43", "stage_06a"),
                 os.path.join(root, "analysis", "thesis_revision_v43", "stage_06")):
        if not os.path.isdir(base):
            continue
        for dp, _dn, fs in os.walk(base):
            if "__pycache__" in dp:
                continue
            for f in fs:
                if f.endswith(".pyc"):
                    continue
                targets.append(os.path.join(dp, f))
    # both STAGE_06_* and STAGE_06A_* docs (startswith STAGE_06, not STAGE_06_)
    for f in sorted(os.listdir(DOCS)):
        if f.startswith("STAGE_06") and f != "STAGE_06_CHECKSUM_MANIFEST.sha256":
            targets.append(os.path.join(DOCS, f))
    lines = []
    for t in sorted(targets):
        rel = os.path.relpath(t, root)
        lines.append(f"{C.sha256_file(t)}  {rel}")
    p = os.path.join(DOCS, "STAGE_06_CHECKSUM_MANIFEST.sha256")
    open(p, "w").write("\n".join(lines) + "\n")
    print(f"wrote {p} ({len(lines)} files)")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    if cmd in ("env", "all"):
        gen_env()
    if cmd in ("manifest", "all"):
        gen_manifest()
    if cmd == "checksums":
        gen_checksums()
