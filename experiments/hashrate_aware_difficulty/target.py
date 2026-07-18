"""Target / difficulty / probability model (integer-safe, 256-bit clamped).

Definitions:
    W_expected  = H_network * T_target                (expected work, hashes)
    target      = floor(2^256 / W_expected) - 1       clamped to [0, 2^256 - 1]
    p_success   = (target + 1) / 2^256  ~=  1 / W_expected
    difficulty  = 2^256 / (target + 1)  ~=  W_expected (expected hashes/block)
    E[T_block]  = difficulty / H_network ~= T_target

Difficulty lives HERE (in the target), never in the nonce-domain size.
"""
from __future__ import annotations

import math

TWO_256 = 1 << 256
MAX_TARGET = TWO_256 - 1


def expected_work(h_network_hps, t_target_s):
    """W_expected = H_network * T_target (float hashes; may be huge)."""
    return float(h_network_hps) * float(t_target_s)


def target_from_work(w_expected):
    """target = floor(2^256 / W) - 1, integer-safe, clamped to [0, 2^256-1]."""
    w = int(math.ceil(float(w_expected)))
    if w <= 1:
        return MAX_TARGET                     # trivial difficulty: everything passes
    t = TWO_256 // w - 1
    return max(0, min(MAX_TARGET, t))


def p_from_target(target):
    """p_success = (target + 1) / 2^256."""
    t = int(target)
    if not (0 <= t <= MAX_TARGET):
        raise ValueError("target outside 256-bit range")
    return (t + 1) / float(TWO_256)


def difficulty_from_target(target):
    """difficulty = 2^256 / (target + 1) = expected hashes per valid candidate."""
    return float(TWO_256) / float(int(target) + 1)


def target_for(h_network_hps, t_target_s):
    """Convenience: target for a network hash rate and expected interval."""
    return target_from_work(expected_work(h_network_hps, t_target_s))


def expected_block_time(target, h_network_hps):
    """E[T_block] = difficulty / H_network seconds."""
    return difficulty_from_target(target) / float(h_network_hps)


def domain_no_success_probability(p_success, m_domain):
    """P(domain of size M has no valid candidate) = (1-p)^M (log-safe)."""
    if p_success <= 0:
        return 1.0
    if p_success >= 1:
        return 0.0
    return math.exp(float(m_domain) * math.log1p(-p_success))
