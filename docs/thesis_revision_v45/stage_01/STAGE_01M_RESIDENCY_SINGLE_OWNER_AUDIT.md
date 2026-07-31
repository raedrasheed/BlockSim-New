# Stage 1M — Residency Single-Owner Boundary Audit (M4)

A structural audit of Stage-1M correction **M4 — one residency-boundary owner in executable text** — in the
**PoCol** protocol pseudocode (`STAGE_01_PROTOCOL_PSEUDOCODE.md`), describing PoCol with **the idle policy
within PoCol** enabled. M4 unifies EVERY boundary residency close/reopen under ONE procedure,
`SettleResidencyBoundary` (§1a), carrying two modes — `REBASE_TO_NEXT_ROUND` (close the old-round interval,
attribute its energy to the old round, and reopen the SAME state at the IDENTICAL `boundary_time` for the
new round with NO transition energy) and `FINAL_RUN_END` (close every open interval at the run horizon with
NO reopen). It supersedes the earlier `RebaseResidencyAtRoundBoundary` and, before it, the
`FinalizeRoundResidency` / `BeginRoundResidency` pair, and it is idempotent via a deterministic
`boundary_id`. In the same correction the in-line executable line that competed with this owner is REMOVED:
`CloseRoundAssignments` (§17a) records `round_terminal_time` ONLY and performs no residency/energy
finalisation, and `RoundAbort` (§20) replaces its former in-line `finalise energy_ledger` step with a call
to `SettleResidencyBoundary` mode `FINAL_RUN_END` before the I5/I6/I7 accounting asserts. This document is
documentation only; it audits wording and control structure, describes only the idle policy within PoCol,
introduces no new consensus feature, and claims **no** security, fairness, energy, or incentive property.
The A1 baseline (`8.420833333 kWh`) is unchanged.

---

## 1. What M4 corrected (one boundary owner, no competing in-line finalisation)

Stage-1L had already collapsed the cross-round rebase into a single idempotent procedure. M4 completes the
consolidation along two axes:

1. **One owner across BOTH boundary kinds.** The cross-round rebase and the run-end settle are now the SAME
   procedure, `SettleResidencyBoundary` (§1a), differentiated only by `mode ∈ {REBASE_TO_NEXT_ROUND,
   FINAL_RUN_END}`. Previously the run end was settled by a separate in-line finalisation step, leaving two
   pieces of executable text that could each close a residency interval at the run horizon.
2. **No competing finalisation in `CloseRoundAssignments`.** The earlier executable line *"finalise state
   durations and energy to the EXACT closure time"* inside `CloseRoundAssignments` (§17a) is DELETED. That
   line was a second writer that closed residency/energy at the round boundary, competing with the single
   boundary owner. `CloseRoundAssignments` now records `round_terminal_time` ONLY — the exact
   `boundary_time` the next `RoundInitialise` (or the final-run settle) reads — and performs no rebase.

The §0.8 `residency_ledger` comment now states this normatively — *"The SINGLE idempotent owner
`SettleResidencyBoundary` (§1a/L5/M4) closes and reopens the SAME state at the identical `boundary_time`
(old-round energy attributed; NO transition energy) … It is idempotent via `boundary_id` — a repeat is a
no-op. The former `FinalizeRoundResidency` / `BeginRoundResidency` are withdrawn."* The §1a intro
adds the unifying statement — *"ONE procedure, `SettleResidencyBoundary`, owns EVERY residency close/reopen
at a boundary … in particular `CloseRoundAssignments` performs NO residency/energy finalisation (M4); it
records `round_terminal_time` only."*

