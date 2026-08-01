# Stage 1W — Miner Rollback Legality Audit (W2)

## 1. Scope

This audit documents correction **W2** of the Stage-1W thesis revision — *"rollback uses only
legal miner-state edges"* — as it applies to the idle policy within PoCol. It certifies that the
executable setup-rollback procedures depart a participant that is left in `WAKING` when a round
setup fails **only** along an edge that appears in the authoritative miner state machine, namely
the `WAKING -> OFFLINE` edge `T12`, and that a rollback which routed any participant to `OFFLINE`
forces a `RoundAbort` rather than a retry from an incompatible state.

Every claim below is grounded in the current text of two authoritative documents in this stage
directory, re-grepped for this audit (line numbers are those of the files as read, not carried
over from earlier stages):

- `STAGE_01_MINER_STATE_MACHINE.md` — the eight-state miner machine and its transition table
  (`§2.6 WAKING`; `§3 Transition table`; `§3.1 Explicitly prohibited (illegal) transitions`);
- `STAGE_01_PROTOCOL_PSEUDOCODE.md` — the executable procedures `PrepareParticipantsForNewRound`,
  `TemplateRefresh`, `RollbackParticipantSetup`, and `RollbackTemplateRefreshSetup`.

This is a documentation-only artifact: it reads the corrected specification and records the
evidence for W2; it modifies no other file. The A1 continuous-control energy baseline of
`8.420833333 kWh` (`STAGE_01_ENERGY_MODEL_SPECIFICATION.md`) is orthogonal to this correction and
is preserved unchanged — W2 concerns miner-state transition legality during rollback and touches
no residency-power or energy-accounting term.

## 2. The defect: illegal `WAKING -> prior` restoration edges

Prior to W2, the V8 executable rollback attempted to *restore* a participant that had been raised
into `WAKING` during a failed setup **back to its captured pre-wake state**. The frozen Stage-1V
lettered artifact `STAGE_01V_SETUP_ROLLBACK_LIVENESS_AUDIT.md` records the pre-correction step
verbatim (its step 4, "Assert no miner left WAKING"):

> `FOR EACH MinerID m in setup_txn.prior_states: IF miner_state(m) = WAKING AND m's bound head was
> rolled back: CALL ApplyMinerStateTransition(m, WAKING, setup_txn.prior_states[m], …, reason =
> participant_setup_rolled_back, …)`
> — `STAGE_01V_SETUP_ROLLBACK_LIVENESS_AUDIT.md`, line 125

and, in prose (its part (c)):

> "Step 4 transitions any such miner from `WAKING` back to its captured `prior_states[m]` through
> `ApplyMinerStateTransition` (F6)."
> — `STAGE_01V_SETUP_ROLLBACK_LIVENESS_AUDIT.md`, lines 277–278

The `prior_states[m]` map records each activated miner's state *before* it was woken. A miner is
raised into `WAKING` only from `REGISTERED` (T3), `RESERVE` (T4), `EXHAUSTED_PENDING` (T9), or
`LOW_POWER_LISTEN` (T10/T30). Consequently, "restoring `WAKING` to `prior_states[m]`" resolves at
runtime to one of the edges:

- `WAKING -> REGISTERED` (for a participant enlisted from `REGISTERED`),
- `WAKING -> RESERVE` (for a participant enlisted from `RESERVE`),
- `WAKING -> LOW_POWER_LISTEN` (for a participant enlisted from `LOW_POWER_LISTEN`).

**None of these three edges exists in the miner state machine.** The only `WAKING` departures the
machine admits are `T5`, `T12`, and `T21` (§3 below). The V8 rollback therefore instructed the
single sanctioned transition hook `ApplyMinerStateTransition` to apply an edge absent from the
authoritative transition table — the exact class of defect that requirement **R161** names ("a
rollback invoking a miner-state edge absent from the authoritative miner transition table",
`STAGE_01_TRACEABILITY_MATRIX.csv`, R161). Worse, `WAKING -> LOW_POWER_LISTEN` is not merely
undefined but **explicitly prohibited** by §3.1 of the machine (quoted in §3.3 below), so the V8
rollback could request a transition the machine is required to reject.

