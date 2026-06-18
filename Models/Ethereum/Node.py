from Models.Node import Node as BaseNode
from Models.Ethereum.Block import Block


class Node(BaseNode):
    """
    Ethereum PoW node/miner model with:
    - hashPower (PoW rate fraction)
    - unclechain buffer (uncle candidates)
    - Bitcoin-style energy + CO2 accounting (start_mining/stop_mining_and_account)
    """

    def __init__(self, id, hashPower, power_w=None):
        super().__init__(id)

        # Mining capability
        self.hashPower = hashPower

        # Local state
        self.blockchain = []
        self.transactionsPool = []
        self.blocks = 0
        self.uncles = 0
        self.balance = 0

        # Uncle candidate buffer
        self.unclechain = []

        # ---------- Energy/CO2 accounting ----------
        self.power_w = power_w  # optional fixed miner power in watts

        self.mining_active = False
        self.mining_start_time = 0.0
        self.mining_parent_id = None

        self.total_energy_kwh = 0.0
        self.total_co2_kg = 0.0

        self.last_mining_energy_kwh = 0.0
        self.last_mining_co2_kg = 0.0
        self.last_mining_duration_s = 0.0

        # Attempts/Hashes totals (per-miner)
        self.attempts_hashes = 0.0
        self.energy_kwh_total = 0.0
        self.co2_kg_total = 0.0

    # ----------------- Genesis and reset -----------------

    @staticmethod
    def generate_gensis_block():
        from InputsConfig import InputsConfig as p
        for node in p.NODES:
            node.blockchain.append(Block())

    @staticmethod
    def resetState():
        from InputsConfig import InputsConfig as p
        for node in p.NODES:
            node.blockchain = []
            node.transactionsPool = []
            node.unclechain = []
            node.blocks = 0
            node.uncles = 0
            node.balance = 0

            node.mining_active = False
            node.mining_start_time = 0.0
            node.mining_parent_id = None

            node.total_energy_kwh = 0.0
            node.total_co2_kg = 0.0
            node.last_mining_energy_kwh = 0.0
            node.last_mining_co2_kg = 0.0
            node.last_mining_duration_s = 0.0

            node.attempts_hashes = 0.0
            node.energy_kwh_total = 0.0
            node.co2_kg_total = 0.0

    # ----------------- Uncle handling helpers -----------------

    @staticmethod
    def add_uncles(miner):
        """
        Select up to p.Buncles eligible uncles from miner.unclechain
        (only within p.Ugenerations depth window).
        """
        from InputsConfig import InputsConfig as p

        max_uncles = int(getattr(p, "Buncles", 0))
        u_generations = int(getattr(p, "Ugenerations", 0))

        if max_uncles <= 0 or u_generations <= 0:
            return []

        uncles = []
        j = 0
        while j < len(miner.unclechain):
            uncle = miner.unclechain[j]
            uncle_depth = getattr(uncle, "depth", -1)
            block_depth = getattr(miner.last_block(), "depth", 0)

            if max_uncles > 0 and uncle_depth > block_depth - u_generations:
                uncles.append(uncle)
                del miner.unclechain[j]
                j -= 1
                max_uncles -= 1
            j += 1

        return uncles

    # ----------------- Energy/CO2 (Bitcoin-style API) -----------------

    def _resolve_power_w(self) -> float:
        """
        Resolve miner power in watts.

        Priority:
        1) self.power_w
        2) InputsConfig.POWER_WATTS (dict or list)
        3) derive from InputsConfig.TOTAL_HASHRATE_HS + InputsConfig.J_PER_HASH
        """
        if self.power_w is not None:
            try:
                return float(self.power_w)
            except Exception:
                return 0.0

        from InputsConfig import InputsConfig as p

        pw = getattr(p, "POWER_WATTS", None)
        if isinstance(pw, dict):
            return float(pw.get(self.id, 0.0))
        if isinstance(pw, (list, tuple)) and 0 <= self.id < len(pw):
            return float(pw[self.id])

        j_per_hash = getattr(p, "J_PER_HASH", None)
        total_hashrate = getattr(p, "TOTAL_HASHRATE_HS", None)
        if j_per_hash is not None and total_hashrate is not None:
            try:
                total_hp = sum(n.hashPower for n in p.NODES) or 1.0
                frac = float(self.hashPower) / float(total_hp)
                miner_hashrate = float(total_hashrate) * frac
                return float(miner_hashrate) * float(j_per_hash)
            except Exception:
                return 0.0

        return 0.0

    def _resolve_hashrate_hps(self) -> float:
        """
        Resolve this miner's absolute hashrate (H/s) for attempts logging.
        Works whether hashPower is a share or an absolute hashrate.
        """
        from InputsConfig import InputsConfig as p

        # Total network hashrate (H/s)
        total_hr = float(getattr(p, "TOTAL_HASHRATE_HS", getattr(p, "NetworkHashRate_Hps", 0.0)))

        if getattr(p, "HashPowerIsShare", True):
            total_hp = sum(n.hashPower for n in p.NODES) or 1.0
            share = float(self.hashPower) / float(total_hp)
            return share * total_hr

        # hashPower is already absolute H/s
        return float(self.hashPower)

    def start_mining(self, parent_block_id, current_time: float):
        self.mining_active = True
        self.mining_start_time = float(current_time)
        self.mining_parent_id = parent_block_id

    def stop_mining_and_account(self, current_time: float, reason: str = "", block_id=None):
        """
        Stop current mining interval and account energy + CO2.
        Also appends a row to Statistics.energyLog for the Excel EnergyLog sheet.

        Returns: (energy_kwh, co2_kg, duration_s)
        """
        if not getattr(self, "mining_active", False):
            self.last_mining_energy_kwh = 0.0
            self.last_mining_co2_kg = 0.0
            self.last_mining_duration_s = 0.0
            return 0.0, 0.0, 0.0

        t1 = float(current_time)
        duration_s = max(0.0, t1 - float(self.mining_start_time))

        # Energy
        power_w = self._resolve_power_w()
        energy_kwh = (power_w * duration_s) / 3_600_000.0  # W*s -> kWh

        # CO2
        from InputsConfig import InputsConfig as p
        grid_g_per_kwh = float(getattr(p, "GRID_GCO2_PER_KWH", 0.0))
        co2_kg = energy_kwh * (grid_g_per_kwh / 1000.0)  # g -> kg

        # Attempts/Hashes
        miner_hr = self._resolve_hashrate_hps()
        hashes = miner_hr * duration_s

        # Update per-miner totals
        self.total_energy_kwh += energy_kwh
        self.total_co2_kg += co2_kg

        self.attempts_hashes += hashes
        self.energy_kwh_total += energy_kwh
        self.co2_kg_total += co2_kg

        # Store last interval (useful for attaching to a mined block)
        self.last_mining_energy_kwh = energy_kwh
        self.last_mining_co2_kg = co2_kg
        self.last_mining_duration_s = duration_s

        # Stop mining
        self.mining_active = False

        # Keep parent id for logging row, then clear
        parent_id = self.mining_parent_id
        self.mining_parent_id = None

        # ---- Log row into Statistics.energyLog (EnergyLog sheet) ----
        try:
            from Statistics import Statistics

            # Ensure log container exists
            if not hasattr(Statistics, "energyLog"):
                Statistics.energyLog = []

            # Many forks export totals from these names:
            Statistics.totalAttempts = getattr(Statistics, "totalAttempts", 0.0) + hashes
            Statistics.totalEnergy_kWh = getattr(Statistics, "totalEnergy_kWh", 0.0) + energy_kwh
            Statistics.totalCO2_kg = getattr(Statistics, "totalCO2_kg", 0.0) + co2_kg

            # Row schema matches your Excel columns:
            # t, miner_id, dt, hashes, energy_kwh, co2_kg, reason, parent_id, block_id
            Statistics.energyLog.append(
                [t1, self.id, duration_s, hashes, energy_kwh, co2_kg, reason, parent_id, block_id]
            )

        except Exception:
            # If Statistics isn't available, we still return computed values
            pass

        return energy_kwh, co2_kg, duration_s
