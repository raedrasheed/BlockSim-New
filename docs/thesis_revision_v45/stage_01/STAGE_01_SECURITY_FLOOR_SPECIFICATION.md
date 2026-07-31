# Stage 1 — PoCol Security-Floor Specification

**Document status:** Stage-1 specification-only. This document defines the time-varying
security quantities monitored under PoCol and a **parameterised** security-floor policy. It
does NOT assign final parameter values, and it does NOT prove 51% resistance or any
consensus-security property. The security floor is an **operational constraint intended to
bound security degradation in the modeled protocol**, not a proof. All quantities are
modeled.

Companion documents: `STAGE_01_PROTOCOL_SCOPE.md`, `STAGE_01_IDLE_POLICY_SPECIFICATION.md`,
`STAGE_01_ENERGY_MODEL_SPECIFICATION.md`, `STAGE_01_RESERVE_POLICY_SPECIFICATION.md`,
`STAGE_01_TERMINOLOGY.md`.

---

## 0. Naming and baseline (binding)

The algorithm is ALWAYS **PoCol**; the mechanism is **the idle policy within PoCol**.
Partitioning alone does not reduce fixed-horizon energy; savings arise only from reduced
active power-time. The security-floor policy exists because reducing active power-time
(moving honest miners into low-power states) must not be allowed to degrade the modeled
active honest hash rate below a monitored bound.

Miner states (8): `REGISTERED`, `RESERVE`, `ACTIVE_HASHING`, `EXHAUSTED_PENDING`,
`LOW_POWER_LISTEN`, `WAKING`, `OFFLINE`, `DISQUALIFIED`. Only `ACTIVE_HASHING` contributes
to the active hash rate.

---

## 1. Time-varying security quantities

The security floor is defined over **time-varying** quantities, sampled and event-updated
across the round (Section 2), never over a single start-of-round snapshot (Section 3).

### 1.1 Definitions

At modeled time `t` within a round, all three hash-rate quantities are computed
**deterministically from the active-state census** — the set of miners that are in
`ACTIVE_HASHING` at time `t`, read off **after** every miner's state has been determined:

- **`H_active(t)`** — total active hash rate: the sum of the hash rates of all miners in
  `ACTIVE_HASHING` at time `t`.
- **`H_honest(t)`** — active **honest** hash rate: the sum of the hash rates of the **honest**
  miners in `ACTIVE_HASHING` at time `t`.
- **`H_adversarial(t)`** — active **adversarial** hash rate: the sum of the hash rates of the
  **adversarial** miners in `ACTIVE_HASHING` at time `t`.
- **`q_adv(t)`** — instantaneous adversarial share of active hash rate:

        q_adv(t) = H_adversarial(t) / ( H_honest(t) + H_adversarial(t) ).           (S-1)

**Exact, deterministic decomposition (invariant I17).** By construction
`H_active(t) = H_honest(t) + H_adversarial(t)` holds **exactly** at every sampling and
event-update time: the active set is partitioned into its honest and adversarial contributors,
and `H_active`, `H_honest`, and `H_adversarial` are each read off the **same** active-state
census once miner states are fixed. The adversarial-behaviour model may sample or decide
**which adversarial miners** are in `ACTIVE_HASHING`; but **after** miner states are
determined, all three quantities are computed **deterministically** from that census.
`H_adversarial(t)` MUST NOT be sampled independently after `H_active(t)` has been computed —
doing so would break the identity. This is invariant **I17** (Section 6).

**Zero-active-hash-rate case.** `q_adv(t)` is defined whenever the denominator
`H_active(t) = H_honest(t) + H_adversarial(t)` is strictly positive. When `H_active(t) = 0`,
`q_adv(t)` is **undefined / NA** (not zero). Computing the hash-rate quantities does not
itself record any breach: the compute step (`ActiveHashRateUpdate`, Section 5.0) merely
reports `q_adv = NA` for this degenerate case. The corresponding **active-floor and
honest-floor breaches are recorded, and `SECURITY_RECOVERY` is triggered, solely by
`SecurityFloorEvaluate`** (Sections 4–5). `NA` is **never numerically compared** against
`maximum_adversarial_share`.

