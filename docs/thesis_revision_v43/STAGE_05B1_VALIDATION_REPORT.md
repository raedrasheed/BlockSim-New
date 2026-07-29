# Stage 5B1 — Pre-Execution Validation Report

Runner: `experiments/thesis_revision_v43/validate_5b1.py`
Machine-readable: `results/thesis_revision_v43/stage_05b1/validation_report.json`

**This stage does NOT execute the frozen 1 890-run matrix.** It runs a bounded
validation set that exercises the engine end-to-end and reconciles its outputs
against independent references.

## 1. Headline

| Metric | Value |
|--------|------:|
| Validation runs executed | **42** |
| Hard cap | 200 |
| Under cap | ✅ |
| Reconciliation checks | **45** |
| Passed | **45** |
| Failed | **0** |

Six reconciliation families are covered: **energy, candidate, domain, events,
blocks, time**.

## 2. Categories

| Cat | Focus | Checks |
|-----|-------|-------:|
| A | Small-domain exact reference (coverage math vs brute force) | 11 |
| B | Range/rate decoupling | 6 |
| C | B1/B2 full event-loop | 7 |
| D | C2 in-loop idle | 8 |
| E | Coordination-counter reconciliation | 6 |
| F | Parallel reproducibility (20 seq vs 20 concurrent) | 2 |
| G | Stress N=500 | 5 |

## 3. Key checks (all pass)

**A — coverage math.** B3 disjoint winner time/owner match brute force (A1, A2);
disjoint distinct == total (A3); B1 winner time = min_pos/max_rate with distinct
coverage = one miner only (A4, A5); B2 linear-merge coverage approximates the
circular brute-force cover within 15 % (A7) with genuine duplicate work under a
long search (A8).

**B — decoupling.** Equal allocation is identical across hash-rate distributions
(B1); weighted differs and depends on shares (B2); both cover the domain exactly
(B3, B4); energy invariant A1 holds under both allocations (B5-*).

**C — B1/B2 in-loop.** Both produce accepted blocks (C1, C2); duplicate-rate
ordering **B3(0) < B2 < B1** (C3); candidate reconciliation `total = distinct +
duplicate` for all three (C4-*).

**D — C2 in-loop idle.** Idle energy emerges in-loop for het-equal (D1);
homogeneous equal-range idle ≡ 0 with energy = A1, i.e. **no forced saving**
(D2); weighted saves less than equal (D3); energy reconciliation `total = active +
idle + coord` exact (D4-*); **time reconciliation** `B3_active − C2_active =
C2_idle` (D5); state-transition reasons recorded (D6).

**E — coordination.** bytes = messages × 1 MB (E1); refreshes = exhausted rounds
(E2); unimplemented agreement energy is `null` (E3); coordination energy and its
lower bound both explicit 0 (E4); common-template has agreement ops, B0 has none
(E5); events reconciliation agreement ops = accepted blocks (E6).

**F — reproducibility.** 20 sequential = 20 concurrent, bit-for-bit, 0 mismatches
(F1); named streams reproducible and independent (F2).

**G — stress.** N=500 executes for all five scenarios; energy invariant A1 holds
for the four continuous scenarios; C2 energy ≤ A1 (G-*).

## 4. The six reconciliations

| Reconciliation | Where | Statement |
|----------------|-------|-----------|
| **Energy** | D4-* | total = active + idle + coordination (exact) |
| **Candidate** | C4-* | total evaluations = distinct + duplicate |
| **Domain** | B3, B4 | Σ range lengths = domain size S |
| **Events** | E6 | abstract agreement ops = accepted blocks |
| **Blocks** | A9-*, C1, C2, G-* | accepted blocks ≥ 1; loop closes on tiny and N=500 domains |
| **Time** | D5 | B3_active − C2_active = C2_idle (in-loop idle removed from active) |

## 5. Verdict

All 45 checks pass with 42 runs. The engine is validated for the frozen matrix;
Stage 5B2 execution is **not** performed here and awaits explicit approval.
