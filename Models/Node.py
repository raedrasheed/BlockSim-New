from Models.Block import Block
from Models.Energy.wallclock_energy import (
    active_power_w as _active_power_w,
    hashes_to_energy_j as _hashes_to_energy_j,
    joules_to_kwh as _joules_to_kwh,
    J_PER_KWH,
)


class Node(object):
    """
    Base Node + wall-clock, state-based energy/CO2 instrumentation.

    Stage 2 (scientific revision) corrections:
      * hash rate is normalized by the SUM of hash-power weights, not by a
        hard-coded 100 (fixes the PoW '/100' bug: total network hash rate is
        now fixed regardless of miner count);
      * energy is derived from actual ACTIVE wall-clock duration
        (E = P_active * t_active), never divided by the number of miners;
      * an idempotent end-of-simulation flush accounts any still-open ACTIVE
        interval up to (never beyond) the simulation cutoff.

    Units are explicit: *_hps (H/s), *_j_per_th (J/TH), *_power_w (W),
    *_time_s (s), *_energy_j (J), *_kwh (kWh).
    """

    def __init__(self, id):
        self.id = id
        self.blockchain = []
        self.transactionsPool = []
        self.blocks = 0
        self.balance = 0

        # ---- wall-clock energy state ----
        self.mining_start_time = None     # start of the currently open ACTIVE interval (s)
        self.mining_parent_id = None

        # cumulative accounting
        self.attempts_hashes = 0.0
        self.active_time_s = 0.0
        self.idle_time_s = 0.0
        self.offline_time_s = 0.0
        self.energy_kwh = 0.0             # total (active + idle + coordination)
        self.active_energy_kwh = 0.0
        self.idle_energy_kwh = 0.0
        self.coordination_energy_kwh = 0.0
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

    # ---------------- Hash-rate / power (unit-explicit) ----------------
    def hash_rate_hps(self):
        """Miner hash rate in H/s under a FIXED aggregate network hash rate.

        With HashPowerIsShare, the miner's share is hashPower / Σ hashPower, so
        Σ_i H_i == NetworkHashRate_Hps for every miner count (Stage 2 fix). The
        previous implementation used hashPower/100, which made the total scale
        with miner count.
        """
        from InputsConfig import InputsConfig as p

        hp = float(getattr(self, "hashPower", 0.0) or 0.0)
        if hp <= 0:
            return 0.0

        if bool(getattr(p, "HashPowerIsShare", True)):
            net = float(getattr(p, "NetworkHashRate_Hps", 0.0) or 0.0)
            total_hp = 0.0
            for n in getattr(p, "NODES", []):
                total_hp += float(getattr(n, "hashPower", 0.0) or 0.0)
            if total_hp <= 0.0:
                return 0.0
            return net * (hp / total_hp)     # <-- Σ hashPower, not 100

        # else hashPower is already an absolute H/s value
        return hp

    # backward-compatible alias (older callers)
    def _effective_hashrate_hps(self):
        return self.hash_rate_hps()

    @staticmethod
    def _efficiency_j_per_th():
        from InputsConfig import InputsConfig as p
        return float(getattr(p, "MinerEfficiency_J_per_TH", 0.0) or 0.0)

    def active_power_w(self):
        """Active mining power (W) = H/s * J/hash."""
        return _active_power_w(self.hash_rate_hps(), Node._efficiency_j_per_th())

    def idle_power_w(self):
        """Idle power (W). Default 0.0 == explicit theoretical lower bound.

        Configurable via InputsConfig.IdlePowerW (absolute) or
        InputsConfig.IdlePowerRatio (fraction of active power).
        """
        from InputsConfig import InputsConfig as p
        w = getattr(p, "IdlePowerW", None)
        if w is not None:
            try:
                return float(w)
            except Exception:
                return 0.0
        ratio = getattr(p, "IdlePowerRatio", None)
        if ratio is not None:
            try:
                return float(ratio) * self.active_power_w()
            except Exception:
                return 0.0
        return 0.0

    @staticmethod
    def _hashes_to_kwh(hashes):
        """Convert hashes to kWh using MinerEfficiency_J_per_TH (J/hash path)."""
        eff = Node._efficiency_j_per_th()
        if eff <= 0:
            return 0.0
        return _joules_to_kwh(_hashes_to_energy_j(float(hashes), eff))

    @staticmethod
    def _kwh_to_co2(energy_kwh):
        from InputsConfig import InputsConfig as p
        ef = float(getattr(p, "GridEF_kgCO2e_per_kWh", 0.0) or 0.0)
        return float(energy_kwh) * ef

    # ---------------- Wall-clock ACTIVE accounting ----------------
    def start_mining(self, parent_id, start_time):
        """Open an ACTIVE interval on a given parent at start_time."""
        self.mining_parent_id = parent_id
        self.mining_start_time = float(start_time)

    def stop_mining_and_account(self, stop_time, reason="", block_id=None):
        """
        Close the open ACTIVE interval, accounting hashes/energy from
        mining_start_time -> stop_time, then stop. Safe/idempotent to call when
        no interval is open (mining_start_time is None).

        Energy is E = P_active * dt (wall-clock). The hash-count path
        (hashes * J/hash) agrees by construction. Never accounts negative time.
        """
        if self.mining_start_time is None:
            return

        stop_time = float(stop_time)
        dt = stop_time - float(self.mining_start_time)
        if dt < 0.0:
            dt = 0.0                      # never account negative time

        rate_hps = self.hash_rate_hps()
        power_w = _active_power_w(rate_hps, Node._efficiency_j_per_th())
        hashes = rate_hps * dt
        e_kwh = (power_w * dt) / J_PER_KWH
        co2 = Node._kwh_to_co2(e_kwh)

        self.attempts_hashes += hashes
        self.active_time_s += dt
        self.active_energy_kwh += e_kwh
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
                block_id=block_id,
            )
        except Exception:
            pass

        # stop (interval closed -> idempotent)
        self.mining_start_time = None
        self.mining_parent_id = None

    def flush_energy_at(self, t_sim):
        """Idempotent end-of-simulation flush.

        Accounts any still-open ACTIVE interval up to (never beyond) t_sim.
        Calling twice does not add energy twice (the interval is closed on the
        first call). This corrects the previous undercount where a miner's final
        active interval to the cutoff was never accounted.
        """
        if self.mining_start_time is None:
            return
        self.stop_mining_and_account(float(t_sim), reason="end_of_sim_flush")

    def add_coordination_energy_kwh(self, energy_kwh):
        """Record coordination/communication energy separately (never invented)."""
        e = float(energy_kwh or 0.0)
        if e < 0:
            return
        self.coordination_energy_kwh += e
        self.energy_kwh += e
        self.co2_kg += Node._kwh_to_co2(e)

    @staticmethod
    def finalize_energy(t_sim):
        """Flush every miner's open ACTIVE interval at the simulation cutoff."""
        from InputsConfig import InputsConfig as p
        for node in getattr(p, "NODES", []):
            if hasattr(node, "flush_energy_at"):
                node.flush_energy_at(t_sim)

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
            node.active_time_s = 0.0
            node.idle_time_s = 0.0
            node.offline_time_s = 0.0
            node.energy_kwh = 0.0
            node.active_energy_kwh = 0.0
            node.idle_energy_kwh = 0.0
            node.coordination_energy_kwh = 0.0
            node.co2_kg = 0.0