### 1.2 Which miner states contribute

Contribution to the hash-rate quantities is determined **solely by state**:

| State | Contributes to `H_active` / `H_honest` / `H_adversarial`? |
|---|---|
| `ACTIVE_HASHING` | **Yes** (honest ones to `H_honest`, adversarial ones to `H_adversarial`; both to `H_active`) |
| `LOW_POWER_LISTEN` | No |
| `RESERVE` | No |
| `WAKING` | No |
| `OFFLINE` | No |
| `DISQUALIFIED` | No |
| `REGISTERED` | No |
| `EXHAUSTED_PENDING` | No (short `P_hash` transient per CR3, but **not** credited as active hashing; assertion pending) |

Only `ACTIVE_HASHING` contributes. A miner in `REGISTERED`, `RESERVE`, `EXHAUSTED_PENDING`,
`LOW_POWER_LISTEN`, `WAKING`, `OFFLINE`, or `DISQUALIFIED` adds **nothing** to any of
`H_active`, `H_honest`, or `H_adversarial` — this holds even though `EXHAUSTED_PENDING` draws
the `P_hash` transient (CR3): drawing hashing power is not the same as contributing to the
active hash-rate census. This is the crux of Section 3: honest miners that go idle stop
contributing to `H_honest` while any always-on adversary keeps contributing to
`H_adversarial`.

---

## 2. Sampling, updates, and summaries

The quantities of Section 1 are tracked as functions of round time, not as one number.

### 2.1 Sampling and event-update times

The security quantities are refreshed at:

- **Periodic sampling times** — a modeled sampling cadence over the round; and
- **Event-update times** — every state transition that changes the active set, in
  particular: `ACTIVE_HASHING → EXHAUSTED_PENDING`, entry into `LOW_POWER_LISTEN`, any
  transition into or out of `WAKING`/`ACTIVE_HASHING` (including reserve activation),
  departures to `OFFLINE`, and `DISQUALIFIED` events.

Because a single honest miner going idle can move `H_honest` and `q_adv` discontinuously,
event-driven updates on active-set changes are required in addition to periodic sampling.

### 2.2 Derived observations and summaries

Over a round, PoCol records at least:

- **Minimum active hash-rate observation** — `min_t H_active(t)`.
- **Minimum honest hash-rate observation** — `min_t H_honest(t)`.
- **Maximum adversarial-share observation** — `max_t q_adv(t)`.
- **Time-weighted summaries** — time-weighted mean/integral of `H_active(t)`,
  `H_honest(t)`, and `q_adv(t)` over the round, so that a brief excursion is distinguished
  from a sustained one.
- **Breach-duration measurements** — for each limit, the cumulative and maximum-contiguous
  duration for which the limit is violated (the input to `maximum_security_breach_duration`,
  Section 4).

The extrema bound worst-case exposure; the time-weighted summaries characterise typical
exposure; the breach-duration measurements characterise persistence. All three families are
required — an acceptable mean does not excuse a deep or long minimum.

---

## 3. Why a fixed start-of-round adversarial fraction is INSUFFICIENT

A single start-of-round adversarial fraction `q_adv(0)` is **insufficient** under the idle
policy, and this is the central reason the quantities are time-varying.

At round start every participating miner may be in `ACTIVE_HASHING`, giving some
`q_adv(0)`. As the idle policy operates, **honest** miners legitimately move into
`LOW_POWER_LISTEN` (on adjudicated exhaustion) or are held in `RESERVE`, and each such
transition **removes their hash rate from `H_honest(t)`**. An adversary, by contrast, is
under no obligation to go idle and may keep all of its capacity in `ACTIVE_HASHING`.
Consequently:

- `H_honest(t)` can fall well below `H_honest(0)` as honest miners idle;
- `H_adversarial(t)` need not fall;
- therefore by (S-1), `q_adv(t)` can rise **monotonically above** `q_adv(0)` purely as a
  side effect of honest idling, even though no adversary added any capacity.

