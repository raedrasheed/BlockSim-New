"""Stage 5B1A deterministic stratified full-log retention design (Section 9).

Replaces the flat 1%-plus-one-per-group sample with a stratified selection that
guarantees coverage of every scenario x count, every sensitivity level, and the
scientifically interesting regimes (zero-block B1, high-exhaustion, legitimate
stale, non-zero-idle C2, zero-idle-opportunity C2), plus a deterministic 1%
sample of the remainder. Every retained run carries reason codes. The selection
is a pure function of the frozen matrix rows -> reproducible checksum.

Regime strata are chosen by EXPECTED behaviour from configuration (not observed
output), so the list is fixed before Stage 5B2. Section 9 permits adding
failed/anomalous runs automatically during execution; nothing else changes.
"""

from __future__ import annotations
import json
import hashlib
from collections import defaultdict


def _add(reasons, run_id, code):
    reasons[run_id].add(code)


def design_retention(rows, validation_run_ids=None):
    """rows: final matrix rows (dicts with run_id + config fields), ORDERED by run_id.
    Returns (annotated_rows, manifest)."""
    rows = sorted(rows, key=lambda r: r["run_id"])
    reasons = defaultdict(set)

    def first_where(pred):
        for r in rows:
            if pred(r):
                return r["run_id"]
        return None

    def all_values(field):
        return sorted({r[field] for r in rows if field in r})

    # --- S3: at least one per scenario x miner-count ---
    seen = set()
    for r in rows:
        key = (r["scenario_id"], r["miner_count"])
        if key not in seen:
            seen.add(key)
            _add(reasons, r["run_id"], "scenario_count_cover")

    # --- S4: at least one per sensitivity level ---
    for delay in all_values("propagation_delay_mean_s"):
        rid = first_where(lambda r: r["propagation_delay_mean_s"] == delay)
        if rid:
            _add(reasons, rid, f"delay_level:{delay}")
    for mu in all_values("mu"):
        rid = first_where(lambda r: r["mu"] == mu)
        if rid:
            _add(reasons, rid, f"mu_level:{mu}")
    for frac in all_values("inactive_miner_fraction"):
        rid = first_where(lambda r: r["inactive_miner_fraction"] == frac)
        if rid:
            _add(reasons, rid, f"inactive_level:{frac}")
    for ratio in all_values("idle_power_ratio"):
        rid = first_where(lambda r: r["scenario_id"] == "C2" and r["idle_power_ratio"] == ratio)
        if rid:
            _add(reasons, rid, f"idle_power_level:{ratio}")
    # allocation / distribution strata
    for code, pred in (
        ("dist:homogeneous", lambda r: r["hash_rate_distribution"] == "homogeneous"),
        ("dist:heterogeneous_equal", lambda r: r["hash_rate_distribution"] == "heterogeneous_moderate"
            and str(r["allocation_policy"]).endswith("equal")),
        ("dist:heterogeneous_weighted", lambda r: r["hash_rate_distribution"] == "heterogeneous_moderate"
            and str(r["allocation_policy"]).endswith("weighted")),
        ("dist:exploratory_high", lambda r: r["hash_rate_distribution"] == "heterogeneous_high"),
    ):
        rid = first_where(pred)
        if rid:
            _add(reasons, rid, code)

    # --- S5: scientifically interesting regimes (by expected behaviour) ---
    max_n = max(r["miner_count"] for r in rows)
    rid = first_where(lambda r: r["scenario_id"] == "B1" and r["miner_count"] == max_n)
    if rid:
        _add(reasons, rid, "expected_zero_block_b1")
    min_mu = min(r["mu"] for r in rows)
    rid = first_where(lambda r: r["mu"] == min_mu)
    if rid:
        _add(reasons, rid, "expected_high_exhaustion")
    max_delay = max(r["propagation_delay_mean_s"] for r in rows)
    rid = first_where(lambda r: r["propagation_delay_mean_s"] == max_delay)
    if rid:
        _add(reasons, rid, "expected_legitimate_stale")
    rid = first_where(lambda r: r["scenario_id"] == "C2"
                      and r["hash_rate_distribution"] == "heterogeneous_moderate"
                      and str(r["allocation_policy"]).endswith("equal"))
    if rid:
        _add(reasons, rid, "expected_nonzero_idle_c2")
    rid = first_where(lambda r: r["scenario_id"] == "C2"
                      and r["hash_rate_distribution"] == "homogeneous"
                      and str(r["allocation_policy"]).endswith("equal"))
    if rid:
        _add(reasons, rid, "expected_zero_idle_c2")

    # --- S6: deterministic 1% sample of the REMAINING (not-yet-retained) rows ---
    remaining = [r for r in rows if r["run_id"] not in reasons]
    for i, r in enumerate(remaining):
        if i % 100 == 0:
            _add(reasons, r["run_id"], "one_percent_sample")

    # --- annotate rows ---
    for r in rows:
        codes = sorted(reasons.get(r["run_id"], []))
        r["retention_full_log"] = bool(codes)
        r["retention_reason_codes"] = ";".join(codes)

    retained = sorted(rid for rid, cs in reasons.items() if cs)
    val_ids = sorted(validation_run_ids or [])
    checksum_blob = json.dumps(dict(matrix=retained, validation=val_ids), sort_keys=True)
    checksum = hashlib.sha256(checksum_blob.encode()).hexdigest()
    manifest = dict(
        matrix_retained_count=len(retained),
        validation_retained_count=len(val_ids),
        total_retained=len(retained) + len(val_ids),
        matrix_retained_run_ids=retained,
        validation_retained_run_ids=val_ids,
        reason_codes={rid: sorted(cs) for rid, cs in reasons.items() if cs},
        retention_checksum_sha256=checksum,
    )
    return rows, manifest
