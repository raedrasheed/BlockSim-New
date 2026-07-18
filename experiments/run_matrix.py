"""Phase B6 — multi-seed experiment matrix (fresh process per run).

Runs the full corrected comparison:

    protocols = {PoW, PoCol}
    miner counts = {100, 200, 300, 400, 500}
    seeds = 1..S   (default S=30  =>  2 x 5 x 30 = 300 runs)

Each individual run is executed in a FRESH Python interpreter
(`experiments/run_scenario.py`) so no global state leaks between runs. Seeds are
PAIRED: PoW and PoCol at the same (n, seed) share the same random stream seed,
enabling a paired comparison.

Outputs (results/corrected/):
    raw_runs.csv                one row per run (all metrics)
    summary_statistics.csv      mean/median/std/95%CI/min/max per (protocol,n),
                                plus the paired PoW-PoCol energy effect size
    configuration.json          the shared ScenarioConfig + protocol-specifics
    reproducibility_manifest.json  git commit, versions, seeds, exact commands

Usage:  python experiments/run_matrix.py [n_seeds] [max_workers]
"""
import os
import sys
import json
import math
import platform
import subprocess
import concurrent.futures as cf

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import numpy as np
import pandas as pd

from Models.scenario import ScenarioConfig, effective_params, PROTOCOL_SPECIFIC, MODEL_ID

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUTDIR = os.path.join(ROOT, "results", "corrected")
RUNNER = os.path.join(ROOT, "experiments", "run_scenario.py")

PROTOCOLS = ["PoW", "PoCol"]
MINER_COUNTS = [100, 200, 300, 400, 500]

# Metrics summarised in summary_statistics.csv
SUMMARY_METRICS = [
    "energy_kWh", "co2_kg", "created_blocks", "accepted_main_blocks",
    "stale_blocks", "stale_rate_pct", "accepted_block_interval_s",
    "created_block_interval_s", "throughput_tx_per_s",
    "confirmation_time_6blk_s", "energy_per_accepted_block_kWh",
    "energy_per_tx_kWh", "total_hashes", "active_mining_time_s",
    "exhausted_rounds",
]


def _run_one(protocol, n, seed):
    """Run a single (protocol, n, seed) in a fresh interpreter; return metrics dict."""
    cmd = [sys.executable, RUNNER, protocol, str(n), str(seed)]
    out = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
    if out.returncode != 0:
        raise RuntimeError(f"run failed {protocol} n={n} seed={seed}:\n{out.stderr[-2000:]}")
    line = out.stdout.strip().splitlines()[-1]
    rec = json.loads(line)
    rec["_cmd"] = " ".join(cmd)
    return rec


def _ci95(x):
    """Normal-approximation 95% CI for the mean (no scipy dependency)."""
    x = np.asarray(x, dtype=float)
    x = x[~np.isnan(x)]
    if len(x) < 2:
        return (float("nan"), float("nan"))
    se = np.std(x, ddof=1) / math.sqrt(len(x))
    m = float(np.mean(x))
    return (m - 1.96 * se, m + 1.96 * se)


def _summ(x):
    x = np.asarray(x, dtype=float)
    x = x[~np.isnan(x)]
    if len(x) == 0:
        return dict(mean=float("nan"), median=float("nan"), std=float("nan"),
                    ci95_low=float("nan"), ci95_high=float("nan"),
                    min=float("nan"), max=float("nan"), n=0)
    lo, hi = _ci95(x)
    return dict(
        mean=float(np.mean(x)), median=float(np.median(x)),
        std=float(np.std(x, ddof=1)) if len(x) > 1 else 0.0,
        ci95_low=lo, ci95_high=hi,
        min=float(np.min(x)), max=float(np.max(x)), n=int(len(x)),
    )


def _paired_cohens_d(diff):
    """Cohen's d for a paired sample = mean(diff)/std(diff)."""
    d = np.asarray(diff, dtype=float)
    d = d[~np.isnan(d)]
    if len(d) < 2 or np.std(d, ddof=1) == 0:
        return float("nan")
    return float(np.mean(d) / np.std(d, ddof=1))


