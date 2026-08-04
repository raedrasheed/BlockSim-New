#!/usr/bin/env python3
"""Stage 6 — the frozen PoCol confirmatory scenario definitions.

This module is the SINGLE source of truth for the Stage-6 scenario matrix.  The matrix
generator, the pilot harness, the frozen confirmatory configs, the preregistration validator
and the Stage-6 validation tests all import from here, so a row cannot drift between the
document and the executable definition.

It builds ACCEPTED ``Stage2Config`` objects only.  It adds no engine capability, changes no
executable model code, and introduces no new seed mechanism: a master seed reaches the engine
solely through the two accepted fields ``template_seed`` and ``adversarial.deterministic_seed``.

CLAIM SCOPE (unchanged from Stage 5).  The algorithm is PoCol.  The energy-saving mechanism is
the idle policy within PoCol; nonce-domain partitioning alone is never an energy-saving
mechanism.  The security floor is an operational active-capacity floor only.  Nothing here
claims unconditional energy reduction, incentive compatibility, fairness, Sybil resistance,
selfish-mining resistance, coalition resistance, common-prefix security, chain-quality security
or Bitcoin/PoW-equivalent security.
"""
from __future__ import annotations

import math
import pathlib
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from Models.PoCol.stage2 import (Stage2Config, AdversarialPolicy,      # noqa: E402
                                 IncentivePolicy, RangeLeasePolicy)
from Models.PoCol.stage2.security import SecurityFloorPolicy           # noqa: E402

# ------------------------------------------------------------------ reference configuration
# Read from the ACCEPTED frozen baseline (Models/PoCol/stage2/config.py) and asserted below,
# so a silent upstream change fails loudly rather than silently re-parameterising the study.
REFERENCE = {
    "num_miners": 141,
    "horizon_T": 10_000.0,
    "P_hash": 21.5,
    "P_listen": 2.15,
    "P_wake": 10.75,
    "P_offline": 0.0,
    "nonce_domain_size": 4000,
    "difficulty": 1000,
    "batch_size": 50,
    "base_hash_rate": 100.0,
    "reserve_fraction": 0.2,
}
A1_REFERENCE_KWH = 8.420833333
A1_TOLERANCE_KWH = 1e-9

#: The frozen batch size for the IP-H10d matched pair (D04C / D04).  Progress withholding
#: under-reports COMMITTED progress, so an intermediate committed frontier must exist, which
#: needs a batch boundary strictly inside a primary's range:
#:     nonce_domain_size / primary_count > batch_size
#: At the reference batch_size 50 that is 4000/113 = 35.4 > 50, i.e. FALSE.  At 25 it holds.
#: Both arms of the pair carry this value, so the contrast still changes exactly one factor.
PROGRESS_PAIR_BATCH_SIZE = 25

#: The single fixed confirmatory difficulty.  No confirmatory condition changes it dynamically,
#: and difficulty is never an experimental factor in the confirmatory matrix (C06 is the one
#: declared non-inferential integrity condition — see ``C06_NOTE``).
CONFIRMATORY_DIFFICULTY = 1000

#: C06 uses an unreachable target so that EVERY round deterministically exhausts the full nonce
#: domain without finding a block.  That is the only way to make the full-domain coverage gate a
#: certainty rather than a ~1.8% chance event at difficulty 1000.  C06 is therefore declared a
#: NON-INFERENTIAL deterministic integrity condition: it is excluded from every paired contrast,
#: from every multiplicity family and from every energy, service and incentive claim.
UNREACHABLE_DIFFICULTY = 1 << 300
C06_NOTE = ("non-inferential deterministic integrity condition; unreachable fixed target so the "
            "full nonce domain is exhausted in every round; excluded from all paired contrasts, "
            "all multiplicity families and all energy/service/incentive claims")

# ------------------------------------------------------------------ Tier definitions
#: Tier 1 — reduced-scale SEMANTIC pilot: does every frozen scenario type construct, execute and
#: expose the preregistered fields?  Not a scaled-down experiment; a configuration validator.
#: ``nominal_round_period`` is the declared round length used to phase the injected fault
#: schedule.  It is a TIMING constant, not an outcome.  It must be the MEAN round length
#: (horizon / rounds executed), not the median: a fixed absolute schedule accumulates drift
#: equal to (mean - assumed) x round index, so using the Tier-1 median 1.40 s instead of the
#: mean 1.2987 s drifted the schedule by -14 s (ten whole rounds) by round 150 and the injected
#: faults stopped landing on live leases altogether.  Measured: both Tier-1 pilot seeds execute
#: 154 rounds over 200 s (1.2987 s); the confirmatory scale executes about 9 700 rounds over
#: 10 000 s (1.031 s).
TIER1 = {"num_miners": 12, "horizon_T": 200.0, "nonce_domain_size": 400, "batch_size": 25,
         "nominal_round_period": 1.2987}
