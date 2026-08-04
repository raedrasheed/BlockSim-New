# Stage 5B — Requirement Traceability

Every Stage-5B requirement maps to executable code and to at least one executing test.
Line references are to the state of this branch at the Stage-5B commit.

## Requirements

| Req | Requirement | Implementation | Tests |
|---|---|---|---|
| **S5B-1** | Preserve unique-work ownership: reward the FIRST physical evaluator of each `(RoundID, TemplateID, RangeSliceID, nonce)`; later re-evaluation earns nothing; unique suffix work belongs to the reassignee; predecessor work stays with the predecessor; both accounting views use the same ownership map; reconciliation table | `adversarial_runtime._interval_subtract`, `_ownership_by_lineage`, the WORK_REWARD block of `finalise_incentives`, `ownership_reconciliation`; adapter key `ownership_reconciliation` | S5B-01, S5B-01b, S5-19 (retained) |
| **S5B-2** | Fully replay-idempotent finalisation: a second `finalise_incentives` leaves both ledger and every derived metric byte-for-byte unchanged | `context.round_incentive_result`, `adversarial_runtime._COMPONENT_STAT`, `_ROUND_DERIVED_STATS`, `refresh_incentive_aggregates` (assigns, never accumulates) | S5B-02, metrics `replay_purity_S5B_2` |
| **S5B-3** | Frontier separation on BOTH reassignment paths; a genuine Path-B E2E scenario | `simulator._bind_reserve_reassignment_if_any` (calls `apply_progress_withholding`, starts at the accepted frontier, adjusts the search state, keeps `committed_frontier` monotonic) | S5B-03, metrics scenario C |
| **S5B-4** | Delayed wake in every real wake lifecycle; real request identity + wake generation in every action; `seated_at` fixes `another_reserve_activated`; realised-interval wake energy; replay returns the same action | `adversarial_runtime.WAKE_LIFECYCLES`, `wake_extra_latency` (declared-flag authority, replay map, lifecycle label), `finalise_delayed_wake_impact`; `security.ReserveActivationRequest.seated_at`; `simulator._start_wake`, `_handle_reserve_activation_start`, `_handle_range_reassignment_start`; `context.adv_wake_action_by_request` | S5B-04, S5B-04b, S5B-05, S5B-06, metrics scenarios D/E/F/G |
| **S5B-5** | One action-registration authority covering all six action types; replay costs nothing; rejected action has no effect; `maximum_actions_per_round = 0` blocks everything; profile materialisation is not an action | `adversarial_runtime.charge_action_budget` + the six charge sites (`ABANDONMENT`, `DELAYED_WAKE`, `SOLUTION_WITHHOLD`, `FALSE_EXHAUSTION`, `PROGRESS_WITHHOLD`, `INVALID_ACTION`); `context.adv_action_budget_charged` | S5B-07, metrics scenario H |
| **S5B-6** | Conserve effective physical capacity under splitting; virtual-subassignment accounting authority; accounting derived from records; capacity sum equals effective entity rate; combined-behaviour coverage | `adversarial_runtime.create_subassignments` (budget `st.hash_rate`), `note_physical_evaluation`, `subassignment_accounting`, `virtual_identity_accounting`; `adversarial.SubAssignmentRecord.evaluated_nonce_count`; `context.subassignments_by_parent` | S5B-08, S5B-09, metrics scenarios I/J/K |
| **S5B-7** | `actual_unsearched_suffix` on abandonment; security floor re-evaluated after abandonment; a gapped round never closes as ordinary/full-domain exhaustion; `claim_overstatement` separated from `actual_unsearched_suffix` | `adversarial.AbandonmentActionRecord.actual_unsearched_suffix`, `ProgressClaim.claim_overstatement` / `.actual_unsearched_suffix`; `adversarial_runtime.maybe_abandon`, `maybe_false_exhaustion`; `simulator._handle_hash_work` (floor re-evaluation), `_maybe_terminate_no_block` (gap checked first) | S5B-10, S5B-11, metrics scenarios L/M |
| **S5B-8** | Map/validate `false_exhaustion_claims_range_end`; offset identical through all three entry points; count `physical_evaluation_count` on every committed evaluation; reconcile with the ledger; floor + reported-rate allocation execute together | `adapter._adversarial_from_blocksim`, `adapter._evaluation_ledger_nonce_total`, `adversarial_runtime.maybe_false_exhaustion` (positive offset wins), `note_physical_evaluation`, `allocate_by_reported_rate(start=…)`, `simulator` floor branch | S5B-12, metrics scenarios N/O/P |

