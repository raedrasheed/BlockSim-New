"""Stage 5B1: regenerate the final matrix with three-tier hashing and semantic
deduplication.

The *naive* experimental plan enumerates every interpretive scenario the thesis
discusses as an independent intended execution. In particular a naive plan lists
B3 (disjoint-continuous energy interpretation) and C1 (disjoint-continuous
collaboration interpretation) as two separate run families over the same grid,
because a reader does not know a priori that they are the identical execution.

The three-tier audit discovers this:
  * configuration_hash       -> distinguishes every labelled planned row.
  * execution_semantics_hash -> drops interpretation-only labels and parameters
                                proven inactive; B3 and C1 collapse to one hash,
                                so one physical run serves both.
  * analysis_group_hash      -> identifies the paired analysis groups.

This module preserves the Stage-5A frozen matrix (immutable) and writes a new
versioned matrix + changelog. It does NOT execute the matrix.
"""

from __future__ import annotations
import os
import csv
import json
import hashlib

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DOCS = os.path.join(ROOT, "docs", "thesis_revision_v43")
RAW = os.path.join(ROOT, "results", "thesis_revision_v43", "stage_05b1", "raw")

from experiments.thesis_revision_v43 import hashing

SEED_BASE = 20260201
SEEDS = [SEED_BASE + i for i in range(30)]
COUNTS = [100, 200, 300, 400, 500]
EDGE = [100, 500]
BASE = dict(network_hash_rate_hps=141e12, efficiency_j_per_th=21.5,
            simulation_duration_s=10000.0, target_block_interval_s=600.0,
            propagation_delay_mean_s=0.42, hash_rate_distribution="homogeneous",
            mu=2.0, inactive_miner_fraction=0.0, idle_power_ratio=0.0,
            allocation_policy="disjoint_equal")

# underlying execution model per scenario_id
EXEC_MODEL = {"B0": "independent_full_parallel", "B1": "common_from_zero",
              "B2": "common_random_start",
              "B3_C1_CONTINUOUS_DISJOINT": "common_disjoint_continuous",
              "C2": "common_disjoint_idle"}

# naive interpretive label(s) each scenario_id is enumerated under.
# B3_C1 is planned twice (B3 and C1) in the naive plan; the audit collapses them.
NAIVE_LABELS = {"B0": ["B0"], "B1": ["B1"], "B2": ["B2"],
                "B3_C1_CONTINUOUS_DISJOINT": ["B3", "C1"], "C2": ["C2"]}


def rows_for(mclass, hyp, scen, counts, seeds, validation=False, **ov):
    """Emit naive planned rows. B3_C1 is emitted once per interpretive label
    (B3, C1) so the audit can demonstrate the collapse."""
    out = []
    for N in counts:
        for sd in seeds:
            cfg = dict(BASE)
            cfg.update(ov)
            cfg.update(scenario_id=scen, miner_count=N, seed=sd)
            um = EXEC_MODEL[scen]
            for label in NAIVE_LABELS[scen]:
                # configuration_hash includes the interpretive label + hypothesis
                # -> B3 and C1 planned rows are distinct planned entries.
                cfg_full = dict(cfg, interpretation_labels=label, hypothesis_id=hyp,
                                matrix_class=mclass)
                out.append(dict(cfg, hypothesis_id=hyp, matrix_class=mclass,
                                underlying_execution_model=um,
                                interpretation_labels=label,
                                configuration_hash=hashing.configuration_hash(cfg_full),
                                execution_semantics_hash=hashing.execution_semantics_hash(cfg),
                                analysis_group_hash=hashing.analysis_group_hash(cfg_full),
                                validation_only=validation))
    return out


def build():
    rows = []
    for scen in ("B0", "B1", "B2", "B3_C1_CONTINUOUS_DISJOINT"):
        rows += rows_for("CORE", "H1;A1", scen, COUNTS, SEEDS)
    rows += rows_for("CORE_C2", "H3;H4", "C2", COUNTS, SEEDS)                       # homogeneous idle=0
    for ratio in (0.0, 0.05, 0.10, 0.20, 0.30):                                     # idle sweep at mu=0.5
        rows += rows_for("SENS_IDLE", "H3", "C2", EDGE, SEEDS, mu=0.5, idle_power_ratio=ratio)
    for scen, idle in (("B3_C1_CONTINUOUS_DISJOINT", 0.0), ("C2", 0.10)):
        for alloc in ("disjoint_equal", "disjoint_weighted"):
            rows += rows_for("SENS_HETERO", "H5", scen, EDGE, SEEDS,
                             hash_rate_distribution="heterogeneous_moderate",
                             allocation_policy=alloc, idle_power_ratio=idle)
    for mu in (0.5, 1.0):
        rows += rows_for("SENS_MU", "H8", "B3_C1_CONTINUOUS_DISJOINT", EDGE, SEEDS, mu=mu)
    for frac in (0.05, 0.15, 0.30):
        rows += rows_for("SENS_INACTIVE", "H6", "B3_C1_CONTINUOUS_DISJOINT", EDGE, SEEDS,
                         inactive_miner_fraction=frac)
    for delay in (0.0, 5.0, 30.0, 60.0):
        rows += rows_for("SENS_DELAY", "H7", "B3_C1_CONTINUOUS_DISJOINT", EDGE, SEEDS,
                         propagation_delay_mean_s=delay)
    rows += rows_for("EXPLORATORY", "H5x", "B3_C1_CONTINUOUS_DISJOINT", EDGE, SEEDS,
                     hash_rate_distribution="heterogeneous_high")
    return rows


