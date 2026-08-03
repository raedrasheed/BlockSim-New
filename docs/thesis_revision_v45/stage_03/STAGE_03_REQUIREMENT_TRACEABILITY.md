# Stage 3 — Requirement Traceability

Maps every Stage-3 requirement (S3-1 … S3-10), test (S3-01 … S3-18) and acceptance gate to
the executable code and test that realises it. Algorithm: PoCol. Mechanism: the idle policy
within PoCol. No dynamic difficulty. The security floor is an operational capacity floor
only (no consensus-security-equivalence claim).

## Requirements → code

| Req | Code |
|---|---|
| S3-1 immutable floor policy + `H_effective` + breach | `security.SecurityFloorPolicy`, `security.compute_h_effective`, `simulator.EvaluateSecurityFloor` |
| S3-2 reserve slices distinct from reassignment | `security.partition_primary_and_reserve`, `RangeSlice`; `simulator._handle_prepare_participants` |
| S3-3 reserve record + immutable request identity | `security.ReserveMinerRecord`, `ReserveActivationRequest`; `simulator.SeatReserveActivation` |
| S3-4 authoritative observation + idempotence | `simulator.EvaluateSecurityFloor`, `security.SecurityFloorObservation` |
| S3-5 deterministic minimal-sufficient selection | `security.select_reserves_to_cover`; decision in `EvaluateSecurityFloor`; `ReserveActivationDecision` |
| S3-6 causal two-step activation + identity verify | `simulator._handle_reserve_activation_start/_complete`, `_verify_activation_identity`; `events` descriptors |
| S3-7 accepted search core for reserves + ledger tag | `_handle_reserve_activation_complete` (normal `MinerSearchState`); `EvaluationRecord.assignment_kind` |
| S3-8 energy accounting by residency | `config.per_miner_power` (RESERVE→`P_reserve`); `adapter._security_floor_results` |
| S3-9 floor-unattainable policy | `simulator._apply_floor_unattainable`, `EvaluateSecurityFloor` CONTINUE_DEGRADED / ABORT_ROUND |
| S3-10 round closure & cleanup | `simulator._close_security_state` (invoked by `_close_and_publish`) |

## Tests → requirement

| Test | Requirement |
|---|---|
| S3-01 floor satisfied, no activation | S3-4 |
| S3-02 breach after exhaust seats activation | S3-1, S3-4, S3-5 |
| S3-03 WAKING reserve not counted | S3-1, S3-3 |
| S3-04 completed reserve active, counts, hashes | S3-6, S3-7 |
| S3-05 minimal sufficient subset | S3-5 |
| S3-06 two runs select same reserves/slices | S3-5 (determinism) |
| S3-07 primary+reserve slices disjoint cover domain | S3-2 |
| S3-08 activated reserve searches only its slice | S3-2, S3-7 |
| S3-09 ledger zero duplicate (primary+reserve) | S3-2, S3-7 |
| S3-10 exact replay → no second activation | S3-3 |
| S3-11 stale cross-round activation → no effect | S3-6 |
| S3-12 pool insufficient → FLOOR_UNATTAINABLE + residual | S3-5, S3-9 |
| S3-13 CONTINUE_DEGRADED exact duration below floor | S3-9, S3-4 |
| S3-14 ABORT_ROUND via closure owner, no live activation | S3-9, S3-10 |
| S3-15 closure cancels pending/waking + terminal slices | S3-10 |
| S3-16 reserve energy == residency terms | S3-8 |
| S3-17 floor doesn't change target/difficulty | S3-1 (orthogonality) |
| S3-18 full-domain no-block includes reserve slices once | S3-2 |

Retained Stage-2B (all rerun, unchanged): TV325–TV338, E2E-1…E2E-5, SCI-1…SCI-10, target
tests. The adapter schema-version assertion is updated to `stage3.1` (a declared Stage-3
schema bump, not a regression).

## Acceptance gates → evidence

| Gate | Evidence |
|---|---|
| 1 `H_effective` counts only ACTIVE_HASHING | `compute_h_effective`; S3-03 |
| 2 WAKING/reserve-only never counted prematurely | `compute_h_effective`; S3-03 |
| 3 floor explicit & immutable per round | `SecurityFloorPolicy` (frozen); S3-17 |
| 4 primary+reserve slices disjoint & cover domain | S3-07 |
| 5 activation never reassigns another range | `partition_primary_and_reserve`; S3-08 |
| 6 selection deterministic & minimally sufficient | S3-05, S3-06 |
| 7 immutable request/decision/event identity | `SeatReserveActivation`, descriptors; S3-10 |
| 8 exact replay → no duplicate activation | S3-10 |
| 9 activated reserves use accepted Stage-2B core | S3-04, S3-08 |
| 10 ledger proves zero duplicate nonce evaluation | S3-09 (dup=0) |
| 11 no activation crosses a round boundary | S3-11 |
| 12 floor-unattainable behavior explicit | S3-12, S3-14 |
| 13 duration below floor measured correctly | S3-13 |
| 14 reserve energy fully accounted by residency | S3-16 (residual 0.0) |
| 15 target/difficulty unchanged | S3-17 |
| 16 full-domain exhaustion includes reserve slices | S3-18 |
| 17 S3-01…S3-18 pass | 18/18 |
| 18 every accepted Stage-2B test still passes | 37/37 |
| 19 GitHub Actions succeeds | `.github/workflows/stage3-pocol-tests.yml` |
| 20 Stage 1 untouched | no `docs/thesis_revision_v45/stage_01/` change |
| 21 Stage 2B evidence preserved | `docs/thesis_revision_v45/stage_02/` unchanged |
| 22 Stage 4 not begun | no leasing/reassignment/dynamic-difficulty code |
