# Stage 1AD — Event-Payload Dispatch Audit (AD2)

This audit verifies correction **AD2 — the complete immutable payload is stored at seating and delivered verbatim at
dispatch**: `ScheduleEvent` captures the COMPLETE caller-supplied handler argument set as `record.immutable_payload` and
stores it in the ONE central `queued_event_record`, and `ProcessEventTime` dispatches `record.event_type` WITH
`immutable_payload = record.immutable_payload` (the STORED payload), so the payload seen at dispatch is identically the
payload captured at seating — never re-read from ambient globals and never patched from advanced global state. The audit was
generated AFTER the normative documents (`STAGE_01_PROTOCOL_PSEUDOCODE.md`, `STAGE_01_ROUND_STATE_MACHINE.md`,
`STAGE_01_TERMINOLOGY.md`) and the Stage-1AD semantic test vectors (`STAGE_01AD_SEMANTIC_TEST_VECTORS.md`, TV252–TV261) were
final; it reads them read-only and modifies nothing. The A1 baseline `8.420833333 kWh` is unchanged, and the binding PoCol
naming rule is preserved: the algorithm is **PoCol** and the mechanism under audit is the idle policy within PoCol.

Scope is documentation-only. Line anchors are approximate (`~L`). Quotes are reproduced verbatim from the current normative
documents; each check is corroborated by TV253 (`STAGE_01AD_SEMANTIC_TEST_VECTORS.md`, ~L31–L39), the vector that exercises
AD2. The completeness assertion is properly AD8's; it is cited only where it structurally guarantees the AD2 no-substitution
property, and the focus stays on AD2.

---

## Checks

