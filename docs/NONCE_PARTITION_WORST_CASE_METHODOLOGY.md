# Nonce-Partitioning Worst-Case Experiment — Methodology

**Branch:** `claude/pocol-disjoint-nonce-worst-case`
**Status:** a *separate, explicitly labelled* controlled experiment. It does **not**
modify, replace, or reinterpret the corrected continuous-mining comparison in
`results/corrected/` or the wall-clock energy model in `Models/Node.py`.

---

## 0. Two different questions — do not conflate them

This repository now contains **two** distinct experiments answering **two**
different questions.

| | Question | Answer | Where |
|---|---|---|---|
| **Finding 1** | Under continuous full-network mining with equal aggregate hash rate and **distinct** candidate work, does PoCol save energy vs PoW? | **No — energy-neutral** (both = 8.4208 kWh). | `results/corrected/`, `docs/CORRECTED_EXPERIMENT_REPORT.md` |
| **Finding 2** | Under a **common-template exact-duplicate-search worst case**, how much can disjoint nonce allocation save? | **Up to `1 − 1/N`** attempts/energy. | this experiment, `results/nonce_partition_worst_case/` |

These are **not** combined. Finding 2 is a bounded synthetic worst case, not a
statement about the Bitcoin network. See
`docs/NONCE_PARTITION_SCOPE_AND_LIMITATIONS.md`.

---

## 1. Terminology (required)

The two primary experimental modes are named:

1. **Common-Template Duplicate-Search Baseline** (`duplicate_full_domain`)
2. **PoCol Disjoint-Nonce Allocation** (`disjoint_partition`)

The first mode is **not** called "Bitcoin PoW" without qualification. It is *an
intentionally constructed common-template duplicate-search baseline* — the
specific worst case in which:

- all miners receive exactly the same immutable block template;
- all miners compute the same complete candidate block header;
- all miners use the same finite nonce domain;
- all miners start at the same nonce;
- all miners traverse nonces in the same deterministic order;
- therefore they repeat identical candidate-header evaluations;
- all miners stop when a valid candidate is found or the domain is exhausted.

Real Bitcoin miners generally use **different** coinbase extranonces, Merkle
roots, timestamps, transaction sets, and therefore **different candidate
headers**. This experiment evaluates a **bounded synthetic redundancy scenario**,
not the full Bitcoin network.

A third, optional **reference** mode is included:

3. **Independent Candidate Headers** (`independent_candidate_headers`) — miners
   search **distinct** candidate headers / independent sequences. Its only
   purpose is to show that the `1/N` saving does **not** automatically apply when
   miners are not repeating identical complete candidate headers. Results from
   the three modes are never mixed.

---

## 2. Interval convention

The nonce domain is the **half-open** integer interval `[domain_start,
domain_end)`, so the domain size is

```
M = domain_end - domain_start
```

`partition_nonce_domain(domain_start, domain_end, miner_count)` returns
`miner_count` half-open sub-intervals `(start, end)` meaning `[start, end)`.
The core example "nonce domain 0 to 99, M = 100" is represented as
`domain_start = 0, domain_end = 100`. Internally the model uses 0-based indices;
"the valid nonce is at the final domain position" means index `M − 1`
(nonce value `domain_end − 1`).

---

## 3. Mathematical model

Let `M` = domain size, `N` = miner count, `r_i` = hash rate (evaluations/s) of
miner `i`, `P_i` = its power (W), `e_i` = energy per candidate evaluation. For
equal miners:

```
e_hash = P_miner / r_miner
```

### 3.1 Attempts (final-nonce worst case)

Duplicate-search worst case — every miner scans the whole domain and all reach
the final nonce simultaneously:

```
A_duplicate = N · M
```

Disjoint allocation — the domain is scanned once, split across miners:

```
A_PoCol = M                      (M divisible by N)
A_PoCol / A_duplicate = 1/N
Reduction               = 1 − 1/N
```

### 3.2 Time and energy (equal miners, concurrent)

```
T_duplicate = M / r_miner
T_PoCol     = ceil(M/N) / r_miner
E_duplicate = N · P_miner · T_duplicate
E_PoCol     = N · P_miner · T_PoCol
```

When `M` is divisible by `N`:

```
E_PoCol / E_duplicate = 1/N
```

### 3.3 Synchronous-step engine (how attempts are actually counted)

