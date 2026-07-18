# PoCol Energy & Event-Semantics Audit (Phase 0)

Branch: `claude/fix-energy-round-semantics`
Scope: read-only audit of the PoW (Bitcoin, model 1) and PoCol (model 3)
execution paths. No behaviour is changed by this document. It records the exact
files, methods, and mechanisms that must be corrected in Phases B1–B5.

Configuration under audit (`InputsConfig.py`): `NetworkHashRate_Hps = 141e12`,
`MinerEfficiency_J_per_TH = 21.5`, `simTime = 10000`, `Binterval = 600`,
`HashPowerIsShare = True`, homogeneous miners `hashPower = 1`.

Physical reference for continuous mining (independent of miner count N):
`P_network = 141e12 · 21.5/1e12 = 3031.5 W`;
`E_max = 3031.5 · 10000 / 3.6e6 = 8.420833 kWh`.

---

## 1. Event loop and queue

- `Event.py` — `Queue` is a min-heap keyed by `(time, _seq)`.
  - **`Queue.remove_event(event)` ignores its argument and pops the heap
    minimum** (`heapq.heappop`). `Main.main` does `get_next_event()` (peek) →
    `handle_event` → `remove_event()` (pop). This works only because handlers
    add events with strictly later times (or larger `_seq`), so the min at pop
    time is the event just handled. There is **no way to cancel a specific
    queued event** — a structural blocker for correct round termination (B2).
- `Scheduler.create_block_event` / `receive_block_event` build `Event` objects
  with no round/template identity. An event carries only `(type, node, time,
  block)`; `block` has `miner, depth, id, previous, timestamp`. There is **no
  `round_id`, `template_id`, or version** to validate against at pop time (B2).
- `Models/Network.py` — `block_prop_delay = expovariate(1/Bdelay)`,
  `Bdelay = 0.42 s`. Propagation is per-recipient random; with N up to 500
  recipients per block, many recipients receive the winning block *after* their
  own losing create-event fires (root of the inflated stale count, §4).

## 2. Hash-rate and power (already partly fixed on the parent branch)

- PoW baseline `Models/Node.py::_effective_hashrate_hps` — previously returned
  `net * (hp/100.0)` (each miner hardcoded to 1% of the network → aggregate
  scaled with N, correct only at N=100). **Fixed** on the parent branch to
  `net * (hp / Σ hp)` so `Σ H_i == net` for any N.
- PoCol `Models/PoCol/Node.py::get_hashrate_hps` = `total_hps · hashPower/Σ hp`
  (already fractional) and `get_power_w = hps · J_per_hash`. Correct: `Σ P_i =
  P_network`.
- Ethereum `Models/Ethereum/Node.py::_resolve_hashrate_hps` already fractional.
- Residual risk: two code paths compute per-miner hash rate (base
  `_effective_hashrate_hps` for PoW; `get_hashrate_hps` for PoCol). B1 must add
  an invariant test asserting both yield `Σ H_i == net` and `Σ P_i == P_network`.

## 3. Energy accounting — the central defect

### 3a. PoW (Bitcoin) — wall-clock integration, but not finalized
- `Models/Bitcoin/BlockCommit.generate_block`: on a valid win calls
  `miner.stop_mining_and_account(eventTime)`.
- `Models/Bitcoin/BlockCommit.receive_block`: calls
  `node.stop_mining_and_account(currentTime)` then `start_mining` again.
- `Models/Node.py::start_mining / stop_mining_and_account` integrate energy over
  `dt = stop_time − mining_start_time` using `E = hashes·J/TH`. This **is** a
  wall-clock integration per miner and is essentially correct.
- **Defect (audit item 8):** miners still mining at `simTime` are never
  stopped, so the final interval `[last start, simTime]` is omitted. This is why
  measured PoW energy (~7.6–8.4 kWh) sits just below the `8.4208 kWh` ideal.
  B1 must add end-of-simulation finalization.

### 3b. PoCol — block-count-driven charging (double counts overlapping time)
- `Models/PoCol/Consensus.apply_energy_for_created_block` is called from **both**
  `Models/PoCol/BlockCommit.generate_block` and `receive_block`. It is keyed by
  `block_id` via `Consensus._energy_applied_block_ids`, so a *given* block is
  charged once — but it charges **all N miners `P_i · block_time` once per
  distinct created block**, including every stale/fork block.
- Consequence: total energy ≈ `Σ_{created blocks} P_network · block_time_of_round`.
  Because forked blocks cover **overlapping** wall-clock intervals, the same real
  time is charged multiple times (audit item 7). Measured PoCol energy reaches
  **35–80 kWh at N=100–400**, which **exceeds the physical bound
  `E_max = 8.4208 kWh`** — an impossibility that proves the double counting.
- Root cause: energy is a function of *block count*, not *wall-clock time*.
  The parent-branch fix (removing the extra `1/N`) corrected the magnitude of a
  single round but did **not** remove the per-block, overlapping-interval model.
- **B1 fix:** delete block-based charging; integrate energy once over wall-clock
  per miner (shared with PoW), plus end-of-sim finalization. A created-block
  event may *trigger* a state update but must never charge a full network-round.

