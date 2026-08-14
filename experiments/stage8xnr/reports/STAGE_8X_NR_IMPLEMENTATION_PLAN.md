# Stage 8X-NR — Implementation Plan

**Scope:** isolated corrective experiment measuring nonce-value reuse over the explicit
32-bit block-header nonce domain, kept strictly separate from exact candidate-input
duplication, physical evaluations, and electrical energy.
**Location:** `experiments/stage8xnr/` only. Protected baseline `8f45fbf5d989bb65…`
(390 files: Stage 8X, 8Y, 8Z, legacy simulator, Models, results, tests, thesis documents)
must be byte-identical at every checkpoint.

---

## 1. The scale fact that shapes every design decision

One S21 Pro evaluates 2.34e14 candidates/s, so a full traversal of the 32-bit nonce field
takes

```
τ_sweep = 2^32 / 2.34e14 = 18.355 µs
```

Per 600 s round each miner completes 3.269e7 full nonce-field sweeps; per 10 000 s run,
5.448e8. Consequences the design must honor rather than fight:

1. **Round-scoped and run-scoped nonce coverage saturate.** Every active miner touches all
   2^32 values in any scope longer than 18.4 µs. `U_nonce = 2^32` and
   `ρ_nonce = 1 − 2^32/C_nonce ≈ 1 − 3.06e-10·(100/N)` for every continuously active
   protocol. These metrics are still reported (the brief requires NR-round and
   NR-global-run) but they are *predictably saturated*, and the analytical model must say
   so in advance.
2. **The discriminating scope is the template epoch.** A template epoch is one traversal
   of one 2^32 domain under one header realization. Within a template epoch:
   conventional PoW gives each miner its *own* template → nonce reuse across miners is
   measured across concurrent per-miner epochs in the round scope; common-template PoW has
   N miners sharing one 2^32 domain → reuse fraction 1 − 1/N (zero-start: (N−1)/N of all
   evaluations are reuse); PoCol partitions the domain → reuse exactly 0.
3. **Event-driven per-sweep simulation is impossible** (5.4e8 epochs × 500 miners × 300
   runs). The engine must advance miners in closed form over macro-intervals and compute
   nonce-set overlap with cyclic interval arithmetic, invoking per-event logic only at
   block arrivals, round boundaries, and PoCol epoch exhaustions that matter (see §5).

## 2. Explicit domain semantics (brief §5–6)

- `S = 2^32`. The header nonce is `nonce32 ∈ [0, 2^32−1]`, always.
- The expanded search coordinate is `position = template_epoch · 2^32 + nonce32` per miner
  (CONV) or per network (MT/PC). `nonce32 = position mod 2^32`. The simulator never claims
  the search space is 2^32; template renewal via extranonce is modeled explicitly and
  counted (`template_epochs_per_miner`, `nonce_domain_exhaustions`, `nonce_resets`).
- Candidate identity for exact-input accounting is `(template_id, nonce32)`; template ids
  are distinct per miner-epoch in CONV and per network-epoch in MT/PC.

## 3. Protocol families and traversal policies (brief §8–9)

| Arm | Template | Allocation | Traversal | Role |
|---|---|---|---|---|
| XNR-PW-CONV-ZERO | per miner, renewed on exhaustion | none | all start at nonce 0 | synchronized worst-case bound (diagnostic) |
| XNR-PW-CONV-OFFSET | per miner | none | start_i ~ U(0, 2^32−1), cyclic | **primary** conventional model |
| XNR-PW-MT-ZERO | common per network epoch | none | zero-start | worst-case comparator (diagnostic) |
| XNR-PW-MT-OFFSET | common per network epoch | none | random offsets | **primary** common-template comparator |
| XNR-PC | common immutable per epoch | disjoint `[⌊iS/N⌋, ⌊(i+1)S/N⌋−1]` | sequential within own range | PoCol |

MT is a controlled comparator, never described as Bitcoin mainnet behaviour. PC has no
reserve/reassignment. PoCol post-range low power: a PC miner that finishes its range
before the epoch's block is found enters LOW_POWER until the next epoch. Because ranges
are equal ±1 nonce and hardware is homogeneous, the residency is the sub-microsecond
straggler gap (predicted `F_low` ≈ 1e-9…7e-8 depending on N mod, see §6) — the honest
consequence of the 2^32 domain, to be reported as such.

## 4. Difficulty (brief §11, re-derived, not inherited)

`q = target/2^256`; success per candidate is Bernoulli(q); network of H_N candidates/s
produces blocks at Poisson rate `H_N·q`. Setting `E[I] = 1/(H_N q) = 600 s`:

```
q_N = 1/(H_N·600);  D_N = H_N·600/2^32;  target_N = 2^256·q_N
```

The Stage 8X formula is confirmed to match the simulator's probability semantics (the
winner law used is exactly Poisson(q·M) over any scanned measure M). Same `D_N` for all
five arms at a given N; no separate PoCol calibration.

Expected winners per 2^32 template-epoch domain: `λ_epoch = q_N·2^32 = 2^32/(H_N·600)`
= 3.06e-11/(N/100)… i.e. an epoch almost never contains a winner; a round consumes ~3.3e7
epochs per miner (CONV) or per network (MT/PC — note MT/PC network epochs last 2^32/(N·h)
seconds). Blocks arrive as a Poisson process at rate H_N·q = 1/600 s⁻¹ in every arm where
all miners are active — **so block production and latency are expected to be statistically
identical across arms**; PC's straggler gap is the only (negligible) deficit. The design
must be able to report exactly that neutral result.

## 5. Engine (closed-form over macro-intervals)

Per round (round = one block race; ends at the first winning candidate network-wide):

1. Draw the round duration from the exact process: with all-active aggregate rate H_N, the
   first-winner time is Exponential(H_N·q) — plus, for PC, the deterministic epoch
   structure does not change the law because the Bernoulli field is i.i.d. across the
   union of scanned candidates (equivalence argument recorded in METHODS; identical to
   Stage 8X's winner-oracle equivalence).
2. Attribute the winner to a miner (uniform by hash share — equal here) and, within the
   winner's traversal, to a `(template_epoch, nonce32)` position, so per-arm template
   epoch counters and reset counters are exact integers derived from elapsed time and h.
3. Compute per-scope nonce metrics **analytically-exactly** from traversal geometry
   (cyclic interval arithmetic — no 2^32 booleans, brief §12/§19):
   - each miner's evaluated multiset in a scope of duration Δ is `k = ⌊hΔ⌋` sequential
     positions from a known offset: `f = ⌊k/S⌋` full sweeps + a partial cyclic interval of
     length `k mod S`;
   - `C_nonce = Σ k_i` (exact integer), per-value multiplicity function is a sum of N
     cyclic step functions ⇒ `U_nonce` = measure of union of partial intervals ∪ (S if any
     f_i ≥ 1), `M_≥2`, `m_max`, pairwise `O_ij = |V_i ∩ V_j|` via interval intersection
     with wrap-around split;
   - PC within-epoch: verify `O_ij = 0` and `ρ_nonce,epoch = 0` from the ledger, not by
     assumption (RQ-XNR3 "must be verified, not assumed").
4. Exact-input accounting (`C_exact/U_exact/R_exact/ρ_exact`) uses the same interval
   machinery keyed by `(template_id)`: CONV templates are per-miner ⇒ R_exact = 0 by
   construction *and verified*; MT: all miners share the epoch template ⇒ union across
   miners per epoch; PC: disjoint ⇒ 0, verified.
5. Energy: two-state ledger (ACTIVE / LOW_POWER) with `t_active + t_low = T` asserted per
   miner; `E = Σ_i P_act·t_active,i + α·P_act·t_low,i`, α ∈ {0, 0.10, 0.25, 0.50} as
   derived observations per run (not separate simulations).

Winner-consistency caveat for MT: when miners share a template, shared candidates must
share outcomes. The exponential first-winner draw at rate H_N·q would overstate the block
rate for MT because duplicated evaluations cannot yield independent successes. MT's
*distinct-input* rate is the measure of the union of scanned candidates per unit time:
with all N miners sweeping the same 2^32 domain, distinct-input throughput is the union
growth rate ≈ h·(coverage factor). For zero-start MT the union grows at exactly `h` (all
miners aligned); for offset MT the union of N random arcs grows at ≈ min(N·h, S/τ)… full
derivation in METHODS; the engine uses the exact union-measure rate per macro-interval to
drive the MT block process. This reproduces Stage 8X's finding (duplicate work costs
blocks) in the 2^32 setting where the effect is extreme: MT effective distinct rate
collapses toward `h·(1 + small)` — a key, honest result of the corrected domain model.

## 6. Analytical models (brief §18–19, preregistered expectations)

- Occupancy (with-replacement sampling): `E[U] = S(1−(1−1/S)^m)`, `E[R] = m−E[U]` — used
  only for the random-sampling toy validation (Test 9); *not* applied to sequential
  traversal, where interval geometry is exact.
