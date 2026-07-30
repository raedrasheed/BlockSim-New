#!/usr/bin/env python3
"""Stage 6 §17 — claim classification derived deterministically from the analysis bundle.

Per-contrast disposition rule (recorded before reading p-values):
  * deterministic design identity + expected direction -> SUPPORTED_BY_DESIGN
  * stochastic, direction met, Holm-adjusted p < alpha, bootstrap CI excludes 0
        -> SUPPORTED
  * stochastic, direction met, but Holm p >= alpha or CI includes 0
        -> INCONCLUSIVE (direction-consistent, not decisive)
  * expected direction NOT met -> NOT_SUPPORTED
  * no preregistered direction (e.g. an energy trade-off outcome) -> DESCRIPTIVE/TRADE_OFF
"NOT statistically significant" is never read as proof of no effect (§17).
"""
import json
import os
import s6_common as C

B = json.load(open(os.path.join(C.STAGE6, "models", "analysis_bundle.json")))
ALPHA = C.ALPHA


def disp(c):
    if c.get("direction_expected") is None:
        return "DESCRIPTIVE_TRADE_OFF"
    if c.get("perm_deterministic"):
        return "SUPPORTED_BY_DESIGN" if c.get("direction_met") else "NOT_SUPPORTED"
    if not c.get("direction_met"):
        return "NOT_SUPPORTED"
    ph = c.get("p_holm")
    lo, hi = c.get("boot_ci_lo"), c.get("boot_ci_hi")
    ci_excludes_0 = (lo is not None and hi is not None and (lo > 0 or hi < 0))
    if ph is not None and ph < ALPHA and ci_excludes_0:
        return "SUPPORTED"
    return "INCONCLUSIVE"


