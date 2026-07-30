# Stage 1 — Progress-Verification Abstraction

**Document status:** Stage-1 specification-only. This document SPECIFIES a **modeled
progress-verification abstraction** for the idle policy within PoCol. It is NOT a cryptographic
proof of range exhaustion, and it does NOT claim that any mechanism here is implemented,
validated, or secure. Stage 1 SPECIFIES; it does NOT demonstrate any property of what it
specifies.

**Naming rule (binding).** The algorithm is ALWAYS **PoCol**. The mechanism here is part of
**the idle policy within PoCol** — an operating policy inside PoCol, not a new algorithm,
variant, or fork. The strings "PoCol-E", "Energy-Aware PoCol", and "Enhanced PoCol" MUST NOT
appear.

**Framing (binding).** Everything below is a *modeled progress-verification abstraction*. It is
NOT a "cryptographic proof" and MUST NOT be described as one. A progress commitment attests a
claimed frontier; it does not, at Stage 1, prove that every nonce up to that frontier was
actually hashed. That gap is recorded as an **open research problem** (Section 5).

---

## 1. Purpose

A miner leasing a nonce range (see `STAGE_01_RANGE_LEASE_AND_REASSIGNMENT.md`) advances a search
frontier through that range. The idle policy needs a way to *reason about* how much of a range
has been searched — to reconcile assignment accounting (I8), to reassign unsearched suffixes,
and to parameterise work reward and false-claim penalties — without requiring, at Stage 1, a
complete cryptographic proof that the claimed search actually occurred. This document specifies
the modeled interface that supplies that reasoning, and states precisely which parts are
simulated and which parts a real implementation would still have to build.

---

## 2. Interface elements

The modeled progress-verification interface consists of the following elements. Each is a
modeled quantity; none asserts real-hardware or real-cryptographic behaviour.

| Element | Definition |
|---|---|
| **Commitment interval** | The spacing (in nonce positions or in time) between successive progress commitments a searching miner is expected to emit. It fixes the granularity at which progress is reported and audited. |
| **Checkpoint index** | A monotonic index numbering successive commitments within a lease. Index `k` corresponds to the `k`-th commitment and its associated frontier. |
| **Reported frontier** | The nonce position up to which the miner *claims* its assigned range has been searched at a given checkpoint index. The searched prefix / unsearched suffix split (lease document, Section 4) is taken relative to the reported frontier. |
| **Audit probability** | `p_audit` — the modeled probability that a given reported frontier is selected for audit (a challenge that would, in a real system, require the miner to substantiate the claimed search). |
| **False-claim probability** | `p_false` — the modeled probability that a miner reports a frontier ahead of the work it actually performed (an overstated searched prefix). A behavioural parameter of a modeled adversary, not a property of honest miners. |
| **Detection probability** | `p_detect` — the modeled probability that a false claim is detected, given that it occurs and (where applicable) is audited. In the simulator this is a function of `p_audit` and the modeled audit strength, not an assertion about any real cryptographic scheme. |
| **Penalty interface** | The hook by which a detected false claim maps to a penalty. It is a *parameterised interface only* — the false-claim penalty term is defined in `STAGE_01_REWARD_PENALTY_INTERFACE.md`; no penalty value and no incentive-compatibility claim are made here. |

---

## 3. What is modeled vs. what a real implementation still requires

The two lists below are deliberately separated. Column (a) is the entirety of what the Stage-1
simulator represents. Column (b) is what a real cryptographic implementation would ADDITIONALLY
require and which Stage 1 does NOT provide.

### (a) What the simulator WILL model

1. Emission of progress commitments at the **commitment interval**, indexed by **checkpoint
   index**.
2. A **reported frontier** per checkpoint, used to derive searched prefix / unsearched suffix and
   to feed the I8 reconciliation.
3. A stochastic **audit** of reported frontiers governed by **audit probability** `p_audit`.
4. A modeled adversary that overstates its frontier with **false-claim probability** `p_false`.
5. A **detection** outcome governed by **detection probability** `p_detect`, deriving from
   `p_audit` and modeled audit strength.
6. Invocation of the **penalty interface** on detection (parameterised hook only; value set in
   the reward/penalty document).
7. The effect of all of the above on **assignment accounting** (searched/unsearched totals) and
   on the energy model's active power-time (a miner that truthfully searches pays hashing energy;
   a false claimant does not perform the corresponding work).

### (b) What a REAL cryptographic implementation WOULD STILL REQUIRE

1. A verifiable commitment scheme binding each reported frontier to work that *actually occurred*
   — not merely an asserted number. The simulator assumes such binding via `p_detect`; a real
   system must construct it.
2. A concrete audit/challenge protocol that a miner cannot satisfy without having performed the
   claimed hashing (i.e. a real basis for `p_detect > 0`), including its bandwidth, latency, and
   storage costs.
3. Soundness and completeness arguments for that protocol: bounds on the probability that a false
   claim survives audit, and that an honest claim is wrongly rejected — the real quantities the
   modeled `p_false`/`p_detect` stand in for.