A policy keyed only to `q_adv(0)` would certify a round as safe at `t = 0` and remain blind
to an adversarial share that grows during the round precisely *because* the energy-saving
mechanism is working. The security floor must therefore be evaluated against the
time-varying `H_active(t)`, `H_honest(t)`, and `q_adv(t)`, with the extrema, time-weighted,
and breach-duration summaries of Section 2 — not against a start-of-round snapshot.

---

## 4. Parameterised security-floor policy (no final values)

The policy is defined by the following parameters. **No final numeric values are assigned at
Stage 1**; each is left symbolic and is a candidate for later calibration.

| Parameter | Meaning | Compared against |
|---|---|---|
| `minimum_active_hashrate` | Lower bound the active hash rate must not fall below | `H_active(t)`, esp. `min_t H_active(t)` |
| `minimum_honest_hashrate` | Lower bound the active honest hash rate must not fall below | `H_honest(t)`, esp. `min_t H_honest(t)` |
| `maximum_adversarial_share` | Upper bound the adversarial share must not exceed | `q_adv(t)`, esp. `max_t q_adv(t)` |
| `maximum_security_breach_duration` | Maximum tolerated duration of any limit violation before escalation | breach-duration measurements (Section 2.2) |
| `security_check_trigger` | The condition/cadence that causes a security-floor evaluation | sampling + event-update times (Section 2.1) |
| `reserve_activation_delay` | Delay between deciding to activate reserves and their contribution counting toward the floor | governs recovery timing (Section 5; reserve doc) |

The floor is defined jointly on hash-rate **level** (`minimum_active_hashrate`,
`minimum_honest_hashrate`), adversarial **share** (`maximum_adversarial_share`), and breach
**persistence** (`maximum_security_breach_duration`), evaluated whenever `security_check_trigger`
fires.

---

## 5. Behaviour when a limit is approached or violated

Evaluations fire per `security_check_trigger`. Outcomes are classified as follows and are
**recorded, never silently repaired** (invariant **I16**).

### 5.0 Separation of computation and evaluation (binding)

Computing the security quantities and evaluating them against the floor are owned by two
distinct procedures, and the split is binding:

- **`ActiveHashRateUpdate` (compute-only).** At each sampling or event-update time (Section
  2.1) it computes ONLY the hash-rate quantities `H_honest(t)`, `H_adversarial(t)`,
  `H_active(t)`, and the adversarial share `q_adv(t)` — or `q_adv = NA` when
  `H_active(t) = 0`. It does **NOT** record any breach and does **NOT** trigger
  `SECURITY_RECOVERY`. It never compares `NA` against any threshold.
- **`SecurityFloorEvaluate` (records and triggers).** It **ALONE** records security-floor
  breaches and triggers `SECURITY_RECOVERY`. Given the quantities produced by
  `ActiveHashRateUpdate`:
  - **If `H_active(t) == 0`:** `q_adv = NA`; record an **active-floor** breach **AND** a
    **honest-floor** breach; do **NOT** compare `NA` with `maximum_adversarial_share` (`NA`
    is never numerically compared); trigger `SECURITY_RECOVERY`.
  - **Otherwise:** evaluate the active-hash-rate threshold (`minimum_active_hashrate` against
    `H_active(t)`), the honest-hash-rate threshold (`minimum_honest_hashrate` against
    `H_honest(t)`), and the adversarial-share threshold (`maximum_adversarial_share` against
    `q_adv(t)`).
- **Duplicate suppression.** Duplicate breach records for the same `(event, threshold, time)`
  are suppressed: a given breach is recorded once, consistent with the recording discipline
  (I16, Section 5.7).

This division matches the executable pseudocode: `ActiveHashRateUpdate` is compute-only and
`SecurityFloorEvaluate` is the single owner of breach recording and recovery triggering.

### 5.1 Warning (limit approached, not yet violated)

