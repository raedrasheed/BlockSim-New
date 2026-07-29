"""Stage 5A: build the FROZEN final Stage-5 experiment matrix (design only).

Emits a machine-readable matrix CSV, a frozen seed schedule, a hypothesis→run
mapping, and heterogeneous-distribution diagnostics. Deduplicates by
configuration_hash so no accidental duplicate configuration is planned. B3 and
C1 share ONE underlying run (interpretation labels "B3;C1") to prevent
pseudoreplication.
"""

from __future__ import annotations

import os
import csv
import json
import hashlib

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DOCS = os.path.join(ROOT, "docs", "thesis_revision_v43")
RAW = os.path.join(ROOT, "results", "thesis_revision_v43", "stage_05a", "raw")

# ---- frozen seed schedule ----
SEED_BASE = 20260201
N_SEEDS = 30
SEEDS = [SEED_BASE + i for i in range(N_SEEDS)]

# ---- fixed baseline ----
BASE = dict(network_hash_rate_hps=141e12, efficiency_j_per_th=21.5,
            simulation_duration_s=10000.0, target_block_interval_s=600.0,
            propagation_delay_mean_s=0.42, hash_rate_distribution="homogeneous",
            mu=2.0, inactive_miner_fraction=0.0, idle_power_ratio=0.0,
            allocation_policy="disjoint_equal")

COUNTS = [100, 200, 300, 400, 500]
EDGE_COUNTS = [100, 500]

# scenario -> (underlying_execution_model, interpretation_labels)
EXEC = {
    "B0": ("bitcoin_independent_pow", "B0"),
    "B1": ("direct_coverage_model", "B1"),
    "B2": ("direct_coverage_model", "B2"),
    "B3_C1_CONTINUOUS_DISJOINT": ("pocol_continuous", "B3;C1"),
    "C2": ("pocol_continuous+idle_transform", "C2"),
}

HETERO_SIGMA_MODERATE = 0.5
HETERO_SIGMA_HIGH = 1.0


def config_hash(cfg: dict) -> str:
    return hashlib.sha256(json.dumps(cfg, sort_keys=True).encode()).hexdigest()[:16]


def rows_for(matrix_class, hypothesis, scenario, counts, seeds, **overrides):
    out = []
    for N in counts:
        for seed in seeds:
            cfg = dict(BASE)
            cfg.update(overrides)
            cfg.update(scenario_id=scenario, miner_count=N, seed=seed)
            ch = config_hash(cfg)
            um, labels = EXEC[scenario]
            row = dict(cfg)
            row.update(hypothesis_id=hypothesis, matrix_class=matrix_class,
                       underlying_execution_model=um, interpretation_labels=labels,
                       configuration_hash=ch)
            out.append(row)
    return out


def build():
    rows = []
    # CORE confirmatory (H1 duplicate coverage, H2 energy equivalence)
    for scen in ("B0", "B1", "B2", "B3_C1_CONTINUOUS_DISJOINT"):
        rows += rows_for("CORE", "H1;H2", scen, COUNTS, SEEDS)
    # CORE C2 (H3, H4) homogeneous mu=2 idle=0 -- idle{5,10,20,30} redundant here
    rows += rows_for("CORE_C2", "H3;H4", "C2", COUNTS, SEEDS)
    # SENS idle-power (H3) where ranges complete early (mu=0.5) -> idle > 0
    for ratio in (0.0, 0.05, 0.10, 0.20, 0.30):
        rows += rows_for("SENS_IDLE", "H3", "C2", EDGE_COUNTS, SEEDS, mu=0.5, idle_power_ratio=ratio)
    # SENS heterogeneous + allocation (H5)
    for scen, idle in (("B3_C1_CONTINUOUS_DISJOINT", 0.0), ("C2", 0.10)):
        for alloc in ("disjoint_equal", "disjoint_weighted"):
            rows += rows_for("SENS_HETERO", "H5", scen, EDGE_COUNTS, SEEDS,
                             hash_rate_distribution="heterogeneous_moderate",
                             allocation_policy=alloc, idle_power_ratio=idle)
    # SENS mu (H8) -- exclude base mu=2 (in core)
    for mu in (0.5, 1.0):
        rows += rows_for("SENS_MU", "H8", "B3_C1_CONTINUOUS_DISJOINT", EDGE_COUNTS, SEEDS, mu=mu)
    # SENS inactive (H6) -- exclude base 0
    for frac in (0.05, 0.15, 0.30):
        rows += rows_for("SENS_INACTIVE", "H6", "B3_C1_CONTINUOUS_DISJOINT", EDGE_COUNTS, SEEDS,
                         inactive_miner_fraction=frac)
    # SENS delay (H7) -- exclude base 0.42
    for delay in (0.0, 5.0, 30.0, 60.0):
        rows += rows_for("SENS_DELAY", "H7", "B3_C1_CONTINUOUS_DISJOINT", EDGE_COUNTS, SEEDS,
                         propagation_delay_mean_s=delay)
    # EXPLORATORY high-concentration heterogeneity (separate, not pooled)
    rows += rows_for("EXPLORATORY", "H5x", "B3_C1_CONTINUOUS_DISJOINT", EDGE_COUNTS, SEEDS,
                     hash_rate_distribution="heterogeneous_high")

    # dedup by configuration_hash
    seen = {}
    deduped = []
    dups = 0
    for r in rows:
        key = (r["scenario_id"], r["configuration_hash"])
        if key in seen:
            dups += 1
            continue
        seen[key] = True
        deduped.append(r)
    for i, r in enumerate(deduped):
        r["run_id"] = f"S5-{i:05d}"
        r["expected_output_path"] = f"results/thesis_revision_v43/stage_05b/raw/{r['run_id']}.summary.json"
        r["planned_status"] = "PLANNED"
    return deduped, dups


