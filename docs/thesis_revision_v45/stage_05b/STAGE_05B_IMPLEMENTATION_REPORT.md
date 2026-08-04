# Stage 5B — Reward-Ownership / Path-B / Wake / Coverage Lock

**Branch:** `thesis-v45-pocol-stage5b-reward-owner-pathb-wake-coverage-lock`
**Base:** `0594ffd62194d22fe0eae55a1fec366a2cff4b86` (Stage 5A)
**Adapter result schema:** `stage5b.1`
**Tests:** 176 passed (162 retained + 14 new S5B-01 … S5B-12)

Every accepted Stage-5A correction is preserved: the physical-frontier rewind is **not**
restored, exact-interval work rewards are **not** restored, the corrected S5-18 / S5-19 semantics
stand, and the Stage-5 model remains disabled by default.

---

## 1. What was actually wrong

The Stage-5A acceptance review identified eight executable defects. Every one was real and every
one was in code I wrote. This report states each plainly, with the measurement that proves it.

| # | Defect | Status before Stage 5B |
|---|---|---|
| S5B-1 | `miner_of_lineage.setdefault(lineage, rec.MinerID)` | The **whole** union of a lineage was paid to whichever miner opened it. A reassignee that physically evaluated a unique suffix earned nothing. |
| S5B-2 | `finalise_incentives` accumulated into run-level counters | A second call re-incremented `duplicate_work_reward_prevented_count` (40 → 80), `naive_identity_reward_total` (80 → 160) and blew `work_reward_union_residual` from 0.0 to 80.0 — the very metric that certifies correctness. |
| S5B-3 | `_bind_reserve_reassignment_if_any` started from `prog.committed_frontier` | Path A applied accepted-frontier separation; **Path B silently discarded it**. |
| S5B-4 | Delayed wake reached only `_start_wake`; `finalise_delayed_wake_impact` read a non-existent `seated_time`; energy used `P_wake × configured_delay` | Three of four wake lifecycles never consulted the policy, `another_reserve_activated` could never become true, and the charged energy was one the run never spent. |
| S5B-5 | Budget charged at four of six action sites; no replay identity | Replaying an action charged the budget again; a rejected action could still leave partial effects. |
| S5B-6 | `create_subassignments` used `prof.actual_hash_rate` as the budget | A FREE_RIDER at 0.5 that also split 4 ways budgeted 100 nonces/s across its shares instead of 50. The records were decorative — nothing derived from them. |
| S5B-7 | Abandonment recorded no coverage gap; false exhaustion conflated overstatement with the real hole | The Stage-5A evidence reported `abandoned_nonce_count = 3000` beside `coverage_gap_nonce_count = 0` and a `round_exhausted_no_block` closure. |
| S5B-8 | `false_exhaustion_claims_range_end` unmapped; `physical_evaluation_count` counted only inside `if cfg.range_lease.enabled`; floor + reported-rate allocation silently exclusive | A configured offset had no effect through BlockSim; a zero physical count sat beside a non-empty evaluation ledger; the allocation mode was dropped without a word. |

## 2. S5B-1 — reward follows the first physical evaluator

`_ownership_by_lineage` walks a round's `EvaluationRecord`s in **causal order**
(`completion_time`, then ledger sequence) and credits each record only with the positions no
earlier record already covered. Ownership is therefore per `(RoundID, TemplateID, RangeSliceID,
nonce)`, not per lineage.

| nonce interval | first evaluator | later evaluators | reward owner | rewarded | duplicate prevented |
|---|---|---|---|---:|---:|
| [0, 80) | M000 | — | **M000** | 80 | 0 |
| [40, 100) | — | M001 | — | 0 | 40 |
| [80, 100) | M001 | — | **M001** | 20 | 0 |

Predecessor 80, successor 20, total 100, 40 duplicate rewards prevented — the exact figures the
directive specifies, asserted in S5B-01. The full table is exposed as
`ownership_reconciliation` in the adapter result. Naive-identity and entity-deduplicated
accounting are computed from **the same ownership map**; they differ only in whether an entity's
identities and splits are collapsed.

`work_reward_union_residual` is 0.0 in every measured scenario.

## 3. S5B-2 — finalisation is state-pure

Per-round results now live in `run_ctx.round_incentive_result`; `refresh_incentive_aggregates`
**recomputes** every aggregate from the immutable incentive ledger plus that registry and
**assigns** rather than accumulates. Component totals come from the ledger, derived per-round
counters are summed across rounds, and the union residual is a maximum, not a sum.

Measured directly (`replay_purity_S5B_2` in the metrics):

| | first call | second call |
|---|---|---|
| work reward by miner | `{M000: 80.0, M001: 20.0}` | `{M000: 80.0, M001: 20.0}` |
| ledger entries | 3 | 3 |
| every metric unchanged | — | **true** |

A third call is equally inert (asserted in S5B-02): idempotence is not a one-shot property here.

