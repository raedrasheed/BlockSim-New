# Stage 6 — Decision Log

Every non-obvious choice made in Stage 6, with the measurement that motivated it. Recorded so
the distinction between **configuration calibration** (permitted) and **outcome-driven tuning**
(forbidden) is auditable rather than asserted.

**No decision in this log consulted an energy value, a service value, an effect size, or a
direction of difference.** Every measurement cited is a liveness, feasibility or accounting-
integrity quantity.

---

## D-01 — Outcome names are resolved, never invented

Twelve names the directive uses are not literal keys of the accepted `results_schema`. Rather
than invent aliases, each was resolved against real accepted state and the resolution recorded
in `STAGE_06_OUTCOME_DICTIONARY.csv`. `generate_outcome_dictionary.py` **executes** the accepted
adapter, checks every declared key is really present, and aborts with
`STAGE_6_PREREGISTRATION_BLOCKED` otherwise.

Key resolutions: `total_energy_kwh → energy_kwh`; `accepted_blocks → rounds_accepted`;
`post_round_evaluation_record_count → post_round_evaluation_count` (the adapter's own causal
computation, identical in definition and 1e-9 tolerance to the accepted Stage-5D audit);
`post_round_evaluation_nonce_count` and `evaluation_missing_terminal_time_count` → the accepted
Stage-5D audit over `evaluation_ledger` + `round_terminal_times` (the adapter's
`if tt is not None` guard skips missing terminal times, so the Stage-5D audit is the authority);
`round_duration` → consecutive differences of `round_terminal_times`;
`nonterminal_activation_request_count` → non-terminal entries of `RunContext.activation_requests`
against `security.TERMINAL_REQUEST_STATUSES`.

**Measured:** the accepted schema exposes 179 keys; 37 outcomes are defined; all resolve.

---

## D-02 — Round duration is derivable exactly

The engine records no round *start* time, only `round_terminal_times`. Rounds execute strictly
sequentially, so round *k* spans `(terminal[k−1], terminal[k]]` with round 1 starting at
`run_start_time`.

**Measured:** terminal times strictly increasing in **all 42** Tier-1 runs; durations all
positive; their sum equals `last_terminal − run_start_time` exactly, and equals the horizon. The
strict-monotonicity property is recorded per run so the derivation is verified rather than
assumed.

---

## D-03 — IP-H5 is a TRUE power-null control: `P_listen = P_reserve = P_wake = P_hash`

IP-H5 requires the equal-power negative control to show **exactly zero** saving
(≤ 1e-9 kWh). Setting `P_listen = P_hash` **alone is insufficient**, because WAKING and RESERVE
residency are real power-time components of the run's energy, not bookkeeping artefacts:

| state | Tier-1 residency | share |
|---|---:|---:|
| WAKING | 60 956 s | **60.5 %** |
| RESERVE | 14 145 s | **14.0 %** |
| LOW_POWER_LISTEN | 13 467 s | 13.4 % |
| ACTIVE_HASHING | 11 570 s | 11.5 % |

Any state drawing less than `P_hash` while the miner is not offline contributes a real energy
difference. With `P_wake` held at 10.75 W the ρ = 1.00 arm reported a residual against A1 of
**0.00446 – 0.00458 kWh** — roughly five million times the 1e-9 kWh tolerance. The "negative
control" was measuring the wake-power discount, not the absence of an idle policy.

Both IP-H5 arms therefore set `P_listen = P_reserve = P_wake = P_hash = 21.5 W`, and neither
carries an injected failure or any OFFLINE transition (`fault_schedule = NONE`, verified
programmatically; OFFLINE + DISQUALIFIED residency measured at exactly **0.000 s**). The
deterministic decision rule is retained unchanged: absolute paired energy residual ≤ 1e-9 kWh for
every seed.

**Measured after the correction:** residual **0.000e+00 kWh** on both arms, both pilot seeds.

