# STAGE 02 — Energy Accounting and Physical-Unit Correction

Replaces the thesis-path energy accounting with an explicit **wall-clock,
state-based** model. Scheduling, block acceptance, stale-block logic, round
transitions, winner selection, difficulty, and transaction processing are
**unchanged** (verified: PoCol stale rates are identical in magnitude to
Stage 1). The thesis DOCX/PDF are untouched.

Authoritative model:

```
E_total = Σ_i ( P_i_active · t_i_active + P_i_idle · t_i_idle + E_i_coordination )
```

Energy is derived from actual state duration, never divided or multiplied by the
number of miners, and never scaled by a redundancy factor.

---

## 1. Old vs corrected — PoW hash-rate normalization

**Old (`Models/Node.py`, Stage 1):**
```python
# _effective_hashrate_hps
return net * (hp / 100.0)          # hp = 1 per miner  ->  H_i = net * 1%
```
Total network hash rate = `(N/100) · net` — it scaled with miner count. Only
correct when N = 100.

**Corrected (`Models/Node.py:hash_rate_hps`, Stage 2):**
```python
total_hp = Σ_n hashPower_n
return net * (hp / total_hp)        # H_i = net · (hashPower_i / Σ hashPower)
```
Now `Σ_i H_i = net` for **every** miner count (identity partition for equal
weights: `H_i = net / N`).

Dimensional check: `[H/s] · [dimensionless share] = [H/s]`. ✓

---

## 2. Old vs corrected — PoCol energy mechanism

**Old (`Models/PoCol/Consensus.py:apply_energy_for_created_block`, Stage 1):**
```python
block_time = active_winner_time
N = len(miners)
time_share = block_time / N         # <-- unphysical division by miner count
# each miner charged: P_i · (block_time / N)
```
Total per block ≈ `P_network · block_time / N`. Loser active time uncounted; no
idle state. Produced the artifactual ~98–99% "saving" (grows with N).

**Corrected (Stage 2):** the `÷N` method is a **no-op**. PoCol now uses the same
wall-clock ACTIVE accounting as PoW via `Node.start_mining` /
`Node.stop_mining_and_account`, hooked into `Models/PoCol/BlockCommit.py`:

- `generate_next_block` → `node.start_mining(...)` (open ACTIVE interval);
- `generate_block` (accepted) → `miner.stop_mining_and_account(eventTime, ...)`;
- `receive_block` → `node.stop_mining_and_account(currentTime, ...)`.

Per miner: `E_i = P_i_active · t_i_active (+ idle + coordination)`, where
`t_i_active` is the summed wall-clock duration of that miner's ACTIVE intervals.

Dimensional check: `[W] · [s] = [J]`; `[J] / [3.6e6 J/kWh] = [kWh]`. ✓

---

## 3. States and accounting primitives

New authoritative module: **`Models/Energy/wallclock_energy.py`**
(`MinerEnergyState`, `WallClockEnergyAccountant`, unit helpers).

- **ACTIVE** — mining; consumes `P_active = H · (J/TH)/1e12`.
- **IDLE** — connected, not mining; consumes `P_idle` (default 0 W = explicit
  theoretical lower bound; configurable via `IdlePowerW` / `IdlePowerRatio`).
- **OFFLINE** — zero accounted mining energy.
- **COORDINATION** — separate energy field; **never invented** (default 0,
  labelled an idealized lower bound; excluded otherwise).

Invariants enforced by construction: at most one open interval (no active/idle
overlap); a transition closes the preceding interval before opening the next;
time is non-decreasing; flush is idempotent and never accounts beyond the cutoff.

---

## 4. End-of-simulation flush (approved Stage 2 addition)

`Node.flush_energy_at(t_sim)` / `Node.finalize_energy(t_sim)` (called once in
`Main.py`, thesis path only) close any still-open ACTIVE interval up to — never
beyond — `t_sim`. Idempotent: the interval is closed on first call, so repeated
calls add nothing. This corrects the Stage-1 undercount (finding Mod-3) where a
miner's final active interval to the cutoff was never accounted.

---

## 5. Numerical invariants (all passing)

