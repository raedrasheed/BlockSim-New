# Stage 1X — Energy / Residency / Census Rollback Reconciliation Audit (X8)

## 1. Scope

This audit documents correction **X8** of the Stage-1X revision to the PoCol formal
specification (the idle policy within PoCol): *reconcile rollback with the
energy / residency / census accounting*. The correction concerns every rollback edge that
departs a still-`WAKING` miner to `OFFLINE`, and the single hook through which that departure
runs.

The concrete X8 claim, verbatim from the round state machine
(`STAGE_01_ROUND_STATE_MACHINE.md` §3.10b, lines 723–726):

> **X8 (rollback reconciled with energy/census accounting).** Each rollback `WAKING -> OFFLINE`
> runs through `ApplyMinerStateTransition` (F6), which closes the `WAKING` residency at the
> rollback `event_time`, charges `E_transition`/`E_coordination` exactly once, opens `OFFLINE`
> residency, and (T12) makes no census change (the miner never entered `H_active`) — so no
> `WAKING` residency stays open until horizon `T`.

The audit is descriptive and documentation-only. It reads the current specification text and
records the state of the corrected contract; it modifies no protocol file. Line references were
re-established by grep against the current files, not inherited from an earlier revision. Every
claim below is grounded in the current text of

- `STAGE_01_PROTOCOL_PSEUDOCODE.md` (the normative pseudocode — source of truth),

with traceability confirmed against `STAGE_01_ROUND_STATE_MACHINE.md` (§3.10b),
`STAGE_01_INVARIANT_CATALOGUE.md` (I16, I19, I5–I7, I17), `STAGE_01_MINER_STATE_MACHINE.md`
(edge T12), `STAGE_01_ENERGY_MODEL_SPECIFICATION.md`, `STAGE_01_TERMINOLOGY.md`, and
`STAGE_01_TRACEABILITY_MATRIX.csv` (TV208, TV209).

The A1 energy-accounting baseline (`8.420833333 kWh`,
`STAGE_01_ENERGY_MODEL_SPECIFICATION.md` line 29) is preserved exactly and is unaffected by
this correction; X8 is a bookkeeping-reconciliation correction with no change to any energy
figure (§8).

## 2. The single residency / energy / census owner (F6)

Every miner-state change — including every rollback `WAKING -> OFFLINE` — runs through exactly
one hook, `ApplyMinerStateTransition` (`STAGE_01_PROTOCOL_PSEUDOCODE.md`, `PROCEDURE` at line
997). It is declared the sole owner of state-residency time and the sole *producer* of the
security census, calling the sole census writer rather than writing the maps itself
(lines 1033–1037):

> `# F6: the SOLE owner of every miner-state change, and (Q4/R5) a PRODUCER of the security census — it`
> `#     COMPUTES the post-transition census and CALLS the sole writer CommitSecurityCensus (§0.8a) with`
> `#     census_source = MINER_STATE_TRANSITION. It is NOT itself a direct writer of security_census_dirty /`
> `#     latest_security_census (R5: only CommitSecurityCensus writes the two maps) ...`

and (lines 1123–1125):

> `NOTE: This is the ONLY writer of miner_state (0.3) and the SOLE owner of state-residency time`
> `      t_<state> incl t_ACTIVE_HASHING = t_hash (H7). It recomputes H_active/H_honest/H_adversarial and`
> `      re-checks I17 at EVERY ACTIVE_HASHING boundary; it never SAMPLES a hash rate.`

The atomic apply (step 5, lines 1073–1100) performs, in one atomic body, the four accounting
actions X8 depends on. Residency boundary (step 5a, lines 1076–1078):

> `# (5a) residency boundary: close OLD interval, open NEW (I5/I6/I19/K3 continuity at round boundaries).`
> `IF old_state != NONE: CLOSE residency(MinerID, old_state) at event_time   # accrues P_old * (event_time - last_boundary)`
> `OPEN  residency(MinerID, new_state) at event_time`

