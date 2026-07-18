"""Stochastic shared-template model for the fixed 600-second rounds.

Per template (seed, round_id, template_index) each disjoint subrange i draws its
first LOCAL success G_i ~ Geometric(p) from a deterministic sha256-derived
range seed. A success is valid only when G_i <= range_size_i. No success is ever
fabricated: a template with no valid success exhausts, and a round that reaches
its boundary without success is an EMPTY round, reported honestly.

- PoCol: discovery = min LOCAL step (a numerically later nonce can win);
  winning nonce = range_start_i + G_i - 1.
- Duplicate baseline: the SAME per-range success set is reconstructed and the
  first success in the common numeric scan order wins:
  g* = min_i (range_start_i + G_i - 1); every miner scans g*+1 steps.
- Independent headers: per-miner independent streams (distinct seed tag), one
  geometric per miner against its budget; no shared nonce identity.

Paired: DUP and POCOL at the same (seed, round, template) share the exact same
success positions. p_success may be given directly or as (target+1)/2^256.
"""
from __future__ import annotations

import math
import hashlib

from .configuration import PROTO_DUP, PROTO_IND, PROTO_POCOL
from .nonce_partition import partition_nonce_domain, range_size
from .round_state import TemplateOutcome


def p_from_target(target, bits=256):
    """Bitcoin-style per-candidate success probability p = (target+1)/2^bits."""
    return (int(target) + 1) / float(2 ** bits)


def _u(seed_material):
    """Deterministic uniform in (0,1] from arbitrary key material (sha256)."""
    h = hashlib.sha256(seed_material.encode()).digest()
    x = int.from_bytes(h[:8], "big")
    return (x + 1) / float(2 ** 64)          # (0, 1]


def _geom(u, p):
    """1-based first-success index of Bernoulli(p) from uniform u (analytic)."""
    if p <= 0.0:
        return None                           # success impossible; never fabricate
    if p >= 1.0:
        return 1
    return int(math.floor(math.log(u) / math.log1p(-p))) + 1


def _range_successes(cfg, round_id, template_index):
    """(ranges, sizes, G) for the shared template; G[i] valid local step or None."""
    M = cfg.effective_M()
    ranges = partition_nonce_domain(0, M, cfg.N)
    sizes = [range_size(r) for r in ranges]
    G = []
    for i, sz in enumerate(sizes):
        g = _geom(_u(f"shared:{cfg.seed}:{round_id}:{template_index}:{i}"), cfg.p_success)
        G.append(g if (g is not None and sz > 0 and g <= sz) else None)
    return ranges, sizes, G


def stochastic_provider(cfg):
    """TemplateOutcome provider for the configured protocol (paired seeds)."""
    if cfg.p_success is None:
        raise ValueError("stochastic_provider requires cfg.p_success")
    M = cfg.effective_M()
    N = cfg.N

    def provider(_cfg, round_id, template_index):
        tid = f"{cfg.protocol}-sto-{cfg.seed}-{round_id}-{template_index}"
        if cfg.protocol == PROTO_POCOL:
            ranges, sizes, G = _range_successes(cfg, round_id, template_index)
            nv = [ranges[i][0] + g - 1 if g is not None else None
                  for i, g in enumerate(G)]
            return TemplateOutcome(tid, sizes, list(G), nv)

        if cfg.protocol == PROTO_DUP:
            ranges, _sizes, G = _range_successes(cfg, round_id, template_index)
            globals_ = [ranges[i][0] + g - 1 for i, g in enumerate(G) if g is not None]
            if globals_:
                g_star = min(globals_)               # first in common scan order
                ls = [g_star + 1] * N
                nv = [g_star] * N
            else:
                ls = [None] * N
                nv = [None] * N
            return TemplateOutcome(tid, [M] * N, ls, nv)

        if cfg.protocol == PROTO_IND:
            budgets = [range_size(r) for r in partition_nonce_domain(0, M, N)]
            ls = []
            for i, b in enumerate(budgets):
                g = _geom(_u(f"indep:{cfg.seed}:{round_id}:{template_index}:{i}"),
                          cfg.p_success)
                ls.append(g if (g is not None and b > 0 and g <= b) else None)
            return TemplateOutcome(tid, budgets, ls, [None] * N)

        raise ValueError(f"unknown protocol {cfg.protocol!r}")
    return provider
