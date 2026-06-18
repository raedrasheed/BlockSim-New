import numpy as np
from InputsConfig import InputsConfig as p
from Models.Bitcoin.Node import Node
from Models.Consensus import Consensus as BaseConsensus
import random

class Consensus(BaseConsensus):

    """
	We modelled PoW consensus protocol by drawing the time it takes the miner to finish the PoW from an exponential distribution
        based on the invested hash power (computing power) fraction
    """
    def Protocol(miner):
        ##### Start solving a fresh PoW on top of last block appended #####
        TOTAL_HASHPOWER = sum([miner.hashPower for miner in p.NODES])
        hashPower = miner.hashPower/TOTAL_HASHPOWER
        return random.expovariate(hashPower * 1/p.Binterval)


    """
	This method apply the longest-chain approach to resolve the forks that occur when nodes have multiple differeing copies of the blockchain ledger
    """
    @staticmethod
    def fork_resolution():
        """
        Same fork-resolution strategy as Bitcoin model:
        - choose the longest local chain
        - break ties using the most common last block miner
        BUT: robust to missing miner IDs (None).
        """
        BaseConsensus.global_chain = []

        lengths = [n.blockchain_length() for n in p.NODES]
        x = max(lengths) if lengths else 0

        candidates = [n.id for n in p.NODES if n.blockchain_length() == x]
        chosen_id = candidates[0] if candidates else (p.NODES[0].id if p.NODES else 0)

        if len(candidates) > 1:
            last_miners = []
            for n in p.NODES:
                if n.blockchain_length() == x:
                    m = getattr(n.last_block(), "miner", None)
                    # Keep only valid integer miner IDs
                    if isinstance(m, int) and m >= 0:
                        last_miners.append(m)

            # If we have valid miner IDs, do bincount tie-break
            if last_miners:
                counts = np.bincount(last_miners)
                chosen_last_miner = int(np.argmax(counts))

                for n in p.NODES:
                    if n.blockchain_length() == x:
                        m = getattr(n.last_block(), "miner", None)
                        if m == chosen_last_miner:
                            chosen_id = n.id
                            break
            # else: fallback keep chosen_id as is (first candidate)

        # Copy the chosen chain into global_chain
        for n in p.NODES:
            if n.id == chosen_id:
                for b in n.blockchain:
                    BaseConsensus.global_chain.append(b)
                break