- Sequential zero-start CONV round scope: all miners traverse identically ⇒
  `U_nonce = min(k_max mod S…, S) = S` (saturated), `m_max = N`, mean pairwise overlap
  `O_ij = S` (after first sweep). Exact prediction: saturation within 18.4 µs.
- Offset CONV round scope: same saturation after first sweep; before saturation (scopes
  < τ_sweep — reported as the *sub-sweep window diagnostic*), arcs of length k on a circle
  give `E[|V_i∩V_j|] = k²/S` for k ≤ S.
- MT-epoch scope: zero-start ⇒ `ρ_nonce,epoch = (N−1)/N` exactly; offset ⇒ same total
  reuse `1 − U/(N·k)` with U the union of N random arcs covering the domain.
- PC-epoch scope: 0 exactly.
- Partition: `start_i = ⌊iS/N⌋`, `end_i = ⌊(i+1)S/N⌋−1`; sizes differ by ≤ 1
  (S mod N ≠ 0 for all five N: remainders 96, 96, 196, 96, 296). PC straggler-gap
  prediction: miners with the short range finish `1/h = 4.27 fs × (range diff)` — i.e.
  4.3 ns earlier per nonce of deficit… `F_low` predictions computed in config and checked
  in Pilot.

## 7. Modules

```
config/nr_config.py     S=2^32, arms, N-grid, T=10 000 s, I=600 s, α-grid, D_N derivation,
                        partition function + F_low/saturation predictions, config_hash
config/seeds.py         30 fresh paired seeds + 6 pilot seeds, all disjoint from
                        8X/8Y/8Z registries (verified against their JSON files), per-purpose
                        stream derivation (round process, winner attribution, offsets)
src/noncedomain.py      cyclic interval type: normalize, union measure, intersection,
                        complement, multiplicity profile from N arcs, partition(N)
src/traversal.py        zero-start & offset traversal state: position→(epoch, nonce32),
                        arcs evaluated in [t0,t1), exhaustion/reset counting
src/metrics_nr.py       scoped counters: NR-round, NR-template-epoch, NR-global-run;
                        C/U/R/ρ for nonce and exact; M_≥2, m_max, O_ij summary
src/engine_nr.py        five arms; round loop; MT union-rate block process; PC low-power
                        ledger; energy; per-run record
src/run_matrix.py       pilot + primary execution, CSV writers
src/analysis_nr.py      paired stats (Shapiro→t/Wilcoxon, Holm), tables NR-A..NR-J
src/figures_nr.py       13 figures + conceptual diagram (PNG+PDF+SVG)
tests/test_stage8xnr.py Tests 1–10 of brief §30 + engine identities
```

## 8. Matrix, pilot, freeze

- **Pilot:** N ∈ {100,300,500} × 5 arms × 2 dedicated pilot seeds = 30 runs; validates the
  13 items of brief §31; results excluded from inference.
- **Primary:** N ∈ {100,…,500} × 5 arms × 30 fresh paired seeds = **750 physical runs**
  (the 2 ZERO arms are cheap diagnostics; brief §10 lists them as optional but Comparison C
  and Table NR-I require them, so they are included in the frozen matrix).
- α sensitivity: 4 derived observations per PC run; energy recomputation, not re-simulation.
- **Freeze:** config_hash over canonical config JSON; seeds SHA-256; code file checksums;
  git commit; protected-baseline re-verification. Then primary → analysis → tables →
  figures → reports.

## 9. Acceptance criteria (preregistered)

1. Engine identities at machine precision: `Σ_s t_{i,s} = T`; `W_total = Σ h·t_active`;
   exact integer candidate counts.
2. PC within-epoch nonce overlap = 0 and exact duplicates = 0, *measured*.
3. CONV: `ρ_exact = 0` while round-scope `ρ_nonce` ≈ saturation prediction within 1e-9.
4. MT: `ρ_nonce ≈ ρ_exact` at epoch scope, both ≈ (N−1)/N (zero-start) — analytic match
   within 1e-6.
5. Analytical vs simulated: every Table NR-J row within stated tolerance.
6. Blocks/latency: PoW-CONV pooled mean interval within 5 % of 600 s.
7. Neutral/negative outcomes are reportable: if energy differences are ~0 (expected for
   CONV vs PC at α=0 given F_low ~1e-8), that is the result.

## 10. Order of work

audit (done — see correction note appendix) → this plan → noncedomain + tests 1–5, 9, 10
→ traversal + metrics + tests 6–8 → engine + identity tests → pilot → pilot report →
freeze → primary 750 runs → analysis → tables/figures → reports → final 24-point answer
with Q1/Q2/Q3 answered separately.
