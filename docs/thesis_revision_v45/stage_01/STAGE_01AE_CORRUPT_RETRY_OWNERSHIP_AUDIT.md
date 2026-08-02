# Stage 1AE — Corrupt Retry Ownership Audit (AE6)

This audit verifies correction **AE6 — corrupt retry ownership bound by EventRef**. AE6 requires that a corrupt
`SetupRetryEvent` reaching the dispatcher's defensive integrity path have its owning retry record resolved from the IMMUTABLE
reverse binding `setup_retry_by_seat_event_ref : EventRef → SetupRetryID` — keyed by the TRUSTED dispatched `EventRef` and
verified against the record's `seat_event_ref` — NEVER from the corrupt payload's `SetupRetryID`. A missing payload id must
still resolve the owner from the EventRef; a payload naming a foreign valid id must leave that foreign record untouched (the
mismatch audited); an event with no reverse-bound owner must mutate nothing beyond recording the failure. A corrupt payload
may never choose which retry record is aborted. The audit was generated AFTER the normative documents
(`STAGE_01_PROTOCOL_PSEUDOCODE.md`, `STAGE_01_ROUND_STATE_MACHINE.md`, `STAGE_01_TERMINOLOGY.md`) and the Stage-1AE semantic
test vectors (`STAGE_01AE_SEMANTIC_TEST_VECTORS.md`, TV262–TV272) were final; it reads them read-only and modifies nothing.
The A1 baseline `8.420833333 kWh` is unchanged, and the binding PoCol naming rule is preserved: the algorithm is **PoCol** and
the mechanism under audit is the idle policy within PoCol.

Scope is documentation-only. Line anchors are approximate (`~L`) and refer to `STAGE_01_PROTOCOL_PSEUDOCODE.md` unless another
document is named. Quotes are reproduced verbatim from the current normative documents. AE6 checks are corroborated by TV267
(`STAGE_01AE_SEMANTIC_TEST_VECTORS.md`, ~L59–68) — the MISSING-id case — and TV268 (~L70–77) — the FOREIGN-id case.

---

## Declaration and atomic publication of the reverse binding

The reverse binding is declared as an empty map at run initialisation and published ATOMICALLY, together with the
`setup_retry_record`, at BOTH retry seating sites. It is never mutated after the seat (immutable reverse binding).

| Site | Grounding quote | ~L |
|------|-----------------|-----|
| **`RunInitialise` (empty-map init).** | `INITIALISE setup_retry_by_seat_event_ref <- empty map   # AE6: EventRef -> SetupRetryID (IMMUTABLE reverse binding; corrupt-retry owner is resolved from the trusted seat EventRef, never the payload)` | ~L1921 |
| **`PrepareParticipantsForNewRound` — PARTICIPANT_SETUP seat.** Inside `ATOMICALLY:` with `SET setup_retry_records[srid] <- setup_retry_record(… seat_event_ref = event_ref, status = SEATED …)`. | `SET setup_retry_by_seat_event_ref[event_ref] <- srid              # AE6: IMMUTABLE reverse binding published with the record` | ~L2223–2228 |
| **`ContinueTemplateRefreshAssignmentSetup` — TEMPLATE_REFRESH_SETUP seat.** Inside `ATOMICALLY:` with `SET setup_retry_records[srid] <- setup_retry_record(… seat_event_ref = event_ref, status = SEATED …)`. | `SET setup_retry_by_seat_event_ref[event_ref] <- srid              # AE6: IMMUTABLE reverse binding published with the record` | ~L5724–5729 |

Both publishes sit inside an `ATOMICALLY:` block that also writes `setup_retry_records[srid]` with `seat_event_ref = event_ref`
(~L2223–2228, ~L5724–5729), so the forward record and its reverse binding commit both-or-neither — the binding can never lag
or diverge from the record it indexes.

---

## The three corrupt-payload cases

`HandleDispatchIntegrityFailure` (`~L318–367`) is entered from `ProcessEventTime` ONLY when a registry entry is detected
corrupt (`IF record is detected corrupt … CALL HandleDispatchIntegrityFailure(RoundContext, er, record)`, ~L237–238). For a
`SetupRetryEvent` it resolves the owner from the trusted `er` and asserts the binding, before any of the three cases branches:
`SET owner_id <- setup_retry_by_seat_event_ref[er]` … `ASSERT setup_retry_records[owner_id] EXISTS AND
setup_retry_records[owner_id].seat_event_ref = er` (~L336–337).

