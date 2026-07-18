"""Phase B3 — single shared experimental scenario for PoW and PoCol.

One `ScenarioConfig` holds every protocol-INDEPENDENT parameter, so PoW and
PoCol cannot silently diverge (as they did with PoW Tn=3 vs PoCol Tn=10). Both
protocols are configured from the same object via `apply_to`. Protocol-specific
parameters are listed explicitly in `PROTOCOL_SPECIFIC` and justified.

A configuration hash (`config_hash`) over the shared parameters is recorded per
run for reproducibility (B6).
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, asdict


# Parameters that legitimately differ between the two protocols. Everything NOT
# listed here MUST be identical across PoW and PoCol for a controlled comparison.
# Each entry is inherent to the protocol, not a workload/environment knob.
PROTOCOL_SPECIFIC = {
    "PoW": {
        # Nakamoto consensus needs no extra workload/environment parameters.
    },
    "PoCol": {
        # Inherent to the nonce-partitioning mechanism only:
        "PoCol_AutoNonceSpace": True,   # size the shared nonce domain to the target interval
        "PoCol_TargetInterval": None,   # set = Binterval by apply_to (same target as PoW)
        "PoCol_AssignStrategy": "equal",
    },
}

# Model ids used by InputsConfig / Main.
MODEL_ID = {"PoW": 1, "PoCol": 3}


@dataclass(frozen=True)
class ScenarioConfig:
    # --- experiment axes ---
    n_miners: int
    seed: int
    # --- shared, protocol-INDEPENDENT parameters ---
    Tn: int = 10
    Binterval: float = 600.0
    Bsize: float = 1.0
    Bdelay: float = 0.42
    Tdelay: float = 5.1
    Tfee: float = 0.000062
    Tsize: float = 0.000546
    NetworkHashRate_Hps: float = 141e12
    MinerEfficiency_J_per_TH: float = 21.5
    GridEF_kgCO2e_per_kWh: float = 0.445
    HashPowerIsShare: bool = True
    simTime: float = 10000.0
    hasTrans: bool = True
    Ttechnique: str = "Light"

    def shared_params(self) -> dict:
        """Every protocol-independent parameter (basis of the equality guard)."""
        d = asdict(self)
        d.pop("seed", None)        # seed is an axis, compared separately in pairing
        return d

    def config_hash(self) -> str:
        payload = json.dumps(self.shared_params(), sort_keys=True).encode()
        return hashlib.sha256(payload).hexdigest()[:16]


def effective_params(scenario: ScenarioConfig, protocol: str) -> dict:
    """Full parameter set a protocol would run under = shared + protocol-specific."""
    params = scenario.shared_params()
    spec = dict(PROTOCOL_SPECIFIC[protocol])
    if protocol == "PoCol":
        spec["PoCol_TargetInterval"] = scenario.Binterval  # same target interval as PoW
    params["_protocol"] = protocol
    params["_protocol_specific"] = spec
    return params


def apply_to(p, scenario: ScenarioConfig, protocol: str) -> None:
    """Configure InputsConfig `p` for one protocol from the shared scenario.

    Does NOT build NODES (the harness builds them with the protocol's Node class).
    """
    p.model = MODEL_ID[protocol]
    for k, v in scenario.shared_params().items():
        if k == "n_miners":
            p.Nn = v
        else:
            setattr(p, k, v)
    # aliases used elsewhere in the codebase
    p.TOTAL_HASHRATE_HS = scenario.NetworkHashRate_Hps
    p.J_PER_HASH = scenario.MinerEfficiency_J_per_TH / 1e12
    p.GRID_GCO2_PER_KWH = scenario.GridEF_kgCO2e_per_kWh * 1000
    # protocol-specific
    spec = dict(PROTOCOL_SPECIFIC[protocol])
    if protocol == "PoCol":
        spec["PoCol_TargetInterval"] = scenario.Binterval
    for k, v in spec.items():
        setattr(p, k, v)


def non_protocol_difference(scenario: ScenarioConfig):
    """Return the set of shared parameters that differ between PoW and PoCol
    effective configs. Must be empty for a controlled comparison."""
    pw = effective_params(scenario, "PoW")
    pc = effective_params(scenario, "PoCol")
    pw.pop("_protocol"); pw.pop("_protocol_specific")
    pc.pop("_protocol"); pc.pop("_protocol_specific")
    return {k for k in set(pw) | set(pc) if pw.get(k) != pc.get(k)}
