# Stage 5B1 — Range Allocation Decoupled from Hash Rate

**Blocker 1 (Stage 5A):** range size was coupled to hash rate, so a heterogeneous
hash-rate distribution silently changed the nonce partition, conflating two
independent design choices. Stage 5B1 separates them.

## 1. Two independent quantities

| Quantity | Symbol | Set by | Engine field |
|----------|--------|--------|--------------|
| Hash rate | `rate_i = share_i · H_net` | `hash_rate_distribution` | `_shares` → `rates` |
| Nonce range | `L_i` (length of `[a_i, b_i]`) | `allocation_policy` | `allocate_equal` / `allocate_weighted` |

The two are now chosen by **different** configuration fields and combined only in
the discovery/energy step. A miner's completion time is `τ_i = L_i / rate_i`, so
range and rate interact *only there*.

## 2. `allocate_equal(S, n)` — rate-independent

`base, rem = divmod(S, n)`; the first `rem` miners get `base+1`, the rest `base`.
Exact cover (`Σ L_i = S`), no overlap, **independent of hash rate**. Two
configs that differ only in `hash_rate_distribution` produce the *identical*
equal partition (validated: check `B1`).

## 3. `allocate_weighted(S, shares)` — share-driven

Largest-remainder apportionment: `L_i ≈ S · share_i`, `Σ L_i = S` exactly,
deterministic index tie-break. This is the policy that *intentionally* couples
range to rate, so that fast miners get proportionally larger ranges and finish
at ≈ the same time as slow miners.

## 4. Why this matters scientifically

- **Equal ranges + heterogeneous rates** ⇒ fast miners finish early and can idle
  (C2 saving opportunity). This is the *only* homogeneous-domain configuration in
  which C2 saves energy.
- **Weighted ranges + heterogeneous rates** ⇒ completion times equalise ⇒ idle
  opportunity shrinks or vanishes (validated: check `D3`, weighted idle <
  equal idle).
- **Homogeneous rates + equal ranges** ⇒ all `τ_i` equal ⇒ idle ≡ 0 (H4; check
  `D2`).

The decoupling makes H5 (heterogeneity × allocation) a genuine two-factor
comparison instead of a coupled artifact.

## 5. Validation evidence (category B, `STAGE_05B1_VALIDATION_REPORT.md`)

- `B1`: equal allocation identical across hash-rate distributions.
- `B2`: weighted allocation differs from equal under heterogeneous shares.
- `B3`, `B4`: both policies cover the domain exactly (`Σ L_i = S`).
- `B5-equal`, `B5-weighted`: continuous energy invariant A1 (8.420833333 kWh)
  holds under **both** allocations — allocation changes *coverage*, never total
  energy in the continuous scenarios.
