# Stage 1L — Round-Boundary Residency Audit (L5)

A structural audit of Stage-1L correction **L5** (a single idempotent round-boundary residency owner) in
the **PoCol** protocol pseudocode (`STAGE_01_PROTOCOL_PSEUDOCODE.md`). The Stage-1K pair of procedures
`FinalizeRoundResidency` + `BeginRoundResidency` is SUPERSEDED by ONE procedure,
`RebaseResidencyAtRoundBoundary` (§1a), that performs the old-round CLOSE and the new-round REOPEN
TOGETHER and is IDEMPOTENT via a deterministic `boundary_id = (prior_RoundID, new_RoundID)`. A boundary
already in the per-run `rebased_boundaries` set is a NO-OP, so a replayed or retried `RoundInitialise`
never re-closes, re-attributes, or re-opens the idle interval. `CloseRoundAssignments` records
`round_terminal_time` ONLY and never rebases. The idle interval between a round's closure and the next
round's `StartWake` is therefore counted EXACTLY ONCE (invariant **I19**, amended for the single
idempotent owner). This document is documentation only; it audits wording and control structure,
describes only the idle policy within PoCol, introduces no new consensus feature, and claims **no**
security, fairness, energy, or incentive property. The A1 baseline (`8.420833333 kWh`) is unchanged.

---

## 1. What L5 corrected (two procedures → one idempotent owner)

Stage-1K established that an OPEN per-miner residency interval persisting across a round boundary must be
rebased, not silently reset (K3). It did so with TWO paired procedures: `FinalizeRoundResidency`
(old-round close) and `BeginRoundResidency` (new-round reopen), invoked in sequence from the
`RoundInitialise` ELSE branch. That pairing had two structural exposures: it depended on the caller
issuing both calls in the correct order, and it had no guard against being invoked twice for the same
boundary. A replayed or retried `RoundInitialise` — permitted because the per-run event-loop bookkeeping
is carried forward across rounds (I-04) — could run the close/reopen a second time, re-attributing and
double-counting the idle interval.

L5 collapses the pair into ONE procedure, `RebaseResidencyAtRoundBoundary` (§1a), that performs both
halves together and short-circuits any repeat. The §0.8 `residency_ledger` comment now states this
normatively — *"The SINGLE idempotent owner `RebaseResidencyAtRoundBoundary` (§1a/L5) closes and reopens
the SAME state at the identical `boundary_time` … so a state that continues across the boundary is counted
exactly once (I19 amended). It is idempotent via `boundary_id` — a repeat is a no-op. The former
`FinalizeRoundResidency` / `BeginRoundResidency` are withdrawn (L5)."*

| Aspect | Stage-1K (K3) | Stage-1L (L5) |
|---|---|---|
| Cross-round rebase owner | TWO procedures: `FinalizeRoundResidency` + `BeginRoundResidency` (§1a) | ONE procedure: `RebaseResidencyAtRoundBoundary` (§1a) |
| Close old-round intervals | `FinalizeRoundResidency(boundary_time)` | step (1), same procedure |
| Reopen same state, new round | `BeginRoundResidency(boundary_time)` | step (2), same procedure |
| Boundary energy | ZERO `E_transition`/`E_coordination` (no state change) | ZERO `E_transition`/`E_coordination` (no state change) — unchanged |
| Idempotence | none — a repeat re-closes / re-attributes | step (0) + step (3): `boundary_id` key; a repeat is a NO-OP |
| Invocation | ELSE branch: `boundary_time <- prior_state.round_terminal_time`; two CALLs | ELSE branch: `boundary_id <- (prior_state.RoundID, RoundID_current)`; ONE CALL |
| `boundary_time` source | `prior_state.round_terminal_time` (by `CloseRoundAssignments`) | `prior_state.round_terminal_time`, recorded ONLY by `CloseRoundAssignments` — unchanged |
| Sole owner for ACTUAL state change | `ApplyMinerStateTransition` (§0.9) | `ApplyMinerStateTransition` (§0.9) — unchanged |

## 2. The single owner (§1a `RebaseResidencyAtRoundBoundary`)

The procedure takes `(prior_state, this RoundContext, boundary_id)` and, per its EFFECTS, runs four
ordered steps:

```
# (0) IDEMPOTENCE guard — a boundary already rebased is a NO-OP.
IF boundary_id in rebased_boundaries:
  RETURN rebase_noop(boundary_id)                        # L5: idempotent no-op
SET boundary_time <- prior_state.round_terminal_time     # recorded ONLY by CloseRoundAssignments (L5)
# (1) CLOSE every OPEN interval in the PRIOR round; attribute its energy to the OLD RoundID.
FOR EACH miner m with an OPEN residency interval in prior_state.residency_ledger (stable MinerID order):
  CLOSE residency(m, miner_state(m)) at boundary_time    # accrues P_state * (boundary_time - last_boundary)
  ATTRIBUTE that interval's energy to prior_state.RoundID
# (2) REOPEN the SAME state at the IDENTICAL boundary_time in the NEW round's ledger.
FOR EACH miner m in {LOW_POWER_LISTEN, REGISTERED, RESERVE, OFFLINE, DISQUALIFIED} whose state
    continues across the boundary (stable MinerID order):
  OPEN residency(m, miner_state(m)) at boundary_time     # same state, same time; continues P_state accrual
  # do NOT charge E_transition/E_coordination: no state change occurred
# (3) record the boundary as rebased so any repeat is a no-op.
ADD boundary_id to rebased_boundaries
```

**One owner, both halves.** The close (step 1) and the reopen (step 2) live in the SAME procedure body, so
the ordering that K3 left to the caller is now internal and cannot be issued out of sequence or partially.
The §1a NOTE states it is *"the ONLY procedure that closes+reopens an open residency interval across a
round boundary (`ApplyMinerStateTransition` remains the sole owner of intervals for an ACTUAL state
change)."*

**Shared boundary instant, no transition energy.** `boundary_time = prior_state.round_terminal_time` is a
single instant shared by the close and the reopen, so the two half-intervals meet exactly at
`boundary_time` with no gap and no overlap. Neither step changes `miner_state`, so neither records
`E_transition`/`E_coordination`; the §1a NOTE records that *"The boundary contributes ZERO transition
energy."* A one-shot boundary energy is charged ONLY for an ACTUAL edge, by `ApplyMinerStateTransition`.

**Five continuing states.** Step (2) reopens for miners in
`{LOW_POWER_LISTEN, REGISTERED, RESERVE, OFFLINE, DISQUALIFIED}`. `ACTIVE_HASHING` is absent by
construction — a terminal round (`ROUND_ACCEPTED`/`ROUND_ABORTED`) has no `ACTIVE_HASHING` miner to
continue — so `t_ACTIVE_HASHING = t_hash` (H7) is unaffected, as the §1a NOTE confirms.

**Invocation (§1, `RoundInitialise` ELSE branch).** The subsequent-round branch first preserves the
per-run bookkeeping (including `rebased_boundaries`) from `prior_state`, then:

```
SET boundary_id <- (prior_state.RoundID, RoundID_current)                    # L5: deterministic boundary id
CALL RebaseResidencyAtRoundBoundary(prior_state, this RoundContext, boundary_id)   # L5 (single owner; idempotent)
```

`rebased_boundaries` is a per-run set: `INITIALISE rebased_boundaries <- empty set` once at run start
(genesis, `prior_state = null`), and PRESERVED across rounds in the ELSE branch (I-04). It is listed in the
`RoundContext` return and the §0.8 registry block as *"the IDEMPOTENCE key: a boundary in this set is a
no-op on repeat, so a replayed/retried `RoundInitialise` never double-closes or double-attributes the idle
interval (I19)."*

## 3. Idempotence argument (`boundary_id` key)

The idempotence key is the deterministic pair `boundary_id = (prior_state.RoundID, RoundID_current)`.
Because both `RoundID`s are already fixed when the ELSE branch runs, the key for a given boundary is
identical on every (re)invocation of `RoundInitialise` for that same pair of rounds. Step (0) tests
membership in the per-run `rebased_boundaries` set BEFORE reading `boundary_time` or touching either
ledger; step (3) adds the key only after both ledger halves have completed. The first invocation therefore
performs the full close+reopen and records the key; every later invocation with the same key returns
`rebase_noop(boundary_id)` at step (0) — no re-close, no re-attribution, no re-open.