## 3. The authoritative `WAKING` out-edges (T5 / T12 / T21)

### 3.1 The out-edge set, as stated in `§2.6 WAKING`

The state description in `STAGE_01_MINER_STATE_MACHINE.md §2.6` enumerates the permitted
`WAKING` departures exactly:

> "**Permitted outgoing transitions.** To `ACTIVE_HASHING` on ramp completion (T5); to
> `OFFLINE` (T12); to `DISQUALIFIED` (T21)."
> — `STAGE_01_MINER_STATE_MACHINE.md`, lines 428–429

and its failure behaviour confirms that a wake that cannot complete validly leaves the state via
`T12`, never by reversion to the pre-wake state:

> "Validation failure of the bound assignment (e.g. overlap with an existing active assignment,
> I1) aborts the wake to `OFFLINE` (T12); attributable protocol violation → `DISQUALIFIED`
> (T21)."
> — `STAGE_01_MINER_STATE_MACHINE.md`, lines 439–441

### 3.2 The three transition-table rows

The transition table (`§3`) carries one row per legal edge. The three rows whose
`current_state` is `WAKING` are:

> `| T5 | `WAKING` | RampComplete (`WakeCompleteEvent` fires, F5) | Ramp complete AND bound
> assignment validated disjoint per I1 and bound to current `TemplateID`; effected by
> `ApplyMinerStateTransition` (F6) at the event's own timestamp | Activate range lease
> (PENDING→CURRENT, or a resumed PATH-B assignment restored to CURRENT …) | `ACTIVE_HASHING` |
> … | Validation failure / wake-deadline expiry → wake abort to `OFFLINE` (T12); range released |`
> — `STAGE_01_MINER_STATE_MACHINE.md`, line 523

> `| T12 | `WAKING` | Departure / WakeDeadlineExpiry / ValidationAbort | Ramp not completed or
> bound assignment fails I1/`TemplateID` validation within wake deadline, or liveness lost |
> Release bound range; stop wake accrual | `OFFLINE` | End `P_wake`; begin `P_offline` residency
> | No census change (never entered `H_active(t)`) | Attributable violation instead →
> `DISQUALIFIED` (T21) |`
> — `STAGE_01_MINER_STATE_MACHINE.md`, line 530

> `| T21 | `WAKING` | ProtocolViolation | Recorded attributable violation | Release bound range;
> void credit; append to audit log | `DISQUALIFIED` | End `P_wake`; `E_coordination`; begin
> `P_offline` (terminal) | No census change; violation logged | Terminal — no recovery |`
> — `STAGE_01_MINER_STATE_MACHINE.md`, line 539

### 3.3 Legality argument

The `WAKING` out-edge set is **closed** at `{T5, T12, T21}`: `§2.6` (lines 428–429) and the table
(rows 523/530/539) agree, and no fourth row in `§3` carries `current_state = WAKING`. Reading the
table for the *targets* of the three illegal V8 edges confirms the absence directly:

- `REGISTERED` is entered only by T1 (external `RegisterRequest`), T17 (`OFFLINE -> REGISTERED`
  rejoin), and T25 (`RESERVE -> REGISTERED` release) — `STAGE_01_MINER_STATE_MACHINE.md`
  lines 519/535/543. There is **no** `WAKING -> REGISTERED` row.
- `RESERVE` is entered only by T2 (`REGISTERED -> RESERVE`) — line 520. There is **no**
  `WAKING -> RESERVE` row.
- `LOW_POWER_LISTEN` is entered only by T8 (via `EXHAUSTED_PENDING`, PATH A) and the direct
  `ACTIVE_HASHING` edges T26–T29 (PATH B and round-closure reasons) — the machine restricts its
  ingress in `§3.1`.

`§3.1 Explicitly prohibited (illegal) transitions` makes the `LOW_POWER_LISTEN` case explicit and
mandatory to reject:

> "**Any edge into `LOW_POWER_LISTEN` without a recorded `stop_reason`, or from a state other than
> `EXHAUSTED_PENDING` (T8) or `ACTIVE_HASHING` (T26–T29).** In particular `WAKING ->
> LOW_POWER_LISTEN`, `RESERVE -> LOW_POWER_LISTEN`, and `REGISTERED -> LOW_POWER_LISTEN` are
> prohibited."
> — `STAGE_01_MINER_STATE_MACHINE.md`, lines 555–557

Hence a legal rollback of a `WAKING` participant has exactly one non-terminal, non-hashing option:
`T12` to `OFFLINE`. (`T5` completes the wake into hashing — the opposite of a rollback; `T21` is
reserved for an attributable violation.) W2 selects `T12` as the sole rollback edge. `T12`'s
action "Release bound range; stop wake accrual" and its energy effect "No census change (never
entered `H_active(t)`)" are exactly the semantics a rollback requires: the aborted wake is undone
without ever having contributed to the active-hash-rate census.

## 4. The corrected rollback (T12 + `rolled_to_offline` + abort)

### 4.1 `RollbackParticipantSetup` — the legal T12 departure

The corrected `RollbackParticipantSetup` (`STAGE_01_PROTOCOL_PSEUDOCODE.md`, lines 1637–1671)
initialises the `rolled_to_offline` flag, cancels the captured wakes first, then departs any
still-`WAKING` participant along `T12` — never along a `prior_states[m]` edge:

> `SET rolled_to_offline <- false   # W2: true iff any WAKING participant is legally departed to
> OFFLINE (T12)`
> — line 1644

> `# W2: a participant left WAKING is departed to OFFLINE via the LEGAL T12 edge (the ONLY legal`
> `#   WAKING departure besides T5/T21) using the txn's COMPLETE rollback_envelope (W1) — NEVER an`
> `#   illegal WAKING->REGISTERED/RESERVE/LOW_POWER_LISTEN edge and NEVER a placeholder/ambient envelope.`
> `FOR EACH MinerID m in setup_txn.prior_states:`
> `  IF miner_state(m) = WAKING:`
> `    SET tr <- CALL ApplyMinerStateTransition(m, WAKING, OFFLINE,`
> `           transition_envelope = setup_txn.rollback_envelope, reason = participant_setup_rolled_back,   # W1: complete envelope; T12`
> `           assignment_ref = null, candidate_id = null, propagation_id = null)   # F6`
> `    IF tr is transition_applied(teid): SET rolled_to_offline <- true    # W2/W8: a WAKING participant was legally departed`
> — lines 1648–1656

Note that `setup_txn.prior_states` is now iterated only as a **key set** (to find which miners were
raised into `WAKING`); the captured value `prior_states[m]` is no longer the *destination* of the
transition, as it was in the V8 defect (§2). The destination is the literal `OFFLINE`. The
procedure then closes every created head as `CLOSED / revoked`, restores the ledgers, verifies no
residual partial setup remains, and reports the flag:

> `RETURN rollback_completed(rolled_to_offline)   # W2/W8: report whether a retry is state-incompatible`
> — line 1665
>
> `RETURNS: rollback_completed(rolled_to_offline) | rollback_failed(reason)`
> — line 1666

The closing NOTE restates the discipline: it "departs any WAKING participant to OFFLINE via the
LEGAL T12 edge … (never an illegal WAKING->prior edge …), closes every created PENDING head
legally, and restores the ledgers — leaving NO live partial assignment and NO participant WAKING.
It reports rolled_to_offline so the caller can refuse a state-incompatible retry (W8)."
(lines 1667–1671).

### 4.2 `RollbackTemplateRefreshSetup` — identical discipline

`RollbackTemplateRefreshSetup` (lines 1673–1697) applies the same legal-edge discipline to the
refresh's just-created assignments and wakes:

> `SET rolled_to_offline <- false   # W2`
> `FOR EACH wref in setup_txn.wakes (stable order):`
> `  IF wref is still pending on EQ: CANCEL wref on EQ`
> `FOR EACH MinerID m in setup_txn.prior_states:`
> `  IF miner_state(m) = WAKING:`
> `    SET tr <- CALL ApplyMinerStateTransition(m, WAKING, OFFLINE,`
> `           transition_envelope = setup_txn.rollback_envelope, reason = template_refresh_rolled_back,   # W1: complete envelope; T12`
> `           assignment_ref = null, candidate_id = null, propagation_id = null)   # F6`
> `    IF tr is transition_applied(teid): SET rolled_to_offline <- true`
> — lines 1679–1687

