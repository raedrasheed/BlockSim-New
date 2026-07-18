# Hash-Rate-Aware Difficulty — Limitations

**Branch:** `claude/pocol-hashrate-aware-difficulty`
Read before quoting any number from `results/hashrate_aware_difficulty/`.

1. **The duplicate baseline is a constructed worst case.** Real Bitcoin miners
   differentiate headers (extranonce/Merkle/timestamp); the network does not
   scan one shared order N times. DUP's ~0 blocks under equal targets shows the
   *cost of hypothetical full duplication*, not real PoW behaviour.
2. **"Difficulty increases with miners" holds only under H2.** Under fixed
   aggregate hash rate (H1) difficulty must stay constant; asserting N-scaling
   there is the exact error this experiment removes.
3. **Idle power 0 and no power-down policy.** In this continuous design miners
   are ~100 % ACTIVE, so total energy = P_agg × sim for every protocol — there
   is no energy saving here by construction. Energy-saving claims belong to the
   separate fixed-slot experiments with explicit power-down (Findings 3–4), not
   to this one.
4. **The exhausted-template overhead (~7 % extra hashes per block at
   budget = 2T) depends on the domain time budget** — a modelling knob,
   disclosed per run, identical across compared protocols.
5. **D3 retargeting oscillates** (clamped feedback on small windows); final
   difficulty lands ~1.2× the analytic ideal on short horizons. Window 10 is a
   test configuration; Bitcoin-like 2016-block windows need far longer horizons.
6. **Security is not analysed.** Accumulated work per block and actual hashes
   per block are *disclosed*, but no claim about attack cost, reorg resistance,
   or incentive compatibility is made or implied. Equal timestamps ≠ equal
   security.
7. **No transaction-level dynamics** (fees, mempool, propagation); throughput
   equality is by identical fixed payloads.
8. **PoCol coordination costs** (range assignment, template distribution) are
   not charged.
