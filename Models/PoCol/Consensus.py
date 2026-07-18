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

    Energy model (Phase B1 — wall-clock integration):
    - Energy is NOT charged per created block. Each Node integrates power over
      simulation wall-clock time via its meter (Models/Node.py: update_energy /
      finalize_energy). apply_energy_for_created_block only advances the meter.
    - For continuous mining the network total is P_network * simTime, independent
      of miner count and of the number of (stale) blocks — enforced by tests in
      tests/test_wallclock_energy.py.
    - History: the original model charged block_time / N_miners per block, then a
      corrected interim charged P_i * block_time per block; both were block-count
      driven and double-counted overlapping wall-clock across forks. Removed.
    """

    # Active round state
    active_parent_id = None
    active_solution_nonce = None
    active_nonce_space = None
    active_ranges = {}         # miner_id -> (start, end)
    active_winner_id = None
    active_winner_time = None  # seconds (time to produce this block)

    # ---- B2: explicit round context ----
    round_id = 0                       # monotonic round counter
    active_round_status = "ACTIVE"     # "ACTIVE" | "CLOSED"
    active_template_id = None          # H(parent_id, round_id) stand-in
    round_start_time = 0.0
    round_end_time = None
    winning_block_id = None
    winning_miner_id = None
    # closed rounds recorded as (parent_id, round_id) for lazy event rejection
    _closed_rounds = set()

    # ---- B5: target-based success bookkeeping ----
    active_exhausted_rounds = 0     # zero-success template attempts in the current round
    total_exhausted_rounds = 0      # cumulative across the run

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

    # ----------------------------
    # B2: round lifecycle API
    # ----------------------------
    @staticmethod
    def _open_round(parent_id):
        """Begin a new round for `parent_id`: bump round_id, derive template_id,
        set status ACTIVE."""
        Consensus.round_id += 1
        Consensus.active_parent_id = parent_id
        Consensus.active_round_status = "ACTIVE"
        Consensus.active_template_id = hash(("PoColTemplate", parent_id, Consensus.round_id))
        Consensus.round_end_time = None
        Consensus.winning_block_id = None
        Consensus.winning_miner_id = None

    @staticmethod
    def is_round_closed(parent_id, round_id):
        """True if the (parent_id, round_id) round has already produced a block."""
        if round_id is None:
            return False
        return (parent_id, round_id) in Consensus._closed_rounds

    @staticmethod
    def close_round(parent_id, round_id, winning_block_id, winning_miner_id, t):
        """Mark a round CLOSED; subsequent events for it must be rejected."""
        Consensus._closed_rounds.add((parent_id, round_id))
        if parent_id == Consensus.active_parent_id:
            Consensus.active_round_status = "CLOSED"
            Consensus.winning_block_id = winning_block_id
            Consensus.winning_miner_id = winning_miner_id
            Consensus.round_end_time = float(t)

    @staticmethod
    def _init_round(parent_id):
        miners = Consensus._miners()
        # B2: a fresh round begins whenever we (re)initialize for a parent
        Consensus._open_round(parent_id)
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

        # ---- B5: target-based stochastic success (replaces guaranteed nonce) ----
        # Per-hash success probability chosen so the expected NETWORK block time
        # equals the target interval T:  p = 1 / (H_total * T)  =>  network first-
        # success time ~ Exponential(rate = H_total * p = 1/T), mean T.
        # A finite nonce domain means a round can EXHAUST (zero successes) before
        # anyone finds a valid header; horizon = time to search the whole domain.
        T = Consensus._target_interval()
        winner_id, block_time, exhausted = Consensus._sample_round_outcome(
            miners, rates, H_total, space, T)
        Consensus.active_winner_id = winner_id
        Consensus.active_winner_time = float(block_time)
        Consensus.active_exhausted_rounds = int(exhausted)
        Consensus.total_exhausted_rounds += int(exhausted)
        # kept for verification/debug only; no longer determines the winner
        Consensus.active_solution_nonce = None

    @staticmethod
    def _sample_round_outcome(miners, rates, H_total, space, T, rng=None):
        """B5 success model. Returns (winner_id, block_time_s, exhausted_rounds).

        - p_success = 1/(H_total*T) (target-based per-hash probability).
        - Network first-success time ~ Exponential(1/T) (memoryless).
        - horizon = space / H_total is the time to exhaust the whole nonce domain.
          If the drawn success time exceeds the horizon, that attempt EXHAUSTS
          with zero successes; a fresh template is drawn (counted) and we retry.
          This makes zero/one/many successes all possible, as required.
        - The winner is chosen with probability proportional to hash share
          (equivalently, the miner whose range would contain the success).
        """
        rng = rng or random
        H_total = float(max(H_total, 1e-12))
        horizon = float(space) / H_total
        T = float(max(T, 1e-12))
        elapsed = 0.0
        exhausted = 0
        # geometric number of exhausted domains before a success
        while True:
            t = rng.expovariate(1.0 / T)
            if t <= horizon:
                block_time = elapsed + t
                break
            exhausted += 1
            elapsed += horizon
            if exhausted > 100000:      # numerical safety valve
                block_time = elapsed
                break
        # hash-weighted winner (uniform over the nonce domain -> proportional to range size = hash share)
        ids = [m.id for m in miners]
        winner_id = rng.choices(ids, weights=rates, k=1)[0]
        return winner_id, block_time, exhausted

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
        """Checkpoint-only hook (Phase B1).

        Energy is integrated over simulation wall-clock time by each Node's
        meter (see Models/Node.py: update_energy / finalize_energy). A created-
        block event only ADVANCES each miner's meter to the block time; it must
        never charge a full network round, which is what previously double-
        counted overlapping wall-clock intervals across fork/stale blocks and
        pushed total energy above the physical bound P_network * simTime.
        """
        if block is None:
            return
        t = getattr(block, "timestamp", None)
        if t is None:
            return
        t = float(t)
        for m in Consensus._miners():
            if hasattr(m, "update_energy"):
                m.update_energy(t)

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