#: Tier 2 — full-scale RUNTIME pilot: wall clock, memory, output size, event count.
TIER2 = {"num_miners": REFERENCE["num_miners"], "horizon_T": REFERENCE["horizon_T"],
         "nonce_domain_size": REFERENCE["nonce_domain_size"],
         "batch_size": REFERENCE["batch_size"], "nominal_round_period": 1.02}

#: Which four full-scale configurations the Tier-2 runtime pilot executes (one pilot seed each).
TIER2_SCENARIOS = ("A03", "A05", "B02", "C04")

# ------------------------------------------------------------------ derived population facts
# Mirrors the ACCEPTED genesis rule in simulator.py:
#     all_ids  = sorted "M000".."M{N-1:03d}"
#     n_reserve = floor(reserve_fraction * N);  reserves are the LAST n_reserve ids
#     primaries keep their enumerate() index, so hash_rate_for(idx) applies with idx = 0..P-1
# The Tier-1 pilot verifies this derivation against the executed engine.


def miner_ids(num_miners: int) -> list:
    return [f"M{i:03d}" for i in range(num_miners)]


def reserve_count(num_miners: int, reserve_fraction: float) -> int:
    return int(math.floor(reserve_fraction * num_miners))


def primary_count(num_miners: int, reserve_fraction: float) -> int:
    return num_miners - reserve_count(num_miners, reserve_fraction)


def initial_active_primary_hash_rate(num_miners: int, reserve_fraction: float,
                                     base_hash_rate: float, heterogeneous: bool) -> float:
    """H0 — the summed ACTUAL hash rate of the initially active PRIMARY miners."""
    p = primary_count(num_miners, reserve_fraction)
    if not heterogeneous:
        return float(p) * base_hash_rate
    return float(sum(base_hash_rate * (1.0 + (i % 4)) for i in range(p)))


def total_population_hash_rate(num_miners: int, base_hash_rate: float,
                               heterogeneous: bool) -> float:
    """The summed ACTUAL hash rate of every miner, primary and reserve alike."""
    if not heterogeneous:
        return float(num_miners) * base_hash_rate
    return float(sum(base_hash_rate * (1.0 + (i % 4)) for i in range(num_miners)))


def adversarial_entity_miners(num_miners: int, fraction: float = 0.10) -> tuple:
    """The FIXED deterministic adversarial entity set: ceil(fraction * N) miners by sorted ID.

    Chosen by a preregistered rule before any pilot result was inspected.  Attackers are never
    selected after viewing pilot effects.
    """
    k = math.ceil(fraction * num_miners)
    return tuple(miner_ids(num_miners)[:k])


ADVERSARIAL_FRACTION = 0.10

# ------------------------------------------------------------------ the experimental factor
#: The Block-A experimental factor is THE IDLE POLICY, indexed by the standby-power ratio
#: rho = P_listen/P_hash = P_reserve/P_hash.
#:
#: rho = 1.00 is the level at which THE IDLE POLICY IS OFF.  "Off" means no state draws less
#: than hashing power while the miner is not offline, so P_wake is ALSO raised to P_hash at that
#: level.  This is not an extra factor: it is what switching the mechanism off means.  Without
#: it the negative control is not a negative control, because the Tier-1 pilot measured WAKING
#: at roughly 62 % of all residency (the 1.0 s wake latency dominates a ~1.4 s round), so a
#: transient wake power below P_hash would by itself produce an apparent "saving" of about
#: 0.0045 kWh at Tier-1 scale — five million times the 1e-9 kWh IP-H5 tolerance.
#:
#: At every rho < 1.00 the transient wake power is held at its frozen reference value 10.75 W,
#: so the rho = 0.10 row is exactly the reference PoCol idle policy the thesis claim is about.
#:
#: IP-H5 exactness at rho = 1.00 additionally requires OFFLINE/DISQUALIFIED residency to be
#: zero.  That is a preregistered per-run precondition, verified by the pilot (measured exactly
#: 0.000 s across all 42 Tier-1 runs) and re-verified on every confirmatory run.  It is never
#: assumed.
IDLE_RATIOS = {"1.00": 1.00, "0.25": 0.25, "0.10": 0.10, "0.00": 0.00}

#: The declared reference transient wake power, held constant at every rho < 1.00.
REFERENCE_P_WAKE = REFERENCE["P_wake"]


def powers_for_ratio(rho: float) -> dict:
    idle_policy_off = (rho >= 1.0)
    return {"P_hash": REFERENCE["P_hash"],
            "P_listen": rho * REFERENCE["P_hash"],
            "P_reserve": rho * REFERENCE["P_hash"],
            "P_wake": REFERENCE["P_hash"] if idle_policy_off else REFERENCE_P_WAKE,
            "P_offline": REFERENCE["P_offline"]}


