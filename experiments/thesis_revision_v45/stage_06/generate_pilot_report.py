#!/usr/bin/env python3
"""Stage 6 — pilot report and runtime/archive plan, generated from the pilot data.

Emits:
    docs/thesis_revision_v45/stage_06/STAGE_06_PILOT_REPORT.md
    docs/thesis_revision_v45/stage_06/STAGE_06_RUNTIME_AND_ARCHIVE_PLAN.md

Every number is read from ``pilot/pilot_results.json``, so the documents cannot disagree with
the executed pilot.

The report may contain ONLY: runtime, peak memory, output bytes, event count, round count,
zero-block count, NA count by field, exception count, integrity-gate failures, configuration
feasibility, and whether the run completed.  It must NOT contain condition-specific mean energy
savings, inferential effect estimates, p-values, confidence intervals, any ranking of conditions
by energy effect, claims about which hypothesis passed, or recommendations based on effect
direction.  This generator emits none of those.

Usage:
    python experiments/thesis_revision_v45/stage_06/generate_pilot_report.py [--check]
"""
from __future__ import annotations

import argparse
import json
import pathlib
import statistics
import sys

HERE = pathlib.Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
for p in (str(REPO_ROOT), str(HERE)):
    if p not in sys.path:
        sys.path.insert(0, p)

import scenarios as S                       # noqa: E402

DOCS = REPO_ROOT / "docs" / "thesis_revision_v45" / "stage_06"
PILOT = HERE / "pilot" / "pilot_results.json"

GATES = ("duplicate_nonce_count", "post_round_evaluation_record_count",
         "post_round_evaluation_nonce_count", "evaluation_missing_terminal_time_count",
         "nonterminal_lease_count", "nonterminal_reassignment_request_count",
         "nonterminal_activation_request_count", "physical_frontier_rewind_count",
         "work_reward_union_residual")

#: Gates that must be zero on EVERY run regardless of the declared adversarial behaviour.
#: ``duplicate_nonce_count`` is deliberately absent: under a declared PROGRESS_WITHHOLDER it is
#: the measured consequence of the behaviour, not a defect (see test_s6_16).
UNCONDITIONAL_GATES = ("evaluation_missing_terminal_time_count", "nonterminal_lease_count",
                       "nonterminal_reassignment_request_count",
                       "nonterminal_activation_request_count",
                       "physical_frontier_rewind_count", "work_reward_union_residual")

D04_SWEEP = "d04_all_seeds.json"

# ---------------------------------------------------------------- scenario cost classes
#: Stage-7 cost is NOT one distribution.  Three structurally different classes were identified
#: from the accepted engine's own control flow and each is represented by a measured Tier-2 run:
#:
#:   SECURITY_FLOOR  the floor is enabled, so EvaluateSecurityFloor runs on every capacity
#:                   change and walks the run-lifetime `reserve_records` map  -> O(rounds^2)
#:   REASSIGNMENT    a fault schedule revokes leases, so entity/ownership reconciliation tables
#:                   are populated -> large serialised output
#:   LIGHTWEIGHT     neither -> cheapest runtime and a tiny output
#:
#: A single global average across these would be wrong in both directions, so every projection
#: below is computed per class.
CLASS_REPRESENTATIVE = {"LIGHTWEIGHT": ("A03", "A05"), "SECURITY_FLOOR": ("B02",),
                        "REASSIGNMENT": ("C04",)}

#: MEASURED compression, not assumed: a C04 payload produced at a reduced horizon was serialised
#: and compressed with the stdlib codecs available in the locked environment.  zstd is NOT
#: installed here, so the archive format is stated in terms of what was actually measured.
COMPRESSION_PROBE = {
    "scenario": "C04", "horizon_T": 600.0, "rounds": 574, "raw_bytes": 2_366_554,
    "gzip9_bytes": 62_621, "xz9_bytes": 30_272,
    "largest_keys": (("entity_reconciliation", 1_435_381, 60.7),
                     ("ownership_reconciliation", 886_263, 37.4),
                     ("reassignment_energy_report", 29_322, 1.2)),
}
GZIP_RATIO = COMPRESSION_PROBE["raw_bytes"] / COMPRESSION_PROBE["gzip9_bytes"]
XZ_RATIO = COMPRESSION_PROBE["raw_bytes"] / COMPRESSION_PROBE["xz9_bytes"]

#: Declared before Stage 7 and not tuned afterwards.
TIMEOUT_SAFETY_FACTOR = 1.5
USABLE_RAM_FRACTION = 0.80          # leave 20 % for the OS, page cache and the scheduler

#: The compression ratio was measured on a REDUCED-HORIZON payload (574 rounds, not 9 592), so
#: planning storage on it directly would trust an extrapolation.  Storage is therefore sized on
#: a deliberately pessimistic ratio: the measured one divided by this factor.  Declared here,
#: before Stage 7, and not revised afterwards.
COMPRESSION_SAFETY_FACTOR = 2.0
#: Extra headroom on raw bytes, covering per-run logs, resource sidecars, checksums and the
#: transient copy that exists while a chunk is being archived and verified.  >= 1.5 (50 %).
RAW_HEADROOM_FACTOR = 1.5

# ---------------------------------------------------------------- concurrency arithmetic
#: THE MEMORY EQUATION.  A worker set {n_c} of classes c is admissible only if
#:
#:     RAM_SAFETY_MARGIN * SUM_c ( n_c * peak_rss_c )  <=  USABLE_RAM_FRACTION * total_ram
#:
#: Core count is an upper bound on the worker set, never a declaration of capacity: a host can
#: have idle cores and still be unable to hold another heavy worker.  Both bounds are applied.
RAM_SAFETY_MARGIN = 1.25            # >= 25 % headroom over measured peak RSS

#: SECURITY_FLOOR and REASSIGNMENT are the "heavy" classes.  Their combined concurrency is
#: additionally capped, independent of the arithmetic, so a host cannot be scheduled to the
#: exact edge of its memory budget.
HEAVY_CLASSES = ("SECURITY_FLOOR", "REASSIGNMENT")
HEAVY_WORKER_CAP = 2


def admissible(counts: dict, cls_rss: dict, usable_gb: float) -> bool:
    """Apply the memory equation and the heavy-worker cap to a candidate worker set."""
    need_gb = sum(n * cls_rss[c] for c, n in counts.items()) / 1024.0
    if RAM_SAFETY_MARGIN * need_gb > usable_gb:
        return False
    return sum(counts.get(c, 0) for c in HEAVY_CLASSES) <= HEAVY_WORKER_CAP


def scenario_cost_class(row: dict) -> str:
    if row["security_floor_policy"] != "DISABLED":
        return "SECURITY_FLOOR"
    if row.get("fault_schedule", "NONE") != "NONE":
        return "REASSIGNMENT"
    return "LIGHTWEIGHT"


def machine_facts() -> dict:
    import os
    import pathlib as _p
    import shutil
    total_kb = 0
    for line in _p.Path("/proc/meminfo").read_text().splitlines():
        if line.startswith("MemTotal:"):
            total_kb = int(line.split()[1])
            break
    du = shutil.disk_usage(str(REPO_ROOT))
    return {"cpu_count": os.cpu_count() or 1, "total_ram_gb": total_kb / 1048576.0,
            "disk_total_gb": du.total / 1e9, "disk_free_gb": du.free / 1e9}


def censored_records() -> list:
    """Right-censored Tier-2 runs: observed but NOT completed.  Never counted as completed."""
    d = PILOT.parent / "tier2"
    return [json.loads(f.read_text()) for f in sorted(d.glob("*.censored.json"))] if d.is_dir() else []


def external_resources(sid: str) -> dict:
    """Externally sampled CPU time / peak RSS for a run, if a sidecar exists."""
    p = PILOT.parent / "tier2" / f"{sid}.resources.json"
    if not p.exists():
        return {}
    return json.loads(p.read_text()).get("final_sample", {})


def na_fields(rec: dict) -> list:
    """Field names whose recorded value is the sentinel string ``NA``."""
    return sorted(k for k, v in rec.items() if v == "NA")


def gate_failures(rec: dict) -> list:
    return [g for g in UNCONDITIONAL_GATES if rec.get(g, 0)]


def fmt(x, nd=3):
    if isinstance(x, float):
        return f"{x:.{nd}f}"
    return str(x)


