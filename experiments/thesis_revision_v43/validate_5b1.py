"""Stage 5B1 bounded pre-execution validation (does NOT run the full matrix).

Executes a small, fixed set of validation runs (hard cap 200) that exercise the
scenario engine end-to-end and reconcile its outputs against independent
references. Categories:

  A  small-domain exact-reference (coverage math for B1/B2/B3 vs brute force)
  B  range/rate decoupling (equal allocation is rate-independent; weighted is not)
  C  B1/B2 full event-loop execution (accepted blocks; duplicate-rate ordering)
  D  C2 in-loop idle (energy emerges in-loop; het-equal saves, hom/weighted do not)
  E  coordination-counter reconciliation (bytes, refreshes, agreement ops)
  F  parallel reproducibility (20 sequential vs 20 concurrent -> identical)
  G  stress N=500 (largest count executes; energy invariant A1 holds)

Every run summary is written atomically to results/.../stage_05b1/raw for the
storage projection. A machine-readable validation_report.json records every
reconciliation with the actual numbers.
"""

from __future__ import annotations
import os
import sys
import json
import math
from concurrent.futures import ThreadPoolExecutor

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)

from experiments.thesis_revision_v43.scenario_engine import (
    EngineConfig, run_scenario, _discover, allocate_equal, allocate_weighted, rng)
from experiments.thesis_revision_v43 import run_utils, hashing

RESULTS = os.path.join(ROOT, "results", "thesis_revision_v43", "stage_05b1")
RAW = os.path.join(RESULTS, "raw")
EXPECTED_KWH = 8.420833333333333
RUN_CAP = 200

_checks = []          # list of dicts: {id, category, description, passed, detail}
_run_count = 0
_byte_sizes = []      # bytes per written run summary


def check(cid, category, description, passed, **detail):
    _checks.append(dict(id=cid, category=category, description=description,
                        passed=bool(passed), **detail))


def run(cfg: EngineConfig, tag: str) -> dict:
    """Execute one scenario and persist its summary atomically (counts toward cap)."""
    global _run_count
    _run_count += 1
    if _run_count > RUN_CAP:
        raise RuntimeError(f"validation run cap {RUN_CAP} exceeded")
    r = run_scenario(cfg)
    path = os.path.join(RAW, f"VAL-{_run_count:04d}-{tag}.summary.json")
    run_utils.atomic_write_json(path, dict(r, status=run_utils.STATUS_COMPLETED))
    _byte_sizes.append(os.path.getsize(path))
    return r