# ------------------------------------------------------------------ policy builders
_DISABLED_FLOOR = SecurityFloorPolicy()          # enabled=False
_DISABLED_LEASE = RangeLeasePolicy()             # enabled=False
_DISABLED_ADV = AdversarialPolicy()              # enabled=False
_DISABLED_INC = IncentivePolicy()                # enabled=False


def floor_policy(minimum_active_hash_rate: float,
                 minimum_active_miner_count=None) -> SecurityFloorPolicy:
    """The IP-H7 operational floor policy, with every field frozen by the directive."""
    return SecurityFloorPolicy(
        enabled=True,
        minimum_active_hash_rate=minimum_active_hash_rate,
        minimum_active_miner_count=minimum_active_miner_count,
        activation_trigger_mode="ON_CAPACITY_CHANGE",
        reserve_selection_policy="MINIMUM_CARDINALITY",
        activation_wake_latency=1.0,
        floor_tolerance=0.0)


def lease_policy(no_eligible_miner_policy: str = "CONTINUE_WITH_UNASSIGNED_RANGE",
                 reassignment_enabled: bool = True) -> RangeLeasePolicy:
    return RangeLeasePolicy(enabled=True,
                            reassignment_enabled=reassignment_enabled,
                            reassignment_wake_latency=1.0,
                            lease_duration=1e18,
                            progress_timeout=1e18,
                            no_eligible_miner_policy=no_eligible_miner_policy)


def incentive_policy() -> IncentivePolicy:
    """Block-C/D incentive accounting.  Incentive quantities are SECONDARY EXPLORATORY only."""
    return IncentivePolicy(enabled=True, r_work=1.0, r_avail=1.0, r_win=1.0,
                           r_reserve=1.0, r_reassign=1.0,
                           q_abandon=1.0, q_false=1.0, q_invalid=1.0)


def adversarial_policy(flags: tuple, num_miners: int, **pol) -> AdversarialPolicy:
    """Declare the FIXED adversarial entity set with the given behaviour flags."""
    miners = adversarial_entity_miners(num_miners, ADVERSARIAL_FRACTION)
    return AdversarialPolicy(
        enabled=True,
        entities=(("E-ADV", pol.pop("actor_class", "BYZANTINE"), tuple(miners), None),),
        miner_behaviours=tuple((0, m, tuple(flags)) for m in miners),
        **pol)


# ------------------------------------------------------------------ the frozen matrix
# Every row declares its own overrides.  ``build_config`` composes reference + tier + row.

def _blockA():
    rows = []
    spec = [("A01", False, "1.00", None), ("A02", False, "0.10", "A01"),
            ("A03", True, "1.00", None), ("A04", True, "0.25", "A03"),
            ("A05", True, "0.10", "A03"), ("A06", True, "0.00", "A03")]
    hyp = {"A01": "IP-H1;IP-H2;IP-H3;IP-H5", "A02": "IP-H1;IP-H2;IP-H3",
           "A03": "IP-H1;IP-H2;IP-H4;IP-H5;IP-H6", "A04": "IP-H1;IP-H2;IP-H6",
           "A05": "IP-H1;IP-H2;IP-H4;IP-H6", "A06": "IP-H1;IP-H2;IP-H6"}
    for sid, hetero, ratio_key, control in spec:
        rows.append({
            "scenario_id": sid, "block_id": "A",
            "confirmatory_or_exploratory": "CONFIRMATORY",
            "paired_control_id": control or "SELF",
            "hypothesis_ids": hyp[sid],
            "heterogeneous_hash_rates": hetero,
            "idle_power_ratio": ratio_key,
            "security_floor_policy": "DISABLED",
            "range_lease_policy": "DISABLED",
            "adversarial_policy": "DISABLED",
            "incentive_policy": "DISABLED",
            "fault_schedule": "NONE",
            "difficulty": CONFIRMATORY_DIFFICULTY,
            "notes": ("mechanistic idle-policy energy; the ONLY factor is the idle-power ratio "
                      "rho = P_listen/P_hash = P_reserve/P_hash"),
        })
    return rows


