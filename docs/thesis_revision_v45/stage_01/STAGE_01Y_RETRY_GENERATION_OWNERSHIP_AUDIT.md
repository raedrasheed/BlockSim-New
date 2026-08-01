# Stage 1Y — Retry-Generation Ownership Audit (correction Y3)

This audit certifies correction **Y3** ("remove setup-retry generation shadowing") in
`STAGE_01_PROTOCOL_PSEUDOCODE.md`. Y3 splits the single, ambiguously-typed `setup_retry_generation`
identifier — which the pre-Y3 text read both as a scalar generation and as a per-scope map, producing an
ill-defined index — into two DISTINCT identifiers:

- the SCALAR `retry_generation` — the retry-generation value carried in and out; and
- the MAP `setup_retry_generation_by_scope` — the bounded per-scope counter registry, keyed by
  `(RoundID, setup_kind, TemplateRefreshSetupID_or_null) -> generation`.

The audit verifies, with exact line grounding and reproducible grep counts, five claims: (1) `retry_generation`
is only ever a scalar; (2) `setup_retry_generation_by_scope` is only ever a map with the
`(RoundID, setup_kind, TemplateRefreshSetupID_or_null)` key; (3) zero `setup_retry_generation[` map-indexing
occurrences remain; (4) no identifier is both a scalar and a map; (5) `SetupRetryID` carries the full scope for
both setup kinds. It then records the TV213 test-vector linkage and the cross-document consistency chain.

This is a documentation-only structural correction (identifier ownership within the idle policy within PoCol);
it does not touch the energy model and does not alter the A1 baseline of 8.420833333 kWh. Line anchors are exact
against the current `STAGE_01_PROTOCOL_PSEUDOCODE.md` (5230 lines); quotations are verbatim.

---

## 0. Grep evidence (reproducible)

Run from the `stage_01/` directory against `STAGE_01_PROTOCOL_PSEUDOCODE.md`:

| Grep | Count | Meaning |
|------|-------|---------|
| `grep -n "setup_retry_generation_by_scope"` | **12** | every use of the map identifier |
| `grep -n "retry_generation\b"` | **21** | every use of the bare scalar identifier |
| `grep -n "setup_retry_generation\["` | **0** (exit 1, no match) | no `setup_retry_generation[` map indexing remains |
| `grep -c "retry_generation\["` | **0** | the scalar is never subscripted (no bare `retry_generation[`) |

The third grep is the decisive shadowing check: the pre-Y3 map was indexed as `setup_retry_generation[...]`;
that token no longer occurs. The 12 map uses are all `setup_retry_generation_by_scope` (a different identifier
whose `[` is preceded by `_by_scope`, so it is correctly excluded from both `setup_retry_generation[` and the
bare `retry_generation[` searches).

---

## 1. PASS — `retry_generation` is only ever a SCALAR

All 21 occurrences of `retry_generation` (word boundary) fall into exactly four scalar roles; none is subscripted
(`grep -c "retry_generation\["` = 0).

**(a) INPUT parameter of the two procedures that receive the generation.**

`SetupRetryEvent` (line 1836–1838):

```
  INPUTS: RoundContext, dispatch_envelope, RoundID, setup_kind, SetupRetryID,
          TemplateID_at_seat, TemplateRefreshSetupID, retry_generation, reason
          # Y3: retry_generation is the SCALAR generation (NEVER a map).
```

`ContinueTemplateRefreshAssignmentSetup` (line 4852):

```
  INPUTS: RoundContext, dispatch_envelope, TemplateID, TemplateRefreshSetupID, SetupRetryID, retry_generation
```

**(b) COMPONENT of `SetupRetryID`.** The §0.8 data-model note (lines 812–813) fixes the two canonical forms:

```
  #   PARTICIPANT_SETUP     : (RoundID, TemplateID, PARTICIPANT_SETUP, retry_generation)
  #   TEMPLATE_REFRESH_SETUP: (TemplateRefreshSetupID, TEMPLATE_REFRESH_SETUP, retry_generation)
```

**(c) BUDGET comparison against `maximum_setup_retries`.** In `SetupRetryEvent` guard (6), line 1875:

```
    IF retry_generation > maximum_setup_retries:
```

**(d) SCALAR value passed through / assigned into event payloads.** Line 1704
(`retry_generation = g`), line 1842 (`retry_generation = 0`, initial refresh call), line 1891
(`retry_generation = retry_generation`, SetupRetryEvent → continuation), line 4930 (`retry_generation = g`).
Each binds the scalar `g` (or `0`) to the `retry_generation` payload/parameter — never an index.

