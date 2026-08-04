# Stage 6 — PoCol Confirmatory Preregistration (v45)

**Status:** complete and frozen — see `STAGE_06_COMPLETION_REPORT.md`.

| | |
|---|---|
| Accepted frozen executable baseline | `fb8a34d63d9369336d5c1e7aeecdfcf8263920b2` |
| Stage-6 branch | `thesis-v45-pocol-stage6-pilot-preregistration` |
| Adapter result schema | `stage5c.1` (179 keys) |
| Confirmatory scenarios | 22 (limit 24) |
| Confirmatory master seeds | 30 |
| Expected Stage-7 physical runs | **660** |
| Executable model code changed | **none** |

Stage 6 is a **pilot and preregistration stage only**. No confirmatory seed has been executed,
no confirmatory statistical analysis has been performed, and no confirmatory energy, security,
service or incentive claim is made anywhere in this stage.

---

## 1. Claim scope (unchanged, binding on every Stage-6 artefact)

* The algorithm is **PoCol**.
* The energy-saving mechanism is **the idle policy within PoCol**. Nonce-domain partitioning
  alone is **never** described as an energy-saving mechanism.
* The security floor is an **operational active-capacity floor only**.
* The progress-verification layer is a **modeled abstraction**, not a complete cryptographic
  proof.

No Stage-6 artefact claims: unconditional energy reduction; incentive compatibility; fairness;
Sybil resistance; selfish-mining resistance; coalition resistance; common-prefix security;
chain-quality security; Bitcoin-equivalent or PoW-equivalent security.

---

## 2. Authoritative reference configuration

Read from the accepted frozen baseline (`Models/PoCol/stage2/config.py`) and re-asserted by
`scenarios.assert_reference_matches_baseline()` on every generator and validator run.

| parameter | value |
|---|---|
| `num_miners` | 141 |
| `horizon_T` | 10000.0 s |
| `P_hash` | 21.5 W |
| `P_listen` | 2.15 W |
| `P_wake` | 10.75 W |
| `P_offline` | 0.0 W |
| `nonce_domain_size` | 4000 |
| `difficulty` | 1000 |
| `batch_size` | 50 |
| `base_hash_rate` | 100.0 |
| `reserve_fraction` | 0.20 |
| A1 continuous full-participation reference | 8.420833333 kWh |

**A1 verification.** `141 × 21.5 × 10000 / 3600000 = 8.4208333333…`; the declared constant is
`8.420833333`; absolute error `3.333e-10 kWh ≤ 1e-9 kWh`. **Verified.**

**Derived population facts** (mirroring the accepted genesis rule and verified against the
executed engine by the Tier-1 pilot):

* reserve miners `= floor(0.20 × 141) = 28`, namely the last 28 sorted IDs `M113…M140`;
* active primaries `= 113`, namely `M000…M112`, each keeping its enumerate index so
  `hash_rate_for(i) = 100 × (1 + i mod 4)`;
* `H0` (initial active-primary actual hash rate) `= 28100` heterogeneous, `11300` homogeneous;
* total population hash rate `= 35100` heterogeneous.

**Difficulty.** No confirmatory condition changes difficulty dynamically. Difficulty is never an
experimental factor. Any difficulty-control study is EXCLUDED from the confirmatory matrix and
labelled EXPLORATORY (`STAGE_06_EXPLORATORY_MATRIX.csv`, rows X01/X02). The single declared
exception is **C06**, a non-inferential deterministic integrity condition — see §4.

---

## 3. The experimental factor

The Block-A factor is **the idle policy**, indexed by the standby-power ratio
`ρ = P_listen/P_hash = P_reserve/P_hash`.

| level | `P_listen` = `P_reserve` | `P_wake` | meaning |
|---|---|---|---|
| ρ = 1.00 | 21.5 W | **21.5 W** | the idle policy is **OFF** |
| ρ = 0.25 | 5.375 W | 10.75 W | |
| ρ = 0.10 | 2.15 W | 10.75 W | **the frozen reference PoCol idle policy** |
| ρ = 0.00 | 0.0 W | 10.75 W | |