## 4. S5B-3 — accepted-frontier separation on BOTH paths

`_bind_reserve_reassignment_if_any` now calls the same
`apply_progress_withholding` authority Path A uses, starts the reserve reassignee at the
**accepted** frontier, opens and consumes the re-evaluation window, keeps the physical
`committed_frontier` monotonic and leaves the original `RangeProgress` the single interval
authority.

Measured in scenario C, a **genuine** Path B — every one of these had to hold before the label
was used:

| assertion | measured |
|---|---|
| `needs_stage3_wake` | `True` |
| reassignee | an AVAILABLE reserve (`M003`) |
| carrier | `ReserveActivationRequest`, scope `REASSIGNMENT_WAKE_ONLY` |
| accepted vs actual | 13 < 25 |
| re-evaluation interval | [13, 25) |
| `physical_frontier_rewind_count` | 0 |
| `adversarial_reevaluation_count` | 12 |
| `duplicate_work_reward_prevented_count` | 12 |

The Stage-5A scenario M did **not** satisfy these (`wake_handles_created = 0`); it was Path A.
It is no longer labelled Path B anywhere.

## 5. S5B-4 — delayed wake in every real wake lifecycle

`wake_extra_latency` is consulted from all four:

| lifecycle | call site | request identity |
|---|---|---|
| `PRIMARY_WAKE` | `_start_wake` | `(PRIMARY_WAKE, MinerID, AssignmentID, version)` |
| `RESERVE_ACTIVATION_WAKE` | `_handle_reserve_activation_start` | `ReserveActivationRequestID` + activation generation |
| `PATH_A_REASSIGNMENT_WAKE` | `_handle_range_reassignment_start` | `RangeReassignmentRequestID` + lease generation |
| `PATH_B_REASSIGNMENT_RESERVE_WAKE` | the same activation start, scope `REASSIGNMENT_WAKE_ONLY` | activation + reassignment request ids + `WakeHandleID` |

Three further corrections:

* a **reserve** miner has no round-bound profile until it is activated, so the declared flags are
  the authority for whether a wake is delayed — consulting only `behaviour_profiles` made the
  reserve and Path-B lifecycles unreachable. Reading declared flags materialises nothing and is
  not an executed action, so it consumes no budget.
* `ReserveActivationRequest` gained an explicit **`seated_at`**. `finalise_delayed_wake_impact`
  read `seated_time`, which never existed on that record, so `another_reserve_activated` could
  never become true. Measured now: **20** actions across the scenarios, each backed by a real
  activation of a *different* miner seated inside the added interval.
* incremental wake energy is charged over the **realised** interval
  `[honest_expected_wake_time, min(actual_wake_time, round_terminal_time)]`. Measured in
  scenario G: configured extra latency 50.0 s, realised 19.0 s per action, energy
  `P_wake × 19.0`, not `P_wake × 50.0`.

Exact replay of a wake request returns the same action, does not increment the wake generation
and does not charge the budget again (`delayed_wake_replay_no_effect_count`). Every action
identity carries the real request identity and a wake generation;
`delayed_wake_unspecified_lifecycle_count` and `delayed_wake_unattributed_refused` stay 0 in
every executed scenario.

## 6. S5B-5 — one action-registration authority

`charge_action_budget` is the single authority and now covers **all six** action types:
solution withholding, out-of-range attempts, false exhaustion, progress withholding, delayed
wake and abandonment. Its declared rules:

* an exact replay of an already-charged action identity consumes no additional budget;
* a rejected-over-limit action is counted and creates **no** protocol effect — no withheld
  record, no invalid-action record, no wake delay, no rolled-forward wake generation;
* `maximum_actions_per_round = 0` prevents every action type;
* materialising a behaviour profile is **not** an executed action and is never charged.

Measured in scenario H: 58 refusals, zero abandonment actions, zero coverage gap.

## 7. S5B-6 — effective physical capacity is conserved

The subassignment budget is the **effective** rate in force after every physical effect
(`st.hash_rate`), never the pre-reduction nominal rate. Option (B) of the directive is
implemented: `note_physical_evaluation` is an explicit virtual-subassignment accounting
authority that maps every committed physical evaluation onto exactly one subassignment per nonce
position.

Measured:

| scenario | behaviours | budget | share sum | derived capacity | effective rate | residual |
|---|---|---:|---:|---:|---:|---:|
| I | FREE_RIDER 0.5 + split ×4 | 50.0 | 50.0 (4 × 12.5) | 50.0 | 50.0 | 0.0 |
| J | MISREPORTER ×5 + split ×4 | 100.0 | 100.0 | 100.0 | 100.0 | 0.0 |
| K | 2 controlled miners, split ×2, 4 identities | — | — | 300.0 | 300.0 | 0.0 |