| Invariant | Expected | Observed | Tolerance | Result |
|---|---|---|---|---|
| Fixed network power | 3031.5 W | 3031.5 W | abs 1e-6 W | ✅ |
| Continuous 10 000 s energy | 8.420833333… kWh | 8.420833333… kWh | rel 1e-9 | ✅ |
| Energy vs miner count (module, N=100–500) | equal ≈ 8.4208 | all 8.420833333 | rel 1e-9 | ✅ |
| Σ per-miner H_i (N=100–500) | 1.41e14 H/s | 1.41e14 H/s | rel 1e-12 | ✅ |
| Σ per-miner energy = network energy | equal | equal | rel 1e-12 | ✅ |
| Simulator PoW energy (N=100–500) | ≈ 8.4208, N-independent | 8.420833333 (all N) | rel 1e-6 (sim) | ✅ |
| Simulator PoCol energy (N=100,200) | ≈ 8.4208 (= PoW) | 8.420833333 | rel 1e-6 (sim) | ✅ |

**Declared tolerances:** module arithmetic rel 1e-9–1e-12 (essentially exact);
full event-loop simulator runs rel 1e-6 here, with a design allowance up to ~1 %
for control-flow gaps (e.g. a Bitcoin recipient that does not immediately
re-open mining in one branch) that are out of Stage-2 scope.

---

## 6. Test results

`python -m pytest tests/` → **37 passed** (0.65 s):
- 20 required Stage-2 tests (`tests/thesis_revision_v43/test_wallclock_energy.py`);
- 6 Node/simulator integration tests
  (`tests/thesis_revision_v43/test_simulator_energy_invariants.py`);
- 11 pre-existing journal-manuscript tests (`tests/test_energy_models.py`) —
  **unchanged and still passing** (required test #18).

All 20 named tests from the Stage-2 brief are present and pass, including
`test_no_block_time_divided_by_miner_count` (asserts the `÷N` source is gone and
the hook is a no-op) and `test_hash_based_and_power_based_crosscheck`.

---

## 7. Before/after diagnostic

See `STAGE_02_BEFORE_AFTER_ENERGY.csv` and
`results/thesis_revision_v43/stage_02/` (raw read-only workbooks + manifests).

Headline: under the corrected model, total energy at a **fixed 141 TH/s** for
10 000 s is **≈ 8.4208 kWh for every miner count and for both PoW and PoCol**
under continuous operation — confirming the accounting principle that, with
matched aggregate hash rate, active power, and duration, continuous PoW and
PoCol consume the same energy. The Stage-1 ~98–99% gap is shown to be entirely
an accounting artifact (PoW inflated `×N/100`; PoCol deflated `×1/N`).

Reason-for-difference summary:
- **PoW** old values were **inflated** by `×N/100` (the `/100` normalization).
- **PoCol** old values were **deflated** by `×1/N` (the `block_time/N` division).
- Both are now correct wall-clock energy; the PoW figure additionally includes
  previously **undercounted** end-of-sim active time (flush).

Stale rates are **unchanged** (PoCol N=100: 62.7 %, N=200: 72.9 %), confirming
no scheduler/stale modification.

---

## 8. Limitations (Stage 2)

- Only the **continuous** (C1-style) policy is exercised end-to-end; the PoCol
  post-range **idle policy** (C2) and its idle-power sensitivity are Stage 4/5.
- Idle and coordination accounting are implemented and unit-tested but default
  to zero in the current continuous runs (no idle transitions occur yet).
- Full-simulator PoCol runs remain slow for N ≥ 300 (scheduler cost, Stage 3);
  the diagnostic covers PoCol at N = 100, 200 (and 300 where it completes).
- Simulator-level energy can deviate by a fraction of a percent from the exact
  invariant due to pre-existing control-flow gaps not in Stage-2 scope.

---

## 9. Issues explicitly deferred to Stage 3+

- Scheduler generation/round IDs and obsolete-event cancellation (the stale
  explosion) — **Stage 3**.
- Difficulty/target semantics and matched block intervals — **Stage 3**.
- B0–B3 / C1–C2 scenario implementation and the idle-policy matrix — **Stage 4**.
- 30-seed experiments and sensitivity (incl. idle-power ratios) — **Stage 5**.
- Bitcoin recipient re-open-mining control-flow gap (sub-percent energy) — noted;
  not fixed in Stage 2 to avoid touching non-energy control flow.