def _blockB():
    hetero = True
    h0 = initial_active_primary_hash_rate(REFERENCE["num_miners"], REFERENCE["reserve_fraction"],
                                          REFERENCE["base_hash_rate"], hetero)
    htotal = total_population_hash_rate(REFERENCE["num_miners"], REFERENCE["base_hash_rate"],
                                        hetero)
    p = primary_count(REFERENCE["num_miners"], REFERENCE["reserve_fraction"])
    rows = [
        {"scenario_id": "B01", "paired_control_id": "SELF",
         "security_floor_policy": "DISABLED", "floor_min_hash_rate": "NA",
         "floor_min_miner_count": "NA",
         "notes": "matched control for the security-floor contrasts; floor disabled"},
        {"scenario_id": "B02", "paired_control_id": "B01",
         "security_floor_policy": "ENABLED_MIN_HASH_RATE",
         "floor_min_hash_rate": 0.80 * h0, "floor_min_miner_count": "NA",
         "notes": ("operational floor at 0.80 x initial active-primary ACTUAL hash rate, "
                   "MINIMUM_CARDINALITY reserve activation")},
        {"scenario_id": "B03", "paired_control_id": "B01",
         "security_floor_policy": "ENABLED_MIN_HASH_RATE_AND_MIN_COUNT",
         "floor_min_hash_rate": 0.80 * h0,
         "floor_min_miner_count": p,
         "notes": ("floor additionally constrained by a minimum ACTIVE-MINER COUNT equal to the "
                   "full initial primary count, so the count constraint genuinely binds; at "
                   "ceil(0.80 x primary count) the Tier-1 pilot measured B03 identical to B02 "
                   "in every field, which would have made the row evidentially empty")},
        {"scenario_id": "B04", "paired_control_id": "B01",
         "security_floor_policy": "ENABLED_UNATTAINABLE",
         "floor_min_hash_rate": 1.50 * htotal, "floor_min_miner_count": "NA",
         "notes": ("DIAGNOSTIC ONLY: floor deliberately unattainable (1.50 x total population "
                   "capacity) to exercise CONTINUE_DEGRADED; MUST NOT be merged into the primary "
                   "energy claim")},
    ]
    for r in rows:
        r.update({"block_id": "B",
                  "confirmatory_or_exploratory": "CONFIRMATORY",
                  "hypothesis_ids": "IP-H1;IP-H2;IP-H7;IP-H8",
                  "heterogeneous_hash_rates": hetero,
                  "idle_power_ratio": "0.10",
                  "range_lease_policy": "DISABLED",
                  "adversarial_policy": "DISABLED",
                  "incentive_policy": "DISABLED",
                  "fault_schedule": "NONE",
                  "difficulty": CONFIRMATORY_DIFFICULTY})
    return rows


def _blockC():
    """Lease / reassignment robustness.

    ``fault_schedule`` entries are ``(round_seq, MinerID, fail_time, reason)`` in the ACCEPTED
    ``injected_lease_faults`` form.  The identities and times are FIXED here, before Stage 7,
    and are calibrated by the Tier-1 pilot for executability only — never for effect size.
    """
    rows = [
        {"scenario_id": "C01", "paired_control_id": "SELF",
         "range_lease_policy": "ENABLED", "reserve_fraction": REFERENCE["reserve_fraction"],
         "fault_schedule": "NONE",
         "notes": "matched control: leases enabled, no injected failure"},
        {"scenario_id": "C02", "paired_control_id": "C01",
         "range_lease_policy": "DISABLED", "reserve_fraction": REFERENCE["reserve_fraction"],
         "fault_schedule": "FAULT_SET_DENSE",
         "notes": "injected failure with leases and reassignment DISABLED"},
        {"scenario_id": "C03", "paired_control_id": "C01",
         "range_lease_policy": "ENABLED", "reserve_fraction": 0.0,
         "fault_schedule": "FAULT_SET_DENSE",
         "notes": ("Path A: no reserve pool, so the reassignee is an already-live primary and "
                   "no Stage-3 wake is required")},
        {"scenario_id": "C04", "paired_control_id": "C01",
         "range_lease_policy": "ENABLED", "reserve_fraction": REFERENCE["reserve_fraction"],
         "fault_schedule": "FAULT_SET_DENSE",
         "notes": ("Path B: identical to C03 except that a reserve pool exists, so the "
                   "reassignment comes from a GENUINE Stage-3 reserve wake through a non-domain "
                   "ReassignmentWakeHandle rather than from a live primary")},
        {"scenario_id": "C05", "paired_control_id": "C01",
         "range_lease_policy": "ENABLED_NO_REASSIGN", "reserve_fraction": 0.0,
         "fault_schedule": "FAULT_SET_DENSE",
         "notes": ("no eligible miner: CONTINUE_WITH_UNASSIGNED_RANGE leaves the range "
                   "unassigned and the coverage gap must be reported, not hidden")},
        {"scenario_id": "C06", "paired_control_id": "NONE",
         "range_lease_policy": "ENABLED", "reserve_fraction": REFERENCE["reserve_fraction"],
         "fault_schedule": "NONE", "difficulty": UNREACHABLE_DIFFICULTY,
         "notes": C06_NOTE},
    ]
    for r in rows:
        r.setdefault("difficulty", CONFIRMATORY_DIFFICULTY)
        r.update({"block_id": "C",
                  "confirmatory_or_exploratory": "CONFIRMATORY",
                  "hypothesis_ids": "IP-H1;IP-H2;IP-H9",
                  "heterogeneous_hash_rates": True,
                  "idle_power_ratio": "0.10",
                  "security_floor_policy": "DISABLED",
                  "adversarial_policy": "DISABLED",
                  "incentive_policy": "ENABLED"})
    return rows


