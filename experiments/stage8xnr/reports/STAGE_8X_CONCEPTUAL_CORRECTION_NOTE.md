# Stage 8X — Conceptual Correction Note

**Subject:** scope and interpretation of the duplication metrics reported by Stage 8X.
**Status of Stage 8X:** frozen, not re-run, not modified, not retracted.
**Corrective experiment:** Stage 8X-NR (`experiments/stage8xnr/`), NR = Nonce Reuse.
**Date:** 2026-08-14.

This note is a **scope/interpretation correction**, not a defect report. Stage 8X's
exact-input duplication metric was implemented correctly and its numbers stand. What
follows records precisely which claim it does and does not support, and why a separate
experiment is required to address the nonce-domain claim.

---

## 1. What Stage 8X actually measured

Stage 8X (`experiments/stage8x/`, config hash
`b871c98ea1c612cdbd5a2223ff017610d908ae78fe08d509113f86983218cebf`, 300 primary physical
runs, 420 secondary runs) compared traditional competitive PoW (X-PW) against PoCol
disjoint allocation with post-range low power (X-PC), at N ∈ {100,…,500}, T = 10 000 s,
under a fixed Antminer S21 Pro profile (234 TH/s, 3510 W, 15 J/TH).

Its unit of account was the **candidate**, defined in
`experiments/stage8x/simulator/hashing.py` as the exact serialized hash input

```
header_bytes(template_id) ‖ extranonce (8 B, BE) ‖ nonce (4 B, BE)
candidate_index = extranonce · 2^32 + nonce
```

with identity `(template_id, candidate_index)`. Stage 8X therefore measured, exactly and
without approximation:

| Quantity | Definition in Stage 8X | Result |
|---|---|---|
| `W_total` | physical candidate evaluations | 2.34e20 … 1.17e21 |
| `W_unique` | measure of the union of scanned candidate intervals, **per template** | equals `W_total` |
| `W_duplicate` | `W_total − W_unique` | **0** for both X-PW and X-PC at every N |
| matched-template duplicate ratio (secondary) | same accounting under one common template | 0.3281 – 0.3313 |
| energy, retention, latency, low-power residency | state × power × time | saving 0.2050 – 0.2568 % at α = 0 |

The interval-union accounting (`ScanLedger`) is exact: total work is the sum of scanned
half-open interval lengths, unique work is the measure of their union per template, and
duplicate work is the difference. Nothing in this note casts doubt on those figures.

## 2. The exact-input duplicate metric remains valid

The claim Stage 8X supports is:

> Under per-miner distinct templates, no two candidate evaluations share the same
> complete serialized hash input, so exact candidate-input duplication is zero; under a
> forced common template with uncoordinated search, roughly one third of evaluations are
> exact duplicates.

This is correct as stated and is confirmed by dedicated tests in
`experiments/stage8x/tests/`. The secondary matched-template ratio of ≈ 0.328–0.331 also
matches its independently derived closed form (0.3660–0.3675) to within the sampling and
epoch-boundary effects documented in the Stage 8X results report. **No Stage 8X
exact-input number is withdrawn.**

## 3. What Stage 8X did not measure adequately

Stage 8X did report a nonce-value quantity — `distinct_nonce_values()` and a
`nonce_value_reuse_ratio` column in Table B — and it did state in the results report that
"nonce-value reuse is not exact-input duplication". Two things were nevertheless
inadequate for the researcher's original nonce-domain claim:

**(a) Only one scope was instrumented, and it saturates.** The nonce-value reuse ratio was
computed once per run, over the whole 10 000 s horizon. At 234 TH/s a single miner
evaluates 2^32 candidates in

```
τ_sweep = 2^32 / 2.34e14 = 1.8355e-5 s = 18.355 µs
```

so every miner traverses the entire 32-bit nonce field 3.269e7 times per 600 s round and
5.448e8 times per run. Consequently `distinct_nonce_values` was exactly 2^32 and the
reported reuse ratio was 0.999999999… for **every** protocol, including PoCol. A metric
that returns the same saturated value for all arms cannot discriminate between them and
therefore cannot answer the question that motivated it.