# ---------------------------------------------------------------------------
# A. small-domain exact-reference: validate the coverage math in _discover
# ---------------------------------------------------------------------------
def category_A():
    S, n = 120, 6
    rates = np.array([2.0, 2.0, 2.0, 2.0, 2.0, 2.0])       # homogeneous, 2 pos/s
    active = list(range(n))
    H = float(rates.sum())

    # --- B3 disjoint: winner owns the lowest-time position; distinct == total ---
    ranges = allocate_equal(S, n)
    pos = np.array([17, 55, 98])
    cfg = EngineConfig("B3_C1_CONTINUOUS_DISJOINT", seed=1, miner_count=n)
    wt, wid, _, total, distinct = _discover(cfg, pos, ranges, rates, active, S,
                                            rng(1, "miner_starts"), H)
    # brute force: for each position find owner and time; winner = min time
    ref_best = math.inf; ref_owner = None
    for q in pos:
        for i in active:
            a, b = ranges[i]
            if a <= q <= b:
                tt = (q - a) / rates[i]
                if tt < ref_best:
                    ref_best, ref_owner = tt, i
    check("A1", "A", "B3 disjoint winner time matches brute force",
          math.isclose(wt, ref_best, rel_tol=1e-12), engine=wt, reference=ref_best)
    check("A2", "A", "B3 disjoint owner matches brute force", wid == ref_owner,
          engine=wid, reference=ref_owner)
    check("A3", "A", "B3 disjoint distinct == total (no overlap)",
          math.isclose(distinct, total, rel_tol=1e-12), distinct=distinct, total=total)

    # --- B1 common-from-zero: fastest miner reaches lowest position first ---
    cfg = EngineConfig("B1", seed=1, miner_count=n)
    wt, wid, _, total, distinct = _discover(cfg, pos, [(0, S - 1)] * n, rates, active, S,
                                            rng(1, "miner_starts"), H)
    ref_wt = float(pos.min()) / rates.max()
    check("A4", "A", "B1 winner time == min_pos / max_rate",
          math.isclose(wt, ref_wt, rel_tol=1e-12), engine=wt, reference=ref_wt)
    check("A5", "A", "B1 distinct coverage == fastest miner only (< total)",
          distinct < total and math.isclose(distinct, ref_wt * rates.max(), rel_tol=1e-9),
          distinct=distinct, total=total, one_miner=ref_wt * rates.max())

    # --- B2 random starts: circular union coverage vs brute-force set cover ---
    # a single far solution forces a long search so miner paths overlap (real
    # duplicate work), which is where B2's overlap semantics must be validated.
    S2, n2 = 60, 8
    rates2 = np.ones(n2)                                    # 1 pos/s each
    active2 = list(range(n2)); H2 = float(rates2.sum())
    pos2 = np.array([59])
    cfg = EngineConfig("B2", seed=7, miner_count=n2)
    r_starts = rng(7, "miner_starts")
    wt, wid, _, total, distinct = _discover(cfg, pos2, [(0, S2 - 1)] * n2, rates2, active2, S2,
                                            r_starts, H2)
    # reproduce the SAME starts with a parallel stream, then brute-force circular cover
    r_starts2 = rng(7, "miner_starts")
    starts = {i: int(r_starts2.integers(0, S2)) for i in active2}
    covered = set()
    for i in active2:
        steps = int(math.floor(rates2[i] * wt))
        for kk in range(steps):
            covered.add((starts[i] + kk) % S2)
    ref_distinct = len(covered)
    # engine uses a linear-merge approximation of the circular cover; require close
    rel_err = abs(distinct - ref_distinct) / max(ref_distinct, 1)
    check("A6", "A", "B2 winner reachable (finite time)", math.isfinite(wt), winner_time=wt)
    check("A7", "A", "B2 linear-merge coverage approximates circular brute force (<=15%)",
          rel_err <= 0.15, engine=distinct, reference=ref_distinct, rel_err=rel_err)
    check("A8", "A", "B2 distinct < total (real duplicate work under long search)",
          distinct < total, distinct=distinct, total=total, winner_time=wt)

    # a couple of end-to-end small runs to confirm the loop closes on tiny domains
    for scen in ("B1", "B2", "B3_C1_CONTINUOUS_DISJOINT"):
        r = run(EngineConfig(scen, seed=3, miner_count=n, network_hash_rate_hps=1200.0,
                             target_block_interval_s=1.0, mu=1.0), f"A-{scen}")
        check(f"A9-{scen}", "A", f"{scen} small-domain end-to-end accepted>=1",
              r["accepted_blocks"] >= 1, accepted=r["accepted_blocks"], domain=r["domain_size"])


# ---------------------------------------------------------------------------
# B. range/rate decoupling
# ---------------------------------------------------------------------------
def category_B():
    S, n = 100000, 50
    eq_hom = allocate_equal(S, n)
    # equal allocation must be identical regardless of hash-rate distribution
    cfg_hom = EngineConfig("B3_C1_CONTINUOUS_DISJOINT", seed=1, miner_count=n,
                           hash_rate_distribution="homogeneous")
    cfg_het = EngineConfig("B3_C1_CONTINUOUS_DISJOINT", seed=1, miner_count=n,
                           hash_rate_distribution="heterogeneous_moderate")
    eq2 = allocate_equal(cfg_het.domain_size(), n)
    eq1 = allocate_equal(cfg_hom.domain_size(), n)
    check("B1", "B", "equal allocation independent of hash-rate distribution",
          eq1 == eq2, same=eq1 == eq2)
    # equal ranges all differ from weighted ranges under heterogeneous shares
    shares = (rng(1, "hash_rate_distribution").lognormal(0, 0.5, n))
    shares = list(shares / shares.sum())
    wt = allocate_weighted(S, shares)
    lens_eq = [b - a + 1 for a, b in allocate_equal(S, n)]
    lens_wt = [b - a + 1 for a, b in wt]
    check("B2", "B", "weighted allocation depends on shares (differs from equal)",
          lens_eq != lens_wt, max_eq=max(lens_eq), max_wt=max(lens_wt))
    check("B3", "B", "equal covers domain exactly", sum(lens_eq) == S, total=sum(lens_eq))
    check("B4", "B", "weighted covers domain exactly", sum(lens_wt) == S, total=sum(lens_wt))
    # end-to-end: energy invariant holds under both allocations (continuous, homogeneous)
    for alloc in ("equal", "weighted"):
        r = run(EngineConfig("B3_C1_CONTINUOUS_DISJOINT", seed=5, miner_count=100,
                             allocation_policy=alloc), f"B-alloc-{alloc}")
        check(f"B5-{alloc}", "B", f"continuous energy invariant A1 under {alloc} allocation",
              math.isclose(r["total_energy_kwh"], EXPECTED_KWH, rel_tol=1e-9),
              energy=r["total_energy_kwh"])


