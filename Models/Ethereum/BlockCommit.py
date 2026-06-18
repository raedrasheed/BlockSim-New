from Scheduler import Scheduler
from InputsConfig import InputsConfig as p
from Statistics import Statistics
from Models.Network import Network
from Models.BlockCommit import BlockCommit as BaseBlockCommit

from Models.Ethereum.Node import Node
from Models.Ethereum.Consensus import Consensus as c
from Models.Ethereum.Transaction import LightTransaction as LT, FullTransaction as FT


class BlockCommit(BaseBlockCommit):
    """
    Ethereum PoW block commit logic (create/receive/propagate),
    extended with Bitcoin-style energy + CO2 accounting.
    """

    @staticmethod
    def handle_event(event):
        if event.type == "create_block":
            BlockCommit.generate_block(event)
        elif event.type == "receive_block":
            BlockCommit.receive_block(event)

    @staticmethod
    def generate_block(event):
        miner = p.NODES[event.block.miner]
        eventTime = event.time
        blockPrev = event.block.previous

        if blockPrev == miner.last_block().id:
            e_kwh, co2_kg, dur_s = miner.stop_mining_and_account(
                eventTime, reason="mined_block", block_id=event.block.id
            )

            try:
                event.block.energy_kwh = e_kwh
                event.block.co2_kg = co2_kg
                event.block.mining_duration_s = dur_s
            except Exception:
                pass

            Statistics.totalBlocks += 1

            if p.hasTrans:
                if p.Ttechnique == "Light":
                    blockTrans, blockSize = LT.execute_transactions()
                else:
                    blockTrans, blockSize = FT.execute_transactions(miner, eventTime)

                event.block.transactions = blockTrans
                event.block.usedgas = blockSize

            if getattr(p, "hasUncles", False):
                BlockCommit.update_unclechain(miner)
                event.block.uncles = Node.add_uncles(miner)

            miner.blockchain.append(event.block)

            if p.hasTrans and p.Ttechnique == "Light":
                LT.create_transactions()

            BlockCommit.propagate_block(event.block)
            BlockCommit.generate_next_block(miner, eventTime)

    @staticmethod
    def receive_block(event):
        sender = p.NODES[event.block.miner]
        node = p.NODES[event.node]
        currentTime = event.time
        blockPrev = event.block.previous
        lastBlockId = node.last_block().id

        if blockPrev == lastBlockId:
            node.stop_mining_and_account(currentTime, reason="received_block", block_id=event.block.id)

            node.blockchain.append(event.block)

            if p.hasTrans and p.Ttechnique == "Full":
                BaseBlockCommit.update_transactionsPool(node, event.block)

            BlockCommit.generate_next_block(node, currentTime)

        else:
            depth = event.block.depth + 1

            if depth > len(node.blockchain):
                node.stop_mining_and_account(currentTime, reason="received_block", block_id=event.block.id)

                BlockCommit.update_local_blockchain(node, sender, depth)

                if p.hasTrans and p.Ttechnique == "Full":
                    BaseBlockCommit.update_transactionsPool(node, event.block)

                BlockCommit.generate_next_block(node, currentTime)

            else:
                if getattr(p, "hasUncles", False):
                    node.unclechain.append(event.block)
                    BlockCommit.update_unclechain(node)

                if p.hasTrans and p.Ttechnique == "Full":
                    BaseBlockCommit.update_transactionsPool(node, event.block)

    @staticmethod
    def generate_next_block(node, currentTime):
        if getattr(node, "hashPower", 0) > 0:
            node.start_mining(node.last_block().id, currentTime)
            blockTime = currentTime + c.Protocol(node)
            Scheduler.create_block_event(node, blockTime)

    @staticmethod
    def generate_initial_events():
        currentTime = 0
        for node in p.NODES:
            BlockCommit.generate_next_block(node, currentTime)

    @staticmethod
    def propagate_block(block):
        for recipient in p.NODES:
            if recipient.id != block.miner:
                blockDelay = Network.block_prop_delay()
                Scheduler.receive_block_event(recipient, block, blockDelay)

    @staticmethod
    def update_local_blockchain(node, sender, depth):
        i = 0
        while i < depth:
            if i < len(node.blockchain):
                if node.blockchain[i].id != sender.blockchain[i].id:
                    if getattr(p, "hasUncles", False):
                        node.unclechain.append(node.blockchain[i])

                    newBlock = sender.blockchain[i]
                    node.blockchain[i] = newBlock

                    if p.hasTrans and p.Ttechnique == "Full":
                        BaseBlockCommit.update_transactionsPool(node, newBlock)
            else:
                newBlock = sender.blockchain[i]
                node.blockchain.append(newBlock)

                if p.hasTrans and p.Ttechnique == "Full":
                    BaseBlockCommit.update_transactionsPool(node, newBlock)

            i += 1

        if getattr(p, "hasUncles", False):
            BlockCommit.update_unclechain(node)

    @staticmethod
    def update_unclechain(node):
        seen = set()
        cleaned = []
        for u in getattr(node, "unclechain", []):
            uid = getattr(u, "id", None)
            if uid is None:
                continue
            if uid in seen:
                continue
            seen.add(uid)
            cleaned.append(u)
        node.unclechain = cleaned

        chain_ids = set(getattr(b, "id", None) for b in node.blockchain)
        node.unclechain = [u for u in node.unclechain if getattr(u, "id", None) not in chain_ids]

        included_uncle_ids = set()
        for b in node.blockchain:
            for u in getattr(b, "uncles", []) or []:
                included_uncle_ids.add(getattr(u, "id", None))

        node.unclechain = [u for u in node.unclechain if getattr(u, "id", None) not in included_uncle_ids]
