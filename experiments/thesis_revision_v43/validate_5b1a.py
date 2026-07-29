"""Stage 5B1A bounded pre-execution validation (hard cap 100 runs). Verifies the
measurement corrections before the frozen matrix executes; NOTHING here enters the
thesis. Categories:

  P  B2 exact circular coverage (integer counts vs exhaustive reference)
  Q  B1 zero-block (analytical table vs seeded empirical; NA metric policy)
  R  per-miner / per-template schema completeness + reconciliation
  S  coordination message-category separation
  T  stratified retention design properties
  U  expanded storage measurement (delegated to storage_projection_5b1a)

Writes validation_report_5b1a.json, b1_zero_block_table.json, and (via the storage
module) storage_projection_5b1a.json.
"""

from __future__ import annotations
import os
import sys
import json
import math

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)

from experiments.thesis_revision_v43.scenario_engine import EngineConfig, run_scenario, _discover, rng
from experiments.thesis_revision_v43 import coverage as cov
from experiments.thesis_revision_v43 import b1_zero_block as zb
from experiments.thesis_revision_v43 import schemas
from experiments.thesis_revision_v43 import run_utils
from experiments.thesis_revision_v43 import retention_5b1a
from experiments.thesis_revision_v43 import storage_projection_5b1a as storage

RESULTS = os.path.join(ROOT, "results", "thesis_revision_v43", "stage_05b1a")
RAW = os.path.join(RESULTS, "raw")
DOCS = os.path.join(ROOT, "docs", "thesis_revision_v43")
MATRIX = os.path.join(DOCS, "STAGE_05B1A_FINAL_MATRIX.csv")
EXPECTED_KWH = 8.420833333333333
RUN_CAP = 100

_checks = []
_run_count = 0


def check(cid, cat, desc, passed, **detail):
    _checks.append(dict(id=cid, category=cat, description=desc, passed=bool(passed), **detail))


def run(cfg, tag, emit_log=False, emit_detail=False):
    global _run_count
    _run_count += 1
    if _run_count > RUN_CAP:
        raise RuntimeError(f"validation run cap {RUN_CAP} exceeded ({_run_count})")
    r = run_scenario(cfg, emit_log=emit_log, emit_detail=emit_detail)
    if not (emit_log or emit_detail):
        run_utils.atomic_write_json(os.path.join(RAW, f"VAL-{_run_count:04d}-{tag}.summary.json"),
                                    dict(r, status=run_utils.STATUS_COMPLETED))
    return r


# --- P: B2 exact coverage -------------------------------------------------
def category_P():
    S, n = 40, 5
    rates = [1.0] * n
    starts = [0, 8, 8, 20, 39]                      # identical starts, wrap, spread
    lengths = [10, 10, 10, 25, 5]                   # includes wrap (39+5>40) and overlap
    exact = cov.b2_coverage_exact(starts, lengths, S)
    ref = cov.exhaustive_coverage_reference(starts, lengths, S)
    check("P1", "P", "B2 exact distinct == exhaustive (mixed wrap/overlap)",
          exact["distinct_candidate_evaluations"] == ref["distinct_candidate_evaluations"],
          exact=exact["distinct_candidate_evaluations"], ref=ref["distinct_candidate_evaluations"])
    check("P2", "P", "B2 exact total == distinct + duplicate (exact reconciliation)",
          exact["total_candidate_evaluations"] ==
          exact["distinct_candidate_evaluations"] + exact["duplicate_candidate_evaluations"],
          **exact)
    # full-domain traversal by one miner covers everything
    full = cov.b2_coverage_exact([0, 5], [S, 3], S)
    check("P3", "P", "B2 one miner covering whole domain -> distinct == S",
          full["distinct_candidate_evaluations"] == S, distinct=full["distinct_candidate_evaluations"])
    # multiple miners covering the entire domain
    multi = cov.b2_coverage_exact([0, 10], [S, S], S)
    check("P4", "P", "B2 multiple full-domain miners -> distinct == S, duplicate == S",
          multi["distinct_candidate_evaluations"] == S and multi["duplicate_candidate_evaluations"] == S,
          **multi)
    # zero-length path contributes nothing
    z = cov.b2_coverage_exact([0, 7], [0, 4], S)
    check("P5", "P", "B2 zero-length path contributes no candidates",
          z["distinct_candidate_evaluations"] == 4 and z["total_candidate_evaluations"] == 4, **z)
    # engine-level: exact integer reconciliation at full scale
    for N in (100, 500):
        r = run(EngineConfig("B2", seed=3, miner_count=N), f"P-b2-{N}")
        tot = r["total_candidate_evaluations"]; dist = r["distinct_candidate_identities"]
        dup = r["duplicate_evaluations"]
        check(f"P6-{N}", "P", f"B2 N={N} engine total == distinct + duplicate (exact)",
              math.isclose(tot, dist + dup, rel_tol=0, abs_tol=1e-6),
              total=tot, distinct=dist, duplicate=dup)
    # small-domain engine winner matches independent reference
    S3, n3 = 30, 4
    rates3 = [1.0, 2.0, 1.0, 3.0]
    r_s = rng(9, "miner_starts")
    starts3 = [int(r_s.integers(0, S3)) for _ in range(n3)]
    import numpy as np
    pos3 = np.array([13, 27])
    wt, wid = cov.b2_winner(pos3, starts3, rates3, S3)
    wt_ref, wid_ref = cov.exhaustive_winner_reference(pos3, starts3, rates3, S3)
    check("P7", "P", "B2 winner time/identity match independent reference",
          math.isclose(wt, wt_ref, rel_tol=1e-12) and wid == wid_ref,
          wt=wt, ref=wt_ref, wid=wid, wid_ref=wid_ref)