**Scope of the change.** ρ = 1.00 is the level at which *the idle policy is off*, and "off" means
no state draws less than hashing power while the miner is not offline. `P_wake` is raised to
`P_hash` at ρ = 1.00 **only**. At every ρ < 1.00 the transient wake power stays at the frozen
reference 10.75 W, so the ρ = 0.10 row is exactly the reference PoCol idle policy.

**Consequence declared in the analysis plan:** the IP-H6 adjacent contrast 0.25 → 1.00 is the
idle-policy on→off contrast and changes the wake power too; the 0.00 → 0.10 and 0.10 → 0.25
contrasts change only the standby powers. This is stated, not hidden.

---

## D-04 — B03's minimum active-miner count is the full primary count

**Measured (Tier-1, at `ceil(0.80 × primary_count)` = 8):** B03 was **identical to B02 in every
reported field** — observations 2359, breaches 191, unattainable 824, duration below floor
191.858 s, deficit 1840.0, activations completed 147. The count constraint never bound, so the
row carried no information.

**Decision.** `minimum_active_miner_count = primary_count` (113 at confirmatory scale), so the
count constraint genuinely binds.

**Measured (after):** B03 observations 2385, breaches 194, unattainable 918, activations
completed 150 — distinct from B02 on every one of those fields.

This is a liveness calibration: the criterion changed so the row *measures something*, not
because any outcome was more favourable.

---

## D-05 — The fault schedule is dense, and why

**Path A** requires an alive primary whose own range is already EXHAUSTED at the instant another
primary's lease is revoked (`simulator.py::_eligible_reassignment_candidates`, categories 0/1,
which require `st.completed and st.completion_kind == "EXHAUSTED"`).

**Measured at confirmatory population:** rounds last ≈1.00–1.05 s and are dominated by the 1.0 s
wake latency, so a round closes ≈0.03 s after hashing begins (37 of 39 rounds accepted a block in
the probe). The fastest primary needs ≈0.09 s to exhaust its ≈35-nonce range. Therefore **no
primary is ever free during an accepted round.** Only a no-block round — measured at ≈2.4 % of
rounds — opens the window, between the fastest primary's exhaustion and the slowest primary's.

**Measured:** a single injected fault produced **0** Path-A reassignments from 41–77 revocations
across three seeds, at every phase tried, at both a 120 s and a 600 s horizon.

**Decision.** `FAULT_SET_DENSE`: for each round `k = 1…2000`, inject `MINER_FAILED` for up to
four *slow* primaries (index mod 4 = 0, i.e. base rate — these exhaust last and so are still
leased while faster primaries have finished) at phases
`(k−1) × 1.02 + {1.05, 1.15, 1.25, 1.35}` s. Several miners at several phases per round give
many independent chances to land inside the window.

**Measured (after):** at confirmatory population over a 600 s horizon, C03 produced
`leases_reassigned = 2`, `reassignment_requests_seated = 2`, `completed = 2`,
**`wake_handles_created = 0`** — a genuine Path A. At Tier-1, C03 gives a Path A
(`wake_handles = 0`) and C04 gives a genuine Path B (`wake_handles = 3`).

The schedule is fixed before Stage 7. How many injections happen to land is a measured,
seed-varying outcome; the schedule itself does not vary.

**Cost check:** the engine scans `injected_lease_faults` once per round, so an 8000-entry
schedule over ≈9700 rounds is ≈78 M tuple unpacks — seconds, against a run that already takes
many minutes.

---

## D-06 — Block D shares one fault schedule across all five rows

`adversarial_runtime.apply_progress_withholding` acts **only at a reassignment boundary**. With
`fault_schedule = NONE`, D04 was byte-identical to D00 (`accepted = 50/48` in both) and IP-H10d
was vacuous.

**Decision.** Every Block-D row carries a fault schedule, and each **contrast** shares one
schedule across its two arms, so within a contrast the only difference is the declared attack.
D00–D03 share `FAULT_SET_DENSE`; the IP-H10d pair D04C/D04 shares its own `FAULT_SET_PROGRESS`
(see D-11 and D-12), applied identically to both arms of that pair.

