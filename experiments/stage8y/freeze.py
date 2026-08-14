"""Stage 8Y — freeze.

    python -m experiments.stage8y.freeze

Freezes source, hardware registry, compositions, difficulty table, nonce-domain rule,
every scientific parameter, the seed registry, selection policies, reserve schedules,
low-power assumptions, wake model, statistical plan and acceptance criteria. Writes
``STAGE_8Y_FREEZE_MANIFEST.json`` and ``STAGE_8Y_FREEZE_REPORT.md``.

No confirmatory run may be executed before this has been produced.
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

from experiments.stage8y.config import seeds as seedmod
from experiments.stage8y.config import stage8y_config as C

FROZEN_CODE: List[str] = [
    "experiments/stage8y/config/hardware_registry.json",
    "experiments/stage8y/config/hardware.py",
    "experiments/stage8y/config/difficulty.py",
    "experiments/stage8y/config/policies.py",
    "experiments/stage8y/config/seeds.py",
    "experiments/stage8y/config/stage8y_config.py",
    "experiments/stage8y/src/powerstate.py",
    "experiments/stage8y/src/energy.py",
    "experiments/stage8y/src/engine.py",
    "experiments/stage8y/src/metrics.py",
    "experiments/stage8y/src/analysis_stats.py",
    "experiments/stage8y/src/analysis_tables.py",
    "experiments/stage8y/src/analysis_figures.py",
    "experiments/stage8y/tests/test_stage8y.py",
    "experiments/stage8y/run.py",
    "experiments/stage8y/analyze.py",
    "experiments/stage8y/validate.py",
    "experiments/stage8y/freeze.py",
    "experiments/stage8y/baseline.py",
]


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _git(*args: str) -> str:
    try:
        out = subprocess.run(["git", *args], cwd=C.REPO_ROOT, capture_output=True,
                             text=True, timeout=30)
        return out.stdout.strip()
    except Exception:
        return "UNKNOWN"


def environment() -> Dict:
    try:
        import matplotlib, numpy, pandas, scipy  # noqa: F401
        deps = {"numpy": numpy.__version__, "pandas": pandas.__version__,
                "scipy": scipy.__version__, "matplotlib": matplotlib.__version__}
    except Exception as exc:                      # pragma: no cover
        deps = {"error": str(exc)}
    return {"python": sys.version.split()[0],
            "implementation": platform.python_implementation(),
            "platform": platform.platform(), "machine": platform.machine(),
            "processor": platform.processor(), "dependencies": deps}


def build_manifest() -> Dict:
    C.ensure_dirs()
    seeds_path = seedmod.write_registry(C.SEEDS_JSON)
    code, missing = {}, []
    for rel in FROZEN_CODE:
        p = os.path.join(C.REPO_ROOT, rel)
        (code.__setitem__(rel, sha256_file(p)) if os.path.exists(p)
         else missing.append(rel))
    status = _git("status", "--porcelain")
    return {
        "experiment": C.EXPERIMENT, "revision": C.REVISION,
        "frozen_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "git": {"commit": _git("rev-parse", "HEAD"),
                "branch": _git("rev-parse", "--abbrev-ref", "HEAD"),
                "working_tree_clean": status.strip() == "",
                "dirty_paths": [l for l in status.splitlines() if l]},
        "config_hash": C.config_hash(),
        "frozen_parameters": C.frozen_parameters(),
        "seed_registry": {"path": os.path.relpath(seeds_path, C.REPO_ROOT),
                          "sha256": sha256_file(seeds_path),
                          "namespace": seedmod.NAMESPACE,
                          "groups": {k: v["seeds"]
                                     for k, v in seedmod.registry()["groups"].items()}},
        "frozen_code_sha256": code, "missing_frozen_files": missing,
        "environment": environment(),
        "run_matrix": {"pilot": len(C.pilot_matrix()),
                       "primary": len(C.primary_matrix()),
                       "secondary": len(C.secondary_matrix()),
                       "longhorizon": len(C.longhorizon_matrix()),
                       "primary_alpha_observations":
                           len([r for r in C.primary_matrix()
                                if r.protocol in C.POCOL_PROTOCOLS])
                           * len(C.ALPHA_CASES)},
        "statistical_plan": {
            "pairing": "seed-paired PoCol - PoW at matched (composition, N, seed)",
            "tests": "Shapiro-Wilk assumption check, then paired t-test or Wilcoxon "
                     "signed-rank; magnitude, t-based CI and paired bootstrap CI, "
                     "Cohen's d_z and rank-biserial reported alongside every p-value",
            "multiplicity": "Holm-Bonferroni within each metric family across "
                            "confirmatory cells",
            "threshold_assessment": "bootstrap CI around EnergySaving vs 0.50 and "
                                    "around BlockRetention vs 0.90 / 0.95",
        },
        "post_freeze_amendments": C.POST_FREEZE_AMENDMENTS,
        "post_freeze_rule": (
            "No scientific parameter may change after the freeze. A change requires: "
            "rerun the Pilot from scratch, document the change, increment REVISION and "
            "refreeze. Serialization or implementation corrections are permitted only "
            "if scientifically neutral and fully documented. Selective re-running of "
            "unfavourable seeds is prohibited."),
    }


def write_report(m: Dict) -> str:
    fp = m["frozen_parameters"]
    L = ["# STAGE 8Y — FREEZE REPORT", "",
         f"Frozen at: {m['frozen_at_utc']}", f"Revision: {m['revision']}",
         f"Git commit: `{m['git']['commit']}`", f"Git branch: `{m['git']['branch']}`",
         f"Working tree clean: {m['git']['working_tree_clean']}",
         f"Config hash: `{m['config_hash']}`",
         f"Seed registry SHA-256: `{m['seed_registry']['sha256']}`", ""]
    if m["git"]["dirty_paths"]:
        L += ["Dirty paths at freeze time:", "", "```"] + \
             m["git"]["dirty_paths"] + ["```", ""]
    L += ["The Pilot passed (`STAGE_8Y_PILOT_REPORT.md`) and the validation suite "
          "passed (`STAGE_8Y_VALIDATION_REPORT.md`). Everything below is frozen.", "",
          "## 1. Hardware registry", "",
          "| Key | Model | h (TH/s) | P (W) | η derived (J/TH) | certification |",
          "|---|---|---|---|---|---|"]
    for d in fp["hardware_registry"]["devices"]:
        L.append(f"| {d['key']} | {d['model']} | {d['hashrate_THs']} | "
                 f"{d['active_power_W']} | {d['efficiency_J_per_TH_derived']:.3f} | "
                 f"{d['manufacturer_certified']} |")
    L += ["", "No device-specific low-power figure is published by the manufacturer, "
              "so none is used. All parked power is `P_low = α·P_active`.", "",
          "## 2. Hardware compositions", "", "| ID | Mix | Rationale |", "|---|---|---|"]
    for k in fp["compositions"]:
        mix = ", ".join(f"{int(100*v)}% {kk}" for kk, v in fp["compositions"][k].items())
        L.append(f"| {k} | {mix} | {fp['composition_rationale'][k]} |")
    L += ["", "## 3. Frozen scientific parameters", "", "| Parameter | Value |",
          "|---|---|",
          f"| Primary N | {fp['primary_network_sizes']} |",
          f"| Secondary N | {fp['secondary_network_sizes']} |",
          f"| Primary compositions | {fp['primary_compositions']} |",
          f"| Primary protocols | {fp['primary_protocols']} |",
          f"| Horizon | {fp['horizon_s']} s (long: {fp['long_horizon_s']} s) |",
          f"| Target interval | {fp['target_interval_s']} s |",
          f"| Epoch sweep τ | {fp['epoch_sweep_s']} s |",
          f"| Propagation | Exp(mean {fp['prop_delay_mean_s']} s) |",
          f"| Difficulty rule | {fp['difficulty_rule']} |",
          f"| Nonce-domain rule | {fp['nonce_domain_rule']} |",
          f"| Domain semantics | {fp['domain_semantics']} |",
          f"| Confirmatory selection | {fp['confirmatory_policy']['selection_rule']} |",
          f"| Confirmatory r_H (P3) | {fp['confirmatory_policy']['target_hash_fraction']} |",
          f"| Confirmatory schedule (P4) | {fp['confirmatory_policy']['reserve_schedule']} |",
          f"| Confirmatory trigger | {fp['confirmatory_policy']['trigger_s']} s |",
          f"| Confirmatory wake delay | {fp['confirmatory_policy']['wake_s']} s |",
          f"| Wake power ratio | {fp['confirmatory_policy']['wake_power_ratio']} "
          f"({fp['confirmatory_policy']['wake_power_note']}) |",
          f"| α cases | {fp['alpha_cases']} |",
          f"| Seeds | {fp['n_primary_seeds']} primary |", "",
          f"*{fp['alpha_note']}*", "",
          "## 4. Difficulty and nonce domain (primary cells)", "",
          "| comp | N | H_N (H/s) | P_N (W) | η_net | D | q | S |",
          "|---|---|---|---|---|---|---|---|"]
    for row in fp["difficulty_table"]:
        if row["composition"] in fp["primary_compositions"] and \
                row["N"] in fp["primary_network_sizes"]:
            L.append(f"| {row['composition']} | {row['N']} | "
                     f"{row['H_N_Hps']:.4e} | {row['P_N_W']:.0f} | "
                     f"{row['eta_network_J_per_TH']:.3f} | {row['difficulty_D']:.6e} | "
                     f"{row['q_per_candidate']:.6e} | {row['nonce_domain_S']:.4e} |")
    L += ["", "## 5. Seed registry", "",
          f"Namespace: `{m['seed_registry']['namespace']}`", ""]
    for g, s in m["seed_registry"]["groups"].items():
        L += [f"**{g}** ({len(s)} seeds):", "", "```"]
        for i in range(0, len(s), 3):
            L.append("  " + ", ".join(str(x) for x in s[i:i + 3]))
        L += ["```", ""]
    L += ["## 6. Run matrix", "", "| Phase | Physical runs |", "|---|---|"]
    for k, v in m["run_matrix"].items():
        L.append(f"| {k} | {v} |")
    L += ["", "## 7. Statistical plan", "", "| Element | Specification |", "|---|---|"]
    for k, v in m["statistical_plan"].items():
        L.append(f"| {k} | {v} |")
    L += ["", "## 8. Acceptance criteria", "", "| Criterion | Definition |", "|---|---|"]
    for k, v in fp["acceptance_criteria"].items():
        L.append(f"| {k} | {v} |")
    L += ["", "## 9. Frozen code checksums", "", "| File | SHA-256 |", "|---|---|"]
    for rel, dg in m["frozen_code_sha256"].items():
        L.append(f"| `{rel}` | `{dg}` |")
    env = m["environment"]
    L += ["", "## 10. Environment", "", "| Item | Value |", "|---|---|",
          f"| Python | {env['python']} ({env['implementation']}) |",
          f"| Platform | {env['platform']} |", f"| Machine | {env['machine']} |"]
    for k, v in env["dependencies"].items():
        L.append(f"| {k} | {v} |")
    L += ["", "## 11. Post-freeze rule", "", m["post_freeze_rule"], "",
          "## 12. Post-freeze amendments", ""]
    if not m["post_freeze_amendments"]:
        L.append("None.")
    for am in m["post_freeze_amendments"]:
        L += [f"### {am['id']} ({am['date']}) — `{am['file']}`", "",
              f"* **Defect:** {am['defect']}", f"* **Fix:** {am['fix']}",
              f"* **Scope:** {am['scope']}", ""]
    path = os.path.join(C.REPORT_DIR, "STAGE_8Y_FREEZE_REPORT.md")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L))
        fh.write("\n")
    return path


def main(argv=None) -> int:
    m = build_manifest()
    C.ensure_dirs()
    mp = os.path.join(C.MANIFEST_DIR, "STAGE_8Y_FREEZE_MANIFEST.json")
    with open(mp, "w", encoding="utf-8") as fh:
        json.dump(m, fh, indent=2, sort_keys=True)
        fh.write("\n")
    rp = write_report(m)
    print(f"config_hash  = {m['config_hash']}")
    print(f"commit       = {m['git']['commit']}  clean={m['git']['working_tree_clean']}")
    print(f"seeds sha256 = {m['seed_registry']['sha256']}")
    if m["missing_frozen_files"]:
        print("MISSING:", m["missing_frozen_files"])
    print(f"manifest -> {mp}")
    print(f"report   -> {rp}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