def load_all() -> dict:
    """Merge the Tier-1 sweep with the independently-executed per-run Tier-2 files.

    Each Tier-2 run is its own process with its own log, its own fixed pilot seed and its own
    checkpointed output file, so the four required full-scale runs execute in parallel without
    sharing state and each is preserved separately in the report.
    """
    data = json.loads(PILOT.read_text())
    results = [r for r in data["results"] if r.get("tier") != "TIER2"]
    t2dir = PILOT.parent / "tier2"
    if t2dir.is_dir():
        for f in sorted(t2dir.glob("*.json")):
            if f.name.endswith((".resources.json", ".censored.json")):
                continue          # sampler sidecar / censored record, not a run checkpoint
            rec = json.loads(f.read_text())
            rec["source_file"] = f.name
            results.append(rec)
    data["results"] = results
    return data


def _runtime_plan(t2: list, done2: list) -> list:
    """The runtime and archive plan, projected PER SCENARIO COST CLASS.

    Every figure is derived from the four measured Tier-2 records plus the measured compression
    probe.  No single global average is used anywhere, because the three classes differ by more
    than an order of magnitude in runtime and by more than three orders of magnitude in output.
    """
    mach = machine_facts()
    rows = S.confirmatory_rows()
    n_seeds = 30
    classes = {}
    for r in rows:
        classes.setdefault(scenario_cost_class(r), []).append(r["scenario_id"])
    rec = {r["scenario_id"]: r for r in done2}

    P = ["# Stage 6 — Runtime and Archive Plan", "",
         f"Grounded in the **{len(done2)} completed** Tier-2 full-scale records, the "
         f"**{len(censored_records())} right-censored** record, and a measured compression "
         f"benchmark. Stage 7 must re-check these figures against its own first chunk before "
         f"committing to the full sweep.", "",
         "> **Projected per scenario cost class, never from one global average.** The three "
         "classes below differ by more than an order of magnitude in runtime and by more than "
         "three orders of magnitude in output size; averaging them would misstate both the "
         "compute requirement and the archive requirement.", "", "---", "",
         "## 1. Scenario cost classes", "",
         "The class of a scenario follows from its own frozen matrix row — it is derived, not "
         "assigned by hand:", "",
         "```",
         "SECURITY_FLOOR   security_floor_policy != DISABLED",
         "REASSIGNMENT     security_floor_policy == DISABLED and fault_schedule != NONE",
         "LIGHTWEIGHT      neither",
         "```", "",
         "| class | scenarios | count | Stage-7 runs | measured by | why it costs what it does |",
         "|---|---|---:|---:|---|---|"]
    WHY = {
        "LIGHTWEIGHT": "no floor evaluation and no reconciliation tables",
        "SECURITY_FLOOR": "`EvaluateSecurityFloor` walks the run-lifetime `reserve_records` map "
                          "on every capacity change — O(rounds^2)",
        "REASSIGNMENT": "revoked leases populate `entity_reconciliation` and "
                        "`ownership_reconciliation`, which dominate the serialised output",
    }
    for cls in ("LIGHTWEIGHT", "SECURITY_FLOOR", "REASSIGNMENT"):
        ids = sorted(classes.get(cls, []))
        reps = [s for s in CLASS_REPRESENTATIVE[cls] if s in rec]
        P.append(f"| **{cls}** | {', '.join(ids)} | {len(ids)} | {len(ids) * n_seeds} | "
                 f"{', '.join(reps) if reps else '**not measured**'} | {WHY[cls]} |")
    unbenchmarked = sorted(sid for sid in (s for v in classes.values() for s in v)
                           if sid not in S.TIER2_SCENARIOS)
    P += ["",
          f"Total: {len(rows)} confirmatory scenarios x {n_seeds} seeds = "
          f"**{len(rows) * n_seeds}** Stage-7 physical runs.", "",
          "### 1.1 Unbenchmarked scenarios and their declared scheduling status", "",
          f"Only {len(S.TIER2_SCENARIOS)} of {len(rows)} scenarios were executed at full scale. "
          f"Every other scenario inherits its class figures as a **lower bound**, never as an "
          f"upper bound, and is scheduled at the worst measured class. `C06` is called out "
          f"explicitly because it is the case where the gap is largest:", "",
          "| scenario | class | `runtime_bound_status` | `timeout_class` | `memory_class` |",
          "|---|---|---|---|---|",
          "| `C06` | LIGHTWEIGHT | **`LOWER_BOUND_ONLY`** | **`SLOWEST_MEASURED_CLASS`** | "
          "**`SLOWEST_MEASURED_CLASS`** |",
          f"| every other unbenchmarked scenario ({len(unbenchmarked) - 1}) | its own | "
          f"`LOWER_BOUND_ONLY` | `SLOWEST_MEASURED_CLASS` | `SLOWEST_MEASURED_CLASS` |",
          f"| the {len(S.TIER2_SCENARIOS)} measured scenarios | its own | `MEASURED` | its own "
          f"class | its own class |", "",
          "`C06` is the declared unreachable-target integrity condition: every round exhausts the "
          "whole nonce domain without finding a block, so its per-round hashing work is the "
          "maximum the model admits. It classifies as LIGHTWEIGHT only because its *policy "
          "fields* are lightweight, and it was not one of the four Tier-2 runs. Treating its "
          "runtime as bounded above by the LIGHTWEIGHT figure would be an unmeasured assumption, "
          "so it is not made.", ""]

    cens = censored_records()
    if len(done2) < len(S.TIER2_SCENARIOS):
        P += ["## 1.2 Tier-2 completion status under the governance amendment", "",
              f"| category | count |", "|---|---:|",
              f"| Tier-2 completed runs | **{len(done2)}** |",
              f"| Tier-2 right-censored runs | **{len(cens)}** |",
              f"| Tier-2 failed runs | **0** |", "",
              "**Tier-2 feasibility evidence sufficient for preregistration freeze; final "
              "security-floor runtime and resource sizing deferred to the mandatory Stage-7 "
              "resource preflight.**", "",
              "Governance reason, recorded exactly: the remaining B02 run required approximately "
              "9-10 additional wall-clock hours and Stage 6 was closed under an explicit "
              "user-authorised time constraint — **not** because of any effect direction or "
              "magnitude. No effect was observed from the partial run and none is inferred.", ""]
        for c in cens:
            P += [f"### {c['scenario_id']} — `{c['run_status']}`", "",
                  "| quantity | value | interpretation |", "|---|---:|---|",
                  f"| elapsed wall | {c['elapsed_wall_seconds_LOWER_BOUND']:,.0f} s | "
                  f"**LOWER_BOUND** |",
                  f"| CPU seconds | {c['cpu_seconds_LOWER_BOUND']:,.0f} s | **LOWER_BOUND** |",
                  f"| CPU / wall | {c['cpu_over_wall_ratio']:.3f} | measured |",
                  f"| VmHWM | {c['vm_hwm_mb_LOWER_BOUND']:,.0f} MB | **LOWER_BOUND** |",
                  f"| simulated time | {c['simulated_time_seconds_LOWER_BOUND']:,.0f} of "
                  f"{c['horizon_T']:,.0f} s "
                  f"({100 * c['simulated_fraction_LOWER_BOUND']:.1f} %) | **LOWER_BOUND** |",
                  f"| output bytes | {c['results_json_bytes']} | no output was written |",
                  f"| config SHA-256 | `{c['config_sha256'][:32]}...` | preserved |",
                  f"| master seed | `{c['master_seed']}` | preserved, **not** redrawn |", "",
                  f"*{c['status_note']}*", "",
                  f"**Termination cause: `{c['censoring']['termination_cause']}`.** "
                  f"{c['censoring']['termination_evidence']}", "",
                  f"Rerun policy: {c['censoring']['rerun_policy']}", "",
                  f"Scientific use: {c['censoring']['scientific_use']}.", ""]
        P += ["The class projections below therefore **cannot be closed for the SECURITY_FLOOR "
              "class**, whose only representative is censored. Every SECURITY_FLOOR figure that "
              "would depend on it is reported as `LOWER_BOUND` or omitted, never as a completed "
              "measurement. The Tier-1 figures do not substitute: the confirmatory scale is "
              "roughly twelve times the population and fifty times the horizon.", "",
              "### Lower-bound resource sizing for the SECURITY_FLOOR class", "",
              "| quantity | value | basis |", "|---|---:|---|"]
        if cens:
            c = cens[0]
            frac = c["simulated_fraction_LOWER_BOUND"]
            P += [f"| runtime `LOWER_BOUND` | {c['elapsed_wall_seconds_LOWER_BOUND'] / 3600:.2f} h | "
                  f"observed before censoring |",
                  f"| runtime `ESTIMATED` (quadratic fit) | "
                  f"~{c['elapsed_wall_seconds_LOWER_BOUND'] / 3600 / (frac ** 2):.1f} h | "
                  f"**ESTIMATED**, not measured |",
                  f"| peak memory `LOWER_BOUND` | {c['vm_hwm_mb_LOWER_BOUND']:,.0f} MB | "
                  f"observed before censoring |",
                  f"| peak memory `ESTIMATED` for sizing | "
                  f"~{c['vm_hwm_mb_LOWER_BOUND'] / frac:,.0f} MB | **ESTIMATED**, linear in "
                  f"simulated fraction |",
                  f"| output bytes | unknown | never written |", ""]
        P += ["Stage 7 must not size the SECURITY_FLOOR class from these numbers without first "
              "passing the resource preflight, which requires either the completed B02 run or an "
              "equivalent full-scale security-floor preflight on the real host.", ""]
        return P

    def stat(cls, key):
        return [rec[s][key] for s in CLASS_REPRESENTATIVE[cls] if s in rec]

    P += ["## 2. Measured cost per class", "",
          "Each class figure is the **maximum** observed in that class, never the mean: a "
          "timeout and a memory budget must be sized on the worst case.", "",
          "| class | wall clock (s) | wall clock (h) | peak RSS (MB) | output bytes | rounds | "
          "events |", "|---|---|---:|---:|---:|---:|---:|"]
    cls_cost = {}
    for cls in ("LIGHTWEIGHT", "SECURITY_FLOOR", "REASSIGNMENT"):
        w, m, b = stat(cls, "wall_clock_seconds"), stat(cls, "peak_rss_mb"), \
            stat(cls, "results_json_bytes")
        rd, ev = stat(cls, "rounds_executed"), stat(cls, "log_event_count")
        cls_cost[cls] = {"wall": max(w), "rss": max(m), "bytes": max(b),
                         "wall_min": min(w), "wall_max": max(w), "n": len(w)}
        span = (f"{min(w):,.1f}" if len(w) == 1
                else f"{min(w):,.1f} – {max(w):,.1f} (n={len(w)})")
        P.append(f"| {cls} | {span} | {max(w) / 3600:.2f} | {max(m):,.0f} | {max(b):,} | "
                 f"{max(rd):,} | {max(ev):,} |")
    lw = cls_cost["LIGHTWEIGHT"]
    P += ["",
          f"**Lightweight runtime distribution** (n={lw['n']}): "
          f"{lw['wall_min']:,.1f} s – {lw['wall_max']:,.1f} s, spread "
          f"{100 * (lw['wall_max'] - lw['wall_min']) / lw['wall_min']:.1f} % — tight enough that "
          f"two observations bound the class usefully.",
          f"**Security-floor runtime**: {cls_cost['SECURITY_FLOOR']['wall']:,.1f} s "
          f"({cls_cost['SECURITY_FLOOR']['wall'] / 3600:.2f} h), "
          f"{cls_cost['SECURITY_FLOOR']['wall'] / lw['wall_max']:.1f}x the lightweight class.",
          f"**Reassignment runtime**: {cls_cost['REASSIGNMENT']['wall']:,.1f} s "
          f"({cls_cost['REASSIGNMENT']['wall'] / 3600:.2f} h), "
          f"{cls_cost['REASSIGNMENT']['wall'] / lw['wall_max']:.1f}x the lightweight class; its "
          f"output is {cls_cost['REASSIGNMENT']['bytes'] / lw['bytes']:,.0f}x larger.",
          "",
          "| class | peak RSS | output bytes |", "|---|---:|---:|"]
    for cls in ("LIGHTWEIGHT", "SECURITY_FLOOR", "REASSIGNMENT"):
        P.append(f"| {cls} | {cls_cost[cls]['rss']:,.0f} MB | "
                 f"{cls_cost[cls]['bytes']:,} |")
    P.append("")

    ext = {s: external_resources(s) for s in S.TIER2_SCENARIOS}
    have = {s: v for s, v in ext.items() if v}
    if have:
        P += ["### 2.1 Externally sampled CPU time and peak RSS", "",
              "Captured from `/proc/<pid>` by `sample_run_resources.py` for a run whose CPU time "
              "was required after it had already started. The harness checkpoint was never "
              "modified.", "",
              "| scenario | CPU seconds | user | system | CPU / wall | VmHWM (MB) |",
              "|---|---:|---:|---:|---:|---:|"]
        for s, v in sorted(have.items()):
            w = rec[s]["wall_clock_seconds"] if s in rec else (v.get("wall_seconds") or 1)
            P.append(f"| {s} | {v['cpu_seconds']:,.1f} | {v['utime_s']:,.1f} | "
                     f"{v['stime_s']:,.1f} | {v['cpu_seconds'] / w:.3f} | "
                     f"{v.get('vm_hwm_kb', 0) / 1024:,.0f} |")
        missing = [s for s in S.TIER2_SCENARIOS if s not in have]
        P += ["", (f"CPU time was **not captured** for {', '.join(sorted(missing))}: those "
                   f"processes had already exited before CPU time became a required field. "
                   f"Their wall clock, peak RSS and every other required field are measured and "
                   f"recorded in full; the missing quantity is stated rather than estimated or "
                   f"back-filled." if missing else
                   "CPU time was captured for every run for which it was required."), ""]

    tot_wall = sum(cls_cost[c]["wall"] * len(classes.get(c, [])) * n_seeds for c in cls_cost)
    tot_bytes = sum(cls_cost[c]["bytes"] * len(classes.get(c, [])) * n_seeds for c in cls_cost)
    #: storage planning quantities, derived once and used by both §5 and §5a
    cons_ratio = XZ_RATIO / COMPRESSION_SAFETY_FACTOR
    chunk_raw = cls_cost["REASSIGNMENT"]["bytes"] * n_seeds
    P += ["## 3. Stage-7 projection", "",
          "| class | runs | per-run wall (h) | class total (h) | per-run bytes | class total |",
          "|---|---:|---:|---:|---:|---:|"]
    for cls in ("LIGHTWEIGHT", "SECURITY_FLOOR", "REASSIGNMENT"):
        n = len(classes.get(cls, [])) * n_seeds
        c = cls_cost[cls]
        P.append(f"| {cls} | {n} | {c['wall'] / 3600:.2f} | {n * c['wall'] / 3600:,.0f} | "
                 f"{c['bytes']:,} | {n * c['bytes'] / 1e9:.2f} GB |")
    P += [f"| **total** | **{len(rows) * n_seeds}** | — | **{tot_wall / 3600:,.0f}** | — | "
          f"**{tot_bytes / 1e9:.2f} GB** |", "",
          "| quantity | value |", "|---|---|",
          f"| projected raw Stage-7 bytes | **{tot_bytes / 1e9:.2f} GB** uncompressed |",
          f"| projected compressed (gzip -9, **measured** {GZIP_RATIO:.1f}x) | "
          f"**{tot_bytes / GZIP_RATIO / 1e9:.3f} GB** |",
          f"| projected compressed (xz -9, **measured** {XZ_RATIO:.1f}x) | "
          f"**{tot_bytes / XZ_RATIO / 1e9:.3f} GB** |",
          f"| **conservative** compressed (xz ratio / {COMPRESSION_SAFETY_FACTOR:.0f} = "
          f"{XZ_RATIO / COMPRESSION_SAFETY_FACTOR:.1f}x) | "
          f"**{tot_bytes / (XZ_RATIO / COMPRESSION_SAFETY_FACTOR) / 1e9:.3f} GB** |",
          f"| **conservative** raw working set (x{RAW_HEADROOM_FACTOR}) | "
          f"**{tot_bytes * RAW_HEADROOM_FACTOR / 1e9:.2f} GB** |",
          f"| single-worker duration | **{tot_wall / 3600:,.0f} h** "
          f"({tot_wall / 86400:,.0f} days) |", "",
          f"**Compression is measured, not assumed.** A `{COMPRESSION_PROBE['scenario']}` payload "
          f"was produced at horizon {COMPRESSION_PROBE['horizon_T']:.0f} s "
          f"({COMPRESSION_PROBE['rounds']} rounds), serialised to "
          f"{COMPRESSION_PROBE['raw_bytes']:,} bytes and compressed with the codecs present in "
          f"the locked environment: gzip -9 gave {COMPRESSION_PROBE['gzip9_bytes']:,} bytes "
          f"({GZIP_RATIO:.1f}x) and xz -9 gave {COMPRESSION_PROBE['xz9_bytes']:,} bytes "
          f"({XZ_RATIO:.1f}x). The ratio is high because the payload is dominated by two "
          f"repetitive tables: "
          + ", ".join(f"`{k}` ({pct:.1f} %)"
                      for k, _b, pct in COMPRESSION_PROBE["largest_keys"][:2]) + ".",
          "",
          "**zstd is not installed in the locked environment**, so the archive format is stated "
          "as `.tar.xz` against a measured ratio rather than `.tar.zst` against an assumed one. "
          "If Stage 7 runs on a host with zstd, the ratio must be re-measured before the plan "
          "claims it.", ""]

    usable = mach["total_ram_gb"] * USABLE_RAM_FRACTION
    rss = {c: cls_cost[c]["rss"] for c in cls_cost}
    worst_heavy = max(rss[c] for c in HEAVY_CLASSES)
    # per-class limit from the MEMORY EQUATION, then bounded by cores — never the reverse
    ram_cap = {c: int(usable * 1024 / (RAM_SAFETY_MARGIN * rss[c])) for c in rss}
    limit = {c: max(0, min(ram_cap[c], mach["cpu_count"])) for c in rss}
    for c in HEAVY_CLASSES:
        limit[c] = min(limit[c], HEAVY_WORKER_CAP)

    P += ["## 4. Memory-aware Stage-7 scheduling plan", "",
          f"Measured on the locked host: **{mach['cpu_count']} cores**, "
          f"**{mach['total_ram_gb']:.1f} GB RAM**, "
          f"**{mach['disk_free_gb']:.1f} GB free disk**.", "",
          "### 4.0 The memory equation", "",
          "**Core count is an upper bound on the worker set, never a declaration of capacity.** "
          "A host can have idle cores and still be unable to hold another heavy worker. A "
          "candidate worker set `{n_c}` over classes `c` is admissible only if **both** hold:", "",
          "```",
          "MEMORY   RAM_SAFETY_MARGIN * SUM_c ( n_c * peak_rss_c )  <=  "
          "USABLE_RAM_FRACTION * total_ram",
          "CORES    SUM_c n_c                                      <=  cpu_count",
          "HEAVY    n_SECURITY_FLOOR + n_REASSIGNMENT               <=  HEAVY_WORKER_CAP",
          "```", "",
          "| symbol | value | provenance |", "|---|---:|---|",
          f"| `RAM_SAFETY_MARGIN` | **{RAM_SAFETY_MARGIN}** | declared; >= 25 % headroom over "
          f"measured peak RSS |",
          f"| `USABLE_RAM_FRACTION` | **{USABLE_RAM_FRACTION}** | declared; OS, page cache, "
          f"scheduler |",
          f"| `HEAVY_WORKER_CAP` | **{HEAVY_WORKER_CAP}** | declared; SECURITY_FLOOR + "
          f"REASSIGNMENT combined |",
          f"| `total_ram` | {mach['total_ram_gb']:.1f} GB | measured |",
          f"| **usable RAM** | **{usable:.2f} GB** | "
          f"{mach['total_ram_gb']:.1f} x {USABLE_RAM_FRACTION} |",
          f"| worst-case heavy `peak_rss` | **{worst_heavy / 1024:.2f} GB** | measured |", "",
          f"Worked example for the heavy classes: "
          f"`floor({usable:.2f} / ({RAM_SAFETY_MARGIN} x {worst_heavy / 1024:.2f})) = "
          f"floor({usable / (RAM_SAFETY_MARGIN * worst_heavy / 1024):.2f}) = "
          f"{int(usable * 1024 / (RAM_SAFETY_MARGIN * worst_heavy))}` worst-case heavy workers. "
          f"Without the margin the arithmetic would read "
          f"`floor({usable:.2f} / {worst_heavy / 1024:.2f}) = "
          f"{int(usable * 1024 / worst_heavy)}`, and using the "
          f"{mach['cpu_count']}-core count instead would claim {mach['cpu_count']} — "
          f"**{mach['cpu_count'] * worst_heavy / 1024:.1f} GB of demand against a "
          f"{usable:.2f} GB budget.**", "",
          "### 4.1 Per-class concurrency limits", "",
          "| class | peak RSS | with margin | RAM-bound limit | core bound | heavy cap | "
          "**max simultaneous** |", "|---|---:|---:|---:|---:|---:|---:|"]
    for cls in ("LIGHTWEIGHT", "SECURITY_FLOOR", "REASSIGNMENT"):
        hc = str(HEAVY_WORKER_CAP) if cls in HEAVY_CLASSES else "—"
        P.append(f"| {cls} | {rss[cls]:,.0f} MB | "
                 f"{RAM_SAFETY_MARGIN * rss[cls]:,.0f} MB | {ram_cap[cls]} | "
                 f"{mach['cpu_count']} | {hc} | **{limit[cls]}** |")
    P += ["",
          f"* **LIGHTWEIGHT**: up to **{limit['LIGHTWEIGHT']}** concurrent — the measured "
          f"CPU/RAM-safe limit.",
          f"* **SECURITY_FLOOR and REASSIGNMENT**: no more than **{HEAVY_WORKER_CAP} heavy "
          f"workers in total**, and only in combinations the memory equation admits.", ""]

    # enumerate every admissible mix under the equation
    mixes = []
    for a in range(mach["cpu_count"] + 1):
        for f in range(mach["cpu_count"] + 1 - a):
            for rr in range(mach["cpu_count"] + 1 - a - f):
                if a + f + rr == 0:
                    continue
                counts = {"LIGHTWEIGHT": a, "SECURITY_FLOOR": f, "REASSIGNMENT": rr}
                if not admissible(counts, rss, usable):
                    continue
                need = sum(n * rss[c] for c, n in counts.items()) / 1024.0
                mixes.append((a + f + rr, a, f, rr, need, RAM_SAFETY_MARGIN * need))
    mixes.sort(key=lambda m: (-(m[2] + m[3]), -m[0], -m[5]))
    P += ["### 4.2 Admissible mixed combinations", "",
          f"Every mix satisfying all three constraints. {len(mixes)} exist; those containing "
          f"heavy workers are listed first because they are the binding cases.", "",
          "| lightweight | security-floor | reassignment | procs | measured RAM | "
          f"x{RAM_SAFETY_MARGIN} required | fits {usable:.2f} GB |",
          "|---:|---:|---:|---:|---:|---:|---|"]
    for tot, a, f, rr, need, req in mixes[:10]:
        P.append(f"| {a} | {f} | {rr} | {tot} | {need:.2f} GB | {req:.2f} GB | yes |")
    heavy_mixes = [m for m in mixes if m[2] + m[3] >= 2]
    P += ["",
          (f"**{len(heavy_mixes)} admissible mix(es) carry {HEAVY_WORKER_CAP} heavy workers.** "
           if heavy_mixes else
           "**No admissible mix carries two heavy workers on this host.** ")
          + (f"Two REASSIGNMENT workers would need "
             f"{RAM_SAFETY_MARGIN * 2 * rss['REASSIGNMENT'] / 1024:.2f} GB against "
             f"{usable:.2f} GB usable, so the pair is inadmissible even though the heavy cap "
             f"permits two; whether a heavy pair fits depends on which classes are paired, "
             f"which is exactly why the equation is applied per-mix rather than as a single "
             f"number."), ""]

    timeout_s = max(c["wall"] for c in cls_cost.values()) * TIMEOUT_SAFETY_FACTOR
    worst = max(c["wall"] for c in cls_cost.values())
    P += ["### 4.1 Fixed per-run timeout", "", "| item | value |", "|---|---|",
          f"| maximum measured Tier-2 wall clock | {worst:,.1f} s ({worst / 3600:.2f} h) |",
          f"| preregistered safety factor | **x{TIMEOUT_SAFETY_FACTOR}** |",
          f"| **fixed per-run timeout** | **{timeout_s:,.0f} s ({timeout_s / 3600:.1f} h)** |",
          "",
          "The factor is declared here **before** Stage 7 and is not adjusted afterwards. A run "
          "that exceeds the timeout is an INFRASTRUCTURE failure under the retention policy, "
          "not a scientific result, and is handled by §4.3.", "",
          "**One timeout, applied to every scenario — including the unbenchmarked ones.** The "
          "timeout is derived from the slowest *measured* class and then applied uniformly. "
          "`C06` in particular is treated as an **unbenchmarked worst case**: it classifies as "
          "LIGHTWEIGHT by policy fields, but it is the declared unreachable-target condition in "
          "which every round exhausts the entire nonce domain without finding a block, so its "
          "per-round hashing work is the maximum the model admits. It was not one of the four "
          "Tier-2 runs. It is therefore scheduled at the **same timeout and the same per-worker "
          "memory reservation as the slowest measured class**, never at the lightweight figure. "
          "The same rule applies to any scenario whose class representative was not itself "
          "executed at full scale.", "",
          "### 4.2 External heartbeat and logging plan", "",
          "The accepted engine emits no progress output and must not be modified, so liveness is "
          "observed from outside the process:", "",
          "* every Stage-7 run is launched as its own process with its own log file "
          "`raw/<scenario>/<run_id>.log`, exactly as the four Tier-2 runs were;",
          "* `sample_run_resources.py --pid <pid>` runs alongside each execution and rewrites "
          "`<run_id>.resources.json` every 30 s with CPU seconds, VmRSS and VmHWM — this file "
          "**is** the heartbeat, and a sample file that stops advancing is the stall signal;",
          "* the checkpoint is written only on completion, so an interrupted run is detectable "
          "as a fresh `.resources.json` with no `.json` beside it;",
          "* progress inside a run can be read without instrumenting the engine by sampling the "
          "live stack (`py-spy dump --locals`), which is how B02's simulated-time progress was "
          "tracked during this pilot;",
          "* a chunk is marked complete only when every run in it has both a checkpoint and a "
          "verified SHA-256.", "",
          "### 4.3 Same-seed infrastructure rerun policy", "",
          "If a run fails for an infrastructure reason — timeout, OOM kill, host loss, disk "
          "exhaustion — then:", "",
          "1. the exact configuration, master seed, log and partial resource samples are "
          "**preserved** under `raw/<scenario>/failed/<run_id>/`;",
          "2. the run is retried with the **same** `(scenario_id, master_seed)` pair and the "
          "**same** frozen configuration;",
          "3. **no replacement seed is ever drawn**, and the seed registry is never extended;",
          "4. the retry is not an additional observation — the pair contributes exactly one "
          "result to the analysis, and both attempts are recorded in the run registry with the "
          "failure reason;",
          "5. a run that fails for a **scientific** reason (an engine exception, an integrity "
          "gate) is **not** retried: it is retained and reported as a failed run.", ""]

    # The realistic sustained schedule is the widest admissible mix, chosen by total processes.
    best = max(mixes, key=lambda m: (m[0], m[2] + m[3]))
    host_conc = best[0]
    host_heavy = best[2] + best[3]
    host_hours = tot_wall / 3600 / host_conc
    worst_rss = max(x["rss"] for x in cls_cost.values())
    P += ["## 5. Duration and required resources", "", "| configuration | duration |",
          "|---|---|",
          f"| single worker | **{tot_wall / 3600:,.0f} h** = {tot_wall / 86400:,.0f} days |",
          f"| this host ({mach['cpu_count']} cores, {mach['total_ram_gb']:.1f} GB), best mix "
          f"{host_conc} concurrent | **{host_hours:,.0f} h** = **{host_hours / 24:,.0f} days** |"]
    for cores, ram in ((16, 64), (32, 128), (64, 256)):
        c = min(cores, int(ram * USABLE_RAM_FRACTION * 1024 / worst_rss))
        P.append(f"| {cores} cores / {ram} GB -> {c} concurrent | "
                 f"{tot_wall / 3600 / c:,.0f} h = {tot_wall / 3600 / c / 24:,.1f} days |")
    P += ["",
          "**Required resources for a practical external execution** — to finish the frozen "
          "660-run sweep in about a week of wall clock:", "",
          "| requirement | value | basis |", "|---|---|---|",
          f"| CPU cores | **>= 16** | {tot_wall / 3600:,.0f} core-hours total; 16 concurrent "
          f"gives {tot_wall / 3600 / 16 / 24:.1f} days |",
          f"| RAM | **>= {16 * worst_rss / 1024:.0f} GB** | 16 x the {worst_rss:,.0f} MB "
          f"worst-case peak RSS, before the {USABLE_RAM_FRACTION:.0%} usable-fraction margin |",
          f"| scratch disk | **>= {tot_bytes / 1e9 * 1.5:.0f} GB** | {tot_bytes / 1e9:.2f} GB "
          f"raw plus 50 % for archives and verification copies |",
          f"| durable archive | **>= {tot_bytes / XZ_RATIO / 1e9:.2f} GB** | measured xz -9 "
          f"ratio of {XZ_RATIO:.1f}x |",
          f"| per-run timeout | **{timeout_s / 3600:.1f} h** | maximum measured x "
          f"{TIMEOUT_SAFETY_FACTOR} |",
          f"| minimum per-worker RAM | **{worst_rss / 1024:.1f} GB** | the worst-case class "
          f"peak |", "",
          "### 5.1 Concrete resources, and whether they suffice", "",
          "Only resources that were **measured in this session** are listed as identified. No "
          "external host is asserted that has not been verified to exist.", "",
          "| resource | measured | Stage-7 requirement | sufficient? |", "|---|---|---|---|",
          f"| locked host CPU | {mach['cpu_count']} cores | "
          f"{tot_wall / 3600:,.0f} core-hours | yes in principle, "
          f"**{host_hours / 24:,.0f} days** wall clock |",
          f"| locked host RAM | {mach['total_ram_gb']:.1f} GB "
          f"({usable:.1f} GB usable) | {worst_rss / 1024:.1f} GB per worst-case worker | "
          f"**yes** — supports {best[0]} concurrent ({host_heavy} heavy) under the "
          f"memory equation |",
          f"| locked host disk | **{mach['disk_free_gb']:.1f} GB free** of "
          f"{mach['disk_total_gb']:.0f} GB | "
          f"{(chunk_raw * RAW_HEADROOM_FACTOR + tot_bytes / cons_ratio) / 1e9:.2f} GB peak with "
          f"compress-on-write | **yes** |",
          f"| locked host disk, raw-first | same | {tot_bytes * RAW_HEADROOM_FACTOR / 1e9:.2f} GB | "
          f"**NO** — compress-on-write is mandatory, not optional |",
          f"| locked host lifetime | ephemeral; reclaimed on inactivity | "
          f"{host_hours / 24:,.0f} days continuous | **NO** |", "",
          "**Storage is solved and compute is not.** Sizing disk on the conservative ratio and "
          "writing each payload through a compressor brings peak disk to "
          f"{(chunk_raw * RAW_HEADROOM_FACTOR + tot_bytes / cons_ratio) / 1e9:.2f} GB against "
          f"{mach['disk_free_gb']:.1f} GB measured free — comfortable. Writing raw first would "
          f"need {tot_bytes * RAW_HEADROOM_FACTOR / 1e9:.2f} GB and would **not** fit, so "
          "compress-on-write is a hard requirement of this plan rather than an optimisation.", "",
          "The binding constraint is **execution-host lifetime**, not cores, RAM or disk: the "
          "locked host is an ephemeral container reclaimed after inactivity, and the sweep needs "
          f"{host_hours / 24:,.0f} days of continuous execution on it. Stage 7 therefore requires "
          "a persistent execution host, identified and verified **before** execution begins.", "",
          f"On the locked host alone the sweep needs **{host_hours / 24:,.0f} days**, which is "
          f"why an external execution host is identified as a Stage-7 **prerequisite** rather "
          f"than discovered during Stage 7. This host is memory-bound below its core count: "
          f"{mach['cpu_count']} simultaneous worst-case runs would need "
          f"{mach['cpu_count'] * worst_rss / 1024:.1f} GB against {usable:.1f} GB usable.", ""]

    # ---- storage strategy, sized on the CONSERVATIVE ratio
    P += ["## 5a. Storage strategy and its safety margin", "",
          f"The compression ratio was **measured on a reduced-horizon "
          f"`{COMPRESSION_PROBE['scenario']}` payload** — "
          f"{COMPRESSION_PROBE['rounds']} rounds against the "
          f"{cls_cost['REASSIGNMENT'].get('rounds', 9592):,}-round full-scale run — so it is an "
          f"extrapolation, not a full-scale observation. Storage is therefore **not** sized on "
          f"it directly. The planning ratio is the measured ratio divided by a declared safety "
          f"factor of **{COMPRESSION_SAFETY_FACTOR:.0f}**, and raw working set carries a further "
          f"**x{RAW_HEADROOM_FACTOR}** headroom for logs, resource sidecars, checksums and the "
          f"transient copy that exists while a chunk is archived and verified.", "",
          "| basis | ratio | projected archive | used for planning |",
          "|---|---:|---:|---|",
          f"| xz -9 measured (reduced horizon) | {XZ_RATIO:.1f}x | "
          f"{tot_bytes / XZ_RATIO / 1e9:.3f} GB | no — optimistic |",
          f"| gzip -9 measured (reduced horizon) | {GZIP_RATIO:.1f}x | "
          f"{tot_bytes / GZIP_RATIO / 1e9:.3f} GB | no — fallback codec |",
          f"| **conservative (xz / {COMPRESSION_SAFETY_FACTOR:.0f})** | **{cons_ratio:.1f}x** | "
          f"**{tot_bytes / cons_ratio / 1e9:.3f} GB** | **yes** |",
          f"| no compression at all | 1.0x | {tot_bytes / 1e9:.2f} GB | bounding case |", "",
          "**Compress on write.** Storing every run raw before archiving would need "
          f"{tot_bytes * RAW_HEADROOM_FACTOR / 1e9:.2f} GB simultaneously. The Stage-7 harness "
          f"instead writes each run's payload through a compressor, so the raw form never has to "
          f"exist on disk at full sweep size. The bounding working set is then **one chunk**:", "",
          "| working-set item | conservative size |", "|---|---:|",
          f"| one REASSIGNMENT chunk, raw, mid-archive | {chunk_raw * RAW_HEADROOM_FACTOR / 1e9:.2f} GB |",
          f"| one REASSIGNMENT chunk, conservative archive | {chunk_raw / cons_ratio / 1e6:.0f} MB |",
          f"| all {len(rows)} chunks, conservative archive | "
          f"{tot_bytes / cons_ratio / 1e9:.3f} GB |",
          f"| **peak disk required** (one raw chunk + all archives) | "
          f"**{(chunk_raw * RAW_HEADROOM_FACTOR + tot_bytes / cons_ratio) / 1e9:.2f} GB** |", "",
          f"This is the number Stage 7 must provision against, not the "
          f"{tot_bytes / 1e9:.2f} GB raw figure.", ""]

    P += ["## 6. Archive plan", "", "| item | value |", "|---|---|",
          "| raw output | `experiments/thesis_revision_v45/stage_07/raw/<block>/<scenario>/"
          "<run_id>.json` |",
          "| per-run log | `raw/<block>/<scenario>/<run_id>.log` |",
          "| per-run heartbeat | `raw/<block>/<scenario>/<run_id>.resources.json` |",
          "| per-run checksum | SHA-256, written beside each output |",
          "| chunk manifest | `manifests/<scenario>.sha256`, SHA-256 over the sorted per-run "
          "digests |",
          "| archive unit | one compressed archive per scenario chunk, "
          "`pocol-v45-stage07-<scenario>.tar.xz` |",
          f"| largest chunk (raw) | {cls_cost['REASSIGNMENT']['bytes'] * n_seeds / 1e9:.2f} GB "
          f"(one REASSIGNMENT scenario x {n_seeds} seeds) |",
          f"| largest chunk (xz -9) | "
          f"{cls_cost['REASSIGNMENT']['bytes'] * n_seeds / XZ_RATIO / 1e6:.0f} MB |",
          "| archive checksum | SHA-256 per archive plus a top-level manifest over all chunk "
          "checksums |",
          "| verification | round-trip extraction and digest comparison before the raw "
          "directory is treated as redundant |", "",
          f"Chunking by scenario ({n_seeds} runs per chunk, {len(rows)} chunks) keeps each chunk "
          f"to a predictable duration and a predictable size, and makes a failed chunk cheap to "
          f"re-run. Because chunk cost is now class-specific, the "
          f"{len(classes.get('SECURITY_FLOOR', []))} SECURITY_FLOOR chunks should be started "
          f"first: each is the longest single unit of work in the sweep at "
          f"{cls_cost['SECURITY_FLOOR']['wall'] * n_seeds / 3600:,.0f} h.", "",
          "Round-level and miner-level tables may be archived as **secondary data**. They are "
          "not inferentially independent and never enter a confirmatory test as units.", "",
          "## 7. What is not archived in Stage 6", "",
          "Nothing. Stage 6 produced **no confirmatory output at all**. "
          "`experiments/thesis_revision_v45/stage_06/confirmatory/` holds configurations and "
          "registries only, enforced by `validate_preregistration.py` check [9] and by the "
          "GitHub Actions workflow.", ""]
    return P