At ρ = 1.00 the transient wake power is also raised to `P_hash`, so both IP-H5 arms satisfy
`P_listen = P_reserve = P_wake = P_hash`. This is not a second factor: it is what switching the
mechanism off means — no state draws less than hashing power while the miner is not offline.
Setting `P_listen = P_hash` alone is **insufficient**, because WAKING and RESERVE residency are
real power-time components: the Tier-1 pilot measured WAKING at **60.5 %** and RESERVE at
**14.0 %** of all residency (the 1.0 s wake latency dominates a ≈1.4 s round). Holding `P_wake`
below `P_hash` at ρ = 1.00 manufactured an apparent "saving" of ≈0.0045 kWh — roughly five
million times the 1e-9 kWh IP-H5 tolerance — so the negative control was measuring the
wake-power discount rather than the absence of an idle policy.

Neither IP-H5 arm carries an injected failure or any OFFLINE transition
(`fault_schedule = NONE`; OFFLINE + DISQUALIFIED residency measured at exactly 0.000 s). With
the correction, IP-H5's residual is measured at **exactly 0.000e+00 kWh**, and the deterministic
decision rule is retained unchanged: absolute paired energy residual ≤ 1e-9 kWh for every seed.

---

## 4. Confirmatory scenario matrix

22 rows in four blocks; full row schema in `STAGE_06_CONFIRMATORY_MATRIX.csv`; per-scenario
frozen configurations in `experiments/thesis_revision_v45/stage_06/confirmatory/frozen_configs/`.

**Block A — mechanistic energy and negative controls** (floor, leases, adversarial and incentive
all disabled).

| id | rates | ρ | paired control | hypotheses |
|---|---|---|---|---|
| A01 | homogeneous | 1.00 | — | IP-H1, IP-H2, IP-H3, IP-H5 |
| A02 | homogeneous | 0.10 | A01 | IP-H1, IP-H2, IP-H3 |
| A03 | heterogeneous 1×–4× | 1.00 | — | IP-H1, IP-H2, IP-H4, IP-H5, IP-H6 |
| A04 | heterogeneous | 0.25 | A03 | IP-H1, IP-H2, IP-H6 |
| A05 | heterogeneous | 0.10 | A03 | IP-H1, IP-H2, IP-H4, IP-H6 |
| A06 | heterogeneous | 0.00 | A03 | IP-H1, IP-H2, IP-H6 |

**Block B — security floor and service** (heterogeneous, ρ = 0.10, leases and adversarial off).

| id | floor | value |
|---|---|---|
| B01 | disabled | — (matched control) |
| B02 | `minimum_active_hash_rate` | `0.80 × H0 = 22480` |
| B03 | B02 **plus** `minimum_active_miner_count` | `113` (the full initial primary count) |
| B04 | deliberately unattainable | `1.50 × 35100 = 52650`, `CONTINUE_DEGRADED` |

Every floor row uses `reserve_selection_policy = MINIMUM_CARDINALITY`,
`activation_trigger_mode = ON_CAPACITY_CHANGE`, `activation_wake_latency = 1.0`,
`floor_tolerance = 0.0`, `floor_unattainable_policy = CONTINUE_DEGRADED`.
**B04 is diagnostic and must not be merged into the primary energy claim.**

`minimum_active_miner_count` for B03 is the *full* primary count because at
`ceil(0.80 × 113)` the Tier-1 pilot measured B03 **identical to B02 in every reported field**,
which would have made the row evidentially empty. At the full count the rows separate
(observations 2385 vs 2359, breaches 194 vs 191, unattainable 918 vs 824).

**Block C — lease and reassignment robustness** (heterogeneous, ρ = 0.10, incentive enabled).

| id | condition | reserve fraction | faults |
|---|---|---|---|
| C01 | leases enabled, no fault (matched control) | 0.20 | none |
| C02 | leases and reassignment disabled | 0.20 | dense |
| C03 | **Path A** — no reserve pool | 0.00 | dense |
| C04 | **Path B** — genuine Stage-3 reserve wake | 0.20 | dense |
| C05 | no eligible miner, `CONTINUE_WITH_UNASSIGNED_RANGE` | 0.00 | dense |
| C06 | full-domain no-block integrity | 0.20 | none |

