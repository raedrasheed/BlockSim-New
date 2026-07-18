# Fixed 600-Second Round Experiment — Results

**Branch:** `claude/pocol-fixed-600s-distributed-nonce` · **Data:** `results/fixed_600s_pocol/`
**Reproduce:** `python experiments/fixed_600s_pocol/run_matrix.py 100 12` · `python -m pytest tests/ -v`

Protocols: **DUP** = common-template duplicate-search PoW baseline (not normal
Bitcoin mining) · **IND** = independent-header PoW control (equal total budget) ·
**PoCol** = disjoint-nonce allocation. Idle power `q = 0` is the idealized upper
bound unless stated.

---

## 1. Required §12 example (M=100, N=10, r=1 c/s, nonce 99, q=0) — all exact

| | DUP | PoCol |
|---|---:|---:|
| attempts per miner | 100 | ≤ 10 |
| total attempts | **1000** | **100** |
| discovery time | 100 s | 10 s (miner 9, nonce 99) |
| ACTIVE miner-seconds | 1000 | 100 |
| all miners IDLE from | 100 s | 10 s |
| block commit | 600 s | 600 s |
| accepted blocks / interval / throughput | 1 / 600 s / equal | 1 / 600 s / equal |
| energy ratio / reduction | — | **0.1 / 90 %** |

§13 multi-round: 60 000 s → **100 blocks for both**, interval exactly 600 s,
equal throughput (automated tests).

## 2. Deterministic primary experiment (H1, placement=last, sim 10 200 s = 17 rounds)

Block-rate guarantees hold **exactly** for all three protocols at every N:
17 accepted blocks, 600.0 s interval, equal throughput (invariants 12–15).

**PoCol energy reduction vs DUP by idle ratio q** (= `(1−q)(1−1/N)` exactly):

| N | q=0 | 0.05 | 0.10 | 0.20 | 0.50 | 1.0 |
|---:|---:|---:|---:|---:|---:|---:|
| 2 | 50.00 % | 47.50 | 45.00 | 40.00 | 25.00 | 0 |
| 10 | 90.00 % | 85.50 | 81.00 | 72.00 | 45.00 | 0 |
| 100 | 99.00 % | 94.05 | 89.10 | 79.20 | 49.50 | 0 |
| 500 | 99.80 % | 94.81 | 89.82 | 79.84 | 49.90 | 0 |

- **IND achieves the identical reduction at every N** (e.g. 99.00 % at N=100):
  the saving is **de-duplication + power-down**, not disjoint partitioning per se.
- H1 and H2 give identical ratios (0.0100 at N=100); only absolute kWh differ.
- Sleep sub-sweep (N=10, q=0→SLEEP): 90.00 / 89.10 / 85.50 % for sleep ratios
  0 / 0.01 / 0.05.
- Placement sweep (N=100, q=0): DUP discovery = 0→600 s across
  first/p25/middle/p75/last; reduction 0 % (first — nobody works, nothing to
  save) to 99.00 % (last). PoCol discovery ≤ 6 s throughout.

## 3. Stochastic experiment (H1, p = 2/M, q=0, 100 paired seeds, fresh subprocesses)

| N | protocol | blocks | interval (s) | thru (tx/s) | disc (s) | idle-after (s) | E (kWh) | E/blk (kWh) | % ACTIVE |
|---:|:--|---:|---:|---:|---:|---:|---:|---:|---:|
| 100 | DUP | 14.86 | 689 | 2.914 | 204.7 | 395.3 | 3.6422 | 0.2525 | 42.4 |
| 100 | IND | 17.00 | 600 | 3.333 | 3.07 | 596.9 | 0.0440 | 0.0026 | 0.51 |
| 100 | PoCol | 17.00 | 600 | 3.333 | 2.92 | 597.1 | 0.0418 | 0.0025 | 0.49 |
| 300 | DUP | 14.82 | 689 | 2.906 | 201.3 | 398.7 | 3.6115 | 0.2502 | 42.1 |
| 300 | IND | 17.00 | 600 | 3.333 | 1.04 | 599.0 | 0.0148 | 0.0009 | 0.17 |
| 300 | PoCol | 17.00 | 600 | 3.333 | 0.98 | 599.0 | 0.0140 | 0.0008 | 0.16 |
| 500 | DUP | 14.56 | 698 | 2.855 | 199.7 | 400.3 | 3.6837 | 0.2599 | 42.9 |
| 500 | IND | 17.00 | 600 | 3.333 | 0.63 | 599.4 | 0.0090 | 0.0005 | 0.10 |
| 500 | PoCol | 17.00 | 600 | 3.333 | 0.62 | 599.4 | 0.0088 | 0.0005 | 0.10 |

