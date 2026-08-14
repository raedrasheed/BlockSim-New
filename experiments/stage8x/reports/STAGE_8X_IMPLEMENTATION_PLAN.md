# STAGE 8X — IMPLEMENTATION PLAN

**Phase 1 deliverable (repository audit + design commitment).**
Written *before* any Stage 8X simulation code was executed.

Experiment family: `8X` — *Fixed per-miner ASIC capacity: PoCol disjoint allocation
with post-range low-power vs. traditional competitive PoW.*

---

## 1. Repository audit (what actually exists today)

The repository is a fork of BlockSim (Alharby & van Moorsel) extended with an energy /
carbon layer and a PoCol consensus model.

### 1.1 Entry points and control flow

| Component | File | Semantics found |
|---|---|---|
| Simulation driver | `Main.py` | Selects a model by `InputsConfig.model` **at import time**, runs `p.Runs` sequential runs of an event loop, exports `.xlsx`. |
| Event queue | `Event.py` | `heapq` min-heap keyed on `(time, seq)`; `Queue` is a **class-level global**. |
| Scheduler | `Scheduler.py` | Chooses the `Block` class from `p.model` **at import time**; creates `create_block` / `receive_block` events. |
| Global config | `InputsConfig.py` | A class body with `if model == k:` branches. `NODES` is instantiated **at import time**. |
| Network | `Models/Network.py` | `block_prop_delay() = random.expovariate(1/p.Bdelay)`, `Bdelay = 0.42 s`. |
| Statistics | `Statistics.py` | Class-level mutable accumulators, pandas → Excel export. |

### 1.2 PoW implementation (`Models/Bitcoin/Consensus.py`)

```python
TOTAL_HASHPOWER = sum(m.hashPower for m in p.NODES)
hashPower = miner.hashPower / TOTAL_HASHPOWER
return random.expovariate(hashPower * 1 / p.Binterval)
```

**Semantics:** the aggregate block interval is *pinned* to `Binterval` by construction and
is completely independent of any absolute hash rate. There is no target, no difficulty, no
nonce, and no per-hash success probability. Miner hash rate enters only as a *share*.

*This is exactly the "fixed aggregate network budget" model that Stage 8X must not use.*

### 1.3 PoCol implementation (`Models/PoCol/Consensus.py`)

* Nonce space auto-sized as `S = 2·H_total·T_target` with the comment
  `E[T] ≈ S/(2·H_total)`. This is the mean of a **uniform** draw over `[0,S)`, i.e. the
  solution nonce is sampled uniformly and the round time is the *position* of that nonce
  inside the winner's range. It is **not** a geometric/exponential PoW search, so the
  block-interval distribution is not exponential.
* Losers are scheduled at `winner_time + loser_lag` purely to suppress forks.
* **Energy** is charged as `time_share = block_time / N_miners` per miner
  (`apply_energy_for_created_block`). This deliberately divides each miner's charged time
  by the miner count. It is a *modelling assertion*, not a state × power × time measurement,
  and it structurally guarantees a "saving" proportional to `1/N`.
* There is **no power state machine**, no `LOW_POWER`, no state-residency timers.
* There is **no duplicate-work instrumentation** of any kind.

### 1.4 Energy layer

* `Models/Node.py` — `stop_mining_and_account()` converts *hashes* → kWh via
  `MinerEfficiency_J_per_TH`. Genuine state-time accounting exists in skeleton form but the
  PoCol path does not use it.
* `Models/Energy/energy_models.py` — four standalone, unit-tested analytic models
  (`PowEconomicEnergyModel`, `PosValidatorEnergyModel`, `CommunicationEnergyModel`,
  `CarbonFootprintModel`). Pure, no global state, no `InputsConfig` import.
  Exposes `J_PER_KWH = 3.6e6` and `HASHES_PER_DIFFICULTY = 2**32`.
