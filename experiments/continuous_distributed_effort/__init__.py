"""Continuous distributed-effort experiment.

A new, explicitly bounded experiment (branch: pocol-continuous-distributed-effort).
It does NOT modify results/corrected/ or results/nonce_partition_worst_case/.

Finding 3: under a common-template duplicate baseline, fixed-slot scheduling, and
actual transition to lower-power IDLE/SLEEP states after assigned work completes,
disjoint nonce allocation reduces active-miner time and energy by (1-q)(1-1/N),
where q = P_idle/P_active. The saving is zero under IMMEDIATE_RESTART / q=1.

See docs/CONTINUOUS_DISTRIBUTED_EFFORT_METHODOLOGY.md and _LIMITATIONS.md.
"""
