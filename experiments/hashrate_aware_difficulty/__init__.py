"""Hash-rate-aware difficulty experiment (branch: pocol-hashrate-aware-difficulty).

Replaces miner-count-dependent nonce-domain calibration with a scientifically
correct difficulty model:

    W_expected = H_network * T_target          (T_target = 600 s)
    p_success  = 1 / W_expected
    target     = floor(2^256 / W_expected) - 1  (clamped to 256-bit range)
    E[T_block] = W_expected / H_network ~= 600 s

Critical rule: difficulty is NEVER multiplied by N unconditionally — it follows
AGGREGATE hash rate. Under H1 (fixed aggregate) difficulty is constant in N;
under H2 (fixed per-miner hardware) D_N = N * D_1 only because H_network = N*H_i.

Blocks commit IMMEDIATELY at discovery (average-interval design); the old
fixed-slot experiment (experiments/fixed_600s_pocol/) is preserved unchanged.

Protected result dirs (byte-identical): results/corrected/,
results/nonce_partition_worst_case/, results/continuous_distributed_effort/,
results/mainsim_idle_after_range/, results/fixed_600s_pocol/.
"""
