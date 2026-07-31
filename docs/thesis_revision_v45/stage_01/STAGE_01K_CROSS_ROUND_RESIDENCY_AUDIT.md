# Stage 1K — Cross-Round Residency Audit (K3)

A structural audit of Stage-1K correction **K3** (cross-round residency continuity) in the **PoCol**
protocol pseudocode (`STAGE_01_PROTOCOL_PSEUDOCODE.md`): an OPEN per-miner residency interval that
PERSISTS across a round boundary is never reset silently. The boundary is a bookkeeping REBASE —
`FinalizeRoundResidency(boundary_time)` (§1a) closes the open interval and attributes its energy to the
OLD round, and `BeginRoundResidency(boundary_time)` (§1a) reopens the SAME state at the IDENTICAL
`boundary_time` for the NEW round, charging NO transition energy because the miner state did not change.
The idle interval between a round's closure and the next round's `StartWake` is therefore counted
EXACTLY ONCE (invariant **I19**, amended for cross-round continuity). This document is documentation
only; it audits wording and control structure, describes only the idle policy within PoCol, introduces
no new consensus feature, and claims **no** security, fairness, energy, or incentive property. The A1
baseline (`8.420833333 kWh`) is unchanged.

---

## 1. The corrected-away problem (an open interval reset at a round boundary)

`RoundInitialise` (§1) resets the PER-ROUND `residency_ledger` fresh every round (I-04). A miner whose
state continues across the boundary — it is `LOW_POWER_LISTEN`, `REGISTERED`, `RESERVE`, `OFFLINE`, or
`DISQUALIFIED` when round `r` closes and is NOT transitioned at the boundary — holds an OPEN residency
interval in round `r`'s ledger. If the new round's fresh ledger simply reopened (or re-zeroed) that
interval WITHOUT a boundary operation, the elapsed time between round `r`'s closure at `boundary_time`
and round `r+1`'s `StartWake` would be **dropped** (never closed in `r`, its energy lost) or
**double-counted** (charged once in `r`'s open interval and again from a fresh open in `r+1`). Either
outcome mis-states `t_<state>` and its energy across the boundary and would break I5/I6.

K3 removes the ambiguity: an OPEN interval NEVER crosses a boundary silently. The §0.8 `residency_ledger`
comment makes this normative — *"an OPEN residency interval is never reset by a round boundary without a
boundary operation … so a state that continues across the boundary is counted exactly once (I19
amended)."*

## 2. Mechanism (close old round, reopen new round, zero transition energy)

The rebase is two paired boundary operations, invoked from the `RoundInitialise` ELSE branch
(§1, subsequent round). Their §1a bodies:

```
# §1, RoundInitialise ELSE branch (subsequent round; prior_state != null):
SET boundary_time <- prior_state.round_terminal_time
CALL FinalizeRoundResidency(prior_state, boundary_time)                       # K3
CALL BeginRoundResidency(this RoundContext, boundary_time,
                         continuing_miner_states = states preserved across the boundary)   # K3

# §1a FinalizeRoundResidency(RoundContext (old round), boundary_time):
#   PRECONDITION: old round reached a terminal state (ROUND_ACCEPTED/ROUND_ABORTED) at boundary_time.
FOR EACH miner m with an OPEN residency interval in this round's residency_ledger (stable MinerID order):
  CLOSE residency(m, miner_state(m)) at boundary_time         # accrues P_state * (boundary_time - last_boundary)
  ATTRIBUTE that interval's energy to the OLD RoundID
                                                              # boundary CLOSE only — no miner_state change, NO E_transition

# §1a BeginRoundResidency(RoundContext (new round), boundary_time, continuing_miner_states):
#   PRECONDITION: FinalizeRoundResidency(boundary_time) has run; new round's residency_ledger initialised.
FOR EACH miner m in {LOW_POWER_LISTEN, REGISTERED, RESERVE, OFFLINE, DISQUALIFIED} whose state
    continues across the boundary (stable MinerID order):
  OPEN residency(m, miner_state(m)) at boundary_time          # same state, same time; continues P_state accrual
  # do NOT charge E_transition/E_coordination: no state change occurred
```

**Sequencing.** `FinalizeRoundResidency` runs FIRST (its output attributed to the OLD `RoundID`);
`BeginRoundResidency` runs SECOND, guarded by the precondition that the finalise already ran and the new
round's ledger is initialised. Both iterate in stable `MinerID` order, so the rebase is deterministic
(G7). `boundary_time = prior_state.round_terminal_time` is a single instant shared by the close and the
reopen, so the two half-intervals meet exactly at `boundary_time` with no gap and no overlap.

**No transition energy.** Neither procedure changes `miner_state`, so neither records
`E_transition`/`E_coordination`. A one-shot boundary energy is charged ONLY for an ACTUAL edge, by
`ApplyMinerStateTransition` (§0.9). The K3 rebase is a pure accounting split of one continuing
occupancy.

## 3. Per-state rebase table (the five continuing states)

Every state that can PERSIST across a round boundary is closed once in the old round and reopened at the
IDENTICAL `boundary_time` in the new round, with zero transition energy. Residency powers per
`STAGE_01_ENERGY_MODEL_SPECIFICATION.md` §1.0.

| Continuing state | Residency power | Old round (`FinalizeRoundResidency`) | New round (`BeginRoundResidency`) | Transition energy at boundary |
|---|---|---|---|---|
| `LOW_POWER_LISTEN` | `P_listen` | CLOSE at `boundary_time`; energy → old `RoundID` | REOPEN same state at `boundary_time` | **0** (no state change) |
| `REGISTERED` | `P_registered` (= `P_listen`) | CLOSE at `boundary_time`; energy → old `RoundID` | REOPEN same state at `boundary_time` | **0** (no state change) |
| `RESERVE` | `P_reserve` (= `P_listen`) | CLOSE at `boundary_time`; energy → old `RoundID` | REOPEN same state at `boundary_time` | **0** (no state change) |
| `OFFLINE` | `P_offline` | CLOSE at `boundary_time`; energy → old `RoundID` | REOPEN same state at `boundary_time` | **0** (no state change) |
| `DISQUALIFIED` | `P_offline` | CLOSE at `boundary_time`; energy → old `RoundID` | REOPEN same state at `boundary_time` | **0** (no state change) |

`ACTIVE_HASHING` is absent by construction: a terminal round (`ROUND_ACCEPTED`/`ROUND_ABORTED`) has no
`ACTIVE_HASHING` miner to continue, so `t_ACTIVE_HASHING = t_hash` (H7) is unaffected by the rebase.
`WAKING` and `EXHAUSTED_PENDING` are likewise not continuing-across-boundary states here.

## 4. Worked accounting example (matching TV85)

Preconditions (TV85): miner `M` is `LOW_POWER_LISTEN` when round `r` closes at `boundary_time = t_b`; it
remains `LOW_POWER_LISTEN` until round `r+1`'s `StartWake` at `t_w > t_b` (a strictly non-zero inter-round
interval). `M`'s open `LOW_POWER_LISTEN` interval was entered at `t_enter < t_b` (during round `r`).