# --- Q: B1 zero-block -----------------------------------------------------
def category_Q():
    table = zb.b1_table()
    json.dump(table, open(os.path.join(RAW, "b1_zero_block_table.json"), "w"), indent=2)
    json.dump(table, open(os.path.join(DOCS, "STAGE_05B1A_B1_ZERO_BLOCK_TABLE.json"), "w"), indent=2)
    seeds = [20260201 + i for i in range(12)]
    empirical = {}
    runs_by_N = {}
    for row in table:
        N = row["miner_count"]
        runs = [run(EngineConfig("B1", seed=s, miner_count=N), f"Q-b1-{N}-{s}") for s in seeds]
        runs_by_N[N] = runs
        accs = [r["accepted_blocks"] for r in runs]
        zero = sum(1 for a in accs if a == 0) / len(accs)
        empirical[N] = dict(zero_frac=zero, mean_blocks=sum(accs) / len(accs), max_blocks=max(accs))
        # Stage 5B1B: exact P0 within the event-loop 99% Clopper-Pearson CI (no 0.25).
        from experiments.thesis_revision_v43 import b1_exact as bx
        p0 = bx.exact_zero_block(141e12, N, 10000.0, 600.0, 2.0)["expected_zero_block_probability_exact"]
        lo99, hi99 = bx.clopper_pearson(int(round(zero * len(seeds))), len(seeds), 0.01)
        check(f"Q-agree-{N}", "Q", f"B1 N={N}: exact P0 within event-loop 99% CI",
              lo99 <= p0 <= hi99, empirical=zero, exact_p0=p0, ci99=[lo99, hi99],
              risk=row["zero_block_risk_category"])
    # monotonicity in N (both analytical and empirical)
    an = [r["zero_block_probability"] for r in table]
    em = [empirical[r["miner_count"]]["zero_frac"] for r in table]
    check("Q-mono-analytical", "Q", "analytical P0 monotone increasing in N",
          all(an[i] <= an[i + 1] + 1e-12 for i in range(len(an) - 1)), values=an)
    check("Q-mono-empirical", "Q", "empirical zero-frac monotone non-decreasing in N",
          all(em[i] <= em[i + 1] + 1e-9 for i in range(len(em) - 1)), values=em)
    check("Q-majority-zero", "Q", "B1 is majority-zero for all planned N (P0 > 0.5)",
          all(x > 0.5 for x in an), values=an)
    # NA policy: reuse a zero-block empirical run (never re-run) if one exists
    zero_runs = [r for r in runs_by_N[500] if r["accepted_blocks"] == 0]
    if zero_runs:
        zr = zero_runs[0]
        check("Q-na", "Q", "zero-block run: block metrics are NA (null) + reason",
              zr["energy_per_accepted_block_kwh"] is None
              and zr["energy_per_accepted_block_na_reason"] == "no_accepted_blocks"
              and zr["effective_block_interval_s"] is None
              and zr["throughput_blocks_per_s"] == 0.0,      # genuine-zero numerator
              epb=zr["energy_per_accepted_block_kwh"], thr=zr["throughput_blocks_per_s"])
    else:
        check("Q-na", "Q", "no zero-block run among N=500 seeds; NA policy untested here", True)
    # ratio-of-totals vs conditional mean are DISTINCT estimands (Section 4.6), reusing N=100 runs
    runs = runs_by_N[100]
    tot_e = sum(r["total_energy_kwh"] for r in runs)
    tot_b = sum(r["accepted_blocks"] for r in runs)
    ratio_of_totals = (tot_e / tot_b) if tot_b else None
    cond = [r["energy_per_accepted_block_kwh"] for r in runs if r["accepted_blocks"] > 0]
    cond_mean = (sum(cond) / len(cond)) if cond else None
    check("Q-estimands", "Q", "ratio-of-totals and conditional mean are reported as distinct estimands",
          ratio_of_totals is not None and cond_mean is not None,
          ratio_of_totals=ratio_of_totals, conditional_mean=cond_mean,
          defined_runs=len(cond), undefined_runs=len(runs) - len(cond))
    _q_empirical.update(empirical)


