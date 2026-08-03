# Stage 5 — Requirement Traceability (S5-1 … S5-13 → code → tests)

Base: `4402bd084fc404cac1d8d85a44fb5d642544c448`. Schema `stage5.1`. 150 tests pass
(124 accepted retained + 26 new).

---

## S5-1 — Round-bound immutable behaviour profiles

| | |
|---|---|
| **Code** | `adversarial.py::MinerBehaviourProfile` (frozen); `adversarial_runtime.py::build_entities`, `materialise_behaviours`; `simulator.py::_handle_prepare_participants` |
| **Tests** | S5-02 (one profile per (round, miner); frozen; re-materialisation is a no-op), S5-04 (actor-class mapping) |

One immutable profile per participant per round, materialised once when the participant set is
prepared — before its wake is seated, so free-rider rate reduction and delayed-wake latency both
apply from the first batch. Re-materialising the same round returns the existing profiles.

## S5-2 — Validated, disabled-by-default configuration

| | |
|---|---|
| **Code** | `adversarial.py::AdversarialPolicy`, `IncentivePolicy` (both `__post_init__` validated); `config.py` (`field(default_factory=…)`); `adapter.py::_adversarial_from_blocksim`, `_incentive_from_blocksim` |
| **Tests** | S5-01 (every feature off, every rate zero, no Stage-5 effect), S5-03 (undeclared vocabulary and out-of-range parameters rejected), S5-26 (BlockSim mapping) |

## S5-3 — Actual / reported / accepted three-value separation

| | |
|---|---|
| **Code** | `MinerBehaviourProfile.actual_hash_rate` vs `reported_hash_rate`; `ProgressClaim.actual_frontier` / `reported_frontier` / `accepted_frontier`; `RunContext.adv_actual_frontier`; `adversarial_runtime.py::audit_claim` |
| **Tests** | S5-06 (reported diverges, physical does not), S5-07 (deterministic replay-idempotent audit), S5-09 (accepted ≠ actual recorded), S5-18 (accepted frontier lowered, actual preserved) |

The modeled audit is a deterministic SHA-256 draw over the seed and the immutable claim
identity. It is a **model parameter**, never a cryptographic verification claim.

## S5-4 — Free riding and hash-rate misreporting

| | |
|---|---|
| **Code** | `materialise_behaviours` (applies `work_fraction` to `st.hash_rate`; records the reported multiplier and `allocation_distortion_max_ratio`) |
| **Tests** | S5-05 (free rider really does less work; actual rate preserved on the profile), S5-06 (misreporting buys no real work) |
| **Measured** | scenario C: `free_rider_count = 20`, rounds 29 → 19. Scenario D: `allocation_distortion_max_ratio = 3.0`, evaluated nonces identical to honest. |

## S5-5 — Progress withholding and false exhaustion

| | |
|---|---|
| **Code** | `maybe_false_exhaustion`, `apply_progress_withholding`, `note_reassignment_reeval`, `round_has_coverage_gap`; `simulator.py::_handle_hash_work`, `_bind_reassigned_lease`, `_maybe_terminate_no_block` |
| **Tests** | S5-08 (detected ⇒ rejected, real state stands), S5-09 (undetected ⇒ recorded coverage gap), S5-10 (never labelled full-domain exhaustion), S5-18 (induced re-evaluation counted) |
| **Measured** | scenario E: 90 attempted, 90 detected, gap 0. Scenario F: 40 accepted, **3,000 nonces uncovered**, all rounds `ROUND_CLOSED_WITH_ADVERSARIAL_COVERAGE_GAP`. |

A round holding an accepted coverage gap did not search its domain, so it is never reported as a
full-domain exhaustion. Duplicate evaluation forced by an under-report is counted, not hidden.

## S5-6 — Solution withholding

| | |
|---|---|
| **Code** | `maybe_withhold_solution`; `events.py` `WithheldSolutionReleaseEvent` (microphase 25); `simulator.py::_handle_withheld_release`, `_HANDLERS` |
| **Tests** | S5-11 (nothing published, nothing accepted, solution valid against the fixed target), S5-12 (delayed release accepted through the normal path at `found_time + delay`), S5-13 (release into a closed round is a no-op; replay is a second no-op), S5-14 (never a full-domain exhaustion) |
| **Measured** | scenario G: 4 withheld, **0 blocks accepted** (control: 29). Scenario H: 40 withheld, 9 released and accepted, 18.0 s total hidden. |

A release is subject to the same identity checks as a prompt publication. Withholding never
changes the fixed target or difficulty, and the model does not claim it is detectable in a real
deployment.

## S5-7 — Delayed wake

| | |
|---|---|
| **Code** | `wake_extra_latency`, `complete_delayed_wake`; `simulator.py::_start_wake`, `_handle_wake_complete` |
| **Tests** | S5-15 (extended interval; both honest and adversarial wake times recorded), S5-16 (**wake energy strictly increases** — delaying a wake is a cost, never a saving) |
| **Measured** | scenario I: `delayed_wake_count = 9`, rounds 29 → 8. |