| Aspect | Stage-1L (L5) | Stage-1M (M4) |
|---|---|---|
| Boundary residency owner | ONE procedure `RebaseResidencyAtRoundBoundary` (§1a), cross-round only | ONE procedure `SettleResidencyBoundary` (§1a), BOTH boundary kinds via `mode` |
| Cross-round close + reopen | that procedure | `mode = REBASE_TO_NEXT_ROUND` (close old, reopen same state at identical `boundary_time`) |
| Run-end close | separate in-line finalisation (`RoundAbort` `finalise energy_ledger`; closure-time finalise) | `mode = FINAL_RUN_END` (close all open intervals at horizon `T`, NO reopen) — same owner |
| `CloseRoundAssignments` (§17a) | records `round_terminal_time`; also carried a closure-time finalise line | records `round_terminal_time` ONLY; the in-line `finalise … to the EXACT closure time` line REMOVED |
| `RoundAbort` (§20) | in-line `finalise energy_ledger` before the I5/I6/I7 asserts | `CALL SettleResidencyBoundary(mode = FINAL_RUN_END, boundary_id = (RoundID_current, RUN_END))` before the asserts |
| Idempotence key | `boundary_id = (prior_RoundID, new_RoundID)` in `rebased_boundaries` | `boundary_id = (prior_RoundID, new_RoundID)` OR `(RoundID, RUN_END)` in `rebased_boundaries` |
| Boundary energy | ZERO `E_transition`/`E_coordination` (no state change) | ZERO `E_transition`/`E_coordination` (no state change) — unchanged |
| Sole owner for an ACTUAL state change | `ApplyMinerStateTransition` (§0.9) | `ApplyMinerStateTransition` (§0.9) — unchanged |

## 2. The single owner (§1a `SettleResidencyBoundary`)

The procedure takes `(RoundContext, mode, boundary_id, prior_state = null)` and, per its EFFECTS, runs the
idempotence guard, then mode-selected close (and, for the rebase mode, reopen) steps:

```
# (0) IDEMPOTENCE: a boundary already settled is a NO-OP -- no re-close, no re-attribution, no re-open.
IF boundary_id in rebased_boundaries:
  RETURN settle_noop(boundary_id)                              # M4/L5: idempotent no-op
IF mode = REBASE_TO_NEXT_ROUND:
  SET boundary_time <- prior_state.round_terminal_time         # recorded ONLY by CloseRoundAssignments (M4/L5)
  SET close_ledger  <- prior_state.residency_ledger ; SET attribute_to <- prior_state.RoundID
ELSE:  # FINAL_RUN_END
  SET boundary_time <- run_horizon_T                           # the fixed simulation horizon
  SET close_ledger  <- RoundContext.residency_ledger ; SET attribute_to <- RoundID_current
# (1) CLOSE every OPEN interval in close_ledger at boundary_time and attribute its energy. miner_state
#     unchanged, so NO E_transition/E_coordination.
FOR EACH miner m with an OPEN residency interval in close_ledger (stable MinerID order):
  CLOSE residency(m, miner_state(m)) at boundary_time          # accrues P_state * (boundary_time - last_boundary)
  ATTRIBUTE that interval's energy to attribute_to
# (2) REBASE_TO_NEXT_ROUND ONLY: REOPEN the SAME state at the IDENTICAL boundary_time in the NEW ledger.
IF mode = REBASE_TO_NEXT_ROUND:
  FOR EACH miner m in {LOW_POWER_LISTEN, REGISTERED, RESERVE, OFFLINE, DISQUALIFIED} whose state
      continues across the boundary (stable MinerID order):
    OPEN residency(m, miner_state(m)) at boundary_time         # same state, same time; continues P_state accrual
    # do NOT charge E_transition/E_coordination: no state change occurred
# (3) record the boundary as settled so any repeat is a no-op (the idempotence key).
ADD boundary_id to rebased_boundaries
```

**One owner, two modes, both halves internal.** The close (step 1) and, for the rebase mode, the reopen
(step 2) live in the SAME procedure body; the ordering is internal and cannot be issued out of sequence or
partially. The §1a NOTE states it is *"the ONLY procedure that closes (and, for REBASE, reopens) an open
residency interval at a boundary … `ApplyMinerStateTransition` remains the sole owner of intervals for an
ACTUAL state change; this procedure performs ONLY the no-state-change boundary settle."*

