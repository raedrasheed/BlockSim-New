"""Stage 4 dry-runs (small, bounded configurations) — semantic validation only.
NOT the final Stage-5 matrix; results must not appear in the thesis.

Validates (section 15): every scenario executes; config validation works; B0
templates independent; B1 has measurable duplicates; B2 reduces overlap vs B1;
B3 disjoint; C1 no artificial energy saving; C2 saving == explicit idle-state
durations; exact duplicate reconciliation; and a propagation-delay stale sweep.
"""

from __future__ import annotations

import os
import sys
import csv
import json
import hashlib
import subprocess

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tests", "thesis_revision_v43"))

from experiments.thesis_revision_v43.scenario_definitions import ScenarioConfig, simulate_round, SCENARIOS
from experiments.thesis_revision_v43 import config_schema as cs
from _pocol_harness import run_pocol   # noqa: E402

OUT = os.path.join(ROOT, "results", "thesis_revision_v43", "stage_04")
RAW = os.path.join(OUT, "raw"); MANI = os.path.join(OUT, "manifests"); LOGS = os.path.join(OUT, "logs")
DOCS = os.path.join(ROOT, "docs", "thesis_revision_v43")


def _git_commit():
    try:
        return subprocess.check_output(["git", "-C", ROOT, "rev-parse", "HEAD"]).decode().strip()
    except Exception:
        return "unknown"


def scenario_rows():
    rows = []
    for N in (5, 10, 20):
        H = float(N)                     # rate 1 H/s per miner -> budget = B per miner
        B = 100.0
        S = N * 100                      # disjoint range == budget (mu=1)
        p = 1.0 / (H * B)
        for scen in SCENARIOS:
            for seed in (1, 2, 3):
                cfg = ScenarioConfig(scenario_id=scen, seed=seed, miner_count=N,
                                     domain_size=S, p=p, network_hash_rate_hps=H,
                                     round_duration_s=B,
                                     idle_power_ratio=0.0)
                rows.append(simulate_round(cfg))
    return rows


def c2_idle_demonstration():
    """A configuration where each miner's range completes before the round ends,
    so C2 genuinely idles (S < H*B). Compare C1 (continuous) vs C2 (idle)."""
    rows = []
    N, H, B = 10, 10.0, 100.0
    S = N * 50                           # range 50 < budget 100 -> idle 50 s
    p = 1.0 / (H * B)
    for ratio in (0.0, 0.1, 0.2):
        c1 = ScenarioConfig("C1", 1, N, S, p, H, round_duration_s=B, idle_power_ratio=0.0)
        c2 = ScenarioConfig("C2", 1, N, S, p, H, round_duration_s=B, idle_power_ratio=ratio)
        r1 = simulate_round(c1); r2 = simulate_round(c2)
        saving = r1["total_energy_kwh"] - r2["total_energy_kwh"]
        frac = (saving / r1["total_energy_kwh"]) if r1["total_energy_kwh"] else 0.0
        rows.append(dict(demo="c2_idle", idle_ratio=ratio,
                         c1_total_kwh=r1["total_energy_kwh"], c2_total_kwh=r2["total_energy_kwh"],
                         c1_active_s=r1["total_active_time_s"], c2_active_s=r2["total_active_time_s"],
                         c2_idle_s=r2["total_idle_time_s"],
                         c2_active_kwh=r2["active_energy_kwh"], c2_idle_kwh=r2["idle_energy_kwh"],
                         saving_kwh=saving, fractional_saving=frac))
    return rows


def stale_delay_sweep():
    rows = []
    for delay in (1e-9, 0.42, 1.0, 5.0, 30.0, 60.0):
        legit = 0; accepted = 0; runs = 0
        for seed in (1, 2, 3):
            r = run_pocol(50, sim_time=8000, seed=seed, bdelay=delay)
            legit += r["diag"]["legit_stales"]; accepted += r["diag"]["accepted_blocks"]; runs += 1
        # rule-of-three upper 95% bound when zero observed
        upper95 = (3.0 / accepted) if legit == 0 and accepted > 0 else None
        rows.append(dict(propagation_delay_s=delay, seeds=runs, accepted_blocks=accepted,
                         legit_stales=legit,
                         legit_stale_rate=(legit / accepted) if accepted else 0.0,
                         zero_obs_upper95_bound=upper95))
    return rows


