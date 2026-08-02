# STAGE 01AF — Scheduler Schema-Enforcement Audit (Correction AF3)

## Introduction

This audit verifies correction **AF3** in the final normative tree: the full
descriptor-schema enforcement that `PROCEDURE ScheduleEvent` performs **before any
state mutation**, and the replacement of the generic ordering tuple by the
descriptor-derived stable tie key. The specification describes **PoCol** with **the
idle policy within PoCol** enabled; this is a documentation-only formal-specification
audit that changes no energy model, so the **A1 baseline `8.420833333 kWh` is
preserved** and unchanged.

All line anchors below refer to `STAGE_01_PROTOCOL_PSEUDOCODE.md` unless a different
document is named. `PROCEDURE ScheduleEvent` begins at **L620**; the AF3 validation
block is **L658–L689**; the AE8 atomic registration block is **L690–L710**; the
RETURNS union is **L711–L721**. The authoritative descriptor schema (§0.7g-schema)
begins at **L890**, with the descriptor core table at **L942–L963**.

## Per-item verification

| # | Claim under audit | Verdict | Line-anchor evidence |
|---|-------------------|:-------:|----------------------|
| 1 | All four checks (3a–3d) execute **BEFORE** any state mutation (before `seq` is minted, `EventRef` derived, record registered, or EQ inserted). | **PASS** | AF3 block header states the ordering explicitly: "ENFORCE THE FULL DESCRIPTOR SCHEMA … BEFORE any state mutation — BEFORE the seq is minted, the EventRef derived, the record registered, or the queue inserted" (**L658–L659**). All four checks sit at **L662–L689**, entirely above the `ATOMICALLY:` block (**L694**) where `seq` is minted (**L696–L697**), the `EventRef` derived (**L699–L700**), the registry entry added (**L709**), and the EQ INSERT performed (**L710**). |
| 1a | (3a) `event_type` must have a descriptor, else `rejected_event_type_unknown`. | **PASS** | `IF event_type is NOT declared in §0.7g-schema` (**L663**) → `RETURN rejected_event_type_unknown(event_type)` (**L665**); descriptor bound only afterward at `SET d <- descriptor(event_type)` (**L666**). |
| 1b | (3b) `target_microphase == descriptor.target_microphase`, else `rejected_microphase_mismatch`. | **PASS** | `IF target_microphase != d.target_microphase` (**L668**) → `RETURN rejected_microphase_mismatch(event_type, target_microphase, d.target_microphase)` (**L670**). |
| 1c | (3c) Payload key set equals the EXACT closed `allowed_payload_keys` (missing **OR** extra key rejected) and every value passes its declared type, else `rejected_payload_schema_mismatch(event_type, missing_fields, extra_fields, type_invalid_fields)`. | **PASS** | `missing_fields` = keys in `d.allowed_payload_keys` absent from payload (**L676**); `extra_fields` = keys in payload not in `d.allowed_payload_keys` — "EXACT set — no extra key permitted" (**L677**); `type_invalid_fields` = keys whose value fails `d.payload_field_types[k]` (**L678**); `IF any … non-empty` (**L679**) → `RETURN rejected_payload_schema_mismatch(event_type, missing_fields, extra_fields, type_invalid_fields)` (**L681**). Descriptor defines `allowed_payload_keys` as "the EXACT, CLOSED set … any missing OR any extra key is rejected" (**L905–L906**) and `payload_field_types` as the per-key declared type (**L907**). |
| 1d | (3d) Descriptor-derived `stable_tie_key` must be computable, else `rejected_stable_tie_key_unavailable`. | **PASS** | `IF d.stable_tie_key names a payload key ABSENT from immutable_payload` (**L686**) → `RETURN rejected_stable_tie_key_unavailable(event_type)` (**L688**); tie key computed only after the guard at `SET tie_key <- d.stable_tie_key(immutable_payload)` (**L689**). |
| 2 | Exact-version fields — `HashWorkEvent`/`WakeCompleteEvent` `assignment_version`; `SetupRetryEvent` `retry_generation` — are covered by the exact-key-set + type check (3c). | **PASS** | (3c) comment names them directly (**L673–L674**). Descriptor table declares each as a typed member of the exact closed set: `HashWorkEvent` → `assignment_version : Integer` (**L950**); `WakeCompleteEvent` → `assignment_version : Integer` (**L954**); `SetupRetryEvent` → `retry_generation : Integer` (**L963**) (also `LeaseExpiry` → `assignment_version : Integer`, **L956**). An absent version key becomes a `missing_fields` hit; a wrong-typed value becomes a `type_invalid_fields` hit (**L676–L678**). |
| 3 | The EQ INSERT orders by the descriptor-derived `tie_key` (from `d.stable_tie_key`), **not** the generic `(CandidateID, MinerID, AssignmentID)` tuple, which no longer appears in the INSERT. | **PASS** | `INSERT event_ref INTO EQ.event_queue ORDERED BY (event_time, delta_cycle, microphase, tie_key, seq)` (**L710**), where `tie_key` is bound at **L689** from `d.stable_tie_key(immutable_payload)`. The generic tuple does **not** appear in the ordering key at **L710**; it survives only as an explicit negation in the trailing comment ("NOT the generic (CandidateID, MinerID, AssignmentID) tuple", **L710**) and in the (3d) rationale (**L683**). |
| 4 | All four new rejection variants are in the RETURNS union, and each rejection returns **before** any mutation (structured, no raw assertion). | **PASS** | RETURNS union lists `rejected_event_type_unknown(event_type)` (**L713**), `rejected_microphase_mismatch(event_type, target_microphase, expected_microphase)` (**L714**), `rejected_payload_schema_mismatch(event_type, missing_fields, extra_fields, type_invalid_fields)` (**L715**), and `rejected_stable_tie_key_unavailable(event_type)` (**L716**). Each corresponding `RETURN` (**L665, L670, L681, L688**) fires inside the AF3 block above the `ATOMICALLY:` mutation block (**L694**). Block header mandates "a STRUCTURED rejection, NEVER a raw assertion that terminates the simulation" (**L659–L660**). |
| 5 | No caller pattern-matches the OLD two-field signature `rejected_payload_schema_mismatch(event_type, missing_or_invalid_fields)` in a way that breaks. | **PASS** | A tree-wide grep for `missing_or_invalid_fields` finds **no** caller that destructures the `ScheduleEvent` result (no `CASE`/`MATCH` binding). Every live-tree occurrence is a historical/supersession reference: the ScheduleEvent NOTE stating AF3 "replaces the AE7 single … `missing_or_invalid_fields`" (**L719**); the terminology AE7 entry (`STAGE_01_TERMINOLOGY.md` **L1127**) and the AF3 addendum declaring it "supersed[es]" the AE7 form (`STAGE_01_TERMINOLOGY.md` **L1169**); the AE7 description (`STAGE_01_ROUND_STATE_MACHINE.md` **L1069**); and the traceability-matrix AE7 row. The remaining hits are prior-stage Stage-1AE audit deliverables (`STAGE_01AE_*.md`), superseded by Stage 1AF. None consumes the current 4-field return. |

## Overall verdict

**PASS (all items).** `PROCEDURE ScheduleEvent` enforces the complete AF3 descriptor
schema — event-type-declared (3a), microphase-fixed (3b), exact-closed-key-set with
declared types (3c), and tie-key-computable (3d) — with every check returning a
structured rejection **before** any state is mutated (before `seq`, `EventRef`,
registry entry, or EQ insertion). The exact-version fields (`assignment_version`,
`retry_generation`) are covered by the exact-key-set-plus-type check. The EQ INSERT
orders by the descriptor-derived `tie_key`, and the generic
`(CandidateID, MinerID, AssignmentID)` tuple no longer appears in the ordering key.
All four new rejection variants are declared in the RETURNS union, and no caller
depends on the superseded two-field signature. The specification remains PoCol with
the idle policy within PoCol; the A1 baseline `8.420833333 kWh` is preserved.