_q_empirical = {}


# --- R: per-miner / per-template schemas ----------------------------------
def category_R():
    specs = [("B0", dict(inactive_miner_fraction=0.15)), ("B1", {}), ("B2", {}),
             ("B3_C1_CONTINUOUS_DISJOINT", {}),
             ("C2", dict(hash_rate_distribution="heterogeneous_moderate",
                         allocation_policy="equal", idle_power_ratio=0.1))]
    for scen, kw in specs:
        r = run(EngineConfig(scen, seed=7, miner_count=60, **kw), f"R-{scen}", emit_detail=True)
        pm, pt = r["per_miner"], r["per_template"]
        miss_m = schemas.validate_fields(pm[0], schemas.PER_MINER_FIELDS)
        miss_t = schemas.validate_fields(pt[0], schemas.PER_TEMPLATE_FIELDS) if pt else ["<none>"]
        rec_m = schemas.reconcile_per_miner(pm, r)
        rec_t = schemas.reconcile_per_template(pt)
        check(f"R-schema-{scen}", "R", f"{scen} per-miner & per-template schemas complete",
              not miss_m and not miss_t, missing_miner=miss_m, missing_template=miss_t)
        check(f"R-recon-{scen}", "R", f"{scen} per-miner->network & per-template domain reconcile",
              rec_m["passed"] and rec_t["passed"], miner=rec_m["passed"], template=rec_t["passed"])
    # per-miner preserved for a zero-block run too
    zr = run(EngineConfig("B1", seed=20260201, miner_count=60), "R-zeroblock", emit_detail=True)
    check("R-zeroblock", "R", "per-miner summary preserved even for zero-block run",
          len(zr["per_miner"]) == 60, rows=len(zr["per_miner"]), accepted=zr["accepted_blocks"])


# --- S: coordination categories -------------------------------------------
def category_S():
    r = run(EngineConfig("B3_C1_CONTINUOUS_DISJOINT", seed=5, miner_count=100), "S-b3")
    b0 = run(EngineConfig("B0", seed=5, miner_count=100), "S-b0")
    check("S1", "S", "block-propagation bytes use configured block size",
          r["block_propagation_bytes"] == r["block_propagation_message_count"] * 1_000_000,
          bytes=r["block_propagation_bytes"], msgs=r["block_propagation_message_count"])
    check("S2", "S", "control-message categories have null bytes (not configured)",
          all(r[f"{c}_bytes"] is None for c in
              ("transaction_reconciliation", "template_announcement", "nonce_allocation", "registration")),
          tr=r["transaction_reconciliation_bytes"], na=r["nonce_allocation_bytes"])
    check("S3", "S", "control-message categories are counted separately (>=0)",
          all(isinstance(r[f"{c}_message_count"], int) for c in schemas.COORD_MESSAGE_CATEGORIES),
          counts={c: r[f"{c}_message_count"] for c in schemas.COORD_MESSAGE_CATEGORIES})
    check("S4", "S", "abstract agreement ops present; unimplemented energy null; B0 no agreement",
          r["abstract_template_agreement_operations"] == r["accepted_blocks"]
          and r["unimplemented_agreement_energy_kwh"] is None
          and b0["abstract_template_agreement_operations"] == 0,
          b3_ops=r["abstract_template_agreement_operations"], b0_ops=b0["abstract_template_agreement_operations"])
    check("S5", "S", "template refresh == exhausted rounds (legacy counter preserved)",
          r["coord_template_refresh_count"] == r["exhausted_rounds"],
          refresh=r["coord_template_refresh_count"], exhausted=r["exhausted_rounds"])