* `Models/Energy/scenarios.py` — seeded scenario runners + `mean/std/t_critical_95/ci95_halfwidth`.
* `InputsConfig.py` currently carries `NetworkHashRate_Hps = 141e12` and
  `MinerEfficiency_J_per_TH = 21.5` (an S19-XP-class figure). **Stage 8X must not inherit
  either value.**

### 1.5 RNG architecture

All randomness comes from the **process-global `random` module** (`random.expovariate`,
`random.randrange`) plus `random.Random` instances inside `Models/Energy/scenarios.py`.
There is no per-run seeding discipline in the event-driven engine and no seed registry.

### 1.6 Seed registry / result schema / tests / plots

* Seeds: only `experiments/_common.py::SEED_BASE = 20260101` +
  `scenarios.make_seeds(count, base)`, used by the *analytic* revision experiments.
* Result schema: `results/data/*.csv` (raw + summary) from the revision experiments; `.xlsx`
  dumps at the repository root from `Main.py`.
* Tests: `tests/test_energy_models.py` — 11 tests, all passing at audit time
  (baseline recorded).
* Plots: `experiments/_common.py::setup_matplotlib/save_fig` (PNG + PDF).

### 1.7 Stage 6A / 8S / 8U

**These stages do not exist in this repository.** A full-tree search for
`stage`, `6A`, `8S`, `8U`, `stage8` returns only unrelated matches in `docs/`.
There are therefore **no Stage 6A/8S/8U artifacts, seed registries, or nonce-domain
settings in-tree** to reuse or to protect. The task brief's prohibitions on reusing the
Stage 6A constants (141 TH/s, 21.5 J/TH) still bind, because those constants **are** present
in `InputsConfig.py`; the prohibition is honoured by not reading `InputsConfig` at all.

Pre-existing artifacts that Stage 8X must leave byte-identical:
`results/data/`, `results/figures/`, `docs/`, root `*.xlsx`, `Models/`, `InputsConfig.py`,
`Main.py`, `Statistics.py`, `Scheduler.py`, `Event.py`, `tests/`, `experiments/*.py`.
A checksum of all of these is recorded in the freeze manifest and re-verified after execution.

---

## 2. Scientific ambiguities discovered in the existing engine

These are the substantive findings of the audit. Each is resolved explicitly below.

**A1 — There is no probability model to preserve.**
The existing PoW draws the block interval directly from `Binterval`; the existing PoCol draws
a uniform solution position. Neither expresses `SHA256(header‖nonce) ≤ target`. Stage 8X
therefore cannot "preserve" a hash-level semantics that is not there — it must *introduce*
one and document the conversion (brief §9).

**A2 — The existing PoCol energy rule is not state × power × time.**
`block_time / N` is an assumption that manufactures an `O(1/N)` saving. Stage 8X must not
reuse it (brief §13) and does not.

**A3 — Global import-time configuration prevents a 300-run matrix.**
`InputsConfig` binds `model`, `NODES`, `Nn`, `simTime` at import; `Scheduler` binds the
`Block` class at import. Re-running with a different `N` in one process is not supported.
Stage 8X uses an injected, immutable per-run config object instead.

**A4 — Global RNG prevents paired seeding.**
Stage 8X uses per-run `random.Random` streams, split by purpose (search / propagation /
template), so PoW and PoCol at the same `(N, seed)` see matched environmental draws.

**A5 (the important one) — static disjoint allocation with a finite domain has a liveness
gap.** Under the brief's §5 (common immutable template, static disjoint ranges, *no* reserve
miners, *no* useful-work floor, *no* reassignment, *no* borrowing), if the round's nonce
domain contains no solution then every honest miner completes its range and stops, and the
round can never end. With homogeneous S21-Pro miners and equal ranges all miners complete at
the *same* instant `|R_i|/h`, so the network exhausts the domain exactly when the individual
miner does. A literal reading of §5.5–5.6 ("sleep until the next round") therefore deadlocks
the chain whenever the domain misses.
**Resolution (frozen before any result was seen):** a *domain-exhaustion template refresh*.
When all honest ranges are swept without a solution, the common template is refreshed
(`ntime`/extranonce roll), a new disjoint allocation is issued over a fresh domain, and each
miner wakes when it receives the refreshed template. This is the minimal liveness mechanism
that adds none of the four forbidden mechanisms — it is a *round/epoch boundary*, i.e. the
"legitimate wake-up event" of §5.6. Legitimate range completion, global domain exhaustion,
and undersized-domain artifacts are counted separately (brief §10).

