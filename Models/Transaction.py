import random
import copy
import operator
from InputsConfig import InputsConfig as p
from Models.Network import Network


class Transaction(object):
    def __init__(self,
                 id=0,
                 timestamp=0,
                 sender=0,
                 to=0,
                 value=0,
                 size=0.000546,
                 fee=0):
        self.id = id
        self.timestamp = timestamp
        self.sender = sender
        self.to = to
        self.value = value
        self.size = size
        self.fee = fee


class LightTransaction:
    pending_transactions = []

    @staticmethod
    def create_transactions():
        LightTransaction.pending_transactions = []
        pool = LightTransaction.pending_transactions

        # original formula: Psize = Tn * Binterval
        Psize = int(p.Tn * p.Binterval)

        # hard cap to avoid huge memory/time (tune as you want)
        max_pool = int(getattr(p, "MaxPendingTx", 200_000))
        Psize = min(Psize, max_pool)

        for _ in range(Psize):
            tx = Transaction()
            tx.id = random.randrange(100000000000)
            tx.sender = random.choice(p.NODES).id
            tx.to = random.choice(p.NODES).id
            tx.size = random.expovariate(1 / p.Tsize)
            tx.fee = random.expovariate(1 / p.Tfee)
            pool.append(tx)

        # No shuffle needed: you sort by fee in execute_transactions anyway.

    @staticmethod
    def execute_transactions():
        pool = LightTransaction.pending_transactions

        # sort by fee desc (your model behavior)
        pool.sort(key=lambda x: x.fee, reverse=True)

        transactions = []
        size = 0.0
        blocksize = float(p.Bsize)

        for tx in pool:
            if blocksize >= tx.size:
                blocksize -= tx.size
                transactions.append(tx)
                size += tx.size

        return transactions, size


class FullTransaction:

    @staticmethod
    def create_transactions():
        Psize = int(p.Tn * p.simTime)

        for _ in range(Psize):
            tx = Transaction()
            tx.id = random.randrange(100000000000)

            creation_time = random.randint(0, p.simTime - 1)
            receive_time = creation_time
            tx.timestamp = [creation_time, receive_time]

            sender = random.choice(p.NODES)
            tx.sender = sender.id
            tx.to = random.choice(p.NODES).id
            tx.size = random.expovariate(1 / p.Tsize)
            tx.fee = random.expovariate(1 / p.Tfee)

            sender.transactionsPool.append(tx)
            FullTransaction.transaction_prop(tx)

    @staticmethod
    def transaction_prop(tx):
        for n in p.NODES:
            if tx.sender != n.id:
                t = copy.deepcopy(tx)
                t.timestamp[1] = t.timestamp[1] + Network.tx_prop_delay()
                n.transactionsPool.append(t)

    @staticmethod
    def execute_transactions(miner, currentTime):
        miner.transactionsPool.sort(key=operator.attrgetter('fee'), reverse=True)

        transactions = []
        size = 0.0
        blocksize = float(p.Bsize)

        for tx in miner.transactionsPool:
            if blocksize >= tx.size and tx.timestamp[1] <= currentTime:
                blocksize -= tx.size
                transactions.append(tx)
                size += tx.size

        return transactions, size
