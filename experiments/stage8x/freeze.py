"""Stage 8X — freeze.

    python -m experiments.stage8x.freeze

Freezes code, configuration, seed registry and analysis scripts before the primary
matrix is executed. Produces ``STAGE_8X_FREEZE_MANIFEST.json`` and
``STAGE_8X_FREEZE_REPORT.md``.

After the freeze no scientific parameter may be modified. If a critical defect is
found later, the procedure is: stop, document, fix transparently, increment
``stage8x_config.REVISION``, and re-run **all** affected primary runs — never a
selective re-run of unfavourable seeds.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import sys
import time
from typing import Dict, List

from experiments.stage8x.config import seeds as seedmod
from experiments.stage8x.config import stage8x_config as C

FROZEN_CODE: List[str] = [
    "experiments/stage8x/config/asic.py",
    "experiments/stage8x/config/difficulty.py",
    "experiments/stage8x/config/seeds.py",
    "experiments/stage8x/config/stage8x_config.py",
    "experiments/stage8x/simulator/hashing.py",
    "experiments/stage8x/simulator/powerstate.py",
    "experiments/stage8x/simulator/energy.py",
    "experiments/stage8x/simulator/engine.py",
    "experiments/stage8x/analysis/stats.py",
    "experiments/stage8x/analysis/tables.py",
    "experiments/stage8x/analysis/figures.py",
    "experiments/stage8x/tests/test_stage8x.py",
    "experiments/stage8x/run.py",
    "experiments/stage8x/validate.py",
    "experiments/stage8x/freeze.py",
    "experiments/stage8x/analyze.py",
]


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _git(*args: str) -> str:
    try:
        out = subprocess.run(["git", *args], cwd=C.REPO_ROOT,
                             capture_output=True, text=True, timeout=30)
        return out.stdout.strip()
    except Exception:
        return "UNKNOWN"


def environment() -> Dict:
    try:
        import numpy, pandas, scipy, matplotlib  # noqa: F401
        deps = {
            "numpy": numpy.__version__, "pandas": pandas.__version__,
            "scipy": scipy.__version__, "matplotlib": matplotlib.__version__,
        }
    except Exception as exc:                      # pragma: no cover
        deps = {"error": str(exc)}
    return {
        "python": sys.version.split()[0],
        "implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "dependencies": deps,
    }


def build_manifest() -> Dict:
    C.ensure_dirs()
    seeds_path = seedmod.write_registry(C.SEEDS_JSON)
    code = {}
    missing = []
    for rel in FROZEN_CODE:
        p = os.path.join(C.REPO_ROOT, rel)
        if os.path.exists(p):
            code[rel] = sha256_file(p)
        else:
            missing.append(rel)
    return {
        "experiment": C.EXPERIMENT,
        "revision": C.REVISION,
        "frozen_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "git": {
            "commit": _git("rev-parse", "HEAD"),
            "branch": _git("rev-parse", "--abbrev-ref", "HEAD"),
            "dirty_files": [l for l in _git("status", "--porcelain").splitlines() if l],
        },
        "config_hash": C.config_hash(),
        "frozen_parameters": C.frozen_parameters(),
        "seed_registry": {
            "path": os.path.relpath(seeds_path, C.REPO_ROOT),
            "sha256": sha256_file(seeds_path),
            "namespace": seedmod.NAMESPACE,
            "primary_seeds": seedmod.primary_seeds(),
            "pilot_seeds": seedmod.pilot_seeds(),
        },
        "frozen_code_sha256": code,
        "missing_frozen_files": missing,
        "environment": environment(),
        "run_matrix": {
            "primary_physical_runs": len(C.primary_matrix()),
            "pilot_physical_runs": len(C.pilot_matrix()),
            "secondary_physical_runs": len(C.secondary_matrix()),
            "pocol_alpha_observations": len(C.primary_matrix()) // 2 * 4,
        },
        "post_freeze_amendments": C.POST_FREEZE_AMENDMENTS,
        "post_freeze_rule": (
            "No scientific parameter may change after primary results are observed. "
            "A critical defect requires: stop, document, fix, increment REVISION, "
            "re-run ALL affected primary runs. Selective re-running of unfavourable "
            "seeds is prohibited."
        ),
    }


def write_report(manifest: Dict) -> str:
    path = os.path.join(C.REPORT_DIR, "STAGE_8X_FREEZE_REPORT.md")
    fp = manifest["frozen_parameters"]
    dt = fp["difficulty_table"]
    lines = [
        "# STAGE 8X — FREEZE REPORT",
        "",
        f"Frozen at: {manifest['frozen_at_utc']}",
        f"Revision: {manifest['revision']}",
        f"Git commit: `{manifest['git']['commit']}`",
        f"Git branch: `{manifest['git']['branch']}`",
        f"Config hash: `{manifest['config_hash']}`",
        f"Seed registry SHA-256: `{manifest['seed_registry']['sha256']}`",
        "",
        "The Pilot passed (see `STAGE_8X_PILOT_REPORT.md`) and the validation suite",
        "passed (see `STAGE_8X_VALIDATION_REPORT.md`). Code, configuration, seed",
        "registry and analysis scripts are frozen as of this document.",
        "",
        "## 1. Frozen hardware model",
        "",
        "| Quantity | Value |",
        "|---|---|",
        f"| ASIC | {fp['asic']['name']} |",
        f"| Per-miner hash rate | {fp['asic']['hashrate_THs']} TH/s |",
        f"| Per-miner active power | {fp['asic']['active_power_W']} W |",
        f"| Efficiency | {fp['asic']['efficiency_J_per_TH']} J/TH |",
        "",
        f"*{fp['asic']['source_note']}*",
        "",
        "Low-power sensitivity cases (**none is a Bitmain-certified mode**):",
        "",
        "| Case | alpha | P_low per miner |",
        "|---|---|---|",
    ]
    for label, alpha in fp["alpha_cases"].items():
        lines.append(f"| {label} | {alpha:.2f} | {alpha * fp['asic']['active_power_W']:.1f} W |")
    lines += [
        "",
        "## 2. Frozen experiment parameters",
        "",
        "| Parameter | Value |",
        "|---|---|",
        f"| Network sizes N | {fp['network_sizes']} |",
        f"| Horizon T | {fp['horizon_s']} s |",
        f"| Target block interval | {fp['target_interval_s']} s |",
        f"| Epoch sweep tau | {fp['epoch_sweep_s']} s |",
        f"| Propagation delay | Exp(mean {fp['prop_delay_mean_s']} s) |",
        f"| Primary seeds | {fp['n_primary_seeds']} |",
        f"| Primary protocols | {fp['primary_protocols']} |",
        f"| Difficulty rule | `{fp['difficulty_rule']}` |",
        f"| Nonce-domain rule | `{fp['nonce_domain_rule']}` |",
        f"| Matched difficulty | {fp['matched_difficulty']} |",
        "",
        "## 3. Frozen difficulty and nonce domain by N",
        "",
        "| N | H_N (H/s) | D_N | target | q per candidate | S_N (candidates) | L per miner | P(epoch exhaustion) |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for row in dt:
        lines.append(
            f"| {row['N']} | {row['aggregate_hashrate_Hps']:.4e} | "
            f"{row['difficulty']:.6e} | `{row['target_hex'][:18]}...` | "
            f"{row['q_per_candidate']:.6e} | {row['nonce_domain']:.4e} | "
            f"{row['range_per_miner']:.4e} | {row['p_epoch_exhaustion_predicted']:.5f} |"
        )
    lines += [
        "",
        "## 4. Frozen seed registry",
        "",
        f"Namespace: `{manifest['seed_registry']['namespace']}`",
        "",
        f"Primary master seeds ({len(manifest['seed_registry']['primary_seeds'])}):",
        "",
        "```",
    ]
    ps = manifest["seed_registry"]["primary_seeds"]
    for i in range(0, len(ps), 3):
        lines.append("  " + ", ".join(str(x) for x in ps[i:i + 3]))
    lines += [
        "```",
        "",
        f"Pilot master seeds ({len(manifest['seed_registry']['pilot_seeds'])}), disjoint from the above:",
        "",
        "```",
        "  " + ", ".join(str(x) for x in manifest["seed_registry"]["pilot_seeds"]),
        "```",
        "",
        "## 5. Frozen run matrix",
        "",
        "| Phase | Physical runs |",
        "|---|---|",
        f"| Primary (5 N x 2 protocols x 30 seeds) | **{manifest['run_matrix']['primary_physical_runs']}** |",
        f"| Pilot (excluded from inference) | {manifest['run_matrix']['pilot_physical_runs']} |",
        f"| Declared secondary diagnostics | {manifest['run_matrix']['secondary_physical_runs']} |",
        "",
        f"PoCol energy sensitivity observations: **{manifest['run_matrix']['pocol_alpha_observations']}** "
        "(150 PoCol physical runs x 4 alpha cases). These are *derived accounting rows*, "
        "not independent physical simulations.",
        "",
        "## 6. Frozen code checksums (SHA-256)",
        "",
        "| File | SHA-256 |",
        "|---|---|",
    ]
    for rel, digest in manifest["frozen_code_sha256"].items():
        lines.append(f"| `{rel}` | `{digest}` |")
    env = manifest["environment"]
    lines += [
        "",
        "## 7. Environment",
        "",
        "| Item | Value |",
        "|---|---|",
        f"| Python | {env['python']} ({env['implementation']}) |",
        f"| Platform | {env['platform']} |",
        f"| Machine | {env['machine']} |",
    ]
    for k, v in env["dependencies"].items():
        lines.append(f"| {k} | {v} |")
    lines += [
        "",
        "## 8. Post-freeze rule",
        "",
        manifest["post_freeze_rule"],
        "",
        "## 9. Post-freeze amendments",
        "",
    ]
    if not manifest["post_freeze_amendments"]:
        lines.append("None.")
    for a in manifest["post_freeze_amendments"]:
        lines += [
            f"### {a['id']} ({a['date']}) - `{a['file']}`",
            "",
            f"* **Defect:** {a['defect']}",
            f"* **Fix:** {a['fix']}",
            f"* **Scope:** {a['scope']}",
            "",
        ]
    lines.append("")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    return path


def main(argv=None) -> int:
    manifest = build_manifest()
    C.ensure_dirs()
    mpath = os.path.join(C.REPORT_DIR, "STAGE_8X_FREEZE_MANIFEST.json")
    with open(mpath, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, sort_keys=True)
        fh.write("\n")
    rpath = write_report(manifest)
    print(f"config_hash = {manifest['config_hash']}")
    print(f"commit      = {manifest['git']['commit']}")
    print(f"seeds sha256= {manifest['seed_registry']['sha256']}")
    if manifest["missing_frozen_files"]:
        print("MISSING frozen files:", manifest["missing_frozen_files"])
    print(f"manifest -> {mpath}")
    print(f"report   -> {rpath}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