def _blockD():
    """Matched adversarial pairs.  Every row shares D00's configuration except the attack."""
    rows = [
        {"scenario_id": "D00", "paired_control_id": "SELF",
         "adversarial_policy": "ENABLED_NO_BEHAVIOUR", "hypothesis_ids": "IP-H1;IP-H2;IP-H9",
         "notes": "honest matched control: the adversarial entity set is declared with NO "
                  "behaviour flags, so the same code path runs with no attack"},
        {"scenario_id": "D01", "paired_control_id": "D00",
         "adversarial_policy": "DELAYED_WAKE", "hypothesis_ids": "IP-H10a",
         "notes": "delayed wake: bounded extra wake latency on every real wake lifecycle"},
        {"scenario_id": "D02", "paired_control_id": "D00",
         "adversarial_policy": "SOLUTION_WITHHOLDER", "hypothesis_ids": "IP-H10b",
         "notes": "solution withholding: a valid solution is never released"},
        {"scenario_id": "D03", "paired_control_id": "D00",
         "adversarial_policy": "FALSE_EXHAUSTION_CLAIMER", "hypothesis_ids": "IP-H10c",
         "notes": "accepted false exhaustion: the audit never detects the claim"},
        # IP-H10d needs its OWN matched pair.  apply_progress_withholding under-reports
        # COMMITTED progress, so an intermediate committed frontier must exist, which requires
        # a batch boundary strictly inside a primary's range:
        #     nonce_domain_size / primary_count > batch_size
        # At the reference batch_size 50 that is 35.4 > 50, which is FALSE — the original
        # parameterisation was structurally incapable of producing an intermediate frontier.
        # BOTH arms therefore carry batch_size 25 (35.4 > 25).  The batch-50 D00 control is NOT
        # reused for this contrast; D04C is a dedicated control differing ONLY in the
        # progress-withholding behaviour.  No pilot effect size, direction, p-value or energy
        # result informed this choice.
        {"scenario_id": "D04C", "fault_schedule": "FAULT_SET_PROGRESS",
         "paired_control_id": "SELF",
         "adversarial_policy": "ENABLED_NO_BEHAVIOUR", "hypothesis_ids": "IP-H1;IP-H2;IP-H9",
         "batch_size_override": PROGRESS_PAIR_BATCH_SIZE,
         "notes": ("dedicated matched control for the IP-H10d progress-withholding contrast; "
                   "identical to D04 in every field except the progress-withholding behaviour")},
        {"scenario_id": "D04", "fault_schedule": "FAULT_SET_PROGRESS",
         "paired_control_id": "D04C",
         "adversarial_policy": "PROGRESS_WITHHOLDER", "hypothesis_ids": "IP-H10d",
         "batch_size_override": PROGRESS_PAIR_BATCH_SIZE,
         "notes": ("progress withholding: the accepted frontier must fall below the actual "
                   "frontier while the physical frontier never rewinds and duplicate reward is "
                   "prevented")},
    ]
    for r in rows:
        r.update({"block_id": "D",
                  "confirmatory_or_exploratory": "CONFIRMATORY",
                  "heterogeneous_hash_rates": True,
                  "idle_power_ratio": "0.10",
                  "security_floor_policy": "DISABLED",
                  "range_lease_policy": "ENABLED",
                  "incentive_policy": "ENABLED",
                  "reserve_fraction": REFERENCE["reserve_fraction"],
                  "difficulty": CONFIRMATORY_DIFFICULTY})
        # per-row schedule wins: the IP-H10d pair carries FAULT_SET_PROGRESS
        r.setdefault("fault_schedule", "FAULT_SET_DENSE")
    return rows


def confirmatory_rows() -> list:
    rows = _blockA() + _blockB() + _blockC() + _blockD()
    for r in rows:
        r.setdefault("reserve_fraction", REFERENCE["reserve_fraction"])
        r.setdefault("floor_min_hash_rate", "NA")
        r.setdefault("floor_min_miner_count", "NA")
        r.setdefault("batch_size_override", None)
    return rows