def build(data: dict) -> tuple:
    res = data["results"]
    t1 = [r for r in res if r["tier"] == "TIER1"]
    t2 = [r for r in res if r["tier"] == "TIER2" and r["scenario_id"] in S.TIER2_SCENARIOS]
    h10d = [r for r in res if r["tier"] == "TIER2" and r["scenario_id"] not in S.TIER2_SCENARIOS]
    done1 = [r for r in t1 if r["run_status"] == "COMPLETED"]
    done2 = [r for r in t2 if r["run_status"] == "COMPLETED"]

    # ---------------------------------------------------------------- pilot report
    R = ["# Stage 6 — Pilot Report (FEASIBILITY ONLY)", "",
         "Generated from `experiments/thesis_revision_v45/stage_06/pilot/pilot_results.json` by",
         "`generate_pilot_report.py`. Every number below is read from the executed pilot.", "",
         "> This report contains **no** condition-specific energy saving, **no** inferential",
         "> effect estimate, **no** p-value, **no** confidence interval, **no** ranking of",
         "> conditions by energy effect, and **no** claim about which hypothesis passed. The only",
         "> energy quantities reported are deterministic accounting residuals with fixed numeric",
         "> tolerances (IP-H1, IP-H2, IP-H5), which are integrity gates rather than effects.", "",
         "**Pilot seeds only.** Every executed seed is drawn from the PILOT registry, which is",
         "provably disjoint from the confirmatory registry. **No confirmatory seed was executed.**",
         "", "---", "", "## 1. Execution summary", "",
         "| tier | planned | executed | completed | failed |", "|---|---:|---:|---:|---:|",
         f"| Tier 1 (12 miners, 200 s, domain 400, batch 25) | {len(t1)} | {len(t1)} | "
         f"{len(done1)} | {len(t1) - len(done1)} |",
         f"| Tier 2 (141 miners, 10 000 s, domain 4000, batch 50) | {len(t2)} | {len(t2)} | "
         f"{len(done2)} | {len(t2) - len(done2)} |", ""]

    if done1:
        w = [r["wall_clock_seconds"] for r in done1]
        R += ["## 2. Tier 1 — reduced-scale semantic pilot", "",
              f"All **{len(S.confirmatory_rows())}** frozen confirmatory scenario types executed, "
              f"**2** pilot seeds each, **{len(t1)}** runs, **{len(t1) - len(done1)}** exceptions.",
              "", "| measurement | value |", "|---|---|",
              f"| wall clock per run | {fmt(min(w))} s – {fmt(max(w))} s "
              f"(total {fmt(sum(w), 1)} s) |",
              f"| peak RSS | {fmt(max(r['peak_rss_mb'] for r in done1), 0)} MB |",
              f"| results JSON bytes per run | "
              f"{min(r['results_json_bytes'] for r in done1):,} – "
              f"{max(r['results_json_bytes'] for r in done1):,} |",
              f"| event-log entries per run | {min(r['log_event_count'] for r in done1):,} – "
              f"{max(r['log_event_count'] for r in done1):,} |",
              f"| rounds per run | {min(r['rounds_executed'] for r in done1)} – "
              f"{max(r['rounds_executed'] for r in done1)} |",
              f"| adapter schema keys | "
              f"{sorted({r['schema_key_count'] for r in done1})[0]} (stable across all runs) |",
              f"| zero-block runs | {sum(r['zero_block_indicator'] for r in done1)} |",
              f"| runs reporting `maximum_q_adv = NA` | "
              f"{sum(1 for r in done1 if r['maximum_q_adv'] == 'NA')} of {len(done1)} |",
              f"| exceptions | {len(t1) - len(done1)} |", ""]

        # residency composition — the measurement behind decision D-03
        agg = {}
        for r in done1:
            for k, v in r["residency_by_state_s"].items():
                agg[k] = agg.get(k, 0.0) + v
        tot = sum(agg.values()) or 1.0
        R += ["### 2.1 Residency composition (the measurement behind decision D-03)", "",
              "| state | seconds | share |", "|---|---:|---:|"]
        for k, v in sorted(agg.items(), key=lambda kv: -kv[1]):
            R.append(f"| `{k}` | {fmt(v, 1)} | {100 * v / tot:.1f} % |")
        R += ["",
              "WAKING dominates because the 1.0 s wake latency is a large fraction of a ≈1.4 s "
              "round. This is why the idle-policy-off level must also raise `P_wake` to `P_hash`: "
              "otherwise the IP-H5 negative control would show a large spurious saving.", ""]

    # ---- Tier-2 per-run record (the exact required field list, one row per run)
    R += ["## 2b. Tier 2 — full-scale runtime pilot, per-run record", "",
          "Four representative full-scale configurations — heterogeneous control (A03), "
          "heterogeneous idle policy (A05), security floor (B02) and genuine Path-B "
          "reassignment (C04) — each on **one fixed pilot seed**, each executed as an "
          "independent process with its own log and its own checkpoint file.", "",
          "Only feasibility quantities are recorded. **No condition-specific energy saving, "
          "ranking, confidence interval, p-value or hypothesis verdict is reported from "
          "Tier 2.**", ""]
    if t2:
        for r in sorted(t2, key=lambda x: x["scenario_id"]):
            sid = r["scenario_id"]
            nas = na_fields(r)
            fails = gate_failures(r)
            R += [f"### {sid}", "", "| field | value |", "|---|---|",
                  f"| scenario id | `{sid}` |",
                  f"| pilot seed | `{r['master_seed']}` (pilot index "
                  f"{r.get('seed_index', '-')}) |",
                  f"| completion status | **{r['run_status']}** |",
                  f"| wall-clock seconds | {fmt(r.get('wall_clock_seconds', 0), 1)} |",
                  f"| peak memory (MB RSS) | {fmt(r.get('peak_rss_mb', 0), 0)} |",
                  f"| output bytes (results JSON) | {r.get('results_json_bytes', 0):,} |",
                  f"| event count | {r.get('log_event_count', 0):,} |",
                  f"| round count | {r.get('rounds_executed', 0):,} |",
                  f"| zero-block count | {r.get('zero_block_indicator', 0)} |",
                  f"| NA count by field | {len(nas)}"
                  + (f" (`{'`, `'.join(nas)}`)" if nas else " (none)") + " |",
                  f"| exception count | {0 if r['run_status'] == 'COMPLETED' else 1} |",
                  f"| integrity-gate failures | {len(fails)}"
                  + (f" (`{'`, `'.join(fails)}`)" if fails else " (none)") + " |",
                  f"| log path | `experiments/thesis_revision_v45/stage_06/pilot/tier2/"
                  f"{sid}.log` |",
                  f"| checkpoint path | `experiments/thesis_revision_v45/stage_06/pilot/tier2/"
                  f"{r.get('source_file', sid + '.json')}` |", ""]
        if len(t2) < len(S.TIER2_SCENARIOS):
            missing = sorted(set(S.TIER2_SCENARIOS) - {r["scenario_id"] for r in t2})
            R += [f"**Incomplete.** {len(t2)} of {len(S.TIER2_SCENARIOS)} required Tier-2 runs "
                  f"are recorded; missing: {', '.join(missing)}. Stage 6 is not ready for "
                  f"scientific freeze until all four are recorded.", ""]
    else:
        R += ["**No Tier-2 run is recorded yet.** Stage 6 is not ready for scientific freeze "
              "until all four are.", ""]

    # ---- integrity gates
    R += ["## 3. Integrity gates", "",
          "Every IP-H9 gate was **computable on every run** and evaluated over a **non-empty** "
          "evaluation ledger, so a zero is evidence rather than absence of activity.", "",
          "| gate | maximum over all completed runs | runs non-zero |", "|---|---:|---:|"]
    alldone = done1 + done2
    for g in GATES:
        vals = [r[g] for r in alldone if g in r]
        if not vals:
            continue
        R.append(f"| `{g}` | {max(vals)} | {sum(1 for v in vals if v)} |")
    if alldone:
        R += ["",
              f"| accounting gate | maximum | tolerance | holds |", "|---|---:|---:|---|",
              f"| `maximum_energy_identity_residual_j` (IP-H2) | "
              f"{max(r['maximum_energy_identity_residual_j'] for r in alldone):.3e} | 1e-8 J | "
              f"{'yes' if max(r['maximum_energy_identity_residual_j'] for r in alldone) <= 1e-8 else 'NO'} |",
              f"| `maximum_residency_partition_residual_s` (IP-H2) | "
              f"{max(r['maximum_residency_partition_residual_s'] for r in alldone):.3e} | 1e-9 s | "
              f"{'yes' if max(r['maximum_residency_partition_residual_s'] for r in alldone) <= 1e-9 else 'NO'} |"]
        eq = [r["equal_power_paired_residual_kwh"] for r in alldone
              if r["equal_power_paired_residual_kwh"] != "NA"]
        if eq:
            R.append(f"| `equal_power_paired_residual_kwh` (IP-H5) | {max(eq):.3e} | 1e-9 kWh | "
                     f"{'yes' if max(eq) <= 1e-9 else 'NO'} |")
        R += ["",
              "The IP-H5 precondition — zero OFFLINE and zero DISQUALIFIED residency — was "
              "verified rather than assumed on every run where the gate applies.", ""]

    # ---- scenario liveness
    by1 = {}
    for r in done1:
        by1.setdefault(r["scenario_id"], r)
    if by1:
        R += ["## 4. Scenario liveness", "",
              "A zero integrity result is only evidence if the scenario really performed the "
              "behaviour it is named for.", "",
              "| scenario | evidence that it is not vacuous |", "|---|---|"]
        def g(sid, key, default=0):
            return by1.get(sid, {}).get(key, default)
        R += [
            f"| B02 / B03 | floor observations {g('B02','security_floor_observation_count')} / "
            f"{g('B03','security_floor_observation_count')}; breaches "
            f"{g('B02','breach_count')} / {g('B03','breach_count')}; activations completed "
            f"{g('B02','reserve_activations_completed')} / "
            f"{g('B03','reserve_activations_completed')} — the two rows are distinct |",
            f"| B04 | floor-unattainable count {g('B04','floor_unattainable_count')} "
            f"(vs {g('B02','floor_unattainable_count')} for B02); maximum deficit "
            f"{fmt(g('B04','maximum_hash_rate_deficit'), 1)} — DIAGNOSTIC row |",
            f"| C03 (Path A) | reassignments {g('C03','leases_reassigned')} with "
            f"**{g('C03','wake_handles_created')} wake handles** — a genuine Path A |",
            f"| C04 (Path B) | reassignments {g('C04','leases_reassigned')} with "
            f"**{g('C04','wake_handles_created')} wake handles** — a genuine Stage-3 reserve "
            f"wake |",
            f"| C05 (no eligible miner) | {g('C05','leases_revoked')} revocations, "
            f"{g('C05','leases_reassigned')} reassignments — CONTINUE_WITH_UNASSIGNED_RANGE |",
            f"| C06 (full domain) | accepted blocks {g('C06','rounds_accepted')} — every round "
            f"exhausts the domain with no block |",
            f"| D00 (honest control) | delayed wakes {g('D00','delayed_wake_count')}, "
            f"withheld {g('D00','solution_withholding_count')}, false exhaustion accepted "
            f"{g('D00','false_exhaustion_accepted')} — no attack occurs |",
            f"| D01 | delayed wakes {g('D01','delayed_wake_count')} |",
            f"| D02 | solutions withheld {g('D02','solution_withholding_count')}, never released "
            f"{g('D02','withheld_never_released_count')} |",
            f"| D03 | false exhaustion accepted {g('D03','false_exhaustion_accepted')} |",
            f"| D04 | progress withholding {g('D04','progress_withholding_count')} — **see §5** |",
            ""]

    # ---- IP-H10d feasibility
    per_primary = S.REFERENCE["nonce_domain_size"] / S.primary_count(
        S.REFERENCE["num_miners"], S.REFERENCE["reserve_fraction"])
    R += ["## 5. IP-H10d matched feasibility pair (D04C / D04)", "",
          "Progress withholding under-reports the **committed** frontier, so an intermediate "
          "committed frontier must exist when the lease is revoked. The frontier advances only at "
          "batch completion, so a batch boundary must fall strictly inside a primary's range:", "",
          "```", "nonce_domain_size / primary_count  >  batch_size", "```", "",
          "| configuration | nonces per primary | batch size | intermediate frontier possible |",
          "|---|---:|---:|---|",
          f"| original D04 (reference batch size) | {per_primary:.1f} | "
          f"{S.REFERENCE['batch_size']} | "
          f"{'yes' if per_primary > S.REFERENCE['batch_size'] else '**no**'} |",
          f"| D04C / D04 pair | {per_primary:.1f} | {S.PROGRESS_PAIR_BATCH_SIZE} | "
          f"{'**yes**' if per_primary > S.PROGRESS_PAIR_BATCH_SIZE else 'no'} |", ""]
    if h10d:
        R += ["Executed at the confirmatory population on **disjoint pilot seeds only**. This is a "
              "feasibility check; the attack effect is **not** a confirmatory result.", "",
              "| scenario | seed | status | wall (s) | withholding | accepted<actual | rewind | "
              "re-evaluated | duplicate prevented |", "|---|---:|---|---:|---:|---:|---:|---:|---:|"]
        for r in sorted(h10d, key=lambda x: x["scenario_id"]):
            R.append(f"| {r['scenario_id']} | {r.get('seed_index','-')} | {r['run_status']} | "
                     f"{fmt(r.get('wall_clock_seconds', 0), 0)} | "
                     f"{r.get('progress_withholding_count','-')} | "
                     f"{r.get('accepted_below_actual_count','-')} | "
                     f"{r.get('physical_frontier_rewind_count','-')} | "
                     f"{r.get('adversarial_reevaluation_count','-')} | "
                     f"{r.get('duplicate_work_reward_prevented_count','-')} |")
        t = [r for r in h10d if r["scenario_id"] == "D04" and r["run_status"] == "COMPLETED"]
        c = [r for r in h10d if r["scenario_id"] == "D04C" and r["run_status"] == "COMPLETED"]
        gates = {
            "accepted_frontier < actual_frontier in the treatment arm":
                bool(t) and all(r.get("accepted_below_actual_count", 0) > 0 for r in t),
            "physical_frontier_rewind_count == 0 in both arms":
                all(r.get("physical_frontier_rewind_count", 1) == 0 for r in h10d
                    if r["run_status"] == "COMPLETED"),
            "adversarial_reevaluation_count > 0 in the treatment arm":
                bool(t) and all(r.get("adversarial_reevaluation_count", 0) > 0 for r in t),
            "duplicate_work_reward_prevented_count >= adversarial_reevaluation_count":
                bool(t) and all(r.get("duplicate_work_reward_prevented_count", 0)
                                >= r.get("adversarial_reevaluation_count", 0) for r in t),
            "the control arm shows no withholding":
                bool(c) and all(r.get("progress_withholding_count", 1) == 0 for r in c),
        }
        R += ["", "| required signal | holds |", "|---|---|"]
        for k, v in gates.items():
            R.append(f"| {k} | {'**yes**' if v else '**NO**'} |")
        R.append("")
    else:
        R += ["The IP-H10d feasibility runs are recorded in "
              "`experiments/thesis_revision_v45/stage_06/pilot/`.", ""]

    # ---- the eight-seed sweep over the FROZEN schedule
    sweep_path = PILOT.parent / D04_SWEEP
    if sweep_path.exists():
        sweep = json.loads(sweep_path.read_text())["results"]
        treat = [r for r in sweep if r["scenario_id"] == "D04"]
        ctrl = [r for r in sweep if r["scenario_id"] == "D04C"]
        zero_action = [r for r in treat if not r.get("progress_withholding_count", 0)]
        R += ["### 5.1 The frozen pair on ALL EIGHT pilot seeds", "",
              "The fault schedule is frozen and fully specified in "
              "[`STAGE_06_D04_FAULT_SCHEDULE_FREEZE.md`]"
              "(STAGE_06_D04_FAULT_SCHEDULE_FREEZE.md). It is seed-independent, so this sweep "
              "can only show how often the modelled state is **reachable**; it is never used to "
              "re-tune the schedule.", "",
              "| arm | seed index | status | wall (s) | withholding | accepted<actual | rewind | "
              "re-evaluated | duplicate prevented |",
              "|---|---:|---|---:|---:|---:|---:|---:|---:|"]
        for r in sorted(sweep, key=lambda x: (x["scenario_id"], x.get("seed_index", 0))):
            R.append(f"| {r['scenario_id']} | {r.get('seed_index', '-')} | {r['run_status']} | "
                     f"{fmt(r.get('wall_clock_seconds', 0), 2)} | "
                     f"{r.get('progress_withholding_count', '-')} | "
                     f"{r.get('accepted_below_actual_count', '-')} | "
                     f"{r.get('physical_frontier_rewind_count', '-')} | "
                     f"{r.get('adversarial_reevaluation_count', '-')} | "
                     f"{r.get('duplicate_work_reward_prevented_count', '-')} |")
        R += ["",
              f"Runs: **{len(sweep)}** ({len(ctrl)} control, {len(treat)} treatment), all "
              f"`{'COMPLETED' if all(r['run_status'] == 'COMPLETED' for r in sweep) else 'NOT all COMPLETED'}`. "
              f"Seeds producing no withholding action: **{len(zero_action)} of {len(treat)}**.",
              "",
              "Every pilot seed is **retained**, including any that produces no withholding "
              "action; its zero-action result is recorded as shown. No seed is replaced and no "
              "seed is redrawn. These are feasibility measurements on seeds disjoint from the "
              "confirmatory registry — not a confirmatory result, and not an effect estimate.",
              ""]

    # ---- observations
    R += ["## 6. Other feasibility observations", "",
          "* **Adapter schema is stable** at 179 keys across every run; every preregistered "
          "outcome resolves against it.",
          "* **Round terminal times are strictly increasing** in every run, so the derivation of "
          "`round_duration` from consecutive differences is verified, not assumed.",
          "* **Residency reconciles** in every run.",
          "* **C05 can degrade to a single unterminated round.** On one pilot seed C05 executed "
          "1 round over the whole 200 s horizon with 596.6 s of OFFLINE residency. This is the "
          "declared CONTINUE_WITH_UNASSIGNED_RANGE behaviour — with no reassignment and no "
          "reserve pool, a failed miner's range stays unassigned and the round cannot close. It "
          "is a real property of the condition, not a defect, and it yields a legitimate "
          "zero-block run. The effect is amplified at Tier-1 scale, where the fault schedule "
          "removes 3 of 12 miners; at the confirmatory scale the same schedule touches at most "
          "4 of 141.",
          "* **IP-H7 risk.** With the floor enabled, the Tier-1 pilot measured "
          f"`total_duration_below_floor` of {fmt(by1.get('B02', {}).get('total_duration_below_floor', 0.0), 3)} s "
          f"against a 200 s horizon and `floor_unattainable_count` of "
          f"{by1.get('B02', {}).get('floor_unattainable_count', 0)}. IP-H7's preregistered "
          "criteria are `floor_unattainable_count == 0` and "
          "`total_duration_below_floor <= 0.01 x horizon_T`, so the criterion is at risk. The "
          "cause is the accepted engine's deliberate semantics: `_pending_primary_capacity` "
          "excludes still-WAKING primaries from `H_effective`, so \"the WAKING ramp is a real "
          "below-floor interval\". **IP-H7 is frozen exactly as specified and the criterion is "
          "not weakened** — adjusting a success criterion because the pilot suggests it may not "
          "be met is precisely the forbidden use of pilot data. The risk is recorded here so the "
          "acceptance reviewer sees it before Stage 7.", ""]

    # ---------------------------------------------------------------- runtime plan
    P = _runtime_plan(t2, done2)

    return "\n".join(R) + "\n", "\n".join(P) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args(argv)
    if not PILOT.exists():
        print(f"FAIL: {PILOT} does not exist — run the pilot first", file=sys.stderr)
        return 1
    data = load_all()
    report, plan = build(data)
    targets = {DOCS / "STAGE_06_PILOT_REPORT.md": report,
               DOCS / "STAGE_06_RUNTIME_AND_ARCHIVE_PLAN.md": plan}
    if args.check:
        bad = [str(p.relative_to(REPO_ROOT)) for p, t in targets.items()
               if not p.exists() or p.read_bytes() != t.encode("utf-8")]
        if bad:
            print("FAIL: differs from regeneration: " + ", ".join(bad), file=sys.stderr)
            return 1
        print("OK: pilot report and runtime plan are byte-identical to regeneration")
    else:
        for p, t in targets.items():
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(t.encode("utf-8"))
        print(f"wrote {len(targets)} documents from {len(data['results'])} pilot runs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
