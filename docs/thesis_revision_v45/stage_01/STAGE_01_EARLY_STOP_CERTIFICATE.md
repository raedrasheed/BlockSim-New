# Stage 1 — Early-Stop Certificate

**Document status:** Stage-1 specification-only. This document DEFINES the early-stop certificate
and its validation for the idle policy within PoCol. It does NOT claim that any mechanism here is
implemented, validated, or secure. Stage 1 SPECIFIES; it does NOT demonstrate any property of
what it specifies.

**Naming rule (binding).** The algorithm is ALWAYS **PoCol**. The mechanism here is part of
**the idle policy within PoCol** — an operating policy inside PoCol, not a new algorithm,
variant, or fork. The strings "PoCol-E", "Energy-Aware PoCol", and "Enhanced PoCol" MUST NOT
appear.

---

## 1. Purpose

When a valid solution is found for a round, continued brute-force hashing by every other miner
wastes active power-time. The idle policy uses an **early-stop certificate** to communicate, in
an authenticated and independently verifiable form, that a round may halt active hashing. The
certificate is the ONLY sanctioned trigger for a miner to stop hashing early. This is the direct
lever on the energy model: stopping active hashing converts `ACTIVE_HASHING` time into listening
or idle time, reducing `Σ_i P_hash,i · t_hash,i`.

The certificate carries a *found solution*; it is distinct from the progress-verification
abstraction (`STAGE_01_PROGRESS_VERIFICATION_ABSTRACTION.md`), which concerns how much of a range
was searched. A certificate asserts "a solution exists and is valid", not "a range was
exhausted".

**Generation rule (CR1, binding).** An early-stop certificate is generated **ONLY** after a
miner finds a valid candidate solution satisfying the current target. It **MUST** contain
exactly: `RoundID`, `TemplateID`, `AssignmentID`, `MinerID`, `nonce`, `candidate_hash`,
`target`, `signature/authentication`. It **MUST NOT** be generated from: aggregated progress
commitments; searched-domain coverage; claimed exhaustion; sufficient coverage; or a progress
frontier. Progress verification and early-stop certification are **completely separate
mechanisms**. A progress commitment says "I claim to have searched up to this frontier." An
early-stop certificate says "I found this exact valid solution."

---

## 2. Certificate fields

An early-stop certificate has exactly the following fields for Stage 1:

| Field | Meaning |
|---|---|
| `RoundID` | The round the solution belongs to. |
| `TemplateID` | The immutable block template the solution targets. |
| `AssignmentID` | The assignment under which the winning miner searched the nonce. |
| `MinerID` | The miner presenting the solution (the certificate signer). |
| `nonce` | The nonce value claimed to solve the round. |
| `candidate hash` | The claimed digest produced from the template and nonce. |
| `target` | The round target the candidate hash is claimed to satisfy. |
| `signature/authentication` | Authentication binding the certificate to `MinerID`. |

A certificate is *well-formed* only if all fields are present. Well-formedness is a
precondition, not acceptance; acceptance requires passing the full validation order (Section 3).

---

## 3. Validation order (strict, binding)

A verifier MUST evaluate a certificate in the following order, and MUST reject at the first step
that fails. The order is normative: later steps MUST NOT be relied upon before earlier steps pass,
and no step may be skipped.

1. **Round validity.** `RoundID` refers to the current, live round. A certificate for a stale,
   unknown, or already-closed round is rejected.
2. **Template validity.** `TemplateID` matches the immutable template committed for that round
   (invariant I3 pairing of RoundID + TemplateID). A mismatched or refreshed template is rejected.
3. **Assignment validity.** `AssignmentID` is a valid, current assignment for `MinerID` under the
   round and template (invariant I2: an accepted solution must lie in the signer's valid current
   assignment). A certificate referencing an expired, superseded, or foreign assignment is
   rejected.
4. **Nonce-range membership.** `nonce` lies within `[range_start, range_end]` of the referenced
   assignment. A nonce outside the signer's leased range is rejected even if it would otherwise
   satisfy the target — the solver must have owned the range it searched.
5. **Hash recomputation.** The verifier recomputes the digest from the committed template and the
   `nonce` and checks it equals `candidate hash`. A certificate whose recomputed digest differs
   from the claimed `candidate hash` is rejected.
6. **Target satisfaction.** The recomputed digest satisfies `target` under the committed
   template (the round acceptance predicate). A digest that does not meet target is rejected.
7. **Signer validity.** `signature/authentication` verifies for `MinerID`, and `MinerID` is a
   registered, non-`DISQUALIFIED` miner entitled to sign for the referenced assignment. A
   certificate with an invalid or unauthorised signature is rejected.

Only a certificate passing steps 1–7 is a **valid early-stop certificate**.

### 3.1 No stopping on unauthenticated messages (I11)

**Invariant I11 — false early-stop cannot end hashing without target verification.** No miner may
transition out of `ACTIVE_HASHING` on the basis of *merely receiving a message* asserting that a
solution exists. A miner may stop hashing early ONLY after it (or a trusted verifier acting under
the same order) has itself completed steps 1–7, including hash recomputation (step 5) and target
satisfaction (step 6). An unauthenticated, unverified, or partially verified message MUST NOT end
a miner's hashing. This is what prevents a forged or premature "stop" message from halting honest
work.

---

## 4. Verification behaviour and edge cases

### 4.1 Verification latency