One-shot boundary energy (step 5b, lines 1079–1080):

> `# (5b) one-shot boundary energy (E_transition/E_coordination per edge). I6; never folded into P*t.`
> `RECORD E_transition/E_coordination for (old_state -> new_state)`

Deterministic census recompute from the post-transition `ACTIVE_HASHING` set (step 5e,
lines 1085–1090):

> `SET H_honest(event_time)      <- SUM over honest miners in ACTIVE_HASHING of modeled hash rate`
> `SET H_adversarial(event_time) <- SUM over adversarial miners in ACTIVE_HASHING of modeled hash rate`
> `SET H_active(event_time)      <- H_honest(event_time) + H_adversarial(event_time)   # I17 EXACT`

Census publication *only when the ACTIVE_HASHING census actually changed* (step 5f,
lines 1096–1100):

> `IF this transition changed the ACTIVE_HASHING census:`
> `  CALL CommitSecurityCensus(RoundContext, event_time, ... census_source = MINER_STATE_TRANSITION)`

Two guards make "exactly once" structural. The **replay guard** (step 2, lines 1055–1058)
suppresses an exact-id replay *without reading old_state and without charging energy*:

> `# (2) K5 REPLAY GUARD — check the APPLIED registry. Suppress ONLY an exact-same-id replay of an`
> `#     ALREADY-APPLIED transition; do NOT read old_state and do NOT charge energy.`
> `IF TransitionEventID in applied_transition_registry:`
> `  RETURN duplicate_suppressed(TransitionEventID) ...`

and the **atomic register-then-apply** (step 5, lines 1073–1075) enters the id into the applied
registry inside the same atomic body that records the energy, so the one-shot charge and the
registration are inseparable:

> `# (5) K5 ATOMIC APPLY. Register-then-apply in ONE atomic step; the id enters the APPLIED registry ONLY here.`
> `ATOMICALLY:`
> `  ADD TransitionEventID to applied_transition_registry             # K5: only APPLIED transitions are registered`

`CommitSecurityCensus` (`PROCEDURE` at line 937) is the *sole atomic writer* of the two census
maps; producers call it and nothing writes the maps directly (lines 944–946):

> `PRECONDITIONS: ... called ONLY by the census sources below — nothing writes the two maps directly (R5: producers`
> `               CALL this writer; NO producer is itself a direct writer of security_census_dirty/latest_security_census)`

## 3. The three rollback call sites (each departs still-WAKING via T12)

Each of the three rollback procedures departs a still-`WAKING` miner through the **single legal
`WAKING` departure edge T12** by calling `ApplyMinerStateTransition` — never mutating residency,
energy, or census itself.

### 3.1 RollbackRecoveryAssignmentPlan (`PROCEDURE` at line 3695)

This procedure carries the explicit X8 rationale in its own comment (lines 3705–3709):

> `# (2) X1/X2/X8: for every miner still WAKING on its plan-created assignment, depart it to OFFLINE via the LEGAL T12`
> `#   edge, using the EXACT assignment version (never null) and the item's COMPLETE rollback_envelope. ApplyMinerStateTransition`
> `#   (F6/X8) closes the WAKING residency at THIS rollback event_time, charges E_transition/E_coordination ONCE, opens`
> `#   OFFLINE residency, and (T12) makes NO census change (the miner never entered H_active) — so no open WAKING`
> `#   residency survives to horizon T, and the complete transition identity is preserved.`

The T12 call (lines 3710–3716):

> `FOR EACH item in rollback_record.items (stable order):`
> `  IF miner_state(item.MinerID) = WAKING AND item.AssignmentID is item.MinerID's bound live head:`
> `    SET tr <- CALL ApplyMinerStateTransition(item.MinerID, WAKING, OFFLINE,`
> `           transition_envelope = item.rollback_envelope, reason = cancellation,           # X2/X7: complete envelope; legal T12`
> `           assignment_ref = assignment_version_ref(item.AssignmentID, item.assignment_version),   # X2: EXACT version, never null`
> `           candidate_id = null, propagation_id = null)   # F6/X8`
> `    IF tr is transition_applied(teid): SET rolled_to_offline <- true`