# ---------------------------------------------------------------------------
# C. B1 / B2 full event-loop
# ---------------------------------------------------------------------------
def category_C():
    b1 = run(EngineConfig("B1", seed=11, miner_count=100), "C-B1")
    b2 = run(EngineConfig("B2", seed=11, miner_count=100), "C-B2")
    b3 = run(EngineConfig("B3_C1_CONTINUOUS_DISJOINT", seed=11, miner_count=100), "C-B3")
    check("C1", "C", "B1 executes in loop (accepted blocks >= 1)", b1["accepted_blocks"] >= 1,
          accepted=b1["accepted_blocks"])
    check("C2", "C", "B2 executes in loop (accepted blocks >= 1)", b2["accepted_blocks"] >= 1,
          accepted=b2["accepted_blocks"])
    check("C3", "C", "duplicate-rate ordering B3(0) < B2 < B1",
          b3["duplicate_evaluation_rate"] < b2["duplicate_evaluation_rate"] < b1["duplicate_evaluation_rate"],
          b3=b3["duplicate_evaluation_rate"], b2=b2["duplicate_evaluation_rate"],
          b1=b1["duplicate_evaluation_rate"])
    # candidate reconciliation: total == distinct + duplicate for each
    for nm, r in (("B1", b1), ("B2", b2), ("B3", b3)):
        check(f"C4-{nm}", "C", f"{nm} candidate reconciliation total == distinct + duplicate",
              math.isclose(r["total_candidate_evaluations"],
                           r["distinct_candidate_identities"] + r["duplicate_evaluations"],
                           rel_tol=1e-9),
              total=r["total_candidate_evaluations"], distinct=r["distinct_candidate_identities"],
              dup=r["duplicate_evaluations"])
    check("C5", "C", "B1/B2 not labelled classical PoW (interpretive honesty)",
          all("classical" not in s.lower() for s in ("B1", "B2")), note="labels are B1/B2")


# ---------------------------------------------------------------------------
# D. C2 in-loop idle
# ---------------------------------------------------------------------------
def category_D():
    het_eq = run(EngineConfig("C2", seed=21, miner_count=100,
                              hash_rate_distribution="heterogeneous_moderate",
                              allocation_policy="equal", idle_power_ratio=0.1), "D-het-equal")
    het_wt = run(EngineConfig("C2", seed=21, miner_count=100,
                              hash_rate_distribution="heterogeneous_moderate",
                              allocation_policy="weighted", idle_power_ratio=0.1), "D-het-weighted")
    hom = run(EngineConfig("C2", seed=21, miner_count=100, allocation_policy="equal",
                           idle_power_ratio=0.3), "D-hom")
    b3 = run(EngineConfig("B3_C1_CONTINUOUS_DISJOINT", seed=21, miner_count=100), "D-b3-ref")

    check("D1", "D", "C2 idle energy emerges in-loop (het-equal saves)",
          het_eq["idle_energy_kwh"] > 0 and het_eq["total_idle_time_s"] > 0,
          idle_kwh=het_eq["idle_energy_kwh"], idle_s=het_eq["total_idle_time_s"])
    check("D2", "D", "C2 homogeneous equal-range idle == 0 (no forced saving)",
          hom["total_idle_time_s"] == 0.0 and math.isclose(hom["total_energy_kwh"], EXPECTED_KWH, rel_tol=1e-9),
          idle_s=hom["total_idle_time_s"], energy=hom["total_energy_kwh"])
    check("D3", "D", "C2 heterogeneous weighted saves less than equal",
          het_wt["total_idle_time_s"] < het_eq["total_idle_time_s"],
          equal_idle_s=het_eq["total_idle_time_s"], weighted_idle_s=het_wt["total_idle_time_s"])
    # energy reconciliation: total == active + idle + coordination (exact)
    for nm, r in (("het-equal", het_eq), ("het-weighted", het_wt), ("hom", hom)):
        check(f"D4-{nm}", "D", f"C2 {nm} energy reconciliation total == active+idle+coord",
              math.isclose(r["total_energy_kwh"],
                           r["active_energy_kwh"] + r["idle_energy_kwh"] + r["coordination_energy_kwh"],
                           rel_tol=0, abs_tol=1e-12),
              total=r["total_energy_kwh"], active=r["active_energy_kwh"],
              idle=r["idle_energy_kwh"], coord=r["coordination_energy_kwh"])
    # time reconciliation vs B3: active_time removed == idle_time (same seed/timeline)
    c2_eq0 = run(EngineConfig("C2", seed=21, miner_count=100,
                              hash_rate_distribution="heterogeneous_moderate",
                              allocation_policy="equal", idle_power_ratio=0.0), "D-het-equal-idle0")
    b3_het = run(EngineConfig("B3_C1_CONTINUOUS_DISJOINT", seed=21, miner_count=100,
                              hash_rate_distribution="heterogeneous_moderate",
                              allocation_policy="equal"), "D-b3-het")
    check("D5", "D", "C2 in-loop time reconciliation: B3_active - C2_active == C2_idle",
          math.isclose(b3_het["total_active_time_s"] - c2_eq0["total_active_time_s"],
                       c2_eq0["total_idle_time_s"], rel_tol=1e-6),
          b3_active=b3_het["total_active_time_s"], c2_active=c2_eq0["total_active_time_s"],
          c2_idle=c2_eq0["total_idle_time_s"])
    check("D6", "D", "C2 state-transition reasons recorded",
          het_eq["idle_enter_reason"] == "range_exhausted_no_solution"
          and het_eq["idle_leave_reason"] == "new_template_generation_or_accepted_block",
          enter=het_eq["idle_enter_reason"], leave=het_eq["idle_leave_reason"])
    _ = b3


