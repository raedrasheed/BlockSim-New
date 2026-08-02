# Stage 1AI — Driver-Request Round-Scope Audit (AI5)

Scope: documentation-only formal-spec verification of correction **AI5** (explicit
driver-request round scope) against the FINAL normative tree of the BlockSim/PoCol
Stage-1 protocol. This audit reads and cites the normative pseudocode only; it performs
no experiments and modifies no source, configuration, or prior Stage-1A..1AH artifact.

All `file:line` anchors below reference the single normative source:
`docs/thesis_revision_v45/stage_01/STAGE_01_PROTOCOL_PSEUDOCODE.md`
(hereafter "the pseudocode"). Line numbers are those of the FINAL tree at audit time.

---

## 1. Defect statement (the AH residual this correction closes)

Through Stage 1AH, a sim-driver request was recorded as an explicit `driver_request`
record (AH4: `kind`, `driver_admission_time`, `requested_event_time`, `payload`,
`status`), but the record carried **no round scope**. The intake
(`SeatPendingDriverRequests`) routed every PENDING request to its seat owner against
whatever `RunContext.current_round_context` happened to be current at intake time. Two
unsound executions were therefore admissible under the AH tree:

1. **Stale reserve activation against a different round.** An
   `ORDINARY_RESERVE_DEFICIT` detected while round *N* was in `SECURITY_RECOVERY` /
   `ASSIGNMENT` could, if not seated before round *N* terminalised, be silently routed
   and executed against round *N+1* — even though a reserve activation is meaningful
   only against the exact round whose deficit was detected.

2. **Stale genesis / exact join re-seated under a later round.** A join that logically
   belonged to a specific round (a genesis registration for `RoundID_current`) had no
   way to declare "this round only", so a request left pending across a round boundary
   could be seated under the wrong, later round.

The shared root cause: the request layer could not express *which* round a request was
valid for, so the intake had no structural gate distinguishing "seat now", "wait for a
later round", and "this request is stale — reject". A stale `EXACT_ROUND` request could
be silently seated under a terminal/new round and then executed there.

**AI5 remedy.** Introduce a first-class `DriverRoundScope` on every `driver_request`,
constrain it structurally at admission, and make `SeatPendingDriverRequests` consult a
declared scope/round-state gate (`SCOPE_ADMITS`) **before** routing to any seat owner, so
that a stale request is rejected (not re-seated), a not-yet-admissible join waits (stays
PENDING), and only an admissible request reaches its owner. This preserves the idle
policy within PoCol: driver intake never advances or mutates a round it is not scoped to.

---

## 2. Numbered verification table