**(b) The disjointness PoCol was verified on was not disjointness of the 32-bit nonce
field.** Stage 8X's PoCol partitioned the *candidate index* domain
`S_N = H_N · 600 s = N · 1.404e17`, giving each miner a slice of L = 1.404e17 candidate
indices. Since L ≫ 2^32, each PoCol miner's slice spans 3.269e7 complete traversals of the
nonce field. PoCol's ranges were disjoint in `(extranonce, nonce)` space — which is what
makes the zero-exact-duplicate result true — but they were **not** disjoint in `nonce32`.
Stage 8X therefore never tested the proposition
`R_i ∩ R_j = ∅ over nonce32 within a common template epoch`.

Neither point makes a Stage 8X number wrong. Both mean that a distinct measurement is
missing.

## 4. Why nonce-value reuse is a separate metric

The block-header nonce is a 32-bit unsigned field, so the explicit header-nonce domain for
a given header/template realization has exactly 2^32 values. Two miners may evaluate the
same numerical value `nonce_A = nonce_B`. If their headers differ,
`(Header_A, nonce_A) ≠ (Header_B, nonce_B)` as hash inputs. Hence

```
nonce-value reuse   ≠   exact candidate-input duplication
```

The two metrics answer different questions and can take opposite values on the same run:

| | nonce-value reuse | exact-input duplication |
|---|---|---|
| identity used | `nonce32` | `(template_id, nonce32)` |
| distinct-template PoW | large | zero |
| common-template PoW | large | large |
| PoCol within one epoch | zero (to be verified) | zero |

`ρ_nonce > 0` together with `ρ_exact ≈ 0` is not a contradiction; it is the precise content
of the conceptual model. Stage 8X collapsed the first of these into a saturated global
counter, which is why the distinction, although stated in prose, was never demonstrated
numerically.

The corollary that must travel with the metric is equally important: 2^32 is **not** the
whole search capability of a miner. A miner extends its search past the header nonce by
changing coinbase/extranonce data, which changes the Merkle root and therefore produces a
new header template. Nonce-domain exhaustion is a *template-renewal event*, not a search
limit.

## 5. Why Stage 8X-NR is required

To answer the original claim, an experiment must:

1. represent the header nonce explicitly as a 32-bit field, `S = 2^32`, and keep the
   expanded search coordinate (`extranonce`, template epoch) separate from it;
2. instrument nonce-value reuse at **scopes that do not saturate** — per template epoch and
   per sub-sweep window — in addition to the round and global-run scopes;
3. separate three protocol families that Stage 8X conflated into two:
   conventional independent-template PoW (XNR-PW-CONV), matched common-template PoW
   (XNR-PW-MT), and PoCol disjoint nonce allocation over exactly 2^32 (XNR-PC);
4. vary the traversal policy (zero-start vs independently offset), because a nonce-reuse
   number derived from one traversal rule cannot be generalized to all PoW implementations;
5. carry nonce-value reuse, exact-input duplication, physical evaluations and electrical
   energy as **four separate columns** in every table, so that none is ever substituted for
   another.

None of this can be obtained by re-analysing Stage 8X outputs, because the required
quantities were never recorded at the required scopes. It also cannot be obtained by
modifying Stage 8X: Stage 8X is frozen and its artifacts are inside the protected baselines
of Stage 8Y (`2d7344a1…`) and Stage 8Z (`b2a68047…`), so any edit would invalidate two
later stages. Stage 8X-NR is therefore a **new, isolated experiment** under
`experiments/stage8xnr/`, with its own configuration, its own 30 fresh paired seeds, and its
own freeze.

## 6. Which Stage 8X conclusions remain unchanged

Unchanged and still citable exactly as reported:

* Zero exact candidate-input duplication for both X-PW and X-PC at every N (Table B).
* Matched-template exact-duplicate ratio 0.3281–0.3313 (Table H) and the associated block
  loss relative to distinct-template PoW.
