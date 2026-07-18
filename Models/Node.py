from Models.Block import Block

class Node(object):
    """
    Base Node + energy/CO2 instrumentation.
    Attempts are tracked as 'hashes' (or nonce trials).
    """

    def __init__(self, id):
        self.id = id
        self.blockchain = []
        self.transactionsPool = []
        self.blocks = 0
        self.balance = 0

        # ---- Energy instrumentation ----
        self.mining_start_time = None
        self.mining_parent_id = None

        self.attempts_hashes = 0.0
        self.energy_kwh = 0.0
        self.co2_kg = 0.0

    @staticmethod
    def generate_gensis_block():
        from InputsConfig import InputsConfig as p
        for node in p.NODES:
            node.blockchain.append(Block())
            # reset mining state at genesis
            node.mining_start_time = None
            node.mining_parent_id = None

    def last_block(self):
        return self.blockchain[len(self.blockchain) - 1]

    def blockchain_length(self):
        return len(self.blockchain) - 1

    # ---------------- Energy helpers ----------------
    def _effective_hashrate_hps(self):
        """Return miner hashrate in H/s, supporting share-based configs.

        When hashPower is a relative share, this miner's absolute hash rate is
        its FRACTION of the total configured network hash rate:

            H_i = NetworkHashRate_Hps * (hashPower_i / sum_j hashPower_j)

        so that sum_i H_i == NetworkHashRate_Hps for ANY number of miners.
        (The previous implementation used a hardcoded `hp / 100.0`, which fixed
        each miner at 1% of the network regardless of miner count; the aggregate
        hash rate then scaled with N and was correct only at exactly 100 miners.
        This matched neither the PoCol model (Models/PoCol/Node.py) nor the
        Ethereum model (Models/Ethereum/Node.py), both of which already normalize
        by the sum of shares.)
        """
        from InputsConfig import InputsConfig as p

        hp = float(getattr(self, "hashPower", 0.0))
        if hp <= 0:
            return 0.0

        # hashPower is a relative share: normalize by the sum of all shares
        if bool(getattr(p, "HashPowerIsShare", True)):
            net = float(getattr(p, "NetworkHashRate_Hps", 0.0))
            total_hp = sum(float(getattr(n, "hashPower", 0.0) or 0.0) for n in getattr(p, "NODES", []))
            if total_hp <= 0.0:
                return 0.0
            return net * (hp / total_hp)

        # Else hashPower is already H/s
        return hp

    @staticmethod
    def _hashes_to_kwh(hashes):
        """Convert hashes to kWh using MinerEfficiency_J_per_TH."""
        from InputsConfig import InputsConfig as p
        eff_j_per_th = float(getattr(p, "MinerEfficiency_J_per_TH", 0.0))
        if eff_j_per_th <= 0:
            return 0.0

        th = float(hashes) / 1e12
        energy_j = th * eff_j_per_th
        return energy_j / 3.6e6  # J -> kWh

    @staticmethod
    def _kwh_to_co2(energy_kwh):
        from InputsConfig import InputsConfig as p
        ef = float(getattr(p, "GridEF_kgCO2e_per_kWh", 0.0))
        return float(energy_kwh) * ef

    def start_mining(self, parent_id, start_time):
        """Mark mining start on a given parent at start_time."""
        self.mining_parent_id = parent_id
        self.mining_start_time = float(start_time)

    def stop_mining_and_account(self, stop_time, reason="", block_id=None):
        """
        Account hashes/energy from mining_start_time -> stop_time, then stop.
        Safe to call even if mining_start_time is None.
        """
        if self.mining_start_time is None:
            return

        stop_time = float(stop_time)
        dt = max(stop_time - float(self.mining_start_time), 0.0)

        rate = self._effective_hashrate_hps()
        hashes = rate * dt

        e_kwh = Node._hashes_to_kwh(hashes)
        co2 = Node._kwh_to_co2(e_kwh)

        self.attempts_hashes += hashes
        self.energy_kwh += e_kwh
        self.co2_kg += co2

        # Optional: log rows into Statistics if available
        try:
            from Statistics import Statistics
            Statistics.log_energy(
                t=stop_time,
                miner_id=self.id,
                dt=dt,
                hashes=hashes,
                energy_kwh=e_kwh,
                co2_kg=co2,
                reason=reason,
                parent_id=self.mining_parent_id,
                block_id=block_id
            )
        except Exception:
            pass

        # stop
        self.mining_start_time = None
        self.mining_parent_id = None

    @staticmethod
    def resetState():
        from InputsConfig import InputsConfig as p
        for node in p.NODES:
            node.blockchain = []
            node.transactionsPool = []
            node.blocks = 0
            node.balance = 0

            node.mining_start_time = None
            node.mining_parent_id = None
            node.attempts_hashes = 0.0
            node.energy_kwh = 0.0
            node.co2_kg = 0.0
