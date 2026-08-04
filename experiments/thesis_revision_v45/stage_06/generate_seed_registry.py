#!/usr/bin/env python3
"""Stage 6 — deterministic master-seed registry generator (PoCol v45).

Emits ``docs/thesis_revision_v45/stage_06/STAGE_06_SEED_REGISTRY.csv``: three DISJOINT
deterministic seed classes.

    PILOT          8 seeds   SHA256("PoCol-v45-stage6-pilot-"        + index)
    CONFIRMATORY  30 seeds   SHA256("PoCol-v45-stage7-confirmatory-" + index)
    ANALYSIS       1 seed    SHA256("PoCol-v45-stage8-analysis-"     + index)

The master seed is the **first unsigned 64-bit big-endian integer** of the digest, i.e.
``int.from_bytes(digest[:8], "big")``.  Indices are **0-based** (pilot 0..7, confirmatory
0..29, analysis 0..0); this base is part of the frozen definition.

Each master seed is mapped into the ACCEPTED Stage-2 configuration surface through two
deterministic child seeds — no new engine seed mechanism is introduced:

    template_seed                = child_seed(master, "template")
    adversarial.deterministic_seed = child_seed(master, "adversarial")

A child seed depends ONLY on the master seed and the role, never on the scenario, so both
arms of a paired contrast running under the same master seed receive the SAME template seed
and the SAME adversarial seed.  That is what makes the pair matched.

Stage 6 does NOT execute any confirmatory seed.  This script only writes the registry.

Usage:
    python experiments/thesis_revision_v45/stage_06/generate_seed_registry.py [--check]

``--check`` regenerates in memory and fails if the committed CSV differs byte-for-byte.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import pathlib
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
REGISTRY_PATH = REPO_ROOT / "docs" / "thesis_revision_v45" / "stage_06" / "STAGE_06_SEED_REGISTRY.csv"

# ---------------------------------------------------------------- frozen definitions
PILOT_LABEL = "PoCol-v45-stage6-pilot-"
CONFIRMATORY_LABEL = "PoCol-v45-stage7-confirmatory-"
ANALYSIS_LABEL = "PoCol-v45-stage8-analysis-"

PILOT_COUNT = 8
CONFIRMATORY_COUNT = 30
ANALYSIS_COUNT = 1

CHILD_LABEL = "PoCol-v45-child-"
CHILD_ROLES = ("template", "adversarial")

SEED_CLASSES = (
    ("PILOT", PILOT_LABEL, PILOT_COUNT),
    ("CONFIRMATORY", CONFIRMATORY_LABEL, CONFIRMATORY_COUNT),
    ("ANALYSIS", ANALYSIS_LABEL, ANALYSIS_COUNT),
)

FIELDNAMES = [
    "seed_class",
    "source_label",
    "seed_index",
    "master_seed_decimal",
    "master_seed_hex",
    "digest_sha256",
    "template_child_seed_decimal",
    "adversarial_child_seed_decimal",
]


def master_seed(source_label: str, index: int) -> tuple:
    """Return ``(seed_decimal, seed_hex, full_digest_hex)`` for one registry entry."""
    digest = hashlib.sha256(f"{source_label}{index}".encode("utf-8")).digest()
    value = int.from_bytes(digest[:8], "big")
    return value, f"{value:016x}", digest.hex()


def child_seed(master: int, role: str) -> int:
    """Deterministic child seed for an ACCEPTED config field (engine unchanged)."""
    if role not in CHILD_ROLES:
        raise ValueError(f"unknown child-seed role: {role!r}")
    digest = hashlib.sha256(f"{CHILD_LABEL}{role}-{master}".encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big")


def build_rows() -> list:
    rows = []
    for seed_class, label, count in SEED_CLASSES:
        for index in range(count):
            value, hexval, digest_hex = master_seed(label, index)
            if seed_class == "ANALYSIS":
                # The analysis seed drives the bootstrap / permutation resampler in Stage 8.
                # It never parameterises a simulation, so it carries no engine child seeds.
                tmpl = adv = "NA"
            else:
                tmpl = child_seed(value, "template")
                adv = child_seed(value, "adversarial")
            rows.append({
                "seed_class": seed_class,
                "source_label": label,
                "seed_index": index,
                "master_seed_decimal": value,
                "master_seed_hex": hexval,
                "digest_sha256": digest_hex,
                "template_child_seed_decimal": tmpl,
                "adversarial_child_seed_decimal": adv,
            })
    # Deterministic total order: seed class in the frozen declaration order, then index.
    order = {name: i for i, (name, _, _) in enumerate(SEED_CLASSES)}
    rows.sort(key=lambda r: (order[r["seed_class"]], r["seed_index"]))
    return rows


def prove_disjointness(rows: list) -> dict:
    """Prove the seed classes are pairwise disjoint and globally unique.  Raises on failure."""
    by_class = {}
    for r in rows:
        by_class.setdefault(r["seed_class"], set()).add(r["master_seed_decimal"])
    report = {}
    names = sorted(by_class)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            overlap = by_class[a] & by_class[b]
            report[f"{a}_vs_{b}_overlap"] = len(overlap)
            if overlap:
                raise SystemExit(
                    f"SEED REGISTRY INVALID: {a} and {b} share {len(overlap)} seed(s): "
                    f"{sorted(overlap)}")
    all_seeds = [r["master_seed_decimal"] for r in rows]
    report["total_seeds"] = len(all_seeds)
    report["distinct_seeds"] = len(set(all_seeds))
    if len(set(all_seeds)) != len(all_seeds):
        raise SystemExit("SEED REGISTRY INVALID: duplicate master seed across the registry")
    # Child seeds must not collide with each other or with any master seed either, so a
    # child seed can never be mistaken for a master seed in an audit.
    children = [r[k] for r in rows for k in
                ("template_child_seed_decimal", "adversarial_child_seed_decimal")
                if r[k] != "NA"]
    report["total_child_seeds"] = len(children)
    report["distinct_child_seeds"] = len(set(children))
    if len(set(children)) != len(children):
        raise SystemExit("SEED REGISTRY INVALID: duplicate child seed")
    collide = set(children) & set(all_seeds)
    report["child_master_collisions"] = len(collide)
    if collide:
        raise SystemExit(f"SEED REGISTRY INVALID: child seed collides with a master seed: "
                         f"{sorted(collide)}")
    return report


def render_csv(rows: list) -> str:
    """Render the registry CSV deterministically (LF endings, no locale dependence)."""
    buf = io.StringIO(newline="")
    writer = csv.DictWriter(buf, fieldnames=FIELDNAMES, lineterminator="\n")
    writer.writeheader()
    for r in rows:
        writer.writerow(r)
    return buf.getvalue()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true",
                    help="verify the committed registry matches regeneration byte-for-byte")
    args = ap.parse_args(argv)

    rows = build_rows()
    report = prove_disjointness(rows)
    text = render_csv(rows)
    checksum = hashlib.sha256(text.encode("utf-8")).hexdigest()

    if args.check:
        if not REGISTRY_PATH.exists():
            print(f"FAIL: {REGISTRY_PATH} does not exist", file=sys.stderr)
            return 1
        committed = REGISTRY_PATH.read_bytes()
        if committed != text.encode("utf-8"):
            print(f"FAIL: {REGISTRY_PATH} differs from regeneration", file=sys.stderr)
            print(f"  committed sha256 : {hashlib.sha256(committed).hexdigest()}",
                  file=sys.stderr)
            print(f"  regenerated      : {checksum}", file=sys.stderr)
            return 1
        print(f"OK: seed registry is byte-identical to regeneration ({checksum})")
    else:
        REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
        REGISTRY_PATH.write_bytes(text.encode("utf-8"))
        print(f"wrote {REGISTRY_PATH.relative_to(REPO_ROOT)}")

    print(f"seed registry sha256 : {checksum}")
    for k in sorted(report):
        print(f"  {k}: {report[k]}")
    pilot = [r["master_seed_decimal"] for r in rows if r["seed_class"] == "PILOT"]
    conf = [r["master_seed_decimal"] for r in rows if r["seed_class"] == "CONFIRMATORY"]
    ana = [r["master_seed_decimal"] for r in rows if r["seed_class"] == "ANALYSIS"]
    print(f"  pilot seeds        : {len(pilot)}")
    print(f"  confirmatory seeds : {len(conf)}")
    print(f"  analysis seed      : {ana[0]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