> `RETURN rollback_completed(rolled_to_offline)   # W2/W8`
> — line 1694

### 4.3 Callers abort when `rb.rolled_to_offline`

`PrepareParticipantsForNewRound` calls the rollback and, when it reports that any participant was
routed to `OFFLINE`, abandons the retry path and forces a `RoundAbort` — because a miner now in
`OFFLINE` cannot be legally re-enlisted by the setup (which enters `WAKING` only from
`REGISTERED`/`RESERVE`/`EXHAUSTED_PENDING`/`LOW_POWER_LISTEN`, not from `OFFLINE`):

> `SET rb <- CALL RollbackParticipantSetup(RoundContext, participant_setup_txn)   # W1/W2/V8`
> `…`
> `# W8 LIVENESS: seat a bounded, state-compatible SetupRetryEvent ONLY when the rollback left EVERY participant in a`
> `#   state the setup can legally re-enlist (no miner routed to OFFLINE) … Otherwise ABORT — never a retry from an`
> `#   incompatible OFFLINE state.`
> `IF rb.rolled_to_offline:`
> `  RETURN CALL RoundAbort(RoundContext, reason = participant_setup_failed(setup_reason),`
> `                         dispatch_envelope = dispatch_envelope, recovery_finalising = false)   # W8: retry state-incompatible`
> — `STAGE_01_PROTOCOL_PSEUDOCODE.md`, lines 1599, 1603–1608

`TemplateRefresh` enforces the same rule for its refresh rollback:

> `SET rb <- CALL RollbackTemplateRefreshSetup(RoundContext, refresh_setup_txn)   # W1/W2/V8`
> `…`
> `IF rb.rolled_to_offline:`
> `  RETURN CALL RoundAbort(RoundContext, reason = template_refresh_failed(setup_reason),`
> `                         dispatch_envelope = dispatch_envelope, recovery_finalising = false)   # W8: retry state-incompatible`
> — `STAGE_01_PROTOCOL_PSEUDOCODE.md`, lines 4666, 4672–4674

Only when `rb.rolled_to_offline` is false (no participant was moved to `OFFLINE`, so every
participant remains in a state the setup can legally re-enter) does either caller proceed to the
bounded, in-horizon `SetupRetryEvent` path (lines 1609–1621 / 4675–4687). This is the
"abort-oriented" Option 1: a `T12` departure to `OFFLINE` is legal, but it is treated as
retry-incompatible and converted into a declared `RoundAbort` rather than an attempt to re-run the
setup from an incompatible source state.

## 5. Grep evidence: no illegal edge remains in the current pseudocode

Re-grepping the current `STAGE_01_PROTOCOL_PSEUDOCODE.md` (not trusting prior line numbers):

1. **No illegal `WAKING` destination is ever passed to a transition.** A search for
   `WAKING, REGISTERED` / `WAKING, RESERVE` / `WAKING, LOW_POWER_LISTEN` / `WAKING,
   setup_txn.prior_states` as a transition destination returns **zero** matches:

   ```
   grep -cnE "WAKING, (REGISTERED|RESERVE|LOW_POWER_LISTEN)|WAKING, setup_txn\.prior_states"
        STAGE_01_PROTOCOL_PSEUDOCODE.md
   → 0
   ```

