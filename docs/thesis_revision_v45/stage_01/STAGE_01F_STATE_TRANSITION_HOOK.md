# Stage 1F — Central Miner-State Transition Hook (F6)

Specifies and audits `ApplyMinerStateTransition`, the single procedure through which EVERY
miner-state change passes. Binds to `STAGE_01_PROTOCOL_PSEUDOCODE.md` §0.3, §0.9 and
`STAGE_01_MINER_STATE_MACHINE.md` §1.7.

## 1. Contract

`ApplyMinerStateTransition(MinerID, old_state, new_state, event_time, reason, assignment_ref,
candidate_ref)` atomically:

1. suppresses a duplicate transition for the same `(MinerID, event_time, old_state→new_state)`;
2. closes the OLD residency interval at `event_time` (no-op for the registration sentinel
   `old_state = NONE`);
3. opens the NEW residency interval at `event_time` (begins `P_new` accrual);
4. records one-shot `E_transition`/`E_coordination` for the crossing (never folded into `P·t`,
   never double-counted);
5. updates assignment status where the edge specifies one (e.g. `WAKING→ACTIVE_HASHING` activates
   PENDING/PAUSED→CURRENT);
6. sets `miner_state(MinerID) = new_state`;
7. recomputes `H_honest`, `H_adversarial`, `H_active = H_honest + H_adversarial` from the
   post-transition `ACTIVE_HASHING` census and sets `q_adv` (or NA) — **I17 exactly, at this boundary**;
8. records a transition audit entry;
9. SCHEDULEs (does not inline) `SecurityFloorEvaluate` for the boundary.

## 2. Sole-writer property

| # | Property | Result |
|--:|----------|--------|
| 1 | No procedure mutates `miner_state` outside the hook | **PASS** — `grep` shows zero `TRANSITION miner_state` in any procedure (only the §0.3 rule text names the retired keyword); every change is a `CALL ApplyMinerStateTransition` (12 sites) |
| 2 | Every required edge routes through the hook | **PASS** — covered edges include `∅→REGISTERED` (T1), `REGISTERED→RESERVE` (T2), `*→WAKING` (via `StartWake`, T3/T4/T10/T30), `WAKING→ACTIVE_HASHING` (T5), `WAKING→OFFLINE` (T12), `ACTIVE_HASHING→EXHAUSTED_PENDING` (T7), `→LOW_POWER_LISTEN` (T8/T26/T27/T28/T29), `EXHAUSTED_PENDING→LOW_POWER_LISTEN` (T8), round-closure edges |
| 3 | I17 recomputed at every ACTIVE_HASHING boundary | **PASS** — step (7) runs on every call; entries/exits of `ACTIVE_HASHING` (T5 in; T7/T11/T18/T26/T27/T28/T29 out) all pass through it (TV34) |
| 4 | Legal-transition precondition | **PASS** — the hook asserts `(old_state→new_state)` is legal per miner-SM §3; this surfaced and fixed the illegal `WAKING→LOW_POWER_LISTEN` closure edge (now `WAKING→OFFLINE`, T12) |
| 5 | Duplicate transitions suppressed | **PASS** — step (1) makes a repeated same-event call a no-op, so concurrent handlers referencing one transition are safe |
| 6 | The hook never samples a hash rate | **PASS** — it computes sums from the census deterministically; the adversarial active-census draw stays solely in `ActiveHashRateUpdate` (sampling summary item 2) |

## 3. Interaction with wake and security-floor

- `StartWake` uses the hook for `→WAKING`; `WakeCompleteEvent` uses it for `WAKING→ACTIVE_HASHING`
  or `WAKING→OFFLINE`. Wake residency is therefore bounded by two hook calls at the wake's start and
  completion timestamps (F5/F6 compose).
- Every hook call SCHEDULEs `SecurityFloorEvaluate` (never inlines it), so a boundary that drops
  `H_active`/`H_honest` below the floor is evaluated as a discrete event under the F8 priority order
  (priority 5), not synchronously inside the transition.

## 4. Latent-defect fix surfaced by F6

Routing all transitions through the legality-checked hook exposed the Stage-1E
`CloseRoundAssignments` WAKING case, which used the prohibited `WAKING → LOW_POWER_LISTEN` edge. It is
corrected to `WAKING → OFFLINE` (T12) in both `CloseRoundAssignments` and `CloseTemplateAssignments`;
the miner rejoins next round via T17. This is a legality correction, not a new feature.

## Result

**STATE-TRANSITION HOOK (F6): PASS.** `ApplyMinerStateTransition` is the sole writer of
`miner_state`; every transition routes through it; I17 is recomputed at every `ACTIVE_HASHING`
boundary; illegal edges are rejected by its precondition. (Exercised by TV34, TV37.)
