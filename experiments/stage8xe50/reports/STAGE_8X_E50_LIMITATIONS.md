# Stage 8X-E50 — Limitations

1. **The same-template control is not Bitcoin mainnet.** Real mining assigns
   distinct extranonce spaces per worker; E50-MT100's (N−1)/N duplication does
   not occur in deployed practice. Every E50 saving is comparator-specific.
2. **Common-template saturation creates the coordination opportunity.** The
   entire recoverable waste exists because one template holds only 2^32
   distinct inputs; the measured savings are properties of that geometry.
3. **Low-power states are sensitivity assumptions** (P_low = α·P_active), not
   Bitmain-certified S21 Pro modes; α = 0 is an idealized lower bound.
4. **No physical hardware validation** — modeled power/time only.
5. **Homogeneous fleet.** Identical units make retention ∝ active fraction and
   duty exactly fair; heterogeneous fleets would change both.
6. **Fixed propagation assumptions.** Instant propagation; rounds end at the
   first accepted block; no orphan races.
7. **Active subsets reduce instantaneous hashrate.** PoCol at fraction A runs
   the network at k·h; against the conventional reference this costs exactly
   fraction A of blocks — visible in §6 of the results report.
8. **Unique coverage is not network security.** Matching MT100's unique-input
   rate says nothing about attack cost; a network at k·h is cheaper to attack
   than one at N·h. No security claim is made.
9. **Template-renewal semantics materially affect results.** The matched rule
   (epoch = assigned traversal complete) drives PoCol's k·h unique rate; a
   fixed-length epoch rule would instead cap PoCol coverage at A of MT100.
   The rule is documented and machine-checked; conclusions do not transfer to
   other renewal semantics.
10. **Full-domain saturation is specific to the 32-bit header-nonce geometry**
    at S21 Pro rates (18.355 µs per sweep).
11. **The observed >50 % savings (α ≤ 0.25) are comparator-specific**; at
    α = 0.50 the maximum is 45.0 % on the frozen fraction grid.
12. **Energy-per-block differs conceptually from fixed-horizon saving.** Here
    they agree in direction; in general a total-energy saving with collapsing
    block output would raise energy per block — checked and absent (PoCol's
    E/block equals CONV100's exactly).
13. **MT100 block statistics are sparse** (0–3 blocks per 30-run cell), so
    pooled retention/latency denominators carry wide Poisson uncertainty;
    counts are printed beside every ratio. The direction (PoCol ≫ MT100) is
    unambiguous — predicted rates differ by factors of 10–250.
14. **Rotation at template cadence implies microsecond-scale power cycling**
    of ASICs, which real hardware cannot do; the α model prices low-power time
    but not transition costs. Coarser rotation would preserve every energy and
    coverage number while reducing transition counts.
