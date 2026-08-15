# Stage 8X-ND — Validation Report

## 1. Automated suite — 33/33 pass (all 21 required tests of brief §36)

| §36 test | Result |
|---|---|
| 1 NONCE_DOMAIN_SIZE == 2^32 | pass |
| 2 MAX_NONCE == 2^32 − 1 (partition ends at 2^32−1 inclusive) | pass |
| 3 every ND-PW miner receives the full domain | pass |
| 4 every ND-PC miner receives only its partition | pass |
| 5 partitions cover all 2^32 values (Σ sizes = 2^32) | pass |
| 6 partitions do not overlap (contiguous tiling) | pass |
| 7 partition-size spread ≤ 1 | pass |
| 8 full-domain sweep time = 2^32/h = 18.355 µs | pass |
| 9 range sweep time = ⌈2^32/N⌉/h (36.7–183.6 ns) | pass |
| 10 PoW reset after 2^32 evaluations (renewals = T·h/2^32 per miner, exact) | pass |
| 11 PoCol coordinated epoch reset after full union exhaustion | pass |
| 12 header/template IDs change appropriately (renewal counters exact) | pass |
| 13 same nonce under different headers = distinct exact candidate (ρ_exact = 0 with m_max = N) | pass |
| 14 low-power only after assigned range completion (F_low = straggler closed form) | pass |
| 15 ND-PC-NOLP never changes physical work (accounting only; E = P·N·T exact) | pass |
| 16 state times sum correctly (0.0 relative error) | pass |
| 17 energy equation exact | pass |
| 18 same target/difficulty across protocols at same N | pass |
| 19 seed reproducibility (bitwise) | pass |
| 20 event abstraction vs toy explicit simulation | pass |
| 21 analytic vs simulated block rate within preregistered 10 % | pass |

Plus: seed disjointness (incl. Stage 8X-E50 registry) and the paired
trial-rate identity check (ND-PW and ND-PC block sequences match per seed).

## 2. Theory-vs-simulation — 40/40 within tolerance (Table ND-N)

Block retention 1.0 (≤2 %), latency ratio 1.0 (≤2 %), F_low = straggler form
(≤1e-3), PC savings = F_low·(1−α) (≤1e-3), NOLP savings exactly 0, PW blocks
within 10 % of 16.67/run, energy-per-block ratio 1.0 (≤1e-4), domain sweeps
per miner exact (≤1e-6). The theory report's unfavourable prediction (TQ6:
no material residency possible) was confirmed, not softened.

## 3. Full-repository regression — 334/334 pass

legacy 11, Stage 8X 74, Stage 8Y 116, Stage 8X-NR 61, Stage 8X-E50 39,
Stage 8X-ND 33.

## 4. Protected artifacts

602-file baseline covering Stage 6A/8S/8U artifacts, original 8X, 8X-NR,
8X-E50, 8Y, 8Z, thesis DOCX/PDF/XLSX, shared simulator code, results and
reports:

```
baseline_sha256 = 6bbebb7def76ad3694867f6f73e8aec095d4c0de1433af57bf1ec73a3916384c
current_sha256  = 6bbebb7def76ad3694867f6f73e8aec095d4c0de1433af57bf1ec73a3916384c  (OK)
```

Stage 8X-ND wrote only under `experiments/stage8xnd/`; the Stage 8X-NR engine
is imported read-only and verified unmodified.

## 5. Run audit

450/450 physical runs (15 cells × 30 seeds) + 150/150 derived ND-PC-NOLP
observations, every row labelled `run_kind`; zero identity violations; no runs
discarded; primary executed in one 6.3 s pass after the freeze.