**C06 declaration.** C06 uses an unreachable fixed target (`2^300`) so that every round
deterministically exhausts the full nonce domain. At difficulty 1000 full-domain exhaustion is a
≈1.8 % chance event, so without this the coverage gate would be a lottery rather than a
certainty. C06 is therefore declared a **non-inferential deterministic integrity condition**: it
has `paired_control_id = NONE`, is excluded from every paired contrast and every multiplicity
family, and contributes to **no** energy, service or incentive claim. Its difficulty is fixed for
the whole run — nothing is controlled dynamically. The same full-domain gate is additionally
evaluated on every other Block-C row wherever natural exhaustion occurs.

**Block D — matched adversarial pairs** (heterogeneous, ρ = 0.10, leases and incentive enabled).
Within each contrast the only difference is the declared attack.

| id | behaviour | control | batch size |
|---|---|---|---:|
| D00 | honest matched control — the entity set declared with **no** behaviour flags | — | 50 |
| D01 | `DELAYED_WAKE`, extra latency 1.0 s | D00 | 50 |
| D02 | `SOLUTION_WITHHOLDER`, `NEVER_RELEASE` | D00 | 50 |
| D03 | `FALSE_EXHAUSTION_CLAIMER`, `audit_detection_probability = 0.0` | D00 | 50 |
| D04C | `D04C_PROGRESS_CONTROL` — entity set declared with **no** behaviour | — | **25** |
| D04 | `D04_PROGRESS_WITHHOLDING`, fraction 0.5, `audit_detection_probability = 0.0` | **D04C** | **25** |

D00–D03 share one fault schedule; the D04C/D04 pair shares its own (§10). The batch-50 D00
control is **not** reused for the IP-H10d contrast.

The adversarial entity set is **fixed by a preregistered rule**: `ceil(0.10 × 141) = 15` miners
selected by sorted MinerID, i.e. `M000…M014`. Attackers were **not** chosen after viewing any
pilot effect. No large incentive-parameter sweep appears in the confirmatory matrix; reward and
identity-splitting sensitivity remain EXPLORATORY (rows X03/X04).

**Fault schedule.** Named `FAULT_SET_DENSE` and frozen before Stage 7: for each round
`k = 1…2000`, inject `MINER_FAILED` for up to four *slow* primaries (index mod 4 = 0, i.e. base
rate) at phases `(k−1)×1.02 + {1.05, 1.15, 1.25, 1.35}` seconds. Rationale and calibration
evidence are in `STAGE_06_PILOT_REPORT.md` §4 and `STAGE_06_DECISION_LOG.md` D-05. The schedule
is fixed; how many injections happen to land is a measured, seed-varying outcome.

---

## 5. Master seeds and the inferential unit

**The inferential unit is one physical run under one master seed** — never a round, a miner, a
block, a transaction, or a repeated row from a single execution.

Three disjoint deterministic registries (`STAGE_06_SEED_REGISTRY.csv`, SHA-256
`4d0369995c6620187f378186515096195f376b6a27ced71e8bd6f80c45bc831b`):

| class | count | source label | index base |
|---|---|---|---|
| PILOT | 8 | `SHA256("PoCol-v45-stage6-pilot-" + index)` | 0-based |
| CONFIRMATORY | 30 | `SHA256("PoCol-v45-stage7-confirmatory-" + index)` | 0-based |
| ANALYSIS | 1 | `SHA256("PoCol-v45-stage8-analysis-" + index)` | 0-based |

The master seed is the **first unsigned 64-bit big-endian integer** of the digest,
`int.from_bytes(digest[:8], "big")`. Disjointness is proved by the generator and re-proved by
the validator: 39 distinct master seeds, 0 overlaps between any two classes, 76 distinct child
seeds, 0 child/master collisions.