**A6 — Under exact-input identity, traditional PoW has ~zero exact duplicates.**
A traditional miner owns a distinct coinbase, hence a distinct template, hence distinct
serialized candidates. Exact duplicate work is therefore ~0 for *both* primary protocols,
and the duplicate-work axis is only non-degenerate against a **common-template** comparator.
This is anticipated by brief §30 and is handled with a declared secondary comparator
(§4.3 below), never by relabelling nonce-value reuse as exact duplication.

---

## 3. Reuse / modify / add

### 3.1 Reused as-is (imported, not copied)

| Component | Use in Stage 8X |
|---|---|
| `Models/Energy/energy_models.J_PER_KWH` | J → kWh conversion (`3.6e6`). |
| `Models/Energy/energy_models.HASHES_PER_DIFFICULTY` | `2**32` in the difficulty derivation. |
| `Models/Energy/scenarios.{mean,std,t_critical_95,ci95_halfwidth}` | Cross-checked against SciPy in the validation suite. |
| BlockSim *design* (heap event queue with `(time,seq)` tie-break; `Exp(1/Bdelay)` gossip delay; longest-chain fork resolution with deterministic tie-break) | Re-implemented against an injected config because of A3/A4; semantics preserved and documented. |

### 3.2 Modified

**Nothing.** No file outside `experiments/stage8x/` is modified, except:
* `experiments/__init__.py` — new empty file so `python -m experiments.stage8x.*` resolves.
  It adds no behaviour and the existing scripts run unchanged (verified).

### 3.3 New files

```
experiments/__init__.py                        (new, empty)
experiments/stage8x/
  __init__.py
  config/__init__.py
  config/asic.py           S21 Pro profile; aggregate H(N), P(N); LP sensitivity table
  config/difficulty.py     D_N derivation, target, per-hash probability, nonce domain
  config/stage8x_config.py frozen immutable RunConfig + experiment matrix + hashing
  config/seeds.py          Stage 8X seed registry generator (30 fresh master seeds)
  simulator/__init__.py
  simulator/hashing.py     real double-SHA256 candidate serialisation + geometric abstraction
  simulator/powerstate.py  ACTIVE/LOW_POWER residency ledger with conservation check
  simulator/engine.py      event-driven engine: X-PW, X-PC, X-PW-MT
  simulator/energy.py      state × power × time accounting incl. alpha sensitivity
  analysis/__init__.py
  analysis/stats.py        paired stats: t / Wilcoxon / CI / effect size / assumptions
  analysis/tables.py       Tables A–G
  analysis/figures.py      Figures 1–13 (+ diagnostics)
  tests/test_stage8x.py    validation suite (brief §25)
  run.py                   --phase pilot|primary|secondary
  validate.py              runs the validation suite + writes the validation report
  freeze.py                manifest, checksums, git hash, environment
  analyze.py               statistics → tables → figures → results report
  outputs/  figures/  reports/
```

**Why no previous experiment is affected:** Stage 8X imports only `Models.Energy.*` (pure,
no global state, no `InputsConfig` import), never `InputsConfig`, `Main`, `Scheduler`,
`Event`, or `Statistics`. It writes only under `experiments/stage8x/`. A pre-execution and
post-execution SHA-256 tree checksum over every pre-existing path proves non-interference.

---

## 4. Frozen scientific design

### 4.1 Hardware (brief §3)

