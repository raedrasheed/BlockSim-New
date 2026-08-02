# Stage-1AH Audit — AH8 Event-Ordering Root (single authoritative queue tie key)

**Audit target (AH8).** The ONLY authoritative queue tie key is
`descriptor(event_type).stable_tie_key(immutable_payload)`. Every surviving *positive* generic
`(CandidateID, MinerID, AssignmentID)` / `(CandidateID, MinerID, AssignmentID, seq)` ordering rule
must be withdrawn; the acceptance VALUE selection (`candidate_hash` then `MinerID`, D6) is a separate
winner arbitration and must be kept, clearly distinct from the queue ordering key.

**Scope.** Documentation-only pseudocode revision. Algorithm is always **PoCol**; the mechanism is
**the idle policy within PoCol**. The A1 energy baseline **`8.420833333 kWh`** is unchanged (no
numeric/energy claim is touched by this ordering-key audit). Inspection covered ONLY the final
normative tree:

- `STAGE_01_PROTOCOL_PSEUDOCODE.md`
- `STAGE_01_INVARIANT_CATALOGUE.md`
- `STAGE_01_TERMINOLOGY.md`
- `STAGE_01_ROUND_STATE_MACHINE.md`

All paths below are under
`/home/user/blocksim-v45-stage1ah/docs/thesis_revision_v45/stage_01/`.

---

## 1. Per-occurrence classification

Every occurrence of the 3-field `(CandidateID, MinerID, AssignmentID)` and the 4-field
`(CandidateID, MinerID, AssignmentID, seq)` strings (including the `[, seq]` bracketed form and the
one line-wrapped occurrence) across the four files. Classification: **NEGATIVE/historical** = states
the tuple is NOT authoritative / is WITHDRAWN / is being replaced (acceptable); **POSITIVE-DEFECT** =
asserts the tuple as an authoritative ordering key (a defect).

| # | file:line | Context (verbatim gist) | Classification |
|---|-----------|--------------------------|----------------|
| 1 | `STAGE_01_PROTOCOL_PSEUDOCODE.md:79` | §0.2: "There is NO universal `(CandidateID, MinerID, AssignmentID)` tie key (that AA-era claim is WITHDRAWN …)" | NEGATIVE |
| 2 | `STAGE_01_PROTOCOL_PSEUDOCODE.md:169-170` | §0.7-H2: "… NEVER by a universal `(CandidateID, MinerID, AssignmentID[, seq])` tuple (that AA-era generic rule is WITHDRAWN …)" (tuple wraps 169→170) | NEGATIVE |
| 3 | `STAGE_01_PROTOCOL_PSEUDOCODE.md:856` | ScheduleEvent step (3d) comment: "This replaces the generic (CandidateID, MinerID, AssignmentID) ordering tuple with the exact per-descriptor tie key" | NEGATIVE |
| 4 | `STAGE_01_PROTOCOL_PSEUDOCODE.md:883` | EQ INSERT comment: "AF3: descriptor-derived stable_tie_key (NOT the generic (CandidateID, MinerID, AssignmentID) tuple)" | NEGATIVE |
| 5 | `STAGE_01_PROTOCOL_PSEUDOCODE.md:1104` | descriptor field def `stable_tie_key`: "… ONLY (never the generic (CandidateID, MinerID, AssignmentID) tuple)" | NEGATIVE |
| 6 | `STAGE_01_PROTOCOL_PSEUDOCODE.md:7059` | Deterministic-vs-sampling summary: "… NOT a universal `(CandidateID, MinerID, AssignmentID[, seq])` tuple, that AA-era generic rule is WITHDRAWN" | NEGATIVE |
| 7 | `STAGE_01_PROTOCOL_PSEUDOCODE.md:7130` | §21 Intra-type tie-break: "There is NO universal `(CandidateID, MinerID, AssignmentID[, seq])` tuple (that AA-era generic rule is WITHDRAWN …)" | NEGATIVE |
| 8 | `STAGE_01_INVARIANT_CATALOGUE.md:493` | AG8 clause: "… the universal `(CandidateID, MinerID, AssignmentID)` tie key is withdrawn." | NEGATIVE |
| 9 | `STAGE_01_INVARIANT_CATALOGUE.md:514` | AH8 clause: "… every surviving positive `(CandidateID, MinerID, AssignmentID[, seq])` ordering rule is removed …" | NEGATIVE |
| 10 | `STAGE_01_INVARIANT_CATALOGUE.md:724` | Stage-1AH clause: "… the universal `(CandidateID, MinerID, AssignmentID[, seq])` tuple is WITHDRAWN everywhere (§0.2, §0.7-H2, §21, and the companion documents) …" | NEGATIVE |
| 11 | `STAGE_01_TERMINOLOGY.md:203` | delta_cycle entry: "The H2-era universal `stable_tie_key = (CandidateID, MinerID, AssignmentID)` is WITHDRAWN (AG8)" | NEGATIVE |
| 12 | `STAGE_01_TERMINOLOGY.md:1214` | Descriptor-derived ordering rule (AG8): "The universal `(CandidateID, MinerID, AssignmentID)` tie key is withdrawn …" | NEGATIVE |
| 13 | `STAGE_01_TERMINOLOGY.md:1261` | Descriptor-derived ordering key (AH8): "AH8 removes every SURVIVING positive `(CandidateID, MinerID, AssignmentID[, seq])` ordering rule (§0.7-H2, the deterministic-vs-sampling summary, §21, and the companion documents)." | NEGATIVE |
| 14 | `STAGE_01_ROUND_STATE_MACHINE.md:185` | "Same-timestamp event order (authoritative …)" bullet: "… intra-microphase ties break by `(CandidateID, MinerID, AssignmentID, seq)` — never by iteration order." | **POSITIVE-DEFECT** |
| 15 | `STAGE_01_ROUND_STATE_MACHINE.md:1119` | AF3 clause: "The EQ insert orders by the descriptor-derived `stable_tie_key`, never the generic `(CandidateID, MinerID, AssignmentID)` tuple." | NEGATIVE |
| 16 | `STAGE_01_ROUND_STATE_MACHINE.md:1210` | AG8 clause: "… the universal `(CandidateID, MinerID, AssignmentID)` claim is withdrawn." | NEGATIVE |

