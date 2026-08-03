# Stage 5 — Adversarial-Behaviour and Incentive Model: Implementation Report

**Branch:** `thesis-v45-pocol-stage5-adversarial-incentive-model`
**Base:** `4402bd084fc404cac1d8d85a44fb5d642544c448` (accepted, frozen Stage-4C baseline)
**Adapter result schema:** `stage5.1`
**Tests:** 150 passed (124 accepted Stage-4C tests retained + 26 new S5-01 … S5-26)

---

## 1. What Stage 5 is, and what it is not

Stage 5 adds an explicit, bounded **adversarial-behaviour layer** and a parameterised
**incentive layer** on top of the accepted PoCol core. It **models** bounded behaviours and
**measures** the outcomes those behaviours produce.

Stage 5 does **not** claim, and nothing in this stage establishes:

- incentive compatibility;
- fairness;
- Sybil resistance;
- selfish-mining resistance;
- coalition resistance;
- common-prefix security;
- chain-quality security;
- Bitcoin-equivalent or PoW-equivalent security.

Stage 5 does not prove that PoCol *defeats* any of the behaviours it models. Where a modeled
attack succeeds, this report says so plainly.

Unchanged framing carried forward from the accepted stages:

- the algorithm is **PoCol**;
- the energy-saving mechanism is **the idle policy within PoCol** — reserve, idle and waking
  residency charged at low power;
- **nonce-domain partitioning alone is never an energy-saving mechanism**, and is not described
  as one anywhere in this stage;
- the security floor remains an **operational active-capacity floor only**;
- **dynamic difficulty remains excluded**; no Stage-5 parameter changes the fixed SHA-256 target
  or difficulty (verified executably by S5-26).

## 2. Disabled by default

Every Stage-5 feature is off by default. `AdversarialPolicy.enabled` and
`IncentivePolicy.enabled` are both `False`, all eight reward/penalty rates are `0.0`, and no
entity or behaviour is declared. A default run touches no Stage-5 registry: measured scenario
`A_honest_baseline_disabled` produces `behaviour_profile_count = 0`,
`incentive_ledger_entries = 0` and `maximum_q_adv = None` (NA — never observed).

This is why the accepted 124-test Stage-4C baseline is behaviourally unchanged, and why the
Stage-2B search core (`Models/PoCol/stage2/search.py`) is **byte-identical** to the frozen
baseline. The whole Stage-5 diff is 451 insertions and 6 deletions; all 6 deletions are the
`stage4.1` → `stage5.1` schema-version literal (one in `adapter.py`, one import line, four in
retained tests). No accepted test was weakened, renamed or removed.

## 3. What was built

### 3.1 `Models/PoCol/stage2/adversarial.py` (new) — the data model

Declared vocabularies (`ACTOR_CLASSES`, `BEHAVIOUR_FLAGS`, `SOLUTION_RELEASE_POLICIES`,
`CLAIM_TYPES`, `REWARD_COMPONENTS`, `PENALTY_COMPONENTS`, `ACCOUNTING_MODES`,
`AVAILABILITY_STATES`), the two validated policy dataclasses, the immutable record types
(`AdversarialEntity`, `MinerBehaviourProfile`, `ProgressClaim`, `WithheldSolutionRecord`,
`DelayedWakeAction`, `InvalidActionRecord`, `IncentiveLedgerEntry`), the deterministic
`audit_draw`, and the closure label `ROUND_CLOSED_WITH_ADVERSARIAL_COVERAGE_GAP`.

Both policies validate at construction: undeclared actor classes, undeclared behaviour flags,
unsupported release policies and accounting modes, out-of-range probabilities and fractions, and
negative rates all raise `ValueError` (S5-03).

### 3.2 `Models/PoCol/stage2/adversarial_runtime.py` (new) — the runtime hooks

Every function returns the honest default unless the model is explicitly enabled. The hooks
cover behaviour materialisation, delayed wake, solution withholding, the modeled audit,
false-exhaustion and progress-withholding, invalid-action recording, `q_adv(t)` accumulation,
the incentive ledger, and round-terminal cleanup.

### 3.3 Wiring into the accepted core

Ten call sites in `simulator.py`, all additive:

| Where | Hook | Requirement |
|---|---|---|
| `_handle_prepare_participants` | `snapshot_availability`, `materialise_behaviours` | S5-1, S5-10 |
| `_start_wake` | `wake_extra_latency` | S5-7 |
| `_handle_wake_complete` | `complete_delayed_wake` | S5-7 |
| `_handle_hash_work` (entry) | `maybe_out_of_range_attempt` | S5-9 |
| `_handle_hash_work` (winner branch) | `maybe_withhold_solution` | S5-6 |
| `_handle_hash_work` (continue branch) | `maybe_false_exhaustion` | S5-5 |
| `_maybe_terminate_no_block` (both paths) | `round_has_coverage_gap` | S5-5, S5-6 |
| `_bind_reassigned_lease` | `apply_progress_withholding`, `note_reassignment_reeval` | S5-5 |
| `_close_and_publish` | `close_adversarial_round` | S5-12 |
| `_handle_acceptance` | `acceptance_times` record | S5-6, S5-11 |

Plus one new event (`WithheldSolutionReleaseEvent`, microphase ordinal 25) and its handler
`_handle_withheld_release`.

## 4. The three-value separation (S5-3 / S5-4)

Every quantity a miner can lie about is carried at three levels:

- **actual** — ground truth. The physical search core *always* runs on the actual effective
  hash rate and the actual searched frontier.
