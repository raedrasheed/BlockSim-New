# Fixed 600-Second Round Experiment — Methodology

**Branch:** `claude/pocol-fixed-600s-distributed-nonce`
**Package:** `experiments/fixed_600s_pocol/` · **Data:** `results/fixed_600s_pocol/`
**Protected (byte-identical):** `results/corrected/`, `results/nonce_partition_worst_case/`,
`results/continuous_distributed_effort/`, `results/mainsim_idle_after_range/`.

---

## 1. Scientific definition (controlled fixed-slot experiment)

`ROUND_DURATION_SECONDS = 600`. Each round has `round_start_time`,
`search_discovery_time`, `round_end_time = round_start_time + 600`,
`block_commit_time = round_end_time`, one immutable block template (per search
phase), one finite nonce domain `[0, M)`, one `TemplateID`, one `RoundID`, and —
in the primary deterministic experiment — **exactly one accepted block**.

**DISCOVERY TIME ≠ BLOCK COMMIT TIME.** A nonce discovered at second 50 is
*buffered*; the block is committed only at the 600-second boundary. This
guarantees: one accepted block per 600 s, identical block production rate,
identical accepted-block interval, identical accepted-block count, and identical
throughput (equal per-block payloads) for every compared protocol.

> **Explicit caveat:** Bitcoin targets an *average* interval via difficulty; it
> does not commit blocks at exact fixed slots. The exact 600-second schedule here
> is a controlled simulation design choice, not a literal model of Bitcoin
> timing. Buffering a found block until the boundary is likewise a protocol
> design choice of this experiment.

## 2. Round state machine

`ROUND_INITIALIZING → ROUND_SEARCHING → SOLUTION_FOUND → ROUND_WAITING →
ROUND_COMMITTING → ROUND_CLOSED`

Round start: generate one immutable template + `TemplateID` + `RoundID`; define
`[0, M)`; determine/sample the valid nonce(s); assign work per protocol; set all
miners with non-empty assignments ACTIVE; begin evaluation. On solution: record
`winner_id`, `winning_nonce`, `discovery_time`, per-miner attempts; stop every
remaining ACTIVE miner immediately; cancel pending search events; **no hashes and
no ACTIVE energy after `discovery_time`**; buffer the block; wait to
`round_end_time`; commit exactly one block; the next round starts exactly at the
boundary.

## 3. Work assignment per protocol

- **`common_template_duplicate_pow` (Mode A)** — *common-template
  duplicate-search PoW baseline* (NOT normal Bitcoin mining): every miner gets
  the same template and the complete domain, starts at the same nonce, scans in
  the same order → repeats identical complete candidate-header evaluations; all
  stop at the first discovery; IDLE until the boundary.
- **`pocol_disjoint_nonce`** — `partition_nonce_domain` splits `[0, M)` into
  mutually disjoint, collectively exhaustive half-open subranges (sizes differ by
  ≤ 1, deterministic remainders, `M < N` supported — empty-range miners stay
  IDLE). Each miner evaluates ONLY its subrange and **never** continues into
  another miner's range.
- **`independent_header_pow` (Mode C)** — each miner searches a distinct
  candidate header (its own stream) with a **controlled aggregate budget equal to
  PoCol's** (`M` total, `M/N` per miner): no duplicate complete-header work. The
  realistic control. A saving versus Mode A must never be quoted as PoCol
  outperforming Mode C.

## 4. Individual miner stopping

A PoCol miner becomes IDLE the moment it (a) exhausts its own subrange with no
solution, or (b) the global search terminates. Exhausted miners idle
*immediately* — they do not wait for the others (e.g. miner 0 idles at 40 s,
miner 1 at 45 s, the winner finds at 70 s and everyone else stops then; nobody
hashes in [70, 600); the block commits at 600).

## 5. Template exhaustion (no fabricated success)

A finite domain may contain no valid nonce. If ALL subranges exhaust before the
boundary: record a template exhaustion, create a NEW immutable template (new
`TemplateID`), repartition, reactivate miners, and continue **within the same
round** until success or the boundary. The primary deterministic experiment
guarantees exactly one valid nonce per template (one block per round); the
stochastic experiment allows zero/one/many successes and **reports empty rounds
honestly** — success is never forced.

## 6. Discovery-time semantics (corrected local-position rule)

For PoCol parallel search, each miner's `local_success_i` is the first success
*position inside its own subrange*; the network discovery time is the **minimum
local discovery time**, and the numerically smallest valid nonce is NOT
necessarily the wall-clock-earliest (a later nonce early in its owner's range
wins). Difficulty never delays an already-found block; the fixed-round scheduler
alone decides commit times.

## 7. Hardware and power

- **H1 fixed aggregate:** 141 TH/s network, 21.5 J/TH → 3031.5 W aggregate;
  per-miner `rate = agg/N`, `power = 3031.5/N`.
- **H2 fixed per-miner:** identical fixed rate & power per miner; aggregate
  scales with N. H1 and H2 are never mixed unlabeled.
- **Power states:** ACTIVE / IDLE / SLEEP. Main idealized experiment:
  `idle_ratio q = 0` (an IDLE miner consumes nothing) — labelled an **idealized
  algorithmic upper bound**, NOT a claim about real hardware. Sensitivity:
  `q ∈ {0, 0.05, 0.10, 0.20, 0.50, 1.0}`, sleep `∈ {0, 0.01, 0.05}`.
- **Domain calibration:** default `M = r_miner × 600` (rounded to a multiple of
  N), so one miner's full-domain scan takes exactly one round; Mode A's
  worst-case discovery then lands at the boundary.

## 8. Energy accounting

Per miner: state, `last_state_change_time`, per-state times, per-state powers,
`cumulative_hashes`, `cumulative_energy_j/_kwh`, evaluated/assigned candidates,
exhaustion & solution flags. On every state change:
`energy_j += P(prev_state)·elapsed`; hashes accrue only while ACTIVE; every miner
is finalized exactly to `sim_seconds`, so
`E_i = P_a·t_a + P_i·t_i + P_s·t_s` and `E_network = Σ E_i`. **Never**: divide by
N, apply 1/N or redundancy multipliers, double-charge an interval, or charge per
block event. Savings emerge only from shorter ACTIVE time / lower-power states.

## 9. Experiment matrix

Deterministic: N ∈ {1,2,5,10,20,50,100,200,300,400,500} × 3 protocols ×
{H1,H2} × 5 placements × 6 idle ratios (+ sleep sub-sweep), analytical in-process.
Stochastic: ≥100 paired seeds × 3 protocols × N ∈ {100…500}, `p=(target+1)/2²⁵⁶`
-style Bernoulli, **fresh subprocess per run**.

## 10. Validity rule

An energy saving is valid ONLY if accepted-block count, accepted-block interval
(600 s), and throughput are all EQUAL and energy is lower purely because miners
spent less wall-clock time ACTIVE. The experiment must never buy energy savings
with fewer blocks or lower throughput.