#: EXPLORATORY rows.  Never confirmatory, never in a multiplicity family, never a thesis claim.
def exploratory_rows() -> list:
    rows = [
        {"scenario_id": "X01", "block_id": "X", "study": "difficulty_control",
         "difficulty": 500,
         "notes": "EXPLORATORY difficulty-control study; excluded from the confirmatory matrix"},
        {"scenario_id": "X02", "block_id": "X", "study": "difficulty_control",
         "difficulty": 2000,
         "notes": "EXPLORATORY difficulty-control study; excluded from the confirmatory matrix"},
        {"scenario_id": "X03", "block_id": "X", "study": "reward_sensitivity",
         "difficulty": CONFIRMATORY_DIFFICULTY,
         "notes": "EXPLORATORY reward-rate sensitivity; incentive quantities are secondary "
                  "exploratory and are never a primary confirmatory endpoint"},
        {"scenario_id": "X04", "block_id": "X", "study": "identity_splitting",
         "difficulty": CONFIRMATORY_DIFFICULTY,
         "notes": "EXPLORATORY identity-splitting sensitivity; establishes no Sybil-resistance "
                  "property"},
    ]
    for r in rows:
        r.update({"confirmatory_or_exploratory": "EXPLORATORY",
                  "paired_control_id": "NONE", "hypothesis_ids": "NONE",
                  "batch_size_override": None,
                  "heterogeneous_hash_rates": True, "idle_power_ratio": "0.10",
                  "reserve_fraction": REFERENCE["reserve_fraction"]})
    return rows


# ------------------------------------------------------------------ config materialisation
# --------------------------------------------------------------- frozen fault schedule
# Calibrated by the Tier-1 and full-population pilots for EXECUTABILITY ONLY — never for effect
# size, and never after inspecting any energy or service outcome.
#
# WHY A DENSE SCHEDULE.  Path A requires an alive primary whose OWN range is already EXHAUSTED
# at the instant another primary's lease is revoked (simulator.py
# ``_eligible_reassignment_candidates``, categories 0/1).  At the confirmatory scale a round
# closes roughly 0.03 s after hashing begins because a block is found, while the fastest primary
# needs about 0.09 s to exhaust its ~35-nonce range — so in an ACCEPTED round no primary is ever
# free.  Only a no-block round (about 2.4 % of rounds, measured) produces the window, between
# the fastest primary's exhaustion and the slowest primary's.  A single injected fault therefore
# never reaches Path A at full scale: the pilot measured 0 Path-A reassignments from 41-77
# revocations across three seeds.  Injecting several SLOW primaries at several phases of every
# round in a fixed prefix gives many independent chances to land in that window; the pilot then
# measured a genuine Path A (wake_handles_created == 0) at full population.
#
# The schedule is FIXED here, before Stage 7.  How many injections happen to land is a measured
# outcome that varies by seed; the schedule itself does not.
FAULT_PHASES = (1.05, 1.15, 1.25, 1.35)

#: Dedicated phases for the IP-H10d matched pair.  Progress withholding additionally requires
#: the revoked owner to have COMMITTED at least one batch, i.e. to have hashed for at least
#: batch_size / hash_rate = 25/100 = 0.25 s past its wake completion at +1.0 s.  Phases earlier
#: than 1.25 can therefore never produce an intermediate committed frontier: the Stage-6
#: instrumentation measured committed == lease_start (done = 0) on every call at the earlier
#: phases.  These phases are applied IDENTICALLY to BOTH arms of the pair, so the contrast still
#: changes exactly one factor.  They were chosen from the batch/rate arithmetic and the measured
#: call-site state, never from an observed effect size, direction, p-value or energy result.
#: Phases spanning every adversarial rate's first batch boundary.  A rate-r miner commits its
#: first batch of 25 at wake_latency + 25/r seconds: r=400 -> +1.0625, r=300 -> +1.083,
#: r=200 -> +1.125, r=100 -> +1.25.  Revocations earlier than a miner's own boundary can only
#: ever measure done = 0.
#: Offsets added to EACH miner's OWN first-batch boundary.  The boundary is
#: wake_latency + batch_size / hash_rate, so it differs per rate (r=400 -> +1.0625,
#: r=300 -> +1.083, r=200 -> +1.125, r=100 -> +1.25).  A single shared phase list is wrong:
#: the EARLIEST landing injection revokes the miner, so a phase before that miner's own
#: boundary consumes its revocation while the committed frontier is still zero.  The Tier-1
#: pilot measured exactly that — 8-10 revocations and zero withholding.
PROGRESS_FAULT_OFFSETS = (0.01, 0.04, 0.07, 0.10, 0.13)
#: The IP-H10d schedule targets the ADVERSARIAL primaries, not the slow ones.  Progress
#: withholding is a behaviour of adversarial miners, so a failure injected into a miner with no
#: WITHHOLD profile can never exercise it: at Tier-1 scale the adversarial set is {M000, M001}
#: while the slow primaries are {M000, M004, M008}, so only ONE target was ever useful and the
#: behaviour fired on one pilot seed and not the other.
PROGRESS_FAULT_ROUND_PREFIX = 200
#: Unlike FAULT_SET_DENSE (one phase per miner), the IP-H10d schedule injects EVERY declared
#: slow primary at EVERY declared phase.  A single phase per miner lands on a live lease only
#: rarely — the Tier-1 pilot measured just 3 revocations across 153 rounds — so the behaviour
#: fired on one pilot seed and not the other.  The cross product multiplies the number of
#: independent chances without changing WHICH miners or WHICH window are used, and it is applied
#: identically to BOTH arms.
PROGRESS_FAULT_CROSS_PRODUCT = True
FAULT_PERIOD = 1.02          # measured nominal round length at full population (~1.00-1.05 s)
FAULT_ROUND_PREFIX = 2000    # faults are injected into rounds 1..2000 only
FAULT_SLOW_MINERS = 4        # at most four slow primaries per round