The remaining occurrences (lines 563, 807, 810, 811, 1396, 1838, 1840, 1841, 1873, 1899, 4839, 4854) are the
event-table row and definitional/normative comments, all of which describe `retry_generation` as "the SCALAR
generation." No occurrence is ever `retry_generation[...]`. **PASS.**

---

## 2. PASS — `setup_retry_generation_by_scope` is only ever a MAP with the `(RoundID, setup_kind, TemplateRefreshSetupID_or_null)` key

All 12 occurrences use the identifier as a map; every subscript uses the three-component key.

**Declaration + typing (§0.8 / field list).** Line 809 and lines 1394–1396:

```
  setup_retry_generation_by_scope : Y3 — map (RoundID, setup_kind, TemplateRefreshSetupID_or_null) -> generation. The
                                : bounded per-scope retry counter registry (RENAMED from the shadowed setup_retry_generation
                                : map). It is NEVER a scalar; the scalar generation carried in/out is retry_generation (Y3).
```

**`RoundInitialise` initialises the map (not the old scalar-shadowed map) and returns it.** Line 1468:

```
    INITIALISE setup_retry_generation_by_scope <- empty map   # W8/Y3: per (RoundID, setup_kind, TemplateRefreshSetupID_or_null) bounded retry counter (absent = 0 so far)
```

and it is returned in the `RoundContext` per-round registry list (line 1494):

```
                        setup_retry_generation_by_scope, template_refresh_setup_committed)   # W8/Y3/X3: per-round scoped retry counter + refresh-setup marker
```

**Map indexing site A — `PrepareParticipantsForNewRound`** (PARTICIPANT_SETUP scope, key third component `null`),
lines 1692, 1696–1697:

```
    IF setup_retry_generation_by_scope[(RoundID_current, PARTICIPANT_SETUP, null)] >= maximum_setup_retries:   # Y3: scoped map
      SET g <- setup_retry_generation_by_scope[(RoundID_current, PARTICIPANT_SETUP, null)] + 1     # Y3: advance the bounded per-scope generation
      SET setup_retry_generation_by_scope[(RoundID_current, PARTICIPANT_SETUP, null)] <- g
```

**Map indexing site B — `ContinueTemplateRefreshAssignmentSetup`** (TEMPLATE_REFRESH_SETUP scope, key third
component `TemplateRefreshSetupID`), lines 4918, 4922–4923:

```
    IF setup_retry_generation_by_scope[(RoundID_current, TEMPLATE_REFRESH_SETUP, TemplateRefreshSetupID)] >= maximum_setup_retries:   # Y3: scoped map keyed by TemplateRefreshSetupID
      SET g <- setup_retry_generation_by_scope[(RoundID_current, TEMPLATE_REFRESH_SETUP, TemplateRefreshSetupID)] + 1     # Y3: advance the bounded per-scope generation
      SET setup_retry_generation_by_scope[(RoundID_current, TEMPLATE_REFRESH_SETUP, TemplateRefreshSetupID)] <- g
```

Both scopes read-compare-advance-store through the same three-component key; the `null` vs `TemplateRefreshSetupID`
third component is exactly the `TemplateRefreshSetupID_or_null` declared in the key type. The remaining occurrences
(line 1397 in the `maximum_setup_retries` note, line 1900 in the `SetupRetryEvent` closing NOTE) describe the map.
Every use is a map; every subscript uses the declared key. **PASS.**

---

## 3. PASS — zero `setup_retry_generation[` map-indexing occurrences remain

`grep -n "setup_retry_generation\["` returns **no matches (exit code 1)**; `grep -c` returns **0**. The pre-Y3
shadowed map subscript is fully removed. The only bracketed uses in this family are
`setup_retry_generation_by_scope[...]` (distinct identifier, §2). **PASS.**

---

## 4. PASS — no identifier is both a scalar and a map

The two roles are carried by two disjoint identifiers:

- `retry_generation` — subscripted **0** times (`grep -c "retry_generation\["` = 0); used only as scalar
  input / `SetupRetryID` component / budget comparison / payload value (§1).
- `setup_retry_generation_by_scope` — used only as a map, never as a scalar (§2).

