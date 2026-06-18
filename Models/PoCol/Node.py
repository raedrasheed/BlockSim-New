# Models/PoCol/Node.py

from Models.Bitcoin.Node import Node as BitcoinNode


def _cfg():
    """
    Lazy import to avoid circular import with InputsConfig.py.
    """
    from InputsConfig import InputsConfig as p
    return p


class Node(BitcoinNode):
    """
    PoCol Miner Node (energy + CO2 + attempts).
    - Tracks cumulative energy (kWh), CO2 (kgCO2e), and total hash attempts.
    - Provides a per-round energy_log row in the same schema used by Statistics.EnergyLog.
    """

    def __init__(self, id, hashPower):
        super().__init__(id, hashPower)

        # ---- cumulative totals ----
        self.energy_j = 0.0
        self.energy_kwh = 0.0
        self.co2_kg = 0.0

        # Keep both names for compatibility across your codebase
        self.hashes = 0.0
        self.attempts_hashes = 0.0

        # ---- per-round rows (optional) ----
        # rows match Statistics._ENERGYLOG_COLS
        self.energy_log = []
        self.energyLog = self.energy_log
        self.EnergyLog = self.energy_log

        # Optional debug fields
        self.nonce_start = None
        self.nonce_end = None
        self.last_assigned_parent = None
        self.last_solution_nonce = None

    # ----------------------------
    # Hashrate / Power Model
    # ----------------------------
    def _total_hashpower_units(self) -> float:
        try:
            p = _cfg()
            return float(sum(float(getattr(n, "hashPower", 0.0) or 0.0) for n in p.NODES))
        except Exception:
            return 0.0

    def hashrate_fraction(self) -> float:
        total = self._total_hashpower_units()
        if total > 0.0:
            return float(getattr(self, "hashPower", 1.0) or 1.0) / total

        # fallback equal split
        try:
            p = _cfg()
            n = max(1, len(getattr(p, "NODES", [])))
        except Exception:
            n = 1
        return 1.0 / float(n)

    @staticmethod
    def _get_first(p, names, default=None):
        for n in names:
            if hasattr(p, n):
                v = getattr(p, n)
                if v is not None:
                    return v
        return default

    def get_hashrate_hps(self) -> float:
        """
        Miner hashrate in hashes/second (H/s).
        - If NetworkHashRate_Hps exists, split by hashrate_fraction().
        - Otherwise fall back to hashPower (relative units).
        """
        p = _cfg()

        total_hps = self._get_first(
            p,
            [
                "NetworkHashRate_Hps",
                "NetworkHashRateHPS",
                "NetworkHashRate_HPS",
                "NetworkHashRate",
                "NhashRate",
                "network_hash_rate",
            ],
            default=None,
        )

        if total_hps is None:
            return float(getattr(self, "hashPower", 1.0) or 1.0)

        try:
            total_hps = float(total_hps)
        except Exception:
            total_hps = 0.0

        return total_hps * self.hashrate_fraction()

    def _efficiency_j_per_hash(self) -> float:
        """
        Returns J/hash.
        Priority:
          1) explicit J/hash config
          2) J/TH config converted to J/hash (divide by 1e12)
          3) fallback 0.0
        """
        p = _cfg()

        j_per_hash = self._get_first(
            p,
            ["PoCol_Efficiency_J_per_hash", "Efficiency_J_per_hash", "J_per_hash", "JperHash"],
            default=None,
        )
        if j_per_hash is not None:
            try:
                return float(j_per_hash)
            except Exception:
                return 0.0

        j_per_th = self._get_first(
            p,
            ["MinerEfficiency_J_per_TH", "MinerEfficiency", "Efficiency_J_per_TH", "J_per_TH", "JperTH"],
            default=None,
        )
        if j_per_th is None:
            return 0.0

        try:
            j_per_th = float(j_per_th)
        except Exception:
            return 0.0

        return j_per_th / 1e12  # J/hash

    def get_power_w(self) -> float:
        """
        Power (W).
        If MinerPowerW is configured, use it.
        Else Power = hashrate(H/s) * efficiency(J/hash).
        """
        p = _cfg()

        # Node override (if someone set it dynamically)
        if hasattr(self, "power_w") and getattr(self, "power_w") is not None:
            try:
                return float(getattr(self, "power_w"))
            except Exception:
                pass

        configured_w = self._get_first(p, ["PoCol_MinerPowerW", "MinerPowerW", "PowerW"], default=None)
        if configured_w is not None:
            try:
                return float(configured_w)
            except Exception:
                return 0.0

        hps = self.get_hashrate_hps()
        eff = self._efficiency_j_per_hash()
        if hps <= 0.0 or eff <= 0.0:
            return 0.0
        return hps * eff

    def carbon_intensity_kg_per_kwh(self) -> float:
        """
        Carbon intensity (kgCO2e/kWh).
        """
        p = _cfg()
        v = self._get_first(
            p,
            ["GridEF_kgCO2e_per_kWh", "GridEF", "GridEF_kg_per_kWh", "CarbonIntensity_kg_per_kWh"],
            default=0.0,
        )
        try:
            return float(v)
        except Exception:
            return 0.0

    # ----------------------------
    # Per-round accounting helper
    # ----------------------------
    def add_energy_for_round(
        self,
        parent_id,
        block_id,
        winner_id=None,
        block_time_s=None,
        time_share_s=None,
        t_s=None,
        reason="PoColRoundShare",
    ):
        """
        Adds this miner's energy/CO2 and pushes a row into self.energy_log.
        Row schema matches Statistics._ENERGYLOG_COLS.
        """
        dt = float(max(time_share_s or 0.0, 0.0))
        t = float(t_s or 0.0)

        power_w = float(self.get_power_w())
        energy_j = power_w * dt
        energy_kwh = energy_j / 3_600_000.0  # 1 kWh = 3.6e6 J

        co2_kg = energy_kwh * float(self.carbon_intensity_kg_per_kwh())

        # Hash attempts (H/s * s). If get_hashrate_hps is unavailable, infer from power+efficiency.
        hps = float(self.get_hashrate_hps() or 0.0)
        if hps <= 0.0 and power_w > 0.0:
            eff = float(self._efficiency_j_per_hash() or 0.0)
            if eff > 0.0:
                hps = power_w / eff

        hashes = hps * dt

        # cumulative totals
        self.energy_j += energy_j
        self.energy_kwh += energy_kwh
        self.co2_kg += co2_kg
        self.hashes += hashes
        self.attempts_hashes += hashes

        row = {
            "t": t,
            "miner_id": self.id,
            "dt": dt,
            "hashes": float(hashes),
            "energy_kwh": float(energy_kwh),
            "co2_kg": float(co2_kg),
            "reason": str(reason or ""),
            "parent_id": parent_id,
            "block_id": block_id,
        }

        self.energy_log.append(row)
        self.energyLog = self.energy_log
        self.EnergyLog = self.energy_log

        # (Optional) if Consensus passes winner_id/block_time_s, keep them as attributes
        self.last_assigned_parent = parent_id
        if winner_id is not None:
            self.last_winner_id = winner_id
        if block_time_s is not None:
            self.last_block_time_s = float(block_time_s)