def slow_primary_ids(num_miners: int, reserve_fraction: float, limit: int) -> tuple:
    """The slowest primaries (hash_rate_for index % 4 == 0 -> base rate).

    A slow primary exhausts LAST, so it is still holding its lease while faster primaries have
    already exhausted — the only configuration in which a Path-A reassignee exists.
    """
    n_res = reserve_count(num_miners, reserve_fraction)
    ids = miner_ids(num_miners)
    primaries = ids[:len(ids) - n_res] if n_res else ids
    slow = [mid for i, mid in enumerate(primaries) if i % 4 == 0]
    return tuple(slow[:limit])


def _fault_schedule(name: str, num_miners: int, reserve_fraction: float,
                    horizon_T: float, period: float = FAULT_PERIOD) -> tuple:
    """Materialise a named fault schedule into ACCEPTED ``injected_lease_faults`` tuples."""
    if name == "NONE":
        return ()
    if name not in ("FAULT_SET_DENSE", "FAULT_SET_PROGRESS"):
        raise ValueError(f"unknown fault schedule: {name!r}")
    progress = (name == "FAULT_SET_PROGRESS")
    phases = None if progress else FAULT_PHASES
    if progress:
        # every adversarial miner that is also a PRIMARY (reserves hold no primary lease)
        n_res = reserve_count(num_miners, reserve_fraction)
        ids = miner_ids(num_miners)
        primaries = set(ids[:len(ids) - n_res] if n_res else ids)
        miners = tuple(m for m in adversarial_entity_miners(num_miners, ADVERSARIAL_FRACTION)
                       if m in primaries)
    else:
        miners = slow_primary_ids(num_miners, reserve_fraction, FAULT_SLOW_MINERS)
    if not miners:
        return ()
    prefix = PROGRESS_FAULT_ROUND_PREFIX if progress else FAULT_ROUND_PREFIX
    rounds = min(prefix, int(horizon_T / period) + 2)
    if progress:
        # per-miner phases: each miner is injected only AT OR AFTER its own batch boundary
        rate_of = {}
        for idx, mid in enumerate(sorted(m for m in miners)):
            i = int(mid[1:])
            rate_of[mid] = REFERENCE["base_hash_rate"] * (1.0 + (i % 4))
        batch = PROGRESS_PAIR_BATCH_SIZE
        wake = 1.0                       # accepted Stage2Config.wake_latency
        per_miner = {mid: tuple(round(wake + batch / rate_of[mid] + off, 6)
                                for off in PROGRESS_FAULT_OFFSETS) for mid in miners}
    out = []
    for k in range(1, rounds + 1):
        base = (k - 1) * period
        if progress:
            for mid in miners:
                for phase in per_miner[mid]:
                    out.append((k, mid, round(base + phase, 6), "MINER_FAILED"))
        else:
            for mid, phase in zip(miners, phases):
                out.append((k, mid, round(base + phase, 6), "MINER_FAILED"))
    return tuple(out)