The closing NOTE restates the X8 guarantee (lines 3735–3737):

> `The T12 departure runs`
> `through ApplyMinerStateTransition, so WAKING residency closes at the rollback time (not at horizon T) and`
> `transition energy is charged exactly once (X8).`

### 3.2 RollbackParticipantSetup (`PROCEDURE` at line 1678)

The X2/W2 comment (lines 1690–1693) and the T12 call (lines 1694–1700):

> `# X2/W2: a participant left WAKING is departed to OFFLINE via the LEGAL T12 edge (the ONLY legal WAKING departure`
> `#   besides T5/T21) using the txn's COMPLETE rollback_envelope (W1) AND the EXACT assignment version recorded in`
> `#   setup_txn.assignment_by_miner[m] ...`
> `FOR EACH (MinerID m, (aid, ver)) in setup_txn.assignment_by_miner (stable order by MinerID):`
> `  IF miner_state(m) = WAKING:`
> `    SET tr <- CALL ApplyMinerStateTransition(m, WAKING, OFFLINE,`
> `           transition_envelope = setup_txn.rollback_envelope, reason = cancellation,          # W1: complete envelope; X7 canonical; T12`
> `           assignment_ref = assignment_version_ref(aid, ver),                                 # X2: EXACT version, never null`
> `           candidate_id = null, propagation_id = null)   # F6`
> `    IF tr is transition_applied(teid): SET rolled_to_offline <- true    # W2/W8: a WAKING participant was legally departed`

### 3.3 RollbackTemplateRefreshSetup (`PROCEDURE` at line 1718)

Identical discipline (comment line 1727; T12 call lines 1728–1734):

> `# X2: depart each still-WAKING miner via T12 using the EXACT version from assignment_by_miner and the complete envelope.`
> `FOR EACH (MinerID m, (aid, ver)) in setup_txn.assignment_by_miner (stable order by MinerID):`
> `  IF miner_state(m) = WAKING:`
> `    SET tr <- CALL ApplyMinerStateTransition(m, WAKING, OFFLINE,`
> `           transition_envelope = setup_txn.rollback_envelope, reason = cancellation,          # W1: complete envelope; X7 canonical; T12`
> `           assignment_ref = assignment_version_ref(aid, ver),                                 # X2: EXACT version, never null`
> `           candidate_id = null, propagation_id = null)   # F6`
> `    IF tr is transition_applied(teid): SET rolled_to_offline <- true`

### 3.4 The T12 edge definition (miner state machine)

The edge these three call sites use is defined once, in
`STAGE_01_MINER_STATE_MACHINE.md` (row T12, line 530):

> `| T12 | WAKING | Departure / WakeDeadlineExpiry / ValidationAbort | ... | Release bound range; stop wake accrual | OFFLINE | End P_wake; begin P_offline residency | No census change (never entered H_active(t)) | Attributable violation instead → DISQUALIFIED (T21) |`

The energy-accounting effect of T12 is *End `P_wake`; begin `P_offline` residency*; the
security-accounting effect is *No census change (never entered `H_active(t)`)*.

## 4. Claim-by-claim verification

### Claim 1 — the WAKING residency is CLOSED at the rollback event_time (not left open to T)

**PASS.** Each rollback departs the miner only through `ApplyMinerStateTransition` (§3.1–3.3),
whose step 5a (line 1077) executes `CLOSE residency(MinerID, old_state) at event_time` with
`old_state = WAKING`, accruing `P_wake * (event_time − last_boundary)`, and step 5b opens the
new interval at the same `event_time`. `event_time` is the rollback's own dispatch time,
destructured from the passed `rollback_envelope` (step 0, lines 1040–1044). Because the hook is
the SOLE residency owner (lines 1123–1125; I19), no `WAKING` interval can be closed anywhere
else or at any other time. The X8 comment in `RollbackRecoveryAssignmentPlan` (line 3707) states
this directly: *"closes the WAKING residency at THIS rollback event_time"*.

