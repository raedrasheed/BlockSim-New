# STAGE 8Y — IMPLEMENTATION PLAN

**Phase 1–2 deliverable.** Written before the Pilot and before any scientific run.
Experiment family: `8Y` — *Heterogeneous Energy-Aware PoCol*.

---

## 1. Repository inspection

### 1.1 Stage 8X as the architectural reference

Stage 8X (`experiments/stage8x/`, commit `ec89b3b`) established, and Stage 8Y
reuses, the following pattern:

| Element | Stage 8X | Stage 8Y |
|---|---|---|
| Layout | `config/ simulator/ analysis/ tests/ outputs/ figures/ reports/` | same, with `src/` in place of `simulator/` and an added `manifests/` |
| Config isolation | frozen immutable `RunConfig`, never imports `InputsConfig` | identical discipline |
| RNG | per-purpose, per-miner `random.Random` streams from a master seed | identical |
| Hashing | `(template_id, candidate_index)` identity, Poisson winner oracle over a domain, interval `ScanLedger` for exact duplicates, real double-SHA-256 validated by Monte Carlo | **imported read-only** from `experiments.stage8x.simulator.hashing` |
| Propagation | gossip `Exp(mean 0.42 s)` broadcast to all peers | retained unchanged |
| Acceptance | longest chain, deterministic first-seen tie-break | retained unchanged |
| Difficulty | `D = H_N · I_target / 2^32`, one `D` shared by all protocols | generalised to heterogeneous `H_N = Σ h_i` |
| Freeze | config hash, code SHA-256, seed registry SHA-256, git + environment | same, plus a protected-artifact baseline |

Stage 8X's key structural finding — that homogeneous miners holding equal disjoint
ranges complete them simultaneously, bounding low-power residency to
`F_low ≈ 2.3e-3` and yielding only ~0.23 % energy saving — is the direct motivation
for Stage 8Y: **heterogeneity is the missing ingredient that could make range
completion, active-set selection and reserve parking produce a first-order effect.**

### 1.2 Protected artifacts

`experiments/stage8y/baseline.py` fingerprints **218 files**: `Models/`, `results/`,
`docs/`, `tests/`, all of `experiments/stage8x/`, the legacy revision-experiment
scripts, the root simulator modules, and every root-level `.xlsx` / `.docx` / `.pdf`
thesis artifact. Baseline SHA-256 `2e9e6f76…`, recorded before any Stage 8Y file was
written and re-verified after execution. The legacy suite (11 tests) and the Stage 8X
suite (74 tests) are run before and after.

Stage 8Y writes **only** under `experiments/stage8y/`. It imports exactly one thing
from outside: the Stage 8X hashing primitives, read-only, which guarantees the two
experiment families share an identical SHA-256 and candidate-identity semantics.

---

## 2. Scientific design (frozen candidate, fixed before the Pilot)

### 2.1 Hardware — heterogeneous, manufacturer-sourced

`config/hardware_registry.json` records manufacturer, model, nominal hash rate,
nominal active power, derived J/TH, source URL, retrieval date, and an explicit
per-device certification status.

| Key | Device | h (TH/s) | P (W) | η derived (J/TH) | Certification status |
|---|---|---|---|---|---|
| `S21PRO` | Antminer S21 Pro | 234 | 3510 | 15.000 | official URL located, table not retrievable in sandbox |
| `S19XP` | Antminer S19 XP | 141 | 3010 | 21.348 | official URL located, table not retrievable in sandbox |
| `S19JPRO` | Antminer S19j Pro 104T | 104 | 3068 | 29.500 | **verified quote** from the official support page |

`(h, P)` are primary; `η = P/h` is derived so `E = P·t` is exact. Where Bitmain's
stated η differs from the derived value (S19 XP: 21.5 vs 21.348, a 0.7 % gap inside
the published ±5 % power tolerance) the discrepancy is recorded, not reconciled away.
**No device-specific low-power figure is invented**: no manufacturer publishes one,
so all parked power is `P_low = α·P_active` with α swept as an explicit assumption.

### 2.2 Compositions

