# Stage 1 — PoCol Energy Model Specification

**Document status:** Stage-1 specification-only. This document states the **normative energy
accounting model** for PoCol and for the idle policy within PoCol, defines every term and
its units, and specifies the conditions for a positive saving. It does NOT claim any
particular energy value is achieved, validated, or measured on real hardware. **No final
numeric parameter values are assigned at Stage 1.** All quantities are modeled.

Companion documents: `STAGE_01_PROTOCOL_SCOPE.md`, `STAGE_01_IDLE_POLICY_SPECIFICATION.md`,
`STAGE_01_SECURITY_FLOOR_SPECIFICATION.md`, `STAGE_01_RESERVE_POLICY_SPECIFICATION.md`,
`STAGE_01_TERMINOLOGY.md`.

---

## 0. Naming and baseline (binding)

The algorithm is ALWAYS **PoCol**; the mechanism is **the idle policy within PoCol** (an
operating policy inside PoCol, not a new algorithm or variant). Nonce-domain **partitioning
alone does NOT reduce total fixed-horizon energy**. Any reduction arises ONLY from **reduced
active power-time** (low-power listening, reserve operation, reduced participation), never
from partitioning.

**Frozen reference setting (accounting invariant A1).** Over the fixed horizon
`T = 10,000 s` at aggregate hash rate `141 TH/s` and efficiency `21.5 J/TH`, active power is
`P_active = 141 × 21.5 = 3031.5 W`, and continuous full-participation energy is

    E_continuous_control = 3031.5 W × 10,000 s = 30,315,000 J
                         = 30,315,000 / 3,600,000 kWh
                         = 8.420833333 kWh.

A1 is **invariant to how the nonce domain is partitioned**. This value is the explicit
matched control against which the idle policy's saving is defined (Section 4).

The eight miner states are `REGISTERED`, `RESERVE`, `ACTIVE_HASHING`, `EXHAUSTED_PENDING`,
`LOW_POWER_LISTEN`, `WAKING`, `OFFLINE`, `DISQUALIFIED`. Only `ACTIVE_HASHING` contributes
to the active hash rate (and hence to `P_hash,i * t_hash,i`).

---

## 1. Normative per-miner energy model

For each miner `i`, the modeled energy over the fixed horizon is the **state-complete
sum** over the eight miner states

    E_i = Σ_{s∈States} (P_{i,s} · t_{i,s})
        + E_transition,i
        + E_coordination,i
        + E_verification,i                                            (E-1)

where `States = {REGISTERED, RESERVE, ACTIVE_HASHING, EXHAUSTED_PENDING,
LOW_POWER_LISTEN, WAKING, OFFLINE, DISQUALIFIED}`, `P_{i,s}` is the single residency
power of miner `i` in state `s` fixed by the canonical state-to-power mapping (§1.0),
and `t_{i,s}` is the time miner `i` spends in state `s` over the horizon.
`E_verification,i` is a **separate event-energy term** (§1.0), not folded into
`P_hash·t_hash`.

This is the normative accounting model. Every energy statement about PoCol at Stage 1 is
expressed through (E-1), through the network total (E-2), or through the saving (E-3).

### 1.0 Canonical state-to-power mapping (single reusable mapping)

The following is the **single, canonical state-to-power mapping** reused across every
Stage-1 document. Each of the eight states has exactly **one** residency power (no numeric
values at Stage 1; ordering `P_offline ≤ P_listen = P_reserve = P_registered ≤ P_hash`,
with `P_wake` a transient):

| Miner state | Residency power | Contributes to `H_active(t)`? | Reward-eligible? |
|-------------|-----------------|:-----------------------------:|:----------------:|
| REGISTERED | `P_registered` (= `P_listen`) | No | No |
| RESERVE | `P_reserve` (= `P_listen`; low-power standby, **not** `P_offline`) | No | Availability only |
| ACTIVE_HASHING | `P_hash` | **Yes** | Yes |
| EXHAUSTED_PENDING | `P_hash` (short transient; no idle saving credited here) | No | Yes |
| LOW_POWER_LISTEN | `P_listen` | No | Yes (idle credit) |
| WAKING | `P_wake` | No | Yes |
| OFFLINE | `P_offline` | No | No |
| DISQUALIFIED | `P_offline` | No | No |