**Tally:** 16 occurrences — 15 NEGATIVE/historical (acceptable), **1 POSITIVE-DEFECT**.

---

## 2. Sites AH8 must have corrected (now descriptor-derived?)

| Correction site | Location | Reads descriptor-derived? | Result |
|-----------------|----------|---------------------------|--------|
| §0.7-H2 within-microphase tie statement | `STAGE_01_PROTOCOL_PSEUDOCODE.md:167-171` | "AH8: within a microphase, ties break by the ONE authoritative ordering key — the descriptor-derived `stable_tie_key = descriptor(event_type).stable_tie_key(immutable_payload)` then `seq` … NEVER by a universal `(…)` tuple (WITHDRAWN)" | PASS |
| Deterministic-vs-sampling summary | `STAGE_01_PROTOCOL_PSEUDOCODE.md:7056-7060` | queue ORDERING key is "the descriptor-derived `stable_tie_key(immutable_payload)` then `seq` (AH8, per event type — NOT a universal `(…)` tuple, WITHDRAWN)" | PASS |
| §21 "Intra-type tie-break" | `STAGE_01_PROTOCOL_PSEUDOCODE.md:7127-7135` | "Events of the SAME type … ordered by the ONE authoritative ordering key — the descriptor-derived `stable_tie_key = descriptor(event_type).stable_tie_key(immutable_payload)` then `seq` … There is NO universal `(…)` tuple (WITHDRAWN)" | PASS |
| Companion invariant statement | `STAGE_01_INVARIANT_CATALOGUE.md:513-515, 722-725` | "the ONE authoritative queue tie key is the descriptor-derived `stable_tie_key`; every surviving positive `(…)` ordering rule is removed" | PASS |
| Companion terminology statement | `STAGE_01_TERMINOLOGY.md:1259-1263` | "The ONE authoritative queue tie key remains `stable_tie_key = descriptor(event_type).stable_tie_key(immutable_payload)`; AH8 removes every SURVIVING positive `(…)` ordering rule" | PASS |
| Companion round-state statement | `STAGE_01_ROUND_STATE_MACHINE.md:184-185` | **NO** — the "Same-timestamp event order (authoritative)" bullet still asserts "intra-microphase ties break by `(CandidateID, MinerID, AssignmentID, seq)`" instead of the descriptor-derived key | **FAIL** |

The AF3 and AG8 clauses elsewhere in the round-state document (`:1119`, `:1210`) ARE corrected;
only the §0.7-H2-echoing authoritative bullet at `:185` was missed.

---

## 3. Acceptance VALUE selection kept & clearly separate (D6)

| Check | Evidence | Result |
|-------|----------|--------|
| `candidate_hash` then `MinerID` (D6) retained | `STAGE_01_PROTOCOL_PSEUDOCODE.md:6329-6330` ("select the winner deterministically: smallest candidate_hash, then smallest MinerID (D6/G7)"; `winner <- argmin …`) | PASS |
| Stated as SEPARATE winner arbitration, not the queue key | `STAGE_01_PROTOCOL_PSEUDOCODE.md:6353-6355` ("Acceptance VALUE selection (candidate_hash then MinerID) is DISTINCT from the queue ordering key (AH8): it is the winner arbitration, not the event tie-break"); `:7056-7058`; `:7133-7134` ("that is winner selection, not the queue ordering key") | PASS |
| Distinction echoed in companions | `STAGE_01_INVARIANT_CATALOGUE.md:515` and `:725`; `STAGE_01_TERMINOLOGY.md:1262` (all: "kept separate / distinct — winner arbitration, not a queue key") | PASS |

---

## 4. ScheduleEvent EQ INSERT & §0.2

