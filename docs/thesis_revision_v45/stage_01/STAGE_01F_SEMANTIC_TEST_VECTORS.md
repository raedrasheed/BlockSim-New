# Stage 1F — Semantic Test Vectors (TV28–TV38)

Eleven blocking test vectors for the Stage-1F concurrency / discrete-event contract. Each vector
names the exact procedure(s) in `STAGE_01_PROTOCOL_PSEUDOCODE.md` and its exact preconditions; no
vector assumes an unmodeled external action. These extend TV1–TV27 (historical, in
`STAGE_01C/D/E_SEMANTIC_TEST_VECTORS.md`, which are NOT modified in Stage 1F). No property (energy,
security, fairness) is claimed — the vectors exercise structure. Name remains **PoCol**; mechanism
is **the idle policy within PoCol**.

Notation: candidate `A` has context `cpc_A` with `CandidateID_A`; likewise `B`. "Live" =
`status ∈ {DISCOVERED, SELF_VALIDATED, PROPAGATING, PENDING_ACCEPTANCE}`.

---

## TV28 — one candidate's failure resumes ONLY its own paused miners; the round stays SOLUTION_PROPAGATION

**Preconditions.** Round `SOLUTION_PROPAGATION`; `active_propagation_set = {cpc_A, cpc_B}`; miner
`Ma` PAUSED with `pause_cause_candidate_id = CandidateID_A`; miner `Mb` PAUSED with
`pause_cause_candidate_id = CandidateID_B`; both contexts have live certificate/block events.

**Trace.** `BlockAcceptancePoint(CandidateID_A, outcome = REJECTED) → HandlePropagationFailure(
CandidateID_A, PropagationID_A, REJECTED)`: sets `status(cpc_A) = FAILED`; REMOVEs `cpc_A` from
`active_propagation_set` (now `{cpc_B}`); CANCELs only `cpc_A`'s certificate-arrival + block-arrival
events; `FOR EACH` miner with `pause_cause_candidate_id = CandidateID_A` ⇒ `SCHEDULE
ResumeFromPause(Ma, …, CandidateID_A)`; `SecurityFloorEvaluate` (no breach); `propagation_quiescent`
is FALSE (`cpc_B` live) ⇒ round STAYS `SOLUTION_PROPAGATION`.

**Expected.** `Ma` resumes (T30→T5); `Mb` is untouched; every `cpc_B` event remains scheduled; the
round does not return to HASHING. Invariants/reqs: **F2, F3**, I4, I5/I6.

## TV29 — a failing candidate never cancels another candidate's events

**Preconditions.** After TV28's setup, `A` fails first (REJECTED); later `B`'s block arrives ACCEPTED.

**Trace.** `HandlePropagationFailure(CandidateID_A, …)` cancels ONLY `cpc_A`'s events (F2), leaving
every `cpc_B` `CertificateArrival`/`BlockAcceptancePoint` event scheduled. Later
`BlockAcceptancePoint(CandidateID_B, ACCEPTED_CANDIDATE) → AcceptanceTimestampBatch → ValidBlockAccept(
CandidateID_B, …)` accepts `B`.

**Expected.** No `cpc_B` event was cancelled or altered by `A`'s failure; `B` proceeds to acceptance
normally. Invariants/reqs: **F2**, F3.

## TV30 — acceptance of one candidate cancels all other live candidates and closes the round once

**Preconditions.** Round `SOLUTION_PROPAGATION`; `active_propagation_set = {cpc_A, cpc_B, cpc_C}`;
`A`'s block arrives ACCEPTED first (strictly earliest acceptance timestamp).

**Trace.** `BlockAcceptancePoint(CandidateID_A, ACCEPTED_CANDIDATE) → AcceptanceTimestampBatch`
(batch = {A}; A validates) `→ ValidBlockAccept(CandidateID_A, …)`: guards "already accepted?" (no);
`status(cpc_A) = ACCEPTED`; for `cpc_B`, `cpc_C` (≠ winner) `status ← CANCELLED`, CANCEL their
events; `CLEAR active_propagation_set`; `SOLUTION_PROPAGATION → ROUND_ACCEPTED` (single transition);
`CloseRoundAssignments(ROUND_ACCEPTED)` closes once. A second acceptance attempt would find "already
accepted" and no-op.

**Expected.** Winner `ACCEPTED`; others `CANCELLED` (or `COMPETING` if same-timestamp valid losers);
their events cancelled; round closed **exactly once**; paused finders of `B`/`C` close with
`stop_reason = ROUND_ACCEPTED` (NOT resumed). Invariants/reqs: **F3**, D6, I2/I3.

