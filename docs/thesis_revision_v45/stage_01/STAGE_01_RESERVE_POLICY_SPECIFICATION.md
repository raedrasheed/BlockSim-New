# Stage 1 — PoCol Reserve Policy Specification

**Document status:** Stage-1 specification-only. This document specifies how reserve miners
are selected, activated, assigned ranges, and handled on failure under **the idle policy
within PoCol**. It does NOT claim the reserve policy is implemented, validated, secure, fair,
or incentive-compatible, and it assigns NO final numeric parameter values. All quantities are
modeled.

Companion documents: `STAGE_01_PROTOCOL_SCOPE.md`, `STAGE_01_IDLE_POLICY_SPECIFICATION.md`,
`STAGE_01_ENERGY_MODEL_SPECIFICATION.md`, `STAGE_01_SECURITY_FLOOR_SPECIFICATION.md`,
`STAGE_01_TERMINOLOGY.md`.

---

## 0. Naming and baseline (binding)

The algorithm is ALWAYS **PoCol**; the mechanism is **the idle policy within PoCol**.
Partitioning alone does not reduce fixed-horizon energy; savings arise only from reduced
active power-time. Reserves are one such source: a held-out reserve draws no active hashing
power — its residency draw is the low-power standby power `P_reserve` (= `P_listen`), **not**
`P_offline` (canonical state-to-power mapping, CR3;
`STAGE_01_ENERGY_MODEL_SPECIFICATION.md` §1.0) — until it is activated to restore hash rate.
Activation passes the reserve through `WAKING`, charging wake energy `P_wake,i * t_wake,i`
plus any `E_transition,i` (Section 4).

Miner states (8): `REGISTERED`, `RESERVE`, `ACTIVE_HASHING`, `EXHAUSTED_PENDING`,
`LOW_POWER_LISTEN`, `WAKING`, `OFFLINE`, `DISQUALIFIED`. A reserve is a `REGISTERED` miner
held in `RESERVE`; activation passes it through `WAKING` into `ACTIVE_HASHING`. Only
`ACTIVE_HASHING` contributes to the active hash rate.

---

## 1. Reserve selection

### 1.1 The reserve set

Registered miners not currently assigned an active range may be held in `RESERVE`: admitted
and available, drawing no active hashing power but the low-power standby power `P_reserve`
(= `P_listen`, **not** `P_offline`; CR3). From this reserve set the protocol draws
activations when the security-floor policy calls for recovery
(`STAGE_01_SECURITY_FLOOR_SPECIFICATION.md`).

### 1.2 Two sourcing disciplines for the activation order

Selection — which reserves are chosen and in what order — may be derived either **(a)
deterministically from a seed** or **(b) from protocol randomness (a beacon)**. Both are
specified here with their predictability/manipulation trade-offs; Stage 1 does not fix a
final choice.

**(a) Deterministic from a seed.**
- *Mechanism.* The activation order is a deterministic function of a published seed (for
  example bound to the `TemplateID` and round identity) over the reserve set.
- *Advantage.* Reproducible and auditable: any observer can recompute the intended order and
  check that activations followed it, which supports the recording discipline (I16) and
  detection of out-of-order activation.
- *Predictability/manipulation risk.* A deterministic order is **predictable in advance**.
  An adversary who knows the seed can foresee which reserves activate and when, and may try
  to influence the seed inputs, or position/withhold its own miners in the order, to bias
  recovery. Seed-grinding (choosing inputs that yield a favourable order) is the principal
  manipulation vector.

**(b) From protocol randomness (a beacon).**
- *Mechanism.* The activation order is drawn from a protocol randomness source revealed at or
  near activation time, so the order is not known in advance.
- *Advantage.* Harder to predict and to pre-position against; reduces the value of
  anticipatory manipulation.
- *Predictability/manipulation risk.* Shifts the risk to the **randomness source itself**: a
  biasable or grindable beacon (last-revealer advantage, withheld contributions) lets an
  adversary influence the draw. Randomness that is late or unavailable can also delay
  recovery, interacting with `reserve_activation_delay` (Section 8).

