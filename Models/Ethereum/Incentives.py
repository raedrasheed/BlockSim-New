from InputsConfig import InputsConfig as p
from Models.Consensus import Consensus as c
from Models.Incentives import Incentives as BaseIncentives
from Statistics import Statistics


class Incentives(BaseIncentives):
    """
    Ethereum incentives:
    - Block reward + transaction fees
    - Uncle generation rewards
    - Uncle inclusion rewards
    """

    @staticmethod
    def uncle_rewards(bc):
        for uncle in getattr(bc, "uncles", []):
            for k in p.NODES:
                if getattr(uncle, "miner", None) == k.id:
                    Statistics.totalUncles += 1
                    uncle_height = getattr(uncle, "depth", 0)
                    block_height = getattr(bc, "depth", 0)
                    k.uncles += 1
                    k.balance += ((uncle_height - block_height + 8) * p.Breward / 8)

    @staticmethod
    def uncle_inclusion_rewards(bc):
        ru = 0
        for _uncle in getattr(bc, "uncles", []):
            ru += p.UIreward
        return ru

    @staticmethod
    def distribute_rewards():
        for bc in c.global_chain:
            for m in p.NODES:
                if getattr(bc, "miner", None) == m.id:
                    m.blocks += 1
                    m.balance += p.Breward
                    tx_fee = Incentives.transactions_fee(bc)
                    m.balance += tx_fee
                    m.balance += Incentives.uncle_inclusion_rewards(bc)

            Incentives.uncle_rewards(bc)
