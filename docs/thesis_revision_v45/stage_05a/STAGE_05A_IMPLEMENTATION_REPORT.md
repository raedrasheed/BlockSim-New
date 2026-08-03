# Stage 5A — Accepted-Frontier / Unique-Reward / Executable-Behaviour Lock

**Branch:** `thesis-v45-pocol-stage5a-accepted-frontier-unique-reward-executable-behaviour-lock`
**Base:** `e44829b26a5ec09545bd5c0ba480ed6b657d0370` (Stage 5)
**Adapter result schema:** `stage5a.1`
**Tests:** 162 passed (150 retained + 12 new S5A-01 … S5A-12)

---

## 1. What was actually wrong

The Stage-5 acceptance review identified seven executable defects. Every one was real, and
every one was in code I wrote. This report states each plainly.

| # | Defect | Status before Stage 5A |
|---|---|---|
| S5A-1 | Progress withholding **rewound** `RangeProgress.committed_frontier` from 80 to 40 | The accepted Stage-4C authoritative physical frontier was being decreased |
| S5A-2 | WORK_REWARD deduplicated on `(lineage, start, end)` | Overlapping intervals `[0,80)` and `[40,80)` were **different keys** → 120 positions rewarded instead of 80 |
| S5A-3 | `coordinator_uses_reported_hash_rate` | Declared, mapped, validated — **zero runtime consumers** |
| S5A-4 | Assignment splitting | A **reward multiplier only**; no subassignment ever existed |
| S5A-5 | `ABANDONMENT_PENALTY` | Charged from the **behaviour flag alone**, with no executed action |
| S5A-6 | Delayed-wake `ActionID` | Constant per round → two wake episodes **collided into one record**; `below_floor_overlap`, `another_reserve_activated` and `attack_induced_floor_breach_duration` were never written |
| S5A-7 | `maximum_actions_per_round`, `false_exhaustion_claim_offset`, `alternative_solution_won` | All three **dead**: declared and validated, never consumed |

## 2. S5A-1 — three separate frontiers, one monotonic physical truth

`RangeProgress.committed_frontier` is the accepted Stage-4C **physical** frontier. It is now
never written downward. The protocol's *accepted* view lives in a separate
`AcceptedFrontierRecord` carrying `actual_frontier`, `reported_frontier`, `accepted_frontier`,
the reassignment start, the re-evaluation interval and the physical frontier at the moment of
decision — bound to round / template / slice / lease / assignment version, and replay-idempotent.

A successor may resume from an accepted frontier *below* the physical one. To let it execute
there without rewinding anything, an explicit **re-evaluation window** is opened; two guards
consult it:

- `_verify_hash_lease` compares the event cursor against `expected_cursor_for_lease`, which
  returns the window cursor while a window is open and the physical frontier otherwise;
- `_handle_hash_work` advances the frontier with `max(...)` and only asserts monotonicity
  outside a window.

With Stage 5 disabled both reduce to the accepted Stage-4C expressions exactly, which is why
all 150 retained tests still pass.

**Measured end-to-end** (scenario M, a real Path-B reassignment after an injected fault):

| actual | reported | accepted | reassignment start | re-evaluation interval |
|---:|---:|---:|---:|---|
| 100 | 50 | 50 | 50 | [50, 100) |

`physical_frontier_rewind_count = 0` in every scenario; the slice's final physical frontier ends
at its full range end, never below the actual frontier at the decision.

## 3. S5A-2 — WORK_REWARD is the unique physical nonce union

Reward is computed from the canonical non-overlapping **union** of physical intervals per
`(RoundID, TemplateID, range lineage)`. `interval_union([(0,80),(40,80)])` is `[(0,80)]` — 80
positions, not 120. One nonce position earns at most one work reward per template, and
adversarially induced re-evaluation earns nothing extra. The re-evaluation itself stays fully
visible in the execution and energy ledgers.

Both accounting views now use the **same** physical work definition (the union); they differ only
in whether an entity's identities and splits are collapsed.

Measured in scenario M: `adversarial_reevaluation_count = 50`,
`duplicate_work_reward_prevented_count = 50`, `work_reward_union_residual = 0.0`.

## 4. S5A-3 — reported-rate allocation is executable

