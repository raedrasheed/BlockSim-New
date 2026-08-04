#!/usr/bin/env python3
"""Stage 7 — shared bundle primitives: paths, run identity, atomic registry, statuses.

Every module in the deployment bundle imports from here so that run identity, the status
lifecycle and the durable registry have exactly one implementation.
"""
from __future__ import annotations

import csv
import fcntl
import hashlib
import io
import json
import os
import pathlib
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
STAGE6 = REPO_ROOT / "experiments" / "thesis_revision_v45" / "stage_06"
for p in (str(REPO_ROOT), str(STAGE6), str(HERE)):
    if p not in sys.path:
        sys.path.insert(0, p)

#: The FROZEN 660-run registry produced by Stage 6.  Run identities are never regenerated.
FROZEN_REGISTRY = STAGE6 / "confirmatory" / "confirmatory_run_registry.csv"
FROZEN_CONFIGS = STAGE6 / "confirmatory" / "frozen_configs"
BASELINE_COMMIT = "026483496ffb434243f45e174c63b43b77b3b43a"

#: Fallback root, used ONLY when no host record is supplied (dry-runs and tests).  Real
#: execution resolves every path from the VERIFIED host record — see ExecutionPaths.
DEFAULT_DATA = REPO_ROOT / "data" / "thesis_revision_v45" / "stage_07"


class ExecutionPaths:
    """Every Stage-7 path, derived from the verified host record's durable locations.

    Nothing is hard-coded to the repository. `durable_output_path` and `archive_path` come
    from the host record, are checked by the preflight against the real filesystem, and are
    threaded through every tool so the scheduler, the worker, the archiver, the dataset
    builder and the verifier all agree on one layout.
    """

    def __init__(self, durable_output_path=None, archive_path=None):
        self.root = pathlib.Path(durable_output_path or DEFAULT_DATA)
        self.archive = pathlib.Path(archive_path) if archive_path else (self.root / "archive")
        self.registry = self.root / "run_registry.csv"
        self.physical_registry = self.root / "physical_execution_registry.csv"
        self.alias_map = self.root / "logical_to_physical_alias.csv"
        self.raw = self.root / "raw"
        self.logs = self.root / "logs"
        self.failed_attempts = self.root / "failed_attempts"
        self.chunks = self.root / "chunks"
        self.manifests = self.root / "manifests"
        self.run_level = self.root / "run_level"

    @classmethod
    def from_record(cls, record: dict):
        return cls(record.get("durable_output_path"), record.get("archive_path"))

    @classmethod
    def from_record_file(cls, path):
        return cls.from_record(json.loads(pathlib.Path(path).read_text()))

    def mkdirs(self):
        for d in (self.root, self.archive, self.raw, self.logs, self.failed_attempts,
                  self.chunks, self.manifests, self.run_level):
            d.mkdir(parents=True, exist_ok=True)
        return self

    def as_dict(self):
        return {k: str(v) for k, v in sorted(vars(self).items())}


#: Default instance for dry-runs and tests only.
PATHS = ExecutionPaths()

#: The complete status lifecycle.  A run is always in exactly one of these.
PENDING = "PENDING"
RUNNING = "RUNNING"
COMPLETED = "COMPLETED"
FAILED_INFRASTRUCTURE = "FAILED_INFRASTRUCTURE"
FAILED_MODEL = "FAILED_MODEL"
RERUN_COMPLETED = "RERUN_COMPLETED"
STATUSES = (PENDING, RUNNING, COMPLETED, FAILED_INFRASTRUCTURE, FAILED_MODEL, RERUN_COMPLETED)
#: Statuses that mean "this run has produced its inferential record; never execute it again".
TERMINAL_SUCCESS = (COMPLETED, RERUN_COMPLETED)
#: Statuses eligible for resume.  FAILED_MODEL is NOT resumable: it stops the frozen execution.
RESUMABLE = (PENDING, FAILED_INFRASTRUCTURE, RUNNING)

REGISTRY_FIELDS = [
    "run_id", "scenario_id", "block_id", "master_seed", "seed_index", "pair_id",
    "cost_class", "config_sha256", "engine_commit_sha", "attempt",
    "start_timestamp", "end_timestamp", "wall_clock_seconds", "run_status",
    "physical_execution_id", "shared_physical_execution", "alias_group_id",
    "materialised_from_run_id", "raw_reclaimed", "raw_sha256",
    "compressed_file", "compressed_sha256", "archive_verified",
    "execution_log", "exception_type", "exception_detail",
]


