# Stage 1W — Rollback Envelope Audit (W1)

## 1. Scope

This audit documents correction **W1** of the Stage-1W revision to the PoCol formal
specification (the idle policy within PoCol): *remove all free / placeholder rollback
envelopes*. The correction concerns the two ordinary assignment-setup rollback procedures,
`RollbackParticipantSetup` and `RollbackTemplateRefreshSetup`, and the setup-transaction
records they consume (`participant_setup_txn` in `PrepareParticipantsForNewRound`,
`refresh_setup_txn` in `TemplateRefresh`).

The audit is descriptive and documentation-only. It reads the current specification text and
records the state of the corrected contract; it modifies no protocol file. Every claim below is
grounded in the current text of

- `STAGE_01_PROTOCOL_PSEUDOCODE.md` (the normative pseudocode; line references re-established by
  grep against the current file, not inherited from an earlier revision),

with traceability confirmed against `STAGE_01_ROUND_STATE_MACHINE.md`,
`STAGE_01_TERMINOLOGY.md`, `STAGE_01_INVARIANT_CATALOGUE.md`, and
`STAGE_01_TRACEABILITY_MATRIX.csv`.

The A1 energy-accounting baseline (`8.420833333 kWh`,
`STAGE_01_ENERGY_MODEL_SPECIFICATION.md` line 29) is unaffected by this correction and is
preserved unchanged; W1 is a control-flow / event-identity correction with no energy semantics.

## 2. The defect (pre-W1 / V8 state)

In the V8 formulation the executable setup rollbacks existed as named procedures, but the
transition they performed to depart a participant left `WAKING` referred to its transition
envelope through an angle-bracket **placeholder** of the form `<the setup dispatch_envelope>`
(and, for the refresh path, `<the refresh dispatch_envelope>`). Two distinct faults followed
from this:

1. **The rollback never *received* the envelope it named.** The placeholder was descriptive
   prose standing in for an object that was not an input to the rollback procedure and was not
   stored on the setup transaction. There was therefore no in-scope, well-typed value the
   rollback could actually pass to `ApplyMinerStateTransition`; the transition identity was left
   to be reconstructed from an ambient or undeclared source.

2. **No five-field envelope guarantee.** `ApplyMinerStateTransition` (§0.9) builds its immutable
   `TransitionEventID` *exclusively* from the one `transition_envelope` object, whose five
   identity fields are `{ envelope_namespace, event_time, delta_cycle, event_seq, hook_id }`
   (`STAGE_01_PROTOCOL_PSEUDOCODE.md` line 970). A placeholder cannot supply those five fields,
   so a rollback transition driven by it would produce a non-reproducible or malformed
   `TransitionEventID` — precisely the threat recorded against requirement R160 (see §6).

The correction W1 replaces the placeholder with a real, immutable, complete envelope stored on
the setup transaction at the moment of its creation, and threaded — unchanged — into the
rollback transition.

## 3. The corrected contract (post-W1)

W1 establishes a single, executable contract in four parts.

**(a) The setup transaction carries an immutable `rollback_envelope`, fixed at creation.**
Both entry points construct their setup-transaction record with the `rollback_envelope` field
bound, at construction time, to that entry point's *own* `dispatch_envelope`. In
`PrepareParticipantsForNewRound` (`STAGE_01_PROTOCOL_PSEUDOCODE.md` lines 1533–1534):

```
    SET participant_setup_txn <- setup_transaction(rollback_envelope = dispatch_envelope,
          wakes = empty, created_assignments = empty, prior_states = empty)   # W1/V8
```

and in `TemplateRefresh` (lines 4626–4627):

```
    SET refresh_setup_txn <- setup_transaction(rollback_envelope = dispatch_envelope,
          wakes = empty, created_assignments = empty, prior_states = empty)   # W1/W3
```

Each entry point declares `dispatch_envelope` as an explicit input —
`PrepareParticipantsForNewRound` at line 1520 (`INPUTS: RoundContext, dispatch_envelope
# L1: this entry point's own dispatch envelope`) and `TemplateRefresh` at line 4602
(`INPUTS: RoundContext, dispatch_envelope`) — so the value bound into `rollback_envelope` is
in scope and well-typed, not ambient. The accompanying W1 comment at lines 1530–1532 states the
intent: the record carries "an IMMUTABLE rollback_envelope (this entry point's own
dispatch_envelope: { envelope_namespace, event_time, delta_cycle, event_seq, hook_id })" so that
an `assignment_phase_failed` "can be ROLLED BACK executably with a COMPLETE transition_envelope
(no placeholder)". The matching comment for the refresh path is at lines 4622–4623.

