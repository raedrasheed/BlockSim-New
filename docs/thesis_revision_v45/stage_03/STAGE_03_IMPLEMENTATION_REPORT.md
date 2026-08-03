# Stage 3 — Security-Floor & Reserve-Activation Implementation Report

Focused executable Stage-3 implementation on top of the accepted, frozen Stage-2B
scientific-core baseline. It adds an explicit **operational active-capacity floor** and a
**reserve-activation policy** inside PoCol, without modifying the accepted Stage-2B search
core.

- **Branch:** `thesis-v45-pocol-stage3-security-floor-reserve-activation`
- **Parent commit (branch base):** `1e495bda74144d86c08aa0549bd3d633033600c4` (accepted Stage-2B)
- **Frozen Stage-1 baseline:** `8c9902e57c0d6557329bc742e39a50ed31b86170` (untouched)
- **New module:** `Models/PoCol/stage2/security.py`
- **Tests:** `tests/thesis_revision_v45/stage2/` — **55 passing** (18 Stage-3 S3-01…S3-18 +
  all 37 retained Stage-2B: TV325–TV338, E2E-1…E2E-5, SCI-1…SCI-10, target, adapter).

Algorithm: **PoCol**. Energy-saving mechanism: **the idle policy within PoCol**. Nonce
partitioning is never described as an energy-saving mechanism. **No dynamic difficulty.**

The security floor is **disabled by default** (`SecurityFloorPolicy.enabled = False`), so
every accepted Stage-2B behaviour and test is byte-for-byte unchanged; Stage-3 behaviour
is opt-in per run.

> **Scope / non-claim.** The floor is an OPERATIONAL capacity floor only. It does not prove
> chain quality, common prefix, Bitcoin/PoW security equivalence, or resistance to any
> adversarial fraction. Reserve activation is a security-capacity policy that may INCREASE
> energy; it never saves energy.

## S3-1 Security-floor policy (`security.SecurityFloorPolicy`)

Immutable config: `enabled`, `minimum_active_hash_rate`, `minimum_active_miner_count|None`,
`activation_trigger_mode`, `reserve_selection_policy`, `maximum_activations_per_round`,
`activation_wake_latency`, `floor_tolerance`. The effective active hash rate
`H_effective(t)` (`security.compute_h_effective`) sums `hash_rate` over miners that are
simultaneously ACTIVE_HASHING with a live current-round/template/version assignment whose
range is not exhausted — WAKING / reserve-only miners contribute nothing. Breach:
`H_effective + floor_tolerance < minimum_active_hash_rate` (and, if configured, the
miner-count condition, reported separately).

## S3-2 Reserve slices distinct from range reassignment

`security.partition_primary_and_reserve` splits the finite domain into PRIMARY ranges plus
UNCLAIMED reserve-domain slices (immutable `RangeSliceID`), pairwise disjoint, union
exactly `[0, D)`. Activation may claim only an UNCLAIMED slice, at most once; no reserve
searches a primary's range; no duplicate nonce results (proved by the ledger). Full-domain
exhaustion requires every primary range exhausted AND every reserve slice
activated+exhausted or terminal — unsearched reserve slices are reported
(`UNUSED_AT_ROUND_CLOSE`), never hidden.

## S3-3 Reserve record & identity (`security.ReserveMinerRecord`)

Per-round reserve records with statuses AVAILABLE / ACTIVATION_PENDING / WAKING / ACTIVE /
EXHAUSTED / CANCELLED / UNUSED_AT_ROUND_CLOSE (never counted in `H_effective` while
AVAILABLE / ACTIVATION_PENDING / WAKING). Each activation carries the immutable
`ReserveActivationRequestID = (RoundID, TemplateID, breach ObservationID, MinerID,
ReserveSliceID, activation_generation)`; exact replay returns the existing request/event
with no second activation or slice claim.

## S3-4 Security-floor observation (`simulator.EvaluateSecurityFloor`)

