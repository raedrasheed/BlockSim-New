#!/usr/bin/env python3
"""Stage 6 — preregistration validator.

Every check below is a FAILING gate: it either passes or it names exactly what is wrong.
The GitHub Actions workflow runs this script, and so does the Stage-6 test suite.

    python experiments/thesis_revision_v45/stage_06/validate_preregistration.py

Checks
  1  reference configuration matches the ACCEPTED frozen baseline exactly
  2  A1 reproduces 8.420833333 kWh to within 1e-9 kWh
  3  seed registry regenerates byte-identically
  4  confirmatory / exploratory matrices and frozen configs regenerate byte-identically
  5  pilot and confirmatory seed classes are disjoint
  6  every scenario id is unique, and <= 24 confirmatory rows
  7  every paired condition matches its control on every frozen nuisance variable
  8  every confirmatory config carries the single fixed difficulty (C06 declared exception)
  9  no confirmatory RUN OUTPUT exists anywhere under the Stage-6 tree
 10  every declared outcome resolves to a real ACCEPTED adapter field or a declared derivation
 11  the preregistration manifest covers every deliverable
 12  the pilot used pilot seeds only, and never a confirmatory seed
 13  the D04 / D04C fault schedule is frozen, arm-identical, seed-independent and outcome-blind
 14  every Tier-2 scenario is accounted for: 3 completed, 1 right-censored, 0 failed
 15  the Stage-7 resource preflight gate exists, is unfilled, and blocks confirmatory execution
"""
from __future__ import annotations

import hashlib
import inspect
import json
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
for p in (str(REPO_ROOT), str(HERE)):
    if p not in sys.path:
        sys.path.insert(0, p)

import scenarios as S                                              # noqa: E402
import generate_seed_registry as GSR                               # noqa: E402
import generate_confirmatory_matrix as GCM                         # noqa: E402

DOCS = REPO_ROOT / "docs" / "thesis_revision_v45" / "stage_06"
CONF = HERE / "confirmatory"
PILOT = HERE / "pilot"

#: Outcome names that are DERIVED rather than read straight from ``results_schema``.  Each maps
#: to the accepted fields it is computed from, so no name is ever invented.
DERIVED_OUTCOMES = {
    "total_energy_kwh": ("energy_kwh",),
    "accepted_blocks": ("rounds_accepted",),
    "accepted_blocks_per_horizon": ("rounds_accepted",),
    "zero_block_indicator": ("rounds_accepted",),
    "zero_block_rate": ("rounds_accepted",),
    "relative_energy_reduction_percent": ("energy_kwh", "continuous_all_active_control_kwh"),
    "round_duration": (),                       # run_ctx.round_terminal_times
    "median_round_duration": (),                # run_ctx.round_terminal_times
    "post_round_evaluation_record_count": ("post_round_evaluation_count",),
    "post_round_evaluation_nonce_count": (),    # Stage-5D audit over the evaluation ledger
    "evaluation_missing_terminal_time_count": (),
    "nonterminal_activation_request_count": (), # run_ctx.activation_requests
    "maximum_energy_identity_residual_j": (),   # MinerRecord.duration x per_miner_power
    "maximum_residency_partition_residual_s": (),
    "maximum_hash_rate_deficit_when_floor_disabled": ("maximum_hash_rate_deficit",),
    "NONE": (), "NONE_EXPLORATORY": (),
}

#: Nuisance variables a paired treatment must match its control on.
PAIRED_MATCH_FIELDS = ("num_miners", "horizon_T", "nonce_domain_size", "difficulty",
                       "batch_size", "base_hash_rate", "P_hash", "P_offline")

FAILURES = []
NOTES = []


def check(ok: bool, label: str, detail: str = "") -> None:
    if ok:
        print(f"  PASS  {label}")
    else:
        print(f"  FAIL  {label}: {detail}")
        FAILURES.append(f"{label}: {detail}")