**Measured (after, Tier-1):** every Block-D row shows 4 revocations, 4 reassignments, 3 wake
handles — identical infrastructure, differing only in the attack (D01 `delayed_wake_count` 198;
D02 `solution_withholding_count` 13, `withheld_never_released` 13; D03
`false_exhaustion_accepted` 224).

---

## D-07 — C06 uses an unreachable target, and is declared non-inferential

At difficulty 1000 with a 4000-nonce domain, full-domain exhaustion without a block is a
**≈1.8 %** chance event per round `((1 − 1/1000)^4000 ≈ e^−4)`, consistent with the ≈2.4 %
measured. A confirmatory row whose purpose is the full-domain coverage gate would therefore be a
lottery rather than a certainty.

**Decision.** C06 uses an unreachable fixed target (`2^300`) so every round deterministically
exhausts the domain, and is declared a **non-inferential deterministic integrity condition**:
`paired_control_id = NONE`, excluded from every paired contrast, every multiplicity family, and
every energy, service and incentive claim.

This is a **fixed** target for the whole run — nothing is controlled dynamically, and difficulty
is not an experimental factor. The same full-domain gate is additionally evaluated on every other
Block-C row wherever natural exhaustion occurs, so C06 strengthens rather than replaces the
evidence. Genuine difficulty-control studies remain EXPLORATORY (rows X01/X02).

This is a deliberate judgement call on a directive requirement and is flagged for the acceptance
reviewer rather than buried.

**Measured:** C06 produces 0 accepted blocks on both pilot seeds — the zero-block feasibility
path, exercised.

---

## D-08 — The wake ramp is a real below-floor interval, so IP-H7 is preregistered unchanged

**Measured (Tier-1, B02):** `total_duration_below_floor = 191.858 s` of a 200 s horizon, and
`floor_unattainable_count = 824`. Against IP-H7's criteria — `floor_unattainable_count == 0` and
`total_duration_below_floor ≤ 0.01 × horizon_T` — this is a large failure.

**Cause, read from the accepted engine, not inferred:** `simulator.py::_pending_primary_capacity`
states that primaries still WAKING are counted only when deciding whether to seat reserves,
"never in `H_effective`, so the WAKING ramp is a real below-floor interval that is nonetheless
not over-activated against." This is deliberate accepted semantics, not a misconfiguration.

**Decision.** IP-H7 is frozen **exactly as specified**, with its parameters and its success
criteria unchanged. Weakening a success criterion because the pilot suggests it may not be met is
precisely the forbidden use of pilot data. The risk is recorded here and in the pilot report so
the acceptance reviewer sees it before Stage 7, and Stage 8 will report the result honestly
whichever way it falls.

---

## D-09 — Seed index base and child-seed derivation

The directive fixes the digest source labels but not the index base or the child-seed rule.
**Decision:** indices are **0-based** for all three classes; the master seed is
`int.from_bytes(SHA256(label + str(index))[:8], "big")`; child seeds are
`int.from_bytes(SHA256(f"PoCol-v45-child-{role}-{master}")[:8], "big")` for
`role ∈ {template, adversarial}`.

A child seed depends only on `(master, role)` and **never on the scenario**, which is exactly
what makes both arms of a paired contrast share a template and an adversarial seed. Verified
directly by validator check [7].

**Measured:** 39 distinct master seeds, 0 pairwise class overlaps, 76 distinct child seeds, 0
child/master collisions.

---

## D-10 — Configurations are built directly, not through the BlockSim mapping

`adapter.stage2config_from_blocksim` does not expose `heterogeneous_hash_rates` or
`injected_lease_faults`, both of which the matrix requires. Stage 6 therefore constructs the
accepted public `Stage2Config` dataclass directly — the same thing the accepted test suite does
— and reports through the accepted `results_schema`. **No engine code is changed and no engine
capability is added.**