(N=200/400 in `stochastic_raw.csv` / `summary_statistics.csv`, same pattern.)

### 3.1 Validity flags (per the §19 rule — read before quoting)

- **PoCol vs IND is the valid stochastic comparison:** identical blocks
  (17.00/17.00), interval (600 s), throughput. Paired energy difference:
  −0.0022 … −0.0002 kWh (PoCol lower), Cohen's d −0.06…−0.24, bootstrap CI
  **includes 0** at every N ⇒ **no statistically distinguishable difference**;
  the pre-registered ±1 % TOST margin was **not** met (CI wider than margin at
  100 seeds) ⇒ equivalence not formally established either. **No PoCol advantage
  over independent-header mining is claimable.**
- **PoCol vs DUP stochastically is an UNEQUAL-block comparison:** DUP commits
  only 14.6–14.9 of 17 blocks (~2.2 empty rounds; its full-domain scan fills the
  slot, so it cannot re-template after exhaustion, while PoCol covers the domain
  N× faster and retries within the round). By the validity rule, the headline
  98.8–99.8 % stochastic "saving" vs DUP must carry this flag; the clean
  DUP-vs-PoCol number is the **deterministic** one (§2), where blocks are equal.

## 4. Interpretation (§19 answers)

1. **Equal accepted blocks?** Deterministic: yes, exactly (17/17; 100/100).
   Stochastic: PoCol = IND = 17.00; DUP fewer (14.6–14.9) — flagged.
2. **Interval exactly 600 s?** Yes wherever a block was committed (invariant 14).
3. **Throughput equal?** Yes for equal payloads (deterministic all three;
   stochastic PoCol = IND; DUP lower with its missing blocks — flagged).
4. **PoCol discovers earlier?** Yes: ~6 s (det., N=100) / 0.6–3 s (stoch.) vs
   DUP's 200–600 s.
5. **Additional idle time?** ~594–599 s per miner-round (post-discovery wait).
6. **Does idle time lower energy?** Only when idle power < active power:
   reduction = `(1−q)(1−1/N)`; 0 at q=1.
7. **Does the saving survive vs IND?** **No.** IND matches PoCol exactly
   (deterministic) / indistinguishably (stochastic).
8. **Share caused purely by de-duplication?** All of it — IND, which only removes
   duplication (plus the same power-down), reproduces the full reduction.
9. **Idle power > 0?** Saving scales down linearly: 99.0 → 49.5 % (q=0.5) → 0 %
   (q=1) at N=100.
10. **N=1?** No saving (0 %), attempts identical (invariant 18).
11. **All subranges exhausted?** New template within the round (honest
    re-templating); stochastically PoCol had 0 empty rounds while DUP had ~2.2 —
    at p=0, zero blocks are committed and reported (no fabricated success).
12. **Algorithmic or power-management saving?** A **fixed-slot power-management
    saving enabled by de-duplication**. The disjoint partition contributes the
    de-duplication; the energy drop itself comes from miners idling in a fixed
    slot — and independent headers achieve the same, so the saving is **not**
    PoCol-specific.

## 5. Tests

`python -m pytest tests/ -v` → **124 passed** (97 pre-existing + 27 new: 17
deterministic invariants, 8 stochastic, 2 runner/isolation).
