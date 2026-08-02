# Stage 1AE — Structured Payload-Schema Rejection + Atomic Registration Audit (corrections AE7, AE8)

This is a documentation-only audit of corrections **AE7** (structured payload-schema rejection) and **AE8** (atomic
registration) in the Stage-1 formal specification of **PoCol** and the idle policy within PoCol. It was generated AFTER
the normative documents were final — `STAGE_01_PROTOCOL_PSEUDOCODE.md` PROCEDURE `ScheduleEvent` (the AE7 payload
validation, the AE8 `ATOMICALLY` block, and the RETURNS union) and its result-binding callers;
`STAGE_01_ROUND_STATE_MACHINE.md` §3.10i AE7/AE8; `STAGE_01_INVARIANT_CATALOGUE.md` I21 — and the Stage-1AE semantic
test vectors (`STAGE_01AE_SEMANTIC_TEST_VECTORS.md`, TV269) were frozen. It modifies no specification document and
quotes the current lines of the frozen source of truth. The A1 baseline `8.420833333 kWh` is unchanged (I21 is a purely
structural scheduler/registry-coherence invariant, "It does not change the A1 baseline (`8.420833333 kWh`)", ~L654 of
the invariant catalogue), and the binding PoCol naming rule (the algorithm is **PoCol**; the mechanism under audit is the
idle policy within PoCol — never "PoCol-E" / "Energy-Aware PoCol" / "Enhanced PoCol") is preserved. Every claim below is
grounded in an actual quote from `STAGE_01_PROTOCOL_PSEUDOCODE.md` (the primary source) with an approximate line anchor,
and is corroborated by TV269 ("An incomplete payload is rejected before any state mutation (AE7/AE8)").

---

## AE7 + AE8 checks