**(b) The complete transition envelope is five fields.** The envelope the rollback transitions
with is the same complete transition-envelope object required everywhere by the central hook.
`ApplyMinerStateTransition` (§0.9) receives "ONE object, `transition_envelope`, carrying the
COMPLETE dispatch identity (§0.2)" defined at line 970 as

```
    transition_envelope = { envelope_namespace, event_time, delta_cycle, event_seq, hook_id }
```

and destructures exactly those five fields (lines 1006–1010) as the sole identity source for the
`TransitionEventID` and the malformed-envelope guard. The `rollback_envelope` field is therefore
type-compatible with `transition_envelope` by construction.

**(c) The rollback procedures transition with the stored envelope.** Neither rollback invents,
hand-stamps, or reads an ambient envelope. `RollbackParticipantSetup` departs any residual
`WAKING` participant to `OFFLINE` via the legal T12 edge using the transaction's stored envelope
(lines 1653–1655):

```
        SET tr <- CALL ApplyMinerStateTransition(m, WAKING, OFFLINE,
               transition_envelope = setup_txn.rollback_envelope, reason = participant_setup_rolled_back,   # W1: complete envelope; T12
               assignment_ref = null, candidate_id = null, propagation_id = null)   # F6
```

`RollbackTemplateRefreshSetup` performs the identical discipline (lines 1684–1686):

```
        SET tr <- CALL ApplyMinerStateTransition(m, WAKING, OFFLINE,
               transition_envelope = setup_txn.rollback_envelope, reason = template_refresh_rolled_back,   # W1: complete envelope; T12
               assignment_ref = null, candidate_id = null, propagation_id = null)   # F6
```

**(d) The envelope is a declared input of the shape carrying `rollback_envelope`.** Each
rollback names `setup_txn` as an input whose shape explicitly includes `rollback_envelope`.
`RollbackParticipantSetup` (line 1638):

```
  INPUTS: RoundContext, setup_txn   # W1: { rollback_envelope, wakes: [WakeEventRef], created_assignments: [AssignmentID], prior_states: {MinerID -> state} }
```

with its precondition (lines 1641–1642) restating that "setup_txn.rollback_envelope is the
caller's COMPLETE dispatch envelope { envelope_namespace, event_time, delta_cycle, event_seq,
hook_id }". `RollbackTemplateRefreshSetup` (line 1674) takes "the same shape as
RollbackParticipantSetup's setup_txn (with rollback_envelope)", its precondition (line 1676)
confirming "setup_txn.rollback_envelope is complete". The closing NOTE of
`RollbackParticipantSetup` (lines 1667–1671) records that the transition uses "the txn's
COMPLETE rollback_envelope (never an illegal WAKING->prior edge and never a placeholder
envelope)".

## 4. The two rollback procedures — envelope source and the five fields

| Rollback procedure | Setup transaction consumed | `rollback_envelope` set at creation to | Where set (pseudocode) | Transition-envelope passed to `ApplyMinerStateTransition` | Five envelope fields carried |
|---|---|---|---|---|---|
| `RollbackParticipantSetup` | `participant_setup_txn` (built in `PrepareParticipantsForNewRound`) | that entry point's own `dispatch_envelope` | line 1533 (`setup_transaction(rollback_envelope = dispatch_envelope, …)`) | `transition_envelope = setup_txn.rollback_envelope` (line 1654) | `envelope_namespace, event_time, delta_cycle, event_seq, hook_id` (§0.9 line 970; destructured 1006–1010) |
| `RollbackTemplateRefreshSetup` | `refresh_setup_txn` (built in `TemplateRefresh`) | that entry point's own `dispatch_envelope` | line 4626 (`setup_transaction(rollback_envelope = dispatch_envelope, …)`) | `transition_envelope = setup_txn.rollback_envelope` (line 1685) | `envelope_namespace, event_time, delta_cycle, event_seq, hook_id` (§0.9 line 970; destructured 1006–1010) |

Both rows resolve to the same complete five-field object; the two procedures differ only in the
transaction they consume and in the `reason` they record (`participant_setup_rolled_back` versus
`template_refresh_rolled_back`). In each case the envelope is immutable — the setup transaction
binds it once at construction (§3(a)) and neither the enclosing loop nor the rollback rebinds it —
and the departure edge is the legal T12 `WAKING -> OFFLINE` edge (W2), never an illegal
`WAKING -> REGISTERED/RESERVE/LOW_POWER_LISTEN` edge.

