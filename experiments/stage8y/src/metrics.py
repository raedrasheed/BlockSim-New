"""Stage 8Y — derived metrics, security/fairness measures and the mandatory
energy-saving decomposition.

The decomposition exists to prevent the claim "PoCol saved X%" when the real
explanation is "PoCol performed X% less hashing" (brief sections 40-41).

Exact accounting identity
-------------------------
Every miner is in exactly one of ACTIVE / WAKING / LOW_POWER / STANDBY at all times,
and WAKING is charged at full active power, so

    P_N * T = pw_active + pw_waking + pw_low + pw_standby                      (1)

with ``pw_s = sum_i P_i * t_{i,s}``. Hence the removed power-time is exactly the
parked power-time,

    R = P_N*T - (pw_active + pw_waking) = pw_low + pw_standby                   (2)

and the energy saving against the always-active PoW baseline is exactly

    dE(alpha) = (1 - alpha) * R                                                 (3)

Two orthogonal exact decompositions of (3) are reported.

D1 — by cause (participation vs selection)
    c = CapacityRemovedFraction = 1 - int H_active dt / (H_N * T)
    A *capacity-neutral* removal (one that parks power in the same proportion as
    it parks hash capacity, which is what a homogeneous network or a random
    selection achieves) would have removed  R_neutral = c * P_N * T.
        dE_participation = (1 - alpha) * R_neutral
        dE_selection     = (1 - alpha) * (R - R_neutral)
    dE_selection is exactly the part of the saving that comes from preferentially
    parking electrically expensive capacity. It is zero in a homogeneous network.

    Because the split is a two-factor attribution it is ordering-dependent, so a
    Shapley-style symmetric split is reported alongside the sequential one:
        v(0)=0, v({part}) = (1-alpha)*R_neutral, v({sel}) = 0, v({both}) = dE
        phi_part = 0.5*v({part}) + 0.5*dE
        phi_sel  = 0.5*(dE - v({part}))

D2 — by state origin (post-range low power vs reserve standby)
        dE_postrange = (1 - alpha) * pw_low
        dE_reserve   = (1 - alpha) * pw_standby

D3 — stale work
    In a wall-clock state x power model an ACTIVE miner draws the same power
    whether its work is useful or stale, so eliminating stale work does **not**
    reduce energy unless it also reduces active time. dE_stale is therefore
    identically zero here, and the stale-work *evaluation* difference is reported
    separately as a physical-work diagnostic rather than folded into the energy
    identity. Reporting it any other way would be exactly the conflation the brief
    forbids.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence


def _safe_div(a: float, b: float) -> Optional[float]:
    return (a / b) if b else None


def gini(values: Sequence[float]) -> Optional[float]:
    """Gini concentration coefficient; None if the total is zero."""
    v = sorted(float(x) for x in values)
    n = len(v)
    s = sum(v)
    if n == 0 or s <= 0:
        return None
    cum = sum((i + 1) * x for i, x in enumerate(v))
    return (2.0 * cum) / (n * s) - (n + 1.0) / n


def participation_metrics(power_state: Dict[str, float], h_total: float,
                          p_total: float, horizon_s: float) -> Dict[str, Optional[float]]:
    """Capacity/power removal, selectivity and security-hash measures."""
    hn_t = h_total * horizon_s
    pn_t = p_total * horizon_s
    int_h = power_state["integral_H_active_hashes"]
    int_p_drawn = (power_state["integral_P_active_Ws"]
                   + power_state["integral_P_waking_Ws"])
    cap_removed = 1.0 - (int_h / hn_t) if hn_t else None
    pow_removed = 1.0 - (int_p_drawn / pn_t) if pn_t else None
    sel_gain = None
    if cap_removed is not None and pow_removed is not None and cap_removed > 1e-9:
        sel_gain = pow_removed / cap_removed
    return {
        "HashCapacityResidence_hashes": int_h,
        "PowerResidence_Ws": int_p_drawn,
        "CapacityRemovedFraction": cap_removed,
        "PowerRemovedFraction": pow_removed,
        "SelectivityGain": sel_gain,
        "SelectivityGain_defined": sel_gain is not None,
        "mean_SecurityHashFraction": power_state["mean_h_active_fraction"],
        "min_SecurityHashFraction": power_state["min_h_active_fraction"],
        "mean_PowerDrawnFraction": power_state["mean_p_drawn_fraction"],
    }


def decompose_saving(power_state: Dict[str, float], h_total: float, p_total: float,
                     horizon_s: float, alpha: float) -> Dict[str, Optional[float]]:
    """Exact energy-saving decomposition, equations (1)-(3) and D1/D2/D3 above."""
    pn_t = p_total * horizon_s
    pw_low = power_state["pw_low_Ws"]
    pw_standby = power_state["pw_standby_Ws"]
    pw_active = power_state["pw_active_Ws"]
    pw_waking = power_state["pw_waking_Ws"]

    identity_error = abs(pn_t - (pw_active + pw_waking + pw_low + pw_standby))
    R = pw_low + pw_standby
    dE = (1.0 - alpha) * R

    int_h = power_state["integral_H_active_hashes"]
    c = 1.0 - (int_h / (h_total * horizon_s)) if h_total and horizon_s else 0.0
    R_neutral = c * pn_t
    dE_part_seq = (1.0 - alpha) * R_neutral
    dE_sel_seq = dE - dE_part_seq
    phi_part = 0.5 * dE_part_seq + 0.5 * dE
    phi_sel = 0.5 * (dE - dE_part_seq)

    return {
        "alpha": alpha,
        "E_PoW_reference_J": pn_t,
        "removed_power_time_Ws": R,
        "dE_total_J": dE,
        "saving_fraction": _safe_div(dE, pn_t),
        # D1 sequential
        "dE_participation_J": dE_part_seq,
        "dE_selection_J": dE_sel_seq,
        "share_participation": _safe_div(dE_part_seq, dE),
        "share_selection": _safe_div(dE_sel_seq, dE),
        # D1 Shapley
        "dE_participation_shapley_J": phi_part,
        "dE_selection_shapley_J": phi_sel,
        "share_participation_shapley": _safe_div(phi_part, dE),
        "share_selection_shapley": _safe_div(phi_sel, dE),
        # D2 by state origin
        "dE_postrange_J": (1.0 - alpha) * pw_low,
        "dE_reserve_J": (1.0 - alpha) * pw_standby,
        "share_postrange": _safe_div((1.0 - alpha) * pw_low, dE),
        "share_reserve": _safe_div((1.0 - alpha) * pw_standby, dE),
        # D3
        "dE_stale_J": 0.0,
        "dE_other_J": 0.0,
        "decomposition_residual_J": dE - (dE_part_seq + dE_sel_seq),
        "power_identity_error_Ws": identity_error,
    }


def fairness_metrics(device_stats: Dict[str, Dict[str, float]],
                     blocks_by_miner: Dict[int, int],
                     active_seconds_by_miner: List[float],
                     n_miners: int, horizon_s: float) -> Dict[str, Optional[float]]:
    """Concentration of participation and reward across hardware classes/miners."""
    total_blocks = sum(blocks_by_miner.values())
    total_active = sum(active_seconds_by_miner)
    out: Dict[str, Optional[float]] = {
        "gini_blocks_by_miner": gini([blocks_by_miner.get(i, 0)
                                      for i in range(n_miners)]),
        "gini_active_time_by_miner": gini(active_seconds_by_miner),
        "miners_with_zero_active_time": sum(1 for x in active_seconds_by_miner
                                            if x <= 1e-9),
        "miners_with_zero_blocks": sum(1 for i in range(n_miners)
                                       if blocks_by_miner.get(i, 0) == 0),
    }
    for key, st in device_stats.items():
        out[f"participation_share_{key}"] = _safe_div(st["active_seconds"], total_active)
        out[f"reward_share_{key}"] = _safe_div(st["blocks_won"], total_blocks)
        out[f"active_time_share_{key}"] = st["active_fraction_of_own_time"]
        out[f"installed_hash_share_{key}"] = st["hash_share_installed"]
        out[f"selection_frequency_{key}"] = _safe_div(st["n_initially_active"],
                                                      st["count"])
    return out


def paired_service_metrics(pocol: Dict, pow_ref: Dict) -> Dict[str, Optional[float]]:
    """Retention/latency ratios against the matched PoW run. NA stays NA."""
    b_pc, b_pw = pocol["accepted_blocks"], pow_ref["accepted_blocks"]
    lat_pc = pocol.get("median_block_interval")
    lat_pw = pow_ref.get("median_block_interval")
    mean_pc = pocol.get("mean_block_interval")
    mean_pw = pow_ref.get("mean_block_interval")
    return {
        "BlockRetention": _safe_div(b_pc, b_pw),
        "LatencyRatio_median": (lat_pc / lat_pw) if (lat_pw and lat_pc) else None,
        "LatencyRatio_mean": (mean_pc / mean_pw) if (mean_pw and mean_pc) else None,
        "HashRetention": _safe_div(
            pocol["power_state"]["integral_H_active_hashes"],
            pow_ref["power_state"]["integral_H_active_hashes"]),
    }
