# Stage 5C — Record-Derived Accounting / Global Physical Count / Replay Lock

**Branch:** `thesis-v45-pocol-stage5c-record-derived-accounting-global-physical-count-replay-lock`
**Base:** `7eac7eed3f4b40171b245f9359bdd34b68057c43` (Stage 5B)
**Adapter result schema:** `stage5c.1`
**Tests:** 185 passed (176 retained + 9 new S5C-01 … S5C-07)

Every accepted Stage-5B correction is intact: the physical `RangeProgress` never rewinds, unique
physical work is rewarded once, the canonical `[0,80)` + `[40,100)` example still pays **80 / 20**,
`finalise_incentives` remains replay-idempotent, Path A and Path B share the accepted-frontier
authority, all four real wake lifecycles retain delayed-wake support, abandonment and
false-exhaustion coverage gaps keep their corrected semantics, and Stage 5 remains disabled by
default. No previously rejected behaviour is restored.

---

## 1. What was actually wrong

| # | Defect | Status before Stage 5C |
|---|---|---|
| S5C-1 | `identities = max(len(controlled_miner_ids), sybil_identity_count)` and `split = max(prof.assignment_split_count)` | Amplification came from **requested configuration**, not executed records. One real miner plus three `VirtualIdentityRecord`s counted as **3** identities, not 4 — the real miner was swallowed by the `max`. A split of 8 requested over a 3-nonce range counted as **8**, though only 3 records exist. |
| S5C-2 | `note_physical_evaluation` returned early when Stage 5 was disabled; the adapter forced the residual to 0 when disabled | The honest disabled control reported `physical_evaluation_count = 0` beside a populated evaluation ledger, making it useless as a comparison baseline, and the residual could not detect the discrepancy because it was suppressed. |
| S5C-3 | `maybe_false_exhaustion` resolved no identity before mutating | A **detected** claim left the search state running, so replaying it re-charged the attempt, appended a second `ProgressClaim` and re-incremented the detection counter. An **accepted** claim set `st.completed`, so its replay fell through the guard and answered `None` instead of the outcome it had produced. A refused over-limit action incremented the rejection diagnostic on every re-offer. |
| S5C-4 | The reconciliation emitted one row per *raw* interval | `[40,100)` was reported as a single duplicate interval, hiding that `[80,100)` inside it was newly covered and rewarded. |

## 2. S5C-1 — identity and split amplification derive from executed records

`entity_record_accounting` is the accounting authority. Per entity and round:

| quantity | source |
|---|---|
| `actual_split_units` | the count of `SubAssignmentRecord`s the entity holds in one range lineage |
| `real_identity_count` | the number of real `MinerID`s the entity controls |
| `virtual_identity_count` | the count of `VirtualIdentityRecord`s it actually holds |
| `total_identity_count` | `real + virtual` |

`naive_identity_reward = unique_physical_work × max(1, actual_split_units) × max(1, total_identity_count)`.
`deduplicated_entity_reward` continues to be the entity's unique first-evaluator physical work,
counted exactly once.

**Measured:**

| scenario | real | virtual | total identities | subassignment records | requested split | split ratio | identity ratio |
|---|---:|---:|---:|---:|---:|---:|---:|
| E — 1 miner + 3 identities | 1 | 3 | **4** | 0 | 1 | 1.0 | **4.0** |
| F — 2 miners + 5 identities | 2 | 5 | **7** | 0 | 1 | 1.0 | **7.0** |
| G — split 8 over a 3-nonce span | 1 | 0 | 1 | **3** | **8** | **3.0** | 1.0 |
| H — split ×4 with 3 identities | 1 | 3 | 4 | 4 | 4 | 4.0 | 4.0 |

A requested count can never override the records: scenario G keeps
`assignment_split_count = 8` on the immutable config while the amplification uses **3**.

The per-entity reconciliation table is exposed as `entity_reconciliation` in the adapter result
and carries exactly the columns the directive specifies: `EntityID`, `real_miner_count`,
`virtual_identity_record_count`, `total_identity_count`, `subassignment_record_count`,
`unique_physical_work_reward`, `naive_identity_reward`, `deduplicated_entity_reward`,
`split_amplification_ratio`, `identity_amplification_ratio` (plus `actual_split_units`).

**This is an exploratory sensitivity model of how a naive accounting scheme could be inflated. It
is not Sybil resistance and is never described as such.**

## 3. S5C-2 — the physical evaluation count is global and ledger-derived

`note_physical_evaluation` now counts on **every** committed physical evaluation, with the
Stage-5 model enabled or disabled. Counting executed work is a **report**, not a protocol effect:
the disabled run still creates no adversarial action, claim, reward or penalty, so baseline
preservation holds — which is exactly what the directive states.

The adapter's `physical_evaluation_ledger_residual` is now
`abs(counter − evaluation_ledger_nonce_total)` unconditionally. The `if enabled else 0` guard is
gone, so the residual can no longer hide a discrepancy behind a disabled model.

**Measured across four independent executions:**

| scenario | Stage 5 | leases | physical count | ledger total | residual |
|---|---|---|---:|---:|---:|
| A | disabled | off | **5,975** | 5,975 | 0 |
| B | disabled | on | **5,975** | 5,975 | 0 |
| C | enabled | off | 3,975 | 3,975 | 0 |
| D | enabled | on | 3,975 | 3,975 | 0 |

