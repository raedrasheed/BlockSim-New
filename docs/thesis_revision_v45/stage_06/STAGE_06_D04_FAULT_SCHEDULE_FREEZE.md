# Stage 6 — Frozen D04 / D04C fault-schedule specification

**Status: FROZEN.** The schedule specified below was corrected once during the pilot, **for
structural event reachability only**, and is now frozen. It may not be tuned again. In
particular it may not be re-tuned on the number of re-evaluated nonces, on the number of
withholding actions, on the size of any effect, or on the direction of any effect.

Everything on this page is a restatement of executable code. The single source of truth is
`experiments/thesis_revision_v45/stage_06/scenarios.py::_fault_schedule` with
`name = "FAULT_SET_PROGRESS"`; this document exists so that the schedule can be audited without
executing it, and so that the freeze is reviewable.

---

## 1. What the schedule is

`Stage2Config.injected_lease_faults` is an accepted-engine field: a tuple of

```
(round_seq: int, miner_id: MinerID, absolute_time: float, reason: str)
```

entries, scanned once per round by the accepted engine. Stage 6 adds no engine mechanism; it
only materialises this tuple. The `FAULT_SET_PROGRESS` schedule is used by **exactly two
scenarios** — `D04C_PROGRESS_CONTROL` and `D04_PROGRESS_WITHHOLDING` — which together form the
IP-H10d matched feasibility pair.

## 2. Adversarial miner-selection rule

The injected set is

```
miners = { m : m in adversarial_entity_miners(N, ADVERSARIAL_FRACTION) } ∩ primaries(N, reserve_fraction)
```

where

```
adversarial_entity_miners(N, f) = miner_ids(N)[0 : ceil(f * N)]          # ADVERSARIAL_FRACTION = 0.10
primaries(N, rf)                = miner_ids(N)[0 : N - floor(rf * N)]
miner_ids(N)                    = ("M000", "M001", ..., zero-padded, sorted)
```

Reserves are excluded because a reserve holds no primary range lease, so a lease fault against a
reserve cannot revoke a lease and cannot produce the state IP-H10d is about.

The rule was fixed **before** any pilot effect was inspected: it is the same preregistered
adversarial-entity rule used by every other Block-D scenario, intersected with a structural
predicate (holds a primary lease). It contains no reference to any measured quantity.

| scale | N | reserve_fraction | adversarial set | ∩ primaries | injected miners |
|---|---:|---:|---:|---:|---|
| Tier 1 (pilot) | 12 | 0.20 | 2 (`M000`,`M001`) | 2 | `M000`, `M001` |
| Confirmatory / Tier 2 | 141 | 0.20 | 15 (`M000`..`M014`) | 15 | `M000` … `M014` |

## 3. Per-miner batch-boundary time formula

`apply_progress_withholding` can only under-report a frontier that has already advanced, and
`RangeProgress.committed_frontier` advances **only at batch completion**. So a fault must arrive
**at or after** the miner's own first batch boundary, and each miner's boundary is different
because hash rates are heterogeneous.

For miner `Mi` (integer index `i`):

```
rate(Mi)     = base_hash_rate * (1 + (i mod 4))            # accepted hash_rate_for rule
boundary(Mi) = wake_latency + batch_size / rate(Mi)
             = 1.0 + 25 / rate(Mi)
phases(Mi)   = ( round(boundary(Mi) + off, 6)  for off in PROGRESS_FAULT_OFFSETS )
```

with `wake_latency = 1.0` (the accepted `Stage2Config` default) and `batch_size = 25`
(`PROGRESS_PAIR_BATCH_SIZE`, applied to **both** arms via `batch_size_override`).

The absolute injection times are then

```
for k in 1 .. rounds:
    for m in sorted(miners):
        for p in phases(m):
            emit (k, m, round((k - 1) * period + p, 6), "MINER_FAILED")
```

Resulting round-1 phase values (identical at both scales, because they depend only on `i mod 4`):

| `i mod 4` | rate | boundary | phases (round 1) |
|---:|---:|---:|---|
| 0 | 100.0 | 1.25 | 1.26, 1.29, 1.32, 1.35, 1.38 |
| 1 | 200.0 | 1.125 | 1.135, 1.165, 1.195, 1.225, 1.255 |
| 2 | 300.0 | 1.083333 | 1.093333, 1.123333, 1.153333, 1.183333, 1.213333 |
| 3 | 400.0 | 1.0625 | 1.0725, 1.1025, 1.1325, 1.1625, 1.1925 |

## 4. Declared period constants