**Common requirement.** Under either discipline the resulting activation order MUST be
recorded so that actual activations can be checked against the intended order (I16), and the
selection MUST NOT, by itself, cause overlapping active ranges (I10, Section 6).

---

## 2. How many reserves may be activated

The number of reserves activated in response to a floor condition is a **parameterised
quantity, not fixed at Stage 1**. It is bounded above by the size of the reserve set and is
governed by the security-floor deficit: enough reserves to restore `H_active(t)` /
`H_honest(t)` above `minimum_active_hashrate` / `minimum_honest_hashrate` and to bring
`q_adv(t)` below `maximum_adversarial_share`, without over-activating beyond the recovery
need (which would forfeit the energy saving the idle policy exists to obtain). The exact
count and any per-trigger cap are left symbolic for later calibration.

---

## 3. Activation ordering

Reserves are activated in the **order fixed by the selected sourcing discipline** (Section
1.2) — deterministic-from-seed or beacon-derived — and paced by `reserve_activation_delay`
(Section 8). Activation is incremental: the protocol may activate in steps, re-evaluating the
security quantities after each step (per `security_check_trigger`) so that it activates only
as many reserves as recovery requires. Actual activation order MUST match the recorded
intended order; deviations are recorded (I16).

---

## 4. Wake latency and wake energy

A reserve does not contribute hash rate instantaneously. On activation it transitions
`RESERVE → WAKING → ACTIVE_HASHING`:

- **Wake latency** — the modeled time spent in `WAKING` before the miner contributes to
  `H_active(t)`. Until it reaches `ACTIVE_HASHING`, a waking reserve contributes **nothing**
  to any security quantity (`STAGE_01_SECURITY_FLOOR_SPECIFICATION.md`, Section 1.2). Wake
  latency plus `reserve_activation_delay` sets how quickly recovery can take effect.
- **Wake energy** — the modeled energy of waking, charged as `P_wake,i * t_wake,i` (the
  power drawn while waking over the wake duration) plus any fixed `E_transition,i` for the
  spin-up/mode change. These are the same terms defined normatively in
  `STAGE_01_ENERGY_MODEL_SPECIFICATION.md`. Wake and transition costs are real overhead and
  count against the saving; over-activation therefore has an energy price (Section 2 and the
  energy-model necessary conditions).

---

## 5. Assignment creation for activated reserves

### 5.1 Fresh vs. reassigned ranges

On activation a reserve must receive an assignment bound to the current `TemplateID`. Two
sources are admissible:

- **Fresh ranges** — a previously unassigned region of the nonce domain, created for the
  activated reserve. Used when uncovered domain remains.
- **Reassigned ranges** — a range (or the unsearched tail of one) reclaimed from a departed,
  revoked, lease-expired, or abandoned assignment (per the termination taxonomy in
  `STAGE_01_IDLE_POLICY_SPECIFICATION.md`). Used to close coverage gaps left by miners that
  stopped before true exhaustion.

Either way, the new assignment is bound to the current `TemplateID`; positions searched under
a prior template do not carry over. Whether a given activation uses fresh or reassigned
ranges is determined by the coverage state at activation time, not fixed a priori.

### 5.2 Assignment uniqueness

Every assignment created for an activated reserve MUST be **unique and disjoint** from all
other currently active assignments for the same `TemplateID`. An activated reserve is never
given a range that overlaps a range currently held by an `ACTIVE_HASHING` miner (Section 6).

---

## 6. No overlapping active ranges (I10)

**Invariant I10:** reserve activation creates no overlap. The assignment given to an
activated reserve MUST NOT overlap any range currently active under the same `TemplateID`.
Concretely:

- A reassigned range may be granted to a reserve only after the prior holder's claim on it
  is validly ended (departure, revocation, lease expiry, or adjudicated exhaustion) — never
  while the prior holder is still `ACTIVE_HASHING` on it.
- Fresh ranges are carved only from domain not currently assigned to any active miner.
- The union of active assignments after activation remains a set of **disjoint** ranges over
  the nonce domain for that `TemplateID`.

