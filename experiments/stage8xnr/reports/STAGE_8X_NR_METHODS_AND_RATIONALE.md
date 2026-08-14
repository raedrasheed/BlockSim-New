# Stage 8X-NR — Methods and Rationale

## 1. Corrected nonce semantics

The explicit block-header nonce is a 32-bit unsigned field; its value domain is
`S = 2^32` (values 0 … 2^32−1). This is **not** the entire search capability of a
miner: search extends past the header nonce through extranonce/coinbase changes that
alter the Merkle root and hence produce a new header template. The simulator
represents this exactly:

```
position  = template_epoch · 2^32 + nonce32          (internal expanded coordinate)
nonce32   = position mod 2^32                        (protocol nonce, always 32-bit)
candidate = (template_id, nonce32)                   (exact-input identity)
```

Nonce-value-reuse counting uses `nonce32` only; exact-input counting uses
`(template_id, nonce32)`. The two are never conflated (metric layer and Tests 6–7).

## 2. Event abstraction and its exactness

Work is counted in integer ticks: 1 tick = one candidate evaluation per miner =
1/h s with h = 2.34e14 evals/s (S21 Pro). The double-SHA acceptance field is
i.i.d. Bernoulli(q) across **distinct** inputs; re-evaluating an input reproduces
its outcome. Hence:

* the number of distinct inputs up to the first winner is Geometric(q), sampled
  exactly per round;
* the winning value is uniform on the winning template's 2^32 domain;
* each arm's round length in ticks follows deterministically from its traversal
  geometry (below), making every count an exact integer. The two engine
  identities — Σ_state t = T per miner, and W_total = Σ evaluations = h·t_active —
  hold with zero error by construction and are asserted per run.

Distinct-input throughput, the quantity that sets the block rate:

| arm | distinct-input rate | round ticks to a winner |
|---|---|---|
| XNR-PW-CONV-* | N·h (per-miner templates: every evaluation fresh) | ⌈g/N⌉ |
| XNR-PW-MT-*   | h (one common 2^32 domain per S-tick epoch)       | F·S + first-hit(x*) + 1 |
| XNR-PC        | N·h (disjoint allocation: every evaluation fresh) | F·hi + (x*−start_owner) + 1 |

with g ~ Geometric(q), F = ⌊(g−1)/2^32⌋ failed epochs, x* the uniform winning
value, first-hit(x*) = min_i (x* − start_i) mod 2^32 (0 = x* for zero-start), and
hi = ⌈2^32/N⌉ the longest PoCol range. The MT rate h is not an assumption — it is
the theorem that a common 2^32 domain contains only 2^32 distinct inputs per
epoch, however many miners sweep it.

## 3. Difficulty

Re-derived (not inherited): q_N = 1/(H_N·600), D_N = H_N·600/2^32,
target = 2^256·q_N, with H_N = N·h. One D_N per N for all five arms; q·D·2^32 = 1
is asserted in test. The empirical CONV pooled mean interval is the calibration
check (586.9 s over 2420 blocks, within 1.1 SE of 600 s).

## 4. Nonce-reuse measurement

All per-scope quantities are computed with exact cyclic interval arithmetic
(`noncedomain.py`): a miner's evaluations over any window are f full sweeps plus
one partial arc; unions, intersections, multiplicity profiles and pairwise
overlaps of arcs are computed as integers, never materialising 2^32 booleans.
The interval model is validated against explicit set enumeration on toy cyclic
domains (Test 10) and the occupancy formula E[U] = S(1−(1−1/S)^m) is validated by
enumeration on toy domains (Test 9) and used only where its
sampling-with-replacement assumption holds; sequential arcs use interval
geometry instead (brief §18–19).

Scopes and reset points: NR-round (reset at every round boundary; the primary
scientific scope), NR-template-epoch (reset at every template renewal),
NR-global-run (diagnostic, never reset), NR-subsweep (first ⌊S/2N⌋ ticks of each
round — the sub-saturation diagnostic that keeps traversal policies
distinguishable). Both repetition-based (C−U) and cross-miner (M_≥2, m_max,
O_ij) families are reported; they deliberately differ for PoCol, whose miners
re-sweep their own ranges across epochs (repetition) but never share a value
within an epoch (no cross-miner reuse).

## 5. Statistical design

30 fresh paired seeds (SHA-256-derived, verified disjoint from the Stage
8X/8Y/8Z registries). Pairing is by common random numbers: the rounds stream,
winning-value stream and attribution stream are consumed identically by every
arm, so paired differences isolate the protocol effect. Two consequences are
documented rather than hidden: (i) CONV and PC block times are nearly identical
per seed by construction; (ii) because g scales exactly with N, interval draws
coincide across N as well — interval statistics are therefore compared across
arms, not across N. Cells whose paired differences are deterministic
(zero or constant) are reported as magnitudes with the test marked "degenerate"
instead of manufacturing p ≈ 0 (brief §25).

## 6. Energy model

E = Σ_i P_active·t_active,i + α·P_active·t_low,i with P_active = 3510 W and
α ∈ {0, 0.10, 0.25, 0.50} as labelled sensitivity assumptions (not vendor modes).
The four α cases are derived observations from each PoCol run's state ledger, not
separate simulations. PoW arms have t_low = 0 by definition of the modeled
protocol (continuously active until round end). Nonce-value reuse enters the
energy model **only** through t_active — this is exactly the proposition the key
hypothesis test verifies (brief §17).

## 7. Why the MT comparator is fair but not Bitcoin

XNR-PW-MT holds the template common across miners to isolate what uncoordinated
search does when nonce values *and* template coincide. Real pooled/solo Bitcoin
mining assigns distinct extranonce spaces per worker, which is exactly why its
duplication is negligible in practice; MT is a controlled comparator for the
coordination question, and is labelled as such everywhere.