`injected_lease_faults` carries an **absolute** simulation time, while round boundaries are an
emergent quantity. The schedule therefore uses a declared nominal round period per tier:

| constant | value | where |
|---|---:|---|
| Tier-1 `nominal_round_period` | **1.2987 s** | `scenarios.TIER1` |
| Confirmatory / Tier-2 `nominal_round_period` | **1.02 s** | `scenarios.TIER2` |
| module default `FAULT_PERIOD` | 1.02 s | `scenarios.FAULT_PERIOD` |

These are timing constants used **only** to phase injected faults. Neither enters an outcome
definition, a hypothesis, an analysis, or any reported quantity. The Tier-1 value is the
measured **mean** round length (`200 / 154`), not the median — see decision-log D-12c for the
drift measurement that forced this.

## 5. Round-count formula and exact fault count per run

```
rounds = min(PROGRESS_FAULT_ROUND_PREFIX, floor(horizon_T / period) + 2)     # prefix = 200
faults = |miners| * |PROGRESS_FAULT_OFFSETS| * rounds                        # offsets = 5
```

| scale | horizon_T | period | rounds | miners | offsets | **exact fault count per run** |
|---|---:|---:|---:|---:|---:|---:|
| Tier 1 (pilot) | 200.0 | 1.2987 | 156 | 2 | 5 | **1 560** |
| Confirmatory / Tier 2 | 10 000.0 | 1.02 | 200 | 15 | 5 | **15 000** |

Round indices run `1 .. rounds` contiguously. The count is a closed-form product of declared
constants; it is not a search result and no value in it was chosen by looking at an outcome.

## 6. Exact fault reason

Every emitted entry carries the single reason string

```
"MINER_FAILED"
```

There is exactly one distinct reason in the schedule at both scales. No other reason value is
emitted, and the reason does not vary by miner, by round, by phase, by tier or by seed.

## 7. Constants table (frozen)

| symbol | value |
|---|---|
| `PROGRESS_PAIR_BATCH_SIZE` | 25 |
| `PROGRESS_FAULT_OFFSETS` | `(0.01, 0.04, 0.07, 0.10, 0.13)` |
| `PROGRESS_FAULT_ROUND_PREFIX` | 200 |
| `ADVERSARIAL_FRACTION` | 0.10 |
| `wake_latency` (accepted default) | 1.0 s |
| `base_hash_rate` (accepted default) | 100.0 |
| fault reason | `"MINER_FAILED"` |

---

## 8. Proof 1 — D04C and D04 use byte-identical fault schedules

`_fault_schedule` is called from `build_config` with the arguments

```
(row["fault_schedule"], num_miners, reserve_fraction, horizon_T, tier["nominal_round_period"])
```

`D04C` and `D04` declare `fault_schedule = "FAULT_SET_PROGRESS"` in the same frozen matrix, and
they are executed at the same tier with the same `reserve_fraction`. Every argument is therefore
equal, and the function is a pure function of its arguments, so the returned tuples are equal.

This is verified executably rather than argued: `test_s6_31` asserts

```
build_config(D04C, seed, tier).injected_lease_faults
    == build_config(D04, seed, tier).injected_lease_faults
```

for **every one of the eight pilot seeds at both tiers** (16 comparisons), and additionally
asserts that the two configurations differ in **exactly one** `Stage2Config` field —
`adversarial`. Measured: all 16 comparisons byte-identical; sole differing field `adversarial`.

Schedule digests (SHA-256 over the materialised tuple), one per tier and constant across all
eight seeds:

| scale | digest |
|---|---|
| Tier 1 | `02777532d5d788765cd6d1f681f1b861ff989d49263e070e2d8776cdba07a7a0` |
| Confirmatory / Tier 2 | `fd55293c80924d1a13265052462386f7db07867d109930533f42c3dc25c25856` |

## 9. Proof 2 — the schedule does not depend on attack-effect magnitude or direction

`_fault_schedule` takes five arguments — a schedule name, a miner count, a reserve fraction, a
horizon and a period — and reads only module constants. It never receives, imports or reads:

* a simulation result, a `RunResult`, or any adapter output;
* an energy quantity, a reward quantity, a frontier value, or any counter;
* `adversarial_reevaluation_count`, `duplicate_work_reward_prevented_count`,
  `accepted_below_actual_count`, or any other measured field;
* any pilot artefact on disk.