This table is the **single reusable mapping**: every other Stage-1 document that assigns a
residency power to a state, or states which states contribute to `H_active(t)`, defers to
it. `E_verification,i` is a **separate event-energy term** (not folded into
`P_hash·t_hash`): `t_hash` still counts the full active duration and `E_verification` is the
incremental cost of validating a **received** early-stop certificate while the miner remains
in `ACTIVE_HASHING` (CR2), so it is not double-counted.

### 1.1 Term-by-term definitions and units

**Convention.** Power is in **watts (W)**; time (duration) is in **seconds (s)**; a
power–time product `P × t` is in **joules (J)**. Energy is converted to **kilowatt-hours
(kWh)** by dividing joules by **3,600,000** (since `1 kWh = 3.6 × 10⁶ J`). All powers are
non-negative; all durations are non-negative (invariant **I5**). Each miner is in exactly
one state at any instant, so the duration terms partition the horizon (Section 3).

| Term | Meaning | Unit | Contributing state(s) | Contributes to active hash rate? |
|---|---|---|---|---|
| `P_hash,i` | Power drawn while actively hashing; also the residency power of the short `EXHAUSTED_PENDING` transient | W | `ACTIVE_HASHING`, `EXHAUSTED_PENDING` | — |
| `t_hash,i` | Total time miner `i` spends actively hashing (full active duration) | s | `ACTIVE_HASHING` | Yes |
| `P_listen,i` | Power drawn while low-power listening; also the residency power of `REGISTERED` (`P_registered`) and `RESERVE` (`P_reserve`) | W | `LOW_POWER_LISTEN`, `REGISTERED`, `RESERVE` | — |
| `t_listen,i` | Total time miner `i` spends low-power listening | s | `LOW_POWER_LISTEN` | No |
| `P_wake,i` | Power drawn while waking (resuming to hash) | W | `WAKING` | — |
| `t_wake,i` | Total time miner `i` spends waking | s | `WAKING` | No |
| `P_offline,i` | Power drawn while offline; also the residency power of `DISQUALIFIED` | W | `OFFLINE`, `DISQUALIFIED` | — |
| `t_offline,i` | Total time miner `i` spends offline | s | `OFFLINE` | No |
| `E_transition,i` | Fixed/aggregate transition energy for state changes not fully captured by a single `P×t` term (spin-up/down, mode switches) | J (→ kWh via /3.6×10⁶) | transitions | No |
| `E_coordination,i` | Modeled energy of coordination for miner `i` (progress commitments, assignment/lease messaging, security-floor participation, reserve activation signalling) | J (→ kWh via /3.6×10⁶) | coordination | No |
| `E_verification,i` | Modeled incremental energy of validating a **received** early-stop certificate while the miner remains in `ACTIVE_HASHING`; a clearly identified coordination/verification increment added on top of the `ACTIVE_HASHING` residency energy, **not** double-counted (CR2) | J (→ kWh via /3.6×10⁶) | verification | No |

Notes on conventions:

- **Product terms** (`P_hash,i * t_hash,i`, etc.) are computed in joules and summed with the
  lump terms `E_transition,i`, `E_coordination,i`, and `E_verification,i`, which are
  **already energies** (J), before any conversion to kWh. Do NOT double-convert.
- **`REGISTERED`, `EXHAUSTED_PENDING`, `WAKING`, `DISQUALIFIED` accounting.** Per the
  canonical mapping (§1.0), `REGISTERED` draws `P_registered` (= `P_listen`);
  `EXHAUSTED_PENDING` draws `P_hash` for its short transient (no idle saving is credited
  there); `WAKING` is charged through `P_wake,i * t_wake,i`; and `DISQUALIFIED` draws
  `P_offline`. Each state has exactly one residency power — there is no "distinct level"
  fallback and no residual bucket.
- **`RESERVE` draw** is accounted at `P_reserve` (= `P_listen`; low-power standby), **not**
  as offline-class draw: a held-out reserve draws no active hashing power but does draw the
  low-power standby power while listening for its activation signal. Its later activation
  cost is the wake and transition terms.
- **`E_verification` accounting.** A miner validating a received early-stop certificate stays
  in `ACTIVE_HASHING` and keeps drawing `P_hash`; the incremental verification cost is
  charged **separately** as `E_verification,i`, not folded into `P_hash·t_hash` and not
  double-counted (CR2).
