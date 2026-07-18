"""Mode A — common-template duplicate-search PoW baseline.

NOT normal Bitcoin mining. Every miner receives the same immutable template and
the COMPLETE nonce domain, starts at the same nonce, scans in the same order,
and therefore repeats identical complete candidate-header evaluations. All stop
at the first discovery and stay IDLE until the 600-second boundary.
"""
from __future__ import annotations

from .round_state import TemplateOutcome
from .deterministic_template import valid_nonces


def deterministic_provider(cfg):
    """One known valid nonce (or explicit set); identical stream for all miners,
    so every miner's local success step is g_first + 1 (same scan order)."""
    M = cfg.effective_M()
    ns = valid_nonces(cfg, M)
    g = min(ns)                       # first success in the common numeric order
    N = cfg.N

    def provider(_cfg, _round_id, _template_index):
        return TemplateOutcome(
            template_id=f"DUP-det-{_round_id}-{_template_index}",
            sizes=[M] * N,
            local_success=[g + 1] * N,
            nonce_value=[g] * N,
        )
    return provider
