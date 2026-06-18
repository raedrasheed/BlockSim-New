from Scheduler import Scheduler
from InputsConfig import InputsConfig as p
from Models.Bitcoin.Node import Node
from Statistics import Statistics
from Models.Transaction import LightTransaction as LT, FullTransaction as FT
from Models.Network import Network
from Models.Bitcoin.Consensus import Consensus as c
from Models.BlockCommit import BlockCommit as BaseBlockCommit


class BlockCommit(BaseBlockCommit):

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

        # Only accept if still mining on same tip
        if blockPrev == miner.last_block().id:
            # account mining up to block find time
            miner.stop_mining_and_account(eventTime, reason="mined_block", block_id=event.block.id)

            Statistics.totalBlocks += 1

            if p.hasTrans:
                if p.Ttechnique == "Light":
                    blockTrans, blockSize = LT.execute_transactions()
                else:
                    blockTrans, blockSize = FT.execute_transactions(miner, eventTime)

                event.block.transactions = blockTrans
                event.block.usedgas = blockSize

            miner.blockchain.append(event.block)

            if p.hasTrans and p.Ttechnique == "Light":
                LT.create_transactions()

            BlockCommit.propagate_block(event.block)
            BlockCommit.generate_next_block(miner, eventTime)

    @staticmethod
    def receive_block(event):
        miner = p.NODES[event.block.miner]
        currentTime = event.time
        blockPrev = event.block.previous

        node = p.NODES[event.node]
        lastBlockId = node.last_block().id

        # If this reception changes what we mine on, stop mining and account
        # (even if it ends up as fork logic later)
        node.stop_mining_and_account(currentTime, reason="received_block", block_id=event.block.id)

        if blockPrev == lastBlockId:
            node.blockchain.append(event.block)
            if p.hasTrans and p.Ttechnique == "Full":
                BlockCommit.update_transactionsPool(node, event.block)
            BlockCommit.generate_next_block(node, currentTime)
        else:
            depth = event.block.depth + 1
            if depth > len(node.blockchain):
                BlockCommit.update_local_blockchain(node, miner, depth)
                BlockCommit.generate_next_block(node, currentTime)

            if p.hasTrans and p.Ttechnique == "Full":
                BlockCommit.update_transactionsPool(node, event.block)

    @staticmethod
    def generate_next_block(node, currentTime):
        if getattr(node, "hashPower", 0) > 0:
            # start mining now on current tip
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