- **PATH-B resume accounting.** When a miner that paused on a verified valid-solution stop
  (PATH B: assignment PAUSED in `LOW_POWER_LISTEN`) later resumes because the full block was
  rejected, unavailable, or timed out, the resume transition
  `LOW_POWER_LISTEN → WAKING → ACTIVE_HASHING` incurs wake and transition energy that is
  charged entirely through the existing `P_wake,i * t_wake,i` (WAKING residency) and
  `E_transition,i` (mode-switch) terms. No separate term is introduced for PATH-B resume and
  no resume energy is left unaccounted.
- **Sign conventions.** No term is negative. A "saving" is never represented as a negative
  energy term; it is the *difference of two totals* (Section 4).

---

## 2. Per-miner state–energy conservation (I6)

**Invariant I6:** for each miner `i`, the sum of the state-attributed energies equals that
miner's total energy `E_i`. That is, the eight state-residency energies plus the three event
terms `E_transition,i + E_coordination,i + E_verification,i` on the right-hand side of (E-1)
are exhaustive and mutually exclusive by state/category, so no energy is created or lost in
attribution:

    E_i = Σ over states/categories of (state energy of miner i).       (I6)

**Energy invariant.** `E_i` equals the sum of the eight state-residency energies plus
`E_transition,i + E_coordination,i + E_verification,i` exactly, with **no residual bucket**.
Every joule miner `i` draws is charged to exactly one term of (E-1); there is no residual,
unattributed energy bucket.

---

## 3. Duration reconciliation to the horizon (I5)

**Invariant I5:** durations are `≥ 0` and reconcile to the fixed horizon. Because each miner
occupies exactly one state at a time over `[0, T]`, the state durations partition the
horizon for each miner `i`:

    Σ_{s∈States} t_{i,s} = T,                                          (I5)

summed over all eight miner states, with every term `≥ 0`. **There is NO residual /
`t_other` bucket:** every instant of the horizon is charged to exactly one of the eight
state durations (`REGISTERED`, `RESERVE`, `ACTIVE_HASHING`, `EXHAUSTED_PENDING`,
`LOW_POWER_LISTEN`, `WAKING`, `OFFLINE`, `DISQUALIFIED`), so the accounting is complete
without an "other" catch-all. No duration may be negative, and the durations for a miner may
not sum to more than the horizon (no double-counted time) nor be silently truncated below it
(no vanished time).

---

## 4. Network total and the saving (I7)

### 4.1 Network total (I7)

**Invariant I7:** per-miner energies sum to the network energy:

    E_total = Σ_i E_i.                                                  (E-2, I7)

There is no network-level energy that is not the sum of per-miner energies, and no per-miner
energy is omitted from the sum. `E_total` under PoCol with the idle policy enabled is
denoted `E_idle_policy`.

### 4.2 The saving relative to an explicit matched control (E-3)

The Stage-1 comparison quantity is

    ΔE = E_continuous_control − E_idle_policy.                          (E-3)

The control and idle-policy scenario are **matched at the start on capacity, not on realised
work**. They match on: the installed/registered **aggregate hash-rate capacity** at the
start; miner hardware and efficiency; fixed difficulty; target; the fixed observation
horizon; and workload/template rules where applicable. **They do not execute the same total
work.** `E_continuous_control` is exactly the A1 value (8.420833333 kWh) computed for this
matched frozen reference setting under **continuous full participation** — every miner in
`ACTIVE_HASHING` for the whole horizon. `E_idle_policy` is `E_total` from (E-2) under PoCol
with the idle policy enabled for the same matched setting. Under the idle policy `H_active(t)`
may decrease, realised hash evaluations may decrease, the accepted-block count and block
interval may change, and security exposure may change; the two scenarios therefore do NOT
generally realise the same total work. `ΔE` is a difference of two energy totals over one
fixed horizon at matched starting capacity, not a comparison across different settings,
difficulties, or horizons.

A fixed-capacity, fixed-horizon **energy** comparison is **not**, by itself, a
service-equivalent or security-equivalent comparison. Nothing in this energy accounting
asserts service or security equivalence; service and security non-inferiority are evaluated
only after the frozen experiments.

A positive `ΔE` (a saving) MUST be attributable to **reduced active power-time**
(`Σ_i P_hash,i * t_hash,i` smaller than in the control) net of the listening, wake,
transition, coordination, and verification terms — NEVER to partitioning, which A1 holds
fixed. At Stage 1, `ΔE` is **defined but not assigned any value**; no saving is claimed as
achieved or validated.

