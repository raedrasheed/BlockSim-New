# INITIAL SCIENTIFIC AUDIT — Thesis Scientific Revision v43

Independent verification of the scientific issues, from **code + thesis data**,
not from assumption. Severity: **CRITICAL / MAJOR / MODERATE / MINOR**.
This audit is a Stage 0 planning artifact; it records *findings*, not fixes.

Physical reference invariant (from thesis Table config): a fixed network of
`141 TH/s` at `21.5 J/TH` for `10,000 s` consumes

```
P = 141e12 × 21.5e-12 = 3031.5 W
E = 3031.5 × 10000 / 3.6e6 = 8.4208 kWh   (constant; independent of miner count)
```

---

## CRITICAL

### C-1 — PoW network hash rate mis-normalized → energy scales with miner count
**Where:** `Models/Node.py:49-54` (`_effective_hashrate_hps`)
```python
if bool(getattr(p, "HashPowerIsShare", True)):
    net = float(getattr(p, "NetworkHashRate_Hps", 0.0))
    return net * (hp / 100.0)     # hp = 1 for every miner (InputsConfig)
```
Each miner is hard-coded to **1% of 141 TH/s regardless of miner count**, so the
*total* network hash rate = `(Nn/100) × 141 TH/s`. The correct denominator is
`Σ hashPower` (= `Nn`), not the literal `100`.

**Corroboration (code + committed data + thesis):**
- Committed `Bitcoin_…153749` (**1000 miners**) → **83.84 kWh** = `0.996 × (10 × 8.4208)`.
- Committed `…143644` (**50 miners**) → **3.93 kWh** ≈ `0.5 × 8.4208`.
- Thesis Table 7.1 PoW (100→500): `7.90/15.56/24.49/33.08/40.41 kWh` →
  `PoW ÷ (Nn/100) ≈ 7.9–8.3 kWh` (≈ constant, ≈ physical invariant).

The thesis narrative "PoW energy rises with miners" is an **accounting
artifact**, not physics. At 100 miners the baseline is coincidentally correct.

**Impact:** inflates the PoW baseline by `×Nn/100` (10× at 1000 miners).
Directly fabricates part of the PoCol-vs-PoW energy gap.

---

### C-2 — PoCol energy divides by miner count → the 98–99% headline is an artifact
**Where:** `Models/PoCol/Consensus.py:262-264` (`apply_energy_for_created_block`)
```python
block_time = float(Consensus.active_winner_time)
N = max(1, len(miners))
time_share = block_time / float(N)   # code comment: "divide by #miners"
```
Every miner is charged only `block_time/N` seconds of active energy per block.
Total network power is correctly `3031.5 W`, so **total PoCol energy ≈
(1/N) × physical wall-clock energy**. The **losers' full-round hashing time is
never charged**, and there is **no idle-state model** — the `÷N` simply *asserts*
that collaboration saves energy proportional to N.

**Why 98–99% and why it grows with N:** two artifacts move oppositely with N —
PoW inflated `×Nn/100` (C-1) **and** PoCol deflated `×1/N` (C-2):

| Miners | PoW (kWh) | PoCol (kWh) | reduction |
|---|---|---|---|
| 100 | 7.902 | 0.131 | 98.34% |
| 200 | 15.558 | 0.300 | 98.07% |
| 300 | 24.486 | 0.470 | 98.08% |
| 400 | 33.078 | 0.454 | 98.63% |
| 500 | 40.408 | 0.335 | 99.17% |

**Self-contradiction in the thesis:** Chapter 5 states "when PoCol and the PoW
baseline use the same aggregate hash rate, hardware efficiency, active power, and
experiment duration, continuous operation is **not** expected to provide an
inherent energy reduction" — which is correct and directly contradicts the
Chapter 7 headline produced by `÷N`.

**Impact:** the single largest defect. Under a correct wall-clock model, a real
saving can arise **only** from a modeled idle transition (post-range idling),
which is a *fraction* of the round, not `1/N`.

---

### C-3 — Chapter 7 headline values have no committed provenance
**Where:** thesis text + repository contents.
- No PoCol workbooks and no 100/200/300/400/500 sweep are committed (only
  Bitcoin 50 & 1000 and Ethereum runs exist).
- Thesis states "every scenario corresponds to just one logged run … analysed
  descriptively without significance testing."
- No seed control (see BASELINE_FREEZE §4) → values are not re-derivable.

