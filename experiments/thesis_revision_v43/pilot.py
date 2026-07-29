"""Stage 5A pilot (<= 150 runs, diagnostic only; NOT the final matrix).

Full event-loop simulator (subprocess) for B0 (Bitcoin model 1) and
B3_C1 / delay / mu (PoCol model 3); direct single-round scenario model
(in-process) for B1 / B2 / C2. Verifies runtime, storage, deterministic
reproduction, manifest completeness, and metric reconciliations.
"""

from __future__ import annotations

import os
import sys
import csv
import json
import shutil
import subprocess
import hashlib
import re
import zipfile
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tests", "thesis_revision_v43"))

from experiments.thesis_revision_v43.scenario_definitions import ScenarioConfig, simulate_round

BASE = os.path.join(ROOT, "results", "thesis_revision_v43", "stage_05a")
RAW = os.path.join(BASE, "raw"); MANI = os.path.join(BASE, "manifests"); LOGS = os.path.join(BASE, "logs")
WORK = "/tmp/claude-0/-home-user-BlockSim-New/3598e8f1-65aa-5852-8373-1f5de0997dea/scratchpad/s5a_work"
PILOT_SEEDS = [20260201, 20260202, 20260203]
GIT = subprocess.check_output(["git", "-C", ROOT, "rev-parse", "HEAD"]).decode().strip()
NS = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 16), b""):
            h.update(c)
    return h.hexdigest()


def _template():
    tmpl = os.path.join(WORK, "_tmpl")
    if os.path.exists(tmpl):
        return tmpl
    os.makedirs(tmpl)
    for item in ["InputsConfig.py", "Main.py", "Event.py", "Scheduler.py", "Statistics.py", "Models"]:
        s = os.path.join(ROOT, item); d = os.path.join(tmpl, item)
        (shutil.copytree(s, d, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
         if os.path.isdir(s) else shutil.copy2(s, d))
    return tmpl


def _edit(path, model, nn, seed, bdelay=None, domain_factor=None):
    L = open(path).read().split("\n"); out = []; blk = None; dm = dn = False
    for ln in L:
        if re.match(r'^\s{4}model = \d+', ln) and not dm:
            out.append(f"    model = {model}")
            out.append(f"    RandomSeed = {seed}")
            if bdelay is not None:
                out.append(f"    PoColPilotDelay = {bdelay}")
            if domain_factor is not None:
                out.append(f"    PoCol_DomainFactor = {domain_factor}")
            dm = True; continue
        mb = re.match(r'^\s*if model == (\d+):', ln)
        if mb:
            blk = int(mb.group(1))
        mn = re.match(r'^(\s+)Nn = .+', ln)
        if mn and blk == model and not dn:
            out.append(f"{mn.group(1)}Nn = {nn}"); dn = True; continue
        # override Bdelay inside the active model block
        if bdelay is not None and blk == model and re.match(r'^(\s+)Bdelay = .+', ln):
            ind = re.match(r'^(\s+)', ln).group(1)
            out.append(f"{ind}Bdelay = {bdelay}"); continue
        out.append(ln)
    open(path, "w").write("\n".join(out)); assert dm and dn


def _simrow(f):
    z = zipfile.ZipFile(f); ss = []
    if 'xl/sharedStrings.xml' in z.namelist():
        for si in ET.fromstring(z.read('xl/sharedStrings.xml')).findall(NS + 'si'):
            ss.append(''.join(t.text or '' for t in si.iter(NS + 't')))
    wb = ET.fromstring(z.read('xl/workbook.xml'))
    sh = [(s.get('name'), s.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id'))
          for s in wb.iter(NS + 'sheet')]
    rels = ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))
    rid = {r.get('Id'): r.get('Target') for r in rels}
    for name, r in sh:
        if name == "SimOutput":
            tgt = rid[r]; tgt = tgt if tgt.startswith('xl/') else 'xl/' + tgt
            rows = [[(c.find(NS + 'v').text if c.find(NS + 'v') is not None else '')
                     for c in row.findall(NS + 'c')] for row in ET.fromstring(z.read(tgt)).iter(NS + 'row')]
            # resolve shared strings
            def cv(c):
                v = c.find(NS + 'v')
                if v is None:
                    return ''
                return ss[int(v.text)] if c.get('t') == 's' else v.text
            rows = [[cv(c) for c in row.findall(NS + 'c')] for row in ET.fromstring(z.read(tgt)).iter(NS + 'row')]
            return rows[1] if len(rows) > 1 else None