**Shared boundary instant, no transition energy.** In `REBASE_TO_NEXT_ROUND`, `boundary_time =
prior_state.round_terminal_time` is a single instant shared by the close and the reopen, so the two
half-intervals meet exactly at `boundary_time` with no gap and no overlap. Neither step changes
`miner_state`, so neither records `E_transition`/`E_coordination`; the §1a NOTE records that *"The boundary
contributes ZERO transition energy."* A one-shot boundary energy is charged ONLY for an ACTUAL edge, by
`ApplyMinerStateTransition` (§0.9, step 5b).

**Run-end mode closes without reopening.** In `FINAL_RUN_END`, `boundary_time = run_horizon_T`, the close
runs over `RoundContext.residency_ledger` attributing to `RoundID_current`, and step (2) is skipped — *"the
run is over."* `t_ACTIVE_HASHING = t_hash` (H7) is unaffected: a terminal round has no `ACTIVE_HASHING`
miner to continue, as the §1a NOTE confirms.

**Invocation sites.** `RoundInitialise` (§1) ELSE branch sets `boundary_id <- (prior_state.RoundID,
RoundID_current)` and calls `SettleResidencyBoundary(this RoundContext, mode = REBASE_TO_NEXT_ROUND,
boundary_id = boundary_id, prior_state = prior_state)`. `RoundAbort` (§20) calls
`SettleResidencyBoundary(RoundContext, mode = FINAL_RUN_END, boundary_id = (RoundID_current, RUN_END))`
after `CloseRoundAssignments` and before `ASSERT per-miner sums (I6) and network sum (I7); ASSERT durations
reconcile to horizon T (I5)`. `rebased_boundaries` is a per-run set: `INITIALISE rebased_boundaries <- empty
set` once at run start (genesis, `prior_state = null`), and PRESERVED across rounds in the ELSE branch
(I-04); the §0.8 registry block records it as *"the IDEMPOTENCE key: a boundary in this set is a no-op on
repeat, so a replayed/retried `RoundInitialise` never double-closes or double-attributes the idle interval
(I19)."*

## 3. Ownership table — every residency close/reopen site

Every site in the pseudocode that closes or reopens a residency interval, and its sole owner.
`SettleResidencyBoundary` (§1a) is the sole owner of every *boundary* (no-state-change) close/reopen;
`ApplyMinerStateTransition` (§0.9) is the sole owner of every *actual state-change* close/open — the two
never overlap, and no third writer of any `t_<state>` exists.

| Site (procedure §) | Residency action | Owner | Competing finalisation? |
|---|---|---|---|
| `ApplyMinerStateTransition` §0.9 (5a) | CLOSE old + OPEN new interval on an ACTUAL miner-state edge | `ApplyMinerStateTransition` (sole owner for state changes) | none — distinct from boundary settle |
| `SettleResidencyBoundary` §1a step (1), `REBASE_TO_NEXT_ROUND` | CLOSE every open prior-round interval at `boundary_time`, energy → old `RoundID` | `SettleResidencyBoundary` | none |
| `SettleResidencyBoundary` §1a step (2), `REBASE_TO_NEXT_ROUND` | REOPEN same state at identical `boundary_time`, ZERO transition energy | `SettleResidencyBoundary` | none |
| `SettleResidencyBoundary` §1a step (1), `FINAL_RUN_END` | CLOSE every open interval at `run_horizon_T`, energy → `RoundID_current`; NO reopen | `SettleResidencyBoundary` | none |
| `RoundInitialise` §1 ELSE branch | invokes the rebase (`mode = REBASE_TO_NEXT_ROUND`, `boundary_id = (prior_RoundID, RoundID_current)`) | delegates to `SettleResidencyBoundary` | none — no in-line finalisation |
| `RoundAbort` §20 | invokes the run-end settle (`mode = FINAL_RUN_END`, `boundary_id = (RoundID_current, RUN_END)`) before I5/I6/I7 asserts | delegates to `SettleResidencyBoundary` | none — former in-line `finalise energy_ledger` REMOVED |
| `CloseRoundAssignments` §17a | records `round_terminal_time` ONLY; performs no residency/energy finalisation | records the boundary timestamp only | none — the in-line `finalise … to the EXACT closure time` line REMOVED |
| `HashWorkEvent` §0.7b/§0.9 | records hash-work METADATA only; increments NO `t_<state>` | not a residency writer | none (H7/G9) |