### Claim 2 — the transition energy is charged EXACTLY once (no double charge, no omission)

**PASS.** The one-shot boundary energy for the `(WAKING -> OFFLINE)` edge is recorded once by
step 5b (line 1080, `RECORD E_transition/E_coordination for (old_state -> new_state)`), inside
the atomic body that registers the `TransitionEventID` exactly once (step 5, lines 1073–1075).
*No omission*: the charge is unconditional within a successful apply, and each rollback marks
`rolled_to_offline` only on `transition_applied` (lines 3716 / 1700 / 1734). *No double charge*:
the replay guard (step 2, line 1056) suppresses any exact-id replay *without charging energy*,
and each call site is itself guarded by `IF miner_state(...) = WAKING` so a re-run over an
already-departed miner does not re-enter the edge. The X8 requirement text — round-SM line 724,
I16 line 346, pseudocode line 3707 — all state *"charges E_transition/E_coordination exactly
once"*. Per the energy model (`STAGE_01_ENERGY_MODEL_SPECIFICATION.md` lines 103–104), these are
the lump event terms of the state-complete sum (E-1, lines 45–48): `E_transition,i`
(mode-switch / spin-down) and `E_coordination,i` (the `cancellation` coordination), each charged
"as applicable" to the departure edge.

### Claim 3 — the departure opens an OFFLINE residency and adds NO H_active

**PASS.** Step 5a opens `residency(MinerID, OFFLINE)` at `event_time` (line 1078). The miner was
only `WAKING` and never `ACTIVE_HASHING`; per the canonical state-to-power mapping
(`STAGE_01_ENERGY_MODEL_SPECIFICATION.md` §1.0, lines 67–76) neither `WAKING` (`P_wake`) nor
`OFFLINE` (`P_offline`) contributes to `H_active(t)` — only `ACTIVE_HASHING` does. Step 5e
(lines 1086–1088) recomputes `H_active` as the sum over the `ACTIVE_HASHING` set, which this
edge does not touch, so the recomputed value is unchanged (no positive delta added). This is
exactly the T12 security-accounting effect (state-machine line 530): *"No census change (never
entered `H_active(t)`)"*.

### Claim 4 — census updated ONLY via CommitSecurityCensus, ONLY on ACTIVE_HASHING membership change

**PASS.** `CommitSecurityCensus` is the sole atomic writer of `security_census_dirty` /
`latest_security_census`; nothing writes the maps directly (lines 937, 944–946; R5). The hook
reaches that writer only through the step-5f guard (line 1096): *"IF this transition changed the
ACTIVE_HASHING census: CALL CommitSecurityCensus(...)"*. A `WAKING -> OFFLINE` rollback changes
no `ACTIVE_HASHING` membership (Claim 3), so the guard is false and no census commit is issued
for the edge; `H_active`, `H_honest`, `H_adversarial`, and `q_adv` are therefore unperturbed by
the rollback. The rollback procedures themselves contain no census write — they own only wake
cancellation, the T12 hook call, head closure, and ledger restoration.

### Claim 5 — after any rollback, NO open WAKING residency remains until horizon T

**PASS.** Two independent mechanisms enforce this. (a) The hook closes the `WAKING` interval at
the rollback `event_time` (Claim 1). (b) Each rollback refuses to report success while any
affected miner is still `WAKING`: `RollbackRecoveryAssignmentPlan` (lines 3724–3728) returns
`rollback_failed(reason = residual_partial_assignment)` if *"any item.MinerID remains WAKING on
a plan-created head"*; `RollbackParticipantSetup` (lines 1707–1709) and
`RollbackTemplateRefreshSetup` (lines 1740–1741) likewise return `rollback_failed` if *"any m …
remains WAKING"*. This ties directly to the residency single-owner invariant **I19**
(`STAGE_01_INVARIANT_CATALOGUE.md`, header line 445; body lines 447–455): every `t_<state>` is
produced exactly once by the `residency_ledger` owned by `ApplyMinerStateTransition`, opened at
entry and closed at exit. Were a `WAKING` interval left open, I19's `FINAL_RUN_END` settle
(lines 461–462) would close it only at the run horizon `T` — precisely the outcome X8 prevents
by closing it at the rollback time. I16's X8 clause records the same (lines 345–346): *"so no
WAKING residency survives to horizon T"*.