| Step | Actor | Ledger effect on `t_listen` |
|---|---|---|
| Entry `t_enter` (round `r`) | `ApplyMinerStateTransition` | `OPEN residency(LOW_POWER_LISTEN) at t_enter` — no duration yet |
| Boundary `t_b`, close | `FinalizeRoundResidency` (§1a) | `CLOSE residency(LOW_POWER_LISTEN) at t_b` — accrues `P_listen · (t_b − t_enter)` → **round `r`** |
| Boundary `t_b`, reopen | `BeginRoundResidency` (§1a) | `OPEN residency(LOW_POWER_LISTEN) at t_b` for `r+1` — same state, **0** transition energy |
| `StartWake` `t_w` (round `r+1`) | `ApplyMinerStateTransition` | `CLOSE residency(LOW_POWER_LISTEN) at t_w` — accrues `P_listen · (t_w − t_b)` → **round `r+1`** |

The single `P_listen` occupancy spanning `[t_enter, t_w]` is **split at `t_b`** into `(t_b − t_enter)`
attributed to `r` and `(t_w − t_b)` attributed to `r+1`. Their sum is `P_listen · (t_w − t_enter)` — the
one continuing interval, counted **exactly once**, not reset and not duplicated (I19 amended). No
transition energy is charged at `t_b`. Had the fresh `r+1` ledger reopened `M` WITHOUT the finalise, the
`(t_b − t_enter)` energy would have been dropped from `r`; had it reopened from `t_enter` again, the
`[t_enter, t_b]` segment would have been double-counted. K3 does neither. Reqs: **K3**, I19, I5, I6.

## 5. Reconciliation with I5 / I6 (A1 unchanged)

- **I5 (durations reconcile to `T`).** The close-at-`t_b` / reopen-at-`t_b` discipline makes the two
  half-intervals share the instant `t_b` — no gap, no overlap — so `M`'s timeline still partitions and
  `Σ_states t_state,i = T = 10,000 s` over the eight states, with no residual `t_other` bucket. Each
  half-duration is `≥ 0` because `t_b ≥ t_enter` and `t_w ≥ t_b`.