## S5-8 — Naive vs deduplicated reward accounting

| | |
|---|---|
| **Code** | `finalise_incentives` (computes both views); `IncentivePolicy.reward_deduplication_policy` |
| **Tests** | S5-23 (splitting/identity multiplication does not move the deduplicated total; the naive view exposes exactly what dedup removes) |
| **Measured** | scenario L (one entity, 4 identities): naive **47,900.0** vs deduplicated **11,975.0** — exactly **4.00×**. Scenario K (×4 split, 3 identities): **44,700.0** vs **11,975.0** — **3.73×**. Amplification is attributed only to the entity that declares it; an undeclared single-identity miner multiplies nothing. |

**This measures an accounting exposure. It is not a Sybil-resistance claim** and must never be
presented as one.

## S5-9 — Rejected invalid / out-of-range actions

| | |
|---|---|
| **Code** | `record_invalid_action`, `maybe_out_of_range_attempt`; `simulator.py::_handle_hash_work` (before any accounting) |
| **Tests** | S5-17 (no ledger record, no frontier advance, no reward; penalty eligible only) |
| **Measured** | scenario J: 30 attempts, 30 rejections, penalty total 150.0, attacker's evaluations strictly inside its own range. |

## S5-10 — Reward and penalty ledger

| | |
|---|---|
| **Code** | `_emit` (dedup-key idempotent), `finalise_incentives`, `snapshot_availability`, `availability_residency`, `incentive_reconciliation_residual` |
| **Tests** | S5-19 (work reward per unique accepted committed evaluation), S5-20 (replay-idempotent; residual 0.0), S5-21 (winner reward to the solver alone), S5-22 (penalties need a detected/rejected action; crash faults spared) |
| **Measured** | `incentive_reconciliation_residual = 0.0` in **all twelve** scenarios. |

Availability residency is time-aware (the still-open interval is added), and is a per-round
delta against a round-start snapshot — never the cumulative run total. Availability is a
residency quantity and is never evidence of actual work.

## S5-11 — `q_adv(t)` with an explicit NA rule

| | |
|---|---|
| **Code** | `observe_adversarial_share`, `q_adv_summary`; `RunContext.adversarial_share_hook` fired from `apply_miner_state_transition` |
| **Tests** | S5-24 (actual active rates; NA when `H_active = 0`; NA excluded from mean and above-threshold duration; never fabricated as 0.0) |
| **Measured** | every scenario carries a non-zero `q_adv_na_duration`; scenarios G/H/L reach `time_weighted_q_adv = 1.0`. |

`q_adv` is a composition measurement, not a security threshold.

## S5-12 — Round-terminal actions and replay idempotence

| | |
|---|---|
| **Code** | `close_adversarial_round` (cancels queued release events, terminalises withheld solutions / claims / wakes); `register_action` |
| **Tests** | S5-13 (release replay is a no-op), S5-25 (nothing survives closure; registry returns the same record and runs the factory once) |

## S5-13 — Matched adversarial pair harness

| | |
|---|---|
| **Code** | `adapter.py::run_matched_adversarial_pair`, `_MATCHED_PAIR_DELTA_KEYS` |
| **Tests** | S5-26 (rejects any profile changing difficulty / domain / seed; baseline 29 accepted vs attacked 0) |

Both arms share every non-adversarial parameter and the same fixed target. The harness raises
`ValueError` on any attack profile touching `difficulty`, `nonce_domain_size` or
`template_seed`, and re-verifies arm equality after mapping.

## S5-26 (constraint) — The fixed target is never changed

| | |
|---|---|
| **Code** | `search.py` **byte-identical** to the frozen baseline; `difficulty` absent from the Stage-5 config mapping |
| **Tests** | S5-26 (`target_for_difficulty` identical across honest and heavily-attacked configs) |

---

## Adapter schema `stage5.1`

All Stage-4C keys retained; ~45 Stage-5 keys added, all inert when disabled. Verified by S5-26
and by the three retained adapter tests. The results themselves carry an explicit
`stage5_claim_scope` string naming every property Stage 5 does **not** establish.

## Prohibited-claim audit

| Claim | Asserted anywhere? |
|---|---|
| incentive compatibility | **No** — explicitly disclaimed in code, results and every report |
| fairness | **No** |
| Sybil resistance | **No** — the S5-8 measurement is labelled an accounting exposure |
| selfish-mining resistance | **No** — withholding is measured succeeding |
| coalition resistance | **No** |
| common-prefix / chain-quality security | **No** |
| Bitcoin/PoW-equivalent security | **No** |
| nonce partitioning as energy saving | **No** — the mechanism is the idle policy only |
| dynamic difficulty | **Excluded** — target fixed, verified executably |
