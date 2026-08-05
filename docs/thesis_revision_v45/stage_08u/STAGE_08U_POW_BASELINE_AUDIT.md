# Stage 8U — Phase 0: PoW Baseline Audit (read-only)

**Branch:** `thesis-v45-pocol-stage8u-single-handoff-pow-comparison`
**Baseline:** exact remote HEAD `bb588e881b667ed021d6cdbbda9971a14a0ae259` of
`thesis-v45-pocol-stage8s-useful-floor-coarse-reassignment` (fetched, checked out, clean
worktree; Stage-8S checksum manifest verified; 235 accepted tests green; difficulty 1000
and its fixed target verified unchanged; matplotlib 3.11.1 available for the figure
pipeline).

**Purpose.** Before implementing anything, this audit records every existing PoW
implementation, adapter, simulator path and historical result in the repository, and
decides — per the directive — whether any of them can serve as a *fairly matched*
same-template PoW control for the Stage-8U comparison. "Fairly matched" means: the same
immutable per-round template, the same SHA-256 work primitive, the same fixed target and
difficulty, the same nonce-domain size, the same horizon, seeds, actual hash rates, power
values, causal event ordering, block-acceptance point, stale-event cancellation, and the
same energy/residency accounting identities as the accepted PoCol Stage-2 engine.

**Verdict (summary).** No existing PoW implementation is fair-matchable. A new ADDITIVE
matched PoW control (`Models/PoCol/stage2/matched_pow.py`) will be created that reuses the
accepted Stage-2 primitives verbatim. No legacy PoW code is rewritten, and no old thesis
PoW numbers are reused, because their assumptions differ (documented per implementation
below).

---

## 1. Legacy BlockSim Bitcoin PoW model

* **Files / classes:** `Models/Bitcoin/Consensus.py` (`Consensus`),
  `Models/Bitcoin/BlockCommit.py` (`BlockCommit`), `Models/Bitcoin/Node.py` (`Node`),
  shared base `Models/Consensus.py`, `Models/BlockCommit.py`, `Models/Node.py`
  (`start_mining` / `stop_mining_and_account`), driven by `Main.py`, `Scheduler.py`,
  `Event.py`, `InputsConfig.py`, `Statistics.py`.
* **Hash primitive:** none. Mining time is drawn from an exponential distribution:
  `random.expovariate((hashPower/Σ hashPower) · 1/Binterval)`
  (`Models/Bitcoin/Consensus.py:13-17`). No digest is ever computed.
* **Template construction:** none. Blocks reference a previous-block id (`event.block.previous`);
  there is no immutable per-round header, no `TemplateID`, no committed template.
* **Nonce-search policy:** none. There is no nonce domain; "work" is a sampled waiting
  time, so per-nonce search order, offsets, and coverage are undefined.
* **Target / difficulty rule:** implicit and dynamic-free but not target-coupled: the
  block interval `p.Binterval` parameterises the exponential rate. There is no
  `target = floor((2^256−1)/difficulty)` rule and no digest-≤-target acceptance.
* **Rate semantics:** `hashPower` is a *share* (normalised against the population sum,
  `Models/Node.py:75-86`), not an absolute nonces/second rate as in Stage 2.
* **Energy accounting:** wall-clock mining-interval accounting via
  `start_mining`/`stop_mining_and_account` (`Models/Node.py:140-152`) and the
  `Models/Energy/wallclock_energy.py` `MinerEnergyState` residency machine. Power states
  do not match the Stage-2 five-state model (no LOW_POWER_LISTEN / RESERVE_STANDBY /
  WAKING taxonomy, no per-state residency identity checks).
* **Event ordering:** `Scheduler`/`Event` queue ordered by time only; no microphase
  ordinals, no deterministic tie-breaking contract, no EventDescriptor schema.
* **Round closure:** none — the chain grows continuously; there is no finite-domain round
  that can close with zero blocks, and no full-domain-exhaustion closure.
* **Stale-work cancellation:** on `receive_block`, a node stops mining and re-arms on the
  new tip (`Models/Bitcoin/BlockCommit.py:50-75`); forks are resolved retroactively by
  longest-chain (`fork_resolution`). This is a *tip-race* model, not the Stage-2
  first-valid-solution-by-simulation-time round model.
* **Physical / duplicate evaluation measurability:** impossible. With no nonces evaluated
  there is no `total_physical_evaluations`, no unique/duplicate split, and no evaluation
  ledger.
* **Fair-matchability: NO.** No shared template, no SHA-256 primitive, no fixed target,
  no nonce domain, share-based rates, different energy states, different event-ordering
  and closure semantics. Matching would require a rewrite, which the directive forbids
  (legacy code must not be rewritten).

## 2. Legacy BlockSim Ethereum PoW variant

* **Files / classes:** `Models/Ethereum/Consensus.py`, `Models/Ethereum/BlockCommit.py`,
  `Models/Ethereum/Node.py`.
* **All fields:** identical abstraction to §1 — exponential mining-time draw
  (`random.expovariate(frac · 1/Binterval)`), no hashing, no template, no nonce domain,
  share-based `hashPower`, wall-clock energy, time-ordered queue, no round closure, tip
  races, no evaluation measurability.
* **Fair-matchability: NO**, for the same reasons as §1.

## 3. Economic PoW energy model (reviewer-response layer)

* **Files / classes:** `Models/Energy/energy_models.py`
  (`PowEconomicEnergyModel`), `Models/Energy/scenarios.py` (`run_pow_scenario`,
  Poisson block counts, Dirichlet hash-power shares),
  `Models/Energy/wallclock_energy.py` (unit helpers, `MinerEnergyState`),
  experiment drivers `experiments/run_pow_miner_scaling.py`,
  `experiments/run_pow_price_sensitivity.py`, `experiments/run_carbon_gamma_sensitivity.py`.