**Mapping into the engine — no new seed mechanism.** A master seed reaches the accepted engine
through exactly two accepted configuration fields:

```
template_seed                  = child_seed(master, "template")
adversarial.deterministic_seed = child_seed(master, "adversarial")
child_seed(m, role) = int.from_bytes(SHA256(f"PoCol-v45-child-{role}-{m}").digest()[:8], "big")
```

A child seed depends only on `(master, role)` and never on the scenario, so **both arms of a
paired contrast under the same master seed receive identical seeds**. That is what makes the
pair matched. The validator asserts this directly.

**Paired-condition matching.** A treatment and its control share: master seed; template seed;
adversarial seed; actual miner population; actual hash rates (unless heterogeneity is the
declared factor, i.e. only within Block A); nonce domain; target and difficulty; horizon. Only
the preregistered factor changes. Enforced by validator check [7] over
`num_miners, horizon_T, nonce_domain_size, difficulty, batch_size, base_hash_rate, P_hash,
P_offline`.

**No confirmatory seed has been executed in Stage 6.** Validator check [12] asserts that every
seed appearing in `pilot_results.json` is a PILOT seed and that the pilot∩confirmatory
intersection of executed seeds is empty.

---

## 6. Hypotheses

IP-H1 … IP-H10 are specified in `STAGE_06_IP_HYPOTHESES.md` (human-readable) and
`STAGE_06_IP_HYPOTHESES.json` (machine-readable), each carrying all fourteen required fields.
IP-H10 is split into four separate matched contrasts a/b/c/d.

**Energy success may be claimed only when IP-H7 and IP-H8 both pass.**

---

## 7. Outcomes

`STAGE_06_OUTCOME_DICTIONARY.csv` defines 37 outcomes with all twelve required columns. Every
name is resolved against the accepted adapter schema by **executing**
`Models/PoCol/stage2/adapter.py::results_schema` and checking the key is really present;
`generate_outcome_dictionary.py` aborts with `STAGE_6_PREREGISTRATION_BLOCKED` rather than emit
an unresolved name. Names that are not literal schema keys carry an explicit derivation from
names that are, or from named accepted `RunContext` state. Notable resolutions:

| directive name | resolution |
|---|---|
| `total_energy_kwh` | `results_schema['energy_kwh']` (= `RunContext.total_energy_kwh()`) |
| `accepted_blocks` | `results_schema['rounds_accepted']` |
| `post_round_evaluation_record_count` | `results_schema['post_round_evaluation_count']` — the adapter's own causal computation, identical in definition and tolerance to the accepted Stage-5D audit |
| `post_round_evaluation_nonce_count` | derived by the accepted Stage-5D audit over `evaluation_ledger` + `round_terminal_times` |
| `evaluation_missing_terminal_time_count` | as above; the adapter's `if tt is not None` guard skips these, so the Stage-5D audit is the authority |
| `round_duration`, `median_round_duration` | consecutive differences of `round_terminal_times` (verified strictly increasing in all 42 Tier-1 runs) |
| `nonterminal_activation_request_count` | non-terminal entries of `RunContext.activation_requests` against `security.TERMINAL_REQUEST_STATUSES` |

---

## 8. Analysis, exclusion and retention

Frozen in `STAGE_06_ANALYSIS_PLAN.md` and `STAGE_06_EXCLUSION_RETENTION_POLICY.md`. Summary:
primary unit is the master seed; primary estimand is the mean paired difference against the
matched control; paired sign-permutation (10 000) and paired cluster bootstrap (10 000) over
master seeds, driven by the frozen analysis seed `13165134141831138817`; Holm **within** each of
three families, never combined into one omnibus family; IP-H1, IP-H2, IP-H5 and IP-H9 are
deterministic gates with no p-values; effect sizes and CIs are reported regardless of
significance; `p ≥ 0.05` is never interpreted as evidence of equivalence.

---

## 9. Runtime, archive and Stage-7 execution

`STAGE_06_RUNTIME_AND_ARCHIVE_PLAN.md` and `STAGE_06_STAGE7_EXECUTION_PLAN.md`. No Stage-7 data
directory contains any confirmatory output; `confirmatory/` holds configurations and registries
only, and validator check [9] enforces this.