### 4.3 Energy-reduction attribution (CR8)

The saving decomposes into named, separately-attributed effects minus their costs:

    Delta_E_total = Delta_E_range_idle + Delta_E_reserve + Delta_E_early_stop
                    − Delta_E_transition_and_wake − Delta_E_coordination_and_verification

- `Delta_E_range_idle`: saving from miners exhausting their assigned ranges and entering
  `LOW_POWER_LISTEN`.
- `Delta_E_reserve`: saving from holding reserve miners outside active hashing (at
  `P_reserve`).
- `Delta_E_early_stop`: a propagation/termination optimisation (stopping once a valid
  solution arrives); **not unique to nonce-domain partitioning**.
- `Delta_E_transition_and_wake`, `Delta_E_coordination_and_verification`: **costs**.

Total saving must be net of wake, transition, coordination, and verification energy. These
effects are **not** attributed generically to nonce partitioning.

---

## 5. Necessary conditions for a positive saving

A positive `ΔE` requires **all** of the following. These are necessary conditions on the
model, not a claim that they hold.

1. **Positive low-power duration.** At least one miner spends strictly positive time in a
   reduced-power state: `t_listen,i > 0` for some `i` (or a reserve is held out,
   `t_offline,i > 0`, instead of hashing). Otherwise active power-time is unchanged.
2. **Listening power below hashing power.** For miners that go idle, `P_listen,i < P_hash,i`
   (and reserve/offline draw `< P_hash`). The reduced-power draw must be genuinely lower than
   the hashing draw it replaces.
3. **Overhead below gross saving.** The overhead incurred to realise and reverse the idle
   period is smaller than the gross active-power-time reduction:

        Σ_i (P_wake,i * t_wake,i + E_transition,i + E_coordination,i + E_verification,i)
            < gross reduction in Σ_i P_hash,i * t_hash,i.

   If overhead meets or exceeds the gross reduction, `ΔE ≤ 0`.
4. **No hidden deletion of failed or zero-block runs.** Failed runs, zero-block runs, and
   uncovered range tails remain fully in the accounting (I5–I7). A "saving" produced by
   omitting unfavourable runs, truncating durations, or dropping coordination/transition
   costs is not a saving and is prohibited.

---

## 6. Degenerate cases (zero or negative saving)

The following cases are specified to fix the boundary of the model. In each, no positive
saving arises.

| Case | Condition | Result |
|---|---|---|
| **Idle draw equals hashing draw** | `P_listen = P_hash` for the idling miners | Gross saving is zero ⇒ `ΔE ≤ 0` (overhead only) |
| **Zero idle duration** | `t_listen = 0` (no miner idles; reserves never held out) | No active-power-time reduction ⇒ `ΔE = 0` |
| **No idle opportunity** | Homogeneous rates with equal ranges sized so every miner hashes the full horizon | No miner reaches `LOW_POWER_LISTEN`/`RESERVE` early ⇒ possibly `ΔE = 0` |
| **Overhead-dominated** | `Σ (P_wake·t_wake + E_transition + E_coordination + E_verification) ≥` gross reduction | Wake + transition + coordination (+ verification) costs eliminate the gross saving ⇒ `ΔE ≤ 0` |

In the "no idle opportunity" case, note that partitioning has been applied but no saving
results — consistent with the accepted baseline that partitioning alone changes nothing.
Only reduced active power-time can move `ΔE` above zero, and only when the necessary
conditions of Section 5 also hold.

---

## 7. Scope, invariant references, and non-claims

- The energy model is **modeled**, not measured. No real-hardware energy measurement is
  claimed (see `STAGE_01_PROTOCOL_SCOPE.md`, Section C).
- **No final numeric parameter values are assigned at Stage 1.** The frozen reference
  setting and the A1 value are accounting anchors, not tuned parameters; the per-term powers
  and durations of (E-1) are left symbolic.
- Invariant references: **I5** (durations ≥ 0, reconcile to horizon — Section 3); **I6**
  (per-miner state energy sums to per-miner energy — Section 2); **I7** (per-miner energies
  sum to network energy — Section 4.1). Failed/zero-block runs are retained under I5–I7
  (Section 5, item 4).

All symbols and terms are defined in `STAGE_01_TERMINOLOGY.md`. This document specifies the
accounting model only and makes no implementation, validation, security, fairness, or
incentive claim.