Reserve activation is thus a coverage-preserving reassignment/extension operation; it adds
active hash rate without duplicating search effort or creating conflicting claims.

---

## 7. Reserve wake failure and repeated failure

### 7.1 A reserve fails to wake

If an activated reserve does not reach `ACTIVE_HASHING` within its expected wake window
(fails to wake, or is unreachable during `WAKING`):

- It contributes no hash rate, so the security deficit it was meant to cover is **not**
  closed. The floor evaluation therefore still shows the deficit (recorded, not silently
  repaired — I16).
- The protocol proceeds to the **next reserve in the activation order** (Section 3),
  activating additional reserves to make up the shortfall, subject to the available reserve
  set and `reserve_activation_delay`.
- The range tentatively earmarked for the failed reserve MUST NOT be treated as covered; it
  remains an uncovered tail / assignable range and may be assigned to a subsequent reserve —
  without ever overlapping an active range (I10). The failed reserve is not credited with any
  progress.

### 7.2 Repeated reserve failure

If reserves repeatedly fail to wake such that activation cannot restore the floor:

- The failures and the persisting deficit are recorded (I16), and the breach-duration
  measurement continues to accrue against `maximum_security_breach_duration`
  (`STAGE_01_SECURITY_FLOOR_SPECIFICATION.md`, Section 2.2).
- If the reserve set is exhausted or the deficit persists beyond
  `maximum_security_breach_duration`, the condition escalates as an **unrecoverable breach**:
  round abort (`ROUND_ABORTED`) and/or template refresh (`TEMPLATE_REFRESH`), per the
  security-floor policy (Section 5.3–5.6 there). Escalation is an explicit recorded outcome,
  never a silent repair.
- Miners that repeatedly fail to wake when activated may be moved toward `OFFLINE` and, where
  warranted, `DISQUALIFIED`, so that the protocol does not keep depending on a reserve that
  does not materialise.

---

## 8. Tie to SECURITY_RECOVERY and reserve_activation_delay

Reserve activation is bound to the `SECURITY_RECOVERY` round state and paced by
`reserve_activation_delay`:

- **Trigger.** Activation is initiated when the security-floor policy classifies a breach as
  recoverable and moves the round toward `SECURITY_RECOVERY`
  (`STAGE_01_SECURITY_FLOOR_SPECIFICATION.md`, Section 5.2/5.5). Reserves are not activated
  outside a floor-driven recovery need (activating without need would forfeit energy saving
  for no security benefit).
- **`reserve_activation_delay`.** The parameterised delay between the decision to activate and
  the point at which the activated reserve's hash rate counts toward the floor. It composes
  with wake latency (Section 4) to determine total recovery time, and it bounds how fast the
  security quantities can be restored. **No final value is assigned at Stage 1.**
- **Re-evaluation.** After each activation step plus `reserve_activation_delay`, the security
  quantities are re-evaluated (per `security_check_trigger`); recovery continues, completes
  (round leaves `SECURITY_RECOVERY`), or escalates to unrecoverable handling (Section 7.2).

---

## 9. Scope, invariant references, and non-claims

- The reserve policy is **specified structure only**. No implementation, validation,
  security, fairness, or incentive property is claimed. Selection predictability/manipulation
  risks are stated (Section 1.2) but no resistance result is asserted.
- Range coverage/exhaustion relies on the **modeled progress-verification abstraction**,
  never a cryptographic proof.
- **No final numeric parameter values are assigned at Stage 1** (reserve count,
  `reserve_activation_delay`, wake latency, per-trigger caps are all symbolic).
- Invariant references: **I10** (reserve activation creates no overlapping active ranges —
  Section 6); **I16** (breaches and activation outcomes recorded, not silently repaired —
  Sections 7–8). Energy terms `P_wake`, `t_wake`, `E_transition` are defined normatively in
  `STAGE_01_ENERGY_MODEL_SPECIFICATION.md`.

All symbols and terms are defined in `STAGE_01_TERMINOLOGY.md`.