**Impact:** every Table 7.1/7.2 cell is a single, uncommitted, non-reproducible
run → classified **UNTRACEABLE**.

---

## MAJOR

### M-1 — Scheduler has no round/generation identity → stale-block explosion
**Where:** `Scheduler.create_block_event` (`Scheduler.py:31-40`) stamps only
`miner/depth/id/previous/timestamp`; no `round_id`, `template_id`, or
`generation_id`. Superseded "loser" events (scheduled at `winner_time + lag` on
the old parent) are never cancelled; they are only filtered at fire time by
`blockPrev == miner.last_block().id` (`Models/PoCol/BlockCommit.py:40`). With
`N-1` losers per round and propagation delay, stale rate grows **35.7% → 85.7%**
with miner count (thesis Table 7.2). Largely a **simulator artifact**, currently
interpreted as an intrinsic PoCol limitation.

### M-2 — Block intervals not matched → throughput/latency comparison not like-for-like
**Where:** PoW `Models/Bitcoin/Consensus.py:13-17` draws `expovariate(fraction/600)`;
PoCol `Models/PoCol/Consensus.py:127-136` auto-sizes nonce space `S = 2·H·T`.
PoCol reports **more main blocks and higher TPS** (11.33 vs 2.87 at 300 miners)
at the same nominal 600 s target — the effective processes differ. Throughput
and 6-confirmation-time claims are not matched comparisons.

### M-3 — No B0–B3 / C1–C2 baseline separation
Only one PoCol variant (`÷N`) vs one PoW model exist. Realistic
independent-template PoW (B0), common-template uncoordinated (B1),
randomized-start (B2), coordinated-no-idle (B3), PoCol continuous (C1) and PoCol
idle (C2) do not exist in code. No ablation isolates which mechanism (if any)
saves energy.

### M-4 — Common-template agreement / exhaustion / security inheritance specified but not executed
`Models/PoCol/BlockCommit.generate_block` calls `LT.execute_transactions()` per
block — **no TemplateID, no canonical ordering, no pre-committed reward, no
finite-domain-exhaustion → new-template logic.** The abstract concedes this.
Chapter 5's "keeps the same backbone security assumptions" needs an explicit
retained-mechanism / argument / proof-status table; "six PoCol confirmations ≈
six PoW confirmations" is asserted without a matched-accumulated-work analysis.

---

## MODERATE

### Mod-1 — Sybil resistance & reward-contribution verification unimplemented
Reward distribution is "proposed"; no identity-cost, no verifiable range-
completion proof, no free-riding / false-idle defense. Must remain framed as
design/future work (thesis already concedes this in places).

### Mod-2 — No idle-power or coordination-energy term in the PoCol path
There is no idle state and no coordination-energy accounting anywhere; the `÷N`
stands in for both. Stage 2 must add explicit, configurable `P_idle` and
`E_coordination` (default 0, labelled idealized lower bound).

### Mod-3 — End-of-simulation active mining time not flushed (PoW)
`stop_mining_and_account` is only called on block-mine/receive events; a miner's
final interval up to `simTime` is never accounted, so PoW totals undercount and
vary with block count (observed in Stage 1 repeats). Interacts with C-1.

---

## MINOR
- **Min-1** Terminology: the common-template baseline is described as/near
  "classical PoW".
- **Min-2** Citation/DOI audit across 153 references (deferred to Stage 9).
- **Min-3** Chapter 5 diagram legibility (deferred to Stage 9).
- **Min-4** English/Arabic abstract numeric parity once numbers change.

---

## Fair-credit note
The candidate's prose is, in many places, already carefully hedged (idealized
abstraction, proof-of-concept, agreement layer not executable, not
deployment-ready, no significance testing). The genuine contribution — the PoCol
**design** (immutable common template + deterministic disjoint nonce allocation
+ collaborative reward), the structured literature survey, and a
sustainability-aware BlockSim extension — **survives** removal of the
artifact-driven numbers. The defect is narrow and fixable: the **quantitative
energy claims** rest on two accounting bugs (C-1, C-2) atop a single-run,
uncommitted, unseeded evidence base (C-3) with a scheduler-induced stale
artifact (M-1).

## Severity roll-up
| Severity | IDs |
|---|---|
| CRITICAL | C-1, C-2, C-3 |
| MAJOR | M-1, M-2, M-3, M-4 |
| MODERATE | Mod-1, Mod-2, Mod-3 |
| MINOR | Min-1 … Min-4 |