## 5. Grep evidence that no placeholder remains

The following searches were run against the current specification text. No angle-bracket
placeholder for a rollback envelope survives.

- Exact placeholder strings, whole stage directory:
  `grep -n "the setup dispatch_envelope|the refresh dispatch_envelope"` over
  `STAGE_01/` — **no matches**.
- Angle-bracket placeholder over `dispatch_envelope`, whole stage directory:
  `grep -n "<the [^>]*dispatch_envelope[^>]*>"` over `STAGE_01/` — **no matches**.
- Envelope-shaped angle-bracket placeholders in the pseudocode:
  `grep -n "<(setup|refresh|dispatch|the setup|the refresh)[^>]*>"` over
  `STAGE_01_PROTOCOL_PSEUDOCODE.md` — **no matches**.

Where the tokens "placeholder" or "`<the`" still appear in the pseudocode, they occur only in
**negative** annotations that assert the placeholder's absence — never as a live envelope value.
The three surviving occurrences are:

- line 1532 — "COMPLETE transition_envelope (no placeholder)";
- line 1650 — "NEVER a placeholder/ambient envelope";
- line 1669 — "never a placeholder envelope".

Correspondingly, the two references to `rollback_envelope` as an actual transition envelope
resolve to the stored transaction field (`transition_envelope = setup_txn.rollback_envelope`,
lines 1654 and 1685), and the two `setup_transaction(...)` initialisers bind it to
`dispatch_envelope` (lines 1533 and 4626). No ambient read of
`EQ.current_event_time / current_delta_cycle / current_event_seq` and no undeclared identity is
used on either rollback path.

## 6. Traceability

| Anchor | Location | What it establishes for W1 |
|---|---|---|
| Round state machine §3.10a addendum, **W1** | `STAGE_01_ROUND_STATE_MACHINE.md` lines 633–639 | "**W1 (no free / placeholder rollback envelope).**" The setup transaction carries an IMMUTABLE `rollback_envelope` set at creation to the setup's own dispatch envelope `{ envelope_namespace, event_time, delta_cycle, event_seq, hook_id }`; both rollbacks transition with `transition_envelope = setup_txn.rollback_envelope` — "no angle-bracket placeholder, ambient envelope, or undeclared identity remains." (V8, the executable-rollback precursor, is at lines 623–627.) |
| Terminology addendum, **`rollback_envelope` (W1)** | `STAGE_01_TERMINOLOGY.md` lines 827–832 | Defines `rollback_envelope` as "An IMMUTABLE field of the setup transaction (`participant_setup_txn` / `refresh_setup_txn`), set at creation to the setup's own dispatch envelope `{ envelope_namespace, event_time, delta_cycle, event_seq, hook_id }`"; "Every rollback transition uses it as its `transition_envelope`; no placeholder, ambient, or undeclared envelope is used." |
| Invariant catalogue, **I16 — W1/W2** | `STAGE_01_INVARIANT_CATALOGUE.md` I16 (heading line 284); W1/W2 clause lines 322–327 | "**W1/W2 (legal setup rollback):** an ordinary-setup rollback (`RollbackParticipantSetup` / `RollbackTemplateRefreshSetup`) transitions with the setup transaction's IMMUTABLE `rollback_envelope` (a complete `{ envelope_namespace, event_time, delta_cycle, event_seq, hook_id }`) and departs any `WAKING` participant to `OFFLINE` via the LEGAL `T12` edge ONLY — no placeholder envelope …". Confirms the five-field completeness (W1) jointly with the legal-edge discipline (W2). |
| Traceability matrix, **R160** | `STAGE_01_TRACEABILITY_MATRIX.csv` line 161 | Requirement R160: "Remove all free/placeholder rollback envelopes (W1) …" — state/event `RollbackParticipantSetup; RollbackTemplateRefreshSetup; PrepareParticipantsForNewRound; TemplateRefresh`; invariant `I16; I3`; threat "a rollback transition with a free/placeholder or ambient envelope producing a non-reproducible or malformed TransitionEventID"; status **SPECIFIED**. |

The four anchors are mutually consistent and consistent with the pseudocode read in §§3–5: the
same immutable, five-field `rollback_envelope`, set at transaction creation to the entry point's
own dispatch envelope and threaded unchanged into both rollback transitions, with the placeholder
provably absent from the current text.