## TV31 — ReserveActivate over a fresh range yields custody ORIGINAL

**Preconditions.** `round_state = SECURITY_RECOVERY`; miner `R` in RESERVE; `candidate_range` is a
fresh never-assigned range.

**Trace.** `ReserveActivate`: `candidate_range` is fresh ⇒ `origin = ORIGINAL`, `source = null`;
`CreatePendingAssignment(R, candidate_range, ORIGINAL, null, null)` sets `custody_status = original`,
`previous_assignment_reference = null`, `assignment_version = 1`, fresh `lineage_id`; `StartWake(R,
…, RESERVE)` (T4).

**Expected.** The reserve assignment is `ORIGINAL` with no previous reference. Invariants/reqs:
**F4**, I1/I10.

## TV32 — ReserveActivate over a previously-assigned unsearched suffix yields custody REASSIGNED with full I9 provenance

**Preconditions.** `round_state = SECURITY_RECOVERY`; miner `R` in RESERVE; `candidate_range` is the
accepted unsearched suffix of a prior source assignment `S`.

**Trace.** `ReserveActivate`: `candidate_range` not fresh ⇒ `origin = REASSIGNED`, `source = S`,
`reason = security_recovery`; `CreatePendingAssignment(R, candidate_range, REASSIGNED, S,
security_recovery)` sets `custody_status = reassigned`, `previous_assignment_reference =
AssignmentID(S)`, `assignment_version = version(S)+1`, `lineage_id = lineage_id(S)`, and APPENDs the
I9 `reassignment_record(range, from = S, reason, timestamp, prior_pc)`; `StartWake(R, …, RESERVE)`.

**Expected.** Custody is `REASSIGNED`; the I9 provenance record is complete (source, reason,
timestamp, prior_pc). A reassignable suffix is NEVER labelled ORIGINAL. Invariants/reqs: **F4**, I8b, I9.

## TV33 — three miners waking at the same timestamp complete independently, not serially

**Preconditions.** Miners `M1, M2, M3` each receive an activation at time `t0` with distinct wake
latencies `L1 < L2 < L3`.

**Trace.** Each activation calls `StartWake(Mi, …)` at `t0`: each performs
`ApplyMinerStateTransition(Mi, …→ WAKING, t0)`, draws `Li`, and `SCHEDULE WakeCompleteEvent(Mi) AT
t0 + Li`, returning immediately (§0.1). The three `WakeCompleteEvent`s fire at `t0+L1`, `t0+L2`,
`t0+L3` — three separate event times — each doing `ApplyMinerStateTransition(Mi, WAKING →
ACTIVE_HASHING, t0+Li)` and beginning hashing.

**Expected.** No wake blocks another; completion times are `t0+Li` independently; wake residency
`P_wake·Li` is charged per miner. Invariants/reqs: **F5**, I5/I6.

## TV34 — every ACTIVE_HASHING boundary updates H_active at the exact transition timestamp; I17 holds

**Preconditions.** Any transition into `ACTIVE_HASHING` (T5) or out of it (T7/T26/T27/T28/T29/T11/T18)
at time `t`.

**Trace.** The transition is applied by `ApplyMinerStateTransition(…, t)`: it closes the old
residency and opens the new at `t`, then recomputes `H_honest(t)`, `H_adversarial(t)`,
`H_active(t) = H_honest(t) + H_adversarial(t)` from the post-transition `ACTIVE_HASHING` census, sets
`q_adv(t)` (or NA if `H_active(t)=0`), and schedules `SecurityFloorEvaluate`.

**Expected.** `H_active` is recomputed at the EXACT boundary timestamp and `I17` holds exactly; no
boundary is missed and no hash rate is sampled here. Invariants/reqs: **F6**, I17, I5/I6.

## TV35 — a solution discovered under version v1 stays valid after a same-range renewal to v2; exactly one CURRENT

**Preconditions.** Miner `M` `ACTIVE_HASHING` on assignment version `v1` (CURRENT); `M` discovers a
valid candidate under `v1` (`snapshot` binds `AssignmentID(v1)`, `assignment_version = v1`).

**Trace.** Later `LeaseExpiry` renews the SAME range: `RenewAssignment` creates `v2` (CURRENT, copied
frontiers/provenance, `previous_assignment_reference = AssignmentID(v1)`), atomically sets
`status(v1) = SUPERSEDED` (`superseded_at`). At acceptance, `ValidateCandidate(certificate, snapshot)`
resolves `snapshot`'s `(AssignmentID(v1), v1)` to the immutable `v1`, checks `v1` was CURRENT at
discovery and not revoked before `discovery_time`, nonce ∈ `v1` range, RoundID/TemplateID/target/sig.

