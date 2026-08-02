# Stage 1AC — SetupRetryEvent Guard-Order Audit (correction AC3)

This audit verifies that correction **AC3** fixes the `SetupRetryEvent` guard order in the frozen source
of truth `STAGE_01_PROTOCOL_PSEUDOCODE.md` so that the terminal-status replay check precedes any
payload-integrity handling. The algorithm is **PoCol**; the mechanism exercised here is the idle policy
within PoCol (a bounded, idempotent retry of a rolled-back setup). All Stage-1AC artifacts preserve the
A1 baseline (`8.420833333 kWh`); nothing in AC3 touches the energy model. This is a documentation-only
audit — it reads the pseudocode and the companion Stage-1AC deliverables and edits none of them.

Every claim below is grounded with `file:line` citations into `STAGE_01_PROTOCOL_PSEUDOCODE.md`
(abbreviated **PC** below) and quotes the operative current lines. Grep counts are reported inline.

The exact correction under audit (AC3): the `SetupRetryEvent` guard order is precisely
(1) validate enough structure to resolve the `SetupRetryID`; (2) resolve the record; (3) verify
dispatched-EventRef ownership (`dispatched_event_ref` vs `rec.seat_event_ref`); (4) **IF `status != SEATED`
return `setup_retry_duplicate_suppressed` — BEFORE any payload-integrity abort**; (5) determine the
stale/closed-round disposition from the immutable record; (6) **only for a current owned SEATED record**,
validate the payload; (7) current-round target guards; (8) target execution. A replay of an
`APPLIED`/`SUPERSEDED`/`CANCELLED`/`ABORTED` (or in-flight `APPLYING`) retry must never abort a round
merely because replayed payload fields differ.

---

## 0. Scope and grounding

AC3 lives entirely inside `PROCEDURE SetupRetryEvent` (**PC:2090–2247**) and its §0.8 addendum
(**PC:1003–1007**). The executable `EFFECTS` block (**PC:2103–2229**) is authoritative; the §0.8 addendum
and the round-state-machine §3.10g clause restate it in prose. This audit quotes the executable steps and
confirms the ordering property the correction asserts.

Grep counts (`STAGE_01_PROTOCOL_PSEUDOCODE.md`):
`setup_retry_duplicate_suppressed` = **3** (the guard return PC:2128, the §0.8 addendum PC:1005, the
`RETURNS` union PC:2231); `rec.status != SEATED` = **1** (the step-(4) test PC:2127);
`dispatched_event_ref != rec.seat_event_ref` = **2** (the step-(3) test PC:2122 plus its annotation);
`setup_retry_payload_integrity_failure` = **2** (the step-(6) abort reason PC:2164 plus its annotation).

---

## 1. PASS — the canonical guard order is exactly steps (1)–(8), and step (4) precedes step (6)

The handler's `EFFECTS` opens with the canonical order as a normative comment, then implements it line for
line. The declared order — **PC:2104–2108**:

> `# AC3 CANONICAL GUARD ORDER: (1) structure to resolve the id; (2) RESOLVE the record; (3) AC5 EVENTREF OWNERSHIP`
> `#   (dispatched_event_ref vs rec.seat_event_ref); (4) AC3 STATUS-based replay (non-SEATED -> duplicate-suppress) BEFORE`
> `#   any payload/integrity handling; (5) AC4 stale/closed-round disposition decided from the IMMUTABLE RECORD fields;`
> `#   (6) ONLY for a current owned SEATED record: validate the dispatch envelope + payload (a failure is a CURRENT-round`
> `#   integrity abort, AC5-C); (7) current-round target guards; (8) target execution.`

The executable steps, in file order:

