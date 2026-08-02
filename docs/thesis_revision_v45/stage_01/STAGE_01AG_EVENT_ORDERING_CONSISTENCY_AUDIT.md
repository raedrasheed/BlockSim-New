# Stage-1AG Event-Ordering Consistency Audit (Correction AG8)

**Document status:** Stage-1 specification-only, audit deliverable for correction AG8. This
document reads across the FINAL normative Stage-1 documents and records, per verification item, a
PASS/FAIL judgement with exact line anchors. It asserts no implementation, security, or fairness
property; it verifies only textual and cross-document consistency of the root event-ordering
contract.

## Intro

The protocol under revision is **PoCol**; its low-power mechanism is referred to only as **the idle
policy within PoCol**. Correction AG8 reconciles the root event-ordering contract so that the event
total-order tie key is derived from each event type's own descriptor
(`stable_tie_key = descriptor(event_type).stable_tie_key(immutable_payload)`) and the earlier
AA-era universal `(CandidateID, MinerID, AssignmentID)` tie key is withdrawn everywhere. AG8 is a
structural ordering reconciliation only: it changes no energy accounting, so the **A1 baseline of
8.420833333 kWh** (141 TH/s, 21.5 J/TH, 3031.5 W over the 10,000 s horizon) is preserved
unchanged, and I21 explicitly notes it does not change that baseline
(`STAGE_01_INVARIANT_CATALOGUE.md` L698).

Documents audited (the five modified normative documents):

- `STAGE_01_PROTOCOL_PSEUDOCODE.md` — §0.2 event-envelope ordering rule, `ScheduleEvent` EQ INSERT,
  §0.7g event-descriptor `stable_tie_key`
- `STAGE_01_INVARIANT_CATALOGUE.md` — I21 and the Stage-1AG clause (under I16)
- `STAGE_01_ROUND_STATE_MACHINE.md` — AF3 / AG8 statements
- `STAGE_01_TERMINOLOGY.md` — Stage-1H (H2) addendum and Stage-1AG addendum
- `STAGE_01_TRACEABILITY_MATRIX.csv` — R256

## Verification results