The ONE authoritative observation procedure, invoked after every capacity-changing point
(all-primary-active, range exhaustion, reserve-activation completion; a solution closes the
round). Records a `SecurityFloorObservation` (effective rate, counts, deficits, breached,
decision id), tracks the duration below the floor, and is idempotent for a satisfied floor
(no recursive duplicate observation/decision).

## S3-5 Deterministic minimal-sufficient selection

On breach, `select_reserves_to_cover` picks the minimum reserve subset (ordered
`(activation_priority, MinerID)`) whose hash rates restore the floor beyond in-flight
activations. `ReserveActivationDecision.policy_result` ∈ {NO_ACTIVATION_REQUIRED,
ACTIVATION_SEATED, PARTIAL_RESTORATION, FLOOR_UNATTAINABLE, ROUND_ALREADY_TERMINAL,
NO_ELIGIBLE_RESERVE, ACTIVATION_LIMIT_REACHED}.

## S3-6 Causal two-step activation

`ReserveActivationStartEvent` → (WAKING) → `ReserveActivationCompleteEvent`
(`= start + activation_wake_latency`) → (ACTIVE_HASHING). Each payload carries the full
identity (request/observation/decision id, round, template, miner, slice, generation,
expected reserve status, expected round state version), verified before mutation; a
stale / duplicated / cancelled / cross-round activation performs no domain effect.

## S3-7 Integration with the accepted search core

An activated reserve receives a NORMAL `MinerSearchState` over its exact reserve slice and
uses the accepted Stage-2B rules (immutable template, target-coupled SHA-256 success,
causal planned batch completion, complete hash-event identity, search-generation replay
guard, evaluation ledger, zero duplicate nonce evaluation, no work after round end). The
ledger tags each interval `PRIMARY_ASSIGNMENT` or `ACTIVATED_RESERVE_ASSIGNMENT`. There is
no second search implementation.

## S3-8 Energy accounting

Reserve miners are charged by actual residency: AVAILABLE/RESERVE → `P_reserve`, WAKING →
`P_wake`, ACTIVE_HASHING → `P_hash`, post-range → `P_listen`. Per activated reserve,
`E_i = P_reserve·t_reserve + P_wake·t_wake + P_active·t_active + P_idle·t_idle` holds
exactly (measured max residual `0.0 J`). The adapter reports reserve standby / wake / active
energy separately and never claims reserve activation saves energy.

## S3-9 Floor-unattainable policy

Configurable `CONTINUE_DEGRADED` (default — record residual, keep the round executable,
accumulate `duration_below_floor`) or `ABORT_ROUND` (route through the one round-closure
owner, cancel pending activations, terminalise reserve requests/slices, publish the
declared abort reason `security_floor_unattainable`). No policy alters the fixed
target/difficulty.

## S3-10 Round closure & cleanup

At any closure the one closure owner cancels every QUEUED reserve-activation event (they
carry `RoundID_at_seat`), terminalises ACTIVATION_PENDING/WAKING reserves (CANCELLED),
marks unclaimed slices UNUSED_AT_ROUND_CLOSE, snapshots the floor metrics (closing the open
breach interval), and leaves no live reserve request/event. Each new round mints fresh
round-bound reserve records and slice identities.

## Verification snapshot (`evidence/stage3_metrics.json`)

Canonical floor scenario (4 miners, 2 reserve, D=400, min=250, zero-solution target):
49 rounds, 342 observations, 98 activations seated == 98 completed, **0** nonce duplicates,
**0** post-round evaluations, max searched-count/time residual **2.8e-12**, max reserve
energy-identity residual **0.0 J**, residency reconciles. ABORT_ROUND scenario: 99
`security_floor_unattainable` aborts. CONTINUE_DEGRADED: exact duration below floor tracked.

## Scope discipline

No range leasing / reassignment of abandoned primary ranges, no dynamic difficulty, no
reward/Sybil/selfish-mining/security-proof/adversarial-matrix/thesis-integration work
(later stages). No Stage-1 document modified; Stage-2B evidence preserved.