## 5. Why this preserves the A1 baseline (8.420833333 kWh) without altering it

A1 is the *matched continuous-participation control*:
`E_continuous_control = 3031.5 W × 10,000 s = 30,315,000 J = 8.420833333 kWh`
(`STAGE_01_ENERGY_MODEL_SPECIFICATION.md` lines 23–29). It is computed from fixed inputs — the
horizon `T = 10,000 s`, aggregate hash rate `141 TH/s`, and efficiency `21.5 J/TH` — and is
"invariant to how the nonce domain is partitioned" (line 31). It contains no rollback term and
no per-miner residency ledger; a miner's `WAKING -> OFFLINE` rollback touches none of `T`,
`P_active`, hash rate, or efficiency. A1 is therefore numerically independent of X8.

X8 is a bookkeeping-integrity reconciliation for the *idle-policy* side of the comparison, and
it preserves that integrity exactly rather than changing it:

- **I5** (durations partition the horizon; `STAGE_01_INVARIANT_CATALOGUE.md` lines 112–117):
  closing `WAKING` at the rollback time and opening `OFFLINE` at the same instant keeps the
  per-miner timeline gap-free and overlap-free with no `t_other` bucket — a `WAKING` interval
  left open to `T` would over-attribute `t_wake` and violate I5.
- **I6 / I7** (per-miner and network energy sum exactly; lines 125–148): charging the one-shot
  edge energy exactly once (Claim 2) keeps `E_i = Σ_s (P_{i,s}·t_{i,s}) + E_transition,i +
  E_coordination,i + E_verification,i` exact with no residual and no double count.
- **I19** (residency single owner; lines 445–501) explicitly records that this class of
  structural accounting correction "does not change the A1 baseline (`8.420833333 kWh`) — any
  energy change is attributable ONLY to reduced active power-time, never to a change in how time
  is counted" (lines 476–477).

Because X8 only guarantees that the rollback's residency and energy are counted correctly
(closed once, charged once, no spurious `H_active`), it changes *how the idle-policy total is
kept honest*, not the control figure it is compared against. A1 remains exactly
`8.420833333 kWh`.

## 6. Test-vector linkage (TV208, TV209)

`STAGE_01_TRACEABILITY_MATRIX.csv` requirement **R177** (line 178) enumerates the Stage-1X
blocking test vectors mapped to `STAGE_01X_SEMANTIC_TEST_VECTORS` and to invariants
`I1;I3;I5;I7;I10;I16;I18b`. Two are the direct X8 vectors:

- **TV208** — *"a rollback T12 closes the WAKING residency charges one transition energy and
  adds no H_active"*. Covered by Claims 1–4: F6 step 5a closes `WAKING` at `event_time`
  (line 1077); step 5b records the one-shot edge energy once (line 1080) under the replay /
  atomic-registration guards (lines 1056, 1075); the step-5f census guard (line 1096) is not
  satisfied so no `H_active` is added (T12 line 530).
- **TV209** — *"after a full recovery-plan rollback no open WAKING residency remains until
  horizon T"*. Covered by Claim 5:
  `RollbackRecoveryAssignmentPlan` cannot return `rollback_completed` while any affected miner
  remains `WAKING` (lines 3724–3728), and the residency single owner I19 guarantees any open
  `WAKING` interval would otherwise be closed only at `T`.

The named procedures exercised by these vectors (matrix line 178) — `RollbackRecoveryAssignmentPlan`,
`ApplyMinerStateTransition`, `CommitSecurityCensus` — are exactly the procedures audited above.