def build_config(row: dict, master_seed: int, tier: dict,
                 seed_registry=None) -> Stage2Config:
    """Materialise ONE ``Stage2Config`` for ``row`` under ``master_seed`` at ``tier`` scale.

    The master seed reaches the engine ONLY through the two accepted fields; no engine seed
    mechanism is added.  Both arms of a paired contrast under the same master seed therefore
    receive identical ``template_seed`` and identical ``adversarial.deterministic_seed``.
    """
    from generate_seed_registry import child_seed        # local import: same package directory

    n = tier["num_miners"]
    horizon = tier["horizon_T"]
    hetero = bool(row["heterogeneous_hash_rates"])
    rho = IDLE_RATIOS[row["idle_power_ratio"]]
    powers = powers_for_ratio(rho)
    reserve_fraction = float(row["reserve_fraction"])

    kwargs = dict(
        num_miners=n,
        horizon_T=horizon,
        nonce_domain_size=tier["nonce_domain_size"],
        batch_size=int(row.get("batch_size_override") or tier["batch_size"]),
        difficulty=int(row["difficulty"]),
        base_hash_rate=REFERENCE["base_hash_rate"],
        heterogeneous_hash_rates=hetero,
        reserve_fraction=reserve_fraction,
        template_seed=child_seed(master_seed, "template"),
        **powers,
    )

    # --- Stage-3 security floor -------------------------------------------------
    fp = row["security_floor_policy"]
    if fp != "DISABLED":
        if fp == "ENABLED_UNATTAINABLE":
            minimum = 1.50 * total_population_hash_rate(n, REFERENCE["base_hash_rate"], hetero)
            count = None
        else:
            minimum = 0.80 * initial_active_primary_hash_rate(
                n, reserve_fraction, REFERENCE["base_hash_rate"], hetero)
            count = (primary_count(n, reserve_fraction)
                     if fp == "ENABLED_MIN_HASH_RATE_AND_MIN_COUNT" else None)
        kwargs["security_floor"] = floor_policy(minimum, count)
        kwargs["floor_unattainable_policy"] = "CONTINUE_DEGRADED"

    # --- Stage-4 range leases ---------------------------------------------------
    lp = row["range_lease_policy"]
    if lp == "ENABLED":
        kwargs["range_lease"] = lease_policy()
    elif lp == "ENABLED_NO_REASSIGN":
        kwargs["range_lease"] = lease_policy(reassignment_enabled=False)

    # --- Stage-5 incentive ------------------------------------------------------
    if row["incentive_policy"] == "ENABLED":
        kwargs["incentive"] = incentive_policy()

    # --- Stage-5 adversarial ----------------------------------------------------
    ap = row["adversarial_policy"]
    adv_seed = child_seed(master_seed, "adversarial")
    if ap != "DISABLED":
        common = dict(deterministic_seed=adv_seed, maximum_actions_per_round=1000)
        if ap == "ENABLED_NO_BEHAVIOUR":
            kwargs["adversarial"] = adversarial_policy((), n, actor_class="HONEST", **common)
        elif ap == "DELAYED_WAKE":
            kwargs["adversarial"] = adversarial_policy(
                ("DELAYED_WAKE",), n, delayed_wake_extra_latency=1.0, **common)
        elif ap == "SOLUTION_WITHHOLDER":
            kwargs["adversarial"] = adversarial_policy(
                ("SOLUTION_WITHHOLDER",), n,
                solution_release_policy="NEVER_RELEASE", **common)
        elif ap == "FALSE_EXHAUSTION_CLAIMER":
            kwargs["adversarial"] = adversarial_policy(
                ("FALSE_EXHAUSTION_CLAIMER",), n,
                audit_detection_probability=0.0, **common)
        elif ap == "PROGRESS_WITHHOLDER":
            kwargs["adversarial"] = adversarial_policy(
                ("PROGRESS_WITHHOLDER",), n,
                audit_detection_probability=0.0, progress_withholding_fraction=0.5, **common)
        else:
            raise ValueError(f"unknown adversarial policy: {ap!r}")

    # --- injected faults --------------------------------------------------------
    faults = _fault_schedule(row["fault_schedule"], n, reserve_fraction, horizon,
                             float(tier.get("nominal_round_period", FAULT_PERIOD)))
    if faults:
        kwargs["injected_lease_faults"] = faults

    return Stage2Config(**kwargs)


def assert_reference_matches_baseline() -> None:
    """Fail loudly if the ACCEPTED frozen baseline no longer matches the reference config."""
    from Models.PoCol.stage2.config import a1_continuous_control_kwh
    base = Stage2Config()
    bad = [f"{k}: baseline {getattr(base, k)!r} != reference {v!r}"
           for k, v in REFERENCE.items() if getattr(base, k) != v]
    if bad:
        raise SystemExit("STAGE_6_PREREGISTRATION_BLOCKED — reference configuration drift:\n  "
                         + "\n  ".join(bad))
    a1 = a1_continuous_control_kwh(base)
    if abs(a1 - A1_REFERENCE_KWH) > A1_TOLERANCE_KWH:
        raise SystemExit(f"STAGE_6_PREREGISTRATION_BLOCKED — A1 mismatch: computed {a1!r}, "
                         f"declared {A1_REFERENCE_KWH!r}, |error| > {A1_TOLERANCE_KWH}")


if __name__ == "__main__":
    assert_reference_matches_baseline()
    conf = confirmatory_rows()
    expl = exploratory_rows()
    print(f"reference configuration matches the frozen baseline; A1 within {A1_TOLERANCE_KWH} kWh")
    print(f"confirmatory rows : {len(conf)}")
    print(f"exploratory rows  : {len(expl)}")
    hetero = True
    print(f"H0 (heterogeneous): "
          f"{initial_active_primary_hash_rate(141, 0.2, 100.0, hetero)}")
    print(f"H0 (homogeneous)  : "
          f"{initial_active_primary_hash_rate(141, 0.2, 100.0, False)}")
    print(f"H_total           : {total_population_hash_rate(141, 100.0, hetero)}")
    print(f"primary count     : {primary_count(141, 0.2)}  reserve: {reserve_count(141, 0.2)}")
    print(f"adversarial set   : {len(adversarial_entity_miners(141))} miners "
          f"{adversarial_entity_miners(141)[:3]}..{adversarial_entity_miners(141)[-1:]}")