| Case | Behaviour (as written) | Grounding quote | ~L |
|------|------------------------|-----------------|-----|
| **Missing `SetupRetryID` in the corrupt payload.** | Owner is still resolved from the trusted `er`; the missing payload id is never consulted. The record then disposes per its own round (see the owner-disposition scope below). | `IF er is a key of setup_retry_by_seat_event_ref:` / `SET owner_id <- setup_retry_by_seat_event_ref[er]                                      # AE6: owner from the TRUSTED er` … `A MISSING payload SetupRetryID is fine: the owner is still resolved from er.` | ~L335–340 |
| **Corrupt payload NAMES a foreign valid `SetupRetryID` (`!= owner_id`).** | Owner is resolved from `er`; the mismatch is audited via `setup_retry_owner_mismatch`; the FOREIGN record is NOT touched; ONLY the actual owner (from `er`) is dispositioned. | `IF the payload's SetupRetryID is PRESENT AND the payload's SetupRetryID != owner_id:` / `RECORD setup_retry_owner_mismatch(er, owner_id, payload_setup_retry_id = the payload's SetupRetryID)   # AE6: foreign id IGNORED` | ~L341–342 |
| **NO EventRef owner (`er` not in the reverse map).** | Record the integrity failure `dispatch_integrity_no_owner(er)`; `ProcessEventTime` marks the queued event `CONSUMED`; do NOT mutate ANY unrelated retry record. | `ELSE:` / `RECORD dispatch_integrity_no_owner(er)` and, in `ProcessEventTime`, `SET queued_event_registry[er].queue_status <- CONSUMED  # AD4: DISPATCHING -> CONSUMED (the corrupt event is drained, never re-QUEUED)` | ~L355–358 / ~L239 |

In every case the payload's `SetupRetryID` is used for AUDIT ONLY (the `setup_retry_owner_mismatch` record, ~L342). It is
never used as a lookup key, a disposition target, or a branch selector — the disposition acts exclusively on `owner_id` /
`rec` (`SET rec <- setup_retry_records[owner_id]`, ~L343).

### Owner disposition scopes the abort to the owner's own round

Once the owner is resolved from `er`, the disposition is scoped to that owner's round — the corrupt event can only affect its
own owner, and only within that owner's round.

| Owner state | Behaviour (as written) | Grounding quote | ~L |
|-------------|------------------------|-----------------|-----|
| **SEATED, current, nonterminal round.** | `SEATED → APPLYING → ABORTED` via a current-round `RoundAbort` carrying the COMPLETE `integrity_envelope` built from the trusted EventRef (never the corrupt one). | `IF rec.status = SEATED AND rec.RoundID = RoundID_current AND round_state NOT in {ROUND_ACCEPTED, ROUND_ABORTED}:` / `CALL SetSetupRetryStatus(owner_id, APPLYING)` / `SET disp <- CALL RoundAbort(RoundContext, reason = setup_retry_payload_integrity_failure(SetupRetryEvent), dispatch_envelope = integrity_envelope, recovery_finalising = false)` / `CALL SetSetupRetryStatus(owner_id, ABORTED)` | ~L344–349 |
| **SEATED, older / terminal round.** | `SUPERSEDED` WITHOUT aborting the current round. | `ELSE IF rec.status = SEATED:` / `CALL SetSetupRetryStatus(owner_id, SUPERSEDED)` / `UPDATE setup_retry_records[owner_id].target_disposition <- setup_retry_stale_noop(owner_id)` | ~L350–353 |
| **Non-SEATED owner.** | Already terminal — left unchanged. | `# a non-SEATED owner is already terminal — left unchanged (AC7)` | ~L354 |

