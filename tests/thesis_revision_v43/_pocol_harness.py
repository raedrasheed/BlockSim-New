"""Deterministic in-process PoCol harness for Stage 3 tests.

Runs the real PoCol Consensus/BlockCommit event loop (no subprocess, no random
event-loop nondeterminism beyond the injected seed) and returns diagnostics.
Transactions are disabled (energy/round semantics do not depend on them), which
keeps the harness fast and free of Transaction-module coupling.
"""

import os
import sys
import functools

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))


def run_pocol(n_miners, sim_time=10000.0, seed=0, binterval=600.0,
              net_hps=141e12, eff=21.5, domain_factor=2.0, bdelay=0.42):
    from InputsConfig import InputsConfig as p
    from Models.PoCol.Node import Node
    from Models.PoCol.Consensus import Consensus
    from Models.PoCol.BlockCommit import BlockCommit
    from Statistics import Statistics
    from Event import Queue

    # configuration
    p.model = 3
    p.simTime = float(sim_time)
    p.Binterval = float(binterval)
    p.Bdelay = float(bdelay)
    p.Bsize = 1.0
    p.NetworkHashRate_Hps = net_hps
    p.MinerEfficiency_J_per_TH = eff
    p.HashPowerIsShare = True
    p.hasTrans = False
    p.Ttechnique = "Light"
    p.Runs = 1
    p.RandomSeed = seed
    p.PoCol_DomainFactor = domain_factor
    p.IdlePowerW = None
    p.IdlePowerRatio = None
    p.NODES = [Node(id=i, hashPower=1) for i in range(n_miners)]

    # reset global singletons
    Queue.event_list = []
    Queue._seq_counter = 0
    Statistics.reset()
    Statistics.reset2()

    Node.generate_gensis_block()
    BlockCommit.generate_initial_events()

    clock = 0.0
    processed = 0
    while not Queue.isEmpty() and clock <= p.simTime:
        e = Queue.get_next_event()
        clock = e.time
        BlockCommit.handle_event(e)
        Queue.remove_event(e)
        processed += 1

    Node.finalize_energy(p.simTime)
    Consensus.fork_resolution()
    Statistics.calculate()

    return dict(
        diag=Consensus.diagnostics(),
        transitions=list(Consensus.round_transitions),
        totalBlocks=Statistics.totalBlocks,
        mainBlocks=Statistics.mainBlocks,
        staleBlocks=Statistics.staleBlocks,
        energy_kwh=sum(float(getattr(nd, "energy_kwh", 0.0)) for nd in p.NODES),
        energylog_rows=len(Statistics.energyLog),
        processed_loop_events=processed,
        n_miners=n_miners,
    )


@functools.lru_cache(maxsize=32)
def cached_run(n_miners, sim_time=10000.0, seed=0):
    """Cache identical runs so multiple assertions reuse one execution."""
    return run_pocol(n_miners, sim_time=sim_time, seed=seed)