### 3.1 Walk-through — call twice for the same `boundary_id`

Preconditions: round `r` closed at `round_terminal_time = t_b`; miner `M` is `LOW_POWER_LISTEN` and
continues across the boundary into round `r+1`; `boundary_id = (r, r+1)`; `rebased_boundaries` does not yet
contain `(r, r+1)`.

| Call | Step (0) test | Steps (1)–(2) | Step (3) | Net effect |
|---|---|---|---|---|
| **First** `RebaseResidencyAtRoundBoundary(prior=r, new=r+1, (r,r+1))` | `(r,r+1) ∉ rebased_boundaries` → proceed | CLOSE `M`'s open `LOW_POWER_LISTEN` at `t_b`, energy → `r`; REOPEN same state at `t_b` for `r+1`, ZERO transition energy | ADD `(r,r+1)` to `rebased_boundaries` | idle interval split once at `t_b` |
| **Second** (replay/retry) `RebaseResidencyAtRoundBoundary(prior=r, new=r+1, (r,r+1))` | `(r,r+1) ∈ rebased_boundaries` → `RETURN rebase_noop((r,r+1))` | not reached | not reached | NO-OP: no second close, no re-attribution, no second reopen |

After the second call the ledgers are byte-for-byte what the first call left: `M`'s `[t_enter, t_b]`
segment is attributed to `r` exactly once and its open `[t_b, …]` segment in `r+1` exists exactly once. The
idle interval is not counted twice. This holds for a retried `RoundInitialise` precisely because
`rebased_boundaries` is per-run and PRESERVED across rounds (I-04), so the key set by the first pass is
still visible to the retry.

## 4. Ownership boundary and `CloseRoundAssignments`

`ApplyMinerStateTransition` (§0.9, F6) REMAINS the SOLE owner of `residency_ledger` accounting for every
ACTUAL miner-state change — it opens/closes an interval and charges one-shot boundary energy only when
`miner_state` actually changes. `RebaseResidencyAtRoundBoundary` (§1a) is the ONLY sanctioned way an OPEN
interval crosses a round boundary WITHOUT a state change, and it is a single idempotent owner rather than a
pair. No third writer of any `t_<state>` exists.

`CloseRoundAssignments` (§17) records the round's terminal time and nothing more: after finalising state
durations and energy to the exact closure time, it executes
`RECORD round_terminal_time(RoundID) <- now` and its NOTE states — *"`CloseRoundAssignments` records
`round_terminal_time` ONLY; the cross-round residency rebase is performed exclusively by
`RebaseResidencyAtRoundBoundary` (§1a), idempotently via `boundary_id`, so the idle interval between this
closure and the next round's `StartWake` is counted EXACTLY ONCE (I19)."* It performs no rebase; the
timestamp it records is exactly the `boundary_time` the next `RoundInitialise` reads.

## 5. Reconciliation with I19 / I5 (A1 unchanged)

- **I19 (single-owner, no double-count residency; catalogue entry amended for L5).** The formal statement
  now names `RebaseResidencyAtRoundBoundary` as the ONE procedure that *"SUPERSEDES the former
  `FinalizeRoundResidency` / `BeginRoundResidency`,"* closes the open interval (energy → OLD round) and
  reopens the SAME state at the IDENTICAL `boundary_time = round_terminal_time` with NO transition energy,
  and is *"**idempotent** via a deterministic `boundary_id = (prior_RoundID, new_RoundID)`: a replayed or
  retried `RoundInitialise` re-invoking it is a no-op."* Its enforcement-point list adds
  `RebaseResidencyAtRoundBoundary` as *"the ONLY cross-round rebase … keyed by `boundary_id`"* and records
  that `CloseRoundAssignments` *"records `round_terminal_time` only, performs no rebase."*
- **I5 (durations reconcile to `T`; energy-model §3 amended).** The close-at-`t_b` / reopen-at-`t_b`
  discipline makes the two half-intervals share the instant `t_b` — no gap, no overlap — so the per-miner
  durations still partition `[0, T]` with `Σ_{s} t_{i,s} = T = 10,000 s` over the eight states and no
  residual `t_other` bucket. The energy-model *"Cross-round boundary rebase (I19; single idempotent owner,
  L5)"* paragraph states the boundary instant is *"neither duplicated nor dropped"* and the rebase *"is
  **idempotent** via a deterministic `boundary_id` … a replayed or retried `RoundInitialise` re-invoking
  it is a no-op, so no boundary is ever applied twice."*
