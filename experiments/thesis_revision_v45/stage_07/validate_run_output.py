#!/usr/bin/env python3
"""Stage 7 — validate one run output against the frozen outcome dictionary.

A run is only inferentially usable if every PREREGISTERED outcome resolves in its payload and
its identity matches the frozen registry.  NA is a legitimate value and is preserved; it is
never imputed as zero.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

from _common import frozen_rows                                       # noqa: E402


def required_outcomes() -> set:
    import generate_confirmatory_matrix as GCM                        # noqa: PLC0415
    names = set()
    for m in (GCM.PRIMARY_OUTCOMES, GCM.SECONDARY_OUTCOMES):
        for v in m.values():
            names |= {x for x in v.split(";") if x and x != "NONE"}
    return names


#: Outcomes computed by the analysis from accepted adapter fields rather than read directly.
DERIVED = {"total_energy_kwh": "energy_kwh", "accepted_blocks": "rounds_accepted",
           "accepted_blocks_per_horizon": "rounds_accepted",
           "zero_block_indicator": "rounds_accepted", "zero_block_rate": "rounds_accepted",
           "relative_energy_reduction_percent": "energy_kwh",
           "round_duration": None, "median_round_duration": None,
           "maximum_hash_rate_deficit_when_floor_disabled": "maximum_hash_rate_deficit"}


def validate(path: pathlib.Path) -> dict:
    problems = []
    try:
        p = json.loads(path.read_text())
    except Exception as exc:
        return {"ok": False, "problems": [f"unreadable: {exc}"]}
    for k in ("run_id", "scenario_id", "master_seed", "pair_id", "config_sha256", "results"):
        if k not in p:
            problems.append(f"missing top-level field {k!r}")
    if problems:
        return {"ok": False, "problems": problems}
    ids = {r["run_id"]: r for r in frozen_rows()}
    row = ids.get(p["run_id"])
    if row is None:
        problems.append(f"{p['run_id']} is not a frozen run identity")
    else:
        if str(row["master_seed"]) != str(p["master_seed"]):
            problems.append("master_seed does not match the frozen registry")
        if row["pair_id"] != p["pair_id"]:
            problems.append("pair_id does not match the frozen registry")
    res = p["results"]
    for name in sorted(required_outcomes()):
        src = DERIVED.get(name, name)
        if src is None:
            continue
        if src not in res:
            problems.append(f"preregistered outcome {name!r} does not resolve (needs {src!r})")
    na = sorted(k for k, v in res.items() if v is None or v == "NA")
    return {"ok": not problems, "problems": problems, "run_id": p["run_id"],
            "na_fields": na, "na_count": len(na),
            "zero_block_indicator": int(res.get("rounds_accepted", -1) == 0)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("paths", nargs="+")
    args = ap.parse_args(argv)
    bad = 0
    for s in args.paths:
        r = validate(pathlib.Path(s))
        print(f"  {'OK  ' if r['ok'] else 'FAIL'} {s}  NA={r.get('na_count','-')}"
              + ("" if r["ok"] else "  " + "; ".join(r["problems"][:3])))
        bad += 0 if r["ok"] else 1
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
