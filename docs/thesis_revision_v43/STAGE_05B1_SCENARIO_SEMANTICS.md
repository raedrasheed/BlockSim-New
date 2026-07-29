# Stage 5B1 — Scenario Search Semantics

Each scenario is a distinct **search discipline** over a common finite-domain
model (domain size `S` chosen so `p·S = μ`; `K ~ Binomial(S, p)` solutions per
template generation). All five run inside one event loop; they differ only in how
miners cover the domain and whether they idle.

## B0 — Independent templates (PoW abstraction)
Each miner searches its **own** domain; full-parallel, non-redundant coverage.
No common-template agreement (`AGREEMENT[B0] = False`) → zero abstract agreement
operations. Physically identical energy to B3/C1 (8.420833333 kWh) but a
different *coordination* interpretation. B0 exists to anchor the PoW baseline.

## B1 — Common template, all miners from nonce 0
Every miner scans the same sequence from 0. The fastest miner reaches the lowest
solution first: `winner_time = min(pos) / max_rate`. Distinct coverage ≈ **one
miner's** work; the other `n−1` miners duplicate it → duplicate rate → ~0.99.
Because block production runs at a *single* miner's rate (no parallel speed-up),
B1 produces far fewer blocks — at N=500 the first block already spans the whole
simulation (1 accepted block). This is the honest cost of uncoordinated common
templates, **not** a labelling of B1 as "classical PoW".

## B2 — Common template, seeded random starts
Each miner starts at an independent seeded offset and scans forward with a
single-traversal stop. Coverage is the **union** of per-miner arcs (circular),
so overlap is partial: duplicate rate strictly between B3 (0) and B1 (~0.99).
Reproducible per seed.

## B3 / C1 — Common template, disjoint continuous ranges
Miners partition the domain (`allocate_equal`/`allocate_weighted`); zero overlap
→ `duplicate_evaluations = 0`. B3 (energy interpretation) and C1 (collaboration
interpretation) are the **same execution** — one physical run, dual label
`B3;C1` (see `STAGE_05B1_SEMANTIC_DUPLICATION_AUDIT.md`). Continuous operation ⇒
energy invariant A1.

## C2 — Disjoint ranges + in-loop idle
Identical to B3/C1 except a miner that **completes its range** within a template
generation with no solution goes **idle** until the next generation or an
accepted block:
```
enter idle : range_exhausted_no_solution
leave idle : new_template_generation_or_accepted_block
```
Idle removes active time (`a`) and accrues idle time (`idl`) *within the loop*:
```
a   = tgen·min(τ_i, D_ex) + min(τ_i, gen_success)
idl = tgen·max(0, D_ex − τ_i) + max(0, gen_success − τ_i)
```
C2 saves energy **iff** some miner can finish early — i.e. heterogeneous rates
with **equal** ranges, or μ<1. In the homogeneous equal-range baseline all `τ_i`
are equal and idle ≡ 0 (no forced saving). The saving, when present, is exactly
`Σ idle_time·(P_active − P_idle)`.

## Summary of invariants

| Scenario | Overlap | Duplicate rate | Idle | Total energy (continuous, homogeneous) |
|----------|---------|----------------|------|----------------------------------------|
| B0 | none (own domain) | 0 | no | 8.420833333 kWh |
| B1 | full (all from 0) | ~0.99 | no | 8.420833333 kWh |
| B2 | partial (random starts) | 0<·<0.99 | no | 8.420833333 kWh |
| B3/C1 | none (disjoint) | 0 | no | 8.420833333 kWh |
| C2 | none (disjoint) | 0 | in-loop | ≤ 8.420833333 kWh (saving only if a miner idles) |

Total energy is **equal** across all continuous scenarios: search discipline
changes *coverage and energy-per-block*, never total energy.
