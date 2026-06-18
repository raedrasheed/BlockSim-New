import operator
import random
import numpy as np

from InputsConfig import InputsConfig as p
from Models.Network import Network
from Models.Ethereum.Distribution.DistFit import DistFit


class Transaction(object):
    """
    Ethereum transaction model.
    In "Full" technique, timestamp is [creation_time, receive_time].
    """

    def __init__(
        self,
        id=0,
        timestamp=None,
        sender=0,
        to=0,
        value=0,
        size=0.000546,
        gasLimit=8000000,
        usedGas=0,
        gasPrice=0,
        fee=0,
    ):
        self.id = id
        self.timestamp = timestamp if timestamp is not None else 0
        self.sender = sender
        self.to = to
        self.value = value
        self.size = size
        self.gasLimit = gasLimit
        self.usedGas = usedGas
        self.gasPrice = gasPrice
        self.fee = usedGas * gasPrice


class LightTransaction:
    pool = []
    _distfit_ready = False

    @staticmethod
    def _cap_pool(psize: int) -> int:
        cap = int(getattr(p, "LightTxPoolMax", 0) or 0)
        return min(psize, cap) if cap > 0 else psize

    @staticmethod
    def _fast_sample(psize: int):
        """
        Fast fallback sampler (no DistFit).
        Produces reasonable gasLimit/usedGas/gasPrice values quickly.
        """
        gasLimit = np.random.randint(21000, int(p.Blimit), size=psize)
        usedGas = np.minimum(
            gasLimit,
            np.random.randint(21000, int(p.Blimit), size=psize),
        )

        # gasPrice in Gwei-ish scale (right-skewed)
        gasPrice = np.random.lognormal(mean=2.0, sigma=0.8, size=psize)

        return gasLimit, usedGas, gasPrice

    @staticmethod
    def create_transactions():
        LightTransaction.pool = []

        psize = int(p.Tn * p.Binterval)
        psize = LightTransaction._cap_pool(psize)

        use_distfit = bool(getattr(p, "UseTxDistFit", True))

        if use_distfit:
            if not LightTransaction._distfit_ready:
                DistFit.fit()  # should run ONCE
                LightTransaction._distfit_ready = True

            gasLimit, usedGas, gasPrice, _ = DistFit.sample_transactions(psize)

            # if DistFit returns gasPrice in Wei, convert -> Gwei
            gasPrice = np.array(gasPrice, dtype=float) / 1_000_000_000.0
        else:
            gasLimit, usedGas, gasPrice = LightTransaction._fast_sample(psize)

        for i in range(psize):
            tx = Transaction()
            tx.id = random.randrange(100000000000)
            tx.sender = random.choice(p.NODES).id
            tx.to = random.choice(p.NODES).id

            tx.gasLimit = int(gasLimit[i])
            tx.usedGas = int(usedGas[i])
            tx.gasPrice = float(gasPrice[i])

            tx.fee = tx.usedGas * tx.gasPrice
            LightTransaction.pool.append(tx)

        random.shuffle(LightTransaction.pool)

    @staticmethod
    def execute_transactions():
        transactions = []
        count = 0
        blocklimit = p.Blimit

        pool = sorted(LightTransaction.pool, key=lambda x: x.gasPrice, reverse=True)

        while count < len(pool):
            if blocklimit >= pool[count].gasLimit:
                blocklimit -= pool[count].usedGas
                transactions.append(pool[count])
            count += 1

        used_gas_sum = sum(t.usedGas for t in transactions)
        return transactions, used_gas_sum


class FullTransaction:
    _distfit_ready = False
    x = 0

    @staticmethod
    def create_transactions():
        psize = int(p.Tn * p.Binterval)

        if FullTransaction.x < 1:
            # keep original behavior but ensure DistFit is fit once
            if not FullTransaction._distfit_ready:
                DistFit.fit()
                FullTransaction._distfit_ready = True
            FullTransaction.x += 1

        gasLimit, usedGas, gasPrice, _ = DistFit.sample_transactions(psize)
        gasPrice = np.array(gasPrice, dtype=float) / 1_000_000_000.0

        for i in range(psize):
            tx = Transaction()
            tx.id = random.randrange(100000000000)

            creation_time = random.randint(0, p.simTime - 1)
            receive_time = creation_time
            tx.timestamp = [creation_time, receive_time]

            sender = random.choice(p.NODES)
            tx.sender = sender.id
            tx.to = random.choice(p.NODES).id

            tx.gasLimit = int(gasLimit[i])
            tx.usedGas = int(usedGas[i])
            tx.gasPrice = float(gasPrice[i])
            tx.fee = tx.usedGas * tx.gasPrice

            sender.transactionsPool.append(tx)
            FullTransaction.transaction_prop(tx)

    @staticmethod
    def transaction_prop(tx):
        for i in p.NODES:
            if tx.sender != i.id:
                t = tx
                t.timestamp[1] = t.timestamp[1] + Network.tx_prop_delay()
                i.transactionsPool.append(t)

    @staticmethod
    def execute_transactions(miner, currentTime):
        transactions = []
        count = 0
        blocklimit = p.Blimit

        miner.transactionsPool.sort(key=operator.attrgetter("gasPrice"), reverse=True)
        pool = miner.transactionsPool

        while count < len(pool):
            if (blocklimit >= pool[count].gasLimit) and (pool[count].timestamp[1] <= currentTime):
                blocklimit -= pool[count].usedGas
                transactions.append(pool[count])
            count += 1

        used_gas_sum = sum(t.usedGas for t in transactions)
        return transactions, used_gas_sum