| Step | What it does | Line range | Operative current line |
|---|---|---|---|
| **(1)** | Validate structure enough to resolve the `SetupRetryID`; else stale no-op | PC:2112–2114 | `IF SetupRetryID is not structurally valid: RETURN setup_retry_stale_noop(SetupRetryID)` |
| **(2)** | Resolve the ONE record (read-only snapshot); unknown id → stale no-op | PC:2115–2118 | `SET rec <- setup_retry_records[SetupRetryID]` |
| **(3)** | EventRef ownership: `dispatched_event_ref` vs immutable `rec.seat_event_ref`; foreign ref → stale no-op leaving the record SEATED | PC:2119–2123 | `IF dispatched_event_ref != rec.seat_event_ref: RETURN setup_retry_stale_noop(SetupRetryID)` |
| **(4)** | **Terminal-replay idempotence: non-SEATED → duplicate-suppress, BEFORE any payload check** | PC:2124–2128 | `IF rec.status != SEATED: RETURN setup_retry_duplicate_suppressed(SetupRetryID)` |
| **(5)** | Stale/closed-round disposition decided from the IMMUTABLE record fields (`rec.RoundID`, round state, `rec.TemplateID_at_seat`) | PC:2129–2152 | `IF rec.RoundID != RoundID_current: CALL SetSetupRetryStatus(SetupRetryID, SUPERSEDED) ...` |
| **(6)** | **Owning-event integrity — ONLY for a current owned SEATED record**: validate envelope + payload; failure → current-round abort via SEATED→APPLYING→ABORTED | PC:2153–2170 | `IF dispatch_envelope is incomplete OR NOT (RoundID = rec.RoundID AND ...): CALL SetSetupRetryStatus(SetupRetryID, APPLYING) ... RoundAbort(...)` |
| **(7)** | Current-round target guards (wrong round state / budget / state-incompatible), each SEATED→APPLYING→ABORTED | PC:2171–2199 | `IF round_state != ASSIGNMENT: ... RoundAbort(...)` |
| **(8)** | First dispatch: SEATED→APPLYING, mark event CONSUMED, capture the target result, re-read, classify terminal | PC:2200–2229 | `ATOMICALLY: CALL SetSetupRetryStatus(SetupRetryID, APPLYING)` |

**Step (4) precedes step (6) — the load-bearing property.** The non-SEATED replay test is written at
**PC:2124–2128**:

> `# (4) AC3 TERMINAL-REPLAY IDEMPOTENCE — checked BEFORE any payload-integrity handling. Any NON-SEATED status`
> `#   (APPLYING / APPLIED / SUPERSEDED / CANCELLED / ABORTED) is a replay: duplicate-suppress. A replay of a terminal record`
> `#   must NEVER abort a round merely because replayed payload fields differ (AC3).`
> `IF rec.status != SEATED:`
> `  RETURN setup_retry_duplicate_suppressed(SetupRetryID)   # AC3: replay of an already-progressed record; no payload check, no abort`

The payload-integrity block is the FIRST place any payload field is inspected, and it sits below the
step-(4) return, at **PC:2159–2164**:

> `IF dispatch_envelope is incomplete`
> `   OR NOT (RoundID = rec.RoundID AND setup_kind = rec.setup_kind AND TemplateID_at_seat = rec.TemplateID_at_seat`
> `           AND TemplateRefreshSetupID = rec.TemplateRefreshSetupID AND retry_generation = rec.retry_generation):`
> `  CALL SetSetupRetryStatus(SetupRetryID, APPLYING)       # AC6: leave SEATED FIRST (the genuine owned event is being consumed)`
> `  ... SET disp <- CALL RoundAbort(RoundContext, reason = setup_retry_payload_integrity_failure(setup_kind), ...)`

Because the step-(4) `RETURN` at PC:2128 lies strictly above the first payload comparison at PC:2160–2161
(the only place the untrusted payload fields `RoundID` / `setup_kind` / `TemplateID_at_seat` /
`TemplateRefreshSetupID` / `retry_generation` are read), any non-SEATED record returns before a single
payload field is examined. The handler's closing NOTE restates the guarantee — **PC:2237–2239**:

> `... GUARD ORDER (AC3) — the non-SEATED`
> `replay check runs BEFORE payload integrity, so a terminal replay with a corrupted payload is duplicate-suppressed and`
> `NEVER aborts a round.`

**Result: PASS.** The executable order is exactly (1)–(8) as declared at PC:2104–2108, and step (4)
(non-SEATED duplicate-suppress, PC:2124–2128) is textually and control-flow-wise upstream of step (6)
(payload validation / integrity abort, PC:2153–2170).

---

## 2. PASS — a terminal-status replay with a corrupted payload returns `setup_retry_duplicate_suppressed` and never reaches `RoundAbort`

Trace a replay of a record that already advanced to a terminal status (`APPLIED` / `SUPERSEDED` /
`CANCELLED` / `ABORTED`, or in-flight `APPLYING`) whose genuine EventRef is replayed
(`dispatched_event_ref = rec.seat_event_ref`) but whose payload fields are corrupted:

- Step (1) PC:2113 — the id is structurally valid (it resolves), so no stale no-op here.
- Step (2) PC:2116–2118 — the record EXISTS, so `rec` is bound.
- Step (3) PC:2122 — ownership holds (`dispatched_event_ref = rec.seat_event_ref`), so control does NOT
  divert to the foreign-ref stale no-op; it falls through to step (4).
- Step (4) PC:2127 — `rec.status != SEATED` is TRUE for any of `APPLYING`/`APPLIED`/`SUPERSEDED`/
  `CANCELLED`/`ABORTED`, so the handler `RETURN setup_retry_duplicate_suppressed(SetupRetryID)` at
  PC:2128 immediately.