| Check | Evidence | Result |
|-------|----------|--------|
| §0.2 states `stable_tie_key = descriptor(event_type).stable_tie_key(immutable_payload)` | `STAGE_01_PROTOCOL_PSEUDOCODE.md:76-79` ("AG8: the ONE authoritative ordering rule — `stable_tie_key = descriptor(event_type).stable_tie_key(immutable_payload)` … There is NO universal `(CandidateID, MinerID, AssignmentID)` tie key") | PASS |
| ScheduleEvent derives `tie_key` from the descriptor | `STAGE_01_PROTOCOL_PSEUDOCODE.md:862` (`SET tie_key <- d.stable_tie_key(immutable_payload)`) plus the unavailability guard `:859-861` (`rejected_stable_tie_key_unavailable`) | PASS |
| EQ INSERT orders by that descriptor-derived tie_key | `STAGE_01_PROTOCOL_PSEUDOCODE.md:883` (`INSERT event_ref INTO EQ.event_queue ORDERED BY (event_time, delta_cycle, microphase, tie_key, seq)  # descriptor-derived stable_tie_key (NOT the generic tuple)`) | PASS |

---

## 5. Checked-item summary

| Item | Description | Result |
|------|-------------|--------|
| 1 | All tuple occurrences classified; every occurrence either NEGATIVE/historical or a POSITIVE-DEFECT | **FAIL** (1 POSITIVE-DEFECT at `STAGE_01_ROUND_STATE_MACHINE.md:185`) |
| 2 | §0.7-H2 within-microphase tie statement reads descriptor-derived | PASS |
| 2 | Deterministic-vs-sampling summary reads descriptor-derived | PASS |
| 2 | §21 "Intra-type tie-break" reads descriptor-derived | PASS |
| 2 | Companion invariant statement reads descriptor-derived | PASS |
| 2 | Companion terminology statement reads descriptor-derived | PASS |
| 2 | Companion round-state statement reads descriptor-derived | **FAIL** (`STAGE_01_ROUND_STATE_MACHINE.md:185`) |
| 3 | Acceptance VALUE selection (`candidate_hash` then `MinerID`, D6) kept & stated as separate winner arbitration | PASS |
| 4 | §0.2 states `stable_tie_key = descriptor(event_type).stable_tie_key(immutable_payload)`; ScheduleEvent EQ INSERT orders by the descriptor-derived tie_key | PASS |

---

## 6. Defect detail (for fixing)

- **`STAGE_01_ROUND_STATE_MACHINE.md:185`** — Inside the bullet headed "Same-timestamp event order
  (**authoritative**: `STAGE_01G_EVENT_MICROPHASE_SPEC.md`, extended by the H2 delta-cycle rule and
  the I-01/I-02 epilogue)" (bullet begins at `:176`), the text reads:
  *"… intra-microphase ties break by `(CandidateID, MinerID, AssignmentID, seq)` — never by iteration
  order."* This is a **surviving positive generic tie-key rule**: it names the withdrawn 4-field
  tuple as the authoritative within-microphase ordering key. Per AH8 it must instead read the
  descriptor-derived key, e.g. *"intra-microphase ties break by the ONE authoritative ordering key —
  the descriptor-derived `stable_tie_key = descriptor(event_type).stable_tie_key(immutable_payload)`
  then `seq` — never by the withdrawn `(CandidateID, MinerID, AssignmentID[, seq])` tuple and never by
  iteration order."* The `never by iteration order` clause only excludes iteration order; it does
  **not** withdraw the tuple, so the occurrence remains positive.

---

## Overall verdict

**PASS (after fold-back correction).**

One surviving positive generic tie-key rule was found and has been FIXED in the final normative tree:

- `STAGE_01_ROUND_STATE_MACHINE.md` (the authoritative "Same-timestamp event order" bullet) previously asserted
  intra-microphase ties break by the withdrawn `(CandidateID, MinerID, AssignmentID, seq)` tuple. **FIXED:** the bullet
  now reads that intra-microphase ties break by the ONE authoritative ordering key — the descriptor-derived
  `stable_tie_key = descriptor(event_type).stable_tie_key(immutable_payload)` then `seq` — and explicitly marks the
  universal `(CandidateID, MinerID, AssignmentID[, seq])` tuple WITHDRAWN (STAGE_01AH_SUPERSESSION_REGISTER.md). After
  the fold-back this occurrence is NEGATIVE/withdrawn, matching the other companion clauses.

All other tuple occurrences are NEGATIVE/historical (withdrawn/replaced) and acceptable; §0.2,
§0.7-H2 (pseudocode), the deterministic-vs-sampling summary, §21, the ScheduleEvent EQ INSERT, and the
companion invariant/terminology statements all correctly read descriptor-derived; the acceptance
VALUE selection (`candidate_hash` then `MinerID`, D6) is kept and clearly stated as a separate winner
arbitration. Algorithm **PoCol**; mechanism **the idle policy within PoCol**; A1 baseline
`8.420833333 kWh` unchanged.
