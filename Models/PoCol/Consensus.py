# Models/PoCol/Consensus.py

import random
from collections import Counter

from InputsConfig import InputsConfig as p
from Models.Consensus import Consensus as BaseConsensus


class Consensus(BaseConsensus):
    """
    PoCol consensus:
    - For each parent block (round), we:
      1) compute nonce-space size so expected block time ~= target interval
      2) split nonce ranges across miners proportional to their hashrate (or hashPower)
      3) sample a solution nonce uniformly in the whole space
      4) the miner whose range contains the solution becomes winner
      5) winner time is derived from the position within its range

    Energy model (corrected):
    - block_time is the network time to produce the block (winner_time)
    - Each concurrently-active miner is charged E_i = P_i * block_time, because
      all miners search their disjoint nonce ranges in parallel during the same
      wall-clock interval. The network total is therefore P_network * block_time.
    - The earlier (block_time / N_miners) rule is removed: it double-counted the
      1/N share (already present in each P_i) and produced an artificial ~1/N
      energy reduction. See apply_energy_for_created_block for details.
    """

    # Active round state
    active_parent_id = None
    active_solution_nonce = None
    active_nonce_space = None
    active_ranges = {}         # miner_id -> (start, end)
    active_winner_id = None
    active_winner_time = None  # seconds (time to produce this block)

    # To prevent double-counting energy for the same created block event
    _energy_applied_block_ids = set()

    # To prevent duplicate EnergyLog rows (block_id, miner_id)
    _energy_log_keys = set()

    @staticmethod
    def _grid_kg_per_kwh():
        # Try common config names; default to 0.0 if unknown.
        for attr in ("grid_kg_per_kwh", "gridEF", "carbon_intensity_kg_per_kwh", "carbonIntensity"):
            try:
                v = getattr(p, attr)
                if v is not None:
                    return float(v)
            except Exception:
                pass
        return 0.0

    @staticmethod
    def _append_energy_log_row(row: dict):
        """Best-effort append to whatever EnergyLog container the Excel exporter reads."""
        try:
            key = (row.get("block_id", None), row.get("miner_id", None))
            if key in Consensus._energy_log_keys:
                return
            Consensus._energy_log_keys.add(key)
        except Exception:
            pass

        # 1) Try InputsConfig store (common in custom forks)
        try:
            if not hasattr(p, "EnergyLog") or getattr(p, "EnergyLog") is None:
                setattr(p, "EnergyLog", [])
            getattr(p, "EnergyLog").append(row)
        except Exception:
            pass

        # 2) Try Statistics class attribute
        try:
            from Statistics import Statistics as Stats  # type: ignore
            if hasattr(Stats, "EnergyLog"):
                getattr(Stats, "EnergyLog").append(row)
        except Exception:
            pass

        # 3) Try module-level EnergyLog in a Statistics module (some forks do this)
        for mod_name in ("Statistics", "Models.Statistics", "Models.PoCol.Statistics"):
            try:
                mod = __import__(mod_name, fromlist=["*"])
                if hasattr(mod, "EnergyLog"):
                    getattr(mod, "EnergyLog").append(row)
                    break
                if hasattr(mod, "Statistics"):
                    s = getattr(mod, "Statistics")
                    if hasattr(s, "EnergyLog"):
                        getattr(s, "EnergyLog").append(row)
                        break
            except Exception:
                continue

    @staticmethod
    def _target_interval():
        return float(getattr(p, "PoCol_TargetInterval", p.Binterval))

    @staticmethod
    def _loser_lag():
        # Ensure losers don't create before hearing winner (reduce forks).
        # You can tune PoCol_LoserLag if you want.
        return float(getattr(p, "PoCol_LoserLag", max(p.Bdelay * 5.0, 1e-3)))

    @staticmethod
    def _miners():
        return list(getattr(p, "NODES", []))

    @staticmethod
    def _miner_hashrate_hps(miner):
        # Prefer Node.get_hashrate_hps() if available (we added it in PoCol/Node.py)
        if hasattr(miner, "get_hashrate_hps") and callable(getattr(miner, "get_hashrate_hps")):
            return float(miner.get_hashrate_hps())

        # Otherwise fall back to hashPower (proxy)
        if hasattr(miner, "hashPower"):
            return float(miner.hashPower)

        # last resort
        return 1.0

    @staticmethod
    def _total_hashrate_hps(miners=None):
        miners = miners or Consensus._miners()
        return sum(max(Consensus._miner_hashrate_hps(m), 0.0) for m in miners)

    @staticmethod
    def _get_nonce_space(total_hashrate_hps):
        """
        Auto-size nonce space to hit target interval:
        E[T] ≈ S / (2 * H_total) => S ≈ 2 * H_total * T
        """
        if bool(getattr(p, "PoCol_AutoNonceSpace", True)):
            S = 2.0 * float(max(total_hashrate_hps, 1e-12)) * Consensus._target_interval()
            return int(max(1.0, S))

        return int(getattr(p, "PoCol_NonceSpace", 3_000_000))

    @staticmethod
    def _init_round(parent_id):
        miners = Consensus._miners()
        if not miners:
            # Nothing to do
            Consensus.active_parent_id = parent_id
            Consensus.active_solution_nonce = 0
            Consensus.active_nonce_space = 1
            Consensus.active_ranges = {}
            Consensus.active_winner_id = None
            Consensus.active_winner_time = Consensus._target_interval()
            return

        Consensus.active_parent_id = parent_id

        rates = [max(Consensus._miner_hashrate_hps(m), 1e-12) for m in miners]
        H_total = sum(rates)
        space = Consensus._get_nonce_space(H_total)

        # Assign nonce ranges proportional to rates
        lengths = []
        acc = 0
        for r in rates:
            L = int((r / H_total) * space) if H_total > 0 else int(space / len(miners))
            L = max(L, 1)
            lengths.append(L)
            acc += L

        # fix rounding drift (adjust last)
        if acc != space:
            lengths[-1] += (space - acc)
            lengths[-1] = max(lengths[-1], 1)

        ranges = {}
        start = 0
        for m, L in zip(miners, lengths):
            end = start + L - 1
            ranges[m.id] = (start, end)
            start = end + 1

        Consensus.active_ranges = ranges
        Consensus.active_nonce_space = space

        # sample solution nonce uniformly in [0, space-1]
        Consensus.active_solution_nonce = random.randrange(0, space)

        # identify winner: the range that contains the nonce
        winner_id = None
        for mid, (a, b) in ranges.items():
            if a <= Consensus.active_solution_nonce <= b:
                winner_id = mid
                break
        Consensus.active_winner_id = winner_id

        # compute winner time (seconds)
        # attempts = (nonce - range_start) + 1, time = attempts / winner_rate
        winner = next((m for m in miners if m.id == winner_id), None)
        if winner is None:
            # fallback
            Consensus.active_winner_time = Consensus._target_interval()
            return

        w_rate = max(Consensus._miner_hashrate_hps(winner), 1e-12)
        w_start, _ = ranges[winner_id]
        attempts = (Consensus.active_solution_nonce - w_start) + 1
        Consensus.active_winner_time = float(attempts) / float(w_rate)

    @staticmethod
    def Protocol(miner):
        """
        Returns the delay (seconds) after currentTime when this miner's create_block event should be scheduled.
        """
        parent_id = miner.last_block().id

        if Consensus.active_parent_id != parent_id:
            Consensus._init_round(parent_id)

        if miner.id not in Consensus.active_ranges:
            Consensus._init_round(parent_id)

        start, end = Consensus.active_ranges[miner.id]

        # store range assignment (optional debug)
        miner.nonce_start, miner.nonce_end = start, end
        miner.last_assigned_parent = parent_id
        miner.last_solution_nonce = Consensus.active_solution_nonce

        if miner.id == Consensus.active_winner_id:
            return float(Consensus.active_winner_time)

        # losers: schedule safely after winner + lag
        return float(Consensus.active_winner_time + Consensus._loser_lag())

    # ----------------------------
    # Energy logic (your requirement)
    # ----------------------------
    @staticmethod
    def apply_energy_for_created_block(block):
        """
        Call this ONLY when a create_block event is actually accepted (blockPrev matches miner.last_block()).

        Energy model (corrected): each miner that is concurrently searching in
        this round is charged for the ACTUAL wall-clock duration of the round,

            E_i = P_i * block_time,

        where block_time = active_winner_time is the elapsed time until the
        winner finds the solution. All miners search their disjoint ranges in
        parallel during that same interval, so the network total is

            sum_i E_i = (sum_i P_i) * block_time = P_network * block_time,

        which is the physically correct energy for producing one block.

        NOTE: a previous version charged each miner block_time / N_miners, which
        divided the elapsed round time by the miner count a second time (each
        P_i already carries the 1/N hash-rate share). That inserted an artificial
        1/N energy reduction by construction and is the reason earlier runs
        reported ~98-99% "savings"; it has been removed. The legitimate saving
        from disjoint nonce ranges is the elimination of duplicate complete hash
        inputs, which does not reduce aggregate concurrent power and must be
        measured separately, not injected through the time term.
        """
        if block is None:
            return

        # Deduplicate by block.id (so we never double-count energy for the same created block)
        block_id = getattr(block, "id", None)
        if block_id is None or block_id in Consensus._energy_applied_block_ids:
            return

        parent_id = getattr(block, "previous", None)
        if parent_id is None:
            return

        # Ensure round state matches this parent
        if Consensus.active_parent_id != parent_id:
            Consensus._init_round(parent_id)

        miners = Consensus._miners()
        if not miners:
            return

        block_time = float(Consensus.active_winner_time)
        # Corrected model: charge each concurrently-active miner for the FULL
        # round wall-clock (block_time), NOT block_time / N. See docstring.
        time_share = block_time

        winner_id = Consensus.active_winner_id

        # Apply per-miner energy
        total_energy_kwh = 0.0
        total_co2_kg = 0.0
        for m in miners:
            # PoCol Node has add_energy_for_round(); if not, we do best-effort.
            if hasattr(m, "add_energy_for_round") and callable(getattr(m, "add_energy_for_round")):
                before_kwh = float(getattr(m, "energy_kwh", 0.0))
                before_co2 = float(getattr(m, "co2_kg", 0.0))
                before_hashes = float(getattr(m, "hashes", 0.0))

                m.add_energy_for_round(
                    parent_id=parent_id,
                    block_id=block_id,
                    winner_id=winner_id,
                    block_time_s=block_time,
                    time_share_s=time_share,
                )

                after_kwh = float(getattr(m, "energy_kwh", 0.0))
                after_co2 = float(getattr(m, "co2_kg", 0.0))
                after_hashes = float(getattr(m, "hashes", 0.0))

                d_kwh = max(0.0, after_kwh - before_kwh)
                d_co2 = max(0.0, after_co2 - before_co2)
                d_hashes = max(0.0, after_hashes - before_hashes)

                total_energy_kwh += d_kwh
                total_co2_kg += d_co2

                # Log per-miner per-created-block energy share
                try:
                    t_s = float(getattr(block, "timestamp", 0.0))
                except Exception:
                    t_s = 0.0
                Consensus._append_energy_log_row(
                    {
                        "t": t_s,
                        "miner_id": int(getattr(m, "id", 0)),
                        "dt": float(time_share),
                        "hashes": float(d_hashes),
                        "energy_kwh": float(d_kwh),
                        "co2_kg": float(d_co2),
                        "reason": "PoColRoundShareWinner" if int(getattr(m, "id", -1)) == int(winner_id) else "PoColRoundShare",
                        "parent_id": parent_id,
                        "block_id": block_id,
                    }
                )
            else:
                # fallback: try minimal fields
                power_w = 0.0
                if hasattr(m, "get_power_w") and callable(getattr(m, "get_power_w")):
                    power_w = float(m.get_power_w())

                energy_j = power_w * time_share
                energy_kwh = energy_j / 3_600_000.0
                co2_kg = energy_kwh * Consensus._grid_kg_per_kwh()

                try:
                    hps = float(Consensus._miner_hashrate_hps(m))
                except Exception:
                    hps = 0.0
                hashes = hps * float(max(time_share, 0.0))

                m.energy_kwh = float(getattr(m, "energy_kwh", 0.0)) + energy_kwh
                m.co2_kg = float(getattr(m, "co2_kg", 0.0)) + co2_kg
                m.hashes = float(getattr(m, "hashes", 0.0)) + hashes

                total_energy_kwh += energy_kwh
                total_co2_kg += co2_kg

                try:
                    t_s = float(getattr(block, "timestamp", 0.0))
                except Exception:
                    t_s = 0.0
                Consensus._append_energy_log_row(
                    {
                        "t": t_s,
                        "miner_id": int(getattr(m, "id", 0)),
                        "dt": float(time_share),
                        "hashes": float(hashes),
                        "energy_kwh": float(energy_kwh),
                        "co2_kg": float(co2_kg),
                        "reason": "PoColRoundShareWinner" if int(getattr(m, "id", -1)) == int(winner_id) else "PoColRoundShare",
                        "parent_id": parent_id,
                        "block_id": block_id,
                    }
                )

        # Attach round totals to block (optional: makes Stats export easier)
        try:
            block.pocol_block_time_s = block_time
            block.pocol_total_energy_kwh = total_energy_kwh
            block.pocol_total_co2_kg = total_co2_kg
            block.pocol_winner_id = winner_id
        except Exception:
            pass

        Consensus._energy_applied_block_ids.add(block_id)

    # ----------------------------
    # Fork resolution (same style as Bitcoin model)
    # ----------------------------
    @staticmethod
    def fork_resolution():
        BaseConsensus.global_chain = []

        lengths = [n.blockchain_length() for n in p.NODES]
        x = max(lengths) if lengths else 0

        candidates = [n for n in p.NODES if n.blockchain_length() == x]
        chosen = candidates[0] if candidates else None

        if chosen is None:
            return

        if len(candidates) > 1:
            last_miners = [n.last_block().miner for n in candidates if n.last_block().miner is not None]
            if last_miners:
                common = Counter(last_miners).most_common(1)[0][0]
                for n in candidates:
                    if n.last_block().miner == common:
                        chosen = n
                        break

        for b in chosen.blockchain:
            BaseConsensus.global_chain.append(b)