Every quantity it uses is either a declared constant (§7), a scale parameter (§2, §4), or an
arithmetic consequence of the accepted engine's own rules (`hash_rate_for`, `wake_latency`,
batch completion). The chain of reasoning that produced it is a **reachability inequality** —
`nonce_domain_size / primary_count > batch_size`, i.e. a batch boundary must fall strictly
inside a primary's range — plus the measured call-site *state* (`committed == lease_start`,
`done = 0`), which is a statement that the event could not occur at all, not a statement about
how large or in which direction an effect was.

The correction therefore changed the schedule from one under which the modelled event was
**structurally impossible** to one under which it is **reachable**. No branch of the derivation
consults an effect size and none consults an effect sign. `test_s6_32` enforces this
statically by asserting that the source of `_fault_schedule` contains no reference to any
outcome-field name.

## 10. Proof 3 — the schedule is not generated separately for each master seed

`_fault_schedule` has no seed parameter. `build_config` passes it no seed, and the master seed
reaches the engine only through the two accepted fields `template_seed` and
`adversarial.deterministic_seed`, both of which are consumed after the schedule is built.

Consequently, for a fixed scenario and tier the materialised tuple is a constant across seeds.
This too is verified executably: the SHA-256 digests in §8 were computed for all eight pilot
seeds and collapse to **exactly one distinct value per tier** (measured: 1 distinct signature at
Tier 1, 1 at Tier 2). `test_s6_33` asserts that the digest set over all eight pilot seeds has
cardinality 1 for each tier and each arm.

The practical consequence is that the schedule cannot encode seed-specific knowledge: it is
written once, before execution, and every seed receives the same injected faults.

---

## 11. What was corrected, and when

**Corrected once, during the pilot, for structural event reachability only.** The original
parameterisation used the reference `batch_size = 50` and no fault schedule in Block D at all.
Under it the inequality `nonce_domain_size / primary_count > batch_size` read `35.4 > 50`, which
is false, so no intermediate committed frontier could exist when a lease was revoked and
`D04` was byte-identical to `D00` in every reported field. Three further corrections were made
inside the same reachability question and are recorded in decision-log D-11, D-12, D-12a, D-12b
and D-12c:

1. batch size 50 → 25 in **both** arms (reachability inequality);
2. injected miners: slow primaries → adversarial primaries (the adversarial set and the slow set
   overlapped in only one miner at Tier 1);
3. phases: one shared list → **per-miner** boundary phases (an earlier-landing injection consumed
   the revocation before the miner's own boundary);
4. period: median → mean (the median drifted the schedule ten whole rounds by round 150).

Each correction was derived from a structural argument and verified by the presence or absence of
a *reachable event*, never by the size or sign of a result. **The schedule is now frozen and will
not be tuned again**, including on the number of re-evaluated nonces.

## 12. Frozen-schedule verification across all eight pilot seeds

The pair was executed on **all eight** pilot seeds at Tier 1
(`run_pilot.py --d04-sweep`, results in
`experiments/thesis_revision_v45/stage_06/pilot/d04_all_seeds.json`). Every seed is retained,
including any that produces no withholding action; no seed is replaced and no seed is redrawn.

| arm | seed idx | accepted < actual | physical rewind | re-evaluated | duplicate prevented |
|---|---:|---:|---:|---:|---:|
| D04C | 0 | 0 | 0 | 0 | 0 |
| D04C | 1 | 0 | 0 | 0 | 0 |
| D04C | 2 | 0 | 0 | 0 | 0 |
| D04C | 3 | 0 | 0 | 0 | 0 |
| D04C | 4 | 0 | 0 | 0 | 0 |
| D04C | 5 | 0 | 0 | 0 | 0 |
| D04C | 6 | 0 | 0 | 0 | 0 |
| D04C | 7 | 0 | 0 | 0 | 0 |
| D04 | 0 | 1 | 0 | 12 | 12 |
| D04 | 1 | 2 | 0 | 24 | 24 |
| D04 | 2 | 1 | 0 | 12 | 12 |
| D04 | 3 | 2 | 0 | 24 | 24 |
| D04 | 4 | 2 | 0 | 24 | 24 |
| D04 | 5 | 1 | 0 | 12 | 12 |
| D04 | 6 | 2 | 0 | 24 | 24 |
| D04 | 7 | 2 | 0 | 24 | 24 |

All 16 runs completed. Zero-action seeds: **0 of 8** — but the retention rule stands regardless
and is not conditional on this outcome.

These are **feasibility measurements on pilot seeds disjoint from the confirmatory registry**.
They establish that the state IP-H10d is about is reachable and that the control arm does not
produce it. They are **not** a confirmatory result, **not** an effect estimate, and must not be
reported as evidence about withholding behaviour, incentive compatibility, or security.