* **Hash primitive:** none — closed-form accounting. Expected hashes per block use the
  external convention `difficulty · 2^32` (`HASHES_PER_DIFFICULTY`,
  `energy_models.py:32`), which is NOT the Stage-2 rule
  `target = floor((2^256−1)/difficulty)` with per-nonce success probability
  `(target+1)/2^256`.
* **Template construction / nonce-search policy:** none.
* **Target / difficulty rule:** economic bound `E_budget = κ·R_t/C_elec` optionally
  min-ed with a technical bound from `difficulty·2^32·j_per_hash`; no acceptance rule.
* **Rate semantics:** network-level TH/s with Dirichlet-sampled shares — not the frozen
  per-miner 100/200/300/400 nonces/s actual rates.
* **Energy accounting:** kWh from fiat budgets or J/hash efficiencies; no per-state
  residency, no energy identity `Σ per-state = total`.
* **Event ordering / round closure / stale-work cancellation:** not applicable (no event
  loop).
* **Physical / duplicate evaluation measurability:** none.
* **Fair-matchability: NO.** This layer answers an economics question (energy bounded by
  reward value), not a matched work-execution question. Its difficulty semantics
  (`·2^32`) actively conflict with the accepted Stage-2 target rule; silently reusing its
  numbers would mix incompatible assumptions.

## 4. Legacy PoCol consensus (pre-Stage-2)

* **Files / classes:** `Models/PoCol/Consensus.py`, `Models/PoCol/BlockCommit.py`,
  `Models/PoCol/Node.py`, `Models/PoCol/round_state.py`.
* **Nature:** finder-based PoCol round model (Stage-3 of the *legacy* line): probability
  `p = 1/(H_total·B)`, finite domain with expected solutions `μ = p·S`, exhaustion and
  template regeneration — but winners are *sampled* rather than target-coupled, and the
  work primitive is not an executed SHA-256 digest per nonce.
* **Fair-matchability as a PoW control: NO** — it is not a PoW implementation at all
  (partitioned cooperative search), and it predates the accepted target-coupled core.
  Listed only for completeness of the sweep.

## 5. Accepted Stage-2 PoCol search core (shared primitive, not a PoW control)

* **Files / classes:** `Models/PoCol/stage2/search.py` (`sha256_int`,
  `target_for_difficulty`, `success_probability`, `Template`, `make_template`,
  `partition_domain`, `MinerSearchState`), used by `simulator.py` under the accepted
  evaluation-ledger, residency and energy-identity contracts.
* **Status:** this is NOT a PoW implementation (miners search disjoint assigned ranges
  under a coordinator), but it is the *only* code in the repository with the immutable
  per-round template, real `SHA256(header||nonce)` work primitive, fixed
  `target = floor((2^256−1)/difficulty)` acceptance, and measurable physical
  evaluations. The matched PoW control therefore reuses exactly these primitives
  (`make_template`, `sha256_int`, `target_for_difficulty`) so that PoW and PoCol evaluate
  the *same* templates under the *same* target — satisfying U-TEST-02 by construction.

## 6. Historical PoW result artifacts (must not be silently reused)

* Repo-root workbooks `Bitcoin_20260122_*.xlsx` and `Ethereum_20260122_*.xlsx`
  (24-hour horizons, exponential model of §1/§2).
* `results/data/pow_miner_scaling_*.csv`, `pow_price_sensitivity_*.csv`,
  `carbon_gamma_*.csv` (economic model of §3).
* Any PoW figures/tables derived from these in the legacy thesis chapters.

**Ruling:** none of these numbers enter Stage-8U. Their generating assumptions
(exponential waiting times or economic budgets; share-based rates; `difficulty·2^32`
hash expectation; no fixed 1600-nonce domain; no 300 s horizon; different power model)
differ from the matched-comparison assumptions, so quoting them beside Stage-8U results
would be an unmatched comparison. They remain untouched as historical evidence.

---

## 7. Decision

No compatible PoW implementation exists. Stage 8U therefore creates an ADDITIVE module
`Models/PoCol/stage2/matched_pow.py` implementing the **matched same-template PoW
control** with:

* the same immutable template per round (`make_template` with the identical
  template-seed stream the PoCol scenarios use), same SHA-256 primitive, same fixed
  target and difficulty (1000), same nonce-domain size (1600), same horizon (300 s),
  same master seeds, same actual per-miner rates (100/200/300/400 nonces/s), same power
  values, and the same causal block-acceptance point (first valid target-coupled
  solution by simulation time) with stale-event cancellation at acceptance;
* independent full-domain search per miner with deterministic seed-derived starting
  offsets and wraparound (overlap allowed — PoW miners do not coordinate), so
  `total_physical_evaluations`, `unique_physical_evaluations`,
  `duplicate_physical_evaluations`, `first_valid_solution`,
  `post_round_evaluation_count`, `energy_identity_residual` and
  `residency_partition_residual` are all measurable and recorded per run;
* two never-merged scenario variants: `W00_POW_POPULATION_MATCHED` (all 20 miners mine
  continuously) and `W01_POW_ACTIVE_CAPACITY_MATCHED` (exactly the 16 initially active
  primaries mine; the 4 reserve nodes stand by at `P_reserve` without mining — an
  explicitly labelled artificial capacity-matched control);
* no dynamic difficulty anywhere.

Legacy PoW code (§1–§4) is left byte-identical. This audit is read-only: no engine file
was modified before it was written.
