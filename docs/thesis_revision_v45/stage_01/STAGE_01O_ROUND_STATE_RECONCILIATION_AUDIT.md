# Stage 1O — Round-State Reconciliation Audit (O5)

## Intro

This is a documentation-only audit. It records no code change, no simulation run, and claims no
property. The consensus algorithm is named **PoCol** throughout; where an energy-behaviour mechanism
is referenced it is described only as **the idle policy within PoCol**, a mechanism and nothing more.
The A1 continuous-control accounting baseline of **8.420833333 kWh** is **UNCHANGED** by this audit
and by correction O5.

**Scope (O5).** This file audits Stage 1O correction **O5 — round-state reconciliation plus
name replacement** across the un-suffixed normative documents in
`docs/thesis_revision_v45/stage_01/` (`STAGE_01_*.md`, `STAGE_01_*.csv`). O5 (i) removes every residual
"security-before-discovery" ordering statement, (ii) replaces the superseded procedure name
`FinalizeTimestampSecurityCensus` with the actually-defined procedure `FinalizeEventTimeSecurityCensus`,
and (iii) leaves the historical Stage-1A..1N lettered artifacts frozen.

## 1. The canonical rule (stated), versus the removed "security-before-discovery" ordering

**Canonical rule.** At a settled `event_time`, ordinary events and **all** delta-cycles are processed
to quiescence; if the run's current round is still nonterminal at the horizon `T`, horizon closure
runs via the named hook `CloseRoundAtHorizon` (pseudocode §20b); the event-time security epilogue
`FinalizeEventTimeSecurityCensus` (I-01/I-02, keyed by `event_time` **alone**, run **AFTER**
quiescence) then decides the security floor at most once; and the run-level `FinalizeSimulationRun`
(pseudocode §20a) runs only when `t = T`. The security decision is therefore the post-quiescence
epilogue — it is **NEVER** a microphase placed **before** certificate/discovery events.

**Contrast (removed ordering).** The superseded formulation placed a settled-census microphase
*inside* the same-timestamp microphase chain, immediately after `AcceptanceBatchFinalize` and
**before** certificate/discovery. O5 removes that placement: the census is not a microphase at all;
it is the epilogue that runs only once the whole `event_time` is quiescent.

The canonical rule is stated in the reconciled normative docs at:
`STAGE_01_ROUND_STATE_MACHINE.md` §3.14 (lines 448-464, "O5 canonical horizon sequence") and §2.6
same-timestamp bullet (lines 175-187); `STAGE_01_INVARIANT_CATALOGUE.md` I17 enforcement point
(lines 312-321); and `STAGE_01_TERMINOLOGY.md` Stage-1O addendum (lines 465-470).

## 2. The §2.6 rewrite (before / after)

Location: `STAGE_01_ROUND_STATE_MACHINE.md` §2.6 `SOLUTION_PROPAGATION`, "Same-timestamp event order"
bullet.

**Before (removed).** The microphase chain read, in part:

> `... AcceptanceBatchFinalize → the single settled-census FinalizeTimestampSecurityCensus →
> certificate/discovery/…`

placing the census microphase **before** certificate/discovery.

**After (present text, lines 177-182).** The microphase chain now reads:

> `... AcceptanceBatchFinalize → certificate/discovery/… → all remaining queued events`, and —
> **ONLY AFTER the whole `event_time` is quiescent** — the single security-floor decision runs as the
> event-time **EPILOGUE** `FinalizeEventTimeSecurityCensus` (I-01/I-02). **O5:** the security decision
> is therefore NEVER a microphase placed BEFORE certificate/discovery events; it is the
> post-quiescence epilogue keyed by `event_time` alone.

The census name is gone from the microphase chain, certificate/discovery now precede any security
decision, and the census is expressed as the post-quiescence epilogue. No positive statement in the
normative corpus places the security decision before certificate/discovery; the only textual matches
of that phrasing are the **corrective** statement itself (`STAGE_01_ROUND_STATE_MACHINE.md:181`,
`STAGE_01_INVARIANT_CATALOGUE.md:319`, `STAGE_01_TERMINOLOGY.md:212` and `:499-500`) and the
negative-evidence ("anti-pattern") columns of traceability rows R51 and R104.

