# Stage 5A — Known Limitations

Stage 5A fixes executable defects. It adds **no** new claim. Everything in
`STAGE_05_KNOWN_LIMITATIONS.md` still applies in full; this document adds what is specific to
the corrections.

---

## 1. No new claims

Stage 5A establishes **no** incentive compatibility, fairness, Sybil resistance, selfish-mining
resistance, coalition resistance, common-prefix security, chain-quality security or
PoW-equivalent security. Making splitting and identities *executable* does not make PoCol
resistant to them — it only makes the modeled behaviour real enough to measure.

## 2. The accepted-frontier layer is a model, not a protocol mechanism

The three-value separation records what a modeled protocol would accept after a modeled audit.
It does not describe a deployed verification mechanism, and the audit remains an assumed
parameter. An undetected under-report still costs the network real re-evaluation and still
attracts no penalty.

## 3. The re-evaluation window is Stage-5-only machinery

Two accepted Stage-4C guards became window-aware. With Stage 5 disabled they evaluate exactly as
before — this is why all 150 retained tests pass unchanged — but the guards are no longer
literally identical in source. The behavioural equivalence is asserted by the retained suite,
not by textual identity.

## 4. Subassignments are records, not independent search states

Splitting creates real records with disjoint subranges and a conserved capacity budget, and the
entity's throughput is provably unchanged. The physical search still runs as one search state
per miner: the model does not simulate concurrent per-subassignment scheduling. That is
sufficient for the accounting question asked, and insufficient for any scheduling-level claim.

## 5. Virtual identities hold nothing

A virtual identity has no assignment, no lease and no capacity. It exists to let identity count
be reported separately from miner count. It does **not** model identity acquisition cost,
registration, admission control, or any consequence of holding an identity beyond reward
accounting.

## 6. Abandonment is a single declared trigger

An `IDLE_POLICY_DEFECTOR` abandons at its first opportunity after committing work and having
range left. The model does not represent a choice of *when* to abandon, nor abandonment in
response to payoffs — behaviours remain declared, not chosen.

## 7. Floor-overlap measurement depends on observation density

`below_floor_overlap` is measured against the breach intervals the security-floor observer
actually recorded. Those intervals are exact for the observations taken, but the observer is
event-driven: an interval that opens and closes between observations is not represented. The
figure is a measurement of observed breach time, not a continuous-time ground truth.

## 8. The declared zero-offset meaning is a modelling choice

With `false_exhaustion_claims_range_end = False`, `false_exhaustion_claim_offset = 0` means
"claim exactly the current cursor" — a truthful claim, which creates no false-claim record and no
coverage gap. That is a documented convention, chosen so the offset never silently means
"range_end". Any external analysis must read the flag and the offset together.

## 9. Scenario figures remain demonstrations

The scenarios in `STAGE_05A_METRICS.json` are single deterministic runs at N = 4 over a
400-nonce domain. They demonstrate that the corrected paths execute. They are not samples,
carry no confidence intervals, and support no statistical claim. The confirmatory matrix has not
been executed.
