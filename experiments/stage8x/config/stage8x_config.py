"""Stage 8X — frozen experiment configuration.

Every scientific parameter of Stage 8X lives here. Nothing in this module may be
changed after the freeze without incrementing ``REVISION`` and re-running all
affected primary runs (brief section 20).

This module never imports ``InputsConfig`` and never touches any earlier stage.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, asdict, field
from typing import Dict, List, Tuple

from experiments.stage8x.config.asic import ALPHA_CASES, S21_PRO
from experiments.stage8x.config import difficulty as diffmod
from experiments.stage8x.config import seeds as seedmod

EXPERIMENT = "Stage8X"
REVISION = 1

#: Corrections applied to NON-scientific code AFTER the freeze, recorded verbatim in
#: the freeze report. None of these touches a scientific parameter, a physical run,
#: or ``config_hash``; each is a defect fix in a reporting/derived quantity only.
POST_FREEZE_AMENDMENTS = [
    {
        "id": "A1",
        "date": "2026-08-14",
        "file": "experiments/stage8x/analysis/tables.py",
        "defect": (
            "Table H's reference column `theoretical_duplicate_ratio` used "
            "1-(1-1/N)^N, which is the expected *coverage* fraction, not the "
            "expected duplicate ratio."
        ),
        "fix": (
            "Corrected to (1-1/N)^N -> e^-1 = 0.3679, the expected duplicate ratio "
            "for N miners scanning L candidates at independent uniform offsets in a "
            "shared domain S = N*L."
        ),
        "scope": (
            "Display-only reference column in a declared SECONDARY diagnostic table. "
            "No physical run, no primary result, no frozen parameter and no "
            "config_hash is affected; no run was re-executed."
        ),
    },
    {
        "id": "A2",
        "date": "2026-08-14",
        "file": "experiments/stage8x/config/asic.py",
        "defect": (
            "ALPHA_LABELS repeated the phrase 'sensitivity assumption', which the "
            "report template already prefixes, producing 'experimental sensitivity "
            "assumption - sensitivity assumption, 10% of active power'."
        ),
        "fix": "Trimmed the redundant prefix from the LP10/LP25/LP50 label strings.",
        "scope": (
            "Human-readable label strings only. No numeric value, no alpha, no "
            "frozen parameter and no config_hash is affected (config_hash covers "
            "ALPHA_CASES values, not ALPHA_LABELS text); no run was re-executed."
        ),
    },
    {
        "id": "A3",
        "date": "2026-08-14",
        "file": "experiments/stage8x/analyze.py",
        "defect": (
            "The interpretation paragraph said 'the reduction in physical evaluations "
            "... is zero', conflating the (zero) duplicate-work reduction with the "
            "(non-zero, 0.24%) reduction in total physical evaluations."
        ),
        "fix": (
            "Reworded to state both quantities explicitly and to report the measured "
            "total-evaluation reduction alongside the energy reduction."
        ),
        "scope": (
            "Report prose only. No data, no frozen parameter, no config_hash; "
            "no run was re-executed."
        ),
    },
]

# --------------------------------------------------------------------------
# Frozen scientific parameters
# --------------------------------------------------------------------------
NETWORK_SIZES: Tuple[int, ...] = (100, 200, 300, 400, 500)
HORIZON_S: float = 10_000.0            # T, simulation horizon per physical run
TARGET_INTERVAL_S: float = 600.0       # I_target, nominal block interval
EPOCH_SWEEP_S: float = 600.0           # tau_epoch -> nonce domain, see difficulty.py
BLOCK_PROP_DELAY_MEAN_S: float = 0.42  # gossip delay ~ Exp(mean); BlockSim default
N_PRIMARY_SEEDS: int = seedmod.N_PRIMARY_SEEDS

#: Primary protocols. Exactly two families (brief section 5).
PROTO_POW = "POW"        # X-PW  : traditional competitive PoW, per-miner templates
PROTO_POCOL = "POCOL"    # X-PC  : PoCol static disjoint allocation + post-range low power
PROTO_POW_MT = "POWMT"   # X-PW-MATCHED-TEMPLATE : declared secondary diagnostic only
PRIMARY_PROTOCOLS: Tuple[str, ...] = (PROTO_POW, PROTO_POCOL)

PROTOCOL_LABELS = {
    PROTO_POW: "X-PW (traditional competitive PoW, per-miner distinct templates)",
    PROTO_POCOL: "X-PC (PoCol static disjoint allocation + post-range low power)",
    PROTO_POW_MT: "X-PW-MATCHED-TEMPLATE (secondary diagnostic, common-template PoW)",
}

# --------------------------------------------------------------------------
# Declared Pilot design (never merged into the primary dataset)
# --------------------------------------------------------------------------
PILOT_NETWORK_SIZES: Tuple[int, ...] = (100, 300, 500)
PILOT_PROTOCOLS: Tuple[str, ...] = (PROTO_POW, PROTO_POCOL, PROTO_POW_MT)
PILOT_N_SEEDS: int = seedmod.N_PILOT_SEEDS

# --------------------------------------------------------------------------
# Declared secondary analyses (frozen BEFORE primary execution, reported apart)
# --------------------------------------------------------------------------
#: S1 - matched-template PoW comparator, the only configuration in which exact
#: candidate-input duplication is non-degenerate (brief section 30).
SECONDARY_MT_NETWORK_SIZES: Tuple[int, ...] = NETWORK_SIZES

#: S2 - PoCol epoch-allocation sensitivity: how much candidate space the common
#: template allocates per epoch. tau_epoch = 600 s is the frozen primary value.
SECONDARY_EPOCH_SWEEPS_S: Tuple[float, ...] = (300.0, 60.0, 6.0)
SECONDARY_EPOCH_NETWORK_SIZES: Tuple[int, ...] = (100, 300, 500)

# --------------------------------------------------------------------------
# Paths
# --------------------------------------------------------------------------
HERE = os.path.dirname(os.path.abspath(__file__))
STAGE_DIR = os.path.dirname(HERE)
REPO_ROOT = os.path.abspath(os.path.join(STAGE_DIR, "..", ".."))
OUT_DIR = os.path.join(STAGE_DIR, "outputs")
FIG_DIR = os.path.join(STAGE_DIR, "figures")
REPORT_DIR = os.path.join(STAGE_DIR, "reports")
SEEDS_JSON = os.path.join(OUT_DIR, "stage8x_seeds.json")


def ensure_dirs() -> None:
    for d in (OUT_DIR, FIG_DIR, REPORT_DIR):
        os.makedirs(d, exist_ok=True)


# --------------------------------------------------------------------------
# Per-run configuration
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class RunConfig:
    """Immutable description of one *physical* simulation run."""

    protocol: str
    n_miners: int
    seed: int
    seed_index: int                     # 1-based index into the seed registry
    horizon_s: float = HORIZON_S
    target_interval_s: float = TARGET_INTERVAL_S
    epoch_sweep_s: float = EPOCH_SWEEP_S
    prop_delay_mean_s: float = BLOCK_PROP_DELAY_MEAN_S
    phase: str = "primary"              # primary | pilot | secondary
    tag: str = ""                       # optional discriminator (e.g. "tau60")

    # ---- identity ----
    @property
    def run_id(self) -> str:
        prefix = {"primary": "8X", "pilot": "8XP", "secondary": "8XS"}[self.phase]
        base = f"{prefix}_N{self.n_miners}_{self.protocol}_seed{self.seed_index:03d}"
        return f"{base}_{self.tag}" if self.tag else base

    @property
    def spec(self) -> diffmod.DifficultySpec:
        return diffmod.derive(
            self.n_miners,
            self.target_interval_s,
            self.epoch_sweep_s,
            S21_PRO,
        )


# --------------------------------------------------------------------------
# Experiment matrices
# --------------------------------------------------------------------------
def primary_matrix() -> List[RunConfig]:
    """5 network sizes x 2 protocols x 30 paired seeds = 300 physical runs."""
    reg = seedmod.primary_seeds(N_PRIMARY_SEEDS)
    runs: List[RunConfig] = []
    for n in NETWORK_SIZES:
        for k, seed in enumerate(reg, start=1):
            for proto in PRIMARY_PROTOCOLS:
                runs.append(
                    RunConfig(protocol=proto, n_miners=n, seed=seed,
                              seed_index=k, phase="primary")
                )
    return runs


def pilot_matrix() -> List[RunConfig]:
    reg = seedmod.pilot_seeds(PILOT_N_SEEDS)
    runs: List[RunConfig] = []
    for n in PILOT_NETWORK_SIZES:
        for k, seed in enumerate(reg, start=1):
            for proto in PILOT_PROTOCOLS:
                runs.append(
                    RunConfig(protocol=proto, n_miners=n, seed=seed,
                              seed_index=k, phase="pilot")
                )
    return runs


def secondary_matrix() -> List[RunConfig]:
    """Declared secondary diagnostics: S1 matched-template PoW, S2 epoch sweep."""
    reg = seedmod.primary_seeds(N_PRIMARY_SEEDS)
    runs: List[RunConfig] = []
    # S1 - matched-template PoW comparator (paired with the primary seeds)
    for n in SECONDARY_MT_NETWORK_SIZES:
        for k, seed in enumerate(reg, start=1):
            runs.append(
                RunConfig(protocol=PROTO_POW_MT, n_miners=n, seed=seed,
                          seed_index=k, phase="secondary", tag="MT")
            )
    # S2 - PoCol epoch-allocation sensitivity
    for tau in SECONDARY_EPOCH_SWEEPS_S:
        for n in SECONDARY_EPOCH_NETWORK_SIZES:
            for k, seed in enumerate(reg, start=1):
                runs.append(
                    RunConfig(protocol=PROTO_POCOL, n_miners=n, seed=seed,
                              seed_index=k, phase="secondary",
                              epoch_sweep_s=tau, tag=f"tau{int(tau)}")
                )
    return runs


# --------------------------------------------------------------------------
# Configuration fingerprint
# --------------------------------------------------------------------------
def frozen_parameters() -> Dict:
    """The complete set of scientific parameters covered by the freeze."""
    return {
        "experiment": EXPERIMENT,
        "revision": REVISION,
        "asic": {
            "name": S21_PRO.name,
            "hashrate_THs": S21_PRO.hashrate_ths,
            "active_power_W": S21_PRO.active_power_w,
            "efficiency_J_per_TH": S21_PRO.efficiency_j_per_th,
            "source_note": (
                "Active values are the official Bitmain Antminer S21 Pro nominal "
                "specification. Low-power values are experimental sensitivity "
                "assumptions, not vendor-certified modes."
            ),
        },
        "alpha_cases": ALPHA_CASES,
        "network_sizes": list(NETWORK_SIZES),
        "horizon_s": HORIZON_S,
        "target_interval_s": TARGET_INTERVAL_S,
        "epoch_sweep_s": EPOCH_SWEEP_S,
        "prop_delay_mean_s": BLOCK_PROP_DELAY_MEAN_S,
        "n_primary_seeds": N_PRIMARY_SEEDS,
        "primary_protocols": list(PRIMARY_PROTOCOLS),
        "seed_namespace": seedmod.NAMESPACE,
        "difficulty_rule": "D_N = H_N * I_target / 2**32 ; q_N = 1/(H_N*I_target)",
        "nonce_domain_rule": "S_N = H_N * tau_epoch ; L = S_N / N = h * tau_epoch",
        "matched_difficulty": "D^PoW_N == D^PoCol_N (single D_N per N)",
        "pilot": {
            "network_sizes": list(PILOT_NETWORK_SIZES),
            "protocols": list(PILOT_PROTOCOLS),
            "n_seeds": PILOT_N_SEEDS,
            "excluded_from_primary_dataset": True,
        },
        "secondary": {
            "S1_matched_template_network_sizes": list(SECONDARY_MT_NETWORK_SIZES),
            "S2_epoch_sweeps_s": list(SECONDARY_EPOCH_SWEEPS_S),
            "S2_network_sizes": list(SECONDARY_EPOCH_NETWORK_SIZES),
            "reported_separately_from_primary": True,
        },
        "difficulty_table": diffmod.difficulty_table(
            list(NETWORK_SIZES), TARGET_INTERVAL_S, EPOCH_SWEEP_S, S21_PRO
        ),
    }


def config_hash() -> str:
    payload = json.dumps(frozen_parameters(), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