4. Resistance to precomputation, replay, and delegation of the underlying work, and to
   grinding/selective disclosure of which positions were "searched".
5. Key management and authentication binding commitments to a `MinerID` and to the round's
   `(RoundID, TemplateID)` such that commitments cannot be transplanted across rounds/templates.
6. **A proof that the committed structure actually covers every nonce in the claimed prefix**
   (Section 5) — the core unmet requirement, recorded as an open research problem.
7. Adversary and threat modeling adequate to justify the parameter choices the simulator treats
   as given.

The mapping is one-directional: the simulator *consumes* the outcomes (detection, penalty
invocation, accounting effects) that a real implementation would have to *produce*. Stage 1 does
not close list (b).

### 3.1 Simulator ground truth vs protocol-level claim (CR5, two layers)

The abstraction is represented at two distinct layers, which MUST NOT be conflated:

- **Simulator ground truth:** `actual_frontier`, `actual_positions_evaluated`,
  `actual_solution_positions`, `actual_exhaustion`. The simulator **may** know actual exhaustion
  exactly.
- **Protocol-level claim:** `reported_frontier`, `reported_exhaustion`, `audit_selected`,
  `audit_result`, `claim_accepted_or_rejected`.

The modeled progress-verification abstraction does **not** prove actual exhaustion, and **no**
progress commitment verifies that no valid solution exists in the whole range. In **honest**
simulations, `EXHAUSTED_PENDING` eligibility **may** use actual cursor completion (ground truth).
In **adversarial** simulations, reported exhaustion is compared with ground truth and passed
through the modeled audit/detection abstraction. All findings are **modeled, not cryptographically
proven**.

---

## 4. Relationship to assignment accounting and to the early-stop path

- The reported frontier is the sole input this interface contributes to the searched-prefix /
  unsearched-suffix split used by I8 reconciliation
  (`STAGE_01_RANGE_LEASE_AND_REASSIGNMENT.md`, Section 8). A frontier that fails audit is treated
  as unreliable: its positions are NOT counted as searched and MAY be re-searched (lease document,
  Section 7, rule 2).
- This abstraction concerns **progress** (how much of a range was searched). It does NOT decide
  round termination on its own. A progress commitment only claims a searched frontier: it is
  **NOT** an early-stop trigger, and it **never** means "found a solution" (CR1). Halting active
  hashing for a round on the basis of a found solution is governed separately by the early-stop
  certificate and its strict validation order, including invariant I11 (no miner stops hashing on
  an unauthenticated message). See `STAGE_01_EARLY_STOP_CERTIFICATE.md`. Progress verification and
  early-stop certification are **completely separate mechanisms** and MUST NOT be conflated. A
  progress commitment says "I claim to have searched up to this frontier"; an early-stop
  certificate says "I found this exact valid solution".

---

## 5. OPEN RESEARCH PROBLEM — proof of exhaustive coverage

**Statement.** Construct a commitment scheme and audit protocol that *proves* a claimed searched
prefix was exhaustively covered — i.e. that every nonce position from `range_start` to the
reported frontier was actually evaluated against the committed template — at acceptable
verification cost, and with stated soundness bounds against an adversary that would prefer to
claim coverage it did not perform.

**Explicit caution (binding).** A Merkle commitment over reported positions **does not**, by
itself, prove that every nonce in the range was hashed. It can bind a set of disclosed values,
but it does not establish exhaustive coverage of the interval, and it is vulnerable to an
adversary committing to a sparse or fabricated set. Therefore **Merkle commitments MUST NOT be
proposed as a complete proof that every nonce was hashed** unless and until such a construction
is *formally justified*. Absent that justification, this remains an OPEN RESEARCH PROBLEM and is
recorded as out of scope for Stage 1.

**Consequence for Stage 1.** Because the coverage proof is open, everything in this document is a
**modeled progress-verification abstraction**, not a complete proof of exhaustion. The simulator
represents detection of false claims *probabilistically* (`p_detect`) precisely because the
sound cryptographic basis for that detection is not yet established. No exhaustion guarantee is
claimed.

---

## 6. Referenced identifiers

- **Interface elements:** commitment interval; checkpoint index; reported frontier; audit
  probability (`p_audit`); false-claim probability (`p_false`); detection probability
  (`p_detect`); penalty interface.
- **Invariants touched:** **I8** (searched positions counted here feed the reconciliation;
  unreliable frontiers are excluded). Coverage proof relates to the Section-C out-of-scope item
  "complete cryptographic proof of range exhaustion" in `STAGE_01_PROTOCOL_SCOPE.md`.
- **Related documents:** `STAGE_01_PROTOCOL_SCOPE.md`,
  `STAGE_01_RANGE_LEASE_AND_REASSIGNMENT.md`, `STAGE_01_EARLY_STOP_CERTIFICATE.md`,
  `STAGE_01_REWARD_PENALTY_INTERFACE.md`.

This document specifies a modeled abstraction only. It claims no cryptographic soundness, no
proof of exhaustion, and no incentive property.