All miners start at simulation time 0 and evaluate one candidate per step at the
same rate. Let `t*` be the **global discovery step** = the step at which the owner
of the winning nonce evaluates it (`t* = local_index_of_solution + 1`). Global
stopping means steps `1 … t*` happen in full and nothing after `t*` is evaluated.
Then, **for every miner `i`**:

```
attempts_i     = min(size_i, t*)
active_time_i  = attempts_i / r_i
energy_i       = attempts_i · e_hash          (Method 1)
             = P_i · active_time_i           (Method 2, identical)
```

Network totals are plain sums — **energy is never divided by N and never
multiplied by a redundancy factor**:

```
total_attempts = Σ attempts_i
total_energy   = Σ energy_i
```

Redundancy emerges naturally: in `duplicate_full_domain` every miner's range is
the whole domain, so `size_i = M` and all `N` miners re-evaluate the same nonces
up to `t*`. In `disjoint_partition` each miner's range is its own slice, so the
domain is covered once.

### 3.4 Large domains

For domains up to `2^32` (and larger) the model **never enumerates nonces**. It
computes `size_i`, the owner, `t*`, and `Σ min(size_i, t*)` with integer
arithmetic over the `N` miners only (O(N)). Python big integers make `2^256`
targets and huge domains exact.

---

## 4. Solution models

**A. Deterministic placement.** The single valid nonce may be placed at the
first, middle, or final position, absent entirely, or given as an explicit set.
The **primary worst-case experiment places the only valid nonce at
`domain_end − 1`** (final position).

**B. Target-based stochastic.** Each candidate succeeds with probability

```
p_success = (target + 1) / 2^256
```

or an equivalent configurable Bernoulli `p`. Zero, one, or many valid candidates
and full exhaustion are all possible — success is never guaranteed. Because tiny
`2^256` targets make success astronomically rare, the stochastic runs use a
configurable `p` sized to the analytical domain so that solutions actually occur
(documented per run). First-success positions are drawn as **geometric jumps**
(`⌊ln U / ln(1−p)⌋ + 1`), never by flipping every nonce, so large domains stay
analytical. Baseline and PoCol are compared with **paired seeds**: the shared
template modes (A, B) consume the same first-success draw; independent headers
(C) draw one geometric per miner.

---

## 5. Modes in one table

| Mode | Template | Range per miner | Redundancy | Purpose |
|---|---|---|---|---|
| A `duplicate_full_domain` | one immutable | whole `[0,M)` for all | maximal (all repeat) | worst-case baseline |
| B `disjoint_partition` | one immutable | unique `[s_i,e_i)` | none (covered once) | PoCol allocation |
| C `independent_candidate_headers` | distinct per miner | own sequence | none, but no shared work either | reference / control |

---

## 6. Energy accounting rules (must hold)

- Method 1 (`attempts · e_hash`) and Method 2 (`P · active_time`) agree within
  floating-point tolerance — asserted in code and tests.
- The invalid `block_time / N` rule from the earlier model is **never** used.
- Savings come from **fewer real candidate evaluations and shorter active time**,
  not from dividing a final energy value.

---

## 7. Experiment matrix

**Deterministic worst case** (valid nonce at final position):

- Miner counts: `1, 2, 5, 10, 20, 50, 100, 200, 500`
- Domain sizes: `100, 1 000, 1 000 000, 2^32`
- Compare A vs B; assert reduction `= 1 − 1/N` where `M` divisible by `N`.

**Stochastic** (section 10): ≥ 30 paired seeds per miner population
`100, 200, 300, 400, 500`, large analytical domain, comparing A, B, C, reporting
mean/median/std/95 % CI/effect size and exhaustion probability. The average
stochastic saving is **not** assumed equal to the deterministic worst-case
saving.

---

## 8. Files

```
experiments/nonce_partition/
    __init__.py
    partition.py      # partition_nonce_domain + coverage/disjointness helpers
    model.py          # Miner record, synchronous-step engine, 3 modes, stochastic
    run_scenario.py   # one (mode, M, N, seed) -> JSON
    run_matrix.py     # deterministic + stochastic matrices -> results/*
    statistics.py     # mean/median/std/95% CI/effect size helpers
results/nonce_partition_worst_case/
    deterministic_results.csv
    stochastic_raw_runs.csv
    stochastic_summary.csv
    configuration.json
    reproducibility_manifest.json
tests/test_nonce_partition.py
```

Reproduce:

```bash
python experiments/nonce_partition/run_matrix.py
python -m pytest tests/ -v
```
