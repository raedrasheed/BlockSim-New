#!/usr/bin/env python3
"""Stage 5B2A §5 — remote roundtrip verification.

Independent of the execution worktree: uses ONLY the freshly-cloned bulk-data
branch as the "downloaded remote assets", plus the two authoritative checksum
manifests as the reference. Steps (exactly the §5 protocol):

  1. list all remote assets (chunk files in the fresh clone);
  2. verify asset names and byte sizes against the archive manifest;
  3. (download already done via `git clone`);
  4. recompute every chunk SHA-256 vs STAGE_05B2A_ARCHIVE_ASSET_CHECKSUMS.sha256;
  5. reconstruct each archive (cat parts | tar -x) into a clean dir;
  6. verify EVERY extracted file vs STAGE_05B2A_ORIGINAL_BULK_FILE_CHECKSUMS.sha256
     (path present + sha match, and no missing / extra files).
"""
import hashlib
import json
import os
import subprocess
import sys

CLONE = "/home/user/blocksim-5b2a-verify/clone"
BULK = os.path.join(CLONE, "results/thesis_revision_v43/stage_05b2/bulk_archives")
EXTRACT = "/home/user/blocksim-5b2a-verify/extract"
DOCS = "/home/user/blocksim-stage5b2-exec/docs/thesis_revision_v43"
CHUNK_MANIFEST = os.path.join(DOCS, "STAGE_05B2A_ARCHIVE_ASSET_CHECKSUMS.sha256")
ORIG_MANIFEST = os.path.join(DOCS, "STAGE_05B2A_ORIGINAL_BULK_FILE_CHECKSUMS.sha256")
ARCH_MANIFEST = os.path.join(DOCS, "STAGE_05B2A_BULK_ARCHIVE_MANIFEST.json")


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_sha_manifest(path, strip_prefix=None):
    d = {}
    with open(path) as fh:
        for line in fh:
            line = line.rstrip("\n")
            if not line:
                continue
            sha, name = line.split(None, 1)
            if strip_prefix and name.startswith(strip_prefix):
                name = name[len(strip_prefix):]
            d[name] = sha
    return d


def main():
    fail = 0
    arch = json.load(open(ARCH_MANIFEST))

    # ---- Step 4: chunk names, sizes, and SHA-256 ----
    chunk_sha = load_sha_manifest(
        CHUNK_MANIFEST,
        strip_prefix="results/thesis_revision_v43/stage_05b2/bulk_archives/")
    print(f"[1-2] chunk manifest entries: {len(chunk_sha)}")

    present = sorted(f for f in os.listdir(BULK) if ".tar.part-" in f)
    print(f"[1] chunk files in fresh clone: {len(present)}")
    if set(present) != set(chunk_sha):
        print("  !! chunk file set != manifest set")
        print("   only-clone:", sorted(set(present) - set(chunk_sha))[:5])
        print("   only-manifest:", sorted(set(chunk_sha) - set(present))[:5])
        fail += 1

    # size map from archive manifest
    size_map = {}
    for a in arch["archives"]:
        for c in a["chunks"]:
            size_map[c["name"]] = c["bytes"]

    chunk_bad = 0
    for name in sorted(chunk_sha):
        p = os.path.join(BULK, name)
        if not os.path.isfile(p):
            print(f"  !! missing chunk {name}"); chunk_bad += 1; continue
        actual_bytes = os.path.getsize(p)
        if name in size_map and actual_bytes != size_map[name]:
            print(f"  !! size mismatch {name}: manifest={size_map[name]} actual={actual_bytes}")
            chunk_bad += 1
        actual = sha256_file(p)
        if actual != chunk_sha[name]:
            print(f"  !! SHA mismatch {name}")
            chunk_bad += 1
    print(f"[2-4] chunk name+size+sha256: {len(chunk_sha)-chunk_bad}/{len(chunk_sha)} OK")
    if chunk_bad:
        fail += 1

    # ---- Step 5: reconstruct each archive ----
    os.makedirs(EXTRACT, exist_ok=True)
    for a in arch["archives"]:
        order = a["reconstruction_order"]
        cmd = "cat " + " ".join(os.path.join(BULK, n) for n in order) + " | tar -xf - -C " + EXTRACT
        rc = subprocess.run(cmd, shell=True).returncode
        status = "OK" if rc == 0 else f"FAIL rc={rc}"
        print(f"[5] reconstruct {a['archive_name']} ({len(order)} parts): {status}")
        if rc != 0:
            fail += 1

    # ---- Step 6: verify every extracted file ----
    orig = load_sha_manifest(ORIG_MANIFEST)
    print(f"[6] original-file manifest entries: {len(orig)}")
    missing = 0
    badsha = 0
    for rel, want in orig.items():
        p = os.path.join(EXTRACT, rel)
        if not os.path.isfile(p):
            missing += 1
            if missing <= 5:
                print(f"  !! extracted file missing: {rel}")
            continue
        got = sha256_file(p)
        if got != want:
            badsha += 1
            if badsha <= 5:
                print(f"  !! sha mismatch: {rel}")
    # extra files?
    extracted = set()
    for dp, _d, fs in os.walk(EXTRACT):
        for fn in fs:
            extracted.add(os.path.relpath(os.path.join(dp, fn), EXTRACT))
    extra = sorted(extracted - set(orig))
    print(f"[6] extracted files: {len(extracted)}; missing: {missing}; sha-bad: {badsha}; extra: {len(extra)}")
    if extra[:5]:
        print("   extra sample:", extra[:5])
    if missing or badsha or extra or len(extracted) != len(orig):
        fail += 1

    print()
    if fail == 0:
        print("ROUNDTRIP_OK all chunks + all 2196 extracted files verified byte-identical")
        sys.exit(0)
    print(f"ROUNDTRIP_FAIL problems={fail}")
    sys.exit(2)


if __name__ == "__main__":
    main()