The two removed lines are the crux of M4: the `CloseRoundAssignments` §17a comment records that *"The
earlier executable line `finalise state durations and energy to the EXACT closure time` is REMOVED: it
competed with the single residency-boundary owner,"* and the `RoundAbort` §20 comment records that *"the
former `finalise energy_ledger` line is REMOVED"* in favour of the `FINAL_RUN_END` call. After M4, no
executable line other than the two owners above touches a residency interval.

## 4. Idempotence walk-through (`boundary_id` key)

The idempotence key is the deterministic `boundary_id` — `(prior_state.RoundID, RoundID_current)` for the
rebase mode, `(RoundID_current, RUN_END)` for the run-end mode. Both components are already fixed when the
owner runs, so the key for a given boundary is identical on every (re)invocation. Step (0) tests membership
in the per-run `rebased_boundaries` set BEFORE reading `boundary_time` or touching either ledger; step (3)
adds the key only after the ledger work completes. The first invocation performs the full close (and, for
the rebase mode, reopen) and records the key; every later invocation with the same key returns
`settle_noop(boundary_id)` at step (0) — no re-close, no re-attribution, no re-open.

### 4.1 Rebase mode — call twice for the same `boundary_id`

Preconditions: round `r` closed at `round_terminal_time = t_b` (recorded by `CloseRoundAssignments`, §17a);
miner `M` is `LOW_POWER_LISTEN` and continues across the boundary into round `r+1`; `boundary_id = (r,
r+1)`; `rebased_boundaries` does not yet contain `(r, r+1)`.

| Call | Step (0) test | Steps (1)–(2) | Step (3) | Net effect |
|---|---|---|---|---|
| **First** `SettleResidencyBoundary(REBASE_TO_NEXT_ROUND, (r,r+1), prior=r)` | `(r,r+1) ∉ rebased_boundaries` → proceed | CLOSE `M`'s open `LOW_POWER_LISTEN` at `t_b`, energy → `r`; REOPEN same state at `t_b` for `r+1`, ZERO transition energy | ADD `(r,r+1)` | idle interval split once at `t_b` |
| **Second** (replay/retry `RoundInitialise`) | `(r,r+1) ∈ rebased_boundaries` → `RETURN settle_noop((r,r+1))` | not reached | not reached | NO-OP: no second close, no re-attribution, no second reopen |

### 4.2 Run-end mode — call twice for the same `boundary_id`

Preconditions: the run is ending; `RoundAbort` (§20) runs for the current round; miner `M` is
`LOW_POWER_LISTEN` with an OPEN interval at the horizon; `boundary_id = (RoundID_current, RUN_END)`;
`rebased_boundaries` does not yet contain it.

| Call | Step (0) test | Step (1) | Step (2) | Step (3) | Net effect |
|---|---|---|---|---|---|
| **First** `SettleResidencyBoundary(FINAL_RUN_END, (RoundID_current, RUN_END))` | key ∉ `rebased_boundaries` → proceed | CLOSE `M`'s open interval at `run_horizon_T`, energy → `RoundID_current` | skipped (no reopen at run end) | ADD `(RoundID_current, RUN_END)` | interval closed once at `T` |
| **Second** (re-entered `RoundAbort`) | key ∈ `rebased_boundaries` → `RETURN settle_noop(...)` | not reached | not reached | not reached | NO-OP: no second close, no re-attribution |