- **I6 (per-miner energies sum exactly).** The continuing occupancy contributes `P_listen · (t_w −
  t_enter)` once, partitioned across two `RoundID`s; the boundary adds **no** `E_transition`/
  `E_coordination` term (no edge), so `E_i = Σ_s (P_{i,s} · t_{i,s}) + E_transition,i + E_coordination,i
  + E_verification,i` holds with exact equality and no residual term. A per-round energy_ledger sees each
  half attributed to its own round; the per-miner sum is unchanged.
- **A1 discipline.** The rebase does not change the A1 baseline: continuous full-participation energy over
  `T = 10,000 s` is **8.420833333 kWh**, UNCHANGED. Any modeled energy change is attributable ONLY to
  reduced active power-time — never to how the boundary counts a continuing idle interval. K3 is a
  structural accounting correction and introduces **no new consensus feature**.

## 6. Ownership boundary (the ONLY sanctioned no-state-change rebase)

`ApplyMinerStateTransition` (§0.9, F6) REMAINS the SOLE owner of `residency_ledger` accounting for every
ACTUAL miner-state change — it opens/closes an interval and charges one-shot boundary energy only when
`miner_state` actually changes. `FinalizeRoundResidency`/`BeginRoundResidency` (§1a) are the ONLY
sanctioned way an OPEN interval crosses a round boundary WITHOUT a state change: they close and reopen the
SAME state at the IDENTICAL `boundary_time` and charge zero transition energy. No third writer of any
`t_<state>` exists; the §1a NOTE fixes the division — *"Only `ApplyMinerStateTransition` opens/closes
intervals for an ACTUAL state change; these two procedures perform the no-state-change round-boundary
rebase, the ONLY sanctioned way an open interval crosses a round boundary."*

## 7. Acceptance-style PASS checklist

| # | Check | Result | Ground |
|---|---|---|---|
| C1 | An OPEN residency interval is never reset at a round boundary without a boundary operation | PASS | §0.8 residency_ledger K3 comment |
| C2 | `FinalizeRoundResidency(boundary_time)` closes every open per-miner interval and attributes energy to the OLD `RoundID` | PASS | §1a `FinalizeRoundResidency` |
| C3 | `BeginRoundResidency(boundary_time)` reopens the SAME state at the IDENTICAL `boundary_time` for the NEW round | PASS | §1a `BeginRoundResidency` |
| C4 | Boundary charges ZERO `E_transition`/`E_coordination` (no state change) | PASS | §1a both bodies; §2 |
| C5 | Covers the five continuing states `LOW_POWER_LISTEN`/`REGISTERED`/`RESERVE`/`OFFLINE`/`DISQUALIFIED` | PASS | §1a `BeginRoundResidency` state set; §3 table |
| C6 | The idle interval across the boundary is counted EXACTLY ONCE | PASS | §4 worked example (split at `t_b`, sum once); I19 amended |
| C7 | Invoked from `RoundInitialise` ELSE branch at `boundary_time = prior_state.round_terminal_time` | PASS | §1 RoundInitialise ELSE branch |
| C8 | `ApplyMinerStateTransition` remains sole owner for ACTUAL state changes; these two are the only no-state-change rebase | PASS | §6; §1a NOTE; §0.3/§0.9 |
| C9 | Reconciles with I5 / I6; A1 baseline unchanged; reduction attributed only to reduced active power-time; no new consensus feature | PASS | §5; I5/I6; I19 amended; A1 = 8.420833333 kWh |

---

## Result

**Result: CROSS-ROUND RESIDENCY AUDIT (Stage 1K): PASS** — an OPEN per-miner residency interval that
persists across a round boundary is rebased, never reset silently: `FinalizeRoundResidency(boundary_time)`
(§1a) closes every open interval and attributes its energy to the OLD `RoundID`, and
`BeginRoundResidency(boundary_time)` (§1a) reopens the SAME state at the IDENTICAL `boundary_time` for the
NEW round with ZERO transition energy, across the five continuing states `LOW_POWER_LISTEN`/`REGISTERED`/
`RESERVE`/`OFFLINE`/`DISQUALIFIED`, invoked from the `RoundInitialise` ELSE branch at
`boundary_time = prior_state.round_terminal_time`; a `LOW_POWER_LISTEN` interval spanning a non-zero
inter-round gap is thus split at `boundary_time` and counted exactly once (TV85, I19 amended), with
`ApplyMinerStateTransition` still the sole residency owner for ACTUAL state changes and these two
procedures the only sanctioned no-state-change round-boundary rebase; the result reconciles with I5/I6,
leaves the A1 baseline (8.420833333 kWh) unchanged with any energy change attributable only to reduced
active power-time, and adds no new consensus feature.