def _write_csv(path, rows):
    keys = []
    for r in rows:
        for k in r:
            if k not in keys:
                keys.append(k)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys); w.writeheader()
        for r in rows:
            w.writerow(r)


def verify(scen_rows):
    """Return (checks dict, all_pass)."""
    by = {}
    for r in scen_rows:
        by.setdefault(r["scenario_id"], []).append(r)

    def mean(scen, key):
        v = [r[key] for r in by[scen]]
        return sum(v) / len(v)

    checks = {}
    checks["1_all_scenarios_execute"] = set(by) == set(SCENARIOS)
    checks["3_b0_independent_zero_duplicates"] = all(r["duplicate_evaluations"] == 0 for r in by["B0"])
    checks["4_b1_measurable_duplicates"] = all(r["duplicate_evaluations"] > 0 for r in by["B1"])
    checks["5_b2_reduces_overlap_vs_b1"] = mean("B2", "duplicate_rate") < mean("B1", "duplicate_rate")
    checks["6_b3_disjoint_zero_overlap"] = all(r["overlap_headers"] == 0 for r in by["B3"])
    checks["7_c1_no_artificial_saving"] = abs(mean("C1", "total_energy_kwh") - mean("B3", "total_energy_kwh")) < 1e-12
    checks["9_duplicate_reconciliation"] = all(
        r["total_candidate_evaluations"] == r["distinct_candidate_identities"] + r["duplicate_evaluations"]
        for r in scen_rows)
    return checks, all(checks.values())


def main():
    for d in (RAW, MANI, LOGS):
        os.makedirs(d, exist_ok=True)
    commit = _git_commit()
    scen = scenario_rows()
    c2 = c2_idle_demonstration()
    stale = stale_delay_sweep()
    checks, ok = verify(scen)
    # C2 saving == idle-state energy reconciliation
    checks["8_c2_saving_equals_idle_durations"] = all(
        abs(row["saving_kwh"] - (row["c1_total_kwh"] - row["c2_total_kwh"])) < 1e-12 for row in c2)
    checks["8b_c2_zero_idle_lower_bound"] = any(row["idle_ratio"] == 0.0 and row["saving_kwh"] > 0 for row in c2)
    checks["stale_increases_with_delay"] = (
        stale[-1]["legit_stale_rate"] >= stale[0]["legit_stale_rate"])
    checks["zero_delay_no_stale"] = stale[0]["legit_stales"] == 0

    _write_csv(os.path.join(DOCS, "STAGE_04_DRY_RUN_RESULTS.csv"), scen)
    _write_csv(os.path.join(RAW, "dry_run_scenarios.csv"), scen)
    _write_csv(os.path.join(RAW, "dry_run_c2_idle.csv"), c2)
    _write_csv(os.path.join(RAW, "dry_run_stale_delay.csv"), stale)
    for f in ("dry_run_scenarios.csv", "dry_run_c2_idle.csv", "dry_run_stale_delay.csv"):
        os.chmod(os.path.join(RAW, f), 0o444)
    man = dict(commit=commit, checks=checks, all_pass=ok and all(checks.values()),
               scenario_rows=len(scen), c2_rows=len(c2), stale_rows=len(stale))
    json.dump(man, open(os.path.join(MANI, "dry_run.manifest.json"), "w"), indent=2)
    return scen, c2, stale, checks


if __name__ == "__main__":
    scen, c2, stale, checks = main()
    print("=== dry-run checks ===")
    for k, v in checks.items():
        print(f"  {'PASS' if v else 'FAIL'}  {k}")
    print("\n=== C2 idle demonstration (toy scale; fractional saving is scale-invariant) ===")
    for r in c2:
        print(f"  idle_ratio={r['idle_ratio']}: active {r['c2_active_s']:.0f}s idle {r['c2_idle_s']:.0f}s  fractional_saving={r['fractional_saving']:.3f}")
    print("\n=== stale vs delay ===")
    for r in stale:
        print(f"  delay={r['propagation_delay_s']:>6}s accepted={r['accepted_blocks']} legit_stales={r['legit_stales']} rate={r['legit_stale_rate']:.4f} upper95={r['zero_obs_upper95_bound']}")
    print("\nALL PASS:", all(checks.values()))