The records are not decorative: `SubAssignmentRecord.evaluated_nonce_count` is what the
subassignment view is derived from, and the sum over a miner's subassignments equals that
miner's evaluation-ledger total (asserted in S5B-09).
`subassignment_unmapped_evaluation_count` is 0 everywhere. Virtual-identity accounting is
derived from `VirtualIdentityRecord`s; `virtual_identity_physical_capacity_granted` stays 0.0.
Throughput is identical to the unsplit control.

**This remains an accounting / sensitivity model. It is not a Sybil defence.**

## 8. S5B-7 — abandonment and false exhaustion report the real hole

* `AbandonmentActionRecord.actual_unsearched_suffix() = range_end - actual_frontier` is recorded
  and added to both `coverage_gap_nonce_count` and the per-round gap. Abandoning 75 unsearched
  nonces records a 75-nonce gap (S5B-10).
* the operational security floor is **re-evaluated** at the abandonment capacity-change point
  (`observation_reason = "adversarial_abandonment"`), exactly as at any other capacity change.
* a round holding an adversarial coverage gap now closes with the explicit
  `ROUND_CLOSED_WITH_ADVERSARIAL_COVERAGE_GAP` disposition — checked **before** the generic
  unassigned-range and unused-reserve labels — so it can never be `round_exhausted_no_block` or
  `FULL_DOMAIN_EXHAUSTED_NO_BLOCK`.
* false exhaustion separates `claim_overstatement = reported - actual` from
  `actual_unsearched_suffix = range_end - actual`. A claim from an actual frontier of 25 to a
  reported 35 records overstatement 10 and suffix 75; the gap and the round closure use **75**
  (S5B-11).

The Stage-5A evidence combination — 3,000 abandoned nonces, a zero coverage gap and an ordinary
exhaustion closure — is now impossible. Measured in scenario L: 14,325 abandoned nonces,
14,325 coverage-gap nonces, 48 abandonment-gap rounds, sole disposition
`ROUND_CLOSED_WITH_ADVERSARIAL_COVERAGE_GAP`.

## 9. S5B-8 — complete adapter and metric semantics

* `false_exhaustion_claims_range_end` is mapped and validated in the BlockSim adapter, and an
  explicitly configured **positive offset takes precedence** over range-end claiming. A
  configured `false_exhaustion_claim_offset = 10` therefore produces the same reported claim
  (cursor 25 → 35) through direct `Stage2Config` construction, `stage2config_from_blocksim` and
  `run_pocol_stage2` (S5B-12).
* `physical_evaluation_count` is counted by one authority on **every** committed physical
  evaluation, with range leases enabled or disabled, and is reconciled against
  `evaluation_ledger_nonce_total`. `physical_evaluation_ledger_residual` is 0 in every scenario.
  **Documented distinction:** when the Stage-5 model is *disabled* the counter stays 0 by design
  while the Stage-2B evaluation ledger is still populated; the residual is reported as 0 for
  disabled runs and the invariant admits that case explicitly via `behaviour_profile_count == 0`.
  With the model enabled, a zero physical count beside a non-empty ledger is impossible.
* the security floor and `coordinator_uses_reported_hash_rate` now **execute together**: the
  floor carves the primary span and the reserve-domain slices, then only the primary span is
  re-sized from reported rates. Measured in scenario P: 8 reported-rate rounds, distortion ratio
  1.5, primaries `[0,150) [150,210) [210,300)` and the reserve slice `[300,400)` — disjoint,
  contiguous and covering the whole domain. Physical hash rates remain the actual rates.

## 10. Preservation

`Models/PoCol/stage2/search.py` remains **byte-identical** to the frozen Stage-4C baseline
(`17367b4c15eaabd664a496412bc3d1685bfcd9cf8749f71aea01aef70b094140`). No Stage-1 document,
protected DOCX/PDF or prior-stage evidence file was touched. Stage 6, preregistration, the
confirmatory matrix, statistical analysis and thesis integration are not begun. The frozen
Stage-2B search core is unmodified.

All 162 previously passing tests are retained. Four accepted tests had the declared schema
literal advanced from `stage5a.1` to `stage5b.1` (a required consequence of the schema bump) and
one assertion in S5-19 names the more precise `first_physical_evaluator_unique_nonce` eligibility
reason; the union semantics it asserts are unchanged. No test was deleted, renamed, skipped or
weakened, and the corrected S5-18 / S5-19 assertions stand exactly as Stage 5A left them.

## 11. Claim scope — unchanged

Stage 5B adds **no** security, fairness, incentive-compatibility, Sybil-resistance,
selfish-mining-resistance, coalition-resistance, common-prefix, chain-quality or
Bitcoin/PoW-equivalent security claim. The algorithm remains PoCol; the energy-saving mechanism
remains the idle policy within PoCol; nonce-domain partitioning alone is never described as an
energy-saving mechanism; the security floor remains an operational active-capacity floor only;
dynamic difficulty remains excluded and no Stage-5 parameter changes the fixed SHA-256 target.