The abort's transition identity is the trusted `integrity_envelope = { envelope_namespace = er.envelope_namespace,
event_time = er.event_time, delta_cycle = er.delta_cycle, event_seq = er.seq, hook_id = null }` (~L329–330), so a malformed
untrusted envelope never becomes the round-closure identity.

---

## Checks

| Check | Result |
|-------|--------|
| **C1.** `setup_retry_by_seat_event_ref` is declared as an empty map at run initialisation, typed `EventRef → SetupRetryID`, labelled the IMMUTABLE reverse binding. | **PASS** — `RunInitialise` (~L1921): `INITIALISE setup_retry_by_seat_event_ref <- empty map   # AE6: EventRef -> SetupRetryID (IMMUTABLE reverse binding; corrupt-retry owner is resolved from the trusted seat EventRef, never the payload)`. Cross-checked by §3.10i AE6 (`STAGE_01_ROUND_STATE_MACHINE.md`, ~L1060–1065) and the terminology addendum (`STAGE_01_TERMINOLOGY.md`, ~L1122–1125). |
| **C2.** The binding is published ATOMICALLY with the `setup_retry_record` at the PARTICIPANT_SETUP seat. | **PASS** — `ATOMICALLY:` block (~L2223–2228) writes `setup_retry_records[srid] <- setup_retry_record(… seat_event_ref = event_ref, status = SEATED …)` then `SET setup_retry_by_seat_event_ref[event_ref] <- srid              # AE6: IMMUTABLE reverse binding published with the record`. Both commit both-or-neither. |
| **C3.** The binding is published ATOMICALLY with the `setup_retry_record` at the TEMPLATE_REFRESH_SETUP seat. | **PASS** — `ATOMICALLY:` block (~L5724–5729) writes `setup_retry_records[srid] <- setup_retry_record(… seat_event_ref = event_ref, status = SEATED …)` then `SET setup_retry_by_seat_event_ref[event_ref] <- srid              # AE6: IMMUTABLE reverse binding published with the record`. |
| **C4.** `HandleDispatchIntegrityFailure` resolves `owner_id` from `setup_retry_by_seat_event_ref[er]` (the TRUSTED dispatched EventRef), never from the corrupt payload's `SetupRetryID`. | **PASS** — `HandleDispatchIntegrityFailure` (~L331–336): `resolve the OWNER from the IMMUTABLE reverse binding keyed by the trusted EventRef (setup_retry_by_seat_event_ref[er], published atomically at seating) — NEVER from the corrupt payload's SetupRetryID.` then `SET owner_id <- setup_retry_by_seat_event_ref[er]`. TV267 Expected (~L65): `resolves owner_id <- setup_retry_by_seat_event_ref[er]`. |
| **C5.** It asserts `setup_retry_records[owner_id].seat_event_ref = er` (verifies the binding against the record). | **PASS** — (~L337): `ASSERT setup_retry_records[owner_id] EXISTS AND setup_retry_records[owner_id].seat_event_ref = er   # AE6: verify the binding`. TV267 Expected (~L65–66): `asserts setup_retry_records[owner_id].seat_event_ref = er`. |
| **C6 (missing id).** A MISSING payload `SetupRetryID` still resolves the owner from `er`; the missing id is never needed. | **PASS** — the resolution at ~L336–337 does not read the payload; the NOTE (~L338–340): `A MISSING payload SetupRetryID is fine: the owner is still resolved from er.` TV267 (~L62–68): the payload `is MISSING its SetupRetryID`, yet `the missing payload id is never needed`. |
| **C7 (foreign id).** A corrupt payload naming a foreign valid `SetupRetryID` leaves that foreign record UNTOUCHED, the mismatch is audited (`setup_retry_owner_mismatch`), and only the actual owner (from `er`) is dispositioned. | **PASS** — (~L338–342): `if the corrupt payload happens to NAME a different (foreign) SetupRetryID, DO NOT touch that foreign record — audit the mismatch and disposition ONLY the actual owner resolved from er.` then `RECORD setup_retry_owner_mismatch(er, owner_id, payload_setup_retry_id = the payload's SetupRetryID)   # AE6: foreign id IGNORED`. TV268 Expected (~L75–77): `the mismatch is audited (setup_retry_owner_mismatch); the FOREIGN record foreign_id is NOT touched; only owner_id is dispositioned.` |
| **C8 (current owner abort).** A current nonterminal-round SEATED owner terminalises `SEATED → APPLYING → ABORTED` via `RoundAbort(dispatch_envelope = integrity_envelope)`. | **PASS** — (~L344–349): the `SEATED AND rec.RoundID = RoundID_current AND round_state NOT in {ROUND_ACCEPTED, ROUND_ABORTED}` branch calls `SetSetupRetryStatus(owner_id, APPLYING)`, `RoundAbort(… dispatch_envelope = integrity_envelope …)`, `SetSetupRetryStatus(owner_id, ABORTED)`. TV267 Expected (~L66–68): `terminalises ONLY that record (SEATED → APPLYING → ABORTED via a current-round RoundAbort with the complete integrity envelope).` |
| **C9 (old/terminal owner).** An older/terminal-round SEATED owner is set `SUPERSEDED` WITHOUT aborting the current round; a non-SEATED owner is left unchanged. | **PASS** — (~L350–354): `ELSE IF rec.status = SEATED:` → `CALL SetSetupRetryStatus(owner_id, SUPERSEDED)` with `owner belongs to an older / terminal round -> terminalise WITHOUT aborting the current round (AC4/AD8)`; `# a non-SEATED owner is already terminal — left unchanged (AC7)`. |
| **C10 (no owner).** With no reverse-bound owner, record `dispatch_integrity_no_owner(er)`; `ProcessEventTime` marks the event `CONSUMED`; no unrelated retry is mutated. | **PASS** — (~L355–358): `ELSE:` → `RECORD dispatch_integrity_no_owner(er)` with `NO EventRef owner exists (er not in the reverse binding). Record the integrity failure; ProcessEventTime CONSUMES the queued event; do NOT mutate ANY unrelated retry record.` `ProcessEventTime` (~L239): `SET queued_event_registry[er].queue_status <- CONSUMED`. |
| **C11 (no victim choice).** A corrupt payload can NEVER choose which retry record is aborted. | **PASS** — the payload `SetupRetryID` appears only in the audit `RECORD setup_retry_owner_mismatch(…)` (~L342); disposition acts solely on `owner_id` / `rec` resolved from `er` (`SET rec <- setup_retry_records[owner_id]`, ~L343). NOTE (~L361–367): `the owner is resolved from the trusted EventRef via setup_retry_by_seat_event_ref (verified against seat_event_ref), never from the corrupt payload — a corrupt payload naming a FOREIGN SetupRetryID leaves that foreign record untouched (mismatch audited) and an event with NO reverse-bound owner mutates nothing.` TV268 Expected (~L77): `A corrupt payload never chooses which retry record is aborted.` |
| **C12 (corroborating — well-formed path).** Even the ordinary (non-corrupt) `SetupRetryEvent` handler binds ownership by the trusted EventRef, not the payload id, so no dispatch path lets a payload `SetupRetryID` select a victim. | **PASS** — `SetupRetryEvent` handler (~L2405–2409): `IF dispatched_event_ref != rec.seat_event_ref:` → `RETURN setup_retry_stale_noop(SetupRetryID)   # AC5-B: foreign/replayed dispatch; genuine event remains seated`, i.e. `a foreign / replayed event carries a valid SetupRetryID but a DIFFERENT EventRef: it does NOT own the record`. |