def _is_b3c1_pair(a, b):
    """True if the two rows are the B3/C1 interpretive pair of one execution."""
    return (a["underlying_execution_model"] == "common_disjoint_continuous"
            and b["underlying_execution_model"] == "common_disjoint_continuous"
            and {a["interpretation_labels"], b["interpretation_labels"]} <= {"B3", "C1", "B3;C1"})


def dedup():
    rows = build()
    naive = len(rows)

    # --- stage 1: exact-duplicate removal (configuration_hash) ---
    seen_cfg = {}
    after_exact = []
    exact_removed = 0
    for r in rows:
        k = r["configuration_hash"]
        if k in seen_cfg:
            exact_removed += 1
            continue
        seen_cfg[k] = r
        after_exact.append(r)

    # --- stage 2: semantic-duplicate removal (execution_semantics_hash) ---
    # one physical run per execution_semantics_hash; folded labels recorded.
    seen_sem = {}
    final = []
    b3c1_merged = 0
    other_semantic_removed = 0
    for r in after_exact:
        k = r["execution_semantics_hash"]
        if k in seen_sem:
            keeper = seen_sem[k]
            if _is_b3c1_pair(keeper, r):
                b3c1_merged += 1
            else:
                other_semantic_removed += 1
            # merge labels + record reuse
            labs = set(keeper["interpretation_labels"].split(";"))
            labs.update(r["interpretation_labels"].split(";"))
            keeper["interpretation_labels"] = ";".join(sorted(labs))
            keeper.setdefault("reused_by_hypotheses", set()).add(r["hypothesis_id"])
            continue
        seen_sem[k] = r
        final.append(r)

    # normalise reuse field
    for r in final:
        r["reused_by_hypotheses"] = ";".join(sorted(r.get("reused_by_hypotheses", set()))) \
            if r.get("reused_by_hypotheses") else ""

    # --- assign ids + retention flag ---
    per_sc = {}
    for i, r in enumerate(final):
        r["run_id"] = f"S5B2-{i:05d}"
        r["expected_output_path"] = f"results/thesis_revision_v43/stage_05b2/raw/{r['run_id']}.summary.json"
        r["planned_status"] = "PLANNED"
        sc = (r["scenario_id"], r["miner_count"])
        first = sc not in per_sc
        per_sc[sc] = True
        onepct = (i % 100 == 0)                       # ~1% deterministic full-log sample
        r["retain_full_log"] = bool(first or onepct)

    stats = dict(naive_planned_rows=naive, exact_duplicates_removed=exact_removed,
                 b3_c1_merged=b3c1_merged, other_semantic_duplicates_removed=other_semantic_removed,
                 final_stage5b2_run_count=len(final))
    return final, stats


def write(final, stats):
    fields = ["run_id", "scenario_id", "interpretation_labels", "reused_by_hypotheses",
              "hypothesis_id", "matrix_class", "seed", "miner_count",
              "underlying_execution_model", "network_hash_rate_hps",
              "efficiency_j_per_th", "simulation_duration_s", "target_block_interval_s",
              "propagation_delay_mean_s", "hash_rate_distribution", "mu", "inactive_miner_fraction",
              "idle_power_ratio", "allocation_policy", "configuration_hash",
              "execution_semantics_hash", "analysis_group_hash", "validation_only",
              "retain_full_log", "expected_output_path", "planned_status"]
    os.makedirs(DOCS, exist_ok=True)
    with open(os.path.join(DOCS, "STAGE_05B1_FINAL_MATRIX.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in final:
            w.writerow(r)

    by_class = {}
    by_scen = {}
    retain = 0
    for r in final:
        by_class[r["matrix_class"]] = by_class.get(r["matrix_class"], 0) + 1
        by_scen[r["scenario_id"]] = by_scen.get(r["scenario_id"], 0) + 1
        retain += int(r["retain_full_log"])
    retain_list = sorted(r["run_id"] for r in final if r["retain_full_log"])
    retain_sha = hashlib.sha256(json.dumps(retain_list, sort_keys=True).encode()).hexdigest()

    n = stats["final_stage5b2_run_count"]
    summary = dict(
        naive_planned_rows=stats["naive_planned_rows"],
        exact_duplicates_removed=stats["exact_duplicates_removed"],
        b3_c1_merged=stats["b3_c1_merged"],
        other_semantic_duplicates_removed=stats["other_semantic_duplicates_removed"],
        final_stage5b2_run_count=n,
        validation_only_rows=sum(int(r["validation_only"]) for r in final),
        by_class=by_class, by_scenario=by_scen,
        ceiling=3500, under_ceiling=n <= 3500,
        full_log_retained=retain, retention_sample_sha256=retain_sha,
        distinct_configuration_hashes=len(set(r["configuration_hash"] for r in final)),
        distinct_execution_semantics_hashes=len(set(r["execution_semantics_hash"] for r in final)),
        distinct_analysis_group_hashes=len(set(r["analysis_group_hash"] for r in final)),
        seed_schedule_sha256=hashlib.sha256(json.dumps(
            dict(seed_base=SEED_BASE, n_seeds=30, seeds=SEEDS), sort_keys=True).encode()).hexdigest())
    os.makedirs(RAW, exist_ok=True)
    json.dump(summary, open(os.path.join(RAW, "matrix_5b1_summary.json"), "w"), indent=2)
    json.dump(dict(run_ids=retain_list, sha256=retain_sha),
              open(os.path.join(RAW, "full_log_retention_sample.json"), "w"), indent=2)
    return summary


if __name__ == "__main__":
    final, stats = dedup()
    s = write(final, stats)
    print(json.dumps(s, indent=2))