---

## D-11 — IP-H10d gets its own matched feasibility pair (D04C / D04) at `batch_size = 25`

### The defect

`adversarial_runtime.apply_progress_withholding` under-reports the **committed** frontier. Its
guard is

```
done = prog.committed_frontier - lease.lease_start_nonce
if done <= 0: return None                    # nothing committed yet -> nothing to under-report
withheld = int(progress_withholding_fraction * done)
if actual - withheld >= actual: return None  # needs done >= 2 at fraction 0.5
```

so an **intermediate committed frontier must exist** at the moment the lease is revoked. The
frontier advances only on batch completion (`simulator.py`, the HashWork completion handler:
`prog.committed_frontier = max(prog.committed_frontier, commit_end)`), so a batch boundary must
fall strictly inside a primary's own range:

```
nonce_domain_size / primary_count  >  batch_size
```

At the reference `batch_size = 50` that is `4000 / 113 = 35.4 > 50`, which is **false**. The
original parameterisation was **structurally incapable** of producing an intermediate committed
frontier, so IP-H10d could never have been satisfied as first written.

### Measured evidence (before the correction)

Stage-6 instrumentation wrapped the accepted entry point — a wrapper only; **no engine file was
modified** — and recorded the state at every call:

| t | miner | profile | committed | lease_start | done |
|---|---|---|---|---|---|
| 24.490 | M000 | WITHHOLD | 0 | 0 | 0 |
| 24.590 | M004 | WITHHOLD | 144 | 144 | 0 |
| 24.690 | M008 | WITHHOLD | 288 | 288 | 0 |
| 24.790 | M012 | WITHHOLD | 432 | 432 | 0 |

The call site was reached with the correct WITHHOLD profile in 4 of 4 cases, and `done` was 0
every time. Across a full-population probe, 108 revocations and 108 reassignments produced
`progress_withholding_count = 0`.

### The correction

A **dedicated matched pair**, `D04C_PROGRESS_CONTROL` (`D04C`) and `D04_PROGRESS_WITHHOLDING`
(`D04`), both carrying `batch_size = 25`, for which `35.4 > 25` holds. The batch-50 `D00` control
is **not** reused for this contrast.

Verified programmatically: materialising both configs under the same master seed, the **only**
differing `Stage2Config` field is `adversarial`. Identical between the arms: `num_miners`,
`horizon_T`, `nonce_domain_size`, difficulty and target, actual miner set, actual hash rates,
`reserve_fraction`, security-floor policy, range-lease policy, fault schedule, master seed,
template child seed, adversarial child seed, and every other field.

> **Superseded by D-12a, D-12b, D-12c and D-13.** The shared phase list described in the next
> paragraph was the first attempt and produced **zero** withholding actions. The frozen schedule
> uses **per-miner** boundary phases; see
> [`STAGE_06_D04_FAULT_SCHEDULE_FREEZE.md`](STAGE_06_D04_FAULT_SCHEDULE_FREEZE.md) for the
> authoritative specification. The paragraph is retained because this log is a chronological
> record of what was tried and why.

The pair also carries its own `FAULT_SET_PROGRESS` phases `(1.25, 1.30, 1.35, 1.40)` instead of
the Block-C phases `(1.05, 1.15, 1.25, 1.35)`, applied **identically to both arms**. A revocation
earlier than `wake_latency + batch_size / hash_rate = 1.0 + 25/100 = 1.25 s` cannot have crossed a
batch boundary, so the earlier phases can only ever measure `done = 0`. The phases follow from the
batch/rate arithmetic and the measured call-site state.

### Provenance of the choice

* The change was made **before** scientific freeze, as a feasibility correction.
* **No pilot effect size, effect direction, p-value, confidence interval or energy result
  informed it.** The only quantities consulted were: the reachability inequality; the measured
  `committed`/`lease_start` pair at the call site; and the batch/rate arithmetic. All are
  structural feasibility facts, none is an outcome.
