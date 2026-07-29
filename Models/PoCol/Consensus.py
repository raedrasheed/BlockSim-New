# Models/PoCol/Consensus.py  (Stage 3: finder-based round model)

import math
import random
import hashlib
import json
from collections import Counter

from InputsConfig import InputsConfig as p
from Models.Consensus import Consensus as BaseConsensus
from Models.PoCol import round_state as rs


class Consensus(BaseConsensus):
    """PoCol consensus with explicit round/event identity and finite-domain
    semantics (Stage 3).

    Key correction vs Stages 1-2: only miners whose disjoint range actually
    contains a solution ("finders") schedule a block event. Loser miners no
    longer fabricate blocks, which removes the artefactual "stale explosion" and
    the O(N) per-round event bloat. Every scheduled event carries an immutable
    EventIdentity and is classified on firing (valid / legitimate competitor /
    obsolete-by-category / exhaustion / invalid).

    Difficulty: p = 1/(H_total * B); domain size S -> mu = p*S expected solutions;
    a round may find no solution (finite-domain exhaustion) -> new template
    generation. Energy is unchanged (Stage 2 wall-clock model).
    """

    # ---- configuration (set in configure()) ----
    configured = False
    base_seed = 0
    h_total_hps = 0.0
    interval_s = 600.0
    p_success = 0.0
    target = 0
    target_version = 0
    nonce_space = 0
    MAX_REFRESH = 10000

    # ---- identity counters ----
    _event_seq = 0
    _round_seq = 0
    _template_seq = 0

    # ---- round metadata keyed by parent block id ----
    round_meta = {}            # parent_id -> dict(round_id, generation_id, template_id, template_generation_id, target_version)
    advanced_parents = set()   # parent ids whose round already produced the accepted (winner) block
    consumed_events = set()    # event_ids already processed/invalidated
    round_transitions = []     # ordered list of round-transition records (with cause)

    # ---- diagnostics ----
    diag = {}

    # ------------------------------------------------------------------
    @staticmethod
    def _reset_diag():
        Consensus.diag = {
            "scheduled_events": 0,
            "processed_valid": 0,
            "legit_stales": 0,
            "accepted_blocks": 0,
            "rounds_started": 0,
            "exhausted_rounds": 0,
            "template_refreshes": 0,
            "queue_peak": 0,
            "obsolete": {rs.OBSOLETE_ROUND: 0, rs.OBSOLETE_PARENT: 0,
                         rs.OBSOLETE_TEMPLATE: 0, rs.OBSOLETE_GENERATION: 0,
                         rs.OBSOLETE_DIFFICULTY: 0, rs.INVALID_EVENT: 0},
            "warnings": [],
        }

    @staticmethod
    def configure():
        """Compute difficulty/domain from the current network; reset all state."""
        seed = getattr(p, "RandomSeed", None)
        Consensus.base_seed = int(seed) if seed is not None else 0
        # aggregate hash rate from the corrected per-miner model (Stage 2)
        h = 0.0
        for n in getattr(p, "NODES", []):
            if hasattr(n, "hash_rate_hps"):
                h += float(n.hash_rate_hps())
            else:
                h += float(getattr(n, "hashPower", 0.0) or 0.0)
        Consensus.h_total_hps = h if h > 0 else 1.0
        Consensus.interval_s = float(getattr(p, "PoCol_TargetInterval", getattr(p, "Binterval", 600.0)))
        Consensus.p_success, Consensus.target = rs.target_for_interval(
            Consensus.h_total_hps, Consensus.interval_s)
        Consensus.target_version = int(getattr(p, "PoCol_TargetVersion", 1))
        # domain size S -> expected solutions mu = p*S. Default factor 2 (S=2HB, mu=2).
        factor = float(getattr(p, "PoCol_DomainFactor", 2.0))
        Consensus.nonce_space = max(int(Consensus.h_total_hps * Consensus.interval_s * factor), 1)
        # reset identity + state
        Consensus._event_seq = 0
        Consensus._round_seq = 0
        Consensus._template_seq = 0
        Consensus.round_meta = {}
        Consensus.advanced_parents = set()
        Consensus.consumed_events = set()
        Consensus.round_transitions = []
        Consensus._reset_diag()
        # seed global RNG so block ids / draws are reproducible for a given seed
        random.seed(Consensus.base_seed)
        Consensus.configured = True

    # ------------------------------------------------------------------
    @staticmethod
    def _rates():
        rates = {}
        for n in getattr(p, "NODES", []):
            r = float(n.hash_rate_hps()) if hasattr(n, "hash_rate_hps") else float(getattr(n, "hashPower", 0.0) or 0.0)
            rates[n.id] = max(r, 0.0)
        return rates

    @staticmethod
    def _partition_ranges(S, rates):
        """Disjoint ranges over [0, S) proportional to hash rate. Returns list of
        (miner_id, start, end_inclusive). Only miners with rate>0 get a range."""
        total = sum(rates.values())
        ids = [mid for mid in rates if rates[mid] > 0]
        if total <= 0 or not ids:
            return []
        lengths = []
        acc = 0
        for mid in ids:
            L = max(int((rates[mid] / total) * S), 1)
            lengths.append(L)
            acc += L
        # fix rounding drift on the last active miner
        if acc != S:
            lengths[-1] = max(lengths[-1] + (S - acc), 1)
        ranges = []
        start = 0
        for mid, L in zip(ids, lengths):
            ranges.append((mid, start, start + L - 1))
            start += L
        return ranges

    @staticmethod
    def _round_rng(parent_id, round_id, tgen):
        key = f"{Consensus.base_seed}:{parent_id}:{round_id}:{tgen}".encode()
        seed = int.from_bytes(hashlib.sha256(key).digest()[:8], "big")
        return random.Random(seed)

    @staticmethod
    def _node_by_id(mid):
        for n in p.NODES:
            if n.id == mid:
                return n
        return None

    # ------------------------------------------------------------------
    @staticmethod
    def start_round(parent_block, current_time, cause="accepted_block"):
        """Initialise the round on `parent_block` and schedule finder events.

        Draws solutions from the finite domain; on exhaustion (no solution) it
        creates a NEW template generation and re-draws, bounded by MAX_REFRESH.
        Records exhaustion/refresh diagnostics. Exhaustion is never a block.

        `cause` is one of: "genesis", "accepted_block", "reset".
        """
        from Scheduler import Scheduler

        parent_id = parent_block.id
        old_round = Consensus._round_seq
        Consensus._round_seq += 1
        round_id = Consensus._round_seq
        generation_id = round_id
        tgen = 0
        base_offset = 0.0            # accumulated search time of exhausted domains
        S = Consensus.nonce_space
        rates = Consensus._rates()

        sols = []
        template_id = 0
        refreshes = 0
        while True:
            Consensus._template_seq += 1
            template_id = Consensus._template_seq
            ranges = Consensus._partition_ranges(S, rates)
            rng = Consensus._round_rng(parent_id, round_id, tgen)
            sols = rs.draw_round_solutions(rng, Consensus.p_success, S, ranges, rates)
            if sols:
                break
            # ---- finite-domain exhaustion (category G) ----
            Consensus.diag["exhausted_rounds"] += 1
            Consensus.diag["template_refreshes"] += 1
            # each exhausted domain consumed S / H_total seconds of search
            base_offset += float(S) / max(Consensus.h_total_hps, 1e-12)
            tgen += 1
            refreshes += 1
            if refreshes > Consensus.MAX_REFRESH:
                Consensus.diag["warnings"].append(
                    f"round on parent {parent_id} exceeded MAX_REFRESH")
                break

        Consensus.round_meta[parent_id] = dict(
            round_id=round_id, generation_id=generation_id, template_id=template_id,
            template_generation_id=tgen, target_version=Consensus.target_version)
        Consensus.diag["rounds_started"] += 1
        # section 8.4: record the round transition and its cause
        Consensus.round_transitions.append(dict(
            old_round_id=old_round, new_round_id=round_id, parent_block_id=parent_id,
            template_id=template_id, template_generation_id=tgen,
            target_version=Consensus.target_version, timestamp=float(current_time),
            cause=("exhaustion+" + cause) if tgen > 0 else cause,
            exhaust_refreshes=tgen))

        # schedule one create_block event per finder (solution holder)
        for s in sols:
            Consensus._event_seq += 1
            fires_at = float(current_time) + base_offset + s.finder_time_s
            meta = rs.EventIdentity(
                event_id=Consensus._event_seq, event_generation_id=generation_id,
                round_id=round_id, parent_block_id=parent_id,
                parent_height=getattr(parent_block, "depth", 0),
                template_id=template_id, template_generation_id=tgen,
                miner_id=s.miner_id, scheduled_at=float(current_time),
                fires_at=fires_at, target_version=Consensus.target_version,
                nonce_range_id=s.miner_id)
            node = Consensus._node_by_id(s.miner_id)
            if node is None:
                continue
            blk = Scheduler.create_block_event(
                node, fires_at, parent_id=parent_id,
                depth=getattr(parent_block, "depth", 0) + 1, meta=meta)
            if blk is not None:
                Consensus.diag["scheduled_events"] += 1

    # ------------------------------------------------------------------
    @staticmethod
    def current_state(miner, ev_meta):
        tip = miner.last_block()
        tm = Consensus.round_meta.get(tip.id, dict(
            round_id=0, generation_id=0, template_id=0,
            template_generation_id=0, target_version=Consensus.target_version))
        return rs.CurrentState(
            miner_tip_id=tip.id,
            miner_generation_id=tm["generation_id"],
            current_round_id=tm["round_id"],
            current_template_id=tm["template_id"],
            current_template_generation_id=tm["template_generation_id"],
            current_target_version=Consensus.target_version,
            parent_already_advanced=(ev_meta.parent_block_id in Consensus.advanced_parents),
            consumed=(ev_meta.event_id in Consensus.consumed_events))

    @staticmethod
    def classify(miner, ev_meta):
        return rs.classify_event(ev_meta, Consensus.current_state(miner, ev_meta))

    @staticmethod
    def mark_consumed(ev_meta):
        if ev_meta is not None:
            Consensus.consumed_events.add(ev_meta.event_id)   # idempotent (set)

    @staticmethod
    def mark_advanced(parent_id):
        Consensus.advanced_parents.add(parent_id)

    @staticmethod
    def record_obsolete(label):
        Consensus.diag["obsolete"][label] = Consensus.diag["obsolete"].get(label, 0) + 1

    # ------------------------------------------------------------------
    @staticmethod
    def diagnostics():
        d = dict(Consensus.diag)
        nodes = getattr(p, "NODES", [])
        accepted = Consensus.diag.get("accepted_blocks", 0)
        d.update(
            h_total_hps=Consensus.h_total_hps, target=str(Consensus.target),
            target_version=Consensus.target_version, p_success=Consensus.p_success,
            nonce_space=str(Consensus.nonce_space),
            expected_solutions=rs.expected_solutions(Consensus.p_success, Consensus.nonce_space),
            finite_domain_exhaust_prob=rs.finite_domain_exhaust_prob(Consensus.p_success, Consensus.nonce_space),
            analytical_expected_interval_s=rs.expected_block_interval(Consensus.h_total_hps, Consensus.p_success),
            effective_block_interval_s=(float(getattr(p, "simTime", 0.0)) / accepted) if accepted else None,
            obsolete_total=sum(Consensus.diag.get("obsolete", {}).values()),
            total_active_energy_kwh=sum(float(getattr(n, "active_energy_kwh", 0.0)) for n in nodes),
            total_idle_energy_kwh=sum(float(getattr(n, "idle_energy_kwh", 0.0)) for n in nodes),
            total_coordination_energy_kwh=sum(float(getattr(n, "coordination_energy_kwh", 0.0)) for n in nodes),
            total_energy_kwh=sum(float(getattr(n, "energy_kwh", 0.0)) for n in nodes),
            base_seed=Consensus.base_seed)
        return d

    @staticmethod
    def dump_diagnostics(path):
        try:
            with open(path, "w") as f:
                json.dump(Consensus.diagnostics(), f, indent=2)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Deprecated Stage-1/2 energy hook (kept as a no-op; energy is wall-clock)
    # ------------------------------------------------------------------
    @staticmethod
    def apply_energy_for_created_block(block):
        """DEPRECATED no-op. Energy is accounted on a wall-clock basis via
        Node.start_mining / Node.stop_mining_and_account (Stage 2)."""
        return None

    # ------------------------------------------------------------------
    # Fork resolution (unchanged: longest chain, tie-break on last miner)
    # ------------------------------------------------------------------
    @staticmethod
    def fork_resolution():
        BaseConsensus.global_chain = []
        lengths = [n.blockchain_length() for n in p.NODES]
        x = max(lengths) if lengths else 0
        candidates = [n for n in p.NODES if n.blockchain_length() == x]
        chosen = candidates[0] if candidates else None
        if chosen is None:
            return
        if len(candidates) > 1:
            last_miners = [n.last_block().miner for n in candidates if n.last_block().miner is not None]
            if last_miners:
                common = Counter(last_miners).most_common(1)[0][0]
                for n in candidates:
                    if n.last_block().miner == common:
                        chosen = n
                        break
        for b in chosen.blockchain:
            BaseConsensus.global_chain.append(b)