| # | Claim (AI5) | Evidence (`STAGE_01_PROTOCOL_PSEUDOCODE.md`) | Verdict |
|---|-------------|-----------------------------------------------|---------|
| 1 | `DriverRoundScope` union is declared as `EXACT_ROUND(RoundID) \| NEXT_AVAILABLE_ROUND \| RUN_LEVEL`. | `STRUCTURE RunContext` note, line **3028**: `# AI5 — DriverRoundScope in { EXACT_ROUND(RoundID), NEXT_AVAILABLE_ROUND, RUN_LEVEL }`; semantics of each variant lines **3028–3033**. | PASS |
| 2 | The `driver_request` STRUCTURE carries a `round_scope` field typed `DriverRoundScope`. | `STRUCTURE driver_request`, lines **3075–3077**: `round_scope : AI5 — the DriverRoundScope this request is validated against (EXACT_ROUND(RoundID) / NEXT_AVAILABLE_ROUND / RUN_LEVEL). ORDINARY_RESERVE_DEFICIT is ALWAYS EXACT_ROUND; a MINER_JOIN is EXACT_ROUND (genesis) or NEXT_AVAILABLE_ROUND (a later external join)`. Header tag `AH4/AI2/AI3/AI4/AI5` at line **3060**. | PASS |
| 3 | `AdmitDriverRequest` takes `round_scope` as an input. | `PROCEDURE AdmitDriverRequest` INPUTS, line **1712**: `INPUTS: RunContext, kind, requested_event_time, round_scope, payload ... round_scope: DriverRoundScope (AI5)`. Field threaded into the record at line **1746**: `round_scope = round_scope`. | PASS |
| 4 | `AdmitDriverRequest` STRUCTURALLY enforces that an `ORDINARY_RESERVE_DEFICIT` is admitted ONLY with `EXACT_ROUND(payload.RoundID_at_seat)`, else it returns `driver_request_scope_invalid`. | Lines **1719–1721**: `IF kind = ORDINARY_RESERVE_DEFICIT AND round_scope != EXACT_ROUND(payload.RoundID_at_seat): RETURN driver_request_scope_invalid(kind, round_scope)`; declared in RETURNS at line **1754**. Precondition text lines **1715–1717**. | PASS |
| 5 | A `MINER_JOIN` is `EXACT_ROUND` (genesis) or `NEXT_AVAILABLE_ROUND` (a later external join). | Precondition, line **1717**: `a MINER_JOIN is EXACT_ROUND (genesis) or NEXT_AVAILABLE_ROUND`; corroborated at `driver_request` note line **3076–3077** and `RoundInitialise` note line **3234** (`Later arrivals use AdmitDriverRequest directly with NEXT_AVAILABLE_ROUND scope`). | PASS |
| 6 | The genesis admission in `RoundInitialise` passes `round_scope = EXACT_ROUND(RoundID_current)`. | `RoundInitialise` genesis block, lines **3238–3240**: `SET g_adm <- CALL AdmitDriverRequest(RunContext, kind = MINER_JOIN, requested_event_time = EQ.current_event_time, round_scope = EXACT_ROUND(RoundID_current), payload = { join_request = g.join_request })`; rationale line **3228** (`a genesis registration belongs to THIS round, never a later one`). | PASS |
| 7 | `SCOPE_ADMITS(round_scope, kind, rc)` notation is defined, returning one of `{ SCOPE_ADMIT, SCOPE_WAIT, SCOPE_STALE }`. | `STRUCTURE RunContext` note, lines **3034–3035**: `Notation SCOPE_ADMITS(round_scope, kind, rc) ... returning one of { SCOPE_ADMIT, SCOPE_WAIT, SCOPE_STALE } (a lowercase notation, NOT a CALL target)`; `round_admits(kind, rc)` defined lines **3035–3037**. | PASS |
| 8 | `SCOPE_ADMITS` maps `EXACT_ROUND(rid)` with `rid = rc.RoundID` and admitting → `SCOPE_ADMIT`. | Line **3038**: `EXACT_ROUND(rid): rid = rc.RoundID AND round_admits(kind, rc) -> SCOPE_ADMIT`. | PASS |
| 9 | `SCOPE_ADMITS` maps `EXACT_ROUND(rid)` matching `rc.RoundID` but non-admitting/terminal → `SCOPE_STALE`. | Line **3039**: `rid = rc.RoundID AND NOT round_admits(kind, rc) -> SCOPE_STALE   # its round is terminal / no longer admits`. | PASS |
| 10 | `SCOPE_ADMITS` maps `EXACT_ROUND(rid)` with `rid != rc.RoundID` → `SCOPE_STALE` (a different round is active — never seat here). | Line **3040**: `rid != rc.RoundID -> SCOPE_STALE   # a DIFFERENT round is active — never seat here`. | PASS |
| 11 | `SCOPE_ADMITS` maps `NEXT_AVAILABLE_ROUND` → `SCOPE_ADMIT` if admitting else `SCOPE_WAIT`. | Line **3041**: `NEXT_AVAILABLE_ROUND: round_admits(kind, rc) -> SCOPE_ADMIT ELSE SCOPE_WAIT   # waits (stays PENDING) for the next admitting round`. | PASS |
| 12 | `SCOPE_ADMITS` maps `RUN_LEVEL` → `SCOPE_STALE` (bootstrap-only scope; never routed through the join/reserve intake). | Line **3042**: `RUN_LEVEL: SCOPE_STALE   # a bootstrap-only scope; never routed through the join/reserve intake`. | PASS |
| 13 | `SeatPendingDriverRequests` consults `SCOPE_ADMITS` BEFORE routing to the seat owner. | Line **1822**: `SET scope_ok <- SCOPE_ADMITS(dr.round_scope, dr.kind, rc)`, evaluated before the `SWITCH dr.kind` seat routing at lines **1830–1833**; the STALE/WAIT branches (lines **1823–1829**) `CONTINUE` past routing. Intent note lines **1811–1814**, **1818–1821**. | PASS |
| 14 | A `SCOPE_STALE` request is REJECTED via `SetDriverRequestStatus` with disposition `driver_request_scope_stale` and removed from the pending index. | Lines **1823–1828**: `IF scope_ok = SCOPE_STALE:` → `CALL SetDriverRequestStatus(..., new_status = REJECTED, disposition = driver_request_scope_stale(dr.round_scope, rc.RoundID))`; `REMOVE drid FROM RunContext.pending_driver_request_index`; `RECORD driver_request_rejected(...)`; `CONTINUE`. | PASS |
| 15 | A `SCOPE_WAIT` request stays PENDING (left on the index for a later round). | Line **1829**: `IF scope_ok = SCOPE_WAIT: CONTINUE   # AI5: NEXT_AVAILABLE_ROUND not yet admissible — leave PENDING for a later round`. (No status mutation, no index removal on this branch.) | PASS |
| 16 | Only `SCOPE_ADMIT` routes to the named seat owner. | Lines **1830–1833**: `# scope_ok = SCOPE_ADMIT — route to the named owner as a DRIVER-intake seat.` followed by `SWITCH dr.kind: CASE MINER_JOIN -> SeatMinerRegister(...); CASE ORDINARY_RESERVE_DEFICIT -> SeatReserveActivate(...)`. Reached only after the STALE (`CONTINUE`) and WAIT (`CONTINUE`) branches are excluded. | PASS |
| 17 | Key property: an `EXACT_ROUND` request is NEVER silently seated under a terminal round and then executed against a different/later round. | Stated in `SeatPendingDriverRequests` intent, lines **1820–1821** (`a stale EXACT_ROUND scope ... is REJECTED here — NEVER silently seated under a terminal round and then executed against a new round`), and in the `RunContext` note, lines **3044–3045** (`This is why no EXACT_ROUND request is ever silently seated under a terminal round and then executed against a new round (AI5)`). Enforced mechanically by items 9, 10, 14. | PASS |

