#!/usr/bin/env python3
"""Stage 7 — resource preflight.  Execution is refused unless this returns PASS.

THE MEMORY EQUATION (the single authority on concurrency):

    required_RAM = 1.25 * (
          n_lightweight     * peak_RAM_lightweight
        + n_security_floor  * peak_RAM_security_floor
        + n_reassignment    * peak_RAM_reassignment
        + n_compressors     * peak_RAM_compressor )

Core count is an upper bound on the worker set, never a declaration of capacity.

    python resource_preflight.py --record host.json          # evaluate a filled host record
    python resource_preflight.py --template out.json         # emit the blank template
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time

from _common import HERE, REPO_ROOT                                  # noqa: E402

RAM_SAFETY_MARGIN = 1.25

#: Per-worker peak RAM, in MB.  LIGHTWEIGHT and REASSIGNMENT are MEASURED at full scale in the
#: Stage-6 Tier-2 pilot.  SECURITY_FLOOR is ESTIMATED from the right-censored B02 record and is
#: labelled as such everywhere it is used.
PEAK_RAM_MB = {
    "LIGHTWEIGHT": 3010.0,          # MEASURED (A03, A05)
    "REASSIGNMENT": 5266.0,         # MEASURED (C04)
    "SECURITY_FLOOR": 4396.6,       # ESTIMATED from censored B02 (2550 MB at 58.0 % of horizon)
    "COMPRESSOR": 706.8,            # MEASURED xz -9 fixed encoder cost, per compressing process
}
PEAK_RAM_BASIS = {
    "LIGHTWEIGHT": "MEASURED", "REASSIGNMENT": "MEASURED",
    "SECURITY_FLOOR": "ESTIMATED (right-censored B02)", "COMPRESSOR": "MEASURED",
}
#: Per-run wall clock, seconds.  Same measured/estimated split.
WALL_SECONDS = {"LIGHTWEIGHT": 9914.3, "REASSIGNMENT": 15735.8, "SECURITY_FLOOR": 66850.0}

REQUIRED_FIELDS = [
    "host_identifier", "provider_or_institution", "persistent_lifetime_guarantee",
    "cpu_count", "usable_ram_bytes", "free_disk_bytes", "durable_output_path",
    "archive_path", "worker_limits_by_class", "compressor_count", "per_run_timeout",
    "heartbeat_interval", "checkpoint_interval", "same_seed_rerun_policy",
    "verified_at", "verdict",
]

TEMPLATE = {
    "host_identifier": None,
    "provider_or_institution": None,
    "persistent_lifetime_guarantee": {"days": None, "evidence": None},
    "cpu_count": None,
    "usable_ram_bytes": None,
    "free_disk_bytes": None,
    "durable_output_path": None,
    "archive_path": None,
    "worker_limits_by_class": {"LIGHTWEIGHT": None, "SECURITY_FLOOR": None,
                               "REASSIGNMENT": None},
    "compressor_count": None,
    "per_run_timeout": {"hours": 24},
    "heartbeat_interval": {"seconds": 30},
    "checkpoint_interval": {"policy": "after every completed run"},
    "same_seed_rerun_policy": ("retry the identical (scenario_id, master_seed) pair with the "
                               "identical frozen configuration; NEVER draw a replacement seed"),
    "verified_at": None,
    "verdict": "NOT_EVALUATED",
    "_instructions": ("Fill every field from DIRECT OBSERVATION of the host. A field filled "
                      "from a quotation, a marketing figure or an intention to provision is a "
                      "preflight failure. Then run: python resource_preflight.py "
                      "--record <this file>"),
}


def required_ram_bytes(limits: dict, compressors: int) -> float:
    """The memory equation.  Returns bytes."""
    total_mb = sum(int(limits.get(c, 0)) * PEAK_RAM_MB[c]
                   for c in ("LIGHTWEIGHT", "SECURITY_FLOOR", "REASSIGNMENT"))
    total_mb += int(compressors) * PEAK_RAM_MB["COMPRESSOR"]
    return RAM_SAFETY_MARGIN * total_mb * 1024 * 1024


def projected_duration_days(limits: dict) -> float:
    """Resource-aware duration under the given worker limits, per cost class."""
    import csv as _csv
    sys.path.insert(0, str(HERE))
    from _common import frozen_rows, cost_class                      # noqa: PLC0415
    import scenarios as S                                            # noqa: PLC0415
    srows = {r["scenario_id"]: r for r in S.confirmatory_rows()}
    from _common import build_physical_map, executor_run_id                # noqa: PLC0415
    m = build_physical_map()
    counts = {}
    for _pid, members in m["physical"].items():
        ex = executor_run_id(members)
        c = cost_class(srows[m["logical"][ex]["scenario_id"]])
        counts[c] = counts.get(c, 0) + 1
    # counts are PHYSICAL executions (630), not logical rows (660)
    worst = 0.0
    for c, n in counts.items():
        k = max(1, int(limits.get(c, 1)))
        worst = max(worst, n * WALL_SECONDS[c] / k)
    # heavy classes share the machine serially in the conservative default, so sum them
    heavy = sum(counts.get(c, 0) * WALL_SECONDS[c] / max(1, int(limits.get(c, 1)))
                for c in ("SECURITY_FLOOR", "REASSIGNMENT"))
    return max(worst, heavy) / 86400.0


def verify_filesystem(rec: dict) -> list:
    """S7A-2: verify the DECLARED PATHS on the real filesystem, not the typed numbers.

    A record whose paths cannot be created, written, atomically replaced or checksummed is
    rejected however plausible its JSON looks.
    """
    import hashlib as _h, lzma as _l, os as _os, shutil as _sh, tempfile as _tf
    checks = []
    for label, key in (("durable_output_path", "durable_output_path"),
                       ("archive_path", "archive_path")):
        raw = rec.get(key)
        if not raw:
            checks.append({"id": f"V2a_{label}_declared", "pass": False,
                           "detail": "not declared"})
            continue
        d = pathlib.Path(raw)
        try:
            d.mkdir(parents=True, exist_ok=True)
            probe = d / ".stage7_write_probe"
            probe.write_bytes(b"probe")
            probe.unlink()
            ok, detail = True, f"{d} exists and is writable"
        except Exception as exc:
            ok, detail = False, f"{d}: {exc}"
        checks.append({"id": f"V2a_{label}_writable", "pass": ok, "detail": detail})
        if ok:
            free = _sh.disk_usage(str(d)).free
            checks.append({"id": f"V2b_{label}_free_space", "pass": bool(free >= 2 * 1024**3),
                           "measured_free_bytes": free,
                           "detail": f"{free / 2**30:.2f} GiB measured AT THE PATH"})

    root = rec.get("durable_output_path")
    if root and pathlib.Path(root).is_dir():
        d = pathlib.Path(root)
        try:                                   # atomic os.replace on the registry filesystem
            fd, tmp = _tf.mkstemp(dir=str(d), prefix=".atomic-probe-")
            with _os.fdopen(fd, "w") as fh:
                fh.write("x")
            target = d / ".atomic-probe-target"
            _os.replace(tmp, target)
            ok = target.read_text() == "x"
            target.unlink()
            checks.append({"id": "V2c_atomic_replace", "pass": ok,
                           "detail": "os.replace works on the registry filesystem"})
        except Exception as exc:
            checks.append({"id": "V2c_atomic_replace", "pass": False, "detail": str(exc)})

    arch = rec.get("archive_path")
    if arch and pathlib.Path(arch).is_dir():
        try:                                   # checksum round-trip on the archive filesystem
            d = pathlib.Path(arch)
            payload = b"stage7 archive round-trip probe" * 64
            blob = d / ".xz-probe.xz"
            blob.write_bytes(_l.compress(payload, preset=1))
            ok = _h.sha256(_l.decompress(blob.read_bytes())).hexdigest() == \
                _h.sha256(payload).hexdigest()
            blob.unlink()
            checks.append({"id": "V2d_archive_roundtrip", "pass": ok,
                           "detail": "compress + decompress + digest verified at archive_path"})
        except Exception as exc:
            checks.append({"id": "V2d_archive_roundtrip", "pass": False, "detail": str(exc)})
    return checks


def evaluate(rec: dict, check_filesystem: bool = True) -> dict:
    missing = [f for f in REQUIRED_FIELDS if f not in rec or rec[f] in (None, "", {})]
    unfilled = [f for f in REQUIRED_FIELDS
                if isinstance(rec.get(f), dict)
                and any(v is None for v in rec[f].values())]
    limits = rec.get("worker_limits_by_class") or {}
    comp = rec.get("compressor_count") or 0
    checks = []
    if missing or unfilled:
        checks.append({"id": "V0_record_complete", "pass": False,
                       "detail": f"unfilled fields: {sorted(set(missing + unfilled))}"})
        return {"verdict": "FAIL", "checks": checks,
                "binding_failure": "V0_record_complete"}
    checks.append({"id": "V0_record_complete", "pass": True, "detail": "all fields filled"})

    need = required_ram_bytes(limits, comp)
    have = float(rec["usable_ram_bytes"])
    checks.append({"id": "V1_memory", "pass": bool(need <= have),
                   "required_bytes": need, "available_bytes": have,
                   "equation": f"1.25 * (sum n_c * peak_c + {comp} * compressor)",
                   "detail": f"{need/2**30:.2f} GiB required, {have/2**30:.2f} GiB usable"})

    total_workers = sum(int(limits.get(c, 0)) for c in limits) + int(comp)
    checks.append({"id": "V1b_cores", "pass": bool(total_workers <= int(rec["cpu_count"])),
                   "detail": f"{total_workers} processes vs {rec['cpu_count']} cores"})

    disk_need = 2 * 1024**3            # compress-on-write peak working set, conservative
    checks.append({"id": "V2_disk", "pass": bool(float(rec["free_disk_bytes"]) >= disk_need),
                   "required_bytes": disk_need, "available_bytes": float(rec["free_disk_bytes"]),
                   "detail": "compress-on-write path; raw-first would need ~16.3 GB"})

    if check_filesystem:
        checks.extend(verify_filesystem(rec))

    days = projected_duration_days(limits)
    guarantee = float(rec["persistent_lifetime_guarantee"]["days"])
    checks.append({"id": "V3_lifetime", "pass": bool(guarantee >= RAM_SAFETY_MARGIN * days),
                   "required_days": RAM_SAFETY_MARGIN * days, "guaranteed_days": guarantee,
                   "projected_duration_days": days,
                   "detail": "lifetime >= 1.25 x resource-aware duration"})

    failed = [c["id"] for c in checks if not c["pass"]]
    return {"verdict": "PASS" if not failed else "FAIL", "checks": checks,
            "binding_failure": failed[0] if failed else None,
            "projected_duration_days": days}


def gate_or_die(record_path: pathlib.Path) -> dict:
    """Called by the scheduler before the FIRST confirmatory run.  Refuses on anything but PASS."""
    if not record_path.exists():
        raise SystemExit(f"STAGE_7_REFUSED: no preflight record at {record_path}. "
                         "Fill the template and re-run resource_preflight.py.")
    rec = json.loads(record_path.read_text())
    res = evaluate(rec)
    if res["verdict"] != "PASS" or rec.get("verdict") != "PASS":
        # a numerically-plausible record whose paths do not work is still a refusal
        raise SystemExit(
            f"STAGE_7_REFUSED: preflight verdict is {res['verdict']} "
            f"(binding failure: {res['binding_failure']}). No confirmatory run may begin.")
    return res


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--record")
    ap.add_argument("--template")
    args = ap.parse_args(argv)
    if args.template:
        pathlib.Path(args.template).write_text(json.dumps(TEMPLATE, indent=1) + "\n")
        print(f"wrote blank template {args.template}")
        return 0
    if not args.record:
        ap.error("one of --record or --template is required")
    rec = json.loads(pathlib.Path(args.record).read_text())
    res = evaluate(rec)
    for c in res["checks"]:
        print(f"  {'PASS' if c['pass'] else 'FAIL'}  {c['id']:20s} {c.get('detail','')}")
    print(f"\nVERDICT: {res['verdict']}"
          + (f"  (binding failure: {res['binding_failure']})" if res["binding_failure"] else ""))
    rec["verdict"] = res["verdict"]
    rec["verified_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    rec["evaluation"] = res
    pathlib.Path(args.record).write_text(json.dumps(rec, indent=1, default=str) + "\n")
    return 0 if res["verdict"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