* **The accepted engine was not modified.** All eight modules remain byte-identical; the
  instrumentation was a temporary in-memory wrapper used only for diagnosis and is not part of
  any committed artefact.
* IP-H10d is **retained**, not dropped, and its decision rule is unchanged.
* The confirmatory matrix grows from 21 to 22 rows, within the limit of 24.

### Verification

`experiments/thesis_revision_v45/stage_06/pilot/ip_h10d_feasibility.json` records the executed
verification on **disjoint pilot seeds only**, against the four required signals:
`accepted_frontier < actual_frontier` (`accepted_below_actual_count > 0`),
`physical_frontier_rewind_count = 0`, `adversarial_reevaluation_count > 0`, and
`duplicate_work_reward_prevented_count >= adversarial_reevaluation_count`. The attack effect is
**not** reported as a confirmatory result.

---

## D-12 — The IP-H10d injection schedule: per-miner boundaries and the mean round period

Making the D04C/D04 pair carry `batch_size = 25` was necessary but not sufficient. Two further
**timing** properties had to be right before the behaviour could occur at all. Both were derived
from the engine's arithmetic and from measured round structure — never from an effect size, an
effect direction, a p-value or an energy result.

### D-12a — Injection targets must be the ADVERSARIAL primaries

The Block-C schedule targets the *slowest* primaries, because Path-A eligibility needs a miner
that exhausts last. Progress withholding needs the opposite: the revoked owner must itself carry
the `WITHHOLD` profile. At Tier-1 the adversarial set is `{M000, M001}` while the slow primaries
are `{M000, M004, M008}`, so only **one** injected target could ever exercise the behaviour.
`FAULT_SET_PROGRESS` therefore targets every adversarial miner that is also a primary — 2 at
Tier-1, 15 at the confirmatory scale.

### D-12b — Each miner is injected only at or after ITS OWN batch boundary

A miner commits its first batch at `wake_latency + batch_size / hash_rate`, which differs by
rate: `400 → +1.0625`, `300 → +1.083`, `200 → +1.125`, `100 → +1.25`. The **earliest** landing
injection revokes the miner, so a shared phase list earlier than a given miner's boundary
consumes that miner's revocation while its committed frontier is still zero. Measured: a shared
list starting at 1.07 produced 8–10 revocations and **zero** withholding. Phases are therefore
computed per miner as `boundary + {0.01, 0.04, 0.07, 0.10, 0.13}`.

### D-12c — The nominal round period must be the MEAN, not the median

`injected_lease_faults` takes an **absolute** simulation time, while round boundaries are an
emergent, seed-dependent quantity. A fixed schedule of the form `(k-1) x period + phase`
therefore accumulates drift equal to `(mean_round − period) x k`.

The Tier-1 **median** round length is 1.4000 s, but the **mean** is `200 / 154 = 1.2987 s`
because rounds that find a block early are shorter. Using the median drifted the schedule by
**−14.3 s — ten whole rounds — by round 150**, and the injections stopped landing on live leases
entirely:

| round | actual start (seed 0) | nominal at 1.40 | drift |
|---:|---:|---:|---:|
| 1 | 0.0000 | 0.0000 | +0.0000 |
| 20 | 24.0950 | 26.6000 | −2.5050 |
| 100 | 128.1142 | 138.6000 | −10.4858 |
| 150 | 194.2783 | 208.6000 | −14.3217 |

`nominal_round_period` is therefore a declared per-tier constant set to the measured mean:
**1.2987 s** at Tier 1 and **1.02 s** at the confirmatory scale. It is a timing constant used
only to phase injected faults; it enters no outcome and no analysis.

### Measured result — all four required signals, on BOTH Tier-1 pilot seeds

