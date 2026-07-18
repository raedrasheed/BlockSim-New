"""Fixed 600-second round experiment (branch: pocol-fixed-600s-distributed-nonce).

A controlled fixed-slot simulation in which PoW and PoCol commit exactly one
accepted block every 600 seconds in the primary deterministic experiment.
PoCol physically distributes the finite nonce domain among miners; each miner
evaluates only its assigned subrange, idles the moment it exhausts that range or
the solution is found, and all miners wait IDLE until the round boundary where
the buffered block is committed.

Energy = integral of per-state power over wall-clock time. Never divided by N.

Protected (byte-identical, never touched):
    results/corrected/
    results/nonce_partition_worst_case/
    results/continuous_distributed_effort/
    results/mainsim_idle_after_range/

See docs/FIXED_600S_POCOL_METHODOLOGY.md.
"""