2. **Every `ApplyMinerStateTransition(..., WAKING, X)` call targets only a legal edge.** Listing
   every occurrence of `WAKING` as the *source* argument shows `X ∈ {ACTIVE_HASHING, OFFLINE}`
   exclusively — i.e. only `T5` and `T12`; no `REGISTERED`/`RESERVE`/`LOW_POWER_LISTEN`
   destination appears:

   | Line | Call | Edge |
   |------|------|------|
   | 1185 | `ApplyMinerStateTransition(MinerID, WAKING, ACTIVE_HASHING, …)` | T5 (`WakeCompleteEvent`, ramp complete) |
   | 1195 | `ApplyMinerStateTransition(MinerID, WAKING, OFFLINE, …)` | T12 (wake-deadline expiry) |
   | 1653 | `ApplyMinerStateTransition(m, WAKING, OFFLINE, …)` | T12 (`RollbackParticipantSetup`) |
   | 1684 | `ApplyMinerStateTransition(m, WAKING, OFFLINE, …)` | T12 (`RollbackTemplateRefreshSetup`) |
   | 3780 | `ApplyMinerStateTransition(holder, WAKING, OFFLINE, …)` | T12 |
   | 4453 | `ApplyMinerStateTransition(h, WAKING, OFFLINE, …)` | T12 (round-close while waking) |
   | 4577 | `ApplyMinerStateTransition(h, WAKING, OFFLINE, …)` | T12 |

3. **The only textual occurrences of the illegal-edge strings are prohibitions, not calls.** The
   strings `WAKING->REGISTERED/RESERVE/LOW_POWER_LISTEN` and `WAKING -> LOW_POWER_LISTEN` appear
   only inside explanatory comments that forbid them:
   - line 1649 — "… NEVER an illegal `WAKING->REGISTERED/RESERVE/LOW_POWER_LISTEN` …";
   - line 4449 — "F6/F8: `WAKING -> LOW_POWER_LISTEN` is ILLEGAL (miner SM §3.1); the legal
     closure edge is `WAKING -> OFFLINE` (T12) …".

4. **`prior_states[m]` is recorded but never used as a transition target.** It is written at
   lines 1582 (`RECORD participant_setup_txn.prior_states[m] <- spec.from`) and 4640
   (`RECORD refresh_setup_txn.prior_states[m] <- miner_state(m)`), and thereafter iterated only
   as a key set in the two rollback loops (§4). The pre-W2 pattern
   `ApplyMinerStateTransition(m, WAKING, setup_txn.prior_states[m], …)` survives only in the
   frozen Stage-1V audit (`STAGE_01V_SETUP_ROLLBACK_LIVENESS_AUDIT.md`, line 125), not in the
   corrected pseudocode.

The corrected specification therefore contains no residual illegal miner-state edge in any
rollback path.

## 6. Mapping to test vectors TV187 / TV188 / TV196

Requirement **R168** (`STAGE_01_TRACEABILITY_MATRIX.csv`) names the blocking test vectors for the
legal-rollback and plan-transaction closure (W1–W8) and assigns them to a
`STAGE_01W_SEMANTIC_TEST_VECTORS` artifact. The three W2 vectors are, per that row:

- **TV187** — "a REGISTERED miner in WAKING rolled back with only legal edges (no
  WAKING->REGISTERED)". This exercises §4.1: a participant enlisted from `REGISTERED` (T3) and left
  in `WAKING` at setup failure is departed by `T12` to `OFFLINE`; the assertion is that no
  `WAKING -> REGISTERED` edge is applied and `rolled_to_offline` becomes true.
- **TV188** — "a LOW_POWER_LISTEN miner in WAKING rolled back with no WAKING->LOW_POWER_LISTEN".
  This exercises the `LOW_POWER_LISTEN`-origin case (T10/T30): the rollback must **not** attempt the
  prohibited `WAKING -> LOW_POWER_LISTEN` edge (§3.1, lines 555–557) but instead depart via `T12`.
- **TV196** — "rollback leaving miners OFFLINE seats no retry and RoundAbort executes". This
  exercises §4.3: when `rb.rolled_to_offline` is true, both `PrepareParticipantsForNewRound`
  (lines 1606–1608) and `TemplateRefresh` (lines 4672–4674) seat no `SetupRetryEvent` and return a
  declared `RoundAbort`.

**Status observation (grounded).** These three vectors are currently *named* in the traceability
matrix (R168, status `SPECIFIED`) but are **not yet written out** as executable vector bodies in
this stage directory. The most recent semantic-test-vector file present,
`STAGE_01V_SEMANTIC_TEST_VECTORS.md`, is titled "TV174–TV185" and defines only TV174–TV185; a
`STAGE_01W_SEMANTIC_TEST_VECTORS.md` (the target artifact named by R168) does not yet exist in the
directory. TV187/TV188/TV196 are therefore forward references to be authored in the Stage-1W
semantic-test-vector artifact; the corrected procedures audited here (§4) are the exact procedures
those vectors are declared to drive (`RollbackParticipantSetup`, `RollbackTemplateRefreshSetup`,
`SetupRetryEvent`, `ApplyMinerStateTransition`).

