from InputsConfig import InputsConfig as p
import random
from Event import Event, Queue

# Model ids (adjust if you use different numbers)
MODEL_BASE = 0
MODEL_BITCOIN = 1
MODEL_ETHEREUM = 2
MODEL_POCOL = 3
MODEL_APPENDABLE = 4  # only if you still use AppendableBlock elsewhere

# Pick the right Block class
if p.model == MODEL_ETHEREUM:
    from Models.Ethereum.Block import Block
else:
    # Bitcoin, PoCol, and Base typically use Models.Block.Block
    from Models.Block import Block

# AppendableBlock support (only if needed)
if p.model == MODEL_APPENDABLE:
    from Models.AppendableBlock.Block import Block as AB


class Scheduler:

    @staticmethod
    def create_block_event(miner, eventTime, parent_id=None, depth=None, meta=None):
        """Schedule a block creation event for a miner.

        Stage 3: optional explicit ``parent_id``/``depth`` let the PoCol
        finder-based scheduler stamp a block onto a specific round parent (rather
        than the miner's possibly-stale local tip), and ``meta`` attaches the
        immutable EventIdentity. All defaults preserve the original behaviour for
        the Bitcoin/base models.
        """
        if eventTime is None:
            return None
        if eventTime <= p.simTime:
            block = Block()
            block.miner = miner.id
            block.depth = depth if depth is not None else len(miner.blockchain)
            block.id = random.randrange(100000000000)
            block.previous = parent_id if parent_id is not None else miner.last_block().id
            block.timestamp = float(eventTime)
            block.meta = meta

            event = Event("create_block", block.miner, float(eventTime), block, meta=meta)
            Queue.add_event(event)
            return block
        return None

    @staticmethod
    def receive_block_event(recipient, block, blockDelay):
        """Schedule a block receiving event for a node."""
        receive_block_time = float(block.timestamp) + float(blockDelay)
        if receive_block_time <= p.simTime:
            e = Event("receive_block", recipient.id, receive_block_time, block)
            Queue.add_event(e)

    # -------- AppendableBlock-only APIs (kept for compatibility) --------
    @staticmethod
    def create_block_event_AB(node, eventTime, receiverGatewayId):
        if p.model != MODEL_APPENDABLE:
            return
        if eventTime <= p.simTime:
            block = AB()
            block.id = random.randrange(100000000000)
            block.timestamp = float(eventTime)
            block.nodeId = node.id
            block.gatewayIds = node.gatewayIds
            block.receiverGatewayId = receiverGatewayId
            event = Event("create_block", node.id, float(eventTime), block)
            Queue.add_event(event)

    @staticmethod
    def append_tx_list_event(txList, gatewayId, tokenTime, eventTime):
        if p.model != MODEL_APPENDABLE:
            return
        if eventTime <= p.simTime:
            block = AB()
            block.transactions = txList.copy()
            block.timestamp = float(tokenTime)
            event = Event("append_tx_list", gatewayId, float(eventTime), block)
            Queue.add_event(event)

    @staticmethod
    def receive_tx_list_event(txList, gatewayId, tokenTime, eventTime):
        if p.model != MODEL_APPENDABLE:
            return
        if eventTime <= p.simTime:
            block = AB()
            block.transactions = txList.copy()
            block.timestamp = float(tokenTime)
            event = Event("receive_tx_list", gatewayId, float(eventTime), block)
            Queue.add_event(event)
