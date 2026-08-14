# STAGE 8X — LIMITATIONS

These limitations qualify every quantitative statement in
`STAGE_8X_RESULTS_REPORT.md`. They are not caveats added after the fact: items 1-9 were
required by the experimental protocol and items 10-14 were identified during the audit
and Pilot, before the primary matrix was executed.

---

## Required limitation statements

**1. The S21 Pro active specifications anchor the active mining model; the low-power
percentages are experimental sensitivity assumptions.**
234 TH/s, 3510 W and 15 J/TH are the official Bitmain nominal specification for the
Antminer S21 Pro, and they are internally consistent (234 x 15 = 3510). The values
`P_low = alpha x 3510 W` for `alpha ∈ {0, 0.10, 0.25, 0.50}` are **not** vendor figures.
Bitmain does not publish an S21 Pro low-power operating state of any kind, and none of
LP0/LP10/LP25/LP50 should be described as a Bitmain mode. LP0 (0 W) is an idealized
lower bound that no real ASIC achieves while remaining responsive to a wake-up event;
LP10, LP25 and LP50 are non-zero assumptions chosen to span a plausible range, not
measurements.

**2. Stage 8X is a simulator experiment and does not demonstrate identical behaviour on
physical S21 Pro hardware.**
No physical device was measured. Transition latency between power states, thermal
behaviour, PSU efficiency curves, ramp-up time to full hash rate after a wake-up, and
firmware constraints are all absent from the model. A real deployment would have to
demonstrate that a device can enter and leave a low-power state within the ~2-3 s
episodes observed here without losing hash rate or damaging the hardware; nothing in
this experiment establishes that.

**3. PoCol energy savings arise only when reduced useful work translates into reduced
active-power residency.**
The entire measured effect is `F_low x (1 - alpha)`. If a device cannot actually reduce
its draw while idle — or cannot do so within the episode durations observed — the
saving is zero regardless of how the nonce space is allocated.

**4. Duplicate-work reduction is not itself equal to energy reduction.**
These are distinct quantities and are reported separately. In the primary comparison
there was *no* duplicate work to remove (both protocols recorded exactly zero exact-input
duplicates), yet a small energy reduction still occurred, caused entirely by low-power
residency. Conversely, the secondary common-template comparator shows large duplicate
work whose removal would not by itself reduce electrical draw — it changes how much
useful search the same energy buys. Neither direction licenses inferring electricity
from a duplicate-hash percentage.

**5. Difficulty is network-size coupled to preserve a common nominal PoW block-interval
reference.**
`D_N = H_N x 600 / 2^32`. Results at different N are therefore not free of this
coupling: N changes the population and the difficulty together, holding the matched PoW
service target fixed. Absolute energy figures scale with N by construction.

**6. PoCol and PoW use the same target within each N.**
A single `D_N` is computed per N and passed to both protocols. PoCol was never
recalibrated to force its block interval to match PoW's, so its (small) block-production
and latency differences are outcomes rather than controlled quantities.

**7. Results depend on the simulator's propagation, workload, template, hardware-state
and nonce-domain assumptions.**
Specifically: gossip delay is `Exp(mean 0.42 s)` broadcast to all peers with no topology,
bandwidth limit, or verification cost; there is no transaction workload; templates are
abstracted to a byte prefix; only two power states exist; and the epoch domain is
`S_N = H_N x 600 s`. The epoch-domain choice is consequential and is swept in a declared
secondary analysis, which shows that a smaller allocation raises `F_low` substantially
**and** costs block production — the primary figure is not the maximum obtainable, nor
is it a worst case.

**8. Any common-template PoW comparator must not be misrepresented as Bitcoin mainnet
behaviour.**
The secondary comparator `X-PW-MATCHED-TEMPLATE` forces every miner onto one shared
template with random start offsets. Real Bitcoin miners build distinct templates with
their own coinbase, so mainnet does not exhibit the ~33 % exact duplicate work this
comparator shows. It is a controlled diagnostic isolating search redundancy, not a
model of deployed mining.

**9. The experiment evaluates a controlled protocol mechanism, not real-world Bitcoin
economics.**
There is no coin price, no reward, no fee market, no hardware capital cost, no
electricity price, no miner entry/exit, and no difficulty retargeting over time.
Nothing here speaks to whether a network would adopt PoCol or what it would cost.

---

## Additional limitations identified during the audit and Pilot

**10. The traditional-PoW comparator is favourable to PoW by construction, and this
drives the primary result.**
A PoW miner rolls its own extranonce locally and instantly at zero cost, so it is ACTIVE
for the entire horizon and never idles. A PoCol miner cannot do this: the template must
be *common* for disjointness to be verifiable, so it must wait for network agreement and
propagation of the refreshed template. That waiting is the only source of low-power time
in the primary experiment. A PoCol implementation that pipelined the next epoch's
allocation would eliminate the waiting — and with it the entire measured saving.

**11. Homogeneous miners with equal disjoint ranges complete their ranges
simultaneously.**
Because every miner has identical capacity and an identical range, the network exhausts
the epoch domain at the same instant the individual miner does. Low-power residency is
therefore bounded by agreement and propagation latency rather than by spare capacity.
Heterogeneous hardware or unequal allocation would change this qualitatively, and
Stage 8X does not test either.

**12. The low-power effect is small in magnitude but extremely consistent, which makes
p-values a poor guide.**
Paired energy differences at LP0 are on the order of 0.2 %, yet every one of the 30
paired differences at every N has the same sign, so p-values reach 1e-19 and Cohen's
`d_z` reaches ~-4.9. Statistical significance here reflects the near-deterministic
pairing, not practical importance. The magnitude and its confidence interval, not the
p-value, are the quantities to read.

**13. The horizon is short relative to the block interval.**
`T = 10 000 s` at a 600 s target yields ~17 accepted blocks per run. Per-run block
counts are therefore coarse (Poisson noise of order sqrt(17) ≈ 4), which is why the
block-production differences are not significant after Holm correction. Thirty paired
seeds per cell mitigate but do not remove this. Latency percentiles beyond the median
are correspondingly noisy.

**14. Fork/stale behaviour is effectively untested.**
With a 0.42 s propagation mean against a 600 s interval, zero stale blocks occurred in
all 300 primary runs. The stale-rate metric is therefore reported as zero rather than
measured, and the experiment says nothing about how either protocol behaves under
propagation delays comparable to the block interval.

**15. Stage 6A / 8S / 8U are not present in this repository.**
No artifacts, seed registries or nonce-domain settings from those stages exist in-tree,
so the requirement not to reuse them is satisfied trivially rather than by comparison.
The prohibited constants (141 TH/s, 21.5 J/TH) *are* present in `InputsConfig.py`, and
are avoided by Stage 8X never importing that module. Cross-stage comparisons with those
experiments cannot be made from this repository alone.

**16. The winner-oracle abstraction is exact in law, not in bytes.**
Acceptance is modelled as an i.i.d. Bernoulli(q) field over candidate indices, validated
against real double SHA-256 at a tractable target. This is mathematically equivalent to
enumerating candidates, but it does not exercise SHA-256 at operational scale, so it
cannot surface any hypothetical structure in the hash function itself.
