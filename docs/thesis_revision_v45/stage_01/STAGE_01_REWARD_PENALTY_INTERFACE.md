# Stage 1 — Reward and Penalty Interface

**Document status:** Stage-1 specification-only. This document DEFINES a **parameterised**
reward/penalty interface for the idle policy within PoCol. It fixes NO final values, and it makes
NO claim of incentive compatibility, fairness, or Sybil resistance. Stage 1 SPECIFIES the
interface; it does NOT demonstrate any property of it.

**Naming rule (binding).** The algorithm is ALWAYS **PoCol**. The mechanism here is part of
**the idle policy within PoCol** — an operating policy inside PoCol, not a new algorithm,
variant, or fork. The strings "PoCol-E", "Energy-Aware PoCol", and "Enhanced PoCol" MUST NOT
appear.

**Binding disclaimer (stated up front).** This is a **parameterised interface only**. Every
component below is a named hook with a parameter, not a set value. No text in this document
asserts that the interface is incentive-compatible, fair, or Sybil-resistant. Those properties
are explicitly OUT OF SCOPE at Stage 1 (see also `STAGE_01_PROTOCOL_SCOPE.md`, Section C).

---

## 1. Purpose and stance

The idle policy changes *when* and *whether* miners hash. Any later study of whether that policy
behaves well under self-interested participants needs a place to attach rewards and penalties.
This document specifies that attachment surface — the set of reward and penalty components and the
attack surfaces they are meant to bear on — as a **parameterised interface**. It deliberately does
NOT choose values, does NOT prove any equilibrium, and does NOT assert that following the interface
yields honest behaviour. Choosing and analysing parameters is later-stage work; asserting
incentive properties is out of scope entirely at Stage 1.

Each component is specified as a hook `component(context) -> parameterised amount`, where the
amount is left as a symbolic parameter. Parameters are the levers a later stage would set and
study; Stage 1 fixes only their existence, their triggering condition, and their sign
(reward vs. penalty).

---

## 2. Reward components (parameterised)

| Component | Triggering condition | Parameter (symbolic, unset) |
|---|---|---|
| **Work reward** | Reliable, provenance-complete searched progress over a leased range (searched prefix counted per I8, at most once per position per template). | `r_work` per unit searched |
| **Availability reward** | Remaining available for participation over the horizon, including sanctioned `LOW_POWER_LISTEN` and `RESERVE` readiness. | `r_avail` per unit availability |
| **Winner reward** | Presenting a valid early-stop certificate whose block finalises the round (`ROUND_ACCEPTED`). | `r_win` per accepted round |
| **Reserve-activation reward** | A `RESERVE` miner promoted to `ACTIVE_HASHING` (or to sanctioned coverage) on demand, incurring the `WAKING` transition. | `r_reserve` per activation |
| **Reassignment reward** | Taking over and searching a reassigned range or unsearched suffix under a provenance-complete reassignment (I9). | `r_reassign` per reassignment served |

All reward hooks read only quantities that the rest of Stage 1 already defines (searched prefix,
availability time, accepted certificate, activation event, reassignment lineage). No reward hook
introduces a new observable.

---

## 3. Penalty components (parameterised)

| Component | Triggering condition | Parameter (symbolic, unset) |
|---|---|---|
| **Abandonment penalty** | Ceasing sanctioned progress on a live lease (holder-originated abandonment) leaving an unsearched suffix to be reassigned. | `q_abandon` per abandonment |
| **False-claim penalty** | A reported frontier detected as overstated under the progress-verification abstraction (detection probability `p_detect`). | `q_false` per detected false claim |
| **Invalid-message penalty** | Emitting a certificate or message that fails validation (e.g. an early-stop certificate rejected under the strict validation order). | `q_invalid` per invalid message |

Penalty hooks are the negative-sign counterparts to the rewards; like the rewards they are
parameterised only. The false-claim penalty attaches to the penalty interface of
`STAGE_01_PROGRESS_VERIFICATION_ABSTRACTION.md`; the invalid-message penalty attaches to the
invalid-certificate behaviour of `STAGE_01_EARLY_STOP_CERTIFICATE.md`.