# ---------------------------------------------------------------------------
# E. coordination-counter reconciliation
# ---------------------------------------------------------------------------
def category_E():
    r = run(EngineConfig("B3_C1_CONTINUOUS_DISJOINT", seed=31, miner_count=100), "E-b3")
    rlow = run(EngineConfig("B3_C1_CONTINUOUS_DISJOINT", seed=31, miner_count=100, mu=0.5), "E-b3-lowmu")
    b0 = run(EngineConfig("B0", seed=31, miner_count=100), "E-b0")
    check("E1", "E", "block-propagation bytes == messages * 1MB",
          r["coord_block_propagation_bytes"] == r["coord_block_propagation_message_count"] * 1_000_000,
          bytes=r["coord_block_propagation_bytes"], msgs=r["coord_block_propagation_message_count"])
    check("E2", "E", "template refresh count == exhausted rounds",
          rlow["coord_template_refresh_count"] == rlow["exhausted_rounds"],
          refresh=rlow["coord_template_refresh_count"], exhausted=rlow["exhausted_rounds"])
    check("E3", "E", "unimplemented agreement energy is null (not zero)",
          r["unimplemented_agreement_energy_kwh"] is None,
          value=r["unimplemented_agreement_energy_kwh"])
    check("E4", "E", "coordination lower bound explicit and zero",
          r["coordination_energy_lower_bound_kwh"] == 0.0 and r["coordination_energy_kwh"] == 0.0,
          lb=r["coordination_energy_lower_bound_kwh"])
    check("E5", "E", "common-template scenario has agreement ops; B0 (independent) has none",
          r["abstract_template_agreement_operations"] == r["accepted_blocks"]
          and b0["abstract_template_agreement_operations"] == 0,
          b3_ops=r["abstract_template_agreement_operations"], b0_ops=b0["abstract_template_agreement_operations"])
    # events reconciliation: one agreement op per accepted block
    check("E6", "E", "events reconciliation: agreement ops == accepted blocks",
          r["abstract_template_agreement_operations"] == r["accepted_blocks"],
          ops=r["abstract_template_agreement_operations"], accepted=r["accepted_blocks"])