| Check | Result |
|-------|--------|
| **C1.** The central record type declares `immutable_payload` as the COMPLETE caller-supplied handler arguments, fixed at seating. | **PASS** — `STRUCTURE queued_event_record` (`STAGE_01_PROTOCOL_PSEUDOCODE.md`, ~L501): `immutable_payload : the COMPLETE set of caller-supplied handler arguments for event_type (AD2), fixed at seating`. Corroborated by TV253 (~L34): the seat stores `record.immutable_payload =` the complete argument set. |
| **C2.** `ScheduleEvent` captures `immutable_payload` = the COMPLETE caller-supplied argument set for `event_type`, and for `SetupRetryEvent` exactly the seven fields. | **PASS** — `PROCEDURE ScheduleEvent` (~L571–573): `SET immutable_payload <- the COMPLETE caller-supplied argument set for event_type (from envelope_fields), e.g. for … SetupRetryEvent EXACTLY { RoundID, setup_kind, SetupRetryID, TemplateID_at_seat, TemplateRefreshSetupID, retry_generation, reason }`. The seven fields match TV253 (~L34–35) verbatim. |
| **C3.** The captured payload is stored inside the ONE central `queued_event_record` and registered under its `EventRef`. | **PASS** — `ScheduleEvent` (~L580–582): `SET record <- queued_event_record(event_ref = event_ref, event_type = event_type, dispatch_envelope = dispatch_envelope, immutable_payload = immutable_payload, queue_status = QUEUED)` then `SET queued_event_registry[event_ref] <- record`. TV253 (~L34) asserts the seat stores the complete set as `record.immutable_payload`. |
| **C4.** `ProcessEventTime` binds the record from the central registry (the STORED record), not from ambient state. | **PASS** — `PROCEDURE ProcessEventTime` (~L212): `SET record <- queued_event_registry[er]  # AD1: the ONE central authoritative record`. TV253 (~L37) drives dispatch through this stored record. |
| **C5.** `ProcessEventTime` dispatches `record.event_type` WITH `immutable_payload = record.immutable_payload`, so payload at dispatch = payload at seating (not re-read from globals). | **PASS** — `ProcessEventTime` (~L233–236): `deliver the STORED immutable_payload (payload at dispatch = payload at seating)` … `DISPATCH record.event_type WITH immutable_payload = record.immutable_payload, dispatch_envelope = ctx.dispatch_envelope`. Matches TV253 Expected (~L37–38): dispatched `WITH immutable_payload = record.immutable_payload` even though ambient `RoundID_current` / `TemplateID_committed` advanced between seating and dispatch. |
| **C6.** `SetupRetryEvent`'s INPUTS take the payload from the STORED `immutable_payload` (AD2), not from current global state. | **PASS** — `PROCEDURE SetupRetryEvent` INPUTS (~L2241–2244): `# AD2: the payload fields below are delivered as the STORED immutable_payload of the dispatched queued_event_record (payload at dispatch = payload at seating)`, over `RoundID, setup_kind, SetupRetryID, TemplateID_at_seat, TemplateRefreshSetupID, retry_generation, reason`. TV253 (~L38–39): `SetupRetryEvent reads its TemplateID_at_seat etc. from the stored payload, not from the advanced ambient state`. |
| **C7.** The stale / closed-round disposition is decided from the IMMUTABLE RECORD fields, so a stale field is never silently replaced by the advanced ambient value. | **PASS** — `SetupRetryEvent` (~L2283–2287): `AC4 STALE / CLOSED-ROUND DISPOSITION decided from the IMMUTABLE RECORD FIELDS (never the untrusted payload)`, e.g. `IF rec.RoundID != RoundID_current`. Corroborates TV253 (~L39): `a stale field cannot be substituted with current globals`. |
| **C8.** Dispatch never substitutes a missing field with a current global value; completeness is enforced at construction (AD8 tie-in that structurally guarantees the AD2 no-substitution property). | **PASS** — `ScheduleEvent` (~L567–574): the capture is `not a substitution with current global values`, closed by `ASSERT immutable_payload contains EVERY required field of the declared payload schema for event_type` (AD8: reject incomplete construction). Because no incomplete record is ever registered, dispatch has no missing field to fill from globals — TV253 (~L38–39); AD8 reinforcement in TV259 (~L100–101). |
| **C9.** AD2 is stated identically in the round-state machine and the terminology (cross-document corroboration). | **PASS** — `STAGE_01_ROUND_STATE_MACHINE.md` §3.10h (~L972–976): `ProcessEventTime dispatches record.event_type with record.immutable_payload and the record's OrdinaryDispatchContext; the payload at dispatch is identically the payload at seating`; `STAGE_01_TERMINOLOGY.md` (~L1094–1097): `delivered verbatim by ProcessEventTime at dispatch — payload at dispatch equals payload at seating`. Both agree with TV253 (~L37–38). |

---

## Result

All nine checks PASS with no inconsistency. The pseudocode establishes a single seating-to-dispatch payload lock: `ScheduleEvent`
captures the COMPLETE caller-supplied argument set — for `SetupRetryEvent` exactly `RoundID, setup_kind, SetupRetryID,
TemplateID_at_seat, TemplateRefreshSetupID, retry_generation, reason` — into `record.immutable_payload` of the ONE central
`queued_event_record` (~L571–582), and `ProcessEventTime` dispatches that STORED payload verbatim via `DISPATCH record.event_type
WITH immutable_payload = record.immutable_payload` (~L236). `SetupRetryEvent` reads its fields from that delivered stored payload
(~L2241–2244) and decides stale/closed dispositions from the immutable record rather than advanced ambient state (~L2283–2287),
so a field frozen at seating can never be re-read from or overwritten by current globals at dispatch. The AD8 construction-time
completeness assert (~L574) removes the only avenue by which a missing field could otherwise be back-filled from global state,
making the AD2 no-substitution guarantee structural rather than incidental. The round-state machine (§3.10h) and terminology
addendum restate AD2 in the same terms, and TV253 exercises exactly this path. The A1 baseline `8.420833333 kWh` and the binding
PoCol naming rule (algorithm PoCol; mechanism the idle policy within PoCol) are preserved throughout.