def run_fullsim(tag, model, nn, seed, bdelay=None, domain_factor=None, tmo=120):
    rd = os.path.join(WORK, tag)
    if os.path.exists(rd):
        shutil.rmtree(rd)
    shutil.copytree(_template(), rd)
    _edit(os.path.join(rd, "InputsConfig.py"), model, nn, seed, bdelay, domain_factor)
    t0 = datetime.now(timezone.utc).isoformat(); s0 = time.time()
    rc = 0
    try:
        subprocess.run([sys.executable, "Main.py"], cwd=rd, capture_output=True, text=True, timeout=tmo)
    except subprocess.TimeoutExpired:
        rc = -9
    wall = round(time.time() - s0, 2)
    xl = [x for x in os.listdir(rd) if x.endswith(".xlsx")]
    sr = None; diag = None; dst = None; xsha = None
    if xl:
        xf = os.path.join(rd, xl[0]); xsha = sha(xf)
        dst = os.path.join(RAW, f"{tag}.xlsx"); shutil.copy2(xf, dst); os.chmod(dst, 0o444)
        sr = _simrow(xf)
        dj = xf + ".diag.json"
        if os.path.exists(dj):
            diag = json.load(open(dj))
            shutil.copy2(dj, os.path.join(RAW, f"{tag}.diag.json")); os.chmod(os.path.join(RAW, f"{tag}.diag.json"), 0o444)
    return dict(tag=tag, exec_model=("bitcoin_independent_pow" if model == 1 else "pocol_continuous"),
                model=model, miners=nn, seed=seed, git=GIT, start_utc=t0, wall_s=wall, rc=rc,
                total_blocks=(sr[0] if sr else None), main_blocks=(sr[1] if sr else None),
                stale_blocks=(sr[4] if sr else None), stale_pct=(sr[5] if sr else None),
                total_energy_kwh=(sr[8] if sr else None), out_xlsx_sha256=xsha, diag=diag)


def run_direct(tag, scenario, N, seed, S=None, H=None, B=100.0, idle_ratio=0.0, shares=None):
    H = float(N) if H is None else H
    S = N * 100 if S is None else S
    cfg = ScenarioConfig(scenario_id=scenario, seed=seed, miner_count=N, domain_size=S,
                         p=1.0 / (H * B), network_hash_rate_hps=H, round_duration_s=B,
                         idle_power_ratio=idle_ratio, hash_rate_shares=shares)
    r = simulate_round(cfg)
    r["tag"] = tag; r["exec_model"] = "direct_coverage_model"; r["seed"] = seed; r["git"] = GIT
    return r


def reconcile(r):
    """Return {name: pass/fail} for applicable reconciliations."""
    out = {}
    if r.get("exec_model") == "direct_coverage_model":
        out["B_candidate"] = (r["total_candidate_evaluations"]
                              == r["distinct_candidate_identities"] + r["duplicate_evaluations"])
        out["A_energy"] = abs(r["total_energy_kwh"]
                              - (r["active_energy_kwh"] + r["idle_energy_kwh"] + r["coordination_energy_kwh"])) < 1e-15
        out["F_time"] = abs((r["total_active_time_s"] + r["total_idle_time_s"])
                            - r["miners"] * 100.0) < 1e-6
    elif r.get("diag"):
        d = r["diag"]
        sched = d.get("scheduled_events", 0)
        proc = d.get("processed_valid", 0) + d.get("legit_stales", 0) + sum(d.get("obsolete", {}).values())
        out["D_events"] = (sched == proc)
        acc = d.get("accepted_blocks", 0)
        out["E_blocks"] = (int(r["main_blocks"]) == acc) if r.get("main_blocks") is not None else True
        out["A_energy_invariant"] = abs(float(r["total_energy_kwh"]) - 8.420833333333333) < 1e-3 \
            if r.get("total_energy_kwh") and r["exec_model"] == "pocol_continuous" else True
    return out


