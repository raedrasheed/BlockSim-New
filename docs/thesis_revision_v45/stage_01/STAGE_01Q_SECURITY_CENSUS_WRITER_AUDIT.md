# Stage 1Q — Security-Census Writer Audit (Q4)

## Intro

This is a documentation-only audit of Stage 1Q correction **Q4 — centralise security-census
writing** for the **PoCol** consensus spec revision. It records, without introducing or claiming
any property, that the event-time security census now has exactly ONE canonical atomic writer with
THREE named sources. The mechanism under review is **the idle policy within PoCol**, referenced here
only as a mechanism; no behavioural property is asserted by this audit. The A1 baseline of
**8.420833333 kWh** is UNCHANGED by this correction.

Scope is Q4 alone: the centralisation of the two census maps `latest_security_census[event_time]`
and `security_census_dirty[event_time]` behind the single procedure `CommitSecurityCensus`, and the
removal of the older contradictory writer-count statements. All facts below are anchored to exact
procedure and section names in `STAGE_01_PROTOCOL_PSEUDOCODE.md`.

## 1. `CommitSecurityCensus` — the sole atomic writer (§0.8a)

Section **0.8a Central security-census writer (Q4)** defines `PROCEDURE CommitSecurityCensus` as
the SOLE atomic writer of the two census maps. Its declared INPUTS are:

- `event_time`
- `census_provenance` — `(RoundID_at_census, TemplateID_at_census, state_version_at_census)` (J8)
- `H_active, H_honest, H_adversarial, q_adv`
- `census_source` — one of `{MINER_STATE_TRANSITION, APPLICABILITY_ENTRY, RECOVERY_DEADLINE}`

Its PRECONDITIONS require the caller to have ALREADY computed a coherent census
(`H_active = H_honest + H_adversarial`, I17), and state it is "called ONLY by the three census
sources below — nothing writes the two maps directly."

The EFFECTS write BOTH maps TOGETHER inside a single `ATOMICALLY:` block:

- `SET latest_security_census[event_time] <- census_record(...)` (with `census_source`, `census_seq`,
  and the J8 provenance fields)
- `SET security_census_dirty[event_time] <- true`

It RETURNS `security_census_committed(event_time, census_source)`.

## 2. The structural J1 invariant

The procedure carries **INVARIANT (J1)**: after EVERY call,
`security_census_dirty[event_time] = true` AND `latest_security_census[event_time]` EXISTS. Because
the two writes are the atomic body of the SOLE writer, this coherence is **STRUCTURAL** — it holds by
construction, not by a per-caller discipline. As the §0.8a EFFECTS comment states: "Because this is
the ONLY writer, the J1 coherence invariant (`dirty[t] = true => latest[t] exists`) is STRUCTURAL,
not a per-caller discipline. Newest write wins." The census is CLEARED only by
`FinalizeEventTimeSecurityCensus(event_time)` (the epilogue, I-01/I-02).

`FinalizeEventTimeSecurityCensus` (§9) reads this coherence as a guarantee: before reading the
latest census it asserts `latest_security_census[event_time] EXISTS`, justified by the note that
"`CommitSecurityCensus` (§0.8a/Q4) is the SOLE writer and writes both together atomically." This is
the J1 note in `FinalizeEventTimeSecurityCensus` that replaces the earlier per-writer framing.

## 3. The three `census_source` values and their calling procedures

`census_source` ranges over exactly three values, each produced by exactly one calling procedure;
none of the three writes the maps directly — each CALLS `CommitSecurityCensus`:

| `census_source`         | Calling procedure                             | Section | Trigger |
|-------------------------|-----------------------------------------------|---------|---------|
| `MINER_STATE_TRANSITION` | `ApplyMinerStateTransition`                   | §0.9    | An ACTIVE_HASHING census change at a miner-state boundary (step 5f) |
| `APPLICABILITY_ENTRY`    | `CaptureSecurityCensusOnApplicabilityEntry`   | §9      | Round entry into a floor-applicable state (K7) |
| `RECOVERY_DEADLINE`      | `CaptureSecurityCensusOnRecoveryDeadline`     | §9a     | Recovery-timeline census checkpoint at the deadline timestamp (P3) |

- **§0.9 `ApplyMinerStateTransition`** recomputes the census deterministically from the
  post-transition ACTIVE_HASHING set and, in step (5f), calls `CommitSecurityCensus(... census_source
  = MINER_STATE_TRANSITION)`.
- **§9 `CaptureSecurityCensusOnApplicabilityEntry`** computes the census on entry to a
  floor-applicable state and calls `CommitSecurityCensus(... census_source = APPLICABILITY_ENTRY)`.
- **§9a `CaptureSecurityCensusOnRecoveryDeadline`** computes the census at the deadline timestamp and
  calls `CommitSecurityCensus(... census_source = RECOVERY_DEADLINE)`.