Bitmain **Antminer S21 Pro** nominal specification:
`h = 234 TH/s`, `P_active = 3510 W`, `η = 15 J/TH`, and `234 × 15 = 3510` is asserted in test.
Every simulated miner is exactly one such unit, for every `N`. Hence
`H(N) = N × 234 TH/s`, `P(N) = N × 3510 W`, both computed, never tabulated.

Low power is **not** a vendor mode: `P_low = α·P_active`, `α ∈ {0, 0.10, 0.25, 0.50}`
(LP0 idealized lower bound; LP10/LP25/LP50 non-certified sensitivity assumptions).

### 4.2 Probability semantics and the scaling model (brief §9)

Bitcoin-style. Per-candidate success probability

```
q = target / 2^256 = 1 / (D · 2^32),      D_N = H_N · I_target / 2^32,   I_target = 600 s
```

so `E[hashes/block] = D_N·2^32 = H_N·600` and `E[interval] = 600 s` for the matched PoW
baseline. `D^PoW_N = D^PoCol_N` by construction (a single `D_N` per `N`).

**No trillions of Python hashes are executed.** A miner's search is advanced analytically:
the number of candidates until its next success is drawn exactly from `Geometric(q)` by
inverse transform, and converted to time by dividing by the miner's *physical* rate
`h = 234e12 candidates/s`. This is mathematically identical to enumerating candidates one by
one. The *real* serialisation `header(template, extranonce, nonce)` and double-SHA-256 are
implemented in `simulator/hashing.py` and validated by Monte-Carlo against `q` at an
artificially easy target, which pins the abstraction to true SHA-256 semantics without
enumerating the operational domain.

Candidate identity is the exact serialized input, indexed as `(template_id, candidate_index)`
with `candidate_index = extranonce·2^32 + nonce`. Scanned candidates are recorded as
half-open **intervals**, so exact-duplicate work is computed exactly (sum of lengths minus
size of union, per template) without materialising 10^17 indices.

### 4.3 Protocols

* **X-PW (primary, traditional competitive PoW).** Each miner owns its *own* template
  (distinct coinbase → distinct `template_id`), searches its own candidate space
  independently and sequentially, rolls its own extranonce locally and instantly on
  exhaustion (zero downtime — this is what real hardware does), never receives a coordinated
  range, never enters `LOW_POWER`, and abandons stale work when it accepts a new tip.
* **X-PC (primary, PoCol).** One common immutable template per epoch; the epoch's candidate
  domain is deterministically partitioned into `N` equal, disjoint, miner-owned ranges;
  a miner evaluates only its own range; on completing it with no remaining legitimate work it
  goes `ACTIVE → LOW_POWER`; it wakes on the next legitimate event (a new accepted block, or
  receipt of the refreshed template after global domain exhaustion — see A5). No reserve
  miners, no useful-work floor, no reassignment, no borrowing.
* **X-PW-MT (secondary diagnostic, declared here, reported separately).** Identical to X-PW
  except all miners share the *same* common template as PoCol and pick independent random
  start offsets. This is the only configuration in which exact-input duplicate work is
  non-degenerate (A6). It is **not** part of the primary energy comparison and is stored in
  its own CSV with its own run-ID prefix.

The single structural asymmetry between X-PW and X-PC is therefore: a PoCol miner needs the
*network* to agree on the next common template before it has new legitimate work, whereas a
PoW miner refreshes locally at zero cost. That asymmetry is precisely the mechanism under
test, and it is stated as a limitation.

### 4.4 Nonce domain (brief §10) — principled, not tuned

The per-epoch candidate domain is **derived from the protocol parameters**, not chosen to
favour either side:

```
S_N = H_N · I_target = D_N · 2^32        (one block's expected work per epoch)
range_i = S_N / N = h · I_target = 234e12 × 600 = 1.404e17 candidates  (identical for all N)
```