## 3. Name replacement — `FinalizeTimestampSecurityCensus` → `FinalizeEventTimeSecurityCensus`

Every **functional** use of the superseded name `FinalizeTimestampSecurityCensus` is replaced by the
actually-defined procedure `FinalizeEventTimeSecurityCensus`. The four replaced sites:

| # | File | Location | Old → New |
|---|------|----------|-----------|
| a | `STAGE_01_ROUND_STATE_MACHINE.md` | §2.6 same-timestamp ordering (line 180) | `FinalizeTimestampSecurityCensus` → `FinalizeEventTimeSecurityCensus` |
| b | `STAGE_01_INVARIANT_CATALOGUE.md` | I17 enforcement-point paragraph — single settled-census evaluation (lines 317-318) | `FinalizeTimestampSecurityCensus` → `FinalizeEventTimeSecurityCensus` |
| c | `STAGE_01_TERMINOLOGY.md` | Stage-1H "single settled-census security evaluation" bullet (lines 208-216) — renamed **and** relocated to the event-time epilogue | `FinalizeTimestampSecurityCensus` → `FinalizeEventTimeSecurityCensus` |
| d | `STAGE_01_TRACEABILITY_MATRIX.csv` | row R51 (line 52) | `FinalizeTimestampSecurityCensus` → `FinalizeEventTimeSecurityCensus` |

At site (c) the bullet additionally notes that the old `(event_time, delta_cycle)` microphase-5 keying
is **no longer used**: the epilogue is keyed by `event_time` **alone** (I-01/I-02).

**The pseudocode procedure is real.** `FinalizeEventTimeSecurityCensus` is the actual defined
`PROCEDURE` in `STAGE_01_PROTOCOL_PSEUDOCODE.md` (declaration at line 1696), invoked by
`ProcessEventTime` as the event-time epilogue (e.g. lines 174, 211, 261). The replacement therefore
points every normative reference at a defined procedure, eliminating the dangling reference to an
undefined procedure name.

