# Stage 8X-ND — Implementation Plan

**Concept under test (verbatim):** every conventional PoW miner independently
uses the same numerical nonce set 0…2^32−1 (with independent headers), versus
PoCol partitioning that same numerical nonce set among miners on a common
template with post-range low power. Exact-hash duplication is a secondary
diagnostic only; same-template PoW is NOT the baseline here.

## Arms

| arm | headers | nonce domain per miner | traversal | role |
|---|---|---|---|---|
| ND-PW | independent, renewed after each full sweep | full 2^32 (D_i = D) | **0,1,…,2^32−1 sequential (primary rule, §9)** | primary conventional control |
| ND-PW-OFFSET | independent | full 2^32 | seeded random offsets, cyclic | secondary diagnostic (traversal sensitivity) |
| ND-PC | one common immutable template per epoch | disjoint R_i, ⌊iS/N⌋ partition | own range; ACTIVE→LOW_POWER on completion; no reassignment/borrowing/handoff | PoCol |
| ND-PC-NOLP | — | — | **derived energy-policy observation** of the ND-PC physical trajectory with completed miners priced at full power | separates partitioning from low-power policy |

Same D_N (q_N = 1/(N·h·600)) for all arms at each N; PoCol never retargeted.

## Engine

The three physical arms map exactly onto the frozen, fully validated Stage
8X-NR engine semantics (read-only import — protected baseline verifies the
module is untouched): ND-PW = XNR-PW-CONV-ZERO, ND-PW-OFFSET =
XNR-PW-CONV-OFFSET, ND-PC = XNR-PC, executed on **fresh Stage 8X-ND seeds**.
This reuses code that already passes 61 tests including the exact interval
arithmetic, identity checks, and toy-domain validations; the ND test suite
re-asserts every §36 property against the wrapper. ND-PC-NOLP is derived:
E_NOLP = P·N·T (t_low priced at full power), identical physical trajectory
(test 15).

## Matrix

Pilot: N ∈ {100,300,500} × 3 physical arms × 2 dedicated seeds = 18 physical
runs. Primary: 5 N × 3 physical arms × 30 fresh seeds = **450 physical runs**
(300 primary: ND-PW, ND-PC; 150 secondary diagnostic: ND-PW-OFFSET) plus 150
derived ND-PC-NOLP energy-policy observations (from the ND-PC trajectories, as
§33 permits). α ∈ {0,.10,.25,.50} are accounting-only.

## Outputs

The nine §37 raw CSVs, tables ND-A…ND-N, 16 figures, the nine §46 reports.
Assessment per §45 uses EnergySaving + BlockRetention + EnergyPerBlockRatio
together; outcomes A–E all reportable; theory (which predicts D with C) is
frozen first.

## Order

protect (done, 602-file baseline `6bbebb7d…`) → theory report (done) → this
plan → config/seeds → wrapper engine + runner → §36 tests → pilot → freeze →
450 physical runs → analysis → figures → reports → re-verify baseline →
commit/push → final 31-point answer + Q1–Q7.
