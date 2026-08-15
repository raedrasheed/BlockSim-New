# Stage 8X-NR — Validation Report

## 1. Automated test suite — 61/61 pass

`experiments/stage8xnr/tests/test_stage8xnr.py` implements all ten named tests of
brief §30 plus engine-identity and saturation checks:

| Brief test | Implementation | Result |
|---|---|---|
| 1 — 32-bit domain | `S = 2^32` asserted; every phase/arc start in [0, 2^32−1] | pass |
| 2 — PoCol full coverage | union of ranges = 2^32 at N ∈ {100…500} | pass |
| 3 — PoCol no overlap | pairwise overlap 0 at all N | pass |
| 4 — uneven partition | 2^32 mod N ≠ 0 at all five N; size spread exactly 1; `start_i = ⌊iS/N⌋` formula checked | pass |
| 5 — cyclic wrap-around | wrap-split, wrap-intersection, wrap-union, full-domain clamp | pass |
| 6 — reuse independent of template | (T_A,42)+(T_B,42) → reuse yes, duplicate no; engine realises it (ρ_nonce>0.999, ρ_exact=0 in CONV) | pass |
| 7 — exact duplicate | (T_A,42)+(T_A,42) → reuse yes, duplicate yes; MT epoch ρ_nonce = ρ_exact = (N−1)/N | pass |
| 8 — epoch reset | cross-epoch repeats do not violate within-epoch disjointness (toy + engine PC) | pass |
| 9 — analytical occupancy | E[U] = S(1−(1−1/S)^m) vs enumeration on toy domains, 4 parameterisations | pass |
| 10 — interval model | union/multiplicity/pairwise vs explicit set enumeration on toy cyclic domains, 300 random cases | pass |

Additional: traversal decomposition exactness; difficulty semantics
(q·D·2^32 = 1; one D_N for all arms); seed count/determinism/disjointness from
Stage 8X/8Y/8Z; engine identities < 1e-12 (measured 0.0); CONV round saturation
(U = 2^32, m_max = N, ρ_exact = 0); PC cross-miner overlap 0 in every round;
MT-ZERO co-discovery stale = (N−1)·blocks; energy equality at equal t_active
(brief §17/§20); sub-sweep ZERO vs OFFSET separation; paired round process;
same-seed full-run reproducibility incl. offsets (brief tests 10/14); template
renewal after every nonce-domain exhaustion, OFFSET resets = 0 vs ZERO resets >
exhaustions (brief test 11); M_≥3 / mean-multiplicity / P95 extensions verified
against explicit enumeration on toy domains.

## 1a. Amendment A1 bit-identity proof

The post-freeze metric extension (amendment A1, see the freeze report) re-ran
the deterministic engine on identical seeds and configuration. Every shared
column of all six primary CSVs is cell-for-cell identical between pre- and
post-amendment outputs: **0 mismatches** over 750 + 8 022 + 1 500 + 1 500 +
3 000 + 750 rows. The amendment is purely additive.

## 2. Analytical-vs-simulation (Table NR-J) — 55/55 within tolerance

Exact-zero requirements met exactly (PC epoch reuse, PC/CONV ρ_exact); closed
forms met to ≤ 1e-12 (MT (N−1)/N both metrics, zero-start sub-sweep (N−1)/N,
round-scope saturation form ≤ 1e-9); stochastic models within 5 % (offset
coverage model, W²/S pairwise overlap, F_low straggler gap); CONV blocks within
10 % of T/600 (16.13 vs 16.67, ≈1σ of the 30-seed mean); MT blocks within the
wide preregistered tolerance (Poisson counts of 1–2 events per cell).

## 3. Full-repository regression — 259/259 pass

| Suite | Tests | Result |
|---|---|---|
| legacy `tests/` | 11 | pass |
| `experiments/stage8x/tests` | 74 | pass |
| `experiments/stage8y/tests` | 116 | pass |
| `experiments/stage8xnr/tests` | 58 | pass |

## 4. Protected-artifact verification

390-file baseline covering Models/, results/, docs/, legacy tests/ and scripts,
all of `experiments/stage8x/`, `experiments/stage8y/`, `experiments/stage8z/`,
and every thesis `.docx`/`.pdf`/`.xlsx`:

```
baseline_sha256 = 8f45fbf5d989bb65d0a16a8eaf06c2159928360c255c1aa7d491f5220ff8e396
current_sha256  = 8f45fbf5d989bb65d0a16a8eaf06c2159928360c255c1aa7d491f5220ff8e396   (OK)
```

Stage 8X-NR wrote only under `experiments/stage8xnr/`. The original Stage 8X was
neither re-run nor modified, and the Stage 8Y/8Z baselines that depend on it are
intact.

## 5. Run audit

750/750 primary runs present; 25 (N, arm) cells × exactly 30 seeds; no NA cells;
no discarded runs (MT runs with zero blocks are retained and reported as zeros —
they are the result, not missing data); state-time conservation and work-identity
errors exactly 0.0 in all 750 runs.