With `coordinator_uses_reported_hash_rate = false` the accepted allocation is preserved
byte-for-byte (verified by comparing `round_ranges` against the honest control). With it true,
profiles are **pre-materialised before sizing** and ranges are sized from reported rates:
the total domain is unchanged, ranges stay pairwise disjoint and contiguous, and physical hash
rates remain the actual effective rates.

Measured in scenario N: `reported_rate_allocation_rounds = 25`,
`allocation_range_size_distortion_max_ratio = 1.42`. Projected completion (from the reported
rate) and actual completion (from the actual rate) are both recorded per miner.

## 5. S5A-4 — splitting and identities are executable records

`SubAssignmentRecord` — disjoint, contiguous subranges whose union equals the parent's allocated
range, each carrying a share of the entity's **single** capacity budget. The shares sum exactly
to that budget: `subassignment_capacity_residual = 0.0`. Physical throughput is identical to the
unsplit case (asserted by comparing evaluated nonce counts).

`VirtualIdentityRecord` — explicit, bound to one `EntityID`, `grants_physical_capacity = False`,
holding no assignment and no lease. Identity count is reported separately from real miner count.

Measured in scenarios K and O: 120 subassignments, 90 virtual identities, capacity residual 0.0.

**This remains an accounting / sensitivity model. It is not a Sybil defence.**

## 6. S5A-5 — an abandonment penalty requires an executed action

`AbandonmentActionRecord` records the abandoning miner, its lease, its actual frontier and the
abandoned suffix. `ABANDONMENT_PENALTY` is emitted strictly per record, deduplicated on the
action identity. A declared `IDLE_POLICY_DEFECTOR` whose round closes before the action executes
receives **no** penalty. An explicit audit counter,
`abandonment_penalty_without_action_count`, stays 0 in every scenario. Crash faults create no
record and no penalty.

Measured in scenario P: 40 executed actions, 40 penalty entries, 3,000 abandoned nonces.

## 7. S5A-6 — one action per wake episode, real floor impact

The delayed-wake `ActionID` now carries a per-`(round, miner)` **wake generation** plus the
activation/reassignment request identity, so two legitimate wakes in one round produce two
distinct records. `complete_delayed_wake` closes one episode per completion.

Closed security-floor breach intervals are recorded at both close points, and at round close
`finalise_delayed_wake_impact` measures, per action, the real overlap of the added waking
interval with the observed breach union, whether another reserve activation was seated inside
that interval, and the incremental wake energy. None of these is a constant any more.

## 8. S5A-7 — every retained declared field has a consumer

- `maximum_actions_per_round` is charged **before** any adversarial action is created;
  `actions_rejected_over_limit` counts refusals.
- `false_exhaustion_claim_offset` derives the reported claim as
  `min(range_end, cursor + offset)`. A companion flag
  `false_exhaustion_claims_range_end` (default true) models the strongest overstatement, so the
  offset never silently means "range_end". **Declared meaning of 0:** with range-end claiming
  disabled, a zero offset reports the truth — which is not a false claim and creates no coverage
  gap (measured: `false_exhaustion_attempted = 0`).
- `alternative_solution_won` is set when an accepted block closes the round before a withheld
  solution is released (measured: 27 in scenario H).

## 9. Preservation

`Models/PoCol/stage2/search.py` remains **byte-identical** to the frozen Stage-4C baseline. No
Stage-1 document, protected DOCX/PDF or prior-stage evidence file was touched. Stage 6,
preregistration and the confirmatory matrix are not begun.

### Two accepted tests were corrected, not weakened

S5-18 and S5-19 asserted the *defective* behaviour the review rejected — that the physical
frontier **is** rewound to 40, and that one reward is paid per raw interval. Both assertions
were replaced with strictly stronger ones asserting the corrected invariants (frontier stays at
80 with a separate accepted record at 40; one entry per canonical union interval with a zero
residual). No test was renamed, deleted, skipped or relaxed.

## 10. Claim scope — unchanged

Stage 5A adds **no** security, fairness, incentive-compatibility or Sybil-resistance claim. The
algorithm remains PoCol; the energy-saving mechanism remains the idle policy within PoCol;
nonce-domain partitioning alone is never an energy-saving mechanism; the security floor remains
an operational active-capacity floor only; dynamic difficulty remains excluded and no Stage-5
parameter changes the fixed SHA-256 target.