Control never reaches step (5) (PC:2129), step (6) (PC:2159), or step (7) (PC:2171–2199) — the only sites
that call `RoundAbort` inside this handler are the step-(6) integrity abort (PC:2164) and the three
step-(7) target-guard aborts (PC:2175, PC:2184, PC:2193), all strictly below the step-(4) return at
PC:2128. The corrupted payload fields at PC:2160–2161 are never read. Therefore a terminal-status replay
with a corrupted payload returns `setup_retry_duplicate_suppressed(SetupRetryID)` and can never invoke
`RoundAbort`.

This also preserves the record: because a terminal record short-circuits at PC:2128 with no status write,
`SetSetupRetryStatus` (**PC:2288–2306**, the sole status writer) is never called on the replay, so no
`terminal → terminal` rewrite is even attempted (that rewrite would be rejected with no mutation anyway,
PC:2299–2303). The replay leaves the terminal record exactly as it was.

**Result: PASS.** A terminal-status replay with a corrupted payload returns
`setup_retry_duplicate_suppressed` at PC:2128 and never reaches any `RoundAbort` call site
(PC:2164 / 2175 / 2184 / 2193).

---

## 3. PASS — payload validation happens ONLY for a current owned SEATED record (after steps 3, 4, 5)

The payload-integrity block (step 6, PC:2153–2170) is reachable only after every earlier guard has passed,
which is exactly the "current owned SEATED record" predicate:

- **Owned** — established at step (3), PC:2122: the block is below the ownership test, so
  `dispatched_event_ref = rec.seat_event_ref` holds (a foreign ref already stale-no-oped at PC:2123).
- **SEATED** — established at step (4), PC:2127: the block is below the non-SEATED return, so `rec.status`
  is necessarily `SEATED` here (every non-SEATED status already returned `setup_retry_duplicate_suppressed`
  at PC:2128).
- **Current** — established at step (5), PC:2133–2152: the block is below all four stale/closed-round
  exits, so the record's own round is the current round (`rec.RoundID = RoundID_current`, PC:2133), that
  round is nonterminal (`round_state not in {ROUND_ACCEPTED, ROUND_ABORTED}`, PC:2137), and the record's
  seat-time template identity is still current (PC:2141–2152). Each of these decisions is made from the
  IMMUTABLE record fields, never the payload.

The step-(6) comment names this precondition explicitly — **PC:2153–2156**:

> `# (6) AC5-C OWNING-EVENT INTEGRITY — ONLY for a CURRENT OWNED SEATED record (established current nonterminal round + current`
> `#   template in step 5). Validate the dispatch envelope AND the payload against the immutable record. A failure is corruption`
> `#   of the genuine owning event: it may NOT remain SEATED with its only event consumed. Since the record belongs to the`
> `#   CURRENT NONTERMINAL round, take the declared current-round integrity abort via the AC6 legal path`

Consequently the untrusted payload fields are compared (PC:2160–2161) only when the record is a current,
owned, SEATED record; and a validation failure aborts *the record's own current round* via the legal
status path `SEATED → APPLYING → ABORTED` (PC:2162, PC:2169) with the abort result captured first
(PC:2164–2168). No historical, foreign, or terminal record ever reaches a payload comparison.

**Result: PASS.** Payload validation (PC:2159–2161) executes only after steps (3), (4), and (5) have
established a current owned SEATED record; it is unreachable for foreign, non-SEATED, or older/terminal
records.

---

## 4. Supersession of the prior-layer ordering narrative (AA3 → AC3)