- **A1 discipline.** The rebase changes ONLY how a continuing occupancy's time is split across the two
  per-round ledgers, never the total. The A1 baseline — continuous full-participation energy over
  `T = 10,000 s` — remains **8.420833333 kWh**, UNCHANGED. Any modeled energy change is attributable ONLY
  to reduced active power-time, never to how the boundary counts a continuing idle interval. L5 is a
  structural accounting correction and introduces **no new consensus feature**.

## 6. Acceptance-style PASS checklist

| # | Check | Result | Ground |
|---|---|---|---|
| C1 | There is exactly ONE cross-round residency-rebase owner (`RebaseResidencyAtRoundBoundary`); the K3 pair is superseded | PASS | §1a procedure + §1a intro; §0.8 residency_ledger comment |
| C2 | The single owner performs the old-round CLOSE and the new-round REOPEN together | PASS | §1a steps (1) and (2) |
| C3 | It is idempotent via `boundary_id = (prior_RoundID, new_RoundID)`; a repeat is a NO-OP | PASS | §1a steps (0) and (3); §0.8 `rebased_boundaries` |
| C4 | A replayed/retried `RoundInitialise` never double-closes or double-attributes the idle interval | PASS | §3.1 walk-through; `rebased_boundaries` per-run, preserved (I-04) |
| C5 | `boundary_time = prior_state.round_terminal_time`; reopen at the IDENTICAL time with ZERO transition energy | PASS | §1a step (0)/(2); §1a NOTE |
| C6 | `CloseRoundAssignments` records `round_terminal_time` ONLY and never rebases | PASS | §17 `RECORD round_terminal_time`; §17 NOTE (L5) |
| C7 | `ApplyMinerStateTransition` remains the SOLE owner of intervals for an ACTUAL state change | PASS | §0.3/§0.9; §1a NOTE |
| C8 | Covers the five continuing states; `ACTIVE_HASHING`/`t_hash` unaffected | PASS | §1a step (2) state set; §1a NOTE |
| C9 | The idle interval is counted EXACTLY ONCE (I19); reconciles with I5 | PASS | I19 formal statement (L5); energy-model §3 (L5) |
| C10 | A1 baseline unchanged; any energy change attributable only to reduced active power-time; no new consensus feature | PASS | §5; I19 scope note; energy-model §3; A1 = 8.420833333 kWh |

---

## Result

**Result: ROUND-BOUNDARY RESIDENCY AUDIT (Stage 1L): PASS** — the Stage-1K pair `FinalizeRoundResidency` +
`BeginRoundResidency` is superseded by ONE idempotent owner, `RebaseResidencyAtRoundBoundary` (§1a), that
performs the old-round CLOSE and the new-round REOPEN together, attributing the closed interval's energy to
the OLD `RoundID` and reopening the SAME state at the IDENTICAL `boundary_time = prior_state.round_terminal_time`
with ZERO transition energy across the five continuing states
`LOW_POWER_LISTEN`/`REGISTERED`/`RESERVE`/`OFFLINE`/`DISQUALIFIED`; it is idempotent via the deterministic
`boundary_id = (prior_state.RoundID, RoundID_current)` recorded in the per-run `rebased_boundaries` set, so
a repeat is a no-op (a second call for the same `boundary_id` returns `rebase_noop` at step (0), leaving the
ledgers unchanged) and a replayed or retried `RoundInitialise` never double-counts or double-attributes the
idle interval; `CloseRoundAssignments` records `round_terminal_time` ONLY and never rebases, while
`ApplyMinerStateTransition` remains the sole residency owner for ACTUAL state changes; the idle interval
between a round's closure and the next round's `StartWake` is thus counted exactly once (I19 amended for the
single idempotent boundary owner), the durations reconcile with I5, and the A1 baseline
(`8.420833333 kWh`) is unchanged with any energy change attributable only to reduced active power-time — the
rebase changes only how time is split across rounds, never the total — adding no new consensus feature.