---

## 10. The IP-H10d matched feasibility pair

IP-H10d is **retained** with its decision rule unchanged. It is carried by its own matched pair
rather than by the batch-50 `D00` control, because the original parameterisation was
**structurally incapable** of producing the state the hypothesis is about.

`adversarial_runtime.apply_progress_withholding` under-reports the **committed** frontier, so an
intermediate committed frontier must exist when the lease is revoked. The frontier advances only
at batch completion, so a batch boundary must fall strictly inside a primary's own range:

```
nonce_domain_size / primary_count  >  batch_size
```

| configuration | nonces per primary | batch size | intermediate frontier possible |
|---|---:|---:|---|
| original D04 (reference batch size) | 35.4 | 50 | **no** |
| **D04C / D04 pair** | **35.4** | **25** | **yes** |

Stage-6 instrumentation — a temporary in-memory wrapper around the accepted entry point, with
**no engine file modified** — measured the call site being reached with the correct `WITHHOLD`
profile in 4 of 4 cases and `committed == lease_start` (`done = 0`) every time. See
`STAGE_06_DECISION_LOG.md` D-11 for the full table.

**The pair.**

| id | role |
|---|---|
| `D04C` | `D04C_PROGRESS_CONTROL` — the adversarial entity set declared with **no** behaviour |
| `D04` | `D04_PROGRESS_WITHHOLDING` — the same set with `PROGRESS_WITHHOLDER`, fraction 0.5 |

Both arms carry `batch_size = 25` and the dedicated `FAULT_SET_PROGRESS` schedule, which is
**frozen** and specified in full — formula, constants, exact fault counts and three executable
proofs — in [`STAGE_06_D04_FAULT_SCHEDULE_FREEZE.md`](STAGE_06_D04_FAULT_SCHEDULE_FREEZE.md).
In summary: the injected set is `adversarial_entity_miners(N, 0.10)` intersected with the
primaries; each miner is injected only at or after **its own** first batch boundary
`1.0 + 25 / hash_rate(m)`, offset by `(0.01, 0.04, 0.07, 0.10, 0.13)` and repeated at
`(k - 1) x nominal_round_period`; the reason is always `MINER_FAILED`; the exact count is
**1 560** faults per Tier-1 run and **15 000** per confirmatory run. A revocation earlier than a
miner's own boundary cannot have crossed a batch boundary, which is why the phases are per-miner
rather than shared. Verified programmatically on **all eight pilot seeds at both tiers**:
`injected_lease_faults` is byte-identical across the two arms in all 16 comparisons, and the
**only** differing `Stage2Config` field is `adversarial`. Identical across the pair:
`num_miners`, `horizon_T`,
`nonce_domain_size`, fixed difficulty and target, actual miner set, actual hash rates,
`reserve_fraction`, security-floor policy, range-lease policy, fault schedule, master seed,
template child seed, adversarial child seed, and every other non-treatment field.

**Provenance.** The change was made before scientific freeze as a feasibility correction. No
pilot effect size, direction, p-value, confidence interval or energy result informed it — only
the reachability inequality, the measured call-site state, and the batch/rate arithmetic. The
accepted engine was not modified. The confirmatory matrix grows from 21 to 22 rows, within the
limit of 24.

**Verification.** `experiments/thesis_revision_v45/stage_06/pilot/ip_h10d_feasibility.json` and
`.../pilot/d04_all_seeds.json` record the executed checks on **disjoint pilot seeds only**,
against `accepted_frontier < actual_frontier`, `physical_frontier_rewind_count = 0`,
`adversarial_reevaluation_count > 0` and
`duplicate_work_reward_prevented_count >= adversarial_reevaluation_count`. The pair was run on
**all eight** pilot seeds (16 runs, all COMPLETED). Every pilot seed is retained, including any
that produces no withholding action; no seed is replaced and none is redrawn. The attack effect
is **not** reported as a confirmatory result.
