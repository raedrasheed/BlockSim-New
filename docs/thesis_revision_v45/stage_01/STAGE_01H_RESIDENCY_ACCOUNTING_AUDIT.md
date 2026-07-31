# Stage 1H — Residency Accounting Audit (H7 / I19)

A structural audit of Stage-1H correction **H7** in the **PoCol** protocol pseudocode
(`STAGE_01_PROTOCOL_PSEUDOCODE.md`): state-residency time `t_<state>` — including
`t_ACTIVE_HASHING = t_hash` — has a **single owner**, the `residency_ledger` owned solely by
`ApplyMinerStateTransition` (§0.9), and is **never double-counted**. It confirms that a
`HashWorkEvent` (§5) records hash-work metadata only and adds ZERO duration, closing the new
invariant **I19** (`STAGE_01_INVARIANT_CATALOGUE.md`). This document is documentation only; it
audits wording and control structure and claims **no** security, fairness, or incentive property.

---

## 1. The corrected-away problem (double-count under event-scheduled hashing, G9)

Since G9 (§0.7b), hashing is a chain of discrete `HashWorkEvent`s, not a blocking `WHILE` loop.
That opens a latent double-count risk: if a `HashWorkEvent` accumulated `t_hash` per unit AND
`ApplyMinerStateTransition` also accrued `t_ACTIVE_HASHING` at the state boundary, the **same**
`ACTIVE_HASHING` occupancy would be charged **twice** — once per hash unit and once at the
boundary — inflating `t_hash` and hence `E_hash = P_hash · t_hash`. H7/I19 removes the ambiguity
by fixing a single writer for every `t_<state>`.

## 2. Mechanism (single owner)

- **`residency_ledger`** (§0.8, `RoundContext registries`) — *"the SOLE owner of every per-miner
  state-residency duration `t_<state>`, including `t_ACTIVE_HASHING = t_hash` (H7). Only
  `ApplyMinerStateTransition` opens/closes residency intervals; no other procedure increments a
  `t_<state>`."* Single writer, keyed by `(MinerID, state, entry_time)`.