| # | Verification item | Finding | Line anchor(s) | Result |
|---|-------------------|---------|----------------|:------:|
| 1 | §0.2 states `stable_tie_key = descriptor(event_type).stable_tie_key(immutable_payload)` as the ONE authoritative ordering rule; the universal `(CandidateID, MinerID, AssignmentID)` tie key is WITHDRAWN there. | §0.2 names it "**AG8: the ONE authoritative ordering rule**" and defines `stable_tie_key` as the descriptor-derived tie key computed from the event's own immutable handler payload; it then states "There is NO universal `(CandidateID, MinerID, AssignmentID)` tie key (that AA-era claim is WITHDRAWN — different event types tie-break on different descriptor keys …)". | `STAGE_01_PROTOCOL_PSEUDOCODE.md` §0.2 L66–L72 | **PASS** |
| 2 | `ScheduleEvent` orders the EQ INSERT by the descriptor-derived `stable_tie_key`, not the generic tuple. | `ScheduleEvent` derives `tie_key <- d.stable_tie_key(immutable_payload)` (with the comment that this "replaces the generic (CandidateID, MinerID, AssignmentID) ordering tuple"), then the atomic INSERT orders by `(event_time, delta_cycle, microphase, tie_key, seq)` annotated "descriptor-derived stable_tie_key (NOT the generic (CandidateID, MinerID, AssignmentID) tuple)". | `STAGE_01_PROTOCOL_PSEUDOCODE.md` `ScheduleEvent` L741–L748 (derivation), L769 (INSERT … ORDERED BY) | **PASS** |
| 3 | I21 states the descriptor-derived ordering (AF5/AG8), consistent with §0.2. | I21's AF5 strengthening states "the EQ order is the descriptor-derived `stable_tie_key` (AF3), so (a)–(f) hold by construction"; the enforcement point records the EQ insert "ordered by the descriptor tie key". AG8 is reaffirmed in the Stage-1AG clause: "`stable_tie_key = descriptor(event_type).stable_tie_key(immutable_payload)` everywhere; the universal `(CandidateID, MinerID, AssignmentID)` tie key is withdrawn." Consistent with §0.2. | `STAGE_01_INVARIANT_CATALOGUE.md` I21 L689–L696, L700–L701; AG8 clause L492–L494 | **PASS** |
| 4 | `STAGE_01_TERMINOLOGY.md`: the H2 addendum line is corrected to the descriptor-derived rule (universal tuple withdrawn) AND the Stage-1AG addendum states the one rule. | H2 addendum header now reads "(H2; ordering key superseded by AG8)" and its body defines `stable_tie_key` as descriptor-derived, stating "The H2-era universal `stable_tie_key = (CandidateID, MinerID, AssignmentID)` is WITHDRAWN (AG8)". The Stage-1AG addendum's "Descriptor-derived ordering rule (AG8)" states it as "the ONE authoritative ordering rule (§0.2, ScheduleEvent, I21)", the universal tuple "is withdrawn", and the three identities "are kept distinct". | `STAGE_01_TERMINOLOGY.md` H2 addendum L199–L204; Stage-1AG addendum L1213–L1216 | **PASS** |
| 5 | Repo-wide grep for the exact string `(CandidateID, MinerID, AssignmentID)` across the five modified normative docs: every remaining occurrence is a NEGATIVE / withdrawal statement, never an authoritative claim. | Exact fixed-string grep returns 9 occurrences, all negative: "There is NO universal …" (PSEUDO L69); "This replaces the generic … ordering tuple" (L742); "NOT the generic … tuple" (L769); "never the generic … tuple" (L982); "the universal … tie key is withdrawn" (INVARIANT L493); "never the generic … tuple" (ROUND_STATE_MACHINE L1119); "the universal … claim is withdrawn" (ROUND_STATE_MACHINE L1210); "is WITHDRAWN (AG8)" (TERMINOLOGY L203); "The universal … tie key is withdrawn" (TERMINOLOGY L1214). No authoritative use survives. (The distinct 4-tuple `(CandidateID, MinerID, AssignmentID, seq)` used for intra-microphase / no-randomness ordering is a different string and is out of scope of this exact-3-tuple check.) | PSEUDO L69, L742, L769, L982; INVARIANT L493; ROUND_STATE_MACHINE L1119, L1210; TERMINOLOGY L203, L1214 | **PASS** |
| 6 | The three identities (dispatch_envelope identity fields; immutable handler payload; descriptor-derived ordering key) are kept distinct in §0.2. | §0.2 states "**AG8: three identities are kept DISTINCT** — the `dispatch_envelope` identity fields `(envelope_namespace, event_time, delta_cycle, event_seq, hook_id)`; the immutable handler `immutable_payload`; and the descriptor-derived ordering key `stable_tie_key`." | `STAGE_01_PROTOCOL_PSEUDOCODE.md` §0.2 L76–L79 | **PASS** |

## Supporting cross-reference

The traceability matrix records the reconciliation as **R256** (SPECIFIED): "Reconcile the root
event-ordering contract (AG8); stable_tie_key equals descriptor(event_type).stable_tie_key(immutable_payload)
in the root 0.2 envelope contract in ScheduleEvent in invariant I21 in terminology and in
traceability; the surviving universal claim … is removed; the dispatch_envelope identity fields the
immutable handler payload and the descriptor-derived ordering key are stated as three distinct
things" (`STAGE_01_TRACEABILITY_MATRIX.csv` L257). The §0.7g-schema `event_descriptor` defines
`stable_tie_key(record)` as "the DESCRIPTOR-DERIVED total-order tie key, computed from THIS
descriptor's payload keys ONLY (never the generic (CandidateID, MinerID, AssignmentID) tuple)"
(`STAGE_01_PROTOCOL_PSEUDOCODE.md` L981–L983), with a per-event-type key column in the descriptor
table (L1006–L1027).

## Overall verdict

**PASS.** All six verification items pass. Across the five modified normative documents the root
event-ordering contract is stated once and consistently — `stable_tie_key =
descriptor(event_type).stable_tie_key(immutable_payload)` (AG8) — the universal
`(CandidateID, MinerID, AssignmentID)` tie key is withdrawn everywhere with every surviving mention
being a negative/withdrawal statement, the three identities are kept distinct in §0.2, and the A1
baseline of 8.420833333 kWh is preserved.