Validation is not instantaneous. Each miner incurs a **verification latency** — the time to run
steps 1–7, dominated by hash recomputation (step 5). During this interval the miner **remains in
`ACTIVE_HASHING`**: it continues hashing while verifying, it remains included in `H_active(t)`,
and **no `VERIFYING` miner state is introduced**. The verification work is energy-accounted
separately as `E_verification` per Section 5. A miner MUST NOT anticipate the outcome and stop
before verification completes; only after **all** of steps 1–7 pass may it leave `ACTIVE_HASHING`,
and a failed certificate produces **no** hashing-state transition (I11).

### 4.2 Invalid-certificate behaviour

A certificate failing any step of Section 3 is **rejected** and has no effect on round state or on
the recipient's hashing: the recipient continues from the state it was in. Rejection MAY feed the
invalid-message penalty interface (`STAGE_01_REWARD_PENALTY_INTERFACE.md`); Stage 1 defines the
hook only, no value.

### 4.3 Replay protection

A certificate is bound to its `(RoundID, TemplateID, AssignmentID)` and is only valid while that
round is live (step 1). Once the round reaches `ROUND_ACCEPTED` (or otherwise closes), a
re-presented certificate for that round fails round validity and is rejected. Certificates MUST
NOT be replayable into a later round or against a refreshed template; the RoundID + TemplateID
binding (I3) and round-liveness check are the replay barrier.

### 4.4 Duplicate certificates

Receiving the *same* valid certificate more than once is idempotent: the first valid receipt drives
the stop/acceptance decision; subsequent identical copies are recognised as duplicates and cause no
additional state change and no double credit. Duplicate suppression keys on
`(RoundID, TemplateID, AssignmentID, nonce, candidate hash)`.

### 4.5 Competing valid certificates

Two or more *distinct* certificates may each pass steps 1–7 for the same round (for example
different nonces, possibly from different assignments, each satisfying target). Stage 1 specifies
that all such certificates are individually valid early-stop triggers — each independently
authorises halting active hashing — and that early-stop authorisation and accepted-block
selection are separate decisions.

Selection among competing valid solutions for the accepted block follows **network-arrival
semantics** (CR6), consistent with `STAGE_01_ROUND_STATE_MACHINE.md`:

1. Each valid solution receives a reproducible propagation/arrival time.
2. Local acceptance uses the **earliest valid arrival**.
3. Other valid solutions are recorded as competing/stale proposals.
4. Only exact arrival-time ties use a deterministic secondary rule: smallest `candidate_hash`,
   then smallest `MinerID`.

No global-oracle "smallest `(TemplateID, nonce, MinerID)`" primary rule is used, and **no
chain-wide fork-choice proof** is claimed. Stage 1 makes no fairness or tie-break guarantee
beyond this recorded ordering.

### 4.6 Delayed full-block propagation

A valid early-stop certificate is compact and may arrive *before* the full block it summarises. The
certificate authorises halting active hashing once verified (steps 1–7), but round finalisation to
`ROUND_ACCEPTED` still awaits the full block through `SOLUTION_PROPAGATION`. Between verified
early-stop and full-block arrival, a miner has stopped active hashing but the round is not yet
final; if the full block ultimately fails to arrive or fails validation, the round does not
finalise on that certificate and normal round-progression/recovery handling applies. Stage 1
specifies the ordering and does not claim a liveness guarantee for it.

---

## 5. Energy accounting during verification

Verification is not free and MUST be accounted in the energy model of `STAGE_01_PROTOCOL_SCOPE.md`.

- **Verification energy.** The interval a miner spends receiving a certificate and running
  steps 1–7 is modeled time during which the miner **remains in `ACTIVE_HASHING` and continues
  hashing**, so it stays included in `H_active(t)` and continues to accrue its `ACTIVE_HASHING`
  residency energy. The verification work (including the hash recomputation of step 5) is recorded
  **separately** as `E_verification` — a clearly identified coordination/verification energy
  increment added on top of the `ACTIVE_HASHING` residency energy and **not double-counted**. It
  is NOT folded into a listening term, and the miner does NOT leave `ACTIVE_HASHING` for
  verification.
- **Transition on stop.** A miner that, after successful verification, leaves `ACTIVE_HASHING` for
  a reduced-power state incurs the relevant transition term `E_transition,i` (and, on any later
  resumption, the `WAKING` term `P_wake,i · t_wake,i`).
- **Net effect.** Early stop reduces active power-time by ending `ACTIVE_HASHING` sooner, at the
  cost of the (smaller) verification and transition terms. Any ΔE benefit claimed at
  later stages must be net of these verification and transition costs, and must arise from reduced
  active power-time, never from partitioning (baseline A1). Stage 1 defines these terms; it claims
  no particular ΔE.

---

## 6. Referenced identifiers

- **Certificate fields:** `RoundID`, `TemplateID`, `AssignmentID`, `MinerID`, `nonce`,
  `candidate hash`, `target`, `signature/authentication`.
- **Round states touched:** `SOLUTION_PROPAGATION`, `ROUND_ACCEPTED`.
- **Miner state touched:** `ACTIVE_HASHING` (the state a verified certificate authorises leaving).
- **Invariants used here:** **I2** (accepted solution lies in the signer's valid current
  assignment); **I3** (certificate matches current RoundID + TemplateID); **I11** (no false
  early-stop ends hashing without target verification).
- **Related documents:** `STAGE_01_PROTOCOL_SCOPE.md`,
  `STAGE_01_RANGE_LEASE_AND_REASSIGNMENT.md`,
  `STAGE_01_PROGRESS_VERIFICATION_ABSTRACTION.md`, `STAGE_01_REWARD_PENALTY_INTERFACE.md`.

This document specifies the certificate and its validation only. It claims no security, liveness,
or fairness property.