def main(n_seeds=30, max_workers=8):
    seeds = list(range(1, n_seeds + 1))
    os.makedirs(OUTDIR, exist_ok=True)

    jobs = [(proto, n, s) for proto in PROTOCOLS for n in MINER_COUNTS for s in seeds]
    print(f"Running {len(jobs)} simulations ({len(PROTOCOLS)} protocols x "
          f"{len(MINER_COUNTS)} miner counts x {len(seeds)} seeds), "
          f"fresh process each, {max_workers} workers...")

    rows = []
    done = 0
    with cf.ThreadPoolExecutor(max_workers=max_workers) as ex:
        fut = {ex.submit(_run_one, p, n, s): (p, n, s) for (p, n, s) in jobs}
        for f in cf.as_completed(fut):
            p, n, s = fut[f]
            rows.append(f.result())
            done += 1
            if done % 25 == 0 or done == len(jobs):
                print(f"  {done}/{len(jobs)} complete")

    raw = pd.DataFrame(rows).sort_values(["protocol", "n_miners", "seed"]).reset_index(drop=True)
    raw_path = os.path.join(OUTDIR, "raw_runs.csv")
    raw.to_csv(raw_path, index=False)
    print(f"wrote {raw_path}  ({len(raw)} rows)")

    # ---- per (protocol, n) summary ----
    srows = []
    for proto in PROTOCOLS:
        for n in MINER_COUNTS:
            sub = raw[(raw.protocol == proto) & (raw.n_miners == n)]
            for metric in SUMMARY_METRICS:
                st = _summ(sub[metric].values)
                srows.append(dict(protocol=proto, n_miners=n, metric=metric, **st))
    summ = pd.DataFrame(srows)

    # ---- paired PoW vs PoCol energy effect size, per n ----
    prows = []
    for n in MINER_COUNTS:
        pw = raw[(raw.protocol == "PoW") & (raw.n_miners == n)].set_index("seed")
        pc = raw[(raw.protocol == "PoCol") & (raw.n_miners == n)].set_index("seed")
        common = sorted(set(pw.index) & set(pc.index))
        for metric in ("energy_kWh", "co2_kg", "energy_per_accepted_block_kWh"):
            dpw = pw.loc[common, metric].values.astype(float)
            dpc = pc.loc[common, metric].values.astype(float)
            diff = dpc - dpw            # PoCol minus PoW (positive => PoCol worse)
            mean_pw = float(np.nanmean(dpw))
            mean_pc = float(np.nanmean(dpc))
            pct = (100.0 * (mean_pc - mean_pw) / mean_pw) if mean_pw else float("nan")
            prows.append(dict(
                n_miners=n, metric=metric, comparison="PoCol_minus_PoW",
                pow_mean=mean_pw, pocol_mean=mean_pc,
                mean_diff=float(np.nanmean(diff)),
                pocol_vs_pow_pct=pct,
                paired_cohens_d=_paired_cohens_d(diff),
                n_pairs=len(common),
            ))
    paired = pd.DataFrame(prows)

    # write both into one summary file (tagged) + a dedicated paired file
    summ_path = os.path.join(OUTDIR, "summary_statistics.csv")
    summ.to_csv(summ_path, index=False)
    paired_path = os.path.join(OUTDIR, "paired_effect_size.csv")
    paired.to_csv(paired_path, index=False)
    print(f"wrote {summ_path}  ({len(summ)} rows)")
    print(f"wrote {paired_path}  ({len(paired)} rows)")

    # ---- configuration.json ----
    ref = ScenarioConfig(n_miners=MINER_COUNTS[0], seed=seeds[0])
    config = {
        "shared_parameters": {k: v for k, v in ref.shared_params().items() if k != "n_miners"},
        "experiment_axes": {"protocols": PROTOCOLS, "miner_counts": MINER_COUNTS, "seeds": seeds},
        "protocol_specific": {
            proto: effective_params(ref, proto)["_protocol_specific"] for proto in PROTOCOLS
        },
        "model_ids": MODEL_ID,
        "config_hash_shared": ref.config_hash(),
        "notes": (
            "config_hash covers protocol-INDEPENDENT parameters only and is "
            "identical for PoW and PoCol at a given miner count; seeds are paired."
        ),
    }
    cfg_path = os.path.join(OUTDIR, "configuration.json")
    with open(cfg_path, "w") as fh:
        json.dump(config, fh, indent=2)
    print(f"wrote {cfg_path}")

    # ---- reproducibility_manifest.json ----
    def _git(*args):
        try:
            return subprocess.run(["git", *args], capture_output=True, text=True,
                                  cwd=ROOT).stdout.strip()
        except Exception:
            return None

    manifest = {
        "git_commit": _git("rev-parse", "HEAD"),
        "git_branch": _git("rev-parse", "--abbrev-ref", "HEAD"),
        "git_dirty": bool(_git("status", "--porcelain")),
        "python_version": sys.version,
        "platform": platform.platform(),
        "packages": {"numpy": np.__version__, "pandas": pd.__version__},
        "n_runs": len(raw),
        "protocols": PROTOCOLS,
        "miner_counts": MINER_COUNTS,
        "seeds": seeds,
        "seed_pairing": "PoW and PoCol share the seed at each (n, seed)",
        "fresh_process_per_run": True,
        "runner": "experiments/run_scenario.py",
        "reproduce": "python experiments/run_matrix.py {} {}".format(n_seeds, max_workers),
        "per_run_commands_example": raw["_cmd"].iloc[0] if "_cmd" in raw else None,
        "config_hash_shared": ref.config_hash(),
    }
    man_path = os.path.join(OUTDIR, "reproducibility_manifest.json")
    with open(man_path, "w") as fh:
        json.dump(manifest, fh, indent=2)
    print(f"wrote {man_path}")

    # ---- console headline ----
    print("\n=== ENERGY (kWh) mean per protocol x miner count ===")
    piv = raw.pivot_table(index="n_miners", columns="protocol",
                          values="energy_kWh", aggfunc="mean")
    print(piv.to_string(float_format=lambda v: f"{v:.4f}"))
    print("\n=== paired PoCol vs PoW energy (%) ===")
    print(paired[paired.metric == "energy_kWh"][
        ["n_miners", "pow_mean", "pocol_mean", "pocol_vs_pow_pct", "paired_cohens_d"]
    ].to_string(index=False, float_format=lambda v: f"{v:.4f}"))
    return raw, summ, paired


if __name__ == "__main__":
    ns = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    mw = int(sys.argv[2]) if len(sys.argv) > 2 else 8
    main(ns, mw)