**Expected.** The `v1`-discovered solution validates after renewal; `v1` is immutable and resolvable;
exactly one version (`v2`) in the lineage is CURRENT. Invariants/reqs: **F7, I18**, E1, I2.

## TV36 — solution discovery vs lease expiry at the same timestamp is resolved deterministically

**Preconditions.** At time `t`, miner `M`'s `ActiveHashing` hit-event and a `LeaseExpiry` event for
`M`'s assignment are both scheduled.

**Trace.** The F8 priority table orders same-timestamp events: **lease expiry (11)** is processed
before **solution discovery (8)**? No — the table places solution discovery (8) ABOVE lease expiry
(11), so **discovery is processed first**; the discovery captures its snapshot against the version
that is CURRENT at `t`, then lease expiry runs. Because both are deterministic and the priority is
fixed, every rerun yields the identical outcome (the discovery's snapshot binds the pre-expiry
version; a subsequent expiry/renewal does not retroactively invalidate it, E1/I18).

**Expected.** One deterministic result independent of iteration order. Invariants/reqs: **F8**, E1, I18.

## TV37 — wake completion vs round acceptance at the same timestamp cannot activate into a closed round

**Preconditions.** At time `t`, a `WakeCompleteEvent(M)` and a round-acceptance closure
(`ValidBlockAccept → ROUND_ACCEPTED`) are both scheduled.

**Trace.** The F8 priority table processes **round-acceptance closure (2)** before **wake completion
(12)**. `ValidBlockAccept → CloseRoundAssignments(ROUND_ACCEPTED)` runs first; for `M`'s WAKING
holder it CANCELs the pending `WakeCompleteEvent` and applies `WAKING → OFFLINE` (T12). When the
(now-cancelled) wake event's slot is reached it is a no-op.

**Expected.** `M` never activates into a closed round; it is `OFFLINE` (rejoins next round via T17).
Invariants/reqs: **F8, F6**, §3.2.

## TV38 — a candidate failure while an acceptance batch is pending does not return the round to HASHING prematurely

**Preconditions.** Round `SOLUTION_PROPAGATION`; `active_propagation_set = {cpc_A}` plus a pending
same-timestamp `ACCEPTED_CANDIDATE` acceptance batch for candidate `Z` at the acceptance point (Z's
block-arrival already fired ACCEPTED and `AcceptanceTimestampBatch` is mid-arbitration or scheduled).

**Trace.** `BlockAcceptancePoint(CandidateID_A, REJECTED) → HandlePropagationFailure(CandidateID_A,
…)`: removes `cpc_A`; but `propagation_quiescent` is FALSE because a same-timestamp acceptance batch
is pending (and/or Z's acceptance event is live) ⇒ round STAYS `SOLUTION_PROPAGATION`. The pending
batch then resolves via `ValidBlockAccept` (accept Z, close once) or, if empty, fails Z
candidate-scoped.

**Expected.** `A`'s failure does not fire R7; the round remains `SOLUTION_PROPAGATION` until the
acceptance batch resolves. Invariants/reqs: **F3**, D6.

---

## Coverage summary

| Vector | Requirement(s) | Named procedure(s) exercised |
|--------|----------------|------------------------------|
| TV28 | F2, F3 | `HandlePropagationFailure`, `ResumeFromPause`, `active_propagation_set` |
| TV29 | F2 | `HandlePropagationFailure`, `BlockAcceptancePoint`, `AcceptanceTimestampBatch` |
| TV30 | F3 | `ValidBlockAccept`, `AcceptanceTimestampBatch`, `CloseRoundAssignments` |
| TV31 | F4 | `ReserveActivate`, `CreatePendingAssignment` (ORIGINAL) |
| TV32 | F4, I9 | `ReserveActivate`, `CreatePendingAssignment` (REASSIGNED) |
| TV33 | F5 | `StartWake`, `WakeCompleteEvent` |
| TV34 | F6, I17 | `ApplyMinerStateTransition` |
| TV35 | F7, I18 | `RenewAssignment`, `ValidateCandidate` |
| TV36 | F8 | event-priority table; `ActiveHashing`/`LeaseExpiry` |
| TV37 | F8, F6 | event-priority table; `CloseRoundAssignments`, `WakeCompleteEvent` |
| TV38 | F3 | `HandlePropagationFailure`, `propagation_quiescent`, `AcceptanceTimestampBatch` |

Every vector uses named procedures and exact preconditions; none assumes an unmodeled external
action; no property is claimed (Stage 1 specifies structure only).