For completeness and audit honesty: the frozen Stage-1AA narrative comment AA3 (**PC:934–937**) describes
the *earlier* ordering ("`SetupRetryEvent` resolves `setup_retry_records[SetupRetryID]` and verifies the
payload BEFORE the stale-RoundID check"). AC3 supersedes that ordering. The current executable `EFFECTS`
block (PC:2104–2229) is authoritative and implements the corrected order, and the §0.8 AC3 addendum
(**PC:1003–1007**) and AB5 annotation (**PC:986–987**, "AC3 reorders the guard so the non-SEATED replay
check precedes payload integrity") record the supersession in place. This supersession is tracked in
`STAGE_01AC_SUPERSESSION_REGISTER.md`; the AA3 line remains only as a frozen historical-layer comment, not
as a live ordering directive. The behaviour that governs is the one audited in §§1–3.

---

## 5. Test-vector linkage (TV246)

`STAGE_01AC_SEMANTIC_TEST_VECTORS.md` (abbreviated **TV** below) exercises AC3 with the blocking paper
vector **TV246** — "An APPLIED replay with a corrupted payload is duplicate-suppressed before integrity
(AC3)" (**TV:36–43**). It names only `SetupRetryEvent`; its setup is a record that is `APPLIED` whose
genuine EventRef is replayed (`dispatched_event_ref = rec.seat_event_ref`) with corrupted payload fields;
its expected result is that "after ownership (step 3), the guard `IF rec.status != SEATED` fires (step 4,
BEFORE any payload-integrity handling) and returns `setup_retry_duplicate_suppressed(SetupRetryID)`. NO
`RoundAbort` occurs" (TV:41–43). This maps one-to-one onto the trace in §2 (PC:2122 → PC:2127–2128) and
the ordering established in §1. **Linkage holds.**

The adjacent vectors confirm the neighbouring guarantees the guard order depends on: TV247 (**TV:45–53**)
checks that a corrupted *historical* retry from `r1` is terminalised `SUPERSEDED` from the immutable
record and never aborts the later round `r2` (step 5, AC4), and TV248 (**TV:55–60**) checks that a genuine
owned SEATED record with an incomplete envelope takes the step-(6) integrity abort (AC5-C). The vector
file's coverage table records **TV246** under correction **AC3** against `SetupRetryEvent` (**TV:99**), and
every vector preserves the A1 baseline `8.420833333 kWh` (**TV:6, TV:108**).

---

## 6. Cross-document consistency

The AC3 statement is identical in substance across the pseudocode, the round state machine, and the
semantic test vectors.

| Document | Location | Consistency check |
|---|---|---|
| Pseudocode `EFFECTS` | PC:2104–2108 (declared order), PC:2112–2229 (implementation), PC:2237–2239 (NOTE) | Steps (1)–(8) with step (4) non-SEATED duplicate-suppress before step (6) payload validation — verified verbatim in §§1–3. |
| Pseudocode §0.8 addendum | PC:1003–1007 | "guard order: (1) structure … (4) IF status != SEATED -> setup_retry_duplicate_suppressed (BEFORE any payload-integrity abort); (5) stale/closed … (6) payload validation for a current owned SEATED record only … A replay of a terminal (APPLIED/SUPERSEDED/CANCELLED/ABORTED) record NEVER aborts a round." Matches the executable block. |
| Round state machine §3.10g (AC3) | `STAGE_01_ROUND_STATE_MACHINE.md:925–928` | "resolve the record → verify EventRef ownership → if `status != SEATED` return `setup_retry_duplicate_suppressed` (BEFORE any payload-integrity abort) → stale/closed disposition → payload validation for a current owned SEATED record only → target guards + execution. A replay of a terminal record never aborts a round because of differing replayed payload fields." Matches PC in substance. |
| Semantic test vectors | `STAGE_01AC_SEMANTIC_TEST_VECTORS.md:36–43, 99` | TV246 drives the AC3 order and asserts duplicate-suppress with no `RoundAbort`; coverage row ties TV246 → AC3 → `SetupRetryEvent`. Consistent. |

The chain pseudocode `EFFECTS` ↔ §0.8 AC3 addendum ↔ round-SM §3.10g (AC3) ↔ TV246 is coherent: one
canonical guard order, the non-SEATED replay check strictly before payload integrity, payload validation
scoped to a current owned SEATED record, and a terminal replay that can never abort a round. No document
contradicts another. AC3 is presented alongside its Stage-1AC siblings — the correction report, the
event-reference & dispatch audit, the stale-integrity scope audit, the retry-status transition audit, the
event-reference lifecycle audit, the procedure signature/call audit, the procedure call graph, the
semantic test vectors, the supersession register, the cross-document audit, and the checksum manifest — as
one committed deliverable set.

---

## 7. Result

**PASS** — AC3 fixes the `SetupRetryEvent` guard order. The executable `EFFECTS` block implements exactly
the eight declared steps (PC:2104–2229): (1) structure, (2) resolve, (3) EventRef ownership, (4) non-SEATED
terminal-replay duplicate-suppress, (5) stale/closed disposition from the immutable record, (6) payload
validation for a current owned SEATED record only, (7) current-round target guards, (8) target execution.
Step (4) (PC:2124–2128) precedes step (6) (PC:2153–2170), so a terminal-status replay with a corrupted
payload returns `setup_retry_duplicate_suppressed` (PC:2128) and never reaches any `RoundAbort` call site
(PC:2164 / 2175 / 2184 / 2193); payload fields (PC:2160–2161) are inspected only for a current owned SEATED
record. TV246 and the §3.10g / §0.8-AC3-addendum chain are consistent. This is a documentation-only audit;
the algorithm is **PoCol** with the idle policy within PoCol, and the A1 baseline `8.420833333 kWh` is
preserved.