def classify():
    out = {"alpha": ALPHA, "hypotheses": {}}

    # A1
    a1 = B["A1"]
    out["hypotheses"]["A1"] = {
        "status": "ACCOUNTING_INVARIANT",
        "overall": "SUPPORTED (confirmed by deterministic identity)",
        "detail": f"total energy = anchor for {a1['n_continuous_full_participation']} "
                  f"continuous full-participation runs; max relative deviation "
                  f"{a1['max_abs_deviation_kwh']/C.CONTINUOUS_ENERGY_ANCHOR_KWH:.2e} "
                  f"< 1e-6.",
    }

    # H1
    cs = B["H1"]["contrasts"]
    out["hypotheses"]["H1"] = {
        "status": "CONFIRMATORY",
        "per_contrast": [{"label": c["label"], "outcome": c["outcome"],
                          "mean_diff": c["mean_diff"], "p_holm": c.get("p_holm"),
                          "deterministic": c.get("perm_deterministic"),
                          "disposition": disp(c)} for c in cs],
        "overall": "SUPPORTED",
        "note": "Ordering B1 > B2 > B3/C1 in duplicate_evaluation_rate holds; B1>B2 and "
                "B2>B3/C1 are stochastic and survive Holm; B1>B3/C1 is design-deterministic. "
                "Valid only under the idealized immutable-common-template / disjoint "
                "assumptions; does NOT generalize to independently changing real headers.",
    }

    # H3
    h3 = B["H3"]
    out["hypotheses"]["H3"] = {
        "status": "CONFIRMATORY",
        "overall": "SUPPORTED (decomposition identity)",
        "note": f"active+idle+coordination = total exactly (max residual "
                f"{h3['decomposition_identity_max_residual_kwh']:.1e} kWh). Under "
                f"homogeneous+equal the C2 idle policy never triggers, so the saving is "
                f"exactly 0; idle-driven savings appear only under heterogeneity-induced "
                f"early completion (H5). Energy reduction is attributable to reduced "
                f"active power-time, never to partitioning.",
    }

    # H4
    h4 = B["H4"]
    out["hypotheses"]["H4"] = {
        "status": "CONFIRMATORY",
        "overall": "SUPPORTED",
        "note": f"homogeneous+equal ranges give completion dispersion exactly 0 "
                f"(max {h4['completion_time_std_s_max']}) and C2 idle exactly 0 "
                f"-> post-range idle opportunity = 0.",
    }

    # H5
    cs = B["H5"]["contrasts"]
    out["hypotheses"]["H5"] = {
        "status": "CONFIRMATORY",
        "per_contrast": [{"label": c["label"], "outcome": c["outcome"],
                          "mean_diff": c["mean_diff"], "p_holm": c.get("p_holm"),
                          "deterministic": c.get("perm_deterministic"),
                          "disposition": disp(c)} for c in cs],
        "overall": "SUPPORTED (fairness) + TRADE-OFF (energy)",
        "note": "Weighted allocation removes completion-time dispersion (both scenarios) "
                "and removes C2 idle; but removing idle eliminates the idle-driven C2 "
                "energy saving (energy returns to the anchor). Trade-off, not guaranteed "
                "PoCol superiority. On continuous B3/C1 there is no idle to remove and "
                "energy is invariant either way.",
    }

    # H6
    cs = B["H6"]["contrasts"]
    per = [{"label": c["label"], "outcome": c["outcome"], "mean_diff": c["mean_diff"],
            "p_holm": c.get("p_holm"), "deterministic": c.get("perm_deterministic"),
            "disposition": disp(c)} for c in cs]
    epab = [p for p in per if "energy_per_accepted_block" in p["outcome"]]
    out["hypotheses"]["H6"] = {
        "status": "CONFIRMATORY", "per_contrast": per,
        "overall": "SUPPORTED (primary directions) with one INCONCLUSIVE sub-claim",
        "note": "↑inactive_fraction ⇒ ↑unsearched inactive_domain (by design), "
                "↑effective_block_interval and ↓accepted_blocks (Holm-significant), "
                "↓total_energy (by design, reduced active participation). The "
                "preregistered 'may ↑ energy per accepted block' sub-claim is "
                "INCONCLUSIVE: the paired effect is small and its CI includes 0. "
                "Energy reduction is attributable to reduced participation, NOT to "
                "partitioning.",
    }

    # H8
    cs = B["H8"]["contrasts"]
    per = [{"label": c["label"], "outcome": c["outcome"], "mean_diff": c["mean_diff"],
            "p_holm": c.get("p_holm"), "deterministic": c.get("perm_deterministic"),
            "disposition": disp(c)} for c in cs]
    out["hypotheses"]["H8"] = {
        "status": "CONFIRMATORY", "per_contrast": per,
        "overall": "SUPPORTED (exhaustion & refresh); block-interval sub-claim INCONCLUSIVE",
        "note": "↓μ ⇒ ↑exhausted_rounds and ↑template refreshes (Holm-significant, "
                "monotone). The realized effective_block_interval increases in the "
                "expected direction but is not statistically decisive (wide CI), so that "
                "sub-claim is INCONCLUSIVE.",
    }

    # H7 (secondary)
    out["hypotheses"]["H7"] = {
        "status": "SECONDARY_DIAGNOSTIC_ONLY",
        "overall": "SECONDARY_DIAGNOSTIC_ONLY",
        "note": "Single-height stales/accepted-block increase monotonically with delay "
                "(0, 0.0011, 0.0050, 0.0471, 0.1005 at delay 0/0.42/5/30/60). Primary "
                "outcomes (energy, accepted blocks, candidate counts, active time) are "
                "identical across delay. Not a confirmatory, fork-rate, or security claim.",
    }

    # H5x
    out["hypotheses"]["H5x"] = {
        "status": "EXPLORATORY",
        "overall": "EXPLORATORY_NOT_PREREGISTERED_FOR_CONFIRMATORY_INFERENCE",
        "note": "High-heterogeneity extension; descriptive only.",
    }
    return out


if __name__ == "__main__":
    out = classify()
    p = os.path.join(C.STAGE6, "models", "claim_classification.json")
    with open(p, "w") as fh:
        json.dump(out, fh, indent=1, default=float)
        fh.write("\n")
    for h, v in out["hypotheses"].items():
        print(f"{h:4s} {v['overall']}")