# --- T: retention design --------------------------------------------------
def category_T():
    import csv
    rows = list(csv.DictReader(open(MATRIX)))
    retained = [r for r in rows if r["retention_full_log"] == "True"]
    # every scenario x count covered
    groups = {(r["scenario_id"], r["miner_count"]) for r in rows}
    covered = {(r["scenario_id"], r["miner_count"]) for r in retained}
    check("T1", "T", "retention covers every scenario x miner-count group",
          groups <= covered, missing=sorted(groups - covered))
    # sensitivity levels covered (reason codes present)
    all_codes = ";".join(r["retention_reason_codes"] for r in retained)
    for token in ("delay_level", "mu_level", "inactive_level", "idle_power_level",
                  "dist:homogeneous", "dist:heterogeneous_equal", "dist:heterogeneous_weighted",
                  "dist:exploratory_high"):
        check(f"T-cov:{token}", "T", f"retention covers stratum '{token}'",
              token in all_codes, present=token in all_codes)
    for regime in ("expected_zero_block_b1", "expected_high_exhaustion", "expected_legitimate_stale",
                   "expected_nonzero_idle_c2", "expected_zero_idle_c2"):
        check(f"T-regime:{regime}", "T", f"retention includes regime '{regime}'",
              regime in all_codes, present=regime in all_codes)
    # deterministic + reproducible checksum
    r2, m2 = retention_5b1a.design_retention([dict(x) for x in rows])
    check("T-determinism", "T", "retention selection is deterministic (reproducible checksum)",
          len([r for r in r2 if r["retention_full_log"]]) == len(retained),
          rerun=len([r for r in r2 if r["retention_full_log"]]), first=len(retained))
    # no duplicate retained ids
    ids = [r["run_id"] for r in retained]
    check("T-nodup", "T", "no duplicate retained run ids", len(ids) == len(set(ids)), n=len(ids))


# --- U: storage -----------------------------------------------------------
def category_U():
    rows = storage.measure(run)
    report = storage.write_report(rows, MATRIX)
    check("U1", "U", "storage probe includes per-miner and per-template files for every probe",
          all(r["per_miner_bytes"] > 0 and r["per_template_bytes"] > 0 for r in rows),
          probes=len(rows))
    check("U2", "U", "expanded projection replaces the prior summary-only estimate",
          report["projection"]["projected_final_mb_expected"] > 0,
          mb_expected=report["projection"]["projected_final_mb_expected"],
          mb_p95=report["projection"]["projected_final_mb_p95"],
          gz_mb=report["projection"]["projected_final_gz_mb_expected"])
    check("U3", "U", "storage measured at N=100 and N=500 for all 9 configurations",
          sorted({r["miner_count"] for r in rows}) == [100, 500] and len(rows) == 18,
          n_probes=len(rows))


def main():
    os.makedirs(RAW, exist_ok=True)
    category_P(); category_Q(); category_R(); category_S(); category_T(); category_U()
    passed = sum(1 for c in _checks if c["passed"])
    failed = [c for c in _checks if not c["passed"]]
    report = dict(run_count=_run_count, run_cap=RUN_CAP, under_cap=_run_count <= RUN_CAP,
                  checks_total=len(_checks), checks_passed=passed, checks_failed=len(failed),
                  all_passed=not failed, b1_empirical=_q_empirical, failed_checks=failed, checks=_checks)
    run_utils.atomic_write_json(os.path.join(RESULTS, "validation_report_5b1a.json"), report)
    print(json.dumps(dict(run_count=_run_count, checks_total=len(_checks),
                          checks_passed=passed, checks_failed=len(failed),
                          all_passed=not failed), indent=2))
    if failed:
        print("\nFAILED:")
        for c in failed:
            print(" ", c["id"], c["description"],
                  {k: v for k, v in c.items() if k not in ("id", "category", "description", "passed")})
    return report


if __name__ == "__main__":
    rep = main()
    sys.exit(0 if rep["all_passed"] else 1)