| Check | Result |
|---|---|
| **1. `ScheduleEvent` validates `event_type` + `immutable_payload` against §0.7g-schema and returns the STRUCTURED `rejected_payload_schema_mismatch(event_type, missing_or_invalid_fields)`** | **PASS** — the body assembles `SET immutable_payload <- the COMPLETE caller-supplied argument set for event_type (from envelope_fields)` (~L598), derives `SET missing_or_invalid_fields <- the required immutable_payload fields of event_type (per §0.7g-schema) that are ABSENT from immutable_payload OR fail their declared type` (~L601–L602), then `IF event_type is NOT declared in §0.7g-schema OR missing_or_invalid_fields is non-empty:` → `RECORD payload_schema_mismatch(event_type, missing_or_invalid_fields)` and `RETURN rejected_payload_schema_mismatch(event_type, missing_or_invalid_fields)      # AE7: STRUCTURED; NO state mutated yet` (~L603–L605). §0.7g-schema is named the "SINGLE authoritative schema … that `ScheduleEvent` validates a request's `immutable_payload` against (AE7 …)" (~L789–L790). RSM §3.10i AE7 restates it (~L1067–L1070). Corroborated by TV269 ("`ScheduleEvent` returns `rejected_payload_schema_mismatch(event_type, missing_or_invalid_fields)`"). |
| **2. The old AD8 construction ASSERT is GONE — replaced by the structured rejection (no raw assertion in the body)** | **PASS** — the AE7 comment states the replacement explicitly: "A malformed request is a STRUCTURED rejection, NEVER a raw assertion that terminates the simulation. (AE7 supersedes the AD8 construction ASSERT: assemble the payload, then validate it here.)" (~L596–L597). The live `ScheduleEvent` EFFECTS body (~L567–L627) contains NO `ASSERT` statement for payload construction; the sole handling of a malformed request is the structured `RETURN` at ~L605. The one residual occurrence of the word "asserts" near this — the queued-event-record STRUCTURE comment "ScheduleEvent REJECTS constructing an incomplete queued_event_record (it asserts the payload carries every required field)" (~L1284) — is descriptive prose inside a comment, not a live `ASSERT` line, and is consistent with the structured `RETURN` (it "REJECTS"). Corroborated by TV269 (a rejection, not a termination). |
| **3. The validation happens BEFORE incrementing `event_creation_seq`, deriving the `EventRef`, registering the `queued_event_record`, and inserting into EQ** | **PASS** — the ordering is quoted in the AE7 comment: "VALIDATE event_type + immutable_payload against the AUTHORITATIVE dispatch schema (§0.7g-schema) BEFORE any state mutation — BEFORE the seq is minted, the EventRef derived, the record registered, or the queue inserted." (~L594–L596), and the rejection carries "# AE7: STRUCTURED; NO state mutated yet" (~L605). Structurally, the validation `IF` (~L603) precedes the `ATOMICALLY:` block (~L610) whose first mutation is `SET EQ.event_creation_seq <- EQ.event_creation_seq + 1` (~L612). RSM §3.10i AE7: "validates … BEFORE minting `seq`, deriving the `EventRef`, registering the record, or inserting into EQ" (~L1067–L1068). Corroborated by TV269 ("BEFORE it increments `event_creation_seq`, derives the `EventRef`, registers a `queued_event_record`, or inserts into EQ. No seq is consumed, no registry entry is created, and nothing is enqueued"). |
| **4. `rejected_payload_schema_mismatch` is a member of the `ScheduleEvent` RETURNS union** | **PASS** — the declared union is `RETURNS: scheduled(event_ref, record) \| rejected_finalised_time \| post_horizon_event_rejected \| rejected_post_epilogue_not_strictly_later \| rejected_backward_time \| rejected_payload_schema_mismatch(event_type, missing_or_invalid_fields)` (~L628–L629), annotated "AD3/AE7: the COMPLETE result union … AE7 adds the structured `rejected_payload_schema_mismatch` (returned BEFORE any state mutation)" (~L630–L632). RSM §3.10i AE7: "(added to its RETURNS union)" (~L1069). Corroborated by TV269 (the named return variant). |
| **5. The successful seat is ONE atomic transaction (`ATOMICALLY` block): mint seq + EventRef, create the QUEUED record, add the registry entry, insert the EventRef into EQ — both-or-neither** | **PASS** — `ATOMICALLY:` (~L610) wraps, in order: `SET EQ.event_creation_seq <- EQ.event_creation_seq + 1` / `SET seq <- EQ.event_creation_seq` (~L612–L613); `SET event_ref <- EventRef(envelope_namespace = ORDINARY_EVENT, event_type = event_type, event_time = target_event_time, delta_cycle = dc, microphase = target_microphase, seq = seq)` (~L615–L616); the dispatch envelope (~L617–L618); `SET record <- queued_event_record(… queue_status = QUEUED)` (~L620–L621); `SET queued_event_registry[event_ref] <- record` (~L625); and `INSERT event_ref INTO EQ.event_queue ORDERED BY (event_time, delta_cycle, microphase, (CandidateID, MinerID, AssignmentID), seq)` (~L626–L627). The AE8 header names it "ONE atomic transaction — mint seq + EventRef, create the QUEUED queued_event_record, add the registry entry, AND insert the EventRef into EQ, committing BOTH-OR-NEITHER" (~L606–L607), and the commit comment: "COMMIT the registry entry AND the EQ insertion together (both-or-neither) … If the enqueue cannot complete, the whole transaction rolls back — neither the registry entry nor an EQ entry persists" (~L622–L624). RSM §3.10i AE8 (~L1072–L1074). Corroborated by TV269 ("atomicity, AE8"). |
| **6. No partial-seat state is observable — no registry entry left QUEUED without a pending EQ entry, and no EQ entry lacks a registry entry (I21 coherence)** | **PASS** — the AE8 comment: "There is no observable intermediate state, so a partial seat is impossible by construction: no registry entry is ever left QUEUED without a pending EQ entry, and no EQ entry ever exists without a registry entry (AE8/AE10 coherence)." (~L608–L609). I21 formalises it: "an `EventRef` is present in `EQ.event_queue` IFF `queued_event_registry[EventRef].queue_status = QUEUED`" and "every enqueue (`ScheduleEvent`, AE8) … changes `EQ` membership and `queue_status` ATOMICALLY (both-or-neither), so the two structures never diverge" (~L645–L652 of the invariant catalogue). Enforcement point: "`ScheduleEvent` (atomic add of registry entry + EQ entry, AE8)" (~L656 of the invariant catalogue). Corroborated by TV269 ("no registry entry is created, and nothing is enqueued"). |
| **7. Result-binding callers handle the new rejection, and no malformed scheduling request terminates the simulation through a raw assertion** | **PASS** — result-BINDING callers pattern-match `scheduled(event_ref, record)` and take an explicit branch on any non-`scheduled` disposition, which subsumes the new variant: e.g. `StartWake` `IF seat is NOT scheduled(event_ref, record):` → `RETURN wake_schedule_failed_before_transition(reason = seat)` carrying the exact `seat` disposition (~L1686–L1689). At these trusted internal call sites the payload is a fixed, in-schema construction for a fixed `event_type`, so `rejected_payload_schema_mismatch` is UNREACHABLE in practice — the same reachability reasoning the spec already states for the fire-and-forget hash path: "the schema/time/backward rejections are unreachable (a valid in-schema HashWorkEvent at a forward, non-finalised time)" (~L2821). Either way the disposition is a STRUCTURED return value, never a raw assertion: AE7 "A malformed request is a STRUCTURED rejection, NEVER a raw assertion that terminates the simulation" (~L596) and RSM §3.10i "No malformed scheduling request terminates the simulation through a raw assertion" (~L1070). Consistent with TV269. |

