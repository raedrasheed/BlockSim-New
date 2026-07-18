"""Shared experiment harness (Phases B4/B6).

Runs ONE (protocol, n_miners, seed) simulation in a fresh interpreter using the
single shared ScenarioConfig (Models/scenario.py), the corrected wall-clock
energy meter (B1), round/stale semantics (B2), and target-based success model
(B5). Prints one JSON metrics record.

CLI:  python experiments/run_scenario.py <PoW|PoCol> <n_miners> <seed>
"""
import os
import sys
import json
import random

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


def run(protocol, n, seed, sim_time=None):
    random.seed(seed)  # single stream seeds Network, Consensus, Transaction, Scheduler

    from InputsConfig import InputsConfig as p
    from Models.scenario import ScenarioConfig, apply_to
    sc = ScenarioConfig(n_miners=n, seed=seed)
    if sim_time is not None:
        object.__setattr__(sc, "simTime", float(sim_time))
    apply_to(p, sc, protocol)

    if protocol == "PoW":
        from Models.Bitcoin.Node import Node
        from Models.Bitcoin.BlockCommit import BlockCommit
        from Models.Bitcoin.Consensus import Consensus
    else:
        from Models.PoCol.Node import Node
        from Models.PoCol.BlockCommit import BlockCommit
        from Models.PoCol.Consensus import Consensus
    from Models.Incentives import Incentives
    from Models.Transaction import LightTransaction as LT
    from Statistics import Statistics
    from Event import Queue

    # reset shared global state (defensive; fresh process anyway)
    Queue.event_list = []; Queue._seq_counter = 0
    Statistics.totalBlocks = 0
    if hasattr(Consensus, "_closed_rounds"):
        Consensus._closed_rounds = set(); Consensus.round_id = 0
        Consensus.total_exhausted_rounds = 0; Consensus.active_parent_id = None

    p.NODES = [Node(id=i, hashPower=1) for i in range(n)]

    # invariants (B1)
    agg_h = sum(nd._effective_hashrate_hps() for nd in p.NODES)
    for nd in p.NODES:
        nd.begin_mining(0.0)
    agg_p = sum(nd.power_watts for nd in p.NODES)

    LT.create_transactions()
    Node.generate_gensis_block()
    BlockCommit.generate_initial_events()
    clock = 0.0
    while not Queue.isEmpty() and clock <= p.simTime:
        ev = Queue.get_next_event(); clock = ev.time
        BlockCommit.handle_event(ev); Queue.remove_event(ev)
    Node.finalize_all(p.simTime)
    Consensus.fork_resolution()
    Incentives.distribute_rewards()
    Statistics.calculate()

    # ---- metrics ----
    chain = [b for b in getattr(Consensus, "global_chain", [])]
    ts = sorted(float(getattr(b, "timestamp", 0.0)) for b in chain[1:])  # skip genesis
    if len(ts) >= 2:
        accepted_interval = (ts[-1] - ts[0]) / (len(ts) - 1)
    elif len(ts) == 1:
        accepted_interval = ts[0]
    else:
        accepted_interval = float("nan")
    main_blocks = Statistics.mainBlocks
    total_blocks = Statistics.totalBlocks
    created_interval = (p.simTime / total_blocks) if total_blocks > 0 else float("nan")
    confirmed_tx = sum(len(getattr(b, "transactions", []) or []) for b in chain[1:])
    energy = Statistics.totalEnergy_kWh
    co2 = Statistics.totalCO2_kg
    active_time = sum(getattr(nd, "cumulative_active_time", 0.0) for nd in p.NODES)
    total_hashes = sum(getattr(nd, "cumulative_hashes", 0.0) for nd in p.NODES)

    from Models.scenario import ScenarioConfig as _SC
    rec = {
        "protocol": protocol, "n_miners": n, "seed": seed,
        "config_hash": sc.config_hash(),
        "sim_time": p.simTime,
        "aggregate_hashrate_THs": agg_h / 1e12,
        "aggregate_power_W": agg_p,
        "energy_kWh": energy,
        "co2_kg": co2,
        "created_blocks": total_blocks,
        "accepted_main_blocks": main_blocks,
        "stale_blocks": Statistics.staleBlocks,
        "stale_rate_pct": Statistics.staleRate,
        "accepted_block_interval_s": accepted_interval,
        "created_block_interval_s": created_interval,
        "throughput_tx_per_s": confirmed_tx / p.simTime if p.simTime else float("nan"),
        "confirmation_time_6blk_s": 6.0 * accepted_interval if accepted_interval == accepted_interval else float("nan"),
        "energy_per_accepted_block_kWh": energy / main_blocks if main_blocks else float("nan"),
        "energy_per_tx_kWh": energy / confirmed_tx if confirmed_tx else float("nan"),
        "total_hashes": total_hashes,
        "active_mining_time_s": active_time,
        "exhausted_rounds": int(getattr(Consensus, "total_exhausted_rounds", 0)),
    }
    return rec


if __name__ == "__main__":
    proto = sys.argv[1]; n = int(sys.argv[2]); seed = int(sys.argv[3])
    st = float(sys.argv[4]) if len(sys.argv) > 4 else None
    print(json.dumps(run(proto, n, seed, sim_time=st)))