The pseudocode states this explicitly at line 810 ("`Y3: no identifier is both a scalar and a map`") and line 1396
("`It is NEVER a scalar; the scalar generation carried in/out is retry_generation (Y3)`"). There is no residual
`setup_retry_generation` bare identifier acting in both roles. **PASS.**

---

## 5. PASS — `SetupRetryID` carries the complete scope for both kinds

The two seating sites construct `srid` with the full per-kind scope tuple.

**PARTICIPANT_SETUP** — `PrepareParticipantsForNewRound`, line 1698:

```
      SET srid <- (RoundID_current, TemplateID_committed, PARTICIPANT_SETUP, g)      # Y3: full-scope SetupRetryID
```

matches the canonical form `(RoundID, TemplateID, PARTICIPANT_SETUP, retry_generation)` (the payload then carries
`retry_generation = g`, line 1704).

**TEMPLATE_REFRESH_SETUP** — `ContinueTemplateRefreshAssignmentSetup`, line 4924:

```
      SET srid <- (TemplateRefreshSetupID, TEMPLATE_REFRESH_SETUP, g)                     # Y3: full-scope SetupRetryID
```

matches the canonical form `(TemplateRefreshSetupID, TEMPLATE_REFRESH_SETUP, retry_generation)` (the payload then
carries `retry_generation = g`, line 4930). Both agree with the §0.8 definition (lines 811–813) and are re-verified
in `SetupRetryEvent`'s payload comment (lines 1840–1841). **PASS.**

**Supporting fact — `setup_retry_status_by_id` is declared in RunContext / `RunInitialise`.** The Y1 companion
registry that the full-scope `SetupRetryID` keys is created once per run: `INITIALISE setup_retry_status_by_id
<- empty map` (line 1417) and returned in the `RunContext` (line 1423); `SetupRetryEvent` reads it in guard (2)
(line 1854) and writes `setup_retry_status_by_id[SetupRetryID] <- APPLYING` in step (7) (line 1884). This confirms
the full-scope `SetupRetryID` is the key of a per-run status map, independent of the per-round generation map.

**§0.8 Y3 note.** The core-data-model block (§0.8, lines 803–813) states the Y3 contract in one place:
`retry_generation (Y3) : the SCALAR retry generation carried as an INPUT ... It is NEVER used as a map. The bounded
per-scope counter registry is the DISTINCT map setup_retry_generation_by_scope ...` followed by the two
`SetupRetryID` scope forms. The procedural bodies (§§1–5 above) conform to this note exactly.

---

## 6. Test-vector linkage — TV213