---

## Atomic-registration ordering (validate time → validate payload → mint seq/EventRef → create record → add registry → insert EQ)

`ScheduleEvent` performs its work in a fixed order in which EVERY rejection precedes ALL state mutation, and EVERY
mutation is confined to the single `ATOMICALLY` block:

1. **Validate time (no mutation).** The finalised-time guard `IF target_event_time in EQ.finalised_event_times: RETURN
   rejected_finalised_time` (~L569–L570), the O2 horizon guard `IF target_event_time > EQ.run_horizon_T: … RETURN
   post_horizon_event_rejected` (~L575–L577), the S7 post-epilogue strictly-later guard (~L581–L583), and the K8
   delta-cycle derivation / backward-time guard `RETURN rejected_backward_time` (~L586–L593) all run first. Only the
   local `dc` is computed here; nothing in EQ or the registry is touched.
2. **Validate payload (no mutation).** AE7 assembles `immutable_payload` (~L598–L600), computes
   `missing_or_invalid_fields` against §0.7g-schema (~L601–L602), and on an undeclared `event_type` or a non-empty
   mismatch set returns the structured `rejected_payload_schema_mismatch(event_type, missing_or_invalid_fields)` with
   "NO state mutated yet" (~L603–L605). This is the step that replaces the old AD8 construction ASSERT.
3. **Mint seq + EventRef (first mutation — inside `ATOMICALLY`).** `SET EQ.event_creation_seq <- EQ.event_creation_seq
   + 1` / `SET seq <- …` (~L612–L613), then `SET event_ref <- EventRef(…, seq = seq)` (~L615–L616). The seq is minted
   only AFTER both validations pass, so a rejected request never consumes a seq.
4. **Create the record.** `SET record <- queued_event_record(… queue_status = QUEUED)` (~L620–L621), built on the
   complete dispatch envelope (~L617–L618).
5. **Add the registry entry.** `SET queued_event_registry[event_ref] <- record` (~L625).
6. **Insert into EQ.** `INSERT event_ref INTO EQ.event_queue ORDERED BY (event_time, delta_cycle, microphase,
   (CandidateID, MinerID, AssignmentID), seq)` (~L626–L627).

Steps 3–6 are the single both-or-neither transaction (~L610, ~L622–L624): if the enqueue cannot complete, the whole
block rolls back and neither the registry entry nor an EQ entry persists, so the registry and EQ never diverge (I21 /
AE10). The two validation phases (steps 1–2) are strictly outside and before this block, guaranteeing that a rejected
request leaves `event_creation_seq`, the registry, and EQ exactly as they were.

---

## Result

**PASS on all seven checks.** AE7 is realised: `ScheduleEvent` validates `event_type` + `immutable_payload` against the
authoritative §0.7g-schema and returns the structured `rejected_payload_schema_mismatch(event_type,
missing_or_invalid_fields)` (~L603–L605) — a declared member of the RETURNS union (~L628–L629) — with the validation
placed strictly BEFORE any state mutation (~L594–L596, ~L605); the old AD8 construction ASSERT is superseded and no raw
construction assertion survives in the procedure body (~L596–L597). AE8 is realised: the successful seat is one
`ATOMICALLY` transaction that mints seq + EventRef, creates the QUEUED record, adds the registry entry, and inserts the
EventRef into EQ both-or-neither (~L610–L627), so no partial seat is observable and the queue/registry coherence
invariant I21 holds (~L608–L609; invariant catalogue ~L645–L656). Result-binding callers inspect the structured
disposition (e.g. `StartWake`, ~L1686–L1689) and the malformed variant is unreachable at the trusted internal call
sites (~L2821); in no case does a malformed scheduling request terminate the simulation through a raw assertion
(~L596, RSM ~L1070). The audit surfaced no residual raw construction assertion and no non-atomic registration; the A1
baseline `8.420833333 kWh` and the PoCol naming rule are preserved. Corroborated by TV269.
