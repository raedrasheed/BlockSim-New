# Stage 1V — Recovery-Work Semantics Audit (V6)

## 0. Scope and method

This document audits correction **V6** of the Stage 1V formal-specification
revision: the separation of *security-floor (hash-rate) recovery work* from
*coverage repair* inside the `SECURITY_RECOVERY` machinery. It is a
**descriptive audit only** — it records and cross-checks the state of the
specification as it now stands; it prescribes no further change and modifies no
specification artefact.

The audit is grounded exclusively in the current text of the Stage 1 corpus
under `docs/thesis_revision_v45/stage_01/`. The primary source is
`STAGE_01_PROTOCOL_PSEUDOCODE.md`; the corroborating sources are
`STAGE_01_INVARIANT_CATALOGUE.md` (I16), `STAGE_01_ROUND_STATE_MACHINE.md`
(§3.10), and `STAGE_01_TERMINOLOGY.md`. Every claim below cites a procedure or
registry by its actual name and location; where a construct is quoted, the
quotation reproduces the file verbatim. Line numbers are given as an aid to
re-verification and reflect the corpus as read for this audit.

The five load-bearing sites are:

| Site | Location (`STAGE_01_PROTOCOL_PSEUDOCODE.md`) | Role in V6 |
|---|---|---|
| §0.8 recovery-WORK registries | lines 714–745 | declares `RECOVERY_WORK_CLASS`, tags `RECOVERY_WORK_ACTION`, adds `work_class` to `work_record` |
| `ClassifyRecoveryWork` | line 2683 (header at 2683) | now returns `{ RESERVE_ACTIVATION_REQUIRED, NONE }` only |
| `SecurityFloorEvaluate` (SECURITY_RECOVERY branch) | line 2276 (branch at 2347–2379) | seats **only** security-floor work in the breach-before-deadline path |
| `ReconcilePendingRecoveryWork` | line 2515 | judges "still warranted" via `ClassifyRecoveryWork(...) != NONE` |
| `PrepareRecoveryAssignmentPlan` | line 3378 | tags each spec with its `RECOVERY_WORK_CLASS` |

---

## 1. The defect V6 corrects

Before V6, the recovery-work classifier `ClassifyRecoveryWork` could return
`RANGE_REDISTRIBUTION_REQUIRED` on the **security-floor** recovery path — i.e. a
range redistribution among the *same* `ACTIVE_HASHING` miners was admissible as
an answer to the question "which security-floor recovery work should be
attempted while the floor is still breached?". That conflation is unsound for a
single, decisive reason recorded in the specification itself:

> "a redistribution AMONG THE SAME ACTIVE_HASHING miners cannot alter
> H_active/H_honest/q_adv (the census sums over the SAME active set)"
> — `ClassifyRecoveryWork`, EFFECTS, lines 2689–2691.

The security-floor census is defined over the `ACTIVE_HASHING` set:
`H_active(t)`, `H_honest(t)`, and `q_adv(t)` are functions of *which miners are
active and how much honest/adversarial hash rate they contribute*
(`SecurityFloorEvaluate`, lines 2308–2323). A redistribution that only
re-partitions disjoint nonce ranges across an unchanged active set leaves every
term of those sums untouched. Permitting such a redistribution to be classified
as security-floor recovery work therefore let a **coverage-only repair
masquerade as a census-changing, breach-relevant action**: the round could
appear to be "doing security-floor recovery work" — and could feed the
breach-before-deadline outcome logic — while making *no* claim on `H_active`,
`H_honest`, or `q_adv` that could ever repair the breach. The result is an
**unsound claim on `H_active` / `q_adv`**: reported recovery activity that
cannot, even in principle, change the quantity whose breach it purports to
address.

V6 removes the conflation by partitioning recovery work into two disjoint
classes and confining each of the two admissible actions to exactly one class.

---

## 2. The two recovery-work classes

V6 introduces the enumeration `RECOVERY_WORK_CLASS` in the §0.8 registries
(lines 720–727):

> "`V6 RECOVERY_WORK_CLASS in { SECURITY_FLOOR_RECOVERY_WORK, COVERAGE_REPAIR_WORK }`"

The two classes are distinguished by exactly one property — *whether the action
can change the `ACTIVE_HASHING` census* — and everything else (census effect,
breach-outcome relevance) follows from it:

| Class | What it MAY change | Census effect (`H_active`/`H_honest`/`q_adv`) | Breach-outcome relevance | Example action |
|---|---|---|---|---|
| `SECURITY_FLOOR_RECOVERY_WORK` | the `ACTIVE_HASHING` census (activates reserve hash rate / replaces participation) | **can change** the census sums | **controls** the breach-before-deadline outcome logic; only this class is returned by `ClassifyRecoveryWork` | reserve activation (`RESERVE_ACTIVATION_REQUIRED`); a declared honest/adversarial participation replacement |
| `COVERAGE_REPAIR_WORK` | nonce-domain / assignment coverage among the SAME active miners | **cannot change** the census sums (same active set) | **exerts no control** over the breach-before-deadline outcome logic | range redistribution (`RANGE_REDISTRIBUTION_REQUIRED`) among active miners; a no-breach branch-C redistribution |

This is the verbatim registry basis for the table:

- `SECURITY_FLOOR_RECOVERY_WORK` — "actions that can ACTUALLY change the
  ACTIVE_HASHING census (H_active/H_honest/q_adv): reserve activation, or a
  declared honest/adversarial participation replacement. ONLY this class is
  returned by ClassifyRecoveryWork and controls the breach-before-deadline
  outcome logic." (lines 721–723).
- `COVERAGE_REPAIR_WORK` — "nonce-domain / assignment coverage repair (e.g.
  RANGE_REDISTRIBUTION_REQUIRED among the SAME ACTIVE_HASHING miners). It does
  NOT claim to restore H_active/H_honest/q_adv and does NOT control the
  breach-before-deadline outcome logic (a same-active-miner redistribution
  cannot change the census sums). A redistribution AFTER a no-breach census is
  the branch-C redistribution-only continuation (§10a)." (lines 724–727).

The action enumeration is correspondingly annotated with the class of each
value (lines 728–729):

> "`RECOVERY_WORK_ACTION in { RESERVE_ACTIVATION_REQUIRED (SECURITY_FLOOR_RECOVERY_WORK),`
>  `                          RANGE_REDISTRIBUTION_REQUIRED (COVERAGE_REPAIR_WORK), NONE }   # U1/V6`"

**The class is a first-class field of the work record.** The `recovery_work`
map's value type carries the class explicitly (lines 732–734):

> "map RecoveryWorkID -> work_record { episode, action (RECOVERY_WORK_ACTION),
>  **work_class (RECOVERY_WORK_CLASS, V6)**, bound_census_version
>  (RecoveryCensusVersion), … }"

so the class is not merely a comment: it is durable state attached to every
recovery-work identity.

---

## 3. `ClassifyRecoveryWork` is now security-floor-only

The classifier's header states its narrowed remit directly (line 2683):

> "`FUNCTION ClassifyRecoveryWork   # U1/V6: compute-only — which SECURITY-FLOOR recovery WORK (if any) to attempt`"

Its declared return set is now the two-value set (line 2699):

> "`RETURNS: RECOVERY_WORK_ACTION in { RESERVE_ACTIVATION_REQUIRED, NONE }   # V6: no coverage-only action here`"

The body returns `RESERVE_ACTIVATION_REQUIRED` in exactly the two
census-changing cases and `NONE` otherwise (lines 2694–2698):

> "`IF there is at least one miner in RESERVE that can be activated to add honest hash rate toward the deficit:`
>  `  RETURN RESERVE_ACTIVATION_REQUIRED`  … (reserve activation CHANGES the ACTIVE_HASHING census)
>  `IF a DECLARED honest/adversarial participation replacement can change the ACTIVE_HASHING census toward the floor:`
>  `  RETURN RESERVE_ACTIVATION_REQUIRED`  … (a census-changing participation replacement is the same work class)
>  `RETURN NONE`  … (no census-changing security-floor work is available)"

Note that a census-changing *participation replacement* is folded into the same
returned token `RESERVE_ACTIVATION_REQUIRED` (line 2697), because both are
`SECURITY_FLOOR_RECOVERY_WORK`; the classifier never emits a distinct
coverage-only token.

**`RANGE_REDISTRIBUTION_REQUIRED` has been removed from the security-floor
path.** The EFFECTS block records the removal explicitly (lines 2692–2693):

