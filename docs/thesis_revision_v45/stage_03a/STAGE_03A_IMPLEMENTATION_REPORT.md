# Stage 3A — Implementation Report

Focused executable correction of the Stage-3 security-floor / reserve-activation
implementation, addressing the eight defects (S3A-1 … S3A-8) found in independent final
acceptance review.  Branch `thesis-v45-pocol-stage3a-security-floor-observation-activation-transaction-exhaustion-lock`,
created from exactly `675995d5b1ff3845638e2402a26ab32dc7cf80fe` (the rejected Stage-3 head).

Algorithm: **PoCol**.  Mechanism: **the idle policy within PoCol**.  The security floor is
an **operational capacity floor only** — it makes no consensus-security-equivalence claim.
Reserve activation may **increase** energy; it never saves it.  No dynamic difficulty, no
range leasing/reassignment, no rewards/Sybil/selfish-mining/adversarial matrices (Stage 4+).

The accepted Stage-2B scientific search core (`search.py`, `energy_experiment.py`) is
**byte-identical** to the baseline; Stage 1 is **untouched**; Stage-2 evidence is preserved.
The floor stays **disabled by default**, so all 37 accepted Stage-2B tests pass unchanged.

## What each correction changed

### S3A-1 — `H_effective` requires a genuinely live assignment
`security.compute_h_effective` now counts a miner ONLY when, simultaneously: the round is
nonterminal; `MinerRecord.state == ACTIVE_HASHING`; a non-completed `MinerSearchState`
exists; `rc.assignments` actually **contains** `st.AssignmentID`; the assignment's
`MinerID`, `assignment_version`, `RoundID` and `TemplateID` all match; and the cursor lies
strictly inside the assigned range.  The previous
missing-assignment-treated-as-current fallback (`_current_assignment_version`) is **removed**.
Primary and activated-reserve assignment records now carry `RoundID`/`TemplateID`.

### S3A-2 — observe every capacity change; idempotent observations; real first breach
`EvaluateSecurityFloor` is invoked after each capacity-changing point: round start
(`participants_prepared`, measure-only), **every** primary `WakeCompleteEvent`, reserve
activation completion, primary/reserve `RangeExhaustEvent`, the reserve-activation
complete-seat-failure cancellation, and terminal round closure.  The all-primary-active gate
is gone.  Each observation is keyed by an immutable
`SecurityFloorObservationKey = (RoundID, TemplateID, triggering EventRef/hook id,
round_state_version, capacity_state_version)`; a replay of the same key returns the existing
observation and seats nothing (no counter advances).  `capacity_state_version` bumps on every
miner state transition (the only thing that changes `H_effective`'s composition).  The
duration below the floor is measured from the **real first breached observation** (round
start), not the later all-primary-active point; WAKING-primary capacity is accounted only for
the seat decision (never in `H_effective`), so the ramp is a real below-floor interval that is
not over-activated against.  A round is never terminated at its own start time (the
`participants_prepared` observation is measure-only; every actionable decision is deferred to
a point where simulation time has advanced).

### S3A-3 — true minimum-cardinality reserve selection
`security.select_reserves_to_cover` establishes minimum cardinality FIRST (fewest reserves,
by largest rate, that cover the hash-rate need and the miner-count need), then breaks ties by
the lexicographically smallest tuple of `activation_priority`, then `MinerID`.  The spec
counterexample (rates `[10, 100]`, need `90`) selects only the single 100-rate reserve.
`PARTIAL_RESTORATION` is recorded when capacity is seated but the floor stays unattainable.

### S3A-4 — transactional seating + start/complete rollback
`SeatReserveActivationTransaction` commits the slice claim, reserve-status transition,
request creation, StartEvent scheduling, EventRef publication and counter increment
all-or-none; a failed `ScheduleEvent` restores the slice to UNCLAIMED, the reserve to
AVAILABLE, clears every request/slice/event field, leaves the counter untouched and returns
`reserve_activation_seat_failed`.  `ReserveActivationStartEvent` inspects CompleteEvent
scheduling: on failure it never strands the miner WAKING — it returns the miner to
LOW_POWER_LISTEN, terminalises the request (FAILED) and reserve (CANCELLED), restores the
slice to UNCLAIMED (declared policy), and re-evaluates the floor.  (The canonical run
naturally exercises the complete-seat-failure path twice near the horizon, with zero stranded
or non-terminal records.)

### S3A-5 — complete activation-identity verification
`_verify_activation_identity` verifies the whole chain before any mutation: the request
exists and its round/template/miner/slice/generation match; the request belongs to the stated
`SecurityFloorObservationID`; the observation belongs to the stated `DecisionID`; the decision
selected this exact miner/slice pair; `rr.activation_request_id` links back; the current
EventRef equals the recorded start/complete EventRef; `expected_reserve_status`,
`expected_round_state_version == rc.state_version`, the slice status/claim, and the request
lifecycle status all match.  Any tampered id, version or EventRef performs no effect.

### S3A-6 — complete activation-request lifecycle
`ReserveActivationRequest` carries `status` (SEATED → STARTED → COMPLETED, or terminal
CANCELLED / FAILED / STALE_NO_EFFECT), `start_event_ref`, `complete_event_ref`, `started_at`,
`completed_at`, `DecisionID` and `disposition`, updated at every transition.  At round
closure: AVAILABLE → UNUSED_AT_ROUND_CLOSE; ACTIVATION_PENDING/WAKING → CANCELLED; ACTIVE →
EXHAUSTED (if its slice was searched to the end) or CLOSED_AT_ROUND_CLOSE — **never** left
ACTIVE or AVAILABLE; every activation request of a closed round is terminal; every queued
activation event is CANCELLED (via the round's QUEUED-event loop) or CONSUMED.

### S3A-7 — correct reserve-domain exhaustion semantics
`_maybe_terminate_no_block` never claims a no-block full-domain exhaustion while a reserve
slice is UNCLAIMED and activation is legally possible.  It classifies honestly:
`FULL_DOMAIN_EXHAUSTED_NO_BLOCK` (every primary AND reserve slice searched once, all slices
EXHAUSTED) vs `ROUND_CLOSED_WITH_UNUSED_RESERVE_DOMAIN` (reserve slices unused, e.g.
`min_rate == 0`).  The `min_rate == 0` counterexample closes with the explicit
unused-reserve-domain disposition and searches no reserve slice.

### S3A-8 — BlockSim adapter configures + executes Stage 3
`stage2config_from_blocksim` maps `P_reserve`, `floor_unattainable_policy` and the full
security-floor policy (`security_floor_enabled`, `minimum_active_hash_rate`,
`minimum_active_miner_count`, `activation_trigger_mode`, `reserve_selection_policy`,
`maximum_activations_per_round`, `activation_wake_latency`, `floor_tolerance`) into a
**validated** immutable `SecurityFloorPolicy` (via `__post_init__`), rejecting unsupported
policy names and negative rates/counts/latencies/tolerances.  The adapter schema is bumped to
`stage3a.1`.

## Files changed
`Models/PoCol/stage2/security.py`, `context.py`, `simulator.py`, `adapter.py`, `__init__.py`;
`tests/thesis_revision_v45/stage2/test_stage3_security_floor.py`,
`test_stage2_adapter.py`; new `.github/workflows/stage3a-pocol-tests.yml`; this
`docs/thesis_revision_v45/stage_03a/` deliverable set.  `events.py` and `config.py` carry the
Stage-3 identity/config surface (activation payload keys already complete; the default
`reserve_selection_policy` is `MINIMUM_CARDINALITY`).  `search.py` / `energy_experiment.py`
are unchanged.