| ID | Mix (by miner count) | Rationale |
|---|---|---|
| H0 | 100 % S21PRO | homogeneous control; reproduces Stage 8X hardware |
| H1 | 75 / 25 S21PRO / S19JPRO | mostly-refreshed network |
| H2 | 50 / 50 | balanced two-generation reference |
| H3 | 25 / 75 | old-capacity-dominated |
| H4 | 20 S21PRO / 30 S19XP / 50 S19JPRO | three generations, newest a minority; spans the full 15.0–29.5 J/TH range |

H4's shares were fixed on a hardware-turnover argument **before any run** and were
not adjusted toward or away from the 50 % threshold. Counts are apportioned by
largest remainder so they sum exactly to N and are deterministic.

`H_N = Σ h_i`, `P_N = Σ P_i`, `η_network = P_N/H_N` — all computed, never tabulated,
and never held constant as N changes.

### 2.3 Difficulty — one per (N, composition), never PoCol-specific

```
D_{N,H} = H_N · I_target / 2^32     q = 1/(H_N · I_target)     target = 2^256/(D·2^32)
```

`H_N` is taken over the **full installed population**, so difficulty never falls
because a policy activates fewer miners. A single `D_{N,H}` is passed to PoW,
PoCol-All, Equal-range, Hash-proportional, Energy-aware and Adaptive-Reserve alike;
there is no PoCol difficulty path in the code, and a test asserts it.

### 2.4 Nonce domain — the decision that matters

```
S_{N,H} = H_N · τ_epoch,  τ_epoch = I_target = 600 s
slot_i  = S · h_i / H_N = h_i · τ   (hash-proportional)   or   S / N (equal)
```

`S` is derived from **installed** capacity and partitioned into one disjoint slot per
**installed** miner. Parking a miner leaves its slot unscanned; it does not shrink
the domain. This is the design the brief prefers: changing the active subset cannot
covertly reduce the work requirement in PoCol's favour. The alternative
(`S` sized from *active* capacity) is implemented as a labelled secondary sensitivity
condition only, never as the primary.

Two consequences fixed in advance: hash-proportional slots give every miner exactly
`τ` seconds of work regardless of `h_i` (equal completion times), while equal slots
give miner *i* `τ·(H_N/N)/h_i` seconds — fast miners finish early and park, which is
exactly what policy P1 is built to expose.

### 2.5 Power states and energy

Four states — `ACTIVE`, `LOW_POWER`, `STANDBY`, `WAKING` — with

```
E_i = P_act,i·t_act,i + α·P_act,i·(t_low,i + t_standby,i) + 1.0·P_act,i·t_wake,i
```

`WAKING` performs no hashing and draws **full active power** (the conservative
choice, unfavourable to PoCol; no vendor wake-power curve exists). `LOW_POWER` and
`STANDBY` share α because no vendor data distinguishes them, but their residence is
tracked and reported separately. `t_active + t_low + t_standby + t_waking = T` is
asserted per miner per run.

α ∈ {0, 0.05, 0.10, 0.25, 0.50}, labelled `alpha_0 … alpha_050`. α affects accounting
only, so each trajectory is simulated once and re-priced five times. `t_wake` affects
dynamics and is therefore simulated, not re-priced.

### 2.6 Protocols

| ID | Role | Description |
|---|---|---|
| `POW` | **principal comparator** | traditional competitive PoW, distinct per-miner templates/extranonce, rolls locally and instantly, always ACTIVE |
| `POW_CT` | secondary diagnostic only | Common-Template Independent PoW; the only configuration where exact duplicates are non-degenerate |
| `P0_ALL` | primary | PoCol, all miners active — within-PoCol control isolating heterogeneity alone |
| `P1_EQUAL` | secondary | PoCol, equal ranges → fast miners park after completion |
| `P2_HASHPROP` | secondary | PoCol, hash-proportional ranges → equal completion; the control for P1 |
| `P3_ENERGY` | primary | PoCol, energy-aware active set held for the horizon |
| `P4_RESERVE` | primary | PoCol, staged reserve activation with an explicit wake transition |

### 2.7 Selection rules and confirmatory parameters