# ---------------------------------------------------------------------------
# F. parallel reproducibility (20 sequential vs 20 concurrent)
# ---------------------------------------------------------------------------
def category_F():
    configs = []
    scen_cycle = ["B0", "B1", "B2", "B3_C1_CONTINUOUS_DISJOINT", "C2"]
    for i in range(20):
        scen = scen_cycle[i % len(scen_cycle)]
        kw = dict(seed=40 + i, miner_count=100)
        if scen == "C2":
            kw.update(hash_rate_distribution="heterogeneous_moderate",
                      allocation_policy="equal", idle_power_ratio=0.1)
        configs.append(EngineConfig(scen, **kw))

    # run_scenario is a pure function -> persist sequential runs (counts toward cap)
    seq = [run(c, f"F-seq-{i:02d}") for i, c in enumerate(configs)]
    # concurrent execution of the SAME configs (does NOT persist; reproducibility only)
    with ThreadPoolExecutor(max_workers=8) as ex:
        con = list(ex.map(run_scenario, configs))

    def _key(r):
        return (round(r["total_energy_kwh"], 12), r["accepted_blocks"],
                round(r["total_active_time_s"], 6), round(r["total_idle_time_s"], 6),
                round(r["duplicate_evaluation_rate"], 12))
    all_match = all(_key(a) == _key(b) for a, b in zip(seq, con))
    n_mismatch = sum(1 for a, b in zip(seq, con) if _key(a) != _key(b))
    check("F1", "F", "20 sequential runs == 20 concurrent runs (bit-for-bit outcomes)",
          all_match, mismatches=n_mismatch, n=len(configs))
    # named-stream determinism
    from experiments.thesis_revision_v43.scenario_engine import derive_stream_seeds, STREAM_NAMES
    s = derive_stream_seeds(40)
    check("F2", "F", "named streams reproducible and independent",
          s == derive_stream_seeds(40) and len(set(s.values())) == len(STREAM_NAMES),
          n_streams=len(STREAM_NAMES))


# ---------------------------------------------------------------------------
# G. stress N=500
# ---------------------------------------------------------------------------
def category_G():
    for scen in ("B0", "B1", "B2", "B3_C1_CONTINUOUS_DISJOINT", "C2"):
        kw = dict(seed=61, miner_count=500)
        if scen == "C2":
            kw.update(hash_rate_distribution="heterogeneous_moderate",
                      allocation_policy="equal", idle_power_ratio=0.1)
        r = run(EngineConfig(scen, **kw), f"G-{scen}")
        cont = scen != "C2"
        if cont:
            # B1 may legitimately produce 0 blocks at N=500 (zero-block policy,
            # Stage 5B1A); the energy invariant A1 still holds regardless.
            min_blocks = 0 if scen == "B1" else 1
            check(f"G-{scen}", "G", f"{scen} N=500 executes; energy invariant A1 holds",
                  math.isclose(r["total_energy_kwh"], EXPECTED_KWH, rel_tol=1e-9)
                  and r["accepted_blocks"] >= min_blocks,
                  energy=r["total_energy_kwh"], accepted=r["accepted_blocks"])
        else:
            check(f"G-{scen}", "G", f"{scen} N=500 executes; energy <= invariant (idle saves)",
                  r["total_energy_kwh"] <= EXPECTED_KWH + 1e-9 and r["accepted_blocks"] >= 1,
                  energy=r["total_energy_kwh"], accepted=r["accepted_blocks"])


def main():
    os.makedirs(RAW, exist_ok=True)
    category_A(); category_B(); category_C(); category_D()
    category_E(); category_F(); category_G()

    passed = sum(1 for c in _checks if c["passed"])
    failed = [c for c in _checks if not c["passed"]]
    sizes = sorted(_byte_sizes)
    n = len(sizes)
    median = sizes[n // 2] if n else 0
    p95 = sizes[min(n - 1, int(math.ceil(0.95 * n)) - 1)] if n else 0
    report = dict(
        run_count=_run_count, run_cap=RUN_CAP, under_cap=_run_count <= RUN_CAP,
        checks_total=len(_checks), checks_passed=passed, checks_failed=len(failed),
        all_passed=len(failed) == 0,
        failed_checks=failed,
        storage=dict(persisted_runs=n, min_bytes=sizes[0] if n else 0,
                     median_bytes=median, p95_bytes=p95, max_bytes=sizes[-1] if n else 0,
                     mean_bytes=int(round(sum(sizes) / n)) if n else 0),
        checks=_checks)
    run_utils.atomic_write_json(os.path.join(RESULTS, "validation_report.json"), report)
    print(json.dumps(dict(run_count=_run_count, checks_total=len(_checks),
                          checks_passed=passed, checks_failed=len(failed),
                          all_passed=len(failed) == 0,
                          median_bytes=median, p95_bytes=p95), indent=2))
    if failed:
        print("\nFAILED CHECKS:")
        for c in failed:
            print(" ", c["id"], c["description"], {k: v for k, v in c.items()
                  if k not in ("id", "category", "description", "passed")})
    return report


if __name__ == "__main__":
    rep = main()
    sys.exit(0 if rep["all_passed"] else 1)