---

## FAIL scan

No path was found where the corrupt payload's `SetupRetryID` influences which record is aborted. The only read of the payload
`SetupRetryID` in `HandleDispatchIntegrityFailure` is the mismatch AUDIT record (~L341–342), which explicitly touches no
record; the disposition target is `owner_id` resolved from the trusted `er` (~L336) and verified against `seat_event_ref`
(~L337). The ordinary handler (C12) independently gates on `dispatched_event_ref != rec.seat_event_ref` (~L2408). There is no
FAIL to report.

---

## Result

AE6 is fully and consistently specified across the three normative documents. The reverse binding
`setup_retry_by_seat_event_ref : EventRef → SetupRetryID` is declared empty at `RunInitialise` (~L1921) and published
atomically alongside the `setup_retry_record` at both the PARTICIPANT_SETUP (~L2223–2228) and TEMPLATE_REFRESH_SETUP
(~L5724–5729) seats. `HandleDispatchIntegrityFailure` resolves the corrupt-event owner exclusively from the trusted dispatched
`er` and asserts the binding against `seat_event_ref` (~L336–337); a missing payload id still resolves the owner (C6), a
foreign named id is audited and leaves the foreign record untouched (C7/TV268), and an event with no reverse-bound owner
records `dispatch_integrity_no_owner` and is consumed with no unrelated mutation (C10). The owner disposition is scoped to the
owner's own round — current nonterminal → `SEATED → APPLYING → ABORTED` with the complete integrity envelope (C8/TV267);
old/terminal → `SUPERSEDED` without aborting the current round (C9). A corrupt payload can never choose which retry record is
aborted (C11), corroborated by the well-formed handler's EventRef-ownership gate (C12). All twelve checks PASS; there is no
FAIL. The A1 baseline `8.420833333 kWh` is preserved, and the PoCol naming rule is intact: the algorithm is PoCol and the
mechanism audited is the idle policy within PoCol.