> "it is COVERAGE_REPAIR_WORK (§0.8), which does not control the
> breach-before-deadline outcome logic. **RANGE_REDISTRIBUTION_REQUIRED is
> therefore REMOVED from security-floor recovery.**"

and the closing NOTE reiterates it (lines 2700–2704):

> "A same-active-miner range redistribution cannot change H_active/H_honest/q_adv,
> so it can never repair a security-floor breach and is classified as
> COVERAGE_REPAIR_WORK (§0.8) — NOT returned here and NOT controlling the
> breach-before-deadline outcome logic."

**Grep evidence.** A search for `RANGE_REDISTRIBUTION_REQUIRED` across the
pseudocode returns it only inside `PrepareRecoveryAssignmentPlan`'s `INPUTS`
signature (line 3379), inside `SeatRecoveryWork`'s `INPUTS` comment (line 2707),
at the branch-C continuation call site (line 3291), and inside prose that names
it as the *removed / coverage-only* token (lines 724, 729, 2692). It does **not**
appear on any `RETURN` line of `ClassifyRecoveryWork`; the only `RETURN` values
there are `RESERVE_ACTIVATION_REQUIRED` and `NONE` (lines 2695, 2697, 2698). The
removal is thus confirmed at the level of the actual control flow, not merely in
commentary.

**Only security-floor work is seated in the breach path.** In
`SecurityFloorEvaluate`, the `SECURITY_RECOVERY` branch (lines 2347–2379)
reaches `ClassifyRecoveryWork` only on the breach-before-deadline outcome
(`warranted = NONE`, lines 2367–2376):

> "`SET work_action <- CALL ClassifyRecoveryWork(RoundContext, episode, census)   # U1/V6: SECURITY_FLOOR_RECOVERY_WORK only`"
> "`IF work_action != NONE:`"
> "`  RETURN CALL SeatRecoveryWork(RoundContext, episode, work_action, t, census.RecoveryCensusVersion)`"

Because `work_action` can now only be `RESERVE_ACTIVATION_REQUIRED` or `NONE`,
the work seated on this path is necessarily `SECURITY_FLOOR_RECOVERY_WORK`; no
coverage-only action can be seated here. This is the single seating site for
breach-triggered recovery work, and it is reachable only from
`round_state = SECURITY_RECOVERY` (line 2347).

---

## 4. Where coverage redistribution now lives

Removing `RANGE_REDISTRIBUTION_REQUIRED` from the security-floor path does not
delete range redistribution from the protocol — it relocates it to the one
context where it is sound: **after a no-breach final census**, as the
*branch-C redistribution-only continuation* (§10a).

That continuation is defined so that its final census shows **no** breach; its
own header records the precondition (lines 3260–3263):

> "the continuation is REDISTRIBUTION-ONLY — its FINAL census shows NO breach, so
> the floor is already met by currently ACTIVE_HASHING miners and the install
> only re-partitions disjoint ranges; it NEVER depends on future reserve hash
> rate (reserve activation while the floor is still breached is recovery WORK,
> §9c, not a continuation)."

The continuation applies branch C only when `census.breach = false`
(lines 3279–3287); it is at this fresh-and-warranted point — and only here —
that it prepares a redistribution plan (line 3291):

> "`SET plan <- CALL PrepareRecoveryAssignmentPlan(RoundContext, episode, RANGE_REDISTRIBUTION_REQUIRED, census)`"

Consequently, a range redistribution now occurs in exactly one place: **after**
the security floor has already been met by the active set, as coverage repair
that asserts nothing about hash rate. It never occurs *as* a claimed remedy for
a live breach. `ClassifyRecoveryWork`'s NOTE closes the loop on this
relocation (lines 2703–2704):

> "A redistribution AFTER a no-breach census remains the branch-C
> redistribution-only continuation (§10a), never a breach-repairing action."

---

## 5. Spec tagging in `PrepareRecoveryAssignmentPlan`

`PrepareRecoveryAssignmentPlan` (line 3378) is the shared compute-only planner
used both by recovery work (`SECURITY_RECOVERY`, §9c) and by the redistribution
continuation (`ASSIGNMENT`, §10a); its preconditions name both callers
(lines 3380–3381). It labels every assignment spec it emits with the spec's
`RECOVERY_WORK_CLASS`, so the class travels with the plan into the commit
step (lines 3390–3396):