---

## 3. Explicit check — reserve activation is always `EXACT_ROUND`

The claim under audit is that a reserve activation can only ever execute against the
exact round whose deficit produced it. This is enforced at three independent layers, and
all three agree:

1. **Admission layer (structural rejection).** `AdmitDriverRequest` refuses to admit any
   `ORDINARY_RESERVE_DEFICIT` whose `round_scope` is not exactly
   `EXACT_ROUND(payload.RoundID_at_seat)`, returning `driver_request_scope_invalid`
   (pseudocode lines **1719–1721**, RETURNS line **1754**). Because the scoped round id is
   bound to `payload.RoundID_at_seat` — the very field that identifies the deficit's round
   — a reserve deficit can never be admitted with `NEXT_AVAILABLE_ROUND` or `RUN_LEVEL`.
   The `payload` shape guarantees `RoundID_at_seat` is present for this kind (line
   **3078**: `ORDINARY_RESERVE_DEFICIT -> { RoundID_at_seat, deficit }`), and the logical
   identity is likewise keyed on it (line **1736**:
   `RESERVE_ACTIVATION(payload.RoundID_at_seat, deficit_identity(payload.deficit))`).

2. **Record-invariant layer.** The `driver_request` STRUCTURE states the invariant
   directly: `ORDINARY_RESERVE_DEFICIT is ALWAYS EXACT_ROUND` (line **3076**).

