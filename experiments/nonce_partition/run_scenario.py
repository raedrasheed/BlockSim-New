"""Run ONE nonce-partition scenario and print a JSON record.

Deterministic worst case (solution at final position):
    python -m experiments.nonce_partition.run_scenario <mode> <M> <N>
    python experiments/nonce_partition/run_scenario.py duplicate_full_domain 100 10
    python experiments/nonce_partition/run_scenario.py disjoint_partition    100 10

Stochastic (Bernoulli success probability p, paired seed):
    python experiments/nonce_partition/run_scenario.py <mode> <M> <N> <seed> <p>

modes: duplicate_full_domain | disjoint_partition | independent_candidate_headers
(independent_candidate_headers requires the stochastic form).
"""
import os
import sys
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from experiments.nonce_partition.model import (
    duplicate_full_domain, disjoint_partition,
    duplicate_full_domain_stochastic, disjoint_partition_stochastic,
    independent_candidate_headers_stochastic, assert_energy_methods_agree,
)

_DET = {
    "duplicate_full_domain": duplicate_full_domain,
    "disjoint_partition": disjoint_partition,
}
_STO = {
    "duplicate_full_domain": duplicate_full_domain_stochastic,
    "disjoint_partition": disjoint_partition_stochastic,
    "independent_candidate_headers": independent_candidate_headers_stochastic,
}


def run(mode, M, N, seed=None, p=None):
    if p is None:
        if mode not in _DET:
            raise ValueError(f"mode {mode!r} requires the stochastic form (provide seed and p)")
        res = _DET[mode](M, N, solution="last")
        stochastic = False
    else:
        if mode not in _STO:
            raise ValueError(f"unknown mode {mode!r}")
        res = _STO[mode](M, N, p, seed)
        stochastic = True
    assert_energy_methods_agree(res)         # section 8 guarantee
    rec = res.to_dict()
    rec["stochastic"] = stochastic
    rec["seed"] = seed
    rec["p_success"] = p
    return rec


if __name__ == "__main__":
    mode = sys.argv[1]
    M = int(sys.argv[2])
    N = int(sys.argv[3])
    seed = int(sys.argv[4]) if len(sys.argv) > 4 else None
    p = float(sys.argv[5]) if len(sys.argv) > 5 else None
    print(json.dumps(run(mode, M, N, seed=seed, p=p)))