> "V6: a RESERVE_ACTIVATION spec is SECURITY_FLOOR_RECOVERY_WORK (it changes the
> ACTIVE_HASHING census); a REDISTRIBUTION spec is COVERAGE_REPAIR_WORK
> (nonce-domain coverage) or a no-breach branch-C redistribution — it does NOT
> claim to change H_active/H_honest/q_adv."

The tagging is honoured at the commit boundary in `CommitRecoveryAssignmentPlan`
(lines 3410–3467), where the two spec kinds are dispatched on their class:

- the reserve-activation branch is annotated as census-changing
  (line 3427):

  > "`IF spec.kind = RESERVE_ACTIVATION:   # V6: a SECURITY_FLOOR_RECOVERY_WORK spec (changes the census)`"

- the redistribution branch is annotated as coverage-only / no-breach
  (line 3447):

  > "`ELSE:  # REDISTRIBUTION spec (RangeReassign / RangeAssign) — V6: COVERAGE_REPAIR_WORK, or a no-breach branch-C redistribution`"

Thus the class assigned at planning time (`RESERVE_ACTIVATION` →
`SECURITY_FLOOR_RECOVERY_WORK`; `REDISTRIBUTION` → `COVERAGE_REPAIR_WORK`) is the
same class recorded in the `work_record.work_class` field (§0.8, line 733) and
the same class the classifier enforces at selection time (§3 above). The three
sites agree.

---

## 6. Soundness argument

The V6 partition is sound because **only census-changing work can influence the
security-floor / breach outcome, and coverage repair cannot** — and the
specification now makes that the *definition* of the security-floor class rather
than an incidental property.

1. **The breach predicate is a function of the `ACTIVE_HASHING` census only.**
   `SecurityFloorEvaluate` sets `breach` solely from `H_active(t)`,
   `H_honest(t)`, and `q_adv(t)` against the floor thresholds
   (lines 2308–2323). The warranted outcome is then a function of that census
   alone: no breach → `RESTORED`; breach with deadline reached →
   `UNRECOVERABLE`; breach before deadline → keep waiting (lines 2364–2366).

2. **An action that cannot change the census cannot change the breach
   predicate.** A redistribution among the same active miners leaves
   `H_active`, `H_honest`, and `q_adv` — the census sums over the *same* active
   set — unchanged (`ClassifyRecoveryWork`, lines 2689–2691). Therefore it can
   never move the breach predicate from `true` to `false`, and can never be the
   cause of a `RESTORED` outcome.

3. **Hence only `SECURITY_FLOOR_RECOVERY_WORK` may control the
   breach-before-deadline logic.** By confining `ClassifyRecoveryWork` to
   `{ RESERVE_ACTIVATION_REQUIRED, NONE }` (line 2699), the specification
   guarantees that the only work ever attempted *as* a breach remedy is work
   that can, in principle, change the census. This is enforced not only at the
   selection site (§3) but also at the *warrant* test in
   `ReconcilePendingRecoveryWork`, where in-flight work counts as "still
   warranted" only if `ClassifyRecoveryWork(...) != NONE` (line 2523–2524):

   > "`SET still_warranted <- (census.breach = true AND census.deadline_reached = false`
   >  `                        AND CALL ClassifyRecoveryWork(RoundContext, episode, census) != NONE)   # V6: still a security-floor breach before deadline`"

   Because the classifier can no longer answer with a coverage-only action, a
   redistribution can never keep a recovery-work record "warranted" against a
   live breach.

4. **Coverage repair is not thereby lost; it is confined to a sound context.**
   It runs only after a no-breach census (§4), where it repairs nonce-domain
   coverage without asserting anything about hash rate. Its class,
   `COVERAGE_REPAIR_WORK`, is precisely the marker that it "does NOT control the
   breach-before-deadline outcome logic" (§0.8, lines 725–726).

The net effect is that the reported recovery state can no longer overstate
safety: a coverage-only repair can never be recorded, reconciled, or seated as
though it were census-changing security-floor recovery, and therefore can never
underwrite an unsound claim on `H_active` / `H_honest` / `q_adv`. This aligns
the recovery-work machinery with the U1 principle that a recovery-work action is
"NEVER a `RecoveryOutcome` and … NEVER marked `APPLIED` as `RESTORED`" (§0.8,
lines 714–719) — RESTORED is minted only from a later no-breach *final census*,
never from the act of doing work.

