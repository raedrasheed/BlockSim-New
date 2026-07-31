# Stage 1K — Semantic Test Vectors (TV81–TV90)

Ten blocking test vectors for the Stage-1K core-handoff closure. Each names the exact procedure(s) in
`STAGE_01_PROTOCOL_PSEUDOCODE.md` and its exact preconditions; none assumes an unmodeled external
action. These extend TV1–TV80 (historical, in `STAGE_01C..J_*`, which are NOT modified in Stage 1K). No
property (energy, security, fairness) is claimed. The A1 baseline (`8.420833333 kWh`) is unchanged. Name
remains **PoCol**; mechanism is **the idle policy within PoCol**.

---

## TV81 — a VALID_SOLUTION_VERIFIED finder is re-assigned in the next round via T10

**Preconditions.** In round `r`, a finder `F` paused with `entry_stop_reason = VALID_SOLUTION_VERIFIED`;
round `r` was ACCEPTED and `F`'s paused head was CLOSED at closure (its `entry_stop_reason` preserved as
`VALID_SOLUTION_VERIFIED` for attribution). Round `r+1` runs `RoundInitialise` then `TemplateCommit`
(new `RoundID`/`TemplateID`), reaching `ASSIGNMENT`.

**Trace.** `PrepareParticipantsForNewRound` iterates in stable MinerID order; for `F` it takes `CASE
LOW_POWER_LISTEN` / `VALID_SOLUTION_VERIFIED OR ROUND_ACCEPTED OR ROUND_ABORTED`: archives the prior
reason, ASSERTs no live head remains (the head is CLOSED, I18b/J7), binds a fresh `ORIGINAL` `PENDING`
under the NEW `RoundID`/`TemplateID`, and `StartWake(from_state = LOW_POWER_LISTEN)` (T10) with the
driver envelope. `VALID_SOLUTION_VERIFIED` does NOT fall into a DEFAULT/CONTINUE.

**Expected.** `F` receives a fresh new-round assignment via T10; no PAUSED/CLOSED head is reopened.
Reqs: **K1**, J7, I18b.

## TV82 — the finder and several certificate-verifying recipients all return in the next round

**Preconditions.** In round `r`, the finder `F` and recipients `R1..Rk` all paused with
`entry_stop_reason = VALID_SOLUTION_VERIFIED` (PATH B) on the accepted certificate; round `r` was
accepted and all their heads were CLOSED at closure.

**Trace.** In round `r+1`'s `ASSIGNMENT`, `PrepareParticipantsForNewRound` processes `F, R1..Rk` (stable
MinerID order); each takes the `VALID_SOLUTION_VERIFIED` branch → archive → fresh `ORIGINAL` under the
new ids → `StartWake` T10. No old assignment is reopened for any of them.

**Expected.** Every verified finder/recipient returns to participation in `r+1` via a fresh T10
assignment; none reopens a closed head. Reqs: **K1**, J7, I18b.

## TV83 — PrepareParticipantsForNewRound performs ASSIGNMENT → HASHING before any hash work

**Preconditions.** Round `r+1` is in `ASSIGNMENT`; `PrepareParticipantsForNewRound` has built the
intended assignment set (all `PENDING`, waking).