def sha256_file(p: pathlib.Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def config_sha256(cfg) -> str:
    return hashlib.sha256(json.dumps(
        {k: str(v) for k, v in sorted(vars(cfg).items())}, sort_keys=True).encode()).hexdigest()


def frozen_rows() -> list:
    """The 660 frozen run identities, exactly as Stage 6 produced them."""
    return list(csv.DictReader(FROZEN_REGISTRY.read_text().splitlines()))


def cost_class(row: dict) -> str:
    if row["security_floor_policy"] != "DISABLED":
        return "SECURITY_FLOOR"
    if row.get("fault_schedule", "NONE") != "NONE":
        return "REASSIGNMENT"
    return "LIGHTWEIGHT"


def _atomic_write(path: pathlib.Path, text: str) -> None:
    """Write via a temp file in the same directory, then os.replace — atomic on POSIX."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".tmp-", suffix=".swap")
    try:
        with os.fdopen(fd, "w", newline="") as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except BaseException:
        pathlib.Path(tmp).unlink(missing_ok=True)
        raise


class Registry:
    """The durable run registry.  Updates are atomic and serialised by an advisory lock.

    An interrupted update can never leave a half-written registry: the new content is written
    to a sibling temp file and swapped in with os.replace.
    """

    def __init__(self, path: pathlib.Path = None):
        self.path = pathlib.Path(path) if path else PATHS.registry
        self.lock_path = path.with_suffix(".lock")

    def initialise(self, scenario_rows: dict, logical: dict = None) -> int:
        if self.path.exists():
            return len(self.read())
        rows = []
        for r in frozen_rows():
            srow = scenario_rows[r["scenario_id"]]
            rows.append({f: "" for f in REGISTRY_FIELDS} | {
                "run_id": r["run_id"], "scenario_id": r["scenario_id"],
                "block_id": r.get("block_id", ""), "master_seed": r["master_seed"],
                "seed_index": r["seed_index"], "pair_id": r["pair_id"],
                "cost_class": cost_class(srow), "engine_commit_sha": BASELINE_COMMIT,
                "attempt": "0", "run_status": PENDING,
                "physical_execution_id": (logical or {}).get(r["run_id"], {}).get(
                    "physical_execution_id", ""),
                "shared_physical_execution": str((logical or {}).get(
                    r["run_id"], {}).get("shared_physical_execution", False)).lower(),
                "alias_group_id": (logical or {}).get(r["run_id"], {}).get(
                    "alias_group_id", ""),
            })
        self.write(rows)
        return len(rows)

    def read(self) -> list:
        if not self.path.exists():
            return []
        return list(csv.DictReader(self.path.read_text().splitlines()))

    def write(self, rows: list) -> None:
        buf = io.StringIO(newline="")
        w = csv.DictWriter(buf, fieldnames=REGISTRY_FIELDS, lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow({f: r.get(f, "") for f in REGISTRY_FIELDS})
        _atomic_write(self.path, buf.getvalue())

    def update(self, run_id: str, **fields) -> dict:
        """Read-modify-write one row under an exclusive lock, atomically."""
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.lock_path, "w") as lk:
            fcntl.flock(lk, fcntl.LOCK_EX)
            try:
                rows = self.read()
                hit = None
                for r in rows:
                    if r["run_id"] == run_id:
                        if "run_status" in fields and fields["run_status"] not in STATUSES:
                            raise ValueError(f"unknown status {fields['run_status']!r}")
                        r.update({k: str(v) for k, v in fields.items()})
                        hit = r
                if hit is None:
                    raise KeyError(f"unknown run_id {run_id!r}")
                self.write(rows)
                return hit
            finally:
                fcntl.flock(lk, fcntl.LOCK_UN)

    def by_status(self) -> dict:
        out = {}
        for r in self.read():
            out.setdefault(r["run_status"], []).append(r["run_id"])
        return out


# ---------------------------------------------------------------- S7A-4 physical identity
def physical_execution_id(config_digest: str, master_seed, engine_commit: str) -> str:
    """Deterministic identity of one PHYSICAL execution.

    A physical execution is fully determined by the executable configuration, the master seed
    and the accepted engine commit.  Two logical scenario-seed rows whose configurations are
    byte-identical under the same master seed denote ONE physical execution, and must be
    executed once, not twice.
    """
    return "P-" + hashlib.sha256(
        f"{config_digest}|{master_seed}|{engine_commit}".encode()).hexdigest()[:24]


def build_physical_map() -> dict:
    """Map every logical run_id to its physical execution, and group aliases.

    Returns {"logical": {run_id: {...}}, "physical": {pid: [run_id, ...]}}.
    """
    import scenarios as S                                            # noqa: PLC0415
    srows = {r["scenario_id"]: r for r in S.confirmatory_rows()}
    logical, physical = {}, {}
    for r in frozen_rows():
        cfg = S.build_config(srows[r["scenario_id"]], int(r["master_seed"]), S.TIER2)
        digest = config_sha256(cfg)
        pid = physical_execution_id(digest, r["master_seed"], BASELINE_COMMIT)
        logical[r["run_id"]] = {
            "run_id": r["run_id"], "scenario_id": r["scenario_id"],
            "master_seed": r["master_seed"], "seed_index": r["seed_index"],
            "pair_id": r["pair_id"], "config_sha256": digest,
            "physical_execution_id": pid, "cost_class": cost_class(srows[r["scenario_id"]]),
        }
        physical.setdefault(pid, []).append(r["run_id"])
    for pid, members in physical.items():
        shared = len(members) > 1
        gid = ("ALIAS-" + "+".join(sorted({m.split("-")[0] for m in members}))) if shared else ""
        for rid in members:
            logical[rid]["shared_physical_execution"] = shared
            logical[rid]["alias_group_id"] = gid
    return {"logical": logical, "physical": physical}


def executor_run_id(members: list) -> str:
    """The single logical run_id whose execution materialises a shared physical execution.

    Deterministic: the lexicographically first member.  Every other member is materialised
    from that same verified output and checksum, never re-executed.
    """
    return sorted(members)[0]
