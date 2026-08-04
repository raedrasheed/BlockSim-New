#!/usr/bin/env python3
"""Stage 6 — external resource sampler for an ALREADY-RUNNING pilot process.

Reads ``/proc/<pid>/stat`` and ``/proc/<pid>/status`` at a fixed interval and keeps the latest
sample on disk, so a process that was launched before a measurement was required can still have
that measurement recorded truthfully rather than estimated.

It writes a sidecar file next to the run's checkpoint; it NEVER edits the checkpoint the pilot
harness produces, so the harness output stays exactly as the harness wrote it.

    python sample_run_resources.py --pid 12496 --scenario B02 \
        --out experiments/thesis_revision_v45/stage_06/pilot/tier2/B02.resources.json

Recorded per sample:
    utime_s, stime_s   user / system CPU seconds  (/proc/<pid>/stat fields 14, 15 / clock ticks)
    cpu_seconds        utime_s + stime_s
    vm_hwm_kb          peak resident set size high-water mark (/proc/<pid>/status VmHWM)
    vm_rss_kb          current resident set size
    wall_seconds       seconds since the process started, from field 22 and /proc/uptime

This is a FEASIBILITY measurement (runtime and memory).  It records no scientific quantity.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import time

CLK_TCK = os.sysconf("SC_CLK_TCK")


def read_proc(pid: int) -> dict:
    stat = pathlib.Path(f"/proc/{pid}/stat").read_text()
    # comm may contain spaces/parens: everything after the final ')' is field 3 onwards
    tail = stat[stat.rfind(")") + 2:].split()
    utime, stime, starttime = int(tail[11]), int(tail[12]), int(tail[19])
    uptime = float(pathlib.Path("/proc/uptime").read_text().split()[0])
    out = {"utime_s": utime / CLK_TCK, "stime_s": stime / CLK_TCK,
           "cpu_seconds": (utime + stime) / CLK_TCK,
           "wall_seconds": uptime - starttime / CLK_TCK}
    for line in pathlib.Path(f"/proc/{pid}/status").read_text().splitlines():
        if line.startswith("VmHWM:"):
            out["vm_hwm_kb"] = int(line.split()[1])
        elif line.startswith("VmRSS:"):
            out["vm_rss_kb"] = int(line.split()[1])
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pid", type=int, required=True)
    ap.add_argument("--scenario", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--interval", type=float, default=30.0)
    args = ap.parse_args(argv)

    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    n, last = 0, None
    while True:
        try:
            s = read_proc(args.pid)
        except (FileNotFoundError, ProcessLookupError, IndexError):
            break                      # the process exited; `last` is the final observation
        n += 1
        last = s
        out.write_text(json.dumps(
            {"source": "external /proc sampler (sample_run_resources.py)",
             "purpose": "FEASIBILITY ONLY — runtime and memory; no scientific quantity",
             "note": ("the pilot process was launched before CPU time was a required field, so "
                      "CPU time is measured externally from /proc rather than estimated; the "
                      "harness checkpoint is never modified"),
             "scenario_id": args.scenario, "pid": args.pid,
             "samples_taken": n, "sample_interval_s": args.interval,
             "final_sample": last}, indent=1, sort_keys=True) + "\n")
        time.sleep(args.interval)

    print(f"{args.scenario}: pid {args.pid} exited after {n} samples; "
          f"cpu={last['cpu_seconds']:.1f}s wall={last['wall_seconds']:.1f}s "
          f"hwm={last.get('vm_hwm_kb', 0) / 1024:.0f}MB" if last else "no sample taken",
          flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
