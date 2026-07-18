"""Run ONE fixed-600s scenario and print one JSON metrics record.

This is the fresh-subprocess unit used by run_matrix.py (invariant 26: no
global-state leakage between runs).

Deterministic:
  python experiments/fixed_600s_pocol/run_scenario.py pocol_disjoint_nonce 10 \
      --hardware H2 --M 100 --h2-rate 1 --placement last --sim 600
Stochastic:
  python experiments/fixed_600s_pocol/run_scenario.py pocol_disjoint_nonce 100 \
      --hardware H1 --p auto --seed 3
"""
import os
import sys
import json
import argparse

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from experiments.fixed_600s_pocol.configuration import (
    FixedRoundConfig, PowerConfig, PROTOCOLS, HW_H1, HW_H2, PLACEMENTS,
)
from experiments.fixed_600s_pocol.round_state import simulate
from experiments.fixed_600s_pocol import pow_duplicate, pow_independent, pocol_disjoint
from experiments.fixed_600s_pocol.configuration import PROTO_DUP, PROTO_IND, PROTO_POCOL

_DET = {
    PROTO_DUP: pow_duplicate.deterministic_provider,
    PROTO_IND: pow_independent.deterministic_provider,
    PROTO_POCOL: pocol_disjoint.deterministic_provider,
}


def run(protocol, N, hardware=HW_H1, M=None, h2_rate=None, placement="last",
        idle=0.0, sleep=0.0, use_sleep=False, seed=0, p=None, sim=10200.0,
        txs=2000, explicit_nonces=None, want_rounds=False, want_miners=False):
    cfg = FixedRoundConfig(
        N=N, protocol=protocol, hardware=hardware, M=M, h2_hashrate_hps=h2_rate,
        placement=placement, explicit_nonces=explicit_nonces,
        power=PowerConfig(idle_ratio=idle, sleep_ratio=sleep, use_sleep=use_sleep),
        seed=seed, p_success=p, sim_seconds=sim, txs_per_block=txs)
    if p is None:
        provider = _DET[protocol](cfg)
    else:
        from experiments.fixed_600s_pocol.stochastic_template import stochastic_provider
        provider = stochastic_provider(cfg)
    metrics, miners, rounds = simulate(cfg, provider)
    if want_rounds:
        metrics["_rounds"] = [{
            "round_id": r.round_id, "round_start": r.round_start,
            "committed": r.committed, "commit_time": r.commit_time,
            "discovery_time": r.discovery_time, "winner_id": r.winner_id,
            "winning_nonce": r.winning_nonce, "n_templates": r.n_templates,
            "exhausted_templates": r.exhausted_templates, "attempts": r.attempts,
            "unique_evals": r.unique_evals, "duplicate_evals": r.duplicate_evals,
            "post_discovery_idle_s": r.post_discovery_idle_s,
        } for r in rounds]
    if want_miners:
        metrics["_miners"] = [m.to_dict() for m in miners]
    return metrics


def _parse():
    ap = argparse.ArgumentParser()
    ap.add_argument("protocol", choices=PROTOCOLS)
    ap.add_argument("N", type=int)
    ap.add_argument("--hardware", choices=["H1", "H2"], default="H1")
    ap.add_argument("--M", type=int, default=None)
    ap.add_argument("--h2-rate", type=float, default=None)
    ap.add_argument("--placement", choices=PLACEMENTS, default="last")
    ap.add_argument("--idle", type=float, default=0.0)
    ap.add_argument("--sleep", type=float, default=0.0)
    ap.add_argument("--use-sleep", action="store_true")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--p", default=None,
                    help="'auto' => 2/M (E[successes]=2 per template), or a float")
    ap.add_argument("--sim", type=float, default=10200.0)
    ap.add_argument("--txs", type=int, default=2000)
    ap.add_argument("--rounds", action="store_true")
    ap.add_argument("--miners", action="store_true")
    return ap.parse_args()


if __name__ == "__main__":
    a = _parse()
    hw = HW_H1 if a.hardware == "H1" else HW_H2
    p = None
    if a.p is not None:
        if a.p == "auto":
            probe = FixedRoundConfig(N=a.N, hardware=hw, M=a.M, h2_hashrate_hps=a.h2_rate)
            p = 2.0 / probe.effective_M()
        else:
            p = float(a.p)
    rec = run(a.protocol, a.N, hardware=hw, M=a.M, h2_rate=a.h2_rate,
              placement=a.placement, idle=a.idle, sleep=a.sleep,
              use_sleep=a.use_sleep, seed=a.seed, p=p, sim=a.sim, txs=a.txs,
              want_rounds=a.rounds, want_miners=a.miners)
    print(json.dumps(rec))
