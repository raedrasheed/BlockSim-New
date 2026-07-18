from Models.Block import Block


# Mining energy states
ACTIVE = "ACTIVE"
IDLE = "IDLE"


class Node(object):
    """
    Base Node with WALL-CLOCK energy integration (Phase B1).

    Energy is integrated ONCE over simulation wall-clock time, independently of
    the number of blocks created, stale blocks, or scheduled events. Whenever a
    miner changes mining state or an event affecting mining is processed, the
    meter is advanced:

        elapsed = current_time - last_energy_update_time
        if state == ACTIVE:
            cumulative_energy_j    += power_watts     * elapsed
            cumulative_hashes      += hashrate_hps    * elapsed
            cumulative_active_time += elapsed
        last_energy_update_time = current_time

    At the end of the simulation, finalize_energy(simTime) closes the open
    interval so the tail after the last block is not omitted. For continuous
    mining every miner is ACTIVE for [0, simTime], so

        cumulative_energy_j = power_watts * simTime,

    and the network total is P_network * simTime, INDEPENDENT of miner count.
    """

    def __init__(self, id):
        self.id = id
        self.blockchain = []
        self.transactionsPool = []
        self.blocks = 0
        self.balance = 0

        # ---- wall-clock energy meter ----
        self.mining_state = IDLE
        self.last_energy_update_time = 0.0
        self.power_watts = 0.0
        self.hashrate_hps = 0.0
        self.cumulative_energy_j = 0.0
        self.cumulative_active_time = 0.0
        self.cumulative_hashes = 0.0

        # ---- public totals (read by Statistics) ----
        self.energy_kwh = 0.0
        self.co2_kg = 0.0
        self.hashes = 0.0
        self.attempts_hashes = 0.0

        # legacy fields kept for compatibility with older call sites
        self.mining_start_time = None
        self.mining_parent_id = None

    # ------------------------------------------------------------------ #
    # Chain helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def generate_gensis_block():
        """Create the genesis block and start every miner's energy meter."""
        from InputsConfig import InputsConfig as p
        for node in p.NODES:
            node.blockchain.append(Block())
            node.mining_start_time = None
            node.mining_parent_id = None
            # Start continuous mining at t = 0 (all registered miners run their
            # hardware for the whole simulation in the current experiments).
            if hasattr(node, "begin_mining"):
                node.begin_mining(0.0)

    def last_block(self):
        return self.blockchain[len(self.blockchain) - 1]

    def blockchain_length(self):
        return len(self.blockchain) - 1

    # ------------------------------------------------------------------ #
    # Per-miner instantaneous hash rate / power (fractional normalization)
    # ------------------------------------------------------------------ #
    def _effective_hashrate_hps(self):
        """Absolute hash rate (H/s): this miner's fraction of the configured
        network hash rate, so sum_i H_i == NetworkHashRate_Hps for ANY N.

        (Previously `net * (hp/100.0)`, which fixed each miner at 1% of the
        network and made the aggregate scale with N — correct only at N=100.
        Now normalized by the sum of shares, matching the PoCol and Ethereum
        models.)
        """
        from InputsConfig import InputsConfig as p
        hp = float(getattr(self, "hashPower", 0.0))
        if hp <= 0:
            return 0.0
        if bool(getattr(p, "HashPowerIsShare", True)):
            net = float(getattr(p, "NetworkHashRate_Hps", 0.0))
            total_hp = sum(float(getattr(n, "hashPower", 0.0) or 0.0) for n in getattr(p, "NODES", []))
            if total_hp <= 0.0:
                return 0.0
            return net * (hp / total_hp)
        return hp

    def _power_w(self):
        """Instantaneous power (W) = hashrate (H/s) * efficiency (J/hash)."""
        from InputsConfig import InputsConfig as p
        eff_j_per_th = float(getattr(p, "MinerEfficiency_J_per_TH", 0.0))
        return self._effective_hashrate_hps() * (eff_j_per_th / 1e12)

    @staticmethod
    def _hashes_to_kwh(hashes):
        from InputsConfig import InputsConfig as p
        eff_j_per_th = float(getattr(p, "MinerEfficiency_J_per_TH", 0.0))
        if eff_j_per_th <= 0:
            return 0.0
        return (float(hashes) / 1e12) * eff_j_per_th / 3.6e6

    @staticmethod
    def _kwh_to_co2(energy_kwh):
        from InputsConfig import InputsConfig as p
        return float(energy_kwh) * float(getattr(p, "GridEF_kgCO2e_per_kWh", 0.0))

    # ------------------------------------------------------------------ #
    # Wall-clock energy meter
    # ------------------------------------------------------------------ #
    def update_energy(self, current_time):
        """Advance the meter to `current_time` at the CURRENT power/state.

        Idempotent for non-advancing times and safe to call from any event; it
        never charges an interval that has already been counted, because
        `last_energy_update_time` only ever moves forward.
        """
        t = float(current_time)
        elapsed = t - float(self.last_energy_update_time)
        if elapsed > 0.0 and self.mining_state == ACTIVE:
            self.cumulative_energy_j += self.power_watts * elapsed
            self.cumulative_hashes += self.hashrate_hps * elapsed
            self.cumulative_active_time += elapsed
            # keep public totals in sync
            self.energy_kwh = self.cumulative_energy_j / 3_600_000.0
            self.co2_kg = Node._kwh_to_co2(self.energy_kwh)
            self.hashes = self.cumulative_hashes
            self.attempts_hashes = self.cumulative_hashes
        if t > self.last_energy_update_time:
            self.last_energy_update_time = t

    def set_mining_state(self, state, current_time):
        """Integrate up to `current_time` at the previous state, then switch."""
        self.update_energy(current_time)
        self.mining_state = state
        if state == ACTIVE:
            self.hashrate_hps = self._effective_hashrate_hps()
            self.power_watts = self._power_w()
        else:
            self.hashrate_hps = 0.0
            self.power_watts = 0.0

    def begin_mining(self, current_time):
        """Mark the miner ACTIVE and (re)load its power/hash rate."""
        self.set_mining_state(ACTIVE, current_time)

    def finalize_energy(self, sim_time):
        """Close the open interval [last update, sim_time] at end of run."""
        self.update_energy(sim_time)

    @staticmethod
    def finalize_all(sim_time):
        from InputsConfig import InputsConfig as p
        for node in p.NODES:
            if hasattr(node, "finalize_energy"):
                node.finalize_energy(sim_time)

    # ------------------------------------------------------------------ #
    # Legacy checkpoint API (kept so existing model code keeps working).
    # These only advance the meter; they never charge a network round.
    # ------------------------------------------------------------------ #
    def start_mining(self, parent_id, start_time):
        self.mining_parent_id = parent_id
        self.mining_start_time = float(start_time)
        self.begin_mining(float(start_time))

    def stop_mining_and_account(self, stop_time, reason="", block_id=None):
        # Checkpoint only: integrate up to stop_time; the miner remains ACTIVE
        # because in both models it immediately resumes on the new tip. Going
        # IDLE is reserved for genuine cessation (future inactivity modeling).
        self.update_energy(float(stop_time))
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
            node.mining_state = IDLE
            node.last_energy_update_time = 0.0
            node.power_watts = 0.0
            node.hashrate_hps = 0.0
            node.cumulative_energy_j = 0.0
            node.cumulative_active_time = 0.0
            node.cumulative_hashes = 0.0
            node.energy_kwh = 0.0
            node.co2_kg = 0.0
            node.hashes = 0.0
            node.attempts_hashes = 0.0
            node.mining_start_time = None
            node.mining_parent_id = None