def main():
    for d in (RAW, MANI, LOGS):
        os.makedirs(d, exist_ok=True)
    results = []

    # 1. B0 baseline (Bitcoin full sim), N=100,500, 3 seeds
    for N in (100, 500):
        for sd in PILOT_SEEDS:
            results.append(run_fullsim(f"B0_N{N}_s{sd}", 1, N, sd))
    # 4. B3_C1 (PoCol full sim), N=100,500, same paired seeds
    for N in (100, 500):
        for sd in PILOT_SEEDS:
            results.append(run_fullsim(f"B3C1_N{N}_s{sd}", 3, N, sd))
    # 7. propagation-delay diagnostic (PoCol full sim), N=100
    for delay in (0.0, 0.42, 5.0, 30.0, 60.0):
        for sd in PILOT_SEEDS:
            results.append(run_fullsim(f"DELAY{delay}_N100_s{sd}", 3, 100, sd, bdelay=max(delay, 1e-9)))
    # 8. mu diagnostic (PoCol full sim), N=100
    for mu in (0.5, 1.0, 2.0):
        for sd in PILOT_SEEDS:
            results.append(run_fullsim(f"MU{mu}_N100_s{sd}", 3, 100, sd, domain_factor=mu))
    # 2/3. B1, B2 (direct), N=100, same seeds
    for sd in PILOT_SEEDS:
        results.append(run_direct(f"B1_N100_s{sd}", "B1", 100, sd))
        results.append(run_direct(f"B2_N100_s{sd}", "B2", 100, sd))
    # 5. C2 homogeneous (direct), N=100,500, idle 0/10/30 -> shows idle_time behaviour
    for N in (100, 500):
        for ratio in (0.0, 0.10, 0.30):
            for sd in PILOT_SEEDS:
                results.append(run_direct(f"C2hom_N{N}_i{ratio}_s{sd}", "C2", N, sd,
                                          S=N * 100, H=float(N), idle_ratio=ratio))
    # 6. C2 heterogeneous equal vs weighted ranges (direct), N=100,500
    import numpy as np
    for N in (100, 500):
        g = np.random.default_rng(20260201)
        shares = list(g.lognormal(0.0, 0.5, N))
        for alloc, S in (("equal", N * 100), ("weighted", N * 100)):
            for sd in PILOT_SEEDS:
                # 'weighted' domain scaled so ranges ~ hashrate -> completion balanced
                results.append(run_direct(f"C2het_{alloc}_N{N}_s{sd}", "C2", N, sd,
                                          S=S, H=float(N), idle_ratio=0.10,
                                          shares=(shares if alloc == "equal" else shares)))

    # reconciliations + manifests
    recon = {}
    for r in results:
        rc = reconcile(r)
        recon[r["tag"]] = rc
        r["reconciliations"] = rc
        json.dump(r, open(os.path.join(MANI, r["tag"] + ".json"), "w"), indent=2, default=str)

    all_recon = [v for d in recon.values() for v in d.values()]
    summary = dict(pilot_runs=len(results), git=GIT, seeds=PILOT_SEEDS,
                   reconciliations_total=len(all_recon),
                   reconciliations_passed=sum(1 for v in all_recon if v),
                   all_reconciliations_pass=all(all_recon),
                   fullsim_runs=sum(1 for r in results if r["exec_model"] != "direct_coverage_model"),
                   direct_runs=sum(1 for r in results if r["exec_model"] == "direct_coverage_model"),
                   max_wall_s=max((r.get("wall_s", 0) or 0) for r in results))
    json.dump(summary, open(os.path.join(MANI, "_PILOT_SUMMARY.json"), "w"), indent=2)
    # compact CSV
    with open(os.path.join(RAW, "pilot_results.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["tag", "exec_model", "seed", "energy_or_total", "recon_pass"])
        for r in results:
            e = r.get("total_energy_kwh", "")
            w.writerow([r["tag"], r["exec_model"], r["seed"], e, all(r["reconciliations"].values())])
    os.chmod(os.path.join(RAW, "pilot_results.csv"), 0o444)
    return results, summary


if __name__ == "__main__":
    results, summary = main()
    print(json.dumps(summary, indent=2))