Rationale: the epoch domain holds exactly the expected work of one block at the target
difficulty. Consequences, all stated *before* execution: `P(no solution in an epoch) = e^-1
= 36.79 %`, so epoch turnover is a *normal, frequent* event (§10.3 satisfiable) yet the
domain is never the binding constraint on block production (§10.2), the per-hash target
probability is untouched (§10.4), and the choice is symmetric in `N` (§10.6). The Pilot
verifies the predicted exhaustion rate; a declared **secondary** epoch-allocation sensitivity
sweep (`τ_epoch ∈ {600, 300, 60, 6} s`) maps the energy↔throughput frontier without touching
the frozen primary.

### 4.5 Matched conditions, horizon, seeds

`T = 10 000 s`; `I_target = 600 s`; gossip delay `Exp(mean 0.42 s)` broadcast to all peers;
longest-chain acceptance with deterministic tie-break; identical genesis; identical logging
precision (raw values unrounded). 30 **fresh** Stage 8X master seeds derived from a declared
Stage-8X-specific base, frozen to `stage8x_seeds.json` with a SHA-256 checksum in the
manifest. `X-PW(N,k)` and `X-PC(N,k)` receive the same master seed and the same purpose-split
sub-streams.

Transactions are **excluded** (`hasTrans=False` equivalent): the workload model is identical
for both protocols and contributes nothing to hashing, energy, or block timing, so including
it would add matched noise without enabling a fair throughput comparison. This is recorded as
a limitation, and blocks-per-hour is used as the service metric.

### 4.6 Energy accounting (brief §13)

`E_PoW = Σ_i P_active · t_active,i`, `E_PoCol(α) = Σ_i [P_active·t_active,i + α·P_active·t_low,i]`,
with `t_active,i + t_low,i = T` asserted per miner per run. α enters **only** here; the
physical trajectory is simulated once per `(N, seed)` and re-priced for the four α values, so
the primary matrix is `5 × 2 × 30 = 300` physical runs and `5 × 4 × 30 = 600` PoCol energy
sensitivity observations. α-invariance of the trajectory is asserted in test.

### 4.7 Declared possible outcomes

Given §4.3 and §4.4 the design *can* produce any of the brief's outcomes A–E. In particular,
because independent PoW with distinct templates already performs no exact duplicate work,
a **null or near-null primary energy result (Outcome C/E) is a live and plausible outcome**
and will be reported as such.

---

## 5. Execution order

1. Phase 1 audit (this document).
2. Phase 2 mathematical spec: ASIC profile, `H(N)`, `P(N)`, `D_N`, domain, state-time ledger.
3. Phase 3 unit tests (brief §25) — must all pass.
4. Phase 4 Pilot: `N ∈ {100,300,500}`, dedicated pilot seeds, never merged into primary.
5. Phase 5 Pilot review → `STAGE_8X_PILOT_REPORT.md`.
6. Phase 6 Freeze → `STAGE_8X_FREEZE_MANIFEST.json`, `STAGE_8X_FREEZE_REPORT.md`.
7. Phase 7 Primary: 300 physical runs (+ declared secondaries in separate files).
8. Phase 8 Completeness audit → `STAGE_8X_EXECUTION_REPORT.md`.
9. Phase 9 Paired statistics + sensitivity.
10. Phase 10 Tables A–G, Figures 1–13, `STAGE_8X_RESULTS_REPORT.md`,
    `STAGE_8X_METHODS_AND_RATIONALE.md`, `STAGE_8X_LIMITATIONS.md`,
    `STAGE_8X_VALIDATION_REPORT.md`, `STAGE_8X_FILE_MANIFEST.json`.

Reproduction sequence (every command is tested):

```
python -m experiments.stage8x.run      --phase pilot
python -m experiments.stage8x.validate
python -m experiments.stage8x.freeze
python -m experiments.stage8x.run      --phase primary
python -m experiments.stage8x.run      --phase secondary
python -m experiments.stage8x.analyze
```