## 7. Traceability

| Anchor | Location | W2 content |
|--------|----------|------------|
| Round-SM §3.10a (W2) | `STAGE_01_ROUND_STATE_MACHINE.md`, lines 641–645 | "A participant left `WAKING` when setup fails is departed to `OFFLINE` via the LEGAL `T12` edge … the illegal `WAKING -> REGISTERED` / `WAKING -> RESERVE` / `WAKING -> LOW_POWER_LISTEN` edges are never passed to `ApplyMinerStateTransition`. The rollback reports `rolled_to_offline`, and a rollback that routed any participant to `OFFLINE` forces a `RoundAbort`." |
| Invariant I16 (W1/W2) | `STAGE_01_INVARIANT_CATALOGUE.md`, lines 322–327 | "**W1/W2 (legal setup rollback):** an ordinary-setup rollback … departs any `WAKING` participant to `OFFLINE` via the LEGAL `T12` edge ONLY — no placeholder envelope and no illegal `WAKING -> REGISTERED`/`RESERVE`/`LOW_POWER_LISTEN` edge is ever passed to `ApplyMinerStateTransition`; after rollback no participant remains `WAKING` and no live partial assignment remains." |
| Terminology (W2) | `STAGE_01_TERMINOLOGY.md`, lines 833–835 | "**Legal rollback edge (W2).** A setup rollback departs a `WAKING` participant to `OFFLINE` via the authoritative `T12` edge only; the illegal `WAKING -> REGISTERED`/`RESERVE`/`LOW_POWER_LISTEN` edges are never used. `RollbackParticipantSetup` / `RollbackTemplateRefreshSetup` return `rollback_completed(rolled_to_offline)`." |
| Requirement R161 | `STAGE_01_TRACEABILITY_MATRIX.csv`, R161 | "Use only legal miner-state edges during rollback (W2) … the illegal `WAKING->REGISTERED / WAKING->RESERVE / WAKING->LOW_POWER_LISTEN` edges are never passed to `ApplyMinerStateTransition`; the rollback reports `rolled_to_offline` and a rollback that routed any participant to `OFFLINE` forces a `RoundAbort`." Procedures: `RollbackParticipantSetup;RollbackTemplateRefreshSetup;ApplyMinerStateTransition`; invariants `I16;I3`; threat "a rollback invoking a miner-state edge absent from the authoritative miner transition table"; status `SPECIFIED`. |
| Requirement R168 (test vectors) | `STAGE_01_TRACEABILITY_MATRIX.csv`, R168 | Names TV187 / TV188 / TV196 (with TV186, TV189–TV197) as blocking vectors targeting `STAGE_01W_SEMANTIC_TEST_VECTORS`; invariants `I1;I3;I16;I18b`; status `SPECIFIED`. |

### 7.1 Consistency of the anchors

The four normative anchors (round-SM §3.10a, invariant I16, terminology W2, requirement R161) and
the two executable procedures (`RollbackParticipantSetup`, `RollbackTemplateRefreshSetup`) state
the same rule in the same terms: the sole legal rollback departure of a `WAKING` participant is
`T12` to `OFFLINE`; the three `WAKING -> prior` edges are never passed to
`ApplyMinerStateTransition`; the outcome is reported via `rolled_to_offline`; and a rollback that
routed any participant to `OFFLINE` forces a `RoundAbort`. R161 correctly binds the requirement to
invariants **I16** (breaches recorded, never silently repaired — a rollback may not manufacture an
undefined transition to "repair" a failed setup) and **I3** (round/template freshness). No
inconsistency was found among the anchors. The A1 baseline `8.420833333 kWh` is unaffected by W2
and remains as specified in `STAGE_01_ENERGY_MODEL_SPECIFICATION.md`.
