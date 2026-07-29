# Models/PoCol/BlockCommit.py  (Stage 3: finder-based round model)

from Scheduler import Scheduler
from InputsConfig import InputsConfig as p
from Statistics import Statistics
from Models.Transaction import LightTransaction as LT, FullTransaction as FT
from Models.Network import Network
from Event import Queue

from Models.PoCol.Consensus import Consensus as c
from Models.PoCol import round_state as rs
from Models.BlockCommit import BlockCommit as BaseBlockCommit


class BlockCommit(BaseBlockCommit):
    """PoCol block-commit with explicit event classification (Stage 3).

    Only finder events (miners whose disjoint range contains a solution) are
    scheduled by ``Consensus.start_round``. On firing, each event is classified:

      * VALID_CURRENT_EVENT           -> accept block, ONE round transition;
      * LEGITIMATE_PROPAGATION_COMPETITOR -> genuine stale (found before hearing
        the winner); counted as stale, does NOT advance the round;
      * OBSOLETE_* / INVALID          -> rejected: no block, no stale, no reward,
        no round advance, no energy change (already-consumed energy is kept);
      * (finite-domain exhaustion is handled inside start_round, never here).

    Energy accounting is unchanged from Stage 2 (wall-clock start/stop).
    """

    @staticmethod
    def handle_event(event):
        # queue-peak diagnostic (bounded-growth evidence)
        try:
            if Queue.size() > c.diag.get("queue_peak", 0):
                c.diag["queue_peak"] = Queue.size()
        except Exception:
            pass
        if event.type == "create_block":
            BlockCommit.generate_block(event)
        elif event.type == "receive_block":
            BlockCommit.receive_block(event)

    # ---------------- Block creation (finder event fires) ----------------
    @staticmethod
    def generate_block(event):
        miner = p.NODES[event.block.miner]
        eventTime = event.time
        ev_meta = getattr(event, "meta", None) or getattr(event.block, "meta", None)

        c.diag["processed_events"] = c.diag.get("processed_events", 0) + 1

        if ev_meta is None:
            # No identity -> cannot validate; reject as invalid (should not occur).
            c.record_obsolete(rs.INVALID_EVENT)
            return

        label = c.classify(miner, ev_meta)

        # ---- rejected obsolete / invalid events ----
        if label in rs.OBSOLETE_CATEGORIES:
            c.record_obsolete(label)
            c.mark_consumed(ev_meta)     # idempotent; never processed twice
            return                        # no block/stale/reward/round/energy

        # ---- legitimate propagation competitor (genuine stale) ----
        if label == rs.LEGIT_COMPETITOR:
            miner.stop_mining_and_account(eventTime, reason="pocol_legit_stale",
                                          block_id=event.block.id)
            Statistics.totalBlocks += 1              # counted, but off the main chain
            c.diag["legit_stales"] += 1
            c.mark_consumed(ev_meta)
            # miner keeps its current tip; it will adopt the winner on receipt
            BlockCommit.generate_next_block(miner, eventTime)
            return

        # ---- VALID_CURRENT_EVENT: the round winner ----
        miner.stop_mining_and_account(eventTime, reason="pocol_mined", block_id=event.block.id)
        Statistics.totalBlocks += 1
        c.diag["processed_valid"] += 1
        c.diag["accepted_blocks"] += 1
        c.mark_advanced(ev_meta.parent_block_id)     # exactly one advance per parent
        c.mark_consumed(ev_meta)

        if getattr(event.block, "timestamp", None) is None:
            event.block.timestamp = eventTime

        if p.hasTrans:
            if p.Ttechnique == "Light":
                blockTrans, blockSize = LT.execute_transactions()
            elif p.Ttechnique == "Full":
                blockTrans, blockSize = FT.execute_transactions(miner, eventTime)
            else:
                blockTrans, blockSize = [], 0
            event.block.transactions = blockTrans
            event.block.usedgas = blockSize

        miner.blockchain.append(event.block)

        if p.hasTrans and p.Ttechnique == "Light":
            LT.create_transactions()

        # exactly one round transition: initialise the next round on this block
        c.start_round(event.block, eventTime)

        BlockCommit.propagate_block(event.block)
        BlockCommit.generate_next_block(miner, eventTime)

    # ---------------- Block reception (energy + chain adoption) ----------------
    @staticmethod
    def receive_block(event):
        miner = p.NODES[event.block.miner]
        currentTime = event.time
        blockPrev = event.block.previous

        node = p.NODES[event.node]  # recipient
        lastBlockId = node.last_block().id

        # Stage 2: receiving a block ends the recipient's ACTIVE interval.
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

    # ---------------- Mining restart (ENERGY ONLY; no scheduling) ----------------
    @staticmethod
    def generate_next_block(node, currentTime):
        """Open an ACTIVE energy interval for the miner on its current tip.

        Stage 3: block-event scheduling is NOT done here anymore -- only finders
        are scheduled, by Consensus.start_round. This method exists purely to
        keep the wall-clock energy accounting continuous.
        """
        if getattr(node, "hashPower", 0) > 0:
            node.start_mining(node.last_block().id, currentTime)

    @staticmethod
    def generate_initial_events():
        currentTime = 0
        c.configure()
        genesis = p.NODES[0].last_block()          # shared genesis (id=0)
        # all miners begin mining (energy); finders for round 1 are scheduled once
        for node in p.NODES:
            BlockCommit.generate_next_block(node, currentTime)
        c.start_round(genesis, float(currentTime), cause="genesis")

    @staticmethod
    def propagate_block(block):
        for recipient in p.NODES:
            if recipient.id != block.miner:
                blockDelay = Network.block_prop_delay()
                Scheduler.receive_block_event(recipient, block, blockDelay)