A quantity is within a modeled margin of its limit (e.g. `H_honest(t)` nearing
`minimum_honest_hashrate`, or `q_adv(t)` nearing `maximum_adversarial_share`) but no limit is
yet crossed. The condition is recorded; the round may pre-stage recovery (e.g. mark reserves
as activation candidates) and may restrict further honest idling. No round state change is
forced yet.

### 5.2 Recoverable breach

A limit is crossed but for a duration within `maximum_security_breach_duration`, and
corrective action can restore the floor. The round moves toward the `SECURITY_RECOVERY`
round state, and recovery is attempted — principally **reserve activation** (Section 6) and
throttling of honest idling. The breach and its duration are recorded (I16). If recovery
restores the floor within `maximum_security_breach_duration`, the round proceeds.

### 5.3 Unrecoverable breach

A limit is crossed and either the breach persists beyond `maximum_security_breach_duration`,
or available recovery capacity (reserves, wake latency) is insufficient to restore the
floor. The breach is recorded as unrecoverable (I16). This escalates to round abort
(Section 5.4) and/or template refresh (Section 5.6); it is never silently repaired or
downgraded to look recoverable after the fact.

### 5.4 Round abort

Where a breach is unrecoverable (or a hard bound such as `minimum_active_hashrate` is
violated with no timely recovery path), the round transitions to `ROUND_ABORTED`. Abort is
an explicit recorded outcome, not a silent discard of the round.

### 5.5 Reserve activation

The primary recovery action for a floor breach on hash-rate level or adversarial share is to
activate reserve miners so that additional honest hash rate re-enters `ACTIVE_HASHING`,
raising `H_active(t)` / `H_honest(t)` and lowering `q_adv(t)`. Activation is tied to the
`SECURITY_RECOVERY` round state and paced by `reserve_activation_delay`; the mechanics
(selection, ordering, wake latency, uniqueness, failure handling) are specified in
`STAGE_01_RESERVE_POLICY_SPECIFICATION.md`. Reserve activation MUST NOT create overlapping
active ranges (invariant **I10**).

### 5.6 Template refresh

Where recovery requires a fresh basis for work — for example, to reorganise assignments
around the surviving active set, or following an abort — the protocol may perform a
`TEMPLATE_REFRESH` (new `TemplateID`), after which progress markers reset and assignments are
re-formed. Template refresh is a recorded transition, not a silent rewrite of round history.

### 5.7 Recording discipline (I16)

**Invariant I16:** security-floor breaches are **recorded, not silently repaired**. Every
warning, recoverable breach, unrecoverable breach, abort, activation, and refresh above is
logged with its triggering quantities and durations. No breach is masked, back-dated, or
resolved by editing the record; recovery actions are recorded alongside the breach that
prompted them.

---

## 6. Scope and non-claims (explicit)

- The security floor **does NOT prove 51% resistance** and does not prove any
  consensus-security property. It is an **operational constraint intended to bound security
  degradation in the modeled protocol** — a monitored floor with recorded breaches — not a
  security proof. Full consensus-security and Sybil-resistance proofs are out of scope (see
  `STAGE_01_PROTOCOL_SCOPE.md`, Section C).
- Progress/coverage claims used elsewhere rely on the **modeled progress-verification
  abstraction**, never a cryptographic proof.
- **No final numeric parameter values are assigned at Stage 1**; all six policy parameters
  are symbolic.
- No fairness or incentive property is claimed for the security-floor policy.

Invariant references: **I16** (breaches recorded, not silently repaired — Section 5);
**I17** (`H_active(t) = H_honest(t) + H_adversarial(t)` exactly, all three computed
deterministically from the active-state census after states are determined; `q_adv(t)` is
NA — not zero — and never numerically compared, with recorded active-floor and honest-floor
breaches (by `SecurityFloorEvaluate`, Section 5.0) when `H_active(t) = 0` — Section 1.1);
**I10**
(reserve activation creates no overlapping active ranges — Section 5.5). All symbols and
terms are defined in `STAGE_01_TERMINOLOGY.md`.