def hetero_diagnostics():
    out = {}
    for name, sigma in (("moderate", HETERO_SIGMA_MODERATE), ("high", HETERO_SIGMA_HIGH)):
        for N in EDGE_COUNTS:
            g = np.random.default_rng(SEED_BASE)
            x = g.lognormal(mean=0.0, sigma=sigma, size=N)
            shares = x / x.sum()
            s = np.sort(shares)
            gini = float((2 * np.arange(1, N + 1) - N - 1).dot(s) / (N * s.sum()))
            out[f"{name}_N{N}"] = dict(sigma=sigma, gini=round(gini, 4),
                                       max_share=float(s[-1]), min_share=float(s[0]),
                                       median_share=float(np.median(shares)),
                                       max_over_mean=float(s[-1] * N))
    return out


def main():
    os.makedirs(RAW, exist_ok=True)
    rows, dups = build()
    fields = ["run_id", "hypothesis_id", "matrix_class", "scenario_id",
              "underlying_execution_model", "interpretation_labels", "seed",
              "miner_count", "network_hash_rate_hps", "efficiency_j_per_th",
              "simulation_duration_s", "target_block_interval_s",
              "propagation_delay_mean_s", "hash_rate_distribution", "mu",
              "inactive_miner_fraction", "idle_power_ratio", "allocation_policy",
              "configuration_hash", "expected_output_path", "planned_status"]
    with open(os.path.join(DOCS, "STAGE_05A_FINAL_MATRIX.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)

    # seed schedule (frozen)
    seed_blob = json.dumps(dict(seed_base=SEED_BASE, n_seeds=N_SEEDS, seeds=SEEDS), sort_keys=True)
    seed_sha = hashlib.sha256(seed_blob.encode()).hexdigest()
    json.dump(dict(seed_base=SEED_BASE, n_seeds=N_SEEDS, seeds=SEEDS, sha256=seed_sha),
              open(os.path.join(RAW, "seed_schedule.json"), "w"), indent=2)

    # hypothesis -> run mapping
    hmap = {}
    for r in rows:
        for h in r["hypothesis_id"].split(";"):
            hmap.setdefault(h, []).append(r["run_id"])
    json.dump(hmap, open(os.path.join(RAW, "hypothesis_to_run.json"), "w"), indent=2)

    # class/scenario/count breakdown
    by_class = {}
    by_scen = {}
    for r in rows:
        by_class[r["matrix_class"]] = by_class.get(r["matrix_class"], 0) + 1
        by_scen[r["scenario_id"]] = by_scen.get(r["scenario_id"], 0) + 1
    diagnostics = hetero_diagnostics()
    summary = dict(total_runs=len(rows), duplicate_configs_removed=dups,
                   by_class=by_class, by_scenario=by_scen, seed_sha256=seed_sha,
                   hetero_distribution_diagnostics=diagnostics)
    json.dump(summary, open(os.path.join(RAW, "matrix_summary.json"), "w"), indent=2)
    for p in ("seed_schedule.json", "hypothesis_to_run.json", "matrix_summary.json"):
        os.chmod(os.path.join(RAW, p), 0o444)
    return summary


if __name__ == "__main__":
    s = main()
    print(json.dumps(s, indent=2))