**Trace.** After the miner loop, `PrepareParticipantsForNewRound` CALLs `CompleteAssignmentPhase`, which
ASSERTs every `PENDING` is bound to the current `(RoundID, TemplateID)` and satisfies I1/I3/I18b, then
`TRANSITION round_state -> HASHING` (R4) and `CaptureSecurityCensusOnApplicabilityEntry(HASHING)`. Only
after this does hashing begin (at each miner's own `WakeCompleteEvent`).

**Expected.** `ASSIGNMENT → HASHING` is an executable named-procedure step; the round is in `HASHING`
before any `HashWorkEvent` executes. Reqs: **K2**, K7.

## TV84 — a HashWorkEvent dispatched while ASSIGNMENT is a no-op; after completion it executes

**Preconditions.** A `HashWorkEvent` is dispatched while `round_state = ASSIGNMENT` (before
`CompleteAssignmentPhase`); later, after `ASSIGNMENT → HASHING`, a new `HashWorkEvent` is dispatched.

**Trace.** The first `HashWorkEvent` hits the guard `round_state not in {HASHING, SOLUTION_PROPAGATION,
SECURITY_RECOVERY}` (ASSIGNMENT is not hashing-capable) → `RETURN hash_work_noop` (K2). After
`CompleteAssignmentPhase` puts the round in `HASHING`, the later `HashWorkEvent` (miner `ACTIVE_HASHING`,
version `CURRENT`) executes normally.

**Expected.** Hashing cannot be stranded behind `ASSIGNMENT`; the pre-transition unit is a no-op, the
post-transition unit runs. Reqs: **K2**.

## TV85 — a LOW_POWER_LISTEN miner across a non-zero inter-round interval is charged exactly once

**Preconditions.** Miner `M` is `LOW_POWER_LISTEN` when round `r` closes at `boundary_time`; it remains
`LOW_POWER_LISTEN` until round `r+1`'s `StartWake` at a strictly later time (a non-zero interval).

**Trace.** `FinalizeRoundResidency(boundary_time)` closes `M`'s open `LOW_POWER_LISTEN` interval,
attributing its energy to round `r`. `BeginRoundResidency(boundary_time)` reopens `LOW_POWER_LISTEN` for
`r+1` at the IDENTICAL `boundary_time`, charging NO transition energy (no state change). The single
`P_listen` interval spanning the boundary is thus split at `boundary_time` and counted once, not reset
or duplicated (I19 amended).

**Expected.** The inter-round `P_listen` interval is counted exactly once across the boundary; no
transition energy is charged. Reqs: **K3**, I19, I5, I6.

## TV86 — a driver-originated transition carries a complete DriverEventEnvelope and a deterministic id

**Preconditions.** `MinerRegister` (a sim-driver entry point) registers a miner `M`.

**Trace.** `MinerRegister` constructs `env = DriverEventEnvelope(event_time = now, delta_cycle = 0,
event_seq = next EQ.event_creation_seq)` and calls `ApplyMinerStateTransition(… , event_time =
env.event_time, delta_cycle = env.delta_cycle, event_seq = env.event_seq, …)` (T1). The
`TransitionEventID` is built from these DEFINED fields; nothing is ambient (K4).

**Expected.** The driver transition has a complete `(event_time, delta_cycle, event_seq)` and a
deterministic `TransitionEventID`; no ambient `event_seq`. Reqs: **K4**, J3.

## TV87 — an illegal stale transition is rejected and absent from the applied registry

**Preconditions.** `ApplyMinerStateTransition` is called with `old_state = WAKING` but
`miner_state(M) = ACTIVE_HASHING` already (a stale source that is NOT an exact replay).

**Trace.** Step (2) finds the `TransitionEventID` NOT in `applied_transition_registry`; step (3) finds
`old_state != miner_state(M)` → `RECORD transition_rejection_log(…, stale_source)` and `RETURN
illegal_stale_source`. The atomic apply (step 5) never runs, so the id is NEVER added to
`applied_transition_registry`.

**Expected.** The stale transition is rejected, logged in `transition_rejection_log`, and absent from
`applied_transition_registry`; no residency/energy is charged. Reqs: **K5**, J2.

## TV88 — an exact replay of an applied TransitionEventID is suppressed

**Preconditions.** A transition was successfully applied (its `TransitionEventID` is in
`applied_transition_registry`); the IDENTICAL `TransitionEventID` is replayed.

**Trace.** Step (2) finds the id in `applied_transition_registry` → `RETURN duplicate_suppressed` before
any old-state check or charge. No second boundary/energy.

**Expected.** The exact replay is suppressed by identity; no second residency boundary or energy (I19
preserved). Reqs: **K5**, J2, I19.

## TV89 — lease expiry closes the CURRENT version atomically with no undefined INVALID state

**Preconditions.** A holder `H`'s lease expires and the holder does NOT renew (E9). `H` is
`ACTIVE_HASHING` on `CURRENT` version `v` (`accepted_frontier = f`, `s ≤ f < e`).

**Trace.** `LeaseExpiry` performs NO `INVALIDATE`; it routes `H` through `EnterLowPowerListen(stop_reason
= ASSIGNMENT_REVOKED, assignment_ref = v, custody_on_close = expired, termination_reason = lease_expiry)`,
whose atomic step sets `status(v) = CLOSED`, `custody_status = expired`, `termination_reason =
lease_expiry` (K6/J7). One live CURRENT head exists before (I18b), zero after (CLOSED lineage). The
accepted searched prefix is preserved; only the accepted unsearched suffix `[f+1, e]` is reassigned via
`RangeReassign`.

**Expected.** No undefined `INVALID` state; the version reaches `CLOSED`/`expired`/`lease_expiry`
atomically; I18a/I18b hold at every observable point. Reqs: **K6**, J7, I18a, I18b.

## TV90 — the round enters HASHING with H_active = 0 and no successful wake; one floor decision fires

**Preconditions.** In round `r+1`, `PrepareParticipantsForNewRound` waked miners but (in this scenario)
NO `WakeCompleteEvent` has yet succeeded, so `H_active = 0` at the `ASSIGNMENT → HASHING` moment. No
miner-state boundary occurs at that `event_time`.

**Trace.** `CompleteAssignmentPhase` transitions to `HASHING` and CALLs
`CaptureSecurityCensusOnApplicabilityEntry(HASHING, at = now)`, which computes `H_active = 0` and writes
`security_census_dirty[now]` AND `latest_security_census[now]` (with provenance) TOGETHER (K7/J1). The
event-time epilogue `FinalizeEventTimeSecurityCensus(now)` then runs `SecurityFloorEvaluate`, which — now
in `HASHING` (an applicable state, J6) with `H_active = 0` — records the active-/honest-floor breach
(I16) and decides the floor ONCE. No breach was recorded while the round was still `ASSIGNMENT`.

**Expected.** The applicability-entry census triggers exactly one floor decision on entry to `HASHING`
even though no wake succeeded and no miner boundary occurred; no breach was created during `ASSIGNMENT`.
Reqs: **K7**, J6, I16, I17.

---

## Coverage

TV81/TV82 (K1 VALID_SOLUTION_VERIFIED next-round path, finder + recipients), TV83/TV84 (K2 executable
ASSIGNMENT→HASHING and no stranded hashing), TV85 (K3 cross-round residency once), TV86 (K4 driver
envelope), TV87/TV88 (K5 rejected-absent-from-applied / replay suppressed), TV89 (K6 canonical lease
termination), TV90 (K7 applicability-entry census). Every vector names exact procedures and
preconditions and assumes no unmodeled external action; the A1 baseline is unchanged.
