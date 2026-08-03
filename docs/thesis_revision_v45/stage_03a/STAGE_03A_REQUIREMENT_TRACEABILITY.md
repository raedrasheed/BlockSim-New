# Stage 3A — Requirement Traceability

Maps every Stage-3A requirement (S3A-1 … S3A-8), mandatory test (S3A-01 … S3A-12) and
acceptance gate to the executable code and test that realises it.  Algorithm: PoCol.
Mechanism: the idle policy within PoCol.  Operational capacity floor only.

## Requirements → code

| Req | Code |
|---|---|
| S3A-1 `H_effective` requires a live assignment (no fallback) | `security.compute_h_effective`; `simulator._handle_prepare_participants` / `_handle_reserve_activation_complete` add `RoundID`/`TemplateID` to assignment records |
| S3A-2 observe every capacity change; idempotent key; real first breach | `simulator.EvaluateSecurityFloor`, `_observation_key`, `_pending_primary_capacity`; `context.RunContext.capacity_state_version` / `observation_by_key`; observation calls at prepare/wake/exhaust/activation-complete/complete-seat-failure/closure |
| S3A-3 true minimum-cardinality selection | `security.select_reserves_to_cover` (+ `_pref_key`); decision in `EvaluateSecurityFloor` |
| S3A-4 transactional seating + start/complete rollback | `simulator.SeatReserveActivationTransaction`; `_handle_reserve_activation_start` CompleteEvent-seat-failure rollback |
| S3A-5 complete activation-identity verification | `simulator._verify_activation_identity` |
| S3A-6 complete activation-request lifecycle | `security.ReserveActivationRequest` (status/refs/timestamps/DecisionID); `simulator._handle_reserve_activation_start/_complete`, `_close_security_state` |
| S3A-7 correct reserve-domain exhaustion semantics | `simulator._maybe_terminate_no_block`; `security.FULL_DOMAIN_EXHAUSTED_NO_BLOCK` / `ROUND_CLOSED_WITH_UNUSED_RESERVE_DOMAIN` |
| S3A-8 adapter configures + validates + executes Stage 3 | `adapter.stage2config_from_blocksim`, `_security_floor_from_blocksim`; `security.SecurityFloorPolicy.__post_init__` |

## Tests → requirement

| Test | Requirement |
|---|---|
| S3A-01 ACTIVE_HASHING + missing assignment excluded | S3A-1 |
| S3A-02 sequential wakes observe + initial below-floor interval | S3A-2 |
| S3A-03 observation-key replay idempotent | S3A-2 |
| S3A-04 rates [10,100] need 90 → single 100-rate | S3A-3 |
| S3A-05 StartEvent seat failure rolls back | S3A-4 |
| S3A-06 CompleteEvent seat failure — no stranded WAKING | S3A-4 |
| S3A-07 tampered request/obs/decision/version/EventRef → no effect | S3A-5 |
| S3A-08 completed request COMPLETED with both EventRefs | S3A-6 |
| S3A-09 closure terminalises all records + requests | S3A-6 |
| S3A-10 floor=0 + unused slices ≠ full-domain exhaustion | S3A-7 |
| S3A-11 true full-domain no-block covers every nonce once | S3A-7 |
| S3A-12 adapter enables floor + executes activation from a config dict | S3A-8 |

Retained (all rerun, unchanged behaviour): the 37 accepted Stage-2B tests (TV325–TV338,
E2E-1…E2E-5, SCI-1…SCI-10, target tests, adapter) and the 19 Stage-3 tests
(S3-01…S3-18 + adapter schema).  S3-03's manually-built assignment now carries
`RoundID`/`TemplateID` (matching the S3A-1 assignment invariant — a scaffolding fixup, not a
weakened assertion).  The adapter schema-version assertions move `stage3.1` → `stage3a.1`.

## Acceptance gates → evidence

| Gate | Evidence |
|---|---|
| 1 `H_effective` requires a real live assignment | `compute_h_effective`; S3A-01 |
| 2 every capacity-changing wake/exhaust/activation event observed | observation call sites; S3A-02; metrics `observation_count` |
| 3 observation replay is idempotent | `_observation_key` + `observation_by_key`; S3A-03; metrics `observation_replay_count` |
| 4 duration below floor begins at the real first breach | measure-only `participants_prepared` obs; S3A-02; metrics `early_wake_below_floor_duration` |
| 5 reserve selection is minimum-cardinality | `select_reserves_to_cover`; S3A-04 |
| 6 activation seating is all-or-none or fully compensated | `SeatReserveActivationTransaction`; S3A-05 |
| 7 CompleteEvent seating failure cannot strand WAKING | `_handle_reserve_activation_start` rollback; S3A-06; metrics `activation_complete_seat_failure_count` with 0 non-terminal |
| 8 all activation identity fields verified | `_verify_activation_identity`; S3A-07 |
| 9 activation requests have a complete terminal lifecycle | `ReserveActivationRequest`; S3A-08, S3A-09 |
| 10 closure leaves no ACTIVE/AVAILABLE closed-round record | `_close_security_state`; S3A-09; metrics `nonterminal_reserve_records_after_closure == 0` |
| 11 full-domain exhaustion never hides unsearched reserve slices | `_maybe_terminate_no_block`; S3A-10, S3A-11 |
| 12 the BlockSim adapter can configure and execute Stage 3 | `stage2config_from_blocksim`; S3A-12 |
| 13 all existing and new tests pass | 68/68 (37 Stage-2B + 19 Stage-3 + 12 Stage-3A) |
| 14 GitHub Actions succeeds | `.github/workflows/stage3a-pocol-tests.yml` |
| 15 Stage 1 and accepted Stage 2B remain untouched | no `stage_01/` change; `search.py`/`energy_experiment.py` byte-identical; `stage_02/` unchanged |
| 16 Stage 4 not begun | no leasing/reassignment/dynamic-difficulty/rewards/adversarial code |