---

## 4. Attack surfaces

The following attack surfaces are the reason the interface exists. Listing an attack surface here
is NOT a claim that the interface defends against it. Column "Stage-5 modeling" states, for each,
whether it is intended to be MODELED in the Stage-5 simulation study or is OUT OF SCOPE.

| Attack surface | Description | Stage-5 modeling |
|---|---|---|
| **Free riding** | Collecting availability/participation credit while performing little or no actual searching. | MODELED in Stage 5 |
| **Self-reported hash-rate manipulation** | Overstating one's own hash rate to gain assignment or reward advantage. | MODELED in Stage 5 |
| **Assignment splitting** | Manipulating how ranges are split/held to farm per-assignment rewards without adding coverage. | MODELED in Stage 5 |
| **Sybil registration** | Registering many identities to multiply availability/registration-linked rewards. | OUT OF SCOPE at Stage 1 (no Sybil-resistance claim); a modeled surface flagged for later study |
| **Withholding progress** | Not emitting progress commitments to obscure how much of a range was searched. | MODELED in Stage 5 |
| **Withholding valid solutions** | Delaying or suppressing a found valid solution (e.g. to extend one's own reward window). | MODELED in Stage 5 |
| **Intentional delayed wake-up** | A `RESERVE`/`LOW_POWER_LISTEN` miner deliberately waking slowly to avoid work while retaining availability standing. | MODELED in Stage 5 |
| **Strategic early-exhaustion claims** | Claiming a range is exhausted (or a stop is justified) earlier than truthful to shed work. | MODELED in Stage 5 |

### 4.1 Scope boundary (binding)

- **Modeled in Stage 5:** free riding; self-reported hash-rate manipulation; assignment splitting;
  withholding progress; withholding valid solutions; intentional delayed wake-up; strategic
  early-exhaustion claims. "Modeled" means the Stage-5 simulator will *represent* the behaviour and
  observe the parameterised interface's response — NOT that Stage 5 proves the interface defeats it.
- **Out of scope at Stage 1:** Sybil registration is not defended against and no Sybil-resistance
  property is claimed. More broadly, any claim of incentive compatibility, fairness, or
  Sybil resistance is out of scope; the interface is specified, not analysed.

---

## 5. Explicit non-claims (binding)

Stated explicitly and without qualification:

1. **No incentive-compatibility claim.** Nothing here asserts that honest participation is a best
   response, an equilibrium, or otherwise incentivised, for the idle policy or for base PoCol.
2. **No fairness claim.** Nothing here asserts fair distribution of rewards, fair assignment, or
   fair treatment across miners.
3. **No Sybil-resistance claim.** Nothing here asserts resistance to Sybil registration or to any
   identity-multiplication attack.

The interface is a set of parameterised hooks and a catalogue of attack surfaces. Whether any
parameterisation of it yields desirable incentive behaviour is a later-stage research question and
is NOT answered — or asserted — at Stage 1.

---

## 6. Referenced identifiers

- **Reward components:** work reward; availability reward; winner reward; reserve-activation
  reward; reassignment reward.
- **Penalty components:** abandonment penalty; false-claim penalty; invalid-message penalty.
- **Miner/round states touched:** `RESERVE`, `LOW_POWER_LISTEN`, `WAKING`, `ACTIVE_HASHING`,
  `EXHAUSTED_PENDING`; `ROUND_ACCEPTED`.
- **Invariants referenced:** **I8** (searched progress counted for work reward), **I9**
  (provenance for reassignment reward).
- **Related documents:** `STAGE_01_PROTOCOL_SCOPE.md`,
  `STAGE_01_RANGE_LEASE_AND_REASSIGNMENT.md`,
  `STAGE_01_PROGRESS_VERIFICATION_ABSTRACTION.md`, `STAGE_01_EARLY_STOP_CERTIFICATE.md`.

This document specifies a parameterised interface only. It claims no incentive compatibility, no
fairness, and no Sybil resistance.