---

## 7. Traceability

### 7.1 Invariant I16

`STAGE_01_INVARIANT_CATALOGUE.md` §I16 — *"Security-floor breaches are recorded,
not silently repaired in the reported data."* (header, line 284) — carries the
V6 note verbatim (lines 313–319):

> "**V6 (security-floor recovery work must change the census):** only an action
> that can ACTUALLY change the `ACTIVE_HASHING` census — `H_active`/`H_honest`/
> `q_adv` (reserve activation, or a declared honest/adversarial participation
> replacement) — is `SECURITY_FLOOR_RECOVERY_WORK` and controls the
> breach-before-deadline logic. A range redistribution AMONG THE SAME
> `ACTIVE_HASHING` miners cannot change those census sums, so it can never repair
> a security-floor breach; it is `COVERAGE_REPAIR_WORK` (`ClassifyRecoveryWork`
> no longer returns `RANGE_REDISTRIBUTION_REQUIRED`), and a redistribution after
> a no-breach census remains the branch-C redistribution-only continuation."

This is consistent with the classifier's actual return set (§3) and with the
soundness argument (§6): I16 guards against a breach being *silently repaired in
the reported data*, and V6 is precisely the correction that stops a coverage-only
repair from being reported as breach-relevant recovery.

### 7.2 Round state machine §3.10

`STAGE_01_ROUND_STATE_MACHINE.md` §3.10 ("What happens after a security-floor
violation", header line 382) carries the V6 addendum block (lines 610–614):

> "**V6 (separate hash-rate recovery from coverage repair).**
> `SECURITY_FLOOR_RECOVERY_WORK` is only an action that can CHANGE the
> `ACTIVE_HASHING` census (reserve activation / declared participation
> replacement); a same-active-miner range redistribution cannot change
> `H_active`/`H_honest`/`q_adv`, so it is `COVERAGE_REPAIR_WORK` and does NOT
> control the breach-before-deadline outcome logic.
> `RANGE_REDISTRIBUTION_REQUIRED` is removed from `ClassifyRecoveryWork`; a
> redistribution after a no-breach census remains the branch-C
> redistribution-only continuation."

### 7.3 Terminology

`STAGE_01_TERMINOLOGY.md` records the class distinction as a defined-term entry
(lines 810–813):

> "**`SECURITY_FLOOR_RECOVERY_WORK` vs `COVERAGE_REPAIR_WORK` (V6).**
> `RECOVERY_WORK_CLASS`: only census-changing actions (reserve activation /
> declared participation replacement) are `SECURITY_FLOOR_RECOVERY_WORK` and
> control the breach-before-deadline logic; a same-active-miner redistribution is
> `COVERAGE_REPAIR_WORK` (cannot change `H_active`/`H_honest`/`q_adv`) and
> `ClassifyRecoveryWork` no longer returns `RANGE_REDISTRIBUTION_REQUIRED`."

### 7.4 Consistency verdict

All four corroborating sites (I16, §3.10, terminology, and the §0.8 registries)
state the same three facts and are mutually consistent with the pseudocode:

1. `SECURITY_FLOOR_RECOVERY_WORK` is exactly the census-changing actions
   (reserve activation / declared participation replacement) and is the only
   class that controls the breach-before-deadline logic.
2. `COVERAGE_REPAIR_WORK` (a same-active-miner redistribution) cannot change
   `H_active` / `H_honest` / `q_adv` and controls nothing about the breach
   outcome.
3. `ClassifyRecoveryWork` no longer returns `RANGE_REDISTRIBUTION_REQUIRED`; a
   redistribution after a no-breach census is the branch-C redistribution-only
   continuation.

No divergence, missing construct, or contradiction was found among the audited
sites. Every V6 construct named in the correction brief — the two-value
`RECOVERY_WORK_CLASS`, the `work_record.work_class` field, the narrowed
`ClassifyRecoveryWork` return set, the spec tagging in
`PrepareRecoveryAssignmentPlan` / `CommitRecoveryAssignmentPlan`, and the
security-floor-only seating in `SecurityFloorEvaluate` — is present in the
current files as described.