## 4. Round termination and stale-block semantics

- `Models/PoCol/Consensus._init_round` builds one round per parent block: sizes
  the nonce space, partitions it into disjoint ranges, **samples exactly one
  solution nonce** `random.randrange(0, space)`, and derives the winner as the
  range containing it and `active_winner_time = attempts / winner_rate`.
  - **Defect (B5):** exactly one solution is guaranteed every round; zero or
    multiple successes are impossible; range exhaustion cannot occur.
- `Models/PoCol/Consensus.Protocol` schedules the winner at `active_winner_time`
  and **every losing miner at `active_winner_time + loser_lag`**
  (`loser_lag = max(Bdelay·5, 1e-3) = 2.1 s`). All N miners get a create event.
- `Models/PoCol/BlockCommit.generate_block` accepts any create event whose
  `blockPrev == miner.last_block().id`. A loser whose create event fires **before
  it has received the winner's block** (propagation delay/order vs. the 2.1 s
  lag, common at large N) still passes the tip check → it increments
  `Statistics.totalBlocks`, is charged energy, executes transactions,
  propagates, and starts another round → it becomes a **stale block**.
- `Models/PoCol/BlockCommit.receive_block` does **not** cancel a recipient's
  pending create event and does not stop its mining; there is no round object to
  mark closed.
- Consequence: measured stale rate **62–74%** at N≥200. These are largely
  **scheduler artifacts** — future events that should have been cancelled once
  the round was won — not genuine near-simultaneous competing blocks.
- **B2 fix:** explicit round context (`round_id, parent_block_id, template_id,
  status, winning_block_id`), stamp every create event with its `round_id`, mark
  the round CLOSED on the first valid block, and **lazily reject** popped events
  whose round is closed (no block count, no energy, no tx, no propagation).
  Genuine stale blocks (a competing valid block produced before the winner is
  received, in an *open* round) remain possible.

## 5. Statistics and blocks

- `Statistics.blocks_results`: `mainBlocks = len(global_chain) − 1`,
  `staleBlocks = totalBlocks − mainBlocks`, `totalEnergy_kWh = Σ node.energy_kwh`,
  `totalCO2_kg = Σ node.co2_kg`. `totalBlocks` is incremented in each model's
  `generate_block` — so every artifact fork inflates both `totalBlocks` and
  `staleBlocks`, and (in PoCol) energy.
- `Consensus.fork_resolution` (both models) picks the longest chain
  (tie-broken by most-common last miner) into `global_chain`.
- No per-run seed capture, commit SHA, or config hash is recorded (B6 gap).

## 6. Configuration divergence

- `InputsConfig.py`: PoW block (`model == 1`) sets `Tn = 3`; PoCol block
  (`model == 3`) sets `Tn = 10`. `Models/Transaction.LightTransaction.create_transactions`
  builds a pool of `Psize = Tn · Binterval`, so PoCol is fed 3.3× the workload.
  Block/network params (Binterval 600, Bdelay 0.42, Bsize 1.0, hashrate,
  efficiency, simTime) coincide, but the divergence is by duplication in two
  separate blocks with **no guard** against further drift (B3 fix: single shared
  scenario object + an equality test over all non-protocol parameters).

## 7. Summary of required corrections

| # | Defect | File · method | Phase |
|---|--------|---------------|-------|
| 1 | Energy charged per created block over overlapping wall-clock (exceeds physical bound) | `Models/PoCol/Consensus.apply_energy_for_created_block` (called from `PoCol/BlockCommit.generate_block` & `receive_block`) | B1 |
| 2 | Final `[last start, simTime]` interval omitted | `Models/Node.stop_mining_and_account` (never called at sim end) | B1 |
| 3 | No end-of-sim energy finalization | `Main.main` / model `BlockCommit` | B1 |
| 4 | Two hashrate code paths; need conservation invariants | `Models/Node._effective_hashrate_hps`, `Models/PoCol/Node.get_hashrate_hps` | B1 |
| 5 | Losing create events not cancelled once round is won → artifact stale blocks | `Models/PoCol/Consensus.Protocol`, `PoCol/BlockCommit.generate_block`/`receive_block`; `Event.remove_event` cannot cancel a specific event | B2 |
| 6 | No round/template/version identity on events | `Event.Event`, `Scheduler.*` | B2 |
| 7 | `Tn` (and any non-protocol param) can diverge between protocols | `InputsConfig.py` model blocks | B3 |
| 8 | No realized-block-interval calibration; six-conf compared at unequal rates | `InputsConfig`, harness | B4 |
| 9 | Exactly one guaranteed solution nonce per round; no exhaustion | `Models/PoCol/Consensus._init_round` | B5 |
| 10 | No multi-seed runs, no seed/commit/config capture, no CIs | harness, `Statistics` | B6 |

Physical invariants to enforce in tests (B1): `Σ H_i == net`; `Σ P_i ==
P_network`; `active_time_i ≤ simTime`; `E_i ≤ P_i · simTime`; `Σ E_kWh ≤
P_network · simTime / 3.6e6`; continuous mining ⇒ `Σ E ≈ 8.420833 kWh` for all N.
