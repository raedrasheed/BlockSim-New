# Models/PoCol/BlockCommit.py

from Scheduler import Scheduler
from InputsConfig import InputsConfig as p
from Statistics import Statistics
from Models.Transaction import LightTransaction as LT, FullTransaction as FT
from Models.Network import Network

from Models.PoCol.Consensus import Consensus as c
from Models.BlockCommit import BlockCommit as BaseBlockCommit


class BlockCommit(BaseBlockCommit):
    """
    PoCol block commit logic is identical to Bitcoin's BlockCommit structure,
    but uses PoCol consensus (c).

    Key addition:
    - When a create_block event is ACCEPTED, we call:
        c.apply_energy_for_created_block(event.block)
      so energy is recorded per miner for this block/round.
    """

    # Handling and running Events
    @staticmethod
    def handle_event(event):
        if event.type == "create_block":
            BlockCommit.generate_block(event)
        elif event.type == "receive_block":
            BlockCommit.receive_block(event)

    # Block Creation Event
    @staticmethod
    def generate_block(event):
        miner = p.NODES[event.block.miner]
        eventTime = event.time
        blockPrev = event.block.previous
        round_id = getattr(event.block, "round_id", None)

        # B2: reject events belonging to a round that another miner already won.
        # An invalidated event is not counted, charged, executed, or propagated,
        # and does not start a new round.
        if c.is_round_closed(blockPrev, round_id):
            return

        # miner still mining on top of its last block?
        if blockPrev == miner.last_block().id:
            # B2: the first valid block closes this (parent, round); every other
            # pending event for the same round will now be rejected above.
            c.close_round(parent_id=blockPrev, round_id=round_id,
                          winning_block_id=event.block.id, winning_miner_id=miner.id,
                          t=eventTime)

            # Count created block
            Statistics.totalBlocks += 1

            # Ensure block.timestamp is set (EnergyLog uses it as 't')
            try:
                if getattr(event.block, 'timestamp', None) is None:
                    event.block.timestamp = eventTime
            except Exception:
                pass

            # >>> Apply PoCol energy for this successfully created block
            c.apply_energy_for_created_block(event.block)

            # Add transactions if enabled
            if p.hasTrans:
                if p.Ttechnique == "Light":
                    blockTrans, blockSize = LT.execute_transactions()
                elif p.Ttechnique == "Full":
                    blockTrans, blockSize = FT.execute_transactions(miner, eventTime)
                else:
                    blockTrans, blockSize = [], 0

                event.block.transactions = blockTrans
                event.block.usedgas = blockSize

            # Commit locally
            miner.blockchain.append(event.block)

            # Generate new pending tx (Light)
            if p.hasTrans and p.Ttechnique == "Light":
                LT.create_transactions()

            # Propagate and schedule next
            BlockCommit.propagate_block(event.block)
            BlockCommit.generate_next_block(miner, eventTime)

    # Block Receiving Event
    @staticmethod
    def receive_block(event):
        miner = p.NODES[event.block.miner]
        currentTime = event.time
        blockPrev = event.block.previous

        node = p.NODES[event.node]  # recipient
        lastBlockId = node.last_block().id

        # Case 1: received block extends recipient's tip
        if blockPrev == lastBlockId:
            node.blockchain.append(event.block)

            if p.hasTrans and p.Ttechnique == "Full":
                BlockCommit.update_transactionsPool(node, event.block)

            BlockCommit.generate_next_block(node, currentTime)

        # Case 2: received block is not built on top of tip => may need update
        else:
            depth = event.block.depth + 1
            if depth > len(node.blockchain):
                BlockCommit.update_local_blockchain(node, miner, depth)

            BlockCommit.generate_next_block(node, currentTime)

            if p.hasTrans and p.Ttechnique == "Full":
                BlockCommit.update_transactionsPool(node, event.block)

    # Start mining/working on the next block (PoCol uses c.Protocol)
    @staticmethod
    def generate_next_block(node, currentTime):
        if getattr(node, "hashPower", 0) > 0:
            blockTime = currentTime + c.Protocol(node)
            # B2: stamp the event with the round it belongs to
            Scheduler.create_block_event(node, blockTime, round_id=c.round_id)

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
