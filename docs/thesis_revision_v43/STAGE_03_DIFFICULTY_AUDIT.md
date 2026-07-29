# STAGE 03 — Difficulty, Block-Rate, and Finite-Domain Audit

Code: `Models/PoCol/round_state.py`. Tests: `test_stage3_difficulty.py`
(tests 23–38) and `test_stage3_performance.py` (block-interval validation).

---

## 1. Target and success probability

For a uniformly distributed 256-bit hash output and target `T`:

```
p = T / 2^256                         (per-header success probability)
```

For aggregate hash rate `H_total` and target block interval `B`:

```
p          = 1 / (H_total * B)
target T   = p * 2^256
lambda     = H_total * p              (network success rate, per second)
E[t_block] = 1 / lambda = B
```

**Key invariants (tested):**
- `lambda` depends on `H_total`, **not** on the miner count (test 24).
- Per-miner rates `H_i * p` **sum** to `H_total * p` (test 25).
- Splitting a fixed `H_total` among 100–500 miners leaves `E[t_block] = B`
  unchanged (test 26); the rate is **not** re-multiplied by the miner count
  (test 27).
- `0 < p < 1`, `0 < T < 2^256` (test 29); `p ↔ T` round-trips (tests 23, 30).

Baseline values (H=141 TH/s, B=600 s): `p = 1.182e-17`,
`T ≈ 1.369e60`, `target_version = 1`, `lambda = 1/600 s⁻¹`.

## 2. PoW vs PoCol search abstractions (kept explicitly separate)

| | PoW (Bitcoin model) | PoCol (finite domain) |
|---|---|---|
| search | unbounded; waiting time `~ Exp(lambda)` | finite domain of size `S` per round |
| block found | always (eventually) | only if a solution exists in `S` |
| interval | `E[t]=1/lambda=B` | first-solution time; **may exhaust** |
| code | `Models/Bitcoin/Consensus.py` (`expovariate`) | `round_state.draw_round_solutions` |

The PoW path is untouched (test 44 asserts it still uses `expovariate` and does
not import the PoCol round model).

## 3. Finite nonce-domain

Domain size `S = PoCol_DomainFactor · H_total · B` (default factor 2 → `S = 2HB`,
so expected solutions `mu = p·S = 2`). Numerically stable probabilities
(`log1p`/`expm1`, test 31/32):

```
P_success = 1 - (1-p)^S = -expm1(S · log1p(-p))
P_exhaust = (1-p)^S     =  exp (S · log1p(-p))
mu        = p · S
```

For the baseline (`mu=2`): `P_exhaust = e^{-2} ≈ 0.1353`.

**Exhaustion handling (`Consensus.start_round`, tests 33–38):**
1. draw `k ~ Poisson(mu)` solutions; `k=0` → exhaustion;
2. on exhaustion: increment `template_generation_id` (and `template_id`),
   record `exhausted_rounds` / `template_refreshes`, add `S/H_total` search time,
   and **re-draw** — bounded by `MAX_REFRESH` (default 10000) with a logged
   warning if hit (no forced success; tests 37, 38);
3. exhaustion is **never** a block, a stale block, or a security event (test 34);
4. events from a superseded template generation are `OBSOLETE_TEMPLATE` (test 35).

## 4. Block-interval validation (section 13)

**Analytical (exact):** `expected_block_interval(H, p=1/(H·B)) = B`
(`test_block_interval_analytical_matches_target`).

**Seeded sampling** (`test_block_interval_seeded_sampling_consistent`): draw
`N = 200000` waiting times `~ Exp(lambda=1/B)` with a fixed seed; the observed
mean must lie within `4·SE` of `B` and within the 95% CI. Reported quantities:
seed, sample size, expected mean, observed mean, std, standard error, 95% CI,
relative error (`< 1%`). The realized numbers are recorded in
`STAGE_03_SCHEDULER_REPORT.md`.

## 5. What is NOT claimed

- The PoCol **effective** block interval (blocks actually produced per second in
  the event loop) differs from the analytical PoW interval because of the
  finite-domain multi-solution structure and exhaustion overhead; it is
  **measured and reported**, not forced to equal `B`.
- Difficulty was **not** tuned to reproduce any prior thesis number.
