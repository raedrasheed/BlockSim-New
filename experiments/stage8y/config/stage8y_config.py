"""Stage 8Y — frozen experiment configuration.

Every scientific parameter of Stage 8Y lives here. After the freeze nothing in this
module may change without rerunning the Pilot from scratch, documenting the change,
incrementing ``REVISION`` and refreezing (brief section 16).

This module never imports ``InputsConfig`` and never writes outside
``experiments/stage8y/``.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from experiments.stage8y.config import difficulty as diffmod
from experiments.stage8y.config import hardware as hw
from experiments.stage8y.config import policies as pol
from experiments.stage8y.config import seeds as seedmod

EXPERIMENT = "Stage8Y"
REVISION = 1

# --------------------------------------------------------------------------
# Protocols
# --------------------------------------------------------------------------
POW = "POW"                    # traditional competitive PoW - PRINCIPAL comparator
POW_CT = "POW_CT"              # common-template independent PoW - SECONDARY diagnostic
P0_ALL = "P0_ALL"              # PoCol, every miner active (within-PoCol control)
P1_EQUAL = "P1_EQUAL"          # PoCol, equal nonce ranges
P2_HASHPROP = "P2_HASHPROP"    # PoCol, hash-proportional ranges
P3_ENERGY = "P3_ENERGY"        # PoCol, energy-aware active set
P4_RESERVE = "P4_RESERVE"      # PoCol, adaptive reserve activation

PRIMARY_PROTOCOLS: Tuple[str, ...] = (POW, P0_ALL, P3_ENERGY, P4_RESERVE)

PROTOCOL_LABELS = {
    POW: "Traditional competitive PoW (distinct per-miner templates) - principal comparator",
    POW_CT: "Common-Template Independent PoW - SECONDARY mechanism diagnostic only",
    P0_ALL: "PoCol-All (all miners active) - within-PoCol control",
    P1_EQUAL: "PoCol equal nonce ranges",
    P2_HASHPROP: "PoCol hash-proportional nonce ranges",
    P3_ENERGY: "PoCol energy-aware active set",
    P4_RESERVE: "PoCol adaptive reserve activation",
}
POCOL_PROTOCOLS = (P0_ALL, P1_EQUAL, P2_HASHPROP, P3_ENERGY, P4_RESERVE)

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
BLOCK_PROP_DELAY_MEAN_S: float = 0.42          # retained from Stage 8X, unchanged

#: Confirmatory policy parameters. Declared before execution; the sweeps around
#: them are secondary/exploratory and are never reported as confirmatory.
CONF_SELECTION_RULE: str = pol.S4_OPTIMIZE
CONF_TARGET_HASH_FRACTION: float = 0.60        # midpoint of the pre-declared range
CONF_RESERVE_SCHEDULE: Tuple[float, ...] = (0.60, 0.75, 0.90, 1.00)
CONF_TRIGGER_S: float = 300.0
CONF_WAKE_S: float = 10.0
CONF_ALLOCATION: str = pol.ALLOC_HASH
DOMAIN_SEMANTICS: str = diffmod.DOMAIN_INSTALLED

#: Wake transition draws FULL active power (the conservative choice, unfavourable
#: to PoCol). No manufacturer wake-power curve exists for any registry device.
WAKE_POWER_RATIO: float = 1.0

#: alpha = P_low / P_active. Model assumptions, NOT Bitmain operating modes.
ALPHA_CASES: Dict[str, float] = {
    "alpha_0": 0.00,
    "alpha_005": 0.05,
    "alpha_010": 0.10,
    "alpha_025": 0.25,
    "alpha_050": 0.50,
}
ALPHA_NOTE = ("These values are model-based sensitivity assumptions and are not "
              "manufacturer-certified Antminer low-power operating modes. alpha = 0 "
              "is an idealized theoretical lower bound, not a physically validated "
              "state.")
IDEALIZED_ALPHA_LABELS = ("alpha_0",)

#: The same alpha is applied to LOW_POWER and STANDBY because no manufacturer data
#: distinguishes them. Residence in the two states is nevertheless tracked and
#: reported separately.
STANDBY_EQUALS_LOW = True

N_PRIMARY_SEEDS = seedmod.N_PRIMARY_SEEDS
N_PILOT_SEEDS = seedmod.N_PILOT_SEEDS

# --------------------------------------------------------------------------
# Preregistered acceptance criteria (brief section 26)
# --------------------------------------------------------------------------
ACCEPTANCE = {
    "saving_threshold": 0.50,
    "retention_strong": 0.95,
    "retention_moderate": 0.90,
    "latency_ratio_max": 1.10,
    "outcome_A": "Saving > 50% AND BlockRetention >= 95% AND LatencyRatio <= 1.10 "
                 "under at least one confirmatory NON-IDEALIZED alpha (alpha > 0).",
    "outcome_B": "Saving > 50% AND BlockRetention >= 90% under at least one "
                 "confirmatory configuration.",
    "outcome_C": "Saving > 50% but BlockRetention < 90%.",
    "outcome_D": "No confirmatory configuration achieves Saving > 50%.",
    "outcome_E": "Saving > 50% only under idealized assumptions (alpha = 0 or "
                 "t_wake = 0) and not under conservative ones.",
}

# --------------------------------------------------------------------------
# Secondary sweep grids (declared before execution)
# --------------------------------------------------------------------------
SEC_SELECTION_RULES = pol.SELECTION_RULES
SEC_TARGET_HASH_FRACTIONS: Tuple[float, ...] = (0.40, 0.50, 0.60, 0.70, 0.80)
SEC_COUNT_FRACTIONS: Tuple[float, ...] = (1.00, 0.80, 0.60, 0.50, 0.40, 0.30)
SEC_WAKE_S: Tuple[float, ...] = (0.0, 1.0, 5.0, 10.0, 30.0)
SEC_TRIGGER_S: Tuple[float, ...] = (150.0, 300.0, 450.0, 600.0)
SEC_RESERVE_INITIAL: Tuple[float, ...] = (0.40, 0.50, 0.60, 0.70, 0.80)
SEC_REF_N: int = 300
SEC_REF_COMPOSITION: str = "H2"

LONG_HORIZON_N: int = 300
LONG_HORIZON_COMPOSITIONS: Tuple[str, ...] = ("H0", "H2", "H4")
LONG_HORIZON_PROTOCOLS: Tuple[str, ...] = PRIMARY_PROTOCOLS

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
SEEDS_JSON = os.path.join(HERE, "stage8y_seeds.json")

POST_FREEZE_AMENDMENTS: List[Dict] = [
    {
        "id": "A1",
        "date": "2026-08-14",
        "file": "experiments/stage8y/config/stage8y_config.py::secondary_matrix",
        "defect": (
            "The SECONDARY matrix contained no traditional-PoW baseline at the "
            "secondary reference cell (H2, N=300), so every secondary sensitivity "
            "run there had no matched control and all of its paired rows were "
            "silently dropped from the secondary energy table."
        ),
        "fix": (
            "Added 30 matched POW runs at (H2, N=300) on the secondary seeds "
            "(tag 'base'). Existing secondary runs were untouched and were not "
            "re-executed; the 30 new control runs were appended."
        ),
        "scope": (
            "Adds a control to a declared SECONDARY/exploratory analysis. It changes "
            "no scientific parameter, no confirmatory run, no primary result, and "
            "config_hash is unchanged (frozen_parameters records the secondary grid "
            "values, not the enumerated run list). Detected by an empty secondary "
            "sensitivity table during analysis, before any secondary result was read."
        ),
    },
]


def ensure_dirs() -> None:
    for d in (OUT_DIR, FIG_DIR, REPORT_DIR, MANIFEST_DIR):
        os.makedirs(d, exist_ok=True)


# --------------------------------------------------------------------------
# Per-run configuration
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class RunConfig:
    protocol: str
    composition: str
    n_miners: int
    seed: int
    seed_index: int
    horizon_s: float = HORIZON_S
    target_interval_s: float = TARGET_INTERVAL_S
    epoch_sweep_s: float = EPOCH_SWEEP_S
    prop_delay_mean_s: float = BLOCK_PROP_DELAY_MEAN_S
    allocation: str = CONF_ALLOCATION
    selection_rule: str = CONF_SELECTION_RULE
    target_hash_fraction: Optional[float] = None
    target_count_fraction: Optional[float] = None
    reserve_schedule: Optional[Tuple[float, ...]] = None
    trigger_s: float = CONF_TRIGGER_S
    wake_s: float = CONF_WAKE_S
    domain_semantics: str = DOMAIN_SEMANTICS
    phase: str = "primary"        # primary | pilot | secondary | longhorizon
    tag: str = ""

    @property
    def run_id(self) -> str:
        prefix = {"primary": "8Y", "pilot": "8YP", "secondary": "8YS",
                  "longhorizon": "8YL"}[self.phase]
        base = (f"{prefix}_{self.composition}_N{self.n_miners}_{self.protocol}"
                f"_seed{self.seed_index:03d}")
        return f"{base}_{self.tag}" if self.tag else base

    @property
    def population(self) -> hw.Population:
        return hw.build_population(self.composition, self.n_miners)

    @property
    def spec(self) -> diffmod.DifficultySpec:
        return diffmod.derive(self.composition, self.n_miners,
                              self.target_interval_s, self.epoch_sweep_s,
                              self.domain_semantics, self.population)


def _conf_pocol(protocol: str, **kw) -> Dict:
    """Confirmatory parameterisation for each PoCol policy."""
    if protocol == P0_ALL:
        return dict(allocation=pol.ALLOC_HASH, target_hash_fraction=1.0, **kw)
    if protocol == P1_EQUAL:
        return dict(allocation=pol.ALLOC_EQUAL, target_hash_fraction=1.0, **kw)
    if protocol == P2_HASHPROP:
        return dict(allocation=pol.ALLOC_HASH, target_hash_fraction=1.0, **kw)
    if protocol == P3_ENERGY:
        return dict(allocation=pol.ALLOC_HASH,
                    selection_rule=CONF_SELECTION_RULE,
                    target_hash_fraction=CONF_TARGET_HASH_FRACTION, **kw)
    if protocol == P4_RESERVE:
        return dict(allocation=pol.ALLOC_HASH,
                    selection_rule=CONF_SELECTION_RULE,
                    reserve_schedule=CONF_RESERVE_SCHEDULE,
                    trigger_s=CONF_TRIGGER_S, wake_s=CONF_WAKE_S, **kw)
    return dict(**kw)


# --------------------------------------------------------------------------
# Run matrices
# --------------------------------------------------------------------------
def primary_matrix() -> List[RunConfig]:
    """3 N x 3 compositions x 4 protocols x 30 paired seeds = 1080 physical runs."""
    runs: List[RunConfig] = []
    for comp in PRIMARY_COMPOSITIONS:
        for n in PRIMARY_NETWORK_SIZES:
            for k, seed in enumerate(seedmod.primary_seeds(), start=1):
                for proto in PRIMARY_PROTOCOLS:
                    kw = {} if proto == POW else _conf_pocol(proto)
                    runs.append(RunConfig(protocol=proto, composition=comp,
                                          n_miners=n, seed=seed, seed_index=k,
                                          phase="primary", **kw))
    return runs


def pilot_matrix() -> List[RunConfig]:
    runs: List[RunConfig] = []
    protos = (POW, POW_CT, P0_ALL, P1_EQUAL, P2_HASHPROP, P3_ENERGY, P4_RESERVE)
    for comp in ("H0", "H2", "H4"):
        for n in (100, 300, 500):
            for k, seed in enumerate(seedmod.pilot_seeds(), start=1):
                for proto in protos:
                    kw = {} if proto in (POW, POW_CT) else _conf_pocol(proto)
                    runs.append(RunConfig(protocol=proto, composition=comp,
                                          n_miners=n, seed=seed, seed_index=k,
                                          phase="pilot", **kw))
    return runs


def secondary_matrix() -> List[RunConfig]:
    """Declared exploratory / sensitivity runs. Never reported as confirmatory."""
    runs: List[RunConfig] = []
    sec = seedmod.secondary_seeds()
    ref_n, ref_c = SEC_REF_N, SEC_REF_COMPOSITION

    # S-A: allocation-policy comparison P1 vs P2 across all N and compositions
    for comp in ALL_COMPOSITIONS:
        for n in PRIMARY_NETWORK_SIZES:
            for k, seed in enumerate(sec, start=1):
                for proto in (P1_EQUAL, P2_HASHPROP):
                    runs.append(RunConfig(protocol=proto, composition=comp, n_miners=n,
                                          seed=seed, seed_index=k, phase="secondary",
                                          tag="alloc", **_conf_pocol(proto)))

    # S-B: selection rule x target hash fraction
    for rule in SEC_SELECTION_RULES:
        for frac in SEC_TARGET_HASH_FRACTIONS:
            for k, seed in enumerate(sec, start=1):
                runs.append(RunConfig(protocol=P3_ENERGY, composition=ref_c,
                                      n_miners=ref_n, seed=seed, seed_index=k,
                                      phase="secondary", allocation=pol.ALLOC_HASH,
                                      selection_rule=rule, target_hash_fraction=frac,
                                      tag=f"sel_{rule}_rh{int(frac*100)}"))

    # S-C: miner-count fraction sweep (shows r != r_H != r_P)
    for frac in SEC_COUNT_FRACTIONS:
        for k, seed in enumerate(sec, start=1):
            runs.append(RunConfig(protocol=P3_ENERGY, composition=ref_c, n_miners=ref_n,
                                  seed=seed, seed_index=k, phase="secondary",
                                  allocation=pol.ALLOC_HASH,
                                  selection_rule=CONF_SELECTION_RULE,
                                  target_count_fraction=frac,
                                  tag=f"cnt{int(frac*100)}"))

    # S-D: wake-delay sensitivity
    for tw in SEC_WAKE_S:
        for k, seed in enumerate(sec, start=1):
            kw = _conf_pocol(P4_RESERVE)
            kw["wake_s"] = tw
            runs.append(RunConfig(protocol=P4_RESERVE, composition=ref_c, n_miners=ref_n,
                                  seed=seed, seed_index=k, phase="secondary",
                                  tag=f"wake{int(tw)}", **kw))

    # S-E: trigger-interval sensitivity
    for tt in SEC_TRIGGER_S:
        for k, seed in enumerate(sec, start=1):
            kw = _conf_pocol(P4_RESERVE)
            kw["trigger_s"] = tt
            runs.append(RunConfig(protocol=P4_RESERVE, composition=ref_c, n_miners=ref_n,
                                  seed=seed, seed_index=k, phase="secondary",
                                  tag=f"trig{int(tt)}", **kw))

    # S-F: reserve initial hash fraction
    for f0 in SEC_RESERVE_INITIAL:
        sched = tuple(sorted({f0, (f0 + 1.0) / 2, (f0 + 3.0) / 4, 1.0}))
        for k, seed in enumerate(sec, start=1):
            kw = _conf_pocol(P4_RESERVE)
            kw["reserve_schedule"] = sched
            runs.append(RunConfig(protocol=P4_RESERVE, composition=ref_c, n_miners=ref_n,
                                  seed=seed, seed_index=k, phase="secondary",
                                  tag=f"init{int(f0*100)}", **kw))

    # S-G: N-scaling at the secondary network sizes
    for comp in PRIMARY_COMPOSITIONS:
        for n in SECONDARY_NETWORK_SIZES:
            for k, seed in enumerate(sec, start=1):
                for proto in PRIMARY_PROTOCOLS:
                    kw = {} if proto == POW else _conf_pocol(proto)
                    runs.append(RunConfig(protocol=proto, composition=comp, n_miners=n,
                                          seed=seed, seed_index=k, phase="secondary",
                                          tag="scale", **kw))

    # S-H: common-template independent PoW mechanism diagnostic
    for k, seed in enumerate(sec, start=1):
        runs.append(RunConfig(protocol=POW_CT, composition=ref_c, n_miners=ref_n,
                              seed=seed, seed_index=k, phase="secondary", tag="ct"))

    # S-I: matched traditional-PoW baseline for the secondary reference cell.
    # Without it the secondary PoCol runs at (H2, N=300) have no paired PoW control
    # and every secondary sensitivity pairing is silently dropped. Added post-freeze
    # as amendment A1; it adds a control, changes no scientific parameter and leaves
    # config_hash unchanged.
    for k, seed in enumerate(sec, start=1):
        runs.append(RunConfig(protocol=POW, composition=ref_c, n_miners=ref_n,
                              seed=seed, seed_index=k, phase="secondary", tag="base"))
    return runs


def longhorizon_matrix() -> List[RunConfig]:
    """Predefined important configurations at T = 100 000 s."""
    runs: List[RunConfig] = []
    for comp in LONG_HORIZON_COMPOSITIONS:
        for k, seed in enumerate(seedmod.longhorizon_seeds(), start=1):
            for proto in LONG_HORIZON_PROTOCOLS:
                kw = {} if proto == POW else _conf_pocol(proto)
                runs.append(RunConfig(protocol=proto, composition=comp,
                                      n_miners=LONG_HORIZON_N, seed=seed, seed_index=k,
                                      horizon_s=LONG_HORIZON_S, phase="longhorizon",
                                      **kw))
    return runs


# --------------------------------------------------------------------------
# Fingerprint
# --------------------------------------------------------------------------
def frozen_parameters() -> Dict:
    return {
        "experiment": EXPERIMENT, "revision": REVISION,
        "hardware_registry": hw.registry_raw(),
        "compositions": {k: hw.COMPOSITIONS[k] for k in ALL_COMPOSITIONS},
        "composition_rationale": hw.COMPOSITION_RATIONALE,
        "primary_network_sizes": list(PRIMARY_NETWORK_SIZES),
        "secondary_network_sizes": list(SECONDARY_NETWORK_SIZES),
        "primary_compositions": list(PRIMARY_COMPOSITIONS),
        "primary_protocols": list(PRIMARY_PROTOCOLS),
        "horizon_s": HORIZON_S, "long_horizon_s": LONG_HORIZON_S,
        "target_interval_s": TARGET_INTERVAL_S, "epoch_sweep_s": EPOCH_SWEEP_S,
        "prop_delay_mean_s": BLOCK_PROP_DELAY_MEAN_S,
        "difficulty_rule": "D = H_N * I_target / 2**32 from FULL installed hardware; "
                           "one D per (N, composition), handed unchanged to PoW and "
                           "every PoCol policy; never recalibrated for PoCol.",
        "nonce_domain_rule": "S = H_N * tau_epoch from FULL installed capacity; one "
                             "disjoint slot per installed miner; parking a miner "
                             "leaves its slot unscanned and does not shrink S.",
        "domain_semantics": DOMAIN_SEMANTICS,
        "confirmatory_policy": {
            "selection_rule": CONF_SELECTION_RULE,
            "target_hash_fraction": CONF_TARGET_HASH_FRACTION,
            "reserve_schedule": list(CONF_RESERVE_SCHEDULE),
            "trigger_s": CONF_TRIGGER_S, "wake_s": CONF_WAKE_S,
            "allocation": CONF_ALLOCATION,
            "wake_power_ratio": WAKE_POWER_RATIO,
            "wake_power_note": "Wake transitions draw full active power. This is the "
                               "conservative choice and is unfavourable to PoCol; no "
                               "manufacturer wake-power curve exists.",
        },
        "alpha_cases": ALPHA_CASES, "alpha_note": ALPHA_NOTE,
        "idealized_alpha_labels": list(IDEALIZED_ALPHA_LABELS),
        "standby_equals_low": STANDBY_EQUALS_LOW,
        "acceptance_criteria": ACCEPTANCE,
        "seed_namespace": seedmod.NAMESPACE,
        "n_primary_seeds": N_PRIMARY_SEEDS,
        "secondary_grids": {
            "selection_rules": list(SEC_SELECTION_RULES),
            "target_hash_fractions": list(SEC_TARGET_HASH_FRACTIONS),
            "count_fractions": list(SEC_COUNT_FRACTIONS),
            "wake_s": list(SEC_WAKE_S), "trigger_s": list(SEC_TRIGGER_S),
            "reserve_initial": list(SEC_RESERVE_INITIAL),
            "reference_N": SEC_REF_N, "reference_composition": SEC_REF_COMPOSITION,
        },
        "longhorizon": {
            "N": LONG_HORIZON_N, "compositions": list(LONG_HORIZON_COMPOSITIONS),
            "protocols": list(LONG_HORIZON_PROTOCOLS), "horizon_s": LONG_HORIZON_S,
        },
        "difficulty_table": diffmod.difficulty_table(
            list(ALL_COMPOSITIONS), list(ALL_NETWORK_SIZES),
            TARGET_INTERVAL_S, EPOCH_SWEEP_S),
    }


def config_hash() -> str:
    payload = json.dumps(frozen_parameters(), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