* Energy saving 0.2050–0.2568 % at α = 0, halving to 0.1025–0.1284 % at α = 0.50 (Table C).
* Low-power residency `F_low` = 0.00205–0.00257 (Table F).
* Block retention 0.9915–0.9985 and latency ratio 0.9829–1.0192 (Table D).
* The difficulty derivation `D_N = H_N · I_target / 2^32` and the empirical calibration
  (pooled mean PoW interval 603.6 s against a 600 s nominal target).
* The central Stage 8X conclusion that PoCol's energy saving in that configuration is
  small, and is attributable to measured low-power residency rather than to duplication
  avoidance.

Nothing in Stage 8X-NR can overturn these, because they are exact-input and energy
quantities and Stage 8X-NR measures a different, additional quantity on a different domain.

## 7. Wording to narrow in the thesis

The following substitutions should be applied wherever Stage 8X is discussed. The left
column is not false, but it is broader than the evidence.

| Narrow this | To this |
|---|---|
| "PoCol eliminates duplicate work / redundant hashing" | "PoCol performs zero exact candidate-input duplication; whether it eliminates *nonce-value* overlap is a separate question, addressed in Stage 8X-NR." |
| "Traditional PoW miners all search the same space, so they repeat each other's work" | "Traditional PoW miners search the same 32-bit header-nonce value domain, but under distinct templates, so equal nonce values are not equal hash inputs." |
| "the nonce space" (unqualified) | either "the 32-bit block-header nonce-value domain (2^32)" or "the candidate space `(template, extranonce, nonce)`" — never both meanings under one term. |
| "nonce-value reuse ratio ≈ 1.0 for every protocol" (Stage 8X Table B) | "run-scoped nonce-value coverage saturates at 2^32 for every protocol at S21 Pro rates; the discriminating scope is the template epoch." |
| "PoCol assigns each miner a disjoint nonce range" | "Stage 8X PoCol assigns each miner a disjoint range of *candidate indices* `(extranonce, nonce)`. Disjoint allocation over the 32-bit header-nonce field itself is Stage 8X-NR's XNR-PC." |
| "duplicate work wastes energy" | "duplicate work is wasted *hashing*; it changes electrical energy only through a change in active power-time, which must be measured separately." |

Three phrasings must not appear at all, in Stage 8X discussion or elsewhere:
"PoW miners always hash exactly the same data"; "every repeated nonce is a duplicate hash";
"the Bitcoin mining search space is only 2^32". The safe formulation is: *the explicit
block-header nonce field is 32-bit, and miners may reuse the same numerical nonce values
while operating on different header templates.*

---

## Appendix — audit trail of the Stage 8X implementation

Read-only audit performed for this note; no Stage 8X file was modified.

| Checked | File | Finding |
|---|---|---|
| Candidate identity | `simulator/hashing.py::candidate_bytes` | `(template_id, extranonce, nonce)` serialized; identity is `(template_id, candidate_index)`. Correct. |
| Extranonce width | `simulator/hashing.py::EXTRANONCE_BITS` | 64 bits, documented as a serialization-width choice needed because `S_N > 2^64` for `N ≥ 132`. Correct, but it is why `nonce32` disjointness was never in scope. |
| Duplicate accounting | `simulator/hashing.py::ScanLedger` | exact interval-union per template; no approximation. Valid. |
| Nonce-value counter | `ScanLedger.distinct_nonce_values` | correct as written — it short-circuits to 2^32 for any interval of length ≥ 2^32, which is every operational interval. Saturated by construction, hence uninformative. |
| PoCol partition | `config/difficulty.py::disjoint_ranges` | tiles `[0, S_N)` exactly with `L = 1.404e17` per miner. Disjoint in candidate-index space, **not** in `nonce32`. |
| Difficulty | `config/difficulty.py::derive` | `D_N = H_N·I/2^32`, `q_N = 1/(H_N·I)`, `target = 2^256·q_N`. Re-derived independently in Stage 8X-NR §11 and confirmed consistent with the simulator's probability semantics. |
| Winner oracle | `simulator/hashing.py::sample_winners` | Poisson(q·M) winners at uniform positions, consistent across miners so shared candidates share outcomes. Valid; reused conceptually, not by import modification, in Stage 8X-NR. |