**Remaining textual mentions are deliberate.** A `grep` of the un-suffixed normative corpus for
`FinalizeTimestampSecurityCensus` returns exactly three matches — `STAGE_01_TERMINOLOGY.md:215`,
`STAGE_01_TERMINOLOGY.md:501`, and `STAGE_01_TRACEABILITY_MATRIX.csv:105` (row R104). All three are
supersession-recording / corrective statements that **quote** the old name expressly to document that
it has been replaced (e.g. "The superseded name `FinalizeTimestampSecurityCensus` is replaced
everywhere by `FinalizeEventTimeSecurityCensus`"). **Zero** functional / defined-procedure references
to the old name remain.

## 4. Historical freeze

The historical Stage-1A..1N lettered artifacts (files named `STAGE_01A_*` .. `STAGE_01N_*`) are **NOT**
modified by O5. The superseded name `FinalizeTimestampSecurityCensus` may still appear inside those
frozen artifacts (for example `STAGE_01H_*` and `STAGE_01I_*`) as a historical record, and that is
intentional — a frozen artifact records the state of the specification at its own stage. Stage 1O only
reconciles the un-suffixed normative documents and records supersessions in the designated register
`STAGE_01O_SUPERSESSION_REGISTER.md`, as stated by the Stage-1O terminology addendum
(`STAGE_01_TERMINOLOGY.md:503`). No lettered artifact was edited under O5.

## 5. Cross-document alignment with the O1 canonical horizon sequence

O5 also aligns the round state machine and the terminology / energy / invariant documents with the O1
canonical horizon sequence:

- **Run driver drains.** `RunEventLoopToHorizon` (pseudocode §0.7d-run) processes every
  `event_time <= T` through `ProcessEventTime` (the SOLE event-loop driver), draining all ordinary
  events and delta-cycles (`STAGE_01_ROUND_STATE_MACHINE.md` §3.14, lines 453-455).
- **`CloseRoundAtHorizon`.** If the current round is still nonterminal at `T`, `ProcessEventTime(T)`
  interposes the named `CloseRoundAtHorizon` hook (pseudocode §20b), one deterministic horizon
  envelope, `→ ROUND_ABORTED` (`STAGE_01_TERMINOLOGY.md:471-474`).
- **`FinalizeEventTimeSecurityCensus(T)` terminal-stale-noop.** The `T` epilogue then runs as a
  `terminal_stale_noop` (`STAGE_01_ROUND_STATE_MACHINE.md:458`; `STAGE_01_TERMINOLOGY.md:469-470`).
- **Run-level `FinalizeSimulationRun` — settle + reconcile only.** As a post-`ProcessEventTime(T)`
  run-level hook (not a queued event), it performs only the single `FINAL_RUN_END`
  `SettleResidencyBoundary` plus the I5/I6/I7 reconciliation to `T`; the former internal drain and
  horizon-close are removed (`STAGE_01_ROUND_STATE_MACHINE.md:459-464`;
  `STAGE_01_TERMINOLOGY.md:475-478`).

## 6. Acceptance checks

| # | Check | Result | Evidence |
|---|-------|--------|----------|
| 1 | Canonical rule stated (quiescence → `CloseRoundAtHorizon` → `FinalizeEventTimeSecurityCensus` → `FinalizeSimulationRun` at `t=T`) | PASS | `STAGE_01_ROUND_STATE_MACHINE.md` §3.14 (448-464); `STAGE_01_TERMINOLOGY.md` (465-470) |
| 2 | §2.6 rewritten: certificate/discovery precede the census; census is the post-quiescence epilogue | PASS | `STAGE_01_ROUND_STATE_MACHINE.md` lines 177-182 |
| 3 | No positive statement places the security decision before certificate/discovery (only corrective / anti-pattern text remains) | PASS | corrective at `:181`, `:319`, `:212`; anti-pattern columns in R51, R104 |
| 4 | Four functional sites replaced with `FinalizeEventTimeSecurityCensus` | PASS | ROUND_STATE_MACHINE §2.6 (180); INVARIANT_CATALOGUE I17 (317-318); TERMINOLOGY bullet (208-216); TRACEABILITY R51 (52) |
| 5 | 0 remaining functional `FinalizeTimestampSecurityCensus` in the normative corpus (3 residual mentions are supersession-recording quotations only) | PASS | grep: only `TERMINOLOGY.md:215,:501` and `TRACEABILITY R104:105`, all corrective |
| 6 | `FinalizeEventTimeSecurityCensus` is a real defined procedure | PASS | `STAGE_01_PROTOCOL_PSEUDOCODE.md:1696` (`PROCEDURE FinalizeEventTimeSecurityCensus`) |
| 7 | Historical Stage-1A..1N lettered artifacts unchanged (old name intentionally retained there) | PASS | old name still present in `STAGE_01H_*` / `STAGE_01I_*`; no lettered artifact edited under O5 |
| 8 | Cross-doc alignment with O1 horizon sequence (drain / `CloseRoundAtHorizon` / terminal-stale-noop / settle+reconcile) | PASS | `STAGE_01_ROUND_STATE_MACHINE.md` 453-464; `STAGE_01_TERMINOLOGY.md` 465-478 |
| 9 | A1 baseline unchanged | PASS | `STAGE_01_ENERGY_MODEL_SPECIFICATION.md:29,197,225` — `8.420833333 kWh` |

---

Documentation only. The algorithm name is **PoCol**; the idle policy within PoCol is described as a
mechanism only, and no property is claimed. The A1 baseline **8.420833333 kWh** is unchanged. The
prohibited rebranded-algorithm-name variants are not used anywhere in this document.