## Tests

| Test | Assertion summary |
|---|---|
| **S5B-01** | Predecessor [0,80) then successor [40,100): predecessor 80, successor 20, total 100, duplicate prevented 40; reconciliation names owner + prevented duplicates per interval |
| **S5B-01b** | Naive-identity and entity-deduplicated accounting use the same ownership map |
| **S5B-02** | Two (and three) `finalise_incentives` calls leave the complete ledger and every Stage-5 metric unchanged |
| **S5B-03** | A true Path-B reserve reassignment applies accepted-frontier separation — wake required, AVAILABLE reserve, `ReserveActivationRequest`, accepted < actual, no physical rewind, re-evaluation, duplicate prevented |
| **S5B-04** | Initial, reserve, Path-A and Path-B wakes all consult the delayed-wake policy, via actual queued events; every action carries a real request identity and generation; no unattributed or unspecified wake |
| **S5B-04b** | Exact wake replay returns the same action, no new generation, no second budget charge |
| **S5B-05** | A real delayed wake triggers another reserve activation and sets `another_reserve_activated = True`, backed by a real activation of a different miner inside the added interval |
| **S5B-06** | A wake cancelled before its configured delay ends charges only the realised delay; a completed wake realises its full delay |
| **S5B-07** | `maximum_actions_per_round = 0` blocks solution withholding, out-of-range actions and delayed wake with no protocol effect; replay consumes no budget; profile materialisation is free |
| **S5B-08** | FREE_RIDER 0.5 + split ×4 conserves effective capacity at 0.5 of the original (4 × 12.5 = 50); MISREPORTER ×5 + split ×4 keeps the actual 100 |
| **S5B-09** | Subassignment and virtual-identity accounting derived from explicit records; every evaluation maps to exactly one subassignment; no throughput increase vs the unsplit control; multiple controlled miners + identities conserve entity capacity |
| **S5B-10** | Abandoning 75 unsearched nonces records a 75-nonce gap; the round cannot close as ordinary or full-domain exhaustion; the floor is re-evaluated at the abandonment |
| **S5B-11** | A false claim from actual 25 to reported 35 records claim overstatement 10 and actual unsearched suffix 75; the gap uses 75 |
| **S5B-12** | The adapter exposes the range-end flag and offset correctly through all three entry points; `physical_evaluation_count` matches the ledger with leases enabled AND disabled; floor + reported-rate allocation execute together |

## Retained tests

All 162 tests accepted at Stage 5A pass unchanged in behaviour. Two mechanical edits were
required and neither weakens an assertion:

| File | Edit | Reason |
|---|---|---|
| `test_stage2_adapter.py`, `test_stage3_security_floor.py`, `test_stage4_range_leases.py`, `test_stage5_adversarial_incentive.py` | schema literal `stage5a.1` → `stage5b.1` | required by the S5B-8 schema bump; the assertion still pins the declared schema exactly |
| `test_stage5_adversarial_incentive.py` (S5-19) | `eligibility_reason` label `unique_physical_nonce_union` → `first_physical_evaluator_unique_nonce` | S5B-1 names the more precise rule; the union-semantics assertions in the same test are unchanged |

No test was deleted, renamed, skipped or relaxed. The corrected S5-18 and S5-19 assertions
introduced by Stage 5A are preserved exactly.
