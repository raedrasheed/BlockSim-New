# Stage 5A — Requirement Traceability (S5A-1 … S5A-7 → code → tests)

Base `e44829b`. Schema `stage5a.1`. 162 tests pass (150 retained + 12 new).

---

## S5A-1 — Separate actual / reported / accepted frontiers

| | |
|---|---|
| **Code** | `adversarial.py::AcceptedFrontierRecord`; `adversarial_runtime.py::apply_progress_withholding`, `expected_cursor_for_lease`, `note_physical_commit`, `frontier_reconciliation`; `simulator.py::_verify_hash_lease`, `_handle_hash_work`, `_bind_reassigned_lease` |
| **Tests** | S5A-01 (physical frontier monotonic, unit + END-TO-END through a real Path-B reassignment; replay-idempotent), S5A-02 (three values independently queryable; round/template/lease/version bound; detected claim keeps accepted == actual) |
| **Measured** | scenario M: actual 100 / reported 50 / accepted 50, reassignment start 50, re-evaluation [50,100); `physical_frontier_rewind_count = 0` in every scenario |

`RangeProgress.committed_frontier` is never written downward — it advances with `max(...)`.
The accepted view is a separate record; the re-evaluation window lets a successor execute below
the physical frontier without rewinding it. With Stage 5 disabled both guards reduce to the
accepted Stage-4C expressions exactly.

## S5A-2 — Work reward deduplicated by unique physical nonce

| | |
|---|---|
| **Code** | `adversarial_runtime.py::interval_union`, `finalise_incentives` (union per RoundID/TemplateID/lineage) |
| **Tests** | S5A-03 ([0,80) + [40,80) rewards exactly 80 positions, never 120; canonicalisation of overlap, order and adjacency), S5A-04 (residual 0.0; exactly 40 duplicates prevented; the 120 physical positions stay visible in the execution ledger) |
| **Measured** | scenario M: `adversarial_reevaluation_count = 50`, `duplicate_work_reward_prevented_count = 50`, `work_reward_union_residual = 0.0` |

Naive and deduplicated accounting now use the SAME physical work definition (the union).

## S5A-3 — Executable reported-rate allocation

| | |
|---|---|
| **Code** | `adversarial_runtime.py::reported_rate_allocation_enabled`, `prematerialise_behaviours`, `ensure_profile`, `allocate_by_reported_rate`, `record_allocation_projection`; `simulator.py::_handle_prepare_participants` |
| **Tests** | S5A-05 (a 5x misreporter receives a different deterministic range; total domain unchanged; ranges contiguous and pairwise disjoint; physical rate == actual rate; projected vs actual completion recorded; flag OFF reproduces the accepted allocation exactly) |
| **Measured** | scenario N: 25 allocation rounds, range-size distortion ratio 1.42 |

## S5A-4 — Executable assignment splitting and identities

| | |
|---|---|
| **Code** | `adversarial.py::SubAssignmentRecord`, `VirtualIdentityRecord`; `adversarial_runtime.py::create_subassignments`, `create_virtual_identities`, `entity_physical_capacity` |
| **Tests** | S5A-06 (real subassignments; shares sum to ONE entity budget; residual 0.0), S5A-07 (subranges disjoint and contiguous, union == parent range, throughput unchanged), S5A-08 (virtual identities explicit, bound to one EntityID, grant no capacity, add no assignment) |
| **Measured** | scenarios K/O: 120 subassignments, 90 virtual identities, `subassignment_capacity_residual = 0.0` |

**Accounting / sensitivity model only — not a Sybil defence.**

## S5A-5 — Executed abandonment action required

| | |
|---|---|
| **Code** | `adversarial.py::AbandonmentActionRecord`; `adversarial_runtime.py::maybe_abandon`, penalty block in `finalise_incentives`; `simulator.py::_handle_hash_work` |
| **Tests** | S5A-09 (round closes first ⇒ no action, no penalty, flag still declared), S5A-10 (one executed action ⇒ exactly one penalty keyed on the action identity; replay adds none; a crash fault creates neither) |
| **Measured** | scenario P: 40 actions, 40 penalties, 3,000 abandoned nonces, `abandonment_penalty_without_action_count = 0` |

## S5A-6 — Delayed-wake identity and real impact

| | |
|---|---|
| **Code** | `wake_extra_latency` (per-(round,miner) wake generation + request identity), `complete_delayed_wake`, `record_floor_breach_interval`, `finalise_delayed_wake_impact`, `interval_union_float`; `simulator.py` both floor-breach close points |
| **Tests** | S5A-11 (two wake episodes ⇒ two distinct actions with independent measured overlap; impact finalisation idempotent; incremental wake energy from P_wake) |

`below_floor_overlap`, `another_reserve_activated` and `attack_induced_floor_breach_duration`
are computed from observed breach intervals, not constants.

## S5A-7 — Declared parameters enforced

| | |
|---|---|
| **Code** | `charge_action_budget` (called before every adversarial action); `maybe_false_exhaustion` (offset-derived claim + `false_exhaustion_claims_range_end`); `close_adversarial_round` (`alternative_solution_won`) |
| **Tests** | S5A-12 (limit rejects actions; offset caps the reported claim; zero offset with range-end claiming off reports the truth and attempts nothing; alternative-solution-won set on a lost race and clear when nobody publishes) |
| **Measured** | scenario H: `withheld_alternative_solution_won_count = 27` |

---

## Retained-configuration audit — every field has an executable consumer

| Field | Consumer |
|---|---|
| `coordinator_uses_reported_hash_rate` | `allocate_by_reported_rate` (S5A-3) |
| `maximum_actions_per_round` | `charge_action_budget` (S5A-7) |
| `false_exhaustion_claim_offset` | `maybe_false_exhaustion` (S5A-7) |
| `false_exhaustion_claims_range_end` | `maybe_false_exhaustion` (S5A-7) |
| `assignment_split_count` | `create_subassignments` (S5A-4) |
| `sybil_identity_count` | `create_virtual_identities` (S5A-4) |
| `alternative_solution_won` | `close_adversarial_round` (S5A-7) |
| `below_floor_overlap` / `another_reserve_activated` | `finalise_delayed_wake_impact` (S5A-6) |
| `attack_induced_floor_breach_duration` | `finalise_delayed_wake_impact` (S5A-6) |

## Prohibited-claim audit — unchanged from Stage 5

Incentive compatibility, fairness, Sybil resistance, selfish-mining resistance, coalition
resistance, common-prefix security, chain-quality security and PoW-equivalent security are all
still **not** claimed. The algorithm remains PoCol, the energy-saving mechanism remains the idle
policy within PoCol, nonce partitioning alone is never an energy-saving mechanism, the security
floor stays an operational active-capacity floor, and dynamic difficulty stays excluded.