def regen_ok(script: str) -> tuple:
    r = subprocess.run([sys.executable, str(HERE / script), "--check"],
                       capture_output=True, text=True)
    return r.returncode == 0, (r.stdout + r.stderr).strip().splitlines()[:3]


def accepted_schema_keys() -> set:
    """The real ``results_schema`` key set, obtained by EXECUTING the accepted adapter."""
    from Models.PoCol.stage2.config import Stage2Config
    from Models.PoCol.stage2.simulator import run_simulation
    from Models.PoCol.stage2.adapter import results_schema
    cfg = Stage2Config(num_miners=4, horizon_T=12.0, nonce_domain_size=80, batch_size=10)
    return set(results_schema(run_simulation(cfg, run_id="validate"), cfg))


def main() -> int:
    print("Stage-6 preregistration validation")
    print("=" * 74)

    # ---- 1 / 2 reference configuration and A1 -----------------------------------
    print("\n[1,2] reference configuration and the A1 accounting invariant")
    try:
        S.assert_reference_matches_baseline()
        check(True, "reference configuration matches the frozen baseline")
        check(True, f"A1 reproduces {S.A1_REFERENCE_KWH} kWh within {S.A1_TOLERANCE_KWH} kWh")
    except SystemExit as exc:
        check(False, "reference configuration / A1", str(exc))

    # ---- 3 / 4 byte-reproducible generation -------------------------------------
    print("\n[3,4] deterministic regeneration")
    ok, out = regen_ok("generate_seed_registry.py")
    check(ok, "seed registry regenerates byte-identically", " | ".join(out))
    ok, out = regen_ok("generate_confirmatory_matrix.py")
    check(ok, "matrices and frozen configs regenerate byte-identically", " | ".join(out))

    # ---- 5 seed disjointness ----------------------------------------------------
    print("\n[5] seed-class disjointness")
    rows = GSR.build_rows()
    pilot = {r["master_seed_decimal"] for r in rows if r["seed_class"] == "PILOT"}
    conf = {r["master_seed_decimal"] for r in rows if r["seed_class"] == "CONFIRMATORY"}
    ana = {r["master_seed_decimal"] for r in rows if r["seed_class"] == "ANALYSIS"}
    check(len(pilot) == 8, "8 pilot seeds", str(len(pilot)))
    check(len(conf) == 30, "30 confirmatory seeds", str(len(conf)))
    check(len(ana) == 1, "1 analysis seed", str(len(ana)))
    check(not (pilot & conf), "pilot and confirmatory seeds are disjoint", str(pilot & conf))
    check(not (pilot & ana) and not (conf & ana), "analysis seed is disjoint from both", "")

    # ---- 6 scenario identity ----------------------------------------------------
    print("\n[6] scenario identity and matrix size")
    crows = S.confirmatory_rows()
    erows = S.exploratory_rows()
    ids = [r["scenario_id"] for r in crows] + [r["scenario_id"] for r in erows]
    check(len(ids) == len(set(ids)), "every scenario id is unique",
          str([i for i in ids if ids.count(i) > 1]))
    check(len(crows) <= 24, f"confirmatory rows <= 24 (have {len(crows)})", str(len(crows)))
    check(all(r["confirmatory_or_exploratory"] == "CONFIRMATORY" for r in crows),
          "every confirmatory row is labelled CONFIRMATORY")
    check(all(r["confirmatory_or_exploratory"] == "EXPLORATORY" for r in erows),
          "every exploratory row is labelled EXPLORATORY")
    blocks = {r["block_id"] for r in crows}
    check(blocks == {"A", "B", "C", "D"}, "blocks are exactly A, B, C, D", str(sorted(blocks)))

    # ---- 7 paired-condition matching --------------------------------------------
    print("\n[7] paired conditions match on every frozen nuisance variable")
    by_id = {r["scenario_id"]: r for r in crows}
    cfgs = {sid: S.build_config(r, 0, S.TIER2) for sid, r in by_id.items()}
    bad = []
    for sid, row in by_id.items():
        ctrl = row["paired_control_id"]
        if ctrl in ("SELF", "NONE"):
            continue
        if ctrl not in cfgs:
            bad.append(f"{sid}: control {ctrl} not in the matrix")
            continue
        a, b = cfgs[sid], cfgs[ctrl]
        for f in PAIRED_MATCH_FIELDS:
            if getattr(a, f) != getattr(b, f):
                bad.append(f"{sid} vs {ctrl}: {f} {getattr(a, f)!r} != {getattr(b, f)!r}")
    check(not bad, "every paired treatment matches its control", "; ".join(bad))

    # both arms of a pair must receive the SAME template and adversarial child seed
    seed0 = sorted(conf)[0]
    same = all(S.build_config(by_id[s], seed0, S.TIER2).template_seed
               == S.build_config(by_id[c], seed0, S.TIER2).template_seed
               for s, c in ((r["scenario_id"], r["paired_control_id"]) for r in crows)
               if c not in ("SELF", "NONE"))
    check(same, "both arms of every pair share the same template seed under one master seed")

    # ---- 8 fixed difficulty ------------------------------------------------------
    print("\n[8] fixed confirmatory difficulty")
    off = [sid for sid, c in cfgs.items()
           if c.difficulty != S.CONFIRMATORY_DIFFICULTY and sid != "C06"]
    check(not off, "every confirmatory config uses the single fixed difficulty "
                   f"{S.CONFIRMATORY_DIFFICULTY}", str(off))
    check(cfgs["C06"].difficulty == S.UNREACHABLE_DIFFICULTY,
          "C06 carries the DECLARED unreachable-target integrity difficulty")
    check(by_id["C06"]["paired_control_id"] == "NONE",
          "C06 is excluded from every paired contrast")

    # ---- 9 no confirmatory outputs ----------------------------------------------
    print("\n[9] Stage 6 contains no confirmatory run output")
    allowed = {"README_DO_NOT_RUN_IN_STAGE6.md", "confirmatory_run_registry.csv"}
    stray = [str(p.relative_to(REPO_ROOT)) for p in CONF.rglob("*")
             if p.is_file() and p.name not in allowed and p.parent.name != "frozen_configs"]
    check(not stray, "confirmatory/ holds configurations and registries only", str(stray))
    non_json = [str(p.relative_to(REPO_ROOT)) for p in (CONF / "frozen_configs").glob("*")
                if p.is_file() and p.suffix != ".json"]
    check(not non_json, "frozen_configs/ holds only .json configurations", str(non_json))

    # ---- 10 outcome fields resolve against the ACCEPTED adapter schema ----------
    print("\n[10] every declared outcome resolves against the accepted adapter schema")
    keys = accepted_schema_keys()
    declared = set()
    for m in (GCM.PRIMARY_OUTCOMES, GCM.SECONDARY_OUTCOMES):
        for v in m.values():
            declared |= {x for x in v.split(";") if x}
    for r in crows:
        declared |= {x for x in GCM.expected_na(r).split(";") if x and x != "NONE"}
    unresolved = sorted(f for f in declared if f not in keys and f not in DERIVED_OUTCOMES)
    check(not unresolved, "no declared outcome is an invented alias", str(unresolved))
    broken = sorted(f for f, src in DERIVED_OUTCOMES.items()
                    if f in declared for s in src if s not in keys)
    check(not broken, "every derivation source exists in the accepted schema", str(broken))
    NOTES.append(f"accepted results_schema exposes {len(keys)} keys; "
                 f"{len(declared)} outcome names declared")

    # ---- 11 manifest coverage ----------------------------------------------------
    print("\n[11] preregistration manifest coverage")
    manifest = DOCS / "STAGE_06_FREEZE_CANDIDATE_MANIFEST.sha256"
    required = [
        "STAGE_06_PREREGISTRATION.md", "STAGE_06_IP_HYPOTHESES.md",
        "STAGE_06_CONFIRMATORY_MATRIX.csv", "STAGE_06_EXPLORATORY_MATRIX.csv",
        "STAGE_06_SEED_REGISTRY.csv", "STAGE_06_ANALYSIS_PLAN.md",
        "STAGE_06_OUTCOME_DICTIONARY.csv", "STAGE_06_EXCLUSION_RETENTION_POLICY.md",
        "STAGE_06_PILOT_PLAN.md", "STAGE_06_PILOT_REPORT.md",
        "STAGE_06_RUNTIME_AND_ARCHIVE_PLAN.md", "STAGE_06_STAGE7_EXECUTION_PLAN.md",
        "STAGE_06_DECISION_LOG.md", "STAGE_06_ENVIRONMENT_LOCK.json",
        "STAGE_06_COMPLETION_REPORT.md", "STAGE_06_D04_FAULT_SCHEDULE_FREEZE.md",
        "STAGE_07_RESOURCE_PREFLIGHT_GATE.md",
    ]
    missing = [f for f in required if not (DOCS / f).exists()]
    check(not missing, "every required deliverable exists", str(missing))
    if manifest.exists():
        listed, mismatched = set(), []
        for line in manifest.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            digest, _, rel = line.partition("  ")
            listed.add(rel)
            p = REPO_ROOT / rel
            if not p.exists():
                mismatched.append(f"{rel}: missing")
            elif hashlib.sha256(p.read_bytes()).hexdigest() != digest:
                mismatched.append(f"{rel}: digest mismatch")
        check(not mismatched, "every manifest entry verifies", str(mismatched[:5]))
        uncovered = [f for f in required
                     if f"docs/thesis_revision_v45/stage_06/{f}" not in listed]
        check(not uncovered, "the manifest covers every deliverable", str(uncovered))
        conf_data = [rel for rel in listed
                     if "/confirmatory/" in rel and "frozen_configs" not in rel
                     and not rel.endswith(("README_DO_NOT_RUN_IN_STAGE6.md",
                                           "confirmatory_run_registry.csv"))]
        check(not conf_data, "the manifest contains no confirmatory data", str(conf_data))
    else:
        check(False, "freeze-candidate manifest exists", str(manifest))

    # ---- 12 the pilot used pilot seeds only --------------------------------------
    print("\n[12] the pilot executed pilot seeds only")
    pr = PILOT / "pilot_results.json"
    if pr.exists():
        data = json.loads(pr.read_text())
        used = {r["master_seed"] for r in data["results"]}
        check(used <= pilot, "every executed pilot seed is a PILOT seed",
              str(sorted(used - pilot)))
        check(not (used & conf), "no confirmatory seed was executed", str(sorted(used & conf)))
        NOTES.append(f"pilot executed {len(data['results'])} runs over {len(used)} pilot seeds")
    else:
        check(False, "pilot results exist", str(pr))

    # ---- 13 the D04 fault schedule is frozen and seed-independent -----------------
    print("\n[13] the D04 / D04C fault schedule is frozen")
    rows_by_id = {r["scenario_id"]: r for r in S.confirmatory_rows()}
    pilot_list = sorted(pilot)
    identical, digests = True, {}
    for tier_key, tier in (("TIER1", S.TIER1), ("TIER2", S.TIER2)):
        for sid in ("D04C", "D04"):
            for seed in pilot_list:
                cfg = S.build_config(rows_by_id[sid], seed, tier)
                digests.setdefault((tier_key, sid), set()).add(
                    hashlib.sha256(repr(cfg.injected_lease_faults).encode()).hexdigest())
        for seed in pilot_list:
            a = S.build_config(rows_by_id["D04C"], seed, tier)
            b = S.build_config(rows_by_id["D04"], seed, tier)
            identical &= (a.injected_lease_faults == b.injected_lease_faults)
    check(identical, "D04C and D04 use byte-identical fault schedules on every pilot seed")
    varying = sorted(k for k, v in digests.items() if len(v) != 1)
    check(not varying, "the fault schedule does not vary by master seed", str(varying))
    sig = inspect.signature(S._fault_schedule)
    check(list(sig.parameters) == ["name", "num_miners", "reserve_fraction",
                                   "horizon_T", "period"],
          "the schedule generator takes no seed and no result argument", str(sig))
    src = inspect.getsource(S._fault_schedule).lower()
    leaks = [w for w in ("reevaluation", "duplicate_work", "accepted_below", "kwh",
                         "reward", "results_schema", "run_simulation", "json", "open(")
             if w in src]
    check(not leaks, "the schedule reads no outcome quantity", str(leaks))
    for tier_key, tier, want in (("TIER1", S.TIER1, 1560), ("TIER2", S.TIER2, 15000)):
        got = len(S._fault_schedule("FAULT_SET_PROGRESS", tier["num_miners"], 0.20,
                                    tier["horizon_T"],
                                    float(tier["nominal_round_period"])))
        check(got == want, f"{tier_key} fault count is the frozen {want}", f"got {got}")
    sweep = PILOT / "d04_all_seeds.json"
    if sweep.exists():
        srows = json.loads(sweep.read_text())["results"]
        used = {r["master_seed"] for r in srows}
        check(used == pilot, "the pair ran on all eight pilot seeds",
              f"{len(used)} of {len(pilot)}")
        check(all(r["run_status"] == "COMPLETED" for r in srows),
              "every D04-pair sweep run completed")
        check(all(r["physical_frontier_rewind_count"] == 0 for r in srows),
              "the physical frontier never rewinds in either arm")
        zero = [r for r in srows if r["scenario_id"] == "D04"
                and not r["progress_withholding_count"]]
        NOTES.append(f"D04 pair swept {len(srows)} runs over {len(used)} pilot seeds; "
                     f"{len(zero)} zero-action seed(s) retained")
    else:
        check(False, "the eight-seed D04 sweep exists", str(sweep))

    # ---- 14 the four required Tier-2 runs are recorded ----------------------------
    print("\n[14] the four required Tier-2 full-scale runs")
    t2dir = PILOT / "tier2"
    found = {}
    if t2dir.is_dir():
        for f in sorted(t2dir.glob("*.json")):
            if f.name.endswith((".resources.json", ".censored.json")):
                continue      # sampler sidecar / censored record, NOT a run checkpoint:
                              # counting either would let 3 completed runs falsely
                              # satisfy "all four"
            rec = json.loads(f.read_text())
            if "master_seed" not in rec or "run_status" not in rec:
                check(False, f"{f.name} is not a valid Tier-2 run checkpoint")
                continue
            found[rec["scenario_id"]] = (rec, f)
    cens = {}
    for f in sorted(t2dir.glob("*.censored.json")) if t2dir.is_dir() else []:
        rec = json.loads(f.read_text())
        cens[rec["scenario_id"]] = (rec, f)
    # AMENDED RULE: Stage 6 was closed under an authorised time constraint with one run
    # right-censored.  Every Tier-2 scenario must be ACCOUNTED FOR — completed or censored —
    # and none may be silently missing or silently counted as completed.
    accounted = set(found) | set(cens)
    check(accounted == set(S.TIER2_SCENARIOS),
          f"all {len(S.TIER2_SCENARIOS)} Tier-2 scenarios are accounted for "
          f"(completed or right-censored)",
          f"unaccounted {sorted(set(S.TIER2_SCENARIOS) - accounted)}")
    check(not (set(found) & set(cens)),
          "no scenario is both completed and censored", str(sorted(set(found) & set(cens))))
    check(len(found) == 3, "exactly 3 Tier-2 runs completed", str(sorted(found)))
    check(len(cens) == 1, "exactly 1 Tier-2 run is right-censored", str(sorted(cens)))
    failed = [s for s, (r, _f) in found.items() if r["run_status"] != "COMPLETED"]
    check(not failed, "zero Tier-2 runs failed", str(failed))
    for sid, (rec, f) in sorted(cens.items()):
        check(rec["run_status"].startswith("RIGHT_CENSORED"),
              f"{sid} carries a RIGHT_CENSORED status", rec["run_status"])
        check(rec["master_seed"] in pilot, f"{sid} censored record keeps its PILOT seed")
        check(rec.get("checkpoint_exists") is False,
              f"{sid} is not claimed to have written a checkpoint")
        for k in ("elapsed_wall_seconds_LOWER_BOUND", "cpu_seconds_LOWER_BOUND",
                  "vm_hwm_mb_LOWER_BOUND", "simulated_time_seconds_LOWER_BOUND"):
            check(k in rec, f"{sid} records {k}")
        check(rec["censoring"]["scientific_use"].startswith("NONE"),
              f"{sid} infers no scientific quantity from the partial run")
        NOTES.append(f"TIER2 {sid}: {rec['run_status']} "
                     f"wall>={rec['elapsed_wall_seconds_LOWER_BOUND']:.0f}s "
                     f"cpu>={rec['cpu_seconds_LOWER_BOUND']:.0f}s "
                     f"hwm>={rec['vm_hwm_mb_LOWER_BOUND']:.0f}MB "
                     f"sim>={rec['simulated_time_seconds_LOWER_BOUND']:.0f}s")
    for sid, (rec, f) in sorted(found.items()):
        check(rec["master_seed"] in pilot, f"{sid} ran on a PILOT seed",
              str(rec["master_seed"]))
        check((t2dir / f"{sid}.log").exists(), f"{sid} log is preserved",
              str(t2dir / f"{sid}.log"))
        NOTES.append(f"TIER2 {sid}: {rec['run_status']} "
                     f"{rec.get('wall_clock_seconds', 0):.0f}s "
                     f"rss={rec.get('peak_rss_mb', 0):.0f}MB "
                     f"rounds={rec.get('rounds_executed', '-')} "
                     f"checkpoint={f.relative_to(REPO_ROOT)}")

    # ---- 15 the Stage-7 resource preflight gate -----------------------------------
    print("\n[15] Stage-7 resource preflight gate")
    gate = DOCS / "STAGE_07_RESOURCE_PREFLIGHT_GATE.md"
    if gate.exists():
        g = gate.read_text()
        check("STAGE_7_RESOURCE_PREFLIGHT_NOT_YET_PASSED" in g,
              "the gate records the preflight as NOT YET PASSED")
        check("NOT APPROVED FOR STAGE-7 FROZEN EXECUTION" in g,
              "the current ephemeral environment is recorded as NOT APPROVED")
        check("STAGE_7_RESOURCE_PREFLIGHT_PASSED" not in g.split("## 5.")[0],
              "no premature PASSED state is recorded")
        for field in ("host identifier", "availability / lifetime guarantee", "CPU cores",
                      "usable RAM", "free disk", "archive destination",
                      "network / durable-storage path", "per-class worker limits",
                      "streaming-compression command",
                      "compression runtime / memory benchmark", "heartbeat command",
                      "checkpoint policy", "per-run timeout",
                      "same-seed infrastructure-rerun policy"):
            if field not in g:
                check(False, f"the preflight record declares the field {field!r}")
        check(all(f in g for f in ("host identifier", "checkpoint policy", "per-run timeout")),
              "the preflight record declares all fourteen required fields")
        check("1.25" in g, "the gate declares the 1.25x memory and lifetime margins")
        # the gate must be UNFILLED: fabricating a host is the failure mode it guards against
        check(g.count("*(unfilled)*") >= 14,
              "every preflight field is unfilled — no host is fabricated",
              f"{g.count('*(unfilled)*')} unfilled markers")
        NOTES.append("Stage-7 resource preflight gate present and unfilled; execution blocked")
    else:
        check(False, "the Stage-7 resource preflight gate exists", str(gate))

    print("\n" + "=" * 74)
    for n in NOTES:
        print(f"  note: {n}")
    if FAILURES:
        print(f"\nVALIDATION FAILED — {len(FAILURES)} check(s):")
        for f in FAILURES:
            print(f"  - {f}")
        return 1
    print("\nAll preregistration validation checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
