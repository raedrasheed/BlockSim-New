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

For each miner `i`, the modeled energy over the fixed horizon is

    E_i = P_hash,i    * t_hash,i
        + P_listen,i  * t_listen,i
        + P_wake,i    * t_wake,i
        + P_offline,i * t_offline,i
        + E_transition,i
        + E_coordination,i.                                            (E-1)

This is the normative accounting model. Every energy statement about PoCol at Stage 1 is
expressed through (E-1), through the network total (E-2), or through the saving (E-3).

### 1.1 Term-by-term definitions and units

**Convention.** Power is in **watts (W)**; time (duration) is in **seconds (s)**; a
power–time product `P × t` is in **joules (J)**. Energy is converted to **kilowatt-hours
(kWh)** by dividing joules by **3,600,000** (since `1 kWh = 3.6 × 10⁶ J`). All powers are
non-negative; all durations are non-negative (invariant **I5**). Each miner is in exactly
one state at any instant, so the duration terms partition the horizon (Section 3).

| Term | Meaning | Unit | Contributing state | Contributes to active hash rate? |
|---|---|---|---|---|
| `P_hash,i` | Power drawn while actively hashing | W | `ACTIVE_HASHING` | — |
| `t_hash,i` | Total time miner `i` spends actively hashing | s | `ACTIVE_HASHING` | Yes |
| `P_listen,i` | Power drawn while low-power listening | W | `LOW_POWER_LISTEN` | — |
| `t_listen,i` | Total time miner `i` spends low-power listening | s | `LOW_POWER_LISTEN` | No |
| `P_wake,i` | Power drawn while waking (resuming to hash) | W | `WAKING` | — |
| `t_wake,i` | Total time miner `i` spends waking | s | `WAKING` | No |
| `P_offline,i` | Power drawn while offline/reserve-idle | W | `OFFLINE` (and idle-reserve draw) | — |
| `t_offline,i` | Total time miner `i` spends offline/reserve-idle | s | `OFFLINE` / `RESERVE` | No |
| `E_transition,i` | Fixed/aggregate transition energy for state changes not fully captured by a single `P×t` term (spin-up/down, mode switches) | J (→ kWh via /3.6×10⁶) | transitions | No |
| `E_coordination,i` | Modeled energy of coordination for miner `i` (progress commitments, assignment/lease messaging, security-floor participation, reserve activation signalling) | J (→ kWh via /3.6×10⁶) | coordination | No |

Notes on conventions:

- **Product terms** (`P_hash,i * t_hash,i`, etc.) are computed in joules and summed with the
  two lump terms `E_transition,i` and `E_coordination,i`, which are **already energies** (J),
  before any conversion to kWh. Do NOT double-convert.
- **`REGISTERED`, `EXHAUSTED_PENDING`, `WAKING` accounting.** `REGISTERED` (admitted,
  pre-assignment) and `EXHAUSTED_PENDING` (assertion pending adjudication) draw their modeled
  power through the applicable term; where a design treats their draw as a distinct level,
  it is represented via `E_transition,i` or a state-specific power at the same units.
  `WAKING` is charged through `P_wake,i * t_wake,i`. `DISQUALIFIED` miners contribute no
  active hash rate and their residual draw, if any, is accounted as offline draw.
- **`RESERVE` draw** is accounted as offline-class idle draw (`P_offline,i * t_offline,i`)
  because a held-out reserve draws no active hashing power. Its later activation cost is the
  wake and transition terms.
- **Sign conventions.** No term is negative. A "saving" is never represented as a negative
  energy term; it is the *difference of two totals* (Section 4).

---

## 2. Per-miner state–energy conservation (I6)

**Invariant I6:** for each miner `i`, the sum of the state-attributed energies equals that
miner's total energy `E_i`. That is, the six contributions on the right-hand side of (E-1)
are exhaustive and mutually exclusive by state/category, so no energy is created or lost in
attribution:

    E_i = Σ over states/categories of (state energy of miner i).       (I6)

There is no residual, unattributed energy bucket. Every joule miner `i` draws is charged to
exactly one term of (E-1).

---

## 3. Duration reconciliation to the horizon (I5)

**Invariant I5:** durations are `≥ 0` and reconcile to the fixed horizon. Because each miner
occupies exactly one state at a time over `[0, T]`, the state durations partition the
horizon for each miner `i`:

    t_hash,i + t_listen,i + t_wake,i + t_offline,i + t_other,i = T,     (I5)

with every term `≥ 0`, where `t_other,i` collects any residual admitted-state time
(`REGISTERED`, `EXHAUSTED_PENDING`, `DISQUALIFIED`) so the accounting is complete. No
duration may be negative, and the durations for a miner may not sum to more than the horizon
(no double-counted time) nor be silently truncated below it (no vanished time).

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

The control is **explicit and matched**: `E_continuous_control` is exactly the A1 value
(8.420833333 kWh) computed for the **same** frozen reference setting (same aggregate hash
rate, efficiency, horizon, and therefore same total work opportunity) under **continuous
full participation** — every miner in `ACTIVE_HASHING` for the whole horizon. `E_idle_policy`
is `E_total` from (E-2) under PoCol with the idle policy enabled for the same setting. `ΔE`
is therefore a like-for-like difference of two totals over one fixed horizon, not a
comparison across different settings, difficulties, or horizons.

A positive `ΔE` (a saving) MUST be attributable to **reduced active power-time**
(`Σ_i P_hash,i * t_hash,i` smaller than in the control) net of the listening, wake,
transition, and coordination terms — NEVER to partitioning, which A1 holds fixed. At Stage 1,
`ΔE` is **defined but not assigned any value**; no saving is claimed as achieved or validated.

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

        Σ_i (P_wake,i * t_wake,i + E_transition,i + E_coordination,i)
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
| **Overhead-dominated** | `Σ (P_wake·t_wake + E_transition + E_coordination) ≥` gross reduction | Wake + transition (+ coordination) costs eliminate the gross saving ⇒ `ΔE ≤ 0` |

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