| arm | seed | withholding | accepted < actual | rewind | re-evaluated | duplicate prevented |
|---|---|---:|---:|---:|---:|---:|
| D04 | index 0 | 1 | **1** | **0** | **12** | **12** |
| D04 | index 1 | 2 | **2** | **0** | **24** | **24** |
| D04C | index 0 | 0 | 0 | 0 | 0 | 0 |
| D04C | index 1 | 0 | 0 | 0 | 0 | 0 |

`accepted_frontier < actual_frontier` holds on every treatment seed; the physical frontier never
rewinds; re-evaluation is strictly positive; duplicate reward is prevented for every
re-evaluation; and the control arm shows none of it. These are **feasibility measurements on
disjoint pilot seeds**, not confirmatory effects.

---

## D-13 — The D04 / D04C fault schedule is FROZEN

**Decision.** The `FAULT_SET_PROGRESS` schedule used by the IP-H10d matched pair is frozen
exactly as specified in
[`STAGE_06_D04_FAULT_SCHEDULE_FREEZE.md`](STAGE_06_D04_FAULT_SCHEDULE_FREEZE.md). It was
corrected **once, during the pilot, for structural event reachability only** (D-11, D-12,
D-12a, D-12b, D-12c) and **will not be tuned again** — in particular it will not be re-tuned on
the number of re-evaluated nonces, the number of withholding actions, or the size or direction
of any effect.

**What is frozen.**

| element | value |
|---|---|
| miner-selection rule | `adversarial_entity_miners(N, 0.10) ∩ primaries(N, reserve_fraction)` |
| per-miner boundary | `1.0 + 25 / (100.0 * (1 + i mod 4))` |
| offsets | `(0.01, 0.04, 0.07, 0.10, 0.13)` |
| absolute time | `(k - 1) * nominal_round_period + boundary(m) + offset` |
| Tier-1 period | 1.2987 s |
| confirmatory period | 1.02 s |
| round count | `min(200, floor(horizon_T / period) + 2)` → 156 (Tier 1), 200 (confirmatory) |
| **faults per run** | **1 560** (Tier 1), **15 000** (confirmatory) |
| reason | `"MINER_FAILED"` — the only reason emitted |

**Three proofs, all executable.**

1. *Byte-identical schedules across arms.* `test_s6_31` compares
   `injected_lease_faults` for `D04C` and `D04` on all eight pilot seeds at both tiers — 16
   comparisons, all equal — and asserts the two configurations differ in exactly one
   `Stage2Config` field, `adversarial`.
2. *No dependence on effect magnitude or direction.* `test_s6_32` asserts `_fault_schedule`'s
   signature is `(name, num_miners, reserve_fraction, horizon_T, period)` and that its source
   references no outcome-field name, no result object, no energy or reward quantity and no file
   read. The correction was derived from a reachability inequality plus a measured *call-site
   state* (`committed == lease_start`, `done = 0`), which is a statement that the modelled event
   could not occur at all — not a statement about how large or in which direction it was.
3. *Not generated per master seed.* `_fault_schedule` takes no seed. `test_s6_33` asserts that
   the SHA-256 digest of the materialised tuple over all eight pilot seeds collapses to exactly
   one value per arm per tier, and that those digests match the ones documented in the freeze
   document.

**Verification across all eight pilot seeds.** The pair was executed on every pilot seed at
Tier 1 (`run_pilot.py --d04-sweep`; 16 runs, all COMPLETED, ~0.8–1.3 s each). Every treatment
seed produced `accepted_frontier < actual_frontier`, zero physical frontier rewinds, strictly
positive re-evaluation, and duplicate-reward prevention for every re-evaluation; every control
seed produced none of it. **Zero-action seeds: 0 of 8.** The retention rule stands regardless of
that outcome and is not conditional on it: a pilot seed producing no withholding action would be
retained with its zero-action result recorded, never replaced and never redrawn.

These are feasibility measurements on pilot seeds disjoint from the confirmatory registry. They
are not a confirmatory result and no attack effect is reported from them.
