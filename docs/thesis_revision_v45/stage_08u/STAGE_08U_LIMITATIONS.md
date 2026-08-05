# Stage 8U — Limitations

These limitations bound every Stage-8U statement.  They are stated before any use of the
results in the thesis, and they are not softened by the fact that two of four gates
passed.

## 1. What this comparison is

A **controlled simulator comparison** between the accepted PoCol Stage-2 engine and a
**matched same-template PoW control** built from the same accepted primitives.  Both
sides commit real SHA-256 evaluations against the same immutable per-round template
stream, the same fixed target `floor((2^256−1)/1000)`, the same 1600-nonce domain, the
same 300 s horizon, the same master seeds, the same actual per-miner rates and the same
power values.

It is **not** a measurement of any deployed network.  The controls are never Bitcoin,
never "the Bitcoin network", never "real-world PoW".  Nothing here supports a claim about
production PoW systems, their security, their economics or their incentives.

## 2. W00 and W01 answer different questions and are never merged

* **W00 (population-matched)**: all 20 nodes mine.  It matches the physical population.
* **W01 (active-capacity-matched)**: exactly the 16 initially active primaries mine, with
  4 non-mining standby nodes at `P_reserve`.  This is an **artificial construction** with
  no deployed counterpart — it exists so the comparison controls for the initial active
  mining capacity rather than the node count.

W01 carries the preregistered service and energy gates; W00 is sensitivity only.  Their
results are reported separately everywhere (FIG02, FIG13, FIG14, both comparison tables)
and are never averaged or presented as one number.

## 3. The scale is deliberately reduced, and it binds on the conclusions

20 miners, a 1600-nonce domain, difficulty 1000 and a 300 s horizon.  Two consequences
are load-bearing:

* **The static 3200 H floor is structurally unattainable.** The four-reserve pool
  contributes at most 1000 H. This was established in Stage 8R and is unchanged here;
  the static-floor family is reported for continuity, not as an achievable target.
* **Reserve wakes cannot pay for themselves at this scale.** A full 100-nonce primary
  range takes at most 1.0 s to search while the wake latency alone is 1.0 s plus 0.25 s
  for one batch. The U4 utility check consequently rejected every wake candidate (mean
  3 619.75 short-window rejections per run) and seated zero. The zero-churn result of
  H-U1 is therefore partly a property of this configuration, not solely of the policy.
  At a larger domain or a longer horizon the mechanism could seat wakes and the churn
  result would need re-measuring.

## 4. The service gate failure is a property of partitioned search

H-U2 fails at a block ratio of 0.6770 and a median-duration ratio of 5.2190. The
mechanism is disjoint-range assignment: a PoCol round cannot close until the specific
miner owning the winning nonce reaches it, whereas any uncoordinated PoW node can find
any solution. The matched PoW control buys that latency with roughly nine times the
physical work (1.16 M evaluations, 942 K of them duplicates, versus 140 K with zero
duplicates). Reporting only the block ratio would misrepresent the trade; the
work-efficiency and energy-per-block columns are part of the finding, not a consolation.

This also means the H-U2 gate as preregistered measures something the single-handoff
policy was never able to influence. The gate was frozen before execution and is honoured
as written; the observation that it targets the search discipline rather than the
controller is stated here as a limitation of the experimental design, not as grounds to
revise the gate.

## 5. The power-null counterfactual is not a PoW control

`relative_reduction` (P02: 0.5486) compares a PoCol run against **itself** with the
low-power states priced at the hashing power. It is a within-run accounting
counterfactual. It is never an executable PoW baseline and is never presented as one; the
executable comparison is W00/W01, and it is the one the gates use.

## 6. Reserve/wake savings are reported separately from range-idle savings

FIG09 and the energy decomposition keep primary hashing, range idle, reserve standby,
wake transient, activated-reserve hashing and offline/other apart. In P02 the reserve and
wake components are zero by construction (no wake was seated), so the whole low-power
difference is range idle. Combining the two into one headline saving would overstate what
the controller contributes.

## 7. Cross-stage comparisons are descriptive only

FIG17 places the 8M, 8R, 8S and 8U primary arms side by side. Each stage used its **own
fresh seed registry** (Stage-6 registry, then 8R, 8S and 8U seeds, all executably
disjoint — 69 previous seeds checked). No cross-stage inferential statistic or p-value is
computed, and none may be added later.

## 8. Statistical scope

n = 12 paired seeds per scenario. The exact paired sign test over 4096 assignments has a
floor of 2/4096 = 0.000488 for a two-sided p, and all four Holm contrasts sit exactly
there — the design can establish that the differences are consistent in sign across every
seed, not that they are of any particular magnitude beyond the reported CIs. The unit of
analysis is the run; rounds, miners, events, hashes and chunks are not independent
observations and were never treated as such.

## 9. Modelling assumptions declared in the matched PoW control

* **Exhaustion closure**: with no solution in the domain, the round closes when the first
  miner completes full-domain coverage — its own coverage proves the domain empty. This
  is the PoW-favourable minimal rule; a stricter rule (waiting for consensus on
  exhaustion) would lengthen PoW rounds and improve PoCol's relative service.
* **Oracle scans** determine round timing only and are never counted as physical work —
  the same convention the accepted engine uses for its planning scan.
* **No propagation, verification or network delay** on either side. Both are
  computation-only models; adding propagation would affect PoW and PoCol differently and
  is outside this stage.
* **Energy is wall-clock residency** on both sides, with mining nodes never idling in the
  PoW control.

## 10. What is not claimed

No claim of broad PoW superiority or inferiority. No security claim: the operational
0.80·H0 target is an engineering target, not a security threshold, and `H_pipeline`
remains a scheduling forecast that never substitutes for physical `H_effective`. No
incentive claim. No claim that the single-handoff policy is licensed — it is not, and
H-U2 and H-U5 name exactly why.

## 11. Future work (not to be executed in this cycle)

Recorded for the thesis, explicitly out of scope now and not to be turned into another
refinement stage: evaluating the policy at a domain and horizon where reserve wakes can
be productive; a service metric that credits work-efficiency rather than raw block count;
and a partitioned-search variant that shortens the tail latency imposed by single-owner
slices. The directive ends refinement here; these are observations, not a plan.