3. **Seat / gate layer (execution).** `SeatReserveActivate` carries the request's own
   scope through to the seat unchanged — `intended_round_scope = driver_request.round_scope`
   (line **1672**), annotated `AI5: always EXACT_ROUND for a reserve deficit` at line
   **1668**. Because the request reaches `SeatReserveActivate` only via the
   `SCOPE_ADMIT` branch of `SeatPendingDriverRequests` (line **1833**, gated by
   `SCOPE_ADMITS` at line **1822**), and because `SCOPE_ADMITS` grants `SCOPE_ADMIT` to an
   `EXACT_ROUND(rid)` request only when `rid = rc.RoundID AND round_admits(...)` (line
   **3038**) — with `round_admits` for a reserve deficit requiring
   `rc.round_state in {SECURITY_RECOVERY, ASSIGNMENT}` and non-terminal (lines
   **3036–3037**) — a reserve activation can be seated against, and only against, the
   exact non-terminal round that admits it. Any other round yields `SCOPE_STALE`
   (lines **3039–3040**) and the request is rejected, never re-seated (item 14).

The three layers are mutually reinforcing: admission cannot even record a
non-`EXACT_ROUND` reserve request, and even if one were somehow present, the intake gate
would classify it `SCOPE_STALE` for any round other than its own and reject it. There is
no path by which a reserve activation executes against a round other than
`payload.RoundID_at_seat`. **Reserve-activation-always-`EXACT_ROUND`: PASS.**

---

## 4. Overall verdict

**PASS.** All seventeen numbered claims verify against exact `file:line` anchors in the
FINAL normative tree, and the reserve-activation-always-`EXACT_ROUND` property is
independently confirmed at the admission, record-invariant, and seat/gate layers.

- The `DriverRoundScope` union `EXACT_ROUND(RoundID) | NEXT_AVAILABLE_ROUND | RUN_LEVEL`
  is declared (line 3028) and carried as `driver_request.round_scope` (lines 3075–3077).
- `AdmitDriverRequest` takes `round_scope` (line 1712) and structurally rejects any
  reserve deficit not scoped `EXACT_ROUND(payload.RoundID_at_seat)` with
  `driver_request_scope_invalid` (lines 1719–1721, 1754); `MINER_JOIN` is `EXACT_ROUND`
  (genesis) or `NEXT_AVAILABLE_ROUND` (later join) (line 1717).
- Genesis admission passes `EXACT_ROUND(RoundID_current)` (lines 3238–3240), and the
  in-dispatch genesis seat filters on `gdr.round_scope = EXACT_ROUND(rc.RoundID)`
  (line 1378).
- `SCOPE_ADMITS(round_scope, kind, rc)` is defined returning
  `{SCOPE_ADMIT, SCOPE_WAIT, SCOPE_STALE}` with the exact mapping required
  (lines 3034–3045).
- `SeatPendingDriverRequests` consults `SCOPE_ADMITS` before routing (line 1822):
  `SCOPE_STALE` is rejected via `SetDriverRequestStatus`
  (`driver_request_scope_stale`) and removed from the pending index (lines 1823–1828);
  `SCOPE_WAIT` stays PENDING (line 1829); only `SCOPE_ADMIT` routes to the owner
  (lines 1830–1833).
- The key soundness property holds by construction: an `EXACT_ROUND` request is never
  silently seated under a terminal round and executed against a later round
  (lines 1820–1821, 3044–3045).

No genuine FAIL was found. The AI5 correction, as expressed in the final normative
pseudocode, closes the AH round-scope defect completely and preserves the idle policy
within PoCol.