In both modes, after the second call the ledgers are byte-for-byte what the first call left: each interval
is closed and attributed exactly once. This holds for a retried `RoundInitialise` or a re-entered
`RoundAbort` precisely because `rebased_boundaries` is per-run and PRESERVED across rounds (I-04), so the key
set by the first pass is still visible to the retry, and the run-end `boundary_id` cannot collide with any
cross-round `boundary_id` (they are structurally distinct — a round pair vs. a `RUN_END` tag).

## 5. Reconciliation with I19 / I5 / the energy model (A1 unchanged)

- **I19 (single-owner, no double-count residency).** The catalogue entry names `SettleResidencyBoundary`
  (M4/L5) as the ONE boundary owner *"which SUPERSEDES the former `FinalizeRoundResidency` /
  `BeginRoundResidency`,"* describing both modes — `REBASE_TO_NEXT_ROUND` closes the open interval (energy →
  old round) and reopens the SAME state at the IDENTICAL `boundary_time = round_terminal_time` charging NO
  transition energy; `FINAL_RUN_END` closes every open interval at the run horizon with NO reopen — and
  states it is *"idempotent via a deterministic `boundary_id` (`(prior_RoundID, new_RoundID)` or `(RoundID,
  RUN_END)`): a replayed or retried `RoundInitialise` / `RoundAbort` re-invoking it is a no-op."* Its
  enforcement-point list adds `SettleResidencyBoundary` as *"the ONLY boundary residency close/reopen"* and
  records that `CloseRoundAssignments` *"performs NO residency finalisation — M4."*
- **I5 (durations reconcile to `T`).** The close-at-`t_b` / reopen-at-`t_b` discipline makes the two
  half-intervals share the boundary instant — no gap, no overlap — so the per-miner durations still
  partition `[0, T]` with `Σ_s t_{i,s} = T = 10,000 s`. `RoundAbort` (§20) asserts this reconciliation
  (`ASSERT durations reconcile to horizon T (I5)`) AFTER the `FINAL_RUN_END` settle, so the run-end close is
  in place before the accounting checks run.
- **Energy model §3 (boundary residency settle).** The *"Boundary residency settle (I19; single idempotent
  owner, L5; unified with run-end, M4)"* paragraph states the boundary instant is *"neither duplicated nor
  dropped,"* that `CloseRoundAssignments` performs *"no residency/energy finalisation … it records
  `round_terminal_time` only, so there is no competing owner,"* and that the rebase *"is idempotent via a
  deterministic `boundary_id` … so no boundary is ever applied twice."*
- **A1 discipline.** The settle changes ONLY how a continuing occupancy's time is split across the per-round
  ledgers (or closed at the horizon), never the total. The A1 baseline — continuous full-participation
  energy over `T = 10,000 s` — remains **8.420833333 kWh**, UNCHANGED. Any modeled energy change is
  attributable ONLY to reduced active power-time, never to how the boundary counts a continuing idle
  interval. M4 is a structural accounting correction and introduces **no new consensus feature**.

> **Frozen-vector naming.** The Stage-1L semantic-vector file records **TV96** against the historical name
> `RebaseResidencyAtRoundBoundary`. Those vectors are FROZEN; on paper TV96 is superseded by the new
> **TV102** written against `SettleResidencyBoundary`. The historical name in the frozen TV96 is expected
> and is NOT a mismatch with the current pseudocode; the frozen file is not modified.

## 6. Acceptance-style PASS checklist

| # | Check | Result | Ground |
|---|---|---|---|
| C1 | Exactly ONE procedure owns round-boundary residency closure (`SettleResidencyBoundary`); the L5/K3 predecessors are superseded | PASS | §1a procedure + §1a intro; §0.8 `residency_ledger` comment |
| C2 | `CloseRoundAssignments` (§17a) performs NO competing residency finalisation — the in-line closure-time finalise line is REMOVED; it records `round_terminal_time` only | PASS | §17a M4 comment + NOTE; `RECORD round_terminal_time(RoundID)` |
| C3 | The run-end case uses the SAME boundary-accounting owner via `mode = FINAL_RUN_END` (`RoundAbort` former `finalise energy_ledger` replaced) | PASS | §1a `FINAL_RUN_END` branch; §20 call + M4 comment |
| C4 | Idempotence via `boundary_id` prevents double closure in BOTH modes; a repeat returns `settle_noop` | PASS | §1a steps (0)/(3); §4.1/§4.2 walk-throughs; §0.8 `rebased_boundaries` |
| C5 | `mode = REBASE_TO_NEXT_ROUND` reopens the SAME state at the IDENTICAL `boundary_time` with ZERO transition energy across the five continuing states | PASS | §1a step (2) state set; §1a NOTE |
| C6 | `ApplyMinerStateTransition` remains the SOLE owner of intervals for an ACTUAL state change; no third writer | PASS | §0.3/§0.9; §1a NOTE; ownership table §3 |
| C7 | `t_ACTIVE_HASHING = t_hash` unaffected; `HashWorkEvent` adds zero duration | PASS | §1a NOTE; §0.7b; I19 formal statement |
| C8 | I19, the energy model §3, and this audit match the actual pseudocode (frozen TV96 naming is historical, superseded on paper by TV102) | PASS | I19 (M4/L5); energy-model §3 (M4); §5 note |
| C9 | A1 baseline unchanged; any energy change attributable only to reduced active power-time; no new consensus feature | PASS | §5; I19 scope note; energy-model §3; A1 = 8.420833333 kWh |

---

## Result

**Result: RESIDENCY SINGLE-OWNER BOUNDARY AUDIT (Stage 1M): PASS** — Stage-1M correction M4 unifies EVERY
boundary residency close/reopen under ONE procedure, `SettleResidencyBoundary` (§1a), with two modes:
`REBASE_TO_NEXT_ROUND` closes each open prior-round interval at `boundary_time =
prior_state.round_terminal_time` (energy → the old `RoundID`) and reopens the SAME state at the IDENTICAL
`boundary_time` for the new round with ZERO transition energy across the five continuing states
`LOW_POWER_LISTEN`/`REGISTERED`/`RESERVE`/`OFFLINE`/`DISQUALIFIED`, while `FINAL_RUN_END` closes every open
interval at the run horizon `T` with NO reopen; the procedure is idempotent via a deterministic `boundary_id`
(`(prior_RoundID, RoundID_current)` or `(RoundID_current, RUN_END)`) recorded in the per-run
`rebased_boundaries` set, so a repeat returns `settle_noop` and a replayed/retried `RoundInitialise` (§1) or
re-entered `RoundAbort` (§20) never double-closes or double-attributes an interval; `CloseRoundAssignments`
(§17a) performs NO competing residency/energy finalisation — its former in-line `finalise state durations
and energy to the EXACT closure time` line is REMOVED and it records `round_terminal_time` ONLY — and
`RoundAbort` (§20) replaces its former in-line `finalise energy_ledger` step with the `FINAL_RUN_END` call
placed before the I5/I6/I7 accounting asserts, while `ApplyMinerStateTransition` (§0.9) remains the sole
residency owner for ACTUAL state changes; the idle interval between a round's closure and the next round's
`StartWake` (or the run horizon) is thus counted EXACTLY ONCE (I19 amended for the single idempotent
boundary owner), the durations reconcile with I5 and the energy-model §3 boundary-settle paragraph, and the
A1 baseline (`8.420833333 kWh`) is unchanged — the settle changes only how time is split, never the total —
adding no new consensus feature.