S1 random, S2 hash-first, S3 efficiency-first, S4 exact optimisation
(`min Σ P_i s.t. Σ h_i ≥ H_required`, solved exactly by enumeration over device
classes with a documented stable tie-break: lowest power, then highest hash, then
lexicographic count vector in efficiency order, then lowest miner ids).

**Confirmatory** (declared now, swept only as secondary):

| Parameter | Confirmatory value | Justification |
|---|---|---|
| selection rule | S4 (exact optimisation) | the principled rule; S1–S3 are controls |
| P3 target active hash fraction | 0.60 | midpoint of the pre-declared range {0.40…0.80} |
| P4 schedule | 0.60 → 0.75 → 0.90 → 1.00 | the brief's example staged schedule |
| P4 trigger | 300 s | midpoint of the pre-declared {150,300,450,600} |
| P4 wake delay | 10 s | conservative interior value of {0,1,5,10,30} |
| allocation | hash-proportional | equalises completion; P1 is the contrast |

Targets are expressed as active **hash-capacity** fractions. The miner-count sweep
exists only to demonstrate that `r ≠ r_H ≠ r_P` in a heterogeneous network.

### 2.8 Run matrices

| Phase | Design | Runs |
|---|---|---|
| Pilot | 3 comp × 3 N × 7 protocols × 6 pilot seeds | 378 |
| **Primary (confirmatory)** | {H0,H2,H4} × {100,300,500} × {POW, P0_ALL, P3_ENERGY, P4_RESERVE} × 30 seeds | **1080** |
| Secondary (exploratory) | allocation, selection × r_H, count fraction, wake, trigger, reserve initial, N∈{200,400}, common-template | 2850 |
| Long horizon | N=300 × {H0,H2,H4} × 4 protocols × 30 seeds at T=100 000 s | 360 |

α re-pricing multiplies **observations**, never physical runs: 810 PoCol primary runs
× 5 α = 4050 derived energy observations. The two counts are always reported apart.

### 2.9 Preregistered acceptance criteria

Outcomes A–E exactly as specified, with `Saving > 0.50`, `BlockRetention ≥ 0.95 /
0.90`, `LatencyRatio ≤ 1.10`, and the explicit rule that **α = 0 alone never
counts as strong physical evidence**.

### 2.10 Mandatory decomposition

Because every miner occupies exactly one state and WAKING is charged at active
power, `P_N·T = pw_active + pw_waking + pw_low + pw_standby` exactly, so the saving
is exactly `(1−α)·(pw_low + pw_standby)`. Two orthogonal exact decompositions are
reported — *participation vs selection* (sequential and Shapley) and *post-range vs
reserve* — plus the explicit finding that stale-work elimination contributes exactly
zero energy in a wall-clock state × power model.

---

## 3. New files

```
experiments/stage8y/
  baseline.py  run.py  validate.py  freeze.py  analyze.py  README.md
  config/  hardware_registry.json  hardware.py  difficulty.py  policies.py
           seeds.py  stage8y_config.py  stage8y_seeds.json
  src/     powerstate.py  energy.py  engine.py  metrics.py  analysis_stats.py
           analysis_tables.py  analysis_figures.py
  tests/   test_stage8y.py
  outputs/  figures/  reports/  manifests/
```

No file outside `experiments/stage8y/` is created or modified.

---

## 4. Execution order

Repository inspection → written design (this document) → implementation → unit and
integration validation → Pilot → documented Pilot fixes → freeze → primary execution
→ secondary sensitivity → long horizon → paired statistics → Pareto analysis →
acceptance evaluation → documentation → final validation → commit and push.

## 5. Declared expectation (recorded before execution)

Under matched difficulty the block rate is proportional to active hash capacity, so
`BlockRetention ≈ r_H` while `Saving ≈ (1−α)·(1 − r_P)`. Selectivity `r_P/r_H < 1`
is bounded by the efficiency spread in the registry (15.0 to 29.5 J/TH, a factor of
1.97). It is therefore **expected in advance** that a large saving and a ≥ 90 %
block retention will be difficult to obtain simultaneously, and that Outcome C or D
is a live possibility. This expectation is recorded here so that a negative result
cannot later be presented as a surprise, and so that a positive result cannot be
presented as if the design had been neutral about it.
