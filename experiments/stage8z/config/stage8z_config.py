"""Stage 8Z — frozen experiment configuration.

Reuses the FROZEN Stage 8Y hardware registry, composition definitions, difficulty rule
and nonce-domain rule by **read-only import**, so the two experiment families are
provably matched rather than merely similar. Stage 8Y is never modified.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

# Read-only reuse of the frozen Stage 8Y scientific inputs.
from experiments.stage8y.config import difficulty as diffmod
from experiments.stage8y.config import hardware as hw

from experiments.stage8z.config import seeds as seedmod

EXPERIMENT = "Stage8Z"
REVISION = 1

# --------------------------------------------------------------------------
# Policies (nested hierarchy, one mechanism per level)
# --------------------------------------------------------------------------
Z0_POW = "Z0_POW"
Z1_8Y_BASELINE = "Z1_8Y_BASELINE"
Z2_FLOOR = "Z2_FLOOR"
Z3_REASSIGN = "Z3_REASSIGN"
Z4_RESERVE = "Z4_RESERVE"
Z5_FAIR = "Z5_FAIR"

PRIMARY_POLICIES: Tuple[str, ...] = (Z0_POW, Z1_8Y_BASELINE, Z2_FLOOR,
                                     Z3_REASSIGN, Z4_RESERVE, Z5_FAIR)
POCOL_POLICIES: Tuple[str, ...] = (Z1_8Y_BASELINE, Z2_FLOOR, Z3_REASSIGN,
                                   Z4_RESERVE, Z5_FAIR)

POLICY_LABELS = {
    Z0_POW: "Z0 Traditional PoW (principal comparator)",
    Z1_8Y_BASELINE: "Z1 Stage-8Y energy-aware baseline (r_H=0.60, no floor)",
    Z2_FLOOR: "Z2 Hash-floor energy-aware",
    Z3_REASSIGN: "Z3 Hash-floor + dynamic work reassignment",
    Z4_RESERVE: "Z4 Hash-floor + reassignment + adaptive reserve",
    Z5_FAIR: "Z5 Fair rotating adaptive PoCol",
}
POLICY_ADDS = {
    Z0_POW: "-", Z1_8Y_BASELINE: "energy-aware selection at a fixed r_H",
    Z2_FLOOR: "minimum active hash-capacity floor",
    Z3_REASSIGN: "dynamic residual-range reassignment",
    Z4_RESERVE: "predictive reserve activation + hash-capacity step-up",
    Z5_FAIR: "rolling-window participation floor (fair rotation)",
}

# --------------------------------------------------------------------------
# Frozen scientific parameters
# --------------------------------------------------------------------------
PRIMARY_NETWORK_SIZES: Tuple[int, ...] = (100, 300, 500)
SECONDARY_NETWORK_SIZES: Tuple[int, ...] = (200, 400)
ALL_NETWORK_SIZES: Tuple[int, ...] = (100, 200, 300, 400, 500)

PRIMARY_COMPOSITIONS: Tuple[str, ...] = ("H0", "H2", "H4")
ALL_COMPOSITIONS: Tuple[str, ...] = ("H0", "H1", "H2", "H3", "H4")

HORIZON_S: float = 10_000.0
LONG_HORIZON_S: float = 100_000.0
TARGET_INTERVAL_S: float = 600.0
EPOCH_SWEEP_S: float = 600.0
BLOCK_PROP_DELAY_MEAN_S: float = 0.42

#: Full exploratory hash-floor sweep (brief section 27).
HASH_FLOORS_ALL: Tuple[float, ...] = (0.70, 0.80, 0.85, 0.90, 0.95, 1.00)
#: Confirmatory floors, DECLARED here, not selected from results (brief section 29).
HASH_FLOORS_CONFIRMATORY: Tuple[float, ...] = (0.85, 0.90, 0.95, 1.00)
#: The single floor used by Z3/Z4/Z5 in the confirmatory matrix.
CONF_FLOOR: float = 0.90

#: Stage 8Y P3's operating point, reproduced by Z1 without touching Stage 8Y.
Z1_TARGET_HASH_FRACTION: float = 0.60

# Reassignment strategies
R0_NONE, R1_FASTEST, R2_EFFICIENCY, R3_MARGINAL = "R0_NONE", "R1_FASTEST", \
    "R2_EFFICIENCY", "R3_MARGINAL"
REASSIGN_RULES: Tuple[str, ...] = (R0_NONE, R1_FASTEST, R2_EFFICIENCY, R3_MARGINAL)
#: a-priori preferred rule; confirmed (not chosen) by the exploratory phase
CONF_REASSIGN_RULE: str = R3_MARGINAL

# Adaptive reserve
RESERVE_THETAS: Tuple[float, ...] = (0.50, 0.70, 0.80, 0.90, 0.95)
CONF_RESERVE_THETA: float = 0.80
RESERVE_DEADLINE_S: float = 600.0
RESERVE_STEPS: Tuple[float, ...] = (0.90, 0.95, 1.00)
RESERVE_CHECK_S: float = 30.0

# Fairness
F0_NONE, F1_SOFT, F2_FLOOR, F3_CLASS = "F0_NONE", "F1_SOFT", "F2_FLOOR", "F3_CLASS"
FAIRNESS_SCHEMES: Tuple[str, ...] = (F0_NONE, F1_SOFT, F2_FLOOR, F3_CLASS)
FAIRNESS_PMIN: Tuple[float, ...] = (0.05, 0.10, 0.20)
CONF_FAIRNESS_SCHEME: str = F2_FLOOR
CONF_FAIRNESS_PMIN: float = 0.10
FAIRNESS_WINDOW_EPOCHS: int = 10

# Wake / low power
CONF_WAKE_S: float = 10.0
WAKE_S_ALL: Tuple[float, ...] = (0.0, 1.0, 5.0, 10.0, 30.0)
WAKE_POWER_RATIO: float = 1.0

ALPHA_CASES: Dict[str, float] = {"alpha_0": 0.00, "alpha_005": 0.05,
                                 "alpha_010": 0.10, "alpha_025": 0.25,
                                 "alpha_050": 0.50}
ALPHA_NOTE = ("These values are model-based sensitivity assumptions and are not "
              "manufacturer-certified Antminer low-power operating modes. alpha = 0 "
              "is an idealized theoretical lower bound, not a physically validated "
              "state. Primary interpretation uses alpha = 0.10.")
IDEALIZED_ALPHA_LABELS = ("alpha_0",)
PRIMARY_ALPHA = "alpha_010"

DOMAIN_SEMANTICS = diffmod.DOMAIN_INSTALLED

# --------------------------------------------------------------------------
# Preregistered acceptance criteria (brief section 45)
# --------------------------------------------------------------------------
ACCEPTANCE = {
    "outcome_A": {"saving_gt": 0.50, "retention_ge": 0.95, "latency_le": 1.10,
                  "non_idealized_alpha": True,
                  "text": "Strong success: Saving>50% AND Retention>=95% AND "
                          "LatencyRatio<=1.10 under a non-idealized alpha."},
    "outcome_B": {"saving_gt": 0.50, "retention_ge": 0.90,
                  "text": "Moderate success: Saving>50% AND Retention>=90%."},
    "outcome_C": {"saving_ge": 0.30, "retention_ge": 0.95, "latency_le": 1.10,
                  "text": "High-quality practical improvement: Saving>=30% AND "
                          "Retention>=95% AND LatencyRatio<=1.10."},
    "outcome_D": {"saving_ge": 0.40, "retention_ge": 0.90,
                  "text": "Strong trade-off improvement: Saving>=40% AND "
                          "Retention>=90%."},
    "outcome_E": {"text": "Stage-8Y-like trade-off: energy saving improves but "
                          "retention remains <90%."},
    "outcome_F": {"text": "No meaningful frontier improvement: Stage 8Z does not "
                          "materially dominate or extend the Stage 8Y frontier."},
}

#: Analytic ceiling recorded BEFORE execution (see STAGE_8Z_SCIENTIFIC_DESIGN.md §2).
#: Computed from the frozen Stage 8Y registry, not from any simulation.
PREREGISTERED_CEILING_NOTE = (
    "Because block rate = H_active*q under a matched target, BlockRetention tracks "
    "the realized mean active hash fraction, so the maximum saving at a realized "
    "floor F_H is 1 - r_P(F_H) at alpha=0. At N=300 the ceilings are: F_H=0.95 -> "
    "4.7%/7.5%/6.5% and F_H=0.90 -> 10.0%/14.9%/13.0% for H0/H2/H4. Outcomes A, B, "
    "C and D are therefore analytically unreachable with this hardware registry, and "
    "that was recorded before execution.")

# --------------------------------------------------------------------------
# Paths
# --------------------------------------------------------------------------
HERE = os.path.dirname(os.path.abspath(__file__))
STAGE_DIR = os.path.dirname(HERE)
REPO_ROOT = os.path.abspath(os.path.join(STAGE_DIR, "..", ".."))
OUT_DIR = os.path.join(STAGE_DIR, "outputs")
FIG_DIR = os.path.join(STAGE_DIR, "figures")
REPORT_DIR = os.path.join(STAGE_DIR, "reports")
MANIFEST_DIR = os.path.join(STAGE_DIR, "manifests")
SEEDS_JSON = os.path.join(HERE, "stage8z_seeds.json")

POST_FREEZE_AMENDMENTS: List[Dict] = []


def ensure_dirs() -> None:
    for d in (OUT_DIR, FIG_DIR, REPORT_DIR, MANIFEST_DIR):
        os.makedirs(d, exist_ok=True)


# --------------------------------------------------------------------------
@dataclass(frozen=True)
class RunConfig:
    policy: str
    composition: str
    n_miners: int
    seed: int
    seed_index: int
    horizon_s: float = HORIZON_S
    target_interval_s: float = TARGET_INTERVAL_S
    epoch_sweep_s: float = EPOCH_SWEEP_S
    prop_delay_mean_s: float = BLOCK_PROP_DELAY_MEAN_S
    hash_floor: Optional[float] = None
    reassign_rule: str = R0_NONE
    reserve_theta: float = CONF_RESERVE_THETA
    reserve_steps: Tuple[float, ...] = RESERVE_STEPS
    fairness_scheme: str = F0_NONE
    fairness_pmin: float = 0.0
    wake_s: float = CONF_WAKE_S
    phase: str = "confirmatory"   # pilot | exploratory | confirmatory | secondary | longhorizon
    tag: str = ""

    @property
    def run_id(self) -> str:
        pre = {"pilot": "8ZP", "exploratory": "8ZX", "confirmatory": "8Z",
               "secondary": "8ZS", "longhorizon": "8ZL"}[self.phase]
        base = (f"{pre}_{self.composition}_N{self.n_miners}_{self.policy}"
                f"_seed{self.seed_index:03d}")
        return f"{base}_{self.tag}" if self.tag else base

    @property
    def population(self) -> hw.Population:
        return hw.build_population(self.composition, self.n_miners)

    @property
    def spec(self) -> diffmod.DifficultySpec:
        return diffmod.derive(self.composition, self.n_miners,
                              self.target_interval_s, self.epoch_sweep_s,
                              DOMAIN_SEMANTICS, self.population)


def policy_kwargs(policy: str, floor: float = None, **over) -> Dict:
    """Confirmatory parameterisation of each policy level."""
    f = CONF_FLOOR if floor is None else floor
    base: Dict = {}
    if policy == Z1_8Y_BASELINE:
        base = dict(hash_floor=Z1_TARGET_HASH_FRACTION, reassign_rule=R0_NONE)
    elif policy == Z2_FLOOR:
        base = dict(hash_floor=f, reassign_rule=R0_NONE)
    elif policy == Z3_REASSIGN:
        base = dict(hash_floor=f, reassign_rule=CONF_REASSIGN_RULE)
    elif policy == Z4_RESERVE:
        base = dict(hash_floor=f, reassign_rule=CONF_REASSIGN_RULE,
                    reserve_theta=CONF_RESERVE_THETA, reserve_steps=RESERVE_STEPS)
    elif policy == Z5_FAIR:
        base = dict(hash_floor=f, reassign_rule=CONF_REASSIGN_RULE,
                    reserve_theta=CONF_RESERVE_THETA, reserve_steps=RESERVE_STEPS,
                    fairness_scheme=CONF_FAIRNESS_SCHEME,
                    fairness_pmin=CONF_FAIRNESS_PMIN)
    base.update(over)
    return base


def uses_reserve(policy: str) -> bool:
    return policy in (Z4_RESERVE, Z5_FAIR)


# --------------------------------------------------------------------------
# Matrices
# --------------------------------------------------------------------------
def pilot_matrix() -> List[RunConfig]:
    runs = []
    for comp in PRIMARY_COMPOSITIONS:
        for n in (100, 300, 500):
            for k, seed in enumerate(seedmod.pilot_seeds(), start=1):
                for pol in PRIMARY_POLICIES:
                    for fl in ((0.85, 0.95) if pol in (Z2_FLOOR, Z3_REASSIGN) else (None,)):
                        kw = {} if pol == Z0_POW else policy_kwargs(pol, fl)
                        tag = f"F{int((fl or CONF_FLOOR)*100)}" if fl else ""
                        runs.append(RunConfig(policy=pol, composition=comp, n_miners=n,
                                              seed=seed, seed_index=k, phase="pilot",
                                              tag=tag, **kw))
    return runs


def exploratory_matrix() -> List[RunConfig]:
    """Policy/parameter tuning on DEDICATED seeds. Never confirmatory evidence."""
    runs = []
    seeds = seedmod.exploratory_seeds()
    for comp in ("H2", "H4"):
        n = 300
        for k, seed in enumerate(seeds, start=1):
            runs.append(RunConfig(policy=Z0_POW, composition=comp, n_miners=n,
                                  seed=seed, seed_index=k, phase="exploratory",
                                  tag="base"))
            # E-A: full hash-floor sweep, Z2 and Z3
            for fl in HASH_FLOORS_ALL:
                for pol in (Z2_FLOOR, Z3_REASSIGN):
                    runs.append(RunConfig(policy=pol, composition=comp, n_miners=n,
                                          seed=seed, seed_index=k, phase="exploratory",
                                          tag=f"F{int(fl*100)}",
                                          **policy_kwargs(pol, fl)))
            # E-B: reassignment rule comparison at the confirmatory floor
            for rule in REASSIGN_RULES:
                runs.append(RunConfig(policy=Z3_REASSIGN, composition=comp, n_miners=n,
                                      seed=seed, seed_index=k, phase="exploratory",
                                      tag=f"rule_{rule}",
                                      **policy_kwargs(Z3_REASSIGN, CONF_FLOOR,
                                                      reassign_rule=rule)))
            # E-C: reserve threshold sweep
            for th in RESERVE_THETAS:
                runs.append(RunConfig(policy=Z4_RESERVE, composition=comp, n_miners=n,
                                      seed=seed, seed_index=k, phase="exploratory",
                                      tag=f"theta{int(th*100)}",
                                      **policy_kwargs(Z4_RESERVE, CONF_FLOOR,
                                                      reserve_theta=th)))
            # E-D: fairness scheme / p_min sweep
            for sch in FAIRNESS_SCHEMES:
                for pmin in (FAIRNESS_PMIN if sch in (F2_FLOOR, F3_CLASS) else (0.0,)):
                    runs.append(RunConfig(
                        policy=Z5_FAIR, composition=comp, n_miners=n, seed=seed,
                        seed_index=k, phase="exploratory",
                        tag=f"{sch}_p{int(pmin*100)}",
                        **policy_kwargs(Z5_FAIR, CONF_FLOOR, fairness_scheme=sch,
                                        fairness_pmin=pmin)))
    return runs


def confirmatory_matrix() -> List[RunConfig]:
    """Fresh seeds, never used for tuning."""
    runs = []
    seeds = seedmod.confirmatory_seeds()
    for comp in PRIMARY_COMPOSITIONS:
        for n in PRIMARY_NETWORK_SIZES:
            for k, seed in enumerate(seeds, start=1):
                for pol in PRIMARY_POLICIES:
                    kw = {} if pol == Z0_POW else policy_kwargs(pol)
                    runs.append(RunConfig(policy=pol, composition=comp, n_miners=n,
                                          seed=seed, seed_index=k,
                                          phase="confirmatory", **kw))
                # declared confirmatory floor sub-matrix for Z2 and Z3
                for fl in HASH_FLOORS_CONFIRMATORY:
                    if fl == CONF_FLOOR:
                        continue
                    for pol in (Z2_FLOOR, Z3_REASSIGN):
                        runs.append(RunConfig(
                            policy=pol, composition=comp, n_miners=n, seed=seed,
                            seed_index=k, phase="confirmatory",
                            tag=f"F{int(fl*100)}", **policy_kwargs(pol, fl)))
    return runs


def secondary_matrix() -> List[RunConfig]:
    runs = []
    seeds = seedmod.exploratory_seeds()
    ref_c, ref_n = "H2", 300
    # S-A: wake-delay sensitivity
    for tw in WAKE_S_ALL:
        for k, seed in enumerate(seeds, start=1):
            runs.append(RunConfig(policy=Z4_RESERVE, composition=ref_c, n_miners=ref_n,
                                  seed=seed, seed_index=k, phase="secondary",
                                  tag=f"wake{int(tw)}",
                                  **policy_kwargs(Z4_RESERVE, wake_s=tw)))
    # S-B: N scaling at the secondary sizes
    for comp in PRIMARY_COMPOSITIONS:
        for n in SECONDARY_NETWORK_SIZES:
            for k, seed in enumerate(seeds, start=1):
                for pol in (Z0_POW, Z2_FLOOR, Z3_REASSIGN, Z4_RESERVE):
                    kw = {} if pol == Z0_POW else policy_kwargs(pol)
                    runs.append(RunConfig(policy=pol, composition=comp, n_miners=n,
                                          seed=seed, seed_index=k, phase="secondary",
                                          tag="scale", **kw))
    # S-C: heterogeneity sensitivity at H1 and H3
    for comp in ("H1", "H3"):
        for k, seed in enumerate(seeds, start=1):
            for pol in (Z0_POW, Z2_FLOOR, Z3_REASSIGN, Z4_RESERVE, Z5_FAIR):
                kw = {} if pol == Z0_POW else policy_kwargs(pol)
                runs.append(RunConfig(policy=pol, composition=comp, n_miners=300,
                                      seed=seed, seed_index=k, phase="secondary",
                                      tag="het", **kw))
    return runs


def longhorizon_matrix() -> List[RunConfig]:
    """Predefined important configurations at T = 100 000 s, selected before results."""
    runs = []
    for comp in PRIMARY_COMPOSITIONS:
        for k, seed in enumerate(seedmod.longhorizon_seeds(), start=1):
            for pol in (Z0_POW, Z1_8Y_BASELINE, Z3_REASSIGN, Z4_RESERVE, Z5_FAIR):
                kw = {} if pol == Z0_POW else policy_kwargs(pol)
                runs.append(RunConfig(policy=pol, composition=comp, n_miners=300,
                                      seed=seed, seed_index=k,
                                      horizon_s=LONG_HORIZON_S, phase="longhorizon",
                                      **kw))
    return runs


# --------------------------------------------------------------------------
def frozen_parameters() -> Dict:
    return {
        "experiment": EXPERIMENT, "revision": REVISION,
        "hardware_registry": hw.registry_raw(),
        "hardware_source": "read-only reuse of the frozen Stage 8Y registry",
        "compositions": {k: hw.COMPOSITIONS[k] for k in ALL_COMPOSITIONS},
        "primary_compositions": list(PRIMARY_COMPOSITIONS),
        "primary_network_sizes": list(PRIMARY_NETWORK_SIZES),
        "secondary_network_sizes": list(SECONDARY_NETWORK_SIZES),
        "horizon_s": HORIZON_S, "long_horizon_s": LONG_HORIZON_S,
        "target_interval_s": TARGET_INTERVAL_S, "epoch_sweep_s": EPOCH_SWEEP_S,
        "prop_delay_mean_s": BLOCK_PROP_DELAY_MEAN_S,
        "policies": {k: POLICY_LABELS[k] for k in PRIMARY_POLICIES},
        "policy_adds": POLICY_ADDS,
        "hash_floors_all": list(HASH_FLOORS_ALL),
        "hash_floors_confirmatory": list(HASH_FLOORS_CONFIRMATORY),
        "conf_floor": CONF_FLOOR,
        "hash_floor_semantics": "operational floor: excursions permitted only during "
                                "waking, template transition and post-acceptance "
                                "cancellation; every excursion is measured and "
                                "reported as HashFloorDeficit.",
        "z1_target_hash_fraction": Z1_TARGET_HASH_FRACTION,
        "reassign_rules": list(REASSIGN_RULES), "conf_reassign_rule": CONF_REASSIGN_RULE,
        "reserve_thetas": list(RESERVE_THETAS), "conf_reserve_theta": CONF_RESERVE_THETA,
        "reserve_steps": list(RESERVE_STEPS),
        "reserve_deadline_s": RESERVE_DEADLINE_S, "reserve_check_s": RESERVE_CHECK_S,
        "reserve_rule": "activate when P_success(deadline) = 1-exp(-H_active*q*dt) < theta",
        "fairness_schemes": list(FAIRNESS_SCHEMES),
        "conf_fairness_scheme": CONF_FAIRNESS_SCHEME,
        "conf_fairness_pmin": CONF_FAIRNESS_PMIN,
        "fairness_window_epochs": FAIRNESS_WINDOW_EPOCHS,
        "alpha_cases": ALPHA_CASES, "alpha_note": ALPHA_NOTE,
        "primary_alpha": PRIMARY_ALPHA,
        "wake_s_all": list(WAKE_S_ALL), "conf_wake_s": CONF_WAKE_S,
        "wake_power_ratio": WAKE_POWER_RATIO,
        "difficulty_rule": "D = H_N * I_target / 2**32 from FULL installed hardware; "
                           "one per (N, composition); identical for Z0-Z5; never "
                           "recalibrated for reduced active sets, reserve activation, "
                           "reassignment or selection.",
        "nonce_domain_rule": "S = H_N * tau from installed capacity; one disjoint slot "
                             "per installed miner; reassignment changes ownership only "
                             "and never changes S, the target or the difficulty.",
        "domain_semantics": DOMAIN_SEMANTICS,
        "acceptance": ACCEPTANCE,
        "preregistered_ceiling_note": PREREGISTERED_CEILING_NOTE,
        "seed_namespace": seedmod.NAMESPACE,
        "exploratory_selection_rules": {
            "reassign_rule": "highest mean realized H_active at fixed floor; ties to R3",
            "reserve_theta": "minimise HashFloorDeficit subject to mean active power "
                             "fraction not rising by more than 2 pp",
            "fairness": "largest p_min whose exploratory energy penalty <= 3 pp",
            "floors": "declared in advance, not selected from data",
        },
        "difficulty_table": diffmod.difficulty_table(
            list(ALL_COMPOSITIONS), list(ALL_NETWORK_SIZES),
            TARGET_INTERVAL_S, EPOCH_SWEEP_S),
    }


def config_hash() -> str:
    return hashlib.sha256(json.dumps(frozen_parameters(), sort_keys=True,
                                     separators=(",", ":")).encode()).hexdigest()
