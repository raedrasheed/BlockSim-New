import random
import numpy as np
from InputsConfig import InputsConfig as p
from Models.Consensus import Consensus as BaseConsensus


class Consensus(BaseConsensus):
    """
    Ethereum PoW consensus timing model (Exponential mining-time model).
    """

    @staticmethod
    def Protocol(miner):
        total_hashpower = sum([n.hashPower for n in p.NODES]) if getattr(p, "NODES", None) else 0.0
        if total_hashpower <= 0:
            return float("inf")

        frac = float(miner.hashPower) / float(total_hashpower)
        return random.expovariate(frac * (1.0 / float(p.Binterval)))

    @staticmethod
    def fork_resolution():
        """
        Longest-chain fork-resolution with a tie-break on most common last-block miner (if available).
        """
        BaseConsensus.global_chain = []

        lengths = [n.blockchain_length() for n in p.NODES] if getattr(p, "NODES", None) else []
        x = max(lengths) if lengths else 0

        candidates = [n.id for n in p.NODES if n.blockchain_length() == x] if lengths else []
        chosen_id = candidates[0] if candidates else (p.NODES[0].id if getattr(p, "NODES", None) else 0)

        if len(candidates) > 1:
            last_miners = []
            for n in p.NODES:
                if n.blockchain_length() == x:
                    m = getattr(n.last_block(), "miner", None)
                    if isinstance(m, int) and m >= 0:
                        last_miners.append(m)

            if last_miners:
                counts = np.bincount(last_miners)
                chosen_last_miner = int(np.argmax(counts))
                for n in p.NODES:
                    if n.blockchain_length() == x and getattr(n.last_block(), "miner", None) == chosen_last_miner:
                        chosen_id = n.id
                        break

        for n in p.NODES:
            if n.id == chosen_id:
                for b in n.blockchain:
                    BaseConsensus.global_chain.append(b)
                break
