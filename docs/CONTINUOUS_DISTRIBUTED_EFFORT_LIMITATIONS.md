# Continuous Distributed-Effort Experiment — Limitations

**Branch:** `claude/pocol-continuous-distributed-effort`

Read this before quoting any number from
`results/continuous_distributed_effort/`.

---

## 1. Mandatory limitations

1. **Energy saving does not result from nonce partitioning alone.** Partitioning
   changes *who* evaluates *which* nonce, not power draw. With no state change the
   saving is zero.
2. **Energy saving requires miners to reduce power after completing assigned
   work.** The saving is `(1 − q)(1 − 1/N)`, driven entirely by `q = P_idle/P_active`
   (and sleep) and by shorter ACTIVE time.
3. **Under IMMEDIATE_RESTART and continuous full-power operation the saving
   disappears** — PoW and PoCol are energy-neutral (the control policy, consistent
   with Finding 1).
4. **The duplicate baseline (Mode A) is an intentionally constructed worst case**
   — the maximum-duplication scenario, not a model of real miner behaviour.
5. **The result applies only to exact duplicate complete-header evaluations.**
6. **Same nonce ≠ same hash input.** A header hash depends on the whole header.
7. **Real miners may use different coinbase extranonces, Merkle roots, timestamps,
   and transaction sets** — i.e. different complete headers — so they do not
   perform the exact-duplicate work Mode A assumes.
8. **PoCol must not be claimed to reduce Bitcoin energy by `1 − 1/N`** (or by
   `(1 − q)(1 − 1/N)`). Those are bounds against a synthetic duplicate baseline.
9. **Idle and sleep power are physical assumptions** requiring sensitivity
   analysis; this experiment sweeps `q ∈ {0, 0.05, 0.10, 0.20, 0.50, 1.0}` and
   sleep `∈ {0, 0.01, 0.05}` precisely because the result is highly sensitive to
   them.
10. **Reducing candidate work may affect success probability or security** unless
    the *unique* candidate budget is kept equivalent. Mode C1 holds the total
    unique budget at `M` to make the comparison fair.
11. **Mode C1 is required** to determine whether PoCol provides any advantage
    beyond simply avoiding duplicate work. If `B ≈ C1`, PoCol's only benefit is
    de-duplication — obtainable just as well by giving miners distinct headers.

---

## 2. What the experiment can and cannot establish

**Can establish (supported):**
- The idealized upper bound on energy saving from disjoint allocation **plus**
  power-down, in the common-template duplicate worst case, is
  `(1 − q)(1 − 1/N)`, verified by state-integrated wall-clock energy.
- That this bound collapses to 0 when `q = 1` or under IMMEDIATE_RESTART.
- Whether disjoint allocation (B) beats independent equal-budget headers (C1),
  via a direct paired test with a pre-registered equivalence margin.

**Cannot establish (unsupported):**
- Any energy saving for the real Bitcoin network (it does not do exact-duplicate
  complete-header work).
- That PoCol is superior to independent-header mining if `B ≈ C1`.
- Any combined Finding-1 + Finding-3 headline number.

---

## 3. Unresolved scientific limitations

- **Security/at-stake modelling is out of scope.** Whether reduced per-miner work
  under equal *unique* budget preserves the security properties of Nakamoto
  consensus is not evaluated here.
- **Idle/sleep transition costs** (ramp time, wake latency, DVFS overhead) are not
  modelled; real hardware cannot switch power states for free.
- **Coordination overhead** of assigning disjoint ranges (communication, template
  distribution) is not charged.
- **The realistic baseline is C1, not A.** All headline savings are stated against
  A explicitly and must be read together with the B-vs-C1 result.