`STAGE_01Y_SEMANTIC_TEST_VECTORS.md` TV213 ("retry_generation scalar and setup_retry_generation_by_scope map are
distinct (Y3)", line 50) names the exact procedures audited here — `SetupRetryEvent`,
`ContinueTemplateRefreshAssignmentSetup`, `PrepareParticipantsForNewRound`, `RoundInitialise` — and its
**Expected** clause (lines 55–58) is the checklist this audit discharges:

> `retry_generation` appears ONLY as a scalar (input parameter / `SetupRetryID` component / budget comparison
> against `maximum_setup_retries`); `setup_retry_generation_by_scope` appears ONLY as a map indexed by
> `(RoundID, setup_kind, TemplateRefreshSetupID_or_null)`. No identifier is read as both a scalar and a map; there
> is no ambiguous indexing. `SetupRetryID` carries the full scope for both kinds.

Each of the three Expected conditions maps to an audit section: scalar-only → §1; map-only with the declared key →
§2; no dual use / no ambiguous indexing → §3 + §4; full-scope `SetupRetryID` → §5. The TV213 index row (line 124)
points at "`SetupRetryEvent`, `RoundInitialise`, seating sites", the same sites quoted above. **Consistent.**

---

## 7. Cross-document consistency

The Y3 contract is stated identically across the source of truth and its dependent artifacts.

| Document | Location | Y3 statement (verbatim key phrase) | Agreement |
|----------|----------|-----------------------------------|-----------|
| `STAGE_01_PROTOCOL_PSEUDOCODE.md` | §0.8 note (803–813); `RoundInitialise` (1468/1494); seating sites (1692–1698, 4918–4924) | scalar `retry_generation` vs DISTINCT map `setup_retry_generation_by_scope` keyed `(RoundID, setup_kind, TemplateRefreshSetupID_or_null)`; full-scope `SetupRetryID` | — (source of truth) |
| `STAGE_01_ROUND_STATE_MACHINE.md` | §3.10c, Y3 (748–752) | "The SCALAR `retry_generation` ... the DISTINCT map `setup_retry_generation_by_scope` keyed by `(RoundID, setup_kind, TemplateRefreshSetupID_or_null)`. No identifier is both a scalar and a map." + both `SetupRetryID` forms | ✓ matches §§1–5 |
| `STAGE_01_INVARIANT_CATALOGUE.md` | I16 Stage-1Y clause, Y3 (354–355) | "the scalar `retry_generation` and the map `setup_retry_generation_by_scope` `(RoundID, setup_kind, TemplateRefreshSetupID_or_null)` are distinct identifiers — no identifier is both a scalar and a map." | ✓ matches §4 |
| `STAGE_01_TERMINOLOGY.md` | `retry_generation` vs `setup_retry_generation_by_scope` entry (919–924) | "`retry_generation` is the SCALAR generation ... the DISTINCT map `setup_retry_generation_by_scope : (RoundID, setup_kind, TemplateRefreshSetupID_or_null) -> generation`. No identifier is both a scalar and a map." + both `SetupRetryID` forms | ✓ matches §§1–5 |
| `STAGE_01Y_SEMANTIC_TEST_VECTORS.md` | TV213 (50–58, 124) | scalar-only / map-only-with-key / no dual use / full-scope `SetupRetryID` | ✓ §6 |
| `STAGE_01_TRACEABILITY_MATRIX.csv` | R180 (line 181) | "Remove setup-retry generation shadowing (Y3); retry_generation is the SCALAR generation input and setup_retry_generation_by_scope is the DISTINCT map keyed by (RoundID setup_kind TemplateRefreshSetupID_or_null); ... SetupRetryID carries the complete scope ..."; procedures `SetupRetryEvent; PrepareParticipantsForNewRound; ContinueTemplateRefreshAssignmentSetup; RoundInitialise`; invariant `I16`; status `SPECIFIED` | ✓ requirement, procedures, invariant, and status all align |

R180's named procedures are exactly the four procedures audited in §§1–5 and named by TV213; its risk statement
("an ambiguous setup_retry_generation identifier read as both a scalar generation and a per-scope map producing an
ill-defined index") is precisely the shadowing that §3's zero-match grep confirms is removed; its bound invariant
is I16, whose Stage-1Y Y3 clause is quoted above. The four normative descriptions (pseudocode §0.8, round-SM
§3.10c, invariant I16, terminology) use the same key type, the same "distinct identifiers / not both scalar and
map" wording, and the same two `SetupRetryID` scope forms — no divergence. **Consistent.**

---

## 8. Deliverable tree (Stage 1Y, correction Y3 context)

This audit adds one file to the Stage-1Y set already present in
`docs/thesis_revision_v45/stage_01/`:

- `STAGE_01Y_CORRECTION_REPORT.md`
- `STAGE_01Y_PROCEDURE_CALL_GRAPH.md`
- `STAGE_01Y_PROCEDURE_SIGNATURE_CALL_AUDIT.md`
- `STAGE_01Y_SEMANTIC_TEST_VECTORS.md`
- `STAGE_01Y_SUPERSESSION_REGISTER.md`
- **`STAGE_01Y_RETRY_GENERATION_OWNERSHIP_AUDIT.md`** — this document.

The revised source of truth (`STAGE_01_PROTOCOL_PSEUDOCODE.md`) and the shared cross-cutting artifacts
(`STAGE_01_ROUND_STATE_MACHINE.md` §3.10c, `STAGE_01_INVARIANT_CATALOGUE.md` I16,
`STAGE_01_TERMINOLOGY.md`, `STAGE_01_TRACEABILITY_MATRIX.csv` R180) all carry the Y3 statements quoted above.
Historical `STAGE_01[A–X]_*` artifacts are unchanged frozen layers and were not read or modified for this audit
beyond confirming the current Y3 wording lives in the shared documents.

---

## 9. Result

**PASS (Y3):** `retry_generation` is used only as a scalar (input / `SetupRetryID` component / budget comparison),
`setup_retry_generation_by_scope` only as a map keyed `(RoundID, setup_kind, TemplateRefreshSetupID_or_null)`, zero
`setup_retry_generation[` map-indexing occurrences remain, no identifier is both a scalar and a map, and
`SetupRetryID` carries the full per-kind scope — consistent with TV213, R180, round-SM §3.10c, invariant I16, and
the terminology.