`RecoveryCompletionDueEvent` (§10a, Q2 step 1) does NOT add a fourth source: its census refresh
REUSES `CaptureSecurityCensusOnRecoveryDeadline`, so the source count remains exactly three. This is
visible in `RecoveryCompletionDueEvent`, which calls
`CaptureSecurityCensusOnRecoveryDeadline(RoundContext, dispatch_envelope.event_time)` rather than
committing a census of its own.

## 4. Removal of the contradictory writer-count statements

The prior spec carried mutually contradictory framings — "exactly two writers", "third writer", and
"sole writer (`ApplyMinerStateTransition`)". Under Q4 these are REMOVED and replaced by the single
consistent framing **"one writer, three sources"** at both anchor points:

- **§0.8 data-model comment (Q4/J1 COHERENCE):** "`security_census_dirty` and
  `latest_security_census` are written by EXACTLY ONE procedure, `CommitSecurityCensus` (§0.8a), with
  THREE named sources (`census_source`) ... The earlier 'two writers'/'third writer' framing is
  superseded by 'one writer, three sources'."
- **§9 `FinalizeEventTimeSecurityCensus` J1 note:** the coherence assertion is justified by
  `CommitSecurityCensus` being "the SOLE writer" that "writes both together atomically", not by any
  count of independent writers.
- **§0.8a preamble:** "The earlier 'exactly two writers' / 'third writer' / 'sole writer' framings
  are SUPERSEDED: there is ONE writer with THREE named sources."

## 5. Grep-verification note

A read-only search over `STAGE_01_PROTOCOL_PSEUDOCODE.md` confirms the centralisation structurally.
The literal writes `SET latest_security_census[...]` and `SET security_census_dirty[...]` occur at
EXACTLY two lines — line 714 and line 721 — both inside the `ATOMICALLY:` block of
`CommitSecurityCensus` (§0.8a, procedure body spanning lines 703–729). No direct
`SET latest_security_census[...]` or `SET security_census_dirty[...]` appears anywhere OUTSIDE
`CommitSecurityCensus`. The three calling procedures (§0.9, §9, §9a) reach the maps ONLY through a
`CALL CommitSecurityCensus(...)`. This is the grep evidence for gate 6: the two maps have one, and
only one, canonical atomic writer.

## 6. BEFORE vs AFTER

| Aspect              | BEFORE (contradictory)                                          | AFTER (Q4)                                                        |
|---------------------|-----------------------------------------------------------------|-------------------------------------------------------------------|
| Writer count        | "exactly two writers" / "third writer" / "sole writer (`ApplyMinerStateTransition`)" — mutually inconsistent | ONE writer: `CommitSecurityCensus` (§0.8a) |
| Map writes          | Independent `SET` of the two maps in multiple procedures        | Both maps SET together in one `ATOMICALLY:` block, sole writer     |
| J1 coherence        | Per-caller discipline, asserted at each writer                  | STRUCTURAL — the atomic body of the sole writer guarantees it      |
| Census producers    | Framed as writers                                               | Framed as three named SOURCES that CALL the sole writer            |
| Source enumeration  | Ambiguous (two vs three)                                        | Exactly three: `MINER_STATE_TRANSITION`, `APPLICABILITY_ENTRY`, `RECOVERY_DEADLINE` |

## 7. Acceptance checks

| # | Check | Evidence | Result |
|---|-------|----------|--------|
| 1 | `CommitSecurityCensus` is the sole atomic writer of both census maps | §0.8a EFFECTS `ATOMICALLY:` block; RETURNS `security_census_committed` | PASS |
| 2 | INVARIANT J1 (`dirty[t]=true => latest[t] exists`) is STRUCTURAL | §0.8a INVARIANT (J1) note; §9 `FinalizeEventTimeSecurityCensus` J1 assertion | PASS |
| 3 | `census_source` has exactly three values | §0.8a INPUTS `{MINER_STATE_TRANSITION, APPLICABILITY_ENTRY, RECOVERY_DEADLINE}` | PASS |
| 4 | Each source CALLS the writer, none writes the maps directly | §0.9 step 5f; §9 capture; §9a capture — all `CALL CommitSecurityCensus(...)` | PASS |
| 5 | `RecoveryCompletionDueEvent` adds no fourth source (reuses §9a) | §10a `RecoveryCompletionDueEvent` calls `CaptureSecurityCensusOnRecoveryDeadline` | PASS |
| 6 | Contradictory writer-count statements removed, replaced by "one writer, three sources" | §0.8 data-model comment; §0.8a preamble; §9 J1 note | PASS |
| 7 | No `SET latest_security_census`/`SET security_census_dirty` outside `CommitSecurityCensus` | grep: only lines 714, 721, both inside §0.8a | PASS |
| 8 | Gate 6 — one canonical atomic writer for the security census | Composite of checks 1, 4, 6, 7 | PASS |

## Footer

This document is documentation only; it introduces no code, no configuration, and no property
claim. The consensus spec revision is named **PoCol**. **The idle policy within PoCol** is referenced
solely as a mechanism, with no property attributed to it. The A1 baseline **8.420833333 kWh** is
unchanged by correction Q4. The prohibited rebranded-algorithm-name variants are not used anywhere in
this document.