## 7. Cross-document consistency

| Document | Location | Statement | Consistent |
|---|---|---|---|
| `STAGE_01_PROTOCOL_PSEUDOCODE.md` | `ApplyMinerStateTransition` step 5a/5b/5e/5f (lines 1077–1100) | Single hook closes old / opens new residency at `event_time`, records one-shot `E_transition`/`E_coordination`, recomputes census from `ACTIVE_HASHING`, commits census only on membership change | — |
| `STAGE_01_PROTOCOL_PSEUDOCODE.md` | `RollbackRecoveryAssignmentPlan` (lines 3705–3716, 3735–3737) | T12 via F6; residency closed at rollback time, energy once, no census change; cannot complete while any miner WAKING | ✓ |
| `STAGE_01_PROTOCOL_PSEUDOCODE.md` | `RollbackParticipantSetup` / `RollbackTemplateRefreshSetup` (lines 1694–1700, 1728–1734) | Same T12-via-F6 departure with complete envelope + exact version | ✓ |
| `STAGE_01_ROUND_STATE_MACHINE.md` | §3.10b X8 (lines 723–726) | Rollback `WAKING->OFFLINE` via F6: closes WAKING residency at rollback time, charges `E_transition`/`E_coordination` once, opens OFFLINE, no census change, none survives to `T` | ✓ |
| `STAGE_01_INVARIANT_CATALOGUE.md` | I16 X8 clause (lines 345–346) | Closes WAKING residency at rollback time, charges transition energy once (F6/T12), none survives to `T` | ✓ |
| `STAGE_01_INVARIANT_CATALOGUE.md` | I19 residency single owner (lines 445–501); scope note (lines 476–477) | `ApplyMinerStateTransition` sole residency owner; correction does not change A1 | ✓ |
| `STAGE_01_MINER_STATE_MACHINE.md` | T12 (line 530) | End `P_wake`; begin `P_offline`; No census change (never entered `H_active(t)`) | ✓ |
| `STAGE_01_ENERGY_MODEL_SPECIFICATION.md` | E-1 (lines 45–48); `E_transition`/`E_coordination` (lines 103–104); §1.0 mapping (lines 67–76); A1 (lines 23–29) | State-complete sum; edge lump terms; WAKING/OFFLINE do not contribute to `H_active`; A1 fixed | ✓ |
| `STAGE_01_TERMINOLOGY.md` | Residency single owner (lines 233–236); WAKING (line 57) | `t_<state>` produced once by `residency_ledger` owned by `ApplyMinerStateTransition` | ✓ |
| `STAGE_01_TRACEABILITY_MATRIX.csv` | R177 / TV208, TV209 (line 178) | Blocking vectors for the X8 residency / energy / census reconciliation | ✓ |

The pseudocode, round-SM §3.10b X8, invariant I16 (with the residency/energy invariants I19,
I5–I7, I17), the T12 edge, the energy model, and the traceability vectors are mutually
consistent: one hook (F6) is the sole owner of residency and the sole producer of census; T12 is
the single legal `WAKING` departure; a rollback closes `WAKING` at its own `event_time`, charges
the edge energy once, opens `OFFLINE`, and perturbs no `H_active`; and no open `WAKING` residency
survives to horizon `T`.

## 8. Result

**PASS — X8 verified.** Every rollback `WAKING -> OFFLINE` runs through the single owner
`ApplyMinerStateTransition` (F6/T12): the `WAKING` residency is closed at the rollback
`event_time`, `E_transition`/`E_coordination` is charged exactly once, an `OFFLINE` residency is
opened with no `H_active` added, the census changes only via `CommitSecurityCensus` and only on
an `ACTIVE_HASHING` membership change (which this edge is not), and no open `WAKING` residency
survives to horizon `T` (I19) — preserving the energy-accounting integrity behind the A1 baseline
of `8.420833333 kWh` without altering that figure.
