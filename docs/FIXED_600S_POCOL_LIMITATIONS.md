# Fixed 600-Second Round Experiment — Limitations

**Branch:** `claude/pocol-fixed-600s-distributed-nonce`
Read before quoting any number from `results/fixed_600s_pocol/`.

## Mandatory limitations (§20)

1. **The exact 600-second schedule is a controlled slot-based experiment.**
2. **Bitcoin targets an average block interval**; it does not commit blocks at
   exact slots. Nothing here models Bitcoin's difficulty-driven timing.
3. **Buffering a discovered block until the round boundary is a protocol design
   choice** of this experiment, with its own latency cost (a block found at 10 s
   waits 590 s before commit).
4. **Zero idle energy (q = 0) is an idealized upper bound.**
5. **Real devices consume nonzero idle or sleep power**; the sensitivity sweep
   (q ∈ {0…1}, sleep ∈ {0, 0.01, 0.05}) exists precisely because the saving is
   `(1−q)(1−1/N)` — at q=1 it is zero.
6. **The duplicate PoW baseline assumes exact repeated complete-header
   evaluations** — an intentionally constructed worst case.
7. **Same nonce does not imply the same hash input**; headers differ whenever any
   other field differs.
8. **Independent Bitcoin miners commonly use different candidate headers**
   (extranonce, Merkle root, timestamp, transaction set), so the real network
   does not perform the duplicate work of Mode A.
9. **A saving versus duplicate search cannot be generalized to Bitcoin.**
10. **PoCol must be compared directly with independent equal-budget candidate
    work (Mode C/IND)** — and in this experiment that comparison shows no PoCol
    advantage (deterministically identical; stochastically indistinguishable,
    equivalence at the strict pre-registered 1 % margin not established at 100
    seeds).
11. **Security implications of idling miners must be analyzed separately.** In
    the fixed-slot design the network hashes only a tiny fraction of the time
    (≈0.1–0.5 % ACTIVE at N≥100, q=0). What that does to attack cost, censorship
    resistance, and incentive compatibility is entirely out of scope here.
12. **No conclusion about equivalent security may be drawn from throughput
    alone.** Equal blocks/interval/throughput say nothing about adversarial
    robustness.

## Additional honest caveats found in the data

- **Stochastic DUP-vs-PoCol violates the equal-blocks validity rule** (DUP
  commits ~14.6–14.9 of 17; PoCol 17.00) because DUP cannot re-template within a
  slot. Quote the deterministic DUP comparison, or the stochastic IND comparison
  — not the stochastic DUP energy gap on its own.
- **Idle/sleep transition costs, wake latency, and range-coordination overhead
  are not modeled** and would erode the idealized saving.
- The deterministic IND success placement (fraction of the owner's stream) is a
  documented modeling choice; different choices change IND's discovery time but
  not the energy conclusions above (attempt budgets are controlled).