The `behaviour_profile_count` exemption is **removed** from the acceptance invariant: the
Stage-5C invariant `S5C_2_no_zero_physical_count_beside_a_non_empty_ledger` applies to every
scenario including the disabled control, with no carve-out.

## 4. S5C-3 — false-exhaustion replay is state-pure

The immutable action identity
`(RoundID, TemplateID, MinerID, AssignmentID, actual_frontier)` is resolved **before every guard,
every counter and every mutation**, and an exact replay returns the stored result. Crucially the
lookup precedes the `st.completed` guard — an accepted claim sets that flag, so a guard-first
ordering made the replay of an accepted claim answer `None` instead of its own outcome.

**Measured — the full state delta across two replays:**

| disposition | first result | replay result | third result | state delta | progress claims | budget charged |
|---|---|---|---|---|---:|---:|
| detected / rejected | `None` | `None` | `None` | **{}** | 1 | 1 |
| undetected / accepted | `false_exhaustion_accepted` | `false_exhaustion_accepted` | `false_exhaustion_accepted` | **{}** | 1 | 1 |

Nothing changes: not `adv_actions_this_round`, `false_exhaustion_attempted`,
`false_exhaustion_detected`, `false_exhaustion_accepted`, `coverage_gap_nonce_count`,
`claim_overstatement_total`, `progress_claims`, `adversarial_actions`, the miner/search state or
the event queue. Replay returns the **same object**, so purity is total rather than
value-equivalent.

The rejection diagnostic is replay-safe too: re-offering the same refused identity five times
records `actions_rejected_over_limit = 1`, with zero progress claims and zero budget consumed.

## 5. S5C-4 — the ownership reconciliation is interval-exact

Each lineage's evaluation intervals are cut at the boundaries of every other interval in that
lineage, so each reported row is an **atomic segment** over which the evaluator set is constant.

For `M000` evaluating `[0,80)` and `M001` evaluating `[40,100)`:

| nonce interval | first evaluator | later evaluators | reward owner | rewarded | duplicate |
|---|---|---|---|---:|---:|
| `[0, 40)` | M000 | — | **M000** | 40 | 0 |
| `[40, 80)` | M000 | M001 | **M000** | 40 | **40** |
| `[80, 100)` | M001 | — | **M001** | 20 | 0 |

`[40,100)` is never reported as one duplicate interval. The table reconciles exactly:

* `sum rewarded_count = 100 = unique_rewarded_nonce_count`
* `sum duplicate_count = 40 = duplicate_work_reward_prevented_count`
* reward-owner totals `{M000: 80, M001: 20}` = the WORK_REWARD ledger totals `{M000: 80.0, M001: 20.0}`

Reward amounts and first-evaluator ownership are unchanged — only the representation was
corrected, exactly as the directive required.

## 6. Preservation

`Models/PoCol/stage2/search.py` remains **byte-identical** to the frozen Stage-4C baseline
(`17367b4c15eaabd664a496412bc3d1685bfcd9cf8749f71aea01aef70b094140`), enforced as a CI gate. No
Stage-1 document, protected DOCX/PDF or prior-stage evidence file was touched. Stage 6,
preregistration, the confirmatory matrix, statistical analysis and thesis integration are not
begun. The frozen Stage-2B search core is unmodified.

All 176 previously passing tests are retained. Three mechanical edits were required; none
weakens an assertion:

| File | Edit | Reason |
|---|---|---|
| four suite files | schema literal `stage5b.1` → `stage5c.1` | required by the schema bump; still pins the declared schema exactly |
| `test_stage5b_ownership_pathb_wake_coverage.py` (S5B-01) | the duplicate row is now asserted as the exact segment `[40,80)` owned by and paid to M000, with M001 as the later evaluator | the old assertion (`rewarded_count == 0` on the duplicate row) asserted the *raw-interval* representation the directive now rejects. The replacement is strictly stronger — it pins the interval, the owner, the later evaluator and both counts. |
| `test_stage5_adversarial_incentive.py` (S5-01) | `physical_evaluation_count` excluded from the all-zero sweep and asserted **strongly** instead (`== evaluation_ledger_nonce_total > 0`) | S5C-2 requires the disabled control to report its real count. The directive settles this explicitly: computing the report from the immutable ledger "is not a protocol effect and does not violate baseline preservation". The test now proves *more*: no adversarial action, claim, reward or penalty **and** a correct non-zero physical count. |

No test was deleted, renamed, skipped or relaxed. The corrected S5-18, S5-19 and every Stage-5B
assertion stand.

## 7. Claim scope — unchanged

Stage 5C adds **no** security, fairness, incentive-compatibility, Sybil-resistance,
selfish-mining-resistance, coalition-resistance, common-prefix, chain-quality or
Bitcoin/PoW-equivalent security claim. The algorithm remains PoCol; the energy-saving mechanism
remains the idle policy within PoCol; nonce-domain partitioning alone is never described as an
energy-saving mechanism; the security floor remains an operational active-capacity floor only;
dynamic difficulty remains excluded and no Stage-5 parameter changes the fixed SHA-256 target.