- **reported** — what the miner claims.
- **accepted** — what the protocol acts on after the modeled audit.

The critical consequence, measured in scenario `D_hash_rate_misreporter`: a miner reporting 3×
its real rate records `allocation_distortion_max_ratio = 3.0` and 30 divergence events, yet
evaluates *exactly* as many nonces as an honest miner. Misreporting buys no real work.

The audit itself is a **model parameter**, not a cryptographic verification claim. It is a
deterministic SHA-256 draw over the policy seed and the immutable claim identity, so replaying a
claim yields the same verdict and creates no second record.

## 5. Measured outcomes

All figures below come from `STAGE_05_ADVERSARIAL_INCENTIVE_METRICS.json`, regenerable with
`python docs/thesis_revision_v45/stage_05/generate_stage5_metrics.py`.

### 5.1 Where the modeled attacks succeed

**They do succeed, and the model records it.**

- **Solution withholding denies liveness completely.** With all four miners withholding under
  `NEVER_RELEASE` (scenario G), **zero** blocks are accepted across the whole horizon, against
  29 in the honest control. Four valid solutions were found and hidden. PoCol does not defeat
  this; the model measures it.
- **Undetected false exhaustion leaves real holes.** With the modeled audit at p = 0
  (scenario F), 40 accepted claims leave **3,000 nonces unsearched**. The protocol is not
  allowed to pretend otherwise: every such round closes as
  `ROUND_CLOSED_WITH_ADVERSARIAL_COVERAGE_GAP`, never as a full-domain exhaustion.
- **Delayed wake is a real liveness cost.** A +5.0 s wake delay (scenario I) cuts completed
  rounds from 29 to 8.
- **Free riding reduces throughput.** At `work_fraction = 0.5` (scenario C), rounds fall from
  29 to 19 and the free rider's evaluated nonce count drops correspondingly.

### 5.2 Where the modeled audit blocks the attack

With detection at p = 1 (scenario E), all 90 false-exhaustion claims are caught and rejected,
the coverage gap is 0, and the round reaches its ordinary honest disposition. This is a
property of the **assumed** detection probability, not a property PoCol is shown to possess.

### 5.3 The accounting-amplification exposure (S5-8)

| Scenario | Naive per-identity | Entity-and-lineage deduplicated | Ratio |
|---|---:|---:|---:|
| L — one entity holding all 4 identities | 47,900.0 | 11,975.0 | **4.00×** |
| K — one entity, ×4 split and 3 identities | 44,700.0 | 11,975.0 | **3.73×** |
| C, D, E, F, I, J — single-identity attacker, no split | unchanged | unchanged | 1.00× |

Deduplicating on range lineage removes the amplification entirely. Amplification is attributed
**only to the entity that actually declares the identities or the split**: a miner with no
declared entity multiplies nothing, which is why scenario K's aggregate ratio (3.73×) is below
that entity's own 12× per-entity factor — the other three miners are not amplified. Both views
are computed in parallel and both are reported.

**This is an accounting measurement, not a Sybil-resistance claim.** It shows what the
deduplication rule removes from the *reward ledger*. It says nothing about an adversary's
ability to acquire identities, and it is not a defence.

### 5.4 The matched pair (S5-13)

Identical configuration in both arms — same miner count, nonce domain, template seed, and the
same fixed target and difficulty — differing only in the declared adversarial configuration:

| Metric | Delta (attacked − baseline) |
|---|---|
| `rounds_accepted` | **−29** (29 → 0) |
| `evaluation_ledger_entries` | −25 |
| `energy_kwh` | −0.000278 |
| `solution_withholding_count` | +4 |

**The negative energy delta must not be read as a saving.** Energy fell because withholding
miners stop hashing and drop to low power — the protocol failed to produce any block at all.
Spending less energy while delivering nothing is a liveness failure, not an efficiency result.
The energy-saving mechanism in PoCol remains the idle policy, evaluated under the accepted
matched-control identity experiment, not this.

Likewise, delaying a wake (S5-16) is charged `P_wake` over the whole extended interval: measured
WAKING residency and wake energy both strictly increase. Delaying a wake costs energy; it never
saves it.

### 5.5 Invariants holding in every scenario

| Invariant | Result |
|---|---|
| Max incentive reconciliation residual | **0.0** |
| Residency reconciles in every scenario | **true** |
| No full-domain-exhaustion label in any gapped scenario | **true** |
| `q_adv` never fabricated when inactive | **true** |
| Disabled baseline has zero Stage-5 effect | **true** |

## 6. `q_adv(t)` and the NA rule (S5-11)

`q_adv(t) = H_adversarial(t) / H_active(t)` over **actual** active hash rates, accumulated
piecewise-constant across intervals. When `H_active(t) = 0` the ratio is undefined and is
recorded as **NA** — it is never compared against the threshold and never enters the
time-weighted mean. Every measured scenario carries a non-zero `q_adv_na_duration` (the pre-wake
and post-exhaustion gaps), and those seconds are excluded from both statistics.

`q_adv` is a **composition measurement**. It is not a security threshold, and crossing it
implies nothing about safety. The security floor remains the operational active-capacity floor.

## 7. Scope discipline

Not done, and deliberately so: no Stage 6, no preregistration, no confirmatory experiment
matrix execution, no statistical analysis, no thesis integration. No Stage-1 document, protected
DOCX/PDF, or prior-stage evidence file was touched. The accepted Stage-2B search core was not
modified.

The micro-scenarios in this report exist to demonstrate that the executable paths work. They are
deterministic single runs, not samples, and no statistical claim is derived from them.