- **`ApplyMinerStateTransition`** (§0.9, F6) — the sole owner. At every boundary it: **(1)** if
  `old_state != NONE`, `CLOSE residency(MinerID, old_state) at event_time`, accruing
  `P_old · (event_time − last_boundary)`; **(2)** `OPEN residency(MinerID, new_state) at
  event_time`, beginning `P_new` accrual (I5/I6); **(3)** records one-shot boundary
  `E_transition`/`E_coordination`, *never folded into `P·t`, never double-counted*. Its NOTE
  states it is *"the SOLE owner of state-residency time `t_<state>` including `t_ACTIVE_HASHING =
  t_hash` (H7)."*
- **`HashWorkEvent`** (§5) — metadata only. Under the H7 comment it *"MUST NOT increment any
  `t_<state>` residency"*; it executes `RECORD hash_work_metadata(MinerID, AssignmentID,
  assignment_version, unit_start = last_unit_time, unit_end = now, modeled_hash_evaluations += 1,
  cursor_progress = cursor, work_event_id)` — annotated *"no duration added to the energy
  ledger"*. The elapsed time of an `ACTIVE_HASHING` occupancy is thus counted once, at the
  boundary, never per hash unit (§0.7b).

## 3. Worked accounting example (N hash units, one occupancy)

A miner enters `ACTIVE_HASHING` at `t_in` (via `WakeCompleteEvent` §0.10 →
`ApplyMinerStateTransition(WAKING, ACTIVE_HASHING, t_in)`, T5) and exits at `t_out` (e.g.
`ApplyMinerStateTransition(ACTIVE_HASHING, EXHAUSTED_PENDING, t_out)`, T7). Between them, `N`
`HashWorkEvent`s fire at `t_in < τ₁ < τ₂ < … < τ_N < t_out`.

| Step | Actor | Residency effect on `t_hash` |
|---|---|---|
| Entry boundary `t_in` | `ApplyMinerStateTransition` | `OPEN residency(ACTIVE_HASHING) at t_in` — no duration yet |
| `HashWorkEvent` #1 … #N (at `τ₁…τ_N`) | `HashWorkEvent` | `RECORD hash_work_metadata` (evaluations, cursor); **+0 duration each** |
| Exit boundary `t_out` | `ApplyMinerStateTransition` | `CLOSE residency(ACTIVE_HASHING) at t_out` — accrues `P_hash · (t_out − t_in)` **once** |

Result: `t_hash = t_out − t_in`, counted exactly once; the `N` units contribute
`Σ 0 = 0` duration; `E_hash = P_hash · (t_out − t_in)`. Were the (removed) per-unit accrual
present, the ledger would have held `(t_out − t_in) + Σ_{k} (τ_k − τ_{k−1}) ≈ 2·(t_out − t_in)`,
inflating `t_hash`/`E_hash`. Under H7 that second term does not exist.

## 4. Residency-component ownership table

Every per-state residency power `P_<state>` (mapping per `STAGE_01_ENERGY_MODEL_SPECIFICATION.md`
§1.0) is opened/closed by exactly one owner; no second writer exists.

| Miner state | Residency power | Duration term | Single owner (opens/closes) | Any other writer? |
|---|---|---|---|---|
| `REGISTERED` | `P_registered` (= `P_listen`) | `t_registered` | `ApplyMinerStateTransition` / `residency_ledger` | None |
| `RESERVE` | `P_reserve` (= `P_listen`) | `t_reserve` | `ApplyMinerStateTransition` / `residency_ledger` | None |
| `ACTIVE_HASHING` | `P_hash` | `t_hash` (= `t_ACTIVE_HASHING`) | `ApplyMinerStateTransition` / `residency_ledger` | None — `HashWorkEvent` records metadata only (+0) |
| `EXHAUSTED_PENDING` | `P_hash` (short transient) | `t_exhausted_pending` | `ApplyMinerStateTransition` / `residency_ledger` | None |
| `LOW_POWER_LISTEN` | `P_listen` | `t_listen` | `ApplyMinerStateTransition` / `residency_ledger` | None |
| `WAKING` | `P_wake` | `t_wake` | `ApplyMinerStateTransition` / `residency_ledger` | None |
| `OFFLINE` | `P_offline` | `t_offline` | `ApplyMinerStateTransition` / `residency_ledger` | None |
| `DISQUALIFIED` | `P_offline` | `t_disqualified` | `ApplyMinerStateTransition` / `residency_ledger` | None |

Boundary energies `E_transition` / `E_coordination` (and the separate event term
`E_verification`) are one-shot increments recorded at the crossing per I6 — additive on top of the
residency energies, never folded into any `P·t`, never double-counted.

## 5. Reconciliation with I5 / I6 / I7 / I17

- **I5 (non-negative durations reconcile to horizon).** The ledger's OPEN-at-entry / CLOSE-at-exit
  discipline makes the intervals of one miner **partition** its timeline: consecutive boundaries
  share an instant, so `Σ_states t_state = T = 10,000 s` with no gap, no overlap, and no residual
  `t_other` bucket. Each `t_state ≥ 0` because `event_time ≥ last_boundary`.
- **I6 (per-miner energies sum).** With each occupancy charged exactly once,
  `E_i = Σ_s (P_{i,s} · t_{i,s}) + E_transition,i + E_coordination,i + E_verification,i` holds with
  exact equality and no residual term; `t_hash` is not inflated by any per-unit term.
- **I7 (network energy).** `E_total = Σ_i E_i` inherits the per-miner exactness of I6.
- **I17 (census at every ACTIVE_HASHING boundary).** The same `ApplyMinerStateTransition` boundary
  that CLOSES/OPENS the residency interval recomputes `H_active = H_honest + H_adversarial` and
  re-checks I17. Residency accounting and census recomputation share one boundary event, so
  `t_hash` occupancy and `H_active` membership are defined by the identical entry/exit instants.

For each `(miner, state occupancy)` the sum of recorded residency contributions equals the single
boundary-to-boundary interval — the I19 formal statement.

## 6. WAKING residency path (incl. zero-latency wake, H5)

`t_wake` is likewise owned by the ledger. `StartWake` (§0.10, F5) opens `WAKING` via
`ApplyMinerStateTransition(from_state, WAKING, now)`; `WakeCompleteEvent` closes it at the
completion timestamp (its note: *"Wake residency `P_wake · wake_latency` is accrued by
`ApplyMinerStateTransition` when it closed the `WAKING` interval at this timestamp"*). A
**zero-latency** wake (H5, a permitted future experimental value) still schedules a
`WakeCompleteEvent` at the same `event_time` in `delta_cycle + 1`, so the ledger still OPENS and
CLOSES a `WAKING` interval with `t_wake = 0` and records its `E_transition` — the accounting path
always exists, even at zero duration.

## 7. A1 discipline

The single-owner rule does **not** change the A1 baseline: continuous full-participation energy
over `T = 10,000 s` is **8.420833333 kWh** (141 TH/s, 21.5 J/TH, `P_active = 3031.5 W`),
UNCHANGED. Any modeled energy reduction is attributable ONLY to reduced active power-time — fewer
or shorter `ACTIVE_HASHING` intervals — never to a change in how time is counted. Double-counting,
had it remained, would have mis-attributed inflated `t_hash`/`E_hash` to the idle policy within
PoCol; this audit shows the second charge cannot occur. H7/I19 is a structural accounting
invariant and introduces **no new consensus feature**.

## 8. Acceptance-style PASS checklist

| # | Check | Result | Ground |
|---|---|---|---|
| C1 | `t_<state>` has a single owner (`residency_ledger` via `ApplyMinerStateTransition`) | PASS | §0.8 residency_ledger; §0.9 NOTE (SOLE owner, H7) |
| C2 | `t_ACTIVE_HASHING = t_hash` opened/closed once, at the boundary | PASS | §0.9 steps (1)–(2); §0.7b (computed once at interval close) |
| C3 | `HashWorkEvent` adds ZERO duration (metadata only) | PASS | §5 H7 comment + `RECORD hash_work_metadata` ("no duration added") |
| C4 | No double count of an `ACTIVE_HASHING` occupancy | PASS | §3 worked example: N units contribute `Σ0`; boundary charges once |
| C5 | No second writer of any `t_<state>` | PASS | §4 ownership table (all "None"); §0.8 ("no other procedure increments a `t_<state>`") |
| C6 | I5 / I6 / I7 reconcile (partition, exact sums, no residual) | PASS | §5; I5/I6/I7 |
| C7 | I17 census recomputed at every `ACTIVE_HASHING` boundary | PASS | §0.9 step (6); I17 enforcement point |
| C8 | WAKING path preserved, incl. zero-latency wake (`t_wake = 0`) | PASS | §0.10 StartWake/WakeCompleteEvent; H5 |
| C9 | A1 baseline unchanged; reduction attributed only to reduced active power-time | PASS | §7; I19 scope; A1 = 8.420833333 kWh |

---

## Result

**RESIDENCY ACCOUNTING AUDIT (Stage 1H): PASS** — every per-miner state-residency duration
`t_<state>`, including `t_ACTIVE_HASHING = t_hash`, is opened and closed exactly once by the
`residency_ledger` owned solely by `ApplyMinerStateTransition` (§0.9); `HashWorkEvent` (§5) records
hash-work metadata only and adds zero duration, so an `ACTIVE_HASHING` occupancy is charged once at
the boundary and never per hash unit (I19); this reconciles with I5/I6/I7 and the I17 boundary
census, preserves the WAKING path including the zero-latency wake, and leaves the A1 baseline
(8.420833333 kWh) unchanged, with any modeled energy change attributable only to reduced active
power-time.
