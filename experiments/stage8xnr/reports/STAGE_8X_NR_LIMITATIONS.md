# Stage 8X-NR — Limitations

1. **The matched-template (MT) arms are controlled comparators, not Bitcoin
   mainnet mining.** Real mining infrastructure assigns distinct
   extranonce/coinbase spaces to workers precisely so that a common template is
   never searched redundantly. The MT retention collapse (~1/N) quantifies what
   uncoordinated common-template search *would* cost over a 2^32 domain; it is
   not a claim about deployed Bitcoin.

2. **The traversal models are two of many.** Zero-start and independently offset
   sequential traversal bracket a synchronized worst case and a conservative
   independent case; real firmware may use other orders (e.g. hardware-parallel
   lane striding). Round-scope conclusions are traversal-insensitive here
   (saturation), but sub-sweep numbers are policy-specific and are labelled so.
   The optional pseudorandom-permutation policy (brief §9 C) was not implemented;
   at S21 Pro rates any per-tick permutation still saturates the domain every
   18.4 µs, so it would change only the sub-sweep diagnostics.

3. **Instant propagation and no network effects.** Rounds end at the first
   accepted block; no propagation delay, no orphan races except the MT-ZERO
   synchrony ties, no difficulty retargeting within a run.

4. **Winner attribution in CONV is uniform** across miners (all have equal hash
   rate and fresh templates); this affects no reported metric.

5. **The Bernoulli-field abstraction** is exact for the statistics reported
   (identical to Stage 8X's winner-oracle equivalence, validated there by real
   double-SHA-256 Monte Carlo at easy targets), but no actual SHA-256 is executed
   in the operational runs.

6. **Low-power findings are configuration-specific.** With homogeneous hardware
   and ranges equal ±1 nonce, PoCol's post-range residency over a 2^32 domain is
   the sub-microsecond straggler gap (≤ 7.1e-8 of miner-time). This does NOT
   contradict Stage 8X, whose PoCol partitions a 600 s candidate-index domain
   (F_low ≈ 0.002), nor Stage 8Y, whose savings come from participation
   scheduling. The three experiments measure different allocation geometries;
   none of their numbers transfer to the others.

7. **Energy α-cases remain labelled sensitivity assumptions** (P_low = α·P_active),
   not vendor-certified S21 Pro modes.

8. **MT latency statistics rest on 1–2 blocks per 30-run cell** (expected: MT
   rounds are ~N·600 s vs a 10 000 s horizon). They are reported with run counts
   and excluded from any strong claim.

9. **Cross-N interval comparisons are not independent** because the paired
   round-process stream is shared across N (documented in METHODS §5); interval
   contrasts are made across arms only.

10. **30 seeds bound the stochastic quantities' precision** (e.g. MT observed
    blocks 2/30 vs expected 4.6 at N=100 is within Poisson sampling error);
    deterministic quantities (reuse fractions, overlaps, energy identities) are
    exact and do not carry sampling error.
